"""Deffkoptas' Deff from Above (2026-09 Ork codex, stage E3d).

RULE (verbatim, rules/orks/Deffkoptas.md):
  "Deff from Above: In your Shooting phase, if this unit made an ingress move
   this turn, this unit's ranged attacks have +1 to hit rolls."

"MADE AN INGRESS MOVE THIS TURN" is IngressController.ingressed_this_turn - the
set Windrider Host's Death from on High reads for "set upon the battlefield from
Reserves this turn", written where an arrival is confirmed and cleared in
main.py's end-of-turn block. NOT Squad.set_up_this_turn, which every placement
sets (deployment and disembarking included), and NOT ingressed_this_phase, which
is the right fact on the Movement phase's clock rather than the turn's. A Deep
Strike arrival IS an ingress move (rule 24.09 says so), and so is the unit's
return after its own Aerial Manoover.

"IN YOUR SHOOTING PHASE" excludes reactive shooting: a Fire Overwatch in the
opponent's turn resolves through the same controller, so the attack step hands
over its `reactive` flag and this answers nothing for it.

A BONUS, so a -1 on the threshold (game/modifiers.py's convention). Appended in
ShootingController._hit_modifiers() BEFORE the ignore-modifier filters, like
every other bonus there. "This unit" is rule 19.04's unit-wide reading.
"""

from game.modifiers import Modifier
from game.squad import unit_wide_ability

DEFF_FROM_ABOVE_NAME = "Deff from Above"


def applies(squad, ingress_controller, reactive=False):
    if squad is None or reactive or ingress_controller is None:
        return False
    if not unit_wide_ability(squad, "deff_from_above"):
        return False
    return squad in getattr(ingress_controller, "ingressed_this_turn", ())


def hit_modifiers(squad, ingress_controller, reactive=False):
    """[Modifier(-1, "Deff from Above")] while the rule applies, else []."""
    if not applies(squad, ingress_controller, reactive):
        return []
    return [Modifier(-1, DEFF_FROM_ABOVE_NAME)]
