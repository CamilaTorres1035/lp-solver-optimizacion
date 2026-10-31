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
    description: str
    # Campos específicos para Símplex Revisado (pueden ser None en Gran M, Solo se implementan si alcanza el tiempo)
    basis_matrix: Optional[Tuple[Tuple[Fraction, ...], ...]] = None
    inverse_basis: Optional[Tuple[Tuple[Fraction, ...], ...]] = None
    cost_basic: Optional[Tuple[Any, ...]] = None
    xb: Optional[Tuple[Fraction, ...]] = None
    multipliers: Optional[Tuple[Any, ...]] = None