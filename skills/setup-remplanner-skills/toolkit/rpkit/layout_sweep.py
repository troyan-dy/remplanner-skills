"""Свободная глубина перед гранью предмета (sweep): лучи от точек грани до препятствия."""

from rpkit.layout_grid import STEP_CM
from rpkit.layout_model import RAY_CM

EDGE_CM = (5, 5)  # отступы от краёв грани по умолчанию
HALF_CELL = 0.5  # точки грани — на полклетки снаружи предмета


def _face(rect, side, across):
    """Координата грани поперёк оси across, на полклетки снаружи."""
    start = rect[across]
    if side[across] > 0:
        return start + rect[across + 2] + HALF_CELL
    return start - HALF_CELL


def _positions(rect, along, margins):
    """Точки вдоль грани через STEP_CM без margins = (lo, hi) см по краям."""
    span = rect[along + 2] - margins[0]
    span -= margins[1]
    start = rect[along] + margins[0]
    count = int(span // STEP_CM) + 1
    return [start + number * STEP_CM for number in range(count)]


def _face_points(rect, side, margins):
    """Точки грани rect со стороны side."""
    if side[0]:
        face = _face(rect, side, 0)
        return [(face, position) for position in _positions(rect, 1, margins)]
    face = _face(rect, side, 1)
    return [(position, face) for position in _positions(rect, 0, margins)]


def _joint_cover(layout, point, side, joint):
    """Точка вплотную закрыта предметом из joint (стык угловой кухни) — не стена."""
    beyond_x = point[0] + side[0] * STEP_CM
    beyond_y = point[1] + side[1] * STEP_CM
    cell = layout.grid.index(beyond_x, beyond_y)
    if cell is None or layout.masks.wall[cell]:
        return False
    return layout.owner[cell] in joint


def sweep(layout, rect, side, margins=EDGE_CM, joint=()):
    """Свободная глубина перед гранью rect со стороны side=(sx, sy): минимум по точкам грани
    (без margins см по краям, считая от меньшей координаты). Точки, вплотную закрытые предметом из
    joint (индексы мебели — стык угловой кухни), не считаются."""
    depth = RAY_CM
    for point in _face_points(rect, side, margins):
        free = layout.ray(layout.masks.front, point, side)
        if free < STEP_CM and joint and _joint_cover(layout, point, side, joint):
            continue
        depth = min(depth, free)
    return depth
