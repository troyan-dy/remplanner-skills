"""Куски стен выгрузки: осевая линия Seg из прямоугольника, слияние кусков одной стены, накладки."""

EPS = 1e-6
TOLERANCE_CM = 1.0  # допуск попадания точки в толщу стены
STUB_CM = 10  # короткие доборы 9×10 у дверей — тоже горизонтальные куски перегородки толщиной 10
HORIZONTAL = "h"
VERTICAL = "v"


class Seg:
    """Осевая линия стены: ось h|v, координата оси offset, концы span = [a0, a1] вдоль оси, толщина depth.
    Направление концов сохраняется, как задано (важно для несущих)."""

    def __init__(self, start, end, depth, kind="partition"):
        self.depth = depth
        self.kind = kind
        horizontal = abs(start[1] - end[1]) < EPS
        self.axis = HORIZONTAL if horizontal else VERTICAL
        along = 0 if horizontal else 1
        self.offset = start[1 - along]
        self.span = [start[along], end[along]]

    @property
    def lo(self):
        """Меньший конец вдоль оси."""
        return min(self.span)

    @property
    def hi(self):
        """Больший конец вдоль оси."""
        return max(self.span)

    def ends(self):
        """(x1, y1, x2, y2) концов в порядке span."""
        if self.axis == HORIZONTAL:
            return (self.span[0], self.offset, self.span[1], self.offset)
        return (self.offset, self.span[0], self.offset, self.span[1])

    def contains(self, x_cm, y_cm, tol=TOLERANCE_CM):
        """Точка в толще стены и в её пределах вдоль оси (с допуском tol)."""
        point = (x_cm, y_cm) if self.axis == HORIZONTAL else (y_cm, x_cm)
        reach = self.depth / 2 + tol
        if abs(point[1] - self.offset) > reach:
            return False
        return self.lo - tol <= point[0] <= self.hi + tol


def seg_of_rect(rect, kind):
    """Прямоугольник (x, y, w, h) в координатах RemPlanner → осевая линия вдоль длинной стороны,
    p1 — у меньшей координаты; толщина — короткая сторона."""
    x_cm, y_cm, width, height = rect
    if width >= height or (height == STUB_CM and width < STUB_CM):
        middle = y_cm + height / 2
        return Seg((x_cm, middle), (x_cm + width, middle), height, kind)
    middle = x_cm + width / 2
    return Seg((middle, y_cm), (middle, y_cm + height), width, kind)
