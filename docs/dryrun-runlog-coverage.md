# D3 实测报告：run-log v2 的执行痕迹覆盖范围

- **卡**：XJ-20261030-002 / D3
- **采集日期**：2026-10-30
- **采集者**：minimax code（本卡实现者）
- **对象**：`tools/eval/run.py --exec` 记录执行 wrapper + `tools/eval/runlog.py`（run-log v2）
- **实验目录**：`dryrun/d3/`（临时，未跟踪，不在触碰面内）

---

## 0. 结论

> ## wrapper 覆盖范围内：逐项与实际执行一致（9/10 项一致，1 项失真）
> ## wrapper 覆盖范围之外：**未被覆盖**——执行者自带工具的执行与落盘不在 run-log 内
> ## 绕过面计数：**6 类「绕过面未覆盖」** ＋ 1 类「部分覆盖」（进程树身份）＋ 1 类「失真」（`cwd` 字段），逐项见 §3
>
> 由此得到本报告最重要的一条读数：**「run-log 零记录」不能单独充当「该臂未执行」的
> 佐证**。它只说明「没有命令经 wrapper 路由」。要让零记录成为有效佐证，必须由
> 权限层把执行者的执行面关掉（见 `docs/dryrun-b-arm-tool-deny.md`），
> 或者由协议明文要求两臂的执行只能经 wrapper 发生并给出强制手段。

本报告不宣称第四轮可开跑；结论汇总见卡内 `## dry-run 结论`。

---

## 1. 实测方法

对**每一条命令**做两次执行：

1. **经 wrapper**：`python tools/eval/run.py --exec "<命令>" --runlog <run-log> --condition A --task-id T11 --key T11-A-r1 --exec-cwd <run-dir>`；
2. **直跑（对照真值）**：同一条命令、同一个 cwd，直接 `subprocess.run(shell=True)` 执行。

随后把 run-log 里的 `exit_code` / `stdout_summary` / `cwd` / `executed` / `refused`
与真值逐字段比对。**比对对象是同一台机器上的同一条命令**，因此任何差异都是记录
失真，而不是环境差异。

样本任务取自冻结的 30 任务清单的代码层形态（T11 命令型任务），实验只落 `dryrun/`
临时目录，**未写入真实 run 目录**（卡面约束 2）。

复跑命令（评审可直接执行，全部使用仓内工具）：

```powershell
python dryrun/d3/runlog_coverage_probe.py     # exit 0
python dryrun/d3/runlog_followup_probe.py     # exit 0
```

---

## 2. 逐项实测结果

`runlog_version: 2`，共 8 条记录（`dryrun/d3/run/run-log-exec.json`）。

| # | 用例 | 实测 | 判定 |
|---|---|---|---|
| C1 | 简单命令 `python -c "print('hello-wrapper')"` | 记录 `exit_code=0`、`stdout_summary='hello-wrapper'`；直跑真值 exit 0、stdout 相同 | **已被覆盖** |
| C2 | 非零退出 `python -c "import sys; sys.exit(3)"` | 记录 `exit_code=3`，与真值一致 | **已被覆盖** |
| C3 | 命令自行切换 cwd（`cd /d <dir> && echo ... > cwdprobe.txt`） | 记录 `cwd` 仍是 wrapper 的 `--exec-cwd`（`…\dryrun\d3\run`），而文件实际落在 `…\dryrun\d3` | **失真（GAP）**：`cwd` 字段记录的是「wrapper 在哪启动」，不是「命令在哪执行」 |
| C4 | 拒绝清单命中的命令 `rm -rf /` | 记录 `executed=False`、`refused='rm -rf'`、`exit_code=None`；wrapper 退出码非零；**命令未执行** | **已被覆盖** |
| C5 | 不存在的命令 `this_command_does_not_exist_xyz` | 记录 `executed=True`、`exit_code=1`、`refused=None`、`stderr_summary` 非空（`'…' is not recognized…`） | **已被覆盖（附注）**：Windows 下 `shell=True` 经 `cmd.exe`，「无法启动」被 shell 归一为「跑了但失败」，`error`/`could not start` 分支在本机不可达；拒绝与失败仍可由 `refused` 字段区分 |
| C6 | 命令派生子进程（子进程成功） | 记录 `exit_code=0`，子进程退出状态**传递**到外层 | **部分覆盖**：退出状态覆盖，**进程身份未覆盖** |
| C6b | 子进程自身以 7 退出（`check=True`） | 记录 `exit_code=1`（外层），**内层 7 不可见** | **未覆盖**：run-log 只存顶层命令行，无进程树 |
| C7 | 后台进程（继承 wrapper 的管道） | wrapper 实测耗时 **45.3s**（命令内睡眠 45s），退出后才返回；检查时无残留子进程 | **已被覆盖**（无「假完成」记录），但**代价**：后台化作业会让 wrapper 阻塞整段时长 |
| C8 | 超长 stdout（900 字符） | `stdout_summary` 截断至 500 字符，`stdout_truncated=true` | **已被覆盖**（截断标志显式） |
| Q1 | 后台进程**继承**管道 | wrapper 耗时 **20.3s**（子进程 20s）→ 等待子进程结束 | **已被覆盖** |
| Q2 | 后台进程**脱离**管道（`spawn_detached.cmd`，输出重定向到 `nul`） | wrapper 耗时 **0.3s** 记录 `exit=0` 即返回；子进程检查时刻仍在运行 | **未被覆盖**：记录声称完成时，实际执行仍在进行 |

> C7/Q1/Q2 三例说明的是同一件事的两面：wrapper 会等**继承管道**的子进程，因此不会
> 写下假「完成」；但**完全脱离管道**的后台进程可以存活于记录之外。Q2 是本次实测
> 复现出的**唯一一条「记录与实际不符」的绕过面**。

### 2.1 交叉核对表（脚本原样输出）

```
=== cross-checks ===
  [PASS] C1 recorded exit == real exit  (0 vs 0)
  [PASS] C1 recorded stdout prefix == real stdout prefix  (recorded='hello-wrapper' real='hello-wrapper')
  [PASS] C2 nonzero exit is preserved  (recorded=3 real=3)
  [GAP] C3 recorded cwd == cwd the command actually used  (recorded=...\dryrun\d3\run actual_file=True)
  [PASS] C4 refused command recorded as not executed  (executed=False refused='rm -rf')
  [PASS] C5 unknown command: recorded as ran-and-failed, not refused  (executed=True refused=None exit=1 stderr=...)
  [PASS] C6 child exit status propagates to the record  (outer exit=0)
  [PASS] C6b inner child exit code (7) is NOT visible in the record  (record exit=1 (inner was 7))
  [PASS] C7 wrapper waited for the background child (no false 'done')  (wrapper elapsed 45.3s for a 45s child; survivors at check time: count=0)
  [PASS] C8 stdout summary truncated, flag set  (len=500 flag=True)
```

---

## 3. 绕过面逐项标注

下表是本报告的主体。判定口径：

- **已被覆盖**：该行为进入 run-log v2（或能由其推导）。
- **绕过面未覆盖**：该行为**不进入** run-log v2，且无法由其推导。

| # | 绕过面 | 是否进入 run-log | 依据 |
|---|---|---|---|
| B1 | **执行者自带 Bash 工具的执行**（agent 直接调 Bash，不经 `run.py --exec`） | **绕过面未覆盖** | run-log 只在 wrapper 进程内写；agent 自发调用不经过该进程 |
| B2 | **执行者自带 Write/Edit 工具的落盘** | **绕过面未覆盖** | 工具写文件不产生命令，也不产生子进程记录 |
| B3 | **MCP 工具的调用与副作用**（浏览器、网络、连接器） | **绕过面未覆盖** | 同 B1/B2；且工具名与内置工具不同，需单独标注（见 D2 §6.2） |
| B4 | **网络下载落临时目录**（`%TEMP%`、app 缓存、用户目录） | **绕过面未覆盖** | 落点不在 run-dir，也不经 wrapper；既不进 run-log，也不进密封（见 `docs/dryrun-seal-capture.md` §4） |
| B5 | **子进程/进程树的进程身份与内层退出码** | **部分覆盖**（仅外层退出状态） | C6 / C6b 实测 |
| B6 | **脱离管道的后台进程** | **绕过面未覆盖** | Q2 实测：记录 `exit=0` 时进程仍在跑 |
| B7 | **命令的实际工作目录** | **失真**（字段记录 wrapper 的 cwd） | C3 实测 |
| B8 | **运行器自身（runtime）的旁路写入**（会话记录、sqlite、日志、缓存） | **绕过面未覆盖** | 这些写入在 `~/.minimax` 与 `%APPDATA%\MiniMax` 下，与 run-dir 无关 |
| B9 | **手写/编辑 run-log 文件本身** | **不适用（另有一道仪器防线）** | `runlog.py` 对不可解析的既有日志拒绝覆盖；run-log 落 run-dir 内时随 run 密封（见 D4） |
| B10 | **拒绝清单之外的命令**（如 `curl` 之外的任意网络/写盘命令） | **已被覆盖（但只是被记录）** | wrapper 记录一切非拒绝命令；拦截靠 `judge.COMMAND_DENYLIST`（冻结文本，import 不复制） |

---

## 4. 最关键的一条读数：B 臂「零执行记录」的证据力

prereg v1.3 约束 1 写的是：「B 臂『凭知识写证据』的判定以 run-log **零执行记录**为
佐证（第三轮 `run-log-r3.json` 先例：B 臂 0 条执行记录、A 臂 126 条）」。

本报告实测表明：

1. 该证据形式在**第三轮形态**成立——第三轮执行者是 `study_runner` 驱动的
   `judge.run_command`，B 臂路径上**代码里就没有执行点**（协议 §3.1），所以
   「0 条记录」与「没有执行」是同一件事。
2. 该证据形式在**第四轮形态**不再自动成立——第四轮执行者是**带工具 agent**，
   它有独立的 Bash/Write/Edit/MCP 通道（B1–B3）。此时「0 条记录」与「没有执行」
   **可以同时为真而记录为空**。
3. 因此：**B 臂的零记录只有在执行面被硬禁时才具备证据力**。D2 已实测权限层硬禁
   可行（`HARD_DENY_OK`），故闭合路径存在：
   - B 臂：整工具 deny（含 MCP 服务器级 + 只读面视裁定）→ 零记录 = 真零执行；
   - A 臂：执行者**只能**经 wrapper 执行 → A 臂记录条数 = A 臂实际执行次数。
4. A 臂若不封堵 B1（执行者自带 Bash），则 A 臂记录条数**系统性低估**其真实执行量；
   A/B 两条记录数的对比（多 vs 0）会同时被 B1 放大与失真。

> 附带一条实践约束：wrapper 会等待**继承管道**的子进程（C7/Q1），因此第四轮
> runbook 不能把长时后台作业交给 wrapper，否则单条记录会挂住整个轮次。

---

## 5. 建议（协议补丁提案，需 adjudicator/sir 裁定，本卡不自行扩权）

1. **协议 §13.2 增补一条「执行面封堵」条文**：两臂执行者的工具调用一律经
   `run.py --exec`；agent 自带 Bash/Write/Edit/MCP 在两臂均不可直接使用
   （实现手段见 D2 §3 的 deny 规则 + 允许规则）。
2. **B 臂 deny 规则的预置清单**写入执行卡，并注明工具名为运行时精确名、MCP 用
   服务器级写法（D2 §6.2）、只读面取舍（D2 §6.3）。
3. **`cwd` 字段语义澄清**：run-log v2 的 `cwd` 语义是「wrapper 启动目录」。
   建议在协议里写明「命令自行切换目录属执行者违规，不得依赖 run-log 的 cwd 字段
   还原实际执行位置」；本卡不改 `runlog.py`（红区）。
4. **后台进程纪律**：wrapper 不保证捕获脱离管道的进程；执行者若需后台作业，
   产物必须落在 run-dir 内并在密封前归并。

---

## 6. 复跑配方

评审可直接在仓内复跑（不需要本卡的实验脚本）：

```powershell
# 单条命令走 wrapper，看记录长什么样
python tools/eval/run.py --exec "python -c \"print('hello-wrapper')\"" `
  --runlog dryrun/d3/run/run-log-exec.json --condition A --task-id T11 `
  --key T11-A-r1 --exec-cwd dryrun/d3/run
# -> exit 0；run-log-exec.json 增加一条记录

# 被拒绝的命令：只记录，不执行
python tools/eval/run.py --exec "rm -rf /" `
  --runlog dryrun/d3/run/run-log-exec.json --condition A --task-id T11 `
  --key T11-A-r1 --exec-cwd dryrun/d3/run
# -> exit 非零；记录 executed=False, refused='rm -rf'

# 完整矩阵（8 用例 + 2 追问）
python dryrun/d3/runlog_coverage_probe.py    # exit 0
python dryrun/d3/runlog_followup_probe.py    # exit 0
```

脚本与输出位于未跟踪的实验目录 `dryrun/d3/`：
`runlog_coverage_probe.py`、`runlog_followup_probe.py`、`count_bg.ps1`、
`spawn_detached.cmd`、`sleeper.py`、`probe-output.txt`、`followup-output.txt`、
`d3-results.json`、`d3-followup.json`。

---

## 7. 边界声明

- 本报告只测量**记录机制与实际执行的一致性**，不测量任何模型行为或效果。
- C3/Q2 等失真与绕过面均为**机制层面的边界**，不代表第四轮一定发生；反之，
  它们意味着「run-log 零记录」在第四轮**需要额外条件**才具备证据力。
- 未改动任何红区文件：`tools/eval/runlog.py`、`tools/eval/run.py`、
  `tools/eval/judge.py` 均只读调用。
