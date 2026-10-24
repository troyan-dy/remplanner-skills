"""Двери и проёмы без полотна выгрузки."""

from rpkit.export_openings import door_ends, find_wall
from rpkit.frozen import frozen
from rpkit.rp_door import DOOR_HEIGHT_CM, door
from rpkit.rp_geometry import ends_of, wall_frame

# doors[].kind → тип проёма RemPlanner. Входная дверь помечается полем "entry": true, экспортёр его не читает;
# kind "entry" по ошибке всё равно выгружается обычной дверью, а не несуществующим типом.
DOOR_TYPE = frozen({"entry": "single"})


def place_doors(plan, walls_by_seg, door_mid, used_doors, frame):
    """Двери и проёмы без полотна (кроме дверей балконных блоков) на стены."""
    for opening in plan["doors"]:
        if opening["id"] not in used_doors:
            _place_door(opening, walls_by_seg, door_mid, frame)


def _place_door(opening, walls_by_seg, door_mid, frame):
    label = f"doors {opening['id']}"
    _, host = find_wall(walls_by_seg, door_mid[opening["id"]], label, frame)
    ends = door_ends(host, opening, frame)
    kind = opening.get("kind", "single")
    door(
        host,
        (min(ends), opening["width"]),
        opening.get("h", DOOR_HEIGHT_CM),
        DOOR_TYPE.get(kind, kind),
        _opening_code(host, opening, ends, frame),
    )


def _opening_code(host, opening, ends, frame):
    """opening RemPlanner «<сторона полотна>-<петля>»: петля l — у p1 стены."""
    hinge_side = "l" if ends[0] < ends[1] else "r"
    return f"{_swing_side(host, opening, frame)}-{hinge_side}"


def _swing_side(host, opening, frame):
    """Сторона стены (l|r), куда открывается полотно; нормаль l = (uy, -ux). При отражении y зеркалится."""
    axis = wall_frame(*ends_of(host), host["depth"])
    swing_x, swing_y = opening["swing"]
    if frame.mirror:
        swing_y = -swing_y
    toward_left = swing_x * axis.unit_y + swing_y * (-axis.unit_x)
    return "l" if toward_left > 0 else "r"
