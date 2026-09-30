# TASK-001: deepfreeze.ps1 规格审查（Ximo 侧)

> 状态: [x] 待审查 → [ ] Ximo 审查中 → [ ] 审查结论回写
> 分配给: Ximo（审查 only，不改代码）
> Jarvis 已完成实现并通过自检（verify.ps1 PASS, exit 0）

## 上下文

- 项目根: `D:\15812\projects\deepfreeze\`（仅 Jarvis 写代码）
- 原「冰点还原」工程未找到（已全盘检索无果），本版为重建试点
- 本项目同时是 Ximo↔Jarvis 代码协同流程的首个试点

## 实现摘要（Jarvis 侧）

| 件 | 说明 |
|---|---|
| `deepfreeze.ps1` | protect / restore / status / unprotect 四子命令，PowerShell 5.1 |
| `verify.ps1` | 自检：正路径（改/删/增三类破坏后 restore 核对）+ 负路径（未保护拒还原） |
| `PROBE-README.md` | 沙箱读权限探针（见下方 Ximo 的第一个动作） |

关键设计：
- 快照 = robocopy `/MIR` 镜像到 `<Source>\.freeze-snap\current`，附 manifest.json（SHA256 清单）
- restore 前自动 pre-restore 备份；restore 后按 manifest 校验，漂移 > 0 时 exit 2
- 冰点语义：快照后新增的文件在 restore 时被删除（`/MIR` 行为）
- 安全边界：默认只允许 `D:\15812\` 下目标，越界必须显式 `-Force`

## Ximo 的第一个动作（探针）

尝试读取 `D:\15812\projects\deepfreeze\PROBE-README.md` 全文：
- 读得到 → 在 `questions.md` 回「探针通过 + 第一行内容」
- 读不到/报错 → 回「探针失败 + 报错信息」，走降级方案

## 请审查（不需要读代码也能答的部分）

1. **安全边界评审**：默认锁 `D:\15812\` 够不够？有没有你见过的翻车姿势我没防？
2. **restore 误操作面**：`ShouldProcess` 确认 + pre-restore 备份，作为防呆够吗？还差什么？
3. **冰点语义风险**：「快照后新增文件在 restore 时被删除」这个语义，有没有让你不安的使用场景？
4. **验收标准**：除了 verify.ps1 已覆盖的，你认为还必须补什么测试用例？

## 审查结论回写格式

在 `D:\15812\mo brain\ximo\.tasks\REVIEW-001.md` 写：
```
- 总评: (通过 / 有条件通过 / 打回)
- 阻塞级问题: (有则列, 没有写"无")
- 建议级问题: (可选)
- 建议补充的测试: (可选)
```
