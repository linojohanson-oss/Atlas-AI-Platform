import ast
import operator
from typing import Any, Dict

from atlas.tools.base_tool import BaseTool


class CalculatorTool(BaseTool):
    """Calculadora segura para expresiones matemáticas básicas."""

    name = "calculator"
    description = "Evalúa expresiones matemáticas de forma segura."
    version = "1.0.0"

    _operators = {
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

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        expression = str(kwargs.get("expression", "")).strip()

        if not expression:
            raise ValueError("Debe indicar una expresión matemática.")

        try:
            tree = ast.parse(expression, mode="eval")
            result = self._evaluate(tree.body)

            return {
                "tool": self.name,
                "status": "completed",
                "input": {
                    "expression": expression,
                },
                "result": result,
            }

        except ZeroDivisionError:
            raise ValueError("No se puede dividir por cero.")
        except (SyntaxError, TypeError, ValueError) as exc:
            raise ValueError(
                f"Expresión matemática inválida: {expression}"
            ) from exc

    def _evaluate(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value

            raise ValueError("Solo se permiten números.")

        if isinstance(node, ast.BinOp):
            operation = self._operators.get(type(node.op))

            if operation is None:
                raise ValueError("Operador no permitido.")

            left = self._evaluate(node.left)
            right = self._evaluate(node.right)

            return operation(left, right)

        if isinstance(node, ast.UnaryOp):
            operation = self._operators.get(type(node.op))

            if operation is None:
                raise ValueError("Operador no permitido.")

            return operation(self._evaluate(node.operand))

        raise ValueError("La expresión contiene elementos no permitidos.")
