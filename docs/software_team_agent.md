# 软件开发团队 Agent：架构设计

本文档说明「软件开发团队」多智能体协作案例的架构设计、所用框架与运行方式，面向希望理解或扩展本案例的开发者与架构师。

---

## 1. AutoGen 简介

**AutoGen**（全称 AutoGen - Multi-Agent Conversation Framework）是微软开源的**多智能体对话框架**，用于构建基于大语言模型（LLM）的协作式应用。支持多个智能体通过对话协作，可配置人机参与方式与发言顺序，与 OpenAI 及兼容 API 集成良好。本案例基于 **AutoGen GroupChat** 的「群聊 + 管理器」模式，实现需求分析 → 编码 → 代码审查 → 用户测试的固定顺序轮询协作。

### 1.1 框架结构的演进

新架构最显著的变化是**清晰的分层**和**异步优先**的设计理念。

- **分层设计**：框架拆分为两个核心模块：
  - **autogen-core**：底层基础，封装与语言模型交互、消息传递等核心功能，保证框架稳定性与扩展性。
  - **autogen-agentchat**：构建于 core 之上，提供开发对话式智能体应用的高级接口，简化多智能体应用开发。  
  上述分层使各组件职责明确，降低系统耦合度。

- **异步优先**：新架构全面采用异步编程（async/await）。多智能体协作中，网络请求（如调用 LLM API）是主要耗时操作；异步模式在等待某一智能体响应时可处理其他任务，避免线程阻塞，提升并发能力与资源利用效率。

### 1.2 核心智能体组件

智能体是执行任务的基本单元，在 0.7.4 及新版本中设计更加专注和模块化。

| 组件 | 说明 |
|------|------|
| **AssistantAgent（助理智能体）** | 任务的主要解决者，封装 LLM，根据对话历史生成回复（如提出计划、撰写文章或编写代码）。通过不同的**系统提示词（System Message）**可赋予不同「专家」角色。 |
| **UserProxyAgent（用户代理智能体）** | 兼具双重角色：作为人类用户的「代言人」发起任务、传达意图；作为「执行器」可配置为执行代码或调用工具，并将结果反馈给其他智能体。清晰区分「思考」（由 AssistantAgent 完成）与「行动」。 |

### 1.3 从 GroupChatManager 到 Team（轮询群聊）

多智能体协作需要协调对话流程。早期版本由 **GroupChatManager** 承担；新架构引入更灵活的 **Team / 群聊** 概念，例如 **RoundRobinGroupChat**。

- **RoundRobinGroupChat（轮询群聊）**：按预定义顺序依次让智能体发言，适用于流程固定的任务（如：产品经理提需求 → 工程师写代码 → 审查员检查）。
- **工作流**：
  1. 创建 `RoundRobinGroupChat` 实例，将所有参与智能体加入。
  2. 任务开始时，群聊按预设顺序依次激活对应智能体。
  3. 被选中的智能体根据当前对话上下文生成回复。
  4. 群聊将新回复加入对话历史，并激活下一名智能体。
  5. 重复直至达到最大轮次或满足终止条件。

---

## 2. 案例目标

本案例演示如何用 **AutoGen**（`autogen.agentchat`）构建一个**轮询协作**的软件开发流水线：

- **需求分析 → 编码 → 代码审查 → 用户测试**，四角色按固定顺序轮流发言，直至用户确认完成或达到最大轮数。
- 每个智能体有明确的**系统提示词**与职责边界，通过群聊消息传递需求、代码与反馈。
- 终止条件：用户代理在回复中输入 **TERMINATE**，或达到 **max_round**（默认 20 轮）。

默认任务为「比特币价格显示应用」（Streamlit + 实时价格与涨跌），可替换为任意开发需求描述。

---

## 3. 本案例架构：组件与职责

本案例采用 **AutoGen GroupChat** 的「群聊 + 管理器」模式（与 1.3 节 RoundRobinGroupChat 的轮询理念一致），按**组件职责**划分如下，不单独抽象框架分层：

| 组件 | 职责 | 实现 |
|------|------|------|
| **编排层** | 创建智能体、配置群聊与终止逻辑、启动对话 | `software_team_agent.py`：`run_software_development_team()` |
| **智能体层** | 四类角色：产品经理、工程师、代码审查员、用户代理 | `agents.py`：`AssistantAgent` × 3 + `UserProxyAgent` × 1 |
| **模型配置层** | 从环境变量生成 LLM 配置，供 AutoGen 使用 | `model_client.py`：`get_llm_config()` |

### 3.1 编排层 (Orchestration)

- **入口**：`run_software_development_team(task=DEFAULT_TASK)` 或对外暴露的 `run(task=...)`。
- **流程**：
  1. 调用 `get_llm_config()` 得到 `llm_config`（API Key、Base URL、模型 ID、temperature）。
  2. 使用 `agents.py` 中的工厂函数创建四名智能体：ProductManager、Engineer、CodeReviewer、UserProxy。
  3. 构建 `GroupChat(agents, messages=[], max_round=20, speaker_selection_method="round_robin")`。
  4. 使用 `GroupChatManager(groupchat, llm_config, is_termination_msg=_is_terminate)` 作为「下一个发言人」的决策者（本案例中轮询由 `round_robin` 固定顺序体现）。
  5. 通过 `user_proxy.initiate_chat(manager, message=task)` 以用户代理发起对话，将 `task` 作为首条消息传入群聊。
- **终止判断**：`_is_terminate(msg)` 检查消息内容中是否包含字符串 **TERMINATE**（大小写不敏感），用于用户代理在测试通过后结束协作。

### 3.2 智能体层 (Agents)

四名智能体均来自 `autogen.agentchat`：

| 角色 | 类型 | 职责与系统提示词要点 |
|------|------|----------------------|
| **ProductManager** | `AssistantAgent` | 需求分析、功能模块划分、技术选型、优先级与验收标准；完成后说「请工程师开始实现」。 |
| **Engineer** | `AssistantAgent` | 根据需求编写完整可运行代码（Python/Streamlit 等），带注释与错误处理；完成后说「请代码审查员检查」。 |
| **CodeReviewer** | `AssistantAgent` | 代码质量、安全性、最佳实践、错误处理审查；提供修改建议；完成后说「代码审查完成，请用户代理测试」。 |
| **UserProxy** | `UserProxyAgent` | 代表用户提出需求、验证结果、给出反馈；`human_input_mode="ALWAYS"` 表示每轮需用户输入；`code_execution_config=False` 不执行代码；在确认通过后输入 TERMINATE。 |

所有 `AssistantAgent` 共用同一套 `llm_config`；UserProxy 不调用 LLM，仅转发用户输入并参与轮询。

### 3.3 模型配置层 (Model Client)

- **文件**：`model_client.py`。
- **函数**：`get_llm_config()` 从环境变量读取 `LLM_API_KEY`（或 `OPENAI_API_KEY`）、`LLM_BASE_URL`（或 `OPENAI_API_BASE`）、`LLM_MODEL_ID`（默认 `gpt-4o`），通过 `autogen.oai.openai_utils.get_config_list` 生成 `config_list`，并返回包含 `config_list`、`model`、`temperature` 的字典，供 `AssistantAgent` 与 `GroupChatManager` 使用。

---

## 4. 协作流程示意

```
用户 / UserProxy 发起任务 (task)
        ↓
GroupChatManager 按 round_robin 选择下一个发言人
        ↓
ProductManager → 需求分析，输出「请工程师开始实现」
        ↓
Engineer → 输出代码与说明，输出「请代码审查员检查」
        ↓
CodeReviewer → 输出审查意见，输出「请用户代理测试」
        ↓
UserProxy → 等待用户输入（确认或反馈）
        ↓
若用户输入包含 TERMINATE → 结束；否则继续轮询，直至 max_round 或再次 TERMINATE
```

发言顺序由 **speaker_selection_method="round_robin"** 与智能体在 `GroupChat.agents` 中的顺序共同决定，因此会按 ProductManager → Engineer → CodeReviewer → UserProxy 循环。

---

## 5. 与三国狼人杀架构的对比（可选参考）

| 维度 | 软件开发团队 Agent | 三国狼人杀 Agent |
|------|--------------------|------------------|
| **框架** | AutoGen GroupChat + GroupChatManager | 自研 MsgHub + fanout_pipeline（仅参考 AgentScope 架构思想，未直接依赖 AgentScope 框架） |
| **流程驱动** | 轮询 + 终止词（TERMINATE） | 消息驱动的阶段编排（夜晚/白天） |
| **角色** | 4 个固定角色，顺序轮询 | N 个玩家 + 主持人，按阶段选择参与方 |
| **输出约束** | 无结构化输出，依赖提示词中的自然语言约定 | Pydantic 结构化输出约束各阶段行为 |
| **用户参与** | UserProxy 每轮需人工输入 | 可无人参与，纯多智能体推演 |

---

## 6. 如何运行

```bash
# 在项目根目录
python -m src.scripts.run_software_team
# 或
python src/scripts/run_software_team.py
```

运行后会提示输入开发任务（直接回车则使用默认「比特币价格显示应用」）；每轮 UserProxy 发言时会等待用户在控制台输入，确认通过时输入 **TERMINATE** 结束。

需在 `.env` 中配置 `LLM_API_KEY`（或 `OPENAI_API_KEY`）、`LLM_BASE_URL`（或 `OPENAI_API_BASE`）、`LLM_MODEL_ID`。

---

## 7. 代码结构速览

```
src/core/agent/software_team_agent/
├── __init__.py           # 包导出（通常暴露 run）
├── software_team_agent.py # 编排：GroupChat、GroupChatManager、run、_is_terminate、DEFAULT_TASK
├── agents.py              # 四角色：create_product_manager / create_engineer / create_code_reviewer / create_user_proxy
└── model_client.py        # get_llm_config()，依赖 autogen.oai.openai_utils

src/scripts/
└── run_software_team.py   # 独立运行脚本，调用 core.agent.software_team_agent.run
```

---

## 8. 依赖说明

- **autogen-agentchat**（旧版 `autogen.agentchat` API）：GroupChat、GroupChatManager、AssistantAgent、UserProxyAgent。
- **autogen-ext[openai]**：与 OpenAI 兼容 API 的集成。
- 模型配置通过 **autogen.oai.openai_utils.get_config_list** 生成，与项目内其他使用 OpenAI 兼容接口的模块共用同一套环境变量。

---

## 9. 框架优劣势分析

任何技术框架都有其适用场景与设计权衡。以下从本案例出发，客观分析 AutoGen 的核心优势及在实际应用中可能面临的局限与挑战。

### 9.1 优势

- **对话式建模，降低任务建模门槛**  
  无需为智能体团队设计复杂的状态机或控制流，而是将完整软件开发流程自然映射为产品经理、工程师、审查员之间的对话，更贴近人类团队协作。开发者可聚焦于定义「谁（角色）」与「做什么（职责）」，而非「如何做（流程控制）」。

- **角色专业化与可复用**  
  通过系统提示词（System Message）为每个智能体赋予高度专业化角色（如 ProductManager 专注需求，CodeReviewer 专注质量）。精心设计的智能体可在不同项目中复用，易于维护与扩展。

- **流程可预测与人类在环**  
  对流程化任务，RoundRobinGroupChat 等机制提供清晰、可预测的协作顺序。UserProxyAgent 为「人类在环」（Human-in-the-loop）提供天然接口：既可发起任务，也可作为监督者与最终验收者，确保自动化系统处于人类监督之下。

- **与 OpenAI 生态一致**  
  使用 `get_config_list`、环境变量等与项目内其他 LLM 调用方式统一，便于维护与接入。

### 9.2 局限性

- **LLM 不确定性与流程偏离**  
  RoundRobinGroupChat 虽提供顺序化流程，但基于 LLM 的对话具有不确定性。智能体可能产生偏离预期的回复，导致对话走向意外分支，甚至陷入循环。

- **对话式调试困难**  
  当智能体团队输出未达预期时，调试往往棘手。与传统程序不同，难以获得清晰错误堆栈，而是长串对话历史，形成「对话式调试」难题。

- **流程与终止的刚性**  
  本案例采用固定轮询顺序，难以按阶段或条件动态选人；终止依赖用户在 UserProxy 轮次输入 TERMINATE，无法仅靠逻辑条件自动结束。若需严格解析输出，需额外结合 Pydantic 等结构化手段。

- **API 与版本**  
  基于旧版 `autogen.agentchat` 时，框架升级需关注 API 迁移与兼容性。
