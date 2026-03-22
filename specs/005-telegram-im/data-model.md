# Data Model: Telegram 入站通道

## 配置（YAML → `ConfigurationProfile`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `telegram` | 对象，可选 | 整块缺省表示不启用 CLI 中的 telegram 模式配置校验提示 |
| `telegram.enabled` | 布尔 | `true` 时 `telegram run` 要求 token 环境变量存在 |
| `telegram.bot_token_ref` | 字符串 | 环境变量**名称**，值为 Bot Token（默认 `TELEGRAM_BOT_TOKEN`） |

说明：`ConfigurationProfile` 顶层增加可选 `telegram: TelegramConfig | None`，与 `security`、`loop` 等并列。

## 入站来源（已有模型）

复用 `InboundSource`：

- `channel`: 固定 `"telegram"`
- `sender_id`: Telegram 用户数字 ID 的十进制字符串（`str(update.effective_user.id)`）

## 配对记录（已有模型）

复用 `PairingRecord`：`channel`、`sender_id`、`paired_at`、`trust_level`。

## 运行时对象（实现层）

| 概念 | 说明 |
|------|------|
| Telegram Application | PTB `Application`，持有 token 与 handler |
| 单次处理上下文 | 当前消息文本、`InboundSource`、已加载的 `LoopDriver` / `ToolRegistry` / `PairingStore` |
