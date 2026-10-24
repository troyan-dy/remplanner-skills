"""Двери: ширина, угол открывания до мебели или стены, пересечение створок двух дверей и створки с проёмом."""

import math

from rpkit.layout_door_clash import door_clashes
from rpkit.layout_door_leaf import door_sector, leaf_doors, windoor_doors
from rpkit.layout_vectors import minus

OPEN_FROM = 5  # угол открывания проверяется от 5°
FULL_OPEN = 90
HINGE_JAMB_CM = 15  # у петли полотно уходит в откос — первые 15 см стены не считаются
ID = "id"


def _hits(layout, hinge, point):
    """Полотно в точке point упирается в препятствие (кроме стены у самой петли)."""
    if not layout.blocked(layout.masks.front, *point):
        return False
    if not layout.masks.wall[layout.grid.index(*point)]:
        return True
    return math.hypot(*minus(point, hinge)) >= HINGE_JAMB_CM


def _open_angle(layout, door):
    """Угол, на который полотно открывается до первого препятствия."""
    hinge = door["hinge"]
    for theta in range(OPEN_FROM, FULL_OPEN + 1):
        if any(_hits(layout, hinge, point) for point in door_sector(door, theta)):
            return theta - 1
    return FULL_OPEN


def _leaf_findings(layout):
    """door_width (кроме двери балконного блока: ширину проёма в несущей стене не выбирают) и door_open."""
    plan = layout.plan
    balcony = windoor_doors(plan)
    found = []
    for door in leaf_doors(plan):
        if door[ID] not in balcony:
            found.append(("door_width", door[ID], door["width"]))
        found.append(("door_open", door[ID], _open_angle(layout, door)))
    return found


def measure_doors(layout):
    """Находки по дверям: ширина и угол открывания, затем пересечения створок."""
    return _leaf_findings(layout) + door_clashes(layout)
