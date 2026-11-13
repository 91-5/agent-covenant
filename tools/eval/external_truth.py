#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""XJ-20261113-002 D3: three-valued external truth T* (ADV-4 phase1).

Reads the frozen ``R15-TRUTH`` block (section 22 D22-E) and the sealed r11
blind samples, then mechanically classifies each claim as ``true`` / ``false`` /
``unjudgeable`` from generator-written text only: the claim sentence, the
recorded ``out=`` / ``exit=`` surface, and the fixture file contents.

Prohibition 4 / C-4.1: this module and every transitive dependency must NOT
import ``judge``, ``rubric_v4`` or ``independent_judge``. It imports only the
standard library; the D2 import-closure audit verifies the whole closure.
UNJUDGEABLE rows are excluded from true/false statistics and their coverage is
disclosed (prohibition 6). No grader output (E-level, anchors, abstention
classes) is ever read.

Two modes:
  --samples ... --out ...                  produce truth-star.json (V3)
  --compare ... --layer-out ... --min-delta ...   re-derive layer truth, compute
                                                  agreement delta (V4)

CI is py3.9: JSON is written through ``open(..., newline="")``.
"""

from __future__ import print_function

import argparse
import hashlib
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple  # noqa: F401

TRUTH_BEGIN = "<!-- R15-TRUTH-BEGIN -->"
TRUTH_END = "<!-- R15-TRUTH-END -->"
DEFAULT_PREREG = "docs/eval-prereg.md"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_frozen_block(prereg_path=DEFAULT_PREREG):
    with open(prereg_path, "r", encoding="utf-8", newline="") as f:
        text = f.read()
    start = text.find(TRUTH_BEGIN)
    end = text.find(TRUTH_END)
    if start < 0 or end < 0 or end < start:
        raise SystemExit("FATAL: frozen R15-TRUTH block not found in %s" % prereg_path)
    block = text[start + len(TRUTH_BEGIN):end]
    fence = block.find("```json")
    if fence >= 0:
        block = block[fence + len("```json"):]
        closing = block.rfind("```")
        if closing >= 0:
            block = block[:closing]
    return json.loads(block)


def claim_sentence(markdown):
    """Frozen rule: first line starting '- [已验证] ' up to the first '。'."""
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("- [已验证] "):
            body = stripped[len("- [已验证] "):]
            stop = body.find("。")
            return body[:stop] if stop >= 0 else body
    return ""


def evidence_surface(case, rules):
    """Return (surface_or_None, kind). Frozen evidence-surface definition.

    cmd: recorded ``out=`` content plus the literal ``exit=N`` token.
    ref: fixtures_workspace[ref] / fixtures_root[ref] content iff present.
    none: no evidence line, incomplete fields, or ref absent from both maps.
    """
    md = case.get("markdown", "")
    ev = None
    for line in md.splitlines():
        if "证据：" in line:
            ev = line.split("证据：", 1)[1].strip()
            break
    if not ev:
        return None, "none"
    if ev.startswith("cmd="):
        m = re.search(r"out=`([^`]*)`", ev)
        if m is None:
            return None, "cmd_incomplete"
        x = re.search(r"exit=(-?\d+)", ev)
        surface = m.group(1)
        if x:
            surface += "exit=" + x.group(1)
        return surface, "cmd"
    if ev.startswith("ref="):
        m = re.search(r"ref=`([^`]*)`", ev)
        if m is None:
            return None, "ref_incomplete"
        key = m.group(1)
        fw = case.get("fixtures_workspace", {}) or {}
        fr = case.get("fixtures_root", {}) or {}
        if key in fw:
            return str(fw[key]), "ref_workspace"
        if key in fr:
            return str(fr[key]), "ref_root"
        return None, "ref_absent"
    return None, "incomplete_fields"


def value_token(claim, extractor, rules):
    """Return the verifiable value-position token, or None."""
    if extractor == "anchor_v1":
        m = re.search(rules["tstar"]["value_position_re"], claim)
        return m.group(1) if m else None
    if extractor == "token_v2":
        tokens = re.findall(r"[0-9A-Za-z][0-9A-Za-z.\-_+]*", claim)
        kept = [t for t in tokens if not re.match(r"^T\d+$", t)]
        return kept[-1] if kept else None
    raise SystemExit("FATAL: unknown extractor %r (frozen extractors: %s)" %
                     (extractor, ",".join(sorted(rules["tstar"]["extractors"].keys()))))


def classify(case, extractor, rules):
    claim = claim_sentence(case.get("markdown", ""))
    surface, kind = evidence_surface(case, rules)
    token = value_token(claim, extractor, rules)
    if surface is None:
        return {"value": "unjudgeable", "reason": "evidence_surface_unavailable",
                "value_token": token, "surface_kind": kind}
    if token is None:
        return {"value": "unjudgeable", "reason": "no_verifiable_value_position",
                "value_token": None, "surface_kind": kind}
    if token in surface:
        return {"value": "true", "reason": "value_token_in_evidence_surface",
                "value_token": token, "surface_kind": kind}
    return {"value": "false", "reason": "value_token_absent_from_evidence_surface",
            "value_token": token, "surface_kind": kind}


def build_truth_star(samples, samples_sha, rules):
    cases = samples["cases"]
    rows = []
    counts = {"true": 0, "false": 0, "unjudgeable": 0}
    for case in cases:
        r = classify(case, "anchor_v1", rules)
        counts[r["value"]] += 1
        rows.append({
            "case_id": case["case_id"],
            "layer": case["layer"],
            "stratum": case["stratum"],
            "claim": claim_sentence(case.get("markdown", "")),
            "tstar": r["value"],
            "reason": r["reason"],
            "value_token": r["value_token"],
            "surface_kind": r["surface_kind"],
        })
    total = len(cases)
    judgeable = counts["true"] + counts["false"]
    by_layer = {}
    for row in rows:
        slot = by_layer.setdefault(row["layer"],
                                   {"true": 0, "false": 0, "unjudgeable": 0})
        slot[row["tstar"]] += 1
    reasons = {}
    for row in rows:
        if row["tstar"] == "unjudgeable":
            reasons[row["reason"]] = reasons.get(row["reason"], 0) + 1
    doc = {
        "schema": "r15-truth-star-v1",
        "card": "XJ-20261113-002",
        "frozen_in": "section 22 D22-E",
        "inputs": {
            "samples": rules["samples_path"],
            "samples_sha256": samples_sha,
            "sample_count": total,
        },
        "values": ["true", "false", "unjudgeable"],
        "counts": counts,
        "true": counts["true"],
        "false": counts["false"],
        "unjudgeable": counts["unjudgeable"],
        "total": total,
        "judgeable": judgeable,
        "coverage": round(judgeable / float(total), 6),
        "by_layer": by_layer,
        "unjudgeable_reasons": reasons,
        "unjudgeable_disposition": rules["tstar"]["unjudgeable_disposition"],
        "externality_declaration": (
            "reads only generator-written claim text, recorded out=/exit= and "
            "fixture contents; no grader imports, no E-level/anchor/abstention "
            "concepts; NOT an independent human annotation (I-4.3-c=false)"
        ),
        "per_case": rows,
    }
    return doc


def build_layer_truth(truth_star, rules):
    table = rules["delta"]["layer_truth_table"]
    rows = []
    for r in truth_star["per_case"]:
        raw = table.get(r["layer"])
        rows.append({"case_id": r["case_id"], "layer": r["layer"],
                     "layer_truth": (raw or "UNKNOWN").lower()})
    return {
        "schema": "r15-layer-truth-v1",
        "card": "XJ-20261113-002",
        "source": rules["delta"]["layer_truth_source"],
        "layer_truth_table": table,
        "per_case": rows,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--samples", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--compare", default="", help="truth-star.json for delta mode")
    ap.add_argument("--layer-out", default="", help="path to write re-derived layer truth")
    ap.add_argument("--delta-out", default="", help="path to persist the delta report")
    ap.add_argument("--min-delta", type=float, default=None)
    ap.add_argument("--prereg", default=DEFAULT_PREREG)
    args = ap.parse_args(argv)

    rules = load_frozen_block(args.prereg)

    if args.compare:
        with open(args.compare, "r", encoding="utf-8", newline="") as f:
            star = json.load(f)
        min_delta = args.min_delta if args.min_delta is not None else rules["delta"]["min_delta"]
        if abs(min_delta - rules["delta"]["min_delta"]) > 1e-9:
            raise SystemExit("FATAL: --min-delta %r diverges from frozen block %r" %
                             (min_delta, rules["delta"]["min_delta"]))
        layer = build_layer_truth(star, rules)
        if args.layer_out:
            out_dir = os.path.dirname(os.path.abspath(args.layer_out))
            if out_dir and not os.path.isdir(out_dir):
                os.makedirs(out_dir)
            with open(args.layer_out, "w", encoding="utf-8", newline="") as f:
                json.dump(layer, f, ensure_ascii=False, indent=2)
        lt = dict((r["case_id"], r["layer_truth"]) for r in layer["per_case"])
        comparable = [r for r in star["per_case"] if r["tstar"] in ("true", "false")]
        agree = [r for r in comparable if lt.get(r["case_id"]) == r["tstar"]]
        delta = len(agree) / float(len(comparable)) if comparable else 0.0
        doc = {
            "schema": "r15-delta-v1",
            "card": "XJ-20261113-002",
            "definition": rules["delta"]["definition"],
            "scope": rules["delta"]["scope"],
            "comparable_rows": len(comparable),
            "agree": len(agree),
            "delta": round(delta, 6),
            "min_delta": min_delta,
            "delta_pass": delta >= min_delta,
            "disagreements": [
                {"case_id": r["case_id"], "layer": r["layer"],
                 "tstar": r["tstar"], "layer_truth": lt.get(r["case_id"])}
                for r in comparable if lt.get(r["case_id"]) != r["tstar"]
            ],
            "interpretation_limit": (
                "delta=1 proves only that layer semantics and mechanical text "
                "check agree on the judgeable subset; it does NOT prove T* is "
                "independent (review Q2). Independence is carried by I-4.3."
            ),
        }
        if args.delta_out:
            out_dir = os.path.dirname(os.path.abspath(args.delta_out))
            if out_dir and not os.path.isdir(out_dir):
                os.makedirs(out_dir)
            with open(args.delta_out, "w", encoding="utf-8", newline="") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
        print("DELTA: %.6f (agree %d / comparable %d, min %.2f) -> %s | "
              "unjudgeable excluded %d" %
              (delta, len(agree), len(comparable), min_delta,
               "PASS" if doc["delta_pass"] else "FAIL",
               star["counts"]["unjudgeable"]))
        return 0 if doc["delta_pass"] else 1

    if not args.samples or not args.out:
        raise SystemExit("FATAL: --samples and --out are required in produce mode")

    actual = sha256_file(args.samples)
    if actual != rules["samples_sha256"]:
        raise SystemExit("FATAL: samples sha256 %s != frozen %s" %
                         (actual, rules["samples_sha256"]))
    with open(args.samples, "r", encoding="utf-8", newline="") as f:
        samples = json.load(f)
    doc = build_truth_star(samples, actual, rules)
    if doc["total"] != rules["sample_count"]:
        raise SystemExit("FATAL: sample count %d != frozen %d" %
                         (doc["total"], rules["sample_count"]))
    out_dir = os.path.dirname(os.path.abspath(args.out))
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print("TRUTH_STAR: true=%d false=%d unjudgeable=%d total=%d coverage=%.6f" %
          (doc["counts"]["true"], doc["counts"]["false"],
           doc["counts"]["unjudgeable"], doc["total"], doc["coverage"]))
    print("UNJUDGEABLE_REASONS: %s" % json.dumps(doc["unjudgeable_reasons"],
                                                 ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
