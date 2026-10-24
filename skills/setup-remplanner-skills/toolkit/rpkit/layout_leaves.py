"""Открытое на 90° полотно двери: остаток прохода за его краем и расстояние до фасада перед ним."""

from rpkit.layout_door_leaf import LEAF_START_CM, door_axis, leaf_doors
from rpkit.layout_leaf_front import LeafFront, leaf_fronts
from rpkit.layout_vectors import dot, minus, moved

RAY_CM = 400
ID = "id"


class _LeafLine:
    """Линия открытого полотна: от петли по swing до препятствия за краем полотна."""

    def __init__(self, layout, door):
        self.layout = layout
        self.door = door
        width, unit = door_axis(door)
        self.width = width
        self.unit = unit
        tip = moved(door["hinge"], door["swing"], width + 1)  # край открытого полотна
        self.gap = layout.ray(layout.masks.path, tip, door["swing"])
        self.reach = self.width + 1 + self.gap

    def crossed(self, routes):
        """Маршрут пересекает линию полотна (ось петли поперёк стены) на участке от петли до препятствия."""
        return any(self._crosses(route) for route in routes)

    def _crosses(self, route):
        coords = [self._coords(cell) for cell in route]
        return any(
            self._step_crosses(before, after)
            for before, after in zip(coords, coords[1:])
        )

    def _coords(self, cell):
        """(вдоль стены от петли, > 0 — в сторону проёма; от стены по swing)."""
        offset = minus(self.layout.grid.center(cell), self.door["hinge"])
        return dot(offset, self.unit), dot(offset, self.door["swing"])

    def _step_crosses(self, before, after):
        if (before[0] < 0) == (after[0] < 0):
            return False
        if LEAF_START_CM > min(after[1], before[1]):
            return False
        return max(after[1], before[1]) <= self.reach


def _front_findings(layout, door, width, fronts):
    """door_leaf_front по каждому фасаду, перед которым оказывается открытое полотно."""
    leaf = LeafFront(layout, door, width)
    distances = [(piece, leaf.distance(piece, face)) for piece, face in fronts]
    return [
        ("door_leaf_front", f"{door[ID]} открыта → {piece[ID]}", round(distance))
        for piece, distance in distances
        if distance is not None
    ]


def _door_leaves(layout, door, routes, fronts):
    line = _LeafLine(layout, door)
    found = []
    if line.crossed(routes):
        width = round(min(line.gap, RAY_CM))
        found.append(("door_leaf_pass", f"{door[ID]} открыта", width))
    return found + _front_findings(layout, door, line.width, fronts)


def measure_leaves(layout, routes):
    """Открытое на 90° полотно (от петли по swing, длина — ширина двери):
    - door_leaf_pass — маршрут от входа пересекает полотно или промежуток за его краем: сколько остаётся прохода
      от края полотна до препятствия (полотно поперёк коридора);
    - door_leaf_front — полотно перед фасадом, который открывается вперёд (LEAF_FRONT: распашной шкаф, ящики,
      кухня и пеналы, стиральная машина): от фасада до полотна, если между ними нет стены."""
    fronts = leaf_fronts(layout.plan)
    found = []
    for door in leaf_doors(layout.plan):
        found.extend(_door_leaves(layout, door, routes, fronts))
    return found
