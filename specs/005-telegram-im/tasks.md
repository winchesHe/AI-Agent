# Tasks: Telegram 即时消息入站通道

**Input**: `/specs/005-telegram-im/`（spec.md、plan.md、research.md、data-model.md、contracts/、quickstart.md）  
**Tests**: 规格未强制 TDD；以手工 quickstart 与可选 pytest 为主。

## Phase 1: Setup（共享基础）

- [x] T001 在 `requirements.txt` 增加 `python-telegram-bot>=21.0` 依赖声明

## Phase 2: Foundational（阻塞项）

- [x] T002 在 `src/core/runtime/config.py` 增加 `TelegramConfig` 与 `ConfigurationProfile.telegram` 可选字段并保证 YAML 缺省时不报错
- [x] T003 在 `src/core/runtime/inbound.py` 为 `PairingStore` 增加列出全部配对记录的方法供 CLI 使用

## Phase 3: User Story 1 — Telegram 文本对话 (P1)

**Goal**: 长轮询收文本 → `LoopDriver.run` → 回复文本  
**Independent Test**: 按 `quickstart.md` 完成首条往返消息

- [x] T004 [US1] 新增 `src/core/runtime/telegram_runner.py`：校验 `telegram.enabled` 与 token 环境变量、注册文本处理器、`asyncio.to_thread` 调用 `LoopDriver`、回复 `LoopResult.answer` 或错误摘要
- [x] T005 [US1] 在 `src/main.py` 增加子命令 `telegram run`（加载配置、`_build_runtime`、调用 runner、`finally` 中 `_close_mcp_bridge`）

## Phase 4: User Story 2 — 入站安全 (P2)

**Goal**: `sensitive_plugin_ids` 与 `InboundGate` 行为与 `task` 一致  
**Independent Test**: 未配对 + 敏感插件配置时收到策略提示；`pair add` 后通过

- [x] T006 [US2] 在 `telegram_runner.py` 消息路径上对 `profile.security.sensitive_plugin_ids` 逐个 `gate.enforce`，捕获 `AccessDeniedError` 并回复用户安全提示（不泄露内部实现）

## Phase 5: User Story 3 — 可配置与可诊断 (P3)

**Goal**: 误配快速失败；文档与示例一致  
**Independent Test**: 缺 token 启动失败信息明确；`pair list` 可见记录

- [x] T007 [US3] 在 `src/main.py` 实现 `pair add` / `pair remove` / `pair list`（依赖 `pairing_store_path`；缺省时清晰报错）
- [x] T008 [US3] 更新仓库根目录 `assistant.yaml` 中可选 `telegram` 示例段（注释形式或与 plan 一致的最小示例）

## Phase 6: Polish

- [x] T009 运行 `cd src && ruff check .` 并修复本特性引入的问题

## Phase 6b: 日志与 IM 错误 UX（实现同步入文档）

**Goal**：本地可检索 ERROR、日志目录不入库；IM 失败时不重复推送等价错误文案  
**Independent Test**：配置 `logging.path` 后触发一次可恢复异常，确认文件仅有 ERROR 行、聊天侧单条错误提示

- [x] T013 [US3/Polish] `assistant.yaml` 示例 `logging.path: logs/hello-agent.log`；`.gitignore` 增加 `logs/`；`logging_config` 对文件 handler 设 `ERROR`、并 `mkdir` 父目录
- [x] T014 [US1/Polish] `telegram_runner`：`LoopDriver` 异常时先 `edit_text` 进度消息，**仅编辑失败**时再 `reply`，避免双气泡

## Phase 7: 运行过程流式反馈（OpenClaw 对齐）

**Goal**: 多步 ReAct 期间用户可看到 **FR-008 轨迹摘要** 与 **FR-009 每步模型流式累积**（同一条进度消息 `edit_text`，最终回答单独 `reply`），减少「长时间无响应」感知  
**Independent Test**: （1）多步工具任务：进度多次编辑 + 最终回答；（2）单轮纯推理 + quickstart 流式友好环境：**SC-006** 手工清单（≥2 次可见变化）

- [x] T010 [US4] 扩展 `trace.new_trace` 支持 `on_step` 回调；`LoopDriver.run` 增加 `on_trace_step` 并传入 `new_trace`
- [x] T011 [US4] 在 `telegram_runner.py` 首条回复为进度占位；`on_trace_step` 经 `asyncio.run_coroutine_threadsafe` 编辑进度文本（思考/工具/MCP/错误等摘要，对齐 FR-008），结束后再 `reply` 最终回答
- [x] T012 [US4] `ReActAgent` 在传入 `llm_stream_callback` 时对每步使用 `HelloAgentsLLM.stream_invoke`；`LoopDriver.run` 增加 `on_llm_stream` 并传入 `agent.run`；`telegram_runner` 将轨迹行与「第 N 步 · 模型输出」累积文本合并展示，并对 `delta` 节流、`step_start`/`end` 强制刷新（对齐 FR-009 与 `quickstart.md`）

## Phase 8: 线程（thread）内承载思考（FR-010）

**Goal**：在**不取消** FR-008 / FR-009 增量过程的前提下，使思考与进度落在 **Telegram 线程视图**内（锚点 + `reply_to` / `message_thread_id` 等，私聊与群/论坛分支）  
**Independent Test**：在支持话题的群与私聊各测一轮：用户可在**同一线程**内看到进度编辑/串联与终稿；无话题能力时验收「回复链」降级仍满足 SC-005 / SC-006

- [x] T015 [US4] `telegram_runner`（及必要配置项）：为每轮入站建立**线程锚点**，进度与流式合并展示**在该线程上下文中**发送/编辑；终稿 **SHOULD** 同线程回复；文档同步 `quickstart.md` / `plan.md`

## Phase 9: 文档 — 工作区不限于仓库根（FR-011）

**Goal**：明确「整台 Mac 任意 cwd」与相对路径解析规则，避免读者误以为只能在仓库根操作  
**Independent Test**：通读 `spec.md` Assumptions / FR-011 与 `quickstart.md` §6，确认无「唯一合法目录」歧义

- [x] T016 [US3/Docs] 更新 `spec.md`（FR-011、Assumptions、修订说明）、`plan.md`、`quickstart.md`、`contracts/cli-invocation.md`、本 checklist Notes

## Dependencies（故事顺序）

1. T001 → T002 → T003 → 并行结束  
2. T004 依赖 T002；T005 依赖 T004  
3. T006 依赖 T004（可与 T005 同一提交，但逻辑上在消息路径）  
4. T007、T008 可与 US1 完成后并行；T007 依赖 T003  
5. T009：Polish（Phase 6），在 Phase 7 之前或与之并行仅当不改共享文件冲突；**推荐** T009 在 Phase 3–5 稳定后执行  
6. **Phase 7**：T010 → T011 → T012 逻辑串联（均依赖 T004/T005 已交付的 `LoopDriver` + `telegram_runner` 骨架）；T012 依赖 T010、T011 所建立的回调与编辑管线  
7. **Phase 8**：T015 依赖 Phase 7 完成后的 `telegram_runner` 行为；可与配置项扩展并行，宜单 PR 串行避免 IM 路径半成品  
8. **Phase 9**：T016 为纯文档，可与运维排障阅读路径并行；无代码依赖

## 并行机会

- T001 与文档阅读并行  
- T007 与 T008 可在 T003 完成后并行  
- T010–T012 修改 `trace.py` / `loop_driver.py` / `react_agent.py` / `telegram_runner.py` 时**宜同批串行**，避免半成品行为

## Implementation strategy

先完成 T001–T005 交付 **MVP（US1）**，再 T006–T008 补齐安全与运维体验，T009 静态检查收尾；**Phase 7（T010–T012）** 交付 US4 / FR-008 / FR-009 与 **SC-005 / SC-006**；**Phase 8（T015）** 对齐 **FR-010**（thread 内思考 + 保留增量过程）；**Phase 9（T016）** 对齐 **FR-011**（整 Mac / 任意 cwd 与路径文档）。
