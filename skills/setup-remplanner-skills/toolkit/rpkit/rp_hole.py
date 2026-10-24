"""Точки проёма (двери, окна, балконного блока) на стене .plan — как в образцах RemPlanner."""

from rpkit.rp_geometry import WallAxis, pt, r3

LABEL_GAP_CM = 18  # точка подписи проёма pc1h — за гранью стены (как в образцах)
SIDES = (("l", 1), ("r", -1))  # сторона стены и знак сдвига от оси
EDGE_KEYS = ("l1", "l2", "r1", "r2")
AXIS_KEYS = ("p1", "p2", "pc")
BACKGROUND_ORDER = ("r1", "r1b", "l1b", "l1", "l2", "l2b", "r2b", "r2")
POLYGON_ORDER = ("l1", "l2", "r2", "r1")


class _Hole:
    """Проём на оси стены: начало и конец span, середина."""

    def __init__(self, host, span):
        self.axis = WallAxis(host)
        self.span = span
        self.middle = (span[0] + span[1]) / 2

    def axis_points(self, keys, across):
        """Середина и концы проёма со сдвигом across: keys — (начало, конец, середина)."""
        start, end = self.span
        points = (
            self.axis.point(start, across),
            self.axis.point(end, across),
            self.axis.point(self.middle, across),
        )
        return dict(zip(keys, points))

    def side_points(self, suffix, center, half_width):
        """<side>1<suffix>, <side>2<suffix> — концы проёма на гранях l и r (center ± half_width)."""
        points = {}
        for side, sign in SIDES:
            across = center + sign * half_width
            points.update(self._ends(f"{side}{{0}}{suffix}", across))
        return points

    def label_point(self):
        """Точка подписи pc1h: напротив середины, за гранью r."""
        return self.axis.point(self.middle, -(self.axis.half + LABEL_GAP_CM))

    def _ends(self, template, across):
        return {
            template.format(index): self.axis.point(along, across)
            for index, along in enumerate(self.span, start=1)
        }


def hole_geometry(host, span, frame_depth, frame_shift):
    """Геометрия проёма на стене host между параметрами span = (t0, t1), t0 < t1 (см от p1 стены вдоль оси).
    frame_shift — смещение коробки/рамы от оси в сторону r (как position/offset в образце)."""
    hole = _Hole(host, span)
    shift = -frame_shift
    geometry = hole.axis_points(AXIS_KEYS, 0)
    geometry.update(hole.side_points("", 0, hole.axis.half))
    frame = hole.axis_points(("p1b", "p2b", "pcb"), shift)
    for key in ("pcb", "p1b", "p2b"):
        geometry[key] = frame[key]
    geometry.update(hole.side_points("b", shift, frame_depth / 2))
    _add_copies(geometry)
    _add_outlines(geometry, r3(span[1] - span[0]))
    geometry["pc1h"] = hole.label_point()
    return geometry


def _add_copies(geometry):
    for key in EDGE_KEYS:
        geometry[f"{key}c"] = dict(geometry[key])
    for key in AXIS_KEYS:
        geometry[f"{key}fact"] = dict(geometry[key])


def _midpoint(first, second):
    x_cm = (first["x"] + second["x"]) / 2
    y_cm = (first["y"] + second["y"]) / 2
    return pt(x_cm, y_cm)


def _edge(geometry, side, length):
    start = geometry[f"{side}1"]
    end = geometry[f"{side}2"]
    return {
        "p1": start,
        "p2": end,
        "c": _midpoint(start, end),
        "length": length,
    }


def _add_outlines(geometry, length):
    geometry["bg_polygon"] = [geometry[key] for key in BACKGROUND_ORDER]
    geometry["eds"] = {
        side: _edge(geometry, side, length) for side, _ in SIDES
    }
    geometry["polygon"] = [geometry[key] for key in POLYGON_ORDER]
