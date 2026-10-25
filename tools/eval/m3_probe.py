#!/usr/bin/env python3
"""M3 gate-interception probe (XJ-20261024-003 D2; prereg v1.1 §7 C3).

M3 measures whether the repo's gate actually blocks what it claims to block.
The probe constructs six fixture rounds in throwaway directories and drives
the REAL tools as subprocesses -- it never re-implements a rule, because a
reimplemented check would measure the probe, not the gate:

  M3-1  MISSING_VERDICT              gate must refuse  (--require, no verdict)
  M3-2  STALE_VERDICT                gate must refuse  (artifact newer than ts)
  M3-3  PASS + blockers>0            gate must refuse  (BLOCKERS_PRESENT)
  M3-4  UNMAPPED_CLAIM_SURFACE       lint must refuse  (WARN; --strict raises)
  M3-5  LINK_VERDICT_SHA_MISMATCH    gate must refuse  (re-signed verdict)
  M3-6  clean round                  gate AND lint --strict must pass

M3 outcome: interception rate over M3-1..M3-5 plus the false-positive rate on
the clean round. A gate that blocks everything is as broken as one that blocks
nothing, which is why M3-6 is a first-class fixture and not an afterthought.

Fixture construction is knowingly rule-aware (a stale fixture needs a stale
mtime), but every judgement is left to the real subprocess: the probe only
reads exit codes and the tools' own --json violation lists.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GATE = REPO_ROOT / "tools" / "gate.py"
LINT = REPO_ROOT / "tools" / "lint_cards.py"

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2

SNAP_STAMP_FORMAT = "%Y%m%d-%H%M%S"


def _safe_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _utc_iso(offset_seconds: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)) \
        .isoformat(timespec="seconds")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _verdict(vid: str, ts: str, verdict: str = "PASS", blockers: int = 0) -> str:
    """A schema-clean verdict payload (gate REQUIRED_FIELDS + evidence)."""
    return json.dumps({
        "id": vid,
        "verdict": verdict,
        "blockers": blockers,
        "independent": True,
        "verifier": "m3-probe fixture",
        "ts": ts,
        "evidence": [f"m3 probe fixture round {vid}"],
    }, ensure_ascii=False, indent=2)


def _run_tool(tool: Path, cwd: Path, args: List[str]) -> Tuple[int, Optional[dict]]:
    """Run the real gate.py / lint_cards.py as a subprocess and parse --json.

    The subprocess boundary is the whole point (card constraint 3): the probe
    observes the tools exactly as CI would, via exit code and stdout."""
    completed = subprocess.run(
        [sys.executable, str(tool), *args],
        cwd=str(cwd), capture_output=True, timeout=300,
        # Explicit UTF-8 with replacement: the tools print CJK violation text and
        # this runs under whatever locale the caller has (measured: text=True on a
        # GBK console dies with UnicodeDecodeError before the probe can parse
        # --json). Same console discipline as judge.run_command.
        encoding="utf-8", errors="replace",
    )
    payload: Optional[dict] = None
    try:
        payload = json.loads(completed.stdout)
    except ValueError:
        payload = None
    return completed.returncode, payload


def _gate(cwd: Path, *args: str) -> Tuple[int, Optional[dict]]:
    return _run_tool(GATE, cwd, ["--json", *args])


def _lint(cwd: Path, *args: str) -> Tuple[int, Optional[dict]]:
    return _run_tool(LINT, cwd, ["--json", *args])


def _gate_codes(payload: Optional[dict]) -> List[str]:
    if not isinstance(payload, dict):
        return []
    return sorted({v.get("code", "?") for v in payload.get("violations", [])})


def _lint_rules(payload: Optional[dict]) -> List[str]:
    """Rules at WARN or above. NOTICE-level findings (e.g. the allow-listed
    topology orphan) are visible-but-nonblocking by design and must not
    appear as violations -- a clean round reports [], not its NOTICEs."""
    if not isinstance(payload, dict):
        return []
    return sorted({
        f.get("rule", "?") for f in payload.get("findings", [])
        if f.get("level") in ("ERROR", "WARN")
    })


def _fixture_root(tmp: str, name: str) -> Path:
    root = Path(tmp) / name
    root.mkdir(parents=True, exist_ok=True)
    return root


def _base_fixture(tmp: str, name: str, *, ts_offset: int, vid: str = "M3-PROBE",
                  verdict: str = "PASS", blockers: int = 0,
                  artifacts: Tuple[str, ...] = ("artifacts/report.md",)) -> Path:
    """A clean, schema-valid round: verdict + artifacts + map. Tests mutate one
    aspect from here so each class's only difference is the intended defect."""
    root = _fixture_root(tmp, name)
    _write(root / "verdicts" / f"{vid}.verdict.json",
           _verdict(vid, _utc_iso(ts_offset), verdict, blockers))
    for rel in artifacts:
        _write(root / rel, f"# fixture artifact for {vid}\n\ncontent frozen at probe time.\n")
    _write(root / "artifacts.json",
           json.dumps({vid: list(artifacts)}, ensure_ascii=False, indent=2))
    return root


def probe_missing_verdict(tmp: str) -> Dict[str, Any]:
    root = _fixture_root(tmp, "M3-1-missing-verdict")
    _write(root / "verdicts" / ".keep", "")  # verdict dir exists, required id absent
    exit_code, payload = _gate(root, "--verdict-dir", "verdicts", "--require", "M3-PROBE")
    return {"caught": exit_code != 0, "exit_code": exit_code,
            "violations": _gate_codes(payload), "tool": "gate"}


def probe_stale_verdict(tmp: str) -> Dict[str, Any]:
    # Artifact mtime is NOW; the verdict signed 60s ago vouches for older text.
    root = _base_fixture(tmp, "M3-2-stale-verdict", ts_offset=-60)
    exit_code, payload = _gate(root, "--verdict-dir", "verdicts",
                               "--artifact-map", "artifacts.json")
    return {"caught": exit_code != 0, "exit_code": exit_code,
            "violations": _gate_codes(payload), "tool": "gate"}


def probe_pass_with_blockers(tmp: str) -> Dict[str, Any]:
    root = _base_fixture(tmp, "M3-3-pass-with-blockers", ts_offset=5, blockers=1)
    exit_code, payload = _gate(root, "--verdict-dir", "verdicts",
                               "--artifact-map", "artifacts.json")
    return {"caught": exit_code != 0, "exit_code": exit_code,
            "violations": _gate_codes(payload), "tool": "gate"}


def _lint_fixture(tmp: str, name: str, ts_offset: int) -> Path:
    """Claim-surface fixture: README.md mapped by a round whose PASS verdict
    either postdates the text (clean) or predates it (no current signature)."""
    root = _base_fixture(tmp, name, ts_offset=ts_offset, artifacts=("README.md",))
    (root / "tasks").mkdir(parents=True, exist_ok=True)
    return root


def _lint_args() -> List[str]:
    # --allow-orphan-id keeps the fixture's cardless verdict a NOTICE, so the
    # ONLY strict-failing finding a defect fixture can produce is its own.
    return ["--allow-orphan-id", "M3-PROBE", "--strict"]


def probe_unmapped_claim_surface(tmp: str) -> Dict[str, Any]:
    root = _lint_fixture(tmp, "M3-4-unmapped-claim-surface", ts_offset=-60)
    exit_code, payload = _lint(root, "--dir", "tasks", "--verdict-dir", "verdicts",
                               "--artifact-map", "artifacts.json", *_lint_args())
    return {"caught": exit_code != 0, "exit_code": exit_code,
            "violations": _lint_rules(payload), "tool": "lint --strict"}


def probe_link_sha_mismatch(tmp: str) -> Dict[str, Any]:
    root = _base_fixture(tmp, "M3-5-link-sha-mismatch", ts_offset=5)
    stamp = datetime.now().strftime(SNAP_STAMP_FORMAT)
    _write(root / ".freeze" / "manifests" / f"{stamp}.json", "{}\n")
    _write(root / ".freeze" / "link-M3-PROBE.json", json.dumps({
        "card": "M3-PROBE",
        "snap_ts": stamp,
        "verdict_sha256": "f" * 64,  # signed bytes changed since the link was written
    }, ensure_ascii=False, indent=2))
    exit_code, payload = _gate(root, "--verdict-dir", "verdicts",
                               "--artifact-map", "artifacts.json")
    return {"caught": exit_code != 0, "exit_code": exit_code,
            "violations": _gate_codes(payload), "tool": "gate"}


def probe_clean_round(tmp: str) -> Dict[str, Any]:
    """M3-6: nothing is wrong. Both tools must pass -- blocking a clean round
    is a false positive, and a gate that cries wolf trains people to bypass it."""
    gate_root = _base_fixture(tmp, "M3-6-clean-gate", ts_offset=5)
    gate_exit, gate_payload = _gate(gate_root, "--verdict-dir", "verdicts",
                                    "--artifact-map", "artifacts.json")
    lint_root = _lint_fixture(tmp, "M3-6-clean-lint", ts_offset=5)
    lint_exit, lint_payload = _lint(lint_root, "--dir", "tasks", "--verdict-dir", "verdicts",
                                    "--artifact-map", "artifacts.json", *_lint_args())
    caught = gate_exit != 0 or lint_exit != 0
    return {"caught": caught, "exit_code": gate_exit,
            "violations": _gate_codes(gate_payload) + _lint_rules(lint_payload),
            "tool": "gate+lint --strict",
            "detail": {"gate_exit": gate_exit, "lint_exit": lint_exit,
                       "gate_violations": _gate_codes(gate_payload),
                       "lint_rules": _lint_rules(lint_payload)}}


#: (class id, defect under test, builder). The class list is the card's
#: decision-3 table; the builders call the real tools and nothing else.
CLASSES = (
    ("M3-1", "MISSING_VERDICT", probe_missing_verdict),
    ("M3-2", "STALE_VERDICT", probe_stale_verdict),
    ("M3-3", "VERDICT_SCHEMA_NONCOMPLIANT (PASS + blockers>0)", probe_pass_with_blockers),
    ("M3-4", "UNMAPPED_CLAIM_SURFACE", probe_unmapped_claim_surface),
    ("M3-5", "LINK_VERDICT_SHA_MISMATCH", probe_link_sha_mismatch),
    ("M3-6", "clean round (false-positive control)", probe_clean_round),
)


def run_probe() -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    intercepted = 0
    with tempfile.TemporaryDirectory(prefix="m3-probe-") as tmp:
        for class_id, defect, builder in CLASSES:
            entry = {"defect": defect}
            entry.update(builder(tmp))
            results[class_id] = entry
    defect_classes = [c for c, _d, _b in CLASSES if c != "M3-6"]
    intercepted = sum(1 for c in defect_classes if results[c]["caught"])
    clean_caught = bool(results["M3-6"]["caught"])
    results["summary"] = {
        "intercepted": f"{intercepted}/{len(defect_classes)}",
        "clean_round_caught": clean_caught,
        "false_positive_rate": 1.0 if clean_caught else 0.0,
        "m3": "PASS" if intercepted == len(defect_classes) and not clean_caught else "FAIL",
    }
    return results


def format_report(results: Dict[str, Any]) -> str:
    lines = ["== M3 gate probe (real gate.py / lint_cards.py subprocesses) =="]
    for class_id, defect, _builder in CLASSES:
        entry = results[class_id]
        lines.append(
            f"{class_id} {entry['tool']}: caught={entry['caught']} "
            f"exit={entry['exit_code']} violations={entry['violations']} [{defect}]")
    summary = results["summary"]
    lines.append(f"interception: {summary['intercepted']}  "
                 f"clean-round false positives: {summary['false_positive_rate']}")
    lines.append(f"M3: {summary['m3']}")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    _safe_utf8()
    parser = argparse.ArgumentParser(
        description="M3 gate-interception probe: 5 defect classes + 1 clean "
                    "round against the real gate.py / lint_cards.py.")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit machine-readable JSON (for the report)")
    args = parser.parse_args(argv)

    results = run_probe()
    if args.as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(format_report(results))
    return EXIT_OK if results["summary"]["m3"] == "PASS" else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
