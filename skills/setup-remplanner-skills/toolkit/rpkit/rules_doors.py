"""Двери и расстояния для правил жильцов: середина проёма, дверь в стене комнаты, расстояние до предмета."""

import math

from rpkit.rules_items import RECT, within

DOOR_REACH_CM = 30  # дверь в стене комнаты: середина проёма не дальше от границы (наружная стена 26)


def door_mid(door):
    """Середина дверного проёма."""
    hinge, other = door["hinge"], door["other"]
    middle_x = (hinge[0] + other[0]) / 2
    return middle_x, (hinge[1] + other[1]) / 2


def door_on(door, room):
    """Дверь в стене комнаты room: середина проёма в 30 см от её границы (наружная стена 26), в пределах стороны."""
    rect = room[RECT]
    middle = door_mid(door)
    return _on_side(middle, rect, 0) or _on_side(middle, rect, 1)


def _on_side(middle, rect, axis_index):
    """Середина проёма у границы rect поперёк оси axis_index и в пределах этой стороны."""
    if not _near_edges(middle[axis_index], rect, axis_index):
        return False
    other = 1 - axis_index
    return within(middle[other], rect, other)


def _near_edges(number, rect, axis_index):
    """number не дальше DOOR_REACH_CM от одной из границ rect по оси."""
    start, size = rect[axis_index], rect[axis_index + 2]
    to_end = abs(number - start - size)
    return min(abs(number - start), to_end) <= DOOR_REACH_CM


def rect_dist(piece, point):
    """Расстояние от точки до прямоугольника предмета (0 — внутри)."""
    rect = piece[RECT]
    gap_x = _gap(point[0], rect, 0)
    return math.hypot(gap_x, _gap(point[1], rect, 1))


def _gap(number, rect, axis_index):
    start, size = rect[axis_index], rect[axis_index + 2]
    return max(start - number, 0, number - start - size)
