# Data Model: 004-openclaw-alignment（修订版）

**Spec**: [spec.md](./spec.md) | **Date**: 2026-03-22

## 1. ConfigurationProfile

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `schema_version` | string | 是 | 配置格式版本 |
| `llm` | object | 是 | provider、model、api_key_ref、base_url、timeout |
| `loop` | object | 是 | `max_iterations`、`max_wall_seconds`、多轮 `max_history_messages` |
| `plugins` | object | 是 | `search_paths[]`、`enabled_ids[]`、`priority_overrides` |
| `mcp` | object | 否 | `servers[]`：`name`、`transport`、`command`、`args`、`env`、`tools_list_ttl_seconds` |
| `daemon` | object | 否 | `probe_interval_seconds`、`shutdown_grace_seconds`、`retry` 退避参数 |
| `security` | object | 是 | `inbound_default_policy`、`sensitive_plugin_ids[]`、`pairing_store_path` |
| `logging` | object | 否 | 级别、路径、轮转参数 |
| `limits` | object | 否 | 常驻内存软上限告警阈值（文档声明interpretation） |

## 2. PluginPackage（manifest + 代码入口）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 全局唯一 |
| `version` | semver string | |
| `kind` | enum | `tool` \| `skill` \| `subagent` \| `mcp_client_config`（后者或并入顶层 mcp） |
| `entry_point` | string | `module:callable` 或约定工厂名 |
| `permissions` | list | `read_only` / `network` / `mutating` / `delegate` |
| `requires` | list[string] | 可选依赖插件 id |
| `metadata` | object | 人类可读名、作者、来源 URL |

## 3. Tool（统一调用视图）

| 字段 | 说明 |
|------|------|
| `name` | 对外暴露名（含 MCP 前缀如 `mcp__server__tool`） |
| `description` | |
| `json_schema` | 参数 schema |
| `source` | `builtin` \| `plugin` \| `mcp` |
| `plugin_id` | 可空 |
| `timeout_seconds` | |
| `risk_tier` | 与权限校验挂钩 |

## 4. Skill

| 字段 | 说明 |
|------|------|
| `id` | |
| `intent_description` | 匹配说明（含关键词或示例句，实现可简化为前缀规则 v1） |
| `system_prompt_addendum` | 注入片段 |
| `tool_allowlist` | name 列表 |

## 5. SubAgentDefinition

| 字段 | 说明 |
|------|------|
| `id` | |
| `tool_allowlist` | 严格子集 |
| `max_iterations` | 子 Run 上限 |
| `can_delegate` | bool，默认 false |

## 6. Run（Agent Loop 运行实例）

| 字段 | 说明 |
|------|------|
| `run_id` | uuid |
| `parent_run_id` | 可空（SubAgent） |
| `depth` | int |
| `iteration` | 当前计数 |
| `budget_remaining` | 迭代/时间 |

## 7. TraceStep（逻辑）

与 [contracts/trace-event.schema.json](./contracts/trace-event.schema.json) 对齐；`payload` 可含 `tool_name`、`error_class`、`mcp_server`、`subagent_id` 等。

## 8. InboundSource & PairingRecord

同前版 spec：`channel` + `sender_id` 复合键；`paired_at`、`trust_level`。

## 9. HealthSnapshot

| 字段 | 说明 |
|------|------|
| `status` | `ok` \| `degraded` \| `unhealthy` |
| `checks` | map: 名 → `{ ok, detail }` |
| `uptime_seconds` | |
| `loaded_plugins` | id 列表 |

## 10. 校验规则

- `enabled_plugins` 解析失败 → 拒绝启动，单一错误源。
- MCP server 名冲突 → 拒绝启动。
- SubAgent `tool_allowlist` 含未加载工具 → 拒绝加载该 SubAgent。
- `sensitive_plugin_ids` 与入站策略组合：未配对来源不得调度这些工具（US5）。
