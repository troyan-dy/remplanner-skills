#!/usr/bin/env python3
"""selftest.py — самопроверка инструментов: во временной папке разворачивает проект с примером
(example/as_is.py, example/concepts_run01.py, reference/rules.example.json), выполняет генераторы,
выгрузку и обе проверки. Итог — «selftest: ok» или первая упавшая команда с её выводом."""

import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))


def run(proj, *cmd, expect=None):
    r = subprocess.run([sys.executable, *cmd], cwd=proj, capture_output=True, text=True)
    out = r.stdout + r.stderr
    if r.returncode or (expect and expect not in out):
        sys.exit(f"selftest: НЕ ПРОХОДИТ — {' '.join(cmd)} (код {r.returncode})\n{out}")
    return out


def main():
    with tempfile.TemporaryDirectory(prefix="remplanner-selftest-") as proj:
        shutil.copytree(TOOLS, os.path.join(proj, "tools"), ignore=shutil.ignore_patterns("__pycache__"))
        os.makedirs(os.path.join(proj, "src"))
        for name in ("as_is.py", "concepts_run01.py"):
            shutil.copy(os.path.join(TOOLS, "example", name), os.path.join(proj, "src", name))
        shutil.copy(os.path.join(TOOLS, "reference", "rules.example.json"), os.path.join(proj, "rules.json"))
        run(proj, "src/as_is.py")
        run(proj, "src/concepts_run01.py")
        plans = ["plan/as_is.json", "concepts/run-01_2026-01-01/shower.json"]
        run(proj, "tools/remplanner_export.py", *plans)
        for p in plans:
            if not os.path.exists(os.path.join(proj, p[:-5] + ".plan")):
                sys.exit(f"selftest: НЕ ПРОХОДИТ — нет {p[:-5]}.plan")
        for check in ("tools/check_layout.py", "tools/check_rules.py"):
            out = run(proj, check, *plans)
            if "НЕ ПРОХОДИТ" in out:
                sys.exit(f"selftest: НЕ ПРОХОДИТ — {check}\n{out}")
        run(proj, "tools/blocks.py")
    print("selftest: ok")


if __name__ == "__main__":
    main()
