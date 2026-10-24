"""Горлышко прохода между двумя несущими стенами: шире его не сделать никакой перестановкой."""

import math

from rpkit.layout_distance import INF
from rpkit.layout_grid import STEP_CM
from rpkit.layout_masks import flat_cells

SEARCH_SCALE = 1.1  # ближайшее препятствие ищется в круге чуть больше расстояния до него
BACK_RAY_CM = 20  # запас луча в противоположную сторону


def _narrower(near, step, neck):
    """Клетка step уже текущего горлышка neck (и в поле, а не INF)."""
    if near[step] >= INF:
        return False
    return neck is None or near[step] < near[neck]


def _bottleneck(layout, best, parent, cell):
    """Клетка с наименьшим полем на самом широком пути к cell (или None)."""
    near = layout.open_dist
    neck = None
    step = cell
    while step != -1:
        if _narrower(near, step, neck):
            neck = step
        step = parent[step]
    if neck is None or near[neck] > best[cell] + STEP_CM:
        return None
    return neck


class _Gap:
    """Горлышко: центр клетки и радиус поиска препятствий вокруг."""

    def __init__(self, layout, neck):
        self.layout = layout
        self.center = layout.grid.center(neck)
        self.reach = layout.dist[neck] * SEARCH_SCALE + 2 * STEP_CM

    def nearest(self):
        """(расстояние, клетка) ближайшего препятствия для проходов или None."""
        found = [
            (self._distance(cell), cell)
            for cell in flat_cells(self.layout.grid, self._square())
            if self.layout.masks.path[cell]
        ]
        return min(found) if found else None

    def direction(self, first, dist):
        """Единичный вектор от горлышка к препятствию first (dist — расстояние до него)."""
        first_x, first_y = self.layout.grid.center(first)
        unit_x = (first_x - self.center[0]) / (dist or 1)
        return unit_x, (first_y - self.center[1]) / (dist or 1)

    def opposite(self, unit):
        """Клетка за горлышком с противоположной стороны (по лучу против unit) или None."""
        limit = 2 * self.reach + BACK_RAY_CM
        backward = (-unit[0], -unit[1])
        back = self.layout.ray(self.layout.masks.path, self.center, backward, limit)
        beyond = back + STEP_CM
        return self.layout.grid.index(
            self.center[0] - unit[0] * beyond,
            self.center[1] - unit[1] * beyond,
        )

    def _square(self):
        reach = self.reach
        return [
            self.center[0] - reach,
            self.center[1] - reach,
            2 * reach,
            2 * reach,
        ]

    def _distance(self, cell):
        cell_x, cell_y = self.layout.grid.center(cell)
        offset_x = cell_x - self.center[0]
        return math.hypot(offset_x, cell_y - self.center[1])


def bearing_gap(layout, best, parent, cell):
    """Сужение на самом широком пути к клетке cell — между двумя несущими стенами? Идём по родителям до клетки
    с наименьшим полем (горлышко); ближайшее к ней препятствие и препятствие с противоположной стороны — оба
    клетки walls_bearing. Тогда шире горлышко не сделать никакой перестановкой."""
    neck = _bottleneck(layout, best, parent, cell)
    if neck is None:
        return False
    gap = _Gap(layout, neck)
    nearest = gap.nearest()
    if nearest is None:
        return False
    first = nearest[1]
    second = gap.opposite(gap.direction(first, nearest[0]))
    if not layout.masks.bearing[first] or second is None:
        return False
    return bool(layout.masks.bearing[second])
