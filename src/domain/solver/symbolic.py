"""
Valor simbólico a + bM para el método de la Gran M.

M se trata como un número infinitamente grande, por lo que el orden
de comparación es: primero el coeficiente de M (b), luego la parte
numérica (a). Esto garantiza que las penalizaciones artificiales
siempre dominen sobre los valores numéricos.

Ejemplos de formato:
    ValorM(3, 2)   → "2M + 3"
    ValorM(2, -11/10) → "-11/10 M + 2/5"  (si constant=2/5, m_coeff=-11/10)
    ValorM(0, -1)  → "-M"
    ValorM(5, 0)   → "5"
    ValorM(0, 0)   → "0"
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Union


# Tipos con los que ValorM puede operar directamente
ScalarLike = Union[int, Fraction, "ValorM"]


@dataclass(frozen=True)
class ValorM:
    """Representa el valor simbólico `constant + m_coeff * M`."""

    constant: Fraction
    m_coeff: Fraction

    #  Construcción flexible
    def __init__(self, constant: ScalarLike = 0, m_coeff: ScalarLike = 0) -> None:
        # object.__setattr__ porque la dataclass es frozen
        object.__setattr__(self, "constant", _to_fraction(constant))
        object.__setattr__(self, "m_coeff", _to_fraction(m_coeff))

    #  Predicados
    @property
    def is_pure_number(self) -> bool:
        """True si no tiene componente de M (se comporta como Fraction)."""
        return self.m_coeff == 0

    @property
    def is_zero(self) -> bool:
        return self.constant == 0 and self.m_coeff == 0

    def to_fraction(self) -> Fraction:
        """Convierte a Fraction. Solo válido si is_pure_number."""
        if not self.is_pure_number:
            raise ValueError(
                f"No se puede convertir {self} a Fraction: tiene componente M"
            )
        return self.constant

    #  Operaciones aritméticas
    def __neg__(self) -> ValorM:
        return ValorM(-self.constant, -self.m_coeff)

    def __pos__(self) -> ValorM:
        return self

    def __add__(self, other: ScalarLike) -> ValorM:
        other = _coerce(other)
        return ValorM(
            self.constant + other.constant,
            self.m_coeff + other.m_coeff,
        )

    def __radd__(self, other: ScalarLike) -> ValorM:
        return self.__add__(other)

    def __sub__(self, other: ScalarLike) -> ValorM:
        other = _coerce(other)
        return ValorM(
            self.constant - other.constant,
            self.m_coeff - other.m_coeff,
        )

    def __rsub__(self, other: ScalarLike) -> ValorM:
        return (-self).__add__(other)

    def __mul__(self, other: ScalarLike) -> ValorM:
        other = _coerce(other)
        if not other.is_pure_number and not self.is_pure_number:
            raise ValueError(
                f"No se puede multiplicar {self} * {other}: "
                "ambos tienen componente M (M² no está soportado)"
            )
        # (a + bM) * c = a*c + b*c*M
        if other.is_pure_number:
            c = other.constant
            return ValorM(self.constant * c, self.m_coeff * c)
        # self es número puro, other tiene M
        a = self.constant
        return ValorM(a * other.constant, a * other.m_coeff)

    def __rmul__(self, other: ScalarLike) -> ValorM:
        return self.__mul__(other)

    def __truediv__(self, other: ScalarLike) -> ValorM:
        other = _coerce(other)
        if not other.is_pure_number:
            raise ValueError(
                f"No se puede dividir {self} / {other}: "
                "el divisor no puede tener componente M"
            )
        if other.constant == 0:
            raise ZeroDivisionError("División por cero")
        c = other.constant
        return ValorM(self.constant / c, self.m_coeff / c)

    def __rtruediv__(self, other: ScalarLike) -> ValorM:
        # other / self: solo válido si self es número puro
        if not self.is_pure_number:
            raise ValueError(
                f"No se puede dividir {other} / {self}: "
                "el divisor tiene componente M"
            )
        if self.constant == 0:
            raise ZeroDivisionError("División por cero")
        other = _coerce(other)
        if not other.is_pure_number:
            raise ValueError(
                f"No se puede dividir {other} / {self}: "
                "el numerador tiene componente M"
            )
        return ValorM(other.constant / self.constant, Fraction(0))

    #  Comparaciones (M primero, luego parte numérica)
    def _cmp_key(self) -> tuple[Fraction, Fraction]:
        return (self.m_coeff, self.constant)

    def __lt__(self, other: ScalarLike) -> bool:
        return self._cmp_key() < _coerce(other)._cmp_key()

    def __le__(self, other: ScalarLike) -> bool:
        return self._cmp_key() <= _coerce(other)._cmp_key()

    def __gt__(self, other: ScalarLike) -> bool:
        return self._cmp_key() > _coerce(other)._cmp_key()

    def __ge__(self, other: ScalarLike) -> bool:
        return self._cmp_key() >= _coerce(other)._cmp_key()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, (int, Fraction)):
            other = _coerce(other)
        if not isinstance(other, ValorM):
            return NotImplemented
        return (self.constant, self.m_coeff) == (other.constant, other.m_coeff)

    def __ne__(self, other: object) -> bool:
        eq = self.__eq__(other)
        return eq if eq is NotImplemented else not eq

    def __hash__(self) -> int:
        return hash((self.constant, self.m_coeff))

    #  Formato (M siempre primero)
    def __str__(self) -> str:
        a, b = self.constant, self.m_coeff

        # Caso 1: cero total
        if a == 0 and b == 0:
            return "0"

        # Caso 2: solo parte numérica
        if b == 0:
            return _format_fraction(a)

        # Caso 3: solo parte de M
        if a == 0:
            return _format_m_term(b)

        # Caso 4: ambos componentes → "{parte_M} ± {parte_numérica}"
        m_part = _format_m_term(b)
        if a > 0:
            return f"{m_part} + {_format_fraction(a)}"
        # a < 0: mostrar como resta
        return f"{m_part} - {_format_fraction(-a)}"

    def __repr__(self) -> str:
        return f"ValorM(constant={self.constant!r}, m_coeff={self.m_coeff!r})"


# ====================================================================== #
#  Helpers privados
# ====================================================================== #

def _to_fraction(value: ScalarLike) -> Fraction:
    """Convierte int, Fraction o ValorM (si es número puro) a Fraction."""
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, ValorM):
        if not value.is_pure_number:
            raise ValueError(
                f"No se puede usar {value} como escalar: tiene componente M"
            )
        return value.constant
    raise TypeError(f"Tipo no soportado: {type(value).__name__}")


def _coerce(value: ScalarLike) -> ValorM:
    """Convierte int/Fraction a ValorM con m_coeff=0."""
    if isinstance(value, ValorM):
        return value
    return ValorM(_to_fraction(value), Fraction(0))


def _format_fraction(f: Fraction) -> str:
    """Formatea una fracción: '3', '-3/2', '2/5'."""
    if f.denominator == 1:
        return str(f.numerator)
    return f"{f.numerator}/{f.denominator}"


def _format_m_term(b: Fraction) -> str:
    """Formatea el término bM: 'M', '-M', '2M', '-11/10 M'."""
    if b == 1:
        return "M"
    if b == -1:
        return "-M"
    if b.denominator == 1:
        return f"{b.numerator}M"
    # Fracción no trivial: "-11/10 M"
    return f"{b.numerator}/{b.denominator} M"