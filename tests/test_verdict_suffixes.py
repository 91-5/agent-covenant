"""EVO-20261117-001: one verdict-name contract, two consumers.

Covers the suffix whitelist, the per-class `id` contract, the unknown-suffix
ERROR, pair merging (a whitelisted sub-verdict belongs to its base card, not to
a phantom card), and the gate-consistent selection used by freshness.

The point of these tests is drift: the gate (PowerShell) and the linter (Python)
must read the SAME data file, and the `id` contract must branch by suffix class
because the live corpus does -- canonical/single/topic carry the base id while
all ten stage verdicts carry the full stem (coldstore).
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load_linter():
    spec = importlib.util.spec_from_file_location('lint_cards', REPO / 'tools' / 'lint_cards.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lint = _load_linter()

CONTRACT = REPO / 'tools' / 'verdict_suffixes.json'
GATE = REPO / 'scripts' / 'verdict_gate.ps1'


def _verdict(card_id: str, ts: str = '2026-11-17T00:00:00Z', verdict: str = 'PASS') -> dict:
    return {
        'id': card_id, 'verdict': verdict, 'blockers': 0, 'conditions': 0,
        'independent': True, 'verifier': 'unit-fixture', 'ts': ts, 'evidence': ['fixture'],
    }


class ContractTest(unittest.TestCase):
    def test_contract_loads(self) -> None:
        contract = lint.load_verdict_contract()
        self.assertNotIn('error', contract, contract.get('error'))
        self.assertTrue(contract['patterns'])
        self.assertTrue(contract['design_only'])

    def test_gate_has_no_second_copy_of_the_patterns(self) -> None:
        text = GATE.read_text(encoding='utf-8')
        self.assertNotIn('^-(?:P|PR)', text, 'gate must not inline the suffix pattern')
        self.assertNotIn('(?:main-merge)', text, 'gate must not inline the topic pattern')
        self.assertIn('verdict_suffixes.json', text, 'gate must read the shared contract')

    def test_gate_reads_design_only_from_the_contract(self) -> None:
        text = GATE.read_text(encoding='utf-8')
        self.assertIn('design_only_pattern', text)
        self.assertNotIn('\\u89C4\\u683C\\u7EA7|', text, 'gate must not inline the design-only regex')


class SplitTest(unittest.TestCase):
    def test_split_cases(self) -> None:
        cases = {
            'OC-20261110-001': ('OC-20261110-001', ''),
            'OC-20261110-001-P3': ('OC-20261110-001', '-P3'),
            'OC-20261113-002-PR4-Afollow1': ('OC-20261113-002', '-PR4-Afollow1'),
            'XJ-20261115-001.posthoc-power-addendum': ('XJ-20261115-001', '.posthoc-power-addendum'),
            'GLASSSUITE-20261110-001': ('GLASSSUITE-20261110-001', ''),
            'not-a-card': ('not-a-card', ''),
        }
        for stem, expected in cases.items():
            self.assertEqual(lint.split_verdict_stem(stem), expected, stem)

    def test_classification(self) -> None:
        contract = lint.load_verdict_contract()
        expected = {
            '': 'canonical',
            '-P3': 'stage', '-P4': 'stage', '-P6': 'stage', '-P7': 'stage',
            '-P3-C1': 'stage', '-P2-B1': 'stage', '-PR4-Afollow1': 'stage',
            '-A': 'single', '-B': 'single', '-C': 'single',
            '.glasspill': 'topic', '.glassdesk': 'topic', '.round2': 'topic', '.main-merge': 'topic',
            '-posthoc-power-addendum': 'unknown',
            '.posthoc-power-addendum': 'unknown',
            '-impl-review': 'unknown',
            '.foo-bar': 'unknown',
        }
        for suffix, cls in expected.items():
            self.assertEqual(lint.classify_verdict_suffix(suffix, contract), cls, suffix)

    def test_id_contract_branches_by_class(self) -> None:
        self.assertEqual(lint.expected_verdict_id('OC-1-x', 'OC-1', 'canonical'), 'OC-1')
        self.assertEqual(lint.expected_verdict_id('XJ-1.round2', 'XJ-1', 'topic'), 'XJ-1')
        self.assertEqual(lint.expected_verdict_id('OC-1-A', 'OC-1', 'single'), 'OC-1')
        self.assertEqual(lint.expected_verdict_id('OC-1-P3', 'OC-1', 'stage'), 'OC-1-P3')


class LintBehaviourTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix='vc-'))
        self.verdicts = self.dir / 'verdicts'
        self.verdicts.mkdir()
        self.cards = self.dir / 'cards'
        self.cards.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, stem: str, payload: dict) -> None:
        (self.verdicts / f'{stem}.verdict.json').write_text(json.dumps(payload), encoding='utf-8')

    def card(self, card_id: str) -> None:
        (self.cards / f'{card_id}.md').write_text(f'# {card_id}\n', encoding='utf-8')

    def test_unknown_suffix_is_error_and_not_a_phantom_card(self) -> None:
        base = 'XJ-20261117-900'
        self.card(base)
        self.write(base, _verdict(base))
        self.write(f'{base}-posthoc-power-addendum', _verdict(base))
        findings = lint.check_verdict_pairs({base}, self.verdicts)
        codes = [f['rule'] for f in findings]
        self.assertIn('VERDICT_SUFFIX_UNKNOWN', codes)
        self.assertNotIn('ORPHAN_VERDICT', codes)

    def test_whitelisted_sub_verdict_belongs_to_base_card(self) -> None:
        base = 'XJ-20261117-901'
        self.card(base)
        self.write(base, _verdict(base))
        self.write(f'{base}.round2', _verdict(base, '2026-11-17T05:00:00Z'))
        findings = lint.check_verdict_pairs({base}, self.verdicts)
        codes = [f['rule'] for f in findings]
        self.assertNotIn('ORPHAN_VERDICT', codes)
        self.assertNotIn('VERDICT_WITHOUT_REVIEW', codes)
        self.assertNotIn('VERDICT_SUFFIX_UNKNOWN', codes)

    def test_stage_verdict_alone_satisfies_the_card(self) -> None:
        base = 'XJ-20261117-902'
        self.card(base)
        self.write(f'{base}-P4', _verdict(f'{base}-P4'))
        findings = lint.check_verdict_pairs({base}, self.verdicts)
        self.assertNotIn('VERDICT_WITHOUT_REVIEW', [f['rule'] for f in findings])

    def test_schema_id_contract_per_class(self) -> None:
        base = 'XJ-20261117-903'
        self.card(base)
        self.write(base, _verdict(base))
        self.write(f'{base}.round2', _verdict(base))
        self.write(f'{base}-P4', _verdict(f'{base}-P4'))
        findings = lint.check_verdict_schema(self.verdicts)
        self.assertEqual([f for f in findings if f['rule'] == 'VERDICT_SCHEMA_NONCOMPLIANT'], [])

    def test_schema_flags_wrong_id_for_each_class(self) -> None:
        base = 'XJ-20261117-904'
        self.card(base)
        self.write(f'{base}.round2', _verdict(f'{base}.round2'))   # topic must use base
        self.write(f'{base}-P4', _verdict(base))                   # stage must use stem
        findings = lint.check_verdict_schema(self.verdicts)
        bad = {Path(str(f['file'])).name for f in findings if f['rule'] == 'VERDICT_SCHEMA_NONCOMPLIANT'}
        self.assertIn(f'{base}.round2.verdict.json', bad)
        self.assertIn(f'{base}-P4.verdict.json', bad)

    def test_index_selection_newest_then_canonical(self) -> None:
        base = 'XJ-20261117-905'
        self.write(base, _verdict(base, '2026-11-17T01:00:00Z', 'CONDITIONAL'))
        self.write(f'{base}.round2', _verdict(base, '2026-11-17T02:00:00Z', 'PASS'))
        records = lint._verdict_index(self.verdicts)
        self.assertEqual(records[base]['verdict'], 'PASS')

        other = 'XJ-20261117-906'
        self.write(other, _verdict(other, '2026-11-17T02:00:00Z', 'CONDITIONAL'))
        self.write(f'{other}.round2', _verdict(other, '2026-11-17T02:00:00Z', 'PASS'))
        records = lint._verdict_index(self.verdicts)
        self.assertEqual(records[other]['verdict'], 'CONDITIONAL', 'tie must prefer canonical')

    def test_index_skips_unknown_suffix(self) -> None:
        base = 'XJ-20261117-907'
        self.write(base, _verdict(base, '2026-11-17T01:00:00Z', 'FAIL'))
        self.write(f'{base}-weird-name', _verdict(base, '2026-11-17T09:00:00Z', 'PASS'))
        records = lint._verdict_index(self.verdicts)
        self.assertEqual(records[base]['verdict'], 'FAIL', 'unknown suffix must not win')


class LiveCorpusTest(unittest.TestCase):
    def test_coldstore_readonly_has_no_unknown_suffix(self) -> None:
        coldstore = Path(r'D:\15812\projects\coldstore\verdicts')
        if not coldstore.is_dir():
            self.skipTest('coldstore verdicts not present on this machine')
        contract = lint.load_verdict_contract()
        unknown = []
        stage_ids = []
        for path in coldstore.glob('*.verdict.json'):
            stem = path.name[: -len(lint.VERDICT_SUFFIX)]
            base, suffix = lint.split_verdict_stem(stem)
            cls = lint.classify_verdict_suffix(suffix, contract)
            if cls == 'unknown':
                unknown.append(path.name)
            if cls == 'stage':
                data = json.loads(path.read_text(encoding='utf-8-sig'))
                stage_ids.append((path.name, data.get('id'), stem))
        self.assertEqual(unknown, [], 'coldstore must have zero unknown suffixes')
        for name, vid, stem in stage_ids:
            self.assertEqual(vid, stem, f'{name}: stage verdict id must be the full stem')


if __name__ == '__main__':
    unittest.main()