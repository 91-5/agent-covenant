# Agent Covenant（协作验证协议）

> **交付物在独立评审产出机器可校验的 verdict 并通过门禁之前，一律不算「完成」。**

两个文件，零依赖：

```bash
python tools/gate.py --verdict-dir verdicts     # 门禁
python tools/lint_cards.py --dir .tasks         # 卡片 schema 与命名检查
```

---

## 为什么需要它

**agent 自己说「做完了」不是证据。** 那个"证据"是一段对话记录，而对话记录不可校验。

这不是猜测，是有出处的：

- **MAST** 多智能体失败分类（[arXiv 2503.13657](https://arxiv.org/abs/2503.13657)，NeurIPS 2025）里，**FC3 就是任务验证失败**——具体是 *FM-3.2：无复核，或复核不完整*。
- **ICML 2026** 多智能体系统立场论文：主流 benchmark **失败率 41–87%**，其中 **37.2%** 因缺少协调屏障而提前提交。

写出来的失败案例都是"有声"的。真正贵的是安静的：

- 某编码 agent 建隔离 worktree，迁移失败后日志写 `Failed to migrate some changes... Continuing with worktree creation`，随后**销毁了数日未提交的工作**（[vscode #289973](https://github.com/microsoft/vscode/issues/289973)，data loss）。
- **Lost update 对测试和 `git diff` 都不可见**——文件看起来是好的，唯一症状是"agent 声称做过的事不在了"。

这个项目就是处理最无聊的那部分：把评审结论变成文件、把文件变成可校验、把「没有 verdict」等同于「没完成」。

## 是什么 / 不是什么

| 这是 | 这**不是** |
|---|---|
| 任务卡 / 评审卡 / 交接 / 决策记录的**文件 schema 规约** | 编排器。我们不调度 agent |
| 针对评审 verdict 的**可进 CI 的门禁** | swarm 库（ruflo 73k★、oh-my-opencode 70k★、crewAI 59k★、langgraph 41k★，编排层已是红海） |
| 逐条对应规则的**失败模式目录** | 模型路由、记忆库、向量库 |
| **harness 无关**——适配器是文档，不是插件 | 绑定某一家厂商的插件 API |

**为什么这块是空的**：质量控制层并不拥挤。我们能找到的同类项目——`AAHP`、`agent-handoff-protocol`、`agent-acceptance-gate`——都是 **0★**，`agents-template` 5★。社区里需求喊得很响（"context loss 是多智能体协作失败第一病因"），但没人做出口碑。反观编排层，星都堆在那儿。我们是**故意挑空地**。

> **第三方数字的出处**——star 数与维护状态是**快照**，不是永久主张。全部于 **2026-09-29** 经 GitHub API 观测：
> [ruflo 73k](https://github.com/ruvnet/ruflo) ·
> [superpowers 293k](https://github.com/obra/superpowers) ·
> [oh-my-opencode 70k](https://github.com/code-yeongyu/oh-my-openagent) ·
> [crewAI 59k](https://github.com/crewAIInc/crewAI) ·
> [langgraph 41k](https://github.com/langchain-ai/langgraph) ·
> [AAHP 0](https://github.com/homeofe/AAHP) ·
> [agent-handoff-protocol 0](https://github.com/amkentech/agent-handoff-protocol) ·
> [agent-acceptance-gate 0](https://github.com/yanqr213/agent-acceptance-gate) ·
> [agents-template 5](https://github.com/pedrofuentes/agents-template)。
> 我们第一轮外部评审正是揪出了这里缺出处，修正见 `ADR-0001.md`。

**与相邻标准的边界**：MCP 是 agent↔**工具**（垂直）；A2A 是 agent↔**agent** 的传输与发现（水平）。Agent Covenant 管的是 agent↔agent 的**问责**：交付物如何被**判定**，而不是如何被传输或发现。

## 60 秒上手

```
your-project/
├─ .tasks/
│  ├─ AC-20260929-001.md              ← 任务卡（命名空间 id！）
│  └─ REVIEW-AC-20260929-001.md       ← 评审卡
├─ verdicts/
│  └─ AC-20260929-001.verdict.json    ← 机器可读 verdict
└─ artifacts.json                     ← {"AC-20260929-001": ["src/pipeline.py"]}
```

1. **作者**复制 `templates/TASK.md` → 重命名为 `AC-20260929-001.md`，验收标准写成带退出码的命令。
2. **评审者**是**另一个** agent，拿到的是**绝对路径**，被要求先读卡。它产出评审卡**和** verdict JSON，**不碰作者的文件**。
3. **门禁**：

```bash
python tools/gate.py --verdict-dir verdicts \
  --require AC-20260929-001 --artifact-map artifacts.json
```

| 退出码 | 含义 |
|---|---|
| `0` | 所有必需 id 均满足策略 |
| `1` | **门禁违规**——打印原因，或 `--json` 给机器读 |
| `2` | 用法/输入错误（目录不存在、verdict 读不了）。**不算通过** |

## 门禁到底查什么

- verdict 存在且可解析；verdict ∈ {PASS, CONDITIONAL, FAIL}
- PASS 要求 `blockers == 0`；CONDITIONAL 需要 `--allow-conditional` **且**有具名 `acknowledged_by`
- **`independent: true`**——作者不能给自己批
- `evidence` 为非空列表——verdict 必须出示它干了什么
- **新鲜度**：verdict 的 `ts` 不得早于它所评判的产物。早于代码的 verdict 是**过期**，过期即拦。（这条是团队最先省的，也最要紧）

## 采纳等级——请诚实声明

| 等级 | 要求 |
|---|---|
| **L0** 无结构 | agent 自由对话，无产物。今天的默认状态 |
| **L1** 卡片化 | 命名空间卡片、schema、独立性规则。允许人工中转 |
| **L2** 门禁化 | 机器 verdict、`gate.py` 进 CI、门禁回路里没有人 |

如果回路里还有一个人点"批准"，那你就是 **L1**。就说 L1。虚报等级正是这个项目要防的失败模式。

## 适配器

刻意做成文档而非代码——避免协议随某家 API 表面一起腐烂：

- `adapters/claude-code/SKILL.md`——评审者做成 skill；作者规则走 `AGENTS.md`
- `adapters/codex/AGENTS.md`——harness 无关的 `AGENTS.md` 规则块
- `adapters/opencode/AGENTS.snippet.md`——规则放置 + 把门禁绑成 MCP 工具

每个都把随版本变化的部分标为 **verify（需自行验证）**，不编造。

## 状态——v0.1，诚实版

规范 + 两个经测试的工具（45 个单测）+ 一次真实试点（`examples/deepfreeze-pilot/`）。**未经规模验证**。已知局限写在 `PROTOCOL.md` §10，包括我们拒绝粉饰的两条：基于文件的协议需要人（或轮询器）去唤醒第二个 agent；门禁能证明"检查跑过了"，但证明不了评审者是否认真。

## 路线图

- [x] v0.1——规范、门禁、linter、模板、适配器、一个真实案例
- [ ] 换一个 harness 再跑一次真实试点（可移植性证据）
- [ ] 验证器注册表——可共享的验收检查器，需求最强烈
- [ ] 扩充事故语料；每个已命名失败模式配一条规则
- [ ] 可选 `--junit` 输出供 CI 看板（有人提才做）

## 参与

先读 `PROTOCOL.md`，再读 `postmortems.md`——后者才是这个项目存在的理由。最欢迎的贡献是适配器和验证器。PR 要过和本项目一样的门禁，见 `CONTRIBUTING.md`。

MIT © 15812
