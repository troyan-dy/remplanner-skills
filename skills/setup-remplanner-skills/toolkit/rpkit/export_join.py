"""Стыки стен как в файлах, сохранённых самим RemPlanner (tools/reference/remplanner_example_v3_catalog.plan)."""

JOIN_PASSES = 3


def join(segs, only=None):
    """only — стыковать только эти стены, остальные не двигать (утепление);
    угол — концы двух стен в общей точке на пересечении осей (link node);
    Т-примыкание — конец стены на грани проходящей стены (link edge), проходящая стена не делится."""
    for _ in range(JOIN_PASSES):
        for seg in segs if only is None else only:
            for end in (0, 1):
                _join_end(seg, end, segs, only)


def _join_end(seg, end, segs, only):
    position = seg.span[end]
    other_position = seg.span[1 - end]
    target = _nearest_crossing(seg, position, segs)
    if target is None:
        return
    target_end = _shared_end(target, seg)
    if target_end is not None and (only is None or target in only):
        # угол: обе стены сходятся в узел на осях
        seg.span[end] = target.offset
        target.span[target_end] = seg.offset
    elif other_position < target.offset:  # Т: упираемся в ближнюю грань
        seg.span[end] = target.offset - target.depth / 2
    else:
        seg.span[end] = target.offset + target.depth / 2


def _nearest_crossing(seg, position, segs):
    """Ближайшая поперечная стена, до оси которой конец seg (position) достаёт."""
    best = None
    for other in segs:
        dist = _reach(seg, position, other)
        if dist is not None and (best is None or dist < best[0]):
            best = (dist, other)
    return best[1] if best else None


def _reach(seg, position, other):
    """Расстояние от конца seg до оси поперечной стены other или None, если other не годится."""
    if other is seg or other.axis == seg.axis:
        return None
    if not _spans_line(other, seg):
        return None
    dist = abs(position - other.offset)
    limit = other.depth / 2 + seg.depth / 2
    if dist <= limit + 1:
        return dist
    return None


def _spans_line(other, seg):
    """Линия seg проходит в пределах other (с запасом в полтолщины seg и 1 см)."""
    low = other.lo - seg.depth / 2
    high = other.hi + seg.depth / 2
    return low - 1 <= seg.offset <= high + 1


def _shared_end(target, seg):
    """Конец target (0 или 1), который лежит на линии seg, или None."""
    limit = max(target.depth, seg.depth) / 2 + 1
    for index in (0, 1):
        if abs(target.span[index] - seg.offset) <= limit:
            return index
    return None
