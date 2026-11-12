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
# ---- rubric v3 (card XJ-20261112-001 D1 / §19 clause 2, frozen before data)
# v3 INHERITS every v2 decision path verbatim. It adds exactly two explicit
# early-return classes for samples where the evidence surface is structurally
# insufficient to reproduce ANY observation. Both keep supports=None, i.e.
# they remain ABSTENTIONS: v3 never launders an unjudgeable sample into a
# boolean verdict. The raw denominator is never reduced (denominator policy).
# v2 remains callable so the v2/v3 equivalence over non-structural samples can
# be mechanically cross-checked instead of asserted in prose.
RUBRIC_V3 = {
    "id": "R12-INDEPENDENT-RUBRIC-V3",
    "inherits": "R11-INDEPENDENT-RUBRIC-V2",
    "weights": dict(RUBRIC_V2["weights"]),
    "support_threshold": RUBRIC_V2["support_threshold"],
    "min_anchor_coverage": RUBRIC_V2["min_anchor_coverage"],
    "explicit_anchor_required": True,
    "root_fallback": False,
    "observation_failure_fallback": False,
    "levels": ("SUPPORT", "NOT_SUPPORT", "OBSERVATION_ERROR", "INSUFFICIENT",
               "STRUCTURALLY_UNJUDGEABLE"),
    "structural_rule": ("evidence_raw non-empty AND cmd is None AND ref is None "
                        "AND anchors empty"),
    "structural_supports": None,
    "denominator_policy": ("raw and judgable denominators reported side by side; "
                           "no sample is dropped from the raw denominator"),
    "out_of_scope": ("samples with an EMPTY evidence line are outside the frozen "
                     "clause-2 definition; v3 keeps their v2 verdict verbatim "
                     "instead of widening a frozen clause after seeing data"),
}
STRUCTURAL_LEVEL = "STRUCTURALLY_UNJUDGEABLE"
STRUCTURAL_ERROR_CLASS = "STRUCTURAL_NO_EVIDENCE"


def is_structurally_unjudgeable(spec: Dict[str, Any]) -> bool:
    """Section 19 clause 2, verbatim. Empty evidence lines are NOT covered."""
    return (bool(spec.get("evidence_raw"))
            and spec.get("cmd") is None
            and spec.get("ref") is None
            and not spec.get("anchors"))


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
            # encoding= is explicit on purpose (XJ-20261111-002 C1): text=True
            # without it decodes the child's bytes with the caller's locale, so a
            # cp936/GBK console mangles any non-ASCII output. errors="replace"
            # keeps a decode failure from raising instead of degrading.
            cp = subprocess.run(spec["cmd"], shell=True, cwd=str(workspace),
                                capture_output=True, text=True, timeout=20,
                                encoding="utf-8", errors="replace")
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


def _judge_case_v2(case: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
    """Rubric v2, byte-for-byte the round-11 decision path (kept for equivalence)."""
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


def _judge_case_v3(case: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
    """Rubric v3 = rubric v2 plus two explicit structural-abstention classes.

    Every non-structural sample is decided by literally calling the v2 path,
    so the v2/v3 equivalence over that subset is mechanical, not asserted.
    """
    spec = _parse_case(case)
    cid = str(case.get("case_id", ""))
    base = {"case_id": cid, "family": case.get("family"),
            "judge": "independent_v3", "rubric": RUBRIC_V3["id"]}

    if not spec["claim_text"]:
        out = _judge_case_v2(case, workspace)
        out.update(base)
        return out
    if not spec["evidence_raw"]:
        # §19 clause 2 does NOT cover this class (it requires a non-empty
        # evidence line). Keep the v2 verdict VERBATIM -- no widening of a
        # frozen clause after seeing data. These samples stay abstentions,
        # stay in the raw denominator, and are disclosed separately in the
        # decomposition report as out-of-scope for the next round.
        out = _judge_case_v2(case, workspace)
        out.update(base)
        out["out_of_frozen_clause2_scope"] = True
        return out
    if is_structurally_unjudgeable(spec):
        return dict(base, level=STRUCTURAL_LEVEL, supports=None, score=0.0,
                    error_class=STRUCTURAL_ERROR_CLASS, features={},
                    structural_basis=("evidence_raw non-empty, cmd=None, ref=None, "
                                      "anchors=[]: no observation surface exists"))

    out = _judge_case_v2(case, workspace)
    out.update(base)
    return out


def judge_case(case: Dict[str, Any], workspace: Path,
               rubric_version: str = "v3") -> Dict[str, Any]:
    """Independent judgement. Never reads any main-track output artifact.

    Default is rubric v3 (round-12 instrument revision). Pass ``"v2"`` to
    replay the frozen round-11 decision path for equivalence checks.
    """
    if rubric_version == "v2":
        return _judge_case_v2(case, workspace)
    if rubric_version == "v3":
        return _judge_case_v3(case, workspace)
    raise ValueError("unknown rubric version: {}".format(rubric_version))


def judge_case_file(path: Path, workspace: Path,
                    rubric_version: str = "v3") -> List[Dict[str, Any]]:
    with open(str(path), "r", encoding="utf-8") as fh:
        cases = json.load(fh)
    return [judge_case(c, workspace, rubric_version) for c in cases]


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
