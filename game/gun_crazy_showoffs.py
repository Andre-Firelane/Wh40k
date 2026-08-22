"""Flash Gitz' own "Gun-crazy Show-offs" ability, as supplied by the user
(not a rule from the generic 40k core rulebook, so it lives in its own module
- same reasoning as game/spirit_of_gork.py for the Kill Rig's and
game/monster_hunters.py for Beast Snagga Boyz').

RULE: Each time a model in this unit targets the closest eligible target with
its Snazzgun, until the end of the phase, that weapon has an Attacks
characteristic of 4.

REUSES THE CLOSEST-TARGET SNAPSHOT, IT DOES NOT RECOMPUTE IT
------------------------------------------------------------
"the closest eligible target" is exactly the condition The Twin Lance's
Exemplars of Mont'ka already reads, and ShootingController answers it once
per activation in _snapshot_target_state() (see
game/exemplars_of_montka.py's own docstring for why it must be settled at
target selection and not per attack, and why it would be far too expensive
to redo per weapon group). This ability just reads the same snapshot.

AN OVERRIDE, NOT A BONUS
------------------------
"has an Attacks characteristic of 4" - an absolute value, so a weapon whose
Attacks is already 4 or more is left alone rather than raised. Today the
printed Snazzgun is A3, so it is always a +1 in practice; writing it as an
override keeps it correct if some other source ever raises the base first.
The same "absolute, not additive" shape as Warboss in Mega Armour's Dead
Brutal (see game/waaagh.py).

WHICH WEAPON
------------
"with its Snazzgun" names one weapon, so the grant is scoped by name rather
than applying to every ranged weapon the unit carries - the same name-based
scoping game/pulse_accelerator.py uses, and flagged the same way: if a
future Flash Gitz loadout prints a differently-named gun that should also
benefit, SNAZZGUN_NAMES is the one place to widen. Both halves are required
(the model has the ability AND the weapon is a Snazzgun), so a Snazzgun
handed to some other datasheet gains nothing, and a Flash Git firing
something else gains nothing either.

"UNTIL THE END OF THE PHASE"
----------------------------
Modeled as a property of the attack being resolved rather than as stored
state. A unit shoots once per Shooting phase, and the grant is conditioned
on which target that weapon was pointed at - so "for this attack" and "until
the end of the phase" cannot be told apart by anything observable here.
Storing a flag would add a lifetime to clear without changing any outcome.
The one case where the wording would matter - the same weapon firing twice
in a phase, at the closest target and then at something else - cannot arise:
a weapon resolves its attacks once, and Split Fire assigns each weapon a
single target before any dice are rolled.
"""

import copy

SNAZZGUN_NAMES = frozenset({"Snazzgun"})
GUN_CRAZY_ATTACKS = 4


def unit_has_gun_crazy_showoffs(squad):
    """True while at least one live model with the ability is in the unit -
    the same rule 19.04 reading every other datasheet ability here uses."""
    if squad is None:
        return False
    return any(m.profile.gun_crazy_showoffs for m in squad.models if not m.is_dead())


def gun_crazy_adjusted_weapon(weapon, pairs, is_closest):
    """Sets the Snazzgun's Attacks to 4 when it was pointed at the closest
    eligible target.

    A real characteristic change on a shallow copy - the shared
    WeaponProfile instance is never mutated, same reasoning as
    montka_adjusted_weapon()/get_stuck_in_adjusted_weapon().

    `is_closest` is passed in rather than recomputed - the caller holds the
    snapshot that decided it (see the module docstring)."""
    if not is_closest or not pairs:
        return weapon
    if weapon.name not in SNAZZGUN_NAMES:
        return weapon
    shooter = pairs[0][0]
    if not shooter.profile.gun_crazy_showoffs:
        return weapon
    if weapon.attacks >= GUN_CRAZY_ATTACKS:
        return weapon
    boosted = copy.copy(weapon)
    boosted.attacks = GUN_CRAZY_ATTACKS
    return boosted
