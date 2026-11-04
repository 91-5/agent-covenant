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

B 臂 profile = **整工具 deny 全量清单**（含只读工具 read/glob/grep），覆盖**当轮
运行时工具注册表全集**（本机 asar 实测枚举：本地工具注册表 28 名 + 本地原生
浏览器族 14 名 + 扩展注册 builtin 3 名 + MCP 披露延迟注册面 2 名
（`tool_search`/`mcp_invoke`）+ 别名转正 1 名（`mcp_browser`）+ goal 面 3 名
（`create_goal`/`get_goal`/`update_goal`，XJ-20261104-001 补）= **51 个工具名**）+
**builtin MCP 服务器级 `mcp__<server>` deny**（`browser`、`matrix` 两服），共
**53 条规则**（R1–R53），以 configV1 规则形态注入 `permission.json`；随 B 轮启动
注入、轮后移除，**不落盘到执行者共用配置文件**（避免污染 A 臂环境）。deny 在
权限引擎归约入口生效（`permission-core.js` 整工具规则先于 bypass 放行快路径），
拒绝落 `permission.enforcement` 结构化日志。

**清单演进纪律（XJ-20261031-002 起）**：deny 清单**纯增不减**——001 卡的 R1–R12、
002 卡的 R13–R47、002 卡（3.1.10 续篇）的 R48–R50 原样保留；补全规则自 R13 起连续
续号（R51–R53 = 第四轮现场发现的 goal 面，XJ-20261104-001 补）；任何拟从清单移除
（放行）原生工具的动作必须停手回 sir 裁定。清单基础是 §2.0 的注册表枚举配方：执行
卡启动时重跑枚举（执行者已实测两度自升级：3.1.7→3.1.9 发生于 003 轮冻结落键前、
3.1.9→3.1.10 发生于 002 卡重测与 003 卡之间——注册表随版本漂移是常态，C3 冻结与
版本重采是枚举前置），枚举结果与 §1 清单差集为空方可注入。

---

## 1. deny 规则文本（configV1 形态）

运行时读取路径（002 报告 §3.1）：`global` 规则 → `<dataDir>/permission.json`
（`@mavis/local-runtime/dist/permissions/rules.js:290-304`）；会话级 →
`<dataDir>/sessions/<session-id>/permission.json`。编解码器为
`@mavis/local-runtime/dist/permissions/rule-codec.js` `configV1ToRules()`，
不含括号的规则串即**整工具规则**（`matcher.kind = 'tool'`）。

```json
{"allow": [], "ask": [], "deny": [
  "bash", "write", "edit", "read", "glob", "grep", "task", "todowrite",
  "web_fetch", "web_search", "miniapp", "mcp__browser",
  "skill", "memory", "code_review", "mavis", "session_create",
  "self_reminder", "cron_create", "cron_read", "cron_update", "cron_delete",
  "ask_user", "request_feature_enable", "task_append", "task_query",
  "task_output", "task_stop", "website_deploy", "workspace_semantic_search",
  "browser", "browser_inspect", "browser_navigate", "browser_click",
  "browser_type", "browser_press_key", "browser_scroll", "browser_hover",
  "browser_wait_for", "browser_get_dom", "browser_screenshot", "browser_paste",
  "browser_verify_text", "browser_inspect_editable_targets",
  "EnterPlanMode", "ExitPlanMode", "mcp__matrix",
  "tool_search", "mcp_invoke", "mcp_browser",
  "get_goal", "create_goal", "update_goal"
]}
```

（47 条 = R1–R12 原清单未动 + R13–R47 补全 35 条；条目与规则号逐一对应见 §1.1，
枚举出处见 §3 第二轮对照表。）

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
| R13 | `skill` | 本地技能读取/执行 | 002 卡漏列；本卡枚举（§2.0）+ 探针复测 deny（§3 第二轮） |
| R14 | `memory` | 本地记忆读写 | 同上 |
| R15 | `code_review` | 本地代码评审 | 同上（001 评审 ADV-1：此前靠引擎工具组映射附带命中，不可审计；本卡显式入清单） |
| R16 | `mavis` | mavis 代理面 | 同上 |
| R17 | `session_create` | 任务会话创建（mavis 能力族） | 同上 |
| R18 | `self_reminder` | 定时自提醒（cron 族） | 同上 |
| R19 | `cron_create` | 定时任务创建 | 同上 |
| R20 | `cron_read` | 定时任务读取 | 同上 |
| R21 | `cron_update` | 定时任务更新 | 同上 |
| R22 | `cron_delete` | 定时任务删除 | 同上 |
| R23 | `ask_user` | 向本地用户提问 | 同上 |
| R24 | `request_feature_enable` | 请求开启功能面 | 同上 |
| R25 | `task_append` | 子任务追加（task 派生面） | 同上（`task` 整工具 deny 命中不了 `task_append`/`task_query` 等独立名——001 评审实测） |
| R26 | `task_query` | 子任务查询 | 同上 |
| R27 | `task_output` | 子任务输出读取 | 同上 |
| R28 | `task_stop` | 子任务停止 | 同上 |
| R29 | `website_deploy` | 网站部署 | 同上（`buildLocalNativeRuntimeTools` 无条件构造该适配器） |
| R30 | `workspace_semantic_search` | 工作区语义检索 | 同上 |
| R31 | `browser` | 本地原生浏览器复合工具 | 同上（本地 `browser_*` 命名空间，R12 的 `mcp__browser` 只命中 MCP 路径——001 评审实测） |
| R32 | `browser_inspect` | 浏览器检查 | 同上 |
| R33 | `browser_navigate` | 浏览器导航 | 同上 |
| R34 | `browser_click` | 浏览器点击 | 同上 |
| R35 | `browser_type` | 浏览器输入 | 同上 |
| R36 | `browser_press_key` | 浏览器按键 | 同上 |
| R37 | `browser_scroll` | 浏览器滚动 | 同上 |
| R38 | `browser_hover` | 浏览器悬停 | 同上 |
| R39 | `browser_wait_for` | 浏览器等待 | 同上 |
| R40 | `browser_get_dom` | 浏览器 DOM 读取 | 同上 |
| R41 | `browser_screenshot` | 浏览器截图 | 同上 |
| R42 | `browser_paste` | 浏览器粘贴 | 同上 |
| R43 | `browser_verify_text` | 浏览器文本校验 | 同上 |
| R44 | `browser_inspect_editable_targets` | 浏览器可编辑目标检查 | 同上 |
| R45 | `EnterPlanMode` | 计划模式进入（扩展注册） | 同上（agent-extension plan-mode 条件注册，运行时精确名含大写） |
| R46 | `ExitPlanMode` | 计划模式退出（扩展注册） | 同上 |
| R47 | `mcp__matrix` | builtin MCP 服务器级整服 deny（`matrix`） | 同上（`BUILTIN_MATRIX_SERVER_NAME='matrix'`，matrix 工具以 `mcp__matrix__<tool>` 原生名投影，服务器级规则整服覆盖） |
| R48 | `tool_search` | MCP 披露面延迟注册：有界工具搜索（3.1.9+ 新注册面） | 003 轮现场 proceed×6（enforcement 记录 `gate_result:"proceed"`）；本卡 3.1.10 asar 实测定位 `agent-tools/dist/mcp-disclosure/bounded-tool-search.js:34` `name: 'tool_search'`；本卡探针 deny（§2.2） |
| R49 | `mcp_invoke` | MCP 披露面延迟注册：延迟加载调用网关（与 R48 同族） | 003 轮同族定位（未在该现场回合出现）；本卡 3.1.10 asar 实测 `agent-tools/dist/mcp-disclosure/loading.js:8` `tool.def.name === 'mcp_invoke'`；本卡探针 deny |
| R50 | `mcp_browser` | 本地 browser 复合工具的**别名转正定义**（3.1.9 起可按此名调用） | 003 轮现场 proceed×1；`local-turn-tool-catalog.js:254-260`（"same compact one renamed"，002 卡「别名不可调用」结论在 3.1.9+ 失效）；本卡 3.1.10 asar 实测同一结构（catalog:52）；本卡探针 deny |
| R51 | `get_goal` | goal 面线程目标读取（3.1.10 实测新增注册面，第四轮现场发现） | **第四轮现场 proceed×1**（round-4 B 臂会话 enforcement 记录，gate_result="proceed"）；3.1.10 asar 定位 `@mavis/goal/dist/tool-defs.js:141`；探针 deny（§2.2） |
| R52 | `create_goal` | goal 面线程目标创建（与 R51 同面） | 同面整组入清单（「可定义全集」口径，`goal/dist/tool-defs.js` 同文件三 defs）；探针 deny |
| R53 | `update_goal` | goal 面线程目标更新（与 R51 同面） | 同上；探针 deny |

两条纪律（002 报告 §6.2 口径）：

1. 工具名必须是**运行时精确名**；
2. MCP 一律服务器级 `mcp__<server>`——整服 deny 由引擎 `findMcpServerRule`
   匹配 `mcp__<server>__<tool>` 前缀，不必逐工具枚举。

> MCP server 清单**随装随变**：执行卡启动时须先枚举当轮实际配置的 MCP server，
> 把每个 server 以 `mcp__<server>` 追加进 deny 清单后再注入（见 §4 步骤 0）。

---

## 2. 验证配方（每条规则的可复跑验证命令与预期输出）

### 2.0 注册表枚举（XJ-20261031-002 新增：deny 清单的机械出处）

deny 清单不是手抄名单，是**枚举脚本的机械输出**。枚举器 `enumerate-registry.mjs`
静态扫描解包树（§2.1）中所有能定义桌面可达工具的面，按出处分类输出：

```javascript
// enumerate-registry.mjs —— 用法：node enumerate-registry.mjs <asar-extract-root>
// 退出码 0 = 枚举完成且 agent-core 层 defs 无桌面注册表之外的孤儿名；否则 exit 1
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(process.argv[2] ?? 'asar');
const rel = (...p) => path.join(ROOT, 'node_modules', '@mavis', ...p);
const read = (p) => fs.readFileSync(rel(p), 'utf8');

// 1) static ToolDef exports (builtin-defs re-exports browser defs; read both directly)
const toolDefRe = /export const Local\w*ToolDef = \{\s*name: '([^']+)'/g;
const staticDefs = {};
for (const f of ['agent-tools/dist/desktop/builtin-defs.js',
                 'agent-tools/dist/desktop/builtin-browser-defs.js']) {
  staticDefs[f] = [...read(f).matchAll(toolDefRe)].map((m) => m[1]);
}

// 2) registry-builder implementation files: inline def names (session_create,
//    website_deploy, workspace_semantic_search, web_search impl, mavis impl, cron impl)
const builderFiles = [
  'agent-tools/dist/desktop/local-session-create-tool.js',
  'agent-tools/dist/desktop/local-website-deploy.js',
  'agent-tools/dist/desktop/local-workspace-semantic-search.js',
  'agent-tools/dist/desktop/local-web-search.js',
  'agent-tools/dist/desktop/local-mavis.js',
  'agent-tools/dist/desktop/local-cron-tools.js',
  'agent-tools/dist/shared/web-search.js', // WebSearchToolDef：本地 web_search 实现与 matrix builtin 共用
  'agent-tools/dist/mcp-disclosure/bounded-tool-search.js', // tool_search：MCP 披露延迟注册面（3.1.9+，XJ-20261102-001 补源）
  'goal/dist/tool-defs.js', // goal 面 create_goal/get_goal/update_goal（3.1.10 现场发现，XJ-20261104-001 补源）
];
const inlineNameRe = /(?:def\s*[:=]\s*\{|name)\s*:\s*'([a-z_][a-z0-9_]*)'/g;
const inlineNames = {};
for (const f of builderFiles) {
  inlineNames[f] = [...read(f).matchAll(inlineNameRe)].map((m) => m[1])
    .filter((n) => !['id', 'mode', 'value'].includes(n));
}

// 3) cron/self_reminder canonical name lists
const cronSrc = read('agent-tools/dist/cron/tool-defs.js');
const cronList = cronSrc.match(/CRON_TOOL_NAMES = \[([^\]]+)\]/s)?.[1]
  .match(/'([a-z_]+)'/g).map((s) => s.slice(1, -1));
const mavisCapList = cronSrc.match(/MAVIS_CAPABILITY_TOOL_NAMES = \[([^\]]+)\]/s)?.[1]
  .match(/'([A-Za-z_]+)'/g).map((s) => s.slice(1, -1));

// 4) extension-registered builtin tools
const miniappNames = [...read('agent-extension/dist/miniapp.js').matchAll(/name: '([a-z_]+)'/g)].map((m) => m[1]);
const planNames = [...read('agent-extension/dist/plan-mode.js').matchAll(/lifecycleTool\('([A-Za-z]+)'/g)].map((m) => m[1]);

// 4.5) MCP 披露延迟注册面（3.1.9+）与别名转正定义（XJ-20261102-001 补源）
const mcpInvoke = [...read('agent-tools/dist/mcp-disclosure/loading.js').matchAll(/def\.name === '([a-z_]+)'/g)].map((m) => m[1]);
const catalogSrc = read('local-runtime-v2/dist/service/turn-system/agent-host/assembly/local-turn-tool-catalog.js');
const aliasNames = [...catalogSrc.matchAll(/selectorAlias: '([A-Za-z_]+)'/g)].map((m) => m[1]);

// 4.6) goal 面线程目标工具（3.1.10 现场发现，XJ-20261104-001 补源）
const goalDefs = [...read('goal/dist/tool-defs.js').matchAll(/name: '([a-z_]+)'/g)].map((m) => m[1]);

// 5) builtin MCP servers (server-level deny rules)
const matrixServer = read('local-runtime-v2/dist/service/mcp/runtime/builtin-matrix.js')
  .match(/BUILTIN_MATRIX_SERVER_NAME = '([^']+)'/)?.[1];
const browserServer = 'browser'; // 002 D2 实测：mcp__browser__navigate 命中服务器规则 mcp__browser

// 6) agent-core layer defs (cross-check: must be subset of the desktop namespace)
const coreDefs = [...read('agent-core/dist/tools/builtin-defs.js').matchAll(toolDefRe)].map((m) => m[1])
  .concat([...read('agent-core/dist/tools/builtin-defs.js').matchAll(/name: '([a-z_]+)'/g)].map((m) => m[1]));

const registry = [
  ...new Set([...staticDefs['agent-tools/dist/desktop/builtin-defs.js'],
              ...staticDefs['agent-tools/dist/desktop/builtin-browser-defs.js'],
              ...Object.values(inlineNames).flat(),
              ...(cronList ?? []),
              ...miniappNames,
              ...planNames,
              ...mcpInvoke,
              ...aliasNames,
              ...goalDefs])].sort();

const coreOnly = coreDefs.filter((n) => !registry.includes(n));

console.log('### A. builtin-defs.js static ToolDefs:',
  staticDefs['agent-tools/dist/desktop/builtin-defs.js'].length);
console.log(JSON.stringify(staticDefs['agent-tools/dist/desktop/builtin-defs.js']));
console.log('### B. builtin-browser-defs.js browser family:',
  staticDefs['agent-tools/dist/desktop/builtin-browser-defs.js'].length);
console.log(JSON.stringify(staticDefs['agent-tools/dist/desktop/builtin-browser-defs.js']));
console.log('### C. registry-builder inline names:');
for (const [f, names] of Object.entries(inlineNames))
  console.log(`  ${path.basename(f)}: ${JSON.stringify([...new Set(names)])}`);
console.log('### D. CRON_TOOL_NAMES:', JSON.stringify(cronList));
console.log('### E. MAVIS_CAPABILITY_TOOL_NAMES:', JSON.stringify(mavisCapList));
console.log('### F. extension-registered: miniapp', JSON.stringify([...new Set(miniappNames)]),
  '| plan-mode lifecycle', JSON.stringify(planNames));
console.log('### F2. mcp-disclosure deferred (3.1.9+):', JSON.stringify([...new Set(mcpInvoke)]),
  '| alias-promoted callables:', JSON.stringify([...new Set(aliasNames)]));
console.log('### F3. goal face (3.1.10+):', JSON.stringify([...new Set(goalDefs)]));
console.log('### G. builtin MCP servers:', JSON.stringify([browserServer, matrixServer]));
console.log('### H. agent-core defs NOT in desktop registry (must be []):', JSON.stringify([...new Set(coreOnly)]));
console.log(`### TOTAL distinct desktop tool names: ${registry.length}`);
console.log(JSON.stringify(registry));
process.exit(coreOnly.length ? 1 : 0);
```

```
node enumerate-registry.mjs asar
# -> ### A..H 分类输出 + TOTAL distinct desktop tool names: N + 全名 JSON
# -> exit 0（H 段为空 = agent-core 层 defs 全部被桌面注册表包含）
# 本机 3.1.10 实测（2026-11-04，asar 4020+19 files，XJ-20261104-001）：N=51
# 历史轮（3.1.7，2026-10-31，XJ-20261031-002）：N=45；历史轮（3.1.9，2026-11-02，XJ-20261102-001）：N=48
# （3.1.9 帧不可回采：更新器于 002 重测后覆盖安装 3.1.9→3.1.10，见指纹文档 §2.8）
```

**枚举口径**（两路枚举纪律，回应 001 评审 ADV-2；XJ-20261102-001 扩源）：

1. **本地工具注册表一路**：`buildLocalToolRegistry`（`agent-tools/dist/desktop/index.js`）
   的静态 def 面（§A）+ 注册器内联构建名（§C：session_create / website_deploy /
   workspace_semantic_search / self_reminder / web_search）+ cron 族规范名
   （§D：`CRON_TOOL_NAMES`）+ 扩展条件注册（§F：miniapp / EnterPlanMode /
   ExitPlanMode）+ **MCP 披露延迟注册面（§F2：`tool_search` / `mcp_invoke`，
   3.1.9+ 新增，XJ-20261102-001 补源）+ 别名转正定义（§F2：`mcp_browser`，
   3.1.9 起可按别名调用）+ goal 面线程目标工具（§F3：`create_goal` / `get_goal` /
   `update_goal`，3.1.10 现场发现，XJ-20261104-001 补源）**；
2. **MCP server 一路**：builtin server 名（§G：`browser`、`matrix`）+ 轮时按 §4
   步骤 0 枚举第三方面。

**静态枚举的已知逃逸面与处置**（回应卡面评审问 Q2；XJ-20261102-001 更新）：

- **MCP 原生名投影**：MCP 工具以 `mcp__<server>__<tool>` 原生名进目录
  （`native-tool-projection.js` `buildNativeToolName`）——不被本地名枚举覆盖，
  由**服务器级规则**整服 deny（R12/R47），轮时枚举 server 清单即可；
- **MCP 披露延迟注册面**：`tool_search`/`mcp_invoke`（`mcp-disclosure/`，按需
  延迟加载 MCP 工具的门面工具）——003 轮现场坐实 `tool_search` proceed 后，002 卡
  已把该面**纳入枚举器一级来源**（§F2），不再属于逃逸面；
- **mcp_invoke 的 gate 不可见通道（XJ-20261104-001 现场发现，已知盲区登记）**：
  第四轮 B 臂现场，minimax 经 `mcp_invoke` 枚举延迟工具目录成功，而
  `permission.enforcement` 记录面**零记录**——该调用路径不经过门禁记录面，R49
  规则在其上**不可执行也不可观测**。影响面实测收敛：仅目录列举可见（cron/session
  族），延迟工具本体的调用仍按名经过门禁且被拒（session_create/cron_create/
  cron_read 现场 blocked）。处置：R49 保留（同名路径仍可拦），本盲区登记为
  已知边界；其彻底封堵属运行时仪器改动（超出门禁清单职责）；
- **goal 面线程目标工具**：`get_goal` 第四轮现场 proceed×1 后，`goal/dist/
  tool-defs.js` 整面（create_goal/get_goal/update_goal）纳入枚举器一级来源
  （§F3）并入清单（R51–R53）；
- **别名转正**：`mcp_browser` 在 3.1.9+ 是 browser 复合工具按别名暴露的**可调用
  定义**（catalog `selectorAlias` + "same compact one renamed"），003 轮现场
  proceed×1 坐实——002 卡「别名不可调用」的旧结论作废，R50 按可调用名 deny；
- **条件注册**：本地注册表多数工具按 deps 条件注册（对照表「注册条件」列）——
  deny 规则按**名**匹配，未注册名的规则惰性无害，清单取「可定义全集」口径；
- **第三方插件动态注册**（`agent-runtime` registry/factories 机制）：静态不可知，
  归 §4 步骤 0 轮时「当轮工具目录核对」纪律；
- **不在桌面目录的面**（002 卡核对后排除，非遗漏；3.1.10 复核仍成立）：
  `agent-tools/dist/cloud/*` 云产品 defs（含 `memory_search`——该名在桌面注册表
  不存在，桌面记忆/检索面是 `memory` 与 `workspace_semantic_search`，均已 deny）；
  `threadGoalTools`（goal-agent 评估者/子代理线程面，非执行者主线程目录）。

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

### 2.2 探针：整工具 deny + bypass 免疫 + 只读面 + MCP 服务器级（一次跑完全清单 53 规则）

探针 `b_arm_deny_probe.mjs` 把 §1 的 deny 清单写入**临时 dataDir** 的
`permission.json`（绝不指向真实 profile），送入真实权限引擎
（`@mavis/permission/dist/engine.js` `PermissionEngine.checkPermission()`），
对**每条规则一个案例**（51 个注册表工具名 + 2 个服务器路径探针
`mcp__browser__navigate` / `mcp__matrix__web_search`）在 `bypassPermissions` 与
`default` 两种模式下各判一次——全清单 × 2 模式，不是抽测：

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

// R1-R12（001 卡原清单，未动）+ R13-R47（002 卡注册表补全，出处 §2.0 枚举）。
// 纯增口径：12 规则清单零删改。
const DENY = [
  // R1-R11 本地工具（001 卡原清单，未动）
  'bash', 'write', 'edit', 'read', 'glob', 'grep', 'task', 'todowrite',
  'web_fetch', 'web_search', 'miniapp',
  // R12 builtin MCP server（001 卡原清单，未动）
  'mcp__browser',
  // R13-R30 本地注册表补全（枚举脚本 §2.0 输出）
  'skill', 'memory', 'code_review', 'mavis', 'session_create',
  'self_reminder', 'cron_create', 'cron_read', 'cron_update', 'cron_delete',
  'ask_user', 'request_feature_enable',
  'task_append', 'task_query', 'task_output', 'task_stop',
  'website_deploy', 'workspace_semantic_search',
  // R31-R44 本地原生浏览器族（14 项全列）
  'browser', 'browser_inspect', 'browser_navigate', 'browser_click', 'browser_type',
  'browser_press_key', 'browser_scroll', 'browser_hover', 'browser_wait_for',
  'browser_get_dom', 'browser_screenshot', 'browser_paste', 'browser_verify_text',
  'browser_inspect_editable_targets',
  // R45-R46 扩展注册（plan-mode lifecycle）
  'EnterPlanMode', 'ExitPlanMode',
  // R47 builtin MCP server（matrix）
  'mcp__matrix',
  // R48-R50 3.1.9+ 版本续篇（XJ-20261102-001：MCP 披露延迟注册面 + 别名转正）
  'tool_search', 'mcp_invoke', 'mcp_browser',
  // R51-R53 goal 面线程目标工具（XJ-20261104-001：3.1.10 现场发现补全）
  'get_goal', 'create_goal', 'update_goal',
];

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
  ['task', { prompt: 'x' }],
  ['todowrite', { todos: [] }],
  ['web_fetch', { url: 'https://example.com' }],
  ['web_search', { query: 'probe' }],
  ['miniapp', {}],
  ['skill', { name: 'probe' }],
  ['memory', { action: 'search', query: 'probe' }],
  ['code_review', {}],
  ['mavis', { query: 'probe' }],
  ['session_create', { agent_name: 'probe' }],
  ['self_reminder', { message: 'probe' }],
  ['cron_create', { name: 'probe', schedule: 'daily', prompt: 'x' }],
  ['cron_read', {}],
  ['cron_update', { id: 'x' }],
  ['cron_delete', { id: 'x' }],
  ['ask_user', { question: 'probe' }],
  ['request_feature_enable', { feature: 'probe' }],
  ['task_append', { task_id: 'x', prompt: 'x' }],
  ['task_query', { task_id: 'x' }],
  ['task_output', { task_id: 'x' }],
  ['task_stop', { task_id: 'x' }],
  ['website_deploy', {}],
  ['workspace_semantic_search', { query: 'probe' }],
  ['browser', { action: 'navigate', url: 'https://example.com' }],
  ['browser_inspect', {}],
  ['browser_navigate', { url: 'https://example.com' }],
  ['browser_click', { ref: 'r1' }],
  ['browser_type', { ref: 'r1', text: 'x' }],
  ['browser_press_key', { key: 'Enter' }],
  ['browser_scroll', { direction: 'down' }],
  ['browser_hover', { ref: 'r1' }],
  ['browser_wait_for', { text: 'x' }],
  ['browser_get_dom', {}],
  ['browser_screenshot', {}],
  ['browser_paste', { text: 'x' }],
  ['browser_verify_text', { texts: ['x'] }],
  ['browser_inspect_editable_targets', {}],
  ['EnterPlanMode', {}],
  ['ExitPlanMode', {}],
  // 服务器级规则探针：每个 builtin server 取一条 mcp__<server>__<tool> 路径名
  ['mcp__browser__navigate', { url: 'https://example.com' }],
  ['mcp__matrix__web_search', { query: 'probe' }],
  ['tool_search', { query: 'probe' }],
  ['mcp_invoke', { tool_name: 'probe' }],
  ['mcp_browser', { action: 'navigate', url: 'https://example.com' }],
  ['get_goal', {}],
  ['create_goal', { title: 'probe' }],
  ['update_goal', { goal_id: 'x' }],
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
`{"type":"rule","rule":{"source":"global","ruleBehavior":"deny","ruleValue":{"toolName":"<规则串>","matcher":{"kind":"tool"}},"destination":"global"}}`，
其中 `<规则串>` = 该案例命中的 deny 规则串（名规则 = 工具名本身，服务器级规则 =
`mcp__<server>`））：

- **名规则（R1–R11、R13–R46、R48–R50、R51–R53，共 51 条）**：探针行 `<工具名> -> deny`，
  reason `toolName` = 同名规则串；
- **服务器级规则（R12、R47）**：探针行 `mcp__browser__navigate -> deny`（toolName=
  `mcp__browser`）与 `mcp__matrix__web_search -> deny`（toolName=`mcp__matrix`）；
- **逐条对照**：注册表枚举项 ↔ 规则号 ↔ 两模式探针实测结果，见 §3 第二轮对照表
  （47 行，零遗漏）。

**对照读数**（复用 002 报告 §3.2 的 CONTROL 场景，防「恒 deny」假象）：同一引擎在
**无 deny 规则**时，`bypassPermissions` 下全部 `allow`、`default` 下安全命令与
非交互工具 `allow`/`ask`——即 deny 只由规则产生，不是引擎默认。002 卡 D2 已实测
该对照；闭合轮复跑时按 `docs/mechanism-closure-round.md` §2 S1 一并取对照。

---

## 3. 配方复测记录

### 3.1 第一轮（XJ-20261031-001，12 规则）

- **执行者**：ZCode（001 卡执行者）。**落点**：仓外临时目录（验证后整体删除，不在仓内
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

### 3.2 第二轮（XJ-20261031-002，47 规则全清单）

- **执行者**：ZCode（002 卡执行者）。**落点**：仓外临时目录（`extract-asar.mjs` →
  `extracted 3901 files (skipped 0 non-regular) ... exit 0`，与第一轮同配方；验证后
  整体删除）。**独立性**（约束 4）：本轮枚举与探针由本卡执行者独立实跑，非照抄
  001 评审 verdict 文本——两份独立采集构成交叉验证。
- **枚举命令与输出原文**（`node enumerate-registry.mjs asar`，**exit 0**）：

```
### A. builtin-defs.js static ToolDefs: 19
["read","write","edit","bash","grep","glob","todowrite","skill","code_review","memory","ask_user","request_feature_enable","web_fetch","task","task_append","task_query","task_output","task_stop","mavis"]
### B. builtin-browser-defs.js browser family: 14
["browser","browser_inspect","browser_navigate","browser_click","browser_type","browser_press_key","browser_scroll","browser_hover","browser_wait_for","browser_get_dom","browser_screenshot","browser_paste","browser_verify_text","browser_inspect_editable_targets"]
### C. registry-builder inline names:
  local-session-create-tool.js: ["session_create"]
  local-website-deploy.js: ["website_deploy"]
  local-workspace-semantic-search.js: ["workspace_semantic_search"]
  local-web-search.js: []
  local-mavis.js: ["mavis"]
  local-cron-tools.js: ["self_reminder"]
  web-search.js: ["web_search"]
### D. CRON_TOOL_NAMES: ["self_reminder","cron_create","cron_read","cron_update","cron_delete"]
### E. MAVIS_CAPABILITY_TOOL_NAMES: ["mavis","session_create"]
### F. extension-registered: miniapp ["miniapp"] | plan-mode lifecycle ["EnterPlanMode","ExitPlanMode"]
### G. builtin MCP servers: ["browser","matrix"]
### H. agent-core defs NOT in desktop registry (must be []): []
### TOTAL distinct desktop tool names: 45
["EnterPlanMode","ExitPlanMode","ask_user","bash","browser","browser_click","browser_get_dom","browser_hover","browser_inspect","browser_inspect_editable_targets","browser_navigate","browser_paste","browser_press_key","browser_screenshot","browser_scroll","browser_type","browser_verify_text","browser_wait_for","code_review","cron_create","cron_delete","cron_read","cron_update","edit","glob","grep","mavis","memory","miniapp","read","request_feature_enable","self_reminder","session_create","skill","task","task_append","task_output","task_query","task_stop","todowrite","web_fetch","web_search","website_deploy","workspace_semantic_search","write"]
```

- **探针实测**（`node b_arm_deny_probe.mjs asar dataDir`，全清单 47 规则 × 2 模式，
  非抽测）：**exit 0**，末行 `### cases=47 x modes=2; failures=0`，**94/94 行
  `deny`**；两模式逐行同形（reason 逐字段一致，形态同 §2.2 统一口径）。

- **对照表（注册表枚举项 ↔ 规则号 ↔ 当轮注册条件 ↔ 探针实测；45 工具名 + 2 builtin
  服务器 = 47 规则，零遗漏、零「未映射」残留）**：

| # | 枚举项 | 来源段 | 当轮注册条件（代码面） | 规则号 | 探针（bypass/default） |
|---|---|---|---|---|---|
| 1 | read | §A | 常驻 | R4 | deny / deny |
| 2 | write | §A | 常驻 | R2 | deny / deny |
| 3 | edit | §A | 常驻 | R3 | deny / deny |
| 4 | bash | §A | 常驻 | R1 | deny / deny |
| 5 | grep | §A | 常驻 | R6 | deny / deny |
| 6 | glob | §A | 常驻 | R5 | deny / deny |
| 7 | todowrite | §A | 常驻（`enableTodoWriteTool` 可门控） | R8 | deny / deny |
| 8 | skill | §A | skillReader（常驻传入） | R13 | deny / deny |
| 9 | code_review | §A | codeReviewAdapter | R15 | deny / deny |
| 10 | memory | §A | memoryFacade + 配置门（本机 `memory.enabled: false` → 当轮未注册，规则按名惰性无害） | R14 | deny / deny |
| 11 | ask_user | §A | askUserAdapter（`buildLocalAskUserAdapter` 常驻传入） | R23 | deny / deny |
| 12 | request_feature_enable | §A | askUserAdapter（同上） | R24 | deny / deny |
| 13 | web_fetch | §A | 常驻（`LocalWebFetchClient` 无条件构造） | R9 | deny / deny |
| 14 | task | §A | delegation 门（`enableTaskTool !== false && features.delegation`） | R7 | deny / deny |
| 15 | task_append | §A | 同 task（同一委托入口门） | R25 | deny / deny |
| 16 | task_query | §A | taskControlAdapter 门（`enableTaskControlTools`） | R26 | deny / deny |
| 17 | task_output | §A | 同 task_query | R27 | deny / deny |
| 18 | task_stop | §A | 同 task_query | R28 | deny / deny |
| 19 | mavis | §A/§C | mavisAgentAdapter | R16 | deny / deny |
| 20 | browser | §B | browser-use 服务（桌面宿主有 browser host；目录选择别名 `mcp_browser` 非可调用名） | R31 | deny / deny |
| 21 | browser_inspect | §B | 同上 | R32 | deny / deny |
| 22 | browser_navigate | §B | 同上 | R33 | deny / deny |
| 23 | browser_click | §B | 同上 | R34 | deny / deny |
| 24 | browser_type | §B | 同上 | R35 | deny / deny |
| 25 | browser_press_key | §B | 同上 | R36 | deny / deny |
| 26 | browser_scroll | §B | 同上 | R37 | deny / deny |
| 27 | browser_hover | §B | 同上 | R38 | deny / deny |
| 28 | browser_wait_for | §B | 同上 | R39 | deny / deny |
| 29 | browser_get_dom | §B | 同上 | R40 | deny / deny |
| 30 | browser_screenshot | §B | 同上 | R41 | deny / deny |
| 31 | browser_paste | §B | 同上 | R42 | deny / deny |
| 32 | browser_verify_text | §B | 同上 | R43 | deny / deny |
| 33 | browser_inspect_editable_targets | §B | 同上 | R44 | deny / deny |
| 34 | session_create | §C | mavisAgentAdapter + mavisSessionAdapter | R17 | deny / deny |
| 35 | website_deploy | §C | 常驻（`LocalWebsiteDeployClient` 在 `buildLocalNativeRuntimeTools` 无条件构造） | R29 | deny / deny |
| 36 | workspace_semantic_search | §C | workspaceSemanticSearchAdapter | R30 | deny / deny |
| 37 | web_search | §C | native 面 `webSearchEnabled === true`；另经 matrix builtin（MCP 面） | R10 | deny / deny |
| 38 | self_reminder | §C/§D | mavisCronAdapter | R18 | deny / deny |
| 39 | cron_create | §D | mavisCronAdapter | R19 | deny / deny |
| 40 | cron_read | §D | mavisCronAdapter | R20 | deny / deny |
| 41 | cron_update | §D | mavisCronAdapter | R21 | deny / deny |
| 42 | cron_delete | §D | mavisCronAdapter | R22 | deny / deny |
| 43 | miniapp | §F | 扩展条件注册（`exposesMiniAppControl(context)`） | R11 | deny / deny |
| 44 | EnterPlanMode | §F | 扩展条件注册（`!ctx.plan && agentEntryEnabled()`） | R45 | deny / deny |
| 45 | ExitPlanMode | §F | 扩展条件注册（`ctx.plan` 时） | R46 | deny / deny |
| 46 | —（builtin server） | §G | builtin MCP server `browser`（工具以 `mcp__browser__<tool>` 原生名进目录） | R12 | `mcp__browser__navigate` -> deny / deny |
| 47 | —（builtin server） | §G | builtin MCP server `matrix`（`BUILTIN_MATRIX_SERVER_NAME`；工具以 `mcp__matrix__<tool>` 原生名投影，服务器级规则整服覆盖其全部工具） | R47 | `mcp__matrix__web_search` -> deny / deny |

- **与 001 评审采集的交叉验证**（两份独立枚举的增量，非矛盾）：本卡机械枚举在
  评审所列清单（静态 defs + 浏览器族）之外，另覆盖注册器内联构建名
  （session_create / website_deploy / workspace_semantic_search / self_reminder）、
  cron 族规范名（`CRON_TOOL_NAMES` 四项）、扩展注册（EnterPlanMode / ExitPlanMode）
  与第二 builtin server（`mcp__matrix`）——共 12 项为 001 清单与 R1–R12 之外的
  新增规则面。名称勘误：`memory_search` 在 3.1.7 桌面注册表**不存在**（该 def 在
  `agent-tools/dist/cloud/cloud-memory.js` 云面）；桌面记忆/检索面是 `memory`
  （R14）与 `workspace_semantic_search`（R30），均已 deny。R15（code_review）
  显式入清单后不再依赖引擎工具组映射的附带命中（回应 001 评审 ADV-1）。

- **边界**：本轮仍是**引擎层**实测（与第一轮同层），现场层证据留待闭合轮（§5）；
  `dataDir` 指向临时目录，未触碰本机真实 profile；仓外 temp 目录验证后整体删除，
  仓内无实验残留。清单为**纯增**：R1–R12 未删未改，新增 R13–R47（约束 5 红线
  未触碰——无任何工具被放行）。

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
