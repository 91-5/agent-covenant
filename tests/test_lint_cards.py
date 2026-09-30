#!/usr/bin/env python3
"""Tests for tools/lint_cards.py — stdlib unittest only, no third-party deps.

Run from the repository root:
    python -m unittest discover -s tests -v
"""
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_linter():
    spec = importlib.util.spec_from_file_location("lint_cards", REPO_ROOT / "tools" / "lint_cards.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lint = _load_linter()

TASK_CARD = """# TASK AC-20260929-001: build the thing

## Context
Some context.

## Deliverables
- src/thing.py

## Constraints
- do not touch other dirs

## Acceptance
- pytest exits 0

## Review questions
1. Is the boundary right?

## Review handoff
Write to REVIEW-AC-20260929-001.md

## Status
OPEN
"""

REVIEW_CARD = """# REVIEW AC-20260929-001

## Verdict
PASS

## Blockers
0

## Conditions
none

## Evidence
- pytest -> 27 passed

## Independence
true
"""


class LintTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.cards = self.tmp / ".tasks"
        self.cards.mkdir()
        self.addCleanup(self._tmp.cleanup)

    def write(self, name, text=TASK_CARD):
        (self.cards / name).write_text(text, encoding="utf-8")

    def run_lint(self, *extra):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = lint.main(["--dir", str(self.cards), *extra])
        return code, out.getvalue(), err.getvalue()

    def codes(self, out):
        return {line.split()[1] for line in out.splitlines() if line.startswith("[")}


class TestNamespaceRule(LintTestCase):
    def test_bare_task_filename_is_rejected(self):
        self.write("TASK-001.md")
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertIn("NAMESPACE_MISSING", self.codes(out))

    def test_namespaced_filename_passes(self):
        self.write("AC-20260929-001.md")
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_OK, code, out)
        self.assertNotIn("NAMESPACE_MISSING", self.codes(out))

    def test_review_and_handoff_names_are_exempt(self):
        self.write("REVIEW-001.md", REVIEW_CARD)
        self.write("HANDOFF-001.md", "# handoff\n")
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_OK, code, out)
        self.assertNotIn("NAMESPACE_MISSING", self.codes(out))


class TestBareTaskReferences(LintTestCase):
    def test_bare_reference_in_body_is_rejected_with_line_number(self):
        self.write("AC-20260929-001.md", TASK_CARD + "\nSee TASK-002 for context.\n")
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertIn("BARE_TASK_NAME", self.codes(out))
        self.assertIn("AC-20260929-001.md:", out)

    def test_reference_with_absolute_path_is_allowed(self):
        body = TASK_CARD + "\nRead `D:\\work\\.tasks\\TASK-002.md` first.\n"
        self.write("AC-20260929-001.md", body)
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_OK, code, out)
        self.assertNotIn("BARE_TASK_NAME", self.codes(out))

    def test_posix_path_reference_is_allowed(self):
        body = TASK_CARD + "\nRead /srv/team/.tasks/TASK-002.md first.\n"
        self.write("AC-20260929-001.md", body)
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_OK, code, out)
        self.assertNotIn("BARE_TASK_NAME", self.codes(out))


class TestReviewCardRules(LintTestCase):
    def test_review_without_verdict_section_is_rejected(self):
        self.write("AC-20260929-001.md")
        self.write("REVIEW-001.md", "# REVIEW\n\n## Blockers\n0\n")
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertIn("REVIEW_MISSING_VERDICT_LINE", self.codes(out))

    def test_review_with_verdict_but_no_token_is_rejected(self):
        self.write("REVIEW-001.md", "# REVIEW\n\n## Verdict\nlooks fine to me\n\n## Blockers\n0\n")
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertIn("REVIEW_MISSING_VERDICT_LINE", self.codes(out))

    def test_review_without_blockers_section_is_rejected(self):
        self.write("REVIEW-001.md", "# REVIEW\n\n## Verdict\nPASS\n")
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertIn("REVIEW_MISSING_BLOCKERS", self.codes(out))

    def test_conformant_review_passes(self):
        self.write("REVIEW-001.md", REVIEW_CARD)
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_OK, code, out)


class TestTaskCardWarnings(LintTestCase):
    def test_missing_sections_are_warnings_only(self):
        self.write("AC-20260929-001.md", "# TASK\n\n## Context\nonly context\n")
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_OK, code)
        self.assertIn("TASK_MISSING_SECTION", self.codes(out))

    def test_strict_promotes_warnings_to_failure(self):
        self.write("AC-20260929-001.md", "# TASK\n\n## Context\nonly context\n")
        code, out, _ = self.run_lint("--strict")
        self.assertEqual(lint.EXIT_ERROR, code, out)
        self.assertIn("LINT: FAIL", out)

    def test_chinese_section_aliases_are_accepted(self):
        body = ("# TASK\n\n## 上下文\nc\n\n## 产出\nd\n\n## 约束\nx\n\n"
                "## 验收\ny\n\n## 审查问题\nq\n\n## 状态\nOPEN\n")
        self.write("AC-20260929-001.md", body)
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_OK, code, out)
        self.assertNotIn("TASK_MISSING_SECTION", self.codes(out))

    def test_closed_card_triggers_archive_warning(self):
        self.write("AC-20260929-001.md", TASK_CARD.replace("OPEN", "GATED"))
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_OK, code)
        self.assertIn("CLOSED_NOT_ARCHIVED", self.codes(out))


class TestVerdictPairing(LintTestCase):
    def setUp(self):
        super().setUp()
        self.verdicts = self.tmp / "verdicts"
        self.verdicts.mkdir()

    def test_orphan_verdict_is_warned(self):
        self.write("AC-20260929-001.md")
        (self.verdicts / "AC-20260929-777.verdict.json").write_text("{}", encoding="utf-8")
        code, out, _ = self.run_lint("--verdict-dir", str(self.verdicts))
        self.assertEqual(lint.EXIT_OK, code)
        self.assertIn("ORPHAN_VERDICT", self.codes(out))

    def test_card_without_verdict_is_warned(self):
        self.write("AC-20260929-001.md")
        code, out, _ = self.run_lint("--verdict-dir", str(self.verdicts))
        self.assertEqual(lint.EXIT_OK, code)
        self.assertIn("VERDICT_WITHOUT_REVIEW", self.codes(out))

    def test_paired_card_and_verdict_is_clean(self):
        self.write("AC-20260929-001.md")
        (self.verdicts / "AC-20260929-001.verdict.json").write_text("{}", encoding="utf-8")
        code, out, _ = self.run_lint("--verdict-dir", str(self.verdicts))
        self.assertEqual(lint.EXIT_OK, code, out)
        self.assertEqual(set(), self.codes(out) & {"ORPHAN_VERDICT", "VERDICT_WITHOUT_REVIEW"})


class TestCliBehaviour(LintTestCase):
    def test_json_output_shape(self):
        self.write("TASK-001.md")
        code, out, _ = self.run_lint("--json")
        payload = json.loads(out)
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertFalse(payload["ok"])
        self.assertGreaterEqual(payload["errors"], 1)
        self.assertIn("findings", payload)

    def test_missing_dir_is_usage_error(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = lint.main(["--dir", str(self.tmp / "nope")])
        self.assertEqual(lint.EXIT_USAGE, code)
        self.assertIn("card directory not found", err.getvalue())

    def test_quiet_suppresses_output(self):
        self.write("TASK-001.md")
        code, out, _ = self.run_lint("--quiet")
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertEqual("", out)


class TestOwnedFilesConflicts(LintTestCase):
    """Two active cards must not claim the same file (PROTOCOL.md R2 / PM-5)."""

    CARD_WITH_OWNED = TASK_CARD + "\n## Owned files\n- tools/gate.py\n"

    def test_two_active_cards_claiming_one_file_warns(self):
        self.write("AC-20260929-001.md", self.CARD_WITH_OWNED)
        self.write("AC-20260929-002.md", TASK_CARD + "\n## Owned files\n- tools/gate.py\n")
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_OK, code)  # WARN does not fail by default
        self.assertIn("OWNED_FILES_CONFLICT", self.codes(out))

    def test_disjoint_ownership_is_clean(self):
        self.write("AC-20260929-001.md", self.CARD_WITH_OWNED)
        self.write("AC-20260929-002.md", TASK_CARD + "\n## Owned files\n- tools/lint_cards.py\n")
        code, out, _ = self.run_lint()
        self.assertNotIn("OWNED_FILES_CONFLICT", self.codes(out))

    def test_closed_card_releases_its_claim(self):
        self.write("AC-20260929-001.md", TASK_CARD.replace("OPEN", "CLOSED")
                   + "\n## Owned files\n- tools/gate.py\n")
        self.write("AC-20260929-002.md", self.CARD_WITH_OWNED)
        code, out, _ = self.run_lint()
        self.assertNotIn("OWNED_FILES_CONFLICT", self.codes(out))

    def test_directory_and_file_inside_it_overlap(self):
        self.write("AC-20260929-001.md", TASK_CARD + "\n## Owned files\n- tools/\n")
        self.write("AC-20260929-002.md", self.CARD_WITH_OWNED)
        code, out, _ = self.run_lint()
        self.assertIn("OWNED_FILES_CONFLICT", self.codes(out))

    def test_glob_claims_overlap(self):
        self.write("AC-20260929-001.md", TASK_CARD + "\n## Owned files\n- tests/*.py\n")
        self.write("AC-20260929-002.md", TASK_CARD + "\n## Owned files\n- tests/test_gate.py\n")
        code, out, _ = self.run_lint()
        self.assertIn("OWNED_FILES_CONFLICT", self.codes(out))

    def test_template_placeholder_is_not_a_claim(self):
        self.write("AC-20260929-001.md", TASK_CARD + "\n## Owned files\n- <path/to/file>\n")
        self.write("AC-20260929-002.md", self.CARD_WITH_OWNED)
        code, out, _ = self.run_lint()
        self.assertNotIn("OWNED_FILES_CONFLICT", self.codes(out))


if __name__ == "__main__":
    unittest.main(verbosity=2)
