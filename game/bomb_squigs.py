"""The Tankbustas' Bomb Squigs (2026-09 Ork codex).

RULE (verbatim, rules/orks/Tankbustas.md):
  "Bomb Squigs (Once per turn, twice per battle, per unit): In your Movement
   phase, when this unit ends a normal move, you can select one visible enemy
   unit within 12" of this unit and roll one D6:
   - On a 3+, that enemy unit suffers D3 mortal wounds.
   Place two Bomb Squig tokens next to the unit, removing one each time this
   ability is used."

THE TRIGGER is MovementController.on_move_finished with the move KIND, the seam
Wraith Form and the Boss Motivations already listen on: "normal" only, so an
Advance or a Fall Back does not throw a squig. "In YOUR Movement phase" is read
off the live clock (phase and turn owner) - an out-of-phase move reported as a
normal one is not the Movement phase.

TWO LEDGERS ON THE UNIT, both saved (activation_state.SQUAD_FLAGS):
  * Squad.bomb_squigs_used - how many of the two tokens are gone. "Twice per
    battle, per unit": a second Tankbustas unit has its own two.
  * Squad.bomb_squigs_turn - the 1-based turn number (riled_up.turn_serial() + 1)
    of the last use. 1-based because the save keeps only truthy values, and
    round 1's first turn is serial 0.
A token is spent when the ability is USED - when a unit is selected and the D6
is rolled - not only when the D6 succeeds: "removing one each time this ability
is used".

"YOU CAN SELECT" IS A REAL CHOICE here, unlike Krushin' Impetus: every use costs
one of two tokens, so a human is asked which unit - or none (a red Decline) - and
the candidates are a board pick (game/unit_pick.py). The AI throws one at its
first opportunity, at the unit the shared damage-value ranking picks (main.py's
_best_damage_target) - 0 API calls.

TWO VISIBLE ROLLS, the D6 that decides whether it happens and the D3 for how
much - Matter Absorption's shape, and for the same reason: one combined roll
could not show which number did what. The 06.02 allocation (the TARGET's owner
picks) and its Feel No Pain leg are MortalWoundOfferController's own plumbing.

"VISIBLE ... WITHIN 12\" OF THIS UNIT" are two unit-level facts: some model of
this unit is within 12" of the enemy unit, and some model of this unit can see
it. `visible(model, squad)` is injected by main.py (the real line of sight), so
this module never re-derives it; None means no filter, what a headless test
wants.
"""

from game.mortal_wound_abilities import MortalWoundOfferController, enemy_squads, gap_to
from game.riled_up import turn_serial
from game.squad import unit_wide_ability
from game.turn import PHASE_MOVEMENT

BOMB_SQUIGS_NAME = "Bomb Squigs"
#: "within 12\" of this unit".
BOMB_SQUIGS_RANGE_IN = 12
#: "On a 3+".
BOMB_SQUIGS_THRESHOLD = 3
#: "D3 mortal wounds".
BOMB_SQUIGS_WOUND_SIDES = 3
#: "twice per battle" - the two Bomb Squig tokens.
BOMB_SQUIGS_PER_BATTLE = 2
#: The on_move_finished kind that triggers it.
BOMB_SQUIGS_MOVE_KIND = "normal"


def has_ability(squad):
    return squad is not None and bool(unit_wide_ability(squad, "bomb_squigs"))


def squigs_left(squad):
    return max(0, BOMB_SQUIGS_PER_BATTLE - int(getattr(squad, "bomb_squigs_used", 0) or 0))


def turn_number(turn_tracker):
    """1-based, so the save (which keeps only truthy values) keeps round 1's
    first turn too."""
    return turn_serial(turn_tracker) + 1


def _alive(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def targets(squad, all_tokens, visible=None):
    """Every enemy unit this unit may select: within 12" of some model of this
    unit and visible to some model of this unit."""
    models = _alive(squad)
    out = []
    for enemy in enemy_squads(squad, all_tokens):
        if not any(gap_to(m, enemy) <= BOMB_SQUIGS_RANGE_IN for m in models):
            continue
        if visible is not None and not any(visible(m, enemy) for m in models):
            continue
        out.append(enemy)
    return out


class BombSquigsController(MortalWoundOfferController):
    """An on_move_finished listener (see main.py)."""

    label = BOMB_SQUIGS_NAME

    def __init__(self, *args, turn_tracker=None, visible=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.turn_tracker = turn_tracker
        self.visible = visible
        self._stage = None

    def why_not(self, squad, kind=BOMB_SQUIGS_MOVE_KIND):
        """None when the ability may be used now, else the reason."""
        if squad is None:
            return "no unit"
        if kind != BOMB_SQUIGS_MOVE_KIND:
            return "not a normal move"
        if not has_ability(squad):
            return "this unit has no Bomb Squigs"
        tt = self.turn_tracker
        if tt is not None and (tt.phase != PHASE_MOVEMENT or tt.turn_owner != squad.owner):
            return "not your Movement phase"
        if squigs_left(squad) <= 0:
            return "no Bomb Squig tokens left"
        if tt is not None and getattr(squad, "bomb_squigs_turn", None) == turn_number(tt):
            return "already used this turn"
        if self._pending is not None or self.mortal_wound_session is not None:
            return "a Bomb Squig is already being resolved"
        if not targets(squad, self._tokens(), self.visible):
            return "no visible enemy unit within 12\""
        return None

    def can_use(self, squad, kind=BOMB_SQUIGS_MOVE_KIND):
        return self.why_not(squad, kind) is None

    def on_move_finished(self, squad, kind):
        """The listener. True when anything was used or asked."""
        if not self.can_use(squad, kind):
            return False
        candidates = targets(squad, self._tokens(), self.visible)
        if squad.owner in self.auto_players or self.decision_manager is None:
            return self._use(squad, self._pick(squad, candidates))
        left = squigs_left(squad)
        options = [("%s: %s" % (BOMB_SQUIGS_NAME, t.name), (lambda target=t: self._use(squad, target)), t)
                   for t in candidates]
        options.append(("Decline", None))
        self.decision_manager.request(
            squad.owner,
            "%s: %s (%d token%s left) - D6, on a 3+ D3 mortal wounds. At which unit?"
            % (squad.name, BOMB_SQUIGS_NAME, left, "" if left == 1 else "s"),
            options)
        return True

    def _use(self, squad, target):
        if target is None or self.dice_manager is None or not self.can_use(squad):
            return False
        squad.bomb_squigs_used = int(getattr(squad, "bomb_squigs_used", 0) or 0) + 1
        if self.turn_tracker is not None:
            squad.bomb_squigs_turn = turn_number(self.turn_tracker)
        self._pending = {"squad": squad, "target": target}
        self._stage = "gate"
        self._log("%s (%s) throws a Bomb Squig at %s - %d token(s) left."
                  % (BOMB_SQUIGS_NAME, squad.name, target.name, squigs_left(squad)))
        self.dice_manager.roll(
            1, 6, label=self.label, success_threshold=BOMB_SQUIGS_THRESHOLD,
            target_name=target.name, attacker_squad=squad, target_squad=target,
            rolled_for=squad)
        return True

    def on_dice_acknowledged(self):
        if self._pending is None:
            return self._ack_session()
        values = (self.dice_manager.last_values if self.dice_manager is not None else None) or [1]
        ctx = self._pending
        if self._stage == "gate":
            if values[0] < BOMB_SQUIGS_THRESHOLD:
                self._pending = None
                self._stage = None
                self._log("%s (%s): rolled a %d, needed %d+ - the squig fizzles."
                          % (BOMB_SQUIGS_NAME, ctx["squad"].name, values[0], BOMB_SQUIGS_THRESHOLD))
                return True
            self._stage = "amount"
            self.dice_manager.roll(
                1, BOMB_SQUIGS_WOUND_SIDES, label="%s - mortal wounds" % self.label,
                target_name=ctx["target"].name, attacker_squad=ctx["squad"],
                target_squad=ctx["target"], rolled_for=ctx["squad"])
            return True
        self._pending = None
        self._stage = None
        wounds = values[0]
        self._log("%s (%s): %s suffers %d mortal wound(s)."
                  % (BOMB_SQUIGS_NAME, ctx["squad"].name, ctx["target"].name, wounds))
        self._inflict(ctx["target"], wounds)
        return True

    def _inflict(self, target, wounds):
        super()._inflict(target, wounds)
        # A single-model target takes the wounds inside the session's
        # constructor and never parks. Left in the slot, that finished session
        # reads as "a Bomb Squig is already being resolved" to why_not() - and
        # the unit's second token could never be thrown.
        self._check_session_done()
