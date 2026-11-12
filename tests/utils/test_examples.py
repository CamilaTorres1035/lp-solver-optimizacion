import unittest
from fractions import Fraction

from src.utils.examples import (
    get_example,
    list_public_examples,
    list_all_examples,
    PUBLIC_EXAMPLES,
    RUBRIC_EXAMPLES,
)


class TestExamplesSeparation(unittest.TestCase):
    """Verifica la separación arquitectónica entre ejemplos públicos y de rúbrica."""

    def test_public_examples_do_not_include_rubric(self):
        """Los ejemplos públicos NO deben tener key tipo 'rubrica_X'"""
        for example in PUBLIC_EXAMPLES:
            self.assertFalse(
                example.key.startswith("rubrica_"),
                f"El ejemplo público '{example.key}' no debería ser de rúbrica."
            )

    def test_rubric_examples_are_present(self):
        """Los 7 ejemplos de rúbrica deben estar en RUBRIC_EXAMPLES para pruebas internas"""
        rubric_keys = {ex.key for ex in RUBRIC_EXAMPLES}
        for i in range(1, 8):
            self.assertIn(f"rubrica_{i}", rubric_keys)

    def test_all_examples_is_union(self):
        """ALL_EXAMPLES debe ser la unión exacta de públicos y rúbrica"""
        all_examples = list_all_examples()
        self.assertEqual(
            len(all_examples),
            len(PUBLIC_EXAMPLES) + len(RUBRIC_EXAMPLES),
        )

    def test_public_examples_count(self):
        """Debe haber exactamente 7 ejemplos públicos bien documentados"""
        self.assertEqual(len(PUBLIC_EXAMPLES), 7)


class TestPublicExamples(unittest.TestCase):
    """Verifica que los ejemplos públicos se cargan y construyen correctamente"""

    def test_wyndor_exact_values(self):
        example = get_example("wyndor")
        model = example.to_model()

        self.assertEqual(model.n_variables, 2)
        self.assertEqual(model.n_constraints, 3)
        self.assertEqual(model.objective, (Fraction(3), Fraction(5)))
        self.assertEqual(model.constraints[0].rhs, Fraction(4))
        self.assertEqual(
            model.constraints[1].coefficients,
            (Fraction(0), Fraction(2)),
        )

    def test_min_dieta_is_minimization(self):
        example = get_example("min_dieta")
        model = example.to_model()
        self.assertEqual(model.sense.value, "min")

    def test_no_factible_wyndor_has_four_constraints(self):
        model = get_example("no_factible_wyndor").to_model()
        self.assertEqual(model.n_constraints, 4)

    def test_no_acotado_wyndor_has_one_constraint(self):
        model = get_example("no_acotado_wyndor").to_model()
        self.assertEqual(model.n_constraints, 1)

    def test_all_public_examples_have_description(self):
        """CRÍTICO PARA UX: Cada ejemplo público debe tener descripción para el usuario"""
        for example in PUBLIC_EXAMPLES:
            self.assertTrue(
                example.description.strip(),
                f"El ejemplo público '{example.key}' no tiene descripción."
            )

    def test_all_public_examples_build_valid_model(self):
        """Todos los ejemplos públicos deben construir un modelo válido sin lanzar excepciones"""
        for example in PUBLIC_EXAMPLES:
            with self.subTest(key=example.key):
                model = example.to_model()
                self.assertEqual(model.n_variables, len(example.objective))
                self.assertEqual(model.n_constraints, len(example.constraints))


class TestRubricExamples(unittest.TestCase):
    """Verifica que los ejemplos de rúbrica siguen funcionando para las pruebas del equipo"""

    def test_rubrica_1_exact_values(self):
        model = get_example("rubrica_1").to_model()
        self.assertEqual(model.objective, (Fraction(50), Fraction(80)))
        self.assertEqual(
            model.constraints[0].coefficients,
            (Fraction(2), Fraction(1)),
        )
        self.assertEqual(model.constraints[0].rhs, Fraction(100))

    def test_rubrica_2_has_negative_rhs(self):
        model = get_example("rubrica_2").to_model()
        self.assertEqual(model.constraints[2].rhs, Fraction(-4))

    def test_rubrica_3_has_three_variables(self):
        model = get_example("rubrica_3").to_model()
        self.assertEqual(model.n_variables, 3)


class TestGetExampleFunction(unittest.TestCase):
    def test_unknown_example_raises(self):
        with self.assertRaises(KeyError):
            get_example("no_existe")

    def test_can_get_rubric_example_by_key(self):
        """Aunque no estén en la UI, los de rúbrica siguen accesibles por key"""
        example = get_example("rubrica_1")
        self.assertEqual(example.key, "rubrica_1")


if __name__ == "__main__":
    unittest.main()