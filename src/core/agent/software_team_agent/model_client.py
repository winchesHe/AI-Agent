"""AutoGen 模型配置，通过环境变量管理 API（兼容旧版 autogen）。"""
import os

from autogen.oai.openai_utils import get_config_list


def get_llm_config():
    """创建 llm_config 字典，供 AssistantAgent / GroupChatManager 使用。"""
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    base_url = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_API_BASE")
    model = os.getenv("LLM_MODEL_ID", "gpt-4o")
    config_list = get_config_list(
        api_keys=[api_key],
        base_urls=[base_url] if base_url else None,
    )
    if not config_list:
        raise ValueError("请在 .env 中配置 LLM_API_KEY（或 OPENAI_API_KEY）")
    return {
        "config_list": config_list,
        "model": model,
        "temperature": 0,
    }
