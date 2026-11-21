"""EVO-20261121-001 regression: design-only dual-track + case switch + BOM.

Covers:
  - contract: case switch compiled into the regex (re.IGNORECASE vs no flag)
  - contract: BOM-prefixed contract loads (ADV-N2 / N2 live bug)
  - contract: missing/non-bool design_only_case_sensitive is fail-closed (A2)
  - gate E-D2: legacy design card (no explicit field, content keyword) stays design-only
  - gate E-D3: explicit design_only=true wins even with no content keyword
  - gate E-D4: explicit design_only=false overrides content keyword (self-deadlock fix)
  - engine layer: compiled regex matches case variants per the switch (A5 engine side);
    the gate -match/-cmatch branch is verified by a standalone probe (temp scripts+tools
    copy, since the gate hard-anchors its contract to $PSScriptRoot), not in this suite.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / 'scripts' / 'verdict_gate.ps1'
BASE = 'XJ-99999998-001'
POWERSHELL = shutil.which('powershell') or shutil.which('pwsh')

spec = importlib.util.spec_from_file_location('lint_cards', REPO / 'tools' / 'lint_cards.py')
lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint)

DESIGN_TOKEN_LOWER = 'design gate'          # lowercase form present in the contract pattern
DESIGN_TOKEN_UPPER = 'DESIGN GATE'          # uppercase form only matches when case-insensitive


def _verdict(ts: str, **extra) -> str:
    payload = {
        'id': BASE, 'verdict': 'PASS', 'blockers': 0, 'conditions': 0,
        'independent': True, 'ts': ts, 'verifier': 'fixture', 'evidence': ['fixture'],
    }
    payload.update(extra)
    # ensure_ascii=False: real verdicts store Chinese scope notes as literal
    # characters; json.dumps' default would escape them to \uXXXX and the
    # gate's content scan would not see the keyword (fixture bug, not impl).
    return json.dumps(payload, ensure_ascii=False)


class ContractTest(unittest.TestCase):
    def test_case_switch_false_compiles_ignorecase(self) -> None:
        c = lint.load_verdict_contract(str(REPO))
        self.assertNotIn('error', c, c.get('error'))
        self.assertIs(c['design_only_case_sensitive'], False)
        self.assertTrue(c['design_only'].search(DESIGN_TOKEN_UPPER),
                        'case-insensitive switch must match uppercase variant')

    def test_bom_contract_loads(self) -> None:
        d = Path(tempfile.mkdtemp(prefix='bomcontract-'))
        try:
            (d / 'tools').mkdir()
            raw = json.loads((REPO / 'tools' / 'verdict_suffixes.json').read_text(encoding='utf-8-sig'))
            (d / 'tools' / 'verdict_suffixes.json').write_text(
                '\ufeff' + json.dumps(raw, ensure_ascii=False), encoding='utf-8')
            c = lint.load_verdict_contract(str(d))
            self.assertNotIn('error', c, c.get('error'))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_missing_or_nonbool_switch_is_fail_closed(self) -> None:
        for bad in ({'remove': True}, 'not-a-bool', 1, 'false'):
            d = Path(tempfile.mkdtemp(prefix='badswitch-'))
            try:
                (d / 'tools').mkdir()
                raw = json.loads((REPO / 'tools' / 'verdict_suffixes.json').read_text(encoding='utf-8-sig'))
                if bad == {'remove': True}:
                    raw.pop('design_only_case_sensitive', None)
                else:
                    raw['design_only_case_sensitive'] = bad
                (d / 'tools' / 'verdict_suffixes.json').write_text(
                    json.dumps(raw, ensure_ascii=False), encoding='utf-8')
                c = lint.load_verdict_contract(str(d))
                self.assertIn('error', c, f'switch={bad!r} must be fail-closed')
            finally:
                shutil.rmtree(d, ignore_errors=True)


@unittest.skipIf(POWERSHELL is None, 'powershell not available')
class GateDualTrackTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix='vg-dual-'))

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, payload: str, suffix: str = '') -> None:
        (self.root / f'{BASE}{suffix}.verdict.json').write_text(payload, encoding='utf-8')

    def run_gate(self, *extra: str):
        cmd = [POWERSHELL, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(GATE),
               '-CardId', BASE, '-VerdictDir', str(self.root), *extra]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return r.returncode, (r.stdout or '') + (r.stderr or '')

    def test_ed2_legacy_design_card_stays_design_only(self) -> None:
        # content keyword, NO explicit field -> content fallback -> design-only -> gate fails
        self.write(_verdict('2026-11-21T00:00:00Z', scope_note='规格级评审（设计门禁）'))
        rc, out = self.run_gate()
        self.assertEqual(rc, 1, out)
        self.assertIn('only design/spec-only', out)

    def test_ed3_explicit_true_wins_without_content(self) -> None:
        self.write(_verdict('2026-11-21T00:00:00Z', design_only=True))
        rc, out = self.run_gate()
        self.assertEqual(rc, 1, out)
        self.assertIn('only design/spec-only', out)

    def test_ed4_explicit_false_overrides_content_keyword(self) -> None:
        # the self-deadlock case: content has keyword but explicit false wins
        self.write(_verdict('2026-11-21T00:00:00Z', design_only=False,
                            scope_note='design gate / 规格级 discussion'))
        rc, out = self.run_gate()
        self.assertEqual(rc, 0, out)
        self.assertIn('OK:', out)

    def test_nonbool_explicit_field_is_fail_closed(self) -> None:
        self.write(_verdict('2026-11-21T00:00:00Z', design_only='false'))
        rc, out = self.run_gate()
        self.assertEqual(rc, 1, out)
        self.assertIn('must be a bool', out)

    def test_engine_layer_case_consistency(self) -> None:
        c = lint.load_verdict_contract(str(REPO))
        regex = c['design_only']
        for token in (DESIGN_TOKEN_LOWER, DESIGN_TOKEN_UPPER, 'Spec-Level', 'spec-level'):
            self.assertTrue(regex.search(token), f'contract regex should match {token!r} case-insensitively')


if __name__ == '__main__':
    unittest.main()
