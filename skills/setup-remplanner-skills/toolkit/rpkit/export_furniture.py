"""Мебель выгрузки: предметы с полем rp и линия кухни kitchen_run (модули + мойка + столешница)."""

from rpkit.catalog_checked import KITCHEN, KITCHEN_MODULE_CM
from rpkit.catalog_store import catalog_info
from rpkit.rp_items import make_item

EPS = 1e-6
NAME = "name"
BACK = "back"
ALONG_X = ("up", "down")  # спинка вверх или вниз — фасад и линия кухни вдоль x
OWN_KEYS = (NAME, BACK, "angle")  # поля rp, которые не передаются в предмет как есть
SINK_ALONG_CM = 45  # мойка в модуле sink: вдоль линии
SINK_ACROSS_CM = 40  # и поперёк
KITCHEN_RUN = "kitchen_run"


def furniture_items(plan, frame):
    """Предметы .plan по мебели с полем rp (rp — объект или список)."""
    pieces = []
    for furniture in plan["furniture"]:
        attached = furniture.get("rp")
        if not attached:
            continue
        for spec_rp in attached if isinstance(attached, list) else [attached]:
            pieces.extend(make_items(furniture["rect"], spec_rp, frame))
    return pieces


def make_items(rect, spec_rp, frame):
    """Предметы .plan по прямоугольнику мебели и её rp."""
    back = spec_rp[BACK]
    if spec_rp[NAME] == KITCHEN_RUN:
        return kitchen_run(rect, back, spec_rp["modules"], frame)
    placement = _placement(rect, back, frame)
    # точный угол (стулья под 45°); back — ближайшая сторона для проверок
    angle = spec_rp.get("angle", frame.angle_of(back))
    extra = _extra(spec_rp)
    return [make_item(spec_rp[NAME], *placement, angle, **extra)]


def _placement(rect, back, frame):
    """(cx, cy, ширина, глубина) предмета в RemPlanner: центр габарита и габарит при angle 0."""
    x_cm, y_cm, width, height = rect
    center = frame.to_rp(
        x_cm + width / 2, y_cm + height / 2,
    )
    if back in ALONG_X:
        return (*center, width, height)
    return (*center, height, width)


def _extra(spec_rp):
    """Поля rp сверх name/back/angle — в предмет как есть (over_floor, self_height…)."""
    return {key: field for key, field in spec_rp.items() if key not in OWN_KEYS}


class _KitchenLine:
    """Линия кухни: прямоугольник линии, спинка; копит предметы, участки столешницы и длину модулей."""

    def __init__(self, rect, back, frame):
        self.rect = rect
        self.back = back
        self.frame = frame
        self.pieces = []
        self.tops = []
        self.position = 0

    @property
    def along_x(self):
        """Линия идёт вдоль x."""
        return self.back in ALONG_X

    def length(self):
        """Длина линии."""
        return self.rect[2] if self.along_x else self.rect[3]

    def piece(self, start, width):
        """Прямоугольник участка линии от start шириной width."""
        x_cm, y_cm, line_width, line_height = self.rect
        if self.along_x:
            return [x_cm + start, y_cm, width, line_height]
        return [x_cm, y_cm + start, line_width, width]

    def add(self, rect, name):
        """Предмет name в прямоугольнике rect со спинкой линии."""
        spec_rp = {NAME: name, BACK: self.back}
        self.pieces.extend(make_items(rect, spec_rp, self.frame))

    def add_module(self, module):
        """Модуль линии (и мойка, если это sink) — следом за предыдущими."""
        name = KITCHEN.get(module, module)
        found = catalog_info(name)
        width = KITCHEN_MODULE_CM if module in KITCHEN else found["width"]
        module_rect = self.piece(self.position, width)
        self.add(module_rect, name)
        shorthand_top = module in KITCHEN and module != "stove"
        if shorthand_top or found.get("custom_type") == "table_top":
            self.tops.append((self.position, self.position + width))
        if module == "sink":
            self.add(_sink_rect(module_rect, self.along_x), "kitchen_sink")
        self.position += width

    def worktop_runs(self):
        """Участки столешницы (с хвостом до конца линии), соседние — одним куском."""
        if self.position < self.length():
            self.tops.append((self.position, self.length()))
        runs = []
        for start, end in self.tops:
            last = runs[-1] if runs else None
            if last and abs(last[1] - start) < EPS:
                last[1] = end
            else:
                runs.append([start, end])
        return runs


def _sink_rect(module_rect, along_x):
    """Мойка по центру модуля sink."""
    if along_x:
        size = (SINK_ALONG_CM, SINK_ACROSS_CM)
    else:
        size = (SINK_ACROSS_CM, SINK_ALONG_CM)
    left, top, width, height = module_rect
    return [
        left + (width - size[0]) / 2,
        top + (height - size[1]) / 2,
        *size,
    ]


def kitchen_run(rect, back, modules, frame):
    """Линия кухни вдоль стены + столешница поверх всего, кроме плиты. Модуль — сокращение
    (sink|box|stove|washer|dishwasher, по 60 см) или любое имя из полного каталога (ширина — из каталога,
    столешница — если custom_type table_top, напр. kitchen_box_oven, kitchen_box_corner_90)."""
    line = _KitchenLine(rect, back, frame)
    for module in modules:
        line.add_module(module)
    for start, end in line.worktop_runs():
        line.add(line.piece(start, end - start), "worktop")
    return line.pieces
