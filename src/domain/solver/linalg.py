"""
Operaciones matriciales con aritmética exacta de fracciones.
No se usa NumPy para preservar la exactitud.
"""
from fractions import Fraction
from typing import Tuple

# Tipo Matrix: tupla de tuplas de Fraction (inmutable)
Matrix = Tuple[Tuple[Fraction, ...], ...]
Vector = Tuple[Fraction, ...]


def identity_matrix(n: int) -> Matrix:
    """Crea una matriz identidad n×n."""
    return tuple(
        tuple(Fraction(1) if i == j else Fraction(0) for j in range(n))
        for i in range(n)
    )


def matrix_multiply(a: Matrix, b: Matrix) -> Matrix:
    """
    Producto de matrices A × B.
    A debe ser m×n y B debe ser n×p.
    """
    m = len(a)
    n = len(a[0])
    p = len(b[0])
    
    if len(b) != n:
        raise ValueError(f"Dimensiones incompatibles: A es {m}×{n}, B es {len(b)}×{p}")
    
    return tuple(
        tuple(
            sum(a[i][k] * b[k][j] for k in range(n))
            for j in range(p)
        )
        for i in range(m)
    )  # type: ignore


def matrix_vector_multiply(a: Matrix, v: Vector) -> Vector:
    """
    Producto matriz A × vector v.
    A debe ser m×n y v debe tener longitud n.
    """
    n = len(a[0])
    
    if len(v) != n:
        raise ValueError(f"Dimensiones incompatibles: A tiene {n} columnas, vector tiene longitud {len(v)}")
    
    return tuple(
        sum(a[i][k] * v[k] for k in range(n))
        for i in range(len(a))
    )  # type: ignore


def pivot_matrix(matrix: Matrix, pivot_row: int, pivot_col: int) -> Matrix:
    """
    Operación de pivoteo elemental (Gauss-Jordan para una columna).
    Hace que el elemento pivote sea 1 y el resto de la columna sea 0.
    
    Optimización: calcula la fila pivote normalizada UNA sola vez.
    """
    m = len(matrix)
    n = len(matrix[0])
    pivot_element = matrix[pivot_row][pivot_col]
    
    if pivot_element == 0:
        raise ValueError("El elemento pivote no puede ser cero")
    
    # calcular la fila pivote normalizada una sola vez
    normalized_pivot_row = tuple(matrix[pivot_row][j] / pivot_element for j in range(n))
    
    result = []
    for i in range(m):
        if i == pivot_row:
            result.append(normalized_pivot_row)
        else:
            factor = matrix[i][pivot_col]
            new_row = tuple(
                matrix[i][j] - factor * normalized_pivot_row[j]
                for j in range(n)
            )
            result.append(new_row)
    
    return tuple(result)


def invert_matrix(matrix: Matrix) -> Matrix:
    """
    Invierte una matriz cuadrada usando Gauss-Jordan.
    Lanza ValueError si la matriz es singular.
    
    Útil para:
    - Pruebas de paridad (verificar B·B⁻¹ = I en HU-07)
    - Verificación cruzada entre Gran M y Revisado
    """
    n = len(matrix)
    if any(len(row) != n for row in matrix):
        raise ValueError("La matriz debe ser cuadrada")
    
    # Crear matriz aumentada [A | I]
    augmented: list[list[Fraction]] = [
        list(matrix[i]) + [Fraction(1) if i == j else Fraction(0) for j in range(n)]
        for i in range(n)
    ]
    
    # Eliminación Gauss-Jordan
    for col in range(n):
        # Buscar pivote (fila con valor distinto de cero)
        pivot_row = None
        for row in range(col, n):
            if augmented[row][col] != 0:
                pivot_row = row
                break
        
        if pivot_row is None:
            raise ValueError("La matriz es singular (no invertible)")
        
        # Intercambiar filas si es necesario
        if pivot_row != col:
            augmented[col], augmented[pivot_row] = augmented[pivot_row], augmented[col]
        
        # Normalizar fila pivote
        pivot_element = augmented[col][col]
        augmented[col] = [x / pivot_element for x in augmented[col]]
        
        # Eliminar el resto de la columna
        for row in range(n):
            if row != col:
                factor = augmented[row][col]
                augmented[row] = [
                    augmented[row][j] - factor * augmented[col][j]
                    for j in range(2 * n)
                ]
    
    # Extraer la matriz inversa (lado derecho)
    return tuple(
        tuple(Fraction(row[j]) for j in range(n, 2 * n))
        for row in augmented
    )


def transpose(matrix: Matrix) -> Matrix:
    """Transpone una matriz."""
    if not matrix:
        return tuple()
    m = len(matrix)
    n = len(matrix[0])
    return tuple(
        tuple(matrix[i][j] for i in range(m))
        for j in range(n)
    )


def get_column(matrix: Matrix, col: int) -> Vector:
    """Extrae una columna de la matriz como vector."""
    return tuple(matrix[i][col] for i in range(len(matrix)))


def get_row(matrix: Matrix, row: int) -> Vector:
    """Extrae una fila de la matriz como vector."""
    return matrix[row]