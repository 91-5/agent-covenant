"""Report generation: blind report (adjudication stage) and the unblinded
paired analysis (sir, after the report is finalized).

Two stages, because the discipline demands it (constraint 3/4 + prereg §6):

1. **Blind report** -- built from the package alone: per-P-code judgement
   tables, pooled level distribution, the FULL failure appendix (失败样本是
   资产; aggregate-only reports are forbidden), and the five frozen
   limitations. No condition information exists in this stage, so none can
   leak.
2. **Unblind fragment** -- requires the sealed key (sir's custody). Joins
   P-codes with task/condition/rep, runs the frozen paired analysis, emits
   the 配对差表 + CI + M3 + coverage section for the final report.

Wording discipline is mechanical here: the generator's verdict phrases come
from stats.Endpoint.verdict_phrase(), which only ever says 未检出/检出 under
预注册条件 -- the module has no sentence containing 证明 and a static test
keeps it that way.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import judge
import stats
from schema import LEVEL_NAMES

#: The five mandatory limitations, verbatim (card D5). Any generated report
#: and the report template must contain these exact five lines.
FIVE_LIMITATIONS = (
    "1. 样本小：30 任务 × 2 条件 × 3 重复远低于能精确估计小效应的样本量，"
    "置信区间宽，未达最小效应不等于无差异。",
    "2. 任务构造：任务由团队自建并自标注标准答案，构造偏差可能同时影响"
    "两个条件，配对设计只能缓解、不能消除。",
    "3. 代理指标：E0-E4 判定测的是过程诚信（断言-证据链完整性），"
    "不是知识正确性；harness 不验证断言内容为真。",
    "4. 单 adjudicator：盲化判定由唯一评审员承担，其系统偏好无法在"
    "本设计内交叉验证。",
    "5. 同执行者：两个条件由同一执行者完成，执行者对假设的预期可能"
    "泄漏到产出中，只能靠盲化与负对照部分约束。",
)

BLIND_STAGE_HEADER = "预注册条件下的对照证据（盲态阶段报告）"


def _fmt_pct(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


class _SealedClaim:
    """Read-through view over a sealed claim dict.

    Mirrors every field of ``schema.Claim.to_dict()``. Hand-picking fields is
    how the failure appendix broke: the sealed view exposed ``text`` only, and
    the appendix reads ``source_line`` too, so --report crashed on any sealed
    package that actually contained a failing judgement (XJ-20261027-002 C1).
    Tests did not catch it because every fixture judged all-E4, leaving the
    appendix loop empty.
    """

    #: Field contract: the report may read any attribute listed here. Kept in
    #: sync with schema.Claim by test_sealed_claim_exposes_every_claim_field.
    def __init__(self, data: Dict[str, object]) -> None:
        self.text = str(data.get("text") or "")
        raw_line = data.get("source_line")
        try:
            self.source_line = int(raw_line) if raw_line is not None else 0
        except (TypeError, ValueError):
            self.source_line = 0
        self.product = str(data.get("product") or "")
        self.anchors = list(data.get("anchors") or [])
        self.unanchored = bool(data.get("unanchored"))
        self.evidence = data.get("evidence")


class _SealedJudgement:
    """Attribute view over a sealed judgement dict.

    Same attributes the report already reads from ClaimJudgement
    (``level`` / ``flags`` / ``detail`` / ``observation`` / ``claim.text``), so
    the report code does not branch on where the judgement came from.
    """

    def __init__(self, data: Dict[str, object]) -> None:
        self.level = str(data.get("level") or "")
        self.flags = list(data.get("flags") or [])
        self.detail = str(data.get("detail") or "")
        self.observation = str(data.get("observation") or "")
        self.claim = _SealedClaim(data.get("claim") or {})  # type: ignore[arg-type]


def sealed_judgements(package_dir: Path) -> Optional[Dict[str, List]]:
    """Judgements sealed at packaging time, or None for a legacy package."""
    path = package_dir / "judgements-blind.json"
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        code: [_SealedJudgement(row) for row in rows]
        for code, rows in payload.items()
    }


def check_product_seal(package_dir: Path) -> None:
    """Verify every packaged product against the manifest's hashes.

    A1 (XJ-20261027-002): sealed judgements are returned without re-reading the
    products, so an edit after packaging would leave them silently stale. A
    mismatch here is tampering or a broken package, not repository drift -- it
    gets no --allow-drift escape hatch.

    Legacy packages carry no ``product_sha256``; they are accepted and the
    report header says the cross-check was not enabled.
    """
    import blind as blind_mod

    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    recorded = manifest.get("product_sha256")
    if not recorded:
        return
    products_dir = package_dir / "products"
    bad = []
    for code, expected in sorted(recorded.items()):
        name = manifest["products"].get(code)
        if not name:
            bad.append(f"{code}: missing from manifest products")
            continue
        path = products_dir / name
        if not path.is_file():
            bad.append(f"{code}: file missing ({name})")
            continue
        actual = blind_mod.file_sha256(path)
        if actual != expected:
            bad.append(f"{code}: {expected[:12]} -> {actual[:12]}")
    if bad:
        raise ValueError(
            "产物与打包时的封签不一致（" + "; ".join(bad[:5]) +
            ("…" if len(bad) > 5 else "") +
            "）：密封判定描述的是打包当时的产物字节，产物被改动后判定即失效。"
            "本检查不提供 --allow-drift 开关（篡改不等于仓库漂移）。"
        )


def product_seal_status(package_dir: Path) -> bool:
    """True when the package carries product hashes (cross-check enabled)."""
    manifest_path = package_dir / "manifest.json"
    if not manifest_path.is_file():
        return False
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return bool(manifest.get("product_sha256"))


def snapshot_lines(package_dir: Path, root: Path, drift: Optional[str]) -> List[str]:
    """A2: the snapshot (and any drift) must live in the body, not only stderr.

    Someone who reads only the report must be unable to quote a drifted number
    as if it were the single truth.
    """
    lines: List[str] = []
    state_path = package_dir / "root-state.json"
    current_head: Optional[str] = None
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        head = str(state.get("git_head") or "unknown")[:12]
        lines.append(
            f"- 判定快照：`git_head={head}`（dirty={bool(state.get('dirty'))}）——"
            f"本文件全部数字均为该仓库状态下的密封判定值"
        )
    if drift:
        lines.append(f"- **⚠ 漂移**：{drift}")
        # XJ-20261029-001 D2 (027-001 A2): when a drifted number was printed
        # under --allow-drift, the body must carry the pairing rule with BOTH
        # heads. The recorded head is already in the snapshot line above; the
        # current head comes from the repository the report is being generated
        # against, re-read here so this function stays self-contained.
        import blind as blind_mod  # same local-import style as check_root_state

        current = blind_mod.root_state(root)
        current_head = str(current.get("git_head") or "unknown")[:12]
        lines.append(
            f"- **引用规则**：本文件数字读自打包时刻 `{head}`；当前仓库为 "
            f"`{current_head}`。引用本数字须同时列出两个 commit，缺一即误引。"
        )
    if not product_seal_status(package_dir):
        lines.append("- 本包无产物封签（旧包）：产物与判定的交叉校验未启用")
    return lines


def check_root_state(package_dir: Path, root: Path, allow_drift: bool = False) -> Optional[str]:
    """Compare the packaging-time repository snapshot with *root* now.

    Returns a human-readable drift description (or None when consistent).
    Raises ValueError on drift unless ``allow_drift`` -- silent drift is the
    exact failure this exists to stop: round 3's primary endpoint moved from
    -50.0% to -48.3% because one task's claims quote live-git facts.
    """
    path = package_dir / "root-state.json"
    if not path.is_file():
        return None
    import blind as blind_mod  # local import, same style as unblind_fragment

    recorded = json.loads(path.read_text(encoding="utf-8"))
    current = blind_mod.root_state(root)
    diffs = []
    if recorded.get("git_head") and recorded.get("git_head") != current["git_head"]:
        diffs.append(f"git_head {recorded.get('git_head')[:12]} -> {str(current['git_head'])[:12]}")
    if bool(recorded.get("dirty")) != bool(current["dirty"]):
        diffs.append(f"dirty {recorded.get('dirty')} -> {current['dirty']}")
    if not diffs:
        return None
    detail = (
        "仓库状态与打包时不一致（" + "; ".join(diffs) + "）：密封判定是在打包时刻形成的，"
        "用当前仓库重新解盲会得到不同数字（实测：第三轮 M1 由 -50.0% 漂到 -48.3%）。"
        "要么在打包时的仓库状态上复算，要么显式加 --allow-drift 并同时引用两个数字。"
    )
    if not allow_drift:
        raise ValueError(detail)
    # Opt-in must still leave a loud trace on stderr: a drifted number that got
    # printed quietly is how -50.0% and -48.3% end up cited as the same thing.
    import sys

    print(f"[DRIFT] {detail}", file=sys.stderr)
    return detail


def judge_package(package_dir: Path, root: Path, timeout: int = judge.DEFAULT_TIMEOUT_SECONDS) -> Dict[str, List]:
    """Deterministically re-judge every packaged product. Same products =>
    same judgements, always.

    **Sealed judgements win** (XJ-20261027-001): when the package carries
    ``judgements-blind.json`` we return those and never touch the repository.
    Re-judging is the legacy path for packages built before sealing existed.
    """
    sealed = sealed_judgements(package_dir)
    if sealed is not None:
        check_product_seal(package_dir)  # A1: bytes must still be the ones judged
        return sealed
    check_product_seal(package_dir)  # A1: same gate for the re-judge path
    products_dir = package_dir / "products"
    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    out: Dict[str, List] = {}
    for code in sorted(manifest["products"]):
        text = (products_dir / manifest["products"][code]).read_text(encoding="utf-8", errors="replace")
        out[code] = judge.judge_markdown(text, root, product=code, timeout=timeout)
    return out


def blind_report(package_dir: Path, root: Path, timeout: int = judge.DEFAULT_TIMEOUT_SECONDS,
                 allow_drift: bool = False) -> str:
    """Stage 1: the blind report. Contains zero condition information by
    construction -- it reads only package contents."""
    drift = check_root_state(package_dir, root, allow_drift=allow_drift)
    judged = judge_package(package_dir, root, timeout=timeout)
    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    metrics_blind = json.loads((package_dir / "metrics-blind.json").read_text(encoding="utf-8"))

    pooled = {"E0": 0, "E1": 0, "E2": 0, "E3": 0, "E4": 0}
    lines: List[str] = []
    lines.append(f"# {BLIND_STAGE_HEADER}")
    lines.append("")
    lines.append(f"- 包：{manifest['package_version']} 版，{manifest['n_products']} 份产品，"
                 f"生成于 {manifest['generated_utc']}（全部为伪码，无条件标签）")
    lines.append("- 判定：确定性规则判定器（E0-E4，见 docs/eval-prereg.md §1），"
                 "同输入必同输出；LLM 判定属于盲化 adjudication 层，不在此文件")
    lines.extend(snapshot_lines(package_dir, root, drift))
    lines.append("")
    lines.append("## 按 P 码判定表")
    lines.append("")
    lines.append("| P码 | 断言数 | E0 | E1 | E2 | E3 | E4 | 无锚断言 | 覆盖 |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for code in sorted(judged):
        judgements = judged[code]
        counts = stats.level_counts(judgements)
        for level in pooled:
            pooled[level] += counts[level]
        unanchored = sum(1 for j in judgements if "unanchored" in j.flags)
        coverage = metrics_blind.get(code, {}).get("coverage")
        coverage_text = {True: "是", False: "否", None: "未运行"}.get(coverage, "未运行")
        lines.append(
            f"| {code} | {len(judgements)} | {counts['E0']} | {counts['E1']} | "
            f"{counts['E2']} | {counts['E3']} | {counts['E4']} | {unanchored} | {coverage_text} |"
        )
    lines.append("")
    lines.append("## 汇总（混合两条件，盲态阶段不分组）")
    lines.append("")
    total_claims = sum(pooled.values())
    lines.append(f"- 断言总数：{total_claims}")
    for level in ("E0", "E1", "E2", "E3", "E4"):
        lines.append(f"- {level}（{LEVEL_NAMES[level]}）：{pooled[level]}")
    lines.append(f"- 混合 M1（仅描述，非配对结论）：{_fmt_pct(stats.m1_false_verification_rate(pooled))}")
    lines.append(f"- 混合 M2（仅描述，非配对结论）：{_fmt_pct(stats.m2_unsupported_claim_rate(pooled))}")
    lines.append("")
    lines.append("## 失败样本附录（全量保留）")
    lines.append("")
    failure_lines: List[str] = []
    for code in sorted(judged):
        for j in judged[code]:
            if j.level in ("E1", "E2", "E3"):
                failure_lines.append(
                    f"- **{code}** 行 {j.claim.source_line} 判 {j.level}：断言「{j.claim.text}」——{j.detail}"
                )
    if failure_lines:
        lines.extend(failure_lines)
    else:
        lines.append("-（无 E1/E2/E3 样本）")
    lines.append("")
    lines.append("## 配对差表与置信区间")
    lines.append("")
    lines.append("> 本节在报告定稿后由 sir 解盲填入（`run.py --unblind`）；"
                 "盲态阶段任何分组数字均不存在。")
    lines.append("")
    lines.append("## 局限性（五条，原文必载）")
    lines.append("")
    lines.extend(FIVE_LIMITATIONS)
    lines.append("")
    lines.append("## 措辞纪律")
    lines.append("")
    lines.append("本报告全部结论只可表述为「预注册条件下的对照证据」；"
                 "「证明降低幻觉」「证明有效」一类措辞被 EVO-20261024-001 禁止，"
                 "未达最小效应时必须写「未检出差异」。")
    return "\n".join(lines)


def unblind_fragment(
    package_dir: Path,
    key_path: Path,
    root: Path,
    run_dir: Optional[Path] = None,
    seed_for_bootstrap: Optional[int] = None,
    timeout: int = judge.DEFAULT_TIMEOUT_SECONDS,
    allow_drift: bool = False,
) -> str:
    """Stage 2 (sir only): the paired analysis, using the sealed key.

    ``seed_for_bootstrap``: the study's bootstrap draws must be reproducible;
    the caller passes the seed recorded in the prereg run log (derived from
    the sealed seed). None => derived deterministically from the key seed.

    ``allow_drift``: packages built with a root snapshot refuse to be unblinded
    against a different repository state (measured drift: -50.0% -> -48.3%).
    """
    import blind as blind_mod

    drift = check_root_state(package_dir, root, allow_drift=allow_drift)
    judged = judge_package(package_dir, root, timeout=timeout)
    mapping_rows = blind_mod.unblind(package_dir, key_path)
    metrics_blind = json.loads((package_dir / "metrics-blind.json").read_text(encoding="utf-8"))

    key_payload = json.loads(key_path.read_text(encoding="utf-8"))
    if seed_for_bootstrap is None:
        seed_for_bootstrap = int(key_payload["seed"][:16], 16)

    records: List[stats.ProductMetrics] = []
    for row in mapping_rows:
        code = row["code"]
        judgements = judged.get(code, [])
        records.append(
            stats.product_metrics(
                task_id=str(row["task_id"]),
                condition=str(row["condition"]),
                repetition=int(row["repetition"]),
                judgements=judgements,
                covered=metrics_blind.get(code, {}).get("coverage"),
            )
        )

    endpoints = stats.analyse_endpoints(records, seed=seed_for_bootstrap)

    lines: List[str] = []
    lines.append("# 解盲附录（sir 专用，报告定稿后执行）")
    lines.append("")
    lines.append(f"- 解盲对象：{package_dir}")
    lines.extend(snapshot_lines(package_dir, root, drift))
    lines.append(f"- 配对任务数：{len(endpoints['M1'].diffs)}（M1 口径）；"
                 f"{len(endpoints['M2'].diffs)}（M2 口径）；"
                 f"排除任务：M1 {endpoints['M1'].excluded_tasks}，M2 {endpoints['M2'].excluded_tasks}")
    lines.append("")
    lines.append("## 主指标配对差（条件 A 门禁全开 − 条件 B 门禁旁路）")
    lines.append("")
    lines.append("| 指标 | 任务数 | 配对差均值 | 95% CI（bootstrap over 任务） | 达最小效应（≥10pp 且 CI 不跨零） |")
    lines.append("|---|---|---|---|---|")
    for metric in ("M1", "M2"):
        endpoint = endpoints[metric]
        mean_text = _fmt_pct(endpoint.mean_diff) if endpoint.mean_diff is not None else "n/a"
        if endpoint.ci_low is None:
            ci_text = "n/a"
        else:
            ci_text = f"[{_fmt_pct(endpoint.ci_low)}, {_fmt_pct(endpoint.ci_high)}]"
        eff_text = {
            True: "是", False: "否", None: "n/a",
        }[endpoint.meets_minimal_effect]
        lines.append(
            f"| {metric} | {len(endpoint.diffs)} | {mean_text} | {ci_text} | {eff_text} |"
        )
    lines.append("")
    for metric in ("M1", "M2"):
        lines.append(f"- {metric}：{endpoints[metric].verdict_phrase()}")
    lines.append("")
    lines.append("## 按任务配对差（全量，禁止单点数字替代区间结论）")
    lines.append("")
    lines.append("| 指标 | 任务 | A − B |")
    lines.append("|---|---|---|")
    for metric in ("M1", "M2"):
        for task_id, diff in endpoints[metric].diffs:
            lines.append(f"| {metric} | {task_id} | {diff:+.3f} |")
    lines.append("")

    coverage = stats.coverage_by_condition(records)
    lines.append("## 任务完成覆盖率（次指标，防「少声称少做事」）")
    lines.append("")
    for condition in sorted(coverage):
        covered, total = coverage[condition]
        lines.append(f"- 条件 {condition}：{covered}/{total}")
    lines.append("")

    m3_lines = _m3_section(run_dir)
    lines.extend(m3_lines)
    return "\n".join(lines)


def _m3_section(run_dir: Optional[Path]) -> List[str]:
    """M3 门禁拦截率（负对照植入任务专用）. Numbers come from the run
    directory's m3.json, written by the study runner after probing the REAL
    gate/lint with implanted defects. Absent run => explicitly 未运行."""
    lines = ["## M3 门禁拦截率（负对照植入）", ""]
    if run_dir is None or not (run_dir / "m3.json").is_file():
        lines.append("- 未运行（本轮未执行负对照门禁探针）")
        return lines
    payload = json.loads((run_dir / "m3.json").read_text(encoding="utf-8"))
    total = int(payload.get("total", 0))
    rejected = int(payload.get("rejected", 0))
    lines.append(f"- 拦截 {rejected}/{total}"
                 + ("（预注册条件下）" if total else ""))
    return lines
