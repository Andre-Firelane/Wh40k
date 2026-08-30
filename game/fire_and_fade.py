"""Kroot Lone-Spear's "Fire and Fade".

RULE (printed, word for word):
  "In your Shooting phase, after this model has shot, if it is not within
   Engagement Range of one or more enemy units, it can make a Normal move of
   up to 6". If it does, until the end of the turn, this model is not eligible
   to declare a charge."

ASURMEN'S TACTICAL ACUMEN WITH TWO CHANGES (game/tactical_acumen.py), so all
three pieces of machinery are already built and this module only supplies the
predicate:

  * the TRIGGER is ShootingController.on_squad_finished_shooting, whose
    "after that unit has shot" is word for word this clause;
  * the MOVE is MovementController.start_post_shooting_move() with a flat 6"
    cap - the same call Tactical Acumen makes, with its own move_mode, since
    the mode is what routes the Confirm button to the controller that owns the
    consequence;
  * the CONSEQUENCE is Squad.charge_locked_until_end_of_turn, which 18.04/
    18.05, The Shortened Blade and Flickerjump already use and which main.py
    already clears at end of turn.

THE TWO CHANGES:

  1. IT IS THE MODEL'S OWN ABILITY, not a "while this model is leading" grant.
     The Lone-Spear is a LONE OPERATIVE who leads nobody, so the predicate is
     a plain read of the living models rather than leader_ability().
  2. THE ENGAGEMENT RANGE CONDITION IS PRINTED HERE and is not on Tactical
     Acumen. It is checked at the moment the ability is offered - a unit locked
     in combat may not fade out of it, which is 09.02's business and would
     otherwise be a Normal move out of Engagement Range that no rule allows.

"IF IT DOES" IS CONDITIONAL ON THE MOVE, so the charge lock is set at CONFIRM
and not when the offer is accepted - a cancelled move costs nothing. Exactly
the distinction The Torchstar Gambit's own confirm_move() draws.
"""

from game.squad import ENGAGEMENT_RANGE_IN, edge_distance
from game import engagement

FIRE_AND_FADE_MOVE_IN = 6.0
FIRE_AND_FADE_MOVE_MODE = "fire_and_fade"


def unit_has_fire_and_fade(squad):
    """Read live off the living models, so it ends with the Lone-Spear."""
    if squad is None:
        return False
    return any(getattr(m.profile, "fire_and_fade", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def is_engaged(squad, all_tokens=()):
    """"not within Engagement Range of one or more enemy units" - rule 03.04.

    Delegates to game/engagement.py, which is where this sentence now lives:
    it had been written out in three modules independently, and Warhost's two
    withdrawal Stratagems made five. See that module for why the living-model
    filter differs from Squad.is_engaged()."""
    return engagement.is_engaged(squad, all_tokens)


def can_use(squad, all_tokens):
    """Everything the printed text requires, in one place - so the offer and
    the move can never disagree about whether it was legal."""
    return unit_has_fire_and_fade(squad) and not is_engaged(squad, all_tokens)


class FireAndFadeController:
    """The offer after shooting, and the charge lock on confirm.

    Structurally TacticalAcumenController (game/tactical_acumen.py) - the same
    hook, the same move call, the same "if it does" lock at confirm - so the
    two are deliberately twins rather than one generalised class: they differ
    in their predicate, and a shared class would have to carry both.
    """

    def __init__(self, movement_controller=None, decision_manager=None,
                 all_tokens=None, game_log=None, auto_players=()):
        self.movement_controller = movement_controller
        self.decision_manager = decision_manager
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.game_log = game_log
        self.auto_players = set(auto_players)
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
        having hit anything - the same distinction Tactical Acumen draws, and
        the opposite of the Lone-Spear's OTHER ability, Advanced Scouting,
        which fires only on a hit."""
        if not self.can_use(squad):
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            # Deterministic for the AI: a free 6" reposition after shooting is
            # worth more to a LONE OPERATIVE sniper than a charge it was never
            # going to declare - it has no melee weapon worth the name.
            return self._start(squad)
        self.decision_manager.request(
            squad.owner,
            f'{squad.name}: Fire and Fade - make a Normal move of up to '
            f'{FIRE_AND_FADE_MOVE_IN:g}"? It cannot declare a charge this turn if it does.',
            [("Make the move", lambda: self._start(squad)), ("Stay put", lambda: None)],
        )
        return True

    def _start(self, squad):
        self.movement_controller.select(squad.models[0])
        if self.movement_controller.selected_squad is not squad:
            return False
        self.movement_controller.start_post_shooting_move(
            squad, move_mode=FIRE_AND_FADE_MOVE_MODE, max_distance=FIRE_AND_FADE_MOVE_IN,
        )
        self._moving_squad = squad
        if self.game_log:
            self.game_log.add(
                f"{squad.name} uses Fire and Fade: a Normal move of up to "
                f"{FIRE_AND_FADE_MOVE_IN:g}\".")
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
                f"{squad.name} faded back and cannot declare a charge this turn.")
        return True

    def cancel_move(self):
        """A cancelled move costs nothing - no charge lock, and the ability is
        available again this phase."""
        if self._moving_squad is None:
            return False
        self.movement_controller.cancel_move()
        self._moving_squad = None
        return True
