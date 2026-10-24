"""Предметы плана для правил жильцов: rp предмета, имя по шаблону, фасад, вхождение в комнату."""

import re

ALONG_X = ("up", "down")  # спинка вверх или вниз — фасад вдоль x
RECT = "rect"


def specs(piece):
    """rp предмета списком (rp — объект или список)."""
    attached = piece.get("rp")
    if not attached:
        return []
    return attached if isinstance(attached, list) else [attached]


def has(piece, patterns, modules=False):
    """Предмет подходит под шаблоны: имя любого rp (или, при modules, модуль kitchen_run) — re.search."""
    for spec_rp in specs(piece):
        names = [spec_rp["name"]]
        if modules:
            names.extend(spec_rp.get("modules", []))
        if any(_found(pattern, names) for pattern in patterns):
            return True
    return False


def _found(pattern, names):
    return any(re.search(pattern, name) for name in names)


def front(piece):
    """(ширина фасада, глубина) по спинке."""
    width, height = piece[RECT][2:]
    back = specs(piece)[0]["back"]
    return (width, height) if back in ALONG_X else (height, width)


def inside(piece, room):
    """Центр предмета — в rect комнаты (включая границу)."""
    x_cm, y_cm, width, height = piece[RECT]
    room_rect = room[RECT]
    if not within(x_cm + width / 2, room_rect, 0):
        return False
    return within(y_cm + height / 2, room_rect, 1)


def within(number, rect, axis_index):
    """number между началом и концом rect по оси (0 — x, 1 — y)."""
    start = rect[axis_index]
    return start <= number <= start + rect[axis_index + 2]
