"""Сетка проверки эргономики: клетки STEP_CM по габариту плана (+ MARGIN_CM), номера клеток и их центры."""

import math

STEP_CM = 2
MARGIN_CM = 20  # запас сетки вокруг габарита плана, см: снаружи входной двери тоже есть клетки
RECT_KEYS = ("walls_bearing", "partitions", "insulation", "furniture", "windows", "zones", "rooms")
DOOR_BOX_DEPTH_CM = 30  # проём двери: поперёк стены ±30 см
# соседние клетки: (шаг по x, шаг по y, по диагонали ли)
NEIGHBOURS = (
    (1, 0, False),
    (-1, 0, False),
    (0, 1, False),
    (0, -1, False),
    (1, 1, True),
    (1, -1, True),
    (-1, 1, True),
    (-1, -1, True),
)


def door_box(door):
    """Проём двери: вдоль — от петли до края (без 1 см с концов), поперёк — ±30 см."""
    hinge, other = door["hinge"], door["other"]
    depth = 2 * DOOR_BOX_DEPTH_CM
    if hinge[1] == other[1]:
        return [
            min(hinge[0], other[0]) + 1,
            hinge[1] - DOOR_BOX_DEPTH_CM,
            abs(other[0] - hinge[0]) - 2,
            depth,
        ]
    return [
        hinge[0] - DOOR_BOX_DEPTH_CM,
        min(hinge[1], other[1]) + 1,
        depth,
        abs(other[1] - hinge[1]) - 2,
    ]


def _plan_rects(plan):
    rects = [
        element["rect"]
        for key in RECT_KEYS
        for element in plan.get(key, [])
        if element.get("rect")
    ]
    return rects + [door_box(door) for door in plan["doors"]]


def _floor_step(number):
    return math.floor(number / STEP_CM) * STEP_CM


def _ceil_step(number):
    return math.ceil(number / STEP_CM) * STEP_CM


def grid_for_plan(plan):
    """Сетка по габариту плана: все rect (стены, утепление, мебель, окна, зоны, комнаты) и проёмы дверей
    + MARGIN_CM, выровнено по STEP_CM."""
    rects = _plan_rects(plan)
    left, right = _extent(rects, 0)
    top, bottom = _extent(rects, 1)
    return Grid(
        (left, top),
        (right - left) // STEP_CM,
        (bottom - top) // STEP_CM,
    )


def _extent(rects, axis_index):
    """Начало и конец габарита по оси с запасом MARGIN_CM, по сетке STEP_CM."""
    low = min(rect[axis_index] for rect in rects)
    high = max(
        rect[axis_index] + rect[axis_index + 2] for rect in rects
    )
    return _floor_step(low - MARGIN_CM), _ceil_step(high + MARGIN_CM)


class Grid:
    """Сетка: начало (origin_x, origin_y) и число клеток по x (columns) и y (rows); клетка k = row * columns + column."""

    def __init__(self, origin, columns, rows):
        self.origin = origin
        self.columns = columns
        self.rows = rows

    def cells(self, rect):
        """Клетки (column, row), которые задевает rect, построчно."""
        columns = self._span(rect[0], rect[2], 0, self.columns)
        rows = self._span(rect[1], rect[3], 1, self.rows)
        return [(column, row) for row in rows for column in columns]

    def index(self, x_cm, y_cm):
        """Номер клетки точки или None вне сетки."""
        column = int((x_cm - self.origin[0]) // STEP_CM)
        row = int((y_cm - self.origin[1]) // STEP_CM)
        return self._cell(column, row)

    def center(self, cell):
        """Центр клетки."""
        column = cell % self.columns + 0.5
        row = cell // self.columns + 0.5
        x_cm = self.origin[0] + column * STEP_CM
        return x_cm, self.origin[1] + row * STEP_CM

    def neighbours(self, cell):
        """[(соседняя клетка, по диагонали ли)] в порядке NEIGHBOURS, только внутри сетки."""
        column = cell % self.columns
        row = cell // self.columns
        around = []
        for step in NEIGHBOURS:
            neighbour = self._cell(
                column + step[0],
                row + step[1],
            )
            if neighbour is not None:
                around.append((neighbour, step[2]))
        return around

    def _cell(self, column, row):
        """Номер клетки (column, row) или None вне сетки."""
        if 0 <= column < self.columns and 0 <= row < self.rows:
            return row * self.columns + column
        return None

    def _span(self, start, size, axis_index, limit):
        origin = self.origin[axis_index]
        first = max(0, int((start - origin) // STEP_CM))
        last = int(math.ceil((start + size - origin) / STEP_CM))
        return range(first, min(limit, last))
