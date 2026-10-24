"""Что мебель значит для проходов и зон: препятствие ли, цель ли прохода, мешает ли стоять перед предметом."""

from rpkit.catalog_store import catalog_info
from rpkit.layout_kinds import over_floor
from rpkit.layout_roles import is_chair

HUNG_CM = 100  # навесное: низ не ниже — не препятствие и не цель
NAME = "name"
TV = "tv"
MIRROR = "bathroom_mirror"
OFFICE_CHAIR = "office_chair"
TOWEL_DRYER = "towel_dryer"
BAR_CHAIR = "bar_chair_backrest"
WALL_TABLE = "folding_wall_table"
STILLAGE = "tetra_stillage"
# навесное, переставляемое (dryer — напольная сушильная машина 60×60×85, она препятствие)
SKIP = frozenset((TV, MIRROR, "chair", OFFICE_CHAIR, "table", TOWEL_DRYER, BAR_CHAIR, WALL_TABLE, STILLAGE))
NO_TARGET = SKIP | frozenset(("worktop", "kitchen_sink", "table_round", "bar_table"))
LIGHT = frozenset((TV, MIRROR, TOWEL_DRYER, "dryer_on_wall", WALL_TABLE))  # не мешают стоять перед предметом


def skip(spec_rp):
    """Не препятствие для проходов: навесное (низ ≥ 100 см), переставляемое (SKIP, стулья)."""
    name = spec_rp[NAME]
    return name in SKIP or over_floor(spec_rp) >= HUNG_CM or is_chair(name)


def no_target(spec_rp):
    """Не цель прохода: NO_TARGET, навесное и переставляемое, мойка в столешнице, настенная инженерия
    (anchor wall: бризер, щиток, кондиционер — перед ней не стоят)."""
    record = catalog_info(spec_rp[NAME])
    if spec_rp[NAME] in NO_TARGET or skip(spec_rp):
        return True
    return record.get("custom_type") == "sink" or record.get("anchor") == "wall"


def light(spec_rp):
    """Не мешает стоять перед другим предметом."""
    name = spec_rp[NAME]
    return name in LIGHT or is_chair(name) or over_floor(spec_rp) >= HUNG_CM
