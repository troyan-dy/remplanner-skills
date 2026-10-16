# Правила жильцов: rules.json для check_rules.py

`python3 tools/check_rules.py [-v] [--rules <path>] <plan.json ...>` читает `rules.json` в корне проекта
(родитель `tools/`). Стартовый набор — `tools/reference/rules.example.json`. Эргономика (проходы, зоны перед
мебелью) — не здесь, а в `tools/check_layout.py` и `ERGONOMICS.md`.

## Файл

| ключ | что | по умолчанию |
|---|---|---|
| `rooms` | роли комнат: роль → префиксы `rooms[].id` | `wet` bath/guest/wc/kitchen/laundry, `bedroom` bed, `walkin` walkin, `toilet` wc, `bathroom` bath, `sanitary` bath/wc/shower, `kitchen` kitchen, `loggia` loggia |
| `entry_radius` | «у входа»: см от середины входной двери | 250 |
| `drain` | `point` [x, y] — точка подключения канализации; `slope` — уклон | `null`, 0.025 |
| `as_is` | план «как есть» от корня проекта | `plan/as_is.json` |
| `rules` | список правил | — |

Правило: `{"id": "п. 12", "check": "<тип>", ...параметры, "text": "формулировка", "source": "…",
"enabled": false}`. Сообщение о нарушении начинается с `id`. Несколько правил могут иметь один `id`.
Неизвестный тип, лишний (опечатка) или пропущенный обязательный параметр — `check_rules` не запускается (код 2).

- **Предметы** (`items`, `beds`, `toilet`) — регулярные выражения по имени каталога `rp.name` (`re.search`):
  `"ward"` — любой шкаф с ward в имени, `"^tv$"` — ровно `tv`, `"^bench"` — начинается с bench. Имена —
  `python3 tools/rp_catalog.py find <слово>`.
- **Комнаты** (`rooms`, `exclude_rooms`, `forbid_rooms`, `extra_rooms`, `wet_rooms`) — роли из `rooms`; строка,
  которой нет среди ролей, сама считается префиксом id. Предмет в комнате — его центр внутри `rooms[].rect`
  (комнаты без `rect` не учитываются).
- **Вход** — дверь с `"entry": true`, иначе дверь с id `door-entry`.
- **Ширина** предмета: `front` — фасад по спинке `back`, `long` — большая сторона `rect`.

## Типы

| check | что проверяет | параметры (по умолчанию) |
|---|---|---|
| `near_entry` | у входа (не дальше `max_dist`) есть предмет из `items`, при размерах — фасад ≥ `min_front` и глубина ≥ `min_depth` | `items`*, `what` (кого нет, род. п.), `max_dist` (= `entry_radius`), `min_front` 0, `min_depth` 0, `exclude_rooms` [] |
| `bedroom_storage` | в каждой комнате с кроватью `beds` (с гардеробными `extra_rooms`) есть шкаф `items`; при `min_front` — сумма фасадов ≥ него | `beds` (взрослые кровати), `items` ["ward"], `extra_rooms` ["walkin"], `min_front` 0 |
| `drain_routes` | от точки подключения до каждого прибора с канализацией (по каталогу: `santeh_data` с drainage_pipe; в `kitchen_run` — sink, washer, dishwasher) есть трасса: по полу комнат `wet_rooms` и сквозь перегородки, не под дверями; унитаз ≤ `toilet_max`. `-v` — длина и перепад | `wet_rooms` "wet", `toilet` (унитазы), `toilet_max` 100, `point`, `slope` (из `drain`) |
| `window_full` | окно `window` не заложено: большая сторона ≥ `min_length`, иначе нужен непустой ключ `waiver` в JSON концепции | `window`*, `min_length`*, `waiver` |
| `window_clear` | перед окном (ближе `gap`) нет мебели выше `max_height`, стоящей на полу | `window`*, `gap` 30, `max_height` 90 |
| `items_in_rooms` | каждый предмет `items` — в комнате ролей `rooms` | `items`*, `rooms`* |
| `behind_door` | каждый предмет `items` — в комнате с `rect` и настоящей дверью (не `doorway`), не в `forbid_rooms` | `items`*, `forbid_rooms` [], `need_door` true |
| `kitchen_straight` | в кухне все предметы `items` спинками по одной оси (прямая или два параллельных ряда) | `rooms` "kitchen", `items` (модули, пеналы, холодильники) |
| `no_corner_join` | предметы `items` не стыкуются под прямым углом (зазор ≤ `tol`) | `items` ["ward"], `tol` 5 |
| `min_size` | `need: any` — есть хоть один `items` шириной ≥ `min_width`; `each` — каждый такой; не в `exclude_rooms` | `items`*, `min_width`*, `measure` long/front, `need` any/each, `exclude_rooms` [], `what` |
| `room_has` | в комнате ролей `rooms` есть всё из `items` (`{"подпись": [шаблоны]}` или `{"подпись": {"items": [...], "sizes": [[a, b], …], "modules": true}}`). `rooms` — список ролей по порядку: берётся первая, у которой есть комнаты; без `rooms` — весь план. Комнаты нет: при `required` — нарушение, иначе не проверено | `items`*, `rooms`, `required` false |

\* — обязательный. `sizes` — подходит предмет, у которого меньшая сторона ≥ a и большая ≥ b хотя бы для одной
пары; `modules` — искать ещё среди модулей `kitchen_run`.

Точка подключения (`drain_routes`): `drain.point` в rules.json или в правиле; иначе `fixed_elements` с
`"kind": "drain"` в плане «как есть» (`point` или центр `rect`); иначе унитаз «как есть» — 10 см внутрь от
середины его спинки. Трасса стартует со всех допустимых клеток в 20 см от точки. `-v` печатает точку и откуда
она взята.

## Из фразы в правило

| сказали | правило |
|---|---|
| «шкаф у входа не меньше метра» | `{"id": "п. 7", "check": "near_entry", "items": ["ward", "coat_rack_unit"], "min_front": 100, "min_depth": 60, "what": "шкафа"}` (глубину 60 уточнить — предположение) |
| «надо где-то сесть, чтобы обуться» | `near_entry`, `items` ["pouf", "^bench", "banquet"], `what` "сиденья" |
| «в спальне шкафов метра три» | `bedroom_storage`, `min_front` 300 |
| «стиралку — только в ванную» | `items_in_rooms`, `items` ["^washing_machine"], `rooms` ["bathroom"] |
| «работаю из дома, нужна дверь» | `behind_door`, `items` ["writingdesk", "work_table", "^desk"], `forbid_rooms` ["bedroom"] |
| «стол не меньше 160» | `min_size`, `items` — столы, `min_width` 160, `exclude_rooms` ["loggia"] |
| «телевизор 65 дюймов» | `min_size`, `items` ["^tv$"], `need` "each", `min_width` 144 (16:9: 0,872 × 165 см) |
| «душ, а не ванна, от 100×100» | `room_has`, `rooms` ["bathroom"], `items` {"душ от 100×100": {"items": ["shower_cabin", "shower_pan"], "sizes": [[100, 100]]}} |
| «отдельный туалет с раковиной» | `room_has`, `rooms` ["toilet"], `required` true, `items` {"унитаз": […], "раковина": ["sink"]} |
| «кошке — лоток в туалете, миски где угодно» | `room_has` `rooms` ["toilet", "bathroom"] с {"лоток": ["cat_litter"]}; `room_has` без `rooms` с {"миски": ["animal_feeder"]} |
| «посудомойка обязательно» | `room_has` без `rooms`, {"посудомойка": {"items": ["dishwasher"], "modules": true}} |
| «кухня в линию, без углов» | `kitchen_straight`; «шкафы без угловых стыков» — `no_corner_join` |
| «балкон не закладывать» | `window_full` с id окна и длиной из `plan/as_is.json`, `waiver` "loggia_brick"; `window_clear` — мебель у стекла |

Порядок: правило с номером п. N — в `REQUIREMENTS.md`, проверяемое — ещё и в `rules.json` с тем же `id`.
Новые роли комнат — в `rooms` (например `"office": ["study", "office"]`). Числа без источника — с пометкой
«предположение» в `source`. Если подходящего типа нет, правило проверяют вручную (пометка в `REQUIREMENTS.md`).
После правки — `python3 tools/check_rules.py -v plan/as_is.json`: у каждого правила должна быть строка
(`✗` или `·`); если правило молчит, значит не нашлось ни одного подходящего предмета или комнаты — проверьте
шаблоны и роли.
