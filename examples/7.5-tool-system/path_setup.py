"""将仓库 `src/` 加入 sys.path，便于在未设置 PYTHONPATH 时直接运行本目录脚本。"""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
_s = str(_SRC)
if _s not in sys.path:
    sys.path.insert(0, _s)
