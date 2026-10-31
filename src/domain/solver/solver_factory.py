from enum import Enum
from .protocols import Solver
# from .big_m_simplex import BigMSimplexSolver (se implementará en Sprint 2)

class SolverMethod(Enum):
    GRAFICO = "grafico"
    GRAN_M = "gran_m"
    REVISADO = "revisado"
    
class SolverFactory:
    @staticmethod
    def create(method: SolverMethod) -> Solver:
        if method == SolverMethod.GRAFICO:
            # return GraphicalSolver()
            raise NotImplementedError("Gráfico en desarrollo")
        elif method == SolverMethod.GRAN_M:
            # return BigMSimplexSolver()
            raise NotImplementedError("Gran M en desarrollo")
        elif method == SolverMethod.REVISADO:
            # return RevisedSimplexSolver()
            raise NotImplementedError("Revisado en desarrollo")
        raise ValueError(f"Método desconocido: {method}")
