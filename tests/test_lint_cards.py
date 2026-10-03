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
from datetime import datetime, timedelta, timezone
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

    def test_directory_readme_is_exempt(self):
        """README.md documents the card directory; it is not a card (2026-10-02)."""
        self.write("README.md", "# Cards\n\nThis directory holds collaboration cards.\n")
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_OK, code, out)
        self.assertNotIn("NAMESPACE_MISSING", self.codes(out))

    def test_localised_readme_is_exempt(self):
        self.write("README.zh-CN.md", "# 评审卡\n")
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_OK, code, out)
        self.assertNotIn("NAMESPACE_MISSING", self.codes(out))

    def test_readme_exemption_does_not_widen_to_other_bare_names(self):
        """The exemption is narrow on purpose: N1's real targets stay rejected."""
        self.write("NOTES.md", "# notes\n")
        self.write("SUSPENDED-something-2026-10-02.md", "# notes\n")
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertIn("NAMESPACE_MISSING", self.codes(out))

    def test_namespaced_review_request_is_exempt_from_n1(self):
        """`<NS>-REVIEW-REQUEST-...` leads with a namespace, so N1 is satisfied (2026-10-02).

        Regression: the deepseek-brain run named a request
        `DSB-REVIEW-REQUEST-XJ-20261002-003.md` and got NAMESPACE_MISSING, because
        N1's pattern requires the namespace token to lead while classify() required
        the literal `REVIEW-REQUEST-` prefix. No one filename satisfied both.
        """
        self.write("DSB-REVIEW-REQUEST-XJ-20261002-003.md",
                   "# DSB-20261002-004 (REVIEW-REQUEST)\n\nRead the card and report.\n")
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_OK, code, out)
        self.assertNotIn("NAMESPACE_MISSING", self.codes(out))

    def test_namespaced_review_request_is_classified_as_a_request(self):
        """Exempting N1 must not cost the request its type: a request carries no verdict."""
        name = "DSB-REVIEW-REQUEST-XJ-20261002-003.md"
        self.write(name, "# request\n\nNo verdict line here on purpose.\n")
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_OK, code, out)
        # A verdict-carrying card would raise REVIEW_MISSING_VERDICT_LINE; a request
        # must not, so the absence of that code is what proves the type was recognised.
        self.assertNotIn("REVIEW_MISSING_VERDICT_LINE", self.codes(out))

    def test_namespaced_request_exemption_does_not_widen(self):
        """Narrow on purpose: the exemption needs both a leading NS and a date-number id."""
        self.write("DSB-REVIEW-REQUEST-XJ.md", "# not a card id\n")
        self.write("REVIEW-REQUEST-whatever.md", "# no id\n")
        self.write("DSB-NOTES-20261002-001.md", "# not a request type\n")
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertIn("NAMESPACE_MISSING", self.codes(out))


class TestBareTaskReferences(LintTestCase):
    def test_bare_reference_in_handover_section_is_rejected_with_line_number(self):
        self.write("AC-20260929-001.md", TASK_CARD + "\n## Review handoff\nRead TASK-002 please.\n")
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

    def test_quoting_an_incident_in_context_is_not_a_handover(self):
        """Quoting "the TASK-002 collision" in prose is history, not an instruction."""
        body = TASK_CARD.replace("Some context.", "Some context. See postmortems PM-1: the TASK-002 collision.")
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
        code, out, _ = self.run_lint("--verdict-dir", str(self.verdicts), "--no-verdict-schema")
        self.assertEqual(lint.EXIT_OK, code)
        self.assertIn("ORPHAN_VERDICT", self.codes(out))

    def test_card_without_verdict_is_warned(self):
        self.write("AC-20260929-001.md")
        code, out, _ = self.run_lint("--verdict-dir", str(self.verdicts), "--no-verdict-schema")
        self.assertEqual(lint.EXIT_OK, code)
        self.assertIn("VERDICT_WITHOUT_REVIEW", self.codes(out))

    def test_paired_card_and_verdict_is_clean(self):
        self.write("AC-20260929-001.md")
        (self.verdicts / "AC-20260929-001.verdict.json").write_text("{}", encoding="utf-8")
        code, out, _ = self.run_lint("--verdict-dir", str(self.verdicts), "--no-verdict-schema")
        self.assertEqual(lint.EXIT_OK, code, out)
        self.assertEqual(set(), self.codes(out) & {"ORPHAN_VERDICT", "VERDICT_WITHOUT_REVIEW"})


class TestVerdictSchema(LintTestCase):
    """Added with check_verdict_schema (DFB-20261003-007).

    The rule reuses gate.py helpers via importlib so its contract is
    identical to gate's, lint stays in sync with the gate it lints against.
    """

    VALID_VERDICT = {
        "id": "AC-20260929-001",
        "verdict": "PASS",
        "blockers": 0,
        "independent": True,
        "verifier": "Test Reviewer",
        "ts": "2026-10-03T12:00:00+08:00",
        "evidence": ["A1: ran", "A2: clean"],
    }

    def setUp(self):
        super().setUp()
        self.verdicts = self.tmp / "verdicts"
        self.verdicts.mkdir()
        self.write("AC-20260929-001.md")

    def _write_verdict(self, name, body):
        path = self.verdicts / f"{name}.verdict.json"
        if isinstance(body, dict):
            path.write_text(json.dumps(body), encoding="utf-8")
        else:
            path.write_text(body, encoding="utf-8")

    def test_valid_verdict_passes_schema(self):
        self._write_verdict("AC-20260929-001", self.VALID_VERDICT)
        code, out, _ = self.run_lint("--verdict-dir", str(self.verdicts))
        self.assertEqual(lint.EXIT_OK, code, out)
        self.assertNotIn("VERDICT_SCHEMA_NONCOMPLIANT", self.codes(out))

    def test_bad_verdict_value_is_error(self):
        bad = dict(self.VALID_VERDICT); bad["verdict"] = "BAD"
        self._write_verdict("AC-20260929-001", bad)
        code, out, _ = self.run_lint("--verdict-dir", str(self.verdicts))
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertIn("VERDICT_SCHEMA_NONCOMPLIANT", self.codes(out))

    def test_missing_evidence_is_error(self):
        bad = dict(self.VALID_VERDICT); bad.pop("evidence")
        self._write_verdict("AC-20260929-001", bad)
        code, out, _ = self.run_lint("--verdict-dir", str(self.verdicts))
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertIn("VERDICT_SCHEMA_NONCOMPLIANT", self.codes(out))

    def test_blockers_wrong_type_is_error(self):
        bad = dict(self.VALID_VERDICT); bad["blockers"] = []
        self._write_verdict("AC-20260929-001", bad)
        code, out, _ = self.run_lint("--verdict-dir", str(self.verdicts))
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertIn("VERDICT_SCHEMA_NONCOMPLIANT", self.codes(out))

    def test_unparseable_ts_is_error(self):
        bad = dict(self.VALID_VERDICT); bad["ts"] = "yesterday"
        self._write_verdict("AC-20260929-001", bad)
        code, out, _ = self.run_lint("--verdict-dir", str(self.verdicts))
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertIn("VERDICT_SCHEMA_NONCOMPLIANT", self.codes(out))

    def test_not_independent_is_error(self):
        bad = dict(self.VALID_VERDICT); bad["independent"] = False
        self._write_verdict("AC-20260929-001", bad)
        code, out, _ = self.run_lint("--verdict-dir", str(self.verdicts))
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertIn("VERDICT_SCHEMA_NONCOMPLIANT", self.codes(out))

    def test_no_verdict_schema_flag_skips_check(self):
        bad = dict(self.VALID_VERDICT); bad["verdict"] = "BAD"
        self._write_verdict("AC-20260929-001", bad)
        code, out, _ = self.run_lint("--verdict-dir", str(self.verdicts), "--no-verdict-schema")
        self.assertEqual(lint.EXIT_OK, code, out)
        self.assertNotIn("VERDICT_SCHEMA_NONCOMPLIANT", self.codes(out))

    def test_empty_dict_is_error(self):
        self._write_verdict("AC-20260929-001", "{}")
        code, out, _ = self.run_lint("--verdict-dir", str(self.verdicts))
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertIn("VERDICT_SCHEMA_NONCOMPLIANT", self.codes(out))


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


class TestReviewRequestExemption(LintTestCase):
    """A review REQUEST carries no verdict by definition; only a REVIEW must."""

    def test_request_without_verdict_is_clean(self):
        self.write("REVIEW-REQUEST-XJ-20260930-004.md", "# request\n\nread the card and reply\n")
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_OK, code, out)
        self.assertNotIn("REVIEW_MISSING_VERDICT_LINE", self.codes(out))

    def test_plain_review_without_verdict_still_fails(self):
        self.write("REVIEW-001.md", "# REVIEW\n\n## Blockers\n0\n")
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertIn("REVIEW_MISSING_VERDICT_LINE", self.codes(out))

    def test_request_still_obeys_the_namespace_and_path_rules(self):
        body = "# request\n\nsee TASK-007 for context\n"
        self.write("REVIEW-REQUEST-XJ-20260930-004.md", body)
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertIn("BARE_TASK_NAME", self.codes(out))


class TestLegacyPairing(LintTestCase):
    """Cards parked in legacy/ are evidence: not linted, but still paired."""

    def test_verdict_for_archived_card_is_not_orphan(self):
        legacy = self.cards / "legacy"
        legacy.mkdir()
        (legacy / "AC-20260929-001.md").write_text("# archived task\n", encoding="utf-8")
        self.verdicts = self.tmp / "verdicts"
        self.verdicts.mkdir(exist_ok=True)
        (self.verdicts / "AC-20260929-001.verdict.json").write_text("{}", encoding="utf-8")
        code, out, _ = self.run_lint("--verdict-dir", str(self.verdicts), "--no-verdict-schema")
        self.assertNotIn("ORPHAN_VERDICT", self.codes(out))

    def test_archived_cards_are_not_linted(self):
        legacy = self.cards / "legacy"
        legacy.mkdir()
        (legacy / "TASK-001.md").write_text("# bare name evidence\n", encoding="utf-8")
        code, out, _ = self.run_lint()
        self.assertNotIn("NAMESPACE_MISSING", self.codes(out))

    def test_review_card_in_legacy_pairs_with_its_verdict(self):
        """REVIEW-<id>.md in legacy/ is evidence too; its verdict is not orphaned."""
        legacy = self.cards / "legacy"
        legacy.mkdir()
        (legacy / "REVIEW-XJ-20260930-004.md").write_text("# archived review\n", encoding="utf-8")
        self.verdicts = self.tmp / "verdicts"
        self.verdicts.mkdir(exist_ok=True)
        (self.verdicts / "XJ-20260930-004.verdict.json").write_text("{}", encoding="utf-8")
        code, out, _ = self.run_lint("--verdict-dir", str(self.verdicts), "--no-verdict-schema")
        self.assertNotIn("ORPHAN_VERDICT", self.codes(out))

    def test_truly_orphan_verdict_still_warns(self):
        self.verdicts = self.tmp / "verdicts"
        self.verdicts.mkdir(exist_ok=True)
        (self.verdicts / "AC-20260929-999.verdict.json").write_text("{}", encoding="utf-8")
        code, out, _ = self.run_lint("--verdict-dir", str(self.verdicts), "--no-verdict-schema")
        self.assertIn("ORPHAN_VERDICT", self.codes(out))


class TestStaleTestCount(LintTestCase):
    """A test count written in prose must match the suite, or the linter says so.

    The repository shipped claiming 45 tests while holding 69. Nothing read prose,
    so nothing complained. This is the rule that would have caught it.
    """

    def _fake_suite(self, module_name, how_many=2):
        tests = self.tmp / "tests"
        tests.mkdir(exist_ok=True)
        body = "import unittest\n\n\nclass T(unittest.TestCase):\n"
        body += "".join(f"    def test_{i}(self):\n        pass\n\n" for i in range(how_many))
        (tests / f"{module_name}.py").write_text(body, encoding="utf-8")
        return how_many

    def _readme(self, name, declared, prose=""):
        """A README shaped like the real ones: a fenced block carries the claim."""
        text = f"# P\n\n```bash\npython -m unittest discover -s tests  # {declared} tests\n```\n"
        if prose:
            text += f"\n{prose}\n"
        (self.tmp / name).write_text(text, encoding="utf-8")

    def test_wrong_declared_count_is_an_error(self):
        self._fake_suite("test_alpha")
        self._readme("README.md", 45)
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertIn("STALE_TEST_COUNT", self.codes(out))

    def test_correct_declared_count_is_silent(self):
        real = self._fake_suite("test_beta")
        self._readme("README.md", real)
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_OK, code, out)
        self.assertNotIn("STALE_TEST_COUNT", self.codes(out))

    def test_chinese_declaration_is_checked_too(self):
        real = self._fake_suite("test_gamma")
        (self.tmp / "README.zh-CN.md").write_text(
            f"# P\n\n```bash\npython -m unittest discover -s tests  # {real + 7} 个单测\n```\n",
            encoding="utf-8")
        code, out, _ = self.run_lint()
        self.assertIn("STALE_TEST_COUNT", self.codes(out))

    def test_no_test_tree_means_nothing_to_compare(self):
        """A project without tests/ is silent, not broken."""
        self._readme("README.md", 45)
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_OK, code, out)
        self.assertNotIn("STALE_TEST_COUNT", self.codes(out))

    def test_changelog_history_is_not_a_live_claim(self):
        """A changelog entry records what was true then; re-counting it would be wrong."""
        self._fake_suite("test_delta")
        (self.tmp / "CHANGELOG.md").write_text("# C\n\n- 45 tests at v0.1.0\n", encoding="utf-8")
        code, out, _ = self.run_lint()
        self.assertNotIn("STALE_TEST_COUNT", self.codes(out))

    def test_prose_about_a_past_count_is_not_a_finding(self):
        """Regression: the rule fired on the paragraph documenting the very fix.

        A number inside a copy-pasteable command is a claim that must stay true.
        A number in an explanation of what used to be claimed is commentary, and
        flagging it would punish the correction this project wants to make.
        """
        real = self._fake_suite("test_epsilon")
        self._readme("README.md", real, prose=(
            "> Correction: the old README claimed 999 tests while the suite held\n"
            "> fewer. That is why the rule exists."))
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_OK, code, out)
        self.assertNotIn("STALE_TEST_COUNT", self.codes(out))

    def test_wrong_count_outside_any_code_block_is_not_a_finding(self):
        """A bare number in ordinary prose is not a maintenance commitment."""
        real = self._fake_suite("test_zeta")
        (self.tmp / "README.md").write_text(
            f"# P\n\nThe suite grew to {real + 99} tests over four rounds.\n", encoding="utf-8")
        code, out, _ = self.run_lint()
        self.assertNotIn("STALE_TEST_COUNT", self.codes(out))

    def test_failed_discovery_warns_instead_of_going_silent(self):
        """A check that cannot run must say so.

        Regression for the exact defect this rule shipped with: `top_level_dir`
        made discovery refuse to import a non-package tests/, and the rule
        reported success while being dead. Silence is PM-10 inverted.
        """
        broken = self.tmp / "tests"
        broken.mkdir()
        (broken / "test_broken.py").write_text(
            "import a_module_that_does_not_exist\n", encoding="utf-8")
        self._readme("README.md", 45)
        code, out, _ = self.run_lint()
        self.assertIn("TEST_COUNT_UNVERIFIED", self.codes(out))
        self.assertNotIn("STALE_TEST_COUNT", self.codes(out))


class TestUnmappedClaimSurface(LintTestCase):
    """The claim surface needs a current PASS signature, or freshness skips it."""

    def _claim_surface(self):
        (self.tmp / "README.md").write_text("# P\n", encoding="utf-8")
        (self.tmp / "CHANGELOG.md").write_text("# C\n", encoding="utf-8")

    def _map(self, **entries):
        path = self.tmp / "artifacts.json"
        path.write_text(json.dumps(entries), encoding="utf-8")
        return str(path)

    def _verdict(self, vid, verdict="PASS", when=None):
        """Write a verdict signed `when` (default: now, so it is never stale)."""
        vdir = self.tmp / "verdicts"
        vdir.mkdir(exist_ok=True)
        stamp = when or datetime.now(timezone.utc).isoformat()
        (vdir / f"{vid}.verdict.json").write_text(
            json.dumps({"id": vid, "verdict": verdict, "ts": stamp}), encoding="utf-8")
        return str(vdir)

    def _aged(self, seconds=3600):
        """An instant far enough back that it predates any file just written."""
        return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()

    def test_unlisted_file_warns(self):
        self._claim_surface()
        path = self._map(_comment="ignored", **{"AC-20260929-001": ["README.md"]})
        code, out, _ = self.run_lint("--artifact-map", path)
        self.assertIn("UNMAPPED_CLAIM_SURFACE", self.codes(out))

    def test_fully_mapped_claim_surface_is_silent(self):
        self._claim_surface()
        path = self._map(**{"AC-20260929-001": ["README.md", "CHANGELOG.md"]})
        code, out, _ = self.run_lint("--artifact-map", path)
        self.assertNotIn("UNMAPPED_CLAIM_SURFACE", self.codes(out))

    def test_no_artifact_map_means_check_not_enabled(self):
        """No flag and no artifacts.json in the project = the check is out of scope."""
        self._claim_surface()
        code, out, _ = self.run_lint()
        self.assertNotIn("UNMAPPED_CLAIM_SURFACE", self.codes(out))

    def test_default_artifact_map_is_used_when_the_file_exists(self):
        """A check that only runs when a flag is remembered will be forgotten (PM-10).

        The flagless invocation must still catch the unmapped claim surface when
        the project plainly has an artifacts.json sitting next to .tasks/.
        """
        self._claim_surface()
        self._map(**{"AC-20260929-001": ["tools/gate.py"]})
        code, out, _ = self.run_lint()
        self.assertIn("UNMAPPED_CLAIM_SURFACE", self.codes(out))

    def test_unreadable_artifact_map_is_a_usage_error(self):
        path = self.tmp / "artifacts.json"
        path.write_text("{not json", encoding="utf-8")
        code, _, err = self.run_lint("--artifact-map", str(path))
        self.assertEqual(lint.EXIT_USAGE, code)
        self.assertIn("cannot read artifact map", err)

    def test_mapping_from_an_old_round_does_not_count(self):
        """The drift that actually happened: mapped long ago, dropped by the new rounds.

        README.md is still listed in the v0.1.0 maps. A "mapped anywhere" check
        stays green forever, which is precisely why the drift went unnoticed.
        """
        self._claim_surface()
        path = self._map(**{
            "AC-20260929-001": ["README.md", "CHANGELOG.md"],
            "AC-20260930-005": ["tools/gate.py"],
        })
        code, out, _ = self.run_lint("--artifact-map", path)
        codes = self.codes(out)
        self.assertIn("UNMAPPED_CLAIM_SURFACE", codes)
        self.assertIn("README.md", out)   # flagged despite being mapped in 001

    def test_newest_id_covering_the_surface_is_silent(self):
        self._claim_surface()
        path = self._map(**{
            "AC-20260929-001": ["README.md"],
            "AC-20260930-005": ["README.md", "CHANGELOG.md"],
        })
        code, out, _ = self.run_lint("--artifact-map", path)
        self.assertNotIn("UNMAPPED_CLAIM_SURFACE", self.codes(out))

    # --- signature semantics -------------------------------------------------
    # Round identity is not coverage. These cases pin the claim *holder*: the
    # round that actually stands behind the file's current text.

    def test_an_older_rounds_fresh_pass_holds_the_claim(self):
        """The coercion this rule used to impose, removed.

        A ledger-only round that never touched the READMEs must not have to list
        them. Coverage comes from whoever really signed, not from whoever is newest.
        """
        self._claim_surface()
        self._verdict("AC-20260929-001")
        path = self._map(**{
            "AC-20260929-001": ["README.md", "CHANGELOG.md"],
            "AC-20260930-005": [".tasks/XJ-20260930-005.md"],
        })
        code, out, _ = self.run_lint("--artifact-map", path,
                                     "--verdict-dir", str(self.tmp / "verdicts"))
        self.assertNotIn("UNMAPPED_CLAIM_SURFACE", self.codes(out))

    def test_a_fail_verdict_does_not_hold_the_claim(self):
        self._claim_surface()
        self._verdict("AC-20260929-001", verdict="FAIL")
        path = self._map(**{"AC-20260929-001": ["README.md", "CHANGELOG.md"]})
        code, out, _ = self.run_lint("--artifact-map", path,
                                     "--verdict-dir", str(self.tmp / "verdicts"))
        codes = self.codes(out)
        self.assertIn("UNMAPPED_CLAIM_SURFACE", codes)
        self.assertIn("FAIL", out)

    def test_a_pass_predating_the_file_does_not_hold_the_claim(self):
        """A signature older than the text it would vouch for says nothing about it."""
        self._claim_surface()
        self._verdict("AC-20260929-001", when=self._aged())
        path = self._map(**{"AC-20260929-001": ["README.md", "CHANGELOG.md"]})
        code, out, _ = self.run_lint("--artifact-map", path,
                                     "--verdict-dir", str(self.tmp / "verdicts"))
        codes = self.codes(out)
        self.assertIn("UNMAPPED_CLAIM_SURFACE", codes)
        self.assertIn("before this text's mtime", out)

    def test_listing_without_any_verdict_is_not_coverage(self):
        """The finding reports the gap rather than the round that caused it."""
        self._claim_surface()
        path = self._map(**{"AC-20260929-001": ["README.md", "CHANGELOG.md"]})
        vdir = self.tmp / "verdicts"
        vdir.mkdir()
        self._verdict("AC-20260929-002")   # a verdict exists, for a round that maps nothing
        code, out, _ = self.run_lint("--artifact-map", path, "--verdict-dir", str(vdir), "--no-verdict-schema")
        codes = self.codes(out)
        self.assertIn("UNMAPPED_CLAIM_SURFACE", codes)
        self.assertIn("no verdict file", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
