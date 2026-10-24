"""rules.json: настройки по умолчанию, типы правил с параметрами и чтение файла правил."""

from rpkit.frozen import frozen
from rpkit.jsonfile import read_json

ITEM_PATTERNS = "items"  # параметр правила: шаблоны имён каталога
ROOMS = "rooms"
DRAIN = "drain"
KITCHEN = "kitchen"
WHAT = "what"
EXCLUDE = "exclude_rooms"
MIN_FRONT = "min_front"
NOT_SET = "нужного предмета"

DEFAULTS = frozen({
    "as_is": "plan/as_is.json",
    "entry_radius": 250,  # предположение: от середины входной двери — в пределах прихожей
    DRAIN: {"point": None, "slope": 0.025},  # предположение: 2–3 см на метр (ориентир СП 30.13330, не сверен)
    ROOMS: {
        "wet": ["bath", "guest", "wc", KITCHEN, "laundry"],
        "bedroom": ["bed"],
        "walkin": ["walkin"],
        "toilet": ["wc"],
        "bathroom": ["bath"],
        "sanitary": ["bath", "wc", "shower"],
        KITCHEN: [KITCHEN],
        "loggia": ["loggia"],
    },
})
COMMON = frozenset(("id", "check", "text", "source", "enabled", "note"))
BEDS = ("^bed_(double|single|near_wall)", "bed_transformer", "^ottoman_bed")  # взрослые кровати каталога
TOILETS = ("^toilet(_with_frame|_embedded|_impulse)?$", "^corner_toilet$")  # без toilet_paper, toilet_brush…

# Параметры каждого типа и их значения по умолчанию (REQ — обязательный, None — не задан).
REQ = ...
TYPES = frozen({
    "near_entry": {ITEM_PATTERNS: REQ, WHAT: NOT_SET, "max_dist": None, MIN_FRONT: 0, "min_depth": 0, EXCLUDE: []},
    "bedroom_storage": {"beds": list(BEDS), ITEM_PATTERNS: ["ward"], "extra_rooms": ["walkin"], MIN_FRONT: 0},
    "drain_routes": {"wet_rooms": "wet", "toilet": list(TOILETS), "toilet_max": 100, "point": None, "slope": None},
    "window_full": {"window": REQ, "min_length": REQ, "waiver": None},
    "window_clear": {"window": REQ, "gap": 30, "max_height": 90},
    "items_in_rooms": {ITEM_PATTERNS: REQ, ROOMS: REQ},
    "behind_door": {ITEM_PATTERNS: REQ, "forbid_rooms": [], "need_door": True},
    "kitchen_straight": {
        ROOMS: KITCHEN,
        ITEM_PATTERNS: ["kitchen_run", "kitchen_box", "fridge", "built_in_fridge", "pencil_case", "worktop"],
    },
    "no_corner_join": {ITEM_PATTERNS: ["ward"], "tol": 5},
    "min_size": {ITEM_PATTERNS: REQ, "min_width": REQ, "measure": "long", "need": "any", EXCLUDE: [], WHAT: NOT_SET},
    "room_has": {ITEM_PATTERNS: REQ, ROOMS: None, "required": False},
})


_MISSING = object()


def _settings(raw):
    """Настройки rules.json поверх DEFAULTS."""
    cfg = dict(DEFAULTS)
    for key in ("as_is", "entry_radius"):
        given = raw.get(key, _MISSING)
        if given is not _MISSING:
            cfg[key] = given
    cfg[DRAIN] = _merged(DRAIN, raw)
    cfg[ROOMS] = _merged(ROOMS, raw)
    return cfg


def _merged(key, raw):
    """Словарь DEFAULTS[key], дополненный rules.json."""
    return dict(DEFAULTS[key], **raw.get(key, {}))


def _missing(defaults, rule):
    """Обязательные параметры (REQ), которых нет в правиле."""
    return [
        key for key, default in defaults.items()
        if default is REQ and rule.get(key) is None
    ]


class _RulesReader:
    """Правила с параметрами по умолчанию и ошибки в файле правил."""

    def __init__(self):
        self.rules = []
        self.bad = []

    def read(self, number, rule):
        """Правило №number (с 0): ошибки — в bad, проверяемое правило — в rules."""
        ordinal = number + 1
        rule_id = rule.get("id", f"правило №{ordinal}")
        kind = rule.get("check")
        if kind not in TYPES:
            known = ", ".join(TYPES)
            self.bad.append(f"{rule_id}: неизвестный тип check «{kind}» (есть: {known})")
        elif self._params_ok(rule_id, kind, rule):
            self.rules.append({**TYPES[kind], **rule, "id": rule_id})

    def _params_ok(self, rule_id, kind, rule):
        """Лишние параметры — ошибка, но правило проверяется; без обязательных — не проверяется."""
        defaults = TYPES[kind]
        extra = sorted(set(rule) - COMMON - set(defaults))
        if extra:
            self._problem(rule_id, kind, "нет параметров", extra)
        need = _missing(defaults, rule)
        if need:
            self._problem(rule_id, kind, "не заданы", need)
        return not need

    def _problem(self, rule_id, kind, text, keys):
        listed = ", ".join(keys)
        self.bad.append(f"{rule_id}: у {kind} {text} {listed}")


def load_rules(path):
    """rules.json → (настройки, правила с параметрами по умолчанию, ошибки в самом файле)."""
    raw = read_json(path)
    reader = _RulesReader()
    for number, rule in enumerate(raw.get("rules", [])):
        reader.read(number, rule)
    return _settings(raw), reader.rules, reader.bad
