"""Pruebas del caso de uso invalidate_results (HU-05). Sin Streamlit: dict plano."""
import unittest
from types import SimpleNamespace

from application.use_cases.invalidate_results import (
    discard_stale_results,
    invalidate_results,
)


def _state(model, fingerprint):
    return {
        "model_defined": True,
        "model": model,
        "solutions": {"gran_m": SimpleNamespace(model_fingerprint=fingerprint)},
        "sensitivity": None,
        "current_step": 3,
        "results_invalidated": False,
    }


class TestInvalidateResults(unittest.TestCase):
    def test_descarta_modelo_y_derivados(self):
        model = ("wyndor", 1)
        state = _state(model, hash(model))
        invalidate_results(state)
        self.assertFalse(state["model_defined"])
        self.assertIsNone(state["model"])
        self.assertEqual(state["solutions"], {})
        self.assertIsNone(state["sensitivity"])
        self.assertEqual(state["current_step"], 0)

    def test_activa_aviso_solo_si_habia_resultados(self):
        model = ("wyndor", 1)
        state = _state(model, hash(model))
        invalidate_results(state)
        self.assertTrue(state["results_invalidated"])

    def test_sin_resultados_previos_no_hay_aviso(self):
        state = {"model_defined": True, "model": ("m",), "solutions": {},
                 "sensitivity": None, "current_step": 0}
        invalidate_results(state)
        self.assertFalse(state.get("results_invalidated", False))

    def test_sensitivity_sola_tambien_activa_aviso(self):
        state = {"solutions": {}, "sensitivity": object(), "current_step": 0}
        invalidate_results(state)
        self.assertTrue(state["results_invalidated"])

    def test_funciona_con_state_vacio(self):
        state = {}
        invalidate_results(state)
        self.assertEqual(state["solutions"], {})
        self.assertEqual(state["current_step"], 0)


class TestDiscardStaleResults(unittest.TestCase):
    def test_huellas_coinciden_no_toca_nada(self):
        model = ("wyndor", 1)
        state = _state(model, hash(model))
        discard_stale_results(state)
        self.assertTrue(state["model_defined"])
        self.assertEqual(len(state["solutions"]), 1)
        self.assertEqual(state["current_step"], 3)
        self.assertFalse(state["results_invalidated"])

    def test_huella_distinta_descarta_pero_conserva_modelo(self):
        model = ("wyndor", 2)
        state = _state(model, hash(model) + 1)  # huella vieja, garantizado distinta
        discard_stale_results(state)
        self.assertTrue(state["model_defined"])
        self.assertEqual(state["model"], model)
        self.assertEqual(state["solutions"], {})
        self.assertEqual(state["current_step"], 0)
        self.assertTrue(state["results_invalidated"])

    def test_sin_modelo_o_sin_soluciones_es_no_op(self):
        cases = [{}, {"model": ("m",), "solutions": {}},
                 {"model": None,
                  "solutions": {"m": SimpleNamespace(model_fingerprint=1)}}]
        for state in cases:
            with self.subTest(state=state):
                before = dict(state)
                discard_stale_results(state)
                self.assertEqual(state, before)


if __name__ == "__main__":
    unittest.main()