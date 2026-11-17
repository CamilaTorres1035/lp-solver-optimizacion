"""
Método gráfico para modelos de exactamente 2 variables — HU-04.

Cómo se resuelve:
  1. Se intersectan de a pares las rectas frontera (incluidos los ejes). Cada
     intersección es una "solución en un vértice"
  2. Cada vértice se clasifica: FEV (factible) o no factible
  3. La solución óptima, si existe, está en un vértice FEV, así que se evalúa Z en los FEV y se escoge el mejor
  4. Si la región es abierta se revisa si Z mejora indefinidamente al alejarse por ella (problema no acotado). Una región abierta NO implica, por sí sola, un problema no acotado

Decisiones aprobadas:
- Se muestran todos los vértices óptimos detectados
- Si hay dos extremos óptimos, se informa el segmento con infinitos óptimos
- El orden values/alt_values es provisional por coordenadas hasta que Gran M fije el criterio definitivo
- Si la función objetivo es constante, se muestra nota y no se dibuja segmento
- Si Z permanece constante a lo largo de una semirrecta de la región, se informa que hay infinitos óptimos (ej.: Max x1; x1 <= 4)
"""
from fractions import Fraction
from typing import List, Optional, Sequence, Tuple

from ..model.enums import OptimizationSense, Relation
from ..model.lp_model import Constraint, LPModel
from .solution import (
    GraphLine,
    GraphVertex,
    GraphicalResult,
    Solution,
    SolutionStatus,
)

F = Fraction
_ZERO = F(0)

Point = Tuple[Fraction, Fraction]                          # (x1, x2) o un vector dirección
Window = Tuple[Fraction, Fraction, Fraction, Fraction]     # (xmin, xmax, ymin, ymax)
HalfPlane = Tuple[Fraction, Fraction, Fraction]            # (a1, a2, b)  ->  a1*x1 + a2*x2 <= b


class GraphicalSolver:
    """Solver gráfico: implementa el Protocol Solver."""

    def solve(self, model: LPModel) -> Solution:
        if model.n_variables != 2:
            # La UI muestra el aviso al seleccionar el método
            raise ValueError(
                f"El método gráfico solo aplica con exactamente 2 variables "
                f"(el modelo tiene {model.n_variables}). Usa Gran M."
            )

        constraints = model.constraints
        half_planes = _constraints_as_half_planes(constraints)

        # vértices (intersecciones de rectas frontera) y su clasificación
        intersection_points = _boundary_intersections(constraints)
        vertices = tuple(
            GraphVertex(
                point=p,
                is_feasible=_satisfies_all(p, half_planes),
                z_value=_objective_value(model, p),
            )
            for p in intersection_points
        )
        feasible_points = [v.point for v in vertices if v.is_feasible]

        # Direcciones por las que la región "sigue", vacío si la región es acotada
        open_directions = _open_region_directions(half_planes)

        window = _visible_window(
            intersection_points, region_is_open=bool(open_directions)
        )
        lines = _constraint_lines_for_plot(constraints, window)

        # Caso 1: no existe ningún vértice FEV: región factible vacía
        if not feasible_points:
            return _infeasible_solution(model, vertices, lines, window)

        # Caso 2: región abierta y Z mejora indefinidamente: no acotada
        improving_directions = tuple(
            d for d in open_directions if _improves(model, d)
        )
        if improving_directions:
            return _unbounded_solution(
                model, vertices, lines, window, half_planes, improving_directions
            )

        # Caso 3: hay óptimo, y está en un vértice FEV
        return _optimal_solution(
            model, vertices, feasible_points, open_directions,
            half_planes, lines, window,
        )

# Construcción de las tres respuestas posibles

def _infeasible_solution(
    model: LPModel,
    vertices: Tuple[GraphVertex, ...],
    lines: Tuple[GraphLine, ...],
    window: Window,
) -> Solution:
    return _solution_without_values(
        model,
        status=SolutionStatus.NO_FACTIBLE,
        notes=(
            "Ningún punto satisface todas las restricciones a la vez: "
            "la región factible es vacía.",
        ),
        message=(
            "El modelo no tiene solución factible. "
            "Revisa restricciones que se contradicen entre sí."
        ),
        graphical=_graphical_result(vertices, lines, window),
    )


def _unbounded_solution(
    model: LPModel,
    vertices: Tuple[GraphVertex, ...],
    lines: Tuple[GraphLine, ...],
    window: Window,
    half_planes: Sequence[HalfPlane],
    improving_directions: Tuple[Point, ...],
) -> Solution:
    return _solution_without_values(
        model,
        status=SolutionStatus.NO_ACOTADA,
        notes=(
            "La región es abierta y Z mejora sin límite al alejarse por ella. "
            "Posible restricción faltante.",
        ),
        message=(
            "La solución es no acotada: la función objetivo puede "
            "mejorar indefinidamente. Revisa la formulación."
        ),
        graphical=_graphical_result(
            vertices, lines, window,
            polygon=_feasible_region_polygon(half_planes, window),
            region_is_unbounded=True,
            improving_directions=improving_directions,
        ),
    )


def _optimal_solution(
    model: LPModel,
    vertices: Tuple[GraphVertex, ...],
    feasible_points: List[Point],
    open_directions: Tuple[Point, ...],
    half_planes: Sequence[HalfPlane],
    lines: Tuple[GraphLine, ...],
    window: Window,
) -> Solution:
    pick_best = max if model.sense == OptimizationSense.MAXIMIZE else min
    best_z = pick_best(_objective_value(model, p) for p in feasible_points)

    optimal_points = sorted(
        p for p in feasible_points if _objective_value(model, p) == best_z
    )
    main_point = optimal_points[0]

    c1, c2 = model.objective
    objective_is_constant = c1 == 0 and c2 == 0

    notes: List[str] = []
    has_constant_z_ray = False  # ¿Z se queda igual a lo largo de una semirrecta?
    alt_values: Tuple[Tuple[str, Fraction], ...] = ()
    optimal_segment: Optional[Tuple[Point, Point]] = None

    if objective_is_constant:
        notes.append(
            "La función objetivo es constante (Z = 0): cualquier punto "
            "factible es óptimo. Se reporta el primer vértice por orden."
        )
    else:
        # Óptimos múltiples entre vértices: la recta de isoutilidad coincide con una arista de la región (ej.: Max 3x1+2x2 en Wyndor -> Z = 18)
        if len(optimal_points) >= 2:
            first, last = optimal_points[0], optimal_points[-1]
            optimal_segment = (first, last)
            alt_values = (("x1", last[0]), ("x2", last[1]))
            notes.append(
                f"Óptimos múltiples: Z = {_fmt(best_z)} en todo el segmento entre "
                f"{_fmt_point(first)} y {_fmt_point(last)}. "
                f"Hay infinitos puntos óptimos: x = λA + (1−λ)B, 0 ≤ λ ≤ 1."
            )

        # Óptimos sobre una semirrecta: la región es abierta y hay una dirección en la que Z no cambia (ej.: Max x1; x1 <= 4 -> (4, x2), x2 >= 0).
        has_constant_z_ray = any(
            _objective_change(model, d) == 0 for d in open_directions
        )
        if has_constant_z_ray:
            notes.append(
                "Hay infinitos óptimos: desde el vértice óptimo, Z permanece "
                "constante a lo largo de una semirrecta de la región."
            )

    if open_directions and not has_constant_z_ray:
        notes.append(
            "La región es abierta, pero Z no mejora en ninguna dirección "
            "infinita: el óptimo existe y está en un vértice."
        )

    notes.append("Resuelto con el método gráfico.")

    isoprofit_segment = (
        None
        if objective_is_constant
        else _line_segment_in_window(c1, c2, best_z, window)
    )

    return Solution(
        status=SolutionStatus.OPTIMA,
        values=(("x1", main_point[0]), ("x2", main_point[1])),
        optimal_value=best_z,
        slacks=_slack_values(model, main_point),
        alt_values=alt_values,
        steps=(),
        notes=tuple(notes),
        message=(
            f"Óptimo encontrado en {_fmt_point(main_point)} "
            f"con Z = {_fmt(best_z)}."
        ),
        basis_info=None,
        model_fingerprint=hash(model),
        graphical=_graphical_result(
            vertices, lines, window,
            polygon=_feasible_region_polygon(half_planes, window),
            optimal_vertices=tuple(optimal_points),
            optimal_segment=optimal_segment,
            isoprofit_z=best_z,
            isoprofit_segment=isoprofit_segment,
            region_is_unbounded=bool(open_directions),
        ),
    )


def _solution_without_values(
    model: LPModel,
    status: SolutionStatus,
    notes: Tuple[str, ...],
    message: str,
    graphical: GraphicalResult,
) -> Solution:
    """Solution para los casos sin óptimo (no factible / no acotada)."""
    return Solution(
        status=status,
        values=(),
        optimal_value=None,
        slacks=(),
        alt_values=(),
        steps=(),
        notes=notes,
        message=message,
        basis_info=None,
        model_fingerprint=hash(model),
        graphical=graphical,
    )


def _graphical_result(
    vertices: Tuple[GraphVertex, ...],
    lines: Tuple[GraphLine, ...],
    window: Window,
    *,
    polygon: Tuple[Point, ...] = (),
    optimal_vertices: Tuple[Point, ...] = (),
    optimal_segment: Optional[Tuple[Point, Point]] = None,
    isoprofit_z: Optional[Fraction] = None,
    isoprofit_segment: Optional[Tuple[Point, Point]] = None,
    region_is_unbounded: bool = False,
    improving_directions: Tuple[Point, ...] = (),
) -> GraphicalResult:
    """Todo lo que necesita la UI para dibujar; los valores por defecto son 'nada que dibujar'."""
    return GraphicalResult(
        vertices=vertices,
        region_polygon=polygon,
        lines=lines,
        window=window,
        optimal_vertices=optimal_vertices,
        optimal_segment=optimal_segment,
        isoprofit_z=isoprofit_z,
        isoprofit_segment=isoprofit_segment,
        region_is_unbounded=region_is_unbounded,
        improving_directions=improving_directions,
    )


# Geometría: semiplanos, vértices y factibilidad

def _constraints_as_half_planes(
    constraints: Sequence[Constraint],
) -> Tuple[HalfPlane, ...]:
    """
    Convierte TODO a la forma a1*x1 + a2*x2 <= b, incluida la no negatividad.
      >=  se multiplica por -1
      =   se parte en dos desigualdades (<= y >=)
    Así factibilidad, direcciones y recorte del polígono usan una sola regla.
    """
    rows: List[HalfPlane] = [
        (F(-1), F(0), F(0)),  # x1 >= 0   ->  -x1 <= 0
        (F(0), F(-1), F(0)),  # x2 >= 0   ->  -x2 <= 0
    ]
    for c in constraints:
        a1, a2 = c.coefficients
        if c.relation == Relation.LESS_EQUAL:
            rows.append((a1, a2, c.rhs))
        elif c.relation == Relation.GREAT_EQUAL:
            rows.append((-a1, -a2, -c.rhs))
        else:  # igualdad
            rows.append((a1, a2, c.rhs))
            rows.append((-a1, -a2, -c.rhs))
    return tuple(rows)


def _boundary_intersections(constraints: Sequence[Constraint]) -> Tuple[Point, ...]:
    """
    Puntos donde se cortan, de a pares, las rectas frontera (a1*x1 + a2*x2 = b), incluidos los ejes x1 = 0 y x2 = 0. Las rectas paralelas no se cortan (determinante exactamente 0) y los puntos repetidos se descartan
    """
    boundary_lines: List[HalfPlane] = [
        (F(1), F(0), F(0)),  # eje x1 = 0
        (F(0), F(1), F(0)),  # eje x2 = 0
    ]
    for c in constraints:
        a1, a2 = c.coefficients
        if a1 != 0 or a2 != 0:  # una restricción 0*x <= b no dibuja ninguna recta
            boundary_lines.append((a1, a2, c.rhs))

    points = set()
    for i in range(len(boundary_lines)):
        for j in range(i + 1, len(boundary_lines)):
            a1, a2, b1 = boundary_lines[i]
            c1, c2, b2 = boundary_lines[j]

            determinant = a1 * c2 - a2 * c1
            if determinant == 0:
                continue  # paralelas

            # Regla de Cramer para el sistema 2x2.
            points.add((
                (b1 * c2 - a2 * b2) / determinant,
                (a1 * b2 - b1 * c1) / determinant,
            ))

    return tuple(sorted(points))


def _satisfies_all(point: Point, half_planes: Sequence[HalfPlane]) -> bool:
    """¿El punto cumple todas las restricciones y x >= 0? (es decir, ¿es FEV?)"""
    return all(a1 * point[0] + a2 * point[1] <= b for a1, a2, b in half_planes)


def _objective_value(model: LPModel, point: Point) -> Fraction:
    return model.objective[0] * point[0] + model.objective[1] * point[1]


# Regiones abiertas: ¿Z mejora indefinidamente?

def _open_region_directions(half_planes: Sequence[HalfPlane]) -> Tuple[Point, ...]:
    """
    Direcciones en las que se puede avanzar sin salir de la región (si no devuelve ninguna, la región es acotada)

    Una dirección d es válida si, para cada semiplano, a*d <= 0 (avanzar no acerca a ninguna frontera). En 2D los rayos extremos de la región solo pueden ser paralelos a alguna recta frontera, así que basta probar esas direcciones; las combinaciones entre ellas no aportan nada nuevo. Los ejes ya están entre los semiplanos, por eso no se agregan aparte.
    """
    candidates: List[Point] = []
    for a1, a2, _ in half_planes:
        candidates.append((a2, -a1))
        candidates.append((-a2, a1))

    valid = set()
    for d1, d2 in candidates:
        if d1 == 0 and d2 == 0:
            continue  # semiplano 0*x <= b: no define dirección
        if all(a1 * d1 + a2 * d2 <= 0 for a1, a2, _ in half_planes):
            scale = max(abs(d1), abs(d2))
            valid.add((d1 / scale, d2 / scale))  # normaliza para no repetir

    return tuple(sorted(valid))


def _objective_change(model: LPModel, direction: Point) -> Fraction:
    """Cuánto cambia Z por cada unidad que se avanza en esa dirección."""
    return model.objective[0] * direction[0] + model.objective[1] * direction[1]


def _improves(model: LPModel, direction: Point) -> bool:
    """¿Avanzar en esa dirección mejora Z? (sube en Max, baja en Min)"""
    change = _objective_change(model, direction)
    return change > 0 if model.sense == OptimizationSense.MAXIMIZE else change < 0


# Dibujo: ventana, región factible y rectas

def _visible_window(points: Sequence[Point], region_is_open: bool) -> Window:
    """
    Ventana de dibujo: el origen y los vértices del primer cuadrante (factibles o no) más un margen del 20 %. Se ignoran los puntos con coordenadas negativas porque x >= 0

    Si la región es abierta se amplía al doble del vértice más lejano, para que en pantalla se vea que la región continúa y no termina en el último vértice.
    """
    in_first_quadrant = [p for p in points if p[0] >= 0 and p[1] >= 0]
    xs = [_ZERO] + [p[0] for p in in_first_quadrant]
    ys = [_ZERO] + [p[1] for p in in_first_quadrant]

    x_max, y_max = max(xs), max(ys)
    if region_is_open:
        reach = 2 * max(x_max, y_max, F(1))
        x_max = y_max = reach

    x_margin = x_max / 5 or F(1)
    y_margin = y_max / 5 or F(1)

    # El margen negativo deja ver los ejes
    return -x_margin, x_max + x_margin, -y_margin, y_max + y_margin


def _feasible_region_polygon(
    half_planes: Sequence[HalfPlane],
    window: Window,
) -> Tuple[Point, ...]:
    """
    Región factible como polígono: se parte del rectángulo de la ventana y se recorta con cada semiplano. Con una igualdad el resultado es un segmento (polígono degenerado); la UI debe dibujarlo como línea, no como relleno.
    """
    xmin, xmax, ymin, ymax = window
    polygon: Tuple[Point, ...] = (
        (xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax),
    )
    for a1, a2, b in half_planes:
        polygon = _clip_polygon(polygon, a1, a2, b)
        if not polygon:
            break
    return polygon


def _clip_polygon(
    polygon: Tuple[Point, ...],
    a1: Fraction,
    a2: Fraction,
    b: Fraction,
) -> Tuple[Point, ...]:
    """Recorta el polígono con a1*x + a2*y <= b (Sutherland–Hodgman, exacto)"""
    if not polygon:
        return ()

    clipped: List[Point] = []
    n = len(polygon)

    for i in range(n):
        current = polygon[i]
        following = polygon[(i + 1) % n]

        # Valor <= 0 significa "dentro del semiplano".
        d_current = a1 * current[0] + a2 * current[1] - b
        d_following = a1 * following[0] + a2 * following[1] - b
        current_inside = d_current <= 0
        following_inside = d_following <= 0

        if current_inside:
            clipped.append(current)

        # La arista cruza la frontera: se agrega el punto de corte.
        if current_inside != following_inside:
            t = d_current / (d_current - d_following)
            clipped.append((
                current[0] + t * (following[0] - current[0]),
                current[1] + t * (following[1] - current[1]),
            ))

    # Quita puntos consecutivos repetidos.
    unique: List[Point] = []
    for p in clipped:
        if not unique or p != unique[-1]:
            unique.append(p)
    if len(unique) > 1 and unique[0] == unique[-1]:
        unique.pop()

    return tuple(unique)


def _line_segment_in_window(
    a1: Fraction,
    a2: Fraction,
    b: Fraction,
    window: Window,
) -> Optional[Tuple[Point, Point]]:
    """Tramo visible de la recta a1*x + a2*y = b: sus cortes con el borde de la ventana."""
    if a1 == 0 and a2 == 0:
        return None

    xmin, xmax, ymin, ymax = window
    hits = set()

    if a2 != 0:
        for x in (xmin, xmax):  # bordes izquierdo y derecho
            y = (b - a1 * x) / a2
            if ymin <= y <= ymax:
                hits.add((x, y))

    if a1 != 0:
        for y in (ymin, ymax):  # bordes inferior y superior
            x = (b - a2 * y) / a1
            if xmin <= x <= xmax:
                hits.add((x, y))

    ordered = sorted(hits)
    if len(ordered) < 2:
        return None  # la recta no cruza la ventana
    return ordered[0], ordered[-1]


def _constraint_lines_for_plot(
    constraints: Sequence[Constraint],
    window: Window,
) -> Tuple[GraphLine, ...]:
    lines: List[GraphLine] = []

    for c in constraints:
        a1, a2 = c.coefficients
        if a1 == 0 and a2 == 0:
            continue  # no es una recta

        segment = _line_segment_in_window(a1, a2, c.rhs, window)
        lines.append(GraphLine(
            label=f"R{c.original_index}",
            coefficients=(a1, a2),
            relation=c.relation,
            rhs=c.rhs,
            p1=segment[0] if segment else None,
            p2=segment[1] if segment else None,
        ))

    return tuple(lines)


# Holguras y formato

def _slack_values(model: LPModel, point: Point) -> Tuple[Fraction, ...]:
    """Holgura (<=) o exceso (>=) de cada restricción original en ese punto; 0 en igualdades."""
    result: List[Fraction] = []

    for c in model.constraints:
        lhs = c.coefficients[0] * point[0] + c.coefficients[1] * point[1]

        if c.relation == Relation.LESS_EQUAL:
            result.append(c.rhs - lhs)
        elif c.relation == Relation.GREAT_EQUAL:
            result.append(lhs - c.rhs)
        else:
            result.append(_ZERO)

    return tuple(result)


# Formato mínimo local

def _fmt(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def _fmt_point(p: Point) -> str:
    return f"({_fmt(p[0])}, {_fmt(p[1])})"