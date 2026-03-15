"""
ReAct Agent 独立运行脚本。
从项目根目录执行: python -m src.scripts.run_re_act
"""
from dotenv import load_dotenv

from core.agent.re_act_agent import ReActAgent
from core.llm.llm_client import HelloAgentsLLM
from tools.web_search import ToolExecutor, search

load_dotenv()

if __name__ == "__main__":
    llm_client = HelloAgentsLLM()
    tool_executor = ToolExecutor()
    search_description = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    tool_executor.registerTool("Search", search_description, search)

    agent = ReActAgent(llm_client=llm_client, tool_executor=tool_executor, max_steps=5)

    question = "英伟达最新的GPU型号是什么？"
    print(f"\n--- ReAct Agent ---\n问题: {question}\n")
    result = agent.run(question)
    if result is not None:
        print(f"\n✅ 完成。最终答案: {result}")
    else:
        print("\n⚠️ 未得到最终答案。")
