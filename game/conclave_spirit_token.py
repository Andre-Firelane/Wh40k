"""Spirit Conclave Stratagem: Spirit Token (1CP, Strategic Ploy).

RULE (verbatim, rules/aeldari/detachments/Spirit Conclave.md):
  WHEN:   Start of your Movement phase.
  TARGET: One WRAITHBLADES or WRAITHGUARD unit from your army.
  EFFECT: Select one objective marker you control that your unit is within
          range of. That objective marker remains under your control until your
          opponent's Level of Control over that objective marker is greater
          than yours at the end of a phase.
  RESTRICTIONS: none printed.

THIS IS RULE 14.03's SECURED, WORD FOR WORD, so it reuses that mechanism rather
than inventing a second kind of sticky control. Objective.secure_for() has
carried exactly this meaning since before there was anything to call it, and it
now has three callers - Advanced Acquisition Cadre's Marker Beacon, Expert
Fieldcraft, and this. Anything else would be a parallel notion of "who holds
this" for level_of_control() to disagree with.

"ONE OBJECTIVE MARKER YOU CONTROL" is checked, not assumed. The Stratagem
cannot plant a token on contested or enemy-held ground; it makes control you
ALREADY have durable. A version that skipped the check would read as a much
stronger card and would still pass any test that used an uncontested objective.

"THAT YOUR UNIT IS WITHIN RANGE OF" uses objectives.is_within_range_of_objective
(), the same 3" every other objective clause in this engine measures - Burden of
Trust and Cleanse both go through it. Not re-derived here.

"START OF YOUR MOVEMENT PHASE" is a moment, not a window: offered once at that
boundary rather than as a button that lingers all phase. It is a PANEL BUTTON
all the same, because the player picks which unit and which marker - but
can_use() closes as soon as the unit has been selected to move, which is what
"start of" means in a phase this engine does not otherwise subdivide.

WRAITHBLADES OR WRAITHGUARD, and NOT Wraithlord - a narrower list than Blades
from Beyond's next door, and narrower than the WRAITH CONSTRUCT keyword. Read
at the two names, with a Wraithlord as an explicit negative case.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import aeldari_detachments, shepherds_of_the_dead
from game.objectives import is_within_range_of_objective
from game.stratagems import Stratagem
from game.turn import PHASE_MOVEMENT

SPIRIT_TOKEN_NAME = "Spirit Token"
SPIRIT_TOKEN_CP = 1

#: "One WRAITHBLADES or WRAITHGUARD unit" - not WRAITHLORD, and not the
#: WRAITH CONSTRUCT keyword.
SPIRIT_TOKEN_KEYWORDS = ("WRAITHBLADES", "WRAITHGUARD")

SETTING = shepherds_of_the_dead.SETTING


def has_detachment(player):
    return aeldari_detachments.has_detachment(player, SETTING)


def eligible_unit(squad):
    if squad is None or not has_detachment(getattr(squad, "owner", None)):
        return False
    from game.attached_units import unit_has_datasheet_keyword
    return any(unit_has_datasheet_keyword(squad, k) for k in SPIRIT_TOKEN_KEYWORDS)


def objectives_for(squad, objectives=()):
    """"one objective marker YOU CONTROL that your unit is WITHIN RANGE of" -
    two clauses, both checked."""
    if squad is None:
        return []
    out = []
    for objective in objectives or ():
        if getattr(objective, "controlled_by", None) != squad.owner:
            continue
        if getattr(objective, "secured_by", None) == squad.owner:
            continue               # already Secured - nothing left to buy
        # The helper takes a LIST of objectives, not one - the same shape
        # Burden of Trust and Cleanse call it with.
        if is_within_range_of_objective(squad, [objective]):
            out.append(objective)
    return out


class SpiritTokenController:
    """A start-of-Movement-phase panel button."""

    def __init__(self, stratagem_controller, objectives=None,
                 movement_controller=None, turn_tracker=None,
                 decision_manager=None, game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.objectives = objectives if objectives is not None else []
        self.movement_controller = movement_controller
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = set(auto_players)
        self._pending = {}
        self._stratagem = Stratagem(
            name=SPIRIT_TOKEN_NAME, cp_cost=SPIRIT_TOKEN_CP, effect=self._secure,
        )

    def panel_label(self, squad):
        return ("%s (%d CP) - hold this objective until your opponent out-controls it"
                % (SPIRIT_TOKEN_NAME, SPIRIT_TOKEN_CP))

    def candidates(self, squad):
        return objectives_for(squad, self.objectives)

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None or self.turn_tracker is None:
            return False
        if self.turn_tracker.phase != PHASE_MOVEMENT:
            return False
        if squad.owner != self.turn_tracker.active_player:
            return False               # "YOUR Movement phase"
        # "START of your Movement phase" - gone once this unit has moved.
        if self.movement_controller is not None \
                and squad in getattr(self.movement_controller, "moved_squad_ids", ()):
            return False
        if not eligible_unit(squad):
            return False
        if not self.candidates(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad, objective=None):
        if not self.can_use(squad):
            return False
        options = self.candidates(squad)
        if objective is None:
            if len(options) > 1 and squad.owner not in self.auto_players \
                    and self.decision_manager is not None:
                self.decision_manager.request(
                    squad.owner,
                    "%s: which objective marker does %s hold?"
                    % (SPIRIT_TOKEN_NAME, squad.name),
                    [(getattr(o, "name", "objective"),
                      (lambda s=squad, o=o: self.use(s, o))) for o in options],
                    is_stratagem=True,
                )
                return True
            objective = options[0]
        self._pending[squad.owner] = (squad, objective)
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _secure(self, controller, player, targets):
        squad, objective = self._pending.pop(player, (None, None))
        if squad is None or objective is None:
            return
        # Rule 14.03's own mechanism - the third caller of it.
        objective.secure_for(player)
        if self.game_log is not None:
            self.game_log.add(
                "%s: %s holds %s until the opponent out-controls it."
                % (SPIRIT_TOKEN_NAME, squad.name,
                   getattr(objective, "name", "an objective")))
