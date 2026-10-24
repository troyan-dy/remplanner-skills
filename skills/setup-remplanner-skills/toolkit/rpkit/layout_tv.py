"""ТВ напротив дивана или кровати: дистанция от глаз в диагоналях экрана и угол в сторону от оси сидящего."""

from rpkit.layout_kinds import kind
from rpkit.layout_roles import is_tv
from rpkit.layout_seat_view import seat_view

SCREEN_RATIO = 0.8716  # ширина экрана 16:9 в диагоналях


def _nearest_seat(layout, center):
    """Ближайшее место, с которого видно ТВ: (расстояние, угол, id) или None."""
    best = None
    for seat in layout.plan["furniture"]:
        seen = seat_view(layout, center, seat)
        if seen and (best is None or seen[0] < best[0]):
            best = seen
    return best


def _tv_findings(layout, tv):
    rect = tv["rect"]
    diagonal = max(rect[2], rect[3]) / SCREEN_RATIO
    center = (
        rect[0] + rect[2] / 2,
        rect[1] + rect[3] / 2,
    )
    best = _nearest_seat(layout, center)
    if not best:
        return []
    label = f"{tv['id']} ← {best[2]}"
    return [
        ("tv_distance", label, round(best[0] / diagonal, 2)),
        ("tv_angle", label, round(best[1])),
    ]


def measure_tv(layout):
    """ТВ напротив дивана/кровати: дистанция в диагоналях и угол от оси (ближайшее место)."""
    found = []
    for tv in layout.plan["furniture"]:
        if is_tv(kind(tv)):
            found.extend(_tv_findings(layout, tv))
    return found
