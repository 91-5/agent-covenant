#!/usr/bin/env python3
"""v1.6 diagnostic self-report emitter (§13 ⑧; card XJ-20261108-002 D2).

 ROLE (frozen in §13 ⑧)
 ----------------------
 This tool serves the DIAGNOSTIC APPENDIX track only: the same executor that
 ran the main track re-emits structured assertion records for the already
 sealed claims, in an isolated pass, with every output marked
 ``diagnostic_only: true``. Its products NEVER enter the 95% agreement gate,
 are never merged with the primary third-track compiler results, and never
 touch the main track (read-only on sealed claims; zero re-judging).

 MECHANICS
 ---------
 For each main-track claim the emitter derives a record mechanically from the
 claim's own evidence line (traceability by construction):

 * claim_id            = "<product-code>-c<index:02d>"
 * claim_type          = command_output when the evidence carries a command,
                         fact_existence when it carries a ref
 * verification_command= the evidence cmd verbatim; B-arm records carry the
                         §13 ⑨ frozen prefix ``B-ARM-NOT-EXECUTED::``
 * evidence_span       = [source_line, source_line + 1)
 * predicate           = exit_equals when only an exit is claimed,
                         contains when an out snippet is claimed
 * expected            = the claimed exit code / out snippet

 Because the derivation is mechanical, the emitter adds no judgment and no
 natural-language understanding — it is the diagnostic track's record writer,
 and the heuristic predicate choice is disclosed here rather than hidden.

 CLI
 ---
    python tools/eval/dsl_emit.py --claims FILE [--arm B] [--out FILE]

 ``--claims`` holds ``{code: [claim dicts]}`` (extract_claims().to_dict()
 snapshot). ``--arm B`` prepends the §13 ⑨ prefix to every verification
 command. Output: JSONL, first line = ``{"_meta": {...diagnostic_only: true}}``,
 then one record per line.

 Exit codes: 0 = ok; 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from schema import validate_dsl_record  # noqa: E402

#: §13 ⑨ frozen B-arm mechanical marker (fixed-prefix convention).
B_ARM_PREFIX = "B-ARM-NOT-EXECUTED::"

DIAGNOSTIC_ONLY = True


def emit_record(code: str, index: int, claim: dict, arm: str) -> dict:
    """Mechanically derive one structured record from a main-track claim."""
    evidence = claim.get("evidence") or {}
    command = evidence.get("command")
    ref = evidence.get("ref")
    out = evidence.get("out")
    exit_code = evidence.get("exit_code")
    line = int(claim.get("source_line", 0))

    verification = command
    if arm == "B" and verification:
        verification = B_ARM_PREFIX + verification
    if command:
        claim_type = "command_output"
        if out is not None:
            predicate, expected = "contains", out
        elif exit_code is not None:
            predicate, expected = "exit_equals", exit_code
        else:
            predicate, expected = None, None
    elif ref:
        claim_type, predicate, expected = "fact_existence", "exists", "ref"
        verification = None
    else:
        claim_type, predicate, expected = "command_output", None, None
        verification = command
    if arm == "B" and predicate == "exit_equals" and not command and ref:
        # ref-form claim on the B arm: existence criterion, no command to mark
        verification = None

    record = {
        "claim_id": f"{code}-c{index:02d}",
        "claim_type": claim_type,
        "statement": claim.get("text", ""),
        "verification_command": verification,
        "artifact_path": ref,
        "evidence_span": [line, line + 1],
        "predicate": predicate,
        "expected": expected,
    }
    return record


def emit(claims_by_code: Dict[str, List[dict]], arm: str) -> Dict[str, object]:
    """Emit the diagnostic JSONL payload (as a Python object; the CLI writes
    it line-by-line). Every record is schema-validated; invalid records are
    kept with their errors (诊断留痕, 现行纪律)."""
    lines: List[str] = [json.dumps({
        "_meta": {
            "diagnostic_only": DIAGNOSTIC_ONLY,
            "track": "self-report diagnostic appendix (§13 ⑧)",
            "arm": arm,
            "note": "never enters the 95% gate; never merged with the primary track",
        }
    }, ensure_ascii=False)]
    invalid = 0
    total = 0
    for code in sorted(claims_by_code):
        for index, claim in enumerate(claims_by_code[code]):
            record = emit_record(code, index, claim, arm)
            errors = validate_dsl_record(record)
            total += 1
            if errors:
                invalid += 1
                record["schema_errors"] = errors
            lines.append(json.dumps(record, ensure_ascii=False))
    return {"lines": lines, "record_count": total, "invalid_count": invalid}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="v1.6 diagnostic self-report emitter (§13 ⑧)")
    ap.add_argument("--claims", metavar="FILE",
                    help="JSON {code: [claim dicts]} — main-track claims snapshot")
    ap.add_argument("--arm", choices=("A", "B"), default="A")
    ap.add_argument("--out", metavar="FILE", help="output JSONL path")
    args = ap.parse_args(argv)

    if not args.claims:
        ap.print_help()
        return 2
    claims_by_code = json.loads(Path(args.claims).read_text(encoding="utf-8"))
    result = emit(claims_by_code, args.arm)
    if args.out:
        Path(args.out).write_text("\n".join(result["lines"]) + "\n",
                                  encoding="utf-8")
        print(f"emitted {result['record_count']} diagnostic records "
              f"(invalid {result['invalid_count']}) -> {args.out} "
              f"[diagnostic_only=true]")
    else:
        print("\n".join(result["lines"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
