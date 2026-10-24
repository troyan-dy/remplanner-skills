"""Правило min_size: предмет не уже min_width (по фасаду или по длинной стороне)."""

from rpkit.rules_items import front, has

ITEM_PATTERNS = "items"
NOTHING = "подходящих предметов нет — не проверено"


def _front_width(piece):
    return front(piece)[0]


def _long_side(piece):
    width, height = piece["rect"][2:]
    return max(width, height)


def _each(pieces, size, limit):
    found = []
    for piece in pieces:
        measured = size(piece)
        tail = "" if measured >= limit else f" (нужно ≥ {limit})"
        found.append((measured >= limit, f"{piece['id']} шириной {measured}{tail}"))
    return found or [(True, NOTHING)]


def _any(rule, pieces, size):
    limit = rule["min_width"]
    good = [piece for piece in pieces if size(piece) >= limit]
    if good:
        first = good[0]
        return [(True, f"{first['id']} шириной {size(first)}")]
    sizes = (f"{piece['id']} {size(piece)}" for piece in pieces)
    have = ", ".join(sizes) or "нет"
    return [(False, f"нет {rule['what']} шириной ≥ {limit} (есть: {have})")]


def min_size(ctx, rule):
    """need each — каждый предмет правила не уже min_width; any — есть хотя бы один такой."""
    pieces = [
        piece for piece in ctx.furn
        if has(piece, rule[ITEM_PATTERNS])
        and not ctx.in_role(piece, rule["exclude_rooms"])
    ]
    size = _front_width if rule["measure"] == "front" else _long_side
    if rule["need"] == "each":
        return _each(pieces, size, rule["min_width"])
    return _any(rule, pieces, size)
