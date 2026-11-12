#!/usr/bin/env python3
"""D1: frozen label-alignment mapping between the main track and independent judge.

Card XJ-20261112-002. The 5x5 matrix (main E0-E4 x independent 5 classes) is
FROZEN in section 20 D20-E as a machine-readable JSON block. This module:

  * mirrors that matrix as a code constant (MAPPING);
  * ``--verify --prereg`` reads the matrix back from section 20 and compares it
    cell by cell against the constant -- code must never bypass the frozen text;
  * reports ``unmapped`` (must be empty) and checks that protected abstention
    error classes (SILENT_FALLBACK / FILE_NOT_FOUND) never appear in an
    ``equivalent`` or ``conflict`` disposition;
  * exposes ``map_pair`` / ``disposition_of_error_class`` used by
    ``r13_alignment.py`` for the D6 recomputation.

Three verdict classes only (section 20 clause 2):
  equivalent           - both tracks boolean and same direction
  conflict             - both tracks boolean and opposite direction
  protected_abstention - independent side abstains; mapping to a boolean
                         agreement/disagreement is FORBIDDEN (round-9 defence).

Standard library only. Python 3.9 compatible (CI). JSON writes, if any, use
open(..., newline="").
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Dict, List, Optional, Tuple

MAIN_LEVELS = ("E0", "E1", "E2", "E3", "E4")
INDEP_CLASSES = ("SUPPORT", "NOT_SUPPORT", "INSUFFICIENT",
                 "OBSERVATION_ERROR", "STRUCTURAL")
VERDICT_CLASSES = ("equivalent", "conflict", "protected_abstention")

# Mirror of section 20 D20-E, frozen before any round-13 data. Every cell is
# explicit; there is intentionally NO "unmapped" value anywhere in this table.
MAPPING: Dict[str, str] = {
    "E0|SUPPORT": "conflict",
    "E0|NOT_SUPPORT": "equivalent",
    "E0|INSUFFICIENT": "protected_abstention",
    "E0|OBSERVATION_ERROR": "protected_abstention",
    "E0|STRUCTURAL": "protected_abstention",
    "E1|SUPPORT": "conflict",
    "E1|NOT_SUPPORT": "equivalent",
    "E1|INSUFFICIENT": "protected_abstention",
    "E1|OBSERVATION_ERROR": "protected_abstention",
    "E1|STRUCTURAL": "protected_abstention",
    "E2|SUPPORT": "conflict",
    "E2|NOT_SUPPORT": "equivalent",
    "E2|INSUFFICIENT": "protected_abstention",
    "E2|OBSERVATION_ERROR": "protected_abstention",
    "E2|STRUCTURAL": "protected_abstention",
    "E3|SUPPORT": "conflict",
    "E3|NOT_SUPPORT": "equivalent",
    "E3|INSUFFICIENT": "protected_abstention",
    "E3|OBSERVATION_ERROR": "protected_abstention",
    "E3|STRUCTURAL": "protected_abstention",
    "E4|SUPPORT": "equivalent",
    "E4|NOT_SUPPORT": "conflict",
    "E4|INSUFFICIENT": "protected_abstention",
    "E4|OBSERVATION_ERROR": "protected_abstention",
    "E4|STRUCTURAL": "protected_abstention",
}

# Frozen error-class-level dispositions. These two classes are the protective
# abstentions from the round-9 false-agreement root cause; they must NEVER be
# mapped to a boolean equivalent/conflict (card 禁令 2 / section 20 clause 4).
PROTECTED_ABSTENTION_ERROR_CLASSES = ("SILENT_FALLBACK", "FILE_NOT_FOUND")
ERROR_CLASS_DISPOSITION: Dict[str, str] = {
    "SILENT_FALLBACK": "protected_abstention",
    "FILE_NOT_FOUND": "protected_abstention",
    "PARSE_FAIL": "protected_abstention",
    "CWD_MISMATCH": "protected_abstention",
    "TIMEOUT": "protected_abstention",
    "STRUCTURAL_NO_EVIDENCE": "protected_abstention",
    "NO_EVIDENCE_LINE": "protected_abstention",
    "": "not_applicable",
}
PROTECTED_ABSTENTION_SUBTYPES = {
    "INSUFFICIENT": "no_anchor_policy",
    "OBSERVATION_ERROR": "observation_failure",
    "STRUCTURAL": "structural_unjudgeable",
}

MAP_BEGIN = "<!-- R13-MAPPING-BEGIN -->"
MAP_END = "<!-- R13-MAPPING-END -->"

# main-track E4 is the only boolean "supported" level (round-11 recompute
# caliber): main_supports = (level == "E4").
MAIN_SUPPORTS = {lvl: (lvl == "E4") for lvl in MAIN_LEVELS}
INDEP_SUPPORTS = {"SUPPORT": True, "NOT_SUPPORT": False,
                  "INSUFFICIENT": None, "OBSERVATION_ERROR": None,
                  "STRUCTURAL": None}


def expected_cells() -> List[str]:
    return ["%s|%s" % (m, i) for m in MAIN_LEVELS for i in INDEP_CLASSES]


def read_frozen_matrix(prereg_path: str) -> Dict[str, object]:
    """Extract the section-20 D20-E JSON block; never accept a silent fallback."""
    with open(prereg_path, "r", encoding="utf-8") as fh:
        text = fh.read()
    head = text.find("## §20")
    if head < 0:
        raise ValueError("section 20 not found in prereg")
    s20 = text[head:]
    mb = s20.find(MAP_BEGIN)
    me = s20.find(MAP_END)
    if mb < 0 or me <= mb:
        raise ValueError("section 20 mapping block markers missing/duplicated")
    if s20.count(MAP_BEGIN) != 1 or s20.count(MAP_END) != 1:
        raise ValueError("mapping block markers not unique")
    raw = s20[mb + len(MAP_BEGIN):me]
    j0 = raw.find("{")
    j1 = raw.rfind("}")
    if j0 < 0 or j1 <= j0:
        raise ValueError("no JSON object inside mapping block")
    return json.loads(raw[j0:j1 + 1])


def verify(prereg_path: str) -> Tuple[bool, Dict[str, object]]:
    """Mechanically compare the frozen matrix against the code constant."""
    frozen = read_frozen_matrix(prereg_path)
    cells = frozen.get("cells", {})
    exp = expected_cells()

    unmapped = [c for c in exp if c not in MAPPING or not MAPPING[c]]
    unmapped_frozen = [c for c in exp if c not in cells or not cells[c]]
    extra = sorted(set(cells) - set(exp))
    bad_verdict = sorted(
        c for c in exp
        if c in cells and cells[c] not in VERDICT_CLASSES
    )
    mismatch = sorted(
        c for c in exp
        if c in cells and c in MAPPING and cells[c] != MAPPING[c]
    )
    # protected classes must never be given an equivalent/conflict disposition.
    protected_leaks = [
        c for c in exp
        if cells.get(c) in ("equivalent", "conflict")
        and c.split("|")[1] in ("INSUFFICIENT", "OBSERVATION_ERROR", "STRUCTURAL")
    ]
    ec_leaks = [
        ec for ec in PROTECTED_ABSTENTION_ERROR_CLASSES
        if ERROR_CLASS_DISPOSITION.get(ec) in ("equivalent", "conflict")
    ]
    frozen_protected = list(frozen.get("protected_abstention_error_classes", []))
    frozen_protected_ok = all(
        ec in frozen_protected for ec in PROTECTED_ABSTENTION_ERROR_CLASSES
    )
    # no protected error class may appear anywhere in an equivalent/conflict
    # cell value either (string-level guard, belt and braces).
    string_leaks = [
        "%s:%s" % (c, v)
        for c, v in cells.items()
        if v in ("equivalent", "conflict")
        and any(ec in str(v) for ec in PROTECTED_ABSTENTION_ERROR_CLASSES)
    ]

    report = {
        "schema": frozen.get("schema"),
        "frozen_in": frozen.get("frozen_in"),
        "prereg": prereg_path,
        "cells_expected": len(exp),
        "cells_frozen": len(cells),
        "cells_code": len(MAPPING),
        "unmapped": unmapped + unmapped_frozen,
        "extra_frozen_cells": extra,
        "bad_verdict_cells": bad_verdict,
        "code_vs_frozen_mismatches": mismatch,
        "protected_class_in_boolean_cells": protected_leaks,
        "protected_error_class_disposition_leaks": ec_leaks,
        "protected_error_class_string_leaks": string_leaks,
        "frozen_protected_error_classes": frozen_protected,
        "frozen_protected_error_classes_ok": frozen_protected_ok,
        "verdict_classes": list(frozen.get("verdict_classes", [])),
        "main_levels": list(frozen.get("main_levels", [])),
        "indep_classes": list(frozen.get("indep_classes", [])),
    }
    ok = (not report["unmapped"]
          and not extra
          and not bad_verdict
          and not mismatch
          and not protected_leaks
          and not ec_leaks
          and not string_leaks
          and frozen_protected_ok
          and len(cells) == 25
          and list(frozen.get("verdict_classes", [])) == list(VERDICT_CLASSES)
          and list(frozen.get("main_levels", [])) == list(MAIN_LEVELS)
          and list(frozen.get("indep_classes", [])) == list(INDEP_CLASSES))
    report["verify_pass"] = ok
    return ok, report


def map_pair(main_level: str, indep_class: str) -> str:
    """Look up one of the 25 frozen cells. Raises on anything unmapped."""
    key = "%s|%s" % (main_level, indep_class)
    if key not in MAPPING:
        raise KeyError("unmapped label pair: %s" % key)
    return MAPPING[key]


def disposition_of_error_class(error_class: str) -> str:
    """Frozen error-class disposition; protected classes stay abstentions."""
    return ERROR_CLASS_DISPOSITION.get(error_class, "protected_abstention")


def normalise_indep(level: str) -> str:
    """Map an independent rubric v4 level into one of the 5 frozen classes."""
    if level in ("SUPPORT", "NOT_SUPPORT", "INSUFFICIENT", "OBSERVATION_ERROR"):
        return level
    if level in ("STRUCTURALLY_UNJUDGEABLE", "VERIFIABLE_ABSENCE",
                 "NO_EVIDENCE_LINE", "STRUCTURAL"):
        return "STRUCTURAL"
    raise KeyError("unknown independent level: %s" % level)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify", action="store_true",
                    help="verify the frozen section-20 matrix against code")
    ap.add_argument("--prereg", default="docs/eval-prereg.md",
                    help="path to the frozen prereg document")
    ap.add_argument("--out", default=None,
                    help="optional JSON path to write the verification report")
    args = ap.parse_args(argv)

    if not args.verify:
        print("label_mapping: use --verify --prereg <path>", file=sys.stderr)
        return 2
    try:
        ok, report = verify(args.prereg)
    except (ValueError, OSError) as exc:
        print("VERIFY_ERROR", type(exc).__name__, exc, file=sys.stderr)
        return 3

    print("UNMAPPED", report["unmapped"])
    print("EXTRA_FROZEN_CELLS", report["extra_frozen_cells"])
    print("CODE_VS_FROZEN_MISMATCHES", report["code_vs_frozen_mismatches"])
    print("PROTECTED_CLASS_IN_BOOLEAN_CELLS",
          report["protected_class_in_boolean_cells"])
    print("PROTECTED_ERROR_CLASS_DISPOSITION_LEAKS",
          report["protected_error_class_disposition_leaks"])
    print("FROZEN_PROTECTED_ERROR_CLASSES",
          report["frozen_protected_error_classes"])
    print("CELLS", report["cells_frozen"], "/", report["cells_expected"])
    print("VERIFY_PASS", ok)

    if args.out:
        text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        with open(args.out, "w", newline="", encoding="utf-8") as fh:
            fh.write(text)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
