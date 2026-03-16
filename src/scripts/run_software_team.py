"""
软件开发团队 (AutoGen) 独立运行脚本。
从项目根目录执行: python -m src.scripts.run_software_team
或: python src/scripts/run_software_team.py

流程：ProductManager → Engineer → CodeReviewer → UserProxy，轮询协作；
当 UserProxy 在控制台输入 TERMINATE 时结束。
"""
import sys
from pathlib import Path

# 保证 src 在路径中，支持 python src/scripts/run_xxx.py 直接运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from core.agent.software_team_agent import run

load_dotenv()

if __name__ == "__main__":
    run()
