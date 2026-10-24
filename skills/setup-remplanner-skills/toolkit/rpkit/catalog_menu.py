"""Разбор дерева меню RemPlanner: tools/reference/remplanner_catalog_menu.txt."""

from typing import NamedTuple, Optional

from rpkit.jsonfile import read_lines
from rpkit.paths import MENU

UNGROUPED = "U "  # строка U: предметы вне групп по разделам
PRO_LINE = "P "  # строка P: id предметов с классом is_pro
SKIPPED = ("#", UNGROUPED, PRO_LINE, "RP ")


class MenuEntry(NamedTuple):
    """Предмет меню: раздел, группа ("" — вне групп), id инструмента, другое имя в меню, описание."""

    root_id: int
    group: str
    tool_id: int
    alias: Optional[str]
    desc: str


def _id_set(text):
    return {int(number) for number in text.split(",")}


def _strip_pro(text, mark):
    """(название без пометки PRO, была ли пометка)."""
    if text.endswith(mark):
        return text[:-len(mark)], True
    return text, False


def _markers(lines):
    """Предметы вне групп {раздел: {id}} (строки U) и id PRO (последняя строка P)."""
    ungrouped, pro_ids = {}, set()
    for line in lines:
        if line.startswith(UNGROUPED):
            ungrouped.update(_ungrouped(line[len(UNGROUPED):]))
        elif line.startswith(PRO_LINE):
            pro_ids = _id_set(line[len(PRO_LINE):])
    return ungrouped, pro_ids


def _ungrouped(text):
    """«раздел:id,id раздел:id…» → {раздел: {id}}."""
    pairs = (chunk.split(":") for chunk in text.split())
    return {int(root_id): _id_set(ids) for root_id, ids in pairs}


class _MenuReader:
    """Разделы, группы и предметы меню по строкам файла."""

    def __init__(self, ungrouped):
        self.ungrouped = ungrouped
        self.roots = {}
        self.entries = []
        self.group = None

    def read(self, line):
        """Строка раздела (R|), группы (G|) или предмета."""
        if line.startswith("R|"):
            _, root_id, title, sheets = line.split("|", 3)
            title, pro = _strip_pro(title, "PRO")
            self.roots[int(root_id)] = (title, pro, sheets.split(","))
        elif line.startswith("G|"):
            _, root_id, group = line.split("|", 2)
            group, pro = _strip_pro(group, " PRO")
            self.group = (int(root_id), group, pro)
        else:
            self._read_entry(line)

    def _read_entry(self, line):
        head, _, desc = line.partition("|")
        tool_id, _, alias = head.partition("=")
        self._add_entry(int(tool_id), alias or None, desc)

    def _add_entry(self, tool_id, alias, desc):
        """Предмет в текущей группе, а если он в строке U своего раздела — без группы ("")."""
        root_id, group, _ = self.group
        if tool_id in self.ungrouped.get(root_id, ()):
            group = ""
        self.entries.append(MenuEntry(root_id, group, tool_id, alias, desc))


def parse_menu(path=MENU):
    """→ (roots {id: (title, pro, sheets)}, entries [(root_id, group, id, alias, desc)], pro_ids)
    Предметы из строки U (вне групп) получают группу ""; PRO — по классу is_pro предмета (строка P)."""
    lines = read_lines(path)
    ungrouped, pro_ids = _markers(lines)
    reader = _MenuReader(ungrouped)
    for line in lines:
        if line and not line.startswith(SKIPPED):
            reader.read(line)
    return reader.roots, reader.entries, pro_ids
