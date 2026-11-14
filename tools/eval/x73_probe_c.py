#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""XJ-20261114-003 D2: X-7.3c nondeterminism probe, L0 caliber (round 17).

Measures the frozen X-7.3c L0 clause of prereg section 24 D24-B: the judge
itself, given the same sealed judging input, must produce byte-identical
output across 3 runs. All probe parameters (corpus sha, case ids, run count,
exit-code semantics, serialization) are read back from the frozen
``R17-LOCAL-EVALUABLE`` block in docs/eval-prereg.md section 24 D24-G; nothing
is hard-coded here that the frozen block already carries.

Zero-new-judged-data discipline: judgement objects are hashed in memory and
never persisted; the probe emits byte-equality readings only. judge.py is a
red-zone file imported and invoked read-only, never modified (round-13
r13_alignment.py precedent). CI is py3.9: JSON is written through
``open(..., newline="")``.

Exit codes (frozen): 0 = identical, 1 = drift (must be recorded as-is), 2 =
probe error (exception / missing input / corpus sha mismatch).
"""

from __future__ import print_function

import argparse
import hashlib
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import judge  # noqa: E402  (red zone: read-only import)

TRUTH_BEGIN = "<!-- R17-LOCAL-EVALUABLE-BEGIN -->"
TRUTH_END = "<!-- R17-LOCAL-EVALUABLE-END -->"


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
        raise SystemExit("FATAL: frozen R17-LOCAL-EVALUABLE block not found in %s" % prereg_path)
    block = text[start + len(TRUTH_BEGIN):end]
    fence = block.find("```json")
    if fence >= 0:
        block = block[fence + len("```json"):]
        closing = block.rfind("```")
        if closing >= 0:
            block = block[:closing]
    return json.loads(block)


def canonical_hash(judgements):
    """Frozen serialization: json.dumps(sort_keys=True, ensure_ascii=False),
    UTF-8 bytes, sha256. Judgement objects never leave memory; their schema
    ``to_dict()`` form is the canonical byte source."""
    payload = [j.to_dict() for j in judgements]
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def judge_case_once(case, runs_dir):
    """One judging run over a hermetic rebuild of the case fixtures."""
    ws = os.path.join(runs_dir, "ws")
    os.makedirs(ws)
    for name, content in (case.get("fixtures_workspace") or {}).items():
        target = os.path.join(ws, name)
        with open(target, "w", encoding="utf-8", newline="") as f:
            f.write(content)
    judgements = judge.judge_markdown(case["markdown"], root=ws, workspace=ws)
    return canonical_hash(judgements)


def main(argv=None):
    ap = argparse.ArgumentParser(description="X-7.3c L0 nondeterminism probe (frozen spec in prereg section 24 D24-G)")
    ap.add_argument("--input", required=True, help="sealed judging corpus (r11-blind-samples.json)")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--prereg", default="docs/eval-prereg.md")
    ap.add_argument("--out", default="run-r17/x73-probe-c.json")
    args = ap.parse_args(argv)

    try:
        frozen = load_frozen_block(args.prereg)
        probe_cfg = frozen["probe"]

        if args.runs != probe_cfg["runs"]:
            print("FATAL: --runs %d != frozen runs %d" % (args.runs, probe_cfg["runs"]))
            return 2

        corpus_sha = sha256_file(args.input)
        if corpus_sha != probe_cfg["corpus_sha256"]:
            print("FATAL: corpus sha256 mismatch vs frozen block: %s" % corpus_sha)
            return 2

        with open(args.input, "r", encoding="utf-8", newline="") as f:
            cases = {c["case_id"]: c for c in json.load(f)["cases"]}

        results = []
        all_identical = True
        for spec in probe_cfg["cases"]:
            cid = spec["case_id"]
            if cid not in cases:
                print("FATAL: frozen probe case %s not found in corpus" % cid)
                return 2
            case = cases[cid]
            hashes = []
            for run_index in range(args.runs):
                runs_dir = tempfile.mkdtemp(prefix="x73c-%s-run%d-" % (cid, run_index))
                try:
                    hashes.append(judge_case_once(case, runs_dir))
                finally:
                    for extra in ("ws",):
                        pass
                # temp dirs left in place would leak; clean up deterministically
                import shutil
                shutil.rmtree(runs_dir, ignore_errors=True)
            identical = len(set(hashes)) == 1
            if not identical:
                all_identical = False
            results.append({
                "case_id": cid,
                "layer": spec["layer"],
                "path_covered": spec.get("path_covered", ""),
                "run_hashes": hashes,
                "identical": identical,
            })

        out = {
            "schema": "r17-x73-probe-c-v1",
            "card": "XJ-20261114-003",
            "frozen_in": "prereg section 24 D24-G",
            "gate": "X-7.3c",
            "caliber": "L0_judge_self_determinism",
            "input": {"path": args.input.replace("\\", "/"), "sha256": corpus_sha},
            "runs": args.runs,
            "cases": results,
            "verdict": "identical" if all_identical else "drift",
            "zero_new_judged_data": probe_cfg.get("zero_new_judged_data", ""),
        }
        with open(args.out, "w", encoding="utf-8", newline="") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)

        for r in results:
            print("%s %s (%s)" % (r["case_id"], "identical" if r["identical"] else "drift",
                                  r["run_hashes"][0][:16]))
        print("x73c_verdict %s" % out["verdict"])
        print("out=%s" % args.out)
        return 0 if all_identical else 1
    except SystemExit:
        raise
    except Exception as exc:  # probe error: frozen exit 2
        print("PROBE ERROR: %r" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
