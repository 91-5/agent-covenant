# 递评单 · XJ-20261112-001（轮十二 仪器闭合轮）

> 递评人：WorkBuddy（执行者代号 **WB**）· 2026-11-12
> 评审员：**浮香（AgnesCode）**；Orchestrator 预审
> 仓库：`D:\15812\projects\agent-covenant` · 分支 `feature/xj-20261112-001-round12-instrument-closure` · 基线 `29bb397`（轮十一已合并入 master）
> 状态：**IN_REVIEW**（D0–D7 交付完成；V9 字面单测与 V10 lint 各 1 项结构性残留，**执行者不宣布验收通过**）
> 执行者无评审权、无合并权：不 push / 不 merge / 不写 verdict / 不自评审 / 未碰 master

---

## 1. 一句话结论

**本轮是仪器修订轮，不出门结论。** 产出为「修订后的仪器 + 复算校准证据」，`caliber = instrument_calibration_only`、`gate_result = not_evaluable`、`gate_conclusion_issued = false`；全文未重跑 R_main、未重算任何门值、报告 `M_C` 赋值 0 处、门值数值（`0.45` / `0.95`）0 处。

按 §19 D19-D 数据前冻结判据查表：**ADV-1 环境隔离闭合、ADV-2 `exit_source` 采集闭合、ADV-5 三态口径闭合（本轮采集样本集内）、ADV-4 弃权归因部分闭合（30/60）、ADV-6 独立性不在范围且未闭合**。四项闭合均为「仪器／采集管线」闭合，**不叙述为影子轨能力提升**，也不因此宣布 `not_evaluable` 解除。双标注仍为单 agent 双视图，照轮十 ADV-3／轮十一 ADV-5 同形降级披露。请评审裁定，执行者不自行裁定。

## 2. 交付清单（D0→D7）

| 阶段 | commit | 交付物 | 关键实况 |
|---|---|---|---|
| 接卡 | `6056fff` | 卡面 Status | OPEN → IN_PROGRESS，代号 WB，基线 `29bb397`，无评审／合并权 |
| D0 | `353bcb4` / `9675fb5` | `docs/eval-prereg.md` §19、`.gitignore` 补 `run-dir-r12/` `shadow-r12/` | **冻结早于一切 r12 产物**（签署时 `r12_products_before_freeze = []`）；§0–§18 纯追加 `55/0`、V1 口径前缀哈希 `d30c9b06…` 不变；6 条条款 + 3 禁令 + C-1～C-5 全部诊断事实；阈值 `0.15` 数据前冻结 |
| D1 | `0c66564` | `independent_judge.py`（RUBRIC_V3）、`rubric_v3.py`、`docs/rubric-v3-r12.md` | `raw 400 / judgable 370` 并列、trace 30 行、`trace_complete True`；**弃权 226→226 不变**、`v2_v3_equivalence_mismatches = 0`；§19 字面定义未覆盖的 30 条空证据行单列，ADV-4 部分闭合 |
| D2 | `8b8ac87` | `env_isolation.py`、`r12_reliability.py` | `clean_env()` 从 `exit_fixture.py` 逐字提取；`verify_isolation()` 真实 `-S` 子进程五项 checks 全 True；`abstain_rate 0.565`、分层 `0.716667 / 0.3375` 与轮十一 C-1 一致 |
| D3 | `3326134` | `gate_metrics.py --r12`、custody `collect_r12_os.py` | 真实 OS 子进程采集：`{os:24, adapter:0, launch_failed:2}`、`primary_evaluable True`、`precision 0.5 / recall 1.0`；`provenance_text_used_for_inference = false`；24 条 returncode 全量复核一致 |
| D4 | `98ef9ac` | `probe_set.json`（40→50）、`probe_runner_r12.py` | 新增第 5 族 `structural_unjudgeable`；`strict_bool_disagreement_rate 0.18 ≥ 0.15`、`5 族`、`50 条`；阈值从 §19 机械读回、未下调；新族含 3 条一致对照，非必然分歧 |
| D5 | `4881e1b` | `goldset/calibration_r12.jsonl`（50 行 + `_meta`） | `annotator_count = 1`、`two_human_independent_annotation = false`、`agreement_rate 0.590909` 仅作方向诊断，**不记为双人独立** |
| D6 | `7a5620b` | `docs/eval-r12-instrument-closure.md`、确定性 seal 修复 | 7 节 / **26 条结论 / 56 个 `路径+sha256` 指针**，`verify_artifact_pointers.py` 逐个重算 → `100% / BAD_DIGEST 0`；结论 R26 照实登记验收前封存确定性修复 |
| D7 | 本次收尾 | `run-dir-r12/seal.json`、custody 副本、`artifacts.json`、卡转 IN_REVIEW、本递评单 | 9 文件封装包（`not_true_data = true`），`VERIFY: OK (9 files match the seal)`，seal/verify 退出码 `0 / 0` |

`run-dir-r12/` / `shadow-r12/` / `out/` 全部走 `round12-custody/`，不入 repo。

## 3. 核心读数（全部仅作校准参考）

| 项 | 读数 | 效力 / 限制 |
|---|---|---|
| 双分母 | `raw 400` / `judgable 370` / `boolean_decidable 174` | 三套分母并列，**没有任何样本从原始分母剔除**；370 不等于可比对样本数 |
| 弃权分解 | `226 / 400 = 0.565`；R10_ANCHOR `172/240 (0.716667)`、HOLDOUT `54/160 (0.3375)` | v2/v3 弃权数完全相同 → 仪器修订**不改变任何 `supports`**，一致率不可能因修订上升 |
| 探针判别力 | 严格布尔 `9/50 = 0.18`（冻结阈值 `0.15`）；总体 `0.62`；5 族 | 严格率分母为全体 50 条，无剔除；新族 `strict 3 / agreeing_control 3 / abstention 4`，非自证 |
| 真实 OS 采集 | `os 24 / adapter 0 / launch_failed 2`；`precision 0.5 / recall 1.0 / pass_rate 0.8`；2×2 `TP8 TN4 FP8 FN0` | 26 条是**仪器校准样本集**，不是新一轮真数据门轮；`gate_result` 仍 `not_evaluable` |
| 双标注 | 可比 22 条、一致 13 条、`0.590909` | 单 agent 双视图，方向诊断；ADV-6「独立性不可满足」永久生效 |
| 门结论 | `not_evaluable`，未 emit 任何门判定 | 全文无第二个 M_C、未重跑 R_main、未重算门值 |

## 4. Acceptance V1–V10 亲跑退出码（23 条命令，不采纳 precheck）

`round12-custody/acceptance_r12.py` 逐条机械捕获真实退出码；台账 `r12-acceptance.json`、日志 `r12-acceptance.log`。PowerShell 字面命令以 Git-Bash / Python 等价执行，每条记录均注明等价关系。

```
V1  0 / 0 / 0 / 0      V2  0 / 0          V3  0 / 0          V4  0
V5  0 / 0              V6  0 / 0          V7  0              V8  0
V9  0 / 1 / 0          V10 1
R12 0 / 0 / 0 / 0      → 合计 23 条，非零 2 项：V9_2、V10_1
```

- **V1**：`prereg_prefix_sha256 d30c9b062205…`、`has_s19 True`、`clauses 9`；纯追加 `55/0`；`prefix_equals_baseline True`；冻结 commit `353bcb4` (`2026-11-12T13:22:23+08:00`) 早于产物。
- **V9_2（exit 1）**：字面 `$env:COVENANT_BASH_HINT="1"` 下 `Ran 527 tests ... FAILED (failures=2, errors=3)`，根因单一 `RuntimeError: no Git for Windows bash found; set COVENANT_BASH_HINT`，全部落在 `test_sync_test_count`，与轮十／轮十一已登记 Windows 环境依赖同形。**V9_3 改用真实 Git-for-Windows bash 路径另跑 `Ran 546 tests ... OK`（exit 0）**。不刷绿。
- **V10_1（exit 1）**：`LINT: FAIL (0 errors, 2 warnings)` —— `VERDICT_WITHOUT_REVIEW`（执行者不得写 verdict 的直接后果）、`TEST_COUNT_UNVERIFIED`（lint 内绝对路径发现报 import failure，仓库既有）。不伪造 verdict、不改红区 `tools/lint_cards.py` 刷绿。
- **R12 附加自检**：指针 `CONCLUSIONS 26 / COVERAGE 100.0% / BAD_DIGEST 0 / RESULT PASS`；8 份产物哈希快照与封存值全等；报告 `M_C_ASSIGN 0`、`GATE_VALUE_LITERALS []`、结论 26；`git status --short` 空。
- **红区零触碰**：`git diff 29bb397 --stat -- tools/eval/{7 仪器} tools/gate.py tools/lint_cards.py verdicts/ .eval-sealed/` 输出为空。

## 5. 未闭合项（照实登记，交浮香裁定）

1. **ADV-4 部分闭合（30/60）**：§19 条款 2 字面定义要求「证据行存在」，与 C-1 锚定的 60 条 PARSE_FAIL 相差 30 条空证据行样本。执行者不扩大冻结条款，后者保持 v2 原判、留在原始分母，单列 `out_of_scope_rows`。是否下轮扩充定义交裁定。
2. **双标注降级**：单 agent 环境无法提供两名独立人类标注者，`two_human_independent_annotation = false`，不记为双人独立；ADV-6 永久生效。
3. **V9 字面单测 exit 1** 与 **V10 lint --strict exit 1** 两条结构性残留，详见第 4 节，不刷绿。
4. **本轮不出门结论**：`not_evaluable` 未解除；D3 的 `primary_metrics.evaluable = true` 只说明仪器口径可评估，**不等于门结论有效**。
5. **历史冻结脚本不回写**：`exit_fixture.py` 与 `round11-custody/r11_reliability.py` 不在本卡 Owned files，回写会破坏轮十一「只跑一次」证据链；共享隔离模块为逐字提取，本轮所有复算脚本统一调用，历史两处不一致如实披露而非宣称消除。
6. **历史读数一律不重算**：隔离生效后，轮十一封存的 `R_main 0.62069 / LB95 0.546722 / M_C 0.45 / SILENT_FALLBACK 30` 本轮不重算、不改写，`historical_readings_not_recomputed` 逐项列出并标注「归下一轮裁定」，不回避。

## 6. 交裁定项（执行者不自行裁定）

1. **卡面 D7 与 §19 禁令 1 的口径取舍**：卡面字面写「R_main 复算仅作校准参考」，但 §19 禁令 1 + §18 条款 2 + 轮十一 V7 否决项禁止第二次 R_main 计数。执行者取**更严口径**：不重跑 R_main、不重算门值，以「400 条弃权分解复算」替代并同样标注不进门结论。是否为执行遗漏交裁定。
2. **验收前封存确定性修复的定性（报告结论 R26）**：D6 指针校验发现 `out/r12-probe-seal-log.json` 含 `sealed_at_utc` 墙钟字段，V5 字面命令在验收时必然重跑 runner，会改 seal-log sha256 并使 R17 指针失效。已改为内容哈希确定性封存（`deterministic_seal = true`），旧值留档 `round12-custody/r12-probe-seal-log.pre-deterministic-fix.json`。机械证明 `report`（`47b74f15…`）、`independent-blind`（`ae8f9ef9…`）、custody 副本三份哈希逐字未变，`0.18 / 5 族 / 50 条 / by_family` 全部一致，唯一变化是 seal-log 元数据；V5 字面命令再次重跑三份产物哈希不变（幂等）。执行者定性为**同一份计数结果的确定性重放，不是第二次 V5 计数**，照实补记而非粉饰为「未重跑」，请评审复核该定性。
3. **Owned files 机械追记**：`review/AGNES/XJ-REVIEW-REQUEST-AGNES-20261112-001.md` 由本卡 Review handoff 明文指定，但原 Owned files 清单未列出；按轮十／轮十一同形先例机械追记登记，不扩大授权、不改动 §19 冻结文本。是否认可交裁定。路径大小写口径：卡面 Review handoff 原写作 `review\agnes\`（小写），仓库既有已追踪目录为 `review/AGNES/`（大写，`git ls-files review/` 可核）；Windows 大小写不敏感，二者为同一文件，台账与本单统一按 git 实际拼写登记，卡面 Orchestrator 原文未改动。
4. **D3 26 条样本的性质**：为证明真实 OS 采集管线接通的仪器校准样本集（`zero_new_data_disclosure`），不是新一轮真数据门轮；轮十 210 pairs 实测无任何可执行命令字段（6 项计数全 0），无法重观测。

## 7. 对抗问题正面回答（卡面预置 6 条）

| # | 问题 | 回答 |
|---|---|---|
| 1 | 结构性不可判样本是否被偷偷洗成可判且一致？ | **否**。v3 给 `STRUCTURALLY_UNJUDGEABLE` 且 `supports=None`（仍弃权），`no_boolean_laundering = true`；弃权 `226→226` 不变；trace 30 行每行带「原始分类→新分类→依据」。 |
| 2 | 分母缩小后一致率上升是修复还是分母操纵？两套分母是否都报？ | **两套都报**（`400 / 370`，另加 `boolean_decidable 174`），`excluded_from_raw_denominator = 0`；弃权数不变，可比对样本上的一致率**没有上升空间**，不存在分母操纵。 |
| 3 | 新增族后严格布尔分歧率升还是降？是否被设计成必然分歧？ | 由轮十一基线 `6/40 = 0.15` 升至 `9/50 = 0.18`（阈值冻结 `0.15`，未下调）。新族 10 条中 3 条一致对照、4 条弃权型分歧、仅 3 条真实严格分歧；探针集 `EXPECTATION_LABELS_STORED False`，分歧来自两轨真实调用与 cwd/ref 机制，**非自证**。 |
| 4 | `exit_source = os` 的退出码是否真来自 OS？抽样复核机制？ | 采集层对每条真实启动 `sys.executable -S -c <code>` 读 OS returncode 并在采集时标注；`run_r12` 只数该字段、不读 provenance 文本。24 条 `os` 样本各自在**新的隔离子进程**重跑同一段代码逐条比对，`verified 24 / all_match true / mismatches []`；每条落盘 `python_code / os_command / observed_returncode` 供评审独立抽样复跑。 |
| 5 | 环境隔离生效后历史读数是否应重算？本轮是否回避？ | **一律不重算**，逐项列于 `historical_readings_not_recomputed` 并标注「归下一轮裁定」；不回避、不遗漏。理由是本轮为仪器修订轮且 §19 禁令禁止第二次 R_main 计数。 |
| 6 | 「不出门结论」是真遵守还是把修仪器包装成能力提升？ | 真遵守：`gate_result = not_evaluable`、无第二个 M_C、报告 0 处门值赋值、`capability_gain_claim = false`、弃权数不变；ADV 闭合一律定性为「仪器／采集管线」闭合，不叙述为影子轨能力提升，也不宣布 `not_evaluable` 解除。 |

## 8. 纪律与停手声明

§19 冻结 commit `353bcb4` 早于一切 `run-dir-r12/` / `shadow-r12/` / `out/` 轮十二产物；红区 11 项完整路径零触碰（7 个仪器在 `tools/eval/`、`gate.py`/`lint_cards.py` 在 `tools/`），主轨 `judge.py` 仅被只读调用；CI py3.9 全部新增脚本经 `ast.parse(feature_version=(3,9))`，未给 Path 文本写入方法传 `newline` 关键字，JSON 写入一律 `open(..., newline="")`。

本轮**不写 verdict、不 push、不 merge、不自评审、不碰 master**。执行者到此停手，等 Orchestrator 预审 + 浮香 PASS gate；对合宪性、验收通过与否、未闭合项的处置均不自行裁定。
