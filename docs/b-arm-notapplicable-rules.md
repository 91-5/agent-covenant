# B 臂 `not_applicable` 处理规则（预注册；卡 XJ-20261108-003 D6，冻结于轮七任何数据产生之前）

> **预注册声明**：本文件在轮七任何数据产生之前冻结（与 §14 同 commit）。规则一经冻结，轮七数据产生后不得修改；修订走「披露 → §14/§15 追记 → 向前生效」。措辞纪律（EVO-20261024-001）全文适用。

## 0. 背景（§13 ⑨ 的轮七缺口）

§13 ⑨ 冻结了 B 臂命令字段的机械标记（固定前缀 `B-ARM-NOT-EXECUTED::`），评测方剥离前缀后按 A 臂同口径机械执行。轮七新增 4 条 `command_*` predicate 后出现结构性问题：**B 臂的 command_output 断言在设计上不可执行**（门禁旁路条件），其 `command_*` 判据无法产生有意义的谓词结果——若强行执行，B 臂一致率被「执行器能否跑动被声称的命令」主导，而非「编译器编译质量」。

## 1. 处理规则（冻结）

1. **结构性标记**：B 臂 `claim_type == command_output` 且 predicate ∈ `command_*` 的记录，评测方判级时**不执行**，逐条标注 `execution_status = "not_applicable"`，并计入 `not_applicable_count`。
2. **分母处理**：`not_applicable` 记录**从判级一致率的可比分母中剔除**（结构性不可比，与 evaluative 桶同型），但从**对齐率分母不剔除**（对齐只看 span 一一对应）。
3. **并列呈现**：`not_applicable_count` / `not_applicable_share` 与四项指标并列呈现，不得静默剔除。
4. **非 command_output 的 B 臂记录**：claim_type ∈ {fact_existence, fact_value, process_state} 且谓词非 `command_*` 的，照常机械执行（artifact 存在性判据与门控无关），不落 `not_applicable`。
5. **`evaluative`**：维持 §12 D2——不入任何分母。
6. **门槛适用性声明（单独，本文件核心）**：**「双一致率 ≥95%」的 §12 D4 门对 B 臂的适用性 = 有条件适用**——B 臂判级一致率的分母剔除 `not_applicable` 后，若剩余可比对 ≥ 冻结下限 30，则 B 臂门照常适用；若剔除后低于 30，B 臂只报 Wilson 区间、不作资格结论（§13 ⑦ 口径延伸）。**A 臂门无条件适用。**两臂资格分别裁定，不以 A 臂达标推断 B 臂。
7. **不洗白边界**：`not_applicable` 是**结构性标记**（门禁设计的必然），不是执行者的达标途径——B 臂断言的 believed 值仍然通过可执行判据（artifact 存在性、非命令谓词）接受机械检验；禁止把本可表达的断言改标 `not_applicable` 规避判据（编译规则检查：仅 `claim_type == command_output` 且 predicate ∈ `command_*` 的记录可标）。

## 2. 机械核验（对应 acceptance V6）

- 全部 B 臂 `command_output` 记录的 `execution_status` ∈ `{"not_applicable"}`（V6 断言）；
- `not_applicable` 记录数与 B 臂 `command_*` predicate 记录数相等（无静默遗漏）；
- 剔除后 B 臂可比对数与四项指标一并入报告，剔除前分母同表并列。

## 3. 版本与生效

- 规则版本：v1.7（随 §14）；生效：轮七影子轨数据产生起，向前生效；
- 修订路径：披露 → §14/§15 追记 → 向前生效；数据产生后不得回改本文件。
