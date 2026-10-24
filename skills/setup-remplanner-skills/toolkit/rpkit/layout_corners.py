"""Выступающие углы, у которых маршрут от входа поворачивает: ширина прохода у угла."""

import math

from rpkit.layout_corner_vertices import bucket, corner_vertices
from rpkit.layout_vectors import degrees_of, dot, minus, moved

TURN_SPAN = 12  # поворот маршрута — между точками за 12 клеток до и после
TURN_DEGREES = 30  # поворот от 30°
NEAR_CM = 4  # вершина у маршрута: не дальше полуширины плеч + 4 см
SEARCH = 2  # корзины вокруг точки маршрута: ±2
CORNER_OFFSET_CM = 0.6  # лучи — от точки чуть снаружи вершины
MERGE_CM = 30  # соседние вершины одной кромки — один угол
WALL = "стена"


def _angle(first, second):
    """Угол между векторами в градусах или None для нулевого вектора."""
    first_norm = math.hypot(*first)
    second_norm = math.hypot(*second)
    if not first_norm or not second_norm:
        return None
    return degrees_of(dot(first, second) / first_norm / second_norm)


def _buckets(corners):
    """{корзина: [вершины]} в порядке corners."""
    grouped = {}
    for vertex in corners:
        grouped.setdefault(bucket(vertex), []).append(vertex)
    return grouped


class _Turns:
    """Вершины углов рядом с точками маршрутов, где маршрут поворачивает."""

    def __init__(self, corners, radius):
        self.grouped = _buckets(corners)
        self.radius = radius
        self.hit = {}

    def route(self, points):
        """Отметить вершины у поворотов маршрута points."""
        for index in range(TURN_SPAN, len(points) - TURN_SPAN):
            near = self._near(points[index])
            if near and self._turns(points, index):
                self.hit.update((vertex, True) for vertex in near)

    def _near(self, point):
        return [
            vertex
            for near_bucket in self._around(bucket(point))
            for vertex in self.grouped.get(near_bucket, [])
            if math.hypot(*minus(vertex, point)) <= self.radius + NEAR_CM
        ]

    def _around(self, center):
        """Корзины в квадрате ±SEARCH вокруг center: по столбцам, в столбце — по строкам."""
        low_column = center[0] - SEARCH
        low_row = center[1] - SEARCH
        side = range(2 * SEARCH + 1)
        return [(low_column + column, low_row + row) for column in side for row in side]

    def _turns(self, points, index):
        point = points[index]
        incoming = minus(point, points[index - TURN_SPAN])
        angle = _angle(incoming, minus(points[index + TURN_SPAN], point))
        return angle is not None and angle >= TURN_DEGREES


def _width(layout, vertex, outward):
    """Ширина прохода у угла: свободное место по обеим граням и по биссектрисе."""
    origin = moved(vertex, outward, CORNER_OFFSET_CM)
    path = layout.masks.path
    return min(
        layout.ray(path, origin, (outward[0], 0)),
        layout.ray(path, origin, (0, outward[1])),
        layout.ray(path, origin, outward) / math.sqrt(2),
    )


def _finding(layout, vertex, corner):
    """(находка corner_turn, вершина)."""
    cell = corner[2]
    owner = layout.owner[cell]
    name = WALL
    if owner >= 0 and not layout.masks.wall[cell]:
        name = layout.plan["furniture"][owner]["id"]
    position = ", ".join(format(coordinate, ".0f") for coordinate in vertex)
    width = round(_width(layout, vertex, corner[:2]))
    return ("corner_turn", f"{name} ({position})", width), vertex


def _merged(found):
    """Один угол предмета/стены — один отчёт: соседние вершины одной кромки сливаются (остаётся самая узкая)."""
    ordered = sorted(found, key=lambda pair: pair[0][2])
    kept = []
    for pair in ordered:
        close = any(
            math.hypot(*minus(pair[1], other[1])) < MERGE_CM
            for other in kept
        )
        if not close:
            kept.append(pair)
    return [finding for finding, _ in kept]


def measure_corners(layout, routes, radius):
    """Выступающие углы, у которых маршрут поворачивает: ширина прохода у угла. radius — полуширина плеч."""
    corners = corner_vertices(layout)
    if not corners:
        return []
    turns = _Turns(corners, radius)
    for route in routes:
        turns.route([layout.grid.center(cell) for cell in route])
    return _merged([_finding(layout, vertex, corners[vertex]) for vertex in turns.hit])
