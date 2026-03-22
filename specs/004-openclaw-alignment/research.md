# Research: 004-openclaw-alignment（修订版）

**Spec**: [spec.md](./spec.md) | **Date**: 2026-03-22

## R1 — Agent Loop 实现策略

**Decision**: 以 **`LoopDriver` 适配层**包装现有 `ReActAgent`（或 `FunctionCallAgent`）作为 **v1 驱动**；对外统一暴露：`run_turn(user_input) -> StepOutcome`、全局 `max_iterations` / `max_wall_seconds`、以及向 `Trace` 追加步骤。后续可替换为 LangGraph 等驱动而不改插件接口。

**Rationale**: 复用已验证的 Thought/Action 解析与 `ToolRegistry`，缩短 M1 周期。

**Alternatives considered**: 直接上 LangGraph 作为唯一驱动 —— 迁移成本高，且与当前教材式代码耦合重。

## R2 — 插件发现与装载

**Decision**: 采用 **声明式 manifest**（JSON 或 YAML，见 `contracts/plugin-manifest.schema.json`）+ **Python 入口点**（`entry_point` 模块路径）装载 Tool / Skill / SubAgent；manifest 含 `id`、`version`、`permissions`、`requires`。冲突策略：**显式优先级字段**，否则按路径字典序并报 warning。

**Rationale**: 满足 FR-005、FR-009；便于非程序员编辑启用列表。

**Alternatives considered**: 仅用 setuptools entry_points —— 对「热路径下 drop-in 文件夹」不友好。

## R3 — MCP 接入（Python）

**Decision**: 使用 **Python 官方/社区维护的 MCP 客户端**（PyPI `mcp` 包，stdio 传输优先）将远端工具列表缓存为内存 `Tool` 适配器；**TTL + 手动失效**（配置项 `mcp.tools_list_ttl_seconds`）；连接失败映射为轨迹 `error` 且 `error_class=transport`，业务错误映射为 `error_class=business`。

**Rationale**: 对齐 FR-007 与 SC-003；stdio 最贴合本地子进程助手场景。

**Alternatives considered**: 手写 JSON-RPC —— 易与协议漂移；HTTP SSE 作为二期。

## R4 — SubAgent 隔离与防循环

**Decision**: SubAgent 运行在**同一进程**内独立 `LoopDriver` 实例，**工具白名单**为 manifest 子集；**`max_delegation_depth` 默认 2**、**子 Run 独立预算**（迭代数上限为父的 1/2 向下取整）；禁止子代理默认调用 `delegate` 类元工具除非 manifest 声明。

**Rationale**: 单进程 MVP 满足规格；限深防止栈溢出与无限递归。

**Alternatives considered**: 子进程隔离 —— IPC 与调试成本显著增高，留作后续 hardening。

## R5 — 7×24 常驻与恢复

**Decision**: **两层**：(1) `python main.py daemon` 内 **asyncio** 长活循环 + 周期性健康自检；(2) 文档提供 **launchd**（macOS）与 **systemd --user**（Linux）单元样例，**Restart=always** + `StartLimitIntervalSec`。退避：对外部 API 使用 **指数退避 + jitter**，最大间隔与总尝试次数配置化（FR-011）。

**Rationale**: 满足 SC-004/005；不强制用户购买商业 supervisor。

**Alternatives considered**: 仅依赖外部 supervisor 无内建 daemon —— 不符合「产品化常驻」叙事。

## R6 — 健康检查与自检

**Decision**: `doctor` 输出 **JSON 或表格**：Python 版本、配置 schema 版本、已加载插件 id、MCP 端点 reachability（可选 `--probe-mcp`）、最近错误摘要。常驻模式额外暴露 **`main.py health`** 或 HTTP localhost（若引入则写入 plan 增补，**默认优先纯 CLI JSON** 以降低攻击面）。

**Rationale**: 对齐 FR-010、FR-014、SC-007。

## R7 — 日志与轨迹磁盘

**Decision**: 使用标准 `logging` + **RotatingFileHandler**（可配置 `max_bytes` / `backup_count`）；轨迹文件与日志分离，同样可轮转（FR 边缘案例）。

**Rationale**: 满足 spec 边缘案例「7×24 磁盘占满」。
