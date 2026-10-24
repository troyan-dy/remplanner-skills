"""Правила у входа: near_entry — нужный предмет у входной двери."""

from rpkit.rules_doors import rect_dist
from rpkit.rules_items import front, has

ITEM_PATTERNS = "items"
MIN_FRONT = "min_front"
MIN_DEPTH = "min_depth"
NO_ENTRY = 'нет входной двери ("entry": true или id door-entry)'


def _size(piece):
    width, depth = front(piece)
    return f"{width}×{depth}"


def _fits(piece, rule):
    width, depth = front(piece)
    return width >= rule[MIN_FRONT] and depth >= rule[MIN_DEPTH]


class _Entrance:
    """Поиск предметов правила near_entry у входной двери."""

    def __init__(self, ctx, rule, point):
        self.rule = rule
        self.point = point
        limit = rule["max_dist"]
        self.limit = ctx.cfg["entry_radius"] if limit is None else limit
        self.candidates = [
            piece for piece in ctx.furn
            if has(piece, rule[ITEM_PATTERNS])
            and not ctx.in_role(piece, rule["exclude_rooms"])
        ]
        self.sized = rule[MIN_FRONT] or rule[MIN_DEPTH]

    def near(self):
        """Кандидаты не дальше limit от середины входной двери."""
        return [piece for piece in self.candidates if rect_dist(piece, self.point) <= self.limit]

    def found(self, good):
        """Строка о ближайшем подходящем предмете."""
        chosen = min(good, key=lambda piece: rect_dist(piece, self.point))
        size = f" {_size(chosen)}" if self.sized else ""
        distance = rect_dist(chosen, self.point)
        return f"у входа {chosen['id']}{size} в {distance:.0f} см"

    def missing(self, near):
        """Строка о том, чего у входа нет."""
        rule = self.rule
        if self.sized:
            sizes = (f"{piece['id']} {_size(piece)}" for piece in near)
            have = ", ".join(sizes) or "нет"
            wanted = f"{rule[MIN_FRONT]}×{rule[MIN_DEPTH]}"
            return f"у входа (≤ {self.limit} см) нет {rule['what']} ≥ {wanted} (есть: {have})"
        return f"у входа (≤ {self.limit} см) нет {rule['what']}{self._nearest()}"

    def _nearest(self):
        """« (ближайший … в … см)» — ближайший кандидат за пределами limit, если он есть."""
        distances = (
            (rect_dist(piece, self.point), piece["id"]) for piece in self.candidates
        )
        nearest = min(distances, default=None)
        if not nearest:
            return ""
        return f" (ближайший {nearest[1]} в {nearest[0]:.0f} см)"


def near_entry(ctx, rule):
    """У входа (entry_radius или max_dist) есть предмет правила, при min_front/min_depth — не меньше них."""
    point = ctx.entry()
    if point is None:
        return [(False, NO_ENTRY)]
    entrance = _Entrance(ctx, rule, point)
    near = entrance.near()
    good = [piece for piece in near if _fits(piece, rule)]
    if good:
        return [(True, entrance.found(good))]
    return [(False, entrance.missing(near))]
