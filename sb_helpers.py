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


def sb_probe_park(relic_key, place):
    """The authoring probe (`sb_probe=inside`): park the ship in a ruin and turn it to face
    the middle of the room it is in. Returns True when it parked.

    `place` is a point's name or `x, y, z` relative to the relic. FACING matters as much as
    the spot: the main screen is a chase camera a few hundred units BEHIND the ship, so a
    ship parked near a wall facing away from it puts the camera outside the room, looking
    at the back of the wall.
    """
    from sbs_utils.procedural.amd_relics import (relic_point, relic_record, relic_pos,
                                                 relic_part_at, _relic_part_pos)
    from sbs_utils.procedural.volume import volume_look_quat
    from sbs_utils.vec import Vec3
    rec = relic_record(relic_key)
    if rec is None:
        return False
    at = relic_point(relic_key, place)
    if at is None:
        try:
            nums = [float(v) for v in str(place).replace(",", " ").split()]
        except ValueError:
            return False
        if len(nums) < 3:
            return False
        base = relic_pos(rec)
        at = (base[0] + nums[0], base[1] + nums[1], base[2] + nums[2])
    ships = to_object_list(role("__player__"))
    if not ships:
        return False
    ship = ships[0]
    ship.pos = Vec3(at[0], at[1], at[2])
    room = relic_part_at(relic_key, at)
    centre = _relic_part_pos(rec, room) if room else None
    if centre is not None:
        d = (centre[0] - at[0], 0.0, centre[2] - at[2])
        if abs(d[0]) + abs(d[2]) > 1.0:
            try:
                import sbs
                w, x, y, z = volume_look_quat(d)
                ship.engine_object.rot_quat = sbs.quaternion(w, x, y, z)
            except Exception:                            # noqa: BLE001
                pass
    return True


def sb_probe_report(relic_key):
    """Write where the probe's ship IS, and what is around it, to debug.log - the engine's
    only reliable output. Distances to the nearest wall pieces, by art key."""
    from sbs_utils.mast.mast import DEBUG
    from sbs_utils.procedural.amd_relics import relic_record, relic_part_at, relic_volume_name
    from sbs_utils.procedural.volume import volume_depth
    ships = to_object_list(role("__player__"))
    if not ships:
        DEBUG("probe: no ship")
        return
    p = ships[0].pos
    here = (p.x, p.y, p.z)
    rec = relic_record(relic_key)
    vol = relic_volume_name(rec) if rec is not None else None
    DEBUG("probe: ship at %s room=%s depth=%s" % (tuple(round(v) for v in here),
          relic_part_at(relic_key, here), volume_depth(vol, here) if vol else None))
    near = []
    for so in to_object_list(role("relic_wall:" + str(relic_key))):
        q = so.pos
        d = ((q.x - p.x) ** 2 + (q.y - p.y) ** 2 + (q.z - p.z) ** 2) ** 0.5
        near.append((round(d), so.art_id, (round(q.x), round(q.y), round(q.z))))
    near.sort()
    DEBUG("probe: %d wall pieces; nearest %s" % (len(near), near[:12]))
