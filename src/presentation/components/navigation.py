"""
Controles de navegación por iteraciones (HU-08)

Una sola fuente de verdad: `st.session_state.current_step` (decisión 7). Lo reinician `invalidate_results` y `_solve_and_store`; aquí solo se lee y se escribe con `clamp_step`.

- Los botones cambian `current_step` en un callback (on_click), que corre ANTES del rerun.
- El deslizador usa su propia clave (`nav_slider`) como espejo: antes de dibujarlo se copia `current_step` en ella, y su callback copia el valor de vuelta. Así botones y deslizador siempre muestran la misma iteración y no se escribe la clave de un widget ya creado (Streamlit lo prohíbe).
- Con una sola iteración no se dibuja el deslizador: st.slider falla si min_value == max_value.

Navegar solo cambia un entero: el solver no se vuelve a ejecutar.
"""
import streamlit as st

from application.step_navigation import clamp_step

STEP_KEY = "current_step"
SLIDER_KEY = "nav_slider"


def _go_to(target: int, n_steps: int) -> None:
    st.session_state[STEP_KEY] = clamp_step(target, n_steps)


def _from_slider(n_steps: int) -> None:
    _go_to(st.session_state[SLIDER_KEY], n_steps)


def render_navigator(n_steps: int) -> int:
    """Dibuja botones + deslizador y devuelve el índice de la iteración que se debe mostrar."""
    current = clamp_step(st.session_state.get(STEP_KEY, 0), n_steps)
    st.session_state[STEP_KEY] = current

    if n_steps <= 1:
        st.caption("Iteración 0 de 0: el tableau inicial ya es el final.")
        return current

    last = n_steps - 1
    first_col, prev_col, label_col, next_col, last_col = st.columns(
        [1, 1, 1.6, 1, 1], vertical_alignment="center"
    )
    first_col.button(
        "Primera", icon=":material/first_page:", key="nav_first", width="stretch",
        disabled=current == 0, on_click=_go_to, args=(0, n_steps),
    )
    prev_col.button(
        "Anterior", icon=":material/chevron_left:", key="nav_prev", width="stretch",
        disabled=current == 0, on_click=_go_to, args=(current - 1, n_steps),
    )
    label_col.markdown(
        f"<div style='text-align:center'><b>Iteración {current} de {last}</b></div>",
        unsafe_allow_html=True,
    )
    next_col.button(
        "Siguiente", icon=":material/chevron_right:", key="nav_next", width="stretch",
        disabled=current == last, on_click=_go_to, args=(current + 1, n_steps),
    )
    last_col.button(
        "Última", icon=":material/last_page:", key="nav_last", width="stretch",
        disabled=current == last, on_click=_go_to, args=(last, n_steps),
    )

    st.session_state[SLIDER_KEY] = current   # espejo: se fija ANTES de crear el widget
    st.slider(
        "Ir a la iteración", min_value=0, max_value=last, step=1,
        key=SLIDER_KEY, on_change=_from_slider, args=(n_steps,),
    )
    return current
