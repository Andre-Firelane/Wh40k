"""Hypercrypt Legion Stratagem: Cosmic Precision (1CP).

RULE (verbatim, rules/necrons/detachments/Hypercrypt Legion.md):
  WHEN:         Your Movement phase.
  TARGET:       One NECRONS unit from your army (excluding MONSTER units) that is
                arriving using an ingress move this phase.
  EFFECT:       Your unit can be set up anywhere on the battlefield that is more
                than 6" horizontally away from all enemy models.
  RESTRICTIONS: A unit targeted with this Stratagem is not eligible to declare a
                charge in the same turn.

THE EFFECT IS THE RELAXED ARRIVAL THIS ENGINE ALREADY HAS. The Shortened Blade
(game/shortened_blade.py) and Baharroth's Cloudstrider print the same EFFECT
word for word, and game/ingress.py answers it through one field,
IngressController.relaxed_arrival_squad: no board-edge band, no opponent's
deployment zone ban ("anywhere on the battlefield", user decision - the Confirm,
the overlay and the AI candidate sweep agree since this stage), and 6" in place
of rule 20.04's 8". So this module arms that field for the arrival in progress
and does nothing else to the placement.

WHAT IS DIFFERENT FROM THE SHORTENED BLADE is only the TARGET line: NECRONS, not
T'AU EMPIRE BATTLESUIT, and ANY ingress move, not only a Deep Strike one. That
second word matters more than it looks - a Necron Warriors unit arriving from
Strategic Reserves has no Deep Strike, so for it this lifts the 6"-of-an-edge
band and the zone ban, where for a Deep Striker it buys only the 2".

"YOUR Movement phase" is the turn owner's, which also refuses Rapid Ingress
(15.07): that arrival happens in the OPPONENT's Movement phase.

NEVER OFFERED WHEN IT BUYS NOTHING:
  * an arrival that already uses the relaxed rule (bought, or Cloudstrider);
  * an arrival through the Monolith's Eternity Gate. game/ingress.py asks the
    gate FIRST in every one of its three placement questions, so the gate's own
    rule ("wholly within 6" of this unit and unengaged") would win and the CP
    would change nothing.

ITS BUTTON IS ON THE ARRIVAL SCREEN (PANEL_SCREEN), not the unit screen: the
TARGET is a placement in progress, and while a placement is open the panel
draws the Set Up screen and never reaches the unit screen. See
game/proactive_stratagems.py.

THE RESTRICTIONS land on Squad.charge_locked_until_end_of_turn, the shared
no-charge lock rules 18.04/18.05 use and main.py already clears at the end of
the turn. That is also why the Monolith's own lock is a SEPARATE field now:
Dimensional Corridor lifts the gate's lock, and must not lift this one.

THE AI buys it inside _auto_ingress_squad() (ai/agent_driver.py) when the best
landing spot with the relaxed rule scores clearly better than without it.
"""

from game import attached_units, necron_detachments
from game.ingress import INGRESS_MIN_ENEMY_DISTANCE_IN, SHORTENED_BLADE_MIN_ENEMY_DISTANCE_IN
from game.proactive_stratagems import ARRIVAL_SCREEN
from game.stratagems import Stratagem
from game.turn import PHASE_MOVEMENT

COSMIC_PRECISION_NAME = "Cosmic Precision"
COSMIC_PRECISION_CP = 1
SETTING = "HYPERCRYPT_LEGION_PLAYERS"
#: "more than 6" horizontally away from all enemy models" - game/ingress.py's
#: one definition of the relaxed distance, not a second literal.
COSMIC_PRECISION_MIN_ENEMY_DISTANCE_IN = SHORTENED_BLADE_MIN_ENEMY_DISTANCE_IN


def is_monster_unit(squad):
    """"(excluding MONSTER units)" - rule 19.03's any-model keyword pooling."""
    return attached_units.unit_has_keyword(squad, lambda m: getattr(m.profile, "monster", False))


class CosmicPrecisionController:
    """A registered proactive Stratagem on the ARRIVAL screen."""

    PANEL_SCREEN = ARRIVAL_SCREEN

    def __init__(self, stratagem_controller, ingress_controller=None, setup_controller=None,
                 turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.ingress_controller = ingress_controller
        self.setup_controller = setup_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        #: Units this Stratagem armed, so the arrival screen can say so - the
        #: relaxed field alone cannot tell Cosmic Precision from Cloudstrider.
        self._armed = set()
        self._stratagem = Stratagem(name=COSMIC_PRECISION_NAME, cp_cost=COSMIC_PRECISION_CP,
                                    effect=self._apply)

    # ------------------------------------------------------------- the button
    def panel_label(self, squad):
        return (f"{COSMIC_PRECISION_NAME} ({COSMIC_PRECISION_CP} CP) - arrive anywhere more than "
                f'{COSMIC_PRECISION_MIN_ENEMY_DISTANCE_IN:.0f}" from the enemy')

    def panel_note(self, squad):
        ic = self.ingress_controller
        if squad is None or ic is None or id(squad) not in self._armed:
            return None
        if ic.relaxed_arrival_squad is not squad:
            return None
        return (f"{COSMIC_PRECISION_NAME} is active: set up anywhere more than "
                f'{COSMIC_PRECISION_MIN_ENEMY_DISTANCE_IN:.0f}" from all enemy models. '
                "This unit cannot declare a charge this turn.")

    def reset_phase(self):
        self._armed.clear()

    def can_use(self, squad):
        return self._eligible(squad, require_arriving=True)

    def could_target(self, squad):
        """can_use() without "is arriving using an ingress move RIGHT NOW" - for
        the AI, which decides before it opens the arrival that makes that
        clause true (ai/agent_driver.py _auto_ingress_squad)."""
        return self._eligible(squad, require_arriving=False)

    def _eligible(self, squad, require_arriving):
        ic = self.ingress_controller
        tt = self.turn_tracker
        if squad is None or ic is None or tt is None or self.stratagem_controller is None:
            return False
        if tt.phase != PHASE_MOVEMENT or tt.turn_owner != squad.owner:
            return False
        if require_arriving and not ic.is_ingressing(squad):
            return False
        if ic._uses_relaxed_arrival(squad):
            return False     # already relaxed - a second purchase buys nothing
        if ic.eternity_gate_squad is squad:
            return False     # the gate's rule is asked first and would win
        if not necron_detachments.has_detachment(squad.owner, SETTING):
            return False
        if not necron_detachments.is_necrons_unit(squad):
            return False
        if is_monster_unit(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _apply(self, controller, player, targets):
        squad = targets[0]
        self.ingress_controller.relaxed_arrival_squad = squad
        self._armed.add(id(squad))
        # RESTRICTIONS: "not eligible to declare a charge in the same turn".
        squad.charge_locked_until_end_of_turn = True
        # The overlay caches its legality mask per placement, and the legal
        # ground is exactly what changed (SetupController.placement_generation).
        if self.setup_controller is not None:
            self.setup_controller.invalidate_placement()
        if self.game_log is not None:
            self.game_log.add(
                f"{player}: {COSMIC_PRECISION_NAME} - {squad.name} can be set up anywhere on the "
                f'battlefield more than {COSMIC_PRECISION_MIN_ENEMY_DISTANCE_IN:.0f}" from all enemy '
                f'models instead of {INGRESS_MIN_ENEMY_DISTANCE_IN:.0f}", and cannot declare a '
                "charge this turn.")
