#!/usr/bin/env python3
"""D2: rubric-v3 abstention decomposition over the frozen 400 samples.

Card XJ-20261112-001, V6. This is an INSTRUMENT CALIBRATION recomputation,
NOT a gate measurement: R_main is not re-counted, no gate value is
re-derived, and gate_result stays not_evaluable (§19 clause 6 / ban 1).

Environment isolation is not decorative: this script calls the shared
env_isolation.clean_env() and MEASURES it with verify_isolation(), which
launches a real child process with host PYTHONPATH / COVENANT_* probes
injected. The measurement result is written into the output artifact.

Python 3.9 compatible. JSON writes use open(..., newline="").
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

import env_isolation  # noqa: E402  (shared D2 module, single source of truth)
import independent_judge as ij  # noqa: E402
import rubric_v3  # noqa: E402  (reuse its fixture materialiser)

SEED = 20261111


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path), "w", newline="", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--samples", default="out/r11-blind-samples.json")
    ap.add_argument("--out", default="out/r12-decomposition.json")
    ap.add_argument("--custody", default="")
    args = ap.parse_args(argv)

    samples_path = Path(args.samples)
    if not samples_path.is_absolute():
        samples_path = REPO_ROOT / samples_path
    doc = json.loads(samples_path.read_bytes().decode("utf-8"))
    cases = doc["cases"]
    if len(cases) != 400 or doc.get("seed") != SEED:
        print("BAD_SAMPLE_SET", len(cases), doc.get("seed"))
        return 2

    # ---- actually measure the shared isolation, not just import it --------
    isolation = env_isolation.verify_isolation()
    _env, env_info = env_isolation.clean_env()

    levels: Counter = Counter()
    by_stratum: Dict[str, Dict[str, Any]] = {}
    abstain_total = 0
    structural_total = 0
    out_of_scope_total = 0
    boolean_total = 0

    with tempfile.TemporaryDirectory(prefix="r12-reliability-") as tmp:
        base = Path(tmp)
        for i, case in enumerate(cases):
            spec = ij._parse_case(case)
            ws = rubric_v3.materialise(case, base / ("c%03d" % i))
            result = ij.judge_case(case, ws, "v3")
            level = str(result.get("level"))
            abstain = not isinstance(result.get("supports"), bool)
            is_struct = ij.is_structurally_unjudgeable(spec)
            empty_ev = not spec["evidence_raw"]

            levels[level] += 1
            abstain_total += int(abstain)
            boolean_total += int(not abstain)
            structural_total += int(is_struct)
            out_of_scope_total += int(empty_ev)

            st = str(case.get("stratum"))
            slot = by_stratum.setdefault(st, {
                "n": 0, "abstain": 0, "boolean_decidable": 0,
                "structural_unjudgeable": 0, "out_of_scope_empty_evidence": 0,
                "levels": Counter(),
            })
            slot["n"] += 1
            slot["abstain"] += int(abstain)
            slot["boolean_decidable"] += int(not abstain)
            slot["structural_unjudgeable"] += int(is_struct)
            slot["out_of_scope_empty_evidence"] += int(empty_ev)
            slot["levels"][level] += 1

    for slot in by_stratum.values():
        slot["abstain_rate"] = (round(slot["abstain"] / slot["n"], 6)
                                if slot["n"] else None)
        slot["levels"] = dict(slot["levels"])

    raw_denominator = len(cases)
    judgable_denominator = raw_denominator - structural_total
    payload = {
        "mode": "r12_instrument_calibration_decomposition",
        "card": "XJ-20261112-001",
        "phase": "D2 / card D3 (V6)",
        "rubric": ij.RUBRIC_V3["id"],
        "seed": SEED,
        "samples_path": str(args.samples),
        "samples_sha256": sha256_file(samples_path),
        # ---- explicit NON-gate caliber -----------------------------------
        "caliber": "instrument_calibration_only",
        "not_gate_conclusion": True,
        "gate_result": "not_evaluable",
        "gate_conclusion_issued": False,
        "r_main_recomputed": False,
        "gate_value_recomputed": False,
        "caliber_note": ("§19 clause 6 / ban 1: R_main is NOT re-counted and "
                         "no gate value is re-derived. These numbers are "
                         "abstention decomposition for instrument calibration "
                         "only and must never be quoted as a gate result."),
        # ---- paired denominators -----------------------------------------
        "raw_denominator": raw_denominator,
        "judgable_denominator": judgable_denominator,
        "denominators_paired": True,
        "excluded_from_raw_denominator": 0,
        "boolean_decidable_denominator": boolean_total,
        "structural_unjudgeable_count": structural_total,
        "out_of_scope_empty_evidence_count": out_of_scope_total,
        # ---- the V6 readings ---------------------------------------------
        "abstain_rate": (round(abstain_total / raw_denominator, 6)
                         if raw_denominator else None),
        "abstain_total": abstain_total,
        "level_distribution": dict(levels),
        "by_stratum": by_stratum,
        "abstain_unchanged_vs_round11": (abstain_total == 226),
        "capability_gain_claim": False,
        # ---- environment isolation (round-9 ADV-1 closure) ---------------
        "env_isolation_applied": True,
        "env_isolation_shared_module": "tools/eval/env_isolation.py",
        "env_isolation_contract": list(env_isolation.ISOLATION_CONTRACT),
        "env_isolation_measured": isolation,
        "env_isolation_all_checks_pass": isolation["all_checks_pass"],
        "clean_env_info": env_info,
        "historical_readings_not_recomputed": [
            "round11 R_main 0.62069",
            "round11 LB95 0.546722",
            "round11 M_C 0.45",
            "round11 SILENT_FALLBACK 30",
        ],
        "historical_note": ("§19 clause 3: whether frozen round-11 readings "
                            "should be recomputed after isolation takes effect "
                            "is explicitly DEFERRED to the next round; this "
                            "script does not touch them."),
        "note": ("single pass with rubric v3 over the frozen 400 samples; no "
                 "main-track output artifact is read; no verdict emitted"),
    }
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = REPO_ROOT / out_path
    write_json(out_path, payload)
    if args.custody:
        write_json(Path(args.custody), payload)

    print("ABSTAIN_RATE", payload["abstain_rate"],
          "ABSTAIN_TOTAL", abstain_total, "N", raw_denominator)
    print("BY_STRATUM", json.dumps(by_stratum, ensure_ascii=False))
    print("ENV_ISOLATION_ALL_CHECKS_PASS", isolation["all_checks_pass"])
    print("CALIBER", payload["caliber"], "NOT_GATE_CONCLUSION True")
    return 0 if isolation["all_checks_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
