# 轮十评估报告 · 双指标门重设计与 Gate 0 主轨信度复测（XJ-20261111-001）

> 执行者：WorkBuddy（代号 **WB**）· 分支 `feature/xj-20261111-001-round10-gate-redesign` · 基线 `1e99458`
> 依据：`docs/eval-prereg.md` §17（冻结 commit `ee7e765`，早于一切轮十产物）
> 执行者无评审权、无合并权；不 push / 不 merge / 不写 verdict

## 0. 首页结论（先说结论，不藏在附录）

**门结论：未过门（`gate_result = not met`）。**

双指标门要求 `decidable_rate ≥ 0.80 ∧ C ≥ M_C` **同时成立**（D17-D 第 5 条）。轮十真数据实测：

- 可判定率 `0.857143`（180/210）≥ 0.80 —— **达标**；
- 条件一致率 `C = 0.5`（90/180）< `M_C = 0.95` —— **未达标**；
- 故 `gate_result = not met`。**不得用可判定率补偿条件一致率、不得改分母让读数变好看**（D17-D 第 5 条）。

Gate 0 未触发挂起（`R_main = 1.0 ≥ 0.90`），故本轮按 D17-C 第 7 条允许报告门结论；但这个 `R_main = 1.0` 是**确定性重放的同义反复，不是主轨语义信度证据**，见 §2 与 `docs/eval-gate0-main-reliability.md`。

**影子轨定位仍为「预筛」非「替代」**（D17-G）。本报告不出现「影子轨可替代主轨」「判级语义已对齐」「影子轨通过即等同主轨判级」等表述；R2（命题层级对齐）仍是另一轮，本卡不解决 R2，不把双指标门达标解释为命题已对齐。

## 1. 合法性与冻结序

**门重设计的唯一合法理由**（dp 大脑裁定、卡面 Context 钉入）：旧 95% 单一致率门测的不是声称要测的东西——① 分母污染（静默失败条目被塌缩成「不支持」计入分母，是分母污染不是能力下降）；② 从来不是实测可达门（pre-R1 的 0.5825 同样远低于 95%）。**不是**因为「旧门让影子过不了」；后者属 HARKing，整轮作废。

**旧门作废声明**：轮十起，95% 单一致率门作废，D17-D 双指标门是唯一资格门。**门重设计只许一次**——§17 之后不得再改门定义（D17-H / 卡面约束）。封存机制：门定义与门值推导函数冻结在 `docs/eval-prereg.md` §17（commit `ee7e765`），门值冻结包 `out/gate-value-freeze.json` 在看到任何影子 C 值之前生成。

**三段序（机械可验）**：

| 序 | 事件 | 时间 / commit |
|---|---|---|
| 1 | §17 冻结 commit | `ee7e765`，`2026-11-11T13:23:58+08:00` |
| 2 | 度量实现冻结 | `tools/eval/gate_metrics.py`，SHA-256 `4f43b098…39e`，commit `ff4f949` |
| 3 | Gate 0 输入集 / 双跑 / 门值盲态冻结 | D1 `f921427`；门值冻结包 `out/gate-value-freeze.json`（`signer_blind_to_c = true`） |
| 4 | D4 标注冻结 | 标注 manifest UTC `2026-11-11T05:57:59.376439+00:00`，早于实现产物 UTC `05:58:40` |
| 5 | 轮十真数据（`run-dir-r10/` / `shadow-r10/`） | D5，晚于门值冻结包 |

**门值盲态冻结**：`M_C = floor_to_5pct(min(0.95, R_main − 0.05)) = 0.95`；预筛分支门槛 `min(0.85, R_main − 0.10) = 0.85`，只在预筛语境使用，与资格门分列。冻结包 `shadow_data_seen = false`，签署时 `shadow-r10/` 不存在、文件数 0；`derived_at_utc` 早于一切轮十影子产物。**签署者独立性有限**：盲态靠顺序与数据隔离，不是独立人类签署者，已写入冻结包并交浮香裁定。

## 2. 四层并列（D6 主表）

> 四层同表并列，避免把任一层单独抽出来当结论。V7 要求的五个键 `R_main`、`可判定率`、`条件一致率`、`A_shadow`、`分层` 均在本表出现。

| 层 | 指标 | 读数 | 门 / 判据 | 定性 |
|---|---|---|---|---|
| **第一层 · Gate 0 主轨信度** | `R_main` | `1.0`（240/240） | `R_main ≥ 0.90` 未挂起 | 确定性重放同义反复，**非语义信度证据**；`R_main_flags = 1.0`、`R_main_detail = 1.0`、扰动副口径 `R_main_perturbed = 1.0` |
| **第二层 · 双指标门** | `可判定率` | `0.857143`（180/210） | `≥ 0.80` | **达标** |
| **第二层 · 双指标门** | `条件一致率 C` | `0.5`（90/180） | `≥ M_C = 0.95` | **未达标** → `gate_result = not met` |
| **第二层 · 双指标门** | `SILENT_FALLBACK` 单列 | `30`（独立计数项存在） | 防注水 | 与 `FILE_NOT_FOUND` 同批 30 条记录双类命中，非 60 条不同记录 |
| **第三层 · 金标准 A 对比** | `A_main` / `A_shadow` | `1.0` / `1.0` | `A_shadow ≥ A_main − 0.05` → `direction_pass = True` | **仅方向判据、诊断用**，不作分层硬门、不膨胀为资格门 |
| **第四层 · `分层` 诊断** | 混淆矩阵 / ERROR 分类 / layer | TP 90 · TN 0 · FP 60 · FN 30；`FILE_NOT_FOUND` 30、`SILENT_FALLBACK` 30 | 无门 | 只作诊断，不与资格门互相代偿 |

**四层关系**：第一层定天花板与门值，第二层是唯一资格门，第三层是校准方向，第四层是诊断。**任一层都不得替代另一层**：`A_shadow = 1.0` 不能把 `C = 0.5` 洗成达标，`R_main = 1.0` 也不能证明影子轨可靠。

## 3. 第一层 · Gate 0 主轨信度（D1）

三次互不可见的独立会话（不同 PID / 启动时间 / 临时工作区 / 盲化 seed / 输入序），同一批 240 条冻结 claim，`R_main = 1.0`、`gate0_suspend = False`。独立性机械核验 6 项全通过。

**必须披露的确定性局限**：`tools/eval/judge.py` 是确定性实现（无 LLM、无网络、无随机源，模块 docstring 明写「same input text + same filesystem state + same command outputs ⇒ same levels/flags/detail」）。因此两次同输入会话若环境一致，`R_main = 1.0` 是**确定性重放的同义反复**，不构成语义信度或跨环境稳健性证据。扰动副口径 `R_main_perturbed = 1.0` 同样受此局限约束。是否需要人工 / 独立判级实现重测，交浮香裁定。

## 4. 第二层 · 双指标门真数据（D5 / V4）

**数据口径**：`run-dir-r10/` + `shadow-r10/`，30 个冻结任务定义 × 9 层 = 270 条主轨 claim；`pairs = 210`（主轨 E2/E3/E4 完整判级轨迹），另有 60 条 `structural_exclusions`（E0/E1 层，`incomplete` / `no_evidence`）。`align()` 默认 `fail_fast_observation = True`，`allow_silent_fallback_used = false`——**本轮未使用 `--allow-silent-fallback`**（V5 / D17-D 第 6 条）。

V4 两条命令亲跑，退出码 `0 / 0`：

```
python tools\eval\gate_metrics.py --run-dir run-dir-r10 --shadow shadow-r10 --out out\gate-metrics-r10.json
  → wrote out\gate-metrics-r10.json (dual_metric)                    EXIT 0
python -X utf8 -c "... print('det_rate:',d['decidable_rate'],'| C:',d['conditional_agreement'],'| silent_fallback:',e.get('SILENT_FALLBACK',0))"
  → det_rate: 0.857143 | C: 0.5 | silent_fallback: 30             EXIT 0
```

| 字段 | 值 |
|---|---|
| `comparable` / `decidable` / `excluded_from_c_denominator` | 210 / 180 / 30 |
| `decidable_rate` / floor | `0.857143` / `0.80` |
| `consistent` / `conditional_agreement` | 90 / `0.5` |
| `m_c` / `gate0_suspend` / `gate_result` | `0.95` / `false` / `not met` |
| `confusion_matrix` | `TP 90 / TN 0 / FP 60 / FN 30` |
| `error_breakdown` | `FILE_NOT_FOUND 30`、`CWD_MISMATCH 0`、`PARSE_FAIL 0`、`TIMEOUT 0`、`SILENT_FALLBACK 30` |
| `silent_fallback_reported_separately` | `true` |
| `own_buckets` | `not_applicable 0` / `evaluative 0` / `schema_invalid 0` |
| `fail_fast_observation` / `allow_silent_fallback_used` | `true` / `false` |
| `run_dir_manifest.run_data_present` | `true`（SHA-256 `d02905eb…880`） |

**防注水机制的实测证据**：轮九 pre-R1 的 `0.5825` 由静默失败塌缩成「不支持」注水而来。轮十的 `fallback_probe` 层（每个 product 1 条，共 30 条）复现该失败模式——命令依赖 `probe-<code>.txt` 在 workspace 不可见，执行器正常返回但判据为假。`align()` 的 fail-fast 把这 30 条**逐条显式报类**（`FILE_NOT_FOUND` + `SILENT_FALLBACK`），`gate_metrics.py` 把它们留在可判定率分母、从 C 分母剔除。若沿用旧静默口径，这 30 条会被当成「判据不支持」进入一致率分母，读数被抬高——这正是 `SILENT_FALLBACK` 必须单列的原因。

**交叉验证**：`decidable = 180`、`consistent = 90` 与 `shadow_align.align()` 严格口径的 `comparable_pairs = 180`、`consistent_pairs = 90`（`agreement_rate = 0.5`）逐项一致。两条独立实现路径在同一可判定集合上得到同一读数，未出现分母漂移。

**`error_breakdown` 计数口径**：`FILE_NOT_FOUND 30` 与 `SILENT_FALLBACK 30` 是**同一批 30 条记录的双类命中**（每条同时带两类），不是 60 条不同记录；`excluded_from_c_denominator = 30` 与 `silent_fallback_count = 30` 可对抗核验。

**`own_buckets` 全 0 的原因**：轮十真数据的 9 层设计未构造 B 臂 `not_applicable` / `evaluative` / `schema_invalid` 桶，故三项计数为 0；这不是漏计，也不是把难判条目挑出去凑分母（D17-D 第 7 条）。B 臂 `not_applicable` 的口径仍按既有规则不计入 C 分母，本轮无该类样本。

## 5. 第三层 · 金标准 A 对比（D4）

`goldset/gold_claims.jsonl` 60 行、0 个 `_meta` 行；轮七 30 条 `record` 逐字保留 + 轮十新增 30 条。`comparable = 51` / `excluded = 9`（4 个桶），`A_main = 1.0`、`A_shadow = 1.0`、`direction_pass = True`、`mismatch 0`、A/B 标注分歧 0。V6 三条命令退出码 `0 / 0 / 0`。

**`A = 1.0` 的含义与边界**：它只表示主轨判级与影子判据各自与「按规范独立推导的标注」在 51 条可比条目上逐条一致；**不等于**主轨语义信度、**不等于**影子轨可替代主轨、**不等于** §15 的 CQ / surface parity / proposition alignment 达标（D17-B：两套集合不互相校准、不重复计分）。方向判据只作诊断，失败也不构成门不过（D17-F 第 4 条）。

**D4 双盲局限（不洗白）**：两条标注视图由同一 agent WB 实现，非两名独立人类标注者；A/B 标注产物字节相同、0 分歧——**0 分歧不证明独立性**。首次标注曾出现 44 条主轨 level 程序性分歧，在实现产物生成之前作废存档、修正后重标，全过程留痕。详见 `docs/eval-goldset-calibration-r10.md` §4 / §5。

## 6. 第四层 · 分层诊断

| 诊断面 | 读数 | 说明 |
|---|---|---|
| 主轨 level 分布 | 见 `run-dir-r10/run-data.json` 的 `level_distribution` | 新判级，未重判轮六–轮九历史轮次（C12） |
| 9 个 layer | `cmd_ok` / `anchor_miss` / `repro_fail` / `incomplete` / `ref_ok` / `ref_missing` / `goldset_text` / `fallback_probe` / `no_evidence` | 每层每 product 1 条，共 270 条；`incomplete` / `no_evidence` 落 E1/E0 → 60 条 structural exclusions |
| ERROR 类 | `FILE_NOT_FOUND 30` + `SILENT_FALLBACK 30`（同批）、其余 3 类 0 | 5 类预注册 ERROR 全列，未把任一类折叠 |
| 混淆矩阵 | `TP 90 / TN 0 / FP 60 / FN 30` | FP 主要来自主轨非支持级而判据为真（`repro_fail` / `ref_missing` 层）；分层只作诊断，不作资格门 |
| `align()` 严格口径 | `comparable 180` / `consistent 90` / `agreement_rate 0.5` / `aligned 270` / `alignment_rate 1.0` | 与双指标门可判定集合逐项一致 |

**分层不得反向用于调门**：门值 `M_C = 0.95` 在看到任何影子分层读数之前已盲态冻结；本节的 layer / ERROR / 混淆矩阵分布**不得**用于回头修改门值或分母（D17-E 第 5 条、D17-D 第 7 条）。

## 7. 数据来源与自由度的如实披露（交评审裁定的重点）

**§17 冻结文本没有明文定义 D5 真数据集的生成规则**，卡面 D5 也只有「轮十真数据轮次（主轨 + 影子轨，fail-fast 默认口径，禁 `--allow-silent-fallback`）」一句。执行者按 D17-C 第 6 条的冻结任务定义路径自行生成：

- 语义源只有 `tools/eval/tasks/T*.json`（30 个冻结任务定义），不导入轮九 309 条封存 pair、不重判历史轮次（C12）；
- **不**把 60 行金标准集当真数据（D17-B 不重复计分）；
- **不**复用 Gate 0 专用 claim 集（claim 文本、fixture 名、层序均不同，`R_main` 计算未接触影子输出）；
- 生成脚本 `round10-custody/r10_truedata.py` 落仓外、SHA-256 入册，生成时间晚于门值冻结包。

**必须披露的自由度**：9 个 layer 的设计与比例、正/反例配比、以及专门放入 `fallback_probe` 层来实测 `SILENT_FALLBACK`，都是**执行者在 D5 阶段的补充设计**，不是 §17 冻结条款明文规定的抽样规则。因此 `C = 0.5` 这个**绝对值不具备对影子轨能力的裁决意义**——它反映的是本轮诊断数据的层次构成。门值虽然先于数据冻结（不构成 HARKing），但「数据生成规则未预注册」仍是一处方法论缺口。**是否接受本轮门结论、是否要求按冻结抽样规则重做 D5，交浮香裁定，执行者不自行裁定。**

另一处适配层：`gate-input.json` 的 `exit_code` / `parse_ok` 是**对冻结编译器 flags/detail 的机械映射**，不是独立 OS 进程退出码（映射规则写在 `gate-input.json` 的 `field_semantics`，可逐条复算）。可判定性三条件中的这两条因此是适配层口径，`error_classes` 才是 `align()` 的原生实测分类。是否构成口径降级，一并交评审裁定。

## 8. 影子轨定位声明（D17-G）

主轨 M1 配对差 5.8%［1.7, 11.2］按冻结判据（≥10pp 且 95% CI 不跨零）为**未检出达到最小效应的差异**，替代标准过高。影子轨定位为**「预筛」**，**不是主轨的替代**。预筛分支门槛 `0.85` 只在预筛语境使用，与资格门 `M_C = 0.95` 分列。本卡不解决 R2，不把双指标门达标解释为命题层级已对齐；本轮门结论为 `not met`，更不构成任何替代性宣称。

## 9. 结论与交浮香裁定项

**结论**：轮十双指标门 `not met`（可判定率达标、条件一致率未达）。`R_main = 1.0` 未触发挂起但受确定性局限约束；`A_shadow = A_main = 1.0`、`direction_pass = True` 仅为校准方向；`SILENT_FALLBACK` 30 条单列并成功阻止注水。影子轨仍是预筛。

**交浮香裁定项（执行者不自行裁定）**：

1. D5 数据生成规则未在 §17 冻结、层次比例由执行者设计，`C = 0.5` 的裁决效力如何认定；是否要求重做 D5。
2. `gate-input.json` 的 `exit_code` / `parse_ok` 机械映射是否构成可判定性三条件的口径降级。
3. Gate 0 `R_main = 1.0` 的确定性局限：是否接受其作为门值输入，是否要求独立判级实现重测。
4. D2 签署者 / D4 标注者均为单 agent：盲态由顺序与数据隔离保证，是否满足「独立签署者」「双人独立标注」条款。
5. D4 首次 44 条程序性分歧作废重标，是否触及「只许一次」类条款。
6. §17 D17-F 第 5 条指定 `docs/eval-goldset-calibration-r10.md` 而卡面 Owned files 原清单未列，机械追记登记是否认可。
7. 门值 `M_C = 0.95` 的盲态冻结是否真未被 C 分布间接污染。

**收尾边界**：本卡不写 verdict、不 push、不 merge、不碰 master、不重判历史轮次。PASS gate 由浮香（AgnesCode）裁定，Orchestrator 预审。

---

## 附录 A · Acceptance V1–V9 亲跑记录（执行者亲跑，不采纳 precheck）

> 卡面 Acceptance 抬头：「任一 FAIL 不进入门结论讨论」。本报告首页的 `gate_result = not met` 是 `gate_metrics.py` 的**机械输出字段**，不是执行者对验收通过性的裁定。V8 / V9 存在未闭合退出码，本轮**不作为验收全绿交付**，是否阻断由 Orchestrator 预审与浮香裁定。

| 检查 | 命令（卡面字面 / 等价） | 退出码 | 真实输出摘要 |
|---|---|---|---|
| V1 | `git log -1 --format=%cI -- docs/eval-prereg.md` | `0` | `2026-11-11T13:23:58+08:00` |
| V1 | `git diff 1e99458..HEAD -- docs/eval-prereg.md \| Select-String "^[-+]" \| Where-Object … \| Measure-Object` | `0` | `V1_CHANGED_LINES = 152` |
| V1 交叉 | `git diff 1e99458..HEAD --numstat -- docs/eval-prereg.md` | `0` | `274  0  docs/eval-prereg.md`（新增 274 / 删除 0） |
| V2 | `python tools\eval\gate_metrics.py --gate0 --main out\gate0-main-a.json --main-rerun out\gate0-main-b.json --out out\gate0-reliability.json` | `0` | `wrote out\gate0-reliability.json (gate0)` |
| V2 | 读 `r_main` | `0` | `R_main: 1.0` |
| V3 | 读 `out/gate-value-freeze.json` | `0` | `M_C: 0.95 \| signer: WB / Gate-0 signer role (no shadow-data access at signing time) \| blind: True` |
| V4 | `python tools\eval\gate_metrics.py --run-dir run-dir-r10 --shadow shadow-r10 --out out\gate-metrics-r10.json` | `0` | `wrote out\gate-metrics-r10.json (dual_metric)` |
| V4 | 读 `decidable_rate` / `C` / `SILENT_FALLBACK` | `0` | `det_rate: 0.857143 \| C: 0.5 \| silent_fallback: 30` |
| V5 | `git diff 1e99458..HEAD -- tools/eval/shadow_align.py \| Measure-Object` | `0` | `V5_DIFF_LINES = 0` |
| V6 | 行数 / `--goldset` / 读 A 值（三条） | `0 / 0 / 0` | `60`；`wrote out\goldset-r10.json (goldset)`；`A_shadow: 1.0 \| A_main: 1.0 \| pass: True` |
| V7 | 报告五键检查 | `0` | `['R_main', '可判定率', '条件一致率', 'A_shadow', '分层']` |
| V8 字面 | `python tools\eval\seal_run.py --verify --run-dir run-dir-r10` | **`2`** | `seal_run.py: error: argument --verify: expected one argument` |
| V8 等价 | `python tools\eval\seal_run.py --verify run-dir-r10` | `0` | `VERIFY: OK (32 files match the seal)` |
| V8 红区 | `git diff 1e99458..HEAD --stat -- <红区 11 项>` | `0` | 空输出 |
| V9 首跑 | `python -m unittest discover -s tests` | **`1`** | `Ran 527 tests` … `FAILED (failures=2, errors=3)` |
| V9 首跑 | `lint_cards.py … --strict` | **`1`** | `LINT: FAIL (0 errors, 6 warnings)` |
| V9 复跑 | `COVENANT_BASH_HINT` 设置后全量单测 | `0` | `Ran 546 tests in 163.656s` / `OK` |
| V9 复跑 | `tools/sync_test_count.py --check` | `0` | README 与 README.zh-CN 均 `in sync at 546` |
| V9 复跑 | `lint_cards.py … --strict` | **`1`** | `LINT: FAIL (0 errors, 2 warnings)` |

**V1 口径差异（如实登记）**：字面 `Select-String` 计数 `152` 与 `git diff --numstat` 的 `274 / 0` 不一致（PowerShell 管道口径差异，D0 阶段已出现过同类 `274 vs 196` 现象）。§0–§16 冻结文本零改动的主证据不是行数，而是 `round10-custody/freeze_s17.py` 的**字节级校验**：冻结前 96004 字节 `prefix_intact = true`、§15 草案 13832 字节 `verbatim_intact = true`、新增 0 删除（numstat）。

**V2 覆盖（如实登记）**：卡面 V2 字面命令未带 `--perturbed`，重跑覆盖了 D1 的完整读数文件 `out/gate0-reliability.json`，使其 `perturbation.available` 由 `true` 变 `false`；`r_main = 1.0` 不变。含扰动副口径的完整版保留在 `out/gate0-reliability-full.json` 与 custody 副本，未删除、未回改。

**V8 字面失败（§17 D17-H 第 8 条预冻结处置）**：卡面字面命令与 `seal_run.py` 真实 CLI（`--verify RUN_DIR`，位置参数、无 `--run-dir`）不符，D0 冻结 §17 时已预写处置。按纪律先按字面跑并登记 `exit 2`，再按等价正确命令跑并登记 `exit 0`，两者都不修饰。密封动作 `python tools/eval/seal_run.py run-dir-r10 --label XJ-20261111-001-r10 --move-to <custody/sealed>` 退出码 `0`，`seal.json` 覆盖 32 个文件，custody 副本 `round10-custody/sealed/run-dir-r10` 验签通过。

**V9 未闭合项（不刷绿）**：

1. 首跑 527 tests / 2 failures + 3 errors 的根因是 `tests/test_pre_push_hook.py` 在 Windows 下导入期需要 `COVENANT_BASH_HINT` 指向 Git for Windows bash；连带 `test_sync_test_count` 三个用例因套件无法发现而失败。设置 `COVENANT_BASH_HINT=D:\WorkBuddy\resources\vendor\PortableGit\usr\bin\bash.exe` 后 546 tests 全绿、`sync_test_count.py --check` 为 0。**两次退出码都如实登记，不隐藏首跑失败。**
2. 首跑 lint 的 6 条 warnings 中有 4 条是本轮把说明写在 Owned files 路径行上引起的（`OWNED_FILES_NONPATH` / `OWNED_FILES_TOO_BROAD`），已把说明移到 Constraints 节、路径单独成行，warnings 降到 2 条；**不改变任何授权边界**。
3. 残余 2 条：① `OWNED_FILES_NONPATH` 对 `.gitignore` —— `lint_cards.py::_looks_like_path` 的裸文件名正则 `^[^/\\]+\.[A-Za-z0-9]{1,8}$` 不接受无扩展名 dotfile，属工具判定缺口，非授权声明错误；② `VERDICT_WITHOUT_REVIEW` —— 执行者按纪律不写 verdict，该卡在浮香评审前必然无 verdict 文件。执行者**不通过改写路径或补写 verdict 来刷绿** `--strict`。

**结论**：V1–V7 全绿；V8 字面命令 `exit 2`（卡面 CLI 缺陷，已按冻结条款双跑登记）、等价命令与红区检查全绿；V9 单测复跑全绿但 `lint --strict` 仍 `exit 1`（2 条结构性 / 工具口径 warnings）。按卡面「任一 FAIL 不进入门结论讨论」，本轮**不宣布验收通过**，交 Orchestrator 预审与浮香裁定。
