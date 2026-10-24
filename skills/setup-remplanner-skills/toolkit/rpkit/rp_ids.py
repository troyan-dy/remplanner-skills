"""id объектов .plan: «_» и 5 случайных символов, без повторов внутри плана; seed делает их стабильными."""

import random
import string

ID_ALPHABET = string.ascii_lowercase + string.digits
ID_LENGTH = 5


class _IdPool:
    """Выданные id текущего плана."""

    def __init__(self):
        self._used = set()

    def next_id(self):
        """Новый id, которого ещё не было в плане."""
        while True:
            suffix = "".join(random.choices(ID_ALPHABET, k=ID_LENGTH))
            candidate = f"_{suffix}"
            if candidate not in self._used:
                self._used.add(candidate)
                return candidate

    def reset(self, seed):
        """Новый план: id с нуля, случайность от seed (перегенерация без изменений даёт тот же файл)."""
        random.seed(seed)
        self._used.clear()


_POOL = _IdPool()


def uid():
    """Новый id объекта .plan."""
    return _POOL.next_id()


def reset_ids(seed):
    """Начать id нового плана со случайностью от seed."""
    _POOL.reset(seed)
