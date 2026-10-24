#!/usr/bin/env python3
"""ergonomics.py — автоматические правила эргономики для check_layout.py: у каждого правила два уровня.

МИНИМАЛЬНО ДОПУСТИМО (min) — жёсткая граница: хуже — концепция не проходит, без исключений.
ЖЕЛАТЕЛЬНО (want) — цель. Уступить, то есть остаться между want и min, можно, только если это кратно улучшает
другое (площадь санузла, вторая раковина, лишний метр шкафа…): концепция пишет в JSON
`"ergo_waivers": {"<правило>" | "<правило>:<начало имени объекта>": "что выигрываем"}` и повторяет это в README серии.
Уступка без обоснования — тоже не проходит. Сумма уступок ограничена бюджетом BUDGET: каждая стоит
weight × доля пути от want к min (0…1), так что уступить можно в одном-двух местах, а не везде понемногу.

ИЗ-ЗА НЕСУЩЕГО. Уступки, которые навязывают несущие конструкции, бюджет не тратят:
- план «как есть» (plan/as_is.json) пишет `"structural_waivers": {"<правило>" | "<правило>:<начало имени объекта>":
  "причина"}` — planlib.as_is()/blank() переносят поле в каждую концепцию; уступка по такому ключу считается
  обоснованной и стоит 0 (ниже min — по-прежнему не проходит: несущее не оправдывает недопустимое);
- проход (pass_any, pass_main), у которого горлышко — между двумя несущими стенами (cap в измерении
  rpkit/layout_passages.py): шире его не сделать, уступка — «из-за несущего» без записи в JSON. Общий случай cost(v, cap):
  цель want снижается до cap, баллы — только за недобор ниже cap.
Такие уступки check_layout -w печатает отдельно («≈ из-за несущего»).

Полный свод правил, включая ручные (свет, розетки, высоты), источники и споры между нормами —
tools/reference/ERGONOMICS.md; числа здесь и там одинаковые, id совпадают."""

from dataclasses import dataclass
from typing import Optional

from rpkit import ergo_judge, ergo_report, ergo_table
from rpkit.console import say
from rpkit.frozen import frozen

GE = "ge"  # больше — лучше
LE = "le"  # меньше — лучше
CM = "см"
DEGREES = "°"
PIECES = "шт."
DIAGONALS = "диаг."
BUDGET = 3.0  # предположение: ≈ три полные уступки или шесть половинных на концепцию


@dataclass(frozen=True)
class Rule:
    """Правило эргономики: граница min, цель want, единицы, источник, направление и вес уступки."""

    id: str
    what: str
    min: Optional[float]  # граница; None — жёсткой границы нет, только желательно
    want: float
    unit: str
    src: str  # откуда min / want; «предп.» — предположение
    sense: str = GE  # ge — больше лучше; le — меньше лучше
    weight: float = 1.0  # цена полной уступки (от want до min) в бюджете

    def is_worse(self, measured, limit):
        """Значение хуже границы limit с учётом направления правила."""
        if self.sense == GE:
            return measured < limit
        return measured > limit

    def level(self, measured):
        """'hard' — хуже min; 'soft' — между want и min; 'ok'."""
        if self.min is not None and self.is_worse(measured, self.min):
            return ergo_judge.HARD
        if self.is_worse(measured, self.want):
            return ergo_judge.SOFT
        return ergo_judge.OK

    def cost(self, measured, cap=None):
        """Цена уступки; cap — лучшее значение, которое пускают несущие стены: хуже want — цель снижается до cap."""
        if self.level(measured) != ergo_judge.SOFT:
            return float(0)
        want = self.want
        if cap is not None and self.level(cap) != ergo_judge.OK:
            want = cap
            if not self.is_worse(measured, want):
                return float(0)
        if self.min is None or self.min == self.want:
            return self.weight
        gap = abs(want - measured)
        share = gap / abs(self.want - self.min)
        return self.weight * min(1.0, share)


# Сокращения источников — tools/reference/ERGONOMICS.md «Источники».
# (id, что, min, want, единицы, источник[, направление, вес])
RULE_TABLE = (
    # Проходы и углы
    ("pass_any", "путь от входа к любой цели (место перед предметом, зона), ширина", 55, 55, CM,
     "плечи взрослого — предп."),
    ("pass_main", "путь от входа к каждой межкомнатной двери (сужение в самом проёме не считается)", 70, 90, CM,
     "min DIN 18011 (70 перед мебелью); want DIN 18011 (90 второстеп. коридор), NKBA K7 (91)"),
    ("corner_turn", "ширина прохода у выступающего угла, где маршрут поворачивает", 55, 90, CM,
     "min = pass_any; want NKBA K7 (91); углы скруглять — NKBA K26, СП 59 п. 6.2.6", GE, 0.5),
    # Двери
    ("door_width", "ширина дверного полотна", 60, 80, CM,
     "min NKBA B1 (61, существующий санузел); want СП 59 п. 7.1.6, DIN 18040-2 (80)", GE, 0.5),
    ("door_open", "угол открывания полотна до мебели или стены", 85, 90, DEGREES,
     "NKBA K2/B2: двери не мешают; 85 — полотно ложится на стену, предп."),
    ("door_clash", "створки двух дверей задевают друг друга или створка заходит в соседний проём", None, 0,
     PIECES, "NKBA K2/B2", LE, 0.5),
    ("door_leaf_pass", "открытое на 90° полотно поперёк маршрута: проход от края полотна до препятствия", 0, 70,
     CM, "want = min pass_main (DIN 18011, 70); NKBA K2/B2: двери не мешают; жёсткой границы нет — полотно "
     "открыто ненадолго, а дверь санузла наружу в коридор 90 — обычное дело (предп.)", GE, 0.25),
    ("door_leaf_front", "открытое на 90° полотно перед распашным шкафом, ящиками, кухней, стиральной машиной: "
     "от фасада до полотна", 50, 70, CM,
     "min предп. (дверца или ящик открывается на 40–55); want DIN 18011 (70 перед мебелью); NKBA K2/B2",
     GE, 0.5),
    # Перед мебелью
    ("bed_side", "свободно вдоль бока кровати (без 55 см у изголовья, где тумба)", 50, 70, CM,
     "min предп.; want DIN 18011 (70)"),
    ("bed_foot", "свободно перед изножьем", 50, 70, CM, "min предп.; want DIN 18011 (70)", GE, 0.5),
    ("ward_front", "перед шкафом-купе / открытым (двери не выходят вперёд)", 60, 70, CM,
     "min предп. (проход 55 + запас); want DIN 18011 (70 перед любой мебелью)"),
    ("ward_hinged_front", "перед шкафом с распашными дверями (створка 40–50 открывается на 90°)", 70, 90, CM,
     "min DIN 18011 (70); want DIN 18040-2 п. 5.4 (90 перед мебелью)"),
    ("drawer_front", "перед комодом/тумбой с ящиками (ящик выдвигается на 40–55)", 70, 90, CM,
     "min DIN 18011 (70); want DIN 18040-2 (90)", GE, 0.5),
    ("shelf_front", "перед открытым стеллажом", 55, 70, CM, "min = pass_any; want DIN 18011", GE, 0.5),
    ("kitchen_front", "перед кухонным фронтом и пеналами / между рядами", 90, 120, CM,
     "min NKBA K7 (91); want DIN 18022, DIN 18040-2 (120); NKBA K6 — 107 на одного"),
    ("washer_front", "перед стиральной машиной", 60, 90, CM, "min предп.; want DIN 18022 (90)", GE, 0.5),
    ("wc_front", "перед унитазом", 60, 75, CM,
     "min выбор набора, предп. (между IRC 53 и NKBA 76); want DIN 18022 (75), NKBA B4 (76)"),
    ("wc_side", "от оси унитаза до препятствия слева и справа (стоя лицом к унитазу)", 38, 45, CM,
     "min IRC через NKBA B20 (38); want DIN 18022 (20+25), NKBA B20 (46)"),
    ("sink_front", "перед раковиной", 70, 75, CM, "min выбор набора, предп.; want DIN 18022 (75), NKBA B4"),
    ("sink_side", "от оси раковины до препятствия слева и справа", 38, 50, CM,
     "min IRC через NKBA B5 (38); want DIN 18022 (30+20), NKBA B5 (51)", GE, 0.5),
    ("sofa_front", "от дивана до столика/препятствия", 30, 40, CM, "предп. (Panero 30–45, не сверено)",
     GE, 0.5),
    ("desk_back", "от кромки рабочего стола до препятствия за креслом", 75, 90, CM,
     "min предп.; want NKBA K8 (91)"),
    ("dining_back", "от кромки обеденного стола до препятствия за стулом", 80, 90, CM,
     "min NKBA K8 (81), DIN 18011 (стул 50 + 30); want NKBA K8 (91)"),
    # Кухня
    ("hob_side", "столешница с меньшей стороны плиты", 30, 40, CM, "min NKBA K17, DIN 18022 (30); want предп."),
    ("hob_side_big", "столешница с большей стороны плиты", 38, 60, CM, "min NKBA K17 (38); want предп.",
     GE, 0.5),
    ("sink_hob", "столешница между мойкой и плитой", 40, 90, CM,
     "min предп. (доска); want NKBA K24 (61 + 30)"),
    ("hob_window", "от плиты до окна по плану", 15, 30, CM, "NKBA K20 (не под окном); числа предп.",
     GE, 0.5),
    ("triangle_sum", "сумма сторон треугольника мойка–плита–холодильник", 900, 790, CM,
     "want NKBA K3; min предп.", LE, 0.5),
    ("triangle_leg", "кратчайшая сторона треугольника", 60, 120, CM, "want NKBA K3; min предп.",
     GE, 0.5),
    ("triangle_leg_max", "длиннейшая сторона треугольника", 300, 270, CM, "want NKBA K3; min предп.",
     LE, 0.5),
    # ТВ и рабочее место
    ("tv_distance", "дистанция от глаз до ТВ в диагоналях, не ближе", 1.0, 1.2, DIAGONALS,
     "предп. (THX 40° ≈ 1,2 диаг.)"),
    ("tv_angle", "ТВ в стороне от оси взгляда", 30, 15, DEGREES, "предп.", LE, 0.5),
    ("desk_window", "окно не сбоку от сидящего: отклонение от 90°", None, 45, DEGREES,
     "предп. (свет сбоку, без бликов и слепящего окна перед экраном)", LE, 0.5),
)
RULES = tuple(Rule(*row) for row in RULE_TABLE)
RULES_BY_ID = frozen({rule.id: rule for rule in RULES})
RULEBOOK = ergo_judge.Rulebook(RULES_BY_ID, BUDGET)


def judge(measurements, waivers, structural=None):
    """measurements: [(правило, объект, значение[, cap])] → итог: ok, hard, soft (с обоснованием или без),
    struct (из-за несущего: structural_waivers или проход не шире cap), score.
    cap — лучшее значение, которое пускают несущие стены (rpkit/layout_passages.py: горлышко прохода между
    двумя несущими), structural — structural_waivers плана."""
    return ergo_judge.judge(measurements, waivers, structural or {}, RULEBOOK)


def table():
    """Markdown-таблица правил — для tools/reference/ERGONOMICS.md."""
    return ergo_table.table(RULES)


def report(name, verdict, verbose=False, waivers=False):
    """Отчёт check_layout по плану: заголовок и проблемы; waivers — и принятые уступки, verbose — и всё прочее."""
    return ergo_report.report(name, verdict, ergo_report.Detail(verbose=verbose, waivers=waivers), RULEBOOK)


if __name__ == "__main__":
    say(table())
