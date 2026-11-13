# 递评单 · XJ-20261113-003（轮十六 报告措辞勘误与 X-7.3' 拆分，P0-a 文本层）

> 递评人：WorkBuddy（执行者代号 **WB**）· 2026-11-13
> 评审员：**浮香（AgnesCode）**；Orchestrator 预审
> 仓库：`D:\15812\projects\agent-covenant` · 分支 `feature/xj-20261113-003-round16-erratum` · 基线 master `0e06f23` · 接卡点 `efff6df`
> 状态：**IN_REVIEW**（D1–D5 交付完成；V1–V10 执行者亲跑；**执行者不宣布验收通过**）
> 执行者无评审权、无合并权：不 push / 不 merge / 不写 verdict / 不自评审 / 未碰 master / 红区零触碰

---

## 1. 一句话结论

**本卡是文本与条款层勘误，零新数据、零重算、零仪器执行，所有数值一字不改。** §23 在任何 D2–D5 产物之前纯追加冻结（`c990b26`，`264 0`，§0–§22 前缀工作树 raw `4c71623a…` 与 blob LF `19c453c2…` 双口径逐字节不变）。两处违规按「原文逐字保留 + 置顶勘误表 + 行内标记 + 更正句紧随」落地：① `FP_overall` 标签越界改为 `FP[anchor_miss] = 1.000 (48/48, Wilson 95% [0.9259, 1.0])` + `FP_overall = not_estimable (truth_coverage_gap, coverage = 0.415 < 0.70)`；② 负向关联读数按 §23 `D-5.1` 降级为「由层构成解释，**不构成总体判别力估计**」。X-7.3 拆为 a/b/c 三门并给出 M1 状态映射（`PROVISIONAL-L1`）与 `E-0` L0–L2 能力矩阵，**只落条款、不实现、不改轮十五任何读数**。`out/fp-overall.json` 逐字节未动（`point = 1.0`）。`gate_result = not_evaluable`、`gate_conclusion_issued = false`、`capability_gain_claim = false`、`independence_satisfied = false`。

## 2. 交付清单（D1→D5）

| 阶段 | commit | 交付物 | 关键实况 |
|---|---|---|---|
| 接卡 | `f914001` | 卡面 Status | OPEN → IN_PROGRESS，代号 WB；接卡时工作树干净、零 r16 产物 |
| D1 | `c990b26` | `docs/eval-prereg.md` §23 | 冻结早于一切 D2–D5 产物（`22:22:14`）；纯追加 `264/0`；6 组条款（`D-5.1` / `P-4.5''` / `X-7.3'` a,b,c / M1 状态映射 / `E-0` L0-L2 / 勘误连续性）+ `R16-ERRATUM` 机器可读冻结块 |
| D2 | 本次收尾 | `tools/eval/report_lint.py` | 5 项机械检查，规则全部从 §23 冻结块读回；`--self-test` 含 5 条构造违规负向用例（必须失败）+ 1 条合规正向用例 |
| D3 | 本次收尾 | `docs/eval-report-r15-truth.md` | 逐行纯插入 `19/0`（删除列 0）；原 189 行逐字保留；置顶勘误表 2 条 + 4 处行内标记；LF 长度 `13554 → 16243` |
| D4 | 本次收尾 | `docs/eval-report-r16-erratum.md` | 勘误说明 + report_lint 全绿证据 + 数值不变证明 |
| D5 | 本次收尾 | `run-r16/` seal、`artifacts.json` 台账、卡转 IN_REVIEW、本单 | seal 经只读 `tools/eval/seal_run.py --verify` 复核；产物走 custody 不入 repo |

仓外 custody：`D:/15812/projects/round16-custody`（冻结脚本、勘误脚本与锚点、sealed 副本）。

## 3. 关键读数（全部来自亲跑产物）

| 项 | 读数 | 说明 |
|---|---|---|
| 冻结序 | §23 `c990b26` 早于 D2–D5 全部产物 | `git diff 0e06f23 --numstat -- docs/eval-prereg.md` = `264 0`；前缀双口径 SHA 不变 |
| 勘误连续性 | `19 0`，原文 189 行逐字保留 | 脚本断言「剥离插入行后逐行等于原文」；`BASE_LINES_SUBSEQUENCE_OF_CURRENT = True` |
| 数值不变 | `REMOVED_NUMERIC_TOKENS = {}` | 零删除；`48/48` 按 dp 冻结格式补入（分母 48 / 分子 48 本就分列于 §3.4 表，未改动） |
| report_lint | 未勘误报告 `FAIL / violations=8`；勘误后 `PASS / checks=5` | 负向干跑证明工具非空转；自测 5 条违规样本全部被正确拒绝 |
| V4 禁词 | `False False False` | 勘误表以转述 + 位置引用代替逐字复刻（`§23 D23-F.4`） |
| V6 长度 | `True 4 16243`（> 13554） | 净增 2689，证明是追加而非删改 |
| `out/fp-overall.json` | sha256 `df8d2d0e…`，`point = 1.0` | 封存产物零触碰，`git status --porcelain out/` 无该文件 |
| X-7.3' | a / b / c 三门；`PROVISIONAL-L1`；`CONDITIONAL`；L0/L1/L2 | **只落条款**，`env_manifest.py` / `nondeterminism_probe.py` / `x73_gate.py` 均未实现 |
| M1 / 历史值 | `+6.153846` pp（`PROVISIONAL`）/ `+5.8` pp | **未回改、未重跑、未替换历史值**；本卡零重算 |

## 4. V1–V10 亲跑台账

> 执行者亲跑，不采纳作者 precheck；真实退出码与日志落在 `out/acceptance-r16.json` / `out/acceptance-r16.log`，并封入 `run-r16/`。

| 验收 | 退出码 | 验收 | 退出码 |
|---|---|---|---|
| V1 §23 纯追加 + 前缀双口径 | 0 | V6 勘误表 / 标记数 / 长度 | 0 |
| V2 §23 七标记机械可读 | 0 | V7 X-7.3' 状态映射表 | 0 |
| V3 report_lint 全绿 | 0 | V8 `--self-test` 负向用例 | 0 |
| V4 禁词三项 | 0 | V9 红区 / 单测 / lint | 0 |
| V5 数值逐字核 | 0 | V10 `fp-overall.json` 未改 | 0 |

**非零项：无**（与轮十五 V9 exit 1 不同，本卡无卡面允许的降级路径被触发）。但**执行者不据此宣布验收通过**——本卡是文本勘误轮，验收权在浮香。另有两次预期失败（非卡面验收项、照实登记）：D2 未勘误报告 lint 负向干跑 `exit 1`（证明工具非空转）、探查链中 `grep -c` 因零删除行返回 1（无匹配即删除列为 0）。

## 5. 执行者立场（不裁定，交浮香）

- **Q1（保留错误原文 vs 原地改对）**：按卡面连续性要求保留原文 + 勘误表；对已 PASS 并合入的报告，撤改不留审计轨迹风险更高。但**只读正文不读置顶勘误表确实可能误导后来读者**，缓解手段是把勘误表放在报告最顶部（§0-E，先于原 §0）并加 4 处行内标记。是否足够，请裁定。
- **Q2（词表 lint 能否被绕过）**：能，换同义表述即可绕过。`report_lint.py` 的价值是**防疏忽、防回归**，不是**防规避**；它保证冻结禁词、标签形式与勘误表在位可机械复核，不替代评审员读语义。V3 `PASS` 只表示冻结规则被机械满足。
- **Q3（后 verdict 覆盖前 verdict）**：本卡不写 verdict，不使用 `superseded by later verdict` 语义；列 `docs/eval-report-r15-truth.md` 为 Owned file 只为登记**文本勘误**，不改写任何已冻结读数。是否仍构成 authority 覆盖，请裁定。
- **Q4（`PROVISIONAL-L1` 是否实质降标准）**：`a` 与 `c` 的实测标准未降，降的只是 `b` 的处置（阻断 → 披露）；「后续悄悄当作已满足」的风险真实存在，§23 已冻结「`CONDITIONAL` 是披露项，永远不是已满足的门」。本卡不解锁任何新读数。
- **Q5（轮十五 verdict 是否给「无瑕疵」印象）**：会。是否回写 verdict notes 需要浮香重签，本卡不越权。
- **Q6（永久 `CONDITIONAL` 是否只是把「永久 FAIL」改名）**：有可能。若本环境永远没有 L2，`X-7.3b` 将永久停在 `CONDITIONAL`，`PROVISIONAL-L1` 会成为事实终态。拆分澄清了 PROVISIONAL 的真实成因（安全边界缺失，不是数值不可信），但**不解锁任何新读数**。L2 挂账由 sir 拍板，本卡不引入容器/VM 依赖。

## 6. 需评审裁定的执行面事项

1. **`.gitignore` 追加 `run-r16/`**：该文件**不在本卡 Owned files**，按轮十四/轮十五先例仅追加一行，在此照实披露，请裁定是否接受。
2. **Markdown 渲染取舍**：为保持「原句逐字保留、零改写」，行内标记以独立行插在有序列表项之间，会打断有序列表的连续渲染；§0-E 勘误区编号与原 `## §0` 并存，标记内「§0」按卡面字面指代置顶勘误区。不影响任何数值、条款或验收项；是否调整请裁定，执行者不擅自挪动原文。
3. **勘误表不逐字复刻禁词**：预审 N1 原措辞命中 §23 `D-5.1` 禁词表，逐字抄进勘误表会让勘误后的报告重新引入一个被禁止的全域断言，且 V4 会失败。可追溯性由位置引用（`14228a7`、卡面 Context 违规 2）保证，此为 §23 `D23-F.4` 冻结策略。请裁定该引述策略是否满足审计连续性。
4. **是否要求回写轮十五 verdict notes**（Q5），以及是否要求下一轮把 `X-7.3'` 三门做成可执行实现（本卡按卡面明确不实现）。
5. **工作树中的非本卡外源改动**：全量验收期间出现 `scripts/verdict_gate.ps1` 未提交改动（`4 3`，PowerShell 空集合判断加固，mtime `22:29:13`）。它不在本卡 Owned files、不在红区 11 条路径内，执行者任何脚本均未触碰。处置为**不提交、不回滚、精确 `git add` 本卡文件**，提交后工作树仍保留该 `M`；V1/V9a/V9c 均不含此路径，验收结论不受影响。请裁定是否属其他卡工作、应由对应会话自行处理。

---

*执行者：WB（WorkBuddy，ZCode 桌面会话）· 2026-11-13 · 本单不构成验收通过，等待 Orchestrator 预审 + 浮香 PASS gate。*

---

## 8. Orchestrator 预审（2026-11-13，亲跑复核，不采纳 precheck）

预审者：Jarvis（OpenCode）/ 分支 `feature/xj-20261113-003-round16-erratum` @ `99eff97`，基线 `0e06f23`。本节仅追加，不改执行者任何原文。

### 8.1 独立复现（全部亲跑）

| 项 | 我的实测 | 结论 |
|---|---|---|
| 红区 11 完整路径 `git diff 0e06f23 --stat` | 空输出 | 零触碰 |
| V1 | prereg `264/0` 纯追加； 存在且 8 个条款 ID 全命中 | 复现 |
| V3 report_lint | `LINT: PASS | checks=5 | coverage_gap_guard=OK | erratum_markers=4 | lf_chars=16243` | 复现 |
| V4 禁词 | `判别力为负=False`、`判别力 −=False`、`完全缺失=False` | 复现 |
| V5 数值 | `48/48` / `0.415` / `0.9259` / `6.15…` 全部在位 | 复现 |
| V6 勘误表 | `勘误表=True`、`【勘误`×4、长度 `13554 → 16243` | 复现 |
| V8 自测 | `SELFTEST_NEGATIVE_CASES=5` 全 PASS，负向用例构造违规样本被拒（violations=4/1/1） | 工具不空转 |
| V10 封存件 | `out/fp-overall.json` `point=1.0`、sha `df8d2d0e…`、`git status out/` 无改动 | 未污染 |
| 原文保全（我另加的硬核） | 轮十五 189 行是现文件的**有序子序列 189/189** | 纯插入坐实，不是改写 |
| 单测 / lint | 546 OK（设 `COVENANT_BASH_HINT`）/ `LINT: PASS (1 warnings)` | 通过 |

我额外做了一项执行者没做的检查：**用 `git show 0e06f23:docs/eval-report-r15-truth.md` 取原文 189 行，逐行验证它是现文件的有序子序列 → 189/189 命中**。这比「删除列 0」更强，因为它同时排除了「删一行再在别处加一行」的可能。

### 8.2 预审新增发现：外源改动 `scripts/verdict_gate.ps1`（我认为比执行者判断的更严重）

执行者的处置是「披露、不提交、不回滚」，我认同这个**动作**，但不同意「不阻断」的定性。理由：

**这不是普通的外源改动，是合并门禁脚本本身的语义变更。** diff 内容：

```diff
-if (-not $all) {
+$all = @($all | Where-Object { $_ -ne $null })
+if (-not $all -or $all.Count -eq 0) {
-$codeVerdicts = $all | Where-Object { -not $_.IsDesign }
-if (-not $codeVerdicts) {
+$codeVerdicts = @($all | Where-Object { -not $_.IsDesign })
+if (-not $codeVerdicts -or $codeVerdicts.Count -eq 0) {
```

这是对 PowerShell 集合语义的加固（`@($null)` 与单元素标量的 `-not` 判定），改动本身**大概率是正确且必要的**。但它是 **AGENTS.md §4.2.8 所依赖的门禁脚本**，其判定逻辑直接决定「能不能合并」。

**三个具体风险**：

1. **仓内版本与工作树版本不一致**：仓库里 `bb8bd06`（旧），工作树 `0e597f9`（新）。任何用 `git` 干净检出的人拿到的是旧版；任何在本工作树跑 gate 的人用的是新版。**下一次合并到底被哪个版本判过，无法从 commit 记录回答。**
2. **改动未经任何 verdict**：`scripts/verdict_gate.ps1` 是 EVO-20261113-001 的交付物，其 round2 verdict 是对**旧版本**签的。改它等于让 verdict 的签署对象发生变化。
3. **改的是「判定器本身」**：这正是 AGENTS.md §5.3 受保护第 5 项（`gate.py` 判定逻辑）的同构对象。自进化系统不得在不经复核的情况下替换自己的评测器。

**我的建议（请评审裁定）**：
- 本轮**不提交**（执行者做法正确），也不阻断轮十六
- 但**不得**当作「不阻断」了事，应立独立小卡（EVO 跟进）：
  - (a) 提交该改动并附**改动理由 + 空集合/单元素真值表**（证明加固前后行为差异）；
  - (b) 由浮香对该脚本变更出**增量 verdict**（不重开 EVO-20261113-001 全卡，只裁脚本语义变更）；
  - (c) 在此之前，把「本地合并使用未提交的 gate 脚本版本」登记进 `ledger/LEDGER-PROCESS-VIOLATIONS.md` 或等价说明，避免后续审计出现「版本不可追溯」。
- 若评审认为这属于「工具卫生」无需走 EVO，也请明确写「判定：不需 EVO 复核 + 理由」，而不是留空。

### 8.3 预审新增发现：Markdown 取舍（执行者的选择我认为正确，但有一个补法）

执行者为了让「原文逐字保留」，把行内标记作为独立行插在有序列表项之间，导致两点：`## §0-E` 与原 `## §0` 并存（两个一级小节），列表渲染被打断。

我的判断：**审计连续性优先于渲染美观，执行者的取舍正确**。但建议补一句在  开头：
> 「本勘误采用逐行插入，可能打断 Markdown 列表渲染；这是为满足『原文逐字可追溯』而付的格式代价。」

理由：后来读者看到断掉的列表会以为是编辑事故，一句说明能省掉一次误判。

### 8.4 一句总评（预审视角）

轮十六做到了我要求的最难的一件事：**在「改对」与「不改原文」之间同时成立**（189/189 有序子序列 + 数值零变化 + 4 处行内标记 + 2 条勘误表）。`report_lint` 有 5 条负向自测、且对未勘误报告干跑得出 `violations=8`，说明它不是空转的装饰。

唯一比执行者判断更严重的是 `verdict_gate.ps1`：**它被改了，而它决定「什么算可合并」**。这条我要求评审必须给出明确裁定（8.2 的 a/b/c 三项），不能只写「不阻断」。
