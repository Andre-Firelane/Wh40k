"""T'au support drone wargear. Modeled via game/factions/datasheet.py's Gear
(a wargear item that isn't a simple weapon swap, applied through an
`effect(token)` callback that mutates the bearer directly) rather than
WargearOption, since three of the four grant an ability/characteristic
change rather than just a weapon.

Real wargear-options text (from the official app, screenshots supplied by
the user):
- Strike Team: "The Fire Warrior Shas'ui can be equipped with up to two of
  the following, and can take duplicates: guardian drone (cannot take
  duplicates of this piece of wargear) / gun drone / marker drone / shield
  drone." So duplicates ARE allowed (2x Gun Drone, 2x Marker Drone, 2x
  Shield Drone) except for Guardian Drone specifically - the opposite of
  what an earlier, pre-screenshot guess here assumed ("never the same one
  twice"). drone_options(allow_duplicates=True) for this datasheet.
- Crisis Starscythe Battlesuits: "Any number of models can be equipped with
  up to two of the following, but cannot take duplicates: gun drone / marker
  drone / shield drone" - no Guardian Drone on this datasheet's menu at all,
  and no duplicates. drone_options(include_guardian=False) for this one.
- Breacher Team: no screenshot supplied yet for this datasheet specifically
  - left on drone_options()'s old default (include_guardian=True,
  allow_duplicates=False) until its own real wargear text is available;
  that may well be wrong the same way Strike Team's guess was, but nothing
  here confirms it either way yet.

Marker Drone
Abilities
Marker Drone: The bearer's unit has the Markerlight keyword and can act as
an Observer unit for another unit even if it Advanced this turn.
Keywords: Markerlight

Shield Drone
Abilities
Shield Drone: Add 1 to the bearer's Wounds characteristic.

Guardian Drone
Abilities
Guardian Drone: Each time a model makes a ranged attack that targets the
bearer's unit, subtract 1 from the Wound roll.

Gun Drone
Equips the bearer with a Twin pulse carbine (same weapon/stats already
defined for Strike Team's "Unselected Profiles", game/weapons.py -
TwinPulseCarbineProfile)."""

from game.weapons import DroneBurstCannonProfile, MissilePodProfile, TwinPulseCarbineProfile
from game.factions.datasheet import Gear

DRONE_SLOTS = 2  # "the leader can get 2 drones, but never the same one twice"

# Gear.group names, for a model line that has more than one independent
# wargear menu (Pathfinder Team's Shas'ui: "2 drones AND one special drone
# from these 3"). Every ordinary drone shares one group so a datasheet with
# a single menu behaves exactly as before - see Datasheet.gear_slots.
DRONE_GROUP = "drones"
SPECIAL_DRONE_GROUP = "special_drone"


def _marker_drone_effect(token):
    """"The bearer's unit has the Markerlight keyword" - both Strike Team
    and Breacher Team already have MARKERLIGHT unconditionally (see their
    own Keywords line), so this is a no-op for them specifically, but still
    set correctly for whichever future T'au unit doesn't already have it.
    "...and can act as an Observer unit for another unit even if it
    Advanced this turn" has nothing to override in this engine:
    GreaterGoodController.can_use() never checked advance status in the
    first place (the "For The Greater Good" army rule text we were given
    doesn't mention one either) - there's no existing restriction for this
    clause to grant an exception to."""
    token.profile.markerlight = True


def _shield_drone_effect(token):
    """"Add 1 to the bearer's Wounds characteristic" - a real characteristic
    change (like Retaliation Cadre's Bonded Heroes), not a roll modifier:
    bumps both the profile's own W stat and this specific model's current
    wound count (already set once at Token construction, before Gear is
    applied - see build_squad())."""
    token.profile.wounds += 1
    token.current_wounds += 1


def _guardian_drone_effect(token):
    token.profile.guardian_drone = True


def _gun_drone_effect(token):
    token.weapons.append(TwinPulseCarbineProfile())


def _missile_drone_effect(token):
    token.weapons.append(MissilePodProfile())


def marker_drone_gear(model_line_name, max_count=1):
    """A standalone Marker Drone Gear item - same reasoning as
    gun_drone_gear() below, for datasheets (e.g. Stealth Battlesuits' Shas'vre)
    that grant Marker Drone on its own rather than through the full
    drone_options() menu."""
    return Gear(model_line_name, "Marker Drone", _marker_drone_effect, max_count=max_count, group=DRONE_GROUP)


def gun_drone_gear(model_line_name, max_count=1):
    """A standalone Gun Drone Gear item, reused both by drone_options()'s
    own menu and directly by datasheets that grant Gun Drone on its own
    (e.g. Stealth Battlesuits' Shas'vre: "can be equipped with 1 gun
    drone")."""
    return Gear(model_line_name, "Gun Drone", _gun_drone_effect, max_count=max_count, group=DRONE_GROUP)


def missile_drone_gear(model_line_name, max_count=1):
    """A standalone Missile Drone Gear item - grants the bearer a Missile
    pod, the same shape as gun_drone_gear()'s Twin pulse carbine. Justified
    by Pathfinder Team's own "Unselected Profiles" table listing a Missile
    pod, which on a unit with no missile-armed model of its own can only be
    a drone's weapon (the Riptide carries the same weapon for the same
    reason, see game/factions/tau_empire.py's _RIPTIDE_LOADOUT)."""
    return Gear(model_line_name, "Missile Drone", _missile_drone_effect, max_count=max_count, group=DRONE_GROUP)


def drone_options(model_line_name, include_guardian=True, allow_duplicates=False, include_missile=False):
    """The Gear choices for a given Shas'ui-type ModelLine, re-scoped to
    that datasheet's own leader line name. `include_guardian` drops Guardian
    Drone entirely for datasheets whose real menu doesn't have it (Crisis
    Starscythe Battlesuits). `allow_duplicates` raises Marker/Shield/Gun
    Drone's own max_count to 2 for datasheets whose real text says "can take
    duplicates" (Strike Team) - Guardian Drone's max_count is always 1
    regardless, per its own explicit "cannot take duplicates of this piece
    of wargear" text wherever it appears. `include_missile` adds a Missile
    Drone for datasheets whose own weapon table shows a Missile pod they
    have no other way of carrying (Pathfinder Team) - off by default, since
    no other datasheet's text or weapon table implies one."""
    dup_count = 2 if allow_duplicates else 1
    options = [
        Gear(model_line_name, "Marker Drone", _marker_drone_effect, max_count=dup_count, group=DRONE_GROUP),
        Gear(model_line_name, "Shield Drone", _shield_drone_effect, max_count=dup_count, group=DRONE_GROUP),
    ]
    if include_guardian:
        options.append(Gear(model_line_name, "Guardian Drone", _guardian_drone_effect, max_count=1, group=DRONE_GROUP))
    options.append(gun_drone_gear(model_line_name, max_count=dup_count))
    if include_missile:
        options.append(missile_drone_gear(model_line_name, max_count=dup_count))
    return options


# --- Special drones (Pathfinder Team) -------------------------------------
# User: "kann 2 drohnen erhalten und eine spezialdrohne aus den 3" - so a
# Pathfinder Team's Shas'ui takes up to DRONE_SLOTS drones from the normal
# menu above PLUS exactly one of these three. Modeled as a separate,
# 1-slot menu (see special_drone_options() / SPECIAL_DRONE_SLOTS) rather
# than as three more entries in drone_options(), because "one of these
# three" is its own cap - folding them in would let a model take two
# special drones and no ordinary one.


def _grav_inhibitor_drone_effect(token):
    """"Each time an enemy unit selects the bearer's unit as the target of a
    charge, subtract 2 from the Charge roll" - a flag rather than a
    characteristic change, because the effect is on someone ELSE's roll and
    has to be read at the moment that charge is declared. See
    game/grav_inhibitor_drone.py, which also explains why the -2 lands where
    the roll is consumed rather than where it is rolled."""
    token.profile.grav_inhibitor_drone = True


def _pulse_accelerator_drone_effect(token):
    """"Add 6\" to the Range characteristic of pulse carbines equipped by
    models in the bearer's unit" - a flag, not a range change baked into the
    weapons, since it applies to the whole UNIT and only while a bearer is
    alive. See game/pulse_accelerator.py."""
    token.profile.pulse_accelerator_drone = True


def _recon_drone_effect(token):
    """"The bearer is equipped with 1 Drone burst cannon and the bearer's
    unit has the Infiltrators ability."

    Both halves are real, already-implemented mechanisms: the weapon is a
    plain append (like Gun Drone's), and INFILTRATORS is rule 24.20, live
    since the Pre-game Sequence was built (game/pregame.py reads
    squad_has_infiltrators(), which requires EVERY model in the unit to have
    it - so the flag is set on the bearer here and the datasheet's own
    models do not carry it, meaning one Recon Drone does NOT by itself make
    the unit Infiltrators).

    The wargear text ("the bearer's UNIT has the Infiltrators ability") and
    rule 24.20's own "if every model in a unit has this ability" gate pull in
    opposite directions: setting `infiltrators` on the bearer alone would
    grant nothing at all, because squad_has_infiltrators() correctly requires
    every model to have it. So this sets its own `recon_drone` flag instead,
    and squad_has_infiltrators() reads that as the unit-level grant it is -
    keeping the reason visible at both ends rather than faking a per-model
    ability the datasheet's models do not have."""
    token.weapons.append(DroneBurstCannonProfile())
    token.profile.recon_drone = True


SPECIAL_DRONE_SLOTS = 1  # "eine spezialdrohne aus den 3"


def special_drone_options(model_line_name):
    """The "one special drone" menu: Grav-inhibitor / Pulse Accelerator /
    Recon. Each capped at 1 in its own right, with the owning Datasheet's
    gear_slots entry capping how many DISTINCT items of this menu a model may
    take - see special_drone_slots()."""
    return [
        Gear(model_line_name, "Grav-inhibitor Drone", _grav_inhibitor_drone_effect, max_count=1, group=SPECIAL_DRONE_GROUP),
        Gear(model_line_name, "Pulse Accelerator Drone", _pulse_accelerator_drone_effect, max_count=1, group=SPECIAL_DRONE_GROUP),
        Gear(model_line_name, "Recon Drone", _recon_drone_effect, max_count=1, group=SPECIAL_DRONE_GROUP),
    ]
