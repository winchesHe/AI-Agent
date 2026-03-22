"""Multi-turn chat session with bounded conversation history.

Provides ``ChatSession`` for managing turn-by-turn message history and
``run_chat_loop`` for the interactive ``chat`` subcommand REPL.
"""
from __future__ import annotations

import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.hello_agents.message import Message
from core.runtime.config import LoopConfig

# ---------------------------------------------------------------------------
# Chat session
# ---------------------------------------------------------------------------

_EXIT_KEYWORDS: set[str] = {"exit", "quit", "bye", "/exit", "/quit"}


class ChatSession:
    """Bounded multi-turn conversation history.

    Keeps at most *max_history* messages, automatically trimming the oldest
    entries when the limit is exceeded.
    """

    def __init__(self, max_history: int = 20) -> None:
        self._max_history = max_history
        self._history: list[Message] = []

    # ---- public API ----

    def add_user_message(self, content: str) -> None:
        """Append a user message and trim if necessary."""
        self._history.append(
            Message(content=content, role="user", timestamp=datetime.now()),
        )
        self._trim()

    def add_assistant_message(self, content: str) -> None:
        """Append an assistant message and trim if necessary."""
        self._history.append(
            Message(content=content, role="assistant", timestamp=datetime.now()),
        )
        self._trim()

    def get_history(self) -> list[Message]:
        """Return a shallow copy of the current history."""
        return list(self._history)

    def get_messages_for_llm(self) -> list[dict[str, str]]:
        """Return history as OpenAI-compatible message dicts."""
        return [msg.to_dict() for msg in self._history]

    def clear(self) -> None:
        """Reset the conversation history."""
        self._history.clear()

    # ---- internal ----

    def _trim(self) -> None:
        """Keep only the most recent *max_history* messages."""
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]


# ---------------------------------------------------------------------------
# Interactive REPL
# ---------------------------------------------------------------------------

def run_chat_loop(
    llm: Any,
    tool_registry: Any,
    loop_config: LoopConfig,
    trace_format: Optional[str] = None,
) -> None:
    """Run an interactive chat REPL.

    Creates a :class:`ChatSession` bounded by ``loop_config.max_history_messages``
    and drives each turn through a :class:`LoopDriver`.

    Parameters
    ----------
    llm:
        The LLM backend instance.
    tool_registry:
        Registry of available tools for the agent loop.
    loop_config:
        Runtime loop configuration (budget, history cap, …).
    trace_format:
        If set (e.g. ``"human"`` or ``"json"``), print trace info after
        each assistant turn.
    """
    # Deferred import – LoopDriver may not exist yet during early bootstrap.
    from core.runtime.loop_driver import LoopDriver  # noqa: WPS433

    session = ChatSession(max_history=loop_config.max_history_messages)

    print("Welcome to Hello-Agent chat! Type 'exit' or 'quit' to leave.")
    print()

    try:
        while True:
            try:
                user_input = input("You> ").strip()
            except EOFError:
                print("\nBye!")
                break

            if not user_input:
                continue

            if user_input.lower() in _EXIT_KEYWORDS:
                print("Bye!")
                break

            session.add_user_message(user_input)

            driver = LoopDriver(
                llm=llm,
                tool_registry=tool_registry,
                loop_config=loop_config,
            )
            result = driver.run(user_input)

            session.add_assistant_message(result.answer)

            print(f"Assistant> {result.answer}")

            if trace_format:
                if trace_format == "json":
                    print(result.trace.to_json())
                else:
                    print(result.trace.to_human_readable())

    except KeyboardInterrupt:
        print("\nInterrupted. Bye!")
