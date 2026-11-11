#!/usr/bin/env python3
"""D2: independent judging implementation (card XJ-20261111-002).

Architecturally distinct from the red-zone main-track ``judge.py``:

* main track: a fixed five-level SHORT-CIRCUIT gate (E0 -> E1 -> E2 -> E3
  -> E4) with command reproduction and an all-anchors-present rule; it has a
  repository-root fallback for ref resolution (round-9 R1 surface).
* this module: a WEIGHTED EVIDENCE-SURFACE ALIGNMENT SCORER. Four features are
  computed independently and combined by a frozen weight vector; there is NO
  root fallback (workspace only), unanchored claims do not pass mechanically,
  and observation failures are surfaced as an explicit ERROR class instead of
  silently degrading into "not supported".

Import graph: standard library only. It does NOT import judge, extract,
schema, dsl_compiler or shadow_align; no model, no network, no randomness.
Python 3.9 compatible (CI). JSON writes use open(..., newline="").
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---- rubric v2: frozen independently from v1 (see round11-custody/rubric-v2-r11.md)
RUBRIC_V2 = {
    "id": "R11-INDEPENDENT-RUBRIC-V2",
    "weights": {"ref_readable": 0.30, "observation_reproduced": 0.30,
                "anchor_coverage": 0.40},
    "support_threshold": 0.60,
    "min_anchor_coverage": 0.50,
    "explicit_anchor_required": True,
    "root_fallback": False,
    "observation_failure_fallback": False,
    "levels": ("SUPPORT", "NOT_SUPPORT", "OBSERVATION_ERROR", "INSUFFICIENT"),
}
OBSERVATION_ERROR_CLASSES = ("FILE_NOT_FOUND", "CWD_MISMATCH", "PARSE_FAIL",
                             "TIMEOUT", "SILENT_FALLBACK")
_ANCHOR_RE = re.compile(r"`([^`]+)`|\b\d+(?:\.\d+)?\b")
_REF_RE = re.compile(r"ref=`([^`]+)`")
_CMD_RE = re.compile(r"cmd=`([^`]+)`")
_EXIT_RE = re.compile(r"\bexit=(-?\d+)")
_OUT_RE = re.compile(r"\bout=`([^`]*)`")
_CLAIM_RE = re.compile(r"^\s*-\s*\[已验证\]\s*(.*)$")
_EVIDENCE_RE = re.compile(r"^\s*证据[：:]\s*(.*)$")
_DENY = ("rm -rf", "rm -fr", "shutdown", "mkfs", "format ", "del /f",
         "git push", "curl ", "wget ", "| sh", "| bash")


def _anchors(claim_text: str) -> List[str]:
    return [m.group(1) if m.group(1) is not None else m.group(0)
            for m in _ANCHOR_RE.finditer(claim_text)]


def _parse_case(case: Dict[str, Any]) -> Dict[str, Any]:
    lines = str(case.get("markdown", "")).splitlines()
    claim_text, evidence_raw = "", ""
    for i, line in enumerate(lines):
        m = _CLAIM_RE.match(line)
        if m:
            claim_text = m.group(1).strip()
            for nxt in lines[i + 1:]:
                em = _EVIDENCE_RE.match(nxt)
                if em:
                    evidence_raw = em.group(1).strip()
                    break
            break
    ref = _REF_RE.search(evidence_raw)
    cmd = _CMD_RE.search(evidence_raw)
    ex = _EXIT_RE.search(evidence_raw)
    out = _OUT_RE.search(evidence_raw)
    return {
        "claim_text": claim_text,
        "evidence_raw": evidence_raw,
        "ref": ref.group(1) if ref else None,
        "cmd": cmd.group(1) if cmd else None,
        "claimed_exit": int(ex.group(1)) if ex else None,
        "claimed_out": out.group(1) if out else None,
        "anchors": _anchors(claim_text),
    }


def _reproduce(spec: Dict[str, Any], workspace: Path) -> Tuple[float, str, str]:
    """Return (reproduction_feature, observation_text, error_class)."""
    if spec["ref"]:
        target = workspace / spec["ref"]
        if not target.is_file():
            return 0.0, "", "FILE_NOT_FOUND"
        try:
            return 1.0, target.read_text(encoding="utf-8", errors="replace"), ""
        except OSError:
            return 0.0, "", "PARSE_FAIL"
    if spec["cmd"]:
        if any(tok in spec["cmd"].lower() for tok in _DENY):
            return 0.0, "", "SILENT_FALLBACK"
        try:
            cp = subprocess.run(spec["cmd"], shell=True, cwd=str(workspace),
                                capture_output=True, text=True, timeout=20)
        except subprocess.TimeoutExpired:
            return 0.0, "", "TIMEOUT"
        except OSError:
            return 0.0, "", "SILENT_FALLBACK"
        observation = (cp.stdout or "") + (cp.stderr or "")
        if not observation.strip():
            return 0.0, "", "SILENT_FALLBACK"
        ok = True
        if spec["claimed_exit"] is not None:
            ok = ok and cp.returncode == spec["claimed_exit"]
        if spec["claimed_out"] is not None:
            ok = ok and spec["claimed_out"] in observation
        return (1.0 if ok else 0.0), observation, ""
    return 0.0, "", "PARSE_FAIL"


def judge_case(case: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
    """Independent judgement. Never reads any main-track output artifact."""
    spec = _parse_case(case)
    cid = str(case.get("case_id", ""))
    base = {"case_id": cid, "family": case.get("family"),
            "judge": "independent_v2", "rubric": RUBRIC_V2["id"]}

    if not spec["claim_text"]:
        return dict(base, level="OBSERVATION_ERROR", supports=None, score=0.0,
                    error_class="PARSE_FAIL", features={})
    if not spec["evidence_raw"]:
        return dict(base, level="OBSERVATION_ERROR", supports=None, score=0.0,
                    error_class="PARSE_FAIL", features={})

    f_ref, observation, err = _reproduce(spec, workspace)
    if err:
        # Explicit, never folded into "not supported" (round-9 root cause).
        return dict(base, level="OBSERVATION_ERROR", supports=None, score=0.0,
                    error_class=err,
                    features={"ref_readable": 0.0,
                              "observation_reproduced": 0.0,
                              "anchor_coverage": 0.0})

    anchors = spec["anchors"]
    if RUBRIC_V2["explicit_anchor_required"] and not anchors:
        # Main track lets unanchored claims pass mechanically (E4). v2 does not.
        return dict(base, level="INSUFFICIENT", supports=None, score=0.0,
                    error_class="", features={"ref_readable": f_ref,
                                              "observation_reproduced": 1.0,
                                              "anchor_coverage": 0.0})

    hits = [a for a in anchors if str(a) in observation]
    coverage = len(hits) / len(anchors) if anchors else 0.0
    if coverage < RUBRIC_V2["min_anchor_coverage"]:
        return dict(base, level="NOT_SUPPORT", supports=False,
                    score=round(RUBRIC_V2["weights"]["ref_readable"] * f_ref
                                + RUBRIC_V2["weights"]["observation_reproduced"],
                                6),
                    error_class="",
                    features={"ref_readable": f_ref,
                              "observation_reproduced": 1.0,
                              "anchor_coverage": round(coverage, 6)})

    w = RUBRIC_V2["weights"]
    score = (w["ref_readable"] * f_ref
             + w["observation_reproduced"] * 1.0
             + w["anchor_coverage"] * coverage)
    return dict(base,
                level="SUPPORT" if score >= RUBRIC_V2["support_threshold"] else "NOT_SUPPORT",
                supports=bool(score >= RUBRIC_V2["support_threshold"]),
                score=round(score, 6), error_class="",
                features={"ref_readable": f_ref,
                          "observation_reproduced": 1.0,
                          "anchor_coverage": round(coverage, 6)})


def judge_case_file(path: Path, workspace: Path) -> List[Dict[str, Any]]:
    with open(str(path), "r", encoding="utf-8") as fh:
        cases = json.load(fh)
    return [judge_case(c, workspace) for c in cases]


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    results = judge_case_file(Path(args.cases), Path(args.workspace))
    text = json.dumps(results, ensure_ascii=False, indent=2) + "\n"
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(str(out), "w", newline="", encoding="utf-8") as fh:
        fh.write(text)
    with open(str(out) + ".sha256", "w", newline="", encoding="utf-8") as fh:
        fh.write(_sha(text.encode("utf-8")) + "\n")
    print("INDEPENDENT_JUDGED", len(results), "SHA", _sha(text.encode("utf-8")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
