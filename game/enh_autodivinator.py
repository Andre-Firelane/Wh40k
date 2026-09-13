"""Canoptek Court Enhancement: Autodivinator (15 pts).

RULE (verbatim, rules/necrons/detachments/Canoptek Court.md):
  "CRYPTEK model only. Each time your opponent gains a CP as the result of an
   ability, roll one D6: on a 2+, you also gain 1CP."

  FAQ: "Does the Canoptek Court Autodivinator Enhancement trigger when army rule
  effects such as Code Chivalric (Imperial Knights) award a player CP, or when an
  opponent discards a Secondary Mission card for 1CP? - No in both cases. It only
  triggers when your opponent gains CP as the result of an ability (not any other
  kind of rule)."

THE HALF THAT NEEDED A NEW SEAM IS "AS THE RESULT OF AN ABILITY"
-----------------------------------------------------------------
CommandPointManager had no idea WHY a CP was gained, and the FAQ makes that the
whole rule. So game/command_points.py's gain_cp() now takes a required `source=`
(SOURCE_ABILITY / SOURCE_MISSION) and fires on_cp_gained listeners with it. Core
CP (08.02) goes through gain_core_cp() and never reaches a listener at all.
test_necron_canoptek_court.py pins, by AST, that every gain_cp() call names its
source - a new CP grant cannot join the engine without deciding what it is.

THE DIE IS ROLLED IN-MODULE, a deliberate exception to this engine's "every die
is visible" habit, and for the reason game/reanimation_boost.py records for the
Reanimator's beam: the trigger can land in the middle of someone else's dice
window (a Command-phase ability's own roll, a Stratagem's), and DiceManager holds
ONE pending roll. The roll and its result are logged instead.

NEVER A DIE THAT CANNOT PAY. The user's house rule caps bonus CP at one per battle
round; with nothing left under it the D6 is not thrown - game/coordinated_
leadership.py's line, for the same reason.

"YOU ALSO GAIN 1CP" IS ITSELF A CP GAINED FROM AN ABILITY, so an opponent's own
Autodivinator can answer it. That is the printed rule working in a mirror match,
and the cap is what ends the exchange.
"""

from game import command_points as command_points_module
from game import enhancements

AUTODIVINATOR = "Autodivinator"
AUTODIVINATOR_THRESHOLD = 2


class AutodivinatorController:
    def __init__(self, command_points=None, game_state=None, turn_tracker=None, game_log=None):
        self.command_points = command_points
        self.game_state = game_state
        self.turn_tracker = turn_tracker
        self.game_log = game_log

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _squads(self):
        state = self.game_state
        if state is None:
            return []
        if hasattr(state, "all_squads"):
            return list(state.all_squads())
        seen, out = set(), []
        for token in getattr(state, "tokens", ()) or ():
            squad = getattr(token, "squad", None)
            if squad is not None and id(squad) not in seen:
                seen.add(id(squad))
                out.append(squad)
        return out

    def bearer_for(self, player):
        """A living Autodivinator bearer in `player`'s army - on the battlefield
        or not: "your army" is the whole army, reserves included."""
        for squad in self._squads():
            if getattr(squad, "owner", None) == player and enhancements.is_active(squad, AUTODIVINATOR):
                return squad
        return None

    def on_cp_gained(self, player, amount, source=None, battle_round=None, reason=None):
        """CommandPointManager.on_cp_gained's listener. `player` is whoever just
        gained; the Autodivinator belongs to their opponent."""
        if source != command_points_module.SOURCE_ABILITY or amount <= 0:
            return 0
        if self.command_points is None:
            return 0
        gained = 0
        for opponent in sorted(p for p in self.command_points.cp if p != player):
            bearer = self.bearer_for(opponent)
            if bearer is None:
                continue
            for _ in range(int(amount)):
                if self.command_points.bonus_cp_remaining(opponent, battle_round) <= 0:
                    self._log(f"[autodivinator] {opponent}: {player} gained a CP from an ability, "
                              "but the bonus-CP cap is already reached - no roll.", file_only=True)
                    break
                from game import dice
                rolled = dice.random.randint(1, 6)
                if rolled >= AUTODIVINATOR_THRESHOLD:
                    self._log(f"{AUTODIVINATOR} ({bearer.name}): {player} gained a CP "
                              f"({reason or 'ability'}) - rolled a {rolled}, {opponent} gains 1CP too.")
                    gained += self.command_points.gain_cp(
                        opponent, battle_round, amount=1, reason=AUTODIVINATOR,
                        source=command_points_module.SOURCE_ABILITY)
                else:
                    self._log(f"{AUTODIVINATOR} ({bearer.name}): {player} gained a CP - "
                              f"rolled a {rolled}, no CP.")
        return gained
