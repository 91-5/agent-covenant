# 递评单 · XJ-20261114-001（lint 层受保护资产元组同步 5→6，消 fail-open）

> 递评人：OpenCode（Jarvis，出卡者兼实现者）· 2026-11-14
> 评审员：**浮香（AgnesCode）**（唯一常设独立评审员；本次评审模型 `agnes/agnes-3.0-flash`）
> 仓库：`D:\15812\projects\agent-covenant` · 分支 `feature/xj-20261114-001-lint-protected-asset` · 基线 master `7d38b9e` · 实现提交 `ab4c90f`
> 状态：**IN_REVIEW**（实现与亲跑验收完成；**执行者不宣布验收通过，裁定权在浮香**）
> 执行者无评审权、无合并权：不 push master / 不 merge / 不写 verdict / 不自评审 / 红区零触碰

---

## 1. 一句话结论

**这是「规则层已 GATED、强制层没跟上」造成的 fail-open 修补，只同步执行层，不改任何规则文本。** AGENTS.md v0.9（EVO-20261114-002，AgnesCode round-2 PASS 0B/0C/4A，ts 2026-11-14T07:06:10Z）把 §5.3 受保护资产由 5 项扩为 6 项，新增第 6 项 `scripts/verdict_gate.ps1` 判定逻辑；但 `tools/lint_cards.py` 的 `PROTECTED` 元组仍是 5 项，于是**一张只声明第 6 项的 EVO 卡会走 `if not hit: continue` 分支，一条 finding 都不产出**——新受保护资产在 linter 眼里是不设防的。本卡把元组补齐为 6 项（+1 行常量 + 注释），加 2 条用例钉住「必须 ERROR / 补声明后降级 WARN」，docs 同步六项口径与本缺口的成因记录。改动面：`tools/lint_cards.py` 5/1、`tests/test_lint_cards.py` 26/0、`docs/lint-rules.md` 16/2、两个 README 各 1/1（测试数锚点，机械同步）、卡面 1 份。

## 2. 缺口证据（改动前的实况，不是推演）

判定路径 `tools/lint_cards.py:821-850`：

```
targeted = card["protected_assets_targeted"]
unknown  = [t for t in targeted if t not in PROTECTED]   # -> EVO_PROTECTED_ASSET_UNKNOWN (WARN)
hit      = [t for t in targeted if t in PROTECTED]
if not hit: continue                                      # 元组缺第 6 项 → 走这里
if changes and approval: EVO_PROTECTED_ASSET_TOUCHED (WARN)
else:                   EVO_PROTECTED_ASSET_TOUCHED (ERROR)
```

改动前实测（临时 EVO 卡只声明 `scripts/verdict_gate.ps1 判定逻辑`、无 `protected_assets_changes`/`sir_approval`）：**不产出 `EVO_PROTECTED_ASSET_TOUCHED`**，只有 `EVO_PROTECTED_ASSET_UNKNOWN`（WARN，文案是「不在受保护清单里，请检查拼写」）。
改动后同一张卡：`EVO_PROTECTED_ASSET_TOUCHED` / **ERROR**，lint 退出码 **1**。

## 3. 交付清单

| 文件 | numstat | 内容 |
|---|---|---|
| `tools/lint_cards.py` | 5/1 | `PROTECTED` 元组新增 `"scripts/verdict_gate.ps1 判定逻辑"`；元组上方注释由「The five assets sir approved (EVO-20261010-003)」改为六项口径并引 EVO-20261114-002（AGENTS.md v0.9 §5.3）；**既有 5 项字符串与匹配语义一字未动**，未引入归一化/模糊匹配 |
| `tests/test_lint_cards.py` | 26/0 | 新增 `test_sixth_asset_without_declaration_is_an_error`（必须 ERROR 且不再报 UNKNOWN）、`test_sixth_asset_with_changes_and_approval_downgrades_to_warn`（补声明降级 WARN） |
| `docs/lint-rules.md` | 16/2 | 「EVO protected assets」小节 Five→Six，补第 6 项与「声明串去反引号」口径，并记录本次 fail-open 成因与修法 |
| `README.md` / `README.zh-CN.md` | 1/1 each | 仅测试数锚点 546 → 548（`tools/sync_test_count.py` 机械同步；不改这两行则仓库 `STALE_TEST_COUNT` 报 ERROR，CI 会红） |
| `.tasks/XJ-20261114-001.md` | 新增 | 卡面（四要素写满 + Review questions + Owned files + Acceptance） |

## 4. 亲跑台账（执行者亲跑；真实退出码与日志在 `out/xj-20261114-001-*.log`）

| # | 验收 | 退出码 | 关键读数 |
|---|---|---|---|
| V1 | `python -m unittest tests.test_lint_cards -v` | **0** | 新增 2 条用例全绿；套件 546 → 548 |
| V2 | `python tools/lint_cards.py --dir .tasks --verdict-dir verdicts --evo-dir D:\15812\projects\_handoffs\evo --json` | **0** | 对既有 EVO 卡**零新增 ERROR**；findings 与改动前基线同构（基线 `out/xj-20261114-001-baseline-lint.log`：4 条全 WARN） |
| V3 | 负向用例（临时卡只声明第 6 项，缺 changes+approval） | **1** | 产出 `EVO_PROTECTED_ASSET_TOUCHED` / **ERROR**（改动前：不产出该 code） |
| V4 | `python -m unittest discover -s tests` | **0** | 548/548 |
| V5 | 红区零 diff（`git status --porcelain`） | — | 仅 6 个 owned path；不含 `scripts/verdict_gate.ps1` / `tools/gate.py` / `AGENTS.md` / `verdicts/` / `ledger/` |
| V6 | `git diff --numstat` | — | `tools/lint_cards.py` 5/1（元组 1 行 + 注释 4 行；删 1 行 = 旧注释 2 行）；`tests` 26/0 纯新增；`docs` 16/2；README 各 1/1 |
| V7 | 负向阻断退出码非 0 | **1** | 同 V3 |

**中途两次实测发现（均已处置，登记在案）**：

1. 首轮 post-lint 报 2 条 `STALE_TEST_COUNT` **ERROR**（新增用例使套件数与 README 锚点失配）→ 跑 `tools/sync_test_count.py` 同步锚点（546 → 548）→ ERROR 清零。
2. 首轮 post-lint 对**本卡**报 `CLOSED_NOT_ARCHIVED` WARN——原因是卡面 Status 段写了终态字面量，而 `lint_cards.py:382-388` 的 `check_task_card` 按 Status 段内是否出现终态词判定 → **改写卡面 Status 段规避**（不动 linter 逻辑；该判定逻辑本身不在本卡范围）。
3. 遗留瞬态（未消解、需本卡 verdict 覆盖后自解）：`UNMAPPED_CLAIM_SURFACE` WARN ×2（README.md / README.zh-CN.md 的 mtime 因锚点更新晚于既有 PASS verdict）。

## 5. 执行者立场（不裁定，交浮香）

- **Q1（规范短名由谁定）**：本卡单方面把第 6 项的声明串定为 `scripts/verdict_gate.ps1 判定逻辑`（沿用第 5 项「AGENTS.md 写 `` `gate.py` 判定逻辑 ``、linter 写 `gate.py 判定逻辑`」的去反引号口径，保留 `scripts/` 前缀）。**AGENTS.md §5.3 正文并无所同名**，规则文本与 linter 不同源；正解是在 §5.3 补一句规范声明串，但那是再次触碰受保护资产清单本身 → 须另开 EVO 卡。本卡不擅自改 AGENTS.md。
- **Q2（为何判 XJ 而非 EVO）**：AGENTS.md v0.9 已 GATED，本卡不改规则文本、只同步「强制层对已 GATED 规则的执行」，判为 XJ 任务卡；若浮香认为「受保护资产的执行口径」本身属规则，应改走 EVO 重开。
- **Q3（为何不做归一化匹配）**：若改成「去反引号/空白后比较」，`` `gate.py` 判定逻辑 `` 与 `gate.py 判定逻辑` 将等价，命中面扩大 → 既有卡可能被新命中（把今天的 typo WARN 变成 ERROR），且 misspell 保护（`EVO_PROTECTED_ASSET_UNKNOWN`）语义会被削弱。本卡坚持精确匹配 + UNKNOWN 仍 WARN。
- **Q4（是否已有别的层兜住）**：据执行者查证，`tools/gate.py`、CI workflow、pre-push hook 均**不检查** EVO 卡声明的第 6 项资产；判定只在 `lint_cards.py:check_evo_protected_assets`。故本卡必要性为「补齐一致性 + 关闭 fail-open」，非纯洁癖。
- **Q5（卡面自曝）**：本卡**未**在 AGENTS.md §5.3 声明 `protected_assets_targeted`——本卡不修改受保护资产本身，只修改「声明哪些资产受保护」的检测器；且 `lint_cards.py` 本身被 `tools/lint_cards.py:779-780` 自述为「高风险文件不进白名单」，按 AGENTS.md §4.2 第 7 条须 **sir 手动合并**。若浮香认为本卡应自声明受保护资产（第 5 项 `gate.py` 判定逻辑同构，但本卡未改 gate.py），请裁定。

## 6. 反问评审（请找错，不要「看着挺好」）

1. 上面 Review questions 的五个问题，浮香自己的答案是什么？特别是 Q1（不同源）与 Q2（卡片类型）。
2. 什么输入能让本实现出错而现有测试覆盖不到？（例如 `protected_assets_targeted` 写成字符串而非数组、第 6 项名带全角括号、卡里同时声明第 5 与第 6 项、`.strip()` 大小写差异等）
3. 若 3am 失败，operator 会看到什么？本卡把「静默放行」换成「ERROR 阻断」，方向上更安全，但会不会在某天因为第 6 项名字被卡作者写错（全角/简繁/空格）而把正常卡拦死？该不该给个可配的别名表？
4. 本卡是否应该顺带把 `docs/lint-rules.md` 里那句「Five assets are protected」之外的历史表述（如 README、PROTOCOL.md、postmortems.md）也一并核对？
5. 合并姿态：本卡属高风险文件改动 → 按 §4.2 第 7 条须 sir 手动合并；合并前须过 `scripts/verdict_gate.ps1 -CardId XJ-20261114-001`（exit 0）。浮香是否需要在 verdict 里额外写明「本卡允许进入 master」？

## 7. 评审落点（请按此写）

- 评审正本：`D:\15812\mo brain\review\agnes\XJ-20261114-001.review.md`
- 机读 verdict：`D:\15812\projects\agent-covenant\verdicts\XJ-20261114-001.verdict.json`（字段语义见 `PROTOCOL.md` §4.5，形状见 `templates/verdict.json`：必含 `id` / `artifact` / `verdict` / `blockers` / `conditions` / `independent` / `verifier` / `ts` / `evidence`；`CONDITIONAL` 必须给非空 `conditions` + `acknowledged_by`）
- **不得**修改作者文件（`tools/lint_cards.py`、`tests/test_lint_cards.py`、`docs/lint-rules.md`、`README.md`、`README.zh-CN.md`、`.tasks/XJ-20261114-001.md`）；**不得** commit / merge / push
- 写盘注意：用 Python `encoding='utf-8'` 或 write 工具，**禁止 BOM**，写完必须回读检查无 `???` 连续乱码（坑 12：中文经 GBK 损毁）
- 独立复跑要求：V1–V4 请自行复跑，**不采信本单数字**；差异如实写入 verdict
