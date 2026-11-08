#!/usr/bin/env python3
"""Round-7 agreement report (docs/eval-prereg.md §14; card XJ-20261108-003,
acceptance V5).

Per arm: claim alignment rate, level-agreement rate with a Wilson 95% CI plus
a product-level bootstrap CI (10000 resamples, seeded — deterministic), and
the per-predicate confusion matrix (predicate x agree/disagree counts). The
SHA-256 of THIS file is pre-registered in §14 as PREREG_REPORT_HASH
(acceptance V5); any byte changed after the freeze invalidates the round-7
run (pre-registration discipline: freeze -> offline replay -> data).

CLI:
    python tools/eval/report_agreement.py --split FILE [--bootstrap N]
        [--out FILE]

Exit codes: 0 ok; 2 usage.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path


def wilson_interval(successes: int, n: int, z: float = 1.959963984540054) -> Tuple[Optional[float], Optional[float]]:
    if n == 0:
        return (None, None)
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return (round(max(0.0, center - half), 4), round(min(1.0, center + half), 4))


def bootstrap_ci(per_product: dict, resamples: int) -> Tuple[Optional[float], Optional[float]]:
    products = []
    for code, p in per_product.items():
        if isinstance(p, dict) and "consistent_flags" in p:
            products.append(list(p["consistent_flags"].values()))
    if not products:
        return (None, None)
    rng = random.Random(20261108)
    rates = []
    for _ in range(resamples):
        s = n = 0
        for flags in (products[rng.randrange(len(products))] for _ in products):
            s += sum(1 for v in flags if v)
            n += len(flags)
        rates.append(s / n if n else 1.0)
    rates.sort()
    lo = rates[int(0.025 * len(rates))]
    hi = rates[min(len(rates) - 1, int(0.975 * len(rates)))]
    return (round(lo, 4), round(hi, 4))


def predicate_confusion(records: list, agrees_by_id: dict) -> dict:
    matrix = {}
    for r in records:
        cid = r.get("claim_id")
        if cid not in agrees_by_id:
            continue
        row = matrix.setdefault(r.get("predicate"), {"agree": 0, "disagree": 0})
        row["agree" if agrees_by_id[cid] else "disagree"] += 1
    return matrix


def build_report(split: dict, resamples: int) -> dict:
    report = {"schema_version": "v1.7", "bootstrap_resamples": resamples,
              "per_arm": {}}
    for arm in ("A", "B"):
        out = split["per_arm"][arm]
        t = out["totals"]
        pairs = {}
        for code, p in out["per_product"].items():
            if isinstance(p, dict) and "consistent_flags" in p:
                pairs.update(p["consistent_flags"])
        n = len(pairs)
        s = sum(1 for v in pairs.values() if v)
        wi = wilson_interval(s, n)
        boot = bootstrap_ci(out["per_product"], resamples)
        summary = split["summary"][arm]
        report["per_arm"][arm] = {
            "records": t["record_count"], "main_claims": t["main_claim_count"],
            "aligned_pairs": t["aligned_pairs"],
            "alignment_rate": t["alignment_rate"],
            "comparable_pairs": n,
            "consistent_pairs": s,
            "agreement_rate": (round(s / n, 4) if n else None),
            "wilson_95": wi, "bootstrap_95": boot,
            "invalid_rate": summary["invalid_rate"],
            "evaluative_share": summary["evaluative_share"],
            "predicate_confusion": predicate_confusion(
                split.get("records", {}).get(arm, []),
                {k: v for k, v in pairs.items()} if pairs else {}),
        }
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="round-7 agreement report (§14)")
    ap.add_argument("--split", default="shadow-r7/alignment-split.json")
    ap.add_argument("--bootstrap", type=int, default=10000)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    split = json.loads(Path(args.split).read_text(encoding="utf-8"))
    report = build_report(split, args.bootstrap)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="") as fh:
            fh.write(payload + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
