"""
Pestaña "Resolver"

Flujo en cada ejecución:
    1. Si no hay modelo confirmado, se pide definirlo
    2. SELECTOR de método (siempre visible). El aviso de n ≠ 2 sale AL SELECCIONAR el método gráfico, sin esperar a pulsar Resolver
    3. SELECTOR de modo Directa / Paso a paso (HU-15), solo en los métodos símplex: el gráfico no tiene iteraciones
    4. Botón Resolver -> caso de uso `solve_lp` -> `st.session_state.solutions[method]`
    5. Resultados
       - Gráfico: figura de Plotly, tabla de vértices y solución final (HU-04)
       - Símplex en Paso a paso: forma estándar, navegación (HU-08), tableau resaltado y justificación (HU-09) y la solución final
       - Símplex en Directa: solo la solución final

Cambiar de modo o de iteración solo vuelve a dibujar: el solver corre únicamente al pulsar Resolver (HU-08 y HU-15).

Estado que usa (st.session_state)
- model_defined / model : los escribe model_tab
- solutions             : dict {SolverMethod: Solution} con lo resuelto por método
- current_step          : índice de iteración para HU-08 (se reinicia al resolver)
- solve_mode_choice     : modo elegido; sobrevive aunque el selector se oculte con el método gráfico
- results_invalidated   : aviso "debes resolver nuevamente" (HU-05)
- number_format         : "Fracción" | "Decimal"

Una solución solo se muestra si coincide con el método elegido y con el modelo actual (`model_fingerprint`), para no enseñar resultados desactualizados (HU-05)
"""

import streamlit as st

from application.step_navigation import build_tableau_view
from application.use_cases.solve_lp import solve_lp
from domain.model.enums import OptimizationSense
from domain.model.lp_model import LPModel
from domain.solver.solution import (
    Solution,
    SolutionStatus,
)
from domain.solver.solver_factory import SolverMethod
from domain.solver.step import Step
from presentation.components.navigation import render_navigator
from presentation.components.plot_view import (
    build_graphical_figure,
    build_vertices_rows,
    hidden_vertices_count,
)
from presentation.components.solution_view import build_slack_rows
from presentation.components.tableau_view import legend_html, render_tableau_html
from utils.formatting import FRACTION_MODE, format_number, subscript

_METHOD_LABELS = {
    SolverMethod.GRAFICO: "Gráfico",
    SolverMethod.GRAN_M: "Gran M",
}

MODE_DIRECT = "Directa"
MODE_STEP_BY_STEP = "Paso a paso"
_MODES = (MODE_DIRECT, MODE_STEP_BY_STEP)
_MODE_KEY = "solve_mode"                 # clave del widget
_MODE_CHOICE_KEY = "solve_mode_choice"   # valor que persiste (espejo, ver _render_mode_selector)


# Render principal
# ================

def render_solve_tab() -> None:
    if not st.session_state.get("model_defined") or st.session_state.get("model") is None:
        st.warning(
            "Primero define y confirma un modelo en la pestaña **Definir Modelo**.",
            icon=":material/lock:",
        )
        return

    model: LPModel = st.session_state.model
    number_format = st.session_state.get("number_format", FRACTION_MODE)

    method = st.radio(
        "Método de resolución",
        options=list(_METHOD_LABELS),
        format_func=lambda m: _METHOD_LABELS[m],
        horizontal=True,
        key="solve_method",
    )

    # Aviso de n ≠ 2: aparece al seleccionar el método, no al resolver.
    graphical_not_applicable = (
        method == SolverMethod.GRAFICO and model.n_variables != 2
    )
    if graphical_not_applicable:
        st.warning(
            f"El método gráfico solo aplica con exactamente 2 variables de decisión "
            f"(tu modelo tiene {model.n_variables}). Selecciona **Gran M** para resolverlo.",
            icon=":material/block:",
        )

    mode = _render_mode_selector(method)

    if st.button(
        "Resolver",
        type="primary",
        icon=":material/play_arrow:",
        disabled=graphical_not_applicable,
    ):
        _solve_and_store(model, method)

    solution = _current_solution(model, method)
    if solution is None:
        if not graphical_not_applicable:
            st.info("Pulsa **Resolver** para ejecutar el método elegido.", icon=":material/info:")
        return

    if solution.graphical is not None:
        _render_graphical_result(solution, model, number_format)
    else:
        _render_simplex_result(solution, model, number_format, mode)


def _render_mode_selector(method: SolverMethod):
    """
    Selector Directa / Paso a paso (HU-15). Devuelve el modo, o None en el gráfico.

    Streamlit borra el estado de un widget que deja de dibujarse; como el selector se oculta con el método gráfico, el valor elegido se guarda aparte (`solve_mode_choice`) y se copia al widget antes de crearlo. Por defecto: Paso a paso.
    """
    if method == SolverMethod.GRAFICO:
        return None
    choice = st.session_state.get(_MODE_CHOICE_KEY, MODE_STEP_BY_STEP)
    st.session_state[_MODE_KEY] = choice
    st.radio(
        "Modo de solución",
        options=_MODES,
        horizontal=True,
        key=_MODE_KEY,
        on_change=_remember_mode,
        help="Directa: solo el resultado. Paso a paso: forma estándar e iteraciones. "
             "Cambiar de modo no vuelve a resolver el modelo.",
    )
    return st.session_state[_MODE_KEY]


def _remember_mode() -> None:
    st.session_state[_MODE_CHOICE_KEY] = st.session_state[_MODE_KEY]


# Estado
# ======

def _solve_and_store(model: LPModel, method: SolverMethod) -> None:
    """Ejecuta el caso de uso y guarda el resultado; los errores se muestran, no rompen la app."""
    try:
        with st.spinner("Resolviendo..."):
            solution = solve_lp(model, method)
    except (ValueError, NotImplementedError) as error:
        st.error(str(error), icon=":material/error:")
        return

    st.session_state.solutions[method] = solution
    st.session_state.current_step = 0
    st.session_state.results_invalidated = False


def _current_solution(model: LPModel, method: SolverMethod):
    """La solución guardada para el método elegido, solo si es del modelo vigente"""
    solution = st.session_state.get("solutions", {}).get(method)
    if solution is None:
        return None
    if solution.model_fingerprint != hash(model):
        return None
    return solution


# Resultados del método gráfico
# =============================

def _render_graphical_result(
    solution: Solution, model: LPModel, number_format: str
) -> None:
    _render_status_banner(solution)

    if solution.status == SolutionStatus.OPTIMA:
        _render_optimal_values(solution, number_format)

    for note in solution.notes:
        st.markdown(f"- {note}")

    graphical = solution.graphical
    figure = build_graphical_figure(
        graphical, sense=model.sense, number_format=number_format
    )
    st.plotly_chart(figure, width="stretch")
    st.caption(
        "Escala 1:1 — una unidad de x₁ ocupa lo mismo que una unidad de x₂; "
        "la cuadrícula es cuadrada"
    )

    st.subheader("Vértices")
    hidden = hidden_vertices_count(graphical)
    if hidden:
        st.caption(
            f"La tabla lista todas las intersecciones de rectas frontera; "
            f"la gráfica solo dibuja las que caen en la ventana de visualización "
            f"({hidden} quedan fuera)."
        )
    st.dataframe(
        build_vertices_rows(graphical, number_format),
        hide_index=True,
        width="stretch",
    )

    _render_slacks(solution, model, number_format)

# Resultados del Gran M
# ======================

def _render_simplex_result(
    solution: Solution, model: LPModel, number_format: str, mode
) -> None:
    """
    Resultado de Gran M (HU-15). Los dos modos terminan con la MISMA función
    `_render_final_solution`, así la solución final es idéntica en ambos.
    """
    _render_status_banner(solution)
    if mode == MODE_STEP_BY_STEP and solution.steps:
        _render_standard_form(solution.steps[0])
        _render_iterations(solution, model, number_format)
        st.subheader("Solución final")
    _render_final_solution(solution, model, number_format)


def _render_final_solution(solution: Solution, model: LPModel, number_format: str) -> None:
    """Valor de cada variable, Z y holgura o exceso; o el porqué si no hay óptimo."""
    if solution.status == SolutionStatus.OPTIMA:
        _render_optimal_values(solution, number_format)
        _render_slacks(solution, model, number_format)
    elif solution.steps:
        # El certificado del caso especial vive en la justificación del último paso (p. ej. "la artificial R2 sigue en la base con valor 3 > 0").
        with st.expander("¿Por qué? (último paso del método)"):
            st.write(solution.steps[-1].justification)
    for note in solution.notes:
        st.info(note, icon=":material/info:")


def _render_standard_form(first_step: Step) -> None:
    """Forma estándar: holguras, excesos, artificiales y preparación de la fila 0 (HU-06/15)."""
    st.subheader("Forma estándar")
    with st.container(border=True):
        for note in first_step.setup_notes:
            st.markdown(f"- {note}")


def _render_iterations(solution: Solution, model: LPModel, number_format: str) -> None:
    """Navegación (HU-08) y la iteración elegida: tableau resaltado y justificación (HU-09)."""
    st.subheader("Iteraciones")
    index = render_navigator(len(solution.steps))
    step = solution.steps[index]

    view = build_tableau_view(
        step,
        minimize=model.sense == OptimizationSense.MINIMIZE,
        number_format=number_format,
    )
    st.markdown(f"**{view.title}**")
    st.html(render_tableau_html(view) + legend_html())
    st.info(step.justification, icon=":material/lightbulb:")

    # Notas propias de la iteración (degeneración, ciclado, óptimos múltiples...); la forma estándar ya se mostró arriba
    for note in step.notes:
        if note not in step.setup_notes:
            st.warning(note, icon=":material/info:")

def _render_status_banner(solution: Solution) -> None:
    if solution.status == SolutionStatus.OPTIMA:
        st.success(solution.message, icon=":material/check_circle:")
    elif solution.status == SolutionStatus.NO_FACTIBLE:
        st.error(solution.message, icon=":material/error:")
    else:
        st.warning(solution.message, icon=":material/warning:")

# Resultados compartidos (Gráfico y Gran M)
# =========================================

# st.metric recorta el valor con "…" (white-space: nowrap + text-overflow:
# ellipsis). Dentro de esta tarjeta se permite el salto de línea; tipografía,
# tamaños y layout quedan exactamente igual.
_METRIC_CSS = """
<style>
.st-key-result_card [data-testid="stElementContainer"]:has(style){display:none;}
.st-key-result_card [data-testid="stMetricValue"],
.st-key-result_card [data-testid="stMetricValue"] > div{
  white-space:normal !important;
  overflow:visible !important;
  text-overflow:clip !important;
  overflow-wrap:anywhere;
  line-height:1.25;
}
</style>
"""


def _format_values(values, number_format: str) -> str:
    parts = []
    for name, value in values:
        shown = f"x{subscript(int(name[1:]))}" if name[1:].isdigit() else name
        parts.append(f"{shown} = {format_number(value, number_format)}")
    return ", ".join(parts)


def _render_optimal_values(solution: Solution, number_format: str) -> None:
    """Estado, Z* y el/los vértice(s) óptimo(s). Con dos extremos se informa el segmento."""
    with st.container(border=True, key="result_card"):
        st.markdown(_METRIC_CSS, unsafe_allow_html=True)
        columns = st.columns(3)
        columns[0].metric("Estado", solution.status.value)
        if solution.optimal_value is not None:
            columns[1].metric("Z*", format_number(solution.optimal_value, number_format))
        columns[2].metric("Solución", _format_values(solution.values, number_format))
        if solution.alt_values:
            # values = primer óptimo; alt_values = el del pivote extra. El orden no es semántico.
            st.info(
                f"Otro vértice óptimo: {_format_values(solution.alt_values, number_format)}. "
                "Hay infinitos óptimos sobre el segmento que los une: "
                "x = λA + (1−λ)B, con 0 ≤ λ ≤ 1.",
                icon=":material/join:",
            )

def _render_slacks(
    solution: Solution, model: LPModel, number_format: str
) -> None:
    """Holgura o exceso de cada restricción en el óptimo; compartido por Gráfico y Gran M (HU-15)."""
    if solution.status != SolutionStatus.OPTIMA or not solution.slacks:
        return
    st.markdown("**Holgura o exceso de cada restricción**")
    st.dataframe(
        build_slack_rows(model, solution, number_format),
        hide_index=True,
        width="stretch",
    )
