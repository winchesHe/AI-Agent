"""
兼容教材中的 `import hello_agents` 写法。

运行示例前请设置: `PYTHONPATH=src`
（与仓库内 `core.*` 包并列）。
"""
from core.hello_agents import (
    DEFAULT_EXECUTOR_PROMPT,
    DEFAULT_PLANNER_PROMPT,
    DEFAULT_PROMPTS,
    MY_REACT_PROMPT,
    Agent,
    AsyncToolExecutor,
    BaseTool,
    CalculatorTool,
    Config,
    FunctionCallAgent,
    HelloAgentsLLM,
    Message,
    MessageRole,
    PlanAndSolveAgent,
    ReActAgent,
    ReflectionAgent,
    SearchTool,
    SimpleAgent,
    Tool,
    ToolChain,
    ToolChainManager,
    ToolParameter,
    ToolRegistry,
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
