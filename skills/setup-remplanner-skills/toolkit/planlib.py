"""planlib.py — библиотека для генераторов серий концепций (src/concepts_runNN.py проекта).

Генератор серии берёт каркас квартиры «как есть» (plan/as_is.json), строит на нём концепции и пишет
их JSON в concepts/run-NN_<ГГГГ-ММ-ДД>/<name>.json. Формат JSON — tools/reference/PLAN_FORMAT.md.
Координаты — см, исходная ориентация плана, y вниз; rect = [x, y, ширина, высота].

Пример (src/concepts_run01.py):

    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
    from planlib import D, F, W, area, blank, room, save, series_dir, waive, zone

    def concept_a():
        p = blank("Концепция A — санузел у стояка")              # несущие, окна, входная и балконная двери
        p["partitions"] += [W("bath-top", [184, 666, 247, 10])]
        p["doors"] += [D("door-bath", 70, [361, 666], [291, 666], [0, -1])]
        p["furniture"] += [F("wc", [213, 771, 38, 65], "унитаз", "toilet", "down")]
        p["zones"] += [zone("z-wc", [194, 706, 77, 65], "перед унитазом")]
        p["rooms"] += [room("bath", "Санузел", area([194, 676, 237, 160]), [194, 676, 237, 160])]
        waive(p, wc_side="унитаз у стояка: сбоку 22 — зато без подиума")
        return p

    if __name__ == "__main__":
        save({"concept_a": concept_a()}, series_dir(1, "2026-01-31"))

План «как есть» (src/as_is.py) строится так же, но с нуля: skeleton, bearing, window, fixed —
образец tools/example/as_is.py; save({"as_is": p}, os.path.join(ROOT, "plan")).

Дальше: python3 tools/remplanner_export.py concepts/run-01_*/*.json и проверки tools/check_layout.py,
tools/check_rules.py по тем же файлам.
"""

import copy
import json
import os

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)  # корень проекта — родитель tools/
AS_IS = os.path.join(ROOT, "plan", "as_is.json")

FIXED_KINDS = ("drain", "riser", "vent")  # точка канализации, стояк, вентканал (PLAN_FORMAT.md, fixed_elements)


def load(path):
    """JSON плана (путь абсолютный или от корня проекта)."""
    path = path if os.path.isabs(path) else os.path.join(ROOT, path)
    return json.load(open(path, encoding="utf-8"))


def as_is():
    """Квартира «как есть» — plan/as_is.json (свежая копия: правки не попадают в другие концепции)."""
    if not os.path.exists(AS_IS):
        raise SystemExit(f"нет {os.path.relpath(AS_IS, ROOT)} — сначала опишите квартиру «как есть»")
    return load(AS_IS)


def is_entry(d):
    """Входная дверь: "entry": true, иначе id "door-entry" (как в check_layout/check_rules)."""
    return bool(d.get("entry")) or d["id"] == "door-entry"


def blank(title, keep_doors=None, base=None):
    """Каркас для новой концепции: несущие стены, окна, утепление, fixed_elements, meta и structural_waivers
    (уступки из-за несущего, ergonomics.py) из плана «как есть»; partitions, furniture, zones, rooms,
    ergo_waivers — пустые.
    keep_doors — id дверей, которые остаются; по умолчанию входная (is_entry) и двери балконных блоков
    (windows[].windoor_door) — они в несущих стенах. base — свой исходный план вместо as_is()."""
    p = copy.deepcopy(base) if base is not None else as_is()
    p.setdefault("meta", {})["title"] = title
    if keep_doors is None:
        windoor = {w["windoor_door"] for w in p.get("windows", []) if w.get("windoor_door")}
        keep = {d["id"] for d in p.get("doors", []) if is_entry(d) or d["id"] in windoor}
    else:
        keep = set(keep_doors)
    p["doors"] = [d for d in p.get("doors", []) if d["id"] in keep]
    p["partitions"], p["furniture"], p["zones"], p["rooms"] = [], [], [], []
    p.pop("ergo_waivers", None)
    return p


def rp(name, back, **kw):
    """Привязка предмета к каталогу RemPlanner (rp_lib.CATALOG или полный каталог tools/catalog).
    back — к какой стороне (в исходных координатах JSON) обращена спинка/бачок/изголовье: up|down|left|right.
    name = "kitchen_run" — линия кухни: kw["modules"] — сокращения sink|box|stove|washer|dishwasher (по 60 см)
    или имена каталога; столешница кладётся сама. Прочие kw (over_floor, self_height, angle…) — как есть в rp."""
    return dict(name=name, back=back, **kw)


def F(fid, rect, name, kind, back, **kw):
    """Предмет мебели: rect в исходных координатах, kind — имя каталога RemPlanner, back — куда спинка."""
    return {"id": fid, "rect": rect, "name": name, "rp": rp(kind, back, **kw)}


def W(wid, rect, note=None, kind=None):
    """Перегородка (partitions): rect; kind — None (блок) или "glass"."""
    w = {"id": wid, "rect": rect}
    if note:
        w["note"] = note
    if kind:
        w["kind"] = kind
    return w


def D(did, width, hinge, other, swing, note=None, kind=None, h=None, entry=False):
    """Дверь: hinge — точка петли, other — второй край проёма (оба на одной линии стены), swing — куда
    открывается полотно ([0, -1] — вверх по y и т. п.). kind — тип проёма RemPlanner: None (распашная single)
    или "doorway" (проём без полотна, так же условно — купе). entry=True — входная дверь квартиры
    ("entry": true; экспортёр поле не читает, проверки ведут от неё маршруты). h — высота, см."""
    d = {"id": did, "width": width, "hinge": hinge, "other": other, "swing": swing}
    if note:
        d["note"] = note
    if kind:
        d["kind"] = kind
    if h:
        d["h"] = h
    if entry:
        d["entry"] = True
    return d


def room(rid, name, area, rect=None, note=None, bti=None):
    """Помещение: area в м² (округляется до 0,01); rect нужен проверкам мокрых комнат, спальни, комнаты со столом.
    bti — площадь по экспликации БТИ, м²: save печатает разницу с area (сверка чертежа «как есть»)."""
    r = {"id": rid, "name": name, "area": round(area, 2)}
    if rect:
        r["rect"] = rect
    if note:
        r["note"] = note
    if bti is not None:
        r["bti_area"] = bti
    return r


def skeleton(title, ceiling_height=None, source=None):
    """Пустой план для src/as_is.py: meta и пустые разделы. Образец — tools/example/as_is.py."""
    meta = {"units": "cm", "title": title}
    if ceiling_height:
        meta["ceiling_height"] = ceiling_height
    if source:
        meta["source"] = source
    keys = ("walls_bearing", "partitions", "windows", "doors", "fixed_elements", "furniture", "zones", "rooms")
    return {"meta": meta, **{k: [] for k in keys}}


def bearing(wid, rect, kind, note=None):
    """Несущая стена (walls_bearing): kind — facade (наружная), interapartment (межквартирная),
    bearing (внутренняя несущая), column (колонна, пилон, бетонный массив)."""
    if kind not in ("facade", "interapartment", "bearing", "column"):
        raise ValueError(f"{wid}: kind {kind!r} — нужен facade, interapartment, bearing или column")
    w = {"id": wid, "rect": rect, "kind": kind}
    if note:
        w["note"] = note
    return w


def window(wid, rect, h=150, sill=85, windoor_door=None, note=None):
    """Окно: rect — в толще стены, длина — ширина проёма. Балконный блок: rect — только оконная часть,
    windoor_door — id двери блока в doors, проём двери вплотную к окну."""
    w = {"id": wid, "rect": rect, "h": h, "sill": sill}
    if windoor_door:
        w["windoor_door"] = windoor_door
    if note:
        w["note"] = note
    return w


def zone(zid, rect, name):
    """Свободная зона (перед унитазом, раковиной, входом в душ…): проверки ведут к ней проход."""
    return {"id": zid, "rect": rect, "name": name}


def fixed(fid, kind, point=None, rect=None, name=None):
    """Неподвижный элемент (fixed_elements): kind "drain" — точка подключения канализации (point),
    "riser" — стояк (point или rect), "vent" — вентканал (rect)."""
    if kind not in FIXED_KINDS:
        raise ValueError(f"fixed_elements kind {kind!r}: нужен один из {', '.join(FIXED_KINDS)}")
    if point is None and rect is None:
        raise ValueError(f"{fid}: нужен point или rect")
    e = {"id": fid, "kind": kind}
    if point is not None:
        e["point"] = list(point)
    if rect is not None:
        e["rect"] = list(rect)
    if name:
        e["name"] = name
    return e


def waive(p, **kw):
    """Уступки от «желательно» с обоснованием (ergo_waivers): ключ — «правило» или «правило:начало имени объекта».
    Два способа записи:
        waive(p, wc_side="унитаз у стояка: сбоку 22 — зато без подиума")         # имя правила — аргумент
        waive(p, **{"door_open:door-bath": "дверь упирается в тумбу на 80° — зато раковина 80"})  # с объектом
    В имени аргумента «:» можно писать как «__» (wc_side__wc → "wc_side:wc"), но id с дефисом так не записать —
    тогда только словарь **{...}. Уступки из-за несущего — не здесь, а structural_waivers в plan/as_is.json."""
    p.setdefault("ergo_waivers", {}).update({k.replace("__", ":"): v for k, v in kw.items()})


def area(*rects, minus=()):
    """Площадь в м²: сумма прямоугольников [x, y, w, h] (см) минус прямоугольники minus (вентблок, короб, ниша)."""
    return (sum(r[2] * r[3] for r in rects) - sum(r[2] * r[3] for r in minus)) / 1e4


def series_dir(nn, date):
    """concepts/run-NN_<дата>/ от корня проекта (папка создаётся при save)."""
    return os.path.join(ROOT, "concepts", f"run-{int(nn):02d}_{date}")


def save(plans, out_dir):
    """Пишет каждую концепцию в <out_dir>/<name>.json и печатает площади комнат.
    plans — {name: plan} или список пар (name, plan)."""
    os.makedirs(out_dir, exist_ok=True)
    items = plans.items() if isinstance(plans, dict) else plans
    for name, p in items:
        path = os.path.join(out_dir, name + ".json")
        json.dump(p, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        rooms = ", ".join(
            f"{r['id']} {r['area']:.2f}" + (f" (БТИ {r['bti_area']:.2f}, {r['area'] - r['bti_area']:+.2f})"
                                            if r.get("bti_area") is not None else "")
            for r in p.get("rooms", []))
        print(f"{os.path.relpath(path, ROOT)}: {rooms or 'комнат нет'}")
