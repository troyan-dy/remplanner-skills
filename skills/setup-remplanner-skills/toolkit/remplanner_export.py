#!/usr/bin/env python3
"""remplanner_export.py [<name>.json ...] — планировка → RemPlanner .plan (v3): стены, двери, окна, мебель.

Без аргументов экспортирует plan/*.json и все серии концепций concepts/<серия>/*.json (пути от корня
проекта — родителя папки tools/). Результат — <name>.plan рядом с JSON. Формат JSON —
tools/reference/PLAN_FORMAT.md.
Координаты RemPlanner: см, отображаемая ориентация, y вниз, центр плана в (0,0); JSON с meta.mirror_vertical
отражается по вертикали.
Несущие стены строятся из walls_bearing: прямоугольник → осевая линия вдоль длинной стороны, толщина —
короткая сторона; куски одной стены, разделённые проёмом, сливаются; концы стыкуются вместе с перегородками
(угол — узел на пересечении осей, Т-примыкание — конец на грани проходящей стены).
Перегородки строятся из partitions: куски одной линии, разделённые дверными проёмами, сливаются.
Мебель экспортируется только с полем "rp" (см. planlib.rp и rp_lib.CATALOG).
Семантика полей проверена импортом тестовых планов (см. tools/reference/REMPLANNER_V3_SCHEMA.md).
"""

import glob
import os
import sys

from rpkit.export_plan import export
from rpkit.paths import ROOT


def plan_files(argv):
    """Планы из аргументов, без них — plan/*.json и concepts/*/*.json проекта."""
    if argv:
        return argv
    as_is = sorted(glob.glob(os.path.join(ROOT, "plan", "*.json")))
    series = glob.glob(os.path.join(ROOT, "concepts", "*", "*.json"))
    return as_is + sorted(series)


def main(argv):
    """Выгрузить каждый план."""
    files = plan_files(argv)
    if not files:
        root = os.path.abspath(ROOT)
        sys.exit(f"нет планов: plan/*.json и concepts/*/*.json в {root} пусты")
    for path in files:
        export(path)


if __name__ == "__main__":
    main(sys.argv[1:])
