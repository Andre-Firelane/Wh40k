"""A capped end-of-opponent-turn withdrawal into Strategic Reserves.

SECOND CONSUMER, so it is extracted. Two detachment rules print the same
paragraph with a different unit filter:

  * Windrider Host's Ride the Wind (game/ride_the_wind.py): "at the end of your
    opponent's turn, you can select a number of ASURYANI MOUNTED or VYPER units
    from your army (excluding units within Engagement Range of one or more enemy
    units), then remove those units from the battlefield and place them into
    Strategic Reserves. The maximum number of units you can select depends on
    the battle size".
  * Hypercrypt Legion's Hyperphasing (game/hypercrypt_hyperphasing.py): the same
    sentence for "a number of NECRONS units".

WHAT IS SHARED is everything that is easy to get subtly wrong, and both halves
of that have been wrong in this repo before:

  * "at the end of your OPPONENT'S turn" - offered to whoever did NOT end the
    turn, the timing most easily read backwards (Airborne Agility records it).
  * EVERY eligible unit is asked, one prompt at a time, through
    game/per_unit_offer.py - and the cap is re-asked before each prompt, because
    the prompt prints how much of it is left and only an earlier answer can move
    that number. Asked once, it could never read anything but the full allowance
    (the Vespid report that built that module).
  * The counter resets HERE and not inside the chain: the chain re-enters
    offer_each(), never this method, so a mid-chain answer cannot hand the
    player back a fresh allowance.
  * The move itself is game/strategic_reserves.withdraw_to_reserves(), which also
    clears ingress_locked and recomputes objective control.

WHAT EACH RULE OWNS: which units qualify (applies()), the cap (limit(), which
takes the player because a Hypercrypt Enhancement raises it for its bearer's
army), and its own words (prompt_for(), withdraw_message()).

THE AI. An `auto_players` owner is never prompted. Without a `choose` callable
it is simply filtered out of the candidates - Ride the Wind's standing "no AI
path" (pulling a unit off the board is a whole-army judgement), unchanged by
this extraction. WITH one, the owner's eligible units are handed to
`choose(candidates, cap)` synchronously and whatever it returns is withdrawn.
game/ must not import ai/, so main.py injects that policy - Hyperphasing's
"Retten + Umpositionieren" lives in ai/agent_driver.py.
"""

from game import ai_mode, per_unit_offer
from game.strategic_reserves import withdraw_to_reserves


class EndOfTurnWithdrawalController:
    """Base class. A subclass supplies applies(), limit(), prompt_for() and
    withdraw_message()."""

    #: The printed name, for the log.
    LABEL = None
    GO_LABEL = "Go into Strategic Reserves"
    STAY_LABEL = "Stay on the battlefield"

    def __init__(self, decision_manager=None, game_state=None, game_log=None,
                 all_tokens=None, auto_players=(), battle_size=None, choose=None):
        self.decision_manager = decision_manager
        self.game_state = game_state
        self.game_log = game_log
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.auto_players = ai_mode.players(auto_players)
        self.battle_size = battle_size
        #: The AI's policy, or None - see the module docstring.
        self.choose = choose
        #: How many have been pulled back during the turn currently ending.
        self._withdrawn_this_turn = 0

    # ------------------------------------------------------------ the hooks
    def applies(self, squad):
        raise NotImplementedError

    def limit(self, player=None):
        raise NotImplementedError

    def prompt_for(self, squad):
        raise NotImplementedError

    def withdraw_message(self, squad):
        raise NotImplementedError

    def is_engaged(self, squad):
        """"excluding units within Engagement Range of one or more enemy units".
        game/engagement.py's one reading - living models on both sides."""
        from game import engagement
        return engagement.is_engaged(squad, self.all_tokens)

    # ------------------------------------------------------------ the cap
    def remaining(self, player=None):
        return max(0, self.limit(player) - self._withdrawn_this_turn)

    def can_use(self, squad):
        if not self.applies(squad) or self.game_state is None:
            return False
        if self.remaining(getattr(squad, "owner", None)) <= 0:
            return False
        if squad in getattr(self.game_state, "reserves", ()) or []:
            return False
        if not any(not m.is_dead() for m in (getattr(squad, "models", ()) or ())):
            return False
        return not self.is_engaged(squad)

    def eligible_squads(self, squads, player):
        return sorted((s for s in squads if s.owner == player and self.can_use(s)),
                      key=lambda s: s.name)

    # ------------------------------------------------------------ the offer
    def offer_at_end_of_turn(self, squads, ending_player):
        """`ending_player` is whose turn just ENDED; the offer goes to everyone
        else. Returns True if a prompt was raised."""
        self._withdrawn_this_turn = 0
        others = [s for s in squads if s.owner != ending_player]
        if self.choose is not None:
            for player in sorted({s.owner for s in others if s.owner in self.auto_players},
                                 key=str):
                eligible = self.eligible_squads(others, player)
                if not eligible:
                    continue
                for squad in list(self.choose(eligible, self.remaining(player)) or ()):
                    if self.can_use(squad):
                        self.use(squad)
        candidates = sorted(
            (s for s in others if s.owner not in self.auto_players),
            key=lambda s: (str(s.owner), s.name))
        return per_unit_offer.offer_each(
            self.decision_manager, candidates, self.can_use, self.prompt_for,
            lambda s: [(self.GO_LABEL, lambda t=s: self.use(t)),
                       (self.STAY_LABEL, lambda: None)])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        self._withdrawn_this_turn += 1
        return withdraw_to_reserves(self.game_state, squad, log=self.game_log,
                                    message=self.withdraw_message(squad))
