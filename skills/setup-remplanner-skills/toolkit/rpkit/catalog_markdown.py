"""Справочник tools/catalog/REMPLANNER_CATALOG.md по собранному каталогу."""

import itertools

from rpkit.catalog_checked import CATALOG
from rpkit.catalog_notes import SHEETS, note_for
from rpkit.catalog_others import others_lines
from rpkit.catalog_purpose import purpose
from rpkit.jsonfile import write_text
from rpkit.paths import CATALOG_MD

ITEM_SHEETS = ("furniture", "santeh", "radiators")  # листы, разделы которых идут в справочник
IN_ITEMS = "in_items"
TITLE = "title"
GROUP_TABLE = ("| name | Название | Ш×Г | В | Назначение |", "|---|---|---|---|---|")
OUTSIDE = (
    "## Вне меню",
    "",
    "Варианты, которые выбираются в свойствах предмета (`subgroup`), и предметы других листов "
    "(датчики, короба, радиаторы-инструменты).",
    "",
    "| name | Название | Ш×Г | В | Листы | Назначение |",
    "|---|---|---|---|---|---|",
)


HEADER = (
        "# Каталог предметов RemPlanner",
        "",
        "Генерируется `python3 tools/rp_catalog.py fetch` (или `build <planner.tools.js>`) — руками не править. "
        "Данные: `tools/catalog/remplanner_catalog.json`, поиск: `python3 tools/rp_catalog.py find <слово>`.",
        "",
        "Колонки: `name` — ключ для `rp_lib.item()`; Ш×Г — габарит в плане при `angle: 0` (ширина вдоль спинки, "
        "глубина), см; В — высота в 3D (`self_height`; 0 — RemPlanner берёт высоту модели сам, предположение); "
        "«Назначение» — по параметрам каталога. Описание группы — толкование по названиям (не текст RemPlanner); "
        "нормативы с пометкой «предположение» не проверены. PRO — в гостевом режиме меню не даёт поставить.",
        "",
        "Как предметы попадают в `.plan`: группы `furniture` и `santeh_furniture` — `plan.items` "
        f"(`rp_lib.item()`; импортом проверены {len(CATALOG)} предметов `rp_lib.CATALOG` и подтверждённые "
        "пользователем в `tools/catalog/confirmed.json`, остальные — по тем же правилам, "
        "см. REMPLANNER_V3_SCHEMA.md «Полный каталог»); остальные (розетки, свет, трубы, щит…) — "
        "схема в `.plan` не получена, `rp_lib.item()` их не ставит.",
        "",
    )


def _size(record):
    return f"{record['width']}×{record['height']} | {record['self_height']}"


def _table_row(cells):
    inner = " | ".join(cells)
    return f"| {inner} |"


def _has_items(groups):
    """В разделе есть предметы plan.items."""
    records = (record for group in groups.values() for _, record, _ in group)
    return any(record[IN_ITEMS] for record in records)


class _Markdown:
    """Строки справочника и имена, которые уже попали в разделы меню."""

    def __init__(self, catalog):
        self.catalog = catalog
        self.lines = list(HEADER)
        self.seen = set()

    def sheet(self, sheet, sections, rows):
        """Лист планировщика: его разделы, в которых есть предметы plan.items."""
        self.lines.extend((f"## Лист «{SHEETS.get(sheet, sheet)}»", ""))
        for root_id, title, root_pro in sections:
            groups = rows.get(root_id, {})
            if _has_items(groups):
                self._section(title, root_pro, groups)

    def outside(self):
        """Предметы plan.items, которых нет в меню."""
        rest = [
            name for name, record in self.catalog.items()
            if self._outside(name, record)
        ]
        if not rest:
            return
        self.lines.extend(OUTSIDE)
        self.lines.extend(self._outside_row(name) for name in rest)
        self.lines.append("")

    def _outside(self, name, record):
        return record[IN_ITEMS] and name not in self.seen and not record.get("menu")

    def _outside_row(self, name):
        record = self.catalog[name]
        labels = (SHEETS.get(key, key) for key in record["plan"])
        sheets = ", ".join(labels)
        cells = (
            f"`{name}`",
            record[TITLE],
            _size(record),
            sheets,
            purpose(record),
        )
        return _table_row(cells)

    def _section(self, title, root_pro, groups):
        pro_mark = " (PRO)" if root_pro else ""
        self.lines.extend((f"### {title}{pro_mark}", ""))
        for group, members in groups.items():
            if group:
                self.lines.extend((f"#### {group}", ""))
            note = note_for(title, group)
            if note:
                self.lines.extend((note, ""))
            self.lines.extend(GROUP_TABLE)
            self.lines.extend(itertools.starmap(self._row, members))
            self.lines.append("")

    def _row(self, name, record, pro):
        self.seen.add(name)
        pro_mark = " PRO" if pro else ""
        title = f"{record[TITLE]}{pro_mark}"
        return _table_row((f"`{name}`", title, _size(record), purpose(record)))


def _by_sheet(roots):
    """Разделы меню по первому листу, где они видны: {лист: [(id, название, pro)]}."""
    sheets = {}
    for root_id, (title, root_pro, root_sheets) in roots.items():
        sheets.setdefault(root_sheets[0], []).append((root_id, title, root_pro))
    return sheets


def _rows(catalog, order):
    """{раздел: {группа: [(имя, запись, pro)]}} в порядке меню."""
    rows = {}
    for root_id, group, name, pro in order:
        rows.setdefault(root_id, {}).setdefault(group, []).append(
            (name, catalog[name], pro),
        )
    return rows


def write_md(catalog, roots, order):
    """REMPLANNER_CATALOG.md: листы → разделы → группы меню, предметы вне меню, прочие инструменты."""
    rows = _rows(catalog, order)
    markdown = _Markdown(catalog)
    for sheet, sections in _by_sheet(roots).items():
        if sheet in ITEM_SHEETS:
            markdown.sheet(sheet, sections, rows)
    markdown.outside()
    lines = markdown.lines + others_lines(catalog)
    write_text(CATALOG_MD, "\n".join(lines))
