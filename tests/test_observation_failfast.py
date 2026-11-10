#!/usr/bin/env python3
"""E7 fail-fast observation ERROR classes (council pre-merge supplement,
cards XJ-20261110-001/002).

Synthetic data only (C12).  Pins the round-9 root cause fix: a criterion that
fails because its observation surface does not expose the artifact must be
reported as a pre-registered ERROR and excluded from the agreement
denominator, never silently graded as "criterion not supported".

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

import shadow_align  # noqa: E402


def main_claim(level="E4", line=10):
    return {"text": "断言", "source_line": line, "product": "P901",
            "evidence": {"raw": "x"}, "anchors": [], "unanchored": True,
            "_level": level}


def record(cid="a", line=10, command="python -c \"pass\"",
           predicate="exit_equals", expected=0):
    return {"claim_id": cid, "claim_type": "command_output",
            "statement": "s", "verification_command": command,
            "artifact_path": None, "evidence_span": [line, line + 1],
            "predicate": predicate, "expected": expected}


def compiled_for(cid="a", flags=None, detail="exit_equals: mechanical grade=False (v1.7)",
                 predicate_ok=False, cwd=".", root="."):
    return {
        "results": [{"claim_id": cid, "predicate_ok": predicate_ok,
                     "detail": detail, "flags": list(flags or []),
                     "cwd": cwd, "artifact_surface": None}],
        "observation_surface": {"command_cwd": cwd or root,
                                "root": root, "workspace": None},
    }


class PreRegisteredClassesTests(unittest.TestCase):
    def test_all_five_classes_are_pre_registered(self):
        self.assertEqual(
            set(shadow_align.OBSERVATION_ERROR_CLASSES),
            {"FILE_NOT_FOUND", "CWD_MISMATCH", "PARSE_FAIL", "TIMEOUT",
             "SILENT_FALLBACK"})

    def test_timeout_is_classified(self):
        c = compiled_for(flags=["observation_failed"],
                         detail="命令无法完成观察: x (timeout after 1s)")
        e = shadow_align.classify_observation_errors([record()], c, Path("."))
        self.assertIn("TIMEOUT", e["a"]["error_classes"])

    def test_regex_timeout_is_classified(self):
        c = compiled_for(flags=["regex_timeout"])
        e = shadow_align.classify_observation_errors([record()], c, Path("."))
        self.assertIn("TIMEOUT", e["a"]["error_classes"])

    def test_parse_fail_is_classified(self):
        c = compiled_for(flags=["parse_fail"], detail="could not parse output")
        e = shadow_align.classify_observation_errors([record()], c, Path("."))
        self.assertIn("PARSE_FAIL", e["a"]["error_classes"])

    def test_schema_invalid_stays_in_its_own_bucket(self):
        c = compiled_for(flags=["schema_invalid"], detail="schema invalid: x")
        e = shadow_align.classify_observation_errors([record()], c, Path("."))
        self.assertEqual(e, {})


class SurfaceFailureTests(unittest.TestCase):
    def _run(self, command, *, artifact_in_root=False, artifact_in_ws=False,
             workspace=False, level="E4", fail_fast_observation=True):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            root = base / "root"
            ws = base / "workspace"
            root.mkdir()
            ws.mkdir()
            for d, flag in ((root, artifact_in_root), (ws, artifact_in_ws)):
                if flag:
                    (d / "artifact.py").write_text("print('ok')\n",
                                                   encoding="utf-8")
            return shadow_align.align(
                {"P901": [main_claim(level, 10)]},
                {"P901": [record(command=command)]},
                root, workspace=ws if workspace else None,
                fail_fast_observation=fail_fast_observation)

    def test_cwd_mismatch_when_artifact_is_root_only(self):
        # E5's gained-3 shape: the tool is visible in the repo root, but the
        # criterion now runs with cwd=workspace.
        r = self._run("python artifact.py", artifact_in_root=True,
                      workspace=True)
        obs = r["observation_errors"]
        self.assertTrue(obs["enabled"])
        self.assertEqual(obs["total"], 1)
        self.assertIn("CWD_MISMATCH", obs["by_claim"]["a"]["error_classes"])
        self.assertIn("SILENT_FALLBACK", obs["by_claim"]["a"]["error_classes"])
        self.assertEqual(r["totals"]["comparable_pairs"], 0)
        self.assertEqual(r["per_product"]["P901"]["observation_error_ids"], ["a"])
        self.assertEqual(obs["class_counts"]["CWD_MISMATCH"], 1)

    def test_file_not_found_on_all_faces(self):
        r = self._run("python artifact.py", workspace=True)
        classes = r["observation_errors"]["by_claim"]["a"]["error_classes"]
        self.assertIn("FILE_NOT_FOUND", classes)
        self.assertIn("SILENT_FALLBACK", classes)
        self.assertEqual(r["totals"]["comparable_pairs"], 0)

    def test_correct_surface_is_not_an_error(self):
        r = self._run("python artifact.py", artifact_in_ws=True,
                      workspace=True)
        self.assertEqual(r["observation_errors"]["total"], 0)
        self.assertEqual(r["totals"]["comparable_pairs"], 1)

    def test_normal_false_predicate_is_not_misclassified(self):
        # no file dependency: a genuine "criterion not supported" must stay
        # in the agreement denominator
        r = self._run("python -c \"import sys;sys.exit(3)\"")
        self.assertEqual(r["observation_errors"]["total"], 0)
        self.assertEqual(r["totals"]["comparable_pairs"], 1)
        self.assertIs(r["per_product"]["P901"]["consistent_flags"]["a"], False)

    def test_legacy_switch_reproduces_historical_denominator(self):
        strict = self._run("python artifact.py", artifact_in_root=True,
                           workspace=True)
        legacy = self._run("python artifact.py", artifact_in_root=True,
                           workspace=True, fail_fast_observation=False)
        self.assertEqual(strict["totals"]["comparable_pairs"], 0)
        self.assertEqual(legacy["totals"]["comparable_pairs"], 1)
        self.assertFalse(legacy["observation_errors"]["enabled"])
        self.assertEqual(legacy["observation_errors"]["total"], 0)

    def test_all_five_classes_reachable_from_one_run(self):
        # One synthetic compiled payload; each record exercises at least one
        # pre-registered class.  `only_in_ws.py` lives on the workspace face
        # but not on the cwd=root face -> CWD_MISMATCH + SILENT_FALLBACK.
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            root = base / "root"
            ws = base / "workspace"
            root.mkdir()
            ws.mkdir()
            (ws / "only_in_ws.py").write_text("print(1)\n", encoding="utf-8")
            recs = [record("t", command="python -c \"pass\""),
                    record("p", command="python -c \"pass\""),
                    record("c", command="python only_in_ws.py"),
                    record("f", command="python nowhere.py")]
            compiled = {"observation_surface": {"command_cwd": str(root)},
                        "results": [
                            {"claim_id": "t", "predicate_ok": False,
                             "flags": ["regex_timeout"],
                             "detail": "grade=False"},
                            {"claim_id": "p", "predicate_ok": False,
                             "flags": ["parse_fail"],
                             "detail": "could not parse"},
                            {"claim_id": "c", "predicate_ok": False,
                             "flags": [], "detail": "grade=False"},
                            {"claim_id": "f", "predicate_ok": False,
                             "flags": [], "detail": "grade=False"},
                        ]}
            errs = shadow_align.classify_observation_errors(
                recs, compiled, root, workspace=ws)
            self.assertIn("TIMEOUT", errs["t"]["error_classes"])
            self.assertIn("PARSE_FAIL", errs["p"]["error_classes"])
            self.assertIn("CWD_MISMATCH", errs["c"]["error_classes"])
            self.assertIn("SILENT_FALLBACK", errs["c"]["error_classes"])
            self.assertIn("FILE_NOT_FOUND", errs["f"]["error_classes"])
            reached = {c for e in errs.values() for c in e["error_classes"]}
            self.assertEqual(reached,
                             set(shadow_align.OBSERVATION_ERROR_CLASSES))


class IsolationTests(unittest.TestCase):
    def test_e7_output_stays_level_token_free(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "x.py").write_text("print(1)\n", encoding="utf-8")
            r = shadow_align.align(
                {"P901": [main_claim("E4", 10)]},
                {"P901": [record(command="python absent.py")]}, root)
        payload = json.dumps(r)
        self.assertNotIn('"E4"', payload)
        self.assertNotIn('"level"', payload)
        self.assertNotIn("verdict", payload)
        self.assertIn("observation_errors", r)

    def test_compile_report_carries_error_counts(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            root = base / "root"
            ws = base / "workspace"
            root.mkdir()
            ws.mkdir()
            (ws / "artifact.py").write_text("print(1)\n", encoding="utf-8")
            r = shadow_align.align(
                {"P901": [main_claim("E4", 10)]},
                {"P901": [record(command="python artifact.py")]},
                root, workspace=None)
            out = base / "compile-report.json"
            payload = shadow_align.write_compile_report(out, r, [record()])
            self.assertIn("error_class_counts", payload)
            self.assertTrue(payload["fail_fast_observation"])
            self.assertEqual(
                json.loads(out.read_text(encoding="utf-8"))["error_class_counts"],
                payload["error_class_counts"])


if __name__ == "__main__":
    unittest.main()
