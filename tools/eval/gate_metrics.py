#!/usr/bin/env python3
"""Round-10 dual-metric gate instrumentation (card XJ-20261111-001, D3).

Frozen in ``docs/eval-prereg.md`` §17. Three independent modes:

* ``--gate0``   Gate 0 main-track reliability: compare two independent judging
                sessions claim-by-claim and report ``r_main`` (plus the
                flags / detail / perturbation side metrics).
* ``--run-dir`` + ``--shadow``
                Dual-metric gate on real round-10 data: decidable rate,
                conditional agreement C, confusion matrix and the five
                pre-registered observation ERROR classes (SILENT_FALLBACK
                reported as its own line, never folded away).
* ``--goldset`` 60-row double-blind gold set calibration: ``a_main``,
                ``a_shadow`` and the direction criterion
                ``A_shadow >= A_main - 0.05`` (diagnostic only, never a gate).

Discipline (§17 D17-D / D17-F / D17-H):
  - decidable == (exit == 0) AND output parseable AND no pre-registered ERROR;
  - ERROR records stay in the decidable-rate denominator (no hiding);
  - C's denominator is the decidable set only;
  - outputs contain no grading tokens and no verdict field;
  - Python 3.9 compatible (CI): never pass a newline kwarg to the Path text
    writer (that kwarg does not exist before 3.10), no PEP 604 unions; every
    JSON write uses ``open(..., newline="")``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = REPO_ROOT / "tools" / "eval"
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

# The five pre-registered classes are owned by the (red-zone) shadow_align
# module. Import, never copy: a duplicated list could silently drift.
import shadow_align  # noqa: E402  (path setup above)
import judge  # noqa: E402
import dsl_compiler  # noqa: E402
from schema import Claim, EvidenceLine  # noqa: E402

OBSERVATION_ERROR_CLASSES = tuple(shadow_align.OBSERVATION_ERROR_CLASSES)
DECIDABLE_RATE_FLOOR = 0.80
DIRECTION_TOLERANCE = 0.05
GATE0_SUSPEND_FLOOR = 0.90
GATE_INPUT_FILENAME = "gate-input.json"


# --------------------------------------------------------------------------
# shared helpers
# --------------------------------------------------------------------------
def _load_json(path: Path) -> Dict[str, Any]:
    with open(str(path), "r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # CI is py3.9: the Path text writer has no newline kwarg there.
    with open(str(path), "w", encoding="utf-8", newline="") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def _sha256_file(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with open(str(path), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def floor_to_5pct(value: Any) -> float:
    """§17 D17-E: floor to the 0.05 grid, decimal arithmetic (no float drift)."""
    d = Decimal(str(value))
    step = Decimal("0.05")
    return float((d / step).to_integral_value(rounding=ROUND_FLOOR) * step)


def derive_gate_value(r_main: Any) -> Tuple[float, float, float]:
    """Return (M_C, min(0.95, R_main-0.05), pre_screen_threshold)."""
    r = Decimal(str(r_main))
    base = min(Decimal("0.95"), r - Decimal("0.05"))
    pre = min(Decimal("0.85"), r - Decimal("0.10"))
    return floor_to_5pct(base), float(base), float(pre)


# --------------------------------------------------------------------------
# mode 1: Gate 0 main-track reliability
# --------------------------------------------------------------------------
def _session_claims(doc: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {str(c["key"]): c for c in doc.get("claims", [])}


def _agreement(a: Dict[str, Dict[str, Any]], b: Dict[str, Dict[str, Any]],
               field: str) -> Tuple[float, int, int]:
    keys = sorted(set(a) & set(b))
    hit = sum(1 for k in keys if a[k].get(field) == b[k].get(field))
    return (hit / len(keys) if keys else 0.0), hit, len(keys)


def run_gate0(args: argparse.Namespace) -> Dict[str, Any]:
    if not args.main or not args.main_rerun:
        raise ValueError("--gate0 requires --main and --main-rerun")
    a_doc = _load_json(Path(args.main))
    b_doc = _load_json(Path(args.main_rerun))
    a, b = _session_claims(a_doc), _session_claims(b_doc)
    r_main, hit, total = _agreement(a, b, "level_digest")
    r_flags, _, _ = _agreement(a, b, "flags_digest")
    r_detail, _, _ = _agreement(a, b, "detail_digest")

    fa, fb = a_doc.get("env_fingerprint", {}), b_doc.get("env_fingerprint", {})
    independence = {
        "distinct_process": fa.get("pid") != fb.get("pid"),
        "distinct_started_utc": fa.get("started_utc") != fb.get("started_utc"),
        "distinct_workspace": fa.get("workspace_root") != fb.get("workspace_root"),
        "distinct_blind_seed": fa.get("blind_seed") != fb.get("blind_seed"),
        "distinct_input_order": fa.get("input_order") != fb.get("input_order"),
        "same_judge_sha256": fa.get("judge_sha256") == fb.get("judge_sha256"),
        "same_claim_set_sha256": (fa.get("claim_set_sha256")
                                  == fb.get("claim_set_sha256")),
    }
    independence["all_checks_pass"] = all(independence.values())

    perturbed: Dict[str, Any] = {"available": False}
    if args.perturbed:
        c_doc = _load_json(Path(args.perturbed))
        c = _session_claims(c_doc)
        r_pert, hit_p, total_p = _agreement(a, c, "level_digest")
        perturbed = {
            "available": True,
            "r_main_perturbed": r_pert,
            "agreeing_claims": hit_p,
            "compared_claims": total_p,
            "below_floor": r_pert < GATE0_SUSPEND_FLOOR,
            "note": ("environment-perturbation robustness; a low value does not "
                     "rewrite r_main but forbids declaring a shadow gate result"),
        }

    by_layer: Dict[str, Dict[str, int]] = {}
    for k in sorted(set(a) & set(b)):
        layer = str(a[k].get("layer", "unspecified"))
        slot = by_layer.setdefault(layer, {"claims": 0, "level_agree": 0})
        slot["claims"] += 1
        if a[k].get("level_digest") == b[k].get("level_digest"):
            slot["level_agree"] += 1

    return {
        "mode": "gate0",
        "r_main": round(r_main, 6),
        "level_agreeing_claims": hit,
        "compared_claims": total,
        "r_main_flags": round(r_flags, 6),
        "r_main_detail": round(r_detail, 6),
        "gate0_suspend": r_main < GATE0_SUSPEND_FLOOR,
        "suspend_floor": GATE0_SUSPEND_FLOOR,
        "perturbation": perturbed,
        "session_independence": independence,
        "by_layer": by_layer,
        "determinism_limitation": (
            "judge.py is deterministic (no LLM / no network / no randomness). "
            "Two sessions with identical inputs therefore agree by construction: "
            "r_main=1.0 is a replay identity, NOT evidence of semantic "
            "reliability or cross-environment robustness. Report this in the "
            "Gate 0 conclusion, do not launder it."
        ),
        "note": ("two independent full judging sessions; outputs carry digests "
                 "only, never grading tokens"),
    }


# --------------------------------------------------------------------------
# mode 2: dual-metric gate on real round-10 data
# --------------------------------------------------------------------------
def run_dual_metric(args: argparse.Namespace) -> Dict[str, Any]:
    if not args.run_dir or not args.shadow:
        raise ValueError("dual-metric mode requires --run-dir and --shadow")
    run_dir, shadow = Path(args.run_dir), Path(args.shadow)
    gate_input = shadow / GATE_INPUT_FILENAME
    doc = _load_json(gate_input)
    pairs = list(doc.get("pairs", []))

    def own_bucket(p: Dict[str, Any]) -> bool:
        return bool(p.get("not_applicable") or p.get("evaluative")
                    or p.get("schema_invalid"))

    comparable = [p for p in pairs if not own_bucket(p)]
    error_breakdown = {c: 0 for c in OBSERVATION_ERROR_CLASSES}
    for p in comparable:
        for cls in p.get("error_classes", []):
            if cls in error_breakdown:
                error_breakdown[cls] += 1

    decidable, excluded = [], []
    for p in comparable:
        classes = [c for c in p.get("error_classes", [])
                   if c in OBSERVATION_ERROR_CLASSES]
        ok = (int(p.get("exit_code", -1)) == 0
              and bool(p.get("parse_ok"))
              and not classes)
        if ok:
            decidable.append(p)
        else:
            excluded.append({
                "claim_id": p.get("claim_id"),
                "exit_code": p.get("exit_code"),
                "parse_ok": p.get("parse_ok"),
                "error_classes": classes,
            })

    confusion = {"TP": 0, "TN": 0, "FP": 0, "FN": 0}
    consistent = 0
    for p in decidable:
        pred = bool(p.get("predicate_ok"))
        main_supports = bool(p.get("main_supports"))
        if pred and main_supports:
            confusion["TP"] += 1
        elif not pred and not main_supports:
            confusion["TN"] += 1
        elif pred and not main_supports:
            confusion["FP"] += 1
        else:
            confusion["FN"] += 1
        if pred == main_supports:
            consistent += 1

    n_comp = len(comparable)
    n_dec = len(decidable)
    decidable_rate = (n_dec / n_comp) if n_comp else None
    conditional_agreement = (consistent / n_dec) if n_dec else None
    m_c = doc.get("m_c")
    gate_result: Optional[str] = None
    if m_c is not None and decidable_rate is not None and conditional_agreement is not None:
        if bool(doc.get("gate0_suspend")):
            gate_result = "suspended"
        else:
            gate_result = ("met" if (decidable_rate >= DECIDABLE_RATE_FLOOR
                                     and conditional_agreement >= float(m_c))
                           else "not met")

    return {
        "mode": "dual_metric",
        "comparable": n_comp,
        "decidable": n_dec,
        "excluded_from_c_denominator": len(excluded),
        "decidable_rate": (round(decidable_rate, 6)
                           if decidable_rate is not None else None),
        "decidable_rate_floor": DECIDABLE_RATE_FLOOR,
        "consistent": consistent,
        "conditional_agreement": (round(conditional_agreement, 6)
                                  if conditional_agreement is not None else None),
        "m_c": m_c,
        "confusion_matrix": confusion,
        "error_breakdown": error_breakdown,
        "silent_fallback_count": error_breakdown.get("SILENT_FALLBACK", 0),
        "silent_fallback_reported_separately": ("SILENT_FALLBACK" in error_breakdown),
        "excluded_from_denominator": excluded,
        "own_buckets": {
            "not_applicable": sum(1 for p in pairs if p.get("not_applicable")),
            "evaluative": sum(1 for p in pairs if p.get("evaluative")),
            "schema_invalid": sum(1 for p in pairs if p.get("schema_invalid")),
        },
        "fail_fast_observation": bool(doc.get("fail_fast_observation", True)),
        "allow_silent_fallback_used": bool(doc.get("allow_silent_fallback_used", False)),
        "gate0_suspend": bool(doc.get("gate0_suspend", False)),
        "gate_result": gate_result,
        "run_dir_manifest": {
            "run_data_present": (run_dir / "run-data.json").is_file(),
            "run_data_sha256": _sha256_file(run_dir / "run-data.json"),
        },
        "gate_input_sha256": _sha256_file(gate_input),
        "note": ("ERROR records stay in the decidable-rate denominator; C uses "
                 "only decidable records; SILENT_FALLBACK is a standalone class"),
    }


# --------------------------------------------------------------------------
# mode 3: gold-set calibration
# --------------------------------------------------------------------------
def run_goldset(args: argparse.Namespace) -> Dict[str, Any]:
    import shutil
    import tempfile

    gold_path = Path(args.goldset)
    rows = [json.loads(line) for line in
            open(str(gold_path), "r", encoding="utf-8").read().splitlines()
            if line.strip()]
    triples = [r for r in rows if "_meta" not in r]

    workdir = Path(tempfile.mkdtemp(prefix="goldset-r10-"))
    main_hits = shadow_hits = comparable = 0
    excluded: List[str] = []
    mismatches: List[Dict[str, Any]] = []
    coverage: Dict[str, int] = {}
    disagreements = 0
    try:
        for row in triples:
            cid = str(row.get("record", {}).get("claim_id")
                      or row.get("claim_id") or "<unknown>")
            ann = row.get("annotation", {})
            if ann.get("disagreement"):
                disagreements += 1
            for label in row.get("coverage_labels", []):
                coverage[str(label)] = coverage.get(str(label), 0) + 1

            if (row.get("expect_uncompilable") or row.get("expect_not_applicable")
                    or row.get("expect_consistent") is None
                    or row.get("expected_main_level") is None
                    or row.get("expected_shadow_predicate_ok") is None):
                excluded.append(cid)
                continue

            triple_root = workdir / cid
            triple_root.mkdir(parents=True, exist_ok=True)
            for name, content in (row.get("fixture", {}).get("files") or {}).items():
                p = triple_root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                with open(str(p), "w", encoding="utf-8", newline="") as fh:
                    fh.write(content)

            # --- main track: frozen judge, independently designated expectation
            mji = row.get("main_judgement_input", {})
            ev = mji.get("evidence") or {}
            evidence = EvidenceLine(
                raw=str(ev.get("raw", "")),
                source_line=int(ev.get("source_line", 0) or 0),
                command=ev.get("command"),
                exit_code=ev.get("exit_code"),
                out=ev.get("out"),
                ref=ev.get("ref"),
            )
            claim = Claim(
                text=str(mji.get("text", row.get("main", {}).get("text", ""))),
                source_line=int(mji.get("source_line", 0) or 0),
                product=cid,
                evidence=evidence,
                anchors=list(mji.get("anchors", [])),
                unanchored=bool(mji.get("unanchored", False)),
            )
            j = judge.judge_claim(claim, triple_root, timeout=args.timeout)
            main_agree = _digest(j.level) == _digest(row["expected_main_level"])

            # --- shadow track: frozen DSL executor
            compiled = dsl_compiler.execute_record(
                dict(row["record"]), triple_root, args.timeout,
                workspace=triple_root)
            shadow_agree = (bool(compiled.get("predicate_ok"))
                            == bool(row["expected_shadow_predicate_ok"]))

            comparable += 1
            main_hits += int(main_agree)
            shadow_hits += int(shadow_agree)
            if not (main_agree and shadow_agree):
                mismatches.append({
                    "claim_id": cid,
                    "main_agree": main_agree,
                    "shadow_agree": shadow_agree,
                    "detail": str(compiled.get("detail", ""))[:120],
                })
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    a_main = (main_hits / comparable) if comparable else None
    a_shadow = (shadow_hits / comparable) if comparable else None
    direction_pass = (a_shadow is not None and a_main is not None
                      and a_shadow >= a_main - DIRECTION_TOLERANCE)
    return {
        "mode": "goldset",
        "goldset_rows": len(rows),
        "triples": len(triples),
        "comparable": comparable,
        "excluded": len(excluded),
        "excluded_ids": excluded,
        "a_main": round(a_main, 6) if a_main is not None else None,
        "a_shadow": round(a_shadow, 6) if a_shadow is not None else None,
        "direction_pass": direction_pass,
        "direction_tolerance": DIRECTION_TOLERANCE,
        "direction_is_diagnostic_only": True,
        "annotation_disagreements": disagreements,
        "coverage_labels": coverage,
        "mismatch_details": mismatches,
        "goldset_sha256": _sha256_file(gold_path),
        "note": ("direction criterion is diagnostic, never a layered hard gate; "
                 "expectations are designated independently of implementation "
                 "output; no grading tokens are emitted"),
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate0", action="store_true", help="Gate 0 reliability mode")
    ap.add_argument("--main", help="first judging session JSON (Gate 0)")
    ap.add_argument("--main-rerun", dest="main_rerun",
                    help="second independent judging session JSON (Gate 0)")
    ap.add_argument("--perturbed", help="optional environment-perturbed session JSON")
    ap.add_argument("--run-dir", dest="run_dir", help="round-10 main run directory")
    ap.add_argument("--shadow", help="round-10 shadow directory")
    ap.add_argument("--goldset", help="gold claims JSONL")
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--out", required=True, help="output JSON path")
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.gate0:
            payload = run_gate0(args)
        elif args.goldset:
            payload = run_goldset(args)
        elif args.run_dir or args.shadow:
            payload = run_dual_metric(args)
        else:
            print("usage error: choose --gate0 / --goldset / --run-dir + --shadow",
                  file=sys.stderr)
            return 2
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        print("gate_metrics: {} ({})".format(type(exc).__name__, exc),
              file=sys.stderr)
        return 1
    _write_json(Path(args.out), payload)
    print("wrote {} ({})".format(args.out, payload.get("mode")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
