"""
LangGraph 三步搜索问答助手（Understand → Search → Answer）。

每完成一个图节点后，会调用一次「Sub-agent」风格的监督 LLM 做核对（见 core.agent.langgraph_search_assistant.supervisor）。

环境变量：
  LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_ID
  SERPAPI_API_KEY（联网搜索，见 tools.web_search）

运行:
  python -m src.scripts.run_langgraph_search
  或 PYTHONPATH=src python src/scripts/run_langgraph_search.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from core.agent.langgraph_search_assistant import stream_with_supervisor
from core.llm.llm_client import HelloAgentsLLM

load_dotenv()


def main() -> None:
    print(
        "\n🔍 LangGraph 智能搜索助手\n"
        "流程：理解 → SerpApi 搜索 → 回答；每步结束会与监督模型核对。\n"
        "输入 quit 退出。\n"
    )
    llm = HelloAgentsLLM()
    tid = 0
    while True:
        q = input("\n🤔 您想了解什么: ").strip()
        if not q:
            continue
        if q.lower() in ("quit", "exit", "q"):
            print("再见。")
            break
        tid += 1
        print("\n" + "=" * 60)
        print("▶ LangGraph：understand → search → answer（每步后有 Sub-agent 核对）")
        merged, audits = stream_with_supervisor(llm, q, thread_id=f"session-{tid}")
        print("💡 最终回答:\n")
        print(merged.get("final_answer") or "(无)")
        print("\n" + "=" * 60)
        print("本轮监督摘要:", audits)


if __name__ == "__main__":
    main()
