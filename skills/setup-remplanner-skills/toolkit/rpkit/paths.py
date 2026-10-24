"""Пути набора: папка инструментов tools/, корень проекта (её родитель), справочники и каталог RemPlanner."""

import os

_PACKAGE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(_PACKAGE)
ROOT = os.path.dirname(TOOLS)  # корень проекта — родитель tools/
REF = os.path.join(TOOLS, "reference")
CAT_DIR = os.path.join(TOOLS, "catalog")
CATALOG_JSON = os.path.join(CAT_DIR, "remplanner_catalog.json")
CATALOG_MD = os.path.join(CAT_DIR, "REMPLANNER_CATALOG.md")
CONFIRMED_JSON = os.path.join(CAT_DIR, "confirmed.json")
CORE_JSON = os.path.join(REF, "catalog_core.json")  # записи полного каталога для имён CATALOG
CHECKED_JSON = os.path.join(REF, "catalog_checked.json")  # rp_lib.CATALOG: сверено с образцами
MENU = os.path.join(REF, "remplanner_catalog_menu.txt")
TEMPLATE_PLAN = os.path.join(REF, "remplanner_example_v3_one_wall.plan")
FETCH = "python3 tools/rp_catalog.py fetch"
