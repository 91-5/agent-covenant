#!/usr/bin/env python3
"""v1.5 C10/C11 instrument implementation tests (card XJ-20261106-002).

C12 discipline: every run-dir, product, registry and workspace in this file is
built synthetically inside a temp dir. The real round-4 sealed package
(.eval-sealed/pkg-round4) and custody are never read and never re-judged -- the
judging-semantics change is exercised exclusively on synthetic data.

Coverage map against card D4:
  1. rebuild success path (declared hashes all match -> verified true)
  2. verification failure paths (hash mismatch -> packaging refused;
     registry entry with no source at either location -> refused)
  3. registry-missing flag (no impl-dual-placement.json -> registry_missing
     true, canonical files seeded unverified, packaging still succeeds)
  4. ref resolution order: workspace hit / judge-root hit / both missing ->
     ref_missing_both flag (workspace path only; legacy single-root has none)
  5. PowerShell flavor dispatch -> pwsh track
  6. exit + out dual condition: pass / exit-only flag / out mismatch /
     exit mismatch / overlong command flag
  7. bash path regression: non-PS commands behave byte-identically (same
     details, zero new flags), flavor detector stays False, legacy
     no-workspace calls unchanged
  +  packaging metadata: manifest carries workspace_rebuild + shell_track,
     lexicon hash matches the frozen §11 list, schema readers are
     backward-compatible, validator reports drift findings.

Run from the repository root:
    python -m unittest discover -s tests
"""
from __future__ import annotations

import hashlib
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
import judge  # noqa: E402
import schema  # noqa: E402


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_claim(text: str, evidence_raw: str, command: str = None,
               exit_code: int = None, out: str = None, ref: str = None,
               product: str = "P901", source_line: int = 9):
    """Build one Claim with a complete evidence line (synthetic)."""
    evidence = schema.EvidenceLine(raw=evidence_raw, source_line=source_line,
                                   command=command, exit_code=exit_code,
                                   out=out, ref=ref)
    return schema.Claim(text=text, source_line=source_line, product=product,
                        evidence=evidence, anchors=[], unanchored=True)


def build_synthetic_run(run_dir: Path, files: dict, registry: bool = True,
                        tamper: dict = None, declared_extra: dict = None):
    """Synthetic round-style run dir: run-data.json + one product per key +
    products/T##/ canonical implementation files + optional registry.

    files: {task: {name: content}}; tamper: {task/name: replacement content}
    applied to the canonical file AFTER the registry records the original hash
    (simulates post-placement drift -> packaging must refuse).

    Files are written with newline='' (LF bytes, no Windows translation) so the
    registry's declared hash matches the canonical bytes exactly."""
    products = run_dir / "products"
    products.mkdir(parents=True, exist_ok=True)
    entries = []
    registry_rows = []
    for index, (task, contents) in enumerate(sorted(files.items()), start=1):
        task_dir = products / task
        task_dir.mkdir(exist_ok=True)
        for name, content in sorted(contents.items()):
            original = content
            if registry:
                registry_rows.append({"task": task, "file": name,
                                      "sha256": hashlib.sha256(original.encode("utf-8")).hexdigest()})
            final = (tamper or {}).get(f"{task}/{name}", content)
            with open(task_dir / name, "w", encoding="utf-8", newline="") as fh:
                fh.write(final)
        for rep in (1, 2):
            key = f"{task}-A-r{rep}"
            (products / f"{key}.md").write_text(
                f"# {task} synthetic\n\n- [已验证] 合成断言 {task}。\n"
                f"  证据：ref={task}.md（独立复核）\n\n答案：{task}\n",
                encoding="utf-8")
            entries.append({"key": key, "task_id": task, "condition": "A",
                            "repetition": rep, "product": f"products/{key}.md",
                            "coverage": True})
    (run_dir / "run-data.json").write_text(
        json.dumps({"generated_utc": "2026-11-06T00:00:00+00:00",
                    "summary": {}, "entries": entries}, ensure_ascii=False),
        encoding="utf-8")
    if registry:
        payload = {"dual_placement": "synthetic fixture", "files": registry_rows}
        if declared_extra:
            payload["files"].extend(declared_extra)
        (run_dir / "impl-dual-placement.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class RebuildWorkspaceTests(unittest.TestCase):
    """C10 rebuild-workspace: success, fail-closed, and registry-missing."""

    def _build(self, tmp: Path, files: dict, registry: bool = True,
               tamper: dict = None, declared_extra: dict = None):
        run_dir = tmp / "run-dir"
        build_synthetic_run(run_dir, files, registry=registry, tamper=tamper,
                            declared_extra=declared_extra)
        out_dir = tmp / "pkg"
        blind.build_package(run_dir, out_dir, seed="ab" * 32, root=tmp / "judge-root")
        return run_dir, out_dir

    def test_1_rebuild_success_hashes_all_match(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            (tmp / "judge-root").mkdir()
            run_dir, out_dir = self._build(
                tmp, {"T91": {"impl.py": "VALUE = 90\n", "data.txt": "alpha\n"}})
            ws = out_dir / "workspace"
            self.assertTrue((ws / "impl.py").is_file())
            self.assertEqual((ws / "impl.py").read_text(encoding="utf-8"), "VALUE = 90\n")
            manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
            rebuild = manifest["workspace_rebuild"]
            self.assertTrue(rebuild["registry_present"])
            self.assertFalse(rebuild["registry_missing"])
            self.assertEqual(rebuild["file_count"], 2)
            self.assertTrue(all(row["verified"] for row in rebuild["files"]))
            # declared hash equals the sealed canonical bytes
            row = next(r for r in rebuild["files"] if r["file"] == "impl.py")
            self.assertEqual(row["sha256"], row["declared_sha256"])

    def test_2_tampered_canonical_fails_packaging(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            (tmp / "judge-root").mkdir()
            with self.assertRaises(ValueError) as ctx:
                self._build(tmp, {"T91": {"impl.py": "VALUE = 90\n"}},
                            tamper={"T91/impl.py": "VALUE = 999\n"})
            self.assertIn("C10 rebuild failed", str(ctx.exception))
            self.assertIn("!= declared", str(ctx.exception))

    def test_2b_registry_entry_without_any_source_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            (tmp / "judge-root").mkdir()
            ghost = hashlib.sha256(b"ghost\n").hexdigest()
            with self.assertRaises(ValueError) as ctx:
                self._build(tmp, {"T91": {"impl.py": "VALUE = 90\n"}},
                            declared_extra=[{"task": "T92", "file": "ghost.py",
                                             "sha256": ghost}])
            self.assertIn("neither", str(ctx.exception))

    def test_2c_working_copy_fallback_when_canonical_missing(self):
        # registry declares a file whose canonical copy is absent but whose
        # run-dir working copy exists and hashes right -> seeded, verified
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            (tmp / "judge-root").mkdir()
            run_dir = tmp / "run-dir"
            build_synthetic_run(run_dir, {"T91": {"impl.py": "VALUE = 90\n"}})
            (run_dir / "products" / "T91" / "impl.py").unlink()
            with open(run_dir / "loose.py", "w", encoding="utf-8", newline="") as fh:
                fh.write("VALUE = 90\n")
            registry_path = run_dir / "impl-dual-placement.json"
            payload = json.loads(registry_path.read_text(encoding="utf-8"))
            payload["files"][0]["file"] = "loose.py"
            registry_path.write_text(json.dumps(payload, ensure_ascii=False),
                                     encoding="utf-8")
            out_dir = tmp / "pkg"
            blind.build_package(run_dir, out_dir, seed="ab" * 32,
                                root=tmp / "judge-root")
            manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
            row = manifest["workspace_rebuild"]["files"][0]
            self.assertTrue(row["verified"])
            self.assertEqual(row["file"], "loose.py")
            self.assertTrue((out_dir / "workspace" / "loose.py").is_file())

    def test_3_registry_missing_is_explicit_not_silent(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            (tmp / "judge-root").mkdir()
            run_dir, out_dir = self._build(tmp, {"T91": {"impl.py": "VALUE = 90\n"}},
                                           registry=False)
            manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
            rebuild = manifest["workspace_rebuild"]
            self.assertTrue(rebuild["registry_missing"])
            self.assertFalse(rebuild["registry_present"])
            self.assertEqual(rebuild["file_count"], 1)
            self.assertFalse(rebuild["files"][0]["verified"])  # nothing to verify against
            # the workspace still seeded from the canonical tree (no silent loss)
            self.assertTrue((out_dir / "workspace" / "impl.py").is_file())


class RefResolutionTests(unittest.TestCase):
    """C10 ref order (workspace -> judge root) + ADV-1 ref_missing_both."""

    def _claim(self, ref: str):
        return make_claim("独立复核断言。", f"ref={ref}（独立复核）", ref=ref)

    def test_4_ref_resolves_in_workspace_first(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            root = tmp / "judge-root"
            root.mkdir()
            ws = tmp / "workspace"
            ws.mkdir()
            (ws / "impl.py").write_text("VALUE = 90\n", encoding="utf-8")
            j = judge.judge_claim(self._claim("impl.py"), root, workspace=ws)
            self.assertEqual(j.level, "E4")
            self.assertIn("ref 存在且可读: impl.py", j.detail)

    def test_4b_ref_falls_back_to_judge_root(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            root = tmp / "judge-root"
            root.mkdir()
            (root / "repo.md").write_text("repo fact\n", encoding="utf-8")
            ws = tmp / "workspace"
            ws.mkdir()
            j = judge.judge_claim(self._claim("repo.md"), root, workspace=ws)
            self.assertEqual(j.level, "E4")
            self.assertIn("repo fact", j.observation)

    def test_4c_ref_missing_both_places_flags(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            root = tmp / "judge-root"
            root.mkdir()
            ws = tmp / "workspace"
            ws.mkdir()
            j = judge.judge_claim(self._claim("nowhere.py"), root, workspace=ws)
            self.assertEqual(j.level, "E2")
            self.assertIn("ref_missing_both", j.flags)
            self.assertIn("ref 不存在", j.detail)

    def test_4d_legacy_single_root_has_no_new_flag(self):
        # no workspace -> pre-v1.5 behaviour: E2, no ref_missing_both
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            root = tmp / "judge-root"
            root.mkdir()
            j = judge.judge_claim(self._claim("nowhere.py"), root)
            self.assertEqual(j.level, "E2")
            self.assertNotIn("ref_missing_both", j.flags)


class ShellDualTrackTests(unittest.TestCase):
    """C11: flavor dispatch, pwsh track, exit+out dual condition, flags."""

    def setUp(self):
        track = judge.powershell_track_info()
        if not track["available"]:
            self.skipTest("powershell.exe unavailable on this host")

    def test_5_lexicon_matches_frozen_s11_list(self):
        # card constraint 3: the 15 tokens are copied verbatim from v1.5 §11
        self.assertEqual(judge.POWERSHELL_FLAVOR_TOKENS, (
            "get-content", "test-path", "select-string", "get-childitem",
            "get-item", "get-date", "measure-object", "set-content",
            "copy-item", "write-output", "out-string", "format-table",
            "get-random", "get-process", "sort-object"))
        self.assertEqual(len(judge.POWERSHELL_FLAVOR_TOKENS), 15)

    def test_5b_flavor_dispatch_hits_pwsh_track(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            root = tmp / "judge-root"
            root.mkdir()
            ws = tmp / "workspace"
            ws.mkdir()
            (ws / "marker.txt").write_text("present\n", encoding="utf-8")
            claim = make_claim("工作区文件存在。", "cmd=`Test-Path marker.txt` exit=0 out=`True`",
                               command="Test-Path marker.txt", exit_code=0, out="True")
            j = judge.judge_claim(claim, root, workspace=ws)
            self.assertEqual(j.level, "E4")
            self.assertIn("pwsh 轨已复现", j.detail)
            self.assertNotIn("pwsh_exit_level_only", j.flags)

    def test_6_exit_and_out_dual_condition_pass(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            root = tmp / "judge-root"
            root.mkdir()
            claim = make_claim("存在性。", "cmd=`Test-Path missing-thing.txt` exit=0 out=`False`",
                               command="Test-Path missing-thing.txt", exit_code=0,
                               out="False")
            j = judge.judge_claim(claim, root)
            self.assertEqual(j.level, "E4")
            self.assertIn("已命中", j.detail)

    def test_6b_out_mismatch_fails_even_when_exit_matches(self):
        # ADV-1 third state: cmdlet exit=0 on logical no-match; only the
        # output-semantic check catches the false claim
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            root = tmp / "judge-root"
            root.mkdir()
            claim = make_claim("存在性。", "cmd=`Test-Path missing-thing.txt` exit=0 out=`True`",
                               command="Test-Path missing-thing.txt", exit_code=0,
                               out="True")
            j = judge.judge_claim(claim, root)
            self.assertEqual(j.level, "E2")
            self.assertIn("声称输出未复现", j.detail)

    def test_6c_exit_only_claim_records_exit_level_flag(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            root = tmp / "judge-root"
            root.mkdir()
            claim = make_claim("存在性。", "cmd=`Test-Path missing-thing.txt` exit=0",
                               command="Test-Path missing-thing.txt", exit_code=0)
            j = judge.judge_claim(claim, root)
            self.assertEqual(j.level, "E4")
            self.assertIn("pwsh_exit_level_only", j.flags)
            self.assertIn("仅 exit 级复现", j.detail)

    def test_6d_exit_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            root = tmp / "judge-root"
            root.mkdir()
            claim = make_claim("存在性。", "cmd=`Test-Path missing-thing.txt` exit=1",
                               command="Test-Path missing-thing.txt", exit_code=1)
            j = judge.judge_claim(claim, root)
            self.assertEqual(j.level, "E2")
            self.assertIn("退出码不符", j.detail)
            self.assertIn("实际 exit=0", j.detail)

    def test_6e_overlong_command_is_flagged_not_executed(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            root = tmp / "judge-root"
            root.mkdir()
            long_cmd = "Write-Output " + "x" * (judge.MAX_PWSH_COMMAND_CHARS + 1)
            claim = make_claim("长命令。", "cmd=`...` exit=0", command=long_cmd,
                               exit_code=0)
            j = judge.judge_claim(claim, root)
            self.assertEqual(j.level, "E2")
            self.assertIn("command_too_long", j.flags)
            self.assertIn("命令超长", j.detail)


class BashPathRegressionTests(unittest.TestCase):
    """Constraint 2: non-PS commands must behave byte-identically."""

    def test_7_bash_command_unchanged_details_and_flags(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            root = tmp / "judge-root"
            root.mkdir()
            (root / "data.txt").write_text("line\n", encoding="utf-8")
            claim = make_claim("文件读取。", "cmd=`python -c \"print('line')\"` exit=0 out=`line`",
                               command="python -c \"print('line')\"", exit_code=0,
                               out="line")
            j = judge.judge_claim(claim, root)
            self.assertEqual(j.level, "E4")
            self.assertIn("命令已复现: ", j.detail)  # legacy detail prefix
            self.assertNotIn("pwsh", j.detail)
            self.assertFalse(any(f.startswith("pwsh") for f in j.flags))
            self.assertNotIn("ref_missing_both", j.flags)

    def test_7b_bash_failure_keeps_legacy_detail(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            root = tmp / "judge-root"
            root.mkdir()
            claim = make_claim("退出码。", "cmd=`python -c \"import sys; sys.exit(3)\"` exit=0",
                               command="python -c \"import sys; sys.exit(3)\"", exit_code=0)
            j = judge.judge_claim(claim, root)
            self.assertEqual(j.level, "E2")
            self.assertIn("退出码不符: 证据声称 exit=0, 实际 exit=3", j.detail)

    def test_7c_flavor_detector_negative_for_bash(self):
        self.assertFalse(judge.is_powershell_flavor("python -c \"print(1)\""))
        self.assertFalse(judge.is_powershell_flavor("git log --oneline -1"))
        self.assertFalse(judge.is_powershell_flavor("ls -la"))
        # and positive only via frozen tokens (case-insensitive)
        self.assertTrue(judge.is_powershell_flavor("Get-Content x.txt"))
        self.assertTrue(judge.is_powershell_flavor("TEST-PATH x"))

    def test_7d_workspace_redirects_command_cwd(self):
        # C10: with a workspace, the command runs THERE (file visible), while
        # the judge root without workspace does not see it
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            root = tmp / "judge-root"
            root.mkdir()
            ws = tmp / "workspace"
            ws.mkdir()
            (ws / "only_ws.txt").write_text("ws\n", encoding="utf-8")
            claim = make_claim("文件存在。",
                               "cmd=`python -c \"import os;print(os.path.exists('only_ws.txt'))\"` exit=0 out=`True`",
                               command="python -c \"import os;print(os.path.exists('only_ws.txt'))\"",
                               exit_code=0, out="True")
            with_ws = judge.judge_claim(claim, root, workspace=ws)
            without_ws = judge.judge_claim(claim, root)
            self.assertEqual(with_ws.level, "E4")
            self.assertEqual(without_ws.level, "E2")


class PwshUnavailableDegradationTests(unittest.TestCase):
    """Constraint 6: a host without powershell.exe degrades explicitly —
    the pwsh track refuses with pwsh_unavailable, never silently falls back
    to cmd (monkeypatched probe, host-independent)."""

    def tearDown(self):
        judge._PWSH_PROBE_CACHE = None

    def test_pwsh_unavailable_flag_no_silent_fallback(self):
        judge._PWSH_PROBE_CACHE = {"available": False, "version": None,
                                   "execution_policy": None,
                                   "engine": "powershell.exe (Windows PowerShell)"}
        try:
            root = Path(tempfile.mkdtemp())
            claim = make_claim("存在性。", "cmd=`Test-Path anything.txt` exit=0",
                               command="Test-Path anything.txt", exit_code=0)
            j = judge.judge_claim(claim, root)
            self.assertEqual(j.level, "E2")
            self.assertIn("pwsh_unavailable", j.flags)
            self.assertIn("powershell 不可用", j.detail)
            self.assertIn("pwsh 轨拒绝执行", j.detail)
        finally:
            judge._PWSH_PROBE_CACHE = None

    def test_probe_failure_reads_as_unavailable(self):
        # a probe subprocess that fails (nonzero exit / empty output) must
        # surface as available=False, never crash or silently approve
        judge._PWSH_PROBE_CACHE = None
        original = judge.run_command
        try:
            judge.run_command = lambda *a, **k: (1, "", "boom")
            info = judge.powershell_track_info()
            self.assertFalse(info["available"])
            self.assertIsNone(info["version"])
        finally:
            judge.run_command = original


class PackagingMetadataTests(unittest.TestCase):
    """D3: manifest metadata block + schema backward-compatible readers."""

    def test_metadata_block_present_and_backward_compatible(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            (tmp / "judge-root").mkdir()
            run_dir = tmp / "run-dir"
            build_synthetic_run(run_dir, {"T91": {"impl.py": "VALUE = 90\n"}})
            out_dir = tmp / "pkg"
            blind.build_package(run_dir, out_dir, seed="ab" * 32,
                                root=tmp / "judge-root")
            manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
            meta = schema.packaging_metadata(manifest)
            self.assertIn("workspace_rebuild", meta)
            self.assertIn("shell_track", meta)
            self.assertEqual(meta["shell_track"]["lexicon_sha256"],
                             judge.lexicon_sha256())
            self.assertEqual(schema.validate_packaging_metadata(meta), [])
            # legacy manifests: no block -> empty read, no findings, no raise
            self.assertEqual(schema.packaging_metadata({}), {})
            self.assertEqual(schema.validate_packaging_metadata({}), [])
            self.assertEqual(schema.packaging_metadata({"products": {}}), {})

    def test_metadata_validator_reports_drift(self):
        meta = {"workspace_rebuild": {"registry_missing": "yes", "files": None},
                "shell_track": {"available": 1}}
        findings = schema.validate_packaging_metadata(meta)
        self.assertEqual(len(findings), 5)
        self.assertTrue(any("registry_missing" in f for f in findings))
        self.assertTrue(any("lexicon_sha256" in f for f in findings))

    def test_metadata_shell_track_records_engine(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            (tmp / "judge-root").mkdir()
            run_dir = tmp / "run-dir"
            build_synthetic_run(run_dir, {"T91": {"impl.py": "VALUE = 90\n"}})
            out_dir = tmp / "pkg"
            blind.build_package(run_dir, out_dir, seed="ab" * 32,
                                root=tmp / "judge-root")
            manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
            track = manifest["shell_track"]
            self.assertIn("available", track)
            self.assertIn("lexicon_sha256", track)
            self.assertIn("engine", track)
            if track["available"]:
                self.assertTrue(str(track["version"]))
                self.assertTrue(str(track["execution_policy"]))


if __name__ == "__main__":
    unittest.main()
