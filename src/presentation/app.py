"""
Punto de entrada de la aplicación (Solver de Programación Lineal).

Streamlit vuelve a ejecutar ESTE archivo completo, de arriba hacia abajo,
cada vez que el usuario interactúa con un widget (escribe, pulsa un botón,
cambia de opción...). Por eso el archivo está organizado así:

1. Configuración y estado    -> se ejecuta en cada rerun, pero solo inicializa
                                lo que todavía no existe en st.session_state.
2. Barra lateral             -> configuración global (formato de números),
                                panel de estado y reinicio de sesión.
3. Pestañas                  -> cada pestaña pinta su contenido. La de
                                "Definir Modelo" delega en model_tab.py.
4. Panel de estado -> se pinta DESPUÉS de las pestañas, aunque
                                visualmente esté en la barra lateral (ver
                                `status_slot`). Así refleja los cambios que
                                las pestañas hicieron en esta misma ejecución.

Estado compartido (st.session_state)
- model_defined : bool, True si hay un modelo confirmado y listo para resolver.
- model         : el modelo confirmado (objeto de dominio), o None.
- solution      : la solución calculada, o None si aún no se resolvió.
- number_format : "Fracción" | "Decimal"; lo leen los helpers de formato.

"""
import sys
import os
import streamlit as st

# 1. Agregar la carpeta src al path para imports limpios
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(current_dir, '..'))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from domain.solver.solution import Solution, SolutionStatus, BasisInfo
from domain.solver.step import Step, PivotInfo
from domain.model.lp_model import LPModel
from fractions import Fraction

# Pestaña de definición del modelo (HU-01)
from presentation.tabs.model_tab import render_model_tab

# 2. Configuración de la página
#    set_page_config debe ser la PRIMERA llamada de Streamlit del script
st.set_page_config(
    page_title="Solver PL",
    page_icon=":material/calculate:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 3. Inicialización de Session State (HU-05)
#    El patrón "if not in" evita sobrescribir el valor en cada rerun.
if "model_defined" not in st.session_state:
    st.session_state.model_defined = False
if "solution" not in st.session_state:
    st.session_state.solution = None

# 4. Stub de Solución para probar la UI (Simula 2 iteraciones)
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

# 5. Layout de Pestañas
st.title("Solver de Programación Lineal")
st.caption("Define tu modelo, resuélvelo paso a paso con el método simplex y analiza la sensibilidad.")

# --- Barra lateral ---
st.sidebar.title("Configuración Global")
if "number_format" not in st.session_state:
    st.session_state.number_format = "Fracción"
# El valor elegido se guarda en session_state para que model_tab y los
# componentes de resultados formateen los números de forma consistente.
st.session_state.number_format = st.sidebar.radio(
    "Mostrar números como:",
    ["Fracción", "Decimal"],
    index=0 if st.session_state.number_format == "Fracción" else 1,
    horizontal=True,
    help="Afecta a la vista previa del modelo y a los resultados.",
)

st.sidebar.divider()
st.sidebar.subheader("Estado del modelo")
# Contenedor reservado: ocupa este lugar en la barra lateral, pero su contenido se escribe más abajo, tras ejecutar las pestañas
status_slot = st.sidebar.container()

st.sidebar.divider()
# El popover pide confirmación antes de borrar todo el session_state
with st.sidebar.popover("Reiniciar sesión", icon=":material/restart_alt:", use_container_width=True):
    st.markdown("Se perderán el modelo, la solución y toda la configuración.")
    if st.button("Sí, reiniciar todo", type="primary", icon=":material/delete_forever:", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- Pestañas ---
# Las etiquetas aceptan íconos Material con la sintaxis :material/nombre:
tab1, tab2, tab3, tab4 = st.tabs([
    ":material/edit_note: Definir Modelo",
    ":material/play_arrow: Resolver",
    ":material/query_stats: Sensibilidad",
    ":material/download: Exportar",
])

# tab1 delega todo su contenido (formulario, validación, confirmación) en model_tab.py.
with tab1:
    st.header("Definir Modelo")
    render_model_tab()

# tab2: solo se habilita si hay un modelo confirmado en tab1
with tab2:
    st.header("Resolver")
    if st.session_state.model_defined:
        if st.button("Resolver (Stub)", type="primary", icon=":material/play_arrow:"):
            with st.spinner("Resolviendo..."):
                st.session_state.solution = get_stub_solution(st.session_state.model)
                st.session_state.current_step = 0
        
        solution = st.session_state.solution
        if solution is not None:
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
        else:
            st.info("Pulsa **Resolver** para ejecutar el método simplex.", icon=":material/info:")
    else:
        st.warning(
            "Primero define y confirma un modelo en la pestaña **Definir Modelo**.",
            icon=":material/lock:",
        )

# tab3: análisis de sensibilidad (pendiente)
with tab3:
    st.header("Sensibilidad")
    if not st.session_state.solution:
        st.caption("Resuelve el modelo para poder analizar su sensibilidad.")
    st.info("Disponible cuando se implementen HU-11 y HU-12.", icon=":material/construction:")

# tab4: exportación de resultados (pendiente)
with tab4:
    st.header("Exportar")
    if not st.session_state.solution:
        st.caption("Resuelve el modelo para poder exportar los resultados.")
    st.info("Disponible cuando se implementen HU-13 y HU-14.", icon=":material/construction:")

# --- Panel de estado (se escribe al final, ver `status_slot`) ---
with status_slot:
    if st.session_state.model_defined and st.session_state.get("model") is not None:
        sidebar_model = st.session_state.model
        st.success("Modelo confirmado", icon=":material/check_circle:")
        side_col1, side_col2 = st.columns(2)
        side_col1.metric("Variables", sidebar_model.n_variables)
        side_col2.metric("Restricciones", sidebar_model.n_constraints)
    else:
        st.warning("Sin modelo confirmado", icon=":material/pending:")
        st.caption("Defínelo y confírmalo en la pestaña **Definir Modelo**.")

    if st.session_state.solution:
        st.success("Modelo resuelto", icon=":material/task_alt:")