import ast
import math
import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


MONEY_QUANT = Decimal("0.01")
RATE_QUANT = Decimal("0.000001")


class FormulaError(ValueError):
    pass


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def rate(value: Decimal) -> Decimal:
    return value.quantize(RATE_QUANT, rounding=ROUND_HALF_UP)


def parse_input_value(value: str | None) -> Any:
    if value is None:
        return None

    text = value.strip()
    if text == "":
        return None

    lowered = text.lower()
    if lowered in {"true", "yes", "y"} or text in {"是", "大", "启用"}:
        return True
    if lowered in {"false", "no", "n"} or text in {"否", "小", "停用"}:
        return False

    normalized = text.replace(",", "").replace("%", "")
    try:
        number = Decimal(normalized)
    except Exception:
        return text

    if text.endswith("%"):
        return number / Decimal("100")
    return number


class SafeFormulaEvaluator:
    def __init__(self, context: dict[str, Any]) -> None:
        self.context = context
        self.functions = {
            "abs": abs,
            "ceil": lambda value: Decimal(math.ceil(float(value))),
            "default": self._default,
            "floor": lambda value: Decimal(math.floor(float(value))),
            "max": max,
            "min": min,
            "round": self._round,
            "where": lambda condition, a, b: a if condition else b,
        }

    def evaluate_decimal(self, expression: str | None) -> Decimal:
        if expression is None or expression.strip() == "":
            return Decimal("0")
        result = self.evaluate(expression)
        if isinstance(result, bool):
            raise FormulaError("金额公式不能返回布尔值")
        return self._to_decimal(result)

    def evaluate_condition(self, expression: str | None) -> bool:
        if expression is None or expression.strip() == "":
            return True
        return bool(self.evaluate(expression))

    def evaluate(self, expression: str) -> Any:
        normalized_expression = normalize_formula_expression(expression)
        try:
            tree = ast.parse(normalized_expression, mode="eval")
        except SyntaxError as exc:
            raise FormulaError(f"公式语法错误: {expression}") from exc
        return self._eval(tree.body)

    def _eval(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, int | float):
                return Decimal(str(node.value))
            if isinstance(node.value, str | bool) or node.value is None:
                return node.value
            raise FormulaError("公式包含不支持的常量")

        if isinstance(node, ast.Name):
            if node.id in {"True", "False", "None"}:
                return {"True": True, "False": False, "None": None}[node.id]
            if node.id not in self.context:
                raise FormulaError(f"公式引用了不存在的字段: {node.id}")
            return self.context[node.id]

        if isinstance(node, ast.List | ast.Tuple):
            return [self._eval(item) for item in node.elts]

        if isinstance(node, ast.UnaryOp):
            value = self._eval(node.operand)
            if isinstance(node.op, ast.USub):
                return -self._to_decimal(value)
            if isinstance(node.op, ast.UAdd):
                return self._to_decimal(value)
            if isinstance(node.op, ast.Not):
                return not bool(value)
            raise FormulaError("公式包含不支持的一元运算")

        if isinstance(node, ast.BinOp):
            left = self._to_decimal(self._eval(node.left))
            right = self._to_decimal(self._eval(node.right))
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                if right == 0:
                    raise FormulaError("公式除数不能为 0")
                return left / right
            if isinstance(node.op, ast.FloorDiv):
                if right == 0:
                    raise FormulaError("公式除数不能为 0")
                return Decimal(left // right)
            if isinstance(node.op, ast.Mod):
                if right == 0:
                    raise FormulaError("公式除数不能为 0")
                return left % right
            if isinstance(node.op, ast.Pow):
                return Decimal(str(float(left) ** float(right)))
            raise FormulaError("公式包含不支持的四则运算")

        if isinstance(node, ast.BoolOp):
            values = [self._eval(value) for value in node.values]
            if isinstance(node.op, ast.And):
                return all(bool(value) for value in values)
            if isinstance(node.op, ast.Or):
                return any(bool(value) for value in values)
            raise FormulaError("公式包含不支持的布尔运算")

        if isinstance(node, ast.Compare):
            left = self._eval(node.left)
            for op, comparator in zip(node.ops, node.comparators, strict=True):
                right = self._eval(comparator)
                if not self._compare(left, op, right):
                    return False
                left = right
            return True

        if isinstance(node, ast.IfExp):
            return self._eval(node.body) if bool(self._eval(node.test)) else self._eval(node.orelse)

        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise FormulaError("公式函数调用不合法")
            function = self.functions.get(node.func.id)
            if function is None:
                raise FormulaError(f"公式使用了不支持的函数: {node.func.id}")
            if node.keywords:
                raise FormulaError("公式函数暂不支持关键字参数")
            args = [self._eval(arg) for arg in node.args]
            return function(*args)

        raise FormulaError("公式包含不支持的表达式")

    def _compare(self, left: Any, op: ast.cmpop, right: Any) -> bool:
        if isinstance(op, ast.Eq):
            return left == right
        if isinstance(op, ast.NotEq):
            return left != right
        if isinstance(op, ast.In):
            return left in right
        if isinstance(op, ast.NotIn):
            return left not in right

        left_number = self._to_decimal(left)
        right_number = self._to_decimal(right)
        if isinstance(op, ast.Lt):
            return left_number < right_number
        if isinstance(op, ast.LtE):
            return left_number <= right_number
        if isinstance(op, ast.Gt):
            return left_number > right_number
        if isinstance(op, ast.GtE):
            return left_number >= right_number
        raise FormulaError("公式包含不支持的比较运算")

    def _default(self, value: Any, fallback: Any) -> Any:
        if value is None or value == "":
            return fallback
        return value

    def _round(self, value: Any, digits: Any = 0) -> Decimal:
        number = self._to_decimal(value)
        places = int(self._to_decimal(digits))
        quantum = Decimal("1") if places == 0 else Decimal("1").scaleb(-places)
        return number.quantize(quantum, rounding=ROUND_HALF_UP)

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        if value is None:
            return Decimal("0")
        if isinstance(value, Decimal):
            return value
        if isinstance(value, bool):
            return Decimal("1") if value else Decimal("0")
        if isinstance(value, int | float):
            return Decimal(str(value))
        if isinstance(value, str):
            try:
                return Decimal(value.replace(",", "").replace("%", ""))
            except Exception as exc:
                raise FormulaError(f"字段值不是可计算数字: {value}") from exc
        raise FormulaError("字段值类型不支持计算")


def normalize_formula_expression(expression: str) -> str:
    replacements = {
        "AND": "and",
        "OR": "or",
        "NOT": "not",
        "TRUE": "True",
        "FALSE": "False",
        "NONE": "None",
    }
    normalized = expression
    for source, target in replacements.items():
        normalized = re.sub(rf"\b{source}\b", target, normalized, flags=re.IGNORECASE)
    return normalized
