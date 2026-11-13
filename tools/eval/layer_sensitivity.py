#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""XJ-20261113-002 D3: extractor-implementation sensitivity sigma (ADV-4).

Recomputes the three-valued T* with two independently implemented value-position
extractors (frozen in section 22 D22-E: ``anchor_v1`` regex capture vs
``token_v2`` token enumeration), and reports the fraction of the 400 sealed
cases whose classification differs. sigma <= max_sigma (0.10) => exit 0.

A low sigma shows the "verbatim presence" check is stable across extractor
implementations; it does NOT prove T* is independent of the generator's text
(review Q1). Imports only the standard library plus external_truth (itself
standard-library only), so the D2 closure audit stays clean.

CI is py3.9: JSON is written through ``open(..., newline="")``.
"""

from __future__ import print_function

import argparse
import hashlib
import json
import os
import sys

import external_truth as et


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--extractor-a", default="anchor_v1")
    ap.add_argument("--extractor-b", default="token_v2")
    ap.add_argument("--max-sigma", type=float, default=None)
    ap.add_argument("--samples", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--prereg", default=et.DEFAULT_PREREG)
    args = ap.parse_args(argv)

    rules = et.load_frozen_block(args.prereg)
    sigma_cfg = rules["sigma"]
    max_sigma = args.max_sigma if args.max_sigma is not None else sigma_cfg["max_sigma"]
    if abs(max_sigma - sigma_cfg["max_sigma"]) > 1e-9:
        raise SystemExit("FATAL: --max-sigma %r diverges from frozen %r" %
                         (max_sigma, sigma_cfg["max_sigma"]))
    known = sorted(rules["tstar"]["extractors"].keys())
    for name in (args.extractor_a, args.extractor_b):
        if name not in known:
            raise SystemExit("FATAL: extractor %r not in frozen set %s" % (name, known))
    if args.extractor_a == args.extractor_b:
        raise SystemExit("FATAL: extractor-a and extractor-b must differ")

    samples_path = args.samples or rules["samples_path"]
    actual = et.sha256_file(samples_path)
    if actual != rules["samples_sha256"]:
        raise SystemExit("FATAL: samples sha256 %s != frozen %s" %
                         (actual, rules["samples_sha256"]))
    with open(samples_path, "r", encoding="utf-8", newline="") as f:
        samples = json.load(f)

    cases = samples["cases"]
    diffs = []
    counts_a = {"true": 0, "false": 0, "unjudgeable": 0}
    counts_b = {"true": 0, "false": 0, "unjudgeable": 0}
    for case in cases:
        ra = et.classify(case, args.extractor_a, rules)
        rb = et.classify(case, args.extractor_b, rules)
        counts_a[ra["value"]] += 1
        counts_b[rb["value"]] += 1
        if ra["value"] != rb["value"]:
            diffs.append({"case_id": case["case_id"], "layer": case["layer"],
                          "claim": et.claim_sentence(case.get("markdown", "")),
                          "a": ra["value"], "b": rb["value"],
                          "token_a": ra["value_token"], "token_b": rb["value_token"]})
    total = len(cases)
    sigma = len(diffs) / float(total) if total else 0.0
    doc = {
        "schema": "r15-layer-sensitivity-v1",
        "card": "XJ-20261113-002",
        "frozen_in": "section 22 D22-E",
        "definition": sigma_cfg["definition"],
        "scope": sigma_cfg["scope"],
        "extractor_a": args.extractor_a,
        "extractor_b": args.extractor_b,
        "extractor_a_description": rules["tstar"]["extractors"][args.extractor_a],
        "extractor_b_description": rules["tstar"]["extractors"][args.extractor_b],
        "total": total,
        "counts_a": counts_a,
        "counts_b": counts_b,
        "differing_cases": len(diffs),
        "sigma": round(sigma, 6),
        "max_sigma": max_sigma,
        "sigma_pass": sigma <= max_sigma,
        "differences": diffs,
        "interpretation_limit": (
            "low sigma = the verbatim-presence check is implementation-stable; "
            "it is not evidence of external independence, and both extractors "
            "are still rules over generator-written text (review Q1)"
        ),
    }
    if args.out:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        with open(args.out, "w", encoding="utf-8", newline="") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
    print("SIGMA: %.6f (differing %d / %d, max %.2f) -> %s | a=%s b=%s" %
          (sigma, len(diffs), total, max_sigma,
           "PASS" if doc["sigma_pass"] else "FAIL",
           json.dumps(counts_a, sort_keys=True), json.dumps(counts_b, sort_keys=True)))
    return 0 if doc["sigma_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
