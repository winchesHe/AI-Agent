# Implementation Plan: 本地常驻个人助理（Agent Loop + 插件 + 7×24）

**Branch**: `004-openclaw-alignment` | **Date**: 2026-03-22 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/004-openclaw-alignment/spec.md`

## Summary

在现有 Python 智能体代码库上，建设三层能力：**(1) 显式 Agent Loop 内核**（推理—行动—观察、预算与终止、步骤级轨迹、多轮会话状态）；**(2) 插件运行时**（Tool / Skill / MCP 端点 / SubAgent 的统一注册、权限、超时与错误分类，尽量不修改内核即可扩展）；**(3) 常驻运行面**（foreground 与 daemon 双模式、健康检查、退避重试、文档化监督重启与资源边界）。配置、自检、入站安全（配对 + 敏感能力授权）与参考插件样例支撑规格 SC-001–SC-007。

## Technical Context

**Language/Version**: Python 3.10+（与仓库一致）  
**Primary Dependencies**: 既有 `openai`、`pydantic`、`python-dotenv`；Agent Loop 首期复用 `core/hello_agents`（ReAct 等）并**抽象**为可插拔 `LoopDriver`；MCP 侧引入官方 **`mcp`（Python SDK）** 或等价 stdio 客户端（见 [research.md](./research.md)）；常驻可选 **`supervisor` 脚本 + launchd/systemd 单元** 或进程内 `asyncio` 长活循环（见 research）  
**Storage**: 本地文件（YAML/TOML/JSON 配置、配对库、轨迹可选落盘、插件 manifest）；无强制 DB  
**Testing**: `cd src && pytest`；契约测试对齐 `contracts/*.schema.json`；常驻与 72h 测试以**可脚本化探针 + 缩短版 soak** 在 CI 外执行  
**Target Platform**: 单机本地；**macOS / Linux** 首优（守护进程文档覆盖 launchd 与 systemd user）；Windows 以「前台 + 计划任务/用户态监督」最佳努力  
**Project Type**: CLI + 可选后台常驻的个人助理运行时  
**Performance Goals**: 交互任务受模型与外部 API 主导；内核侧工具/MCP 调用须**可配置超时**；常驻模式内存上限在配置中声明并由 `doctor`/metrics 观测  
**Constraints**: 密钥不入库入轨迹；插件默认**能力白名单**；SubAgent **限深/限时/限轮次**；重试须**指数退避 + 上限**  
**Scale/Scope**: 单用户单实例；多通道 IM 全量对接仍 out of scope（仅保留入站抽象）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` 仍为占位模板。本计划采用以下**临时门禁**：

| 门禁 | 状态 | 说明 |
|------|------|------|
| 可测试性 | Pass | Loop、插件、健康、自检均有契约或 CLI 可验 |
| 安全默认 | Pass | 敏感插件 + 入站配对在数据模型与 contracts 中体现 |
| 复杂度论证 | Pass | 引入 `runtime/` 包隔离内核与插件加载，避免散落在 `main.py` |

**Phase 1 后复检**：`data-model.md` 与 `contracts/` 覆盖 FR-001–FR-015 的主要接口面；无未解析的 NEEDS CLARIFICATION。

## Project Structure

### Documentation (this feature)

```text
specs/004-openclaw-alignment/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md              # 由 /speckit.tasks 更新（与 spec 可能不同步时需重跑）
```

### Source Code（建议增量布局）

```text
src/
├── main.py                      # 唯一文档化主入口：子命令 foreground / daemon / doctor / plugins
├── core/
│   ├── hello_agents/            # 现有 ReAct / ToolRegistry（LoopDriver 适配层）
│   ├── llm/
│   └── runtime/                 # 本特性新增（名称可微调）
│       ├── __init__.py
│       ├── loop_driver.py       # Agent Loop 抽象：迭代、预算、轨迹收集
│       ├── trace.py             # 轨迹模型与序列化（对齐 contracts）
│       ├── config.py            # 统一配置加载与校验（Pydantic）
│       ├── plugin_host.py       # 插件发现、manifest 解析、注册表
│       ├── tools_builtin.py     # 内置 Tool 适配进插件接口
│       ├── skill_loader.py      # Skill → 系统提示补丁 + 工具子集
│       ├── mcp_bridge.py        # MCP 端点 → 统一 Tool 调用
│       ├── subagent.py          # 委派、白名单、限深
│       ├── daemon.py            # 常驻循环、事件入口（定时/队列占位）
│       ├── health.py            # 健康快照
│       └── inbound.py           # 配对与策略（与 spec US5 对齐）
├── plugins/                     # 参考插件（各类型 1 个）
│   ├── example_tool/
│   ├── example_skill/
│   ├── example_subagent/
│   └── README.md
└── tools/                       # 现有搜索等（经 adapter 暴露为插件）

deploy/ 或 docs/daemon/          # launchd/systemd 样例单元（可选目录）
tests/
├── unit/
└── integration/
```

**Structure Decision**: **单项目 `src/`**，新增 `core/runtime/` 作为编排与扩展宿主；**不**新建独立仓库。MCP 与 SubAgent 逻辑放在 `runtime/` 下便于测试与契约对齐。

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 新增 `runtime/` 包 | 分离 Loop、插件、常驻、健康，避免 `main.py` 成为上帝对象 | 继续堆在脚本中将无法满足 FR-005–008 与可测性 |
| MCP 桥接层 | FR-007 要求统一权限/超时/轨迹 | 直接散落调用无法分类错误与审计 |

## Phase 0 & 1 产出索引

| 文档 | 路径 |
|------|------|
| 研究结论 | [research.md](./research.md) |
| 数据模型 | [data-model.md](./data-model.md) |
| 契约 | [contracts/](./contracts/) |
| 快速上手 | [quickstart.md](./quickstart.md) |

## 建议实现里程碑（供后续 tasks 拆解）

1. **M1 — Loop + 轨迹**：`loop_driver` + 扩展 `trace-event.schema.json`；foreground `task`/`chat` 走统一路径。  
2. **M2 — 插件宿主**：manifest、`plugin_host`、四类参考插件最小实现（含 MCP bridge PoC）。  
3. **M3 — Daemon**：`daemon` 子命令、健康检查、`doctor` 扩展；文档化监督重启与退避。  
4. **M4 — 配置与安全**：统一 `config`、入站配对、敏感插件 ACL；`quickstart` 与 SC 对齐。  
5. **M5 — Soak 与观测**：日志/轨迹轮转、可选 metrics 钩子、72h 测试手册（CI 外）。
