"""Перегородки и утепление выгрузки: partitions и insulation → осевые линии, куски одной линии сливаются."""

import operator

from rpkit.export_pieces import MERGE_GAP_CM
from rpkit.export_segments import HORIZONTAL, seg_of_rect

NARROW_GAP_CM = 12  # узкий разрыв линии сливается, если поперечная стена в нём только заканчивается
_ORDER = operator.attrgetter("axis", "offset", "depth", "lo")  # куски одной линии подряд, по возрастанию
_LINE = operator.attrgetter("axis", "offset", "depth", "kind")  # одна линия одного вида


def partitions(plan, doors_rp, bearing, frame):
    """Куски одной линии сливаются, если разрыв — дверь (doors_rp — середины проёмов в координатах RemPlanner)
    или узкий (≤ NARROW_GAP_CM) и поперечная стена в нём только заканчивается."""
    segs = _segs(plan, frame)
    crossing = segs + bearing
    segs.sort(key=_ORDER)
    merged = []
    for seg in segs:
        last = merged[-1] if merged else None
        if last and _continues(last, seg, doors_rp, crossing):
            last.span = [last.lo, max(last.hi, seg.hi)]
        else:
            merged.append(seg)
    return merged


def _segs(plan, frame):
    insulation = [dict(wall, kind="insulation") for wall in plan.get("insulation", [])]
    return [
        seg_of_rect(frame.rect_rp(wall["rect"]), wall.get("kind", "partition"))
        for wall in plan["partitions"] + insulation
    ]


def _continues(last, seg, doors_rp, crossing):
    """seg продолжает last: та же линия, и разрыв между ними закрывается."""
    if _LINE(last) != _LINE(seg):
        return False
    return _gap_closes(last, seg, doors_rp, crossing)


def _gap_closes(last, seg, doors_rp, crossing):
    gap = seg.lo - last.hi
    if gap <= MERGE_GAP_CM and _door_in_gap(last, seg, doors_rp):
        return True
    if gap > NARROW_GAP_CM:
        return False
    return not _crossed(seg, (last.hi, seg.lo), crossing)


def _door_in_gap(last, seg, doors_rp):
    horizontal = seg.axis == HORIZONTAL
    for door_x, door_y in doors_rp:
        along, across = (door_x, door_y) if horizontal else (door_y, door_x)
        if not last.hi - 1 <= along <= seg.lo + 1:
            continue
        if abs(across - seg.offset) <= seg.depth:
            return True
    return False


def _crossed(seg, gap, crossing):
    """Проходит ли поперечная стена через разрыв gap насквозь — тогда это Х-стык, куски не сливать."""
    half = seg.depth / 2
    # толща линии seg с запасом 1 см
    band = (
        seg.offset - half - 1,
        seg.offset + half + 1,
    )
    across = [other for other in crossing if other.axis != seg.axis]
    window = (gap[0] - 1, gap[1] + 1)
    for other in across:
        if not window[0] <= other.offset <= window[1]:
            continue
        if other.lo < band[0] and other.hi > band[1]:
            return True
    return False
