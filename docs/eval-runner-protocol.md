# 执行协议：两臂去退化 runner 与 M3 门禁探针（v1.1 执行侧）

- **依据：** 卡 XJ-20261024-003（D4）；预注册 v1.1 §7 变更 C1/C3 与三条执行约束
- **地位：** 执行层文档。**不改 prereg**（v1.1 已冻结）；本文与其冲突时以 prereg 为准
- **工具：** `tools/eval/study_runner.py`（两臂执行）、`tools/eval/m3_probe.py`（M3 探针）
- **措辞纪律：** EVO-20261024-001 全文适用——「预注册条件下的对照证据」，禁「证明有效」

## §1 两臂定义（决定 1 的执行侧落法）

两臂共用**同一份草稿**（executor 对每个任务写一次 `claims`），产物语法完全一致
（`- [已验证]` + `证据：cmd=… exit=… out=…` / ref 形式），唯一差异是证据值的来源：

| 条件 | 证据命令执行 | 证据值来源 | 兜底 |
|---|---|---|---|
| A（门禁全开） | **runner 真执行**（复用判定器同款 `judge.run_command`） | 真实 exit code + 真实输出前缀行 | 评审 + 门禁 |
| B（无兜底） | **runner 零执行**（协议层禁止，见 §3） | executor 草稿里的 believed 值原样落笔 | 无 |

这样 M1 分母（E2+E3+E4）在两臂都非空（C1 的去退化目标），判定器用同一套规则
区分两臂；B 臂证据是否撑得住，由判定阶段统一复跑揭晓——B 臂写对的算它知识
真准，写错的落 E2/E3，这正是被测量的失败模式。

## §2 执行者与去污染（决定 2）

- 第二轮两臂执行者：**ZCode**（sir 2026-10-24 拍板）。作者 Jarvis 已在首轮真跑过
  全部命令，不得再执行任何一臂。
- **草稿先于一切执行**：executor 必须在调用 runner 之前写完全部草稿。草稿写入时
  点是污染边界——之后发生的任何执行都改变不了草稿。
- 派单顺序：先 `--condition B` 后 `--condition A`（或一次 `both` 亦可，因为草稿是
  输入、runner 不会中途询问 executor）；两个条件用同一 `--drafts-dir`。

## §3 B 臂零执行（硬约束的落法）

1. **协议层**：`run_arm` 的 B 路径不存在任何 `judge.run_command` 调用点——不是
   "默认关"，是代码路径上没有。
2. **零到什么程度**：B 臂连 acceptance 命令也不执行（见 §5 的 coverage 政策），
   B 臂运行全程零子进程。
3. **执行痕迹**：`run-log.json` 记录 runner 产生的每一条执行/拒绝记录（A 臂）。
   B 臂运行后 run-log 的 B 记录必须为空；CLI 在 B 臂发现非空时直接
   `EXIT_FAIL`（防携带/篡改的旧记录混过）。
4. **诚实回退**：A 臂命令被拒绝清单拦截、超时或无法启动时，**绝不伪造
   exit/out**——证据行回退为纯命令形式（判定时结构性 E1），run-log 记录原因。
   缺失的观察必须保持缺失。

## §4 草稿与产物契约

### 4.1 草稿（executor 写，`<drafts-dir>/T##.json`）

```json
{
  "task_id": "T01",
  "answer": "MIT",
  "acceptance_ok": true,
  "notes": "可选：执行说明",
  "claims": [
    {"text": "断言文本（含锚）", "cmd": "命令",
     "believed_exit": 0, "believed_out": "预期输出片段"},
    {"text": "断言文本", "ref": "仓库相对路径"}
  ]
}
```

- `answer` → 产物末尾 `答案：` 行；`acceptance_ok` 仅在 **B 臂 command 型任务**
  的 coverage 生效（§5）。
- `believed_exit` / `believed_out` 只进 B 臂；A 臂一律以真实执行结果为准，草稿
  里的 believed 值被忽略。
- 证据语法是单行且 `out=` span 内不得含反引号——两臂共用同一 normalize
  （取第一条非空且无反引号的输出行，截断到 500 字符）。语法约束对两臂对称，
  不构成臂间差异。

### 4.2 产物与 run-data

产物：`<out>/products/<task>-<condition>-r<N>.md`。
`run-data.json` 字段契约 = `blind.py:load_run_data`（key / task_id / condition /
repetition / product / coverage），另加只读的 `summary`（§6 对称性检查数据）。

### 4.3 run-log

`run-log.json`：`{generated_utc, workspace, records[]}`，每条记录
`{key, task_id, condition, kind: "evidence"|"acceptance", command, executed,
exit_code, refused, error, utc}`。这是事后核验「两臂差异是否只有执行」的唯一
机读痕迹；B 臂记录恒空。

## §5 coverage 政策（一处已知不对称，提请 adjudicator 裁定）

- **answer 型（T01-T10, T21-T30）**：两臂同法——产物含与 `acceptance.value`
  精确一致的 `答案：` 行即 covered，零执行。
- **command 型（T11-T20）**：
  - A 臂：runner 执行任务定义里冻结的 acceptance 命令（它属于任务定义，不属
    断言证据面），exit == expect_exit 即 covered，执行入 run-log（kind=acceptance）。
  - B 臂：**不执行**，coverage 取草稿 `acceptance_ok` 自报值。

不对称说明：B 条件的定义就是「无验证兜底」，自报 coverage 是该条件下的诚实
形态；若在 B 臂也执行 acceptance 命令，B 臂就不再零执行，§3 的红线与卡面
「B 臂必须为空」直接冲突。两害相权取后者，并在此显式登记供评审裁定。

## §6 对称性检查（v1.1 附加执行约束 1）

`run-data.json` 的 `summary[arm].tasks_with_evidenced_claim` 即卡面要的数据：
若 B 臂出现大面积零证据任务，该轮判定为**再次退化**，不得进入配对分析。
runner 只产出数据，判定「是否退化」属报告层。

## §7 M3 门禁探针（C3 的可执行定义）

`python tools/eval/m3_probe.py [--json]`，全部在一次性临时目录中构造 fixture
轮次，**子进程调用真实 `tools/gate.py` / `tools/lint_cards.py`**（探针不重实现
任何规则，观察面只有退出码与工具自己的 `--json` 违规列表）：

| 类 | 缺陷 | 调用 | 期望 |
|---|---|---|---|
| M3-1 | MISSING_VERDICT | gate `--require`（无 verdict 文件） | 拦截 |
| M3-2 | STALE_VERDICT | gate + artifact-map（产物晚于 ts） | 拦截 |
| M3-3 | PASS + blockers>0 | gate（真实违规码 BLOCKERS_PRESENT） | 拦截 |
| M3-4 | UNMAPPED_CLAIM_SURFACE | lint `--strict`（WARN 升 ERROR；`--allow-orphan-id` 隔离无关告警） | 拦截 |
| M3-5 | LINK_VERDICT_SHA_MISMATCH | gate + `.freeze/link-*.json` 哈希不符 | 拦截 |
| M3-6 | 干净轮次 | gate 与 lint `--strict` 双跑 | **放行（误拦=0）** |

`M3: PASS` 当且仅当 M3-1..5 全拦 **且** M3-6 双工具 exit 0。M3 未跑的轮次按
v1.1 附加约束 3 标注端点缺失。

## §8 成本与失败处理（prereg §4 全文适用）

- **无重试**：命令失败/超时/被拒一律原样记录，禁止跑挂再跑挑好的。
- 单命令超时默认 120s（`--timeout` 可调）；拒绝清单沿用 `judge.COMMAND_DENYLIST`
  冻结文本（import，不复制）。
- 单任务判定预算（10 分钟）属判定层，runner 不重复实现。
- 失败样本全量保留进 run 产物，禁只报聚合分。

## §9 第二轮运行 runbook

1. `run.py --selftest` 全绿（自检前置，prereg §5.5）+ `study_runner --selftest`。
2. executor（ZCode）写完全部 30 份草稿（`--drafts-dir`）；**此刻起草稿不可再改**。
3. `m3_probe.py` → 记录 M3 结果。
4. `study_runner --condition B --drafts-dir … --out <run-dir>`（B 先）。
5. `study_runner --condition A --drafts-dir … --out <run-dir>`（后）。
6. 核对 `run-log.json`：B 记录为空、A 记录数 = A 臂命令型证据断言数 + command
   型 acceptance 数。
7. `run-data.json` summary 对称性检查（§6）→ 通过后 `run.py --package <run-dir>`。
8. **密封**：打包前 `python tools/eval/seal_run.py <run-dir> --move-to <custody>`
   对整个 run 目录取 SHA-256 清单（§11）；核对 `VERIFY: OK` 后把 seal.json 与
   custody 副本一并移交 sir。

## §10 边界与已知局限

1. runner 不判题、不盲化、不植入对照组（`run.py`/`blind.py`/`controls.py` 职责不变）。
2. run-log 不是密码学封印：executor 事后补造假日志在工具层无防线；当前防线是
   草稿先行的污染边界（§2）+ runner 结构性零执行（§3）+ run 目录移交 sir 保管。
   若 adjudicator 认定需要更强保证，后续卡可把 run 目录纳入 `.eval-sealed/` 同款
   密封流程——本卡不扩权。
3. coverage 的 command 型不对称（§5）已登记，报告须显式引用本节。
4. 探针的 fixture 构造是「规则感知」的（要构造过期就得动 mtime），但一切判定
   都出自真实工具；探针零规则复实现是卡面红线，由测试监视子进程调用面守卫。

## §11 运行密封（XJ-20261024-004，闭合 §10.2 的可检出部分）

**边界先行**：密封是**可检出改动**（tamper-evident），**不是防篡改**
（tamper-proof）。它不回答「谁的日志是真的」，只回答「封存之后动过没有」。
无签名、无私钥设施；以下三条局限是能力边界本身，引用本节时必须连同引用：

1. **seal.json 自身无防线**：能写 run 目录的人也能重写 seal.json（重算全部
   哈希）让改动隐身。缓解靠保管而非密码学——seal.json 必须离开执行者的写权限
   （移交 sir / custody），否则密封只对无写权限的改动方有意义。
2. **整体替换不可检出**：换上另一份「内容 + 哈希自洽」的目录，verify 照样
   通过。哈希清单只证明**恒定**，不证明**来源**；把目录绑定到「产生它的那次
   运行」的是 custody 链，不是哈希。
3. **封住的谎言仍是谎言**：密封发生在运行结束时；runner 封存前记录了什么，
   由 §2 污染边界 + §3 零执行 + 事后交叉核对约束，密封工具不在其覆盖内。

### 11.1 何时密封

runbook（§9）第 7 步对称性检查通过之后、`run.py --package` 之前：此时证据面
（run-data.json / run-log.json / products/）已定形，而打包操作尚未来得及引入
任何中间态。密封后 run 目录即视为**只读**——后续任何阶段（打包、判定、评审）
若需要动它，必须在 seal 之外留痕并重新核对。

### 11.2 怎么密封

```bash
python tools/eval/seal_run.py <run-dir> --move-to <custody-dir>
python tools/eval/seal_run.py --verify <run-dir>   # 之后任何时点，0=一致 / 1=漂移 / 2=用法错误
```

- 产出 `seal.json`：每个文件的 posix 相对路径 + SHA-256 + 字节数，外加
  `sealed_at_utc` / `file_count` / `root_label`；seal.json 自身不入清单（自指）。
- 哈希流式分块（1 MiB），目录大小只受磁盘约束；纯 stdlib，工具自身零子进程。
- `--move-to` 是**复制**不是移动：原件留在执行侧原地不动，密封副本 + seal 落入
  custody，复制后立即对副本重验。custody 目标已存在时拒绝（append-only）。

### 11.3 seal.json 的保管（两种放法的攻击面）

- **留在 run 目录内**：方便——verify 随手可跑；但执行者对目录仍有写权限时，
  局限 1 完全敞开，密封退化为「提示牌」。
- **单独移交 custody（本协议的取法）**：runbook 第 8 步用 `--move-to` 一步做到
  「副本 + seal 同时落入执行者写不到的地方」。此后即便 run 目录原位被改，sir
  手里的 seal.json 仍能逐字节指出改了什么。要攻破就得出 custody 链的假——
  那已经是局限 2 的范畴，诚实记录，不谎称密码学可解。
