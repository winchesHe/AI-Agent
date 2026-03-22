# 个人助理快速上手指南

**目标**：约 **60 分钟内**完成本地 foreground 启动 + **4 类冒烟测试**（纯推理、单工具调用、多步工具链、多轮对话），并可选验证 **插件系统** 与 **常驻守护进程**。

---

## 1. 环境要求

| 依赖 | 最低版本 | 说明 |
|------|---------|------|
| Python | 3.10+ | 推荐 3.12 |
| 模型 API | — | 需可达的 OpenAI 兼容接口（云端或本地） |
| SerpAPI（可选） | — | 搜索工具所需，需要 API Key |

确认 Python 版本：

```bash
python3 --version   # >= 3.10
```

---

## 2. 安装步骤

```bash
cd /path/to/Hello-Agent

# 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

> **提示**：`requirements.txt` 已包含 `mcp>=1.0.0`（MCP 客户端），若不需要 MCP 功能可忽略其安装警告。

---

## 3. 配置

### 3.1 环境变量

从示例文件复制并填入真实值：

```bash
cp .env.example .env
```

编辑 `.env`，填写以下字段：

```dotenv
LLM_API_KEY="your-api-key"
LLM_MODEL_ID="gpt-5.4"
LLM_BASE_URL="https://api.openai.com/v1"

SERPAPI_API_KEY="your-serpapi-key"
```

### 3.2 助理配置文件

如果项目提供了 `assistant.yaml` 示例，复制并按需编辑：

```bash
cp assistant.yaml.example assistant.yaml   # 若存在示例文件
```

配置文件可包含以下部分（详见 spec `data-model.md`）：

- `loop` — Agent Loop 参数（最大轮次、超时等）
- `plugins` — 插件加载配置
- `mcp` — MCP 服务器连接
- `daemon` — 守护进程参数
- `security` — 安全策略

---

## 4. Foreground 冒烟测试

进入 `src` 目录，依次执行以下命令：

### 4.1 环境自检

```bash
cd src
python3 main.py doctor
```

预期：输出配置状态、网络连通性、插件加载情况，**无 ERROR 级别报错**。

### 4.2 纯推理任务

```bash
python3 main.py task -m "仅推理：解释何为 Agent Loop。"
```

预期：模型直接返回文本回答，轨迹中不含工具调用。

### 4.3 单工具调用任务

```bash
python3 main.py task -m "调用搜索：OpenClaw 项目的定位一句话。" --trace human
```

预期：轨迹显示一次搜索工具调用 + 模型总结，`--trace human` 以可读格式输出执行轨迹。

### 4.4 多步工具链任务

```bash
python3 main.py task -m "多步：先查再总结。" --trace json
```

预期：轨迹包含多次工具调用（搜索 → 整理 → 总结），`--trace json` 以 JSON 格式输出完整事件序列。

### 4.5 多轮对话

```bash
python3 main.py chat
```

预期：进入交互式对话模式，支持上下文多轮对话。输入 `exit` 或 `Ctrl+C` 退出。

---

## 5. 插件验证

```bash
python3 main.py plugins list
```

预期：列出所有已注册插件的 `id`、类型（Tool / Skill / SubAgent / MCP）及状态。

如需测试新插件，将插件文件放入 `src/plugins/` 目录后重新执行 `plugins list`，确认新插件 ID 出现在列表中。

---

## 6. 常驻模式

### 6.1 启动守护进程

```bash
python3 main.py daemon
```

进程将在前台以 daemon 模式运行（可配合 `nohup` 或系统服务管理器放入后台）。

### 6.2 健康检查

在另一个终端执行：

```bash
python3 main.py health --json
```

预期：返回 JSON 格式的健康状态，包含运行时长、内存占用、插件状态等信息。

---

## 7. 监督重启

项目提供 macOS（launchd）和 Linux（systemd）的守护进程配置示例，详见 [`docs/daemon/README.md`](daemon/README.md)。

| 平台 | 配置文件 | 管理命令 |
|------|---------|---------|
| macOS | `docs/daemon/hello-agent.plist` | `launchctl load/unload` |
| Linux | `docs/daemon/hello-agent.service` | `systemctl --user enable/start/stop` |

快速示例（macOS）：

```bash
cp docs/daemon/hello-agent.plist ~/Library/LaunchAgents/com.hello-agent.daemon.plist
# 编辑 plist，将 WorkingDirectory 改为实际路径
launchctl load ~/Library/LaunchAgents/com.hello-agent.daemon.plist
launchctl list | grep hello-agent
```

---

## 8. 验收勾选清单

完成以上步骤后，逐项确认：

- [ ] `doctor` 正常运行，能区分配置错误 / 网络错误 / 插件错误
- [ ] 纯推理任务返回合理文本，无工具调用
- [ ] 单工具任务轨迹包含搜索调用（`--trace human` 可读输出）
- [ ] 多步任务轨迹包含多次工具调用（`--trace json` 结构化输出）
- [ ] `chat` 模式可正常多轮对话并退出
- [ ] `plugins list` 列出所有已注册插件
- [ ] `daemon` 启动后 `health --json` 返回正常状态
- [ ] 日志与轨迹轮转配置生效
- [ ] 未配对入站请求不触发敏感工具调用
