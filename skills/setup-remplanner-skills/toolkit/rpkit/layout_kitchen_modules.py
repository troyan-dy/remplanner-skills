"""Модули линии кухни (kitchen_run): длины вдоль линии, мойки и плиты, где прерывается столешница."""

from rpkit.catalog_checked import KITCHEN, KITCHEN_MODULE_CM
from rpkit.catalog_store import catalog_info
from rpkit.layout_kinds import specs
from rpkit.layout_menu import M_STOVE, in_menu

SINK = "sink"
STOVE = "stove"
CUSTOM_TYPE = "custom_type"


def kitchen_modules(piece):
    """[(модуль, начало, конец)] вдоль линии kitchen_run от меньшей координаты."""
    start, modules = 0, []
    for module in specs(piece)[0]["modules"]:
        size = KITCHEN_MODULE_CM
        if module not in KITCHEN:
            size = catalog_info(module).get("width", KITCHEN_MODULE_CM)
        modules.append((module, start, start + size))
        start += size
    return modules


def has_top(module):
    """Над модулем линии кухни лежит столешница — как в экспорте kitchen_run."""
    if module in KITCHEN and module != STOVE:
        return True
    return catalog_info(module).get(CUSTOM_TYPE) == "table_top"


def _custom_type(module):
    """custom_type записи каталога модуля (сокращение — по имени каталога из KITCHEN)."""
    return catalog_info(KITCHEN.get(module, module)).get(CUSTOM_TYPE)


def is_sink_module(module):
    """Модуль — мойка."""
    return module == SINK or _custom_type(module) == SINK


def is_stove_module(module):
    """Модуль — плита или варочная панель."""
    name = KITCHEN.get(module, module)
    if module == STOVE or name == "hob":
        return True
    return in_menu(name, M_STOVE)


def stops_top(module):
    """Модуль прерывает столешницу у плиты: мойка, другая плита, модуль без столешницы."""
    if module in {STOVE, SINK} or not has_top(module):
        return True
    return _custom_type(module) == SINK


def free_top(modules):
    """(длина столешницы подряд до первого модуля, который её прерывает; дошла ли до конца modules)."""
    length = 0
    for module, start, end in modules:
        if stops_top(module):
            return length, False
        length += end - start
    return length, True
