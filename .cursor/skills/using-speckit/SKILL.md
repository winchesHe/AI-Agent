---
name: using-speckit
description: MANUAL ATTACHMENT ONLY — Do not infer or apply from casual mentions of specs or plans. Orchestrates this repository’s Spec Kit flow (constitution/memory, specify, plan, tasks, implement) by delegating to .cursor/commands/speckit.*. Use only when the user attached this skill or explicitly asked to follow the using-speckit / spec-kit manual workflow.
---

# Spec Kit 流程（using-speckit）

## 何时启用（硬规则）

- **仅**在：用户**手动附加**本 skill，或**明确写出**要按 `using-speckit` /「spec-kit 手动流程」执行时，才按本文件推进。
- 对话里偶然出现「写个 spec」「做个计划」等表述，**不**自动视为启用本 skill。

## 总流程（默认顺序）

```text
[可选] Constitution / Memory → Specify → Plan → Tasks → Implement
         ↑ 见下文「何时做 memory」
```

可选增强（按需插入，不改变主链语义）：

- **Clarify**：需求不清、验收标准含糊时，在 Specify 前后使用 `.cursor/commands/speckit.clarify.md`。
- **Checklist**：质量域（安全、UX 等）需要门禁时，在 Tasks 之后、Implement 之前参考 `.cursor/commands/speckit.checklist.md`。
- **Analyze**：大规模改动或跨模块一致性，可在 Tasks 生成后参考 `.cursor/commands/speckit.analyze.md`。

## 各阶段做什么（执行准则）

每一阶段以仓库内对应 **命令说明** 为唯一详细步骤来源（含脚本路径、JSON 解析、钩子与 handoff）。执行该阶段时：**先读取对应文件，再严格按其 Outline 操作**。

| 阶段                  | 命令说明文件                               | 核心产出 / 动作                                                  |
| --------------------- | ------------------------------------------ | ---------------------------------------------------------------- |
| Memory / Constitution | `.cursor/commands/speckit.constitution.md` | 维护 `.specify/memory/constitution.md`，必要时同步模板与依赖文档 |
| Specify               | `.cursor/commands/speckit.specify.md`      | 特性分支、`specs/<feature>/spec.md` 等                           |
| Plan                  | `.cursor/commands/speckit.plan.md`         | `plan.md`、设计产物；加载 constitution                           |
| Tasks                 | `.cursor/commands/speckit.tasks.md`        | 依赖有序的 `tasks.md`                                            |
| Implement             | `.cursor/commands/speckit.implement.md`    | 按 `tasks.md` 分阶段实现；尊重 checklists 状态                   |

脚本与配置根目录：**`.specify/`**（如 `scripts/bash/create-new-feature.sh`、`setup-plan.sh`、`check-prerequisites.sh` 等，以各命令文件为准）。

注意：
1. 生成的文档内容必须是中文的。
2. 不需要创建新的分支。

## 何时做 memory（Constitution）

在下列情况**优先或必须**走 `speckit.constitution` 对应流程（读取 `.cursor/commands/speckit.constitution.md`）：

- 新项目 / 首次固化工程原则与治理规则。
- 用户要求新增、修改、删除原则或治理条款（版本号、修订日期、同步模板）。
- `.specify/memory/constitution.md` 仍为大量占位符（`[PROJECT_NAME]` 等），且即将编写会引用它的 **Plan / Spec**。
- 架构或质量门禁发生**全局级**变更，需要反映到 constitution 与模板一致性。

若当前特性仅局部实现、与原则无关，可跳过 constitution，直接从 Specify 进入。

## 与用户协作方式

1. 确认本次是否包含 constitution 更新；确认特性描述是否足够写 spec。
2. 按上表顺序推进；每一阶段结束前用**简短中文**说明本阶段完成项与下一阶段入口。
3. 遇到命令文件中要求的**用户确认**（如 checklist 未完成是否继续实现），必须等待用户答复后再继续。

## 额外参考（按需）

- 扩展钩子：`.specify/extensions.yml`（各 `hooks.before_*` 键，以各命令文件说明为准）。
- 分支编号：`.specify/init-options.json` 中的 `branch_numbering`（影响 `create-new-feature.sh` 参数）。
