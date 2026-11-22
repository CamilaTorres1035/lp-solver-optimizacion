"""
Caso de uso: invalidación de resultados (HU-05, decisión 7 del documento).

Lo usan tres puntos:
  - model_tab: cualquier edición del borrador  -> invalidate_results()
  - app.py:    "Reiniciar sesión"              -> invalidate_results()
  - app.py:    chequeo de huella en cada rerun -> discard_stale_results()

No importa Streamlit: recibe st.session_state como un mapping mutable, así se prueba con un dict normal, sin UI.
"""
from typing import Any, MutableMapping


def invalidate_results(state: MutableMapping[str, Any]) -> None:
    """Invalidación completa: desconfirma el modelo y descarta lo derivado."""
    state["model_defined"] = False
    state["model"] = None
    _discard_derived(state)


def discard_stale_results(state: MutableMapping[str, Any]) -> None:
    """Si la huella de alguna solución no coincide con el modelo vigente, descarta lo derivado. El modelo confirmado se conserva."""
    model = state.get("model")
    solutions = state.get("solutions") or {}
    if model is None or not solutions:
        return
    if any(s.model_fingerprint != hash(model) for s in solutions.values()):
        _discard_derived(state)


def _discard_derived(state: MutableMapping[str, Any]) -> None:
    had_results = bool(state.get("solutions")) or state.get("sensitivity") is not None
    state["solutions"] = {}
    state["sensitivity"] = None
    state["current_step"] = 0
    if had_results:
        # Aviso "debe resolver nuevamente" (HU-05): solo si había
        # resultados que perder. Lo apaga la próxima resolución exitosa.
        state["results_invalidated"] = True