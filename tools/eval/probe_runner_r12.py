#!/usr/bin/env python3
"""D4: run the 5-family, 50-case discrimination probe set (card XJ-20261112-001).

§19 clause 5 freezes the strict-bool disagreement threshold at 0.15 and says
it must never be lowered after seeing data. This runner READS that frozen
value back out of the §19 constant table and refuses to proceed if the local
constant differs, so "threshold unchanged" is mechanically checkable.

Blind order (as in round 11): independent v3 runs FIRST over all 50 cases,
its output is hashed and sealed; only then is the main-track judge invoked.
No expectation label is stored in the probe set; both tracks are invoked for
real. Disagreement definitions are unchanged from round 11:

  * disagreement       main_supports != indep_supports (None counts);
  * strict_bool        both are booleans AND they differ (abstention excluded);
  * strict rate        n_strict / TOTAL cases (50), never a reduced denominator.

The new `structural_unjudgeable` family deliberately contains 3 control cases
that agree, so it is not engineered to disagree by construction. It also calls
the shared env_isolation module (round-9 ADV-1 / D2 uniformity).

Python 3.9 compatible. JSON writes use open(..., newline="").
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = REPO_ROOT / "tools" / "eval"
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

import env_isolation  # noqa: E402
import independent_judge  # noqa: E402
import judge  # noqa: E402  (RED ZONE: read-only invocation, never modified)
import rubric_v3  # noqa: E402

P_THRESHOLD = 0.15           # frozen in §19 D19-D, must not be lowered
N_PROBE = 50
MIN_FAMILIES = 5
NEW_FAMILY = "structural_unjudgeable"

_SECTION19_THRESHOLD_RE = re.compile(
    r"\|\s*严格布尔分歧阈值\s*\|\s*`?([0-9.]+)`?\s*\|")


def frozen_threshold_from_prereg() -> Optional[float]:
    """Mechanically read the threshold back from the FROZEN §19 text."""
    path = REPO_ROOT / "docs" / "eval-prereg.md"
    with open(str(path), "r", encoding="utf-8") as fh:
        text = fh.read()
    i = text.find("## §19")
    if i < 0:
        return None
    m = _SECTION19_THRESHOLD_RE.search(text[i:])
    return float(m.group(1)) if m else None


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _write(path: Path, obj: Any) -> str:
    text = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path), "w", newline="", encoding="utf-8") as fh:
        fh.write(text)
    return _sha(text.encode("utf-8"))


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--probe-set", dest="probe_set",
                    default="tools/eval/probe_set.json")
    ap.add_argument("--out", default="out/r12-probe-report.json")
    ap.add_argument("--custody", default="")
    args = ap.parse_args(argv)

    probe_path = Path(args.probe_set)
    if not probe_path.is_absolute():
        probe_path = REPO_ROOT / probe_path
    probe_bytes = probe_path.read_bytes()
    cases = json.loads(probe_bytes.decode("utf-8"))
    if len(cases) != N_PROBE:
        print("BAD_N_PROBE", len(cases))
        return 2
    families = sorted(set(c["family"] for c in cases))
    if len(families) < MIN_FAMILIES or NEW_FAMILY not in families:
        print("BAD_FAMILIES", families)
        return 2

    frozen = frozen_threshold_from_prereg()
    threshold_matches = (frozen is not None and abs(frozen - P_THRESHOLD) < 1e-9)
    if not threshold_matches:
        print("THRESHOLD_MISMATCH local", P_THRESHOLD, "§19", frozen)
        return 2

    isolation = env_isolation.verify_isolation()

    # ---- stage 1: independent implementation, blind ---------------------
    independent: List[Dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="r12-probe-independent-") as tmp:
        base = Path(tmp)
        for i, c in enumerate(cases):
            ws = rubric_v3.materialise(c, base / ("c%02d" % i))
            independent.append(independent_judge.judge_case(c, ws, "v3"))
    blind_doc = {
        "stage": "independent_blind_run",
        "probe_set_sha256": _sha(probe_bytes),
        "rubric": independent_judge.RUBRIC_V3["id"],
        "n": len(independent),
        "results": independent,
    }
    blind_path = REPO_ROOT / "out" / "r12-probe-independent-blind.json"
    blind_sha = _write(blind_path, blind_doc)
    seal = {
        "sealed_at_utc": datetime.now(timezone.utc).isoformat(),
        "sealed_sha256": blind_sha,
        "sealed_path": "out/r12-probe-independent-blind.json",
        "main_track_invoked_before_seal": False,
        "order": "independent_run -> sha256 seal -> main_track -> compare",
        "env_isolation_all_checks_pass": isolation["all_checks_pass"],
    }
    _write(REPO_ROOT / "out" / "r12-probe-seal-log.json", seal)

    # ---- stage 2: main-track judge (red zone, read-only) ----------------
    main_rows = []
    with tempfile.TemporaryDirectory(prefix="r12-probe-main-") as tmp:
        base = Path(tmp)
        for i, c in enumerate(cases):
            b = base / ("c%02d" % i)
            ws = rubric_v3.materialise(c, b)
            root = b / "root"
            root.mkdir(parents=True, exist_ok=True)
            kw = dict(product=c["case_id"], timeout=20)
            if c.get("main_workspace_mode") == "workspace":
                kw["workspace"] = ws
            try:
                js = judge.judge_markdown(c["markdown"], root, **kw)
                level = js[0].level if js else "NO_CLAIM"
            except Exception as exc:
                level = "EXC:" + type(exc).__name__
            main_rows.append({"case_id": c["case_id"], "level": level,
                              "supports": level == "E4"})

    by_id = {r["case_id"]: r for r in main_rows}
    rows = []
    for c, ind in zip(cases, independent):
        m = by_id[c["case_id"]]
        s = ind.get("supports")
        disagree = (m["supports"] != s)
        strict = isinstance(s, bool) and m["supports"] != s
        rows.append({
            "case_id": c["case_id"], "family": c["family"],
            "intent": c["intent"],
            "main_level": m["level"], "main_supports": m["supports"],
            "indep_level": ind.get("level"), "indep_supports": s,
            "indep_error_class": ind.get("error_class", ""),
            "structural_basis": ind.get("structural_basis", ""),
            "disagreement": disagree,
            "strict_bool_disagreement": strict,
            "adversarial_intent": c.get("adversarial_intent", ""),
        })

    n_dis = sum(1 for r in rows if r["disagreement"])
    n_strict = sum(1 for r in rows if r["strict_bool_disagreement"])
    rate = n_dis / len(rows)
    strict_rate = n_strict / len(rows)

    by_family = {}
    for fam in families:
        fr = [r for r in rows if r["family"] == fam]
        by_family[fam] = {
            "n": len(fr),
            "disagreements": sum(1 for r in fr if r["disagreement"]),
            "rate": round(sum(1 for r in fr if r["disagreement"]) / len(fr), 6),
            "strict_bool_disagreements": sum(
                1 for r in fr if r["strict_bool_disagreement"]),
            "strict_bool_rate": round(
                sum(1 for r in fr if r["strict_bool_disagreement"]) / len(fr), 6),
            "agreeing_control_cases": sum(
                1 for r in fr if not r["disagreement"]),
        }
    by_intent = {}
    for it in ("adversarial", "control"):
        ir = [r for r in rows if r["intent"] == it]
        by_intent[it] = {
            "n": len(ir),
            "disagreements": sum(1 for r in ir if r["disagreement"]),
            "strict_bool_disagreements": sum(
                1 for r in ir if r["strict_bool_disagreement"]),
        }

    threshold_pass = strict_rate >= P_THRESHOLD
    report = {
        "mode": "discrimination_probe_r12",
        "card": "XJ-20261112-001",
        "phase": "D4 / card D5 (V5)",
        "rubric": independent_judge.RUBRIC_V3["id"],
        "n_probe": len(rows),
        "n_families": len(families),
        "families": families,
        "new_family": NEW_FAMILY,
        "p_threshold_frozen": P_THRESHOLD,
        "p_threshold_read_from_section19": frozen,
        "threshold_matches_section19": threshold_matches,
        "threshold_lowered_after_data": False,
        "disagreement_rate": round(rate, 6),
        "strict_bool_disagreement_rate": round(strict_rate, 6),
        "strict_bool_disagreements": n_strict,
        "strict_rate_denominator": len(rows),
        "strict_rate_denominator_policy": "ALL probe cases; no sample removed",
        "threshold_pass": threshold_pass,
        "families_pass": len(families) >= MIN_FAMILIES,
        "by_family": by_family,
        "by_intent": by_intent,
        "new_family_not_engineered": {
            "control_cases_that_agree": by_family[NEW_FAMILY][
                "agreeing_control_cases"],
            "strict_bool_disagreements_in_new_family":
                by_family[NEW_FAMILY]["strict_bool_disagreements"],
            "note": ("the new family contains agreeing controls and abstention "
                     "cases, so it is not designed to disagree by construction; "
                     "no expectation labels are stored in the probe set"),
        },
        "main_level_distribution": dict(Counter(r["main_level"] for r in rows)),
        "indep_level_distribution": dict(
            Counter(str(r["indep_level"]) for r in rows)),
        "probe_set_sha256": _sha(probe_bytes),
        "probe_set_first40_prefix_sha256_before":
            "d6ab79d4946c8fcd03330ae3775121477a9bd150d2d0c940e68905b237e0aaa2",
        "blind_output_sha256": blind_sha,
        "seal_then_main_order": True,
        "env_isolation_shared_module": "tools/eval/env_isolation.py",
        "env_isolation_all_checks_pass": isolation["all_checks_pass"],
        "disagreement_definition": (
            "main_supports != indep_supports; None counts as disagreement; "
            "strict_bool excludes abstention"),
        "gate_result": "not_evaluable",
        "gate_conclusion_issued": False,
        "caliber": "instrument_calibration_only",
        "rows": rows,
    }
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = REPO_ROOT / out_path
    _write(out_path, report)
    if args.custody:
        _write(Path(args.custody), report)

    print("PROBE_SET_SHA256", _sha(probe_bytes))
    print("N_PROBE", len(rows), "FAMILIES", len(families), families)
    print("THRESHOLD_FROZEN", P_THRESHOLD, "FROM_S19", frozen,
          "MATCH", threshold_matches)
    print("DISAGREEMENT_RATE", round(rate, 6),
          "STRICT_BOOL_RATE", round(strict_rate, 6),
          "STRICT_N", n_strict, "PASS", threshold_pass)
    print("BY_FAMILY", json.dumps(
        {k: {"n": v["n"], "strict": v["strict_bool_disagreements"],
             "agreeing_control": v["agreeing_control_cases"]}
         for k, v in by_family.items()}, ensure_ascii=False))
    print("ENV_ISOLATION_ALL_CHECKS_PASS", isolation["all_checks_pass"])
    ok = threshold_pass and len(families) >= MIN_FAMILIES
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
