"""Проходы и маршруты от входа: ширина самого широкого пути к каждой цели и кратчайшие маршруты."""

import math

from rpkit.layout_bearing_gap import bearing_gap
from rpkit.layout_distance import INF
from rpkit.layout_masks import flat_cells
from rpkit.layout_paths import shortest, widest
from rpkit.layout_targets import targets

PASS_MAIN = "pass_main"
WIDE_CM = 400  # шире — «400»: дальше сетка не мерит


def width_of(neck):
    """Ширина прохода по полю расстояний в горлышке (−1 — пути нет)."""
    width = round(2 * neck) if neck >= 0 else -1
    if width >= WIDE_CM or neck >= INF:
        return WIDE_CM
    return width


class _Passages:
    """Самые широкие и кратчайшие пути от входа и находки по целям."""

    def __init__(self, layout, start, radius):
        self.layout = layout
        cell = layout.grid.index(*start)
        self.widest = widest(layout.open_dist, layout.grid, cell)
        self.shortest = shortest(layout.open_dist, layout.grid, cell, radius)
        self.findings = []
        self.routes = []
        self.doors = {}

    def add(self, name, rect, rule):
        """Цель name: ширина прохода к ней и маршрут от входа."""
        free = self._free(rect)
        width, cap = self._width(free)
        if rule == PASS_MAIN:  # по двери одна строка — сторона, ближняя ко входу
            door = name.rsplit(" ", 1)[0]
            if width > self.doors.get(door, (-1, None))[0]:
                self.doors[door] = (width, cap)
        else:
            self.findings.append((rule, name, width, cap))
        self._route(free)

    def doors_found(self):
        """Находки pass_main по дверям; двери, в которые не попасть, ловит pass_any других целей."""
        return [
            (PASS_MAIN, door, width, cap)
            for door, (width, cap) in self.doors.items()
            if width >= 0
        ]

    def _free(self, rect):
        """Свободные для прохода клетки цели."""
        path = self.layout.masks.path
        cells = flat_cells(self.layout.grid, rect)
        return [cell for cell in cells if not path[cell]]

    def _width(self, free):
        """(ширина, cap): cap = ширина, если горлышко — между двумя несущими стенами (bearing_gap)."""
        best, parent = self.widest
        widest_cell = max(free, key=lambda cell: best[cell], default=None)
        if widest_cell is None:
            return width_of(-1), None
        width = width_of(best[widest_cell])
        if best[widest_cell] > 0 and bearing_gap(self.layout, best, parent, widest_cell):
            return width, width
        return width, None

    def _route(self, free):
        dist, parent = self.shortest
        reach = [cell for cell in free if dist[cell] < math.inf]
        if not reach:
            return
        cell = min(reach, key=lambda candidate: dist[candidate])
        route = []
        while cell != -1:
            route.append(cell)
            cell = parent[cell]
        self.routes.append(list(reversed(route)))


def measure_passages(layout, start, radius):
    """Проходы и маршруты: (находки, маршруты [список клеток]). Находка прохода — (правило, объект, ширина, cap):
    cap = ширина, если горлышко самого широкого пути — между двумя несущими стенами (bearing_gap), иначе None.
    Такую уступку judge считает «из-за несущего» и баллы за неё не берёт. radius — полуширина плеч (pass_any)."""
    passages = _Passages(layout, start, radius)
    for target in targets(layout):
        passages.add(*target)
    return passages.findings + passages.doors_found(), passages.routes
