"""Run-directory sealing: a hash manifest that makes post-hoc edits detectable.

Card XJ-20261024-004 (advisory F2 from XJ-20261024-003). The second round's
core claim is "arm B executed nothing", and that claim is only as strong as
the run evidence it cites: if run-log.json can be edited after the fact, the
claim has no floor. This tool does NOT decide whose log is true -- it makes
"was the evidence surface touched after sealing" answerable.

The boundary, stated as narrowly as it actually holds (EVO-20261024-001
wording discipline applies to every sentence about this tool):

* What it claims: **tamper-EVIDENT** (可检出改动). Any byte added, removed or
  altered under the run directory after ``seal`` was taken is reported by
  ``--verify`` with the exact file.
* What it does NOT claim: **tamper-PROOF** (防篡改). There is no signature and
  no secret: whoever can write the directory can also rewrite seal.json with
  recomputed hashes, and the edit becomes invisible. Three concrete holes,
  named rather than hidden:
    1. In-place seal rewriting -- detectable only if seal.json outlives write
       access to the directory. Mitigation is procedural, not cryptographic:
       hand seal.json to custody (sir) separately, or use ``--move-to`` so a
       copy plus its seal lands where the executor cannot write.
    2. Whole-directory replacement -- a substituted directory with an
       internally consistent seal verifies clean. A hash manifest attests
       constancy, not origin; the chain of custody, not the hash, is what
       binds the directory to the run that produced it.
    3. Truthfulness of the sealed content -- a sealed lie is still a lie.
       Sealing happens at end of run; what the runner recorded before sealing
       is governed by protocol (draft-first pollution boundary, arm-B zero
       execution), not by this tool.
* Hashes are streaming (1 MiB chunks): file size is bounded by disk, not RAM.
* Pure stdlib, Py3.9 compatible. No subprocess is spawned anywhere in this
  tool, so the cross-locale text-decoding defect class (F1) has no surface
  here at all.

Usage::

    python tools/eval/seal_run.py RUN_DIR [--label LABEL] [--move-to DIR]
    python tools/eval/seal_run.py --verify RUN_DIR

Exit codes: 0 = sealed / verified clean; 1 = drift detected (verify) or an
operational failure (seal); 2 = usage error (bad arguments, missing
run-data.json, missing or unreadable seal.json).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SEAL_VERSION = 1
SEAL_FILENAME = "seal.json"
RUN_DATA_FILENAME = "run-data.json"
ALGORITHM = "sha256"

#: 1 MiB. Hashing reads this much at a time so a multi-gigabyte run directory
#: never lives in memory; the chunk size is not part of the seal format.
CHUNK_SIZE = 1024 * 1024

BOUNDARY_NOTE = (
    "tamper-evident, not tamper-proof: detects post-seal modification of the "
    "hashed files; seal.json itself carries no signature and must be kept "
    "where the run executor cannot rewrite it (custody). See "
    "docs/eval-runner-protocol.md section 11."
)

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2


def _safe_utf8() -> None:
    """Windows consoles default to a legacy codepage; never let output crash."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def hash_file(path: Path) -> Tuple[str, int]:
    """Stream a file through the hash in chunks; return (hexdigest, size)."""
    digest = hashlib.new(ALGORITHM)
    size = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def list_files(run_dir: Path) -> List[Path]:
    """Every file under run_dir, recursively, sorted.

    Only the top-level seal.json is excluded (the manifest cannot hash
    itself); a seal.json nested deeper is ordinary evidence and stays in."""
    files: List[Path] = []
    for path in run_dir.rglob("*"):
        if path.is_file() and path.relative_to(run_dir).as_posix() != SEAL_FILENAME:
            files.append(path)
    return sorted(files, key=lambda p: p.relative_to(run_dir).as_posix())


def build_manifest(run_dir: Path, root_label: str) -> Dict[str, object]:
    """Hash the run directory into the seal manifest (dict, not yet written).

    Relative paths are stored posix-style so a custody copy on another
    platform (or an archive) still verifies against the same seal."""
    entries: Dict[str, Dict[str, object]] = {}
    for path in list_files(run_dir):
        rel = path.relative_to(run_dir).as_posix()
        digest, size = hash_file(path)
        entries[rel] = {ALGORITHM: digest, "bytes": size}
    return {
        "seal_version": SEAL_VERSION,
        "sealed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "root_label": root_label,
        "file_count": len(entries),
        "boundary": BOUNDARY_NOTE,
        "files": entries,
    }


def seal(run_dir: Path, root_label: str) -> Path:
    """Write seal.json into run_dir. Requires the runner's run-data.json so a
    random directory cannot be sealed by accident; returns the seal path."""
    if not run_dir.is_dir():
        raise NotADirectoryError(f"not a directory: {run_dir}")
    if not (run_dir / RUN_DATA_FILENAME).is_file():
        raise ValueError(
            f"refusing to seal {run_dir}: {RUN_DATA_FILENAME} missing "
            f"(seal targets a run directory produced by study_runner)"
        )
    manifest = build_manifest(run_dir, root_label)
    seal_path = run_dir / SEAL_FILENAME
    seal_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return seal_path


def copy_to_custody(run_dir: Path, custody_dir: Path) -> Path:
    """Copy the sealed run directory into custody (never move: the executor's
    original must stay exactly where sealing found it). Refuses to overwrite
    -- custody is append-only."""
    target = custody_dir / run_dir.name
    if target.exists():
        raise FileExistsError(f"custody target already exists: {target}")
    custody_dir.mkdir(parents=True, exist_ok=True)
    return shutil.copytree(run_dir, target)


def verify(run_dir: Path) -> Tuple[bool, List[str]]:
    """Recompute every hash against the seal; return (clean, findings).

    Findings are one human-readable line each, prefixed MODIFIED / MISSING /
    ADDED. A run directory without a readable seal is a usage error (raised),
    not a drift report: with no seal there is nothing to verify against."""
    seal_path = run_dir / SEAL_FILENAME
    if not seal_path.is_file():
        raise ValueError(f"no {SEAL_FILENAME} in {run_dir}: nothing to verify against")
    try:
        manifest = json.loads(seal_path.read_text(encoding="utf-8"))
        sealed_files: Dict[str, Dict[str, object]] = manifest["files"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError(f"unreadable {SEAL_FILENAME} in {run_dir}: {exc}") from exc

    findings: List[str] = []
    actual_rel = {p.relative_to(run_dir).as_posix() for p in list_files(run_dir)}

    for rel in sorted(sealed_files):
        path = run_dir / rel
        expected = sealed_files[rel]
        if not path.is_file():
            findings.append(f"MISSING  {rel}")
            continue
        digest, size = hash_file(path)
        if digest != expected.get(ALGORITHM) or size != expected.get("bytes"):
            findings.append(f"MODIFIED  {rel}")
    for rel in sorted(actual_rel - set(sealed_files)):
        findings.append(f"ADDED  {rel}")

    return (not findings), findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Seal a study run directory with a SHA-256 manifest, or verify it "
            "later. Tamper-evident, NOT tamper-proof (no signature; keep "
            "seal.json in custody)."
        ),
    )
    parser.add_argument("run_dir", metavar="RUN_DIR", nargs="?",
                        help="run directory to seal (must contain run-data.json)")
    parser.add_argument("--verify", metavar="RUN_DIR", dest="verify_dir",
                        help="recompute all hashes in RUN_DIR against its seal.json")
    parser.add_argument("--label", metavar="LABEL", default=None,
                        help="root_label recorded in the seal (default: directory name)")
    parser.add_argument("--move-to", metavar="DIR", dest="move_to", default=None,
                        help="after sealing, copy the sealed run dir into custody "
                             "DIR (copy, never move; refuses to overwrite)")
    return parser


def cmd_seal(run_dir: Path, label: Optional[str], move_to: Optional[str]) -> int:
    root_label = label if label is not None else run_dir.name
    try:
        seal_path = seal(run_dir, root_label)
    except (NotADirectoryError, ValueError) as exc:
        print(f"[ERROR] seal refused: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except OSError as exc:
        print(f"[ERROR] seal failed: {exc}", file=sys.stderr)
        return EXIT_FAIL

    manifest = json.loads(seal_path.read_text(encoding="utf-8"))
    print(f"seal: {seal_path}")
    print(f"root_label: {manifest['root_label']}")
    print(f"files: {manifest['file_count']}")
    print("boundary: tamper-evident, not tamper-proof -- keep seal.json in custody")

    if move_to is not None:
        try:
            target = copy_to_custody(run_dir, Path(move_to))
        except FileExistsError as exc:
            print(f"[ERROR] custody copy refused: {exc}", file=sys.stderr)
            return EXIT_FAIL
        except OSError as exc:
            print(f"[ERROR] custody copy failed: {exc}", file=sys.stderr)
            return EXIT_FAIL
        clean, findings = verify(target)
        if not clean:
            print(f"[ERROR] custody copy does not match the seal:", file=sys.stderr)
            for line in findings:
                print(f"  {line}", file=sys.stderr)
            return EXIT_FAIL
        print(f"custody: {target} (copy verified against the seal)")
    return EXIT_OK


def cmd_verify(run_dir: Path) -> int:
    try:
        clean, findings = verify(run_dir)
    except (NotADirectoryError, ValueError) as exc:
        print(f"[ERROR] verify refused: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except OSError as exc:
        print(f"[ERROR] verify failed: {exc}", file=sys.stderr)
        return EXIT_FAIL

    if findings:
        for line in findings:
            print(line)
        print(f"VERIFY: DRIFT ({len(findings)} finding(s))")
        return EXIT_FAIL
    count = len(list_files(run_dir))
    print(f"VERIFY: OK ({count} files match the seal)")
    return EXIT_OK


def main(argv: Optional[List[str]] = None) -> int:
    _safe_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.verify_dir and args.run_dir:
        parser.error("--verify and a positional RUN_DIR are mutually exclusive")
    if args.verify_dir:
        return cmd_verify(Path(args.verify_dir))
    if args.run_dir:
        if args.move_to is not None and Path(args.move_to).exists() and \
                not Path(args.move_to).is_dir():
            parser.error(f"--move-to target is not a directory: {args.move_to}")
        return cmd_seal(Path(args.run_dir), args.label, args.move_to)
    parser.print_help()
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
