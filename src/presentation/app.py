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

# 2. Configuración de la página
st.set_page_config(page_title="Solver PL", layout="wide")

# 3. Inicialización de Session State (HU-05)
if "model_defined" not in st.session_state:
    st.session_state.model_defined = False
if "solution" not in st.session_state:
    st.session_state.solution = None

# 4. Stub de Solución para probar la UI (Simula 2 iteraciones)
def get_stub_solution() -> Solution:
    # ... (Aquí iría una solución hardcodeada con 2 Steps para probar la navegación)
    pass

# 5. Layout de Pestañas
st.title("Solver de Programación Lineal")
st.sidebar.title("Configuración Global")
format_choice = st.sidebar.radio("Mostrar números como:", ["Fracción", "Decimal"])
if st.sidebar.button("Reiniciar sesión"):
    st.session_state.clear()
    st.rerun()

tab1, tab2, tab3, tab4 = st.tabs(["Definir Modelo", "Resolver", "Sensibilidad", "Exportar"])

with tab1:
    st.header("Definir Modelo")
    if st.button("Construir y Validar Modelo (Stub)"):
        st.session_state.model_defined = True
        st.success("Modelo válido (Stub para Sprint 0)")

with tab2:
    st.header("Resolver")
    if st.session_state.model_defined:
        if st.button("Resolver (Stub)"):
            st.session_state.solution = get_stub_solution()
            st.success("Resuelto con éxito (Datos de prueba)")
        
        if st.session_state.solution:
            st.write(f"Estado: {st.session_state.solution.status.value}")
            # Aquí irán los componentes de navegación (HU-08) y tableau (HU-09)