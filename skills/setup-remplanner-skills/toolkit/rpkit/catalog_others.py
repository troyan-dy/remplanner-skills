"""Раздел справочника о прочих инструментах каталога (не plan.items)."""

import itertools

IN_ITEMS = "in_items"
TITLE = "title"


def others_lines(catalog):
    """Прочие инструменты (не plan.items) по группам."""
    groups = {}
    for name, record in catalog.items():
        if not record[IN_ITEMS]:
            label = f"`{name}` {record[TITLE]}"
            groups.setdefault(record["group"], []).append(label)
    lines = ["## Прочие инструменты (не plan.items, схема не получена)", ""]
    lines.extend(itertools.starmap(_group_line, sorted(groups.items())))
    lines.append("")
    return lines


def _group_line(group, names):
    joined = "; ".join(names)
    return f"- **{group}** ({len(names)}): {joined}"
