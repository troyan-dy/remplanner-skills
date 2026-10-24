"""Створка двери: ось проёма, точки полотна, открытого на угол theta, и какие двери проверяются по створке."""

import math

from rpkit.layout_entry import is_entry
from rpkit.layout_vectors import dot, minus, scaled

LEAF_START_CM = 3  # точки полотна — от 3 см от петли
DOORWAY = "doorway"


def door_axis(door):
    """(ширина проёма, единичный вектор от петли к другому краю)."""
    offset = minus(door["other"], door["hinge"])
    width = math.hypot(*offset)
    return width, scaled(offset, width)


def _blade(door, theta):
    """(ширина, направление полотна, открытого на theta градусов от линии стены в сторону swing)."""
    width, unit = door_axis(door)
    swing = door["swing"]
    turn = (
        math.cos(math.radians(theta)),
        math.sin(math.radians(theta)),
    )
    direction = (
        dot(turn, (unit[0], swing[0])),
        dot(turn, (unit[1], swing[1])),
    )
    return width, direction


def _along(start, radius, blade, shift):
    """Координата точки полотна: от петли на radius по blade и на 1 см по swing."""
    return start + radius * blade + shift


def door_sector(door, theta):
    """Точки полотна двери, открытого на theta градусов от линии стены (по swing), через 1 см."""
    width, blade = _blade(door, theta)
    hinge, swing = door["hinge"], door["swing"]
    return [
        (
            _along(hinge[0], radius, blade[0], swing[0]),
            _along(hinge[1], radius, blade[1], swing[1]),
        )
        for radius in range(LEAF_START_CM, int(width))
    ]


def windoor_doors(plan):
    """id дверей балконных блоков (windows[].windoor_door) — проём в несущей стене, как у входной."""
    return {
        opening["windoor_door"]
        for opening in plan.get("windows", [])
        if opening.get("windoor_door")
    }


def is_doorway(door):
    """Проём без полотна (doorway: проём или купе)."""
    return door.get("kind") == DOORWAY


def leaf_doors(plan):
    """Двери со створкой, которую проверяют door_open и правила открытого полотна: без входной (как есть, в нише
    несущей стены; её swing — «внутрь», а не сторона открывания) и без doorway (проём или купе, створки нет)."""
    return [
        door for door in plan["doors"]
        if not is_entry(door) and not is_doorway(door)
    ]
