# Research: 003-tool-system

## 决策

- **工具统一存储**：`register_function` 在内部包装为 `CallableStringTool` 并写入 `_tools`，保证 `FunctionCallAgent` 与 `execute_tool` 单一路径；同时保留 `_functions` 元数据以贴近教材结构。
- **字符串入参映射**：`execute_tool(name, str)` 按参数名优先级 `query` → `expression` → `input`，否则使用唯一必填参数名。
- **SearchTool 依赖**：在 `requirements.txt` 中加入 `tavily-python`；SerpApi 沿用 `google-search-results`。
- **异步执行**：对同步 `execute_tool` 使用 `ThreadPoolExecutor`，避免阻塞事件循环（适合 I/O 型工具）。

## 备选方案

- 仅为函数工具单独实现 `execute_tool` 分支：拒绝，易与 OpenAI schema 分叉。
- 完全移除 `_functions`：保留以兼容教材描述与后续扩展。
