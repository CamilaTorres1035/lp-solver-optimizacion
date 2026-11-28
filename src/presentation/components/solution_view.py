"""
Filas de la solución final (HU-15): holgura o exceso de cada restricción.

La misma función se usa en modo Directa, al final del Paso a paso y en el método gráfico, para que la solución final sea idéntica en todos los casos.

Los valores vienen de `Solution.slacks`, que el dominio calcula sobre el modelo ORIGINAL (RHS − LHS en ≤, LHS − RHS en ≥, 0 en =); por eso también es correcto cuando una restricción se multiplicó por −1. El tipo sale de la relación original.

En pantalla se dice "Restricción i" y no "Ri" para no confundir con las artificiales R_i (decisión 4 del documento).
"""
from typing import Dict, List

from domain.model.enums import Relation
from domain.model.lp_model import LPModel
from domain.solver.solution import Solution
from utils.formatting import FRACTION_MODE, format_constraint, format_number

_KIND = {
    Relation.LESS_EQUAL: "Holgura",
    Relation.GREAT_EQUAL: "Exceso",
    Relation.EQUAL: "Igualdad (sin holgura)",
}


def build_slack_rows(
    model: LPModel, solution: Solution, number_format: str = FRACTION_MODE
) -> List[Dict[str, str]]:
    """Una fila por restricción: nombre, expresión original, tipo y valor."""
    return [
        {
            "Restricción": f"Restricción {constraint.original_index}",
            "Expresión": format_constraint(
                constraint.coefficients, constraint.relation.value,
                constraint.rhs, number_format,
            ),
            "Tipo": _KIND[constraint.relation],
            "Valor": format_number(slack, number_format),
        }
        for constraint, slack in zip(model.constraints, solution.slacks)
    ]
