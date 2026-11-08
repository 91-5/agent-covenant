#!/usr/bin/env python3
"""v1.6 shadow-track aligner (docs/eval-prereg.md §12 D4; card XJ-20261108-001
D2).

 WHAT THIS TOOL DOES
 -------------------
 Aligns the shadow track (executor-declared structured assertion records,
 compiled by dsl_compiler) against the main track (extract.py claims judged by
 judge.py) and measures the two §12 D4 agreement rates:

 * claim 对齐率 — the share of a one-to-one bijection between structured
   records and main-track entries: aligned pairs / max(record count, main
   claim count). Unmatched records AND uncovered main claims both count
   against it, so neither side alone can inflate the rate (card review
   question 5).
 * 判级一致率 — over comparable aligned pairs, the share where the shadow's
   mechanical predicate outcome agrees with the main-track level
   (predicate_ok True <=> main E4; False <=> main E2/E3).

 ISOLATION GUARANTEES (card constraint: 影子轨隔离)
 --------------------------------------------------
 * The shadow track NEVER emits its own E0-E4 level sequence: the only
   per-pair output is a boolean (consistent / inconsistent) plus gap classes.
 * No endpoint numbers: nothing here feeds M1/M2/M3 or any report conclusion.
 * Read-only on sealed products; zero re-judging (C12) — the main-track levels
   used for comparison come from the caller-provided snapshot; this module
   never invokes judge.py's judging path.

 ALIGNMENT RULE (frozen in card D2)
 ----------------------------------
 One-to-one by line span only — a record's ``evidence_span`` [start, end)
 covers a main claim's ``source_line`` (half-open interval). A record spanning
 several main claims, a main claim covered by several records, and unmatched
 records or claims are all misalignment gaps; no text matching, no approximate
 joining (there is no natural-language understanding here either).

 GAP TRIAGE (card D2: 缺口三分类)
 --------------------------------
 * ``syntax``   — record failed §12 schema validation (never executed);
 * ``anchor``   — record valid but not aligned one-to-one (span miss, span
                  multi-match, duplicate coverage) or a main claim left
                  uncovered / lacking a comparable level (E0/E1);
 * ``semantic`` — aligned and comparable but the predicate outcome disagrees
                  with the main-track level.

 ``evaluative`` records carry no predicate by §12 D2: counted in their own
 bucket, excluded from both agreement denominators (构念外).

 CLI
 ---
    python tools/eval/shadow_align.py --main FILE --records FILE [--root DIR]
        [--out FILE] [--selftest]

 Both input files are JSON objects keyed by product code: ``{code: [...]}``
 (main = claim dicts as extract_claims().to_dict(); records = structured
 assertion records). Alignment runs per product, aggregated.

 Exit codes: 0 = ok; 1 = selftest failed or operational error; 2 = usage.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from dsl_compiler import compile_records  # noqa: E402
from schema import DSL_EVALUATIVE_TYPE  # noqa: E402

#: §12 D4 frozen gate: reported for reference; this tool reports rates and
#: never decides the gate itself (the gate is adjudicated in the pilot report).
AGREEMENT_GATE = 0.95


def _align_product(main_claims: List[dict], records: List[dict],
                   compiled: Dict[str, object]) -> Dict[str, object]:
    """One product's alignment accounting (no endpoint numbers)."""
    results = {str(r["claim_id"]): r for r in compiled["results"]}

    span_matches: Dict[str, List[dict]] = {}
    covered_by: Dict[int, List[str]] = {}
    for rec in records:
        cid = str(rec.get("claim_id"))
        span = rec.get("evidence_span") or [0, 0]
        hits = [c for c in main_claims
                if span[0] <= int(c.get("source_line", -1)) < span[1]]
        span_matches[cid] = hits
        for c in hits:
            covered_by.setdefault(id(c), []).append(cid)

    aligned: Dict[str, dict] = {}
    anchor_gaps: List[str] = []
    for cid, hits in span_matches.items():
        if len(hits) == 1:
            main = hits[0]
            if len(covered_by.get(id(main), [])) == 1:
                aligned[cid] = main
                continue
        anchor_gaps.append(cid)
    uncovered_main = [c for c in main_claims
                      if len(covered_by.get(id(c), [])) != 1]

    syntax_gaps = sorted({str(r.get("claim_id")) for r in records
                          if "schema_invalid" in results.get(
                              str(r.get("claim_id")), {}).get("flags", [])})
    comparable: Dict[str, bool] = {}
    evaluative: List[str] = []
    semantic_gaps: List[str] = []
    for cid, main in aligned.items():
        result = results.get(cid, {})
        rec = next(r for r in records if str(r.get("claim_id")) == cid)
        level = main.get("level") or main.get("_level")
        if rec.get("claim_type") == DSL_EVALUATIVE_TYPE:
            evaluative.append(cid)
            continue
        if "schema_invalid" in result.get("flags", []):
            continue  # already a syntax gap
        if level not in ("E2", "E3", "E4"):
            # main claim has no complete evidence trail (E0/E1) — the shadow
            # criterion has nothing comparable to check against
            anchor_gaps.append(cid)
            continue
        consistent = bool(result.get("predicate_ok")) == (level == "E4")
        comparable[cid] = consistent
        if not consistent:
            semantic_gaps.append(cid)

    n_records = len(records)
    n_main = len(main_claims)
    aligned_pairs = len(aligned)
    alignment_rate = (aligned_pairs / max(n_records, n_main)) if max(n_records, n_main) else 1.0
    comparable_pairs = len(comparable)
    agreement_rate = (sum(1 for v in comparable.values() if v) / comparable_pairs
                      if comparable_pairs else None)
    return {
        "record_count": n_records,
        "main_claim_count": n_main,
        "aligned_pairs": aligned_pairs,
        "alignment_rate": round(alignment_rate, 4),
        "comparable_pairs": comparable_pairs,
        "agreement_rate": (round(agreement_rate, 4) if agreement_rate is not None else None),
        "evaluative_count": len(evaluative),
        "gaps": {
            "syntax": sorted(set(syntax_gaps)),
            "anchor": sorted(set(anchor_gaps)),
            "semantic": sorted(set(semantic_gaps)),
        },
        "consistent_flags": {cid: bool(v) for cid, v in sorted(comparable.items())},
        "anchor_gap_note": (f"record-side {len(anchor_gaps)}; "
                            f"main-side uncovered {len(uncovered_main)}"),
    }


def align(main_by_code: Dict[str, List[dict]],
          records_by_code: Dict[str, List[dict]],
          root: Path, timeout: int = 30) -> Dict[str, object]:
    """Aggregate alignment over all products. The output carries no E0-E4
    sequence and no endpoint numbers — per-claim outputs are booleans and gap
    classes only (card D2 / §12 D4)."""
    per_product: Dict[str, Dict[str, object]] = {}
    totals = {"record_count": 0, "main_claim_count": 0, "aligned_pairs": 0,
              "comparable_pairs": 0, "consistent_pairs": 0}
    codes = sorted(set(main_by_code) | set(records_by_code))
    for code in codes:
        main_claims = list(main_by_code.get(code, []))
        records = list(records_by_code.get(code, []))
        if not records:
            per_product[code] = {"record_count": 0, "alignment_rate": None,
                                 "agreement_rate": None,
                                 "note": "no structured records for this product"}
            totals["main_claim_count"] += len(main_claims)
            continue
        compiled = compile_records(records, root, timeout)
        acc = _align_product(main_claims, records, compiled)
        per_product[code] = acc
        totals["record_count"] += acc["record_count"]
        totals["main_claim_count"] += acc["main_claim_count"]
        totals["aligned_pairs"] += acc["aligned_pairs"]
        totals["comparable_pairs"] += acc["comparable_pairs"]
        totals["consistent_pairs"] += sum(1 for v in acc["consistent_flags"].values() if v)

    denom_align = max(totals["record_count"], totals["main_claim_count"])
    alignment_rate = (round(totals["aligned_pairs"] / denom_align, 4)
                      if denom_align else 1.0)
    agreement_rate = (round(totals["consistent_pairs"] / totals["comparable_pairs"], 4)
                      if totals["comparable_pairs"] else None)
    return {
        "note": ("shadow-track alignment only; no E0-E4 sequence, no endpoint "
                 "numbers, no rejudge (§12 D4 / C12)"),
        "totals": {**totals,
                   "alignment_rate": alignment_rate,
                   "agreement_rate": agreement_rate,
                   "agreement_gate": AGREEMENT_GATE},
        "per_product": per_product,
    }


def _selftest() -> int:
    checks: List[Tuple[str, bool, str]] = []

    def check(name: str, cond: bool):
        checks.append((name, bool(cond), "" if cond else "selftest mismatch"))

    def main_claim(level: str, line: int, text: str = "断言") -> dict:
        return {"text": text, "source_line": line, "product": "P901",
                "evidence": {"raw": f"cmd=`x` exit=0 out=`y` ({level})"},
                "anchors": [], "unanchored": True, "_level": level}

    def rec(cid: str, start: int, end: int, ctype: str = "command_output",
            predicate: str = "exit_equals", expected=0,
            command="python -c \"pass\""):
        return {"claim_id": cid, "claim_type": ctype, "statement": "s " + cid,
                "verification_command": command, "artifact_path": None,
                "evidence_span": [start, end], "predicate": predicate,
                "expected": expected}

    # ONE workspace for the whole selftest: the probes are read-only
    # python -c commands, and the aligned-pair accounting never depends on
    # the workspace contents — only on the commands starting successfully.
    # (A per-check TemporaryDirectory deleted its dir before the next check
    # re-entered the same generated name and produced WinError 267.)
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)

        # perfect alignment + full agreement: 3 records on 3 main claims
        mains = [main_claim("E4", 10), main_claim("E4", 20), main_claim("E2", 30)]
        recs = [rec("c1", 10, 11), rec("c2", 20, 21),
                rec("c3", 30, 31, predicate="exit_equals", expected=1,
                    command="python -c \"import sys;sys.exit(3)\"")]
        r = align({"P901": mains}, {"P901": recs}, root)
        t = r["totals"]
        check("perfect-alignment-rate-1.0", t["alignment_rate"] == 1.0)
        check("perfect-agreement-rate-1.0", t["agreement_rate"] == 1.0)
        check("no-level-sequence-emitted",
              all("level" not in str(k) for k in r.keys()))

        # one-to-one violation: record spanning two claims -> anchor gap
        mains = [main_claim("E4", 10), main_claim("E4", 12)]
        recs = [rec("wide", 10, 13)]
        r = align({"P901": mains}, {"P901": recs}, root)
        check("span-multi-match-is-anchor-gap",
              "wide" in r["per_product"]["P901"]["gaps"]["anchor"]
              and r["totals"]["aligned_pairs"] == 0)

        # duplicate coverage of one main claim by two records -> anchor gap
        mains = [main_claim("E4", 10)]
        recs = [rec("d1", 10, 11), rec("d2", 10, 11)]
        r = align({"P901": mains}, {"P901": recs}, root)
        check("duplicate-coverage-is-anchor-gap",
              r["totals"]["aligned_pairs"] == 0
              and {"d1", "d2"} <= set(r["per_product"]["P901"]["gaps"]["anchor"]))

        # semantic gap: predicate_ok True against a main E2 claim
        mains = [main_claim("E2", 10)]
        recs = [rec("s1", 10, 11)]
        r = align({"P901": mains}, {"P901": recs}, root)
        check("semantic-gap-detected",
              "s1" in r["per_product"]["P901"]["gaps"]["semantic"]
              and r["per_product"]["P901"]["consistent_flags"]["s1"] is False
              and r["totals"]["agreement_rate"] == 0.0)

        # syntax gap: schema-invalid record (evaluative carrying a predicate)
        recs = [rec("bad", 10, 11, ctype="evaluative", predicate="equals",
                    expected="x")]
        r = align({"P901": [main_claim("E4", 10)]}, {"P901": recs}, root)
        check("syntax-gap-detected",
              "bad" in r["per_product"]["P901"]["gaps"]["syntax"])

        # evaluative record (valid: no predicate) — own bucket, excluded from
        # both agreement denominators
        eval_rec = {"claim_id": "ev", "claim_type": "evaluative",
                    "statement": "评价", "verification_command": None,
                    "artifact_path": None, "evidence_span": [10, 11],
                    "predicate": None, "expected": None}
        r = align({"P901": [main_claim("E2", 10)]}, {"P901": [eval_rec]}, root)
        check("evaluative-excluded-from-denominators",
              r["per_product"]["P901"]["evaluative_count"] == 1
              and r["totals"]["comparable_pairs"] == 0
              and r["totals"]["agreement_rate"] is None)

        # uncovered main claim counts against the alignment rate
        mains = [main_claim("E4", 10), main_claim("E4", 50)]
        recs = [rec("only", 10, 11)]
        r = align({"P901": mains}, {"P901": recs}, root)
        check("uncovered-main-lowers-alignment",
              r["totals"]["alignment_rate"] == 0.5)

        # the frozen gate is reported, never decided by this tool
        check("gate-reported-not-enforced", r["totals"]["agreement_gate"] == 0.95)

    failed = [name for name, ok, _ in checks if not ok]
    for name, ok, _ in checks:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {name}")
    print(f"SHADOW-ALIGN SELFTEST: {'PASS' if not failed else 'FAIL'} "
          f"({len(checks)} checks, {len(failed)} failed)")
    return 0 if not failed else 1


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="v1.6 shadow-track aligner (§12 D4)")
    ap.add_argument("--main", metavar="FILE",
                    help="JSON {code: [claim dicts]} — main-track snapshot")
    ap.add_argument("--records", metavar="FILE",
                    help="JSON {code: [structured records]} — shadow track")
    ap.add_argument("--root", default=".",
                    help="observation root for verification commands")
    ap.add_argument("--out", metavar="FILE", help="write machine-readable JSON")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()
    if not args.main or not args.records:
        ap.print_help()
        return 2
    main_by_code = json.loads(Path(args.main).read_text(encoding="utf-8"))
    records_by_code = json.loads(Path(args.records).read_text(encoding="utf-8"))
    result = align(main_by_code, records_by_code, Path(args.root))
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
        t = result["totals"]
        print(f"aligned {t['aligned_pairs']} pairs "
              f"(alignment_rate {t['alignment_rate']}, "
              f"agreement_rate {t['agreement_rate']}, "
              f"comparable {t['comparable_pairs']}) -> {args.out}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
