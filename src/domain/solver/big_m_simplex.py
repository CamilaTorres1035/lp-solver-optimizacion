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

class BigMSimplexSolver:
    """Implementa el Protocol Solver con el método de la Gran M"""
    def _initialize(self, model: LPModel) -> None:
        n, m = model.n_variables, model.n_constraints
        sf = 1 if model.sense == OptimizationSense.MAXIMIZE else -1
        notes: List[str] = []
        if sf == -1:
            notes.append("Minimización: se resuelve Max W = −Z; la fila 0 es la de −Z")

        # 1) RHS negativo: se multiplica por -1 y se invierte la relación
        rows = []
        for c in model.constraints:
            coeffs, rel, rhs, flipped = c.coefficients, c.relation, c.rhs, False
            if rhs < 0:
                before = _text(coeffs, rel, rhs)
                coeffs = tuple(-a for a in coeffs)
                rel, rhs, flipped = _FLIP[rel], -rhs, True
                notes.append(
                    f"Restricción {c.original_index}: {before} se multiplicó por −1 "
                    f"→ {_text(coeffs, rel, rhs)}."
                )
            rows.append((coeffs, rel, rhs, flipped))

        # 2) Columnas: Z, x1..xn y, por restricción i, S_i y luego R_i
        labels = ["Z"] + [f"x{j + 1}" for j in range(n)]
        slack, art = {}, {}
        for i, (_, rel, _, _) in enumerate(rows, start=1):
            if rel != Relation.EQUAL:
                slack[i] = len(labels)
                labels.append(f"S{i}")
            if rel != Relation.LESS_EQUAL:
                art[i] = len(labels)
                labels.append(f"R{i}")
        labels.append("RHS")
        width = len(labels)

        # 3) Filas de restricciones (Fraction) y base inicial
        body, basis = [], []
        for i, (coeffs, rel, rhs, _) in enumerate(rows, start=1):
            row = [F(0)] * width
            row[1:1 + n] = coeffs
            if rel == Relation.LESS_EQUAL:
                row[slack[i]] = F(1)
                basis.append(slack[i])
            elif rel == Relation.GREAT_EQUAL:
                row[slack[i]] = F(-1)
                row[art[i]] = F(1)
                basis.append(art[i])
            else:
                row[art[i]] = F(1)
                basis.append(art[i])
            row[-1] = rhs
            body.append(tuple(row))
            extra = {Relation.LESS_EQUAL: f" + S{i}",
                     Relation.GREAT_EQUAL: f" − S{i} + R{i}",
                     Relation.EQUAL: f" + R{i}"}[rel]
            notes.append(f"Ec {i}: {_lhs(coeffs)}{extra} = {_s(rhs)}")

        # 4) Fila 0: Z - c'x + M·ΣR = 0, con c' = sentido × c
        row0 = ([ValorM(sf)]
                + [ValorM(-sf * c) for c in model.objective]
                + [ValorM(0)] * (width - 1 - n))
        for col in art.values():
            row0[col] = M
        if art:
            notes.append(f"Fila 0 inicial: {_fmt_row(row0)}")
        for i in art:                       # preparación: restar M × fila i
            row0 = [r0 - M * b for r0, b in zip(row0, body[i - 1])]
        if art:
            restas = " y ".join(f"M·(Ec {i})" for i in art)
            notes.append(
                f"Preparación de la fila 0: se resta {restas} para que las "
                f"artificiales básicas queden con coeficiente 0 → {_fmt_row(row0)}"
            )

        self._model = model
        self._sf = sf
        self._labels = labels
        self._tableau = (tuple(row0),) + tuple(body)
        self._basis = basis                            # índice de columna por fila
        self._initial_basis = tuple(basis)             # B^-1 se lee bajo estas columnas
        self._artificial = frozenset(art.values())
        self._candidates = tuple(j for j in range(1, width - 1)
                                 if j not in self._artificial)
        self._flipped = tuple(r[3] for r in rows)
        self._notes = tuple(notes)
        self._steps: List[Step] = []