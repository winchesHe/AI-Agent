# Specification Quality Checklist: Telegram 即时消息入站通道

**Purpose**: 在进入 Plan 前校验规格完整性与质量  
**Created**: 2026-03-22  
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] 无实现细节泄露（未绑定具体 SDK、语言模块名）
- [x] 聚焦用户价值与安全运维需求
- [x] 非技术干系人可理解主要旅程
- [x] 必填章节均已填写

## Requirement Completeness

- [x] 无 [NEEDS CLARIFICATION] 残留
- [x] 需求可测试且语义明确
- [x] 成功标准可度量
- [x] 成功标准与技术无关（不涉及具体框架名）
- [x] 验收场景已覆盖主流程与安全、上线
- [x] 边界情况已列出
- [x] 范围已界定（文本优先、凭证引用假设）
- [x] 依赖与假设已写明（与既有助理行为一致）
- [x] **FR-011**：文件类相对路径相对进程 cwd；已说明典型 cwd 为 `~` 与仓库根两种情形，已在 spec 与 quickstart / plan / 契约中说明

## Feature Readiness

- [x] 功能需求均具备可推导的验收方式
- [x] 用户场景覆盖 P1 主对话、P2 安全、P3 可运维；**P1 US4**（过程可见 + 流式）已写入 spec
- [x] 与 Success Criteria 中的指标对齐（含 **SC-005 / SC-006**）
- [x] 规格未将具体供应商 SDK 列为强制实现手段；FR-009 以行为（流式补全、降级、节流边界）表述为主

## 流式与进度（FR-008 / FR-009 / FR-010 / SC-005 / SC-006）

- [x] **FR-008** 与 **FR-009** 职责分离：轨迹步骤摘要 vs 每步模型输出累积
- [x] **FR-009** 含流式前提、非流式 MAY 降级、quickstart 说明义务及「不保证逐字」边界
- [x] **FR-010**：过程不得因 thread 化而取消；思考进度落在线程/回复链内；终稿与过程关系已写明
- [x] **US4** 验收场景 4 与扩展后的 Independent Test 覆盖多步轨迹与单轮流式观察（含 thread 上下文）
- [x] **SC-005 / SC-006** 手工步骤见 [quickstart.md §7](../quickstart.md)
- [x] **tasks.md** Phase 7 含 T010–T012（FR-008 / FR-009）；**Phase 8 · T015**（FR-010：回复链 + `message_thread_id`）已实现

## Notes

- 校验结论：**修订后**规格与 plan/tasks/quickstart 对齐 US4 流式叙事；可继续按 `tasks.md` 维护实现与回归。
- 若未来将「关闭 IM 流式」产品化，须在 spec 增加显式开关需求并同步本清单。
- **实现同步**：`logs/` 落盘（仅 ERROR+）、`.gitignore`、`telegram_runner` 单条错误反馈等已写入 spec（边界/假设）、plan（表）、quickstart（§6–§8）、`tasks.md`（T013–T014）、`contracts/cli-invocation.md`（`telegram run` 日志行）。
- **FR-010 / T015**：代码已对齐（进度首条 `reply` 用户 + 终稿 `reply` 进度消息；论坛附 `message_thread_id`）。
- **工作区 / cwd（FR-011）**：规格已写明相对路径相对进程 cwd；已补充**典型 cwd 为用户主目录 `~`**（相对路径落在 `~/...`）与「仓库根启动 / 绝对路径」推荐；plan / quickstart / `cli-invocation.md` 已同步。
