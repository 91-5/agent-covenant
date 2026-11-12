#!/usr/bin/env python3
"""D1: four-bucket triage of the 90 round-10 mismatches. ZERO new data.

Reads only the two sealed round-10 artifacts plus the frozen section-18 text.
The decision rules come from round11-custody/triage-codebook-canon.json (whose
sha256 is anchored in section 18 D18-E); the trigger verdict strings are
extracted VERBATIM out of section 18 clause 8, never retyped here.

Python 3.9 compatible (CI). JSON/TSV writes use open(..., newline="").
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
CUSTODY = Path("D:/15812/projects/round11-custody")
PREREG = REPO_ROOT / "docs" / "eval-prereg.md"
CANON = CUSTODY / "triage-codebook-canon.json"

ERR_CLASSES = ("FILE_NOT_FOUND", "CWD_MISMATCH", "PARSE_FAIL",
               "TIMEOUT", "SILENT_FALLBACK")
BUCKETS = ("a", "b", "c", "d", "unclassifiable")


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _load(path: Path) -> Any:
    with open(str(path), "r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    with open(str(path), "w", newline="", encoding="utf-8") as fh:
        fh.write(text)


def extract_clause8_triggers() -> Dict[str, str]:
    """Pull the two trigger verdicts verbatim out of the frozen section 18.

    Clause 8 is inside the verbatim block (S18_VERBATIM_BEGIN/END), so the
    strings are the card's own words rather than a restatement here.
    """
    text = PREREG.read_text(encoding="utf-8")
    b = text.index("<!-- S18_VERBATIM_BEGIN -->")
    e = text.index("<!-- S18_VERBATIM_END -->", b)
    block = text[b:e]
    m = re.search(r"8\.\s+\*\*四桶 triage codebook.*?\*\*", block)
    if not m:
        raise RuntimeError("clause 8 not found in frozen verbatim block")
    tail = block[m.start():m.start() + 900]
    # The verdicts sit inside **...** emphasis pairs; capture only the text
    # between the markers so sentence-final punctuation outside the pair is
    # not swallowed (the earlier semicolon-delimited pattern did that).
    b_hit = re.search(r"\*\*桶 b ≥ 60% → ([^*]+)\*\*", tail)
    c_hit = re.search(r"\*\*桶 c ≥ 10% → ([^*]+)\*\*", tail)
    if not b_hit or not c_hit:
        raise RuntimeError("trigger text not found in clause 8")
    return {"b_ge_60pct": b_hit.group(1).strip(),
            "c_ge_10pct": c_hit.group(1).strip(),
            "clause8_span_sha256": _sha(m.group(0).encode("utf-8"))}


def own_bucket(p: Dict[str, Any]) -> bool:
    return bool(p.get("not_applicable") or p.get("evaluative")
                or p.get("schema_invalid"))


def decidable(p: Dict[str, Any]) -> bool:
    classes = [c for c in p.get("error_classes", []) if c in ERR_CLASSES]
    return (int(p.get("exit_code", -1)) == 0
            and bool(p.get("parse_ok"))
            and not classes)


def crosscheck_main_level(claim_id: str, main_level: str,
                          main: Dict[str, Any]) -> Optional[bool]:
    """claim_id suffix cNN indexes main[product] list; no re-judging."""
    m = re.match(r"^([A-Za-z0-9]+)-c(\d+)$", str(claim_id))
    if not m:
        return None
    product, idx = m.group(1), int(m.group(2))
    rows = main.get(product)
    if not isinstance(rows, list) or idx >= len(rows):
        return None
    return rows[idx].get("level") == main_level


def classify(p: Dict[str, Any], rules: List[Dict[str, str]]) -> Tuple[str, str]:
    """Lookup only: the ordered rules are frozen in the canon codebook."""
    layer = p.get("layer")
    errs = [c for c in p.get("error_classes", []) if c in ERR_CLASSES]
    main_supports = bool(p.get("main_supports"))
    predicate_ok = bool(p.get("predicate_ok"))

    by_layer = {r["layer"]: r for r in rules}
    rule = by_layer.get(layer)
    # decision order (canon): c first, then d, then b, then a, else unclassifiable
    if layer == "fallback_probe" or errs:
        bucket = "c"
    elif layer in ("incomplete", "no_evidence"):
        bucket = "d"
    elif (layer in ("anchor_miss", "repro_fail", "ref_missing")
          and main_supports != predicate_ok):
        bucket = "b"
    elif layer in ("cmd_ok", "ref_ok", "goldset_text"):
        bucket = "a"
    else:
        bucket = "unclassifiable"
    basis = rule["basis"] if rule else "no frozen rule for layer " + str(layer)
    # guard: the frozen layer rule must agree with the ordered decision
    if rule and rule["bucket"] != bucket:
        bucket = "unclassifiable"
        basis = "CONFLICT: canon layer rule says " + rule["bucket"]
    return bucket, basis


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--main", dest="main", required=True)
    ap.add_argument("--codebook", dest="codebook", required=True)
    ap.add_argument("--out", dest="out", required=True)
    args = ap.parse_args(argv)

    gate_path, main_path = Path(args.inp), Path(args.main)
    gate = _load(gate_path)
    main = _load(main_path)
    canon_bytes = CANON.read_bytes()
    canon = json.loads(canon_bytes.decode("utf-8"))
    out_path = Path(args.out)
    summary_path = out_path.parent / "triage-r11-summary.json"

    # codebook output must be byte-identical to the frozen canon
    cb_path = Path(args.codebook)
    cb_path.parent.mkdir(parents=True, exist_ok=True)
    cb_path.write_bytes(canon_bytes)

    triggers_text = extract_clause8_triggers()
    pairs = list(gate.get("pairs", []))
    comparable = [p for p in pairs if not own_bucket(p)]
    mismatches = [p for p in comparable
                  if decidable(p)
                  and bool(p.get("predicate_ok")) != bool(p.get("main_supports"))]

    rows = []
    counts = {b: 0 for b in BUCKETS}
    cc_ok = 0
    for p in mismatches:
        bucket, basis = classify(p, canon["layer_rules"])
        counts[bucket] += 1
        cc = crosscheck_main_level(p.get("claim_id"), p.get("main_level"), main)
        if cc is True:
            cc_ok += 1
        rows.append({
            "claim_id": p.get("claim_id"),
            "product": p.get("product"),
            "layer": p.get("layer"),
            "main_level": p.get("main_level"),
            "main_supports": bool(p.get("main_supports")),
            "predicate_ok": bool(p.get("predicate_ok")),
            "error_classes": list(p.get("error_classes", [])),
            "bucket": bucket,
            "main_level_crosscheck": cc,
            "basis": basis,
        })

    total = len(mismatches)
    shares = {b: (round(counts[b] / total, 6) if total else None)
              for b in BUCKETS}
    b_fired = shares["b"] is not None and shares["b"] >= 0.60
    c_fired = shares["c"] is not None and shares["c"] >= 0.10

    # write TSV (explicit newline discipline, py3.9 safe)
    cols = ("claim_id", "product", "layer", "main_level", "main_supports",
            "predicate_ok", "error_classes", "bucket",
            "main_level_crosscheck", "basis")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(out_path), "w", newline="", encoding="utf-8") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in rows:
            fh.write("\t".join(
                "|".join(r[c]) if c == "error_classes" else str(r[c])
                for c in cols) + "\n")

    buckets_out = {
        b: {"count": counts[b], "share": shares[b]} for b in BUCKETS
    }
    summary = {
        "mode": "four_bucket_triage",
        "card": "XJ-20261111-002",
        "new_data_generated": False,
        "zero_new_data": True,
        "sources": [
            {"path": str(gate_path), "sha256": _sha(gate_path.read_bytes())},
            {"path": str(main_path), "sha256": _sha(main_path.read_bytes())},
            {"path": str(PREREG), "sha256": _sha(PREREG.read_bytes())},
        ],
        "codebook_path": str(cb_path),
        "codebook_sha256": _sha(canon_bytes),
        "codebook_matches_frozen_canon": _sha(cb_path.read_bytes()) == _sha(canon_bytes),
        "mismatch_selection": canon["mismatch_selection"],
        "total": total,
        "comparable": len(comparable),
        "buckets": buckets_out,
        "share_sum": round(sum(v for v in shares.values() if v is not None), 6),
        "unclassifiable": counts["unclassifiable"],
        "main_level_crosscheck_pass": cc_ok,
        "main_level_crosscheck_total": total,
        "triggers": {
            "b_ge_60pct": b_fired,
            "c_ge_10pct": c_fired,
            "fired": ([ "b_ge_60pct" ] if b_fired else []) + ([ "c_ge_10pct" ] if c_fired else []),
            "lookup": [
                {"condition": "桶 b ≥ 60%",
                 "observed_share": shares["b"], "fired": b_fired,
                 "verdict_verbatim": triggers_text["b_ge_60pct"]},
                {"condition": "桶 c ≥ 10%",
                 "observed_share": shares["c"], "fired": c_fired,
                 "verdict_verbatim": triggers_text["c_ge_10pct"]},
            ],
            "no_trigger": not (b_fired or c_fired),
            "clause8_span_sha256": triggers_text["clause8_span_sha256"],
            "lookup_only_no_interpretation": True,
        },
        "rows_path": str(out_path),
    }
    _write_json(summary_path, summary)

    print("TOTAL", total, "COMPARABLE", len(comparable))
    print("BUCKETS", {b: counts[b] for b in BUCKETS})
    print("SHARE_SUM", summary["share_sum"])
    print("UNCLASSIFIABLE", counts["unclassifiable"])
    print("MAIN_LEVEL_CROSSCHECK", cc_ok, "/", total)
    print("CODEBOOK_SHA_MATCH", summary["codebook_matches_frozen_canon"])
    print("TRIGGERS", json.dumps(summary["triggers"], ensure_ascii=False))
    ok = (total == 90 and counts["unclassifiable"] == 0
          and summary["share_sum"] == 1.0
          and cc_ok == total
          and summary["codebook_matches_frozen_canon"])
    print("TRIAGE_SELFCHECK_PASS", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
