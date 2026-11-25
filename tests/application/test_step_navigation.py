"""Pruebas de navegación (HU-08) y roles de resaltado (HU-09). Sin Streamlit."""
import unittest

from application.step_navigation import (
    MIN_RATIO,
    PIVOT_COLUMN,
    PIVOT_ELEMENT,
    PIVOT_ROW,
    build_tableau_view,
    clamp_step,
    iteration_title,
)
from domain.solver.big_m_simplex import BigMSimplexSolver
from utils.examples import get_example, list_all_examples
from utils.formatting import DECIMAL_MODE


def _solve(key):
    return BigMSimplexSolver().solve(get_example(key).to_model())


def _texts(row):
    return [c.text for c in row]


def _cells_with(view, role):
    """(fila, columna) de las celdas del cuerpo que tienen el rol."""
    return {
        (i, j)
        for i, row in enumerate(view.rows)
        for j, cell in enumerate(row)
        if role in cell.roles
    }


class TestClampStep(unittest.TestCase):
    def test_mantiene_el_indice_en_rango(self):
        self.assertEqual(clamp_step(-1, 3), 0)
        self.assertEqual(clamp_step(0, 3), 0)
        self.assertEqual(clamp_step(2, 3), 2)
        self.assertEqual(clamp_step(3, 3), 2)      # avanzar en la última se queda en la última
        self.assertEqual(clamp_step(99, 1), 0)

    def test_sin_iteraciones_devuelve_cero(self):
        self.assertEqual(clamp_step(5, 0), 0)


class TestTableauWyndor(unittest.TestCase):
    """Iteración 0 de Wyndor: el ejemplo de la HU-09."""

    def setUp(self):
        self.step = _solve("wyndor").steps[0]
        self.view = build_tableau_view(self.step)

    def test_formato_de_clase(self):
        self.assertEqual(
            _texts(self.view.header),
            ["Ec #", "VB", "Z", "x1", "x2", "S1", "S2", "S3", "Lado derecho", "Razón"],
        )
        self.assertEqual(_texts(self.view.rows[0])[:3], ["0", "Z", "1"])
        self.assertEqual([r[1].text for r in self.view.rows[1:]], ["S1", "S2", "S3"])

    def test_columna_razon(self):
        self.assertEqual([r[-1].text for r in self.view.rows], ["", "—", "6", "9"])

    def test_pivote_resaltado(self):
        col_x2 = 2 + self.step.column_labels.index("x2")       # +2 por Ec # y VB
        self.assertEqual(_cells_with(self.view, PIVOT_ELEMENT), {(2, col_x2)})
        self.assertEqual(self.view.rows[2][col_x2].text, "2")
        self.assertIn(PIVOT_COLUMN, self.view.header[col_x2].roles)
        self.assertEqual({j for _, j in _cells_with(self.view, PIVOT_COLUMN)}, {col_x2})
        self.assertEqual({i for i, _ in _cells_with(self.view, PIVOT_ROW)}, {2})
        self.assertEqual(_cells_with(self.view, MIN_RATIO), {(2, len(self.view.header) - 1)})

    def test_titulo(self):
        self.assertEqual(self.view.title, "Iteración 0: entra x2, sale S2")

    def test_justificacion_con_cifras(self):
        text = self.step.justification
        for piece in ("Entra x2", "(-5)", "12/2 = 6", "18/2 = 9", "sale S2", "Pivote = 2"):
            self.assertIn(piece, text)


class TestTableauCasos(unittest.TestCase):
    def test_fila_0_con_m_y_minimizacion(self):
        view = build_tableau_view(_solve("min_dieta").steps[0], minimize=True)
        self.assertEqual(view.rows[0][1].text, "−Z")
        self.assertIn("-11/10 M + 2/5", _texts(view.rows[0]))

    def test_formato_decimal(self):
        view = build_tableau_view(_solve("min_dieta").steps[0], minimize=True,
                                  number_format=DECIMAL_MODE)
        self.assertIn("-1.1M + 0.4", _texts(view.rows[0]))

    def test_tableau_final_sin_resaltado_ni_razones(self):
        view = build_tableau_view(_solve("wyndor").steps[-1])
        self.assertEqual(view.title, "Iteración 2: tableau final")
        self.assertTrue(all(r[-1].text == "" for r in view.rows))
        for role in (PIVOT_COLUMN, PIVOT_ROW, PIVOT_ELEMENT, MIN_RATIO):
            self.assertEqual(_cells_with(view, role), set())

    def test_empate_de_razones_destaca_ambas(self):
        view = build_tableau_view(_solve("rubrica_7").steps[0])
        ratio_col = len(view.header) - 1
        self.assertEqual(_cells_with(view, MIN_RATIO), {(1, ratio_col), (2, ratio_col)})
        self.assertEqual({i for i, _ in _cells_with(view, PIVOT_ROW)}, {1})   # sale S1

    def test_no_acotado_resalta_la_columna_sin_fila(self):
        step = _solve("rubrica_5").steps[-1]
        view = build_tableau_view(step)
        col_x2 = 2 + step.column_labels.index("x2")
        self.assertEqual({j for _, j in _cells_with(view, PIVOT_COLUMN)}, {col_x2})
        self.assertEqual(_cells_with(view, PIVOT_ROW), set())
        self.assertEqual(_cells_with(view, PIVOT_ELEMENT), set())
        self.assertEqual([r[-1].text for r in view.rows[1:]], ["—", "—"])
        self.assertIn("no se pivotea", iteration_title(step))

    def test_todos_los_pasos_de_todos_los_ejemplos(self):
        """Cada paso se puede dibujar y hay a lo sumo un elemento pivote."""
        for ex in list_all_examples():
            model = ex.to_model()
            s = BigMSimplexSolver().solve(model)
            for step in s.steps:
                with self.subTest(ex=ex.key, k=step.iteration):
                    view = build_tableau_view(step, minimize=model.sense.value == "min")
                    self.assertEqual(len(view.rows), len(step.tableau))
                    self.assertTrue(all(len(r) == len(view.header) for r in view.rows))
                    expected = 1 if step.pivot is not None else 0
                    self.assertEqual(len(_cells_with(view, PIVOT_ELEMENT)), expected)


if __name__ == "__main__":
    unittest.main()
