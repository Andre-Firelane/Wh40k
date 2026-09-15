"""War Horde Enhancement: Da Boss is Watchin' (25 pts).

RULE (verbatim, rules/orks/detachments/War Horde.md):
  "ORKS model only. (Once per battle, per army) In your Movement phase, you can
   use this ability. If you do, this unit is riled up until the start of your
   next turn."

A PANEL BUTTON through game/proactive_stratagems.py. The registry needs only
can_use / use / panel_label, and an Enhancement ability costs no CP, so there is
no Stratagem object and no rule 15.01 ledger here. NAMED: the registry draws
every button in the Stratagem accent, so the label says "no CP" and the colour
cannot mislead on its own.

"YOUR MOVEMENT PHASE" is read off the live clock, and that is right here: the
button is pressed while the phase is under way, not answered at a phase
boundary, so game/phase_window.py does not apply.

"ONCE PER BATTLE, PER ARMY" is a spend, so it is written onto the unit that used
it (Squad.da_boss_is_watchin_used, in activation_state.SQUAD_FLAGS) and read
back over every unit the player has - game/war_cry.py's arrangement, so a save
keeps it. Two bearers in one army share the one use.

"THIS UNIT IS RILED UP" goes through game/riled_up.py's grant(), which refuses a
unit without the Waaagh! ability and never shortens a longer grant; the
deadline is "until the start of your next turn".

THE AI (ai/agent_driver.py's _handle_da_boss()): for a unit that is not riled up
and has an enemy within its Advance reach plus a charge.
"""

from game import enhancements, riled_up
from game.turn import PHASE_MOVEMENT

DA_BOSS_IS_WATCHIN = "Da Boss is Watchin'"


class DaBossIsWatchinController:
    def __init__(self, turn_tracker=None, squads_provider=None, game_log=None):
        self.turn_tracker = turn_tracker
        # Every unit in the game, wherever it is - main.py hands over
        # GameState.all_squads, because "per army" means the whole army.
        self.squads_provider = squads_provider
        self.game_log = game_log

    def _squads(self):
        if self.squads_provider is None:
            return []
        return [s for s in self.squads_provider() if s is not None]

    def is_used(self, player, squad=None):
        """Whether `player`'s army has already used it. `squad` is counted too,
        so a harness without a squads_provider still sees its own spend."""
        pool = self._squads()
        if squad is not None and squad not in pool:
            pool.append(squad)
        return any(getattr(s, "da_boss_is_watchin_used", False)
                   for s in pool if getattr(s, "owner", None) == player)

    def panel_label(self, squad):
        return f"{DA_BOSS_IS_WATCHIN} (no CP, once per battle) - riled up until your next turn"

    def can_use(self, squad):
        tt = self.turn_tracker
        if squad is None or tt is None:
            return False
        if tt.phase != PHASE_MOVEMENT or squad.owner != tt.turn_owner:
            return False
        if not enhancements.is_active(squad, DA_BOSS_IS_WATCHIN):
            return False
        if not riled_up.has_ability(squad):
            return False
        return not self.is_used(squad.owner, squad)

    def use(self, squad):
        if not self.can_use(squad):
            return False
        deadline = riled_up.until_start_of_your_next_turn(self.turn_tracker, squad.owner)
        if not riled_up.grant(squad, deadline, self.turn_tracker):
            return False
        squad.da_boss_is_watchin_used = True
        if self.game_log is not None:
            self.game_log.add(f"{DA_BOSS_IS_WATCHIN}: {squad.name} is riled up until the start of "
                              f"{squad.owner}'s next turn.")
        return True
