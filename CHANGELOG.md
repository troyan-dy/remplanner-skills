# Changelog

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
