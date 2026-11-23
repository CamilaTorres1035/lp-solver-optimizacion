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
    
    def _entering_column(self) -> Tuple[Optional[int], Tuple[int, ...]]:
        """Más negativo (M primero); el empate lo gana el menor índice de columna"""
        row0 = self._tableau[0]
        negatives = [(row0[j], j) for j in self._candidates if row0[j] < 0]
        if not negatives:
            return None, ()
        best = min(v for v, _ in negatives)
        tied = tuple(j for v, j in negatives if v == best)
        return tied[0], tied

    def _check_optimality(self) -> bool:
        return self._entering_column()[0] is None

    def _find_pivot(self):
        """Devuelve (pivote o None si no hay fila que salga, razones, justificación)"""
        entering, tied = self._entering_column()
        m = self._model.n_constraints
        ratios = tuple(
            self._tableau[i][-1] / self._tableau[i][entering]
            if self._tableau[i][entering] > 0 else None
            for i in range(1, m + 1)
        )
        valid = [(r, i) for i, r in enumerate(ratios, start=1) if r is not None]
        if not valid:
            return None, ratios, (
                f"Entra {self._labels[entering]}, pero ninguna ecuación tiene "
                "coeficiente positivo en su columna: Z mejora sin límite (no acotado)."
            )
        r_min = min(r for r, _ in valid)
        tied_rows = [i for r, i in valid if r == r_min]
        # Empate: sale la variable básica de menor índice de columna
        row = min(tied_rows, key=lambda i: self._basis[i - 1])
        return (PivotInfo(row=row, column=entering), ratios,
                self._justify(entering, tied, ratios, row))

    def _justify(self, entering, tied, ratios, row) -> str:
        labels = self._labels
        text = (f"Entra {labels[entering]}: es la variable con el coeficiente más "
                f"negativo en la fila 0 ({self._tableau[0][entering]}).")
        if len(tied) > 1:
            names = ", ".join(labels[j] for j in tied)
            text += (f" Empate entre {names}: entra {labels[entering]} por la "
                     "regla del menor índice.")
        parts = []
        for i, r in enumerate(ratios, start=1):
            a = self._tableau[i][entering]
            parts.append(f"Ec {i}: no aplica (coef. {a} → —)" if r is None
                         else f"Ec {i}: {self._tableau[i][-1]}/{a} = {r}")
        text += (f" Razones: {'; '.join(parts)} → mínima {ratios[row - 1]} en la "
                 f"Ec {row}, sale {labels[self._basis[row - 1]]}.")
        return text + f" Pivote = {self._tableau[row][entering]}."
    
    def _update(self, pivot: PivotInfo) -> None:
        self._tableau = pivot_matrix(self._tableau, pivot.row, pivot.column)
        self._basis[pivot.row - 1] = pivot.column

    def _build_step(self, pivot, ratios, justification, notes=()) -> None:
        m = self._model.n_constraints
        all_notes = tuple(notes) + (self._notes if not self._steps else ())
        self._steps.append(Step(
            iteration=len(self._steps),
            row_labels=tuple(str(i) for i in range(m + 1)),
            column_labels=tuple(self._labels),
            tableau=self._tableau,
            basic_variables=tuple(self._labels[b] for b in self._basis),
            ratios=ratios,
            pivot=pivot,
            notes=all_notes,
            justification=justification,
        ))

    def solve(self, model: LPModel) -> Solution:
        self._initialize(model)
        while True:
            if self._check_optimality():
                return self._finish()
            pivot, ratios, text = self._find_pivot()
            if pivot is None:
                self._build_step(None, ratios, text)
                return self._solution(
                    SolutionStatus.NO_ACOTADA,
                    "La solución es no acotada: la función objetivo puede mejorar "
                    "sin límite. Revisa la formulación (posible restricción faltante).",
                )
            if len(self._steps) >= MAX_ITERATIONS:
                self._build_step(None, ratios, (
                    f"Se alcanzó el límite de {MAX_ITERATIONS} iteraciones."))
                return self._solution(
                    SolutionStatus.LIMITE_ITERACIONES,
                    f"Se detuvo tras {MAX_ITERATIONS} iteraciones sin llegar al "
                    "óptimo (posible ciclado).",
                )
            self._build_step(pivot, ratios, text)
            self._update(pivot)