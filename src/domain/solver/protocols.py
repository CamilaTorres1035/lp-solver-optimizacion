from typing import Protocol
from ..model.lp_model import LPModel # Pendiente de implementar
from .solution import Solution

class Solver(Protocol):
    def solve(self, model:LPModel):
        """Resuelve el modelo y devuelve una secuencia inmutable de pasos y la solución."""
        ...
