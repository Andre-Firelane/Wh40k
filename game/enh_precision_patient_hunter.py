"""Kauyon Enhancement: Precision of the Patient Hunter (15 pts).

RULE (verbatim, rules/tau_empire/detachments/Kauyon.md):
  T'AU EMPIRE model only. Each time the bearer makes a ranged attack, add 1 to
  the Hit roll. From the third battle round onwards, add 1 to the Wound roll as
  well.

PER MODEL, NOT PER UNIT - AND THAT IS WHY IT REACHES _attack_key()
-------------------------------------------------------------------
"Each time the BEARER makes a ranged attack" is the bearer's own attacks, not
his unit's; there is no "while leading" clause here, so after a rule 19.01
merge a ten-model unit has one model with the bonus and nine without.

ShootingController resolves attacks in GROUPS and reads several per-model
things off `group["pairs"][0]` - the one-representative shortcut. That is exact
only while the thing in question is part of _attack_key(), which is what makes
a group homogeneous in it. game/psychic_communion.py is the precedent and the
cautionary tale: its docstring claimed the groups "sort themselves out for
free" because its bonus changes Strength and Strength is in the key - and they
did not, because the key reads the RAW weapon.strength before any adjuster
runs. Both Warlocks landed in one group and the shortcut handed whichever bonus
pairs[0] happened to carry to all of them.

So the flag itself goes in the key (hit_bonus() below, 0 for every model
without the Enhancement, so no group that already exists splits), and the
one-representative read is then exact by construction rather than by luck.

THE TWO HALVES HAVE DIFFERENT CONDITIONS, AND ONLY ONE OF THEM IS A ROUND
--------------------------------------------------------------------------
The Hit bonus is unconditional. The Wound bonus starts in round 3 - which is
also when Kauyon's own Patient Hunter starts, but they are NOT the same
condition and are not read through the same function: this one is a flat "from
the third battle round onwards", so it is NOT widened by Exemplar of the Kauyon
(game/enh_exemplars.py), which widens the DETACHMENT RULE and says so. Pinned
as its own test line, because "they both start in round 3" makes sharing
tempting and would silently make this one start in round 2 for a unit led by
an Exemplar.

SIGNS. game/modifiers.py's convention is that a Modifier adjusts the THRESHOLD,
so a bonus to the roll is a NEGATIVE amount - the same -1 that [HEAVY], Guide
and Command Protocols carry. Written the other way round this would be an
army-wide permanent penalty on the one model that paid 15 points for it.
"""

from game import enhancements

PRECISION_OF_THE_PATIENT_HUNTER = "Precision of the Patient Hunter"
WOUND_BONUS_FROM_ROUND = 3
LABEL = PRECISION_OF_THE_PATIENT_HUNTER


def applies(model):
    """Whether this MODEL is a live bearer whose owner fields Kauyon."""
    return enhancements.model_is_active(model, PRECISION_OF_THE_PATIENT_HUNTER)


def hit_bonus(model):
    """1 while this model has the Enhancement, else 0.

    A NUMBER rather than a bool because this is what goes into
    ShootingController._attack_key() - see the module docstring. Kept 0 for
    every other model so no existing group splits."""
    return 1 if applies(model) else 0


def hit_modifiers(model):
    """"add 1 to the Hit roll" - ranged only, so only _hit_modifiers() in
    game/shooting.py reads this; game/fight.py deliberately does not."""
    from game.modifiers import Modifier
    if not applies(model):
        return []
    return [Modifier(-1, LABEL)]


def wound_modifiers(model, turn_tracker):
    """"From the third battle round onwards, add 1 to the Wound roll as well."

    A missing turn_tracker, or one with no battle round yet, reads as BEFORE
    round 3 - the safe direction, since it withholds a bonus rather than
    inventing one. That falls out of the comparison rather than needing a guard
    of its own, the same way game/tau_detachments.py's battle_round_in()
    handles it."""
    from game.modifiers import Modifier
    if not applies(model):
        return []
    battle_round = getattr(turn_tracker, "battle_round", None)
    if battle_round is None or battle_round < WOUND_BONUS_FROM_ROUND:
        return []
    return [Modifier(-1, f"{LABEL} (round {WOUND_BONUS_FROM_ROUND}+)")]
