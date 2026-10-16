#!/usr/bin/env python3
"""blocks.py — индекс готовых блоков для новой серии: функции tools/planlib.py и генераторов проекта
src/*.py (первая строка docstring), константы и каталог RemPlanner (rp_lib.CATALOG, confirmed.json).
Читать его вместо исходников прошлых серий; нужный блок импортировать из его модуля, исходник смотреть
только по имени функции."""

import ast
import glob
import os

import rp_lib

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)  # корень проекта — родитель tools/


def index(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    print("##", os.path.relpath(path, ROOT))
    consts = [
        t.id
        for n in tree.body
        if isinstance(n, ast.Assign)
        for t in n.targets
        if isinstance(t, ast.Name) and t.id.isupper()
    ]
    if consts:
        print("  const:", ", ".join(consts))
    for n in tree.body:
        if isinstance(n, ast.FunctionDef):
            doc = (ast.get_docstring(n) or "").split("\n")[0]
            print(f"  {n.name}({', '.join(a.arg for a in n.args.args)}): {doc}")


if __name__ == "__main__":
    index(os.path.join(TOOLS, "planlib.py"))
    for f in sorted(glob.glob(os.path.join(ROOT, "src", "*.py"))):
        index(f)
    print("## rp_lib.CATALOG (тип → item_id), сверены с образцами")
    print("  " + ", ".join(f"{k}:{v['item_id']}" for k, v in rp_lib.CATALOG.items()))
    extra = sorted(set(rp_lib.confirmed()) - set(rp_lib.CATALOG))
    if extra:
        print("## подтверждены пользователем (tools/catalog/confirmed.json)")
        print("  " + ", ".join(extra))
    if os.path.exists(rp_lib.CATALOG_JSON):
        n = sum(e["in_items"] for e in rp_lib.full_catalog().values())
        print(
            f"## полный каталог: {n} предметов для rp_lib.item(name, cx, cy[, w, h]) — "
            "python3 tools/rp_catalog.py find <слово> | show <name>; справочник tools/catalog/REMPLANNER_CATALOG.md"
        )
    else:
        print("## полного каталога нет — python3 tools/rp_catalog.py fetch")
