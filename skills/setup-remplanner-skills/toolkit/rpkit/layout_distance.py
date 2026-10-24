"""Поле расстояний на сетке: до ближайшего препятствия, фаска 2-3 (≈ евклидово)."""

from rpkit.layout_grid import STEP_CM

INF = 10**9
STRAIGHT = 2  # фаска 2-3: шаг вдоль оси, ×STEP_CM/2 → см
DIAGONAL = 3  # и по диагонали


class _Chamfer:
    """Два прохода фаски 2-3 по сетке: вперёд (слева сверху) и назад (справа снизу)."""

    def __init__(self, obstacles, grid):
        self.columns = grid.columns
        self.rows = grid.rows
        self.dist = [
            0 if obstacles[cell] else INF for cell in range(grid.columns * grid.rows)
        ]

    def forward(self):
        """Проход сверху вниз, слева направо."""
        for row in range(self.rows):
            for column in range(self.columns):
                self._relax(row, column, -1)

    def backward(self):
        """Проход снизу вверх, справа налево."""
        for row in range(self.rows - 1, -1, -1):
            for column in range(self.columns - 1, -1, -1):
                self._relax(row, column, 1)

    def _relax(self, row, column, sign):
        """Клетка через уже пройденных соседей: sign −1 — слева и сверху, 1 — справа и снизу."""
        dist = self.dist
        cell = row * self.columns + column
        if dist[cell] == 0:
            return
        best = dist[cell]
        if 0 <= column + sign < self.columns:
            best = min(best, dist[cell + sign] + STRAIGHT)
        if 0 <= row + sign < self.rows:
            above = cell + sign * self.columns
            best = min(best, dist[above] + STRAIGHT)
            if 0 <= column + sign < self.columns:
                best = min(best, dist[above + sign] + DIAGONAL)
            if 0 <= column - sign < self.columns:
                best = min(best, dist[above - sign] + DIAGONAL)
        dist[cell] = best


def distance(obstacles, grid):
    """Расстояние до препятствия, фаска 2-3 (≈ евклидово), в см."""
    chamfer = _Chamfer(obstacles, grid)
    chamfer.forward()
    chamfer.backward()
    return [_centimeters(steps) for steps in chamfer.dist]


def _centimeters(steps):
    """Шаги фаски → см (INF — препятствий нет)."""
    if steps < INF:
        return steps * STEP_CM / STRAIGHT
    return INF
