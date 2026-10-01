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


if __name__ == "__main__":
    unittest.main(verbosity=2)
