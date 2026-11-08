import unittest
from fractions import Fraction

from src.domain.model.enums import OptimizationSense, Relation
from src.domain.model.lp_model import build_model


class TestLPModel(unittest.TestCase):
    def test_build_wyndor_model(self):
        """Construye el modelo Wyndor correctamente."""
        model = build_model(
            sense=OptimizationSense.MAXIMIZE,
            objective=[3, 5],
            constraints_data=[
                {"coefficients": [1, 0], "relation": "<=", "rhs": 4},
                {"coefficients": [0, 2], "relation": "<=", "rhs": 12},
                {"coefficients": [3, 2], "relation": "<=", "rhs": 18},
            ],
        )

        self.assertEqual(model.sense, OptimizationSense.MAXIMIZE)
        self.assertEqual(model.n_variables, 2)
        self.assertEqual(model.n_constraints, 3)
        self.assertEqual(model.objective, (Fraction(3), Fraction(5)))
        self.assertEqual(model.constraints[0].relation, Relation.LESS_EQUAL)
        self.assertEqual(model.constraints[0].rhs, Fraction(4))

    def test_build_model_with_strings_and_fractions(self):
        """Convierte strings a Fraction correctamente."""
        model = build_model(
            sense="max",
            objective=["3/2", "0,5"],
            constraints_data=[
                {
                    "coefficients": ["1.5", "-2"],
                    "relation": ">=",
                    "rhs": "4",
                }
            ],
        )

        self.assertEqual(model.objective[0], Fraction(3, 2))
        self.assertEqual(model.objective[1], Fraction(1, 2))
        self.assertEqual(model.constraints[0].coefficients[0], Fraction(3, 2))
        self.assertEqual(model.constraints[0].relation, Relation.GREAT_EQUAL)

    def test_model_is_immutable(self):
        """El modelo no puede modificarse después de creado."""
        model = build_model(
            sense="max",
            objective=[1, 2],
            constraints_data=[
                {"coefficients": [1, 1], "relation": "<=", "rhs": 10}
            ],
        )

        with self.assertRaises(AttributeError):
            model.sense = OptimizationSense.MINIMIZE  # type: ignore

    def test_constraint_is_immutable(self):
        """Las restricciones no pueden modificarse después de creadas."""
        model = build_model(
            sense="max",
            objective=[1, 2],
            constraints_data=[
                {"coefficients": [1, 1], "relation": "<=", "rhs": 10}
            ],
        )

        with self.assertRaises(AttributeError):
            model.constraints[0].rhs = Fraction(20)  # type: ignore

    def test_empty_objective_raises(self):
        """Falla si no hay coeficientes en la función objetivo."""
        with self.assertRaises(ValueError):
            build_model(
                sense="max",
                objective=[],
                constraints_data=[
                    {"coefficients": [1], "relation": "<=", "rhs": 10}
                ],
            )

    def test_no_constraints_raises(self):
        """Falla si no hay restricciones."""
        with self.assertRaises(ValueError):
            build_model(
                sense="max",
                objective=[1, 2],
                constraints_data=[],
            )

    def test_dimension_mismatch_raises(self):
        """Falla si una restricción tiene distinto número de coeficientes."""
        with self.assertRaises(ValueError):
            build_model(
                sense="max",
                objective=[1, 2],
                constraints_data=[
                    {"coefficients": [1], "relation": "<=", "rhs": 10}
                ],
            )

    def test_invalid_relation_raises(self):
        """Falla si la relación no es válida."""
        with self.assertRaises(ValueError):
            build_model(
                sense="max",
                objective=[1, 2],
                constraints_data=[
                    {"coefficients": [1, 1], "relation": "><", "rhs": 10}
                ],
            )

    def test_non_numeric_coefficient_raises(self):
        """Falla si un coeficiente no es numérico."""
        with self.assertRaises(ValueError):
            build_model(
                sense="max",
                objective=["abc", 2],
                constraints_data=[
                    {"coefficients": [1, 1], "relation": "<=", "rhs": 10}
                ],
            )

    def test_float_is_rejected_to_preserve_exactness(self):
        """No acepta float para preservar exactitud."""
        with self.assertRaises(TypeError):
            build_model(
                sense="max",
                objective=[0.5, 2],
                constraints_data=[
                    {"coefficients": [1, 1], "relation": "<=", "rhs": 10}
                ],
            )

    def test_model_hash_is_stable(self):
        """Dos modelos idénticos tienen el mismo hash."""
        model_a = build_model(
            sense="max",
            objective=[3, 5],
            constraints_data=[
                {"coefficients": [1, 0], "relation": "<=", "rhs": 4}
            ],
        )

        model_b = build_model(
            sense="max",
            objective=[3, 5],
            constraints_data=[
                {"coefficients": [1, 0], "relation": "<=", "rhs": 4}
            ],
        )

        self.assertEqual(hash(model_a), hash(model_b))

    def test_variable_names(self):
        """Los nombres de variables son x1, x2, x3..."""
        model = build_model(
            sense="max",
            objective=[1, 2, 3],
            constraints_data=[
                {"coefficients": [1, 1, 1], "relation": "<=", "rhs": 10}
            ],
        )

        self.assertEqual(model.variable_name(0), "x1")
        self.assertEqual(model.variable_name(1), "x2")
        self.assertEqual(model.variable_name(2), "x3")

    def test_constraint_names(self):
        """Los nombres de restricciones son R1, R2, R3..."""
        model = build_model(
            sense="max",
            objective=[1, 2],
            constraints_data=[
                {"coefficients": [1, 1], "relation": "<=", "rhs": 10},
                {"coefficients": [2, 2], "relation": "<=", "rhs": 20},
            ],
        )

        self.assertEqual(model.constraint_name(0), "R1")
        self.assertEqual(model.constraint_name(1), "R2")


if __name__ == "__main__":
    unittest.main()