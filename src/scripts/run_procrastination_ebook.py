"""
拖延症心理学科普电子书：双智能体（作家 + 心理学家）RolePlaying 风格协作示例。

依赖 OpenAI 兼容接口（与项目其他模块相同的环境变量）：
  LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_ID

从项目根目录执行:
  python -m src.scripts.run_procrastination_ebook
或:
  python src/scripts/run_procrastination_ebook.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from core.agent.procrastination_ebook_roleplay import (
    TASK_PROMPT,
    run_procrastination_ebook_collab,
)
from core.llm.llm_client import HelloAgentsLLM

load_dotenv()

if __name__ == "__main__":
    print("\n协作任务（task_prompt）:\n")
    print(TASK_PROMPT)
    print()
    llm = HelloAgentsLLM()
    run_procrastination_ebook_collab(llm=llm, chat_turn_limit=30)
