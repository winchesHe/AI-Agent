# Implementation Plan: 003-tool-system

**Branch**: `003-tool-system` | **Date**: 2025-03-22 | **Spec**: [spec.md](./spec.md)

## Summary

在 HelloAgents 核心包中落地教材 7.5：参数自描述（`ToolParameter` + `get_parameters`）、增强的 `ToolRegistry`（函数注册、覆盖提示、统一 OpenAI payload）、内置 `SearchTool`（Tavily/SerpApi/hybrid）、`ToolChain`/`AsyncToolExecutor`，并补充 `examples/7.5-tool-system`。

## Technical Context

**Language/Version**: Python 3.10+（与仓库现有代码一致）  
**Primary Dependencies**: `openai`, `pydantic`, `python-dotenv`, `google-search-results`, `tavily-python`  
**Storage**: N/A  
**Testing**: 可运行示例脚本 + 既有 7.4 示例回归  
**Target Platform**: 本地 / 服务端 Python  
**Project Type**: 库 + 教材示例  
**Performance Goals**: 无特殊 SLA；异步示例用于 I/O 并行  
**Constraints**: 无密钥时搜索需优雅降级；保持 `FunctionCallAgent` 兼容  
**Scale/Scope**: 单仓库内核心模块 + 示例目录  

## Constitution Check

仓库 constitution 仍为占位模板；本特性为教程对齐的框架扩展，不引入新治理项。**GATE**: 通过（无额外违例需记录）。

## Project Structure

### Documentation (this feature)

```text
specs/003-tool-system/
├── plan.md
├── spec.md
├── research.md
├── quickstart.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code

```text
src/core/hello_agents/
├── tool_registry.py
├── tool_chain.py
├── async_tool_executor.py
├── tools/
│   ├── base_tool.py
│   ├── tool_parameter.py
│   ├── function_tool.py
│   ├── search_tool.py
│   └── calculator.py
examples/7.5-tool-system/
├── path_setup.py
├── my_calculator_tool.py
├── test_my_calculator.py
├── my_advanced_search.py
├── test_advanced_search.py
├── tool_chain_manager.py
└── test_async_tools.py
```

**Structure Decision**: 核心能力在 `core/hello_agents`；示例与教材命名对齐放在 `examples/7.5-tool-system`。

## Complexity Tracking

无。
