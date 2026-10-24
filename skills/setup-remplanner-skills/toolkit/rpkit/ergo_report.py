"""Текст по итогу эргономики: отчёт check_layout и markdown-таблица правил для ERGONOMICS.md."""

from typing import NamedTuple

from rpkit.ergo_judge import HARD, OK, ROWS, SOFT, STRUCT, UNJUST

_REASON = "reason"  # в конце строки — обоснование уступки
_BEARING = "bearing"  # в конце строки — пометка, если горлышко между несущими
# находки по разделам итога: (раздел, начало строки, что в конце)
_PROBLEMS = (
    (HARD, "  ✗ ниже минимума: ", _BEARING),
    (UNJUST, "  ? уступка без обоснования: ", None),
)
_ACCEPTED = ((SOFT, "  ~ уступка: ", _REASON), (STRUCT, "  ≈ из-за несущего: ", _REASON))
_BEARING_TAIL = " — горлышко между двумя несущими стенами"


class Detail(NamedTuple):
    """Подробность отчёта: waivers — и принятые уступки, verbose — ещё и пройденные правила."""

    verbose: bool
    waivers: bool


def describe(rule, measured):
    """«правило значение единицы (жел. …, мин …)»."""
    limit = "без мин."
    if rule.min is not None:
        limit = f"мин {rule.min}"
    return f"{rule.id} {measured} {rule.unit} (жел. {rule.want}, {limit})"


def _headline(name, verdict, budget):
    status = "ok" if verdict[OK] else "НЕ ПРОХОДИТ"
    waived = len(verdict[SOFT]) + len(verdict[UNJUST])
    head = f"{name}: {status} · уступок {waived}, балл {verdict['score']} из {budget}"
    if verdict.get(STRUCT):
        head = f"{head} (и {len(verdict[STRUCT])} из-за несущего)"
    return head


def _finding(lead, row, rules):
    """«<lead><объект> — <правило значение …>» для строки итога (правило, объект, значение, …)."""
    measured = describe(rules[row[0]], row[2])
    return f"{lead}{row[1]} — {measured}"


def _section_lines(verdict, sections, rules):
    lines = []
    for section, lead, ending in sections:
        rows = verdict.get(section, [])
        lines.extend(
            _row_line(lead, row, ending, rules) for row in rows
        )
    return lines


def _row_line(lead, row, ending, rules):
    line = _finding(lead, row, rules)
    if ending == _REASON:
        return f"{line} — {row[3]}"
    if ending == _BEARING and row[3] is not None:
        return f"{line}{_BEARING_TAIL}"
    return line


def report(name, verdict, detail, rulebook):
    """Отчёт по плану — см. ergonomics.report."""
    rules = rulebook.rules
    lines = [_headline(name, verdict, rulebook.budget)]
    lines.extend(_section_lines(verdict, _PROBLEMS, rules))
    if detail.waivers or detail.verbose:
        lines.extend(_section_lines(verdict, _ACCEPTED, rules))
    for key in verdict["unused"]:
        lines.append(f"  · обоснование не нужно (нарушения нет): {key}")
    if verdict["score"] > rulebook.budget:
        lines.append(f"  ✗ уступок больше бюджета: {verdict['score']} > {rulebook.budget}")
    if detail.verbose:
        passed = (row for row in verdict[ROWS] if row[3] == OK)
        lines.extend(_finding("    ok ", row, rules) for row in passed)
    return "\n".join(lines)
