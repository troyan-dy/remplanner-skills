"""Проверка планов правилами rules.json: итог по плану и разбор аргументов check_rules.py."""

import os

from rpkit.catalog_names import check_names
from rpkit.console import complain, say
from rpkit.jsonfile import read_json
from rpkit.paths import ROOT
from rpkit.rules_checks import CHECKS
from rpkit.rules_config import load_rules
from rpkit.rules_context import Ctx

FAILED = "  ✗ "
BAD_INPUT = 2  # код выхода: нет файла правил или в нём ошибки


def check(path, cfg, rules):
    """Нарушения и пройденные (и выключенные) правила для плана path."""
    plan = read_json(path)
    check_names(plan, path)
    ctx = Ctx(plan, cfg)
    errs, passed = [], []
    for rule in rules:
        _apply(ctx, rule, (errs, passed))
    return errs, passed


def _apply(ctx, rule, lists):
    """Правило к плану: сообщения — в lists = (нарушения, пройденные)."""
    errs, passed = lists
    if rule.get("enabled", True) is False:
        passed.append(f"{rule['id']}: выключено")
        return
    for outcome in CHECKS[rule["check"]](ctx, rule):
        target = passed if outcome[0] else errs
        target.append(f"{rule['id']}: {outcome[1]}")


def _rules_path(args):
    """(путь к rules.json, аргументы без --rules <path>)."""
    if "--rules" not in args:
        return os.path.join(ROOT, "rules.json"), args
    index = args.index("--rules")
    rules_path = args[index + 1]
    return rules_path, args[:index] + args[index + 2:]


def _report(path, cfg, rules, verbose):
    """Итог по плану; → есть ли нарушения."""
    errs, passed = check(path, cfg, rules)
    status = "НЕ ПРОХОДИТ" if errs else "ok"
    say(f"{path}: {status}")
    for error in errs:
        say(f"{FAILED}{error}")
    if verbose:
        for line in passed:
            say(f"  · {line}")
    return bool(errs)


def _load(rules_path):
    """(настройки, правила) или None, если файла нет или в нём ошибки (они — в stderr)."""
    if not os.path.exists(rules_path):
        shown = os.path.normpath(rules_path)
        complain(
            f"нет {shown}: скопируйте tools/reference/rules.example.json в rules.json "
            "проекта или укажите --rules <path>",
        )
        return None
    cfg, rules, bad = load_rules(rules_path)
    if bad:
        complain(f"{rules_path}: ошибки в правилах")
        for problem in bad:
            complain(f"{FAILED}{problem}")
        return None
    return cfg, rules


def main(argv):
    """check_rules.py [-v] [--rules <rules.json>] <plan.json ...> → код выхода."""
    rules_path, plans = _rules_path([arg for arg in argv if arg != "-v"])
    loaded = _load(rules_path)
    if loaded is None:
        return BAD_INPUT
    code = 0
    for path in plans:
        code |= _report(path, *loaded, "-v" in argv)
    return code
