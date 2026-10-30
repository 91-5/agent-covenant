# 执行者自动更新关闭操作规程（轮次前操作项）

- **卡**：XJ-20261031-001 / D3
- **日期**：2026-10-31
- **性质**：**轮次前操作项规程**——闭合 XJ-20261030-002 条件 C3（轮次前环境固定）。
  第四轮执行卡 Acceptance 将引用本规程；本卡**未执行**本规程（未改用户现装配置，
  002 卡指纹文档 §4 P1 同款边界），执行卡启动时按本规程操作并核验。
- **上游实测**：`docs/executor-fingerprint-minimax.md` §2.7（F13：更新器每小时静默
  检查 = 自动更新**开启**；`@mavis/config/dist/config.js:1197-1207`
  `resolvePromptConfig` 显式布尔优先）；`verdicts/XJ-20261030-002.verdict.json`
  条件 C3、`not_verified_disclosed`（自动更新开启态下热更新可替换渲染层）。

---

## 0. 目的与现状事实

**目的**：消除轮次中途自动升级/热更新导致的执行者指纹漂移（F2 版本号 / F3 运行时
包版本 / F4 shell 指纹 / F5 热更新状态），使第四轮「轮次开始与结束各采集
F2/F3/F4/F5 并比对」（指纹文档 §4 P3，002 verdict C3）有可固定的环境前提。

**现状事实**（2026-10-31 只读复核，与指纹文档 2026-10-30 采集一致）：

1. `C:\Users\15812\.minimax\config.yaml`（本机执行者配置）**没有** `promptConfig`
   键 → `resolvePromptConfig` 取默认值：prod 构建下 `autoUpdate: true`
   （`@mavis/config/dist/config.js:1197-1207`：键缺失或非布尔 → `defaultAutoUpdate`）。
2. 更新器日志实测每小时静默检查（指纹文档 §2.7(a)：`update-10-30.log` 连续三条
   间隔一小时：`[Updater] 静默检查更新 (当前状态: not-available)`）。
3. 桌面端设置 `earlyAccessUpdateEnabled: false` 只关 early-access 灰度，**不是**
   稳定通道的自动更新开关（指纹文档 §2.7(c)）。
4. `state.json`（`%APPDATA%\MiniMax\hot-update\state.json`，schemaVersion 2）
   **没有** autoUpdate 键；其 `lastCheckTime` / `lastUpdateTime` 是更新器活动的
   可观测痕迹（002 复采：`enabled: true, channel: "prod", lastUpdateTime: 0`）。

---

## 1. 关闭步骤（执行卡启动时执行）

1. **退出 MiniMax Code 桌面端**（确认进程结束；更新器随宿主进程运行）。
2. **编辑** `C:\Users\15812\.minimax\config.yaml`，**新增**顶层键（现文件无此键，
   追加在文件末尾即可；YAML 两层缩进形态）：

   ```yaml
   promptConfig:
     autoUpdate: false
   ```

   - 依据：`resolvePromptConfig(obj)` 对 `obj.autoUpdate` 为布尔时**原样采纳**
     （显式布尔优先于默认值，`config.js:1197-1207` 实测代码面）；
   - 键位路径（顶层 `promptConfig`）来自 002 verdict C3 与指纹文档 §2.7(b) 的
     同一口径；**该键在真实运行时中的最终生效位置以执行卡启动时实测为准**
     （见 §2 V1–V3 三道验证，任何一道 FAIL 即视为未生效，不得以「已写入」替代）。
3. **重启应用**，记录重启完成时刻（本地时间，V2 的观察窗起点）。
4. **运行 §2 验证**；全过 → 冻结成立，登记进执行卡记录；任一 FAIL → §4 回退。

> 与 A 臂共用环境的边界：本改动是**两臂共用的环境固定**（C3 属执行者环境面，不是
> 两臂差异变量），A/B 两轮都必须在冻结成立的环境下进行；与 §13.2 第 4 点的
> 「权限门控单变量」不冲突——门控变量指工具权限规则，本规程固定的是更新器行为。

---

## 2. 关闭后验证（命令 + 退出码）

三道验证互补：V1 配置回读（写入面）、V2 更新器日志（行为面）、V3 state.json
时间戳（状态面）。**V2/V3 需重启后运行满 1 小时以上才有判别力**（更新器每小时
静默检查；不足 1 小时的「无记录」不是证据）。

**V1 配置回读**——`autoUpdate: false` 显式在场：

```powershell
$raw = Get-Content 'C:\Users\15812\.minimax\config.yaml' -Raw
if ($raw -match '(?m)^\s*autoUpdate\s*:\s*false\s*(#.*)?$') {
  'V1 PASS: promptConfig.autoUpdate=false present in config.yaml'; exit 0
} else {
  'V1 FAIL: explicit autoUpdate=false not found'; exit 1
}
```

- 退出码 `0` = 通过（显式布尔在场）；`1` = 未通过（键缺失/取值非 false）。

**V2 更新器日志静默检查停止**——重启时刻之后不再出现 `静默检查更新` 记录：

```powershell
$cut = Get-Date 'YYYY-MM-DD HH:MM:SS'   # = 步骤 3 记录的重启完成时刻（本地时间）
$hits = Select-String -Path "$env:APPDATA\MiniMax\logs\update-*.log" `
          -Pattern '静默检查更新' | Where-Object {
            [datetime]::ParseExact($_.Line.Substring(1, 23),
              'yyyy-MM-dd HH:mm:ss.fff', $null) -gt $cut }
if ($hits) { $hits; 'V2 FAIL: silent update checks continue after restart'; exit 1 }
else { 'V2 PASS: no silent update check after restart'; exit 0 }
```

- 日志行形（指纹文档 §2.7(a) 原样）：`[2026-10-30 00:06:41.186] [info] [Updater]
  静默检查更新 (当前状态: not-available)`；`Substring(1,23)` 取时间戳
  `yyyy-MM-dd HH:mm:ss.fff`。
- 退出码 `0` = 观察窗内零静默检查；`1` = 仍有静默检查（自动更新未被尊重）。
- 日志按日滚动（`update-MM-DD.log`），通配覆盖；观察窗跨日时两天的日志都在
  通配范围内。

**V3 state.json 时间戳停止增长**——`lastCheckTime` 为代理读数：

```powershell
$s1 = (Get-Content "$env:APPDATA\MiniMax\hot-update\state.json" -Raw | ConvertFrom-Json).lastCheckTime
# ……距 s1 采样至少 75 分钟后……
$s2 = (Get-Content "$env:APPDATA\MiniMax\hot-update\state.json" -Raw | ConvertFrom-Json).lastCheckTime
if ($s2 -eq $s1) { "V3 PASS: lastCheckTime frozen at $s2"; exit 0 }
else { "V3 FAIL: lastCheckTime advanced $s1 -> $s2"; exit 1 }
```

- 退出码 `0` = 两次采样（间隔 ≥75 分钟，略长于 1 小时检查周期）值相同，更新器
  未再检查；`1` = 值增长，更新器仍在活动。
- **诚实声明**：`state.json` 没有 autoUpdate 键（§0 事实 4），「`lastCheckTime`
  停止增长」是关闭生效的**代理读数**，与 V2 日志证据互补；此为可复核的实测口径，
  不宣称「state.json 键值直接反映开关」。

**判定规则**：V1 + V2 + V3 **全部 exit 0** 才记「冻结成立」；V2/V3 在重启后不足
1 小时内跑出的结果**不得**作为通过证据。

---

## 3. 与轮次纪律的衔接

1. 本规程属**轮次前操作项**：第四轮执行卡 Acceptance 引用本文件并核验
   V1–V3 三道退出码；002 verdict C3 的「轮次开始与结束各采集 F2/F3/F4/F5 并
   比对」在本冻结成立的前提下执行（指纹文档 §4 P3）。
2. 轮次结束后是否恢复自动更新，由执行卡/sir 决定；恢复动作不在本规程内。
3. 本规程不触碰仓库文件，不产生 run 数据；`config.yaml` 是执行者本机配置，
   不入仓、不登记 artifacts。

---

## 4. 回退与升级面

- V2/V3 任一 FAIL（显式 `false` 未被更新器尊重）：登记为执行卡**阻塞项**，按
  002 卡先例如实记「自动更新仍开启」，不得开跑；备选升级路径（版本降级固定、
  网络隔离、通道切换）属执行卡/sir 裁量，本规程不代裁。
- `config.js` 的 `resolvePromptConfig` 是 2026-10-30 采集的 3.1.7 代码面；若
  执行卡启动时版本已变（V0 指纹复核发现 F2/F3 变动），须按
  `docs/executor-fingerprint-minimax.md` §2 重新采集该实现的对应行为后再操作。

---

## 5. 边界声明

- 本文件是**操作规程**，不是「已关闭」的记录；2026-10-31 本机自动更新仍处于
  **开启**状态（002 D1 实测结论顺延），任何报告不得在 V1–V3 通过前写成「已关闭」。
- 本文件不构成对第四轮效果的前瞻判断（EVO-20261024-001 术语纪律）；它固定的是
  执行者环境，与测评结论无涉。
