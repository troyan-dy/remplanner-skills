"""Все измерения эргономики плана: проходы, зоны перед предметами, двери, полотна, углы, кухня, ТВ, стол."""

from rpkit.layout_corners import measure_corners
from rpkit.layout_desk import measure_desk
from rpkit.layout_doors import measure_doors
from rpkit.layout_entry import entry_start
from rpkit.layout_fronts import measure_fronts
from rpkit.layout_kitchen import measure_kitchen
from rpkit.layout_leaves import measure_leaves
from rpkit.layout_model import LayoutPlan
from rpkit.layout_passages import measure_passages
from rpkit.layout_tv import measure_tv


def measure(plan, radius, start=None):
    """[(правило, объект, значение[, cap])] плана; radius — полуширина плеч (pass_any), start — старт маршрутов
    (по умолчанию от входной двери)."""
    layout = LayoutPlan(plan)
    start = start or entry_start(plan)
    passes, routes = measure_passages(layout, start, radius)
    return (
        passes
        + measure_fronts(layout)
        + measure_doors(layout)
        + measure_leaves(layout, routes)
        + measure_corners(layout, routes, radius)
        + measure_kitchen(layout)
        + measure_tv(layout)
        + measure_desk(layout)
    )
