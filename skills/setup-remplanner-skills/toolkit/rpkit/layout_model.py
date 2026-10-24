"""LayoutPlan — план и его сетки для проверки эргономики: поля расстояний и лучи."""

import math

from rpkit.layout_distance import INF, distance
from rpkit.layout_entry import door_center
from rpkit.layout_grid import STEP_CM, grid_for_plan
from rpkit.layout_masks import build_masks, flat_cells

RAY_CM = 400  # дальше луч не ведётся
DOOR_FREE_CM = 10  # у проёма сужение не считается в круге радиуса ширина / 2 + 10


class LayoutPlan:
    """План и его сетки: grid, masks, owner — какой предмет занимает клетку, dist — расстояние до препятствия
    для проходов, open_dist — то же, но у проёмов сужение не считается (ширину двери проверяет door_width)."""

    def __init__(self, plan):
        self.plan = plan
        self.grid = grid_for_plan(plan)
        masks, owner = build_masks(plan, self.grid)
        self.masks = masks
        self.owner = owner
        self.dist = distance(masks.path, self.grid)
        self.open_dist = self._near_doors()

    def blocked(self, mask, x_cm, y_cm):
        """Точка на препятствии маски или вне сетки."""
        cell = self.grid.index(x_cm, y_cm)
        return True if cell is None else bool(mask[cell])

    def ray(self, mask, origin, direction, limit=RAY_CM):
        """Свободная длина луча от точки origin по направлению direction до препятствия."""
        norm = math.hypot(*direction)
        unit = (direction[0] / norm, direction[1] / norm)
        along = 1.0
        while along < limit:
            x_cm = origin[0] + unit[0] * along
            y_cm = origin[1] + unit[1] * along
            if self.blocked(mask, x_cm, y_cm):
                return along - 1
            along += STEP_CM / 2
        return limit

    def _near_doors(self):
        """Копия поля расстояний, где у проёмов сужение не считается."""
        near = list(self.dist)
        for door in self.plan["doors"]:
            for cell in self._door_circle(door):
                near[cell] = INF
        return near

    def _door_circle(self, door):
        """Свободные клетки в круге радиуса ширина / 2 + DOOR_FREE_CM у середины проёма."""
        center = door_center(door)
        radius = door["width"] / 2 + DOOR_FREE_CM
        square = [
            center[0] - radius,
            center[1] - radius,
            2 * radius,
            2 * radius,
        ]
        return [
            cell for cell in flat_cells(self.grid, square)
            if self._in_circle(cell, center, radius) and not self.masks.path[cell]
        ]

    def _in_circle(self, cell, center, radius):
        x_cm, y_cm = self.grid.center(cell)
        offset = (x_cm - center[0]) ** 2
        return offset + (y_cm - center[1]) ** 2 <= radius * radius
