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
import subprocess
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
        check.trailer_adoption = lambda repo, base, head="HEAD": (3, 3, True)

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
        check.trailer_adoption = lambda repo, base, head="HEAD": (3, 1, True)
        payload = self._run(["XJ-20261007-001"], [("M", "src/allowed.py")])
        self.assertEqual(payload["metrics"]["commits_total"], 3)
        self.assertEqual(payload["metrics"]["commits_with_trailer"], 1)
        self.assertTrue(any("trailer adoption: 1/3" in i for i in payload["info"]))

    def test_full_trailer_adoption_stays_silent(self):
        """No warning line when every commit declares its cards."""
        check.trailer_adoption = lambda repo, base, head="HEAD": (2, 2, True)
        payload = self._run(["XJ-20261007-001"], [("M", "src/allowed.py")])
        self.assertFalse(any("trailer adoption" in i for i in payload["info"]))

    def test_failed_measurement_is_labelled_not_shown_as_zero(self):
        """Round 002 review point 3: a failed measurement must not look clean.

        Before this, a git failure returned (0, 0), which reads exactly like
        'measured, and no commit declared a trailer'. The two are worlds apart:
        one means the report proves nothing about drift, the other means the
        convention is unused. Only an explicit flag keeps them distinguishable.
        """
        check.trailer_adoption = lambda repo, base, head="HEAD": (0, 0, False)
        payload = self._run(["XJ-20261007-001"], [("M", "src/allowed.py")])
        self.assertFalse(payload["metrics"]["trailer_measured"])
        self.assertTrue(any("NOT MEASURED" in i for i in payload["info"]))

    def test_measured_zero_is_not_labelled_as_unmeasured(self):
        """The mirror case: a real, empty measurement says so honestly."""
        check.trailer_adoption = lambda repo, base, head="HEAD": (2, 0, True)
        payload = self._run(["XJ-20261007-001"], [("M", "src/allowed.py")])
        self.assertTrue(payload["metrics"]["trailer_measured"])
        self.assertFalse(any("NOT MEASURED" in i for i in payload["info"]))
        self.assertTrue(any("trailer adoption: 0/2" in i for i in payload["info"]))


class RealGitParsingTests(unittest.TestCase):
    """Exercise the real `git log --format` split, with no mock in the path.

    This class exists because of a defect that shipped past 185 green tests
    (round 003, found by an independent reviewer calling the function directly):
    the record format put the same `\\x1e` on both sides of the body, so the
    split cut every commit into two non-empty chunks and `total` was exactly 2x
    the truth. Every other test in this file replaces `trailer_adoption` with a
    lambda, so nothing ever parsed a real `git log` stream -- the one code path
    that was broken had zero coverage while the suite reported success.

    The guard is therefore not "test the parser with a fixture" but "compare the
    parser against git's own count in a real repository". A fixture would have
    been written by the same person who wrote the bug.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self._seq = 0
        self._git("init", "-q")
        self._git("config", "user.email", "test@example.com")
        self._git("config", "user.name", "test")

    def _git(self, *args):
        result = subprocess.run(["git", *args], cwd=str(self.root),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"git {' '.join(args)}: {result.stderr}")
        return result.stdout

    def _commit(self, message):
        # Content must differ every time or git refuses the commit ("nothing to
        # commit") and the fixture silently stops creating history.
        self._seq += 1
        (self.root / "f.txt").write_text(f"version {self._seq}\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", message)

    def _baseline(self):
        """Return a revision that predates every commit the test cares about.

        `rev-list --max-parents=0` gives the root commit, and `root..HEAD`
        excludes that commit itself -- so using it as the base silently drops one
        from both sides of the comparison and the test would agree with any
        off-by-one in the parser. An empty initial commit gives a base that is
        genuinely outside the range.
        """
        self._git("commit", "-q", "--allow-empty", "-m", "baseline")
        return self._git("rev-parse", "HEAD").strip()

    def _truth(self, base):
        return len([line for line in
                    self._git("log", "--oneline", f"{base}..HEAD").splitlines() if line.strip()])

    def test_count_matches_git_for_plain_messages(self):
        base = self._baseline()
        for i in range(3):
            self._commit(f"chore: commit {i}")
        total, with_trailer, measured = check.trailer_adoption(self.root, base)
        self.assertTrue(measured)
        self.assertEqual(total, self._truth(base))
        self.assertEqual(total, 3)
        self.assertEqual(with_trailer, 0)

    def test_count_matches_git_when_trailers_present(self):
        """The regression that mattered: trailers must not change the count."""
        base = self._baseline()
        self._commit("feat: one\n\nCard-Id: XJ-20261007-001")
        self._commit("chore: two")
        self._commit("fix: three\n\nCard-Id: XJ-20261007-002")
        total, with_trailer, measured = check.trailer_adoption(self.root, base)
        self.assertEqual(total, self._truth(base))
        self.assertEqual(total, 3, "a 2x inflation here is the exact bug this guards")
        self.assertEqual(with_trailer, 2)

    def test_multiline_body_without_trailer_is_still_one_commit(self):
        """A body containing text that looks like structure must not split it."""
        base = self._baseline()
        self._commit("feat: subject\n\nbody line one\nbody line two\n\nnot a trailer")
        total, _, _ = check.trailer_adoption(self.root, base)
        self.assertEqual(total, self._truth(base))
        self.assertEqual(total, 1)

    def test_card_ids_and_adoption_agree_on_the_same_range(self):
        """The two parsers must not judge one commit body two different ways."""
        base = self._baseline()
        self._commit("feat: a\n\nCard-Id: XJ-20261007-001")
        self._commit("chore: b")
        ids = check.collect_trailer_card_ids(self.root, base)
        _, with_trailer, _ = check.trailer_adoption(self.root, base)
        self.assertEqual(ids, ["XJ-20261007-001"])
        self.assertEqual(with_trailer, 1, "same body, same verdict from both parsers")


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