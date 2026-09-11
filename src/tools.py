import ast
import operator
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, List


@dataclass
class ToolCallResult:
    name: str
    input: str
    output: str


class ToolExecutionError(ValueError):
    pass


ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def safe_calculate(expression: str) -> float:
    tree = ast.parse(expression, mode="eval")

    def evaluate(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)

        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value

        if isinstance(node, ast.BinOp) and type(node.op) in ALLOWED_OPERATORS:
            return ALLOWED_OPERATORS[type(node.op)](evaluate(node.left), evaluate(node.right))

        if isinstance(node, ast.UnaryOp) and type(node.op) in ALLOWED_OPERATORS:
            return ALLOWED_OPERATORS[type(node.op)](evaluate(node.operand))

        raise ToolExecutionError("지원하지 않는 수식입니다.")

    return evaluate(tree)


def calculator_tool(expression: str) -> ToolCallResult:
    result = safe_calculate(expression)
    formatted = int(result) if isinstance(result, float) and result.is_integer() else result
    return ToolCallResult(name="calculator", input=expression, output=str(formatted))


def text_stats_tool(text: str) -> ToolCallResult:
    words = re.findall(r"[A-Za-z0-9가-힣]+", text)
    characters_without_spaces = len(re.sub(r"\s+", "", text))
    characters_with_spaces = len(text)
    output = (
        f"words={len(words)}, "
        f"characters_without_spaces={characters_without_spaces}, "
        f"characters_with_spaces={characters_with_spaces}"
    )
    return ToolCallResult(name="text_stats", input=text, output=output)


def date_diff_tool(start_date: str, end_date: str) -> ToolCallResult:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    days = abs((end - start).days)
    return ToolCallResult(name="date_diff", input=f"{start_date} to {end_date}", output=f"{days} days")


def extract_expression(text: str) -> str | None:
    candidates = re.findall(r"(?<!\w)[0-9][0-9\s+\-*/().%]*[+\-*/%][0-9\s+\-*/().%]*", text)
    if not candidates:
        return None
    return max(candidates, key=len).strip()


def extract_dates(text: str) -> List[str]:
    return re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text)


def select_and_run_tools(user_request: str) -> List[ToolCallResult]:
    results = []

    expression = extract_expression(user_request)
    if expression:
        try:
            results.append(calculator_tool(expression))
        except (SyntaxError, ZeroDivisionError, ToolExecutionError, ValueError) as exc:
            results.append(ToolCallResult(name="calculator", input=expression, output=f"error: {exc}"))

    lowered = user_request.lower()
    wants_text_stats = any(
        keyword in lowered
        for keyword in ["word count", "character count", "text length", "문자 수", "글자 수", "단어 수", "문장 길이"]
    )
    if wants_text_stats:
        results.append(text_stats_tool(user_request))

    dates = extract_dates(user_request)
    wants_date_diff = any(keyword in lowered for keyword in ["date difference", "days between", "날짜 차이", "며칠"])
    if wants_date_diff and len(dates) >= 2:
        try:
            results.append(date_diff_tool(dates[0], dates[1]))
        except ValueError as exc:
            results.append(ToolCallResult(name="date_diff", input=f"{dates[0]} to {dates[1]}", output=f"error: {exc}"))

    return results


def format_tool_results(results: List[ToolCallResult]) -> str:
    if not results:
        return "Tool calls: none"

    lines = ["Tool calls:"]
    for result in results:
        lines.append(f"- {result.name}({result.input}) => {result.output}")
    return "\n".join(lines)
