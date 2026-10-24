"""Система координат выгрузки: JSON плана (y вниз, исходная ориентация) → координаты RemPlanner.

Ориентация и центр — свои у каждого плана. meta.mirror_vertical: true — план в JSON отражён относительно того,
что показывает RemPlanner (y_m = H - y); иначе y как есть. Центр плана RemPlanner (0,0) — середина габарита
несущих стен (без несущих — перегородок)."""

import sys

from rpkit.frozen import frozen

# спинка в координатах JSON при mirror_vertical → angle RemPlanner (без отражения верх и низ меняются местами)
ANGLE = frozen({
    "down": 180,
    "up": 0,
    "left": 90,
    "right": 270,
})
FLIP = frozen({"up": "down", "down": "up"})


class PlanFrame:
    """Отражение по вертикали, высота отражения и центр плана."""

    def __init__(self, mirror, height, center):
        self.mirror = mirror
        self.height = height
        self.center = center

    @classmethod
    def from_plan(cls, plan):
        """mirror — meta.mirror_vertical; высота отражения — meta.outer_height (без неё — y_min + y_max габарита
        несущих стен; на результат она не влияет — центр вычитается); центр — середина габарита."""
        rects = _wall_rects(plan)
        extent_x = _extent(rects, 0)
        mirror, height, center_y = _vertical(
            plan.get("meta", {}), _extent(rects, 1),
        )
        return cls(
            mirror,
            height,
            ((extent_x[0] + extent_x[1]) / 2, center_y),
        )

    def to_rp(self, x_cm, y_cm):
        """Точка JSON → точка RemPlanner."""
        center_x, center_y = self.center
        if self.mirror:
            return x_cm - center_x, (self.height - y_cm) - center_y
        return x_cm - center_x, y_cm - center_y

    def rect_rp(self, rect):
        """Прямоугольник JSON [x, y, w, h] → (x, y, w, h) в RemPlanner (верхний левый угол после отражения)."""
        x_cm, y_cm, width, height = rect
        if self.mirror:
            y_rp = (self.height - y_cm - height) - self.center[1]
        else:
            y_rp = y_cm - self.center[1]
        return x_cm - self.center[0], y_rp, width, height

    def to_json(self, x_cm, y_cm):
        """Точка RemPlanner → обратно в координаты JSON (для сообщений об ошибке)."""
        center_x, center_y = self.center
        if self.mirror:
            y_json = self.height - center_y - y_cm
        else:
            y_json = y_cm + center_y
        return x_cm + center_x, y_json

    def angle_of(self, back):
        """Сторона спинки в координатах JSON → angle RemPlanner (при отражении верх и низ меняются местами)."""
        if not self.mirror:
            back = FLIP.get(back, back)
        return ANGLE[back]


def _wall_rects(plan):
    """rect несущих стен, а без них — перегородок; стен нет — выход."""
    rects = [wall["rect"] for wall in plan.get("walls_bearing", [])]
    rects = rects or [wall["rect"] for wall in plan.get("partitions", [])]
    if not rects:
        sys.exit("в плане нет стен: walls_bearing и partitions пусты")
    return rects


def _vertical(meta, extent_y):
    """(отражать ли, высота отражения, y центра) по meta и габариту по y."""
    span_sum = extent_y[0] + extent_y[1]
    if not meta.get("mirror_vertical"):
        return False, 0, span_sum / 2
    height = meta.get("outer_height", span_sum)
    return True, height, height - span_sum / 2


def _extent(rects, axis_index):
    """Наименьшая и наибольшая координата прямоугольников по оси (0 — x, 1 — y)."""
    low = min(rect[axis_index] for rect in rects)
    high = max(
        rect[axis_index] + rect[axis_index + 2] for rect in rects
    )
    return low, high
