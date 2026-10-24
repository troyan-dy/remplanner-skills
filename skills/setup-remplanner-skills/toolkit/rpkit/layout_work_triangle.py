"""Рабочий треугольник кухни: первая мойка, первая плита (лицевая кромка) и лицевая грань первого холодильника."""

import math

from rpkit.layout_kinds import FRONT, is_fridge, kind, specs


def _face_mid(start, size, direction):
    """Середина предмета по оси, сдвинутая к лицевой грани."""
    return start + size / 2 + direction * size / 2


def _fridge_front(fridge):
    """Середина лицевой грани холодильника."""
    rect = fridge["rect"]
    face = FRONT[specs(fridge)[0]["back"]]
    return (
        _face_mid(rect[0], rect[2], face[0]),
        _face_mid(rect[1], rect[3], face[1]),
    )


def _triangle(sink, stove, fridge):
    """Сумма, кратчайшая и длиннейшая стороны треугольника мойка–плита–холодильник; sink и stove —
    (линия кухни, точка на лицевой кромке, начало, конец)."""
    sink_point, stove_point = sink[1], stove[1]
    fridge_point = _fridge_front(fridge)
    legs = [
        math.dist(sink_point, stove_point),
        math.dist(stove_point, fridge_point),
        math.dist(fridge_point, sink_point),
    ]
    return [
        ("triangle_sum", "мойка–плита–холодильник", round(sum(legs))),
        ("triangle_leg", "кратчайшая сторона треугольника", round(min(legs))),
        ("triangle_leg_max", "длиннейшая сторона треугольника", round(max(legs))),
    ]


def work_triangle(furniture, runs):
    """Находки треугольника, если на плане есть мойка, плита и холодильник, иначе []."""
    sinks = [run.sinks[0] for run in runs if run.sinks]
    stoves = [run.stoves[0] for run in runs if run.stoves]
    fridges = [piece for piece in furniture if is_fridge(kind(piece))]
    if sinks and stoves and fridges:
        return _triangle(sinks[0], stoves[0], fridges[0])
    return []
