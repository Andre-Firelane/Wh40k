"""Two Enhancements, one mechanism: Through Unity, Devastation (Kauyon) and
Coordinated Exploitation (Mont'ka).

RULES (verbatim, and both are the ERRATA'd text - the corpus prints the errata
immediately below each, changing nothing but the punctuation):
  Through Unity, Devastation (Kauyon, 30 pts)
    T'AU EMPIRE model only (excluding KROOT SHAPER models). While the bearer is
    leading a unit, each time that unit is an Observer unit, until the end of
    the phase, ranged weapons equipped by models in a Guided unit have the
    [LETHAL HITS] ability while targeting their Spotted unit.

  Coordinated Exploitation (Mont'ka, 30 pts)
    ... the same sentence with [SUSTAINED HITS 1].

WHY BOTH LIVE HERE
------------------
Word for word the same rule with one keyword swapped - the same relationship
game/kauyon.py and game/montka.py have to each other, and the same reason their
shared half was extracted. Two files would be two copies of a three-part
trigger ("bearer leads", "that unit spotted something this phase", "this attack
is a Guided one") whose middle part is the easy one to get wrong.

NO NEW STATE. "EACH TIME THAT UNIT IS AN OBSERVER UNIT, UNTIL THE END OF THE
PHASE" IS ALREADY RECORDED
---------------------------------------------------------------------------
GreaterGoodController keeps `observer_squad_ids` - the friendly units that have
used their Observer action this phase - and clears it in
reset_shooting_phase(), which is precisely "until the end of the phase". So the
trigger is a QUERY over state the army rule already holds, not a second ledger
that would have to be reset in the same place and could fall out of step with
it. This module holds nothing at all.

THE GRANT IS ARMY-WIDE, NOT TIED TO THE BEARER'S OWN MARK - AND THAT IS THE
PRINTED READING
---------------------------------------------------------------------------
Compare Stealth Battlesuits' Forward Observers, which this otherwise resembles:
that one is explicitly narrowed to "the SPECIFIC Observer that marked
target_squad" (game/greater_good.py's has_forward_observers()). These two are
not. Their sentence spends its Observer requirement on the BEARER'S unit and
then says "until the end of the phase" - a clause that would be redundant if
the grant only ever applied to attacks against the one unit the bearer just
marked, because that mark itself already lasts exactly the phase. So: once the
bearer's unit has spotted anything, every Guided attack that player makes for
the rest of the phase carries the keyword.

"their Spotted unit" is therefore read as game/tau_detachments.py's
is_guided_attack() reads it - the target of a Guided attack - which is the same
test Mont'ka's own second clause uses. Written out because the narrower reading
is entirely plausible in isolation and would be invisible in a test that only
ever fields one Observer.

WHERE THEY LAND
---------------
ShootingController._adjusted_weapon()'s chain, beside Kauyon's and Mont'ka's own
grants, and for the same reason those are there rather than at the wound step:
_crit_note() reads these keywords at ROLL time to label a critical die, so a
grant applied later would resolve correctly and describe itself wrongly on
screen.

NEVER DOWNGRADES. "have the [SUSTAINED HITS 1] ability" GRANTS the ability, it
does not SET the value - a weapon already printing [SUSTAINED HITS 2] keeps its
2, and one printing a dice X is left alone. The same two guards game/kauyon.py
and game/ritual_butchery.py carry, for the same keyword.
"""

import copy

from game import attached_units, enhancements, tau_detachments
from game.weapons import RANGED

THROUGH_UNITY_DEVASTATION = "Through Unity, Devastation"
COORDINATED_EXPLOITATION = "Coordinated Exploitation"

SUSTAINED_HITS_GRANTED = 1


def observer_bearer_active(greater_good, player, name):
    """"While the bearer is leading a unit, each time that unit is an Observer
    unit" - has any Observer unit of `player` this phase got this Enhancement's
    bearer leading it?

    Three conditions, all printed: the unit is one of this phase's Observers
    (the army rule's own record), the Enhancement is live on it
    (game/enhancements.py's is_active(), which also checks the owner really
    fields the detachment), and the bearer is LEADING it - 24.22, read through
    attached_units.leader_ability() and not unit_wide_ability(), which asks
    whether every model prints the ability and is therefore False for every
    unit that actually has a leader ability.
    """
    if greater_good is None or player is None:
        return False
    flag = enhancements.get(name).flag
    for squad in getattr(greater_good, "observer_squad_ids", ()) or ():
        if getattr(squad, "owner", None) != player:
            continue
        if not enhancements.is_active(squad, name):
            continue
        if attached_units.leader_ability(squad, flag):
            return True
    return False


def _applies(name, squad, target_squad, greater_good):
    if squad is None:
        return False
    if not tau_detachments.is_guided_attack(greater_good, squad, target_squad):
        return False
    return observer_bearer_active(greater_good, getattr(squad, "owner", None), name)


def lethal_hits_applies(squad, target_squad, greater_good):
    """Through Unity, Devastation - Kauyon."""
    return _applies(THROUGH_UNITY_DEVASTATION, squad, target_squad, greater_good)


def sustained_hits_applies(squad, target_squad, greater_good):
    """Coordinated Exploitation - Mont'ka."""
    return _applies(COORDINATED_EXPLOITATION, squad, target_squad, greater_good)


def adjusted_weapon(weapon, squad, target_squad, greater_good):
    """Both grants in one call, so a caller cannot wire up one and forget the
    other - the same arrangement game/montka.py's adjusted_weapon() uses for
    its own two halves.

    They belong to different detachments and can never both be live: a player
    fields one detachment, and is_active() checks which. Applied through one
    copy anyway, because "can never both fire" is a fact about the config, not
    about this function.

    Returns the weapon unchanged when neither applies; the shared WeaponProfile
    instance is never mutated.
    """
    if weapon is None or weapon.weapon_type != RANGED:
        return weapon
    wants_lethal = (
        not weapon.lethal_hits
        and lethal_hits_applies(squad, target_squad, greater_good)
    )
    wants_sustained = (
        getattr(weapon, "sustained_hits", 0) < SUSTAINED_HITS_GRANTED
        and getattr(weapon, "sustained_hits_notation", None) is None
        and sustained_hits_applies(squad, target_squad, greater_good)
    )
    if not wants_lethal and not wants_sustained:
        return weapon
    granted = copy.copy(weapon)
    if wants_lethal:
        granted.lethal_hits = True
    if wants_sustained:
        granted.sustained_hits = SUSTAINED_HITS_GRANTED
    return granted
