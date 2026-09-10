"""The Hexmark Destroyer's "Multi-threat Eliminator" (Necrons).

RULE (printed, word for word):
  "Once per turn, in your opponent's Shooting phase, when an enemy unit makes a
   ranged attack that targets a friendly NECRONS unit within 3" of a model with
   this ability, after that enemy unit has shot, one model with this ability
   that is within 3" of that target can shoot as if it were your Shooting
   phase, but it must target only that enemy unit when doing so, and can only
   do so if that enemy unit is an eligible target."

KROOT PACKMATES WITH TWO WORDS CHANGED, which is why the four-part trigger both
print now lives in game/reactive_bodyguard_shooting.py rather than a second
time here. What this card owns is exactly the two:

  * 3", not 6".
  * "a friendly NECRONS unit", not "a friendly KROOT INFANTRY unit" - and
    NECRONS is a faction, so it is read the way every other "a friendly NECRONS
    unit" in this faction is read: the army rule Reanimation Protocols is
    printed on every Necron datasheet, so its flag IS the faction test (see
    game/illuminor.py, which settled that reading).

"WITHIN 3" OF A MODEL WITH THIS ABILITY" AND "ONE MODEL WITH THIS ABILITY THAT
IS WITHIN 3" OF THAT TARGET" ARE THE SAME MEASUREMENT, printed twice - once to
say which friendly units are covered, once to say which carrier may answer. The
base class measures model to model on both sides, so one test answers both.

THE BEARER'S OWN UNIT IS COVERED, and that is not a special case: a Hexmark
Destroyer is himself a friendly NECRONS unit within 3" of a model with this
ability (0"), so an enemy shooting HIM triggers it. That is what the printed
text says, and it is worth stating because "bodyguard reaction" is the mental
model the shared base class is named for.

LONE OPERATIVE MAKES THAT LAST POINT MATTER LESS THAN IT LOOKS: he is printed
with 24.24, so most of the time nothing can target him at all while a friendly
unit stands nearby - which is precisely when a friendly unit IS being shot
instead, and this ability answers.
"""

from game.reactive_bodyguard_shooting import ReactiveBodyguardShooting

MULTI_THREAT_ELIMINATOR_RANGE_IN = 3.0
MULTI_THREAT_ELIMINATOR_LABEL = "Multi-threat Eliminator"


def unit_has_multi_threat_eliminator(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "multi_threat_eliminator", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def is_necron_unit(squad):
    """"a friendly NECRONS unit" - the army-rule flag as the faction test, the
    reading game/illuminor.py settled for the identical phrase."""
    if squad is None:
        return False
    return any(getattr(m.profile, "reanimation_protocols", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


class MultiThreatEliminatorController(ReactiveBodyguardShooting):
    """Registered in ShootingController.target_reactions and in
    on_squad_finished_shooting, exactly like its Kroot twin."""

    flag = "multi_threat_eliminator"
    range_in = MULTI_THREAT_ELIMINATOR_RANGE_IN
    label = MULTI_THREAT_ELIMINATOR_LABEL

    def protects(self, squad):
        return is_necron_unit(squad)
