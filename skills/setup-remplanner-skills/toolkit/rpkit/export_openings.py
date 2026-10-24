"""Проёмы выгрузки на стенах: какая стена держит проём и где он на её оси."""

import sys

from rpkit.export_segments import HORIZONTAL
from rpkit.rp_geometry import position_on


def find_wall(walls_by_seg, point, what, frame):
    """(Seg, стена .plan), в толще которой точка point координат RemPlanner; what — подпись проёма для ошибки."""
    candidates = [
        (seg, host) for seg, host in walls_by_seg if seg.contains(*point)
    ]
    if not candidates:
        _no_wall(what, point, frame)
    return min(candidates, key=lambda pair: _distance_to_axis(pair[0], point))


def _no_wall(what, point, frame):
    json_x, json_y = frame.to_json(*point)
    sys.exit(
        f"{what}: нет стены для проёма в точке ({json_x:.0f}, {json_y:.0f}) в координатах JSON — середина "
        "проёма должна лежать в толще стены walls_bearing, partitions или insulation",
    )


def _distance_to_axis(seg, point):
    across = point[1] if seg.axis == HORIZONTAL else point[0]
    return abs(across - seg.offset)


def rect_span(host, rect, frame):
    """Параметры вдоль стены host от и до проекции прямоугольника rect (координаты JSON)."""
    corners = _corners(frame.rect_rp(rect))
    positions = [position_on(host, corner) for corner in corners]
    return min(positions), max(positions)


def _corners(rect):
    x_cm, y_cm, width, height = rect
    return (
        (x_cm, y_cm),
        (x_cm + width, y_cm),
        (x_cm, y_cm + height),
        (x_cm + width, y_cm + height),
    )


def door_ends(host, opening, frame):
    """Параметры петли и второго края проёма двери opening вдоль стены host."""
    hinge = position_on(host, frame.to_rp(*opening["hinge"]))
    return hinge, position_on(host, frame.to_rp(*opening["other"]))
