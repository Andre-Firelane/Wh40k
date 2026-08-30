"""Vespid Stingwings' "Airborne Agility".

RULE (printed, word for word):
  "At the end of your opponent's turn, if this unit is not within Engagement
   Range of one or more enemy units, you can remove it from the battlefield and
   place it into Strategic Reserves."

THE FIRST ABILITY HERE THAT TAKES A UNIT OFF THE BOARD VOLUNTARILY. Everything
else that touches Strategic Reserves puts units there before the battle (20.01,
game/pregame.py) or brings them back (20.03/20.04, Ingress and Rapid Ingress).
Going the other way mid-battle is new, but it needs no new state: a unit in
Strategic Reserves is exactly a unit whose models are off `state.tokens` and on
the reserves list, which is what game/strategic_reserves.py already defines.

THE TIMING IS THE OPPONENT'S TURN END, NOT YOUR OWN - which is the one thing
easy to get backwards, and the reason the offer takes the player whose turn
just ended and asks the OTHER one.

"YOU CAN", so it is a real choice: a DecisionManager prompt for a human, and
deterministic for an `auto_players` owner. The AI declines by default, and that
is a judgement rather than a shrug - leaving the board surrenders whatever the
unit was holding and costs it the following turn to come back, which is only
worth it to save a unit that is about to die, and this engine has no "about to
die" estimate that looks at the opponent's coming turn.

ENGAGEMENT RANGE IS CHECKED AT THE MOMENT OF USE, not when the offer is built,
because the two are the same instant here - but stating it keeps the predicate
honest if a later caller separates them.
"""

from game.squad import ENGAGEMENT_RANGE_IN, edge_distance
from game import engagement
from game.strategic_reserves import withdraw_to_reserves


def unit_has_airborne_agility(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "airborne_agility", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def is_engaged(squad, all_tokens=()):
    """"not within Engagement Range of one or more enemy units" - rule 03.04.

    Delegates to game/engagement.py, which is where this sentence now lives:
    it had been written out in three modules independently, and Warhost's two
    withdrawal Stratagems made five. See that module for why the living-model
    filter differs from Squad.is_engaged()."""
    return engagement.is_engaged(squad, all_tokens)


class AirborneAgilityController:
    """Offered at the end of every turn, to the player whose turn it is NOT."""

    def __init__(self, decision_manager=None, game_state=None, game_log=None,
                 auto_players=()):
        self.decision_manager = decision_manager
        self.game_state = game_state
        self.game_log = game_log
        self.auto_players = set(auto_players)

    def can_use(self, squad):
        tokens = getattr(self.game_state, "tokens", []) if self.game_state else []
        return (unit_has_airborne_agility(squad)
                and any(not m.is_dead() for m in getattr(squad, "models", ()) or ())
                and not is_engaged(squad, tokens))

    def eligible_squads(self, squads, player):
        return sorted((s for s in squads if s.owner == player and self.can_use(s)),
                      key=lambda s: s.name)

    def offer_at_end_of_turn(self, squads, ending_player):
        """`ending_player` is whose turn just ended - so the offer goes to
        everyone ELSE, which is what "your opponent's turn" means from the
        Vespid owner's side."""
        for squad in sorted((s for s in squads if s.owner != ending_player),
                            key=lambda s: (str(s.owner), s.name)):
            if not self.can_use(squad):
                continue
            if squad.owner in self.auto_players or self.decision_manager is None:
                return False  # see the module docstring: the AI stays put
            self.decision_manager.request(
                squad.owner,
                f"{squad.name}: Airborne Agility - leave the battlefield and go into "
                f"Strategic Reserves?",
                [("Go into Strategic Reserves", lambda s=squad: self.use(s)),
                 ("Stay on the battlefield", lambda: None)],
            )
            return True
        return False

    def use(self, squad):
        """Take the unit off the board and put it into Strategic Reserves."""
        if not self.can_use(squad) or self.game_state is None:
            return False
        # The shared mechanical move (game/strategic_reserves.py), which also
        # re-evaluates objective control - a unit that leaves the board must
        # stop holding what it was standing on.
        return withdraw_to_reserves(
            self.game_state, squad, log=self.game_log,
            message=f"{squad.name} uses Airborne Agility and returns to Strategic Reserves.")
