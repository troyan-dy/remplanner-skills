#!/usr/bin/env python3
"""as_is.py — пример плана «как есть» (обезличенная однокомнатная квартира) → plan/as_is.json.

Образец для src/as_is.py проекта: так переносят план БТИ в JSON. Внешний контур 700×620, наружная стена
сверху (окно), межквартирные по остальным сторонам, вход снизу. Комната с кухней 650×350 у окна, ниже —
санузел 260×210 и прихожая 380×210. Площади «по БТИ» здесь условные."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from planlib import D, F, ROOT, W, area, bearing, fixed, room, save, skeleton, waive, window, zone  # noqa: E402

LIVING = [25, 25, 650, 350]
BATH = [25, 385, 260, 210]
HALL = [295, 385, 380, 210]


def as_is():
    p = skeleton("Пример: однокомнатная квартира «как есть»", 270, "пример набора, не реальная квартира")
    p["walls_bearing"] += [
        bearing("outer-top", [0, 0, 700, 25], "facade", "окно комнаты"),
        bearing("outer-bottom", [0, 595, 700, 25], "interapartment", "в подъезд"),
        bearing("outer-left", [0, 0, 25, 620], "interapartment"),
        bearing("outer-right", [675, 0, 25, 620], "interapartment"),
    ]
    p["partitions"] += [
        W("room-hall", [25, 375, 650, 10], "комната / санузел и прихожая"),
        W("bath-hall", [285, 385, 10, 210], "санузел / прихожая"),
    ]
    p["windows"].append(window("win-room", [250, 0, 180, 25], h=150, sill=85))
    p["doors"] += [
        D("door-entry", 90, [650, 595], [560, 595], [0, -1], "входная", entry=True),
        D("door-room", 80, [385, 375], [305, 375], [0, -1], "из прихожей в комнату"),
        D("door-bath", 80, [285, 475], [285, 395], [-1, 0], "в санузел, внутрь"),
    ]
    p["fixed_elements"] += [
        fixed("riser", "riser", point=[270, 585], name="стояки В/К"),
        fixed("drain", "drain", point=[250, 585], name="подключение канализации"),
    ]
    p["furniture"] += [
        F("wc", [217, 530, 38, 65], "унитаз", "toilet", "down"),
        F("bathtub", [25, 525, 160, 70], "ванна 160", "bathtub", "down"),
        F("sink", [25, 385, 60, 50], "раковина", "sink_box_floor", "up"),
        F("washer", [95, 385, 60, 45], "стиральная машина", "washing_machine", "up"),
        F("fridge", [615, 25, 60, 60], "холодильник 60", "fridge", "right"),
        F("kitchen", [615, 85, 60, 290], "кухня: тумба, мойка, тумба, плита", "kitchen_run", "right",
          modules=["box", "sink", "box", "stove"]),
        F("table", [400, 200, 80, 80], "стол", "table", "up"),
        F("sofa", [35, 160, 95, 215], "диван", "sofa_triple", "left"),
        F("ward", [25, 25, 220, 60], "шкаф", "ward_coupe", "up"),
        F("hall-ward", [305, 535, 120, 60], "шкаф в прихожей", "ward_coupe", "down"),
        F("bench", [635, 400, 40, 80], "банкетка", "banquet_shelf_shoes", "right"),
        F("mirror", [669, 400, 6, 60], "зеркало над банкеткой", "bathroom_mirror", "right", over_floor=100),
    ]
    p["zones"] += [
        zone("z-wc", [217, 465, 38, 65], "перед унитазом"),
        zone("z-sink", [25, 435, 60, 70], "перед раковиной"),
    ]
    p["rooms"] += [
        room("kitchen-living", "Комната с кухней", area(LIVING), LIVING, bti=22.8),
        room("bath", "Санузел", area(BATH), BATH, bti=5.4),
        room("hall", "Прихожая", area(HALL), HALL, bti=8.0),
    ]
    waive(p, sink_hob="кухня 290 между окном и перегородкой: мойка и плита через тумбу 60, зато холодильник в линии")
    return p


if __name__ == "__main__":
    save({"as_is": as_is()}, os.path.join(ROOT, "plan"))
