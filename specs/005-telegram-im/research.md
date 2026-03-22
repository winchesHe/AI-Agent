# Research: Telegram 入站通道

## 决策 1：Python Bot SDK

- **Decision**: 采用 **`python-telegram-bot` 21.x**（`telegram.ext.Application`，异步 `run_polling`）。
- **Rationale**: 与仓库 Python/asyncio 栈一致；社区成熟；文档完善；便于 `post_shutdown` 挂钩清理 MCP。
- **Alternatives considered**:
  - *Aiogram 3*：纯 asyncio，亦可行；团队若已熟悉 PTB 则维持 PTB 降低认知成本。
  - *直接调用 Bot HTTP API*：无 SDK 维护成本但易错，首期不采纳。

## 决策 2：Polling 与 Webhook

- **Decision**: **首期仅实现 long polling**；Webhook 作为后续增强（需公网 URL + TLS）。
- **Rationale**: 本地开发与内网部署零依赖；符合 spec P3「最短上线路径」。
- **Alternatives considered**:
  - *Webhook-only*：部署门槛高，不适合默认 quickstart。

## 决策 3：与 Agent 执行线程模型

- **Decision**: 在 asyncio 的 Telegram `MessageHandler` 内使用 **`asyncio.to_thread`（或 `run_in_executor`）** 调用同步的 `LoopDriver.run`，避免阻塞 PTB 事件循环。
- **Rationale**: `ReActAgent` / LLM 当前为同步 API；小步集成不强制全链路 async 重写。
- **Alternatives considered**：
  - *整链改为 async LLM*：工作量大，超出本期 IM 接入范围。

## 决策 4：配对管理界面

- **Decision**：CLI 子命令 **`pair`**（`add` / `remove` / `list`），读写既有 `PairingStore` JSON。
- **Rationale**：满足 spec FR-006；无需额外 HTTP 管理面；与现有安全模型一致。
