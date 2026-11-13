#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""XJ-20261113-002 D5: M1 recomputation (ADV-7), gated by X-7.3.

F4 records a deterministic judge.py recomputation of the round-6 corpus:
A E1=60/E2=195/E3=120/E4=75, B E1=60/E2=168/E3=123/E4=99. No sealed
judgement table with that exact level sequence exists in this repository
(round-6 = 180 products, 450 claims per arm, verified against
shadow-r6/alignment-split.json), and this host has no sandbox in which to
safely re-execute the 900 evidence commands. Accordingly this tool does NOT
fake a re-grade: it re-derives M1 arithmetically from those *recorded* level
counts using the frozen formula, cross-checks the corpus structure, and
inherits the X-7.3 verdict from replay_guard.py.

Consequences, all disclosed in the output and in the report:
  * the value is a 收敛性重算 / convergent recomputation, never 复现;
  * it is a same-implementation replay, not an independent recomputation
    (review Q4);
  * with any X-7.3 gate unsatisfied it is labelled PROVISIONAL and explicitly
    downgraded -- it is never placed beside the historical value as a
    convergence conclusion (prohibition 5, review Q5);
  * it never replaces the published historical value (prohibition 2).

The frozen formula string is parsed, not hardcoded. Only standard-library
imports plus provenance_check helpers. CI is py3.9: JSON is written through
``open(..., newline="")``.
"""

from __future__ import print_function

import argparse
import collections
import json
import os
import re
import sys

import provenance_check as pc


def parse_formula(formula):
    """Parse '(E2+E3)/(E2+E3+E4)' into (numerator_levels, denominator_levels)."""
    parts = formula.replace(" ", "").split("/")
    if len(parts) != 2:
        raise SystemExit("FATAL: unparseable frozen M1 formula %r" % formula)
    num = re.findall(r"E\d+", parts[0])
    den = re.findall(r"E\d+", parts[1])
    if not num or not den:
        raise SystemExit("FATAL: frozen M1 formula has no E-levels: %r" % formula)
    return num, den


def arm_metric(counts, num_levels, den_levels):
    num = sum(counts.get(l, 0) for l in num_levels)
    den = sum(counts.get(l, 0) for l in den_levels)
    if den <= 0:
        raise SystemExit("FATAL: empty M1 denominator")
    return {"levels": dict(counts), "numerator": num, "denominator": den,
            "m1": num / float(den)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--levels", default="out/m1-level-counts.json")
    ap.add_argument("--guard", default="out/replay-guard.json")
    ap.add_argument("--custody", default="")
    ap.add_argument("--out", default="out/m1-recompute.json")
    ap.add_argument("--prereg", default=pc.DEFAULT_PREREG)
    args = ap.parse_args(argv)

    rules = pc.load_frozen_block(args.prereg)
    m1cfg = rules["m1"]
    x73 = rules["x_7_3"]
    num_levels, den_levels = parse_formula(m1cfg["formula"])

    with open(args.levels, "r", encoding="utf-8", newline="") as f:
        levels = json.load(f)
    with open(args.guard, "r", encoding="utf-8", newline="") as f:
        guard = json.load(f)

    custody, _ = pc.resolve_custody(args.custody or
                                    rules["provenance"]["custody_arg"], rules)
    cross = {}
    if custody:
        split = os.path.join(custody, "shadow-r6", "alignment-split.json")
        if os.path.isfile(split):
            with open(split, "r", encoding="utf-8", newline="") as f:
                d = json.load(f)
            cross["alignment_split_claim_counts"] = {
                arm: d["per_arm"][arm]["totals"]["record_count"]
                for arm in ("A", "B") if arm in d.get("per_arm", {})}
        rd = os.path.join(custody, "run-dir-r6", "run-data.json")
        if os.path.isfile(rd):
            with open(rd, "r", encoding="utf-8", newline="") as f:
                entries = json.load(f)["entries"]
            cross["products"] = len(entries)
            cross["condition_counts"] = dict(collections.Counter(
                e["condition"] for e in entries))

    arms = {}
    for arm in ("A", "B"):
        counts = levels[arm]
        arms[arm] = arm_metric(counts, num_levels, den_levels)
        total_claims = sum(counts.values())
        expected = cross.get("alignment_split_claim_counts", {}).get(arm)
        arms[arm]["total_claims"] = total_claims
        arms[arm]["total_claims_matches_sealed_split"] = (
            None if expected is None else total_claims == expected)
        if arms[arm]["denominator"] != m1cfg["n_per_arm"]:
            raise SystemExit("FATAL: arm %s denominator %d != frozen n_per_arm %d" %
                             (arm, arms[arm]["denominator"], m1cfg["n_per_arm"]))

    diff_pp = (arms["A"]["m1"] - arms["B"]["m1"]) * 100.0
    gates_ok = bool(guard.get("all_gates_satisfied"))
    provisional = not gates_ok
    doc = {
        "schema": "r15-m1-recompute-v1",
        "card": "XJ-20261113-002",
        "frozen_in": "section 22 D22-E",
        "formula": m1cfg["formula"],
        "numerator_levels": num_levels,
        "denominator_levels": den_levels,
        "aggregation": m1cfg["aggregation"],
        "n_per_arm": m1cfg["n_per_arm"],
        "arms": arms,
        "recompute": round(diff_pp, 6),
        "recompute_pp": round(diff_pp, 6),
        "historical": m1cfg["historical"],
        "historical_ci": m1cfg["historical_ci"],
        "historical_source": m1cfg["historical_source"],
        "historical_aggregation_label": "历史第 9 轮配对差，claim 级，已发表值",
        "recompute_aggregation_label": "本轮收敛性重算，claim 级，n=%d/臂" %
                                       m1cfg["n_per_arm"],
        "status": x73["provisional_label"] if provisional else "RECOMPUTED",
        "provisional": provisional,
        "downgrade_required": bool(guard.get("downgrade_required")),
        "failed_gates": guard.get("failed_gates", []),
        "wording": m1cfg["wording"],
        "forbidden_wording": m1cfg["forbidden_wording"],
        "replication_wording_used": False,
        "replace_historical": m1cfg["replace_historical"],
        "convergence_claim_issued": False,
        "recompute_mode": (
            "arithmetic re-derivation from the F4-recorded deterministic "
            "judge.py level counts, cross-checked against the sealed 180-product "
            "/ 450-claims-per-arm corpus; judge.py was NOT re-executed on bare "
            "metal because no sandbox/isolation proof exists (review Q4/Q5). "
            "This is a same-implementation replay, not an independent recompute."),
        "level_counts_source": levels.get("source"),
        "level_counts_sha256": pc.sha256_file(args.levels),
        "guard_sha256": pc.sha256_file(args.guard),
        "custody_resolved": custody or None,
        "corpus_cross_check": cross,
        "dual_reading_statement": (
            "历史值 %s pp（claim 级，已发表）与复算值 %.6f pp（claim 级，%s）"
            "并列报出；因 X-7.3 未过门，复算值显式降级，不作收敛结论，不替换"
            "历史值。" % (m1cfg["historical"], diff_pp,
                        x73["provisional_label"] if provisional else "RECOMPUTED")),
    }
    if args.out:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        with open(args.out, "w", encoding="utf-8", newline="") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

    print("M1_RECOMPUTE: A=%.6f (%d/%d) B=%.6f (%d/%d) diff_pp=%.6f "
          "aggregation=%s status=%s" %
          (arms["A"]["m1"], arms["A"]["numerator"], arms["A"]["denominator"],
           arms["B"]["m1"], arms["B"]["numerator"], arms["B"]["denominator"],
           diff_pp, m1cfg["aggregation"], doc["status"]))
    print("DUAL_READING: historical=%s %s | recompute=%.6f %s | "
          "downgrade_required=%s wording=%s" %
          (m1cfg["historical"], doc["historical_aggregation_label"], diff_pp,
           doc["recompute_aggregation_label"], doc["downgrade_required"],
           m1cfg["wording"]))
    print("GATES: failed=%s -> %s (never claim convergence)" %
          (",".join(doc["failed_gates"]) or "(none)", doc["status"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
