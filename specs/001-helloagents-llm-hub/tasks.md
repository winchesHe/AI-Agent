# Tasks: HelloAgentsLLM 适应性模型调用中枢

**Input**: Design documents from `/specs/001-helloagents-llm-hub/`  
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md)

**Tests**: 规格未要求 TDD；本任务单不含独立测试任务。

**Organization**: 按用户故事划分阶段，便于独立实现与验收。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、无未完成依赖）
- **[Story]**: 对应 spec 中的用户故事 US1 / US2 / US3
- 描述中须含确切文件路径

## Path Conventions

- 单仓库 Python：`src/` 为核心代码；示例：`src/examples/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 确认现状与依赖，避免改接口后遗漏调用点

- [x] T001 Audit `HelloAgentsLLM` 的导入与构造方式 across `src/main.py`, `src/scripts/`, `src/core/agent/`
- [x] T002 [P] 核对 `requirements.txt` 中 `openai` 与 `python-dotenv` 版本是否满足 OpenAI 兼容客户端与多 `base_url` 用法

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 所有用户故事依赖的统一入口与内部结构

**⚠️ CRITICAL**: 未完成本阶段前不应开始分故事收尾

- [x] T003 在 `src/core/llm/llm_client.py` 为 `HelloAgentsLLM` 增加 `provider`（默认 `auto`）、实例级 `temperature`/`max_tokens`（可选），并同时接受 `api_key`/`apiKey`、`base_url`/`baseUrl` 别名且行为一致
- [x] T004 在 `src/core/llm/llm_client.py` 抽取创建底层 HTTP 客户端的私有方法（单一出口，供各 provider 分支复用）
- [x] T005 在 `src/core/llm/llm_client.py` 于解析完成后输出不含密钥的诊断信息（最终 `provider`、是否使用默认基地址）

**Checkpoint**: 基类结构就绪，可开始按故事补全各服务商解析逻辑

---

## Phase 3: User Story 1 - 多提供商统一配置 (Priority: P1) 🎯 MVP

**Goal**: 显式 `provider` 时正确解析 OpenAI、ModelScope、智谱的密钥、默认基地址与模型回退

**Independent Test**: 仅配置目标云厂商环境变量并指定对应 `provider`，`think` 成功返回内容

### Implementation for User Story 1

- [x] T006 [US1] 在 `src/core/llm/llm_client.py` 实现 `_resolve_credentials`（或等价）中 `openai` / `modelscope` / `zhipu` 分支，含教材约定默认 `base_url` 与环境变量优先级
- [x] T007 [US1] 在 `src/core/llm/llm_client.py` 确保显式 `provider != auto` 时不运行自动推断，仅按该服务商规则解析
- [x] T008 [P] [US1] 在 `src/examples/my_llm_modelscope.py` 添加教材风格 `MyLLM(HelloAgentsLLM)` 子类示例（`provider=="modelscope"` 走子类，其余 `super()`），展示零改上游包扩展方式

**Checkpoint**: 三云端厂商可独立切换验证

---

## Phase 4: User Story 2 - 本地高性能推理 (Priority: P2)

**Goal**: VLLM、Ollama 及泛本地 OpenAI 兼容端点可通过统一客户端接入

**Independent Test**: 本地服务启动后，仅改 `base_url`/环境即可跑通与 US1 相同调用形态

### Implementation for User Story 2

- [x] T009 [US2] 在 `src/core/llm/llm_client.py` 的 `_resolve_credentials` 增加 `vllm`、`ollama`、`local` 分支（占位 API key、默认 localhost 端口约定、可被参数与环境覆盖）
- [x] T010 [US2] 在 `src/core/llm/llm_client.py` 模块文档字符串中补充 VLLM/Ollama 典型 `base_url` 与 `api_key` 占位说明

**Checkpoint**: 本地兼容服务与云端可在同一代码路径切换

---

## Phase 5: User Story 3 - 环境自动检测 (Priority: P3)

**Goal**: `provider=auto` 时按优先级推断服务商并解析凭证

**Independent Test**: 仅 `.env` 设置 `LLM_BASE_URL`（含端口特征）与 `LLM_MODEL_ID`，无显式 `provider` 时推断正确且可调用

### Implementation for User Story 3

- [x] T011 [US3] 在 `src/core/llm/llm_client.py` 实现 `_auto_detect_provider`：`MODELSCOPE_API_KEY` / `OPENAI_API_KEY` / `ZHIPU_API_KEY` 等优先 → `LLM_BASE_URL` 域名与端口启发 → `LLM_API_KEY` 前缀辅助 → 安全默认
- [x] T012 [US3] 在 `src/core/llm/llm_client.py` 将 `auto` 流程串联：检测 → 解析 → 构建客户端；显式 `provider` 始终覆盖检测结果
- [x] T013 [US3] 在 `src/core/llm/llm_client.py` 为缺密钥、缺模型、缺基地址等情况抛出带操作指引的 `ValueError`

**Checkpoint**: 约定式配置可跑通 Ollama/VLLM/云端典型场景

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 回归与一致性

- [x] T014 [P] 遍历 `src/` 中所有 `HelloAgentsLLM(` 调用，确认默认参数下行为与升级前兼容或有意Breaking已在同 PR 修完
- [x] T015 按 `specs/001-helloagents-llm-hub/spec.md` 中各 User Story 的 Acceptance Scenarios 做一次手工验收并记录结果

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1**: 无依赖
- **Phase 2**: 依赖 Phase 1 — **阻塞**所有用户故事
- **Phase 3–5**: 均依赖 Phase 2；建议顺序 US1 → US2 → US3（US3 依赖前两阶段已定义的解析表）
- **Phase 6**: 依赖 Phase 3–5 中计划交付的范围全部完成

### User Story Dependencies

- **US1**: Phase 2 完成后可开始；不依赖 US2/US3
- **US2**: Phase 2 完成后可开始；解析表与 US1 共享同一函数时可顺序接在 US1 之后
- **US3**: 建议在 US1+US2 解析分支齐全后实现，以便自动检测能映射到完整解析逻辑

### Parallel Opportunities

- T002 与 T001 可并行
- T008 与 T007 可并行（不同文件）
- T014 可在功能代码稳定后与其他收尾并行准备

---

## Parallel Example: User Story 1

```text
T007: 显式 provider 跳过 auto — src/core/llm/llm_client.py
T008: ModelScope 子类示例 — src/examples/my_llm_modelscope.py
```

---

## Implementation Strategy

### MVP First（仅 User Story 1）

1. Phase 1 → Phase 2 → Phase 3（至 T007；示例 T008 可选同迭代）
2. 停在对三云端厂商的手工验收

### Incremental Delivery

1. Setup + Foundational
2. +US1 → 演示云端切换
3. +US2 → 演示本地 VLLM/Ollama
4. +US3 → 演示零显式 provider
5. Polish

---

## Notes

- 任务格式均为 `- [ ] Txxx ...` 且含路径，便于代理或人类逐步勾选

## T015 验收记录（实现后）

- **US1**：`_resolve_credentials` 覆盖 openai / modelscope / zhipu；`provider` 显式非 `auto` 时跳过 `_auto_detect_provider`；`src/examples/my_llm_modelscope.py` 可演示子类扩展。
- **US2**：vllm / ollama / local 分支与模块级文档说明已就绪；真机连通依赖本地服务，未在本机启动推理进程。
- **US3**：自动检测顺序与 `openai` 回退已实现；显式 `provider` 覆盖自动推断已用脚本断言（`provider=ollama` 且存在 `MODELSCOPE_API_KEY` 时仍以 ollama 为准）。
- **回归**：`HelloAgentsLLM()` 无参调用仍兼容「LLM_* 三联」配置；`think(..., stream=False, temperature=...)` 调用点无需修改。
- **校验命令**：`PYTHONPATH=src python -c "from core.llm.llm_client import HelloAgentsLLM"`；见实现会话中的 resolution 脚本断言。
