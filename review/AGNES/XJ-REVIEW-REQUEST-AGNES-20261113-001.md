# 递评单 · XJ-20261113-001（轮十四 真值源有效性校验与无锚假支持测量·分层报告骨架）

> 递评人：WorkBuddy（执行者代号 **WB**）· 2026-11-13
> 评审员：**浮香（AgnesCode）**；Orchestrator 预审
> 仓库：`D:\15812\projects\agent-covenant` · 分支 `feature/xj-20261113-001-round14-strata` · 基线 master `3126899` · 接卡点 `66f547c`
> 状态：**IN_REVIEW**（D1–D6 交付完成；V1–V10 亲跑 17 条命令、1 项非零残留照实登记；**执行者不宣布验收通过**）
> 执行者无评审权、无合并权：不 push / 不 merge / 不写 verdict / 不自评审 / 未碰 master

---

## 1. 一句话结论

**本轮是报告层测量轮，不出门结论。** §21 在轮十四任何数据产物之前冻结（`89264dc`，纯追加 `165/0`，§0–§20 前缀 SHA `4abeb255…` 前后逐字节一致），D2–D6 只做实现、查表与机械验证。三件事全部复现卡面事实：①F2——`design_error_class` 133/133 标签惰性、矛盾 0，**真值资格被机械证伪**；②F1——无锚假支持 30/150 = 20.0%、bootstrap 95% CI 上限 0.2667 > 0.15，按冻结定级表判 **`high`**（`severity_source = frozen_table`）；③分层骨架——三 stratum 建立且守恒（118+0+0 = 118、292+108 = 400），主 `R_main = 1.0` 分母 118 封存只读、逐位未动，`R_main_anchored = 1.0` 并列另出。`gate_result = not_evaluable`、`gate_conclusion_issued = false`、`capability_gain_claim = false`。

## 2. 交付清单（D1→D6）

| 阶段 | commit | 交付物 | 关键实况 |
|---|---|---|---|
| 接卡 | `efa20c6` | 卡面 Status | OPEN → IN_PROGRESS，代号 WB；接卡点 `66f547c`，接卡时工作树干净、零 r14 产物 |
| D1 | `89264dc` | `docs/eval-prereg.md` §21、`.gitignore` 补 `run-r14/` | **冻结早于一切 r14 产物**（D21-A 执行者预冻结复算全部为控制台输出、零落盘）；纯追加 `165/0`；D21-B 7 条款 + D21-C 4 禁令 + D21-D 冻结常量 + D21-E 机器可读 `r14-truth-frozen-v1` 块；`.gitignore` 不在 Owned files，照实登记交裁定 |
| D2 | `2b42d94` | `tools/eval/verify_truth_source.py`、`out/truth-source.json` | 规则全部从 §21 D21-E 机械读回；`holdout_labels_inert 133/133`、`contradictions 0`、三分 cmd 59 / ref 在场 59 / ref 缺席 15、方向核验 15/15 |
| D3 | `a701646` | `tools/eval/measure_unanchored_fp.py`、`out/unanchored-fp.json` | `false_support 30`、`false_support_rate 0.2`、`anchor_miss_e4 30/30`；bootstrap B=2000 seed=20261113 → `fp_upper95 0.266667`；severity `high`（`frozen_table`）；M1 各臂影响块（diagnostic_only） |
| D4 | `3779d22` | `tools/eval/report_strata.py`、`out/strata.json` | 分层隶属逐格对照封存 v4 分解（fail-fast）；`sum_strata==comparable_set True`、`primary_denominator_changed False`、`r_main 1.0`（封存只读）、`r_main_anchored 1.0`、`no_anchor_mapping_count 0` |
| D5 | `3bd8721` | `docs/eval-report-r14-strata.md` | 7 节 / **8 条结论 / 13 个方括号指针 + 8 个圆括号指针**；`verify_artifact_pointers.py` → `COVERAGE 100.0% / BAD_DIGEST 0 / MALFORMED 0 / RESULT PASS`；§0 最显眼主/锚双读数防误读声明 |
| D6 | 本次收尾 | `run-r14/seal.json`（8 文件）、custody 副本、`artifacts.json` 三条台账、卡转 `IN_REVIEW`、本递评单 | `VERIFY: OK (8 files match the seal)`；`not_true_data=true`；产物哈希在验收重跑后逐字节未变 |

## 3. 关键读数（全部来自亲跑产物）

| 项 | 读数 | 说明 |
|---|---|---|
| 冻结序 | §21 冻结 `89264dc` 早于 D2–D6 全部产物 | `git diff 3126899 --numstat -- docs/eval-prereg.md` = `165 0`（删除列 0）；前缀 SHA（LF 口径）`4abeb255…` 冻结前后一致，CRLF 原始口径 `53d43d1b…` 同样一致 |
| F2 真值源 | `133/133` 标签惰性、矛盾 **0** | 133 = cmd 59（29 数值逐字命中 recorded `out=` + 30 无数值位引用）+ ref 在场 59 + ref 缺席 15；`design_error_class` 自此只能以「设计意图记录 / 被证伪对象」身份出现 |
| F1 假支持 | `30/150 = 0.2`、`anchor_miss_e4 30/30` | 机制：零锚点 → `judge.py:379-386` 无锚机械通过 → E4（如 T01-c01：claim `Apache-2.0`、`out=MIT`）；bootstrap 上限 `0.266667 > 0.15` → 定级 `high`（`frozen_table`，非人工裁量） |
| M1 影响 | 主轨臂 33.33% → 反事实 50.00%（**+16.67pp**）；独立轨臂 0.00pp；有锚子集假支持质量 0 | 臂 = 判级臂（主轨/独立轨）；原研究 A/B 臂标签语料不可恢复，照实披露；`caliber = diagnostic_only`，不进门结论 |
| 分层守恒 | anchored 118（可比 118）/ no_anchor 126（可比 0）/ verified_absence 48（可比 0）/ residual 108；292+108=400 | `sum_strata == comparable_set == 118`；`INSUFFICIENT_NO_ANCHOR` 一致性计算出现 **0 次**（V7 exit 0）；`protected_total 96` 未下降 |
| 主 R_main | `1.0` / 分母 `118`，读自封存 `out/r13-alignment.json`，`recomputed=false` | `r_main_identical True` / `denominator_identical True`；`R_main_anchored = 1.0`（分母 118）并列另出，其可比子集经守恒证明恰为封存可比集全体 |
| 门结论 | `not_evaluable`，未 emit 任何门判定 | 无第二个 R_main 门计数、无第二个 M_C、无门值数值 |

**执行者留痕的两处实现裁量（交评审裁定）**：①一致率永不从 rows 文件重算（其主轨判定是轮十一未对齐的陈旧值）——`R_main` 与 `agree` 读自轮十三封存产物，「可比集 = v4 SUPPORT = anchored 层」的等式由封存 118/118/0 + 逐层交叉核对证明；②V6 字段置于 `out/strata.json` 顶层（卡面 V6 的 `d['r_main']` 字面读取口径）。

## 4. Acceptance V1–V10 亲跑退出码（17 条命令，不采纳 precheck）

`round14-custody/acceptance_r14.py` 统一执行（卡面 PowerShell 字面命令以 Python/Git-Bash 等价执行，同轮十三口径差登记）。台账：`r14-acceptance.json` / `.log`（custody）。

```
V1  0 / 0      V2  0      V3  0      V4  0 / 0      V5  0
V6  0 / 0      V7  0      V8  0      V9  0
V10 1(literal) / 0(with real bash hint) / 0(lint)
X   0(pointers) / 0(product hashes)
→ 合计 17 条，非零 1 项：V10_unittest_literal（照实登记，不刷绿）
```

- **V1**：numstat `165 0`；`v1_prefix_sha256 4abeb255…` 冻结前后一致（LF 口径），CRLF 口径 `53d43d1b…` 同验。
- **V2 / V3**：`holdout_labels_inert 133/133`、`contradictions 0`；`false_support 30`、`false_support_rate 0.2`、`anchor_miss_e4 30/30`。
- **V4**：`severity high`、`severity_source frozen_table`。
- **V5 / V6 / V7**：`sum_strata==comparable_set True`、`primary_denominator_changed False`；`1.0 118 1.0`、逐位一致三 True；`no_anchor_mapped 0`。
- **V8**：`git diff 3126899 --stat` 对 11 条红区**完整路径**输出为空、退出码 0（含 `tools/eval/judge.py`、`tools/eval/extract.py`、`verdicts/`、`.eval-sealed/`）。
- **V9**：`VERIFY: OK (8 files match the seal)`，custody 副本 `D:/15812/projects/round14-custody/sealed/run-r14`。
- **V10_unittest_literal（exit 1）**：`Ran 527 tests ... FAILED (failures=2, errors=3)`，根因单一 `no Git for Windows bash found; set COVENANT_BASH_HINT`（轮十/十一/十二/十三已登记的 Windows 依赖，同形）；**改用真实 bash 路径另跑 `Ran 546 tests ... OK`（exit 0）**。不刷绿。
- **V10_lint（exit 0）**：`LINT: PASS (2 warnings)`，0 errors——`VERDICT_WITHOUT_REVIEW`（执行者不写 verdict 的直接后果）+ `TEST_COUNT_UNVERIFIED`（lint 内部 discovery 无 hint 抛错的既有问题）。不伪造 verdict、不改红区 `tools/lint_cards.py` 刷绿。
- **确定性**：三份 r14 产物在全部验收重跑后 SHA 逐字节不变（`True/True/True`）；报告指针复验 PASS。

## 5. 未闭合项（照实登记，交浮香裁定）

1. **层语义真值的残余循环性**：层定义由样本生成器给出、非外部基准；本轮以「生成器设计属性 + fixture 机械核对（133 条内容可核查行零矛盾）」作为真值源口径并如实登记（报告结论 C3），是否需第三方基准复核待裁定。
2. **`severity = high` 的处置落地**：「正式门结论仅用有锚子集」与 §17/§18 门条款的衔接表述（及是否构成门放松——报告 §0/结论 C8 给出「移除的是假支持质量本身」的量化论据），待裁定。
3. **15 条 `ref_absent` 行**与轮十三 `VERIFIABLE_ABSENCE` 升级候选线索的归并，待裁定。
4. **M1「各臂」口径**：本轮按判级臂（主轨/独立轨）量化并披露边界；若需按原研究 A/B 研究臂量化，须在含臂标签的新语料上另行立项。

## 6. 卡面评审问题对照（执行者立场，供评审起点）

- 问 1（30 例是否全为矛盾+零锚）：是——30 条全部 `anchor_miss` 层、值位引用为非数值 token、证据面无该 token（报告结论 C4 与 `out/unanchored-fp.json` counterexamples 逐条列出）；无一例「断言其实为真、层标签错判」。
- 问 2（F2 是否过度解读）：非 TIMEOUT 类独有——五类标签（含 TIMEOUT 27 条）全部惰性；且 15 条 ref 缺席行登记 `unverifiable` 而非「真」，未把「无矛盾」过度说成「已证真」。
- 问 3（循环论证）：见未闭合项 1，已在结论 C3 正面登记残余风险。
- 问 4（双读数误读）：报告 §0 置顶防误读声明 + 结论 C6；`R_main_anchored` 本轮与主读数同值的原因（可比集全等）已量化说明。
- 问 5（变相放松门）：结论 C8——有锚子集内假支持质量为 0，分层移除的是偏置质量；主分母未缩小。
- 问 6（anchored 样本量）：结论 C7——118 条可比，本轮不做功效声明，升层须先过样本量下限（§13 ⑦ 先例：每臂 30 对）。

---

*执行者：WB（WorkBuddy，ZCode 桌面会话，模型 GLM-5.3-Flash）· 2026-11-13 · 本单不构成验收通过，等待 Orchestrator 预审 + 浮香 PASS gate。*
