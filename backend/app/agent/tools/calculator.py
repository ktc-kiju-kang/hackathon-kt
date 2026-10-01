import ast
import asyncio
import json
import operator

from pydantic import BaseModel, Field

from app.agent.tools import Tool

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def _eval(node: ast.AST) -> float:
    # eval() 금지: 숫자와 사칙연산만 허용 (LLM 입력은 신뢰하지 않는다)
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow):
            # 계산 전에 결과 크기를 막는다 (중첩 거듭제곱으로 서버가 멈추지 않게)
            if abs(right) > 100 or abs(left) > 1e12:
                raise ValueError("거듭제곱 값이 너무 큽니다")
        return _check(_OPS[type(node.op)](left, right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _check(_OPS[type(node.op)](_eval(node.operand)))
    raise ValueError("숫자와 + - * / ** % ( ) 만 사용할 수 있습니다")


def _check(value: float) -> float:
    if abs(value) > 1e300:
        raise ValueError("결과가 너무 큽니다")
    return value


class Input(BaseModel):
    expression: str = Field(max_length=200, description="계산식 (예: (1200 * 3) / 4)")


async def run(args: Input) -> str:
    tree = ast.parse(args.expression, mode="eval").body
    value = await asyncio.to_thread(_eval, tree)  # CPU 작업이 이벤트 루프를 막지 않게
    return json.dumps({"expression": args.expression, "result": value})


tool = Tool(
    name="calculator",
    description="정확한 사칙연산 계산. 숫자 계산은 암산하지 말고 이 도구를 쓴다.",
    input_model=Input,
    run=run,
)
