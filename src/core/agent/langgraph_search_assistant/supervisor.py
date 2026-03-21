"""
步骤监督（Sub-agent 语义）：每完成一个图节点后，用独立 LLM 调用核对状态是否满足该步验收标准。

与 Cursor 里真正的 Task subagent 不同，运行时可复现的「核对」统一走本模块，避免在 Python 内嵌 IDE 工具。
"""

from __future__ import annotations

import re
from typing import Any, Dict, Tuple

from core.llm.llm_client import HelloAgentsLLM


def _fmt_messages(messages: list) -> str:
    lines = []
    for m in messages or []:
        role = getattr(m, "type", None) or getattr(m, "role", "unknown")
        content = getattr(m, "content", str(m))
        lines.append(f"- [{role}] {content[:2000]}")
    return "\n".join(lines) if lines else "(无)"


def state_audit_blob(state: Dict[str, Any], max_chars: int = 6000) -> str:
    """将当前状态压成可送入监督模型的文本。"""
    parts = [
        f"user_query:\n{state.get('user_query', '')}",
        f"search_query:\n{state.get('search_query', '')}",
        f"search_results:\n{str(state.get('search_results', ''))[:3000]}",
        f"final_answer:\n{str(state.get('final_answer', ''))[:2000]}",
        f"step:\n{state.get('step', '')}",
        "messages:\n" + _fmt_messages(state.get("messages")),
    ]
    text = "\n\n".join(parts)
    return text[:max_chars]


_SUP_PROMPTS = {
    "understand": """你是严格的流程监督员（Sub-agent）。刚完成节点「理解用户查询」。
请根据下列状态判断：是否已总结用户需求，且 search_query 非空、适合用于网页搜索。
输出严格三行：
VERDICT: PASS 或 FAIL
REASON: 一句话理由
CHECKS: 你检查了哪些要点（逗号分隔）""",
    "search": """你是严格的流程监督员（Sub-agent）。刚完成节点「联网搜索」。
判断：search_results 是否有实质内容；若 step 为 search_failed，是否仍记录了失败原因。
输出严格三行：
VERDICT: PASS 或 FAIL
REASON: 一句话理由
CHECKS: 要点列表""",
    "answer": """你是严格的流程监督员（Sub-agent）。刚完成节点「生成最终回答」。
判断：final_answer 是否非空，且与用户意图相关（允许基于模型知识回退）。
输出严格三行：
VERDICT: PASS 或 FAIL
REASON: 一句话理由
CHECKS: 要点列表""",
}


def verify_step_after_node(
    llm: HelloAgentsLLM,
    node_name: str,
    state: Dict[str, Any],
) -> Tuple[str, str]:
    """
    对刚结束的节点做核对。返回 (VERDICT, REASON)。
    node_name 为 understand / search / answer。
    """
    spec = _SUP_PROMPTS.get(node_name)
    if not spec:
        return "SKIP", "无该节点的监督模板"

    user = spec + "\n\n--- 当前状态 ---\n" + state_audit_blob(state)
    text = llm.think(
        [
            {
                "role": "system",
                "content": "你只输出要求的三行格式，不要多余解释。",
            },
            {"role": "user", "content": user},
        ],
        temperature=0,
        stream=False,
    ) or ""

    verdict = "FAIL"
    m = re.search(r"VERDICT:\s*(\w+)", text, re.I)
    if m and m.group(1).upper() == "PASS":
        verdict = "PASS"
    reason_m = re.search(r"REASON:\s*(.+)", text)
    reason = reason_m.group(1).strip() if reason_m else text[:200]
    return verdict, reason


def print_supervisor_banner(node_name: str, verdict: str, reason: str) -> None:
    bar = "=" * 60
    print(f"\n{bar}\n Sub-agent 核对 · 节点「{node_name}」\n{bar}")
    print(f"  结果: {verdict}")
    print(f"  说明: {reason}\n{bar}\n")
