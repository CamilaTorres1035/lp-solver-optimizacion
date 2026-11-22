"""
Caso de uso: validar el formulario del modelo (HU-02)
La lógica sigue en domain/validation/parsing.py; esto solo fija la puerta de entrada presentation -> application (regla de capas)
`parse_fraction` se reexporta para la vista previa de model_tab
"""
from domain.model.lp_model import LPModel
from domain.validation.parsing import parse_fraction, validate_model_form

__all__ = ["validate_model", "parse_fraction"]


def validate_model(form: dict) -> tuple[LPModel | None, list[str]]:
    """Devuelve (modelo, errores). Modelo None si hay errores."""
    return validate_model_form(form)