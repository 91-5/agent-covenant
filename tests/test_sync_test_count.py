#!/usr/bin/env python3
"""Tests for tools/sync_test_count.py — stdlib unittest only.

Run from the repository root:
    python -m unittest discover -s tests -v

The properties worth protecting here are the ones that make the tool honest:
it must refuse to claim success while changing nothing (a missing anchor is an
error, not a no-op), it must be idempotent, and it must not touch anything
outside the markers it owns.
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


sync = _load("sync_test_count")


ANCHORED = "cmd            # <!-- test-count -->12<!-- /test-count --> tests\n"


class SyncFileTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _write(self, text):
        path = self.root / "README.md"
        path.write_text(text, encoding="utf-8")
        return path

    def test_updates_anchor_to_count(self):
        path = self._write(ANCHORED)
        changed, error = sync.sync_file(path, 42)
        self.assertTrue(changed)
        self.assertIsNone(error)
        self.assertIn("<!-- test-count -->42<!-- /test-count -->", path.read_text(encoding="utf-8"))

    def test_idempotent_second_run_changes_nothing(self):
        path = self._write(ANCHORED)
        sync.sync_file(path, 42)
        first = path.read_text(encoding="utf-8")
        changed, _ = sync.sync_file(path, 42)
        self.assertFalse(changed)
        self.assertEqual(path.read_text(encoding="utf-8"), first)

    def test_missing_anchor_is_an_error_not_a_silent_noop(self):
        """A tool that reports OK while changing nothing is the defect class
        this whole exercise exists to prevent."""
        path = self._write("cmd            # 12 tests\n")
        changed, error = sync.sync_file(path, 42)
        self.assertFalse(changed)
        self.assertIsNotNone(error)
        self.assertIn("no", error)

    def test_missing_file_is_an_error(self):
        changed, error = sync.sync_file(self.root / "nope.md", 42)
        self.assertFalse(changed)
        self.assertIn("missing file", error)

    def test_check_mode_reports_without_writing(self):
        path = self._write(ANCHORED)
        changed, error = sync.sync_file(path, 42, write=False)
        self.assertTrue(changed)
        self.assertIsNone(error)
        self.assertIn("-->12<!--", path.read_text(encoding="utf-8"))  # untouched

    def test_multiple_anchors_all_updated(self):
        path = self._write(ANCHORED + ANCHORED)
        sync.sync_file(path, 7)
        text = path.read_text(encoding="utf-8")
        self.assertEqual(text.count("<!-- test-count -->7<!-- /test-count -->"), 2)

    def test_text_outside_markers_is_untouched(self):
        """Numbers elsewhere in the file are not ours to rewrite."""
        body = "version 3 release\n" + ANCHORED + "see 12 tests above\n"
        path = self._write(body)
        sync.sync_file(path, 42)
        text = path.read_text(encoding="utf-8")
        self.assertIn("version 3 release", text)
        self.assertIn("see 12 tests above", text)

    def test_spacing_variants_of_the_anchor_are_recognised(self):
        path = self._write("x <!--test-count-->12<!--/test-count--> y\n")
        changed, error = sync.sync_file(path, 5)
        self.assertTrue(changed)
        self.assertIsNone(error)
        self.assertIn("<!--test-count-->5<!--/test-count-->", path.read_text(encoding="utf-8"))


class RealCountTests(unittest.TestCase):
    def test_real_count_matches_this_suite(self):
        """The script's count must come from unittest, not from grep."""
        linter = sync._load_linter()
        count, failed = linter._discover_test_count(REPO_ROOT)
        self.assertFalse(failed)
        self.assertEqual(count, sync.real_test_count(linter))

    def test_check_mode_on_the_real_repo_is_clean(self):
        """The shipped READMEs must be in sync at the time of commit.

        This test is deliberately self-referential and will fail the moment a
        new test is added without running `tools/sync_test_count.py` -- because
        adding *this* file changed the count. That is the intended pressure: the
        alternative is prose that silently rots (the 141->166->168 cycle this
        tool exists to end). The fix when it fires is one command, not an edit:

            python tools/sync_test_count.py

        It is asserted through `main(["--check"])` so the failure message is the
        tool's own drift report, which names the file and the correct number.
        """
        out = io.StringIO()
        with redirect_stdout(out):
            code = sync.main(["--check"])
        self.assertEqual(code, sync.EXIT_OK, out.getvalue())

    def test_json_payload_shape(self):
        out = io.StringIO()
        with redirect_stdout(out):
            sync.main(["--check", "--json"])
        payload = json.loads(out.getvalue())
        self.assertTrue(payload["ok"])
        self.assertIsInstance(payload["count"], int)
        self.assertEqual({item["file"] for item in payload["files"]},
                         {"README.md", "README.zh-CN.md"})


if __name__ == "__main__":
    unittest.main()