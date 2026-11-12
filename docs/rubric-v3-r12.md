# rubric v3 · 结构性不可判样本的分层处置

> 卡 `XJ-20261112-001` · D1（卡面 D2）· 2026-11-12 · 执行者 WB
> 上位冻结：`docs/eval-prereg.md` §19 D19-B 条款 2、D19-C 禁令 2、D19-D 冻结常量表
> 实现：`tools/eval/independent_judge.py`（`RUBRIC_V3` / `_judge_case_v3`）、`tools/eval/rubric_v3.py`
> 产物：`out/r12-abstention-decomposition.json`

## 1. 这份规格修的是什么

轮十一 C-2 已实测更正：R10_ANCHOR 层 71.67% 弃权的真因**不是判级器偏置**，而是 rubric v2 未定义「结构上无证据可复现」这一类样本的处置。v2 对这类样本落 `OBSERVATION_ERROR / PARSE_FAIL`，把「仪器没有定义」伪装成「观测失败」。

v3 修的是**判级器定义**，不是判级能力。修完之后弃权样本仍然弃权，只是它们的类别变成显式、可归因、可分层统计。

## 2. 处置定义（§19 条款 2 逐字）

**结构性不可判样本**：证据行**非空**，且 `cmd is None`、`ref is None`、`anchors == []`。即证据面上不存在任何可复现的观测（无命令、无文件引用、无锚点）。

判定函数：`independent_judge.is_structurally_unjudgeable(spec)`，与 §19 D19-D 冻结字符串 `evidence_raw non-empty AND cmd is None AND ref is None AND anchors empty` 一一对应。

判级结果：

| 字段 | 值 |
|---|---|
| `level` | `STRUCTURALLY_UNJUDGEABLE` |
| `supports` | `None`（**仍是弃权**） |
| `error_class` | `STRUCTURAL_NO_EVIDENCE` |
| `score` | `0.0` |
| `structural_basis` | 逐条写明「evidence_raw non-empty, cmd=None, ref=None, anchors=[]」 |

**硬约束**：`supports` 必须保持 `None`。把结构性不可判样本判成 `SUPPORT` / `NOT_SUPPORT` 即为「洗成可判且一致」，直接违反禁令 2。`rubric_v3.py` 用 `no_boolean_laundering` 字段机械核验每一条 trace 行的 `new_supports is None`。

## 3. 两个分母并列（禁止从分母剔除）

| 分母 | 定义 | 冻结值 |
|---|---|---|
| 原始分母 `raw_denominator` | 全部冻结样本 | 400（seed 20261111，`out/r11-blind-samples.json`） |
| 可判分母 `judgable_denominator` | 原始分母 − 结构性不可判样本数 | 按 §19 条款 2 公式计算 |
| 真实可比对分母 `boolean_decidable_denominator` | `supports` 为布尔的样本数 | 额外单列，非冻结公式产物 |

两列必须同时出现在产物与 D6 报告中，`denominators_paired = True`，`excluded_from_raw_denominator = 0`。

**必须说清的一点**：冻结公式给出的 `judgable_denominator` 里仍包含其他类型的弃权样本（OBSERVATION_ERROR / INSUFFICIENT / 空证据行），它**不等于**可比对样本数。本规格额外报 `boolean_decidable_denominator`，防止把冻结公式值误读成能力读数。这是对抗问题 2 的正面回答。

## 4. 为什么弃权数不会下降（不许叙述为能力提升）

v3 对**非结构性样本**逐字委托 v2 决策路径（`_judge_case_v2`），只改 `judge` / `rubric` 标识字段；对结构性样本返回 `supports=None` 的显式类别。因此：

- `abstain_total_v2 == abstain_total_v3`（产物字段 `abstain_unchanged`）；
- 在可比对样本上的一致率**不可能因仪器修订而上升**；
- 产物显式写 `capability_gain_claim = false` 与 `capability_note`。

`rubric_v3.py` 还把 v3 的非结构性逐条结果与轮十一封存的 `out/r11-independent-blind.json` 比对 `level / supports / score / error_class / features`，字段 `v2_v3_equivalence_over_nonstructural.all_equivalent` 必须为真。这同时证明 v2 路径未被漂移、v3 只在结构性样本上改变分类。

## 5. 逐条留痕

`reclassification_trace` 每一行含 `case_id / stratum / layer / original_level / original_error_class / original_supports / new_level / new_error_class / new_supports / basis / evidence_raw / cmd / ref / anchors`。

`trace_complete` 的判据是**独立核算**而非自证：trace 行数 == 独立用 `is_structurally_unjudgeable` 统计出的结构性样本数 == `reclassified_total`，且每行字段齐全、`v2/v3` 等价性无 mismatch、每行 `new_supports is None`。

## 6. 冻结定义未覆盖的样本（如实的部分闭合）

§19 条款 2 字面要求「证据行**存在**」。冻结文本同时把该类锚定到「C-1 的 60 条 PARSE_FAIL」。接卡后实测：这 60 条由两类构成——

- 30 条 `incomplete` 层：证据行非空但内容为 `（缺字段）`，严格符合字面定义 → **本轮重分类**；
- 30 条 `no_evidence` 层：**证据行整体为空**，不满足字面定义 → **本轮不重分类**。

执行者**不擅自扩大冻结条款**：后 30 条保持 v2 原判（`OBSERVATION_ERROR / PARSE_FAIL`）、`supports=None`、留在原始分母内，单列入 `out_of_scope_rows`，字段 `out_of_scope_no_evidence_line_count` 与 `out_of_scope_note` 明写「§19 字面定义未覆盖，归下一轮裁定」。

因此 ADV-4 在本轮是**部分闭合**：结构性不可判样本中 30/60 有了显式处置，剩余 30 条的口径缺口如实登记。宣称全部闭合即为不实。此处也解释了 `judgable_denominator` 的口径边界，避免「从分母剔除」的误读。

## 7. 与轮十一证书的关系

轮十一 `tools/eval/independence_cert.json` 的 `impl_blob_sha` 指向 v2 时期的 `independent_judge.py` blob。本卡 Owned files 明确授权修订该文件，v3 是**新 blob**，该证书不复用、不回填、不改写；轮十一已 CLOSED 归档 legacy。`_judge_case_v2` 保持逐字可用，正是为了让 v2 时期的封存产物仍可复算比对。

## 8. 纪律

- 红区零触碰；本文件与 `rubric_v3.py` / `independent_judge.py` 均在本卡 Owned files 内。
- CI py3.9：无 PEP 604 联合类型、不给 Path 文本写入方法传 `newline` 关键字，JSON 写入用 `open(..., newline="")`。
- 本轮所有复算读数 `caliber = instrument_calibration_only`，**不进门结论**；不重跑 R_main 计数、不重算任何门值。
