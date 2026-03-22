# 插件系统（Plugin System）

本目录存放 Hello-Agent 的**本地插件**。每个插件以独立子目录形式存在，包含一个 `manifest.json` 和对应的 Python 入口模块。

> **MCP 服务不放在此目录**——见下方 [MCP 说明](#mcp-说明)。

---

## 目录结构

```text
src/plugins/
├── README.md                  # 本文件
├── example_tool/              # 参考 Tool 插件（待添加）
│   ├── manifest.json
│   └── tool.py
├── example_skill/             # 参考 Skill 插件（待添加）
│   ├── manifest.json
│   └── skill.py
└── example_subagent/          # 参考 SubAgent 插件（待添加）
    ├── manifest.json
    └── agent.py
```

每个子目录**必须包含** `manifest.json`，否则插件宿主将跳过该目录。

---

## Manifest 格式

完整 JSON Schema：[`specs/004-openclaw-alignment/contracts/plugin-manifest.schema.json`](../../specs/004-openclaw-alignment/contracts/plugin-manifest.schema.json)

### 必填字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 全局唯一标识，仅允许 `a-z 0-9 . _ -`，不能以符号开头 |
| `version` | string | 语义版本号，如 `"0.1.0"` |
| `kind` | enum | 插件类型：`tool` / `skill` / `subagent` |

### 可选字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `entry_point` | string | 入口函数，格式为 `module:callable`（见下方约定） |
| `permissions` | string[] | 权限声明列表（见下方权限等级） |
| `requires` | string[] | 依赖的其它插件 id |
| `priority` | integer | 加载优先级（数值越小越先加载） |
| `metadata` | object | 自由扩展，如 `name`、`author`、`homepage` |

### 示例

```json
{
  "id": "example-tool",
  "version": "0.1.0",
  "kind": "tool",
  "entry_point": "tool:register",
  "permissions": ["read_only"],
  "metadata": {
    "name": "示例工具",
    "author": "Hello-Agent Team"
  }
}
```

---

## 入口约定（Entry Point）

`entry_point` 采用 `module:callable` 格式：

- **module**：相对于插件目录的 Python 模块名（不带 `.py` 后缀）。
- **callable**：模块内的工厂函数或注册函数名。

```text
entry_point: "tool:register"
```

插件宿主加载时等价于：

```python
from plugins.example_tool.tool import register
register(host)  # host 为插件宿主提供的注册上下文
```

---

## 权限等级（Permissions）

插件通过 `permissions` 声明所需权限，运行时据此做能力管控：

| 权限 | 说明 |
|------|------|
| `read_only` | 只读操作，不产生副作用 |
| `network` | 需要网络访问（HTTP 调用、API 请求等） |
| `mutating` | 会修改本地状态或外部资源 |
| `delegate` | 可委派子 Agent（仅 `subagent` 类型使用） |

- 未声明 `permissions` 的插件默认无任何特权。
- 配置中的 `security.sensitive_plugin_ids` 可对特定插件施加额外入站策略限制。

---

## 参考插件

以下三个参考插件将在后续任务中添加：

| 目录 | Kind | 任务编号 | 说明 |
|------|------|----------|------|
| `example_tool/` | `tool` | T014 | 注册一个原子工具 |
| `example_skill/` | `skill` | T015 | 注入系统提示 + 工具白名单 |
| `example_subagent/` | `subagent` | T017 | 委派子 Agent，受限深/限时/限轮次 |

---

## 启用 / 禁用插件

在 `assistant.yaml`（或项目使用的配置文件）中管理插件：

```yaml
plugins:
  search_paths:
    - src/plugins          # 插件搜索目录
  enabled_ids:
    - example-tool         # 仅列出的 id 会被加载
    - example-skill
  priority_overrides:
    example-tool: 10       # 可选：覆盖 manifest 中的优先级
```

- **`search_paths`**：插件宿主在这些路径下扫描含 `manifest.json` 的子目录。
- **`enabled_ids`**：白名单模式，只有列出的插件 id 才会激活。移除 id 即可禁用。
- **`priority_overrides`**：按需覆盖 manifest 中的 `priority` 值。

验证命令：

```bash
cd src
python main.py plugins list
```

---

## MCP 说明

MCP（Model Context Protocol）服务**不作为插件目录**管理，而是在 `assistant.yaml` 顶层 `mcp.servers` 中配置：

```yaml
mcp:
  servers:
    - name: example-mcp
      transport: stdio
      command: python
      args: ["-m", "mcp.server.example"]
      env:
        SOME_VAR: value
      tools_list_ttl_seconds: 300
```

MCP 工具由 `mcp_bridge` 桥接为统一 Tool 视图（名称前缀 `mcp__server__tool`），与本地插件共享权限校验和超时管理。

**本地测试**：如无远程 MCP 服务，可使用官方 MCP Python SDK 提供的示例服务器在本地测试：

```bash
pip install mcp
python -m mcp.server.example   # 启动示例 stdio 服务器
```

配置后可通过 `python main.py doctor --probe-mcp` 验证连通性。
