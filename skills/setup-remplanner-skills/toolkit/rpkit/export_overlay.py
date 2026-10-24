"""Тонкие накладки на грани несущей стены (уступ отделки, граница помещения): отдельной стеной не строятся."""

from rpkit.intervals import EPS, side

THIN_CM = 10  # несущий кусок тоньше этого вплотную к грани параллельной несущей стены — накладка, не стена


def is_overlay(rect, others):
    """Тонкий (< THIN_CM) кусок вплотную к длинной грани более толстой параллельной стены и в её пределах."""
    thickness = min(rect[2], rect[3])
    if thickness >= THIN_CM:
        return False
    return any(_lies_on(rect, other, thickness) for other in others)


def _lies_on(rect, other, thickness):
    if min(other[2], other[3]) <= thickness:
        return False
    # обе горизонтальные (ширина ≥ высоты) или обе вертикальные (высота > ширины)
    if _wide(rect) and _wide(other) and _touches(rect, other, 1):
        return True
    if _tall(rect) and _tall(other):
        return _touches(rect, other, 0)
    return False


def _wide(rect):
    return rect[2] >= rect[3]


def _tall(rect):
    return rect[3] > rect[2]


def _touches(rect, other, cross):
    """rect прилегает к грани other поперёк оси cross и не выходит за other вдоль неё."""
    span = side(rect, cross)
    other_span = side(other, cross)
    near_end = abs(span.low - other_span.high) <= EPS
    if not near_end and abs(span.high - other_span.low) > EPS:
        return False
    along = 1 - cross
    return side(other, along).covers(side(rect, along), EPS)
