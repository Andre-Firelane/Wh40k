"""Guardian Battlehost Stratagem: Warding Salvoes (1CP, Battle Tactic).

RULE (verbatim, rules/aeldari/detachments/Guardian Battlehost.md):
  WHEN:   Your Shooting phase or the Fight phase.
  TARGET: One DIRE AVENGERS or GUARDIANS unit from your army that has not been
          selected to shoot or fight this phase.
  EFFECT: Until the end of the phase, each time a model in your unit makes an
          attack that targets an enemy unit within range of one or more
          objective markers, you can re-roll the Wound roll.
  RESTRICTIONS: none printed.

THE CONDITION IS ON THE TARGET, NOT ON THE PURCHASE. "an enemy unit within
range of one or more objective markers" is measured when the attack is made, so
the same unit that bought this re-rolls against a target standing on an
objective and does not against one that is not. That is the shape
game/reavers_of_the_void.py and game/implacable_eradication.py already have -
offers_full_reroll(squad, target_squad, objectives) - and both attack steps
already hold `self.objectives`.

"WITHIN RANGE OF", NOT "ON". objectives.is_within_range_of_objective() carries
the printed 3" buffer; is_on_objective() is footprint overlap with no buffer.
The two are a recorded user correction in this repo, and this text says
"within range of".

BOTH PHASES. "Your Shooting phase or the Fight phase" - and note the
asymmetry, which is printed and deliberate: YOUR Shooting phase, but THE Fight
phase, which belongs to nobody. So the Fight-phase half is not gated on whose
turn it is.

A PLAIN "YOU CAN RE-ROLL THE WOUND ROLL", so it is NOT a
game/reroll_scope.py entry: there is no "instead" clause, so the player gets
the ordinary failures-or-whole offer rather than a ones-or-whole one. Pinned as
an absence, the only place that shows.
"""

from game import aeldari_detachments, defend_at_all_costs
from game.objectives import is_within_range_of_objective
from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT, PHASE_SHOOTING

WARDING_SALVOES_NAME = "Warding Salvoes"
WARDING_SALVOES_CP = 1

#: The two keyword lines this Stratagem names. A SUBSET of the detachment
#: rule's four - Defend at All Costs also names SUPPORT WEAPON and WAR WALKERS,
#: this does not - so the lists are separate rather than shared.
WARDING_SALVOES_KEYWORDS = ("DIRE AVENGERS", "GUARDIANS")


def is_active(squad):
    return bool(getattr(squad, "warding_salvoes_active", False))


def eligible_unit(squad):
    """"One DIRE AVENGERS or GUARDIANS unit from your army"."""
    if squad is None or not defend_at_all_costs.has_detachment(getattr(squad, "owner", None)):
        return False
    if not aeldari_detachments.is_aeldari_unit(squad):
        return False
    from game.attached_units import unit_has_datasheet_keyword
    return any(unit_has_datasheet_keyword(squad, k) for k in WARDING_SALVOES_KEYWORDS)


def offers_reroll(squad, target_squad, objectives=()):
    """Whether this unit's Wound roll against THIS target may be re-rolled."""
    if not is_active(squad) or target_squad is None:
        return False
    return bool(objectives) and is_within_range_of_objective(target_squad, objectives)


def reset_phase(squads=()):
    for squad in squads or ():
        if squad is not None:
            squad.warding_salvoes_active = False


class WardingSalvoesController:
    """A panel button, in either of the two printed phases."""

    def __init__(self, stratagem_controller, shooting_controller=None,
                 fight_controller=None, turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.shooting_controller = shooting_controller
        self.fight_controller = fight_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name=WARDING_SALVOES_NAME, cp_cost=WARDING_SALVOES_CP, effect=self._grant,
        )

    def panel_label(self, squad):
        return ("%s (%d CP) - re-roll Wound rolls against units on objectives"
                % (WARDING_SALVOES_NAME, WARDING_SALVOES_CP))

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None or self.turn_tracker is None:
            return False
        phase = self.turn_tracker.phase
        if phase == PHASE_SHOOTING:
            # "YOUR Shooting phase".
            if squad.owner != self.turn_tracker.active_player:
                return False
            if self.shooting_controller is not None \
                    and self.shooting_controller.active_squad is squad:
                return False          # "has not been selected to shoot"
        elif phase == PHASE_FIGHT:
            # "THE Fight phase" - it belongs to nobody, so no owner check.
            if self.fight_controller is not None \
                    and self.fight_controller.fighting_squad is squad:
                return False          # "has not been selected to fight"
        else:
            return False
        if is_active(squad):
            return False
        if not eligible_unit(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.warding_salvoes_active = True
            if self.game_log is not None:
                self.game_log.add(
                    "%s: %s may re-roll Wound rolls against units within range of "
                    "an objective marker this phase."
                    % (WARDING_SALVOES_NAME, squad.name))
