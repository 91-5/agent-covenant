#!/usr/bin/env python3
"""Tests for tools/pre-push-hook.sh and tools/install-hooks.sh.

All tests run inside temporary git repositories; the real .git/hooks/
directory is never touched.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_SRC = REPO_ROOT / "tools" / "pre-push-hook.sh"
INSTALL_SRC = REPO_ROOT / "tools" / "install-hooks.sh"

HOOK_STDIN_BRANCH = f"refs/heads/main {'0' * 40} refs/heads/main {'0' * 40}\n"
HOOK_STDIN_TAG = "refs/tags/v1.0 0000000000000000000000000000000000000000 refs/tags/v1.0\n"
HOOK_STDIN_DELETE = f"refs/heads/main {'0' * 40} refs/heads/topic {'0' * 40}\n"


def run_hook(repo: Path, stdin_data: str) -> subprocess.CompletedProcess:
    """Run the pre-push hook inside *repo*, feeding *stdin_data* to stdin."""
    return subprocess.run(
        ["bash", str(HOOK_SRC)],
        input=stdin_data,
        capture_output=True,
        text=True,
        cwd=str(repo),
    )


class PrePushHookTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        subprocess.run(["git", "init", "-b", "main"], capture_output=True, cwd=self.repo)
        subprocess.run(
            ["git", "config", "user.email", "test@local"], capture_output=True, cwd=self.repo
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"], capture_output=True, cwd=self.repo
        )
        # Seed a commit so git rev-parse works.
        (self.repo / "README.md").write_text("test", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], capture_output=True, cwd=self.repo)
        subprocess.run(
            ["git", "commit", "-m", "init"], capture_output=True, cwd=self.repo
        )
        # Seed a minimal artifacts.json and verdict so the hook has something to read.
        artifacts = {"XJ-20261008-001": ["README.md"]}
        (self.repo / "artifacts.json").write_text(
            json.dumps(artifacts), encoding="utf-8"
        )
        # A minimal PASS verdict for XJ-20261008-001.
        verdict = {
            "id": "XJ-20261008-001",
            "artifact": "README.md",
            "verdict": "PASS",
            "blockers": 0,
            "conditions": [],
            "independent": True,
            "verifier": "reviewer@local",
            "ts": "2026-10-08T10:00:00Z",
            "evidence": ["git init -> success"],
        }
        (self.repo / "verdicts").mkdir(exist_ok=True)
        (self.repo / "verdicts" / "XJ-20261008-001.verdict.json").write_text(
            json.dumps(verdict), encoding="utf-8"
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_branch_push_passes_when_gate_is_green(self):
        """A branch push with a PASS verdict and clean lint exits 0."""
        result = run_hook(self.repo, HOOK_STDIN_BRANCH)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_branch_push_blocked_when_verdict_missing(self):
        """A branch push with no verdict file for the required id exits non-zero."""
        (self.repo / "verdicts" / "XJ-20261008-001.verdict.json").unlink()
        result = run_hook(self.repo, HOOK_STDIN_BRANCH)
        self.assertNotEqual(result.returncode, 0)

    def test_branch_push_blocked_on_lint_error(self):
        """A branch push with a schema violation (unblocks missing) exits non-zero."""
        bad = {
            "id": "XJ-20261013-001",
            "verdict": "PASS",
            "blockers": 0,
            "conditions": [],
            "independent": True,
            "verifier": "author@local",
            "ts": "2026-10-13T10:00:00Z",
            "evidence": ["x"],
            "unblocks": ["NONEXISTENT"],
        }
        (self.repo / "verdicts" / "XJ-20261013-001.verdict.json").write_text(
            json.dumps(bad), encoding="utf-8"
        )
        # The hook should try to lint this new verdict and fail.
        result = run_hook(self.repo, HOOK_STDIN_BRANCH)
        self.assertNotEqual(result.returncode, 0)

    def test_tag_push_bypasses_gate(self):
        """A tag push exits 0 regardless of verdict state."""
        (self.repo / "verdicts" / "XJ-20261008-001.verdict.json").unlink()
        result = run_hook(self.repo, HOOK_STDIN_TAG)
        self.assertEqual(result.returncode, 0)

    def test_delete_push_bypasses_gate(self):
        """A branch delete push exits 0 regardless of verdict state."""
        (self.repo / "verdicts" / "XJ-20261008-001.verdict.json").unlink()
        result = run_hook(self.repo, HOOK_STDIN_DELETE)
        self.assertEqual(result.returncode, 0)

    def test_empty_stdin_passes(self):
        """Empty stdin (nothing to push) exits 0."""
        result = run_hook(self.repo, "")
        self.assertEqual(result.returncode, 0)


class InstallHooksTestCase(unittest.TestCase):
    """Tests for tools/install-hooks.sh idempotency and backup behaviour."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        subprocess.run(["git", "init", "-b", "main"], capture_output=True, cwd=self.repo)
        subprocess.run(
            ["git", "config", "user.email", "test@local"], capture_output=True, cwd=self.repo
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"], capture_output=True, cwd=self.repo
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_install_creates_hook(self):
        """First run creates .git/hooks/pre-push and makes it executable."""
        result = subprocess.run(
            ["bash", str(INSTALL_SRC)],
            capture_output=True,
            text=True,
            cwd=self.repo,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        hook = self.repo / ".git" / "hooks" / "pre-push"
        self.assertTrue(hook.exists())
        self.assertTrue(hook.stat().st_mode & 0o110)  # owner-executable

    def test_install_is_idempotent(self):
        """Second run does not overwrite or error."""
        r1 = subprocess.run(
            ["bash", str(INSTALL_SRC)],
            capture_output=True,            text=True,
            cwd=self.repo,
        )
        r2 = subprocess.run(
            ["bash", str(INSTALL_SRC)],
            capture_output=True,
            text=True,
            cwd=self.repo,
        )
        self.assertEqual(r1.returncode, 0)
        self.assertEqual(r2.returncode, 0)

    def test_install_backs_up_existing_hook(self):
        """If a pre-push already exists with different content, it gets backed up."""
        hooks_dir = self.repo / ".git" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        existing = hooks_dir / "pre-push"
        existing.write_text("#!/bin/sh\necho custom\n", encoding="utf-8")
        result = subprocess.run(
            ["bash", str(INSTALL_SRC)],
            capture_output=True,
            text=True,
            cwd=self.repo,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        backups = list(hooks_dir.glob("pre-push.bak.*"))
        self.assertEqual(len(backups), 1)
        self.assertIn("custom", backups[0].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
