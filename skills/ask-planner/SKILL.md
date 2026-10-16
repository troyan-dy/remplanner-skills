---
name: ask-planner
description: "Где я во флоу планировки и какой скил нужен сейчас. Карта всех скилов набора."
disable-model-invocation: true
---

# Какой скил нужен

Сначала посмотри на проект, потом советуй. Прежде чем сказать, что делает скил, или предложить пропустить шаг,
прочитай его `SKILL.md`: описания ниже — для ориентира.

## Где мы

Проверь по порядку; первая невыполненная строка — следующий шаг:

| Признак | Следующий шаг |
|---|---|
| нет `tools/` или блока «Планировка» в `CLAUDE.md`/`AGENTS.md` | `/setup-remplanner-skills` |
| нет `plan/as_is.json` | `/trace-bti` |
| в `REQUIREMENTS.md` нет жильцов и правил расстановки | `/interview-household` |
| нет ни одной серии в `concepts/` | `/plan-concepts` |
| последняя серия есть, а замечаний к ней в `REQUIREMENTS.md` нет | посмотреть снимки, затем `/plan-feedback` |
| в «Замечания — ещё не учтены» что-то есть | `/plan-concepts` |

## Основной флоу

1. **`/setup-remplanner-skills`** — один раз: проект, инструменты, каталог. Повторный запуск обновляет
   инструменты.
2. **`/trace-bti`** — план БТИ и замеры → `plan/as_is.json`, сверка в RemPlanner. Переделать чертёж можно
   в любой момент; серии после этого перегенерировать.
3. **`/interview-household`** — опрос жильцов → `REQUIREMENTS.md`, `rules.json`. Можно до чертежа, но с ним
   вопросы точнее.
4. **`/plan-concepts`** — серия концепций. Внутри агент сам вызывает `check-plan`, `critique-plan`,
   `remplanner-catalog`, `remplanner-export`, `remplanner-screenshots`.
5. **`/plan-feedback`** — замечания к серии → правила → бриф следующей серии. Затем снова `/plan-concepts`.

## Вне флоу

- **`/remplanner-primitive`** — нужного предмета, проёма или поля нет ни в инструментах, ни в каталоге.
- Служебные скилы можно позвать и руками: `/check-plan` (проходит ли план), `/remplanner-export` (нужен
  `.plan`), `/remplanner-screenshots` (картинки), `/remplanner-catalog` (найти предмет), `/critique-plan`
  (ещё круг критики).
