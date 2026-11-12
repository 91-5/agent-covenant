#!/usr/bin/env python3
"""D1: rubric v3 structural-unjudgeable decomposition (card XJ-20261112-001).

Implements §19 clause 2 exactly as frozen:

  * a structurally unjudgeable sample has a NON-EMPTY evidence line with
    cmd=None, ref=None and anchors=[] (no observation surface at all);
  * rubric v3 gives it the explicit level STRUCTURALLY_UNJUDGEABLE with
    supports=None -- still an ABSTENTION, never a boolean verdict;
  * raw denominator (all 400 frozen samples) and judgable denominator are
    ALWAYS reported side by side; no sample is dropped from the raw denominator;
  * every reclassification is traced row by row (original -> new -> basis).

Samples with an EMPTY evidence line are OUTSIDE the frozen clause-2 wording.
v3 keeps their v2 verdict verbatim rather than widening a frozen clause after
seeing the data; they are disclosed separately as out-of-scope. This is a
deliberate, reported partial closure, not a hidden exclusion.

The sealed round-11 blind output is the "original classification" baseline.
Because v3 delegates every non-structural sample to the v2 path, comparing
v3 against that sealed file mechanically proves v2 did not drift and that v3
changed ONLY the structural samples.

Python 3.9 compatible. No PEP 604 unions. JSON writes use open(..., newline="").
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = REPO_ROOT / "tools" / "eval"
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

import independent_judge as ij  # noqa: E402

SEED = 20261111
STRUCTURAL_LEVEL = ij.STRUCTURAL_LEVEL
STRUCTURAL_ERROR_CLASS = ij.STRUCTURAL_ERROR_CLASS
CLAUSE2_VERBATIM = ("evidence_raw non-empty AND cmd is None AND ref is None "
                    "AND anchors empty")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path), "w", newline="", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def materialise(case: Dict[str, Any], base: Path) -> Path:
    """Create the per-case workspace from its frozen fixtures."""
    ws = base / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    for name, content in (case.get("fixtures_workspace") or {}).items():
        p = ws / name
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(str(p), "w", newline="", encoding="utf-8") as fh:
            fh.write(content)
    for name, content in (case.get("fixtures_root") or {}).items():
        p = base / "root" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(str(p), "w", newline="", encoding="utf-8") as fh:
            fh.write(content)
    return ws


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--samples", default="out/r11-blind-samples.json")
    ap.add_argument("--v2-blind", dest="v2_blind",
                    default="out/r11-independent-blind.json")
    ap.add_argument("--out", default="out/r12-abstention-decomposition.json")
    ap.add_argument("--custody", default="")
    args = ap.parse_args(argv)

    samples_path = Path(args.samples)
    v2_path = Path(args.v2_blind)
    if not samples_path.is_absolute():
        samples_path = REPO_ROOT / samples_path
    if not v2_path.is_absolute():
        v2_path = REPO_ROOT / v2_path

    doc = json.loads(samples_path.read_bytes().decode("utf-8"))
    cases = doc["cases"]
    sealed = json.loads(v2_path.read_bytes().decode("utf-8"))["results"]
    if len(cases) != 400 or doc.get("seed") != SEED or len(sealed) != 400:
        print("BAD_INPUT", len(cases), doc.get("seed"), len(sealed))
        return 2
    if [c["case_id"] for c in cases] != [r["case_id"] for r in sealed]:
        print("BAD_INPUT: sample/sealed id order mismatch")
        return 2

    trace: List[Dict[str, Any]] = []
    out_of_scope: List[Dict[str, Any]] = []
    equivalence_mismatch: List[Dict[str, Any]] = []
    v3_levels: Counter = Counter()
    v2_levels: Counter = Counter()
    structural_ids = set()
    by_stratum: Dict[str, Dict[str, int]] = {}
    by_layer: Dict[str, Dict[str, int]] = {}
    abstain_v2 = abstain_v3 = 0
    boolean_decidable = 0

    with tempfile.TemporaryDirectory(prefix="r12-rubric-v3-") as tmp:
        base = Path(tmp)
        for i, (case, old) in enumerate(zip(cases, sealed)):
            cid = case["case_id"]
            spec = ij._parse_case(case)
            is_struct = ij.is_structurally_unjudgeable(spec)
            empty_evidence = not spec["evidence_raw"]
            if is_struct:
                structural_ids.add(cid)
            ws = materialise(case, base / ("c%03d" % i))
            new = ij.judge_case(case, ws, "v3")

            v2_levels[str(old.get("level"))] += 1
            v3_levels[str(new.get("level"))] += 1
            abstain_v2 += int(not isinstance(old.get("supports"), bool))
            abstain_v3 += int(not isinstance(new.get("supports"), bool))
            boolean_decidable += int(isinstance(new.get("supports"), bool))

            for bucket, key in ((by_stratum, str(case.get("stratum"))),
                                (by_layer, str(case.get("layer")))):
                slot = bucket.setdefault(key, {"n": 0, "structural": 0,
                                               "out_of_scope": 0,
                                               "abstain_v3": 0})
                slot["n"] += 1
                slot["structural"] += int(is_struct)
                slot["out_of_scope"] += int(empty_evidence)
                slot["abstain_v3"] += int(
                    not isinstance(new.get("supports"), bool))

            changed = (str(new.get("level")) != str(old.get("level"))
                       or str(new.get("error_class", ""))
                       != str(old.get("error_class", "")))
            if changed:
                trace.append({
                    "case_id": cid,
                    "stratum": case.get("stratum"),
                    "layer": case.get("layer"),
                    "original_level": old.get("level"),
                    "original_error_class": old.get("error_class", ""),
                    "original_supports": old.get("supports"),
                    "new_level": new.get("level"),
                    "new_error_class": new.get("error_class", ""),
                    "new_supports": new.get("supports"),
                    "basis": new.get("structural_basis", ""),
                    "evidence_raw": spec["evidence_raw"],
                    "cmd": spec["cmd"], "ref": spec["ref"],
                    "anchors": spec["anchors"],
                })
            else:
                # Non-structural samples must be byte-equivalent to the sealed
                # round-11 v2 result on every semantic field.
                same = all(
                    new.get(k) == old.get(k)
                    for k in ("level", "supports", "score", "error_class",
                              "features"))
                if not same:
                    equivalence_mismatch.append({
                        "case_id": cid,
                        "v3": {k: new.get(k) for k in
                               ("level", "supports", "score", "error_class")},
                        "sealed_v2": {k: old.get(k) for k in
                                      ("level", "supports", "score",
                                       "error_class")},
                    })

            if empty_evidence:
                out_of_scope.append({
                    "case_id": cid,
                    "stratum": case.get("stratum"),
                    "layer": case.get("layer"),
                    "v2_level": old.get("level"),
                    "v3_level": new.get("level"),
                    "v2_error_class": old.get("error_class", ""),
                    "v3_error_class": new.get("error_class", ""),
                    "supports": new.get("supports"),
                    "reason": ("empty evidence line: outside §19 clause 2 "
                               "literal definition; v2 verdict kept verbatim, "
                               "still abstaining, still in raw denominator"),
                })

    raw_denominator = len(cases)
    n_struct = len(structural_ids)
    judgable_denominator = raw_denominator - n_struct
    reclassified_total = len(trace)
    trace_rows_well_formed = all(
        all(k in row for k in ("case_id", "original_level", "new_level",
                               "basis", "original_supports", "new_supports"))
        for row in trace)
    trace_complete = bool(
        reclassified_total == n_struct
        and trace_rows_well_formed
        and not equivalence_mismatch
        and all(r["new_supports"] is None for r in trace))

    payload = {
        "mode": "r12_structural_unjudgeable_decomposition",
        "card": "XJ-20261112-001",
        "rubric": ij.RUBRIC_V3["id"],
        "inherits": ij.RUBRIC_V3["inherits"],
        "section19_clause2_verbatim": CLAUSE2_VERBATIM,
        "phase": "D1",
        "samples_path": str(args.samples),
        "samples_sha256": sha256_file(samples_path),
        "v2_blind_path": str(args.v2_blind),
        "v2_blind_sha256": sha256_file(v2_path),
        "seed": SEED,
        # ---- the two mandatory denominators, always paired ---------------
        "raw_denominator": raw_denominator,
        "judgable_denominator": judgable_denominator,
        "denominators_paired": True,
        "excluded_from_raw_denominator": 0,
        "structural_unjudgeable_count": n_struct,
        "reclassified_total": reclassified_total,
        "reclassification_trace": trace,
        "trace_complete": trace_complete,
        "trace_complete_basis": ("trace rows == independently counted structural "
                                 "samples == reclassified_total; all rows carry "
                                 "original/new/basis; v2/v3 equivalence holds "
                                 "over every non-structural sample"),
        # ---- honesty: the frozen-clause formula is NOT a capability gain ---
        "boolean_decidable_denominator": boolean_decidable,
        "boolean_decidable_note": ("judgable_denominator follows the frozen "
                                   "clause-2 formula (raw minus structural); it "
                                   "still contains other abstaining samples. The "
                                   "actually comparable set is this field."),
        "abstain_total_v2": abstain_v2,
        "abstain_total_v3": abstain_v3,
        "abstain_unchanged": abstain_v2 == abstain_v3,
        "no_boolean_laundering": all(
            r["new_supports"] is None for r in trace),
        "capability_gain_claim": False,
        "capability_note": ("rubric v3 changed CLASSIFICATION only: every "
                            "reclassified sample still abstains (supports=None), "
                            "so the abstention count and any agreement rate "
                            "computed on comparable samples cannot rise. "
                            "This is an instrument-definition repair, not a "
                            "capability improvement."),
        # ---- out-of-scope disclosure --------------------------------------
        "out_of_scope_no_evidence_line_count": len(out_of_scope),
        "out_of_scope_rows": out_of_scope,
        "out_of_scope_note": ("§19 clause 2 requires a non-empty evidence line; "
                              "these samples have none. They are NOT silently "
                              "excluded, NOT reclassified and NOT laundered. "
                              "Partial closure is reported honestly and deferred "
                              "to the next round for adjudication."),
        # ---- mechanical equivalence ---------------------------------------
        "v2_v3_equivalence_over_nonstructural": {
            "checked": raw_denominator - reclassified_total,
            "mismatches": equivalence_mismatch,
            "all_equivalent": not equivalence_mismatch,
        },
        "v2_level_distribution": dict(v2_levels),
        "v3_level_distribution": dict(v3_levels),
        "by_stratum": by_stratum,
        "by_layer": by_layer,
        "note": ("single pass over the frozen 400 samples; the sealed v2 blind "
                 "output is the original-classification baseline; no main-track "
                 "output artifact is read"),
    }
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = REPO_ROOT / out_path
    write_json(out_path, payload)
    if args.custody:
        write_json(Path(args.custody), payload)

    print("RAW_DENOMINATOR", raw_denominator)
    print("JUDGABLE_DENOMINATOR", judgable_denominator)
    print("STRUCTURAL", n_struct, "RECLASSIFIED", reclassified_total,
          "TRACE_COMPLETE", trace_complete)
    print("BOOLEAN_DECIDABLE", boolean_decidable,
          "ABSTAIN_V2", abstain_v2, "ABSTAIN_V3", abstain_v3,
          "ABSTAIN_UNCHANGED", abstain_v2 == abstain_v3)
    print("OUT_OF_SCOPE_EMPTY_EVIDENCE", len(out_of_scope))
    print("V2_V3_EQUIV_MISMATCHES", len(equivalence_mismatch))
    print("V3_LEVELS", dict(v3_levels))
    return 0 if trace_complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
