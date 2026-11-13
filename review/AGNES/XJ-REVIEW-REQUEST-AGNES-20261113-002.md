# 递评单 · XJ-20261113-002（轮十五 外部真值源、门域冻结与 M1 可复算）

> 递评人：WorkBuddy（执行者代号 **WB**）· 2026-11-13
> 评审员：**浮香（AgnesCode）**；Orchestrator 预审
> 仓库：`D:\15812\projects\agent-covenant` · 分支 `feature/xj-20261113-002-round15-truth-source` · 基线 master `a64c982` · 接卡点 `d689de4`
> 状态：**IN_REVIEW**（D1–D6 交付完成；V1–V12 执行者亲跑，**1 项非零退出码照实登记**；**执行者不宣布验收通过**）
> 执行者无评审权、无合并权：不 push / 不 merge / 不写 verdict / 不自评审 / 未碰 master / 红区零触碰

---

## 1. 一句话结论

**本轮不出门结论。** §22 在任何 r15 数据产物之前冻结（`80aaa61`，纯追加 `306/0`，§0–§21 前缀 raw `b1b32c49…` 与 LF `90a84f34…` 双口径逐字节不变），D2–D6 只做实现、机械核对与降级登记。三件核心事实：① **T\* 覆盖缺口真实存在**——`true=118 / false=48 / unjudgeable=234`，`coverage=0.415 < 0.70` → `truth_coverage_gap=true`，234 条 `UNJUDGEABLE` 逐条给理由、未默认判真判假；② **`FP_overall = 1.0`，Wilson 95% `[0.9259, 1.0]`**，分母严格 `Tstar_false = 48`，与层内条件率 `FP[anchor_miss]=20%` 分栏并报、互不外推；③ **X-7.3 三重门未过**（`sandbox=FAIL / env_manifest=FAIL / hash_match=PASS / nondeterminism=UNMEASURED`），V9 **exit 1**，M1 复算值 `+6.153846 pp` 标 **`PROVISIONAL`** 并在报告显式降级，虽落在历史 CI `[1.7, 11.2]` 内也**不作收敛结论、不称复现、不替换历史值 5.8**。`gate_result = not_evaluable`、`gate_conclusion_issued = false`、`capability_gain_claim = false`、`independence_satisfied = false`。

## 2. 交付清单（D1→D6）

| 阶段 | commit | 交付物 | 关键实况 |
|---|---|---|---|
| 接卡 | `0b980b2` | 卡面 Status | OPEN → IN_PROGRESS，代号 WB；接卡时工作树干净、零 r15 产物 |
| D1 | `80aaa61` | `docs/eval-prereg.md` §22 | 冻结早于一切 D2–D6 产物；纯追加 `306/0`；12 组条款 + 6 禁令 + `R15-TRUTH` 机器可读冻结块（含全部阈值、路径候选链、红区清单、门域条款、X-7.3、provenance、ci_align） |
| D2 | `54be340` | `tools/eval/independence_audit.py` | AST 传递闭包硬门；间接 import 合成链自检 PASS；首跑命中失败后「命中即停、先修再往下」修复 `KeyError: 'path'` 与 phantom roots，重跑 exit 0 |
| D3 | `80395b0` | `external_truth.py`、`layer_sensitivity.py`、`fp_overall.py` | 三值 T\*（只依赖标准库、零判级器 import）、δ/σ、Wilson 区间；V6 首跑因冻结分子无引号、正则写死引号 exit 1，修解析后 exit 0 |
| D4 | （D1 冻结内） | §22 四个门域条款 | **只落条款、零 v2 实现**；全仓扫描四个条款 ID 仅见于卡面与 §22 |
| D5 | `0de51ec` | `provenance_check.py`、`replay_guard.py`、`m1_recompute.py`、`ci_align.py` | 三件套 + 三重门 + 同实现重放 + CI 对齐；**V9 exit 1 未刷绿** |
| D6 | 本次收尾 | `docs/eval-report-r15-truth.md`、`run-r15/` seal、`artifacts.json` 台账、卡转 IN_REVIEW、本单 | seal 经只读 `tools/eval/seal_run.py --verify` 复核；产物走 custody 不入 repo |

仓外 custody：`D:/15812/projects/round15-custody`（冻结脚本与锚点）、`D:/15812/projects/round6-custody`（M1 原始语料，只读）。

## 3. 关键读数（全部来自亲跑产物）

| 项 | 读数 | 说明 |
|---|---|---|
| 冻结序 | §22 `80aaa61` 早于 D2–D6 全部产物 | `git diff a64c982 --numstat -- docs/eval-prereg.md` = `306 0` |
| D2 硬门 | 49 模块 / `violations=0` / legacy 14 / `roots_pending=(none)` | 闭包恰为 4 个真值源 root；14 个历史只读调用者列名 + F6 声明 |
| T\* 三值 | `118 / 48 / 234`，`coverage=0.415` | `evidence_surface_unavailable 108` + `no_verifiable_value_position 126` |
| δ | `1.000000`（166/166，排除 234） | ≥0.95 PASS；解释力限制已标注（Q2） |
| σ | `0.035000`（14/400，全在 `goldset_text`） | ≤0.10 PASS；`a` 与 `b` 三值计数并列落盘 |
| FP_overall | `Tstar_false` n=48 / k=48 / `point=1.0` / `[0.9259, 1.0]` | `coverage=0.415` → `truth_coverage_gap=true`；分母 100% `anchor_miss`，禁用的两个分母机械避开 |
| 层内率 | `FP[anchor_miss]=30/150=20.0%` | **仅层内条件率**，登记为 reference，禁止外推 |
| M1 双读数 | 历史 `+5.8 pp`（claim 级，已发表） / 复算 `+6.153846 pp`（claim 级，`PROVISIONAL`） | A `315/390`、B `291/390`；`within_ci=True`，`convergence_claim_issued=false` |
| X-7.3 | `sandbox=FAIL / env_manifest=FAIL / hash_match=PASS(180/180) / nondeterminism=UNMEASURED` | V9 exit 1；`provisional_required=true`、`downgrade_required=true` |
| provenance | `products=180`、`{A:90,B:90}`、三件哈希、`seal 180/180` | custody 由候选链解析；`b-arm` 不在 custody 内 → `provenance_gaps=1` 披露 |

## 4. Acceptance V1–V12 亲跑退出码（不采纳 precheck）

```
V1  0     V2  0     V3  0     V4  0     V5  0     V6  0
V7  0     V8  0     V9  1(*)   V10 0     V11 0     V12 0
(*) V9 为卡面明文允许的降级路径：任一门不满足则 exit 1 且复算值标 PROVISIONAL
```

- **V1**：`306 0`，双口径前缀 SHA 均不变。
- **V2**：`violations=0`；`unauditable_legacy_layers` 14 条列名 + 声明齐全。
- **V3–V6**：见 §3；V6 输出含 `denominator_basis="Tstar_false"`、`point`、`[lower, upper]`、`coverage`、`truth_coverage_gap=true`。
- **V7**：`True True True True`，且四个条款 ID 无任何 `.py` 实现。
- **V8**：`products=180 condition_counts={A:90,B:90}`、三件哈希；`b-arm-enforcement` 仓外副本明示 `in_custody=false`，不冒认。
- **V9**：**exit 1**，逐门给出可执行扫描证据（Windows 11 / CPython 3.13.14 裸机、无容器证明、`pkg-manifest-copy.json` 缺 python 版本/依赖哈希/平台指纹、判级重放未执行故随机性率不可测）。未测量**不**当作 ≤0.05。
- **V10**：`6.153846 ∈ [1.7,11.2]`，`aggregation=claim` 对齐，`replication_wording_used=false`、`replace_historical=false`。
- **V11**：报告含「收敛性重算」并同时并报历史值与复算值 + 各自聚合层级标签，检查输出 `False`。
- **V12**：红区 11 条**完整路径** `git diff a64c982 --stat` 为空；单测设 `COVENANT_BASH_HINT` 后 `Ran 546 tests ... OK`；`lint_cards.py` **0 errors**（评审前 `VERDICT_WITHOUT_REVIEW` 属预期 warning，不伪造 verdict）。终跑设 hint 时为 `PASS (1 warnings)`；封存后复核未设 hint 时为 `PASS (2 warnings)`（多出 `TEST_COUNT_UNVERIFIED`，为 lint 内部 discovery 的既有环境问题），两次均 0 errors，验收口径以设 hint 的终跑为准。
- **交付后追加复跑的非零观察（非卡面验收项）**：D6 提交后额外重跑一次 V12b 同命令出现 `FAILED (failures=1)`（exit 1），该次未保留完整日志、未捕获失败用例名；紧接两次完整日志重跑均 `Ran 546 tests ... OK`（exit 0，日志已封存）。期间无代码/配置改动，判为瞬时抖动而非本卡回归，不改动上表任何卡面退出码，是否列条件项请评审裁定。

开发中另有两次「命中即停、先修再往下」：D2 自检 `KeyError: 'path'` + phantom roots、V6 冻结分子正则引号，均已修复并重跑至 exit 0，未隐藏。

## 5. 未闭合项（照实登记，交浮香裁定）

1. **T\* 覆盖缺口**：234/400 不可判，`coverage=0.415`；FP 区间只描述 48 条可判假行，不能外推全语料。
2. **分母同质化**：`Tstar_false` 48 条全来自 `anchor_miss`；T\* 结构上覆盖不到 `ref_ok` / `repro_fail` / `goldset_text` 层的 claim-证据矛盾，F1 的「被漏掉的低估机制」本轮仍在。
3. **provenance 缺口**：`b-arm-enforcement.json` 不在解析后 custody 内（仓外两处副本已给哈希与 65/65 blocked 读数），是否足以支撑 B 臂执行阻塞证据待裁定。
4. **X-7.3 永久降级**：本环境无沙箱，M1 值只能 `PROVISIONAL`；是否改以「provenance 可追溯性」立项、把数值复现移到带沙箱执行面，待裁定。
5. **独立性**：I-4.3-c=false，无独立人类标注、无异模型族判级；三指标只作方向诊断。
6. **同实现重放**：仓内封存判级包与解盲 key 的任意组合都对不出 F4 的 E 级序列（已逐包机械比对），本轮复算基于 F4 记录计数 + 冻结公式，未在新沙箱中重判；是否要求补一次带沙箱重放待裁定。
7. **门域数值**：`D_full=118` 在 ADV-6 归并后会变，本轮冻结的是规则而非数字；数值变更须另立卡。
8. **交付后单测抖动**：一次非卡面追加复跑 `FAILED (failures=1)`，两次紧接重跑均 OK；首次失败未捕获用例名，无法归因，已照实登记并封存两份重跑日志，待评审裁定是否需列为条件项。

## 6. 卡面评审问题对照（执行者立场，供评审起点）

- **Q1**：不真外部——仍是生成器文本上的规则，把循环从判级器锚点移到逐字比对，未造出外部基准；已在报告 §3.1 正面承认。
- **Q2**：δ=1 不能区分「层标签本来就对」与「T\* 冗余」，判据解释力有限；已在 §3.3 标注 `interpretation_limit`，未把 δ 当有效性证明。
- **Q3**：已披露分母层构成、`unjudgeable_reasons`、分母 `main_level` 分布，并把误判稀释风险写入 `interpretation_limits`；不把 1.0 读成全语料率。
- **Q4**：不能叫独立复算；本轮如实标为同实现重放 / 收敛性重算，且因环境漂移不可排除而 `PROVISIONAL`。
- **Q5**：本环境实际价值是 provenance 可追溯性 + 三重门的可执行否定结论，不是数值复现；已在 §5.2 明写。
- **Q6**：冻结域规则而非数字 118，ADV-6 归并后数值变更另立卡，条款不自相矛盾。

---

*执行者：WB（WorkBuddy，ZCode 桌面会话）· 2026-11-13 · 本单不构成验收通过，等待 Orchestrator 预审 + 浮香 PASS gate。*

---

## 9. Orchestrator 预审（2026-11-13，亲跑复核，不采纳 precheck）

预审者：Jarvis（OpenCode）/ 分支 `feature/xj-20261113-002-round15-truth-source` @ `5235fba`，基线 `a64c982`。本节仅追加，不改执行者任何原文。

### 9.1 独立复现（全部亲跑）

| 项 | 我的实测 | 结论 |
|---|---|---|
| 红区 11 完整路径 `git diff a64c982 --stat` | 空输出 | 零触碰 |
| V2 import 审计 | `violations=0` `roots_pending=0` `audited_modules=49` | 硬门通过 |
| V3 T* 三值 | `true=118 false=48 unjudgeable=234 total=400 coverage=0.415`；`UNJUDGEABLE_REASONS={"evidence_surface_unavailable":108,"no_verifiable_value_position":126}` | 复现 |
| V6 FP_overall | `denominator_basis=Tstar_false n=48 k=48 point=1.0 ci95=[0.9259,1.0]`、`coverage=0.415`、`truth_coverage_gap=True`、`DENOMINATOR_LAYERS={"anchor_miss":48}` | 复现 |
| V7 条款机械可读 | 12 个条款 ID 全部命中 §22；prereg diff `306/0` 纯追加 | 复现 |
| V8 provenance | `products=180` `condition_counts={A:90,B:90}` 三件哈希齐全 | 复现 |
| V9 X-7.3 | `sandbox=FAIL env_manifest=FAIL hash_match=PASS(180/180) nondeterminism=UNMEASURED -> FAIL`、`PROVISIONAL required=True`、`convergence_claim_issued=False`，exit 1 | 如实失败，未刷绿 |
| V10 ci_align | `within_ci=True status=PROVISIONAL -> PASS`、`used=False replace_historical=False` | 复现 |
| V11 措辞合规 | 报告内每处「复现」均在否定语境（「不得表述为复现」「不是复现」） | 合规 |
| 单测 | 设 `COVENANT_BASH_HINT` → `Ran 546 tests OK` | 通过 |
| lint | `LINT: PASS (1 warnings)`（VERDICT_WITHOUT_REVIEW 评审前瞬态） | 通过 |

### 9.2 预审新增发现（三条）

**N1 · T\* × 主轨交叉表显示「负向判别」（新，执行者报告未含此表）**

我对 `out/truth-star.json`（400 条 per-case）与 `out/r11-reliability-rows.json` 做交叉：

| T\* | 主轨判定 | 条数 |
|---|---|---|
| true | E4 | 100 |
| true | E2 | 18 |
| **false** | **E4** | **48** |
| unjudgeable | E0/E1/E2/E4 | 30/30/96/78 |

- `T*=true` 的 E4 率 = 100/118 = **84.7%**
- `T*=false` 的 E4 率 = 48/48 = **100.0%**
- **判别力（E4率差）= −0.1525（负向）**：主轨对「外部可判为假」的样本判 E4 的比率，**高于**对「外部可判为真」的样本

**必须同时说明混杂**：`T*=false` 48 条 100% 来自 `anchor_miss` 层（由构造决定——只有「claim 值 与 证据面 矛盾」的样本才能被外部判假），而 `T*=true` 中的 18 条 E2 集中在 `cwd_probe` 层。因此该 −0.1525 **不能直接作为「判别力」结论**，必须有**分层版本**后才可解释。

**请评审裁定**：报告是否应补这张交叉表 + 分层版本？我倾向「应补」——因为 `FP_overall=1.0` 单独看只说明「假支持率高」，而加上这张表才说明**主轨在可判子集上从未否决过任何一条假 claim，却否决了 18 条真 claim**，这是「断言支撑维度完全缺失」的直接证据，与 §22 的分层设计动机直接对应。

**N2 · provenance gap 可解析（不是证据丢失，是 custody 根写错）**

- 执行者登记 `b-arm-enforcement.json` `in_custody=false`、`provenance_gaps=1`
- 我实测：该文件哈希 `6d11e805b21ff047044b9b58e93308c48e515c0f8e5ab29f33b4fd624b536de0` 与执行者记录**逐字相同**，且现存于两处：
  - `D:\15812\projects\agent-covenant\run-dir\b-arm-enforcement.json`（仓内，被 .gitignore 覆盖）
  - `D:\15812\projects\round4-custody\run-dir\b-arm-enforcement.json`
- 判定：**证据未丢失，只是不在 `round6-custody` 根下**。执行者照实标 gap 是对的（未冒认），但正确的处置应是：在 §22 provenance 候选链里加入 `round4-custody/run-dir/` 与仓内 `run-dir/`，或把该文件复制进 `round6-custody` 并记录来源。
- **请评审裁定**：这是「缺口」还是「路径配置问题」？我倾向后者，且不构成阻断。

**N3 · 一次无日志的单测失败（执行者已披露，我认为必须留痕而非放手）**

- 执行者自述：交付后一次非卡面单测复跑出现 `FAILED (failures=1)`，紧接两次全量重跑 OK，**首次未留完整日志、未抓到失败用例名**
- 我亲跑一次：`Ran 546 tests OK`
- 判定：**无法排除真实间歇性缺陷**。我认同执行者「不猜根因、交评审裁定」的处置（没有编造根因），但建议：
  - 本轮不因此阻断（无证据、且两次复跑绿）
  - **列入下轮强制项**：`python -m unittest -v` 全量日志落盘至 custody，并在 CI 开启 `-v`；若再次出现则按真实缺陷处理
- **请评审裁定**是否同意该处置。

### 9.3 一句总评（预审视角）

本轮把「真值源」从循环依赖中拉出来（外部三值 T\*、δ=1.000、σ=0.035），并且**在 X-7.3 三门不过时如实让 V9 exit 1、把 M1 复算降级为 PROVISIONAL、明写「本轮价值是 provenance 可追溯性 + 可执行否定结论，不是数值复现」**——这是本项目到目前为止最克制的一次交付。N1 是我认为最需要在评审阶段补上的内容；N2/N3 不阻断。
