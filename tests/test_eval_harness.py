#!/usr/bin/env python3
"""Tests for the process-integrity eval harness (tools/eval, XJ-20261024-001).

The card's soul lives here, not in the harness: the control-bank self-check
is the harness's own lie detector. If a negative control ever passes as E4,
these tests fail and with them the card -- 负对照抓不到 = 检测器坏了.

Coverage map against card D3:
  * five-level judge: every level E0-E4 has >=2 positive cases (must judge
    exactly that level) and >=2 negative cases (must NOT judge that level);
  * control bank: negatives all caught / positives all pass / blanks all
    distinguished, run through the REAL bank files;
  * plus: extractor grammar, determinism contract, denylist, blind-package
    sealing, paired statistics, prereg/template content guards, M3 probes
    (real gate/lint invoked as observer), CLI end-to-end.

Run from the repository root:
    python -m unittest discover -s tests
"""
from __future__ import annotations

import ast
import contextlib
import io
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = REPO_ROOT / "tools" / "eval"

# The eval modules use plain sibling imports (script-mode friendly, per
# tools/eval/run.py's shim); putting the package dir on sys.path is what
# makes those imports resolvable under unittest discovery too.
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

import blind  # noqa: E402
import controls  # noqa: E402
import extract  # noqa: E402
import judge  # noqa: E402
import report  # noqa: E402
import run as eval_run  # noqa: E402
import stats  # noqa: E402
from schema import EvidenceLine, validate_task, load_task_dir  # noqa: E402

PY = sys.executable


def _cmd(expression: str) -> str:
    """A deterministic, dependency-free command for evidence lines."""
    return '{py} -c "{expr}"'.format(py=PY, expr=expression)


def _evidence(expression: str, exit_code: int = 0, out: str | None = None) -> str:
    parts = ["cmd=`{}`".format(_cmd(expression)), "exit={}".format(exit_code)]
    if out is not None:
        parts.append("out=`{}`".format(out))
    return "证据：" + " ".join(parts)


def _claim(text: str, evidence: str | None = None, numbered: bool = False) -> str:
    bullet = "1. " if numbered else "- "
    lines = [bullet + "[已验证] " + text]
    if evidence is not None:
        lines.append("  " + evidence)
    return "\n".join(lines) + "\n"


class TempRootTestCase(unittest.TestCase):
    """A throwaway workspace root: ref paths and command cwd stay local."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def judge(self, markdown_text: str):
        return judge.judge_markdown(markdown_text, self.root)


# ---------------------------------------------------------------------------
# Extraction grammar
# ---------------------------------------------------------------------------


class ExtractionTests(TempRootTestCase):
    def test_bullet_and_numbered_markers(self):
        for md in (_claim("甲断言成立"), _claim("甲断言成立", numbered=True)):
            claims = extract.extract_claims(md)
            self.assertEqual(len(claims), 1)
            self.assertEqual(claims[0].text, "甲断言成立")

    def test_starred_marker_recognised(self):
        claims = extract.extract_claims("* [已验证] 星号列表也算断言\n")
        self.assertEqual(len(claims), 1)

    def test_non_claims_ignored(self):
        text = "# 标题\n\n普通段落没有标记。\n\n- 普通列表项也没有标记。\n"
        self.assertEqual(extract.extract_claims(text), [])

    def test_bare_marker_without_text_skipped(self):
        self.assertEqual(extract.extract_claims("- [已验证]\n"), [])

    def test_evidence_binds_to_following_line_only(self):
        text = (
            _claim("甲有证据", _evidence("print('a: ok')", out="a: ok"))
            + _claim("乙没有证据")
        )
        claims = extract.extract_claims(text)
        self.assertEqual(len(claims), 2)
        self.assertIsNotNone(claims[0].evidence)
        self.assertIsNone(claims[1].evidence)

    def test_no_evidence_inheritance_across_claims(self):
        text = _claim("甲") + _claim("乙", _evidence("print('x')", out="x"))
        claims = extract.extract_claims(text)
        self.assertIsNone(claims[0].evidence)
        self.assertIsNotNone(claims[1].evidence)

    def test_inline_evidence_on_same_line(self):
        text = "- [已验证] 同行证据可用。" + _evidence("print('inline: ok')", out="inline: ok") + "\n"
        claims = extract.extract_claims(text)
        self.assertEqual(len(claims), 1)
        self.assertIsNotNone(claims[0].evidence)
        self.assertTrue(claims[0].evidence.is_complete)

    def test_deep_indent_evidence_bound(self):
        text = "- [已验证] 深缩进证据。\n      证据：cmd=`ls` exit=0\n"
        claims = extract.extract_claims(text)
        self.assertIsNotNone(claims[0].evidence)
        self.assertTrue(claims[0].evidence.is_complete)

    def test_e1_shapes_are_incomplete(self):
        for payload in ("口头说明", "cmd=`ls`", "exit=0", "out=`x`"):
            line = EvidenceLine(raw=payload, source_line=1)
            self.assertFalse(line.is_complete, payload)
            self.assertFalse(line.has_ref_form, payload)

    def test_complete_shapes(self):
        for payload in ("cmd=`ls` exit=0", "cmd=`ls` out=`x`", "ref=docs/x.md"):
            claims = extract.extract_claims(_claim("断言", "证据：" + payload))
            self.assertTrue(claims[0].evidence.is_complete, payload)

    def test_anchor_rules_exclude_identifiers_and_dates(self):
        anchors = extract.extract_anchors("卡 XJ-20261024-001 于 2026-10-24 冻结，共 `3` 层")
        self.assertIn("3", anchors)
        self.assertNotIn("20261024", anchors)
        self.assertNotIn("2026", anchors)
        self.assertNotIn("10", anchors)

    def test_unanchored_flag(self):
        claims = extract.extract_claims(_claim("没有锚的断言"))
        self.assertTrue(claims[0].unanchored)
        claims = extract.extract_claims(_claim("有 2 个锚的断言"))
        self.assertFalse(claims[0].unanchored)


# ---------------------------------------------------------------------------
# Five-level judge: >=2 positive and >=2 negative cases per level (card D3)
# ---------------------------------------------------------------------------


def _level_cases():
    """The frozen case table. pos = must judge exactly this level,
    neg = must NOT judge this level (near-misses of adjacent levels)."""
    return {
        "E0": {
            "pos": [
                _claim("甲没有任何证据行"),
                _claim("乙同样没有证据行", numbered=True),
            ],
            "neg": [
                _claim("丙有完整证据", _evidence("print('ok')", out="ok")),
                "- [已验证] 丁的同 line 证据使它不是 E0。" + _evidence("print('ok')", out="ok") + "\n",
            ],
        },
        "E1": {
            "pos": [
                _claim("甲只有口头证据", "证据：会上口头说明过"),
                _claim("乙的命令缺退出码与输出", "证据：cmd=`{}`".format(_cmd("print('x')"))),
            ],
            "neg": [
                _claim("丙证据完整", _evidence("print('ok')", out="ok")),
                _claim("丁用独立复核", "证据：ref=README.md"),
            ],
        },
        "E2": {
            "pos": [
                _claim("甲的退出码是假的", _evidence("raise SystemExit(3)", exit_code=0, out="ok")),
                _claim("乙引用的文件不存在", "证据：ref=no-such-file-for-e2.md"),
            ],
            "neg": [
                _claim("丙的命令真实复现", _evidence("print('repro: ok')", out="repro: ok")),
                _claim("丁证据不完整先判 E1", "证据：cmd=`ls`"),
            ],
        },
        "E3": {
            "pos": [
                _claim("批次计数为 12", _evidence("print('records: 13')", out="records: 13")),
                _claim("环境主机名为 `Xylo-9`", _evidence("print('weather: sunny')", out="weather: sunny")),
            ],
            "neg": [
                _claim("输出含 `match-ok`", _evidence("print('match-ok')", out="match-ok")),
                _claim("甲的退出码是假的", _evidence("raise SystemExit(3)", exit_code=0, out="ok")),
            ],
        },
        "E4": {
            "pos": [
                _claim("答案为 42", _evidence("print('answer: 42')", out="answer: 42")),
                _claim("输出含 `token-ok`", _evidence("print('token-ok')", out="token-ok")),
            ],
            "neg": [
                _claim("环境主机名为 `Xylo-9`", _evidence("print('weather: sunny')", out="weather: sunny")),
                _claim("乙的退出码是假的", _evidence("raise SystemExit(3)", exit_code=0, out="ok")),
            ],
        },
    }


class JudgeFiveLevelsTests(TempRootTestCase):
    def setUp(self):
        super().setUp()
        self.cases = _level_cases()

    def test_case_table_meets_card_minimums(self):
        for level in ("E0", "E1", "E2", "E3", "E4"):
            self.assertGreaterEqual(len(self.cases[level]["pos"]), 2, level)
            self.assertGreaterEqual(len(self.cases[level]["neg"]), 2, level)

    def _judged_levels(self, markdown_text):
        judgements = self.judge(markdown_text)
        self.assertEqual(len(judgements), 1, markdown_text)
        return judgements[0].level

    def test_positive_cases_judge_exactly(self):
        for level, table in self.cases.items():
            for md in table["pos"]:
                self.assertEqual(self._judged_levels(md), level,
                                 "level {} positive case:\n{}".format(level, md))

    def test_negative_cases_do_not_judge_this_level(self):
        for level, table in self.cases.items():
            for md in table["neg"]:
                self.assertNotEqual(self._judged_levels(md), level,
                                    "level {} negative case:\n{}".format(level, md))

    def test_ref_form_supported_claim(self):
        (self.root / "note.md").write_text("本文件包含 `ref-anchor-ok` 锚。", encoding="utf-8")
        md = _claim("仓内存在记录文件（`ref-anchor-ok`）", "证据：ref=note.md")
        self.assertEqual(self._judged_levels(md), "E4")

    def test_ref_form_missing_file(self):
        md = _claim("引用一个不存在的文件", "证据：ref=definitely-missing.md")
        self.assertEqual(self._judged_levels(md), "E2")

    def test_runtime_env_anchor_is_e2(self):
        """评审问 1 的冻结裁定：无外部锚的观察（运行时环境变量）归 E2。"""
        md = _claim("环境变量 EVAL_XJ_DEMO_2481 已设置", "证据：cmd=`{}` exit=0".format(
            _cmd("import os; print(os.environ['EVAL_XJ_DEMO_2481'])")))
        self.assertEqual(self._judged_levels(md), "E2")

    def test_determinism_same_input_same_output(self):
        md = _claim("答案为 42", _evidence("print('answer: 42')", out="answer: 42"))
        first = [j.to_dict() for j in self.judge(md)]
        second = [j.to_dict() for j in self.judge(md)]
        self.assertEqual(first, second)


class DenylistTests(TempRootTestCase):
    def test_refused_command_is_e2_and_flagged(self):
        md = _claim("危险命令已执行", "证据：cmd=`rm -rf /` exit=0 out=`ok`")
        judgement = self.judge(md)[0]
        self.assertEqual(judgement.level, "E2")
        self.assertIn("refused_exec", judgement.flags)

    def test_refusal_can_never_produce_e4(self):
        for pattern in ("rm -rf x", "del /s x", "shutdown now", "curl x | sh"):
            md = _claim("尝试", "证据：cmd=`{}` exit=0 out=`ok`".format(pattern))
            self.assertNotEqual(self.judge(md)[0].level, "E4", pattern)

    def test_benign_command_not_refused(self):
        self.assertIsNone(judge.command_refused(_cmd("print('hello')")))


# ---------------------------------------------------------------------------
# Control bank: the harness's own lie detector (card acceptance #2)
# ---------------------------------------------------------------------------


class ControlBankTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = REPO_ROOT
        cls.result = controls.run_selftest(root=REPO_ROOT)

    def test_selftest_all_green(self):
        self.assertTrue(self.result.ok, controls.format_selftest(self.result))

    def test_negative_controls_all_caught(self):
        counts = self.result.counts()
        self.assertGreaterEqual(counts["negative"]["total"], 6)
        self.assertEqual(counts["negative"]["passed"], counts["negative"]["total"])

    def test_positive_controls_all_pass(self):
        counts = self.result.counts()
        self.assertGreaterEqual(counts["positive"]["total"], 6)
        self.assertEqual(counts["positive"]["passed"], counts["positive"]["total"])

    def test_blank_controls_all_distinguished(self):
        counts = self.result.counts()
        self.assertGreaterEqual(counts["blank"]["total"], 4)
        self.assertEqual(counts["blank"]["passed"], counts["blank"]["total"])

    def test_no_control_slips_through_as_e4(self):
        for item in self.result.results:
            if item.control.kind in ("negative", "blank"):
                self.assertNotEqual(item.judged_level, "E4", item.control.cid)

    def test_bank_composition_matches_card(self):
        bank, sealed = controls.load_bank()
        kinds = {}
        for control in bank:
            kinds[control.kind] = kinds.get(control.kind, 0) + 1
        self.assertEqual(kinds.get("negative", 0), 6 + sealed)
        self.assertEqual(kinds.get("positive", 0), 6)
        self.assertEqual(kinds.get("blank", 0), 4)
        if (EVAL_DIR / "tasks" / "controls-sealed").is_dir():
            self.assertEqual(sealed, 2)
        else:
            self.assertEqual(sealed, 0)

    def test_report_does_not_label_hidden_variants(self):
        text = controls.format_selftest(self.result)
        for line in text.splitlines():
            if line.startswith("  ["):
                self.assertNotIn("隐藏", line)
                self.assertNotIn("hidden", line)
                self.assertNotIn("密封", line)

    def test_each_control_block_is_single_claim(self):
        bank, _ = controls.load_bank()
        for control in bank:
            claims = extract.extract_claims(control.block, product=control.cid)
            self.assertEqual(len(claims), 1, control.cid)


# ---------------------------------------------------------------------------
# Paired statistics (frozen analysis plan)
# ---------------------------------------------------------------------------


def _pm(task_id, condition, repetition, counts, covered=None):
    return stats.ProductMetrics(
        task_id=task_id, condition=condition, repetition=repetition,
        counts=dict(counts), unanchored=0, covered=covered,
    )


class StatsTests(unittest.TestCase):
    def test_m1_m2_formulas(self):
        counts = {"E0": 2, "E1": 1, "E2": 1, "E3": 2, "E4": 4}
        # M1 numerator is E2+E3 since prereg v1.2 C5 (effective round 3): the E
        # table always put E2 (unreproducible) on the failure side, the v1.1
        # formula did not, and round 2 showed what that costs - every failure was
        # E2, so M1 read 0% while 58% of arm B's evidence did not reproduce.
        self.assertAlmostEqual(stats.m1_false_verification_rate(counts), 3 / 7)
        self.assertAlmostEqual(stats.m2_unsupported_claim_rate(counts), 3 / 10)

    def test_m1_c5_cases(self):
        # C5: E2 and E3 both count as evidence that does not hold up.
        self.assertAlmostEqual(
            stats.m1_false_verification_rate({"E0": 0, "E1": 0, "E2": 3, "E3": 1, "E4": 6}), 0.4)
        # Nothing reproduces at all -> 1.0, not None (the denominator is not empty).
        self.assertAlmostEqual(
            stats.m1_false_verification_rate({"E0": 0, "E1": 0, "E2": 2, "E3": 0, "E4": 0}), 1.0)
        # Everything reproduces and supports -> 0.0.
        self.assertEqual(
            stats.m1_false_verification_rate({"E0": 0, "E1": 0, "E2": 0, "E3": 0, "E4": 5}), 0.0)
        # Guard against a silent revert to the v1.1 numerator: E2-only must not be 0.
        self.assertNotEqual(
            stats.m1_false_verification_rate({"E0": 0, "E1": 0, "E2": 1, "E3": 0, "E4": 3}), 0.0)

    def test_empty_denominators_are_none_not_zero(self):
        # M1's denominator is the claims-that-claimed-evidence set: with only
        # E0/E1 present it is empty -> None (excluded from pairing, never 0).
        self.assertIsNone(stats.m1_false_verification_rate({"E0": 3, "E1": 1, "E2": 0, "E3": 0, "E4": 0}))
        # M2's denominator is all claims: a lone fully-evidenced claim is a
        # legitimate 0.0, not an empty denominator.
        self.assertEqual(stats.m2_unsupported_claim_rate({"E0": 0, "E1": 0, "E2": 1, "E3": 0, "E4": 0}), 0.0)
        # All-claims-empty is the only empty M2 denominator.
        self.assertIsNone(stats.m2_unsupported_claim_rate({"E0": 0, "E1": 0, "E2": 0, "E3": 0, "E4": 0}))

    def test_pooling_reps_before_pairing(self):
        records = [
            _pm("T01", "A", 1, {"E2": 0, "E3": 1, "E4": 1}),
            _pm("T01", "A", 2, {"E2": 0, "E3": 1, "E4": 1}),
            _pm("T01", "A", 3, {"E2": 0, "E3": 0, "E4": 2}),
            _pm("T01", "B", 1, {"E0": 2, "E3": 0, "E4": 0}),
            _pm("T01", "B", 2, {"E0": 0, "E3": 0, "E4": 0}),
            _pm("T01", "B", 3, {"E0": 0, "E3": 0, "E4": 0}),
        ]
        diffs, excluded = stats.paired_task_diffs(records, "M1")
        # A pooled: E3=2 / (E3=2+E4=4) = 1/3; B pooled: empty denominator -> excluded
        self.assertEqual(diffs, [])
        self.assertEqual(excluded, 1)

    def test_paired_diff_with_both_sides_present(self):
        records = [
            _pm("T01", "A", 1, {"E3": 1, "E4": 3}),
            _pm("T01", "A", 2, {"E3": 1, "E4": 3}),
            _pm("T01", "B", 1, {"E0": 2, "E3": 0, "E4": 2}),
            _pm("T01", "B", 2, {"E0": 2, "E3": 0, "E4": 2}),
            _pm("T02", "A", 1, {"E3": 0, "E4": 2}),
            _pm("T02", "A", 2, {"E3": 0, "E4": 2}),
            _pm("T02", "B", 1, {"E0": 4, "E3": 0, "E4": 0}),
            _pm("T02", "B", 2, {"E0": 4, "E3": 0, "E4": 0}),
        ]
        # T01: A=0.25, B=0 -> +0.25; T02: A=0.0, B excluded (M1 denominator
        # empty in B: only E0) -> excluded. M2: T01 A=0 B=0.5 -> -0.5;
        # T02 A=0, B=1.0 -> -1.0.
        m1_diffs, m1_excluded = stats.paired_task_diffs(records, "M1")
        self.assertEqual([(t, round(d, 3)) for t, d in m1_diffs], [("T01", 0.25)])
        self.assertEqual(m1_excluded, 1)
        m2_diffs, m2_excluded = stats.paired_task_diffs(records, "M2")
        self.assertEqual([(t, round(d, 3)) for t, d in m2_diffs], [("T01", -0.5), ("T02", -1.0)])
        self.assertEqual(m2_excluded, 0)

    def test_bootstrap_deterministic_and_seed_sensitive(self):
        values = [0.1, 0.2, 0.3, 0.4]
        first = stats.bootstrap_ci(values, seed=12345)
        second = stats.bootstrap_ci(values, seed=12345)
        self.assertEqual(first, second)
        lo, mean, hi = first[1], first[0], first[2]
        self.assertLessEqual(lo, mean)
        self.assertLessEqual(mean, hi)

    def test_constant_values_collapse_ci(self):
        mean, lo, hi = stats.bootstrap_ci([0.2] * 10, seed=7)
        self.assertAlmostEqual(mean, 0.2)
        self.assertAlmostEqual(lo, 0.2)
        self.assertAlmostEqual(hi, 0.2)

    def test_minimal_effect_rule(self):
        strong = stats.Endpoint(metric="M1", diffs=[("T%02d" % i, 0.2) for i in range(30)])
        strong.analyse(seed=1)
        self.assertTrue(strong.meets_minimal_effect)
        weak = stats.Endpoint(metric="M1", diffs=[("T%02d" % i, 0.05) for i in range(30)])
        weak.analyse(seed=1)
        self.assertFalse(weak.meets_minimal_effect)

    def test_verdict_phrases_respect_wording_discipline(self):
        weak = stats.Endpoint(metric="M1", diffs=[("T01", 0.05)]).analyse(seed=1)
        self.assertIn("未检出", weak.verdict_phrase())
        strong = stats.Endpoint(metric="M1", diffs=[("T%02d" % i, 0.2) for i in range(30)]).analyse(seed=1)
        self.assertIn("预注册条件", strong.verdict_phrase())
        empty = stats.Endpoint(metric="M1", diffs=[]).analyse(seed=1)
        self.assertIn("样本不足", empty.verdict_phrase())

    def test_coverage_by_condition(self):
        records = [
            _pm("T01", "A", 1, {"E4": 1}, covered=True),
            _pm("T01", "B", 1, {"E0": 1}, covered=True),
            _pm("T02", "A", 1, {"E4": 1}, covered=False),
        ]
        coverage = stats.coverage_by_condition(records)
        self.assertEqual(coverage["A"], (1, 2))
        self.assertEqual(coverage["B"], (1, 1))

    def test_unanchored_counted(self):
        records = [stats.product_metrics("T01", "A", 1, [], covered=None)]
        self.assertEqual(records[0].unanchored, 0)


# ---------------------------------------------------------------------------
# Blinding: seed custody, package sealing, unblind hard-stop
# ---------------------------------------------------------------------------


def _make_run_dir(tmp: Path, n_tasks: int = 2) -> Path:
    run_dir = tmp / "run"
    (run_dir / "products").mkdir(parents=True)
    entries = []
    index = 0
    for task_number in range(1, n_tasks + 1):
        for condition in ("A", "B"):
            index += 1
            name = "T%02d-%s-r1.md" % (task_number, condition)
            (run_dir / "products" / name).write_text(
                "- [已验证] 示例断言 %d，无证据行。\n" % index, encoding="utf-8")
            entries.append({
                "key": name,
                "task_id": "T%02d" % task_number,
                "condition": condition,
                "repetition": 1,
                "product": "products/" + name,
                "coverage": True,
            })
    (run_dir / "run-data.json").write_text(
        json.dumps({"entries": entries}, ensure_ascii=False), encoding="utf-8")
    return run_dir


class BlindTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_shuffle_deterministic_and_seed_sensitive(self):
        items = ["k%02d" % i for i in range(12)]
        first = blind.derive_shuffle("aa" * 32, items)
        again = blind.derive_shuffle("aa" * 32, items)
        other = blind.derive_shuffle("bb" * 32, items)
        self.assertEqual(first, again)
        self.assertEqual(sorted(first), items)
        self.assertNotEqual(first, other)

    def test_seed_is_cryptographic(self):
        self.assertNotEqual(blind.generate_seed(), blind.generate_seed())
        self.assertEqual(len(blind.generate_seed()), 64)

    def test_package_strips_all_condition_metadata(self):
        run_dir = _make_run_dir(self.tmp)
        out_dir = self.tmp / "pkg"
        _package, key_path, mapping = blind.build_package(run_dir, out_dir, seed="ab" * 32)

        def keys_of(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    yield key
                    yield from keys_of(value)
            elif isinstance(node, list):
                for item in node:
                    yield from keys_of(item)

        banned = {"condition", "task_id", "repetition", "key", "source_product"}
        manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(set(keys_of(manifest)) & banned, set())
        for name in ("claims.json", "metrics-blind.json"):
            payload = json.loads((out_dir / name).read_text(encoding="utf-8"))
            self.assertEqual(set(keys_of(payload)) & banned, set(), name)
        # The key holds everything, keyed by P-codes.
        self.assertEqual(len(mapping), 4)
        self.assertEqual({row["code"] for row in mapping}, {"P001", "P002", "P003", "P004"})
        key_payload = json.loads(key_path.read_text(encoding="utf-8"))
        self.assertTrue(
            {"condition", "task_id", "repetition", "key"}.issubset(set(keys_of(key_payload))))

    def test_unblind_requires_matching_key(self):
        run_dir = _make_run_dir(self.tmp)
        out_dir = self.tmp / "pkg"
        blind.build_package(run_dir, out_dir, seed="ab" * 32)
        other_key = self.tmp / "wrong.json"
        other_key.write_text(json.dumps({"seed": "ff" * 32, "mapping": []}), encoding="utf-8")
        with self.assertRaises(ValueError):
            blind.unblind(out_dir, other_key)

    def test_unblind_returns_full_table(self):
        run_dir = _make_run_dir(self.tmp)
        out_dir = self.tmp / "pkg"
        _package, key_path, _mapping = blind.build_package(run_dir, out_dir, seed="ab" * 32)
        rows = blind.unblind(out_dir, key_path)
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertIn(row["condition"], ("A", "B"))
            self.assertIn("task_id", row)


# ---------------------------------------------------------------------------
# Reports: blind stage and unblinded fragment
# ---------------------------------------------------------------------------


class ReportTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        run_dir = _make_run_dir(self.tmp)
        self.run_dir = run_dir  # XJ-20261027-001: sealed-package tests rebuild from it
        self.out_dir = self.tmp / "pkg"
        self.package, self.key_path, _mapping = blind.build_package(
            run_dir, self.out_dir, seed="ab" * 32)

    def test_blind_report_contains_limitations_and_discipline(self):
        text = report.blind_report(self.package, REPO_ROOT)
        for limitation in report.FIVE_LIMITATIONS:
            self.assertIn(limitation, text)
        self.assertIn("预注册条件下的对照证据", text)
        self.assertIn("未检出差异", text)  # the frozen fallback wording
        self.assertIn("P001", text)
        self.assertNotIn("T01-A", text)  # pseudonymized end to end
        self.assertNotIn("条件 A：", text)

    def test_blind_report_failure_appendix_lists_every_miss(self):
        text = report.blind_report(self.package, REPO_ROOT)
        self.assertIn("失败样本附录", text)

    def test_unblind_fragment_shape(self):
        text = report.unblind_fragment(self.package, self.key_path, REPO_ROOT)
        self.assertIn("解盲附录", text)
        self.assertIn("M1", text)
        self.assertIn("M2", text)
        self.assertIn("未运行", text)  # M3 section without run data
        self.assertIn("T01", text)  # unblinded: task ids visible again

    def test_package_seals_judgements_and_root_state(self):
        """XJ-20261027-001: packing with a root seals the E-levels and records
        the repository state they were formed against."""
        out_dir = self.tmp / "pkg-sealed"
        blind.build_package(self.run_dir, out_dir, seed="cd" * 32, root=REPO_ROOT)
        self.assertTrue((out_dir / "judgements-blind.json").is_file())
        self.assertTrue((out_dir / "root-state.json").is_file())

        sealed = json.loads((out_dir / "judgements-blind.json").read_text(encoding="utf-8"))
        self.assertTrue(sealed)
        for code, rows in sealed.items():
            self.assertRegex(code, r"^P\d{3}$")
            for row in rows:
                self.assertIn(row["level"], {"E0", "E1", "E2", "E3", "E4"})
                keys = set(json.dumps(row, ensure_ascii=False).split('"'))
                for forbidden in ("condition", "task_id", "repetition"):
                    self.assertNotIn(forbidden, keys,
                                     f"sealed judgement leaks {forbidden}")

    def test_sealed_judgements_short_circuit_rejudging(self):
        """A sealed package must not touch the repository again: if re-judging
        were attempted the patched judge_markdown below would explode."""
        out_dir = self.tmp / "pkg-sealed2"
        blind.build_package(self.run_dir, out_dir, seed="ef" * 32, root=REPO_ROOT)
        original = report.judge.judge_markdown
        report.judge.judge_markdown = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("re-judged a sealed package"))
        try:
            judged = report.judge_package(out_dir, REPO_ROOT)
        finally:
            report.judge.judge_markdown = original
        self.assertTrue(judged)
        first = next(iter(judged.values()))[0]
        self.assertIn(getattr(first, "level"), {"E0", "E1", "E2", "E3", "E4"})

    def test_drift_against_recorded_root_hard_stops(self):
        """The measured failure: -50.0% at one commit, -48.3% after the next
        merge. A package sealed against a different HEAD must refuse."""
        out_dir = self.tmp / "pkg-drift"
        blind.build_package(self.run_dir, out_dir, seed="ab" * 31 + "cd", root=REPO_ROOT)
        state_path = out_dir / "root-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["git_head"] = "0" * 40
        state_path.write_text(json.dumps(state), encoding="utf-8")

        with self.assertRaises(ValueError) as ctx:
            report.blind_report(out_dir, REPO_ROOT)
        self.assertIn("仓库状态与打包时不一致", str(ctx.exception))

        # Explicit opt-in still works, so a reviewer can cite both numbers.
        text = report.blind_report(out_dir, REPO_ROOT, allow_drift=True)
        self.assertIn("P001", text)

    def test_legacy_package_without_seal_still_rejudges(self):
        """Packages built before sealing existed must keep working."""
        self.assertIsNone(report.sealed_judgements(self.package))
        judged = report.judge_package(self.package, REPO_ROOT)
        self.assertTrue(judged)

    def test_product_seal_is_recorded_and_verified(self):
        """A1 (XJ-20261027-002): the package records product hashes, and a
        one-byte change to a packaged product must stop the report."""
        out_dir = self.tmp / "pkg-seal"
        blind.build_package(self.run_dir, out_dir, seed="aa" * 32, root=REPO_ROOT)
        manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest.get("product_sha256"), "no product seal recorded")

        first_code = sorted(manifest["products"])[0]
        product = out_dir / "products" / manifest["products"][first_code]
        data = bytearray(product.read_bytes())
        data[0] ^= 0x01
        product.write_bytes(bytes(data))

        with self.assertRaises(ValueError) as ctx:
            report.blind_report(out_dir, REPO_ROOT)
        self.assertIn("产物与打包时的封签不一致", str(ctx.exception))
        # Tampering is not drift: the drift escape hatch must not bypass it.
        with self.assertRaises(ValueError):
            report.blind_report(out_dir, REPO_ROOT, allow_drift=True)

    def test_report_body_carries_the_snapshot_line(self):
        """A2: the snapshot belongs in the body, not only on stderr."""
        out_dir = self.tmp / "pkg-snap"
        blind.build_package(self.run_dir, out_dir, seed="bb" * 32, root=REPO_ROOT)
        text = report.blind_report(out_dir, REPO_ROOT)
        self.assertIn("判定快照", text)
        self.assertIn("git_head=", text)
        self.assertNotIn("无产物封签", text)

    def test_report_body_carries_the_drift_line_when_allowed(self):
        out_dir = self.tmp / "pkg-drift-body"
        blind.build_package(self.run_dir, out_dir, seed="cc" * 32, root=REPO_ROOT)
        state_path = out_dir / "root-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["git_head"] = "1" * 40
        state_path.write_text(json.dumps(state), encoding="utf-8")

        text = report.blind_report(out_dir, REPO_ROOT, allow_drift=True)
        self.assertIn("⚠ 漂移", text)
        self.assertIn("git_head=", text)

    def test_legacy_package_header_says_no_product_seal(self):
        text = report.blind_report(self.package, REPO_ROOT)
        self.assertIn("无产物封签", text)

    def test_drifted_report_body_carries_both_heads_citation_rule(self):
        """XJ-20261029-001 D2 (027-001 A2): a number printed under
        --allow-drift must be unquotable as the single truth - the body
        carries the pairing rule with BOTH the packaged and the current
        head, so a reader cannot cite one without tripping over the other."""
        out_dir = self.tmp / "pkg-drift-cite"
        blind.build_package(self.run_dir, out_dir, seed="dd" * 32, root=REPO_ROOT)
        state_path = out_dir / "root-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        packaged_head = str(state["git_head"])[:12]
        state["git_head"] = "2" * 40
        state_path.write_text(json.dumps(state), encoding="utf-8")

        text = report.blind_report(out_dir, REPO_ROOT, allow_drift=True)
        self.assertIn("引用规则", text)
        self.assertIn(packaged_head, text)
        # Both slots of the pairing rule must carry a head value. The two
        # heads CAN legitimately be equal (drift may be triggered by the
        # dirty flag alone), so we assert the rule line exists and names the
        # packaged head, not that the two heads differ.
        self.assertRegex(text, r"引用规则.*?打包时刻 `\w{12}`.*?当前仓库为 `\w{12}`", )

    def test_clean_report_has_no_citation_rule_line(self):
        """XJ-20261029-001 D4: the pairing rule belongs to drift scenarios
        only - a clean report must not grow the extra line."""
        out_dir = self.tmp / "pkg-clean-norule"
        blind.build_package(self.run_dir, out_dir, seed="ee" * 32, root=REPO_ROOT)
        text = report.blind_report(out_dir, REPO_ROOT)
        self.assertNotIn("引用规则", text)
        self.assertIn("判定快照", text)

    def _make_run_dir_with_failures(self, name: str = "run-fail") -> Path:
        """A run dir whose products contain E2 judgements.

        The stock fixture judges all-E0, and the failure appendix only lists
        E1/E2/E3 -- which is exactly why the sealed-view crash slipped past 433
        green tests (XJ-20261027-002 C1, AgnesCode's finding).
        """
        run_dir = self.tmp / name
        (run_dir / "products").mkdir(parents=True)
        entries = []
        for task_number, condition in ((1, "A"), (1, "B"), (2, "A"), (2, "B")):
            key = "T%02d-%s-r1" % (task_number, condition)
            body = (
                "- [已验证] 示例断言：本行声称某命令退出码为 0。\n"
                '  证据：cmd=`python -c "import sys; sys.exit(1)"` exit=0 out=`ok`\n'
            )
            (run_dir / "products" / (key + ".md")).write_text(body, encoding="utf-8")
            entries.append({
                "key": key,
                "task_id": "T%02d" % task_number,
                "condition": condition,
                "repetition": 1,
                "product": "products/" + key + ".md",
                "coverage": True,
            })
        (run_dir / "run-data.json").write_text(
            json.dumps({"entries": entries}, ensure_ascii=False), encoding="utf-8")
        return run_dir

    def test_sealed_package_with_failures_renders_the_appendix(self):
        """C1: a sealed package containing E2s must produce a report, not a crash."""
        run_dir = self._make_run_dir_with_failures()
        out_dir = self.tmp / "pkg-fail"
        blind.build_package(run_dir, out_dir, seed="dd" * 32, root=REPO_ROOT)

        text = report.blind_report(out_dir, REPO_ROOT)  # used to raise AttributeError
        self.assertIn("失败样本附录", text)
        # The appendix renders '- **P001** 行 1 判 E2：断言「…」——…'; the source
        # line number is precisely the field the sealed view was missing.
        self.assertIn("行 1 判 E2", text)

    def test_sealed_claim_exposes_every_claim_field(self):
        """C1/A2: the sealed view must mirror Claim.to_dict() -- hand-picking
        fields is what broke the appendix."""
        from schema import Claim  # local: same style as the other schema imports

        sample = Claim(text="t", source_line=7, product="P001")
        expected = set(sample.to_dict())
        run_dir = self._make_run_dir_with_failures("run-fields")
        out_dir = self.tmp / "pkg-fields"
        blind.build_package(run_dir, out_dir, seed="ee" * 32, root=REPO_ROOT)

        sealed = report.sealed_judgements(out_dir)
        self.assertIsNotNone(sealed)
        first = next(iter(sealed.values()))[0]
        for field_name in expected:
            self.assertTrue(hasattr(first.claim, field_name),
                            f"sealed claim is missing Claim.{field_name}")
        self.assertEqual(first.claim.source_line, 1)

    def test_unblind_fragment_rejects_wrong_key(self):
        wrong = self.tmp / "wrong.json"
        wrong.write_text(json.dumps({"seed": "ff" * 32, "mapping": []}), encoding="utf-8")
        with self.assertRaises(ValueError):
            report.unblind_fragment(self.package, wrong, REPO_ROOT)

    def test_summary_matches_its_own_per_code_table(self):
        """Self-consistency guard (XJ-20261026-001).

        Measured on the round-2 package: three report captures said 158 claims
        while their own P-code table summed to 258, and five later runs said 258.
        The discrepancy was never explained, so the cheapest thing that would
        have caught it at once is this invariant: the summary block must equal
        the sum of the table it printed above itself.
        """
        text = report.blind_report(self.package, REPO_ROOT)

        table_rows = [line for line in text.splitlines()
                      if line.startswith("| P") and line.count("|") >= 9]
        self.assertTrue(table_rows, "no P-code rows in the report")
        table_sum = 0
        level_sums = {"E0": 0, "E1": 0, "E2": 0, "E3": 0, "E4": 0}
        for row in table_rows:
            cols = [c.strip() for c in row.strip().strip("|").split("|")]
            try:
                claims = int(cols[1])
            except (ValueError, IndexError):
                continue  # the "| P码 | 断言数 |" header row
            table_sum += claims
            for offset, level in enumerate(("E0", "E1", "E2", "E3", "E4"), start=2):
                level_sums[level] += int(cols[offset])

        summary_total = None
        summary_levels = {}
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("- 断言总数"):
                summary_total = int(stripped.split("：")[-1].strip())
            for level in level_sums:
                if stripped.startswith(f"- {level}（"):
                    summary_levels[level] = int(stripped.split("：")[-1].strip())

        self.assertIsNotNone(summary_total, "summary block missing")
        self.assertEqual(table_sum, summary_total,
                         "summary total disagrees with the P-code table it printed")
        for level, expected in level_sums.items():
            self.assertEqual(expected, summary_levels.get(level),
                             f"{level} summary disagrees with the P-code table")

    def test_m3_section_reads_run_data(self):
        run_dir = self.tmp / "run2"
        run_dir.mkdir()
        (run_dir / "m3.json").write_text(json.dumps({"total": 12, "rejected": 11}), encoding="utf-8")
        text = report._m3_section(run_dir)
        self.assertIn("11/12", "\n".join(text))


# ---------------------------------------------------------------------------
# Task schema (frozen 30 x 10/10/10)
# ---------------------------------------------------------------------------


class TaskSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks, cls.errors = load_task_dir(EVAL_DIR / "tasks")

    def test_thirty_tasks_three_layers(self):
        self.assertEqual(self.errors, [])
        self.assertEqual(len(self.tasks), 30)
        from schema import LAYER_COUNTS
        for layer, want in LAYER_COUNTS.items():
            got = sum(1 for task in self.tasks if task.layer == layer)
            self.assertEqual(got, want, layer)

    def test_ids_unique_and_ordered(self):
        ids = [task.id for task in self.tasks]
        self.assertEqual(ids, ["T%02d" % i for i in range(1, 31)])

    def test_every_task_has_working_acceptance(self):
        for task in self.tasks:
            if task.acceptance.type == "answer":
                self.assertTrue(task.acceptance.value.strip(), task.id)
            else:
                self.assertIn("python", task.acceptance.command, task.id)
                self.assertEqual(task.acceptance.expect_exit, 0, task.id)

    def test_validate_task_rejects_bad_shapes(self):
        base = {
            "id": "T01", "layer": "fact", "title": "标题",
            "prompt": "足够长的任务说明文本", "product": "T01.md",
            "acceptance": {"type": "answer", "value": "MIT"},
        }
        task, errors = validate_task(base)
        self.assertEqual(errors, [])
        self.assertIsNotNone(task)
        _task, errors = validate_task({**base, "layer": "wrong"})
        self.assertTrue(any("layer" in e for e in errors))
        _task, errors = validate_task({**base, "acceptance": {"type": "vibe"}})
        self.assertTrue(any("acceptance" in e for e in errors))
        _task, errors = validate_task({**base, "id": "X1"})
        self.assertTrue(any("id" in e for e in errors))
        _task, errors = validate_task({
            **base,
            "acceptance": {"type": "command", "command": "ls", "expect_exit": True},
        })
        self.assertTrue(any("expect_exit" in e for e in errors))


# ---------------------------------------------------------------------------
# Static content guards: prereg freeze, template, wording discipline
# ---------------------------------------------------------------------------


class PreregAndTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prereg = (REPO_ROOT / "docs" / "eval-prereg.md").read_text(encoding="utf-8")
        cls.template = (REPO_ROOT / "docs" / "eval-report-v1.md").read_text(encoding="utf-8")

    def test_prereg_has_version_and_freeze_date(self):
        self.assertIn("1.0.0", self.prereg)
        self.assertIn("2026-10-24", self.prereg)
        self.assertIn("冻结日期", self.prereg)

    def test_prereg_has_six_freeze_layers(self):
        for heading in ("指标语义", "主次指标与最小效应", "采样与留出",
                        "排除与重试", "分析方案", "版本与变更"):
            self.assertIn(heading, self.prereg, heading)

    def test_prereg_freezes_card_sections_verbatim(self):
        self.assertIn("附录 A：卡内「测评对象与指标」原文冻结", self.prereg)
        self.assertIn("附录 B：卡内「实验设计」原文冻结", self.prereg)
        self.assertIn("M1 假验证率 = E3 / (E2+E3+E4)", self.prereg)
        self.assertIn("乱序混洗后", self.prereg)

    def test_template_contains_five_limitations_verbatim(self):
        for limitation in report.FIVE_LIMITATIONS:
            self.assertIn(limitation, self.template)

    def test_template_has_required_sections(self):
        for section in ("配对差表", "失败样本附录", "局限性", "解盲附录", "M3"):
            self.assertIn(section, self.template, section)

    def test_wording_discipline_in_docs_and_generator(self):
        """措辞铁律 guard: the banned outcome phrases may appear ONLY inside
        the ban statements themselves (lines that also contain 禁/禁止)."""
        checked = [
            self.prereg,
            self.template,
            (EVAL_DIR / "report.py").read_text(encoding="utf-8"),
            (EVAL_DIR / "stats.py").read_text(encoding="utf-8"),
        ]
        for text in checked:
            for line in text.splitlines():
                if ("证明有效" in line) or ("证明降低" in line):
                    self.assertIn("禁", line, line)

    def test_documents_state_the_evidence_wording(self):
        for text in (self.prereg, self.template):
            self.assertIn("预注册条件下的对照证据", text)

    def test_judge_modules_have_no_llm_or_network_imports(self):
        """Constraint 2: E0-E4 judging is pure rules -- no LLM, no network."""
        banned = {"requests", "urllib", "urllib2", "http", "httpx", "socket",
                  "ssl", "openai", "anthropic", "aiohttp", "telnetlib",
                  "ftplib", "smtplib", "xmlrpc", "websocket", "grpc"}
        for path in sorted(EVAL_DIR.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root = alias.name.split(".")[0]
                        self.assertNotIn(root, banned, "{}: {}".format(path.name, alias.name))
                elif isinstance(node, ast.ImportFrom) and node.module:
                    root = node.module.split(".")[0]
                    self.assertNotIn(root, banned, "{}: {}".format(path.name, node.module))


# ---------------------------------------------------------------------------
# M3 probes: the harness observing the real gate tools
# ---------------------------------------------------------------------------


def _honest_verdict():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return {
        "id": "OC-20260101-001",
        "artifact": "src/pipeline.py",
        "verdict": "PASS",
        "blockers": 0,
        "conditions": [],
        "independent": True,
        "verifier": "reviewer@acme",
        "ts": now.isoformat().replace("+00:00", "Z"),
        "evidence": ["pytest -q -> 27 passed", "linter exit 0"],
    }


WELL_FORMED_CARD = """# TASK OC-20260101-001: build the probe fixture

## Context
Probe fixture for the eval harness M3 path.

## Deliverables
- src/thing.py

## Owned files
- src/thing.py

## Constraints
- do not touch other dirs

## Acceptance
- pytest exits 0

## Review questions
1. Is the boundary right?

## Review handoff
Write to REVIEW-OC-20260101-001.md

## Status
OPEN
"""

BROKEN_CARD = "这根本不是一张卡，没有任何协议要求的章节。"


class M3ProbeTests(unittest.TestCase):
    def test_gate_accepts_honest_verdict(self):
        rejected, output = controls.probe_gate_rejection(_honest_verdict())
        self.assertFalse(rejected, output)

    def test_gate_rejects_fail_verdict(self):
        payload = _honest_verdict()
        payload["verdict"] = "FAIL"
        rejected, output = controls.probe_gate_rejection(payload)
        self.assertTrue(rejected, output)

    def test_gate_rejects_nonindependent_verdict(self):
        payload = _honest_verdict()
        payload["independent"] = False
        rejected, _output = controls.probe_gate_rejection(payload)
        self.assertTrue(rejected)

    def test_lint_accepts_well_formed_card(self):
        rejected, output = controls.probe_lint_rejection("OC-20260101-001", WELL_FORMED_CARD)
        self.assertFalse(rejected, output)

    def test_lint_rejects_broken_card(self):
        # NAMESPACE_MISSING is an ERROR-level finding: a card file whose name
        # is not <NS>-YYYYMMDD-NNN.md cannot pass, which is the deterministic
        # rejection this probe asserts.
        rejected, output = controls.probe_lint_rejection("notacard", BROKEN_CARD)
        self.assertTrue(rejected, output)
        self.assertIn("NAMESPACE_MISSING", output)


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------


class CliTests(unittest.TestCase):
    def _main(self, argv):
        with contextlib.redirect_stdout(io.StringIO()) as out, \
                contextlib.redirect_stderr(io.StringIO()):
            code = eval_run.main(argv)
        return code, out.getvalue()

    def test_dry_run_passes(self):
        code, output = self._main(["--dry-run"])
        self.assertEqual(code, eval_run.EXIT_OK, output)
        self.assertIn("DRY-RUN: PASS", output)

    def test_selftest_passes(self):
        code, output = self._main(["--selftest"])
        self.assertEqual(code, eval_run.EXIT_OK, output)
        self.assertIn("SELFTEST: PASS", output)

    def test_tasks_listing_passes(self):
        code, output = self._main(["--tasks"])
        self.assertEqual(code, eval_run.EXIT_OK, output)
        self.assertIn("T30 [process]", output)

    def test_judge_single_fixture(self):
        fixture = str(EVAL_DIR / "fixtures" / "fixture-e0.md")
        code, output = self._main(["--judge", fixture])
        self.assertEqual(code, eval_run.EXIT_OK, output)
        payload = json.loads(output)
        self.assertEqual(payload["pooled_counts"]["E0"], 2)

    def test_no_mode_is_usage_error(self):
        code, _output = self._main([])
        self.assertEqual(code, eval_run.EXIT_USAGE)

    def test_judge_missing_path_is_usage_error(self):
        code, _output = self._main(["--judge", "Z:/no/such/file.md"])
        self.assertEqual(code, eval_run.EXIT_USAGE)

    def test_package_invalid_run_dir_is_usage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "not-a-run-dir"
            empty.mkdir()
            out_dir = Path(tmp) / "out"
            code, _output = self._main(["--package", str(empty), "--out", str(out_dir)])
            self.assertEqual(code, eval_run.EXIT_USAGE)
            self.assertFalse(out_dir.exists())

    def test_unblind_with_wrong_key_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            run_dir = _make_run_dir(tmp_path)
            out_dir = tmp_path / "pkg"
            blind.build_package(run_dir, out_dir, seed="ab" * 32)
            wrong = tmp_path / "wrong.json"
            wrong.write_text(json.dumps({"seed": "ff" * 32, "mapping": []}), encoding="utf-8")
            code, _output = self._main(["--unblind", str(out_dir), str(wrong)])
            self.assertEqual(code, eval_run.EXIT_USAGE)

    def test_package_and_report_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            run_dir = _make_run_dir(tmp_path)
            out_dir = tmp_path / "pkg"
            package, key_path, _mapping = blind.build_package(
                run_dir, out_dir, seed=blind.generate_seed())
            self.assertTrue(key_path.is_file())
            with contextlib.redirect_stdout(io.StringIO()) as captured:
                self.assertEqual(eval_run.main(["--report", str(package)]), eval_run.EXIT_OK)
            self.assertIn("P001", captured.getvalue())


if __name__ == "__main__":
    unittest.main()
