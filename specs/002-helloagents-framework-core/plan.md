# Implementation Plan: HelloAgents 框架核心接口（002）

**Branch**: `002-helloagents-framework-core`  
**Spec**: [spec.md](./spec.md)

## Scope

新增包 `src/core/hello_agents/`，与现有 `src/core/agent/`（具体智能体）并列，避免命名冲突。

## Files

| 文件 | 职责 |
|------|------|
| `src/core/hello_agents/message.py` | `MessageRole`, `Message`, `to_dict()` |
| `src/core/hello_agents/config.py` | `Config`, `from_env()`, `to_dict()` → `model_dump()` |
| `src/core/hello_agents/agent.py` | 抽象 `Agent`，历史与 `HelloAgentsLLM` 依赖 |
| `src/core/hello_agents/__init__.py` | 导出 API |

## Integration

- `HelloAgentsLLM` 继续定义于 `src/core/llm/llm_client.py`；`agent.py` 使用 `from core.llm.llm_client import HelloAgentsLLM`。
- 环境变量：`LLM_MODEL_ID`、`LLM_DEFAULT_PROVIDER`、`HELLOAGENTS_*` 等与 001 LLM Hub 约定对齐。

## Non-goals

- 不修改现有 `ReActAgent` / LangGraph 节点以继承新 `Agent`（可后续迭代）。
- 不在本计划内引入新第三方依赖。
