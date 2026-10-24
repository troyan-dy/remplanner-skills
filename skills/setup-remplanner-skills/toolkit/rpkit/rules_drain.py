"""Канализация для правил жильцов: приборы с выпуском в предмете (раковина, унитаз, модули линии кухни…)."""

import itertools

from rpkit.catalog_checked import KITCHEN, KITCHEN_MODULE_CM
from rpkit.catalog_store import catalog_info
from rpkit.rules_items import ALONG_X, specs

DRAINING_MODULES = ("sink", "washer", "dishwasher")  # модули линии кухни с выпуском
RECT = "rect"


def _module_size(module):
    if module in KITCHEN:
        return KITCHEN_MODULE_CM
    return catalog_info(module).get("width", KITCHEN_MODULE_CM)


def _draining(module):
    return module in DRAINING_MODULES or catalog_info(module).get("custom_type") == "sink"


def _placed_modules(modules):
    """(модуль, начало, ширина) вдоль линии кухни."""
    sizes = [_module_size(module) for module in modules]
    return zip(modules, itertools.accumulate(sizes, initial=0), sizes)


def _named_outlet(piece, along_x, placed):
    """(«id:модуль», середина модуля) для модуля placed = (модуль, начало, ширина)."""
    module, start, size = placed
    rect = piece[RECT]
    if along_x:
        point = (
            rect[0] + start + size / 2,
            rect[1] + rect[3] / 2,
        )
    else:
        point = (
            rect[0] + rect[2] / 2,
            rect[1] + start + size / 2,
        )
    return f"{piece['id']}:{module}", point


def _module_outlets(piece, spec_rp):
    """Выпуски модулей линии кухни: [(«id:модуль», точка)]."""
    along_x = spec_rp["back"] in ALONG_X
    return [
        _named_outlet(piece, along_x, placed)
        for placed in _placed_modules(spec_rp["modules"])
        if _draining(placed[0])
    ]


def drains(piece):
    """Приборы с канализацией в предмете: [(имя, точка выпуска)]."""
    outlets = []
    for spec_rp in specs(piece):
        if spec_rp["name"] == "kitchen_run":
            outlets.extend(_module_outlets(piece, spec_rp))
            continue
        santeh = catalog_info(spec_rp["name"]).get("santeh_data") or {}
        if "drainage_pipe" in santeh.get("pipes", []):
            outlets.append((f"{piece['id']}", center(piece[RECT])))
            break
    return outlets


def center(rect):
    x_cm, y_cm, width, height = rect
    return (x_cm + width / 2, y_cm + height / 2)
