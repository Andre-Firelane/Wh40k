"""Awakened Dynasty Stratagem: "Protocol of the Sudden Storm".

RULE (printed, word for word):
  WHEN:   "Your Movement phase."
  TARGET: "One NECRONS unit from your army."
  EFFECT: "Until the end of the turn, ranged weapons equipped by models in your
           unit have the [ASSAULT] ability. In addition, if a NECRONS CHARACTER
           is leading your unit, until the end of the phase, you can re-roll
           Advance rolls made for your unit."

TWO CLAUSES WITH TWO DIFFERENT CLOCKS, and that is printed, not a slip: the
[ASSAULT] grant lasts until the end of the TURN, the Advance re-roll only until
the end of the PHASE. They are therefore expired by two different callers, and
each flag is named after its own lifetime so the difference cannot be tidied
away by someone clearing both in one place.

WHY [ASSAULT] IS WORTH BUYING: rule 10.05 lets a unit that Advanced still shoot
with [ASSAULT] weapons. So this is the Stratagem that turns a Necron unit's
Advance from "I gave up shooting" into "I closed the distance and shot anyway",
which is also what makes the AI's gate below the right one - it is worthless to
a unit that was not going to Advance.

WHERE THE EFFECT IS READ: ShootingController's _adjusted_weapon() chain, like
every other keyword grant; and game/movement.py's Advance re-roll site for the
second clause.
"""

import copy

from game import ai_mode, awakened_dynasty
from game.stratagems import Stratagem
from game.weapons import RANGED

SUDDEN_STORM_CP_COST = 1
SUDDEN_STORM_NAME = "Protocol of the Sudden Storm"
#: A D6 Advance averages 3.5, so re-rolling a 4+ loses on average.
ADVANCE_REROLL_FLOOR = 4


def is_active(squad):
    """The [ASSAULT] half - until the end of the TURN."""
    return bool(getattr(squad, "sudden_storm_active", False))


def advance_reroll_available(squad):
    """The second half - until the end of the PHASE, and only while a CHARACTER
    is actually leading."""
    if not getattr(squad, "sudden_storm_advance_reroll", False):
        return False
    return awakened_dynasty.is_led_by_character(squad)


def adjusted_weapon(weapon, squad):
    """[ASSAULT] on ranged weapons while the grant is up."""
    if weapon is None or not is_active(squad):
        return weapon
    if weapon.weapon_type != RANGED or weapon.assault:
        return weapon
    granted = copy.copy(weapon)
    granted.assault = True
    return granted


class SuddenStormController:
    def __init__(self, stratagem_controller, turn_tracker=None, game_log=None,
                 dice_manager=None, decision_manager=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.auto_players = ai_mode.players(auto_players)
        self._stratagem = Stratagem(name=SUDDEN_STORM_NAME, cp_cost=SUDDEN_STORM_CP_COST,
                                    effect=self._grant)

    def reset_phase(self, squads=()):
        """Only the Advance re-roll - "until the end of the phase". The
        [ASSAULT] grant deliberately survives this; see expire_for_turn()."""
        for squad in squads or ():
            squad.sudden_storm_advance_reroll = False

    def expire_for_turn(self, squads=()):
        """The [ASSAULT] half - "until the end of the turn"."""
        for squad in squads or ():
            squad.sudden_storm_active = False
            squad.sudden_storm_advance_reroll = False

    def can_use(self, squad):
        if squad is None or is_active(squad):
            return False
        if not awakened_dynasty.stratagem_target_ok(squad):
            return False
        if self.turn_tracker is not None:
            from game.turn import PHASE_MOVEMENT
            # "YOUR Movement phase" - the phase, and whose it is.
            if self.turn_tracker.phase != PHASE_MOVEMENT:
                return False
            if squad.owner != self.turn_tracker.turn_owner:
                return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def maybe_offer_advance_reroll(self, squad):
        """The second clause: "you can re-roll Advance rolls made for your
        unit". Called from main.py right after an Advance roll is acknowledged.

        A D6 Advance averages 3.5, so the AI re-rolls anything below
        ADVANCE_REROLL_FLOOR and keeps the rest - the same "re-rolling an
        average result wins nothing" reasoning game/reanimation_protocols.py's
        should_reroll() uses for its D3. A die that has already used its one
        re-roll is left alone (DiceManager.already_rerolled), so a Command
        Re-roll and this cannot both throw it."""
        if self.dice_manager is None or not advance_reroll_available(squad):
            return False
        if not self.dice_manager.rerollable_indices():
            return False
        values = self.dice_manager.pending_values or self.dice_manager.last_values or []
        if not values:
            return False
        # ONCE per roll. Declining used to leave the die on the table with
        # nothing changed, so the next click asked again - see
        # DiceManager.claim_reroll_offer().
        if not self.dice_manager.claim_reroll_offer(SUDDEN_STORM_NAME):
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            if values[0] >= ADVANCE_REROLL_FLOOR:
                return False
            return bool(self.dice_manager.reroll_die(0))
        self.decision_manager.request(
            squad.owner,
            f"{squad.name} advanced {values[0]}\" - re-roll it? "
            f"({SUDDEN_STORM_NAME})",
            [("Re-roll the Advance", lambda: self.dice_manager.reroll_die(0)),
             ("Keep it", None)],
        )
        return True

    def _grant(self, controller, player, targets):
        squad = targets[0]
        squad.sudden_storm_active = True
        squad.sudden_storm_advance_reroll = True
        if self.game_log is not None:
            extra = (" and can re-roll Advance rolls this phase"
                     if awakened_dynasty.is_led_by_character(squad) else "")
            self.game_log.add(
                f"{SUDDEN_STORM_NAME}: {squad.name}'s ranged weapons have [ASSAULT] "
                f"until the end of the turn{extra}.")
