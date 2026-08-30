"""The Farseer's "Branching Fates" - a datasheet ability, so its own module.

RULE (printed, word for word):
  "While this model is leading a unit, once per phase, you can change the
  result of one Hit roll, one Wound roll or one Damage roll made for a model in
  that unit (excluding SUPPORT WEAPON models) to an unmodified 6."

THE SAME EFFECT AS AN ASPECT SHRINE TOKEN, A DIFFERENT RESOURCE
---------------------------------------------------------------
"Change the result of one Hit roll or one Wound roll ... to an unmodified 6" is
word for word what the ASPECT WARRIORS token grants, so the arithmetic and the
"is it worth offering" gate come from game/unmodified_six.py, which was
extracted out of that ability precisely because this is its second consumer.

What is genuinely this ability's own is only:
  * the RESOURCE - once per PHASE while leading, rather than a per-battle
    token, so it refreshes and is far cheaper to spend;
  * the EXCLUSION - SUPPORT WEAPON models rather than CHARACTER models;
  * a third roll type - the DAMAGE roll, which the token does not cover.

THE DAMAGE HALF NEEDED A NEW SEAM. A dice-notation Damage characteristic is
rolled per allocated attack inside game/damage_resolution.py's
DamageAllocationSession, which already had one collaborator for that die
(game/damage_reroll.py, whose answer is "throw it again"). "Set it to 6" is a
different answer, so it is a second, parallel collaborator rather than a bool
overloaded into the first.

ONE ROLL TYPE PER PHASE, and the offer stops entirely once it is spent - which
is what keeps this from becoming the interruption problem. Unlike the token,
which is precious enough that a player will hoard it, this refreshes every
phase, so the gate inherited from unmodified_six.py does most of the work:
nothing is offered on a roll where changing a die would buy nothing.

"AN UNMODIFIED 6" ON A DAMAGE ROLL is taken literally, including where the
Damage characteristic is a D3 and a 6 could never come up on its own - the
sentence says what the result becomes, not what the die shows. Noted rather
than quietly capped.
"""

from game import attached_units
from game import unmodified_six

BRANCHING_FATES_RESULT = unmodified_six.UNMODIFIED_SIX


def unit_has_farseer(squad):
    """Whether this unit is being LED by a model with the ability.

    attached_units.leader_ability() is the 19.04-correct lookup: it requires a
    real attached unit (a lone Farseer leads nobody), reads the ability off the
    leader COMPONENT so it ends when he dies, and brings 19.04's grace window
    with it."""
    return attached_units.leader_ability(squad, "branching_fates")


def _excluded(model):
    """"Excluding SUPPORT WEAPON models". No SUPPORT WEAPON datasheet exists
    in this engine yet, so this is currently always False - a condition that
    correctly evaluates to False, and one that will start excluding on its own
    when such a datasheet arrives."""
    return bool(getattr(model, "profile", None) and getattr(model.profile, "support_weapon", False))


def available(squad):
    return unit_has_farseer(squad) and not getattr(squad, "branching_fates_used", False)


def spend(squad):
    squad.branching_fates_used = True


def reset_phase(squads=()):
    """"Once per phase"."""
    for squad in squads:
        squad.branching_fates_used = False


def _usable(squad, model):
    return squad is not None and available(squad) and not _excluded(model)


def usable(squad, model):
    """Public: is the ability live for a roll made by `model`? See
    aspect_shrine.usable() - same contract, different resource."""
    return _usable(squad, model)


def button_label(squad):
    """The left-panel button. No count to show - it is once per phase, so it
    is either there or it is not."""
    return "Branching Fates (once per phase)"


def damage_change(squad, model, amount):
    """The Damage half: the rolled amount becomes 6, or None if there is
    nothing to gain (it already is 6 or more) or the ability is unavailable."""
    if not _usable(squad, model):
        return None
    if amount >= BRANCHING_FATES_RESULT:
        return None
    return BRANCHING_FATES_RESULT


ACCEPT_LABEL = "Use Branching Fates"

