# 机制闭合轮（零数据）脚本化预案

- **卡**：XJ-20261031-001 / D4
- **日期**：2026-10-31
- **性质**：**预案**——闭合 XJ-20261030-002 条件 C4（取证补强，备选 A 形态）。
  **本卡不执行闭合轮**（卡面约束 3：闭合轮由第四轮执行卡触发）；闭合轮本身
  不出卡不评审（纯机制预演），但其 PASS 判据（§3）可被第四轮执行卡引用。
- **输入**：`docs/b-arm-permission-profile.md`（B 臂规则预置配方）、
  `docs/executor-update-freeze.md`（C3 轮次前冻结）、
  `docs/dryrun-b-arm-tool-deny.md` §4（permission.enforcement 记录面）、
  `docs/dryrun-seal-capture.md`（密封捕获与 H1–H7 隐藏面）、
  `docs/eval-runner-protocol.md` §13.1/§13.2。

---

## 0. 目的与边界

**目的**：在真实 30 任务测评前，用 1–2 个代码层任务（建议 T11 命令型 + 一个
`products/` 落盘型）做**零数据 dry 轮**，机械验证「**封堵 → 记录 → 密封 →
解封 → 判定**」全链闭合。

**硬边界**（违反任何一条即闭合轮无效）：

1. **不出任何 E 级数据**：不触发 E 级判定（判定器不进闭合轮命令序列），
   闭合轮产物不进 `artifacts.json` newest 位、不写 verdicts；
2. **不触碰 run-data**：闭合轮工作目录只在 `dryrun/closure/`（仓内未跟踪）或
   **仓外临时目录**，不写入任何正式 run 目录；
3. 不启动 30 任务实跑——闭合轮只有 1–2 个任务的机制动作，不产生测评结论；
4. 术语纪律 EVO-20261024-001 适用：闭合轮只证**机制动作**（工具被拒、记录落盘、
   封签校验），不产出任何效果表述。

---

## 1. 前置条件（闭合轮启动时核验）

| # | 前置 | 依据 |
|---|---|---|
| P0-1 | C3 冻结完成：`docs/executor-update-freeze.md` §2 V1–V3 全 exit 0（正式轮必做；闭合轮建议先行，若未冻结须在闭合轮记录中登记未冻结状态） | 002 verdict C3 |
| P0-2 | B 臂 profile 配方复核：`docs/b-arm-permission-profile.md` §2.2 探针在当轮环境复跑 exit 0；MCP server 清单重新枚举 | 002 verdict C2「预置后开跑前复跑 compact_probe」 |
| P0-3 | 环境事实：仓内工具带 `COVENANT_BASH_HINT=D:\AI\Git\bin\bash.exe` 跑，否则假红（卡面约束 5 同款） | 本仓约束 |
| P0-4 | `permission.json` 环境基线：两臂共用环境核验 `permission.json` 不存在（或 deny 为空）——闭合轮结束时以此复原 | profile §4 步骤 4 |

---

## 2. 触发命令序列（预案：每步命令 + 预期输出 + 退出码）

工作目录约定：`$W = dryrun/closure`（或仓外临时目录），`$W/run` 为闭合轮 run-dir
（内含 `run-data.json` + `products/<task-id>/`，§13.1 目录约定）。

### S0 落点与 run-dir 骨架

```
mkdir -p $W/run/products/T11
# 预期：目录建立；$W 不在 git 跟踪面（git status 不出现 $W）
```

### S1 封堵生效 + 取证（B 臂）

1. 按 `docs/b-arm-permission-profile.md` §4 注入 deny 规则（会话级优先）；
2. B 臂会话执行 1–2 个代码层任务（执行者尝试 `bash`/`write`/`read` 等）；
3. 取证：会话记录中的 **`permission.enforcement`** 结构化记录非空
   （字段含 `session_id` / `turn_id` / `tool_call_id` / `tool_name` /
   `policy_behavior: 'deny'` / `gate_result: 'blocked'`；
   `docs/dryrun-b-arm-tool-deny.md` §4）。记录落盘路径以执行卡启动时实测为准
   （002 D2 只固化了记录面存在性，未固化磁盘路径）；
4. 引擎层旁证：复跑 profile §2.2 探针（exit 0 = 12 规则两模式全 deny）。

```
预期：permission.enforcement 记录 ≥ 1 条，gate_result=blocked（现场层证据，闭合 002 §6.1）
     探针 exit 0（引擎层旁证）
失败形态：记录为空 -> 闭合轮 FAIL（P1 不成立），不得开正式轮
```

### S2 A 臂经 wrapper 执行（记录）

```
python tools/eval/run.py --exec "python -c \"print('closure-dry-A')\"" \
  --runlog $W/run/run-log-exec.json --condition A --task-id T11 \
  --key T11-A-r1 --exec-cwd $W/run
# 预期：exit 0；run-log v2 新增 1 条记录（executed=True, exit_code=0）
```

（A 臂任务产物按 §13.1 落 `$W/run/products/T11/`；wrapper 拒绝清单抽查可另发一条
`rm -rf /` 形态命令，预期 `executed=False`、`refused='rm -rf'`、wrapper 退出码非零。）

### S3 判空（B 臂零记录核验，不误报）

```
python -c "import json,sys; d=json.load(open('$W/run/run-log-exec.json',encoding='utf-8')); \
b=[r for r in d['records'] if r.get('condition')=='B']; \
a=[r for r in d['records'] if r.get('condition')=='A']; \
print('A records:', len(a)); print('B records:', len(b)); \
sys.exit(0 if len(a)>=1 and len(b)==0 else 1)"
# 预期：A records: >=1 / B records: 0；exit 0
# 失灵对照（证明检查活着）：向 $W/run 的**副本**注入一条伪造 B 记录 -> 上述断言必须翻 exit 1
# （对照在副本上做，正本保持 B 零记录原样）
```

- **判空不误报**：B 臂 log 本来就该是空的——合法空白必须 exit 0（对照 002 卡
  D3 §4：零记录只在执行面被硬禁时才具备证据力，S1 的记录非空正是那个前提）；
- **判空不失灵**：伪造 B 记录必须翻红——检查不能恒绿。

### S4 密封

```
python tools/eval/seal_run.py $W/run --label closure-dry
# 预期：exit 0；打印 files: N（run-data.json、run-log-exec.json、products/ 递归全量入清单；
#       run-log 落 run-dir 内随封 = 002 D4 §2.6 实测形态）
```

### S5 解封 / 校验（custody）

```
python tools/eval/seal_run.py --verify $W/run
# 预期：exit 0；VERIFY: OK (N files match the seal)

python tools/eval/seal_run.py $W/run --label closure-dry-custody --move-to $W/custody
# 预期：exit 0；custody 副本对封一致（002 D4 §2.3 同款）

# tamper 抽查（可选但建议）：改密封副本任一字节 -> --verify 报 MODIFIED、exit 1；
# 还原后 --verify 恢复 OK。H6（整体替换自洽清单）为工具自述已知洞，闭合轮不验收 H6，
# 以 custody 规程（seal 与副本分置）为既定缓解（002 D4 §4 H6 处置建议）。
```

### S6 解封后环境复原

```
# 移除注入的 deny 规则（删除会话级 permission.json / 还原 global 级原状）
# 预期：$W 外的运行时环境回到 P0-4 基线（permission.json 不存在或 deny 为空）
# $W 的处置照 002 ADV-2 先例：评审后由 Jarvis 合并链路删除，或移仓外 + 处置日志一行
```

---

## 3. PASS 判据清单（供第四轮执行卡引用；全过才记闭合轮 PASS）

| # | 判据 | 核验物 |
|---|---|---|
| **P1** | B 臂 `permission.enforcement` 拒绝记录**非空**（含 `gate_result: 'blocked'`、tool_name 可回溯）——002 §6.1 现场层缺口在此闭合 | S1 |
| **P2** | A 臂 run-log v2 记录**非空**（`condition=A`，`executed=True`，退出码在记录） | S2 |
| **P3** | B 臂 run-log **B 记录 = 0**（零记录成立；其证据力由 P1 的权限门控前提保证） | S3 |
| **P4** | 判空脚本对空白 run **不误报**：合法 B 零记录 exit 0；且对注入伪造 B 记录的副本**翻红**（exit 1）——检查活着 | S3 |
| **P5** | 密封 exit 0，`run-data.json` + `run-log-exec.json` + `products/<task-id>/` 递归全量入清单（含代码层实现文件落位 §13.1） | S4 |
| **P6** | `--verify` OK exit 0；custody 副本对封 exit 0；tamper 抽查 MODIFIED 检出（若执行） | S5 |
| **P7** | 执行面封堵引擎层旁证：profile §2.2 探针当轮复跑 exit 0 | S1.4 |
| **P8** | 环境复原：注入规则移除，`permission.json` 回到 P0-4 基线（A 臂共用环境无渗漏） | S6 |
| **P9** | 零数据边界：闭合轮全程无 E 级判定触发；产物只在 `$W`；`artifacts.json` newest 位无闭合轮条目；无 verdict 产生 | 全程 |

**PASS 判定的证据形态**：P1–P9 逐条带命令 + 退出码 + 关键输出行登记（对照本卡
A1–A8 的带退出码口径）；闭合轮记录落 `$W/` 内（或仓外），随 `$W` 一并处置。

---

## 4. 产物落点（重申）

- 闭合轮一切产物（run-dir、run-log、封签、custody 副本、探针输出、记录文件）只落
  `dryrun/closure/`（仓内未跟踪目录，不入 git）或**仓外临时目录**；
- 不触碰：`verdicts/`、`artifacts.json`、`ledger/`、任何正式 run 目录、红区九文件；
- 处置：002 ADV-2 先例（删除或移仓外 + 处置日志一行），归 Jarvis 合并链路。

---

## 5. 闭合轮不做的事

1. 不出卡、不评审、不写 verdict——纯机制预演，第四轮执行卡以本文件 §3 为判据清单；
2. 不跑 30 任务、不产生 E 级数据、不做任何两臂效果比较（S1/S2 的 1–2 个任务只服务
   机制动作，其产物内容不进任何分析）；
3. 不改仪器：`seal_run.py` / `runlog.py` / `run.py` / 判定器全部只读调用（红区纪律）；
4. 不预设第四轮结论——闭合轮 PASS 只说明「机制链路就绪」，不构成对任何测评
   效果的前瞻判断（EVO-20261024-001）。
