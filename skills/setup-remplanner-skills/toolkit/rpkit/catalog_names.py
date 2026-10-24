"""Имена каталога в плане: все ли известны и параметры предмета для .plan (rp_lib.check_names, rp_lib.spec)."""

import sys

from rpkit.catalog_checked import CATALOG, KITCHEN
from rpkit.catalog_store import entry, has_full
from rpkit.paths import FETCH

KITCHEN_RUN = "kitchen_run"
_MISSING = object()


def plan_names(plan):
    """[(где, имя)] — все имена каталога в плане: rp.name и модули kitchen_run (кроме сокращений KITCHEN)."""
    names = []
    for piece in plan.get("furniture", []):
        for spec_rp in _rp_list(piece):
            names.extend(_names_of(piece["id"], spec_rp))
    return names


def _rp_list(piece):
    attached = piece.get("rp")
    if not attached:
        return []
    return attached if isinstance(attached, list) else [attached]


def _names_of(piece_id, spec_rp):
    if spec_rp["name"] != KITCHEN_RUN:
        return [(f"furniture {piece_id}", spec_rp["name"])]
    where = f"furniture {piece_id}: модуль {KITCHEN_RUN}"
    return [(where, module) for module in spec_rp.get("modules", []) if module not in KITCHEN]


def check_names(plan, label):
    """Все предметы плана известны: без полного каталога — только CATALOG и confirmed.json с записью "catalog".
    Иначе SystemExit с перечнем предметов (id и rp.name) и командой fetch."""
    unknown = [
        (where, name) for where, name in plan_names(plan) if entry(name) is None
    ]
    if not unknown:
        return
    rows = "\n".join(
        f"  {where}: rp.name {name!r}" for where, name in unknown
    )
    if has_full():
        sys.exit(f"{label}: нет в каталоге RemPlanner:\n{rows}\nимена — python3 tools/rp_catalog.py find <слово>")
    sys.exit(
        f"{label}: предметы не из rp_lib.CATALOG и не из tools/catalog/confirmed.json, "
        f"а полного каталога нет:\n{rows}\nсоберите его: {FETCH} "
        "(или возьмите имена из CATALOG — python3 tools/blocks.py)",
    )


def spec(name):
    """Параметры предмета: из CATALOG (сверено с образцами), иначе из записи каталога (entry) —
    только группы plan.items."""
    checked = CATALOG.get(name)
    if checked is not None:
        return checked
    found = entry(name)
    if found is None:
        if has_full():
            sys.exit(f"предмет {name!r}: нет в каталоге RemPlanner")
        sys.exit(f"предмет {name!r}: нет сведений — нужен полный каталог ({FETCH})")
    if not found["in_items"]:
        raise ValueError(f"{name}: группа {found['group']} — схема в .plan не получена")
    fields = {
        "item_id": found["id"],
        "plan": found["plan"],
        "self_height": found["self_height"],
    }
    over_floor = found.get("over_floor", _MISSING)
    if over_floor is not _MISSING:
        fields["over_floor"] = over_floor
    if found.get("icon"):
        fields["on_show_decoration"] = 1
    fields["size"] = (found["width"], found["height"])
    return fields
