"""Точка подключения канализации для трасс: rules.json, fixed_elements плана «как есть» или его унитаз."""

import os

from rpkit.jsonfile import read_json
from rpkit.paths import ROOT
from rpkit.rules_drain import center, drains
from rpkit.rules_items import has, specs

TOILET_OUTLET_CM = 10  # выпуск унитаза — в 10 см от середины спинки, внутрь
POINT = "point"
RECT = "rect"


def _toilet_outlet(piece):
    """Середина спинки унитаза, 10 см внутрь."""
    x_cm, y_cm, width, height = piece[RECT]
    outlets = {
        "down": (x_cm + width / 2, y_cm + height - TOILET_OUTLET_CM),
        "up": (x_cm + width / 2, y_cm + TOILET_OUTLET_CM),
        "left": (x_cm + TOILET_OUTLET_CM, y_cm + height / 2),
        "right": (x_cm + width - TOILET_OUTLET_CM, y_cm + height / 2),
    }
    return outlets[specs(piece)[0]["back"]]


def drain_point(cfg, toilet):
    """Точка подключения канализации: drain.point в rules.json (или в правиле); иначе fixed_elements с
    `kind: "drain"` в плане «как есть» (`point` или центр `rect`); иначе унитаз «как есть» — середина его спинки,
    10 см внутрь. Возвращает ((x, y), откуда) или (None, причина)."""
    if cfg.get(POINT):
        return tuple(cfg[POINT]), "rules.json"
    source = cfg["as_is"]
    path = os.path.join(ROOT, source)
    if not os.path.exists(path):
        return None, f"нет {source} и drain.point в rules.json"
    return _as_is_point(read_json(path), source, toilet)


def _as_is_point(as_is, source, toilet):
    for element in as_is.get("fixed_elements", []):
        if element.get("kind") == "drain":
            return _element_point(element), f"{element['id']} в {source}"
    toilets = [
        piece for piece in as_is["furniture"]
        if has(piece, toilet) and drains(piece)
    ]
    if not toilets:
        return None, f"в {source} нет ни fixed_elements kind drain, ни унитаза"
    named_wc = (piece for piece in toilets if piece["id"] == "wc")
    chosen = next(named_wc, toilets[0])
    return _toilet_outlet(chosen), f"унитаз {chosen['id']} в {source}"


def _element_point(element):
    if element.get(POINT):
        return tuple(element[POINT])
    return center(element[RECT])
