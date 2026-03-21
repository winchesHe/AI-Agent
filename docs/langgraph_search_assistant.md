# LangGraph：状态图与三步搜索问答助手

**LangGraph** 是 LangChain 生态里偏「控制流」的扩展：把智能体执行建模为**有向图**，**节点（Node）**做具体计算（调 LLM、调工具），**边（Edge）**决定走向；配合**条件边**可表达循环、分支与容错。这与以「对话轮替」为中心的 AutoGen、CAMEL 等形成对照——你显式编写**状态如何演进**，而不是主要依赖群聊涌现。

本仓库示例实现教材 **6.5.2** 的固定三步：**理解 → 搜索 → 回答**。搜索层使用项目已有的 **SerpApi**（`tools.web_search.search`），LLM 使用 **OpenAI 兼容**的 `HelloAgentsLLM`，不强制安装 `langchain-openai`。

---

## 1. 三个基本要素（6.5.1）

### 1.1 全局状态 State

全图共享一份状态（常用 `TypedDict` 描述）。各节点读取字段、返回**部分更新**，由框架合并进当前快照。

本例见 `SearchState`：`messages`（带 `add_messages` 归约）、`user_query`、`search_query`、`search_results`、`final_answer`、`step`。

### 1.2 节点 Node

节点是普通 Python 可调用对象：`state_in → dict 更新`。本例三个节点在 `nodes.py` 中由 `build_nodes(llm)` 绑定同一个 `HelloAgentsLLM`。

### 1.3 边 Edge

本例为**线性图**：`START → understand → search → answer → END`。教材中的**条件边**（如 `should_continue` 在 planner/executor 间循环）可在同项目里按相同模式扩展：对 `add_conditional_edges` 返回的键映射到下一节点或 `END`。

---

## 2. 三步助手在做什么（6.5.2）

| 节点 | 职责 |
|------|------|
| **understand** | 解析用户最后一则 `HumanMessage`，让 LLM 输出「理解 + 搜索词」，写入 `user_query` / `search_query`，`step=understood`。 |
| **search** | 用 `search_query` 调用 SerpApi；失败则 `step=search_failed` 并保留错误信息，供回答节点走回退策略。 |
| **answer** | 成功则结合 `search_results` 生成答案；失败则提示基于模型知识回答。更新 `final_answer` 与 `step=completed`。 |

图编译时使用 `MemorySaver` 作为 checkpointer，便于与教材一致、后续可接多轮线程 ID（`configurable.thread_id`）。

---

## 3. 每步完成后的「Sub-agent 核对」

教材实现完成后，常见需求是**逐步验收**。本示例在**运行时**每结束一个节点，立刻用**另一路 LLM 调用**（独立 system/user 提示）扮演监督员，按节点检查状态字段是否合格，并打印 `PASS/FAIL` 与理由（见 `supervisor.py`）。

这与 IDE 里 Cursor 的 **Task subagent** 不是同一机制，但语义一致：**每完成一个任务（节点）就与 subagent 核对**，再进入下一节点（下一任务由 LangGraph 自动继续）。

若监督返回 `FAIL`，当前实现**不中断图**（避免线上卡死），仅记录日志；你可改为在 `runner.py` 里根据 `verdict` 触发重试或 `END`。

---

## 4. 如何运行

```bash
cd <项目根目录>
pip install -r requirements.txt   # 含 langgraph、langchain-core
python -m src.scripts.run_langgraph_search
```

环境变量：`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL_ID`；搜索需要 `SERPAPI_API_KEY`。

---

## 5. 代码落点（速查）

| 教材概念 | 位置 |
|----------|------|
| `SearchState` | `langgraph_search_assistant/state.py` |
| 三节点 | `langgraph_search_assistant/nodes.py` |
| `StateGraph` 组装 | `langgraph_search_assistant/graph.py` |
| 流式执行 + 逐步监督 | `langgraph_search_assistant/runner.py` |
| 监督提示与解析 | `langgraph_search_assistant/supervisor.py` |
| 交互入口 | `src/scripts/run_langgraph_search.py` |

---

## 6. 优势与局限（6.5.3）

**优势**：流程**可见、可测、可审计**；节点即函数，易单测与插桩；天然支持条件边与环，适合「反思—再试」类控制流；中间可插人审节点。

**局限**：比纯对话式多智能体**样板代码更多**；行为不如开放式对话「涌现」灵活；调试要同时看节点逻辑、状态合并与边的条件。

选型简要对比：**要强流程与容错** → LangGraph；**要角色扮演共创** → CAMEL RolePlaying；**要固定轮询 + 人在环** → AutoGen 群聊等。
