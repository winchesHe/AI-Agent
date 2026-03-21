"""组装 StateGraph：START → understand → search → answer → END。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .nodes import build_nodes
from .state import SearchState

if TYPE_CHECKING:
    from core.llm.llm_client import HelloAgentsLLM


def create_search_assistant(llm: "HelloAgentsLLM") -> Any:
    """
    编译可执行的 LangGraph 应用（带内存 checkpointer，便于后续扩展多轮线程）。
    """
    understand, search_n, answer = build_nodes(llm)

    workflow = StateGraph(SearchState)
    workflow.add_node("understand", understand)
    workflow.add_node("search", search_n)
    workflow.add_node("answer", answer)

    workflow.add_edge(START, "understand")
    workflow.add_edge("understand", "search")
    workflow.add_edge("search", "answer")
    workflow.add_edge("answer", END)

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


def merge_state_delta(base: Dict[str, Any], delta: Dict[str, Any]) -> None:
    """将 LangGraph 单步 update 合并到用于监督展示的 dict（就地）。"""
    for k, v in delta.items():
        if k == "messages":
            base["messages"] = list(base.get("messages") or []) + list(v)
        else:
            base[k] = v
