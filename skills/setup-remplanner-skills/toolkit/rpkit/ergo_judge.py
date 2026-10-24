"""Итог проверки эргономики (ergonomics.judge): уровни находок, уступки с обоснованием и без, бюджет."""

import functools
import operator
from typing import NamedTuple

OK = "ok"
SOFT = "soft"
HARD = "hard"
STRUCT = "struct"  # уступка из-за несущего: бюджет не тратит
ROWS = "rows"
UNJUST = "unjust"
LISTS = (ROWS, HARD, SOFT, UNJUST, STRUCT)  # списки итога в порядке ключей


class Rulebook(NamedTuple):
    """Правила по id и бюджет уступок."""

    rules: dict
    budget: float


def waiver_matches(key, rule_id, obj_name):
    """Ключ уступки «правило» или «правило:начало имени объекта» подходит находке."""
    key_rule, _, prefix = key.partition(":")
    return key_rule == rule_id and (not prefix or obj_name.startswith(prefix))


def find_waiver(waivers, rule_id, obj_name):
    """Обоснование первой подходящей уступки или None."""
    for key, why in waivers.items():
        if waiver_matches(key, rule_id, obj_name):
            return why
    return None


class _Judge:
    """Раскладывает находки по спискам итога и считает баллы уступок."""

    def __init__(self, rulebook, waivers, structural):
        self.rules = rulebook.rules
        self.waivers = waivers
        self.structural = structural
        self.lists = {name: [] for name in LISTS}

    def add(self, measurement):
        """Находка (правило, объект, значение[, cap]) → её цена в бюджете."""
        head = tuple(measurement[:3])
        cap = measurement[3] if len(measurement) > 3 else None
        rule = self.rules[head[0]]
        level = rule.level(head[2])
        if level == SOFT:
            return self._soft(rule, head, cap)
        if level == HARD:
            hard_cap = self._hard_cap(rule, cap)
            self.lists[HARD].append((*head, hard_cap))
        self.lists[ROWS].append((*head, level, None))
        return float(0)

    def used(self):
        """Ключи уступок, которые пригодились хотя бы одной находке между want и min."""
        soft_rows = [row for row in self.lists[ROWS] if row[3] == SOFT]
        return {
            key for key in self.waivers
            if any(
                waiver_matches(key, row[0], row[1]) for row in soft_rows
            )
        }

    def _soft(self, rule, head, cap):
        rule_id, obj_name, measured = head
        reason = find_waiver(self.structural, rule_id, obj_name)
        if reason is None and self._within_cap(rule, measured, cap):
            reason = self._bottleneck(cap, rule.unit)
        if reason is not None:
            self.lists[STRUCT].append((*head, reason))
            self.lists[ROWS].append((*head, STRUCT, None))
            return float(0)
        why = find_waiver(self.waivers, rule_id, obj_name)
        self.lists[SOFT if why else UNJUST].append((*head, why))
        self.lists[ROWS].append((*head, SOFT, why))
        return rule.cost(measured, cap)

    def _within_cap(self, rule, measured, cap):
        """Уступка ничего не стоит, потому что шире горлышка между несущими не сделать."""
        return cap is not None and rule.cost(measured, cap) == 0

    def _bottleneck(self, cap, unit):
        """Обоснование уступки, когда проход не шире горлышка между двумя несущими."""
        return f"горлышко прохода между двумя несущими стенами — {cap} {unit}"

    def _hard_cap(self, rule, cap):
        """cap остаётся в находке ниже минимума, только если и горлышко между несущими ниже минимума."""
        if cap is not None and cap >= 0 and rule.level(cap) == HARD:
            return cap
        return None


def judge(measurements, waivers, structural, rulebook):
    """Итог по находкам — см. ergonomics.judge."""
    judgement = _Judge(rulebook, waivers, structural)
    # по порядку, как сложение в цикле (sum() с 3.12 складывает float с компенсацией)
    costs = map(judgement.add, measurements)
    score = functools.reduce(operator.add, costs, float(0))
    lists = judgement.lists
    return {
        **lists,
        "score": round(score, 2),
        "unused": sorted(set(waivers) - judgement.used()),
        "ok": not lists[HARD] and not lists[UNJUST] and score <= rulebook.budget,
    }
