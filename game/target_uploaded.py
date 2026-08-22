"""Pathfinder Team's own "Target Uploaded" ability, as supplied by the user
(not a rule from the generic 40k core rulebook, so it lives in its own
module - same reasoning as game/nova_charge.py for the Riptide's datasheet
ability and game/crack_shot.py for the Cadre Fireblade's).

RULE: Each time a model in this unit makes an attack that targets their
Spotted unit, improve the Ballistic Skill characteristic of that attack by 1
and that attack has the [IGNORES COVER] ability.

WHY THIS NEEDS ITS OWN MODULE INSTEAD OF REUSING "GUIDED"
--------------------------------------------------------
The two effects are exactly the two a Guided attack already gets (see
game/shooting.py's _hit_modifiers() and _cover_ignored_for_group()), so the
tempting reading is "this unit is just Guided". It is the opposite: the
"For The Greater Good" army rule explicitly EXCLUDES an Observer unit from
being Guided itself (GreaterGoodController.is_guided_attack() returns False
for one), which is precisely the case this ability is about.

The phrase that decides it is "THEIR Spotted unit" - the same wording
Stealth Battlesuits' Forward Observers uses, and resolved the same way
(has_forward_observers()): not "any Spotted unit", but the one THIS unit
marked. GreaterGoodController.spotted_by maps target -> the Observer that
marked it, so that is a direct lookup.

So the net effect is: a Pathfinder Team that spends its own Observer action
marking a target still gets the Guided benefits when it shoots that target
itself, which it otherwise would not. Against a unit Spotted by somebody
else, this ability does nothing - the normal Guided path already covers
that case, and stacking both would double-count.

WHY IT IS NOT CUMULATIVE WITH GUIDED IN PRACTICE
------------------------------------------------
It cannot be: the two conditions are mutually exclusive by construction. If
this unit marked the target, it is an Observer and is_guided_attack() is
False; if somebody else marked it, applies() below is False. Both callers
in game/shooting.py therefore OR the two together rather than summing, so
even a future rules change that let both hold at once would improve BS by 1,
not 2.
"""


def unit_has_target_uploaded(squad):
    """Rule 19.04: an ability granted by a datasheet applies while at least
    one model that HAS it is still alive - the same "source models" reading
    game/attached_units.py uses, applied here through the simple
    any()-over-live-models form (this ability is printed on every model of
    its own datasheet, so an attached unit keeps it exactly as long as some
    Pathfinder is still standing)."""
    if squad is None:
        return False
    return any(m.profile.target_uploaded for m in squad.models if not m.is_dead())


def applies(greater_good, attacking_squad, target_squad):
    """Whether this attack is "a model in this unit attacking THEIR Spotted
    unit" - i.e. the attacker has the ability and is the very Observer that
    marked this target.

    `greater_good` may be None (a controller built without the army rule
    wired, as several tests do) - then nothing is Spotted at all and this is
    simply False."""
    if greater_good is None or attacking_squad is None or target_squad is None:
        return False
    if not unit_has_target_uploaded(attacking_squad):
        return False
    return greater_good.spotted_by.get(target_squad) is attacking_squad
