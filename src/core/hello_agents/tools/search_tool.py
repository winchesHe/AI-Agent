"""多源网页搜索工具：Tavily / SerpApi / 混合与降级。"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .base_tool import BaseTool
from .tool_parameter import ToolParameter


class SearchTool(BaseTool):
    """
    智能混合搜索工具。

    支持 backend: hybrid（默认）、tavily、serpapi。
    密钥从参数或环境变量 `TAVILY_API_KEY`、`SERPAPI_API_KEY` 读取。
    """

    name = "search"
    description = (
        "智能网页搜索引擎。支持混合模式，按可用性在 Tavily 与 SerpApi 间选择与降级。"
    )

    def __init__(
        self,
        backend: str = "hybrid",
        tavily_key: Optional[str] = None,
        serpapi_key: Optional[str] = None,
    ) -> None:
        self.backend = (backend or "hybrid").lower()
        self.tavily_key = tavily_key or os.getenv("TAVILY_API_KEY")
        self.serpapi_key = serpapi_key or os.getenv("SERPAPI_API_KEY")
        self.available_backends: List[str] = []
        self.tavily_client: Any = None
        self._setup_backends()

    def _setup_backends(self) -> None:
        self.available_backends = []
        if self.tavily_key:
            try:
                from tavily import TavilyClient

                self.tavily_client = TavilyClient(api_key=self.tavily_key)
                self.available_backends.append("tavily")
            except ImportError:
                print("⚠️ Tavily 库未安装，可执行: pip install tavily-python")
        if self.serpapi_key:
            try:
                import serpapi  # noqa: F401

                self.available_backends.append("serpapi")
            except ImportError:
                print("⚠️ SerpApi 库未安装，可执行: pip install google-search-results")

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="搜索查询词",
                required=True,
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        raw = parameters.get("query")
        if raw is None:
            raw = parameters.get("input", "")
        if not isinstance(raw, str):
            raw = str(raw)
        query = raw.strip()
        if not query:
            return "❌ 错误: 搜索查询不能为空"

        if self.backend == "tavily":
            return self._search_tavily(query)
        if self.backend == "serpapi":
            return self._search_serpapi(query)
        return self._search_hybrid(query)

    def _search_hybrid(self, query: str) -> str:
        if "tavily" in self.available_backends:
            try:
                return self._search_tavily(query)
            except Exception as e:
                print(f"⚠️ Tavily 搜索失败: {e}")
                if "serpapi" in self.available_backends:
                    print("🔄 切换到 SerpApi 搜索")
                    try:
                        return self._search_serpapi(query)
                    except Exception as e2:
                        print(f"⚠️ SerpApi 搜索失败: {e2}")
        elif "serpapi" in self.available_backends:
            try:
                return self._search_serpapi(query)
            except Exception as e:
                print(f"⚠️ SerpApi 搜索失败: {e}")

        return (
            "❌ 没有可用的搜索源，请配置 TAVILY_API_KEY 或 SERPAPI_API_KEY，"
            "并安装 tavily-python / google-search-results。"
        )

    def _search_tavily(self, query: str) -> str:
        if self.tavily_client is None:
            raise RuntimeError("Tavily 客户端未初始化")
        response = self.tavily_client.search(
            query=query,
            search_depth="basic",
            include_answer=True,
            max_results=3,
        )
        answer = response.get("answer", "") or "未找到直接答案"
        result = f"🎯 Tavily AI 搜索结果:{answer}\n\n"
        for i, item in enumerate(response.get("results", [])[:3], 1):
            result += f"[{i}] {item.get('title', '')}\n"
            content = (item.get("content", "") or "")[:200]
            result += f"    {content}...\n"
            result += f"    来源: {item.get('url', '')}\n\n"
        return result

    def _search_serpapi(self, query: str) -> str:
        import serpapi

        if not self.serpapi_key:
            return "❌ SERPAPI_API_KEY 未配置"

        search = serpapi.GoogleSearch(
            {
                "q": query,
                "api_key": self.serpapi_key,
                "num": 3,
            }
        )
        results = search.get_dict()
        result = "🌐 SerpApi Google 搜索结果:\n\n"
        organic = results.get("organic_results") or []
        if not organic:
            return result + "未找到有机结果条目。"
        for i, res in enumerate(organic[:3], 1):
            result += f"[{i}] {res.get('title', '')}\n"
            result += f"    {res.get('snippet', '')}\n\n"
        return result
