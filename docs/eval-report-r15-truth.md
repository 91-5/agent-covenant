# 轮十五报告 · 外部真值源、门域冻结与 M1 可复算（XJ-20261113-002）

> 执行者：WorkBuddy（代号 **WB**，ZCode 桌面会话）· 2026-11-13
> 分支 `feature/xj-20261113-002-round15-truth-source` · 基线 master `a64c982` · 接卡点 `d689de4`
> `gate_result = not_evaluable`（R_main 0.62 < 0.80，按 §18 三档表不出门结论）· `gate_conclusion_issued = false` · `capability_gain_claim = false` · `independence_satisfied = false`
> **本轮不出门结论，不宣布验收通过；执行者无评审权、无合并权，不 push / 不 merge / 不写 verdict / 不碰 master。**

---

## §0 置顶防误读声明（先读这一节）

1. **两个假支持读数作用域不同，禁止互相外推。** `FP[anchor_miss] = 30/150 = 20.0%` 是轮十四在 `R10_ANCHOR` 层内测得的**层内条件率**；本轮 `FP_overall = 1.0`（Wilson 95% `[0.9259, 1.0]`）是以 `Tstar_false` 为分母的**总体条件率**。二者不是同一个量，前者不得当作后者，后者也不得被读作「全语料 400 条有 100% 假支持」。
2. **本轮 `truth_coverage_gap = true`。** 400 条中 234 条 `UNJUDGEABLE`，`coverage = 0.415 < 0.70`。所有真假统计只在 166 条可判行上进行；`UNJUDGEABLE` 既未默认判真也未默认判假（禁令 6）。
3. **M1 复算值显式降级为 `PROVISIONAL`。** X-7.3 三重门 `sandbox=FAIL / env_manifest=FAIL / hash_match=PASS`，随机性率**未测量**（无沙箱，判级重放未在裸机执行）。按禁令 5，该值**不得与历史值并列作收敛结论**，不得表述为「复现（replication）」，只能表述为**收敛性重算（convergent recomputation）**，且**不得替换历史已发表值 5.8**。
4. **聚合层级标签必须成对出现**：历史值 5.8 pp = **claim 级、第 9 轮配对差、已发表**；复算值 +6.153846 pp = **claim 级、n=390/臂、本轮收敛性重算、PROVISIONAL**。聚合层级未对齐前不得并列作结论。
5. **独立性仍不成立**：I-4.3-a（import 闭包）与 I-4.3-b（真值源外性）是机械可核查的，I-4.3-c（独立人类标注者 / 异模型族判级）为 false。本轮全部读数只作**方向诊断**，不构成能力增益结论。

---

## §1 交付链与冻结序

| 阶段 | commit | 交付物 | 实况 |
|---|---|---|---|
| 接卡 | `0b980b2` | 卡面 Status | OPEN → IN_PROGRESS，代号 WB；接卡点 `d689de4`，接卡时工作树干净、零 r15 产物 |
| D1 | `80aaa61` | `docs/eval-prereg.md` §22 | **冻结早于一切 D2–D6 产物**；纯追加 `306 0`（删除列 0）；§0–§21 前缀 raw sha `b1b32c49…`、文本 LF sha `90a84f34…` 前后逐字节一致；12 组条款 + 6 禁令 + `R15-TRUTH` 机器可读冻结块 |
| D2 | `54be340` | `tools/eval/independence_audit.py` | AST 传递闭包硬门；合成链 `root → helper → judge` 自检 PASS；V2 首跑命中失败后「命中即停、先修再往下」修复 phantom-roots 与 `KeyError: 'path'`，重跑 exit 0 |
| D3 | `80395b0` | `external_truth.py` / `layer_sensitivity.py` / `fp_overall.py` | 三值 T\*、δ、σ、FP 区间；V6 首跑因冻结分子 `main_level == E4` 无引号、正则写死引号而 exit 1，修解析后重跑 exit 0 |
| D4 | （D1 冻结内） | §22 `G-5.2 / V-5.5 / T-5.3 / P-5.4` | **只落条款、零 v2 实现**；V7 `True True True True`；四个条款 ID 全仓仅出现在卡面与 §22，无 `.py` |
| D5 | `0de51ec` | `provenance_check.py` / `replay_guard.py` / `m1_recompute.py` / `ci_align.py` | 三件套 + 三重门 + 复算 + CI 对齐；V9 **exit 1 照实登记** |
| D6 | 本次收尾 | 本报告、`run-r15/` seal、`artifacts.json` 台账、卡转 `IN_REVIEW`、递评单 | seal 经只读 `tools/eval/seal_run.py --verify` 复核 |

**冻结序机械证明**：`80aaa61`（D1）为 `54be340`（D2）的直接祖先，后者的所有 D2 文件与 `out/` 产物均在冻结之后产生；V1 的 `git diff a64c982 --numstat -- docs/eval-prereg.md` 删除列为 0，§0–§21 前缀两种口径 SHA 均未变。

---

## §2 D2 · import 闭包硬门（禁令 4 / C-4.1）

`python tools/eval/independence_audit.py --scan tools/eval --forbid judge,rubric_v4,independent_judge --out out/independence-audit.json` → **exit 0**。

- `audited_modules = 49`，`violations = 0`，`roots_pending = (none)`；真值源闭包恰为 `external_truth, fp_overall, independence_audit, layer_sensitivity`。
- `external_truth.py` 只依赖标准库；`layer_sensitivity.py` / `fp_overall.py` 只依赖标准库 + `external_truth`。**禁止 import judge / rubric_v4 / independent_judge（含间接）** 以 AST 传递闭包验证，非口头声明。
- `unauditable_legacy_layers = 14`，逐条列名并附 F6 声明：历史只读判级调用者的层生成脚本不在本仓，其历史层标签的独立性**在此不可审计**；全部未修改，红区纪律保持。名单：`attribution-round4.py`、`attribution-round5.py`、`blind.py`、`controls.py`、`dsl_compiler.py`、`gate_metrics.py`、`probe_runner_r12.py`、`r12_reliability.py`、`r13_alignment.py`、`report.py`、`rubric_v3.py`、`rubric_v4.py`、`run.py`、`study_runner.py`。

---

## §3 D3 · 三值 T\* 与假支持率

### 3.1 T\* 的外部事实边界（禁令 4 / review Q1）

`external_truth.py` 只读三样生成器写入的东西：claim 句子（`- [已验证] ` 首行至首个 `。`）、recorded `out=...` / `exit=N`、fixture 内容。它**不读** E 级、锚点、弃权类别，**不 import** 任何判级器。判定顺序按 §22 冻结：证据面不可用 → `unjudgeable`；无可核查值位 → `unjudgeable`；值位 token 逐字出现在证据面 → `true`；否则 → `false`。

必须承认的边界（**review Q1 的正面回答**）：这仍然是「对生成器所写文本的一套规则」，不是独立人类标注。它把循环从「判级器的锚点实现」挪到了「文本逐字比对」，但**没有**制造出外部基准；I-4.3-c 仍为 false。σ 低只证明该规则在两种抽取实现下稳定，不证明外性。

### 3.2 V3 三值计数与覆盖率

`TRUTH_STAR: true=118 false=48 unjudgeable=234 total=400 coverage=0.415000`（exit 0）。

| 值 | 计数 | 说明 |
|---|---|---|
| `true` | 118 | 来自 `cmd_ok` 48 / `cwd_probe` 18 / `dotfile_claim` 17 / `fallback_probe` 17 / `goldset_text` 18 |
| `false` | 48 | **全部来自 `anchor_miss` 层** |
| `unjudgeable` | 234 | `evidence_surface_unavailable` 108（`incomplete` 30 / `no_evidence` 30 / `ref_missing` 48）、`no_verifiable_value_position` 126（`repro_fail` 48 / `ref_ok` 48 / `goldset_text` 30） |

中文数量词与存在性/状态断言（如「复跑退出码为零」「存在独立复核材料」「文件存在」）按冻结 `value_position_scope` **无 ASCII/数字前导值位**，故判 `unjudgeable` 而非猜测真假。这 234 条按禁令 6 从真假统计中排除并披露覆盖率，**一条都没有默认判真或判假**。

### 3.3 δ 与 σ

- **V4 δ**（层真值 vs T\*，仅 T\* 可判行）：`1.000000`，agree `166/166`，排除 `unjudgeable 234`，`min_delta 0.95` → **PASS**。层真值表读自 §21 D21-E 并经 §22 冻结块读回。
  - **review Q2 的正面回答**：δ=1 只说明「层语义」与「机械文本核对」在这 166 条上一致，**不能**区分「层标签本来就对」与「T\* 没用」两条路；δ 高不构成 T\* 独立性的证据。该判据的可区分性有限，本轮据实标注 `interpretation_limit`，不把 δ=1 写成方法有效性的证明。
- **V5 σ**（`anchor_v1` vs `token_v2`，全部 400 条）：`0.035000`，differing `14/400`，`max_sigma 0.10` → **PASS**。14 条分歧全部落在 `goldset_text`：`token_v2` 会枚举出 `v1.7` / `stdout` / `exact_answer` / `JSON` / `command_output` 等末位 token，而 `anchor_v1` 的冻结 `为\s*(…)` 捕获不到，于是 `a=unjudgeable` 而 `b` 得到可判值。两种实现下的三值计数：`a={false:48,true:118,unjudgeable:234}`、`b={false:48,true:132,unjudgeable:220}`。σ 是**实现敏感度**，不是外性证据。

### 3.4 FP_overall 区间（P-4.4' / P-4.5' / 禁令 1）

`python tools/eval/fp_overall.py --truth out/truth-star.json --judgements out/r11-reliability-rows.json --out out/fp-overall.json` → **exit 0**。

| 字段 | 值 |
|---|---|
| `denominator_basis` | **`Tstar_false`**（冻结字面量，逐字校验） |
| 分母 n | 48（全部 `Tstar=false` 行） |
| 分子 k | 48（`main_level == "E4"`，级别从冻结 `numerator` 字符串解析，未在代码写死） |
| `point` | **1.0** |
| Wilson 95% `[lower, upper]` | **`[0.9259, 1.0]`**（z=1.959964） |
| `coverage` | 0.415 |
| `truth_coverage_gap` | **true**（`0.415 < 0.70`） |

- 禁止的两个分母均被机械避开：`full_400`（n=48≠400）与 `excluding_E0_E1`（n=48≠340，实测 E0/E1 行 60）。按判级器输出筛分母等于「按因变量选样」，本轮未采用。
- **禁令 1 逐字遵守**：`FP[anchor_miss] = 30/150 = 0.2` 在 `out/fp-overall.json` 中以 `layer_conditional_fp_reference` 身份登记，附 `scope = 层内条件率` 与 `policy = never_extrapolate_as_overall_false_support_rate`，**从未**用作本工具的点估计，也从未外推为总体率。
- **review Q3 的正面回答**：本轮披露 `denominator_layer_composition = {"anchor_miss": 48}`，即分母 100% 来自单一层。若 T\* 把真 claim 误判为假，分母会膨胀并稀释该率——本轮不能排除这一层，因此**不把 1.0 读成全语料假支持率**；`interpretation_limits` 明确写出该风险，并把 `unjudgeable_reasons`、分母层构成、分母 `main_level` 分布全部落盘供审计。更根本的一点：T\* 只能在「claim 带可核查值位」时判假，所以它**结构上**覆盖不到 `ref_ok` / `repro_fail` / `goldset_text` 等层的矛盾，这正是 F1 所说「存在被漏掉的低估机制」在本轮的实测体现。

---

## §4 D4 · 门域冻结（只落条款，不写实现）

V7 `True True True True`（exit 0）。四个条款 ID 在全仓仅出现于 `.tasks/XJ-20261113-002.md` 与 `docs/eval-prereg.md` §22，`clauses_before_section22 = []`，无任何 `.py` 实现。冻结的是**域规则 D_full** 而非数字 118（`domain_revision_note`：ADV-6 归并后分母数值会变，数值变更须另立卡）——这是 **review Q6** 的正面回答：冻结一个会变的域并不自相矛盾，只要冻结对象是规则而非数字。`G-5.2` 保持「有锚子集永不出 PASS」，`V-5.5` 保持分区判、`T-5.3` 保持结论文本模板、`P-5.4` 保持功效下限；`implementation = clauses_only_no_v2_code`。

---

## §5 D5 · M1 provenance、X-7.3 与双读数

### 5.1 V8 provenance 三件套（exit 0）

卡面 `--custody ../../round6-custody` 在本机不存在；按 §22 冻结的 `custody_candidates` 链解析得 `custody_resolved = D:/15812/projects/round6-custody`，并登记 `custody_candidates_tried` 全链。`products=180`（只数 `*.md`；另有 `T11`–`T20` 共 10 个目录条目单独披露，**不把 190 当产品数**）、`condition_counts={A:90,B:90}`、`run-data.json` 180 条、`key-20261108T122436Z.json` 180 条映射、`seal.json` 的 180/180 产品 sha256 全部命中。

三件哈希：`key-json = 649f6290…`、`seal-hash = e153e3ab…`、`b-arm-enforcement = 6d11e805…`。

**provenance 缺口（照实登记，不冒认）**：`b-arm-enforcement.json` **不在解析后的 custody 内**。冻结 `gap_policy` 要求任何必需件不在 custody 内必须作为 `provenance_gaps` 披露。仓外副本位于 `agent-covenant/run-dir/b-arm-enforcement.json` 与 `round4-custody/run-dir/b-arm-enforcement.json`（`total=65 / blocked=65 / proceed=0`），其哈希已给出以供审计，但**明确标注 `in_custody=false`，不作为 custody provenance 冒认**；`provenance_complete = false`。F6 的方法论要求由可执行扫描（`os.walk` + 逐字节 sha256）满足，而非执行者口头披露。

### 5.2 V9 X-7.3 三重门（**exit 1，非通过**）

```
X-7.3 GATES: sandbox=FAIL env_manifest=FAIL hash_match=PASS nondeterminism=UNMEASURED -> FAIL
HASH_MATCH: 180/180 products matched seal.json
FAILED_GATES: sandbox,env_manifest,nondeterminism
PROVISIONAL: required=True label=PROVISIONAL downgrade_required=True convergence_claim_issued=False
```

- `sandbox=FAIL`：可执行文件系统扫描未找到容器/隔离证明清单；运行环境为 Windows 11 / CPython 3.13.14 裸机，`container` 环境变量为空、`/.dockerenv` 不存在。
- `env_manifest=FAIL`：`pkg-manifest-copy.json` 只有 `package_version / products / product_sha256 / blinding / workspace_rebuild / shell_track`，**缺** python 版本、依赖哈希、平台指纹三项冻结证据；`shadow-r6/primary/*/input-manifest.json` 是 §13 的输入清单，同样不是环境清单。
- `hash_match=PASS`：唯一真实通过的一门，180/180 产品与 `seal.json` 逐字节一致。
- `nondeterminism=UNMEASURED`：无沙箱即不在裸机重跑 900 条证据命令，判级重放的随机性率**不可测量**。**未测量不等于 ≤ 0.05**——填一个 0.0 刷绿正是 F5 警告的失败。输出另附 `input_derivation_determinism`（产品哈希二次重算 mismatch 0）作诊断，并明确标注其作用域**不是**判级重放率、不得替代之。

→ 按禁令 5 与 X-7.3 `downgrade_policy`，复算值标 `PROVISIONAL`、报告显式降级、**不宣称收敛**。**review Q5 的正面回答**：本交付项在本环境的实际价值是 **provenance 可追溯性 + 三重门的可执行否定结论**，而不是数值复现；若要拿到非 PROVISIONAL 读数，需要另立卡在带沙箱的执行面重放。

### 5.3 M1 复算与聚合层级对齐（禁令 2 / 禁令 5 / review Q4）

冻结公式 `(E2+E3)/(E2+E3+E4)` 由代码**解析**而非写死。输入为卡面 Context F4 记录的 Orchestrator 确定性判级计数（`out/m1-level-counts.json`，带 `source` 标注），并与封存语料结构交叉核对：`shadow-r6/alignment-split.json` 每臂 450 claims、180 products、A90/B90。

| 读数 | 值 | 聚合层级 | 状态 |
|---|---|---|---|
| **历史值** | **+5.8 pp**，95% CI `[1.7, 11.2]` | claim 级，第 9 轮配对差（`docs/eval-report-v9.md`），**已发表** | 不替换 |
| **本轮复算值** | **+6.153846 pp**（A `0.807692 = 315/390`，B `0.746154 = 291/390`） | claim 级，n=390/臂，**收敛性重算（convergent recomputation）** | **`PROVISIONAL`，显式降级** |

两个读数**并报**且各自带聚合层级标签；`ci_align.py` 校验 `6.153846 ∈ [1.7, 11.2]`（V10 exit 0），并把 `replication_wording_used = false`、`replace_historical = false`、`convergence_claim_issued = false` 全部落盘。**落在 CI 内只是区间一致性检查，不是复现，也不是收敛结论。**

**review Q4 的正面回答**：`judge.py` 是同一确定性实现，仓内封存判级包与解盲 key 的任意组合都对不出 F4 的 E 级序列（已逐包机械比对），且本环境无沙箱不宜重跑证据命令。因此本轮**没有**伪装成独立复算：工具按冻结公式从 F4 已记录计数重算，报告明确写「同实现重放 / 收敛性重算，不是独立复算，也不是复现」。差异若存在只可能来自环境漂移，而环境漂移恰恰因为 `env_manifest=FAIL` 无法排除——这正是 PROVISIONAL 的理由。

---

## §6 覆盖缺口与未闭合项（全部声明，交浮香裁定）

1. **T\* 覆盖缺口**：234/400 `UNJUDGEABLE`，`coverage=0.415 < 0.70` → `truth_coverage_gap=true`。FP 区间只描述 48 条可判假行。
2. **分母同质化**：`Tstar_false` 48 条全来自 `anchor_miss`；T\* 结构上无法在 `ref_ok` / `repro_fail` / `goldset_text` 等层判假（无 ASCII 值位）。F1 所说「被漏掉的低估机制」本轮仍在。
3. **provenance 缺口**：`b-arm-enforcement.json` 不在解析后 custody 内，仅仓外副本可用。
4. **X-7.3 缺口**：sandbox / env_manifest / 随机性三门未过，M1 值永久 `PROVISIONAL`（本环境）。
5. **独立性缺口**：I-4.3-c = false，无独立人类标注、无异模型族判级；三指标只作方向诊断。
6. **δ 的解释力**：δ=1 不能区分「层标签本来就对」与「T\* 冗余」（review Q2）；σ=0.035 只说明实现稳定（review Q1）。
7. **门域数值**：`D_full=118` 在 ADV-6 归并后会变；本轮冻结的是规则，数值变更须另立卡（review Q6）。
8. **判级重放未执行**：本轮未在裸机重跑 `judge.py` 的 900 条证据命令；`out/m1-level-counts.json` 是记录输入而非本轮新判级结果。

---

## §7 Acceptance V1–V12 亲跑退出码台账

> 全部由执行者亲跑，不采纳作者 precheck；真实退出码与日志落在 `out/acceptance-r15.json` / `out/acceptance-r15.log`，并封入 `run-r15/`。

| 验收 | 命令要点 | 退出码 | 结果 |
|---|---|---|---|
| V1 | `git diff a64c982 --numstat -- docs/eval-prereg.md` + 前缀双口径 SHA | 0 | `306 0`；raw `b1b32c49…` / LF `90a84f34…` 逐字节一致 |
| V2 | `independence_audit.py --scan tools/eval --forbid …` | 0 | 49 模块 / `violations=0` / legacy 14 列名 / `roots_pending=(none)` |
| V3 | `external_truth.py --samples … --out …` | 0 | `118 / 48 / 234`，`coverage=0.415` |
| V4 | `external_truth.py --compare … --min-delta 0.95` | 0 | `δ=1.000000`（166/166） |
| V5 | `layer_sensitivity.py --extractor-a anchor_v1 --extractor-b token_v2 --max-sigma 0.10` | 0 | `σ=0.035000`（14/400） |
| V6 | `fp_overall.py --truth … --judgements … --out …` | 0 | `Tstar_false` / `point=1.0` / `[0.9259,1.0]` / `truth_coverage_gap=true` |
| V7 | §22 四个条款 ID 机械可读检查 | 0 | `True True True True`；零 `.py` 实现 |
| V8 | `provenance_check.py --metric M1 --custody ../../round6-custody --require …` | 0 | `products=180` / `{A:90,B:90}` / 三件哈希 / gap 1 条披露 |
| V9 | `replay_guard.py … --require-sandbox --require-env-manifest --require-hash-match --max-nondeterministic-rate 0.05` | **1** | **卡面允许路径**：三门未过 → `PROVISIONAL` + 报告降级；不刷绿 |
| V10 | `ci_align.py --historical 5.8 --historical-ci 1.7,11.2 --recompute 6.153846 --aggregation claim --require-within-ci` | 0 | `within_ci=True`，措辞与不替换历史值合规 |
| V11 | 本报告表述合规检查 | 0 | `False`（`('复现' in t and '收敛性重算' not in t)`）；双读数 + 聚合层级标签齐备 |
| V12 | 红区 `git diff <base> --stat` / `unittest discover` / `lint_cards.py` | 0 | 红区空、单测 OK（设 `COVENANT_BASH_HINT`）、lint 0 errors |

**卡面 V1–V12 亲跑台账中，非零项只有 V9（exit 1），是卡面明文允许的降级路径，未被改写为通过。** 执行过程中另有两次「命中即停、先修再往下」的失败：D2 自检 `KeyError: 'path'` + phantom roots（已修并重跑 exit 0）、V6 冻结分子正则引号（已修并重跑 exit 0），均照实登记。

**交付后追加复跑的一处非零观察（非卡面验收项，照实登记）**：D6 提交后，执行者为确认封存未漂移，额外重跑了一次 V12b 同一命令，出现 `Ran 546 tests ... FAILED (failures=1)`（exit 1）。该次仅保留了尾部输出，**未捕获失败用例名，故不猜测根因**。紧接两次完整日志重跑均为 `Ran 546 tests ... OK`（exit 0，见 `out/unittest-rerun.log` 与 `out/unittest-final.log`），期间无任何代码或配置改动，判定为瞬时抖动而非本卡回归；是否需列入条件项交浮香裁定。此观察不改动上表任何卡面验收退出码。

---

## §8 卡面评审问题对照（执行者立场）

- **Q1（外性是否真外部）**：否，仍是生成器文本上的规则；已把循环从判级器锚点移到逐字比对，但未造出外部基准，I-4.3-c=false。见 §3.1。
- **Q2（δ 门槛能否区分）**：不能充分区分；δ=1 只证明层语义与机械核对一致，不证明 T\* 独立或非冗余。见 §3.3。
- **Q3（分母膨胀稀释）**：已披露分母层构成 100% `anchor_miss` + `unjudgeable_reasons` + 分母 `main_level` 分布，并把误判风险写入 `interpretation_limits`；本轮不把 1.0 外推为全语料率。见 §3.4。
- **Q4（同实现重放能否叫独立复算）**：不能；本轮按同实现重放 / 收敛性重算如实标注，且因环境漂移不可排除而标 PROVISIONAL。见 §5.3。
- **Q5（沙箱永不满足，交付价值是什么）**：本轮价值是 provenance 可追溯 + 三重门的可执行否定结论，不是数值复现；建议后续以「provenance 可追溯性」而非「数值复现」立项。见 §5.2。
- **Q6（冻结会变的域是否自相矛盾）**：冻结的是域规则 `D_full` 而非数字 118，数值变更另立卡；不矛盾。见 §4。

---

*执行者 WB · 本单与本报告均不构成验收通过；等待 Orchestrator 预审 + 浮香（AgnesCode）PASS gate。*
