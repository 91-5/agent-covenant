#!/usr/bin/env python3
"""Shared environment isolation (XJ-20261112-001 D2; round-9 ADV-1 closure).

Round-9 ADV-1: a host PYTHONPATH shim shipped a sitecustomize.py that shadowed
stdlib bisect and silently changed 6 lost attributions. This module is the one
source of truth: clear PYTHONPATH and every COVENANT_* variable, disable
sitecustomize / site initialisation with python -S, set PYTHONNOUSERSITE=1,
and fix the child cwd. All round-12 recomputation scripts call clean_env()
here instead of carrying private copies of the isolation logic.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]

ISOLATION_CONTRACT = (
    "clear PYTHONPATH",
    "clear every COVENANT_* variable",
    "disable sitecustomize / site initialisation with -S",
    "set PYTHONNOUSERSITE=1",
    "fix child cwd",
)


def clean_env() -> Tuple[Dict[str, str], Dict[str, Any]]:
    """Return (env, info). Verbatim extraction of exit_fixture.clean_env().

    exit_fixture.py is a frozen round-11 fixture and is NOT in this card's
    Owned files, so it is not rewritten. This is the shared implementation
    that round-12 recomputation scripts import.
    """
    env = dict(os.environ)
    removed_covenant = sorted(k for k in env if k.startswith("COVENANT_"))
    for k in removed_covenant:
        env.pop(k, None)
    had_pythonpath = "PYTHONPATH" in env
    env.pop("PYTHONPATH", None)
    env["PYTHONNOUSERSITE"] = "1"
    info: Dict[str, Any] = {
        "pythonpath_key_present_in_host": had_pythonpath,
        "pythonpath_cleared_for_subprocess": True,
        "covenant_vars_removed": removed_covenant,
        "site_initialisation_disabled": True,
        "python_nousersite": "1",
        "cwd_fixed_to": str(REPO_ROOT),
        "contract": list(ISOLATION_CONTRACT),
    }
    return env, info


def run_python_isolated(code: str, cwd: Optional[Path] = None,
                        timeout: int = 15) -> Tuple[subprocess.CompletedProcess,
                                                    Dict[str, Any]]:
    """Run python -S -c <code> in a genuinely isolated child process."""
    env, info = clean_env()
    proc = subprocess.run(
        [sys.executable, "-S", "-c", code],
        capture_output=True, cwd=str(cwd or REPO_ROOT), env=env,
        timeout=timeout, text=True, encoding="utf-8", errors="replace")
    return proc, info


def verify_isolation() -> Dict[str, Any]:
    """Actually MEASURE isolation inside a child, with host probes injected.

    Temporarily sets PYTHONPATH and a COVENANT_* probe in the host, launches an
    isolated child that reports its own environment and sys.flags, then checks
    the probes are gone and -S really took effect. Host env is restored.
    """
    probe_keys = ("PYTHONPATH", "COVENANT_R12_ISOLATION_PROBE")
    saved = {k: os.environ.get(k) for k in probe_keys}
    os.environ["PYTHONPATH"] = "D:/r12-isolation-probe-should-be-cleared"
    os.environ["COVENANT_R12_ISOLATION_PROBE"] = "must-not-reach-child"
    try:
        code = (
            "import json,os,sys;"
            "print(json.dumps({"
            "'pythonpath_present':'PYTHONPATH' in os.environ,"
            "'covenant_keys':sorted(k for k in os.environ "
            "if k.startswith('COVENANT_')),"
            "'no_site':bool(sys.flags.no_site),"
            "'nousersite':os.environ.get('PYTHONNOUSERSITE'),"
            "'cwd':os.getcwd()}))"
        )
        proc, info = run_python_isolated(code, timeout=15)
        try:
            child = json.loads((proc.stdout or "").strip().splitlines()[-1])
        except (ValueError, IndexError, AttributeError):
            child = {}
        checks = {
            "pythonpath_absent_in_child": child.get("pythonpath_present") is False,
            "covenant_probes_absent_in_child":
                child.get("covenant_keys") == [],
            "site_disabled_in_child": child.get("no_site") is True,
            "nousersite_set_in_child": child.get("nousersite") == "1",
            "child_returncode_zero": proc.returncode == 0,
        }
        return {
            "measured_in_child_process": True,
            "host_probes_injected": list(probe_keys),
            "child_report": child,
            "checks": checks,
            "all_checks_pass": all(checks.values()),
            "clean_env_info": info,
            "child_stderr_tail": (proc.stderr or "")[-200:],
        }
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def main(argv: Optional[List[str]] = None) -> int:
    result = verify_isolation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["all_checks_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
