"""Цели проходов у межкомнатных дверей: точки по обе стороны проёма."""

from rpkit.layout_entry import door_center

PASS_MAIN = "pass_main"
DOOR_SIDE_CM = 45  # цель у двери — в 45 см от полотна с каждой стороны
MARK_CM = 4  # цель — квадрат 4×4 см
SIDES = ((1, "+"), (-1, "−"))


def _mark(center, shift, sign):
    """Квадрат MARK_CM вокруг точки center + sign·shift."""
    point_x = center[0] + sign * shift[0]
    point_y = center[1] + sign * shift[1]
    return [point_x - 2, point_y - 2, MARK_CM, MARK_CM]


def door_targets(door):
    """(имя, rect, pass_main) по обе стороны межкомнатной двери (в 45 см от полотна)."""
    center = door_center(door)
    if door["hinge"][1] == door["other"][1]:
        shift = (0, DOOR_SIDE_CM)
    else:
        shift = (DOOR_SIDE_CM, 0)
    return [
        (f"{door['id']} ({mark})", _mark(center, shift, sign), PASS_MAIN)
        for sign, mark in SIDES
    ]
