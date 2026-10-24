"""Выгрузка одного плана JSON в .plan RemPlanner."""

import os

from rpkit.catalog_names import check_names
from rpkit.export_doors import place_doors
from rpkit.export_frame import PlanFrame
from rpkit.export_furniture import furniture_items
from rpkit.export_walls import build_walls, door_middles
from rpkit.export_windows import place_windows
from rpkit.export_write import write_plan
from rpkit.jsonfile import read_json
from rpkit.rp_ids import reset_ids


def export(path):
    """План JSON → .plan рядом; печатает итог и предметы, ещё не подтверждённые импортом."""
    plan = read_json(path)
    check_names(plan, path)
    stem = os.path.splitext(os.path.basename(path))[0]
    reset_ids(stem)  # стабильные id: перегенерация без изменений даёт тот же файл
    frame = PlanFrame.from_plan(plan)
    walls = [host for _, host in _walls_with_openings(plan, frame)]
    write_plan(path, walls, furniture_items(plan, frame))


def _walls_with_openings(plan, frame):
    doors = {door["id"]: door for door in plan["doors"]}
    middles = door_middles(plan, frame)
    walls_by_seg = build_walls(plan, frame, middles)
    used_doors = place_windows(plan, walls_by_seg, doors, frame)
    place_doors(plan, walls_by_seg, middles, used_doors, frame)
    return walls_by_seg
