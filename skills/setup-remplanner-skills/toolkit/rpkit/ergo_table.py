"""Markdown-таблица правил эргономики для tools/reference/ERGONOMICS.md (python3 tools/ergonomics.py)."""

_TABLE_HEAD = (
    "| id | что | мин. допустимо | желательно | ед. | вес | источник |",
    "|---|---|---|---|---|---|---|",
)


def table(rules):
    """Markdown-таблица правил."""
    return "\n".join([*_TABLE_HEAD, *map(_table_row, rules)])


def _table_row(rule):
    sign = "≥" if rule.sense == "ge" else "≤"
    lowest = "—"
    if rule.min is not None:
        lowest = f"{sign} {format(rule.min, 'g')}"
    cells = (
        f"`{rule.id}`",
        rule.what,
        lowest,
        f"{sign} {format(rule.want, 'g')}",
        rule.unit,
        format(rule.weight, "g"),
        rule.src,
    )
    inner = " | ".join(cells)
    return f"| {inner} |"
