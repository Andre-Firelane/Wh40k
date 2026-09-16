"""Intimidating Motivation (Warboss, Warboss in Mega Armour) and Keep Huntin'!
(Beastboss) - 2026-09 Ork codex.

RULES (verbatim, rules/orks/Warboss.md, Warboss in Mega Armour.md, Beastboss.md):
  "Intimidating Motivation (Once per battle round, per army): In your Movement
   phase, at the start or end of this unit's move, you can select one friendly
   ORKS unit within 6" of this unit. That unit:
   - Is no longer battle-shocked.
   - Is riled up until the start of your next turn."
  "Keep Huntin'! (Once per battle round, per army): In your Movement phase, at
   the start or end of this unit's move, you can select one friendly BEAST
   SNAGGA unit within 6" of this unit. That unit: [the same two bullets]"

ONE MECHANISM, TWO RULES. The same sentence with a different target keyword and -
because the limit is per ABILITY, not per model - a separate
once-per-battle-round budget (game/per_army_round_limit.py). So one controller
class with its knobs (NAME, the profile FLAG, the limit's LIMIT_FLAG, which
units qualify) and two subclasses. A Warboss and a Warboss in Mega Armour share
Intimidating Motivation's one use; a Beastboss beside them has his own.

"AT THE START OR END OF THIS UNIT'S MOVE" - two moments, one use (the limit
spends it). The human gets a PANEL BUTTON (game/proactive_stratagems.py; no CP,
so no Stratagem object and a "no CP" label) while one of the two windows is
open:
  * START: the unit has not been selected to move, Advance or stay stationary
    this phase, and no move of it is under way;
  * END: its move is the one that finished last, and no unit has begun a move
    since - MovementController.on_move_finished opens that window and
    on_move_started closes it.
A button rather than a prompt at both moments: a prompt would ask up to twice
per bearer move, every Movement phase, until used.

"SELECT ONE FRIENDLY UNIT WITHIN 6" OF THIS UNIT". The bearer's own unit counts -
it is a friendly ORKS unit, and it is within 6" of itself - the reading Carrier
Wave takes. Measured unit to unit, edge to edge (Squad.min_distance_to()), on the
battlefield only. A unit the ability would do nothing for is not offered
(Fehlerklasse 5): one that is not battle-shocked AND cannot gain from riled up
(no Waaagh!, or already riled up at least that long). One candidate is used
outright; several are a board pick (game/unit_pick.py) with a Cancel that spends
nothing.

"IS RILED UP UNTIL THE START OF YOUR NEXT TURN" goes through game/riled_up.py's
grant(). "Is no longer battle-shocked" clears the flag: this engine has a door
for BECOMING shocked (game/battle_shock.py), not for leaving it.

THE AI answers in the two move hooks, which fire for its moves too, through an
injected choice (ai/agent_driver.py's boss_motivation_choice()) - 0 API calls.
"""

from game import ai_mode, riled_up
from game.per_army_round_limit import PerArmyRoundLimit
from game.turn import PHASE_MOVEMENT

#: "within 6" of this unit".
BOSS_MOTIVATION_RANGE_IN = 6.0

MOVING = "moving"   # game/movement.py's MovementController.state while a move is under way


def _alive(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


class BossMotivationController:
    NAME = "Boss motivation"
    FLAG = None          # the UnitProfile flag of the printing model
    LIMIT_FLAG = None    # the Squad field the limit's spend is written to
    TARGET_WORD = ""     # the printed target keyword, for labels

    def __init__(self, turn_tracker=None, movement_controller=None, decision_manager=None,
                 game_log=None, squads_provider=None, all_tokens=None, auto_players=(),
                 choice=None):
        self.turn_tracker = turn_tracker
        self.movement_controller = movement_controller
        self.decision_manager = decision_manager
        self.game_log = game_log
        # Every unit in the game, wherever it is - "per army" is the whole army.
        self.squads_provider = squads_provider
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.auto_players = ai_mode.players(auto_players)
        # The AI's rule, injected (game/ must not import ai/):
        # choice(bearer_squad, candidates) -> a candidate, or None to hold it.
        self.choice = choice
        self.limit = PerArmyRoundLimit(self.NAME, self.LIMIT_FLAG)
        self._just_moved = None

    # ----------------------------------------------------------- questions
    def target_qualifies(self, squad):
        raise NotImplementedError

    def bearer_models(self, squad):
        return [m for m in _alive(squad) if getattr(m.profile, self.FLAG, False)]

    def _squads(self):
        if self.squads_provider is None:
            return []
        return [s for s in self.squads_provider() if s is not None]

    def _battle_round(self):
        return getattr(self.turn_tracker, "battle_round", None)

    def is_spent(self, player, squad=None):
        pool = self._squads()
        if squad is not None and squad not in pool:
            pool.append(squad)
        return self.limit.is_spent(player, self._battle_round(), pool)

    def _deadline(self, player):
        return riled_up.until_start_of_your_next_turn(self.turn_tracker, player)

    def benefits(self, target, player):
        if getattr(target, "battle_shocked", False):
            return True
        if not riled_up.has_ability(target):
            return False
        current = getattr(target, "riled_up_expires_turn", None)
        return current is None or current < self._deadline(player)

    def candidates(self, squad):
        if squad is None:
            return []
        on_board = {t.squad for t in self.all_tokens
                    if getattr(t, "squad", None) is not None and not t.is_dead()}
        out = []
        for other in on_board:
            if other.owner != squad.owner or not _alive(other):
                continue
            if not self.target_qualifies(other):
                continue
            if squad.min_distance_to(other) > BOSS_MOTIVATION_RANGE_IN:
                continue
            if not self.benefits(other, squad.owner):
                continue
            out.append(other)
        return sorted(out, key=lambda s: s.name)

    def window_open(self, squad):
        """The START or END of this unit's move - see the module docstring."""
        if squad is self._just_moved:
            return True
        mc = self.movement_controller
        if mc is None:
            return True
        for ledger in ("moved_squad_ids", "advanced_squad_ids", "stationary_squad_ids"):
            if squad in getattr(mc, ledger, ()):
                return False
        if getattr(mc, "state", None) == MOVING and getattr(mc, "selected_squad", None) is squad:
            return False
        return True

    def why_not(self, squad, ignore_window=False):
        tt = self.turn_tracker
        if squad is None or tt is None:
            return "no unit"
        if not self.bearer_models(squad):
            return "this unit has no %s" % self.NAME
        if tt.phase != PHASE_MOVEMENT or squad.owner != tt.turn_owner:
            return "not your Movement phase"
        if self.is_spent(squad.owner, squad):
            return "already used this battle round"
        if not ignore_window and not self.window_open(squad):
            return "only at the start or end of this unit's move"
        if not self.candidates(squad):
            return "no friendly %s unit within 6\" it would help" % self.TARGET_WORD
        return None

    def can_use(self, squad):
        return self.why_not(squad) is None

    # --------------------------------------------------------- the button
    def panel_label(self, squad):
        return "%s (no CP, once per round) - unshock + rile up a unit within 6\"" % self.NAME

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self._select(squad)

    def _select(self, squad):
        cands = self.candidates(squad)
        if not cands:
            return False
        if len(cands) == 1 or self.decision_manager is None:
            return self.apply(squad, cands[0])
        options = [("%s: %s" % (self.NAME, t.name), (lambda t=t: self.apply(squad, t)), t)
                   for t in cands]
        options.append(("Cancel", lambda: None))
        self.decision_manager.request(
            squad.owner,
            "%s: %s - which unit is no longer battle-shocked and is riled up until the start "
            "of your next turn?" % (squad.name, self.NAME),
            options,
        )
        return True

    def apply(self, bearer_squad, target):
        """The effect. Checked again, because a board pick is answered frames
        later and the limit may have been spent in between."""
        player = bearer_squad.owner
        if self.is_spent(player, bearer_squad) or not _alive(target):
            return False
        was_shocked = bool(getattr(target, "battle_shocked", False))
        target.battle_shocked = False
        riled = riled_up.grant(target, self._deadline(player), self.turn_tracker)
        self.limit.spend(player, self._battle_round(), bearer_squad)
        if self.game_log is not None:
            parts = []
            if was_shocked:
                parts.append("is no longer battle-shocked")
            if riled:
                parts.append("is riled up until the start of %s's next turn" % player)
            self.game_log.add("%s (%s): %s %s." % (self.NAME, bearer_squad.name, target.name,
                                                   " and ".join(parts) or "is unaffected"))
        return True

    # ------------------------------------------------------- the move hooks
    def on_move_started(self, squad):
        """Closes the END window for everyone, then the START moment for the AI."""
        self._just_moved = None
        return self._auto(squad, ignore_window=True)

    def on_move_finished(self, squad, kind=None):
        tt = self.turn_tracker
        if (squad is not None and tt is not None and tt.phase == PHASE_MOVEMENT
                and squad.owner == tt.turn_owner):
            self._just_moved = squad
        return self._auto(squad)

    def _auto(self, squad, ignore_window=False):
        if squad is None or squad.owner not in self.auto_players or self.choice is None:
            return False
        if self.why_not(squad, ignore_window=ignore_window) is not None:
            return False
        target = self.choice(squad, self.candidates(squad))
        if target is None:
            return False
        return self.apply(squad, target)

    def reset_phase(self):
        self._just_moved = None


class IntimidatingMotivationController(BossMotivationController):
    NAME = "Intimidating Motivation"
    FLAG = "intimidating_motivation"
    LIMIT_FLAG = "intimidating_motivation_round"
    TARGET_WORD = "ORKS"

    def target_qualifies(self, squad):
        return any(getattr(m.profile, "orks", False) for m in _alive(squad))


class KeepHuntinController(BossMotivationController):
    NAME = "Keep Huntin'!"
    FLAG = "keep_huntin"
    LIMIT_FLAG = "keep_huntin_round"
    TARGET_WORD = "BEAST SNAGGA"

    def target_qualifies(self, squad):
        return any(getattr(m.profile, "beast_snagga", False) for m in _alive(squad))
