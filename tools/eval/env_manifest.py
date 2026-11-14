#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""XJ-20261114-003 D3: environment manifest + seal consistency (X-7.3a).

Builds the environment reproduction manifest frozen in prereg section 24
D24-C (read back from the ``R17-LOCAL-EVALUABLE`` block, never hard-coded):
python_version / platform_fingerprint / dependency_hashes (pip freeze +
native shared libraries shipped with the interpreter) / locale_timezone /
env_whitelist / fixtures_sha256, then checks the manifest against a seal.json
byte-for-byte: every file the manifest declares as consumed that the seal also
covers must hash-identically match, all required fields must be non-empty, and
every seal-covered file must still hash to its recorded value.

Exit codes (frozen): 0 = match, 1 = mismatch (recorded as-is), 2 = error.
Output manifest.json is written into the sealed bundle (re-seal registered
deterministically, r12 precedent). CI is py3.9: ``open(..., newline="")`` and
subprocess with explicit encoding.
"""

from __future__ import print_function

import argparse
import hashlib
import json
import locale
import os
import platform
import re
import subprocess
import sys
import time

TRUTH_BEGIN = "<!-- R17-LOCAL-EVALUABLE-BEGIN -->"
TRUTH_END = "<!-- R17-LOCAL-EVALUABLE-END -->"

NATIVE_LIB_RE = re.compile(r"^(python\w*\.dll|vcruntime[\w.]*\.dll|libcrypto[\w.-]*\.dll|libssl[\w.-]*\.dll)$", re.I)


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


def build_manifest(frozen):
    exe_dir = os.path.dirname(sys.executable)
    freeze = subprocess.run(
        [sys.executable, "-m", "pip", "freeze", "--disable-pip-version-check"],
        capture_output=True, encoding="utf-8", errors="replace")
    native = {}
    for name in sorted(os.listdir(exe_dir)):
        if NATIVE_LIB_RE.match(name):
            native[name] = sha256_file(os.path.join(exe_dir, name))
    env_keys = sorted(k for k in os.environ if k.upper().startswith("COVENANT_"))
    whitelist = {
        "covenant_vars_present": env_keys,
        "pythonpath_set": bool(os.environ.get("PYTHONPATH")),
        "pythonnousersite": os.environ.get("PYTHONNOUSERSITE", ""),
        "capture_rule": "COVENANT_* names only (values never recorded); PYTHONPATH/PYTHONNOUSERSITE presence",
    }
    fixtures = {}
    for spec in frozen["manifest"]["fixtures"]:
        fixtures[spec["path"]] = sha256_file(spec["path"])
    return {
        "schema": "r17-env-manifest-v1",
        "card": "XJ-20261114-003",
        "frozen_in": "prereg section 24 D24-C/D24-G",
        "gate": "X-7.3a",
        "python_version": {
            "short": sys.version.split()[0],
            "full": sys.version,
            "executable": sys.executable.replace("\\", "/"),
        },
        "platform_fingerprint": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "dependency_hashes": {
            "pip_freeze": freeze.stdout.splitlines(),
            "pip_freeze_exit": freeze.returncode,
            "native_shared_libs": native,
            "native_scan_dir": exe_dir.replace("\\", "/"),
        },
        "locale_timezone": {
            "preferred_encoding": locale.getpreferredencoding(),
            "locale": str(locale.getlocale()),
            "tzname": list(time.tzname),
            "utc_offset_minutes": time.localtime().tm_gmtoff // 60 if time.daylight or True else 0,
        },
        "env_whitelist": whitelist,
        "fixtures_sha256": fixtures,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="X-7.3a environment manifest + seal consistency (frozen spec in prereg section 24 D24-C)")
    ap.add_argument("--seal", required=True, help="seal.json of the bundle whose consistency is checked")
    ap.add_argument("--prereg", default="docs/eval-prereg.md")
    ap.add_argument("--out", default="run-r17/env-manifest.json")
    args = ap.parse_args(argv)

    try:
        frozen = load_frozen_block(args.prereg)
        required = frozen["manifest"]["required_fields"]

        manifest = build_manifest(frozen)
        problems = []

        for field in required:
            value = manifest.get(field)
            if value is None or value == "" or value == {} or value == []:
                problems.append("required field %r empty or missing" % field)

        # fixture declarations must equal the frozen sha256 values
        for spec in frozen["manifest"]["fixtures"]:
            got = manifest["fixtures_sha256"].get(spec["path"])
            if got != spec["sha256"]:
                problems.append("fixture %s sha256 %s != frozen %s"
                                % (spec["path"], got, spec["sha256"]))

        # seal consistency: recompute every seal-covered file; intersect with
        # the manifest fixture declarations byte-for-byte. seal files values
        # may be plain sha256 strings (r15 era) or {sha256, bytes} dicts (r17).
        with open(args.seal, "r", encoding="utf-8", newline="") as f:
            seal = json.load(f)
        seal_dir = os.path.dirname(os.path.abspath(args.seal))
        seal_files = seal.get("files") or {}

        def recorded_sha(value):
            if isinstance(value, dict):
                return value.get("sha256")
            return value

        seal_ok = True
        for name in sorted(seal_files):
            recorded = recorded_sha(seal_files[name])
            actual = sha256_file(os.path.join(seal_dir, name))
            if actual != recorded:
                seal_ok = False
                problems.append("seal file %s sha256 %s != recorded %s" % (name, actual, recorded))
        # intersection by CONTENT: a manifest-declared fixture is covered by
        # the seal iff some sealed file has the identical sha256 (byte-for-byte
        # agreement is the evidence, file naming is incidental)
        sha_to_seal_names = {}
        for name in seal_files:
            sha_to_seal_names.setdefault(recorded_sha(seal_files[name]), []).append(name)
        intersection = {}
        for declared_path, declared_sha in sorted(manifest["fixtures_sha256"].items()):
            sealed_as = sha_to_seal_names.get(declared_sha, [])
            intersection[declared_path] = {
                "manifest_sha256": declared_sha,
                "sealed_as": sealed_as,
                "match": bool(sealed_as),
            }
            if not sealed_as:
                problems.append("fixture %s (%s) is not covered by the seal"
                                % (declared_path, declared_sha[:16]))
        if not intersection:
            problems.append("no manifest fixture is covered by the seal; consistency check is vacuous")

        manifest["seal_consistency"] = {
            "seal_path": args.seal.replace("\\", "/"),
            "seal_root_label": seal.get("root_label", ""),
            "seal_file_count": len(seal_files),
            "seal_files_recomputed_ok": seal_ok,
            "fixture_intersection": intersection,
        }
        manifest["verdict"] = "match" if not problems else "mismatch"

        with open(args.out, "w", encoding="utf-8", newline="") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        print("x73a_manifest %s" % manifest["verdict"])
        print("required_fields %d/%d present" % (
            len(required) - len([p for p in problems if p.startswith('required field')]),
            len(required)))
        print("fixture_intersection %d" % len(intersection))
        print("seal_files_recomputed_ok %s" % seal_ok)
        for p in problems:
            print("PROBLEM: %s" % p)
        print("out=%s" % args.out)
        return 0 if not problems else 1
    except SystemExit:
        raise
    except Exception as exc:
        print("MANIFEST ERROR: %r" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
