"""Предмет мебели .plan (rp_lib.item): параметры из CATALOG или каталога, габарит, угол и поправка значка."""

import copy
import math

from rpkit.catalog_checked import PC_SHIFT
from rpkit.catalog_names import spec
from rpkit.catalog_store import catalog_info
from rpkit.rp_geometry import pt
from rpkit.rp_ids import uid

OVER_FLOOR = "over_floor"
SPEC_ONLY = frozenset(("item_id", "plan", "self_height", "size"))  # поля spec, которые не копируются как есть


# имена и порядок параметров — публичный API rp_lib.item(name, cx, cy[, w, h]) (tools/blocks.py, документация)
def make_item(name, cx, cy, width=None, height=None, angle=0, **over):  # noqa: WPS211
    """width/height — габарит в плане при angle 0; None — размер по умолчанию из полного каталога.
    (cx, cy) — центр габарита; для моделей из PC_SHIFT pc сдвигается от спинки, значок остаётся в габарите."""
    fields = spec(name)
    if width is None or height is None:
        width, height = _default_size(name, width, height)
    record = {
        "name": name,
        "pc": _icon_anchor(name, (cx, cy), angle),
        "angle": angle,
        "width": width,
        "height": height,
        "plan": copy.deepcopy(fields["plan"]),
        "id": uid(),
        "item_id": fields["item_id"],
        "self_height": fields["self_height"],
        "comment": {"id": ""},
        "dimensions": {"display": True},
        "f0offset": 0,
        "dls": {"l": {}, "r": {}},
        "dls_prs": {"v": {}, "h": {}},
        "icon_center": pt(cx, cy),
        "center3d": pt(cx, cy),
    }
    _copy_extra(record, fields)
    _apply_over(record, over)
    return record


def _copy_extra(record, fields):
    """Доп. поля spec (over_floor, on_show_decoration…) — копиями."""
    for key, field in fields.items():
        if key not in SPEC_ONLY:
            record[key] = copy.deepcopy(field)


def _apply_over(record, over):
    """Поля rp из плана поверх: over_floor — числом (низ над полом, см), прочие — как есть."""
    for key, field in over.items():
        record[key] = {"value": field, "display": False} if key == OVER_FLOOR else field


def _default_size(name, width, height):
    """Габарит по умолчанию из каталога там, где он не задан."""
    found = catalog_info(name)
    if not found:
        spec(name)  # SystemExit: сведений о предмете нет
    return width or found["width"], height or found["height"]


def _icon_anchor(name, center, angle):
    """pc предмета: центр габарита, у моделей из PC_SHIFT — со сдвигом от спинки."""
    shift = PC_SHIFT.get(name, 0)
    turn = math.radians(angle)
    # спинка при angle θ — направление (−sin θ, cos θ)
    x_cm = center[0] + shift * math.sin(turn)
    y_cm = center[1] - shift * math.cos(turn)
    return pt(x_cm, y_cm)
