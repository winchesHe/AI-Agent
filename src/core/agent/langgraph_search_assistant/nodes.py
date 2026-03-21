"""三步工作流节点：理解 → SerpApi 搜索 → 回答（教材 6.5.2，搜索层用项目内 `tools.web_search`）。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.messages import AIMessage, HumanMessage

from tools.web_search import search as serp_search

from .state import SearchState

if TYPE_CHECKING:
    from core.llm.llm_client import HelloAgentsLLM


def _last_user_text(state: SearchState) -> str:
    for m in reversed(state.get("messages") or []):
        if isinstance(m, HumanMessage):
            return (m.content or "").strip()
    return ""


def build_nodes(llm: "HelloAgentsLLM"):
    """绑定 LLM 的节点工厂（便于测试注入同一客户端）。"""

    def understand_query_node(state: SearchState) -> dict:
        user_message = _last_user_text(state) or (
            state.get("messages")[-1].content if state.get("messages") else ""
        )

        understand_prompt = f"""分析用户的查询："{user_message}"
请完成两个任务：
1. 简洁总结用户想要了解什么
2. 生成最适合搜索引擎的关键词（中英文均可，要精准）

格式：
理解：[用户需求总结]
搜索词：[最佳搜索关键词]"""

        response_text = llm.think(
            [
                {"role": "system", "content": understand_prompt},
                {"role": "user", "content": "请按上述格式输出。"},
            ],
            temperature=0.3,
            stream=False,
        ) or ""

        search_query = user_message
        if "搜索词：" in response_text:
            search_query = response_text.split("搜索词：", 1)[1].strip().split("\n")[0].strip()

        return {
            "user_query": response_text,
            "search_query": search_query,
            "step": "understood",
            "messages": [
                AIMessage(content=f"我将为您搜索：{search_query}\n\n理解摘要：{response_text[:500]}")
            ],
        }

    def serp_search_node(state: SearchState) -> dict:
        q = (state.get("search_query") or "").strip() or _last_user_text(state)
        try:
            print(f"🔍 正在搜索: {q}")
            raw = serp_search(q)
        except Exception as e:
            raw = f"搜索时发生错误: {e}"

        failed = (
            "SERPAPI_API_KEY 未" in raw
            or "搜索时发生错误" in raw
            or raw.startswith("错误:")
        )
        if failed:
            return {
                "search_results": raw,
                "step": "search_failed",
                "messages": [
                    AIMessage(content="❌ 搜索遇到问题，将在回答阶段尽量基于模型知识回退。")
                ],
            }

        return {
            "search_results": raw,
            "step": "searched",
            "messages": [AIMessage(content="✅ 搜索完成！正在整理答案...")],
        }

    def generate_answer_node(state: SearchState) -> dict:
        uq = state.get("user_query") or _last_user_text(state)
        if state.get("step") == "search_failed":
            fallback_prompt = (
                "搜索 API 不可用或失败，请基于你的知识尽力回答，并在开头简短说明无法联网。\n"
                f"用户问题与理解：\n{uq}"
            )
            response_text = llm.think(
                [
                    {"role": "system", "content": fallback_prompt},
                    {"role": "user", "content": "请直接给出完整回答。"},
                ],
                temperature=0.5,
                stream=False,
            ) or ""
        else:
            sr = state.get("search_results") or ""
            answer_prompt = (
                "基于以下搜索结果为用户提供完整、准确、有条理的回答（可用 Markdown 小标题）。\n"
                f"用户问题与理解：\n{uq}\n\n"
                f"搜索结果：\n{sr}\n\n"
                "请综合搜索结果作答；若结果不充分请明确说明。"
            )
            response_text = llm.think(
                [
                    {"role": "system", "content": answer_prompt},
                    {"role": "user", "content": "请输出最终回答。"},
                ],
                temperature=0.5,
                stream=False,
            ) or ""

        return {
            "final_answer": response_text,
            "step": "completed",
            "messages": [AIMessage(content=response_text)],
        }

    return understand_query_node, serp_search_node, generate_answer_node
