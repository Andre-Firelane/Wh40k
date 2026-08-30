"""How far a hidden unit's detection range reaches, after everything that
changes it.

THE SEVENTEENTH EXTRACTION, made at the second and third consumer at once.

Rule 13.09's detection range used to be a base distance plus exactly one
adjustment, and game/status_effects.py's is_detectable() took that one source
as a named argument (`prey_marks`, Auxiliary Cadre's Harnessed Alien Instincts).
Two Advanced Acquisition Cadre Enhancements now change the same number:

  * Negation Emitters  -3" on the bearer's own unit (game/enh_negation_emitters.py)
  * Unmasking Suite    +9" on a marked enemy unit  (game/enh_unmasking_suite.py)

Three arguments named after three particular abilities, summed at the call
site, is how the next one ends up added to only one of the two call sites -
which is exactly the shape of the bug already sitting in this area (see BLIND
CALLER below). So the sum lives here, is_detectable() asks for it once, and a
fourth source changes nothing at either call site.

WHICH DIRECTION EACH SOURCE GOES
---------------------------------
Detection range in this engine belongs to the HIDDEN model: is_detectable()
asks whether an observer stands within the hidden model's own detection range.
So a POSITIVE bonus makes the unit easier to see (it is visible from further
away) and a NEGATIVE one hides it better. Both printed texts read naturally
that way round - a prey-marked or scanner-lit enemy is exposed, Negation
Emitters mask their own bearer - but the sign is the easy thing to invert, so
each source states its own reading and each is measured in both bands (the
15" default and the 12" house rule) rather than only one.

A FLOOR AT ZERO. Nothing printed stacks far enough to reach it today (-3" off
the 12" house rule is 9"), but a negative detection range would silently invert
the comparison rather than failing, so it is clamped and said so.

A BLIND CALLER, NAMED RATHER THAN QUIETLY FIXED
------------------------------------------------
game/greater_good.py's eligible_targets() calls is_detectable() WITHOUT any of
these sources, so For The Greater Good's own target eligibility measures the
printed distance while game/shooting.py measures the adjusted one. That
predates this extraction (it was already true of `prey_marks` alone) and it is
a real inconsistency: an Observer can be refused a mark on a unit its own army
could legally shoot. It is left alone here because fixing it changes which
units may be Spotted - a behaviour change in the army rule, not in this fold -
and because doing it under cover of an extraction is exactly how a refactor
stops being verifiable. Recorded so the next reader does not have to rediscover
it.
"""


def bonus_in(squad, prey_marks=None, unmasking=None):
    """The total change to `squad`'s detection range, in inches.

    Every source is optional and defaults to absent, so a caller that knows
    about none of them measures the printed distance - the same arrangement
    every other controller argument in game/status_effects.py uses.
    """
    from game import (enh_negation_emitters, far_reaching_doom,
                      outcast_casting_back_the_veil)
    total = 0.0
    if prey_marks is not None:
        total += prey_marks.detection_bonus_in(squad)
    if unmasking is not None:
        total += unmasking.detection_bonus_in(squad)
    total += enh_negation_emitters.detection_bonus_in(squad)
    # Path of the Outcast's Far-Reaching Doom - the fourth source, and the
    # second attached this way rather than as a named argument, so neither of
    # this function's two call sites had to grow a parameter. It is live only
    # while a Rangers/Shroud Runners unit is inside its "selected to shoot"
    # window, and it is POSITIVE on the shooter's ENEMIES: detection range
    # belongs to the hidden model, so more of it means visible from further
    # away. See game/far_reaching_doom.py.
    total += far_reaching_doom.detection_bonus_in(squad)
    # Path of the Outcast's Casting Back the Veil - the FIFTH source, and the
    # same +6" as that detachment's own rule above. Deliberately a separate
    # term rather than shared with it: the rule's window closes when the unit
    # has shot, this mark never expires, and because they ADD a unit hit while
    # the window is open is at +12" - which is what two printed effects each
    # saying "+6" should do.
    total += outcast_casting_back_the_veil.detection_bonus_in(squad)
    return total


def apply(base_range_in, squad, prey_marks=None, unmasking=None):
    """`base_range_in` adjusted by every source, floored at 0."""
    return max(0.0, base_range_in + bonus_in(squad, prey_marks=prey_marks, unmasking=unmasking))
