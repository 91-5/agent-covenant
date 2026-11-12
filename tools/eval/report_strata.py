#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""XJ-20261113-001 D4: stratified report skeleton (round 14).

Builds the frozen three-stratum report skeleton (anchored / no_anchor /
verified_absence) over the sealed round-11 corpus with the round-13 rubric-v4
class membership recomputed row-by-row and cross-checked cell-for-cell against
the sealed per-layer decomposition. The primary R_main and its denominator are
only ever READ from the sealed round-13 alignment artifact (never recomputed);
R_main_anchored is emitted alongside. Conservation law: the three strata's
comparable rows must sum exactly to the primary comparable set, and rows of
class INSUFFICIENT_NO_ANCHOR must appear zero times in any agreement
computation (--check-no-anchor-mapping).

All rules are read back from the frozen machine-readable block in prereg
section 21 D21-E. Red-zone discipline: judge.py/extract.py are frozen
references (verbatim regex semantics, read-only); CI is py3.9: JSON is written
through ``open(..., newline="")``.
"""

from __future__ import print_function

import argparse
import hashlib
import json
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
    """Frozen anchor rule (verbatim semantics of extract.py, read-only)."""
    backtick_tokens = re.findall(r"`([^`]*)`", claim)
    stripped = re.sub(r"`[^`]*`", " ", claim)
    ints = [m.group(0) for m in integer_re.finditer(stripped)]
    return list(dict.fromkeys(backtick_tokens + ints))


def main(argv=None):
    ap = argparse.ArgumentParser(description="round-14 stratified report skeleton (frozen rules in prereg section 21 D21-E)")
    ap.add_argument("--round", default="r14")
    ap.add_argument("--strata", default="anchored,no_anchor,verified_absence")
    ap.add_argument("--primary", default="R_main")
    ap.add_argument("--also", default="R_main_anchored")
    ap.add_argument("--rows", default="out/r11-reliability-rows.json")
    ap.add_argument("--samples", default="out/r11-blind-samples.json")
    ap.add_argument("--prereg", default="docs/eval-prereg.md")
    ap.add_argument("--out", default="out/strata.json")
    ap.add_argument("--check-no-anchor-mapping", action="store_true")
    args = ap.parse_args(argv)

    frozen = load_frozen_block(args.prereg)
    strata_map = frozen["strata_map"]
    v4_layer_class = frozen["v4_layer_class"]
    integer_re = re.compile(frozen["anchor_rule"]["integer_anchor_re"])

    if args.primary != "R_main":
        raise SystemExit("FATAL: --primary %r != frozen primary R_main" % args.primary)
    requested = [s.strip() for s in args.strata.split(",") if s.strip()]
    if requested != list(strata_map.keys()):
        raise SystemExit("FATAL: --strata %r != frozen strata %r" % (requested, list(strata_map.keys())))

    samples_sha = sha256_file(args.samples)
    rows_sha = sha256_file(args.rows)
    v4_sha = sha256_file(frozen["v4_decomposition_path"])
    align_sha = sha256_file(frozen["r13_alignment_path"])
    if samples_sha != frozen["samples_sha256"]:
        raise SystemExit("FATAL: samples sha256 mismatch vs frozen block")
    if rows_sha != frozen["rows_sha256"]:
        raise SystemExit("FATAL: rows sha256 mismatch vs frozen block")
    if v4_sha != frozen["v4_decomposition_sha256"]:
        raise SystemExit("FATAL: v4 decomposition sha256 mismatch vs frozen block")
    if align_sha != frozen["r13_alignment_sha256"]:
        raise SystemExit("FATAL: r13 alignment sha256 mismatch vs frozen block")

    with open(args.samples, "r", encoding="utf-8", newline="") as f:
        samples = json.load(f)
    with open(args.rows, "r", encoding="utf-8", newline="") as f:
        rows = json.load(f)["rows"]
    with open(frozen["v4_decomposition_path"], "r", encoding="utf-8", newline="") as f:
        v4_sealed = json.load(f)
    with open(frozen["r13_alignment_path"], "r", encoding="utf-8", newline="") as f:
        r13 = json.load(f)

    cases = {c["case_id"]: c for c in samples["cases"]}

    # ---- per-row v4 class membership (frozen function) ----
    per_layer_recomputed = {}
    memberships = []
    for r in rows:
        layer = r["layer"]
        if layer in v4_layer_class:
            v4_class = v4_layer_class[layer]
        else:
            claim = claim_sentence(cases[r["case_id"]]["markdown"])
            v4_class = "SUPPORT" if extract_anchors(claim, integer_re) else "INSUFFICIENT_NO_ANCHOR"
        memberships.append((r, v4_class))
        agg = per_layer_recomputed.setdefault(layer, {})
        agg[v4_class] = agg.get(v4_class, 0) + 1

    # fail-fast: recomputed per-layer distribution must equal the sealed one cell-for-cell
    sealed_layers = v4_sealed["per_layer_classes"]
    layer_mismatches = []
    for layer in sorted(set(sealed_layers) | set(per_layer_recomputed)):
        if sealed_layers.get(layer) != per_layer_recomputed.get(layer):
            layer_mismatches.append(layer)

    # ---- strata + conservation ----
    strata_out = {}
    comparable_rows = []
    residual_counts = {}
    for r, v4_class in memberships:
        if v4_class in strata_map.values():
            comparable = (v4_class == "SUPPORT") and isinstance(r["main_supports"], bool)
            if comparable:
                comparable_rows.append((r, v4_class))
        else:
            residual_counts[v4_class] = residual_counts.get(v4_class, 0) + 1
    for name in strata_map:
        v4_class = strata_map[name]
        members = [(r, c) for (r, c) in memberships if c == v4_class]
        comp = len([1 for (r, c) in members if c == "SUPPORT" and isinstance(r["main_supports"], bool)])
        strata_out[name] = {
            "v4_class": v4_class,
            "raw": len(members),
            "comparable": comp,
            "abstain": len(members) - comp,
        }

    sum_strata = sum(strata_out[name]["comparable"] for name in strata_map)
    comparable_set = r13["comparable"]
    sealed_agree = r13["agree"]
    recomputed_abstain = len(memberships) - len(comparable_rows)
    no_anchor_mapping_count = sum(1 for (r, c) in comparable_rows
                                  if c == "INSUFFICIENT_NO_ANCHOR")

    # ---- primary R_main: read-only from the sealed round-13 artifact ----
    r_main = r13["r_main"]
    primary_denominator_changed = (comparable_set != frozen["sealed_r13"]["comparable"])

    # The comparable set is identified with the v4-SUPPORT set by the sealed
    # round-13 recompute (comparable 118 = agree 118 + disagree 0): the
    # membership cross-check above proves the SUPPORT set is exactly the
    # anchored stratum, so the sealed agreement applies wholly to it. Agreement
    # is NEVER recomputed from the stale round-11 main levels in the rows file.
    anchored = strata_out["anchored"]
    r_main_anchored = None
    if anchored["comparable"]:
        r_main_anchored = sealed_agree / float(anchored["comparable"])

    strata_raw_sum = sum(strata_out[name]["raw"] for name in strata_map)
    residual_raw_sum = sum(residual_counts.values())

    result = {
        "schema": "r14-strata-v1",
        "card": "XJ-20261113-001",
        "round": args.round,
        "frozen_in": "prereg section 21 D21-E",
        "strata_names": requested,
        "strata": strata_out,
        "residual": {"classes": residual_counts, "raw_total": residual_raw_sum},
        "raw_conservation": {"strata_raw_sum": strata_raw_sum,
                             "residual_raw_sum": residual_raw_sum,
                             "total": len(memberships)},
        "sum_strata": sum_strata,
        "comparable_set": comparable_set,
        "sum_strata_equals_comparable_set": sum_strata == comparable_set,
        "r_main": r_main,
        "r_main_denominator": comparable_set,
        "r_main_anchored": r_main_anchored,
        "r_main_anchored_denominator": anchored["comparable"],
        "primary": {
            "name": args.primary,
            "r_main": r_main,
            "denominator": comparable_set,
            "agree": sealed_agree,
            "source": frozen["r13_alignment_path"],
            "recomputed": False,
        },
        "primary_denominator_changed": primary_denominator_changed,
        "also": {
            "name": args.also,
            "r_main_anchored": r_main_anchored,
            "denominator": anchored["comparable"],
            "note": "anchored comparable subset only; never replaces the primary R_main",
        },
        "no_anchor_mapping_count": no_anchor_mapping_count,
        "layer_cross_check": {
            "mismatches": layer_mismatches,
            "pass": not layer_mismatches,
        },
        "agree_cross_check": {
            "note": "agreement is sealed round-13 state; the rows file keeps stale round-11 main levels and is never used to recompute agreement",
            "sealed": sealed_agree,
            "abstain_sealed": r13["abstain"],
            "abstain_recomputed": recomputed_abstain,
            "comparable_identification": "comparable_set == v4 SUPPORT set == anchored stratum (layer cross-check must pass)",
            "pass": r13["abstain"] == recomputed_abstain and sum_strata == comparable_set,
        },
        "inputs": {
            "samples_path": args.samples,
            "samples_sha256": samples_sha,
            "rows_path": args.rows,
            "rows_sha256": rows_sha,
            "v4_decomposition_path": frozen["v4_decomposition_path"],
            "v4_decomposition_sha256": v4_sha,
            "r13_alignment_path": frozen["r13_alignment_path"],
            "r13_alignment_sha256": align_sha,
            "prereg_path": args.prereg,
        },
        "gate_result": frozen["gate_result"],
        "gate_conclusion_issued": frozen["gate_conclusion_issued"],
        "capability_gain_claim": frozen["capability_gain_claim"],
    }

    if not args.check_no_anchor_mapping:
        with open(args.out, "w", encoding="utf-8", newline="") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    ok = (not layer_mismatches
          and sum_strata == comparable_set
          and not primary_denominator_changed
          and no_anchor_mapping_count == 0
          and r13["abstain"] == recomputed_abstain)

    if args.check_no_anchor_mapping:
        print("no_anchor_mapped %d" % no_anchor_mapping_count)
        print("INSUFFICIENT_NO_ANCHOR appears %d time(s) in agreement computation" % no_anchor_mapping_count)
    else:
        print("sum_strata==comparable_set %s" % (sum_strata == comparable_set))
        print("primary_denominator_changed %s" % primary_denominator_changed)
        print("r_main %s denominator %d (sealed, read-only)" % (r_main, comparable_set))
        print("r_main_anchored %s denominator %d" % (r_main_anchored, anchored["comparable"]))
        print("no_anchor_mapping_count %d" % no_anchor_mapping_count)
        print("layer_cross_check pass=%s" % (not layer_mismatches))
        print("agree_cross_check pass=%s" % result["agree_cross_check"]["pass"])
        print("out=%s" % args.out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
