"""Окно и балконный блок (дверь + окно) на стене .plan."""

from rpkit.rp_geometry import WallAxis
from rpkit.rp_hole import hole_geometry
from rpkit.rp_attach import attach, hole_link

FRAME_DEPTH_CM = 6  # рама окна и балконного блока
WINDOOR_FLOOR_CM = 10  # порог балконного блока
DOOR_MARK_CM = 3  # метки lc/rc стыка двери и окна — по 3 см от оси
LABEL_GAP_CM = 26  # подпись балконного блока pc2h — за гранью l


def _sill():
    return {"thinkness": 4, "overhang": 0, "overmeasure": 0, "side": "r"}


def window(host, opening_span, height, sill, casements=1):
    """Окно: opening_span = (t0, ширина) на стене host, height — высота, sill — высота подоконника."""
    start, width = opening_span
    geometry = hole_geometry(host, (start, start + width), FRAME_DEPTH_CM, 0)
    record = {
        "plan": "a",
        "type": "window",
        "group": "windows",
        "width": width,
        "height": height,
        "depth": FRAME_DEPTH_CM,
        "floor_height": sill,
        "slopes": 20,
        "opening": "r-l",
        **hole_link(host),
        "position": "c",
        "offset": 0,
        "slope_angle": 0,
        "casing": 1,
        "casements": casements,
        "sill": _sill(),
        "room_l": "",
        "room_r": "",
        "p1corner": 0,
        "p2corner": 0,
    }
    record.update(geometry)
    return attach(host, record)


def windoor(host, start, door_size, window_size, door_position="l"):
    """Балконный блок: door_size и window_size — (ширина, высота) двери и окна.
    В образце door_position 'l' = дверь у p1 проёма (connection_point = p1 + door_width)."""
    width = door_size[0] + window_size[0]
    geometry = hole_geometry(host, (start, start + width), FRAME_DEPTH_CM, 0)
    record = {
        "plan": "a",
        "type": "windoor",
        "group": "windows",
        "width": width,
        "depth": FRAME_DEPTH_CM,
        "window_width": window_size[0],
        "window_height": window_size[1],
        "door_width": door_size[0],
        "door_height": door_size[1],
        "door_position": door_position,
        "opening": "r-l",
        **hole_link(host),
        "position": "c",
        "offset": 0,
        "floor_height": WINDOOR_FLOOR_CM,
        "slope_angle": 0,
        "casing": 1,
        "casements": 1,
        "sill": _sill(),
        "room_l": "",
        "room_r": "",
        "p1corner": 0,
        "p2corner": 0,
    }
    widths = (door_size[0], window_size[0])
    record.update(_joint_points(host, start, widths, door_position))
    record.update(geometry)
    return attach(host, record)


def _joint_at(start, widths, door_position):
    """Параметр стыка двери и окна и середины окна (для подписи) вдоль стены."""
    door_width, window_width = widths
    if door_position == "l":
        width = door_width + window_width
        return start + door_width, (start + door_width + start + width) / 2
    return start + window_width, (start + start + window_width) / 2


def _joint_points(host, start, widths, door_position):
    """Точки стыка двери и окна (lc, rc, connection_point, pcl, pcr) и подписи pc2h."""
    axis = WallAxis(host)
    joint, label_at = _joint_at(start, widths, door_position)
    return {
        "lc": axis.point(joint, DOOR_MARK_CM),
        "rc": axis.point(joint, -DOOR_MARK_CM),
        "connection_point": axis.point(joint),
        "pcl": axis.point(joint, axis.half),
        "pcr": axis.point(joint, -axis.half),
        "pc2h": axis.point(label_at, axis.half + LABEL_GAP_CM),
    }
