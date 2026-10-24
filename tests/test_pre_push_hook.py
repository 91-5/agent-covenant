#!/usr/bin/env python3
"""Tests for tools/pre-push-hook.sh and tools/install-hooks.sh.

Every test runs the scripts against a throwaway git repository created under the
system temp directory. The real repository's ``.git/hooks/`` is never written to,
and ``RealHooksUntouchedTestCase`` enforces that as an assertion rather than a
promise: an earlier version of ``install-hooks.sh`` resolved the target repo from
its own file location instead of the working directory, so running this suite
installed a hook (and two ``.bak`` copies) into the real repository's hooks
directory. Three tests in this file passed for the wrong reason because of the
same bug -- the hook looked for ``tools/lint_cards.py`` in a temp repo that had
none, so every push was blocked no matter what the fixture claimed.
"""
# Runtime-evaluated `X | Y` annotations in this file (the hook-test helpers)
# are a TypeError on Python 3.9 -- which is exactly what CI runs. Deferring
# annotation evaluation keeps the 3.9 gate green without rewriting them.
from __future__ import annotations

import json
import os
import hashlib
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_SRC = REPO_ROOT / "tools" / "pre-push-hook.sh"
INSTALL_SRC = REPO_ROOT / "tools" / "install-hooks.sh"
REAL_HOOKS = REPO_ROOT / ".git" / "hooks"


def _find_bash() -> str:
    """Return a POSIX bash that accepts Windows paths -- never a bare "bash".

    A bare ``bash`` resolves through PATH, and on 2026-10-20 a WSL install
    registered ``%LOCALAPPDATA%\\Microsoft\\WindowsApps\\bash.exe`` (an
    app-execution alias to the WSL launcher) *ahead* of Git for Windows.
    WSL bash does no Windows-drive translation, so the hook path arrived as
    ``D:15812projects...`` (backslashes eaten as escapes) and every call
    exited 127. Git itself runs hooks with its bundled sh and never consults
    PATH, so production hooks were never affected -- only these tests.

    Locking the Git for Windows bash restores the environment this suite was
    written against instead of skipping anything: the assertions stay exactly
    as strict. Resolution order:
    1. ``COVENANT_BASH_HINT`` env var — an absolute path to bash.exe. The
       pre-push hook exports it (``cygpath -w`` of its own bash) because a
       python spawned as a Git-bash child can be blind to Windows PATH
       entries: ``shutil.which("git")`` returns None there, the install root
       may be ``D:\\AI\\Git`` (not Program Files), and PATH entries arrive
       POSIX-style. The hook knows its own bash reliably; this suite does not.
    2. ``shutil.which("git")`` sibling ``bin/bash.exe`` (PowerShell-spawned
       runs, where the Windows PATH is intact).
    3. The two standard Windows install roots.
    No silent fallback to the bare name -- if none is found the suite must
    fail loudly rather than drift back to WSL.
    """
    hint = os.environ.get("COVENANT_BASH_HINT")
    if hint and Path(hint).is_file():
        return str(Path(hint))

    git = shutil.which("git")
    if git:
        candidate = Path(git).resolve().parent.parent / "bin" / "bash.exe"
        if candidate.is_file():
            return str(candidate)
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
    ):
        if Path(candidate).is_file():
            return candidate
    raise RuntimeError(
        "no Git for Windows bash found; refusing to fall back to a bare "
        "'bash' (a WSL alias would swallow Windows paths, ENV-1). If bash "
        "exists, set COVENANT_BASH_HINT to its absolute path."
    )


if os.name == "posix":
    # POSIX: bare bash is the correct, drift-free resolution here. The
    # Windows lookup below would raise at import time on Linux CI (no
    # bin/bash.exe sibling, no C:\Program Files roots), which is exactly
    # the cross-platform regression the retroactive review caught (C1 of
    # XJ-20261020-001). The WSL-alias trap does not exist on POSIX.
    BASH = shutil.which("bash") or "bash"
else:
    BASH = _find_bash()

CARD_ID = "XJ-20261008-001"
# A second round that is *not* the newest one. Step 2 only gates the newest id,
# so only this card can show the step-3 sweep doing work step 2 would not do.
OLD_ID = "XJ-20261007-002"
SHA = "a" * 40
HOOK_STDIN_BRANCH = f"refs/heads/main {SHA} refs/heads/main {SHA}\n"
HOOK_STDIN_TAG = f"refs/tags/v1.0 {SHA} refs/tags/v1.0\n"
HOOK_STDIN_DELETE = f"refs/heads/main {'0' * 40} refs/heads/topic {'0' * 40}\n"

CARD_TEXT = f"""# TASK {CARD_ID}: fixture card for the pre-push hook test

- **Author:** test@local
- **Created:** 2026-10-08
- **Gated by:** `verdicts/{CARD_ID}.verdict.json`

## Context

Seeded by `tests/test_pre_push_hook.py` so the hook has a real card to lint and a
real round to gate. Nothing here is under review; the round only has to be
shaped like one.

## Deliverables

- `README.md` �?the fixture's claim surface

## Owned files

- `README.md`

## Constraints

- none; this is test scaffolding

## Acceptance

- [x] `python tools/lint_cards.py --dir .tasks --verdict-dir verdicts --strict` exits 0

## Review questions

- Is the fixture shaped like a round the gate would actually sign?

## Status

IN_REVIEW
"""


def _card_text(card_id: str) -> str:
    """A minimal lint-clean card for *card_id* (same shape as CARD_TEXT)."""
    return (
        f"# TASK {card_id}: fixture card for the pre-push hook test\n\n"
        "- **Author:** test@local\n"
        "- **Created:** 2026-10-07\n"
        f"- **Gated by:** `verdicts/{card_id}.verdict.json`\n\n"
        "## Context\n\n"
        "Seeded by `tests/test_pre_push_hook.py` as an already-landed round, so a\n"
        "link can drift off the newest one and only the sweep can see it.\n\n"
        "## Deliverables\n\n"
        "- `README.md` — the fixture's claim surface\n\n"
        "## Owned files\n\n"
        "- `README.md`\n\n"
        "## Constraints\n\n"
        "- none; this is test scaffolding\n\n"
        "## Acceptance\n\n"
        "- [x] `python tools/lint_cards.py --dir .tasks --verdict-dir verdicts --strict` exits 0\n\n"
        "## Review questions\n\n"
        "- Is the fixture shaped like a round the gate would actually sign?\n\n"
        "## Status\n\n"
        "IN_REVIEW\n"
    )


def _snap_ts() -> str:
    """deepfreeze's compact local stamp (YYYYMMDD-HHMMSS)."""
    return datetime.now().strftime("%Y%m%d-%H%M%S")



def _now() -> str:
    # Microseconds are kept on purpose: the freshness check compares this
    # timestamp against README.md's mtime, and truncating to whole seconds
    # lands the verdict *before* the file it judges.
    return datetime.now(timezone.utc).isoformat()


def _popen(cmd, **kw):
    """subprocess.run with the decoding this machine needs.

    The default locale codec here is GBK, while the hook and the two tools it runs
    emit UTF-8 (em dashes, the checks' own diagnostics). ``text=True`` without an
    explicit encoding kills subprocess's reader thread mid-capture and hands the
    test a truncated result with a meaningless returncode -- which is how a green
    fixture once reported rc=49. Do not drop these two kwargs.
    """
    kw.setdefault("capture_output", True)
    kw.setdefault("encoding", "utf-8")
    kw.setdefault("errors", "replace")
    return subprocess.run(cmd, **kw)


def run_hook(repo: Path, stdin_data: str, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run the pre-push hook with *repo* as the working directory.

    ``env`` is merged over the inherited environment; the link sweep's skip
    switch (`DEEPFREEZE_SKIP_LINK_CHECK`) is read from it.
    """
    return _popen(
        [BASH, str(HOOK_SRC)],
        input=stdin_data,
        capture_output=True,
        text=True,
        cwd=str(repo),
        env={**os.environ, **env} if env else None,
    )


class SeededRepoMixin:
    """Builds a temp git repo that looks enough like agent-covenant to lint."""

    def _git_init(self, repo: Path) -> None:
        _popen(["git", "init", "-b", "main"], capture_output=True, cwd=repo, check=True)
        _popen(["git", "config", "user.email", "test@local"], capture_output=True, cwd=repo)
        _popen(["git", "config", "user.name", "Test"], capture_output=True, cwd=repo)

    def _seed_round(self, repo: Path, verdict_overrides: dict | None = None) -> Path:
        """Write the minimal round the hook needs: claim surface, card, tools, verdict.

        ``tools/lint_cards.py`` and ``tools/gate.py`` are copied in because the
        hook invokes them by repo-relative path. Both are stdlib-only, so nothing
        else has to travel with them.

        The card is parked in ``.tasks/legacy/`` on purpose. ``lint_cards.py``
        makes ``--strict`` structurally unsatisfiable for a card that sits in
        ``.tasks/``: an open card with a PASS verdict draws STATUS_DRIFT, a closed
        one draws CLOSED_NOT_ARCHIVED, and no card at all draws ORPHAN_VERDICT.
        A parked card is evidence that is still paired with its verdict but is not
        linted, which is the only warning-free shape -- and it is the shape a real
        repo reaches once a round is archived. Without it the green-path test
        could only ever be red, and a red green-path test teaches nothing.
        """
        (repo / "README.md").write_text("fixture\n", encoding="utf-8")
        (repo / "tools").mkdir()
        for tool in ("lint_cards.py", "gate.py"):
            shutil.copy2(REPO_ROOT / "tools" / tool, repo / "tools" / tool)
        (repo / ".tasks" / "legacy").mkdir(parents=True)
        (repo / ".tasks" / "legacy" / f"{CARD_ID}.md").write_text(CARD_TEXT, encoding="utf-8")
        (repo / "artifacts.json").write_text(
            json.dumps({CARD_ID: ["README.md"]}), encoding="utf-8"
        )
        verdict = {
            "id": CARD_ID,
            "artifact": "README.md",
            "verdict": "PASS",
            "blockers": 0,
            "conditions": [],
            "independent": True,
            "verifier": "reviewer@local",
            # Freshness is judged against the mapped artifact's mtime, so this has
            # to be written after README.md -- which is why it is not a constant.
            "ts": _now(),
            "evidence": ["git init -> success"],
        }
        if verdict_overrides:
            verdict.update(verdict_overrides)
        (repo / "verdicts").mkdir()
        (repo / "verdicts" / f"{CARD_ID}.verdict.json").write_text(
            json.dumps(verdict), encoding="utf-8"
        )
        return repo / "verdicts" / f"{CARD_ID}.verdict.json"

    def _commit_all(self, repo: Path) -> None:
        _popen(["git", "add", "-A"], capture_output=True, cwd=repo)
        _popen(["git", "commit", "-m", "seed"], capture_output=True, cwd=repo)

    def _seed_older_round(self, repo: Path) -> Path:
        """Add an already-landed round that is *not* the newest id.

        artifacts.json keeps insertion order and the hook gates the last
        non-underscore key, so this entry goes first: CARD_ID must stay the
        newest round or step 2 would gate the old one and the sweep test would
        stop testing the sweep.
        """
        (repo / ".tasks" / "legacy" / f"{OLD_ID}.md").write_text(
            _card_text(OLD_ID), encoding="utf-8"
        )
        verdict = {
            "id": OLD_ID,
            "artifact": "README.md",
            "verdict": "PASS",
            "blockers": 0,
            "conditions": [],
            "independent": True,
            "verifier": "reviewer@local",
            "ts": _now(),
            "evidence": ["git init -> success"],
        }
        verdict_path = repo / "verdicts" / f"{OLD_ID}.verdict.json"
        verdict_path.write_text(json.dumps(verdict), encoding="utf-8")
        map_path = repo / "artifacts.json"
        current = json.loads(map_path.read_text(encoding="utf-8"))
        rebuilt = {OLD_ID: ["README.md"], **{k: v for k, v in current.items() if k != OLD_ID}}
        map_path.write_text(json.dumps(rebuilt), encoding="utf-8")
        return verdict_path

    def _seed_link(self, repo: Path, card_id: str = CARD_ID,
                   verdict_sha: str | None = None) -> Path:
        """Write `.freeze/link-<id>.json` plus the manifest it points at.

        ``verdict_sha`` overrides the digest, reproducing the drift this step
        exists to catch: the verdict was re-signed (its bytes changed) and
        `link_card.py` was not re-run, so the link still carries the old hash.

        The snapshot manifest has to exist even though this test only exercises
        the sha rule -- `check_links()` also blocks a link pointing at a snapshot
        the checkout cannot show, and a fixture that tripped that rule would be
        testing the wrong finding.
        """
        freeze = repo / ".freeze"
        (freeze / "manifests").mkdir(parents=True, exist_ok=True)
        snap_ts = _snap_ts()
        (freeze / "manifests" / f"{snap_ts}.json").write_text("{}", encoding="utf-8")
        verdict_path = repo / "verdicts" / f"{card_id}.verdict.json"
        digest = hashlib.sha256(verdict_path.read_bytes()).hexdigest()
        link = {
            "card": card_id,
            "snap_ts": snap_ts,
            "snap_path": f".freeze-snap/snap-{snap_ts}",
            "snapshot_root": ".freeze-snap",
            "source": str(repo),
            "created_at": _now(),
            "verdict_ts": _now(),
            "verdict_sha256": digest if verdict_sha is None else verdict_sha,
            "verifier": "reviewer@local",
            "updated_at": _now(),
        }
        link_path = freeze / f"link-{card_id}.json"
        link_path.write_text(json.dumps(link), encoding="utf-8")
        return link_path


class PrePushHookTestCase(unittest.TestCase, SeededRepoMixin):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name)
        self._git_init(self.repo)
        self._seed_round(self.repo)

    def test_branch_push_passes_when_gate_is_green(self):
        """A branch push with a PASS verdict and clean lint exits 0."""
        result = run_hook(self.repo, HOOK_STDIN_BRANCH)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[pre-push] OK", result.stdout)

    def test_link_whose_sha_matches_passes(self):
        """A link that matches its verdict bytes is not a finding."""
        self._seed_link(self.repo)

        result = run_hook(self.repo, HOOK_STDIN_BRANCH)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("LINKS: PASS", result.stdout)
        self.assertIn("[pre-push] OK", result.stdout)

    def test_blocked_when_verdict_was_resigned_without_refreshing_link(self):
        """A stale verdict_sha256 on an older round blocks the push (step 3).

        The link belongs to a round that is not the newest, so step 2 never reads
        it: if this test passes it is the sweep that caught the drift, not the
        gate it already runs.
        """
        self._seed_older_round(self.repo)
        self._seed_link(self.repo, card_id=OLD_ID, verdict_sha="0" * 64)

        result = run_hook(self.repo, HOOK_STDIN_BRANCH)
        output = result.stdout + result.stderr

        self.assertNotEqual(result.returncode, 0, output)
        self.assertIn("LINK_VERDICT_SHA_MISMATCH", output)
        self.assertIn("tools/link_card.py --card <id>", output)
        self.assertIn(f"LINK_VERDICT_SHA_MISMATCH] {OLD_ID}", output)

    def test_no_freeze_directory_is_not_a_finding(self):
        """A checkout with no .freeze has nothing to sweep and pushes normally."""
        self.assertFalse((self.repo / ".freeze").exists())

        result = run_hook(self.repo, HOOK_STDIN_BRANCH)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("link sweep skipped", result.stdout)
        self.assertIn("[pre-push] OK", result.stdout)

    def test_skip_switch_bypasses_only_the_link_sweep(self):
        """DEEPFREEZE_SKIP_LINK_CHECK=1 lets a known-stale link through."""
        self._seed_older_round(self.repo)
        self._seed_link(self.repo, card_id=OLD_ID, verdict_sha="0" * 64)

        result = run_hook(self.repo, HOOK_STDIN_BRANCH,
                          env={"DEEPFREEZE_SKIP_LINK_CHECK": "1"})
        output = result.stdout + result.stderr

        self.assertEqual(result.returncode, 0, output)
        self.assertIn("SKIP link sweep", result.stdout)
        self.assertNotIn("LINK_VERDICT_SHA_MISMATCH", output)

    def test_branch_push_blocked_when_verdict_missing(self):
        """No verdict for the newest round blocks the push."""
        (self.repo / "verdicts" / f"{CARD_ID}.verdict.json").unlink()
        result = run_hook(self.repo, HOOK_STDIN_BRANCH)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BLOCKED", result.stdout + result.stderr)

    def test_branch_push_blocked_on_conditional_verdict(self):
        """A CONDITIONAL verdict the gate has not acknowledged blocks the push."""
        verdict_path = self.repo / "verdicts" / f"{CARD_ID}.verdict.json"
        verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
        verdict["verdict"] = "CONDITIONAL"
        verdict["conditions"] = ["C1: not yet satisfied"]
        verdict_path.write_text(json.dumps(verdict), encoding="utf-8")
        result = run_hook(self.repo, HOOK_STDIN_BRANCH)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BLOCKED", result.stdout + result.stderr)

    def _break_gate_only(self) -> None:
        """Make the newest round fail gate step 2 while lint step 1 stays green.

        Two rounds: an older PASS round whose artifact-map entry retires the
        claim-surface staleness for README.md (lint green), plus the newest
        round flipped to FAIL (schema-valid; gate rejects it). Every
        single-round shortcut trips lint first and never reaches the gate
        step whose 4b disposition block these tests assert on:
        deleting the verdict draws VERDICT_WITHOUT_REVIEW; touching the
        artifact draws UNMAPPED_CLAIM_SURFACE; PASS+blockers=1 draws
        VERDICT_SCHEMA_NONCOMPLIANT; a lone CONDITIONAL draws
        UNMAPPED_CLAIM_SURFACE again (a listing only retires staleness
        once a PASS covers it).
        """
        # Older round: PASS, owns the claim surface, inserted FIRST so
        # CARD_ID stays the newest (artifacts.json insertion order decides).
        (self.repo / ".tasks" / "legacy" / f"{OLD_ID}.md").write_text(
            _card_text(OLD_ID), encoding="utf-8"
        )
        old_verdict = {
            "id": OLD_ID,
            "artifact": "README.md",
            "verdict": "PASS",
            "blockers": 0,
            "conditions": [],
            "independent": True,
            "verifier": "reviewer@local",
            "ts": _now(),
            "evidence": ["git init -> success"],
        }
        (self.repo / "verdicts" / f"{OLD_ID}.verdict.json").write_text(
            json.dumps(old_verdict), encoding="utf-8"
        )
        map_path = self.repo / "artifacts.json"
        artifact_map = json.loads(map_path.read_text(encoding="utf-8"))
        # OLD_ID first (owns README.md's claim surface for lint), CARD_ID last
        # (stays the newest round -- gate step 2 targets it). CARD_ID keeps a
        # map entry even though its verdict is FAIL so the hook still finds
        # and gates it; dropping the entry instead would re-target OLD_ID
        # and the gate would pass.
        entries = {OLD_ID: ["README.md"]}
        entries.update(artifact_map)
        map_path.write_text(json.dumps(entries), encoding="utf-8")

        # Newest round: FAIL verdict -- gate step 2 rejects it.
        verdict_path = self.repo / "verdicts" / f"{CARD_ID}.verdict.json"
        verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
        verdict["verdict"] = "FAIL"
        verdict["blockers"] = 1
        verdict_path.write_text(json.dumps(verdict), encoding="utf-8")

    def test_gate_fail_with_freeze_state_prints_rollback_guide(self):
        """Phase 4b: a gate FAIL in a deepfreeze-managed tree prints the manual
        rollback guide (command TEXT read from .freeze/state.json) and the
        common-causes line -- but the hook still just exits 1; it never runs
        the restore itself."""
        self._break_gate_only()  # PASS + blockers=1 -> gate BAD_VERDICT_VALUE, lint green
        freeze = self.repo / ".freeze" / "state.json"
        freeze.parent.mkdir(parents=True, exist_ok=True)
        freeze.write_text(
            json.dumps({"latest_snapshot": "snap-20261024-012602"}), encoding="utf-8"
        )
        result = run_hook(self.repo, HOOK_STDIN_BRANCH)
        output = result.stdout + result.stderr

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("gate FAIL disposition", output)
        self.assertIn("common causes", output)
        self.assertIn("rollback guide (MANUAL", output)
        self.assertIn("snap-20261024-012602", output)
        self.assertIn("quarantine preserves post-snapshot new files", output)

    def test_gate_fail_without_freeze_state_says_no_snapshot(self):
        """Phase 4b: with no .freeze the disposition block still prints, but
        with the no-deepfreeze line instead of a rollback guide."""
        self._break_gate_only()  # gate-only FAIL; lint stays green
        result = run_hook(self.repo, HOOK_STDIN_BRANCH)
        output = result.stdout + result.stderr

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("gate FAIL disposition", output)
        self.assertIn("no deepfreeze state", output)
        self.assertNotIn("rollback guide", output)

    def test_gate_pass_prints_no_disposition_block(self):
        """Phase 4b: a green push stays green -- the disposition block (and the
        guide) must not leak into the happy path."""
        freeze = self.repo / ".freeze" / "state.json"
        freeze.parent.mkdir(parents=True, exist_ok=True)
        freeze.write_text(
            json.dumps({"latest_snapshot": "snap-20261024-012602"}), encoding="utf-8"
        )
        result = run_hook(self.repo, HOOK_STDIN_BRANCH)
        output = result.stdout + result.stderr

        self.assertEqual(result.returncode, 0, output)
        self.assertNotIn("gate FAIL disposition", output)
        self.assertNotIn("rollback guide", output)


    def test_tag_push_bypasses_gate(self):
        """A tag push exits 0 even with the round's verdict deleted."""
        (self.repo / "verdicts" / f"{CARD_ID}.verdict.json").unlink()
        result = run_hook(self.repo, HOOK_STDIN_TAG)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_delete_push_bypasses_gate(self):
        """A branch delete exits 0 even with the round's verdict deleted."""
        (self.repo / "verdicts" / f"{CARD_ID}.verdict.json").unlink()
        result = run_hook(self.repo, HOOK_STDIN_DELETE)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_empty_stdin_passes(self):
        """Empty stdin (nothing to push) exits 0."""
        result = run_hook(self.repo, "")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_multi_ref_with_one_branch_still_gates(self):
        """A tag plus a branch on the same push gates -- any branch line counts."""
        (self.repo / "verdicts" / f"{CARD_ID}.verdict.json").unlink()
        stdin_data = f"refs/tags/v1.0 {SHA} refs/tags/v1.0\n" + HOOK_STDIN_BRANCH
        result = run_hook(self.repo, stdin_data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BLOCKED", result.stdout + result.stderr)

    def test_outside_a_git_work_tree_is_a_hard_error(self):
        """Running outside a repo exits 2 with a message, not a silent pass."""
        plain = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, plain, True)
        result = run_hook(plain, HOOK_STDIN_BRANCH)
        self.assertEqual(result.returncode, 2)
        self.assertIn("not inside a git work tree", result.stderr)


class InstallHooksTestCase(unittest.TestCase, SeededRepoMixin):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name)
        self._git_init(self.repo)

    def _install(self) -> subprocess.CompletedProcess:
        return _popen(
            [BASH, str(INSTALL_SRC)], capture_output=True, text=True, cwd=str(self.repo)
        )

    def test_install_creates_hook(self):
        """First run creates .git/hooks/pre-push and makes it executable."""
        result = self._install()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        hook = self.repo / ".git" / "hooks" / "pre-push"
        self.assertTrue(hook.exists(), f"no hook at {hook}")
        # os.access, not st_mode & 0o110: NTFS has no POSIX execute bit, so the
        # bitmask reads 0 on Windows even after a successful `chmod +x`, and the
        # mask assertion fails on a hook that is installed correctly.
        self.assertTrue(os.access(hook, os.X_OK), f"{hook} is not executable")

    def test_install_is_idempotent(self):
        """A second run finds an identical hook and does nothing."""
        r1 = self._install()
        r2 = self._install()
        self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
        self.assertIn("nothing to do", r2.stdout)
        self.assertEqual(list((self.repo / ".git" / "hooks").glob("pre-push.bak.*")), [])

    def test_install_backs_up_existing_hook(self):
        """A different pre-existing hook is backed up, not clobbered."""
        hooks = self.repo / ".git" / "hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        (hooks / "pre-push").write_text("#!/bin/sh\necho custom\n", encoding="utf-8")
        result = self._install()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        backups = list(hooks.glob("pre-push.bak.*"))
        self.assertEqual(len(backups), 1, result.stdout + result.stderr)
        self.assertIn("custom", backups[0].read_text(encoding="utf-8"))

    def test_install_outside_a_git_work_tree_is_a_hard_error(self):
        """Refuses to install rather than guessing a repository."""
        plain = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, plain, True)
        result = _popen(
            [BASH, str(INSTALL_SRC)], capture_output=True, text=True, cwd=str(plain)
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("not inside a git work tree", result.stderr)


class RealHooksUntouchedTestCase(unittest.TestCase):
    """The card's hard constraint: the suite must never write real hooks."""

    def _snapshot(self) -> set:
        if not REAL_HOOKS.is_dir():
            return set()
        return {p.name: p.stat().st_mtime_ns for p in REAL_HOOKS.iterdir() if p.is_file()}

    def test_installing_into_a_temp_repo_leaves_real_hooks_untouched(self):
        before = self._snapshot()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _popen(["git", "init", "-b", "main"], capture_output=True, cwd=repo)
            _popen(
                [BASH, str(INSTALL_SRC)], capture_output=True, text=True, cwd=str(repo)
            )
        self.assertEqual(
            before,
            self._snapshot(),
            "running the installer against a temp repo modified the real "
            f"{REAL_HOOKS}; install-hooks.sh must resolve the target repo from "
            "the working directory, not from its own file location",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)