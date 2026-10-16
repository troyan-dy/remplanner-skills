#!/usr/bin/env python3
"""ergonomics.py — автоматические правила эргономики для check_layout.py: у каждого правила два уровня.

МИНИМАЛЬНО ДОПУСТИМО (min) — жёсткая граница: хуже — концепция не проходит, без исключений.
ЖЕЛАТЕЛЬНО (want) — цель. Уступить, то есть остаться между want и min, можно, только если это кратно улучшает
другое (площадь санузла, вторая раковина, лишний метр шкафа…): концепция пишет в JSON
`"ergo_waivers": {"<правило>" | "<правило>:<начало имени объекта>": "что выигрываем"}` и повторяет это в README серии.
Уступка без обоснования — тоже не проходит. Сумма уступок ограничена бюджетом BUDGET: каждая стоит
weight × доля пути от want к min (0…1), так что уступить можно в одном-двух местах, а не везде понемногу.

Полный свод правил, включая ручные (свет, розетки, высоты), источники и споры между нормами —
tools/reference/ERGONOMICS.md; числа здесь и там одинаковые, id совпадают."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Rule:
    id: str
    what: str
    min: Optional[float]  # граница; None — жёсткой границы нет, только желательно
    want: float
    unit: str
    src: str  # откуда min / want; «предп.» — предположение
    sense: str = "ge"  # ge — больше лучше; le — меньше лучше
    weight: float = 1.0  # цена полной уступки (от want до min) в бюджете

    def level(self, v):
        """'hard' — хуже min; 'soft' — между want и min; 'ok'."""
        worse = (lambda a, b: a < b) if self.sense == "ge" else (lambda a, b: a > b)
        if self.min is not None and worse(v, self.min):
            return "hard"
        if worse(v, self.want):
            return "soft"
        return "ok"

    def cost(self, v):
        if self.level(v) != "soft":
            return 0.0
        if self.min is None or self.min == self.want:
            return self.weight
        return self.weight * min(1.0, abs(self.want - v) / abs(self.want - self.min))


BUDGET = 3.0  # предположение: ≈ три полные уступки или шесть половинных на концепцию

# Сокращения источников — tools/reference/ERGONOMICS.md «Источники».
RULES = [
    # Проходы и углы
    Rule("pass_any", "путь от входа к любой цели (место перед предметом, зона), ширина", 55, 55, "см",
         "плечи взрослого — предп."),
    Rule("pass_main", "путь от входа к каждой межкомнатной двери (сужение в самом проёме не считается)", 70, 90, "см",
         "min DIN 18011 (70 перед мебелью); want DIN 18011 (90 второстеп. коридор), NKBA K7 (91)"),
    Rule("corner_turn", "ширина прохода у выступающего угла, где маршрут поворачивает", 55, 90, "см",
         "min = pass_any; want NKBA K7 (91); углы скруглять — NKBA K26, СП 59 п. 6.2.6", weight=0.5),
    # Двери
    Rule("door_width", "ширина дверного полотна", 60, 80, "см",
         "min NKBA B1 (61, существующий санузел); want СП 59 п. 7.1.6, DIN 18040-2 (80)", weight=0.5),
    Rule("door_open", "угол открывания полотна до мебели или стены", 85, 90, "°",
         "NKBA K2/B2: двери не мешают; 85 — полотно ложится на стену, предп."),
    Rule("door_clash", "створки двух дверей задевают друг друга", None, 0, "шт.", "NKBA K2/B2", "le", 0.5),
    # Перед мебелью
    Rule("bed_side", "свободно вдоль бока кровати (без 55 см у изголовья, где тумба)", 50, 70, "см",
         "min предп.; want DIN 18011 (70)"),
    Rule("bed_foot", "свободно перед изножьем", 50, 70, "см", "min предп.; want DIN 18011 (70)", weight=0.5),
    Rule("ward_front", "перед шкафом-купе / открытым (двери не выходят вперёд)", 60, 70, "см",
         "min предп. (проход 55 + запас); want DIN 18011 (70 перед любой мебелью)"),
    Rule("ward_hinged_front", "перед шкафом с распашными дверями (створка 40–50 открывается на 90°)", 70, 90, "см",
         "min DIN 18011 (70); want DIN 18040-2 п. 5.4 (90 перед мебелью)"),
    Rule("drawer_front", "перед комодом/тумбой с ящиками (ящик выдвигается на 40–55)", 70, 90, "см",
         "min DIN 18011 (70); want DIN 18040-2 (90)", weight=0.5),
    Rule("shelf_front", "перед открытым стеллажом", 55, 70, "см", "min = pass_any; want DIN 18011", weight=0.5),
    Rule("kitchen_front", "перед кухонным фронтом и пеналами / между рядами", 90, 120, "см",
         "min NKBA K7 (91); want DIN 18022, DIN 18040-2 (120); NKBA K6 — 107 на одного"),
    Rule("washer_front", "перед стиральной машиной", 60, 90, "см", "min предп.; want DIN 18022 (90)", weight=0.5),
    Rule("wc_front", "перед унитазом", 60, 75, "см",
         "min выбор набора, предп. (между IRC 53 и NKBA 76); want DIN 18022 (75), NKBA B4 (76)"),
    Rule("wc_side", "от оси унитаза до препятствия слева и справа (стоя лицом к унитазу)", 38, 45, "см",
         "min IRC через NKBA B20 (38); want DIN 18022 (20+25), NKBA B20 (46)"),
    Rule("sink_front", "перед раковиной", 70, 75, "см", "min выбор набора, предп.; want DIN 18022 (75), NKBA B4"),
    Rule("sink_side", "от оси раковины до препятствия слева и справа", 38, 50, "см",
         "min IRC через NKBA B5 (38); want DIN 18022 (30+20), NKBA B5 (51)", weight=0.5),
    Rule("sofa_front", "от дивана до столика/препятствия", 30, 40, "см", "предп. (Panero 30–45, не сверено)",
         weight=0.5),
    Rule("desk_back", "от кромки рабочего стола до препятствия за креслом", 75, 90, "см",
         "min предп.; want NKBA K8 (91)"),
    Rule("dining_back", "от кромки обеденного стола до препятствия за стулом", 80, 90, "см",
         "min NKBA K8 (81), DIN 18011 (стул 50 + 30); want NKBA K8 (91)"),
    # Кухня
    Rule("hob_side", "столешница с меньшей стороны плиты", 30, 40, "см", "min NKBA K17, DIN 18022 (30); want предп."),
    Rule("hob_side_big", "столешница с большей стороны плиты", 38, 60, "см", "min NKBA K17 (38); want предп.",
         weight=0.5),
    Rule("sink_hob", "столешница между мойкой и плитой", 40, 90, "см",
         "min предп. (доска); want NKBA K24 (61 + 30)"),
    Rule("hob_window", "от плиты до окна по плану", 15, 30, "см", "NKBA K20 (не под окном); числа предп.",
         weight=0.5),
    Rule("triangle_sum", "сумма сторон треугольника мойка–плита–холодильник", 900, 790, "см",
         "want NKBA K3; min предп.", "le", 0.5),
    Rule("triangle_leg", "кратчайшая сторона треугольника", 60, 120, "см", "want NKBA K3; min предп.",
         weight=0.5),
    Rule("triangle_leg_max", "длиннейшая сторона треугольника", 300, 270, "см", "want NKBA K3; min предп.",
         "le", 0.5),
    # ТВ и рабочее место
    Rule("tv_distance", "дистанция от глаз до ТВ в диагоналях, не ближе", 1.0, 1.2, "диаг.",
         "предп. (THX 40° ≈ 1,2 диаг.)"),
    Rule("tv_angle", "ТВ в стороне от оси взгляда", 30, 15, "°", "предп.", "le", 0.5),
    Rule("desk_window", "окно не сбоку от сидящего: отклонение от 90°", None, 45, "°",
         "предп. (свет сбоку, без бликов и слепящего окна перед экраном)", "le", 0.5),
]
R = {r.id: r for r in RULES}


def _waiver(waivers, rule, obj):
    for k, why in waivers.items():
        rid, _, pre = k.partition(":")
        if rid == rule and (not pre or obj.startswith(pre)):
            return why
    return None


def judge(measurements, waivers):
    """measurements: [(правило, объект, значение)] → итог: ok, hard, soft (с обоснованием или без), score."""
    rows, hard, soft, unjust, score = [], [], [], [], 0.0
    for rule, obj, v in measurements:
        r = R[rule]
        lv = r.level(v)
        why = _waiver(waivers, rule, obj) if lv == "soft" else None
        rows.append((rule, obj, v, lv, why))
        if lv == "hard":
            hard.append((rule, obj, v))
        elif lv == "soft":
            score += r.cost(v)
            (soft if why else unjust).append((rule, obj, v, why))
    used = {k for k in waivers if any(_waiver({k: 1}, rl, ob) for rl, ob, _, lv, _ in rows if lv == "soft")}
    return {
        "rows": rows,
        "hard": hard,
        "soft": soft,
        "unjust": unjust,
        "score": round(score, 2),
        "unused": sorted(set(waivers) - used),
        "ok": not hard and not unjust and score <= BUDGET,
    }


def _fmt(rule, v):
    r = R[rule]
    lim = f"мин {r.min}" if r.min is not None else "без мин."
    return f"{rule} {v} {r.unit} (жел. {r.want}, {lim})"


def table():
    """Markdown-таблица правил — для tools/reference/ERGONOMICS.md."""
    rows = ["| id | что | мин. допустимо | желательно | ед. | вес | источник |", "|---|---|---|---|---|---|---|"]
    for r in RULES:
        sign = "≥" if r.sense == "ge" else "≤"
        mn = f"{sign} {r.min:g}" if r.min is not None else "—"
        rows.append(f"| `{r.id}` | {r.what} | {mn} | {sign} {r.want:g} | {r.unit} | {r.weight:g} | {r.src} |")
    return "\n".join(rows)


def report(name, v, verbose=False, waivers=False):
    head = f"{name}: " + ("ok" if v["ok"] else "НЕ ПРОХОДИТ")
    head += f" · уступок {len(v['soft']) + len(v['unjust'])}, балл {v['score']} из {BUDGET}"
    lines = [head]
    for rule, obj, val in v["hard"]:
        lines.append(f"  ✗ ниже минимума: {obj} — {_fmt(rule, val)}")
    for rule, obj, val, _ in v["unjust"]:
        lines.append(f"  ? уступка без обоснования: {obj} — {_fmt(rule, val)}")
    for rule, obj, val, why in v["soft"] if waivers or verbose else []:
        lines.append(f"  ~ уступка: {obj} — {_fmt(rule, val)} — {why}")
    for k in v["unused"]:
        lines.append(f"  · обоснование не нужно (нарушения нет): {k}")
    if v["score"] > BUDGET:
        lines.append(f"  ✗ уступок больше бюджета: {v['score']} > {BUDGET}")
    if verbose:
        for rule, obj, val, lv, _ in v["rows"]:
            if lv == "ok":
                lines.append(f"    ok {obj} — {_fmt(rule, val)}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(table())
