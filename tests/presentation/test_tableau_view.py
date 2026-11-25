"""Pruebas del HTML del tableau (HU-09, caso de integración 4) y de la solución final (HU-15)."""
import re
import unittest
from fractions import Fraction as F

from application.step_navigation import TableauCell, TableauView, build_tableau_view
from domain.solver.big_m_simplex import BigMSimplexSolver
from presentation.components.solution_view import build_slack_rows
from presentation.components.tableau_view import (
    COLUMN_COLOR,
    ELEMENT_COLOR,
    ROW_COLOR,
    legend_html,
    render_tableau_html,
)
from utils.examples import get_example
from utils.formatting import DECIMAL_MODE


def _solve(key):
    model = get_example(key).to_model()
    return model, BigMSimplexSolver().solve(model)


def _cells(html):
    """[(clases, texto)] de cada celda del cuerpo, en orden."""
    body = html.split("<tbody>")[1]
    return re.findall(r'<td(?: class="([^"]*)")?(?: title="[^"]*")?>([^<]*)</td>', body)


class TestTableauHtml(unittest.TestCase):
    def setUp(self):
        _, s = _solve("wyndor")
        self.html = render_tableau_html(build_tableau_view(s.steps[0]))

    def test_colores_rojo_azul_amarillo(self):
        self.assertIn(COLUMN_COLOR, self.html)
        self.assertIn(ROW_COLOR, self.html)
        self.assertIn(ELEMENT_COLOR, self.html)

    def test_clases_aplicadas_a_las_celdas_correctas(self):
        cells = _cells(self.html)
        pivots = [text for classes, text in cells if "lp-pivot" in classes]
        self.assertEqual(pivots, ["2"])
        self.assertEqual(sum("lp-col" in c for c, _ in cells), 3)     # x2 en filas 0, 1 y 3
        mins = [text for classes, text in cells if "lp-min" in classes]
        self.assertEqual(mins, ["6"])
        self.assertIn('class="lp-col" title="Columna pivote (variable que entra)">x2</th>', self.html)

    def test_escapa_el_texto(self):
        view = TableauView(
            title="t",
            header=(TableauCell("<b>"), TableauCell("a&b")),
            rows=((TableauCell("<script>"), TableauCell("1")),),
        )
        html = render_tableau_html(view)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("a&amp;b", html)

    def test_leyenda(self):
        legend = legend_html()
        for text in ("Columna pivote", "Fila pivote", "Elemento pivote", "Razón mínima"):
            self.assertIn(text, legend)


class TestSolucionFinal(unittest.TestCase):
    def test_wyndor_holguras(self):
        model, s = _solve("wyndor")
        rows = build_slack_rows(model, s)
        self.assertEqual([r["Restricción"] for r in rows],
                         ["Restricción 1", "Restricción 2", "Restricción 3"])
        self.assertEqual([r["Tipo"] for r in rows], ["Holgura"] * 3)
        self.assertEqual([r["Valor"] for r in rows], ["2", "0", "0"])

    def test_dieta_holgura_igualdad_y_exceso(self):
        model, s = _solve("min_dieta")
        rows = build_slack_rows(model, s)
        self.assertEqual([r["Tipo"] for r in rows],
                         ["Holgura", "Igualdad (sin holgura)", "Exceso"])
        self.assertEqual(rows[2]["Valor"], "3/10")
        self.assertEqual(build_slack_rows(model, s, DECIMAL_MODE)[2]["Valor"], "0.3")

    def test_rubrica_2_usa_el_modelo_original(self):
        """La restricción 3 se multiplicó por −1 dentro del solver, pero se informa como ≥."""
        model, s = _solve("rubrica_2")
        rows = build_slack_rows(model, s)
        self.assertEqual(rows[2]["Tipo"], "Exceso")
        self.assertIn("≥", rows[2]["Expresión"])
        self.assertEqual([r["Valor"] for r in rows], ["0", "1", "0"])
        self.assertEqual(s.slacks, (F(0), F(1), F(0)))


if __name__ == "__main__":
    unittest.main()
