#!/bin/bash
# SessionStart для облачных сессий Claude Code: проверить Python и собрать каталог RemPlanner,
# чтобы selftest гонял и экспорт. Сторонних пакетов у инструментов нет — ставить нечего.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"
TOOLKIT=skills/setup-remplanner-skills/toolkit

python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' \
  || { echo "session-start: нужен Python 3.9+, а есть $(python3 --version 2>&1)" >&2; exit 1; }

# каталог не коммитим (CLAUDE.md); если сеть окружения не пускает на remplanner.ru,
# selftest всё равно проходит на catalog_core.json — поэтому неудача fetch не роняет сессию
if [ -n "$(find "$TOOLKIT" -name remplanner_catalog.json -print -quit)" ]; then
  echo "session-start: каталог RemPlanner уже собран"
elif python3 "$TOOLKIT/rp_catalog.py" fetch >/dev/null 2>&1; then
  echo "session-start: каталог RemPlanner собран"
else
  echo "session-start: каталог RemPlanner не скачался (нет доступа к remplanner.ru?) — selftest пойдёт на catalog_core.json"
fi
