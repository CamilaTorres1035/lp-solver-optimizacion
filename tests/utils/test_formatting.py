"""Pruebas de format_value: números exactos y ValorM (fila 0 de Gran M)."""
import unittest
from fractions import Fraction as F

from domain.solver.symbolic import ValorM
from utils.formatting import DECIMAL_MODE, FRACTION_MODE, format_value


class TestFormatValue(unittest.TestCase):
    def test_numeros_se_formatean_igual_que_format_number(self):
        self.assertEqual(format_value(F(3, 2)), "3/2")
        self.assertEqual(format_value(F(3, 2), DECIMAL_MODE), "1.5")
        self.assertEqual(format_value(F(-5)), "-5")

    def test_valorm_sin_parte_m_es_un_numero(self):
        self.assertEqual(format_value(ValorM(F(-21, 4))), "-21/4")
        self.assertEqual(format_value(ValorM(F(-21, 4)), DECIMAL_MODE), "-5.25")
        self.assertEqual(format_value(ValorM(0)), "0")

    def test_modo_fraccion_coincide_con_str_de_valorm(self):
        casos = [ValorM(3, 2), ValorM(F(2, 5), F(-11, 10)), ValorM(0, -1),
                 ValorM(-5, 1), ValorM(F(1, 2), 3), ValorM(0, F(3, 4)),
                 ValorM(F(-3, 2), -1), ValorM(0, 1), ValorM(0, -3)]
        for v in casos:
            with self.subTest(v=repr(v)):
                self.assertEqual(format_value(v, FRACTION_MODE), str(v))

    def test_modo_decimal(self):
        self.assertEqual(format_value(ValorM(F(2, 5), F(-11, 10)), DECIMAL_MODE), "-1.1M + 0.4")
        self.assertEqual(format_value(ValorM(-5, 1), DECIMAL_MODE), "M - 5")
        self.assertEqual(format_value(ValorM(0, -1), DECIMAL_MODE), "-M")
        self.assertEqual(format_value(ValorM(3, 2), DECIMAL_MODE), "2M + 3")
        self.assertEqual(format_value(ValorM(F(1, 3), F(1, 3)), DECIMAL_MODE), "0.3333M + 0.3333")


if __name__ == "__main__":
    unittest.main()
