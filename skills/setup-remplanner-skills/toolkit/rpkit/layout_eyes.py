"""Глаза сидящего на диване или лежащего на кровати — точка, от которой меряется дистанция до ТВ."""

from rpkit.layout_kinds import kind
from rpkit.layout_roles import is_bed

BED_EYES_CM = 35  # глаза: в 35 см от изголовья кровати
SOFA_EYES_CM = 40  # и в 40 см от спинки дивана


def _from_back(rect, axis, direction, offset):
    """Координата глаз по оси места: offset от спинки (спинка — со стороны, обратной direction)."""
    start, size = rect[axis], rect[axis + 2]
    return (start + offset) if direction > 0 else (start + size - offset)


def _middle(rect, axis):
    """Середина прямоугольника по оси."""
    return rect[axis] + rect[axis + 2] / 2


def seat_eyes(seat, face):
    """Глаза: на оси места в BED_EYES_CM (кровать) или SOFA_EYES_CM (диван) от спинки, посередине поперёк."""
    rect = seat["rect"]
    offset = BED_EYES_CM if is_bed(kind(seat)) else SOFA_EYES_CM
    axis = 0 if face[0] else 1
    eyes = [_middle(rect, 0), _middle(rect, 1)]
    eyes[axis] = _from_back(rect, axis, face[axis], offset)
    return tuple(eyes)
