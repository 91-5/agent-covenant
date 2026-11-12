# 轮十一 · 四桶 triage（轮十 90 条失配，零新数据）

> 卡 `XJ-20261111-002` · D1 · 2026-11-11 · 执行者 WB
> 依据：`docs/eval-prereg.md` §18 D18-E（codebook 与触发条款在任何轮十一数据之前冻结）
> 定位：本报告**只对轮十已封存产物做分类**，不重判、不改写轮十 verdict、不产生任何新判级数据。

## 1. 结论（每条带 artifact 指针）

- **结论 T1**：轮十 `C = 0.5` 的 90 条失配**全部**归入桶 b（命题层级不一致），占比 **100%**；桶 a/c/d 均为 0，`unclassifiable = 0`，占比和 = 100%。`[artifact: out/triage-r11-summary.json sha256=dedcf473e560325988327738bb8adf6590f1f6bc2b6a80884707bf2e874f4bef]`

- **结论 T2**：桶 b = 100% ≥ 60%，**§18 条款 8 的 `b_ge_60pct` 触发**：「C 这个标量指标作废，改用 2×2 矩阵」。裁决文本逐字取自 §18 逐字并入块的条款 8，非本卡复述。C 自此降为次要指标，主指标为 `(pass_rate, precision, recall)` 三元组 + 2×2 混淆矩阵。`[artifact: out/triage-r11-summary.json sha256=dedcf473e560325988327738bb8adf6590f1f6bc2b6a80884707bf2e874f4bef]`

- **结论 T3**：桶 c = 0% < 10%，**`c_ge_10pct` 未触发**，不判 E7 回归、本轮不降级为修复轮；观测面残留读数照实登记为 0，不作「E7 已彻底修好」的过度解读（本轮 90 条失配中不含 `fallback_probe` 层，该层 30 条因 `FILE_NOT_FOUND` / `SILENT_FALLBACK` 已在可判定率分母外）。`[artifact: out/triage-r11-summary.json sha256=dedcf473e560325988327738bb8adf6590f1f6bc2b6a80884707bf2e874f4bef]`

- **结论 T4**：90 条失配只有 3 个判别键，各 30 条：`anchor_miss / E4 / main_supports=True / predicate_ok=False`、`repro_fail / E2 / False / True`、`ref_missing / E2 / False / True`。三者都是「主轨判证据是否复现 vs 影子判内容/进程状态/文件存在性是否为真」，属命题层级分歧；**不是**影子轨能力读数，也**不是**谓词表达力不足。`[artifact: out/triage-r11.tsv sha256=c339a7ba0bb1e9a1652c1917aa3b9a34ff474cdff34436975fb17bd67b539e41]`

- **结论 T5**：主轨判级交叉核对 **90 / 90 全对**——用 `main-judgements.json[product][cNN]` 的 `level` 逐条比对 gate-input 的 `main_level`，零不一致。这坐实 triage 的分析对象与轮十密封主轨判级是同一批，未发生重判或改写。`[artifact: D:/15812/projects/round10-custody/sealed/run-dir-r10/main-judgements.json sha256=3787cfc571b026bcb5982a629e86812ed946dda1d34e1c16a5469c58c73ed360]`

- **结论 T6**：codebook 输出与冻结规范**字节全等**（SHA-256 同为 `0d6c2a776fae4068cf53ee58b990ef9f5e7ed04be725427fa4b415363793d789`），与 §18 D18-E 登记的锚点一致；codebook 未在看到结果后调整。`[artifact: out/triage-codebook-r11.json sha256=0d6c2a776fae4068cf53ee58b990ef9f5e7ed04be725427fa4b415363793d789]`

## 2. 零新数据声明

输入只有三份**已存在**的文件：`r10-gate-input.json`（轮十封存）、`main-judgements.json`（轮十 seal 正本）、`docs/eval-prereg.md`（§18 冻结文本，只读以抽取条款 8 裁决文本）。`tools/eval/triage.py` 不调用 `judge.py` / `dsl_compiler.py` / `shadow_align.py`，不执行任何被观测命令，不产生新判级、新观测或新抽样。`new_data_generated = false`。`[artifact: tools/eval/triage.py sha256=5a7841733c52f753c6891f0cbfd34958ee563fa8e5807c55e501f7352cc2b41a]`

| 源 | SHA-256 |
|---|---|
| `D:/15812/projects/round10-custody/r10-gate-input.json` | `8260dcad587a9047f935e4bcc08df80e3c552d105bb2a51273d93899df1b3117` |
| `D:/15812/projects/round10-custody/sealed/run-dir-r10/main-judgements.json` | `3787cfc571b026bcb5982a629e86812ed946dda1d34e1c16a5469c58c73ed360` |
| `D:/15812/projects/round11-custody/triage-codebook-canon.json` | `0d6c2a776fae4068cf53ee58b990ef9f5e7ed04be725427fa4b415363793d789` |

## 3. 失配选取口径（照抄冻结 codebook，可复算）

`comparable = not (not_applicable or evaluative or schema_invalid)` → **210**；
`decidable = exit_code == 0 and parse_ok and 无预注册 ERROR 类` → **180**；
`mismatch = decidable and predicate_ok != main_supports` → **90**（与轮十 `confusion_matrix = {TP:90, TN:0, FP:60, FN:30}`、`consistent_pairs = 90` 机械吻合）。
`[artifact: out/triage-r11-summary.json sha256=dedcf473e560325988327738bb8adf6590f1f6bc2b6a80884707bf2e874f4bef]`

## 4. 四桶分布与查表

| 桶 | 定义 | 条数 | 占比 | 触发 |
|---|---|---|---|---|
| a | 谓词/DSL 表达力（先验 ≈ 0） | 0 | 0% | — |
| b | **命题层级不一致**（先验 ≈ 47%） | **90** | **100%** | `b_ge_60pct = True` → **C 作废，改用 2×2 + 三元组** |
| c | 观测面残留（E7 后应 ≈ 0） | 0 | 0% | `c_ge_10pct = False`，不降修复轮 |
| d | 抽样与 ERROR 口径污染 | 0 | 0% | — |
| unclassifiable | 无规则命中 | 0 | 0% | 须为 0，满足 |
| 合计 | | **90** | **100%** | `no_trigger = false` |

查表结果（`triggers.lookup`）逐字裁决文本：`b` → 「C 这个标量指标作废，改用 2×2 矩阵」；`c` → 「判 E7 回归，本轮降级为修复轮（先修后测，不出 C 结论）」（未触发）。`lookup_only_no_interpretation = true`：本报告只查表，不对阈值做解释性调整。`[artifact: out/triage-r11-summary.json sha256=dedcf473e560325988327738bb8adf6590f1f6bc2b6a80884707bf2e874f4bef]`

## 5. 与 dp 大脑先验的对照（不作裁定）

- 桶 a = 0 与「轮七/八先验 ≈ 0，已死」一致；桶 c = 0 与「E7 后应 ≈ 0」一致。
- 桶 b = 100% **高于** Context 的先验 75/159 ≈ 47%。差异来自本轮 90 条的构成：轮十真数据的失配层只有 `anchor_miss / repro_fail / ref_missing` 三种，全部是命题层级面；这是**样本构成事实**，不是「命题层级分歧在总体上更严重」的证据。不得据此把 100% 外推为影子轨的总体缺陷率。
- 结论 T2 与 §18 条款 7（C 降为次要、三元组 + 2×2 为主）方向一致，但二者是**各自独立冻结**的条款，本轮按条款 8 查表触发，不靠叙述合并。

## 6. 已披露的处置（不修饰）

首次运行 triage.py 时，逐字裁决抽取器按「分号」截断，把句末 `**。` 吞进桶 c 的 `verdict_verbatim`。这是抽取器边界缺陷，不是数据或 codebook 问题；已改为按 `**` 强调对精确定界后重跑，两次的桶计数、占比与交叉核对完全一致，仅裁决文本修正。codebook 规范与 §18 冻结文本**一字未改**。`[artifact: tools/eval/triage.py sha256=5a7841733c52f753c6891f0cbfd34958ee563fa8e5807c55e501f7352cc2b41a]`

## 7. 边界

本卡不写 verdict、不 push、不 merge、不重判轮六–轮十历史轮次。triage 结论的效力限于「轮十 90 条失配的性质判定」；是否接受 C 作废、如何执行 2×2 主指标，交 D4/D6 与浮香评审。
