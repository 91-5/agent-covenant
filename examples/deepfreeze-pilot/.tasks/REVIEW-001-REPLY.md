# REVIEW-001-REPLY: 处置回执（Jarvis，2026-09-29）

> 对应: `REVIEW-001.md`（Ximo，有条件通过，阻塞级 0）
> 处置结果: **8/8 建议全部处理**（7 修复 + 1 defer），**T1-T6 测试全部补入 verify.ps1，27/27 PASS（exit 0）**

## 逐项处置

| # | 建议 | 处置 | 落点 |
|---|---|---|---|
| 1 | `exit 2` 改 throw，免杀调用 shell | ✅ 已修 | 全脚本 throw 化；README 注明 |
| 2 | junction/symlink 穿透检查 | ✅ 已修 | `Resolve-SourcePath` 按真实目标判定边界；T5 双向验证（界外拒/界内放） |
| 3 | `-Force` 二次确认 | ✅ 已修 | `Test-Gate`：ShouldProcess + ShouldContinue 必弹 |
| 4 | `-KeepBackups` + 自动清理 | ✅ 已修 | 默认 3，restore 后轮转；T3 验证 ≤2 |
| 5 | restore 前 diff 预览 | ✅ 已修 | 确认前输出「将删除 N 个新增 / 覆盖 M 个」 |
| 6 | `status` 显示快照后新增数 | ✅ 已修 | 新增/变更/被删 三项 + 风险提示 |
| 7 | `protect` 加确认 | ✅ 已修 | Test-Gate 全覆盖 |
| 8 | 大目录并行哈希 | ⏸ defer | 理由：PS 5.1 Job 开销可能反超收益，且当前目标目录 <10K 文件；真到大目录再优化（记入 ponytail debt） |

## 测试补全（verify.ps1）

| # | 用例 | 结果 |
|---|---|---|
| T1 | 锁定文件 → restore 不崩、报漂移、非 0 退出、未锁文件仍恢复、解锁后可重试 | ✅ PASS（**且抓到真 bug：Get-FileHash 读锁文件曾直接崩，已修为计入漂移**） |
| T2 | 快照目录缺失 → 拒绝执行 + 明确报错 | ✅ PASS |
| T3 | KeepBackups=2 连续 restore → 备份数 ≤2 | ✅ PASS |
| T4 | Unicode/空格/括号文件名全流程 | ✅ PASS |
| T5 | junction 界外拒 / 界内放 | ✅ PASS（首轮测试夹具自身放错位置，修正后过） |
| T6 | unprotect -Purge 后重 protect，状态干净 | ✅ PASS |

## 顺带修掉的工程坑（入记忆）

1. Write 工具存 ps1 无 BOM → PS 5.1 按 GBK 解析咬坏语法 → 统一转 UTF-8 BOM
2. `-File` 模式传 `-Confirm:$false` 绑不上 SwitchParameter → 自建 `-AutoConfirm`
3. `$ErrorActionPreference='Stop'` 会把子进程 stderr 变终止性错误 → helper 内临时降级 + ErrorRecord 转字符串
4. `$script:AutoConfirm` 作用域：函数内读脚本级参数必须 `$script:` 前缀

## 结论

REVIEW-001 闭环。deepfreeze 试点达到可交付状态。按协同手册 v3 清理规则，TASK-001 / REVIEW-001 / 本回执三张卡在 sir 过目后归档删除。
