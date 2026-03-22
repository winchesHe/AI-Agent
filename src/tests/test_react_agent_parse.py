"""ReActAgent：解析层回归（多行 Finish 等）。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.hello_agents.react_agent import ReActAgent


@pytest.fixture
def agent() -> ReActAgent:
    return ReActAgent("t", MagicMock(), MagicMock())


def test_parse_output_multiline_finish_payload(agent: ReActAgent) -> None:
    text = """Thought: 列举工具
Action: Finish[目前可用工具有：
1. search: 智能网页搜索引擎
2. workspace_list_dir: 列出目录]
"""
    _thought, action = agent._parse_output(text)
    final = agent._parse_finish_payload(action)
    assert "1. search" in final
    assert "2. workspace_list_dir" in final


def test_parse_output_single_line_finish(agent: ReActAgent) -> None:
    text = "Thought: ok\nAction: Finish[单行答案]"
    _thought, action = agent._parse_output(text)
    assert agent._parse_finish_payload(action) == "单行答案"
