"""Pruebas de la figura y la tabla del método gráfico (HU-04, caso 8 de 7.1)."""
import unittest
from fractions import Fraction as F

from domain.model.enums import OptimizationSense
from domain.solver.graphical_solver import GraphicalSolver
from domain.validation.parsing import validate_model_form
from presentation.components.plot_view import (
    build_graphical_figure,
    build_vertices_rows,
    hidden_vertices_count,
)
from utils.formatting import DECIMAL_MODE, FRACTION_MODE


def _result(sense, objective, rows):
    form = {
        "sense": sense,
        "n_variables": len(objective),
        "objective": list(objective),
        "constraints": [
            {
                **{f"x{i + 1}": c for i, c in enumerate(coefficients)},
                "rel": relation,
                "rhs": rhs,
            }
            for coefficients, relation, rhs in rows
        ],
    }
    model, errors = validate_model_form(form)
    assert not errors
    return model, GraphicalSolver().solve(model).graphical


def _wyndor():
    return _result("max", ["3", "5"], [
        (["1", "0"], "<=", "4"),
        (["0", "2"], "<=", "12"),
        (["3", "2"], "<=", "18"),
    ])


def _red_traces(fig):
    return [
        t for t in fig.data
        if getattr(t, "line", None) is not None and t.line.color == "red"
    ]


class TestGraphicalFigure(unittest.TestCase):
    def test_isoutilidad_roja_unica_y_discontinua(self):
        model, result = _wyndor()
        fig = build_graphical_figure(
            result, sense=model.sense, number_format=FRACTION_MODE
        )
        red = _red_traces(fig)
        self.assertEqual(len(red), 1)
        self.assertEqual(red[0].line.dash, "dash")
        self.assertEqual(red[0].line.width, 2)
        self.assertIn("Z = 36", red[0].name)

    def test_isocosto_en_minimizacion(self):
        model, result = _result("min", ["1", "2"], [(["1", "1"], ">=", "2")])
        fig = build_graphical_figure(result, sense=model.sense)
        self.assertIn("Isocosto", _red_traces(fig)[0].name)

    def test_anotacion_z_por_cada_fev(self):
        model, result = _wyndor()
        fig = build_graphical_figure(result, sense=model.sense)
        fev = [v for v in result.vertices if v.is_feasible]
        z_annotations = [a for a in fig.layout.annotations if "Z =" in a.text]
        self.assertEqual(len(z_annotations), len(fev))

    def test_etiqueta_por_cada_restriccion(self):
        model, result = _wyndor()
        fig = build_graphical_figure(result, sense=model.sense)
        texts = [a.text for a in fig.layout.annotations]
        for label in ("R1", "R2", "R3"):
            self.assertIn(f"<b>{label}</b>", texts)
            self.assertTrue(any(t.name.startswith(f"{label}:") for t in fig.data))

    def test_objetivo_constante_no_dibuja_isoutilidad(self):
        model, result = _result("max", ["0", "0"], [
            (["1", "0"], "<=", "1"),
            (["0", "1"], "<=", "1"),
        ])
        fig = build_graphical_figure(result, sense=model.sense)
        self.assertEqual(_red_traces(fig), [])

    def test_no_factible_sin_region_pero_con_rectas(self):
        model, result = _result("max", ["1", "1"], [
            (["1", "1"], "<=", "2"),
            (["1", "1"], ">=", "5"),
        ])
        fig = build_graphical_figure(result, sense=model.sense)
        self.assertFalse(any(t.name.startswith("Región factible") for t in fig.data))
        self.assertTrue(any(t.name.startswith("R1:") for t in fig.data))
        self.assertEqual(_red_traces(fig), [])
    
    def test_escala_1a1_y_cuadricula_cuadrada(self):
        model, result = _wyndor()
        fig = build_graphical_figure(result, sense=model.sense)
        self.assertEqual(fig.layout.yaxis.scaleanchor, "x")
        self.assertEqual(fig.layout.yaxis.scaleratio, 1)
        self.assertEqual(fig.layout.xaxis.constrain, "domain")
        self.assertEqual(fig.layout.yaxis.constrain, "domain")
        self.assertEqual(fig.layout.xaxis.dtick, fig.layout.yaxis.dtick)
        x0, x1 = fig.layout.xaxis.range
        y0, y1 = fig.layout.yaxis.range
        self.assertAlmostEqual(x1 - x0, y1 - y0, places=9)


class TestVerticesTable(unittest.TestCase):
    def test_tabla_lista_todos_los_vertices(self):
        _, result = _wyndor()
        rows = build_vertices_rows(result, FRACTION_MODE)
        self.assertEqual(len(rows), 8)
        self.assertEqual(sum(r["Tipo"].startswith("FEV") for r in rows), 5)
        self.assertEqual(sum(r["Tipo"] == "No factible" for r in rows), 3)
        self.assertTrue(all(r["Z"] == "—" for r in rows if r["Tipo"] == "No factible"))
        self.assertEqual(sum(r["Tipo"] == "FEV (óptimo)" for r in rows), 1)

    def test_formato_fraccion_y_decimal(self):
        _, result = _result("max", ["2", "4"], [
            (["1", "2"], "<=", "5"),
            (["1", "1"], "<=", "4"),
        ])
        fraccion = build_vertices_rows(result, FRACTION_MODE)
        decimal = build_vertices_rows(result, DECIMAL_MODE)
        self.assertIn("5/2", [r["x₂"] for r in fraccion])
        self.assertIn("2.5", [r["x₂"] for r in decimal])

    def test_vertices_fuera_de_la_ventana(self):
        _, result = _result("max", ["1", "1"], [
            (["1", "-1"], "<=", "1"),
            (["-1", "1"], "<=", "2"),
        ])
        # (0, -1) y (-2, 0) están en la tabla pero no en la gráfica.
        self.assertEqual(hidden_vertices_count(result), 2)
        self.assertEqual(len(build_vertices_rows(result, FRACTION_MODE)), 5)

    def test_wyndor_no_oculta_vertices(self):
        _, result = _wyndor()
        self.assertEqual(hidden_vertices_count(result), 0)


if __name__ == "__main__":
    unittest.main()