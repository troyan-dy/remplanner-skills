"""Короткое «что это и как ставить» о предмете по параметрам каталога (справочник, find, show)."""

from rpkit.catalog_notes import PIPES
from rpkit.frozen import frozen

CUSTOM_TYPES = frozen({
    "table_top": "нижний модуль/столешница: на него ставят мойку и варочную панель",
    "sink": "врезается в столешницу",
    "chair": "стул, задвигается под стол",
})


def purpose(record):
    """Назначение предмета: высота над полом, привязка, тип, подводки, варианты — через «; »."""
    notes = _placement(record)
    custom = CUSTOM_TYPES.get(record.get("custom_type"))
    if custom:
        notes.append(custom)
    santeh = record.get("santeh_data")
    if santeh:
        notes.append(_pipes(santeh))
    if record.get("can_be_outside"):
        notes.append("можно вне помещения")
    if record.get("subgroup"):
        variants = ", ".join(record["subgroup"])
        notes.append(f"варианты: {variants}")
    return "; ".join(notes)


def _placement(record):
    notes = []
    over_floor = record.get("over_floor")
    if over_floor and over_floor["value"]:
        notes.append(f"низ на {over_floor['value']} см от пола")
    anchor = record.get("anchor")
    if anchor == "wall":
        notes.append("к стене")
    if anchor == "ceiling" or record.get("from_ceiling"):
        notes.append("от потолка")
    return notes


def _pipes(santeh):
    names = (PIPES.get(pipe, pipe) for pipe in santeh.get("pipes", []))
    pipes = ", ".join(names)
    diameter = santeh.get("drainage_pipe_diameter")
    if diameter:
        return f"подводка: {pipes} Ø{diameter}"
    return f"подводка: {pipes}"
