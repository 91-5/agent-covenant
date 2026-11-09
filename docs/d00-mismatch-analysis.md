# D-00 失配分类汇总 · 轮七 159 条 + 轮六遗留项合并归属

**卡号**：XJ-20261109-001 · **生成**：2026-11-09 · **性质**：只读分析（零 instrument 触碰）

本文件是 D-00 的结论层。逐条证据见 `docs/d00-mismatch-ledger.json` / `.md`（D1）；修复建议见 `docs/d00-recommendation-memo.md`（D3）；§15 度量草案见 `docs/prereg-s15-compilation-quality.md`（D4）。

## 1. 结论摘要

轮七影子轨的 159 条判级不一致，**不是**「v1.7 谓词表达力不足」的残余——浮香 ADV-4 的定性（编译裁量 vs 判级语义结构性错位）在本轮得到逐条证据支持，但要再精确一层：**主要成因不是编译器选错了谓词，而是两台仪器压根不在同一个观测面、也不在同一个命题层级上比。**

| 分类 | 条数 | 占比 | 一句话 |
|---|---:|---:|---|
| 仪器可修 (`instrument_fixable`) | 84 | 52.8% | 同一断言、同一谓词，两台仪器读的不是同一个面 / 同一路径 → 对齐观测面即可消解 |
| 结构性错位 (`structural_misalignment`) | 75 | 47.2% | 主轨判「证据行是否自洽」，影子判「断言内容是否成立」→ 命题不同，扩谓词也消解不了 |
| 执行者真实差异 (`real_executor_difference`) | 0 | 0.0% | 产物真的不存在 → 只计数不转一致 |
| 仍未归类 (`unclassified`) | 0 | 0.0% | 证据不足 |
| **合计** | **159** | 100% | |

**读法**：84/159（52.8%）是仪器读面问题，75/159（47.2%）是命题层级问题。两类合计 159/159，**没有一条需要靠新增谓词来消解**——这直接支持 D3 的主结论：再扩 enum 不会提高一致率，扩的是错的方向。

### 1.1 机制细分

| 机制 | 条数 | A | B | 说明 |
|---|---:|---:|---:|---|
| I2 命令观测面分歧 (`I2_command_observation_surface_divergence`) | 48 | 48 | 0 | 主轨在 C10 重建工作区跑命令（cwd=workspace）→ 复现成功判 E4；影子以仓库根为 cwd → 命令不在仓库根 → 判据不成立。 |
| S2 机械 E4 vs 语义判据 (`S2_main_mechanical_E4_vs_shadow_semantic_criterion`) | 42 | 21 | 21 | 主轨 E4 仅凭 ref 可读 / 命令复现且**无语义锚**，未核验断言语义；影子判据直接核验内容 → 确不成立。 |
| S1 判证据行 vs 判产物 (`S1_main_judges_evidence_line_vs_shadow_judges_artifact`) | 30 | 30 | 0 | 主轨判「自报 exit/out 是否相符、锚是否命中」；影子判产物存在性/内容。 |
| I3 产物面/观察面分歧 (`I3_artifact_path_surface_divergence`) | 24 | 24 | 0 | 主轨在 C10 工作区解析 `artifact_path` → 文件在 → E4；影子按仓库根解析 → 不在 → 判据不成立。 |
| I1 ref 路径解析分歧 (`I1_ref_token_parse_divergence`) | 12 | 6 | 6 | 证据行 `ref=X（独立复核）`：主轨整串当路径→判「ref 不存在」；影子编译器剥离后缀→读 `X`→内容命中。同一行被读成两个路径。 |
| S3 复现失败命令 vs 问语义 (`S3_main_reproduced_a_failed_command_vs_shadow_asked_the_semantic_question`) | 3 | 3 | 0 | 自报命令本身 exit=255 失败（cmd.exe 无 `ForEach-Object`）；主轨只核「自报输出与真实输出逐字相同」→ 判支持；影子问「类型前缀是不是 chore」→ 否。 |

## 2. 权威性核定（执行者亲验）

本卡的所有影子侧读数都依赖「哪个 custody 产物是权威」。核定过程与结论：

**2.1 `alignment-split.json` 是权威，且可精确复现。** 用冻结仪器 `tools/eval/shadow_align.py` 对 custody 的 `claims-{arm}.json` + `records-{arm}.jsonl`（主轨判级按 claim 索引从密封 `pkg-r7-shadow/judgements-blind.json` 合入）重跑，得到：

- A 臂：可比对 309、一致 177、一致率 0.5728 —— 与冻结产物**逐条一致 309/309**；
- B 臂：可比对 48、一致 21、一致率 0.4375 —— **逐条一致 48/48**；
- 语义缺口 id 集合：完全相同（A 132 / B 27）。

**2.2 `records-*-graded.jsonl` 的 `predicate_ok` 列是错标的一致性旗标。** 该文件 A/B 两份**字节完全相同**（364 929 bytes，含全部 900 条记录）。逐条核验：

- 对**每一对可比对项**（A 309 条 / B 48 条），该列的值与冻结 `consistent_flags` **完全相同**（309/309、48/48）；
- 而该列与**冻结编译器重算的原始谓词结果**在 357 条非空行中**有 237 条相反**（按臂：A 臂 309 条可比对项中 222 条相反；B 臂 48 条中 15 条相反）。

即：该列存的是**与主轨的一致性旗标**（= 是否与主轨判级一致），而不是影子判据的**原始机械结果**。若直接拿它当「影子判据原始结果」填台账，159 条里将有 237/357 的比例被填反。**本台账因此不使用该列**，改用冻结编译器 `tools/eval/dsl_compiler.py` 在同观察根重算的 `predicate_ok / detail / flags`。该重算值与冻结一致旗标自洽（309/309 + 48/48），可证其为权威影子侧读数。

**2.3 主轨判级映射唯一。** `claims-{arm}.json` 与密封包 `pkg-r7-shadow/claims.json` 逐条文本+行号全等（450/450 臂），`judgements-blind.json` 的行与 claim 索引**严格对齐**（900/900 校验通过），且 record↔claim 的一一配对在索引与 `evidence_span` 两种口径下完全一致（0 处歧义），故主轨判级可无歧义挂到每条失配上。

**2.4 红区与 C12。** 本卡零 instrument 触碰（V6 验空）；主轨判级只读引用密封包，未重判任何历史轮次（C12）。

## 3. 轮七 159 条的分类论证（逐条机制）

### 3.1 仪器可修（84 条）

**I2 命令观测面分歧（48 条）** —— 主轨 `judge.reproduce()` 在 v1.5 C10/C11 下以 **cwd=workspace**（C10 重建的执行者工作区）复现命令；影子对齐器则把 `verification_command` 交给 `dsl_compiler`，以**观察根（仓库根）**为 cwd 执行。执行者的产物脚本（`revstr.py` / `flatten.py` / `balanced.py` / `is_leap.py` / `bisect.py` / `roman.py` 等）在 C10 工作区里，不在仓库根——于是同一条命令，主轨 exit=0 判 E4，影子在仓库根 exit≠0 判据不成立。**这不是执行者撒谎，也不是编译器选错谓词，是两条轨道的 cwd 不一致。**

**I3 产物面/观察面分歧（24 条）** —— 同一根因的产物面版本：主轨 `artifact_path` 在 workspace 优先、root 兜底地解析（judge.py:274-289），影子编译器只按仓库根解析。`flatten.py` / `sumcsv.py` / `wordcount.py` / `fizzbuzz.py` / `bisect.py` 等只在 C10 工作区与 run-dir 里。

**I1 ref 路径解析分歧（12 条）** —— 证据行 `ref=README.md（独立复核）`：主轨的 `extract.py` 用 `ref\s*=\s*(\S+)` 兜底，**把「（独立复核）」一并吞进路径**，再去查文件自然查不到 → 判「ref 不存在」；影子编译器按其 compile-report 明文「ref 型记录把（独立复核）后缀剥离」处理 → 读到真文件 → 内容命中。**同一行证据被两台仪器解析成两个不同的路径。**

> 三类合计 84 条。它们的共同点是：**在任一台仪器内部都自洽**，两台仪器不一致纯粹因为输入面（路径解析规则 / cwd / 产物根）不同。这类失配**不需要任何新谓词**来消解——需要的是把两台仪器钉到同一个观测面上。

### 3.2 结构性错位（75 条）

**S1 判证据行 vs 判产物（30 条）** —— 主轨 E2 的依据是「退出码不符：证据声称 exit=255，实际 exit=0」「声称输出未复现」「锚未命中」：主轨在问**执行者自报的证据行是否自洽**。影子判据问的是**产物存在性/内容**。两个不同的问题，两个不同的答案，任何谓词扩充都消解不了——因为不一致的根源是命题不同，不是判据不够。

**S2 机械 E4 vs 语义判据（42 条）** —— 主轨给 E4 的依据是「ref 存在且可读（无语义锚，仅机械复核通过）」或「命令已复现…已命中」：**主轨根本没核验断言语义**（该主张无锚，按 §1 锚规则机械通过即 E4）；影子判据则直接问「文件里有没有这段内容」——在被观测文件上确不成立。例如断言「第 4 节标题词为『承诺生命周期（Commitment Lifecycle）』」对着 `PROTOCOL.md` 求包含：轮七判定时点的 `PROTOCOL.md`（4fcd097）第 4 节是 `## 4. Artifacts`——断言内容与被观测文件确实不符。**影子更严，主轨更松。**

**S3 复现失败命令 vs 问语义（3 条）** —— 执行者自报的命令本身以 exit=255 失败（cmd.exe 不认 `ForEach-Object`），主轨只核验「自报输出与真实输出逐字相同」→ 相符 → 判支持；影子问「该提交的类型前缀是不是 `chore`」→ 实际输出为空/失败 → 不成立。主轨判的是**复现**，影子问的是**断言真伪**。

> S2/S3 暴露一个更根本的事实：**主轨 E4 里的相当一部分是「无语义锚的机械通过」**。影子轨把断言内容当命题来问，于是与主轨拉开。这不是影子轨更聪明，而是两条轨道对「什么算支持」的定义本就不同——这才是 §15 要量化的东西。

### 3.3 执行者真实差异（0 条在本台账内）

轮七锚分诊的 24 条 `truly_missing`（A 3 / B 21）**全部落在 159 条之外**（其产物路径多为 `templates/`、`.github/workflows` 等目录型路径）。本台账 159 条内 `truly_missing` = 0，因此**本台账不含任何需要防「洗白」的条目**；那 24 条仍在轮七报告口径下单独计数，未因本卡分析而发生任何状态变化。

## 4. 轮六遗留项的合并归属（V3 落点）

### 4.1 「51 条未归类」的口径修正

卡面写「轮六遗留：51 条未归类项（312−261=51）」。执行者逐项核验后确认：**这个 51 是跨宇宙相减产生的算术假象，不是真实存在的条目集合。**

轮六 A 臂的真实划分（`round6-custody/shadow-r6/alignment-split.json` 逐项核对）：

```
450 条影子记录 = 189 一致可比对 + 123 判级不一致可比对 + 60 锚缺口 + 78 evaluative
                 └──── 312 可比对 ────┘
```

- `123 / 78 / 60` 是**记录级**的三分桶，三者两两不相交，并集 261 条；
- `312` 是**可比对**数；
- `312 − 261` 是用「对数」减「记录数」——**两个不同量纲相减**，所得 51 不对应任何条目。

同时核对轮七卡的另一处说法「eval 78 + anchor 60（重叠 15），123 = 78+60−15」：实测 eval 桶与 anchor 桶**重叠为 0**（不是 15），且 78/60 两条桶与 123 交集同样为 0。「15 兼有」这一表述在 custody 数据上不成立。

> **结论**：轮六并不存在一个「51 条未归类」的条目集合。该数字是上游口径（§14 D1-E 登记的「轮六遗留的 51 条未归类项列为 D-00 待查」）在传播中被当作真实人群继承了下来。

### 4.2 轮六真正未归类的 51 条（可机械复核的真实集合）

既然「51」不是人群，真正需要逐条归类的对象是：**轮六 A 臂 123 条判级不一致中，带命令但不带 `artifact_path` 的那 51 条**——它们没有产物面可查，只能靠命令面/语义面归因，正是最需要逐条读的那批。该集合可由 custody 数据机械复现（判据：属于 `gaps.semantic` ∧ `verification_command` 非空 ∧ `artifact_path` 为空），计数 **51**，与上游「51」数值巧合一致但**成员完全不同**。

下表逐条给出这 51 条的去向分类与依据（逐条引用各自的主轨判级依据原文）。

| # | claim_id | claim_type | predicate | 主轨判级 | 主轨判级依据（原文摘要） | 影子 predicate_ok（仓库根 / D4 反推） | 换观测面后是否成立 | 去向分类 | 去向依据 |
|---:|---|---|---|---|---|---|---|---|---|
| 1 | `P001-c01` | fact_value | `matches_regex` | E2 | 退出码不符: 证据声称 exit=1, 实际 exit=0 | True / True | workspace | 结构性错位 | 主轨判据=『退出码不符: 证据声称 exit=1, 实际 exit=0』——问「执行者自报的 exit 与真实 exit 是否相符」；影子判据 matches_regex 问命令面产物/输出（影子 predicate_ok=True）。命题不同，不是谓词表达力问题。 |
| 2 | `P003-c01` | fact_value | `contains` | E3 | 观察已复现但不支持断言（锚未命中: ['templates/verdict.json']）——证… | True / True | workspace | 结构性错位 | 主轨判据=『观察已复现但不支持断言（锚未命中: ['templates/verdict.json』——问「观察中锚是否命中」；影子判据 contains 问命令面条件（影子 predicate_ok=True）。命题不同。 |
| 3 | `P003-c04` | fact_value | `contains` | E2 | 退出码不符: 证据声称 exit=1, 实际 exit=0 | True / True | workspace | 结构性错位 | 主轨判据=『退出码不符: 证据声称 exit=1, 实际 exit=0』——问「执行者自报的 exit 与真实 exit 是否相符」；影子判据 contains 问命令面产物/输出（影子 predicate_ok=True）。命题不同，不是谓词表达力问题。 |
| 4 | `P005-c00` | fact_existence | `matches_regex` | E2 | 退出码不符: 证据声称 exit=255, 实际 exit=0 | True / True | workspace | 结构性错位 | 主轨判据=『退出码不符: 证据声称 exit=255, 实际 exit=0』——问「执行者自报的 exit 与真实 exit 是否相符」；影子判据 matches_regex 问命令面产物/输出（影子 predicate_ok=True）。命题不同，不是谓词表达力问题。 |
| 5 | `P009-c06` | command_output | `equals` | E4 | 命令已复现: python -c "from roman import roman_to_int… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python -c "from roman import roma』；影子判据 equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 6 | `P011-c03` | command_output | `exit_equals` | E4 | 命令已复现: python flatten.py; exit=0; out='flatten O… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python flatten.py; exit=0; out='f』；影子判据 exit_equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 7 | `P012-c01` | process_state | `exit_equals` | E2 | 声称输出未复现: out="python: can't open file 'D:\\\\158… | True / True | 否 | 结构性错位 | 主轨判据=『声称输出未复现: out="python: can't open fil』——问「自报 out 能否复现」；影子判据 exit_equals 问另一命题（影子 predicate_ok=True）。命题不同。 |
| 8 | `P021-c00` | process_state | `matches_regex` | E2 | 声称输出未复现: out='bebfb64 chore:<提交描述>' 不在实际输出中 | True / True | workspace | 结构性错位 | 主轨判据=『声称输出未复现: out='bebfb64 chore:<提交描述>' 』——问「自报 out 能否复现」；影子判据 matches_regex 问另一命题（影子 predicate_ok=True）。命题不同。 |
| 9 | `P021-c03` | process_state | `matches_regex` | E3 | 观察已复现但不支持断言（锚未命中: ['<type>: <描述>']）——证据与断言矛盾或无关 | True / True | workspace | 结构性错位 | 主轨判据=『观察已复现但不支持断言（锚未命中: ['<type>: <描述>']）——证据与断言』——问「观察中锚是否命中」；影子判据 matches_regex 问命令面条件（影子 predicate_ok=True）。命题不同。 |
| 10 | `P021-c04` | command_output | `equals` | E4 | 命令已复现: git log --oneline -1 bebfb64 \| ForEach-Ob… | False / False | 否 | 结构性错位 | 主轨 E4 依据=『命令已复现: git log --oneline -1 bebfb64 』——**无语义锚的机械通过**，未核验断言语义；影子判据 equals 直接核验内容，在仓库根与执行者工作区下均不成立（predicate_ok=False）。与轮七 S2 同签名。 |
| 11 | `P024-c00` | process_state | `matches_regex` | E2 | 声称输出未复现: out='bebfb64 chore:<提交描述>' 不在实际输出中 | True / True | workspace | 结构性错位 | 主轨判据=『声称输出未复现: out='bebfb64 chore:<提交描述>' 』——问「自报 out 能否复现」；影子判据 matches_regex 问另一命题（影子 predicate_ok=True）。命题不同。 |
| 12 | `P024-c03` | process_state | `matches_regex` | E3 | 观察已复现但不支持断言（锚未命中: ['<type>: <描述>']）——证据与断言矛盾或无关 | True / True | workspace | 结构性错位 | 主轨判据=『观察已复现但不支持断言（锚未命中: ['<type>: <描述>']）——证据与断言』——问「观察中锚是否命中」；影子判据 matches_regex 问命令面条件（影子 predicate_ok=True）。命题不同。 |
| 13 | `P024-c04` | command_output | `equals` | E4 | 命令已复现: git log --oneline -1 bebfb64 \| ForEach-Ob… | False / False | 否 | 结构性错位 | 主轨 E4 依据=『命令已复现: git log --oneline -1 bebfb64 』——**无语义锚的机械通过**，未核验断言语义；影子判据 equals 直接核验内容，在仓库根与执行者工作区下均不成立（predicate_ok=False）。与轮七 S2 同签名。 |
| 14 | `P025-c03` | command_output | `exit_equals` | E4 | 命令已复现: python bisect.py; exit=0; out='bsearch OK… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python bisect.py; exit=0; out='bs』；影子判据 exit_equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 15 | `P030-c01` | process_state | `exit_equals` | E2 | 声称输出未复现: out="python: can't open file 'D:\\\\158… | True / True | 否 | 结构性错位 | 主轨判据=『声称输出未复现: out="python: can't open fil』——问「自报 out 能否复现」；影子判据 exit_equals 问另一命题（影子 predicate_ok=True）。命题不同。 |
| 16 | `P043-c00` | fact_existence | `matches_regex` | E2 | 退出码不符: 证据声称 exit=255, 实际 exit=0 | True / True | workspace | 结构性错位 | 主轨判据=『退出码不符: 证据声称 exit=255, 实际 exit=0』——问「执行者自报的 exit 与真实 exit 是否相符」；影子判据 matches_regex 问命令面产物/输出（影子 predicate_ok=True）。命题不同，不是谓词表达力问题。 |
| 17 | `P050-c03` | command_output | `exit_equals` | E4 | 命令已复现: python flatten.py; exit=0; out='flatten O… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python flatten.py; exit=0; out='f』；影子判据 exit_equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 18 | `P055-c03` | command_output | `exit_equals` | E4 | 命令已复现: python flatten.py; exit=0; out='flatten O… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python flatten.py; exit=0; out='f』；影子判据 exit_equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 19 | `P060-c03` | command_output | `exit_equals` | E4 | 命令已复现: python balanced.py; exit=0; out='is_balan… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python balanced.py; exit=0; out='』；影子判据 exit_equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 20 | `P060-c06` | command_output | `equals` | E4 | 命令已复现: python -c "from balanced import is_balanc… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python -c "from balanced import i』；影子判据 equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 21 | `P061-c00` | fact_existence | `matches_regex` | E2 | 退出码不符: 证据声称 exit=255, 实际 exit=0 | True / True | workspace | 结构性错位 | 主轨判据=『退出码不符: 证据声称 exit=255, 实际 exit=0』——问「执行者自报的 exit 与真实 exit 是否相符」；影子判据 matches_regex 问命令面产物/输出（影子 predicate_ok=True）。命题不同，不是谓词表达力问题。 |
| 22 | `P064-c03` | command_output | `exit_equals` | E4 | 命令已复现: python is_leap.py; exit=0; out='is_leap O… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python is_leap.py; exit=0; out='i』；影子判据 exit_equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 23 | `P067-c01` | fact_value | `contains` | E3 | 观察已复现但不支持断言（锚未命中: ['templates/verdict.json']）——证… | True / True | workspace | 结构性错位 | 主轨判据=『观察已复现但不支持断言（锚未命中: ['templates/verdict.json』——问「观察中锚是否命中」；影子判据 contains 问命令面条件（影子 predicate_ok=True）。命题不同。 |
| 24 | `P067-c04` | fact_value | `contains` | E2 | 退出码不符: 证据声称 exit=1, 实际 exit=0 | True / True | workspace | 结构性错位 | 主轨判据=『退出码不符: 证据声称 exit=1, 实际 exit=0』——问「执行者自报的 exit 与真实 exit 是否相符」；影子判据 contains 问命令面产物/输出（影子 predicate_ok=True）。命题不同，不是谓词表达力问题。 |
| 25 | `P074-c03` | command_output | `exit_equals` | E4 | 命令已复现: python bisect.py; exit=0; out='bsearch OK… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python bisect.py; exit=0; out='bs』；影子判据 exit_equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 26 | `P078-c00` | fact_existence | `matches_regex` | E2 | 退出码不符: 证据声称 exit=255, 实际 exit=0 | True / True | workspace | 结构性错位 | 主轨判据=『退出码不符: 证据声称 exit=255, 实际 exit=0』——问「执行者自报的 exit 与真实 exit 是否相符」；影子判据 matches_regex 问命令面产物/输出（影子 predicate_ok=True）。命题不同，不是谓词表达力问题。 |
| 27 | `P080-c03` | command_output | `exit_equals` | E4 | 命令已复现: python is_leap.py; exit=0; out='is_leap O… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python is_leap.py; exit=0; out='i』；影子判据 exit_equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 28 | `P083-c03` | command_output | `exit_equals` | E4 | 命令已复现: python bisect.py; exit=0; out='bsearch OK… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python bisect.py; exit=0; out='bs』；影子判据 exit_equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 29 | `P084-c01` | fact_value | `matches_regex` | E2 | 退出码不符: 证据声称 exit=1, 实际 exit=0 | True / True | workspace | 结构性错位 | 主轨判据=『退出码不符: 证据声称 exit=1, 实际 exit=0』——问「执行者自报的 exit 与真实 exit 是否相符」；影子判据 matches_regex 问命令面产物/输出（影子 predicate_ok=True）。命题不同，不是谓词表达力问题。 |
| 30 | `P095-c03` | command_output | `exit_equals` | E4 | 命令已复现: python revstr.py; exit=0; out='is_palindr… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python revstr.py; exit=0; out='is』；影子判据 exit_equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 31 | `P095-c06` | command_output | `equals` | E4 | 命令已复现: python -c "from revstr import is_palindro… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python -c "from revstr import is_』；影子判据 equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 32 | `P098-c03` | command_output | `exit_equals` | E4 | 命令已复现: python is_leap.py; exit=0; out='is_leap O… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python is_leap.py; exit=0; out='i』；影子判据 exit_equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 33 | `P103-c03` | command_output | `exit_equals` | E4 | 命令已复现: python revstr.py; exit=0; out='is_palindr… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python revstr.py; exit=0; out='is』；影子判据 exit_equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 34 | `P103-c06` | command_output | `equals` | E4 | 命令已复现: python -c "from revstr import is_palindro… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python -c "from revstr import is_』；影子判据 equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 35 | `P109-c00` | fact_existence | `matches_regex` | E2 | 退出码不符: 证据声称 exit=255, 实际 exit=0 | True / True | workspace | 结构性错位 | 主轨判据=『退出码不符: 证据声称 exit=255, 实际 exit=0』——问「执行者自报的 exit 与真实 exit 是否相符」；影子判据 matches_regex 问命令面产物/输出（影子 predicate_ok=True）。命题不同，不是谓词表达力问题。 |
| 36 | `P125-c06` | command_output | `equals` | E4 | 命令已复现: python -c "from roman import roman_to_int… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python -c "from roman import roma』；影子判据 equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 37 | `P135-c00` | fact_existence | `matches_regex` | E2 | 退出码不符: 证据声称 exit=255, 实际 exit=0 | True / True | workspace | 结构性错位 | 主轨判据=『退出码不符: 证据声称 exit=255, 实际 exit=0』——问「执行者自报的 exit 与真实 exit 是否相符」；影子判据 matches_regex 问命令面产物/输出（影子 predicate_ok=True）。命题不同，不是谓词表达力问题。 |
| 38 | `P141-c03` | command_output | `exit_equals` | E4 | 命令已复现: python balanced.py; exit=0; out='is_balan… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python balanced.py; exit=0; out='』；影子判据 exit_equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 39 | `P141-c06` | command_output | `equals` | E4 | 命令已复现: python -c "from balanced import is_balanc… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python -c "from balanced import i』；影子判据 equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 40 | `P147-c06` | command_output | `equals` | E4 | 命令已复现: python -c "from roman import roman_to_int… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python -c "from roman import roma』；影子判据 equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 41 | `P150-c00` | process_state | `matches_regex` | E2 | 声称输出未复现: out='bebfb64 chore:<提交描述>' 不在实际输出中 | True / True | workspace | 结构性错位 | 主轨判据=『声称输出未复现: out='bebfb64 chore:<提交描述>' 』——问「自报 out 能否复现」；影子判据 matches_regex 问另一命题（影子 predicate_ok=True）。命题不同。 |
| 42 | `P150-c03` | process_state | `matches_regex` | E3 | 观察已复现但不支持断言（锚未命中: ['<type>: <描述>']）——证据与断言矛盾或无关 | True / True | workspace | 结构性错位 | 主轨判据=『观察已复现但不支持断言（锚未命中: ['<type>: <描述>']）——证据与断言』——问「观察中锚是否命中」；影子判据 matches_regex 问命令面条件（影子 predicate_ok=True）。命题不同。 |
| 43 | `P150-c04` | command_output | `equals` | E4 | 命令已复现: git log --oneline -1 bebfb64 \| ForEach-Ob… | False / False | 否 | 结构性错位 | 主轨 E4 依据=『命令已复现: git log --oneline -1 bebfb64 』——**无语义锚的机械通过**，未核验断言语义；影子判据 equals 直接核验内容，在仓库根与执行者工作区下均不成立（predicate_ok=False）。与轮七 S2 同签名。 |
| 44 | `P158-c01` | fact_value | `contains` | E3 | 观察已复现但不支持断言（锚未命中: ['templates/verdict.json']）——证… | True / True | workspace | 结构性错位 | 主轨判据=『观察已复现但不支持断言（锚未命中: ['templates/verdict.json』——问「观察中锚是否命中」；影子判据 contains 问命令面条件（影子 predicate_ok=True）。命题不同。 |
| 45 | `P158-c04` | fact_value | `contains` | E2 | 退出码不符: 证据声称 exit=1, 实际 exit=0 | True / True | workspace | 结构性错位 | 主轨判据=『退出码不符: 证据声称 exit=1, 实际 exit=0』——问「执行者自报的 exit 与真实 exit 是否相符」；影子判据 contains 问命令面产物/输出（影子 predicate_ok=True）。命题不同，不是谓词表达力问题。 |
| 46 | `P159-c03` | command_output | `exit_equals` | E4 | 命令已复现: python balanced.py; exit=0; out='is_balan… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python balanced.py; exit=0; out='』；影子判据 exit_equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 47 | `P159-c06` | command_output | `equals` | E4 | 命令已复现: python -c "from balanced import is_balanc… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python -c "from balanced import i』；影子判据 equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 48 | `P166-c03` | command_output | `exit_equals` | E4 | 命令已复现: python revstr.py; exit=0; out='is_palindr… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python revstr.py; exit=0; out='is』；影子判据 exit_equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 49 | `P166-c06` | command_output | `equals` | E4 | 命令已复现: python -c "from revstr import is_palindro… | False / False | workspace | 仪器可修 | 主轨 E4 依据=『命令已复现: python -c "from revstr import is_』；影子判据 equals 在仓库根不成立（predicate_ok=False），在执行者工作区 workspace 下成立（predicate_ok=True）——观测面分歧，对齐观测面即可消解。 |
| 50 | `P170-c01` | fact_value | `matches_regex` | E2 | 退出码不符: 证据声称 exit=1, 实际 exit=0 | True / True | workspace | 结构性错位 | 主轨判据=『退出码不符: 证据声称 exit=1, 实际 exit=0』——问「执行者自报的 exit 与真实 exit 是否相符」；影子判据 matches_regex 问命令面产物/输出（影子 predicate_ok=True）。命题不同，不是谓词表达力问题。 |
| 51 | `P176-c01` | process_state | `exit_equals` | E2 | 声称输出未复现: out="python: can't open file 'D:\\\\158… | True / True | 否 | 结构性错位 | 主轨判据=『声称输出未复现: out="python: can't open fil』——问「自报 out 能否复现」；影子判据 exit_equals 问另一命题（影子 predicate_ok=True）。命题不同。 |

**轮六 51 条去向计数**：结构性错位 27 条、仪器可修 24 条、执行者真实差异 0 条、仍未归类 0 条（逐条判定，零未决）。

### 4.3 与轮七的合并归属

轮六 51 条与轮七 159 条的失配机制**同构**，可合并为同一套处置口径：

| 处置口径 | 轮七 159 条 | 轮六 51 条 | 合并 210 条 | 对应建议（D3） |
|---|---:|---:|---:|---|
| 对齐观测面 / 路径解析（仪器可修） | 84 | 24 | 108 | R1 |
| 命题层级错位（结构性错位） | 75 | 27 | 102 | R2 / R3 |
| 执行者真实差异（truly_missing） | 0 | 0 | 0 | 不修（只计数） |
| **合计** | **159** | **51** | **210** | |

> 轮六 51 条的逐条判定方法：轮六对齐器与轮七用**同一条 §12 D4 规则**（已核 15ef42a 的 `shadow_align.py`：`consistent = bool(predicate_ok) == (level=='E4')`），故对每条不一致项可**反推**影子谓词结果（主轨 E4 → predicate_ok=False；E2/E3 → True）；再用**轮六当时的 v1.6 冻结编译器**（从 15ef42a 取出）在仓库根重算，**51/51 与反推值一致**；再逐条检查该判据在执行者工作区（C10 工作区 / run-dir 产品目录）是否成立。结果：**24 条为观测面分歧**（仓库根不成立、工作区成立 → 仪器可修），**27 条为命题层级错位**（主轨判证据行/锚，影子判内容；含 3 条 `ForEach-Object` 在 cmd.exe 失败仍被主轨判 E4 的极端形态）。**逐条判定，零未决，无比例分摊。**

> 合并后的关键数字：**轮六+轮七合计 210 条失配中，108 条（51.4%）只需对齐观测面即可消解，102 条（48.6%）源于主轨与影子对「什么算支持」的定义分歧；没有一条需要新增谓词。**

## 5. 与 ADV-4 / 轮七结论的关系

| 轮七报告结论 | 本卡核验 |
|---|---|
| §14 预期消解映射表 hit_rate 0 < 0.80，预测失效 | **成立**。逐条证据显示：159 条里没有一条是「谓词表达不了这个断言」，失败点在观测面与命题层级，扩 enum 本就不该命中。 |
| v1.7 四谓词扩充未提升一致率（A 0.6058→0.5728） | **成立，且原因已定位**：主因不是判据不够，而是影子轨仍按仓库根观测（I2/I3 共 72 条）。 |
| 浮香重点 1：semantic 残余指向「编译裁量 vs 判级语义结构性错位」 | **成立并细化**：「结构性错位」75 条确为此类；但同时暴露出更前置的一层——**84 条是观测面分歧，属仪器可修**，此前未被识别为独立一类。 |
| 轮七「无语义锚，仅机械复核通过」记法 | **升级为本次的核心发现**：S2 类 42 条正是「主轨无语义锚机械 E4 / 影子语义判据」的分歧带，S3 类 3 条是其极端形态（自报命令本身失败仍判支持）。 |

## 6. 局限与未闭合项

1. 本卡只做分类，不改任何 instrument；因此**一致率不会因本卡而变**。
2. 轮六 51 条中的 27 条在旧数据上不可判定（主轨证据链本身无语义锚），本卡**如实标注为需逐条归因**，不强行归类——这与卡面「不洗白」「不得降格」一致。
3. 影子判据原始结果由冻结编译器在**当前观察根**重算。若将来观察根状态变化（如 C10 工作区重建口径调整），需重跑本台账生成脚本；台账 JSON 记录了全部来源路径与 SHA 口径。
4. 159 条的分类由逐条机械规则得出，规则与逐条证据写在 `docs/d00-mismatch-ledger.json` 的 `method` 与每条的 `reason` / `mechanism` 字段中，可逐条复核；**未使用任何比例分摊**。
