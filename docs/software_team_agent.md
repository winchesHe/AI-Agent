# 软件开发团队 Agent：架构设计

本文档说明「软件开发团队」多智能体协作案例的架构设计、所用框架与运行方式。

---

## 1. 案例目标

本案例演示如何用 **AutoGen**（`autogen.agentchat`）构建一个**轮询协作**的软件开发流水线：

- **需求分析 → 编码 → 代码审查 → 用户测试**，四角色按固定顺序轮流发言，直至用户确认完成或达到最大轮数。
- 每个智能体有明确的**系统提示词**与职责边界，通过群聊消息传递需求、代码与反馈。
- 终止条件：用户代理在回复中输入 **TERMINATE**，或达到 **max_round**（默认 20 轮）。

默认任务为「比特币价格显示应用」（Streamlit + 实时价格与涨跌），可替换为任意开发需求描述。

---

## 2. 架构设计：组件与职责

本案例采用 **AutoGen GroupChat** 的「群聊 + 管理器」模式，不单独抽象分层，而是按**组件职责**划分：

| 组件 | 职责 | 实现 |
|------|------|------|
| **编排层** | 创建智能体、配置群聊与终止逻辑、启动对话 | `software_team_agent.py`：`run_software_development_team()` |
| **智能体层** | 四类角色：产品经理、工程师、代码审查员、用户代理 | `agents.py`：`AssistantAgent` × 3 + `UserProxyAgent` × 1 |
| **模型配置层** | 从环境变量生成 LLM 配置，供 AutoGen 使用 | `model_client.py`：`get_llm_config()` |

### 2.1 编排层 (Orchestration)

- **入口**：`run_software_development_team(task=DEFAULT_TASK)` 或对外暴露的 `run(task=...)`。
- **流程**：
  1. 调用 `get_llm_config()` 得到 `llm_config`（API Key、Base URL、模型 ID、temperature）。
  2. 使用 `agents.py` 中的工厂函数创建四名智能体：ProductManager、Engineer、CodeReviewer、UserProxy。
  3. 构建 `GroupChat(agents, messages=[], max_round=20, speaker_selection_method="round_robin")`。
  4. 使用 `GroupChatManager(groupchat, llm_config, is_termination_msg=_is_terminate)` 作为「下一个发言人」的决策者（本案例中轮询由 `round_robin` 固定顺序体现）。
  5. 通过 `user_proxy.initiate_chat(manager, message=task)` 以用户代理发起对话，将 `task` 作为首条消息传入群聊。
- **终止判断**：`_is_terminate(msg)` 检查消息内容中是否包含字符串 **TERMINATE**（大小写不敏感），用于用户代理在测试通过后结束协作。

### 2.2 智能体层 (Agents)

四名智能体均来自 `autogen.agentchat`：

| 角色 | 类型 | 职责与系统提示词要点 |
|------|------|----------------------|
| **ProductManager** | `AssistantAgent` | 需求分析、功能模块划分、技术选型、优先级与验收标准；完成后说「请工程师开始实现」。 |
| **Engineer** | `AssistantAgent` | 根据需求编写完整可运行代码（Python/Streamlit 等），带注释与错误处理；完成后说「请代码审查员检查」。 |
| **CodeReviewer** | `AssistantAgent` | 代码质量、安全性、最佳实践、错误处理审查；提供修改建议；完成后说「代码审查完成，请用户代理测试」。 |
| **UserProxy** | `UserProxyAgent` | 代表用户提出需求、验证结果、给出反馈；`human_input_mode="ALWAYS"` 表示每轮需用户输入；`code_execution_config=False` 不执行代码；在确认通过后输入 TERMINATE。 |

所有 `AssistantAgent` 共用同一套 `llm_config`；UserProxy 不调用 LLM，仅转发用户输入并参与轮询。

### 2.3 模型配置层 (Model Client)

- **文件**：`model_client.py`。
- **函数**：`get_llm_config()` 从环境变量读取 `LLM_API_KEY`（或 `OPENAI_API_KEY`）、`LLM_BASE_URL`（或 `OPENAI_API_BASE`）、`LLM_MODEL_ID`（默认 `gpt-4o`），通过 `autogen.oai.openai_utils.get_config_list` 生成 `config_list`，并返回包含 `config_list`、`model`、`temperature` 的字典，供 `AssistantAgent` 与 `GroupChatManager` 使用。

---

## 3. 协作流程示意

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

## 4. 与三国狼人杀架构的对比（可选参考）

| 维度 | 软件开发团队 Agent | 三国狼人杀 Agent |
|------|--------------------|------------------|
| **框架** | AutoGen GroupChat + GroupChatManager | 自研 MsgHub + fanout_pipeline（仅参考 AgentScope 架构思想，未直接依赖 AgentScope 框架） |
| **流程驱动** | 轮询 + 终止词（TERMINATE） | 消息驱动的阶段编排（夜晚/白天） |
| **角色** | 4 个固定角色，顺序轮询 | N 个玩家 + 主持人，按阶段选择参与方 |
| **输出约束** | 无结构化输出，依赖提示词中的自然语言约定 | Pydantic 结构化输出约束各阶段行为 |
| **用户参与** | UserProxy 每轮需人工输入 | 可无人参与，纯多智能体推演 |

---

## 5. 如何运行

```bash
# 在项目根目录
python -m src.scripts.run_software_team
# 或
python src/scripts/run_software_team.py
```

运行后会提示输入开发任务（直接回车则使用默认「比特币价格显示应用」）；每轮 UserProxy 发言时会等待用户在控制台输入，确认通过时输入 **TERMINATE** 结束。

需在 `.env` 中配置 `LLM_API_KEY`（或 `OPENAI_API_KEY`）、`LLM_BASE_URL`（或 `OPENAI_API_BASE`）、`LLM_MODEL_ID`。

---

## 6. 代码结构速览

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

## 7. 依赖说明

- **autogen-agentchat**（旧版 `autogen.agentchat` API）：GroupChat、GroupChatManager、AssistantAgent、UserProxyAgent。
- **autogen-ext[openai]**：与 OpenAI 兼容 API 的集成。
- 模型配置通过 **autogen.oai.openai_utils.get_config_list** 生成，与项目内其他使用 OpenAI 兼容接口的模块共用同一套环境变量。
