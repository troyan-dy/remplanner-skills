"""Запись .plan рядом с JSON и итог выгрузки."""

import os

from rpkit.catalog_store import confirmed_names
from rpkit.console import say
from rpkit.paths import ROOT
from rpkit.rp_plan import dump_plan, new_plan


def out_path(path):
    """<name>.json → <name>.plan в той же папке."""
    stem = os.path.splitext(os.path.abspath(path))[0]
    return f"{stem}.plan"


def write_plan(path, walls, pieces):
    """.plan из стен и предметов → рядом с JSON; печатает итог и предметы, ещё не подтверждённые импортом."""
    target = out_path(path)
    dump_plan(new_plan(walls, pieces), target)
    stem = os.path.splitext(os.path.basename(path))[0]
    holes = sum(
        len(host.get("holes", {})) for host in walls
    )
    counts = f"стен {len(walls)}, проёмов {holes}, предметов {len(pieces)}"
    relative = os.path.relpath(target, ROOT)
    say(f"{stem}: {counts} → {relative}")
    _report_unconfirmed(pieces)


def _report_unconfirmed(pieces):
    """Предметы, которых нет среди подтверждённых импортом (CATALOG и confirmed.json)."""
    names = {piece["name"] for piece in pieces}
    unconfirmed = sorted(names - confirmed_names())
    if unconfirmed:
        listed = ", ".join(unconfirmed)
        say(f"  · не подтверждены импортом (проверить на снимке, затем python3 tools/rp_catalog.py confirm <name>): {listed}")
