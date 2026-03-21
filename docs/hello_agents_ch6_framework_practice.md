# Hello-Agents 第六章：框架开发实践（精读笔记）

**来源**：[DataWhale《Hello-Agents》第六章](https://datawhalechina.github.io/hello-agents/#/./chapter6/%E7%AC%AC%E5%85%AD%E7%AB%A0%20%E6%A1%86%E6%9E%B6%E5%BC%80%E5%8F%91%E5%AE%9E%E8%B7%B5) · [GitHub](https://github.com/datawhalechina/Hello-Agents)

**本文定位**：压缩版学习笔记——用**表格 + 要点**概括教材逻辑；**完整原文、长代码与日志**请以官方章节与仓库 `code` 为准。本仓库 LangGraph 实战说明另见 [`langgraph_search_assistant.md`](./langgraph_search_assistant.md)。

---

## 本章在讲什么

手写 ReAct / Plan-and-Solve 适合理解原理；要做多个、复杂、可维护的智能体应用，应转向**框架**：把主循环、状态、工具、记忆、日志与观测等共性抽掉，你只写业务。本章用**四个代表性框架 + 四个完整案例**对比「怎么协作、怎么控流程」。

---

## 6.1 为什么需要框架

| 价值       | 要点                                                                                           |
| ---------- | ---------------------------------------------------------------------------------------------- |
| **分层**   | 模型层 / 工具层 / 记忆层解耦，便于替换实现。                                                   |
| **可观测** | Callbacks（如 `on_llm_start`、`on_tool_end`、`on_agent_finish`）系统化追踪，优于到处 `print`。 |
| **代际**   | LangChain、LlamaIndex 偏第一代通用范式；新一代更强调**多智能体协作**与**复杂工作流控制**。     |

---

## 6.1.2 四框架总览（教材表 6.1 压缩）

| 框架           | 一句话                      | 协作与控制                                                                              |
| -------------- | --------------------------- | --------------------------------------------------------------------------------------- |
| **AutoGen**    | 多智能体 **群聊**           | 对话与消息驱动轮替；角色 + 规则，任务在自动对话中推进。                                 |
| **AgentScope** | **消息驱动** 的多智能体平台 | `Msg` 为中心，Hub/Pipeline 编排；强调工程化、并发、分布式。                             |
| **CAMEL**      | **双智能体角色扮演**        | `Role-Playing` + **Inception Prompting**（初始结构化提示），少写流程多靠协议约束对话。  |
| **LangGraph**  | **有向图 / 状态机**         | 节点 = 步骤（调 LLM、工具），边 = 跳转；**天然支持循环**，适合 Reflection、分支与回退。 |

---

## 6.2 AutoGen

**哲学**：以**对话**组织协作，复杂任务 ≈ 多角色自动群聊。

**机制（教材以 0.7.4 为例）**

- 分层：`autogen-core`（底层）+ `autogen-agentchat`（对话应用 API）。
- **异步优先**：多路 LLM 等待时不阻塞。
- **AssistantAgent**：绑 LLM，靠 **System Message** 定角色与交接话术。
- **UserProxyAgent**：既可代表用户，又可执行代码/工具；常负责发 **`TERMINATE`** 结束协作。
- 多智能体协调：**RoundRobinGroupChat** 按 `participants` 顺序发言；**TextMentionTermination**、`max_turns` 防死循环。

**案例：软件开发团队**

- 角色：产品经理 → 工程师 → 代码审查 → 用户代理。
- 任务：用 **Streamlit** 做 **比特币价格** Web（需求—实现—审查—验收闭环）。
- 非 OpenAI 兼容端点：可在 `OpenAIChatCompletionClient` 里配 **`model_info`** 声明能力边界。

**优劣**

- **长**：贴近人类协作、角色复用、人在回路自然。
- **短**：对话不确定易跑偏；调试靠**长对话历史**（「对话式调试」）。

---

## 6.3 AgentScope

**哲学**：**工程化**优先——组合式架构 + **消息**而非单纯函数调用链；偏「智能体操作系统」。

**结构（教材分层）**

- 基础：`Message`、`Memory`、`Model API`、`Tool`。
- 智能体层：ReAct、钩子、并行工具、异步等。
- 协作：**MsgHub** 路由；**Pipeline** 顺序/并发编排。
- 上层：Runtime、Studio 等工具链。

**消息驱动的收益**：异步解耦、**位置透明**（本地/远程）、易观测、可持久化与重试。

**智能体**：继承 **AgentBase**，核心实现 **`reply(Msg) -> Msg`**；可选 **`observe`**。

**MsgHub**：点对点 / 广播 / 组播；可落库（如 SQLite、MongoDB）；跨节点 **RPC** 对开发者透明。

**案例：三国狼人杀**

- 三层：**游戏控制类**（全局状态与阶段）、**MsgHub**（一切对话与私聊频道）、**DialogAgent + 提示词**（游戏规则 + 三国人物性格）。
- 狼人夜：**MsgHub** 建狼人私密频道；讨论后轮询 **`fanout_pipeline`** 并行收「击杀投票」，贴近「同时投票」。
- **Pydantic 结构化输出**（如讨论、女巫行动）把规则写进字段与校验，减少胡编。
- **容错**：单智能体异常时用默认结构化结果，游戏不中断。

**优劣**

- **长**：并发与规则约束强，适合复杂多智能体、要稳定跑在生产形态的场景。
- **短**：学习异步与消息范式成本高；简单对话可能**过度工程**；生态仍在长。

---

## 6.4 CAMEL

**哲学**：**轻架构、重提示**——两个互补角色 + **Inception Prompting**，用协议（一次一步、完成标记等）约束自主多轮对话。

**角色模型（经典）**

- **AI User**：提需求、拆步骤（如「交易员」）。
- **AI Assistant**：执行与产出（如「Python 程序员」）。

**案例：拖延症科普电子书**

- **RolePlaying**（`assistant_role_name` / `user_role_name` / `task_prompt`）；作家推结构，心理学家给实证内容。
- 循环：`init_chat()` → 反复 **`step()`**；出现 **`<CAMEL_TASK_DONE>`** 则结束。
- 协作阶段（教材描述）：对齐框架 → 内容生产循环 → 润色与事实核对 → 收尾。

**教材亦提到**：CAMEL 生态在扩展（多模态、工具、多后端、与 LangChain / CrewAI / AutoGen 等互通）。

**优劣**

- **长**：双专家深度协作、代码量少、行为可很灵活。
- **短**：强依赖提示质量、难定位失败原因；大规模多智能体、硬流程、极高并发分别不如 AutoGen 群聊路由、LangGraph 图、AgentScope 消息架构。

---

## 6.5 LangGraph

**哲学**：把执行流画成 **StateGraph**——共享 **State**、**Node** 返回部分更新、**Edge / conditional_edges** 决定下一步；**循环**一等公民。

**三要素**：`TypedDict` 状态；节点函数；普通边 + **条件边**（路由函数返回下一节点名或 `END`）。

**案例：三步搜索问答助手**

1. **Understand**：从用户话里提炼 **`user_query` + `search_query`**。  
2. **Search**：教材示例为 **Tavily**；失败则 **`step=search_failed`**。  
3. **Answer**：成功则结合检索生成；失败则回退为「仅凭模型知识」并说明情况。

图结构：线性 **`START → understand → search → answer → END`**；可挂 **checkpointer**（如 `InMemorySaver`）做状态持久化。本仓库实现与差异见 [`langgraph_search_assistant.md`](./langgraph_search_assistant.md)。

**优劣**

- **长**：流程**显式、可审计、可预测**；易插**人在回路**；条件边做反思/重试/回退。
- **短**：样板多；偏「怎么跑」而非开放式群聊涌现；调试要懂**全图与状态传递**。

---

## 6.6 本章小结（两条主轴）

1. **涌现式协作 vs 显式控制**  
   AutoGen、CAMEL：靠角色与目标，协作从对话里**长出来**——像人，但更难预测。  
   LangGraph：每一步和分支写死——像流程引擎，**可靠、可观测**，少一点惊喜。

2. **工程化**  
   不论选哪种协作范式，上生产都要面对并发、容错、分布式；**AgentScope** 这条线把「能跑」往「能稳定服务」推。

---

## 参考文献（教材）

[1] AutoGen (COLM 2024) · [2] AgentScope (arXiv:2402.14034) · [3] CAMEL (NeurIPS 2023) · [4] [LangGraph](https://github.com/langchain-ai/langgraph) · [5] [AutoGen UserProxyAgent 文档](https://microsoft.github.io/autogen/stable/reference/python/autogen_agentchat.agents.html#autogen_agentchat.agents.UserProxyAgent)

---

*精读笔记 · 替代不了原文章节；需要长代码与完整日志请打开官方第六章。*
