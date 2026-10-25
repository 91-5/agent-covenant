#!/usr/bin/env python3
"""Tests for the M3 gate-interception probe (XJ-20261024-003 D3).

Two things must hold at once:

* the five defect classes are really intercepted and the clean round really
  passes (the measurement is correct);
* the measurement comes from the REAL tools as subprocesses -- if the probe
  ever started re-implementing gate rules, a green M3 would mean nothing.
  The card explicitly allows a mock assertion for this: the tests watch
  every subprocess invocation and check it targets the repository's own
  tools/gate.py and tools/lint_cards.py.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = REPO_ROOT / "tools" / "eval"

if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

import m3_probe  # noqa: E402


class ProbeOutcomeTests(unittest.TestCase):
    """The card's acceptance: M3-1..5 all caught; M3-6 clean round passes."""

    @classmethod
    def setUpClass(cls):
        cls.results = m3_probe.run_probe()

    def test_intercepts_all_five_defect_classes(self):
        for class_id in ("M3-1", "M3-2", "M3-3", "M3-4", "M3-5"):
            entry = self.results[class_id]
            self.assertTrue(entry["caught"], f"{class_id} was not intercepted")
            self.assertEqual(entry["exit_code"], 1, f"{class_id} exit code")

    def test_clean_round_passes_both_tools(self):
        entry = self.results["M3-6"]
        self.assertFalse(entry["caught"], "clean round blocked -- false positive")
        self.assertEqual(entry["detail"]["gate_exit"], 0)
        self.assertEqual(entry["detail"]["lint_exit"], 0)
        self.assertEqual(entry["violations"], [])

    def test_each_class_hits_its_own_violation_code(self):
        """The gate must block for the RIGHT reason: a stale fixture that
        failed on an unrelated rule would make M3 a number without meaning."""
        expectations = {
            "M3-1": "MISSING_VERDICT",
            "M3-2": "STALE_VERDICT",
            "M3-3": "BLOCKERS_PRESENT",
            "M3-4": "UNMAPPED_CLAIM_SURFACE",
            "M3-5": "LINK_VERDICT_SHA_MISMATCH",
        }
        for class_id, code in expectations.items():
            self.assertIn(code, self.results[class_id]["violations"], class_id)

    def test_summary_passes_only_when_both_sides_hold(self):
        summary = self.results["summary"]
        self.assertEqual(summary["intercepted"], "5/5")
        self.assertEqual(summary["false_positive_rate"], 0.0)
        self.assertEqual(summary["m3"], "PASS")


class RealToolBoundaryTests(unittest.TestCase):
    """Constraint 3: the probe must invoke the real tools as subprocesses.
    Watching the subprocess calls is the card-sanctioned mock assertion."""

    def test_every_invocation_targets_the_repository_tools(self):
        calls = []
        real_run = m3_probe.subprocess.run

        def spy(*args, **kwargs):
            calls.append(args[0] if args else kwargs.get("args"))
            return real_run(*args, **kwargs)

        with mock.patch.object(m3_probe.subprocess, "run", spy):
            results = m3_probe.run_probe()
        self.assertTrue(calls, "probe must spawn subprocesses")
        for argv in calls:
            tool = Path(argv[1])
            self.assertIn(str(tool), {str(m3_probe.GATE), str(m3_probe.LINT)},
                          f"unexpected tool invoked: {tool}")
            self.assertTrue(tool.is_file(),
                            "invoked tool must be the repository's real file")
        self.assertEqual(results["summary"]["m3"], "PASS")

    def test_gate_and_lint_are_invoked_as_scripts_not_imported(self):
        """A subprocess boundary (python <script>) is what makes the probe an
        observer: the tools' own __main__ must run, not an in-process import
        the probe could accidentally perturb."""
        calls = []
        real_run = m3_probe.subprocess.run

        def spy(*args, **kwargs):
            calls.append((args[0] if args else kwargs.get("args"), kwargs))
            return real_run(*args, **kwargs)

        with mock.patch.object(m3_probe.subprocess, "run", spy):
            m3_probe.run_probe()
        for argv, kwargs in calls:
            self.assertEqual(argv[0], sys.executable)
            self.assertIn("--json", argv)
            self.assertTrue(kwargs.get("capture_output"))


if __name__ == "__main__":
    unittest.main()
