"""Deffkoptas' Aerial Manoover (2026-09 Ork codex, stage E3d).

RULE (verbatim, rules/orks/Deffkoptas.md):
  "Aerial Manoover: At the end of your opponent's Fight phase, if this unit is
   unengaged, you can place this unit in strategic reserves."

AIRBORNE AGILITY'S SHAPE (game/airborne_agility.py) AT A DIFFERENT SEAM. The
Vespids go "at the end of your opponent's TURN", the Deffkoptas "at the end of
your opponent's FIGHT PHASE". Fight is the last phase, so both land in the same
advance_turn_phase() call - but the printed seam is the end-of-Fight-phase block,
and there the offer takes `mover_before`, never the turn_owner that
advance_phase() has already flipped (test_event_chain_wiring.py section 8).

"YOUR OPPONENT'S" - offered to every player who is NOT the one whose Fight phase
just ended. can_use() reads no clock (section 15): the window is the seam itself,
and a human answers frames later while the decision holds the game.

"THIS UNIT" is per unit, so EVERY eligible unit is asked, one prompt at a time,
through game/per_unit_offer.py - the Vespid report that built that module.

"UNENGAGED" is rule 03.04, asked through game/engagement.py (living models only,
so an enemy wiped out this phase does not keep the unit engaged).

NEVER OFFERED WHEN IT CANNOT COME BACK: at the end of battle round 3 main.py
destroys the unarrived reserves in the same advance_turn_phase() call (rule
20.03), and after the battle's last turn there is nothing to come back to (rule
20.01.02). Both are game/strategic_reserves.withdrawal_is_doomed() - the same
refusal Hyperphasing makes, for the same reason: a question whose only answer
destroys the unit is not a choice.

A REPOSITIONED UNIT (rule 20.02). The move itself is
strategic_reserves.withdraw_to_reserves(), which clears ingress_locked and
recomputes objective control. The unit's return is an ordinary ingress move - on
which its own Deff from Above then gives +1 to hit.

THE AI USES IT deterministically (0 API calls): main.py injects `choose`, which
is ai/agent_driver.py's aerial_manoover_choice() - Hyperphasing's "rescue or
reposition" policy without a cap. game/ must not import ai/.
"""

from game import ai_mode, engagement, per_unit_offer
from game.squad import unit_wide_ability
from game.strategic_reserves import withdraw_to_reserves, withdrawal_is_doomed

AERIAL_MANOOVER_NAME = "Aerial Manoover"


def has_ability(squad):
    return squad is not None and bool(unit_wide_ability(squad, "aerial_manoover"))


class AerialManooverController:
    def __init__(self, decision_manager=None, game_state=None, game_log=None, turn_tracker=None,
                 auto_players=(), choose=None):
        self.decision_manager = decision_manager
        self.game_state = game_state
        self.game_log = game_log
        self.turn_tracker = turn_tracker
        self.auto_players = ai_mode.players(auto_players)
        #: The AI's policy: choose(candidates) -> the units to withdraw. None
        #: withdraws nothing for an auto player.
        self.choose = choose

    def _tokens(self):
        return getattr(self.game_state, "tokens", None) or []

    def can_use(self, squad):
        if not has_ability(squad) or self.game_state is None:
            return False
        if getattr(squad, "embarked_in", None) is not None:
            return False
        tokens = self._tokens()
        if not any(m in tokens for m in squad.models if not m.is_dead()):
            return False
        if engagement.is_engaged(squad, tokens):
            return False
        return not withdrawal_is_doomed(self.turn_tracker)

    def eligible_squads(self, squads, player):
        return sorted((s for s in squads if s.owner == player and self.can_use(s)),
                      key=lambda s: s.name)

    def offer_at_end_of_fight_phase(self, squads, mover_before):
        """`mover_before` is the player whose Fight phase just ended; the offer
        goes to everyone else. Returns True if anything was asked or done."""
        others = sorted({s.owner for s in squads if s is not None and s.owner != mover_before})
        acted = False
        for player in others:
            eligible = self.eligible_squads(squads, player)
            if not eligible:
                continue
            if player in self.auto_players:
                chosen = list(self.choose(eligible)) if self.choose is not None else []
                for squad in chosen:
                    acted = self.use(squad) or acted
                continue
            acted = per_unit_offer.offer_each(
                self.decision_manager, eligible, self.can_use,
                lambda s: ("%s: %s - place this unit in Strategic Reserves?"
                           % (s.name, AERIAL_MANOOVER_NAME)),
                lambda s: [("Go into Strategic Reserves", lambda t=s: self.use(t)),
                           ("Stay on the battlefield", None)]) or acted
        return acted

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return withdraw_to_reserves(
            self.game_state, squad, log=self.game_log,
            message="%s: %s uses %s and is placed in Strategic Reserves."
                    % (squad.owner, squad.name, AERIAL_MANOOVER_NAME))
