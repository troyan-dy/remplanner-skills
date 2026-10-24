"""Файл .plan целиком: стены и предметы в шаблоне RemPlanner, габарит чертежа, запись на диск."""

import copy

from rpkit.jsonfile import read_json, write_json
from rpkit.paths import TEMPLATE_PLAN
from rpkit.rp_wall import HEIGHT

FACES = ("l1", "l2", "r1", "r2")
DRAWING_ORDER = ("l2", "r2", "r1", "l1")  # контур стены в plan.drawings


def new_plan(walls, pieces=(), pillars=()):
    """План .plan из стен (с проёмами), предметов и колонн по шаблону remplanner_example_v3_one_wall.plan."""
    document = copy.deepcopy(read_json(TEMPLATE_PLAN))
    plan = document["plan"]
    plan["walls"] = {wall["id"]: wall for wall in walls}
    plan["items"] = {piece["id"]: piece for piece in pieces}
    plan["pillars"] = {pillar["id"]: pillar for pillar in pillars}
    plan["drawings"] = [
        [wall[face] for face in DRAWING_ORDER] for wall in walls
    ]
    plan["drawing"] = _drawing(walls)
    plan["total_height"] = HEIGHT
    return document


def _xy(x_cm, y_cm):
    return {"x": x_cm, "y": y_cm}


def _drawing(walls):
    """Габарит чертежа по граням стен."""
    corners = [wall[face] for wall in walls for face in FACES]
    left = min(corner["x"] for corner in corners)
    right = max(corner["x"] for corner in corners)
    top = min(corner["y"] for corner in corners)
    bottom = max(corner["y"] for corner in corners)
    return {
        "x_min": left,
        "x_max": right,
        "y_min": top,
        "y_max": bottom,
        "cx": (left + right) / 2,
        "cy": (top + bottom) / 2,
        "center": _xy((left + right) / 2, (top + bottom) / 2),
        "tl_point": _xy(left, top),
        "br_point": _xy(right, bottom),
        "width": right - left,
        "height": bottom - top,
    }


def dump_plan(plan, path):
    """Запись .plan: компактный JSON без экранирования кириллицы."""
    write_json(path, plan, ensure_ascii=False, separators=(",", ":"))
