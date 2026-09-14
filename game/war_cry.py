"""War Cry - the once-per-battle half of the Orks army rule Waaagh!.

PRINTED (rules/orks/army_rules.md):

    War Cry (Once per battle, per army): At the start of the Command phase, you
    can use this ability. If you do, friendly ORKS units with the Waaagh!
    ability are riled up until the end of the next turn.

THREE WORDS DO THE WORK
-----------------------
  * "THE Command phase", not "your Command phase" - so it is offered at the
    start of EVERY Command phase, the opponent's included (user decision, taken
    literally). Used in the opponent's Command phase, "the next turn" is the
    user's own: the army is riled up through the enemy turn and into its own.
  * "per ARMY" - one use per player, and only for a player whose army has the
    ability at all (game/waaagh.py's qualifying_players()). Gated HERE rather
    than in the AI, so the human's prompt gets the same answer; the old rule was
    once called by a Necron army for exactly the want of this gate.
  * "friendly ORKS units with the Waaagh! ability" - every such unit the player
    has, wherever it is: on the board, in Strategic Reserves or embarked.
    game/riled_up.py's grant() refuses anything without the ability.

WHO ANSWERS
-----------
A human is ASKED at the start of each Command phase until they use it - a
prompt with a red Decline. The AI answers inside this controller, through an
injected `verdict(player, turn_tracker)` (ai/agent_driver.py's
war_cry_verdict()), so it costs no API call and game/ never imports ai/.

SAVED ACROSS A LOAD. "Once per battle" is a spend, and a mid-battle save that
forgot it would hand the army a second one. Rather than a new snapshot slot, the
use is written onto every unit it reached (Squad.war_cry_called, in
activation_state.SQUAD_FLAGS) and is_used() reads it back - the same "a paid
grant lives on the unit" arrangement every other one-turn grant here uses.
"""

from game import ai_mode, riled_up

WAR_CRY_NAME = "War Cry"
USE_LABEL = "Use War Cry"
DECLINE_LABEL = "Decline"
PLAYERS = ("Player 1", "Player 2")


class WarCryController:
    def __init__(self, turn_tracker=None, decision_manager=None, game_log=None,
                 auto_players=(), squads_provider=None, verdict=None):
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        # Every unit in the game, wherever it is - main.py hands over
        # GameState.all_squads, because the grant reaches Reserves and
        # passengers too.
        self.squads_provider = squads_provider
        # The AI's answer, injected by main.py: verdict(player, turn_tracker)
        # -> bool. None means the AI never uses it.
        self.verdict = verdict
        self.used_players = set()
        # WHOSE army rule this is. None means "nobody has told me" and lifts the
        # restriction, so a harness that never sets it keeps working; an EMPTY
        # set is a real answer ("nobody fields Orks") and refuses. A truthiness
        # test would read the empty set as "unknown" and re-open the bug.
        self.orks_players = None
        self.on_used = None  # optional callable(player) - main.py's notice overlay

    # ------------------------------------------------------------ questions
    def _squads(self):
        if self.squads_provider is None:
            return []
        return [s for s in self.squads_provider() if s is not None]

    def is_used(self, player):
        if player in self.used_players:
            return True
        return any(getattr(s, "war_cry_called", False)
                   for s in self._squads() if s.owner == player)

    def can_use(self, player):
        if self.orks_players is not None and player not in self.orks_players:
            return False
        if self.is_used(player):
            return False
        return True

    def is_active(self, player):
        """Whether any of this player's units is riled up right now."""
        return any(riled_up.is_riled_up(s) for s in self._squads() if s.owner == player)

    # ------------------------------------------------------------ the offer
    def offer_at_start_of_command_phase(self, turn_tracker=None):
        """Called at the start of EVERY Command phase. The phase's owner is
        asked first, then the other player - the order the phase is played in.
        Returns how many prompts it opened."""
        tracker = turn_tracker if turn_tracker is not None else self.turn_tracker
        owner = getattr(tracker, "turn_owner", None)
        order = sorted(PLAYERS, key=lambda p: (p != owner, p))
        opened = 0
        for player in order:
            if not self.can_use(player):
                continue
            if not any(riled_up.has_ability(s) for s in self._squads() if s.owner == player):
                continue
            if player in self.auto_players:
                if self.verdict is not None and self.verdict(player, tracker):
                    self.use(player, tracker)
                continue
            if self.decision_manager is None:
                continue
            self.decision_manager.request(
                player,
                "%s (once per battle): make every unit with the Waaagh! ability riled up until "
                "the end of the next turn - 5+ invulnerable save, [ASSAULT] on ranged attacks, and "
                "an Advance no longer stops a charge?" % WAR_CRY_NAME,
                [(USE_LABEL, lambda p=player, t=tracker: self.use(p, t)),
                 (DECLINE_LABEL, None)],
            )
            opened += 1
        return opened

    def use(self, player, turn_tracker=None):
        tracker = turn_tracker if turn_tracker is not None else self.turn_tracker
        if not self.can_use(player):
            return False
        self.used_players.add(player)
        deadline = riled_up.until_end_of_next_turn(tracker)
        reached = []
        for squad in self._squads():
            if squad.owner != player:
                continue
            if riled_up.grant(squad, deadline, tracker):
                squad.war_cry_called = True
                reached.append(squad)
        if self.game_log is not None:
            self.game_log.add(
                "%s uses %s: %d unit(s) with the Waaagh! ability are riled up until the end of "
                "the next turn." % (player, WAR_CRY_NAME, len(reached)))
        if self.on_used is not None:
            self.on_used(player)
        return True
