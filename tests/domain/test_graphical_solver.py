"""Pruebas de dominio del método gráfico (HU-04). Sin Streamlit."""
import unittest
from fractions import Fraction as F

from domain.solver.graphical_solver import GraphicalSolver
from domain.solver.solution import SolutionStatus
from domain.solver.solver_factory import SolverFactory, SolverMethod
from domain.validation.parsing import validate_model_form

WYNDOR_ROWS = [
    (["1", "0"], "<=", "4"),
    (["0", "2"], "<=", "12"),
    (["3", "2"], "<=", "18"),
]


def _model(sense, objective, rows):
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
    if errors or model is None:
        raise AssertionError(f"Modelo de prueba inválido: {errors}")
    return model


def _solve(sense, objective, rows):
    return GraphicalSolver().solve(_model(sense, objective, rows))


class TestGraphicalSolver(unittest.TestCase):
    def test_wyndor_vertices_y_optimo(self):
        s = _solve("max", ["3", "5"], WYNDOR_ROWS)
        self.assertEqual(s.status, SolutionStatus.OPTIMA)
        self.assertEqual(dict(s.values), {"x1": F(2), "x2": F(6)})
        self.assertEqual(s.optimal_value, F(36))
        self.assertEqual(s.slacks, (F(2), F(0), F(0)))

        fev = {v.point for v in s.graphical.vertices if v.is_feasible}
        no_fev = {v.point for v in s.graphical.vertices if not v.is_feasible}
        self.assertEqual(fev, {
            (F(0), F(0)), (F(4), F(0)), (F(4), F(3)),
            (F(2), F(6)), (F(0), F(6)),
        })
        self.assertEqual(no_fev, {(F(0), F(9)), (F(4), F(6)), (F(6), F(0))})

    def test_grafico_no_produce_iteraciones_ni_base(self):
        for rows, sense, obj in [
            (WYNDOR_ROWS, "max", ["3", "5"]),
            ([(["1", "1"], "<=", "2"), (["1", "1"], ">=", "5")], "max", ["1", "1"]),
            ([(["1", "-1"], "<=", "1"), (["-1", "1"], "<=", "2")], "max", ["1", "1"]),
        ]:
            s = _solve(sense, obj, rows)
            self.assertEqual(s.steps, ())
            self.assertIsNone(s.basis_info)
            self.assertIsNotNone(s.graphical)

    def test_rubrica_1_redundante_no_aporta_vertices(self):
        s = _solve("max", ["50", "80"], [
            (["2", "1"], "<=", "100"),
            (["1", "3"], "<=", "90"),
            (["0", "1"], "<=", "40"),
        ])
        self.assertEqual(dict(s.values), {"x1": F(42), "x2": F(16)})
        self.assertEqual(s.optimal_value, F(3380))
        self.assertEqual(s.slacks, (F(0), F(0), F(24)))
        self.assertTrue(all(
            v.point[1] != 40 for v in s.graphical.vertices if v.is_feasible
        ))

    def test_rubrica_2_rhs_negativo_evalua_original(self):
        s = _solve("min", ["4", "1"], [
            (["3", "1"], "=", "3"),
            (["4", "3"], ">=", "6"),
            (["-1", "-2"], ">=", "-4"),
        ])
        self.assertEqual(dict(s.values), {"x1": F(2, 5), "x2": F(9, 5)})
        self.assertEqual(s.optimal_value, F(17, 5))
        # Holguras sobre el modelo ORIGINAL: exceso de R2 = 1, R3 activa.
        self.assertEqual(s.slacks, (F(0), F(1), F(0)))
        # Decisión aprobada: en el gráfico se omite la nota de transformación.
        self.assertFalse(any("transform" in n.lower() for n in s.notes))

    def test_rubrica_4_no_factible(self):
        s = _solve("max", ["1", "1"], [
            (["1", "1"], "<=", "2"),
            (["1", "1"], ">=", "5"),
        ])
        self.assertEqual(s.status, SolutionStatus.NO_FACTIBLE)
        self.assertEqual(s.values, ())
        self.assertIsNone(s.optimal_value)
        self.assertEqual(s.graphical.region_polygon, ())
        self.assertEqual(s.graphical.optimal_vertices, ())
        # Las rectas sí se entregan para dibujarlas sin región.
        self.assertEqual(len(s.graphical.lines), 2)
        self.assertTrue(s.graphical.vertices)

    def test_rubrica_5_no_acotado(self):
        s = _solve("max", ["1", "1"], [
            (["1", "-1"], "<=", "1"),
            (["-1", "1"], "<=", "2"),
        ])
        self.assertEqual(s.status, SolutionStatus.NO_ACOTADA)
        self.assertIn((F(1), F(1)), s.graphical.improving_directions)
        self.assertTrue(s.graphical.region_is_unbounded)
        self.assertTrue(s.graphical.region_polygon)  # sombreada hasta la ventana
        self.assertEqual(s.values, ())

    def test_no_acotado_informa_direccion_con_cifras(self):
        """Requiere el Fix 3 (dirección en la nota)."""
        s = _solve("max", ["1", "1"], [
            (["1", "-1"], "<=", "1"),
            (["-1", "1"], "<=", "2"),
        ])
        self.assertTrue(any("(1, 1)" in n and "ΔZ = 2" in n for n in s.notes))

    def test_region_abierta_con_optimo_no_es_no_acotada(self):
        s = _solve("min", ["1", "2"], [(["1", "1"], ">=", "2")])
        self.assertEqual(s.status, SolutionStatus.OPTIMA)
        self.assertEqual(dict(s.values), {"x1": F(2), "x2": F(0)})
        self.assertTrue(s.graphical.region_is_unbounded)
        self.assertEqual(s.graphical.improving_directions, ())
        self.assertTrue(any("no mejora" in n for n in s.notes))

    def test_rubrica_6_optimos_multiples(self):
        s = _solve("max", ["2", "4"], [
            (["1", "2"], "<=", "5"),
            (["1", "1"], "<=", "4"),
        ])
        self.assertEqual(s.optimal_value, F(10))
        self.assertEqual(dict(s.values), {"x1": F(0), "x2": F(5, 2)})
        self.assertEqual(dict(s.alt_values), {"x1": F(3), "x2": F(1)})
        self.assertEqual(
            s.graphical.optimal_vertices, ((F(0), F(5, 2)), (F(3), F(1)))
        )
        self.assertEqual(
            s.graphical.optimal_segment, ((F(0), F(5, 2)), (F(3), F(1)))
        )
        self.assertTrue(any("λ" in n for n in s.notes))

    def test_igualdad_produce_segmento(self):
        s = _solve("max", ["3", "5"], [
            (["1", "0"], "<=", "4"),
            (["0", "2"], "<=", "12"),
            (["3", "2"], "=", "18"),
        ])
        self.assertEqual(s.status, SolutionStatus.OPTIMA)
        self.assertEqual(dict(s.values), {"x1": F(2), "x2": F(6)})
        self.assertEqual(len(s.graphical.region_polygon), 2)

    def test_objetivo_constante_sin_segmento(self):
        s = _solve("max", ["0", "0"], [
            (["1", "0"], "<=", "1"),
            (["0", "1"], "<=", "1"),
        ])
        self.assertEqual(s.status, SolutionStatus.OPTIMA)
        self.assertEqual(s.optimal_value, F(0))
        self.assertEqual(s.alt_values, ())
        self.assertIsNone(s.graphical.optimal_segment)
        self.assertIsNone(s.graphical.isoprofit_segment)
        self.assertEqual(len(s.graphical.optimal_vertices), 4)
        self.assertTrue(any("constante" in n for n in s.notes))

    def test_optimos_en_semirrecta(self):
        s = _solve("max", ["1", "0"], [(["1", "0"], "<=", "4")])
        self.assertEqual(s.status, SolutionStatus.OPTIMA)
        self.assertEqual(dict(s.values), {"x1": F(4), "x2": F(0)})
        self.assertTrue(s.graphical.region_is_unbounded)
        self.assertIsNone(s.graphical.optimal_segment)
        self.assertTrue(any("semirrecta" in n for n in s.notes))

    def test_isoutilidad_pasa_por_el_optimo(self):
        s = _solve("max", ["3", "5"], WYNDOR_ROWS)
        p1, p2 = s.graphical.isoprofit_segment
        for p in (p1, p2):
            self.assertEqual(3 * p[0] + 5 * p[1], s.optimal_value)
        self.assertEqual(s.graphical.isoprofit_z, F(36))

    def test_restriccion_degenerada_redundante(self):
        s = _solve("max", ["1", "1"], [
            (["0", "0"], "<=", "5"),
            (["1", "0"], "<=", "1"),
            (["0", "1"], "<=", "1"),
        ])
        self.assertEqual(s.status, SolutionStatus.OPTIMA)
        self.assertEqual(dict(s.values), {"x1": F(1), "x2": F(1)})
        self.assertEqual([l.label for l in s.graphical.lines], ["R2", "R3"])

    def test_restriccion_degenerada_contradictoria(self):
        s = _solve("max", ["1", "1"], [
            (["0", "0"], "<=", "-1"),
            (["1", "0"], "<=", "1"),
        ])
        self.assertEqual(s.status, SolutionStatus.NO_FACTIBLE)
        self.assertEqual(s.graphical.region_polygon, ())

    def test_ventana_con_margen_y_ejes_visibles(self):
        s = _solve("max", ["3", "5"], WYNDOR_ROWS)
        xmin, xmax, ymin, ymax = s.graphical.window
        self.assertLess(xmin, 0)
        self.assertLess(ymin, 0)
        for v in s.graphical.vertices:
            self.assertTrue(xmin <= v.point[0] <= xmax)
            self.assertTrue(ymin <= v.point[1] <= ymax)

    def test_n_distinto_de_2_contrato_defensivo(self):
        model = _model("max", ["1", "1", "1"], [(["1", "1", "1"], "<=", "1")])
        with self.assertRaises(ValueError):
            GraphicalSolver().solve(model)

    def test_factory_registra_grafico(self):
        self.assertIsInstance(
            SolverFactory.create(SolverMethod.GRAFICO), GraphicalSolver
        )

    def test_fingerprint_del_modelo(self):
        model = _model("max", ["3", "5"], WYNDOR_ROWS)
        self.assertEqual(GraphicalSolver().solve(model).model_fingerprint,
                         hash(model))


if __name__ == "__main__":
    unittest.main()