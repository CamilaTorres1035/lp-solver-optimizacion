from typing import Protocol
from ..model.lp_model import LPModel
from .solution import Solution

class Solver(Protocol):
    def solve(self, model:LPModel) -> Solution:
        """Resuelve el modelo y devuelve una secuencia inmutable de pasos y la solución."""
        ...
