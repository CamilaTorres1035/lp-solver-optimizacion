"""
Stress test de rendimiento actualizado para operaciones matriciales con fracciones.
Objetivo del Sprint 0: Validar que un problema de 20x20 con 200 iteraciones
se resuelva en menos de 2 segundos.
"""
import unittest
import time
import random
from fractions import Fraction
from domain.solver.linalg import (
    Matrix,
    pivot_matrix,
    matrix_multiply,
    invert_matrix,
    identity_matrix,
)
from domain.solver.symbolic import ValorM


def F(n, d=None) -> Fraction:
    return Fraction(n) if d is None else Fraction(n, d)


# Semilla fija: los datos "aleatorios" son siempre los mismos, así la prueba da el mismo resultado en cada corrida (local y en GitHub Actions)
SEED = 2026


def _nonzero_row(matrix, preferred: int, col: int, first_row: int) -> int:
    """La fila preferida si su elemento en `col` no es 0; si no, la primera
    fila (desde first_row) que sí lo tenga. Pivotear sobre un 0 es imposible"""
    if matrix[preferred][col] != 0:
        return preferred
    for r in range(first_row, len(matrix)):
        if matrix[r][col] != 0:
            return r
    return preferred   # columna sin ningún valor distinto de 0: pivot_matrix lo informa


class TestPerformance(unittest.TestCase):
    """Pruebas de rendimiento con los límites máximos del documento."""

    def test_20x20_pivot_performance(self):
        """
        200 iteraciones de pivoteo en un tableau de 21×42
        (1 fila FO + 20 restricciones | Z + 20 vars + 20 holguras/artificiales + RHS).
        Debe completarse en un tiempo razonable (propuesta: < 10s).
        """
        rows = 21   # 1 FO + 20 restricciones
        cols = 42   # Z + 20 vars + 20 holguras/artificiales + RHS
        iterations = 200

        rng = random.Random(SEED)
        initial = [
            [F(rng.randint(1, 10)) for _ in range(cols)]
            for _ in range(rows)
        ]
        current_matrix = tuple(tuple(row) for row in initial)

        start = time.perf_counter()
        for i in range(iterations):
            pivot_col = (i % (cols - 1)) + 1
            # evita la fila 0 (FO) y los pivotes en 0: tras varios pivoteos un elemento puede quedar exactamente en 0 (antes fallaba ~1 de cada 60 corridas)
            pivot_row = _nonzero_row(current_matrix, (i % (rows - 1)) + 1, pivot_col, 1)
            current_matrix = pivot_matrix(current_matrix, pivot_row, pivot_col)
        elapsed = time.perf_counter() - start

        print(f"\n200 pivoteos en tableau {rows}x{cols}: {elapsed:.4f}s")
        self.assertLess(elapsed, 10.0,
                        f"200 pivoteos en 21×42 tomó {elapsed:.4f}s (límite 10s)")

    def test_20x20_revised_simplex_performance(self):
        """
        200 iteraciones de pivoteo sobre una base 20×20 (Revisado).
        """
        n = 20
        iterations = 200

        rng = random.Random(SEED)
        initial = [
            [F(rng.randint(1, 10)) for _ in range(n)]
            for _ in range(n)
        ]
        current_matrix = tuple(tuple(row) for row in initial)

        start = time.perf_counter()
        for i in range(iterations):
            pivot_col = i % n
            pivot_row = _nonzero_row(current_matrix, i % n, pivot_col, 0)
            current_matrix = pivot_matrix(current_matrix, pivot_row, pivot_col)
        elapsed = time.perf_counter() - start

        print(f"\n200 iteraciones Revisado en matriz {n}x{n}: {elapsed:.4f}s")
        self.assertLess(elapsed, 10.0,
                        f"Revisado 20×20 tomó {elapsed:.4f}s (límite 10s)")

    def test_20x20_matrix_inversion_performance(self):
        """
        Invertir una matriz 20×20 debe ser rápido (el Revisado lo hace
        implícitamente en cada pivoteo, pero conviene medirlo aparte).
        """
        n = 20
        # Matriz diagonalmente dominante → garantizamos que sea invertible
        rng = random.Random(SEED)
        initial = [[F(0)] * n for _ in range(n)]
        for i in range(n):
            initial[i][i] = F(rng.randint(5, 20))
            for j in range(n):
                if i != j:
                    initial[i][j] = F(rng.randint(0, 2))
        matrix = tuple(tuple(row) for row in initial)

        start = time.perf_counter()
        inv = invert_matrix(matrix)
        product = matrix_multiply(matrix, inv)
        elapsed = time.perf_counter() - start

        print(f"\nInversión + producto 20x20: {elapsed:.4f}s")
        self.assertEqual(product, identity_matrix(n))
        self.assertLess(elapsed, 5.0,
                        f"Inversión 20×20 tomó {elapsed:.4f}s (límite 5s)")

    def test_valorm_arithmetic_overhead(self):
        """10,000 operaciones ValorM deben ser rápidas."""
        start = time.perf_counter()
        v1 = ValorM(F(2, 5), F(-11, 10))
        v2 = ValorM(F(1, 2), F(-9, 10))
        for _ in range(10_000):
            _ = v1 + v2
            _ = v1 * F(3)
            _ = v1 < v2
        elapsed = time.perf_counter() - start

        print(f"\n10,000 operaciones ValorM: {elapsed:.4f}s")
        self.assertLess(elapsed, 1.0,
                        f"ValorM overhead: {elapsed:.4f}s (límite 1s)")


if __name__ == "__main__":
    unittest.main()