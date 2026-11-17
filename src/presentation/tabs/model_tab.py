"""
Pestaña "Definir Modelo" — HU-01.

el formulario sigue este ciclo en CADA ejecución:

    1. LEER     -> se sincroniza el borrador con los valores de los widgets (st.session_state)
    2. COMPARAR -> si algo cambió, se actualiza el borrador y se invalida el modelo confirmado
    3. PINTAR   -> se dibujan widgets y vistas previas con el borrador ya actualizado
    4. VALIDAR  -> validate_model_form() decide si se muestra el botón de confirmar o la lista de errores

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

from domain.validation.parsing import validate_model_form
from utils.examples import get_example, list_public_examples

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

# Nueva función try_build_model compatible con HU-02
def _try_build_model(form: dict) -> tuple[bool, str, list[str]]:
    """Valida el borrador y devuelve el resultado en el formato de la interfaz."""
    model, errors = validate_model_form(form)

    if errors:
        return False, "Modelo con errores ✗", errors

    if model is None:
        return False, "No se pudo construir el modelo ✗", [
            "La validación no devolvió un modelo ni errores."
        ]

    return True, "Modelo válido ✓", []

# Render principal
# ================

def render_model_tab() -> None:
    """
    Renderiza el formulario dinámico de definición del modelo

    Orden de la pantalla:
    - carga de ejemplos 
    - tamaño
    - función objetivo
    - restricciones
    - validación/confirmación
    """
    _ensure_form_state()

    form = st.session_state.model_form
    version = st.session_state.form_version
    
    st.subheader("Cargar ejemplo")
    
    public_examples = list_public_examples()
    example_keys = [""] + [ex.key for ex in public_examples]
    
    selected_key = st.selectbox(
            "Selecciona un problema clásico para cargar",
            options=example_keys,
            format_func=lambda key: (
                "- Selecciona un ejemplo -" if key == ""
                else get_example(key).name
            ),
            key=f"example_selector_{version}",
        )
    
    if selected_key:
        example = get_example(selected_key)
        st.info(f"**{example.name}**: {example.description}", icon=":material/info:")
    
    col_load, _ = st.columns([1, 3])
    with col_load:
        if st.button("Cargar ejemplo", disabled=not selected_key, icon=":material/content_paste_go:"):
            _load_example(selected_key)
            st.session_state.form_version += 1 # Fuerza regeneración de keys de widgets
            _invalidate_results() # Invalida cualquier modelo confirmado previo
            st.rerun()
    
    st.divider()

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
    
    # PASO 1 -> LEER Y COMPARAR: sincroniza el borrador con los widgets ANTES de pintar
    for idx, row in enumerate(form["constraints"]):
        new_row = _read_constraint_card(idx, form["n_variables"], version, row)
        if new_row != row:
            form["constraints"][idx] = new_row
            constraints_changed = True

    if constraints_changed:
        _invalidate_results()
    
    # PASO 2 -> PINTAR: las tarjetas se renderizan con el borrador ya sincronizado.
    for idx, row in enumerate(form["constraints"]):
        _render_constraint_card(idx, row, form["n_variables"], version)

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

    Solo PINTA: los valores ya se leyeron y sincronizaron en el PASO 1 de render_model_tab() con _read_constraint_card(), usando estas mismas keys.
    Las keys siguen el patrón `<prefijo>_<version>_<idx>[_<variable>]`:
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
                st.session_state.form_version += 1
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


def _read_constraint_card(idx: int, n_variables: int, version: int, fallback:dict) -> dict:
    """
    Lee los valores actuales de una tarjeta de restricción.

    Consulta st.session_state con las mismas keys que usa _render_constraint_card(). 
    Si una key todavía no existe (primera pintura de la tarjeta, o tras un cambio de form_version), usa como respaldo el valor del borrador (`fallback`), NO un "0" fijo: así leer antes de pintar no pisa los datos recién cargados por un ejemplo, un redimensionado o una eliminación.
    """
    row = {}
    
    for i in range(n_variables):
        key = f"x{i + 1}"
        row[key] = st.session_state.get(f"c_{version}_{idx}_{i}", fallback.get(key, "0"))
    
    row["rel"] = st.session_state.get(f"rel_{version}_{idx}", fallback.get("rel", "<="))
    row["rhs"] = st.session_state.get(f"rhs_{version}_{idx}", fallback.get("rhs", "0"))
    
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

# Nueva función confirm model compatible con HU-02
def _confirm_model(form: dict) -> None:
    """Valida el borrador y guarda el modelo si es válido."""
    model, errors = validate_model_form(form)

    if errors or model is None:
        st.session_state.model_defined = False
        st.session_state.model = None

        if errors:
            for error in errors:
                st.error(error)
        else:
            st.error("La validación no devolvió un modelo.")

        return

    st.session_state.model = model
    st.session_state.model_defined = True
    st.session_state.model_fingerprint = hash(model)

    st.session_state.solution = None
    st.session_state.sensitivity = None
    st.session_state.current_step = 0

    st.success("Modelo confirmado. Puedes resolverlo en la pestaña Resolver.")

def _load_example(key: str) -> None:
    """
    Carga un ejemplo precargado en el borrador del formulario
    
    Sobrescribe el borrador actual y fuerza una nueva versión para regenerar las keys de los widgets, asegurando que Streamlit renderice los nuevos campos correctamente
    """
    example = get_example(key)
    n_variables = len(example.objective)
    
    constraints = []
    for constraint in example.constraints:
        row = {
            f"x{index + 1}": coefficient
            for index, coefficient in enumerate(constraint.coefficients)
        }
        row['rel'] = constraint.relation
        row['rhs'] = constraint.rhs
        constraints.append(row)
    
    st.session_state.model_form = {
        "sense": example.sense,
        "n_variables": n_variables,
        "objective": list(example.objective),
        "constraints": constraints
    }

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