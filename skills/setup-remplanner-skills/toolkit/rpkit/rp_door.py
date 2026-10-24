"""Дверь или проём без двери на стене .plan."""

from rpkit.rp_hole import hole_geometry
from rpkit.rp_attach import attach, hole_link

DOOR_HEIGHT_CM = 210
FRAME_DEPTH_CM = 4  # коробка двери
FRAME_SHIFT_CM = 3  # коробка распашной двери сдвинута от оси стены в сторону r
SINGLE = "single"


def door(host, opening_span, height=DOOR_HEIGHT_CM, kind=SINGLE, opening="r-l"):
    """kind: single (дверь стандартная) | doorway (проём без двери); opening_span = (t0, ширина) на стене host."""
    start, width = opening_span
    single = kind == SINGLE
    shift = FRAME_SHIFT_CM if single else 0
    record = {
        "plan": "a",
        "type": kind,
        "group": "doors",
        "width": width,
        "height": height,
        "depth": FRAME_DEPTH_CM,
        "opening": opening,
        **hole_link(host),
        "position": "r" if single else "c",
        "offset": shift,
        "slope_angle": 0,
        "casing": 1 if single else 0,
        "casements": 1,
        "p1corner": 0,
        "p2corner": 0,
        "f0offset": 0,
        "room_l": "",
        "room_r": "",
    }
    record.update(hole_geometry(host, (start, start + width), FRAME_DEPTH_CM, shift))
    return attach(host, record)
