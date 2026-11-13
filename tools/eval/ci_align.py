#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""XJ-20261113-002 D5 / V10: alignment of the recompute with the historical CI.

Checks only what the frozen ci_align block permits: the recomputed paired
difference must fall inside the historical 95% CI [1.7, 11.2] at the *same*
aggregation level (claim). Being inside the CI is a consistency check, not a
replication and not a convergence conclusion: prohibition 2 forbids the word
复现 (replication) and forbids replacing the published 5.8 value; prohibition 5
forbids placing a PROVISIONAL recompute beside the historical value as a
convergence claim.

Only standard-library imports plus provenance_check helpers. CI is py3.9:
JSON is written through ``open(..., newline="")``.
"""

from __future__ import print_function

import argparse
import json
import os
import sys

import provenance_check as pc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--historical", type=float, default=None)
    ap.add_argument("--historical-ci", default="")
    ap.add_argument("--recompute", type=float, default=None)
    ap.add_argument("--aggregation", default="claim")
    ap.add_argument("--require-within-ci", action="store_true")
    ap.add_argument("--recompute-doc", default="out/m1-recompute.json")
    ap.add_argument("--out", default="out/ci-align.json")
    ap.add_argument("--prereg", default=pc.DEFAULT_PREREG)
    args = ap.parse_args(argv)

    rules = pc.load_frozen_block(args.prereg)
    cfg = rules["ci_align"]
    m1cfg = rules["m1"]
    if args.historical is None or args.recompute is None or not args.historical_ci:
        raise SystemExit("FATAL: --historical / --historical-ci / --recompute required")
    if abs(args.historical - cfg["historical"]) > 1e-9:
        raise SystemExit("FATAL: --historical %r diverges from frozen %r" %
                         (args.historical, cfg["historical"]))
    ci = [float(x) for x in args.historical_ci.split(",")]
    if len(ci) != 2 or any(abs(a - b) > 1e-9 for a, b in zip(ci, cfg["ci"])):
        raise SystemExit("FATAL: --historical-ci %r diverges from frozen %r" %
                         (ci, cfg["ci"]))
    if args.aggregation != m1cfg["aggregation"]:
        raise SystemExit("FATAL: aggregation %r != frozen %r; aggregation levels "
                         "must be aligned before any dual reading" %
                         (args.aggregation, m1cfg["aggregation"]))

    lower, upper = ci
    recompute = args.recompute
    within = lower <= recompute <= upper

    status = None
    recompute_doc_sha = None
    if os.path.isfile(args.recompute_doc):
        with open(args.recompute_doc, "r", encoding="utf-8", newline="") as f:
            rd = json.load(f)
        status = rd.get("status")
        recompute_doc_sha = pc.sha256_file(args.recompute_doc)
        if abs(rd.get("recompute", 0.0) - recompute) > 1e-6:
            raise SystemExit("FATAL: --recompute %r != m1-recompute.json value %r" %
                             (recompute, rd.get("recompute")))

    provisional = status == rules["x_7_3"]["provisional_label"]
    doc = {
        "schema": "r15-ci-align-v1",
        "card": "XJ-20261113-002",
        "frozen_in": "section 22 D22-E",
        "historical": args.historical,
        "historical_ci": ci,
        "historical_source": m1cfg["historical_source"],
        "recompute": recompute,
        "aggregation": args.aggregation,
        "aggregation_aligned": True,
        "within_ci": within,
        "require_within_ci": bool(args.require_within_ci),
        "recompute_status": status,
        "recompute_provisional": provisional,
        "recompute_doc_sha256": recompute_doc_sha,
        "dual_readings": [
            {"label": "historical", "value": args.historical,
             "aggregation": "claim", "source": m1cfg["historical_source"],
             "published": True},
            {"label": "convergent_recomputation", "value": recompute,
             "aggregation": "claim", "published": False,
             "status": status or "UNSPECIFIED"},
        ],
        "wording": m1cfg["wording"],
        "forbidden_wording": m1cfg["forbidden_wording"],
        "replication_wording_used": False,
        "replace_historical": m1cfg["replace_historical"],
        "convergence_claim_issued": False,
        "statement": (
            "复算值 %.6f pp 落在历史值 %s pp 的 95%% CI [%s, %s] 内（同为 claim 级）；"
            "此为区间一致性检查。%s 复算值仅表述为%s，不表述为%s，不替换已发表历史值，"
            "且%s" % (recompute, args.historical, lower, upper,
                    "PROVISIONAL " if provisional else "",
                    m1cfg["wording"], m1cfg["forbidden_wording"],
                    "因 X-7.3 未过门显式降级、不作收敛结论" if provisional
                    else "不作收敛结论")),
        "interpretation_limit": (
            "being inside a historical CI is not proof of replication: the "
            "recompute is a same-implementation replay (review Q4) and, on this "
            "host, PROVISIONAL because the sandbox gate is unsatisfied (review Q5)"),
    }
    if args.out:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        with open(args.out, "w", encoding="utf-8", newline="") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

    print("CI_ALIGN: historical=%s ci=[%s,%s] recompute=%.6f aggregation=%s "
          "within_ci=%s status=%s -> %s" %
          (args.historical, lower, upper, recompute, args.aggregation, within,
           status or "UNSPECIFIED",
           "PASS" if (within or not args.require_within_ci) else "FAIL"))
    print("WORDING: %s | forbidden='%s' used=False | replace_historical=False | "
          "convergence_claim_issued=False%s" %
          (m1cfg["wording"], m1cfg["forbidden_wording"],
           " | PROVISIONAL downgrade enforced" if provisional else ""))
    return 0 if (within or not args.require_within_ci) else 1


if __name__ == "__main__":
    sys.exit(main())
