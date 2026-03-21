# Cursor：Commands、Skills、Rules 与 Sub-agent

本文说明在 Cursor 生态中几类常见「配置与协作机制」各自解决什么问题、如何触发、如何搭配。可与 `docs/context_engineering_practice.md` 中的**子 Agent 架构**、**上下文策展**对照阅读。

---

## 1. 总览：四类东西各管什么

| 类型 | 典型位置 / 形态 | 主要作用 | 谁触发 |
|------|-----------------|----------|--------|
| **Rules** | `.cursor/rules/*.mdc`、部分团队用根目录 `AGENTS.md` 等 | **长期、默认**的行为约束与项目惯例（代码风格、安全红线、流程偏好） | 按规则配置**自动或按文件匹配**注入上下文 |
| **Skills** | 用户或团队的 `SKILL.md`（如 `~/.cursor/skills/`、插件附带） | **可复用的专长说明**：何时适用、遵循什么步骤与标准 | 系统/模型按任务与 **description** 等**匹配后加载** |
| **Commands** | `.cursor/commands/*.md` | **显式工作流**：一次跑完「规格 → 计划 → …」这类固定剧本 | **你在输入框用 `/` 主动选择** |
| **Sub-agent** | IDE 内「子任务 / 并行 Agent」等能力；或你在应用里自建的子调用 | **隔离上下文**做子任务，向主会话**只回传摘要** | 主 Agent **委派**或由你手动拆任务 |

下面分节展开。产品界面与文件名可能随 Cursor 版本微调，以你当前客户端说明为准。

---

## 2. Rules（规则）

### 2.1 是什么

**Rules** 是贴在项目（或全局）上的**持久指令**，用来回答：「在这个仓库里，AI 默认应该怎样写代码、怎样沟通、哪些事禁止做？」

常见落盘形式包括：

- **项目规则**：`.cursor/rules/` 下的规则文件（例如 `.mdc`，可带 YAML frontmatter）。  
- **其它约定**：部分团队用根目录 `AGENTS.md`、`CONTRIBUTING` 中与 AI 协作相关的章节等，视团队是否把它接进 Cursor 而定。

### 2.2 与 Commands / Skills 的差别（记忆锚点）

- **Rules**：偏 **默认值** —— 不点命令、不提 skill，也应尽量遵守。  
- **Commands**：偏 **单次流程** —— 你明确说「现在执行 plan 这条线」。  
- **Skills**：偏 **某类任务的专门打法** —— 任务对上描述才强调那份做法。

### 2.3 实践建议

- 把 **稳定、通用** 的内容放 Rules（命名、测试要求、禁止提交密钥）。  
- 把 **冗长、仅偶尔需要** 的 playbook 放 Commands 或拆成 Skill，避免每条对话都占满上下文。  
- 规则过多时注意 **上下文工程**：能合并的合并，能「按路径匹配」的不要全局 Always Apply（若你的版本支持该粒度）。

---

## 3. Skills（技能）

### 3.1 是什么

**Skills** 通常是一份结构化的 `SKILL.md`：**description** 写清「什么情况下该用我」，正文写步骤、检查清单、与项目工具的约定等。  
作用类似给模型一本**按需打开的专题手册**，而不是每次对话都全文塞进系统提示。

### 3.2 与 Commands 的差别（再强调）

| 维度 | Skills | Commands |
|------|--------|----------|
| 触发 | 常由**任务语义匹配**到 description | **你输入 `/命令名`** |
| 内容形态 | 原则、规范、多场景复用 | 一条流程从头到尾（常含 `$ARGUMENTS`） |
| 典型用途 | TDD、设计系统、文档驱动开发 | Spec Kit：`/speckit.plan` 等 |

二者可同时存在：例如用 Command 拉起「从 spec 生成 plan」，实现阶段仍受「测试先行」类 Skill 约束。

---

## 4. Commands（命令）

### 4.1 是什么

**Commands** 是 `.cursor/commands/` 下的 Markdown：正文多为**给 AI 的执行说明**，前面可有 YAML（如 `description`、`handoffs`）。  
你在聊天里用 **`/`** 选择后，相当于**注入整段剧本**；`$ARGUMENTS` 会替换为你跟在命令后面的文字。

### 4.2 本仓库中的例子

当前仓库的 `speckit.*` 系列（如 `speckit.plan.md`）把 **Specify / Plan / Tasks / Checklist / Implement / Analyze** 等流程固化为命令，并可通过 `handoffs` 建议下一步接力命令。

### 4.3 实践建议

- 适合 **重复率高、步骤易遗漏** 的流程。  
- 命令正文过长时，可拆成「主命令 + 多个子命令」，或用 Rules 写死不变的红线，命令里只写可变步骤。

---

## 5. Sub-agent（子 Agent）

「Sub-agent」在不同层次有两种常见含义：**产品内的子任务**，与**你在系统里自己实现的子调用**。都服务于同一件事：**把重活放在隔离上下文里做，主线程只保留高信号摘要**（与 Anthropic 上下文工程文中子 Agent 架构一致：[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)）。

### 5.1 IDE / Cursor 语境（概念层）

在支持多任务、并行或子会话的 Agent 产品中，主对话可以把工作**拆给子 Agent**：子侧可大量读文件、尝试工具，**返回较短结论**给主侧，从而减轻 **context rot**、避免主窗口堆满中间输出。  
具体菜单名、是否并行、如何汇总，以你使用的 Cursor 版本文档为准。

### 5.2 应用代码语境（本仓库对照）

不依赖 IDE 也能实现**同一思想**：例如 `docs/langgraph_search_assistant.md` 中描述的 **`supervisor.py`**——每完成图上的一个节点，用**独立一次 LLM 调用**核对状态；监督模型看到的是 `state_audit_blob()` **截断后的状态**，而不是整条原始工具流水。这是典型的「子调用 + 浓缩上下文」，语义上可称为 **Sub-agent 模式**。

### 5.3 何时考虑 Sub-agent

- 探索空间大（大仓检索、多轮试错）而主任务只需结论。  
- 需要**不同 system 提示**（如「严格审计」vs「自由编码」）又不想混在同一消息历史里。  
- 长任务中与 **Compaction、外部笔记** 配合，避免单窗口无限增长。

---

## 6. 如何搭配（简图）

```text
Rules          → 默认约束（全局/按路径）
Skills         → 某类任务的专门打法（按需匹配）
Commands       → 你显式触发的固定流程（/xxx）
Sub-agent      → 重活外包到子上下文，主会话只收摘要
```

**推荐心智**：Rules 管「底线」；Skills 管「这类事怎么做」；Commands 管「今天把这条流水线跑一遍」；Sub-agent 管「别让主窗口被探索过程撑爆」。

---

## 7. 相关文档

- `docs/context_engineering_practice.md` — 上下文工程与子 Agent 在原理层的关系。  
- `docs/langgraph_search_assistant.md` — 本仓库中节点级监督（Sub-agent 语义）的落地说明。  
- `docs/sdd_development_practices.md` — 规格驱动与工件沉淀（也可视为「上下文外真相源」）。

---

## 8. 修订说明

本文描述的是 **Cursor 生态中常见概念**与**本仓库已有结构**的对应关系；若官方对 Rules / Commands / Skills 的路径或 frontmatter 字段有更新，以 [Cursor 官方文档](https://cursor.com/docs) 为准，并可在本文件末尾追加变更记录。
