"""Кровать: свободно вдоль боков (без 55 см у изголовья, где тумбы) и перед изножьем."""

import functools

from rpkit.layout_sweep import sweep
from rpkit.layout_targets import bed_sides

FOOT_CM = (20, 20)  # изножье: без 20 см по краям
RECT = "rect"


def bed_fronts_found(layout, piece, face):
    """Бока (без 55 см у изголовья) и изножье кровати."""
    sides = bed_sides(layout, piece)
    labels = _side_labels(len(sides))
    found = list(map(functools.partial(_side, layout, piece), labels, sides))
    foot = sweep(layout, piece[RECT], face, FOOT_CM)
    found.append(("bed_foot", f"{piece['id']} изножье", foot))
    return found


def _side(layout, piece, label, side):
    """Находка bed_side: side = (сторона, отступы по краям бока)."""
    depth = sweep(layout, piece[RECT], *side)
    return "bed_side", f"{piece['id']} {label}", depth


def _side_labels(count):
    """«бок», а у двуспальной — «бок 1», «бок 2»."""
    if count == 1:
        return ["бок"]
    return [f"бок {number}" for number in range(1, count + 1)]
