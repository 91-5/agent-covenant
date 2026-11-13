#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""XJ-20261113-002 D3: FP_overall with a T*-false denominator (ADV-4 phase1).

F1 / P-4.4': the clean denominator is *all samples T* judged false*, never the
full 400 (true claims dilute it) and never the subset obtained by dropping
E0/E1 (that is selecting the denominator by the grader's own output, i.e.
sampling on the dependent variable). The numerator is the frozen rule
``main_level == "E4"`` restricted to that denominator.

P-4.5': Wilson 95% interval for the point estimate; coverage is
``(true + false) / sample_count`` read from truth-star.json, and when it is
below the frozen 0.70 threshold the output sets ``truth_coverage_gap = true``
instead of quietly reporting a precise-looking number off a small subset.

Prohibition 1: ``FP[anchor_miss] = 20%`` is a layer-internal conditional rate
from round 14. It is carried here with its scope label and an explicit
``never_extrapolate_as_overall_false_support_rate`` policy, and is NEVER used
as (or substituted for) this tool's point estimate.

Prohibition 4: no import of judge / rubric_v4 / independent_judge, directly or
transitively. Only the standard library plus ``external_truth`` (itself
standard-library only) are imported; the D2 closure audit verifies this.

CI is py3.9: JSON is written through ``open(..., newline="")``.
"""

from __future__ import print_function

import argparse
import collections
import json
import math
import os
import re
import sys

import external_truth as et

# Standard normal 97.5th percentile, frozen for a reproducible Wilson 95% CI.
Z_95 = 1.959963984540054


def wilson_95(successes, trials):
    """Return (point, lower, upper) for a binomial proportion."""
    if trials <= 0:
        return None, None, None
    p = successes / float(trials)
    z2 = Z_95 * Z_95
    denom = 1.0 + z2 / trials
    centre = (p + z2 / (2.0 * trials)) / denom
    margin = (Z_95 / denom) * math.sqrt(p * (1.0 - p) / trials +
                                        z2 / (4.0 * trials * trials))
    return p, max(0.0, centre - margin), min(1.0, centre + margin)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--truth", default="out/truth-star.json")
    ap.add_argument("--judgements", default="out/r11-reliability-rows.json")
    ap.add_argument("--out", default="out/fp-overall.json")
    ap.add_argument("--prereg", default=et.DEFAULT_PREREG)
    args = ap.parse_args(argv)

    rules = et.load_frozen_block(args.prereg)
    cfg = rules["fp_overall"]

    if cfg["ci_method"] != "wilson_95":
        raise SystemExit("FATAL: unsupported frozen ci_method %r" % cfg["ci_method"])
    # The frozen numerator is prose ("rows with Tstar=false whose
    # main_level == E4") rather than a JSON field, so accept both quoted and
    # bare level tokens instead of hardcoding a grader level in this module.
    m = re.search(r"main_level\s*==\s*\"?([A-Za-z0-9_]+)\"?", cfg["numerator"])
    if m is None:
        raise SystemExit("FATAL: cannot read numerator main_level from frozen block")
    numerator_level = m.group(1)

    # Input integrity: the judgement rows must be byte-identical to the frozen
    # sha, otherwise the join is against a different population.
    rows_sha = et.sha256_file(args.judgements)
    if rows_sha != rules["rows_sha256"]:
        raise SystemExit("FATAL: judgements sha256 %s != frozen %s" %
                         (rows_sha, rules["rows_sha256"]))
    with open(args.judgements, "r", encoding="utf-8", newline="") as f:
        rows_doc = json.load(f)
    rows = rows_doc["rows"] if isinstance(rows_doc, dict) else rows_doc
    by_case = dict((r["case_id"], r) for r in rows)

    with open(args.truth, "r", encoding="utf-8", newline="") as f:
        star = json.load(f)
    if star.get("schema") != "r15-truth-star-v1":
        raise SystemExit("FATAL: unexpected truth-star schema %r" % star.get("schema"))

    per_case = star["per_case"]
    missing = [r["case_id"] for r in per_case if r["case_id"] not in by_case]
    if missing:
        raise SystemExit("FATAL: %d truth-star cases absent from judgement rows "
                         "(first: %s)" % (len(missing), missing[0]))

    denominator = [r for r in per_case if r["tstar"] == "false"]
    numerator = [r for r in denominator
                 if by_case[r["case_id"]]["main_level"] == numerator_level]
    n = len(denominator)
    k = len(numerator)
    point, lower, upper = wilson_95(k, n)

    sample_count = star["total"]
    coverage = star["coverage"]
    gap_threshold = cfg["coverage_gap_threshold"]
    truth_coverage_gap = coverage < gap_threshold

    # Mechanical disclosure of what the denominator actually consists of:
    # T* can only falsify claims carrying a verifiable value position, so a
    # layer-homogeneous denominator is a limitation, not a hidden assumption.
    denom_layers = collections.Counter(r["layer"] for r in denominator)
    level_mix = collections.Counter(by_case[r["case_id"]]["main_level"]
                                    for r in denominator)
    excluded_e0_e1 = 0
    for r in rows:
        if r.get("main_level") in ("E0", "E1"):
            excluded_e0_e1 += 1

    doc = {
        "schema": "r15-fp-overall-v1",
        "card": "XJ-20261113-002",
        "frozen_in": "section 22 D22-E",
        "denominator_basis": cfg["denominator_basis_literal"],
        "denominator_basis_checked": cfg["denominator_basis_literal"] == "Tstar_false",
        "numerator_rule": cfg["numerator"],
        "numerator_level": numerator_level,
        "denominator": n,
        "numerator": k,
        "point": None if point is None else round(point, 6),
        "lower": None if lower is None else round(lower, 6),
        "upper": None if upper is None else round(upper, 6),
        "ci_95_wilson": [None if lower is None else round(lower, 6),
                         None if upper is None else round(upper, 6)],
        "ci_method": cfg["ci_method"],
        "z_95": Z_95,
        "coverage": coverage,
        "coverage_definition": cfg["coverage_definition"],
        "coverage_gap_threshold": gap_threshold,
        "truth_coverage_gap": truth_coverage_gap,
        "gap_literal": cfg["truth_coverage_gap_literal"] if truth_coverage_gap else None,
        "inputs": {
            "truth": args.truth,
            "judgements": args.judgements,
            "judgements_sha256": rows_sha,
            "truth_counts": star["counts"],
            "sample_count": sample_count,
        },
        "denominator_prohibitions": cfg["denominator_prohibitions"],
        "prohibited_bases_avoided": {
            "full_400": n != sample_count,
            "excluding_E0_E1": n != sample_count - excluded_e0_e1,
            "observed_E0_E1_rows": excluded_e0_e1,
        },
        "denominator_layer_composition": dict(denom_layers),
        "denominator_main_level_mix": dict(level_mix),
        "layer_conditional_fp_reference": cfg["layer_conditional_fp"],
        "scope_label": ("overall false-support rate conditional on T* being "
                        "judgeable and false; NOT a layer-internal rate"),
        "coverage_gap_statement": (
            "coverage %.6f < %.2f: %d of %d cases are UNJUDGEABLE and were "
            "excluded from true/false statistics (never defaulted to true or "
            "false). The T*-false denominator is therefore narrow; the point "
            "estimate and its interval describe only that judgeable-false "
            "subset and must not be read as a population-wide false-support "
            "rate." % (coverage, gap_threshold, star["counts"]["unjudgeable"],
                       sample_count)
        ) if truth_coverage_gap else (
            "coverage %.6f >= %.2f; no truth coverage gap flagged."
            % (coverage, gap_threshold)
        ),
        "interpretation_limits": [
            "review Q1: T* is a rule over generator-written text, not an "
            "independent human annotation (I-4.3-c=false)",
            "review Q3: if T* mislabels true claims as false, the denominator "
            "inflates and dilutes FP_overall; the denominator layer composition "
            "and the unjudgeable-reason breakdown are disclosed so this can be "
            "audited rather than assumed away",
            "prohibition 1: the round-14 FP[anchor_miss]=20% is layer-internal "
            "and is never extrapolated as this overall rate",
        ],
    }

    if args.out:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        with open(args.out, "w", encoding="utf-8", newline="") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

    print("FP_OVERALL: denominator_basis=%s n=%d k=%d point=%s ci95=[%s, %s] "
          "| coverage=%.6f %s=%s" %
          (doc["denominator_basis"], n, k, doc["point"], doc["lower"],
           doc["upper"], coverage, cfg["truth_coverage_gap_literal"],
           truth_coverage_gap))
    print("DENOMINATOR_LAYERS: %s" %
          json.dumps(doc["denominator_layer_composition"], sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
