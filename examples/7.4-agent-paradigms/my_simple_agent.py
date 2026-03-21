# my_simple_agent.py
import path_setup  # noqa: F401

from typing import Iterator, Optional

from hello_agents import Config, HelloAgentsLLM, Message, SimpleAgent, ToolRegistry


class MySimpleAgent(SimpleAgent):
    """
    重写的简单对话Agent
    展示如何基于框架基类构建自定义Agent
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        tool_registry: Optional[ToolRegistry] = None,
        enable_tool_calling: bool = True,
    ):
        super().__init__(
            name,
            llm,
            system_prompt,
            config,
            tool_registry=tool_registry,
            enable_tool_calling=enable_tool_calling,
        )
        print(
            f"✅ {name} 初始化完成，工具调用: "
            f"{'启用' if self.enable_tool_calling else '禁用'}"
        )

    def run(self, input_text: str, max_tool_iterations: int = 3, **kwargs) -> str:
        """重写的运行方法 - 实现简单对话逻辑，支持可选工具调用"""
        print(f"🤖 {self.name} 正在处理: {input_text}")
        out = super().run(
            input_text, max_tool_iterations=max_tool_iterations, **kwargs
        )
        print(f"✅ {self.name} 响应完成")
        return out

    def stream_run(self, input_text: str, **kwargs) -> Iterator[str]:
        """自定义的流式运行方法"""
        print(f"🌊 {self.name} 开始流式处理: {input_text}")

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        for msg in self._history:
            messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": input_text})

        full_response = ""
        print("📝 实时响应: ", end="")
        for chunk in self.llm.stream_invoke(messages, **kwargs):
            full_response += chunk
            print(chunk, end="", flush=True)
            yield chunk

        print()
        self.add_message(Message(content=input_text, role="user"))
        self.add_message(Message(content=full_response, role="assistant"))
        print(f"✅ {self.name} 流式响应完成")

    def add_tool(self, tool) -> None:
        """添加工具到Agent（便利方法）"""
        super().add_tool(tool)
        print(f"🔧 工具 '{getattr(tool, 'name', tool)}' 已添加")


if __name__ == "__main__":
    print(
        "本文件只定义 MySimpleAgent，没有默认「跑一轮对话」的入口。\n"
        "直接执行它会正常退出且几乎无输出（以前就是这种情况）。\n"
        "要跑完整示例请用:\n"
        "  python examples/7.4-agent-paradigms/test_simple_agent.py\n"
        "或在其他脚本里: from my_simple_agent import MySimpleAgent 后自行 .run(...)。"
    )
