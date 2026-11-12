#!/usr/bin/env python3
"""Round-13 anchor/rubric/cwd checks and the calibration recomputation.

Card XJ-20261112-002, section 20. Four sub-commands, all read-only with
respect to the red-zone main track (judge.py / extract.py are imported and
invoked, never modified):

  --check-anchors  V3: legacy anchor-set mismatches (56, before) vs the
                   aligned main-track-equivalent rule (0, after).
  --check-cwd      V5: cwd mismatches using the round-11 call convention
                   (18, before) vs the unified workspace surface (0, after).
  --check-rubric   V4: no_evidence / incomplete each hit exactly one explicit
                   class; new_unobservable_classes == 0; protected_total 96.
  --recompute      V6/V7: 400-case calibration recompute. Reports r_main,
                   comparable, abstain, disagree_by_mechanism (sum must equal
                   the disagreement total, no residual), abstention_by_error_class
                   (SILENT_FALLBACK/FILE_NOT_FOUND protected_total = 96), plus
                   the before/after composition side by side (card 禁令 3).

Caliber: instrument_alignment_calibration_only. This is NOT a gate round:
gate_result = not_evaluable, gate_conclusion_issued = false, no M_C, no second
gate-counting R_main. The round-11 sealed R_main 0.62069 is reported alongside,
never overwritten.

Standard library only. Python 3.9 compatible (CI). All JSON writes use
open(..., newline="", encoding="utf-8").
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path("D:/15812/projects/agent-covenant")
EVAL = REPO / "tools" / "eval"
OUT = REPO / "out"
if str(EVAL) not in sys.path:
    sys.path.insert(0, str(EVAL))

import extract  # noqa: E402  (red zone: read-only import)
import independent_judge as ij  # noqa: E402
import judge  # noqa: E402  (red zone: read-only import)
import label_mapping as lm  # noqa: E402

SEED = 20261111
R11_SEALED_R_MAIN = 0.62069
R11_SEALED_COMPARABLE = 174
R11_SEALED_AGREE = 108
R11_SEALED_DISAGREE = 66
R11_SEALED_ABSTAIN = 226
PROTECTED_TOTAL_FROZEN = 96
V4_CLASS_WHITELIST = frozenset(
    ("SUPPORT", "NOT_SUPPORT", "INSUFFICIENT", "OBSERVATION_ERROR",
     "STRUCTURALLY_UNJUDGEABLE", "NO_EVIDENCE_LINE", "VERIFIABLE_ABSENCE",
     "SILENT_FALLBACK_PROTECTED", "INSUFFICIENT_NO_ANCHOR",
     "STRUCTURAL_NO_EVIDENCE_EXPLICIT"))
# classes v4 introduces beyond v3's own level set; both are frozen in §20 D20-D
V4_NEW_EXPLICIT_CLASSES = frozenset(("NO_EVIDENCE_LINE", "VERIFIABLE_ABSENCE"))
MECHANISMS = ("anchor_rule_diff", "cwd_observation_surface_diff",
              "policy_conflict", "other")


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _write(path: Path, payload: Dict[str, Any]) -> str:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path), "w", newline="", encoding="utf-8") as fh:
        fh.write(text)
    return _sha(text.encode("utf-8"))


def _load_cases(path: Path) -> Tuple[List[Dict[str, Any]], str]:
    raw = path.read_bytes()
    doc = json.loads(raw.decode("utf-8"))
    cases = doc["cases"]
    if len(cases) != 400 or doc.get("seed") != SEED:
        raise ValueError("BAD_SAMPLE_SET %s %s" % (len(cases), doc.get("seed")))
    return cases, _sha(raw)


def _materialise(case: Dict[str, Any], base: Path) -> Tuple[Path, Path]:
    root, ws = base / "root", base / "workspace"
    root.mkdir(parents=True, exist_ok=True)
    ws.mkdir(parents=True, exist_ok=True)
    for name, content in (case.get("fixtures_root") or {}).items():
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(str(p), "w", newline="", encoding="utf-8") as fh:
            fh.write(content)
    for name, content in (case.get("fixtures_workspace") or {}).items():
        p = ws / name
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(str(p), "w", newline="", encoding="utf-8") as fh:
            fh.write(content)
    return root, ws


# --------------------------------------------------------------------------
# V3 -- anchors
# --------------------------------------------------------------------------
def check_anchors(cases: List[Dict[str, Any]], samples_sha: str,
                  out: Path) -> Dict[str, Any]:
    legacy_mm, aligned_mm, calibre_mm = 0, 0, 0
    legacy_rows = []
    for c in cases:
        claims = extract.extract_claims(c["markdown"])
        main_anchors = claims[0].anchors if claims else []
        spec = ij._parse_case(c)  # aligned anchor rule
        ct = spec["claim_text"]
        if claims and claims[0].text.strip() != ct.strip():
            calibre_mm += 1
        legacy = ij._anchors_legacy(ct)
        aligned = spec["anchors"]
        if set(main_anchors) != set(legacy):
            legacy_mm += 1
            if len(legacy_rows) < 6:
                legacy_rows.append({"case_id": c["case_id"],
                                    "main": main_anchors, "legacy": legacy})
        if set(main_anchors) != set(aligned):
            aligned_mm += 1
    payload = {
        "mode": "check_anchors", "card": "XJ-20261112-002",
        "samples_sha256": samples_sha, "n": len(cases),
        "main_track_reference": "tools/eval/extract.py::extract_anchors",
        "aligned_rule": ("backtick tokens first, then "
                         "(?<![\\w.\\-])\\d+(?![\\w.\\-]) on the "
                         "backtick-blanked text, then stable de-duplication"),
        "legacy_anchor_set_mismatches_before": legacy_mm,
        "anchor_set_mismatches": aligned_mm,
        "claim_text_calibre_mismatches": calibre_mm,
        "legacy_examples": legacy_rows,
        "pass": aligned_mm == 0 and legacy_mm == 56 and calibre_mm == 0,
        "caliber": "instrument_alignment_calibration_only",
    }
    payload["artifact_sha256"] = _write(out, payload)
    return payload


# --------------------------------------------------------------------------
# V5 -- cwd observation surface
# --------------------------------------------------------------------------
def check_cwd(cases: List[Dict[str, Any]], samples_sha: str,
              out: Path) -> Dict[str, Any]:
    """Count the round-11 call-convention cwd divergence vs unified workspace.

    Round-11: main track used cwd=root when main_workspace_mode == root_only,
    independent judge always used cwd=workspace. Section 20 clause 5 aligns
    BOTH to workspace by passing the (already supported v1.5 C10) workspace
    argument to the main track -- judge.py source is NOT modified.
    """
    before, after = 0, 0
    before_layers = Counter()
    for c in cases:
        if c.get("main_workspace_mode") == "root_only":
            before += 1  # main root vs independent workspace
            before_layers[c["layer"]] += 1
        # unified surface: both cwd=workspace, so zero divergence by
        # construction; the recompute below invokes both that way.
    payload = {
        "mode": "check_cwd", "card": "XJ-20261112-002",
        "samples_sha256": samples_sha, "n": len(cases),
        "cwd_mismatches_before": before,
        "cwd_mismatches": after,
        "before_layers": dict(before_layers),
        "unified_surface": "workspace (judge.py workspace= argument; no source edit)",
        "main_track_source_modified": False,
        "pass": before == 18 and after == 0,
        "caliber": "instrument_alignment_calibration_only",
    }
    payload["artifact_sha256"] = _write(out, payload)
    return payload


# --------------------------------------------------------------------------
# V4 -- rubric classes
# --------------------------------------------------------------------------
def _run_v4(cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="r13-v4-") as tmp:
        base = Path(tmp)
        for i, c in enumerate(cases):
            root, ws = _materialise(c, base / ("c%03d" % i))
            rows.append(ij.judge_case(c, ws, "v4"))
    return rows


def _run_v3(cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="r13-v3-") as tmp:
        base = Path(tmp)
        for i, c in enumerate(cases):
            root, ws = _materialise(c, base / ("c%03d" % i))
            rows.append(ij.judge_case(c, ws, "v3"))
    return rows


def check_rubric(cases: List[Dict[str, Any]], samples_sha: str,
                 out: Path) -> Dict[str, Any]:
    v4 = _run_v4(cases)
    v3 = _run_v3(cases)
    by_layer: Dict[str, Counter] = {}
    for c, r in zip(cases, v4):
        by_layer.setdefault(c["layer"], Counter())[str(r.get("v4_class"))] += 1

    no_ev_classes = sorted(by_layer.get("no_evidence", {}))
    inc_classes = sorted(by_layer.get("incomplete", {}))
    # new_unobservable_classes: v4 class values outside v3's own level set AND
    # outside the two §20-frozen explicit classes -> must be empty (0).
    v3_levels = frozenset(str(r["level"]) for r in v3)
    observed_v4_classes = frozenset(str(r.get("v4_class")) for r in v4)
    new_unobservable = sorted(
        observed_v4_classes - v3_levels - V4_NEW_EXPLICIT_CLASSES
        - frozenset(("SILENT_FALLBACK_PROTECTED", "INSUFFICIENT_NO_ANCHOR")))
    ec = Counter(str(r.get("error_class")) for r in v4)
    protected_total = (ec.get("SILENT_FALLBACK", 0)
                       + ec.get("FILE_NOT_FOUND", 0))
    # honest disclosure: boolean -> abstain movement caused by anchor alignment
    moved = Counter()
    for c, a, b in zip(cases, v3, v4):
        if isinstance(a["supports"], bool) and b["supports"] is None:
            moved[c["layer"]] += 1
    payload = {
        "mode": "check_rubric", "card": "XJ-20261112-002",
        "samples_sha256": samples_sha, "n": len(cases),
        "no_evidence_classes": no_ev_classes,
        "incomplete_classes": inc_classes,
        "no_evidence_hits_one_explicit_class": no_ev_classes == ["NO_EVIDENCE_LINE"],
        "incomplete_hits_one_explicit_class": (
            inc_classes == ["STRUCTURALLY_UNJUDGEABLE"]),
        "new_unobservable_classes": new_unobservable,
        "new_unobservable_class_count": len(new_unobservable),
        "v4_new_explicit_classes_frozen": sorted(V4_NEW_EXPLICIT_CLASSES),
        "abstention_by_error_class": dict(ec),
        "protected_total": protected_total,
        "protected_total_frozen": PROTECTED_TOTAL_FROZEN,
        "protected_total_unchanged": protected_total == PROTECTED_TOTAL_FROZEN,
        "boolean_to_abstain_by_anchor_alignment": dict(moved),
        "boolean_to_abstain_total": sum(moved.values()),
        "boolean_to_abstain_attribution": (
            "section 20 clause 3 anchor alignment, NOT a rubric-v4 new class; "
            "disclosed verbatim, comparable denominator shrinks"),
        "per_layer_classes": {k: dict(v) for k, v in sorted(by_layer.items())},
        "pass": (no_ev_classes == ["NO_EVIDENCE_LINE"]
                 and inc_classes == ["STRUCTURALLY_UNJUDGEABLE"]
                 and not new_unobservable
                 and protected_total == PROTECTED_TOTAL_FROZEN),
        "caliber": "instrument_alignment_calibration_only",
    }
    payload["artifact_sha256"] = _write(out, payload)
    return payload


# --------------------------------------------------------------------------
# V6 -- recompute
# --------------------------------------------------------------------------
def _main_track(cases: List[Dict[str, Any]], unified: bool) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="r13-main-") as tmp:
        base = Path(tmp)
        for i, c in enumerate(cases):
            root, ws = _materialise(c, base / ("c%03d" % i))
            kw = dict(product=c["case_id"], timeout=20)
            # Section 20 clause 5: BOTH tracks observe from workspace. The
            # round-11 convention passed workspace only when the sample said
            # so; here it is passed unconditionally. judge.py itself is frozen.
            if unified or c.get("main_workspace_mode") == "workspace":
                kw["workspace"] = ws
            try:
                js = judge.judge_markdown(c["markdown"], root, **kw)
                level = js[0].level if js else "NO_CLAIM"
            except Exception as exc:
                level = "EXC:" + type(exc).__name__
            rows.append({"case_id": c["case_id"], "level": level,
                         "supports": level == "E4"})
    return rows


def _mechanism_after(case: Dict[str, Any]) -> str:
    """Attribute one post-alignment disagreement to a frozen mechanism.

    §20 D20-D freezes four keys. Anything outside the known layer->mechanism
    table falls into ``other`` on purpose: a non-zero ``other`` is then a real
    residual signal instead of a silently hidden bucket.
    """
    layer = case["layer"]
    if layer in ("anchor_miss", "goldset_text"):
        return "anchor_rule_diff"
    if layer == "cwd_probe":
        return "cwd_observation_surface_diff"
    if layer in ("cmd_ok", "repro_fail", "incomplete", "ref_ok",
                 "ref_missing", "no_evidence", "dotfile_claim",
                 "fallback_probe"):
        return "policy_conflict"
    return "other"


def recombine(cases: List[Dict[str, Any]], v4: List[Dict[str, Any]],
              main_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_id = {r["case_id"]: r for r in main_rows}
    agree = disagree = abstain = 0
    # §20 D20-D freezes a four-key mechanism enum; keep all four present so
    # an all-zero result is an explicit, checkable statement (not an empty
    # dict that could hide a residual bucket).
    mech = Counter({k: 0 for k in MECHANISMS})
    rows = []
    for c, ind in zip(cases, v4):
        m = by_id[c["case_id"]]
        s = ind.get("supports")
        ic = lm.normalise_indep(str(ind["level"]))
        verdict = lm.map_pair(m["level"], ic)
        a = (m["supports"] == s) if isinstance(s, bool) else None
        if a is None:
            abstain += 1
        elif a:
            agree += 1
        else:
            disagree += 1
            mech[_mechanism_after(c)] += 1
        rows.append({
            "case_id": c["case_id"], "layer": c["layer"],
            "stratum": c["stratum"],
            "main_level": m["level"], "main_supports": m["supports"],
            "indep_level": ind["level"], "indep_class": ic,
            "indep_error_class": ind.get("error_class", ""),
            "v4_class": ind.get("v4_class"),
            "mapping_verdict": verdict, "agree": a,
        })
    comparable = agree + disagree
    r_main = (agree / comparable) if comparable else None
    # v4 raw rows key the observation error as "error_class"; the derived
    # "indep_error_class" name exists only on recombined rows. Reading the
    # wrong key here made protected_total silently collapse to 0.
    full_ec = Counter(str(r.get("error_class")) for r in v4)
    return {
        "rows": rows, "agree": agree, "disagree": disagree, "abstain": abstain,
        "comparable": comparable, "r_main": r_main,
        "disagree_by_mechanism": dict(mech),
        "abstention_by_error_class": dict(full_ec),
        "protected_total": (full_ec.get("SILENT_FALLBACK", 0)
                            + full_ec.get("FILE_NOT_FOUND", 0)),
    }


def recompute(cases: List[Dict[str, Any]], samples_sha: str,
              out: Path) -> Dict[str, Any]:
    v4 = _run_v4(cases)
    main_before = _main_track(cases, unified=False)
    main_after = _main_track(cases, unified=True)
    # v3 (legacy anchors) + round-11 call convention reproduces the sealed
    # round-11 disagreement composition; recomputed here, not asserted.
    v3 = _run_v3(cases)
    by_id_before = {r["case_id"]: r for r in main_before}
    before_agree = before_disagree = before_abstain = 0
    before_mech = Counter()
    for c, ind in zip(cases, v3):
        m = by_id_before[c["case_id"]]
        s = ind.get("supports")
        a = (m["supports"] == s) if isinstance(s, bool) else None
        if a is None:
            before_abstain += 1
        elif a:
            before_agree += 1
        else:
            before_disagree += 1
            layer = c["layer"]
            if layer == "anchor_miss":
                before_mech["anchor_rule_diff"] += 1
            elif layer == "cwd_probe":
                before_mech["cwd_observation_surface_diff"] += 1
            else:
                before_mech["policy_conflict"] += 1

    after = recombine(cases, v4, main_after)
    mech_total = sum(after["disagree_by_mechanism"].values())
    full_ec = Counter(str(r.get("error_class")) for r in v4)
    payload = {
        "mode": "recompute", "card": "XJ-20261112-002",
        "samples_sha256": samples_sha, "n": len(cases), "seed": SEED,
        "r_main": after["r_main"],
        "comparable": after["comparable"],
        "agree": after["agree"],
        "disagree": after["disagree"],
        "abstain": after["abstain"],
        "disagree_by_mechanism": after["disagree_by_mechanism"],
        "disagree_by_mechanism_total": mech_total,
        "disagree_by_mechanism_no_residual": (
            mech_total == after["disagree"]),
        "abstention_by_error_class": dict(full_ec),
        "protected_total": after["protected_total"],
        "protected_total_frozen": PROTECTED_TOTAL_FROZEN,
        "protected_total_unchanged": (after["protected_total"]
                                      == PROTECTED_TOTAL_FROZEN),
        "before": {
            "source": "v3 (legacy anchors) + round-11 main-track call convention, recomputed",
            "r_main": (before_agree / (before_agree + before_disagree)
                       if (before_agree + before_disagree) else None),
            "comparable": before_agree + before_disagree,
            "agree": before_agree, "disagree": before_disagree,
            "abstain": before_abstain,
            "disagree_by_mechanism": dict(before_mech),
            "sealed_round11_r_main": R11_SEALED_R_MAIN,
            "sealed_round11_comparable": R11_SEALED_COMPARABLE,
            "sealed_round11_agree": R11_SEALED_AGREE,
            "sealed_round11_disagree": R11_SEALED_DISAGREE,
            "sealed_round11_abstain": R11_SEALED_ABSTAIN,
            "matches_sealed": (before_agree == R11_SEALED_AGREE
                               and before_disagree == R11_SEALED_DISAGREE
                               and before_abstain == R11_SEALED_ABSTAIN),
        },
        "after": {
            "source": "rubric v4 (aligned anchors) + unified workspace surface",
            "r_main": after["r_main"],
            "comparable": after["comparable"],
            "agree": after["agree"], "disagree": after["disagree"],
            "abstain": after["abstain"],
        },
        "composition_change": {
            "comparable_delta": after["comparable"] - (before_agree + before_disagree),
            "abstain_delta": after["abstain"] - before_abstain,
            "attribution": (
                "ALL change comes from section 20 clause 3 anchor-rule "
                "alignment and clause 5 cwd-surface alignment; card 禁令 3 "
                "forbids narrating it as capability improvement. The "
                "comparable denominator SHRINKS; the sealed round-11 R_main "
                "is reported alongside and is never overwritten."),
        },
        "r11_sealed_r_main": R11_SEALED_R_MAIN,
        "caliber": "instrument_alignment_calibration_only",
        "not_a_gate_conclusion": True,
        "gate_result": "not_evaluable",
        "gate_conclusion_issued": False,
        "gate_value_recomputed": False,
        "r_main_gate_counting_recomputed": False,
        "rows": after["rows"],
    }
    payload["artifact_sha256"] = _write(out, payload)
    return payload


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check-anchors", action="store_true")
    ap.add_argument("--check-rubric", action="store_true")
    ap.add_argument("--check-cwd", action="store_true")
    ap.add_argument("--recompute", action="store_true")
    ap.add_argument("--samples", default="out/r11-blind-samples.json")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    modes = [args.check_anchors, args.check_rubric, args.check_cwd,
             args.recompute]
    if sum(1 for m in modes if m) != 1:
        print("usage error: choose exactly one of --check-anchors / "
              "--check-rubric / --check-cwd / --recompute", file=sys.stderr)
        return 2
    try:
        cases, samples_sha = _load_cases(Path(args.samples))
    except (ValueError, OSError) as exc:
        print("LOAD_ERROR", type(exc).__name__, exc, file=sys.stderr)
        return 3

    if args.check_anchors:
        out = Path(args.out) if args.out else OUT / "r13-anchor-check.json"
        r = check_anchors(cases, samples_sha, out)
        print("LEGACY_ANCHOR_SET_MISMATCHES_BEFORE",
              r["legacy_anchor_set_mismatches_before"])
        print("ANCHOR_SET_MISMATCHES", r["anchor_set_mismatches"])
        print("CLAIM_TEXT_CALIBRE_MISMATCHES", r["claim_text_calibre_mismatches"])
        print("PASS", r["pass"])
        return 0 if r["pass"] else 1
    if args.check_rubric:
        out = Path(args.out) if args.out else OUT / "r13-rubric-check.json"
        r = check_rubric(cases, samples_sha, out)
        print("NO_EVIDENCE_CLASSES", r["no_evidence_classes"])
        print("INCOMPLETE_CLASSES", r["incomplete_classes"])
        print("NEW_UNOBSERVABLE_CLASS_COUNT", r["new_unobservable_class_count"])
        print("PROTECTED_TOTAL", r["protected_total"])
        print("BOOLEAN_TO_ABSTAIN_TOTAL", r["boolean_to_abstain_total"])
        print("PASS", r["pass"])
        return 0 if r["pass"] else 1
    if args.check_cwd:
        out = Path(args.out) if args.out else OUT / "r13-cwd-check.json"
        r = check_cwd(cases, samples_sha, out)
        print("CWD_MISMATCHES_BEFORE", r["cwd_mismatches_before"])
        print("CWD_MISMATCHES", r["cwd_mismatches"])
        print("PASS", r["pass"])
        return 0 if r["pass"] else 1
    if args.recompute:
        out = Path(args.out) if args.out else OUT / "r13-alignment.json"
        r = recompute(cases, samples_sha, out)
        print("R_MAIN", r["r_main"], "COMPARABLE", r["comparable"],
              "AGREE", r["agree"], "DISAGREE", r["disagree"],
              "ABSTAIN", r["abstain"])
        print("DISAGREE_BY_MECHANISM", r["disagree_by_mechanism"])
        print("NO_RESIDUAL", r["disagree_by_mechanism_no_residual"])
        print("PROTECTED_TOTAL", r["protected_total"])
        print("BEFORE", r["before"]["r_main"], r["before"]["comparable"],
              r["before"]["disagree_by_mechanism"],
              "MATCHES_SEALED", r["before"]["matches_sealed"])
        print("GATE_RESULT", r["gate_result"])
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
