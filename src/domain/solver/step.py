from dataclasses import dataclass
from fractions import Fraction
from typing import Tuple, Optional, Any

@dataclass(frozen=True)
class PivotInfo:
    row: int
    column: int

@dataclass(frozen=True)
class Step:
    iteration: int
    row_labels: Tuple[str, ...]
    column_labels: Tuple[str, ...]
    tableau: Tuple[Tuple[Any, ...], ...]  # Any puede ser Fraction o ValorM
    basic_variables: Tuple[str, ...]
    ratios: Tuple[Optional[Fraction], ...]  # None si el coeficiente es <= 0
    pivot: Optional[PivotInfo]
    notes: Tuple[str, ...]
    justification: str
    # Campos específicos para Símplex Revisado (pueden ser None en Gran M, Solo se implementan si alcanza el tiempo)
    basis_matrix: Optional[Tuple[Tuple[Fraction, ...], ...]] = None
    inverse_basis: Optional[Tuple[Tuple[Fraction, ...], ...]] = None
    cost_basic: Optional[Tuple[Any, ...]] = None
    xb: Optional[Tuple[Fraction, ...]] = None
    multipliers: Optional[Tuple[Any, ...]] = None
    # HU-09: columna que entra en este paso. Coincide con pivot.column cuando hay pivote; también se llena cuando la variable entra pero no hay pivote (no acotado, límite de iteraciones) para poder resaltar la columna. None si ninguna variable entra (tableau final)
    entering_column: Optional[int] = None
    # HU-15: notas de la forma estándar (solo en el paso 0). Son un subconjunto de `notes`; la UI las muestra en su propia sección y no las repite en la iteración
    setup_notes: Tuple[str, ...] = ()
