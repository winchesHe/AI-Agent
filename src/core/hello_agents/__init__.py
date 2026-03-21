"""
HelloAgents 框架（教材 7.3–7.4）：消息、配置、Agent 基类与各范式实现。

LLM 见 `core.llm.llm_client.HelloAgentsLLM`。
"""
from core.llm.llm_client import HelloAgentsLLM

from .agent import Agent
from .async_tool_executor import AsyncToolExecutor
from .config import Config
from .function_call_agent import FunctionCallAgent
from .message import Message, MessageRole
from .plan_solve_agent import (
    DEFAULT_EXECUTOR_PROMPT,
    DEFAULT_PLANNER_PROMPT,
    PlanAndSolveAgent,
)
from .react_agent import MY_REACT_PROMPT, ReActAgent
from .reflection_agent import DEFAULT_PROMPTS, ReflectionAgent
from .simple_agent import SimpleAgent
from .tool_chain import ToolChain, ToolChainManager
from .tool_registry import ToolRegistry
from .tools import (
    BaseTool,
    CalculatorTool,
    SearchTool,
    Tool,
    ToolParameter,
)

__all__ = [
    "Agent",
    "AsyncToolExecutor",
    "BaseTool",
    "CalculatorTool",
    "Config",
    "DEFAULT_EXECUTOR_PROMPT",
    "DEFAULT_PLANNER_PROMPT",
    "DEFAULT_PROMPTS",
    "FunctionCallAgent",
    "HelloAgentsLLM",
    "Message",
    "MessageRole",
    "MY_REACT_PROMPT",
    "PlanAndSolveAgent",
    "ReActAgent",
    "ReflectionAgent",
    "SearchTool",
    "SimpleAgent",
    "Tool",
    "ToolChain",
    "ToolChainManager",
    "ToolParameter",
    "ToolRegistry",
]
