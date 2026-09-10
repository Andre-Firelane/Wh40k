""""Evasion Engrams" - the Tomb Blades' own ability (Necrons).

RULE (printed, word for word):
  "In your Shooting phase, after this unit has shot, it can make a Normal move
   of up to 6". If it does, until the end of the turn, this unit is not
   eligible to declare a charge."

THE FIFTH MODULE OF THIS SHAPE, and that is worth writing down rather than
just doing again. The family is now:

  game/tactical_acumen.py        Asurmen        6"  leader grant   no ER clause
  game/fire_and_fade.py          Lone-Spear     6"  own ability    ER clause
  game/warhost_fire_and_fade.py  Warhost        6"  stratagem      + embark lock
  game/chronometron.py           Chronomancer   5"  unit ability   ER clause
  game/evasion_engrams.py        Tomb Blades    6"  unit ability   no ER clause

game/fire_and_fade.py argues for twins over one generalised class ("they
differ in their predicate, and a shared class would have to carry both"),
which was a fair reading at two. At five the varying parts have resolved into
exactly four knobs - predicate, distance, whether the printed text carries an
Engagement Range clause, and which locks apply on confirm - so an extraction
is now overdue by this repo's own "extract at the SECOND consumer" rule. It is
NOT done here: it would rewrite four working modules and their suites inside a
datasheet stage, which is how a refactor gets smuggled in. Recorded in
CLAUDE.md as a named candidate with that knob list instead.

NO ENGAGEMENT RANGE CLAUSE, and that is the printed text and not an oversight.
Fire and Fade and the Chronometron both say "if it is not within Engagement
Range"; this one does not, and neither does Tactical Acumen. So a Tomb Blade
squad locked in combat MAY take this move - which reads odd next to its two
neighbours and is what the sheet says. Asserted in the suite so it cannot be
"fixed" into agreement with them.

"IF IT DOES" IS CONDITIONAL ON THE MOVE, so the charge lock is set at CONFIRM
and not when the offer is accepted - a cancelled move costs nothing.
"""

from game import ai_mode
from game.attached_units import unit_has_keyword

EVASION_ENGRAMS_MOVE_IN = 6.0
EVASION_ENGRAMS_MOVE_MODE = "evasion_engrams"


def unit_has_evasion_engrams(squad):
    """Rule 19.03's any-model pooling. Tomb Blades lead nothing and are led by
    nothing today, so this collapses to their own models - written this way so
    it keeps meaning "this unit" if that ever changes."""
    if squad is None:
        return False
    return unit_has_keyword(squad, lambda m: getattr(m.profile, "evasion_engrams", False))


def can_use(squad, all_tokens=()):
    """`all_tokens` is accepted and DELIBERATELY UNUSED: every other member of
    this family takes it because its printed text has an Engagement Range
    clause to check, and this one has none. Keeping the signature identical is
    what lets the eventual extraction treat the clause as a knob rather than as
    a different function."""
    return unit_has_evasion_engrams(squad)


class EvasionEngramsController:
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
        having hit anything - the same distinction every twin draws."""
        if not self.can_use(squad):
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            # Deterministic for the AI, and for this datasheet the trade is
            # one-sided: Tomb Blades are a M12" gun platform whose melee is one
            # S4 attack per model. A 6" reposition after shooting is worth more
            # than a charge they should not be declaring.
            return self._start(squad)
        self.decision_manager.request(
            squad.owner,
            "%s: Evasion Engrams - make a Normal move of up to %g\"? It cannot "
            "declare a charge this turn if it does." % (squad.name, EVASION_ENGRAMS_MOVE_IN),
            [("Make the move", lambda: self._start(squad)), ("Stay put", lambda: None)],
        )
        return True

    def _start(self, squad):
        self.movement_controller.select(squad.models[0])
        if self.movement_controller.selected_squad is not squad:
            return False
        self.movement_controller.start_post_shooting_move(
            squad, move_mode=EVASION_ENGRAMS_MOVE_MODE,
            max_distance=EVASION_ENGRAMS_MOVE_IN,
        )
        self._moving_squad = squad
        if self.game_log:
            self.game_log.add(
                "%s uses Evasion Engrams: a Normal move of up to %g\"."
                % (squad.name, EVASION_ENGRAMS_MOVE_IN))
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
                "%s evaded and cannot declare a charge this turn." % squad.name)
        return True

    def cancel_move(self):
        """A cancelled move costs nothing - no charge lock, and the ability is
        available again this phase."""
        if self._moving_squad is None:
            return False
        self.movement_controller.cancel_move()
        self._moving_squad = None
        return True
