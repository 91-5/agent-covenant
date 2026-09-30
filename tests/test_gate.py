#!/usr/bin/env python3
"""Tests for tools/gate.py — stdlib unittest only, no third-party deps.

Run from the repository root:
    python -m unittest discover -s tests -v
"""
import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_gate():
    spec = importlib.util.spec_from_file_location("gate", REPO_ROOT / "tools" / "gate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _load_gate()


def _verdict(**overrides):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    base = {
        "id": "AC-20260929-001",
        "artifact": "src/pipeline.py",
        "verdict": "PASS",
        "blockers": 0,
        "conditions": [],
        "independent": True,
        "verifier": "reviewer@acme",
        "ts": now.isoformat().replace("+00:00", "Z"),
        "evidence": ["pytest -q -> 27 passed", "linter exit 0"],
    }
    base.update(overrides)
    return base


class GateTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.vdir = self.tmp / "verdicts"
        self.vdir.mkdir()
        self.addCleanup(self._tmp.cleanup)

    def write_verdict(self, vid, payload):
        (self.vdir / f"{vid}.verdict.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )

    def write_raw(self, vid, text):
        (self.vdir / f"{vid}.verdict.json").write_text(text, encoding="utf-8")

    def run_gate(self, *argv):
        """Run main() capturing output; returns (exit_code, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = gate.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def base_args(self, *extra):
        return ["--verdict-dir", str(self.vdir), *extra]


class TestHappyPath(GateTestCase):
    def test_clean_pass_via_require(self):
        self.write_verdict("AC-20260929-001", _verdict())
        code, out, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001"))
        self.assertEqual(gate.EXIT_OK, code)
        self.assertIn("GATE: PASS", out)

    def test_scans_all_verdicts_when_require_absent(self):
        self.write_verdict("AC-20260929-001", _verdict())
        self.write_verdict("AC-20260929-002", _verdict(id="AC-20260929-002"))
        code, out, _ = self.run_gate(*self.base_args())
        self.assertEqual(gate.EXIT_OK, code)
        self.assertIn("(2 checked)", out)

    def test_json_output_shape(self):
        self.write_verdict("AC-20260929-001", _verdict())
        code, out, _ = self.run_gate(*self.base_args("--json"))
        payload = json.loads(out)
        self.assertEqual(gate.EXIT_OK, code)
        self.assertTrue(payload["ok"])
        self.assertEqual(1, payload["checked"])
        self.assertEqual([], payload["violations"])

    def test_quiet_suppresses_output(self):
        self.write_verdict("AC-20260929-001", _verdict())
        code, out, _ = self.run_gate(*self.base_args("--quiet"))
        self.assertEqual(gate.EXIT_OK, code)
        self.assertEqual("", out)


class TestBlockingRules(GateTestCase):
    def assert_violation(self, code_name, *argv, vid="AC-20260929-001", payload=None, expect_exit=None):
        if payload is not None:
            self.write_verdict(vid, payload)
        exit_code, out, _ = self.run_gate(*self.base_args(*argv))
        self.assertEqual(expect_exit or gate.EXIT_VIOLATION, exit_code, out)
        self.assertIn(code_name, out)
        return out

    def test_missing_verdict_file(self):
        self.assert_violation("MISSING_VERDICT", "--require", "AC-20260929-404")

    def test_unreadable_verdict_json(self):
        self.write_raw("AC-20260929-001", "{not json")
        self.assert_violation("UNREADABLE_VERDICT", "--require", "AC-20260929-001")

    def test_unknown_verdict_value(self):
        self.assert_violation("BAD_VERDICT_VALUE", "--require", "AC-20260929-001",
                              payload=_verdict(verdict="LGTM"))

    def test_blockers_with_pass(self):
        self.assert_violation("BLOCKERS_PRESENT", "--require", "AC-20260929-001",
                              payload=_verdict(blockers=2))

    def test_fail_verdict_blocks(self):
        self.assert_violation("VERDICT_FAIL", "--require", "AC-20260929-001",
                              payload=_verdict(verdict="FAIL", blockers=1))

    def test_conditional_blocked_by_default(self):
        self.assert_violation("CONDITIONAL_NOT_ALLOWED", "--require", "AC-20260929-001",
                              payload=_verdict(verdict="CONDITIONAL", acknowledged_by="15812"))

    def test_conditional_allowed_with_acknowledgement(self):
        self.write_verdict("AC-20260929-001", _verdict(verdict="CONDITIONAL",
                                                       acknowledged_by="15812",
                                                       conditions=["add a regression test"]))
        code, out, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001",
                                                      "--allow-conditional"))
        self.assertEqual(gate.EXIT_OK, code, out)

    def test_conditional_without_acknowledgement_blocks(self):
        self.write_verdict("AC-20260929-001", _verdict(verdict="CONDITIONAL",
                                                       conditions=["follow-up"]))
        self.assert_violation("CONDITIONAL_UNACKNOWLEDGED", "--require", "AC-20260929-001",
                              "--allow-conditional")

    def test_conditional_with_blockers_needs_conditions(self):
        self.write_verdict("AC-20260929-001", _verdict(verdict="CONDITIONAL", blockers=1,
                                                       acknowledged_by="15812", conditions=[]))
        self.assert_violation("CONDITIONAL_NO_CONDITIONS", "--require", "AC-20260929-001",
                              "--allow-conditional")

    def test_non_independent_blocks(self):
        self.assert_violation("NOT_INDEPENDENT", "--require", "AC-20260929-001",
                              payload=_verdict(independent=False))

    def test_non_independent_allowed_explicitly(self):
        self.write_verdict("AC-20260929-001", _verdict(independent=False))
        code, out, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001",
                                                      "--allow-nonindependent"))
        self.assertEqual(gate.EXIT_OK, code, out)

    def test_missing_required_field(self):
        payload = _verdict()
        del payload["verifier"]
        self.assert_violation("MISSING_FIELD", "--require", "AC-20260929-001", payload=payload)

    def test_id_field_mismatch(self):
        self.assert_violation("ID_MISMATCH", "--require", "AC-20260929-001",
                              payload=_verdict(id="AC-20260929-999"))

    def test_empty_evidence_blocks(self):
        self.assert_violation("NO_EVIDENCE", "--require", "AC-20260929-001",
                              payload=_verdict(evidence=[]))


class TestFreshness(GateTestCase):
    def _artifact_map(self, vid, path):
        map_path = self.tmp / "artifacts.json"
        map_path.write_text(json.dumps({vid: [str(path)]}), encoding="utf-8")
        return str(map_path)

    def test_stale_verdict_blocks(self):
        artifact = self.tmp / "src" / "pipeline.py"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("print('hi')", encoding="utf-8")
        old_ts = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat().replace("+00:00", "Z")
        self.write_verdict("AC-20260929-001", _verdict(ts=old_ts))
        code, out, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001",
                                                      "--artifact-map",
                                                      self._artifact_map("AC-20260929-001", artifact)))
        self.assertEqual(gate.EXIT_VIOLATION, code, out)
        self.assertIn("STALE_VERDICT", out)

    def test_fresh_verdict_passes_with_artifact_map(self):
        artifact = self.tmp / "src" / "pipeline.py"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("print('hi')", encoding="utf-8")
        self.write_verdict("AC-20260929-001", _verdict())
        code, out, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001",
                                                      "--artifact-map",
                                                      self._artifact_map("AC-20260929-001", artifact)))
        self.assertEqual(gate.EXIT_OK, code, out)

    def test_missing_artifact_blocks(self):
        self.write_verdict("AC-20260929-001", _verdict())
        ghost = self.tmp / "does-not-exist.py"
        code, out, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001",
                                                      "--artifact-map",
                                                      self._artifact_map("AC-20260929-001", ghost)))
        self.assertEqual(gate.EXIT_VIOLATION, code, out)
        self.assertIn("ARTIFACT_MISSING", out)

    def test_bad_timestamp_blocks(self):
        self.write_verdict("AC-20260929-001", _verdict(ts="not-a-timestamp"))
        self.assertIn("BAD_TIMESTAMP", self.run_gate(*self.base_args("--require", "AC-20260929-001"))[1])


class TestUsageErrors(GateTestCase):
    def test_missing_verdict_dir_is_usage_error(self):
        code, _, err = self.run_gate("--verdict-dir", str(self.tmp / "nope"))
        self.assertEqual(gate.EXIT_USAGE, code)
        self.assertIn("verdict directory not found", err)

    def test_unreadable_artifact_map_is_usage_error(self):
        bad_map = self.tmp / "bad.json"
        bad_map.write_text("{oops", encoding="utf-8")
        code, _, err = self.run_gate(*self.base_args("--artifact-map", str(bad_map)))
        self.assertEqual(gate.EXIT_USAGE, code)
        self.assertIn("cannot parse artifact map", err)

    def test_empty_verdict_dir_without_require_passes_vacuously(self):
        code, out, _ = self.run_gate(*self.base_args())
        self.assertEqual(gate.EXIT_OK, code)
        self.assertIn("(0 checked)", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
