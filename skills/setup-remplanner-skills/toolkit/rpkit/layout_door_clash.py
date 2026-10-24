"""Пересечения створок: створки двух дверей задевают одни клетки; створка заходит в проём без полотна."""

import itertools

from rpkit.layout_door_leaf import door_sector, is_doorway
from rpkit.layout_masks import flat_cells
from rpkit.layout_vectors import minus

FULL_OPEN = 90
SWEEP_STEP = 3  # створка для пересечений — через 3°
DOORWAY_DEPTH_CM = 5  # проём без полотна — полоса ±5 см по линии стены
CLASH = "door_clash"
ID = "id"


def _swept(layout, door):
    """Клетки, по которым проходит створка от 0 до 90°."""
    cells = {
        layout.grid.index(*point)
        for theta in range(0, FULL_OPEN + 1, SWEEP_STEP)
        for point in door_sector(door, theta)
    }
    cells.discard(None)
    return cells


def _doorway_hole(door):
    """Полоса проёма без полотна по линии стены: вдоль — от петли до края, поперёк — ±DOORWAY_DEPTH_CM."""
    hinge, other = door["hinge"], door["other"]
    axis = 0 if hinge[1] == other[1] else 1
    across = 1 - axis
    hole = [0, 0, 0, 0]
    hole[axis] = min(hinge[axis], other[axis])
    hole[axis + 2] = abs(minus(other, hinge)[axis])
    hole[across] = hinge[across] - DOORWAY_DEPTH_CM
    hole[across + 2] = 2 * DOORWAY_DEPTH_CM
    return hole


def _pair_clashes(swept):
    """Пары дверей, створки которых пересекаются."""
    return [
        (CLASH, f"{first} × {second}", 1)
        for first, second in itertools.combinations(swept, 2)
        if swept[first] & swept[second]
    ]


def _doorway_clashes(layout, swept, doorway):
    """Створки, которые заходят в проём без полотна doorway."""
    hole = set(flat_cells(layout.grid, _doorway_hole(doorway)))
    return [
        (CLASH, f"{door_id} × {doorway[ID]} (проём)", 1)
        for door_id, cells in swept.items()
        if cells & hole
    ]


def door_clashes(layout):
    """Створки двух дверей пересекаются; створка заходит в соседний проём без полотна (doorway)."""
    doors = layout.plan["doors"]
    swept = {
        door[ID]: _swept(layout, door)
        for door in doors
        if not is_doorway(door)
    }
    found = _pair_clashes(swept)
    for doorway in filter(is_doorway, doors):
        found.extend(_doorway_clashes(layout, swept, doorway))
    return found
