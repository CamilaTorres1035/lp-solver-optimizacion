import unittest
from fractions import Fraction

from domain.model.enums import OptimizationSense, Relation
from domain.model.lp_model import Constraint, LPModel
from domain.validation.parsing import (
    MAX_CONSTRAINTS,
    MAX_VARIABLES,
    _build_model,
    _collect_form_shape_errors,
    _collect_numeric_errors,
    _collect_option_errors,
    _collect_size_errors,
    _parse_relation,
    _parse_sense,
    _to_fraction,
    validate_model_form,
)

class TestParsing(unittest.TestCase):
    def test_to_fraction_accepts_supported_number_formats(self):
        """Convierte a Fraction enteros, decimales y fracciones."""
        cases = [
            ("3", Fraction(3)),
            ("-2", Fraction(-2)),
            ("1.5", Fraction(3, 2)),
            ("1,5", Fraction(3, 2)),
            ("3/2", Fraction(3, 2)),
        ]

        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(_to_fraction(text), expected)

    def test_to_fraction_rejects_invalid_text(self):
        """Rechaza texto vacío, formatos inválidos y denominador cero."""
        invalid_values = ["", "   ", "abc", "3/", "1/0"]

        for text in invalid_values:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    _to_fraction(text)

    def test_collect_numeric_errors_reports_and_accumulates_errors(self):
        """Ubica y recopila varios errores numéricos del formulario."""
        form = {
        "n_variables": 2,
        "objective": ["abc", "5"], # Error en los coef de la F.O
        "constraints": [
            # Error en x2 con xyz
            {"x1": "1", "x2": "xyz", "rel": "<=", "rhs": "10"},
            # Error en rhs con ""
            {"x1": "2", "x2": "0", "rel": ">=", "rhs": ""},
        ],
        }

        errors = _collect_numeric_errors(form=form)
        self.assertEqual(len(errors), 3)
        self.assertEqual(errors,
            [
            "Error en función objetivo, coeficiente de x1: 'abc' no es un número válido.",
            "Error en restricción 1, coeficiente de x2: 'xyz' no es un número válido.",
            "Error en restricción 2, lado derecho: Celda vacía: se esperaba un número.",
            ],
        )

    def test_collect_size_errors_accepts_valid_size(self):
        """Acepta un modelo dentro de los límites."""
    
        form = {
            "n_variables": 2,
            "objective": ["3", "5"],
            "constraints": [
                {"x1": "1", "x2": "0", "rel": "<=", "rhs": "4"},
            ],
        }

        self.assertEqual(_collect_size_errors(form), [])

    def test_collect_size_errors_reports_invalid_sizes_and_dimensions(self):
        """Reporta límites excedidos, ausencia de restricciones y dimensiones incorrectas."""
        cases = [
            (
                "sin variables",
                {
                    "n_variables": 0,
                    "objective": [],
                    "constraints": [{"x1": "1"}],
                },
                ["El modelo debe tener al menos una variable."],
            ),
            (
                "sin restricciones",
                {
                    "n_variables": 1,
                    "objective": ["1"],
                    "constraints": [],
                },
                ["El modelo debe tener al menos una restricción."],
            ),
            (
                "exceso de variables",
                {
                    "n_variables": MAX_VARIABLES + 1,
                    "objective": ["1"] * (MAX_VARIABLES + 1),
                    "constraints": [{}],
                },
                [f"El modelo no puede exceder {MAX_VARIABLES} variables."],
            ),
            (
                "exceso de restricciones",
                {
                    "n_variables": 1,
                    "objective": ["1"],
                    "constraints": [{}] * (MAX_CONSTRAINTS + 1),
                },
                [f"El modelo no puede exceder {MAX_CONSTRAINTS} restricciones."],
            ),
            (
                "dimensión del objetivo incorrecta",
                {
                    "n_variables": 2,
                    "objective": ["1"],
                    "constraints": [{}],
                },
                [
                    "La función objetivo tiene 1 coeficientes, "
                    "pero el modelo declara 2 variables."
                ],
            ),
        ]

        for name, form, expected_errors in cases:
            with self.subTest(case=name):
                self.assertEqual(_collect_size_errors(form), expected_errors)

    def test_collect_form_shape_errors_accepts_valid_form(self):
        """Acepta un formulario con estructura correcta."""
        form = {
            "sense": "max",
            "n_variables": 2,
            "objective": ["3", "5"],
            "constraints": [
                {"x1": "1", "x2": "0", "rel": "<=", "rhs": "4"},
            ],
        }

        self.assertEqual(_collect_form_shape_errors(form), [])

    def test_collect_form_shape_errors_reports_invalid_forms(self):
        """Reporta tipos incorrectos y campos requeridos ausentes."""
        cases = [
            (
                "formulario no es diccionario",
                [],
                ["El formulario debe ser un diccionario."],
            ),
            (
                "faltan campos",
                {},
                [
                    "Falta el campo 'sense'.",
                    "Falta el campo 'n_variables'.",
                    "Falta el campo 'objective'.",
                    "Falta el campo 'constraints'.",
                ],
            ),
            (
                "faltan campos de restricción",
                {
                    "sense": "max",
                    "n_variables": 1,
                    "objective": ["1"],
                    "constraints": [{}],
                },
                [
                    "Falta el coeficiente de x1 en la restricción 1.",
                    "Falta la relación en la restricción 1.",
                    "Falta el lado derecho en la restricción 1.",
                ],
            ),
            (
                "tipos incorrectos",
                {
                    "sense": 1,
                    "n_variables": True,
                    "objective": "1",
                    "constraints": [
                        {"x1": 1, "rel": 2, "rhs": 3},
                    ],
                },
                [
                    "El campo 'sense' debe ser texto.",
                    "El campo 'n_variables' debe ser un entero.",
                    "El campo 'objective' debe ser una lista.",
                    "El coeficiente de x1 en la restricción 1 debe ser texto.",
                    "La relación en la restricción 1 debe ser texto.",
                    "El lado derecho de la restricción 1 debe ser texto.",
                ],
            ),
        ]

        for name, form, expected_errors in cases:
            with self.subTest(case=name):
                self.assertEqual(
                    _collect_form_shape_errors(form),
                    expected_errors,
                )

    def test_parse_sense_accepts_valid_values(self):
        """Convierte los sentidos de optimización admitidos."""
        cases = [
            ("max", OptimizationSense.MAXIMIZE),
            (" MAXIMIZE ", OptimizationSense.MAXIMIZE),
            ("Maximizar", OptimizationSense.MAXIMIZE),
            ("min", OptimizationSense.MINIMIZE),
            (" MINIMIZE ", OptimizationSense.MINIMIZE),
            ("Minimizar", OptimizationSense.MINIMIZE),
            (OptimizationSense.MAXIMIZE, OptimizationSense.MAXIMIZE),
            (OptimizationSense.MINIMIZE, OptimizationSense.MINIMIZE),
        ]

        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(_parse_sense(value), expected)

    def test_parse_sense_rejects_invalid_value(self):
        """Rechaza un sentido de optimización inválido."""
        cases = [
            ("average", "Sentido de optimización no válido: average"),
            ("", "Sentido de optimización no válido: "),
        ]

        for value, expected_message in cases:
            with self.subTest(value=value):
                with self.assertRaises(ValueError) as context:
                    _parse_sense(value)

                self.assertEqual(str(context.exception), expected_message)

    def test_parse_relation_accepts_valid_values(self):
        """Convierte las relaciones admitidas."""
        cases = [
            ("<=", Relation.LESS_EQUAL),
            ("≤", Relation.LESS_EQUAL),
            (" LE ", Relation.LESS_EQUAL),
            (">=", Relation.GREAT_EQUAL),
            ("≥", Relation.GREAT_EQUAL),
            (" GE ", Relation.GREAT_EQUAL),
            ("=", Relation.EQUAL),
            ("==", Relation.EQUAL),
            (" EQ ", Relation.EQUAL),
            (Relation.LESS_EQUAL, Relation.LESS_EQUAL),
            (Relation.GREAT_EQUAL, Relation.GREAT_EQUAL),
            (Relation.EQUAL, Relation.EQUAL),
        ]

        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(_parse_relation(value), expected)

    def test_parse_relation_rejects_invalid_value(self):
        """Rechaza una relación inválida."""
        cases = [
            ("!=", "Relación no válida: !="),
            ("", "Relación no válida: "),
        ]

        for value, expected_message in cases:
            with self.subTest(value=value):
                with self.assertRaises(ValueError) as context:
                    _parse_relation(value)

                self.assertEqual(str(context.exception), expected_message)

    def test_collect_option_errors_reports_invalid_options(self):
        """Recopila errores de sentido y relaciones con su ubicación."""
        form = {
            "sense": "average",
            "constraints": [
                {"rel": "!="},
                {"rel": "<="},
                {"rel": "<"},
            ],
        }

        self.assertEqual(
            _collect_option_errors(form),
            [
                "Sentido de optimización no válido: average",
                "Restricción 1: Relación no válida: !=",
                "Restricción 3: Relación no válida: <",
            ],
        )

    def test_build_model_creates_model_with_fraction_values(self):
        """Construye el modelo y convierte sus datos a Fraction."""
        model = _build_model(
            sense="max",
            objective=["1.5", "-2"],
            constraints_data=[
                {
                    "coefficients": ["3/2", "0"],
                    "relation": "<=",
                    "rhs": "4.25",
                },
            ],
        )

        self.assertEqual(
            model,
            LPModel(
                sense=OptimizationSense.MAXIMIZE,
                objective=(Fraction(3, 2), Fraction(-2)),
                constraints=(
                    Constraint(
                        coefficients=(Fraction(3, 2), Fraction(0)),
                        relation=Relation.LESS_EQUAL,
                        rhs=Fraction(17, 4),
                        original_index=1,
                    ),
                ),
                n_variables=2,
            ),
        )

    def test_validate_model_form_returns_model_for_valid_form(self):
        """Devuelve el modelo cuando el formulario es válido."""
        form = {
            "sense": "min",
            "n_variables": 2,
            "objective": ["1,5", "-2"],
            "constraints": [
                {"x1": "3/2", "x2": "0", "rel": "<=", "rhs": "4.25"},
            ],
        }

        model, errors = validate_model_form(form)

        self.assertEqual(errors, [])
        self.assertEqual(
            model,
            LPModel(
                sense=OptimizationSense.MINIMIZE,
                objective=(Fraction(3, 2), Fraction(-2)),
                constraints=(
                    Constraint(
                        coefficients=(Fraction(3, 2), Fraction(0)),
                        relation=Relation.LESS_EQUAL,
                        rhs=Fraction(17, 4),
                        original_index=1,
                    ),
                ),
                n_variables=2,
            ),
        )

    def test_validate_model_form_returns_errors_for_invalid_form(self):
        """Devuelve errores y ningún modelo cuando el formulario es inválido."""
        form = {
            "sense": "average",
            "n_variables": 1,
            "objective": ["abc"],
            "constraints": [
                {"x1": "1", "rel": "!=", "rhs": "2"},
            ],
        }

        model, errors = validate_model_form(form)

        self.assertIsNone(model)
        self.assertEqual(
            errors,
            [
                "Error en función objetivo, coeficiente de x1: "
                "'abc' no es un número válido.",
                "Sentido de optimización no válido: average",
                "Restricción 1: Relación no válida: !=",
            ],
        )


if __name__ == "__main__":
    unittest.main()