#!/usr/bin/env python3
"""v1.5.1 D4 flag tests (card XJ-20261107-002): ``out_encoding_miss``.

ADV-1 (fuxiang, v1.5 follow-up): the frozen ``out=`` caliber is exact
substring; when a miss is ONLY a line-ending/whitespace-encoding boundary
(CRLF vs LF, whitespace runs), the judge now leaves an explicit
``out_encoding_miss`` flag on the failed reproduction. Diagnostics only —
the E-level must be unchanged (E2 stays E2), which is what these tests pin.

Host-independent: subprocess output is monkeypatched, no real pwsh needed.

C12: synthetic data only; no sealed package is read here.

Run from the repository root:
    python -m unittest discover -s tests
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = REPO_ROOT / "tools" / "eval"

if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

import judge  # noqa: E402
from schema import Claim, EvidenceLine  # noqa: E402


def claim_with_out(command: str, exit_code: int, out: str):
    evidence = EvidenceLine(raw=f"cmd=`{command}` exit={exit_code} out=`{out}`",
                            source_line=9, command=command, exit_code=exit_code,
                            out=out)
    return Claim(text="合成断言。", source_line=9, product="P901",
                 evidence=evidence, anchors=[], unanchored=True)


class OutEncodingMissTests(unittest.TestCase):
    def setUp(self):
        self._original_run_command = judge.run_command
        self._original_probe = judge._PWSH_PROBE_CACHE
        judge._PWSH_PROBE_CACHE = {"available": True, "version": "test",
                                   "execution_policy": "Bypass", "engine": "x"}

    def tearDown(self):
        judge.run_command = self._original_run_command
        judge._PWSH_PROBE_CACHE = self._original_probe

    def _judge_with_output(self, output: str, out_claimed: str,
                           command: str = "python -c \"print(1)\"",
                           flavor: bool = False):
        """Monkeypatch run_command so the reproduction sees `output` verbatim."""
        def fake_run(cmd, cwd, timeout):
            return (0, output, "")
        judge.run_command = fake_run
        real_flavor = judge.is_powershell_flavor
        judge.is_powershell_flavor = lambda cmd: flavor
        try:
            with tempfile.TemporaryDirectory() as raw:
                c = claim_with_out(command, 0, out_claimed)
                return judge.judge_claim(c, Path(raw))
        finally:
            judge.is_powershell_flavor = real_flavor

    def test_crlf_boundary_flags_but_stays_e2(self):
        # claimed out written against LF; the recorded output carries CRLF
        j = self._judge_with_output("alpha\r\nbeta\r\n", "alpha\nbeta")
        self.assertEqual(j.level, "E2")
        self.assertIn("out_encoding_miss", j.flags)
        self.assertIn("声称输出未复现", j.detail)

    def test_whitespace_run_boundary_flags(self):
        j = self._judge_with_output("alpha  \t beta", "alpha beta")
        self.assertEqual(j.level, "E2")
        self.assertIn("out_encoding_miss", j.flags)

    def test_genuine_content_mismatch_has_no_flag(self):
        j = self._judge_with_output("totally different content", "alpha beta")
        self.assertEqual(j.level, "E2")
        self.assertNotIn("out_encoding_miss", j.flags)

    def test_exact_hit_never_flags(self):
        # exact substring hit reproduces (E4 for an unanchored claim) — the
        # flag only ever rides on a failed reproduction
        j = self._judge_with_output("alpha beta", "alpha")
        self.assertEqual(j.level, "E4")
        self.assertNotIn("out_encoding_miss", j.flags)

    def test_flag_works_on_pwsh_track_too(self):
        j = self._judge_with_output("alpha\r\nbeta\r\n", "alpha\nbeta",
                                    command="Get-Content x.txt", flavor=True)
        self.assertEqual(j.level, "E2")
        self.assertIn("out_encoding_miss", j.flags)
        self.assertIn("声称输出未复现", j.detail)


if __name__ == "__main__":
    unittest.main()
