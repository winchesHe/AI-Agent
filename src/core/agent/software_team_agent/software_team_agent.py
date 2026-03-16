"""
软件开发团队 Agent：需求分析 → 编码 → 代码审查 → 用户测试，轮询协作直至 TERMINATE。
使用旧版 autogen (autogen.agentchat) API，兼容 Python 3.9 与当前 pip 安装的 autogen-agentchat。
"""
from autogen.agentchat import GroupChat, GroupChatManager

from .agents import (
    create_code_reviewer,
    create_engineer,
    create_product_manager,
    create_user_proxy,
)
from .model_client import get_llm_config

# 默认任务描述（比特币价格显示应用）
DEFAULT_TASK = """我们需要开发一个比特币价格显示应用，具体要求如下：
核心功能：
- 实时显示比特币当前价格（USD）
- 显示24小时价格变化趋势（涨跌幅和涨跌额）
- 提供价格刷新功能

技术要求：
- 使用 Streamlit 框架创建 Web 应用
- 界面简洁美观，用户友好
- 添加适当的错误处理和加载状态

请团队协作完成这个任务，从需求分析到最终实现。"""


def _is_terminate(msg):
    content = msg.get("content") or ""
    if isinstance(content, list):
        content = " ".join(
            c.get("text", "") if isinstance(c, dict) else str(c) for c in content
        )
    return "TERMINATE" in str(content).upper()


def run_software_development_team(task: str = DEFAULT_TASK):
    """
    初始化 llm_config 与四角色智能体，构建轮询群聊并运行协作任务。
    当任意消息包含 TERMINATE 或达到 max_round 时结束。
    """
    print("🔧 正在初始化模型配置...")
    llm_config = get_llm_config()

    print("👥 正在创建智能体团队...")
    product_manager = create_product_manager(llm_config)
    engineer = create_engineer(llm_config)
    code_reviewer = create_code_reviewer(llm_config)
    user_proxy = create_user_proxy()

    groupchat = GroupChat(
        agents=[product_manager, engineer, code_reviewer, user_proxy],
        messages=[],
        max_round=20,
        speaker_selection_method="round_robin",
    )
    manager = GroupChatManager(
        groupchat=groupchat,
        llm_config=llm_config,
        is_termination_msg=_is_terminate,
    )

    print("🚀 启动 AutoGen 软件开发团队协作...")
    print("=" * 60)
    user_proxy.initiate_chat(manager, message=task)
    print("=" * 60)
    print("✅ 团队协作完成！")
    print(f"\n📋 协作结果摘要：参与智能体数量 4 个，消息数 {len(groupchat.messages)}")
    return groupchat.messages


def run(task: str = DEFAULT_TASK):
    """同步入口：在脚本中直接调用 run() 时使用。"""
    return run_software_development_team(task=task)
