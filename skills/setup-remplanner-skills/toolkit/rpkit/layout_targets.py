"""Цели проходов: зоны, место стоящего человека перед предметом, обе стороны межкомнатных дверей."""

from rpkit.layout_door_targets import door_targets
from rpkit.layout_entry import is_entry
from rpkit.layout_kinds import FRONT, specs
from rpkit.layout_obstacles import no_target
from rpkit.layout_roles import bed_fronts
from rpkit.layout_sweep import sweep

PASS_ANY = "pass_any"
SMALL_FACE_CM = 50  # предмет с фасадом уже — встать перед ним можно и со сдвигом вдоль фасада (миски, лоток)
STAND_CM = 30  # место стоящего — в 30 см от лицевой грани
DOUBLE_BED_CM = 140  # кровать с изголовьем не уже — двуспальная: оба длинных бока
HEAD_CM = 55  # у изголовья — тумбы: бока меряются без этих см
EDGE_CM = 5
MARK_CM = 4  # цель — полоска шириной 4 см
INSET_CM = 10  # цель короче грани на 10 см с каждого края
RECT = "rect"
SIDES_ALONG_X = ((0, 1), (0, -1))
SIDES_ALONG_Y = ((1, 0), (-1, 0))


def _bed_layout(back):
    """(вдоль ли x длина кровати, отступы sweep по краям бока: у изголовья — HEAD_CM)."""
    along_x = FRONT[back][0] != 0
    if back in ("left", "up"):
        return along_x, (HEAD_CM, EDGE_CM)
    return along_x, (EDGE_CM, HEAD_CM)


def bed_sides(layout, piece):
    """Бока кровати [(сторона, (lo, hi))] для зон и целей: двуспальная (изголовье ≥ 140) — оба длинных бока,
    односпальная — один, более свободный (второй обычно у стены). lo, hi — отступы sweep по краям бока."""
    along_x, margins = _bed_layout(specs(piece)[0]["back"])
    sides = list(SIDES_ALONG_X if along_x else SIDES_ALONG_Y)
    head = piece[RECT][3] if along_x else piece[RECT][2]
    if head < DOUBLE_BED_CM:
        sides = [max(
            sides,
            key=lambda side: sweep(layout, piece[RECT], side, margins),
        )]
    return [(side, margins) for side in sides]


def _stand_line(rect, side):
    """(координата полоски поперёк грани, начало и длина грани вдоль неё) перед гранью rect со стороны side;
    перед узким (< SMALL_FACE_CM) предметом — и со сдвигом вдоль фасада: в углу к миске подходят сбоку."""
    across = 0 if side[0] else 1
    start = rect[across]
    if side[across] > 0:
        stand = start + rect[across + 2] + STAND_CM
    else:
        stand = start - STAND_CM
    face_start = rect[1 - across]
    face = rect[3 - across]
    if face < SMALL_FACE_CM:
        return stand, face_start + face / 2 - SMALL_FACE_CM / 2, SMALL_FACE_CM
    return stand, face_start, face


def _stand_rect(rect, side):
    """Полоска, где стоит человек перед гранью rect со стороны side."""
    stand, face_start, face = _stand_line(rect, side)
    length = max(face - 2 * INSET_CM, MARK_CM)
    if side[0]:
        return [stand - 2, face_start + INSET_CM, MARK_CM, length]
    return [face_start + INSET_CM, stand - 2, length, MARK_CM]


def _faces(layout, piece, spec_rp):
    """Стороны, перед которыми стоят: лицевая, у кровати — длинные бока (у двуспальной оба)."""
    face = FRONT[spec_rp["back"]]
    if bed_fronts(spec_rp["name"]):
        return [side for side, _ in bed_sides(layout, piece)]
    return [face]


def _furniture_targets(layout, piece, attached):
    """Место перед предметом: перед лицевой гранью, у кровати — у боков."""
    sides = _faces(layout, piece, attached[0])
    named = []
    for number, side in enumerate(sides, start=1):
        suffix = f" сторона {number}" if len(sides) > 1 else ""
        named.append(
            (f"{piece['id']}{suffix}", _stand_rect(piece[RECT], side), PASS_ANY),
        )
    return named


def targets(layout):
    """(имя, rect, правило): зоны, место перед предметом, обе стороны межкомнатных дверей."""
    plan = layout.plan
    found = [
        (f"зона {zone['id']}", zone[RECT], PASS_ANY)
        for zone in plan.get("zones", [])
    ]
    for piece in plan["furniture"]:
        attached = specs(piece)
        if attached and not no_target(attached[0]):
            found.extend(_furniture_targets(layout, piece, attached))
    for door in plan["doors"]:
        if not is_entry(door):
            found.extend(door_targets(door))
    return found
