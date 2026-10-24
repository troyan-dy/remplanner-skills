"""Стена .plan по осевой линии и привязка проёма к стене."""

import math

from rpkit.rp_geometry import pt, r3, wall_frame
from rpkit.rp_ids import uid

HEIGHT = 270  # высота стен в .plan, см (поле ceiling_height плана — только для людей)
SQ_CM_IN_M2 = 1e4


def wall(ends, depth, material="a_block"):
    """Стена от (x1, y1) до (x2, y2) — ends = (x1, y1, x2, y2) — толщиной depth из материала material."""
    frame = wall_frame(ends[:2], ends[2:], depth)
    record = _head(ends, depth)
    record.update(_faces(ends, (frame.left_x, frame.left_y)))
    area = round(frame.length * HEIGHT / SQ_CM_IN_M2, 1)
    record.update({
        "p1st": 0,
        "p2st": 0,
        "material": material,
        "color": 0,
        "inRoom": 0,
        "area": {"outer": area, "inner": area},
        "neighbors": {},
        "level": "1",
        "show_dls": True,
        "room_on_left": 0,
        "room_on_right": 0,
    })
    return record


def _head(ends, depth):
    x1, y1, x2, y2 = ends
    angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
    return {
        "id": uid(),
        "plan": "a",
        "role": "wall",
        "child": 0,
        "archive": 0,
        "demount": 0,
        "depth": depth,
        "height": HEIGHT,
        "angle": round(angle, 1),
        "p1": {"role": "p1", "x": r3(x1), "y": r3(y1), "demount": 0},
        "p2": {"role": "p2", "x": r3(x2), "y": r3(y2), "demount": 0},
    }


def _faces(ends, left):
    """Грани l и r стены (l1, l2, r1, r2) и их копии l1f…r2f."""
    first, second = ends[:2], ends[2:]
    faces = {
        "l1": _shifted(first, left, 1),
        "l2": _shifted(second, left, 1),
        "r1": _shifted(first, left, -1),
        "r2": _shifted(second, left, -1),
    }
    for key in tuple(faces):
        faces[f"{key}f"] = dict(faces[key])
    return faces


def _shifted(point, left, sign):
    """Конец стены, сдвинутый на кромку: sign 1 — к l, −1 — к r."""
    x_cm, y_cm = point
    if sign > 0:
        return pt(x_cm + left[0], y_cm + left[1])
    return pt(x_cm - left[0], y_cm - left[1])
