"""План и настройки rules.json для проверки правил: комнаты по ролям, вход."""

from rpkit.rules_doors import door_mid
from rpkit.rules_items import inside

ROOMS = "rooms"
DOORS = "doors"


class Ctx:
    """План и настройки: комнаты по ролям, вход, точка подключения."""

    def __init__(self, plan, cfg):
        self.plan = plan
        self.cfg = cfg
        self.furn = plan["furniture"]
        self.rooms = [room for room in plan[ROOMS] if room.get("rect")]

    def prefixes(self, roles):
        """Префиксы rooms[].id для ролей (роль или список ролей); неизвестная роль — сама префикс."""
        roles = [roles] if isinstance(roles, str) else roles
        found = []
        for role in roles:
            found.extend(self.cfg[ROOMS].get(role, [role]))
        return tuple(found)

    def role(self, roles, need_rect=True):
        """Комнаты с ролью (по умолчанию — только с rect)."""
        prefixes = self.prefixes(roles)
        rooms = self.rooms if need_rect else self.plan[ROOMS]
        return [room for room in rooms if room["id"].startswith(prefixes)]

    def in_role(self, piece, roles):
        """Предмет в одной из комнат роли; пустые roles — нет."""
        if not roles:
            return False
        return any(inside(piece, room) for room in self.role(roles))

    def entry(self):
        """Середина входной двери ("entry": true, иначе id door-entry) или None."""
        doors = [door for door in self.plan[DOORS] if door.get("entry")]
        if not doors:
            doors = [door for door in self.plan[DOORS] if door["id"] == "door-entry"]
        return door_mid(doors[0]) if doors else None
