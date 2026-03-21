"""LangGraph 三步搜索助手：全局状态 Schema（教材 6.5.2）。"""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class SearchState(TypedDict, total=False):
    """贯穿 Understand → Search → Answer 的共享状态。"""

    messages: Annotated[list, add_messages]
    user_query: str
    search_query: str
    search_results: str
    final_answer: str
    step: str
