"""Унитаз и раковина: от оси прибора до препятствия слева и справа (wc_side, sink_side)."""

from rpkit.layout_sweep import sweep

AXIS_CM = (2, 2)
RECT = "rect"


def _right_hand(layout, face):
    """Направление «справа» от стоящего лицом к прибору (взгляд — (-fx, -fy)), в осях JSON (y вниз);
    JSON отражён по вертикали (mirror_vertical) — стороны меняются местами, как на снимке RemPlanner."""
    right = (face[1], -face[0])
    if layout.plan.get("meta", {}).get("mirror_vertical"):
        return (-right[0], -right[1])
    return right


def _half_width(rect, face):
    """Половина ширины прибора по фасаду."""
    if face[0] == 0:
        return rect[2] / 2
    return rect[3] / 2


def _measured(layout, piece, face, side):
    """От оси прибора до препятствия в сторону side: половина ширины + свободно за боком."""
    rect = piece[RECT]
    free = sweep(layout, rect, side, AXIS_CM)
    return round(_half_width(rect, face) + free)


def fixture_sides(layout, piece, rule, face):
    """Находки <wc|sink>_side «слева» и «справа»."""
    right = _right_hand(layout, face)
    sides = (
        ("слева", (-right[0], -right[1])),
        ("справа", right),
    )
    side_rule = rule.replace("front", "side")
    return [
        (side_rule, f"{piece['id']} {word}", _measured(layout, piece, face, side))
        for word, side in sides
    ]
