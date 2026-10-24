"""Правила об окнах: окно не заложено (window_full), перед окном нет высокой мебели (window_clear)."""

import math

from rpkit.catalog_store import catalog_info
from rpkit.rules_items import specs

TALL_UNKNOWN_CM = 200  # высота 0 в каталоге — не задана: напольный предмет считаем высоким
HUNG_UNKNOWN_CM = 5  # а навесной — тонким
WINDOW = "window"
RECT = "rect"
MAX_HEIGHT = "max_height"


def find_window(ctx, window_id):
    """Окно плана по id или None."""
    windows = ctx.plan.get("windows", [])
    return next((opening for opening in windows if opening["id"] == window_id), None)


def _absent(rule):
    return [(True, f"окна {rule[WINDOW]} в плане нет — не проверено")]


def window_full(ctx, rule):
    """Окно не короче min_length, иначе нужно обоснование waiver в плане."""
    opening = find_window(ctx, rule[WINDOW])
    if opening is None:
        return _absent(rule)
    length = max(opening[RECT][2], opening[RECT][3])
    waived = rule["waiver"] and ctx.plan.get(rule["waiver"])
    measured = f"{length} из {rule['min_length']}"
    if length < rule["min_length"] and not waived:
        return [(False, f"окно {rule[WINDOW]} заложено ({measured}) без обоснования {rule['waiver']}")]
    return [(True, f"окно {rule[WINDOW]} {measured}")]


def _axis_gap(window_rect, rect, axis_index):
    window_start, start = window_rect[axis_index], rect[axis_index]
    before = window_start - (start + rect[axis_index + 2])
    return max(before, start - (window_start + window_rect[axis_index + 2]), 0)


def _blocking_top(piece, rule):
    """Высота первого rp предмета, который выше max_height и стоит ниже него (по каталогу), иначе None."""
    for spec_rp in specs(piece):
        found = catalog_info(spec_rp["name"])
        bottom = (found.get("over_floor") or {}).get("value") or 0
        unknown = HUNG_UNKNOWN_CM if bottom else TALL_UNKNOWN_CM
        top = bottom + (found.get("self_height") or unknown)
        if top > rule[MAX_HEIGHT] and bottom < rule[MAX_HEIGHT]:
            return top
    return None


def window_clear(ctx, rule):
    """Перед окном (ближе gap) нет мебели, которая выше max_height и стоит ниже него."""
    opening = find_window(ctx, rule[WINDOW])
    if opening is None:
        return _absent(rule)
    found = []
    for piece in ctx.furn:
        if not _near_window(opening, piece, rule):
            continue
        top = _blocking_top(piece, rule)
        if top is not None:
            where = f"перед окном {rule[WINDOW]} (ближе {rule['gap']} см)"
            found.append((False, f"{piece['id']} (высота {top}) стоит {where}"))
    return found or [(True, f"перед окном {rule[WINDOW]} высокой мебели нет")]


def _near_window(opening, piece, rule):
    """Предмет ближе gap к окну."""
    gap_x = _axis_gap(opening[RECT], piece[RECT], 0)
    gap_y = _axis_gap(opening[RECT], piece[RECT], 1)
    return math.hypot(gap_x, gap_y) < rule["gap"]
