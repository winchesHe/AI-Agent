# CAMEL RolePlaying：拖延症科普电子书双智能体协作

**CAMEL**（Communicative Agents for “Mind” Exploration of Large Language Model Society）中的 **RolePlaying** 是一种「双智能体角色扮演」协作范式：为两个角色设定分工与共同任务，通过多轮对话让模型**自发形成**类似人类团队协作的创作或推理过程，而无需手写复杂状态机。

本仓库中的「作家 + 心理学家」示例是对官方教材 **6.4.2** 场景的复现思路：**OpenAI 兼容 API** 驱动两个角色；实现上不依赖 `camel-ai` 安装包，但 API 形态（`task_prompt`、`init_chat`、`step`、完成标记）与 CAMEL 教程一致，便于对照学习。

---

## 1. RolePlaying 在解决什么问题

- **单模型**长文创作容易在「学术严谨」与「通俗可读」之间顾此失彼。  
- **RolePlaying** 把两种能力拆到两个角色：**User 侧**推动结构与读者体验，**Assistant 侧**供给专业知识与事实核查，通过对话迭代成稿。  
- 设计理念是 **轻编排、重提示**：协作行为主要来自角色与任务描述，而非硬编码流程图。

---

## 2. 三个核心要素：任务、角色、对话环

### 2.1 任务说明书 `task_prompt`

`task_prompt` 是整段协作的「合同」：目标读者、体裁、科学性与可读性要求、篇幅与结构等。CAMEL 会把它注入上下文，让后续轮次始终锚定同一目标。

本示例中的任务正文见代码内常量 **`TASK_PROMPT`**（`prompts.py`），与教材五条要求对齐：实证基础、少术语、实用建议与案例、8000–10000 字量级、引言—章节—总结结构。

### 2.2 角色与 CAMEL 中的 User / Assistant

在 CAMEL 的 RolePlaying 约定里：

| 侧 | 典型职责（本案例） |
|----|---------------------|
| **User 角色名**（本例：**作家**） | 对话的**推动者**：章节结构、改写指令、篇幅与风格；把专家输出「转译」给读者。 |
| **Assistant 角色名**（本例：**心理学家**） | **执行/供给方**：理论、研究依据、草稿与修订、事实核查。 |

教材将作家放在 `user_role_name`、心理学家放在 `assistant_role_name`，正是为了匹配「需求方先提要求、专家再交付」的协作节奏（具体每轮谁先谁后由框架的 `step` 与初始化逻辑组织；理解时抓住「分工」即可）。

### 2.3 对话环：`init_chat` → 反复 `step`

典型控制流与教材代码一致：

1. **`init_chat()`**  
   根据任务与角色生成**进入协作的第一条上下文**（本实现用心理学家侧简短种子开场，避免首轮无上文）。

2. **`step(input_msg)`**  
   以**上一轮心理学家侧产出**为输入，推进一轮完整交互：作家提出本轮 **Instruction**（及可选 **Input** 片段），心理学家给出 **Solution**。

3. **终止**  
   任一侧在回复中出现约定标记 **`<CAMEL_TASK_DONE>`**，或达到轮次上限，或空响应则停止。

多轮之后，常会自然经历教材描述的若干阶段：先对齐大纲 → 再「请求—专业回应—转写」循环 → 再润色与质控 → 最后收尾与总结（**未在代码里写死阶段**，依赖提示与模型行为）。

---

## 3. 在本项目中如何运行与改写

**环境变量**（与常见 OpenAI 兼容网关一致）：`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL_ID`。

```bash
cd <项目根目录>
python -m src.scripts.run_procrastination_ebook
```

**想换主题时**：主要改 `prompts.py` 里的 `TASK_PROMPT`，并按需调整 `WRITER_SYSTEM` / `PSYCHOLOGIST_SYSTEM` 中的角色边界与输出格式（Instruction/Solution、完成标记）。

**想接 CAMEL 官方库时**：把同一 `task_prompt`、角色名与 `ModelFactory` 配置代入官方 `RolePlaying` 即可；本示例等价的是**心智模型与轮次语义**，不是包名。

---

## 4. CAMEL 式 RolePlaying 的优劣与选型（教材 6.4.3 要点）

**优势**

- **上手成本低**：两个 system 角色 + 一段任务说明即可启动深度协作。  
- **适合创造性、长链路任务**：写作、方案研讨等多轮迭代场景与「双专家」叙事契合。  
- **后端可替换**：与 CAMEL 生态一致，可接多种 LLM（本示例通过 OpenAI 兼容接口接入）。

**局限**

- **效果强依赖提示**：角色是否「站稳」、格式是否利于解析，直接决定协作质量；换模型常需重调。  
- **调试偏「对话考古」**：出问题时要对照多轮历史判断是任务、角色还是轮次设计不当。  
- **规模与流程**：双智能体链擅长「对谈式」共创；若需要**多角色路由、群聊仲裁、分布式状态**或**严格有向图步骤**，教材亦指出可对比 AutoGen、AgentScope、LangGraph 等更偏工程编排的方案。

---

## 5. 代码对应关系（速查）

| CAMEL 概念 | 本示例中的位置 |
|------------|----------------|
| `task_prompt` | `prompts.py` → `TASK_PROMPT` |
| 双角色 system | `WRITER_SYSTEM`、`PSYCHOLOGIST_SYSTEM` |
| `RolePlaying` / `init_chat` / `step` | `role_playing.py` → `RolePlayingEbookSession` |
| 一键跑满轮 | `run_procrastination_ebook_collab()`、`run_procrastination_ebook.py` |

以上便于你把教材中的 CAMEL API 与本地实现对号入座；文档重心是 **CAMEL RolePlaying 怎么用、为何这样设计**，而非罗列本仓库其它 Agent。
