# Agent Covenant（协作验证协议）

> **交付物在独立评审产出机器可校验的 verdict 并通过门禁之前，一律不算「完成」。**

两个文件，零依赖（Python 3.9+）：

```bash
git clone https://github.com/91-5/agent-covenant.git
cd agent-covenant
python tools/gate.py --verdict-dir verdicts     # 门禁
python tools/lint_cards.py --dir .tasks         # 卡片 schema 与命名检查
python -m unittest discover -s tests            # 84 个单测
```

## 安装

没有东西可装。两个工具都只用标准库、没有第三方依赖，`git clone` 加一个
`PATH` 里的 `python` 就是全部步骤——这是刻意的，好让门禁能直接跑在什么都不用
放行的封闭 CI 镜像里。需要 Python 3.9 或更新版本。

## 你的第一轮

六步，大约十分钟。只打算读这份规范的话，下面都可以跳过。

**1. 复制工具。** `tools/gate.py` 和 `tools/lint_cards.py` 是独立脚本，只用标准库。
原样复制到你自己的项目即可，它们不从本仓库 import 任何东西。

**2. 选一个命名空间。** 两个或更多大写字母，按作者或团队唯一——`AC`、`MYTEAM`、
`SIR`。这个前缀会出现在每张卡的 id 里。裸的 `TASK-001.md` 会被别的 agent 冒名顶替，
所以是故意拒绝的（`NAMESPACE_MISSING`）。

**3. 写第一张任务卡。** 把 `templates/TASK.md` 复制成 `.tasks/<NS>-YYYYMMDD-001.md`，
填好 Context、Deliverables、Owned files 和 Acceptance。评审者读的就是这张卡——它要是
没写清"做完"意味着什么，评审者就只能猜，而猜测不是评审。

**4. 声明被评审的文件面。** 以 `examples/deepfreeze-pilot/artifacts.json` 为起点，把
评审要判断的每个文件都列进去。往后你修改了但**没**列进去的文件，没有任何新鲜度检查
覆盖它，`lint_cards.py` 会就这件事报警（`UNMAPPED_CLAIM_SURFACE`）。正是这个文件让
门禁的新鲜度规则真正生效——没有它，门禁分不出哪份 verdict 早于你的代码、哪份覆盖了它。

**5. 请求评审。** 下一节那段提示词就是能用的那种。只把任务卡的绝对路径给评审者，别给
别的。评审者产出 `.tasks/REVIEW-<id>.md` 和 `verdicts/<id>.verdict.json`，且不得改动
被评审的文件。完整的一次往返——包含一个判FAIL 的轮次——在
`examples/deepfreeze-pilot/` 里。

**6. 跑门禁。**

```bash
python tools/lint_cards.py --dir .tasks --verdict-dir verdicts --strict
python tools/gate.py --verdict-dir verdicts --artifact-map artifacts.json --require <NS>-YYYYMMDD-001
```

退出码 `0` 表示 verdict 满足策略。`1` 表示不满足——去读打印出来的原因，而不是重试。
`2` 是用法错误，不算通过。

然后把同样这两条命令接进 CI（下一节），让答案是被强制的，而不是靠记性。

所有产物的模板都在 `templates/`；一次完整的真实流程（含其中的 FAIL 轮次）在
`examples/deepfreeze-pilot/`。

## 在 CI 里跑

`.github/workflows/gate.yml` 跑的就是上面这三条命令，可以直接拿来改：

```yaml
name: covenant
on: [push, pull_request]
jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.9' }
      - run: python -m unittest discover -s tests
      - run: python tools/lint_cards.py --dir .tasks --verdict-dir verdicts --artifact-map artifacts.json --strict
      - run: python tools/gate.py --verdict-dir verdicts --artifact-map artifacts.json
```

非零退出就是失败，不是提醒。同时说清门禁能证明什么、不能证明什么：它能证明
检查**跑过了**、且该 verdict 满足策略；它证明不了评审者是否认真，这里任何退出码
都不该被当作"评审认真"的证据。

## 怎么发起一次评审

只给评审者绝对路径，别的一概不给。下面这段是真实用过的指令：

> 先读 `D:\path\to\project\.tasks\<NS>-YYYYMMDD-NNN.md`。它写明了你要判断的产物
> 和必须自己核对的验收标准。评审期间不要改动任何被评审文件；你只拥有评审卡和
> verdict 两样产出。评审写到 `.tasks/REVIEW-<id>.md`，机器可读孪生体写到
> `verdicts/<id>.verdict.json`。你的 `ts` 必须满足
> **被评审产物的最新 mtime ≤ ts ≤ 当前时间**——先查 mtime，再取两者之间的时刻。
> 发现有 blocker 就在 `## Blockers` 里写明并给 `FAIL`；一份你没挣来的绿灯比没有
> verdict 更糟。

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

## 状态——诚实版，且有意不写版本号

**本仓库已通过门禁。**下面每一个发布版本在 `verdicts/` 里都有一份评审 verdict，
而这条证据链的当前状态就是最新那份 verdict 文件所说的——去读它，而不是相信散文里
手打的版本号。这句话是刻意的：手工维护的版本标题连续三轮都是陈旧的（写着
"v0.1.4，评审中"，而 v0.1.5 其实已过门禁），而且每次都错在保守的方向——这正是
它能躲过评审的原因。

> 更正一下，也正是有教育意义的部分：上一版 README 在已经交出 PASS verdict 的情况
> 下写着"刻意尚未过门禁"。这句话错在**贬低自己**的方向，而这种错误通常一眼就能被
> 发现。同一份 README 还写着 45 个单测，而当时测试套件里有 69 个。两处都是散文，
> 而门禁只读 `.tasks/`。v0.1.4 补上 `STALE_TEST_COUNT` 和
> `UNMAPPED_CLAIM_SURFACE`，让**这两类形状**的缺陷由检查兜住，而不是指望一个细心
> 的读者：可复制代码块里过期的测试数，以及没有任何 verdict 覆盖的声明表面。
>
> 比第一版听起来窄，而且是有意收窄的。同一轮里还漏掉一条指向不存在文件的命令，
> CHANGELOG 声称它已被移除——实际只从它出现的三个地方中的两个里移掉了。独立评审
> 抓到了这一条（`verdicts/XJ-20260930-006.verdict.json`，FAIL，1 个 blocker）。
> 写错的命令、过期的参数、错误的路径：这些一个都不检查，本项目也不假装检查。

不吹的部分：这是**一份规范加两个经测试的工具**，跑过一次真实试点
（`examples/deepfreeze-pilot/`）和本仓库自己的历史——不是一个机队，也没有经过
规模验证。已知局限写在 `PROTOCOL.md` §10，包括我们拒绝粉饰的两条：基于文件的协议
需要人（或轮询器）去唤醒第二个 agent；门禁能证明"检查跑过了"，但证明不了评审者
是否认真。

> ### `verdicts/` 里的评审者是 AI，而 `independent: true` 是它对自己的声明
>
> 本目录下的每一份 verdict 都由同一位评审者出具——**是 AI，不是人。** 它在不同轮次
> 里的签名并不一致（早期是 `ximo@agnes`，后期是 `ximo@agnes-ai`），而本仓库没有任何
> 工具检查这个签名字段。请把这里的 verdict 读作**一个 AI 在评审另一个 AI**，由机器
> 检查了一致性与诚实性，而不是独立的人类签字。
>
> 每份 verdict 都带 `independent: true`，而这个字段是**评审者对自己的声明**，不是本仓库
> 验证过的属性。格式里没有任何东西能区分"确实没碰过这份工作的评审者"和"碰过的"；
> `PROTOCOL.md` §10.3 有更长的说明，这里写这一段，是为了让读者不必自己去翻。
>
> 门禁真正检查的只是这个字段**存在且可读**——也就是 `independent` 不是 `false`。
> 它检查不了这个词所暗示的那件事。`evidence` 同理：那是评审者自述"我跑过"的命令
> 清单，门禁从不复跑。证据是声明，不是收据。
>
> 我们认为只写在附录里的局限等于没披露，所以才写在这里，而不只是留在 §10.3。

## 路线图

- [x] v0.1——规范、门禁、linter、模板、适配器、一个真实案例
- [x] v0.1.1–v0.1.3——修掉 linter 假阳性、纠正评审者时间戳指引、由独立评审者对本
      仓库过门禁并公开
- [ ] 换一个 harness 再跑一次真实试点（可移植性证据）
- [ ] 验证器注册表——可共享的验收检查器，需求最强烈
- [ ] 扩充事故语料；每个已命名失败模式配一条规则
- [ ] 可选 `--junit` 输出供 CI 看板（有人提才做）

## 参与

先读 `PROTOCOL.md`，再读 `postmortems.md`——后者才是这个项目存在的理由。最欢迎的贡献是适配器和验证器。PR 要过和本项目一样的门禁，见 `CONTRIBUTING.md`。

MIT © 15812
