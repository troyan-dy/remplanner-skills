"""Предметы, сверенные с образцами RemPlanner (rp_lib.CATALOG), и сокращения модулей линии кухни.

CATALOG — из tools/reference/catalog_checked.json: item_id, plan, self_height и доп. поля по группам с источником
(образцы tools/reference/remplanner_example_v3_*.plan и снимки RemPlanner после импорта)."""

from rpkit.frozen import frozen
from rpkit.jsonfile import read_json
from rpkit.paths import CHECKED_JSON


def _load_checked():
    """Предметы всех групп catalog_checked.json одним словарём, в порядке файла."""
    checked = {}
    for group in read_json(CHECKED_JSON)["groups"]:
        checked.update(group["items"])
    return frozen(checked)


CATALOG = _load_checked()

# Модули линии кухни (kitchen_run): сокращение → имя каталога; по 60 см, столешница — над всеми, кроме плиты.
KITCHEN = frozen({
    "box": "kitchen_box_door_double",
    "sink": "kitchen_box_door_double",
    "stove": "stove",
    "washer": "washing_machine",
    "dishwasher": "kitchen_box_dishwasher",
})
KITCHEN_MODULE_CM = 60  # ширина модуля-сокращения

# Точка pc у некоторых моделей не в центре значка: RemPlanner рисует значок со сдвигом к стене (спинке).
# Плита 102: icon_center = pc + 14,1 см в сторону спинки (все образцы tools/reference/remplanner_example_v3_*.plan,
# угол 0 и 180). Без поправки плита на снимке уходила в стену на 14 см.
PC_SHIFT = frozen({"stove": 14.1})
