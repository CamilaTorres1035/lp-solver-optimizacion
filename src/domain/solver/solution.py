from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Tuple, Optional, Any
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

@dataclass(frozen=True)
class Solution:
    status: SolutionStatus
    values: Tuple[Tuple[str, Fraction], ...]  # (nombre_variable, valor)
    optimal_value: Optional[Fraction]
    steps: Tuple[Step, ...]
    notes: Tuple[str, ...]
    message: str
    basis_info: Optional[BasisInfo]
    model_fingerprint: int  # Hash del modelo para invalidar en HU-05