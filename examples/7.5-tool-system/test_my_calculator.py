# test_my_calculator.py
import path_setup  # noqa: F401

from dotenv import load_dotenv

from hello_agents import HelloAgentsLLM

from my_calculator_tool import create_calculator_registry

load_dotenv()


def test_calculator_tool() -> None:
    registry = create_calculator_registry()

    print("🧪 测试自定义计算器工具\n")

    test_cases = [
        "2 + 3",
        "10 - 4",
        "5 * 6",
        "15 / 3",
        "sqrt(16)",
    ]

    for i, expression in enumerate(test_cases, 1):
        print(f"测试 {i}: {expression}")
        result = registry.execute_tool("my_calculator", expression)
        print(f"结果: {result}\n")


def test_with_simple_agent() -> None:
    llm = HelloAgentsLLM()
    registry = create_calculator_registry()

    print("🤖 与 SimpleAgent / LLM 集成测试:")

    user_question = "请帮我计算 sqrt(16) + 2 * 3"

    print(f"用户问题: {user_question}")

    calc_result = registry.execute_tool("my_calculator", "sqrt(16) + 2 * 3")
    print(f"计算结果: {calc_result}")

    final_messages = [
        {
            "role": "user",
            "content": (
                f"计算结果是 {calc_result}，请用自然语言回答用户的问题:{user_question}"
            ),
        }
    ]

    print("\n🎯 LLM 回答:")
    response = llm.think(final_messages)
    for chunk in response:
        print(chunk, end="", flush=True)
    print("\n")


if __name__ == "__main__":
    test_calculator_tool()
    import os

    if os.getenv("OPENAI_API_KEY"):
        test_with_simple_agent()
    else:
        print("跳过 LLM 集成测试（未设置 OPENAI_API_KEY）")
