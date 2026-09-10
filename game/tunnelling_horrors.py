"""Ophydian Destroyers' "Tunnelling Horrors" (Necrons).

RULE (printed, word for word):
  "At the end of your opponent's turn, if this unit is unengaged, you can use
   this ability. If you do:
     - Place this unit in strategic reserves.
     - This unit must make an ingress move in your next Movement phase
       (including in your first turn)."

TWO EXISTING HALVES, ONE PHASE APART - and the gap between them is the only new
thing here.

  * THE WITHDRAWAL is Vespid Stingwings' Airborne Agility, word for word:
    "at the end of your opponent's turn, if this unit is unengaged, ...
    Strategic Reserves". Same timing, same Engagement Range test, same
    game/strategic_reserves.py move, same per-unit offer chain. Nothing about
    it is re-derived here.
  * THE FORCED RETURN is Seer Council's Unshrouded Truth, whose own EFFECT
    says "your unit must make an ingress move this phase" - and which
    therefore had to override rule 20.03's "reserves arrive from battle round
    2 onward", because a unit placed into reserves in round 1 could otherwise
    not come back at all. game/ingress.py's can_ingress() already asks that
    module first, and asks this one beside it.

WHAT IS ACTUALLY DIFFERENT IS THE CLOCK, and it is the reason this is not just
a third caller of Unshrouded Truth's flag. That stratagem is used in YOUR
Movement phase and the unit comes back in the SAME one, so its flag is cleared
at the end of that phase. This ability is used at the end of your OPPONENT'S
turn and the unit comes back in your NEXT Movement phase - so the flag has to
survive the rest of the opponent's turn AND your own Command phase, and is
cleared at the end of the MOVEMENT phase it was owed in.

"(INCLUDING IN YOUR FIRST TURN)" is the parenthesis that makes the round-gate
override load-bearing rather than decorative: a unit that tunnels at the end of
the opponent's first turn is expected back in battle round 1, which 20.03 flatly
forbids. Without the override the ability would read as written and do nothing
for a whole round.

NO DEEP STRIKE GRANT, unlike Unshrouded Truth. That stratagem hands its target
"your unit has Deep Strike" because an ASURYANI INFANTRY unit generally has
none; the Ophydian Destroyers print [DEEP STRIKE] on their own datasheet, so
the arrival already uses rule 24.09's "anywhere more than 9" from every enemy"
without anything being granted. Stated because the two abilities otherwise line
up so closely that a missing line reads like an omission.

"MUST" IS NOT ENFORCED AS A COMPULSION, and that is the same reading
Unshrouded Truth records for the same word: nothing in this engine can force a
player to complete a placement. What the flag buys is that the arrival is
LEGAL when the ordinary rules would refuse it. A player who simply does not
place the unit leaves it in reserves, and it arrives later under 20.03 like
anything else.
"""

from game import ai_mode, engagement, per_unit_offer
from game.strategic_reserves import withdraw_to_reserves

TUNNELLING_HORRORS_LABEL = "Tunnelling Horrors"


def unit_has_tunnelling_horrors(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "tunnelling_horrors", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def applies(squad):
    """Whether this unit currently owes an ingress move under this ability -
    which is also what lifts rule 20.03's round gate for it.

    Read by game/ingress.py's can_ingress(), beside
    unshrouded_truth.applies()."""
    return squad is not None and bool(getattr(squad, "tunnelling_horrors_owed", False))


def reset_movement_phase(squads=()):
    """Cleared at the end of the MOVEMENT phase the arrival was owed in - not
    at the end of a turn, and not at the end of every phase.

    Its Unshrouded Truth twin is cleared per phase because that one is used and
    paid off inside a single Movement phase. This one is armed at the end of
    the OPPONENT'S turn and has to survive the rest of it plus the owner's own
    Command phase, so a per-phase reset would throw it away before it could be
    used - which is exactly the kind of half-length flag CLAUDE.md's error
    class 14 is about.

    An unmet obligation simply stops mattering here: the unit stays in reserves
    and arrives under the ordinary rules later."""
    for squad in squads or ():
        squad.tunnelling_horrors_owed = False


class TunnellingHorrorsController:
    """Offered at the end of every turn, to the player whose turn it is NOT -
    the same host and the same chain as game/airborne_agility.py."""

    def __init__(self, decision_manager=None, game_state=None, game_log=None,
                 auto_players=()):
        self.decision_manager = decision_manager
        self.game_state = game_state
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)

    def can_use(self, squad):
        tokens = getattr(self.game_state, "tokens", []) if self.game_state else []
        return (unit_has_tunnelling_horrors(squad)
                and any(not m.is_dead() for m in getattr(squad, "models", ()) or ())
                and not engagement.is_engaged(squad, tokens))

    def eligible_squads(self, squads, player):
        return sorted((s for s in squads if s.owner == player and self.can_use(s)),
                      key=lambda s: s.name)

    def offer_at_end_of_turn(self, squads, ending_player):
        """`ending_player` is whose turn just ended, so the offer goes to
        everyone ELSE - which is what "your opponent's turn" means from the
        Ophydian owner's side.

        EVERY eligible unit is asked, one prompt at a time, through
        game/per_unit_offer.py: the rule is written per unit ("if THIS UNIT is
        unengaged"), and the bug that chain exists for is precisely an army
        with two such units being asked about only one of them.

        THE AI DECLINES, and that is a judgement rather than a shrug - the same
        one Airborne Agility records, plus one reason of its own. Leaving the
        board surrenders whatever the unit was holding; unlike the Vespid it
        comes back the very next Movement phase rather than losing a turn,
        which makes the trade better, but choosing WHERE it comes back is a
        placement decision and this engine's deployment AI does not plan
        arrivals it did not itself schedule. Named rather than half-built."""
        candidates = sorted(
            (s for s in squads
             if s.owner != ending_player and s.owner not in self.auto_players),
            key=lambda s: (str(s.owner), s.name))
        return per_unit_offer.offer_each(
            self.decision_manager, candidates, self.can_use,
            lambda s: ("%s: Tunnelling Horrors - tunnel into Strategic Reserves? It "
                       "must make its ingress move in your next Movement phase." % s.name),
            lambda s: [("Tunnel into Strategic Reserves", lambda t=s: self.use(t)),
                       ("Stay on the battlefield", lambda: None)])

    def use(self, squad):
        if not self.can_use(squad) or self.game_state is None:
            return False
        # Set BEFORE the withdrawal, so nothing can observe the unit sitting in
        # reserves without the obligation that lets it come straight back - the
        # ordering game/unshrouded_truth.py records for the same pair of steps.
        squad.tunnelling_horrors_owed = True
        moved = withdraw_to_reserves(
            self.game_state, squad, log=self.game_log,
            message=("%s uses Tunnelling Horrors and burrows into Strategic Reserves - "
                     "it must make its ingress move in its next Movement phase." % squad.name))
        if not moved:
            squad.tunnelling_horrors_owed = False
        return moved
