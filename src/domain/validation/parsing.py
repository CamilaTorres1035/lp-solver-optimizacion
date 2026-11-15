from typing import Any, Mapping, Sequence, Tuple
from model.lp_model import OptimizationSense, LPModel, Constraint, Relation

from fractions import Fraction
import re

# Formato esperado de un entero
_INTEGER = r"[+-]?\d+"
# Formato esperado de un decimal
_DECIMAL = r"[+-]?\d+[.,]\d+"

# Patrón de número para comparar textos
_NUMBER_RE = re.compile(rf"(?:{_INTEGER}|{_DECIMAL})")

# Patrón de fracción
_FRACTION_RE = re.compile(rf"({_INTEGER})\s*/\s*({_INTEGER})")

# Límites de dimensión
MAX_VARIABLES = 20
MAX_CONSTRAINTS = 20

def _to_fraction(value: str) -> Fraction:
    """
        Parser, recibe el texto de una celda y devuelve un Fraction.
        Reconoce enteros, decimales con punto o coma y fracciones, y devuelve Fraction.
    """
    raw = str(value)
    text = raw.strip()

    if not text:
        raise ValueError("Celda vacía: se esperaba un número.")

    fraction_match = _FRACTION_RE.fullmatch(text)

    if fraction_match:
        numerator = int(fraction_match.group(1))
        denominator = int(fraction_match.group(2))
        if denominator == 0:
            raise ValueError(f"'{raw}' tiene denominador cero.")

        return Fraction(numerator= numerator,
                        denominator= denominator)

    if _NUMBER_RE.fullmatch(text):
        return Fraction(text.replace(",", "."))

    raise ValueError(f"'{raw}' no es un número válido.")

def _collect_numeric_errors(form: dict) -> list[str]:
    """
        Recolecta los errores numéricos obtenidos
        del formulario donde se entrega el modelo.
        Nota sobre las restricciones:
            Se espera que cuando una restricción
            no incluye una variable, se indique
            explícitamente que el coeficiente de esa
            variable es 0.
    """
    errors = []

    # Recorrer los coeficientes de la F.O y detectar errores
    for index, value in enumerate(form["objective"]):
        try:
            _to_fraction(value)
        except ValueError as e:
            errors.append(
                f"Error en función objetivo, coeficiente de x{index + 1}: {e}"
            )

    n_variables = form["n_variables"]

    # Recorrer cada restricción del modelo
    for row_index, row in enumerate(form["constraints"], 1):
        # Recorrer cada variable de la restricción
        for variable_index in range(n_variables):
            # Si una restricción no incluye una variable,
            # debe asignarse un cero como coeficiente de esa variable
            # para esa restricción, de lo contrario marca error por
            # celda vacía.
            value = row.get(f"x{variable_index + 1}", "")

            try:
                _to_fraction(value)
            except ValueError as e:
                errors.append(
                    f"Error en restricción {row_index}, "
                    f"coeficiente de x{variable_index + 1}: {e}"
                )

        # Intentar convertir a fracción el lado derecho
        try:
            _to_fraction(row.get("rhs", ""))
        except ValueError as e:
            errors.append(f"Error en restricción {row_index}, lado derecho: {e}")

    return errors

def _collect_size_errors(form: dict) -> list[str]:
    """
        Valida errores de dimensión en el modelo.
    """

    errors = []

    n_variables = form["n_variables"]
    objective = form["objective"]
    constraints = form["constraints"]

    if n_variables < 1:
        errors.append("El modelo debe tener al menos una variable.")
    elif n_variables > MAX_VARIABLES:
        errors.append(
            f"El modelo no puede exceder {MAX_VARIABLES} variables."
        )

    if len(objective) != n_variables:
        errors.append(
            f"La función objetivo tiene {len(objective)} coeficientes, "
            f"pero el modelo declara {n_variables} variables."
        )

    if len(constraints) == 0:
        errors.append("El modelo debe tener al menos una restricción.")
    elif len(constraints) > MAX_CONSTRAINTS:
        errors.append(
            f"El modelo no puede exceder {MAX_CONSTRAINTS} restricciones."
        )

    return errors

def _collect_form_shape_errors(form: Any) -> list[str]:
    """Comprueba que el formulario tenga la estructura esperada por el validador."""
    if not isinstance(form, dict):
        return ["El formulario debe ser un diccionario."]

    errors = []

    if "sense" not in form:
        errors.append("Falta el campo 'sense'.")
    elif not isinstance(form["sense"], str):
        errors.append("El campo 'sense' debe ser texto.")

    if "n_variables" not in form:
        errors.append("Falta el campo 'n_variables'.")
        n_variables = None
    else:
        n_variables = form["n_variables"]
        if not isinstance(n_variables, int) or isinstance(n_variables, bool):
            errors.append("El campo 'n_variables' debe ser un entero.")
            n_variables = None

    if "objective" not in form:
        errors.append("Falta el campo 'objective'.")
    elif not isinstance(form["objective"], list):
        errors.append("El campo 'objective' debe ser una lista.")
    else:
        for index, value in enumerate(form["objective"], start=1):
            if not isinstance(value, str):
                errors.append(
                    f"El coeficiente de x{index} en la función objetivo debe ser texto."
                )

    if "constraints" not in form:
        errors.append("Falta el campo 'constraints'.")
    elif not isinstance(form["constraints"], list):
        errors.append("El campo 'constraints' debe ser una lista.")
    else:
        for row_index, row in enumerate(form["constraints"], start=1):
            if not isinstance(row, dict):
                errors.append(
                    f"La restricción {row_index} debe ser un diccionario."
                )
                continue

            if n_variables is not None:
                for variable_index in range(1, n_variables + 1):
                    key = f"x{variable_index}"
                    if key not in row:
                        errors.append(
                            f"Falta el coeficiente de x{variable_index} "
                            f"en la restricción {row_index}."
                        )
                    elif not isinstance(row[key], str):
                        errors.append(
                            f"El coeficiente de x{variable_index} en la "
                            f"restricción {row_index} debe ser texto."
                        )

            if "rel" not in row:
                errors.append(f"Falta la relación en la restricción {row_index}.")
            elif not isinstance(row["rel"], str):
                errors.append(
                    f"La relación en la restricción {row_index} debe ser texto."
                )

            if "rhs" not in row:
                errors.append(
                    f"Falta el lado derecho en la restricción {row_index}."
                )
            elif not isinstance(row["rhs"], str):
                errors.append(
                    f"El lado derecho de la restricción {row_index} debe ser texto."
                )

    return errors

def _parse_sense(value: OptimizationSense | str) -> OptimizationSense:
    if isinstance(value, OptimizationSense):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("max", "maximize", "maximizar"):
            return OptimizationSense.MAXIMIZE
        if normalized in ("min", "minimize", "minimizar"):
            return OptimizationSense.MINIMIZE

    raise ValueError(f"Sentido de optimización no válido: {value}")


def _parse_relation(value: Relation | str) -> Relation:
    if isinstance(value, Relation):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()

        if normalized in ("<=", "≤", "le"):
            return Relation.LESS_EQUAL
        if normalized in (">=", "≥", "ge"):
            return Relation.GREAT_EQUAL
        if normalized in ("=", "==", "eq"):
            return Relation.EQUAL

    raise ValueError(f"Relación no válida: {value}")

def _collect_option_errors(form: dict) -> list[str]:
    """
        Recolecta errores de parseo sobre el sentido (max o min) y 
        la relación (=, <=, >=) de las restricciones.
    """
    errors = []

    try:
        _parse_sense(form["sense"])
    except ValueError as error:
        errors.append(str(error))

    for row_index, row in enumerate(form["constraints"], start=1):
        try:
            _parse_relation(row["rel"])
        except ValueError as error:
            errors.append(f"Restricción {row_index}: {error}")

    return errors

def validate_model_form(form: Any) -> tuple[LPModel | None, list[str]]:
    """Valida el formulario y construye el modelo solo si no hay errores."""

    shape_errors = _collect_form_shape_errors(form) # Errores de forma del diccionario DTO
    if shape_errors:
        return None, shape_errors

    # Errores de tamaño
    errors = _collect_size_errors(form)
    # Errores numéricos
    errors.extend(_collect_numeric_errors(form))
    # Errres en desigualdades o max, min
    errors.extend(_collect_option_errors(form))

    if errors:
        return None, errors

    constraints_data = [
        {
            "coefficients": [row[f"x{variable_index + 1}"] for variable_index in range(form["n_variables"])],
            "relation": row["rel"],
            "rhs": row["rhs"],
        }

        for row in form["constraints"]
    ]

    try:
        model = _build_model(
            sense=form["sense"],
            objective=form["objective"],
            constraints_data= constraints_data,
        )
    except (ValueError, TypeError, KeyError) as e:
        return None, [str(e)]

    return model, []

def _build_model(
    sense: OptimizationSense | str,
    objective: Sequence[Any],
    constraints_data: Sequence[Mapping[str, Any]],
) -> LPModel:
    """Construye un LPModel a partir de sus datos.

    La validación completa del formulario se realiza en
    _validate_model_form. Aquí se convierten los valores y se crea
    el modelo inmutable.
    """
    parsed_sense = _parse_sense(sense)
    parsed_objective = tuple(_to_fraction(value) for value in objective)
    n_variables = len(parsed_objective)

    constraints = tuple(
        Constraint(
            coefficients=tuple(
                _to_fraction(value)
                for value in row["coefficients"]
            ),
            relation=_parse_relation(row["relation"]),
            rhs=_to_fraction(row["rhs"]),
            original_index=index + 1,
        )
        for index, row in enumerate(constraints_data)
    )

    return LPModel(
        sense=parsed_sense,
        objective=parsed_objective,
        constraints=constraints,
        n_variables=n_variables,
    )















