"""Dragon Knights' and the Leystalker's "Drakolithe" - a datasheet ability.

RULE (printed, word for word):
  "(Once per battle, per token) When an enemy unit ends a move within 8" of
  this unit, if this unit is unengaged or if that enemy unit ended that move
  engaged with this unit, you can use this ability. If you do, roll one D6:
    - On a 3+, that enemy unit suffers 1 mortal wound.
  Place one Drakolithe token next to the unit for each Drakolithe the unit is
  equipped with, removing one each time this ability is used."

A REACTION TO A MOVE, ON A SEAM THAT ALREADY EXISTS
----------------------------------------------------
"When an enemy unit ends a move" is MovementController.confirm_move(), the one
place every confirmed move passes through - the same seam rule 16.01 and the
Shadow Weaver's Monofilament Snare already report from. Nothing new was needed.

AND NO MOVE-TYPE FILTER, deliberately: the Monofilament Snare names three kinds
of move and this names none, so it reacts to a Charge and a Consolidate as well.
That difference is printed, and it is the reason the snare's exclusion set is
not reused here.

THE TOKENS ARE THE RESOURCE, per UNIT rather than per model or per army: "one
token for each Drakolithe the unit is equipped with", removed one at a time. The
Leystalker prints two on its own wargear line; the Dragon Knights buy them
("for every 3 models in this unit, this unit can be equipped with 2"). So the
count is set when the unit is built and this module only spends it.

THE CONDITION HAS TWO ARMS AND THEY ARE AN OR, not a refinement of each other:
either the BEARER is unengaged, or the MOVER ended its move engaged with the
bearer. So a bearer already locked in combat still reacts to something charging
into it - the case the first arm alone would miss, and its own test line.

RESOLVED IMMEDIATELY rather than as a dice-panel step, for the reason Undying
Spite and the Monofilament Snare give: no decision hangs on the die itself, and
an enemy moves many times a turn. Reported in the log instead.
"""
from game.squad import ENGAGEMENT_RANGE_IN, edge_distance
from game import ai_mode
from game import mortal_wound_sessions

DRAKOLITHE_LABEL = "Drakolithe"

#: "within 8 inches of this unit".
DRAKOLITHE_RANGE_IN = 8.0
#: "On a 3+, that enemy unit suffers 1 mortal wound."
DRAKOLITHE_THRESHOLD = 3
DRAKOLITHE_MORTAL_WOUNDS = 1


def _living(squad):
    return [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]


def tokens_on(squad):
    return int(getattr(squad, "drakolithe_tokens", 0) or 0)


def has_drakolithe(squad):
    return any(getattr(m.profile, "drakolithe", False) for m in _living(squad))


class DrakolitheController:
    """One per battle. Fed from MovementController.confirm_move()."""

    def __init__(self, dice_manager=None, decision_manager=None, game_log=None,
                 game_state=None, all_tokens=None, auto_players=()):
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.game_state = game_state
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.auto_players = ai_mode.players(auto_players)
        self.mortal_wound_sessions = []

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _is_engaged(self, squad):
        mine = _living(squad)
        for token in self.all_tokens or ():
            other = getattr(token, "squad", None)
            if other is None or other.owner == squad.owner:
                continue
            if any(edge_distance(a, b) <= ENGAGEMENT_RANGE_IN
                   for a in mine for b in _living(other)):
                return True
        return False

    def bearers_reacting_to(self, mover):
        """Units that may spend a token against this move: within 8", holding
        at least one token, and satisfying the two-armed condition."""
        out, seen = [], set()
        moved = _living(mover)
        if not moved:
            return out
        for token in self.all_tokens or ():
            bearer = getattr(token, "squad", None)
            if bearer is None or id(bearer) in seen or bearer.owner == mover.owner:
                continue
            if not has_drakolithe(bearer) or tokens_on(bearer) <= 0:
                continue
            mine = _living(bearer)
            if not mine:
                continue
            if not any(edge_distance(a, b) <= DRAKOLITHE_RANGE_IN
                       for a in mine for b in moved):
                continue
            engaged_with_mover = any(edge_distance(a, b) <= ENGAGEMENT_RANGE_IN
                                     for a in mine for b in moved)
            if not (not self._is_engaged(bearer) or engaged_with_mover):
                continue
            seen.add(id(bearer))
            out.append(bearer)
        return out

    def notify_move(self, mover, move_mode=None):
        """"When an enemy unit ends a move" - ANY move, so no mode filter."""
        if mover is None:
            return 0
        used = 0
        for bearer in self.bearers_reacting_to(mover):
            if bearer.owner in self.auto_players or self.decision_manager is None:
                used += 1 if self.use(bearer, mover) else 0
                continue
            self.decision_manager.request(
                bearer.owner,
                '%s: %s ended a move within %d" of %s - spend a token? (%d left)'
                % (DRAKOLITHE_LABEL, mover.name, int(DRAKOLITHE_RANGE_IN),
                   bearer.name, tokens_on(bearer)),
                [("Spend a Drakolithe token", (lambda b=bearer: self.use(b, mover))),
                 ("Keep it", None)],
            )
            return used     # one prompt at a time
        return used

    def use(self, bearer, mover):
        """Spends the token whatever the die says - "removing one each time
        this ability is USED", not each time it succeeds."""
        if tokens_on(bearer) <= 0:
            return False
        bearer.drakolithe_tokens = tokens_on(bearer) - 1
        rolled = self._roll_one()
        self._log("%s: %s spends a token against %s - rolled %d (%d left)."
                  % (DRAKOLITHE_LABEL, bearer.name, mover.name, rolled,
                     tokens_on(bearer)))
        if rolled < DRAKOLITHE_THRESHOLD:
            return False
        from game.damage_resolution import MortalWoundAllocationSession
        self.mortal_wound_sessions.append(MortalWoundAllocationSession(
            mover, DRAKOLITHE_MORTAL_WOUNDS, dice_manager=self.dice_manager,
            log=self._log))
        return True

    def _roll_one(self):
        from game.dice import random as dice_random
        return dice_random.randint(1, 6)

    @property
    def is_busy(self):
        return mortal_wound_sessions.any_open(self.mortal_wound_sessions)

    # ------------------------------------------------- rule 06.02 allocation
    # This ability can open SEVERAL sessions in one go, so the three members
    # main.py asks about delegate to game/mortal_wound_sessions.py rather than
    # being written twice - see that module for why insertion order is part of
    # the answer. Without them the wounds were rolled, logged and never
    # applied against any multi-model target.

    @property
    def pending_damage_choice(self):
        return mortal_wound_sessions.pending_choice(self.mortal_wound_sessions)

    def choose_damage_model(self, model):
        if mortal_wound_sessions.choose(self.mortal_wound_sessions, model):
            mortal_wound_sessions.prune(self.mortal_wound_sessions)

    def on_dice_acknowledged(self):
        """Only the Feel No Pain leg: this ability rolls its own dice inline,
        so there is no pending dice context to resume."""
        if not mortal_wound_sessions.acknowledge_fnp(self.mortal_wound_sessions):
            return False
        mortal_wound_sessions.prune(self.mortal_wound_sessions)
        return True
