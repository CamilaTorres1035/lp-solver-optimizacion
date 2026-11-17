"""
Formato compartido de números y expresiones (Fracción / Decimal).

El modo de formato lo decide quien llama (la UI lo lee de `st.session_state.number_format`).
"""
from fractions import Fraction
from typing import Sequence, Tuple

FRACTION_MODE = "Fracción"
DECIMAL_MODE = "Decimal"

_SUBSCRIPTS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def subscript(n: int) -> str:
    """1 -> '₁', 12 -> '₁₂'."""
    return str(n).translate(_SUBSCRIPTS)


def format_number(value: Fraction, mode: str = FRACTION_MODE) -> str:
    """
    Fracción: '3/2' o '4'.
    Decimal: hasta 4 decimales sin ceros sobrantes ('1.5', '4', '0.3333').
    """
    value = Fraction(value)
    if mode == DECIMAL_MODE:
        if value.denominator == 1:
            return str(value.numerator)
        text = f"{float(value):.4f}".rstrip("0").rstrip(".")
        return "0" if text in ("-0", "") else text
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def format_point(point: Tuple[Fraction, Fraction], mode: str = FRACTION_MODE) -> str:
    """(2, 6) o (0, 5/2)."""
    return f"({format_number(point[0], mode)}, {format_number(point[1], mode)})"


def format_linear_expression(
    coefficients: Sequence[Fraction], mode: str = FRACTION_MODE
) -> str:
    """'3·x₁ + 5·x₂'; los coeficientes negativos se escriben con ' − '."""
    pieces = []
    for index, coefficient in enumerate(coefficients, start=1):
        magnitude = format_number(abs(Fraction(coefficient)), mode)
        term = f"{magnitude}·x{subscript(index)}"
        if not pieces:
            pieces.append(f"−{term}" if coefficient < 0 else term)
        else:
            pieces.append(f"{'−' if coefficient < 0 else '+'} {term}")
    return " ".join(pieces)


_RELATION_SYMBOL = {"<=": "≤", ">=": "≥", "=": "="}


def format_constraint(
    coefficients: Sequence[Fraction],
    relation_value: str,
    rhs: Fraction,
    mode: str = FRACTION_MODE,
) -> str:
    """'3·x₁ + 2·x₂ ≤ 18'. `relation_value` es `Relation.<X>.value`."""
    symbol = _RELATION_SYMBOL.get(relation_value, relation_value)
    return f"{format_linear_expression(coefficients, mode)} {symbol} {format_number(rhs, mode)}"