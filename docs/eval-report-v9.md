# 第九轮报告：R1 影子轨观测面对齐（XJ-20261110-001 / 续作 XJ-20261110-002）

**边界声明**：本报告不含新判定。主轨判级权威 `tools/eval/judge.py`（v1.5 语义零改动），判级取自 `.eval-sealed/pkg-r9-shadow/judgements-blind.json` 原文；影子轨只产结构化记录与布尔一致性旗标，不产出判级。§16（`docs/eval-prereg.md`，commit `123279b`，2026-11-10 12:47:05 +0800）在轮九任何数据产生之前冻结，本报告不改动该节任何文字。措辞纪律全文适用：凡引用本 harness 的结论只可写「**预注册条件下的对照证据**」；未达最小效应时写「**未检出差异**」。

**运行协议**：§12 D4（四项指标口径）+ §13 ④（影子节零判级记号）+ §14（谓词集与哈希冻结）+ §16（R1 观测面对齐、96 条预期消解映射表、冻结序）。B 臂 `not_applicable` 规则按 `docs/b-arm-notapplicable-rules.md`。R3 双版一致率沿用主轨既有锚规则（`extract.py` 锚抽取 + `judge.py` 的 `claim.unanchored`），**不新造判据**。

**数据来源（全部为已封存产物，本报告不重算任何实验）**：

| 面 | 产物 |
|---|---|
| §16 冻结映射表 | `docs/eval-prereg.md` @ `123279b`（96 行） |
| D2 off-line 回放 | `out/replay_r1.json` → custody `round9-custody/replay_r1.json` |
| D3 真数据双臂附卷 | custody `round9-custody/shadow-r9/{alignment-split.json,alignment-split-prer1.json,dual-version-agreement.json,primary/{A,B}/compile-report.json}` |
| 主轨新封装 | `.eval-sealed/pkg-r9-shadow/{claims.json,judgements-blind.json,manifest.json}` |
| 主轨解盲 | custody `round9-custody/unblind-r9.md` |
| 执行者产物 | `run-dir-r9/`（seal 后移交 custody）与今日复跑探针 `re-execution-log-r9.json` |

**观测面两版唯一变量**（custody `shadow-r9/shadow-track.json` 原文）：`r1 = cwd=workspace; artifact workspace-first / root-fallback (§16 D16-1/D16-2)`；`prer1 = cwd=root; artifact root-only (the pre-R1 instrument)`。两版同数据、同记录、同主轨断言面，**唯一变量为观测面**——这是 §4 归因纯净的机械依据。

## 1. 主轨（单列）

新封装 `.eval-sealed/pkg-r9-shadow` 的盲态判级分布（900 条，180 个产物码 × 5 条断言）：

| E1 | E2 | E3 | E4 | 合计 |
|---:|---:|---:|---:|---:|
| 120 | 249 | 258 | 273 | 900 |

对轮七密封判级 `pkg-r7-shadow` 逐条比对，**仅 3 条漂移**：`P097-c05`（E4→E2）、`P136-c05`（E4→E2）、`P157-c05`（E4→E2），成因为 `cmd.exe` 报错语种由中文变英文（`ForEach-Object` 三条 `P0xx-c05`），属环境不可控漂移，如实披露，不作有利解读。

| 指标 | 任务数 | 配对差均值 | 95% CI（bootstrap over 任务） | 达最小效应（≥10pp 且 CI 不跨零） |
|---|---:|---:|---|---|
| M1 | 30 | 5.8% | [1.7%, 11.2%] | 否 |
| M2 | 30 | 0.0% | [0.0%, 0.0%] | 否 |

- M1 / M2：在预注册条件下**未检出达到最小效应的差异**（冻结判据为「配对差 ≥10pp 且 95% CI 不跨零」；M1 点估计 5.8% 未达 10pp、CI 上界 11.2% 略越该值，按冻结判据仍为未检出；M2 恒为 0.0%）。
- M3 负对照未运行（延续既往口径）。
- 本轮沿用执行者产物原样；用 `study_runner` 重新生成产物会把复跑段落按今日观察值改写，主轨判级漂移 84/900，该变体已留档为 `run-dir-r9-preregen-anomaly/` / `pkg-r9-shadow-preregen-anomaly/`，**不作端点**（见 §9）。

## 2. 双版一致率（R3 口径：全量 / 排除无语义锚 E4，同表并列）

两版**同表并列**，缺一即构成选择性报告（卡面 V5）。R3 沿用主轨既有锚规则：`extract.py` 锚抽取 + `judge.py` 的 `claim.unanchored`，本轮不新造判据、不调整排除口径。

| 臂 | 观测面 | 全量 | 排除无语义锚 E4 | 被排除条数 |
|---|---|---|---|---:|
| A | pre-R1（仓库根） | 180/309 = **0.5825** | 168/234 = **0.7179** | 75 |
| A | **post-R1（workspace）** | 129/309 = **0.4175** | 72/234 = **0.3077** | 75 |
| B | pre-R1 | 21/48 = **0.4375** | 12/21 = **0.5714** | 27 |
| B | **post-R1（workspace）** | 21/48 = **0.4375** | 12/21 = **0.5714** | 27 |

- 排除条数：A 臂 75（占可比对的 0.2427）、B 臂 27（占 0.5625）；两版排除集合逐条相同（`dual-version-agreement.json` 的 `excluded_ids`），pre/post 之间零口径漂移。
- 两版一致率**方向一致**（A 臂两版均下降、B 臂两版均不变），不存在「只报好看一版」的空间。
- 排除无语义锚 E4 后的 A 臂 post-R1 一致率 0.3077 低于全量 0.4175——排除了机械通过的主轨条目后，影子轨与有语义锚的断言面错位更明显；该不利数字如实并列，不作口径替换。

## 3. 影子轨四项指标（§12 D4 口径，轮九真数据面；本节零判级记号）

主资格轨 = 独立第三轨编译器的结构化记录附卷（A/B 双臂各 450 条），谓词机械执行沿用 §13 ⑪ 口径。本节按 §13 ④ 自检：正文与表格内**不含任何判级记号**，逐条输出仅 claim_id / 布尔 / 缺口类。

| 臂 | 观测面 | 记录 | 主轨断言 | claim 对齐率 | 可比对 | 判级一致率 | invalid_rate | evaluative 占比 | not_applicable |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|
| A | pre-R1（仓库根） | 450 | 450 | 1.0 | 309 | 180（**0.5825**） | 0.0 | 0.18 | 0 |
| A | **post-R1（workspace）** | 450 | 450 | 1.0 | 309 | 129（**0.4175**） | 0.0 | 0.18 | 0 |
| B | pre-R1 | 450 | 450 | 1.0 | 48 | 21（**0.4375**） | 0.4267 | 0.1933 | 123 |
| B | **post-R1（workspace）** | 450 | 450 | 1.0 | 48 | 21（**0.4375**） | 0.4267 | 0.1933 | 123 |

- **门（四项 ≥95%）：未达标（事实）**。A 臂全量一致率由 0.5825 降至 0.4175；B 臂 0.4375 两版不变。
- **A 臂主轨断言面按记录覆盖的码过滤**：90 个产物码 × 5 = 450 条主轨断言（不是 900）；不过滤会让 claim 对齐率掉成 0.5（陷阱 3，口径错误而非发现）。
- **B 臂 invalid 192 条（0.4267）**：单一错误类为 §12 XOR 规则违反（记录同时携带前缀命令与 `artifact_path`），按 D-00 口径入 invalid 桶、不入一致率分母，如实计数不修复。`not_applicable` 123 条为 B 臂 `command_*` 全量的结构性标记（D6 规则），与轮七口径一致，防口径漂移洗门。
- 两版之间除观测面外零变量：记录数、主轨断言数、对齐率、invalid_rate、evaluative 占比、`not_applicable` 全同，只有判级一致率变化——变化可全部归因于 §16 D16-1 / D16-2。

## 4. R1 翻转分解：+48 / −102（gained 51 / lost 102）

**先给净数字，再给分解，禁止只报下降后的数字**：A 臂全量一致率 pre-R1 **180/309（0.5825）** → post-R1 **129/309（0.4175）**，净 **−51**。对 `alignment-split-prer1.json` 与 `alignment-split.json` 的 `consistent_flags` 逐条做差集：

| 方向 | 条数 | 与 §16 映射集（轮七 72 条）的交集 | 说明 |
|---|---:|---:|---|
| gained（不一致 → 一致） | **51** | **48** | §16 预测消解的全部条目，逐条吻合 |
| lost（一致 → 不一致） | **102** | **0** | 全部落在 §16 映射集之外，即「偶然一致」 |
| 净变化 | **−51** | — | 51 − 102 = −51，与 180−129 一致 |

- 卡面要求的「**+48 / −102**」是 **§16 归因口径**：gained 中可归因于冻结预测的 48 条，lost 中 0 条属 §16 映射集。gained 里另有 **3 条集外条目**（`P046-c02`, `P085-c02`, `P090-c02`，主轨判级均为 E2、谓词均为 `command_exit_code`），**不并入 +48**，如实单列。完整机械分解为 **+51 / −102**。
- **净下降 ≠ R1 让影子轨变差**。R1 把 §16 预测的轮七 72 条逐条兑现：预测消解子集 **48/48** 在 R1 后一致（预测 48），预测不消解子集 **0/24** 一致（预测 0）——轮七子集 **72/72 逐条吻合**（冻结面交叉核验 `pkg-r7-shadow`：177/309 → 126/309，gained 51 / lost 102，分解与真数据面一致；两口径基线各差 3 条（180 vs 177、129 vs 126），与 §1 主轨 3 条漂移数量相同，本报告**不据此作逐条因果归因**，仅并列呈现）。
- **「偶然一致」机制**：pre-R1 时影子判据在**仓库根**执行，相对路径产物不在根下 → 判据静默失败、落「不通过」；这批条目的主轨判级恰好不是支持级（要求影子「不通过」），于是形成**同向的假一致**。换到 workspace 后产物可见 → 判据转「通过」，与主轨不再同向，真实的命题层级错位显形。**pre-R1 的 0.5825 被这 102 条假一致抬高**，不是可引用的基线。
- **worked example**：`P010-c01`，主轨 E3，判据 `command_artifact_created`（expected `revstr.py`，cmd `python revstr.py`）。pre-R1：影子在仓库根执行 → 文件不在根下 → 判据 False → 与主轨 E3 同向 → 假一致；post-R1：workspace 内有 `revstr.py` → 判据 True → 与主轨 E3 不同向 → 真实命题层级错位显形。该条即 lost 102 条之一。
- **lost 102 条的可核验构成**：主轨判级 {'E3': 99, 'E2': 3}；谓词分布 {'command_artifact_created': 42, 'command_stdout_contains': 45, 'command_exit_code': 9, 'command_stdout_regex': 6}。逐条清单见**附录 A**，可对抗核验「−102 条偶然一致」是否成立。
- **不洗白**：`truly_missing` 只计数不转一致；§16 映射表 96 条内 `truly_missing` = 0（轮七 24 条全落在 159 条之外），本轮对其零处理。

## 5. §16 预测—验证闭环（回放与真数据分列）

按 §16 D16-5 条款 4，off-line 回放只估覆盖率，**回放数字不得充当真数据证据**（§14 V4 预测失效的教训 / ADV-4）。两列分别列示：

| 面 | 结果 | 性质 |
|---|---|---|
| §16 冻结预测 | 预期消解 **72/96（75.0%）**、预期不消解 24 条 | 冻结设计，零改动 |
| D2 off-line 回放（`replay_r1.json`） | 与预测逐条一致 **81/96**；轮七子集 **72/72**；轮六子集 **9/24** | 覆盖率报告，非资格证据 |
| 回放实测消解 | **57/96**（预测 72） | 同上 |
| D3 轮九真数据 | A 臂 180/309 → 129/309；分解 +48 / −102（§4） | **唯一一致率证据源** |

- **pre-R1 逐条复现成功**：A 臂 309/309、B 臂 48/48，一致性旗标差 0（`pre_r1_reproduction_verdict = reproduced`）→ 关闭轮八 ADV-1（`replay_r1.py` 已 tracked，换机可独立重放）。
- **15 条偏差全部来自同一处转录缺陷**：D-00 `docs/d00-mismatch-analysis.md` §4.2 表把 15 条轮六条目的「主轨判级」列写成 E4，密封判定实为 **E3**（该表截断了判级 detail，而「命令已复现…」是 E3/E4 共有的 `reproduce()` 前缀）。偏差条目：`P011-c03`、`P025-c03`、`P050-c03`、`P055-c03`、`P060-c03`、`P064-c03`、`P074-c03`、`P080-c03`、`P083-c03`、`P095-c03`、`P098-c03`、`P103-c03`、`P141-c03`、`P159-c03`、`P166-c03`。**登记为 D-00 待查项**：不改写 D-00 文件、不改 §16、不重判历史轮次（C12）；本报告 §6 的对照表把「实测主轨判级」与「§16 预测主轨」并列，让这 15 条逐条可见。
- 回放工作区按 D2 默认重建到仓内 `.eval-sealed/` 下（陷阱 2）：6 条 git 类条目在仓内可见，若改到仓外会让覆盖率读数由 57 变 63，那是保真度 bug 而非发现。

## 6. 96 条逐条对照表（V8；本节承载主轨判级，与 §3 影子指标节分离）

按 §16 映射表**原顺序**逐条列出，共 96 行，无批量汇总代替逐条（卡面 V8）。四列硬要求 `claim_id / 修正前影子判级 / 修正后影子判级 / 主轨判级` 全部具备：

- 「修正前 / 修正后影子判级」= D2 off-line 回放的机械实测（`actual_before` / `actual_after`），**不是预测值**；§16 的冻结预测另列于「§16 预期消解 / 预测主轨」两列，便于逐条对照。
- 「主轨判级（实测）」= 回放逐条 `main_level`；「§16 预测主轨」= 冻结表原列。二者不同的 15 行即 §5 的 D-00 待查项，标 ⚠️，**不就地改写 §16**。
- 「轮九真数据一致性」= D3 `alignment-split-prer1.json` → `alignment-split.json` 的逐条布尔旗标；轮六 24 条样本不在轮九真数据面，标「—」。
- 96 条全为 A 臂；归属 = I2 命令观测面 48 + I3 产物面 24 + 轮六-I2 命令观测面 24；与 I1（12 条）零交集。

| # | claim_id | 归属 | 谓词 | 修正前影子判级 | 修正后影子判级 | 主轨判级（实测） | §16 预测主轨 | §16 预期消解 | 回放实测判定 | 轮九真数据一致性 pre→post | 预测吻合 |
|---:|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `P010-c04` | I2 命令观测面 | `command_exit_code` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 2 | `P010-c07` | I2 命令观测面 | `command_stdout_contains` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 3 | `P025-c04` | I2 命令观测面 | `command_exit_code` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 4 | `P025-c07` | I2 命令观测面 | `command_stdout_contains` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 5 | `P027-c04` | I2 命令观测面 | `command_exit_code` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 6 | `P027-c07` | I2 命令观测面 | `command_stdout_contains` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 7 | `P039-c04` | I2 命令观测面 | `command_exit_code` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 8 | `P052-c02` | I2 命令观测面 | `command_stdout_contains` | 通过 | **通过** | E3 | E3 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 9 | `P052-c05` | I2 命令观测面 | `command_stdout_contains` | 通过 | **通过** | E2 | E2 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 10 | `P053-c04` | I2 命令观测面 | `command_exit_code` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 11 | `P060-c04` | I2 命令观测面 | `command_exit_code` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 12 | `P063-c04` | I2 命令观测面 | `command_exit_code` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 13 | `P063-c07` | I2 命令观测面 | `command_stdout_contains` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 14 | `P065-c01` | I2 命令观测面 | `exit_equals` | 通过 | **通过** | E2 | E2 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 15 | `P065-c03` | I2 命令观测面 | `command_stdout_contains` | 通过 | **通过** | E3 | E3 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 16 | `P065-c04` | I2 命令观测面 | `command_stdout_contains` | 通过 | **通过** | E2 | E2 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 17 | `P065-c06` | I2 命令观测面 | `exit_equals` | 通过 | **通过** | E2 | E2 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 18 | `P067-c04` | I2 命令观测面 | `command_exit_code` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 19 | `P067-c07` | I2 命令观测面 | `command_stdout_contains` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 20 | `P069-c04` | I2 命令观测面 | `command_exit_code` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 21 | `P080-c04` | I2 命令观测面 | `command_exit_code` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 22 | `P080-c07` | I2 命令观测面 | `command_stdout_contains` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 23 | `P082-c04` | I2 命令观测面 | `command_exit_code` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 24 | `P095-c04` | I2 命令观测面 | `command_exit_code` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 25 | `P097-c01` | I2 命令观测面 | `command_stdout_regex` | 通过 | **通过** | E2 | E2 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 26 | `P097-c04` | I2 命令观测面 | `command_stdout_regex` | 通过 | **通过** | E3 | E3 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 27 | `P104-c04` | I2 命令观测面 | `command_exit_code` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 28 | `P110-c07` | I2 命令观测面 | `command_stdout_contains` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 29 | `P122-c07` | I2 命令观测面 | `command_stdout_contains` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 30 | `P126-c01` | I2 命令观测面 | `exit_equals` | 通过 | **通过** | E2 | E2 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 31 | `P126-c03` | I2 命令观测面 | `command_stdout_contains` | 通过 | **通过** | E3 | E3 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 32 | `P126-c04` | I2 命令观测面 | `command_stdout_contains` | 通过 | **通过** | E2 | E2 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 33 | `P126-c06` | I2 命令观测面 | `exit_equals` | 通过 | **通过** | E2 | E2 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 34 | `P135-c02` | I2 命令观测面 | `command_stdout_contains` | 通过 | **通过** | E3 | E3 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 35 | `P135-c05` | I2 命令观测面 | `command_stdout_contains` | 通过 | **通过** | E2 | E2 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 36 | `P136-c01` | I2 命令观测面 | `command_stdout_regex` | 通过 | **通过** | E2 | E2 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 37 | `P136-c04` | I2 命令观测面 | `command_stdout_regex` | 通过 | **通过** | E3 | E3 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 38 | `P138-c07` | I2 命令观测面 | `command_stdout_contains` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 39 | `P150-c04` | I2 命令观测面 | `command_exit_code` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 40 | `P155-c01` | I2 命令观测面 | `exit_equals` | 通过 | **通过** | E2 | E2 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 41 | `P155-c03` | I2 命令观测面 | `command_stdout_contains` | 通过 | **通过** | E3 | E3 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 42 | `P155-c04` | I2 命令观测面 | `command_stdout_contains` | 通过 | **通过** | E2 | E2 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 43 | `P155-c06` | I2 命令观测面 | `exit_equals` | 通过 | **通过** | E2 | E2 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 44 | `P157-c01` | I2 命令观测面 | `command_stdout_regex` | 通过 | **通过** | E2 | E2 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 45 | `P157-c04` | I2 命令观测面 | `command_stdout_regex` | 通过 | **通过** | E3 | E3 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 46 | `P162-c02` | I2 命令观测面 | `command_stdout_contains` | 通过 | **通过** | E3 | E3 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 47 | `P162-c05` | I2 命令观测面 | `command_stdout_contains` | 通过 | **通过** | E2 | E2 | 不消解 | 不消解（仍不一致） | 不一致 → 不一致 | ✅ |
| 48 | `P164-c04` | I2 命令观测面 | `command_exit_code` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 49 | `P010-c05` | I3 产物面 | `command_artifact_created` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 50 | `P025-c05` | I3 产物面 | `command_artifact_created` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 51 | `P027-c05` | I3 产物面 | `command_artifact_created` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 52 | `P035-c08` | I3 产物面 | `contains` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 53 | `P037-c05` | I3 产物面 | `command_artifact_created` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 54 | `P038-c06` | I3 产物面 | `command_artifact_created` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 55 | `P038-c08` | I3 产物面 | `contains` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 56 | `P039-c05` | I3 产物面 | `command_artifact_created` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 57 | `P053-c05` | I3 产物面 | `command_artifact_created` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 58 | `P055-c08` | I3 产物面 | `contains` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 59 | `P057-c06` | I3 产物面 | `command_artifact_created` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 60 | `P057-c08` | I3 产物面 | `contains` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 61 | `P060-c05` | I3 产物面 | `command_artifact_created` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 62 | `P063-c05` | I3 产物面 | `command_artifact_created` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 63 | `P067-c05` | I3 产物面 | `command_artifact_created` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 64 | `P078-c05` | I3 产物面 | `command_artifact_created` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 65 | `P080-c05` | I3 产物面 | `command_artifact_created` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 66 | `P100-c05` | I3 产物面 | `command_artifact_created` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 67 | `P104-c05` | I3 产物面 | `command_artifact_created` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 68 | `P148-c08` | I3 产物面 | `contains` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 69 | `P150-c05` | I3 产物面 | `command_artifact_created` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 70 | `P164-c05` | I3 产物面 | `command_artifact_created` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 71 | `P176-c06` | I3 产物面 | `command_artifact_created` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 72 | `P176-c08` | I3 产物面 | `contains` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | 不一致 → 一致 | ✅ |
| 73 | `P009-c06` | 轮六-I2 命令观测面 | `equals` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | —（轮六样本不在轮九真数据面） | ✅ |
| 74 | `P011-c03` | 轮六-I2 命令观测面 | `exit_equals` | 不通过 | **通过** | E3 | E4 | 消解 | 不消解（一致被破坏） | —（轮六样本不在轮九真数据面） | ⚠️ |
| 75 | `P025-c03` | 轮六-I2 命令观测面 | `exit_equals` | 不通过 | **通过** | E3 | E4 | 消解 | 不消解（一致被破坏） | 一致 → 不一致 | ⚠️ |
| 76 | `P050-c03` | 轮六-I2 命令观测面 | `exit_equals` | 不通过 | **通过** | E3 | E4 | 消解 | 不消解（一致被破坏） | —（轮六样本不在轮九真数据面） | ⚠️ |
| 77 | `P055-c03` | 轮六-I2 命令观测面 | `exit_equals` | 不通过 | **通过** | E3 | E4 | 消解 | 不消解（一致被破坏） | 一致 → 一致 | ⚠️ |
| 78 | `P060-c03` | 轮六-I2 命令观测面 | `exit_equals` | 不通过 | **通过** | E3 | E4 | 消解 | 不消解（一致被破坏） | 一致 → 不一致 | ⚠️ |
| 79 | `P060-c06` | 轮六-I2 命令观测面 | `equals` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | —（轮六样本不在轮九真数据面） | ✅ |
| 80 | `P064-c03` | 轮六-I2 命令观测面 | `exit_equals` | 不通过 | **通过** | E3 | E4 | 消解 | 不消解（一致被破坏） | —（轮六样本不在轮九真数据面） | ⚠️ |
| 81 | `P074-c03` | 轮六-I2 命令观测面 | `exit_equals` | 不通过 | **通过** | E3 | E4 | 消解 | 不消解（一致被破坏） | —（轮六样本不在轮九真数据面） | ⚠️ |
| 82 | `P080-c03` | 轮六-I2 命令观测面 | `exit_equals` | 不通过 | **通过** | E3 | E4 | 消解 | 不消解（一致被破坏） | 一致 → 不一致 | ⚠️ |
| 83 | `P083-c03` | 轮六-I2 命令观测面 | `exit_equals` | 不通过 | **通过** | E3 | E4 | 消解 | 不消解（一致被破坏） | 不一致 → 不一致 | ⚠️ |
| 84 | `P095-c03` | 轮六-I2 命令观测面 | `exit_equals` | 不通过 | **通过** | E3 | E4 | 消解 | 不消解（一致被破坏） | 一致 → 不一致 | ⚠️ |
| 85 | `P095-c06` | 轮六-I2 命令观测面 | `equals` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | —（轮六样本不在轮九真数据面） | ✅ |
| 86 | `P098-c03` | 轮六-I2 命令观测面 | `exit_equals` | 不通过 | **通过** | E3 | E4 | 消解 | 不消解（一致被破坏） | —（轮六样本不在轮九真数据面） | ⚠️ |
| 87 | `P103-c03` | 轮六-I2 命令观测面 | `exit_equals` | 不通过 | **通过** | E3 | E4 | 消解 | 不消解（一致被破坏） | 一致 → 一致 | ⚠️ |
| 88 | `P103-c06` | 轮六-I2 命令观测面 | `equals` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | —（轮六样本不在轮九真数据面） | ✅ |
| 89 | `P125-c06` | 轮六-I2 命令观测面 | `equals` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | —（轮六样本不在轮九真数据面） | ✅ |
| 90 | `P141-c03` | 轮六-I2 命令观测面 | `exit_equals` | 不通过 | **通过** | E3 | E4 | 消解 | 不消解（一致被破坏） | —（轮六样本不在轮九真数据面） | ⚠️ |
| 91 | `P141-c06` | 轮六-I2 命令观测面 | `equals` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | —（轮六样本不在轮九真数据面） | ✅ |
| 92 | `P147-c06` | 轮六-I2 命令观测面 | `equals` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | —（轮六样本不在轮九真数据面） | ✅ |
| 93 | `P159-c03` | 轮六-I2 命令观测面 | `exit_equals` | 不通过 | **通过** | E3 | E4 | 消解 | 不消解（一致被破坏） | —（轮六样本不在轮九真数据面） | ⚠️ |
| 94 | `P159-c06` | 轮六-I2 命令观测面 | `equals` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | —（轮六样本不在轮九真数据面） | ✅ |
| 95 | `P166-c03` | 轮六-I2 命令观测面 | `exit_equals` | 不通过 | **通过** | E3 | E4 | 消解 | 不消解（一致被破坏） | —（轮六样本不在轮九真数据面） | ⚠️ |
| 96 | `P166-c06` | 轮六-I2 命令观测面 | `equals` | 不通过 | **通过** | E4 | E4 | 消解 | 消解（消解） | —（轮六样本不在轮九真数据面） | ✅ |

**表内统计（可由上表逐条点数，不作批量替代）**：✅ 81 行 / ⚠️ 15 行；主轨判级（实测）E4 57 / E3 24 / E2 15；修正前影子判级 不通过 72 / 通过 24；修正后影子判级 96 行全为「通过」（机械观察面结果，**不等于一致**——主轨非支持级要求影子「不通过」时才一致，这正是 §4 lost 102 条的机制）。⚠️ 15 行全部为轮六-I2 条目，其 §16 预测主轨 E4、实测 E3。

## 7. R1 / R2 边界声明

1. **R1 只解决「读同一个面」，不解决「测同一个命题」。** 本轮把影子判据命令的 cwd 对齐到主轨 C10 workspace（D16-1）、把 `artifact_path` 对齐到 workspace 优先 / root 兜底（D16-2）。命题层级对齐是 **R2（另一轮）**，本卡未做。
2. **不得**把本轮结果表述为「影子轨可替代主轨」，也**不得**表述为「影子轨判级语义已对齐」。两轨仍测不同命题：主轨测「断言→证据行→观察」链完整性，影子轨测编译器声明的结构化谓词能否机械通过。
3. **归因纯净**：本轮不改任何 predicate、不改判级顺序、不改 E 级语义、不改指标口径；`predicates_v17.py` 与 `report_agreement.py` 保持 §14 哈希冻结零改动（workspace 优先解析是在 `dsl_compiler.py` 里先解析基准目录再交给冻结谓词模块实现的）。`shadow-track.json` 已固化「两版同数据、同记录，唯一变量为观测面」。
4. **因此净下降的正确读法**：观测面对齐后，掩盖假一致的静默失败消失，102 条真实命题层级错位显形；这是**观测保真度提高**，不是影子轨质量倒退，也不构成任何主判定切换的资格证据。影子门（四项 ≥95%）仍未达标，事实不变。

## 8. D-00 待查项与不洗白

| # | 待查项 | 处置 |
|---|---|---|
| 1 | `docs/d00-mismatch-analysis.md` §4.2 表把 **15 条轮六条目**的主轨判级转录为 E4，密封判定实为 **E3** | 登记为待查项；§6 表把实测与预测主轨并列；**不改写 D-00 文件、不改 §16、不重判历史轮次**（C12） |
| 2 | D-00 台账 I2 族 **24 条**的 `reason` 字段是族级样板文字（统一称「在主轨观测面复现成功、判 E4」），与同条 `main_level`（E2/E3，绝对路径命令 18 + git 命令 6）自相矛盾 | §16 已按逐条 `main_level` / `main_grading_basis` 原文推导，24 条登记为「预期不消解」；本卡不修、不洗白、不转一致 |

- **不洗白红线**：`truly_missing`（工件三面皆不存在）只计数、不得借观测面对齐转成一致；§16 映射表 96 条内 `truly_missing` = 0，轮七 24 条 `truly_missing` 全部落在 159 条之外，本卡对其零处理。结构性错位（S 类，轮七 75 + 轮六 27）与 I1（12 条）同样不在本表内、零状态变化。
- 15 条偏差**没有**被「就地改写 D-00」掩盖：本报告、回放产物、§6 对照表三处均可见 E4/E3 差异。

## 9. 局限性与披露

1. **环境漂移 3/900**：`P097-c05` / `P136-c05` / `P157-c05` 由 E4 漂到 E2，成因为 `cmd.exe` 报错语种中文→英文，不可控；如实披露，不作有利解读。
2. **产物重建异常 84/900**：探索性用 `study_runner` 重新生成轮九产物时，runner 的复跑段落被今日观察值改写，主轨判级漂移 84 条。该变体已留档 `round9-custody/run-dir-r9-preregen-anomaly/` 与 `pkg-r9-shadow-preregen-anomaly/`，**不作端点**；最终沿用执行者产物原样后漂移仅 3 条。
3. **冻结序执行史**：首次探索性回放曾先于真数据运行；最终交付链已按 **freeze → replay → data** 顺序重跑。§16 文本自冻结后零改动，D1 仪器改动亦早于首次真数据。时间戳链与 V1b 口径见 §10。
4. **V1b 口径披露（请评审裁定）**：`run-dir-r9/run-data.json` 的 mtime 为 **2026-11-09 00:02:44**，早于 §16 冻结 commit——因为陷阱 4 / §9 要求**沿用执行者产物原样**，该文件保留历史 mtime。按该字面文件 mtime 判，V1b 的「§16 < replay < run-data < shadow」链不成立；按本轮实际生成的 `run-dir-r9/re-execution-log-r9.json`（13:26:33，目录 mtime 同步）与 custody `shadow-r9/alignment-split.json`（13:31:12）判，四段严格单调递增。两种口径的真实输出均已贴入交付单，本报告不改写卡面验收命令。
5. **证据行两套**：产物内同时有执行者自报段（believed 值）与 runner 复跑段（真实观察值），`extract.py` 两段都抽；理解这一点才不会误判「证据行不一致」。
6. **回放 ≠ 真数据**：off-line 回放只估覆盖率（§16 D16-5 条款 4 / ADV-4）；本报告 §5 与 §2/§3/§4 分列，未以回放数字充当资格证据。
7. **常规局限**（沿附录 D）：草稿来源为 round-4 冻结集重用、单编译者（两臂两会话同模型）、解盲由执行者执行、M3 未运行、B 臂分母受 invalid 192 / `not_applicable` 123 收缩、A 臂可比对 309 ≥ 冻结下限 30 而 B 臂 48 ≥ 30（点估计可报，门适用性按 `docs/b-arm-notapplicable-rules.md` 单独声明）。
8. **本报告只写「预注册条件下的对照证据」**，不构成对任何因果效应或有效性的证明（§0.2 铁律）。

## 10. 冻结序与哈希锚点（机械可验）

| 段 | 对象 | 时间戳 / 哈希 |
|---|---|---|
| ① freeze | §16 commit `123279b` | `2026-11-10 12:47:05 +0800` |
| ② replay | `out/replay_r1.json` | `2026-11-10 13:07:58 +0800` |
| ③ data | `run-dir-r9/re-execution-log-r9.json`（目录 mtime 同步 13:26:33） | `2026-11-10 13:26:33 +0800` |
| ④ shadow | custody `shadow-r9/alignment-split.json` | `2026-11-10 13:31:12 +0800` |

① < ② < ③ < ④ 严格单调递增。③ 的另一种口径（沿用原样的 `run-data.json` = 11-09 00:02:44）见 §9.4 披露。

| 锚点 | 值 |
|---|---|
| `PREREG_FILE_SHA256_AT_FREEZE` | `9f357af9eb17953fb7ed5f8511d1ba728e18400b02869b7e8372dd8fad1549b7` |
| `PREREG_S16_SECTION_SHA256` | `ca02b681c94bf1255baae356e829d44c3268906fe0fd001a078788a622eb2f43` |
| `dsl_compiler.py`（D1 修订后） | `ac553ad28fbe70d82008b5b5e4237c79b65da38ff6c80253691f6e2ca1c56351` |
| `shadow_align.py`（D1 修订后） | `f8c7b82cd278d3c5a251d9f03706b9d2ad6480628fe63eb036151abe84ee0aa6` |
| `replay_r1.py`（D2 tracked） | `b9d351553a986cae39d0b721396f71f5a493bd2a42296d34e872462a1b397c44` |

- §16 小节文本自 `## §16 变更记录` 起至文件末，冻结后**零改动**；本卡未写 §17 追记（须由评审 / Orchestrator 侧做）。
- V4 影子 cwd 机械核验：custody `shadow-r9/primary/{A,B}/compile-report.json` 的 `cwd` 与 `observation_surface.command_cwd` 两臂均为 `.eval-sealed\pkg-r9-shadow\workspace`（**非仓库根**），`artifact_resolution = workspace-first, root-fallback`，`surface_mode = r1-workspace`。
- `artifacts.json` 的 D5 补登记见交付卡，不把未评审的卡自身文件列为 judged artifact。

## 11. 结论

1. **在预注册条件下，R1 观测面对齐的对照证据是逐条兑现冻结预测**：§16 轮七子集 72/72 逐条吻合（48/48 预测消解一致、0/24 预测不消解未误消解）；同时暴露 102 条「偶然一致」，使 A 臂全量一致率由 0.5825 降至 0.4175。**必须连「+48 / −102」分解一起读**；只报下降后的数字，或只报 §16 命中率，都是选择性报告。
2. **双版一致率同表并列、方向一致**：A 臂全量 0.5825 → 0.4175、排除无语义锚 E4 后 0.7179 → 0.3077；B 臂两版 0.4375 / 0.5714 均不变。影子门（四项 ≥95%）**未达标**，事实不变。
3. **主轨**：M1 / M2 在预注册条件下**未检出达到最小效应的差异**；主轨新封装对轮七密封判级仅 3 条环境漂移，已披露。
4. **R1 不等于 R2**：观测面对齐没有解决命题层级错位，影子轨不能替代主轨，也不构成主判定切换的资格证据。R2 另轮。
5. **不洗白 / 不改写**：`truly_missing` 零转一致；D-00 两处缺陷登记为待查项，未就地改写 D-00 或 §16；红区（含 `extract.py`、`predicates_v17.py`、`report_agreement.py`）自 `9cf2d1e` 起零触碰。

## 附录 A：翻转逐条清单（gained 51 / lost 102）

对 §4 的逐条可核验展开（对抗问题「−102 条偶然一致是否成立」）。主轨判级取自 `pkg-r9-shadow/judgements-blind.json`，谓词取自轮七封存 `records-A.jsonl`；「一致性」列 = D3 pre-R1 → post-R1 布尔旗标。

| # | claim_id | 方向 | 主轨判级 | 谓词 | §16 映射集内 | 一致性 pre→post |
|---:|---|---|---|---|---|---|
| 1 | `P010-c04` | gained | E4 | `command_exit_code` | 是 | 不一致 → 一致 |
| 2 | `P010-c05` | gained | E4 | `command_artifact_created` | 是 | 不一致 → 一致 |
| 3 | `P010-c07` | gained | E4 | `command_stdout_contains` | 是 | 不一致 → 一致 |
| 4 | `P025-c04` | gained | E4 | `command_exit_code` | 是 | 不一致 → 一致 |
| 5 | `P025-c05` | gained | E4 | `command_artifact_created` | 是 | 不一致 → 一致 |
| 6 | `P025-c07` | gained | E4 | `command_stdout_contains` | 是 | 不一致 → 一致 |
| 7 | `P027-c04` | gained | E4 | `command_exit_code` | 是 | 不一致 → 一致 |
| 8 | `P027-c05` | gained | E4 | `command_artifact_created` | 是 | 不一致 → 一致 |
| 9 | `P027-c07` | gained | E4 | `command_stdout_contains` | 是 | 不一致 → 一致 |
| 10 | `P035-c08` | gained | E4 | `contains` | 是 | 不一致 → 一致 |
| 11 | `P037-c05` | gained | E4 | `command_artifact_created` | 是 | 不一致 → 一致 |
| 12 | `P038-c06` | gained | E4 | `command_artifact_created` | 是 | 不一致 → 一致 |
| 13 | `P038-c08` | gained | E4 | `contains` | 是 | 不一致 → 一致 |
| 14 | `P039-c04` | gained | E4 | `command_exit_code` | 是 | 不一致 → 一致 |
| 15 | `P039-c05` | gained | E4 | `command_artifact_created` | 是 | 不一致 → 一致 |
| 16 | `P046-c02` | gained | E2 | `command_exit_code` | 否 | 不一致 → 一致 |
| 17 | `P053-c04` | gained | E4 | `command_exit_code` | 是 | 不一致 → 一致 |
| 18 | `P053-c05` | gained | E4 | `command_artifact_created` | 是 | 不一致 → 一致 |
| 19 | `P055-c08` | gained | E4 | `contains` | 是 | 不一致 → 一致 |
| 20 | `P057-c06` | gained | E4 | `command_artifact_created` | 是 | 不一致 → 一致 |
| 21 | `P057-c08` | gained | E4 | `contains` | 是 | 不一致 → 一致 |
| 22 | `P060-c04` | gained | E4 | `command_exit_code` | 是 | 不一致 → 一致 |
| 23 | `P060-c05` | gained | E4 | `command_artifact_created` | 是 | 不一致 → 一致 |
| 24 | `P063-c04` | gained | E4 | `command_exit_code` | 是 | 不一致 → 一致 |
| 25 | `P063-c05` | gained | E4 | `command_artifact_created` | 是 | 不一致 → 一致 |
| 26 | `P063-c07` | gained | E4 | `command_stdout_contains` | 是 | 不一致 → 一致 |
| 27 | `P067-c04` | gained | E4 | `command_exit_code` | 是 | 不一致 → 一致 |
| 28 | `P067-c05` | gained | E4 | `command_artifact_created` | 是 | 不一致 → 一致 |
| 29 | `P067-c07` | gained | E4 | `command_stdout_contains` | 是 | 不一致 → 一致 |
| 30 | `P069-c04` | gained | E4 | `command_exit_code` | 是 | 不一致 → 一致 |
| 31 | `P078-c05` | gained | E4 | `command_artifact_created` | 是 | 不一致 → 一致 |
| 32 | `P080-c04` | gained | E4 | `command_exit_code` | 是 | 不一致 → 一致 |
| 33 | `P080-c05` | gained | E4 | `command_artifact_created` | 是 | 不一致 → 一致 |
| 34 | `P080-c07` | gained | E4 | `command_stdout_contains` | 是 | 不一致 → 一致 |
| 35 | `P082-c04` | gained | E4 | `command_exit_code` | 是 | 不一致 → 一致 |
| 36 | `P085-c02` | gained | E2 | `command_exit_code` | 否 | 不一致 → 一致 |
| 37 | `P090-c02` | gained | E2 | `command_exit_code` | 否 | 不一致 → 一致 |
| 38 | `P095-c04` | gained | E4 | `command_exit_code` | 是 | 不一致 → 一致 |
| 39 | `P100-c05` | gained | E4 | `command_artifact_created` | 是 | 不一致 → 一致 |
| 40 | `P104-c04` | gained | E4 | `command_exit_code` | 是 | 不一致 → 一致 |
| 41 | `P104-c05` | gained | E4 | `command_artifact_created` | 是 | 不一致 → 一致 |
| 42 | `P110-c07` | gained | E4 | `command_stdout_contains` | 是 | 不一致 → 一致 |
| 43 | `P122-c07` | gained | E4 | `command_stdout_contains` | 是 | 不一致 → 一致 |
| 44 | `P138-c07` | gained | E4 | `command_stdout_contains` | 是 | 不一致 → 一致 |
| 45 | `P148-c08` | gained | E4 | `contains` | 是 | 不一致 → 一致 |
| 46 | `P150-c04` | gained | E4 | `command_exit_code` | 是 | 不一致 → 一致 |
| 47 | `P150-c05` | gained | E4 | `command_artifact_created` | 是 | 不一致 → 一致 |
| 48 | `P164-c04` | gained | E4 | `command_exit_code` | 是 | 不一致 → 一致 |
| 49 | `P164-c05` | gained | E4 | `command_artifact_created` | 是 | 不一致 → 一致 |
| 50 | `P176-c06` | gained | E4 | `command_artifact_created` | 是 | 不一致 → 一致 |
| 51 | `P176-c08` | gained | E4 | `contains` | 是 | 不一致 → 一致 |
| 52 | `P010-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 53 | `P010-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 54 | `P025-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 55 | `P025-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 56 | `P027-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 57 | `P027-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 58 | `P032-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 59 | `P032-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 60 | `P032-c04` | lost | E3 | `command_exit_code` | 否 | 一致 → 不一致 |
| 61 | `P032-c05` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 62 | `P032-c07` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 63 | `P035-c01` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 64 | `P035-c02` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 65 | `P035-c05` | lost | E2 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 66 | `P035-c06` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 67 | `P037-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 68 | `P037-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 69 | `P037-c04` | lost | E3 | `command_exit_code` | 否 | 一致 → 不一致 |
| 70 | `P037-c07` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 71 | `P038-c02` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 72 | `P038-c03` | lost | E3 | `command_stdout_regex` | 否 | 一致 → 不一致 |
| 73 | `P038-c07` | lost | E3 | `command_stdout_regex` | 否 | 一致 → 不一致 |
| 74 | `P039-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 75 | `P039-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 76 | `P039-c07` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 77 | `P053-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 78 | `P053-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 79 | `P053-c07` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 80 | `P055-c01` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 81 | `P055-c02` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 82 | `P055-c05` | lost | E2 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 83 | `P055-c06` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 84 | `P057-c02` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 85 | `P057-c03` | lost | E3 | `command_stdout_regex` | 否 | 一致 → 不一致 |
| 86 | `P057-c07` | lost | E3 | `command_stdout_regex` | 否 | 一致 → 不一致 |
| 87 | `P060-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 88 | `P060-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 89 | `P060-c07` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 90 | `P063-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 91 | `P063-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 92 | `P067-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 93 | `P067-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 94 | `P069-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 95 | `P069-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 96 | `P069-c05` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 97 | `P069-c07` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 98 | `P072-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 99 | `P072-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 100 | `P072-c04` | lost | E3 | `command_exit_code` | 否 | 一致 → 不一致 |
| 101 | `P072-c05` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 102 | `P072-c07` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 103 | `P078-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 104 | `P078-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 105 | `P078-c04` | lost | E3 | `command_exit_code` | 否 | 一致 → 不一致 |
| 106 | `P078-c07` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 107 | `P080-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 108 | `P080-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 109 | `P082-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 110 | `P082-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 111 | `P082-c05` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 112 | `P082-c07` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 113 | `P095-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 114 | `P095-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 115 | `P095-c05` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 116 | `P095-c07` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 117 | `P100-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 118 | `P100-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 119 | `P100-c04` | lost | E3 | `command_exit_code` | 否 | 一致 → 不一致 |
| 120 | `P100-c07` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 121 | `P104-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 122 | `P104-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 123 | `P104-c07` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 124 | `P110-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 125 | `P110-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 126 | `P110-c04` | lost | E3 | `command_exit_code` | 否 | 一致 → 不一致 |
| 127 | `P110-c05` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 128 | `P122-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 129 | `P122-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 130 | `P122-c04` | lost | E3 | `command_exit_code` | 否 | 一致 → 不一致 |
| 131 | `P122-c05` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 132 | `P138-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 133 | `P138-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 134 | `P138-c04` | lost | E3 | `command_exit_code` | 否 | 一致 → 不一致 |
| 135 | `P138-c05` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 136 | `P148-c01` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 137 | `P148-c02` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 138 | `P148-c05` | lost | E2 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 139 | `P148-c06` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 140 | `P150-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 141 | `P150-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 142 | `P150-c07` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 143 | `P154-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 144 | `P154-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 145 | `P154-c04` | lost | E3 | `command_exit_code` | 否 | 一致 → 不一致 |
| 146 | `P154-c05` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 147 | `P154-c07` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 148 | `P164-c01` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 149 | `P164-c03` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 150 | `P164-c07` | lost | E3 | `command_stdout_contains` | 否 | 一致 → 不一致 |
| 151 | `P176-c02` | lost | E3 | `command_artifact_created` | 否 | 一致 → 不一致 |
| 152 | `P176-c03` | lost | E3 | `command_stdout_regex` | 否 | 一致 → 不一致 |
| 153 | `P176-c07` | lost | E3 | `command_stdout_regex` | 否 | 一致 → 不一致 |

---

*本报告由续作卡 XJ-20261110-002 的 D4 产出；写入权仅 `docs/eval-report-v9.md` 与 `artifacts.json`。数据全部来自已封存产物，未重算实验。评审正本由浮香（AgnesCode）写入评审目录，执行者不写 verdict。*
