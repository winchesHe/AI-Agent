# Implementation Plan: Telegram 即时消息入站通道

**Branch**: `005-telegram-im` | **Date**: 2026-03-22 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/005-telegram-im/spec.md`

## Summary

在个人助理运行时增加 **Telegram Bot** 作为入站通道：用户向机器人发送文本，系统调用既有 `LoopDriver` + `ToolRegistry` 生成回复并写回 Telegram。凭证通过环境变量名引用（不写明文）；安全上复用 `InboundGate` / `PairingStore`（`channel="telegram"`）。首期采用 **长轮询（polling）** 接收更新，降低公网 HTTPS/Webhook 部署依赖；配对通过 **CLI `pair`** 管理。

**进度与流式（对齐 spec FR-008 / FR-009）**：与 OpenClaw 对齐的 **trace** 经 `new_trace(on_step=…)`、`LoopDriver.run(on_trace_step=…)` 推送；**模型侧**在 `ReActAgent` 内对每步使用 `HelloAgentsLLM.stream_invoke`（经 `LoopDriver.run(on_llm_stream=…)` 透出），由 `telegram_runner` 将 **轨迹行 + 当前 ReAct 步的累积模型输出** 合并进**同一条进度消息**的 `edit_text`，并对高频 `delta` 做节流（`step_start` / `end` 强制刷新）。最终可见回答仍单独 `reply`。网关缓冲 SSE 时可能呈块状到达；可选环境变量 `HELLOAGENTS_STREAM_SMOOTH_MS` 见 `llm_client` 与 quickstart。

## Technical Context

**Language/Version**: Python 3.10+（与仓库一致）  
**Primary Dependencies**: 既有 `openai` / `pydantic` / `python-dotenv` / `pyyaml`；新增 **`python-telegram-bot`**（v21+，内置 asyncio）  
**Storage**: 复用 `security.pairing_store_path` 的 JSON 配对库；无新数据库  
**Testing**: `pytest`、`ruff check`（与仓库一致）  
**Target Platform**: macOS / Linux 本机或服务器 CLI 常驻进程  
**Project Type**: Python CLI + 常驻 IM 适配层  
**Performance Goals**: 单用户消息在 `loop.max_wall_seconds` 内完成；轮询间隔使用库默认或可配置  
**Constraints**: 不在仓库中存储 Bot Token；敏感插件须在配对后可用（与 004 一致）；Telegram `edit_text` 频率受平台限制，进度更新须节流  
**Scale/Scope**: 单机器人、中小并发；非 Telegram 其他 IM 不在本期范围

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

当前 `.specify/memory/constitution.md` 仍为占位模板，无可执行门禁条款。本特性在既有 `src/core/runtime` 内增量扩展，不引入新顶层应用仓库；**复杂度可接受**，无额外违记录入。

## Project Structure

### Documentation (this feature)

```text
specs/005-telegram-im/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── core/
│   ├── hello_agents/
│   │   └── react_agent.py         # stream_invoke + llm_stream_callback（Telegram 路径启用）
│   └── runtime/
│       ├── config.py              # 增加可选 Telegram 配置块
│       ├── inbound.py             # 可选：配对列表 API
│       ├── loop_driver.py         # on_trace_step / on_llm_stream 透传
│       └── telegram_runner.py     # Bot、进度消息合并编辑（trace + 流式累积）
├── main.py                        # 子命令 telegram / pair
requirements.txt                 # python-telegram-bot
assistant.yaml                     # 示例 telegram 段（注释说明）
tests/
└── (按需) test_telegram_runner.py 或集成测试占位
```

**Structure Decision**: 单项目，IM 适配放在 `core/runtime`，与 `daemon`、`mcp_bridge` 同级；CLI 统一由 `main.py` 暴露。

## Complexity Tracking

> 无 Constitution 违规需论证；本表留空。

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
