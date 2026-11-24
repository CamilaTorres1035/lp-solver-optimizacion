"""
Pestaña "Resolver"

Flujo en cada ejecución:
    1. Si no hay modelo confirmado, se pide definirlo
    2. SELECTOR de método (siempre visible). El aviso de n ≠ 2 sale AL SELECCIONAR el método gráfico, sin esperar a pulsar Resolver
    3. Botón Resolver -> caso de uso `solve_lp` -> `st.session_state.solutions[method]`
    4. Resultados: estado, valores, holguras y notas; en el gráfico: figura de Plotly y tabla de vértices (HU-04)

Estado que usa (st.session_state)
- model_defined / model : los escribe model_tab
- solutions             : dict {SolverMethod: Solution} con lo resuelto por método
- current_step          : índice de iteración para HU-08 (se reinicia al resolver)
- results_invalidated   : aviso "debes resolver nuevamente" (HU-05)
- number_format         : "Fracción" | "Decimal"

Una solución solo se muestra si coincide con el método elegido y con el modelo actual (`model_fingerprint`), para no enseñar resultados desactualizados (HU-05)
La navegación paso a paso y el tableau llegan con HU-08 y HU-09.
"""

import streamlit as st
from html import escape as _escape

from application.use_cases.solve_lp import solve_lp
from domain.model.lp_model import LPModel
from domain.model.enums import Relation
from domain.solver.solution import (
    Solution,
    SolutionStatus,
)
from domain.solver.solver_factory import SolverMethod
from presentation.components.plot_view import (
    build_graphical_figure,
    build_vertices_rows,
    hidden_vertices_count,
)
from utils.formatting import FRACTION_MODE, format_number, subscript

_METHOD_LABELS = {
    SolverMethod.GRAFICO: "Gráfico",
    SolverMethod.GRAN_M: "Gran M",
}


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
        _render_simplex_result(solution, model, number_format)


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

def _render_simplex_result(solution: Solution, model: LPModel, number_format: str) -> None:
    """Resultado de Gran M: estado, valores, holguras y notas (HU-06 / HU-10)."""
    _render_status_banner(solution)
    if solution.status == SolutionStatus.OPTIMA:
        _render_optimal_values(solution, number_format)
        _render_slacks(solution, model, number_format)
    elif solution.steps:
        # El certificado del caso especial vive en la justificación del último paso (p. ej. "la artificial R2 sigue en la base con valor 3 > 0").
        with st.expander("¿Por qué? (último paso del método)"):
            st.write(solution.steps[-1].justification)
    for note in solution.notes:
        st.info(note, icon=":material/info:")
    st.caption(
        f"{len(solution.steps)} iteraciones calculadas. "
        "La navegación y el tableau llegan con HU-08 y HU-09."
    )

def _render_status_banner(solution: Solution) -> None:
    if solution.status == SolutionStatus.OPTIMA:
        st.success(solution.message, icon=":material/check_circle:")
    elif solution.status == SolutionStatus.NO_FACTIBLE:
        st.error(solution.message, icon=":material/error:")
    else:
        st.warning(solution.message, icon=":material/warning:")

# ---------- resultados
# --------------------------------------------------------------- resultados

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
    """Holguras y excesos del óptimo; compartido por Gráfico y Gran M."""
    if solution.status != SolutionStatus.OPTIMA or not solution.slacks:
        return
    kinds = {
        Relation.LESS_EQUAL: "holgura",
        Relation.GREAT_EQUAL: "exceso",
        Relation.EQUAL: "igualdad",
    }
    with st.expander("Holguras y excesos en el óptimo"):
        for constraint, slack in zip(model.constraints, solution.slacks):
            st.markdown(
                f"- **R{constraint.original_index}** ({kinds[constraint.relation]}): "
                f"{format_number(slack, number_format)}"
            )