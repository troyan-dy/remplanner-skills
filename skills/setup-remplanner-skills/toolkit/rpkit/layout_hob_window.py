"""Плита — окно: по плану, от края модуля плиты до откоса ближайшего окна."""

import math

from rpkit.layout_kitchen_run import along_x

WINDOW_CM = 150  # окно дальше от плиты не проверяется


def _stove_rect(stove):
    """Габарит модуля плиты на плане: stove — (линия кухни, точка, начало, конец)."""
    piece = stove[0]
    axis = 0 if along_x(piece) else 1
    strip = list(piece["rect"])
    strip[axis] = piece["rect"][axis] + stove[2]
    strip[axis + 2] = stove[3] - stove[2]
    return strip


def _axis_gap(first, second, axis):
    """Зазор между прямоугольниками по оси (0 — перекрываются)."""
    first_end = first[axis] + first[axis + 2]
    second_end = second[axis] + second[axis + 2]
    return max(second[axis] - first_end, first[axis] - second_end, 0)


def _rect_gap(first, second):
    """Расстояние между прямоугольниками (0 — касаются или пересекаются)."""
    return math.hypot(_axis_gap(first, second, 0), _axis_gap(first, second, 1))


def _hob_window(plan, stove):
    """[hob_window], если окно ближе WINDOW_CM к плите stove, иначе []."""
    rect = _stove_rect(stove)
    gaps = [
        _rect_gap(rect, window["rect"])
        for window in plan.get("windows", [])
    ]
    if not gaps or min(gaps) >= WINDOW_CM:
        return []
    label = stove[0]["id"]
    return [("hob_window", f"{label} плита — окно", round(min(gaps)))]


def hob_windows(plan, runs):
    """Плита — окно для каждой плиты линий кухни runs."""
    found = []
    for run in runs:
        for stove in run.stoves:
            found.extend(_hob_window(plan, stove))
    return found
