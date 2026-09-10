"""Krootox Riders' "Kroot Packmates".

RULE (printed, word for word):
  "Once per turn, in your opponent's Shooting phase, when a friendly KROOT
   INFANTRY unit within 6" of this unit is selected as the target of an attack,
   one unit from your army with this ability can use it. If it does, after that
   enemy unit has finished making its attacks, that unit with this ability can
   shoot as if it were your Shooting phase, but when resolving those attacks it
   can only target that enemy unit (and only if it is an eligible target)."

AWAKENED DYNASTY'S PROTOCOL OF THE VENGEFUL STARS WITHOUT THE CP. Word for word
the same second half - "can shoot as if it were your Shooting phase, but ...
can only target that enemy unit" - so it uses the same machinery:
ShootingController.start_reactive_shooting(restrict_to=...), which grants the
ORDINARY activation rather than 15.09's deliberately weaker Snap Shooting, and
whose `restrict_to` is enforced in the one place that decides what may be shot
at (_is_valid_target_squad).

THE TRIGGER IS NOW SHARED TOO. The four conditions below were written out here
when this was the only card with them; the Hexmark Destroyer's Multi-threat
Eliminator prints the same four with two words changed, so they moved to
game/reactive_bodyguard_shooting.py at the second consumer, as this repo's
convention asks. What stayed is what this card actually says:

  * "A FRIENDLY KROOT INFANTRY UNIT WITHIN 6" OF THIS UNIT" is the unit being
    SHOT AT, not the Krootox - the Krootox react on someone else's behalf. Both
    keywords, and INFANTRY is the half that does the work: another Krootox unit
    (MOUNTED) does not qualify, which is the printed reading and the reason the
    predicate is not simply "a KROOT unit".

The other three - the opponent's Shooting phase, the once-per-turn-per-ARMY
ledger, and "after that enemy unit has finished making its attacks" - are the
base class's, and its docstring says why each is written the way it is.
"""

from game.reactive_bodyguard_shooting import ReactiveBodyguardShooting

KROOT_PACKMATES_RANGE_IN = 6.0
KROOT_PACKMATES_LABEL = "Kroot Packmates"


def unit_has_kroot_packmates(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "kroot_packmates", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def is_kroot_infantry(squad):
    """Both keywords on the same model - a MOUNTED Krootox does not qualify."""
    if squad is None:
        return False
    return any(getattr(m.profile, "kroot", False) and getattr(m.profile, "infantry", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def within_range(squad, other):
    """Kept as a module function because the suite drives it directly; the
    measurement itself is the base class's."""
    return _MEASURE.within_range(squad, other)


class KrootPackmatesController(ReactiveBodyguardShooting):
    """Registered in ShootingController.target_reactions."""

    flag = "kroot_packmates"
    range_in = KROOT_PACKMATES_RANGE_IN
    label = KROOT_PACKMATES_LABEL

    def protects(self, squad):
        return is_kroot_infantry(squad)


#: A bare instance used only by the module-level within_range() above, so the
#: distance has one definition rather than two.
_MEASURE = KrootPackmatesController()
