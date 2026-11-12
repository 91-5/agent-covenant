# 轮十二 · 仪器闭合轮复算校准报告

> 卡 `XJ-20261112-001` · D6（卡面 D7）· 2026-11-12 · 执行者 WB
> 依据：`docs/eval-prereg.md` §19（D19-A 诊断事实 / D19-B 六条冻结条款 / D19-C 三条禁令 / D19-D 冻结常量表）
> 上游：轮十一 `gate_result = not_evaluable`（已 CLOSED，归档 legacy）；dp 大脑 2026-11-12 Q3 裁定「有效演练 + 仪器缺陷待修」

## 零、定位声明：本轮不出门结论

**本轮是仪器修订轮，产出为「修订后的仪器 + 复算校准证据」，不是门结论轮。** 全文 `caliber = instrument_calibration_only`、`gate_result = not_evaluable`、`gate_conclusion_issued = false`。所有复算读数仅作校准参考，**不进门结论**；门结论留给下一轮。

**本报告未重跑 R_main 计数、未重算任何门值、全文不出现任何门值数值**（§19 禁令 1 + §18 条款 2 + 轮十一 V7 否决项）。卡面 D7 字面写有「R_main 复算仅作校准参考」，本轮按禁令取更严口径：**以「400 条冻结样本的弃权分解复算」替代 R_main 复算**，同样明确标注不进门结论；此口径取舍在第五节如实披露并交浮香裁定。

本报告**不把修好仪器叙述为影子轨能力提升**：rubric v3 只改变弃权样本的**分类**，不改变任何 `supports`，弃权总数前后均为 226，可比对样本上的一致率不可能因仪器修订上升。

- **结论 R1**：§19 于冻结 commit `353bcb4` 落定，签署时无任何 `r12-*` 产物；§0–§18 纯追加零回写，V1 口径前缀哈希 `d30c9b06…` 冻结前后一致；含 6 条条款 + 3 条禁令（共 9 条编号项）与 C-1～C-5 全部诊断事实。[artifact: docs/eval-prereg.md sha256=0975c1bdfc6acfb2554704307e41498db4a5842052c307c8faafeb2f4220cf49][artifact: ../round12-custody/s19-freeze-anchors.json sha256=2aa8a94b4839337fd0f3422f10b037ae83762403bccd000a4f9aead5c275f57d]

- **结论 R2**：全部复算读数标 `not_gate_conclusion = true` / `r_main_recomputed = false` / `gate_value_recomputed = false`，`gate_result` 一律 `not_evaluable`；探针与门度量产物同样登记 `gate_conclusion_issued = false`。[artifact: out/r12-decomposition.json sha256=d5989b0a6436454054195cafab0df5e6d1fd1019641677fd2a9a03b2524edb52][artifact: out/r12-gate-metrics.json sha256=7fcc037291174728aba2241e287f5395ab8e85195a22a29dd0aa8a3439a74cc3][artifact: out/r12-probe-report.json sha256=47b74f1568ae4522c7c421956b33f2a78030b61b0bd6a7bb3bfe61b6bf9e99ed]

## 一、原始分母与可判分母并列（rubric v3 结构性不可判样本处置）

rubric v3 依 §19 条款 2 逐字定义「结构性不可判样本」为证据行非空且 `cmd=None / ref=None / anchors=[]`，给显式类别 `STRUCTURALLY_UNJUDGEABLE`、`supports=None`（**仍是弃权**）、`error_class=STRUCTURAL_NO_EVIDENCE`。v3 逐字继承 v2 决策路径，非结构性样本委托 `_judge_case_v2`。

- **结论 R3**：（双分母并列）`raw_denominator = 400`（全部冻结样本，seed 20261111），`judgable_denominator = 370`（= 400 − 30 结构性不可判样本），`denominators_paired = true`，`excluded_from_raw_denominator = 0`。**没有任何样本被从原始分母剔除**。[artifact: out/r12-abstention-decomposition.json sha256=97091832be84c634b34414b161114f8e1373121318f49c393765ba5646ea40c8][artifact: tools/eval/rubric_v3.py sha256=fc87560241b61584810860cbe18fc93bc01c813330dfbe09027f7caffaa0462e]

- **结论 R4**：（防止冻结公式被误读成能力读数）额外报 `boolean_decidable_denominator = 174`；冻结公式给出的 370 里仍包含 OBSERVATION_ERROR / INSUFFICIENT / 空证据行等弃权样本，**不等于可比对样本数**。产物明写 `boolean_decidable_note` 与 `capability_gain_claim = false`。这是对抗问题 2 的正面回答。[artifact: out/r12-abstention-decomposition.json sha256=97091832be84c634b34414b161114f8e1373121318f49c393765ba5646ea40c8][artifact: docs/rubric-v3-r12.md sha256=7bb9220e97c556e22c535c381047d91caabcee6a533a800605d7303269a8d04b]

- **结论 R5**：（逐条留痕）`reclassification_trace` 30 行，每行含 `原始分类 → 新分类 → 依据 → stratum/layer → evidence_raw/cmd/ref/anchors`；`trace_complete = true` 的判据是独立核算——trace 行数 == 独立用 `is_structurally_unjudgeable` 统计的 30 == `reclassified_total`，且每行 `new_supports is None`（`no_boolean_laundering = true`）。[artifact: out/r12-abstention-decomposition.json sha256=97091832be84c634b34414b161114f8e1373121318f49c393765ba5646ea40c8][artifact: tools/eval/independent_judge.py sha256=3ba89be10588adec3f13d815884f4132f203f441671c4330e490a2193850a8d6]

- **结论 R6**：（冻结定义未覆盖的 30 条，如实部分闭合）C-1 的 60 条 PARSE_FAIL 实测为 `incomplete 30`（证据行非空、符合 §19 字面定义）+ `no_evidence 30`（证据行整体为空、不符合字面定义）。后 30 条**不擅自扩大冻结条款**：保持 v2 原判、`supports=None`、留在原始分母，单列 `out_of_scope_rows` 并标注归下一轮裁定。故 ADV-4 为**部分闭合（30/60）**，不宣称全闭合。[artifact: out/r12-abstention-decomposition.json sha256=97091832be84c634b34414b161114f8e1373121318f49c393765ba5646ea40c8][artifact: docs/rubric-v3-r12.md sha256=7bb9220e97c556e22c535c381047d91caabcee6a533a800605d7303269a8d04b]

- **结论 R7**：（v2/v3 机械等价）v3 对 370 条非结构性样本与轮十一封存 v2 逐条比对 `level/supports/score/error_class/features`，`v2_v3_equivalence_mismatches = 0`，同时证明 v2 路径未漂移、v3 只在结构性样本上改变分类。[artifact: out/r12-abstention-decomposition.json sha256=97091832be84c634b34414b161114f8e1373121318f49c393765ba5646ea40c8][artifact: tools/eval/independent_judge.py sha256=3ba89be10588adec3f13d815884f4132f203f441671c4330e490a2193850a8d6]

## 二、弃权分解复算（仅校准参考，不进门结论）

- **结论 R8**：修订后仪器对 400 条冻结样本的 `abstain_rate = 0.565`（226/400），`abstain_total_v2 = 226`、`abstain_total_v3 = 226`、`abstain_unchanged = true`。v3 前后弃权数完全相同，**仪器修订不产生任何能力提升**。[artifact: out/r12-decomposition.json sha256=d5989b0a6436454054195cafab0df5e6d1fd1019641677fd2a9a03b2524edb52][artifact: out/r12-abstention-decomposition.json sha256=97091832be84c634b34414b161114f8e1373121318f49c393765ba5646ea40c8]

- **结论 R9**：（分层，从不合并掩盖）`R10_ANCHOR` 240 条弃权 172（0.716667）、真实可比对 68、结构性 30、空证据行 30；`HOLDOUT` 160 条弃权 54（0.3375）、真实可比对 106、结构性 0、空证据行 0。与轮十一 C-1 逐项一致，差异来自分层样本构成而非判级能力。[artifact: out/r12-decomposition.json sha256=d5989b0a6436454054195cafab0df5e6d1fd1019641677fd2a9a03b2524edb52][artifact: tools/eval/r12_reliability.py sha256=eda440df9d9e302832a0ce1ca6c809ce551b6ab3791656d6e5d88e04ae1515b5]

- **结论 R10**：（环境隔离真实生效，ADV-1）复算脚本调用共享 `env_isolation.py`；`verify_isolation()` 在宿主注入 `PYTHONPATH` 与 `COVENANT_*` 探针后起真实 `-S` 子进程回读自身环境，实测 `pythonpath_present=false / covenant_keys=[] / no_site=true / nousersite="1"`、五项 checks 全 True。[artifact: out/r12-decomposition.json sha256=d5989b0a6436454054195cafab0df5e6d1fd1019641677fd2a9a03b2524edb52][artifact: tools/eval/env_isolation.py sha256=40b8921a53c796d0c0f1d7af0a15b375068a241a12ce7640d65cf47c3085e3c3]

- **结论 R11**：（历史读数不重算的显式登记）隔离生效后，轮十一封存的 R_main / LB95 / 门值 / `SILENT_FALLBACK 30` 本轮**一律不重算、不改写**，产物 `historical_readings_not_recomputed` 逐项列出并标注「归下一轮裁定」（§19 条款 3，对抗问题 5）。[artifact: out/r12-decomposition.json sha256=d5989b0a6436454054195cafab0df5e6d1fd1019641677fd2a9a03b2524edb52]

## 三、探针判别力与真实 OS 采集管线（ADV-2 / ADV-5）

- **结论 R12**：（exit_source 由采集层产出，ADV-2）采集层真实启动 `sys.executable -S -c` 隔离子进程并把 OS returncode 在采集时标注为 `exit_source = os`；`--r12` **只数**该字段，不读 `field_semantics` 或任何 provenance 文本（`provenance_text_used_for_inference = false`、`field_semantics_key_read = false`）。`exit_source_counts = {os: 24, adapter: 0, launch_failed: 2}`，`primary_metrics.evaluable = true`。[artifact: out/r12-gate-input.json sha256=bf6d3ca51b96b16e49108f1419eede14401ed3a3d8e72af55973f9a862623058][artifact: out/r12-gate-metrics.json sha256=7fcc037291174728aba2241e287f5395ab8e85195a22a29dd0aa8a3439a74cc3][artifact: tools/eval/gate_metrics.py sha256=fbd4fd361fded6d10e2e676152ccd3d55a74203a010e0c601fecd2cf77e12ff6]

- **结论 R13**：（主指标可评估且不进门结论）`precision 0.5` / `recall 1.0` / `pass_rate 0.8` 均非 null，2×2 `TP8 TN4 FP8 FN0`、主样本 20 条、排除 4 条（真 exit=3，按 §17 可判定规则逐条留痕）。`main_supports` 来自红区主轨只读真实调用（E4 12 / E2 12），`predicate_ok` 来自采集层真实观测，二者互不预置 expectation。产物仍标 `gate_result = not_evaluable` 且不含任何门值数值。[artifact: out/r12-gate-metrics.json sha256=7fcc037291174728aba2241e287f5395ab8e85195a22a29dd0aa8a3439a74cc3][artifact: out/r12-gate-input.json sha256=bf6d3ca51b96b16e49108f1419eede14401ed3a3d8e72af55973f9a862623058]

- **结论 R14**：（抽样复核机制，对抗问题 4）采集层对 24 条 `os` 样本各自在**新的隔离子进程**重跑同一段代码并逐条比对 OS returncode，`verified 24 / all_match true / mismatches []`；每条落盘 `python_code / os_command / observed_returncode / observed_stdout_head / env_isolation` 供评审独立抽样复跑。2 条 `launch_failed` 由真实 `FileNotFoundError` 触发，`launch_failed_counted_as_unsupported = 0`（ADV-5 三态口径）。[artifact: out/r12-gate-input.json sha256=bf6d3ca51b96b16e49108f1419eede14401ed3a3d8e72af55973f9a862623058][artifact: ../round12-custody/collect_r12_os.py sha256=5f3136158bb87b70bd83e13efcdeed85a7889eeddc2a3e719bf23ef188f5fc1e]

- **结论 R15**：（探针判别力达冻结阈值）`strict_bool_disagreement_rate = 0.18 ≥ 0.15`、`n_families = 5`、`n_probe = 50`；严格率分母为**全体 50 条**（`strict_rate_denominator_policy = ALL probe cases; no sample removed`），未从分母剔除任何样本。`disagreement_rate = 0.62`、严格分歧 9 条。[artifact: out/r12-probe-report.json sha256=47b74f1568ae4522c7c421956b33f2a78030b61b0bd6a7bb3bfe61b6bf9e99ed][artifact: tools/eval/probe_runner_r12.py sha256=4a13cf8db777b0e3ad85f071d3493b1715ffd7df0a45a494a9ce370994d28114]

- **结论 R16**：（阈值未下调 / 新族非自证，对抗问题 3）运行器从 §19 D19-D 冻结常量表**读回** `0.15` 与本地常量比对（`threshold_matches_section19 = true`、`threshold_lowered_after_data = false`），不一致直接 exit 2。新增族 10 条中 3 条一致对照、4 条真结构性不可判（弃权型分歧、不计入严格布尔）、仅 3 条有-ref-无-cmd 边界样本产生真实严格分歧；族内 `strict 3 / agreeing_control 3`，**不是被设计成必然分歧**，探针集 `EXPECTATION_LABELS_STORED False`。[artifact: out/r12-probe-report.json sha256=47b74f1568ae4522c7c421956b33f2a78030b61b0bd6a7bb3bfe61b6bf9e99ed][artifact: tools/eval/probe_set.json sha256=92dbb9552b011e64637b6c5cd6af6c75e7ba4aa5db6930255b58a6ae81c5f6c2][artifact: ../round12-custody/probe_set_r12.py sha256=97a92271359ff409fda5ff62e582ad10946163d25ba278bbd412bba83ca0259c]

- **结论 R17**：（盲态序与隔离）独立 v3 先跑 50 条 → SHA 封存 → 主轨只读调用 → 比对；`main_track_invoked_before_seal = false`；`probe_runner_r12.py` 亦调用共享隔离模块且 `env_isolation_all_checks_pass = true`。[artifact: out/r12-probe-independent-blind.json sha256=ae8f9ef9777d46cbee175d3d714a92f3c5e0e6ce2c5cb38d63c86e97ac11ce13][artifact: out/r12-probe-seal-log.json sha256=40088ceb0d5d9a7c4b9535a98c1c92ec043de08d1701f4dae4b020dc1ecf6384]

- **结论 R18**：（双标注照实降级）单 agent 环境无法提供两名独立人类标注者；`annotator_count = 1`、`two_human_independent_annotation = false`、`independence_satisfied = false`、`triangle_verdict = not_evaluable_no_independent_human_annotation`、`caliber = single_agent_dual_view_direction_only`。view B 为本轮真实重测的 v3 判级，非复制 v2 标签；可比 22 条、一致 13 条、`agreement_rate 0.590909` 仅作方向诊断，不记为双人独立，0 分歧不证明独立性。**不得记为双人独立**。[artifact: goldset/calibration_r12.jsonl sha256=9f8f7a0748e26fd78ca56208814d49b114680354d5775480940389d42c170347][artifact: out/r12-calibration-summary.json sha256=946db8da232e0ce22d1acba9bda7ef49af745b43fb545c18a0d82d0259cf3495][artifact: ../round12-custody/build_calibration_r12.py sha256=211b71ae1f8dfdf90c17410cc8607bebb937cc69e7fcdab833b86b521195bcfb]

## 四、ADV-1 / ADV-2 / ADV-4 / ADV-5 闭合状态（按 §19 D19-D 冻结判据查表）

报告只查表，不解释。判据在 D0 数据前冻结于 §19 D19-D。

| advisory | 冻结判据 | 实测 | 状态 |
|---|---|---|---|
| ADV-1 环境隔离 | V2 `has_clean_env` + 复算脚本统一调用 | `has_clean_env=True`、源码前 400 字符含两关键词、隔离子进程五项 checks 全 True；`r12_reliability.py` / 采集脚本 / `probe_runner_r12.py` 均调用共享模块 | **闭合** |
| ADV-2 exit_source 采集 | V3 `os>0` / `adapter=0` / `primary.evaluable=true` + 采集层产出 | `os 24 / adapter 0 / launch_failed 2`、`evaluable true`、`provenance_text_used_for_inference=false` | **闭合** |
| ADV-4 弃权归因 | V4 双分母并列 + `trace_complete` + 逐条留痕 | `400 / 370` 并列、trace 30 行、`trace_complete=true`、弃权 226→226 不变；但 §19 字面定义只覆盖 60 条中的 30 条 | **部分闭合（30/60）** |
| ADV-5 exit_code 口径 | 三态 + 抽样复核 | 三态齐、`launch_failed_counted_as_unsupported=0`、24 条 returncode 全量复核一致 | **闭合（本轮采集样本集内）** |
| ADV-6 独立性 | 不在本轮范围 | 轮十一裁定「独立性不可满足」永久生效 | **不在范围，未闭合** |

- **结论 R19**：（查表结果）ADV-1 / ADV-2 / ADV-5 闭合，ADV-4 部分闭合、ADV-6 不在范围；**本轮不因此宣布 `not_evaluable` 解除**，门结论仍归下一轮。四项闭合均为「仪器/采集管线」闭合，不得叙述为影子轨能力提升。[artifact: docs/eval-prereg.md sha256=0975c1bdfc6acfb2554704307e41498db4a5842052c307c8faafeb2f4220cf49][artifact: out/r12-decomposition.json sha256=d5989b0a6436454054195cafab0df5e6d1fd1019641677fd2a9a03b2524edb52][artifact: out/r12-gate-metrics.json sha256=7fcc037291174728aba2241e287f5395ab8e85195a22a29dd0aa8a3439a74cc3]

## 五、边界、口径取舍与未闭合项（照实登记，交浮香裁定）

- **结论 R20**：（卡面 D7 与禁令 1 的口径取舍）卡面 D7 字面写「R_main 复算仅作校准参考」，但 §19 禁令 1 + §18 条款 2 + 轮十一 V7 否决项禁止第二次 R_main 计数（出现第二个门值数值即整轮 `invalid`）。本轮取**更严口径**：不重跑 R_main、不重算门值，以「400 条弃权分解复算」作为校准证据并同样标注不进门结论。此为口径取舍，非执行遗漏，交浮香裁定。[artifact: docs/eval-prereg.md sha256=0975c1bdfc6acfb2554704307e41498db4a5842052c307c8faafeb2f4220cf49][artifact: out/r12-decomposition.json sha256=d5989b0a6436454054195cafab0df5e6d1fd1019641677fd2a9a03b2524edb52]

- **结论 R21**：（§19 条款 2 的措辞张力）冻结条款字面要求「证据行存在」，同时锚定「C-1 的 60 条 PARSE_FAIL」；实测二者相差 30 条空证据行样本。执行者不事后改写冻结文本，选择严格字面执行并把差额单列披露，ADV-4 因此只部分闭合。是否在下轮扩充定义交裁定。[artifact: docs/rubric-v3-r12.md sha256=7bb9220e97c556e22c535c381047d91caabcee6a533a800605d7303269a8d04b][artifact: out/r12-abstention-decomposition.json sha256=97091832be84c634b34414b161114f8e1373121318f49c393765ba5646ea40c8]

- **结论 R22**：（本轮采集样本的性质）D3 的 26 条样本是**仪器校准样本集**，用于证明真实 OS 采集管线接通；轮十 210 pairs 实测无任何可执行命令字段（6 项计数全 0），无法重观测。这**不是新一轮真数据门轮**，`zero_new_data_disclosure` 已在采集产物中写明。[artifact: out/r12-gate-input.json sha256=bf6d3ca51b96b16e49108f1419eede14401ed3a3d8e72af55973f9a862623058]

- **结论 R23**：（历史脚本不回写）`exit_fixture.py`（轮十一冻结夹具）与 `round11-custody/r11_reliability.py`（轮十一封存复算脚本，带 `FIRST_RUN_ONLY` 保护）不在本卡 Owned files，回写会破坏轮十一「只跑一次」证据链；共享隔离模块为逐字提取，本轮所有复算脚本统一调用，历史两处的不一致如实披露而非宣称消除。[artifact: tools/eval/env_isolation.py sha256=40b8921a53c796d0c0f1d7af0a15b375068a241a12ce7640d65cf47c3085e3c3][artifact: tools/eval/r12_reliability.py sha256=eda440df9d9e302832a0ce1ca6c809ce551b6ab3791656d6e5d88e04ae1515b5]

- **结论 R24**：（验收残留不刷绿）V10 `lint_cards.py --strict` 存在 2 条结构性 WARN —— `VERDICT_WITHOUT_REVIEW`（执行者不得写 verdict 的直接后果）与 `TEST_COUNT_UNVERIFIED`（lint 内绝对路径测试发现报 import failure，仓库既有，与轮十一同形）；`--strict` 下 WARN 即 FAIL。V9 字面单测受 `COVENANT_BASH_HINT` Windows 环境依赖影响，带真实 bash 路径另跑登记。二者均不通过改红区 `tools/lint_cards.py`、不伪造 verdict 来刷绿，逐条交裁定。[artifact: docs/eval-prereg.md sha256=0975c1bdfc6acfb2554704307e41498db4a5842052c307c8faafeb2f4220cf49]

## 六、冻结序、红区与纪律

§19 冻结 commit `353bcb4` 早于一切 `run-dir-r12/` / `shadow-r12/` / `out/` 轮十二产物（`r12_products_before_freeze = []`）。红区完整路径为 `tools/eval/judge.py`、`tools/eval/extract.py`、`tools/eval/blind.py`、`tools/eval/report.py`、`tools/eval/stats.py`、`tools/eval/study_runner.py`、`tools/eval/seal_run.py`、`tools/gate.py`、`tools/lint_cards.py`、`verdicts/`、`.eval-sealed/`，本轮零触碰；主轨 `judge.py` 仅被只读调用。CI py3.9：全部新增脚本经 `ast.parse(feature_version=(3,9))`，未给 Path 文本写入方法传 `newline` 关键字，JSON 写入一律 `open(..., newline="")`。V1–V10 由执行者亲跑并粘贴真实退出码，不采纳作者 precheck。

- **结论 R25**：本轮不写 verdict、不 push、不 merge、不自评审、不碰 master；收尾为 seal 移交 custody → `artifacts.json` 补登记 → 卡转 `IN_REVIEW` → 递浮香 → 停手等 Orchestrator 预审 + 浮香 PASS gate。[artifact: docs/eval-prereg.md sha256=0975c1bdfc6acfb2554704307e41498db4a5842052c307c8faafeb2f4220cf49][artifact: out/r12-calibration-summary.json sha256=946db8da232e0ce22d1acba9bda7ef49af745b43fb545c18a0d82d0259cf3495]

- **结论 R26**：（验收前封存确定性修复，照实补记、不粉饰为「未重跑」）D6 指针校验发现 `out/r12-probe-seal-log.json` 含 `sealed_at_utc` 墙钟字段，而 V5 字面命令在验收时必然重跑 `probe_runner_r12.py`，会改变该 seal-log 的 sha256 并使本报告 R17 指针失效。修复方式为去掉墙钟字段、改为**内容哈希确定性封存**（`deterministic_seal = true`、`seal_basis` 明写依据）：盲态序不再靠时间戳，而由代码路径（stage 1 独立先跑并哈希后才进入 stage 2 主轨）与 `main_track_invoked_before_seal = false` 证明。**这是验收前仪器确定性修复后的确定性重放，不是第二次 V5 计数**：机械对比显示 `out/r12-probe-report.json`（`47b74f15…`）、`out/r12-probe-independent-blind.json`（`ae8f9ef9…`）与 custody 副本三份哈希逐字未变，`strict_bool_disagreement_rate = 0.18`、`n_families = 5`、`n_probe = 50`、`by_family` 全部一致，唯一变化仅为 seal-log 元数据（修复前旧值留档 `r12-probe-seal-log.pre-deterministic-fix.json`）。V5 字面命令再次重跑后三份产物哈希完全不变，幂等已验证；冻结阈值 `0.15`、探针集、判级实现、门结论口径均未改动，未事后下调阈值、未删样本、未产生第二个门值。[artifact: tools/eval/probe_runner_r12.py sha256=4a13cf8db777b0e3ad85f071d3493b1715ffd7df0a45a494a9ce370994d28114][artifact: out/r12-probe-seal-log.json sha256=40088ceb0d5d9a7c4b9535a98c1c92ec043de08d1701f4dae4b020dc1ecf6384][artifact: ../round12-custody/r12-probe-seal-log.pre-deterministic-fix.json sha256=4e4130bd956cd2af8a31e99bb02f1d6ced929db20be89a139ff066094918dbd4][artifact: out/r12-probe-report.json sha256=47b74f1568ae4522c7c421956b33f2a78030b61b0bd6a7bb3bfe61b6bf9e99ed]
