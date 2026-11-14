# 轮十七报告 · 收缩主张面——层内 evaluable 判决 + X-7.3 非确定性探针（不进门结论）

> 卡：XJ-20261114-003 · 分支 `feature/xj-20261114-003-round17`（worktree `D:\15812\projects\agent-covenant-r17`，基线 master `e744d61`）· 执行者 ZCode（余念安）· §24 冻结 commit `2387c22`（纯追加 183/0，§0–§23 双口径前缀 `7b6a475b…` / `e8ac6b03…` 不变）
> 性质：收束主张面 + 补非确定性测量。**零模型重跑、零重判级、零新 victim 数据**；`gate_result = not_evaluable`、`gate_conclusion_issued = false`、`capability_gain_claim = false`。源数据只读自双 seal 源（`run-r15` 32 文件、`run-r16` 13 文件，`seal_run.py --verify` 均 exit 0）。

## 0. 口径声明（收缩后的主张面，写在一切读数之前）

**本报告的全部主张面只有两个层内读数与三项门读数，没有任何全域判别力主张。** 全域假支持率维持轮十五冻结结论原样：

`FP_overall = not_estimable (truth_coverage_gap, coverage = 0.415 < 0.70)`

T\* 真值覆盖 166/400（true 118 / false 48 / unjudgeable 234），coverage = 0.415 低于 0.70 冻结阈值，任何全域点估计被禁止；234 条 `unjudgeable` 样本的断言支撑判别力**不可评估**，该边界既是读数也是结论范围限制。在 T\* 可判子集上，主轨 E4 判定与 T\* 真值呈负向关联；该关联由层构成解释，不构成总体判别力估计。本轮不使用「证明」类断言：以下一切读数定性为**预注册条件下的层内对照证据**（scope-tag 为强制字段）。

## 1. 冻结序与数据源

§24（v2.5 → v2.6）以纯追加冻结于轮十七任何 D2–D5 产物之前（`git diff master --numstat -- docs/eval-prereg.md` = `183 0`；工作树 raw 前缀 256516 字节 sha `7b6a475b…`、blob LF 前缀 254316 字节 sha `e8ac6b03…` 冻结前后逐字节一致）。源数据：`run-r15/truth-star.json`（T\* 三值 118/48/234）、`run-r15/fp-overall.json`（protected artifact，原值未动）、`run-r15/m1-recompute.json`（M1 读数与状态）、`out/r11-reliability-rows.json`（主轨判定行，sha `2b38e9ab…`）——全部 sha256 在 §24 D24-G 冻结块中登记，消费时逐一核验。

- **结论 C1**：冻结序合法（纯追加、双口径前缀不变、早于一切 r17 产物），双 seal 源验签 exit 0（`run-r15` 32 文件、`run-r16` 13 文件），报告数值与 seal 源一致。 [artifact: docs/eval-prereg.md sha256=cd39e1272de7bfd94227cb8879fa1bce59bd36f240359a4e4a7dd16f76921faf]（docs/eval-prereg.md）cd39e1272de7bfd94227cb8879fa1bce59bd36f240359a4e4a7dd16f76921faf [artifact: ../agent-covenant/run-r15/truth-star.json sha256=3f24ec031b0f1858b87795e9bc1d3b5ec64fb87fb9c278263a5e999072bc4a68]（../agent-covenant/run-r15/truth-star.json）3f24ec031b0f1858b87795e9bc1d3b5ec64fb87fb9c278263a5e999072bc4a68

## 2. 层内读数一：`FP[anchor_miss]`（T\* 可判子集，层内确定事实）

scope-tag: FP_anchor_miss → `FP[anchor_miss]`（post-hoc layer subset, T\* coverage=100%；层内条件率，禁止外推）

| 项 | 值 | 源 |
|---|---|---|
| 层大小 = T\*-false 数 | 48 = 48 | truth-star.json `by_layer.anchor_miss` |
| 主轨判定 | E4 48/48 | r11-reliability-rows.json（anchor_miss 层 main_level 全 E4） |
| 层内读数 | `FP[anchor_miss] = 1.000 (48/48, Wilson 95% [0.9259, 1.0])` | §23 `P-4.5''` 冻结字面逐字沿用，机械复算逐位相等 |

该层定义即「无锚 → 机械通过 → E4」的构造性恒等：48 条 claim 值位引用为非数值 token（如 `Apache-2.0`），主轨锚点正则正确排除后零锚点落入 `judge.py:379-386` 无锚机械通过分支。**层内零否决 48/48 是层内确定事实，不外推**（§23 D-5.1 条款 3a）。与轮十四读数 `FP[anchor_miss] = 30/150 = 20.0%`（R10_ANCHOR 层内率）分母不同、不可互相外推，二者各自带 scope 标签。

- **结论 C2**：`FP[anchor_miss] = 1.000 (48/48, Wilson 95% [0.9259, 1.0])` 层内复现成立（机械复算与冻结字面逐位相等），scope-tag 强制携带。 [artifact: ../agent-covenant/run-r15/fp-overall.json sha256=df8d2d0e7392e93ec134ca3141b6fea7e1deb1cb14f03f1cd0ea851b8e956a3c]（../agent-covenant/run-r15/fp-overall.json）df8d2d0e7392e93ec134ca3141b6fea7e1deb1cb14f03f1cd0ea851b8e956a3c [artifact: ../agent-covenant/out/r11-reliability-rows.json sha256=2b38e9abf5fde4ba9b624311c107ced1498c6d286b601ba8aad8bfe845cd3fe7]（../agent-covenant/out/r11-reliability-rows.json）2b38e9abf5fde4ba9b624311c107ced1498c6d286b601ba8aad8bfe845cd3fe7

## 3. 层内读数二：`FP[cwd_probe]`（零假支持与其代价成对呈现）

scope-tag: FP_anchor_miss 方法族 → `FP[cwd_probe]`（post-hoc layer subset, T\* coverage=100% (all true, zero E4)；层内条件率，禁止外推）

| 项 | 值 | 源 |
|---|---|---|
| 层大小 = T\*-true 数 | 18 = 18 | truth-star.json `by_layer.cwd_probe` |
| 主轨判定 | E2 18/18（**否决率 18/18 = 1.000**） | r11-reliability-rows.json（cwd_probe 层 main_level 全 E2） |
| 层内读数 | `FP[cwd_probe] = 0.000 (0/18, Wilson 95% [0.0, 0.1759])` | §24 D24-A 冻结分母与方法（z = 1.959963984540054，4 位小数） |

**成对呈现条款（缺一即不合规）**：零假支持是**以总否决为代价的读数**——18 条 T\*-true claim 被主轨 100% 否决，该层主轨误差形态是**假否决**（漏报方向），不是假支持。禁止把 `FP[cwd_probe] = 0.000` 单独表述为主轨能力或判别力：它只说明「该层没有出现 E4 形态的假支持」，与 §23 D-5.1 条款 3b「主轨并非全域无判别力：cwd_probe 层否决了 18 条真 claim，其敏感性存在于非断言支撑维度」并列成立。

- **结论 C3**：`FP[cwd_probe] = 0.000 (0/18, Wilson 95% [0.0, 0.1759])` 且否决率 18/18 = 1.000 成对落库；零假支持不得脱离总否决事实单独引用。 [artifact: ../agent-covenant/run-r15/truth-star.json sha256=3f24ec031b0f1858b87795e9bc1d3b5ec64fb87fb9c278263a5e999072bc4a68]（../agent-covenant/run-r15/truth-star.json）3f24ec031b0f1858b87795e9bc1d3b5ec64fb87fb9c278263a5e999072bc4a68 [artifact: ../agent-covenant/run-r15/layer-truth.json sha256=e54fbd7ec4b8b13991e8c99e3ed014b5f4982f5ed65cf260a9108fec716fed91]（../agent-covenant/run-r15/layer-truth.json）e54fbd7ec4b8b13991e8c99e3ed014b5f4982f5ed65cf260a9108fec716fed91

## 4. X-7.3 三门读数表与 M1 状态映射（实测派生，非预设）

| 门 | 本轮读数 | 机械依据 |
|---|---|---|
| **X-7.3a 环境可复现** | **PASS** | `env-manifest.json` verdict `match`（exit 0）：6/6 必填字段齐备（`python_version` / `platform_fingerprint` / `dependency_hashes`（pip freeze 276 项 + 本机共享库 python3.dll / python314.dll / vcruntime140.dll / vcruntime140_1.dll 哈希）/ `locale_timezone` / `env_whitelist` / `fixtures_sha256`）；两份封存判级语料副本被 seal 逐字节覆盖（intersection 2/2 match）；seal 全清单重算一致 |
| **X-7.3b 隔离安全** | **CONDITIONAL（不动，L2 挂账）** | sir 2026-11-14 范围定稿；L2 真沙箱不立项（§23 D23-E 挂账理由延续）。条款间张力照实登记：§23 状态映射写 L0 → FAIL，本轮按 sir 显式范围表维持 `CONDITIONAL`——**CONDITIONAL 是披露项，永远不是已满足的门**，差异交浮香裁定（review Q4） |
| **X-7.3c 非确定性** | **实测：3/3 byte-identical**（观测非确定率 0/3 = 0.0 ≤ 0.05） | `x73-probe-c.json` exit 0：3 条封存 case（`T01-c00` 命令复现路径 / `T01-c01` 零锚机械通过路径 / `T01-c07` 结构弃权路径）× 3 次运行，判级输出规范序列化哈希逐 run 全等；`UNMEASURED` 已被实测值取代 |

**M1 状态映射（按 §23 D23-D 冻结表对实测三元组套用）**：`a = PASS ∧ b = CONDITIONAL ∧ c ≤ 0.05` → **`PROVISIONAL-L1`**（可用，必须披露）。轮十五 M1 读数不变：`+6.153846`（本轮收敛性重算，claim 级，n=390/臂）与历史 `+5.8`（第 9 轮配对差，CI [1.7, 11.2]）双读数并报；轮十五 `failed_gates`（sandbox / env_manifest / nondeterminism）中 `env_manifest` 与 `nondeterminism` 两项由本轮实测读数对应（a = PASS、c = 0.0 ≤ 0.05），`sandbox` 维持不动。

**终态披露（review Q3 正面答案）**：若 L2 永远不落地，`PROVISIONAL-L1` 就是事实终态（永久 CONDITIONAL 的另一个名字），本报告显式登记该风险；且 `PROVISIONAL-L1` 的可信度上限受双重封顶——`independence_satisfied = false`（单 agent 双视图）与 T\* 非独立人类标注（I-4.3-c = false）。升级只把「安全边界缺失」从阻断项降为披露项，不降低 a 与 c 的实测标准。

- **结论 C4**：X-7.3a = PASS（manifest match，exit 0，6/6 字段、封存语料 intersection 2/2）。 [artifact: run-r17/env-manifest.json sha256=f05ca4bdd7dcdf0e30c4d3bee81e83d48cacbbcf7becd8c46e5f080e8aa6d8f1]（run-r17/env-manifest.json）f05ca4bdd7dcdf0e30c4d3bee81e83d48cacbbcf7becd8c46e5f080e8aa6d8f1 [artifact: tools/eval/env_manifest.py sha256=d63d4836bdb3744da5d7a43d5f75bf6110c645e77228a9f98886e1351b4ad363]（tools/eval/env_manifest.py）d63d4836bdb3744da5d7a43d5f75bf6110c645e77228a9f98886e1351b4ad363
- **结论 C5**：X-7.3c = 实测 3/3 byte-identical（exit 0），`UNMEASURED` 状态被实测值取代；观测非确定率 0/3 = 0.0 ≤ 0.05。 [artifact: run-r17/x73-probe-c.json sha256=335c62f732545a6fc691e04f6303f413b4d168bd8c5e0596c7dae3ddade7c7e1]（run-r17/x73-probe-c.json）335c62f732545a6fc691e04f6303f413b4d168bd8c5e0596c7dae3ddade7c7e1 [artifact: tools/eval/x73_probe_c.py sha256=8baa7752e55e4c4d24667ac67e260c2e21ca2547d1d998355bec22c894e9fbfb]（tools/eval/x73_probe_c.py）8baa7752e55e4c4d24667ac67e260c2e21ca2547d1d998355bec22c894e9fbfb
- **结论 C6**：M1 状态映射按 §23 D23-D 冻结表派生为 `PROVISIONAL-L1`（可用，须披露）；轮十五读数 `+6.153846` / `+5.8` 双读数并报不变，`sandbox` 门维持不动。 [artifact: ../agent-covenant/run-r15/m1-recompute.json sha256=c62f2fe13b4377371aa53d7b283f317417344031880688cfd02bfe371e681622]（../agent-covenant/run-r15/m1-recompute.json）c62f2fe13b4377371aa53d7b283f317417344031880688cfd02bfe371e681622

## 5. 探针与 manifest 的实现边界（零新判级数据）

- 探针输入 = 封存判级语料（sha `6d61994c…`）中 3 条 case，判级环境由临时目录逐字节重建（`fixtures_workspace` 内嵌于样本 → hermetic，不依赖演进中的仓库树）；判级对象只做内存内规范序列化取哈希，**不落盘、不入任何读数**——`X-7.3c` 的输出是字节等值判定，不是第二个门计数。判级经由红区 `judge.py` 只读调用（`r13_alignment.py` 先例），源码零改动。
- runs=3 为卡面字面冻结值；「C1 = 至少 5 次」更稳口径作为未闭合项登记（review Q2），本轮不自行加码。
- manifest 的 `fixtures_sha256` 冻结口径 = 本轮实际消费的两份封存语料文件；其字节副本随 `run-r17` seal（确定性二次封存，r12 先例：内容不变、只增列新文件），一致性核对因此非空集（intersection 2/2）。工作树不含 `out/`（gitignored 不随 worktree 复制），语料从规范 checkout 解析，路径口径照实登记。
- 全部规则从 §24 D24-G `R17-LOCAL-EVALUABLE` 块机械读回（`label_mapping.py`/`report_lint.py` 读回先例），代码不携带脱离冻结文本的参数。

- **结论 C7**：探针与 manifest 的实现边界符合 §24 D24-B/C 冻结条款：零新判级数据、红区只读、规则全部读回冻结文本。 [artifact: docs/eval-prereg.md sha256=cd39e1272de7bfd94227cb8879fa1bce59bd36f240359a4e4a7dd16f76921faf]（docs/eval-prereg.md）cd39e1272de7bfd94227cb8879fa1bce59bd36f240359a4e4a7dd16f76921faf

## 6. 纪律执行与未闭合项

纪律：`out/fp-overall.json` 等受保护产物未回改；`immutable_numerals`（`48/48`、`0.415`、`[0.9259, 1.0]`、`+6.153846`、`delta=1.000`、`sigma=0.035`、`118/48/234`）逐字沿用；红区 + `ledger/` + `scripts/verdict_gate.ps1` + `.github/` + `AGENTS.md`（本仓不存在，空集约束）零触碰；不 push、不 merge、不写 verdict；AgnesCode（浮香，盲化）唯一 adjudicator。V1–V8 验收退出码登记于 `out/acceptance-r17.json`。

未闭合项（交浮香裁定）：① X-7.3c 的 3× 口径是否应升为 C1 = 至少 5 次（review Q2）；② `PROVISIONAL-L1` 终态风险与双重封顶披露是否充分（review Q3）；③ §23 L0→FAIL 映射与 sir 范围表「b 维持 CONDITIONAL」的条款张力（review Q4）；④ 探针输入选 hermetic 封存语料而非 `.eval-sealed/pkg-*` 盲化包的取舍。

## 附：产物哈希（生成时实时计算）

| 产物 | sha256 |
|---|---|
| run-r17/x73-probe-c.json | 335c62f732545a6fc691e04f6303f413b4d168bd8c5e0596c7dae3ddade7c7e1 |
| run-r17/env-manifest.json | f05ca4bdd7dcdf0e30c4d3bee81e83d48cacbbcf7becd8c46e5f080e8aa6d8f1 |
| docs/eval-prereg.md（含 §24） | cd39e1272de7bfd94227cb8879fa1bce59bd36f240359a4e4a7dd16f76921faf |
