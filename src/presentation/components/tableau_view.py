"""
Tableau del símplex en HTML (HU-09)

Recibe la `TableauView` de application/step_navigation.py, que ya dice QUÉ celdas resaltar (roles), y aquí se decide CÓMO: colores, bordes y leyenda
- columna pivote (entra) en rojo, fila pivote (sale) en azul, elemento pivote en amarillo y razón mínima con borde y negrita.
- El color no es la única señal: el pivote y la razón mínima van en negrita, cada celda resaltada tiene un `title` (texto al pasar el mouse) y hay leyenda.

Es una función pura (devuelve un string), así se prueba sin Streamlit. Todo el texto pasa por html.escape.
"""
from html import escape
from typing import FrozenSet

from application.step_navigation import (
    MIN_RATIO,
    PIVOT_COLUMN,
    PIVOT_ELEMENT,
    PIVOT_ROW,
    TableauView,
)

# Tintes translúcidos para que el texto siga legible sobre el fondo claro del tema
COLUMN_COLOR = "rgba(220, 38, 38, 0.30)"      # rojo; más opaco que el azul para que no se lea rosado sobre el fondo del tema
ROW_COLOR = "rgba(37, 99, 235, 0.16)"         # azul
ELEMENT_COLOR = "#FDE047"                     # amarillo
MIN_RATIO_BORDER = "#1D4ED8"

_CSS = f"""
<style>
.lp-tableau-wrap {{ overflow-x: auto; margin: 0.25rem 0 0.5rem 0; }}
.lp-tableau {{ border-collapse: collapse; font-variant-numeric: tabular-nums;
  font-size: 0.92rem; white-space: nowrap; }}
.lp-tableau th, .lp-tableau td {{ border: 1px solid #F3D1E4; padding: 0.3rem 0.6rem;
  text-align: center; }}
.lp-tableau th {{ background: #FCEEF5; font-weight: 600; }}
.lp-tableau tbody tr:first-child td {{ border-bottom: 2px solid #B83280; }}
.lp-tableau .lp-label {{ font-weight: 600; }}
.lp-tableau .lp-rhs {{ border-left: 2px solid #B83280; }}
.lp-tableau .lp-col {{ background: {COLUMN_COLOR}; }}
.lp-tableau .lp-row {{ background: {ROW_COLOR}; }}
.lp-tableau .lp-pivot {{ background: {ELEMENT_COLOR}; font-weight: 700;
  box-shadow: inset 0 0 0 2px #CA8A04; }}
.lp-tableau .lp-min {{ font-weight: 700; box-shadow: inset 0 0 0 2px {MIN_RATIO_BORDER}; }}
.lp-legend {{ display: flex; flex-wrap: wrap; gap: 0.4rem 1.1rem; font-size: 0.82rem;
  margin-bottom: 0.25rem; }}
.lp-legend span {{ display: inline-flex; align-items: center; gap: 0.35rem; }}
.lp-legend i {{ display: inline-block; width: 0.95rem; height: 0.95rem;
  border: 1px solid #F3D1E4; border-radius: 3px; }}
</style>
"""

_TITLES = {
    PIVOT_ELEMENT: "Elemento pivote",
    PIVOT_COLUMN: "Columna pivote (variable que entra)",
    PIVOT_ROW: "Fila pivote (variable que sale)",
    MIN_RATIO: "Razón mínima",
}


def _classes(roles: FrozenSet[str]) -> list:
    """Precedencia: elemento pivote > fila > columna. La razón mínima se suma (borde)."""
    classes = []
    if PIVOT_ELEMENT in roles:
        classes.append("lp-pivot")
    elif PIVOT_ROW in roles:
        classes.append("lp-row")
    elif PIVOT_COLUMN in roles:
        classes.append("lp-col")
    if MIN_RATIO in roles:
        classes.append("lp-min")
    return classes


def _title(roles: FrozenSet[str]) -> str:
    for role in (PIVOT_ELEMENT, MIN_RATIO, PIVOT_ROW, PIVOT_COLUMN):
        if role in roles:
            return _TITLES[role]
    return ""


def _cell(tag: str, cell, extra_classes=()) -> str:
    classes = list(extra_classes) + _classes(cell.roles)
    attrs = f' class="{" ".join(classes)}"' if classes else ""
    title = _title(cell.roles)
    if title:
        attrs += f' title="{escape(title)}"'
    return f"<{tag}{attrs}>{escape(cell.text)}</{tag}>"


def render_tableau_html(view: TableauView) -> str:
    """Tabla HTML completa (con su CSS) de una iteración."""
    n = len(view.header)
    rhs_index = n - 2   # la penúltima columna es "Lado derecho"; la última, "Razón"

    def extra(j: int) -> tuple:
        if j in (0, 1):
            return ("lp-label",)
        if j == rhs_index:
            return ("lp-rhs",)
        return ()

    head = "".join(
        _cell("th", c, ("lp-rhs",) if j == rhs_index else ()) for j, c in enumerate(view.header)
    )
    body = "".join(
        "<tr>" + "".join(_cell("td", c, extra(j)) for j, c in enumerate(row)) + "</tr>"
        for row in view.rows
    )
    return (
        _CSS
        + '<div class="lp-tableau-wrap"><table class="lp-tableau">'
        + f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"
    )


def legend_html() -> str:
    """Leyenda de colores. Va junto a render_tableau_html, que trae el CSS."""
    items = (
        (COLUMN_COLOR, "", "Columna pivote (entra)"),
        (ROW_COLOR, "", "Fila pivote (sale)"),
        (ELEMENT_COLOR, "", "Elemento pivote"),
        ("transparent", f"box-shadow: inset 0 0 0 2px {MIN_RATIO_BORDER};", "Razón mínima"),
    )
    spans = "".join(
        f'<span><i style="background:{color};{style}"></i>{escape(text)}</span>'
        for color, style, text in items
    )
    return f'<div class="lp-legend">{spans}</div>'
