"""Canoptek Court Stratagem: Suboptimal Facade (1CP).

RULE (verbatim, rules/necrons/detachments/Canoptek Court.md):
  WHEN:   Your opponent's Charge phase, just after an enemy unit has declared a
          charge.
  TARGET: One CANOPTEK unit from your army that was selected as a target of that
          charge and is wholly within your army's Power Matrix.
  EFFECT: Your unit's Reanimation Protocols activate.

A CHARGE-DECLARATION REACTOR THAT OWNS THE RESUME (charge_declaration_reactions'
protocol, game/grav_inhibitor_field.py's shape), and the whole EFFECT is the army
rule: game/reanimation_protocols.activate() - the one door every activation goes
through, which adds the Canoptek boosts, heals before it revives, and hands a
human's returning models to the placer. So this module restates none of that.

THE CHARGE WAITS FOR ALL OF IT: the D3 (one dice window), and - for a human whose
models come back - the placement, which is frames of dragging. The resume runs
from activate()'s on_placed, or at once when nothing needs placing.

NEVER OFFERED WHEN IT BUYS NOTHING: a unit with nothing to recover
(reanimation_protocols.recoverable_wounds() == 0) is not a candidate.

THE AI answers with the same threshold Protocol of the Undying Legions uses
(recoverable wounds >= 2) - one CP spent on one activation, the same trade.

_declaration_key MEMO, because begin_charge_move() is re-run for every retry of a
failed approach (Fehlerklasse 26) and a declined offer leaves 15.01's ledger
untouched.
"""

from game import ai_mode, court_power_matrix, necron_detachments, reanimation_protocols
from game.stratagems import Stratagem
from game.turn import PHASE_CHARGE

SUBOPTIMAL_FACADE_NAME = "Suboptimal Facade"
SUBOPTIMAL_FACADE_CP = 1
SUBOPTIMAL_FACADE_DICE_SIDES = 3
SUBOPTIMAL_FACADE_MIN_RECOVERABLE = 2
SETTING = "CANOPTEK_COURT_PLAYERS"


class SuboptimalFacadeController:
    def __init__(self, stratagem_controller, dice_manager=None, decision_manager=None,
                 turn_tracker=None, game_state=None, power_matrix=None, position_valid=None,
                 placer=None, boost=None, game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.turn_tracker = turn_tracker
        self.game_state = game_state
        self.power_matrix = power_matrix
        self.position_valid = position_valid
        self.placer = placer
        self.boost = boost
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._offered_key = None
        self._resume = None
        self._pending = None           # the unit whose D3 is on the table
        self._waiting_placement = False
        self._stratagem = Stratagem(name=SUBOPTIMAL_FACADE_NAME, cp_cost=SUBOPTIMAL_FACADE_CP,
                                    effect=self._effect)

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _tokens(self):
        return list(getattr(self.game_state, "tokens", ()) or ())

    @property
    def is_busy(self):
        return self._pending is not None or self._waiting_placement

    # ------------------------------------------------------------ eligibility
    def can_use(self, charging_squad, target_squad):
        if charging_squad is None or target_squad is None or self.stratagem_controller is None:
            return False
        if target_squad.owner == charging_squad.owner:
            return False
        tt = self.turn_tracker
        if tt is not None and (tt.phase != PHASE_CHARGE or tt.turn_owner != charging_squad.owner):
            return False
        if not necron_detachments.has_detachment(target_squad.owner, SETTING):
            return False
        if not necron_detachments.is_canoptek_unit(target_squad):
            return False
        if not any(not m.is_dead() for m in target_squad.models):
            return False
        if reanimation_protocols.recoverable_wounds(target_squad) <= 0:
            return False
        if not court_power_matrix.unit_wholly_within(target_squad, self.power_matrix):
            return False
        return self.stratagem_controller.can_use(target_squad.owner, self._stratagem, [target_squad])

    def _declaration_key(self, charging_squad, targets):
        battle_round = getattr(self.turn_tracker, "battle_round", None)
        return (battle_round, id(charging_squad), tuple(sorted(id(t) for t in targets)))

    # --------------------------------------------------------------- the chain
    def maybe_offer(self, charging_squad, targets, on_resolved=None):
        key = self._declaration_key(charging_squad, targets)
        if key == self._offered_key or self.is_busy or self._resume is not None:
            return False
        eligible = sorted((t for t in targets or () if self.can_use(charging_squad, t)),
                          key=lambda s: s.name)
        if not eligible:
            return False
        self._offered_key = key
        player = eligible[0].owner
        if player in self.auto_players:
            worth = [t for t in eligible
                     if reanimation_protocols.recoverable_wounds(t) >= SUBOPTIMAL_FACADE_MIN_RECOVERABLE]
            if not worth:
                return False
            best = max(worth, key=lambda t: (reanimation_protocols.recoverable_wounds(t), t.name))
            self._resume = on_resolved
            if not self._buy(best):
                self._resume = None
                return False
            if self._resume is None:
                return True   # resolved to the end already; the resume has run
            return True
        if self.decision_manager is None:
            return False
        self._resume = on_resolved
        self.decision_manager.request(
            player,
            f"{SUBOPTIMAL_FACADE_NAME} ({SUBOPTIMAL_FACADE_CP} CP): {charging_squad.name} has "
            "declared a charge - activate Reanimation Protocols for which CANOPTEK unit?",
            [(t.name, (lambda t=t: self._accept(t)), t) for t in eligible]
            + [("Decline", self._finish)],
            is_stratagem=True,
        )
        return True

    def _accept(self, target):
        if not self._buy(target):
            self._finish()

    def _buy(self, target):
        return self.stratagem_controller.use(target.owner, self._stratagem, [target])

    def _effect(self, controller, player, targets):
        squad = targets[0]
        self._log(f"{SUBOPTIMAL_FACADE_NAME}: {squad.name}'s Reanimation Protocols activate.")
        self._pending = squad
        if self.dice_manager is None:
            from game import dice
            self._apply(squad, dice.random.randint(1, SUBOPTIMAL_FACADE_DICE_SIDES))
            return
        self.dice_manager.roll(
            1, SUBOPTIMAL_FACADE_DICE_SIDES, label=SUBOPTIMAL_FACADE_NAME,
            target_name=squad.name, target_squad=squad, rolled_for=squad,
            subject_label="Reanimating")

    def on_dice_acknowledged(self):
        if self._pending is None or self.dice_manager is None:
            return False
        rolled = (self.dice_manager.last_values or [1])[0]
        self._apply(self._pending, rolled)
        return True

    def _apply(self, squad, rolled):
        self._pending = None
        self._waiting_placement = True
        wounds, spent, revived = reanimation_protocols.activate(
            squad, rolled,
            boost=self.boost,
            all_tokens=self._tokens(),
            position_valid=self.position_valid,
            game_state=self.game_state,
            placer=self.placer,
            on_placed=self._after_placement,
            log=self._log,
        )
        detail = f"{spent} wound(s)"
        if revived:
            detail += f", {len(revived)} model(s) back on the battlefield"
        self._log(f"{SUBOPTIMAL_FACADE_NAME} ({squad.name}): rolled a {rolled} for {wounds} - "
                  f"reanimated {detail}.")
        if self.placer is not None and getattr(self.placer, "is_busy", False):
            return            # _after_placement() resumes the charge
        self._waiting_placement = False
        self._finish()

    def _after_placement(self, _models=None):
        if not self._waiting_placement or (self.placer is not None and getattr(self.placer, "is_busy", False)):
            return
        self._waiting_placement = False
        self._finish()

    def _finish(self):
        resume, self._resume = self._resume, None
        if resume is not None:
            resume()
