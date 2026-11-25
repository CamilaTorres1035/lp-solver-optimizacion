"""
Pruebas de integración de la pestaña Resolver con streamlit.testing (AppTest).

Cubren lo que no se puede probar con funciones puras:
- HU-08: botones y deslizador muestran siempre la misma iteración, y navegar NO vuelve a ejecutar el solver
- HU-15: Directa no muestra iteraciones; cambiar de modo no vuelve a resolver
- Casos borde: una sola iteración (sin deslizador) y no acotado

El solver se espía con mock.patch(wraps=...) para contar cuántas veces se ejecuta
"""
import os
import unittest
from unittest import mock

from streamlit.testing.v1 import AppTest

import presentation.tabs.solve_tab as solve_tab
from domain.model.lp_model import build_model
from domain.solver.solver_factory import SolverMethod
from utils.examples import get_example

_APP = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "src", "presentation", "app.py",
)


def _app_with_model(form, model):
    """App con el modelo ya confirmado (como si el usuario hubiera pulsado Confirmar)."""
    at = AppTest.from_file(_APP, default_timeout=30)
    at.session_state["model_form"] = form
    at.session_state["form_version"] = 0
    at.session_state["model"] = model
    at.session_state["model_defined"] = True
    return at


def _example_app(key):
    ex = get_example(key)
    return _app_with_model(ex.to_form(), ex.to_model())


def _solve_gran_m(at):
    at.run()
    at.radio(key="solve_method").set_value(SolverMethod.GRAN_M).run()
    next(b for b in at.button if b.label == "Resolver").click().run()
    return at


def _markdown(at):
    return [m.value for m in at.markdown]


def _title(at):
    return next(v for v in _markdown(at) if v.startswith("**Iteración"))


def _slider(at):
    return at.slider(key="nav_slider").value


class TestNavegacion(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(solve_tab, "solve_lp", wraps=solve_tab.solve_lp)
        self.spy = patcher.start()
        self.addCleanup(patcher.stop)
        self.at = _solve_gran_m(_example_app("wyndor"))

    def assertShowing(self, index, title):
        self.assertEqual(self.at.session_state["current_step"], index)
        self.assertEqual(_slider(self.at), index)
        self.assertEqual(_title(self.at), f"**{title}**")
        self.assertIn(f"Iteración {index} de 2", " ".join(_markdown(self.at)))

    def test_por_defecto_paso_a_paso_en_la_iteracion_0(self):
        self.assertEqual(len(self.at.exception), 0)
        self.assertEqual(self.at.radio(key="solve_mode").value, "Paso a paso")
        self.assertShowing(0, "Iteración 0: entra x2, sale S2")
        self.assertEqual(len(self.at.get("html")), 1)            # un solo tableau visible
        self.assertTrue(self.at.button(key="nav_prev").disabled)

    def test_botones_y_deslizador_sincronizados_sin_resolver_de_nuevo(self):
        self.at.button(key="nav_next").click().run()
        self.assertShowing(1, "Iteración 1: entra x1, sale S3")

        self.at.slider(key="nav_slider").set_value(2).run()
        self.assertShowing(2, "Iteración 2: tableau final")
        self.assertTrue(self.at.button(key="nav_next").disabled)

        self.at.button(key="nav_prev").click().run()
        self.assertShowing(1, "Iteración 1: entra x1, sale S3")

        self.at.button(key="nav_first").click().run()
        self.assertShowing(0, "Iteración 0: entra x2, sale S2")

        self.at.button(key="nav_last").click().run()
        self.assertShowing(2, "Iteración 2: tableau final")

        self.assertEqual(self.spy.call_count, 1)                 # solo el clic en Resolver

    def test_modo_directa_no_muestra_iteraciones_ni_resuelve(self):
        self.at.button(key="nav_next").click().run()
        self.at.radio(key="solve_mode").set_value("Directa").run()
        self.assertEqual(len(self.at.exception), 0)
        self.assertEqual(len(self.at.get("html")), 0)
        self.assertEqual(len(self.at.slider), 0)
        self.assertFalse(any(v.startswith("**Iteración") for v in _markdown(self.at)))
        self.assertEqual(len(self.at.dataframe), 1)              # holgura o exceso
        self.assertEqual(self.spy.call_count, 1)

        # Al volver, se conserva la iteración que se estaba viendo
        self.at.radio(key="solve_mode").set_value("Paso a paso").run()
        self.assertShowing(1, "Iteración 1: entra x1, sale S3")
        self.assertEqual(self.spy.call_count, 1)

    def test_el_modo_se_conserva_al_pasar_por_el_grafico(self):
        self.at.radio(key="solve_mode").set_value("Directa").run()
        self.at.radio(key="solve_method").set_value(SolverMethod.GRAFICO).run()
        self.assertEqual(len([r for r in self.at.radio if r.key == "solve_mode"]), 0)
        self.at.radio(key="solve_method").set_value(SolverMethod.GRAN_M).run()
        self.assertEqual(self.at.radio(key="solve_mode").value, "Directa")


class TestCasosBorde(unittest.TestCase):
    def test_una_sola_iteracion_no_dibuja_deslizador(self):
        model = build_model("max", ["-1"], [
            {"coefficients": ["1"], "relation": "<=", "rhs": "4"}])
        form = {"sense": "max", "n_variables": 1, "objective": ["-1"],
                "constraints": [{"x1": "1", "rel": "<=", "rhs": "4"}]}
        at = _solve_gran_m(_app_with_model(form, model))
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.slider), 0)
        self.assertTrue(any("Iteración 0 de 0" in c.value for c in at.caption))
        self.assertEqual(_title(at), "**Iteración 0: tableau final**")

    def test_no_acotado_muestra_la_columna_que_entra(self):
        at = _solve_gran_m(_example_app("rubrica_5"))
        at.button(key="nav_last").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertIn("no se pivotea", _title(at))
        self.assertIn('class="lp-col"', at.get("html")[0].proto.body)

    def test_grafico_sin_selector_de_modo_y_con_holguras(self):
        at = _example_app("wyndor")
        at.run()
        next(b for b in at.button if b.label == "Resolver").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len([r for r in at.radio if r.key == "solve_mode"]), 0)
        self.assertEqual(len(at.dataframe), 2)                   # vértices + holgura o exceso

    def test_minimizacion_con_m(self):
        at = _solve_gran_m(_example_app("min_dieta"))
        self.assertEqual(len(at.exception), 0)
        body = at.get("html")[0].proto.body
        self.assertIn("−Z", body)
        self.assertIn("-11/10 M + 2/5", body)


if __name__ == "__main__":
    unittest.main()
