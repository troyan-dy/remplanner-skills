"""Сетка трасс канализации: клетки STEP_CM, которые задевает прямоугольник, и полоса под дверью."""

import math

STEP_CM = 5  # клетка трассы
ORIGIN_CM = 0  # привязка клеток трассы (кратно STEP_CM)
DOOR_BAND_CM = 15  # полоса под дверным проёмом поперёк стены, в каждую сторону
SEED_RADIUS_CM = 20  # трасса стартует со всех допустимых клеток в 20 см от точки подключения


def _cell_range(start, size):
    """Номера клеток, которые задевает отрезок [start, start + size]."""
    first = int((start - ORIGIN_CM) // STEP_CM)
    end = start + size - ORIGIN_CM
    return range(first, int(math.ceil(end / STEP_CM)))


def grid_cells(rect):
    """Клетки трассы, которые задевает прямоугольник."""
    x_cm, y_cm, width, height = rect
    rows = _cell_range(y_cm, height)
    return [(column, row) for column in _cell_range(x_cm, width) for row in rows]


def door_box(door):
    """Полоса под дверным проёмом: трасса под дверью не идёт."""
    hinge, other = door["hinge"], door["other"]
    band = 2 * DOOR_BAND_CM
    if hinge[1] == other[1]:
        return [
            min(hinge[0], other[0]),
            hinge[1] - DOOR_BAND_CM,
            abs(other[0] - hinge[0]),
            band,
        ]
    return [
        hinge[0] - DOOR_BAND_CM,
        min(hinge[1], other[1]),
        band,
        abs(other[1] - hinge[1]),
    ]


def seed_cells(cells, point):
    """Допустимые клетки в SEED_RADIUS_CM от точки подключения."""
    left = point[0] - SEED_RADIUS_CM
    top = point[1] - SEED_RADIUS_CM
    around = grid_cells([left, top, 2 * SEED_RADIUS_CM, 2 * SEED_RADIUS_CM])
    return [cell for cell in around if cell in cells]
