from dotenv import load_dotenv

from core.agent.reflection_agent import ReflectionAgent
from core.llm.llm_client import HelloAgentsLLM

# 加载 .env 文件中的环境变量
load_dotenv()


if __name__ == "__main__":
    # 1. 初始化 LLM 客户端
    llm_client = HelloAgentsLLM()

    # 2. 创建 Reflection 智能体并运行（执行-反思-优化循环）
    agent = ReflectionAgent(llm_client=llm_client, max_iterations=3)

    task = "编写一个Python函数，找出1到n之间所有的素数 (prime numbers)。"
    print(f"\n--- Reflection Agent 任务 ---\n{task}\n")
    agent.run(task)
