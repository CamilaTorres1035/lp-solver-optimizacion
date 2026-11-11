"""
Pestaña "Definir Modelo" — HU-01.

el formulario sigue este ciclo en CADA ejecución:

    1. RENDER   -> se pintan los widgets con los valores guardados en st.session_state.model_form (el "borrador" del modelo)
    2. LEER     -> se leen de vuelta los valores que el usuario escribió
    3. COMPARAR -> si algo cambió respecto al borrador, se actualiza el borrador y se invalida el modelo confirmado
    4. VALIDAR  -> se intenta construir el modelo con build_model(); el resultado decide si se muestra el botón de confirmar o la lista de errores

- st.session_state.model_form : borrador editable. Guarda TEXTO crudo (lo que el usuario escribe, p. ej. "3/2" o "1,5"), nunca números ya convertidos.
- st.session_state.model: modelo de dominio ya validado. Solo existe tras pulsar "Confirmar modelo". Cualquier edición posterior lo invalida (ver _invalidate_results) para que no se resuelva un modelo desactualizado
- `form_version`: Streamlit recuerda el valor de un widget por su `key`; el argumento `value=` solo se usa la PRIMERA vez que esa key aparece. Cuando cambia el número de variables hay que reconstruir todos los campos con valores nuevos, así que todas las keys incluyen `form_version`. Al incrementarlo, Streamlit trata los widgets como nuevos y respeta los valores del borrador

Estructura del archivo
- Helpers de formato          : convierten texto a vista previa legible
- Render principal            : render_model_tab(), la función pública
- Render de restricciones     : una "tarjeta" por restricción
- Helpers de estado           : inicializar, redimensionar, confirmar, invalidar
"""
import streamlit as st
from fractions import Fraction

from domain.model.enums import OptimizationSense
from domain.model.lp_model import build_model

# Helpers de formato
# ==================

# Tabla de traducción dígito a subíndice Unicode, para nombrar x₁, x₂, ...
SUBSCRIPTS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def _subscript(n: int) -> str:
    """Convierte un número a subíndice Unicode (x₁, x₂, x₃...)."""
    return str(n).translate(SUBSCRIPTS)


def _format_number_text(text: str) -> str:
    """
    Formatea un texto numérico según el formato global (Fracción/Decimal)
    Si el texto está vacío o es inválido, devuelve "?"

    Acepta coma o punto decimal ("1,5" y "1.5") y fracciones ("3/2")
    Solo afecta a la VISTA PREVIA: el valor guardado en el borrador sigue siendo el texto original del usuario
    """
    text_stripped = text.strip()
    if text_stripped == "":
        return "?"
    
    try:
        normalized = text_stripped.replace(",", ".")
        value = Fraction(normalized)
    except (ValueError, ZeroDivisionError):
        return "?"
    
    number_format = st.session_state.get("number_format", "Fracción")
    
    if number_format == "Decimal":
        # Decimal con precisión razonable, sin ceros innecesarios
        as_float = float(value)
        if as_float == int(as_float):
            return str(int(as_float))
        return f"{as_float:g}"
    
    # Fracción (por defecto)
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def _format_objective_equation(sense: str, objective: list[str]) -> str:
    """
    Formatea la función objetivo como ecuación escrita
    Ejemplo: "Max Z = 3·x₁ + 5·x₂"
    Respeta el formato global (Fracción/Decimal)
    """
    terms = []
    for i, coef in enumerate(objective):
        coef_formatted = _format_number_text(coef)
        var_name = f"x{_subscript(i + 1)}"
        terms.append(f"{coef_formatted}·{var_name}")
    
    equation = " + ".join(terms)
    sense_symbol = "Max" if sense == "max" else "Min"
    return f"{sense_symbol} Z = {equation}"


def _format_constraint(row: dict, n_variables: int) -> str:
    """
    Formatea una restricción como ecuación escrita
    Ejemplo: "1·x₁ + 0·x₂ ≤ 4"
    Respeta el formato global (Fracción/Decimal)

    `row` usa las claves "x1".."xN" (coeficientes), "rel" y "rhs"
    """
    terms = []
    for i in range(n_variables):
        coef = _format_number_text(row.get(f"x{i + 1}", ""))
        var_name = f"x{_subscript(i + 1)}"
        terms.append(f"{coef}·{var_name}")
    
    relation = row.get("rel", "<=")
    rhs = _format_number_text(row.get("rhs", ""))
    
    equation = " + ".join(terms)
    return f"{equation} {relation} {rhs}"


def _try_build_model(form: dict) -> tuple[bool, str, list[str]]:
    """
    Intenta construir el modelo y devuelve (éxito, mensaje, errores)

    Se llama en cada rerun como validación en tiempo real
    El modelo construido aquí se descarta: el que se guarda en session_state lo crea _confirm_model() cuando el usuario pulsa el botón de confirmar
    """
    constraints_data = []
    for row in form["constraints"]:
        constraints_data.append({
            "coefficients": [
                row.get(f"x{i + 1}", "")
                for i in range(form["n_variables"])
            ],
            "relation": row.get("rel", "<="),
            "rhs": row.get("rhs", ""),
        })
    
    try:
        model = build_model(
            sense=form["sense"],
            objective=form["objective"],
            constraints_data=constraints_data,
        )
        return True, "Modelo válido ✓", []
    except Exception as e:
        return False, "Modelo con errores ✗", [str(e)]

# Render principal
# ================

def render_model_tab() -> None:
    """
    Renderiza el formulario dinámico de definición del modelo

    Orden de la pantalla: 
    - tamaño
    - función objetivo
    - restricciones
    - validación/confirmación
    """
    _ensure_form_state()

    form = st.session_state.model_form
    version = st.session_state.form_version

    # Tamaño del modelo
    st.subheader("Tamaño del modelo")

    col_nvars, _ = st.columns([1, 3])
    with col_nvars:
        n_variables = st.number_input(
            "Número de variables de decisión",
            min_value=1,
            max_value=20,
            step=1,
            value=form["n_variables"],
            key=f"n_variables_{version}",
            help="Entre 1 y 20. Los valores ya ingresados se conservan al cambiar el tamaño.",
        )

        # Al cambiar el tamaño se ajusta el borrador, se sube la versión (para regenerar las keys de los widgets) y se re-ejecuta de inmediato para que el resto de la pantalla use el nuevo tamaño.
        if n_variables != form["n_variables"]:
            _resize_model_form(int(n_variables))
            _invalidate_results()
            st.session_state.form_version += 1
            st.rerun()

    # Función objetivo
    st.subheader("Función objetivo")

    with st.container(border=True):
        sense = st.radio(
            "Sentido de optimización",
            options=["max", "min"],
            format_func=lambda v: "Maximizar" if v == "max" else "Minimizar",
            index=0 if form["sense"] == "max" else 1,
            horizontal=True,
            key=f"sense_{version}",
        )

        if sense != form["sense"]:
            form["sense"] = sense
            _invalidate_results()

        st.caption("Coeficientes de cada variable en Z")
        # Una columna por variable: la fila de coeficientes queda alineada como en la ecuación escrita
        objective_columns = st.columns(form["n_variables"])
        new_objective = []

        for index, column in enumerate(objective_columns):
            with column:
                value = st.text_input(
                    f"x{_subscript(index + 1)}",
                    value=form["objective"][index],
                    key=f"obj_{version}_{index}",
                    placeholder="0",
                )
                new_objective.append(value)

        if new_objective != form["objective"]:
            form["objective"] = new_objective
            _invalidate_results()

        # VISTA PREVIA DE LA ECUACIÓN
        # Se calcula con el borrador ya actualizado, por eso refleja lo que el usuario acaba de escribir en la misma ejecución
        objective_equation = _format_objective_equation(form["sense"], form["objective"])
        st.info(f"**{objective_equation}**", icon=":material/functions:")

    # Restricciones (tarjetas)
    header_left, header_right = st.columns([3, 1], vertical_alignment="bottom")
    with header_left:
        st.subheader("Restricciones")
    with header_right:
        add_clicked = st.button(
            "Agregar restricción",
            icon=":material/add:",
            key=f"add_constraint_{version}",
            use_container_width=True,
        )

    # Se procesa el clic fuera del bloque de columnas y se re-ejecuta para que la nueva tarjeta aparezca de inmediato en esta misma pantalla.
    if add_clicked:
        new_row = {f"x{i + 1}": "0" for i in range(form["n_variables"])}
        new_row["rel"] = "<="
        new_row["rhs"] = "0"
        form["constraints"].append(new_row)
        _invalidate_results()
        st.rerun()

    constraints_changed = False

    if not form["constraints"]:
        st.info(
            "Aún no hay restricciones. Usa **Agregar restricción** para crear la primera.",
            icon=":material/info:",
        )
    
    # Por cada restricción: se pinta la tarjeta con los valores del borrador y luego se leen los widgets para detectar si el usuario cambió algo
    for idx, row in enumerate(form["constraints"]):
        _render_constraint_card(idx, row, form["n_variables"], version)
        
        new_row = _read_constraint_card(idx, form["n_variables"], version)
        if new_row != row:
            form["constraints"][idx] = new_row
            constraints_changed = True

    if constraints_changed:
        _invalidate_results()

    # Validación en tiempo real
    st.divider()

    is_valid, status_message, errors = _try_build_model(form)

    if is_valid:
        st.success(status_message, icon=":material/check_circle:")
        
        # Dos estados posibles cuando el modelo es válido:
        #   - ya confirmado: se muestra el resumen del modelo guardado
        #   - sin confirmar: se ofrece el botón para confirmarlo
        if st.session_state.get("model_defined"):
            model = st.session_state.model
            with st.container(border=True):
                metric_cols = st.columns(3)
                metric_cols[0].metric("Variables", model.n_variables)
                metric_cols[1].metric("Restricciones", model.n_constraints)
                metric_cols[2].metric(
                    "Sentido",
                    "Maximizar" if model.sense.value == "max" else "Minimizar",
                )
            st.success(
                "Modelo confirmado. Puedes resolverlo en la pestaña Resolver.",
                icon=":material/task_alt:",
            )
        elif st.button(
            "Confirmar modelo y habilitar resolución",
            type="primary",
            icon=":material/check:",
        ):
            _confirm_model(form)
            # Re-ejecuta para que el resumen (y la barra lateral) muestren el estado "confirmado" sin esperar a otra interacción
            st.rerun()
    else:
        with st.container(border=True):
            st.error(status_message, icon=":material/error:")
            for error in errors:
                st.markdown(f"- {error}")
            st.caption("Corrige los errores para habilitar la resolución.")

# Render de cada restricción como "tarjeta"
# ==========================================

def _render_constraint_card(idx: int, row: dict, n_variables: int, version: int) -> None:
    """
    Renderiza una restricción como una tarjeta con inputs claros

    Solo PINTA: los valores que escribe el usuario se recuperan después con
    _read_constraint_card(), usando las mismas keys. Las keys siguen el
    patrón `<prefijo>_<version>_<idx>[_<variable>]`:
        c_   -> coeficiente de una variable
        rel_ -> relación (<=, >=, =)
        rhs_ -> lado derecho
        del_ -> botón de eliminar
    """
    
    with st.container(border=True):
        # Header de la tarjeta: etiqueta + vista previa + botón eliminar
        header_cols = st.columns([0.6, 4, 0.5], vertical_alignment="center")
        
        with header_cols[0]:
            st.markdown(f"**R{idx + 1}**")
        
        with header_cols[1]:
            # Vista previa escrita en tamaño LEGIBLE (markdown normal, no caption)
            preview = _format_constraint(row, n_variables)
            st.markdown(f"`{preview}`")
        
        with header_cols[2]:
            if st.button("", icon=":material/delete:", key=f"del_{version}_{idx}", help="Eliminar esta restricción", use_container_width=True):
                st.session_state.model_form["constraints"].pop(idx)
                _invalidate_results()
                st.rerun()
        
        # Inputs de la restricción: n coeficientes + relación + lado derecho, todos en una sola fila (por eso n_variables + 2 columnas).
        input_cols = st.columns(n_variables + 2)
        
        for i in range(n_variables):
            with input_cols[i]:
                st.text_input(
                    f"x{_subscript(i + 1)}",
                    value=row.get(f"x{i + 1}", "0"),
                    key=f"c_{version}_{idx}_{i}",
                    placeholder="0",
                )
        
        with input_cols[-2]:
            st.selectbox(
                "Relación",
                options=["<=", ">=", "="],
                index=["<=", ">=", "="].index(row.get("rel", "<=")),
                key=f"rel_{version}_{idx}",
            )
        
        with input_cols[-1]:
            st.text_input(
                "Lado derecho",
                value=row.get("rhs", "0"),
                key=f"rhs_{version}_{idx}",
                placeholder="0",
            )


def _read_constraint_card(idx: int, n_variables: int, version: int) -> dict:
    """
    Lee los valores actuales de una tarjeta de restricción.

    Consulta st.session_state con las mismas keys que usó _render_constraint_card(). Devuelve un dict con el mismo formato que las filas del borrador, listo para compararse con la fila original
    """
    row = {}
    
    for i in range(n_variables):
        row[f"x{i + 1}"] = st.session_state.get(f"c_{version}_{idx}_{i}", "0")
    
    row["rel"] = st.session_state.get(f"rel_{version}_{idx}", "<=")
    row["rhs"] = st.session_state.get(f"rhs_{version}_{idx}", "0")
    
    return row

# Helpers de estado
# =================

def _ensure_form_state() -> None:
    """
    Crea el borrador inicial la primera vez (ejemplo clásico de 2 variables y 3 restricciones) y el contador `form_version`. En reruns posteriores no hace nada, para no pisar lo que el usuario ya editó
    """
    if "model_form" not in st.session_state:
        st.session_state.model_form = {
            "sense": "max",
            "n_variables": 2,
            "objective": ["3", "5"],
            "constraints": [
                {"x1": "1", "x2": "0", "rel": "<=", "rhs": "4"},
                {"x1": "0", "x2": "2", "rel": "<=", "rhs": "12"},
                {"x1": "3", "x2": "2", "rel": "<=", "rhs": "18"},
            ],
        }

    if "form_version" not in st.session_state:
        st.session_state.form_version = 0


def _resize_model_form(new_n: int) -> None:
    """
    Ajusta el borrador a `new_n` variables conservando lo ya escrito.

    - Si crece: las variables nuevas empiezan con coeficiente "0".
    - Si se reduce: se descartan los coeficientes de las últimas variables.
    Se aplica tanto a la función objetivo como a cada restricción.
    """
    form = st.session_state.model_form
    old_n = form["n_variables"]

    objective = form["objective"]
    if new_n > old_n:
        objective = objective + ["0"] * (new_n - old_n)
    else:
        objective = objective[:new_n]

    new_constraints = []
    for row in form["constraints"]:
        new_row = {
            f"x{index + 1}": row.get(f"x{index + 1}", "0")
            for index in range(new_n)
        }
        new_row["rel"] = row.get("rel", "<=")
        new_row["rhs"] = row.get("rhs", "0")
        new_constraints.append(new_row)

    form["n_variables"] = new_n
    form["objective"] = objective
    form["constraints"] = new_constraints


def _confirm_model(form: dict) -> None:
    """
    Construye el modelo de dominio a partir del borrador y lo guarda en session_state como modelo confirmado

    Al confirmar se descartan solución, sensibilidad y paso actual, porque pertenecían a un modelo anterior. `model_fingerprint` permite detectar más adelante si el modelo cambió respecto al que se resolvió
    """
    constraints_data = [
        {
            "coefficients": [
                row.get(f"x{index + 1}", "")
                for index in range(form["n_variables"])
            ],
            "relation": row.get("rel", "<="),
            "rhs": row.get("rhs", ""),
        }
        for row in form["constraints"]
    ]

    try:
        model = build_model(
            sense=form["sense"],
            objective=form["objective"],
            constraints_data=constraints_data,
        )

        st.session_state.model = model
        st.session_state.model_defined = True
        st.session_state.model_fingerprint = hash(model)

        st.session_state.solution = None
        st.session_state.sensitivity = None
        st.session_state.current_step = 0

        st.success("Modelo confirmado. Puedes resolverlo en la pestaña Resolver.")

    except Exception as error:
        st.session_state.model_defined = False
        st.session_state.model = None
        st.error(str(error))


def _invalidate_results() -> None:
    """
    Marca el modelo como "no confirmado" y borra todo lo derivado de él

    Se llama ante CUALQUIER edición del borrador (sentido, coeficientes, restricciones, tamaño), de modo que el usuario siempre tenga que reconfirmar y nunca se muestre una solución de un modelo viejo
    """
    st.session_state.model_defined = False
    st.session_state.model = None
    st.session_state.solution = None
    st.session_state.sensitivity = None
    st.session_state.current_step = 0