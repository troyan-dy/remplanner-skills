"""Сведения каталога RemPlanner о предметах: полный каталог (tools/catalog/remplanner_catalog.json, если собран),
выписка для CATALOG (tools/reference/catalog_core.json) и подтверждённые пользователем (tools/catalog/confirmed.json)."""

import functools
import os
import sys

from rpkit.catalog_checked import CATALOG
from rpkit.jsonfile import read_json
from rpkit.paths import CATALOG_JSON, CONFIRMED_JSON, CORE_JSON, FETCH


def has_full():
    """Собран ли полный каталог tools/catalog/remplanner_catalog.json."""
    return os.path.exists(CATALOG_JSON)


@functools.lru_cache(maxsize=None)
def full_catalog():
    """Предметы полного каталога; без него — выход с командой fetch."""
    if not has_full():
        sys.exit(f"нет полного каталога {CATALOG_JSON} — запустите {FETCH}")
    return read_json(CATALOG_JSON)["items"]


@functools.lru_cache(maxsize=None)
def core():
    """Записи полного каталога для имён CATALOG (tools/reference/catalog_core.json) — работают без fetch."""
    return read_json(CORE_JSON) if os.path.exists(CORE_JSON) else {}


@functools.lru_cache(maxsize=None)
def confirmed():
    """Предметы, которые пользователь подтвердил снимком RemPlanner после импорта:
    tools/catalog/confirmed.json — {"<name>": {"date": "ГГГГ-ММ-ДД", "note": "...", "catalog": {…}}}; файла может
    не быть. "catalog" — копия записи полного каталога (её пишет `rp_catalog.py confirm`): с ней предмет
    работает и без полного каталога. Нужен потому, что tools/ перезаписывается установкой и CATALOG
    пользователь не дописывает."""
    if os.path.exists(CONFIRMED_JSON):
        return read_json(CONFIRMED_JSON)
    return {}


def confirmed_names():
    """Проверенные импортом имена: CATALOG ∪ confirmed.json."""
    return set(CATALOG) | set(confirmed())


def entry(name):
    """Запись каталога о предмете: из полного каталога, если он собран; иначе из выписки для CATALOG
    (catalog_core.json) или из confirmed.json (поле "catalog"). None — сведений нет."""
    if has_full():
        return full_catalog().get(name)
    user_confirmed = confirmed().get(name) or {}
    return core().get(name) or user_confirmed.get("catalog")


def catalog_info(name):
    """Как entry(), но {} вместо None: для проверок, которым хватает «нет сведений» (линия кухни, опечатка)."""
    found = entry(name) if name else None
    return found or {}
