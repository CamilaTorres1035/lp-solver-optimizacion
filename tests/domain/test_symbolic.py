"""
Pruebas unitarias para ValorM (número simbólico a + bM).
Ejecutar: python -m unittest tests/domain/test_symbolic.py -v
"""
import unittest
from fractions import Fraction

from src.domain.solver.symbolic import ValorM


def F(n, d=None) -> Fraction:
    if d is None:
        return Fraction(n)
    return Fraction(n, d)


# ====================================================================== #
#  Construcción y predicados
# ====================================================================== #

class TestConstruction(unittest.TestCase):
    def test_default_is_zero(self):
        v = ValorM()
        self.assertEqual(v.constant, F(0))
        self.assertEqual(v.m_coeff, F(0))
        self.assertTrue(v.is_zero)

    def test_from_int(self):
        v = ValorM(5, 2)
        self.assertEqual(v.constant, F(5))
        self.assertEqual(v.m_coeff, F(2))

    def test_from_fraction(self):
        v = ValorM(F(1, 2), F(-3, 4))
        self.assertEqual(v.constant, F(1, 2))
        self.assertEqual(v.m_coeff, F(-3, 4))

    def test_from_pure_number_valor_m(self):
        # Pasar un ValorM puro como argumento debe funcionar
        v = ValorM(ValorM(5), 3)
        self.assertEqual(v.constant, F(5))
        self.assertEqual(v.m_coeff, F(3))

    def test_from_non_pure_valor_m_raises(self):
        with self.assertRaises(ValueError):
            ValorM(ValorM(1, 2), 3)  # El primer arg tiene M

    def test_is_pure_number(self):
        self.assertTrue(ValorM(5, 0).is_pure_number)
        self.assertFalse(ValorM(5, 1).is_pure_number)

    def test_to_fraction(self):
        self.assertEqual(ValorM(5, 0).to_fraction(), F(5))
        with self.assertRaises(ValueError):
            ValorM(5, 1).to_fraction()


# ====================================================================== #
#  Operaciones aritméticas
# ====================================================================== #

class TestArithmetic(unittest.TestCase):
    def test_add_two_valor_m(self):
        a = ValorM(3, 2)    # 2M + 3
        b = ValorM(5, -1)   # -M + 5
        result = a + b      # M + 8
        self.assertEqual(result, ValorM(8, 1))

    def test_add_with_int(self):
        v = ValorM(3, 2)
        self.assertEqual(v + 5, ValorM(8, 2))
        self.assertEqual(5 + v, ValorM(8, 2))  # reflexivo

    def test_add_with_fraction(self):
        v = ValorM(3, 2)
        self.assertEqual(v + F(1, 2), ValorM(F(7, 2), 2))
        self.assertEqual(F(1, 2) + v, ValorM(F(7, 2), 2))

    def test_sub(self):
        a = ValorM(3, 2)
        b = ValorM(5, 1)
        self.assertEqual(a - b, ValorM(-2, 1))
        self.assertEqual(10 - a, ValorM(7, -2))

    def test_neg(self):
        v = ValorM(3, 2)
        self.assertEqual(-v, ValorM(-3, -2))

    def test_mul_by_scalar(self):
        v = ValorM(3, 2)    # 2M + 3
        self.assertEqual(v * 5, ValorM(15, 10))  # 10M + 15
        self.assertEqual(5 * v, ValorM(15, 10))  # reflexivo
        self.assertEqual(v * F(1, 2), ValorM(F(3, 2), 1))  # M + 3/2

    def test_mul_two_valor_m_with_m_raises(self):
        a = ValorM(1, 1)  # M + 1
        b = ValorM(2, 1)  # M + 2
        with self.assertRaises(ValueError):
            a * b  # M² no soportado

    def test_mul_pure_by_with_m(self):
        # (5) * (M + 2) = 5M + 10
        pure = ValorM(5, 0)
        with_m = ValorM(2, 1)
        self.assertEqual(pure * with_m, ValorM(10, 5))
        self.assertEqual(with_m * pure, ValorM(10, 5))

    def test_div_by_scalar(self):
        v = ValorM(6, 4)    # 4M + 6
        self.assertEqual(v / 2, ValorM(3, 2))  # 2M + 3
        self.assertEqual(v / F(1, 2), ValorM(12, 8))

    def test_div_by_zero_raises(self):
        with self.assertRaises(ZeroDivisionError):
            ValorM(1, 1) / 0

    def test_div_by_valor_m_with_m_raises(self):
        with self.assertRaises(ValueError):
            ValorM(1, 1) / ValorM(1, 1)

    def test_rtruediv_pure(self):
        # 10 / (2) = 5
        v = ValorM(2, 0)
        self.assertEqual(10 / v, ValorM(5, 0))

    def test_rtruediv_with_m_raises(self):
        with self.assertRaises(ValueError):
            10 / ValorM(2, 1)


# ====================================================================== #
#  Comparaciones (M primero, luego parte numérica)
# ====================================================================== #

class TestComparison(unittest.TestCase):
    def test_m_coeff_dominates(self):
        # 2M + 100 > 100M + 0? NO. 2M < 100M.
        a = ValorM(100, 2)    # 2M + 100
        b = ValorM(0, 100)    # 100M
        self.assertLess(a, b)

    def test_same_m_coeff_compares_constant(self):
    # -5/3 M + 11/6 vs -5/3 M + 7/3
    # Mismo coef de M (-5/3), entonces gana el menor constant: 7/3 < 11/6
        a = ValorM(F(11, 6), F(-5, 3))
        b = ValorM(F(7, 3), F(-5, 3))
        self.assertLess(a,b)

    def test_negative_m_is_less_than_positive(self):
        # -M < M
        self.assertLess(ValorM(0, -1), ValorM(0, 1))

    def test_negative_m_is_less_than_any_pure_number(self):
        # 10 - M < 3 (porque -M domina)
        self.assertLess(ValorM(10, -1), ValorM(3, 0))

    def test_positive_m_is_greater_than_any_pure_number(self):
        # 2M > 1000
        self.assertGreater(ValorM(0, 2), ValorM(1000, 0))

    def test_equality(self):
        self.assertEqual(ValorM(3, 2), ValorM(3, 2))
        self.assertNotEqual(ValorM(3, 2), ValorM(4, 2))
        self.assertNotEqual(ValorM(3, 2), ValorM(3, 3))

    def test_equality_with_fraction(self):
        # ValorM(5, 0) == 5
        self.assertEqual(ValorM(5, 0), 5)
        self.assertEqual(ValorM(5, 0), F(5))
        self.assertNotEqual(ValorM(5, 1), 5)

    def test_ordering_with_fraction(self):
        # 2M + 3 > 100
        self.assertGreater(ValorM(3, 2), 100)
        # -M + 5 < 0
        self.assertLess(ValorM(5, -1), 0)

    def test_hash_consistent_with_equality(self):
        a = ValorM(3, 2)
        b = ValorM(3, 2)
        self.assertEqual(hash(a), hash(b))
        # Pueden usarse en sets/dicts
        s = {a, b}
        self.assertEqual(len(s), 1)


# ====================================================================== #
#  Formato (M siempre primero, según documento)
# ====================================================================== #

class TestFormatting(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(str(ValorM(0, 0)), "0")

    def test_pure_number_int(self):
        self.assertEqual(str(ValorM(5, 0)), "5")
        self.assertEqual(str(ValorM(-3, 0)), "-3")

    def test_pure_number_fraction(self):
        self.assertEqual(str(ValorM(F(3, 2), 0)), "3/2")
        self.assertEqual(str(ValorM(F(-7, 4), 0)), "-7/4")

    def test_m_only(self):
        self.assertEqual(str(ValorM(0, 1)), "M")
        self.assertEqual(str(ValorM(0, -1)), "-M")

    def test_m_with_integer_coeff(self):
        self.assertEqual(str(ValorM(0, 2)), "2M")
        self.assertEqual(str(ValorM(0, -3)), "-3M")

    def test_m_with_fraction_coeff(self):
        # "-11/10 M" (del documento)
        self.assertEqual(str(ValorM(0, F(-11, 10))), "-11/10 M")
        self.assertEqual(str(ValorM(0, F(3, 4))), "3/4 M")

    def test_m_plus_positive_constant(self):
        # "2M + 3" (del documento)
        self.assertEqual(str(ValorM(3, 2)), "2M + 3")
        self.assertEqual(str(ValorM(F(2, 5), F(-11, 10))), "-11/10 M + 2/5")

    def test_m_minus_negative_constant(self):
        # "M - 5"
        self.assertEqual(str(ValorM(-5, 1)), "M - 5")
        self.assertEqual(str(ValorM(F(-3, 2), -1)), "-M - 3/2")

    def test_m_with_fraction_constant(self):
        self.assertEqual(str(ValorM(F(1, 2), 3)), "3M + 1/2")
        self.assertEqual(str(ValorM(F(-1, 2), 3)), "3M - 1/2")


# ====================================================================== #
#  Inmutabilidad
# ====================================================================== #

class TestImmutability(unittest.TestCase):
    def test_cannot_set_constant(self):
        v = ValorM(3, 2)
        with self.assertRaises(AttributeError):
            v.constant = 5  # type: ignore

    def test_cannot_set_m_coeff(self):
        v = ValorM(3, 2)
        with self.assertRaises(AttributeError):
            v.m_coeff = 1  # type: ignore

    def test_operations_return_new_instance(self):
        a = ValorM(3, 2)
        b = ValorM(5, 1)
        c = a + b
        self.assertIsNot(c, a)
        self.assertIsNot(c, b)
        # Los originales no cambiaron
        self.assertEqual(a, ValorM(3, 2))
        self.assertEqual(b, ValorM(5, 1))


# ====================================================================== #
#  Caso del documento: iteración 0 de minimización de Clase 10
# ====================================================================== #

class TestDocumentExample(unittest.TestCase):
    def test_clase_10_iteracion_0_fila_0(self):
        """
        Del documento, HU-06 caso 6:
        La fila 0 de la iteración 0 del ejemplo de minimización de clase
        debe tener coeficientes como (-11/10 M + 2/5, -9/10 M + 1/2, 0, 0, M, 0).
        
        Verificamos que el formato coincide exactamente con el documento.
        """
        c1 = ValorM(F(2, 5), F(-11, 10))
        c2 = ValorM(F(1, 2), F(-9, 10))
        c5 = ValorM(0, 1)

        self.assertEqual(str(c1), "-11/10 M + 2/5")
        self.assertEqual(str(c2), "-9/10 M + 1/2")
        self.assertEqual(str(c5), "M")

        # El orden correcto: c1 < c2 porque -11/10 < -9/10
        self.assertLess(c1, c2)


# ====================================================================== #

if __name__ == "__main__":
    unittest.main()