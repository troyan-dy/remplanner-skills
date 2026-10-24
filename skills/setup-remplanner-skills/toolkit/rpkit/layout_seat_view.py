"""Взгляд с дивана или кровати на ТВ: стены на луче глаза → экран, угол от оси места."""

import math

from rpkit.layout_eyes import seat_eyes
from rpkit.layout_grid import STEP_CM
from rpkit.layout_kinds import FRONT, kind, specs
from rpkit.layout_roles import is_bed, is_sofa
from rpkit.layout_vectors import degrees_of, dot, minus

TV_WALL_CM = 20  # у самого ТВ стена не мешает: он висит на ней
MAX_ANGLE = 50  # ТВ дальше 50° от оси сидящего — не напротив


def _view_point(eyes, view, step, steps):
    """step-я из steps точек луча глаза → экран."""
    x_cm = eyes[0] + view[0] * step / steps
    return x_cm, eyes[1] + view[1] * step / steps


def _through_wall(layout, eyes, view, distance):
    """На луче глаза → экран (без TV_WALL_CM у самого ТВ) есть стена: сквозь стену ТВ не смотрят."""
    steps = int(distance // STEP_CM)
    for step in range(1, steps):
        if distance - step * STEP_CM <= TV_WALL_CM:
            continue
        cell = layout.grid.index(*_view_point(eyes, view, step, steps))
        if cell is not None and layout.masks.wall[cell]:
            return True
    return False


def _off_axis(view, face, distance):
    """Угол от оси места в градусах или None, если ТВ дальше MAX_ANGLE от оси."""
    cosine = dot(view, face) / distance
    if cosine < math.cos(math.radians(MAX_ANGLE)):
        return None
    return degrees_of(cosine)


def _is_seat(piece):
    name = kind(piece)
    return is_sofa(name) or is_bed(name)


def seat_view(layout, center, seat):
    """(расстояние, угол от оси, id места) для дивана или кровати, с которых видно точку center, иначе None."""
    if not _is_seat(seat):
        return None
    face = FRONT[specs(seat)[0]["back"]]
    eyes = seat_eyes(seat, face)
    view = minus(center, eyes)
    distance = math.hypot(*view)
    if not distance or _through_wall(layout, eyes, view, distance):
        return None
    angle = _off_axis(view, face, distance)
    return None if angle is None else (distance, angle, seat["id"])
