"""Поиск по каталогу (rp_catalog.py find) и сведения о предмете (rp_catalog.py show)."""

import json
import os
import sys

from rpkit.catalog_lookup import SEP, load_catalog, search
from rpkit.catalog_notes import note_for
from rpkit.catalog_purpose import purpose
from rpkit.console import say
from rpkit.paths import CATALOG_JSON

NAME_WIDTH = "40"
ID_WIDTH = "5"


def _hit_line(name, record):
    places = " | ".join(
        _place(*place) for place in record.get("menu", [])
    )
    tail = "" if record["in_items"] else "  [не items]"
    return f"{_hit_head(name, record)}{tail}  — {places}  {purpose(record)}"


def _hit_head(name, record):
    """«имя id Ш×Г×В название» с выравниванием колонок."""
    height = format(record["self_height"], "<4")
    size = f"{record['width']}×{record['height']}×{height}"
    number = format(record["id"], ID_WIDTH)
    return f"{format(name, NAME_WIDTH)} {number} {size} {record['title']}"


def _place(section, group, pro):
    pro_mark = " PRO" if pro else ""
    return f"{section}/{group}{pro_mark}"


def find(words):
    """Поиск без учёта регистра по имени (английскому), названию, описанию и разделу меню; все слова сразу.
    Ничего не нашлось — повтор с заменой по SYNONYMS («миска» → «кормушк»), затем с корнем слов, укороченных
    до 4 и до 3 букв (русские словоформы: «кошк» → «кош» найдёт «Кошачий»); такие находки помечены."""
    lowered = list(map(str.lower, words))
    hits, how = search(load_catalog(strict=False), lowered)
    if not hits:
        say(f"ничего не найдено: {SEP.join(words)}")
        return
    if how:
        say(f"точных совпадений нет — найдено {how}:")
    for hit in hits:
        say(_hit_line(*hit))


def show(name):
    """Всё о предмете: запись каталога, назначение, толкование групп меню."""
    record = load_catalog(strict=False).get(name)
    if record is None:
        tail = "" if os.path.exists(CATALOG_JSON) else " — нужен полный каталог"
        sys.exit(f"{name}: нет сведений{tail}")
    say(json.dumps(record, ensure_ascii=False, indent=1))
    say(f"назначение: {purpose(record)}")
    for section, group, _ in record.get("menu", []):
        note = note_for(section, group)
        if note:
            say(f"{section} / {group}: {note}")
