"""Привязка проёма к стене .plan."""

from rpkit.rp_ids import uid


def hole_link(host):
    """Поля проёма, которые связывают его со стеной host: новый id, parent, parent_depth, dls_prs."""
    return {
        "id": uid(),
        "parent": host["id"],
        "parent_depth": host["depth"],
        "dls_prs": {},
    }


def attach(host, hole):
    """Проём hole — в holes стены host."""
    host.setdefault("holes", {})[hole["id"]] = hole
    return hole
