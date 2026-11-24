import unittest
from fractions import Fraction as F
from unittest import mock

from domain.model.lp_model import build_model
from domain.solver import big_m_simplex
from domain.solver.big_m_simplex import BigMSimplexSolver
from domain.solver.linalg import pivot_matrix
from domain.solver.solution import SolutionStatus
from domain.solver.symbolic import ValorM
from utils.examples import get_example


def _solve(key):
    return BigMSimplexSolver().solve(get_example(key).to_model())

def _solve_model(sense, objective, constraints):
    rows = [{"coefficients": c, "relation": r, "rhs": b} for c, r, b in constraints]
    return BigMSimplexSolver().solve(build_model(sense, objective, rows))

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

class TestCasosEspeciales(unittest.TestCase):
    """HU-10: cada caso especial termina con un estado, nunca con una excepción."""
    def test_rayo_con_artificial_positiva_es_no_factible_no_no_acotado(self):
    # x2 podría crecer sin límite, pero x1 <= 2 y x1 >= 5 son incompatibles
        s = _solve_model("max", ["0", "1"], [
            (["1", "0"], "<=", "2"), (["1", "0"], ">=", "5")])
        self.assertEqual(s.status, SolutionStatus.NO_FACTIBLE)

    def test_rubrica_7_degenerado(self):
        s = _solve("rubrica_7")
        self.assertEqual(s.status, SolutionStatus.OPTIMA)
        self.assertEqual(s.steps[0].ratios, (F(2), F(2)))
        self.assertEqual(_path(s), [("x2", "S1"), ("x1", "S2")])
        self.assertEqual(dict(s.values), {"x1": F(0), "x2": F(2)})
        self.assertEqual(s.optimal_value, F(18))
        self.assertEqual(s.alt_values, ())
        self.assertEqual(s.steps[-1].basic_variables, ("x2", "x1"))  # x1 básica en 0
        self.assertTrue(any("Degeneración" in n for n in s.steps[0].notes))
        self.assertIn("menor índice", s.steps[0].justification)
    
    # --- empate al entrar --
    def test_empate_al_entrar_usa_menor_indice(self):
        s = _solve("empate_entrar_wyndor")
        self.assertEqual(s.steps[0].pivot.column, 1)   # entra x1
        self.assertIn("Empate entre x1, x2", s.steps[0].justification)
        self.assertEqual(s.optimal_value, F(24))
    
     # --- ciclado y límite --
    def test_ciclado_de_beale_se_resuelve_con_bland(self):
        s = _solve_model("min", ["-3/4", "20", "-1/2", "6"], [
            (["1/4", "-8", "-1", "9"], "<=", "0"),
            (["1/2", "-12", "-1/2", "3"], "<=", "0"),
            (["0", "0", "1", "0"], "<=", "1")])
        self.assertEqual(s.status, SolutionStatus.OPTIMA)
        self.assertEqual(s.optimal_value, F(-5, 4))
        self.assertEqual([v for _, v in s.values], [F(1), F(0), F(1), F(0)])
        ciclado = [st for st in s.steps if any("Ciclado" in n for n in st.notes)]
        self.assertEqual(len(ciclado), 1) # El tableau del paso donde se detecta repite el del paso 0 (misma base)
        self.assertEqual(ciclado[0].basic_variables, s.steps[0].basic_variables)
        self.assertIn("Bland", s.steps[ciclado[0].iteration].notes[0])
    
    def test_limite_de_iteraciones(self):
        with mock.patch.object(big_m_simplex, "MAX_ITERATIONS", 1):
            s = _solve("wyndor")
        self.assertEqual(s.status, SolutionStatus.LIMITE_ITERACIONES)
        self.assertEqual(s.values, ())
        self.assertIsNone(s.optimal_value)

if __name__ == "__main__":
    unittest.main()