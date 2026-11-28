"""Símplex Gran M (HU-06) con casos especiales (HU-10)

El tableau guarda la fila 0 como ValorM (a + bM) y las filas de restricciones
como Fraction. M solo aparece en la fila 0

Convención de Step (acorde para HU-08/09):
- tableau[0] es la fila 0; columna 0 = Z; última columna = RHS
- ratios[i] y basic_variables[i] corresponden a tableau[i + 1].
- El pivote del paso k se aplica al tableau del paso k y produce el del paso k+1
- entering_column = pivot.column si hay pivote; en el paso terminal de no acotado, límite o rayo no factible es la columna que intentó entrar; None en el tableau final
- setup_notes (solo paso 0) = la forma estándar; también va incluida en notes
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
    """Texto de un número exacto (ASCII): '3', '3/2', '-5'. Usa ValorM.__str__"""
    return str(ValorM(value))

def _num(value) -> str:
    """Número exacto con signo menos tipográfico: '3/2', '−5'"""
    return str(F(value)).replace("-", "−")

_REL_TEXT = {"<=": "≤", ">=": "≥", "=": "="} # Local pues domain no importa utils

def _lhs(coefficients) -> str:
    """'x1 + 2·x2', '−x1 − 2·x2', '3/2·x1 − x3'; omite los coeficientes 0"""
    out = ""
    for j, a in enumerate(coefficients, start=1):
        a = F(a)
        if a == 0:
            continue
        mag = abs(a)
        body = f"x{j}" if mag == 1 else f"{_num(mag)}·x{j}"
        if not out:
            out = body if a > 0 else "−" + body
        else:
            out += (" + " if a > 0 else " − ") + body
    return out or "0"

def _text(coefficients, relation: Relation, rhs) -> str:
    return f"{_lhs(coefficients)} {_REL_TEXT.get(relation.value, relation.value)} {_num(rhs)}"

def _fmt_row(row) -> str:
    return "(" + ", ".join(str(v) for v in row) + ")"

def _fmt_point(point) -> str:
    return "(" + ", ".join(_s(v) for v in point) + ")"
class BigMSimplexSolver:
    """Implementa el Protocol Solver con el método de la Gran M."""

    def _initialize(self, model: LPModel) -> None:
        n, m = model.n_variables, model.n_constraints
        sf = 1 if model.sense == OptimizationSense.MAXIMIZE else -1
        notes: List[str] = []
        flip_notes: List[str] = []   # nota original/transformada (también en modo Directa)
        if sf == -1:
            notes.append("Minimización: se resuelve Max W = −Z; la fila 0 es la de −Z")

        rows = []
        for c in model.constraints:
            coeffs, rel, rhs, flipped = c.coefficients, c.relation, c.rhs, False
            if rhs < 0:
                before = _text(coeffs, rel, rhs)
                coeffs = tuple(-a for a in coeffs)
                rel, rhs, flipped = _FLIP[rel], -rhs, True
                flip = (f"Restricción {c.original_index}: {before} se multiplicó por −1 "
                        f"→ {_text(coeffs, rel, rhs)}.")
                notes.append(flip)
                flip_notes.append(flip)
            rows.append((coeffs, rel, rhs, flipped))

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
            notes.append(f"Ec {i}: {_lhs(coeffs)}{extra} = {_num(rhs)}")

        row0 = ([ValorM(sf)]
                + [ValorM(-sf * c) for c in model.objective]
                + [ValorM(0)] * (width - 1 - n))
        for col in art.values():
            row0[col] = M
        if art:
            notes.append(f"Fila 0 inicial: {_fmt_row(row0)}")
        for i in art:
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
        self._basis = basis
        self._initial_basis = tuple(basis)
        self._artificial = frozenset(art.values())
        self._candidates = tuple(j for j in range(1, width - 1)
                                 if j not in self._artificial)
        self._flipped = tuple(r[3] for r in rows)
        self._notes = tuple(notes)
        self._flip_notes = tuple(flip_notes)
        self._steps: List[Step] = []
        # HU-10: ciclado
        self._bland = False
        self._seen = {frozenset(basis)}
        self._pending: List[str] = []
    
    # -------- reglas de pivoteo --------
    def _entering_column(self) -> Tuple[Optional[int], Tuple[int, ...]]:
        """Dantzig: Más negativo (M primero); el empate lo gana el menor índice de columna
            Bland si hubo ciclado: menor índice negativo"""
        row0 = self._tableau[0]
        negatives = [(row0[j], j) for j in self._candidates if row0[j] < 0]
        if not negatives:
            return None, ()
        if self._bland:
            return negatives[0][1], (negatives[0][1],)
        best = min(v for v, _ in negatives)
        tied = tuple(j for v, j in negatives if v == best)
        return tied[0], tied

    def _check_optimality(self) -> bool:
        return self._entering_column()[0] is None

    def _ratios(self, column: int) -> Tuple[Optional[Fraction], ...]:
        return tuple(
            self._tableau[i][-1] / self._tableau[i][column]
            if self._tableau[i][column] > 0 else None
            for i in range(1, self._model.n_constraints + 1)
        )

    def _leaving_row(self, ratios) -> Optional[int]:
        """Menor razón; el empate lo gana la variable básica de menor índice de columna"""
        valid = [(r, i) for i, r in enumerate(ratios, start=1) if r is not None]
        if not valid:
            return None
        r_min = min(r for r, _ in valid)
        return min((i for r, i in valid if r == r_min),
                   key=lambda i: self._basis[i - 1])

    def _tied_rows(self, ratios, row: int) -> List[int]:
        rows = [i for i, r in enumerate(ratios, start=1) if r == ratios[row - 1]]
        return sorted(rows, key=lambda i: self._basis[i - 1])

    def _find_pivot(self):
        """(pivote o None si no hay fila que salga, razones, justificación, notas)."""
        entering, tied = self._entering_column()
        ratios = self._ratios(entering)
        row = self._leaving_row(ratios)
        if row is None:
            return None, ratios, (
                f"Entra {self._labels[entering]}, pero ninguna ecuación tiene "
                "coeficiente positivo en su columna: Z mejora sin límite (no acotado)."
            ), ()
        notes = ()
        tied_rows = self._tied_rows(ratios, row)
        if len(tied_rows) > 1:
            others = [self._labels[self._basis[i - 1]] for i in tied_rows[1:]]
            verb = "quedan" if len(others) > 1 else "queda"
            notes = (
                f"Degeneración: empate en la razón mínima ({ratios[row - 1]}) entre "
                f"{', '.join(self._labels[self._basis[i - 1]] for i in tied_rows)}. "
                f"Sale {self._labels[self._basis[row - 1]]} (menor índice); "
                f"{', '.join(others)} {verb} en la base con valor 0.",
            )
        return (PivotInfo(row=row, column=entering), ratios,
                self._justify(entering, tied, ratios, row, tied_rows), notes)

    def _justify(self, entering, tied, ratios, row, tied_rows) -> str:
        labels = self._labels
        if self._bland:
            text = (f"Entra {labels[entering]}: regla de Bland (menor índice con "
                    f"coeficiente negativo en la fila 0: {self._tableau[0][entering]}).")
        else:
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
        if len(tied_rows) > 1:
            eqs = ", ".join(f"Ec {i}" for i in tied_rows)
            text += (f" Empate de razones en {eqs}: sale {labels[self._basis[row - 1]]} "
                     "por la regla del menor índice.")
        return text + f" Pivote = {self._tableau[row][entering]}."

    def _update(self, pivot: PivotInfo) -> None:
        self._tableau = pivot_matrix(self._tableau, pivot.row, pivot.column)
        self._basis[pivot.row - 1] = pivot.column
        # Hu-10: ciclo --> cambio a bland
        key = frozenset(self._basis)
        if key in self._seen and not self._bland:
            self._bland = True
            self._pending.append(
                "Ciclado: se repitió una base ya visitada. Desde aquí se usa la "
                "regla de Bland (entra la variable de menor índice con coeficiente "
                "negativo) para garantizar que el método termine."
            )
        self._seen.add(key)

    def _build_step(self, pivot, ratios, justification, notes=(), entering=None) -> None:
        """`entering`: columna que entra cuando no hay pivote (no acotado, límite)."""
        m = self._model.n_constraints
        first = self._notes if not self._steps else ()
        all_notes = first + tuple(self._pending) + tuple(notes)
        self._pending = []
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
            entering_column=pivot.column if pivot is not None else entering,
            setup_notes=first,
        ))

    def solve(self, model: LPModel) -> Solution:
        self._initialize(model)
        while True:
            if self._check_optimality():
                return self._finish()
            pivot, ratios, text, notes = self._find_pivot()
            if pivot is None:
                entering = self._entering_column()[0]
                row = self._positive_artificial()
                if row is not None:   # rayo con artificial > 0: el modelo es no factible
                    return self._infeasible(row, ratios,
                                            "La variable que entra puede crecer sin límite, pero ",
                                            entering=entering)
                self._build_step(None, ratios, text, entering=entering)   # no acotada
                return self._solution(
                    SolutionStatus.NO_ACOTADA,
                    "La solución es no acotada: la función objetivo puede mejorar "
                    "sin límite. Revisa la formulación (posible restricción faltante).",
                )
            if len(self._steps) >= MAX_ITERATIONS:
                self._build_step(None, ratios, (
                    f"Se alcanzó el límite de {MAX_ITERATIONS} iteraciones."),
                    entering=pivot.column)
                return self._solution(
                    SolutionStatus.LIMITE_ITERACIONES,
                    f"Se detuvo tras {MAX_ITERATIONS} iteraciones sin llegar al "
                    "óptimo (posible ciclado).",
                )
            self._build_step(pivot, ratios, text, notes)
            self._update(pivot)

    # ---------------- resultado final ----------------

    def _point(self) -> Tuple[Fraction, ...]:
        n = self._model.n_variables
        point = [F(0)] * n
        for i, b in enumerate(self._basis, start=1):
            if 1 <= b <= n:
                point[b - 1] = self._tableau[i][-1]
        return tuple(point)

    def _positive_artificial(self) -> Optional[int]:
        """Fila de una artificial básica con valor > 0 (certificado de no factibilidad)."""
        for i, b in enumerate(self._basis, start=1):
            if b in self._artificial and self._tableau[i][-1] > 0:
                return i
        return None

    def _infeasible(self, row: int, ratios, prefix: str, entering=None) -> Solution:
        name = self._labels[self._basis[row - 1]]
        self._build_step(None, ratios, (
            f"{prefix}La artificial {name} sigue en la base con valor "
            f"{self._tableau[row][-1]} > 0: la suma de artificiales no se puede "
            "reducir → no factible."), entering=entering)
        return self._solution(
            SolutionStatus.NO_FACTIBLE,
            "El modelo no tiene solución factible: no se pudo eliminar la "
            f"variable artificial {name}.",
        )

    def _alternative_column(self) -> Optional[int]:
        """VNB (no artificial) con coeficiente 0 en la fila 0 final: indica óptimos alternos."""
        row0 = self._tableau[0]
        for j in self._candidates:
            if j not in self._basis and row0[j] == 0:
                return j
        return None

    def _finish(self) -> Solution:
        model, m = self._model, self._model.n_constraints
        no_ratios = (None,) * m

        # No factible: una artificial con valor > 0 sigue en la base
        row = self._positive_artificial()
        if row is not None:
            return self._infeasible(row, no_ratios, "Ningún coeficiente negativo en la fila 0. ")

        # Óptimo encontrado por el símplex
        point = self._point()
        z = self._sf * self._tableau[0][-1].to_fraction()
        basis = BasisInfo(
            basic_variables=tuple(self._labels[b] for b in self._basis),
            basis_inverse=tuple(
                tuple(self._tableau[i][c] for c in self._initial_basis)
                for i in range(1, m + 1)),
            row_to_constraint=tuple(range(1, m + 1)),
            rhs_sign_flipped=self._flipped,
            sense_factor=self._sf,
        )
        values = tuple((f"x{j + 1}", v) for j, v in enumerate(point))
        slacks = _slacks(model, point)

        notes: List[str] = [
            f"La artificial {self._labels[b]} queda en la base con valor 0 "
            "(restricción redundante o degeneración); se ignora en la sensibilidad."
            for b in self._basis if b in self._artificial
        ]
        final_text = ("Ningún coeficiente negativo en la fila 0 → la solución es óptima. "
              f"Z = {_s(z)} con "
              + ", ".join(f"x{j+1} = {_s(v)}" for j, v in enumerate(point)) + ".")
        alt_values: Tuple[Tuple[str, Fraction], ...] = ()
        final_notes: List[str] = []

        column = self._alternative_column()
        if column is not None:
            name = self._labels[column]
            ratios = self._ratios(column)
            row = self._leaving_row(ratios)
            if row is None:
                final_notes.append(
                    f"Óptimos múltiples: {name} es no básica con coeficiente 0 en la "
                    "fila 0 y su columna no tiene coeficientes positivos: el "
                    "conjunto óptimo es no acotado.")
            elif ratios[row - 1] > 0:
                # Pivote extra automático: segundo vértice óptimo
                leaving = self._labels[self._basis[row - 1]]
                self._build_step(
                    PivotInfo(row=row, column=column), ratios,
                    f"{final_text} Como la variable no básica {name} tiene "
                    "coeficiente 0 en la fila 0, hay óptimos alternativos. Pivote "
                    f"extra: entra {name}, sale {leaving} (razón mínima "
                    f"{ratios[row - 1]}); Z no cambia.",
                    notes + ["Óptimos múltiples: se hace un pivote extra automático."])
                notes = []
                self._update(PivotInfo(row=row, column=column))
                other = self._point()
                alt_values = tuple((f"x{j + 1}", v) for j, v in enumerate(other))
                final_text = ("Segundo vértice óptimo, con el mismo valor de Z. "
                              "Todo punto del segmento entre ambos vértices es óptimo.")
                final_notes.append(
                    f"Óptimos múltiples: Z = {_s(z)} en A = {_fmt_point(point)} y "
                    f"B = {_fmt_point(other)}. Todo x = λA + (1−λ)B con 0 ≤ λ ≤ 1 "
                    "es óptimo.")
            # razón 0: el pivote extra no cambia de vértice; no hay otro óptimo distinto

        self._build_step(None, no_ratios, final_text, notes)
        message = f"Solución óptima: Z = {_s(z)}."
        if alt_values:
            message += " Hay óptimos múltiples (infinitos sobre el segmento entre dos vértices)"
        return self._solution(
            SolutionStatus.OPTIMA, message, values=values, z=z, slacks=slacks,
            basis=basis, alt_values=alt_values, extra_notes=final_notes,
        )

    def _solution(self, status, message, values=(), z=None, slacks=(), basis=None,
                  alt_values=(), extra_notes=()):
        return Solution(
            status=status, values=values, optimal_value=z, slacks=slacks,
            alt_values=alt_values, steps=tuple(self._steps),
            notes=self._flip_notes + tuple(extra_notes),
            message=message, basis_info=basis,
            model_fingerprint=hash(self._model),
        )


def _slacks(model: LPModel, point) -> Tuple[Fraction, ...]:
    """Holgura (<=) o exceso (>=) sobre el modelo ORIGINAL; 0 en igualdades."""
    result = []
    for c in model.constraints:
        lhs = sum((a * x for a, x in zip(c.coefficients, point)), F(0))
        if c.relation == Relation.LESS_EQUAL:
            result.append(c.rhs - lhs)
        elif c.relation == Relation.GREAT_EQUAL:
            result.append(lhs - c.rhs)
        else:
            result.append(F(0))
    return tuple(result)
