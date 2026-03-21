# Quickstart: 7.5 工具系统

## 环境

```bash
export PYTHONPATH=src
pip install -r requirements.txt
```

可选：在 `.env` 中配置 `TAVILY_API_KEY`、`SERPAPI_API_KEY`、`OPENAI_API_KEY`。

## 运行示例

```bash
cd examples/7.5-tool-system
python test_my_calculator.py
python test_async_tools.py
python tool_chain_manager.py   # 需要至少一种搜索密钥以完成第一步
python test_advanced_search.py
```

## 代码入口

- 核心：`src/core/hello_agents/tool_registry.py`、`tools/base_tool.py`、`tools/search_tool.py`
- 工具链：`src/core/hello_agents/tool_chain.py`
- 异步：`src/core/hello_agents/async_tool_executor.py`
