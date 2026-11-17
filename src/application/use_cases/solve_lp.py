"""
Caso de uso: resolver un modelo con el método elegido (HU-04: gráfico).

Depende del Protocol `Solver` a través de la fábrica (DIP): no conoce solvers concretos

Errores que deja pasar a la capa de presentación:
- ValueError: el método no aplica al modelo (gráfico con n ≠ 2).
- NotImplementedError: el método aún no está implementado (Gran M, Revisado).
"""
from domain.model.lp_model import LPModel
from domain.solver.solution import Solution
from domain.solver.solver_factory import SolverFactory, SolverMethod


def solve_lp(model: LPModel, method: SolverMethod) -> Solution:
    solver = SolverFactory.create(method)
    return solver.solve(model)