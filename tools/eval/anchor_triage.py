#!/usr/bin/env python3
"""Round-7 anchor triage (card XJ-20261108-003 D3; acceptance V3).

Classifies every shadow record carrying an artifact_path:

* ``exists_but_unlisted`` — the artifact EXISTS under an observation surface
  (run-dir workspace / repo root) but the main-track anchor list missed it →
  instrument gap;
* ``truly_missing``       — the artifact does not exist on any surface → real
  executor difference / fabrication signal (never laundered into agreement:
  counted, reported, kept in the anchor bucket per the card's 不洗白 red line);
* ``resolved``            — artifact exists AND the record's predicate
  outcome already agrees with the main-track level;
* ``out_of_bounds``       — relative path escapes the root (rejected).

Surfaces checked: run-dir workspace (round-dir root itself = the C10 seeded
execution workspace), the sealed package workspace (C10 rebuild), and the
repo root. CLI:
    python tools/eval/anchor_triage.py --run-dir DIR [--shadow-dir DIR]
        [--package DIR] [--out FILE]

Exit codes: 0 ok; 2 usage.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def triage(run_dir: Path, shadow_dir: Path, package_dir: Path,
           root: Path) -> Dict[str, object]:
    records: List[dict] = []
    levels: Dict[str, List[str]] = {}
    claims: Dict[str, List[dict]] = {}
    for arm in ("A", "B"):
        rec_file = shadow_dir / "primary" / arm / f"records-{arm}.jsonl"
        if rec_file.is_file():
            for line in rec_file.read_text(encoding="utf-8").splitlines()[1:]:
                if line.strip():
                    records.append(json.loads(line))
        cl_file = shadow_dir / "primary" / arm / f"claims-{arm}.json"
        if cl_file.is_file():
            claims.update(json.loads(cl_file.read_text(encoding="utf-8")))
    if package_dir:
        jf = package_dir / "judgements-blind.json"
        if jf.is_file():
            levels = json.loads(jf.read_text(encoding="utf-8"))

    surfaces = [run_dir, root]
    ws = package_dir / "workspace" if package_dir else None
    if ws and ws.is_dir():
        surfaces.append(ws)

    triage_counts = {"exists_but_unlisted": 0, "truly_missing": 0,
                     "resolved": 0, "out_of_bounds": 0}
    rows: List[dict] = []
    for rec in records:
        art = rec.get("artifact_path")
        if not art:
            continue
        cid = str(rec.get("claim_id"))
        code = cid.split("-c")[0]
        rel = str(art).replace("\\", "/")
        found_on = None
        if ".." in rel.split("/"):
            triage_counts["out_of_bounds"] += 1
            rows.append({"claim_id": cid, "artifact": art, "class": "out_of_bounds"})
            continue
        for surface in surfaces:
            if (surface / rel).is_file():
                found_on = str(surface)
                break
        if not found_on:
            triage_counts["truly_missing"] += 1
            rows.append({"claim_id": cid, "artifact": art, "class": "truly_missing"})
            continue
        # exists somewhere: resolved if the record's predicate outcome already
        # agrees with the main-track level; otherwise exists_but_unlisted
        lv_rows = levels.get(code, [])
        main_lv = None
        for c in claims.get(code, []):
            if int(c.get("source_line", -1)) == int(rec.get("evidence_span", [0, 0])[0]):
                idx = claims[code].index(c)
                if idx < len(lv_rows):
                    main_lv = lv_rows[idx]
                break
        consistent = None
        if main_lv in ("E2", "E3", "E4") and rec.get("predicate_ok") is not None:
            consistent = bool(rec["predicate_ok"]) == (main_lv == "E4")
        if consistent is True:
            triage_counts["resolved"] += 1
            cls = "resolved"
        else:
            triage_counts["exists_but_unlisted"] += 1
            cls = "exists_but_unlisted"
        rows.append({"claim_id": cid, "artifact": art, "class": cls,
                     "found_on": found_on, "main_level": main_lv,
                     "predicate_ok": rec.get("predicate_ok"),
                     "consistent": consistent})
    return {"run_dir": str(run_dir), "record_count": len(records),
            "artifact_path_records": len(rows), "triage": triage_counts,
            "rows": rows,
            "note": ("不洗白红线: truly_missing = real-difference/fabrication "
                     "signal — counted, never converted into agreement")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="round-7 anchor triage (§14 D1-D)")
    ap.add_argument("--run-dir", default="run-dir-r7")
    ap.add_argument("--shadow-dir", default="shadow-r7")
    ap.add_argument("--package", default=None,
                    help="sealed package dir (workspace surface + levels)")
    ap.add_argument("--root", default=".", help="repo root surface")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    result = triage(Path(args.run_dir), Path(args.shadow_dir),
                    Path(args.package) if args.package else None,
                    Path(args.root))
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    print(json.dumps(result["triage"], ensure_ascii=False))
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="") as fh:
            fh.write(payload + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
