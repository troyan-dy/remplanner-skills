#!/usr/bin/env python3
"""selftest.py — самопроверка инструментов: во временной папке разворачивает проект с примером
(example/as_is.py, example/concepts_run01.py, reference/rules.example.json), выполняет генераторы,
выгрузку и обе проверки. Итог — «selftest: ok» или первая упавшая команда с её выводом."""

import os
import shutil
import subprocess
import sys
import tempfile

from rpkit.console import say

TOOLS = os.path.dirname(os.path.abspath(__file__))
EXAMPLES = ("as_is.py", "concepts_run01.py")
PLANS = ("plan/as_is.json", "concepts/run-01_2026-01-01/shower.json")
CHECKS = ("tools/check_layout.py", "tools/check_rules.py")
FAILED = "selftest: НЕ ПРОХОДИТ"


def run(proj, *cmd, expect=None):
    """Запускает инструмент в папке проекта; при ошибке — выход с его выводом."""
    completed = subprocess.run(
        [sys.executable, *cmd], cwd=proj, capture_output=True, text=True, check=False,
    )
    out = completed.stdout + completed.stderr
    if completed.returncode or (expect and expect not in out):
        command = " ".join(cmd)
        sys.exit(f"{FAILED} — {command} (код {completed.returncode})\n{out}")
    return out


def deploy(proj):
    """Копирует инструменты, генераторы примера и правила в проект."""
    skip_cache = shutil.ignore_patterns("__pycache__")
    shutil.copytree(TOOLS, os.path.join(proj, "tools"), ignore=skip_cache)
    src = os.path.join(proj, "src")
    os.makedirs(src)
    for name in EXAMPLES:
        example = os.path.join(TOOLS, "example", name)
        shutil.copy(example, os.path.join(src, name))
    rules = os.path.join(TOOLS, "reference", "rules.example.json")
    shutil.copy(rules, os.path.join(proj, "rules.json"))


def check_exports(proj):
    """Выгрузка обоих планов и наличие .plan рядом с JSON."""
    run(proj, "tools/remplanner_export.py", *PLANS)
    for plan in PLANS:
        stem = plan[:-len(".json")]
        if not os.path.exists(os.path.join(proj, f"{stem}.plan")):
            sys.exit(f"{FAILED} — нет {stem}.plan")


def main():
    """Весь прогон во временной папке."""
    with tempfile.TemporaryDirectory(prefix="remplanner-selftest-") as proj:
        deploy(proj)
        for name in EXAMPLES:
            run(proj, f"src/{name}")
        check_exports(proj)
        for check in CHECKS:
            out = run(proj, check, *PLANS)
            if "НЕ ПРОХОДИТ" in out:
                sys.exit(f"{FAILED} — {check}\n{out}")
        run(proj, "tools/blocks.py")
    say("selftest: ok")


if __name__ == "__main__":
    main()
