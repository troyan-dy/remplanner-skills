"""Правило drain_routes: трасса канализации от точки подключения до каждого прибора."""

from rpkit.rules_drain_point import drain_point
from rpkit.rules_items import has
from rpkit.rules_routes import routes

CM_IN_M = 100


def _drain_settings(ctx, rule):
    """drain из rules.json с путём к плану «как есть» и точкой из правила, если она задана."""
    settings = dict(ctx.cfg["drain"], as_is=ctx.cfg["as_is"])
    if rule["point"]:
        settings["point"] = rule["point"]
    return settings


def _route_line(name, length, piece, rule, slope):
    """(ok, сообщение) о трассе к прибору."""
    if length is None:
        return False, f"к {name} нет трассы канализации от точки подключения (через коридор/дверь)"
    if has(piece, rule["toilet"]) and length > rule["toilet_max"]:
        return False, f"унитаз {name} в {length:.0f} см от точки подключения (нужно ≤ {rule['toilet_max']})"
    meters = length / CM_IN_M
    drop = length * slope
    return True, f"{name} — трасса {meters:.1f} м, перепад {drop:.0f} см"


def _point_line(point, source):
    where = f"({point[0]:.0f}, {point[1]:.0f})"
    return f"точка подключения {where} — {source}"


def drain_routes(ctx, rule):
    """От точки подключения до каждого прибора с канализацией есть трасса; унитаз — не дальше toilet_max."""
    settings = _drain_settings(ctx, rule)
    slope = settings["slope"] if rule["slope"] is None else rule["slope"]
    point, source = drain_point(settings, rule["toilet"])
    if point is None:
        return [(False, f"нет точки подключения канализации: {source}")]
    found = [(True, _point_line(point, source))]
    found.extend(_routes_lines(ctx, point, rule, slope))
    return found


def _routes_lines(ctx, point, rule, slope):
    """Мокрые комнаты без rect и трассы к приборам."""
    traced, missing = routes(ctx, point, rule["wet_rooms"])
    found = [
        (False, f"у мокрой комнаты {room_id} нет rect — трассу не построить") for room_id in missing
    ]
    found.extend(_route_line(*route, rule, slope) for route in traced)
    return found
