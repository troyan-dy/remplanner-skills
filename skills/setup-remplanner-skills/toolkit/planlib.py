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
import os
import sys

from rpkit.console import say
from rpkit.jsonfile import read_json, write_json
from rpkit.plan_records import (
    BEARING_KINDS,
    CLEARED_KEYS,
    DOORS,
    ID,
    KIND,
    NAME,
    NOTE,
    PLAN_KEYS,
)
from rpkit.plan_records import RECT, SQ_CM_IN_M2, default_doors, room_areas, with_optional

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)  # корень проекта — родитель tools/
AS_IS = os.path.join(ROOT, "plan", "as_is.json")

FIXED_KINDS = ("drain", "riser", "vent")  # точка канализации, стояк, вентканал (PLAN_FORMAT.md, fixed_elements)


def load(path):
    """JSON плана (путь абсолютный или от корня проекта)."""
    if not os.path.isabs(path):
        path = os.path.join(ROOT, path)
    return read_json(path)


def as_is():
    """Квартира «как есть» — plan/as_is.json (свежая копия: правки не попадают в другие концепции)."""
    if not os.path.exists(AS_IS):
        relative = os.path.relpath(AS_IS, ROOT)
        sys.exit(f"нет {relative} — сначала опишите квартиру «как есть»")
    return load(AS_IS)


def is_entry(d):  # noqa: WPS111 — публичный API, имя параметра видно в tools/blocks.py
    """Входная дверь: "entry": true, иначе id "door-entry" (как в check_layout/check_rules)."""
    return bool(d.get("entry")) or d[ID] == "door-entry"


def blank(title, keep_doors=None, base=None):
    """Каркас для новой концепции: несущие стены, окна, утепление, fixed_elements, meta и structural_waivers
    (уступки из-за несущего, ergonomics.py) из плана «как есть»; partitions, furniture, zones, rooms,
    ergo_waivers — пустые.
    keep_doors — id дверей, которые остаются; по умолчанию входная (is_entry) и двери балконных блоков
    (windows[].windoor_door) — они в несущих стенах. base — свой исходный план вместо as_is()."""
    plan = as_is() if base is None else copy.deepcopy(base)
    plan.setdefault("meta", {})["title"] = title
    keep = default_doors(plan) if keep_doors is None else set(keep_doors)
    doors = plan.get(DOORS, [])
    plan[DOORS] = [door for door in doors if door[ID] in keep]
    for key in CLEARED_KEYS:
        plan[key] = []
    plan.pop("ergo_waivers", None)
    return plan


def rp(name, back, **kw):
    """Привязка предмета к каталогу RemPlanner (rp_lib.CATALOG или полный каталог tools/catalog).
    back — к какой стороне (в исходных координатах JSON) обращена спинка/бачок/изголовье: up|down|left|right.
    name = "kitchen_run" — линия кухни: kw["modules"] — сокращения sink|box|stove|washer|dishwasher (по 60 см)
    или имена каталога; столешница кладётся сама. Прочие kw (over_floor, self_height, angle…) — как есть в rp."""
    return dict(name=name, back=back, **kw)


def F(fid, rect, name, kind, back, **kw):  # noqa: WPS111, WPS211 — публичный API генераторов (PLAN_FORMAT.md)
    """Предмет мебели: rect в исходных координатах, kind — имя каталога RemPlanner, back — куда спинка."""
    return {
        ID: fid,
        RECT: rect,
        NAME: name,
        "rp": rp(kind, back, **kw),
    }


def W(wid, rect, note=None, kind=None):  # noqa: WPS111 — публичный API генераторов (PLAN_FORMAT.md)
    """Перегородка (partitions): rect; kind — None (блок) или "glass"."""
    optional = ((NOTE, note), (KIND, kind))
    return with_optional({ID: wid, RECT: rect}, optional)


# публичный API генераторов (PLAN_FORMAT.md): имя D и параметр h= есть в генераторах проектов
def D(did, width, hinge, other, swing, note=None, kind=None, h=None, entry=False):  # noqa: WPS111, WPS211
    """Дверь: hinge — точка петли, other — второй край проёма (оба на одной линии стены), swing — куда
    открывается полотно ([0, -1] — вверх по y и т. п.). kind — тип проёма RemPlanner: None (распашная single)
    или "doorway" (проём без полотна, так же условно — купе). entry=True — входная дверь квартиры
    ("entry": true; экспортёр поле не читает, проверки ведут от неё маршруты). h — высота, см."""
    door = {
        ID: did,
        "width": width,
        "hinge": hinge,
        "other": other,
        "swing": swing,
    }
    optional = (
        (NOTE, note),
        (KIND, kind),
        ("h", h),
        ("entry", True if entry else None),
    )
    return with_optional(door, optional)


def room(rid, name, area, rect=None, note=None, bti=None):  # noqa: WPS211 — публичный API
    """Помещение: area в м² (округляется до 0,01); rect нужен проверкам мокрых комнат, спальни, комнаты со столом.
    bti — площадь по экспликации БТИ, м²: save печатает разницу с area (сверка чертежа «как есть»)."""
    record = {ID: rid, NAME: name, "area": round(area, 2)}
    with_optional(record, ((RECT, rect), (NOTE, note)))
    if bti is not None:
        record["bti_area"] = bti
    return record


def skeleton(title, ceiling_height=None, source=None):
    """Пустой план для src/as_is.py: meta и пустые разделы. Образец — tools/example/as_is.py."""
    optional = (("ceiling_height", ceiling_height), ("source", source))
    meta = with_optional({"units": "cm", "title": title}, optional)
    return {"meta": meta, **{key: [] for key in PLAN_KEYS}}


def bearing(wid, rect, kind, note=None):
    """Несущая стена (walls_bearing): kind — facade (наружная), interapartment (межквартирная),
    bearing (внутренняя несущая), column (колонна, пилон, бетонный массив)."""
    if kind not in BEARING_KINDS:
        raise ValueError(f"{wid}: kind {kind!r} — нужен facade, interapartment, bearing или column")
    return with_optional({ID: wid, RECT: rect, KIND: kind}, ((NOTE, note),))


def window(wid, rect, h=150, sill=85, windoor_door=None, note=None):  # noqa: WPS111, WPS211 — публичный API
    """Окно: rect — в толще стены, длина — ширина проёма. Балконный блок: rect — только оконная часть,
    windoor_door — id двери блока в doors, проём двери вплотную к окну."""
    record = {"id": wid, RECT: rect, "h": h, "sill": sill}
    return with_optional(record, (("windoor_door", windoor_door), (NOTE, note)))


def zone(zid, rect, name):
    """Свободная зона (перед унитазом, раковиной, входом в душ…): проверки ведут к ней проход."""
    return {ID: zid, RECT: rect, NAME: name}


def fixed(fid, kind, point=None, rect=None, name=None):
    """Неподвижный элемент (fixed_elements): kind "drain" — точка подключения канализации (point),
    "riser" — стояк (point или rect), "vent" — вентканал (rect)."""
    if kind not in FIXED_KINDS:
        kinds = ", ".join(FIXED_KINDS)
        raise ValueError(f"fixed_elements kind {kind!r}: нужен один из {kinds}")
    if point is None and rect is None:
        raise ValueError(f"{fid}: нужен point или rect")
    element = {ID: fid, KIND: kind}
    if point is not None:
        element["point"] = list(point)
    if rect is not None:
        element[RECT] = list(rect)
    return with_optional(element, ((NAME, name),))


def waive(p, **kw):  # noqa: WPS111 — публичный API, имя параметра видно в tools/blocks.py
    """Уступки от «желательно» с обоснованием (ergo_waivers): ключ — «правило» или «правило:начало имени объекта».
    Два способа записи:
        waive(p, wc_side="унитаз у стояка: сбоку 22 — зато без подиума")         # имя правила — аргумент
        waive(p, **{"door_open:door-bath": "дверь упирается в тумбу на 80° — зато раковина 80"})  # с объектом
    В имени аргумента «:» можно писать как «__» (wc_side__wc → "wc_side:wc"), но id с дефисом так не записать —
    тогда только словарь **{...}. Уступки из-за несущего — не здесь, а structural_waivers в plan/as_is.json."""
    waivers = {
        key.replace("__", ":"): why for key, why in kw.items()
    }
    p.setdefault("ergo_waivers", {}).update(waivers)


def area(*rects, minus=()):
    """Площадь в м²: сумма прямоугольников [x, y, w, h] (см) минус прямоугольники minus (вентблок, короб, ниша)."""
    total = sum(rect[2] * rect[3] for rect in rects)
    cut = sum(rect[2] * rect[3] for rect in minus)
    return (total - cut) / SQ_CM_IN_M2


def series_dir(nn, date):
    """concepts/run-NN_<дата>/ от корня проекта (папка создаётся при save)."""
    number = format(int(nn), "02d")
    return os.path.join(ROOT, "concepts", f"run-{number}_{date}")


def save(plans, out_dir):
    """Пишет каждую концепцию в <out_dir>/<name>.json и печатает площади комнат.
    plans — {name: plan} или список пар (name, plan)."""
    os.makedirs(out_dir, exist_ok=True)
    pairs = plans.items() if isinstance(plans, dict) else plans
    for name, plan in pairs:
        path = os.path.join(out_dir, f"{name}.json")
        write_json(path, plan, ensure_ascii=False, indent=1)
        relative = os.path.relpath(path, ROOT)
        say(f"{relative}: {room_areas(plan)}")
