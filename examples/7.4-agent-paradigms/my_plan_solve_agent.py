# my_plan_solve_agent.py
import path_setup  # noqa: F401

from typing import Optional

from hello_agents import Config, HelloAgentsLLM, PlanAndSolveAgent


class MyPlanAndSolveAgent(PlanAndSolveAgent):
    """教材示例：Plan-and-Solve，可传入 custom_prompts 覆盖 planner/executor。"""

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        custom_prompts: Optional[dict[str, str]] = None,
    ):
        super().__init__(
            name,
            llm,
            system_prompt=system_prompt,
            config=config,
            custom_prompts=custom_prompts,
        )
