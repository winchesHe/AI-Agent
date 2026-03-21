# test_function_call_agent.py — 需 OpenAI 兼容 API 与有效 LLM_API_KEY
import path_setup  # noqa: F401

from dotenv import load_dotenv
from hello_agents import FunctionCallAgent, HelloAgentsLLM, ToolRegistry
from hello_agents.tools import CalculatorTool

load_dotenv()

if __name__ == "__main__":
    llm = HelloAgentsLLM()
    registry = ToolRegistry()
    registry.register_tool(CalculatorTool())
    agent = FunctionCallAgent(
        name="函数调用助手",
        llm=llm,
        tool_registry=registry,
        system_prompt="需要计算时请调用 calculator 工具。",
    )
    out = agent.run("请用工具计算 99 / 3 + 7，并一句话说明结果。")
    print(out)
