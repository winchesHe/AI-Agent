# my_reflection_agent.py
import path_setup  # noqa: F401

from typing import Dict, Optional

from hello_agents import Config, HelloAgentsLLM, ReflectionAgent


class MyReflectionAgent(ReflectionAgent):
    """教材示例：在框架 ReflectionAgent 上保留自定义 prompts 能力。"""

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_rounds: int = 3,
        custom_prompts: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            name,
            llm,
            system_prompt=system_prompt,
            config=config,
            max_rounds=max_rounds,
            custom_prompts=custom_prompts,
        )
