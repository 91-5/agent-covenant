#!/usr/bin/env python3
"""v1.8 R1 observation-surface alignment tests (card XJ-20261110-001 D1).

Synthetic data only (C12). These tests pin the two frozen behaviours of
docs/eval-prereg.md §16:

  D16-1  criterion commands run with cwd = workspace (the C10 rebuilt
          execution workspace), with NO fallback to root;
  D16-2  artifact paths resolve workspace-first, root as fallback, first hit
          wins — the same order the main track uses for ref-form evidence
          (judge.py:274-289).

They also pin the two properties that make the attribution possible: with no
workspace the behaviour is byte-identical to the pre-R1 instrument, and the
aligner output stays free of any five-level token (§13 ④).

Run from the repository root:
    python -m unittest discover -s tests
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

import dsl_compiler as dc  # noqa: E402
import shadow_align  # noqa: E402


def _rec(cid, predicate="exit_equals", expected=0, command=None, artifact=None,
         ctype="command_output", span=(1, 2)):
    return {"claim_id": cid, "claim_type": ctype, "statement": "s " + cid,
            "verification_command": command, "artifact_path": artifact,
            "evidence_span": list(span), "predicate": predicate,
            "expected": expected}


class CommandCwdTests(unittest.TestCase):
    """D16-1: the command's cwd is the workspace, not the observation root."""

    def test_command_runs_in_workspace_not_root(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            root = base / "root"
            workspace = base / "workspace"
            root.mkdir()
            workspace.mkdir()
            # a marker file only the workspace can see
            (workspace / "marker.py").write_text("print('from-workspace')\n",
                                                 encoding="utf-8")
            rec = _rec("w1", command="python marker.py",
                       predicate="command_stdout_contains",
                       expected="from-workspace")
            at_workspace = dc.execute_record(rec, root, 30, workspace=workspace)
            at_root = dc.execute_record(rec, root, 30)
            self.assertTrue(at_workspace["predicate_ok"])
            self.assertFalse(at_root["predicate_ok"])

    def test_workspace_is_recorded_as_cwd(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            root = base / "root"
            workspace = base / "workspace"
            root.mkdir()
            workspace.mkdir()
            rec = _rec("w2", command="python -c \"pass\"")
            res = dc.execute_record(rec, root, 30, workspace=workspace)
            self.assertEqual(res["cwd"], str(workspace))

    def test_no_workspace_keeps_legacy_root_cwd(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            root = base / "root"
            workspace = base / "workspace"
            root.mkdir()
            workspace.mkdir()
            (root / "marker.py").write_text("print('from-root')\n",
                                            encoding="utf-8")
            rec = _rec("w3", command="python marker.py",
                       predicate="command_stdout_contains",
                       expected="from-root")
            res = dc.execute_record(rec, root, 30)
            self.assertTrue(res["predicate_ok"])
            self.assertIsNone(res["cwd"])


class ArtifactResolutionTests(unittest.TestCase):
    """D16-2: workspace first, root as fallback, first hit wins."""

    def test_artifact_found_in_workspace(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            root = base / "root"
            workspace = base / "workspace"
            root.mkdir()
            workspace.mkdir()
            (workspace / "doc.md").write_text("workspace-copy\n", encoding="utf-8")
            rec = _rec("a1", ctype="fact_value", predicate="contains",
                       expected="workspace-copy", artifact="doc.md")
            res = dc.execute_record(rec, root, 30, workspace=workspace)
            self.assertTrue(res["predicate_ok"])
            self.assertEqual(res["artifact_surface"], "workspace")

    def test_artifact_falls_back_to_root(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            root = base / "root"
            workspace = base / "workspace"
            root.mkdir()
            workspace.mkdir()
            (root / "only-root.md").write_text("root-copy\n", encoding="utf-8")
            rec = _rec("a2", ctype="fact_value", predicate="contains",
                       expected="root-copy", artifact="only-root.md")
            res = dc.execute_record(rec, root, 30, workspace=workspace)
            self.assertTrue(res["predicate_ok"])
            self.assertEqual(res["artifact_surface"], "root")

    def test_workspace_wins_over_root_when_both_exist(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            root = base / "root"
            workspace = base / "workspace"
            root.mkdir()
            workspace.mkdir()
            (root / "both.md").write_text("root-copy\n", encoding="utf-8")
            (workspace / "both.md").write_text("workspace-copy\n", encoding="utf-8")
            rec = _rec("a3", ctype="fact_value", predicate="contains",
                       expected="workspace-copy", artifact="both.md")
            res = dc.execute_record(rec, root, 30, workspace=workspace)
            self.assertTrue(res["predicate_ok"])
            self.assertEqual(res["artifact_surface"], "workspace")

    def test_artifact_absent_in_both_faces_is_a_miss_not_a_crash(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            root = base / "root"
            workspace = base / "workspace"
            root.mkdir()
            workspace.mkdir()
            rec = _rec("a4", ctype="fact_existence", predicate="exists",
                       expected="x", artifact="nope.md")
            res = dc.execute_record(rec, root, 30, workspace=workspace)
            self.assertFalse(res["predicate_ok"])
            self.assertEqual(res["artifact_surface"], "root")

    def test_out_of_bounds_still_refused(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            root = base / "root"
            workspace = base / "workspace"
            root.mkdir()
            workspace.mkdir()
            rec = _rec("a5", ctype="fact_existence", predicate="exists",
                       expected="x", artifact="../escape.md")
            res = dc.execute_record(rec, root, 30, workspace=workspace)
            self.assertFalse(res["predicate_ok"])
            self.assertIn("artifact_path_out_of_bounds", res["flags"])

    def test_command_artifact_created_resolves_workspace_first(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            root = base / "root"
            workspace = base / "workspace"
            root.mkdir()
            workspace.mkdir()
            (workspace / "made.py").write_text("x = 1\n", encoding="utf-8")
            rec = _rec("a6", predicate="command_artifact_created",
                       expected="made.py", command="python -c \"pass\"")
            res = dc.execute_record(rec, root, 30, workspace=workspace)
            self.assertTrue(res["predicate_ok"])
            self.assertEqual(res["artifact_surface"], "workspace")

    def test_command_artifact_created_absent_everywhere_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            root = base / "root"
            workspace = base / "workspace"
            root.mkdir()
            workspace.mkdir()
            rec = _rec("a7", predicate="command_artifact_created",
                       expected="never.py", command="python -c \"pass\"")
            res = dc.execute_record(rec, root, 30, workspace=workspace)
            self.assertFalse(res["predicate_ok"])


class AlignerSurfaceTests(unittest.TestCase):
    """The aligner reports the surface it used and stays level-token free."""

    def _main(self, level, line):
        return {"text": "断言", "source_line": line, "product": "P901",
                "evidence": {"raw": "x"}, "anchors": [], "unanchored": True,
                "_level": level}

    def _rec(self, cid, line):
        return {"claim_id": cid, "claim_type": "command_output",
                "statement": "s", "verification_command": "python -c \"pass\"",
                "artifact_path": None, "evidence_span": [line, line + 1],
                "predicate": "exit_equals", "expected": 0}

    def test_surface_block_reports_cwd(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            root = base / "root"
            workspace = base / "workspace"
            root.mkdir()
            workspace.mkdir()
            r = shadow_align.align({"P901": [self._main("E4", 10)]},
                                   {"P901": [self._rec("a", 10)]},
                                   root, workspace=workspace)
            surface = r["observation_surface"]
            self.assertEqual(surface["command_cwd"], str(workspace))
            self.assertEqual(surface["surface_mode"], "r1-workspace")

    def test_pre_r1_mode_is_root(self):
        with tempfile.TemporaryDirectory() as raw:
            r = shadow_align.align({"P901": [self._main("E4", 10)]},
                                   {"P901": [self._rec("a", 10)]}, Path(raw))
            self.assertEqual(r["observation_surface"]["surface_mode"],
                             "pre-r1-root")
            self.assertIsNone(r["observation_surface"]["workspace"])

    def test_output_still_carries_no_level_token(self):
        with tempfile.TemporaryDirectory() as raw:
            r = shadow_align.align({"P901": [self._main("E4", 10)]},
                                   {"P901": [self._rec("a", 10)]}, Path(raw))
        payload = json.dumps(r)
        self.assertNotIn('"E4"', payload)
        self.assertNotIn('"level"', payload)
        self.assertNotIn("verdict", payload)


class CompileReportTests(unittest.TestCase):
    """Card D1: the compile-report records the cwd explicitly."""

    def test_compile_report_records_cwd(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            root = base / "root"
            workspace = base / "workspace"
            root.mkdir()
            workspace.mkdir()
            rec = {"claim_id": "a", "claim_type": "command_output",
                   "statement": "s", "verification_command": "python -c \"pass\"",
                   "artifact_path": None, "evidence_span": [10, 11],
                   "predicate": "exit_equals", "expected": 0}
            result = shadow_align.align(
                {"P901": [{"text": "断言", "source_line": 10, "product": "P901",
                           "evidence": {"raw": "x"}, "anchors": [],
                           "unanchored": True, "_level": "E4"}]},
                {"P901": [rec]}, root, workspace=workspace)
            out = base / "compile-report.json"
            payload = shadow_align.write_compile_report(out, result, [rec])
            self.assertTrue(out.is_file())
            self.assertEqual(payload["cwd"], str(workspace))
            on_disk = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(on_disk["cwd"], str(workspace))


if __name__ == "__main__":
    unittest.main()
