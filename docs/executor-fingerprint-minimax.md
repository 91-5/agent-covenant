# 执行者指纹：MiniMax Code（第四轮第四轮带工具执行者候选）

- **卡**：XJ-20261030-002 / D1
- **采集日期**：2026-10-30（UTC+8）
- **采集者**：minimax code（本卡实现者）
- **采集主机**：Windows 11 / x64，`python 3.14.4`，`node v24.18.0`
- **采集范围**：本机 MiniMax Code 桌面端安装（region `cn`，appId `com.minimax.agent.cn`）

> **自我报告声明（卡面约束 6）**
> 本卡实现者与第四轮被测执行者是**同一个工具**（minimax code）。因此本文件的指纹属
> **自我报告**，不得当作独立第三方观测。凡本文件写入的每个字段，均附**可复跑命令**与
> **退出码**；评审者可在同一台机器上独立复跑验证。凡本机无法观测的字段，一律记为
> **不可锁**，不做推测填充。

> **术语纪律（EVO-20261024-001）**
> 本文件只描述「本机当前配置与安装状态的观测」，不含任何效果结论，不出现「证明」「有效」
> 「显著」等措辞。

---

## 1. 指纹主表

| # | 字段 | 观测值 | 采集命令 | 退出码 | 状态 |
|---|---|---|---|---|---|
| F1 | 产品名 | `MiniMax Code`（CompanyName `MiniMax`） | 见 §2.1 | 0 | 已验证 |
| F2 | 桌面端版本号（安装包语义） | `3.1.7` | 见 §2.2 | 0 | 已验证 |
| F3 | 可执行文件版本号 | `3.1.7.195` | 见 §2.1 | 0 | 已验证 |
| F4 | 构建哈希（shell fingerprint） | `11c2328d0e7ec036f12fd025a1e06d75f987c164a37ae4a9b76ebcc85b737f72` | 见 §2.2 | 0 | 已验证 |
| F5 | 热更新状态 | `enabled: true`，`channel: prod`，`appVersion: 3.1.7`，`active: null`，`pending: null`，`lastUpdateTime: 0` | 见 §2.3 | 0 | 已验证 |
| F6 | 模型快照（目录 id） | `MiniMax-M3.1-Flash`（`defaultModel: minimax/MiniMax-M3.1-Flash`） | 见 §2.4 | 0 | 已验证 |
| F7 | 思考变体 / 思考强度 | `defaultModelVariant: thinking`；`defaultModelThinking.effort: high` | 见 §2.4 | 0 | 已验证 |
| F8 | 上下文窗口设定 | `defaultModelContextWindow: 1000000`；模型目录 `limit.context: 512000`，`limit.output: 128000` | 见 §2.4 | 0 | 已验证 |
| F9 | API endpoint | `https://agent.minimax.cn/mavis/api/v1/llm/v1` | 见 §2.4 | 0 | 已验证 |
| F10 | 凭据 | 配置内为占位 `apiKey: sk-xxx`；真实凭据在 auth 存储内，本卡**不读取、不落盘** | 见 §2.4 | 0 | 已验证（占位形态） |
| F11 | 运行模式 | `permissionMode: bypassPermissions`；`appModePreference: coding`；`workingDirectory: D:\15812\Documents` | 见 §2.4 / §2.5 | 0 | 已验证 |
| F12 | 运行时包版本 | `@mavis/local-runtime-v2 0.1.0`（private）；`@mavis/local-runtime`（权限规则存储）；`mcode-tools` CLI `0.0.6` | 见 §2.6 | 0 | 已验证 |
| F13 | 自动更新 | **开启**（稳定通道每小时静默检查）；仅预览通道关闭（`earlyAccessUpdateEnabled: false`） | 见 §2.7 | 0 | 已验证 |
| F14 | 采样参数（temperature / top_p / max_tokens） | **不可锁**（详见 §3） | 见 §3 | 0 | 不可锁 |
| F15 | 服务端模型快照（权重/快照日期） | **不可锁**（客户端不暴露） | 见 §3 | — | 不可锁 |

**F13 的运行风险**：`promptConfig.autoUpdate` 未设置时默认 `true`（prod 构建），
意味着正式轮次进行中**存在自动升级导致指纹漂移的可能**。这是 D1 中唯一一条
「当前状态与第四轮要求相反」的字段，处理方案见 §4。

---

## 2. 采集命令与原始输出

所有命令在 PowerShell 5.1 下执行，工作目录不限（命令内为绝对路径）。

### 2.1 可执行文件版本（F1 / F3）

```powershell
(Get-Item 'D:\MiniMaxcode\MiniMax Code\MiniMax Code.exe').VersionInfo |
  Format-List FileVersion,ProductVersion,ProductName,CompanyName
```

退出码 `0`。输出摘录：

```
FileVersion      : 3.1.7.195
ProductVersion   : 3.1.7.195
ProductName      : MiniMax Code
CompanyName      : MiniMax
```

### 2.2 版本号与构建哈希（F2 / F4）

`app.asar` 为 Electron 打包格式，下列单行命令直接解析其头部索引并取出两个条目，
无需安装 `asar` 工具：

```powershell
node -e "const fs=require('fs');const p='D:/MiniMaxcode/MiniMax Code/resources/app.asar';const fd=fs.openSync(p,'r');const b=Buffer.alloc(16);fs.readSync(fd,b,0,16,0);const n=b.readUInt32LE(4);const h=Buffer.alloc(n);fs.readSync(fd,h,0,n,8);const L=h.readUInt32LE(4);const H=JSON.parse(h.slice(8,8+L).toString('utf8'));const ds=8+n;function get(rel){let e={files:H.files};for(const s of rel.split('/')){e=e.files[s];}const buf=Buffer.alloc(e.size);fs.readSync(fd,buf,0,e.size,ds+Number(e.offset));return buf.toString('utf8');}console.log('package.json version:',JSON.parse(get('package.json')).version);console.log('shellFingerprint:',JSON.parse(get('dist/hot-update-shell.json')).shellFingerprint);"
```

退出码 `0`。输出：

```
package.json version: 3.1.7
shellFingerprint: 11c2328d0e7ec036f12fd025a1e06d75f987c164a37ae4a9b76ebcc85b737f72
```

> F4 的语义边界：`shellFingerprint` 是**外壳（shell）指纹**，与热更新下发的渲染层
> 资源分开。热更新通道开启时（F5 `enabled: true`），渲染层可被替换而
> `package.json` 版本号不变。故正式轮次的指纹必须 **F2+F3+F4+F5 一起记录**，
> 单看版本号不足以固定执行面。

### 2.3 热更新状态（F5）

```powershell
Get-Content 'C:\Users\15812\AppData\Roaming\MiniMax\hot-update\state.json' -Raw
```

退出码 `0`。输出：

```json
{
  "schemaVersion": 2,
  "enabled": true,
  "channel": "prod",
  "locale": "zh",
  "appVersion": "3.1.7",
  "shellFingerprint": "11c2328d0e7ec036f12fd025a1e06d75f987c164a37ae4a9b76ebcc85b737f72",
  "latestManifestVersion": null,
  "active": null,
  "pending": null,
  "lastKnownGood": null,
  "bootAttempts": 0,
  "resetToBundled": false,
  "revoked": [],
  "lastCheckTime": 1793275630444,
  "lastUpdateTime": 0
}
```

### 2.4 模型 / endpoint / 模式（F6–F10 / F11）

```powershell
Get-Content 'C:\Users\15812\.minimax\config.yaml' -Raw
```

退出码 `0`。与本文件有关的字段（原文摘录，未改写）：

```yaml
provider:
  minimax:
    npm: '@ai-sdk/anthropic'
    models:
      MiniMax-M3.1-Flash:
        name: M3.1-Flash
        attachment: true
        reasoning: true
        temperature: true          # ← 能力标志，非数值采样参数（见 §3）
        tool_call: true
        limit:
          context: 512000
          output: 128000
        thinking_config:
          mode: forced_on
        thinking:
          effortOptions: [default, low, medium, high, xhigh, max]
          defaultEffort: default
    options:
      apiKey: sk-xxx
      baseURL: https://agent.minimax.cn/mavis/api/v1/llm/v1
defaultModel: minimax/MiniMax-M3.1-Flash
defaultModelContextWindow: 1000000
defaultModelThinking:
  effort: high
defaultModelVariant: thinking
permissionMode: bypassPermissions
```

### 2.5 桌面端设置（F11 / F13 前半）

```powershell
Get-Content 'C:\Users\15812\AppData\Roaming\MiniMax\minimax-agent-cn-config.json' -Raw
```

退出码 `0`。相关字段：

```json
"appModePreference": { "value": "coding", "updatedAt": 1792774379396 },
"earlyAccessUpdateEnabled": false,
"developerOptions": { "enabled": true, "autoOpenNativeDevTools": false },
"chatPermissions": {},
"workingDirectory": "D:\\15812\\Documents",
"runOnStartup": true,
```

> `chatPermissions: {}` —— 当前**没有任何会话级权限规则**。这与 D2 的结论直接相关：
> 现装状态下，B 臂的「硬禁工具」**尚未预置**，需要显式写入（见
> `docs/dryrun-b-arm-tool-deny.md` §5）。

### 2.6 运行时包版本（F12）

```powershell
mcode-tools --version
```

退出码 `0`，输出 `0.0.6`。

包版本用与 §2.2 相同的 asar 解析法取出：

```powershell
node -e "<§2.2 同款解析器>" node_modules/@mavis/local-runtime-v2/package.json
```

退出码 `0`。输出：`"name": "@mavis/local-runtime-v2", "version": "0.1.0", "private": true`。
`@mavis/local-runtime` 提供权限规则存储（`dist/permissions/rules.js`），
`@mavis/permission` 提供判定引擎（`dist/engine.js`）——D2 的实测对象即此二者。

### 2.7 自动更新状态（F13）

**（a）更新器确实在周期性检查**（日志实测）：

```powershell
Select-String -Path 'C:\Users\15812\AppData\Roaming\MiniMax\logs\update-10-30.log' `
  -Pattern 'Updater' | Select-Object -First 12
```

退出码 `0`。输出（连续三次，间隔一小时）：

```
[2026-10-30 00:06:41.186] [info] [Updater] 收到检查更新请求 (userTriggered: false, status: not-available, cachedVersion: 3.1.7)
[2026-10-30 00:06:41.187] [info] [Updater] 静默检查更新 (当前状态: not-available)
[2026-10-30 00:06:42.288] [info] Update for version 3.1.7 is not available (latest version: 3.1.7, downgrade is disallowed).
[2026-10-30 01:06:41.066] [info] [Updater] 收到检查更新请求 (userTriggered: false, status: not-available, cachedVersion: 3.1.7)
[2026-10-30 02:06:41.254] [info] [Updater] 收到检查更新请求 (userTriggered: false, status: not-available, cachedVersion: 3.1.7)
```

→ 稳定通道的自动更新**处于开启状态**（每小时静默检查）。

**（b）存在可锁的开关**（代码面）：

```powershell
node -e "<§2.2 同款解析器>" node_modules/@mavis/config/dist/config.js   # 再取第 1199-1205 行
```

退出码 `0`。取到的实现（`@mavis/config/dist/config.js:1197-1207`）：

```js
export function resolvePromptConfig(obj) {
    const defaultAutoUpdate = getRuntimeBuildEnv() === 'prod' && !isInternalBuild();
    if (obj == null || typeof obj !== 'object' || Array.isArray(obj)) {
        return { autoUpdate: defaultAutoUpdate };
    }
    const rawAutoUpdate = obj.autoUpdate;
    return {
        autoUpdate: typeof rawAutoUpdate === 'boolean' ? rawAutoUpdate : defaultAutoUpdate,
    };
}
```

→ 关闭方式：`config.yaml` 中设置 `promptConfig.autoUpdate: false`（显式布尔值优先于
默认值）。**当前 `config.yaml` 未设该键**，故取默认 `true`。

**（c）预览通道已关**（F13 补充）：桌面端设置 `earlyAccessUpdateEnabled: false`。
这只关掉 early-access 灰度，**不是**稳定通道的自动更新开关。

---

## 3. 可锁采样参数快照与「不可锁项」声明

### 3.1 可锁（配置面可固定）

| 参数 | 可锁位置 | 当前值 |
|---|---|---|
| 模型 id | `config.yaml` → `defaultModel` | `minimax/MiniMax-M3.1-Flash` |
| 思考变体 | `config.yaml` → `defaultModelVariant` | `thinking` |
| 思考强度 | `config.yaml` → `defaultModelThinking.effort` | `high` |
| 上下文窗口 | `config.yaml` → `defaultModelContextWindow` | `1000000` |
| 权限模式 | `config.yaml` → `permissionMode` | `bypassPermissions`（B 臂需另行预置，见 D2） |
| 自动更新 | `config.yaml` → `promptConfig.autoUpdate` | 未设置 → 默认 `true`（**需在正式 run 前置 false**） |

### 3.2 不可锁项（预注册声明）

以下项目在**当前客户端配置面不存在可固定入口**，第四轮期间只能以「默认值 + 声明」方式
记录；评审与报告引用时必须一并引用本声明：

1. **`temperature`（数值采样温度）** —— 不可锁。
   证据：模型目录中唯一同名字段是**布尔能力标志**，不是数值：
   `@mavis/config/dist/minimax-model-catalog.js:22,40` 为 `temperature: true`；
   `@mavis/local-runtime-v2/dist/http/controllers/model-provider-mappers.js:151`
   把该字段原样当作「能力字段」映射（`toUserModelInputCapabilityFields`）。
   配置面**没有**数值型 temperature 入口，故每轮实际采样温度由服务端默认决定，
   客户端既不可见也不可写。
2. **`top_p`（及 top_k 等核采样参数）** —— 不可锁。
   证据：在 `@mavis/config/dist/` 全包内检索 `temperature|maxTokens|topP|top_p`，
   命中的 `topP`/`top_p` 出现次数为 **0**（仅 `temperature` 能力标志与
   `goal-config.js` 的 `maxTokens`）。
3. **`max_tokens`（每请求输出上限）** —— 不可锁（仅可锁「上限」而非「实际请求值」）。
   证据：`@mavis/config/dist/goal-config.js:14,102` 的 `maxTokens` 属于
   `goal.*`（evaluator / subagent）角色配置；主模型侧只有 `limit.output: 128000`
   这一**天花板**，请求实际下发的 `max_tokens` 不由配置面控制、也不落盘可观测。
4. **服务端模型快照（权重版本 / 快照日期）** —— 不可锁。
   客户端只持有**目录 id** `MiniMax-M3.1-Flash`；同一 id 后端是否已换快照，客户端
   无观测面。故「模型快照」在第四轮中只能表述为**目录 id 层面的快照**。
5. **系统提示词 / 工具 schema 全文** —— 不作为指纹项冻结。
   理由：随热更新（F5 `enabled: true`）与安装包更新变动，且体积过大不便逐轮比对；
   若需要，只能以 F4 `shellFingerprint` + F2/F3 版本号作为**代理锚点**。

---

## 4. 正式轮次前的强制动作（本卡建议，不代执行）

| # | 动作 | 目的 | 状态 |
|---|---|---|---|
| P1 | 在 `config.yaml` 设 `promptConfig.autoUpdate: false`，重启应用后复测更新器日志（不再出现每小时静默检查） | 消除轮次中途自动升级导致的指纹漂移 | **未执行**（本卡只读，未改用户配置） |
| P2 | 预置 B 臂权限规则（`permission.json` 整工具 deny，含 MCP server 级） | 见 `docs/dryrun-b-arm-tool-deny.md` | **未执行**（需在正式 run 前按 D2 结论预置） |
| P3 | 每轮开始与结束各采集一次 F2/F3/F4/F5 并比对 | 检测轮次中途的热更新/升级 | 协议待写入 runbook |

---

## 5. 边界声明

- 本文件记录的是**本机当前安装状态**，不是「MiniMax Code 产品的一般能力」。
- `apiKey` 只观察到占位串 `sk-xxx`；真实凭据不在本文件、也不落盘（本卡不接触凭据）。
- F13 的结论来自**更新器日志与配置解析代码**两处独立证据；「自动更新已关闭」在本机
  **未成立**，不得在报告中写成「已关闭」。
- 本文件任何一行都不构成对第四轮效果的前瞻判断；第四轮结论等执行卡与报告期产生。
