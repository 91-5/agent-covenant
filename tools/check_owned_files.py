#!/usr/bin/env python3
"""agent-covenant owned-files reporter — SHADOW PERIOD, NEVER BLOCKS.

Answers one question after the fact: *did this branch touch files that no card
claimed?* `lint_cards.py` already checks owned_files at planning time
(`OWNED_FILES_CONFLICT`), but nothing ever compared a commit against the claim
surface, so a drifting agent was caught only by a reviewer reading a diff.

Three decisions define this tool, and all three are argued rather than assumed:

1. **Authorization is per-diff, not per-agent.** The obvious design -- "whatever
   cards this assignee has open" -- was rejected after review: one forgotten
   CLOSED card silently widens an agent's write surface forever, so the union
   grows stale exactly when discipline is already slipping. The author instead
   declares the cards a commit belongs to (`Card-Id:` trailers) and the
   authorized surface is the union of *those* cards. A commit with no trailer is
   therefore *not* a violation, it is an **unknown** -- reported, never failed,
   because a hard failure on a missing trailer punishes the honest agent that
   forgot a convention instead of the one that broke a boundary.

2. **Exit code is always 0.** This runs in shadow mode for a week to collect
   false-positive data before anyone is allowed to be blocked by it (see
   EVO-20261007-001). A checker that can fail the build before its false-positive
   rate is known is not a measurement, it is an outage. So every finding here --
   violation, unknown card, unreadable whitelist -- is data, and `--strict` is
   deliberately absent: adding it now would be building the enforcement path
   before the evidence that justifies it.

3. **The whitelist is an exception list, not a permission.** It is checked with
   exact paths only, because a glob in a shared exception list is a universal
   escape hatch wearing a config file's clothes. High-impact files (this
   repository's own CI, linter, gate, artifact map) are protected by
   `.github/CODEOWNERS` instead -- a human approval boundary, which is the only
   kind that survives a determined agent.

Usage
-----
    python tools/check_owned_files.py --card-dir .tasks --json
    python tools/check_owned_files.py --card-dir .tasks --warn
    python tools/check_owned_files.py --card-dir .tasks --base origin/master
    python tools/check_owned_files.py --card-dir .tasks --whitelist policy/owned-files-whitelist.yml

Exit codes
----------
    0  always, by design (see decision 2). Internal failures are reported on
       stderr and in the JSON payload as `error`; they do not change the code
       so that a broken report can never masquerade as a clean one *silently* --
       `error` is always present in `--json` output when something went wrong.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

EXIT_OK = 0  # structural constant: shadow period, see decision 2

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CARD_DIR = REPO_ROOT / ".tasks"
DEFAULT_WHITELIST = REPO_ROOT / "policy" / "owned-files-whitelist.yml"
DEFAULT_BASE = "origin/master"

# Card ids look like `XJ-20261004-006`; the trailer may carry several.
CARD_ID_RE = re.compile(r"\b([A-Z]{2,6}-\d{8}-\d{3})\b")
TRAILER_RE = re.compile(r"^\s*(?:card-ids?)\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)


def _safe_utf8() -> None:
    """Windows consoles default to a legacy codepage; never let output crash."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _load_linter():
    """Reuse lint_cards' parsers instead of re-implementing the card grammar.

    `_owned_files`, `_is_active` and `_paths_overlap` encode decisions that were
    already argued (directory claims own their subtree, glob prefix counts as
    overlap, GATED/CLOSED means inactive). A second parser would drift from the
    first within a release, and the drift would show up as enforcement gaps.
    """
    spec = importlib.util.spec_from_file_location(
        "lint_cards", REPO_ROOT / "tools" / "lint_cards.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lint = _load_linter()


def _git(args, cwd):
    """Run a git command; return stdout or None when git is unhappy."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, ValueError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def resolve_base(cwd, base_spec):
    """Resolve the diff base.

    `merge-base` rather than the branch tip: on a branch that has fallen behind,
    diffing against the tip attributes someone else's commits to this branch and
    the report becomes noise nobody reads. Falls back to the literal spec when
    merge-base cannot run (no origin, fresh clone) and says so in the payload.
    """
    if base_spec != "auto":
        return base_spec, None
    for candidate in (DEFAULT_BASE, "origin/main", "main", "master"):
        merged = _git(["merge-base", candidate, "HEAD"], cwd)
        if merged and merged.strip():
            return merged.strip(), None
    return DEFAULT_BASE, "merge-base unavailable; fell back to the literal base"


def collect_trailer_card_ids(cwd, base, head="HEAD"):
    """Card ids declared by commit trailers in the range.

    The trailer is the author's *claim*, not proof — an agent can name someone
    else's card. That is a known limitation of the shadow design (recorded in the
    card's review questions), and it is why this tool reports coverage rather
    than certifying it.
    """
    body = _git(["log", "--format=%B", f"{base}..{head}"], cwd)
    if not body:
        return []
    found = []
    for line in TRAILER_RE.findall(body):
        found.extend(CARD_ID_RE.findall(line))
    seen = []
    for card_id in found:
        if card_id not in seen:
            seen.append(card_id)
    return seen


def trailer_adoption(cwd, base, head="HEAD"):
    """Count commits in range and how many declare a Card-Id trailer.

    Reviewer instruction (EVO-20261007-001 review, point 1a): the coverage gap
    -- "zero violations" does not mean "nothing drifted" -- is acceptable only
    while it is *measured*. A range where nobody uses the trailer convention
    produces a report that can say nothing about drift, so the adoption rate
    belongs in every report, and promoting the checker to a real gate is
    blocked until that rate reaches 50%.

    Returns `(total, with_trailer, measured)`. The third element exists because
    of a review finding on this function itself (round 002, point 3): returning
    `(0, 0)` when git failed made "could not measure" indistinguishable from
    "measured, and nothing declared a trailer". A measurement tool that reports
    a confident zero it never took is the same defect class as
    `TEST_COUNT_UNVERIFIED` -- a disabled check wearing a passing result. So a
    failed git call now says so explicitly and the report carries
    `trailer_measured: false`; callers must not read 0/0 as "all clear".

    This parses commits the same way `collect_trailer_card_ids` does -- one line
    at a time against `TRAILER_RE` -- after splitting on `\\x1e` (the record
    separator git itself uses). Round 002 used `\\x00`/`\\x01` instead, which
    was a second, divergent notion of "what is a trailer"; review point 1 asked
    for the two to be aligned so one commit body cannot be judged two ways.
    `\\x1e` splits *between* commits only and never takes part in the per-line
    analysis, so the anchor semantics stay identical to the id collector.
    """
    raw = _git(["log", "--format=%H%x1e%B%x1e", f"{base}..{head}"], cwd)
    if raw is None:
        return (0, 0, False)
    records = [chunk for chunk in raw.split("\x1e") if chunk.strip()]
    total = 0
    with_trailer = 0
    for record in records:
        # Each record is "<sha>\n<body>"; drop the sha line, then treat the body
        # exactly as the id collector does.
        body = record.split("\n", 1)[1] if "\n" in record else ""
        total += 1
        if any(TRAILER_RE.match(line) for line in body.splitlines()):
            with_trailer += 1
    return (total, with_trailer, True)


def changed_paths(cwd, base, head="HEAD"):
    """Changed paths as (status, path) pairs, renames contributing both sides.

    `--name-status` rather than `--name-only` because a rename that moves a file
    *out* of an owned path is exactly the diff shape that hides an unauthorized
    edit behind a legitimate one.
    """
    out = _git(["diff", "--name-status", "-M", f"{base}..{head}"], cwd)
    if out is None:
        return None
    pairs = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0].strip()
        if status.startswith("R") and len(parts) >= 3:
            pairs.append((status, parts[1].strip()))
            pairs.append((status, parts[2].strip()))
        elif len(parts) >= 2:
            pairs.append((status, parts[1].strip()))
    return pairs


def _norm(path):
    """Normalize to forward slashes so Windows reports compare to card claims."""
    return path.strip().replace("\\", "/").lstrip("./")


def _norm_claim(entry):
    """Normalize one owned-files claim as written on a card.

    Cards spell claims as markdown inline code -- templates/TASK.md says
    ``- `path/to/file.py` `` -- so the shared parser hands back the backticks.
    Stripping presentation markup here (rather than in `_owned_files`) keeps the
    conflict rule's existing behaviour untouched while letting this reporter
    compare a claim to a git path.
    """
    return entry.strip().strip("`'\"").replace("\\", "/").strip()


def load_whitelist(path):
    """Parse the exception list. Returns `(paths, invalid, missing)`.

    Hand-parsed because this repository is stdlib-only by policy. The accepted
    shape is deliberately narrow, and both spellings are supported:

        paths:
          - path: docs/lint-rules.md      # mapping form (owner/reason/expires
            owner: sir                    # lines are read but not enforced yet)
            expires: 2026-12-31
          - docs/other.md                 # bare form

        paths: []                         # inline empty list

    A glob, a directory claim (trailing slash) or a root path is reported as
    `invalid` rather than honoured -- see decision 3. Anything malformed is
    reported, never silently dropped: an exception list that fails open is
    indistinguishable from one that was never written.
    """
    if not path.is_file():
        return [], [], True
    entries = []
    in_paths = False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split(" #", 1)[0].rstrip() if " #" in raw else raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if not in_paths:
            if stripped == "paths:":
                in_paths = True
            continue
        # A new top-level key ends the list; an indented `- item` continues it.
        if indent == 0 and not stripped.startswith("-"):
            in_paths = False
            continue
        if stripped.startswith("- "):
            body = stripped[2:].strip()
            match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+)$", body)
            if match:
                key, value = match.group(1).lower(), match.group(2).strip()
                if key == "path":
                    entries.append(value.strip("'\""))
            elif body == "[]":
                continue
            else:
                entries.append(body.strip("'\""))
    valid = []
    invalid = []
    for entry in entries:
        raw = entry.strip().strip("'\"")
        candidate = _norm(raw)
        if (
            not candidate
            or "*" in raw
            or candidate.endswith("/")
            or "/" not in candidate
            or raw.startswith("/")
        ):
            invalid.append(entry)
        else:
            valid.append(candidate)
    return valid, invalid, False


def load_card_claims(card_dir, card_ids):
    """Authorized paths per declared card, plus cards that could not be used."""
    claims = {}
    unknown = []
    inactive = []
    for card_id in card_ids:
        candidates = list(card_dir.glob(f"{card_id}.md"))
        if not candidates:
            legacy = card_dir / "legacy"
            if legacy.is_dir():
                candidates = list(legacy.glob(f"{card_id}.md"))
        if not candidates:
            unknown.append(card_id)
            continue
        text = candidates[0].read_text(encoding="utf-8", errors="replace")
        if not lint._is_active(text):
            inactive.append(card_id)
            continue
        claims[card_id] = lint._owned_files(text)
    return claims, unknown, inactive


def evaluate(repo, card_dir, base_spec, head, whitelist_path):
    """Produce the report payload. Pure enough to be unit tested with fakes."""
    resolved_base, base_note = resolve_base(repo, base_spec)
    declared = collect_trailer_card_ids(repo, resolved_base, head)
    claims, unknown, inactive = load_card_claims(card_dir, declared)
    allowed = []
    for paths in claims.values():
        allowed.extend(_norm_claim(item) for item in paths)

    whitelist_paths, whitelist_invalid, whitelist_missing = load_whitelist(whitelist_path)

    violations = []
    whitelist_hits = 0
    changed = changed_paths(repo, resolved_base, head)
    if changed is None:
        return {
            "schema": "owned-files-dryrun/v1",
            "error": "git diff failed; is this a git repository with a reachable base?",
            "merge_base": resolved_base,
            "base_note": base_note,
            "authorized_card_ids": sorted(claims),
            "unknown_card_ids": unknown,
            "inactive_card_ids": inactive,
            "violations": [],
            "whitelist_invalid": whitelist_invalid,
            "whitelist_missing": whitelist_missing,
            "info": [],
            "metrics": {"changed_paths": 0, "violations": 0, "whitelist_hits": 0,
                        "commits_total": 0, "commits_with_trailer": 0,
                        "trailer_measured": False},
        }

    seen = set()
    for status, raw in changed:
        path = _norm(raw)
        if path in seen:
            continue
        seen.add(path)
        if any(lint._paths_overlap(path, allow) for allow in whitelist_paths):
            whitelist_hits += 1
            continue
        owner = None
        for card_id, paths in claims.items():
            if any(lint._paths_overlap(path, _norm_claim(allow)) for allow in paths):
                owner = card_id
                break
        if owner is None and not declared:
            # No card was declared at all: the authorization surface is unknown,
            # not exceeded. Reporting a violation here would punish the agent
            # that forgot a trailer convention instead of the one that broke a
            # boundary -- see decision 1. A declared-but-closed card is the
            # opposite case (the surface is known to be empty) and does fall
            # through to a violation, which is why this tests `declared` and not
            # the non-empty `claims`.
            continue
        if owner is None:
            violations.append({"path": path, "status": status, "covered_by": None})

    info = []
    commits_total, commits_with_trailer, trailer_measured = trailer_adoption(repo, resolved_base, head)
    if not trailer_measured:
        # Never let a failed measurement look like a clean bill of health.
        info.append(
            "trailer adoption: NOT MEASURED (git log failed) -- 0/0 here means "
            "'could not measure', not 'nothing declared a trailer'"
        )
    elif commits_total and commits_with_trailer < commits_total:
        info.append(
            f"trailer adoption: {commits_with_trailer}/{commits_total} commits declare a "
            "Card-Id trailer; until that reaches 50%, a zero-violation report is not "
            "evidence that nothing drifted (GATED precondition, review point 1a)"
        )
    if not declared:
        active = []
        for card_file in sorted(card_dir.glob("*.md")):
            text = card_file.read_text(encoding="utf-8", errors="replace")
            if lint._is_active(text):
                active.append(card_file.stem)
        info.append(
            "no Card-Id trailer in this range: authorization is undetermined, "
            "so nothing is reported as a violation. Active cards seen: "
            + (", ".join(active) if active else "none")
        )
    for card_id in unknown:
        info.append(f"declared card {card_id} has no file under {card_dir}")
    for card_id in inactive:
        info.append(f"declared card {card_id} is not active (CLOSED/GATED); claims ignored")

    return {
        "schema": "owned-files-dryrun/v1",
        "merge_base": resolved_base,
        "base_note": base_note,
        "authorized_card_ids": sorted(claims),
        "unknown_card_ids": unknown,
        "inactive_card_ids": inactive,
        "violations": violations,
        "whitelist_invalid": whitelist_invalid,
        "whitelist_missing": whitelist_missing,
        "info": info,
        "metrics": {
            "changed_paths": len(seen),
            "violations": len(violations),
            "whitelist_hits": whitelist_hits,
            "commits_total": commits_total,
            "commits_with_trailer": commits_with_trailer,
            "trailer_measured": trailer_measured,
        },
    }


def render_warn(payload):
    """Human-readable digest for a terminal or a pre-commit hint."""
    lines = []
    if payload.get("error"):
        lines.append(f"owned-files: report error: {payload['error']}")
    measured = payload["metrics"].get("trailer_measured", False)
    trailer_repr = (
        "{}/{}".format(payload["metrics"].get("commits_with_trailer", 0),
                       payload["metrics"].get("commits_total", 0))
        if measured else "NOT MEASURED"
    )
    lines.append(
        "owned-files (dry-run, never blocks): base={base} cards={cards} "
        "changed={changed} violations={violations} whitelist_hits={hits} "
        "trailer={trailer}".format(
            base=payload.get("merge_base"),
            cards=",".join(payload.get("authorized_card_ids") or []) or "-",
            changed=payload["metrics"]["changed_paths"],
            violations=payload["metrics"]["violations"],
            hits=payload["metrics"]["whitelist_hits"],
            trailer=trailer_repr,
        )
    )
    for item in payload.get("info", []):
        lines.append(f"  info: {item}")
    for entry in payload.get("whitelist_invalid", []):
        lines.append(f"  WHITELIST_INVALID: {entry!r} (globs and directory claims are refused)")
    for violation in payload.get("violations", []):
        lines.append(
            f"  VIOLATION: {violation['path']} ({violation['status']}) — no declared card owns it"
        )
    return "\n".join(lines)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Report commits that touched files no declared card owns (shadow period)."
    )
    parser.add_argument("--card-dir", default=str(DEFAULT_CARD_DIR),
                        help="directory holding card markdown files (default: <repo>/.tasks)")
    parser.add_argument("--repo", default=str(REPO_ROOT),
                        help="git repository to inspect (default: this file's repository)")
    parser.add_argument("--base", default="auto",
                        help="diff base; 'auto' uses merge-base against the remote default "
                             "branch (default: auto)")
    parser.add_argument("--head", default="HEAD", help="git revision to compare (default: HEAD)")
    parser.add_argument("--whitelist", default=str(DEFAULT_WHITELIST),
                        help="exact-path exception list (default: policy/owned-files-whitelist.yml)")
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    parser.add_argument("--warn", action="store_true",
                        help="emit a human-readable digest (default output when neither flag is given)")
    return parser


def main(argv=None):
    _safe_utf8()
    args = build_parser().parse_args(argv)
    payload = evaluate(
        Path(args.repo),
        Path(args.card_dir),
        args.base,
        args.head,
        Path(args.whitelist),
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_warn(payload))
    # Shadow period: the exit code is a constant, not a verdict. See decision 2.
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())