"""Зоны перед предметами: свободная глубина от лицевой грани (кровать — бока и изножье), для унитаза
и раковины — ещё от оси до боковых препятствий, для обеденного стола — за стульями."""

from rpkit.layout_bed import bed_fronts_found
from rpkit.layout_dining import dining_backs
from rpkit.layout_fixtures import fixture_sides
from rpkit.layout_front_rule import SHELF, WARD, WARD_HINGED, front_rule
from rpkit.layout_kinds import FRONT, kind, specs
from rpkit.layout_roles import bed_fronts, is_dining
from rpkit.layout_sweep import sweep

STORAGE = (WARD, WARD_HINGED, SHELF)  # шкафы и стеллажи стыкуются углом друг с другом без помехи
FIXTURES = ("wc_front", "sink_front")
FACE_CM = (10, 10)
RECT = "rect"


def _rule_of(piece):
    attached = specs(piece)
    return front_rule(kind(piece), attached[0] if attached else None)


def _groups(furniture):
    """{правило: индексы мебели} — стык углом с соседом той же группы (шкафы и стеллажи — одна) не помеха."""
    groups = {}
    for index, piece in enumerate(furniture):
        groups.setdefault(_rule_of(piece), set()).add(index)
    storage = set()
    for rule in STORAGE:
        storage |= groups.get(rule, set())
    for rule in STORAGE:
        groups[rule] = storage
    return groups


def _piece_fronts(layout, piece, groups):
    spec_rp = specs(piece)[0]
    name = spec_rp["name"]
    face = FRONT[spec_rp["back"]]
    if bed_fronts(name):
        return bed_fronts_found(layout, piece, face)
    rule = front_rule(name, spec_rp)
    found = _front(layout, piece, face, rule, groups)
    if rule in FIXTURES and "double" not in name:  # у двойной раковины оси две
        found.extend(fixture_sides(layout, piece, rule, face))
    if is_dining(name):
        found.extend(dining_backs(layout, piece))
    return found


def _front(layout, piece, face, rule, groups):
    """Свободная глубина перед лицевой гранью (если у предмета есть правило зоны)."""
    if not rule:
        return []
    joint = groups.get(rule, ())
    depth = sweep(layout, piece[RECT], face, FACE_CM, joint)
    return [(rule, piece["id"], depth)]


def measure_fronts(layout):
    """Зоны перед предметами."""
    furniture = layout.plan["furniture"]
    groups = _groups(furniture)
    found = []
    for piece in furniture:
        if specs(piece):
            found.extend(_piece_fronts(layout, piece, groups))
    return found
