"""Правила о месте предметов: в комнатах роли (items_in_rooms), за дверью (behind_door)."""

from rpkit.rules_doors import door_on
from rpkit.rules_items import has, inside

ITEM_PATTERNS = "items"
NOTHING = "подходящих предметов нет — не проверено"


def items_in_rooms(ctx, rule):
    """Каждый предмет правила — в комнате одной из ролей rooms."""
    found = [
        _room_line(ctx, rule, piece) for piece in ctx.furn if has(piece, rule[ITEM_PATTERNS])
    ]
    return found or [(True, NOTHING)]


def _room_line(ctx, rule, piece):
    """(ok, сообщение) о предмете правила items_in_rooms."""
    if ctx.in_role(piece, rule["rooms"]):
        return True, f"{piece['id']} на месте"
    prefixes = ctx.prefixes(rule["rooms"])
    where = "/".join(f"{prefix}*" for prefix in prefixes)
    return False, f"{piece['id']} не в комнатах {where}"


def _has_door(ctx, room):
    """У комнаты есть дверь с полотном (не проём doorway)."""
    return any(
        door_on(door, room) and door.get("kind", "single") != "doorway"
        for door in ctx.plan["doors"]
    )


def _door_line(ctx, rule, piece):
    """(ok, сообщение) о предмете правила behind_door."""
    rooms = (candidate for candidate in ctx.rooms if inside(piece, candidate))
    room = next(rooms, None)
    if room is None:
        return False, f"{piece['id']} не в комнате с rect — не проверить дверь"
    forbidden = rule["forbid_rooms"]
    if forbidden and room["id"].startswith(ctx.prefixes(forbidden)):
        return False, f"{piece['id']} в комнате {room['id']} — здесь его быть не должно"
    if rule["need_door"] and not _has_door(ctx, room):
        return False, f"у комнаты {room['id']} с {piece['id']} нет двери"
    tail = " с дверью" if rule["need_door"] else ""
    return True, f"{piece['id']} — {room['id']}{tail}"


def behind_door(ctx, rule):
    """Предмет правила — в комнате с дверью (need_door) и не в комнатах forbid_rooms."""
    found = [
        _door_line(ctx, rule, piece) for piece in ctx.furn if has(piece, rule[ITEM_PATTERNS])
    ]
    return found or [(True, NOTHING)]
