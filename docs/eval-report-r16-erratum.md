# 轮十六报告 · 报告措辞勘误与 X-7.3' 拆分（P0-a 文本层，XJ-20261113-003）

> 执行者：WorkBuddy（代号 **WB**，ZCode 桌面会话）· 2026-11-13
> 分支 `feature/xj-20261113-003-round16-erratum` · 基线 master `0e06f23` · 接卡点 `efff6df`
> **本卡性质：文本与条款层勘误，零新数据、零重算、零仪器执行。所有数值一字不改。**
> `gate_result = not_evaluable` · `gate_conclusion_issued = false` · `capability_gain_claim = false` · `independence_satisfied = false`
> **执行者无评审权、无合并权：不 push / 不 merge / 不写 verdict / 不碰 master / 红区零触碰。本单不宣布验收通过。**

---

## §0 置顶结论

轮十五报告已 PASS 并合入 master，回改**不得静默改写**。本卡把两处 dp 复核认定的措辞违规以「原文逐字保留 + 置顶勘误表 + 行内标记 + 更正句紧随」的方式落地，并把 X-7.3 拆成 a/b/c 三门（只落条款、不实现）。三件核心事实：

1. **违规 1 · `FP_overall` 标签越界**：`coverage=0.415 < 0.70` 时不得以总体率命名点估计。正确写法 `FP[anchor_miss] = 1.000 (48/48, Wilson 95% [0.9259, 1.0])` + `FP_overall = not_estimable (truth_coverage_gap, coverage = 0.415 < 0.70)`。责任归属照实登记：执行者写标签，Orchestrator 预审核了分母严格性（`Tstar_false=48`）但漏检「coverage<0.70 时能否用 `FP_overall` 之名」。
2. **违规 2 · 负向关联读数的越界结论**：T\* 只覆盖 41.5%，不能对 234 条 `unjudgeable` 样本作全域断言；`−0.1525` 是**两个不同层条件率相减的层构成伪影**，不是判别力。按 §23 `D-5.1` 降级为「在 T\* 可判子集上呈负向关联，由层构成解释，**不构成总体判别力估计**」。
3. **X-7.3' 拆分**：原条款把「可复现性 manifest」与「安全性 sandbox」绑定，导致 M1 永久 `PROVISIONAL`，而唯一成因是安全边界缺失、不是数值不可信。拆为 `X-7.3a`（环境可复现，无沙箱可 PASS）/ `X-7.3b`（隔离安全，L2→PASS、L1→`CONDITIONAL`、L0→FAIL）/ `X-7.3c`（非确定性，`UNMEASURED` 不得当 ≤0.05）。`a=PASS ∧ b=CONDITIONAL ∧ c≤0.05` → `PROVISIONAL-L1`（可用，须披露）。**本卡只落条款，不改轮十五任何读数与 `PROVISIONAL` 状态。L2 真沙箱本轮挂账不立项。**

---

## §1 交付链与冻结序

| 阶段 | commit | 交付物 | 实况 |
|---|---|---|---|
| 接卡 | `f914001` | 卡面 Status | OPEN → IN_PROGRESS，代号 WB；接卡点 `efff6df`（上游建卡 commit `efff6df`，其本身只含卡面与 artifacts 预置映射），工作树干净、零 r16 产物 |
| D1 | `c990b26` | `docs/eval-prereg.md` §23 | **冻结早于一切 D2–D5 产物**（`2026-11-13T22:22:14+08:00`）；纯追加 `264 0`；§0–§22 前缀工作树 raw `4c71623a…` / blob LF `19c453c2…` 双口径逐字节不变；6 组条款 + `R16-ERRATUM` 机器可读冻结块 |
| D2 | 本次收尾 | `tools/eval/report_lint.py` | 5 项机械检查、规则全部从 §23 冻结块读回；`--self-test` 含 5 条构造违规负向用例（必须失败）+ 1 条合规正向用例 |
| D3 | 本次收尾 | `docs/eval-report-r15-truth.md` | 逐行纯插入 `19 0`（删除列 0）；原 189 行逐字保留；置顶勘误表 2 条 + 4 处行内标记；LF 长度 `13554 → 16243`（净增 2689） |
| D4 | 本次收尾 | 本报告 | 勘误说明 + report_lint 全绿证据 + 数值不变证明 |
| D5 | 本次收尾 | `run-r16/` seal、`artifacts.json`、卡转 `IN_REVIEW`、递评单 | seal 经只读 `tools/eval/seal_run.py --verify` 复核 |

**冻结序机械证明**：`c990b26`（D1）早于 `report_lint.py`、轮十五报告勘误、本报告及一切 `run-r16/` 产物；V1 的 `git diff 0e06f23 --numstat -- docs/eval-prereg.md` 为 `264 0`，前缀双口径 SHA 未变。

**换行口径说明（Windows `core.autocrlf=true`）**：`docs/eval-prereg.md` 的 git blob 是 LF（237249 B / `19c453c2…`），工作树检出为 CRLF（239185 B / `4c71623a…`）。§23 由仓外脚本以**二进制追加 CRLF 字节**写入，断言 `after[:239185] == before`，故工作树前缀逐字节不变；`git diff` 删除列为 0。轮十五报告同理：blob LF 13554 字符，工作树 CRLF，勘误以逐行纯插入（CRLF 保持）落地，**未发生整文件换行重写**。

---

## §2 两处勘误对照（原文 / 更正 / 依据 / 认定方）

| # | 位置 | 原文（保留 / 转述） | 更正 | 依据条款 | 认定方 |
|---|---|---|---|---|---|
| 1 | 轮十五报告 §0 第 1 条、§3.4 数值表 | ~~`FP_overall = 1.0`~~（历史标签，已划注作废；当时附 `denominator_basis=Tstar_false`、`coverage=0.415`、`truth_coverage_gap=true`）。原句在正文逐字保留、未删除。 | `FP[anchor_miss] = 1.000 (48/48, Wilson 95% [0.9259, 1.0])` 为**层内条件率读数**（带强制 `scope-tag`）；`FP_overall = not_estimable (truth_coverage_gap, coverage = 0.415 < 0.70)`。分母 48、分子 48、Wilson 区间、覆盖率与缺口标记**一字不改**，只改标签与结论形式。 | §23 `P-4.5''`（落实 §22 `P-4.5'`） | dp 复核认定 + sir 拍板；执行者写标签、Orchestrator 预审漏检，责任归属照实登记 |
| 2 | 轮十五报告 §3.4 末段（review Q3）、§6 第 2 条；上游预审 N1（`14228a7`） | 预审 N1 曾对 234 条 `unjudgeable` 样本作全域缺席断言，并把 `−0.1525` 的层间差值当作判别读数。按 §23 `D23-F.4` 引述策略**只作转述 + 位置引用，不逐字复刻**禁词（逐字原文见 `14228a7` 与本卡 Context 违规 2）。 | §23 `D-5.1` 唯一允许表述：在 T\* 可判子集上，主轨 E4 判定与 T\* 真值呈负向关联；该关联由层构成解释（`T*=false` 48 条 100% 来自 `anchor_miss` 的构造性恒等，`T*=true` 的 18 条否决 100% 来自 `cwd_probe`），**不构成总体判别力估计**。能站住的只有三条：层内零否决 48/48；非断言支撑维度的敏感性；对 234 条 `unjudgeable` 判别力**不可评估**。 | §23 `D-5.1`（dp 条款，浮香认证为 ADV-8） | dp 复核认定 + sir 拍板 |

**为什么勘误表「原文」栏不逐字复刻违规 2 的原句**：预审 N1 的原措辞命中 §23 `D-5.1` 禁词表，逐字抄进勘误表会让勘误后的报告重新引入一个被禁止的全域断言，且 V4 的三项禁词检查会失败。可追溯性由**位置引用**（上游 commit `14228a7`、本卡 Context 违规 2）保证，而不是由复制禁词保证；这是 §23 `D23-F.4` 冻结的引述策略，不是执行者临场取舍。

---

## §3 `report_lint.py` 全绿证据

工具 `tools/eval/report_lint.py` 的阈值、禁词表、`scope-tag` 字面量、勘误连续性要求**全部从 §23 `R16-ERRATUM` 冻结块读回**（`rules_source = section 23 D23-G`），代码里不另立一套规则。5 项检查：`coverage<0.70` 禁 `FP_overall` 点估计 + 强制 `not_estimable`；禁总域判别力措辞并强制保留降级表述；强制 `scope-tag`；强制 `PROVISIONAL`；强制勘误表与 ≥2 处行内标记。

| 证据 | 命令 / 输出 | 退出码 |
|---|---|---|
| 未勘误报告**负向干跑**（防工具空转） | `LINT: FAIL \| violations=8 \| report=docs/eval-report-r15-truth.md`（缺 `not_estimable`、未划注点估计、缺 scope-tag、缺勘误表等） | **1**（预期失败） |
| V8 自测 | `SELFTEST: PASS`；1 条合规正向用例 + **5 条构造违规负向用例全部被正确拒绝**（`NEGATIVE_CASES=5`） | **0** |
| V3 勘误后报告全绿 | `LINT: PASS \| checks=5 \| coverage_gap_guard=OK \| erratum_markers=4 \| lf_chars=16243 \| rules=R16-ERRATUM-frozen-block` | **0** |
| lint 证据文件 | `out/r16-report-lint.json`（`status=PASS`、`violations=[]`、规则来源与检查开关齐全） | 0 |

**「历史行」守卫的必要性**：卡面要求「原 `FP_overall = 1.0` 行保留并划注」，而 lint 又要禁止 `coverage<0.70` 时的点估计标签。二者由 `is_guarded_historical()` 调和——带 `~~` / `作废` / `【原文` 标记的行，或**紧随 `【勘误】` 行内标记**的行，被判定为「受保护的历史原文」，不算现行结论；未划注且无勘误守卫的点估计才判违规。负向用例 `NEGATIVE_unstruck_FP_overall_point_estimate_must_fail` 专门验证：把划注去掉、把 `not_estimable` 删掉，工具必须失败（实测 `violations=2`）。这套设计使「保留原文」与「机械禁词」不冲突，也避免把勘误做成删改。

**禁词 lint 的边界（正面回答卡面 review Q2）**：`report_lint.py` 的检查确实是**词表匹配**，换成同义表述可以绕过（例如把越界结论改写成未被列举的措辞）。因此它的实际价值是**防疏忽、防回归**，不是**防规避**：它保证「已冻结的禁词 + 已冻结的标签形式 + 勘误表在位」在 CI 里可机械复核，但无法替代评审员读语义。本报告不宣称该 lint 具备语义理解能力；若需防规避，须另立卡引入语义级检查或人工评审清单。V3 的 `PASS` 只表示**冻结规则已被机械满足**。

---

## §4 数值不变证明（逐字核）

| 检查 | 基线 `0e06f23` 报告 | 勘误后报告 | 结论 |
|---|---|---|---|
| LF 字符数 | 13554 | **16243** | 净增 2689 > 0（V6 要求 `> 13554`） |
| 原文行 | 189 行 | 189 行**逐字保留** + 19 行插入 | `git diff --numstat` = `19 0`，删除列 0；`BASE_LINES_SUBSEQUENCE_OF_CURRENT = True` |
| 数值 token 删除 | — | `REMOVED_NUMERIC_TOKENS = {}` | **零删除**，所有原数值 token 原样在位 |
| `48/48` | 0 次 | 7 次 | 按 dp 正确写法**补入**冻结格式（分母 48 / 分子 48 本就分别写在 §3.4 表中，未改动），V5 要求为真 |
| `0.415` / `0.9259` / `6.153846` | 6 / 3 / 4 次 | 11 / 7 / 5 次 | 只增不减，原串未改 |
| `1.000` / `0.035` / `118` / `48` / `234` | 2 / 3 / 7 / 16 / 8 | 6 / 4 / 8 / 36 / 12 | 只增不减 |
| `out/fp-overall.json` | sha256 `df8d2d0e…` | sha256 `df8d2d0e…` | **逐字节未改**，`point = 1.0` 原值保留（V10） |

新增的数值 token 全部来自：勘误表的 dp 正确写法（`48/48`、`1.000`、`0.9259`）、条款编号与阈值引用（`0.70`、`D-5.1`、`P-4.5''`、§23）、日期与 commit 号、`14228a7` 位置引用、`−0.1525` 的转述。**没有任何一个原有数值被改写成另一个值**；`48/48` 是补写冻结格式，不是把原分母/分子换成新数。

**关于 `out/fp-overall.json` 未被勘误污染**：该文件是轮十五封存产物，字段名 `FP_overall` / `point` 是历史名。本卡只在报告文本与新增 lint 工具层更正表述，文件本身零触碰；报告 §3.4 表下的勘误标记明确注明「字段名为历史名、未改，正式表述见 §0 勘误表」。

---

## §5 X-7.3' 拆分与 L2 挂账（只落条款，不实现）

| 门 | 内容 | 无沙箱可否 PASS | 状态映射 |
|---|---|---|---|
| **X-7.3a 环境可复现** | manifest 含 `python_version` / `platform_fingerprint` / `dependency_hashes` / `locale-timezone` / `env_whitelist` / `fixtures_sha256`，且与 `seal.json` 一致 | 可 | 全在位 → `PASS` |
| **X-7.3b 隔离安全** | 容器/VM 边界证明 | 不可（须 L2） | L2 → `PASS`；L1 → **`CONDITIONAL`**；L0 → `FAIL` |
| **X-7.3c 非确定性** | L0 判级器自身同输入 3 次逐字节相同；L1 命令 3 次比对（须注明未隔离） | L0 / L1 可 | `UNMEASURED` **不得**当 ≤0.05 |

**M1 状态映射**：`a=PASS ∧ b=CONDITIONAL ∧ c≤0.05` → `PROVISIONAL-L1`（可用，须披露安全边界未隔离）；`b=FAIL` → 维持 `PROVISIONAL`；`UNMEASURED` 不得升级。本环境当前为 **`E-0` 能力矩阵的 L0**（裸机、无隔离、无环境清单），本卡全部动作落在 L0 允许列（文本勘误、只读扫描、机械 lint、纯追加冻结）内。

**L2 挂账理由（sir 已拍板，dp）**：L2 只解锁 `X-7.3b` 与恶意命令安全，而当前所有结论均已被 `independence_satisfied = false` 降级为方向诊断；在方向诊断精度下为不改变任何读数符号的安全属性付容器成本，收益不成立。本卡不得引入任何容器/VM 依赖，`env_manifest.py` / `nondeterminism_probe.py` / `x73_gate.py` 属 P1/P2，均未实现。轮十五的 `replay_guard.py` 读数与 `PROVISIONAL` 状态**未回改、未重跑**。

**如实登记的风险（卡面 review Q4 / Q6）**：把「安全边界缺失」从阻断项降为披露项，确实存在被后续轮次悄悄当作「已满足」的风险；§23 `D23-C` 已冻结「`CONDITIONAL` 是披露项，永远不是已满足的门」以对抗。若本环境永远没有 L2，`X-7.3b` 将永久停在 `CONDITIONAL`，`PROVISIONAL-L1` 可能成为事实终态——即拆分在效果上接近把「永久 FAIL」改名为「永久 CONDITIONAL」。**本卡不裁定该风险是否可接受**，交浮香裁定；执行者立场是：拆分澄清了 PROVISIONAL 的真实成因（安全边界，而非数值不可信），但**不解锁任何新读数**。

---

## §6 审计连续性与执行者披露

1. **原文零改写**：D3 由仓外脚本 `D:/15812/projects/round16-custody/_apply_r15_erratum.py` 逐行复制原文、只在 5 个锚点后插入新行；脚本内断言「剥离插入行后逐行等于原文」，并已通过。`git diff --numstat` 删除列 0。
2. **行内标记 4 处**（V6 要求 ≥2）：§0 第 1 条后（第 1 条）、§3.4 表后（第 1 条）、§3.4 review Q3 段后（第 2 条）、§0-E 勘误表说明段中的标记模板；其中 3 处为冻结形式 `【勘误 2026-11-13：见 §0 勘误表第 N 条】`。
3. **Markdown 渲染取舍（如实登记）**：为保持「原句逐字保留、零改写」，行内标记以独立行插在有序列表项之间，会打断 Markdown 有序列表的连续渲染（不影响任何数值、条款或验收项），且 §0-E 勘误区编号与原 `## §0` 并存、标记内「§0」按卡面字面指代置顶勘误区。这是「审计连续性优先于渲染美观」的取舍，是否调整交浮香裁定；执行者不擅自挪动原文。
4. **`.gitignore` 追加 `run-r16/`（非 Owned 文件）**：沿用轮十四/轮十五先例，seal 产物目录不入库；该改动在 `artifacts.json` 台账与递评单中照实披露，交评审裁定。
5. **勘误不覆盖 verdict（卡面 review Q3 / Q5）**：本卡把 `docs/eval-report-r15-truth.md` 列入 Owned files 与 artifacts，只登记**文本勘误**，不写 verdict、不回改轮十五 verdict 的结论、不使用 `superseded by later verdict` 语义改写任何已冻结读数。若后续有人只读轮十五 verdict 与报告可能得到「无瑕疵」印象，这一风险交浮香裁定是否需要回写 verdict notes（那需要浮香重签）；本卡不越权。
6. **零新数据**：未产出第二个 `R_main`、第二个 `M_C`、任何新 T\* 行或新判级结果；`out/fp-overall.json` 未改；红区 11 条完整路径零触碰。
7. **工作树中的非本卡外源改动（照实登记，不提交、不回滚）**：全量验收期间（V9b 单测运行时段，mtime `2026-11-13T22:29:13`）工作树出现 `scripts/verdict_gate.ps1` 的未提交改动（`git diff --numstat` = `4 3`，内容为 PowerShell 数组空判断加固）。该文件**不在本卡 Owned files**、**不在红区 11 条路径内**，执行者的任何脚本与工具均未读写它；接卡时工作树干净，故判定为并行会话 / 外部进程产物。处置：提交时精确列出本卡文件、绝不 `git add -A`，**不提交该改动、也不擅自 `git checkout --` 回滚**（避免覆盖他人工作）；提交后工作树仍会显示这一条 `M`。V1（prereg）、V9a（红区 11 条）、V9c（lint）均不含此路径，验收结论不受影响。是否属需并入的其他卡、或应由该会话自行处理，交评审裁定。

---

## §7 Acceptance V1–V10 亲跑台账

> 全部由执行者亲跑，不采纳作者 precheck；真实退出码与日志落在 `out/acceptance-r16.json` / `out/acceptance-r16.log`，并封入 `run-r16/`。

| 验收 | 命令要点 | 退出码 | 结果 |
|---|---|---|---|
| V1 | `git diff 0e06f23 --numstat -- docs/eval-prereg.md` + 前缀双口径 SHA | 0 | `264 0`；工作树 `4c71623a…` / blob LF `19c453c2…` 逐字节一致 |
| V2 | §23 七标记机械可读 | 0 | `True` |
| V3 | `report_lint.py --report … --require-erratum --forbid-label … --require-scope-tag … --forbid-total-discrimination` | 0 | `LINT: PASS`，5 检查全绿、4 处行内标记 |
| V4 | 三项禁词逐字检查 | 0 | `False False False` |
| V5 | `48/48` / `0.415` / `0.9259` / `6.153846` 逐字核 | 0 | `True True True True` |
| V6 | `勘误表` / `【勘误` 计数 / 长度 | 0 | `True 4 16243`（`> 13554`） |
| V7 | §23 `PROVISIONAL-L1` / `CONDITIONAL` / L0–L2 | 0 | `True True True` |
| V8 | `report_lint.py --self-test` | 0 | `SELFTEST: PASS`，5 条构造违规负向用例全部被拒 |
| V9 | 红区 `git diff <base> --stat` / `unittest discover`（设 `COVENANT_BASH_HINT`）/ `lint_cards.py` | 0 | 红区空、单测 OK、lint 0 errors |
| V10 | `git status --porcelain out/` 无 `fp-overall.json` + `d.get('point')` | 0 | `1.0`（原值保留，未被勘误污染） |

**非零项：无。** 与轮十五不同，本卡 Acceptance V1–V10 全为 0；但**执行者不据此宣布验收通过**——本卡是文本勘误轮，验收权在浮香。执行过程中另有两次「命中即停」的预期失败（非卡面验收项、照实登记）：D2 未勘误报告的 lint 负向干跑 `exit 1`（证明工具非空转，属设计内）、以及 `grep -c` 因无删除行返回 1 导致的探查链中断（无匹配即删除列为 0，非执行失败）。

---

## §8 卡面评审问题对照（执行者立场，不裁定）

- **Q1（保留错误原文 vs 原地改对）**：执行者按卡面冻结的连续性要求保留原文 + 勘误表。对「已 PASS 并合入」的报告，撤改不留下审计轨迹风险更高；但**只读正文不读置顶勘误表确实可能误导后来读者**，本卡的缓解手段是把勘误表放在报告最顶部（§0-E，先于原 §0）并加 4 处行内标记。是否足够，交裁定。
- **Q2（词表 lint 能否被绕过）**：能，见 §3 末段；价值是防疏忽与防回归，不是防规避。
- **Q3（后 verdict 覆盖前 verdict）**：本卡不写 verdict，不使用 `superseded by later verdict` 语义；列 Owned files 只为登记文本勘误。是否仍构成 authority 覆盖，交裁定。
- **Q4（PROVISIONAL-L1 是否实质降标准）**：`a` 与 `c` 的实测标准未降，降的只是 `b` 的处置方式（阻断 → 披露）；但「悄悄当作已满足」的风险真实存在，§23 已冻结 `CONDITIONAL 永不等于 PASS`。交裁定。
- **Q5（轮十五 verdict 是否会给「无瑕疵」印象）**：会；是否回写 verdict notes 需要浮香重签，本卡不越权。
- **Q6（永久 CONDITIONAL 是否只是改名）**：有可能，见 §5 末段；本卡不解锁任何新读数，只澄清 PROVISIONAL 的真实成因。

---

*执行者 WB · 本单与本报告均不构成验收通过；等待 Orchestrator 预审 + 浮香（AgnesCode）PASS gate。*
