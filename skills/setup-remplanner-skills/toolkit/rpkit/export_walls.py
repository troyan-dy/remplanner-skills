"""Стены выгрузки целиком: несущие, перегородки и утепление — состыкованные, со стенами .plan."""

from rpkit.export_bearing import bearing_segs
from rpkit.export_join import join
from rpkit.export_partitions import partitions
from rpkit.frozen import frozen
from rpkit.rp_wall import wall

# В RemPlanner нет признака «несущая» — тип стены передаётся материалом (своя штриховка на плане).
# Ключи материалов — tools/reference/remplanner_example_v3_wall_materials.plan.
MATERIAL = frozen({
    "facade": "a_brick",
    "interapartment": "a_concrete",
    "column": "a_concrete",
    "bearing": "a_concrete",  # внутренняя несущая — как межквартирная (предположение: отдельного образца нет)
    "partition": "a_block",
    "glass": "a_glass",  # partitions[].kind = "glass" — стеклянная перегородка (образец ..._wall_materials.plan)
    "insulation": "a_block",  # insulation[] — утепление лоджии: без него RemPlanner считал лоджию шире
    # на толщину утепления
})
INSULATION = "insulation"


def door_middles(plan, frame):
    """Середины дверных проёмов в координатах RemPlanner по id двери."""
    middles = {}
    for door in plan["doors"]:
        middle = _middle(door["hinge"], door["other"], frame)
        middles[door["id"]] = middle
    return middles


def _middle(hinge, other, frame):
    middle_x = (hinge[0] + other[0]) / 2
    middle_y = (hinge[1] + other[1]) / 2
    return frame.to_rp(middle_x, middle_y)


def build_walls(plan, frame, middles):
    """[(Seg, стена .plan)]: несущие, перегородки и утепление, состыкованные."""
    bearing = bearing_segs(plan, frame)
    parts = partitions(plan, list(middles.values()), bearing, frame)
    # утепление стыкуется последним и не двигает другие стены: иначе стена комнаты у лоджии укорачивалась
    # до оси утепления и помещение «протекало» в щель у фасада
    insulation = [seg for seg in parts if seg.kind == INSULATION]
    segs = bearing + [seg for seg in parts if seg.kind != INSULATION]
    join(segs)
    segs += insulation
    join(segs, only=insulation)
    return [(seg, _wall_of(seg)) for seg in segs]


def _wall_of(seg):
    return wall(seg.ends(), seg.depth, MATERIAL[seg.kind])
