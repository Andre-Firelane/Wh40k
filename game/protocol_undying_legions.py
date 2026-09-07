"""Awakened Dynasty Stratagem: "Protocol of the Undying Legions".

RULE (printed, word for word):
  WHEN:   "Your opponent's Shooting phase or the Fight phase, just after an
           enemy unit has resolved its attacks."
  TARGET: "One NECRONS unit from your army that had one or more of its models
           destroyed as a result of the attacking unit's attacks."
  EFFECT: "Your unit activates its Reanimation Protocols and reanimates D3
           wounds (or D3+1 wounds if a NECRONS CHARACTER is leading your unit)."

THE WHOLE EFFECT IS THE ARMY RULE, so this module does not restate any of it:
game/reanimation_protocols.py's reanimate() already knows about healing before
reviving, the CHARACTER exclusion, the starting-strength cap and the placement
rules. This is a Stratagem that buys an extra activation of it, nothing more.
That is also why the +1 is applied to the DICE RESULT rather than modelled as a
different die - "D3+1" is a D3 with 1 added, not a D4.

WHEN IT FIRES is the same instant 'Ard as Nails, Stim Injectors, Forewarned and
Psychic Shield react to, so it goes in the same target_reactions lists - except
that those fire "just after an enemy unit has SELECTED ITS TARGETS" and this one
fires "just after an enemy unit has RESOLVED its attacks". Different moment, so
it hangs off the after-resolution hook instead: shooting.py's
on_squad_finished_shooting and fight.py's on_unit_finished_fighting.

THE AI'S ANSWER IS DETERMINISTIC and shares the gate every other Necron
recovery decision uses - recoverable_wounds(). A unit that can only turn one
wound into something is not worth a CP, and one that can use several is; the
threshold is named rather than inlined so the two Necron CP decisions
(this and the Resurrection Orb) can be compared side by side.
"""

from game import ai_mode, awakened_dynasty, reanimation_protocols
from game.stratagems import Stratagem

UNDYING_LEGIONS_CP_COST = 1
UNDYING_LEGIONS_NAME = "Protocol of the Undying Legions"
UNDYING_LEGIONS_DICE_SIDES = 3
UNDYING_LEGIONS_LED_BONUS = 1
#: How much a unit must be able to recover before the AI spends a CP on it.
#: Below the Resurrection Orb's 4, because this costs 1 CP rather than a
#: once-per-battle piece of wargear.
UNDYING_LEGIONS_MIN_RECOVERABLE = 2


class UndyingLegionsController:
    """Reactive. Wired into main.py's after-attacks hooks; a human is prompted,
    the AI answers from is_worth_using() - the same auto_players split
    game/ard_as_nails.py uses, so both routes share one verdict."""

    def __init__(self, stratagem_controller, dice_manager=None, decision_manager=None,
                 game_log=None, game_state=None, position_valid=None, auto_players=(),
                 placer=None):
        self.stratagem_controller = stratagem_controller
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.game_state = game_state
        self.position_valid = position_valid
        self.auto_players = ai_mode.players(auto_players)
        # ReturnPlacementController - rule 01.02.03's "set up" half, the same
        # one ReanimationProtocolsController holds. This Stratagem is a SECOND
        # DOOR into reanimate(), so it needs its own; without it a human's
        # models reappeared wherever the engine put them while the army rule
        # itself asked (user: "Einheiten wurde automatisch platziert bei
        # protocol of the undying legion, obwohl ich necrons spiele").
        self.placer = placer
        self._pending = None
        self._stratagem = Stratagem(
            name=UNDYING_LEGIONS_NAME, cp_cost=UNDYING_LEGIONS_CP_COST,
            effect=self._resolve,
            # A unit can be shot at by several enemy units in one phase, and
            # each time is its own "just after that unit resolved its attacks"
            # window - so 15.01's once-per-target-per-phase would be wrong here.
            allow_repeat_target=True,
        )

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _tokens(self):
        return list(self.game_state.tokens) if self.game_state is not None else []

    @property
    def is_busy(self):
        return self._pending is not None

    def can_use(self, squad):
        if squad is None or self._pending is not None:
            return False
        if not awakened_dynasty.stratagem_target_ok(squad):
            return False
        if not squad.destroyed_models:
            return False   # "had one or more of its models destroyed"
        if reanimation_protocols.recoverable_wounds(squad) <= 0:
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def is_worth_using(self, squad):
        """The AI's deterministic gate."""
        return (self.can_use(squad)
                and reanimation_protocols.recoverable_wounds(squad)
                >= UNDYING_LEGIONS_MIN_RECOVERABLE)

    def maybe_offer(self, target_squad):
        """Called from the after-attacks hooks with the unit that was shot at
        or fought. Returns True if anything was used or prompted."""
        if not self.can_use(target_squad):
            return False
        if target_squad.owner in self.auto_players:
            if not self.is_worth_using(target_squad):
                return False
            return self.use(target_squad)
        if self.decision_manager is None:
            return False
        self.decision_manager.request(
            target_squad.owner,
            f"{target_squad.name} lost models - use {UNDYING_LEGIONS_NAME}? "
            f"({UNDYING_LEGIONS_CP_COST} CP)",
            [(f"Use {UNDYING_LEGIONS_NAME}", lambda: self.use(target_squad)),
             ("Decline", None)],
            is_stratagem=True,
        )
        return True

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _resolve(self, controller, player, targets):
        squad = targets[0]
        self._pending = squad
        if self.dice_manager is None:
            self._apply(squad, UNDYING_LEGIONS_DICE_SIDES)
            return
        self.dice_manager.roll(
            1, UNDYING_LEGIONS_DICE_SIDES, label=UNDYING_LEGIONS_NAME,
            target_name=squad.name, target_squad=squad, subject_label="Reanimating")

    def on_dice_acknowledged(self):
        if self._pending is None:
            return False
        values = (self.dice_manager.last_values if self.dice_manager is not None else None) or [1]
        self._apply(self._pending, values[0])
        return True

    def _apply(self, squad, rolled):
        self._pending = None
        wounds = rolled
        if awakened_dynasty.is_led_by_character(squad):
            wounds += UNDYING_LEGIONS_LED_BONUS   # "or D3+1 ... if a CHARACTER is leading"
        spent, revived = reanimation_protocols.reanimate(
            squad, wounds,
            all_tokens=self._tokens(),
            position_valid=self.position_valid,
            game_state=self.game_state,
            placer=self.placer,
        )
        detail = f"{spent} wound(s)"
        if revived:
            detail += f", {len(revived)} model(s) back on the battlefield"
        self._log(f"{UNDYING_LEGIONS_NAME} ({squad.name}): rolled a {rolled} for {wounds} - "
                  f"reanimated {detail}.")
