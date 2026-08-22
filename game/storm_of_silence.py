"""Jain Zar's "Storm of Silence" - a datasheet ability, so its own module.

RULE (printed, word for word):
  "Each time this model makes an attack that targets a CHARACTER unit, you can
  re-roll the Wound roll."

TWO PHASES, BECAUSE THE RULE SAYS "AN ATTACK"
---------------------------------------------
Not "a ranged attack", and Jain Zar's main weapon is a melee one (Blade of
Destruction, A8), so restricting this to shooting would miss the case it is
mostly for. game/shooting.py already had a _wound_reroll_reason() lookup with
five sources in it; game/fight.py had no such lookup at all, only a hard-coded
[TWIN-LINKED] test - so that side was brought to the same shape rather than
this ability being bolted on beside the keyword. Its own methods already
claimed to be "identical" to shooting.py's; now they are.

WHOLE ROLL, not failures only - "you can re-roll the Wound roll" with no
"failed", the same wording that settled Breach and Clear, Sunforge, Assured
Destruction and Fire Support. As on the shooting side, wherever a full re-roll
is offered the failures-only subset of it is offered too, since re-rolling
fewer of a roll's dice than all of them is permitted by the same sentence.

"THIS MODEL", NOT "THIS UNIT" - so it is checked against the attacking MODEL,
not the squad. That is exact rather than a simplification here: a weapon group
is one weapon by construction (_attack_key()), and Jain Zar carries her own
datasheet's weapons, so a group containing her contains only her.

"A CHARACTER UNIT" is read off the datasheet keyword line via
attached_units.unit_has_datasheet_keyword(), which answers it per component -
so an ordinary squad with a character attached to it (19.01/19.03) counts,
which is what the pooled keyword means.
"""

from game import attached_units

STORM_OF_SILENCE_LABEL = "Storm of Silence"


def applies(attacking_model, target_squad):
    """Whether this attack is one the ability covers."""
    if attacking_model is None or target_squad is None:
        return False
    if not getattr(attacking_model.profile, "storm_of_silence", False):
        return False
    return attached_units.unit_has_datasheet_keyword(target_squad, "CHARACTER")
