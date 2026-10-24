"""Линия кухни (kitchen_run) для проверки эргономики: мойки и плиты на лицевой кромке, столешница у плиты."""

from rpkit.layout_kinds import FRONT, specs
from rpkit.layout_kitchen_modules import free_top, is_sink_module, is_stove_module, kitchen_modules

ALONG_X = frozenset(("up", "down"))


def along_x(piece):
    """Линия кухни идёт вдоль x (спинкой вверх или вниз)."""
    return specs(piece)[0]["back"] in ALONG_X


def _edge(start, size, direction):
    """Лицевая кромка: start, если лицо смотрит к меньшей координате, иначе start + size."""
    return start if direction < 0 else start + size


class KitchenRun:
    """Линия кухни: модули, мойки и плиты [(предмет, точка на лицевой кромке, начало, конец)]."""

    def __init__(self, piece):
        self.piece = piece
        self.modules = kitchen_modules(piece)
        rect = piece["rect"]
        self.length = rect[2] if along_x(piece) else rect[3]
        self.sinks = self._find(is_sink_module)
        self.stoves = self._find(is_stove_module)

    def edge_point(self, position):
        """Точка на лицевой кромке в позиции position вдоль линии."""
        left, top, width, height = self.piece["rect"]
        face = FRONT[specs(self.piece)[0]["back"]]
        if along_x(self.piece):
            return left + position, _edge(top, height, face[1])
        return _edge(left, width, face[0]), top + position

    def counter_left(self, start):
        """Столешница слева от модуля, начинающегося в start, до препятствия; хвост до начала линии — 0."""
        before = [module for module in reversed(self.modules) if module[2] <= start]
        return free_top(before)[0]

    def counter_right(self, end):
        """Столешница справа от модуля, кончающегося в end, до препятствия или конца линии."""
        after = [module for module in self.modules if module[1] >= end]
        length, through = free_top(after)
        if through:
            length += self.length - self._last_end()
        return length

    def _last_end(self):
        return self.modules[-1][2] if self.modules else 0

    def _find(self, test):
        return [
            (self.piece, self.edge_point((start + end) / 2), start, end)
            for module, start, end in self.modules
            if test(module)
        ]
