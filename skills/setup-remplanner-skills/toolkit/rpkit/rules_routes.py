"""Трассы канализации: BFS по клеткам мокрых комнат и перегородок от точки подключения до приборов."""

from collections import deque

from rpkit.rules_drain import center, drains
from rpkit.rules_grid import STEP_CM, door_box, grid_cells, seed_cells

NEIGHBOURS = (
    (1, 0),
    (-1, 0),
    (0, 1),
    (0, -1),
)
RECT = "rect"


def _allowed(ctx, wet_rooms, devices):
    """Клетки, где может идти трасса: мокрые комнаты, перегородки, сами приборы — без дверных проёмов."""
    rects = [room[RECT] for room in wet_rooms if room.get(RECT)]
    rects.extend(wall[RECT] for wall in ctx.plan["partitions"])
    # прибор в нише за стеной санузла — его собственный габарит тоже допустим
    rects.extend(device[2][RECT] for device in devices)
    cells = set()
    for rect in rects:
        cells.update(grid_cells(rect))
    for door in ctx.plan["doors"]:
        cells.difference_update(grid_cells(door_box(door)))
    return cells


def _distances(cells, point):
    """BFS от клеток у точки подключения: длина трассы до каждой достижимой клетки."""
    seed = seed_cells(cells, point)
    dist = {cell: float(0) for cell in seed}
    queue = deque(seed)
    while queue:
        cell = queue.popleft()
        for neighbour in _neighbours(cell):
            if neighbour in cells and neighbour not in dist:
                dist[neighbour] = dist[cell] + STEP_CM
                queue.append(neighbour)
    return dist


def _neighbours(cell):
    column, row = cell
    return [
        (column + step[0], row + step[1]) for step in NEIGHBOURS
    ]


def _length(dist, outlet, piece):
    """Длина трассы до выпуска прибора: до ближайшей клетки прибора и от его центра до выпуска; None — нет."""
    reached = [
        dist[cell] for cell in grid_cells(piece[RECT]) if cell in dist
    ]
    best = min(reached, default=None)
    if best is None:
        return None
    middle = center(piece[RECT])
    to_x = abs(outlet[0] - middle[0])
    return best + (to_x + abs(outlet[1] - middle[1]))


def routes(ctx, point, wet_role):
    """Трассы от точки подключения: [(прибор, длина или None, предмет)] и мокрые комнаты без rect."""
    wet_rooms = ctx.role(wet_role, need_rect=False)
    missing = [room["id"] for room in wet_rooms if not room.get(RECT)]
    devices = _devices(ctx.plan)
    dist = _distances(_allowed(ctx, wet_rooms, devices), point)
    return [_traced(dist, device) for device in devices], missing


def _devices(plan):
    """[(прибор, точка выпуска, предмет)] — все приборы с канализацией в плане."""
    return [
        (name, outlet, piece)
        for piece in plan["furniture"]
        for name, outlet in drains(piece)
    ]


def _traced(dist, device):
    name, outlet, piece = device
    return name, _length(dist, outlet, piece), piece
