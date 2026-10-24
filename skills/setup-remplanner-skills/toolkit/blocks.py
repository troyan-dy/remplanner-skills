#!/usr/bin/env python3
"""blocks.py — индекс готовых блоков для новой серии: функции tools/planlib.py и генераторов проекта
src/*.py (первая строка docstring), константы и каталог RemPlanner (rp_lib.CATALOG, confirmed.json).
Читать его вместо исходников прошлых серий; нужный блок импортировать из его модуля, исходник смотреть
только по имени функции."""

import ast
import glob
import os

import rp_lib
from rpkit.console import say
from rpkit.jsonfile import read_text

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)  # корень проекта — родитель tools/
_LIST_SEP = ", "


def index(path):
    """Константы модуля и его функции с первой строкой docstring."""
    tree = ast.parse(read_text(path))
    relative = os.path.relpath(path, ROOT)
    say(f"## {relative}")
    consts = _constants(tree)
    if consts:
        say(f"  const: {_LIST_SEP.join(consts)}")
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            say(f"  {_signature(node)}: {_first_doc_line(node)}")


def _constants(tree):
    return [
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name) and target.id.isupper()
    ]


def _signature(function):
    args = _LIST_SEP.join(arg.arg for arg in function.args.args)
    return f"{function.name}({args})"


def _first_doc_line(function):
    docstring = ast.get_docstring(function) or ""
    return docstring.split("\n")[0]


def catalog():
    """Предметы rp_lib.CATALOG и confirmed.json, полный каталог — есть ли он."""
    say("## rp_lib.CATALOG (тип → item_id), сверены с образцами")
    pairs = (
        f"{name}:{entry['item_id']}" for name, entry in rp_lib.CATALOG.items()
    )
    say(f"  {_LIST_SEP.join(pairs)}")
    extra = sorted(set(rp_lib.confirmed()) - set(rp_lib.CATALOG))
    if extra:
        say("## подтверждены пользователем (tools/catalog/confirmed.json)")
        say(f"  {_LIST_SEP.join(extra)}")
    _full_catalog_line()


def _full_catalog_line():
    if not os.path.exists(rp_lib.CATALOG_JSON):
        say("## полного каталога нет: работают предметы CATALOG и confirmed.json, прочие — после "
            "python3 tools/rp_catalog.py fetch")
        return
    entries = rp_lib.full_catalog().values()
    count = sum(entry["in_items"] for entry in entries)
    say(
        f"## полный каталог: {count} предметов для rp_lib.item(name, cx, cy[, w, h]) — "
        "python3 tools/rp_catalog.py find <слово> | show <name>; справочник tools/catalog/REMPLANNER_CATALOG.md",
    )


if __name__ == "__main__":
    index(os.path.join(TOOLS, "planlib.py"))
    for generator in sorted(glob.glob(os.path.join(ROOT, "src", "*.py"))):
        index(generator)
    catalog()
