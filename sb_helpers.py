"""Storm's Beacon - the handful of questions the story asks that MAST cannot ask in a line.

Every function is prefixed `sb_` on purpose: a mission's `.py` lands in the same flat MAST
namespace as every addon it loads, and a name like `crew_has` would be one collision away
from breaking a story that has nothing to do with this one.
"""
from sbs_utils.procedural.query import to_object_list
from sbs_utils.procedural.roles import role
from sbs_utils.procedural.inventory import get_inventory_value


def sb_crew_has(key, count=1):
    """Is the clue (or item) `key` in any player ship's hold?

    Asked of every player ship rather than "the" ship: this is a one-ship campaign today,
    but a gate that silently means "ship one" is the kind of thing that only shows up on
    the day somebody adds a second bridge.

    The items addon stores a collected item on the ship under its own key, so this is a
    direct read - and it is the same store the dialogue guard `if carrying clue_x >= 1`
    uses, so the comms branch and the story gate can never disagree about what the crew
    is carrying.
    """
    held = 0
    for so in to_object_list(role("__player__")):
        held += int(get_inventory_value(so.id, key, 0) or 0)
        if held >= count:
            return True
    return held >= count
