#!/usr/bin/env python3
"""check_rules.py [-v] [--rules <rules.json>] <plan.json ...> — правила жильцов, которых нет в эргономике.
Правила читаются из ROOT/rules.json (ROOT — папка проекта, родитель tools/) или из --rules; типы правил,
их параметры и примеры — tools/reference/RULES.md, стартовый набор — tools/reference/rules.example.json.

rules.json:
  "rooms"        — роли комнат: роль → префиксы rooms[].id (мокрые wet, спальня bedroom, туалет toilet…);
                   в параметрах правил комнаты задаются ролями, неизвестная роль — сама считается префиксом;
  "entry_radius" — «у входа»: не дальше стольких см от середины входной двери (`"entry": true`, иначе
                   id `door-entry`);
  "drain"        — точка подключения канализации `point` [x, y] (если не задана — см. drain_point) и уклон
                   `slope`;
  "as_is"        — путь к плану «как есть» от ROOT (по умолчанию plan/as_is.json);
  "rules"        — список {"id": "п. N", "check": "<тип>", ...параметры, "text": "…", "source": "…",
                   "enabled": false — выключено}. Сообщение о нарушении начинается с id правила.
Предметы в параметрах `items`, `beds` — регулярные выражения по имени каталога (`rp.name`, re.search): "ward" —
любой шкаф, "^tv$" — ровно tv. Предмет в комнате — его центр внутри rooms[].rect.

Трасса канализации (drain_routes) — от точки подключения до каждого прибора с канализацией: по полу мокрых
комнат, сквозь перегородки, но не по полу коридоров и комнат и не под дверными проёмами; вдоль несущих стен —
только с их внутренней стороны. Печатает длину трассы и перепад при уклоне slope — по нему подиум или короб.
Итог: «ok» или «НЕ ПРОХОДИТ» с перечнем; -v печатает и пройденные правила, и трассы."""

import json
import math
import os
import re
import sys
from collections import deque

import rp_lib
from rp_lib import KITCHEN

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # корень проекта — родитель tools/
STEP = 5
X0 = Y0 = 0  # привязка клеток трассы (кратно STEP)

DEFAULTS = {
    "as_is": "plan/as_is.json",
    "entry_radius": 250,  # предположение: от середины входной двери — в пределах прихожей
    "drain": {"point": None, "slope": 0.025},  # предположение: 2–3 см на метр (ориентир СП 30.13330, не сверен)
    "rooms": {
        "wet": ["bath", "guest", "wc", "kitchen", "laundry"],
        "bedroom": ["bed"],
        "walkin": ["walkin"],
        "toilet": ["wc"],
        "bathroom": ["bath"],
        "sanitary": ["bath", "wc", "shower"],
        "kitchen": ["kitchen"],
        "loggia": ["loggia"],
    },
}
COMMON = {"id", "check", "text", "source", "enabled", "note"}
BEDS = ["^bed_(double|single|near_wall)", "bed_transformer", "^ottoman_bed"]  # взрослые кровати каталога
TOILETS = ["^toilet(_with_frame|_embedded|_impulse)?$", "^corner_toilet$"]  # без toilet_paper, toilet_brush…

# Параметры каждого типа и их значения по умолчанию (REQ — обязательный, None — не задан).
REQ = ...
TYPES = {
    "near_entry": {"items": REQ, "what": "нужного предмета", "max_dist": None, "min_front": 0, "min_depth": 0,
                   "exclude_rooms": []},
    "bedroom_storage": {"beds": BEDS, "items": ["ward"], "extra_rooms": ["walkin"], "min_front": 0},
    "drain_routes": {"wet_rooms": "wet", "toilet": TOILETS, "toilet_max": 100, "point": None, "slope": None},
    "window_full": {"window": REQ, "min_length": REQ, "waiver": None},
    "window_clear": {"window": REQ, "gap": 30, "max_height": 90},
    "items_in_rooms": {"items": REQ, "rooms": REQ},
    "behind_door": {"items": REQ, "forbid_rooms": [], "need_door": True},
    "kitchen_straight": {"rooms": "kitchen",
                         "items": ["kitchen_run", "kitchen_box", "fridge", "built_in_fridge", "pencil_case",
                                   "worktop"]},
    "no_corner_join": {"items": ["ward"], "tol": 5},
    "min_size": {"items": REQ, "min_width": REQ, "measure": "long", "need": "any", "exclude_rooms": [],
                 "what": "нужного предмета"},
    "room_has": {"items": REQ, "rooms": None, "required": False},
}


# ── Предметы и комнаты ─────────────────────────────────────────────────────────────────────────────────


def specs(f):
    s = f.get("rp")
    return (s if isinstance(s, list) else [s]) if s else []


def cat(name):
    """Запись каталога (без полного каталога — для имён CATALOG и confirmed.json, rp_lib.info)."""
    return rp_lib.info(name)


def has(f, pats, modules=False):
    """Предмет подходит под шаблоны: имя любого rp (или, при modules, модуль kitchen_run) — re.search."""
    for sp in specs(f):
        names = [sp["name"]] + (list(sp.get("modules", [])) if modules else [])
        if any(re.search(p, nm) for p in pats for nm in names):
            return True
    return False


def front(f):
    """(ширина фасада, глубина) по спинке."""
    x, y, w, h = f["rect"]
    back = specs(f)[0]["back"]
    return (w, h) if back in ("up", "down") else (h, w)


def inside(f, r):
    x, y, w, h = f["rect"]
    rx, ry, rw, rh = r["rect"]
    return rx <= x + w / 2 <= rx + rw and ry <= y + h / 2 <= ry + rh


def door_mid(d):
    return (d["hinge"][0] + d["other"][0]) / 2, (d["hinge"][1] + d["other"][1]) / 2


def door_on(d, r):
    """Дверь в стене комнаты r: середина проёма в 30 см от её границы (наружная стена 26), в пределах стороны."""
    x, y, w, h = r["rect"]
    mx, my = door_mid(d)
    near_x = min(abs(mx - x), abs(mx - x - w)) <= 30 and y <= my <= y + h
    near_y = min(abs(my - y), abs(my - y - h)) <= 30 and x <= mx <= x + w
    return near_x or near_y


def rect_dist(f, pt):
    x, y, w, h = f["rect"]
    return math.hypot(max(x - pt[0], 0, pt[0] - x - w), max(y - pt[1], 0, pt[1] - y - h))


class Ctx:
    """План и настройки: комнаты по ролям, вход, точка подключения."""

    def __init__(self, p, cfg):
        self.p, self.cfg = p, cfg
        self.furn = p["furniture"]
        self.rooms = [r for r in p["rooms"] if r.get("rect")]
        self._routes = None

    def prefixes(self, roles):
        roles = [roles] if isinstance(roles, str) else roles
        out = []
        for role in roles:
            out += self.cfg["rooms"].get(role, [role])
        return tuple(out)

    def role(self, roles, need_rect=True):
        pre = self.prefixes(roles)
        return [r for r in (self.rooms if need_rect else self.p["rooms"]) if r["id"].startswith(pre)]

    def in_role(self, f, roles):
        return any(inside(f, r) for r in self.role(roles)) if roles else False

    def entry(self):
        ds = [d for d in self.p["doors"] if d.get("entry")] or [d for d in self.p["doors"] if d["id"] == "door-entry"]
        return door_mid(ds[0]) if ds else None


# ── Канализация ────────────────────────────────────────────────────────────────────────────────────────


def drains(f):
    """Приборы с канализацией в предмете: [(имя, точка выпуска)]."""
    out = []
    x, y, w, h = f["rect"]
    for sp in specs(f):
        nm = sp["name"]
        if nm == "kitchen_run":
            along_x = sp["back"] in ("up", "down")
            a = 0
            for m in sp["modules"]:
                n = 60 if m in KITCHEN else cat(m).get("width", 60)
                if m in ("sink", "washer", "dishwasher") or cat(m).get("custom_type") == "sink":
                    c = (x + a + n / 2, y + h / 2) if along_x else (x + w / 2, y + a + n / 2)
                    out.append((f"{f['id']}:{m}", c))
                a += n
            continue
        sd = cat(nm).get("santeh_data") or {}
        if "drainage_pipe" in sd.get("pipes", []):
            out.append((f"{f['id']}", (x + w / 2, y + h / 2)))
            break
    return out


def drain_point(cfg, toilet):
    """Точка подключения канализации: drain.point в rules.json (или в правиле); иначе fixed_elements с
    `kind: "drain"` в плане «как есть» (`point` или центр `rect`); иначе унитаз «как есть» — середина его спинки,
    10 см внутрь. Возвращает ((x, y), откуда) или (None, причина)."""
    if cfg.get("point"):
        return tuple(cfg["point"]), "rules.json"
    path = os.path.join(ROOT, cfg["as_is"])
    if not os.path.exists(path):
        return None, f"нет {cfg['as_is']} и drain.point в rules.json"
    a = json.load(open(path, encoding="utf-8"))
    for e in a.get("fixed_elements", []):
        if e.get("kind") == "drain":
            if e.get("point"):
                return tuple(e["point"]), f"{e['id']} в {cfg['as_is']}"
            x, y, w, h = e["rect"]
            return (x + w / 2, y + h / 2), f"{e['id']} в {cfg['as_is']}"
    wcs = [f for f in a["furniture"] if has(f, toilet) and drains(f)]
    if not wcs:
        return None, f"в {cfg['as_is']} нет ни fixed_elements kind drain, ни унитаза"
    f = next((f for f in wcs if f["id"] == "wc"), wcs[0])
    x, y, w, h = f["rect"]
    back = specs(f)[0]["back"]
    pt = {
        "down": (x + w / 2, y + h - 10),
        "up": (x + w / 2, y + 10),
        "left": (x + 10, y + h / 2),
        "right": (x + w - 10, y + h / 2),
    }[back]
    return pt, f"унитаз {f['id']} в {cfg['as_is']}"


def grid_cells(rect):
    x, y, w, h = rect
    i0, i1 = int((x - X0) // STEP), int(math.ceil((x + w - X0) / STEP))
    j0, j1 = int((y - Y0) // STEP), int(math.ceil((y + h - Y0) / STEP))
    return [(i, j) for i in range(i0, i1) for j in range(j0, j1)]


def door_box(d):
    (hx, hy), (ox, oy) = d["hinge"], d["other"]
    if hy == oy:
        return [min(hx, ox), hy - 15, abs(ox - hx), 30]
    return [hx - 15, min(hy, oy), 30, abs(oy - hy)]


def routes(c, P, wet_role):
    """Трассы от точки подключения: BFS по клеткам мокрых комнат и перегородок, без дверных проёмов."""
    p = c.p
    ok = set()
    wet = c.role(wet_role, need_rect=False)
    missing = [r["id"] for r in wet if not r.get("rect")]
    for r in wet:
        if r.get("rect"):
            ok.update(grid_cells(r["rect"]))
    for w in p["partitions"]:
        ok.update(grid_cells(w["rect"]))
    devices = [(n, pt, f) for f in p["furniture"] for n, pt in drains(f)]
    for _, _, f in devices:  # прибор в нише за стеной санузла — его собственный габарит тоже допустим
        ok.update(grid_cells(f["rect"]))
    for d in p["doors"]:
        ok.difference_update(grid_cells(door_box(d)))
    # точка подключения — обычно в стене за унитазом: стартуем со всех допустимых клеток в 20 см от неё
    seed = [q for q in grid_cells([P[0] - 20, P[1] - 20, 40, 40]) if q in ok]
    dist = {q: 0.0 for q in seed}
    queue = deque(seed)
    while queue:
        q = queue.popleft()
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (q[0] + di, q[1] + dj)
            if n in ok and n not in dist:
                dist[n] = dist[q] + STEP
                queue.append(n)
    out = []
    for name, (cx, cy), f in devices:
        best = min((dist[q] for q in grid_cells(f["rect"]) if q in dist), default=None)
        if best is not None:  # до выпуска внутри прибора
            best += abs(cx - (f["rect"][0] + f["rect"][2] / 2)) + abs(cy - (f["rect"][1] + f["rect"][3] / 2))
        out.append((name, best, f))
    return out, missing


# ── Типы правил: (ctx, правило) → [(ok, сообщение)] ────────────────────────────────────────────────────


def r_near_entry(c, r):
    e = c.entry()
    if e is None:
        return [(False, 'нет входной двери ("entry": true или id door-entry)')]
    lim = r["max_dist"] if r["max_dist"] is not None else c.cfg["entry_radius"]
    cand = [f for f in c.furn if has(f, r["items"]) and not c.in_role(f, r["exclude_rooms"])]
    near = [f for f in cand if rect_dist(f, e) <= lim]
    sized = r["min_front"] or r["min_depth"]
    good = [f for f in near if front(f)[0] >= r["min_front"] and front(f)[1] >= r["min_depth"]]
    if good:
        f = min(good, key=lambda q: rect_dist(q, e))
        size = f" {front(f)[0]}×{front(f)[1]}" if sized else ""
        return [(True, f"у входа {f['id']}{size} в {rect_dist(f, e):.0f} см")]
    if sized:
        have = ", ".join(f"{f['id']} {front(f)[0]}×{front(f)[1]}" for f in near) or "нет"
        return [(False, f"у входа (≤ {lim} см) нет {r['what']} ≥ {r['min_front']}×{r['min_depth']} (есть: {have})")]
    far = min(((rect_dist(f, e), f["id"]) for f in cand), default=None)
    tail = f" (ближайший {far[1]} в {far[0]:.0f} см)" if far else ""
    return [(False, f"у входа (≤ {lim} см) нет {r['what']}{tail}")]


def r_bedroom_storage(c, r):
    out = []
    extra = c.role(r["extra_rooms"]) if r["extra_rooms"] else []
    for room in c.rooms:
        if not any(inside(f, room) for f in c.furn if has(f, r["beds"])):
            continue
        ws = [f for f in c.furn if has(f, r["items"]) and any(inside(f, q) for q in [room] + extra)]
        total = sum(front(f)[0] for f in ws)
        if not ws:
            out.append((False, f"в комнате {room['id']} с кроватью нет шкафа"))
        elif total < r["min_front"]:
            out.append((False, f"в комнате {room['id']} с кроватью шкафы {total} по фасаду (нужно ≥ {r['min_front']})"))
        else:
            out.append((True, f"{room['id']} — шкафы {total} по фасаду: {', '.join(f['id'] for f in ws)}"))
    return out or [(True, "комнат с кроватью (с rect) нет — не проверено")]


def r_drain_routes(c, r):
    dcfg = dict(c.cfg["drain"], as_is=c.cfg["as_is"])
    if r["point"]:
        dcfg["point"] = r["point"]
    slope = r["slope"] if r["slope"] is not None else dcfg["slope"]
    P, src = drain_point(dcfg, r["toilet"])
    if P is None:
        return [(False, f"нет точки подключения канализации: {src}")]
    rts, missing = routes(c, P, r["wet_rooms"])
    out = [(True, f"точка подключения ({P[0]:.0f}, {P[1]:.0f}) — {src}")]
    out += [(False, f"у мокрой комнаты {m} нет rect — трассу не построить") for m in missing]
    for name, L, f in rts:
        if L is None:
            out.append((False, f"к {name} нет трассы канализации от точки подключения (через коридор/дверь)"))
        elif has(f, r["toilet"]) and L > r["toilet_max"]:
            out.append((False, f"унитаз {name} в {L:.0f} см от точки подключения (нужно ≤ {r['toilet_max']})"))
        else:
            out.append((True, f"{name} — трасса {L / 100:.1f} м, перепад {L * slope:.0f} см"))
    return out


def window(c, wid):
    return next((w for w in c.p.get("windows", []) if w["id"] == wid), None)


def r_window_full(c, r):
    w = window(c, r["window"])
    if w is None:
        return [(True, f"окна {r['window']} в плане нет — не проверено")]
    L = max(w["rect"][2], w["rect"][3])
    if L < r["min_length"] and not (r["waiver"] and c.p.get(r["waiver"])):
        return [(False, f"окно {r['window']} заложено ({L} из {r['min_length']}) без обоснования {r['waiver']}")]
    return [(True, f"окно {r['window']} {L} из {r['min_length']}")]


def r_window_clear(c, r):
    w = window(c, r["window"])
    if w is None:
        return [(True, f"окна {r['window']} в плане нет — не проверено")]
    wx, wy, ww, wh = w["rect"]
    out = []
    for f in c.furn:
        x, y, fw, fh = f["rect"]
        gap = math.hypot(max(wx - (x + fw), x - (wx + ww), 0), max(wy - (y + fh), y - (wy + wh), 0))
        if gap >= r["gap"]:
            continue
        for s in specs(f):
            e = cat(s["name"])
            over = (e.get("over_floor") or {}).get("value") or 0
            top = over + (e.get("self_height") or (5 if over else 200))  # высота 0 в каталоге — не задана
            if top > r["max_height"] and over < r["max_height"]:
                out.append((False, f"{f['id']} (высота {top}) стоит перед окном {r['window']} (ближе {r['gap']} см)"))
                break
    return out or [(True, f"перед окном {r['window']} высокой мебели нет")]


def r_items_in_rooms(c, r):
    out = []
    for f in c.furn:
        if has(f, r["items"]):
            ok = c.in_role(f, r["rooms"])
            where = "/".join(q + "*" for q in c.prefixes(r["rooms"]))
            out.append((ok, f"{f['id']} " + ("на месте" if ok else f"не в комнатах {where}")))
    return out or [(True, "подходящих предметов нет — не проверено")]


def r_behind_door(c, r):
    out = []
    for f in c.furn:
        if not has(f, r["items"]):
            continue
        room = next((q for q in c.rooms if inside(f, q)), None)
        if room is None:
            out.append((False, f"{f['id']} не в комнате с rect — не проверить дверь"))
        elif r["forbid_rooms"] and room["id"].startswith(c.prefixes(r["forbid_rooms"])):
            out.append((False, f"{f['id']} в комнате {room['id']} — здесь его быть не должно"))
        elif r["need_door"] and not any(door_on(d, room) and d.get("kind", "single") != "doorway" for d in c.p["doors"]):
            out.append((False, f"у комнаты {room['id']} с {f['id']} нет двери"))
        else:
            out.append((True, f"{f['id']} — {room['id']}" + (" с дверью" if r["need_door"] else "")))
    return out or [(True, "подходящих предметов нет — не проверено")]


def r_kitchen_straight(c, r):
    out = []
    for room in c.role(r["rooms"]):
        units = [f for f in c.furn if inside(f, room) and has(f, r["items"])]
        axes = {specs(f)[0]["back"] in ("up", "down") for f in units}
        if len(axes) > 1:
            out.append((False, f"кухня {room['id']} Г-образная — модули по двум осям"))
        else:
            out.append((True, f"кухня {room['id']} прямая или в два ряда"))
    return out or [(True, "кухни с rect нет — не проверено")]


def r_no_corner_join(c, r):
    ws = [f for f in c.furn if has(f, r["items"])]
    t = r["tol"]
    out = []
    for i, a in enumerate(ws):
        for b in ws[i + 1:]:
            if (specs(a)[0]["back"] in ("up", "down")) == (specs(b)[0]["back"] in ("up", "down")):
                continue
            ax, ay, aw, ah = a["rect"]
            bx, by, bw, bh = b["rect"]
            if ax - t <= bx + bw and bx - t <= ax + aw and ay - t <= by + bh and by - t <= ay + ah:
                out.append((False, f"{a['id']} и {b['id']} стыкуются углом (Г-образно)"))
    return out or [(True, f"угловых стыков нет ({len(ws)} шт.)")]


def r_min_size(c, r):
    items = [f for f in c.furn if has(f, r["items"]) and not c.in_role(f, r["exclude_rooms"])]
    size = (lambda f: front(f)[0]) if r["measure"] == "front" else (lambda f: max(f["rect"][2], f["rect"][3]))
    lim = r["min_width"]
    if r["need"] == "each":
        out = []
        for f in items:
            ok = size(f) >= lim
            out.append((ok, f"{f['id']} шириной {size(f)}" + ("" if ok else f" (нужно ≥ {lim})")))
        return out or [(True, "подходящих предметов нет — не проверено")]
    good = [f for f in items if size(f) >= lim]
    if not good:
        have = ", ".join(f"{f['id']} {size(f)}" for f in items) or "нет"
        return [(False, f"нет {r['what']} шириной ≥ {lim} (есть: {have})")]
    return [(True, f"{good[0]['id']} шириной {size(good[0])}")]


def r_room_has(c, r):
    if r["rooms"]:
        roles = [r["rooms"]] if isinstance(r["rooms"], str) else r["rooms"]
        rooms = next((rs for rs in (c.role(x) for x in roles) if rs), [])  # первая роль, у которой есть комнаты
        if not rooms:
            msg = f"нет комнаты {' или '.join(p + '*' for p in c.prefixes(roles))} с rect"
            return [(not r["required"], msg + ("" if r["required"] else " — не проверено"))]
    else:
        rooms = [None]  # весь план
    out = []
    for room in rooms:
        miss = []
        for label, spec in r["items"].items():
            spec = spec if isinstance(spec, dict) else {"items": spec}
            found = [f for f in c.furn if has(f, spec["items"], spec.get("modules", False))
                     and (room is None or inside(f, room))]
            if spec.get("sizes"):
                dims = [sorted(f["rect"][2:]) for f in found]
                if not any(a >= m and b >= M for a, b in dims for m, M in (sorted(s) for s in spec["sizes"])):
                    have = ", ".join(f"{a}×{b}" for a, b in dims) or "нет"
                    miss.append(f"{label} (есть: {have})")
            elif not found:
                miss.append(label)
        where = f"в {room['id']}" if room else "в плане"
        out.append((not miss, f"{where} нет: {', '.join(miss)}" if miss else f"{where} есть: {', '.join(r['items'])}"))
    return out


CHECKS = {name: globals()["r_" + name] for name in TYPES}


# ── Загрузка правил и проверка ─────────────────────────────────────────────────────────────────────────


def load_rules(path):
    """rules.json → (настройки, правила с параметрами по умолчанию, ошибки в самом файле)."""
    raw = json.load(open(path, encoding="utf-8"))
    cfg = {k: v for k, v in DEFAULTS.items()}
    for k in ("as_is", "entry_radius"):
        if k in raw:
            cfg[k] = raw[k]
    cfg["drain"] = dict(DEFAULTS["drain"], **raw.get("drain", {}))
    cfg["rooms"] = dict(DEFAULTS["rooms"], **raw.get("rooms", {}))
    rules, bad = [], []
    for n, r in enumerate(raw.get("rules", [])):
        rid = r.get("id", f"правило №{n + 1}")
        t = r.get("check")
        if t not in TYPES:
            bad.append(f"{rid}: неизвестный тип check «{t}» (есть: {', '.join(TYPES)})")
            continue
        extra = set(r) - COMMON - set(TYPES[t])
        if extra:
            bad.append(f"{rid}: у {t} нет параметров {', '.join(sorted(extra))}")
        need = [k for k, v in TYPES[t].items() if v is REQ and r.get(k) is None]
        if need:
            bad.append(f"{rid}: у {t} не заданы {', '.join(need)}")
            continue
        rules.append({**TYPES[t], **r, "id": rid})
    return cfg, rules, bad


def check(path, cfg, rules):
    p = json.load(open(path, encoding="utf-8"))
    rp_lib.check_names(p, path)
    c = Ctx(p, cfg)
    errs, info = [], []
    for r in rules:
        if r.get("enabled", True) is False:
            info.append(f"{r['id']}: выключено")
            continue
        for ok, msg in CHECKS[r["check"]](c, r):
            (info if ok else errs).append(f"{r['id']}: {msg}")
    return errs, info


def main(argv):
    verbose = "-v" in argv
    args = [a for a in argv if a != "-v"]
    rules_path = os.path.join(ROOT, "rules.json")
    if "--rules" in args:
        i = args.index("--rules")
        rules_path = args[i + 1]
        del args[i : i + 2]
    if not os.path.exists(rules_path):
        print(f"нет {os.path.normpath(rules_path)}: скопируйте tools/reference/rules.example.json в rules.json "
              "проекта или укажите --rules <path>", file=sys.stderr)
        return 2
    cfg, rules, bad = load_rules(rules_path)
    if bad:
        print(f"{rules_path}: ошибки в правилах", file=sys.stderr)
        for b in bad:
            print("  ✗ " + b, file=sys.stderr)
        return 2
    rc = 0
    for a in args:
        errs, info = check(a, cfg, rules)
        print(f"{a}: {'ok' if not errs else 'НЕ ПРОХОДИТ'}")
        for e in errs:
            print("  ✗ " + e)
        if verbose:
            for i in info:
                print("  · " + i)
        rc |= bool(errs)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
