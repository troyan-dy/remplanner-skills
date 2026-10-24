#!/usr/bin/env python3
"""rp_catalog.py — полный каталог предметов RemPlanner: сборка, поиск, справочник.

  python3 tools/rp_catalog.py fetch [<url|planner.tools___*.js>]  # скачать скрипт планировщика и собрать каталог
  python3 tools/rp_catalog.py build <planner.tools___*.js>   # → tools/catalog/remplanner_catalog.json + REMPLANNER_CATALOG.md
  python3 tools/rp_catalog.py find <слово> [<слово> ...]      # поиск по имени/названию/разделу
  python3 tools/rp_catalog.py show <name>                    # всё о предмете
  python3 tools/rp_catalog.py confirm <name> [заметка]       # подтверждён снимком → tools/catalog/confirmed.json
  python3 tools/rp_catalog.py core                           # выписка для CATALOG → tools/reference/catalog_core.json

find и show без полного каталога ищут среди предметов rp_lib.CATALOG и confirmed.json (выписка
tools/reference/catalog_core.json и поле "catalog" в confirmed.json) и говорят, что полный каталог не собран.

Источники (как получить заново — tools/reference/REMPLANNER_V3_SCHEMA.md, «Полный каталог»):
  - window.global_tools из публичного https://remplanner.ru/files/js/v2/app/planner.tools___<ver>.js —
    параметры каждого инструмента (id, название, габарит, высота, over_floor, листы, привязка, подводки);
  - tools/reference/remplanner_catalog_menu.txt — дерево меню (раздел → группа → id), снято из DOM планировщика.
SVG-контуры RemPlanner в каталог не копируются: для .plan нужен только item_id, рисует RemPlanner сам.
"""

import sys

from rpkit.catalog_build import build
from rpkit.catalog_confirm import confirm, core_dump
from rpkit.catalog_fetch import fetch
from rpkit.catalog_search import find, show
from rpkit.frozen import frozen


def _fetch(args):
    fetch(args[0] if args else None)


def _build(args):
    build(args[0])


def _show(args):
    show(args[0])


def _confirm(args):
    confirm(args[0], " ".join(args[1:]))


COMMANDS = frozen({
    "fetch": _fetch,
    "build": _build,
    "find": find,
    "show": _show,
    "confirm": _confirm,
    "core": lambda _: core_dump(),
})


def main(argv):
    """rp_catalog.py <команда> [аргументы] — см. docstring модуля."""
    if not argv or argv[0] not in COMMANDS:
        sys.exit(__doc__)
    COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    main(sys.argv[1:])
