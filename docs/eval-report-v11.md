# 轮十一评估报告 v11 · 独立判级 / R_main 重测 / M_C 重推 / exit_source 升级

> 卡 `XJ-20261111-002` · D6 · 2026-11-11 · 执行者 `WB`（WorkBuddy） · 分支 `feature/xj-20261111-002-round11-independent-judge` · 基线 `f62f353`
> 依据：`docs/eval-prereg.md` §18（D18-0 / D18-A 11 条 + 3 禁令 / D18-B 冻结常量与三档表 / D18-C 盲态 / D18-D 独立性诚实 / D18-E codebook / D18-F 真数据规则 / D18-G 冻结序）
> **门结论：`not_evaluable`，不出门结论**。三档表按点估计 `R_main < 0.80` 命中，`gate_result = not_evaluable`（**不是** `not met`）；本轮产出为「主轨判级有效性报告」。
> **结论效力**：`caliber = single_agent_dual_view_direction_only`。独立性证书 `independence_satisfied = false`、三角锚定无双人独立标注，全部读数仅作方向诊断，**不是有效语义信度估计，不产生有效门**。
> 纪律：§18 冻结 commit 早于一切轮十一产物；报告**只查表、不解释**；每条结论带 `路径 + sha256` artifact 指针，缺指针即整轮 `invalid`；不写 verdict、不 push、不 merge、不重判轮六–轮十。

## 0. 元声明、合宪性与「只跑一次」

- **结论 M1**：§18 于 `2699a9c` 冻结，11 条条款 + 3 条禁令逐字并入，§0–§17 冻结文本逐字节未改（`prefix_intact = true`、`verbatim_intact = true`、纯追加 110 行）；冻结时间早于任何 `run-dir-r11/` / `shadow-r11/` / `out/` 轮十一产物。冻结序为 `freeze → offline replay → data`，公式、seed、三档表、codebook 均在数据生成前写死。`[artifact: out/triage-codebook-r11.json sha256=0d6c2a776fae4068cf53ee58b990ef9f5e7ed04be725427fa4b415363793d789]`
- **结论 M2**：轮十旧门值 **0.95 作废**，留痕 `out/void-mc095.json` 记 `implementation_output_existed = false` / `voided_value = 0.95` / `reason` 非空，签署时机械核验 10 个实现与产物探针全部不存在。作废理由：其输入 `R_main = 1.0` 是同一确定性 judge 同一输入的两次运行恒等，属 stability 同义反复、不是语义信度；该输出值从生成起无信息量。重推是原规则的**首次有效执行**，不是第二次门重设计；留痕为纯追加，不触「只许一次」条款。`[artifact: out/void-mc095.json sha256=83ac2ab1242c1d9c824651b61a5a806578ca0b8a2cc602469b503a8461472b1f]`
- **结论 M3**：重推**只跑一次**。`derive_mc.py` 首次运行写入 `first_count_utc` 与 `input_sha256`；结果文件已存在时重算并逐字段比对，全等则打印 `RECOMPUTE_IDENTICAL: not a second counting run`、退出 0、拒绝覆盖，不等则退出 3。R_main 重测同样设 `FIRST_RUN_ONLY` 重跑保护，结果存在即拒绝第二次计数。两次「只跑一次」约束均未触发违规。`[artifact: out/derive-mc-r11.json sha256=e091424a2fe852c9ad7bca6c57878bc5fecede4879a164769dfc22325d69e648]`
- **结论 M4**：按 §18 D18-B 第 4 条冻结公式 `floor_to_5pct(min(0.95, LB95 − 0.05))`，`LB95 = 0.546722` → `0.496722` → 落到 0.05 网格，得 **M_C = 0.45**（Decimal `ROUND_FLOOR`，与 §17 D17-E 实现交叉校验 `identical = true`）。全文只有这一个门值数值；结果公开发布，**即使对本轮不利也不再改动**。`[artifact: out/derive-mc-r11.json sha256=e091424a2fe852c9ad7bca6c57878bc5fecede4879a164769dfc22325d69e648]`
- **结论 M5**：**方向如实披露**。0.45 在数值上比作废的旧门 0.95 **更低／更松**，不是「使门更难」。但按冻结三档表命中 `not_evaluable`，**不 emit 任何门判定**（`gate_conclusion_issued = false`），门值变松不产生判定效力、反常激励无法兑现；按 §18 禁令 2，低 R_main 是参照失效，不允许自动放宽门。`[artifact: out/derive-mc-r11.json sha256=e091424a2fe852c9ad7bca6c57878bc5fecede4879a164769dfc22325d69e648]`

## 第一层 · Gate 0：R_main 重测（盲态，n = 400）

- **结论 G1**：`R_main = 0.62069`（108/174 可比对样本逐条一致），`LB95 = 0.546722`（Wilson，z = 1.959963984540054），`n = 400`，`seed = 20261111`。R_main 定义为主轨判级与独立判级在同一盲样本上的逐条一致率（inter-implementation agreement），**不是** test-retest；`R_stability` 降级为确定性 sanity check、不入公式。三档查表按点估计命中 `R_main < 0.80` → `branch = not_evaluable`。`[artifact: out/r11-main-reliability.json sha256=b54d2d43038ff6ce9f39e96e89235f54cf9f8085559ea44b6eb44a44a73c2b68]`
- **结论 G2**：盲态序机械成立——独立实现先跑完 400 条，`out/r11-independent-blind.json` 的 SHA-256 `3d4d6bb3…` 于 `2026-11-11T15:00:56.391372+00:00` 封存，封存日志记 `main_track_invoked_before_seal = false`，之后才调用主轨比对；`seal_then_unblind_order = true`。样本集 `n = 400`（`R10_ANCHOR 240` + `HOLDOUT 160`）生成一次、封哈希、不回头改。`[artifact: out/r11-seal-log.json sha256=49517437036cc151fa6c1c39dcd3cc4e140aa49f2d96f762ec28244da3cae0a2]`
- **结论 G3**：**最大效力限制**——独立实现在 400 条中弃权 **226 条（56.5%）**（`OBSERVATION_ERROR 156` + `INSUFFICIENT 70`），R_main 的分母实为 174 条而非 400。弃权**不是随机缺失**，集中在无证据行、ref 缺失、unanchored 层，会系统性影响一致率且方向未知；另报全 400 分母口径 `0.27` 仅供对照、不作 R_main。`[artifact: out/r11-reliability-rows.json sha256=2b38e9abf5fde4ba9b624311c107ced1498c6d286b601ba8aad8bfe845cd3fe7]`
- **结论 G4**：独立性**不可满足**（照实声明，非执行失败）。六字段证书中 `judge_model_family` 与 `rubric_blind` 不满足：主轨 `judge.py` 自述确定性符号规则引擎、无模型族，独立实现同为确定性符号打分器；本环境单一 agent、CI py3.9、无网络／外部模型调用，无法提供不同模型族且可机械复算的第二判级器；作者写 rubric v2 前已读 §0–§17 与 judge 文件头，不能诚实主张未读 v1。`independence_satisfied = false`、`honesty_clause_invoked = true`，**未伪造任何字段**；按 §18 D18-D 结论效力降级为「单 agent 双视图一致性 + 方向诊断」。V5 字面命令退出码 0（七字段全在）但语义判据不满足，照实登记 FAIL、不刷绿。`[artifact: tools/eval/independence_cert.json sha256=297a1409599a96ca91fc5c2f1b2e60b236e4f998fa7f1c171edb218337b8b0c2]`
- **结论 G5**：判别探针 40 条（四族各 10：cwd 根错位 / SILENT_FALLBACK 伪装 / 内容为真但证据未复现 / dotfile Owned-claim），分歧率 `0.60 ≥ p = 0.30`，四族各 0.60，对抗 24/24 分歧、对照 16/16 一致。**但严格布尔分歧率仅 0.15**——多数分歧来自独立实现显式弃权而非相反布尔判级，不拿它冒充强分歧。探针集生成一次、封哈希 `cbe980f9…`、独立先跑再比主轨。`[artifact: out/probe-report-r11.json sha256=23c4422e2ed36da9e6a8efe8ec3180c2c3b944225cfc315def1900a6d6163cf5]`

## 第二层 · 双指标门 + 三元组 + 2×2 + exit_source 三态

- **结论 D1**：门重跑**零新数据**——输入仍为轮十封存 `r10-gate-input.json` 的 210 pairs，只换度量口径，不重判、不改写轮十 verdict。门结论从 `out/derive-mc-r11.json` **照抄冻结查表结果**（`branch = not_evaluable`、`gate_result = not_evaluable`、`gate_conclusion_issued = false`），度量函数不重新解释、不重新开门。`[artifact: out/gate-metrics-r11.json sha256=3de7a235f41b89150f209f31b19fa8e1b35716d95a4f11a5e35bb5fb9892bf41]`
- **结论 D2**：**可判定率** `0.857143`（180/210）≥ 冻结下限 0.80，未回退；30 条因 `FILE_NOT_FOUND` + `SILENT_FALLBACK` 被排除出 C 分母，但**仍留在可判定率分母中**（不隐藏 ERROR）。`fail_fast_observation = true`、`allow_silent_fallback_used = false`。`[artifact: out/gate-metrics-r11.json sha256=3de7a235f41b89150f209f31b19fa8e1b35716d95a4f11a5e35bb5fb9892bf41]`
- **结论 D3**：主指标三元组（二级诊断口径）`pass_rate = 0.833333`、`precision = 0.6`、`recall = 0.75`，**2×2 混淆矩阵** `TP 90 / TN 0 / FP 60 / FN 30`。三元组与 2×2 已按 §18 条款 7 预注册为主指标，取代标量 C；本报告并列给出，不合并成单一「一致率」。`[artifact: out/gate-metrics-r11.json sha256=3de7a235f41b89150f209f31b19fa8e1b35716d95a4f11a5e35bb5fb9892bf41]`
- **结论 D4**：**条件一致率** `C = 0.5`（90/180）**仅作次要指标**，供统一命题层级后的对角线单元率历史对比；D1 四桶 triage 桶 b = 100% 触发 §18 条款 8，C 这个标量指标**已作废**、不作门判据。双轨统一命题层级为「证据复现」（方案 A 目标态），过渡期允许方案 B 双层级并报；方案 C「影子只判可观测面」按 §18 禁令 1 明确拒绝。`[artifact: out/gate-metrics-r11.json sha256=3de7a235f41b89150f209f31b19fa8e1b35716d95a4f11a5e35bb5fb9892bf41]`
- **结论 D5**：**主指标不可评估（本轮最重要的诚实结论）**。`r10-gate-input.json` 的 `field_semantics.exit_code` 逐字声明其退出码为「a mechanical map over flags/detail, **NOT an independent OS process exit code**」，故 210/210 全部如实标注 `exit_source = adapter`（`os: 0 / adapter: 210 / launch_failed: 0`）。按 §18 条款 11，adapter 样本标 `caliber = degraded`、从**主 C / 主 precision 排除**、进二级报告 → 主样本集 **0 条**，`primary_metrics_excluding_adapter.evaluable = false`、`c = null`、`precision = null`。顶层三元组是 `metrics_caliber = secondary_diagnostic_only_adapter_inclusive` 的二级诊断值，**不冒充主指标、不作门判据**。`[artifact: out/gate-metrics-r11.json sha256=3de7a235f41b89150f209f31b19fa8e1b35716d95a4f11a5e35bb5fb9892bf41]`
- **结论 D6**：`exit_source` 三态落地并机械自洽——`adapter_samples_in_secondary = 210` 与 `secondary_report.sample_count` 一致，`launch_failed_counted_as_unsupported = 0`；夹具 `python tools/eval/exit_fixture.py --expect 10/10` 亲跑 `10/10`、退出码 0，4 `os` / 4 `adapter` / 2 `launch_failed` 全部真实执行。环境固定：清 `PYTHONPATH` 与全部 `COVENANT_*`、`-S` 禁 site/sitecustomize、`PYTHONNOUSERSITE=1`、cwd 固定（轮九 ADV-1 `bisect` 遮蔽根因）。`[artifact: out/exit-fixture-r11.json sha256=6b86832d9967c64e608c242fe88d0f66aa710c9aa63b8bb98e5926fe5988554a]`
- **结论 D7**：**不伪造 9009**。本机 `cmd /c <missing>` 真实返回 **1**（GBK 中文「不是内部或外部命令」），不是 9009；夹具保留真实观测码 1，把 9009 仅作冻结的 Windows shell 语义标注写入 `windows_shell_semantic_code`，不制造 OS 从未产生的退出码。两条 launch_failed 夹具的 `unsupported` 均为 false，验证「127 / 9009 不得计入不支持」。`[artifact: tools/eval/fixtures/exit_codes.yaml sha256=f5002d9b94ba61243e920581ca66cfdbfe25eaf1ca0c283af8308e45af7e4dac]`

## 第三层 · 金标准校准（50 条三角锚定子集）

- **结论 K1**：50 条子集由 `R11_SEED = 20261111` 从 400 条盲样本确定性抽取，两视图可比 22 条、一致 13 条，一致率 `0.590909`；逐条数据落在 `goldset/calibration_r11.jsonl`（50 行）。`[artifact: out/r11-triangle-anchor.json sha256=215e706ab81a5b0f6d1ba488f70cd7d0a76ecfff7f4a6300681abbe15bdae3e2]`
- **结论 K2**：**双人独立标注不可满足**。`two_human_independent_annotation = false`、`R_main_human = null`、`R_indep_human = null`、`triangle_verdict = not_evaluable_no_independent_human_annotation`；执行者为单一 agent WB，两个「视图」是同一主体的两套确定性程序。逐行自证 `annotation_mode = single_agent_double_view` / `two_human_independent = false`，**不得记为双人独立，0 分歧也不证明独立性**。`[artifact: goldset/calibration_r11.jsonl sha256=ebf3821ecd005a6f8f0ef5baa0696762ae5c44c2e5e21c42ea4caf36c02e517e]`
- **结论 K3**：按 §18 D18-D 与轮十 ADV-3 同形处理——明确披露 + 效力降级为「单 agent 双视图一致性 + 方向诊断」；三条三角判据（两实现可互换 / 主轨是薄弱环 / 独立实现薄弱需重建）因输入不存在，**本轮均不裁定**。该路径与 `R_main < 0.80` 的 `not_evaluable` 同向不矛盾，但各自独立成立，不靠叙述合并。`[artifact: docs/eval-goldset-calibration-r11.md sha256=8855757bcee8329d283c6bcd99afd1894141dcfd536df925f39e5884aea25116]`

## 第四层 · 四桶 triage（轮十 90 条失配，零新数据）

- **结论 T1**：90 条失配全部落桶 **b（命题层级不一致）= 100%**，桶 a / c / d 与 `unclassifiable` 皆为 0，占比和 100%；与 `main-judgements.json` 逐条交叉核对 90/90 全对；codebook 输出与冻结 canon 字节全等 `0d6c2a77…`。四桶源仅用轮十封存 artifact，**零新数据、零重判、不改写轮十 verdict**。`[artifact: out/triage-r11-summary.json sha256=dedcf473e560325988327738bb8adf6590f1f6bc2b6a80884707bf2e874f4bef]`
- **结论 T2**：查表触发 `b_ge_60pct` →「C 这个标量指标作废，改用 2×2 矩阵 + 三元组」；`c_ge_10pct` **未触发**（桶 c = 0，不判 E7 回归、不降修复轮）。该触发在数据前写死于 §18 D18-E，triage 只做分类、报告只做查表。`[artifact: out/triage-r11.tsv sha256=c339a7ba0bb1e9a1652c1917aa3b9a34ff474cdff34436975fb17bd67b539e41]`
- **结论 T3**：命题层级分歧（主轨判「证据复现」vs 影子判「内容／进程状态为真」）是 90 条失配的唯一构成；在拆解之前，任何「影子轨能力 = 0.5」的表述都是错的。§18 指标降级正是针对此：一致率把 precision 与 base rate 混在一起，全放行的影子轨 `recall = 1.0` 却毫无预筛价值。`[artifact: docs/eval-triage-r11.md sha256=1c86dfa627acde9340534df8c0bc0da49181b05d02ead9e29ea971c20b1baa7a]`

## 第五层 · 分层诊断

- **结论 L1**：两层**分层并列、不合并掩盖**——`R10_ANCHOR n=240`：可比 68、弃权 172（71.67%）、`R_main = 0.558824`、`LB95 = 0.440819`；`HOLDOUT n=160`：可比 106、弃权 54（33.75%）、`R_main = 0.660377`、`LB95 = 0.566027`。两层差 10.16pp，弃权率差 38.17pp；若合并会掩盖分层结构，故按 §18 条款 5 分别报告。`[artifact: out/r11-main-reliability.json sha256=b54d2d43038ff6ce9f39e96e89235f54cf9f8085559ea44b6eb44a44a73c2b68]`
- **结论 L2**：层级分布并列——主轨 `E4 226 / E2 114 / E1 30 / E0 30`，独立实现 `SUPPORT 126 / NOT_SUPPORT 48 / OBSERVATION_ERROR 156 / INSUFFICIENT 70`。独立实现架构差异（无 root 兜底、unanchored 不放行、观测失败显式 ERROR、锚点覆盖率软判据）使其在主轨 E4 层大量弃权，解释了 G3 的 226 条弃权来源。`[artifact: tools/eval/independent_judge.py sha256=a792aef6bb3afc6188512941aeadfcae6da6543804175e00e6e752e0d6c00329]`
- **结论 L3**：`SILENT_FALLBACK = 30` **单列不折叠**，五类预注册 ERROR 分布 `FILE_NOT_FOUND 30 / CWD_MISMATCH 0 / PARSE_FAIL 0 / TIMEOUT 0 / SILENT_FALLBACK 30`；E7 fail-fast 默认 `fail_fast_observation = true`，本轮禁用 `--allow-silent-fallback`。轮九「假一致」根因（观测静默失败恰好与主轨同向）在本轮口径下不会被折叠进「不支持」。`[artifact: out/gate-metrics-r11.json sha256=3de7a235f41b89150f209f31b19fa8e1b35716d95a4f11a5e35bb5fb9892bf41]`
- **结论 L4**：D3 首次样本生成曾返回 `BAD_COUNTS 210 160 370`（Gate 0 第 8 层 `no_evidence` 无证据行被正则静默漏抓 30 条），该次**在写出任何样本文件之前即失败**，随后计数运行因读不到样本报 `FileNotFoundError`；两次均未产生轮十一数据、未触碰「只跑一次」。修正为「证据行可选」块正则后重生成，240/160 分层核对通过，才执行唯一一次盲态重测。`[artifact: out/r11-blind-samples.json sha256=6d61994c7104747a797658b72733898b5c833b07715155e3aba0c987b4b9fcc9]`
- **结论 L5**：效力总表——① 独立性证书不满足（`judge_model_family` / `rubric_blind`）；② 三角锚定无双人独立标注；③ 独立实现弃权 56.5%；④ `R_main < 0.80` 命中 `not_evaluable`；⑤ 门重跑全部样本为 adapter、主 C / 主 precision 不可评估。五条**各自独立成立、同向不矛盾**，任一条都足以阻止宣布有效门结论；本轮不宣布任何门结论有效。`[artifact: out/r11-main-reliability.json sha256=b54d2d43038ff6ce9f39e96e89235f54cf9f8085559ea44b6eb44a44a73c2b68]`

## 附录 A · 三档分支查表（决策规则写死，报告只查表）

| R_main（点估计） | branch | 处置 | 本轮 |
|---|---|---|---|
| ≥ 0.85 | `normal` | 按公式应用门值，出正常门结论 | 否 |
| 0.80 – 0.85 | `weak_reference` | 门结论标 `caliber = weak_reference`，门值照算 | 否 |
| **< 0.80** | **`not_evaluable`** | **不出门结论**，`gate_result = not_evaluable`；产出转「主轨判级有效性报告」 | **命中（0.62069）** |

按 §18 元条款，本表与 M_C 公式、seed、codebook 均在 D0 冻结；本报告对上述结果**只查表、不解释**，且 D4 之后无公式或样本改动（禁令 3）。`[artifact: out/derive-mc-r11.json sha256=e091424a2fe852c9ad7bca6c57878bc5fecede4879a164769dfc22325d69e648]`

## 附录 B · 披露清单（不修饰）

1. 重推值 0.45 在数值上**比作废的旧门更松**，不是「使门更难」；因 `not_evaluable` 不 emit 门判定，不构成放宽门（结论 M5）。
2. V5 字面命令退出码 0，但语义判据 `judge_model_family ≠ 主轨族` 与 `rubric_blind = true` **不满足**，按卡面「任一 FAIL 不进入门结论讨论」照实登记，不刷绿（结论 G4）。
3. 判别探针 0.60 主要由显式弃权贡献，严格布尔分歧率仅 0.15（结论 G5）。
4. 轮十一门重跑的 210 条样本全部为 `adapter` 口径，主指标不可评估（结论 D5）；顶层三元组是二级诊断值。
5. 本机 `cmd.exe` 真实返回 1，9009 仅为冻结语义标注，未伪造 OS 退出码（结论 D7）。
6. 全量回归：字面 `unittest discover -s tests` 退出码 1（2 failures / 3 errors，全部源于 `no Git for Windows bash found; set COVENANT_BASH_HINT`，与轮十 V9 同形）；设置 `COVENANT_BASH_HINT` 后 `Ran 546 tests ... OK`、退出码 0。两份日志留档 `round11-custody/`，不刷绿。
7. 本卡未产生 `run-dir-r11/` / `shadow-r11/` 真数据；§18 D18-F 真数据生成规则已冻结，供轮十二复用。

## 附录 C · 边界与交裁定项

不写 verdict、不 push、不 merge、不碰 master、不重判轮六–轮十历史轮次；红区（judge / extract / blind / report / stats / study_runner / seal_run / gate / lint_cards / verdicts / .eval-sealed + prereg §0–§17）零触碰；CI py3.9 兼容（禁用 API 字面量为 0，新增脚本 `ast.parse(feature_version=(3,9))` 全通过）。

交浮香（AgnesCode）裁定：① 独立性不可满足时本轮「照跑如实发布 + 不出门结论」的处置是否认可；② 门值 0.45 方向变松但被 `not_evaluable` 封死，是否满足「即使使门更难也公开发布」的合宪性约束；③ 210/210 全 adapter 导致主指标不可评估，是否需要新卡补做真实 OS 观测；④ 是否需要独立人类标注 / 不同模型族判级；⑤ V5 语义 FAIL 与 V12 lint --strict 残余 warnings 的处置。执行者无评审权、无合并权，本卡停在 `IN_REVIEW` 等 Orchestrator 预审 + 浮香 PASS gate。
