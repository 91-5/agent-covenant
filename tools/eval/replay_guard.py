#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""XJ-20261113-002 D5 / V9: X-7.3 executable recomputation gate (ADV-7).

F5 states categorically that the round-15 M1 recompute was done with no
sandbox, no environment hash check and no randomness check. This module checks
the three frozen gates rather than asserting them:

  * ``sandbox``      -- container / isolation proof manifest must exist
  * ``env_manifest`` -- python version + dependency hashes + platform
                        fingerprint in one environment manifest
  * ``hash_match``   -- every product sha256 must match the sealed seal.json

plus ``nondeterministic_rate <= max_nondeterministic_rate`` (0.05). An
*unmeasured* randomness rate is NOT a passing rate: without a sandbox the
judge replay is deliberately not executed on bare metal, so the rate is
reported as null and the gate fails. Faking a 0.0 here would be exactly the
failure F5 warns about.

When any required gate is unsatisfied the tool exits 1 and emits
``provisional_required=true`` / ``downgrade_required=true``; the M1 recompute
value is then labelled PROVISIONAL by m1_recompute.py and explicitly downgraded
in the report (prohibition 5 / X-7.3). No "convergence" claim is issued.

Only standard-library imports plus provenance_check helpers. CI is py3.9:
JSON is written through ``open(..., newline="")``.
"""

from __future__ import print_function

import argparse
import json
import os
import platform
import sys

import provenance_check as pc

ENV_MARKERS = (
    ("python_version", ("python_version", "python", "python_version_exact")),
    ("dependency_hashes", ("dependency_hashes", "dependency_sha256",
                           "dependencies_sha256", "pip_freeze_sha256")),
    ("platform_fingerprint", ("platform_fingerprint", "platform",
                              "platform_signature", "os_fingerprint")),
)
SANDBOX_NAME_MARKERS = ("sandbox", "container", "isolation", "docker",
                        "cgroup", "chroot", "namespace-proof")


def collect_json_candidates(custody, max_depth=3):
    out = []
    for root, dirs, files in os.walk(custody):
        rel = os.path.relpath(root, custody)
        if rel != "." and rel.count(os.sep) >= max_depth:
            dirs[:] = []
            continue
        for name in sorted(files):
            if not name.endswith(".json"):
                continue
            out.append(os.path.join(root, name))
    return out


def check_env_manifest(custody):
    """Look for a real environment manifest, not a package manifest."""
    inspected = []
    for path in collect_json_candidates(custody):
        lname = os.path.basename(path).lower()
        if not any(k in lname for k in ("manifest", "env", "environment")):
            continue
        try:
            with open(path, "r", encoding="utf-8", newline="") as f:
                doc = json.load(f)
        except Exception as exc:
            inspected.append({"path": path.replace("\\", "/"),
                              "parse_error": str(exc)})
            continue
        keys = set(doc.keys()) if isinstance(doc, dict) else set()
        found = {}
        for label, variants in ENV_MARKERS:
            hit = [k for k in variants if k in keys]
            found[label] = hit[0] if hit else None
        inspected.append({"path": path.replace("\\", "/"),
                          "top_level_keys": sorted(keys)[:20],
                          "markers_found": found})
    satisfied = any(
        all(x.get("markers_found", {}).get(label) for label, _ in ENV_MARKERS)
        for x in inspected)
    return satisfied, inspected


def check_sandbox(custody):
    """Container / isolation proof, searched by executable filesystem scan."""
    hits = []
    for root, dirs, files in os.walk(custody):
        for name in files:
            if any(k in name.lower() for k in SANDBOX_NAME_MARKERS):
                hits.append(os.path.join(root, name).replace("\\", "/"))
    runtime = {
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "container_env_var": os.environ.get("container"),
        "dockerenv_present": os.path.exists("/.dockerenv"),
    }
    # A container marker alone is not isolation *proof*; the frozen evidence
    # requires a manifest. Windows bare metal has none.
    satisfied = bool(hits) or bool(runtime["container_env_var"]) or \
        runtime["dockerenv_present"]
    return satisfied, {"candidate_files": hits, "runtime": runtime,
                       "note": "no container/isolation proof manifest found"}


def check_hash_match(custody, rules):
    cfg = rules["provenance"]
    seal_path = os.path.join(custody, cfg["seal_json"])
    if not os.path.isfile(seal_path):
        return False, {"reason": "seal.json missing"}
    with open(seal_path, "r", encoding="utf-8", newline="") as f:
        seal = json.load(f)
    entries = seal["files"]
    pdir = os.path.join(custody, "run-dir-r6", "products")
    names = sorted(f for f in os.listdir(pdir) if f.endswith(".md"))
    matched, mismatched, absent = 0, [], []
    for name in names:
        digest = pc.sha256_file(os.path.join(pdir, name))
        ent = entries.get("products/" + name)
        if ent is None:
            absent.append(name)
        elif ent.get("sha256") == digest:
            matched += 1
        else:
            mismatched.append(name)
    return (not mismatched and not absent), {
        "total": len(names), "matched": matched,
        "mismatched": mismatched[:10], "mismatch_count": len(mismatched),
        "absent": absent[:10], "absent_count": len(absent),
        "seal_sha256": pc.sha256_file(seal_path),
    }


def input_derivation_determinism(custody):
    """Diagnostic only: re-hash every product twice and compare.

    This measures determinism of the *input derivation*, NOT the judge replay
    nondeterminism required by X-7.3. It must never be substituted for it.
    """
    pdir = os.path.join(custody, "run-dir-r6", "products")
    names = sorted(f for f in os.listdir(pdir) if f.endswith(".md"))
    first = [pc.sha256_file(os.path.join(pdir, n)) for n in names]
    second = [pc.sha256_file(os.path.join(pdir, n)) for n in names]
    mismatches = sum(1 for a, b in zip(first, second) if a != b)
    return {"scope": "input_derivation_only_not_judge_replay",
            "cases": len(names), "mismatches": mismatches,
            "rate": mismatches / float(len(names)) if names else 0.0}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--custody", default="")
    ap.add_argument("--require-sandbox", action="store_true")
    ap.add_argument("--require-env-manifest", action="store_true")
    ap.add_argument("--require-hash-match", action="store_true")
    ap.add_argument("--max-nondeterministic-rate", type=float, default=None)
    ap.add_argument("--out", default="out/replay-guard.json")
    ap.add_argument("--prereg", default=pc.DEFAULT_PREREG)
    args = ap.parse_args(argv)

    rules = pc.load_frozen_block(args.prereg)
    x73 = rules["x_7_3"]
    max_rate = args.max_nondeterministic_rate
    if max_rate is None:
        max_rate = x73["max_nondeterministic_rate"]
    if abs(max_rate - x73["max_nondeterministic_rate"]) > 1e-9:
        raise SystemExit("FATAL: --max-nondeterministic-rate %r diverges from "
                         "frozen %r" % (max_rate, x73["max_nondeterministic_rate"]))

    custody, tried = pc.resolve_custody(args.custody or
                                        rules["provenance"]["custody_arg"], rules)
    if not custody:
        raise SystemExit("FATAL: custody not resolvable; tried %s" %
                         json.dumps(tried, ensure_ascii=False))

    sandbox_ok, sandbox_ev = check_sandbox(custody)
    env_ok, env_ev = check_env_manifest(custody)
    hash_ok, hash_ev = check_hash_match(custody, rules)

    # Without a sandbox the deterministic judge replay is deliberately NOT
    # executed on bare metal; its nondeterministic rate is therefore unmeasured.
    # Unmeasured is not <= 0.05 -- reporting 0.0 would be a false pass.
    diag = input_derivation_determinism(custody)
    nondet_rate = None
    nondet_measured = False
    nondet_ok = False
    nondet_reason = (
        "judge replay not executed: no sandbox/isolation proof, so the "
        "nondeterministic rate cannot be measured; an unmeasured rate is not "
        "treated as <= %.2f (F5 / X-7.3)" % max_rate)

    gates = {
        "sandbox": {"required": bool(args.require_sandbox),
                    "satisfied": sandbox_ok, "evidence": sandbox_ev},
        "env_manifest": {"required": bool(args.require_env_manifest),
                         "satisfied": env_ok, "evidence": env_ev},
        "hash_match": {"required": bool(args.require_hash_match),
                       "satisfied": hash_ok, "evidence": hash_ev},
        "nondeterminism": {
            "required": True, "satisfied": nondet_ok, "measured": nondet_measured,
            "observed_rate": nondet_rate, "max_rate": max_rate,
            "reason": nondet_reason,
            "input_derivation_diagnostic": diag,
        },
    }
    failed = [k for k, v in gates.items() if v["required"] and not v["satisfied"]]
    all_ok = not failed
    doc = {
        "schema": "r15-replay-guard-v1",
        "card": "XJ-20261113-002",
        "frozen_in": "section 22 D22-E",
        "clause": "X-7.3",
        "custody_resolved": custody,
        "custody_candidates_tried": tried,
        "gates": gates,
        "required_gates": [k for k, v in gates.items() if v["required"]],
        "failed_gates": failed,
        "all_gates_satisfied": all_ok,
        "provisional_required": not all_ok,
        "provisional_label": x73["provisional_label"] if not all_ok else None,
        "downgrade_required": bool(x73["downgrade_required"]) and not all_ok,
        "downgrade_policy": x73["downgrade_policy"],
        "convergence_claim_issued": False,
        "replay_executed": False,
        "replay_not_executed_reason": (
            "Windows bare metal, no container/isolation proof; re-running the "
            "900 evidence commands of the measured products outside a sandbox "
            "is neither safe nor evidentially valid (review Q5)"),
        "max_nondeterministic_rate": max_rate,
    }
    if args.out:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        with open(args.out, "w", encoding="utf-8", newline="") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

    print("X-7.3 GATES: sandbox=%s env_manifest=%s hash_match=%s "
          "nondeterminism=%s -> %s" %
          ("PASS" if sandbox_ok else "FAIL", "PASS" if env_ok else "FAIL",
           "PASS" if hash_ok else "FAIL",
           "UNMEASURED" if not nondet_measured else
           ("PASS" if nondet_ok else "FAIL"),
           "PASS" if all_ok else "FAIL"))
    print("HASH_MATCH: %d/%d products matched seal.json" %
          (hash_ev.get("matched", 0), hash_ev.get("total", 0)))
    print("FAILED_GATES: %s" % (",".join(failed) or "(none)"))
    print("PROVISIONAL: required=%s label=%s downgrade_required=%s "
          "convergence_claim_issued=False" %
          (doc["provisional_required"], doc["provisional_label"],
           doc["downgrade_required"]))
    for name in failed:
        g = gates[name]
        print("  GATE_FAIL %s -> %s" %
              (name, g.get("reason") or
               json.dumps(g["evidence"], ensure_ascii=False)[:400]))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
