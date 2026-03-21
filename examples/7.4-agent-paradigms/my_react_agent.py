# my_react_agent.py
import path_setup  # noqa: F401

from typing import Optional

from hello_agents import Config, HelloAgentsLLM, ReActAgent, ToolRegistry


class MyReActAgent(ReActAgent):
    """
    重写的 ReAct Agent - 推理与行动结合的智能体
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        tool_registry: ToolRegistry,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_steps: int = 5,
        custom_prompt: Optional[str] = None,
    ):
        super().__init__(
            name,
            llm,
            tool_registry,
            system_prompt=system_prompt,
            config=config,
            max_steps=max_steps,
            custom_prompt=custom_prompt,
            verbose=True,
        )
        print(f"✅ {name} 初始化完成，最大步数: {max_steps}")
