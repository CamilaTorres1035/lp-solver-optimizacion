from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Tuple, Optional, Any

from ..model.enums import Relation
from .step import Step

class SolutionStatus(Enum):
    OPTIMA = "Óptima"
    NO_FACTIBLE = "No Factible"
    NO_ACOTADA = "No Acotada"
    LIMITE_ITERACIONES = "Límite de Iteraciones Alcanzado"
    ERROR = "Error Interno"

@dataclass(frozen=True)
class BasisInfo:
    basic_variables: Tuple[str, ...]
    basis_inverse: Tuple[Tuple[Fraction, ...], ...]
    row_to_constraint: Tuple[int, ...]  # Índice de la restricción original
    rhs_sign_flipped: Tuple[bool, ...]  # Si se multiplicó por -1
    sense_factor: int  # 1 para Max, -1 para Min (para ajustar Z final)

# Payload del método gráfico (solo lo produce GraphicalSolver)

@dataclass(frozen=True)
class GraphVertex:
    point: Tuple[Fraction, Fraction]
    is_feasible: bool
    z_value: Fraction
    
@dataclass(frozen=True)
class GraphLine:
    label: str
    coefficients: Tuple[Fraction, Fraction]
    relation: Relation
    rhs: Fraction
    p1: Optional[Tuple[Fraction, Fraction]]
    p2: Optional[Tuple[Fraction, Fraction]]
    
@dataclass(frozen=True)
class GraphicalResult:
    vertices: Tuple[GraphVertex, ...]
    region_polygon: Tuple[Tuple[Fraction, Fraction], ...]
    lines: Tuple[GraphLine, ...]
    window: Tuple[Fraction, Fraction, Fraction, Fraction]  # xmin, xmax, ymin, ymax

    # Todos los vértices óptimos detectados.
    optimal_vertices: Tuple[Tuple[Fraction, Fraction], ...]

    # Segmento óptimo entre extremos, solo si hay óptimos múltiples no constantes.
    optimal_segment: Optional[
        Tuple[Tuple[Fraction, Fraction], Tuple[Fraction, Fraction]]
    ]

    isoprofit_z: Optional[Fraction]
    isoprofit_segment: Optional[
        Tuple[Tuple[Fraction, Fraction], Tuple[Fraction, Fraction]]
    ]

    region_is_unbounded: bool
    improving_directions: Tuple[Tuple[Fraction, Fraction], ...]

@dataclass(frozen=True)
class Solution:
    status: SolutionStatus
    values: Tuple[Tuple[str, Fraction], ...]  # (nombre_variable, valor)
    optimal_value: Optional[Fraction]
    slacks: Tuple[Fraction, ...] # Una fracción por restricción
    alt_values: Tuple[Tuple[str, Fraction], ...] 
    steps: Tuple[Step, ...]
    notes: Tuple[str, ...]
    message: str
    basis_info: Optional[BasisInfo]
    model_fingerprint: int  # Hash del modelo para invalidar en HU-05
    # HU-04: None en stub, Gran M y Revisado.
    graphical: Optional[GraphicalResult] = None