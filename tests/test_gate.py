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


class TestTimestampPlausibility(GateTestCase):
    """A verdict dated in the future can never be reported stale (postmortems PM-9)."""

    def test_future_verdict_blocks(self):
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        self.write_verdict("AC-20260929-001", _verdict(ts=tomorrow.isoformat().replace("+00:00", "Z")))
        code, out, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001"))
        self.assertEqual(gate.EXIT_VIOLATION, code, out)
        self.assertIn("FUTURE_VERDICT", out)

    def test_small_clock_skew_is_tolerated(self):
        slightly_ahead = datetime.now(timezone.utc) + timedelta(seconds=30)
        self.write_verdict("AC-20260929-001", _verdict(ts=slightly_ahead.isoformat().replace("+00:00", "Z")))
        code, out, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001"))
        self.assertEqual(gate.EXIT_OK, code, out)

    def test_wide_skew_tolerates_a_larger_jump(self):
        ahead = datetime.now(timezone.utc) + timedelta(hours=2)
        self.write_verdict("AC-20260929-001", _verdict(ts=ahead.isoformat().replace("+00:00", "Z")))
        code, _, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001",
                                                    "--max-clock-skew", "7200"))
        self.assertEqual(gate.EXIT_OK, code)


class TestEvidenceQuality(GateTestCase):
    """Opt-in floor: evidence must carry something a pattern can recognise."""

    def test_single_character_evidence_passes_without_the_flag(self):
        self.write_verdict("AC-20260929-001", _verdict(evidence=["x"]))
        code, out, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001"))
        self.assertEqual(gate.EXIT_OK, code, out)

    def test_single_character_evidence_blocks_with_the_flag(self):
        self.write_verdict("AC-20260929-001", _verdict(evidence=["x"]))
        code, out, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001",
                                                      "--evidence-must-match", r"exit [0-9]|passed|failed"))
        self.assertEqual(gate.EXIT_VIOLATION, code, out)
        self.assertIn("WEAK_EVIDENCE", out)

    def test_real_evidence_satisfies_the_pattern(self):
        self.write_verdict("AC-20260929-001", _verdict(evidence=["python -m unittest -> 45 passed, exit 0"]))
        code, out, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001",
                                                      "--evidence-must-match", r"exit [0-9]|passed|failed"))
        self.assertEqual(gate.EXIT_OK, code, out)

    def test_invalid_regex_is_a_usage_error(self):
        self.write_verdict("AC-20260929-001", _verdict())
        code, _, err = self.run_gate(*self.base_args("--require", "AC-20260929-001",
                                                     "--evidence-must-match", "([unclosed"))
        self.assertEqual(gate.EXIT_USAGE, code)
        self.assertIn("not a valid regex", err)


class TestSilentDegradationGuard(GateTestCase):
    """A forgotten --artifact-map must announce itself, not quietly weaken the gate."""

    def test_notice_printed_when_no_artifact_map(self):
        self.write_verdict("AC-20260929-001", _verdict())
        code, out, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001"))
        self.assertEqual(gate.EXIT_OK, code)
        self.assertIn("freshness NOT checked", out)

    def test_no_notice_when_artifact_is_mapped(self):
        artifact = self.tmp / "src" / "pipeline.py"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("print('hi')", encoding="utf-8")
        self.write_verdict("AC-20260929-001", _verdict())
        map_path = self.tmp / "artifacts.json"
        map_path.write_text(json.dumps({"AC-20260929-001": [str(artifact)]}), encoding="utf-8")
        code, out, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001",
                                                      "--artifact-map", str(map_path)))
        self.assertEqual(gate.EXIT_OK, code, out)
        self.assertNotIn("freshness NOT checked", out)

    def test_notice_silent_under_quiet_and_json(self):
        self.write_verdict("AC-20260929-001", _verdict())
        _, quiet_out, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001", "--quiet"))
        self.assertNotIn("freshness NOT checked", quiet_out)
        _, json_out, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001", "--json"))
        self.assertNotIn("freshness NOT checked", json_out)


class TestSupersededFreshness(GateTestCase):
    """A later round that re-judged the same file retires the earlier staleness.

    Without this, a full-chain run can never return to green: any fix to a README
    outlives the verdict that read it, so the chain accumulates STALE forever.

    Artifact paths go into the map as the tmpdir path, not a bare relative name:
    gate.py resolves a relative artifact against the process CWD, which under
    `unittest discover` is the repository root - so a relative name would silently
    test this repository's real README instead of the fixture.
    """

    def _aged_artifact(self, name="artifact-under-test.md"):
        p = self.tmp / name
        p.write_text("x", encoding="utf-8")
        return p

    def _map(self, payload):
        mpath = self.tmp / "artifacts.json"
        mpath.write_text(json.dumps(payload), encoding="utf-8")
        return str(mpath)

    def test_later_verdict_supersedes_earlier_staleness(self):
        art = self._aged_artifact()
        old = datetime.now(timezone.utc) - timedelta(days=2)
        self.write_verdict("AC-001", _verdict(id="AC-001", ts=old.isoformat().replace("+00:00", "Z")))
        self.write_verdict("AC-002", _verdict(id="AC-002"))
        code, out, _ = self.run_gate(*self.base_args(
            "--artifact-map", self._map({"AC-001": [str(art)], "AC-002": [str(art)]})))
        self.assertEqual(gate.EXIT_OK, code, out)
        self.assertIn("SUPERSEDED", out)
        self.assertNotIn("STALE_VERDICT", out)

    def test_supersession_is_reported_not_silently_dropped(self):
        art = self._aged_artifact()
        old = datetime.now(timezone.utc) - timedelta(days=2)
        self.write_verdict("AC-001", _verdict(id="AC-001", ts=old.isoformat().replace("+00:00", "Z")))
        self.write_verdict("AC-002", _verdict(id="AC-002"))
        _, out, _ = self.run_gate(*self.base_args(
            "--artifact-map", self._map({"AC-001": [str(art)], "AC-002": [str(art)]})))
        self.assertIn("re-judged it later", out)
        self.assertIn("do not block", out)

    def test_unreviewed_successor_cannot_retire_staleness(self):
        """The gate that stops a pending round from laundering an earlier one."""
        art = self._aged_artifact()
        old = datetime.now(timezone.utc) - timedelta(days=2)
        self.write_verdict("AC-001", _verdict(id="AC-001", ts=old.isoformat().replace("+00:00", "Z")))
        # AC-002 is in the map but has NO verdict file on disk.
        code, out, _ = self.run_gate(*self.base_args(
            "--require", "AC-001",
            "--artifact-map", self._map({"AC-001": [str(art)], "AC-002": [str(art)]})))
        self.assertEqual(gate.EXIT_VIOLATION, code)
        self.assertIn("STALE_VERDICT", out)
        self.assertNotIn("SUPERSEDED", out)

    def test_earlier_verdict_does_not_supersede_a_later_one(self):
        art = self._aged_artifact()
        # Two verdicts stamped the same second: neither is later, so neither can
        # retire the other's staleness. Force the artifact past both timestamps.
        now = datetime.now(timezone.utc).replace(microsecond=0)
        stamp = now.isoformat().replace("+00:00", "Z")
        self.write_verdict("AC-001", _verdict(id="AC-001", ts=stamp))
        self.write_verdict("AC-002", _verdict(id="AC-002", ts=stamp))
        future = (now + timedelta(hours=1)).timestamp()
        os.utime(art, (future, future))
        code, out, _ = self.run_gate(*self.base_args(
            "--require", "AC-002",
            "--artifact-map", self._map({"AC-001": [str(art)], "AC-002": [str(art)]})))
        self.assertEqual(gate.EXIT_VIOLATION, code)
        self.assertIn("STALE_VERDICT", out)

    def test_successor_that_omits_the_file_does_not_supersede(self):
        art = self._aged_artifact()
        other = self.tmp / "other.md"
        other.write_text("y", encoding="utf-8")
        old = datetime.now(timezone.utc) - timedelta(days=2)
        self.write_verdict("AC-001", _verdict(id="AC-001", ts=old.isoformat().replace("+00:00", "Z")))
        self.write_verdict("AC-002", _verdict(id="AC-002"))
        code, out, _ = self.run_gate(*self.base_args(
            "--require", "AC-001",
            "--artifact-map", self._map({"AC-001": [str(art)], "AC-002": [str(other)]})))
        self.assertEqual(gate.EXIT_VIOLATION, code)
        self.assertIn("STALE_VERDICT", out)

    def test_json_mode_separates_advisories_from_violations(self):
        art = self._aged_artifact()
        old = datetime.now(timezone.utc) - timedelta(days=2)
        self.write_verdict("AC-001", _verdict(id="AC-001", ts=old.isoformat().replace("+00:00", "Z")))
        self.write_verdict("AC-002", _verdict(id="AC-002"))
        code, out, _ = self.run_gate(*self.base_args(
            "--json",
            "--artifact-map", self._map({"AC-001": [str(art)], "AC-002": [str(art)]})))
        self.assertEqual(gate.EXIT_OK, code)
        payload = json.loads(out)
        self.assertTrue(payload["ok"])
        self.assertEqual([], payload["violations"])
        self.assertTrue(any(a["code"] == "SUPERSEDED" for a in payload["advisories"]))


class TestSuccessorMustEarnAuthority(GateTestCase):
    """A successor that cannot pass its own check cannot retire an earlier one.

    Found by independent review of round 011, after the first version of this rule
    shipped green with six tests. Every case below returned exit 0 before the fix.
    The rule relaxes a blocker, so the precondition has to be as strong as the check
    it relaxes -- otherwise the relaxation becomes the hole.
    """

    def _pair(self, art_offset, v1_offset, v2_offset, **v2_overrides):
        art = self.tmp / "a.md"
        art.write_text("x", encoding="utf-8")
        now = datetime.now(timezone.utc).replace(microsecond=0)
        t = (now + art_offset).timestamp()
        os.utime(art, (t, t))

        def stamp(off):
            return (now + off).isoformat().replace("+00:00", "Z")

        self.write_verdict("AC-001", _verdict(id="AC-001", ts=stamp(v1_offset)))
        self.write_verdict("AC-002", _verdict(id="AC-002", ts=stamp(v2_offset), **v2_overrides))
        mpath = self.tmp / "artifacts.json"
        mpath.write_text(json.dumps({"AC-001": [str(art)], "AC-002": [str(art)]}),
                         encoding="utf-8")
        return str(mpath)

    def _expect_stale(self, mpath):
        code, out, _ = self.run_gate(*self.base_args("--require", "AC-001",
                                                     "--artifact-map", mpath))
        self.assertEqual(gate.EXIT_VIOLATION, code, out)
        self.assertIn("STALE_VERDICT", out)
        self.assertNotIn("SUPERSEDED", out)

    def test_stale_successor_cannot_retire_an_earlier_verdict(self):
        """The successor judged an older copy of the file, so nobody judged this one."""
        self._expect_stale(self._pair(timedelta(hours=1), timedelta(days=-2), timedelta(days=-1)))

    def test_future_dated_successor_cannot_retire(self):
        """PM-9 through a second door: a far-future ts must not count as 'later'."""
        self._expect_stale(self._pair(timedelta(0), timedelta(days=-2), timedelta(days=30)))

    def test_nonindependent_successor_cannot_retire(self):
        self._expect_stale(self._pair(timedelta(hours=-1), timedelta(days=-2), timedelta(0),
                                      independent=False))

    def test_evidence_free_successor_cannot_retire(self):
        self._expect_stale(self._pair(timedelta(hours=-1), timedelta(days=-2), timedelta(0),
                                      evidence=[]))

    def test_fail_successor_can_retire(self):
        """A later FAIL is the current authority on the file, and the run blocks on it.

        Requiring the successor to be PASS would be the wrong axis: it would mean a
        later round saying 'this is worse than you thought' could not retire an
        earlier round's claim about the file.
        """
        mpath = self._pair(timedelta(hours=-1), timedelta(days=-2), timedelta(0),
                           verdict="FAIL", blockers=1)
        code, out, _ = self.run_gate(*self.base_args("--require", "AC-001",
                                                     "--artifact-map", mpath))
        self.assertEqual(gate.EXIT_OK, code, out)
        self.assertIn("SUPERSEDED", out)
        # And it is not laundering: checking the successor itself still fails.
        code2, out2, _ = self.run_gate(*self.base_args("--require", "AC-002",
                                                      "--artifact-map", mpath))
        self.assertEqual(gate.EXIT_VIOLATION, code2)
        self.assertIn("VERDICT_FAIL", out2)


class TestCwdContext(GateTestCase):
    """Every gate output carries the CWD, and a split run says so loudly.

    The 012 evidence error was a gate driven from a foreign CWD: worktree tools,
    main-tree files, and the resulting 17/31 figure read as a "clean checkout".
    Counts are a property of the calling directory (PROTOCOL.md §10 item 7), so
    the output must bind that coordinate to every number it prints.
    """

    def _artifact_map(self, vid):
        artifact = self.tmp / "src" / "pipeline.py"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("print('hi')", encoding="utf-8")
        map_path = self.tmp / "artifacts.json"
        map_path.write_text(json.dumps({vid: [str(artifact)]}), encoding="utf-8")
        return str(map_path)

    def test_json_output_carries_cwd(self):
        # A non-split run: fixtures must live *under* the process CWD, so build
        # them inside a fresh subdir of the repo's tests dir (CWD = repo root).
        base = Path(tempfile.mkdtemp(dir=REPO_ROOT / "tests"))
        self.addCleanup(lambda: __import__("shutil").rmtree(base, ignore_errors=True))
        vdir = base / "verdicts"
        vdir.mkdir()
        artifact = base / "src" / "pipeline.py"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("print('hi')", encoding="utf-8")
        map_path = base / "artifacts.json"
        map_path.write_text(json.dumps({"AC-20260929-001": [str(artifact)]}), encoding="utf-8")
        (vdir / "AC-20260929-001.verdict.json").write_text(
            json.dumps(_verdict(), ensure_ascii=False), encoding="utf-8")
        code, out, _ = self.run_gate("--verdict-dir", str(vdir), "--require",
                                     "AC-20260929-001", "--artifact-map", str(map_path),
                                     "--json")
        self.assertEqual(gate.EXIT_OK, code, out)
        payload = json.loads(out)
        self.assertEqual(Path(os.getcwd()).resolve(), Path(payload["cwd"]))
        self.assertFalse(payload["split_run"])

    def test_split_run_warns_on_stdout(self):
        """Tools/verdicts outside the CWD is the 012 mistake; it must be visible."""
        self.write_verdict("AC-20260929-001", _verdict())
        code, out, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001",
                                                     "--artifact-map",
                                                     self._artifact_map("AC-20260929-001")))
        # In the test process the CWD is the repo root while the fixtures live in
        # a temp dir — a split run by construction — so the banner must appear.
        if not Path(os.getcwd()).resolve().is_relative_to(self.tmp):
            self.assertIn("[CWD]", out)
            self.assertIn("not the verdict directory", out)

    def test_split_run_still_exits_correctly(self):
        """The banner is advisory: it must not change the exit code or findings."""
        self.write_verdict("AC-20260929-001", _verdict())
        code, _, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001",
                                                   "--artifact-map",
                                                   self._artifact_map("AC-20260929-001")))
        self.assertEqual(gate.EXIT_OK, code)

    def test_quiet_suppresses_cwd_banner(self):
        self.write_verdict("AC-20260929-001", _verdict())
        code, out, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001",
                                                     "--artifact-map",
                                                     self._artifact_map("AC-20260929-001")),
                                     "--quiet")
        self.assertEqual(gate.EXIT_OK, code)
        self.assertNotIn("[CWD]", out)
        self.assertNotIn("CWD context", out)


class SelfSignedTestCase(GateTestCase):
    """ADR-0002 R3: self_signed is read, not merely permitted."""

    def test_self_signed_with_independent_true_is_a_contradiction(self):
        """A verdict may not claim independence while carrying the marker."""
        self.write_verdict("AC-20260929-001",
                           _verdict(self_signed=True, independent=True))
        code, out, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001"))
        self.assertEqual(gate.EXIT_VIOLATION, code, out)
        self.assertIn("SELF_SIGNED_CONTRADICTION", out)

    def test_self_signed_alone_is_not_independent(self):
        """self_signed with independent false is a self-sign: not an authority."""
        self.write_verdict("AC-20260929-001",
                           _verdict(self_signed=True, independent=False))
        code, out, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001"))
        self.assertEqual(gate.EXIT_VIOLATION, code, out)
        self.assertIn("NOT_INDEPENDENT", out)

    def test_self_signed_is_admitted_with_allow_nonindependent(self):
        """The flag admits a *declared* self-sign; that is the whole point of it."""
        self.write_verdict("AC-20260929-001",
                           _verdict(self_signed=True, independent=False))
        code, out, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001"),
                                     "--allow-nonindependent")
        self.assertEqual(gate.EXIT_OK, code, out)

    def test_absent_self_signed_is_never_an_error(self):
        """A normal review omits the field; that must not be read as a defect."""
        self.write_verdict("AC-20260929-001", _verdict())
        code, out, _ = self.run_gate(*self.base_args("--require", "AC-20260929-001"))
        self.assertEqual(gate.EXIT_OK, code, out)

    def test_self_signed_cannot_supersede_another_finding(self):
        """R4 boundary: a self-signed later verdict is not a valid authority.

        Even with --allow-nonindependent, a self-signed verdict must not retire
        an earlier finding - otherwise the flag becomes a laundering route.
        """
        base = self.tmp
        artifact = base / "src" / "pipeline.py"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("print('hi')", encoding="utf-8")
        map_path = base / "artifacts.json"
        map_path.write_text(
            json.dumps({"AC-20260929-001": [str(artifact)],
                        "AC-20260929-002": [str(artifact)]}),
            encoding="utf-8")
        # Earlier verdict is fresh on the file; the later one is self-signed.
        self.write_verdict("AC-20260929-001", _verdict())
        later = _verdict(id="AC-20260929-002", self_signed=True, independent=False,
                         verifier="author@acme")
        self.write_verdict("AC-20260929-002", later)
        code, out, _ = self.run_gate("--verdict-dir", str(self.vdir),
                                     "--require", "AC-20260929-001",
                                     "--artifact-map", str(map_path), "--json",
                                     "--allow-nonindependent")
        payload = json.loads(out)
        codes = [v.get("code") or v.get("reason") for v in payload.get("violations", [])]
        # Whatever the earlier verdict reports, it must NOT be retired as
        # SUPERSEDED by a self-signed successor.
        advisories = payload.get("advisories", [])
        self.assertNotIn("SUPERSEDED", json.dumps(payload.get("violations", [])), out)
        self.assertEqual(gate.EXIT_OK, code, out)


class UnblocksBoundaryTestCase(GateTestCase):
    """ADR-0002 R4: closure never substitutes for freshness, in either direction."""

    def test_self_signed_successor_check_is_load_bearing(self):
        """S2: show the strictness is necessary, not just present.

        Same fixture under both semantics. With strict_independence=False
        (the pre-ADR-0002 behaviour, where the run-level
        --allow-nonindependent flag flowed into the successor bar), a
        self-signed later verdict enters the candidate set and can retire an
        earlier finding. With the default True, it does not. Asserting both
        directions is what makes this a necessity proof rather than a
        behaviour snapshot: if the default ever stopped mattering, this test
        fails on the False branch, not the True one.
        """
        base = self.tmp
        artifact = base / "src" / "pipeline.py"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("print('hi')", encoding="utf-8")
        map_path = base / "artifacts.json"
        map_path.write_text(
            json.dumps({"AC-20260929-001": [str(artifact)],
                        "AC-20260929-002": [str(artifact)]}),
            encoding="utf-8")
        self.write_verdict("AC-20260929-001", _verdict())
        later = _verdict(id="AC-20260929-002", self_signed=True, independent=False,
                         verifier="author@acme")
        self.write_verdict("AC-20260929-002", later)

        class _Args:
            allow_nonindependent = True   # the run-level flag is ON
            max_clock_skew = 300

        args = _Args()
        amap = gate._read_artifact_map(map_path)

        # Old semantics: the flag flowed into the successor bar, so the
        # self-signed verdict qualified as a superseding authority.
        old = gate._successor_candidates(self.vdir, amap, args,
                                         strict_independence=False)
        self.assertIn("AC-20260929-002", old,
                      "pre-ADR-0002 semantics must admit the self-signed "
                      "successor; if it does not, the fixture stopped "
                      "demonstrating the hole")

        # Current semantics: the default refuses the same verdict even with
        # the run-level flag on.
        new = gate._successor_candidates(self.vdir, amap, args)
        self.assertNotIn("AC-20260929-002", new)

    def test_unblocks_does_not_launder_a_stale_finding(self):
        """Positive direction: closure leaves a STALE finding reported.

        The verdict carries unblocks, but the artifact changed after it was
        signed and no later verdict covers it. The STALE must still be raised -
        discharging a condition is not a claim about file freshness.
        """
        base = self.tmp
        artifact = base / "src" / "pipeline.py"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("print('hi')", encoding="utf-8")
        map_path = base / "artifacts.json"
        map_path.write_text(
            json.dumps({"AC-20260929-001": [str(artifact)]}), encoding="utf-8")
        old = _verdict(unblocks=["AC-20260929-000.C1"])
        old_ts = (datetime.now(timezone.utc) - timedelta(days=2)).replace(microsecond=0)
        old["ts"] = old_ts.isoformat().replace("+00:00", "Z")
        self.write_verdict("AC-20260929-001", old)
        # Make the artifact newer than the verdict that judged it.
        later = datetime.now(timezone.utc) + timedelta(seconds=5)
        os.utime(artifact, (later.timestamp(), later.timestamp()))
        code, out, _ = self.run_gate("--verdict-dir", str(self.vdir),
                                     "--require", "AC-20260929-001",
                                     "--artifact-map", str(map_path))
        self.assertEqual(gate.EXIT_VIOLATION, code, out)
        self.assertIn("STALE", out)
        self.assertNotIn("SUPERSEDED", out)

    def test_unblocks_never_produces_superseded(self):
        """Negative direction: no arrangement turns unblocks into SUPERSEDED.

        Two verdicts, both carrying the same resolution reference, neither of
        which lists the other's artifact as fresh. Whatever else is reported,
        SUPERSEDED must not appear from the unblocks field alone.
        """
        base = self.tmp
        artifact = base / "src" / "pipeline.py"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("print('hi')", encoding="utf-8")
        map_path = base / "artifacts.json"
        # Only 001 lists the artifact; 002 lists nothing, so it cannot be a
        # successor on that file however its unblocks reads.
        map_path.write_text(
            json.dumps({"AC-20260929-001": [str(artifact)],
                        "AC-20260929-002": []}),
            encoding="utf-8")
        self.write_verdict("AC-20260929-001", _verdict(unblocks=["AC-20260929-000.C1"]))
        self.write_verdict("AC-20260929-002",
                           _verdict(id="AC-20260929-002", unblocks=["AC-20260929-000.C1"]))
        code, out, _ = self.run_gate("--verdict-dir", str(self.vdir),
                                     "--require", "AC-20260929-001",
                                     "--artifact-map", str(map_path))
        self.assertNotIn("SUPERSEDED", out)


class TestLinkTraceability(GateTestCase):
    """Phase 2: the gate consumes `.freeze/link-<id>.json`.

    A link is written by two tools (`deepfreeze protect --card` for the snap
    group, `tools/link_card.py` for the verdict group) and, unlike every other
    input here, it names the *snapshot* a review was performed against. The gate
    only honours it when it exists: most historical cards predate the convention,
    so a missing link is silent unless `--require-link` names the id. Once a link
    exists the card has promised traceability, so every defect in it blocks.
    """

    def setUp(self):
        super().setUp()
        self.ldir = self.tmp / ".freeze"
        (self.ldir / "manifests").mkdir(parents=True)

    # -- fixtures ---------------------------------------------------------
    def stamp(self, offset=timedelta(0)):
        """deepfreeze's compact local-time stamp, offset from 'now'."""
        return (datetime.now() + offset).strftime("%Y%m%d-%H%M%S")

    def link_payload(self, vid="AC-20260929-001", snap_ts=None, **extra):
        payload = {
            "card": vid,
            "snap_ts": snap_ts or self.stamp(timedelta(hours=-2)),
            "snap_path": str(self.tmp / "snapshot"),
            "snapshot_root": str(self.tmp),
            "source": str(self.tmp),
            "created_at": "2026-10-20 19:21:35",
        }
        payload.update(extra)
        return payload

    def write_link(self, payload, vid="AC-20260929-001", bom=True, raw=None):
        text = raw if raw is not None else json.dumps(payload, ensure_ascii=False)
        data = text.encode("utf-8")
        if bom:
            data = b"\xef\xbb\xbf" + data
        path = self.ldir / f"link-{vid}.json"
        path.write_bytes(data)
        return path

    def write_manifest(self, snap_ts):
        path = self.ldir / "manifests" / f"{snap_ts}.json"
        path.write_text("{}", encoding="utf-8")
        return path

    def verdict_sha(self, vid="AC-20260929-001"):
        import hashlib
        return hashlib.sha256((self.vdir / f"{vid}.verdict.json").read_bytes()).hexdigest()

    def link_args(self, *extra):
        return self.base_args("--link-dir", str(self.ldir), *extra)

    # -- happy paths ------------------------------------------------------
    def test_full_link_passes(self):
        self.write_verdict("AC-20260929-001", _verdict())
        snap = self.stamp(timedelta(hours=-2))
        self.write_manifest(snap)
        self.write_link(self.link_payload(
            snap_ts=snap,
            verdict_ts=_verdict()["ts"],
            verdict_sha256=self.verdict_sha(),
            verifier="reviewer@acme",
            updated_at="2026-10-20 19:25:00",
        ))
        code, out, _ = self.run_gate(*self.link_args("--require", "AC-20260929-001"))
        self.assertEqual(gate.EXIT_OK, code, out)
        self.assertNotIn("LINK_", out)

    def test_snap_only_link_skips_the_verdict_group(self):
        """A pre-verdict link carries only the snap group; nothing to compare yet."""
        self.write_verdict("AC-20260929-001", _verdict())
        snap = self.stamp(timedelta(hours=-2))
        self.write_manifest(snap)
        self.write_link(self.link_payload(snap_ts=snap))
        code, out, _ = self.run_gate(*self.link_args("--require", "AC-20260929-001"))
        self.assertEqual(gate.EXIT_OK, code, out)
        self.assertNotIn("LINK_", out)

    def test_bom_prefixed_link_is_read_cleanly(self):
        """deepfreeze writes a UTF-8 BOM; utf-8-sig must strip it, not fail the parse."""
        self.write_verdict("AC-20260929-001", _verdict())
        snap = self.stamp(timedelta(hours=-2))
        self.write_manifest(snap)
        path = self.write_link(self.link_payload(snap_ts=snap), bom=True)
        self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"))
        code, out, _ = self.run_gate(*self.link_args("--require", "AC-20260929-001"))
        self.assertEqual(gate.EXIT_OK, code, out)
        self.assertNotIn("LINK_UNREADABLE", out)

    # -- absence policy ---------------------------------------------------
    def test_missing_link_is_silent_without_require_link(self):
        self.write_verdict("AC-20260929-001", _verdict())
        code, out, _ = self.run_gate(*self.link_args())
        self.assertEqual(gate.EXIT_OK, code, out)
        self.assertNotIn("LINK_", out)

    def test_missing_link_blocks_when_required(self):
        self.write_verdict("AC-20260929-001", _verdict())
        code, out, _ = self.run_gate(*self.link_args("--require", "AC-20260929-001",
                                                     "--require-link", "AC-20260929-001"))
        self.assertEqual(gate.EXIT_VIOLATION, code, out)
        self.assertIn("LINK_REQUIRED_MISSING", out)
        self.assertIn("deepfreeze protect --card", out)

    def test_no_link_check_disables_the_whole_family(self):
        self.write_verdict("AC-20260929-001", _verdict())
        self.write_link(self.link_payload(card="AC-999"), raw='{"card": "AC-999", "snap_ts": "bogus"}')
        code, out, _ = self.run_gate(*self.link_args("--require", "AC-20260929-001",
                                                     "--require-link", "AC-20260929-001",
                                                     "--no-link-check"))
        self.assertEqual(gate.EXIT_OK, code, out)
        self.assertNotIn("LINK_", out)

    def test_missing_verdict_skips_link_checks(self):
        """No verdict means nothing to trace; the existing MISSING_VERDICT is the finding."""
        code, out, _ = self.run_gate(*self.link_args("--require", "AC-20260929-404",
                                                     "--require-link", "AC-20260929-404"))
        self.assertEqual(gate.EXIT_VIOLATION, code, out)
        self.assertIn("MISSING_VERDICT", out)
        self.assertNotIn("LINK_REQUIRED_MISSING", out)

    # -- blocking defects -------------------------------------------------
    def assert_link_violation(self, code_name, payload=None, raw=None, vid="AC-20260929-001",
                              bom=True):
        self.write_verdict(vid, _verdict(id=vid))
        self.write_link(payload, vid=vid, bom=bom, raw=raw)
        code, out, _ = self.run_gate(*self.link_args("--require", vid))
        self.assertEqual(gate.EXIT_VIOLATION, code, out)
        self.assertIn(code_name, out)
        return out

    def test_corrupt_link_json_blocks(self):
        self.assert_link_violation("LINK_UNREADABLE", raw="{not json")

    def test_card_mismatch_blocks(self):
        self.assert_link_violation("LINK_CARD_MISMATCH",
                                   payload=self.link_payload(card="AC-20260929-999"))

    def test_manifest_missing_blocks(self):
        snap = self.stamp(timedelta(hours=-2))
        out = self.assert_link_violation("LINK_MANIFEST_MISSING",
                                         payload=self.link_payload(snap_ts=snap))
        self.assertIn(snap, out)

    def test_verdict_sha_mismatch_blocks(self):
        """Re-signing a verdict changes its bytes and invalidates the link."""
        self.write_verdict("AC-20260929-001", _verdict())
        snap = self.stamp(timedelta(hours=-2))
        self.write_manifest(snap)
        self.write_link(self.link_payload(snap_ts=snap,
                                          verdict_ts=_verdict()["ts"],
                                          verdict_sha256=self.verdict_sha()))
        # Re-serialise the verdict (same meaning, different bytes).
        self.write_verdict("AC-20260929-001", _verdict(conditions=["re-serialised"]))
        code, out, _ = self.run_gate(*self.link_args("--require", "AC-20260929-001"))
        self.assertEqual(gate.EXIT_VIOLATION, code, out)
        self.assertIn("LINK_VERDICT_SHA_MISMATCH", out)
        self.assertIn("link_card.py", out)

    def test_verdict_ts_before_snap_ts_blocks(self):
        """A verdict cannot have judged a snapshot taken after it was signed."""
        self.write_verdict("AC-20260929-001", _verdict())
        snap = self.stamp(timedelta(hours=2))
        self.write_manifest(snap)
        past = (datetime.now(timezone.utc) - timedelta(hours=3)).replace(microsecond=0)
        self.write_link(self.link_payload(
            snap_ts=snap,
            verdict_ts=past.isoformat().replace("+00:00", "Z"),
            verdict_sha256=self.verdict_sha(),
        ))
        code, out, _ = self.run_gate(*self.link_args("--require", "AC-20260929-001"))
        self.assertEqual(gate.EXIT_VIOLATION, code, out)
        self.assertIn("LINK_TS_INVERTED", out)

    def test_link_findings_appear_as_blocking_json(self):
        self.write_verdict("AC-20260929-001", _verdict())
        self.write_link(self.link_payload(card="AC-20260929-999"))
        code, out, _ = self.run_gate(*self.link_args("--require", "AC-20260929-001", "--json"))
        payload = json.loads(out)
        self.assertEqual(gate.EXIT_VIOLATION, code)
        self.assertFalse(payload["ok"])
        self.assertTrue(any(v["code"] == "LINK_CARD_MISMATCH" for v in payload["violations"]))
        self.assertEqual([], payload["advisories"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
