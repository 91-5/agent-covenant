#!/usr/bin/env python3
"""v1.6 diagnostic emitter + §13 isolation tests (card XJ-20261108-002).

C12: synthetic claims only; no sealed package is read here.

Pinned properties:
 * every emitted record carries diagnostic_only=true in the JSONL meta line;
 * B-arm records carry the §13 ⑨ frozen prefix on verification_command;
 * the compiler strips the prefix and executes the remainder (provenance
   flag b_arm_not_executed, same caliber as arm A);
 * the shadow alignment payload contains NO E0-E4 level tokens (A8, ADV-3);
 * emitted records validate against the §12 schema (mechanical derivation).

Run from the repository root:
    python -m unittest discover -s tests
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = REPO_ROOT / "tools" / "eval"

if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

import dsl_compiler  # noqa: E402
import dsl_emit  # noqa: E402
import shadow_align  # noqa: E402
from schema import validate_dsl_record  # noqa: E402


def claim(level_ignore, line, text="断言", command="python -c \"print('ok')\"",
          exit_code=0, out="ok"):
    return {"text": text, "source_line": line, "product": "P901",
            "evidence": {"raw": "x", "command": command, "exit_code": exit_code,
                         "out": out, "ref": None},
            "anchors": [], "unanchored": True}


class EmitTests(unittest.TestCase):
    def test_meta_carries_diagnostic_only(self):
        with tempfile.TemporaryDirectory() as raw:
            out = Path(raw) / "d.jsonl"
            dsl_emit.main(["--claims", _write_claims(raw), "--arm", "A",
                           "--out", str(out)])
            first = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
            self.assertIs(first["_meta"]["diagnostic_only"], True)

    def test_b_arm_records_carry_frozen_prefix(self):
        with tempfile.TemporaryDirectory() as raw:
            out = Path(raw) / "b.jsonl"
            dsl_emit.main(["--claims", _write_claims(raw), "--arm", "B",
                           "--out", str(out)])
            rows = [json.loads(l) for l in
                    out.read_text(encoding="utf-8").splitlines()[1:]]
            with_cmd = [r for r in rows if r["verification_command"]]
            self.assertTrue(with_cmd)
            for r in with_cmd:
                self.assertTrue(r["verification_command"].startswith(
                    dsl_emit.B_ARM_PREFIX), r["verification_command"])

    def test_records_validate_against_frozen_schema(self):
        with tempfile.TemporaryDirectory() as raw:
            out = Path(raw) / "a.jsonl"
            dsl_emit.main(["--claims", _write_claims(raw), "--arm", "A",
                           "--out", str(out)])
            rows = [json.loads(l) for l in
                    out.read_text(encoding="utf-8").splitlines()[1:]]
            for r in rows:
                # ref-form claims emit artifact_path (valid); command-form too
                self.assertEqual(schema_errors(r), [],
                                 r.get("schema_errors", "unexpected"))

    def test_prefix_stripped_and_executed_same_caliber(self):
        # §13 ⑨: provenance only — the evaluator strips and executes
        record = {"claim_id": "c1", "claim_type": "command_output",
                  "statement": "s",
                  "verification_command": dsl_emit.B_ARM_PREFIX + "python -c \"pass\"",
                  "artifact_path": None, "evidence_span": [1, 2],
                  "predicate": "exit_equals", "expected": 0}
        with tempfile.TemporaryDirectory() as raw:
            r = dsl_compiler.execute_record(record, Path(raw))
        self.assertTrue(r["predicate_ok"])
        self.assertIn("b_arm_not_executed", r["flags"])


class ZeroETokenTests(unittest.TestCase):
    """A8 / ADV-3: the shadow payload contains no E0-E4 level tokens."""

    def test_alignment_payload_has_no_e_tokens(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            mains = [{"text": "断言", "source_line": 10, "product": "P901",
                      "evidence": {"raw": "x"}, "anchors": [],
                      "unanchored": True, "_level": "E4", "level": "E4"}]
            recs = [{"claim_id": "a", "claim_type": "command_output",
                     "statement": "s", "verification_command": "python -c \"pass\"",
                     "artifact_path": None, "evidence_span": [10, 11],
                     "predicate": "exit_equals", "expected": 0}]
            r = shadow_align.align({"P901": mains}, {"P901": recs}, root)
        payload = json.dumps(r, ensure_ascii=False)
        for token in ("E0", "E1", "E2", "E3", "E4"):
            self.assertNotIn(token, payload, token)
        # even though the MAIN snapshot carried levels, none leaked through

    def test_diag_jsonl_has_no_e_tokens(self):
        with tempfile.TemporaryDirectory() as raw:
            out = Path(raw) / "d.jsonl"
            dsl_emit.main(["--claims", _write_claims(raw), "--arm", "A",
                           "--out", str(out)])
            payload = out.read_text(encoding="utf-8")
        for token in ("E0", "E1", "E2", "E3", "E4"):
            self.assertNotIn(token, payload, token)


def schema_errors(record):
    return validate_dsl_record(record)


def _write_claims(raw: str) -> str:
    claims = {"P901": [
        claim("x", 10, command="python -c \"pass\"", exit_code=0, out=None),
        claim("x", 20, command=None, exit_code=None, out=None),
    ]}
    claims["P901"][1]["evidence"] = {"raw": "ref=x", "command": None,
                                     "exit_code": None, "out": None,
                                     "ref": "LICENSE"}
    p = Path(raw) / "claims.json"
    p.write_text(json.dumps(claims, ensure_ascii=False), encoding="utf-8")
    return str(p)


if __name__ == "__main__":
    unittest.main()
