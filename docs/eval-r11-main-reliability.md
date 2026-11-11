# 轮十一 · R_main 盲态重测与主轨判级有效性

> 卡 `XJ-20261111-002` · D3 · 2026-11-11 · 执行者 WB
> 依据：`docs/eval-prereg.md` §18 D18-B（seed / LB95 / 三档表）、D18-C（R_main 定义与盲态序）、D18-D（独立性诚实条款）、D18-F（真数据生成规则）
> **本轮结论效力**：`caliber = single_agent_dual_view_direction_only`。独立性证书 `independence_satisfied = false`，故本报告的 R_main 是方向诊断读数，**不是有效语义信度估计**。

## 1. 结论（每条带 artifact 指针）

- **结论 R1**：`R_main = 0.62069`（108/174 可比对样本逐条一致），`LB95 = 0.546722`（Wilson，z = 1.959963984540054），`n = 400`，`seed = 20261111`。按 §18 三档分支表点估计 `0.62069 < 0.80` → `branch = not_evaluable`，`gate_result = not_evaluable`（**不是** `not met`），本轮产出转为「主轨判级有效性报告」。`[artifact: out/r11-main-reliability.json sha256=b54d2d43038ff6ce9f39e96e89235f54cf9f8085559ea44b6eb44a44a73c2b68]`

- **结论 R2**：分层报告完整、未合并掩盖——`R10_ANCHOR n=240`，可比 68、弃权 172（71.67%）、`R_main = 0.558824`、`LB95 = 0.440819`；`HOLDOUT n=160`，可比 106、弃权 54（33.75%）、`R_main = 0.660377`、`LB95 = 0.566027`。两层差 10.16pp，**不得合并成一个数掩盖**。另报「全 400 分母」口径 `r_main_all_denominator = 0.27`（108/400），供对照，不作为 R_main。`[artifact: out/r11-main-reliability.json sha256=b54d2d43038ff6ce9f39e96e89235f54cf9f8085559ea44b6eb44a44a73c2b68]`

- **结论 R3**：**独立实现在 400 条中弃权 226 条（56.5%）**——`OBSERVATION_ERROR 156`、`INSUFFICIENT 70`；主轨层级分布 `E4 226 / E2 114 / E1 30 / E0 30`，独立层级分布 `SUPPORT 126 / NOT_SUPPORT 48 / OBSERVATION_ERROR 156 / INSUFFICIENT 70`。R_main 的分母实为 174 条可比样本，不是 400；**这是本轮最大的效力限制**，因为弃权不是随机缺失（集中在无证据行、ref 缺失、unanchored 层），会系统性抬高或压低一致率，方向未知。`[artifact: out/r11-reliability-rows.json sha256=2b38e9abf5fde4ba9b624311c107ced1498c6d286b601ba8aad8bfe845cd3fe7]`

- **结论 R4**：盲态序机械成立——独立判级先跑完 400 条，产物 `out/r11-independent-blind.json` 的 SHA-256 `3d4d6bb3f555ed14b9dcc817d2a5eb8c817b79861ecae4b639a26f22254a4180` 于 `2026-11-11T15:00:56.391372+00:00` 封存；封存日志记 `main_track_invoked_before_seal = false`；之后才调用主轨判级并比对。`seal_then_unblind_order = true`。`[artifact: out/r11-seal-log.json sha256=49517437036cc151fa6c1c39dcd3cc4e140aa49f2d96f762ec28244da3cae0a2]`

- **结论 R5**：R_main **只计算一次**。`r11_reliability.py` 设 `FIRST_RUN_ONLY` 重跑保护，结果文件已存在时拒绝第二次计数并返回退出码 3；本次为唯一一次计数运行，违反「只跑一次」即作废的三重约束未触发。`[artifact: out/r11-main-reliability.json sha256=b54d2d43038ff6ce9f39e96e89235f54cf9f8085559ea44b6eb44a44a73c2b68]`

- **结论 R6**：`R_stability` 未入公式（按 §18 条款 1，确定性 sanity check 本应为 1.0，不是信度证据）；本轮未做 test-retest，R_main 是「主轨判级 vs 独立判级」的逐条一致率。`[artifact: tools/eval/independent_judge.py sha256=a792aef6bb3afc6188512941aeadfcae6da6543804175e00e6e752e0d6c00329]`

## 2. 样本设计（冻结规则的可复算落地）

| 层 | 条数 | 来源 |
|---|---|---|
| `R10_ANCHOR` | 240 | 轮十 Gate 0 冻结输入集 30 产品 × 8 层，拆为单 claim case，fixture 原样保留 |
| `HOLDOUT` | 160 | `tools/eval/tasks/T*.json` 冻结任务定义 + `R11_SEED = 20261111` 确定性派生，9 层 × 6 类 ERROR 设计标签 |

样本集 SHA-256 `6d61994c7104747a797658b72733898b5c833b07715155e3aba0c987b4b9fcc9`，Gate 0 源 SHA-256 `474bc0514de5b1dd3803a3b962fedd8381ab734bb459c7304e58d236d875809d`。生成规则在 §18 D18-F 明文冻结（轮十 ADV-1 闭合），样本生成一次、封哈希、不回头改。`[artifact: out/r11-blind-samples.json sha256=6d61994c7104747a797658b72733898b5c833b07715155e3aba0c987b4b9fcc9]`

## 3. 三档分支查表（报告只查表，不解释）

| 条件 | 本轮读数 | 查表结果 |
|---|---|---|
| `R_main ≥ 0.85` → `normal` | 0.62069 | 否 |
| `0.80 ≤ R_main < 0.85` → `weak_reference` | 0.62069 | 否 |
| **`R_main < 0.80` → `not_evaluable`** | **0.62069** | **命中** |

命中档处置：**不出门结论**，`gate_result = not_evaluable`，本轮产出转为主轨判级有效性报告。按 §18 禁令 2，低 R_main 是参照失效、**不允许自动放宽门**；按元条款，此决策规则在 D0 冻结、本报告只查表。`[artifact: out/r11-main-reliability.json sha256=b54d2d43038ff6ce9f39e96e89235f54cf9f8085559ea44b6eb44a44a73c2b68]`

## 4. 三角锚定：诚实降级

n=50 子集由 `R11_SEED` 从 400 条抽取，两视图一致率 `0.590909`（26/44 可比）。**本执行环境为单一 agent WB，无法提供双人独立标注**，`R_main_human` / `R_indep_human` 均为 `null`，`triangle_verdict = not_evaluable_no_independent_human_annotation`。按轮十 ADV-3 同形处理：明确披露 + 结论效力降级为「单 agent 双视图一致性 + 方向诊断」，**不得记为双人独立，0 分歧也不证明独立性**。三条三角判据（可互换 / 主轨薄弱 / 独立实现薄弱重建）本轮**均不裁定**。`[artifact: out/r11-triangle-anchor.json sha256=215e706ab81a5b0f6d1ba488f70cd7d0a76ecfff7f4a6300681abbe15bdae3e2]`

## 5. 独立性与诚实边界

证书 `independence_satisfied = false`（`judge_model_family` 与 `rubric_blind` 两字段不满足，未伪造）。因此本报告的所有数值**只作为方向诊断发布**，不得据此宣布门结论有效；M_C 重推仍按冻结协议只跑一次并如实发布，但同样不产生有效门。`[artifact: tools/eval/independence_cert.json sha256=297a1409599a96ca91fc5c2f1b2e60b236e4f998fa7f1c171edb218337b8b0c2]`

## 6. 已披露的处置（不修饰）

首次样本生成返回 `BAD_COUNTS 210 160 370`：Gate 0 第 8 层 `no_evidence` 无证据行，抽取正则要求证据行而静默漏抓 30 条。该次运行**在写出任何样本文件之前就失败**，R_main 计数运行因读不到样本文件而报 `FileNotFoundError`，**两者均未产生轮十一数据、未触碰「只跑一次」约束**。修正为「证据行可选」的块正则后重新生成，240/160 分层核对通过，再执行唯一一次盲态重测。全过程留痕于 custody 脚本与控制台日志。`[artifact: out/r11-blind-samples.json sha256=6d61994c7104747a797658b72733898b5c833b07715155e3aba0c987b4b9fcc9]`

## 7. 边界

不写 verdict、不 push、不 merge、不重判轮六–轮十历史轮次。本卡的 M_C 数值与门结论由 D4/D6 按冻结查表给出；是否需要独立人类 / 不同模型族判级，交浮香裁定。
