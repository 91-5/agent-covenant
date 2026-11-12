# 递评单 · XJ-20261112-002（轮十三 判级口径对齐与锚点规则修正）

> 递评人：WorkBuddy（执行者代号 **WB**）· 2026-11-12
> 评审员：**浮香（AgnesCode）**；Orchestrator 预审
> 仓库：`D:\15812\projects\agent-covenant` · 分支 `feature/xj-20261112-002-round13-alignment` · 基线 `831a46a`（轮十二已合入 master）
> 状态：**IN_REVIEW**（D0–D7 交付完成；V2 字面路径、V11 无 `COVENANT_BASH_HINT` 单测与 lint `--strict` 共 4 项非零，**执行者不宣布验收通过**）
> 执行者无评审权、无合并权：不 push / 不 merge / 不写 verdict / 不自评审 / 未碰 master

---

## 1. 一句话结论

**本轮是仪器口径对齐轮，不出门结论。** §20 在轮十三任何数据产物之前冻结（`ae237e3`），D1–D6 只做实现、查表与机械验证。产出为「冻结的 5×5 标签映射矩阵 + 与主轨逐字等价的锚点规则 + rubric v4 显式弃权类别 + 统一 cwd 观测面 + 校准复算」。

本轮 `r_main` 标 `caliber = instrument_alignment_calibration_only`；`gate_result = not_evaluable`、`gate_conclusion_issued = false`。不重测门值、不重算门结论、不产出第二个门计数读数、不产出第二个 M_C；报告 `M_C` 数值赋值 0 处、门值数值 0 处。轮十一封存 `R_main = 0.62069` 只作并列参照，冻结不动。

修正后校准读数 `r_main 1.0 / comparable 118` 是**口径修正后的校准值**，一致率上升全部由锚点规则（48 条）与 cwd 观测面（18 条）两处口径修正贡献，可比集由 174 **缩小**到 118、弃权由 226 增到 282；按禁令 3 明确**不叙述为影子轨能力提升**。请评审裁定，执行者不自行裁定。

## 2. 交付清单（D0→D7）

| 阶段 | commit | 交付物 | 关键实况 |
|---|---|---|---|
| 接卡 | `89d56ee` | 卡面 Status | OPEN → IN_PROGRESS，代号 WB，登记编号对齐说明与 V1–V10 / V1–V11 编号差 |
| D0 | `ae237e3` / `ae54fef` | `docs/eval-prereg.md` §20、`.gitignore` 补 `run-dir-r13/` `shadow-r13/` | **冻结早于一切 r13 产物**（签署时 `r13_products_before_freeze = []`）；纯追加 `148/0`，V1 文本口径前缀 SHA `8941bc96…` 前后一致；D20-B 7 条款 + D20-C 3 禁令 + D20-C′ 卡面 6 禁令逐字并入 + D20-D 冻结常量 + D20-E 机器可读 25 格矩阵 |
| D1 | `c734fde` | `tools/eval/label_mapping.py` | 25 格三类映射，`--verify --prereg` 从 §20 **机械读回**；篡改 `E4\|SUPPORT` 一格 → `verify_pass False` 并精确定位，证明读的是冻结文本 |
| D2 / D3 / D4 | `c2347e3` | `tools/eval/independent_judge.py`、`tools/eval/rubric_v4.py`、`tools/eval/r13_alignment.py` | `_ANCHOR_RE` 与主轨 `INTEGER_ANCHOR_RE` 逐字相等；`_anchors()` 三步算法；RUBRIC_V4 四类显式弃权；`_ANCHOR_RE` 别名修正后 legacy 仅留 `_LEGACY_ANCHOR_RE` 供 v2/v3 复算；`rubric_v4.py` 为卡面 D1 明文的独立落点（补齐偏差） |
| D5 | 本次收尾 | `goldset/annotation_r13.jsonl`、`out/r13-annotation-summary.json` | `annotator_count` 机械实测 `1`、`two_human_independent_annotation=false`；第二机械视图标 `mechanical_view=true` 且不计入标注者人数 |
| D6 | 本次收尾 | `docs/eval-report-r13-alignment.md` | 6 节 / **24 条结论 / 38 个方括号指针 + 24 个圆括号指针**，`verify_artifact_pointers.py` → `CONCLUSIONS 24 / COVERAGE 100.0% / BAD_DIGEST 0 / MALFORMED 0 / RESULT PASS` |
| D7 | 本次收尾 | `run-dir-r13/seal.json`、custody 副本、`artifacts.json`、卡转 `IN_REVIEW`、本递评单 | `VERIFY: OK (9 files match the seal)`；`not_true_data=true`；产物哈希在验收重跑后逐字节未变 |

## 3. 关键读数（全部来自亲跑产物）

| 项 | 读数 | 说明 |
|---|---|---|
| 冻结序 | `ae237e3` @ `2026-11-12T22:26:14+08:00` | 前缀 `166693` 字节与基线 blob 逐字节相等；`prereg_prefix_sha256 8941bc96…` |
| 锚点规则 | 修正前差集 56 → **0** | `_ANCHOR_RE.pattern == extract.INTEGER_ANCHOR_RE.pattern` 为 True；`claim_text_calibre_mismatches 0` |
| rubric v4 | 30 / 30 / 48 / 48 四层各命中一个显式类别；`new_unobservable_class_count 0` | `no_evidence → NO_EVIDENCE_LINE`、`incomplete → STRUCTURALLY_UNJUDGEABLE`、`ref_missing → VERIFIABLE_ABSENCE`、`repro_fail → SILENT_FALLBACK_PROTECTED` |
| 布尔→弃权转移 | 56 条，**56/56 归因锚点规则，残余 0** | 逐条留 `legacy_anchors / aligned_anchors`，不是新造不可判类别 |
| 保护性弃权 | `SILENT_FALLBACK 48 + FILE_NOT_FOUND 48 = 96` | 修正前后不变；`ref_missing_upgrade_candidate_rows 48`，本轮未激活为布尔 |
| cwd 观测面 | 18 → **0** | 主轨用 `workspace=` 参数统一，`main_track_source_modified false` |
| 修正前复算 | `0.6206896551724138 / comparable 174 / agree 108 / disagree 66 / abstain 226` | 机制 `{anchor_rule_diff:48, cwd_observation_surface_diff:18}`，`matches_sealed True` |
| 修正后校准 | `1.0 / comparable 118 / agree 118 / disagree 0 / abstain 282` | 四键机制全 0、`other 0`、`no_residual True`；`comparable_delta -56`、`abstain_delta +56` |
| 双标注 | `annotator_count 1`、可比 13 / 一致 13、`1.0` | 与轮十二同 seed 同子集；轮十二可比 22 / `0.590909`；方向诊断，不证明独立性 |
| 门结论 | `not_evaluable`，未 emit 任何门判定 | 无第二个 M_C、无第二个门计数读数、报告门值数值 0 处 |

## 4. Acceptance V1–V11 亲跑退出码（39 条命令，不采纳 precheck）

`round13-custody/acceptance_r13.py` 跑 V1–V9 / V11 共 **33 条**；`round13-custody/verify_r13_v10.py` 在报告生成后跑 V10 及附加检查共 **6 条**。台账 `r13-acceptance.json` / `.log` 与 `r13-acceptance-v10.json` / `.log`。PowerShell 字面命令以 Git-Bash / Python 等价执行，每条记录均注明等价关系。

```
V1  0 / 0 / 0 / 0 / 0        V2  2 / 0 / 0 / 0        V3  0 / 0 / 0
V4  0 / 0 / 0                V5  0 / 0                V6  0 / 0
V7  0 / 0                    V8  0 / 0 / 0            V9  0 / 0
V10 0 / 0 / 0 / 0 / 0 / 0   V11 1 / 1 / 0 / 1        R13 0 / 0 / 0
→ 合计 39 条，非零 4 项：V2_1、V11_1、V11_2、V11_4
```

- **V1**：`prereg_prefix_sha256 8941bc96…`、`has_s20 True`、`clauses 10`；D20-B 7 条 / D20-C 3 条 / 卡面禁令 6 条 / 矩阵 25 格；纯追加 `148/0`；`prefix_equals_baseline True`；冻结 commit `ae237e3` 早于产物。
- **V2_1（exit 2）**：卡面字面 PowerShell 反斜杠路径在 Git Bash 未加引号时 `\e` 被吞 → `can't open file '…\toolsevallabel_mapping.py'`。这是 **shell 路径口径差，不是代码缺陷**；加引号（V2_2）与正斜杠（V2_3）两种等价路径均 exit 0、`UNMAPPED []` / `VERIFY_PASS True`。与轮十 V8 先例同形，照实登记不刷绿。
- **V3 / V4 / V5**：`56→0`、`0 新不可判类别 / protected_total 96`、`18→0` 全部 PASS；V4_2 独立脚本额外给出 `56/56 归因、0 残余、冻结常量与 r13_alignment 一致 True`。
- **V6 / V7**：四键机制枚举全部显式为 0、`other 0`、合计等于分歧总数；`SF 48 / FNF 48 / protected_total 96`；`caliber instrument_alignment_calibration_only`。
- **V8**：`git diff 831a46a -- <11 个完整路径>` 输出为空、退出码 0；`git diff --name-only` 只列出 Owned files。V8_3 当时 `?? goldset/annotation_r13.jsonl`（D5 交付物尚未提交），本次收尾提交后工作树干净，属披露过的瞬态。
- **V9**：字面与等价路径均 `VERIFY: OK (9 files match the seal)`。
- **V10**：`pointers 24 bad 0`；指针验真 `24/24 COVERAGE 100.0% / 38 指针 / 20 唯一路径 / BAD_DIGEST 0 / MALFORMED 0 / RESULT PASS`；`BARE_FILENAME_POINTERS 0`；`M_C_NUMERIC_ASSIGN 0`、`GATE_VALUE_LITERALS []`、`gate_result = not_evaluable`。
- **V11_1 / V11_2（各 exit 1）**：字面 `python -m unittest discover -s tests` 与 `COVENANT_BASH_HINT=1` 均 `Ran 527 tests ... FAILED (failures=2, errors=3)`，根因单一 `RuntimeError: no Git for Windows bash found; refusing to fall back to a bare 'bash' ... set COVENANT_BASH_HINT`，连带 `test_sync_test_count` 的 discovery 失败。**V11_3 改用真实 Git-for-Windows bash 路径另跑 `Ran 546 tests ... OK`（exit 0）**。不刷绿。
- **V11_4（exit 1）**：`LINT: FAIL (0 errors, 2 warnings)` —— `VERDICT_WITHOUT_REVIEW`（执行者不得写 verdict 的直接后果）、`TEST_COUNT_UNVERIFIED`（仓库既有 discovery 问题）。不伪造 verdict、不改红区 `tools/lint_cards.py` 刷绿。
- **R13 附加自检**：`R13_1` 8 份产物在验收重跑后 `byte_identical_after_rerun true / changed []`；`R13_2` 4 个新增脚本 `ast.parse(feature_version=(3,9))` 全过、`BANNED_API_LITERAL_PRESENT False`；`R13_3` 修正前后构成并列。
- **验收执行器自身缺陷留痕（照实登记）**：首次亲跑时 `acceptance_r13.py` 有 6 处内联 `python -c` 多写一个右括号、1 处把 `timeout` 误传给 `list.append`，且 D2 把 `_ANCHOR_RE` 改为主轨等价正则后旧离线探针 `anchor_probe.py` 仍按旧捕获组读取而 `IndexError`。三处均为**执行器 / 探针缺陷，不是产物缺陷**，已逐一修复并用 AST 机械复检（11/11 内联代码可编译、离线探针 `56/0/0` exit 0）后重跑，最终台账为修复后的完整 33 条；首跑日志未写成正式台账，不冒充验收结果。

## 5. 未闭合项（照实登记，交浮香裁定）

1. **双标注降级**：单 agent 环境无法提供两名独立人类标注者，`two_human_independent_annotation=false`、`annotator_count=1`，不记为双人独立；轮十一 ADV-6「独立性不可满足」裁定永久生效。
2. **V2 字面路径 exit 2** 与 **V11 字面单测 exit 1 / 两次、lint --strict exit 1** 共 4 项结构性残留，详见第 4 节，不刷绿。
3. **本轮不出门结论**：`not_evaluable` 未解除；校准 `r_main 1.0` 不是门计数读数，不因此宣布仪器信度达标。
4. **历史冻结读数不重算**：轮十一封存 `R_main 0.62069 / LB95 0.546722` 等一律不改写、不重推，只作并列参照。
5. **`rubric_v4.py` 落点偏差**：卡面 Owned files 明文 `tools/eval/rubric_v4.py`，而首版实现把 v4 全放在 `independent_judge.py` 内；已按轮十二 `rubric_v3.py` 先例补建独立脚本并产出逐条分解，非薄包装。是否在授权内交裁定。
6. **`ref_missing` 升级候选**：48 条 `VERIFIABLE_ABSENCE` 本轮保持弃权，是否可升级为可判 NOT_SUPPORT 需单独立项。

## 6. 交裁定项（执行者不自行裁定）

1. **指令内部张力**：接卡指令 D3 写「ref_missing→缺席可判路径」，与卡面禁令 2 / V7（`protected_total=96` 不得下降）直接冲突。§20 条款 4 按**禁令优先**裁决：只建显式独立路径 + `upgrade_candidate=true`，不激活布尔判定。该取舍是否认可交裁定。
2. **V6 交付物编号差**：接卡指令 D0→D6，卡面 Deliverables D1→D7；Acceptance 指令写 V1–V10，卡面实为 V1–V11。执行者按卡面全量跑 V1–V11，并在卡面「编号对齐说明」逐项登记，不擅自裁剪。
3. **`_ANCHOR_RE` 别名口径**：§20 条款 3 要求该符号与主轨逐字等价，执行者令 `_ANCHOR_RE = INTEGER_ANCHOR_RE`，legacy 交替正则另存 `_LEGACY_ANCHOR_RE` 仅供 v2/v3 复算。是否属「逐字等价」的合理解释交裁定；V3_2 已给机械证明。
4. **验收前修复执行器缺陷的定性**：同轮十二 R26 先例，修复对象是验收脚本与离线探针而非计数产物；`R13_1` 证明 8 份产物重跑逐字节未变、seal 8 份副本哈希全等，属**同一份计数结果的确定性重放**，不是第二次计数。请评审复核该定性。
5. **Owned files 机械追记**：`review/AGNES/XJ-REVIEW-REQUEST-AGNES-20261112-002.md` 由卡面 Review handoff 明文指定；`goldset/annotation_r13.jsonl`、`tools/eval/rubric_v4.py`、`docs/eval-report-r13-alignment.md` 均在 Owned files 内。`.gitignore` 的 `run-dir-r13/` / `shadow-r13/` 追记沿用 D0 先例，不扩大授权、不改 §20 冻结文本。

## 7. 对抗问题正面回答（卡面预置 7 条）

| # | 问题 | 回答 |
|---|---|---|
| 1 | 锚点对齐后是否把主轨判级错误「对齐成一致」、掩盖执行者真实缺陷？ | **否**。改的是独立轨 `_ANCHOR_RE`/`_anchors()`，主轨 `extract.py` / `judge.py` 零改动（V8 空 diff）。48 条 `anchor_miss` 不是变成一致，而是因对齐后无语义锚、按 `explicit_anchor_required=True` **转为弃权**；`V3_BOOL_TO_V4_ABSTAIN 56` 逐条留痕且 56/56 归因锚点规则，可比集缩小而非变大。 |
| 2 | `FILE_NOT_FOUND` 升级为「可验证的缺席」会否与 `SILENT_FALLBACK` 保护逻辑冲突？ | 本轮裁决为**二者同属保护性弃权、不做区别对待**：`VERIFIABLE_ABSENCE` 显式独立路径 + `upgrade_candidate=true`，但 `supports=None`、`error_class=FILE_NOT_FOUND`、`protected_total` 不变。升级需单独立项并交浮香，避免重建轮九伪一致。 |
| 3 | `cwd_probe` 18 条是否说明主轨本身错了、修独立轨掩盖了主轨缺陷？ | 不是源码缺陷。主轨 `reproduce()` 支持 `workspace` 参数，轮十一复算调用方式让两轨落在 root / workspace 两个观测面；本轮由 `r13_alignment.py` 统一传 workspace，两轨同面，`main_track_source_modified false`。这是复算调用口径修正，不是改主轨答案。 |
| 4 | 无锚政策差异（70 条）谁当基准？主轨无锚 E4 是否设计缺陷？ | 以**主轨冻结 E 级为参照、独立轨显式锚要求为自身判级政策**，差异登记为设计政策差异并标 `protected_abstention / subtype=no_anchor_policy`，不放宽弃权迁就主轨。主轨无锚 E4 是否属设计缺陷**不在本卡裁定范围**（禁令 1 不许改主轨），交浮香。 |
| 5 | 修正后一致率显著上升能否排除「调口径把一致率调高」？ | **不能排除，本轮也不主张能力提升**。报告并列修正前后：可比集 `174→118`（−56）、弃权 `226→282`（+56）、分歧 `66→0`；56 条布尔转弃权 56/56 归因条款 3 锚点规则、残余 0；`capability_gain_claim=false`。判别方法即「看分母与弃权构成 + 逐条转移归因」，而非只看一致率。 |
| 6 | `no_evidence` 与 `incomplete` 归为同一不可判类别是否恰当？ | **本轮分开**：`no_evidence 30 → NO_EVIDENCE_LINE`（无证据行）、`incomplete 30 → STRUCTURALLY_UNJUDGEABLE`（证据行非空但三字段全缺）。卡面 6 行初稿第 6 行沿用 v2 的 `PARSE_FAIL` 口径与当前实现不符，已在 D20-A/A-3 登记偏差并以当前实现冻结。 |
| 7 | 映射表是否构成「先看数据再定规则」的 HARKing？ | **不构成**。25 格矩阵、三类语义、`new_unobservable_classes` 定义、四类白名单、分歧机制枚举、双标注降级口径、双格式指针、`gate_result=not_evaluable` 全部写在 §20 冻结 commit（`ae237e3`，`2026-11-12T22:26:14+08:00`）内；冻结脚本自检 `r13_products_before_freeze=[]`；V1 前缀 SHA 与基线逐字节相等、`git diff --numstat 148/0`。D1–D6 只实现与查表。 |

## 8. 纪律与停手声明

§20 冻结 commit `ae237e3` 早于一切 `run-dir-r13/` / `shadow-r13/` / `out/` 轮十三产物；红区 11 项**完整路径**零触碰（7 个仪器在 `tools/eval/`、`gate.py` / `lint_cards.py` 在 `tools/`，写裸文件名会让 diff 假绿），主轨 `judge.py` 仅被只读调用；CI py3.9 下 4 个新增脚本均经 `ast.parse(feature_version=(3,9))`，未给 Path 文本写入方法传 `newline` 关键字，JSON/JSONL 写入一律 `open(..., newline="")`。

本轮**不写 verdict、不 push、不 merge、不自评审、不碰 master**。执行者到此停手，等 Orchestrator 预审 + 浮香 PASS gate；对合宪性、验收通过与否、未闭合项与交裁定项的处置均不自行裁定。
