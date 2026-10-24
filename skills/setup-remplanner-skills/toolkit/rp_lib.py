"""rp_lib.py — сборка объектов RemPlanner .plan v3 по образцам из tools/reference/.

Все координаты здесь — координаты RemPlanner: см, ось y вниз, начало в центре плана.
Поля и значения повторяют наблюдённые в tools/reference/remplanner_example_v3_*.plan
(см. tools/reference/REMPLANNER_V3_SCHEMA.md); производные поля считаются так же, как в образцах.
Предметы: CATALOG — сверены с образцами (tools/reference/catalog_checked.json); полный каталог — tools/catalog/remplanner_catalog.json
(собирается `python3 tools/rp_catalog.py fetch`); подтверждённые снимком пользователя —
tools/catalog/confirmed.json (confirmed_names()).

Без полного каталога работают предметы CATALOG и confirmed.json: сведения каталога о них (габарит по умолчанию,
over_floor, custom_type, подводки, раздел меню) — в tools/reference/catalog_core.json (выписка из полного
каталога, `python3 tools/rp_catalog.py core`) и в поле "catalog" записи confirmed.json (`rp_catalog.py confirm`).
Полный каталог нужен только для прочих имён: entry() / info() / check_names().

Здесь — только имена для генераторов и инструментов; сборка объектов — в модулях tools/rpkit/ (rp_wall, rp_door,
rp_window, rp_items, rp_plan, catalog_*).
"""

from rpkit import rp_door, rp_wall, rp_window
from rpkit.catalog_checked import CATALOG, KITCHEN, PC_SHIFT
from rpkit.catalog_names import check_names, plan_names, spec
from rpkit.catalog_store import catalog_info, confirmed, confirmed_names, core, entry, full_catalog, has_full
from rpkit.paths import CAT_DIR, CATALOG_JSON, CONFIRMED_JSON, CORE_JSON, FETCH, REF, TOOLS
from rpkit.rp_geometry import pt, r3
from rpkit.rp_ids import reset_ids, uid
from rpkit.rp_items import make_item
from rpkit.rp_plan import dump_plan, new_plan

HEIGHT = rp_wall.HEIGHT
# публичные имена rp_lib.info и rp_lib.item (их называют check_layout, check_rules, документация и генераторы)
info = catalog_info  # noqa: WPS110
item = make_item  # noqa: WPS110
dump = dump_plan  # прежнее имя rp_lib.dump


# Прежние сигнатуры сборки стены и проёмов (их зовут генераторы проектов и скил remplanner-primitive):
# имена и порядок параметров сохранены, сборка — в rpkit.rp_wall, rp_door, rp_window.
def wall(x1, y1, x2, y2, depth, material="a_block"):  # noqa: WPS211
    """Стена от (x1, y1) до (x2, y2) толщиной depth."""
    return rp_wall.wall((x1, y1, x2, y2), depth, material)


def door(w, t0, width, height=210, kind="single", opening="r-l"):  # noqa: WPS111, WPS211
    """kind: single (дверь стандартная) | doorway (проём без двери)."""
    return rp_door.door(w, (t0, width), height, kind, opening)


def window(w, t0, width, height, sill, casements=1):  # noqa: WPS111, WPS211
    """Окно шириной width от t0 вдоль стены w."""
    return rp_window.window(w, (t0, width), height, sill, casements)


def windoor(  # noqa: WPS211
    w, t0, door_width, window_width, door_height, window_height, door_position="l",  # noqa: WPS111
):
    """Балконный блок. В образце door_position 'l' = дверь у p1 проёма (connection_point = p1 + door_width)."""
    return rp_window.windoor(w, t0, (door_width, door_height), (window_width, window_height), door_position)
