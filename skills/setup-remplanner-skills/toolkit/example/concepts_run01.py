#!/usr/bin/env python3
"""concepts_run01.py — пример генератора серии (для selftest и как образец src/concepts_runNN.py).

Концепция shower: стены как есть, в санузле душ 90×90 вместо ванны; стиральная машина уходит на место
ванны, у раковины освобождается место под полки.
Пишет concepts/run-01_2026-01-01/<name>.json."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from planlib import F, as_is, save, series_dir, zone  # noqa: E402


def shower():
    p = as_is()
    p["meta"]["title"] = "Пример: душ вместо ванны"
    p["furniture"] = [f for f in p["furniture"] if f["id"] not in ("bathtub", "washer")] + [
        F("shower", [25, 505, 90, 90], "душ 90×90", "shower_cabin", "down"),
        F("washer", [125, 550, 60, 45], "стиральная машина", "washing_machine", "down"),
    ]
    p["zones"].append(zone("z-shower", [25, 435, 90, 70], "вход в душ"))
    return p


if __name__ == "__main__":
    save({"shower": shower()}, series_dir(1, "2026-01-01"))
