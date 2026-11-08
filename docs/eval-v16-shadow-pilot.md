# v1.6 影子试点试运行报告（XJ-20261108-001 D5）

> **如实声明（卡 D3 明文，全文适用）**：本文所载全部读数来自**合成样例试运行**（验证编译器/对齐器机械正确性），**不是 `docs/eval-prereg.md` §12 D4 定义的影子试点本身**——§12 D4 的一致率证据需要真实执行者在真实轮次中产出结构化记录，随 v1.6 下一轮执行发生。**本报告的任何读数不得被表述为 §12 D4 的一致率达标证据。**

## 0. 边界声明

- 本报告不含新判定：E 级判定唯一权威是 `tools/eval/judge.py`，主轨仪器（extract.py 抽取 → judge.py 判级）零改动（卡 D4：主轨文件对基线 15a6de1 diff 为空）。
- 影子轨隔离：对齐器输出**不产生任何 E0–E4 端点数字**、不含判级序列——逐条输出只有「与主轨一致/不一致」布尔与缺口三分类（实现与报告双面核查，见 tests/test_shadow_align.py::IsolationTests）。
- 第五轮密封判级零重判（C12）：本试运行只读 `pkg-beecf4ed` 的判级原文（作主轨级别快照）与产物正本（作抽取面）；执行面全部为**合成验证命令**（`python -c` 只读探针）。
- 单 adjudicator 局限口径沿用：合成样例的预期结果由执行者构造，无法交叉验证——本试运行只验证机械正确性，不构成对一致率门（≥95%）的任何评估。

## 1. 交付物与使用方法

| 交付物 | 入口 |
|---|---|
| 编译器（D1） | `python tools/eval/dsl_compiler.py --records <JSON> --root <dir> [--out <JSON>]`；`--selftest` 内嵌 9 predicate 各 ≥1 正 1 反自检（22 checks，exit 0） |
| 影子对齐器（D2） | `python tools/eval/shadow_align.py --main <JSON> --records <JSON> --root <dir> [--out <JSON>]`；`--selftest` 内嵌对齐率/缺口分类自检（10 checks，exit 0） |
| 输入格式 | 两文件均为 `{产物码: [记录]}` JSON——main = `extract_claims().to_dict()` 快照（附密封判级 level）；records = §12 八字段结构化记录 |
| 试运行脚本 | `dryrun/v16-shadow-pilot/run_pilot.py`（本地，`dryrun/` 已 gitignore；机读产物 `main-snapshot.json` / `records-synthetic.json` / `alignment-result.json`） |

**编译器使用要点**（零裁量边界）：
1. 编译器不含自然语言理解/语义相似度——「自由文本 → 结构化记录」由被测执行者承担，编译质量是影子试点要测的对象；
2. `predicate` ∈ §12 冻结 9 值（封闭集合，覆盖缺口走「披露 → §12 追记 → 向前生效」）；
3. `claim_type=evaluative` 不得携带 predicate（§12 D2，构念外，不入对齐一致率分母）；
4. `verification_command` 与 `artifact_path` 二者必居其一（≤1 条命令）；`exists`/`not_exists` 走 artifact 面，`exit_equals`/`exact_answer` 走命令面（实现语义，已入 schema 校验）；
5. `exact_answer` = 验证命令输出与期望答案文本**精确比对**（仅尾随换行归一）——语义等价路径不存在，测试样例「MIT」vs「MIT License」断言其不得通过；
6. `matches_regex` 限 Python re，在 30s 超时罩的子进程内执行，超时按观察失败留痕并记 `regex_timeout` 旗标；
7. `json_path_equals` 仅支持点分路径取值（无 jq 依赖），编译器冻结约定 `expected = "<dotted.path>-><value>"`，其余形态记 `json_path_convention_missing` 旗标不猜测。

## 2. 试运行读数（D3）

试运行输入：第五轮密封包 `pkg-beecf4ed` 全 180 产物正本的主轨抽取面（900 条判级原文联接）+ 合成结构化记录 **158** 条；对齐**试运行范围** = 30 个抽样产物（169 条主轨断言；每 6 个 P 码取 1）。

| 读数 | 值 | 说明 |
|---|---:|---|
| 合成记录 | 158 | ≥30 达标；覆盖 predicate 9 值 × 正反双例、claim_type 5 枚举 |
| 一一对齐对 | 154 | 对齐率 = 154 / max(158 记录, 169 主轨断言) = **0.9112**（试运行范围口径） |
| 可比对 | 132 | 排除 evaluative 面（2 条）与锚缺口 |
| 判级一致率 | **0.9848**（130/132） | 仅有的 2 处不一致 = **故意构造的语义失败样例**（FAIL-semantic-1/2） |
| 全包分母参照 | 900 | 合成样例按设计不可能覆盖整轮（30/180 产物抽样），全包口径对齐率 0.1722 仅作范围说明 |

覆盖面：predicate 9 值全部出现（`no_such_predicate` 仅来自故意 schema 失败样例）；claim_type 5 枚举全部出现（4 个可测面 + evaluative 独立桶 2 条）。

**故意失败样例（6 条）逐一定位**：

| 样例 | 缺口类 | 机制 |
|---|---|---|
| FAIL-syntax-1 / FAIL-syntax-2 | `syntax` | evaluative 携带 predicate / predicate 不在冻结枚举 → schema 校验拒绝，不执行 |
| FAIL-anchor-1 | `anchor` | span [9000, 9001) 无主轨断言 → 一对一对齐失败 |
| FAIL-anchor-2 | `anchor` | 宽 span 覆盖 4 条主轨断言 → 多对一，按对齐规则记缺口（连带其覆盖面上未另设记录的主轨断言记为未覆盖——一对一双侧计数口径） |
| FAIL-semantic-1 / FAIL-semantic-2 | `semantic` | 对齐可比但 predicate 结果与主轨判级矛盾（E4 断言配失败谓词 / 非 E4 断言配成功谓词） |

**试运行范围发现（非故意构造，对齐器如实上报）**：anchor 缺口合计 24 = 故意 4（anchor-1/2 及语法样例的对齐面）+ **20 条对齐到 E1 主轨断言的记录**——主轨断言证据链不完整（E1）时影子判据无可比对面，按对齐规则归锚类。这一分类行为与冻结规则一致，供 v1.6 真实试点预案参考。

## 3. 一致率门的正确读法

- §12 D4 的双一致率 ≥95% 门针对**真实影子试点**；本试运行是合成样例的机械正确性验证——一致率 0.9848 反映的是「合成样例与对齐器/编译器的机械行为符合预期」，其中 2 处不一致是**故意放入的**。
- 冻结前置清单第 3 条（编译器实现 + 影子试点一致率报告）由本卡补齐**实现半边**；真实试点随 v1.6 下一轮执行发生，其读数另行出具。
- 本报告不触发 §12 D4 门的通过/不通过裁定，不产生端点数字，不触发重判。

## 4. 局限

1. 合成样例的预期结果由执行者构造（单 adjudicator 口径），机械正确性之外的效度无法在本试运行中测量；
2. 抽样范围 30/180 产物——全包口径的对齐率（0.1722）是范围事实，不是质量读数；
3. 对齐按行区间一对一口径，产物中同源行多断言的场景归锚类（本轮 20 条 E1 面记录即此类），真实试点需在样例规范中预写 claim_id 对齐约定以减少此类缺口；
4. 编译器词法面（CRLF/空白归一、编码边界）未在 predicate 层引入归一化——`out=` 精确子串口径在 §1 冻结不变，边界情形由 `out_encoding_miss` 旗标（v1.5.1）留痕，本试运行未触发。

---
*交付：XJ-20261108-001（D1 编译器 / D2 对齐器 / D3 试运行 / D5 本报告）。判级权威：`tools/eval/judge.py`（零改动）；预注册本体：`docs/eval-prereg.md` §12（零触碰）。*
