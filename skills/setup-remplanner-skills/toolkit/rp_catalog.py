#!/usr/bin/env python3
"""rp_catalog.py — полный каталог предметов RemPlanner: сборка, поиск, справочник.

  python3 tools/rp_catalog.py fetch [<url|planner.tools___*.js>]  # скачать скрипт планировщика и собрать каталог
  python3 tools/rp_catalog.py build <planner.tools___*.js>   # → tools/catalog/remplanner_catalog.json + REMPLANNER_CATALOG.md
  python3 tools/rp_catalog.py find <слово> [<слово> ...]      # поиск по имени/названию/разделу
  python3 tools/rp_catalog.py show <name>                    # всё о предмете

Источники (как получить заново — tools/reference/REMPLANNER_V3_SCHEMA.md, «Полный каталог»):
  - window.global_tools из публичного https://remplanner.ru/files/js/v2/app/planner.tools___<ver>.js —
    параметры каждого инструмента (id, название, габарит, высота, over_floor, листы, привязка, подводки);
  - tools/reference/remplanner_catalog_menu.txt — дерево меню (раздел → группа → id), снято из DOM планировщика.
SVG-контуры RemPlanner в каталог не копируются: для .plan нужен только item_id, рисует RemPlanner сам.
"""

import http.cookiejar
import json
import os
import re
import sys
import tempfile
import urllib.parse
import urllib.request

import rp_lib

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)  # корень проекта — родитель tools/
REF = os.path.join(TOOLS, "reference")
CAT_DIR = os.path.join(TOOLS, "catalog")
MENU = os.path.join(REF, "remplanner_catalog_menu.txt")
JSON_OUT = os.path.join(CAT_DIR, "remplanner_catalog.json")
MD_OUT = os.path.join(CAT_DIR, "REMPLANNER_CATALOG.md")

SITE = "https://remplanner.ru"
TOOLS_RE = re.compile(r"planner\.tools___[0-9_]+\.js")
UA = "Mozilla/5.0 (rp_catalog.py)"

# Группы global_tools, которые живут в plan.items и проверены импортом (см. REMPLANNER_V3_SCHEMA.md).
ITEM_GROUPS = ("furniture", "santeh_furniture")

SHEETS = {
    "init": "Исходный план",
    "break_walls": "Демонтаж",
    "create_walls": "Перегородки",
    "furniture": "Мебель",
    "santeh": "Сантехника",
    "sockets": "Розетки",
    "cables": "Электрика",
    "light": "Освещение",
    "light_connections": "Выключатели",
    "warm_floor": "Тёплый пол",
    "conditioners": "Кондиционеры",
    "radiators": "Отопление",
    "waterplan": "Водоснабжение",
    "water": "Водоснабжение",
    "styazhka": "Стяжка",
    "shtukaturka": "Штукатурка",
    "isolation": "Изоляция",
    "hydroisolation": "Гидроизоляция",
    "ceiling": "Потолки",
    "walls": "Стены",
    "floor": "Полы",
    "ventilation": "Вентиляция",
    "projections": "Развёртки",
    "security": "Безопасность",
    "shield": "Электрощит",
    "ai": "Распознавание",
}

PIPES = {"water_pipe": "ХВС", "water_hot_pipe": "ГВС", "drainage_pipe": "канализация"}

# Назначение групп меню и правила применения. Ключ — «раздел / группа» без пометки PRO
# (пустая группа — «раздел / »). Это толкование по названиям и параметрам каталога, не текст RemPlanner.
NOTES = {
    "Гостиная и спальня / Диваны": "Сиденье гостиной/кухни. Спинкой к стене или спинкой к проходу при зонировании; перед диваном ≥ 50–60 см до журнального стола (предположение), до ТВ — по диагонали.",
    "Гостиная и спальня / Модульные диваны": "Секции, из которых собирается диван любой формы: ставить вплотную друг к другу в одну линию/угол.",
    "Гостиная и спальня / Кресла мягкие": "Одиночное сиденье для гостиной/спальни, у окна или в паре с диваном.",
    "Гостиная и спальня / Кресла для отдыха": "Кресла с откидной спинкой/подставкой: нужен запас позади или спереди на раскладку.",
    "Гостиная и спальня / Крупногабаритные кресла": "Большие лаунж-кресла — только в просторной гостиной.",
    "Гостиная и спальня / Кровати": "Спальное место, изголовьем к стене; проходы с боков и в ногах (правила пользователя — в требованиях проекта). Трансформеры — откидные кровати в шкафу.",
    "Гостиная и спальня / Стулья": "Стулья к обеденному/письменному столу; задвигаются под стол.",
    "Гостиная и спальня / Мягкие панели и изголовья": "Отделка стены за кроватью/диваном; навесные, глубина несколько см, ставить вплотную к стене.",
    "Гостиная и спальня / Комоды и тумбы": "Хранение высотой до ~70–80 см: прикроватные тумбы у изголовья, комоды и ТВ-тумбы у стены.",
    "Гостиная и спальня / Шкафы": "Высокое распашное хранение и шкафы-стенки (гостиная). Перед распашными дверцами нужен проход на открывание.",
    "Гостиная и спальня / Банкетки и пуфы": "Мелкие сиденья: в ногах кровати, в прихожей, у туалетного столика.",
    "Гостиная и спальня / Стеллажи и полки": "Открытое хранение; навесные полки — over_floor, напольные стеллажи — к стене или как перегородка зоны.",
    "Гостиная и спальня / Крупногабаритные стеллажи": "Декоративные стеллажи во всю стену или как разделитель зон.",
    "Гостиная и спальня / Журнальные столы": "Столик перед диваном.",
    "Гостиная и спальня / Консольные столы": "Узкие столики у стены или за диваном; подвесные — over_floor.",
    "Гостиная и спальня / ": "Прочее: косметический (туалетный) столик, придиванные и приставные столики, сундук, гамак, сиденье для подоконника.",
    "Кухня и столовая / Напольные шкафы": "Нижние модули кухни (глубина 60, высота 85 с учётом столешницы, тип table_top): в линию вдоль стены; модули со встроенной техникой — посудомойка, стиральная, духовка, СВЧ. Угловые — в стык двух линий.",
    "Кухня и столовая / Навесные шкафы": "Верхние модули кухни: over_floor ≈ 140+ см, глубина 30–35, над нижними модулями; над плитой — вытяжка вместо шкафа.",
    "Кухня и столовая / Шкафы-пеналы": "Колонны до потолка (≈ 212 см) на краю кухонной линии: встроенный холодильник, духовка/СВЧ/кофемашина, витрины.",
    "Кухня и столовая / Кухонные острова": "Отдельностоящий модуль со свесом для барных стульев; проход вокруг ≥ 90–100 см (предположение).",
    "Кухня и столовая / Мебельные элементы": "Отдельные фасады и щиты — добор и заглушки в кухонной линии.",
    "Кухня и столовая / Стулья": "Стулья к обеденному столу.",
    "Кухня и столовая / Обеденные столы": "Обеденная зона; вокруг стола место для отодвигания стульев.",
    "Кухня и столовая / Кухонные мойки": "Мойка (тип sink) — ставится поверх нижнего модуля/столешницы, over_floor 85; требует воды и канализации.",
    "Кухня и столовая / Барная мебель": "Барные стойки, консоли и столы, барные (≈ 75 см сиденье) и полубарные (≈ 65 см) стулья.",
    "Кухня и столовая / ": "Прочее: столешница `worktop` (over_floor 81, кладётся поверх нижних модулей, тянется на всю линию), откидной настенный стол, табурет, буфеты, кухонные диваны.",
    "Бытовая техника / Холодильники": "Отдельностоящие холодильники и морозильники; сзади нужен зазор на вентиляцию (инструкция изготовителя).",
    "Бытовая техника / Варочные панели": "Врезаются в столешницу над нижним модулем; электро- или газовые.",
    "Бытовая техника / Кухонные плиты": "Отдельностоящие плиты (60 см) в линии нижних модулей; настольные — на столешницу.",
    "Бытовая техника / Вытяжки": "Над плитой/варочной панелью, навесные; островные — над островом.",
    "Бытовая техника / Техника для кухни": "Встраиваемая и настольная техника: стиральная/посудомоечная машины (нужна вода), мелкая техника на столешницу.",
    "Бытовая техника / ТВ и мультимедиа": "Телевизор (на кронштейне — over_floor, на подставке, на стойке), ТВ-тумбы, акустика, проекторы и экраны.",
    "Гардероб и прихожая / Гардеробные шкафы": "Распашные гардеробы глубиной ~60 и антресоли; перед ними проход на открывание дверей.",
    "Гардероб и прихожая / Шкафы-купе": "Шкафы и двери-купе для ниш; дверям-купе не нужен проход на открывание — подходят для узких коридоров.",
    "Гардероб и прихожая / Открытые гардеробные": "Секции открытой гардеробной (полки, штанги, обувницы) — ставить в ряд в гардеробной/нише.",
    "Гардероб и прихожая / Угловые шкафы": "Угловые и законцовочные секции для соединения шкафов в угол.",
    "Гардероб и прихожая / Обувницы и тумбы": "Обувь в прихожей, узкие (≈ 25–45 см) — у стены у входа.",
    "Гардероб и прихожая / Прихожие и пеналы": "Готовые прихожие (вешалка, зеркало, тумба) и пеналы-зеркала.",
    "Гардероб и прихожая / Консольные столы": "Узкие столики у стены в прихожей.",
    "Гардероб и прихожая / Вешалки и крючки": "Верхняя одежда: настенные крючки (навесные) и напольные стойки.",
    "Гардероб и прихожая / Банкетки и пуфы": "Сиденье для обувания в прихожей.",
    "Мебель для детской / Кровати и диваны": "Детские кровати, кроватки, двухъярусные и кровати-чердаки (PRO).",
    "Мебель для детской / Столы и стулья": "Детские столы, парты, стульчики (PRO).",
    "Мебель для детской / Игрушечная мебель": "Игрушки и игровое оборудование детской (PRO).",
    "Кабинет и офис / Столы и стойки": "Рабочие и письменные столы, угловые столы, ресепшн и переговорные.",
    "Кабинет и офис / Кресла и стулья": "Рабочие кресла и стулья.",
    "Кабинет и офис / Шкафы, тумбы, полки": "Офисное хранение.",
    "Кабинет и офис / Офисная техника": "Компьютеры, принтеры, проекторы, часы (PRO).",
    "Кабинет и офис / Перегородки": "Офисные перегородки (PRO).",
    "Кабинет и офис / ": "Прочее: кулер, вешалка-стойка, маркерная доска, флипчарт, сейф, урна.",
    "Интерьер и декор / Цветы и растения": "Комнатные растения и вазы (PRO).",
    "Интерьер и декор / Зеркала": "Настенные (over_floor) и напольные зеркала, пеналы-зеркала.",
    "Интерьер и декор / Мебель для животных": "Лежанки, когтеточки, аквариумы и т. п. (PRO).",
    "Интерьер и декор / Шторы, жалюзи, ставни": "Текстиль и защита окон — ставить вдоль окна (PRO).",
    "Интерьер и декор / Музыкальные инструменты": "Пианино, гитары, барабаны и т. п. (PRO).",
    "Интерьер и декор / Фотооборудование": "Свет, фоны, штативы для фотостудии.",
    "Интерьер и декор / Манекены": "Манекены (PRO).",
    "Интерьер и декор / ": "Прочий декор (PRO): торшеры, экраны радиаторов, декоративная ширма, ёлка, глобус-бар.",
    "Мебель для детской / ": "Игрушки, игровые комплексы, манеж, пеленальный столик (PRO).",
    "Спортивный инвентарь / ": "Скамьи, турник, шведская стенка, стойки для гантелей, балетный станок, дартс — к стене, с зоной движения вокруг.",
    "Спортивный инвентарь / Тренажеры": "Тренажёры; вокруг нужна зона движения.",
    "Спортивный инвентарь / Инвентарь для бокса": "Груши, ринг.",
    "Спортивный инвентарь / Игровые столы": "Бильярд, теннис, шведские стенки, турники и др.",
    "Коттеджи и бани": "Частный дом: баня, камины, хамам, котельная, транспорт — для квартиры не нужно.",
    "Салоны красоты": "Коммерческое оборудование (PRO) — для квартиры не нужно.",
    "Торговое оборудование": "Коммерческое оборудование (PRO) — для квартиры не нужно.",
    "Рестораны и кафе": "Коммерческое оборудование (PRO) — для квартиры не нужно.",
    "Медицина": "Медицинское оборудование (PRO); «Поручни для инвалидов» — для доступного санузла.",
    "Пром. оборудование": "Мастерская: станки, гончарное, кузня — для квартиры не нужно.",
    "Автосервисы и шиномонтаж": "Автосервис (PRO) — для квартиры не нужно.",
    "Раковины и мойки / Тумбы с раковиной": "Раковина санузла с тумбой (напольной или подвесной); перед ней зона ≥ 70 см.",
    "Раковины и мойки / Подвесные раковины": "Раковина на стене без тумбы (over_floor); экономит пол, освобождает место под ней.",
    "Раковины и мойки / Накладные раковины": "Раковина поверх столешницы/комода (PRO).",
    "Раковины и мойки / Напольные раковины": "Раковины на пьедестале/напольные.",
    "Раковины и мойки / Кухонные мойки": "Кухонные мойки — те же, что в «Кухня и столовая».",
    "Мебель для ванной / ": "Хранение в санузле: пеналы, шкафы над стиральной машиной, комоды под раковину, зеркальные шкафы.",
    "Бытовая техника / ": "Без группы — две разные вещи. Лист «Мебель»: пылесосы, гладильная доска, отпариватель, сушилки для белья, увлажнитель, рециркулятор, обогреватель, швейная машинка. Лист «Сантехника»: стиральные и сушильные машины (в т. ч. сушилка над стиральной), сушильный шкаф, посудомойки, фильтр обратного осмоса — со своими выводами воды/канализации.",
    "Бытовая техника / Водонагреватели": "Бойлеры и проточные нагреватели, навесные; нужны ХВС и ГВС.",
    "Бытовая техника / Водоснабжение дома": "Насосы, фильтры, гидроаккумуляторы частного дома (PRO).",
    "Бытовая техника / Оборудование для котельной": "Котлы и бойлеры частного дома (PRO).",
    "Ванны / ": "Ванны разных материалов и форм; перед ванной зона ≥ 70 см, у отдельностоящей — подводка снизу.",
    "Унитазы и биде / ": "Унитазы (напольные, подвесные с инсталляцией), биде, писсуары; перед унитазом ≥ 60–70 см.",
    "Душевые кабины / Готовые кабины": "Кабины с поддоном — условно и для душа без поддона (shower_cabin нужного размера).",
    "Душевые кабины / Душевые поддоны": "Поддоны (PRO).",
    "Душевые кабины / Поддоны из плитки/мозаики": "Поддоны, выложенные плиткой (PRO).",
    "Душевые кабины / Душевые уголки": "Стеклянные ограждения душа (PRO).",
    "Душевые кабины / Душевые двери в нишу": "Стеклянные двери душевой ниши (PRO).",
    "Смесители и душ / ": "Смесители, душевые стойки, лейки, трапы — точки подводки воды.",
    "Полотенцесушители / ": "Водяные и электрические полотенцесушители, навесные (over_floor).",
    "Аксессуары / Зеркала": "Зеркала санузла (те же, что в «Интерьер и декор»).",
    "Аксессуары / Поручни для инвалидов": "Поручни для доступного санузла.",
    "Аксессуары / ": "Ревизионные люки (доступ к стоякам/счётчикам), полки и крючки для полотенец, держатели, корзина для белья, ершики, урна.",
    "Раковины и мойки / ": "Консоли с раковиной — подвесная (over_floor) и напольная.",
    "Душевые кабины / ": "Душевая перегородка, трап и лоток (PRO), откидное сиденье для душа.",
}


def parse_tools(js_path):
    src = open(js_path, encoding="utf-8").read()
    i = src.index("{", src.index("window.global_tools"))
    tools, _ = json.JSONDecoder().raw_decode(src, i)
    return tools


def parse_menu(path=MENU):
    """→ (roots {id: (title, pro, sheets)}, entries [(root_id, group, id, alias, desc)], pro_ids)
    Предметы из строки U (вне групп) получают группу ""; PRO — по классу is_pro предмета (строка P)."""
    roots, entries, cur, ung, pro_ids = {}, [], None, {}, set()
    lines = [x.rstrip("\n") for x in open(path, encoding="utf-8")]
    for line in lines:
        if line.startswith("U "):
            for chunk in line[2:].split():
                rid, ids = chunk.split(":")
                ung[int(rid)] = {int(x) for x in ids.split(",")}
        elif line.startswith("P "):
            pro_ids = {int(x) for x in line[2:].split(",")}
    for line in lines:
        if not line or line.startswith(("#", "U ", "P ", "RP ")):
            continue
        if line.startswith("R|"):
            _, rid, title, sheets = line.split("|", 3)
            pro = title.endswith("PRO")
            roots[int(rid)] = (title[:-3] if pro else title, pro, sheets.split(","))
        elif line.startswith("G|"):
            _, rid, grp = line.split("|", 2)
            pro = grp.endswith(" PRO")
            cur = (int(rid), grp[:-4] if pro else grp, pro)
        else:
            head, _, desc = line.partition("|")
            tid, _, alias = head.partition("=")
            rid, grp, _ = cur
            if int(tid) in ung.get(rid, ()):
                grp = ""
            entries.append((rid, grp, int(tid), alias or None, desc))
    return roots, entries, pro_ids


def build(js_path):
    tools = parse_tools(js_path)
    roots, entries, pro_ids = parse_menu()
    byid = {v["id"]: n for n, v in tools.items()}
    menu, desc, order = {}, {}, []
    for rid, grp, tid, alias, d in entries:
        name = alias if alias in tools else byid.get(tid)
        if not name:
            continue
        title, rpro, _ = roots[rid]
        pro = rpro or tid in pro_ids
        menu.setdefault(name, []).append([title, grp, pro])
        order.append((rid, grp, name, pro))
        if d:
            desc[name] = d
    # раздел-инструмент без подменю (радиаторы, щитки…)
    for rid, (title, rpro, _) in roots.items():
        name = byid.get(rid)
        if name and name not in menu:
            menu[name] = [[title, "", rpro]]
            order.append((rid, "", name, rpro))

    cat = {}
    for n, v in tools.items():
        e = {
            "id": v["id"],
            "title": v["title"],
            "group": v["group"],
            "plan": v["plan"],
            "width": v["width"],
            "height": v["height"],
            "self_height": v["self_height"],
        }
        if isinstance(v["over_floor"], dict):
            e["over_floor"] = v["over_floor"]
        if v["anchor"] != "free":
            e["anchor"] = v["anchor"]
        if v.get(
            "icon"
        ):  # → on_show_decoration: 1 (так делает RemPlanner при создании)
            e["icon"] = True
        for k in ("custom_type", "santeh_data", "subgroup", "from_ceiling"):
            if v.get(k):
                e[k] = v[k]
        if v.get("can_be_outside"):
            e["can_be_outside"] = True
        if v.get("width_label") == "length":
            e["width_is_length"] = True
        if n in menu:
            e["menu"] = menu[n]
            if all(m[2] for m in menu[n]):
                e["pro"] = True
        if n in desc:
            e["desc"] = desc[n]
        e["in_items"] = v["group"] in ITEM_GROUPS
        cat[n] = e
    os.makedirs(CAT_DIR, exist_ok=True)
    json.dump(
        {"source": os.path.basename(js_path), "items": cat},
        open(JSON_OUT, "w", encoding="utf-8"),
        ensure_ascii=False,
        indent=0,
        sort_keys=False,
    )
    write_md(cat, roots, order)
    n_items = sum(e["in_items"] for e in cat.values())
    print(
        f"{len(cat)} инструментов, из них предметов plan.items: {n_items} → {os.path.relpath(JSON_OUT, ROOT)}, {os.path.relpath(MD_OUT, ROOT)}"
    )


def load():
    if not os.path.exists(JSON_OUT):
        sys.exit(f"нет каталога {os.path.relpath(JSON_OUT, ROOT)} — запустите python3 tools/rp_catalog.py fetch")
    return json.load(open(JSON_OUT, encoding="utf-8"))["items"]


def _get(opener, url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    with opener.open(req, timeout=120) as r:
        return r.read()


def find_tools_url(opener):
    """Имя planner.tools___<ver>.js есть только в странице редактора. Публичная /planner/ без сессии —
    заставка «Нарисовать чертежи»; её кнопка отправляет форму POST /planner/create/ (create_trigger=1, значение
    ставит front.js), после чего /planner/ отдаёт редактор со списком скриптов. Это создаёт гостевой проект —
    то же, что нажать кнопку в браузере."""
    html = _get(opener, SITE + "/planner/").decode("utf-8", "replace")
    m = TOOLS_RE.search(html)
    if not m:
        form = urllib.parse.urlencode({"create_trigger": "1"}).encode()
        html = _get(opener, SITE + "/planner/create/", form).decode("utf-8", "replace")
        m = TOOLS_RE.search(html)
    if not m:
        sys.exit(
            "не нашёл planner.tools___<ver>.js на странице редактора. Откройте https://remplanner.ru/planner/ в "
            "браузере, найдите имя в performance.getEntriesByType('resource') и запустите "
            "python3 tools/rp_catalog.py fetch <имя или url>"
        )
    return f"{SITE}/files/js/v2/app/{m.group(0)}"


def fetch(arg=None):
    """Скачать скрипт инструментов планировщика (по умолчанию — актуальную версию с сайта) и собрать каталог.
    arg — путь к уже скачанному .js, полный url или имя planner.tools___<ver>.js."""
    if arg and os.path.exists(arg):
        return build(arg)
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    if arg:
        url = arg if arg.startswith("http") else f"{SITE}/files/js/v2/app/{os.path.basename(arg)}"
    else:
        url = find_tools_url(opener)
    print("скачиваю", url)
    data = _get(opener, url)
    if b"window.global_tools" not in data:
        sys.exit(f"{url}: в файле нет window.global_tools — формат скрипта сменился")
    os.makedirs(CAT_DIR, exist_ok=True)
    name = os.path.basename(urllib.parse.urlparse(url).path)
    with tempfile.TemporaryDirectory() as tmp:
        js = os.path.join(tmp, name)
        open(js, "wb").write(data)
        build(js)


def purpose(e):
    """Короткое «что это и как ставить» по параметрам каталога."""
    p = []
    of = e.get("over_floor")
    if of and of["value"]:
        p.append(f"низ на {of['value']} см от пола")
    if e.get("anchor") == "wall":
        p.append("к стене")
    if e.get("anchor") == "ceiling" or e.get("from_ceiling"):
        p.append("от потолка")
    ct = e.get("custom_type")
    if ct == "table_top":
        p.append("нижний модуль/столешница: на него ставят мойку и варочную панель")
    elif ct == "sink":
        p.append("врезается в столешницу")
    elif ct == "chair":
        p.append("стул, задвигается под стол")
    sd = e.get("santeh_data")
    if sd:
        pipes = ", ".join(PIPES.get(x, x) for x in sd.get("pipes", []))
        d = sd.get("drainage_pipe_diameter")
        p.append(f"подводка: {pipes}" + (f" Ø{d}" if d else ""))
    if e.get("can_be_outside"):
        p.append("можно вне помещения")
    if e.get("subgroup"):
        p.append("варианты: " + ", ".join(e["subgroup"]))
    return "; ".join(p)


def note_for(section, group):
    return NOTES.get(f"{section} / {group}") or NOTES.get(section, "")


def write_md(cat, roots, order):
    L = [
        "# Каталог предметов RemPlanner",
        "",
        "Генерируется `python3 tools/rp_catalog.py fetch` (или `build <planner.tools.js>`) — руками не править. "
        "Данные: `tools/catalog/remplanner_catalog.json`, поиск: `python3 tools/rp_catalog.py find <слово>`.",
        "",
        "Колонки: `name` — ключ для `rp_lib.item()`; Ш×Г — габарит в плане при `angle: 0` (ширина вдоль спинки, "
        "глубина), см; В — высота в 3D (`self_height`; 0 — RemPlanner берёт высоту модели сам, предположение); "
        "«Назначение» — по параметрам каталога. Описание группы — толкование по названиям (не текст RemPlanner); "
        "нормативы с пометкой «предположение» не проверены. PRO — в гостевом режиме меню не даёт поставить.",
        "",
        "Как предметы попадают в `.plan`: группы `furniture` и `santeh_furniture` — `plan.items` "
        f"(`rp_lib.item()`; импортом проверены {len(rp_lib.CATALOG)} предметов `rp_lib.CATALOG` и подтверждённые "
        "пользователем в `tools/catalog/confirmed.json`, остальные — по тем же правилам, "
        "см. REMPLANNER_V3_SCHEMA.md «Полный каталог»); остальные (розетки, свет, трубы, щит…) — "
        "схема в `.plan` не получена, `rp_lib.item()` их не ставит.",
        "",
    ]
    seen = set()
    by_sheet, rows = {}, {}
    for rid, (title, rpro, sheets) in roots.items():
        by_sheet.setdefault(sheets[0], []).append((rid, title, rpro))
    for rid, grp, n, pro in order:
        rows.setdefault(rid, {}).setdefault(grp, []).append((n, cat[n], pro))
    for sheet, secs in by_sheet.items():
        if sheet not in ("furniture", "santeh", "radiators"):
            continue
        L.append(f"## Лист «{SHEETS.get(sheet, sheet)}»")
        L.append("")
        for rid, title, rpro in secs:
            groups = rows.get(rid, {})
            if not any(e["in_items"] for g in groups.values() for _, e, _ in g):
                continue
            L.append(f"### {title}{' (PRO)' if rpro else ''}")
            L.append("")
            for grp, items in groups.items():
                if grp:
                    L.append(f"#### {grp}")
                    L.append("")
                nt = note_for(title, grp)
                if nt:
                    L += [nt, ""]
                L.append("| name | Название | Ш×Г | В | Назначение |")
                L.append("|---|---|---|---|---|")
                for n, e, pro in items:
                    seen.add(n)
                    L.append(
                        f"| `{n}` | {e['title']}{' PRO' if pro else ''} | {e['width']}×{e['height']} | "
                        f"{e['self_height']} | {purpose(e)} |"
                    )
                L.append("")
    rest = [
        (n, e)
        for n, e in cat.items()
        if e["in_items"] and n not in seen and not e.get("menu")
    ]
    if rest:
        L += [
            "## Вне меню",
            "",
            "Варианты, которые выбираются в свойствах предмета (`subgroup`), и предметы других листов "
            "(датчики, короба, радиаторы-инструменты).",
            "",
            "| name | Название | Ш×Г | В | Листы | Назначение |",
            "|---|---|---|---|---|---|",
        ]
        for n, e in rest:
            sh = ", ".join(SHEETS.get(k, k) for k in e["plan"])
            L.append(
                f"| `{n}` | {e['title']} | {e['width']}×{e['height']} | {e['self_height']} | {sh} | {purpose(e)} |"
            )
        L.append("")
    other = {}
    for n, e in cat.items():
        if not e["in_items"]:
            other.setdefault(e["group"], []).append(f"`{n}` {e['title']}")
    L += [
        "## Прочие инструменты (не plan.items, схема не получена)",
        "",
    ]
    for g, xs in sorted(other.items()):
        L.append(f"- **{g}** ({len(xs)}): " + "; ".join(xs))
    L.append("")
    open(MD_OUT, "w", encoding="utf-8").write("\n".join(L))


def find(words):
    cat = load()
    ws = [w.lower() for w in words]
    for n, e in cat.items():
        hay = " ".join(
            [n, e["title"]] + [" ".join(map(str, m[:2])) for m in e.get("menu", [])]
        ).lower()
        if all(w in hay for w in ws):
            m = " | ".join(
                f"{a}/{b}{' PRO' if p else ''}" for a, b, p in e.get("menu", [])
            )
            print(
                f"{n:40} {e['id']:5} {e['width']}×{e['height']}×{e['self_height']:<4} {e['title']}"
                f"{'' if e['in_items'] else '  [не items]'}  — {m}  {purpose(e)}"
            )


def show(name):
    e = load()[name]
    print(json.dumps(e, ensure_ascii=False, indent=1))
    print("назначение:", purpose(e))
    for sec, grp, _ in e.get("menu", []):
        nt = note_for(sec, grp)
        if nt:
            print(f"{sec} / {grp}: {nt}")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("fetch", "build", "find", "show"):
        sys.exit(__doc__)
    cmd, args = sys.argv[1], sys.argv[2:]
    {
        "fetch": lambda: fetch(args[0] if args else None),
        "build": lambda: build(args[0]),
        "find": lambda: find(args),
        "show": lambda: show(args[0]),
    }[cmd]()
