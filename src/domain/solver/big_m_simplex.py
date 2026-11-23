"""Símplex Gran M (HU-06)

El tableau guarda la fila 0 como ValorM (a + bM) y las filas de restricciones
como Fraction. M solo aparece en la fila 0

Convención de Step (acorde para HU-08/09):
- tableau[0] es la fila 0; columna 0 = Z; última columna = RHS
- ratios[i] y basic_variables[i] corresponden a tableau[i + 1].
- El pivote del paso k se aplica al tableau del paso k y produce el del paso k+1
"""

from fractions import Fraction
from typing import List, Optional, Tuple

from ..model.enums import OptimizationSense, Relation
from ..model.lp_model import LPModel
from .linalg import pivot_matrix
from .solution import BasisInfo, Solution, SolutionStatus
from .step import PivotInfo, Step
from .symbolic import ValorM

F = Fraction
M = ValorM(0, 1)          # el símbolo M
MAX_ITERATIONS = 200

_FLIP = {
    Relation.LESS_EQUAL: Relation.GREAT_EQUAL,
    Relation.GREAT_EQUAL: Relation.LESS_EQUAL,
    Relation.EQUAL: Relation.EQUAL,
}

def _s(value) -> str:
    """Texto de un número exacto: '3', '3/2', '-5'."""
    return str(ValorM(value))

def _lhs(coefficients) -> str:
    return " + ".join(f"{_s(a)}·x{j + 1}" for j, a in enumerate(coefficients))

def _text(coefficients, relation: Relation, rhs) -> str:
    return f"{_lhs(coefficients)} {relation.value} {_s(rhs)}"


def _fmt_row(row) -> str:
    return "(" + ", ".join(str(v) for v in row) + ")"

