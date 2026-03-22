# CLI 调用约定（主入口 `src/main.py`）

## 运行模式

| 子命令 | 用途 | 典型调用 |
|--------|------|----------|
| `task` | 单次任务（foreground） | `python main.py task -m "..."` |
| `chat` | 交互对话 | `python main.py chat` |
| `daemon` | 常驻循环（7×24） | `python main.py daemon` |
| `doctor` | 自检（配置、插件、可选探测） | `python main.py doctor` |
| `health` | 输出健康快照 JSON（常驻或一次性） | `python main.py health --json` |
| `plugins` | 列出已发现/已启用插件 | `python main.py plugins` 或 `python main.py plugins list`（等价） |

> 工作目录：默认在 `src/` 下执行；实现可支持 `python -m` 自仓库根。

## 通用选项

| 长选项 | 说明 |
|--------|------|
| `--config PATH` | 覆盖默认配置文件路径 |
| `--trace human\|json` | 轨迹输出格式 |
| `--trace-file PATH` | 轨迹落盘 |
| `--plugin-path PATH` | 附加插件搜索路径（可重复） |

## 退出码

| Code | 含义 |
|------|------|
| 0 | 成功 |
| 2 | CLI 用法错误 |
| 3 | 配置 / manifest 校验失败 |
| 4 | 模型或外部依赖失败（可重试） |
| 5 | 内部错误 |
| 6 | 插件加载失败（致命） |

## 稳定性

破坏性变更须 bump `schema_version`（配置与契约同步说明于 `quickstart.md`）。
