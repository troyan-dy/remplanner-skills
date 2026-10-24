"""Выступающие углы стен и мебели на сетке проходов: вершина, где из четырёх клеток занята ровно одна."""

import math

from rpkit.layout_grid import STEP_CM
from rpkit.layout_vectors import minus

JAMB_CM = 25  # вершины у откосов дверей — не углы на маршруте
BUCKET_CM = 20  # корзины поиска вершин рядом с точкой маршрута
LEFT_CELLS = frozenset((0, 2))  # занятая клетка слева от вершины: наружу — вправо
TOP_CELLS = frozenset((0, 1))  # занятая клетка сверху: наружу — вниз


def _quad(grid, column, row):
    """Четыре клетки вокруг вершины (column + 1, row + 1): ↖, ↗, ↙, ↘."""
    top = row * grid.columns + column
    bottom = top + grid.columns
    return (top, top + 1, bottom, bottom + 1)


def _outward(corner):
    """Направление наружу от угла по номеру занятой клетки: 0 ↖, 1 ↗, 2 ↙, 3 ↘."""
    step_x = 1 if corner in LEFT_CELLS else -1
    step_y = 1 if corner in TOP_CELLS else -1
    return step_x, step_y


class _Vertices:
    """Поиск вершин-углов на сетке проходов плана."""

    def __init__(self, layout):
        self.layout = layout
        self.jambs = [
            point
            for door in layout.plan["doors"]
            for point in (door["hinge"], door["other"])
        ]

    def at(self, column, row):
        """(вершина, (наружу x, наружу y, занятая клетка)) или None."""
        quad = _quad(self.layout.grid, column, row)
        marks = [self.layout.masks.path[cell] for cell in quad]
        if sum(marks) != 1:
            return None
        corner = marks.index(1)
        origin = self.layout.grid.origin
        vertex = (
            origin[0] + (column + 1) * STEP_CM,
            origin[1] + (row + 1) * STEP_CM,
        )
        if self._near_jamb(vertex):
            return None
        return vertex, (*_outward(corner), quad[corner])

    def _near_jamb(self, vertex):
        return any(
            math.hypot(*minus(vertex, jamb)) < JAMB_CM
            for jamb in self.jambs
        )


def corner_vertices(layout):
    """{вершина: (наружу x, наружу y, занятая клетка)} — выступающие углы, кроме вершин у откосов дверей."""
    finder = _Vertices(layout)
    corners = {}
    for row in range(layout.grid.rows - 1):
        for column in range(layout.grid.columns - 1):
            found = finder.at(column, row)
            if found:
                corners[found[0]] = found[1]
    return corners


def bucket(point):
    """Корзина точки для поиска соседних вершин."""
    return (
        int(point[0] // BUCKET_CM),
        int(point[1] // BUCKET_CM),
    )
