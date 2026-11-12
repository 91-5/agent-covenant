#!/usr/bin/env python3
"""Round-11 artifact-pointer verifier (card XJ-20261111-002, D6 / V12).

Section 18 D18-G clause 8 makes a report conclusion *invalid* unless every
conclusion carries an artifact pointer of the form

    [artifact: <relative/path> sha256=<64 lowercase hex>]

and the acceptance rule is "100% hit (number of conclusions without a pointer
== 0)".  A pointer that merely exists is not enough: this tool also recomputes
each referenced file's SHA-256 and rejects a stale or invented digest.  That
matters here because most of the round-11 evidence lives in ``out/`` (git
ignored, custody only), so a typo would be invisible to git.

Verification is read-only.  Python 3.9 compatible (CI): no PEP 604 unions, no
newline kwarg on the Path text writer, ``open(..., newline="")`` for writes.
Only the standard library is used.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]

POINTER_RE = re.compile(
    r"\[artifact:\s*([^\s\]]+)\s+sha256=([0-9a-fA-F]{64})\]")
CONCLUSION_RE = re.compile(r"^\s*-\s+\*\*结论\s+([A-Za-z0-9._-]+)\*\*")
HEADING_RE = re.compile(r"^\s*#{1,6}\s")

# A pointer that is syntactically present but points at nothing / has a bad
# digest is worse than a missing one: it looks verified. Count it separately.
BAD_POINTER_RE = re.compile(r"\[artifact:[^\]]*\]")


def _sha256_file(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with open(str(path), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _conclusion_blocks(lines: List[str]) -> List[Tuple[str, str]]:
    """Return (conclusion_id, full_block_text) for every conclusion bullet.

    A block runs from its ``- **结论 X**：`` line up to the next conclusion
    bullet or the next markdown heading, so a pointer placed on a wrapped
    continuation line still counts.
    """
    starts = [(i, m.group(1))
              for i, line in enumerate(lines)
              for m in [CONCLUSION_RE.match(line)] if m]
    blocks: List[Tuple[str, str]] = []
    for n, (start, cid) in enumerate(starts):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
        for j in range(start + 1, end):
            if HEADING_RE.match(lines[j]):
                end = j
                break
        blocks.append((cid, "\n".join(lines[start:end])))
    return blocks


def verify(report: Path, root: Path, verbose: bool = True) -> Dict[str, Any]:
    text = report.read_text(encoding="utf-8")
    lines = text.splitlines()
    blocks = _conclusion_blocks(lines)

    missing: List[str] = []
    bad_digest: List[Dict[str, str]] = []
    malformed: List[Dict[str, str]] = []
    checked_ptr = 0
    unique_paths: Dict[str, str] = {}

    for cid, block in blocks:
        hits = POINTER_RE.findall(block)
        if not hits:
            missing.append(cid)
            continue
        for rel, claimed in hits:
            checked_ptr += 1
            target = root / rel
            real = _sha256_file(target)
            unique_paths[rel] = claimed
            if real is None:
                bad_digest.append({"conclusion": cid, "path": rel,
                                   "reason": "file_missing"})
            elif real != claimed.lower():
                bad_digest.append({"conclusion": cid, "path": rel,
                                   "reason": "sha256_mismatch",
                                   "claimed": claimed.lower()[:16],
                                   "actual": real[:16]})
        for raw in BAD_POINTER_RE.findall(block):
            if not POINTER_RE.fullmatch(raw):
                malformed.append({"conclusion": cid, "raw": raw[:120]})

    # Also validate every pointer anywhere in the document, including prose
    # and tables, not just inside conclusion blocks.
    all_hits = POINTER_RE.findall(text)
    for rel, claimed in all_hits:
        target = root / rel
        real = _sha256_file(target)
        if real is None or real != claimed.lower():
            if not any(b["path"] == rel for b in bad_digest):
                bad_digest.append({"conclusion": "(outside conclusion block)",
                                   "path": rel,
                                   "reason": ("file_missing" if real is None
                                              else "sha256_mismatch"),
                                   "claimed": claimed.lower()[:16],
                                   "actual": (real or "")[:16]})

    n = len(blocks)
    covered = n - len(missing)
    pct = (100.0 * covered / n) if n else 100.0
    ok = (n > 0 and not missing and not bad_digest and not malformed
          and len(all_hits) > 0)

    if verbose:
        print("REPORT {}".format(report.as_posix()))
        print("CONCLUSIONS {} | WITH_VALID_POINTER {} | MISSING {} | COVERAGE {:.1f}%".format(
            n, covered, len(missing), pct))
        print("POINTERS_TOTAL {} | UNIQUE_PATHS {} | BAD_DIGEST {} | MALFORMED {}".format(
            len(all_hits), len(unique_paths), len(bad_digest), len(malformed)))
        for cid in missing:
            print("  MISSING_POINTER conclusion={}".format(cid))
        for b in bad_digest[:20]:
            print("  BAD_POINTER {} {} {}".format(b["conclusion"], b["path"],
                                                  b["reason"]))
        for m in malformed[:20]:
            print("  MALFORMED_POINTER {} {}".format(m["conclusion"], m["raw"]))
        print("RESULT {}".format("PASS" if ok else "FAIL"))
    return {
        "report": report.as_posix(),
        "conclusions": n,
        "covered": covered,
        "missing": missing,
        "coverage_pct": pct,
        "pointers_total": len(all_hits),
        "bad_digest": bad_digest,
        "malformed": malformed,
        "pass": ok,
    }


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", default="docs/eval-report-v11.md",
                    help="markdown report to verify (relative to repo root)")
    ap.add_argument("--root", default=str(REPO_ROOT),
                    help="root that artifact pointers are resolved against")
    ap.add_argument("--json-out", dest="json_out",
                    help="optional JSON result path")
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root)
    report = Path(args.report)
    if not report.is_absolute():
        report = root / report
    if not report.is_file():
        print("verify_artifact_pointers: report not found: {}".format(report),
              file=sys.stderr)
        return 2
    result = verify(report, root)
    if args.json_out:
        import json
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(str(out), "w", encoding="utf-8", newline="") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
