"""
Ejemplos precargados de problemas de Programación Lineal

Se separan en dos listas:
- PUBLIC_EXAMPLES: ejemplos clásicos reconocibles que se muestran en la UI
- RUBRIC_EXAMPLES: problemas de la rúbrica, solo para pruebas internas
- ALL_EXAMPLES: unión de ambas (uso exclusivo en tests)
"""
from dataclasses import dataclass
from typing import Tuple

from domain.model.enums import OptimizationSense
from domain.model.lp_model import LPModel, build_model


@dataclass(frozen=True)
class ConstraintExample:
    coefficients: Tuple[str, ...]
    relation: str
    rhs: str


@dataclass(frozen=True)
class LPExample:
    key: str
    name: str
    description: str
    sense: str
    objective: Tuple[str, ...]
    constraints: Tuple[ConstraintExample, ...]

    def to_model(self) -> LPModel:
        """Construye el LPModel a partir del ejemplo."""
        return build_model(
            sense=self.sense,
            objective=self.objective,
            constraints_data=[
                {
                    "coefficients": constraint.coefficients,
                    "relation": constraint.relation,
                    "rhs": constraint.rhs,
                }
                for constraint in self.constraints
            ],
        )


# EJEMPLOS PÚBLICOS (se muestran en la UI)
# Problemas clásicos reconocibles en el ámbito de investigación de operaciones

PUBLIC_EXAMPLES: Tuple[LPExample, ...] = (
    LPExample(
        key="wyndor",
        name="Mezcla de productos (Wyndor)",
        description=(
            "Problema clásico de Hillier & Lieberman. "
            "Maximizar la ganancia de dos productos con tres restricciones de capacidad."
        ),
        sense="max",
        objective=("3", "5"),
        constraints=(
            ConstraintExample(("1", "0"), "<=", "4"),
            ConstraintExample(("0", "2"), "<=", "12"),
            ConstraintExample(("3", "2"), "<=", "18"),
        ),
    ),
    LPExample(
        key="wyndor_igualdad",
        name="Wyndor con restricción de igualdad",
        description=(
            "Variante del problema Wyndor donde la tercera restricción "
            "se vuelve una igualdad exacta."
        ),
        sense="max",
        objective=("3", "5"),
        constraints=(
            ConstraintExample(("1", "0"), "<=", "4"),
            ConstraintExample(("0", "2"), "<=", "12"),
            ConstraintExample(("3", "2"), "=", "18"),
        ),
    ),
    LPExample(
        key="min_dieta",
        name="Problema de la dieta",
        description=(
            "Problema clásico de minimización de costos con restricciones "
            "de igualdad y mayor o igual. Requiere variables artificiales."
        ),
        sense="min",
        objective=("0.4", "0.5"),
        constraints=(
            ConstraintExample(("0.3", "0.1"), "=", "2.7"),
            ConstraintExample(("0.5", "0.5"), "=", "6"),
            ConstraintExample(("0.6", "0.4"), ">=", "6"),
        ),
    ),
    LPExample(
        key="no_factible_wyndor",
        name="Problema no factible",
        description=(
            "Variante de Wyndor con una restricción adicional incompatible. "
            "No existe solución que satisfaga todas las restricciones."
        ),
        sense="max",
        objective=("3", "5"),
        constraints=(
            ConstraintExample(("1", "0"), "<=", "4"),
            ConstraintExample(("0", "2"), "<=", "12"),
            ConstraintExample(("3", "2"), "<=", "18"),
            ConstraintExample(("3", "5"), ">=", "500"),
        ),
    ),
    LPExample(
        key="no_acotado_wyndor",
        name="Problema no acotado",
        description=(
            "Variante de Wyndor con una sola restricción. "
            "La función objetivo puede crecer sin límite."
        ),
        sense="max",
        objective=("3", "5"),
        constraints=(
            ConstraintExample(("1", "0"), "<=", "4"),
        ),
    ),
    LPExample(
        key="optimos_multiples_wyndor",
        name="Problema con óptimos múltiples",
        description=(
            "Variante de Wyndor donde la función objetivo es paralela "
            "a una restricción activa. Existen infinitas soluciones óptimas."
        ),
        sense="max",
        objective=("3", "2"),
        constraints=(
            ConstraintExample(("1", "0"), "<=", "4"),
            ConstraintExample(("0", "2"), "<=", "12"),
            ConstraintExample(("3", "2"), "<=", "18"),
        ),
    ),
    LPExample(
        key="empate_entrar_wyndor",
        name="Problema degenerado (empate al entrar)",
        description=(
            "Variante de Wyndor con empate en el criterio de la variable "
            "que entra. Se resuelve por la regla del menor índice."
        ),
        sense="max",
        objective=("3", "3"),
        constraints=(
            ConstraintExample(("1", "0"), "<=", "4"),
            ConstraintExample(("0", "2"), "<=", "12"),
            ConstraintExample(("3", "2"), "<=", "18"),
        ),
    ),
)


# EJEMPLOS DE RÚBRICA (solo para pruebas internas del equipo)
#!Estos NO se muestran en la UI

RUBRIC_EXAMPLES: Tuple[LPExample, ...] = (
    LPExample(
        key="rubrica_1",
        name="Rúbrica 1 — estándar, redundante, gráfico",
        description="Max 50x1 + 80x2 con restricciones <=.",
        sense="max",
        objective=("50", "80"),
        constraints=(
            ConstraintExample(("2", "1"), "<=", "100"),
            ConstraintExample(("1", "3"), "<=", "90"),
            ConstraintExample(("0", "1"), "<=", "40"),
        ),
    ),
    LPExample(
        key="rubrica_2",
        name="Rúbrica 2 — Min, =, >=, RHS negativo",
        description="Min 4x1 + x2 con igualdad, >= y RHS negativo.",
        sense="min",
        objective=("4", "1"),
        constraints=(
            ConstraintExample(("3", "1"), "=", "3"),
            ConstraintExample(("4", "3"), ">=", "6"),
            ConstraintExample(("-1", "-2"), ">=", "-4"),
        ),
    ),
    LPExample(
        key="rubrica_3",
        name="Rúbrica 3 — tres variables",
        description="Max 3x1 + 2x2 + 5x3.",
        sense="max",
        objective=("3", "2", "5"),
        constraints=(
            ConstraintExample(("1", "2", "1"), "<=", "430"),
            ConstraintExample(("3", "0", "2"), "<=", "460"),
            ConstraintExample(("1", "4", "0"), "<=", "420"),
        ),
    ),
    LPExample(
        key="rubrica_4",
        name="Rúbrica 4 — no factible",
        description="Max x1 + x2 con restricciones incompatibles.",
        sense="max",
        objective=("1", "1"),
        constraints=(
            ConstraintExample(("1", "1"), "<=", "2"),
            ConstraintExample(("1", "1"), ">=", "5"),
        ),
    ),
    LPExample(
        key="rubrica_5",
        name="Rúbrica 5 — no acotado",
        description="Max x1 + x2 con región no acotada.",
        sense="max",
        objective=("1", "1"),
        constraints=(
            ConstraintExample(("1", "-1"), "<=", "1"),
            ConstraintExample(("-1", "1"), "<=", "2"),
        ),
    ),
    LPExample(
        key="rubrica_6",
        name="Rúbrica 6 — óptimos múltiples",
        description="Max 2x1 + 4x2.",
        sense="max",
        objective=("2", "4"),
        constraints=(
            ConstraintExample(("1", "2"), "<=", "5"),
            ConstraintExample(("1", "1"), "<=", "4"),
        ),
    ),
    LPExample(
        key="rubrica_7",
        name="Rúbrica 7 — degenerado",
        description="Max 3x1 + 9x2 con empate en razón mínima.",
        sense="max",
        objective=("3", "9"),
        constraints=(
            ConstraintExample(("1", "4"), "<=", "8"),
            ConstraintExample(("1", "2"), "<=", "4"),
        ),
    ),
    LPExample(
        key="revisado_ejemplo_2",
        name="Simplex Revisado — Ejemplo 2",
        description="Max 5x1 + 4x2 con cuatro restricciones <=.",
        sense="max",
        objective=("5", "4"),
        constraints=(
            ConstraintExample(("6", "4"), "<=", "24"),
            ConstraintExample(("1", "2"), "<=", "6"),
            ConstraintExample(("-1", "1"), "<=", "1"),
            ConstraintExample(("0", "1"), "<=", "2"),
        ),
    ),
    LPExample(
        key="sensibilidad_con_ge",
        name="Sensibilidad con <= y >=",
        description="Max 5x1 + 4x2 con restricción >=.",
        sense="max",
        objective=("5", "4"),
        constraints=(
            ConstraintExample(("2", "1"), "<=", "20"),
            ConstraintExample(("1", "1"), "<=", "18"),
            ConstraintExample(("1", "2"), ">=", "12"),
        ),
    ),
)


# UNIÓN (solo para tests que necesitan recorrer todos)

ALL_EXAMPLES: Tuple[LPExample, ...] = PUBLIC_EXAMPLES + RUBRIC_EXAMPLES


# Funciones públicas

def list_public_examples() -> Tuple[LPExample, ...]:
    """Devuelve los ejemplos que se muestran en la UI"""
    return PUBLIC_EXAMPLES


def list_all_examples() -> Tuple[LPExample, ...]:
    """Devuelve todos los ejemplos (públicos + rúbrica), para tests"""
    return ALL_EXAMPLES


def get_example(key: str) -> LPExample:
    """Busca un ejemplo por su key en todos los disponibles"""
    for example in ALL_EXAMPLES:
        if example.key == key:
            return example

    raise KeyError(f"No existe un ejemplo con key='{key}'")