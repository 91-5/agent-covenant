#!/usr/bin/env python3
"""link_card.py - write a verdict's fields back into its card's link file.

Phase 1 of the deepfreeze <-> agent-covenant fusion. The pair splits cleanly:

  * deepfreeze's `protect --card <id>` writes the **snap group** into
    `.freeze/link-<id>.json`: `card`, `snap_ts`, `snap_path`, `snapshot_root`,
    `source`, `created_at`.
  * this tool writes the **verdict group** into the *same* file once a verdict
    exists: `verdict_ts`, `verdict_sha256`, `verifier`, `updated_at`.

Each side owns its own field group and neither imports the other, so the two
tools stay independently copyable. This tool never reads `.freeze-snap` and
never touches a snapshot directory.

It **only writes; it does not validate**. Nothing machine-checks a link today -
a gate that reads the link back to confirm "this verdict covers that snapshot"
is a later phase. Until then, treat the link as a record, not as a check.

Usage
-----
    python tools/link_card.py --card DFB-20261019-001 --verdict verdicts/DFB-20261019-001.verdict.json
    python tools/link_card.py --card XJ-20261019-001 --verdict verdicts/XJ-20261019-001.verdict.json --freeze-dir /path/to/.freeze

Exit codes
----------
    0  the link file was updated
    1  a business error (no link to update, unreadable/corrupt link, verdict
       does not belong to this card, unsafe card id); the message says what to do
    2  usage error (missing/unreadable arguments)

Behaviour
---------
    1. Reject a `--card` that could escape the freeze directory (path
       separators, `..`, an absolute prefix, or empty). Namespace *format* is
       deliberately not checked here - that is lint_cards.py's job; this guard
       only stops a link filename from walking out of the directory.
    2. Find `<freeze-dir>/link-<card>.json`. Missing -> exit 1 with the
       "run deepfreeze protect --card <id> first" hint.
    3. Parse the verdict: it must be JSON, `id` must equal `--card` (a verdict
       for another card must never be bound here), and `ts` must be present.
    4. Read the existing link. If it does not parse, exit 1 and leave it
       untouched - overwriting it would destroy the snapshot binding.
    5. Hash the verdict file's *raw bytes* (streamed SHA-256).
    6. Merge: keep every existing field (the snap group in particular) and set
       only the verdict group. The snap group is never written here.
    7. Write back atomically (temp file in the same directory + os.replace) so a
       concurrent reader never sees a half-written link.
    8. On success, print one summary line:
       `linked <card>: snap_ts=<...> verdict_ts=<...>`

Re-running for the same card (a rework with a new verdict) overwrites the
verdict group, last-write-wins - symmetric with deepfreeze overwriting the snap
group on a repeat protect.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2

LINK_PREFIX = "link-"
LINK_SUFFIX = ".json"
DEFAULT_FREEZE_DIR = ".freeze"

#: Verdict-group fields this tool owns. The snap group (card, snap_ts,
#: snap_path, snapshot_root, source, created_at) belongs to deepfreeze and is
#: never written here - writing it would be a second writer on one field group.
VERDICT_GROUP = ("verdict_ts", "verdict_sha256", "verifier", "updated_at")


def _safe_utf8() -> None:
    """Windows consoles default to a legacy codepage; never let output crash."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _utc_now_z() -> str:
    """Current UTC time as ISO-8601 with a trailing `Z` (no microseconds)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def is_unsafe_card_id(card):
    """True when `card` could escape the freeze directory as a filename.

    Rejects an empty value, anything with a path separator, a `..` component,
    and an absolute/drive-prefixed path. This is a path-injection guard only;
    it does not judge whether the id's namespace is well formed.
    """
    if not isinstance(card, str) or not card.strip():
        return True
    if "/" in card or "\\" in card:
        return True
    if ".." in card:
        return True
    # An absolute path or a drive-relative path (e.g. `C:evil`, `/etc/x`).
    if os.path.isabs(card) or Path(card).is_absolute():
        return True
    if len(card) >= 2 and card[1] == ":":
        return True
    return False


def load_json_file(path):
    """Return (data, error). `error` is a short human-readable string on failure."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return None, f"cannot read {path}: {exc}"
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return None, f"{path} is not valid UTF-8: {exc}"
    try:
        data = json.loads(text)
    except ValueError as exc:
        return None, f"cannot parse {path}: {exc}"
    if not isinstance(data, dict):
        return None, f"{path} must contain a JSON object"
    return data, None


def sha256_file(path):
    """SHA-256 of a file's raw bytes, streamed (no full-file slurp)."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path, data):
    """Write `data` as UTF-8 JSON atomically in the same directory.

    A temp file next to the target plus `os.replace` means a concurrent reader
    (deepfreeze reading the link) never observes a truncated file. The temp
    file is removed if anything fails.
    """
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    directory = path.parent
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(directory))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.remove(tmp_name)
        except OSError:
            pass
        raise


def build_parser():
    parser = argparse.ArgumentParser(
        prog="link_card.py",
        description="Write a verdict's fields back into .freeze/link-<card>.json "
                    "(the verdict group), preserving deepfreeze's snap group.",
    )
    parser.add_argument("--card", required=True,
                        help="card id whose link file to update (e.g. DFB-20261019-001)")
    parser.add_argument("--verdict", required=True,
                        help="path to the machine-readable verdict JSON for this card")
    parser.add_argument("--freeze-dir", default=DEFAULT_FREEZE_DIR, metavar="DIR",
                        help=f"directory holding the link files (default: {DEFAULT_FREEZE_DIR})")
    return parser


def main(argv=None):
    _safe_utf8()
    args = build_parser().parse_args(argv)

    card = args.card

    # 1. Path-injection guard: a card id is used as a filename component.
    if is_unsafe_card_id(card):
        print(f"[ERROR] unsafe --card value {card!r}: card ids must not be empty, "
              "contain '/', '\\\\', '..' or an absolute path prefix (a link filename "
              "must not be able to escape the freeze directory)", file=sys.stderr)
        return EXIT_ERROR

    freeze_dir = Path(args.freeze_dir)
    if not freeze_dir.is_dir():
        print(f"[ERROR] freeze directory not found: {freeze_dir} - pass --freeze-dir "
              "pointing at the directory that holds the link files", file=sys.stderr)
        return EXIT_ERROR

    link_path = freeze_dir / f"{LINK_PREFIX}{card}{LINK_SUFFIX}"

    # 2. The link must exist; it is written by deepfreeze, not created here.
    if not link_path.is_file():
        print(f"[ERROR] no link file at {link_path} - run "
              f"`deepfreeze protect --card {card}` first to create it, then re-run "
              "link_card.py", file=sys.stderr)
        return EXIT_ERROR

    # 3. The verdict must parse and must belong to this card.
    verdict_path = Path(args.verdict)
    if not verdict_path.is_file():
        print(f"[ERROR] verdict file not found: {verdict_path}", file=sys.stderr)
        return EXIT_ERROR
    verdict, error = load_json_file(verdict_path)
    if error:
        print(f"[ERROR] unreadable verdict: {error}", file=sys.stderr)
        return EXIT_ERROR
    if "id" not in verdict:
        print(f"[ERROR] verdict {verdict_path} has no 'id' field; cannot confirm it "
              f"belongs to {card}", file=sys.stderr)
        return EXIT_ERROR
    if verdict["id"] != card:
        print(f"[ERROR] verdict id {verdict['id']!r} does not match --card {card!r}; "
              "refusing to bind a verdict to the wrong card", file=sys.stderr)
        return EXIT_ERROR
    if "ts" not in verdict or not isinstance(verdict["ts"], str) or not verdict["ts"].strip():
        print(f"[ERROR] verdict {verdict_path} has no usable 'ts' field; "
              "verdict_ts would be empty", file=sys.stderr)
        return EXIT_ERROR

    # 4. Read the existing link. A corrupt link is never overwritten: it still
    #    holds the snapshot binding, and clobbering it would destroy evidence.
    link, error = load_json_file(link_path)
    if error:
        print(f"[ERROR] existing link is unreadable: {error} - refusing to overwrite it "
              "(that would destroy the snapshot binding); repair or re-run "
              f"`deepfreeze protect --card {card}`", file=sys.stderr)
        return EXIT_ERROR

    # 5. Hash the verdict's raw bytes.
    try:
        digest = sha256_file(verdict_path)
    except OSError as exc:
        print(f"[ERROR] cannot hash verdict {verdict_path}: {exc}", file=sys.stderr)
        return EXIT_ERROR

    # 6. Merge: keep the snap group, set only the verdict group.
    merged = dict(link)
    merged["verdict_ts"] = verdict["ts"]
    merged["verdict_sha256"] = digest
    if "verifier" in verdict:
        merged["verifier"] = verdict["verifier"]
    else:
        # verifier is optional in a verdict; if the previous link had one, it now
        # describes an older verdict, so drop it rather than leave a stale name.
        merged.pop("verifier", None)
    merged["updated_at"] = _utc_now_z()

    # 7. Atomic write-back.
    try:
        atomic_write_json(link_path, merged)
    except OSError as exc:
        print(f"[ERROR] cannot write link {link_path}: {exc}", file=sys.stderr)
        return EXIT_ERROR

    # 8. One summary line.
    snap_ts = link.get("snap_ts", "-")
    if snap_ts in (None, ""):
        snap_ts = "-"
    print(f"linked {card}: snap_ts={snap_ts} verdict_ts={merged['verdict_ts']}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
