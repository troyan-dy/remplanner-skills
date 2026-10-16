"""rp_lib.py — сборка объектов RemPlanner .plan v3 по образцам из tools/reference/.

Все координаты здесь — координаты RemPlanner: см, ось y вниз, начало в центре плана.
Поля и значения повторяют наблюдённые в tools/reference/remplanner_example_v3_*.plan
(см. tools/reference/REMPLANNER_V3_SCHEMA.md); производные поля считаются так же, как в образцах.
Предметы: CATALOG — сверены с образцами; полный каталог — tools/catalog/remplanner_catalog.json
(собирается `python3 tools/rp_catalog.py fetch`); подтверждённые снимком пользователя —
tools/catalog/confirmed.json (confirmed_names()).

Без полного каталога работают предметы CATALOG и confirmed.json: сведения каталога о них (габарит по умолчанию,
over_floor, custom_type, подводки, раздел меню) — в tools/reference/catalog_core.json (выписка из полного
каталога, `python3 tools/rp_catalog.py core`) и в поле "catalog" записи confirmed.json (`rp_catalog.py confirm`).
Полный каталог нужен только для прочих имён: entry() / info() / check_names().
"""

import copy
import json
import math
import os
import random
import string

HEIGHT = 270
TOOLS = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(TOOLS, "reference")
CAT_DIR = os.path.join(TOOLS, "catalog")
CATALOG_JSON = os.path.join(CAT_DIR, "remplanner_catalog.json")
CONFIRMED_JSON = os.path.join(CAT_DIR, "confirmed.json")
CORE_JSON = os.path.join(REF, "catalog_core.json")  # записи полного каталога для имён CATALOG
FETCH = "python3 tools/rp_catalog.py fetch"

# Каталог предметов: значения item_id / plan / self_height / доп. поля — из
# tools/reference/remplanner_example_v3_catalog.plan (кроме toilet / sink_table_susp — из ..._objects.plan).
CATALOG = {
    "bed_double": dict(item_id=97, plan={"furniture": 6}, self_height=77),
    "sofa_triple": dict(item_id=93, plan={"furniture": 6}, self_height=85),
    "ward_coupe": dict(
        item_id=152,
        plan={"furniture": 6},
        self_height=230,
        over_floor={"value": 0, "display": False},
    ),
    "bedside_table": dict(item_id=162, plan={"furniture": 6}, self_height=68),
    "tv": dict(
        item_id=91,
        plan={"furniture": 6},
        self_height=51,
        over_floor={"value": 110, "display": True},
        on_tv_diagonal=1,
        tv_diagonal=41,
    ),
    "tv_table": dict(item_id=167, plan={"furniture": 6}, self_height=48),
    "table": dict(item_id=89, plan={"furniture": 6}, self_height=75),
    "chair": dict(item_id=107, plan={"furniture": 6}, self_height=77),
    "writingdesk_drawers": dict(item_id=801, plan={"furniture": 6}, self_height=75),
    "office_chair": dict(item_id=106, plan={"furniture": 6}, self_height=112),
    "fridge": dict(
        item_id=100, plan={"furniture": 6}, self_height=190, on_show_decoration=1
    ),
    "stove": dict(item_id=102, plan={"furniture": 6}, self_height=85),
    "kitchen_box_door_double": dict(
        item_id=1714, plan={"furniture": 6}, self_height=85
    ),
    "worktop": dict(
        item_id=159,
        plan={"furniture": 6},
        self_height=4,
        over_floor={"value": 81, "display": False},
    ),
    "kitchen_sink": dict(
        item_id=169,
        plan={"santeh": 7, "furniture": 6},
        self_height=0,
        over_floor={"value": 85, "display": False},
    ),
    "toilet": dict(item_id=135, plan={"santeh": 7}, self_height=79),
    "sink_table_susp": dict(
        item_id=1694,
        plan={"santeh": 7},
        self_height=38,
        over_floor={"value": 47, "display": False},
    ),
    "bathtub": dict(item_id=130, plan={"santeh": 7}, self_height=60),
    "shower_cabin": dict(item_id=122, plan={"santeh": 7}, self_height=220),
    "washing_machine": dict(
        item_id=126,
        plan={"santeh": 7, "furniture": 6},
        self_height=85,
        over_floor={"value": 0, "display": False},
        on_show_decoration=1,
    ),
    "dryer": dict(
        item_id=280,
        plan={"santeh": 7},
        self_height=85,
        over_floor={"value": 0, "display": False},
        on_show_decoration=1,
    ),
    # из tools/reference/remplanner_example_v3_hall_mirror_shoes.plan
    "bathroom_mirror": dict(
        item_id=440,
        plan={"furniture": 6},
        self_height=70,
        over_floor={"value": 105, "display": False},
    ),
    "shoes_closet": dict(
        item_id=166, plan={"furniture": 6}, self_height=0, on_show_decoration=1
    ),
    # из tools/reference/remplanner_example_v3_catalog2.plan
    "armchair_le_corbusier": dict(item_id=860, plan={"furniture": 6}, self_height=0),
    "commode": dict(item_id=163, plan={"furniture": 6}, self_height=68),
    "chest_for_sink": dict(item_id=454, plan={"santeh": 7}, self_height=85),
    "tetra_stillage": dict(
        item_id=822,
        plan={"furniture": 6},
        self_height=57,
        over_floor={"value": 100, "display": False},
        on_show_decoration=1,
    ),
    "table_round": dict(item_id=115, plan={"furniture": 6}, self_height=75),
    "bar_chair_backrest": dict(item_id=672, plan={"furniture": 6}, self_height=0),
    "bar_table": dict(item_id=920, plan={"furniture": 6}, self_height=96),
    "kitchen_box_penal": dict(item_id=178, plan={"furniture": 6}, self_height=212),
    "kitchen_box_dishwasher": dict(
        item_id=636, plan={"furniture": 6}, self_height=85, on_show_decoration=1
    ),
    "pencil_case_oven_microwave": dict(
        item_id=664, plan={"furniture": 6}, self_height=212, on_show_decoration=1
    ),
    "built_in_fridge": dict(
        item_id=676, plan={"furniture": 6}, self_height=212, on_show_decoration=1
    ),
    "kitchen_bench": dict(item_id=783, plan={"furniture": 6}, self_height=84),
    "folding_wall_table": dict(
        item_id=921,
        plan={"furniture": 6},
        self_height=4,
        over_floor={"value": 81, "display": False},
    ),
    "low_cabinet_sideboard": dict(item_id=855, plan={"furniture": 6}, self_height=135),
    "monkey_bars": dict(item_id=251, plan={"furniture": 6}, self_height=0),
    "sofa_double": dict(item_id=92, plan={"furniture": 6}, self_height=85),
    "towel_dryer": dict(
        item_id=125,
        plan={"santeh": 7},
        self_height=60,
        over_floor={"value": 110, "display": False},
    ),
    "toilet_with_frame": dict(
        item_id=414,
        plan={"santeh": 7},
        self_height=34,
        over_floor={"value": 6, "display": False},
    ),
    "pencil_cabinet_above_washing": dict(
        item_id=446, plan={"santeh": 7}, self_height=200
    ),
    "stillage_floor_book": dict(item_id=1836, plan={"furniture": 6}, self_height=200),
    "bookshelf": dict(item_id=153, plan={"furniture": 6}, self_height=190),
    # подтверждены снимком RemPlanner после импорта, параметры — из полного каталога
    "double_sink_box_floor": dict(item_id=1698, plan={"santeh": 7}, self_height=80),
    "rectangular_shower_cabin_true": dict(item_id=1395, plan={"santeh": 7}, self_height=220),
    "four_door_ward_coupe": dict(item_id=844, plan={"furniture": 6}, self_height=230, over_floor={"value": 0, "display": False}),
    "ward_coupe_3doors": dict(item_id=1807, plan={"furniture": 6}, self_height=230, over_floor={"value": 0, "display": False}),
    "hanger_hallway": dict(item_id=652, plan={"furniture": 6}, self_height=146, over_floor={"value": 50, "display": False}),
    "tele_on_mobile_stand": dict(item_id=934, plan={"furniture": 6}, self_height=190),
    "bar_rack_console": dict(item_id=616, plan={"furniture": 6}, self_height=0, over_floor={"value": 85, "display": False}),
    "dryer_on_wall": dict(item_id=915, plan={"furniture": 6}, self_height=19, over_floor={"value": 190, "display": False}),
    # подтверждены снимком RemPlanner после импорта
    "bedside_bench": dict(item_id=618, plan={"furniture": 6}, self_height=43),
    "mezzanine_cabinet_2door": dict(item_id=1470, plan={"furniture": 6}, self_height=40, over_floor={"value": 230, "display": False}),
    "bed_transformer_with_sofa": dict(item_id=627, plan={"furniture": 6}, self_height=260),
    "workbench_with_shelves": dict(item_id=1230, plan={"furniture": 6}, self_height=80),
    "horizontal_bar": dict(item_id=320, plan={"furniture": 6}, self_height=0, over_floor={"value": 200, "display": False}),
    "hooks_for_hangers": dict(item_id=1793, plan={"furniture": 6}, self_height=8, over_floor={"value": 150, "display": False}),
    # подтверждены снимком RemPlanner после импорта
    "banquet_shelf_shoes": dict(item_id=838, plan={"furniture": 6}, self_height=45),
    "pouf-cube": dict(item_id=784, plan={"furniture": 6}, self_height=45),
    "installation_сabinet": dict(item_id=1428, plan={"santeh": 7}, self_height=140, over_floor={"value": 120, "display": True}),
    "monstera": dict(item_id=1624, plan={"furniture": 6}, self_height=0),
    "ficus": dict(item_id=658, plan={"furniture": 6}, self_height=0, over_floor={"value": 0, "display": False}),
    # подтверждены снимком RemPlanner после импорта
    "exercycle": dict(item_id=313, plan={"furniture": 6}, self_height=0),
    "hammock_chair": dict(item_id=696, plan={"furniture": 6}, self_height=250, over_floor={"value": 65, "display": False}),
    "stillage_floor_open": dict(item_id=1837, plan={"furniture": 6}, self_height=200),
    # подтверждены снимком RemPlanner после импорта
    "cat_litter": dict(item_id=717, plan={"furniture": 6}, self_height=0),
    "animal_feeder": dict(item_id=720, plan={"furniture": 6}, self_height=0),
    "service_cabinet": dict(item_id=608, plan={"furniture": 6}, self_height=67),
    "3d_printer": dict(item_id=1207, plan={"furniture": 6}, self_height=46, over_floor={"value": 75, "display": False}),
    "kitchen_box_penal_glass": dict(item_id=1745, plan={"furniture": 6}, self_height=212),
    "shelf": dict(item_id=179, plan={"furniture": 6}, self_height=3, over_floor={"value": 140, "display": False}),
    # подтверждены снимком RemPlanner после импорта
    "bottle_box": dict(item_id=105, plan={"furniture": 6}, self_height=85),
    "kitchen_box_ending": dict(item_id=1754, plan={"furniture": 6}, self_height=85),
    "floor_pencil_cabinet": dict(item_id=443, plan={"santeh": 7}, self_height=200),
    "sink_box_floor": dict(item_id=1552, plan={"santeh": 7}, self_height=85),
    "ward": dict(item_id=150, plan={"furniture": 6}, self_height=230, over_floor={"value": 0, "display": False}),
}

# Модули линии кухни (kitchen_run): сокращение → имя каталога; по 60 см, столешница — над всеми, кроме плиты.
KITCHEN = {
    "box": "kitchen_box_door_double",
    "sink": "kitchen_box_door_double",
    "stove": "stove",
    "washer": "washing_machine",
    "dishwasher": "kitchen_box_dishwasher",
}

_full = None


def has_full():
    """Собран ли полный каталог tools/catalog/remplanner_catalog.json."""
    return os.path.exists(CATALOG_JSON)


def full_catalog():
    global _full
    if _full is None:
        if not has_full():
            raise SystemExit(f"нет полного каталога {CATALOG_JSON} — запустите {FETCH}")
        _full = json.load(open(CATALOG_JSON, encoding="utf-8"))["items"]
    return _full


_core = None


def core():
    """Записи полного каталога для имён CATALOG (tools/reference/catalog_core.json) — работают без fetch."""
    global _core
    if _core is None:
        _core = json.load(open(CORE_JSON, encoding="utf-8")) if os.path.exists(CORE_JSON) else {}
    return _core


_confirmed = None


def confirmed():
    """Предметы, которые пользователь подтвердил снимком RemPlanner после импорта:
    tools/catalog/confirmed.json — {"<name>": {"date": "ГГГГ-ММ-ДД", "note": "...", "catalog": {…}}}; файла может
    не быть. "catalog" — копия записи полного каталога (её пишет `rp_catalog.py confirm`): с ней предмет
    работает и без полного каталога. Нужен потому, что tools/ перезаписывается установкой и CATALOG
    пользователь не дописывает."""
    global _confirmed
    if _confirmed is None:
        _confirmed = {}
        if os.path.exists(CONFIRMED_JSON):
            _confirmed = json.load(open(CONFIRMED_JSON, encoding="utf-8"))
    return _confirmed


def confirmed_names():
    """Проверенные импортом имена: CATALOG ∪ confirmed.json."""
    return set(CATALOG) | set(confirmed())


def entry(name):
    """Запись каталога о предмете: из полного каталога, если он собран; иначе из выписки для CATALOG
    (catalog_core.json) или из confirmed.json (поле "catalog"). None — сведений нет."""
    if has_full():
        return full_catalog().get(name)
    return core().get(name) or (confirmed().get(name) or {}).get("catalog")


def info(name):
    """Как entry(), но {} вместо None: для проверок, которым хватает «нет сведений» (линия кухни, опечатка)."""
    return (entry(name) if name else None) or {}


def plan_names(plan):
    """[(где, имя)] — все имена каталога в плане: rp.name и модули kitchen_run (кроме сокращений KITCHEN)."""
    out = []
    for f in plan.get("furniture", []):
        sp = f.get("rp")
        for s in (sp if isinstance(sp, list) else [sp]) if sp else []:
            if s["name"] == "kitchen_run":
                out += [(f"furniture {f['id']}: модуль kitchen_run", m) for m in s.get("modules", []) if m not in KITCHEN]
            else:
                out.append((f"furniture {f['id']}", s["name"]))
    return out


def check_names(plan, label):
    """Все предметы плана известны: без полного каталога — только CATALOG и confirmed.json с записью "catalog".
    Иначе SystemExit с перечнем предметов (id и rp.name) и командой fetch."""
    bad = [(w, n) for w, n in plan_names(plan) if entry(n) is None]
    if not bad:
        return
    rows = "\n".join(f"  {w}: rp.name {n!r}" for w, n in bad)
    if has_full():
        raise SystemExit(f"{label}: нет в каталоге RemPlanner:\n{rows}\n"
                         "имена — python3 tools/rp_catalog.py find <слово>")
    raise SystemExit(f"{label}: предметы не из rp_lib.CATALOG и не из tools/catalog/confirmed.json, "
                     f"а полного каталога нет:\n{rows}\nсоберите его: {FETCH} "
                     "(или возьмите имена из CATALOG — python3 tools/blocks.py)")


def spec(name):
    """Параметры предмета: из CATALOG (сверено с образцами), иначе из записи каталога (entry) —
    только группы plan.items."""
    if name in CATALOG:
        return CATALOG[name]
    e = entry(name)
    if e is None:
        raise SystemExit(f"предмет {name!r}: нет сведений — нужен полный каталог ({FETCH})"
                         if not has_full() else f"предмет {name!r}: нет в каталоге RemPlanner")
    if not e["in_items"]:
        raise ValueError(f"{name}: группа {e['group']} — схема в .plan не получена")
    s = dict(item_id=e["id"], plan=e["plan"], self_height=e["self_height"])
    if "over_floor" in e:
        s["over_floor"] = e["over_floor"]
    if e.get("icon"):
        s["on_show_decoration"] = 1
    s["size"] = (e["width"], e["height"])
    return s


_used = set()


def uid():
    while True:
        i = "_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=5))
        if i not in _used:
            _used.add(i)
            return i


def r3(v):
    return round(v, 3)


def pt(x, y):
    return {"x": r3(x), "y": r3(y)}


def _frame(x1, y1, x2, y2, depth):
    """Единичный вектор стены и смещение левой кромки (как в образце: (uy, -ux) * depth/2)."""
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    return L, ux, uy, uy * depth / 2, -ux * depth / 2


def wall(x1, y1, x2, y2, depth, material="a_block"):
    L, _, _, lx, ly = _frame(x1, y1, x2, y2, depth)
    l1, l2 = pt(x1 + lx, y1 + ly), pt(x2 + lx, y2 + ly)
    rr1, rr2 = pt(x1 - lx, y1 - ly), pt(x2 - lx, y2 - ly)
    area = round(L * HEIGHT / 1e4, 1)
    i = uid()
    return {
        "id": i,
        "plan": "a",
        "role": "wall",
        "child": 0,
        "archive": 0,
        "demount": 0,
        "depth": depth,
        "height": HEIGHT,
        "angle": round(math.degrees(math.atan2(y2 - y1, x2 - x1)), 1),
        "p1": {"role": "p1", "x": r3(x1), "y": r3(y1), "demount": 0},
        "p2": {"role": "p2", "x": r3(x2), "y": r3(y2), "demount": 0},
        "l1": l1,
        "l2": l2,
        "r1": rr1,
        "r2": rr2,
        "l1f": dict(l1),
        "l2f": dict(l2),
        "r1f": dict(rr1),
        "r2f": dict(rr2),
        "p1st": 0,
        "p2st": 0,
        "material": material,
        "color": 0,
        "inRoom": 0,
        "area": {"outer": area, "inner": area},
        "neighbors": {},
        "level": "1",
        "show_dls": True,
        "room_on_left": 0,
        "room_on_right": 0,
    }


def _hole_geom(w, t0, t1, frame_depth, frame_shift):
    """Геометрия проёма на стене w между параметрами t0 < t1 (см от p1 стены вдоль оси).
    frame_shift — смещение коробки/рамы от оси в сторону r (как position/offset в образце)."""
    x1, y1, x2, y2, d = (
        w["p1"]["x"],
        w["p1"]["y"],
        w["p2"]["x"],
        w["p2"]["y"],
        w["depth"],
    )
    _, ux, uy, lx, ly = _frame(x1, y1, x2, y2, d)
    nx, ny = lx / (d / 2), ly / (d / 2)  # единичная нормаль в сторону l
    P = lambda t, s=0.0: (x1 + ux * t + nx * s, y1 + uy * t + ny * s)
    hd, fc, fh = d / 2, -frame_shift, frame_depth / 2
    g = {}
    g["p1"], g["p2"], g["pc"] = pt(*P(t0)), pt(*P(t1)), pt(*P((t0 + t1) / 2))
    g["l1"], g["l2"], g["r1"], g["r2"] = (
        pt(*P(t0, hd)),
        pt(*P(t1, hd)),
        pt(*P(t0, -hd)),
        pt(*P(t1, -hd)),
    )
    g["pcb"], g["p1b"], g["p2b"] = (
        pt(*P((t0 + t1) / 2, fc)),
        pt(*P(t0, fc)),
        pt(*P(t1, fc)),
    )
    g["l1b"], g["l2b"] = pt(*P(t0, fc + fh)), pt(*P(t1, fc + fh))
    g["r1b"], g["r2b"] = pt(*P(t0, fc - fh)), pt(*P(t1, fc - fh))
    for k in ("l1", "l2", "r1", "r2"):
        g[k + "c"] = dict(g[k])
    g["p1fact"], g["p2fact"], g["pcfact"] = dict(g["p1"]), dict(g["p2"]), dict(g["pc"])
    g["bg_polygon"] = [
        g["r1"],
        g["r1b"],
        g["l1b"],
        g["l1"],
        g["l2"],
        g["l2b"],
        g["r2b"],
        g["r2"],
    ]
    mid = lambda a, b: pt((a["x"] + b["x"]) / 2, (a["y"] + b["y"]) / 2)
    g["eds"] = {
        "l": {
            "p1": g["l1"],
            "p2": g["l2"],
            "c": mid(g["l1"], g["l2"]),
            "length": r3(t1 - t0),
        },
        "r": {
            "p1": g["r1"],
            "p2": g["r2"],
            "c": mid(g["r1"], g["r2"]),
            "length": r3(t1 - t0),
        },
    }
    g["polygon"] = [g["l1"], g["l2"], g["r2"], g["r1"]]
    g["pc1h"] = pt(*P((t0 + t1) / 2, -(hd + 18)))
    g["_P"] = P
    return g


def _attach(w, h):
    w.setdefault("holes", {})[h["id"]] = h
    return h


def door(w, t0, width, height=210, kind="single", opening="r-l"):
    """kind: single (дверь стандартная) | doorway (проём без двери)."""
    g = _hole_geom(w, t0, t0 + width, 4, 3 if kind == "single" else 0)
    g.pop("_P")
    h = {
        "plan": "a",
        "type": kind,
        "group": "doors",
        "width": width,
        "height": height,
        "depth": 4,
        "opening": opening,
        "id": uid(),
        "parent": w["id"],
        "parent_depth": w["depth"],
        "dls_prs": {},
        "position": "r" if kind == "single" else "c",
        "offset": 3 if kind == "single" else 0,
        "slope_angle": 0,
        "casing": 1 if kind == "single" else 0,
        "casements": 1,
        "p1corner": 0,
        "p2corner": 0,
        "f0offset": 0,
        "room_l": "",
        "room_r": "",
    }
    h.update(g)
    return _attach(w, h)


def window(w, t0, width, height, sill, casements=1):
    g = _hole_geom(w, t0, t0 + width, 6, 0)
    g.pop("_P")
    h = {
        "plan": "a",
        "type": "window",
        "group": "windows",
        "width": width,
        "height": height,
        "depth": 6,
        "floor_height": sill,
        "slopes": 20,
        "opening": "r-l",
        "id": uid(),
        "parent": w["id"],
        "parent_depth": w["depth"],
        "dls_prs": {},
        "position": "c",
        "offset": 0,
        "slope_angle": 0,
        "casing": 1,
        "casements": casements,
        "sill": {"thinkness": 4, "overhang": 0, "overmeasure": 0, "side": "r"},
        "room_l": "",
        "room_r": "",
        "p1corner": 0,
        "p2corner": 0,
    }
    h.update(g)
    return _attach(w, h)


def windoor(
    w, t0, door_width, window_width, door_height, window_height, door_position="l"
):
    """Балконный блок. В образце door_position 'l' = дверь у p1 проёма (connection_point = p1 + door_width)."""
    width = door_width + window_width
    g = _hole_geom(w, t0, t0 + width, 6, 0)
    P = g.pop("_P")
    hd = w["depth"] / 2
    tc = t0 + door_width if door_position == "l" else t0 + window_width
    twin = (
        (t0 + door_width + t0 + width) / 2
        if door_position == "l"
        else (t0 + t0 + window_width) / 2
    )
    h = {
        "plan": "a",
        "type": "windoor",
        "group": "windows",
        "width": width,
        "depth": 6,
        "window_width": window_width,
        "window_height": window_height,
        "door_width": door_width,
        "door_height": door_height,
        "door_position": door_position,
        "opening": "r-l",
        "id": uid(),
        "parent": w["id"],
        "parent_depth": w["depth"],
        "dls_prs": {},
        "position": "c",
        "offset": 0,
        "floor_height": 10,
        "slope_angle": 0,
        "casing": 1,
        "casements": 1,
        "sill": {"thinkness": 4, "overhang": 0, "overmeasure": 0, "side": "r"},
        "room_l": "",
        "room_r": "",
        "p1corner": 0,
        "p2corner": 0,
        "lc": pt(*P(tc, 3)),
        "rc": pt(*P(tc, -3)),
        "connection_point": pt(*P(tc)),
        "pcl": pt(*P(tc, hd)),
        "pcr": pt(*P(tc, -hd)),
        "pc2h": pt(*P(twin, hd + 26)),
    }
    h.update(g)
    return _attach(w, h)


# Точка pc у некоторых моделей не в центре значка: RemPlanner рисует значок со сдвигом к стене (спинке).
# Плита 102: icon_center = pc + 14,1 см в сторону спинки (все образцы tools/reference/remplanner_example_v3_*.plan,
# угол 0 и 180). Без поправки плита на снимке уходила в стену на 14 см.
PC_SHIFT = {"stove": 14.1}


def item(name, cx, cy, width=None, height=None, angle=0, **over):
    """width/height — габарит в плане при angle 0; None — размер по умолчанию из полного каталога.
    (cx, cy) — центр габарита; для моделей из PC_SHIFT pc сдвигается от спинки, значок остаётся в габарите."""
    c = spec(name)
    if width is None or height is None:
        e = info(name)
        if not e:
            spec(name)  # SystemExit: сведений о предмете нет
        dw, dh = e["width"], e["height"]
        width, height = width or dw, height or dh
    i = uid()
    k = PC_SHIFT.get(name, 0)
    t = math.radians(angle)
    px, py = cx + k * math.sin(t), cy - k * math.cos(t)  # спинка при angle θ — направление (−sin θ, cos θ)
    it = {
        "name": name,
        "pc": pt(px, py),
        "angle": angle,
        "width": width,
        "height": height,
        "plan": copy.deepcopy(c["plan"]),
        "id": i,
        "item_id": c["item_id"],
        "self_height": c["self_height"],
        "comment": {"id": ""},
        "dimensions": {"display": True},
        "f0offset": 0,
        "dls": {"l": {}, "r": {}},
        "dls_prs": {"v": {}, "h": {}},
        "icon_center": pt(cx, cy),
        "center3d": pt(cx, cy),
    }
    for k, v in c.items():
        if k not in ("item_id", "plan", "self_height", "size"):
            it[k] = copy.deepcopy(v)
    for k, v in over.items():
        if k == "over_floor":
            it["over_floor"] = {"value": v, "display": False}
        else:
            it[k] = v
    return it


def new_plan(walls, items=(), pillars=()):
    tpl = json.load(
        open(os.path.join(REF, "remplanner_example_v3_one_wall.plan"), encoding="utf-8")
    )
    out = copy.deepcopy(tpl)
    p = out["plan"]
    p["walls"] = {w["id"]: w for w in walls}
    p["items"] = {it["id"]: it for it in items}
    p["pillars"] = {pl["id"]: pl for pl in pillars}
    p["drawings"] = [[w["l2"], w["r2"], w["r1"], w["l1"]] for w in walls]
    xs = [q["x"] for w in walls for q in (w["l1"], w["l2"], w["r1"], w["r2"])]
    ys = [q["y"] for w in walls for q in (w["l1"], w["l2"], w["r1"], w["r2"])]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    p["drawing"] = {
        "x_min": x0,
        "x_max": x1,
        "y_min": y0,
        "y_max": y1,
        "cx": (x0 + x1) / 2,
        "cy": (y0 + y1) / 2,
        "center": {"x": (x0 + x1) / 2, "y": (y0 + y1) / 2},
        "tl_point": {"x": x0, "y": y0},
        "br_point": {"x": x1, "y": y1},
        "width": x1 - x0,
        "height": y1 - y0,
    }
    p["total_height"] = HEIGHT
    return out


def dump(plan, path):
    json.dump(
        plan,
        open(path, "w", encoding="utf-8"),
        ensure_ascii=False,
        separators=(",", ":"),
    )
