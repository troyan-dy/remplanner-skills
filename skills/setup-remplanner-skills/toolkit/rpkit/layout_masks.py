"""Сетки препятствий плана: стены с проёмами, мебель для проходов и для зон перед предметами, несущие."""

from typing import NamedTuple

from rpkit.layout_grid import door_box
from rpkit.layout_kinds import specs
from rpkit.layout_obstacles import light, skip

RECT = "rect"
WALLS_BEARING = "walls_bearing"


class Masks(NamedTuple):
    """Сетки клеток 0/1: wall — стены с прорезанными проёмами; path — стены + мебель для проходов;
    front — стены + мебель, мешающая стоять перед предметом; bearing — несущие стены."""

    wall: bytearray
    path: bytearray
    front: bytearray
    bearing: bytearray


def flat_cells(grid, rect):
    """Номера клеток, которые задевает rect (построчно)."""
    pairs = grid.cells(rect)
    return [row * grid.columns + column for column, row in pairs]


class _Builder:
    """Сетки плана по его стенам, проёмам и мебели."""

    def __init__(self, plan, grid):
        self.plan = plan
        self.grid = grid
        self.size = grid.columns * grid.rows
        self.owner = [-1 for _ in range(self.size)]

    def fill(self, mask, rects, flag):
        """Клетки rects в маске mask — flag (1 или 0)."""
        for rect in rects:
            for cell in flat_cells(self.grid, rect):
                mask[cell] = flag

    def walls(self):
        """Стены (несущие, перегородки, утепление) с прорезанными проёмами дверей: поперёк ±30 см."""
        wall = bytearray(self.size)
        plan = self.plan
        solid = plan[WALLS_BEARING] + plan["partitions"]
        solid = solid + plan.get("insulation", [])
        self.fill(wall, [element[RECT] for element in solid], 1)
        self.fill(wall, [door_box(door) for door in plan["doors"]], 0)
        return wall

    def bearing(self):
        """Клетки несущих стен."""
        bearing = bytearray(self.size)
        rects = [element[RECT] for element in self.plan[WALLS_BEARING]]
        self.fill(bearing, rects, 1)
        return bearing

    def furniture(self):
        """Мебель для проходов и для зон перед предметами; owner — индекс мебели в клетке."""
        masks = (bytearray(self.size), bytearray(self.size))
        for index, piece in enumerate(self.plan["furniture"]):
            self._mark(index, piece, masks)
        return masks

    def _mark(self, index, piece, masks):
        flags = _flags(piece)
        for cell in flat_cells(self.grid, piece[RECT]):
            for mask, flag in zip(masks, flags):
                if flag:
                    mask[cell] = 1
            if flags[0] or flags[1]:
                self.owner[cell] = index


def _flags(piece):
    """(мешает проходу, мешает стоять перед предметом)."""
    attached = specs(piece)
    on_path = not (attached and all(skip(spec_rp) for spec_rp in attached))
    return on_path, not (attached and all(light(spec_rp) for spec_rp in attached))


def _merged(wall, extra):
    return bytearray(left | right for left, right in zip(wall, extra))


def build_masks(plan, grid):
    """(Masks, owner) плана на сетке grid."""
    builder = _Builder(plan, grid)
    wall = builder.walls()
    on_path, on_front = builder.furniture()
    masks = Masks(
        wall,
        _merged(wall, on_path),
        _merged(wall, on_front),
        builder.bearing(),
    )
    return masks, builder.owner
