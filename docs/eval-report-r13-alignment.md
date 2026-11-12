# 轮十三 · 判级口径对齐与锚点规则修正（校准复算报告，不进门结论）

> 卡号 `XJ-20261112-002` · 分支 `feature/xj-20261112-002-round13-alignment` · 基线 `831a46a` · 冻结 commit `ae237e3` · 执行者 `WB = WorkBuddy`
> 本报告由执行者撰写，**无评审权、无合并权**；不写 verdict、不 push、不 merge、不碰 master。产出交 Orchestrator 预审 + 浮香（AgnesCode）PASS gate 裁定。

## 0. 口径声明（写在一切读数之前）

本轮是**仪器口径对齐轮**，不是门轮。§20 在轮十三任何数据产物之前冻结，D1–D6 只做实现、查表与机械验证。本轮 `r_main` 标 `caliber = instrument_alignment_calibration_only`，是校准复算读数；`gate_result = not_evaluable`、`gate_conclusion_issued = false`。不重测门值、不重算门结论、不产出第二个门计数读数、不产出第二个 M_C；报告不出现任何门值数值。轮十一封存 `R_main = 0.62069` 只作并列参照，冻结不动。

## 1. 冻结序与 HARKing 防线

`freeze → offline replay → data`。D20-B 七条条款、D20-C 三条禁令、D20-C′ 卡面六条禁令逐字并入、D20-D 冻结常量表、D20-E 机器可读 25 格映射矩阵，全部写在冻结 commit 内。V1 文本口径前缀 SHA 前后一致，`git diff 831a46a --numstat -- docs/eval-prereg.md` 删除行数为 0，§0–§19 与基线 blob 在 LF 归一后逐字节相等。

## 2. 修正前后并列（禁令 3）

| 口径 | r_main | comparable | agree | disagree | abstain | 分歧机制 |
|---|---|---|---|---|---|---|
| 轮十一封存（门计数，冻结） | 0.62069 | 174 | 108 | 66 | 226 | A48 + B18 |
| 修正前重算（v3 + 轮十一调用约定） | 0.62069 | 174 | 108 | 66 | 226 | anchor 48 / cwd 18 |
| 修正后校准（非门计数） | 1.0 | 118 | 118 | 0 | 282 | 四键全 0 |

可比集由 174 缩到 118（−56），弃权由 226 增到 282（+56）；56 条布尔→弃权转移 56/56 全部归因于条款 3 锚点规则对齐，未归因残余 0。一致率变化是**口径修正**，不是能力提升：可比集缩小、原始分母 400 从不缩减。

## 3. 三条判级政策差异与保护性弃权

- 无锚政策（70 条 INSUFFICIENT）：独立轨维持 `explicit_anchor_required=True`，不放宽。
- 缺席的判级（48 条 ref_missing）：建立 `VERIFIABLE_ABSENCE` 独立路径 + `upgrade_candidate=true`，`supports` 仍为 `None`，本轮不激活为布尔判定。
- 静默失败（48 条 repro_fail）：保持 `SILENT_FALLBACK` 保护性弃权，禁止映射。

`protected_total = 48 + 48 = 96` 修正前后不变（V7）。冻结映射矩阵把两类保护性弃权锁在 `protected_abstention`，任何 `equivalent` / `conflict` 格子都不含它们。

## 4. D5 双标注实测与降级

`annotator_count` 由逐行登记的标注者身份集合机械统计，实测 1；`two_human_independent_annotation=false`。50 条子集与轮十二同 seed 同抽样：本轮 comparable 13 / agree 13 / rate 1.0，轮十二 comparable 22 / rate 0.590909。这是单 agent 双视图一致性 + 方向诊断，不是双标注满足、不是独立性证据、不是可靠性估计。第二机械视图为查表结果，显式不计入标注者人数。

## 5. 验收与未闭合项

V1–V11 全量亲跑，真实退出码逐条留档；V2 字面路径口径差、V11 无 `COVENANT_BASH_HINT` 的单测失败与 lint `--strict` 结构性 WARN 照实登记，不改红区刷绿。未闭合项：① `FILE_NOT_FOUND` 是否升级为可判的「可验证的缺席」需单独立项交浮香；② 无锚政策以谁为基准、主轨无锚 E4 是否属设计缺陷，不在本卡裁定；③ 双人独立人类标注本环境仍不可满足。

## 6. 结论（每条带双格式 artifact 指针）

- **结论 R1**：§20 在轮十三任何产物之前冻结（commit `ae237e3`），纯追加：`prereg_before_bytes 168010` → `prereg_after_bytes 191760`，§20 小节 23750 字节；V1 文本口径前缀 SHA 前后同为 `8941bc966a02f94bee78ee3dfad34f09ddc808033d2284c8bbb4875858675561`。决策规则、阈值、类别白名单、映射矩阵、机制枚举全部在冻结 commit 内写死，D1–D6 只做实现与查表，此为对抗问题 7（HARKing）的正面答案。
  [artifact: docs/eval-prereg.md sha256=53d43d1b76e6bb9bee2eb470be0d391f261d8c0bd81fad9a1aefa4b3ecb0f3a8]
  (docs/eval-prereg.md) 53d43d1b76e6bb9bee2eb470be0d391f261d8c0bd81fad9a1aefa4b3ecb0f3a8

- **结论 R2**：D20-E 冻结 5×5 = 25 格标签映射矩阵，三类别 `equivalent` / `conflict` / `protected_abstention` 穷举覆盖、无 `unmapped`；`label_mapping.py --verify` 从 §20 机械读回矩阵并逐格比对代码常量。
  [artifact: out/r13-label-mapping-verify.json sha256=10f0902506d42b10d2131968d7f63b3a14496e1bdf932b716dba01ba004c317b]
  (out/r13-label-mapping-verify.json) 10f0902506d42b10d2131968d7f63b3a14496e1bdf932b716dba01ba004c317b
  [artifact: tools/eval/label_mapping.py sha256=038b0403532625ed316871f8b86aadbef2f902f373a92216a3a0b3d5f3b384e4]

- **结论 R3**：V2 篡改负对照：把冻结矩阵 `E4|SUPPORT` 一格改成 `protected_abstention` 后重验，`verify_pass False` 且精确定位该格 mismatch，证明校验器读的是冻结文本而不是绕开文本的代码常量。卡面 V2 字面 PowerShell 反斜杠路径在 Git Bash 未加引号时退出码 2（`\e` 被 shell 吞掉），加引号与正斜杠两种等价路径退出码 0，口径差照实登记、不刷绿。
  [artifact: out/r13-label-mapping-verify.json sha256=10f0902506d42b10d2131968d7f63b3a14496e1bdf932b716dba01ba004c317b]
  (out/r13-label-mapping-verify.json) 10f0902506d42b10d2131968d7f63b3a14496e1bdf932b716dba01ba004c317b
  [artifact: ../round13-custody/prereg-tamper-test.md sha256=efe2501b2509853758df4d25c4176218cae2e216575c142ab67955eb2fd56aa9]

- **结论 R4**：D2 锚点规则逐字等价：`independent_judge._ANCHOR_RE.pattern` 与主轨 `extract.INTEGER_ANCHOR_RE.pattern` 逐字相同（`(?<![\w.\-])\d+(?![\w.\-])`）；`_anchors()` 复现主轨三步算法（先收全部反引号 token → 反引号置空格后抽整数 → `dict.fromkeys` 去重保序）。legacy 交替正则仅保留给 v2/v3 复算路径，不进入 v4 决策。
  [artifact: out/r13-anchor-check.json sha256=95aa7235a62782752fdb9a96c868fe6eef539f5d3c5553d7c93a21d1effea156]
  (out/r13-anchor-check.json) 95aa7235a62782752fdb9a96c868fe6eef539f5d3c5553d7c93a21d1effea156
  [artifact: tools/eval/independent_judge.py sha256=25b55674573f2373844e486458741c4350cf2338099d473f8c6c475080b76896]

- **结论 R5**：V3 在 400 条冻结样本上逐条集合比对：`legacy_anchor_set_mismatches_before 56` → `anchor_set_mismatches 0`，`claim_text_calibre_mismatches 0`，`PASS True`。56 条差集全部源于 legacy 把 `Apache-2.0` 的 `2.0` 抽成锚点。
  [artifact: out/r13-anchor-check.json sha256=95aa7235a62782752fdb9a96c868fe6eef539f5d3c5553d7c93a21d1effea156]
  (out/r13-anchor-check.json) 95aa7235a62782752fdb9a96c868fe6eef539f5d3c5553d7c93a21d1effea156
  [artifact: out/r11-blind-samples.json sha256=6d61994c7104747a797658b72733898b5c833b07715155e3aba0c987b4b9fcc9]

- **结论 R6**：D3 rubric v4 四个命名弃权层各自只命中一个显式类别：`no_evidence 30 → NO_EVIDENCE_LINE`、`incomplete 30 → STRUCTURALLY_UNJUDGEABLE`、`ref_missing 48 → VERIFIABLE_ABSENCE`、`repro_fail 48 → SILENT_FALLBACK_PROTECTED`；`new_unobservable_class_count 0`。
  [artifact: out/r13-rubric-v4-decomposition.json sha256=4e0c40eaf751f80c3c87c962370d4bd409b66958f9a48f172cbec46270c77232]
  (out/r13-rubric-v4-decomposition.json) 4e0c40eaf751f80c3c87c962370d4bd409b66958f9a48f172cbec46270c77232
  [artifact: tools/eval/rubric_v4.py sha256=930ca332c3eb09c4b5f9a02eb5d188b11eb3aedc460f7979fea9325a86ccb4a2]

- **结论 R7**：V4 验收：`no_evidence_classes ['NO_EVIDENCE_LINE']`、`incomplete_classes ['STRUCTURALLY_UNJUDGEABLE']`、`new_unobservable_class_count 0`、`protected_total 96`、`PASS True`。卡面 6 行初稿第 6 行把 `incomplete` 写成 `PARSE_FAIL`，与轮十二 v3 起的当前实现不符，已在 D20-A/A-3 冻结时登记偏差，不按初稿把两层混为同一类。
  [artifact: out/r13-rubric-check.json sha256=c2cb9dccabab2868522f883b9898b6b34602f2f30d02b5b5f0daa0aa4252d1ce]
  (out/r13-rubric-check.json) c2cb9dccabab2868522f883b9898b6b34602f2f30d02b5b5f0daa0aa4252d1ce

- **结论 R8**：rubric v4 逐条分解证明：`boolean_to_abstain_total 56`、`boolean_to_abstain_attributed_anchor_rule 56`、`boolean_to_abstain_unattributed_residual 0` —— 56 条布尔转弃权全部由条款 3 锚点规则对齐造成，不是 rubric 新造的不可判类别，也不是隐藏桶。原始分母 400 从不缩减。
  [artifact: out/r13-rubric-v4-decomposition.json sha256=4e0c40eaf751f80c3c87c962370d4bd409b66958f9a48f172cbec46270c77232]
  (out/r13-rubric-v4-decomposition.json) 4e0c40eaf751f80c3c87c962370d4bd409b66958f9a48f172cbec46270c77232

- **结论 R9**：指令内部张力按禁令优先裁决：接卡指令 D3 的「ref_missing→缺席可判路径」与卡面禁令 2 / V7 冲突，本轮只建立 `VERIFIABLE_ABSENCE` 显式独立路径与 `upgrade_candidate=true` 留痕（48 条），`supports` 保持 `None`、`error_class` 仍 `FILE_NOT_FOUND`、`ref_missing_activated_as_boolean false`；是否升级为可判 NOT_SUPPORT 单独立项交浮香裁定。
  [artifact: out/r13-rubric-v4-decomposition.json sha256=4e0c40eaf751f80c3c87c962370d4bd409b66958f9a48f172cbec46270c77232]
  (out/r13-rubric-v4-decomposition.json) 4e0c40eaf751f80c3c87c962370d4bd409b66958f9a48f172cbec46270c77232

- **结论 R10**：V7：`SILENT_FALLBACK 48 + FILE_NOT_FOUND 48 = 96`，修正前后不得下降且实测未下降；映射表把两类保护性弃权锁在 `protected_abstention`，未出现在任何 `equivalent` / `conflict` 格子里（禁令 2 守住，不重建轮九伪一致）。
  [artifact: out/r13-alignment.json sha256=a3e37809d8b2cb7743c1ca8a533ae5f4f167cab37506f979c828aee17c5df181]
  (out/r13-alignment.json) a3e37809d8b2cb7743c1ca8a533ae5f4f167cab37506f979c828aee17c5df181
  [artifact: tools/eval/label_mapping.py sha256=038b0403532625ed316871f8b86aadbef2f902f373a92216a3a0b3d5f3b384e4]

- **结论 R11**：rubric v4 保留 `explicit_anchor_required=True`，`SILENT_FALLBACK` 保持 `OBSERVATION_ERROR` 弃权，48 条 `repro_fail` 全部 `supports=None`；分解产物 `protected_rows_all_abstain true`、`capability_gain_claim false`。
  [artifact: out/r13-rubric-v4-decomposition.json sha256=4e0c40eaf751f80c3c87c962370d4bd409b66958f9a48f172cbec46270c77232]
  (out/r13-rubric-v4-decomposition.json) 4e0c40eaf751f80c3c87c962370d4bd409b66958f9a48f172cbec46270c77232

- **结论 R12**：D4 无锚政策显式裁决：70 条 INSUFFICIENT（`ref_ok 48 + goldset_text 22`）维持弃权，映射表标 `protected_abstention / subtype=no_anchor_policy`，不为抬高一致率迁就主轨无锚 E4；主轨无锚 E4 是否属设计缺陷不在本卡裁定范围，交浮香。
  [artifact: out/r13-alignment.json sha256=a3e37809d8b2cb7743c1ca8a533ae5f4f167cab37506f979c828aee17c5df181]
  (out/r13-alignment.json) a3e37809d8b2cb7743c1ca8a533ae5f4f167cab37506f979c828aee17c5df181
  [artifact: out/r13-label-mapping-verify.json sha256=10f0902506d42b10d2131968d7f63b3a14496e1bdf932b716dba01ba004c317b]

- **结论 R13**：D4 cwd 观测面对齐：`cwd_mismatches_before 18 → cwd_mismatches 0`，两轨统一到 workspace，主轨通过其 v1.5 C10 已支持的 `workspace=` 参数调用，`main_track_source_modified false`（禁令 1：不改主轨，改主轨等于改答案）。
  [artifact: out/r13-cwd-check.json sha256=87e015736c9b6e0a19713a61e3b1469e5c8907aaf748e4ff45f0af556d496186]
  (out/r13-cwd-check.json) 87e015736c9b6e0a19713a61e3b1469e5c8907aaf748e4ff45f0af556d496186
  [artifact: tools/eval/r13_alignment.py sha256=b3c98072ba284561b9b109baf1ed3f270a25519b52039f9d9f82355e077591fa]

- **结论 R14**：V6 修正前读数由 v3（legacy 锚点）+ 轮十一调用约定**重算复现**，不是照抄：`r_main 0.6206896551724138`、`comparable 174`、`agree 108`、`disagree 66`、`abstain 226`、`disagree_by_mechanism {anchor_rule_diff: 48, cwd_observation_surface_diff: 18}`、`matches_sealed True`，与轮十一封存 `R_main = 0.62069` 逐位吻合。
  [artifact: out/r13-alignment.json sha256=a3e37809d8b2cb7743c1ca8a533ae5f4f167cab37506f979c828aee17c5df181]
  (out/r13-alignment.json) a3e37809d8b2cb7743c1ca8a533ae5f4f167cab37506f979c828aee17c5df181
  [artifact: out/r11-reliability-rows.json sha256=2b38e9abf5fde4ba9b624311c107ced1498c6d286b601ba8aad8bfe845cd3fe7]

- **结论 R15**：V6 修正后校准读数：`r_main 1.0`、`comparable 118`、`agree 118`、`disagree 0`、`abstain 282`。该值标 `caliber = instrument_alignment_calibration_only`，是仪器口径对齐后的校准复算，**不是**第二个门计数读数，不用于任何门结论。
  [artifact: out/r13-alignment.json sha256=a3e37809d8b2cb7743c1ca8a533ae5f4f167cab37506f979c828aee17c5df181]
  (out/r13-alignment.json) a3e37809d8b2cb7743c1ca8a533ae5f4f167cab37506f979c828aee17c5df181

- **结论 R16**：`disagree_by_mechanism` 冻结四键全部显式保留：`{anchor_rule_diff: 0, cwd_observation_surface_diff: 0, policy_conflict: 0, other: 0}`；`disagree_by_mechanism_total 0 = disagree 0`、`no_residual True`，`other` 为空，没有靠空 dict 或隐藏桶制造「无残余」。
  [artifact: out/r13-alignment.json sha256=a3e37809d8b2cb7743c1ca8a533ae5f4f167cab37506f979c828aee17c5df181]
  (out/r13-alignment.json) a3e37809d8b2cb7743c1ca8a533ae5f4f167cab37506f979c828aee17c5df181

- **结论 R17**：禁令 3 正面答案：修正前后构成并列——可比集 `174 → 118`（`comparable_delta -56`）、弃权 `226 → 282`（`abstain_delta +56`）、分歧 `66 → 0`（A48 + B18 全消解）。一致率上升**全部**由锚点规则与 cwd 观测面两处口径修正贡献，可比集是**缩小**而不是变大；本报告明确不叙述为影子轨能力提升或仪器能力提升。
  [artifact: out/r13-alignment.json sha256=a3e37809d8b2cb7743c1ca8a533ae5f4f167cab37506f979c828aee17c5df181]
  (out/r13-alignment.json) a3e37809d8b2cb7743c1ca8a533ae5f4f167cab37506f979c828aee17c5df181

- **结论 R18**：禁令 4 正面答案：本轮 `gate_result = not_evaluable`、`gate_conclusion_issued false`、`gate_value_recomputed false`、`r_main_gate_counting_recomputed false`；不重测门值、不重算门结论、不产出第二个 M_C，报告不出现任何门值数值。轮十一封存门计数 `R_main = 0.62069` 只作并列参照，冻结不动、不被覆盖。
  [artifact: out/r13-alignment.json sha256=a3e37809d8b2cb7743c1ca8a533ae5f4f167cab37506f979c828aee17c5df181]
  (out/r13-alignment.json) a3e37809d8b2cb7743c1ca8a533ae5f4f167cab37506f979c828aee17c5df181

- **结论 R19**：D5 双标注**实测降级**：`annotator_count` 由逐行标注者身份集合机械统计得出，实测 `1`；`two_human_independent_annotation false`、`independence_satisfied false`、`triangle_verdict not_evaluable_no_independent_human_annotation`。本环境只有一个执行 agent，照轮十 ADV-3 / 轮十一 ADV-5 / 轮十二 ADV-5 同形降级，不得记为双人独立标注。
  [artifact: out/r13-annotation-summary.json sha256=ff1264792a97b60cc88a4c8082ceae8b1f353b875c429aca4aea80c5350307b5]
  (out/r13-annotation-summary.json) ff1264792a97b60cc88a4c8082ceae8b1f353b875c429aca4aea80c5350307b5
  [artifact: goldset/annotation_r13.jsonl sha256=60e4fcfe76f644f808b6b8c7d5a066105a2951812b577081d149dc95ccacba0e]

- **结论 R20**：D5 第二机械视图只是 `label_mapping.map_pair` 查表结果，标 `mechanical_view=true` / `is_human_annotation=false` / `counts_toward_annotator_count=false`，不计入标注者人数、不冒充独立人类标注。
  [artifact: out/r13-annotation-summary.json sha256=ff1264792a97b60cc88a4c8082ceae8b1f353b875c429aca4aea80c5350307b5]
  (out/r13-annotation-summary.json) ff1264792a97b60cc88a4c8082ceae8b1f353b875c429aca4aea80c5350307b5
  [artifact: goldset/annotation_r13.jsonl sha256=60e4fcfe76f644f808b6b8c7d5a066105a2951812b577081d149dc95ccacba0e]

- **结论 R21**：D5 50 条子集与轮十二同 seed 同抽样（`round12_same_seed_same_subset true`）：本轮 `comparable 13 / agree 13 / agreement_rate 1.0`，轮十二 `comparable 22 / rate 0.590909`。这是两个不同 rubric 下**单 agent 双视图**读数的方向诊断，可比集缩小来自锚点口径修正，0 分歧不证明独立性，也不是可靠性估计或能力提升证据。
  [artifact: out/r13-annotation-summary.json sha256=ff1264792a97b60cc88a4c8082ceae8b1f353b875c429aca4aea80c5350307b5]
  (out/r13-annotation-summary.json) ff1264792a97b60cc88a4c8082ceae8b1f353b875c429aca4aea80c5350307b5

- **结论 R22**：V8 红区零触碰用**完整路径**核验（7 个仪器在 `tools/eval/`、`gate.py`/`lint_cards.py` 在 `tools/`），`git diff 831a46a -- <11 个完整路径>` 输出为空、退出码 0；写裸文件名会让 diff 假绿，本轮不采用。所有变更均为 Owned files。
  [artifact: ../round13-custody/r13-acceptance.json sha256=883fe714ab46d40fc812a6836b44bd18ce7f1e4b7d710baee1523111d9d3f066]
  (../round13-custody/r13-acceptance.json) 883fe714ab46d40fc812a6836b44bd18ce7f1e4b7d710baee1523111d9d3f066
  [artifact: ../round13-custody/r13-acceptance.log sha256=7c8dc90dac7bf061e422f5e9ac7807051c3c2927c27c7ccdd49718cc53a2d9e1]
  [artifact: docs/eval-prereg.md sha256=53d43d1b76e6bb9bee2eb470be0d391f261d8c0bd81fad9a1aefa4b3ecb0f3a8]

- **结论 R23**：V9 seal 验签：`VERIFY: OK (9 files match the seal)`，`run-dir-r13/` 是执行产物封装包（`not_true_data true`，仅 `out/r13-*` 与 `goldset/annotation_r13.jsonl` 的副本），custody 正本在 `round13-custody/sealed/run-dir-r13`；`seal_cmd_exit 0` / `verify_exit 0`。
  [artifact: ../round13-custody/sealed/run-dir-r13/seal.json sha256=98a81661e1f48f52236cd43c885740eb3cd7aabb372a5576af12c480c35de7a4]
  (../round13-custody/sealed/run-dir-r13/seal.json) 98a81661e1f48f52236cd43c885740eb3cd7aabb372a5576af12c480c35de7a4
  [artifact: ../round13-custody/r13-seal-summary.json sha256=18d9e5c66e884ad6fc1b4eed73120ff355d30fd82e517b84b6d36c6355dbd6cb]

- **结论 R24**：V1–V11 由执行者亲跑并逐条留真实退出码，不采纳作者 precheck；字面失败项（V2 未加引号反斜杠路径、V11 无 `COVENANT_BASH_HINT` 单测、lint `--strict` 结构性 WARN）照实登记不刷绿，V10 指针完整性单独留档。验收台账与本报告均未改红区文件以求绿。
  [artifact: ../round13-custody/r13-acceptance.json sha256=883fe714ab46d40fc812a6836b44bd18ce7f1e4b7d710baee1523111d9d3f066]
  (../round13-custody/r13-acceptance.json) 883fe714ab46d40fc812a6836b44bd18ce7f1e4b7d710baee1523111d9d3f066

## 附：产物哈希（生成时实时计算）

| 路径 | sha256 |
|---|---|
| `../round13-custody/prereg-tamper-test.md` | `efe2501b2509853758df4d25c4176218cae2e216575c142ab67955eb2fd56aa9` |
| `../round13-custody/r13-acceptance.json` | `883fe714ab46d40fc812a6836b44bd18ce7f1e4b7d710baee1523111d9d3f066` |
| `../round13-custody/r13-acceptance.log` | `7c8dc90dac7bf061e422f5e9ac7807051c3c2927c27c7ccdd49718cc53a2d9e1` |
| `../round13-custody/r13-seal-summary.json` | `18d9e5c66e884ad6fc1b4eed73120ff355d30fd82e517b84b6d36c6355dbd6cb` |
| `../round13-custody/sealed/run-dir-r13/seal.json` | `98a81661e1f48f52236cd43c885740eb3cd7aabb372a5576af12c480c35de7a4` |
| `docs/eval-prereg.md` | `53d43d1b76e6bb9bee2eb470be0d391f261d8c0bd81fad9a1aefa4b3ecb0f3a8` |
| `goldset/annotation_r13.jsonl` | `60e4fcfe76f644f808b6b8c7d5a066105a2951812b577081d149dc95ccacba0e` |
| `out/r11-blind-samples.json` | `6d61994c7104747a797658b72733898b5c833b07715155e3aba0c987b4b9fcc9` |
| `out/r11-reliability-rows.json` | `2b38e9abf5fde4ba9b624311c107ced1498c6d286b601ba8aad8bfe845cd3fe7` |
| `out/r13-alignment.json` | `a3e37809d8b2cb7743c1ca8a533ae5f4f167cab37506f979c828aee17c5df181` |
| `out/r13-anchor-check.json` | `95aa7235a62782752fdb9a96c868fe6eef539f5d3c5553d7c93a21d1effea156` |
| `out/r13-annotation-summary.json` | `ff1264792a97b60cc88a4c8082ceae8b1f353b875c429aca4aea80c5350307b5` |
| `out/r13-cwd-check.json` | `87e015736c9b6e0a19713a61e3b1469e5c8907aaf748e4ff45f0af556d496186` |
| `out/r13-label-mapping-verify.json` | `10f0902506d42b10d2131968d7f63b3a14496e1bdf932b716dba01ba004c317b` |
| `out/r13-rubric-check.json` | `c2cb9dccabab2868522f883b9898b6b34602f2f30d02b5b5f0daa0aa4252d1ce` |
| `out/r13-rubric-v4-decomposition.json` | `4e0c40eaf751f80c3c87c962370d4bd409b66958f9a48f172cbec46270c77232` |
| `tools/eval/independent_judge.py` | `25b55674573f2373844e486458741c4350cf2338099d473f8c6c475080b76896` |
| `tools/eval/label_mapping.py` | `038b0403532625ed316871f8b86aadbef2f902f373a92216a3a0b3d5f3b384e4` |
| `tools/eval/r13_alignment.py` | `b3c98072ba284561b9b109baf1ed3f270a25519b52039f9d9f82355e077591fa` |
| `tools/eval/rubric_v4.py` | `930ca332c3eb09c4b5f9a02eb5d188b11eb3aedc460f7979fea9325a86ccb4a2` |

分解产物 `pass True` / `protected_total 96` / `unattributed_residual 0`；复算产物 `gate_result not_evaluable` / `caliber instrument_alignment_calibration_only`.
