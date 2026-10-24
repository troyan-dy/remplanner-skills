"""Роли предметов по разделу меню каталога (поле menu: «раздел», «группа») — чтобы любые диваны, кровати,
столы каталога проверялись, а не только перечисленные. Для имён rp_lib.CATALOG раздел известен и без полного
каталога (tools/reference/catalog_core.json). Группа None — весь раздел."""

from rpkit.catalog_store import catalog_info

LIVING = "Гостиная и спальня"
KITCHEN = "Кухня и столовая"
WARDROBE = "Гардероб и прихожая"
OFFICE = "Кабинет и офис"
KIDS = "Мебель для детской"
APPLIANCES = "Бытовая техника"

M_SOFA = frozenset(((LIVING, "Диваны"), (LIVING, "Модульные диваны")))
M_BED = frozenset(((LIVING, "Кровати"), (KIDS, "Кровати и диваны")))
M_CHAIR = frozenset(((LIVING, "Стулья"), (KITCHEN, "Стулья"), (OFFICE, "Кресла и стулья")))
M_BAR = frozenset(((KITCHEN, "Барная мебель"),))
M_KIDS_TABLES = frozenset(((KIDS, "Столы и стулья"),))
M_DESK = frozenset(((OFFICE, "Столы и стойки"),))
M_DINING = frozenset(((KITCHEN, "Обеденные столы"),))
M_TALL = frozenset(((KITCHEN, "Шкафы-пеналы"),))
M_FRIDGE = frozenset(((APPLIANCES, "Холодильники"),))
M_STOVE = frozenset(((APPLIANCES, "Кухонные плиты"),))
M_SINK = frozenset((("Раковины и мойки", None),))
M_HINGED = frozenset((
    (WARDROBE, "Гардеробные шкафы"),
    (WARDROBE, "Угловые шкафы"),
    (LIVING, "Шкафы"),
    ("Мебель для ванной", ""),
))
M_OPEN_WARD = frozenset(((WARDROBE, "Шкафы-купе"), (WARDROBE, "Открытые гардеробные")))
M_DRAWER = frozenset(((LIVING, "Комоды и тумбы"), (WARDROBE, "Обувницы и тумбы")))
M_SHELF = frozenset(((LIVING, "Стеллажи и полки"), (LIVING, "Крупногабаритные стеллажи")))


def in_menu(name, sections):
    """Предмет в одной из групп меню каталога (группа None — весь раздел)."""
    places = catalog_info(name).get("menu", [])
    return any(_listed(place, sections) for place in places)


def _listed(place, sections):
    section = place[0]
    return (section, place[1]) in sections or (section, None) in sections
