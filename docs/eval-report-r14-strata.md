# 轮十四 · 真值源有效性校验与无锚假支持测量（分层报告骨架，不进门结论）

> 卡：XJ-20261113-001 · 分支 feature/xj-20261113-001-round14-strata（基线 master `3126899`）· 执行者 WB（WorkBuddy，ZCode 桌面会话）· 预注册 §21 冻结 commit `89264dc`（早于一切 r14 产物）
> 性质：报告层测量轮。`gate_result = not_evaluable`、`gate_conclusion_issued = false`、`capability_gain_claim = false`；主 `R_main` 与分母只从轮十三封存产物读入，永不重算。

## 0. 口径声明（写在一切读数之前——主/锚双读数防误读）

**最显眼的防误读声明**：本报告同时给出主 `R_main = 1.0`（分母 118）与 `R_main_anchored = 1.0`（分母 118）。读者最容易犯的误读是「既然加了 anchored 读数，是不是正式门以后只用有锚子集、门更容易过」。**不是**：

1. 主 `R_main` 的分子、分母**逐位不变**（分母仍为轮十三封存可比集 118，读自封存产物、非重算；`primary_denominator_changed = false`）；
2. `R_main_anchored` 只是**并列另出**的诊断读数；本轮三 stratum 的可比行守恒证明 anchored 可比子集**恰好等于**封存可比集全体（118 = 118 + 0 + 0），`no_anchor` / `verified_absence` 两层按轮十三冻结政策是保护性弃权、可比贡献恒为 0——本轮没有任何一行从主分母移入或移出；
3. 定级 `high` 触发的处置「正式结论仅用有锚子集」移除的**恰是假支持质量本身**（有锚子集内假支持 = 0，见结论 C6），不是把任何真实通过门槛调低；旁路读数任何上升均不得叙述为能力提升。

本轮语料不可恢复原研究 A/B 研究臂标签；「各臂」按 §21 条款 5 冻结口径取**判级臂**（主轨臂 / 独立轨臂），并照实披露该边界。

## 1. 冻结序与合法性

§21（v2.2 → v2.3）以纯追加冻结于轮十四任何产物之前：`git diff 3126899 --numstat -- docs/eval-prereg.md` = `165 0`（删除列 0）；§0–§20 前缀 SHA256（V1 文本口径，universal newlines → LF）冻结前后逐字节一致 = `4abeb25527682b6da4b889012c984355c159ea5743e7c82bd3e3ab65f1a0e58b`（CRLF 原始口径同为 `53d43d1b76e6bb9bee2eb470be0d391f261d8c0bd81fad9a1aefa4b3ecb0f3a8`）。冻结 commit `89264dc` 早于 D2–D6 全部执行产物；执行者接卡时 `r14_products_before_freeze = []`（D21-A 复算全部为控制台输出、零落盘）。

- **结论 C1**：§21 冻结为纯追加、前缀逐字节不变、冻结序合法；三个工具的全部规则从 §21 D21-E 机器可读块机械读回（同轮十三 `label_mapping.py` 读回 §20 矩阵先例），代码不携带任何脱离冻结文本的阈值。 [artifact: docs/eval-prereg.md sha256=b1b32c49d33f814b2440bf60c4cde71ac4c842291959805d4e0a73ff11d4b226]（docs/eval-prereg.md）b1b32c49d33f814b2440bf60c4cde71ac4c842291959805d4e0a73ff11d4b226

## 2. F2 实测：`design_error_class` 不能作 HOLDOUT 真值（真值源有效性）

对轮十一封存 400 条（`out/r11-blind-samples.json` × `out/r11-reliability-rows.json`，SHA 由工具对冻结块逐字节核验）逐条机械复核：

- `design_error_class != NONE` 共 **133 条，全部在 HOLDOUT 层**（类别构成 CWD_MISMATCH 27 / FILE_NOT_FOUND 27 / PARSE_FAIL 27 / SILENT_FALLBACK 25 / TIMEOUT 27）；
- 按冻结矛盾规则（可用证据面 + 值位数值引用 + 引用缺席于证据面）：**矛盾 0 条**；三分构成 = cmd 型 59（29 条数值引用逐字命中 recorded `out=` + 30 条无数值位引用，如 `Apache-2.0` / `零` 等非数值值位）+ ref 型 fixture 在场 59 + ref 型 fixture 缺席 15；
- fixture 缺席的 15 条（全为 `ref_missing` 层）登记 `unverifiable`，方向核验 `main_level != "E4"` 全部通过；
- **判定：133/133 标签惰性**——HOLDOUT 层「注入错误」实际未生效，`design_error_class` 在本轮只能以「设计意图记录 / 被证伪对象」身份出现，**禁止**作为任何真值计算输入。

- **结论 C2**：F2 被独立复现——`holdout_labels_inert 133/133`、`contradictions 0`、三分 59/59/15、方向核验 15/15；`design_error_class` 的真值资格被机械证伪。 [artifact: out/truth-source.json sha256=bcfe1a9ddd8d880dddc00a32ce3e86235b8a768b70855fe2f4c5b8731ba4a706]（out/truth-source.json）bcfe1a9ddd8d880dddc00a32ce3e86235b8a768b70855fe2f4c5b8731ba4a706 [artifact: tools/eval/verify_truth_source.py sha256=35c03f758ae6b98594a41912a6cddde1ce90cecc6110856e8cba9fe152c525fb]（tools/eval/verify_truth_source.py）35c03f758ae6b98594a41912a6cddde1ce90cecc6110856e8cba9fe152c525fb
- **结论 C3**：本轮真值源口径 = **层语义 + fixture 机械核对**（`layer_semantics_plus_fixture_mechanical_check`）。循环论证处置（对抗问 3 正面答案）：层语义是**生成器设计属性**（层由样本生成器的注入设计定义，不由任何判级器输出定义），且全部内容可核查行的数值引用已对照证据面机械核实（cmd 29 条逐字命中、ref 59 条在 fixture 内容中命中、矛盾 0）；「被测物」是判级器，真值不来自判级器。残余循环性风险（层定义本身由生成器而非外部基准给出）照实登记，交评审裁定。 [artifact: out/truth-source.json sha256=bcfe1a9ddd8d880dddc00a32ce3e86235b8a768b70855fe2f4c5b8731ba4a706]（out/truth-source.json）bcfe1a9ddd8d880dddc00a32ce3e86235b8a768b70855fe2f4c5b8731ba4a706 [artifact: out/r11-blind-samples.json sha256=6d61994c7104747a797658b72733898b5c833b07715155e3aba0c987b4b9fcc9]（out/r11-blind-samples.json）6d61994c7104747a797658b72733898b5c833b07715155e3aba0c987b4b9fcc9

## 3. F1 实测：无锚假支持 30/150 = 20.0%，定级 high

R10_ANCHOR 层 240 条，按层语义真值 × 主轨判定交叉表（封存复现）：

| 真值 | 主轨判定 | 条数 |
|---|---|---|
| TRUE | E4 | 90（全部正确） |
| FALSE | E0 / E1 / E2 | 30 / 30 / 60（弃权向，全部正确） |
| **FALSE** | **E4** | **30（假支持）** |

- `false_support = 30`（分母 = FALSE 层 150），`false_support_rate = 0.2`；`anchor_miss_e4 = 30/30`（anchor_miss 层全军覆没）；
- 机制坐实：30 条假支持的 claim 值位引用为非数值 token（如 `Apache-2.0`），主轨锚点正则 `(?<![\w.\-])\d+(?![\w.\-])` 正确排除后提取到**零锚点**，落入 `judge.py:379-386` 的「无锚机械通过」分支 → E4（断言内容与证据直接矛盾仍判支持，如 T01-c01：claim `Apache-2.0`，`out=MIT`）；
- bootstrap 95% CI（B=2000、seed=20261113、有放回、近邻秩百分位）：`fp_upper95 = 0.266667 > 0.15` → 按冻结定级表判 **`high`**（`severity_source = frozen_table`），处置 = **上报 sir + 正式结论仅用有锚子集**。

- **结论 C4**：F1 被独立复现——`false_support 30`、`false_support_rate 0.2`、`anchor_miss_e4 30/30`；`fp_upper95 0.266667`，按 §21 D21-E 冻结定级表判 `high`，非人工裁量（`severity_source = frozen_table`）。 [artifact: out/unanchored-fp.json sha256=bbab0f6fe8ee911e1dfa84075a51dffc37ec7a1b8c4a6915c241b299160faca0]（out/unanchored-fp.json）bbab0f6fe8ee911e1dfa84075a51dffc37ec7a1b8c4a6915c241b299160faca0 [artifact: tools/eval/measure_unanchored_fp.py sha256=644591f623efd69b6bc5adaf1d20f253bb8543beacbfa34cf008f6b59f240b8f]（tools/eval/measure_unanchored_fp.py）644591f623efd69b6bc5adaf1d20f253bb8543beacbfa34cf008f6b59f240b8f

## 4. 分层读数：三 stratum + residual + 守恒

分层隶属函数（§21 条款 4 冻结）：逐行 rubric v4 类别 = 层映射 + 主轨锚点规则逐字重抽取；**逐层聚合与封存 `out/r13-rubric-v4-decomposition.json` 的 `per_layer_classes` 逐格相等（fail-fast 通过）**。守恒：292 + 108 = 400。

| stratum / residual | v4 类别 | raw | 可比 | 弃权 |
|---|---|---|---|---|
| `anchored` | SUPPORT | 118 | **118** | 0 |
| `no_anchor` | INSUFFICIENT_NO_ANCHOR | 126 | **0**（保护性弃权） | 126 |
| `verified_absence` | VERIFIABLE_ABSENCE | 48 | **0**（保护性弃权） | 48 |
| residual | SILENT_FALLBACK_PROTECTED 48 / STRUCTURALLY_UNJUDGEABLE 30 / NO_EVIDENCE_LINE 30 | 108 | 0 | 108 |

- `sum_strata == comparable_set`：**True**（118 + 0 + 0 = 118）；
- `INSUFFICIENT_NO_ANCHOR` 在一致性计算中出现 **0 次**（`--check-no-anchor-mapping` exit 0）——独立轨对无锚 claim 的弃权（ADV5.C5）构造性维持；
- `protected_total = 96`（SILENT_FALLBACK 48 + VERIFIABLE_ABSENCE/FILE_NOT_FOUND 48）封存值未下降；
- 无锚 claim 70 条（v2 口径 `ref_ok 48 + goldset_text 22`）维持 `INSUFFICIENT_NO_ANCHOR` 弃权，未映射布尔。

- **结论 C5**：三 stratum 建立且守恒成立——`sum_strata == comparable_set == 118`（True）、residual 108 显式列报（292+108=400）、逐层聚合与封存 v4 分解逐格相等、`INSUFFICIENT_NO_ANCHOR` 一致性映射 0 次。 [artifact: out/strata.json sha256=ac0d3b25380d50d9c69af07371a0e8b9f4b3b5bcc2077258cf4c635fc1cc7c60]（out/strata.json）ac0d3b25380d50d9c69af07371a0e8b9f4b3b5bcc2077258cf4c635fc1cc7c60 [artifact: tools/eval/report_strata.py sha256=56cdefec1f84dc49535627fe34ce9a0a0d984c9eb8e06bc5e20095bc0702bdd1]（tools/eval/report_strata.py）56cdefec1f84dc49535627fe34ce9a0a0d984c9eb8e06bc5e20095bc0702bdd1
- **结论 C6**：主 `R_main` 未被更换——`r_main = 1.0`、`r_main_denominator = 118`（读自封存轮十三对齐产物，`recomputed = false`，`primary_denominator_changed = false`）；`R_main_anchored = 1.0`（分母 118）并列另出，且其可比子集经守恒证明恰为封存可比集全体；无锚弃权映射 0 次。 [artifact: out/r13-alignment.json sha256=a3e37809d8b2cb7743c1ca8a533ae5f4f167cab37506f979c828aee17c5df181]（out/r13-alignment.json）a3e37809d8b2cb7743c1ca8a533ae5f4f167cab37506f979c828aee17c5df181 [artifact: out/strata.json sha256=ac0d3b25380d50d9c69af07371a0e8b9f4b3b5bcc2077258cf4c635fc1cc7c60]（out/strata.json）ac0d3b25380d50d9c69af07371a0e8b9f4b3b5bcc2077258cf4c635fc1cc7c60
- **结论 C7**：样本量与功效边界（对抗问 6 正面答案）：anchored 可比 118、no_anchor 126、verified_absence 48——本轮**不做任何统计功效声明**，`no_anchor` / `verified_absence` 两层只作诊断附录；若未来把任何一层升为正式结论面，须先过样本量下限（§13 ⑦ 先例：每臂最低可比 30 对）并单独立项。 [artifact: out/strata.json sha256=ac0d3b25380d50d9c69af07371a0e8b9f4b3b5bcc2077258cf4c635fc1cc7c60]（out/strata.json）ac0d3b25380d50d9c69af07371a0e8b9f4b3b5bcc2077258cf4c635fc1cc7c60

## 5. M1 各臂绝对失败率影响量化（caliber = diagnostic_only，不进门结论）

M1 定义沿用 v1.2 C5 冻结口径 `M1 = (E2+E3)/(E2+E3+E4)`；臂 = 判级臂（主轨臂 / 独立轨臂；原研究 A/B 臂标签在本语料不可恢复，照实披露）：

| 臂 | population（R10_ANCHOR） | 实测 | 反事实 | 绝对影响 |
|---|---|---|---|---|
| 主轨臂 | 240（E0 30 / E1 30 / E2 60 / E4 120） | M1 = 60/180 = **33.33%** | 30 条假支持按机制归属重分类 E3a（事实不支持）→ M1 = 90/180 = **50.00%** | **+16.67pp（相对 +50%）** |
| 独立轨臂 | 布尔可判 68（SUPPORT 38 / NOT_SUPPORT 30） | M1 族 = 30/68 = **44.12%** | 假支持 = 0 → 不变 | **0.00pp** |
| 主轨臂 · 有锚子集 | 30（全部 E4） | M1 = 0/30 = **0.00%** | 假支持质量 = 0 → 不变 | **0.00pp** |

读法（对抗问 5 正面答案）：假支持质量**全部**落在 no-anchor 侧（有锚子集内为 0）——「正式结论仅用有锚子集」移除的是主轨把矛盾断言机械判 E4 的偏置质量，不是把门调松；独立轨臂因对零锚 claim 一律弃权，M1 族不受该偏置污染（其 44.12% 来自正确拒绝 anchor_miss 的 30 条与 38 条真实支持的构成，非假支持）。主 `R_main` 分母不因分层缩小（结论 C6）。

- **结论 C8**：M1 量化——主轨臂实测 33.33% → 反事实 50.00%（+16.67pp，30 条假支持重分类 E3a）；独立轨臂影响 0.00pp；有锚子集假支持质量 0。该块 `caliber = diagnostic_only`，不进门结论、不叙述为能力变化。 [artifact: out/unanchored-fp.json sha256=bbab0f6fe8ee911e1dfa84075a51dffc37ec7a1b8c4a6915c241b299160faca0]（out/unanchored-fp.json）bbab0f6fe8ee911e1dfa84075a51dffc37ec7a1b8c4a6915c241b299160faca0

## 6. 红区与纪律

红区零触碰：`tools/eval/judge.py`、`tools/eval/extract.py`、`tools/eval/blind.py`、`tools/eval/report.py`、`tools/eval/stats.py`、`tools/eval/study_runner.py`、`tools/eval/seal_run.py`、`tools/gate.py`、`tools/lint_cards.py`、`verdicts/`、`.eval-sealed/`（`seal_run.py` 仅只读调用）。主轨 `judge.py` / `extract.py` 冻结不动；`design_error_class` 禁作 HOLDOUT 真值；主 `R_main` 分母未更换；`capability_gain_claim = false`；不 push、不 merge、不写 verdict、不碰 master。V1–V10 由执行者亲跑、真实退出码登记于 `artifacts.json` 的 `_round14_final_XJ-20261113_001` 台账与评审请求单（本报告不内嵌退出码表，以台账为准）。

## 7. 未闭合项（交浮香裁定）

1. 层语义真值的残余循环性（结论 C3 已登记）：层定义由生成器给出、非外部基准，是否需要引入第三方基准复核，待裁定。
2. `severity = high` 的处置落地：正式门结论「仅用有锚子集」在后续门轮的表述方式（以及与 §17/§18 门条款的衔接），待裁定。
3. F2 的 15 条 `ref_absent` 行是否纳入 `VERIFIABLE_ABSENCE` 升级候选的后续处理（轮十三 upgrade_candidate 线索的延伸），待裁定。
4. M1「各臂」口径（判级臂 vs 原研究 A/B 研究臂）：本轮按判级臂量化并披露边界；若需按研究臂量化，须在含臂标签的新语料上另行立项。

---

### 附：产物哈希（生成时实时计算）

| 产物 | sha256 |
|---|---|
| out/truth-source.json | bcfe1a9ddd8d880dddc00a32ce3e86235b8a768b70855fe2f4c5b8731ba4a706 |
| out/unanchored-fp.json | bbab0f6fe8ee911e1dfa84075a51dffc37ec7a1b8c4a6915c241b299160faca0 |
| out/strata.json | ac0d3b25380d50d9c69af07371a0e8b9f4b3b5bcc2077258cf4c635fc1cc7c60 |
| tools/eval/verify_truth_source.py | 35c03f758ae6b98594a41912a6cddde1ce90cecc6110856e8cba9fe152c525fb |
| tools/eval/measure_unanchored_fp.py | 644591f623efd69b6bc5adaf1d20f253bb8543beacbfa34cf008f6b59f240b8f |
| tools/eval/report_strata.py | 56cdefec1f84dc49535627fe34ce9a0a0d984c9eb8e06bc5e20095bc0702bdd1 |
| docs/eval-prereg.md（含 §21） | b1b32c49d33f814b2440bf60c4cde71ac4c842291959805d4e0a73ff11d4b226 |
