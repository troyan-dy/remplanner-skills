#!/usr/bin/env python3
"""as_is.py — пример плана «как есть» (обезличенная однокомнатная квартира) → plan/as_is.json.

Образец для src/as_is.py проекта: так переносят план БТИ в JSON. Внешний контур 700×620, наружная стена
сверху (окно), межквартирные по остальным сторонам, вход снизу. Комната с кухней 650×350 у окна, ниже —
санузел 260×210 и прихожая 380×210. Площади «по БТИ» здесь условные."""

import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "tools",
))
import planlib  # noqa: E402

CEILING_CM = 270
LIVING = (25, 25, 650, 350)
BATH = (25, 385, 260, 210)
HALL = (295, 385, 380, 210)
WINDOW_HEIGHT_CM = 150
WINDOW_SILL_CM = 85
ENTRY_DOOR_CM = 90
ROOM_DOOR_CM = 80
MIRROR_OVER_FLOOR_CM = 100
BTI_AREA_M2 = {"kitchen-living": 22.8, "bath": 5.4, "hall": 8.0}  # условные, пример
UP, DOWN, RIGHT = "up", "down", "right"


def walls(plan):
    """Несущие стены, перегородки, окно и двери."""
    plan["walls_bearing"] += [
        planlib.bearing("outer-top", [0, 0, 700, 25], "facade", "окно комнаты"),
        planlib.bearing("outer-bottom", [0, 595, 700, 25], "interapartment", "в подъезд"),
        planlib.bearing("outer-left", [0, 0, 25, 620], "interapartment"),
        planlib.bearing("outer-right", [675, 0, 25, 620], "interapartment"),
    ]
    plan["partitions"] += [
        planlib.W("room-hall", [25, 375, 650, 10], "комната / санузел и прихожая"),
        planlib.W("bath-hall", [285, 385, 10, 210], "санузел / прихожая"),
    ]
    plan["windows"].append(
        planlib.window("win-room", [250, 0, 180, 25], h=WINDOW_HEIGHT_CM, sill=WINDOW_SILL_CM),
    )
    plan["doors"] += [
        planlib.D(
            "door-entry", ENTRY_DOOR_CM, [650, 595], [560, 595], [0, -1], "входная",
            entry=True,
        ),
        planlib.D(
            "door-room", ROOM_DOOR_CM, [385, 375], [305, 375], [0, -1], "из прихожей в комнату",
        ),
        planlib.D(
            "door-bath", ROOM_DOOR_CM, [285, 475], [285, 395], [-1, 0], "в санузел, внутрь",
        ),
    ]
    plan["fixed_elements"] += [
        planlib.fixed("riser", "riser", point=[270, 585], name="стояки В/К"),
        planlib.fixed("drain", "drain", point=[250, 585], name="подключение канализации"),
    ]


def furniture(plan):
    """Мебель и сантехника «как есть»."""
    plan["furniture"] += [
        planlib.F("wc", [217, 530, 38, 65], "унитаз", "toilet", DOWN),
        planlib.F("bathtub", [25, 525, 160, 70], "ванна 160", "bathtub", DOWN),
        planlib.F("sink", [49, 385, 60, 40], "раковина", "sink_box_floor", UP),
        planlib.F("washer", [133, 385, 60, 45], "стиральная машина", "washing_machine", UP),
        planlib.F("fridge", [615, 25, 60, 60], "холодильник 60", "fridge", RIGHT),
        planlib.F(
            "kitchen", [615, 85, 60, 290], "кухня: тумба, мойка, тумба, плита", "kitchen_run", RIGHT,
            modules=["box", "sink", "box", "stove"],
        ),
        planlib.F("table", [400, 200, 80, 80], "стол", "table", UP),
        planlib.F("sofa", [35, 160, 95, 215], "диван", "sofa_triple", "left"),
        planlib.F("ward", [25, 25, 220, 60], "шкаф", "ward_coupe", UP),
        planlib.F("hall-ward", [305, 535, 120, 60], "шкаф в прихожей", "ward_coupe", DOWN),
        planlib.F("bench", [635, 400, 40, 80], "банкетка", "banquet_shelf_shoes", RIGHT),
        planlib.F(
            "mirror", [669, 400, 6, 60], "зеркало над банкеткой", "bathroom_mirror", RIGHT,
            over_floor=MIRROR_OVER_FLOOR_CM,
        ),
    ]


def rooms(plan):
    """Зоны перед сантехникой и помещения с площадью по БТИ."""
    plan["zones"] += [
        planlib.zone("z-wc", [217, 465, 38, 65], "перед унитазом"),
        planlib.zone("z-sink", [49, 425, 60, 70], "перед раковиной"),
    ]
    plan["rooms"] += [
        _room("kitchen-living", "Комната с кухней", LIVING),
        _room("bath", "Санузел", BATH),
        _room("hall", "Прихожая", HALL),
    ]


def _room(rid, name, rect):
    """Помещение с площадью по rect и площадью по экспликации БТИ."""
    rect = list(rect)
    square_meters = planlib.area(rect)
    return planlib.room(rid, name, square_meters, rect, bti=BTI_AREA_M2[rid])


def as_is():
    """План «как есть» примера."""
    plan = planlib.skeleton(
        "Пример: однокомнатная квартира «как есть»", CEILING_CM, "пример набора, не реальная квартира",
    )
    walls(plan)
    furniture(plan)
    rooms(plan)
    planlib.waive(
        plan, sink_hob="кухня 290 между окном и перегородкой: мойка и плита через тумбу 60, зато холодильник в линии",
    )
    return plan


if __name__ == "__main__":
    plan_dir = os.path.join(planlib.ROOT, "plan")
    planlib.save({"as_is": as_is()}, plan_dir)
