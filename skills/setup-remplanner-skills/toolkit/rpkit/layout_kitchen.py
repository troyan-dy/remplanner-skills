"""Кухня (kitchen_run): столешница по бокам плиты, между мойкой и плитой, рабочий треугольник, плита — окно."""

from rpkit.layout_hob_window import hob_windows
from rpkit.layout_kinds import kind
from rpkit.layout_kitchen_run import KitchenRun
from rpkit.layout_work_triangle import work_triangle


def _hob_sides(run, label):
    """hob_side и hob_side_big по каждой плите линии."""
    found = []
    for stove in run.stoves:
        sides = (
            run.counter_left(stove[2]),
            run.counter_right(stove[3]),
        )
        found.append(("hob_side", f"{label} плита: меньшая сторона", min(sides)))
        found.append(("hob_side_big", f"{label} плита: большая сторона", max(sides)))
    return found


def _gap(sink, stove):
    """Столешница между мойкой и плитой."""
    if stove[2] >= sink[3]:
        return stove[2] - sink[3]
    return sink[2] - stove[3]


def _run_findings(run):
    """Столешница у плит линии, затем sink_hob — по каждой паре мойка–плита."""
    label = run.piece["id"]
    found = _hob_sides(run, label)
    for sink in run.sinks:
        found.extend(
            ("sink_hob", f"{label} мойка–плита", _gap(sink, stove))
            for stove in run.stoves
        )
    return found


def measure_kitchen(layout):
    """Находки по кухне: по каждой линии, затем треугольник (первые мойка, плита и холодильник), плита — окно."""
    furniture = layout.plan["furniture"]
    runs = [KitchenRun(piece) for piece in furniture if kind(piece) == "kitchen_run"]
    found = []
    for run in runs:
        found.extend(_run_findings(run))
    return found + work_triangle(furniture, runs) + hob_windows(layout.plan, runs)
