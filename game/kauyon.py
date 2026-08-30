"""T'au Empire detachment rule: Kauyon's Patient Hunter.

RULE (verbatim, rules/tau_empire/detachments/Kauyon.md):
  During the third, fourth and fifth battle rounds, ranged weapons equipped by
  T'AU EMPIRE models from your army have the [SUSTAINED HITS 1] ability.
  During the third, fourth and fifth battle rounds, while a unit is a Guided
  unit (see For the Greater Good), each time a ranged attack is made by a model
  in that unit that targets a Spotted unit, you can ignore any or all modifiers
  to that attack's Ballistic Skill characteristic and/or all modifiers to the
  Hit roll.

Mont'ka (game/montka.py) is the same shape with the other three rounds and
different keywords; what the two share is in game/tau_detachments.py.

THE TWO HALVES HOOK IN TWO DIFFERENT PLACES, AND THAT IS THE POINT
------------------------------------------------------------------
The [SUSTAINED HITS 1] half is a KEYWORD GRANT, so it belongs in
ShootingController._adjusted_weapon()'s chain - and specifically it must be
there rather than at the wound step, because _crit_note() has to know at ROLL
time whether a critical die is a Sustained one.

The second half is not a keyword at all: it removes MODIFIERS, so it belongs in
_hit_modifiers(). Its wording is word for word what rule 24.29's [PSYCHIC] and
UnitProfile.ignores_hit_modifiers already say, and it gets the same treatment
they do - see hit_modifiers_ignored() below.

WHY "IGNORE ANY OR ALL" IS APPLIED AUTOMATICALLY
------------------------------------------------
The printed text is a permission ("you CAN ignore"), so in principle it is a
choice. It is resolved automatically anyway, and not as a shortcut: the choice
is between keeping a modifier that makes the roll worse and dropping it, so
there is no board state in which keeping one is the better play. That is the
identical argument game/shooting.py already writes out for [PSYCHIC], and both
filters do the identical thing - drop the worsening modifiers, keep the
improving ones. Handing the player an interactive prompt per attack for a
decision with one rational answer would be the Fehlerklasse-5 mistake of
offering what nobody would choose.

"BALLISTIC SKILL CHARACTERISTIC AND/OR THE HIT ROLL" is one thing here for the
same reason UnitProfile.ignores_hit_modifiers records: this engine applies both
to the same hit threshold, so there is nothing to separate.
"""

import copy

from game import tau_detachments
from game.weapons import RANGED

SETTING = "KAUYON_PLAYERS"
PATIENT_HUNTER_ROUNDS = (3, 4, 5)
SUSTAINED_HITS_GRANTED = 1
LABEL = "Patient Hunter"


def is_active(squad, turn_tracker):
    """The condition both halves open with."""
    return tau_detachments.doctrine_active(
        squad, SETTING, PATIENT_HUNTER_ROUNDS, turn_tracker)


def adjusted_weapon(weapon, squad, turn_tracker):
    """[SUSTAINED HITS 1] on this army's ranged weapons, rounds 3-5.

    Returns the weapon unchanged when it does not apply, and a COPY when it
    does - the shared WeaponProfile instance is never mutated.
    """
    if weapon is None or not is_active(squad, turn_tracker):
        return weapon
    if weapon.weapon_type != RANGED:
        return weapon
    # NEVER DOWNGRADES. "have the [SUSTAINED HITS 1] ability" GRANTS the
    # ability; it does not SET the value, so a weapon already printing
    # [SUSTAINED HITS 2] keeps its 2. Same reading - and the same two guards -
    # as game/ritual_butchery.py, which grants the identical keyword.
    if getattr(weapon, "sustained_hits", 0) >= SUSTAINED_HITS_GRANTED:
        return weapon
    if getattr(weapon, "sustained_hits_notation", None) is not None:
        # A printed dice X ([SUSTAINED HITS D3]) is already at least as good as
        # a flat 1 in every outcome, so granting a flat 1 could only take
        # something away.
        return weapon
    granted = copy.copy(weapon)
    granted.sustained_hits = SUSTAINED_HITS_GRANTED
    return granted


def hit_modifiers_ignored(squad, target_squad, turn_tracker, greater_good):
    """Whether this attack may ignore its hit modifiers - the second half.

    Three conditions, and all three are in the printed text: the round window,
    the attacking unit being Guided, and the target being its Spotted unit.
    The last two are one question here, because the army rule defines a unit as
    Guided only "while targeting one or more Spotted units" - see
    game/tau_detachments.is_guided_attack().
    """
    if not is_active(squad, turn_tracker):
        return False
    return tau_detachments.is_guided_attack(greater_good, squad, target_squad)
