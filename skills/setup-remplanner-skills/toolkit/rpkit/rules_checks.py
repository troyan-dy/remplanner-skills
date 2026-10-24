"""Типы правил rules.json → функции проверки: (ctx, правило) → [(ok, сообщение)]."""

from rpkit.frozen import frozen
from rpkit.rules_check_drain import drain_routes
from rpkit.rules_check_entry import near_entry
from rpkit.rules_check_kitchen import kitchen_straight, no_corner_join
from rpkit.rules_check_places import behind_door, items_in_rooms
from rpkit.rules_check_room_has import room_has
from rpkit.rules_check_sizes import min_size
from rpkit.rules_check_storage import bedroom_storage
from rpkit.rules_check_windows import window_clear, window_full

CHECKS = frozen({
    "near_entry": near_entry,
    "bedroom_storage": bedroom_storage,
    "drain_routes": drain_routes,
    "window_full": window_full,
    "window_clear": window_clear,
    "items_in_rooms": items_in_rooms,
    "behind_door": behind_door,
    "kitchen_straight": kitchen_straight,
    "no_corner_join": no_corner_join,
    "min_size": min_size,
    "room_has": room_has,
})
