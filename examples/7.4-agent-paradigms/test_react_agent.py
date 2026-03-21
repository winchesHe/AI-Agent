# test_react_agent.py — 与教材一致，依赖 LLM 与计算器工具协同
import path_setup  # noqa: F401

from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM, ToolRegistry
from hello_agents.tools import CalculatorTool

from my_react_agent import MyReActAgent

load_dotenv()

if __name__ == "__main__":
    llm = HelloAgentsLLM()
    registry = ToolRegistry()
    registry.register_tool(CalculatorTool())
    agent = MyReActAgent(
        name="ReAct 助手",
        llm=llm,
        tool_registry=registry,
        system_prompt="你善于分步推理并在需要时使用计算器工具。",
        max_steps=6,
    )
    ans = agent.run("请计算 (128 + 256) / 4 等于多少？先用工具再总结。")
    print("最终答案:", ans)
