"""
Pestaña "Resolver"

Flujo en cada ejecución:
    1. Si no hay modelo confirmado, se pide definirlo
    2. SELECTOR de método (siempre visible). El aviso de n ≠ 2 sale AL SELECCIONAR el método gráfico, sin esperar a pulsar Resolver
    3. Botón Resolver -> caso de uso `solve_lp` -> `st.session_state.solution`
    4. Resultados: estado, valores, notas, gráfica de Plotly y tabla de vértices (HU-04)

Estado que usa (st.session_state)
- model_defined / model : los escribe model_tab
- solution              : la `Solution` calculada, o None
- solution_method       : el `SolverMethod` con el que se calculó `solution`
- number_format         : "Fracción" | "Decimal"

Una solución solo se muestra si coincide con el método elegido y con el modelo actual (`model_fingerprint`), para no enseñar resultados desactualizados (HU-05)

Gran M sigue usando `get_stub_solution` (transitorio) hasta que HU-06 exista; el método gráfico ya usa el solver real
"""
from fractions import Fraction

import streamlit as st

from application.use_cases.solve_lp import solve_lp
from domain.model.lp_model import LPModel
from domain.solver.solution import (
    BasisInfo,
    Solution,
    SolutionStatus,
)
from domain.solver.solver_factory import SolverMethod
from domain.solver.step import PivotInfo, Step
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
    elif method == SolverMethod.GRAN_M:
        st.caption(
            "Gran M está en desarrollo: por ahora se muestra una solución de ejemplo (stub)."
        )

    solve_label = "Resolver (Stub)" if method == SolverMethod.GRAN_M else "Resolver"
    if st.button(
        solve_label,
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
        _render_stub_result(solution)


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

    if solution.status == SolutionStatus.OPTIMA and solution.slacks:
        with st.expander("Holguras y excesos en el óptimo"):
            for index, slack in enumerate(solution.slacks, start=1):
                st.markdown(f"- **R{index}**: {format_number(slack, number_format)}")


def _render_status_banner(solution: Solution) -> None:
    if solution.status == SolutionStatus.OPTIMA:
        st.success(solution.message, icon=":material/check_circle:")
    elif solution.status == SolutionStatus.NO_FACTIBLE:
        st.error(solution.message, icon=":material/error:")
    else:
        st.warning(solution.message, icon=":material/warning:")


def _render_optimal_values(solution: Solution, number_format: str) -> None:
    """Estado, Z y el/los vértice(s) óptimo(s). Con dos extremos se informa el segmento."""
    with st.container(border=True):
        columns = st.columns(3)
        columns[0].metric("Estado", solution.status.value)
        if solution.optimal_value is not None:
            columns[1].metric("Z*", format_number(solution.optimal_value, number_format))
        columns[2].metric("Solución", _format_values(solution.values, number_format))

        if solution.alt_values:
            # Orden de values/alt_values provisional (por coordenadas) hasta que Gran M fije el criterio.
            st.info(
                f"Otro vértice óptimo: {_format_values(solution.alt_values, number_format)}. "
                "Hay infinitos óptimos sobre el segmento que los une.",
                icon=":material/join:",
            )


def _format_values(values, number_format: str) -> str:
    parts = []
    for name, value in values:
        shown = f"x{subscript(int(name[1:]))}" if name[1:].isdigit() else name
        parts.append(f"{shown} = {format_number(value, number_format)}")
    return ", ".join(parts)


# Resultados del stub (Gran M transitorio)
# ========================================

def _render_stub_result(solution: Solution) -> None:
    with st.container(border=True):
        col_status, col_z = st.columns(2)
        col_status.metric("Estado", solution.status.value)
        if solution.optimal_value is not None:
            col_z.metric("Z (ejemplo)", str(solution.optimal_value))
        st.caption(
            f"{len(solution.steps)} iteraciones generadas. "
            "Aquí se conectan la navegación (HU-08) y el tableau (HU-09)."
        )
    st.info(solution.message, icon=":material/science:")


# Stub transitorio (se elimina cuando Gran M devuelva soluciones reales)
def get_stub_solution(model: LPModel) -> Solution:
    """
    Solution hardcodeada de Wyndor (Max 3x1+5x2; x1<=4; 2x2<=12; 3x1+2x2<=18).
    Solo para probar la UI (HU-08/HU-09) sin esperar a los solvers reales.
    Los números son exactos y coherentes entre sí, pero NO son el resultado
    de resolver el modelo confirmado: el message y las notes lo aclaran.
    """
    F = Fraction
    column_labels = ("Z", "x1", "x2", "S1", "S2", "S3", "RHS")
    row_labels = ("0", "1", "2", "3")
    
    step_0 = Step(
        iteration=0,
        row_labels=row_labels,
        column_labels=column_labels,
        tableau=(
            (F(1), F(-3), F(-5), F(0), F(0),   F(0), F(0)),
            (F(0), F(1),  F(0),  F(1), F(0),   F(0), F(4)),
            (F(0), F(0),  F(2),  F(0), F(1),   F(0), F(12)),
            (F(0), F(3),  F(2),  F(0), F(0),   F(1), F(18)),
        ),
        basic_variables=("S1", "S2", "S3"),
        ratios=(None, F(6), F(9)),
        pivot=PivotInfo(row=2, column=2),
        notes=(),
        justification=(
            "Entra x2: es la variable con el coeficiente más negativo en la "
            "fila 0 (−5). Razones: R1 no aplica (coef. 0 → —), 12/2 = 6, "
            "18/2 = 9 → mínima 6 en la Ec 2, sale S2. Pivote = 2."
        ),
    )
        
    step_1 = Step(
        iteration=1,
        row_labels=row_labels,
        column_labels=column_labels,
        tableau=(
            (F(1), F(-3), F(0), F(0), F(5, 2),  F(0), F(30)),
            (F(0), F(1),  F(0), F(1), F(0),     F(0), F(4)),
            (F(0), F(0),  F(1), F(0), F(1, 2),  F(0), F(6)),
            (F(0), F(3),  F(0), F(0), F(-1),    F(1), F(6)),
        ),
        basic_variables=("S1", "x2", "S3"),
        ratios=(F(4), None, F(2)),
        pivot=PivotInfo(row=3, column=1),
        notes=(),
        justification=(
            "Entra x1: coeficiente más negativo en la fila 0 (−3). "
            "Razones: 4/1 = 4, R2 no aplica (coef. 0 → —), 6/3 = 2 "
            "→ mínima 2 en la Ec 3, sale S3. Pivote = 3."
        ),
    )

    step_2 = Step(
        iteration=2,
        row_labels=row_labels,
        column_labels=column_labels,
        tableau=(
            (F(1), F(0), F(0), F(1), F(3, 2),  F(1),    F(36)),
            (F(0), F(0), F(0), F(1), F(1, 3),  F(-1, 3), F(2)),
            (F(0), F(0), F(1), F(0), F(1, 2),  F(0),    F(6)),
            (F(0), F(1), F(0), F(0), F(-1, 3), F(1, 3),  F(2)),
        ),
        basic_variables=("S1", "x2", "x1"),
        ratios=(None, None, None),
        pivot=None,
        notes=("Prueba de optimalidad cumplida: no hay negativos en la fila 0.",),
        justification=(
            "Ningún coeficiente negativo en la fila 0 → la solución es óptima. "
            "Z = 36 con x1 = 2, x2 = 6."
        ),
    )
    
    basis = BasisInfo(
        basic_variables=("S1", "x2", "x1"),
        basis_inverse=(
            (F(1), F(1, 3),  F(-1, 3)),
            (F(0), F(1, 2),  F(0)),
            (F(0), F(-1, 3), F(1, 3)),
        ),
        row_to_constraint=(1, 2, 3),
        rhs_sign_flipped=(False, False, False),
        sense_factor=1,
    )
    
    return Solution(
        status=SolutionStatus.OPTIMA,
        values=(("x1", F(2)), ("x2", F(6))),
        optimal_value=F(36),
        slacks=(F(2), F(0), F(0)),
        alt_values=(),
        steps=(step_0, step_1, step_2),
        notes=(
            "Datos de prueba (stub) de Wyndor: no son el resultado de resolver tu modelo.",
        ),
        message="Solución de ejemplo para probar la interfaz (aún no hay solver real).",
        basis_info=basis,
        model_fingerprint=hash(model),
    )