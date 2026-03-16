"""
Reflection Agent 独立运行脚本。
从项目根目录执行: python -m src.scripts.run_reflection 或 python src/scripts/run_reflection.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from core.agent.reflection_agent import ReflectionAgent
from core.llm.llm_client import HelloAgentsLLM

load_dotenv()

if __name__ == "__main__":
    llm_client = HelloAgentsLLM()
    agent = ReflectionAgent(llm_client=llm_client, max_iterations=3)

    task = "编写一个Python函数，找出1到n之间所有的素数 (prime numbers)。"
    print(f"\n--- Reflection Agent ---\n任务: {task}\n")
    agent.run(task)
