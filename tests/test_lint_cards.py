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

    def test_verdict_heading_mentioning_blockers_is_not_a_section(self):
        """EVO-20261010-004: a heading that NAMES blockers is not one.

        Three review copies shipped with `### **PASS** (blockers=0)` and no
        Blockers section, and passed -- the rule matched the substring. This is
        the guard: the word appearing in a verdict heading must not satisfy it.
        """
        self.write("REVIEW-001.md",
                   "# REVIEW\n\n## Verdict\nPASS\n\n### **PASS** (blockers=0)\n")
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertIn("REVIEW_MISSING_BLOCKERS", self.codes(out))

    def test_finding_heading_mentioning_blocked_is_not_a_section(self):
        """`### P1 - blocked (2x regression)` is a finding, not a section."""
        self.write("REVIEW-001.md",
                   "# REVIEW\n\n## Verdict\nFAIL\n\n### P1 - blocked (2x regression)\n")
        code, out, _ = self.run_lint()
        self.assertIn("REVIEW_MISSING_BLOCKERS", self.codes(out))

    def test_singular_blocker_section_is_accepted(self):
        """The corpus genuinely uses `## Blocker` once; keep it legal."""
        self.write("REVIEW-001.md", "# REVIEW\n\n## Verdict\nPASS\n\n## Blocker\n0\n")
        code, out, _ = self.run_lint()
        self.assertNotIn("REVIEW_MISSING_BLOCKERS", self.codes(out))

    def test_chinese_blockers_section_is_accepted(self):
        self.write("REVIEW-001.md", "# REVIEW\n\n## Verdict\nPASS\n\n## 阻断\n0\n")
        code, out, _ = self.run_lint()
        self.assertNotIn("REVIEW_MISSING_BLOCKERS", self.codes(out))

    def test_second_chinese_spelling_is_accepted(self):
        """`阻塞` was matched by the pre-fix rule; do not narrow the vocabulary.

        Reviewer T-1 (EVO-20261010-004) caught that the fix dropped it: the old
        test read `"阻塞" in name`, the new regex had only `阻断`. No card writes
        either as a heading today, so nothing observable changed -- but quietly
        accepting less than before is a regression waiting to fail the first
        author who uses the word.
        """
        self.write("REVIEW-001.md", "# REVIEW\n\n## Verdict\nPASS\n\n## 阻塞\n0\n")
        code, out, _ = self.run_lint()
        self.assertNotIn("REVIEW_MISSING_BLOCKERS", self.codes(out))

    def test_bold_blockers_section_is_accepted(self):
        self.write("REVIEW-001.md", "# REVIEW\n\n## Verdict\nPASS\n\n## **Blockers**\n0\n")
        code, out, _ = self.run_lint()
        self.assertNotIn("REVIEW_MISSING_BLOCKERS", self.codes(out))

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

    # ---- XJ-20261003-002 review regressions (the three confirmed defects) ----

    def test_future_timestamp_is_rejected_by_lint(self):
        """Defect 3: lint now mirrors gate's future-ts plausibility check.

        Before the fix, `ts` was only checked for parseability, so a future-dated
        verdict passed lint while gate rejected it with FUTURE_VERDICT - the exact
        'lint and gate drift' the docstring claimed never happens. A future ts is
        now an ERROR.
        """
        bad = dict(self.VALID_VERDICT)
        bad["ts"] = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        self._write_verdict("AC-20260929-001", bad)
        code, out, _ = self.run_lint("--verdict-dir", str(self.verdicts))
        self.assertEqual(lint.EXIT_ERROR, code, out)
        self.assertIn("VERDICT_SCHEMA_NONCOMPLIANT", self.codes(out))
        self.assertIn("future", out)

    def test_skipped_run_leaves_a_visible_trace(self):
        """Defect 2: a bypassed check must not be silent.

        With --no-verdict-schema the verdict schema check is skipped, but the run
        must say so. A check that can be turned off and leave no trace is not a
        check - the default (silent-skip) is what this regression guards.
        """
        bad = dict(self.VALID_VERDICT)
        bad["verdict"] = "BOGUS"
        self._write_verdict("AC-20260929-001", bad)
        code, out, _ = self.run_lint("--verdict-dir", str(self.verdicts),
                                     "--no-verdict-schema")
        # The bad verdict is not flagged (the check was skipped)...
        self.assertEqual(lint.EXIT_OK, code, out)
        self.assertNotIn("VERDICT_SCHEMA_NONCOMPLIANT", self.codes(out))
        # ...but the skip is visible in the output.
        self.assertIn("verdict schema check SKIPPED", out)
        self.assertIn("--no-verdict-schema", out)

    def test_conditional_pass_value_is_rejected_via_gate_source(self):
        """Defect 1: verdict values are checked against gate's single source.

        `CONDITIONAL_PASS` was the value the last real verdict in this repo used,
        and gate rejected it with BAD_VERDICT_VALUE. Lint must reject it too, by
        delegating to gate._check_verdict_value (the authoritative vocabulary),
        not to a local shadow copy. If a shadow VALID_VERDICTS ever became the
        source of truth again, this check would silently depend on it.
        """
        bad = dict(self.VALID_VERDICT)
        bad["verdict"] = "CONDITIONAL_PASS"
        self._write_verdict("AC-20260929-001", bad)
        code, out, _ = self.run_lint("--verdict-dir", str(self.verdicts))
        self.assertEqual(lint.EXIT_ERROR, code, out)
        self.assertIn("VERDICT_SCHEMA_NONCOMPLIANT", self.codes(out))

    def test_no_shadow_verdicts_constant_in_lint(self):
        """Defect 1 (structural): lint must not keep its own verdict vocabulary.

        The shadow `VALID_VERDICTS` tuple in check_verdict_schema was dead code -
        a local copy of gate's tuple that editing never affected. The linter now
        owns no such *definition*; the vocabulary lives only in gate.py. This
        guards against the shadow being reintroduced. (The docstring may still name
        the removed constant to document its removal, so the test looks for the
        binding, not the bare word.)
        """
        import inspect
        src = inspect.getsource(lint.check_verdict_schema)
        import re as _re
        self.assertIsNone(_re.search(r"\bVALID_VERDICTS\s*=", src),
                          "a shadow VALID_VERDICTS definition reappeared in "
                          "check_verdict_schema")
        # And the module must not define an authoritative copy at top level either.
        self.assertFalse(hasattr(lint, "VALID_VERDICTS"),
                         "lint_cards.py must not keep its own verdict vocabulary; "
                         "gate.py is the single source of truth")


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


class TestUnblocksLint(LintTestCase):
    """ADR-0002 R1/R3: unblocks shape checks and duplicate-closure warning."""

    def _write_verdict_raw(self, vid, payload):
        vdir = self.tmp / "verdicts"
        vdir.mkdir(exist_ok=True)
        (vdir / f"{vid}.verdict.json").write_text(
            json.dumps(payload), encoding="utf-8")
        return str(vdir)

    def _good(self, vid, **over):
        stamp = datetime.now(timezone.utc).isoformat()
        payload = {"id": vid, "verdict": "PASS", "blockers": 0, "independent": True,
                   "verifier": "reviewer@acme", "ts": stamp,
                   "evidence": ["pytest -q -> 27 passed"]}
        payload.update(over)
        return payload

    def test_malformed_unblocks_is_rejected(self):
        self.write("AC-20260929-001.md")
        vdir = self._write_verdict_raw(
            "AC-20260929-001", self._good("AC-20260929-001", unblocks="not-a-card-id"))
        code, out, _ = self.run_lint("--verdict-dir", vdir)
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertIn("VERDICT_SCHEMA_NONCOMPLIANT", self.codes(out))
        self.assertIn("not of the form", out)

    def test_wellformed_unblocks_is_accepted(self):
        self.write("AC-20260929-001.md")
        vdir = self._write_verdict_raw(
            "AC-20260929-001",
            self._good("AC-20260929-001", unblocks=["AC-20260929-000.C1"]))
        code, out, _ = self.run_lint("--verdict-dir", vdir)
        self.assertNotIn("not of the form", out)
        self.assertEqual(lint.EXIT_OK, code, out)

    def test_self_referencing_unblocks_is_rejected(self):
        """A verdict cannot discharge a condition of the card it judges."""
        self.write("AC-20260929-001.md")
        vdir = self._write_verdict_raw(
            "AC-20260929-001",
            self._good("AC-20260929-001", unblocks=["AC-20260929-001.C1"]))
        code, out, _ = self.run_lint("--verdict-dir", vdir)
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertIn("references its own id", out)

    def test_duplicate_unblocks_warns_and_does_not_block(self):
        """Two claimants is the two-card hazard; ADR-0002 6.3 says warn, not error."""
        self.write("AC-20260929-001.md")
        self.write("AC-20260929-002.md")
        vdir = self._write_verdict_raw(
            "AC-20260929-001", self._good("AC-20260929-001", unblocks=["AC-20260929-000.C1"]))
        (Path(vdir) / "AC-20260929-002.verdict.json").write_text(
            json.dumps(self._good("AC-20260929-002", unblocks=["AC-20260929-000.C1"])),
            encoding="utf-8")
        code, out, _ = self.run_lint("--verdict-dir", vdir)
        self.assertIn("DUPLICATE_UNBLOCKS", self.codes(out))
        # warn, not error: the run must still succeed
        self.assertEqual(lint.EXIT_OK, code, out)

    def test_single_claim_does_not_warn(self):
        self.write("AC-20260929-001.md")
        vdir = self._write_verdict_raw(
            "AC-20260929-001", self._good("AC-20260929-001", unblocks=["AC-20260929-000.C1"]))
        code, out, _ = self.run_lint("--verdict-dir", vdir)
        self.assertNotIn("DUPLICATE_UNBLOCKS", self.codes(out))

    def test_self_signed_is_rejected_by_lint(self):
        """Lint has no --allow-nonindependent, so a self-sign is an error here."""
        self.write("AC-20260929-001.md")
        vdir = self._write_verdict_raw(
            "AC-20260929-001",
            self._good("AC-20260929-001", self_signed=True, independent=False))
        code, out, _ = self.run_lint("--verdict-dir", vdir)
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertIn("self-signed", out)

    def test_self_signed_with_independent_true_is_a_contradiction(self):
        self.write("AC-20260929-001.md")
        vdir = self._write_verdict_raw(
            "AC-20260929-001",
            self._good("AC-20260929-001", self_signed=True, independent=True))
        code, out, _ = self.run_lint("--verdict-dir", vdir)
        self.assertEqual(lint.EXIT_ERROR, code)
        self.assertIn("contradiction", out)


class TestUnblocksDangling(LintTestCase):
    """S1: an unblocks reference to a condition that does not exist, WARNed."""

    def _write_verdict_raw(self, vid, payload):
        vdir = self.tmp / "verdicts"
        vdir.mkdir(exist_ok=True)
        (vdir / f"{vid}.verdict.json").write_text(
            json.dumps(payload), encoding="utf-8")
        return str(vdir)

    def _good(self, vid, **over):
        stamp = datetime.now(timezone.utc).isoformat()
        payload = {"id": vid, "verdict": "PASS", "blockers": 0, "independent": True,
                   "verifier": "reviewer@acme", "ts": stamp,
                   "evidence": ["pytest -q -> 27 passed"]}
        payload.update(over)
        return payload

    def _write_pair(self, claimant_extra, target_conditions):
        """Two verdicts: a claimant with unblocks, a target with conditions."""
        self.write("AC-20260929-001.md")
        self.write("AC-20260929-002.md")
        vdir = self.tmp / "verdicts"
        vdir.mkdir(exist_ok=True)
        self._write_verdict_raw(
            "AC-20260929-001", self._good("AC-20260929-001", **claimant_extra))
        (vdir / "AC-20260929-002.verdict.json").write_text(
            json.dumps(self._good("AC-20260929-002",
                                  conditions=target_conditions)),
            encoding="utf-8")
        return str(vdir)

    def test_reference_to_missing_card_warns(self):
        vdir = self._write_pair(
            {"unblocks": ["XJ-99999999-001.C9"]},
            ["C1: something"],
        )
        code, out, _ = self.run_lint("--verdict-dir", vdir)
        self.assertIn("UNBLOCKS_DANGLING", self.codes(out))
        self.assertIn("cannot be verified", out)
        # WARN only: the run still succeeds.
        self.assertEqual(lint.EXIT_OK, code, out)

    def test_reference_to_missing_condition_warns(self):
        vdir = self._write_pair(
            {"unblocks": ["AC-20260929-002.C9"]},
            ["C1: the real condition"],
        )
        code, out, _ = self.run_lint("--verdict-dir", vdir)
        self.assertIn("UNBLOCKS_DANGLING", self.codes(out))
        self.assertIn("do not open with C9", out)
        self.assertEqual(lint.EXIT_OK, code, out)

    def test_reference_to_real_condition_is_silent(self):
        vdir = self._write_pair(
            {"unblocks": ["AC-20260929-002.C1"]},
            ["C1: the real condition"],
        )
        code, out, _ = self.run_lint("--verdict-dir", vdir)
        self.assertNotIn("UNBLOCKS_DANGLING", self.codes(out))
        self.assertEqual(lint.EXIT_OK, code, out)

    def test_annotated_prefix_matches_base_id(self):
        """"C1 (B1, from Q2): ..." must match a reference to C1."""
        vdir = self._write_pair(
            {"unblocks": ["AC-20260929-002.C1"]},
            ["C1 (B1, from Q2): the annotated form seen on XJ-20261004-004"],
        )
        code, out, _ = self.run_lint("--verdict-dir", vdir)
        self.assertNotIn("UNBLOCKS_DANGLING", self.codes(out))

    def test_prefixless_conditions_report_undecidable_not_missing(self):
        """A target whose conditions carry no id prefix warns as undecidable.

        The empty prefix set must not be read as 'no conditions matched, so
        every reference dangles' -- it is 'cannot verify', the honest
        degradation the rule promises for free-text conditions.
        """
        vdir = self._write_pair(
            {"unblocks": ["AC-20260929-002.C1"]},
            ["fix the thing before the next release"],  # no prefix
        )
        code, out, _ = self.run_lint("--verdict-dir", vdir)
        self.assertIn("UNBLOCKS_DANGLING", self.codes(out))
        self.assertIn("no id prefixes", out)
        self.assertEqual(lint.EXIT_OK, code, out)


class TestOwnedFilesQuality(LintTestCase):
    """A claim surface that cannot constrain anything is not a claim.

    `OWNED_FILES_CONFLICT` only fires on overlap, so a card claiming nothing —
    or claiming `**` — passed every other rule while making the ownership model
    decorative. Both rules are WARN: CI runs this linter with `--strict`, and
    promoting them to ERROR is a gate, which EVO-20261007-001 forbids until the
    current corpus has been measured.
    """

    def test_active_card_without_owned_files_warns(self):
        self.write("AC-20260929-001.md", TASK_CARD)
        code, out, _ = self.run_lint()
        self.assertEqual(lint.EXIT_OK, code)  # WARN does not fail by default
        self.assertIn("OWNED_FILES_EMPTY", self.codes(out))

    def test_closed_card_without_owned_files_is_silent(self):
        """A finished card has nothing left to constrain."""
        self.write("AC-20260929-001.md", TASK_CARD.replace("OPEN", "CLOSED"))
        code, out, _ = self.run_lint()
        self.assertNotIn("OWNED_FILES_EMPTY", self.codes(out))

    def test_review_card_is_not_held_to_task_rules(self):
        """Review cards carry no owned files by design."""
        self.write("REVIEW-AC-20260929-001.md", REVIEW_CARD)
        code, out, _ = self.run_lint()
        self.assertNotIn("OWNED_FILES_EMPTY", self.codes(out))

    def test_double_star_claim_is_too_broad(self):
        self.write("AC-20260929-001.md", TASK_CARD + "\n## Owned files\n- src/**\n")
        code, out, _ = self.run_lint()
        self.assertIn("OWNED_FILES_TOO_BROAD", self.codes(out))

    def test_root_claim_is_too_broad(self):
        self.write("AC-20260929-001.md", TASK_CARD + "\n## Owned files\n- .\n")
        code, out, _ = self.run_lint()
        self.assertIn("OWNED_FILES_TOO_BROAD", self.codes(out))

    def test_directory_claim_stays_legal(self):
        """templates/TASK.md: a directory claim owns everything beneath it.

        The whitelist is where directory claims are refused; a card may still
        take a whole subtree, so this rule must not drift into forbidding it.
        """
        self.write("AC-20260929-001.md", TASK_CARD + "\n## Owned files\n- tools/\n")
        code, out, _ = self.run_lint()
        self.assertNotIn("OWNED_FILES_TOO_BROAD", self.codes(out))

    def test_concrete_claims_are_clean(self):
        self.write("AC-20260929-001.md",
                   TASK_CARD + "\n## Owned files\n- tools/gate.py\n- docs/lint-rules.md\n")
        code, out, _ = self.run_lint()
        self.assertNotIn("OWNED_FILES_EMPTY", self.codes(out))
        self.assertNotIn("OWNED_FILES_TOO_BROAD", self.codes(out))

    def test_empty_section_reports_only_one_finding(self):
        """An empty section is one defect, not one per rule."""
        self.write("AC-20260929-001.md", TASK_CARD + "\n## Owned files\n\n")
        code, out, _ = self.run_lint()
        empty_lines = [line for line in out.splitlines() if "OWNED_FILES_EMPTY" in line]
        self.assertEqual(len(empty_lines), 1, out)
        self.assertNotIn("OWNED_FILES_TOO_BROAD", self.codes(out))


class TestAnchoredTestCount(unittest.TestCase):
    """The `<!-- test-count -->N<!-- /test-count -->` anchor is a writer's
    convenience, not an exemption: a stale anchor must fail like stale prose.

    `tools/sync_test_count.py` owns the number, but the checker still reads it
    back. These test the *parsing* unit -- `_declared_counts` over a fenced
    block -- because that is where an unrecognised anchor would silently stop
    being checked at all. Whether a wrong number then fails is
    `check_stale_test_count`'s job, already covered by the ruleset tests.
    """

    def _declared(self, line):
        text = "# Setup\n\n```\n" + line + "\n```\n"
        return list(lint._declared_counts(text))

    def test_anchored_form_is_read(self):
        found = self._declared("python -m unittest discover -s tests  # "
                               "<!-- test-count -->170<!-- /test-count --> tests")
        self.assertEqual([v for _, v in found], [170])

    def test_anchored_form_survives_spacing_variants(self):
        found = self._declared("x <!--test-count-->42<!--/test-count--> y")
        self.assertEqual([v for _, v in found], [42])

    def test_prose_forms_still_read(self):
        self.assertEqual([v for _, v in self._declared("cmd  # 170 tests")], [170])
        self.assertEqual([v for _, v in self._declared("cmd  # 170 个单测")], [170])

    def test_anchor_is_reported_once_not_twice(self):
        """One line, one claim: the anchor must not double-count with the
        prose regex that also matches the trailing 'tests'."""
        found = self._declared("python -m unittest discover -s tests  # "
                               "<!-- test-count -->170<!-- /test-count --> tests")
        self.assertEqual(len(found), 1)


class TestCardSelfInMap(unittest.TestCase):
    """A round must not list its own card as a judged artifact.

    Listing it makes the round stale by definition: closing the card edits the
    card file, which necessarily happens after the verdict, and no later round
    revisits a closed card to supersede the finding. The result is a permanent
    finding that no one can act on.
    """

    def _codes(self, artifact_map):
        return {f["rule"] for f in lint.check_card_self_in_map(artifact_map)}

    def test_self_listed_card_warns(self):
        found = self._codes({
            "XJ-20261008-001": ["tools/lint_cards.py", ".tasks/XJ-20261008-001.md"],
        })
        self.assertIn("CARD_SELF_IN_MAP", found)

    def test_backslash_and_dot_slash_spellings_are_caught(self):
        """Windows paths and './' prefixes must not smuggle a self-listing past."""
        found = self._codes({
            "XJ-20261008-001": [".\\.tasks\\XJ-20261008-001.md"],
        })
        self.assertIn("CARD_SELF_IN_MAP", found)

    def test_clean_map_is_silent(self):
        found = self._codes({
            "XJ-20261008-001": ["tools/lint_cards.py", "docs/lint-rules.md"],
        })
        self.assertNotIn("CARD_SELF_IN_MAP", found)

    def test_another_rounds_card_is_not_flagged(self):
        """Only a round's OWN card is the defect; citing someone else's is normal."""
        found = self._codes({
            "XJ-20261008-001": [".tasks/XJ-20261008-002.md"],
        })
        self.assertNotIn("CARD_SELF_IN_MAP", found)

    def test_private_keys_are_skipped(self):
        found = self._codes({"_comment": [".tasks/_comment.md"]})
        self.assertNotIn("CARD_SELF_IN_MAP", found)

    def test_shipped_map_reports_only_known_legacy_rounds(self):
        """The repository's own map is not clean, and this rule says so.

        Seven rounds carried the pattern; XJ-20261008-001 was corrected by
        EVO-20261010-001 while the rest were left alone deliberately (their red
        has other causes). If this count changes, someone either fixed more
        rounds or reintroduced the habit -- both worth noticing.
        """
        artifact_map = lint.load_artifact_map(REPO_ROOT / "artifacts.json")
        details = " ".join(f["detail"] for f in lint.check_card_self_in_map(artifact_map))
        self.assertNotIn("XJ-20261008-001", details, "the corrected round must stay corrected")
        self.assertIn("XJ-20260930-015", details)


class TestOwnedFilesNonPath(LintTestCase):
    """Constraint prose in the Owned files section must not become a claim.

    On the real corpus this produced 132 OWNED_FILES_CONFLICT findings where only
    5 were real (EVO-20261010-002) -- about 96% noise, and that rule is the only
    ERROR-level blocker under --strict, so the noise was burying real conflicts.
    The prose is reported rather than dropped: silently skipping it would be the
    same "check quietly stopped looking" defect this repository keeps postmorteming.
    """

    def test_prose_line_is_reported_not_claimed(self):
        card = TASK_CARD + "\n## Owned files\n- 不要** `tools/gate.py`、`PROTOCOL.md`\n"
        self.write("AC-20260929-001.md", card)
        code, out, _ = self.run_lint()
        self.assertIn("OWNED_FILES_NONPATH", self.codes(out))
        self.assertNotIn("OWNED_FILES_CONFLICT", self.codes(out))

    def test_prose_does_not_collide_with_a_real_claim(self):
        """The regression that mattered: noise colliding with a genuine claim."""
        self.write("AC-20260929-001.md",
                   TASK_CARD + "\n## Owned files\n- `tools/gate.py`\n")
        self.write("AC-20260929-002.md",
                   TASK_CARD + "\n## Owned files\n- 不要** `tools/gate.py`、`PROTOCOL.md`\n")
        code, out, _ = self.run_lint()
        self.assertNotIn("OWNED_FILES_CONFLICT", self.codes(out))
        self.assertIn("OWNED_FILES_NONPATH", self.codes(out))

    def test_prose_alongside_valid_paths_is_still_reported(self):
        """A well-formed line must not shelter the prose next to it."""
        card = (TASK_CARD
                + "\n## Owned files\n- `tools/gate.py`\n- 本卡与评审产物（只读）\n")
        self.write("AC-20260929-001.md", card)
        code, out, _ = self.run_lint()
        self.assertIn("OWNED_FILES_NONPATH", self.codes(out))

    def test_directory_claim_is_still_a_path(self):
        """templates/TASK.md: a directory claim owns everything beneath it."""
        self.write("AC-20260929-001.md", TASK_CARD + "\n## Owned files\n- tools/\n")
        code, out, _ = self.run_lint()
        self.assertNotIn("OWNED_FILES_NONPATH", self.codes(out))

    def test_bare_filename_with_extension_is_a_path(self):
        self.write("AC-20260929-001.md", TASK_CARD + "\n## Owned files\n- CHANGELOG.md\n")
        code, out, _ = self.run_lint()
        self.assertNotIn("OWNED_FILES_NONPATH", self.codes(out))

    def test_windows_path_is_a_path(self):
        self.write("AC-20260929-001.md",
                   TASK_CARD + "\n## Owned files\n- `docs\\lint-rules.md`\n")
        code, out, _ = self.run_lint()
        self.assertNotIn("OWNED_FILES_NONPATH", self.codes(out))

    def test_shipped_conflict_count_is_the_known_real_set(self):
        """Pins the measurement so a regression back to ~132 is visible.

        Five real conflicts is what path-shaped recomputation finds; the count
        changing is fine, but it should change because the cards did, not because
        the filter stopped filtering.
        """
        findings, _ = lint.lint_card_dir(REPO_ROOT / ".tasks")
        conflicts = [f for f in findings if f["rule"] == "OWNED_FILES_CONFLICT"]
        self.assertLessEqual(
            len(conflicts), 20,
            "OWNED_FILES_CONFLICT ballooned -- prose is being claimed again")


class TestEvoProtectedAssets(unittest.TestCase):
    """A rule-evolution card may not rewrite the system that judges it.

    EVO-20261010-003, from two independent sources: AgentDescent's "a
    self-modifying system must not be able to replace its own evaluator", and
    DarwinAgent's asset boundary. Detection is by DECLARATION
    (`protected_assets_targeted`), not by scraping prose -- the first draft
    keyword-matched and produced three false positives on cards that were
    *protecting* gate.py ("不改 gate.py（评审明确禁区）"). A scan that fires
    harder the more a card defends an asset is disqualifying.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.evo = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _card(self, name, **fields):
        payload = {"id": name, "proposed_change": "x"}
        payload.update(fields)
        (self.evo / f"{name}.json").write_text(json.dumps(payload), encoding="utf-8")
        return name

    def _codes(self):
        return {f["rule"] for f in lint.check_evo_protected_assets(self.evo)}

    def test_targeting_without_declaration_is_an_error(self):
        self._card("EVO-20990101-001", protected_assets_targeted=["gate.py 判定逻辑"])
        self.assertIn("EVO_PROTECTED_ASSET_TOUCHED", self._codes())

    def test_targeting_with_changes_and_approval_downgrades_to_warn(self):
        self._card("EVO-20990101-002",
                   protected_assets_targeted=["sir 终裁权"],
                   protected_assets_changes=["why"],
                   sir_approval="sir 2026-10-11")
        findings = lint.check_evo_protected_assets(self.evo)
        levels = {f["rule"]: f["level"] for f in findings}
        self.assertEqual(levels.get("EVO_PROTECTED_ASSET_TOUCHED"), "WARN")

    def test_prose_that_merely_mentions_gate_py_is_silent(self):
        """The regression that mattered: protecting an asset is not touching it."""
        self._card("EVO-20990101-003",
                   proposed_change="不改 gate.py（评审明确禁区）；gate.yml、lint_cards.py 均不进白名单")
        self.assertNotIn("EVO_PROTECTED_ASSET_TOUCHED", self._codes())

    def test_card_without_targeting_is_silent(self):
        self._card("EVO-20990101-004", proposed_change="加一条 lint 规则")
        self.assertEqual(self._codes(), set())

    def test_unknown_asset_name_warns_as_a_typo(self):
        self._card("EVO-20990101-005", protected_assets_targeted=["gate.py 判定邏輯"])
        self.assertIn("EVO_PROTECTED_ASSET_UNKNOWN", self._codes())

    def test_unreadable_card_is_an_error_not_silence(self):
        (self.evo / "EVO-20990101-006.json").write_text("{not json", encoding="utf-8")
        self.assertIn("EVO_UNREADABLE", self._codes())

    def test_shipped_evo_cards_are_clean(self):
        """The seven real cards must not trip this rule."""
        evo_dir = Path("D:/15812/projects/_handoffs/evo")
        if not evo_dir.is_dir():
            self.skipTest("EVO handoff directory not present")
        findings = lint.check_evo_protected_assets(evo_dir)
        errors = [f for f in findings if f["level"] == "ERROR"]
        self.assertEqual(errors, [], f"protected-asset boundary tripped on real cards: {errors}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
