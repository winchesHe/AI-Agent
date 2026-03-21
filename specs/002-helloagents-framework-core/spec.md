# Feature Specification: HelloAgents 框架核心接口（7.3）

**Feature Branch**: `002-helloagents-framework-core`  
**Created**: 2026-03-21  
**Status**: Draft  
**Input**: User description: "7.3 框架接口：message.py 统一消息格式；config.py 中心化配置与环境覆盖；agent.py 抽象 Agent 基类，与 HelloAgentsLLM、Message、Config 协同，为上层智能体提供统一结构。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 标准化消息与 API 互操作 (Priority: P1)

作为编写智能体逻辑的开发者，我需要一种类型安全、与 OpenAI Chat 消息字典一致的数据结构来表示单条对话，以便在写入历史、调用 `HelloAgentsLLM.think` 时无需手写散落字典。

**Why this priority**: 消息格式是所有对话流的基础类型。

**Independent Test**: 构造 `Message` 实例并调用 `to_dict()`，得到仅含 `role` 与 `content` 的字典，且 `role` 只能为 `user`/`assistant`/`system`/`tool` 之一。

**Acceptance Scenarios**:

1. **Given** 合法 `content` 与 `role`，**When** 创建 `Message`，**Then** 可读取字段且 `to_dict()` 符合 OpenAI 消息形状。
2. **Given** 需要扩展信息，**When** 设置 `metadata` 与时间戳，**Then** 不影响 `to_dict()` 的对外兼容输出（仍仅为 role+content）。
3. **Given** 非法 `role` 字符串，**When** 校验/构造，**Then** 在构造阶段被拒绝。

---

### User Story 2 - 可部署的配置中心 (Priority: P2)

作为在不同环境（本地、预发、生产）运行同一套示例的开发者，我希望能用环境变量覆盖温度、调试开关、日志级别等，而无需改代码。

**Why this priority**: 降低部署差异与试错成本。

**Independent Test**: 调用 `Config.from_env()`，在设置/取消特定环境变量后，对应字段发生变化；未设置时使用合理默认值。

**Acceptance Scenarios**:

1. **Given** 未设置可选环境变量，**When** 使用 `Config()` 或 `from_env()`，**Then** 框架仍可用默认模型名、默认 provider 标签、默认温度等。
2. **Given** 设置 `DEBUG=true`、`LOG_LEVEL`、`TEMPERATURE`、`MAX_TOKENS` 等，**When** `from_env()`，**Then** 解析为正确类型（布尔、字符串、浮点、可选整数）。
3. **Given** 本仓库已有 `LLM_MODEL_ID`（及可选 provider 相关变量），**When** `from_env()`，**Then** 可作为 `default_model` / `default_provider` 的来源之一，与现有 `.env` 约定兼容。

---

### User Story 3 - 智能体抽象与历史管理 (Priority: P3)

作为实现各类智能体（ReAct、Plan-and-Solve 等）的开发者，我需要继承同一抽象基类，强制实现统一入口 `run`，并复用基于 `Message` 的历史增删查接口。

**Why this priority**: 统一「智能体」契约，便于组合与测试。

**Independent Test**: 无法直接实例化抽象 `Agent`；具体子类实现 `run` 后可调用 `add_message`/`get_history`/`clear_history`，且 `str(agent)` 暴露名称与底层 LLM 的 `provider`。

**Acceptance Scenarios**:

1. **Given** 抽象类 `Agent`，**When** 尝试直接实例化，**Then** 失败。
2. **Given** 子类提供 `run`，**When** 注入 `HelloAgentsLLM` 与可选 `Config`/`system_prompt`，**Then** 可正常运行一轮文本交互（由子类定义具体逻辑）。
3. **Given** 多条 `Message`，**When** 追加后 `get_history`，**Then** 返回副本，清空后历史为空。

---

### Edge Cases

- `metadata` 为 `None` 时应规范化为空映射，避免下游对 `None` 误判。
- `MAX_TOKENS` 为空或未设置时，`max_tokens` 应为 `None`，不得因空字符串解析崩溃。
- 包路径须避免与现有 `core.agent`（具体智能体实现目录）命名冲突，采用独立子包（如 `core.hello_agents`）。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系统 MUST 提供 `Message` 模型，包含 `content`、`role`（受限枚举）、`timestamp`、`metadata`，并提供 `to_dict()` 输出 OpenAI 兼容消息字典。
- **FR-002**: 系统 MUST 提供 `Config` 模型，包含 LLM 默认值、系统调试/日志项、历史长度上限等分组字段，并提供 `from_env()` 与字典序列化能力。
- **FR-003**: 系统 MUST 提供抽象基类 `Agent`，构造函数接收 `name`、`HelloAgentsLLM` 实例、可选 `system_prompt` 与 `Config`，并维护 `Message` 历史。
- **FR-004**: `Agent` MUST 将 `run(input_text, **kwargs)` 声明为抽象方法，强制子类实现。
- **FR-005**: `Agent` MUST 提供 `add_message`、`clear_history`、`get_history`（返回副本）及可读的 `__str__`（至少包含 `name` 与 `llm.provider`）。
- **FR-006**: 公共导出 MUST 可通过 `core.hello_agents` 包一次性导入 `Message`、`Config`、`Agent` 与 `HelloAgentsLLM`（后者来自现有 `llm_client`）。

### Assumptions

- 使用 Pydantic v2（与本仓库 `pydantic>=2` 一致）；序列化使用 `model_dump()` 等 v2 API。
- 不强制在本特性内迁移现有 `ReActAgent` 等至新基类，仅提供可复用基础层。

### Key Entities

- **Message**: 单条对话单元；对外 `to_dict` 与对内 `metadata`/`timestamp` 分离。
- **Config**: 框架级可调参数快照。
- **Agent（抽象）**: 绑定 LLM 与配置、承载历史的执行单元模板。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 新开发者可在 5 分钟内根据文档从 `core.hello_agents` 导入四类符号并完成一条 `Message.to_dict()` 用例。
- **SC-002**: `Config.from_env()` 在设置/取消 `DEBUG` 与 `TEMPERATURE` 时行为可重复验证，无未捕获解析异常。
- **SC-003**: 抽象 `Agent` 不可实例化，具体子类实现 `run` 后可通过单元级脚本或交互验证历史 API（至少 3 次 `add_message` + `get_history` 长度一致）。
