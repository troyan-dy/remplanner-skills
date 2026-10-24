"""Правило room_has: в комнате роли (или в плане) есть нужные предметы, при sizes — не меньше размеров."""

import itertools

from rpkit.rules_items import has, inside

ITEM_PATTERNS = "items"
ROOMS = "rooms"
LIST_SEP = ", "


def _first_role_rooms(ctx, roles):
    """Комнаты первой роли, у которой они есть."""
    for role in roles:
        rooms = ctx.role(role)
        if rooms:
            return rooms
    return []


def _target_rooms(ctx, rule):
    """(комнаты для проверки, итог, если проверять нечего); без rooms — весь план ([None])."""
    if not rule[ROOMS]:
        return [None], None
    roles = rule[ROOMS]
    if isinstance(roles, str):
        roles = [roles]
    rooms = _first_role_rooms(ctx, roles)
    if rooms:
        return rooms, None
    names = " или ".join(f"{prefix}*" for prefix in ctx.prefixes(roles))
    message = f"нет комнаты {names} с rect"
    if rule["required"]:
        return [], (False, message)
    return [], (True, f"{message} — не проверено")


def _fits(dims, sizes):
    """Какой-то из предметов (dims — их стороны по возрастанию) не меньше какого-то из размеров sizes."""
    wanted = [sorted(size) for size in sizes]
    return any(
        side >= small and other >= big
        for side, other in dims
        for small, big in wanted
    )


def _sized_missing(label, found, sizes):
    """Подпись пункта с размерами найденных предметов, если ни один не дотягивает до sizes, иначе None."""
    dims = [sorted(piece["rect"][2:]) for piece in found]
    if _fits(dims, sizes):
        return None
    sizes_found = (f"{side}×{other}" for side, other in dims)
    have = LIST_SEP.join(sizes_found) or "нет"
    return f"{label} (есть: {have})"


class _Presence:
    """Есть ли пункты правила в комнате (None — во всём плане)."""

    def __init__(self, ctx, room):
        self.ctx = ctx
        self.room = room

    def missing(self, label, wanted):
        """Чего нет по пункту label: подпись (с размерами, если заданы sizes) или None — всё есть."""
        if not isinstance(wanted, dict):
            wanted = {ITEM_PATTERNS: wanted}
        found = self._found(wanted)
        if not wanted.get("sizes"):
            return None if found else label
        return _sized_missing(label, found, wanted["sizes"])

    def _found(self, wanted):
        modules = wanted.get("modules", False)
        return [
            piece for piece in self.ctx.furn
            if has(piece, wanted[ITEM_PATTERNS], modules) and self._in_room(piece)
        ]

    def _in_room(self, piece):
        return self.room is None or inside(piece, self.room)


def _room_line(ctx, rule, room):
    """(ok, сообщение) о пунктах правила в комнате room."""
    presence = _Presence(ctx, room)
    misses = itertools.starmap(presence.missing, rule[ITEM_PATTERNS].items())
    missing = [miss for miss in misses if miss is not None]
    where = f"в {room['id']}" if room else "в плане"
    if missing:
        return False, f"{where} нет: {LIST_SEP.join(missing)}"
    return True, f"{where} есть: {LIST_SEP.join(rule[ITEM_PATTERNS])}"


def room_has(ctx, rule):
    """В каждой комнате первой роли с комнатами (или в плане) есть все пункты items."""
    rooms, verdict = _target_rooms(ctx, rule)
    if verdict is not None:
        return [verdict]
    return [_room_line(ctx, rule, room) for room in rooms]
