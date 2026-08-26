"""Awakened Dynasty Stratagem: "Protocol of the Conquering Tyrant".

RULE (printed, word for word):
  WHEN:   "Your Shooting phase."
  TARGET: "One NECRONS unit from your army that has not been selected to shoot
           this phase."
  EFFECT: "Until the end of the phase, each time a model in your unit makes an
           attack that targets a unit within half range, re-roll a Hit roll of
           1. If a NECRONS CHARACTER is leading your unit, until the end of the
           phase, you can re-roll the Hit roll for that attack instead."

THE SAME TWO-CLAUSE SHAPE the Necron datasheets already use - "re-roll a 1",
upgraded by "INSTEAD" to an optional re-roll of the whole roll - so it registers
in game/reroll_scope.py alongside Swift Demise, Hard-wired for Destruction,
Whirling Onslaught and Implacable Eradication rather than inventing a second
arrangement. That is also what stops the offer including "failures only", which
would let a 2 that missed be thrown again.

WHAT MAKES IT DIFFERENT FROM ITS FOUR COUSINS: the condition is not about the
attacker or the target's keywords but about DISTANCE - "a unit within half
range" - which is per WEAPON, since half range is half of that weapon's own
Range characteristic. So applies() takes the attacking pairs and the target
unit and measures it the same way [RAPID FIRE X] and [MELTA X] already do.

HALF RANGE IS READ THROUGH game/weapon_range.py, not off weapon.range_in: that
module exists because two abilities already extend a weapon's range, and a
second opinion about what half range means is exactly the drift this repo keeps
consolidating away.
"""

from game import awakened_dynasty, weapon_range
from game.squad import edge_distance
from game.stratagems import Stratagem

CONQUERING_TYRANT_CP_COST = 1
CONQUERING_TYRANT_NAME = "Protocol of the Conquering Tyrant"
CONQUERING_TYRANT_LABEL = "Conquering Tyrant"


def is_active(squad):
    return bool(getattr(squad, "conquering_tyrant_active", False))


def applies(squad, weapon, pairs, target_squad):
    """The base clause: the grant is up AND the target is within half range.

    `pairs` and `target_squad` rather than a pre-measured distance, because
    that is how every other half-range test in game/shooting.py is written
    ([RAPID FIRE X], [MELTA X]) - true if ANY attacking model is within half
    range of ANY target model, the same representative-group simplification.
    Measuring it a second way here would be the drift this repo consolidates
    away, and half range is read through game/weapon_range.py for the same
    reason: two abilities already extend a weapon's range."""
    if weapon is None or not is_active(squad) or not pairs or target_squad is None:
        return False
    return any(
        edge_distance(shooter, defender) <= weapon_range.half_range_in(shooter, weapon)
        for shooter, _ in pairs
        for defender in target_squad.models if not defender.is_dead()
    )


def offers_full_reroll(squad, weapon, pairs, target_squad):
    """The upgrade: the same condition, plus a CHARACTER leading the unit."""
    return (applies(squad, weapon, pairs, target_squad)
            and awakened_dynasty.is_led_by_character(squad))


class ConqueringTyrantController:
    def __init__(self, stratagem_controller, turn_tracker=None, shooting_controller=None,
                 game_log=None):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.shooting_controller = shooting_controller
        self.game_log = game_log
        self._stratagem = Stratagem(name=CONQUERING_TYRANT_NAME,
                                    cp_cost=CONQUERING_TYRANT_CP_COST, effect=self._grant)

    def reset_phase(self, squads=()):
        for squad in squads or ():
            squad.conquering_tyrant_active = False

    def can_use(self, squad):
        if squad is None or is_active(squad):
            return False
        if not awakened_dynasty.stratagem_target_ok(squad):
            return False
        if self.turn_tracker is not None:
            from game.turn import PHASE_SHOOTING
            if self.turn_tracker.phase != PHASE_SHOOTING:
                return False
            if squad.owner != self.turn_tracker.turn_owner:
                return False
        # "that has not been selected to shoot this phase" - read from the
        # engine's own ledger rather than re-derived.
        if self.shooting_controller is not None:
            if squad in getattr(self.shooting_controller, "shot_squad_ids", ()) or ():
                return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        squad = targets[0]
        squad.conquering_tyrant_active = True
        if self.game_log is not None:
            extra = (" - and the whole Hit roll, since a CHARACTER is leading it"
                     if awakened_dynasty.is_led_by_character(squad) else "")
            self.game_log.add(
                f"{CONQUERING_TYRANT_NAME}: {squad.name} re-rolls Hit rolls of 1 against "
                f"targets within half range this phase{extra}.")
