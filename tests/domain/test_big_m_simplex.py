import unittest
from fractions import Fraction as F

from domain.model.lp_model import build_model
from domain.solver.big_m_simplex import BigMSimplexSolver
from domain.solver.linalg import pivot_matrix
from domain.solver.solution import SolutionStatus
from domain.solver.symbolic import ValorM
from utils.examples import get_example


def _solve(key):
    return BigMSimplexSolver().solve(get_example(key).to_model())


def _path(solution):
    """[(entra, sale), ...] según el contrato de Step."""
    return [(s.column_labels[s.pivot.column], s.basic_variables[s.pivot.row - 1])
            for s in solution.steps if s.pivot]


class TestGranMSoloMenorIgual(unittest.TestCase):
    def test_wyndor_camino_y_resultado(self):
        s = _solve("wyndor")
        self.assertEqual(s.status, SolutionStatus.OPTIMA)
        self.assertEqual(dict(s.values), {"x1": F(2), "x2": F(6)})
        self.assertEqual(s.optimal_value, F(36))
        self.assertEqual(_path(s), [("x2", "S2"), ("x1", "S3")])
        self.assertEqual(len(s.steps), 3)
        self.assertEqual(s.steps[0].ratios, (None, F(6), F(9)))
        self.assertIsNone(s.steps[-1].pivot)
        self.assertEqual(s.slacks, (F(2), F(0), F(0)))

    def test_rubrica_1(self):
        s = _solve("rubrica_1")
        self.assertEqual(dict(s.values), {"x1": F(42), "x2": F(16)})
        self.assertEqual(s.optimal_value, F(3380))
        self.assertEqual(s.slacks, (F(0), F(0), F(24)))

    def test_rubrica_3(self):
        s = _solve("rubrica_3")
        self.assertEqual([v for _, v in s.values], [F(0), F(100), F(230)])
        self.assertEqual(s.optimal_value, F(1350))
        self.assertEqual(s.slacks, (F(0), F(0), F(20)))

    def test_sin_artificiales_si_solo_menor_igual(self):
        s = _solve("wyndor")
        self.assertFalse(any(l.startswith("R") and l[1:].isdigit() for l in s.steps[0].column_labels))


class TestGranMArtificiales(unittest.TestCase):
    def test_dieta_fila_0_iteracion_0(self):
        s0 = _solve("min_dieta").steps[0]
        self.assertEqual(s0.column_labels,
                         ("Z", "x1", "x2", "S1", "R2", "S3", "R3", "RHS"))
        row0 = s0.tableau[0]
        self.assertEqual(row0[0], ValorM(-1))                 # columna Z de la fila -Z
        self.assertEqual(row0[1], ValorM(F(2, 5), F(-11, 10)))
        self.assertEqual(row0[2], ValorM(F(1, 2), F(-9, 10)))
        self.assertEqual(row0[5], ValorM(0, 1))               # exceso S3 -> M

    def test_dieta_camino_y_resultado(self):
        s = _solve("min_dieta")
        self.assertEqual(_path(s), [("x1", "S1"), ("x2", "R3"), ("S3", "R2")])
        self.assertEqual(dict(s.values), {"x1": F(15, 2), "x2": F(9, 2)})
        self.assertEqual(s.optimal_value, F(21, 4))
        self.assertEqual(s.steps[-1].tableau[0][-1], ValorM(F(-21, 4)))  # RHS = -Z
        self.assertEqual(s.slacks, (F(0), F(0), F(3, 10)))

    def test_rubrica_2_min_igualdad_y_rhs_negativo(self):
        s = _solve("rubrica_2")
        self.assertEqual(dict(s.values), {"x1": F(2, 5), "x2": F(9, 5)})
        self.assertEqual(s.optimal_value, F(17, 5))
        self.assertEqual(s.slacks, (F(0), F(1), F(0)))        # sobre el modelo ORIGINAL
        self.assertEqual(s.basis_info.rhs_sign_flipped, (False, False, True))
        self.assertTrue(any("multiplicó por −1" in n for n in s.steps[0].notes))

    def test_rubrica_4_no_factible(self):
        s = _solve("rubrica_4")
        self.assertEqual(s.status, SolutionStatus.NO_FACTIBLE)
        self.assertEqual(s.values, ())
        self.assertIsNone(s.optimal_value)

    def test_rubrica_5_no_acotado(self):
        s = _solve("rubrica_5")
        self.assertEqual(s.status, SolutionStatus.NO_ACOTADA)
        self.assertEqual(_path(s), [("x1", "S1")])   # luego x2 no tiene fila que salga

    def test_ejemplo_a_mano_min(self):
        model = build_model("min", ["2", "3"], [
            {"coefficients": ["1", "1"], "relation": ">=", "rhs": "4"},
            {"coefficients": ["1", "3"], "relation": "<=", "rhs": "9"},
        ])
        s = BigMSimplexSolver().solve(model)
        self.assertEqual(dict(s.values), {"x1": F(4), "x2": F(0)})
        self.assertEqual(s.optimal_value, F(8))
        self.assertEqual(s.slacks, (F(0), F(5)))
        self.assertEqual(_path(s), [("x1", "R1")])
        self.assertEqual(s.steps[0].tableau[0][1], ValorM(2, -1))       # 2 - M
        self.assertEqual(s.steps[-1].tableau[0][-1], ValorM(-8))


class TestPivoteConValorM(unittest.TestCase):
    def test_pivot_matrix_acepta_fila_0_con_valorm(self):
        m = ((ValorM(2, -1), ValorM(0)), (F(1), F(4)))
        r = pivot_matrix(m, 1, 0)
        self.assertEqual(r[0][0], ValorM(0))
        self.assertEqual(r[0][1], ValorM(-8, 4))                       # 0 − (2−M)·4 = 4M − 8


class TestGranMEstabilidad(unittest.TestCase):
    def test_todos_los_ejemplos_terminan_sin_excepcion(self):
        from utils.examples import list_all_examples
        for ex in list_all_examples():
            with self.subTest(ex.key):
                s = BigMSimplexSolver().solve(ex.to_model())
                self.assertIsNotNone(s.status)
                self.assertGreater(len(s.steps), 0)


if __name__ == "__main__":
    unittest.main()