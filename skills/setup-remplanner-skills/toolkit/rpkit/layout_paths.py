"""Пути по сетке от клетки: самый широкий (bottleneck по полю расстояний) и кратчайший с минимальной шириной."""

import heapq
import itertools
import math

DIAGONAL_STEP = 1.414  # длина диагонального шага кратчайшего пути, клеток


class _Search:
    """Поиск путей по сетке от клетки: значение и родитель для каждой клетки, очередь с приоритетом."""

    def __init__(self, grid, field, initial):
        self.grid = grid
        self.field = field
        size = grid.columns * grid.rows
        self.marks = list(itertools.repeat(initial, size))
        self.parent = list(itertools.repeat(-1, size))
        self.heap = []

    def push(self, cell, mark, key):
        """Новое значение клетки и её место в очереди (key — приоритет)."""
        self.marks[cell] = mark
        heapq.heappush(self.heap, (key, cell))

    def tables(self):
        """(значения, родители)."""
        return self.marks, self.parent


def widest(field, grid, start):
    """Для каждой клетки — максимальная по путям минимальная field (bottleneck) от клетки start
    и родитель на таком пути."""
    search = _Search(grid, field, -1.0)
    search.push(start, field[start], -field[start])
    while search.heap:
        neck, cell = heapq.heappop(search.heap)
        neck = -neck
        if neck >= search.marks[cell]:
            _widen(search, cell, neck)
    return search.tables()


def _widen(search, cell, neck):
    for neighbour, _ in search.grid.neighbours(cell):
        narrowest = min(neck, search.field[neighbour])
        if narrowest > search.marks[neighbour]:
            search.parent[neighbour] = cell
            search.push(neighbour, narrowest, -narrowest)


def shortest(field, grid, start, radius):
    """Кратчайшие пути от start по клеткам с field ≥ radius (центр человека с плечами 2·radius):
    длины и родители."""
    search = _Search(grid, field, math.inf)
    search.push(start, float(0), float(0))
    while search.heap:
        length, cell = heapq.heappop(search.heap)
        if length <= search.marks[cell]:
            _extend(search, cell, length, radius)
    return search.tables()


def _extend(search, cell, length, radius):
    for neighbour, diagonal in search.grid.neighbours(cell):
        if search.field[neighbour] < radius:
            continue
        step = DIAGONAL_STEP if diagonal else 1
        candidate = length + step
        if candidate < search.marks[neighbour]:
            search.parent[neighbour] = cell
            search.push(neighbour, candidate, candidate)
