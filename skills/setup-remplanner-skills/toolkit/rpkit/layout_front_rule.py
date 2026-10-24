"""Правило зоны перед предметом: по имени каталога (явные наборы), затем по роли и разделу меню."""

import re

from rpkit.layout_kinds import is_sink, is_tall_kitchen, is_toilet, over_floor
from rpkit.layout_menu import M_DRAWER, M_HINGED, M_OPEN_WARD, M_SHELF, M_STOVE, in_menu
from rpkit.layout_obstacles import HUNG_CM
from rpkit.layout_roles import is_desk, is_sofa

WARD_HINGED = "ward_hinged_front"
WARD = "ward_front"
DRAWER = "drawer_front"
SHELF = "shelf_front"
# шкафы с распашными дверями (купе, гармошка, открытые — ward_front)
HINGED = frozenset((
    "ward_single",
    "ward",
    "threedoor_ward",
    "ward_double",
    "pencil_cabinet_above_washing",
    "floor_pencil_cabinet",
    "cupboard_with_drawers",
    "corner_cabinet",
    "double_leaf_corner_section",
    "single_leaf_corner_section",
))
DRAWERS = frozenset(("commode", "shoes_closet", "low_cabinet_sideboard", "chest_for_sink"))
SHELVES = frozenset(("bookshelf", "stillage_floor_book"))
WASHERS = re.compile("^(washing_machine(_top|_mini)?|dryer|dryer_over_washing)$")
NOT_DRAWER = re.compile("bedside|tele_stand|tv_table")  # прикроватные тумбы — у бока кровати, его проверяет bed_side


def _kitchen(name):
    if name in ("kitchen_run", "stove") or is_tall_kitchen(name):
        return True
    return in_menu(name, M_STOVE)


# по имени и роли — по порядку, первое подходящее
BY_NAME = (
    (lambda name: name in HINGED, WARD_HINGED),
    (lambda name: "ward" in name, WARD),
    (lambda name: name in DRAWERS, DRAWER),
    (lambda name: name in SHELVES, SHELF),
    (_kitchen, "kitchen_front"),
    (lambda name: WASHERS.search(name) is not None, "washer_front"),
    (is_toilet, "wc_front"),
    (is_sink, "sink_front"),
    (is_sofa, "sofa_front"),
    (is_desk, "desk_back"),
)
# по разделу меню — для того, что не навесное
BY_MENU = (
    (lambda name: in_menu(name, M_HINGED) and "open" not in name, WARD_HINGED),
    (lambda name: in_menu(name, M_OPEN_WARD) or in_menu(name, M_HINGED), WARD),
    (lambda name: in_menu(name, M_DRAWER) and not NOT_DRAWER.search(name), DRAWER),
    (lambda name: in_menu(name, M_SHELF), SHELF),
)


def _first(rules, name):
    return next((rule for matches, rule in rules if matches(name)), None)


def front_rule(name, spec_rp=None):
    """Правило зоны перед предметом name; spec_rp — объект rp: навесное (низ ≥ 100 см) зоны перед собой
    не требует."""
    if not name:
        return None
    rule = _first(BY_NAME, name)
    if rule is not None:
        return rule
    if over_floor(spec_rp or {"name": name}) >= HUNG_CM:
        return None
    return _first(BY_MENU, name)
