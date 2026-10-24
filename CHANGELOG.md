# Changelog

## 0.1.1 — 2026-10-24

Для пользователей скилов ничего не изменилось — правки только для разработки набора.

- CI гоняет selftest на Python 3.9 и 3.15 (actions v7).
- SessionStart-хук для облачных сессий Claude Code: проверяет Python и собирает каталог RemPlanner.
- Линтер wemake-python-styleguide для разработки набора: конфиг в `setup.cfg`, `requirements-dev.txt`, отдельная
  задача CI на Python 3.15, установка в SessionStart-хуке (на Python 3.10+). Инструментам сторонние пакеты
  по-прежнему не нужны.
- Код инструментов приведён к линтеру без нарушений: внутренности — в пакете `tools/rpkit/`, в `tools/` — CLI и
  библиотеки `planlib`, `rp_lib`, `ergonomics` с прежними именами и сигнатурами. Вывод, `.plan`, каталог, коды
  выхода и команды прежние — сверено побайтно на наборе планов на Python 3.9, 3.13 и 3.15.
- Проверенные предметы `rp_lib.CATALOG` — данными в `tools/reference/catalog_checked.json` с источником по группе;
  константы `rp_lib.CATALOG`, `KITCHEN`, `PC_SHIFT` и `ergonomics.RULES_BY_ID` (было `ergonomics.R`) — только
  для чтения.

## 0.1.0 — 2026-10-16

Первый релиз.

- Скилы флоу: `setup-remplanner-skills`, `trace-bti`, `interview-household`, `plan-concepts`, `plan-feedback`,
  `remplanner-primitive`, `ask-planner`.
- Служебные скилы: `check-plan`, `critique-plan`, `remplanner-export`, `remplanner-catalog`,
  `remplanner-screenshots`.
- Инструменты (`toolkit` → `tools/` проекта): экспорт в `.plan`, проверки `check_layout` и `check_rules`
  (11 типов правил), `planlib` для генераторов, сборка каталога RemPlanner, `PLAN_FORMAT.md` и `RULES.md`.
- Работа без полного каталога: ядро `catalog_core.json` и `rp_catalog confirm`; проверки по разделам каталога
  вместо зашитых имён; уступки из-за несущих (`structural_waivers`) не тратят бюджет; створка двери против прохода
  и фасадов.
- Пример выдуманной однокомнатной квартиры и `selftest.py`; CI гоняет selftest на Python 3.9 и 3.13.
- README: флоу, структура проекта квартиры, картинка примера; манифест плагина и marketplace.
