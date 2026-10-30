# D2 实测报告：B 臂「硬禁工具」是否成立（权限层）

- **卡**：XJ-20261030-002 / D2
- **采集日期**：2026-10-30
- **采集者**：minimax code（本卡实现者）
- **对象**：MiniMax Code 3.1.7 桌面端（本机安装，region `cn`）

---

## 0. 结论

> ## `HARD_DENY_OK`
>
> B 臂的「硬禁工具」在**权限层**成立：整工具 deny 规则由随包的权限引擎
> （`@mavis/permission`）判定为 `deny`，**bypass 免疫**（在 `bypassPermissions`
> 模式下同样拒绝），两条策略路径（`core` / `engine`）结论一致，且拒绝在
> 引擎入口即发生——不是提示词层的「请不要」，也不是事后统计。
>
> 附四条**必须随结论一起引用**的残留缺口，见 §6；其中 §6.5 是**协议级**问题
> （与 prereg C7(a)「两臂同执行者同工具集」的直接张力），需 sir / adjudicator
> 裁定，不由本卡代决。

本结论只回答「工具能不能被硬禁住」，**不回答**「第四轮该怎么做」；后者见
`docs/dryrun-runlog-coverage.md` §5 与卡内 `## dry-run 结论`。

---

## 1. 三选一结论的定义与本次取值

| 取值 | 含义 | 本次 |
|---|---|---|
| `HARD_DENY_OK` | 权限层硬禁成立（工具调用真被拒），B 臂可做 | **本次取值** |
| `SOFT_ONLY` | 只能提示层禁（模型自行约束），B 臂不可用 → 升级裸 API 对照方案 | 未取 |
| `FAIL` | 无法接入该工具 | 未取 |

判定口径（对应卡面 Review question 1）：**硬禁 = 权限层实测**，即
（i）送入真实权限引擎的工具调用返回 `deny`；（ii）该 `deny` 在引擎入口产生，
不依赖模型配合；（iii）拒绝有机器可读记录面。三条同时满足才记 `HARD_DENY_OK`。

---

## 2. 实测对象：什么是真的，什么是合成的

**真实（随包代码，原样取用）**

| 组件 | 路径（`app.asar` 内） | 作用 |
|---|---|---|
| 权限引擎 | `node_modules/@mavis/permission/dist/engine.js` | `PermissionEngine.checkPermission()` |
| 判定归约 | `node_modules/@mavis/permission/dist/permission-core.js` | `reducePermissionDecision()` / `reducePermissionEvaluation()` |
| 规则上下文 | `node_modules/@mavis/permission/dist/context.js` | `createToolPermissionContext()` |
| Bash 检查器 | `node_modules/@mavis/permission/dist/tools/bash-checker.js` | `BashToolPermissionChecker` |
| 文件系统检查器 | `node_modules/@mavis/permission/dist/tools/fs-checker.js` | `FsToolPermissionChecker` |
| 规则文件编解码 | `node_modules/@mavis/local-runtime/dist/permissions/rule-codec.js` | `configV1ToRules()`（与运行时读 `permission.json` 同一编解码器） |
| 规则文件路径解析 | `node_modules/@mavis/local-runtime/dist/permissions/rules.js:290-304` | 全局规则落 `<dataDir>/permission.json` |

**合成（已声明，不隐藏）**

1. **dataDir 指向临时目录**（`dryrun/d2/dataDir`），**未触碰本机真实 profile 的
   `permission.json`**——本卡对用户现装配置只读（卡面约束 4）。正式落法是把同一份
   规则文件写到真实 `<dataDir>/permission.json`（或会话级
   `<dataDir>/sessions/<session-id>/permission.json`）。
2. **工具调用是直接送入引擎的**，不是走一次真实模型回合。理由：本机**未安装
   MiniMax Code 的 headless CLI**（`mcode` 不在 PATH；本机只有 Electron 桌面端，
   代理进程内运行，无 TCP 监听口可供外部驱动），强行驱动会要求改动用户现装 profile
   的权限配置以影响其正在运行的其他会话——超出本卡授权。故本项列为**残留缺口 §6.1**，
   不以「已实测」措辞冒充。
3. `dryrun/asar/node_modules/@mavis/shared/local-runtime-logging/logger.js` 是本次
   dry-run 早期写入的一个**影子文件**，**未被 Node 解析命中**：真实模块经
   `@mavis/shared`（0.2.1）的 exports 映射解析到
   `dist/local-runtime-logging/logger.js`。该影子文件不参与任何判定路径。

---

## 3. 实测命令与输出

### 3.1 规则文件格式（随包编解码器所接受的形态）

`node_modules/@mavis/local-runtime/dist/permissions/rule-codec.js:104-120`
`parseRuleString()`：不含括号的字符串即为**整工具规则**（`matcher.kind = 'tool'`）。
运行时实际读取的文件路径见 `rules.js:290-304`：`global` → `<dataDir>/permission.json`。

```json
{"allow": [], "deny": ["bash", "write", "edit", "task", "todowrite",
                       "web_fetch", "web_search", "mcp_browser", "miniapp"],
 "ask": []}
```

### 3.2 实测矩阵

命令（完整可复跑驱动见 §7 附录）：

```
node dryrun/d2/d2_permission_probe.mjs        # exit 0
```

输出（`policyOwner=core` 段，`policyOwner=engine` 段结论一致）：

```
### SCENARIO CONTROL bypassPermissions, no deny rules (mode=bypassPermissions, policyOwner=core, deny=(none))
  bash       -> allow      {"type":"mode","mode":"bypassPermissions"}
  write      -> allow      {"type":"mode","mode":"bypassPermissions"}
  edit       -> allow      {"type":"mode","mode":"bypassPermissions"}
  read       -> allow      {"type":"mode","mode":"bypassPermissions"}
  glob       -> allow      {"type":"mode","mode":"bypassPermissions"}
  web_fetch  -> allow      {"type":"mode","mode":"bypassPermissions"}
  task       -> allow      {"type":"mode","mode":"bypassPermissions"}
  mcp__browser__navigate -> allow      {"type":"mode","mode":"bypassPermissions"}

### SCENARIO CONTROL default mode, no deny rules (mode=default, policyOwner=core, deny=(none))
  bash       -> allow      {"type":"subcommandResults","reasons":{}}      # echo hello
  bash       -> ask        {"type":"subcommandResults","reasons":{}}      # python -c "print(1)"
  write      -> ask        {"type":"workingDirectory","path":"C:\\temp\\probe.txt"}
  edit       -> ask        {"type":"workingDirectory","path":"C:\\temp\\probe.txt"}
  read       -> ask        {"type":"workingDirectory","path":"C:\\temp\\probe.txt"}
  glob       -> allow      {"type":"safetyCheck","description":"No permission checker r...
  web_fetch  -> allow      {"type":"safetyCheck","description":"No permission checker r...
  task       -> allow      {"type":"safetyCheck","description":"No permission checker r...
  mcp__browser__navigate -> allow      {"type":"safetyCheck","description":"No permission checker r...

### SCENARIO TREATMENT bypassPermissions + whole-tool deny rules (mode=bypassPermissions, policyOwner=core, deny=bash,write,edit,task,todowrite,web_fetch,web_search,mcp_browser,miniapp)
  bash       -> deny       rule:bash
  bash       -> deny       rule:bash
  write      -> deny       rule:write
  edit       -> deny       rule:edit
  read       -> allow      {"type":"mode","mode":"bypassPermissions"}
  glob       -> allow      {"type":"mode","mode":"bypassPermissions"}
  web_fetch  -> deny       rule:web_fetch
  task       -> deny       rule:task
  mcp__browser__navigate -> allow      {"type":"mode","mode":"bypassPermissions"}

### SCENARIO TREATMENT default mode + whole-tool deny rules (mode=default, policyOwner=core, deny=...)
  bash       -> deny       rule:bash
  bash       -> deny       rule:bash
  write      -> deny       rule:write
  edit       -> deny       rule:edit
  read       -> ask        {"type":"workingDirectory","path":"C:\\temp\\probe.txt"}
  glob       -> allow      {"type":"safetyCheck","description":"No permission checker r...
  web_fetch  -> deny       rule:web_fetch
  task       -> deny       rule:task
  mcp__browser__navigate -> allow      {"type":"safetyCheck","description":"No permission checker r...
```

### 3.3 三条读数（本报告的核心）

| 读数 | 结论 |
|---|---|
| **对照 1**：`bypassPermissions` 且无 deny 规则 → 全部 `allow` | 现装权限模式（`config.yaml` 的 `permissionMode: bypassPermissions`）**本身不提供任何阻断**；B 臂「零执行」不可能靠模式默认获得 |
| **对照 2**：`default` 模式且无 deny 规则 → 安全命令（`echo hello`）**直接放行**，非交互工具（`glob`/`web_fetch`/`task`）**直接放行** | `default` 模式是「有风险才问」，**不是硬禁**；靠切模式实现 B 臂零执行不可行 |
| **处理**：整工具 deny 规则 → `bash`/`write`/`edit`/`web_fetch`/`task` 全部 `deny`，reason 为 `rule:<tool>`；且在 `bypassPermissions` 下**依然 deny** | 硬禁成立且 **bypass 免疫** |

### 3.4 机制解释（代码面，评审可核对）

- 整工具 deny 在**归约入口**生效，早于任何「放行快路径」：
  `permission-core.js:11-13`
  ```js
  const denyRule = hasWholeToolRule(context, toolName, 'deny')
      ?? findMcpServerRule(toolName, context, 'deny');
  if (denyRule)
      return { behavior: 'deny', reason: { type: 'rule', rule: denyRule } };
  ```
  而 bypass 放行位于其后的 Step 2（`engine.js:90-93` 注释：「Step 1 — Reject
  check (hard block, bypass-immune)」）→ **deny 先于 bypass**。
- `engine.js:81-96` 的三步流程注释原文：「Step 1: Reject check (hard block,
  unaffected by bypass mode)」。
- MCP 工具另有**服务器级** deny：`engine.js:149-153` + `mcp-runtime-name.js:9-19`，
  规则写作 `mcp__<server>`，匹配 `mcp__<server>__<tool>`。

---

## 4. 拒绝记录面（有没有「拒绝记录」）

有，且是机器可读的结构化记录。实现在
`node_modules/@mavis/local-runtime-v2/dist/service/turn-system/agent-host/runner/policy/local-turn-permission-gate.js`：

- `beforeToolCall` → `checkPermissionDecision(this.options.decisions, ...)`
  （同文件 `:235`）→ 命中 deny 时走 `:237-241` 分支，`gate_result: 'blocked'`。
- `logEnforcement()`（同文件 `:348-356`）落一条 `permission.enforcement` 日志记录：

```js
logEnforcement(input, request, fields, level = 'info') {
    this.options.logger?.[level]?.({
        session_id: input.sessionId,
        turn_id: input.turnId,
        tool_call_id: request.toolCallId,
        tool_name: request.toolName,
        ...fields,
    }, 'permission.enforcement');
}
```

字段含 `session_id` / `turn_id` / `tool_call_id` / `tool_name` /
`policy_behavior: 'deny'` / `gate_result: 'blocked'` / `decision_source: 'policy'`。

→ B 臂的「工具被拒」因此可取**会话级、可回溯的拒绝记录**，而不是靠人工读日志。

---

## 5. 与 D3（run-log 覆盖）的联动

本报告证明「B 臂的**执行面可以被硬关掉**」；D3 证明「run-log 只覆盖经 wrapper
路由的命令」。两者合起来才成立的一条推论（本卡据此提出，**需协议确认**）：

> 若 B 臂不预置 deny 规则，则「B 臂 run-log 零执行记录」**不能**作为「B 臂未执行」
> 的佐证——它只说明「没有命令经 wrapper 路由」，不说明「没有执行发生」。

这是 dp 大脑参谋所列三坑之一（run-log/seal 只覆盖可见边界）的具体落点，详见
`docs/dryrun-runlog-coverage.md` §4。

---

## 6. 残留缺口（必须随结论一起引用）

| # | 缺口 | 性质 | 状态 |
|---|---|---|---|
| 6.1 | **未走真实模型回合取证**：拒绝结论来自权限引擎实测，不是「模型发起一次调用被拒」的现场记录。本机无 headless CLI，且现场取证需改动用户现装 profile 的权限配置（影响其正在运行的其他会话），超出本卡授权 | 实测范围 | 开放 |
| 6.2 | **工具名必须精确**：deny 按**运行时工具名**匹配。写 `mcp_browser` **不生效**（实测 `mcp__browser__navigate` 在该规则下仍 `allow`）；MCP 工具必须写服务器级 `mcp__browser`（实测即 `deny rule:mcp__browser`） | 实测发现 | 已知，须写入 runbook |
| 6.3 | **只读面默认仍放行**：`read` / `glob` / `grep` 未被 deny 时仍 `allow`。若 B 臂要复现第三轮「执行者无任何工具」的语义，须一并 deny（实测 deny-all 变体下 `read`/`glob` 均 `deny`） | 实测发现 | 需协议裁定（见 6.5） |
| 6.4 | **会话级规则可继承到子会话**：父会话的 deny/ask 规则由 `rules.js:86-108` `inheritSessionRestrictions()` 复制给子会话 → `task` 派生的子 agent 不会绕过父级 deny；本项为**代码面阅读**，未做端到端实测 | 推断（未实测） | 需正式 run 前实测 |
| 6.5 | **协议张力（需裁定）**：prereg C7(a) 要求「两臂同执行者同工具集，两臂差异只体现在有无独立评审/门禁兜底」。而 B 臂的「零执行」要求其执行面被关掉 → 两臂**有效工具集不同**。本卡不代裁 | 协议级 | **开放，阻塞第四轮** |

---

## 7. 复跑配方（附录：已验证的最小驱动）

前置：把随包代码取出到 `dryrun/asar/node_modules/`（`app.asar` 解析器见
`docs/executor-fingerprint-minimax.md` §2.2 的单行命令，同款逻辑批量落盘），
并准备 `dryrun/asar/package.json` = `{"type":"module"}`。

驱动脚本保存为 `dryrun/d2/compact_probe.mjs`（以下为全文，已在本机跑通，exit 0）：

```javascript
// Condensed reproduction of the D2 permission probe (XJ-20261030-002).
import fs from 'node:fs';
import path from 'node:path';

import { createToolPermissionContext } from '../asar/node_modules/@mavis/permission/dist/context.js';
import { PermissionEngine } from '../asar/node_modules/@mavis/permission/dist/engine.js';
import { BashToolPermissionChecker } from '../asar/node_modules/@mavis/permission/dist/tools/bash-checker.js';
import { FsToolPermissionChecker } from '../asar/node_modules/@mavis/permission/dist/tools/fs-checker.js';
import { configV1ToRules } from '../asar/node_modules/@mavis/local-runtime/dist/permissions/rule-codec.js';

const DATA_DIR = path.resolve('dryrun/d2/dataDir');
const RULE_FILE = path.join(DATA_DIR, 'permission.json');
const MUTATING = ['bash', 'write', 'edit', 'task', 'todowrite',
  'web_fetch', 'web_search', 'mcp_browser', 'miniapp'];

fs.mkdirSync(DATA_DIR, { recursive: true });
fs.writeFileSync(RULE_FILE, JSON.stringify({ allow: [], deny: MUTATING, ask: [] }));

const rules = configV1ToRules(JSON.parse(fs.readFileSync(RULE_FILE, 'utf8')),
  'global', 'global');
const ctx = createToolPermissionContext({
  mode: 'bypassPermissions', rules, workingDirectory: DATA_DIR,
  dataDir: DATA_DIR, homeDir: DATA_DIR, platform: process.platform,
  shellFamily: 'powershell',
});
const engine = new PermissionEngine();
engine.registerToolPermissionChecker('bash', new BashToolPermissionChecker());
engine.registerToolPermissionChecker('edit', new FsToolPermissionChecker());
engine.registerToolPermissionChecker('write', new FsToolPermissionChecker());

for (const [tool, input] of [
  ['bash', { command: 'echo hello' }],
  ['write', { file_path: 'C:/temp/probe.txt', content: 'x' }],
  ['web_fetch', { url: 'https://example.com' }],
  ['task', { prompt: 'x' }],
]) {
  const d = engine.checkPermission(tool, input, ctx, { policyOwner: 'core' });
  console.log(tool.padEnd(10) + ' -> ' + d.behavior +
    '  reason=' + JSON.stringify(d.reason));
}
```

本机输出（exit 0）：

```
bash       -> deny  reason={"type":"rule","rule":{"source":"global","ruleBehavior":"deny","ruleValue":{"toolName":"bash","matcher":{"kind":"tool"}},"destination":"global"}}
write      -> deny  reason={"type":"rule","rule":{"source":"global","ruleBehavior":"deny","ruleValue":{"toolName":"write","matcher":{"kind":"tool"}},"destination":"global"}}
web_fetch  -> deny  reason={"type":"rule","rule":{"source":"global","ruleBehavior":"deny","ruleValue":{"toolName":"web_fetch","matcher":{"kind":"tool"}},"destination":"global"}}
task       -> deny  reason={"type":"rule","rule":{"source":"global","ruleBehavior":"deny","ruleValue":{"toolName":"task","matcher":{"kind":"tool"}},"destination":"global"}}
```

> 注：完整实测脚本 `dryrun/d2/d2_permission_probe.mjs` 另覆盖了
> 「deny-all（含只读面）」与「MCP 服务器级 deny」两组扩展场景，输出见
> `dryrun/d2/probe-output.txt`（未跟踪的实验目录，不在触碰面内）。

---

## 8. 本报告不做的事

- 不宣称第四轮可以开跑——B 臂的协议张力（§6.5）与 run-log 覆盖问题
  （`docs/dryrun-runlog-coverage.md` §4）尚未关闭。
- 不宣称「禁工具机制已接入执行卡」——本卡只验机制，规则的**预置与继承**属执行卡职责。
- 不含任何效果判断（术语纪律 EVO-20261024-001）。
