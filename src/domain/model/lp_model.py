from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Mapping, Sequence, Tuple

from .enums import OptimizationSense, Relation


@dataclass(frozen=True)
class Constraint:
    """
    Restricción inmutable del modelo original del usuario

    coefficients:
        Un coeficiente por variable de decisión

    relation:
        LESS_EQUAL, GREAT_EQUAL o EQUAL

    rhs:
        Lado derecho.

    original_index:
        Índice 1-based de la restricción original
        Permite mostrar R1, R2, R3...
    """
    coefficients: Tuple[Fraction, ...]
    relation: Relation
    rhs: Fraction
    original_index: int

    def __post_init__(self) -> None:
        if not self.coefficients:
            raise ValueError("Una restricción debe tener al menos un coeficiente.")
        if self.original_index < 1:
            raise ValueError("El índice original de la restricción debe ser >= 1.")


@dataclass(frozen=True)
class LPModel:
    """
    Modelo de Programación Lineal inmutable

    Solo representa la estructura matemática
    """
    sense: OptimizationSense
    objective: Tuple[Fraction, ...]
    constraints: Tuple[Constraint, ...]
    n_variables: int

    def __post_init__(self) -> None:
        if self.n_variables < 1:
            raise ValueError("Debe existir al menos una variable de decisión.")

        if len(self.objective) != self.n_variables:
            raise ValueError(
                "La función objetivo debe tener un coeficiente por variable."
            )

        if not self.constraints:
            raise ValueError("Debe existir al menos una restricción.")

        for constraint in self.constraints:
            if len(constraint.coefficients) != self.n_variables:
                raise ValueError(
                    f"Restricción R{constraint.original_index}: "
                    f"tiene {len(constraint.coefficients)} coeficientes, "
                    f"pero el modelo tiene {self.n_variables} variables."
                )

    @property
    def n_constraints(self) -> int:
        return len(self.constraints)

    def variable_name(self, index: int) -> str:
        """
        index es 0-based.
        """
        return f"x{index + 1}"

    def constraint_name(self, index: int) -> str:
        """
        index es 0-based.
        """
        return f"R{index + 1}"