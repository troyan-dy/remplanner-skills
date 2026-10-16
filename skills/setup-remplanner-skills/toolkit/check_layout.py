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
  человека в 30 см перед лицевой стороной предмета (перед фасадом уже SMALL_FACE — со сдвигом вдоль фасада, как
  перед фасадом SMALL_FACE: к миске в углу подходят чуть сбоку), обеим сторонам каждой межкомнатной двери (в 45 см
  от полотна). В круге радиуса w/2 + 10 у каждого проёма сужение не считается: ширину двери проверяет своё правило.
  Горлышко пути между двумя несущими стенами (bearing_gap) — уступка «из-за несущего», без баллов;
- зоны перед предметами: свободная глубина от лицевой грани (кровать — бока и изножье, без 55 см у изголовья,
  где тумбы; у односпальной — один, более свободный бок) до первого препятствия; для унитаза и раковины — ещё
  от оси до боковых препятствий;
- двери: ширина (кроме входной и двери балконного блока — проёмы в несущих стенах); угол, на который полотно
  открывается до мебели/стены; пересечение створок двух дверей и створки с соседним проёмом без полотна;
  полотно, открытое на 90°: остаток прохода за его краем, если мимо идёт маршрут, и расстояние до фасада шкафа,
  ящиков, кухни, стиральной машины перед ним;
- выступающие углы на маршрутах: кратчайший путь от входа к каждой цели (плечи 55) поворачивает у угла стены
  или мебели — меряется ширина прохода у этого угла (свободное место по обеим граням и по биссектрисе);
- кухня (`kitchen_run`): столешница по бокам плиты, между мойкой и плитой, рабочий треугольник
  мойка–плита–холодильник, плита — окно;
- ТВ: расстояние от глаз (диван, кровать напротив) в диагоналях и угол в сторону от оси;
- рабочий стол: окно сбоку, а не перед лицом или за спиной.
Препятствия для проходов — без навесного с низом ≥ 100 см (rp.over_floor, иначе каталог) и переставляемого (SKIP,
стулья); для зон перед предметами столы считаются, стулья — нет.
Роли предметов (диван, кровать, стул, рабочий и обеденный стол, ТВ, холодильник, пенал, плита, раковина, шкаф…) —
по разделу меню каталога и шаблонам имён (M_*, is_*), так что проверяются любые предметы каталога, а не только
перечисленные; для имён rp_lib.CATALOG разделы есть и без полного каталога (tools/reference/catalog_core.json).
Не проверяет: высоты, навесные шкафы, свет и розетки (их нет в плане) — это ручные правила из
tools/reference/ERGONOMICS.md."""

import heapq
import json
import math
import re
import sys

import ergonomics as E
import rp_lib
from rp_lib import KITCHEN

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
    "towel_dryer",
    "bar_chair_backrest",
    "folding_wall_table",
    "tetra_stillage",
}  # навесное, переставляемое (dryer — напольная сушильная машина 60×60×85, она препятствие)
NO_TARGET = {
    "tv",
    "bathroom_mirror",
    "chair",
    "office_chair",
    "table",
    "worktop",
    "kitchen_sink",
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
DRAWERS = {"commode", "shoes_closet", "low_cabinet_sideboard", "chest_for_sink"}
SHELVES = {"bookshelf", "stillage_floor_book"}
TOILETS = r"^toilet(_with_frame|_embedded|_impulse)?$|^corner_toilet$"  # как check_rules.TOILETS
WASHERS = r"^(washing_machine(_top|_mini)?|dryer|dryer_over_washing)$"
SMALL_FACE = 50  # предмет с фасадом уже — встать перед ним можно и со сдвигом вдоль фасада (миски, лоток, унитаз)

# Роли предметов — по разделу меню каталога (поле menu: «раздел», «группа») и шаблонам имён, чтобы любые диваны,
# кровати, столы каталога проверялись, а не только перечисленные. Для имён rp_lib.CATALOG раздел известен и без
# полного каталога (tools/reference/catalog_core.json). Группа None — весь раздел.
M_SOFA = {("Гостиная и спальня", "Диваны"), ("Гостиная и спальня", "Модульные диваны")}
M_BED = {("Гостиная и спальня", "Кровати"), ("Мебель для детской", "Кровати и диваны")}
M_CHAIR = {("Гостиная и спальня", "Стулья"), ("Кухня и столовая", "Стулья"), ("Кабинет и офис", "Кресла и стулья")}
M_DESK = {("Кабинет и офис", "Столы и стойки")}
M_DINING = {("Кухня и столовая", "Обеденные столы")}
M_TALL = {("Кухня и столовая", "Шкафы-пеналы")}
M_FRIDGE = {("Бытовая техника", "Холодильники")}
M_STOVE = {("Бытовая техника", "Кухонные плиты")}
M_SINK = {("Раковины и мойки", None)}
M_HINGED = {("Гардероб и прихожая", "Гардеробные шкафы"), ("Гардероб и прихожая", "Угловые шкафы"),
            ("Гостиная и спальня", "Шкафы"), ("Мебель для ванной", "")}
M_OPEN_WARD = {("Гардероб и прихожая", "Шкафы-купе"), ("Гардероб и прихожая", "Открытые гардеробные")}
M_DRAWER = {("Гостиная и спальня", "Комоды и тумбы"), ("Гардероб и прихожая", "Обувницы и тумбы")}
M_SHELF = {("Гостиная и спальня", "Стеллажи и полки"), ("Гостиная и спальня", "Крупногабаритные стеллажи")}


def _cat(name):
    """Запись каталога (без полного каталога — для имён CATALOG и confirmed.json; неизвестное имя — {})."""
    return rp_lib.info(name)


def in_menu(name, sections):
    """Предмет в одной из групп меню каталога (группа None — весь раздел)."""
    return any((m[0], m[1]) in sections or (m[0], None) in sections for m in _cat(name).get("menu", []))


def is_chair(name):
    """Стул, кресло к столу, барный стул или табурет — переставляемое: не мешает проходам и зонам."""
    return bool(name) and (
        _cat(name).get("custom_type") == "chair"
        or in_menu(name, M_CHAIR)
        or (in_menu(name, {("Кухня и столовая", "Барная мебель")}) and re.search(r"chair|tabouret", name) is not None)
        or (in_menu(name, {("Мебель для детской", "Столы и стулья")}) and "chair" in name)
    )


def is_sofa(name):
    """Диван (с него смотрят ТВ, перед ним sofa_front); кухонный диван-скамья — место за столом, не диван."""
    if not name or re.search(r"kitchen|armrest|pouf", name):
        return False
    return in_menu(name, M_SOFA) or (in_menu(name, M_BED) and "sofa" in name and "bed" not in name)


def is_bed(name):
    """Кровать любого размера (с неё смотрят ТВ)."""
    return bool(name) and in_menu(name, M_BED) and not is_sofa(name)


def bed_fronts(name):
    """Кровать, у которой проверяются бока и изножье: без трансформеров (откидные, в шкафу) и люлек."""
    return is_bed(name) and not re.search(r"transformer|cradle|chaiselongue", name)


def is_tv(name):
    return _cat(name).get("title", "").startswith("Телевизор")


def is_desk(name):
    """Рабочий стол: «Кабинет и офис / Столы и стойки» без стоек ресепшн и переговорных; школьная парта."""
    return bool(name) and (
        (in_menu(name, M_DESK) and not re.search(r"reception|meeting|briefing", name)) or name == "kid_desk"
    )


def is_dining(name):
    return name in ("table", "table_round", "bar_table") or in_menu(name, M_DINING)


def is_fridge(name):
    return bool(name) and "fridge" in name and name != "mini_fridge"


def is_tall_kitchen(name):
    """Высокий кухонный модуль: пенал, холодильник в рост."""
    return bool(name) and (
        in_menu(name, M_TALL)
        or is_fridge(name)
        or (in_menu(name, M_FRIDGE) and _cat(name).get("self_height", 0) >= 120)
    )


def is_toilet(name):
    return bool(name) and re.search(TOILETS, name) is not None


def is_sink(name):
    return bool(name) and (
        _cat(name).get("custom_type") == "sink"
        or name in ("sink_table_susp", "double_sink_box_floor")
        or in_menu(name, M_SINK)
    )


def over_floor(s):
    """Низ предмета над полом, см: число rp.over_floor или over_floor каталога."""
    v = s.get("over_floor")
    if isinstance(v, (int, float)):
        return v
    return (_cat(s["name"]).get("over_floor") or {}).get("value", 0) or 0


def skip(s):
    """Не препятствие для проходов: навесное (низ ≥ 100 см), переставляемое (SKIP, стулья). s — объект rp."""
    return s["name"] in SKIP or over_floor(s) >= 100 or is_chair(s["name"])


def no_target(s):
    """Не цель прохода: NO_TARGET, навесное и переставляемое, мойка в столешнице, настенная инженерия
    (anchor wall: бризер, щиток, кондиционер — перед ней не стоят)."""
    e = _cat(s["name"])
    return s["name"] in NO_TARGET or skip(s) or e.get("custom_type") == "sink" or e.get("anchor") == "wall"


def light(s):
    """Не мешает стоять перед другим предметом."""
    return s["name"] in LIGHT or is_chair(s["name"]) or over_floor(s) >= 100


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
            sps = specs(f)
            on_path = not (sps and all(skip(s) for s in sps))
            on_front = not (sps and all(light(s) for s in sps))
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
        self.dd = self.near_doors(self.d, self.path)
        self.bearing = bytearray(n)  # клетки несущих стен: сужение между двумя несущими — m_passages
        for r in p["walls_bearing"]:
            for i, j in cells(r["rect"]):
                self.bearing[j * NX + i] = 1

    def near_doors(self, d, mask):
        """Копия поля расстояний d, где у проёмов сужение не считается (ширину двери проверяет door_width)."""
        dd = list(d)
        for dr in self.p["doors"]:
            cx, cy = door_center(dr)
            rr = dr["width"] / 2 + 10
            for i, j in cells([cx - rr, cy - rr, 2 * rr, 2 * rr]):
                x, y = xy_of(j * NX + i)
                k = j * NX + i
                if (x - cx) ** 2 + (y - cy) ** 2 <= rr * rr and not mask[k]:
                    dd[k] = INF
        return dd

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
    """Для каждой клетки — максимальная по путям минимальная d (bottleneck) от клетки s и родитель на таком пути."""
    best = [-1.0] * (NX * NY)
    par = [-1] * (NX * NY)
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
                best[kk], par[kk] = v, k
                heapq.heappush(h, (-v, kk))
    return best, par


def bearing_gap(P, best, par, k):
    """Сужение на самом широком пути к клетке k — между двумя несущими стенами? Идём по родителям до клетки
    с наименьшей d (горлышко); ближайшее к ней препятствие и препятствие с противоположной стороны — оба
    клетки walls_bearing. Тогда шире горлышко не сделать никакой перестановкой."""
    q, b = k, None
    while q != -1:
        if P.dd[q] < INF and (b is None or P.dd[q] < P.dd[b]):
            b = q
        q = par[q]
    if b is None or P.dd[b] > best[k] + STEP:
        return False
    x, y = xy_of(b)
    r = P.d[b] * 1.1 + 2 * STEP
    near = []
    for i, j in cells([x - r, y - r, 2 * r, 2 * r]):
        c = j * NX + i
        if P.path[c]:
            cx, cy = xy_of(c)
            near.append((math.hypot(cx - x, cy - y), c))
    if not near:
        return False
    dist, c1 = min(near)
    nx, ny = (xy_of(c1)[0] - x) / (dist or 1), (xy_of(c1)[1] - y) / (dist or 1)
    back = P.ray(P.path, x, y, -nx, -ny, 2 * r + 20)
    c2 = k_of(x - nx * (back + STEP), y - ny * (back + STEP))
    return bool(P.bearing[c1]) and c2 is not None and bool(P.bearing[c2])


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


def bed_sides(P, f):
    """Бока кровати [(сторона, lo, hi)] для зон и целей: двуспальная (изголовье ≥ 140) — оба длинных бока,
    односпальная — один, более свободный (второй обычно у стены). lo, hi — отступы sweep по краям бока."""
    sp = specs(f)[0]
    x, y, w, h = f["rect"]
    fr = FRONT[sp["back"]]
    along_x = fr[0] != 0  # длина кровати вдоль x
    head_lo = sp["back"] in ("left", "up")
    lo, hi = (55, 5) if head_lo else (5, 55)
    sides = [(0, 1), (0, -1)] if along_x else [(1, 0), (-1, 0)]
    if (h if along_x else w) < 140:
        sides = [max(sides, key=lambda sd: P.sweep(f["rect"], sd, lo, hi))]
    return [(sd, lo, hi) for sd in sides]


def targets(P):
    """(имя, rect, правило): зоны, место перед предметом, обе стороны межкомнатных дверей."""
    p = P.p
    out = [(f"зона {z['id']}", z["rect"], "pass_any") for z in p.get("zones", [])]
    for f in p["furniture"]:
        sp = specs(f)
        if not sp or no_target(sp[0]):
            continue
        sp = sp[0]
        x, y, w, h = f["rect"]
        fx, fy = FRONT[sp["back"]]
        if bed_fronts(sp["name"]):  # длинные стороны: у двуспальной обе
            sides = [sd for sd, _, _ in bed_sides(P, f)]
        else:
            sides = [(fx, fy)]
        for n, (sx, sy) in enumerate(sides):
            # стоим на 30 см от грани, по всей длине грани; перед узким (< SMALL_FACE) предметом — и со сдвигом
            # вдоль фасада, как перед фасадом SMALL_FACE: в углу к миске или лотку подходят чуть сбоку
            if sx:
                cx = x + w + 30 if sx > 0 else x - 30
                a0, n0 = (y, h) if h >= SMALL_FACE else (y + h / 2 - SMALL_FACE / 2, SMALL_FACE)
                rect = [cx - 2, a0 + 10, 4, max(n0 - 20, 4)]
            else:
                cy = y + h + 30 if sy > 0 else y - 30
                a0, n0 = (x, w) if w >= SMALL_FACE else (x + w / 2 - SMALL_FACE / 2, SMALL_FACE)
                rect = [a0 + 10, cy - 2, max(n0 - 20, 4), 4]
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
    """Проходы и маршруты: (находки, маршруты [список клеток]). Находка прохода — (правило, объект, ширина, cap):
    cap = ширина, если горлышко самого широкого пути — между двумя несущими стенами (bearing_gap), иначе None.
    Такую уступку judge считает «из-за несущего» и баллы за неё не берёт."""
    s = k_of(*start)
    best, wpar = widest(P.dd, s)
    dist, par = shortest(P.dd, s, E.R["pass_any"].min / 2)
    out, routes, doors = [], [], {}

    def width(v):
        w = round(2 * v) if v >= 0 else -1
        return 400 if w >= 400 or v >= INF else w

    for name, rect, rule in targets(P):
        free = [j * NX + i for i, j in cells(rect) if not P.path[j * NX + i]]
        kb = max(free, key=lambda q: best[q], default=None)
        w = width(best[kb] if kb is not None else -1)
        cap = w if kb is not None and best[kb] > 0 and bearing_gap(P, best, wpar, kb) else None
        if rule == "pass_main":  # по двери одна строка — сторона, ближняя ко входу
            door = name.rsplit(" ", 1)[0]
            if w > doors.get(door, (-1, None))[0]:
                doors[door] = (w, cap)
        else:
            out.append((rule, name, w, cap))
        reach = [k for k in free if dist[k] < math.inf]
        if reach:
            k = min(reach, key=lambda q: dist[q])
            r = []
            while k != -1:
                r.append(k)
                k = par[k]
            routes.append(r[::-1])
    # двери, в которые не попасть, ловит pass_any других целей
    out += [("pass_main", d, w, cap) for d, (w, cap) in doors.items() if w >= 0]
    return out, routes


def front_rule(nm, s=None):
    """Правило зоны перед предметом: по имени каталога (явные наборы), затем по роли и разделу меню.
    s — объект rp: навесное (низ ≥ 100 см) зоны перед собой не требует."""
    if not nm:
        return None
    if nm in HINGED:
        return "ward_hinged_front"
    if "ward" in nm:
        return "ward_front"
    if nm in DRAWERS:
        return "drawer_front"
    if nm in SHELVES:
        return "shelf_front"
    if nm == "kitchen_run" or is_tall_kitchen(nm) or nm == "stove" or in_menu(nm, M_STOVE):
        return "kitchen_front"
    if re.search(WASHERS, nm):
        return "washer_front"
    if is_toilet(nm):
        return "wc_front"
    if is_sink(nm):
        return "sink_front"
    if is_sofa(nm):
        return "sofa_front"
    if is_desk(nm):
        return "desk_back"
    if over_floor(s or {"name": nm}) >= 100:
        return None
    if in_menu(nm, M_HINGED) and "open" not in nm:
        return "ward_hinged_front"
    if in_menu(nm, M_OPEN_WARD) or in_menu(nm, M_HINGED):
        return "ward_front"
    if in_menu(nm, M_DRAWER) and not re.search(r"bedside|tele_stand|tv_table", nm):
        return "drawer_front"  # прикроватные тумбы — у бока кровати, его проверяет bed_side
    if in_menu(nm, M_SHELF):
        return "shelf_front"
    return None


def m_fronts(P):
    """Зоны перед предметами."""
    out = []
    furn = P.p["furniture"]
    groups = {}
    for n, f in enumerate(furn):
        sp = specs(f)
        groups.setdefault(front_rule(kind(f), sp[0] if sp else None), set()).add(n)
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
        if bed_fronts(nm):
            sides = bed_sides(P, f)
            for n, (sd, lo, hi) in enumerate(sides):
                label = f"бок {n + 1}" if len(sides) > 1 else "бок"
                out.append(("bed_side", f"{f['id']} {label}", P.sweep(f["rect"], sd, lo, hi)))
            out.append(("bed_foot", f"{f['id']} изножье", P.sweep(f["rect"], fr, 20, 20)))
            continue
        rule = front_rule(nm, sp[0])
        if rule:
            joint = groups.get(rule, ())  # стык углом с соседом той же группы — не помеха
            out.append((rule, f["id"], P.sweep(f["rect"], fr, 10, 10, joint)))
        if rule in ("wc_front", "sink_front") and "double" not in nm:  # у двойной раковины оси две
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
        if is_dining(nm):
            for c in furn:
                if not is_chair(kind(c)):
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


def windoor_doors(p):
    """id дверей балконных блоков (windows[].windoor_door) — проём в несущей стене, как у входной."""
    return {w["windoor_door"] for w in p.get("windows", []) if w.get("windoor_door")}


def leaf_doors(p):
    """Двери со створкой, которую проверяют door_open и правила открытого полотна: без входной (как есть, в нише
    несущей стены; её swing — «внутрь», а не сторона открывания) и без doorway (проём или купе, створки нет)."""
    return [d for d in p["doors"] if not is_entry(d) and d.get("kind") != "doorway"]


def m_doors(P):
    out = []
    balcony = windoor_doors(P.p)
    for d in leaf_doors(P.p):
        if d["id"] not in balcony:  # ширину проёма в несущей стене не выбирают
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
    # створки двух дверей пересекаются; створка заходит в соседний проём без полотна (doorway)
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
    for o in [d for d in P.p["doors"] if d.get("kind") == "doorway"]:
        (hx, hy), (ox, oy) = o["hinge"], o["other"]
        hole = [min(hx, ox), hy - 5, abs(ox - hx), 10] if hy == oy else [hx - 5, min(hy, oy), 10, abs(oy - hy)]
        cs = {j * NX + i for i, j in cells(hole)}
        for i in ids:
            if swept[i] & cs:
                out.append(("door_clash", f"{i} × {o['id']} (проём)", 1))
    return out


LEAF_FRONT = ("ward_hinged_front", "drawer_front", "kitchen_front", "washer_front")  # фасад открывается вперёд


def m_leaves(P, routes):
    """Открытое на 90° полотно (от петли по swing, длина — ширина двери):
    - door_leaf_pass — маршрут от входа пересекает полотно или промежуток за его краем: сколько остаётся прохода
      от края полотна до препятствия (полотно поперёк коридора);
    - door_leaf_front — полотно перед фасадом, который открывается вперёд (LEAF_FRONT: распашной шкаф, ящики,
      кухня и пеналы, стиральная машина): от фасада до полотна, если между ними нет стены."""
    out = []
    furn = P.p["furniture"]
    fronts = []
    for f in furn:
        sp = specs(f)
        if sp and front_rule(sp[0]["name"], sp[0]) in LEAF_FRONT:
            fronts.append((f, FRONT[sp[0]["back"]]))
    for d in leaf_doors(P.p):
        (hx, hy), (ox, oy) = d["hinge"], d["other"]
        w = math.hypot(ox - hx, oy - hy)
        sx, sy = d["swing"]
        tx, ty = hx + sx * (w + 1), hy + sy * (w + 1)  # край открытого полотна
        gap = P.ray(P.path, tx, ty, sx, sy)
        # маршрут пересекает линию полотна (ось петли поперёк стены) на участке от петли до препятствия
        ux, uy = (ox - hx) / w, (oy - hy) / w
        reach = w + 1 + gap
        crossed = False
        for rt in routes:
            prev = None
            for k in rt:
                x, y = xy_of(k)
                a = (x - hx) * ux + (y - hy) * uy  # вдоль стены от петли (> 0 — в сторону проёма)
                t = (x - hx) * sx + (y - hy) * sy  # от стены по swing
                if prev is not None and (prev[0] < 0) != (a < 0) and 3 <= min(t, prev[1]) and max(t, prev[1]) <= reach:
                    crossed = True
                    break
                prev = (a, t)
            if crossed:
                break
        if crossed:
            out.append(("door_leaf_pass", f"{d['id']} открыта", round(min(gap, 400))))
        for f, (fx, fy) in fronts:
            x, y, fw, fh = f["rect"]
            best = None
            for r in range(3, int(w) + 1, STEP):
                px, py = hx + sx * (r + 1), hy + sy * (r + 1)
                if fx:  # фасад смотрит по x
                    face = x + fw if fx > 0 else x
                    dist, along, lo, hi = (px - face) * fx, py, y, y + fh
                    fp = (face + fx * 0.5, py)
                else:
                    face = y + fh if fy > 0 else y
                    dist, along, lo, hi = (py - face) * fy, px, x, x + fw
                    fp = (px, face + fy * 0.5)
                if not (0 <= dist < 150 and lo + 5 < along < hi - 5):
                    continue  # полотно вдоль боковой грани — не перед фасадом
                if P.ray(P.wall, fp[0], fp[1], fx, fy, 150) < dist - STEP:
                    continue  # между фасадом и полотном стена
                best = dist if best is None else min(best, dist)
            if best is not None:
                out.append(("door_leaf_front", f"{d['id']} открыта → {f['id']}", round(best)))
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
        n = 60 if m in KITCHEN else _cat(m).get("width", 60)
        out.append((m, a, a + n))
        a += n
    return out


def has_top(m):
    """Над модулем линии кухни лежит столешница — как в remplanner_export.kitchen_run."""
    return (m in KITCHEN and m != "stove") or _cat(m).get("custom_type") == "table_top"


def m_kitchen(P):
    out = []
    furn = P.p["furniture"]
    fridges = [f for f in furn if is_fridge(kind(f))]
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
            if m == "stove" or KITCHEN.get(m, m) == "hob" or in_menu(KITCHEN.get(m, m), M_STOVE):
                stoves.append((f, at((a0 + a1) / 2), a0, a1))
        for _, (sx, sy), a0, a1 in [s for s in stoves if s[0] is f]:
            # столешница по бокам плиты — до препятствия: мойки, другой плиты, модуля без столешницы (высокий пенал,
            # отдельностоящая техника) или конца линии; над модулем со столешницей (шкаф, посудомойка,
            # стиральная машина) рабочее место продолжается
            def counter(direction, a_start):
                L = 0
                seq = mods if direction > 0 else mods[::-1]
                for m, b0, b1 in seq:
                    if (direction > 0 and b0 < a_start) or (direction < 0 and b1 > a_start):
                        continue
                    if m in ("stove", "sink") or not has_top(m) or _cat(KITCHEN.get(m, m)).get("custom_type") == "sink":
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
        if not is_tv(kind(tv)):
            continue
        tx, ty, tw, th = tv["rect"]
        width = max(tw, th)
        diag = width / 0.8716  # 16:9
        tc = (tx + tw / 2, ty + th / 2)
        best = None
        for s in furn:
            nm = kind(s)
            if not (is_sofa(nm) or is_bed(nm)):
                continue
            x, y, w, h = s["rect"]
            fx, fy = FRONT[specs(s)[0]["back"]]
            # глаза: в 40 см от спинки (диван) / 35 от изголовья (кровать)
            off = 35 if is_bed(nm) else 40
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
        if not is_desk(kind(f)):
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
        + m_leaves(P, routes)
        + m_corners(P, routes)
        + m_kitchen(P)
        + m_tv(P)
        + m_desk(P)
    )


def check(path):
    p = json.load(open(path, encoding="utf-8"))
    rp_lib.check_names(p, path)
    return E.judge(measure(p), p.get("ergo_waivers", {}), p.get("structural_waivers", {}))


if __name__ == "__main__":
    args = sys.argv[1:]
    verbose, waivers = "-v" in args, "-w" in args
    rc = 0
    for f in [a for a in args if a not in ("-v", "-w")]:
        v = check(f)
        print(E.report(f, v, verbose, waivers))
        rc |= not v["ok"]
    sys.exit(rc)
