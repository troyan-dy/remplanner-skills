"""Правила о кухне и шкафах: прямая кухня, шкафы без углового стыка."""

import itertools

from rpkit.rules_items import ALONG_X, has, inside, specs

ITEM_PATTERNS = "items"


def _along_x(piece):
    return specs(piece)[0]["back"] in ALONG_X


def kitchen_straight(ctx, rule):
    """Кухня прямая или в два параллельных ряда: модули правила в комнате — по одной оси."""
    found = []
    for room in ctx.role(rule["rooms"]):
        units = [
            piece for piece in ctx.furn
            if inside(piece, room) and has(piece, rule[ITEM_PATTERNS])
        ]
        if len({_along_x(piece) for piece in units}) > 1:
            found.append((False, f"кухня {room['id']} Г-образная — модули по двум осям"))
        else:
            found.append((True, f"кухня {room['id']} прямая или в два ряда"))
    return found or [(True, "кухни с rect нет — не проверено")]


def _touch(first, second, tolerance):
    """Прямоугольники соприкасаются или перекрываются (с допуском tolerance)."""
    return all(
        _overlap(first["rect"], second["rect"], axis_index, tolerance) for axis_index in (0, 1)
    )


def _overlap(first, second, axis_index, tolerance):
    first_start, second_start = first[axis_index], second[axis_index]
    if first_start - tolerance > second_start + second[axis_index + 2]:
        return False
    return second_start - tolerance <= first_start + first[axis_index + 2]


def no_corner_join(ctx, rule):
    """Шкафы правила не стыкуются под прямым углом (Г-образно)."""
    wardrobes = [piece for piece in ctx.furn if has(piece, rule[ITEM_PATTERNS])]
    found = []
    for first, second in itertools.combinations(wardrobes, 2):
        crosswise = _along_x(first) != _along_x(second)
        if crosswise and _touch(first, second, rule["tol"]):
            found.append((False, f"{first['id']} и {second['id']} стыкуются углом (Г-образно)"))
    return found or [(True, f"угловых стыков нет ({len(wardrobes)} шт.)")]
