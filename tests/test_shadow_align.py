#!/usr/bin/env python3
"""v1.6 shadow-track aligner tests (card XJ-20261108-001 D2, §12 D4).

Synthetic data only (C12). Isolation guarantees pinned here: the aligner
output carries no E-level sequence and no endpoint numbers — per-claim outputs
are booleans and gap classes only; the frozen 95% gate is reported, never
decided by the tool.

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

import shadow_align  # noqa: E402

align = shadow_align.align


class AlignmentRateTests(unittest.TestCase):
    def _main(self, level, line):
        return {"text": "断言", "source_line": line, "product": "P901",
                "evidence": {"raw": "x"}, "anchors": [], "unanchored": True,
                "_level": level}

    def _rec(self, cid, line, ok=True):
        command = "python -c \"pass\"" if ok else \
            "python -c \"import sys;sys.exit(3)\""
        return {"claim_id": cid, "claim_type": "command_output",
                "statement": "s " + cid, "verification_command": command,
                "artifact_path": None, "evidence_span": [line, line + 1],
                "predicate": "exit_equals", "expected": 0}

    def _align(self, mains, recs):
        with tempfile.TemporaryDirectory() as raw:
            return align({"P901": mains}, {"P901": recs}, Path(raw))

    def test_perfect_one_to_one_dual_rates(self):
        r = self._align([self._main("E4", 10), self._main("E2", 20)],
                        [self._rec("a", 10, ok=True),
                         self._rec("b", 20, ok=False)])
        self.assertEqual(r["totals"]["alignment_rate"], 1.0)
        self.assertEqual(r["totals"]["agreement_rate"], 1.0)
        self.assertEqual(r["totals"]["aligned_pairs"], 2)

    def test_uncovered_main_counts_against_alignment(self):
        r = self._align([self._main("E4", 10), self._main("E4", 50)],
                        [self._rec("only", 10)])
        self.assertEqual(r["totals"]["alignment_rate"], 0.5)

    def test_span_multi_match_is_anchor_gap(self):
        wide = self._rec("wide", 10)
        wide["evidence_span"] = [10, 13]
        r = self._align([self._main("E4", 10), self._main("E4", 12)], [wide])
        self.assertIn("wide", r["per_product"]["P901"]["gaps"]["anchor"])
        self.assertEqual(r["totals"]["aligned_pairs"], 0)

    def test_duplicate_coverage_is_anchor_gap(self):
        r = self._align([self._main("E4", 10)],
                        [self._rec("d1", 10), self._rec("d2", 10)])
        self.assertEqual(r["totals"]["aligned_pairs"], 0)
        self.assertLessEqual({"d1", "d2"},
                             set(r["per_product"]["P901"]["gaps"]["anchor"]))


class AgreementTests(unittest.TestCase):
    def _main(self, level, line):
        return {"text": "断言", "source_line": line, "product": "P901",
                "evidence": {"raw": "x"}, "anchors": [], "unanchored": True,
                "_level": level}

    def _rec(self, cid, line, ok=True):
        command = "python -c \"pass\"" if ok else \
            "python -c \"import sys;sys.exit(3)\""
        return {"claim_id": cid, "claim_type": "command_output",
                "statement": "s " + cid, "verification_command": command,
                "artifact_path": None, "evidence_span": [line, line + 1],
                "predicate": "exit_equals", "expected": 0}

    def _align(self, mains, recs):
        with tempfile.TemporaryDirectory() as raw:
            return align({"P901": mains}, {"P901": recs}, Path(raw))

    def test_semantic_gap_when_predicate_contradicts_main(self):
        r = self._align([self._main("E2", 10)], [self._rec("s", 10, ok=True)])
        self.assertIn("s", r["per_product"]["P901"]["gaps"]["semantic"])
        self.assertIs(r["per_product"]["P901"]["consistent_flags"]["s"], False)
        self.assertEqual(r["totals"]["agreement_rate"], 0.0)

    def test_syntax_gap_for_schema_invalid_record(self):
        bad = self._rec("bad", 10)
        bad["claim_type"] = "evaluative"
        bad["predicate"] = "equals"
        r = self._align([self._main("E4", 10)], [bad])
        self.assertIn("bad", r["per_product"]["P901"]["gaps"]["syntax"])
        self.assertEqual(r["totals"]["comparable_pairs"], 0)

    def test_evaluative_record_in_own_bucket(self):
        ev = {"claim_id": "ev", "claim_type": "evaluative", "statement": "评价",
              "verification_command": None, "artifact_path": None,
              "evidence_span": [10, 11], "predicate": None, "expected": None}
        r = self._align([self._main("E2", 10)], [ev])
        self.assertEqual(r["per_product"]["P901"]["evaluative_count"], 1)
        self.assertEqual(r["totals"]["comparable_pairs"], 0)
        self.assertIsNone(r["totals"]["agreement_rate"])


class IsolationTests(unittest.TestCase):
    def test_output_carries_no_level_sequence(self):
        with tempfile.TemporaryDirectory() as raw:
            mains = [{"text": "断言", "source_line": 10, "product": "P901",
                      "evidence": {"raw": "x"}, "anchors": [],
                      "unanchored": True, "_level": "E4"}]
            recs = [{"claim_id": "a", "claim_type": "command_output",
                     "statement": "s", "verification_command": "python -c \"pass\"",
                     "artifact_path": None, "evidence_span": [10, 11],
                     "predicate": "exit_equals", "expected": 0}]
            r = align({"P901": mains}, {"P901": recs}, Path(raw))
        payload = json.dumps(r)
        # no E-level sequence anywhere in the shadow output
        self.assertNotIn('"level"', payload)
        self.assertNotIn('"E4"', payload)
        # booleans only for the aligned pairs
        self.assertEqual(r["per_product"]["P901"]["consistent_flags"], {"a": True})

    def test_gate_reported_never_enforced(self):
        with tempfile.TemporaryDirectory() as raw:
            mains = [{"text": "断言", "source_line": 10, "product": "P901",
                      "evidence": {"raw": "x"}, "anchors": [],
                      "unanchored": True, "_level": "E4"}]
            recs = [{"claim_id": "a", "claim_type": "command_output",
                     "statement": "s", "verification_command": "python -c \"pass\"",
                     "artifact_path": None, "evidence_span": [10, 11],
                     "predicate": "exit_equals", "expected": 0}]
            r = align({"P901": mains}, {"P901": recs}, Path(raw))
        self.assertEqual(r["totals"]["agreement_gate"], 0.95)
        # no "PASS/FAIL verdict" field exists in the output at all
        self.assertNotIn("verdict", json.dumps(r))


if __name__ == "__main__":
    unittest.main()
