#!/usr/bin/env python3
"""Tests for the v1.1 two-arm study runner (XJ-20261024-003 D3).

The card's soul lives in the B-arm zero-execution guarantee: if arm B ever
executes an evidence command, the degenerate-arm defect (the exact thing v1.1
C1 was written to fix) walks back in through the instrument. So these tests
prove non-execution behaviorally (marker files a real execution would leave
behind), not just by reading the run log the runner itself wrote.
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

import blind  # noqa: E402
import study_runner  # noqa: E402
from extract import extract_claims  # noqa: E402
from schema import Acceptance, TaskDef  # noqa: E402


MARKER_COMMAND = ("python -c \"from pathlib import Path; "
                  "Path('marker.txt').write_text('ran'); print('ran')\"")


def make_task(task_id="T01", acceptance=None):
    return TaskDef(
        id=task_id, layer="fact", title="runner test task",
        prompt="runner test: produce a report with evidence-tagged claims.",
        product=f"{task_id}.md",
        acceptance=acceptance or Acceptance(type="answer", value="ok"),
        notes="synthetic test task",
    )


def make_draft(claims=None, answer="ok", acceptance_ok=None):
    draft = {
        "task_id": "T01",
        "answer": answer,
        "claims": claims if claims is not None else [{
            "text": "测试断言：标记命令以退出码 0 运行并写出 `marker` 文件",
            "cmd": MARKER_COMMAND,
            "believed_exit": 0,
            "believed_out": "ran",
        }],
    }
    if acceptance_ok is not None:
        draft["acceptance_ok"] = acceptance_ok
    return draft


class ArmBehaviorTests(unittest.TestCase):
    """Arm A executes and records; arm B executes nothing at all."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.workspace = self.root / "ws"
        self.workspace.mkdir()
        self.task = make_task()
        self.draft = make_draft()

    def tearDown(self):
        self._tmp.cleanup()

    def run_arm(self, condition, out_dir=None, task=None, draft=None):
        out_dir = out_dir or self.root / f"run-{condition}"
        out_dir.mkdir(parents=True, exist_ok=True)
        entries = []
        run_log = study_runner.RunLog(self.workspace)
        study_runner.run_arm(condition, [task or self.task],
                             {task.id if task else "T01": draft or self.draft},
                             1, out_dir, self.workspace, 60, entries, run_log)
        study_runner.write_run_data(out_dir, entries)
        study_runner.write_run_log(out_dir, run_log)
        return out_dir, entries, run_log

    def test_arm_a_executes_and_records(self):
        out_dir, entries, run_log = self.run_arm("A")
        self.assertTrue((self.workspace / "marker.txt").exists(),
                        "arm A must really execute the evidence command")
        executed = [r for r in run_log.records
                    if r["kind"] == "evidence" and r["executed"]]
        self.assertTrue(executed, "arm A run-log must hold an executed record")
        self.assertEqual(executed[0]["exit_code"], 0)

    def test_arm_b_executes_nothing(self):
        out_dir, entries, run_log = self.run_arm("B")
        self.assertFalse((self.workspace / "marker.txt").exists(),
                         "arm B executed the evidence command -- protocol violation")
        self.assertEqual(run_log.records, [],
                         "arm B run-log must be empty: no subprocess of any kind")
        log = json.loads((out_dir / "run-log.json").read_text(encoding="utf-8"))
        self.assertEqual(log["records"], [])

    def test_arm_b_writes_believed_values_verbatim(self):
        _, _, _ = self.run_arm("B")
        text = (self.root / "run-B" / "products" / "T01-B-r1.md").read_text(encoding="utf-8")
        self.assertIn("exit=0", text)
        self.assertIn("out=`ran`", text)

    def test_arm_a_writes_real_values(self):
        self.run_arm("A")
        text = (self.root / "run-A" / "products" / "T01-A-r1.md").read_text(encoding="utf-8")
        self.assertIn("exit=0", text)
        self.assertIn("out=`ran`", text)

    def test_arms_are_syntax_identical(self):
        """Card decision 1: same claims, same commands; only evidence
        provenance differs. Any other divergence is an arm confound."""
        self.run_arm("A")
        self.run_arm("B")
        text_a = (self.root / "run-A" / "products" / "T01-A-r1.md").read_text(encoding="utf-8")
        text_b = (self.root / "run-B" / "products" / "T01-B-r1.md").read_text(encoding="utf-8")
        claims_a = extract_claims(text_a)
        claims_b = extract_claims(text_b)
        self.assertEqual([c.text for c in claims_a], [c.text for c in claims_b])
        self.assertTrue(claims_a and claims_b, "both products must carry claims")
        for pair in zip(claims_a, claims_b):
            self.assertIsNotNone(pair[0].evidence)
            self.assertIsNotNone(pair[1].evidence)
            self.assertTrue(pair[0].evidence.is_complete)
            self.assertTrue(pair[1].evidence.is_complete)
            self.assertEqual(pair[0].evidence.command, pair[1].evidence.command)

    def test_arm_a_refused_command_never_runs_and_stays_honest(self):
        """Denylist: no execution, no fabricated exit/out -- the evidence line
        falls back to command-only (structurally E1), never a made-up pass."""
        draft = make_draft(claims=[{
            "text": "拒绝清单断言：该命令不应被执行",
            "cmd": "python -c \"print('x')\" && rm -rf nowhere",
            "believed_exit": 0,
            "believed_out": "x",
        }])
        out_dir, entries, run_log = self.run_arm("A", draft=draft)
        records = [r for r in run_log.records if r["kind"] == "evidence"]
        self.assertTrue(records and records[0]["executed"] is False)
        self.assertIsNotNone(records[0]["refused"])
        text = (out_dir / "products" / "T01-A-r1.md").read_text(encoding="utf-8")
        claims = extract_claims(text)
        self.assertEqual(len(claims), 1)
        self.assertIsNotNone(claims[0].evidence)
        self.assertIsNone(claims[0].evidence.exit_code, "refused command must not gain an exit code")
        self.assertFalse(claims[0].evidence.is_complete)

    def test_snippet_is_single_line_without_backticks(self):
        draft = make_draft(claims=[{
            "text": "多行输出断言：`marker` 应出现在输出中",
            "cmd": "python -c \"print('line1'); print('line2')\"",
            "believed_exit": 0,
            "believed_out": "line1",
        }])
        out_dir, _, _ = self.run_arm("A", draft=draft)
        text = (out_dir / "products" / "T01-A-r1.md").read_text(encoding="utf-8")
        claims = extract_claims(text)
        self.assertEqual(len(claims), 1)
        evidence = claims[0].evidence
        self.assertIsNotNone(evidence)
        self.assertTrue(evidence.is_complete)
        self.assertNotIn("`", evidence.out or "")
        self.assertNotIn("\n", evidence.out or "")

    def test_coverage_answer_type(self):
        out_dir, entries, _ = self.run_arm("A")
        self.assertTrue(entries[0]["coverage"], "答案：ok must count as covered")
        draft = make_draft(answer="MIT")
        out_dir, entries, _ = self.run_arm("A", out_dir=self.root / "run-wrong",
                                           draft=draft)
        self.assertFalse(entries[0]["coverage"])

    def test_coverage_command_type_asymmetric_by_design(self):
        """Command acceptance: arm A verifies by running the frozen acceptance
        command; arm B takes the draft's self-assessment and runs nothing."""
        acc_command = ("python -c \"from pathlib import Path; "
                       "Path('accept.txt').write_text('done')\"")
        task = make_task(acceptance=Acceptance(type="command", command=acc_command))
        draft = make_draft(claims=[{
            "text": "无命令断言（coverage 走 acceptance 路径）",
            "ref": "README.md",
        }], answer=None, acceptance_ok=True)

        out_a, entries_a, log_a = self.run_arm("A", out_dir=self.root / "run-acc-a",
                                               task=task, draft=draft)
        self.assertTrue((self.workspace / "accept.txt").exists())
        self.assertTrue(entries_a[0]["coverage"])
        self.assertTrue(any(r["kind"] == "acceptance" for r in log_a.records))

        (self.workspace / "accept.txt").unlink()  # B must not recreate it
        out_b, entries_b, log_b = self.run_arm("B", out_dir=self.root / "run-acc-b",
                                               task=task, draft=draft)
        self.assertFalse((self.workspace / "accept.txt").exists(),
                         "arm B must not run the acceptance command")
        self.assertTrue(entries_b[0]["coverage"], "B coverage comes from the draft claim")
        self.assertEqual(log_b.records, [])

        draft_deny = make_draft(claims=[{"text": "x", "ref": "README.md"}],
                                answer=None, acceptance_ok=False)
        _, entries_c, _ = self.run_arm("B", out_dir=self.root / "run-acc-c",
                                       task=task, draft=draft_deny)
        self.assertFalse(entries_c[0]["coverage"])


class RunDataContractTests(unittest.TestCase):
    """run-data.json must round-trip through blind.load_run_data, and resume
    must never duplicate a key."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.task = make_task()
        self.draft = make_draft()

    def tearDown(self):
        self._tmp.cleanup()

    def _produce(self, out_dir, condition):
        workspace = self.root / "ws"
        workspace.mkdir(parents=True, exist_ok=True)
        entries, records = study_runner.load_existing(out_dir)
        run_log = study_runner.RunLog(workspace)
        run_log.records = list(records)
        study_runner.run_arm(condition, [self.task], {"T01": self.draft}, 2,
                             out_dir, workspace, 60, entries, run_log)
        study_runner.write_run_data(out_dir, entries)
        study_runner.write_run_log(out_dir, run_log)
        return entries

    def test_run_data_round_trip(self):
        out_dir = self.root / "run"
        self._produce(out_dir, "A")
        self._produce(out_dir, "B")
        parsed = blind.load_run_data(out_dir)
        self.assertEqual(len(parsed), 4)  # 1 task x 2 reps x 2 arms
        by_key = {entry.key: entry for entry in parsed}
        self.assertEqual(by_key["T01-A-r1"].condition, "A")
        self.assertEqual(by_key["T01-B-r2"].condition, "B")
        self.assertEqual(by_key["T01-A-r1"].repetition, 1)
        self.assertTrue(by_key["T01-A-r1"].product_path.is_file())

    def test_resume_is_idempotent(self):
        out_dir = self.root / "run"
        entries_first = self._produce(out_dir, "A")
        product = out_dir / "products" / "T01-A-r1.md"
        before = product.read_text(encoding="utf-8")
        entries_second = self._produce(out_dir, "A")
        self.assertEqual(entries_first, entries_second)
        self.assertEqual(product.read_text(encoding="utf-8"), before)

    def test_summary_reports_arm_symmetry_data(self):
        out_dir = self.root / "run"
        self._produce(out_dir, "A")
        self._produce(out_dir, "B")
        data = json.loads((out_dir / "run-data.json").read_text(encoding="utf-8"))
        self.assertEqual(data["summary"]["A"]["tasks_with_evidenced_claim"], 1)
        self.assertEqual(data["summary"]["B"]["tasks_with_evidenced_claim"], 1)


class ProtocolGuardTests(unittest.TestCase):
    """The card's hard constraint 2: if arm B ever holds execution records,
    the run itself must fail."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_task_and_draft(self):
        tasks_dir = self.root / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "T01.json").write_text(json.dumps({
            "id": "T01", "layer": "fact", "title": "guard task",
            "prompt": "guard: draft must load for the CLI run.",
            "product": "T01.md",
            "acceptance": {"type": "answer", "value": "ok"},
        }, ensure_ascii=False), encoding="utf-8")
        drafts_dir = self.root / "drafts"
        drafts_dir.mkdir()
        (drafts_dir / "T01.json").write_text(json.dumps(make_draft(), ensure_ascii=False),
                                             encoding="utf-8")
        return tasks_dir, drafts_dir

    def test_cli_b_run_with_tampered_log_fails(self):
        """A B-arm run-log that already holds a B record (tampered or carried
        over) must make the run fail loudly, not pass silently."""
        tasks_dir, drafts_dir = self._write_task_and_draft()
        out_dir = self.root / "run"
        out_dir.mkdir()
        (out_dir / "run-log.json").write_text(json.dumps({
            "generated_utc": "2026-10-24T00:00:00+00:00",
            "workspace": str(self.root),
            "records": [{"key": "T01-B-r1", "task_id": "T01", "condition": "B",
                         "kind": "evidence", "command": "python -c \"print('x')\"",
                         "executed": True, "exit_code": 0, "refused": None,
                         "error": "", "utc": "2026-10-24T00:00:00+00:00"}],
        }, ensure_ascii=False), encoding="utf-8")
        code = study_runner.main([
            "--condition", "B", "--drafts-dir", str(drafts_dir),
            "--out", str(out_dir), "--tasks-dir", str(tasks_dir), "--reps", "1",
        ])
        self.assertEqual(code, study_runner.EXIT_FAIL)

    def test_cli_selftest_passes(self):
        self.assertEqual(study_runner.main(["--selftest"]), study_runner.EXIT_OK)

    def test_dispatch_briefs_keep_syntax_symmetric(self):
        """v1.1 extra constraint 2: the B brief must not hint that evidence
        lines are optional; both briefs carry the identical frozen syntax."""
        tasks_dir, _ = self._write_task_and_draft()
        out_dir = self.root / "briefs"
        code = study_runner.main([
            "--dispatch", "--out", str(out_dir), "--tasks-dir", str(tasks_dir),
        ])
        self.assertEqual(code, study_runner.EXIT_OK)
        for condition in ("A", "B"):
            brief = (out_dir / "dispatch" / condition / "T01.md").read_text(encoding="utf-8")
            self.assertIn("证据：cmd=`<命令>` exit=<整数> out=`<预期输出片段>`", brief)
            self.assertIn("答案：", brief)
        brief_b = (out_dir / "dispatch" / "B" / "T01.md").read_text(encoding="utf-8")
        for forbidden in ("不做证据行", "可以随便写", "无需证据行"):
            self.assertNotIn(forbidden, brief_b)


if __name__ == "__main__":
    unittest.main()
