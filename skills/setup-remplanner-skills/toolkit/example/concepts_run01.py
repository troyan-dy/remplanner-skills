#!/usr/bin/env python3
"""concepts_run01.py — пример генератора серии (для selftest и как образец src/concepts_runNN.py).

Концепция shower: стены как есть, в санузле душ 90×90 вместо ванны; стиральная машина уходит на место
ванны, у раковины освобождается место под полки.
Пишет concepts/run-01_2026-01-01/<name>.json."""

import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "tools",
))
import planlib  # noqa: E402

REPLACED = ("bathtub", "washer")  # уходят из санузла «как есть»


def shower():
    """Душ 90×90 на месте ванны, стиральная машина рядом."""
    plan = planlib.as_is()
    plan["meta"]["title"] = "Пример: душ вместо ванны"
    kept = [piece for piece in plan["furniture"] if piece["id"] not in REPLACED]
    plan["furniture"] = kept + [
        planlib.F("shower", [25, 505, 90, 90], "душ 90×90", "shower_cabin", "down"),
        planlib.F("washer", [125, 550, 60, 45], "стиральная машина", "washing_machine", "down"),
    ]
    entrance = planlib.zone("z-shower", [25, 435, 90, 70], "вход в душ")
    plan["zones"].append(entrance)
    return plan


if __name__ == "__main__":
    series = planlib.series_dir(1, "2026-01-01")
    planlib.save({"shower": shower()}, series)
