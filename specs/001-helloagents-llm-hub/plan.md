# Implementation Plan: HelloAgentsLLM 适应性模型调用中枢

**Branch**: `001-helloagents-llm-hub`  
**Spec**: [spec.md](./spec.md)  
**Primary module**: `src/core/llm/llm_client.py` (`HelloAgentsLLM`)

## Technical Context

- **Language**: Python 3  
- **HTTP client**: OpenAI 官方 Python SDK（`OpenAI` 客户端，`base_url` 指向兼容服务端点）  
- **Config**: `python-dotenv`，进程环境变量；与现有 `LLM_MODEL_ID`、`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_TIMEOUT` 保持向后兼容或可迁移路径  
- **Call sites**（需冒烟验证）: `src/main.py`，`src/scripts/run_*.py`，`src/core/agent/**/*.py` 中注入的 `HelloAgentsLLM`

## API Shape (target)

- 构造函数支持：`model`、`api_key` / `apiKey`、`base_url` / `baseUrl`、`provider`（含 `auto`）、`temperature`、`max_tokens`、`timeout` 等与 spec 一致的参数；内部统一为 OpenAI 兼容客户端。  
- 内部方法：`_auto_detect_provider`、`_resolve_credentials`（或等价命名），职责与教材 7.2.3 一致。  
- `think(messages, temperature, stream)` 保持现有语义；必要时将内部 `client` 与对外参数命名对齐（蛇形与现有驼峰可二选一为主并兼容别名）。

## Provider Defaults (reference)

| Provider   | Key env (primary)      | Default base URL hint                          |
| ---------- | ---------------------- | --------------------------------------------- |
| openai     | `OPENAI_API_KEY`       | `https://api.openai.com/v1`                   |
| modelscope | `MODELSCOPE_API_KEY`   | `https://api-inference.modelscope.cn/v1/`   |
| zhipu      | `ZHIPU_API_KEY`        | `open.bigmodel.cn` 路径按官方兼容端点        |
| vllm       | `LLM_API_KEY` 占位即可 | 通常 `http://localhost:8000/v1`               |
| ollama     | 占位即可               | 通常 `http://localhost:11434/v1`              |

## Structure

- 核心逻辑集中在 `src/core/llm/llm_client.py`。  
- 可选：教材示例 `my_llm.py` 放在 `src/examples/` 或 `docs/` 旁，仅作扩展演示，不强制纳入包导出。

## Out of Scope

- 不在本计划内安装或编排 VLLM/Ollama 二进制与 GPU 驱动。  
- 不实现非 OpenAI 兼容的专有协议。
