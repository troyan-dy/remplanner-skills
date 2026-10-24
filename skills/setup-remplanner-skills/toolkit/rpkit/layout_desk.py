"""Рабочий стол: окно относительно сидящего — отклонение от «окно сбоку» (90°)."""

import math

from rpkit.layout_kinds import FRONT, kind, specs
from rpkit.layout_roles import is_desk
from rpkit.layout_vectors import degrees_of, dot, minus, negated

SEAT_CM = 30  # глаза сидящего — в 30 см перед столом
WINDOW_CM = 450  # окна дальше не учитываются
SIDE_DEGREES = 90


def _seat_eyes(start, size, direction):
    """Координата глаз сидящего: от середины стола за лицевую грань на SEAT_CM."""
    return start + size / 2 + direction * (size / 2 + SEAT_CM)


def _desk_eyes(desk, face):
    rect = desk["rect"]
    return (
        _seat_eyes(rect[0], rect[2], face[0]),
        _seat_eyes(rect[1], rect[3], face[1]),
    )


def _clamp(number, start, size):
    """number в пределах [start, start + size]."""
    return min(max(number, start), start + size)


def _closest_point(rect, point):
    """Ближайшая к point точка прямоугольника rect."""
    return (
        _clamp(point[0], rect[0], rect[2]),
        _clamp(point[1], rect[1], rect[3]),
    )


def _nearest_window(windows, eyes):
    """(расстояние, ближайшая точка) ближайшего окна в пределах WINDOW_CM или None."""
    best = None
    for window in windows:
        point = _closest_point(window["rect"], eyes)
        distance = math.dist(eyes, point)
        if distance < WINDOW_CM and (best is None or distance < best[0]):
            best = (distance, point)
    return best


def _desk_angle(desk, windows):
    """Угол между взглядом сидящего (на стол) и направлением на ближайшее окно или None."""
    face = FRONT[specs(desk)[0]["back"]]
    eyes = _desk_eyes(desk, face)
    best = _nearest_window(windows, eyes)
    if not best:
        return None
    view = minus(best[1], eyes)
    cosine = dot(view, negated(face)) / math.hypot(*view)  # сидящий смотрит на стол
    return degrees_of(cosine)


def measure_desk(layout):
    """desk_window по каждому рабочему столу, у которого есть окно ближе WINDOW_CM."""
    windows = layout.plan.get("windows", [])
    found = []
    for desk in layout.plan["furniture"]:
        if not is_desk(kind(desk)):
            continue
        angle = _desk_angle(desk, windows)
        if angle is not None:
            deviation = round(abs(angle - SIDE_DEGREES))
            found.append(("desk_window", desk["id"], deviation))
    return found
