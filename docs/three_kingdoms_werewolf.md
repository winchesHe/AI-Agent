# 三国狼人杀：架构设计与 AgentScope 的作用

本文档说明「三国狼人杀」案例的架构设计，以及 **AgentScope** 消息驱动架构在本项目中的对应实现与作用。

---

## 1. 案例目标

为了深入理解 **AgentScope 的消息驱动架构**和**多智能体协作能力**，本案例实现了一个融合中国古典文化元素的「三国狼人杀」游戏：

- 每个智能体既要完成狼人杀的基本任务（狼人击杀、预言家查验、村民推理等），又要体现对应三国人物的性格与行为模式。
- 游戏流程通过**消息驱动**组织：所有智能体间通信由**消息中心**路由与分发，而非中心化状态机。
- 通过 **结构化输出** 约束智能体行为，使游戏规则可自动校验与执行。

---

## 2. 架构设计：三层解耦

系统按**分层解耦**划分，每层对应 AgentScope 的核心理念或组件：

| 层次 | 职责 | 在本项目中的实现 | AgentScope 对应 |
|------|------|------------------|-----------------|
| **游戏控制层** | 维护全局状态、推进阶段、裁定胜负 | `ThreeKingdomsWerewolfGame` | 应用层编排；不直接对应单一组件，由开发者基于 MsgHub/Agent 编排 |
| **智能体交互层** | 路由与分发消息，建立私密/公开频道 | `MsgHub`、`fanout_pipeline` | **MsgHub**（消息中心）、**fanout_pipeline**（并行收集） |
| **角色建模层** | 为每个玩家注入「游戏角色 + 三国人格」 | `PlayerAgent`、提示词 `get_role_prompt()` | **DialogAgent**（仅通过对话参与，无工具调用） |

### 2.1 游戏控制层 (Game Control Layer)

- **类**：`ThreeKingdomsWerewolfGame`
- **职责**：
  - 维护全局状态：存活/死亡玩家、当前回合、女巫技能使用情况等。
  - 推进游戏流程：依次调用夜晚阶段（狼人 → 预言家 → 女巫）与白天阶段（公布结果 → 讨论 → 投票）。
  - 胜负判定：狼人全灭则好人胜；狼人数量 ≥ 好人数量则狼人胜。

本层**不**直接维护复杂状态机，而是通过「在特定上下文中发起何种消息交互」来驱动流程，对应 AgentScope 中由应用层基于 MsgHub 编排的用法。

### 2.2 智能体交互层 (Agent Interaction Layer)

- **核心**：完全由「消息」驱动。狼人间的秘密协商、白天的公开讨论与投票，都通过消息中心进行路由与分发。
- **本项目中**：
  - **`MsgHub`**：为指定智能体列表建立通信上下文（如仅狼人可见的频道）。支持进入时广播公告、多轮讨论后关闭广播再收集投票。
  - **`fanout_pipeline`**：向多个智能体并行发送同一条消息，并收集各自的结构化输出（如击杀目标、投票对象）。

这样，游戏逻辑被表达为「在特定上下文中，以何种模式进行消息交换」，而不是一连串僵硬的状态转换。

### 2.3 角色建模层 (Role Modeling Layer)

- **实现**：每个玩家是 `PlayerAgent` 的实例，通过**系统提示词**注入「游戏角色」（狼人/预言家/女巫/村民）和「三国人格」（刘备、曹操等）。
- **约束**：仅通过对话参与游戏，不调用外部工具；输出通过 Pydantic 模型约束为规定 JSON，便于规则校验。

对应 AgentScope 中基于 **DialogAgent** 的角色建模方式。

---

## 3. 消息驱动的游戏流程示例

以**狼人阶段**为例，流程不是「状态机 + 函数调用」，而是「建立频道 → 讨论 → 收集决策」的消息模式：

```python
# 通过消息中心建立狼人专属通信频道
async with MsgHub(
    self.werewolves,
    enable_auto_broadcast=True,
    announcement="狼人们，请讨论今晚的击杀目标。存活玩家：...",
) as werewolves_hub:
    # 讨论阶段：狼人通过消息交换策略
    for _ in range(MAX_DISCUSSION_ROUND):
        for wolf in self.werewolves:
            await wolf.respond(..., structured_model=DiscussionModelCN)
    # 投票阶段：关闭广播，收集击杀决策
    werewolves_hub.set_auto_broadcast(False)

kill_votes = await fanout_pipeline(
    self.werewolves,
    msg="请选择击杀目标",
    structured_model=WerewolfKillModelCN,
    enable_gather=False,
)
```

白天讨论（全员广播）、预言家查验（点对点请求）、投票（全员 fanout 收集）等阶段都遵循同一套「消息 + 结构化输出」的设计范式。

---

## 4. 结构化输出约束游戏规则

通过 Pydantic 定义各阶段输出格式，实现**规则自动化约束**：

| 模型 | 用途 | 规则约束示例 |
|------|------|----------------|
| `DiscussionModelCN` | 讨论阶段 | 是否达成一致、信心程度、关键证据 |
| `WerewolfKillModelCN` | 狼人击杀 | 仅一个 `target_name` |
| `WitchActionModelCN` | 女巫行动 | `use_antidote` / `use_poison`，毒药需 `target_name` |
| `SeerCheckModelCN` | 预言家查验 | 仅一个 `target_name` |
| `get_vote_model_cn(alive_players)` | 投票 | 投票目标必须在存活名单中 |

这样，女巫不能同时用解药和毒药于同一目标、预言家每晚只查一人等，都通过数据模型与校验逻辑自动体现。

---

## 5. 角色建模：游戏角色 + 三国人格

通过 `get_role_prompt(role, character)` 将**游戏功能角色**与**文化人格角色**融合进系统提示词：

- 同一游戏角色（如狼人）由不同三国人物扮演时，会呈现不同策略与话语风格。
- 规则中明确：仅通过对话参与、不调用工具、严格按 JSON 格式回复。

实现文件：`prompts.py`。

---

## 6. 并发与容错

- **并发**：投票、狼人击杀等需要同时收集多份决策的阶段，使用 `fanout_pipeline` 并行向所有相关智能体发送消息并收集响应，对应「同时投票」的语义。
- **容错**：在 `fanout_pipeline` 与关键 `respond` 调用处使用 try/except，单个智能体异常时生成默认响应或跳过该票，保证游戏可继续推进。参见 `msg_hub.py` 与 `game.py` 中的异常处理。

---

## 7. AgentScope 在本项目中的「作用」总结

| AgentScope 概念 | 在本项目中的体现 |
|-----------------|------------------|
| **消息驱动** | 游戏流程由「消息交互模式」驱动，而非中心化状态机。 |
| **MsgHub** | `MsgHub` 类：建立临时通信频道、广播公告、支持多轮讨论后关闭广播再收集。 |
| **fanout_pipeline** | `fanout_pipeline`：并行向多智能体发送同一消息并收集结构化输出。 |
| **DialogAgent** | `PlayerAgent`：仅对话、无工具；通过系统提示词注入角色与人格。 |
| **结构化输出** | 各阶段使用 Pydantic 模型约束 LLM 输出，实现规则自动约束与解析。 |

本实现采用与 AgentScope 相同的**架构思想**（消息驱动、分层、结构化输出），便于在接入 AgentScope SDK 时做最小化迁移：将 `MsgHub`/`fanout_pipeline`/`PlayerAgent` 替换为 AgentScope 官方实现即可。

---

## 8. 如何运行

```bash
# 在项目根目录
python -m src.scripts.run_three_kingdoms_werewolf
# 或
python src/scripts/run_three_kingdoms_werewolf.py
```

需在 `.env` 中配置 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL_ID`（与项目其他 agent 共用同一 LLM 客户端）。

---

## 9. 代码结构速览

```
src/core/agent/three_kingdoms_werewolf/
├── __init__.py      # 包导出
├── models.py        # 结构化输出模型（讨论/击杀/女巫/预言家/投票）
├── prompts.py      # 角色提示词与主持人话术
├── msg_hub.py       # 消息中心 MsgHub、fanout_pipeline
├── agents.py        # PlayerAgent、ModeratorAgent
└── game.py          # ThreeKingdomsWerewolfGame 主控制器

src/scripts/
└── run_three_kingdoms_werewolf.py   # 独立运行脚本
```
