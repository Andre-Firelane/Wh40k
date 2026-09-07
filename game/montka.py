"""T'au Empire detachment rule: Mont'ka's Killing Blow.

RULE (verbatim, rules/tau_empire/detachments/Mont'ka.md):
  During the first, second and third battle rounds, ranged weapons equipped by
  T'AU EMPIRE models from your army have the [ASSAULT] ability. During the
  first, second and third battle rounds, while a unit is a Guided unit, its
  ranged weapons have the [LETHAL HITS] ability.

Kauyon (game/kauyon.py) is the mirror image - the other three rounds, and its
second clause removes modifiers where this one grants a keyword. What the two
share is in game/tau_detachments.py.

BOTH HALVES ARE KEYWORD GRANTS, so unlike Kauyon both live in
ShootingController._adjusted_weapon()'s chain. [LETHAL HITS] in particular MUST
be applied there rather than at the wound step: _crit_note() reads the keyword
at ROLL time to label a critical die, so a grant applied later would resolve
correctly but describe itself wrongly on screen.

THE SECOND CLAUSE IS NARROWER THAN IT LOOKS
-------------------------------------------
"while a unit is a Guided unit, its ranged weapons have [LETHAL HITS]" reads
like a property of the unit, but the army rule defines Guided as "while
targeting one or more Spotted units" - so it is a property of the ATTACK, and
the same unit shooting a second, unspotted target does not have it. That is why
this takes `target_squad` at all, and it is pinned as its own test line because
a unit-level reading looks perfectly plausible in isolation.

Note the contrast with Kauyon's second clause, which additionally spells out
"that targets a Spotted unit". Both end up at the same test; only Kauyon says it
twice.
"""

import copy

from game import tau_detachments
from game.weapons import RANGED

SETTING = "MONTKA_PLAYERS"
KILLING_BLOW_ROUNDS = (1, 2, 3)
LABEL = "Killing Blow"


def is_active(squad, turn_tracker):
    """The condition both halves open with."""
    return tau_detachments.doctrine_active(
        squad, SETTING, KILLING_BLOW_ROUNDS, turn_tracker)


def grants_assault(squad):
    """Whether Killing Blow's [ASSAULT] half is up for this unit RIGHT NOW.

    Reads the flag refresh_killing_blow() stamps rather than asking is_active()
    live, and that is forced rather than chosen: rule 10.05 is decided by
    game/coldstar.py's weapon_has_assault(), which is handed only
    (weapon, squad). The turn_tracker this rule opens with would have to be
    threaded through _attack_groups()'s eleven call sites on the hottest
    shooting path to reach it, so it arrives as state on the unit instead - the
    same arrangement, and the same reason, as Nurgle's Gift's Squad.afflicted
    and Star Engines' Squad.star_engines_active.

    A squad that has never been through a refresh reads False: no Mont'ka on
    the table means no grant, which is the safe direction for a detachment rule
    - it withholds a bonus rather than inventing one, exactly as
    tau_detachments.battle_round_in()'s getattr default does.
    """
    return bool(getattr(squad, "montka_killing_blow", False))


def refresh_killing_blow(squads, turn_tracker):
    """Stamp Squad.montka_killing_blow for every unit in `squads`.

    ONE condition, two read paths: this calls is_active(), the same function
    adjusted_weapon() opens with, so the round window - including
    game/enh_exemplars.py's per-unit widening for a bearer of the Exemplar of
    the Mont'ka - is never written down twice. A literal KILLING_BLOW_ROUNDS
    here would be a second answer to a question game/tau_detachments.py already
    owns, and it would drop the Enhancement's fourth round at the Advance gate
    only - leaving the two readers of one rule disagreeing.
    """
    for squad in squads or ():
        squad.montka_killing_blow = is_active(squad, turn_tracker)


def adjusted_weapon(weapon, squad, turn_tracker, target_squad=None, greater_good=None):
    """[ASSAULT] on this army's ranged weapons, plus [LETHAL HITS] while the
    attack is a Guided one - rounds 1-3.

    Both halves in one call, so a caller cannot wire up one and forget the
    other. Returns the weapon unchanged when neither applies, and a single COPY
    when either does; the shared WeaponProfile instance is never mutated.
    """
    if weapon is None or not is_active(squad, turn_tracker):
        return weapon
    if weapon.weapon_type != RANGED:
        return weapon

    wants_assault = not weapon.assault
    wants_lethal = (
        not weapon.lethal_hits
        and tau_detachments.is_guided_attack(greater_good, squad, target_squad)
    )
    if not wants_assault and not wants_lethal:
        return weapon
    granted = copy.copy(weapon)
    if wants_assault:
        granted.assault = True
    if wants_lethal:
        granted.lethal_hits = True
    return granted
