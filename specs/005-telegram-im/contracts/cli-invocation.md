# CLI 契约：Telegram 与配对

## `telegram run`

- **用途**：启动 Telegram 长轮询，接收文本消息并调用助理回复。
- **前置**：
  - 配置文件存在且 LLM 校验通过（与既有 `task` 一致）。
  - `telegram.enabled` 为 `true`（若配置块存在且要求显式启用）。
  - 环境变量 `telegram.bot_token_ref` 所指变量已设置且非空。
- **退出**：`SIGINT` / `SIGTERM` 优雅停止；若启用 MCP，应在进程退出路径上关闭连接。

## `pair add`

```text
pair add --channel <str> --sender-id <str> [--trust full|limited]
```

- **用途**：写入配对库。Telegram 场景下 `--channel telegram`，`--sender-id` 为用户数字 ID。

## `pair remove`

```text
pair remove --channel <str> --sender-id <str>
```

## `pair list`

- **用途**：列出当前配对库中的记录（需配置 `security.pairing_store_path` 且文件可读）。

## 错误与退出码

- 与 `main.py` 既有约定对齐：配置错误 → `EXIT_CONFIG`；可选地，缺失依赖（未安装 `python-telegram-bot`）→ `EXIT_EXTERNAL_DEP` 或明确错误信息。
