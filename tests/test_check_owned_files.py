#!/usr/bin/env python3
"""Tests for tools/check_owned_files.py — stdlib unittest only.

Run from the repository root:
    python -m unittest discover -s tests -v

The point of these tests is the *shadow period* contract: findings are data,
never a verdict. So the assertions that matter most are about the exit code
staying 0 and about a missing Card-Id trailer degrading to "unknown" instead of
"violation". A tool that blocks before its false-positive rate is known is an
outage, not a measurement (EVO-20261007-001, decision 2).
"""
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check = _load("check_owned_files")


CARD = """# TASK XJ-20261007-001: touch two files

- **Author:** opencode@agent-covenant
- **Created:** 2026-10-07

## Context
ctx

## Deliverables
- a

## Owned files

- `src/allowed.py`
- `src/nested/`

## Constraints
- none

## Acceptance
- python -m unittest exits 0

## Status
OPEN
"""

CARD_CLOSED = CARD.replace("OPEN", "CLOSED").replace("XJ-20261007-001", "XJ-20260901-001")


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class WhitelistTests(unittest.TestCase):
    def test_missing_file_is_reported_not_treated_as_empty_permission(self):
        """A missing whitelist must surface, not fail open silently."""
        paths, invalid, missing = check.load_whitelist(REPO_ROOT / "no-such-whitelist.yml")
        self.assertEqual((paths, invalid), ([], []))
        self.assertTrue(missing)

    def test_exact_path_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            wl = Path(tmp) / "wl.yml"
            _write(wl, "paths:\n  - path: docs/shared.md\n    owner: sir\n")
            paths, invalid, _ = check.load_whitelist(wl)
            self.assertEqual(paths, ["docs/shared.md"])
            self.assertEqual(invalid, [])

    def test_glob_and_directory_claims_refused(self):
        """A glob in an exception list is a universal escape hatch."""
        with tempfile.TemporaryDirectory() as tmp:
            wl = Path(tmp) / "wl.yml"
            _write(wl, "paths:\n  - path: schema/**\n  - path: tools/\n  - path: /etc/passwd\n")
            paths, invalid, _ = check.load_whitelist(wl)
            self.assertEqual(paths, [])
            self.assertEqual(len(invalid), 3)

    def test_shipped_whitelist_is_empty_and_legal(self):
        """The shipped policy file must itself pass its own validator."""
        paths, invalid, _ = check.load_whitelist(REPO_ROOT / "policy" / "owned-files-whitelist.yml")
        self.assertEqual(paths, [])
        self.assertEqual(invalid, [])


class NormalisationTests(unittest.TestCase):
    def test_backslashes_become_forward_slashes(self):
        self.assertEqual(check._norm("src\\deep\\file.py"), "src/deep/file.py")

    def test_leading_dot_slash_is_dropped(self):
        self.assertEqual(check._norm("./src/file.py"), "src/file.py")


class EvaluateTests(unittest.TestCase):
    """`evaluate` is exercised with the git layer faked — no repo required."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.cards = self.root / ".tasks"
        _write(self.cards / "XJ-20261007-001.md", CARD)
        _write(self.cards / "XJ-20260901-001.md", CARD_CLOSED)
        self.wl = self.root / "wl.yml"
        _write(self.wl, "paths: []\n")
        self._orig = (check.collect_trailer_card_ids, check.changed_paths, check.resolve_base,
                     check.trailer_adoption)
        check.resolve_base = lambda repo, spec: ("base123", None)
        check.trailer_adoption = lambda repo, base, head="HEAD": (3, 3)

    def tearDown(self):
        (check.collect_trailer_card_ids, check.changed_paths,
         check.resolve_base, check.trailer_adoption) = self._orig
        self._tmp.cleanup()

    def _run(self, card_ids, pairs):
        check.collect_trailer_card_ids = lambda repo, base, head="HEAD": list(card_ids)
        check.changed_paths = lambda repo, base, head="HEAD": list(pairs)
        return check.evaluate(self.root, self.cards, "auto", "HEAD", self.wl)

    def test_owned_path_is_not_a_violation(self):
        payload = self._run(["XJ-20261007-001"], [("M", "src/allowed.py")])
        self.assertEqual(payload["violations"], [])
        self.assertEqual(payload["authorized_card_ids"], ["XJ-20261007-001"])

    def test_directory_claim_covers_subtree(self):
        payload = self._run(["XJ-20261007-001"], [("M", "src/nested/deep/file.py")])
        self.assertEqual(payload["violations"], [])

    def test_unowned_path_is_a_violation(self):
        payload = self._run(["XJ-20261007-001"], [("M", "tools/gate.py")])
        self.assertEqual([v["path"] for v in payload["violations"]], ["tools/gate.py"])

    def test_rename_contributes_both_paths(self):
        """A rename can move a file *out* of an owned path; both sides count."""
        payload = self._run(
            ["XJ-20261007-001"],
            [("R100", "src/allowed.py"), ("R100", "elsewhere/stolen.py")],
        )
        self.assertEqual([v["path"] for v in payload["violations"]], ["elsewhere/stolen.py"])

    def test_whitelisted_path_is_not_a_violation(self):
        _write(self.wl, "paths:\n  - path: tools/shared.md\n    owner: sir\n")
        payload = self._run(["XJ-20261007-001"], [("M", "tools/shared.md")])
        self.assertEqual(payload["violations"], [])
        self.assertEqual(payload["metrics"]["whitelist_hits"], 1)

    def test_missing_trailer_is_unknown_not_violation(self):
        payload = self._run([], [("M", "anything/at/all.py")])
        self.assertEqual(payload["violations"], [])
        self.assertTrue(any("no Card-Id trailer" in i for i in payload["info"]))

    def test_declared_card_without_file_is_reported(self):
        payload = self._run(["XJ-20991231-999"], [("M", "src/allowed.py")])
        self.assertEqual(payload["unknown_card_ids"], ["XJ-20991231-999"])
        self.assertEqual(payload["authorized_card_ids"], [])

    def test_closed_card_claims_are_ignored(self):
        payload = self._run(["XJ-20260901-001"], [("M", "src/allowed.py")])
        self.assertEqual(payload["inactive_card_ids"], ["XJ-20260901-001"])
        self.assertEqual([v["path"] for v in payload["violations"]], ["src/allowed.py"])

    def test_multiple_declared_cards_union_their_claims(self):
        _write(self.cards / "XJ-20261007-002.md",
               CARD.replace("XJ-20261007-001", "XJ-20261007-002").replace(
                   "- `src/allowed.py`", "- `tools/extra.py`"))
        payload = self._run(["XJ-20261007-001", "XJ-20261007-002"],
                            [("M", "src/allowed.py"), ("M", "tools/extra.py")])
        self.assertEqual(payload["violations"], [])

    def test_trailer_adoption_below_half_is_measured_and_flagged(self):
        """Review point 1a: a coverage gap must be measured, not assumed away."""
        check.trailer_adoption = lambda repo, base, head="HEAD": (3, 1)
        payload = self._run(["XJ-20261007-001"], [("M", "src/allowed.py")])
        self.assertEqual(payload["metrics"]["commits_total"], 3)
        self.assertEqual(payload["metrics"]["commits_with_trailer"], 1)
        self.assertTrue(any("trailer adoption: 1/3" in i for i in payload["info"]))

    def test_full_trailer_adoption_stays_silent(self):
        """No warning line when every commit declares its cards."""
        check.trailer_adoption = lambda repo, base, head="HEAD": (2, 2)
        payload = self._run(["XJ-20261007-001"], [("M", "src/allowed.py")])
        self.assertFalse(any("trailer adoption" in i for i in payload["info"]))


class ExitCodeTests(unittest.TestCase):
    def test_exit_code_is_zero_even_with_violations(self):
        """The load-bearing property of the shadow period."""
        out = io.StringIO()
        with redirect_stdout(out):
            code = check.main(["--repo", str(REPO_ROOT), "--card-dir",
                               str(REPO_ROOT / ".tasks"), "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out.getvalue())
        self.assertIn("metrics", payload)

    def test_warn_output_mentions_never_blocks(self):
        out = io.StringIO()
        with redirect_stdout(out):
            check.main(["--repo", str(REPO_ROOT), "--card-dir",
                        str(REPO_ROOT / ".tasks"), "--warn"])
        self.assertIn("never blocks", out.getvalue())


if __name__ == "__main__":
    unittest.main()