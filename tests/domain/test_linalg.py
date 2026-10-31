"""
Pruebas unitarias para el módulo de álgebra lineal con fracciones exactas.
Ejecutar: python -m unittest tests/domain/test_linalg.py -v
"""
import unittest
from fractions import Fraction

from src.domain.solver.linalg import (
    Matrix,
    Vector,
    identity_matrix,
    matrix_multiply,
    matrix_vector_multiply,
    pivot_matrix,
    invert_matrix,
    transpose,
    get_column,
    get_row,
)


# ============================================================================
# Helpers para construir matrices de forma legible en las pruebas
# ============================================================================

def F(n, d=None) -> Fraction:
    """
    Atajo para crear fracciones rápidamente en las pruebas.
    
    Uso:
        F(3)      → Fraction(3, 1)
        F(1, 2)   → Fraction(1, 2)
        F("0.5")  → Fraction(1, 2)
    """
    if d is None:
        return Fraction(n)
    return Fraction(n, d)


def mat(*rows) -> Matrix:
    """Construye una Matrix a partir de filas de números/fracciones."""
    return tuple(tuple(F(x) for x in row) for row in rows)


def vec(*values) -> Vector:
    """Construye un Vector a partir de valores."""
    return tuple(F(x) for x in values)


# ============================================================================
# Pruebas de identity_matrix
# ============================================================================

class TestIdentityMatrix(unittest.TestCase):
    def test_identity_1x1(self):
        self.assertEqual(identity_matrix(1), ((F(1),),))

    def test_identity_3x3(self):
        expected = mat([1, 0, 0], [0, 1, 0], [0, 0, 1])
        self.assertEqual(identity_matrix(3), expected)

    def test_identity_diagonal_is_one(self):
        I = identity_matrix(5)
        for i in range(5):
            self.assertEqual(I[i][i], F(1))

    def test_identity_off_diagonal_is_zero(self):
        I = identity_matrix(4)
        for i in range(4):
            for j in range(4):
                if i != j:
                    self.assertEqual(I[i][j], F(0))


# ============================================================================
# Pruebas de matrix_multiply
# ============================================================================

class TestMatrixMultiply(unittest.TestCase):
    def test_identity_times_matrix_is_matrix(self):
        A = mat([1, 2], [3, 4])
        I = identity_matrix(2)
        self.assertEqual(matrix_multiply(I, A), A)
        self.assertEqual(matrix_multiply(A, I), A)

    def test_2x3_times_3x2(self):
        A = mat([1, 2, 3], [4, 5, 6])
        B = mat([7, 8], [9, 10], [11, 12])
        result = matrix_multiply(A, B)
        # Fila 1: 1*7+2*9+3*11=58, 1*8+2*10+3*12=64
        # Fila 2: 4*7+5*9+6*11=139, 4*8+5*10+6*12=154
        expected = mat([58, 64], [139, 154])
        self.assertEqual(result, expected)

    def test_with_fractions(self):
        A = mat([F(1, 2), F(1, 3)], [F(1, 4), F(1, 5)])
        B = mat([F(6), F(0)], [F(0), F(15)])
        result = matrix_multiply(A, B)
        expected = mat([F(3), F(5)], [F(3, 2), F(3)])
        self.assertEqual(result, expected)

    def test_dimension_mismatch_raises(self):
        A = mat([1, 2], [3, 4])
        B = mat([1, 2, 3])
        with self.assertRaises(ValueError):
            matrix_multiply(A, B)

    def test_exactness_no_rounding(self):
        """Verifica que 1/3 * 3 = 1 exacto, no 0.9999..."""
        A = mat([F(1, 3)])
        B = mat([F(3)])
        result = matrix_multiply(A, B)
        self.assertEqual(result, ((F(1),),))


# ============================================================================
# Pruebas de matrix_vector_multiply
# ============================================================================

class TestMatrixVectorMultiply(unittest.TestCase):
    def test_identity_times_vector(self):
        I = identity_matrix(3)
        v = vec(1, 2, 3)
        self.assertEqual(matrix_vector_multiply(I, v), v)

    def test_2x3_times_vector_3(self):
        A = mat([1, 2, 3], [4, 5, 6])
        v = vec(1, 1, 1)
        result = matrix_vector_multiply(A, v)
        self.assertEqual(result, vec(6, 15))

    def test_with_fractions(self):
        A = mat([F(1, 2), F(1, 4)], [F(1, 3), F(1, 6)])
        v = vec(2, 4)
        # Fila 1: 1/2*2 + 1/4*4 = 1 + 1 = 2
        # Fila 2: 1/3*2 + 1/6*4 = 2/3 + 2/3 = 4/3
        expected = vec(2, F(4, 3))
        self.assertEqual(matrix_vector_multiply(A, v), expected)

    def test_dimension_mismatch_raises(self):
        A = mat([1, 2], [3, 4])
        v = vec(1, 2, 3)
        with self.assertRaises(ValueError):
            matrix_vector_multiply(A, v)


# ============================================================================
# Pruebas de pivot_matrix (la operación más crítica del Símplex)
# ============================================================================

class TestPivotMatrix(unittest.TestCase):
    def test_pivot_makes_pivot_element_one(self):
        M = mat([2, 4], [6, 8])
        result = pivot_matrix(M, 0, 0)
        self.assertEqual(result[0][0], F(1))

    def test_pivot_makes_rest_of_column_zero(self):
        M = mat([2, 4], [6, 8])
        result = pivot_matrix(M, 0, 0)
        self.assertEqual(result[1][0], F(0))

    def test_pivot_preserves_other_columns(self):
        # Tableau típico del Símplex: pivote en (0, 0)
        M = mat([1, 2, 3, 10],
                [0, 1, 4, 20],
                [0, 0, 1, 30])
        result = pivot_matrix(M, 1, 1)
        # Fila 1 queda [0, 1, 4, 20]
        # Fila 0: [1, 2-2*1, 3-2*4, 10-2*20] = [1, 0, -5, -30]
        # Fila 2: [0, 0-0*1, 1-0*4, 30-0*20] = [0, 0, 1, 30]
        expected = mat([1, 0, -5, -30],
                       [0, 1, 4, 20],
                       [0, 0, 1, 30])
        self.assertEqual(result, expected)

    def test_pivot_with_fractions_exact(self):
        """Caso real del Símplex: pivote 1/6 debe dar 1, y el resto 0 exacto."""
        M = mat([F(1, 6), F(0)],
                [F(1, 3), F(1)])
        result = pivot_matrix(M, 0, 0)
        # Fila 0: [1, 0]
        # Fila 1: [1/3 - 1/3*1, 1 - 1/3*0] = [0, 1]
        expected = mat([1, 0], [0, 1])
        self.assertEqual(result, expected)

    def test_pivot_zero_raises(self):
        M = mat([0, 1], [2, 3])
        with self.assertRaises(ValueError):
            pivot_matrix(M, 0, 0)

    def test_pivot_idempotent_on_already_pivoted(self):
        """Si ya está pivoteado, volver a pivotar no cambia nada."""
        M = mat([1, 2], [0, 3])
        result = pivot_matrix(M, 0, 0)
        self.assertEqual(result, M)


# ============================================================================
# Pruebas de invert_matrix
# ============================================================================

class TestInvertMatrix(unittest.TestCase):
    def test_inverse_of_identity_is_identity(self):
        I = identity_matrix(3)
        self.assertEqual(invert_matrix(I), I)

    def test_inverse_2x2(self):
        # A = [[1, 2], [3, 4]]
        # A⁻¹ = [[-2, 1], [3/2, -1/2]]
        A = mat([1, 2], [3, 4])
        A_inv = invert_matrix(A)
        expected = mat([-2, 1], [F(3, 2), F(-1, 2)])
        self.assertEqual(A_inv, expected)

    def test_B_times_B_inverse_is_identity(self):
        """Propiedad matemática fundamental para HU-07."""
        B = mat([2, 1, 0],
                [1, 3, 1],
                [0, 2, 4])
        B_inv = invert_matrix(B)
        product = matrix_multiply(B, B_inv)
        expected = identity_matrix(3)
        self.assertEqual(product, expected)

    def test_B_inverse_times_B_is_identity(self):
        B = mat([1, 2, 3],
                [0, 1, 4],
                [5, 6, 0])
        B_inv = invert_matrix(B)
        product = matrix_multiply(B_inv, B)
        self.assertEqual(product, identity_matrix(3))

    def test_singular_matrix_raises(self):
        # Matriz con filas linealmente dependientes
        M = mat([1, 2], [2, 4])
        with self.assertRaises(ValueError):
            invert_matrix(M)

    def test_non_square_raises(self):
        M = mat([1, 2, 3], [4, 5, 6])
        with self.assertRaises(ValueError):
            invert_matrix(M)

    def test_inverse_with_fractions(self):
        """Matriz con fracciones, como las que aparecen en el Símplex Revisado."""
        B = mat([F(1, 2), F(0)],
                [F(1, 4), F(1)])
        B_inv = invert_matrix(B)
        # B⁻¹ = [[2, 0], [-1/2, 1]]
        expected = mat([2, 0], [F(-1, 2), 1])
        self.assertEqual(B_inv, expected)
        # Verificar B·B⁻¹ = I
        self.assertEqual(matrix_multiply(B, B_inv), identity_matrix(2))


# ============================================================================
# Pruebas de transpose, get_column, get_row
# ============================================================================

class TestTranspose(unittest.TestCase):
    def test_transpose_2x3(self):
        M = mat([1, 2, 3], [4, 5, 6])
        expected = mat([1, 4], [2, 5], [3, 6])
        self.assertEqual(transpose(M), expected)

    def test_transpose_square_symmetric(self):
        M = mat([1, 2], [2, 3])
        self.assertEqual(transpose(M), M)

    def test_transpose_empty(self):
        self.assertEqual(transpose(tuple()), tuple())

    def test_double_transpose_is_identity(self):
        M = mat([1, 2, 3], [4, 5, 6])
        self.assertEqual(transpose(transpose(M)), M)


class TestGetters(unittest.TestCase):
    def test_get_column(self):
        M = mat([1, 2, 3], [4, 5, 6])
        self.assertEqual(get_column(M, 1), vec(2, 5))

    def test_get_row(self):
        M = mat([1, 2, 3], [4, 5, 6])
        self.assertEqual(get_row(M, 0), vec(1, 2, 3))


# ============================================================================
# Pruebas de inmutabilidad (principio arquitectónico clave)
# ============================================================================

class TestImmutability(unittest.TestCase):
    def test_pivot_does_not_modify_input(self):
        M = mat([2, 4], [6, 8])
        original = M
        pivot_matrix(M, 0, 0)
        self.assertIs(M, original)
        self.assertEqual(M, original)

    def test_invert_does_not_modify_input(self):
        M = mat([1, 2], [3, 4])
        original = M
        invert_matrix(M)
        self.assertEqual(M, original)

    def test_multiply_does_not_modify_inputs(self):
        A = mat([1, 2], [3, 4])
        B = mat([5, 6], [7, 8])
        original_A = A
        original_B = B
        matrix_multiply(A, B)
        self.assertEqual(A, original_A)
        self.assertEqual(B, original_B)


# ============================================================================
# Prueba de integración: pivoteo como en el Símplex del problema Wyndor
# ============================================================================

class TestSimplexIntegration(unittest.TestCase):
    def test_wyndor_first_pivot(self):
        """
        Problema Wyndor: Max 3x1 + 5x2
        s.t. x1 ≤ 4, 2x2 ≤ 12, 3x1+2x2 ≤ 18
        
        Forma estándar con holguras:
        x1 + S1 = 4
        2x2 + S2 = 12
        3x1 + 2x2 + S3 = 18
        
        Tableau inicial (solo la parte de restricciones, sin fila 0):
        [1, 0, 1, 0, 0 | 4]
        [0, 2, 0, 1, 0 | 12]
        [3, 2, 0, 0, 1 | 18]
        
        Pivote en columna x2 (col 1), fila S2 (row 1), pivote = 2
        """
        tableau = mat([1, 0, 1, 0, 0, 4],
                      [0, 2, 0, 1, 0, 12],
                      [3, 2, 0, 0, 1, 18])
        
        result = pivot_matrix(tableau, pivot_row=1, pivot_col=1)
        
        # Fila 1 (pivote): [0, 1, 0, 1/2, 0, 6]
        self.assertEqual(result[1], vec(0, 1, 0, F(1, 2), 0, 6))
        
        # Fila 0: no cambia en columna 1 (ya era 0)
        self.assertEqual(result[0], vec(1, 0, 1, 0, 0, 4))
        
        # Fila 2: [3, 2-2*1, 0-2*0, 0-2*1/2, 1-2*0, 18-2*6] = [3, 0, 0, -1, 1, 6]
        self.assertEqual(result[2], vec(3, 0, 0, -1, 1, 6))


# ============================================================================
# Ejecución
# ============================================================================

if __name__ == "__main__":
    unittest.main()