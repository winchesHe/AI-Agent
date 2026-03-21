# my_advanced_search.py
from __future__ import annotations

import os
from typing import Any, List

import path_setup  # noqa: F401

from hello_agents import ToolRegistry


class MyAdvancedSearchTool:
    """
    自定义高级搜索工具类：多源整合与顺序尝试（教材 7.5.3 风格）。
    """

    def __init__(self) -> None:
        self.name = "my_advanced_search"
        self.description = "智能搜索工具，支持多个搜索源，自动选择最佳结果"
        self.search_sources: List[str] = []
        self.tavily_client: Any = None
        self._setup_search_sources()

    def _setup_search_sources(self) -> None:
        if os.getenv("TAVILY_API_KEY"):
            try:
                from tavily import TavilyClient

                self.tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
                self.search_sources.append("tavily")
                print("✅ Tavily 搜索源已启用")
            except ImportError:
                print("⚠️ Tavily 库未安装")

        if os.getenv("SERPAPI_API_KEY"):
            try:
                import serpapi  # noqa: F401

                self.search_sources.append("serpapi")
                print("✅ SerpApi 搜索源已启用")
            except ImportError:
                print("⚠️ SerpApi 库未安装")

        if self.search_sources:
            print(f"🔧 可用搜索源: {', '.join(self.search_sources)}")
        else:
            print("⚠️ 没有可用的搜索源，请配置 API 密钥")

    def search(self, query: str) -> str:
        if not query.strip():
            return "❌ 错误: 搜索查询不能为空"

        if not self.search_sources:
            return """❌ 没有可用的搜索源，请配置以下 API 密钥之一:

1. Tavily API: 设置环境变量 TAVILY_API_KEY
   获取地址: https://tavily.com/

2. SerpAPI: 设置环境变量 SERPAPI_API_KEY
   获取地址: https://serpapi.com/

配置后重新运行程序。"""

        print(f"🔍 开始智能搜索: {query}")

        for source in self.search_sources:
            try:
                if source == "tavily":
                    result = self._search_with_tavily(query)
                    if result and "未找到" not in result:
                        return f"📊 Tavily AI 搜索结果:\n\n{result}"

                elif source == "serpapi":
                    result = self._search_with_serpapi(query)
                    if result and "未找到" not in result:
                        return f"🌐 SerpApi Google 搜索结果:\n\n{result}"

            except Exception as e:
                print(f"⚠️ {source} 搜索失败: {e}")
                continue

        return "❌ 所有搜索源都失败了，请检查网络连接和 API 密钥配置"

    def _search_with_tavily(self, query: str) -> str:
        if self.tavily_client is None:
            return ""
        response = self.tavily_client.search(query=query, max_results=3)

        if response.get("answer"):
            result = f"💡 AI 直接答案:{response['answer']}\n\n"
        else:
            result = ""

        result += "🔗 相关结果:\n"
        for i, item in enumerate(response.get("results", [])[:3], 1):
            result += f"[{i}] {item.get('title', '')}\n"
            content = (item.get("content", "") or "")[:150]
            result += f"    {content}...\n\n"

        return result

    def _search_with_serpapi(self, query: str) -> str:
        import serpapi

        search = serpapi.GoogleSearch(
            {
                "q": query,
                "api_key": os.getenv("SERPAPI_API_KEY"),
                "num": 3,
            }
        )
        results = search.get_dict()

        result = "🔗 Google 搜索结果:\n"
        organic = results.get("organic_results") or []
        if not organic:
            return "未找到有机结果。"
        for i, res in enumerate(organic[:3], 1):
            result += f"[{i}] {res.get('title', '')}\n"
            result += f"    {res.get('snippet', '')}\n\n"

        return result


def create_advanced_search_registry() -> ToolRegistry:
    registry = ToolRegistry()
    search_tool = MyAdvancedSearchTool()
    registry.register_function(
        name="advanced_search",
        description=(
            "高级搜索工具，整合 Tavily 和 SerpAPI 多个搜索源，提供更全面的搜索结果"
        ),
        func=search_tool.search,
    )
    return registry
