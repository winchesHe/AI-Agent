# Tasks: HelloAgents 框架核心接口（002）

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md)

## Phase 1: Implementation

- [x] T001 [P] 新增 `src/core/hello_agents/message.py`（`Message`、`MessageRole`、`to_dict`、Pydantic v2）
- [x] T002 [P] 新增 `src/core/hello_agents/config.py`（`Config`、`from_env`、`to_dict`）
- [x] T003 新增 `src/core/hello_agents/agent.py`（抽象 `Agent`、历史 API、`HelloAgentsLLM` 类型依赖）
- [x] T004 新增 `src/core/hello_agents/__init__.py`（导出 `Message`、`MessageRole`、`Config`、`Agent`、`HelloAgentsLLM`）

## Phase 2: Verification

- [x] T005 `PYTHONPATH=src` 下导入 `core.hello_agents` 并断言 `Message.to_dict()` 与抽象 `Agent` 不可实例化

## Phase 3: 7.4 Agent 范式框架化

- [x] T006 `HelloAgentsLLM.invoke` / `stream_invoke`（`src/core/llm/llm_client.py`）
- [x] T007 [P] 工具层：`tool_registry.py`、`tools/base_tool.py`、`tools/calculator.py`
- [x] T008 [P] `SimpleAgent`、`ReActAgent`、`ReflectionAgent`、`PlanAndSolveAgent`、`FunctionCallAgent`（`src/core/hello_agents/`）
- [x] T009 `src/hello_agents/` 兼容包名与 `src/hello_agents/tools/`
- [x] T010 教材示例脚本（`examples/7.4-agent-paradigms/`）

## Dependencies

- T001–T002 可并行；T003 依赖 T001、T002 的类型存在；T004 最后；T005 依赖 T001–T004。
- Phase 3：T006 为 LLM 能力前置；T007–T008 依赖 T003/T004；T009–T010 依赖 T008。
