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
 * The shadow track NEVER emits its own five-level sequence: the only
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
        [--workspace DIR] [--compile-report FILE] [--compiler-report FILE]
        [--out FILE] [--selftest]

 Both input files are JSON objects keyed by product code: ``{code: [...]}``
 (main = claim dicts as extract_claims().to_dict(); records = structured
 assertion records). Alignment runs per product, aggregated.

 ``--workspace`` is the v1.8 R1 switch (card XJ-20261110-001, §16): the C10
 rebuilt execution workspace the main track judged against. With it, criterion
 commands run with cwd=workspace and artifact paths resolve workspace-first /
 root-fallback, so both instruments read the same surface. Without it the
 behaviour is byte-identical to the pre-R1 instrument (cwd=root) — which is
 what the pre-R1 control run uses.

 Exit codes: 0 = ok; 1 = selftest failed or operational error; 2 = usage.
"""
from __future__ import annotations

import argparse
import json
import re
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

# E7 (council pre-merge supplement, cards XJ-20261110-001/002):
# Pre-registered observation ERROR classes.  Before this patch a criterion
# that failed because its artifact was invisible on the observation surface
# (wrong cwd, missing file, timeout, parse failure) was silently downgraded to
# ``predicate_ok=False`` -- i.e. "criterion not supported" -- and could enter
# the agreement denominator as a spurious agreement.  That is the root cause
# of the round-9 "coincidental agreement" (lost 102) and of the new false
# positives (gained 3).  These five classes are frozen here; the aligner now
# classifies such records explicitly and excludes them from comparable pairs
# unless the caller explicitly asks for the legacy behaviour.
OBSERVATION_ERROR_CLASSES = (
    "FILE_NOT_FOUND",
    "CWD_MISMATCH",
    "PARSE_FAIL",
    "TIMEOUT",
    "SILENT_FALLBACK",
)


def _criterion_targets(rec: dict) -> List[str]:
    """Cwd-sensitive files the criterion COMMAND depends on.

    Deliberately excludes ``artifact_path`` and ``command_artifact_created``
    expected values: those have a legal workspace-first / root-fallback
    resolution (§16 D16-2) and must not be reported as an observation error
    merely because they are absent from the command cwd."""
    cmd = str(rec.get("verification_command") or "")
    targets: List[str] = []
    targets += re.findall(r"python\s+([A-Za-z0-9_./-]+\.py)", cmd)
    targets += [m + ".py" for m in re.findall(
        r"from\s+([A-Za-z_]\w*)\s+import", cmd)]
    targets += re.findall(
        r"(?<![\w/\\])([A-Za-z0-9_][\w./-]*\.(?:py|txt|csv|json|md|log|dat))\b",
        cmd)
    seen, out = set(), []
    for t in targets:
        t = t.lstrip("./")
        if not t or t in seen or ".." in t.split("/"):
            continue
        seen.add(t)
        out.append(t)
    return out


def classify_observation_errors(records: List[dict], compiled: Dict[str, object],
                                root: Path,
                                workspace: Optional[Path] = None
                                ) -> Dict[str, dict]:
    """Classify observation failures using pre-registered ERROR classes.

    Scope is deliberately narrow: only records that would otherwise enter the
    agreement denominator as a *silent* "criterion not supported".  Structural
    buckets (not_applicable / evaluative / schema-invalid) already have their
    own accounting and are skipped.  A criterion that PASSED is never an
    observation error.  ``SILENT_FALLBACK`` marks the exact round-9 failure
    mode: the executor returned normally (no ``observation_failed`` flag) yet
    the criterion came back False because a command dependency was invisible.
    """
    results = {str(r.get("claim_id")): r
               for r in compiled.get("results", [])}
    surface = compiled.get("observation_surface", {}) or {}
    cwd = Path(str(surface.get("command_cwd") or root))
    faces: List[Path] = []
    for f in (cwd, Path(root),
              Path(workspace) if workspace is not None else None):
        if f is not None and f not in faces:
            faces.append(f)
    out: Dict[str, dict] = {}
    for rec in records:
        cid = str(rec.get("claim_id"))
        if rec.get("execution_status") == "not_applicable":
            continue
        if rec.get("claim_type") == DSL_EVALUATIVE_TYPE:
            continue
        res = results.get(cid, {}) or {}
        flags = list(res.get("flags") or [])
        detail = str(res.get("detail") or "")
        if "schema_invalid" in flags:
            continue  # already a syntax gap
        classes: List[str] = []
        if ("regex_timeout" in flags
                or ("observation_failed" in flags
                    and "timeout" in detail.lower())):
            classes.append("TIMEOUT")
        if ("parse_fail" in flags
                or "could not parse" in detail.lower()
                or "jsondecodeerror" in detail.lower()):
            classes.append("PARSE_FAIL")
        if res.get("predicate_ok") is False:
            targets = _criterion_targets(rec)
            visible_here = (any((cwd / t).is_file() for t in targets)
                            if targets else True)
            visible_elsewhere = (any((f / t).is_file()
                                     for f in faces for t in targets)
                                 if targets else False)
            if targets and not visible_here:
                classes.append("CWD_MISMATCH" if visible_elsewhere
                               else "FILE_NOT_FOUND")
                if "observation_failed" not in flags:
                    classes.append("SILENT_FALLBACK")
        if classes:
            ordered = [c for c in OBSERVATION_ERROR_CLASSES if c in classes]
            out[cid] = {"error_classes": ordered,
                        "error_class": ordered[0],
                        "command_cwd": str(cwd),
                        "targets": _criterion_targets(rec),
                        "detail": detail[:300],
                        "flags": flags}
    return out


def _align_product(main_claims: List[dict], records: List[dict],
                   compiled: Dict[str, object],
                   observation_errors: Optional[set] = None
                   ) -> Dict[str, object]:
    """One product's alignment accounting (no endpoint numbers).

    E7: ``observation_errors`` is the set of claim ids classified as
    observation failures.  Those pairs are reported explicitly and excluded
    from the agreement denominator instead of being silently graded as
    "criterion not supported".  ``None`` restores the pre-E7 behaviour and is
    only used by the explicit legacy switch."""
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

    # §14 D2 (v1.7): a non-evaluative record with no legal predicate is
    # EXPLICITLY uncompilable — the fallback default-grading is gone; such
    # records are counted (uncompilable_count) and excluded from the
    # agreement denominator, never silently graded.
    uncompilable = sorted({str(r.get("claim_id")) for r in records
                           if r.get("claim_type") != DSL_EVALUATIVE_TYPE
                           and not r.get("predicate")})
    syntax_gaps = sorted({str(r.get("claim_id")) for r in records
                          if "schema_invalid" in results.get(
                              str(r.get("claim_id")), {}).get("flags", [])})
    comparable: Dict[str, bool] = {}
    evaluative: List[str] = []
    not_applicable: List[str] = []
    semantic_gaps: List[str] = []
    observation_error_ids: List[str] = []
    for cid, main in aligned.items():
        result = results.get(cid, {})
        rec = next(r for r in records if str(r.get("claim_id")) == cid)
        level = main.get("level") or main.get("_level")
        if rec.get("execution_status") == "not_applicable":
            # §14 / docs/b-arm-notapplicable-rules.md: B-arm command_* records
            # are design-unexecutable — structural bucket, out of the agreement
            # denominator, never silently dropped
            not_applicable.append(cid)
            continue
        if observation_errors and cid in observation_errors:
            # E7: an observation failure is NOT a "criterion not supported".
            # It must never enter the agreement denominator.
            observation_error_ids.append(cid)
            continue
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
        "not_applicable_count": len(not_applicable),
        "not_applicable_ids": sorted(set(not_applicable)),
        "gaps": {
            "syntax": sorted(set(syntax_gaps)),
            "anchor": sorted(set(anchor_gaps)),
            "semantic": sorted(set(semantic_gaps)),
        },
        "consistent_flags": {cid: bool(v) for cid, v in sorted(comparable.items())},
        "observation_error_ids": sorted(set(observation_error_ids)),
        "anchor_gap_note": (f"record-side {len(anchor_gaps)}; "
                            f"main-side uncovered {len(uncovered_main)}"),
        "uncompilable_count": len(uncompilable),
        "uncompilable_ids": uncompilable,
    }


def align(main_by_code: Dict[str, List[dict]],
          records_by_code: Dict[str, List[dict]],
          root: Path, timeout: int = 30,
          workspace: Optional[Path] = None,
          fail_fast_observation: bool = True) -> Dict[str, object]:
    """Aggregate alignment over all products. The output carries no five-level
    sequence and no endpoint numbers — per-claim outputs are booleans and gap
    classes only (card D2 / §12 D4).

    v1.8 R1 (§16, card XJ-20261110-001): ``workspace`` is the C10 rebuilt
    execution workspace the main track judged against. With it, criterion
    commands run with cwd=workspace and artifact paths resolve
    workspace-first / root-fallback — the shadow track reads the same surface
    as the main track. Without it the behaviour is unchanged (cwd=root),
    which is what the pre-R1 control run uses.

    E7: ``fail_fast_observation`` (default True) classifies observation
    failures into the pre-registered OBSERVATION_ERROR_CLASSES and excludes
    those pairs from the agreement denominator.  Set it to False ONLY to
    reproduce historical sealed readings (--allow-silent-fallback); it does
    not change the frozen consistency rule itself."""
    per_product: Dict[str, Dict[str, object]] = {}
    all_errors: Dict[str, dict] = {}
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
        compiled = compile_records(records, root, timeout, workspace=workspace)
        per_claim_errors = (classify_observation_errors(
            records, compiled, root, workspace)
            if fail_fast_observation else {})
        all_errors.update(per_claim_errors)
        acc = _align_product(main_claims, records, compiled,
                             observation_errors=(set(per_claim_errors)
                                                 if fail_fast_observation else None))
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
        "note": ("shadow-track alignment only; no level-sequence, no endpoint "
                 "numbers, no rejudge (§12 D4 / C12)"),
        "observation_surface": {
            "root": str(root),
            "workspace": str(workspace) if workspace is not None else None,
            "command_cwd": (str(workspace) if workspace is not None else str(root)),
            "artifact_resolution": "workspace-first, root-fallback",
            "surface_mode": "r1-workspace" if workspace is not None else "pre-r1-root",
        },
        "totals": {**totals,
                   "alignment_rate": alignment_rate,
                   "agreement_rate": agreement_rate,
                   "agreement_gate": AGREEMENT_GATE},
        "observation_errors": {
            "enabled": fail_fast_observation,
            "pre_registered_classes": list(OBSERVATION_ERROR_CLASSES),
            "total": len(all_errors),
            "class_counts": {
                c: sum(1 for e in all_errors.values()
                       if c in e["error_classes"])
                for c in OBSERVATION_ERROR_CLASSES},
            "by_claim": {k: all_errors[k] for k in sorted(all_errors)},
            "note": ("观测失败不再静默降级为判据不支持；被分类的 pair 从 comparable 分母剔除并显式报类。"
                     "历史读数只在 --allow-silent-fallback 下复现，不用于新评审。"),
        },
        "per_product": per_product,
    }


def write_compile_report(path: Path, align_result: Dict[str, object],
                         records: List[dict],
                         base_report: Optional[Path] = None) -> Dict[str, object]:
    """Write the shadow compile-report (card D1: the report must record the
    observation ``cwd`` explicitly).

    The compiler-side metadata (compiler model, compilation notes) is carried
    over from ``base_report`` when given — the round-9 pass reuses the
    round-7 frozen primary-track compiler output, so its compiler identity is
    the round-7 one and must be disclosed, not re-invented. The observation
    surface block is always this run's own."""
    surface = align_result.get("observation_surface", {})
    totals = align_result.get("totals", {})
    payload: Dict[str, object] = {
        "schema_version": "v1.8",
        "record_count": len(records),
        "invalid_count": 0,
        "cwd": surface.get("command_cwd"),
        "root": surface.get("root"),
        "workspace": surface.get("workspace"),
        "observation_surface": surface,
        "notes": (
            "R1 观测面对齐（§16 D16-1/D16-2）：判据命令 cwd = workspace（C10 重建工作区，"
            "对齐主轨 judge.py:306），artifact_path workspace 优先 / root 兜底"
            "（对齐主轨 judge.py:274-289）。本报告显式记录 cwd 字段供验收 V4 机械核验。"
        ),
    }
    invalid = 0
    for code, product in align_result.get("per_product", {}).items():
        if isinstance(product, dict):
            invalid += len(product.get("gaps", {}).get("syntax", []) or [])
    payload["invalid_count"] = invalid
    payload["comparable_pairs"] = totals.get("comparable_pairs")
    payload["agreement_rate"] = totals.get("agreement_rate")
    payload["alignment_rate"] = totals.get("alignment_rate")
    obs = align_result.get("observation_errors", {}) or {}
    payload["fail_fast_observation"] = obs.get("enabled", True)
    payload["observation_error_total"] = obs.get("total", 0)
    payload["error_class_counts"] = obs.get("class_counts", {})
    if base_report is not None and base_report.is_file():
        base = json.loads(base_report.read_text(encoding="utf-8"))
        payload["compiler_model"] = base.get("compiler_model")
        payload["compiler_notes"] = base.get("notes")
        payload["compiler_report_source"] = str(base_report)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return payload


def run_goldset(gold_path: Path, root: Path, timeout: int = 30) -> Dict[str, object]:
    """§14 gold-set calibration (acceptance V7): for each hand-designated
    triple, compile the record, derive the aligner boolean, and compare with
    the designated expectation. Each triple evaluates in a FRESH temp root
    with its declared fixture files materialized (isolation: no cross-triple
    interference). Evaluative/uncompilable/not_applicable triples carry
    expect_consistent=null (own buckets, not in the agreement rate). No
    level token is emitted (the gold "level" field is consumed here and
    never echoed)."""
    import shutil

    rows = [json.loads(l) for l in gold_path.read_text(encoding="utf-8").splitlines()
            if l.strip()]
    meta = rows[0] if rows and "_meta" in rows[0] else {"_meta": {}}
    triples = [r for r in rows if "_meta" not in r]
    consistent = {}
    uncompilable = []
    not_applicable = []
    mismatches = []
    workdir = Path(tempfile.mkdtemp(prefix="goldset-"))
    try:
        for t in triples:
            cid = t["record"]["claim_id"]
            if t.get("expect_uncompilable"):
                uncompilable.append(cid)
                continue
            if t.get("expect_not_applicable") or t.get("expect_consistent") is None:
                not_applicable.append(cid)
                continue
            triple_root = workdir / cid
            triple_root.mkdir(parents=True, exist_ok=True)
            for name, content in (t.get("fixture", {}).get("files") or {}).items():
                p = triple_root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                with open(p, "w", encoding="utf-8", newline="") as fh:
                    fh.write(content)
            compiled = compile_records([t["record"]], triple_root, timeout)
            res = compiled["results"][0]
            ok = bool(res["predicate_ok"])
            agrees = ok == t["expect_consistent"]
            consistent[cid] = agrees
            if not agrees:
                mismatches.append({"claim_id": cid, "predicate_ok": ok,
                                   "detail": res.get("detail", "")[:120]})
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    n = len(consistent)
    rate = (round(sum(1 for v in consistent.values() if v) / n, 4) if n else None)
    return {
        "note": ("gold-set calibration; designated outcomes are hand-authored "
                 "independently of any judging run; no level token emitted"),
        "gold_version": meta.get("_meta", {}).get("gold_version"),
        "triples": len(triples),
        "comparable": n,
        "agreement_rate": rate,
        "threshold": 0.95,
        "gate": ("met" if rate is not None and rate >= 0.95 else "not met"),
        "uncompilable_ids": uncompilable,
        "not_applicable_ids": not_applicable,
        "mismatch_details": mismatches,
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
    ap.add_argument("--workspace", metavar="DIR", default=None,
                    help="v1.8 R1: C10 rebuilt execution workspace — criterion "
                         "commands run with cwd=workspace and artifact paths "
                         "resolve workspace-first / root-fallback (§16)")
    ap.add_argument("--compile-report", metavar="FILE", default=None,
                    help="write the shadow compile-report (records cwd)")
    ap.add_argument("--compiler-report", metavar="FILE", default=None,
                    help="compiler-side report whose metadata is carried over "
                         "into --compile-report (compiler identity disclosure)")
    ap.add_argument("--allow-silent-fallback", action="store_true",
                    help="DEPRECATED / replay-only: disable E7 fail-fast and "
                         "reproduce historical sealed readings that counted "
                         "observation failures as 'criterion not supported'. "
                         "Never use this for new evidence.")
    ap.add_argument("--out", metavar="FILE", help="write machine-readable JSON")
    ap.add_argument("--goldset", metavar="FILE",
                    help="section-14 gold-set calibration (acceptance V7)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()
    if args.goldset:
        result = run_goldset(Path(args.goldset), Path(args.root or "."))
        payload = json.dumps(result, ensure_ascii=False, indent=2)
        if args.out:
            with open(args.out, "w", encoding="utf-8", newline="") as fh:
                fh.write(payload + "\n")
        print(payload)
        return 0
    if not args.main or not args.records:
        ap.print_help()
        return 2
    main_by_code = json.loads(Path(args.main).read_text(encoding="utf-8"))
    records_by_code = json.loads(Path(args.records).read_text(encoding="utf-8"))
    workspace = Path(args.workspace) if args.workspace else None
    result = align(main_by_code, records_by_code, Path(args.root),
                   workspace=workspace,
                   fail_fast_observation=not args.allow_silent_fallback)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.compile_report:
        flat = [rec for recs in records_by_code.values() for rec in recs]
        report = write_compile_report(
            Path(args.compile_report), result, flat,
            Path(args.compiler_report) if args.compiler_report else None)
        print(f"compile-report -> {args.compile_report} "
              f"(cwd {report.get('cwd')})")
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="") as fh:
            fh.write(payload + "\n")
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
