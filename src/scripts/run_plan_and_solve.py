"""
Plan-and-Solve Agent 独立运行脚本。
从项目根目录执行: python -m src.scripts.run_plan_and_solve
"""
from dotenv import load_dotenv

from core.agent.plan_and_solve_agent import PlanAndSolveAgent
from core.llm.llm_client import HelloAgentsLLM

load_dotenv()

if __name__ == "__main__":
    llm_client = HelloAgentsLLM()
    agent = PlanAndSolveAgent(llm_client=llm_client)

    question = "一个水果店周一卖出了15个苹果。周二卖出的苹果数量是周一的两倍。周三卖出的数量比周二少了5个。请问这三天总共卖出了多少个苹果？"
    print(f"\n--- Plan-and-Solve Agent ---\n问题: {question}\n")
    agent.run(question)
