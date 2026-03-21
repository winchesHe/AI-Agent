"""计算器工具：在安全字符集内求值算术表达式。"""
from __future__ import annotations

import ast
import operator
from typing import Any, Dict, List

from .base_tool import BaseTool
from .tool_parameter import ToolParameter

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_ast(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError("仅支持数值常量")
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_ast(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_ast(node.left), _eval_ast(node.right))
    raise ValueError("不支持的表达式节点")


def safe_eval_arithmetic(expression: str) -> float:
    """仅允许加减乘除与括号的算术表达式。"""
    expr = expression.strip()
    if not expr:
        raise ValueError("表达式为空")
    tree = ast.parse(expr, mode="eval")
    return _eval_ast(tree)


class CalculatorTool(BaseTool):
    name = "calculator"
    description = (
        "计算仅含数字与 + - * / 括号 的算术表达式。"
        "参数使用键 expression，值为要求值的表达式字符串。"
    )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="expression",
                type="string",
                description="要求值的算术表达式，如 15 * 8 + 32",
                required=True,
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        raw = parameters.get("expression")
        if raw is None:
            raw = parameters.get("input", "")
        if not isinstance(raw, str):
            raw = str(raw)
        try:
            return str(safe_eval_arithmetic(raw))
        except Exception as e:
            return f"计算错误: {e}"
