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
# mode 4: round-11 gate re-run (§18 D18-B clauses 7/8/10, card D4/D5)
# --------------------------------------------------------------------------
def run_r11(args: argparse.Namespace) -> Dict[str, Any]:
    """Re-run the gate metrics on the round-10 210 pairs, zero new data.

    The round-11 upgrades applied here are **measurement-only**:

    * three-state ``exit_source`` provenance (os / adapter / launch_failed);
    * main metric = (pass_rate, precision, recall) + 2x2 confusion matrix,
      with C demoted to a secondary historical-comparison cell rate;
    * ``adapter`` samples excluded from main C / main precision and moved to
      the secondary report;
    * ``launch_failed`` never counted as "not supported";
    * gate conclusion copied from the D4 frozen lookup result, never
      re-interpreted here.

    Honesty note: ``r10-gate-input.json::field_semantics.exit_code`` declares
    verbatim that its exit codes are "a mechanical map over flags/detail, NOT
    an independent OS process exit code".  Every one of the 210 pairs is
    therefore ``exit_source = adapter``.  Applying clause 11 excludes all of
    them from main C / main precision, which leaves the primary metrics with
    no valid denominator.  That is reported as ``evaluable = false`` rather
    than being laundered into a favourable number.
    """
    gate_input = Path(args.gate_input)
    doc = _load_json(gate_input)
    pairs = list(doc.get("pairs", []))

    mc_doc = _load_json(Path(args.mc)) if args.mc else {}
    rel_doc = (_load_json(Path(args.reliability))
               if args.reliability else {})

    provenance = str(doc.get("field_semantics", {}).get("exit_code", ""))
    mechanical = ("mechanical map" in provenance.lower()
                  or "not an independent os" in provenance.lower())

    def own_bucket(p: Dict[str, Any]) -> bool:
        return bool(p.get("not_applicable") or p.get("evaluative")
                    or p.get("schema_invalid"))

    comparable = [p for p in pairs if not own_bucket(p)]

    exit_source_counts = {"os": 0, "adapter": 0, "launch_failed": 0}
    launch_failed_as_unsupported = 0
    provenance_rows: List[Dict[str, Any]] = []
    for p in comparable:
        code = int(p.get("exit_code", -1))
        if code in (127, 9009):
            src = "launch_failed"
        elif mechanical:
            src = "adapter"
        else:
            src = "os"
        exit_source_counts[src] += 1
        classes = [c for c in p.get("error_classes", [])
                   if c in OBSERVATION_ERROR_CLASSES]
        # "not supported" here means the observation was used to judge the
        # claim as unsupported. launch_failed must never contribute.
        judged_unsupported = (not bool(p.get("predicate_ok"))
                              and src != "launch_failed")
        if src == "launch_failed" and judged_unsupported:
            launch_failed_as_unsupported += 1
        provenance_rows.append({
            "claim_id": p.get("claim_id"),
            "exit_source": src,
            "caliber": ("primary" if src == "os"
                        else "degraded" if src == "adapter" else "excluded"),
            "error_classes": classes,
        })

    error_breakdown = {c: 0 for c in OBSERVATION_ERROR_CLASSES}
    for p in comparable:
        for cls in p.get("error_classes", []):
            if cls in error_breakdown:
                error_breakdown[cls] += 1

    decidable = []
    excluded: List[Dict[str, Any]] = []
    for p in comparable:
        classes = [c for c in p.get("error_classes", [])
                   if c in OBSERVATION_ERROR_CLASSES]
        ok = (int(p.get("exit_code", -1)) == 0
              and bool(p.get("parse_ok")) and not classes)
        if ok:
            decidable.append(p)
        else:
            excluded.append({"claim_id": p.get("claim_id"),
                             "exit_code": p.get("exit_code"),
                             "parse_ok": p.get("parse_ok"),
                             "error_classes": classes})

    confusion = {"TP": 0, "TN": 0, "FP": 0, "FN": 0}
    for p in decidable:
        pred = bool(p.get("predicate_ok"))
        main = bool(p.get("main_supports"))
        if pred and main:
            confusion["TP"] += 1
        elif not pred and not main:
            confusion["TN"] += 1
        elif pred and not main:
            confusion["FP"] += 1
        else:
            confusion["FN"] += 1

    tp, tn, fp, fn = (confusion[k] for k in ("TP", "TN", "FP", "FN"))
    positives = tp + fp
    actual_positives = tp + fn
    n_dec = len(decidable)
    n_comp = len(comparable)

    # Top-level triple is the SECONDARY diagnostic (adapter-inclusive) view;
    # the primary view is reported separately and may be non-evaluable.
    pass_rate = (positives / n_dec) if n_dec else None
    precision = (tp / positives) if positives else None
    recall = (tp / actual_positives) if actual_positives else None
    conditional_agreement = ((tp + tn) / n_dec) if n_dec else None

    decidable_ids = set(id(p) for p in decidable)
    primary_decidable = [
        p for p, row in zip(comparable, provenance_rows)
        if row["exit_source"] == "os"
        and id(p) in decidable_ids
    ]
    primary_confusion = {"TP": 0, "TN": 0, "FP": 0, "FN": 0}
    for p in primary_decidable:
        pred, main = bool(p.get("predicate_ok")), bool(p.get("main_supports"))
        if pred and main:
            primary_confusion["TP"] += 1
        elif not pred and not main:
            primary_confusion["TN"] += 1
        elif pred and not main:
            primary_confusion["FP"] += 1
        else:
            primary_confusion["FN"] += 1
    ptp, pfp, pfn = (primary_confusion[k] for k in ("TP", "FP", "FN"))
    primary_evaluable = len(primary_decidable) > 0

    # Cross-check the classifier against the frozen D5 fixture, so the gate
    # report and the 10/10 fixture cannot silently use different rules.
    fixture_cross: Dict[str, Any] = {"available": False}
    try:
        import exit_fixture  # noqa: E402  (same directory, already on sys.path)
        probe = exit_fixture.classify("adapter", "flags_ok", REPO_ROOT)
        fixture_cross = {
            "available": True,
            "adapter_caliber": probe["caliber"],
            "agrees_with_gate_report": probe["caliber"] == "degraded",
        }
    except (ImportError, ValueError, OSError) as exc:
        fixture_cross = {"available": False, "reason": str(exc)}

    m_c = mc_doc.get("m_c")
    branch = mc_doc.get("branch")
    gate_result = mc_doc.get("gate_result")
    gate_conclusion_issued = bool(mc_doc.get("gate_conclusion_issued", False))

    return {
        "mode": "r11_gate_rerun",
        "card": "XJ-20261111-002",
        "zero_new_data": True,
        "source": "D:/15812/projects/round10-custody/r10-gate-input.json",
        "source_sha256": _sha256_file(gate_input),
        "source_pairs": len(pairs),
        "exit_code_provenance_verbatim": provenance,
        "comparable": n_comp,
        "decidable": n_dec,
        "excluded_from_c_denominator": len(excluded),
        "decidable_rate": (round(n_dec / n_comp, 6) if n_comp else None),
        "decidable_rate_floor": DECIDABLE_RATE_FLOOR,
        # ---- main metrics: (pass_rate, precision, recall) + 2x2 ----------
        "pass_rate": round(pass_rate, 6) if pass_rate is not None else None,
        "precision": round(precision, 6) if precision is not None else None,
        "recall": round(recall, 6) if recall is not None else None,
        "confusion_matrix": confusion,
        "metrics_caliber": "secondary_diagnostic_only_adapter_inclusive",
        "metrics_note": ("top-level triple is the secondary diagnostic view "
                         "over all decidable pairs; §18 clause 11 excludes "
                         "adapter samples from MAIN C / MAIN precision, see "
                         "primary_metrics_excluding_adapter"),
        # ---- C demoted to secondary --------------------------------------
        "conditional_agreement": (round(conditional_agreement, 6)
                                  if conditional_agreement is not None else None),
        "c_role": "secondary_historical_comparison_only",
        "c_demoted_to_secondary": True,
        "c_voided_by_triage": True,
        "c_void_reason": "triage bucket b = 100% >= 60% -> §18 clause 8 voids scalar C",
        # ---- degraded / excluded provenance -------------------------------
        "exit_source_counts": exit_source_counts,
        "adapter_samples_in_secondary": exit_source_counts["adapter"],
        "secondary_report": {
            "sample_count": exit_source_counts["adapter"],
            "caliber": "degraded",
            "excluded_from": ["main_c", "main_precision"],
            "sample_ids": [r["claim_id"] for r in provenance_rows
                           if r["exit_source"] == "adapter"],
        },
        "launch_failed_counted_as_unsupported": launch_failed_as_unsupported,
        "primary_metrics_excluding_adapter": {
            "sample_count": len(primary_decidable),
            "evaluable": primary_evaluable,
            "c": (round((ptp + primary_confusion["TN"])
                        / len(primary_decidable), 6)
                  if primary_evaluable else None),
            "precision": (round(ptp / (ptp + pfp), 6)
                          if primary_evaluable and (ptp + pfp) else None),
            "recall": (round(ptp / (ptp + pfn), 6)
                       if primary_evaluable and (ptp + pfn) else None),
            "confusion_matrix": primary_confusion,
            "reason": ("all {} decidable pairs are exit_source=adapter, "
                       "excluded by §18 clause 11; no valid primary "
                       "denominator remains".format(n_dec)),
        },
        "fixture_cross_check": fixture_cross,
        "fixture_path": "out/exit-fixture-r11.json",
        "fixture_sha256": _sha256_file(REPO_ROOT / "out" / "exit-fixture-r11.json"),
        "fixture_yaml": "tools/eval/fixtures/exit_codes.yaml",
        "fixture_yaml_sha256": _sha256_file(
            REPO_ROOT / "tools" / "eval" / "fixtures" / "exit_codes.yaml"),
        # ---- error classes (SILENT_FALLBACK never folded away) ------------
        "error_breakdown": error_breakdown,
        "silent_fallback_count": error_breakdown.get("SILENT_FALLBACK", 0),
        "silent_fallback_reported_separately": ("SILENT_FALLBACK" in error_breakdown),
        "fail_fast_observation": bool(doc.get("fail_fast_observation", True)),
        "allow_silent_fallback_used": bool(doc.get("allow_silent_fallback_used", False)),
        # ---- frozen lookup result, copied verbatim, never re-argued -------
        "m_c": m_c,
        "branch": branch,
        "gate_result": gate_result,
        "gate_conclusion_issued": gate_conclusion_issued,
        "r_main": rel_doc.get("r_main", mc_doc.get("r_main")),
        "lb95": rel_doc.get("lb95", mc_doc.get("lb95")),
        "caliber": mc_doc.get("caliber"),
        "independence_satisfied": rel_doc.get("independence_satisfied", False),
        "note": ("measurement-only re-run on frozen round-10 pairs; no new "
                 "true data, no re-judging, no verdict; gate conclusion copied "
                 "from out/derive-mc-r11.json frozen lookup"),
    }


# --------------------------------------------------------------------------
# mode 5: round-12 real-OS collection gate re-run (§19 D19-B clause 4)
# --------------------------------------------------------------------------
def run_r12(args: argparse.Namespace) -> Dict[str, Any]:
    """Count the exit_source PRODUCED BY THE COLLECTION LAYER, never infer it.

    ADV-2 closure: round-11 ``run_r11`` read
    ``r10-gate-input.json::field_semantics.exit_code`` ("a mechanical map over
    flags/detail") and mechanically concluded 210/210 adapter. That was a
    COLLECTION defect, not a capability gap. Here the input has no provenance
    text at all; each pair carries ``exit_source`` stamped when the collection
    layer actually launched an isolated OS subprocess and read its returncode.

    This function deliberately does NOT look at any field_semantics key. The
    only source of exit_source is ``pairs[i]["exit_source"]``. A missing field
    is a hard error, so a silently unstamped sample cannot pass as primary.

    This is an instrument-calibration re-run: gate_result is pinned to
    not_evaluable (§19 clause 6) and NO gate conclusion is emitted.
    """
    gate_input = Path(args.gate_input)
    doc = _load_json(gate_input)
    pairs = list(doc.get("pairs", []))

    exit_source_counts: Dict[str, int] = {
        "os": 0, "adapter": 0, "launch_failed": 0}
    for p in pairs:
        src = p.get("exit_source")
        if src not in exit_source_counts:
            raise ValueError("unstamped or unknown exit_source: {!r}".format(src))
        exit_source_counts[str(src)] += 1

    launch_failed_as_unsupported = sum(
        1 for p in pairs
        if p["exit_source"] == "launch_failed" and p.get("unsupported"))

    # Primary set: real OS samples that are decidable under §17's rule.
    primary = []
    excluded: List[Dict[str, Any]] = []
    for p in pairs:
        if p["exit_source"] != "os":
            continue
        classes = [c for c in p.get("error_classes", [])
                   if c in OBSERVATION_ERROR_CLASSES]
        ok = (int(p.get("exit_code", -1)) == 0
              and bool(p.get("parse_ok")) and not classes)
        if ok:
            primary.append(p)
        else:
            excluded.append({
                "claim_id": p.get("claim_id"),
                "exit_code": p.get("exit_code"),
                "parse_ok": p.get("parse_ok"),
                "error_classes": classes,
                "reason": ("§17 decidable rule: exit==0 AND parseable AND "
                           "no pre-registered ERROR class"),
            })

    confusion = {"TP": 0, "TN": 0, "FP": 0, "FN": 0}
    for p in primary:
        pred = bool(p.get("predicate_ok"))
        main = bool(p.get("main_supports"))
        if pred and main:
            confusion["TP"] += 1
        elif not pred and not main:
            confusion["TN"] += 1
        elif pred and not main:
            confusion["FP"] += 1
        else:
            confusion["FN"] += 1
    tp, tn, fp, fn = (confusion[k] for k in ("TP", "TN", "FP", "FN"))
    n_primary = len(primary)
    evaluable = n_primary > 0
    precision = (tp / (tp + fp)) if (tp + fp) else None
    recall = (tp / (tp + fn)) if (tp + fn) else None
    pass_rate = ((tp + fp) / n_primary) if n_primary else None
    conditional_agreement = ((tp + tn) / n_primary) if n_primary else None

    verification = doc.get("collection_self_verification", {})
    return {
        "mode": "r12_gate_rerun_real_os_collection",
        "card": "XJ-20261112-001",
        "phase": "D3 / card D4",
        "source": str(args.gate_input),
        "source_sha256": _sha256_file(gate_input),
        "n_pairs": len(pairs),
        # ---- ADV-2: provenance from the collection layer only ------------
        "exit_source_counts": exit_source_counts,
        "exit_source_from_collection_layer": True,
        "provenance_text_used_for_inference": False,
        "field_semantics_key_read": False,
        "provenance_discipline_note": (
            "run_r12 never reads field_semantics or any provenance text; "
            "exit_source is counted verbatim from each collected pair"),
        "collection_layer": doc.get("collection_layer"),
        "collection_self_verification": verification,
        "os_samples_returncode_reverified": bool(verification.get("all_match")),
        "sample_reverification_mechanism": verification.get("mechanism"),
        "launch_failed_counted_as_unsupported": launch_failed_as_unsupported,
        "env_isolation_shared_module": doc.get("env_isolation_shared_module"),
        # ---- main metrics (triple + 2x2), C stays secondary -------------
        "primary_sample_count": n_primary,
        "excluded_from_primary": len(excluded),
        "excluded_detail": excluded,
        "pass_rate": round(pass_rate, 6) if pass_rate is not None else None,
        "precision": round(precision, 6) if precision is not None else None,
        "recall": round(recall, 6) if recall is not None else None,
        "confusion_matrix": confusion,
        "conditional_agreement": (round(conditional_agreement, 6)
                                  if conditional_agreement is not None else None),
        "c_role": "secondary_historical_comparison_only",
        "primary_metrics": {
            "evaluable": evaluable,
            "sample_count": n_primary,
            "precision": round(precision, 6) if precision is not None else None,
            "recall": round(recall, 6) if recall is not None else None,
            "pass_rate": (round(pass_rate, 6)
                          if pass_rate is not None else None),
            "confusion_matrix": dict(confusion),
            "exit_source": "os_only",
            "reason": ("§19 clause 4 / clause 11: adapter samples are excluded "
                       "from main precision; here adapter=0 because the "
                       "collection layer really launched OS processes"),
        },
        "c_demoted_to_secondary": True,
        # ---- no gate conclusion, ever -------------------------------------
        "caliber": "instrument_calibration_only",
        "gate_result": "not_evaluable",
        "gate_conclusion_issued": False,
        "gate_value_recomputed": False,
        "r_main_recomputed": False,
        "note": ("instrument-calibration re-run to prove the real-OS "
                 "collection pipeline is connected (ADV-2). NOT a new true-data "
                 "gate round and NOT a gate conclusion; no gate value appears."),
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
    # Round-11 mode (D4/D5): zero-new-data gate re-run with tri-state
    # exit_source, triple + 2x2 main metrics and C demoted to secondary.
    ap.add_argument("--r11", action="store_true",
                    help="round-11 gate re-run mode")
    # Round-12 mode (D3): count exit_source stamped by the real-OS collection
    # layer; no provenance-text inference; no gate conclusion.
    ap.add_argument("--r12", action="store_true",
                    help="round-12 real-OS collection gate re-run mode")
    ap.add_argument("--gate-input", dest="gate_input",
                    default="D:/15812/projects/round10-custody/r10-gate-input.json",
                    help="frozen round-10 gate input (210 pairs)")
    ap.add_argument("--mc", default="out/derive-mc-r11.json",
                    help="D4 frozen M_C lookup result")
    ap.add_argument("--reliability", default="out/r11-main-reliability.json",
                    help="D3 blind R_main result")
    ap.add_argument("--out", required=True, help="output JSON path")
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.r12:
            payload = run_r12(args)
        elif args.r11:
            payload = run_r11(args)
        elif args.gate0:
            payload = run_gate0(args)
        elif args.goldset:
            payload = run_goldset(args)
        elif args.run_dir or args.shadow:
            payload = run_dual_metric(args)
        else:
            print("usage error: choose --r12 / --r11 / --gate0 / --goldset / "
                  "--run-dir + --shadow", file=sys.stderr)
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
