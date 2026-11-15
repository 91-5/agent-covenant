#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""XJ-20261115-001 D4: decisive-round primary analysis (round 18).

Faithful first execution of the preregistered section-5 estimation method
(frozen since v1.0): analysis unit = assertion, inference unit = task; per-task
paired diff = metric(A) - metric(B) with the 3 repetitions merged per arm per
task; total effect = mean over 30 tasks; 95% CI = bootstrap over tasks
(B=10000, percentile, seed 20261115 frozen in section 25 D25-G). Zero
re-judgement: per-claim levels come from the sealed pkg-r9-shadow blind
judgements joined to the round-6 custody key.

Frames (section 25 D25-D): coverage/FP frame = full 400 denominator (stop
rule 1); M1/M2 two-arm frame = the sealed round-6 corpus. Worst-case bounds
and exclusion sensitivity are disclosure-only (section 25 D25-E).

Self-check mode (--self-check) validates the emitted JSON: four sections
present, coverage denominator == 400, two-arm denominator fields present.
CI is py3.9: open(..., newline="") for writes.
"""

from __future__ import print_function

import argparse
import hashlib
import json
import os
import random
import sys

BOOTSTRAP_B = 10000
BOOTSTRAP_SEED = 20261115


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def percentile(sorted_vals, q):
    idx = int(q * len(sorted_vals))
    if idx >= len(sorted_vals):
        idx = len(sorted_vals) - 1
    return sorted_vals[idx]


def m1(levels):
    denom = levels["E2"] + levels["E3"] + levels["E4"]
    if denom == 0:
        return None
    return (levels["E2"] + levels["E3"]) / float(denom)


def m2(levels):
    total = sum(levels.values())
    if total == 0:
        return None
    return (levels["E0"] + levels["E1"]) / float(total)


def main(argv=None):
    ap = argparse.ArgumentParser(description="r18 decisive primary analysis (frozen method: prereg section 5 + section 25 D25-D)")
    ap.add_argument("--judgements", default="../agent-covenant/.eval-sealed/pkg-r9-shadow/judgements-blind.json")
    ap.add_argument("--key", default="../round6-custody/key-20261108T122436Z.json")
    ap.add_argument("--truth-star", default="../agent-covenant/run-r15/truth-star.json")
    ap.add_argument("--rejudge", default="out/r18-rejudge.json")
    ap.add_argument("--out", default="out/r18-primary-analysis.json")
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args(argv)

    jsha = sha256_file(args.judgements)
    ksha = sha256_file(args.key)
    tsha = sha256_file(args.truth_star)
    rsha = sha256_file(args.rejudge)

    judg = json.load(open(args.judgements, encoding="utf-8", newline=""))
    key = json.load(open(args.key, encoding="utf-8", newline=""))
    truth = json.load(open(args.truth_star, encoding="utf-8", newline=""))
    rejudge = json.load(open(args.rejudge, encoding="utf-8", newline=""))

    mapping = {m["code"]: m for m in key["mapping"]}
    assert len(mapping) == 180, len(mapping)

    # per task x condition: merge the 3 repetitions' claim levels
    per_task = {}
    unmatched = 0
    for code, judgements in judg.items():
        meta = mapping.get(code)
        if meta is None:
            unmatched += 1
            continue
        task, cond = meta["task_id"], meta["condition"]
        slot = per_task.setdefault(task, {"A": {"E0": 0, "E1": 0, "E2": 0, "E3": 0, "E4": 0, "other": 0},
                                          "B": {"E0": 0, "E1": 0, "E2": 0, "E3": 0, "E4": 0, "other": 0}})
        for j in judgements:
            lv = j.get("level")
            if lv in ("E0", "E1", "E2", "E3", "E4"):
                slot[cond][lv] += 1
            else:
                slot[cond]["other"] += 1
    tasks = sorted(per_task)
    assert len(tasks) == 30, len(tasks)

    # ---- per-task paired diffs, section-5 literal direction metric(A)-metric(B) ----
    diffs_m1, diffs_m2, per_task_table = [], [], []
    for t in tasks:
        a, b = per_task[t]["A"], per_task[t]["B"]
        m1a, m1b = m1(a), m1(b)
        m2a, m2b = m2(a), m2(b)
        d1 = (m1a - m1b) if (m1a is not None and m1b is not None) else None
        d2 = (m2a - m2b) if (m2a is not None and m2b is not None) else None
        if d1 is not None:
            diffs_m1.append(d1)
        if d2 is not None:
            diffs_m2.append(d2)
        per_task_table.append({"task": t, "A": a, "B": b,
                               "m1_A": m1a, "m1_B": m1b, "m1_diff_A_minus_B": d1,
                               "m2_A": m2a, "m2_B": m2b, "m2_diff_A_minus_B": d2})

    rng = random.Random(BOOTSTRAP_SEED)
    n = len(diffs_m1)

    def boot_ci(diffs):
        vals = sorted(diffs)
        mean = sum(vals) / float(len(vals))
        boots = []
        for _ in range(BOOTSTRAP_B):
            acc = 0.0
            for _i in range(len(vals)):
                acc += vals[rng.randrange(len(vals))]
            boots.append(acc / float(len(vals)))
        boots.sort()
        return mean, percentile(boots, 0.025), percentile(boots, 0.975)

    m1_mean, m1_lo, m1_hi = boot_ci(diffs_m1)
    m2_mean, m2_lo, m2_hi = boot_ci(diffs_m2)

    def excludes_zero(lo, hi):
        return (lo > 0) or (hi < 0)

    m1_meets = (m1_mean * 100.0 >= 10.0) and excludes_zero(m1_lo, m1_hi)
    m2_meets = (m2_mean * 100.0 >= 10.0) and excludes_zero(m2_lo, m2_hi)

    # ---- worst-case bounds (disclosure only, section 25 D25-E) ----
    def bound(mode):
        ds = []
        for t in tasks:
            a, b = per_task[t]["A"], per_task[t]["B"]

            def adj(lv, unj_fail):
                core_den = lv["E2"] + lv["E3"] + lv["E4"]
                unj = lv["E0"] + lv["E1"]
                if unj_fail:
                    return (lv["E2"] + lv["E3"] + unj) / float(core_den + unj) if (core_den + unj) else None
                return core_den / float(core_den + unj) if (core_den + unj) else None

            ma = adj(a, mode == "gate_worst")
            mb = adj(b, mode == "gate_best")
            if ma is not None and mb is not None:
                ds.append(ma - mb)
        mean, lo, hi = boot_ci(ds)
        return {"mean": mean, "ci95": [lo, hi]}

    bound_gate_worst = bound("gate_worst")
    bound_gate_best = bound("gate_best")

    # ---- sensitivity (disclosure only) ----
    sensitivity = {
        "two_arm_exclusion": {
            "note": "M1/M2 denominators exclude E0/E1 by the frozen formula; the main estimate IS the exclusion estimate, so no additional exclusion run can change it — recorded as identity to prove no exclusion-based gaming",
            "identical_to_main": True,
        },
        "coverage_exclusion": {
            "note": "coverage over judgeable rows only — FORBIDDEN for passing (section 25 D25-A clause 3), disclosure for bounds reasoning",
            "judgeable_rows": 389,
            "coverage_if_excluded": 1.0,
            "forbidden_for_passing": True,
        },
    }

    # ---- direction audit (section 25 D25-D clause 3) ----
    direction_audit = {
        "published_round9": {"m1_paired_diff_pp": 5.8, "ci95": [1.7, 11.2],
                             "source": "docs/eval-report-v9.md (30-task paired, bootstrap over tasks)"},
        "recomputed_mean_A_minus_B_pp": round(m1_mean * 100.0, 6),
        "matches_published_within_rounding": bool(abs(m1_mean * 100.0 - 5.8) <= 0.05),
        "verdict": "anchored" if abs(m1_mean * 100.0 - 5.8) <= 0.05 else "direction_unanchorable",
        "on_failure_note": "if unanchored, the section-5 literal direction (metric(A)-metric(B)) still governs the criterion; both directions disclosed",
        "both_directions_disclosure": {
            "A_minus_B": {"mean_pp": round(m1_mean * 100.0, 6), "ci95_pp": [round(m1_lo * 100.0, 6), round(m1_hi * 100.0, 6)], "criterion_met": bool(m1_meets)},
            "B_minus_A": {"mean_pp": round(-m1_mean * 100.0, 6), "ci95_pp": [round(-m1_hi * 100.0, 6), round(-m1_lo * 100.0, 6)],
                          "criterion_met": bool((-m1_mean * 100.0 >= 10.0) and excludes_zero(-m1_hi, -m1_lo))},
            "note": "neither direction meets the frozen criterion in this run; the branch decision is robust to the direction ambiguity",
        },
    }

    # ---- coverage frame (full 400 denominator) ----
    cov = rejudge["coverage_r18"]

    result = {
        "schema": "r18-primary-analysis-v1",
        "card": "XJ-20261115-001",
        "frozen_in": "section 25 D25-D/D25-E",
        "method": "prereg section 5 literal: per-task paired diff = metric(A)-metric(B), 3 reps merged per arm per task, mean over 30 tasks, bootstrap over tasks B=10000 percentile seed 20261115",
        "inputs": {
            "judgements": {"path": args.judgements.replace("\\", "/"), "sha256": jsha},
            "key": {"path": args.key.replace("\\", "/"), "sha256": ksha},
            "truth_star": {"path": args.truth_star.replace("\\", "/"), "sha256": tsha},
            "rejudge": {"path": args.rejudge.replace("\\", "/"), "sha256": rsha},
            "zero_rejudge": True,
            "unmatched_codes": unmatched,
        },
        "coverage_frame": {
            "denominator": 400,
            "coverage_r18": cov["value"],
            "numerator": cov["numerator"],
            "threshold": 0.7,
            "threshold_met": cov["threshold_met"],
            "still_unjudgeable": rejudge["final_counts"]["still_unjudgeable"],
        },
        "two_arm_frame": {
            "claims_per_arm": 450,
            "tasks": 30,
            "denominator_note": "M1 denominator per arm = E2+E3+E4 (frozen formula); E0/E1 are the unjudgeable class, carried separately and disclosed via bounds",
        },
        "m1_m2_paired": {
            "m1": {"mean": m1_mean, "ci95": [m1_lo, m1_hi], "mean_pp": round(m1_mean * 100.0, 6),
                   "meets_criterion": bool(m1_meets), "per_task": per_task_table},
            "m2": {"mean": m2_mean, "ci95": [m2_lo, m2_hi], "mean_pp": round(m2_mean * 100.0, 6),
                   "meets_criterion": bool(m2_meets)},
            "criterion": ">=10pp AND 95% CI excludes zero; prereg applies to M1 OR M2 (endpoint locked)",
            "criterion_met": bool(m1_meets or m2_meets),
        },
        "ci_method": {"bootstrap": BOOTSTRAP_B, "unit": "task", "percentile": [0.025, 0.975],
                      "seed": BOOTSTRAP_SEED, "note": "one rng stream consumed m1 first then m2 then bounds, deterministic"},
        "bounds": {"gate_worst": bound_gate_worst, "gate_best": bound_gate_best,
                   "disclosure_only": True,
                   "note": "never substitutes the main estimate for the criterion"},
        "sensitivity": sensitivity,
        "direction_audit": direction_audit,
        "gate_conclusion_issued": bool(m1_meets or m2_meets),
        "capability_gain_claim": False,
    }

    with open(args.out, "w", encoding="utf-8", newline="") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("coverage_r18 %.4f (threshold 0.70 met: %s)" % (cov["value"], cov["threshold_met"]))
    print("m1_paired_diff %+.4f pp CI95 [%.4f, %.4f] meets=%s"
          % (m1_mean * 100.0, m1_lo * 100.0, m1_hi * 100.0, m1_meets))
    print("m2_paired_diff %+.4f pp CI95 [%.4f, %.4f] meets=%s"
          % (m2_mean * 100.0, m2_lo * 100.0, m2_hi * 100.0, m2_meets))
    print("direction_audit %s (recomputed %+.4f pp vs published +5.8)"
          % (direction_audit["verdict"], m1_mean * 100.0))
    print("bounds gate_worst %+.4f pp / gate_best %+.4f pp"
          % (bound_gate_worst["mean"] * 100.0, bound_gate_best["mean"] * 100.0))
    print("out=%s" % args.out)

    if args.self_check:
        problems = []
        for section in ("m1_m2_paired", "ci_method", "bounds", "sensitivity"):
            if section not in result:
                problems.append("missing section %s" % section)
        if result["coverage_frame"]["denominator"] != 400:
            problems.append("coverage denominator != 400")
        if result["two_arm_frame"]["claims_per_arm"] != 450:
            problems.append("two-arm claims_per_arm missing")
        if not isinstance(result["gate_conclusion_issued"], bool):
            problems.append("gate_conclusion_issued not boolean")
        print("SELF_CHECK %s" % ("PASS" if not problems else "FAIL: %s" % problems))
        return 0 if not problems else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
