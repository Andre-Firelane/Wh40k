"""Death Lord's Chosen Stratagem: SIGNAL POX (1 CP, Epic Deed).

  WHEN: Your Command phase.
  TARGET: One LORD OF VIRULENCE model from your army.
  EFFECT: Select one objective marker within 30" of and visible to your model.
        Until the start of your next turn, while an enemy unit is within range
        of that objective marker, that unit is Afflicted.

A DOCUMENTED NO-OP FOR THIS ROSTER. No datasheet this engine builds carries the
LORD OF VIRULENCE keyword - Typhus is TYPHUS/TERMINATOR, and the other two
characters are neither. So can_use() can never return True today.

It is written out anyway rather than skipped, which is this repo's standing
treatment for a printed clause nothing can currently satisfy - the same status
AIRCRAFT, FORTIFICATION and TITANIC have in game/actions.py and
game/rapid_ingress.py, and the same reason Cleanse's "if you have Plunder
active" clause was written before Plunder existed: adding a Lord of Virulence
later then costs one datasheet and no rules work at all.
test_death_guard_stratagems.py pins the emptiness, so that day is a visible
change rather than a silent one.

IT IS ALSO THE ONLY STRATAGEM IN THE SIX THAT USES THE STICKY HALF of
Nurgle's Gift. "Until the start of your next turn ... that unit is Afflicted"
is exactly NurglesGiftController.mark_afflicted()'s contract, and this is the
second caller of it (the Plague Marines' own ability is the first). That is
worth recording because it is what makes Squad.afflicted a FLAG rather than a
live distance test - see game/nurgles_gift.py's docstring.

THE MARK IS RE-APPLIED EVERY REFRESH, not set once: the objective is fixed for
the duration, but WHICH units stand on it changes. So the controller holds the
chosen objective and re-marks whatever is in range each frame, and drops the
whole thing at the start of its owner's next turn.

NO AI PATH, per the user's instruction that only Grim Reapers, Undying Spite
and Sickening Impact need one - and it would be unreachable in any case.
"""
from game import death_lords_chosen, objectives
from game.stratagems import Stratagem

SIGNAL_POX_CP = 1
SIGNAL_POX_NAME = "Signal Pox"
SIGNAL_POX_RANGE_IN = 30.0


def bearers(squad):
    """"One LORD OF VIRULENCE model from your army" - a datasheet keyword, read
    the same way TERMINATOR is. Empty for every unit this engine builds."""
    if not death_lords_chosen.is_lord_of_virulence_unit(squad):
        return []
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


class SignalPoxController:
    def __init__(self, stratagem_controller, nurgles_gift_controller=None,
                 decision_manager=None, turn_tracker=None, game_log=None,
                 game_state=None, visible=None):
        self.stratagem_controller = stratagem_controller
        self.nurgles_gift = nurgles_gift_controller
        self.decision_manager = decision_manager
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self.game_state = game_state
        # visible(model, objective) -> bool, supplied by main.py so "visible to
        # your model" means what it means everywhere else.
        self.visible = visible
        self._marked_objective = None
        self._owner = None
        self._stratagem = Stratagem(name=SIGNAL_POX_NAME, cp_cost=SIGNAL_POX_CP,
                                    effect=self._grant)

    def _tokens(self):
        return list(self.game_state.tokens) if self.game_state is not None else []

    def eligible_objectives(self, squad, all_objectives):
        """"one objective marker within 30" of and visible to your model"."""
        out = []
        for objective in all_objectives or ():
            for model in bearers(squad):
                area = getattr(objective, "terrain_area", None)
                if area is None:
                    continue
                cx, cy = area.center if hasattr(area, "center") else (None, None)
                if cx is None:
                    continue
                gap = ((model.x_in - cx) ** 2 + (model.y_in - cy) ** 2) ** 0.5
                if gap > SIGNAL_POX_RANGE_IN:
                    continue
                if self.visible is not None and not self.visible(model, objective):
                    continue
                out.append(objective)
                break
        return out

    def can_use(self, squad, all_objectives=()):
        if squad is None or self._marked_objective is not None:
            return False
        if not death_lords_chosen.stratagem_target_ok(squad):
            return False
        if not bearers(squad):
            return False   # the no-op: nothing in this roster has the keyword
        if self.turn_tracker is not None:
            from game.turn import PHASE_COMMAND
            if self.turn_tracker.phase != PHASE_COMMAND:
                return False
            if squad.owner != self.turn_tracker.turn_owner:
                return False   # "YOUR Command phase"
        if not self.eligible_objectives(squad, all_objectives):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad, objective, all_objectives=()):
        if objective is None or not self.can_use(squad, all_objectives):
            return False
        self._pending_objective = objective
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        self._marked_objective = getattr(self, "_pending_objective", None)
        self._owner = player
        if self.game_log is not None and self._marked_objective is not None:
            self.game_log.add(
                f"{SIGNAL_POX_NAME}: enemy units within range of "
                f"{self._marked_objective.name} are Afflicted until the start of "
                f"{player}'s next turn.")
        return True

    def refresh(self, all_tokens=()):
        """Re-mark whatever is standing on the chosen objective RIGHT NOW.

        The objective is fixed for the duration but the units on it are not, so
        this runs every frame beside the aura refresh rather than once at
        purchase. Returns the units marked, for tests."""
        if self._marked_objective is None or self.nurgles_gift is None:
            return []
        marked = []
        seen = set()
        for token in all_tokens or ():
            squad = getattr(token, "squad", None)
            if squad is None or id(squad) in seen or token.is_dead():
                continue
            if squad.owner == self._owner:
                continue   # "an ENEMY unit"
            seen.add(id(squad))
            if objectives.is_within_range_of_objective(squad, [self._marked_objective]):
                self.nurgles_gift.mark_afflicted(squad, until_turn_of=self._owner)
                marked.append(squad)
        return marked

    def expire_for_turn(self, player):
        """"Until the start of your next turn." The sticky marks themselves are
        dropped by NurglesGiftController.expire_marks_for(), which owns them -
        this only forgets the objective, so the Stratagem stops re-marking."""
        if self._owner == player:
            self._marked_objective = None
            self._owner = None
