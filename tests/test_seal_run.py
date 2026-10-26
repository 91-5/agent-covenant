#!/usr/bin/env python3
"""Tests for tools/eval/seal_run.py — stdlib unittest only (XJ-20261024-004).

The card's promise is deliberately narrow -- tamper-EVIDENT, not tamper-PROOF
-- so these tests pin the promise at exactly that width: post-seal edits are
named file-by-file (modified / missing / added), while the three documented
holes (in-place seal rewriting, whole-directory substitution, sealed lies)
stay out of the claims. The manifest must also never hash itself, and a
directory that is not a run directory must be refused rather than sealed.
"""
from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = REPO_ROOT / "tools" / "eval"
SEAL_TOOL = EVAL_DIR / "seal_run.py"

if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

import seal_run  # noqa: E402


def _make_run_dir(root: Path) -> Path:
    """A minimal run directory shaped like the runner's output."""
    run_dir = root / "run-20261026"
    (run_dir / "products").mkdir(parents=True)
    (run_dir / "run-data.json").write_text(
        json.dumps({"entries": [{"key": "T01-A-r1", "task_id": "T01",
                                 "condition": "A", "repetition": 1,
                                 "product": "products/T01-A-r1.md"}]}),
        encoding="utf-8")
    (run_dir / "run-log.json").write_text(
        json.dumps({"generated_utc": "2026-10-26T00:00:00+00:00",
                    "workspace": "test", "records": []}), encoding="utf-8")
    (run_dir / "products" / "T01-A-r1.md").write_text(
        "# T01\n\n- [已验证] 断言：命令以退出码 0 运行\n"
        "  证据：cmd=`echo ok` exit=0 out=`ok`\n", encoding="utf-8")
    return run_dir


class SealVerifyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.run_dir = _make_run_dir(self.root)

    def _seal(self, *extra):
        out = io.StringIO()
        with redirect_stdout(out):
            code = seal_run.main([str(self.run_dir), *extra])
        return code, out.getvalue()

    def _verify(self, target=None):
        out = io.StringIO()
        with redirect_stdout(out):
            code = seal_run.main(["--verify", str(target or self.run_dir)])
        return code, out.getvalue()

    def test_seal_then_verify_clean(self):
        code, out = self._seal()
        self.assertEqual(code, 0)
        self.assertIn("files: 3", out)
        vcode, vout = self._verify()
        self.assertEqual(vcode, 0)
        self.assertIn("VERIFY: OK", vout)

    def test_seal_manifest_contract(self):
        self._seal("--label", "round-2")
        manifest = json.loads((self.run_dir / "seal.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["root_label"], "round-2")
        self.assertEqual(manifest["file_count"], 3)
        for entry in manifest["files"].values():
            self.assertEqual(set(entry), {"sha256", "bytes"})
        self.assertIn("sealed_at_utc", manifest)
        self.assertIn("not tamper-proof", manifest["boundary"])
        for rel in manifest["files"]:
            self.assertNotIn("\\", rel, "paths must be posix-style")
            self.assertTrue((self.run_dir / rel).is_file())
        self.assertIn("run-data.json", manifest["files"])
        self.assertIn("products/T01-A-r1.md", manifest["files"])

    def test_seal_json_never_hashes_itself(self):
        self._seal()
        manifest = json.loads((self.run_dir / "seal.json").read_text(encoding="utf-8"))
        self.assertNotIn("seal.json", manifest["files"])
        # Re-sealing overwrites in place and still verifies.
        (self.run_dir / "products" / "T01-A-r1.md").write_text(
            "changed", encoding="utf-8")
        code, _ = self._seal()
        self.assertEqual(code, 0)
        vcode, _ = self._verify()
        self.assertEqual(vcode, 0)

    def test_nested_seal_json_is_ordinary_evidence(self):
        nested = self.run_dir / "products" / "seal.json"
        nested.write_text("{}", encoding="utf-8")
        self._seal()
        manifest = json.loads((self.run_dir / "seal.json").read_text(encoding="utf-8"))
        self.assertIn("products/seal.json", manifest["files"])

    def test_one_byte_change_is_reported_as_modified(self):
        self._seal()
        product = self.run_dir / "products" / "T01-A-r1.md"
        raw = bytearray(product.read_bytes())
        raw[0] ^= 0x01
        product.write_bytes(bytes(raw))
        vcode, vout = self._verify()
        self.assertEqual(vcode, 1)
        self.assertIn("MODIFIED", vout)
        self.assertIn("products/T01-A-r1.md", vout)

    def test_deleted_file_is_reported_missing(self):
        self._seal()
        (self.run_dir / "run-log.json").unlink()
        vcode, vout = self._verify()
        self.assertEqual(vcode, 1)
        self.assertIn("MISSING", vout)
        self.assertIn("run-log.json", vout)

    def test_added_file_is_reported_unregistered(self):
        self._seal()
        (self.run_dir / "products" / "T99-B-r9.md").write_text(
            "post-seal implant", encoding="utf-8")
        vcode, vout = self._verify()
        self.assertEqual(vcode, 1)
        self.assertIn("ADDED", vout)
        self.assertIn("products/T99-B-r9.md", vout)

    def test_all_three_drift_kinds_in_one_report(self):
        self._seal()
        (self.run_dir / "run-log.json").unlink()
        (self.run_dir / "run-data.json").write_text("{}", encoding="utf-8")
        (self.run_dir / "extra.txt").write_text("x", encoding="utf-8")
        vcode, vout = self._verify()
        self.assertEqual(vcode, 1)
        self.assertIn("MISSING  run-log.json", vout)
        self.assertIn("MODIFIED  run-data.json", vout)
        self.assertIn("ADDED  extra.txt", vout)

    def test_streaming_hash_matches_direct_hash_beyond_chunk_size(self):
        big = self.run_dir / "products" / "big.bin"
        payload = bytes(range(256)) * ((seal_run.CHUNK_SIZE * 2 + 137) // 256)
        big.write_bytes(payload)
        self._seal()
        manifest = json.loads((self.run_dir / "seal.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["files"]["products/big.bin"]["bytes"], len(payload))
        self.assertEqual(
            manifest["files"]["products/big.bin"]["sha256"],
            hashlib.sha256(payload).hexdigest())


class SealUsageErrorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_seal_empty_dir_is_usage_error(self):
        empty = self.root / "empty"
        empty.mkdir()
        out = io.StringIO()
        with redirect_stdout(out):
            code = seal_run.main([str(empty)])
        self.assertEqual(code, 2)
        self.assertFalse((empty / "seal.json").exists())

    def test_seal_without_run_data_is_usage_error(self):
        not_a_run = self.root / "not-a-run"
        not_a_run.mkdir()
        (not_a_run / "other.txt").write_text("x", encoding="utf-8")
        out = io.StringIO()
        with redirect_stdout(out):
            code = seal_run.main([str(not_a_run)])
        self.assertEqual(code, 2)
        self.assertFalse((not_a_run / "seal.json").exists())

    def test_seal_nonexistent_dir_is_usage_error(self):
        self.assertEqual(seal_run.main([str(self.root / "nope")]), 2)

    def test_verify_without_seal_is_usage_error(self):
        run_dir = _make_run_dir(self.root)
        self.assertEqual(seal_run.main(["--verify", str(run_dir)]), 2)

    def test_verify_with_corrupt_seal_is_usage_error(self):
        run_dir = _make_run_dir(self.root)
        seal_run.main([str(run_dir)])
        (run_dir / "seal.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(seal_run.main(["--verify", str(run_dir)]), 2)

    def test_no_arguments_prints_help_and_exit_2(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = seal_run.main([])
        self.assertEqual(code, 2)
        self.assertIn("usage:", out.getvalue())

    def test_verify_and_positional_are_mutually_exclusive(self):
        run_dir = _make_run_dir(self.root)
        # argparse-level conflict: parser.error prints to stderr and exits 2.
        with self.assertRaises(SystemExit) as ctx:
            seal_run.main([str(run_dir), "--verify", str(run_dir)])
        self.assertEqual(ctx.exception.code, 2)


class CustodyCopyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.run_dir = _make_run_dir(self.root)
        self.custody = self.root / "custody"

    def test_move_to_copies_and_verifies(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = seal_run.main([str(self.run_dir), "--move-to", str(self.custody)])
        self.assertEqual(code, 0)
        target = self.custody / self.run_dir.name
        self.assertTrue((target / "seal.json").is_file())
        self.assertIn("custody:", out.getvalue())
        # The original stays untouched (copy, never move) and still verifies.
        self.assertTrue((self.run_dir / "run-data.json").is_file())
        self.assertEqual(
            seal_run.main(["--verify", str(target)]), 0)
        # A drift in the copy is caught by its own seal.
        (target / "run-data.json").write_text("{}", encoding="utf-8")
        self.assertEqual(
            seal_run.main(["--verify", str(target)]), 1)

    def test_move_to_refuses_existing_target(self):
        target = self.custody / self.run_dir.name
        target.mkdir(parents=True)
        code = seal_run.main([str(self.run_dir), "--move-to", str(self.custody)])
        self.assertEqual(code, 1)


class CliContractTests(unittest.TestCase):
    """The real argv surface, including the cross-locale discipline: every
    subprocess capture uses text=True WITH explicit encoding + errors
    (XJ-20261024-004 constraint 2 / advisory F1)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.run_dir = _make_run_dir(self.root)

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(SEAL_TOOL), *args],
            text=True, encoding="utf-8", errors="replace", timeout=60,
            capture_output=True)

    def test_help_flag_works(self):
        proc = self._run("--help")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("--verify", proc.stdout)

    def test_seal_and_verify_round_trip_via_cli(self):
        proc = self._run(str(self.run_dir))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("seal:", proc.stdout)
        proc = self._run("--verify", str(self.run_dir))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("VERIFY: OK", proc.stdout)

    def test_missing_run_data_via_cli_exit_2(self):
        bare = self.root / "bare"
        bare.mkdir()
        proc = self._run(str(bare))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("run-data.json", proc.stderr)


if __name__ == "__main__":
    unittest.main()
