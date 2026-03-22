# Quickstart: 本地常驻个人助理（对齐修订 spec）

**目标**：约 **60 分钟内**完成 foreground 启动 + **4 类冒烟**（纯推理、单工具、多步工具、多轮对话）；可选启动 **daemon** 与 **plugins list** 验证（对齐 SC-001、SC-003）。

## 1. 环境

- Python 3.10+
- 模型 API 可达（或本地 OpenAI 兼容）

## 2. 安装

```bash
cd /path/to/Hello-Agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# 实现若将 mcp 列为可选依赖：pip install mcp 或见 pyproject/文档
```

## 3. 配置

复制并编辑（路径以实现为准）：

- `.env`：LLM 密钥与模型
- `assistant.yaml`（或实现选定的文件名）：`loop`、`plugins`、`mcp`、`daemon`、`security`（见 [data-model.md](./data-model.md)）

## 4. Foreground 冒烟（SC-001）

```bash
cd src
python main.py doctor
python main.py task -m "仅推理：解释何为 Agent Loop。"
python main.py task -m "调用搜索：OpenClaw 项目的定位一句话。"
python main.py task -m "多步：先查再总结。"
python main.py chat
```

期望：轨迹中含对应 `kind`（见 [contracts/trace-event.schema.json](./contracts/trace-event.schema.json)）。

## 5. 插件四类参考（SC-003）

```bash
python main.py plugins list
# 启用 src/plugins/ 下示例后再次 list，确认 id 齐全
```

- Tool / Skill / SubAgent：manifest 见 [contracts/plugin-manifest.schema.json](./contracts/plugin-manifest.schema.json)
- MCP：在配置 `mcp.servers` 后执行 `python main.py doctor --probe-mcp`（若实现）

## 6. 常驻（SC-004 手工/长测）

```bash
python main.py daemon
# 另终端
python main.py health --json
```

72 小时与 99% 探针：**在 CI 外**按运维文档执行；可分段累计须在文档声明。

## 7. 监督重启（示例）

- macOS：`deploy/launchd/hello-agent.plist`（若添加）
- Linux：`deploy/systemd/hello-agent.service`（若添加）

## 8. 验收勾选

- [ ] doctor 区分配置 / 网络 / 插件错误（SC-007 子集）
- [ ] 未配对入站不触发敏感工具（US5）
- [ ] 日志与轨迹轮转配置生效（边缘案例）
