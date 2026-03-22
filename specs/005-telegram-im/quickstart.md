# Quickstart：Telegram 接入

## 1. 创建机器人

1. 在 Telegram 中联系 [@BotFather](https://t.me/BotFather)，创建机器人并复制 **HTTP API Token**。

## 2. 环境变量

```bash
export TELEGRAM_BOT_TOKEN="你的 token"
# 已有 LLM 变量，例如：
export LLM_API_KEY="..."
```

若使用自定义变量名，在 `assistant.yaml` 的 `telegram.bot_token_ref` 中填写该变量名。

## 3. 配置文件

在 `assistant.yaml` 中增加（示例）：

```yaml
telegram:
  enabled: true
  bot_token_ref: 'TELEGRAM_BOT_TOKEN'

security:
  pairing_store_path: '.local/pairing.json'
  inbound_default_policy: 'deny'
  sensitive_plugin_ids: []   # 填入插件 id 则未配对用户无法触发
```

## 4. 登记配对

向机器人发一条消息后，从日志或 [@userinfobot](https://t.me/userinfobot) 获取你的数字 ID，然后执行：

```bash
cd src
python main.py pair add --channel telegram --sender-id <你的用户ID>
```

## 5. 启动通道

```bash
cd src
python main.py telegram run
```

在 Telegram 客户端向机器人发送文本，应收到助理回复。

多步任务时，机器人会先回复一条 **运行进度** 消息（随推理与工具执行**多次编辑**）。进度内包含 **OpenAI 兼容接口的 token 流式输出**（每步 ReAct 调用 `stream=True`），再在**下一条消息**中给出最终可见回答。若网关缓冲 SSE，可能仍呈块状到达；可设环境变量 `HELLOAGENTS_STREAM_SMOOTH_MS` 做客户端侧拆字（见 `llm_client` 文档）。

**流式友好环境（便于验收 SC-006）**：直连延迟较低的 Chat Completions 兼容端点；避免经过会整段缓冲 SSE 的企业代理。若只能块状到达，在验收记录中注明「网关缓冲」，仍可与 spec FR-009 的 MAY 降级一致。

## 6. US4 手工验收（SC-005 / SC-006）

在配对已完成、`telegram run` 正常的前提下：

1. **SC-005（多步轨迹）**：发送一条会触发 **≥2 条**有意义 trace 步骤的任务（例如需调用工具的多步问题）。在最终回答所在消息出现前，进度消息应被编辑 **至少 1 次**（通常多次），且内容能反映步骤推进。
2. **SC-006（单轮 + 流式）**：发送一条**无需工具**、单轮即可答完的简短推理题（流式友好网络）。在最终回答出现前，进度区应出现 **≥2 次**可区分的内容变化（含首次占位、轨迹行更新与/或「第 N 步 · 模型输出」文本变长；块状到达计为有效）。

## 7. 排障

- **未收到回复**：检查 token、网络、LLM 配额；查看控制台日志。
- **提示无权限**：检查 `sensitive_plugin_ids` 与配对状态；执行 `pair list`。
- **进度不「流」、很久才变一次**：多为 API/网关缓冲或非流式端点；见上文 `HELLOAGENTS_STREAM_SMOOTH_MS` 与 FR-009 说明。
