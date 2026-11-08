#!/usr/bin/env python3
"""v1.6 DSL compiler tests (card XJ-20261108-001 D1, §12 D1-D3 frozen schema).

Synthetic data only (C12). The compiler must be zero-discretion: schema
validation is mechanical, predicates execute mechanically, and there is no
natural-language understanding anywhere (acceptance 7 greps the source too).

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

import dsl_compiler as dc  # noqa: E402
import judge  # noqa: E402
import schema  # noqa: E402
import shadow_align  # noqa: E402

sa_align = shadow_align.align


def rec(cid="c1", ctype="command_output", pred="exit_equals", expected=0,
        command=None, artifact=None, span=(1, 2)):
    return {"claim_id": cid, "claim_type": ctype, "statement": "s " + cid,
            "verification_command": command, "artifact_path": artifact,
            "evidence_span": list(span), "predicate": pred,
            "expected": expected}


class SchemaValidationTests(unittest.TestCase):
    """§12 D1/D2/D3 frozen-schema validation (schema.py additions only)."""

    def test_valid_record_zero_errors(self):
        self.assertEqual(schema.validate_dsl_record(
            rec(command="python -c \"pass\"")), [])

    def test_missing_field_rejected(self):
        bad = rec()
        del bad["predicate"]
        errors = schema.validate_dsl_record(bad)
        self.assertTrue(any("missing field: predicate" in e for e in errors))

    def test_bad_claim_type_rejected(self):
        errors = schema.validate_dsl_record(rec(ctype="emotional"))
        self.assertTrue(any("claim_type not in frozen enum" in e for e in errors))

    def test_bad_predicate_rejected(self):
        errors = schema.validate_dsl_record(rec(pred="seems_right"))
        self.assertTrue(any("predicate not in frozen enum" in e for e in errors))

    def test_frozen_set_sizes(self):
        # §12: exactly 8 fields / 5 claim types / 9 predicates
        self.assertEqual(len(schema.DSL_FIELDS), 8)
        self.assertEqual(len(schema.DSL_CLAIM_TYPES), 5)
        self.assertEqual(len(schema.DSL_PREDICATES), 9)

    def test_evaluative_must_not_carry_predicate(self):
        errors = schema.validate_dsl_record(
            rec(cid="ev", ctype="evaluative", pred="equals", expected="x"))
        self.assertTrue(any("evaluative" in e and "predicate" in e for e in errors))

    def test_evaluative_without_predicate_valid(self):
        clean = {"claim_id": "ev", "claim_type": "evaluative", "statement": "评价",
                 "verification_command": None, "artifact_path": None,
                 "evidence_span": [1, 1], "predicate": None, "expected": None}
        self.assertEqual(schema.validate_dsl_record(clean), [])

    def test_both_sources_rejected(self):
        errors = schema.validate_dsl_record(
            rec(command="python -c \"pass\"", artifact="a.txt"))
        self.assertTrue(any("both" in e for e in errors))

    def test_neither_source_rejected(self):
        errors = schema.validate_dsl_record(rec(command="", artifact=None))
        self.assertTrue(any("neither" in e for e in errors))

    def test_bad_span_rejected(self):
        errors = schema.validate_dsl_record(rec(span=(5, 2)))
        self.assertTrue(any("evidence_span" in e for e in errors))

    def test_exact_answer_requires_command_form(self):
        # surface coupling: exact_answer compares command output
        errors = schema.validate_dsl_record(
            rec(pred="exact_answer", expected="MIT", command=None,
                artifact="answer.txt"))
        self.assertTrue(any("requires verification_command" in e for e in errors))

    def test_exit_equals_requires_command_form(self):
        errors = schema.validate_dsl_record(
            rec(pred="exit_equals", expected=0, command=None, artifact="a.txt"))
        self.assertTrue(any("requires verification_command" in e for e in errors))

    def test_exists_requires_artifact_form(self):
        errors = schema.validate_dsl_record(rec(pred="exists", expected="x"))
        self.assertTrue(any("requires artifact_path" in e for e in errors))


class PredicateExecutionTests(unittest.TestCase):
    """All 9 predicates, positive + negative, mechanical only."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "answer.txt").write_text("MIT\n", encoding="utf-8", newline="")
        (self.root / "doc.md").write_text("# head\nbody line\n",
                                          encoding="utf-8", newline="")
        (self.root / "data.json").write_text('{"a": {"b": "yes"}}',
                                             encoding="utf-8", newline="")
        (self.root / "three.txt").write_text("1\n2\n3\n",
                                             encoding="utf-8", newline="")

    def tearDown(self):
        self._tmp.cleanup()

    def run_rec(self, r):
        return dc.execute_record(r, self.root)

    def test_exists_positive_and_negative(self):
        self.assertTrue(self.run_rec(
            rec(cid="p", ctype="fact_existence", pred="exists", expected="x",
                artifact="answer.txt"))["predicate_ok"])
        self.assertFalse(self.run_rec(
            rec(cid="n", ctype="fact_existence", pred="exists", expected="x",
                command=None, artifact="gone.txt"))["predicate_ok"])

    def test_not_exists_positive_and_negative(self):
        self.assertTrue(self.run_rec(
            rec(cid="p", ctype="fact_existence", pred="not_exists", expected="x",
                artifact="gone.txt"))["predicate_ok"])
        self.assertFalse(self.run_rec(
            rec(cid="n", ctype="fact_existence", pred="not_exists", expected="x",
                artifact="answer.txt"))["predicate_ok"])

    def test_equals_positive_and_negative(self):
        self.assertTrue(self.run_rec(
            rec(cid="p", pred="equals", expected="1",
                command="python -c \"print(1)\""))["predicate_ok"])
        self.assertFalse(self.run_rec(
            rec(cid="n", pred="equals", expected="2",
                command="python -c \"print(1)\""))["predicate_ok"])

    def test_contains_positive_and_negative(self):
        self.assertTrue(self.run_rec(
            rec(cid="p", ctype="fact_value", pred="contains", expected="body line",
                command=None, artifact="doc.md"))["predicate_ok"])
        self.assertFalse(self.run_rec(
            rec(cid="n", ctype="fact_value", pred="contains", expected="absent",
                command=None, artifact="doc.md"))["predicate_ok"])

    def test_matches_regex_positive_and_negative(self):
        self.assertTrue(self.run_rec(
            rec(cid="p", pred="matches_regex", expected=r"^\[1\]$",
                command="python -c \"print('[1]')\""))["predicate_ok"])
        self.assertFalse(self.run_rec(
            rec(cid="n", pred="matches_regex", expected=r"^\[9\]$",
                command="python -c \"print('[1]')\""))["predicate_ok"])

    def test_json_path_equals_positive_negative_and_convention(self):
        r = self.run_rec(rec(cid="p", ctype="fact_value", pred="json_path_equals",
                             expected="a.b->yes", command=None, artifact="data.json"))
        self.assertTrue(r["predicate_ok"])
        n = self.run_rec(rec(cid="n", ctype="fact_value", pred="json_path_equals",
                             expected="a.b->no", command=None, artifact="data.json"))
        self.assertFalse(n["predicate_ok"])
        c = self.run_rec(rec(cid="c", ctype="fact_value", pred="json_path_equals",
                             expected="a.b", command=None, artifact="data.json"))
        self.assertIn("json_path_convention_missing", c["flags"])

    def test_line_count_equals_positive_and_negative(self):
        self.assertTrue(self.run_rec(
            rec(cid="p", ctype="fact_value", pred="line_count_equals", expected=3,
                command=None, artifact="three.txt"))["predicate_ok"])
        self.assertFalse(self.run_rec(
            rec(cid="n", ctype="fact_value", pred="line_count_equals", expected=9,
                command=None, artifact="three.txt"))["predicate_ok"])

    def test_exit_equals_positive_and_negative(self):
        self.assertTrue(self.run_rec(
            rec(cid="p", pred="exit_equals", expected=0,
                command="python -c \"pass\""))["predicate_ok"])
        self.assertFalse(self.run_rec(
            rec(cid="n", pred="exit_equals", expected=0,
                command="python -c \"import sys;sys.exit(3)\""))["predicate_ok"])

    def test_exact_answer_exact_compare_only(self):
        # exact hit (trailing line ending normalization only)
        self.assertTrue(self.run_rec(
            rec(cid="p", ctype="fact_value", pred="exact_answer", expected="MIT",
                command="python -c \"print('MIT')\""))["predicate_ok"])
        # semantic equivalence ("MIT" vs "MIT License") must NOT pass
        self.assertFalse(self.run_rec(
            rec(cid="n", ctype="fact_value", pred="exact_answer",
                expected="MIT License", command="python -c \"print('MIT')\""))["predicate_ok"])

    def test_regex_timeout_guard_flags(self):
        # catastrophic backtracking under a short guard -> flag, no crash
        found, flags = dc.regex_search_guarded("(a+)+$", "a" * 40 + "x", timeout=2)
        self.assertIsNone(found)
        self.assertIn("regex_timeout", flags)

    def test_denylist_refusal(self):
        r = self.run_rec(rec(cid="d", pred="exit_equals", expected=0,
                             command="del /f something.txt"))
        self.assertEqual(r["predicate_ok"], False)
        self.assertIn("refused_exec", r["flags"])

    def test_artifact_path_out_of_bounds(self):
        r = self.run_rec(rec(cid="o", ctype="fact_existence", pred="exists",
                             expected="x", command=None, artifact="../etc/passwd"))
        self.assertIn("artifact_path_out_of_bounds", r["flags"])


if __name__ == "__main__":
    unittest.main()
