#!/usr/bin/env python3
"""check_layout.py [-w] [-v] <plan.json ...> — проверка эргономики плана по правилам tools/ergonomics.py
(«минимально допустимо» / «желательно», уступки и бюджет; описание и источники — tools/reference/ERGONOMICS.md).
Вывод: строка на план и только проблемы (ниже минимума, уступка без обоснования, лишнее обоснование, бюджет);
-w — ещё принятые уступки с обоснованием (для README серии), -v — ещё и все пройденные правила.

Модель: сетка STEP см по габариту плана (все rect стен, мебели, окон, зон и комнат, проёмы дверей + MARGIN);
препятствия — стены (несущие, перегородки, утепление) и мебель. В стенах прорезаны дверные проёмы (`doors`).
Для каждой клетки считается расстояние до ближайшего препятствия d.
Вход в квартиру — дверь с `"entry": true`, иначе дверь с id `door-entry` (поле `kind` не годится: экспортёр
передаёт его в RemPlanner как тип двери). Маршруты начинаются в START см от середины входной двери в сторону
открывания `swing` (внутрь квартиры); входную дверь не проверяют door_width/door_open и не делают целью прохода.
Измерения:
- проходы: «самый широкий путь» от входа (клетки с d ≥ w/2) к каждой цели — зонам `zones`, месту стоящего
  человека в 30 см перед лицевой стороной предмета, обеим сторонам каждой межкомнатной двери (в 45 см от
  полотна). В круге радиуса w/2 + 10 у каждого проёма сужение не считается: ширину двери проверяет своё правило;
- зоны перед предметами: свободная глубина от лицевой грани (кровать — бока и изножье, без 55 см у изголовья,
  где тумбы) до первого препятствия; для унитаза и раковины — ещё от оси до боковых препятствий;
- двери: угол, на который полотно открывается до мебели/стены; пересечение створок двух дверей;
- выступающие углы на маршрутах: кратчайший путь от входа к каждой цели (плечи 55) поворачивает у угла стены
  или мебели — меряется ширина прохода у этого угла (свободное место по обеим граням и по биссектрисе);
- кухня (`kitchen_run`): столешница по бокам плиты, между мойкой и плитой, рабочий треугольник
  мойка–плита–холодильник, плита — окно;
- ТВ: расстояние от глаз (диван, кровать напротив) в диагоналях и угол в сторону от оси;
- рабочий стол: окно сбоку, а не перед лицом или за спиной.
Препятствия для проходов — без навесного с низом ≥ 100 см и переставляемого (SKIP, стулья); для зон перед
предметами столы считаются, стулья — нет. Не проверяет: высоты, навесные шкафы, свет и розетки (их нет в плане) —
это ручные правила из tools/reference/ERGONOMICS.md."""

import heapq
import json
import math
import sys

import ergonomics as E
import rp_lib
from remplanner_export import KITCHEN

STEP = 2
MARGIN = 20  # запас сетки вокруг габарита плана, см: снаружи входной двери тоже есть клетки
START = 40  # старт маршрутов: от середины входной двери внутрь квартиры, см
# Сетка — по габариту текущего плана, задаёт set_grid(p) (Plan вызывает её сам); функции модуля работают с ней.
X0, Y0, X1, Y1 = 0, 0, STEP, STEP
NX, NY = 1, 1
INF = 10**9
SKIP = {
    "tv",
    "bathroom_mirror",
    "chair",
    "office_chair",
    "table",
    "dryer",
    "towel_dryer",
    "bar_chair_backrest",
    "folding_wall_table",
    "tetra_stillage",
}  # навесное, переставляемое
NO_TARGET = {
    "tv",
    "bathroom_mirror",
    "chair",
    "office_chair",
    "table",
    "worktop",
    "kitchen_sink",
    "dryer",
    "towel_dryer",
    "bar_chair_backrest",
    "table_round",
    "bar_table",
    "folding_wall_table",
    "tetra_stillage",
}
LIGHT = {"tv", "bathroom_mirror", "towel_dryer", "dryer_on_wall", "folding_wall_table"}  # не мешают стоять перед предметом
FRONT = {
    "down": (0, -1),
    "up": (0, 1),
    "left": (1, 0),
    "right": (-1, 0),
}  # куда смотрит лицо при back=…
CHAIRS = {"chair", "office_chair", "bar_chair_backrest"}
SEATS = {"sofa_triple", "sofa_double", "bed_double"}
TALL_KITCHEN = {
    "built_in_fridge",
    "fridge",
    "pencil_case_oven_microwave",
    "kitchen_box_penal",
}
FRIDGES = {"built_in_fridge", "fridge"}
HINGED = {  # шкафы с распашными дверями (купе, гармошка, открытые — ward_front)
    "ward_single",
    "ward",
    "threedoor_ward",
    "ward_double",
    "pencil_cabinet_above_washing",
    "floor_pencil_cabinet",
    "cupboard_with_drawers",
    "corner_cabinet",
    "double_leaf_corner_section",
    "single_leaf_corner_section",
}


def _cat(name):
    return rp_lib.full_catalog().get(name, {})


def skip(name):
    e = _cat(name)
    of = e.get("over_floor") or {}
    return name in SKIP or of.get("value", 0) >= 100 or e.get("custom_type") == "chair"


def no_target(name):
    return name in NO_TARGET or skip(name) or _cat(name).get("custom_type") == "sink"


def light(name):
    e = _cat(name)
    of = e.get("over_floor") or {}
    return (
        name in LIGHT
        or name in CHAIRS
        or of.get("value", 0) >= 100
        or e.get("custom_type") == "chair"
    )


def specs(f):
    s = f.get("rp")
    return (s if isinstance(s, list) else [s]) if s else []


def kind(f):
    s = specs(f)
    return s[0]["name"] if s else None


def cells(rect):
    x, y, w, h = rect
    i0, i1 = max(0, int((x - X0) // STEP)), min(NX, int(math.ceil((x + w - X0) / STEP)))
    j0, j1 = max(0, int((y - Y0) // STEP)), min(NY, int(math.ceil((y + h - Y0) / STEP)))
    return [(i, j) for j in range(j0, j1) for i in range(i0, i1)]


def k_of(x, y):
    i, j = int((x - X0) // STEP), int((y - Y0) // STEP)
    return j * NX + i if 0 <= i < NX and 0 <= j < NY else None


def xy_of(k):
    return X0 + (k % NX + 0.5) * STEP, Y0 + (k // NX + 0.5) * STEP


def door_box(d):
    (hx, hy), (ox, oy) = d["hinge"], d["other"]
    if hy == oy:
        return [min(hx, ox) + 1, hy - 30, abs(ox - hx) - 2, 60]
    return [hx - 30, min(hy, oy) + 1, 60, abs(oy - hy) - 2]


def door_center(d):
    (hx, hy), (ox, oy) = d["hinge"], d["other"]
    return (hx + ox) / 2, (hy + oy) / 2


def is_entry(d):
    """Входная дверь квартиры: `"entry": true`, иначе id `door-entry`."""
    return bool(d.get("entry")) or d["id"] == "door-entry"


def entry_door(p):
    doors = [d for d in p["doors"] if d.get("entry")] or [d for d in p["doors"] if d["id"] == "door-entry"]
    if not doors:
        raise SystemExit('нет входной двери: пометьте её в doors полем "entry": true (или id "door-entry")')
    return doors[0]


def entry_start(p):
    """Точка старта маршрутов: START см от середины входной двери в сторону открывания (внутрь)."""
    d = entry_door(p)
    cx, cy = door_center(d)
    sx, sy = d["swing"]
    return cx + sx * START, cy + sy * START


def set_grid(p):
    """Границы сетки по габариту плана: все rect (стены, утепление, мебель, окна, зоны, комнаты) и проёмы
    дверей + MARGIN, выровнено по STEP."""
    global X0, Y0, X1, Y1, NX, NY
    rects = [
        o["rect"]
        for key in ("walls_bearing", "partitions", "insulation", "furniture", "windows", "zones", "rooms")
        for o in p.get(key, [])
        if o.get("rect")
    ] + [door_box(d) for d in p["doors"]]
    X0 = math.floor((min(r[0] for r in rects) - MARGIN) / STEP) * STEP
    Y0 = math.floor((min(r[1] for r in rects) - MARGIN) / STEP) * STEP
    X1 = math.ceil((max(r[0] + r[2] for r in rects) + MARGIN) / STEP) * STEP
    Y1 = math.ceil((max(r[1] + r[3] for r in rects) + MARGIN) / STEP) * STEP
    NX, NY = (X1 - X0) // STEP, (Y1 - Y0) // STEP


class Plan:
    """Сетки препятствий плана: wall — стены с прорезанными проёмами; path — стены + мебель для проходов;
    front — стены + мебель, мешающая стоять перед предметом; owner — какой предмет занимает клетку."""

    def __init__(self, p):
        self.p = p
        set_grid(p)
        n = NX * NY
        self.wall = bytearray(n)
        for r in p["walls_bearing"] + p["partitions"] + p.get("insulation", []):
            for i, j in cells(r["rect"]):
                self.wall[j * NX + i] = 1
        for d in p["doors"]:  # проём: вдоль петля…край, поперёк ±30 см
            for i, j in cells(door_box(d)):
                self.wall[j * NX + i] = 0
        fp, ff = bytearray(n), bytearray(n)
        self.owner = [-1] * n
        for idx, f in enumerate(p["furniture"]):
            names = {s["name"] for s in specs(f)}
            on_path = not (names and all(skip(nm) for nm in names))
            on_front = not (names and all(light(nm) for nm in names))
            for i, j in cells(f["rect"]):
                k = j * NX + i
                if on_path:
                    fp[k] = 1
                if on_front:
                    ff[k] = 1
                if on_path or on_front:
                    self.owner[k] = idx
        self.path = bytearray(a | b for a, b in zip(self.wall, fp))
        self.front = bytearray(a | b for a, b in zip(self.wall, ff))
        self.d = distance(self.path)
        # у проёмов сужение не считается (ширину двери проверяет door_width)
        self.dd = list(self.d)
        for dr in p["doors"]:
            cx, cy = door_center(dr)
            rr = dr["width"] / 2 + 10
            for i, j in cells([cx - rr, cy - rr, 2 * rr, 2 * rr]):
                x, y = xy_of(j * NX + i)
                k = j * NX + i
                if (x - cx) ** 2 + (y - cy) ** 2 <= rr * rr and not self.path[k]:
                    self.dd[k] = INF

    def blocked(self, mask, x, y):
        k = k_of(x, y)
        return True if k is None else bool(mask[k])

    def ray(self, mask, x, y, dx, dy, maxd=400):
        """Свободная длина луча от точки (x, y) по направлению (dx, dy) до препятствия."""
        n = math.hypot(dx, dy)
        dx, dy = dx / n, dy / n
        t = 1.0
        while t < maxd:
            if self.blocked(mask, x + dx * t, y + dy * t):
                return t - 1
            t += STEP / 2
        return maxd

    def sweep(self, rect, side, lo=5, hi=5, joint=(), maxd=400):
        """Свободная глубина перед гранью rect со стороны side=(sx, sy): минимум по точкам грани
        (без lo и hi см по краям, считая от меньшей координаты). Точки, вплотную закрытые предметом из
        joint (индексы мебели — стык угловой кухни), не считаются."""
        mask = self.front
        x, y, w, h = rect
        sx, sy = side
        out = maxd
        if sx:
            fx = x + w + 0.5 if sx > 0 else x - 0.5
            pts = [(fx, y + lo + n * STEP) for n in range(int((h - lo - hi) // STEP) + 1)]
        else:
            fy = y + h + 0.5 if sy > 0 else y - 0.5
            pts = [(x + lo + n * STEP, fy) for n in range(int((w - lo - hi) // STEP) + 1)]
        for px, py in pts:
            v = self.ray(mask, px, py, sx, sy, maxd)
            if v < STEP and joint:
                k = k_of(px + sx * STEP, py + sy * STEP)
                if k is not None and not self.wall[k] and self.owner[k] in joint:
                    continue
            out = min(out, v)
        return out


def distance(obst):
    """Расстояние до препятствия, фаска 2-3 (≈ евклидово), в см."""
    d = [0 if obst[k] else INF for k in range(NX * NY)]
    a, b = 2, 3  # ×STEP/2 → см
    for j in range(NY):
        for i in range(NX):
            k = j * NX + i
            if d[k] == 0:
                continue
            m = d[k]
            if i > 0:
                m = min(m, d[k - 1] + a)
            if j > 0:
                m = min(m, d[k - NX] + a)
                if i > 0:
                    m = min(m, d[k - NX - 1] + b)
                if i < NX - 1:
                    m = min(m, d[k - NX + 1] + b)
            d[k] = m
    for j in range(NY - 1, -1, -1):
        for i in range(NX - 1, -1, -1):
            k = j * NX + i
            m = d[k]
            if m == 0:
                continue
            if i < NX - 1:
                m = min(m, d[k + 1] + a)
            if j < NY - 1:
                m = min(m, d[k + NX] + a)
                if i < NX - 1:
                    m = min(m, d[k + NX + 1] + b)
                if i > 0:
                    m = min(m, d[k + NX - 1] + b)
            d[k] = m
    return [v * STEP / a if v < INF else INF for v in d]


NB = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))


def widest(d, s):
    """Для каждой клетки — максимальная по путям минимальная d (bottleneck) от клетки s."""
    best = [-1.0] * (NX * NY)
    best[s] = d[s]
    h = [(-d[s], s)]
    while h:
        nb, k = heapq.heappop(h)
        nb = -nb
        if nb < best[k]:
            continue
        i, j = k % NX, k // NX
        for di, dj in NB:
            ii, jj = i + di, j + dj
            if not (0 <= ii < NX and 0 <= jj < NY):
                continue
            kk = jj * NX + ii
            v = min(nb, d[kk])
            if v > best[kk]:
                best[kk] = v
                heapq.heappush(h, (-v, kk))
    return best


def shortest(d, s, r):
    """Кратчайшие пути от s по клеткам с d ≥ r (центр человека с плечами 2r): длины и родители."""
    dist = [math.inf] * (NX * NY)
    par = [-1] * (NX * NY)
    dist[s] = 0.0
    h = [(0.0, s)]
    while h:
        c, k = heapq.heappop(h)
        if c > dist[k]:
            continue
        i, j = k % NX, k // NX
        for di, dj in NB:
            ii, jj = i + di, j + dj
            if not (0 <= ii < NX and 0 <= jj < NY):
                continue
            kk = jj * NX + ii
            if d[kk] < r:
                continue
            cc = c + (1.414 if di and dj else 1)
            if cc < dist[kk]:
                dist[kk], par[kk] = cc, k
                heapq.heappush(h, (cc, kk))
    return dist, par


# ── Цели проходов ─────────────────────────────────────────────────────────────────────────────────────


def targets(p):
    """(имя, rect, правило): зоны, место перед предметом, обе стороны межкомнатных дверей."""
    out = [(f"зона {z['id']}", z["rect"], "pass_any") for z in p.get("zones", [])]
    for f in p["furniture"]:
        sp = specs(f)
        if not sp or no_target(sp[0]["name"]):
            continue
        sp = sp[0]
        x, y, w, h = f["rect"]
        fx, fy = FRONT[sp["back"]]
        if sp["name"] == "bed_double":  # обе длинные стороны
            sides = [(1, 0), (-1, 0)] if fx == 0 else [(0, 1), (0, -1)]
        else:
            sides = [(fx, fy)]
        for n, (sx, sy) in enumerate(sides):
            if sx:  # стоим справа/слева на 30 см от грани, по всей длине грани
                cx = x + w + 30 if sx > 0 else x - 30
                rect = [cx - 2, y + 10, 4, max(h - 20, 4)]
            else:
                cy = y + h + 30 if sy > 0 else y - 30
                rect = [x + 10, cy - 2, max(w - 20, 4), 4]
            out.append(
                (
                    f"{f['id']}" + (f" сторона {n + 1}" if len(sides) > 1 else ""),
                    rect,
                    "pass_any",
                )
            )
    for d in p["doors"]:
        if is_entry(d):
            continue
        cx, cy = door_center(d)
        nx, ny = (0, 1) if d["hinge"][1] == d["other"][1] else (1, 0)
        for sgn in (1, -1):
            px, py = cx + sgn * nx * 45, cy + sgn * ny * 45
            out.append((f"{d['id']} ({'+' if sgn > 0 else '−'})", [px - 2, py - 2, 4, 4], "pass_main"))
    return out


# ── Измерения ─────────────────────────────────────────────────────────────────────────────────────────


def m_passages(P, start):
    """Проходы и маршруты: (находки, маршруты [список клеток])."""
    s = k_of(*start)
    best = widest(P.dd, s)
    dist, par = shortest(P.dd, s, E.R["pass_any"].min / 2)
    out, routes, doors = [], [], {}
    for name, rect, rule in targets(P.p):
        free = [j * NX + i for i, j in cells(rect) if not P.path[j * NX + i]]
        v = max((best[k] for k in free), default=-1)
        w = round(2 * v) if v >= 0 else -1
        if w >= 400 or v >= INF:
            w = 400
        if rule == "pass_main":  # по двери одна строка — сторона, ближняя ко входу
            door = name.rsplit(" ", 1)[0]
            doors[door] = max(doors.get(door, -1), w)
        else:
            out.append((rule, name, w))
        reach = [k for k in free if dist[k] < math.inf]
        if reach:
            k = min(reach, key=lambda q: dist[q])
            r = []
            while k != -1:
                r.append(k)
                k = par[k]
            routes.append(r[::-1])
    # двери, в которые не попасть, ловит pass_any других целей
    out += [("pass_main", d, w) for d, w in doors.items() if w >= 0]
    return out, routes


def front_rule(nm):
    """Правило зоны перед предметом по имени каталога."""
    if not nm:
        return None
    if nm in HINGED:
        return "ward_hinged_front"
    if "ward" in nm:
        return "ward_front"
    if nm in ("commode", "shoes_closet", "low_cabinet_sideboard", "chest_for_sink"):
        return "drawer_front"
    if nm in ("bookshelf", "stillage_floor_book"):
        return "shelf_front"
    if nm == "kitchen_run" or nm in TALL_KITCHEN or nm == "stove":
        return "kitchen_front"
    if nm == "washing_machine":
        return "washer_front"
    if nm in ("toilet", "toilet_with_frame"):
        return "wc_front"
    if _cat(nm).get("custom_type") == "sink" or nm in ("sink_table_susp", "double_sink_box_floor"):
        return "sink_front"
    if nm in ("sofa_triple", "sofa_double"):
        return "sofa_front"
    if nm == "writingdesk_drawers":
        return "desk_back"
    return None


def m_fronts(P):
    """Зоны перед предметами."""
    out = []
    furn = P.p["furniture"]
    groups = {}
    for n, f in enumerate(furn):
        groups.setdefault(front_rule(kind(f)), set()).add(n)
    storage = set()
    for g in ("ward_front", "ward_hinged_front", "shelf_front"):
        storage |= groups.get(g, set())
    for g in ("ward_front", "ward_hinged_front", "shelf_front"):
        groups[g] = storage
    for f in furn:
        sp = specs(f)
        if not sp:
            continue
        nm, back = sp[0]["name"], sp[0]["back"]
        x, y, w, h = f["rect"]
        fr = FRONT[back]
        if nm == "bed_double":
            along_x = fr[0] != 0  # длина кровати вдоль x
            head_lo = back in ("left", "up")
            lo, hi = (55, 5) if head_lo else (5, 55)
            sides = [(0, 1), (0, -1)] if along_x else [(1, 0), (-1, 0)]
            for n, sd in enumerate(sides):
                out.append(("bed_side", f"{f['id']} бок {n + 1}", P.sweep(f["rect"], sd, lo, hi)))
            out.append(("bed_foot", f"{f['id']} изножье", P.sweep(f["rect"], fr, 20, 20)))
            continue
        rule = front_rule(nm)
        if rule:
            joint = groups.get(rule, ())  # стык углом с соседом той же группы — не помеха
            out.append((rule, f["id"], P.sweep(f["rect"], fr, 10, 10, joint)))
        if rule in ("wc_front", "sink_front") and nm != "double_sink_box_floor":
            # от оси до препятствия с каждой стороны; «слева/справа» — стоя лицом к прибору, как на снимке
            # RemPlanner (JSON отражён по вертикали — mirror_vertical — и стороны меняются местами)
            half = (w if fr[0] == 0 else h) / 2
            gx, gy = -fr[0], -fr[1]  # взгляд стоящего перед прибором
            right = (-gy, gx)  # в осях JSON (y вниз)
            if P.p.get("meta", {}).get("mirror_vertical"):
                right = (-right[0], -right[1])
            left = (-right[0], -right[1])
            for word, sd in (("слева", left), ("справа", right)):
                v = P.sweep(f["rect"], sd, 2, 2)
                out.append((rule.replace("front", "side"), f"{f['id']} {word}", round(half + v)))
        # обеденный стол: от кромки за стул до препятствия
        if nm in ("table", "table_round", "bar_table"):
            for c in furn:
                if kind(c) not in CHAIRS:
                    continue
                cx, cy, cw, ch = c["rect"]
                for sd in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    # стул примыкает к этой грани стола
                    if sd[0]:
                        edge = x + w if sd[0] > 0 else x
                        gap = (cx - edge) if sd[0] > 0 else (edge - (cx + cw))
                        overlap = min(y + h, cy + ch) - max(y, cy)
                        lo, hi = cy - y, (y + h) - (cy + ch)
                    else:
                        edge = y + h if sd[1] > 0 else y
                        gap = (cy - edge) if sd[1] > 0 else (edge - (cy + ch))
                        overlap = min(x + w, cx + cw) - max(x, cx)
                        lo, hi = cx - x, (x + w) - (cx + cw)
                    if -15 <= gap <= 15 and overlap > 20:
                        v = P.sweep(f["rect"], sd, max(lo, 0) + 5, max(hi, 0) + 5)
                        out.append(("dining_back", f"{f['id']}→{c['id']}", v))
    return out


def door_sector(d, theta):
    (hx, hy), (ox, oy) = d["hinge"], d["other"]
    w = math.hypot(ox - hx, oy - hy)
    ux, uy = (ox - hx) / w, (oy - hy) / w
    sx, sy = d["swing"]
    c, s = math.cos(math.radians(theta)), math.sin(math.radians(theta))
    return [
        (hx + r * (c * ux + s * sx) + sx, hy + r * (c * uy + s * sy) + sy)
        for r in range(3, int(w))
    ]


def m_doors(P):
    out = []
    # входная — как есть, в нише несущей стены; doorway — проём или раздвижные полотна, створки нет
    doors = [d for d in P.p["doors"] if not is_entry(d) and d.get("kind") != "doorway"]
    for d in doors:
        out.append(("door_width", d["id"], d["width"]))
        ang = 90
        hx, hy = d["hinge"]
        for t in range(5, 91):
            # у петли полотно уходит в откос — первые 15 см стены не считаются
            if any(
                P.blocked(P.front, x, y)
                and not (P.wall[k_of(x, y)] and math.hypot(x - hx, y - hy) < 15)
                for x, y in door_sector(d, t)
            ):
                ang = t - 1
                break
        out.append(("door_open", d["id"], ang))
    # створки двух дверей пересекаются
    swept = {}
    for d in [d for d in P.p["doors"] if d.get("kind") != "doorway"]:
        s = set()
        for t in range(0, 91, 3):
            for x, y in door_sector(d, t):
                k = k_of(x, y)
                if k is not None:
                    s.add(k)
        swept[d["id"]] = s
    ids = list(swept)
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            if swept[ids[a]] & swept[ids[b]]:
                out.append(("door_clash", f"{ids[a]} × {ids[b]}", 1))
    return out


def m_corners(P, routes):
    """Выступающие углы, у которых маршрут поворачивает: ширина прохода у угла."""
    r = E.R["pass_any"].min / 2
    jambs = [pt for d in P.p["doors"] for pt in (d["hinge"], d["other"])]
    corners = {}
    for j in range(NY - 1):
        for i in range(NX - 1):
            q = (j * NX + i, j * NX + i + 1, (j + 1) * NX + i, (j + 1) * NX + i + 1)
            m = [P.path[k] for k in q]
            if sum(m) != 1:
                continue
            n = m.index(1)  # клетка-препятствие: 0 ↖, 1 ↗, 2 ↙, 3 ↘
            vx, vy = X0 + (i + 1) * STEP, Y0 + (j + 1) * STEP
            if any(math.hypot(vx - a, vy - b) < 25 for a, b in jambs):
                continue
            ox, oy = (1 if n in (0, 2) else -1), (1 if n in (0, 1) else -1)  # наружу от угла
            corners[(vx, vy)] = (ox, oy, q[n])
    if not corners:
        return []
    grid = {}
    for (vx, vy) in corners:
        grid.setdefault((int(vx // 20), int(vy // 20)), []).append((vx, vy))
    hit = {}
    K = 12
    for rt in routes:
        pts = [xy_of(k) for k in rt]
        for t in range(K, len(pts) - K):
            x, y = pts[t]
            near = [
                c
                for gx in range(int(x // 20) - 2, int(x // 20) + 3)
                for gy in range(int(y // 20) - 2, int(y // 20) + 3)
                for c in grid.get((gx, gy), [])
                if math.hypot(c[0] - x, c[1] - y) <= r + 4
            ]
            if not near:
                continue
            ax, ay = x - pts[t - K][0], y - pts[t - K][1]
            bx, by = pts[t + K][0] - x, pts[t + K][1] - y
            na, nb = math.hypot(ax, ay), math.hypot(bx, by)
            if not na or not nb:
                continue
            turn = math.degrees(math.acos(max(-1, min(1, (ax * bx + ay * by) / na / nb))))
            if turn >= 30:
                for c in near:
                    hit[c] = True
    out = []
    for (vx, vy) in hit:
        ox, oy, k = corners[(vx, vy)]
        o = P.owner[k]
        name = P.p["furniture"][o]["id"] if o >= 0 and not P.wall[k] else "стена"
        e = 0.6
        w = min(
            P.ray(P.path, vx + ox * e, vy + oy * e, ox, 0),
            P.ray(P.path, vx + ox * e, vy + oy * e, 0, oy),
            P.ray(P.path, vx + ox * e, vy + oy * e, ox, oy) / math.sqrt(2),
        )
        out.append(("corner_turn", f"{name} ({vx:.0f}, {vy:.0f})", round(w)))
    # один угол предмета/стены — один отчёт: соседние вершины одной кромки сливаются
    out.sort(key=lambda t: t[2])
    seen, res = [], []
    for rule, name, w in out:
        xy = tuple(float(v) for v in name[name.rfind("(") + 1 : -1].split(","))
        if any(math.hypot(xy[0] - a, xy[1] - b) < 30 for a, b in seen):
            continue
        seen.append(xy)
        res.append((rule, name, w))
    return res


def kitchen_modules(f):
    """[(модуль, начало, конец)] вдоль линии kitchen_run от меньшей координаты."""
    sp = specs(f)[0]
    a, out = 0, []
    for m in sp["modules"]:
        n = 60 if m in KITCHEN else _cat(m)["width"]
        out.append((m, a, a + n))
        a += n
    return out


def m_kitchen(P):
    out = []
    furn = P.p["furniture"]
    fridges = [f for f in furn if kind(f) in FRIDGES]
    sinks, stoves = [], []
    for f in furn:
        if kind(f) != "kitchen_run":
            continue
        x, y, w, h = f["rect"]
        back = specs(f)[0]["back"]
        along_x = back in ("up", "down")
        length = w if along_x else h
        mods = kitchen_modules(f)
        fx, fy = FRONT[back]

        def at(a, _x=x, _y=y, _w=w, _h=h, _ax=along_x, _fx=fx, _fy=fy):
            # точка на лицевой кромке в позиции a вдоль линии
            if _ax:
                return _x + a, (_y if _fy < 0 else _y + _h)
            return (_x if _fx < 0 else _x + _w), _y + a

        for n, (m, a0, a1) in enumerate(mods):
            if m == "sink" or _cat(KITCHEN.get(m, m)).get("custom_type") == "sink":
                sinks.append((f, at((a0 + a1) / 2), a0, a1))
            if m == "stove" or KITCHEN.get(m, m) in ("stove", "hob"):
                stoves.append((f, at((a0 + a1) / 2), a0, a1))
        for _, (sx, sy), a0, a1 in [s for s in stoves if s[0] is f]:
            # столешница по бокам плиты: до мойки, высокого модуля или конца линии
            def counter(direction, a_start):
                a, L = a_start, 0
                seq = mods if direction > 0 else mods[::-1]
                for m, b0, b1 in seq:
                    if (direction > 0 and b0 < a_start) or (direction < 0 and b1 > a_start):
                        continue
                    if m in ("stove", "sink", "washer"):
                        return L
                    L += b1 - b0
                if direction > 0:
                    L += length - (mods[-1][2] if mods else 0)
                return L

            left, right = counter(-1, a0), counter(1, a1)
            # хвост столешницы до начала линии — 0 (модули с начала)
            out.append(("hob_side", f"{f['id']} плита: меньшая сторона", min(left, right)))
            out.append(("hob_side_big", f"{f['id']} плита: большая сторона", max(left, right)))
        for sf, _, s0, s1 in [s for s in sinks if s[0] is f]:
            for tf, _, t0, t1 in [s for s in stoves if s[0] is f]:
                gap = t0 - s1 if t0 >= s1 else s0 - t1
                out.append(("sink_hob", f"{f['id']} мойка–плита", gap))
    if sinks and stoves and fridges:
        fr = fridges[0]
        x, y, w, h = fr["rect"]
        fx, fy = FRONT[specs(fr)[0]["back"]]
        fpt = (x + w / 2 + fx * w / 2, y + h / 2 + fy * h / 2)
        s, t = sinks[0][1], stoves[0][1]
        legs = [math.dist(s, t), math.dist(t, fpt), math.dist(fpt, s)]
        out.append(("triangle_sum", "мойка–плита–холодильник", round(sum(legs))))
        out.append(("triangle_leg", "кратчайшая сторона треугольника", round(min(legs))))
        out.append(("triangle_leg_max", "длиннейшая сторона треугольника", round(max(legs))))
    # плита — окно (по плану, от края плиты до откоса)
    for f, (sx, sy), a0, a1 in stoves:
        x, y, w, h = f["rect"]
        along_x = specs(f)[0]["back"] in ("up", "down")
        r = [x + a0, y, a1 - a0, h] if along_x else [x, y + a0, w, a1 - a0]
        best = None
        for wn in P.p.get("windows", []):
            wx, wy, ww, wh = wn["rect"]
            dx = max(wx - (r[0] + r[2]), r[0] - (wx + ww), 0)
            dy = max(wy - (r[1] + r[3]), r[1] - (wy + wh), 0)
            dd = math.hypot(dx, dy)
            best = dd if best is None else min(best, dd)
        if best is not None and best < 150:
            out.append(("hob_window", f"{f['id']} плита — окно", round(best)))
    return out


def m_tv(P):
    """ТВ напротив дивана/кровати: дистанция в диагоналях и угол от оси."""
    out = []
    furn = P.p["furniture"]
    for tv in furn:
        if kind(tv) not in ("tv", "tele_on_mobile_stand"):
            continue
        tx, ty, tw, th = tv["rect"]
        width = max(tw, th)
        diag = width / 0.8716  # 16:9
        tc = (tx + tw / 2, ty + th / 2)
        best = None
        for s in furn:
            nm = kind(s)
            if nm not in SEATS:
                continue
            x, y, w, h = s["rect"]
            fx, fy = FRONT[specs(s)[0]["back"]]
            # глаза: в 40 см от спинки (диван) / 35 от изголовья (кровать)
            off = 35 if nm == "bed_double" else 40
            if fx:
                ex = (x + off) if fx > 0 else (x + w - off)
                ey = y + h / 2
            else:
                ey = (y + off) if fy > 0 else (y + h - off)
                ex = x + w / 2
            vx, vy = tc[0] - ex, tc[1] - ey
            dist = math.hypot(vx, vy)
            if not dist:
                continue
            # сквозь стену ТВ не смотрят: на луче глаза → экран (без 20 см у самого ТВ, он висит на стене) нет стен
            n = int(dist // STEP)
            if any(
                P.wall[k]
                for i in range(1, n)
                if dist - i * STEP > 20
                and (k := k_of(ex + vx * i / n, ey + vy * i / n)) is not None
            ):
                continue
            cosang = (vx * fx + vy * fy) / dist
            if cosang < math.cos(math.radians(50)):
                continue
            ang = math.degrees(math.acos(max(-1, min(1, cosang))))
            if best is None or dist < best[0]:
                best = (dist, ang, s["id"])
        if best:
            dist, ang, sid = best
            out.append(("tv_distance", f"{tv['id']} ← {sid}", round(dist / diag, 2)))
            out.append(("tv_angle", f"{tv['id']} ← {sid}", round(ang)))
    return out


def m_desk(P):
    """Окно относительно сидящего за столом: отклонение от «окно сбоку» (90°)."""
    out = []
    wins = P.p.get("windows", [])
    for f in P.p["furniture"]:
        if kind(f) != "writingdesk_drawers":
            continue
        x, y, w, h = f["rect"]
        fx, fy = FRONT[specs(f)[0]["back"]]
        face = (-fx, -fy)  # сидящий смотрит на стол
        c = (x + w / 2 + fx * (w / 2 + 30), y + h / 2 + fy * (h / 2 + 30))  # глаза сидящего
        best = None
        for wn in wins:
            wx, wy, ww, wh = wn["rect"]
            q = (min(max(c[0], wx), wx + ww), min(max(c[1], wy), wy + wh))  # ближайшая точка окна
            dd = math.dist(c, q)
            if dd < 450 and (best is None or dd < best[0]):
                best = (dd, q)
        if not best:
            continue
        vx, vy = best[1][0] - c[0], best[1][1] - c[1]
        ang = math.degrees(math.acos(max(-1, min(1, (vx * face[0] + vy * face[1]) / math.hypot(vx, vy)))))
        out.append(("desk_window", f["id"], round(abs(ang - 90))))
    return out


def measure(p, start=None):
    P = Plan(p)
    start = start or entry_start(p)
    passes, routes = m_passages(P, start)
    return (
        passes
        + m_fronts(P)
        + m_doors(P)
        + m_corners(P, routes)
        + m_kitchen(P)
        + m_tv(P)
        + m_desk(P)
    )


def check(path):
    p = json.load(open(path, encoding="utf-8"))
    return E.judge(measure(p), p.get("ergo_waivers", {}))


if __name__ == "__main__":
    args = sys.argv[1:]
    verbose, waivers = "-v" in args, "-w" in args
    rc = 0
    for f in [a for a in args if a not in ("-v", "-w")]:
        v = check(f)
        print(E.report(f, v, verbose, waivers))
        rc |= not v["ok"]
    sys.exit(rc)
