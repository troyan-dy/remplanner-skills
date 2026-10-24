"""Каталог для поиска: полный или (без него) предметы CATALOG и confirmed.json; совпадения по словам."""

import os
import sys

from rpkit.catalog_notes import SYNONYMS
from rpkit.catalog_store import confirmed, core
from rpkit.console import say
from rpkit.jsonfile import read_json
from rpkit.paths import CATALOG_JSON, ROOT

ROOT_LENGTHS = (4, 3)  # корни слов для повторного поиска (русские словоформы)
SEP = " "


def load_catalog(strict=True):
    """Полный каталог; без него при strict=False — предметы CATALOG и confirmed.json (с предупреждением)."""
    if os.path.exists(CATALOG_JSON):
        return read_json(CATALOG_JSON)["items"]
    if strict:
        relative = os.path.relpath(CATALOG_JSON, ROOT)
        sys.exit(f"нет каталога {relative} — запустите python3 tools/rp_catalog.py fetch")
    catalog = dict(core())
    for name, record in confirmed().items():
        user_copy = record.get("catalog")
        if user_copy:
            catalog[name] = user_copy
    say(
        f"полный каталог не собран (python3 tools/rp_catalog.py fetch) — ищу среди {len(catalog)} предметов "
        "rp_lib.CATALOG и confirmed.json",
    )
    return catalog


def _haystack(name, record):
    places = [_place_words(place) for place in record.get("menu", [])]
    parts = [
        name,
        name.replace("_", SEP),
        record["title"],
        record.get("desc", ""),
    ]
    return SEP.join(parts + places).lower()


def _place_words(place):
    """«раздел группа» места в меню."""
    return SEP.join(map(str, place[:2]))


def _matches(catalog, words):
    return [
        (name, record) for name, record in catalog.items()
        if all(word in _haystack(name, record) for word in words)
    ]


def _synonym(word):
    """Слово с заменой начала по SYNONYMS («миск…» → «кормушк»), если такая есть."""
    for key, synonym in SYNONYMS.items():
        if word.startswith(key):
            return synonym
    return word


def search(catalog, words):
    """(находки, как найдено): точно, по замене SYNONYMS, по корням из 4 и 3 букв."""
    hits = _matches(catalog, words)
    if hits:
        return hits, ""
    attempts = [([_synonym(word) for word in words], "по замене")]
    attempts.extend(
        ([word[:length] for word in words], "по корню") for length in ROOT_LENGTHS
    )
    for changed, how in attempts:
        if changed != words:
            hits = _matches(catalog, changed)
            if hits:
                return hits, f"{how} «{SEP.join(changed)}»"
    return hits, ""
