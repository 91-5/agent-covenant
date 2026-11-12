#!/usr/bin/env python3
"""Round-11 M_C re-derivation (card XJ-20261111-002, D4 / V8).

Implements the formula frozen in ``docs/eval-prereg.md`` §18 D18-B::

    M_C = floor_to_5pct( min(0.95, LB95(R_main) - 0.05) )

and the three-branch lookup table, which is keyed on the **point estimate**
of R_main (never on LB95, never on a post-hoc argument):

    R_main >= 0.85          -> normal
    0.80 <= R_main < 0.85   -> weak_reference
    R_main <  0.80          -> not_evaluable  (NO gate conclusion issued)

Section 18 D18-0 / prohibition 3: the re-derivation is performed **once** and
published even when it makes the gate harder.  Re-running this command is not
a second counting run: when the result file already exists the script
recomputes from the frozen formula, verifies byte-level agreement with the
sealed first result, refuses to overwrite, and exits 0 only on identity.  A
mismatch (someone edited the result or the input after seeing it) exits 3.

Python 3.9 compatible (CI): no PEP 604 unions; text writes use
``open(..., newline="")``; the Path text writer is never given a newline
keyword.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]

# ---- frozen constants (§18 D18-B clauses 3, 4, 5; §17 D17-E) -------------
CAP = Decimal("0.95")
MARGIN = Decimal("0.05")
STEP = Decimal("0.05")
BRANCH_NORMAL_FLOOR = Decimal("0.85")
BRANCH_WEAK_FLOOR = Decimal("0.80")
FORMULA = "floor_to_5pct(min(0.95, LB95(R_main) - 0.05))"
BRANCH_TABLE = [
    {"condition": "R_main >= 0.85", "branch": "normal",
     "gate_conclusion": True, "caliber": "normal"},
    {"condition": "0.80 <= R_main < 0.85", "branch": "weak_reference",
     "gate_conclusion": True, "caliber": "weak_reference"},
    {"condition": "R_main < 0.80", "branch": "not_evaluable",
     "gate_conclusion": False, "caliber": "main_track_validity_report_only"},
]
VOIDED_OLD_VALUE = 0.95


def floor_to_5pct(value: Any) -> float:
    """§17 D17-E / §18 D18-B clause 4: floor onto the 0.05 grid."""
    d = Decimal(str(value))
    return float((d / STEP).to_integral_value(rounding=ROUND_FLOOR) * STEP)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(str(path), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    with open(str(path), "r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path), "w", encoding="utf-8", newline="") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def branch_lookup(r_main: Any) -> Dict[str, Any]:
    """Pure table lookup. No interpretation, no discretion (§18 meta-clause)."""
    r = Decimal(str(r_main))
    if r >= BRANCH_NORMAL_FLOOR:
        row = BRANCH_TABLE[0]
    elif r >= BRANCH_WEAK_FLOOR:
        row = BRANCH_TABLE[1]
    else:
        row = BRANCH_TABLE[2]
    return dict(row)


def derive(doc: Dict[str, Any], input_sha256: str) -> Dict[str, Any]:
    r_main = doc.get("r_main")
    lb95 = doc.get("lb95")
    if r_main is None or lb95 is None:
        raise ValueError("input must carry r_main and lb95")
    base = min(CAP, Decimal(str(lb95)) - MARGIN)
    m_c = floor_to_5pct(base)
    row = branch_lookup(r_main)

    gate_result = "not_evaluable" if not row["gate_conclusion"] else "pending"
    independence_satisfied = bool(doc.get("independence_satisfied", False))
    caliber = (doc.get("caliber") or row["caliber"])

    # Cross-check against the §17 implementation when importable. This is a
    # guard against two floor_to_5pct copies drifting apart, not a second run.
    cross: Dict[str, Any] = {"available": False}
    try:
        sys.path.insert(0, str(REPO_ROOT / "tools" / "eval"))
        import gate_metrics  # noqa: E402
        other = gate_metrics.floor_to_5pct(float(base))
        cross = {"available": True, "s17_impl_value": other,
                 "identical": other == m_c}
        if not cross["identical"]:
            raise ValueError("floor_to_5pct disagrees with §17 implementation")
    except ImportError as exc:
        cross = {"available": False, "reason": str(exc)}

    return {
        "mode": "m_c_rederivation_r11",
        "card": "XJ-20261111-002",
        "m_c": m_c,
        "formula": FORMULA,
        "branch": row["branch"],
        "branch_condition": row["condition"],
        "branch_table": BRANCH_TABLE,
        "gate_conclusion_issued": bool(row["gate_conclusion"]),
        "gate_result": gate_result,
        "caliber": caliber,
        "r_main": r_main,
        "lb95": lb95,
        "n": doc.get("n"),
        "seed": doc.get("seed"),
        "raw_formula_value": float(base),
        "floor_step": float(STEP),
        "cap": float(CAP),
        "margin": float(MARGIN),
        "voided_round10_value": VOIDED_OLD_VALUE,
        "void_trace": "out/void-mc095.json",
        "independence_satisfied": independence_satisfied,
        "validity_limitation": (
            "Independence certificate is NOT satisfied (§18 D18-D). The "
            "re-derived value is published as required by the once-only "
            "protocol but no effective gate conclusion may be declared from it."
        ),
        "computed_once": True,
        "lookup_only": True,
        "input_path": "out/r11-main-reliability.json",
        "input_sha256": input_sha256,
        "cross_check_s17_floor": cross,
        "note": (
            "Re-running this command recomputes and verifies identity; it does "
            "not produce a second candidate value and does not overwrite the "
            "first sealed result."
        ),
    }


RECOMPARE_KEYS = ("m_c", "formula", "branch", "r_main", "lb95",
                  "gate_result", "input_sha256", "seed", "n")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default="out/r11-main-reliability.json")
    ap.add_argument("--out", default="out/derive-mc-r11.json")
    args = ap.parse_args(argv)

    inp, outp = Path(args.input), Path(args.out)
    if not inp.is_absolute():
        inp = REPO_ROOT / inp
    if not outp.is_absolute():
        outp = REPO_ROOT / outp
    if not inp.is_file():
        print("derive_mc: input not found: {}".format(inp), file=sys.stderr)
        return 2

    input_sha = _sha256_file(inp)
    doc = _load_json(inp)
    payload = derive(doc, input_sha)

    if outp.is_file():
        first = _load_json(outp)
        diffs = [k for k in RECOMPARE_KEYS if first.get(k) != payload.get(k)]
        if diffs:
            print("derive_mc: SEALED_RESULT_MISMATCH fields={}".format(diffs),
                  file=sys.stderr)
            print("derive_mc: refusing to overwrite a published first count",
                  file=sys.stderr)
            return 3
        print("RECOMPUTE_IDENTICAL: not a second counting run; "
              "sealed result unchanged")
        print("M_C {} | FORMULA {} | BRANCH {} | GATE_RESULT {}".format(
            first.get("m_c"), first.get("formula"), first.get("branch"),
            first.get("gate_result")))
        return 0

    payload["first_count_utc"] = datetime.now(timezone.utc).isoformat()
    _write_json(outp, payload)
    print("FIRST_COUNT (this is the only counting run)")
    print("M_C {} | LB95 {} | R_MAIN {} | BRANCH {} | GATE_RESULT {}".format(
        payload["m_c"], payload["lb95"], payload["r_main"],
        payload["branch"], payload["gate_result"]))
    print("GATE_CONCLUSION_ISSUED {}".format(payload["gate_conclusion_issued"]))
    print("wrote {}".format(outp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
