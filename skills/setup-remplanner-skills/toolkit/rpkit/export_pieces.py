"""Куски несущих стен из walls_bearing: слияние кусков одной стены, разделённых проёмом."""

import itertools

from rpkit.intervals import EPS, gap_between, hull, side

MERGE_GAP_CM = 130  # максимальный разрыв между кусками одной стены, который считается дверным проёмом


def merge_pieces(first, second, openings):
    """Два куска одной стены → общий прямоугольник или None. Куски — на одной линии с одинаковым
    поперечным сечением; соприкасаются или разделены разрывом ≤ MERGE_GAP_CM, в котором стоит дверь или окно."""
    for cross in (0, 1):  # 0 — общий диапазон x (куски друг над другом), 1 — общий диапазон y
        merged = _merge_across(first, second, openings, cross)
        if merged is not None:
            return merged
    return None


def _merge_across(first, second, openings, cross):
    section = side(first, cross)
    if not section.matches(side(second, cross)):
        return None
    along = 1 - cross
    pieces = (side(first, along), side(second, along))
    gap = gap_between(*pieces)
    if gap.length() > EPS and not _opening_in_gap(section, gap, openings, cross):
        return None
    joined = hull(*pieces)
    if cross == 0:
        return [section.low, joined.low, section.length(), joined.length()]
    return [joined.low, section.low, joined.length(), section.length()]


def _opening_in_gap(section, gap, openings, cross):
    """Разрыв не шире MERGE_GAP_CM и в нём середина двери или окна."""
    if gap.length() > MERGE_GAP_CM:
        return False
    return any(
        _opening_between(section, gap, opening, cross) for opening in openings
    )


def _opening_between(section, gap, opening, cross):
    if not section.holds(opening[cross], 1):
        return False
    return gap.holds(opening[1 - cross], 1)


def merge_all(pieces, openings):
    """Сливать по паре кусков одного kind, пока сливается."""
    merged = _first_merge(pieces, openings)
    while merged is not None:
        first, second, rect = merged
        pieces[first][0] = rect
        pieces.pop(second)
        merged = _first_merge(pieces, openings)


def _first_merge(pieces, openings):
    for first, second in itertools.combinations(range(len(pieces)), 2):
        rect = _merge_pair(pieces[first], pieces[second], openings)
        if rect:
            return first, second, rect
    return None


def _merge_pair(first, second, openings):
    if first[1] != second[1]:
        return None
    return merge_pieces(first[0], second[0], openings)
