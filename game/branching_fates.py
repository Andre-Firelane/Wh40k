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

"AN UNMODIFIED 6" ON A DAMAGE ROLL SETS THE DIE, exactly as it does on the
Hit and Wound rolls, and that is forced by the printed sentence: there is one
verb and one object list - "change the result of one Hit roll, one Wound roll
OR one Damage roll ... to an unmodified 6" - so all three share the predicate.
"An unmodified 6" names a DIE FACE throughout these rules (05.01/05.02 both
speak of the unmodified roll), and the hit/wound halves have always read it
that way. So does the one OTHER ability in this engine that talks about a
Damage die: game/structural_collapse.py's header says outright that "a Damage
roll of 1" names the die and not the total, and derives the face from the
notation for exactly that reason. Two readings of one phrase were shipped side
by side; this is the one that had two thirds of the engine already agreeing
with it.

REPORTED, and this is what the earlier reading cost. It set the RESULT to 6
instead, so on a D6+2 the die became a 4 ("Bright Lance counts as an
unmodified 6 (die 1 -> 4)" - the user's log). Two consequences, both wrong:
the ability CAPPED a weapon whose own maximum is 8, and it withheld itself
entirely once the result already reached 6 (a roll of 5 on a D6+2 is a 7, so
nothing was offered - while setting the die would have paid 8). On a Railgun
(D6+6) it could never be offered at all. 22 weapon profiles here print a
Damage bonus, and [MELTA] plus two enhancements add one at RUNTIME.

Where the Damage characteristic is a D3, the die is still set to 6 - an
impossible face for that die, taken literally, unchanged by the above and
noted rather than quietly capped.
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


def damage_change(squad, model, face):
    """The Damage half: the rolled DIE becomes an unmodified 6, or None if
    there is nothing to gain (it already shows one) or the ability is
    unavailable.

    Takes the die FACE, not the resulting amount - see the module docstring.
    Gating on the face is what makes this the same question the Hit and Wound
    halves ask, so one rule cannot have two disagreeing readers: a D6+2 that
    rolled a 5 is a result of 7 and still worth changing, because the die can
    still become a 6 and pay 8."""
    if not _usable(squad, model):
        return None
    if face >= BRANCHING_FATES_RESULT:
        return None
    return BRANCHING_FATES_RESULT


ACCEPT_LABEL = "Use Branching Fates"

