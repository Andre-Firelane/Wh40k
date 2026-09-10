""""Chronometron" - the Chronomancer's own ability (Necrons).

RULE (printed, word for word):
  "In your Shooting phase, after this model's unit has shot, if it is not
   within Engagement Range of any enemy units, that unit can make a Normal
   move of up to 5" as if it were your Movement phase. If it does, until the
   end of the turn, that unit is not eligible to declare a charge."

THE THIRD TWIN, and it supplies only a predicate and a number.
game/tactical_acumen.py (Asurmen) and game/fire_and_fade.py (Kroot
Lone-Spear) are the two already here, and this clause is the second of them
word for word with 6" changed to 5":

  * the TRIGGER is ShootingController.on_squad_finished_shooting;
  * the MOVE is MovementController.start_post_shooting_move() with its own
    move_mode - the mode is what routes the Confirm button back to the
    controller that owns the consequence, so each ability needs its own;
  * the CONSEQUENCE is Squad.charge_locked_until_end_of_turn, which main.py
    already clears at end of turn.

THE ONE REAL DIFFERENCE FROM ITS TWO TWINS is the SUBJECT. Tactical Acumen is
"while he is leading a unit" and Fire and Fade is a LONE OPERATIVE's own move;
this one says "this model's UNIT", and the Chronomancer is a SUPPORT model
whose whole purpose is to be attached. So the predicate is 19.03's any-model
pooling, which is right in both directions: a Chronomancer standing alone is
his own unit, and once attached the move belongs to the merged unit.

"IF IT DOES" IS CONDITIONAL ON THE MOVE, so the charge lock is set at CONFIRM
and not when the offer is accepted - a cancelled move costs nothing. The same
distinction its two twins draw.
"""

from game import ai_mode, engagement
from game.attached_units import unit_has_keyword

CHRONOMETRON_MOVE_IN = 5.0
CHRONOMETRON_MOVE_MODE = "chronometron"


def unit_has_chronometron(squad):
    """Rule 19.03's any-model pooling - the printed subject is "this model's
    unit", so a lone Chronomancer and an attached one both qualify."""
    if squad is None:
        return False
    return unit_has_keyword(squad, lambda m: getattr(m.profile, "chronometron", False))


def can_use(squad, all_tokens):
    """Everything the printed text requires, in one place - so the offer and
    the move can never disagree about whether it was legal."""
    return unit_has_chronometron(squad) and not engagement.is_engaged(squad, all_tokens)


class ChronometronController:
    """The offer after shooting, and the charge lock on confirm."""

    def __init__(self, movement_controller=None, decision_manager=None,
                 all_tokens=None, game_log=None, auto_players=()):
        self.movement_controller = movement_controller
        self.decision_manager = decision_manager
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._moving_squad = None

    @property
    def is_moving(self):
        return self._moving_squad is not None

    def can_use(self, squad):
        if self.movement_controller is None or self._moving_squad is not None:
            return False
        return can_use(squad, self.all_tokens)

    def offer_after_shooting(self, squad, hit_squads=None):
        """Wired into ShootingController.on_squad_finished_shooting.

        `hit_squads` is unused: this clause triggers on having SHOT, not on
        having hit anything - the same distinction both twins draw."""
        if not self.can_use(squad):
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            # Deterministic for the AI, and the reasoning is the Chronomancer's
            # own: he is a SUPPORT model on a 5" Move with one D6 blast, and the
            # unit he rides in is a gunline. Repositioning after shooting is
            # worth more than a charge such a unit had no business declaring.
            return self._start(squad)
        self.decision_manager.request(
            squad.owner,
            f'{squad.name}: Chronometron - make a Normal move of up to '
            f'{CHRONOMETRON_MOVE_IN:g}"? It cannot declare a charge this turn if it does.',
            [("Make the move", lambda: self._start(squad)), ("Stay put", lambda: None)],
        )
        return True

    def _start(self, squad):
        self.movement_controller.select(squad.models[0])
        if self.movement_controller.selected_squad is not squad:
            return False
        self.movement_controller.start_post_shooting_move(
            squad, move_mode=CHRONOMETRON_MOVE_MODE,
            max_distance=CHRONOMETRON_MOVE_IN,
        )
        self._moving_squad = squad
        if self.game_log:
            self.game_log.add(
                f"{squad.name} uses Chronometron: a Normal move of up to "
                f"{CHRONOMETRON_MOVE_IN:g}\".")
        return True

    def confirm_move(self):
        """"If it does" - the charge lock is set only once the move has really
        been confirmed, so a cancelled move costs nothing."""
        squad = self._moving_squad
        if squad is None:
            return False
        self.movement_controller.confirm_move()
        self._moving_squad = None
        squad.charge_locked_until_end_of_turn = True
        if self.game_log:
            self.game_log.add(
                f"{squad.name} slipped through time and cannot declare a charge this turn.")
        return True

    def cancel_move(self):
        """A cancelled move costs nothing - no charge lock, and the ability is
        available again this phase."""
        if self._moving_squad is None:
            return False
        self.movement_controller.cancel_move()
        self._moving_squad = None
        return True
