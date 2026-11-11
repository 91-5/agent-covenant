# Gate 0 · 主轨判定可复现性盲态双跑（轮十 D1）

> 卡 `XJ-20261111-001` · 冻结依据 `docs/eval-prereg.md` §17 D17-C · 执行者代号 `WB` · 2026-11-11
> 本节是**信度复测记录**，不是门结论；门结论见 `docs/eval-report-v10.md`（且须在 Gate 0 未挂起时才允许讨论）。

## 0 · 结论首段（先说局限，再报数字）

**`R_main = 1.0`（240/240），未触发 `R_main < 0.90` 挂起条款。**

**但这个 1.0 是确定性重放的同义反复，不是主轨语义信度的证据。** `tools/eval/judge.py` 模块 docstring 明写其确定性契约：same input text + same filesystem state + same command outputs ⇒ same levels / flags / detail；判级链路无 LLM、无网络、无随机源。两次独立会话只要输入与环境一致，逐条全等是**构造使然**。council 提出的关切——「主轨判定稳定可复现从未被验证，M1 效应仅 5.8%［1.7, 11.2］、未达最小效应」——**没有被本轮双跑证伪，也没有被证实**：本轮只证明「同一确定性实现在相同输入上可重放」。

因此本报告**不得**被引用为「主轨信度已达标」；Gate 0 的作用是按冻结公式给出门值推导输入 `R_main`，并把确定性局限一并交给浮香裁定。若评审认为 Gate 0 必须测出语义信度（例如跨判级实现 / 跨人工判级者），则本轮挂起、转主轨稳定化是合法结论，执行者不预先裁定。

## 1 · 输入集（冻结，先于双跑）

| 项 | 值 |
|---|---|
| 生成脚本 | `round10-custody/gate0_claims.py`（仓外，不入 repo） |
| 落点 | `out/gate0-claims.json` + custody 副本；`out/gate0-claims-sha256.txt` |
| 输入集 SHA-256 | `54379b38a0b1f0d88c6d8f4e47aa5ee16d16fdfe27f75765ea4ec2797583f6cd` |
| 来源 | 仓库冻结的 `tools/eval/tasks/T*.json` 30 个任务定义 + `goldset/gold_claims.jsonl` 的 30 条既有 `main` 文本 |
| 规模 | 30 个产品 × 8 条 claim = **240 条**（`extract.extract_claims()` 机械核对每产品 8/8 对齐） |
| 分层 | `cmd_ok` / `anchor_miss` / `repro_fail` / `incomplete` / `ref_ok` / `ref_missing` / `goldset_text` / `no_evidence` 各 30 条 |
| 独立性 | 不读取任何影子轨产物、不使用 D5 真数据、不重判轮六–轮九历史轮次（C12）；Gate 0 双跑只产生新的信度估计 |
| 时序 | §17 冻结 commit `ee7e765`（`2026-11-11T13:23:58+08:00`）与实现冻结 `ff4f949` 均早于 `out/` 首个产物 |

## 2 · 三次独立会话（不是把第一次结果复制两次）

| 会话 | 进程 PID | 启动 UTC | 独立工作区 | 盲化 seed | 输入序 | timeout | 环境微扰 |
|---|---:|---|---|---|---|---:|---|
| a | 55860 | `2026-11-11T05:34:11.372957+00:00` | `…\Temp\gate0-a-u0gj_5o2` | `gate0-a-20261111` | forward | 30 | 无 |
| b | 11588 | `2026-11-11T05:34:28.656672+00:00` | `…\Temp\gate0-b-8ewlgjp7` | `gate0-b-20261111` | reverse | 30 | 无 |
| perturbed | 15412 | `2026-11-11T05:34:46.084564+00:00` | `…\Temp\gate0-perturbed-zold3xxg` | `gate0-perturbed-20261111` | hashed | 60 | `PYTHONIOENCODING=utf-8`、`PYTHONPATH` 移除 |

- 三次会话由 `round10-custody/gate0_double_run.py` 以**独立 subprocess** 启动，各自 `tempfile.mkdtemp()` 重建工作区与 fixture，**不共享临时目录、不共享判级缓存、不读取其他会话输出**；产物分别封存后才比对。
- 父进程机械核验：`distinct_pid / distinct_started_utc / distinct_workspace / distinct_seed / distinct_order / same_claim_set / same_judge` **全部 True**（`INDEPENDENCE_ALL_PASS True`）；三份 `env_fingerprint` 落在各自会话 JSON。
- `judge.py` 的 SHA-256 三次相同、输入集 SHA-256 三次相同 —— 排除「换判级器 / 换 claim 集」造成的伪一致。
- **必须披露的无效维度**：盲化 seed 只经 `blind.derive_shuffle()` 影响 P-code 分配，判级按 `sorted` 遍历；输入序差异也因 `judge_claim` 之间无状态耦合而不改变结果。故 seed / 序的「独立性」是**协议完整性**，不是改变判级结果的随机化。伪双跑质疑的正面回答就是这一条，没有把它藏起来。

## 3 · 读数（真实命令与退出码）

```text
$ python round10-custody/gate0_double_run.py
  EXIT_TABLE {"a": 0, "b": 0, "perturbed": 0}   CLAIM_COUNTS a/b/perturbed = 240/240/240
  INDEPENDENCE_ALL_PASS True                    (GATE0_DOUBLE_EXIT=0)

$ python tools/eval/gate_metrics.py --gate0 --main out/gate0-main-a.json \
      --main-rerun out/gate0-main-b.json --out out/gate0-reliability.json
  wrote out/gate0-reliability.json (gate0)     V2_GATE0_EXIT=0
$ python -X utf8 -c "... print('R_main:', d.get('r_main'))"      V2_READ_EXIT=0
  R_main: 1.0 | gate0_suspend: False | r_main_flags: 1.0 | r_main_detail: 1.0

$ python tools/eval/gate_metrics.py --gate0 --main ... --main-rerun ... \
      --perturbed out/gate0-main-perturbed.json --out out/gate0-reliability-full.json
  GATE0_FULL_EXIT=0
  perturbation r_main_perturbed = 1.0 (240/240), below_floor = False
```

| 口径 | 读数 | 说明 |
|---|---:|---|
| **主口径 `R_main`** | **1.0（240/240）** | `(claim 定位键, level)` 逐条全等率；`level` 取自 `schema.ClaimJudgement.to_dict()`，输出只带摘要不含判级记号 |
| `R_main_flags` | 1.0 | 副口径，`flags` 序列一致率 |
| `R_main_detail` | 1.0 | 副口径，判级轨迹文本一致率 |
| `R_main_perturbed` | 1.0（240/240） | 扰动稳健性副口径；未低于 0.90，但按 §17 仍不得据此宣布影子门结论已通过 |
| 分层 | 8/8 层各 30/30 全等 | `by_layer` 见 `out/gate0-reliability.json` |
| 挂起条款 | **未触发** | `gate0_suspend = False`；`R_main ≥ 0.90` |

判级结果字段澄清（防臆造）：主轨 `ClaimJudgement` 只有 `level / flags / detail / observation / claim`；**没有** `reason`（属人工归因台账 `docs/d00-mismatch-ledger.json`）、**没有** `claim_id`（属影子 record）、**没有** `cwd`（属执行环境）。本轮判级向量未纳入任何不存在的字段。

## 4 · 不洗白清单

1. **合成输入集**：Gate 0 claim 集由冻结模板从任务定义与金标准文本派生，不是真实项目产出的产品草稿。它测的是「判级器在受控分层输入上的重放一致性」，不覆盖真实草稿的语言多样性。
2. **确定性同义反复**：见 §0。`R_main = 1.0` 不证明语义信度，不证明跨判级实现一致，不回答 council 关于 M1 效应弱的关切。
3. **扰动强度有限**：第三轮只做了工作区路径 / 启动时间 / 编码环境变量 / timeout 微扰，未做 filesystem state 实质变化（那会改变输入而非环境）。`R_main_perturbed = 1.0` 只说明本组微扰下稳定。
4. **副口径不进门值**：门值 `M_C` 只由主口径 `R_main` 推导；副口径低于 0.90 时的处置已在 §17 D17-C 第 5 条冻结，本轮未发生。
5. **非人类标注**：本轮无人工判级者；双跑是两次机器会话，「独立」指会话隔离，不指独立判级主体。

## 5 · 交浮香裁定

1. `R_main = 1.0` 作为门值推导输入是否可接受，还是因「确定性重放不构成信度证据」应判定 Gate 0 未真正完成、整轮挂起转主轨稳定化？
2. 若接受，报告 v10 是否必须在门结论旁并列本节 §0 的局限声明（执行者已按此写）？
3. 后续轮次若要测语义信度，是否须另开卡引入独立判级实现 / 人工判级者（涉 C12 与红区边界）？

## 6 · 证据文件

| 文件 | 说明 |
|---|---|
| `out/gate0-claims.json` / `out/gate0-claims-sha256.txt` | 冻结输入集与哈希 |
| `out/gate0-main-a.json` / `out/gate0-main-b.json` / `out/gate0-main-perturbed.json` | 三次独立会话原始输出（含各自环境指纹） |
| `out/gate0-reliability.json` / `out/gate0-reliability-full.json` | Gate 0 主口径 / 含扰动副口径读数 |
| `out/gate0-double-run.log` | 三次会话命令、退出码、独立性机械核验输出 |
| `round10-custody/gate0_claims.py` / `gate0_session.py` / `gate0_double_run.py` | 生成 / 会话 / 父进程脚本（仓外） |
| `round10-custody/gate0-*.json` / `gate0-double-run-console.log` | custody 副本 |

> 本报告不写 verdict、不宣布门结论；`R_main` 的唯一用途是 D2 门值盲态冻结的输入。
