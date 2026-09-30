# REVIEW-001: deepfreeze.ps1 规格审查结论

> 审查人: Ximo
> 日期: 2026-09-29
> 被审对象: `deepfreeze.ps1` (167行) + `verify.ps1` (67行)
> 探针结果: ✅ 通过 — 第一行 `# 沙箱读权限探针（PROBE）`，沙箱外可读确认

---

## 逐项审查回答

### 1. 安全边界评审：默认锁 `D:\15812\` 够不够？

**基本够用，但有一个真实漏洞：**

- `Resolve-Path` 在 PowerShell 5.1 中**不解析符号链接/junction**。如果在 `D:\15812\projects\` 下人为建一个 junction 指向 `C:\Windows`，`StartsWith("D:\15812\")` 通过，但 robocopy `/MIR` 实际操作的是 `C:\Windows`。这是最可能的翻车姿势。
- 其余风险已防住：UNC 路径、`..` 穿越、大小写（Win 不敏感）都没问题。
- `-Force` 只 `Write-Warning` 不二次确认——对破坏性操作偏弱。

**建议**：
- 加一条检查：`Get-Item $full | Select-Object LinkType`，若为 Junction/Symlink 则拒绝或需额外确认。
- `-Force` 路径加 `$PSCmdlet.ShouldProcess($full, '跨越安全边界')` 或 `Read-Host "输入 YES 确认"` 二次验证。

### 2. restore 误操作面

**防呆基本到位，有两个缺口：**

| 已有防护 | 缺口 |
|---------|------|
| `ShouldProcess` 确认 ✓ | 确认提示太笼统，没列出「将删除 N 个快照后新增文件 / 将覆盖 M 个文件」 |
| pre-restore 备份 ✓ | 备份目录 `prerestore-*` 无上限、无清理机制，反复 restore 会撑爆磁盘 |
| 哈希校验 drift=0 ✓ | — |

**建议**：
- restore 前跑一次 diff（对比快照 manifest 与当前文件列表），输出「将删除 3 个文件、覆盖 1 个文件」再让 `ShouldProcess` 确认。
- 加 `-KeepBackups <n>` 参数（默认 3），restore 完自动清理超出上限的旧 pre-restore 目录。
- `exit 2`（第138行）会杀死调用者的 shell 进程——脚本内应改用 `throw` 或 `Write-Error` + `$global:LASTEXITCODE = 2`。

### 3. 冰点语义风险

**「快照后新增文件在 restore 时被删除」确实有不安心场景：**

- **用户误操作**：protect 后写了新文件，忘了自己保护过，手滑 restore → 文件消失（虽有 pre-restore 备份，但用户大概率不知道）。
- **运行中程序**：受保护目录下有进程写日志/缓存，restore 时文件被锁 → robocopy `/R:1` 跳过 → 哈希校验 drift > 0 → exit 2（实际是 exit 0 但校验失败）→ 目标目录处于半还原状态。
- **网络映射盘**：restore 到一半网络断开，部分文件已覆盖，部分没到 → 同上。

**建议**：
- `status` 子命令增加「快照后新增文件数」提示（对比 manifest 文件列表与当前目录），让用户在 restore 前知情。
- 文档/注释强调「restore 是破坏性操作，请确认没有未保存的新文件」。

### 4. 验收标准：必须补的测试

verify.ps1 覆盖了核心正/负路径，以下场景**必须补**：

| # | 用例 | 预期 | 优先级 |
|---|------|------|--------|
| T1 | 受保护目录中有文件被进程锁定（`[IO.File]::Open` 保持句柄）→ restore | 跳过锁定文件，drift>0，exit 2，不崩 | 高 |
| T2 | protect 后手动删除 `.freeze-snap\current\` 目录 → restore | 报「快照目录缺失」，不执行 | 高 |
| T3 | 连续 restore 3 次 → 检查 `prerestore-*` 目录数 ≤ KeepBackups | 旧备份被清理 | 中 |
| T4 | 目标目录含 Unicode/空格/特殊字符文件名（`测试 文件(1).txt`）→ 全流程 | manifest 哈希正确，restore 成功 | 中 |
| T5 | 在 `D:\15812\` 下建 junction 指向外部 → protect | 被拒绝或明确警告 | 高 |
| T6 | unprotect -Purge 后立即 re-protect | state.json 正确重建，snapshot 干净 | 中 |

---

## 总评

- **总评: 有条件通过**
- **阻塞级问题: 无**（核心逻辑正确，verify.ps1 证明四子命令主路径全部 OK）
- **建议级问题:**
  1. `exit 2`（L138）改为 `throw` / `Write-Error`，避免杀死调用 shell
  2. junction/symlink 穿透检查（安全边界加固）
  3. `-Force` 路径加二次确认
  4. pre-restore 备份加 `-KeepBackups` 上限 + 自动清理
  5. restore 前输出 diff 预览（将删除/覆盖哪些文件）
  6. `status` 增加「快照后新增 N 个文件」提示
  7. `protect` 也加 `ShouldProcess`（当前只有 restore/unprotect 有）
  8. `Get-Manifest` 对大目录（>10K文件）可考虑并行哈希（性能优化，非必须）
- **建议补充的测试: 上表 T1–T6，其中 T1/T2/T5 为高优**

---

*审查完成。Jarvis 侧可按「建议级问题」逐条处理或标注 defer；高优先测试建议在下一轮 verify.ps1 迭代中覆盖。*
