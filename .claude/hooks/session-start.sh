#!/bin/bash
# SessionStart для облачных сессий Claude Code: проверить Python, поставить линтер набора и собрать каталог
# RemPlanner, чтобы selftest гонял и экспорт. Инструментам сторонние пакеты не нужны; линтер
# (wemake-python-styleguide, requirements-dev.txt) — только для разработки набора и только на Python 3.10+.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"
TOOLKIT=skills/setup-remplanner-skills/toolkit

python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' \
  || { echo "session-start: нужен Python 3.9+, а есть $(python3 --version 2>&1)" >&2; exit 1; }

# линтер: на Python < 3.10 его нет, а неудача установки (нет сети) не роняет сессию
if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
  echo "session-start: $(python3 --version 2>&1) — wemake-python-styleguide требует 3.10+, линтер пропущен"
elif python3 -c 'import wemake_python_styleguide' 2>/dev/null; then
  echo "session-start: линтер уже стоит — python3 -m flake8"
elif python3 -m pip install -q -r requirements-dev.txt >/dev/null 2>&1 \
  || python3 -m pip install -q --user -r requirements-dev.txt >/dev/null 2>&1; then
  echo "session-start: линтер поставлен — python3 -m flake8"
else
  echo "session-start: wemake-python-styleguide не поставился (нет доступа к PyPI?) — линтер недоступен"
fi

# каталог не коммитим (CLAUDE.md); если сеть окружения не пускает на remplanner.ru,
# selftest всё равно проходит на catalog_core.json — поэтому неудача fetch не роняет сессию
if [ -n "$(find "$TOOLKIT" -name remplanner_catalog.json -print -quit)" ]; then
  echo "session-start: каталог RemPlanner уже собран"
elif python3 "$TOOLKIT/rp_catalog.py" fetch >/dev/null 2>&1; then
  echo "session-start: каталог RemPlanner собран"
else
  echo "session-start: каталог RemPlanner не скачался (нет доступа к remplanner.ru?) — selftest пойдёт на catalog_core.json"
fi
