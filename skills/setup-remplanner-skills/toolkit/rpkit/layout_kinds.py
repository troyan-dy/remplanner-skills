"""Роли кухонных и сантехнических предметов, высота над полом, rp предмета мебели."""

import re

from rpkit.catalog_store import catalog_info
from rpkit.frozen import frozen
from rpkit.layout_menu import M_FRIDGE, M_SINK, M_TALL, in_menu

TALL_CM = 120  # холодильник выше этого — высокий модуль кухни
TOILETS = re.compile("^toilet(_with_frame|_embedded|_impulse)?$|^corner_toilet$")  # как в rules_config.TOILETS
SINKS = ("sink_table_susp", "double_sink_box_floor")
OVER_FLOOR = "over_floor"
# куда смотрит лицо предмета при back=…
FRONT = frozen({
    "down": (0, -1),
    "up": (0, 1),
    "left": (1, 0),
    "right": (-1, 0),
})


def specs(piece):
    """rp предмета списком (rp — объект или список)."""
    attached = piece.get("rp")
    if not attached:
        return []
    return attached if isinstance(attached, list) else [attached]


def kind(piece):
    """Имя каталога первого rp предмета или None."""
    attached = specs(piece)
    return attached[0]["name"] if attached else None


def is_fridge(name):
    """Холодильник (кроме мини-холодильника)."""
    return bool(name) and "fridge" in name and name != "mini_fridge"


def is_tall_kitchen(name):
    """Высокий кухонный модуль: пенал, холодильник в рост."""
    if not name:
        return False
    if in_menu(name, M_TALL) or is_fridge(name):
        return True
    height = catalog_info(name).get("self_height", 0)
    return in_menu(name, M_FRIDGE) and height >= TALL_CM


def is_toilet(name):
    """Унитаз (по имени каталога)."""
    return bool(name) and TOILETS.search(name) is not None


def is_sink(name):
    """Раковина или мойка."""
    if not name:
        return False
    if catalog_info(name).get("custom_type") == "sink" or name in SINKS:
        return True
    return in_menu(name, M_SINK)


def over_floor(spec_rp):
    """Низ предмета над полом, см: число rp.over_floor или over_floor каталога."""
    given = spec_rp.get(OVER_FLOOR)
    if isinstance(given, (int, float)):
        return given
    record = catalog_info(spec_rp["name"]).get(OVER_FLOOR) or {}
    return record.get("value", 0) or 0
