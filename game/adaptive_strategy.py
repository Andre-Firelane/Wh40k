"""Adaptive Strategy - the Royal Warden's own ability.

RULE (printed, word for word):

  "This model's unit is eligible to shoot and declare a charge in a turn in
   which it Fell Back."

BOTH HALVES, and that is the whole content of this file. Rule 09.07 bans two
things after a Fall Back, and game/move_exceptions.py keeps them as two
separate questions because the printed sources disagree about which they lift:
Battlesuit Support System and Agile Combatant say only "shoot", the Triarch
Praetorians' Relentless Combatants says only "declare a charge", Hovering Death
and Full Throttle say both.

This is the SECOND Necron source of the exemption and the first that says both,
so it is the only name that appears in both folds. A copy of its Triarch
neighbour - the obvious thing to write, one stage later, in the same faction -
would lift the charge ban and silently leave the shooting ban standing.
"""


def _living(squad):
    return [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]


def squad_has_adaptive_strategy(squad):
    """Rule 19.03 pooling: the printed subject is "this MODEL's unit", so one
    Royal Warden merged into Necron Warriors exempts the whole unit."""
    if squad is None:
        return False
    return any(getattr(m.profile, "adaptive_strategy", False) for m in _living(squad))
