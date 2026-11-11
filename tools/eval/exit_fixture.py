#!/usr/bin/env python3
"""Round-11 exit_source tri-state fixture (card XJ-20261111-002, D5 / V10).

Section 18 D18-B clause 7 / clause 9 and card clause 11:

  * ``os``            independent OS process exit code (real subprocess);
  * ``adapter``       frozen compiler flags/detail mechanical map;
  * ``launch_failed`` 127 / 9009, process never started -- NEVER counted as
                      "not supported".

``adapter`` samples are ``caliber = degraded``, excluded from main C and main
precision, and reported in the secondary report.  Environment is pinned per
round-9 ADV-1: PYTHONPATH and every COVENANT_* variable are removed, site
initialisation is disabled with ``-S`` (blocks sitecustomize shadowing stdlib
``bisect``), and cwd is fixed.

The fixture file is parsed with a small standard-library-only YAML subset
reader, so CI py3.9 needs no third-party package.  No network, no randomness,
no grading output: this module only classifies process-exit provenance.

Python 3.9 compatible: no PEP 604 unions, no newline kwarg on the Path text
writer, ``open(..., newline="")`` for the JSON result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE = REPO_ROOT / "tools" / "eval" / "fixtures" / "exit_codes.yaml"
DEFAULT_OUT = REPO_ROOT / "out" / "exit-fixture-r11.json"
MISSING_CMD = "definitely_missing_r11_cmd_xyz"

# Frozen mechanical map over compiler flags/detail. These are NOT OS exit
# codes: they are the same flags/detail the round-10 gate input derived its
# exit_code from (see r10-gate-input.json field_semantics.exit_code).
ADAPTER_MAP: Dict[str, Dict[str, Any]] = {
    "flags_ok": {"exit_code": 0, "unsupported": False, "error_class": None},
    "observation_failed": {"exit_code": 1, "unsupported": True,
                           "error_class": "FILE_NOT_FOUND"},
    "parse_fail": {"exit_code": 1, "unsupported": True,
                   "error_class": "PARSE_FAIL"},
    "silent_fallback": {"exit_code": 0, "unsupported": False,
                        "error_class": "SILENT_FALLBACK"},
}


# --------------------------------------------------------------------------
# mini-YAML reader (standard library only)
# --------------------------------------------------------------------------
def _scalar(raw: str) -> Any:
    s = raw.strip()
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    if s in ("null", "~", ""):
        return None
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("\"", "'"):
        return s[1:-1]
    try:
        return int(s)
    except ValueError:
        return s


def load_fixture(path: Path) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Parse the frozen YAML subset: top-level scalars + a ``cases:`` list."""
    meta: Dict[str, Any] = {}
    cases: List[Dict[str, Any]] = []
    in_cases = False
    current: Optional[Dict[str, Any]] = None
    with open(str(path), "r", encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line == "cases:":
            in_cases = True
            continue
        if not in_cases:
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = _scalar(v)
            continue
        if line.startswith("- "):
            if current is not None:
                cases.append(current)
            current = {}
            line = line[2:]
        if current is None or ":" not in line:
            continue
        k, v = line.split(":", 1)
        # strip an inline trailing comment only when unquoted
        current[k.strip()] = _scalar(v)
    if current is not None:
        cases.append(current)
    return meta, cases


# --------------------------------------------------------------------------
# environment pinning + tri-state classifier
# --------------------------------------------------------------------------
def clean_env() -> Tuple[Dict[str, str], Dict[str, Any]]:
    env = dict(os.environ)
    removed_covenant = sorted(k for k in env if k.startswith("COVENANT_"))
    for k in removed_covenant:
        env.pop(k, None)
    had_pythonpath = "PYTHONPATH" in env
    env.pop("PYTHONPATH", None)
    env["PYTHONNOUSERSITE"] = "1"
    info = {
        "pythonpath_key_present_in_host": had_pythonpath,
        "pythonpath_cleared_for_subprocess": True,
        "covenant_vars_removed": removed_covenant,
        "site_initialisation_disabled": True,
        "python_nousersite": "1",
        "cwd_fixed_to": str(REPO_ROOT),
    }
    return env, info


def classify(kind: str, payload: Any, root: Path) -> Dict[str, Any]:
    """Return the observed provenance for one fixture case.

    This function is also imported by gate_metrics.py for the r11 gate
    metrics, so the fixture and the gate report cannot drift apart.
    """
    env, isolation = clean_env()
    if kind == "os":
        code = int(payload)
        proc = subprocess.run(
            [sys.executable, "-S", "-c",
             "import sys; sys.exit({})".format(code)],
            capture_output=True, cwd=str(root), env=env, timeout=15)
        return {
            "exit_source": "os",
            "exit_code": int(proc.returncode),
            "caliber": "primary",
            "unsupported": int(proc.returncode) != 0,
            "error_class": None,
            "evidence": "independent OS subprocess returncode (-S, clean env)",
            "env_isolation": isolation,
        }
    if kind == "adapter":
        if str(payload) not in ADAPTER_MAP:
            raise ValueError("unknown adapter payload: {}".format(payload))
        m = ADAPTER_MAP[str(payload)]
        return {
            "exit_source": "adapter",
            "exit_code": m["exit_code"],
            "caliber": "degraded",
            "unsupported": bool(m["unsupported"]),
            "error_class": m["error_class"],
            "evidence": "frozen compiler flags/detail mechanical map",
            "env_isolation": isolation,
        }
    if kind == "launch_failed":
        if str(payload) == "missing_cmd":
            try:
                subprocess.run([MISSING_CMD, "--r11"], capture_output=True,
                               cwd=str(root), env=env, timeout=15)
                raise AssertionError("missing command unexpectedly launched")
            except FileNotFoundError:
                return {
                    "exit_source": "launch_failed",
                    "exit_code": 127,
                    "caliber": "excluded",
                    "unsupported": False,
                    "error_class": None,
                    "evidence": "FileNotFoundError -> POSIX 127 launch_failed",
                    "env_isolation": isolation,
                }
        if str(payload) == "cmd_missing":
            try:
                proc = subprocess.run(["cmd", "/c", MISSING_CMD],
                                      capture_output=True, cwd=str(root),
                                      env=env, timeout=15)
            except FileNotFoundError:
                # Non-Windows host: cmd.exe itself never started. Report the
                # observed truth; the frozen expectation will then fail and be
                # registered instead of being silently laundered.
                return {
                    "exit_source": "launch_failed",
                    "exit_code": 127,
                    "caliber": "excluded",
                    "unsupported": False,
                    "error_class": None,
                    "evidence": ("cmd.exe unavailable on this host -> "
                                 "FileNotFoundError, POSIX 127 semantics"),
                    "env_isolation": isolation,
                }
            raw = proc.stdout + proc.stderr
            # Windows console output is locale-encoded (cp936 here); decode in
            # both UTF-8 and GBK so the command-not-found marker is detectable
            # without pretending the host uses one fixed encoding.
            blob = (raw.decode("utf-8", "replace") + "\n"
                    + raw.decode("gbk", "replace"))
            recognised = ("不是内部或外部命令" in blob
                          or "not recognized" in blob.lower())
            if not recognised:
                raise AssertionError("cmd.exe did not report command-not-found")
            return {
                "exit_source": "launch_failed",
                "exit_code": int(proc.returncode),
                "caliber": "excluded",
                "unsupported": False,
                "error_class": None,
                "windows_shell_semantic_code": 9009,
                "evidence": ("cmd.exe command-not-found; observed returncode "
                             "kept verbatim, 9009 is a frozen semantic marker "
                             "only, never a fabricated OS exit code"),
                "env_isolation": isolation,
            }
        raise ValueError("unknown launch_failed payload: {}".format(payload))
    raise ValueError("unknown fixture kind: {}".format(kind))


# --------------------------------------------------------------------------
# runner
# --------------------------------------------------------------------------
def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(str(path), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_fixture(fixture: Path, root: Path) -> Dict[str, Any]:
    meta, cases = load_fixture(fixture)
    results: List[Dict[str, Any]] = []
    passed = 0
    for case in cases:
        obs = classify(str(case["kind"]), case["payload"], root)
        checks = {
            "exit_source": obs["exit_source"] == case["expect_exit_source"],
            "exit_code": obs["exit_code"] == case["expect_exit_code"],
            "caliber": obs["caliber"] == case["expect_caliber"],
            "unsupported": (bool(obs["unsupported"])
                            == bool(case["expect_unsupported"])),
            "error_class": (
                (obs["error_class"] or "none") == case["expect_error_class"]),
        }
        ok = all(checks.values())
        passed += int(ok)
        results.append({
            "id": case["id"],
            "kind": case["kind"],
            "payload": case["payload"],
            "observed": obs,
            "expect": {k[7:]: v for k, v in case.items()
                       if k.startswith("expect_")},
            "checks": checks,
            "pass": ok,
        })

    by_source: Dict[str, int] = {}
    for r in results:
        s = str(r["observed"]["exit_source"])
        by_source[s] = by_source.get(s, 0) + 1
    launch_as_unsupported = sum(
        1 for r in results
        if r["observed"]["exit_source"] == "launch_failed"
        and r["observed"]["unsupported"])
    adapter_degraded = sum(
        1 for r in results
        if r["observed"]["exit_source"] == "adapter"
        and r["observed"]["caliber"] == "degraded")

    return {
        "mode": "exit_source_fixture_r11",
        "card": "XJ-20261111-002",
        "fixture": "tools/eval/fixtures/exit_codes.yaml",
        "fixture_sha256": _sha256_file(fixture),
        "schema": meta.get("schema"),
        "total": len(results),
        "passed": passed,
        "pass_rate": (passed / len(results)) if results else 0.0,
        "by_exit_source": by_source,
        "adapter_samples_degraded": adapter_degraded,
        "launch_failed_counted_as_unsupported": launch_as_unsupported,
        "env_isolation": results[0]["observed"]["env_isolation"] if results else {},
        "results": results,
        "note": ("all cases really executed; 9009 is a frozen semantic marker "
                 "only, the observed cmd.exe returncode is kept verbatim"),
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--expect", default="10/10",
                    help="expected passed/total, e.g. 10/10")
    args = ap.parse_args(argv)

    fixture = Path(args.fixture)
    if not fixture.is_absolute():
        fixture = REPO_ROOT / fixture
    if not fixture.is_file():
        print("exit_fixture: fixture not found: {}".format(fixture),
              file=sys.stderr)
        return 2
    payload = run_fixture(fixture, REPO_ROOT)
    out = Path(args.out)
    if not out.is_absolute():
        out = REPO_ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(str(out), "w", encoding="utf-8", newline="") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    for r in payload["results"]:
        o = r["observed"]
        print("{} {} exit_source={} exit_code={} caliber={} unsupported={}".format(
            "PASS" if r["pass"] else "FAIL", r["id"], o["exit_source"],
            o["exit_code"], o["caliber"], o["unsupported"]))
        if not r["pass"]:
            print("  failed checks: {}".format(
                [k for k, v in r["checks"].items() if not v]))
    print("FIXTURE {}/{} | BY_SOURCE {} | LAUNCH_FAILED_AS_UNSUPPORTED {}".format(
        payload["passed"], payload["total"], payload["by_exit_source"],
        payload["launch_failed_counted_as_unsupported"]))

    try:
        want_pass, want_total = (int(x) for x in args.expect.split("/"))
    except ValueError:
        print("exit_fixture: bad --expect format", file=sys.stderr)
        return 2
    if payload["passed"] != want_pass or payload["total"] != want_total:
        print("exit_fixture: EXPECT {} not met".format(args.expect),
              file=sys.stderr)
        return 1
    if payload["launch_failed_counted_as_unsupported"] != 0:
        print("exit_fixture: launch_failed counted as unsupported",
              file=sys.stderr)
        return 1
    print("EXPECT {} MET".format(args.expect))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
