"""流式执行图，并在每个节点结束后触发监督核对。"""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Tuple

from langchain_core.messages import HumanMessage

from core.llm.llm_client import HelloAgentsLLM

from .graph import create_search_assistant, merge_state_delta
from .supervisor import print_supervisor_banner, verify_step_after_node


def build_initial_state(user_text: str) -> Dict[str, Any]:
    return {
        "messages": [HumanMessage(content=user_text)],
        "user_query": "",
        "search_query": "",
        "search_results": "",
        "final_answer": "",
        "step": "",
    }


def stream_with_supervisor(
    llm: HelloAgentsLLM,
    user_text: str,
    thread_id: str = "default",
) -> Tuple[Dict[str, Any], List[Tuple[str, str, str]]]:
    """
    执行完整三步图；每完成一个节点立即调用监督 LLM 核对。

    返回 (最终合并状态, [(节点名, VERDICT, REASON), ...])。
    """
    app = create_search_assistant(llm)
    inputs = build_initial_state(user_text)
    merged: Dict[str, Any] = {
        "messages": list(inputs["messages"]),
        "user_query": inputs["user_query"],
        "search_query": inputs["search_query"],
        "search_results": inputs["search_results"],
        "final_answer": inputs["final_answer"],
        "step": inputs["step"],
    }
    config = {"configurable": {"thread_id": thread_id}}
    audit_log: List[Tuple[str, str, str]] = []

    for update in app.stream(inputs, config, stream_mode="updates"):
        for node_name, delta in update.items():
            merge_state_delta(merged, delta)
            verdict, reason = verify_step_after_node(llm, node_name, merged)
            print_supervisor_banner(node_name, verdict, reason)
            audit_log.append((node_name, verdict, reason))

    return merged, audit_log
