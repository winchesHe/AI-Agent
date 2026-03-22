---
description: "Task list for 004-openclaw-alignment（Agent Loop + 插件 + 7×24，对齐修订 spec/plan）"
---

# Tasks: 本地常驻个人助理（Agent Loop + 插件 + 7×24）

**Input**: `/specs/004-openclaw-alignment/` 下 `spec.md`、`plan.md`、`data-model.md`、`research.md`、`contracts/`、`quickstart.md`  
**Prerequisites**: [plan.md](./plan.md)、[spec.md](./spec.md)

**Tests**: 规格未强制 TDD；本清单不含独立测试任务（实现阶段可按需补 `tests/`）。

**Organization**: 按用户故事 US1–US5 分阶段；Setup / Foundational 先行。

## Format: `[ID] [P?] [Story] Description`

- **[P]**：可并行（不同文件、无未完成依赖）
- **[US*]**：仅用户故事阶段
- 路径相对仓库根 `Hello-Agent/`（绝对路径在描述中给出关键配置文件）

---

## Phase 1: Setup（共享基建）

**Purpose**: 建立 `runtime` 与插件目录骨架

- [x] T001 Create package scaffold in `src/core/runtime/__init__.py`
- [x] T002 [P] Create `src/plugins/README.md` describing manifest layout and reference plugins per `specs/004-openclaw-alignment/contracts/plugin-manifest.schema.json`
- [x] T003 [P] Add optional MCP client dependency line or `requirements-mcp.txt` at `/Users/moego-winches/Desktop/Company/AI-Agent/Hello-Agent/requirements.txt` (document choice in `src/plugins/README.md`)

---

## Phase 2: Foundational（阻塞项）

**Purpose**: 轨迹、配置、日志、CLI 骨架——完成前不实现业务故事

**⚠️ CRITICAL**: 未完成本阶段不得合并 US1+ 行为逻辑

- [x] T004 Implement `AssistantRunTrace` / `TraceStep` builders and JSON dumps in `src/core/runtime/trace.py` aligned with `specs/004-openclaw-alignment/contracts/trace-event.schema.json`
- [x] T005 [P] Define Pydantic `ConfigurationProfile` (and nested models) per `specs/004-openclaw-alignment/data-model.md` in `src/core/runtime/config.py` with load from YAML + env override
- [x] T006 Implement `load_and_validate_profile()` raising structured errors for missing LLM fields in `src/core/runtime/config.py`
- [x] T007 Implement argparse subparsers `task`, `chat`, `daemon`, `doctor`, `health`, `plugins` with exit codes per `specs/004-openclaw-alignment/contracts/cli-invocation.md` in `src/main.py` (stubs OK until stories land)
- [x] T008 [P] Add `setup_logging()` with optional `RotatingFileHandler` driven by profile in `src/core/runtime/logging_config.py`

**Checkpoint**: `python src/main.py doctor` 可运行（可先返回「未实现」以外的配置错误路径）

---

## Phase 3: User Story 1 — 主入口与可观测 Agent Loop (Priority: P1) 🎯 MVP

**Goal**: 显式循环、预算、步骤轨迹、多轮会话（对齐 spec US1、FR-002/003）

**Independent Test**: `specs/004-openclaw-alignment/quickstart.md` 第 4 节四类 foreground 场景；`--trace json` 验证 schema

### Implementation for User Story 1

- [x] T009 [US1] Implement `LoopDriver` wrapping `src/core/hello_agents/react_agent.py` `ReActAgent` with `max_iterations` / wall-clock budget and trace emission in `src/core/runtime/loop_driver.py`
- [x] T010 [US1] Wire `task` subcommand (`-m` / `--message`) to `LoopDriver` with `--trace`, `--trace-file`, `--no-tools` in `src/main.py`
- [x] T011 [US1] Implement bounded multi-turn history for `chat` subcommand in `src/core/runtime/session.py` and integrate in `src/main.py`

**Checkpoint**: US1 单独可演示，无需插件与 daemon

---

## Phase 4: User Story 2 — 插件式扩展 Tool / Skill / MCP / SubAgent (Priority: P2)

**Goal**: manifest 发现、统一注册、四类最小参考实现（对齐 spec US2、FR-005–009、SC-003）

**Independent Test**: `python src/main.py plugins list` 显示四类参考；禁用某插件后能力集变化

### Implementation for User Story 2

- [x] T012 [US2] Implement manifest discovery, JSON schema validation, and load order (priority / id conflict rules) in `src/core/runtime/plugin_host.py`
- [x] T013 [US2] Merge plugin-provided tools into runtime `ToolRegistry` facade used by `LoopDriver` in `src/core/runtime/plugin_host.py`
- [x] T014 [P] [US2] Add reference Tool plugin: `src/plugins/example_tool/manifest.json` + 入口模块（现为 manifest 结构示例，默认不注册工具；原 echo 已移除；Tool 冒烟可依赖搜索等；`local_workspace` 默认不启用见 `workspace.enabled`）
- [x] T015 [US2] Implement skill activation (prompt addendum + tool allowlist) in `src/core/runtime/skill_loader.py` plus reference `src/plugins/example_skill/`
- [x] T016 [US2] Implement MCP stdio client bridge mapping remote tools to local adapters with timeout and `transport` vs `business` error classes in `src/core/runtime/mcp_bridge.py`
- [x] T017 [US2] Implement SubAgent delegation with `max_delegation_depth` and tool allowlist in `src/core/runtime/subagent.py` plus reference `src/plugins/example_subagent/`

**Checkpoint**: SC-003 四类各 1 个参考可加载（MCP 可无远端时用 mock server 文档说明）

---

## Phase 5: User Story 3 — 本地 7×24 常驻运行 (Priority: P2)

**Goal**: daemon 循环、健康快照、监督单元样例（对齐 spec US3、FR-010–012、SC-004/005）

**Independent Test**: `daemon` + 第二终端 `health --json`；样例 plist/service 可被人工安装验证

### Implementation for User Story 3

- [x] T018 [US3] Implement asyncio long-running loop with periodic internal probe and exponential backoff for external calls in `src/core/runtime/daemon.py`
- [x] T019 [US3] Wire `daemon` subcommand: graceful shutdown on SIGTERM, configurable probe interval from profile, in `src/main.py`
- [x] T020 [US3] Implement `build_health_snapshot()` returning JSON matching `specs/004-openclaw-alignment/contracts/health-snapshot.schema.json` in `src/core/runtime/health.py`
- [x] T021 [US3] Wire `health --json` subcommand to stdout in `src/main.py`
- [x] T022 [P] [US3] Add sample supervision files `docs/daemon/launchd.example.plist` and `docs/daemon/hello-agent.service` under `/Users/moego-winches/Desktop/Company/AI-Agent/Hello-Agent/docs/daemon/`

**Checkpoint**: 72h soak 仍按运维手册在 CI 外执行；代码路径已具备探针与退避

---

## Phase 6: User Story 4 — 引导式上线与可维护配置 (Priority: P3)

**Goal**: 示例配置、doctor 增强、操作文档（对齐 spec US4、FR-013/014、SC-001/007）

**Independent Test**: 新目录克隆后按 `docs/personal-assistant-quickstart.md` 完成首次启动

### Implementation for User Story 4

- [x] T023 [US4] Add `assistant.yaml.example` at `/Users/moego-winches/Desktop/Company/AI-Agent/Hello-Agent/assistant.yaml.example` covering `loop`, `plugins`, `mcp`, `daemon`, `security`, `logging` keys per `specs/004-openclaw-alignment/data-model.md`
- [x] T024 [US4] Implement `run_doctor()` reporting config version, plugins, optional MCP probe flag in `src/core/runtime/doctor.py` and invoke from `src/main.py`
- [x] T025 [P] [US4] Create or update `docs/personal-assistant-quickstart.md` at `/Users/moego-winches/Desktop/Company/AI-Agent/Hello-Agent/docs/personal-assistant-quickstart.md` mirroring `specs/004-openclaw-alignment/quickstart.md` with final CLI names

**Checkpoint**: `doctor` 帮助区分配置 / 插件 / 网络（SC-007 子集）

---

## Phase 7: User Story 5 — 不可信入站与最小安全默认 (Priority: P3)

**Goal**: 配对存储、敏感插件 ACL、可模拟入站（对齐 spec US5、FR-015、SC-006）

**Independent Test**: 模拟未配对 `InboundSource` 不触发 `sensitive_plugin_ids` 工具；配对后可触发

### Implementation for User Story 5

- [x] T026 [US5] Implement pairing JSON store and `pairing_required` policy gate in `src/core/runtime/inbound.py`
- [x] T027 [US5] Add CLI flags (e.g. `task --inbound-channel` / `--inbound-sender`) to simulate inbound and enforce ACL before `LoopDriver` in `src/main.py`

**Checkpoint**: US5 可与 US1/US2 联合验收

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 静态检查、帮助文案、人工冒烟清单

- [x] T028 [P] Run `ruff check .` from `src/` and fix new issues in `src/core/runtime/`、`src/plugins/`、`src/main.py`
- [x] T029 Update argparse help strings and epilog to match `specs/004-openclaw-alignment/contracts/cli-invocation.md` in `src/main.py`
- [x] T030 Execute manual checklist section 8 in `specs/004-openclaw-alignment/quickstart.md` and note results in PR description

---

## Phase 9: 本地工作区权限（OpenClaw 对齐扩展）

**Purpose**: 配置化 `workspace.allowed_roots`，插件化提供列出/读/写能力，并纳入 `sensitive_plugin_ids`。

- [x] T031 Add `WorkspaceConfig` and `workspace` field on `ConfigurationProfile` in `src/core/runtime/config.py`
- [x] T032 Extend `PluginHost` with `PluginLoadContext`, `resolve_workspace_roots`, multi-tool factory return, and `workspace=` in `src/core/runtime/plugin_host.py`; wire in `src/main.py`
- [x] T033 Implement `src/plugins/local_workspace/` (manifest + `workspace_list_dir` / `workspace_read_file` / `workspace_write_file`) and JSON multi-arg parsing in `src/core/hello_agents/tool_registry.py`
- [x] T034 Add `workspace` / `sensitive_plugin_ids` example in `assistant.yaml` and workspace diagnostics in `src/core/runtime/doctor.py`（仓库示例 `workspace.enabled` 默认 `false`）

---

## Dependencies & Execution Order

### Phase Dependencies

`Phase 1` → `Phase 2` → `Phase 3 (US1)` → `Phase 4 (US2)` → `Phase 5 (US3)` → `Phase 6 (US4)` → `Phase 7 (US5)` → `Phase 8`

- **US2** 依赖 **US1** 的 `LoopDriver` 与 `main.py` 接线面
- **US3** 依赖 **US1** 的执行内核（daemon 内复用 loop）；可与 **US4** 部分并行（文档 vs 代码）
- **US5** 依赖 **US2** 的权限模型字段（sensitive ids）与 **US1** 的 loop 入口

### Parallel Opportunities

- T002 / T003；T005 / T004 / T008（在 T006 前完成模型与 trace、日志）；T014 与 T022；T025 与 T024（文档与 doctor 合并前需对齐 CLI 名称）；T028 与 T029（同一文件时串行）

### Parallel Example: User Story 2

```text
同时开工：T014（example_tool）与 T016（mcp_bridge 骨架），合并前由 T013 统一注册表接口冻结
```

---

## Implementation Strategy

### MVP（仅 US1）

完成 Phase 1–3 后暂停，按 `quickstart.md` 做 foreground 四类冒烟。

### Incremental Delivery

1. +US2 插件与 MCP/SubAgent  
2. +US3 daemon 与健康  
3. +US4 文档与示例配置  
4. +US5 入站安全  
5. Polish

---

## Task Summary

| 阶段 | 任务数 | IDs |
|------|--------|-----|
| Phase 1 Setup | 3 | T001–T003 |
| Phase 2 Foundational | 5 | T004–T008 |
| Phase 3 US1 | 3 | T009–T011 |
| Phase 4 US2 | 6 | T012–T017 |
| Phase 5 US3 | 5 | T018–T022 |
| Phase 6 US4 | 3 | T023–T025 |
| Phase 7 US5 | 2 | T026–T027 |
| Phase 8 Polish | 3 | T028–T030 |
| **Total** | **30** | T001–T030 |

---

## Notes

- 所有任务含明确路径；实现时若调整包名须同步更新本文件与 `plan.md`  
- MCP 无可用远端时，在 `src/plugins/README.md` 说明如何用官方示例 server 本地起测
