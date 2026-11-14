# 递评单 · EVO-20261114-003（受保护资产规范声明串 + 元组镜像义务，AGENTS.md v0.9 → v0.10）

> 递评人：OpenCode（Jarvis，出卡者兼实施者）· 2026-11-14
> 评审员：**浮香（AgnesCode）**（唯一常设独立评审员；本次评审模型 `agnes/agnes-3.0-flash`）
> 卡面：`D:\15812\projects\_handoffs\evo\EVO-20261114-003.json`（status = CANDIDATE）
> 补丁包：`D:\15812\projects\_handoffs\evo\materials\EVO-20261114-003.apply.py`（默认 DRY-RUN）
> 目标文件：`C:\Users\15812\.config\opencode\AGENTS.md`（当前 v0.9，sha256 `D4F945502237EF1C1D8BC5D6730C8B3DE15FD1E5051E9F02B893AF52CE5F9532`）
> 状态：**IN_REVIEW**（卡面与补丁包就绪；**执行者不宣布验收通过，裁定权在浮香**）
> 执行者无评审权、无合并权：不改 AGENTS.md（未 --apply）、不写 verdict、不 commit/merge/push

---

## 1. 一句话结论

**本卡是条文澄清，不是清单扩展。** 承接 XJ-20261114-001 评审 advisory A1：AGENTS.md §5.3 的六项受保护资产用带反引号、带括号说明、带 §引用的自然写法书写，而 `lint_cards.py` 的 `PROTECTED` 元组用的是无反引号、无括号的短串——**六项里有四项按条文原文抄写就不命中**。本卡在 §5.3 追加一段：六项**规范声明串**（逐字复制，不带反引号/括号说明/§引用）+「只有规范串构成声明」+ 非规范写法按拼写错误处理（WARN，`--strict` 下等同阻断）+ 评审员人工核对兜底 + **规范串与 `PROTECTED` 元组必须逐字相同、任一方改动必须同卡同步**（把 XJ-20261114-001 的 fail-open 教训写进条文）。**不扩清单、不改 lint_cards.py、不改任何判定逻辑与级别。**

## 2. 缺口证据（实测，非推演）

| 项 | 实测 |
|---|---|
| 条文 vs 元组 | §5.3 清单写「EVO 状态机定义（§5.4）」「sir 终裁权（§5.6）」「`gate.py` 判定逻辑」「`scripts/verdict_gate.ps1` 判定逻辑（…）」；元组写「EVO 状态机定义」「sir 终裁权」「gate.py 判定逻辑」「scripts/verdict_gate.ps1 判定逻辑」→ **6 项中 4 项按原文抄写不命中** |
| 非规范写法的行为 | 构造两张负向卡：声明「EVO 状态机定义（§5.4）」与「`scripts/verdict_gate.ps1` 判定逻辑」→ `EVO_PROTECTED_ASSET_UNKNOWN`（WARN，'check for a typo'），`--strict` → `LINT: FAIL (0 errors, 2 warnings)`、**exit 1**。即：**CI / pre-push（跑 --strict）会阻断，非 strict 的本地运行不阻断**；错误语义是「拼写错误」而非「触碰受保护资产」，具误导性 |
| 前情 | XJ-20261114-001 修的是更严重的一档：元组缺第 6 项 → 只声明第 6 项的卡走 `if not hit: continue` → **零 finding**。已由 master `2c473b4` 关闭（评审员独立复跑 R4 证实） |

## 3. 交付清单

| 文件 | 内容 |
|---|---|
| `_handoffs/evo/EVO-20261114-003.json` | 卡面（28 字段：触发/证据/现状/提案/置信度/风险/验证方案/回滚/supersedes/conflicts_with/TTL/负责人/状态 + `protected_assets_targeted`/`protected_assets_changes`/`sir_approval`/owned_files/acceptance/open_followups/patch_package） |
| `_handoffs/evo/materials/EVO-20261114-003.apply.py` | 两处锚定补丁（A：在 §5.3 第 6 项后插入规范声明串段；B：附录版本行 v0.9 → v0.10），默认 DRY-RUN，`--apply` 才写盘 |
| `_handoffs/evo/index.json` | 追加索引条目（status CANDIDATE，review_status PENDING） |

**补丁包自检（执行者亲跑，dry-run，文件未动）**：
```
changed=True  crlf_preserved=True  has_all_canon_strings=True  has_canonical_para=True
has_v010=True  no_v09_header=True  roundtrip_exact=True  six_refs_unchanged=True
line-endings: CRLF 101->102, lone-LF 148->148
DRYRUN_EXIT=0      target sha256 未变：D4F94550…（27325 B）
```
`roundtrip_exact=True` 是强自检：**移除插入段 + 还原版本行后与原文逐字节一致** → 证明除两处外零改动。行尾预期值由锚点推导（插入行复制锚点行终止符），未写死。

## 4. 请浮香裁定的问题

1. **规范串条款的位置与措辞**：放在 §5.3 清单第 6 项之后（现状）是否合适？是否应改为清单前的「前置定义」？措辞里「非规范写法按拼写错误处理」是否会被读成「拼错即可绕过」？本卡已用「只有规范声明串构成声明」+「--strict 下等同阻断」+「评审员必须核对」三重兜底，是否足够？
2. **镜像义务的硬度**：条文写「规范声明串与 `PROTECTED` 元组必须逐字相同，任一方改动必须同卡同步」——这等于给 lint 元组的每次改动都加一个 AGENTS.md 同步义务。是否过重？是否应改成「元组变更须在同一评审中提交条文同步的证据」？
3. **是否该现在就动 linter**：非规范写法在非 strict 本地运行下不阻断（本卡不修）。是否同意维持「另立卡 + 独立 verdict + sir 批准」的处置？若你认为必须在同卡一并修，请指出——那会触碰第 5/6 项受保护资产本身。
4. **卡片类型**：本卡判为 EVO 卡（改全局规则文本）。它是否更像任务卡（XJ）？若你判为 XJ，规则文本的修改路径会不同，请裁定。
5. **`protected_assets_targeted` 的申报口径**：本卡按 EVO-20261114-002 的先例声明「gate.py 判定逻辑」（清单条文与检测器同构，故以清单项作为触碰点），并用 `protected_assets_changes` 说明「只追加口径段、不改资产语义」。这个申报方式是否可接受？另：本卡在 §5.3 里点名了第 5/6 项资产本身（规范串列举），是否构成「引用」而非「触碰」（按 §5.3 原理：检测按声明而非关键词）？
6. **残留缺口的白话**：本卡把「拼写偏差在非 strict 本地运行不阻断」写进了条文（作为诚实披露）。这是否属于把实现缺陷写进规则文本？另一条路是先修实现、再写条文。请裁定哪条更符合纪律。

## 5. 反问（请找错，不要「看着挺好」）

1. 什么输入能让本卡实现出错而现有自检覆盖不到？（例如：AGENTS.md 里第 2/4 项将来被改成别的写法、`PROTECTED` 元组新增第 7 项而本卡的 CANON_STRINGS 未同步、插入段落被评审员认为过长应拆成两条、`--strict` 语义日后变化）
2. `roundtrip_exact` 自检是否真的证明了「除两处外零改动」？请自己独立复算一遍（不要采信本单数字）。
3. 本卡把「规范声明串」写死为**当前**六项。若日后受保护清单增减，条文会不会立刻过期？该不该写成「以 `lint_cards.py` 的 `PROTECTED` 元组为准，条文列举仅为示例」——那又回到不同源。
4. 补丁若被重复执行（`--apply` 跑两次）会怎样？请实跑一次 `--apply` 后再 `--apply`，看是否幂等、是否会二次插入（**注意：请勿在作者文件上做破坏性测试**；如需测试请复制 AGENTS.md 到临时目录并改脚本 TARGET 常量，或只做 dry-run 推演并说明理由）。
5. 合并/应用姿态：AGENTS.md 属高风险全局规则 → §4.2 第 7 条要求 sir 手动应用；本卡 `--apply` 由 sir 明确指令触发。是否需要在 verdict 中额外写明「允许应用」字样？

## 6. 评审落点（请按此写）

- 评审正本：`D:\15812\mo brain\review\evo\EVO-20261114-003.review.md`
- 机读 verdict：`D:\15812\projects\_handoffs\evo\EVO-20261114-003.verdict.json`
  （**放在 `_handoffs/evo`，不要放进 agent-covenant 仓的 `verdicts/`**：仓内 EVO verdict 会被 lint 的 orphan 检查盯上，push 时 `--strict` 可能因新 orphan 而阻断；`scripts/verdict_gate.ps1` 的搜索根**包含** `D:\15812\projects\_handoffs\evo`，故门禁照样能取到本卡 verdict。）
  字段语义见 `PROTOCOL.md` §4.5，形状见 `templates/verdict.json`：必含 `id`（"EVO-20261114-003"）、`artifact`、`verdict`、`blockers`、`conditions`、`independent`、`verifier`、`ts`（**真实当前 UTC**，不得超前/编造）、`evidence`；CONDITIONAL 必须给非空 `conditions` + `acknowledged_by`；REJECT 必须 blockers 非空并写清文件与行。
- **不得**修改任何作者文件（AGENTS.md、apply.py、卡 JSON、index.json）；**不得** `--apply`、commit、merge、push。
- 写盘要求：UTF-8 **无 BOM**；写完回读，确认无 `???` 连续乱码（中文经 GBK 损毁的坑），JSON 可解析。

## 7. 独立复跑要求（不得采信本单数字）

- `python -X utf8 D:\15812\projects\_handoffs\evo\materials\EVO-20261114-003.apply.py`（**dry-run**，确认 exit 0 与 8/8 自检、目标文件 sha256 未变）
- 自行复算 `roundtrip_exact`：按 apply.py 的两步锚定做「移除插入段 + 还原版本行」，与原文逐字节比对
- `python tools/lint_cards.py --dir .tasks --verdict-dir verdicts --artifact-map artifacts.json --evo-dir ../_handoffs/evo --strict`（在 `D:\15812\projects\agent-covenant` 下）→ 确认仍只有既有的 2 条 `EVO_PROTECTED_ASSET_TOUCHED`、零新增 ERROR、WARN 数不增
- 独立核对 §5.3 清单原文与 `tools/lint_cards.py` 的 `PROTECTED` 元组是否确如本单所述「六项中四项不同源」
