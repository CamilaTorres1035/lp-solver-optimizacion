"""
Vista del método gráfico (HU-04): figura de Plotly y tabla de vértices

Reciben un `GraphicalResult` y devuelven una `go.Figure` o filas de tabla
El formato de números llega como argumento

La figura contiene:
- una traza por restricción, con una etiqueta R1, R2, ... en el plano
- la región factible sombreada (o un segmento/punto si es degenerada)
- una anotación `(x1, x2) Z = …` por cada vértice FEV
- la recta de isoutilidad/isocosto en ROJO (`line.color == 'red'`) por el óptimo
- el segmento resaltado si hay óptimos múltiples
"""
from fractions import Fraction
import math
from typing import Dict, List, Optional, Sequence, Tuple

import plotly.graph_objects as go

from domain.model.enums import OptimizationSense
from domain.solver.solution import GraphicalResult
from utils.formatting import (
    FRACTION_MODE,
    format_constraint,
    format_number,
    format_point,
)

Point = Tuple[Fraction, Fraction]

# El rojo puro queda reservado para la recta de isoutilidad.
_LINE_PALETTE = (
    "#1f77b4", "#2ca02c", "#9467bd", "#8c564b",
    "#e377c2", "#17becf", "#7f7f7f", "#bcbd22",
)
_REGION_FILL = "rgba(46, 134, 193, 0.25)"
_FEV_COLOR = "#2e7d32"
_INFEASIBLE_COLOR = "#757575"
_OPTIMAL_SEGMENT_COLOR = "#ff9800"
_OPTIMAL_MARKER_COLOR = "gold"


def build_graphical_figure(
    result: GraphicalResult,
    *,
    sense: OptimizationSense,
    number_format: str = FRACTION_MODE,
) -> go.Figure:
    """Construye la gráfica 2D del método gráfico."""
    xmin, xmax, ymin, ymax = (float(v) for v in result.window)
    fig = go.Figure()

    _add_region(fig, result.region_polygon)
    _add_constraint_lines(fig, result, number_format)
    _add_vertices(fig, result, number_format)

    if result.optimal_segment is not None:
        _add_optimal_segment(fig, result.optimal_segment)
    if result.optimal_vertices:
        _add_optimal_markers(fig, result.optimal_vertices, number_format)
    if result.isoprofit_segment is not None and result.isoprofit_z is not None:
        _add_isoprofit_line(
            fig, result.isoprofit_segment, result.isoprofit_z, sense, number_format
        )

    span = max(xmax - xmin, ymax - ymin)
    step = float(_nice_step(span))
    grid = dict(
        dtick=step, tick0=0.0, showgrid=True,
        gridcolor="rgba(120,120,120,0.18)",
        zeroline=True, zerolinewidth=2, zerolinecolor="rgba(80,80,80,0.55)",
        ticks="outside", ticklen=4, mirror=True,
        constrain="domain", constraintoward="center",
    )
    fig.update_layout(
        xaxis=dict(title="x₁", range=[xmin, xmax], **grid),
        yaxis=dict(
            title="x₂", range=[ymin, ymax],
            scaleanchor="x", scaleratio=1, **grid,
        ),
        hovermode="closest",
        height=580,
        margin=dict(l=56, r=24, t=24, b=56),
        legend=dict(orientation="h", yanchor="top", y=-0.18, x=0),
        template="plotly_white",
    )
    return fig


def build_vertices_rows(
    result: GraphicalResult, number_format: str = FRACTION_MODE
) -> List[Dict[str, str]]:
    """Filas de la tabla bajo la gráfica: coordenadas, FEV / no factible y Z (solo si es FEV)."""
    optimal = set(result.optimal_vertices)
    rows: List[Dict[str, str]] = []
    for index, vertex in enumerate(result.vertices, start=1):
        if vertex.is_feasible:
            kind = "FEV (óptimo)" if vertex.point in optimal else "FEV"
            z_text = format_number(vertex.z_value, number_format)
        else:
            kind, z_text = "No factible", "—"
        rows.append({
            "Vértice": f"V{index}",
            "x₁": format_number(vertex.point[0], number_format),
            "x₂": format_number(vertex.point[1], number_format),
            "Tipo": kind,
            "Z": z_text,
        })
    return rows


# Trazas

def _add_region(fig: go.Figure, polygon: Sequence[Point]) -> None:
    points = list(polygon)
    if not points:
        return  # región vacía: solo rectas

    if len(points) >= 3 and _twice_area(points) != 0:
        xs = [float(p[0]) for p in points] + [float(points[0][0])]
        ys = [float(p[1]) for p in points] + [float(points[0][1])]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", fill="toself", fillcolor=_REGION_FILL,
            line=dict(width=0), name="Región factible", hoverinfo="skip",
        ))
        return

    # Degenerada (igualdad o punto): se dibuja como línea, no como relleno.
    start, end = min(points), max(points)
    fig.add_trace(go.Scatter(
        x=[float(start[0]), float(end[0])], y=[float(start[1]), float(end[1])],
        mode="lines+markers", line=dict(color="#2e86c1", width=5),
        name="Región factible (segmento o punto)", hoverinfo="skip",
    ))


def _add_constraint_lines(
    fig: go.Figure, result: GraphicalResult, number_format: str
) -> None:
    for index, line in enumerate(result.lines):
        color = _LINE_PALETTE[index % len(_LINE_PALETTE)]
        legend_name = (
            f"{line.label}: "
            f"{format_constraint(line.coefficients, line.relation.value, line.rhs, number_format)}"
        )
        if line.p1 is None or line.p2 is None:
            # La recta no cruza la ventana: queda en la leyenda, sin trazo.
            fig.add_trace(go.Scatter(
                x=[None], y=[None], mode="lines", line=dict(color=color, width=2),
                name=f"{legend_name} (fuera de la ventana)",
            ))
            continue

        fig.add_trace(go.Scatter(
            x=[float(line.p1[0]), float(line.p2[0])],
            y=[float(line.p1[1]), float(line.p2[1])],
            mode="lines", line=dict(color=color, width=2),
            name=legend_name, hovertext=legend_name, hoverinfo="text",
        ))
        # Etiqueta R# al 85 % del trazo, para que no choque con los ejes.
        label_x = line.p1[0] + Fraction(85, 100) * (line.p2[0] - line.p1[0])
        label_y = line.p1[1] + Fraction(85, 100) * (line.p2[1] - line.p1[1])
        fig.add_annotation(
            x=float(label_x), y=float(label_y), text=f"<b>{line.label}</b>",
            showarrow=False, font=dict(color=color, size=13),
            bgcolor="rgba(255,255,255,0.75)",
        )


def _add_vertices(
    fig: go.Figure, result: GraphicalResult, number_format: str
) -> None:
    xmin, xmax, ymin, ymax = result.window
    feasible, infeasible = [], []
    for vertex in result.vertices:
        x, y = vertex.point
        if not (xmin <= x <= xmax and ymin <= y <= ymax):
            continue  # vértice con coordenadas negativas: fuera de la ventana
        (feasible if vertex.is_feasible else infeasible).append(vertex)

    if infeasible:
        fig.add_trace(go.Scatter(
            x=[float(v.point[0]) for v in infeasible],
            y=[float(v.point[1]) for v in infeasible],
            mode="markers", name="No factible",
            marker=dict(symbol="x", size=8, color=_INFEASIBLE_COLOR),
            hovertext=[
                f"{format_point(v.point, number_format)} — no factible"
                for v in infeasible
            ],
            hoverinfo="text",
        ))

    if feasible:
        fig.add_trace(go.Scatter(
            x=[float(v.point[0]) for v in feasible],
            y=[float(v.point[1]) for v in feasible],
            mode="markers", name="Vértice FEV",
            marker=dict(symbol="circle", size=9, color=_FEV_COLOR),
            hovertext=[
                f"{format_point(v.point, number_format)} — "
                f"Z = {format_number(v.z_value, number_format)}"
                for v in feasible
            ],
            hoverinfo="text",
        ))
        for vertex in feasible:
            fig.add_annotation(
                x=float(vertex.point[0]), y=float(vertex.point[1]),
                text=(
                    f"{format_point(vertex.point, number_format)} "
                    f"Z = {format_number(vertex.z_value, number_format)}"
                ),
                showarrow=False, xanchor="left", xshift=8, yshift=12,
                font=dict(size=11, color=_FEV_COLOR),
            )


def _add_optimal_segment(
    fig: go.Figure, segment: Tuple[Point, Point]
) -> None:
    start, end = segment
    fig.add_trace(go.Scatter(
        x=[float(start[0]), float(end[0])], y=[float(start[1]), float(end[1])],
        mode="lines", line=dict(color=_OPTIMAL_SEGMENT_COLOR, width=8),
        opacity=0.8, name="Segmento óptimo (infinitos óptimos)", hoverinfo="skip",
    ))


def _add_optimal_markers(
    fig: go.Figure, optimal_vertices: Sequence[Point], number_format: str
) -> None:
    fig.add_trace(go.Scatter(
        x=[float(p[0]) for p in optimal_vertices],
        y=[float(p[1]) for p in optimal_vertices],
        mode="markers",
        name="Óptimo" if len(optimal_vertices) == 1 else "Óptimos",
        marker=dict(
            symbol="star", size=17, color=_OPTIMAL_MARKER_COLOR,
            line=dict(color="black", width=1),
        ),
        hovertext=[f"Óptimo {format_point(p, number_format)}" for p in optimal_vertices],
        hoverinfo="text",
    ))


def _add_isoprofit_line(
    fig: go.Figure,
    segment: Tuple[Point, Point],
    z_value: Fraction,
    sense: OptimizationSense,
    number_format: str,
) -> None:
    kind = "Isocosto" if sense == OptimizationSense.MINIMIZE else "Isoutilidad"
    name = f"{kind} (Z = {format_number(z_value, number_format)})"
    start, end = segment
    fig.add_trace(go.Scatter(
        x=[float(start[0]), float(end[0])], y=[float(start[1]), float(end[1])],
        mode="lines", line=dict(color="red", width=2, dash="dash"),
        name=name, hovertext=name, hoverinfo="text",
    ))


def _twice_area(points: Sequence[Point]) -> Fraction:
    """Doble del área con signo (fórmula del cordón); 0 si los puntos son colineales."""
    total = Fraction(0)
    for i, (x1, y1) in enumerate(points):
        x2, y2 = points[(i + 1) % len(points)]
        total += x1 * y2 - x2 * y1
    return total

def _nice_step(span: Fraction) -> Fraction:
    """Paso redondo (1, 2, 5 × 10^k) que da unas 8 divisiones en el eje."""
    target = float(span) / 8
    if target <= 0:
        return Fraction(1)
    base = Fraction(10) ** math.floor(math.log10(target))
    for factor in (1, 2, 5, 10):
        step = base * factor
        if float(step) >= target:
            return step
    return base * 10

def hidden_vertices_count(result: GraphicalResult) -> int:
    """Cuántos vértices de la tabla no se dibujan por caer fuera de la ventana."""
    xmin, xmax, ymin, ymax = result.window
    return sum(
        1 for v in result.vertices
        if not (xmin <= v.point[0] <= xmax and ymin <= v.point[1] <= ymax)
    )