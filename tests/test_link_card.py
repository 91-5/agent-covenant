#!/usr/bin/env python3
"""Tests for tools/link_card.py - stdlib unittest only, no third-party deps.

Run from the repository root:
    python -m unittest discover -s tests -v

The exit code is asserted from `subprocess.returncode` directly, never through a
pipe: on Windows a piped exit code is what the *pipe* returned, not the child's
(see the deepfreeze repo's AGENTS.md note on the lost-exit-code trap). In-process
`main()` returns would hide a real CLI regression, so the CLI is exercised as a
subprocess end to end.
"""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL = REPO_ROOT / "tools" / "link_card.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("link_card", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


link_card = _load_module()


def _run(*args):
    """Run the CLI and return (returncode, stdout, stderr). No pipe for the code."""
    proc = subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return proc.returncode, proc.stdout, proc.stderr


def _write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class LinkCardTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.freeze = self.root / ".freeze"
        self.freeze.mkdir()
        self.card = "DFB-20261019-001"
        self.link_path = self.freeze / f"link-{self.card}.json"

    def tearDown(self):
        self._tmp.cleanup()

    # -- helpers -----------------------------------------------------------
    def _snap_link(self):
        """A link as deepfreeze would write it: the snap group only."""
        return {
            "card": self.card,
            "snap_ts": "2026-10-19T07:00:00Z",
            "snap_path": "snap-20261019-070000",
            "snapshot_root": ".freeze-snap",
            "source": "deepfreeze",
            "created_at": "2026-10-19T07:00:01Z",
        }

    def _write_link(self, data):
        _write_json(self.link_path, data)

    def _write_verdict(self, **overrides):
        verdict = {
            "id": self.card,
            "verdict": "PASS",
            "verifier": "agnes-code",
            "ts": "2026-10-19T07:30:00Z",
        }
        verdict.update(overrides)
        path = self.root / "verdict.json"
        _write_json(path, verdict)
        return path

    def _read_link(self):
        return json.loads(self.link_path.read_text(encoding="utf-8"))

    # -- forward -----------------------------------------------------------
    def test_forward_write_back_preserves_snap_and_sets_verdict_group(self):
        snap = self._snap_link()
        self._write_link(snap)
        verdict = self._write_verdict()

        code, out, err = _run("--card", self.card, "--verdict", str(verdict),
                              "--freeze-dir", str(self.freeze))

        self.assertEqual(code, 0, err)
        linked = self._read_link()
        # Snap group survives byte-for-byte (value-for-value).
        for key, value in snap.items():
            self.assertEqual(linked[key], value, f"snap field {key} changed")
        # Verdict group is correct.
        self.assertEqual(linked["verdict_ts"], "2026-10-19T07:30:00Z")
        expected_sha = hashlib.sha256(verdict.read_bytes()).hexdigest()
        self.assertEqual(linked["verdict_sha256"], expected_sha)
        self.assertEqual(linked["verifier"], "agnes-code")
        # updated_at is ISO-8601 with a trailing Z.
        self.assertTrue(linked["updated_at"].endswith("Z"), linked["updated_at"])
        self.assertIn("snap_ts=2026-10-19T07:00:00Z", out)
        self.assertIn("verdict_ts=2026-10-19T07:30:00Z", out)

    def test_forward_repeat_write_overwrites_verdict_group_only(self):
        snap = self._snap_link()
        self._write_link(snap)
        first = self._write_verdict(ts="2026-10-19T07:30:00Z", verifier="agnes-code")
        code, _, err = _run("--card", self.card, "--verdict", str(first),
                            "--freeze-dir", str(self.freeze))
        self.assertEqual(code, 0, err)

        # A rework produces a new verdict; re-run overwrites the verdict group.
        second = self._write_verdict(ts="2026-10-19T09:00:00Z", verifier="zcode")
        code, _, err = _run("--card", self.card, "--verdict", str(second),
                            "--freeze-dir", str(self.freeze))
        self.assertEqual(code, 0, err)

        linked = self._read_link()
        self.assertEqual(linked["verdict_ts"], "2026-10-19T09:00:00Z")
        self.assertEqual(linked["verifier"], "zcode")
        self.assertEqual(linked["verdict_sha256"],
                         hashlib.sha256(second.read_bytes()).hexdigest())
        # Snap group untouched.
        for key, value in snap.items():
            self.assertEqual(linked[key], value, f"snap field {key} changed on re-run")

    # -- reverse -----------------------------------------------------------
    def test_reverse_missing_link_errors_with_hint_and_creates_nothing(self):
        verdict = self._write_verdict()
        before = sorted(p.name for p in self.freeze.iterdir())

        code, out, err = _run("--card", self.card, "--verdict", str(verdict),
                              "--freeze-dir", str(self.freeze))

        self.assertEqual(code, 1)
        self.assertIn("protect --card", err)
        self.assertIn(self.card, err)
        after = sorted(p.name for p in self.freeze.iterdir())
        self.assertEqual(before, after, "no file should have been created")

    def test_reverse_corrupt_link_is_left_untouched(self):
        self.link_path.write_bytes(b'{"card": "DFB-20261019-001", "snap_ts":')  # half JSON
        original = self.link_path.read_bytes()
        verdict = self._write_verdict()

        code, out, err = _run("--card", self.card, "--verdict", str(verdict),
                              "--freeze-dir", str(self.freeze))

        self.assertEqual(code, 1)
        self.assertIn("refusing to overwrite", err)
        self.assertEqual(self.link_path.read_bytes(), original,
                         "a corrupt link must not be rewritten")

    def test_reverse_verdict_id_mismatch_leaves_link_unchanged(self):
        snap = self._snap_link()
        self._write_link(snap)
        original = self.link_path.read_bytes()
        verdict = self._write_verdict(id="XJ-20261019-999")

        code, out, err = _run("--card", self.card, "--verdict", str(verdict),
                              "--freeze-dir", str(self.freeze))

        self.assertEqual(code, 1)
        self.assertIn("does not match", err)
        self.assertEqual(self.link_path.read_bytes(), original)

    def test_reverse_corrupt_verdict_errors(self):
        self._write_link(self._snap_link())
        bad = self.root / "verdict.json"
        bad.write_text("{not json", encoding="utf-8")

        code, out, err = _run("--card", self.card, "--verdict", str(bad),
                              "--freeze-dir", str(self.freeze))

        self.assertEqual(code, 1)
        self.assertIn("unreadable verdict", err)

    def test_reverse_card_path_injection_has_zero_side_effects(self):
        self._write_link(self._snap_link())
        verdict = self._write_verdict()
        before_freeze = sorted(p.name for p in self.freeze.iterdir())
        before_root = sorted(p.name for p in self.root.iterdir())

        for evil in ("../evil", "a/b", "..\\..\\x", ""):
            code, out, err = _run("--card", evil, "--verdict", str(verdict),
                                  "--freeze-dir", str(self.freeze))
            self.assertEqual(code, 1, f"{evil!r} should be rejected: {err}")
            self.assertIn("unsafe --card", err)

        self.assertEqual(sorted(p.name for p in self.freeze.iterdir()), before_freeze)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), before_root,
                         "path injection must not create files anywhere")

    def test_reverse_verdict_without_verifier_writes_no_verifier_key(self):
        self._write_link(self._snap_link())
        verdict = self._write_verdict()
        data = json.loads(verdict.read_text(encoding="utf-8"))
        del data["verifier"]
        _write_json(verdict, data)

        code, out, err = _run("--card", self.card, "--verdict", str(verdict),
                              "--freeze-dir", str(self.freeze))

        self.assertEqual(code, 0, err)
        linked = self._read_link()
        self.assertNotIn("verifier", linked)

    # -- edge --------------------------------------------------------------
    def test_edge_unicode_verifier_round_trips(self):
        self._write_link(self._snap_link())
        name = "浮香-评审员"
        verdict = self._write_verdict(verifier=name)

        code, out, err = _run("--card", self.card, "--verdict", str(verdict),
                              "--freeze-dir", str(self.freeze))

        self.assertEqual(code, 0, err)
        linked = self._read_link()
        self.assertEqual(linked["verifier"], name)
        # Raw bytes on disk are real UTF-8, not escaped ASCII.
        self.assertIn(name.encode("utf-8"), self.link_path.read_bytes())

    def test_edge_missing_freeze_dir_is_actionable_not_a_traceback(self):
        verdict = self._write_verdict()
        missing = self.root / "nope"

        code, out, err = _run("--card", self.card, "--verdict", str(verdict),
                              "--freeze-dir", str(missing))

        self.assertEqual(code, 1)
        self.assertIn("freeze directory not found", err)
        self.assertNotIn("Traceback", err)


if __name__ == "__main__":
    unittest.main()
