"""Pruebas del caso de uso validate_model (HU-02). Sin Streamlit."""
import unittest
from fractions import Fraction as F

from application.use_cases.validate_model import parse_fraction, validate_model


class TestValidateModel(unittest.TestCase):
    def test_formulario_valido_devuelve_modelo(self):
        model, errors = validate_model({
            "sense": "max", "n_variables": 1, "objective": ["3"],
            "constraints": [{"x1": "1", "rel": "<=", "rhs": "4"}],
        })
        self.assertEqual(errors, [])
        self.assertEqual(model.objective, (F(3),))

    def test_formulario_invalido_devuelve_errores(self):
        model, errors = validate_model({
            "sense": "max", "n_variables": 1, "objective": ["abc"],
            "constraints": [{"x1": "1", "rel": "<=", "rhs": "4"}],
        })
        self.assertIsNone(model)
        self.assertTrue(errors)

    def test_parse_fraction_publico(self):
        self.assertEqual(parse_fraction("1,5"), F(3, 2))


if __name__ == "__main__":
    unittest.main()