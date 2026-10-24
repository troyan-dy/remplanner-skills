"""Несущие стены выгрузки: walls_bearing → осевые линии."""

import sys

from rpkit.export_join import join
from rpkit.export_overlay import is_overlay
from rpkit.export_pieces import merge_all
from rpkit.export_segments import seg_of_rect

BEARING_KINDS = ("facade", "interapartment", "column", "bearing")
RECT = "rect"


def bearing_segs(plan, frame):
    """Несущие стены из walls_bearing → осевые линии (концы потом стыкует join() вместе с перегородками).

    1. Куски одной стены (тот же kind) сливаются (merge_pieces): стена с входной дверью обычно задана
       двумя короткими простенками, и по отдельности они легли бы поперёк стены.
    2. Тонкая накладка на грани более толстой параллельной несущей стены (is_overlay: уступ отделки,
       граница помещения для расчёта площади) отдельной стеной не строится — её место остаётся в помещении.
    3. Прямоугольник → осевая линия вдоль длинной стороны (seg_of_rect).
    4. Несущие стыкуются сначала между собой (join): каркас — узлы на осях несущих стен, и только потом
       к нему примыкают перегородки. Иначе конец несущей, не дошедший до оси соседней несущей, мог
       сойтись в угол с перегородкой, которая заканчивается рядом (стена комнаты у лоджии — с перегородкой
       коридора вместо торца лоджии)."""
    pieces = [_bearing_piece(wall) for wall in plan["walls_bearing"]]
    merge_all(pieces, _opening_centers(plan))
    segs = [
        seg_of_rect(frame.rect_rp(rect), kind)
        for rect, kind in pieces
        if not _overlay(rect, pieces)
    ]
    join(segs)
    return segs


def _overlay(rect, pieces):
    others = [other for other, _ in pieces if other is not rect]
    return is_overlay(rect, others)


def _bearing_piece(wall):
    kind = wall.get("kind", "bearing")
    if kind not in BEARING_KINDS:
        kinds = ", ".join(BEARING_KINDS)
        sys.exit(f"walls_bearing {wall.get('id')}: kind {kind!r} — нужен один из {kinds}")
    return [list(wall[RECT]), kind]


def _opening_centers(plan):
    """Середины дверей и окон в координатах JSON."""
    doors = [_door_center(door) for door in plan.get("doors", [])]
    windows = plan.get("windows", [])
    return doors + [_rect_center(window[RECT]) for window in windows]


def _door_center(door):
    hinge, other = door["hinge"], door["other"]
    middle_x = (hinge[0] + other[0]) / 2
    return middle_x, (hinge[1] + other[1]) / 2


def _rect_center(rect):
    x_cm, y_cm, width, height = rect
    return x_cm + width / 2, y_cm + height / 2
