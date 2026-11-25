import unittest
from fractions import Fraction as F
from unittest import mock

from domain.model.lp_model import build_model
from domain.model.enums import Relation
from domain.solver import big_m_simplex
from domain.solver.big_m_simplex import BigMSimplexSolver, _lhs
from domain.solver.linalg import pivot_matrix
from domain.solver.solution import SolutionStatus
from domain.solver.symbolic import ValorM
from domain.solver.graphical_solver import GraphicalSolver
from utils.examples import get_example, list_all_examples


def _solve(key):
    return BigMSimplexSolver().solve(get_example(key).to_model())

def _solve_model(sense, objective, constraints):
    rows = [{"coefficients": c, "relation": r, "rhs": b} for c, r, b in constraints]
    return BigMSimplexSolver().solve(build_model(sense, objective, rows))

def _path(solution):
    """[(entra, sale), ...] según el contrato de Step."""
    return [(s.column_labels[s.pivot.column], s.basic_variables[s.pivot.row - 1])
            for s in solution.steps if s.pivot]

def _points(solution):
    points = {tuple(v for _, v in solution.values)}
    if solution.alt_values:
        points.add(tuple(v for _, v in solution.alt_values))
    return points

def _slacks_at(model, values):
    """Holgura/exceso según la definición, sobre el modelo ORIGINAL del usuario."""
    point = tuple(v for _, v in values)
    result = []
    for c in model.constraints:
        lhs = sum((a * x for a, x in zip(c.coefficients, point)), F(0))
        if c.relation == Relation.LESS_EQUAL:
            result.append(c.rhs - lhs)
        elif c.relation == Relation.GREAT_EQUAL:
            result.append(lhs - c.rhs)
        else:
            result.append(F(0))
    return tuple(result)
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
        self.assertEqual(row0[0], ValorM(-1))
        self.assertEqual(row0[1], ValorM(F(2, 5), F(-11, 10)))
        self.assertEqual(row0[2], ValorM(F(1, 2), F(-9, 10)))
        self.assertEqual(row0[5], ValorM(0, 1))

    def test_dieta_camino_y_resultado(self):
        s = _solve("min_dieta")
        self.assertEqual(_path(s), [("x1", "S1"), ("x2", "R3"), ("S3", "R2")])
        self.assertEqual(dict(s.values), {"x1": F(15, 2), "x2": F(9, 2)})
        self.assertEqual(s.optimal_value, F(21, 4))
        self.assertEqual(s.steps[-1].tableau[0][-1], ValorM(F(-21, 4)))
        self.assertEqual(s.slacks, (F(0), F(0), F(3, 10)))

    def test_rubrica_2_min_igualdad_y_rhs_negativo(self):
        s = _solve("rubrica_2")
        self.assertEqual(dict(s.values), {"x1": F(2, 5), "x2": F(9, 5)})
        self.assertEqual(s.optimal_value, F(17, 5))
        self.assertEqual(s.slacks, (F(0), F(1), F(0)))
        self.assertEqual(s.basis_info.rhs_sign_flipped, (False, False, True))
        self.assertTrue(any("multiplicó por −1" in n for n in s.steps[0].notes))

    def test_ejemplo_a_mano_min(self):
        s = _solve_model("min", ["2", "3"], [
            (["1", "1"], ">=", "4"), (["1", "3"], "<=", "9")])
        self.assertEqual(dict(s.values), {"x1": F(4), "x2": F(0)})
        self.assertEqual(s.optimal_value, F(8))
        self.assertEqual(s.slacks, (F(0), F(5)))
        self.assertEqual(_path(s), [("x1", "R1")])
        self.assertEqual(s.steps[0].tableau[0][1], ValorM(2, -1))
        self.assertEqual(s.steps[-1].tableau[0][-1], ValorM(-8))


class TestFormatoDeNotas(unittest.TestCase):
    def test_lhs_signos_y_coeficientes(self):
        self.assertEqual(_lhs((F(1), F(2))), "x1 + 2·x2")
        self.assertEqual(_lhs((F(-1), F(-2))), "−x1 − 2·x2")
        self.assertEqual(_lhs((F(3, 2), F(0), F(-1), F(-5, 2))), "3/2·x1 − x3 − 5/2·x4")
        self.assertEqual(_lhs((F(0), F(0))), "0")
        self.assertEqual(_lhs((F(0), F(-1))), "−x2")
        self.assertEqual(_lhs((F(1), F(-1))), "x1 − x2")

    def test_nota_de_rhs_negativo_de_la_rubrica_2(self):
        nota = ("Restricción 3: −x1 − 2·x2 ≥ −4 se multiplicó por −1 "
                "→ x1 + 2·x2 ≤ 4.")
        s = _solve("rubrica_2")
        self.assertIn(nota, s.steps[0].notes)    # modo paso a paso
        self.assertIn(nota, s.notes)             # modo Directa (HU-15)

    def test_solution_notes_no_incluye_la_forma_aumentada(self):
        s = _solve("rubrica_2")
        self.assertFalse(any(n.startswith("Ec ") for n in s.notes))
        self.assertTrue(any(n.startswith("Ec ") for n in s.steps[0].notes))


class TestPivoteConValorM(unittest.TestCase):
    def test_pivot_matrix_acepta_fila_0_con_valorm(self):
        m = ((ValorM(2, -1), ValorM(0)), (F(1), F(4)))
        r = pivot_matrix(m, 1, 0)
        self.assertEqual(r[0][0], ValorM(0))
        self.assertEqual(r[0][1], ValorM(-8, 4))


class TestCasosEspeciales(unittest.TestCase):
    """HU-10: cada caso especial termina con un estado, nunca con una excepción."""

    # --- no factible ---
    def test_rubrica_4_no_factible(self):
        s = _solve("rubrica_4")
        self.assertEqual(s.status, SolutionStatus.NO_FACTIBLE)
        self.assertEqual(s.values, ())
        self.assertIsNone(s.optimal_value)
        self.assertIn("artificial R2", s.steps[-1].justification)

    def test_no_factible_wyndor(self):
        self.assertEqual(_solve("no_factible_wyndor").status, SolutionStatus.NO_FACTIBLE)

    def test_rayo_con_artificial_positiva_es_no_factible_no_no_acotado(self):
        # x2 podría crecer sin límite, pero x1 <= 2 y x1 >= 5 son incompatibles
        s = _solve_model("max", ["0", "1"], [
            (["1", "0"], "<=", "2"), (["1", "0"], ">=", "5")])
        self.assertEqual(s.status, SolutionStatus.NO_FACTIBLE)

    # --- no acotado ---
    def test_rubrica_5_no_acotado(self):
        s = _solve("rubrica_5")
        self.assertEqual(s.status, SolutionStatus.NO_ACOTADA)
        self.assertEqual(_path(s), [("x1", "S1")])
        self.assertIsNone(s.steps[-1].pivot)
        self.assertEqual(s.steps[-1].ratios, (None, None))

    def test_no_acotado_wyndor(self):
        self.assertEqual(_solve("no_acotado_wyndor").status, SolutionStatus.NO_ACOTADA)

    # --- degeneración ---
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

    # --- óptimos múltiples ---
    def test_rubrica_6_optimos_multiples(self):
        s = _solve("rubrica_6")
        self.assertEqual(dict(s.values), {"x1": F(0), "x2": F(5, 2)})
        self.assertEqual(dict(s.alt_values), {"x1": F(3), "x2": F(1)})
        self.assertEqual(s.optimal_value, F(10))
        self.assertEqual(_path(s), [("x2", "S1"), ("x1", "S2")])   # el 2.º es el extra
        self.assertEqual(len(s.steps), 3)
        self.assertEqual(s.steps[1].pivot.column, 1)
        self.assertIsNone(s.steps[-1].pivot)
        self.assertTrue(any("λA + (1−λ)B" in n for n in s.notes))

    def test_wyndor_optimos_multiples_orden_del_documento(self):
        s = _solve("optimos_multiples_wyndor")
        self.assertEqual(dict(s.values), {"x1": F(4), "x2": F(3)})
        self.assertEqual(dict(s.alt_values), {"x1": F(2), "x2": F(6)})
        self.assertEqual(s.optimal_value, F(18))

    def test_optimos_multiples_conservan_la_base_del_primer_optimo(self):
        s = _solve("rubrica_6")
        self.assertEqual(s.basis_info.basic_variables, ("x2", "S2"))

    def test_conjunto_optimo_no_acotado(self):
        s = _solve_model("max", ["1", "0"], [(["1", "0"], "<=", "4")])
        self.assertEqual(s.status, SolutionStatus.OPTIMA)
        self.assertEqual(s.alt_values, ())
        self.assertTrue(any("no acotado" in n for n in s.notes))

    # --- empate al entrar ---
    def test_empate_al_entrar_usa_menor_indice(self):
        s = _solve("empate_entrar_wyndor")
        self.assertEqual(s.steps[0].pivot.column, 1)   # entra x1
        self.assertIn("Empate entre x1, x2", s.steps[0].justification)
        self.assertEqual(s.optimal_value, F(24))

    # --- artificial en base con valor 0 ---
    def test_artificial_en_base_con_valor_cero(self):
        s = _solve_model("max", ["1", "0"], [
            (["1", "1"], "=", "2"), (["2", "2"], "=", "4")])
        self.assertEqual(s.status, SolutionStatus.OPTIMA)
        self.assertEqual(s.optimal_value, F(2))
        self.assertTrue(any("artificial R2" in n for n in s.steps[-1].notes))

    # --- ciclado y límite ---
    def test_ciclado_de_beale_se_resuelve_con_bland(self):
        s = _solve_model("min", ["-3/4", "20", "-1/2", "6"], [
            (["1/4", "-8", "-1", "9"], "<=", "0"),
            (["1/2", "-12", "-1/2", "3"], "<=", "0"),
            (["0", "0", "1", "0"], "<=", "1")])
        self.assertEqual(s.status, SolutionStatus.OPTIMA)
        self.assertEqual(s.optimal_value, F(-5, 4))
        self.assertEqual([v for _, v in s.values], [F(1), F(0), F(1), F(0)])
        ciclado = [st for st in s.steps if any("Ciclado" in n for n in st.notes)]
        self.assertEqual(len(ciclado), 1)
        # El tableau del paso donde se detecta repite el del paso 0 (misma base)
        self.assertEqual(ciclado[0].basic_variables, s.steps[0].basic_variables)
        self.assertIn("Bland", s.steps[ciclado[0].iteration].notes[0])

    def test_limite_de_iteraciones(self):
        with mock.patch.object(big_m_simplex, "MAX_ITERATIONS", 1):
            s = _solve("wyndor")
        self.assertEqual(s.status, SolutionStatus.LIMITE_ITERACIONES)
        self.assertEqual(s.values, ())
        self.assertIsNone(s.optimal_value)
        self.assertIsNone(s.steps[-1].pivot)
        self.assertEqual(s.steps[-1].ratios, (F(4), None, F(2)))   # razones con pivote None
        self.assertIn("límite de 1 iteraciones", s.steps[-1].justification)
        # se detiene en la iteración 1, cuando iba a entrar x1 (razones 4, —, 2)
        self.assertEqual(s.steps[-1].column_labels[s.steps[-1].entering_column], "x1")

    # --- transversal ---
    def test_ningun_ejemplo_lanza_excepcion(self):
        for ex in list_all_examples():
            with self.subTest(ex.key):
                s = BigMSimplexSolver().solve(ex.to_model())
                self.assertIn(s.status, {
                        SolutionStatus.OPTIMA, SolutionStatus.NO_FACTIBLE,
                        SolutionStatus.NO_ACOTADA, SolutionStatus.LIMITE_ITERACIONES,
                })
                self.assertGreater(len(s.steps), 0)
                if s.status != SolutionStatus.OPTIMA:
                    self.assertEqual(s.values, ())
    
    def test_razon_cero_sin_empate_no_genera_nota(self):
        s = _solve("rubrica_7")
        self.assertEqual(s.steps[1].ratios, (F(8), F(0)))
        self.assertEqual(s.steps[1].pivot.row, 2)
        self.assertFalse(any("Degeneración" in n for n in s.steps[1].notes))
    
    def test_contrato_de_step_en_todos_los_ejemplos(self):
        for ex in list_all_examples():
            with self.subTest(ex.key):
                model = ex.to_model()
                s = BigMSimplexSolver().solve(model)
                m = model.n_constraints
                for k, step in enumerate(s.steps):
                    self.assertEqual(step.iteration, k)
                    self.assertEqual(len(step.tableau), m + 1)
                    self.assertEqual(len(step.row_labels), m + 1)
                    self.assertEqual(len(step.basic_variables), m)
                    self.assertEqual(len(step.ratios), m)
                    self.assertEqual(len(step.column_labels), len(step.tableau[0]))
                    for i, name in enumerate(step.basic_variables, start=1):
                        col = step.column_labels.index(name)
                        self.assertEqual(step.tableau[i][col], 1)   # columna unitaria
                        self.assertEqual(step.tableau[0][col], 0)   # coste reducido nulo
                    # setup_notes: solo en el paso 0 y siempre dentro de notes
                    if k == 0:
                        self.assertTrue(step.setup_notes)
                        self.assertEqual(step.notes[:len(step.setup_notes)], step.setup_notes)
                    else:
                        self.assertEqual(step.setup_notes, ())
                    if step.pivot is None:
                        self.assertEqual(k, len(s.steps) - 1)       # terminal = último
                        # sin pivote: entering_column solo si el paso terminal no es óptimo
                        if step.entering_column is not None:
                            self.assertNotEqual(s.status, SolutionStatus.OPTIMA)
                    else:
                        self.assertEqual(step.entering_column, step.pivot.column)
                        entering = step.column_labels[step.pivot.column]
                        self.assertFalse(entering.startswith("R") and entering[1:].isdigit())
                        self.assertEqual(
                            s.steps[k + 1].tableau,
                            pivot_matrix(step.tableau, step.pivot.row, step.pivot.column),
                        )
    def test_paridad_grafico_y_gran_m(self):
        for ex in list_all_examples():
            model = ex.to_model()
            # el gráfico exige n=2; con objetivo constante los métodos difieren por decisión
            if model.n_variables != 2 or all(c == 0 for c in model.objective):
                continue
            with self.subTest(ex.key):
                g = GraphicalSolver().solve(model)
                s = BigMSimplexSolver().solve(model)
                self.assertEqual(s.status, g.status)
                self.assertEqual(s.optimal_value, g.optimal_value)
                if s.status == SolutionStatus.OPTIMA:
                    # el conjunto óptimo coincide; el orden NO es semántico
                    self.assertEqual(_points(s), _points(g))
                    # cada método reporta holguras de SU vértice principal
                    self.assertEqual(s.slacks, _slacks_at(model, s.values))
                    self.assertEqual(g.slacks, _slacks_at(model, g.values))


class TestDatosParaLaVista(unittest.TestCase):
    """Campos de Step que usa la interfaz: entering_column (HU-09) y setup_notes (HU-15)."""

    def test_no_acotado_informa_la_columna_que_entra(self):
        last = _solve("rubrica_5").steps[-1]
        self.assertIsNone(last.pivot)
        self.assertEqual(last.column_labels[last.entering_column], "x2")

    def test_rayo_no_factible_informa_la_columna_que_entra(self):
        s = _solve_model("max", ["0", "1"], [
            (["1", "0"], "<=", "2"), (["1", "0"], ">=", "5")])
        last = s.steps[-1]
        self.assertEqual(s.status, SolutionStatus.NO_FACTIBLE)
        self.assertIsNotNone(last.entering_column)

    def test_tableau_final_sin_columna_que_entra(self):
        for key in ("wyndor", "rubrica_4", "rubrica_6"):
            with self.subTest(key):
                self.assertIsNone(_solve(key).steps[-1].entering_column)

    def test_setup_notes_es_la_forma_estandar(self):
        setup = _solve("rubrica_2").steps[0].setup_notes
        self.assertTrue(setup[0].startswith("Minimización"))
        self.assertTrue(any("multiplicó por −1" in n for n in setup))
        self.assertEqual(sum(n.startswith("Ec ") for n in setup), 3)
        self.assertTrue(any(n.startswith("Preparación de la fila 0") for n in setup))

    def test_nota_de_degeneracion_no_es_parte_de_la_forma_estandar(self):
        step0 = _solve("rubrica_7").steps[0]
        extra = [n for n in step0.notes if n not in step0.setup_notes]
        self.assertEqual(len(extra), 1)
        self.assertTrue(extra[0].startswith("Degeneración"))


if __name__ == "__main__":
    unittest.main()
