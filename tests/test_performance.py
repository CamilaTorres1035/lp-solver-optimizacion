"""
Stress test de rendimiento para operaciones matriciales con fracciones.
Objetivo del Sprint 0: Validar que un problema de 10x10 con 100 iteraciones
se resuelva en menos de 2 segundos.
"""
import unittest
import time
import random
from fractions import Fraction

from src.domain.solver.linalg import (
    Matrix,
    pivot_matrix,
    matrix_multiply,
    identity_matrix,
)
from src.domain.solver.symbolic import ValorM


def F(n, d=None) -> Fraction:
    if d is None:
        return Fraction(n)
    return Fraction(n, d)


class TestPerformance(unittest.TestCase):
    def setUp(self):
        """Configuración inicial para las pruebas de rendimiento."""
        self.iterations = 100  # Límite de seguridad del documento
        self.rows = 11         # 1 FO + 10 restricciones
        self.cols = 22         # Z + 10 vars + 10 holguras/artificiales + RHS
        
        # Crear un tableau inicial con fracciones (simulando datos reales)
        # Aseguramos que la diagonal tenga valores no nulos para evitar ZeroDivisionError
        self.tableau: list[list[Fraction]] = []
        for i in range(self.rows):
            row = []
            for j in range(self.cols):
                # Valores aleatorios entre 1 y 10 para evitar ceros en el pivote
                val = F(random.randint(1, 10))
                if i == j and i < self.rows:
                    val = F(random.randint(1, 10)) # Diagonal segura
                row.append(val)
            self.tableau.append(row)
        
        # Convertir a Matrix inmutable para las pruebas
        self.matrix_tuple = tuple(tuple(row) for row in self.tableau)

    def test_10x10_pivot_performance(self):
        """
        Simula 100 iteraciones de pivoteo en un tableau de 11x22.
        Debe completarse en < 2.0 segundos.
        """
        start_time = time.perf_counter()
        
        current_matrix = self.matrix_tuple
        
        for i in range(self.iterations):
            # Elegimos un pivote seguro en la diagonal para evitar división por cero
            # En un solver real, esto lo decide el algoritmo, pero aquí probamos la operación pura
            pivot_row = (i % (self.rows - 1)) + 1  # Evitar fila 0 (FO) para este test
            pivot_col = (i % (self.cols - 1)) + 1
            
            # Ejecutar la operación de pivoteo
            current_matrix = pivot_matrix(current_matrix, pivot_row, pivot_col)
        
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        
        print(f"\n⏱️ 100 pivoteos en matriz {self.rows}x{self.cols}: {elapsed:.4f} segundos")
        
        self.assertLess(
            elapsed, 
            2.0, 
            f"El pivoteo de 100 iteraciones tomó {elapsed:.4f}s, superando el límite de 2.0s"
        )

    def test_10x10_revised_simplex_performance(self):
        """
        Simula 100 iteraciones de pivoteo sobre una matriz base de 10x10.
        Debe completarse en < 2.0 segundos.
        """
        n = 10
        
        # Crear una matriz inicial con valores no nulos (evita ZeroDivisionError)
        # Usamos lista solo para la construcción inicial, luego la convertimos a tupla una vez.
        initial_matrix = [
            [F(random.randint(1, 10)) for _ in range(n)]
            for _ in range(n)
        ]
        current_matrix = tuple(tuple(row) for row in initial_matrix)
        
        start_time = time.perf_counter()
        
        for i in range(self.iterations):
            # Elegir un pivote. Usamos la diagonal para garantizar que no sea 0 
            # (empezamos con randint(1,10), y el pivoteo en la diagonal de una matriz 
            # no singular tiende a mantener valores manejables).
            pivot_row = i % n
            pivot_col = i % n
            
            # Seguridad: si por alguna razón el elemento es 0, buscar otro en la misma columna
            if current_matrix[pivot_row][pivot_col] == 0:
                for r in range(n):
                    if current_matrix[r][pivot_col] != 0:
                        pivot_row = r
                        break
            
            # Operación pura sobre la estructura inmutable, sin conversiones intermedias
            current_matrix = pivot_matrix(current_matrix, pivot_row, pivot_col)
        
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        
        print(f"\n⏱️ 100 iteraciones de pivoteo en matriz 10x10: {elapsed:.4f} segundos")
        
        self.assertLess(
            elapsed, 
            2.0, 
            f"El álgebra del Revisado tomó {elapsed:.4f}s, superando el límite de 2.0s"
        )

    def test_valorm_arithmetic_overhead(self):
        """
        Verifica que las operaciones con ValorM no introduzcan una sobrecarga
        inaceptable en comparación con Fraction pura.
        """
        start_time = time.perf_counter()
        
        v1 = ValorM(F(2, 5), F(-11, 10))
        v2 = ValorM(F(1, 2), F(-9, 10))
        
        for _ in range(10000):  # 10,000 operaciones para medir overhead
            _ = v1 + v2
            _ = v1 * F(3)
            _ = v1 < v2
        
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        
        print(f"\n⏱️ 10,000 operaciones ValorM: {elapsed:.4f} segundos")
        
        self.assertLess(
            elapsed, 
            1.0, 
            f"Las operaciones ValorM son demasiado lentas: {elapsed:.4f}s"
        )


if __name__ == "__main__":
    unittest.main()