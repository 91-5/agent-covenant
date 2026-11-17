"""EVO-20261116-001 regression: verdict_gate.ps1 candidate-set hardening.

Each scenario builds an isolated verdict root in a temp dir and drives
scripts/verdict_gate.ps1 with -VerdictDir, so the real repo is never touched.

Scenarios (mirroring the card acceptance):
  S1  incident suffix (-posthoc-power-addendum) -> fail closed (cannot shadow)
  S1b legitimate topic sub-verdict (.round2) newer + canonical PASS -> allowed, audited
  S3  stage-only card -> newest stage verdict authorizes (4.2 item 8 semantics)
  S4  canonical PASS + newer sub FAIL -> fail closed (newest wins) + WARNING
  S4b older CONDITIONAL + newer .round2 PASS -> legitimate supersede, exit 0, WARNING
  S6  unknown suffix -> exit 1, offending file listed
  S7  identical ts -> canonical filename wins
  S8  audit prints chosen path + sha + ts + tsSource + provenance + script sha
  C1  -PR4-Afollow1 accepted (the condition AgnesCode raised in round 1)
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / 'scripts' / 'verdict_gate.ps1'
BASE = 'XJ-99999999-001'
POWERSHELL = shutil.which('powershell') or shutil.which('pwsh')

pytestmark = None


def _verdict(ts: str, verdict: str = 'PASS', blockers: int = 0) -> str:
    return json.dumps({
        'id': BASE,
        'verdict': verdict,
        'blockers': blockers,
        'conditions': 0,
        'independent': True,
        'ts': ts,
        'verifier': 'regression-fixture',
        'evidence': ['fixture'],
    })


@unittest.skipIf(POWERSHELL is None, 'powershell not available')
class VerdictGateHardeningTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix='vg-reg-'))

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, suffix: str, payload: str) -> None:
        (self.root / f'{BASE}{suffix}.verdict.json').write_text(payload, encoding='utf-8')

    def run_gate(self, *extra: str):
        cmd = [POWERSHELL, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(SCRIPT),
               '-CardId', BASE, '-VerdictDir', str(self.root), *extra]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return r.returncode, (r.stdout or '') + (r.stderr or '')

    def test_s1_incident_suffix_is_fail_closed(self) -> None:
        self.write('', _verdict('2026-11-15T11:46:50Z'))
        self.write('.posthoc-power-addendum', _verdict('2026-11-15T13:27:58Z'))
        rc, out = self.run_gate()
        self.assertEqual(rc, 1, out)
        self.assertIn('FAIL-CLOSED', out)
        self.assertIn('posthoc-power-addendum', out)

    def test_s1b_topic_sub_verdict_is_allowed_and_audited(self) -> None:
        self.write('', _verdict('2026-11-15T11:00:00Z'))
        self.write('.round2', _verdict('2026-11-15T13:00:00Z'))
        rc, out = self.run_gate()
        self.assertEqual(rc, 0, out)
        self.assertIn('provenance=topic-sub', out)

    def test_s3_stage_only_uses_newest_stage_verdict(self) -> None:
        self.write('-P3', _verdict('2026-11-15T10:00:00Z', 'FAIL', 1))
        self.write('-P4', _verdict('2026-11-15T11:00:00Z'))
        rc, out = self.run_gate()
        self.assertEqual(rc, 0, out)
        self.assertIn('provenance=stage', out)

    def test_s4_newer_sub_fail_blocks(self) -> None:
        self.write('', _verdict('2026-11-15T11:00:00Z', 'PASS'))
        self.write('.round2', _verdict('2026-11-15T13:00:00Z', 'FAIL', 2))
        rc, out = self.run_gate()
        self.assertEqual(rc, 1, out)
        self.assertIn('not PASS', out)
        self.assertIn('WARNING', out)

    def test_s4b_legitimate_supersede_is_not_blocked(self) -> None:
        self.write('', _verdict('2026-11-15T11:00:00Z', 'CONDITIONAL', 1))
        self.write('.round2', _verdict('2026-11-15T13:00:00Z', 'PASS'))
        rc, out = self.run_gate()
        self.assertEqual(rc, 0, out)
        self.assertIn('WARNING', out)

    def test_s6_unknown_suffix_fails_closed(self) -> None:
        self.write('', _verdict('2026-11-15T11:00:00Z'))
        self.write('-posthoc-power-addendum', _verdict('2026-11-15T13:00:00Z'))
        rc, out = self.run_gate()
        self.assertEqual(rc, 1, out)
        self.assertIn('FAIL-CLOSED', out)

    def test_s7_identical_ts_prefers_canonical(self) -> None:
        self.write('', _verdict('2026-11-15T12:00:00Z', 'FAIL', 2))
        self.write('.round2', _verdict('2026-11-15T12:00:00Z', 'PASS'))
        rc, out = self.run_gate()
        self.assertEqual(rc, 1, out)
        self.assertIn('not PASS', out)

    def test_s8_audit_fields_present(self) -> None:
        self.write('', _verdict('2026-11-15T11:00:00Z'))
        rc, out = self.run_gate()
        self.assertEqual(rc, 0, out)
        for token in ('audit: script=', 'chosen=', 'sha=', 'ts=', 'tsSource=', 'provenance='):
            self.assertIn(token, out)

    def test_c1_pr4_afollow1_accepted(self) -> None:
        self.write('-PR4-Afollow1', _verdict('2026-11-15T11:00:00Z'))
        rc, out = self.run_gate()
        self.assertEqual(rc, 0, out)
        self.assertNotIn('FAIL-CLOSED', out)

    def test_suffix_class_coverage(self) -> None:
        for suffix in ('-A', '-B', '-C', '.glasspill', '.glassdesk', '.round2', '.main-merge',
                       '-P2-B1', '-P3-C1', '-P6', '-P7', '-PR4-Afollow1'):
            self.write(suffix, _verdict('2026-11-15T10:00:00Z'))
        rc, out = self.run_gate()
        self.assertEqual(rc, 0, out)
        self.assertNotIn('FAIL-CLOSED', out)

    def test_require_exact_ignores_sub_verdicts(self) -> None:
        self.write('.round2', _verdict('2026-11-15T13:00:00Z', 'PASS'))
        rc, out = self.run_gate('-RequireExact')
        self.assertEqual(rc, 1, out)
        self.assertIn('no canonical', out)

    def test_allow_sub_verdict_escape_hatch(self) -> None:
        self.write('', _verdict('2026-11-15T11:00:00Z'))
        self.write('-posthoc-power-addendum', _verdict('2026-11-15T13:00:00Z'))
        rc, out = self.run_gate('-AllowSubVerdict', '-posthoc-power-addendum')
        self.assertEqual(rc, 0, out)


if __name__ == '__main__':
    unittest.main()