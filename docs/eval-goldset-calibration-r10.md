# 轮十 金标准集双盲锚定校准报告（XJ-20261111-001 · D4）

> 依据：`docs/eval-prereg.md` §17 D17-F（冻结文本，2026-11-11 commit `ee7e765`）
> 执行者：WorkBuddy（代号 **WB**）；无评审权、无合并权；不 push / 不 merge / 不写 verdict
> 产物落点：仓内 `goldset/gold_claims.jsonl`（60 行）、本报告；执行产物与标注台账落 `D:\15812\projects\round10-custody\`（不入 repo）

## 1. 定位与纪律边界

本报告只回答一个问题：**主轨判级器与影子判据，各自与「独立于判级结果的标注」符合到什么程度**。

`A_main` / `A_shadow` 是**校准读数**，不是资格门；`A_shadow ≥ A_main − 0.05` 是**方向判据**，按 D17-F 第 4 条仅表示「影子不劣于主轨的方向」，**不作分层硬门、不膨胀为资格门**（样本量噪声 + 多重比较），分层结果只作诊断。本卡的资格门是 D17-D 的双指标门，与本报告读数互不代偿。

**影子轨定位仍为「预筛」非「替代」**。本报告任何读数都不得解释为「影子轨可替代主轨」「判级语义已对齐」或「影子轨通过即等同主轨判级」（D17-G 第 2 条）。主轨 M1 配对差 5.8%［1.7, 11.2］按冻结判据为未检出达到最小效应的差异。

金标准集**分别**校准两轨对各自独立标注的符合度，**不主张两轨读同一个观测面**：主轨标注走 `main_judgement_input` 的 ref 证据面，影子标注走 `record` 的 predicate 观测面。两轨同面由 D5 真数据轮的 `workspace` 对齐（§16 R1）保证，不由金标准集保证。此设计在本节明示，避免把校准集的 `A` 值误读为 surface parity 证据。

## 2. 轮七 `_meta` 完整迁移（D17-F 第 1 条）

D17-F 第 1 条要求轮十版 60 行**全部为锚定三元组、不设 `_meta` 行**，并把既有轮七 `_meta` 内容完整迁移至校准报告与卡面，不丢失、不改写其历史含义。原 `_meta` 行逐字如下（取自 `round10-custody/goldset-legacy-v1.7.jsonl` 第 1 行）：

```json
{"_meta": {"note": "round-7 gold set: 30 hand-designated claim-predicate-verdict triples; designated outcomes authored independently of any judging run (pre-registration discipline, card XJ-20261108-003 D4); covers 13 predicates x pos/neg, 5 claim_types, evaluative bucket, uncompilable, B-arm prefix", "diagnostic_only": false, "gold_version": "v1.7"}}
```

历史含义不改写：该集合为轮七 `XJ-20261108-003` D4 的 30 条手工指定三元组，标注在判级运行之前独立指定，`gold_version = v1.7`，`diagnostic_only = false`。轮十版保留其 30 条 `record` **逐字不变**（`verify-blindness` 的 `legacy_records_verbatim = true` 为机械证据），并新增 30 条。

## 3. 标注规程与机械盲态

标注脚本：`round10-custody/goldset_r10.py`（SHA-256 见 §10）。**该脚本不导入** `judge` / `dsl_compiler` / `gate_metrics` / `predicates_v17` / `shadow_align`，也不执行任何验证命令；`verify-blindness` 以正则逐行核验源码中的实现模块 import，结果 `implementation_imports_found = []`。

两条互斥输入视图（D17-F 第 2 条「双人独立标注」的执行形态）：

| 视图 | 输入 | 不接触 | 实现 |
|---|---|---|---|
| **标注者 A** | `record` / `fixture` / `observation`（预期观测面）/ `main_judgement_input` | `design_intent` | 符号规则引擎：按 §1 的 E0–E4 判定顺序 + 13 个封闭 predicate 语义，用纯 Python 重新推导两个标签 |
| **标注者 B** | `design_intent`（样本设计意图声明） | `observation` / `record` / `fixture` / `main_judgement_input` | 只做类型校验后读出声明值 |

**冻结序（可机械验）**：`annotate` 生成标注并写 manifest → `arbitrate` 才写 `goldset/gold_claims.jsonl` → 之后才跑 `gate_metrics.py --goldset`。`annotate` 对已存在的标注文件**拒绝覆盖**（退出码 3），保证实现比对之后不可能回改标注。

| 时间戳（UTC） | 事件 |
|---|---|
| `2026-11-11T05:57:59.376439+00:00` | 标注 manifest 生成（`annotation_generated_at_utc`） |
| `2026-11-11T05:57:59.631281+00:00` | 仲裁完成，写 60 行金标准集 |
| `2026-11-11T05:58:40.127434+00:00` | `out/goldset-r10.json` 实现产物 mtime |

`annotation_before_implementation = true`，差值约 41 秒；这是「标注不得来自实现输出」的机械证据。

**仲裁规则（冻结）**：A == B 记 `unanimous`；A ≠ B 记 `disagreement = true`，按「规范规则表优先于设计意图」取 A，并逐条登记交评审。最终 60 条分歧数 **0**，`annotation_disagreements = 0`。

## 4. 首次标注作废事件（如实登记，不隐藏）

第一次执行 `annotate` 得到 **44 条分歧，全部为主轨 level 的 A=E2 / B=E4，影子 `shadow_ok` 0 分歧**。根因不是标注语义分歧，而是标注脚本的**程序缺陷**：`symbolic_main()` 在 `main_judgement_input` 顶层读 `ref` / `form`，而这两个字段实际位于其 `evidence` 成员内，导致所有非 E2 条目被误推为 E2。

处置：

- 在**任何实现产物生成之前**（`out/goldset-r10.json` 当时不存在，`void-reason.json` 中 `implementation_output_existed_at_void_time = false`）把首次 4 个标注产物整体移入 `round10-custody/attempt1/` 存档作废，另写 `attempt1/void-reason.json` 登记根因与定性；
- 修正 `symbolic_main()` 为从 `evidence.ref` 读取；
- 重新冻结标注一次，得 0 分歧。

**定性**：这是标注仪器在实现比对之前的作废重标，不是「看过实现输出后改标注洗白」。首次产物完整保留可查，未删除、未修饰。若评审认为作废重标本身应计入「只许一次」约束，本报告不自行裁定，交浮香。

## 5. 标注者独立性与局限（交评审裁定的核心项）

**必须如实说明：D17-F 第 2 条要求的「双人独立标注」在本轮未完全满足。**

- 两个标注视图由**同一执行者 agent WB** 实现，不是两名独立人类标注者；两者靠「互斥输入视图 + 冻结先于实现 + 源码不导入实现模块」机械隔离，**不是靠人的独立性**；
- A 与 B 的标注产物字节完全相同（`annotations_a_sha256 == annotations_b_sha256 == d3c60e0137e…8ebc`），0 分歧。**0 分歧不证明独立性**，在单 agent 双角色下恰恰是独立性不足的表征；本报告不把 0 分歧包装成「双人一致」的证据；
- 与 D2 门值冻结包 `signer_independence_limitation` 同类局限，一并列为交浮香裁定项：**该偏差是否影响 D4 有效性、是否需要独立人类标注者重做，执行者不自行裁定**。

可验的盲态仅限以下四项：① 标注 manifest 早于实现产物；② 标注脚本无实现模块 import；③ 标注脚本不执行验证命令、不读取实现输出（`implementation_output_read = false`）；④ 标注只冻结一次且拒绝覆盖。

## 6. 覆盖矩阵

`out/goldset-r10.json` 的 `coverage_labels` 原样计数（**标签为可重复计数，非唯一条目数**）：

| 维度 | 计数 |
|---|---|
| 13 个封闭 predicate | `exists` 5、`not_exists` 3、`equals` 5、`contains` 3、`matches_regex` 3、`json_path_equals` 3、`line_count_equals` 3、`exit_equals` 7、`exact_answer` 3、`command_exit_code` 4、`command_stdout_contains` 7、`command_stdout_regex` 4、`command_artifact_created` 4 —— **13/13 全覆盖** |
| 5 类预注册 ERROR（场景标签） | `FILE_NOT_FOUND` 6、`CWD_MISMATCH` 2、`PARSE_FAIL` 3、`TIMEOUT` 1、`SILENT_FALLBACK` 2 —— **5/5 全覆盖** |
| 4 个桶 | `evaluative` 3、`uncompilable` 2、`schema_invalid` 2、`not_applicable` 2 |
| A/B 两臂 | `arm:A` 53、`arm:B` 14（含 7 条重复标签，去重后 `arm:B` = 7，与 `arm:A` 53 合计 60） |
| 正 / 负 / 桶 | `positive` 25、`negative` 26、`bucket` 9（合计 60） |
| 主轨 level 分层 | `E1` 1、`E2` 16、`E3` 1、`E4` 42 |
| 来源 | `provenance:round7` 30、`provenance:round10` 30 |

**覆盖口径的三点如实说明**：

1. **标签簿记冗余**：`arm:B` 14 条中有 7 条是「自动 arm 标签 + 额外 `arm:B` 标签」叠加（g28/g29/g30/g46/g47/g59/g60）；`predicate:line_count_equals` 3 条中 g31 有 1 条同类叠加（去重后 2 条）。这是 `coverage_labels` 的标签冗余，**不影响标注值、不影响 `A` 值计算**；本报告不回改已冻结的金标准集来「修好看」。
2. **5 类 ERROR 是标注层面的场景标签，不是运行时分类**：例如 `TIMEOUT` 只有 1 条场景标签，该条验证命令是瞬时 `python -c "pass"`，**并未制造真实超时**；`SILENT_FALLBACK` 场景标签也不等于 `run_goldset()` 运行时产出了该 ERROR 类。运行时 5 类 ERROR 的实测计数在 D5 真数据轮的 `error_breakdown`（V4）中给出，两者不得混算。
3. **E0 不可达**：`run_goldset()` 对每行恒构造 `EvidenceLine`，无法产生 `claim.evidence is None`，故本集合覆盖 E1/E2/E3/E4 但不覆盖 E0。这是冻结实现的边界，不掩饰、不为凑覆盖改实现（D3 已冻结，SHA-256 入册）。

## 7. 反例检出率（D17-F 第 3 条）

D17-F 第 3 条要求每类至少 1 条反例，防止金标准集只能证明「不误报」。本集合含 **26 条反例**（`expect_consistent = false`，即预期 `predicate_ok = False`），覆盖全部 13 个封闭 predicate，其中新增集补上了轮七缺失的 `json_path_equals` 反例（g35/g36）与 `line_count_equals` 反例（g32）。

实现比对结果 `mismatch_details = []`，26 条反例与独立标注**逐条一致（26/26 = 1.0）**。这说明金标准集确实能验证指标「能发现」而不只是「不误报」。9 条桶条目按 D17-F 第 4 条单列、不进分子：`g24 g25 g26 g27 g30 g56 g57 g58 g59`。

## 8. A 值、方向判据与 V6 验收（亲跑，带退出码）

卡面 V6 三条命令在 `D:\15812\projects\agent-covenant` 下由执行者亲跑（PowerShell，未采纳 precheck）：

| # | 命令 | 输出 | 退出码 |
|---|---|---|---|
| V6-1 | `python -X utf8 -c "print(sum(1 for _ in open('goldset/gold_claims.jsonl',encoding='utf-8')))"` | `60` | `0` |
| V6-2 | `python tools\eval\gate_metrics.py --goldset goldset\gold_claims.jsonl --out out\goldset-r10.json` | `wrote out\goldset-r10.json (goldset)` | `0` |
| V6-3 | `python -X utf8 -c "import json; d=json.load(open('out/goldset-r10.json',encoding='utf-8')); print('A_shadow:',d.get('a_shadow'),'\| A_main:',d.get('a_main'),'\| pass:',d.get('direction_pass'))"` | `A_shadow: 1.0 \| A_main: 1.0 \| pass: True` | `0` |

`out/goldset-r10.json` 关键读数：

| 字段 | 值 |
|---|---|
| `goldset_rows` / `triples` | 60 / 60（`_meta` 行 0） |
| `comparable` / `excluded` | 51 / 9 |
| `a_main` / `a_shadow` | 1.0 / 1.0 |
| `direction_pass` / `direction_tolerance` | `True` / 0.05 |
| `direction_is_diagnostic_only` | `True` |
| `annotation_disagreements` | 0 |
| `mismatch_details` | `[]`（0 条） |
| `goldset_sha256` | `fbc059750c164bfb7779daa79045255aa1124935128db5636ece9a4daf7c94e8` |

**A=1.0 的含义与局限**：它表示实现与「按规范独立推导的标注」在这 51 条可比条目上逐条一致，**不等于**主轨语义信度、不等于影子轨可替代主轨、也不等于 §15 的 CQ / surface parity / proposition alignment 达标（D17-B 明确两套集合不互相校准、不重复计分）。Gate 0 的 `R_main = 1.0` 同理是确定性重放同义反复，见 `docs/eval-gate0-main-reliability.md`。

## 9. 失败判据与处置（D17-F 第 5 条）

| 情形 | 处置 |
|---|---|
| `direction_pass = False`（`A_shadow < A_main − 0.05`） | **不构成门不过、不触发整轮作废**；按 D17-F 第 4 条只登记为方向性诊断异常，写入轮十报告四层并列，交浮香裁定 |
| `comparable = 0` 或 `a_main` / `a_shadow` 为 `None` | 校准集失效，V6 FAIL，按卡面「任一 FAIL 不进入门结论讨论」停手登记 |
| 行数 ≠ 60 / 出现 `_meta` 行 / 轮七 30 条 `record` 非逐字保留 | D17-F 第 1 条违规，V6 / `verify-blindness` FAIL，如实登记退出码 |
| 发现任一条标注值来自实现输出回填 | 双盲作废，整轮挂起，**执行者不自行修补** |

本轮实测：行数 60、无 `_meta`、轮七 30 条逐字保留、`comparable = 51`、`direction_pass = True`、`verify-blindness` 的 8 项检查 `all_pass = true`（退出码 0）。**未触发任何失败判据。**

## 10. 哈希锚点与产物台账

| 产物 | 路径 | SHA-256 |
|---|---|---|
| 标注脚本 | `round10-custody/goldset_r10.py` | `8a48e8257d9e6878a86576b3328af0a8005b56d1631086a59c2e6b6b23e18c2d` |
| 轮七快照（含 `_meta`） | `round10-custody/goldset-legacy-v1.7.jsonl` | `a4b2afce5d18464f1ee0e77be7886de2eb365caa90342c132b33d19f3bc1d192` |
| 60 条 spec 快照 | `round10-custody/goldset-spec-r10.json` | `4c9209c8f62becd32e143977a6e8bdc2be8001f872d421ad4bf1cbd1063623c3` |
| 标注 A | `round10-custody/goldset-annotations-a.json` | `d3c60e0137e771af8f3fbfd8f5c6b4055ec5fd05e1536aac695937817e778ebc` |
| 标注 B | `round10-custody/goldset-annotations-b.json` | `d3c60e0137e771af8f3fbfd8f5c6b4055ec5fd05e1536aac695937817e778ebc` |
| 标注 manifest | `round10-custody/goldset-annotation-manifest.json` | 见文件（`generated_at_utc` 见 §3） |
| 仲裁台账 | `round10-custody/goldset-arbitration-r10.json` | 见文件（0 分歧 / 51 可比） |
| 作废存档 | `round10-custody/attempt1/`（5 个文件） | 见 §4 |
| 盲态核验 | `round10-custody/goldset-blindness-verify.json` | `all_pass = true` |
| 金标准集 | `goldset/gold_claims.jsonl` | `fbc059750c164bfb7779daa79045255aa1124935128db5636ece9a4daf7c94e8` |
| 实现读数 | `out/goldset-r10.json` | `adf0496bdc66e88f1ab20790c321f125b1a09ef14bb069d8401e4a38cbc7e353` |

仓外执行产物 `out/` 已被 D0 追加的 `.gitignore` 覆盖，且未 `git add`；`run-dir-r10/` / `shadow-r10/` 截至本报告仍不存在。

## 11. 定位声明（D17-G）

影子轨定位为**「预筛」非「替代」**。本报告 `A_shadow = A_main = 1.0` 与 `direction_pass = True` 只说明在本金标准集的 51 条可比条目上，两轨各自与独立标注一致且影子不劣于主轨；**不得**据此表述为「影子轨可替代主轨」「判级语义已对齐」或「影子轨通过即等同主轨判级」。预筛分支门槛 `min(0.85, R_main − 0.10) = 0.85` 只在预筛语境使用，与资格门 `M_C = 0.95` 分列。R2（命题层级对齐）仍是另一轮，本卡不解决 R2。

## 12. 交浮香裁定项（执行者不自行裁定）

1. **D4 双盲有效性**：单 agent 双角色 + 0 分歧 + A/B 产物同哈希，是否满足 D17-F 第 2 条「双人独立标注」；是否需要独立人类标注者重做。
2. **作废重标**：首次 44 条程序性分歧在实现比对之前作废重标，是否触及「门重设计只许一次」或预注册「只许一次」类条款。
3. **覆盖口径**：5 类 ERROR 仅作标注场景标签（无真实 TIMEOUT）、E0 不可达、`coverage_labels` 两处标签重复，是否满足 D17-F 第 3 条覆盖要求。
4. **A=1.0 的解释边界**：是否接受把校准集读数与 Gate 0 确定性局限、D5 真数据门结论分列而不互相代偿。
5. **报告落点授权**：卡面 Owned files 原清单未列本报告，而 §17 D17-F 第 5 条明文指定 `docs/eval-goldset-calibration-r10.md`；执行者已在卡面 Owned files 机械追记登记该冲突与处置，是否认可由评审裁定。

---

**收尾边界**：本报告不写 verdict、不改门值、不触碰红区、不重判轮六–轮九历史轮次（C12）。D4 到此停手，后续 D5 / D6 / D7 与 V1–V9 全量亲跑另记。
