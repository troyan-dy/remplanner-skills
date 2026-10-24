"""Полотно, открытое на 90°, перед фасадом, который открывается вперёд: от фасада до полотна."""

from rpkit.layout_door_leaf import LEAF_START_CM
from rpkit.layout_front_rule import front_rule
from rpkit.layout_grid import STEP_CM
from rpkit.layout_kinds import FRONT, specs
from rpkit.layout_vectors import moved

LEAF_FRONT = ("ward_hinged_front", "drawer_front", "kitchen_front", "washer_front")  # фасад открывается вперёд
FACADE_REACH_CM = 150  # дальше фасада полотно ему не мешает
FACADE_EDGE_CM = 5  # полотно у края фасада (вдоль боковой грани) — не перед фасадом
HALF_CM = 0.5


def _opens_forward(spec_rp):
    return front_rule(spec_rp["name"], spec_rp) in LEAF_FRONT


def leaf_fronts(plan):
    """[(предмет, куда смотрит фасад)] мебели с фасадом из LEAF_FRONT."""
    found = []
    for piece in plan["furniture"]:
        attached = specs(piece)
        if attached and _opens_forward(attached[0]):
            found.append((piece, FRONT[attached[0]["back"]]))
    return found


class _Facade:
    """Фасад предмета rect, который смотрит по face: плоскость фасада и его края вдоль."""

    def __init__(self, rect, face):
        self.face = face
        self.axis = 0 if face[0] else 1
        self.across = 1 - self.axis
        self.direction = face[self.axis]
        self.plane = rect[self.axis]
        if self.direction > 0:
            self.plane = rect[self.axis] + rect[self.axis + 2]
        start = rect[self.across]
        self.edges = (
            start + FACADE_EDGE_CM,
            start + rect[self.across + 2] - FACADE_EDGE_CM,
        )

    def distance(self, point):
        """От фасада до точки по направлению face."""
        offset = point[self.axis] - self.plane
        return offset * self.direction

    def beside(self, point):
        """Точка не перед фасадом, а у края или сбоку."""
        low, high = self.edges
        return not low < point[self.across] < high

    def foot(self, point):
        """Точка на фасаде (в 0,5 см перед ним) напротив point."""
        on_face = [0, 0]
        on_face[self.axis] = self.plane + self.direction * HALF_CM
        on_face[self.across] = point[self.across]
        return tuple(on_face)


class LeafFront:
    """Открытое полотно двери (от петли по swing, длина — ширина двери) против фасадов."""

    def __init__(self, layout, door, width):
        self.layout = layout
        self.door = door
        self.width = width

    def distance(self, piece, face):
        """Ближайшее расстояние от фасада piece до полотна или None (полотно не перед фасадом)."""
        facade = _Facade(piece["rect"], face)
        found = [
            self._facing(facade, radius)
            for radius in range(LEAF_START_CM, int(self.width) + 1, STEP_CM)
        ]
        found = [distance for distance in found if distance is not None]
        return min(found) if found else None

    def _facing(self, facade, radius):
        """Расстояние от фасада до точки полотна в radius см от петли или None."""
        door = self.door
        point = moved(door["hinge"], door["swing"], radius + 1)
        distance = facade.distance(point)
        if not 0 <= distance < FACADE_REACH_CM:
            return None
        if facade.beside(point):
            return None  # полотно вдоль боковой грани — не перед фасадом
        wall = self.layout.masks.wall
        free = self.layout.ray(wall, facade.foot(point), facade.face, FACADE_REACH_CM)
        if free < distance - STEP_CM:
            return None  # между фасадом и полотном стена
        return distance
