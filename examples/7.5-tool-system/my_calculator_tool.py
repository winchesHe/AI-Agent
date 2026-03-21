# my_calculator_tool.py
from __future__ import annotations

import ast
import math
import operator

import path_setup  # noqa: F401

from hello_agents import ToolRegistry


def my_calculate(expression: str) -> str:
    """简单的数学计算函数（教材示例：四则运算 + sqrt + pi）。"""
    if not expression.strip():
        return "计算表达式不能为空"

    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }

    functions = {
        "sqrt": math.sqrt,
        "pi": math.pi,
    }

    try:
        node = ast.parse(expression, mode="eval")
        result = _eval_node(node.body, operators, functions)
        return str(result)
    except Exception:
        return "计算失败，请检查表达式格式"


def _eval_node(node, operators, functions):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, operators, functions)
        right = _eval_node(node.right, operators, functions)
        op = operators.get(type(node.op))
        if op is None:
            raise ValueError("不支持的运算符")
        return op(left, right)
    if isinstance(node, ast.Call):
        func_name = getattr(node.func, "id", None)
        if func_name in functions and callable(functions[func_name]):
            args = [_eval_node(arg, operators, functions) for arg in node.args]
            return functions[func_name](*args)
    if isinstance(node, ast.Name):
        v = functions.get(node.id)
        if v is not None and not callable(v):
            return v
    raise ValueError("不支持的表达式节点")


def create_calculator_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register_function(
        name="my_calculator",
        description="简单的数学计算工具，支持基本运算(+,-,*,/)和 sqrt、pi",
        func=my_calculate,
    )
    return registry
