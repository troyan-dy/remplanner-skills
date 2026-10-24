"""Окна и балконные блоки выгрузки."""

from rpkit.console import say
from rpkit.export_openings import door_ends, find_wall, rect_span
from rpkit.rp_door import DOOR_HEIGHT_CM
from rpkit.rp_window import window, windoor

WINDOW_HEIGHT_CM = 150
SILL_CM = 85
HEIGHT = "h"


def place_windows(plan, walls_by_seg, doors, frame):
    """Окна и балконные блоки на стены; → id дверей, которые выгружены в составе балконных блоков."""
    used_doors = set()
    for opening in plan["windows"]:
        host, span = _host_span(opening, walls_by_seg, frame)
        if opening.get("windoor_door"):
            balcony_door = doors[opening["windoor_door"]]
            used_doors.add(balcony_door["id"])
            _place_windoor(host, opening, balcony_door, span, frame)
        else:
            _place_window(host, opening, span)
    return used_doors


def _host_span(opening, walls_by_seg, frame):
    """Стена окна (по середине его rect) и параметры окна вдоль неё."""
    rect = frame.rect_rp(opening["rect"])
    center = (
        rect[0] + rect[2] / 2,
        rect[1] + rect[3] / 2,
    )
    _, host = find_wall(walls_by_seg, center, f"windows {opening['id']}", frame)
    return host, rect_span(host, opening["rect"], frame)


def _place_window(host, opening, span):
    width = round(span[1] - span[0])
    window(
        host,
        (span[0], width),
        opening.get(HEIGHT, WINDOW_HEIGHT_CM),
        opening.get("sill", SILL_CM),
        opening.get("casements", 1),
    )


def _place_windoor(host, opening, balcony_door, span, frame):
    start = min(door_ends(host, balcony_door, frame))
    door_size = (
        balcony_door["width"],
        balcony_door.get(HEIGHT, DOOR_HEIGHT_CM),
    )
    window_size = (
        round(span[1] - span[0]),
        opening.get(HEIGHT, WINDOW_HEIGHT_CM),
    )
    windoor(host, min(span[0], start), door_size, window_size, "l")
    if start > span[0]:
        say(f"  ! {opening['id']}: дверь не у начала стены — RemPlanner поставит её у p1 (см. схему)")
