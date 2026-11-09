#!/usr/bin/env python3
"""v1.7 command_output predicates (docs/eval-prereg.md §14; card
XJ-20261108-003 D1, frozen BEFORE round-7 data exists).

 WHAT FROZE HERE
 ---------------
 Four command_output predicates closing the round-6 frozen-enum gap (the
 round-6 shadow compile reported ``predicate not in frozen enum`` for
 command-output assertions — an instrument gap, not an executor difference):

 * ``command_exit_code``        — the verification command exits with the
                                  expected integer code.
 * ``command_stdout_contains``  — the combined stdout/stderr text contains the
                                  expected substring EXACTLY (same caliber as
                                  the main judge's out= check; trailing
                                  line-endings stripped, no other
                                  normalization, no semantic comparison).
 * ``command_stdout_regex``     — the combined output matches the expected
                                  Python-re pattern (search), executed under
                                  the 30s timeout guard; a guard timeout is
                                  recorded as an observation failure with the
                                  regex_timeout flag.
 * ``command_artifact_created`` — the expected path exists as a file under the
                                  observation root after the verification
                                  command ran.

 All four require the COMMAND form (verification_command present) and are
 invalid on artifact-only records (surface coupling, validated below).

 B-ARM (§13 ⑨ / §14): on arm-B records the verification_command carries the
 frozen ``B-ARM-NOT-EXECUTED::`` prefix; the evaluator strips the prefix and
 executes the remainder at the same caliber as arm A. Round 7 additionally
 freezes a structural not_applicable marking for arm-B command_output claims
 whose criterion is design-unexecutable — see docs/b-arm-notapplicable-rules.md
 (frozen before round-7 data).

 SCHEMA HASH (pre-registered, acceptance V1)
 -------------------------------------------
 The sha256 of THIS file is recorded in docs/eval-prereg.md §14 as
 PREREG_SCHEMA_HASH. Any byte changed here after the freeze invalidates the
 round-7 run (pre-registration discipline: freeze -> offline replay -> data).

 GRADING PSEUDOCODE (frozen; shared by every command_* predicate)
 ----------------------------------------------------------------
     observed  = execute(verification_command, cwd=root, timeout=30)
                 # exit_code, combined_output  (judge.run_command + C11 dispatch)
     predicate_ok =
         command_exit_code         : observed.exit_code == int(expected)
         command_stdout_contains   : expected in observed.output
         command_stdout_regex      : re.search(expected, observed.output)
                                     under 30s guard; timeout -> fail + flag
         command_artifact_created  : (root / expected).is_file()
     level-facing boolean  = predicate_ok
     flags                 = [regex_timeout] (only on guard timeout)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

#: v1.7 schema version (frozen; §14).
SCHEMA_VERSION = "v1.7"

#: The four command_output predicates added by v1.7.
COMMAND_PREDICATES_V17 = (
    "command_exit_code",
    "command_stdout_contains",
    "command_stdout_regex",
    "command_artifact_created",
)

#: Regex guard seconds (§12 D3 discipline carried into v1.7).
REGEX_GUARD_SECONDS = 30


def validate_v17_command_record(record: Dict[str, object]) -> List[str]:
    """v1.7 additions to record validation: command_* surface coupling and
    expected typing. Returns violations (empty = valid)."""
    errors: List[str] = []
    predicate = record.get("predicate")
    if predicate not in COMMAND_PREDICATES_V17:
        return errors  # not a v1.7 command predicate — nothing to add
    command = record.get("verification_command")
    if not (isinstance(command, str) and command.strip()):
        errors.append(f"{predicate}: requires verification_command form")
    if predicate in ("command_exit_code",):
        exp = record.get("expected")
        if isinstance(exp, bool) or not isinstance(exp, int):
            errors.append("command_exit_code: expected must be an int")
    else:
        exp = record.get("expected")
        if not isinstance(exp, str) or not exp.strip():
            errors.append(f"{predicate}: expected must be a non-empty string")
    return errors


def grade_command_predicate(predicate: str, expected: object,
                            exit_code: object, output: str, root: Path,
                            flags: List[str]) -> bool:
    """Mechanical grading of one v1.7 command predicate against an executed
    observation. ``flags`` is mutated in place (regex_timeout)."""
    if predicate == "command_exit_code":
        return exit_code is not None and exit_code == expected
    if predicate == "command_stdout_contains":
        return str(expected) in (output or "")
    if predicate == "command_stdout_regex":
        from dsl_compiler import regex_search_guarded
        found, guard_flags = regex_search_guarded(
            str(expected), output or "", REGEX_GUARD_SECONDS)
        flags.extend(guard_flags)
        return found is True
    if predicate == "command_artifact_created":
        rel = str(expected).replace("\\", "/")
        if ".." in rel.split("/"):
            flags.append("artifact_path_out_of_bounds")
            return False
        return (Path(root) / rel).is_file()
    raise ValueError(f"not a v1.7 command predicate: {predicate!r}")


def schema_hash() -> str:
    """SHA-256 of THIS file — the value pre-registered in §14 (acceptance V1
    compares the on-disk hash against the frozen prereg value)."""
    import hashlib

    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


if __name__ == "__main__":
    print(f"predicates {SCHEMA_VERSION}: {', '.join(COMMAND_PREDICATES_V17)}")
    print(f"schema sha256: {schema_hash()}")
