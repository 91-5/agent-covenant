# B 臂权限规则预置 profile（配方文档）

- **卡**：XJ-20261031-001 / D2
- **日期**：2026-10-31
- **性质**：**配方文档**（卡面约束 4）——本文件交付「规则文本 + 验证命令 +
  预期拒绝输出」；具体 deny 生效以执行卡启动时的实测为准，本卡验收只核齐备性
  与可复跑性。
- **上游实测**：`docs/dryrun-b-arm-tool-deny.md`（002 卡 D2，`HARD_DENY_OK`：
  整工具 deny 引擎层实测拒绝、`bypassPermissions` 免疫、`permission.enforcement`
  结构化记录面）。
- **裁定来源**：B 臂 deny 到只读面（read/glob/grep 一并 deny）——sir 2026-10-31
  终裁，依据 `verdicts/XJ-20261030-002.verdict.json` `adjudicator_pending`；
  协议侧条文见 `docs/eval-runner-protocol.md` §13.2 第 4 点。

---

## 0. 结论性口径

B 臂 profile = **整工具 deny 全量清单**（含只读工具 read/glob/grep）+ **MCP
服务器级 `mcp__<server>` deny**，以 configV1 规则形态注入 `permission.json`；
随 B 轮启动注入、轮后移除，**不落盘到执行者共用配置文件**（避免污染 A 臂环境）。
deny 在权限引擎归约入口生效（`permission-core.js` 整工具规则先于 bypass 放行
快路径），拒绝落 `permission.enforcement` 结构化日志。

---

## 1. deny 规则文本（configV1 形态）

运行时读取路径（002 报告 §3.1）：`global` 规则 → `<dataDir>/permission.json`
（`@mavis/local-runtime/dist/permissions/rules.js:290-304`）；会话级 →
`<dataDir>/sessions/<session-id>/permission.json`。编解码器为
`@mavis/local-runtime/dist/permissions/rule-codec.js` `configV1ToRules()`，
不含括号的规则串即**整工具规则**（`matcher.kind = 'tool'`）。

```json
{"allow": [], "ask": [], "deny": ["bash", "write", "edit", "read", "glob", "grep",
                                  "task", "todowrite", "web_fetch", "web_search",
                                  "miniapp", "mcp__browser"]}
```

### 1.1 规则逐条口径

| # | 规则串 | 覆盖面 | 实测依据 |
|---|---|---|---|
| R1 | `bash` | 内置 shell 执行 | 002 D2 实测 deny（bypass 免疫） |
| R2 | `write` | 内置写文件 | 002 D2 实测 deny |
| R3 | `edit` | 内置编辑文件 | 002 D2 实测 deny |
| R4 | `read` | 只读：读文件（sir 终裁并入） | 002 报告 §6.3 deny-all 变体实测 deny；本卡 §3 复测 deny |
| R5 | `glob` | 只读：文件名匹配（sir 终裁并入） | 同上 |
| R6 | `grep` | 只读：内容搜索（sir 终裁并入） | 002 报告 §6.3 只单测了 read/glob；grep 为同一整工具机制，本卡 §3 复测 deny——运行时工具名以执行卡启动时实测为准 |
| R7 | `task` | 子 agent 派生 | 002 D2 实测 deny；子会话继承（`rules.js:86-108`）为代码面阅读，端到端确认留待闭合轮 |
| R8 | `todowrite` | 任务清单写入 | 002 D2 deny 清单收录 |
| R9 | `web_fetch` | 网络抓取 | 002 D2 实测 deny |
| R10 | `web_search` | 网络搜索 | 002 D2 deny 清单收录 |
| R11 | `miniapp` | 小程序面 | 002 D2 deny 清单收录 |
| R12 | `mcp__<server>` | MCP **服务器级**整服 deny（本机已知 server：`browser`） | 002 报告 §6.2 实测：裸 `mcp_browser` **无效**；`mcp__browser` 使 `mcp__browser__navigate` deny（reason=`rule:mcp__browser`） |

两条纪律（002 报告 §6.2 口径）：

1. 工具名必须是**运行时精确名**；
2. MCP 一律服务器级 `mcp__<server>`——整服 deny 由引擎 `findMcpServerRule`
   匹配 `mcp__<server>__<tool>` 前缀，不必逐工具枚举。

> MCP server 清单**随装随变**：执行卡启动时须先枚举当轮实际配置的 MCP server，
> 把每个 server 以 `mcp__<server>` 追加进 deny 清单后再注入（见 §4 步骤 0）。

---

## 2. 验证配方（每条规则的可复跑验证命令与预期输出）

### 2.1 前置：从随包 `app.asar` 解出真实权限引擎（只读解析，不改安装）

解析器 `extract-asar.mjs`（asar 头索引遍历，无需安装 asar 工具；`app.asar`
本机路径 `D:/MiniMaxcode/MiniMax Code/resources/app.asar`，执行卡启动时以
`docs/executor-fingerprint-minimax.md` §2.2 口径复核）：

```javascript
// extract-asar.mjs —— 用法：node extract-asar.mjs <app.asar> <out-root> [prefix]
import fs from 'node:fs';
import path from 'node:path';

const ASAR = process.argv[2];
const OUT = process.argv[3];
const PREFIX = process.argv[4] ?? 'node_modules/@mavis';

const fd = fs.openSync(ASAR, 'r');
const b = Buffer.alloc(16);
fs.readSync(fd, b, 0, 16, 0);
const headerSize = b.readUInt32LE(4);
const hbuf = Buffer.alloc(headerSize);
fs.readSync(fd, hbuf, 0, headerSize, 8);
const jsonLen = hbuf.readUInt32LE(4);
const H = JSON.parse(hbuf.slice(8, 8 + jsonLen).toString('utf8'));
const dataStart = 8 + headerSize;

let files = 0, skipped = 0;
function walk(node, rel) {
  for (const [name, child] of Object.entries(node.files ?? {})) {
    const childRel = path.join(rel, name);
    if (child.files) { walk(child, childRel); continue; }
    if (!('offset' in child)) { skipped++; continue; } // 符号链接等非常规条目：探针不需要
    const dest = path.join(OUT, rel, name);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    const buf = Buffer.alloc(child.size);
    fs.readSync(fd, buf, 0, child.size, dataStart + Number(child.offset));
    fs.writeFileSync(dest, buf);
    files++;
  }
}
let top = H; // asar 头 JSON 根即文件树（{files: ...}）
for (const seg of PREFIX.split('/')) top = top.files[seg];
if (!top) { console.error(`prefix not found in asar header: ${PREFIX}`); process.exit(2); }
walk(top, PREFIX);
console.log(`extracted ${files} files (skipped ${skipped} non-regular) from ${PREFIX} -> ${OUT}`);
```

```
node extract-asar.mjs "D:/MiniMaxcode/MiniMax Code/resources/app.asar" asar node_modules/@mavis
# -> extracted N files (skipped 0 non-regular) from node_modules/@mavis -> asar
# -> exit 0
```

### 2.2 探针：整工具 deny + bypass 免疫 + 只读面 + MCP 服务器级（一次跑完 12 规则）

探针 `b_arm_deny_probe.mjs` 把 §1 的 deny 清单写入**临时 dataDir** 的
`permission.json`（绝不指向真实 profile），送入真实权限引擎
（`@mavis/permission/dist/engine.js` `PermissionEngine.checkPermission()`），
对每个工具在 `bypassPermissions` 与 `default` 两种模式下各判一次：

```javascript
// b_arm_deny_probe.mjs —— 用法：node b_arm_deny_probe.mjs <extract-root> [dataDir]
// 退出码 0 = 所有被探工具在两种模式下均 deny；任一非 deny -> exit 1
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const ROOT = path.resolve(process.argv[2] ?? 'asar');
const DATA_DIR = path.resolve(process.argv[3] ?? 'dataDir');

const pkg = path.join(ROOT, 'package.json');
if (!fs.existsSync(pkg)) fs.writeFileSync(pkg, JSON.stringify({ type: 'module' }));

const mod = (p) => import(pathToFileURL(path.join(ROOT, p)).href);
const { createToolPermissionContext } = await mod('node_modules/@mavis/permission/dist/context.js');
const { PermissionEngine } = await mod('node_modules/@mavis/permission/dist/engine.js');
const { BashToolPermissionChecker } = await mod('node_modules/@mavis/permission/dist/tools/bash-checker.js');
const { FsToolPermissionChecker } = await mod('node_modules/@mavis/permission/dist/tools/fs-checker.js');
const { configV1ToRules } = await mod('node_modules/@mavis/local-runtime/dist/permissions/rule-codec.js');

// B 臂 deny 清单 = 全部工具（含只读面 read/glob/grep，sir 2026-10-31 终裁）
// + MCP 服务器级 mcp__<server>。运行时精确名；裸 mcp_browser 无效（002 报告 §6.2）。
const DENY = ['bash', 'write', 'edit', 'read', 'glob', 'grep', 'task', 'todowrite',
              'web_fetch', 'web_search', 'miniapp', 'mcp__browser'];

fs.mkdirSync(DATA_DIR, { recursive: true });
const RULE_FILE = path.join(DATA_DIR, 'permission.json');
fs.writeFileSync(RULE_FILE, JSON.stringify({ allow: [], deny: DENY, ask: [] }));

const rules = configV1ToRules(JSON.parse(fs.readFileSync(RULE_FILE, 'utf8')), 'global', 'global');
const engine = new PermissionEngine();
engine.registerToolPermissionChecker('bash', new BashToolPermissionChecker());
engine.registerToolPermissionChecker('edit', new FsToolPermissionChecker());
engine.registerToolPermissionChecker('write', new FsToolPermissionChecker());

const CASES = [
  ['bash', { command: 'echo hello' }],
  ['write', { file_path: 'C:/temp/probe.txt', content: 'x' }],
  ['edit', { file_path: 'C:/temp/probe.txt', old_string: 'x', new_string: 'y' }],
  ['read', { file_path: 'C:/temp/probe.txt' }],
  ['glob', { pattern: '*.py', path: 'C:/temp' }],
  ['grep', { pattern: 'x', path: 'C:/temp' }],
  ['web_fetch', { url: 'https://example.com' }],
  ['web_search', { query: 'probe' }],
  ['task', { prompt: 'x' }],
  ['todowrite', { todos: [] }],
  ['miniapp', {}],
  ['mcp__browser__navigate', { url: 'https://example.com' }],
];

let fail = 0;
for (const mode of ['bypassPermissions', 'default']) {
  console.log(`### mode=${mode} deny=${DENY.join(',')}`);
  const ctx = createToolPermissionContext({
    mode, rules, workingDirectory: DATA_DIR,
    dataDir: DATA_DIR, homeDir: DATA_DIR, platform: process.platform,
    shellFamily: 'powershell',
  });
  for (const [tool, input] of CASES) {
    const d = engine.checkPermission(tool, input, ctx, { policyOwner: 'core' });
    const ok = d.behavior === 'deny';
    if (!ok) fail++;
    console.log(`  ${tool.padEnd(24)} -> ${d.behavior.padEnd(6)} ${ok ? '' : '<< UNEXPECTED '}${JSON.stringify(d.reason)}`);
  }
}
process.exit(fail ? 1 : 0);
```

```
node b_arm_deny_probe.mjs asar dataDir
# -> exit 0（全部 deny）；exit 1 = 存在非 deny 行，预置无效
```

**每条规则的预期拒绝输出**（两模式同形；`reason` 一律为
`{"type":"rule","rule":{"source":"global","ruleBehavior":"deny","ruleValue":{"toolName":"<规则串>","matcher":{"kind":"tool"}},"destination":"global"}}`）：

| 探针行 | 预期 | 对应规则 |
|---|---|---|
| `bash -> deny` | reason ruleValue.toolName=`bash` | R1 |
| `write -> deny` | toolName=`write` | R2 |
| `edit -> deny` | toolName=`edit` | R3 |
| `read -> deny` | toolName=`read` | R4 |
| `glob -> deny` | toolName=`glob` | R5 |
| `grep -> deny` | toolName=`grep` | R6 |
| `web_fetch -> deny` | toolName=`web_fetch` | R9 |
| `web_search -> deny` | toolName=`web_search` | R10 |
| `task -> deny` | toolName=`task` | R7 |
| `todowrite -> deny` | toolName=`todowrite` | R8 |
| `miniapp -> deny` | toolName=`miniapp` | R11 |
| `mcp__browser__navigate -> deny` | toolName=`mcp__browser`（服务器级规则命中） | R12 |

**对照读数**（复用 002 报告 §3.2 的 CONTROL 场景，防「恒 deny」假象）：同一引擎在
**无 deny 规则**时，`bypassPermissions` 下全部 `allow`、`default` 下安全命令与
非交互工具 `allow`/`ask`——即 deny 只由规则产生，不是引擎默认。002 卡 D2 已实测
该对照；闭合轮复跑时按 `docs/mechanism-closure-round.md` §2 S1 一并取对照。

---

## 3. 配方复测记录（本卡，2026-10-31）

- **执行者**：ZCode（本卡）。**落点**：仓外临时目录（验证后整体删除，不在仓内
  留任何实验产物；不给 `dryrun/` 添量——002 ADV-2 先例）。
- **命令序列**：`node extract-asar.mjs "D:/MiniMaxcode/MiniMax Code/resources/app.asar" asar node_modules/@mavis`
  → `extracted 3901 files (skipped 0 non-regular) ... exit 0`；
  `node b_arm_deny_probe.mjs asar dataDir` → **exit 0**。
- **实测输出**（`mode=bypassPermissions` 段全文；`mode=default` 段逐行同形，
  仅 reason 完全一致故不重复抄录）：

```
### mode=bypassPermissions deny=bash,write,edit,read,glob,grep,task,todowrite,web_fetch,web_search,miniapp,mcp__browser
  bash                     -> deny   {"type":"rule","rule":{...,"ruleValue":{"toolName":"bash","matcher":{"kind":"tool"}},...}}
  write                    -> deny   {"type":"rule","rule":{...,"ruleValue":{"toolName":"write","matcher":{"kind":"tool"}},...}}
  edit                     -> deny   {"type":"rule","rule":{...,"ruleValue":{"toolName":"edit","matcher":{"kind":"tool"}},...}}
  read                     -> deny   {"type":"rule","rule":{...,"ruleValue":{"toolName":"read","matcher":{"kind":"tool"}},...}}
  glob                     -> deny   {"type":"rule","rule":{...,"ruleValue":{"toolName":"glob","matcher":{"kind":"tool"}},...}}
  grep                     -> deny   {"type":"rule","rule":{...,"ruleValue":{"toolName":"grep","matcher":{"kind":"tool"}},...}}
  web_fetch                -> deny   {"type":"rule","rule":{...,"ruleValue":{"toolName":"web_fetch","matcher":{"kind":"tool"}},...}}
  web_search               -> deny   {"type":"rule","rule":{...,"ruleValue":{"toolName":"web_search","matcher":{"kind":"tool"}},...}}
  task                     -> deny   {"type":"rule","rule":{...,"ruleValue":{"toolName":"task","matcher":{"kind":"tool"}},...}}
  todowrite                -> deny   {"type":"rule","rule":{...,"ruleValue":{"toolName":"todowrite","matcher":{"kind":"tool"}},...}}
  miniapp                  -> deny   {"type":"rule","rule":{...,"ruleValue":{"toolName":"miniapp","matcher":{"kind":"tool"}},...}}
  mcp__browser__navigate   -> deny   {"type":"rule","rule":{...,"ruleValue":{"toolName":"mcp__browser","matcher":{"kind":"tool"}},...}}
```

（上录为压缩显示；复测原样输出 reason 全文与 §2.2 模板逐字段一致，含
`source: "global"` / `ruleBehavior: "deny"` / `destination: "global"`。）

- **边界**：本复测是**引擎层**（与 002 D2 同层），不是真实模型回合的现场取证；
  现场层证据由闭合轮取（§5）。本轮 `dataDir` 指向临时目录，未触碰本机真实
  profile 的 `permission.json`。

---

## 4. profile 的应用方式（执行卡职责，本卡只固化方法）

0. **枚举 MCP server**（随装随变，注入前必做）：从当轮执行者配置/会话清单读取
   实际启用的 MCP server 名，把每个 server 以 `mcp__<server>` 追加进 §1 清单
   （本机 2026-10-31 已知：`browser`）。
1. **注入时点**：B 轮启动前（执行卡触发）；A 轮**不注入**任何规则。
2. **注入形态**：优先**会话级** `<dataDir>/sessions/<session-id>/permission.json`
   （随 B 臂会话生命周期，天然不外溢）；仅当会话级路径实测未被运行时读取时降级用
   `global` 级 `<dataDir>/permission.json`，且 B 轮结束后**必须移除并复查**。
   两个落点均须在执行卡启动时实测确认 `<dataDir>` 真实位置（本卡 2026-10-31 只读
   观测：`C:\Users\15812\.minimax\` 有 `config.yaml` 且**无** `permission.json`；
   `%APPDATA%\MiniMax\` 下同样未观测到 `permission.json`——哪个目录是运行时实际
   读取的 `<dataDir>`，以执行卡实测为准，不得以本卡观测代证）。
3. **不落盘到执行者配置文件**：不修改 `config.yaml`（含 `permissionMode`）——
   B 臂**不**改 `permissionMode: bypassPermissions`，两臂配置面保持一致（身份面
   一致），差异只在注入的 deny 规则；deny 的 bypass 免疫已实测（002 D2 + 本卡 §3）。
4. **A 臂环境保护**：A 轮启动前核验 `permission.json` 不存在（或 deny 为空）；
   B 轮移除规则后同样复查——防止 B 轮规则渗漏进两臂共用环境。
5. **预置生效证据**：注入后、开跑前复跑 §2.2 探针（002 verdict 条件 C2 原文口径
   「预置后开跑前复跑 D2 compact_probe 取预置生效证据」），exit 0 方可开跑。

---

## 5. 残留边界（随结论一起引用，002 §6 顺延）

1. **未走真实模型回合取证**（002 §6.1）：本 profile 的全部证据是引擎层；现场层
   （模型发起调用被拒、`permission.enforcement` 落盘可回溯）由闭合轮取——见
   `docs/mechanism-closure-round.md` P1。
2. **子会话继承未端到端实测**（002 §6.4）：`inheritSessionRestrictions`
   （`rules.js:86-108`）为代码面阅读；闭合轮的 B 臂任务含 `task` 派生场景时顺带确认。
3. **`<dataDir>` 落点未定**：§4 步骤 2，执行卡实测确认。
4. **MCP server 清单时效**：§4 步骤 0，注入前枚举。
5. **grep 的现场层**：R6 引擎层已复测（§3），但运行时真实工具名与调用形态
   以执行卡启动时实测为准。

---

## 6. 闭合轮接口

本 profile 的 PASS 判据在 `docs/mechanism-closure-round.md` §3（P1：B 臂
permission 拒绝记录非空；P8：解封后环境复原含规则移除复查）。闭合轮本身零数据、
不出卡不评审；本文件是配方输入，不是执行记录。
