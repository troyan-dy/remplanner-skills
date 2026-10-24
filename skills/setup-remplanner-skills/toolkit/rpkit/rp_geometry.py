"""Геометрия объектов .plan: точки с округлением и ось стены."""

import math
import operator
from typing import NamedTuple

XY = operator.itemgetter("x", "y")  # точка .plan → (x, y)


def r3(number):
    """Округление координаты до 0,001 см, как в файлах RemPlanner."""
    return round(number, 3)


def pt(x_cm, y_cm):
    """Точка .plan {"x", "y"}."""
    return {"x": r3(x_cm), "y": r3(y_cm)}


class Frame(NamedTuple):
    """Длина стены, единичный вектор оси и смещение левой кромки (как в образце: (uy, -ux) * depth/2)."""

    length: float
    unit_x: float
    unit_y: float
    left_x: float
    left_y: float


def wall_frame(start, end, depth):
    """Frame стены от точки start (x, y) до end."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    unit_x = dx / length
    unit_y = dy / length
    return Frame(
        length,
        unit_x,
        unit_y,
        unit_y * depth / 2,
        -unit_x * depth / 2,
    )


class WallAxis:
    """Ось стены .plan: точка на расстоянии along от p1 вдоль оси и across поперёк (в сторону l)."""

    def __init__(self, host):
        start, end = ends_of(host)
        self.origin = start
        depth = host["depth"]
        self.half = depth / 2
        frame = wall_frame(self.origin, end, depth)
        self.unit = (frame.unit_x, frame.unit_y)
        # единичная нормаль в сторону l
        self.normal = (
            frame.left_x / self.half,
            frame.left_y / self.half,
        )

    def point(self, along, across=0):
        """Точка .plan на оси (along) со сдвигом поперёк (across)."""
        x_cm = self._coord(0, along, across)
        y_cm = self._coord(1, along, across)
        return pt(x_cm, y_cm)

    def _coord(self, axis_index, along, across):
        origin = self.origin[axis_index]
        shifted = origin + self.unit[axis_index] * along
        return shifted + self.normal[axis_index] * across


def ends_of(host):
    """Концы оси стены .plan: (x1, y1), (x2, y2)."""
    return XY(host["p1"]), XY(host["p2"])


def position_on(host, point):
    """Параметр точки point вдоль оси стены host (см от p1)."""
    start, end = ends_of(host)
    span_x = end[0] - start[0]
    span_y = end[1] - start[1]
    along = (
        (point[0] - start[0]) * span_x
        + (point[1] - start[1]) * span_y
    )
    return along / math.hypot(span_x, span_y)
