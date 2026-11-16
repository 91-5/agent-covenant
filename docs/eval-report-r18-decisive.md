# 轮十八结案报告 · 决定性一测（最后一次数据补全 + 强制结案）

> 卡：XJ-20261115-001 · 分支 `feature/xj-20261115-001-decisive`（worktree `D:\15812\projects\agent-covenant-r18`，基线 master `5d8de6f`）· 执行者 ZCode（余念安）· 盲化 adjudicator AgnesCode（浮香）· §25 冻结 commit `fc3e77a`（纯追加 162/0，§0–§24 双口径前缀 `cd39e127…`/`c4b3be66…` 不变）· **sir 2026-11-15 确认「按 §25 执行」**
> `caliber = inconclusive_by_stop_rule` · `gate_conclusion_issued = false`（布尔字面）· `capability_gain_claim = false`

## 0. 结案分支声明（三分支必居其一）

**本报告结案分支 = `inconclusive_by_stop_rule`，触发项 = stop rule ②：「补全后 M1 差 <10pp 或 CI 跨零」——两条子条件同时成立**（M1 两臂配对差 +6.04pp < 10pp，且 95% CI [−1.02, +14.23] 跨零；M2 亦不达）。按卡面 stop rule 硬条件表「任一触发立即转结案分支 `inconclusive_by_stop_rule`，停止投入」的字面指令执行。

**实质结论（insufficient_evidence 模板句，逐字）**：**现有证据不足以支持『门禁降低假验证』。** 本轮数据补全后，主分析未观察到达到预注册最小效应（≥10pp 且 95% CI 不跨零）的两臂差异；阴性结果照实登记为「未观察到足够差异」——不是仪器问题，不提议第 19 轮（`instrument_calibration_only` 自本轮起禁用）。

**分支措辞优先级歧义（照实登记，交浮香裁定）**：stop rule ② 的触发条件与 `insufficient_evidence` 分支的触发条件（「差 <10pp 或 CI 跨零」）字面相同，两个分支因此重叠；本报告按 stop rule 表的「立即转」字面指令选择 `inconclusive_by_stop_rule`，并同时满足 `insufficient_evidence` 的明写要求（上句）。若浮香裁定分支标签应为 `insufficient_evidence`，本报告仅需改标签一词，实质内容不变。

## 1. 冻结序与数据源

§25 修正案（v2.6 → v2.7）以纯追加冻结于轮十八任何补数据之前；sir 于冻结当日确认「按 §25 执行」（stop rule ③ 自此解除）。本轮全部读数来自三类被授权动作：①234 条二次盲判（双视图 + 机械盲化 + 仲裁分流）②外部锚子集（30 条盲判包已交付 sir，agent 视图先封）③§5 冻结方法的首次忠实执行（封存盲判 join，零重判级）。判级器与其余仪器零改动。

- **结论 C1**：冻结序合法（纯追加、双口径前缀不变、早于一切补数据）；D2/D3/D4 全部规则从 §25 `R18-DECISIVE` 块机械读回。 [artifact: docs/eval-prereg.md sha256=d7f64a397cba68dc3a5225079627ededb8f3230ac6b09db14a9e84f4c2119c53]（docs/eval-prereg.md）d7f64a397cba68dc3a5225079627ededb8f3230ac6b09db14a9e84f4c2119c53

## 2. coverage 框（全分母 400）：0.415 → 0.9725，stop rule ① 未触发

234 条原 `unjudgeable` 二次盲判（双视图、盲于层/臂/T\*/既有判级）：

| 项 | 值 |
|---|---|
| 双视图一致 | **225/234（96.2%）**（一致行：true 97 / false 126 — 精确计数见 `out/r18-rejudge.json`） |
| 分歧 | 9 条（全部 goldset 文本族），按 §25-B.4 保守计 `still_unjudgeable`，送 AgnesCode 盲仲裁（仲裁只会抬升 coverage，不会降低） |
| 全分母 coverage | **389/400 = 0.9725 ≥ 0.70（stop rule ① 未触发）** |
| 诚实降级 | `two_human_independent = false`；单 agent 双隔离视图（全新上下文子代理 ×8，两种子洗牌、先封 A 再开 B）+ 外部仲裁；只作方向诊断 |

全域假支持率维持轮十五冻结结论原样：`FP_overall = not_estimable (truth_coverage_gap, coverage = 0.415 < 0.70)`（历史字面；本轮 coverage 补全不回改该冻结读数）。轮十五层内读数历史字面（scope-tag: FP_anchor_miss → `FP[anchor_miss]`，post-hoc layer subset，禁止外推）：`FP[anchor_miss] = 1.000 (48/48, Wilson 95% [0.9259, 1.0])`。在 T\* 可判子集上，主轨 E4 判定与 T\* 真值呈负向关联；该关联由层构成解释，不构成总体判别力估计。

- **结论 C2**：二次盲判使 coverage 达 0.9725（全分母 400），stop rule ① 未触发；双视图一致性 225/234，9 条分歧保守单列待仲裁。 [artifact: out/r18-rejudge.json sha256=8851c1fb2b712f4c01578baa91d1a905de978eacc9f654e8023ca544da5f77eb]（out/r18-rejudge.json）8851c1fb2b712f4c01578baa91d1a905de978eacc9f654e8023ca544da5f77eb [artifact: run-r18/custody-ledger.json sha256=c89a277664de839b1415ecd38b30a85feb3bd18147b1bb740aec70099dbe743b]（run-r18/custody-ledger.json）c89a277664de839b1415ecd38b30a85feb3bd18147b1bb740aec70099dbe743b

## 3. 两臂框（M1/M2，§5 字面）：判据未达 → stop rule ②

§5 冻结方法首次忠实执行：分析单位=断言、推断单位=任务、每任务配对差 = 指标(A) − 指标(B)、3 重复合并、30 任务均值、bootstrap over 任务（B=10000，种子 20261115）。输入 = `.eval-sealed/pkg-r9-shadow/judgements-blind.json`（900 条封存盲判）× round-6 custody key（P-code→task/condition），**零重判级**。

| 指标 | 配对差（A−B） | 95% CI | 达判据（≥10pp 且 CI 不跨零） |
|---|---|---|---|
| M1（假验证率，v1.2 C5 口径） | **+6.04pp** | **[−1.02, +14.23]（跨零）** | **否** |
| M2（无依据主张率） | −5.15pp | [−12.79, +2.13]（跨零） | 否 |

- **方向审计（§25-D.3）**：同一 join 复算历史第 9 轮 +5.8pp → 得 +6.04pp，差 0.24pp 超出舍入容差 → **`direction_unanchorable`**，按冻结路径「判据仍按 §5 字面方向执行 + 两种方向并列披露」：A−B = +6.04pp [−1.02, +14.23] 未达；B−A = −6.04pp [−14.23, +1.02] 未达。**分支决策对方向歧义稳健——任一方向都不达判据。** F4 聚合读数 +6.153846 并列报告（claim 级聚合差，与任务配对层级不可比）。
- **读数状态（r17 X-7.3 映射延续）**：两臂框读数状态 = **`PROVISIONAL-L1`**（a=PASS：r17 manifest match；b=CONDITIONAL：L2 挂账；c=0.0：r17 探针 3/3 identical）——可用，须披露安全边界未隔离；本轮结案不改变该状态标签，L2 永不落地时 PROVISIONAL-L1 即终态并在此显式披露（review Q3 延续）。
- **最坏情况 bounds（仅披露）**：gate_worst −11.37pp / gate_best +17.38pp——不可判类（E0/E1，60 条/臂）使配对差在 ±14pp 量级摆动，判据评估只用主估计 + CI。
- **敏感性（仅披露）**：M1/M2 分母按冻结公式本就排除 E0/E1，主估计即剔除估计（恒等登记，证明无剔除操纵空间）；coverage 框「剔除 still_unjudgeable = 1.0」仅作展示，标注 forbidden_for_passing。

- **结论 C3**：M1/M2 两臂配对差均未达预注册判据（M1 +6.04pp CI 跨零；M2 −5.15pp CI 跨零）→ **stop rule ② 触发**，`gate_conclusion_issued = false`。 [artifact: out/r18-primary-analysis.json sha256=76cc271f028796d2bd16a6b8b38b6b0c1932e529ecfb03e8342fe8b7766b35f2]（out/r18-primary-analysis.json）76cc271f028796d2bd16a6b8b38b6b0c1932e529ecfb03e8342fe8b7766b35f2 [artifact: tools/eval/r18_primary_analysis.py sha256=c350296d7cb0c36b3e95347e32b36c3419394dc5ea0c40a64f3c607d1042eee0]（tools/eval/r18_primary_analysis.py）c350296d7cb0c36b3e95347e32b36c3419394dc5ea0c40a64f3c607d1042eee0

## 4. stop rule 判定表（五条全量）

| # | 条件 | 判定 |
|---|---|---|
| ① | 结案日 coverage 仍 <0.70 | **未触发**（coverage = 0.9725，2026-11-15 即已达标） |
| ② | 补全后 M1 差 <10pp 或 CI 跨零 | **触发（本结案分支的触发项）**：+6.04pp <10pp 且 CI 跨零 |
| ③ | §25 修正案被治理方否决 | 未触发（sir 2026-11-15 确认「按 §25 执行」） |
| ④ | 补数据后仍无法归因、只能再修仪器 | 未触发（归因清楚：差异未达判据，不是仪器不可归因） |
| ⑤ | 独立性仍只能 false 且预注册不允许 partial | 未触发（§25-C 许可 partial，独立性问题不阻断结案） |

## 5. 独立性：partial（κ = 1.00 almost-perfect；外部锚经改派，偏差登记）

30 条外部锚盲判包按冻结种子分层抽取（12 T\*-true / 8 T\*-false / 10 前 unjudgeable），盲字段交付；**agent 视图（ZCode）在对方判定之前封存**（sha `e9760df7…`，30/30；首视图 29/30 旁证，自导航瑕疵照实登记）。**判定者改派登记（偏差，交浮香裁定）**：卡面写「sir 盲判 30 条」；sir 于 2026-11-15 决定将该批盲判委托给 **WorkBuddy**（另一 agent harness）执行——判定者 = WorkBuddy agent + ZCode agent，**非人类锚**。Cohen κ 按 §25-C 冻结口径计算（二值化、still_unjudgeable 排除分母并单列）：

| 项 | 值 |
|---|---|
| 判定子集 | 24 条（WB 与 agent 均给出 true/false） |
| 观察一致率 | **24/24 = 1.000** |
| Cohen κ | **1.0000（almost_perfect 带）** |
| κ 分母外单列 | WB 6 条 still_unjudgeable / agent 1 条（不对称已逐条披露） |

**措辞（锁死口径）**：独立性 = **`partial`**——外部锚经改派为 WorkBuddy agent + ZCode agent，非人类锚，不构成 satisfied；两个 AI agent 间的 κ 上限是跨 harness 一致性，不等于人类独立性（执行者历史轮次接触层语义的暴露同样登记为上限）。κ ≥0.81 未触发 exploratory 强制降级；是否因「非人类锚」进一步降为探索性，由浮香裁定。

- **结论 C4**：外部锚协议机械在位（包交付、agent 视图先封、key 隔离）；κ = 1.0000（24/24 判定子集，almost_perfect）；判定者改派为 WorkBuddy（用户决定）已登记为偏差交裁定；独立性措辞 = partial（永非 satisfied）。 [artifact: out/r18-external-anchor.json sha256=030a5284256bcef07a510ccb57f99e2c1fad995586054d433414392d27ba262f]（out/r18-external-anchor.json）030a5284256bcef07a510ccb57f99e2c1fad995586054d433414392d27ba262f

## 6. 解释禁令执行声明

本轮阴性结果登记为「未观察到足够差异」：M1 差 +6.04pp 未达 10pp 且 CI 跨零——**不**解释为「仪器还不够好」；**不**提议第 19 轮；`instrument_calibration_only` 未使用（本轮 caliber ∈ 三值白名单）。判据、方向、样本框均按 §25 冻结文本执行，无端点修改、无分母剔除达标、无新指标。

## 7. 未闭合项（交浮香裁定）

1. 9 条二次盲判分歧的盲仲裁（保守计 still_unjudgeable；仲裁可抬升 coverage 至多至 398/400，不改变本结案分支——M1 未达与 coverage 无关）。
2. 分支措辞优先级（§0 登记的 ②≡insufficient_evidence 重叠）。
3. 判定者改派（sir → WorkBuddy）与 κ=1.0 的效力评估：两个 AI agent 间的一致性能否支撑 partial 措辞，或须降为探索性。
4. D6 副产品（`docs/r18-anchor-blindspot-repro.md`，与主分析物理隔离）的产品缺陷判定的处置：修复须改判级器 = 改测量基准，按既有纪律须 sir + 独立预注册 + 基准版本化全量重跑。

## 8. Limitation（post-hoc, not_for_passing）

**性质声明（先于读数）**：本节为**后验灵敏度刻画**（`post_hoc_sensitivity`、`not_for_passing = true`），由 Orchestrator 在结案后完成，输入仅为冻结产物 `out/r18-primary-analysis.json`（只读），**零新判据、零仪器改动**。本节**不构成**任何 M 读数、门结论或能力主张的依据，**不改变** §0 的 `inconclusive_by_stop_rule` 结案分支。

**读数**：M1 两臂配对差 **+6.04pp**；95% CI —— **冻结 percentile bootstrap [−1.02, +14.23]**（冻结端点口径）、**解析正态 [−1.02, +13.76]**（诊断口径）。n=30 任务、每任务配对差 SD **21.58pp**、SE 3.94pp。

**灵敏度**：80% 功效最小可检出效应 **MDE(80%) ≈ 11.04pp**；若真实效应为 10pp，功效 ≈ **0.719**；达 80% 功效需 ≈ **36.5** 个任务（9pp 需 ≈45.1）。

**结论（措辞受 post-hoc 附录裁定 Q-C 约束）**：本设计属**临界欠功效**（10pp 处功效约 72%）。因此本轮**未观察到 ≥14pp 的效应**，但 **10pp 量级效应不能排除**；对 ≥14pp 的排除**仅在解析正态口径成立**（上界 13.76 < 14），**冻结 bootstrap 口径处于边界**（上界 14.229 > 14）。外部锚独立性为 `partial`（非人类锚，见 §5）。

**口径提示**：以上为**预注册条件下、冻结两臂框（round-6 两臂封存语料，n=30 任务）的层内对照证据**，**不构成对门禁能力的证明**，**亦不外推为全域**。判据与端点未因本节改变。

## 附：产物哈希（生成时实时计算）

| 产物 | sha256 |
|---|---|
| out/r18-rejudge.json | 见结论 C2 指针 |
| out/r18-primary-analysis.json | 见结论 C3 指针 |
| out/r18-external-anchor.json | 见结论 C4 指针 |
| run-r18/custody-ledger.json | 见结论 C2 指针 |
