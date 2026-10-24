"""Двери для проверки эргономики: середина проёма, входная дверь и точка старта маршрутов."""

import sys

START_CM = 40  # старт маршрутов: от середины входной двери внутрь квартиры, см
DOORS = "doors"


def door_center(door):
    """Середина дверного проёма."""
    hinge, other = door["hinge"], door["other"]
    middle_x = (hinge[0] + other[0]) / 2
    return middle_x, (hinge[1] + other[1]) / 2


def is_entry(door):
    """Входная дверь квартиры: `"entry": true`, иначе id `door-entry`."""
    return bool(door.get("entry")) or door["id"] == "door-entry"


def entry_door(plan):
    """Входная дверь плана; без неё — выход с подсказкой."""
    doors = [door for door in plan[DOORS] if door.get("entry")]
    if not doors:
        doors = [door for door in plan[DOORS] if door["id"] == "door-entry"]
    if not doors:
        sys.exit('нет входной двери: пометьте её в doors полем "entry": true (или id "door-entry")')
    return doors[0]


def entry_start(plan):
    """Точка старта маршрутов: START_CM от середины входной двери в сторону открывания (внутрь)."""
    door = entry_door(plan)
    center_x, center_y = door_center(door)
    swing_x, swing_y = door["swing"]
    return center_x + swing_x * START_CM, center_y + swing_y * START_CM
