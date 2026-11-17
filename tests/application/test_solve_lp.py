"""Pruebas del caso de uso solve_lp. Sin Streamlit."""
import unittest
from fractions import Fraction as F

from application.use_cases.solve_lp import solve_lp
from domain.solver.solution import SolutionStatus
from domain.solver.solver_factory import SolverMethod
from domain.validation.parsing import validate_model_form


def _wyndor():
    model, errors = validate_model_form({
        "sense": "max",
        "n_variables": 2,
        "objective": ["3", "5"],
        "constraints": [
            {"x1": "1", "x2": "0", "rel": "<=", "rhs": "4"},
            {"x1": "0", "x2": "2", "rel": "<=", "rhs": "12"},
            {"x1": "3", "x2": "2", "rel": "<=", "rhs": "18"},
        ],
    })
    assert not errors
    return model


class TestSolveLp(unittest.TestCase):
    def test_grafico_devuelve_solution_con_payload(self):
        s = solve_lp(_wyndor(), SolverMethod.GRAFICO)
        self.assertEqual(s.status, SolutionStatus.OPTIMA)
        self.assertEqual(s.optimal_value, F(36))
        self.assertIsNotNone(s.graphical)

    def test_metodos_pendientes_avisan(self):
        for method in (SolverMethod.GRAN_M, SolverMethod.REVISADO):
            with self.assertRaises(NotImplementedError):
                solve_lp(_wyndor(), method)

    def test_grafico_con_tres_variables_propaga_valueerror(self):
        model, errors = validate_model_form({
            "sense": "max",
            "n_variables": 3,
            "objective": ["1", "1", "1"],
            "constraints": [
                {"x1": "1", "x2": "1", "x3": "1", "rel": "<=", "rhs": "1"},
            ],
        })
        assert not errors
        with self.assertRaises(ValueError):
            solve_lp(model, SolverMethod.GRAFICO)


if __name__ == "__main__":
    unittest.main()