# Implementation Plan: Telegram 即时消息入站通道

**Branch**: `005-telegram-im` | **Date**: 2026-03-22 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/005-telegram-im/spec.md`

## Summary

在个人助理运行时增加 **Telegram Bot** 作为入站通道：用户向机器人发送文本，系统调用既有 `LoopDriver` + `ToolRegistry` 生成回复并写回 Telegram。凭证通过环境变量名引用（不写明文）；安全上复用 `InboundGate` / `PairingStore`（`channel="telegram"`）。首期采用 **长轮询（polling）** 接收更新，降低公网 HTTPS/Webhook 部署依赖；配对通过 **CLI `pair`** 管理。

**进度与流式（对齐 spec FR-008 / FR-009 / FR-010）**：与 OpenClaw 对齐的 **trace** 经 `new_trace(on_step=…)`、`LoopDriver.run(on_trace_step=…)` 推送；**模型侧**在 `ReActAgent` 内对每步使用 `HelloAgentsLLM.stream_invoke`（经 `LoopDriver.run(on_llm_stream=…)` 透出），由 `telegram_runner` 将 **轨迹行 + 当前 ReAct 步的累积模型输出** 合并进**同一条进度消息**的 `edit_text`，并对高频 `delta` 做节流（`step_start` / `end` 强制刷新）。最终可见回答仍单独 `reply`。网关缓冲 SSE 时可能呈块状到达；可选环境变量 `HELLOAGENTS_STREAM_SMOOTH_MS` 见 `llm_client` 与 quickstart。

**线程（thread）承载思考（FR-010，T015）**：首条进度仍 `reply` 用户消息并 `edit_text`；**终稿**改为 **`reply` 进度消息**（`status_msg.reply_text`），在私聊/群内形成「用户 → 进度 → 终稿」回复链。**论坛超级群**对出站 `reply_text` 附加入站消息的 **`message_thread_id`**，保证进度与终稿落在同一话题。错误兜底在进度 `edit` 失败时亦对 `status_msg` 回复。

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
**工作目录 / 工作区**：操作者常在**用户主目录 `~`**（终端默认 cwd）或**仓库根**下启动 `python main.py …`；`logging.path`、`security.pairing_store_path` 等**相对路径**均相对该次 cwd。**若 cwd 为 `~`**，示例相对路径会落在 `~/logs/`、`~/.local/` 等，而非克隆目录内。Quickstart **推荐**先 `cd` 到仓库根再启动，使示例与 `.gitignore` 一致；或在家目录 cwd 下对 YAML 使用**绝对路径**指向期望目录。

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
│       ├── logging_config.py      # 控制台 level + 可选文件；文件仅 ERROR+
│       └── telegram_runner.py     # Bot、进度消息合并编辑（trace + 流式累积）；异常单条反馈
├── main.py                        # 子命令 telegram / pair
requirements.txt                 # python-telegram-bot
assistant.yaml                     # 示例 telegram / logging 段（含 logs/ 路径说明）
.gitignore                         # logs/ 不入库
tests/
└── (按需) test_telegram_runner.py 或集成测试占位
```

**Structure Decision**: 单项目，IM 适配放在 `core/runtime`，与 `daemon`、`mcp_bridge` 同级；CLI 统一由 `main.py` 暴露。

## 日志与 IM 错误呈现（实现同步）

与 IM 相关的运行日志与排障约定（仓库当前实现）：

| 项 | 说明 |
|----|------|
| **文件日志路径** | `assistant.yaml` 的 `logging.path`（示例 `logs/hello-agent.log`）；**相对进程启动时的当前工作目录**，与 `security.pairing_store_path` 一致。常见 cwd 为**用户主目录 `~`** 或**仓库根**：前者下相对路径落在 `~/...`；**推荐**在仓库根执行 `telegram run`，或配置**绝对路径**（如 `~/.hello-agent/logs/hello-agent.log` 展开后的形式）固定位置。 |
| **目录与 Git** | 仓库根 `.gitignore` 包含 `logs/`，日志内容**不上报**远程。 |
| **文件日志级别** | `core/runtime/logging_config.py`：`RotatingFileHandler` 固定 **`logging.ERROR`**，仅 ERROR/CRITICAL（含异常栈）写入文件；**控制台**仍用配置中的 `logging.level`（如 INFO）。父目录不存在时自动 `mkdir`。 |
| **IM 未捕获异常** | `telegram_runner`：`LoopDriver.run` 抛错时 **优先** `edit_text` 更新**同一条进度消息**为 `❌ 内部错误…`；仅当编辑失败时再 `reply` 一条同语义纯文本，**避免双发重复**。用户提示中的「详情已写入日志」在启用 `logging.path` 且为 ERROR 时指向上述文件中的栈记录。 |

## Complexity Tracking

> 无 Constitution 违规需论证；本表留空。

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
