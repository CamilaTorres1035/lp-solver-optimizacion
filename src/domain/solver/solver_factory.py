from enum import Enum
from .protocols import Solver
from .graphical_solver import GraphicalSolver
from .big_m_simplex import BigMSimplexSolver 

class SolverMethod(Enum):
    GRAFICO = "grafico"
    GRAN_M = "gran_m"
    REVISADO = "revisado"
    
class SolverFactory:
    @staticmethod
    def create(method: SolverMethod) -> Solver:
        if method == SolverMethod.GRAFICO:
            return GraphicalSolver()
        elif method == SolverMethod.GRAN_M:
            return BigMSimplexSolver()
        elif method == SolverMethod.REVISADO:
            # return RevisedSimplexSolver()
            raise NotImplementedError("Revisado en desarrollo")
        raise ValueError(f"Método desconocido: {method}")
