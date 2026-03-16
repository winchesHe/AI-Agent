"""
三国狼人杀 独立运行脚本。

从项目根目录执行:
  python -m src.scripts.run_three_kingdoms_werewolf
或:
  python src/scripts/run_three_kingdoms_werewolf.py

流程：夜晚（狼人讨论与击杀 → 预言家查验 → 女巫解药/毒药）→ 白天（公布结果 → 讨论 → 投票），
循环直至好人或狼人一方获胜。所有智能体间通信由消息中心（MsgHub / fanout_pipeline）驱动。
"""
import sys
from pathlib import Path

# 保证 src 在路径中，支持 python src/scripts/run_xxx.py 直接运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from core.llm.llm_client import HelloAgentsLLM
from core.agent.three_kingdoms_werewolf import ThreeKingdomsWerewolfGame

load_dotenv()

if __name__ == "__main__":
    # 使用与项目其他 agent 一致的 LLM 客户端（.env 中配置 API）
    llm_client = HelloAgentsLLM()
    # 创建游戏：1 狼人、1 预言家、1 女巫、1 村民，默认使用前 4 名三国人物
    game = ThreeKingdomsWerewolfGame(
        llm_client,
        num_werewolves=1,
        num_seers=1,
        num_witches=1,
        num_villagers=1,
    )
    winner = game.run()
    print(f"\n本局获胜方: {'好人' if winner == 'good' else '狼人'}")
