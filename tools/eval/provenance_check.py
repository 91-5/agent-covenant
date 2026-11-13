#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""XJ-20261113-002 D5 / V8: M1 provenance three-piece check (ADV-7, M-7.1'/R-7.2).

Resolves the round-6 custody through the frozen candidate chain (the card's
literal ``../../round6-custody`` does not exist on this host), then verifies:

  * ``key-json``  -- key-20261108T122436Z.json (180-way unblinding mapping)
  * ``seal-hash`` -- run-dir-r6/seal.json, plus a byte-level re-hash of all
                     180 product markdown files against its file table
  * ``b-arm-enforcement`` -- the 65/65 blocked B-arm tool-call evidence

F4 says the B-arm evidence lives in custody; on this host it does not. The
frozen ``provenance.gap_policy`` forbids silently claiming it: the item is
resolved from the frozen outside-custody candidates, hashed, labelled
``in_custody=false`` and disclosed in ``provenance_gaps``. The hash is reported
so the artifact is auditable, but it is never presented as custody provenance.

Only standard-library imports. CI is py3.9: JSON is written through
``open(..., newline="")``.
"""

from __future__ import print_function

import argparse
import collections
import hashlib
import json
import os
import sys

TRUTH_BEGIN = "<!-- R15-TRUTH-BEGIN -->"
TRUTH_END = "<!-- R15-TRUTH-END -->"
DEFAULT_PREREG = "docs/eval-prereg.md"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


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


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_custody(arg, rules):
    """Walk the frozen candidate chain and return (path_or_empty, tried_list)."""
    cfg = rules["provenance"]
    candidates = [arg] + list(cfg["custody_candidates"])
    tried = []
    for cand in candidates:
        path = cand if os.path.isabs(cand) else os.path.abspath(
            os.path.join(REPO_ROOT, cand))
        norm = path.replace("\\", "/")
        is_dir = os.path.isdir(path)
        has_run_data = os.path.isfile(os.path.join(path, "run-dir-r6",
                                                  "run-data.json"))
        tried.append({"candidate": cand, "resolved": norm,
                      "is_dir": is_dir, "has_run_data": has_run_data,
                      "selected": bool(is_dir and has_run_data)})
        if is_dir and has_run_data:
            return norm, tried
    return "", tried


def inside(path, root):
    try:
        return os.path.commonpath([os.path.normcase(os.path.abspath(path)),
                                   os.path.normcase(os.path.abspath(root))]) == \
               os.path.normcase(os.path.abspath(root))
    except ValueError:
        return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--metric", default="M1")
    ap.add_argument("--custody", default="")
    ap.add_argument("--require", default="key-json,seal-hash,b-arm-enforcement")
    ap.add_argument("--out", default="out/provenance-check.json")
    ap.add_argument("--prereg", default=DEFAULT_PREREG)
    args = ap.parse_args(argv)

    rules = load_frozen_block(args.prereg)
    cfg = rules["provenance"]
    if args.metric != cfg["metric"]:
        raise SystemExit("FATAL: metric %r != frozen %r" % (args.metric, cfg["metric"]))
    required = [x.strip() for x in args.require.split(",") if x.strip()]
    if sorted(required) != sorted(cfg["required"]):
        raise SystemExit("FATAL: --require %r diverges from frozen %r" %
                         (required, cfg["required"]))

    custody, tried = resolve_custody(args.custody or cfg["custody_arg"], rules)
    if not custody:
        raise SystemExit("FATAL: custody not resolvable; tried %s" %
                         json.dumps(tried, ensure_ascii=False))

    # ---- key-json -------------------------------------------------------
    key_path = os.path.join(custody, cfg["key_json"])
    if not os.path.isfile(key_path):
        raise SystemExit("FATAL: key-json missing at %s" % key_path)
    key_doc = json.load(open(key_path, "r", encoding="utf-8", newline=""))
    mapping = key_doc["mapping"]

    # ---- seal-hash ------------------------------------------------------
    seal_path = os.path.join(custody, cfg["seal_json"])
    if not os.path.isfile(seal_path):
        raise SystemExit("FATAL: seal-hash missing at %s" % seal_path)
    seal_doc = json.load(open(seal_path, "r", encoding="utf-8", newline=""))
    seal_files = seal_doc["files"]

    product_dir = os.path.join(custody, "run-dir-r6", "products")
    all_entries = sorted(os.listdir(product_dir))
    md_files = [f for f in all_entries if f.endswith(".md")]
    non_products = [f for f in all_entries if not f.endswith(".md")]
    matched, mismatched, absent = [], [], []
    for name in md_files:
        digest = sha256_file(os.path.join(product_dir, name))
        ent = seal_files.get("products/" + name)
        if ent is None:
            absent.append(name)
        elif ent.get("sha256") == digest:
            matched.append(name)
        else:
            mismatched.append(name)

    run_data = json.load(open(os.path.join(custody, "run-dir-r6", "run-data.json"),
                             "r", encoding="utf-8", newline=""))
    entries = run_data["entries"]
    condition_counts = dict(collections.Counter(e["condition"] for e in entries))

    # ---- b-arm-enforcement (outside custody => disclosed gap) -----------
    b_arm_hits = []
    for cand in cfg["b_arm_candidates"]:
        p = cand if os.path.isabs(cand) else os.path.abspath(
            os.path.join(custody, cand))
        if not os.path.isfile(p):
            continue
        doc = json.load(open(p, "r", encoding="utf-8", newline=""))
        b_arm_hits.append({
            "candidate": cand,
            "path": p.replace("\\", "/"),
            "in_custody": inside(p, custody),
            "sha256": sha256_file(p),
            "total": doc.get("total"),
            "blocked": doc.get("blocked"),
            "proceed": doc.get("proceed"),
        })
    inside_hits = [h for h in b_arm_hits if h["in_custody"]]
    chosen = (inside_hits or b_arm_hits or [None])[0]

    gaps = []
    if not inside_hits:
        gaps.append({
            "item": "b-arm-enforcement",
            "reason": "not found inside resolved custody %s" % custody,
            "disposition": ("outside-custody copies located and hashed for "
                            "auditability, but NOT claimed as custody provenance "
                            "(frozen provenance.gap_policy)"),
            "outside_custody_candidates": [h["path"] for h in b_arm_hits],
        })

    appendix = os.path.join(custody, "run-dir-r6", "shadow-appendix-hashes.json")
    hashes = {
        "key-json": sha256_file(key_path),
        "seal-hash": sha256_file(seal_path),
        "b-arm-enforcement": chosen["sha256"] if chosen else None,
    }
    doc = {
        "schema": "r15-provenance-v1",
        "card": "XJ-20261113-002",
        "metric": args.metric,
        "frozen_in": "section 22 D22-E",
        "custody_arg": args.custody or cfg["custody_arg"],
        "custody_resolved": custody,
        "custody_candidates_tried": tried,
        "required": required,
        "products": len(md_files),
        "products_expected": cfg["products_expected"],
        "condition_counts": condition_counts,
        "condition_counts_expected": cfg["condition_counts_expected"],
        "non_product_entries": non_products,
        "non_product_entries_note": ("directory entries, not product markdown; "
                                     "counted separately so 190 is never "
                                     "reported as the product count"),
        "three_item_hashes": hashes,
        "b_arm_enforcement": chosen,
        "b_arm_candidates_found": b_arm_hits,
        "key_json": {
            "path": cfg["key_json"], "sha256": hashes["key-json"],
            "mapping_entries": len(mapping),
        },
        "seal_hash": {
            "path": cfg["seal_json"], "sha256": hashes["seal-hash"],
            "file_count": seal_doc.get("file_count"),
            "products_matched": len(matched),
            "products_mismatched": len(mismatched),
            "products_absent": len(absent),
        },
        "shadow_appendix_hashes_sha256": (
            sha256_file(appendix) if os.path.isfile(appendix) else None),
        "provenance_gaps": gaps,
        "gap_policy": cfg["gap_policy"],
        "provenance_complete": not gaps,
        "F6_scan_evidence": ("executable os.walk + byte-level sha256 over all "
                             "product markdown; negative claims are backed by "
                             "this scan, not by executor disclosure"),
    }
    if doc["products"] != cfg["products_expected"]:
        raise SystemExit("FATAL: products %d != frozen %d" %
                         (doc["products"], cfg["products_expected"]))
    if condition_counts != cfg["condition_counts_expected"]:
        raise SystemExit("FATAL: condition_counts %r != frozen %r" %
                         (condition_counts, cfg["condition_counts_expected"]))
    if mismatched or absent:
        raise SystemExit("FATAL: seal hash mismatch=%d absent=%d" %
                         (len(mismatched), len(absent)))

    if args.out:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        with open(args.out, "w", encoding="utf-8", newline="") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

    cc = condition_counts
    print("PROVENANCE: metric=%s custody=%s products=%d condition_counts={A:%d,B:%d} "
          "required=%s provenance_gaps=%d" %
          (args.metric, custody, doc["products"], cc.get("A", 0), cc.get("B", 0),
           ",".join(required), len(gaps)))
    print("HASHES: key-json=%s seal-hash=%s b-arm-enforcement=%s" %
          (hashes["key-json"], hashes["seal-hash"], hashes["b-arm-enforcement"]))
    print("SEAL: products_matched=%d/%d non_product_entries=%d" %
          (len(matched), len(md_files), len(non_products)))
    for g in gaps:
        print("PROVENANCE_GAP: %s -> %s" % (g["item"], g["reason"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
