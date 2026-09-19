"""The Weirdboy's Da Jump (2026-09 Ork codex, Mecha Orks stage G1).

RULE (verbatim, rules/orks/Weirdboy.md):
  "Da Jump (psychic level 1, once per army, per battle round): In your Movement
   phase, if this unit is not battle-shocked, you can make a psychic roll for
   this unit by rolling one D6. If you do:
   - On a 1, this unit is battle-shocked.
   - Place this unit in strategic reserves.
   - This unit has Deep Strike."

READ AS the Kill Rig's psychic abilities are (the plan's reading of the shared
frame): the effect lands on EVERY roll, and a 1 additionally battle-shocks the
unit. So use() throws the D6 and then applies both effects at once; the shock is
game/psychic_roll.py's, read on acknowledgement.

A PANEL BUTTON through game/proactive_stratagems.py, as Da Boss is Watchin' is:
"in your Movement phase ... you can" is a moment of the owner's choosing, not a
break point, and it costs no CP. "Your Movement phase" is read off the live clock
- the button is pressed while the phase runs, so game/phase_window.py does not
apply.

THE GATES, each a line of the printed text or of the engine:
  * the unit has the ability - unit_wide_ability() (rule 19.04), so a Boyz or
    Beast Snagga Boyz mob the Weirdboy supports jumps as ONE attached unit;
  * your Movement phase;
  * on the battlefield - "place this unit in strategic reserves" needs a unit
    that is not already there or embarked;
  * "once per army, per battle round" - game/per_army_round_limit.py, written
    onto the unit (Squad.da_jump_round, saved) like the boss motivations;
  * the psychic roll's own three - not battle-shocked, the Unstable Energies
    budget (psyker level 1, shared with Warpath), a free dice slot.
  * NOT MID-MOVE, an engine gate rather than a printed one: a unit whose move has
    started holds its origin in MovementController.move_start, and taking its
    models off the board under that move would strand it. Nothing else of the
    unit's phase is asked - the text does not forbid a unit that has moved, or an
    engaged one.

"PLACE THIS UNIT IN STRATEGIC RESERVES" is game/strategic_reserves.py's
withdraw_to_reserves(), the move every other withdrawal shares (it clears the
ingress lock and recomputes objective control). It comes back by the ordinary Ingress
move (rule 20.03/20.04, from battle round 2) - in this same phase if the round
allows, which is the engine's reading of Strategic Reserves and not something
this module adds.

"THIS UNIT HAS DEEP STRIKE" is a unit-level grant with no end, so it is a Squad
flag (da_jump_deep_strike, saved) read by IngressController._has_deep_strike()
- the one reader of rule 24.09 an arrival asks, also asked by the AI's landing
sweep. Not written onto the model profiles like Osteoclave Fulcrum: that grant is
made before the battle and re-applied on load, while this one is made mid-battle
and must survive a save by itself.

THE AI (ai/agent_driver.py's _handle_da_jump(), 0 API calls): jump a unit that
cannot reach a fight on foot this turn, is not holding an objective, and can
arrive this same phase.
"""

from game.per_army_round_limit import PerArmyRoundLimit
from game.squad import unit_wide_ability
from game.strategic_reserves import withdraw_to_reserves
from game.turn import PHASE_MOVEMENT

DA_JUMP_NAME = "Da Jump"
DA_JUMP_PSYCHIC_LEVEL = 1

#: The Squad flag the "(once per army, per battle round)" spend is written to.
DA_JUMP_LIMIT_FLAG = "da_jump_round"


def has_ability(squad):
    return squad is not None and bool(unit_wide_ability(squad, "da_jump"))


def grants_deep_strike(squad):
    """Read by game/ingress.py's _has_deep_strike()."""
    return squad is not None and bool(getattr(squad, "da_jump_deep_strike", False))


class DaJumpController:
    def __init__(self, psychic_roll, game_state=None, movement_controller=None, turn_tracker=None,
                 game_log=None, squads_provider=None):
        self.psychic_roll = psychic_roll
        self.game_state = game_state
        self.movement_controller = movement_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        # Every unit in the game, wherever it is - "per army" means the whole
        # army, reserves included (main.py hands over GameState.all_squads).
        self.squads_provider = squads_provider
        # One budget for every Weirdboy the army has. Per controller, as the
        # boss motivations hold theirs: its in-memory half must not outlive a
        # battle.
        self.limit = PerArmyRoundLimit(DA_JUMP_NAME, DA_JUMP_LIMIT_FLAG)

    def _squads(self):
        if self.squads_provider is None:
            return []
        return [s for s in self.squads_provider() if s is not None]

    def _battle_round(self):
        return getattr(self.turn_tracker, "battle_round", None)

    def panel_label(self, squad):
        return "%s (psychic level %d, no CP) - into Strategic Reserves with Deep Strike" % (
            DA_JUMP_NAME, DA_JUMP_PSYCHIC_LEVEL)

    def why_not(self, squad):
        """None when `squad` may use Da Jump right now, else the reason."""
        if not has_ability(squad):
            return "no Da Jump"
        tt = self.turn_tracker
        if tt is None or tt.phase != PHASE_MOVEMENT or tt.turn_owner != squad.owner:
            return "not your Movement phase"
        st = self.game_state
        if st is None or squad in st.reserves or squad in st.embarked_squads:
            return "not on the battlefield"
        if not any(m in st.tokens and not m.is_dead() for m in squad.models):
            return "not on the battlefield"
        starts = getattr(self.movement_controller, "move_start", None) or {}
        if any(m.id in starts for m in squad.models):
            return "its move is under way"
        pool = self._squads()
        if squad not in pool:
            pool.append(squad)
        if self.limit.is_spent(squad.owner, self._battle_round(), pool):
            return "already used by this army this battle round"
        if self.psychic_roll is None:
            return "no psychic roll"
        return self.psychic_roll.why_not(squad, DA_JUMP_PSYCHIC_LEVEL)

    def can_use(self, squad):
        return self.why_not(squad) is None

    def use(self, squad):
        if not self.can_use(squad):
            return False
        if not self.psychic_roll.roll(squad, DA_JUMP_NAME, DA_JUMP_PSYCHIC_LEVEL):
            return False
        self.limit.spend(squad.owner, self._battle_round(), squad)
        squad.da_jump_deep_strike = True
        withdraw_to_reserves(
            self.game_state, squad, log=self.game_log,
            message="%s: %s uses %s - into Strategic Reserves, with Deep Strike."
                    % (squad.owner, squad.name, DA_JUMP_NAME))
        # The panel hangs off the picked unit; a pick left on a unit that is no
        # longer on the board would offer it a Move for models that are not there.
        mc = self.movement_controller
        if mc is not None and getattr(mc, "selected_squad", None) is squad:
            mc.select(None)
        return True
