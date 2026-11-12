#!/usr/bin/env python3
"""D1/D3: rubric v4 explicit-class decomposition (card XJ-20261112-002).

Section 20 clause 4 freezes the rubric-v4 class whitelist BEFORE any round-13
data. This module is the standalone deliverable named in the card's Owned
files. It does not re-decide anything: it runs ``independent_judge`` rubric v4
once over the 400 frozen round-11 blind samples and writes a ROW-BY-ROW
decomposition against the sealed round-11 v2 blind output.

What it mechanically proves (all checks are printed, none asserted by hand):

  * ``no_evidence`` (30) -> NO_EVIDENCE_LINE only;
    ``incomplete`` (30)  -> STRUCTURALLY_UNJUDGEABLE only;
    ``ref_missing`` (48) -> VERIFIABLE_ABSENCE only, supports=None,
    error_class still FILE_NOT_FOUND, upgrade_candidate=True recorded;
    ``repro_fail`` (48)  -> SILENT_FALLBACK_PROTECTED only, supports=None.
  * no v4 class outside the frozen whitelist (new_unobservable_classes == 0);
  * protected_total (SILENT_FALLBACK 48 + FILE_NOT_FOUND 48) == 96, unchanged;
  * raw denominator is 400, never reduced;
  * every boolean -> abstain movement is attributed, row by row, to the
    clause-3 anchor-rule alignment (legacy anchor set != aligned anchor set),
    NOT to a newly invented unobservable class. Any unattributed row is a
    real residual and is reported rather than hidden.
  * the frozen constants mirror those in ``r13_alignment.py`` exactly.

The sealed round-11 v2 blind file is READ ONLY. The main track is never
invoked and no red-zone file is written. Python 3.9 compatible; all JSON
writes use ``open(..., newline="")``.
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
RAW_DENOMINATOR = 400
PROTECTED_TOTAL_FROZEN = 96
ANCHOR_MISMATCH_BEFORE = 56

# Mirrors section 20 D20-D / clause 4, and MUST equal the constants used by
# r13_alignment.py (checked at runtime below so the two cannot drift).
V4_CLASS_WHITELIST = frozenset(
    ("SUPPORT", "NOT_SUPPORT", "INSUFFICIENT", "OBSERVATION_ERROR",
     "STRUCTURALLY_UNJUDGEABLE", "NO_EVIDENCE_LINE", "VERIFIABLE_ABSENCE",
     "SILENT_FALLBACK_PROTECTED", "INSUFFICIENT_NO_ANCHOR",
     "STRUCTURAL_NO_EVIDENCE_EXPLICIT"))
V4_NEW_EXPLICIT_CLASSES = frozenset(("NO_EVIDENCE_LINE", "VERIFIABLE_ABSENCE"))
EXPECTED_CLASS_BY_LAYER = {
    "no_evidence": "NO_EVIDENCE_LINE",
    "incomplete": "STRUCTURALLY_UNJUDGEABLE",
    "ref_missing": "VERIFIABLE_ABSENCE",
    "repro_fail": "SILENT_FALLBACK_PROTECTED",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with open(str(path), "w", newline="", encoding="utf-8") as fh:
        fh.write(text)


def materialise(case: Dict[str, Any], base: Path) -> Path:
    """Same fixture layout as rubric_v3.materialise (round-12 precedent)."""
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


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else REPO_ROOT / p


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--samples", default="out/r11-blind-samples.json")
    ap.add_argument("--v2-blind", dest="v2_blind",
                    default="out/r11-independent-blind.json")
    ap.add_argument("--out", default="out/r13-rubric-v4-decomposition.json")
    ap.add_argument("--custody", default="")
    args = ap.parse_args(argv)

    samples_path = _resolve(args.samples)
    v2_path = _resolve(args.v2_blind)
    doc = json.loads(samples_path.read_bytes().decode("utf-8"))
    cases: List[Dict[str, Any]] = doc["cases"]
    sealed: List[Dict[str, Any]] = json.loads(
        v2_path.read_bytes().decode("utf-8"))["results"]
    if (len(cases) != RAW_DENOMINATOR or doc.get("seed") != SEED
            or len(sealed) != RAW_DENOMINATOR):
        print("BAD_INPUT", len(cases), doc.get("seed"), len(sealed))
        return 2
    if [c["case_id"] for c in cases] != [r["case_id"] for r in sealed]:
        print("BAD_INPUT: sample/sealed id order mismatch")
        return 2

    # Frozen-constant consistency with the V4/V6 acceptance script.
    import r13_alignment as ra  # noqa: WPS433  (deliberately late: local check)
    constants_match = (
        set(V4_CLASS_WHITELIST) == set(ra.V4_CLASS_WHITELIST)
        and set(V4_NEW_EXPLICIT_CLASSES) == set(ra.V4_NEW_EXPLICIT_CLASSES)
        and PROTECTED_TOTAL_FROZEN == ra.PROTECTED_TOTAL_FROZEN)

    by_layer: Dict[str, Counter] = {}
    classes_seen: Counter = Counter()
    error_classes: Counter = Counter()
    trace: List[Dict[str, Any]] = []
    bool_to_abstain: List[Dict[str, Any]] = []
    layer_mismatch: List[Dict[str, Any]] = []
    protected_rows: List[Dict[str, Any]] = []
    upgrade_candidates = 0

    with tempfile.TemporaryDirectory(prefix="r13-rubric-v4-") as tmp:
        base = Path(tmp)
        for i, (case, old) in enumerate(zip(cases, sealed)):
            ws = materialise(case, base / ("c%03d" % i))
            new = ij.judge_case(case, ws, "v4")
            layer = str(case.get("layer"))
            cls = str(new.get("v4_class"))
            ec = str(new.get("error_class", ""))
            by_layer.setdefault(layer, Counter())[cls] += 1
            classes_seen[cls] += 1
            error_classes[ec] += 1

            expected = EXPECTED_CLASS_BY_LAYER.get(layer)
            if expected and cls != expected:
                layer_mismatch.append({"case_id": case["case_id"],
                                       "layer": layer, "expected": expected,
                                       "observed": cls})
            if ec in ("SILENT_FALLBACK", "FILE_NOT_FOUND"):
                protected_rows.append({"case_id": case["case_id"],
                                       "layer": layer, "error_class": ec,
                                       "supports": new.get("supports")})
            if new.get("upgrade_candidate"):
                upgrade_candidates += 1

            if str(new.get("level")) != str(old.get("level")) or ec != str(
                    old.get("error_class", "")):
                trace.append({
                    "case_id": case["case_id"], "layer": layer,
                    "v2_level": old.get("level"),
                    "v2_error_class": old.get("error_class", ""),
                    "v4_level": new.get("level"), "v4_class": cls,
                    "v4_error_class": ec,
                    "v2_supports": old.get("supports"),
                    "v4_supports": new.get("supports"),
                    "abstention_basis": new.get("abstention_basis", ""),
                })

            if (isinstance(old.get("supports"), bool)
                    and not isinstance(new.get("supports"), bool)):
                spec = ij._parse_case(case)
                claim_text = spec["claim_text"]
                legacy = ij._anchors_legacy(claim_text)
                aligned = ij._anchors(claim_text)
                bool_to_abstain.append({
                    "case_id": case["case_id"], "layer": layer,
                    "v2_supports": old.get("supports"),
                    "v4_level": new.get("level"), "v4_class": cls,
                    "legacy_anchors": legacy, "aligned_anchors": aligned,
                    "anchor_set_differs": set(legacy) != set(aligned),
                    "attribution": ("anchor_rule_diff (section 20 clause 3)"
                                    if set(legacy) != set(aligned)
                                    else "UNATTRIBUTED_RESIDUAL"),
                })

    new_unobservable = sorted(set(classes_seen) - V4_CLASS_WHITELIST)
    protected_total = (error_classes.get("SILENT_FALLBACK", 0)
                       + error_classes.get("FILE_NOT_FOUND", 0))
    unattributed = [r for r in bool_to_abstain
                    if not r["anchor_set_differs"]]
    layer_ok = all(
        sorted(by_layer.get(layer, {})) == [expected]
        for layer, expected in EXPECTED_CLASS_BY_LAYER.items())
    all_protected_abstain = all(r["supports"] is None for r in protected_rows)

    payload = {
        "mode": "r13_rubric_v4_explicit_class_decomposition",
        "card": "XJ-20261112-002",
        "rubric": ij.RUBRIC_V4["id"],
        "inherits": ij.RUBRIC_V4["inherits"],
        "section20_clause": 4,
        "samples_path": str(args.samples),
        "samples_sha256": sha256_file(samples_path),
        "v2_blind_path": str(args.v2_blind),
        "v2_blind_sha256": sha256_file(v2_path),
        "seed": SEED,
        "raw_denominator": RAW_DENOMINATOR,
        "excluded_from_raw_denominator": 0,
        "expected_class_by_layer": EXPECTED_CLASS_BY_LAYER,
        "per_layer_classes": {k: dict(v) for k, v in sorted(by_layer.items())},
        "named_layers_all_single_explicit_class": layer_ok,
        "named_layer_mismatches": layer_mismatch,
        "v4_class_distribution": dict(classes_seen),
        "new_unobservable_classes": new_unobservable,
        "new_unobservable_class_count": len(new_unobservable),
        "frozen_class_whitelist": sorted(V4_CLASS_WHITELIST),
        "frozen_constants_match_r13_alignment": constants_match,
        "error_class_distribution": dict(error_classes),
        "protected_total": protected_total,
        "protected_total_frozen": PROTECTED_TOTAL_FROZEN,
        "protected_total_unchanged": protected_total == PROTECTED_TOTAL_FROZEN,
        "protected_rows_all_abstain": all_protected_abstain,
        "protected_rows": protected_rows,
        "ref_missing_upgrade_candidate_rows": upgrade_candidates,
        "ref_missing_activated_as_boolean": False,
        "boolean_to_abstain_total": len(bool_to_abstain),
        "boolean_to_abstain_attributed_anchor_rule": (
            len(bool_to_abstain) - len(unattributed)),
        "boolean_to_abstain_unattributed_residual": len(unattributed),
        "boolean_to_abstain_rows": bool_to_abstain,
        "reclassification_trace_rows": len(trace),
        "reclassification_trace": trace,
        "label_mapping_note": (
            "every v4 level normalises through label_mapping.normalise_indep "
            "into one of the 5 frozen classes; protected abstentions never "
            "become equivalent/conflict (card 禁令 2)"),
        "capability_gain_claim": False,
        "caliber": "instrument_alignment_calibration_only",
        "gate_result": "not_evaluable",
        "gate_conclusion_issued": False,
        "pass": bool(
            layer_ok and not new_unobservable and constants_match
            and protected_total == PROTECTED_TOTAL_FROZEN
            and all_protected_abstain and not unattributed
            and upgrade_candidates == 48),
    }
    # normalised distribution needs the v4 rows; collect from the trace is not
    # exhaustive, so recompute the mapping from the per-layer class counters.
    norm: Counter = Counter()
    for layer, counter in by_layer.items():
        for cls, n in counter.items():
            if cls in ("SUPPORT", "NOT_SUPPORT"):
                norm[cls] += n
            elif cls in ("INSUFFICIENT", "INSUFFICIENT_NO_ANCHOR"):
                norm["INSUFFICIENT"] += n
            elif cls in ("OBSERVATION_ERROR", "SILENT_FALLBACK_PROTECTED"):
                norm["OBSERVATION_ERROR"] += n
            else:
                norm["STRUCTURAL"] += n
    payload["normalised_class_distribution"] = dict(norm)

    out_path = _resolve(args.out)
    write_json(out_path, payload)
    if args.custody:
        write_json(Path(args.custody), payload)

    print("RAW_DENOMINATOR", RAW_DENOMINATOR)
    for layer, expected in EXPECTED_CLASS_BY_LAYER.items():
        print("LAYER", layer, "EXPECTED", expected,
              "OBSERVED", dict(by_layer.get(layer, {})))
    print("NAMED_LAYERS_ALL_SINGLE_EXPLICIT_CLASS", layer_ok)
    print("NEW_UNOBSERVABLE_CLASS_COUNT", len(new_unobservable))
    print("PROTECTED_TOTAL", protected_total,
          "UNCHANGED", protected_total == PROTECTED_TOTAL_FROZEN)
    print("BOOLEAN_TO_ABSTAIN_TOTAL", len(bool_to_abstain),
          "ATTRIBUTED_ANCHOR_RULE", len(bool_to_abstain) - len(unattributed),
          "UNATTRIBUTED_RESIDUAL", len(unattributed))
    print("FROZEN_CONSTANTS_MATCH_R13_ALIGNMENT", constants_match)
    print("REF_MISSING_UPGRADE_CANDIDATE_ROWS", upgrade_candidates)
    print("PASS", payload["pass"])
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
