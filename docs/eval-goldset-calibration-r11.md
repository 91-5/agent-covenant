# 轮十一 · 50 条三角锚定子集与独立性降级说明

> 卡 `XJ-20261111-002` · D3 附带 · 2026-11-11 · 执行者 WB
> 依据：`docs/eval-prereg.md` §18 D18-D（三角锚定与人力条款）、卡面「三角锚定与人力条款」
> 定位：**本文件不是双人独立标注报告**。本环境无法满足双人独立标注，按轮十 ADV-3 同形处理。

## 1. 结论（每条带 artifact 指针）

- **结论 C1**：50 条子集由 `R11_SEED = 20261111` 从 400 条盲样本确定性抽取；两视图（主轨判级 / 独立判级）可比 44 条、一致 26 条，一致率 `0.590909`。`[artifact: out/r11-triangle-anchor.json sha256=215e706ab81a5b0f6d1ba488f70cd7d0a76ecfff7f4a6300681abbe15bdae3e2]`

- **结论 C2**：**双人独立标注不可满足**。`two_human_independent_annotation = false`、`R_main_human = null`、`R_indep_human = null`、`triangle_verdict = not_evaluable_no_independent_human_annotation`。执行者为单一 agent WB，两个「视图」是同一主体的两套确定性程序，不是两个独立人类标注者。`[artifact: goldset/calibration_r11.jsonl sha256=ebf3821ecd005a6f8f0ef5baa0696762ae5c44c2e5e21c42ea4caf36c02e517e]`

- **结论 C3**：按 §18 D18-D 与轮十 ADV-3 同形处理，结论效力降级为「**单 agent 双视图一致性 + 方向诊断**」；三条三角判据（两实现可互换 / 主轨是薄弱环 / 独立实现薄弱需重建）本轮**均不裁定**，因为它们的输入 `R_main_human`、`R_indep_human` 不存在。`[artifact: out/r11-triangle-anchor.json sha256=215e706ab81a5b0f6d1ba488f70cd7d0a76ecfff7f4a6300681abbe15bdae3e2]`

- **结论 C4**：`goldset/calibration_r11.jsonl` 为 50 行，每行携带 `annotation_mode = single_agent_double_view` 与 `two_human_independent = false`，逐行自证不被误读为双人独立标注。`[artifact: goldset/calibration_r11.jsonl sha256=ebf3821ecd005a6f8f0ef5baa0696762ae5c44c2e5e21c42ea4caf36c02e517e]`

## 2. 为什么不做「人工双标」的替代动作

卡面明确排除「把双人独立标注全量提前」（成本/收益倒挂，人工只做 50 条校准子集）。本环境连这 50 条的双人独立也无法提供：执行者只有 WB 一个 agent，没有第二个独立人类，也没有可调用的不同模型族判级器（见 `tools/eval/independence_cert.json`）。用同一主体生成两份标注、再宣称「双人独立」属于伪造独立性，比缺独立性严重——本卡拒绝该做法。`[artifact: tools/eval/independence_cert.json sha256=297a1409599a96ca91fc5c2f1b2e60b236e4f998fa7f1c171edb218337b8b0c2]`

## 3. 与轮十 ADV-3 的同形对照

| 项 | 轮十 ADV-3 | 轮十一本卡 |
|---|---|---|
| 缺口 | 单 agent 双角色标注 | 单 agent 双视图标注 |
| 处置 | 明确披露 + 效力降级为方向诊断 | 同形：明确披露 + 效力降级为方向诊断 |
| 禁止 | 不得记为双人独立 | 同形：不得记为双人独立 |
| 0 分歧解读 | 不证明独立性 | 同形：不证明独立性 |

`[artifact: tools/eval/independence_cert.json sha256=297a1409599a96ca91fc5c2f1b2e60b236e4f998fa7f1c171edb218337b8b0c2]`

## 4. 对门结论的影响

由于三角锚定与独立证书双双不满足，`R_main = 0.62069` 与由此推导的 M_C 数值**均不作为有效门依据**发布；按 §18 三档表，`R_main < 0.80` 亦独立命中 `not_evaluable`。两条路径同向不矛盾，但各自独立成立，不靠叙述合并。`[artifact: out/r11-main-reliability.json sha256=b54d2d43038ff6ce9f39e96e89235f54cf9f8085559ea44b6eb44a44a73c2b68]`

## 5. 边界

不写 verdict、不 push、不 merge。是否需要补独立人类标注 / 不同模型族判级，由评审侧下新卡。
