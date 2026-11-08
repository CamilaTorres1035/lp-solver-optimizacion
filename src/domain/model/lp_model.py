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


def build_model(
    sense: OptimizationSense | str,
    objective: Sequence[Any],
    constraints_data: Sequence[Mapping[str, Any]],
) -> LPModel:
    """
    Construye un LPModel inmutable

    Esta función verifica estructura:
    - objetivo con coeficientes,
    - restricciones existentes,
    - dimensiones consistentes.

    La validación semántica completa corresponde a HU-02:
    - celdas vacías con ubicación exacta,
    - máximo 20 variables,
    - máximo 20 restricciones,
    - mensajes por fila/columna,
    - etc.

    Nota:
        Este parser exacto mínimo puede extraerse luego a
        domain/validation/parsing.py cuando se implemente HU-02
    """
    parsed_sense = _parse_sense(sense)
    parsed_objective = tuple(_to_fraction(value) for value in objective)
    n_variables = len(parsed_objective)

    constraints = tuple(
        Constraint(
            coefficients=tuple(
                _to_fraction(value) for value in row["coefficients"]
            ),
            relation=_parse_relation(row["relation"]),
            rhs=_to_fraction(row["rhs"]),
            original_index=index + 1,
        )
        for index, row in enumerate(constraints_data)
    )

    return LPModel(
        sense=parsed_sense,
        objective=parsed_objective,
        constraints=constraints,
        n_variables=n_variables,
    )


def _parse_sense(value: OptimizationSense | str) -> OptimizationSense:
    if isinstance(value, OptimizationSense):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("max", "maximize", "maximizar"):
            return OptimizationSense.MAXIMIZE
        if normalized in ("min", "minimize", "minimizar"):
            return OptimizationSense.MINIMIZE

    raise ValueError(f"Sentido de optimización no válido: {value}")


def _parse_relation(value: Relation | str) -> Relation:
    if isinstance(value, Relation):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()

        if normalized in ("<=", "≤", "le"):
            return Relation.LESS_EQUAL
        if normalized in (">=", "≥", "ge"):
            return Relation.GREAT_EQUAL
        if normalized in ("=", "==", "eq"):
            return Relation.EQUAL

    raise ValueError(f"Relación no válida: {value}")


def _to_fraction(value: Any) -> Fraction:
    """
    Convierte una entrada exacta a Fraction

    Acepta:
    - int
    - Fraction
    - str: "3", "-2", "3/2", "0.5", "0,5"

    No acepta float para evitar errores binarios de precisión
    """
    if isinstance(value, Fraction):
        return value

    if isinstance(value, int) and not isinstance(value, bool):
        return Fraction(value)

    if isinstance(value, str):
        text = value.strip().replace(",", ".")

        if text == "":
            raise ValueError("Celda vacía: se esperaba un número.")

        try:
            return Fraction(text)
        except (ValueError, ZeroDivisionError) as error:
            raise ValueError(f"'{value}' no es un número válido.") from error

    raise TypeError(
        f"Tipo no soportado para conversión exacta: {type(value).__name__}"
    )