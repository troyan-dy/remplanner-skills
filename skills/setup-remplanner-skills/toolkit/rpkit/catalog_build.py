"""Сборка полного каталога: global_tools + меню → tools/catalog/remplanner_catalog.json и REMPLANNER_CATALOG.md."""

import json
import os

from rpkit.catalog_markdown import write_md
from rpkit.catalog_menu import parse_menu
from rpkit.console import say
from rpkit.jsonfile import read_text, write_json
from rpkit.paths import CAT_DIR, CATALOG_JSON, CATALOG_MD, ROOT

# Группы global_tools, которые живут в plan.items и проверены импортом (см. REMPLANNER_V3_SCHEMA.md).
ITEM_GROUPS = ("furniture", "santeh_furniture")
BASE_FIELDS = ("id", "title", "group", "plan", "width", "height", "self_height")
COPIED_FIELDS = ("custom_type", "santeh_data", "subgroup", "from_ceiling")
MENU = "menu"


def parse_tools(js_path):
    """Словарь window.global_tools из скрипта инструментов планировщика."""
    source = read_text(js_path)
    start = source.index("{", source.index("window.global_tools"))
    tools, _ = json.JSONDecoder().raw_decode(source, start)
    return tools


class _MenuIndex:
    """Где предмет в меню (menu), описание из меню (desc) и порядок предметов для справочника (order)."""

    def __init__(self, tools):
        self.tools = tools
        self.by_id = {tool["id"]: name for name, tool in tools.items()}
        self.menu = {}
        self.desc = {}
        self.order = []

    def add_entry(self, entry, roots, pro_ids):
        """Предмет меню (MenuEntry): в каком разделе и группе, PRO ли, описание."""
        name = entry.alias
        if name not in self.tools:
            name = self.by_id.get(entry.tool_id)
        if not name:
            return
        title, root_pro, _ = roots[entry.root_id]
        pro = root_pro or entry.tool_id in pro_ids
        self.menu.setdefault(name, []).append([title, entry.group, pro])
        self.order.append((entry.root_id, entry.group, name, pro))
        if entry.desc:
            self.desc[name] = entry.desc

    def add_roots(self, roots):
        """Раздел-инструмент без подменю (радиаторы, щитки…)."""
        for root_id, (title, root_pro, _) in roots.items():
            name = self.by_id.get(root_id)
            if name and name not in self.menu:
                self.menu[name] = [[title, "", root_pro]]
                self.order.append((root_id, "", name, root_pro))

    def annotate(self, record, name):
        """Место предмета в меню (и pro, если везде PRO) и описание из меню — в запись каталога."""
        places = self.menu.get(name)
        if places is not None:
            record[MENU] = places
            if all(place[2] for place in places):
                record["pro"] = True
        desc = self.desc.get(name)
        if desc:
            record["desc"] = desc


def _entry(name, tool, index):
    """Запись каталога о предмете по его global_tools и месту в меню."""
    record = {field: tool[field] for field in BASE_FIELDS}
    if isinstance(tool["over_floor"], dict):
        record["over_floor"] = tool["over_floor"]
    if tool["anchor"] != "free":
        record["anchor"] = tool["anchor"]
    if tool.get("icon"):  # → on_show_decoration: 1 (так делает RemPlanner при создании)
        record["icon"] = True
    record.update(
        (field, tool[field]) for field in COPIED_FIELDS if tool.get(field)
    )
    if tool.get("can_be_outside"):
        record["can_be_outside"] = True
    if tool.get("width_label") == "length":
        record["width_is_length"] = True
    index.annotate(record, name)
    record["in_items"] = tool["group"] in ITEM_GROUPS
    return record


def build(js_path):
    """Каталог из скрипта инструментов js_path: JSON и справочник Markdown; печатает итог."""
    tools = parse_tools(js_path)
    roots, index = _menu_index(tools)
    catalog = _catalog(tools, index)
    os.makedirs(CAT_DIR, exist_ok=True)
    document = {"source": os.path.basename(js_path), "items": catalog}
    write_json(CATALOG_JSON, document, ensure_ascii=False, indent=0, sort_keys=False)
    write_md(catalog, roots, index.order)
    _report(catalog)


def _catalog(tools, index):
    return {name: _entry(name, tool, index) for name, tool in tools.items()}


def _menu_index(tools):
    """Разделы меню и _MenuIndex предметов tools."""
    roots, entries, pro_ids = parse_menu()
    index = _MenuIndex(tools)
    for entry in entries:
        index.add_entry(entry, roots, pro_ids)
    index.add_roots(roots)
    return roots, index


def _report(catalog):
    in_items = sum(record["in_items"] for record in catalog.values())
    json_path = os.path.relpath(CATALOG_JSON, ROOT)
    md_path = os.path.relpath(CATALOG_MD, ROOT)
    say(f"{len(catalog)} инструментов, из них предметов plan.items: {in_items} → {json_path}, {md_path}")
