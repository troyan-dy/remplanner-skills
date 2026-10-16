#!/usr/bin/env python3
"""remplanner_export.py [<name>.json ...] — планировка → RemPlanner .plan (v3): стены, двери, окна, мебель.

Без аргументов экспортирует plan/*.json и все серии концепций concepts/<серия>/*.json (пути от корня
проекта — родителя папки tools/). Результат — <name>.plan рядом с JSON. Формат JSON —
tools/reference/PLAN_FORMAT.md.
Координаты RemPlanner: см, отображаемая ориентация, y вниз, центр плана в (0,0); JSON с meta.mirror_vertical
отражается по вертикали.
Несущие стены строятся из walls_bearing: прямоугольник → осевая линия вдоль длинной стороны, толщина —
короткая сторона; куски одной стены, разделённые проёмом, сливаются; концы стыкуются вместе с перегородками
(угол — узел на пересечении осей, Т-примыкание — конец на грани проходящей стены).
Перегородки строятся из partitions: куски одной линии, разделённые дверными проёмами, сливаются.
Мебель экспортируется только с полем "rp" (см. planlib.rp и rp_lib.CATALOG).
Семантика полей проверена импортом тестовых планов (см. tools/reference/REMPLANNER_V3_SCHEMA.md).
"""

import glob
import json
import math
import os
import sys

import rp_lib as R

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # корень проекта — родитель tools/

# Ориентация и центр — свои у каждого плана (set_frame). meta.mirror_vertical: true — план в JSON отражён
# относительно того, что показывает RemPlanner (y_m = H - y); иначе y как есть. Центр плана RemPlanner (0,0) —
# середина габарита несущих стен.
MIRROR = False
H = 0
CX, CY = 0.0, 0.0

# В RemPlanner нет признака «несущая» — тип стены передаётся материалом (своя штриховка на плане).
# Ключи материалов — tools/reference/remplanner_example_v3_wall_materials.plan.
MATERIAL = {
    "facade": "a_brick",
    "interapartment": "a_concrete",
    "column": "a_concrete",
    "bearing": "a_concrete",  # внутренняя несущая — как межквартирная (предположение: отдельного образца нет)
    "partition": "a_block",
    "glass": "a_glass",  # partitions[].kind = "glass" — стеклянная перегородка (образец ..._wall_materials.plan)
    "insulation": "a_block",  # insulation[] — утепление лоджии: без него RemPlanner считал лоджию шире
    # на толщину утепления
}
BEARING_KINDS = ("facade", "interapartment", "column", "bearing")
ANGLE = {
    "down": 180,
    "up": 0,
    "left": 90,
    "right": 270,
}  # спинка в координатах JSON при mirror_vertical → angle RemPlanner (без отражения — angle_of)
MERGE_GAP = 130  # максимальный разрыв между кусками одной стены, который считается дверным проёмом
THIN = 10  # несущий кусок тоньше этого вплотную к грани параллельной несущей стены — накладка, не стена
# doors[].kind → тип проёма RemPlanner. Входная дверь помечается полем "entry": true, экспортёр его не читает;
# kind "entry" по ошибке всё равно выгружается обычной дверью, а не несуществующим типом.
DOOR_TYPE = {"entry": "single"}


def set_frame(plan):
    """MIRROR — meta.mirror_vertical; высота зеркалирования H — meta.outer_height (без неё — y_min + y_max
    габарита несущих стен; на результат H не влияет — центр вычитается); центр — середина габарита несущих стен
    (без несущих — перегородок)."""
    global MIRROR, H, CX, CY
    rects = [w["rect"] for w in plan.get("walls_bearing", [])] or [
        w["rect"] for w in plan.get("partitions", [])
    ]
    if not rects:
        raise SystemExit("в плане нет стен: walls_bearing и partitions пусты")
    x0 = min(r[0] for r in rects)
    x1 = max(r[0] + r[2] for r in rects)
    y0 = min(r[1] for r in rects)
    y1 = max(r[1] + r[3] for r in rects)
    meta = plan.get("meta", {})
    MIRROR = bool(meta.get("mirror_vertical"))
    H = meta.get("outer_height", y0 + y1) if MIRROR else 0
    CX, CY = (x0 + x1) / 2, (H - (y0 + y1) / 2 if MIRROR else (y0 + y1) / 2)


def to_rp(x, y):
    return x - CX, ((H - y) - CY if MIRROR else y - CY)


def rect_rp(r):
    x, y, w, h = r
    return x - CX, ((H - y - h) - CY if MIRROR else y - CY), w, h


def angle_of(back):
    """Сторона спинки в координатах JSON → angle RemPlanner (при отражении верх и низ меняются местами)."""
    if not MIRROR:
        back = {"up": "down", "down": "up"}.get(back, back)
    return ANGLE[back]


class Seg:
    def __init__(self, x1, y1, x2, y2, d, kind="partition"):
        self.d, self.kind = d, kind
        if abs(y1 - y2) < 1e-6:
            self.axis, self.c, self.a0, self.a1 = "h", y1, x1, x2
        else:
            self.axis, self.c, self.a0, self.a1 = "v", x1, y1, y2
        self.rev = (
            self.a0 > self.a1
        )  # направление сохраняем как задано (важно для несущих)

    @property
    def lo(self):
        return min(self.a0, self.a1)

    @property
    def hi(self):
        return max(self.a0, self.a1)

    def ends(self):
        if self.axis == "h":
            return (self.a0, self.c, self.a1, self.c)
        return (self.c, self.a0, self.c, self.a1)

    def contains(self, x, y, tol=1.0):
        along, perp = (x, y) if self.axis == "h" else (y, x)
        return (
            abs(perp - self.c) <= self.d / 2 + tol
            and self.lo - tol <= along <= self.hi + tol
        )


def seg_of_rect(r, kind):
    """Прямоугольник в исходных координатах → осевая линия в координатах RemPlanner вдоль длинной стороны,
    p1 — у меньшей координаты; толщина — короткая сторона."""
    x, y, w, h = rect_rp(r)
    # короткие доборы 9×10 у дверей — тоже горизонтальные куски перегородки толщиной 10
    if w >= h or (h == 10 and w < 10):
        return Seg(x, y + h / 2, x + w, y + h / 2, h, kind)
    return Seg(x + w / 2, y, x + w / 2, y + h, w, kind)


def _merge_pieces(a, b, openings, eps=1e-6):
    """Два куска одной стены → общий прямоугольник или None. Куски — на одной линии с одинаковым
    поперечным сечением; соприкасаются или разделены разрывом ≤ MERGE_GAP, в котором стоит дверь или окно."""
    for cross in (0, 1):  # 0 — общий диапазон x (куски друг над другом), 1 — общий диапазон y
        along = 1 - cross
        c0, c1 = a[cross], a[cross] + a[cross + 2]
        if abs(c0 - b[cross]) > eps or abs(c1 - (b[cross] + b[cross + 2])) > eps:
            continue
        a0, a1 = a[along], a[along] + a[along + 2]
        b0, b1 = b[along], b[along] + b[along + 2]
        g0, g1 = min(a1, b1), max(a0, b0)  # разрыв между кусками (g1 ≤ g0 — соприкасаются/перекрываются)
        if g1 - g0 > eps and not (
            g1 - g0 <= MERGE_GAP
            and any(
                c0 - 1 <= o[cross] <= c1 + 1 and g0 - 1 <= o[along] <= g1 + 1
                for o in openings
            )
        ):
            continue
        lo, hi = min(a0, b0), max(a1, b1)
        return [c0, lo, c1 - c0, hi - lo] if cross == 0 else [lo, c0, hi - lo, c1 - c0]
    return None


def _is_overlay(r, others, eps=1e-6):
    """Тонкий (< THIN) кусок вплотную к длинной грани более толстой параллельной стены и в её пределах."""
    x, y, w, h = r
    t = min(w, h)
    if t >= THIN:
        return False
    for ox, oy, ow, oh in others:
        if min(ow, oh) <= t:
            continue
        if w >= h and ow >= oh:  # обе горизонтальные
            if (abs(y - (oy + oh)) <= eps or abs(y + h - oy) <= eps) and ox - eps <= x and x + w <= ox + ow + eps:
                return True
        if h > w and oh > ow:  # обе вертикальные
            if (abs(x - (ox + ow)) <= eps or abs(x + w - ox) <= eps) and oy - eps <= y and y + h <= oy + oh + eps:
                return True
    return False


def bearing_segs(plan):
    """Несущие стены из walls_bearing → осевые линии (концы потом стыкует join() вместе с перегородками).

    1. Куски одной стены (тот же kind) сливаются (_merge_pieces): стена с входной дверью обычно задана
       двумя короткими простенками, и по отдельности они легли бы поперёк стены.
    2. Тонкая накладка на грани более толстой параллельной несущей стены (_is_overlay: уступ отделки,
       граница помещения для расчёта площади) отдельной стеной не строится — её место остаётся в помещении.
    3. Прямоугольник → осевая линия вдоль длинной стороны (seg_of_rect).
    4. Несущие стыкуются сначала между собой (join): каркас — узлы на осях несущих стен, и только потом
       к нему примыкают перегородки. Иначе конец несущей, не дошедший до оси соседней несущей, мог
       сойтись в угол с перегородкой, которая заканчивается рядом (стена комнаты у лоджии — с перегородкой
       коридора вместо торца лоджии)."""
    openings = [
        ((d["hinge"][0] + d["other"][0]) / 2, (d["hinge"][1] + d["other"][1]) / 2)
        for d in plan.get("doors", [])
    ] + [
        (w["rect"][0] + w["rect"][2] / 2, w["rect"][1] + w["rect"][3] / 2)
        for w in plan.get("windows", [])
    ]
    pieces = []
    for w in plan["walls_bearing"]:
        kind = w.get("kind", "bearing")
        if kind not in BEARING_KINDS:
            raise SystemExit(f"walls_bearing {w.get('id')}: kind {kind!r} — нужен один из {', '.join(BEARING_KINDS)}")
        pieces.append([list(w["rect"]), kind])
    changed = True
    while changed:
        changed = False
        for i in range(len(pieces)):
            for j in range(i + 1, len(pieces)):
                if pieces[i][1] == pieces[j][1]:
                    u = _merge_pieces(pieces[i][0], pieces[j][0], openings)
                    if u:
                        pieces[i][0] = u
                        del pieces[j]
                        changed = True
                        break
            if changed:
                break
    out = []
    for r, kind in pieces:
        if _is_overlay(r, [o for o, _ in pieces if o is not r]):
            continue
        out.append(seg_of_rect(r, kind))
    join(out)
    return out


def partitions(plan, doors_rp, bearing):
    walls = plan["partitions"] + [dict(w, kind="insulation") for w in plan.get("insulation", [])]
    segs = [seg_of_rect(p["rect"], p.get("kind", "partition")) for p in walls]
    raw = segs + bearing

    def crossed(s, g0, g1):
        """Проходит ли поперечная стена через разрыв (g0, g1) насквозь — тогда это Х-стык, куски не сливать."""
        for o in raw:
            if o.axis == s.axis or not (g0 - 1 <= o.c <= g1 + 1):
                continue
            if o.lo < s.c - s.d / 2 - 1 and o.hi > s.c + s.d / 2 + 1:
                return True
        return False

    # слить куски одной линии, если разрыв — дверь, или узкий (≤ 12 см) и поперечная стена в нём только заканчивается
    segs.sort(key=lambda s: (s.axis, s.c, s.d, s.lo))
    merged = []
    for s in segs:
        m = merged[-1] if merged else None
        if m and (m.axis, m.c, m.d, m.kind) == (s.axis, s.c, s.d, s.kind):
            gap = s.lo - m.hi
            door_in_gap = any(
                m.hi - 1 <= (dx if s.axis == "h" else dy) <= s.lo + 1
                and abs((dy if s.axis == "h" else dx) - s.c) <= s.d
                for dx, dy in doors_rp
            )
            if (gap <= MERGE_GAP and door_in_gap) or (
                gap <= 12 and not crossed(s, m.hi, s.lo)
            ):
                m.a0, m.a1 = m.lo, max(m.hi, s.hi)
                continue
        merged.append(s)
    return merged


def join(segs, only=None):
    """Стыки как в файлах, сохранённых самим RemPlanner (tools/reference/remplanner_example_v3_catalog.plan):
    only — стыковать только эти стены, остальные не двигать (утепление);
    угол — концы двух стен в общей точке на пересечении осей (link node);
    Т-примыкание — конец стены на грани проходящей стены (link edge), проходящая стена не делится."""
    for _ in range(3):
        for s in segs if only is None else only:
            for end, other_end in (("a0", "a1"), ("a1", "a0")):
                e, oe = getattr(s, end), getattr(s, other_end)
                best = None
                for o in segs:
                    if o is s or o.axis == s.axis:
                        continue
                    if not (o.lo - s.d / 2 - 1 <= s.c <= o.hi + s.d / 2 + 1):
                        continue
                    dist = abs(e - o.c)
                    if dist <= o.d / 2 + s.d / 2 + 1 and (
                        best is None or dist < best[0]
                    ):
                        best = (dist, o)
                if not best:
                    continue
                o = best[1]
                o_end = next(
                    (
                        k
                        for k in ("a0", "a1")
                        if abs(getattr(o, k) - s.c) <= max(o.d, s.d) / 2 + 1
                    ),
                    None,
                )
                if o_end and (only is None or o in only):  # угол: обе стены сходятся в узел на осях
                    setattr(s, end, o.c)
                    setattr(o, o_end, s.c)
                else:  # Т: упираемся в ближнюю грань
                    setattr(s, end, o.c - o.d / 2 if oe < o.c else o.c + o.d / 2)


def find_wall(walls_by_seg, x, y):
    cands = [(s, w) for s, w in walls_by_seg if s.contains(x, y)]
    if not cands:
        raise SystemExit(f"нет стены для проёма в точке ({x:.0f},{y:.0f})")
    return min(cands, key=lambda sw: abs((y if sw[0].axis == "h" else x) - sw[0].c))


def t_on(w, x, y):
    p1, p2 = w["p1"], w["p2"]
    L = math.hypot(p2["x"] - p1["x"], p2["y"] - p1["y"])
    return (
        (x - p1["x"]) * (p2["x"] - p1["x"]) + (y - p1["y"]) * (p2["y"] - p1["y"])
    ) / L


def rect_span(w, r):
    x, y, ww, hh = rect_rp(r)
    pts = [(x, y), (x + ww, y), (x, y + hh), (x + ww, y + hh)]
    ts = [t_on(w, *q) for q in pts]
    return min(ts), max(ts)


def out_path(path):
    """<name>.json → <name>.plan в той же папке."""
    return os.path.splitext(os.path.abspath(path))[0] + ".plan"


def export(path):
    plan = json.load(open(path, encoding="utf-8"))
    stem = os.path.splitext(os.path.basename(path))[0]
    R.random.seed(stem)  # стабильные id: перегенерация без изменений даёт тот же файл
    R._used.clear()
    set_frame(plan)
    doors = {d["id"]: d for d in plan["doors"]}
    door_mid = {
        k: to_rp(
            (d["hinge"][0] + d["other"][0]) / 2, (d["hinge"][1] + d["other"][1]) / 2
        )
        for k, d in doors.items()
    }

    bearing = bearing_segs(plan)
    parts = partitions(plan, list(door_mid.values()), bearing)
    # утепление стыкуется последним и не двигает другие стены: иначе стена комнаты у лоджии укорачивалась
    # до оси утепления и помещение «протекало» в щель у фасада
    ins = [s for s in parts if s.kind == "insulation"]
    segs = bearing + [s for s in parts if s.kind != "insulation"]
    join(segs)
    segs += ins
    join(segs, only=ins)
    walls_by_seg = []
    for s in segs:
        w = R.wall(*s.ends(), s.d, MATERIAL[s.kind])
        walls_by_seg.append((s, w))

    used_doors = set()
    for wd in plan["windows"]:
        x, y, ww, hh = rect_rp(wd["rect"])
        s, w = find_wall(walls_by_seg, x + ww / 2, y + hh / 2)
        t0, t1 = rect_span(w, wd["rect"])
        if wd.get("windoor_door"):
            d = doors[wd["windoor_door"]]
            used_doors.add(d["id"])
            th, to = t_on(w, *to_rp(*d["hinge"])), t_on(w, *to_rp(*d["other"]))
            dt0 = min(th, to)
            R.windoor(
                w,
                min(t0, dt0),
                d["width"],
                round(t1 - t0),
                d.get("h", 210),
                wd.get("h", 150),
                "l",
            )
            if dt0 > t0:
                print(
                    f"  ! {wd['id']}: дверь не у начала стены — RemPlanner поставит её у p1 (см. схему)"
                )
        else:
            R.window(
                w,
                t0,
                round(t1 - t0),
                wd.get("h", 150),
                wd.get("sill", 85),
                wd.get("casements", 1),
            )

    for d in plan["doors"]:
        if d["id"] in used_doors:
            continue
        mx, my = door_mid[d["id"]]
        s, w = find_wall(walls_by_seg, mx, my)
        th, to = t_on(w, *to_rp(*d["hinge"])), t_on(w, *to_rp(*d["other"]))
        p1, p2 = w["p1"], w["p2"]
        L = math.hypot(p2["x"] - p1["x"], p2["y"] - p1["y"])
        ux, uy = (p2["x"] - p1["x"]) / L, (p2["y"] - p1["y"]) / L
        sx, sy = d["swing"][0], (-d["swing"][1] if MIRROR else d["swing"][1])  # при отражении зеркалим y
        side = "l" if sx * uy + sy * (-ux) > 0 else "r"  # нормаль l = (uy, -ux)
        hinge = "l" if th < to else "r"  # l — петля у p1 стены
        kind = d.get("kind", "single")
        R.door(
            w,
            min(th, to),
            d["width"],
            d.get("h", 210),
            DOOR_TYPE.get(kind, kind),
            f"{side}-{hinge}",
        )

    items = []
    for f in plan["furniture"]:
        specs = f.get("rp")
        if not specs:
            continue
        for sp in specs if isinstance(specs, list) else [specs]:
            items += make_items(f["rect"], sp)

    out = R.new_plan([w for _, w in walls_by_seg], items)
    dst = out_path(path)
    R.dump(out, dst)
    nh = sum(len(w.get("holes", {})) for _, w in walls_by_seg)
    print(
        f"{stem}: стен {len(walls_by_seg)}, проёмов {nh}, предметов {len(items)} → {os.path.relpath(dst, ROOT)}"
    )
    new = sorted({it["name"] for it in items} - R.confirmed_names())
    if new:
        print(
            "  · не подтверждены импортом (проверить на снимке, затем — в tools/catalog/confirmed.json): "
            + ", ".join(new)
        )


def make_items(rect, sp):
    name, back = sp["name"], sp["back"]
    x, y, w, h = rect
    if name == "kitchen_run":
        return kitchen_run(rect, back, sp["modules"])
    cx, cy = to_rp(x + w / 2, y + h / 2)
    width, height = (w, h) if back in ("up", "down") else (h, w)
    extra = {k: v for k, v in sp.items() if k not in ("name", "back", "angle")}
    angle = sp.get("angle", angle_of(back))  # точный угол (стулья под 45°); back — ближайшая сторона для проверок
    return [R.item(name, cx, cy, width, height, angle, **extra)]


KITCHEN = {
    "box": "kitchen_box_door_double",
    "sink": "kitchen_box_door_double",
    "stove": "stove",
    "washer": "washing_machine",
    "dishwasher": "kitchen_box_dishwasher",
}


def kitchen_run(rect, back, modules):
    """Линия кухни вдоль стены + столешница поверх всего, кроме плиты. Модуль — сокращение
    (sink|box|stove|washer|dishwasher, по 60 см) или любое имя из полного каталога (ширина — из каталога,
    столешница — если custom_type table_top, напр. kitchen_box_oven, kitchen_box_corner_90)."""
    x, y, w, h = rect
    along_x = back in ("up", "down")
    length = w if along_x else h
    sub = lambda a, n: [x + a, y, n, h] if along_x else [x, y + a, w, n]
    out, a, top = [], 0, []
    for m in modules:
        name = KITCHEN.get(m, m)
        e = R.full_catalog()[name]
        n = 60 if m in KITCHEN else e["width"]
        r = sub(a, n)
        out += make_items(r, {"name": name, "back": back})
        if m in KITCHEN and m != "stove" or e.get("custom_type") == "table_top":
            top.append((a, a + n))
        if m == "sink":
            rx, ry, rw, rh = r
            s = (
                [rx + (rw - 45) / 2, ry + (rh - 40) / 2, 45, 40]
                if along_x
                else [rx + (rw - 40) / 2, ry + (rh - 45) / 2, 40, 45]
            )
            out += make_items(s, {"name": "kitchen_sink", "back": back})
        a += n
    if a < length:
        top.append((a, length))
    # слить соседние участки столешницы
    runs = []
    for s0, s1 in top:
        if runs and abs(runs[-1][1] - s0) < 1e-6:
            runs[-1][1] = s1
        else:
            runs.append([s0, s1])
    for s0, s1 in runs:
        out += make_items(sub(s0, s1 - s0), {"name": "worktop", "back": back})
    return out


if __name__ == "__main__":
    files = sys.argv[1:] or (
        sorted(glob.glob(os.path.join(ROOT, "plan", "*.json")))
        + sorted(glob.glob(os.path.join(ROOT, "concepts", "*", "*.json")))
    )
    if not files:
        raise SystemExit(f"нет планов: plan/*.json и concepts/*/*.json в {os.path.abspath(ROOT)} пусты")
    for p in files:
        export(p)
