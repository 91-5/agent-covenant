#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""XJ-20261113-001 D2: truth-source validity verifier (round 14).

Mechanically re-verifies the frozen F2 finding of prereg section 21: the 133
HOLDOUT rows carrying a design_error_class label are label-inert (no injected
content error is mechanically detectable), so ``design_error_class`` cannot
serve as a HOLDOUT truth source. All rules are read back from the frozen
machine-readable block in ``docs/eval-prereg.md`` section 21 D21-E; this script
never hard-codes thresholds that the frozen block already carries.

Red-zone discipline: read-only with respect to judge.py/extract.py and every
other red-zone path; CI is py3.9, so no ``write_text(newline=)`` -- JSON is
written through ``open(..., newline="")``.
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
    """Frozen rule: first line starting '- [已验证] ' up to the first '。'."""
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("- [已验证] "):
            body = stripped[len("- [已验证] "):]
            stop = body.find("。")
            return body[:stop] if stop >= 0 else body
    return ""


def evidence_kind(markdown):
    if "证据：" not in markdown:
        return "none"
    ev = markdown.split("证据：", 1)[1].strip()
    if ev.startswith("cmd="):
        return "cmd"
    if ev.startswith("ref="):
        return "ref"
    return "none"


def numeric_citations(claim, pattern):
    return [m.group(1) for m in pattern.finditer(claim)]


def cmd_out_value(markdown):
    m = re.search(r"out=`([^`]*)`", markdown)
    return m.group(1) if m else None


def ref_name(markdown):
    m = re.search(r"ref=`([^`]*)`", markdown)
    return m.group(1) if m else None


def main(argv=None):
    ap = argparse.ArgumentParser(description="round-14 truth-source validity verifier (frozen rules in prereg section 21 D21-E)")
    ap.add_argument("--samples", default="out/r11-blind-samples.json")
    ap.add_argument("--rows", default="out/r11-reliability-rows.json")
    ap.add_argument("--prereg", default="docs/eval-prereg.md")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    frozen = load_frozen_block(args.prereg)

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
    cite_re = re.compile(frozen["citation_numeric_re"])
    label_classes = set(frozen["label_error_classes"])

    per_row = []
    per_layer = {}
    contradictions = []
    direction_violations = []
    f2_splits = {
        "cmd_numeric_ok": 0,
        "cmd_no_numeric_citation": 0,
        "ref_fixture_numeric_ok": 0,
        "ref_fixture_existence": 0,
        "ref_absent_inert": 0,
    }

    for r in rows:
        cid = r["case_id"]
        case = cases[cid]
        md = case["markdown"]
        layer = r["layer"]
        truth = layer_truth[layer]
        kind = evidence_kind(md)
        claim = claim_sentence(md)
        cites = numeric_citations(claim, cite_re)

        surface_available = False
        corroboration = "no_evidence_surface"
        contradiction = False

        if kind == "cmd":
            out_val = cmd_out_value(md)
            surface_available = out_val is not None
            if not surface_available:
                corroboration = "unverifiable_no_recorded_out"
            elif cites:
                missing = [c for c in cites if c not in out_val]
                if missing:
                    contradiction = True
                    corroboration = "numeric_citation_missing_from_out"
                else:
                    corroboration = "numeric_citations_in_out"
            else:
                corroboration = "no_numeric_value_position"
        elif kind == "ref":
            ref = ref_name(md)
            fixtures = case.get("fixtures_workspace") or {}
            surface_available = ref in fixtures
            if surface_available:
                content = fixtures[ref]
                if cites:
                    missing = [c for c in cites if c not in content]
                    if missing:
                        contradiction = True
                        corroboration = "numeric_citation_missing_from_fixture"
                    else:
                        corroboration = "numeric_citations_in_fixture"
                else:
                    corroboration = "fixture_present_existence_claim"
            else:
                corroboration = "unverifiable_fixture_absent"
        else:
            corroboration = "unverifiable_no_evidence_line"

        if r.get("design_error_class", "NONE") in label_classes:
            if corroboration == "unverifiable_fixture_absent":
                f2_splits["ref_absent_inert"] += 1
                if r["main_level"] == "E4":
                    direction_violations.append(cid)
            elif corroboration == "numeric_citations_in_out":
                f2_splits["cmd_numeric_ok"] += 1
            elif corroboration == "no_numeric_value_position" and kind == "cmd":
                f2_splits["cmd_no_numeric_citation"] += 1
            elif corroboration == "numeric_citations_in_fixture":
                f2_splits["ref_fixture_numeric_ok"] += 1
            elif corroboration == "fixture_present_existence_claim":
                f2_splits["ref_fixture_existence"] += 1
            if contradiction:
                contradictions.append(cid)

        entry = {
            "case_id": cid,
            "stratum": r["stratum"],
            "layer": layer,
            "layer_truth": truth,
            "design_error_class": r.get("design_error_class", "NONE"),
            "main_level": r["main_level"],
            "evidence_kind": kind,
            "claim_sentence": claim,
            "numeric_citations": cites,
            "surface_available": surface_available,
            "corroboration": corroboration,
            "contradiction": contradiction,
        }
        per_row.append(entry)

        agg = per_layer.setdefault(layer, {"n": 0, "truth": truth, "contradictions": 0,
                                           "corroboration_counts": {}})
        agg["n"] += 1
        agg["corroboration_counts"][corroboration] = agg["corroboration_counts"].get(corroboration, 0) + 1
        if contradiction:
            agg["contradictions"] += 1

    labeled = [e for e in per_row if e["design_error_class"] in label_classes]
    inert = [e for e in labeled if not e["contradiction"]]

    f2 = {
        "labeled_total": len(labeled),
        "holdout_labels_inert": len(inert),
        "holdout_labels_inert_fraction": "%d/%d" % (len(inert), len(labeled)),
        "contradictions": len(contradictions),
        "counterexamples": contradictions,
        "splits": dict(f2_splits),
        "direction_check_violations": direction_violations,
        "label_inertness_rule": frozen["contradiction_rule"],
        "non_numeric_citation_disposition": frozen["non_numeric_citation_disposition"],
        "ref_absent_disposition": frozen["ref_absent_disposition"],
    }

    result = {
        "schema": "r14-truth-source-v1",
        "card": "XJ-20261113-001",
        "frozen_in": "prereg section 21 D21-E",
        "truth_source_caliber": frozen["fp_measurement"]["truth_source_caliber"],
        "inputs": {
            "samples_path": args.samples,
            "samples_sha256": samples_sha,
            "rows_path": args.rows,
            "rows_sha256": rows_sha,
            "prereg_path": args.prereg,
        },
        "totals": {"n": len(per_row), "labeled": len(labeled)},
        "f2": f2,
        "per_layer_summary": per_layer,
        "per_row": per_row,
    }

    with open(args.out, "w", encoding="utf-8", newline="") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("holdout_labels_inert %d/%d" % (len(inert), len(labeled)))
    print("contradictions %d" % len(contradictions))
    print("splits cmd=%d ref_present=%d ref_absent=%d" % (
        f2_splits["cmd_numeric_ok"] + f2_splits["cmd_no_numeric_citation"],
        f2_splits["ref_fixture_numeric_ok"] + f2_splits["ref_fixture_existence"],
        f2_splits["ref_absent_inert"]))
    print("out=%s" % args.out)

    ok = (len(contradictions) == 0
          and len(inert) == len(labeled)
          and not direction_violations)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
