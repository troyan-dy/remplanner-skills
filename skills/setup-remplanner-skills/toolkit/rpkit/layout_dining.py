"""Обеденный стол: от кромки стола за стулом до препятствия (dining_back)."""

from rpkit.layout_kinds import kind
from rpkit.layout_roles import is_chair
from rpkit.layout_sweep import sweep

CHAIR_GAP_CM = 15  # стул примыкает к грани стола: зазор не больше
CHAIR_OVERLAP_CM = 20  # и перекрытие вдоль грани больше
EDGE_CM = 5
SIDES = (
    (1, 0),
    (-1, 0),
    (0, 1),
    (0, -1),
)
RECT = "rect"


def _end(rect, axis_index):
    return rect[axis_index] + rect[axis_index + 2]


class _Pair:
    """Стол и стул: как стул стоит у грани стола."""

    def __init__(self, table, chair):
        self.table = table
        self.chair = chair

    def gap(self, side):
        """Зазор между гранью стола side и стулом поперёк грани."""
        across = 0 if side[0] else 1
        if side[across] > 0:
            return self.chair[across] - _end(self.table, across)
        return self.table[across] - _end(self.chair, across)

    def overlap(self, along):
        """Перекрытие стола и стула вдоль грани."""
        low = max(self.table[along], self.chair[along])
        high = min(_end(self.table, along), _end(self.chair, along))
        return high - low

    def margins(self, along):
        """Отступы sweep по краям грани: от краёв стола до стула (не меньше 0) + EDGE_CM."""
        before = self.chair[along] - self.table[along]
        after = _end(self.table, along) - _end(self.chair, along)
        return max(before, 0) + EDGE_CM, max(after, 0) + EDGE_CM

    def touches(self, side):
        """Стул примыкает к грани стола side."""
        along = 1 if side[0] else 0
        if not -CHAIR_GAP_CM <= self.gap(side) <= CHAIR_GAP_CM:
            return False
        return self.overlap(along) > CHAIR_OVERLAP_CM

    def touching(self):
        """Грани стола, к которым примыкает стул."""
        return [side for side in SIDES if self.touches(side)]

    def depth(self, layout, side):
        """Свободно за стулом у грани side."""
        along = 1 if side[0] else 0
        return sweep(layout, self.table, side, self.margins(along))


def _chairs(layout):
    return [piece for piece in layout.plan["furniture"] if is_chair(kind(piece))]


def dining_backs(layout, table):
    """Находки dining_back для стола table: по каждому стулу, примыкающему к его грани."""
    found = []
    for chair in _chairs(layout):
        pair = _Pair(table[RECT], chair[RECT])
        label = f"{table['id']}→{chair['id']}"
        found.extend(
            ("dining_back", label, pair.depth(layout, side)) for side in pair.touching()
        )
    return found
