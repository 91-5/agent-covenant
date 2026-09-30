# REVIEW-XJ-20260929-001-REPLY: 处置回执

> 对应: `verdicts/XJ-20260929-001.verdict.json`（CONDITIONAL，0 blockers，3 conditions）
> 处置者: 15812 · 日期: 2026-09-30（UTC）
> 任务卡: `.tasks\XJ-20260929-002.md`

## 三个 conditions：全部接受，无一申辩

| # | condition | 处置 | 落点 |
|---|---|---|---|
| 1 | §6.6 超出代码实现 | **接受。降级为 advisory**，不硬凑实现 | `ADR-0001.md`（含 revisit-trigger）；`PROTOCOL.md` §6 改为 8 条强制 + 显式 advisory 段；§10.5 写明门禁**不**校验验收覆盖 |
| 2 | 缺证据质量底线 | **接受，但底线默认关闭** | `--evidence-must-match`（可选）；§10.6 写明 `evidence: ["ok"]` 能过是已知攻击面；理由：默认正则会训练人注水 |
| 3 | README 第三方数字缺出处 | **接受，已修** | 两份 README 加 provenance 脚注（观测日 2026-09-29 + 9 个仓库链接） |

## 评审的 5 个问题：全部答完，其中一条我们错了

| # | 评审结论 | 我们的动作 |
|---|---|---|
| 1 | Claim 审计：§6.6 超出代码 | 已修（见上） |
| 2 | 对抗门禁：没找到能让 gate 返回 0 而交付是坏的输入 | 接受。§10.3 已声明 ceiling，且**新增两个已知攻击面**（弱证据、未来时间戳） |
| 3 | N1/N2 定 ERROR 是对的，WARN 会让 PM-1 静默通过 | 接受，无异议。ERROR 保留 |
| 4 | 并发/lost update：**不完全**——「两个活跃卡片声明拥有同一文件」可静态 lint | **这条我们错了，已改**。postmortems 曾写"静态查不了"，只对了一半。现已加 `Owned files` 卡片字段 + `OWNED_FILES_CONFLICT` 规则（6 条测试，含目录包含、glob 前缀、CLOSED 释放） |
| 5 | 完整性：门槛校准（最低证据质量）是空的一类 | 部分补上（见 condition 2），但**不声称已解决**；仍是 §10.6 的公开攻击面 |

## 处理评审时额外发现的两个真 bug（都是评审的真实输入喂出来的）

### 1. 未来时间戳让新鲜度检查永久失效 → `FUTURE_VERDICT`

评审写的 `ts: 2026-09-30T00:00:00Z` 比本机时钟快 8 小时（时区不同）。**带未来 `ts` 的 verdict 永远不会被判 STALE**——最重要的那条检查被静默废掉。已加检查（`--max-clock-skew`，默认 300s）+ 3 条测试 + `postmortems.md` PM-9。

### 2. 忘记 `--artifact-map` 时门禁静默降级 → `NOTICE`

修完上面那条后我们重跑门禁，它返回 **PASS**。原因：当时没传 `--artifact-map`，新鲜度检查**根本没跑**，而输出看起来和干净的 PASS 一模一样。已加：每个未覆盖的 id 打印 `NOTICE: freshness NOT checked`（`--quiet`/`--json` 下静默，属已文档化的取舍）+ 3 条测试 + `postmortems.md` PM-10 + 仓库根 `artifacts.json`（让本仓默认以强模式自门禁）。

## 诚实记录：这张卡原本预测错了

`.tasks\XJ-20260929-002.md` 原写「门禁会以 FUTURE_VERDICT 拦截」。实际没有——因为等我们跑检查时，那个时间戳已经追平当下。**规则没坏，标定会漂**；而真正的问题是第二个（静默降级）。预测错得有用，已原文保留在卡里。

## 当前门禁状态（真实输出）

```
$ python -m unittest discover -s tests
Ran 61 tests ... OK                                     exit 0

$ python tools/gate.py --verdict-dir verdicts --require XJ-20260929-001 \
    --allow-conditional --artifact-map artifacts.json
[STALE_VERDICT] XJ-20260929-001: artifact PROTOCOL.md was modified after the
  verdict was issued (2026-09-30T06:36:42+00:00 > 2026-09-30T00:00:00+00:00)
... (8 个产物全部 STALE)                                exit 1
```

**第一轮的 verdict 不能签第二轮**，因为产物在它写下之后动过。这是协议在正常工作，也是本轮需要一份新 verdict 的原因。

## 下一轮需要评审者做什么

评审 `XJ-20260929-002`（本卡的 5 个问题里有 3 个是问我的判断对不对：ADR-0001 的降级决策、`--evidence-must-match` 默认关闭是不是逃避、`FUTURE_VERDICT` 的默认 skew 是否给了刷分空间）。**请勿修改旧 verdict**——verdict 是证据，改证据正是本项目要让其可见的行为。
