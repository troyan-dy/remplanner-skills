"""Роли предметов для проверки эргономики: стул, диван, кровать, ТВ, рабочий и обеденный стол — по разделу
меню каталога и шаблонам имён."""

import re

from rpkit.catalog_store import catalog_info
from rpkit.layout_menu import M_BAR, M_BED, M_CHAIR, M_DESK, M_DINING, M_KIDS_TABLES, M_SOFA, in_menu

CHAIR = "chair"
BAR_SEAT = re.compile("chair|tabouret")
NOT_SOFA = re.compile("kitchen|armrest|pouf")
NOT_BED_FRONTS = re.compile("transformer|cradle|chaiselongue")
NOT_DESK = re.compile("reception|meeting|briefing")
DINING_TABLES = ("table", "table_round", "bar_table")


def is_chair(name):
    """Стул, кресло к столу, барный стул или табурет — переставляемое: не мешает проходам и зонам."""
    if not name:
        return False
    if catalog_info(name).get("custom_type") == CHAIR or in_menu(name, M_CHAIR):
        return True
    if in_menu(name, M_BAR) and BAR_SEAT.search(name) is not None:
        return True
    return in_menu(name, M_KIDS_TABLES) and CHAIR in name


def is_sofa(name):
    """Диван (с него смотрят ТВ, перед ним sofa_front); кухонный диван-скамья — место за столом, не диван."""
    if not name or NOT_SOFA.search(name):
        return False
    if in_menu(name, M_SOFA):
        return True
    return in_menu(name, M_BED) and "sofa" in name and "bed" not in name


def is_bed(name):
    """Кровать любого размера (с неё смотрят ТВ)."""
    return bool(name) and in_menu(name, M_BED) and not is_sofa(name)


def bed_fronts(name):
    """Кровать, у которой проверяются бока и изножье: без трансформеров (откидные, в шкафу) и люлек."""
    return is_bed(name) and not NOT_BED_FRONTS.search(name)


def is_tv(name):
    """Телевизор (по названию в каталоге)."""
    return catalog_info(name).get("title", "").startswith("Телевизор")


def is_desk(name):
    """Рабочий стол: «Кабинет и офис / Столы и стойки» без стоек ресепшн и переговорных; школьная парта."""
    if not name:
        return False
    if in_menu(name, M_DESK) and not NOT_DESK.search(name):
        return True
    return name == "kid_desk"


def is_dining(name):
    """Обеденный стол: стол из CATALOG или «Кухня и столовая / Обеденные столы»."""
    return name in DINING_TABLES or in_menu(name, M_DINING)
