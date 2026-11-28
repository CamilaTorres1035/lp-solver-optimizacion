"""
Navegación por iteraciones (HU-08) y resaltado del tableau (HU-09).

Decisión 7 del documento: la iteración visible es un entero en st.session_state que `clamp_step` mantiene entre 0 y N−1; botones y deslizador leen y escriben ese mismo valor.

`build_tableau_view` decide QUÉ se resalta (roles por celda); los colores los decide presentation (tableau_view.py). Sin Streamlit: se prueba con unittest
"""
from dataclasses import dataclass
from typing import FrozenSet, Optional, Tuple

from domain.solver.step import Step
from utils.formatting import FRACTION_MODE, format_value

# Roles de una celda. Son aditivos: el elemento pivote tiene los tres primeros
PIVOT_COLUMN = "columna_pivote"
PIVOT_ROW = "fila_pivote"
PIVOT_ELEMENT = "elemento_pivote"
MIN_RATIO = "razon_minima"

_NO_ROLES: FrozenSet[str] = frozenset()


def clamp_step(index: int, n_steps: int) -> int:
    """Índice válido entre 0 y n_steps − 1 (0 si no hay iteraciones)."""
    if n_steps <= 0:
        return 0
    return max(0, min(int(index), n_steps - 1))


@dataclass(frozen=True)
class TableauCell:
    text: str
    roles: FrozenSet[str] = _NO_ROLES


@dataclass(frozen=True)
class TableauView:
    """Tableau listo para dibujar: encabezado, filas y un título con lo que pasa en la iteración"""
    title: str
    header: Tuple[TableauCell, ...]
    rows: Tuple[Tuple[TableauCell, ...], ...]


def entering_column(step: Step) -> Optional[int]:
    """Columna que entra: la del pivote o, sin pivote, la que intentó entrar."""
    if step.pivot is not None:
        return step.pivot.column
    return step.entering_column


def iteration_title(step: Step) -> str:
    """'Iteración 1: entra x1, sale S3' y variantes para los pasos sin pivote"""
    entering = entering_column(step)
    head = f"Iteración {step.iteration}"
    if step.pivot is not None:
        leaving = step.basic_variables[step.pivot.row - 1]
        return f"{head}: entra {step.column_labels[entering]}, sale {leaving}"
    if entering is not None:
        return f"{head}: entra {step.column_labels[entering]}, pero no se pivotea"
    return f"{head}: tableau final"


def build_tableau_view(
    step: Step,
    *,
    minimize: bool = False,
    number_format: str = FRACTION_MODE,
) -> TableauView:
    """
    Tableau con el formato de clase: Ec #, VB, Z, variables, lado derecho y Razón.

    - Fila 0: VB = 'Z' (o '−Z' si se minimiza, porque la fila 0 es la de −Z y su lado derecho muestra −Z). Su razón queda vacía
    - Razón de la fila i: step.ratios[i−1]; '—' si el coeficiente de la columna que entra es <= 0
    - Si no entra ninguna variable (tableau final), toda la columna Razón queda vacía: no hay prueba de razón mínima que mostrar.
    - Roles: columna que entra (también en el encabezado), fila pivote, elemento pivote y razón mínima (todas las filas empatadas)
    """
    entering = entering_column(step)
    pivot_row = step.pivot.row if step.pivot is not None else None
    show_ratios = entering is not None

    valid = [r for r in step.ratios if r is not None]
    r_min = min(valid) if show_ratios and valid else None

    def roles_for(row: int, col: int) -> FrozenSet[str]:
        roles = set()
        if col == entering:
            roles.add(PIVOT_COLUMN)
        if row == pivot_row:
            roles.add(PIVOT_ROW)
        if col == entering and row == pivot_row:
            roles.add(PIVOT_ELEMENT)
        return frozenset(roles)

    def row_header_roles(row: int) -> FrozenSet[str]:
        return frozenset({PIVOT_ROW}) if row == pivot_row else _NO_ROLES

    header_labels = [
        "Lado derecho" if label == "RHS" else label for label in step.column_labels
    ]
    header = (
        (TableauCell("Ec #"), TableauCell("VB"))
        + tuple(
            TableauCell(label, frozenset({PIVOT_COLUMN}) if j == entering else _NO_ROLES)
            for j, label in enumerate(header_labels)
        )
        + (TableauCell("Razón"),)
    )

    rows = []
    for i, values in enumerate(step.tableau):
        if i == 0:
            basic = "−Z" if minimize else "Z"
            ratio = TableauCell("")
        else:
            basic = step.basic_variables[i - 1]
            ratio = _ratio_cell(step.ratios[i - 1], show_ratios, r_min, i == pivot_row, number_format)
        label = step.row_labels[i] if i < len(step.row_labels) else str(i)
        rows.append(
            (TableauCell(label, row_header_roles(i)), TableauCell(basic, row_header_roles(i)))
            + tuple(
                TableauCell(format_value(v, number_format), roles_for(i, j))
                for j, v in enumerate(values)
            )
            + (ratio,)
        )

    return TableauView(
        title=iteration_title(step), header=header, rows=tuple(rows)
    )


def _ratio_cell(ratio, show: bool, r_min, is_pivot_row: bool, number_format: str) -> TableauCell:
    if not show:
        return TableauCell("")
    if ratio is None:
        return TableauCell("—", frozenset({PIVOT_ROW}) if is_pivot_row else _NO_ROLES)
    roles = set()
    if is_pivot_row:
        roles.add(PIVOT_ROW)
    if r_min is not None and ratio == r_min:
        roles.add(MIN_RATIO)
    return TableauCell(format_value(ratio, number_format), frozenset(roles))
