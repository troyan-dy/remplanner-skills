"""Записи каталога, которые живут без полного каталога: подтверждённые пользователем (confirmed.json)
и выписка для имён CATALOG (catalog_core.json)."""

import datetime
import itertools
import json
import os
import sys

from rpkit.catalog_checked import CATALOG
from rpkit.catalog_lookup import load_catalog
from rpkit.catalog_store import confirmed
from rpkit.console import say
from rpkit.jsonfile import write_json, write_text
from rpkit.paths import CAT_DIR, CONFIRMED_JSON, CORE_JSON, ROOT

CORE_SKIPPED = ("desc", "subgroup")  # проверкам и экспорту не нужны


def confirm(name, note=""):
    """Записать предмет, подтверждённый снимком RemPlanner, в tools/catalog/confirmed.json — с датой, заметкой
    и копией записи полного каталога (с ней предмет работает и без полного каталога)."""
    record = load_catalog().get(name)
    if record is None:
        sys.exit(f"{name}: нет в каталоге — python3 tools/rp_catalog.py find <слово>")
    known = dict(confirmed())
    known[name] = {
        "date": datetime.date.today().isoformat(),
        "note": note,
        "catalog": record,
    }
    os.makedirs(CAT_DIR, exist_ok=True)
    write_json(CONFIRMED_JSON, known, ensure_ascii=False, indent=1)
    relative = os.path.relpath(CONFIRMED_JSON, ROOT)
    say(f"{name} → {relative}")


def core_dump():
    """Выписка полного каталога для имён rp_lib.CATALOG → tools/reference/catalog_core.json (для разработчика
    набора: обновлять при правке CATALOG). Без desc и subgroup — проверкам и экспорту они не нужны."""
    catalog = load_catalog()
    extract = {name: _core_record(catalog[name]) for name in CATALOG}
    body = ",\n".join(itertools.starmap(_core_line, extract.items()))
    write_text(CORE_JSON, f"{{\n{body}\n}}\n")
    relative = os.path.relpath(CORE_JSON, ROOT)
    say(f"{len(extract)} предметов → {relative}")


def _core_record(record):
    return {key: field for key, field in record.items() if key not in CORE_SKIPPED}


def _core_line(name, record):
    """Строка выписки: «"имя": {запись}» — по предмету на строку."""
    return f"{json.dumps(name)}: {json.dumps(record, ensure_ascii=False)}"
