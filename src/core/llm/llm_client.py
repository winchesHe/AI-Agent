"""
HelloAgentsLLM：OpenAI Chat Completions 兼容客户端，支持多服务商、本地推理与自动检测。

环境变量（常用）：
  - 通用：LLM_MODEL_ID, LLM_API_KEY, LLM_BASE_URL, LLM_TIMEOUT
  - OpenAI：OPENAI_API_KEY
  - ModelScope：MODELSCOPE_API_KEY
  - 智谱：ZHIPU_API_KEY

本地 OpenAI 兼容服务（无需真实密钥，可传占位非空字符串或通过环境设置 LLM_API_KEY）：
  - VLLM：典型基地址 ``http://localhost:8000/v1``（启动命令见 VLLM 文档）
  - Ollama：典型基地址 ``http://localhost:11434/v1``（与 ``ollama run <model>`` 对应）

使用 ``provider="auto"``（默认）时，按环境变量与 URL 启发式推断服务商。

流式相关：

  - 部分企业网关会缓冲 SSE，客户端会「整段一次收到」，看起来像非流式。
  - 可设 ``HELLOAGENTS_STREAM_SMOOTH_MS``（毫秒，>0）或调用 ``stream_invoke(..., stream_smooth_ms=...)``：
    将每个 API 返回的文本片段拆成单字并间隔 sleep，便于在终端看到逐字效果（不改变网关行为）。
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, Iterator, List, Optional, Tuple
from urllib.parse import urlparse

from dotenv import load_dotenv
from openai import OpenAI

from tools.web_search import ToolExecutor, search

load_dotenv()

_VALID_PROVIDERS = frozenset(
    {"openai", "modelscope", "zhipu", "vllm", "ollama", "local"}
)

_DEFAULT_MODEL_MODELSCOPE = "Qwen/Qwen2.5-VL-72B-Instruct"
_DEFAULT_MODEL_ZHIPU = "glm-4-flash"


class HelloAgentsLLM:
    """
    为本书 "Hello Agents" 定制的 LLM 客户端。
    调用任何兼容 OpenAI Chat Completions 接口的服务，默认使用流式响应。
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        apiKey: Optional[str] = None,
        base_url: Optional[str] = None,
        baseUrl: Optional[str] = None,
        provider: Optional[str] = "auto",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        if "temperature" in kwargs and temperature is None:
            temperature = kwargs.pop("temperature")
        else:
            kwargs.pop("temperature", None)
        if "max_tokens" in kwargs and max_tokens is None:
            max_tokens = kwargs.pop("max_tokens")
        else:
            kwargs.pop("max_tokens", None)
        if kwargs:
            raise TypeError(
                f"HelloAgentsLLM 收到未识别的关键字参数: {sorted(kwargs.keys())}"
            )

        self.temperature = float(0.0 if temperature is None else temperature)
        self.max_tokens = max_tokens
        self.timeout = int(timeout or int(os.getenv("LLM_TIMEOUT", "60")))

        raw_key = api_key if api_key is not None else apiKey
        raw_base = base_url if base_url is not None else baseUrl

        prov_raw = (provider or "auto").strip().lower()
        if prov_raw == "auto":
            self.provider = self._auto_detect_provider(raw_key, raw_base)
        else:
            if prov_raw not in _VALID_PROVIDERS:
                raise ValueError(
                    f"未知的 provider={provider!r}，可选: {', '.join(sorted(_VALID_PROVIDERS))}, auto"
                )
            self.provider = prov_raw

        api_resolved, base_resolved, used_default_base = self._resolve_credentials(
            raw_key, raw_base
        )
        self.model = model or os.getenv("LLM_MODEL_ID") or self._default_model_for_provider()
        if not self.model:
            raise ValueError(
                "未设置模型 ID：请在构造函数传入 model，或设置环境变量 LLM_MODEL_ID。"
            )
        if not api_resolved:
            raise ValueError(self._missing_key_help())
        if not base_resolved:
            raise ValueError(self._missing_base_help())

        self.client = self._build_openai_client(api_resolved, base_resolved, self.timeout)
        self._log_resolution(used_default_base, base_resolved)

    def _default_model_for_provider(self) -> Optional[str]:
        if self.provider == "modelscope":
            return _DEFAULT_MODEL_MODELSCOPE
        if self.provider == "zhipu":
            return _DEFAULT_MODEL_ZHIPU
        return None

    def _missing_key_help(self) -> str:
        hints = {
            "openai": "请设置 OPENAI_API_KEY 或通用 LLM_API_KEY。",
            "modelscope": "请设置 MODELSCOPE_API_KEY 或 LLM_API_KEY。",
            "zhipu": "请设置 ZHIPU_API_KEY 或 LLM_API_KEY。",
            "vllm": "本地 VLLM 可设置任意非空 LLM_API_KEY（如 vllm），或传入 api_key。",
            "ollama": "本地 Ollama 可设置任意非空 LLM_API_KEY（如 ollama），或传入 api_key。",
            "local": "请设置 LLM_API_KEY（可为占位非空串）或传入 api_key。",
        }
        extra = hints.get(self.provider, "请设置 LLM_API_KEY 或对应服务商的环境变量。")
        return f"缺少 API 密钥（provider={self.provider}）。{extra}"

    def _missing_base_help(self) -> str:
        return (
            f"缺少服务基地址（provider={self.provider}）。"
            "请传入 base_url / baseUrl，或设置 LLM_BASE_URL；"
            "云端服务商也可使用各 provider 的默认基地址（需已配置密钥）。"
        )

    def _build_openai_client(self, api_key: str, base_url: str, timeout: int) -> OpenAI:
        return OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    def _log_resolution(self, used_default_base: bool, base_resolved: str) -> None:
        try:
            host = urlparse(base_resolved).hostname or base_resolved
        except Exception:
            host = "(unparsed)"
        print(
            f"[HelloAgentsLLM] provider={self.provider} "
            f"base_url_defaulted={used_default_base} endpoint_host={host}"
        )

    def _auto_detect_provider(
        self, api_key: Optional[str], base_url: Optional[str]
    ) -> str:
        if os.getenv("MODELSCOPE_API_KEY"):
            return "modelscope"
        if os.getenv("OPENAI_API_KEY"):
            return "openai"
        if os.getenv("ZHIPU_API_KEY"):
            return "zhipu"

        actual_key = api_key or os.getenv("LLM_API_KEY")
        actual_base = base_url or os.getenv("LLM_BASE_URL") or ""

        if actual_base:
            lower = actual_base.lower()
            if "api-inference.modelscope.cn" in lower:
                return "modelscope"
            if "open.bigmodel.cn" in lower:
                return "zhipu"
            if "api.openai.com" in lower:
                return "openai"
            if "localhost" in lower or "127.0.0.1" in lower:
                if ":11434" in lower:
                    return "ollama"
                if ":8000" in lower:
                    return "vllm"
                return "local"

        if actual_key:
            if actual_key.startswith("ms-"):
                return "modelscope"

        return "openai"

    def _resolve_credentials(
        self, api_key: Optional[str], base_url: Optional[str]
    ) -> Tuple[Optional[str], Optional[str], bool]:
        used_default = False
        p = self.provider

        if p == "openai":
            key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
            base = base_url or os.getenv("LLM_BASE_URL")
            if not base:
                base = "https://api.openai.com/v1"
                used_default = True
            return key, base, used_default

        if p == "modelscope":
            key = api_key or os.getenv("MODELSCOPE_API_KEY") or os.getenv("LLM_API_KEY")
            base = base_url or os.getenv("LLM_BASE_URL")
            if not base:
                base = "https://api-inference.modelscope.cn/v1/"
                used_default = True
            return key, base, used_default

        if p == "zhipu":
            key = api_key or os.getenv("ZHIPU_API_KEY") or os.getenv("LLM_API_KEY")
            base = base_url or os.getenv("LLM_BASE_URL")
            if not base:
                base = "https://open.bigmodel.cn/api/paas/v4"
                used_default = True
            return key, base, used_default

        if p == "vllm":
            key = api_key or os.getenv("LLM_API_KEY") or "vllm"
            base = base_url or os.getenv("LLM_BASE_URL")
            if not base:
                base = "http://localhost:8000/v1"
                used_default = True
            return key, base, used_default

        if p == "ollama":
            key = api_key or os.getenv("LLM_API_KEY") or "ollama"
            base = base_url or os.getenv("LLM_BASE_URL")
            if not base:
                base = "http://localhost:11434/v1"
                used_default = True
            return key, base, used_default

        if p == "local":
            key = api_key or os.getenv("LLM_API_KEY") or "local"
            base = base_url or os.getenv("LLM_BASE_URL")
            return key, base, used_default

        return None, None, False

    def _build_chat_completion_kwargs(
        self,
        messages: List[Dict[str, Any]],
        *,
        stream: bool,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """合并默认温度、max_tokens 与用户传入的 OpenAI 兼容参数。"""
        temperature = kwargs.pop("temperature", None)
        max_tokens_kw = kwargs.pop("max_tokens", None)
        model = kwargs.pop("model", None) or self.model
        eff_temp = self.temperature if temperature is None else float(temperature)
        eff_max = self.max_tokens if max_tokens_kw is None else max_tokens_kw
        create_kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": eff_temp,
            "stream": stream,
            **kwargs,
        }
        if eff_max is not None:
            create_kwargs["max_tokens"] = eff_max
        return create_kwargs

    def invoke(self, messages: List[Dict[str, Any]], **kwargs: Any) -> str:
        """非流式 Chat Completions，返回 assistant 文本。"""
        create_kwargs = self._build_chat_completion_kwargs(
            messages, stream=False, **kwargs
        )
        response = self.client.chat.completions.create(**create_kwargs)
        return (response.choices[0].message.content or "").strip()

    def stream_invoke(
        self, messages: List[Dict[str, Any]], **kwargs: Any
    ) -> Iterator[str]:
        """流式 Chat Completions，逐块产出文本增量。

        额外参数（不会传给 OpenAI API）：

        - ``stream_smooth_ms``: 每个字符间隔的毫秒数；>0 时将每个 delta 片段拆成单字并
          ``sleep``，用于网关缓冲导致「整块到达」时在终端仍能看出逐字输出。
          未传时读环境变量 ``HELLOAGENTS_STREAM_SMOOTH_MS``（默认 0 表示关闭）。
        """
        smooth_kw = kwargs.pop("stream_smooth_ms", None)
        if smooth_kw is None:
            smooth_ms = float(os.getenv("HELLOAGENTS_STREAM_SMOOTH_MS", "0") or 0)
        else:
            smooth_ms = float(smooth_kw)

        create_kwargs = self._build_chat_completion_kwargs(
            messages, stream=True, **kwargs
        )
        stream_resp = self.client.chat.completions.create(**create_kwargs)
        for chunk in stream_resp:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta is None:
                continue
            piece = delta.content or ""
            if not piece:
                continue
            if smooth_ms > 0:
                for ch in piece:
                    yield ch
                    time.sleep(smooth_ms / 1000.0)
            else:
                yield piece

    def think(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        stream: bool = True,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        """
        调用大语言模型进行思考，并返回其响应。
        stream=False 时一次性返回全文，适合多轮对话循环中避免交错打印。
        """
        eff_temp = self.temperature if temperature is None else float(temperature)
        eff_max = self.max_tokens if max_tokens is None else max_tokens

        print(f"🧠 正在调用 {self.model} 模型（provider={self.provider}）...")
        try:
            create_kwargs: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": eff_temp,
                "stream": stream,
            }
            if eff_max is not None:
                create_kwargs["max_tokens"] = eff_max

            response = self.client.chat.completions.create(**create_kwargs)

            if not stream:
                text = (response.choices[0].message.content or "").strip()
                print("✅ 大语言模型响应成功（非流式）。")
                return text

            print("✅ 大语言模型响应成功:")
            collected_content = []
            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                print(content, end="", flush=True)
                collected_content.append(content)
            print()
            return "".join(collected_content)

        except Exception as e:
            print(f"❌ 调用LLM API时发生错误: {e}")
            return None


# --- 客户端使用示例 ---
if __name__ == "__main__":
    toolExecutor = ToolExecutor()
    search_description = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    toolExecutor.registerTool("Search", search_description, search)

    print("\n--- 可用的工具 ---")
    print(toolExecutor.getAvailableTools())

    print("\n--- 执行 Action: Search['英伟达最新的GPU型号是什么'] ---")
    tool_name = "Search"
    tool_input = "英伟达最新的GPU型号是什么"

    tool_function = toolExecutor.getTool(tool_name)
    if tool_function:
        observation = tool_function(tool_input)
        print("--- 观察 (Observation) ---")
        print(observation)
    else:
        print(f"错误:未找到名为 '{tool_name}' 的工具。")
