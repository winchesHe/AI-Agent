# Tasks: 003-tool-system

## Phase 1: Setup

- [x] T001 在 `requirements.txt` 增加 `tavily-python` 依赖

## Phase 2: Foundational（工具抽象与注册表）

- [x] T002 [US1] 新增 `ToolParameter` 与扩展 `BaseTool`（`get_parameters`、`to_openai_schema`）于 `src/core/hello_agents/tools/tool_parameter.py`、`src/core/hello_agents/tools/base_tool.py`
- [x] T003 [US1] 实现 `CallableStringTool` 于 `src/core/hello_agents/tools/function_tool.py`
- [x] T004 [US1] 增强 `ToolRegistry`（`register_function`、字符串入参映射、`openai_tools_payload`）于 `src/core/hello_agents/tool_registry.py`
- [x] T005 [US1] 更新 `CalculatorTool.get_parameters` 于 `src/core/hello_agents/tools/calculator.py`

## Phase 3: User Story 2 — 多源搜索

- [x] T006 [US2] 实现 `SearchTool` 于 `src/core/hello_agents/tools/search_tool.py`

## Phase 4: User Story 3 — 工具链与异步

- [x] T007 [US3] 实现 `ToolChain` / `ToolChainManager` 于 `src/core/hello_agents/tool_chain.py`
- [x] T008 [US3] 实现 `AsyncToolExecutor` 于 `src/core/hello_agents/async_tool_executor.py`

## Phase 5: 导出与示例

- [x] T009 更新 `src/core/hello_agents/__init__.py`、`src/core/hello_agents/tools/__init__.py`、`src/hello_agents/__init__.py`、`src/hello_agents/tools/__init__.py` 导出
- [x] T010 [P] [US1] 添加 `examples/7.5-tool-system/my_calculator_tool.py` 与 `test_my_calculator.py`
- [x] T011 [P] [US2] 添加 `examples/7.5-tool-system/my_advanced_search.py` 与 `test_advanced_search.py`
- [x] T012 [P] [US3] 添加 `examples/7.5-tool-system/tool_chain_manager.py` 与 `test_async_tools.py`
- [x] T013 [P] 添加 `examples/7.5-tool-system/path_setup.py`

## Phase 6: 文档（Spec Kit）

- [x] T014 填写 `specs/003-tool-system/spec.md`、`plan.md`、`tasks.md`、`research.md`、`quickstart.md`、`checklists/requirements.md`

## Dependencies

US1 → US2 / US3（注册表与基类为先）；US2 与 US3 可并行于核心导出之后。

## Implementation Strategy

先完成注册表与参数 schema，再 SearchTool，再链式/异步，最后示例与 Spec 文档。
