"""The Triarch Stalker's own ability "Targeting Relay" (Necrons).

RULE (printed, word for word):

  "In your Shooting phase, each time this model is selected to shoot, after
  resolving its attacks, select one enemy unit that was hit by one or more of
  those attacks. Until the end of the phase, that unit cannot have the Benefit
  of Cover."

THE SECOND ABILITY OF THIS EXACT SHAPE, and the reason game/cover_denial.py
exists - the Defiler's Barrage of Filth prints the same sentence under another
name, so the shared head was extracted here rather than copied. The base class
docstring carries the reasoning; only two things are this datasheet's own.

  * "EACH TIME THIS MODEL IS SELECTED TO SHOOT, AFTER RESOLVING ITS ATTACKS"
    is the Defiler's "after this model has shot" in longer words. It is the
    same moment: ShootingController.on_squad_finished_shooting fires once per
    shooting activation, which is precisely one selection-and-resolution. Said
    out loud because the two wordings look different enough to invite a second
    seam, and a second seam would fire twice or not at all.
  * THE STALKER IS A ONE-MODEL UNIT, so "this model" and "this unit" cannot
    come apart here - the base class asks per SQUAD because a shooting
    activation is per squad in this engine, and there is no Necron datasheet on
    which a Targeting Relay bearer stands beside models without it. A future
    multi-model carrier would need a per-model activation this engine does not
    have; named rather than half-built.
"""

from game.cover_denial import CoverDenialAfterShooting

TARGETING_RELAY_LABEL = "Targeting Relay"


class TargetingRelayController(CoverDenialAfterShooting):
    flag = "targeting_relay"
    label = TARGETING_RELAY_LABEL
