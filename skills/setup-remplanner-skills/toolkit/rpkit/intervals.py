"""Отрезок на оси: стороны прямоугольника, разрывы между кусками стен."""

from typing import NamedTuple

EPS = 1e-6


class Interval(NamedTuple):
    """Отрезок [low, high] на оси."""

    low: float
    high: float

    def length(self):
        """high − low (у разрыва между перекрывающимися кусками — ≤ 0)."""
        return self.high - self.low

    def matches(self, other):
        """Концы совпадают с точностью EPS."""
        if abs(self.low - other.low) > EPS:
            return False
        return abs(self.high - other.high) <= EPS

    def holds(self, number, margin):
        """number внутри отрезка с запасом margin с обеих сторон."""
        return self.low - margin <= number <= self.high + margin

    def covers(self, inner, margin):
        """inner целиком внутри отрезка (с запасом margin)."""
        if self.low - margin > inner.low:
            return False
        return inner.high <= self.high + margin


def side(rect, axis_index):
    """Сторона прямоугольника [x, y, w, h] по оси 0 — x, 1 — y."""
    start = rect[axis_index]
    return Interval(start, start + rect[axis_index + 2])


def gap_between(first, second):
    """Разрыв между двумя отрезками одной линии: от конца одного до начала другого (≤ 0 — перекрываются)."""
    end = min(first.high, second.high)
    start = max(first.low, second.low)
    return Interval(end, start)


def hull(first, second):
    """Отрезок, покрывающий оба."""
    low = min(first.low, second.low)
    high = max(first.high, second.high)
    return Interval(low, high)
