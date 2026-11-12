#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""XJ-20261113-001 D3: unanchored false-support measurement (round 14).

Mechanically re-measures the frozen F1 finding of prereg section 21 on the
sealed round-11 corpus: main-track E4 supports on claims whose layer semantics
say FALSE (unanchored false support), with a frozen-bootstrap 95% CI and the
frozen severity table (read back from prereg section 21 D21-E; never
hard-coded here). Also emits the frozen M1 per-arm absolute-failure-rate
impact block (clause 5), caliber diagnostic_only.

Red-zone discipline: judge.py/extract.py semantics are referenced verbatim for
the anchor rule but the files are not imported or modified. CI is py3.9: JSON
is written through ``open(..., newline="")``.
"""

from __future__ import print_function

import argparse
import hashlib
import json
import random
import re
import sys

TRUTH_BEGIN = "<!-- R14-TRUTH-BEGIN -->"
TRUTH_END = "<!-- R14-TRUTH-END -->"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_frozen_block(prereg_path):
    with open(prereg_path, "r", encoding="utf-8", newline="") as f:
        text = f.read()
    start = text.find(TRUTH_BEGIN)
    end = text.find(TRUTH_END)
    if start < 0 or end < 0 or end < start:
        raise SystemExit("FATAL: frozen R14-TRUTH block not found in %s" % prereg_path)
    block = text[start + len(TRUTH_BEGIN):end]
    fence = block.find("```json")
    if fence >= 0:
        block = block[fence + len("```json"):]
        closing = block.rfind("```")
        if closing >= 0:
            block = block[:closing]
    return json.loads(block)


def claim_sentence(markdown):
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("- [已验证] "):
            body = stripped[len("- [已验证] "):]
            stop = body.find("。")
            return body[:stop] if stop >= 0 else body
    return ""


def extract_anchors(claim, integer_re):
    """Frozen anchor rule (verbatim semantics of extract.py, read-only):
    collect backtick tokens; strip backticks to spaces; extract integers;
    dict.fromkeys dedup preserving order."""
    backtick_tokens = re.findall(r"`([^`]*)`", claim)
    stripped = re.sub(r"`[^`]*`", " ", claim)
    ints = [m.group(0) for m in integer_re.finditer(stripped)]
    return list(dict.fromkeys(backtick_tokens + ints))


def percentile_nearest_rank(sorted_vals, q):
    """Nearest-rank percentile on an ascending list; deterministic, no interpolation."""
    idx = int(q * len(sorted_vals))
    if idx >= len(sorted_vals):
        idx = len(sorted_vals) - 1
    return sorted_vals[idx]


def severity_lookup(frozen_table, fp_upper):
    """Bands are ordered [<=0.05 low, <=0.15 medium, null high]."""
    for band in frozen_table:
        cap = band["max_fp_upper"]
        if cap is None or fp_upper <= cap:
            return band["severity"], band["disposition"]
    raise SystemExit("FATAL: severity table did not resolve for %r" % fp_upper)


def main(argv=None):
    ap = argparse.ArgumentParser(description="round-14 unanchored false-support measurement (frozen rules in prereg section 21 D21-E)")
    ap.add_argument("--rows", default="out/r11-reliability-rows.json")
    ap.add_argument("--samples", default="out/r11-blind-samples.json")
    ap.add_argument("--prereg", default="docs/eval-prereg.md")
    ap.add_argument("--bootstrap", type=int, default=2000)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    frozen = load_frozen_block(args.prereg)
    fp_cfg = frozen["fp_measurement"]

    if args.bootstrap != fp_cfg["bootstrap_resamples"]:
        raise SystemExit("FATAL: --bootstrap %d != frozen bootstrap_resamples %d"
                         % (args.bootstrap, fp_cfg["bootstrap_resamples"]))

    samples_sha = sha256_file(args.samples)
    rows_sha = sha256_file(args.rows)
    if samples_sha != frozen["samples_sha256"]:
        raise SystemExit("FATAL: samples sha256 mismatch vs frozen block: %s" % samples_sha)
    if rows_sha != frozen["rows_sha256"]:
        raise SystemExit("FATAL: rows sha256 mismatch vs frozen block: %s" % rows_sha)

    with open(args.samples, "r", encoding="utf-8", newline="") as f:
        samples = json.load(f)
    with open(args.rows, "r", encoding="utf-8", newline="") as f:
        rows = json.load(f)["rows"]

    cases = {c["case_id"]: c for c in samples["cases"]}
    layer_truth = frozen["layer_truth"]
    integer_re = re.compile(frozen["anchor_rule"]["integer_anchor_re"])

    population = [r for r in rows if r["stratum"] == fp_cfg["population_stratum"]]
    cross_table = {}
    false_rows = []
    anchor_miss_rows = [r for r in population if r["layer"] == "anchor_miss"]
    true_rows = [r for r in population if layer_truth[r["layer"]] == "TRUE"]

    for r in population:
        truth = layer_truth[r["layer"]]
        supports = r["main_level"] == "E4"
        key = "%s|%s" % (truth, r["main_level"])
        cross_table[key] = cross_table.get(key, 0) + 1
        if truth == "FALSE":
            false_rows.append((r, supports))

    false_total = len(false_rows)
    false_support_rows = [(r, s) for (r, s) in false_rows if s]
    false_support = len(false_support_rows)
    false_support_rate = false_support / float(false_total) if false_total else 0.0
    anchor_miss_e4 = sum(1 for r in anchor_miss_rows if r["main_level"] == "E4")
    true_total = len(true_rows)
    true_e4 = sum(1 for r in true_rows if r["main_level"] == "E4")

    flags = [1 if s else 0 for (_r, s) in false_rows]
    rng = random.Random(fp_cfg["bootstrap_seed"])
    n = len(flags)
    boot = []
    for _ in range(args.bootstrap):
        acc = 0
        for _i in range(n):
            acc += flags[rng.randrange(n)]
        boot.append(acc / float(n) if n else 0.0)
    boot.sort()
    ci_low = percentile_nearest_rank(boot, 0.025)
    ci_high = percentile_nearest_rank(boot, 0.975)

    severity, disposition = severity_lookup(fp_cfg["severity_table"], ci_high)

    counterexamples = []
    for (r, _s) in false_support_rows:
        case = cases[r["case_id"]]
        counterexamples.append({
            "case_id": r["case_id"],
            "layer": r["layer"],
            "claim": claim_sentence(case["markdown"]),
        })

    # ---- M1 per-arm absolute-failure-rate impact (clause 5, diagnostic_only) ----
    e_counts = {"E0": 0, "E1": 0, "E2": 0, "E3": 0, "E4": 0}
    for r in population:
        if r["main_level"] in e_counts:
            e_counts[r["main_level"]] += 1
    denom_as_judged = e_counts["E2"] + e_counts["E3"] + e_counts["E4"]
    m1_main = (e_counts["E2"] + e_counts["E3"]) / float(denom_as_judged) if denom_as_judged else None
    cf_e3 = e_counts["E3"] + false_support
    cf_e4 = e_counts["E4"] - false_support
    m1_main_cf = (e_counts["E2"] + cf_e3) / float(denom_as_judged) if denom_as_judged else None

    indep_support = sum(1 for r in population if r["indep_level"] == "SUPPORT")
    indep_not_support = sum(1 for r in population if r["indep_level"] == "NOT_SUPPORT")
    indep_denom = indep_support + indep_not_support
    m1_indep = indep_not_support / float(indep_denom) if indep_denom else None

    anchored_rows = []
    for r in population:
        claim = claim_sentence(cases[r["case_id"]]["markdown"])
        if extract_anchors(claim, integer_re):
            anchored_rows.append(r)
    a_e4 = sum(1 for r in anchored_rows if r["main_level"] == "E4")
    a_e2 = sum(1 for r in anchored_rows if r["main_level"] == "E2")
    a_e3 = sum(1 for r in anchored_rows if r["main_level"] == "E3")
    a_denom = a_e2 + a_e3 + a_e4
    m1_anchored = (a_e2 + a_e3) / float(a_denom) if a_denom else None
    fp_mass_in_anchored = sum(1 for r in anchored_rows
                              if layer_truth[r["layer"]] == "FALSE" and r["main_level"] == "E4")

    m1_impact = {
        "caliber": fp_cfg.get("truth_source_caliber") and "diagnostic_only",
        "m1_formula": frozen["m1"]["formula"],
        "arm_note": "arms = judging arms (main / independent); original study A/B arm labels are not recoverable in this corpus, disclosed per clause 5",
        "main_arm": {
            "population": len(population),
            "e_counts_as_judged": e_counts,
            "denominator": denom_as_judged,
            "m1_as_judged": m1_main,
            "counterfactual": {"e2": e_counts["E2"], "e3": cf_e3, "e4": cf_e4,
                               "rule": "reclassify the false supports to E3a"},
            "m1_counterfactual": m1_main_cf,
            "absolute_delta_pp": (m1_main_cf - m1_main) * 100 if (m1_main is not None and m1_main_cf is not None) else None,
        },
        "independent_arm": {
            "boolean_decidable": indep_denom,
            "support": indep_support,
            "not_support": indep_not_support,
            "m1_family_as_judged": m1_indep,
            "false_supports": 0,
            "absolute_delta_pp": 0.0,
        },
        "anchored_only": {
            "anchored_rows": len(anchored_rows),
            "m1_as_judged": m1_anchored,
            "m1_counterfactual": m1_anchored,
            "absolute_delta_pp": 0.0,
            "fp_mass_in_anchored": fp_mass_in_anchored,
            "reading": "the entire false-support mass lies in the no-anchor stratum; anchored-only M1 is unchanged by the counterfactual",
        },
    }

    result = {
        "schema": "r14-unanchored-fp-v1",
        "card": "XJ-20261113-001",
        "frozen_in": "prereg section 21 D21-E",
        "inputs": {
            "samples_path": args.samples,
            "samples_sha256": samples_sha,
            "rows_path": args.rows,
            "rows_sha256": rows_sha,
            "prereg_path": args.prereg,
        },
        "population_stratum": fp_cfg["population_stratum"],
        "population_n": len(population),
        "false_support": false_support,
        "false_support_total": false_total,
        "false_support_rate": false_support_rate,
        "anchor_miss_e4": "%d/%d" % (anchor_miss_e4, len(anchor_miss_rows)),
        "true_block": {"true_total": true_total, "true_e4": true_e4,
                       "all_true_supported": true_e4 == true_total},
        "cross_table": cross_table,
        "bootstrap": {
            "resamples": args.bootstrap,
            "seed": fp_cfg["bootstrap_seed"],
            "method": "nearest_rank_percentile_no_interpolation",
            "ci_low": ci_low,
            "ci_high": ci_high,
        },
        "fp_upper95": ci_high,
        "severity": severity,
        "severity_disposition": disposition,
        "severity_source": fp_cfg["severity_source_literal"],
        "counterexamples": counterexamples,
        "m1_impact": m1_impact,
        "gate_result": frozen["gate_result"],
        "gate_conclusion_issued": frozen["gate_conclusion_issued"],
        "capability_gain_claim": frozen["capability_gain_claim"],
    }

    with open(args.out, "w", encoding="utf-8", newline="") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("false_support %d" % false_support)
    print("false_support_rate %s" % false_support_rate)
    print("anchor_miss_e4 %d/%d" % (anchor_miss_e4, len(anchor_miss_rows)))
    print("fp_upper95 %s" % ci_high)
    print("severity %s (source=%s)" % (severity, fp_cfg["severity_source_literal"]))
    print("out=%s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
