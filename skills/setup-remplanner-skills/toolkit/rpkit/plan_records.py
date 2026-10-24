"""Записи плана для planlib: имена полей, разделы и общие куски сборки (вне planlib — их не индексирует
tools/blocks.py)."""

BEARING_KINDS = ("facade", "interapartment", "bearing", "column")
PLAN_KEYS = ("walls_bearing", "partitions", "windows", "doors", "fixed_elements", "furniture", "zones", "rooms")
CLEARED_KEYS = ("partitions", "furniture", "zones", "rooms")  # blank(): разделы концепции, которые пишутся заново
DOORS = "doors"
ID = "id"
NAME = "name"
NOTE = "note"
KIND = "kind"
RECT = "rect"
SQ_CM_IN_M2 = 1e4


def default_doors(plan):
    """id дверей, которые остаются в концепции: входная и двери балконных блоков."""
    windoor = {
        opening["windoor_door"]
        for opening in plan.get("windows", [])
        if opening.get("windoor_door")
    }
    return {
        door[ID]
        for door in plan.get(DOORS, [])
        if _is_entry(door) or door[ID] in windoor
    }


def with_optional(record, optional):
    """Дописывает в record поля (ключ, значение) с непустым значением — по порядку."""
    for key, field in optional:
        if field:
            record[key] = field
    return record


def room_areas(plan):
    """«id площадь, …» по комнатам плана или «комнат нет»."""
    rooms = plan.get("rooms", [])
    areas = ", ".join(room_area(record) for record in rooms)
    return areas or "комнат нет"


def room_area(record):
    """«id площадь» и разница с БТИ, если она задана."""
    measured = record["area"]
    line = f"{record[ID]} {measured:.2f}"
    bti = record.get("bti_area")
    if bti is None:
        return line
    diff = measured - bti
    signed = format(diff, "+.2f")
    return f"{line} (БТИ {bti:.2f}, {signed})"


def _is_entry(door):
    """Входная дверь — как planlib.is_entry."""
    return bool(door.get("entry")) or door[ID] == "door-entry"
