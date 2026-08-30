"""Armoured Warhost Stratagem: Soulsight (1CP).

RULE (verbatim, rules/aeldari/detachments/Armoured Warhost.md):
  WHEN:   Your Shooting phase, when a friendly AELDARI VEHICLE unit is
          selected to shoot.
  TARGET: That AELDARI VEHICLE unit.
  EFFECT: Your unit's attacks can re-roll:
            - One hit roll.
            - One wound roll.
            - One damage roll.
  RESTRICTIONS: none printed.

THE THIRD ABILITY OF THE TARGETING ARRAY SHAPE, so it is an entry in
game/activation_reroll.py's ABILITIES tuple and not a new mechanism. That module
already owns the panel button, the click-a-die selection, the "a die is never
re-rolled twice" gate, and the per-activation ledger; it was extracted at the
second consumer (Crystal Matrix) precisely so a third would cost a line.

WHAT THE THIRD ENTRY MADE THE REGISTRY LEARN, and why neither change is
cosmetic:

  * A THIRD ROLL KIND. Targeting Array and Crystal Matrix both print "one Hit
    roll ... one Wound roll"; this one adds a Damage roll. REROLLABLE_KINDS was
    a single module constant, so widening it in place would have quietly let
    Targeting Array re-roll a Damage roll its text never mentions. Each ability
    now names its OWN kinds and the module constant is only the union, used to
    reject a roll no ability could touch before asking which one the unit has.
    game/command_reroll.py already reached DAMAGE_ROLL, so the die-selection UI
    needed nothing.
  * A FLAG ON THE SQUAD RATHER THAN THE PROFILE. The other two are printed on a
    datasheet - they are what the model IS, so they are UnitProfile fields.
    This is bought for one activation, so it latches on the Squad. Same ledger,
    different shelf, one `on_squad` bit to say which.

"ONE OF EACH", NOT "ONE OF THE THREE": the printed text is a bulleted list, not
an "or", so `shared_use=False` - the same distinction that separates Crystal
Matrix from Targeting Array, and the reason that field exists at all.

THE WINDOW IS THE ACTIVATION. "when a unit is SELECTED TO SHOOT" opens it and
the activation closes it, which is exactly the pair of seams
ActivationRerollController already hangs on (start_shooting /
_actually_finish_squad). So the Stratagem sets its flag and the existing ledger
does the rest - including forgetting it, since begin_activation() clears per
squad.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import aeldari_detachments, skilled_crews
from game.stratagems import Stratagem

SOULSIGHT_NAME = "Soulsight"
SOULSIGHT_CP = 1


def is_active(squad):
    return bool(getattr(squad, "soulsight_active", False))


def applies(squad):
    """"a friendly AELDARI VEHICLE unit" of a player fielding it."""
    if squad is None or not skilled_crews.has_detachment(getattr(squad, "owner", None)):
        return False
    if not aeldari_detachments.is_aeldari_unit(squad):
        return False
    return any(getattr(m.profile, "vehicle", False)
               for m in (getattr(squad, "models", ()) or ()) if not m.is_dead())


def reset_phase(squads=()):
    for squad in squads or ():
        if squad is not None:
            squad.soulsight_active = False


class SoulsightController:
    """A panel button, bought during the unit's own activation."""

    def __init__(self, stratagem_controller, shooting_controller=None,
                 turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.shooting_controller = shooting_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name=SOULSIGHT_NAME, cp_cost=SOULSIGHT_CP, effect=self._grant,
        )

    def panel_label(self, squad):
        return ("%s (%d CP) - re-roll one hit, one wound and one damage roll"
                % (SOULSIGHT_NAME, SOULSIGHT_CP))

    def can_use(self, squad):
        from game.turn import PHASE_SHOOTING
        if squad is None or self.stratagem_controller is None or self.turn_tracker is None:
            return False
        if self.turn_tracker.phase != PHASE_SHOOTING:
            return False
        if squad.owner != self.turn_tracker.active_player:
            return False                      # "YOUR Shooting phase"
        if is_active(squad):
            return False
        if not applies(squad):
            return False
        # "when a unit IS SELECTED TO SHOOT" - the opposite gate from every
        # other proactive Stratagem in this batch, which say "has NOT been
        # selected to shoot this phase". This one is bought during the
        # activation it applies to, so the unit has to BE the active one.
        if self.shooting_controller is None or self.shooting_controller.active_squad is not squad:
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.soulsight_active = True
            if self.game_log is not None:
                self.game_log.add(
                    "%s: %s may re-roll one hit roll, one wound roll and one "
                    "damage roll during this activation."
                    % (SOULSIGHT_NAME, squad.name))
