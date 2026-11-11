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
def get_stub_solution() -> Solution:
    # Pendiente: devolver una Solution hardcodeada con 2 Steps para probar la
    # navegación entre iteraciones (HU-08) antes de tener el solver real.
    pass

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
                st.session_state.solution = get_stub_solution()
            st.success("Resuelto con éxito (Datos de prueba)", icon=":material/check_circle:")

        if st.session_state.solution:
            with st.container(border=True):
                st.metric("Estado", str(st.session_state.solution.status.value))
            # Aquí irán los componentes de navegación entre iteraciones (HU-08)
            # y la tabla del tableau simplex (HU-09)
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