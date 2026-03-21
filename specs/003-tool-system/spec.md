# Feature Specification: HelloAgents 7.5 工具系统

**Feature Branch**: `003-tool-system`  
**Created**: 2025-03-22  
**Status**: Implemented  
**Input**: 教材 7.5 节——统一工具抽象与注册、自定义工具、多源搜索、工具链与异步执行

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 统一注册与执行工具 (Priority: P1)

作为使用 HelloAgents 的开发者，我希望用同一套 API 注册「类工具」与「字符串函数工具」，并在 Agent 提示词与 OpenAI function calling 中自动获得一致的工具描述与 schema，以便快速扩展能力。

**Why this priority**: 工具系统是 Agent 调用外部能力的根基。

**Independent Test**: 仅注册计算器类工具与 `register_function` 注册的函数工具后，`get_tools_description` 与 `execute_tool(name, str)` 均可正确工作。

**Acceptance Scenarios**:

1. **Given** 已注册 `CalculatorTool`，**When** 调用 `execute_tool("calculator", "1+2")`，**Then** 返回期望的数值文本结果。
2. **Given** 已用 `register_function` 注册 `my_calculator`，**When** 调用 `execute_tool("my_calculator", "sqrt(9)")`，**Then** 返回正确计算结果字符串。

---

### User Story 2 - 多源搜索与降级 (Priority: P2)

作为应用开发者，我希望在配置 Tavily 和/或 SerpApi 密钥时，搜索工具能优先使用更合适的后端并在失败时降级，以便提高可用性。

**Why this priority**: 生产场景常见多供应商与网络波动。

**Independent Test**: 在仅有其一密钥或两者皆有时，`SearchTool` 的 `run`/`execute_tool` 返回可读结果或明确配置提示。

**Acceptance Scenarios**:

1. **Given** 仅 `TAVILY_API_KEY` 有效，**When** 使用 hybrid 模式查询，**Then** 返回 Tavily 格式化结果或明确错误信息。
2. **Given** Tavily 失败且 SerpApi 可用，**When** hybrid 模式查询，**Then** 自动尝试 SerpApi（若实现包含降级逻辑）。

---

### User Story 3 - 工具链与并行执行 (Priority: P3)

作为进阶开发者，我希望将多个已注册工具按模板顺序串联，并可选地并行执行多个工具调用，以便组合复杂流程与缩短延迟。

**Why this priority**: 体现教材 7.5.4 高级特性。

**Independent Test**: 注册链后 `ToolChainManager.execute_chain` 完成；`AsyncToolExecutor` 对多个独立计算任务返回与顺序一致的结果列表。

**Acceptance Scenarios**:

1. **Given** 注册表含搜索与计算工具，**When** 执行示例工具链，**Then** 各步骤按模板展开上下文并产生最终字符串输出。
2. **Given** 多个仅计算类任务，**When** `execute_tools_parallel` 调用，**Then** 全部任务完成且无未捕获异常。

---

### Edge Cases

- 重复注册同名工具时应给出覆盖警告并以后者为准。
- 未配置任何搜索密钥时应返回可操作的配置说明，而非空指针或崩溃。
- `execute_tool` 的字符串输入应能映射到工具声明的主参数名（如 `query` / `expression` / `input`）。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 框架 MUST 提供可扩展的工具基类（含 `run`、`get_parameters`、OpenAI schema 生成）。
- **FR-002**: 框架 MUST 提供 `ToolParameter` 用于描述参数名、类型、是否必填与默认值语义（用于 schema 文案）。
- **FR-003**: `ToolRegistry` MUST 支持 `register_tool` 与 `register_function`，并支持 `get_tools_description`、`execute_tool`、`openai_tools_payload`。
- **FR-004**: 框架 MUST 提供内置 `SearchTool`，支持 hybrid / tavily / serpapi 模式及失败降级策略（在依赖与密钥允许范围内）。
- **FR-005**: 框架 SHOULD 提供 `ToolChain` / `ToolChainManager` 与 `AsyncToolExecutor`（线程池包装同步 `execute_tool`）。
- **FR-006**: 仓库 MUST 提供 `examples/7.5-tool-system` 下的教材对齐示例（计算器、高级搜索类、测试脚本、工具链与异步示例）。

### Key Entities

- **Tool / BaseTool**: 可执行、可自描述的单元。
- **ToolRegistry**: 工具名到实例的映射与统一执行入口。
- **ToolChain**: 有序步骤与模板上下文。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 在未调用外部 LLM 的前提下，计算器示例脚本能 100% 通过教材列出的算术用例。
- **SC-002**: 在已配置至少一种搜索密钥且网络正常时，搜索类调用能返回非空结构化文本（标题/摘要或答案片段）。
- **SC-003**: 现有 7.4 FunctionCallAgent 示例在注册 `CalculatorTool` 场景下行为与改动前一致（函数调用闭环仍可用）。
