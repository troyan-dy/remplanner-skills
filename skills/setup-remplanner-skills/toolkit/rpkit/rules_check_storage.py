"""Правило о хранении: шкаф в комнате с кроватью."""

from rpkit.rules_items import front, has, inside

ITEM_PATTERNS = "items"


def _beds_in(ctx, room, beds):
    bed_pieces = (piece for piece in ctx.furn if has(piece, beds))
    return any(inside(piece, room) for piece in bed_pieces)


def _storage_line(room, wardrobes, rule):
    """(ok, сообщение) о шкафах комнаты с кроватью."""
    total = sum(front(piece)[0] for piece in wardrobes)
    if not wardrobes:
        return False, f"в комнате {room['id']} с кроватью нет шкафа"
    if total < rule["min_front"]:
        need = rule["min_front"]
        return False, f"в комнате {room['id']} с кроватью шкафы {total} по фасаду (нужно ≥ {need})"
    names = ", ".join(piece["id"] for piece in wardrobes)
    return True, f"{room['id']} — шкафы {total} по фасаду: {names}"


def _wardrobes(ctx, rule, places):
    """Шкафы правила в одной из комнат places."""
    return [
        piece for piece in ctx.furn
        if has(piece, rule[ITEM_PATTERNS])
        and any(inside(piece, place) for place in places)
    ]


def bedroom_storage(ctx, rule):
    """В каждой комнате с кроватью (или в extra_rooms) есть шкафы, суммарно по фасаду не меньше min_front."""
    extra = ctx.role(rule["extra_rooms"]) if rule["extra_rooms"] else []
    found = []
    for room in ctx.rooms:
        if not _beds_in(ctx, room, rule["beds"]):
            continue
        wardrobes = _wardrobes(ctx, rule, [room] + extra)
        found.append(_storage_line(room, wardrobes, rule))
    return found or [(True, "комнат с кроватью (с rect) нет — не проверено")]
