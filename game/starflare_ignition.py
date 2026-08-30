"""T'au Empire Enhancement: Starflare Ignition System, as supplied by the
user - the FIRST Enhancement this engine implements at all (until now
game/factions/detachment.py's Enhancement class had no instances and no
runtime counterpart; game/attached_units.py's docstring still records
"Enhancements are not modeled at all" as the reason rule 19.04's
"abilities that affect a single specified model" only ever showed up as
wargear).

RULE (Starflare Ignition System, 20 pts):
  BEARER: T'AU EMPIRE BATTLESUIT model only.
  EFFECT: At the end of your opponent's turn, if the bearer's unit is not
          within Engagement Range of one or more enemy units, you can
          remove that unit from the battlefield and place it into
          Strategic Reserves.

WHAT THIS ENGINE ALREADY HAD, AND WHAT IT DID NOT

Strategic Reserves is not new: game_state.reserves plus rule 20.03/20.04's
IngressController is the whole return trip, and this Enhancement only needs
the one direction nothing did yet - board -> reserves. That move is
mechanically TransportController.embark()'s (pull the models out of
game_state.tokens, record the unit somewhere off-board), which is why
withdraw() looks like it: a unit whose models are not in tokens is, by this
engine's own convention (GameState.add_reserve_squad's docstring), simply
not on the battlefield, and every on-board rule stops seeing it for free.

Being off the board and coming back is already a supported round trip, so
almost nothing here is special-cased:
  * can_ingress() gates on battle_round >= 2, so a unit that withdraws at
    the end of the opponent's turn can arrive again in its owner's very
    next Movement phase - which is the point of the Enhancement, and needed
    no new code.
  * ingress_locked is cleared on the way out, because it describes an
    arrival that has now been undone; confirm_ingress() sets it again on
    the next arrival.
  * Objective control is recomputed here rather than left to the next phase
    boundary: rule 14.02 recomputes "at the end of each phase and turn",
    and removing models mid-turn-end is exactly the kind of change that
    boundary exists to pick up.

TIMING, AND ONE DOCUMENTED DEVIATION

"At the end of your opponent's turn" is main.py's advance_turn_phase()
end-of-turn block (`ending_player is not None`) - the same instant rule
11.04's Fights First and 18.04/18.05's charge locks expire in. The bearer's
owner is whoever is NOT the ending player, and offer() derives that from
the eligible units themselves rather than from a player-name scheme.

"You can" makes it optional, so it is a DecisionManager prompt rather than
an automatic effect - which also means it resolves ASYNCHRONOUSLY, a frame
or more after advance_turn_phase() has already run to completion. That is
the established shape for every reactive offer here (Rapid Ingress, Fire
Overwatch, Heroic Intervention all work this way), and it is harmless for
all of them - but it has one real consequence for this rule specifically,
recorded rather than papered over:

  advance_turn_phase() also opens the NEXT player's Command phase in the
  same call, including MissionController.score_primary(). By the real
  sequence, "the end of your opponent's turn" comes BEFORE your Command
  phase, so a unit you withdraw should already be gone when Primary is
  scored. Here it is not: Primary is scored first, then the human answers
  the prompt. The error is bounded (one scoring event) and only bites when
  the withdrawing unit was the sole controller of an objective, and it
  favours the withdrawing player. Fixing it properly means deferring the
  Command-phase Primary scoring until decision_manager has no pending
  decision, which is a change to main.py's phase-transition ordering rather
  than to this rule - left alone until it actually matters.

A second, smaller edge, also left as-is: rule 20.03's "at the end of the
third battle round, all strategic reserves units that have not made one or
more ingress moves are destroyed" is a one-shot sweep in
IngressController.destroy_remaining_reserves(), fired earlier in the same
advance_turn_phase() call. A unit withdrawing at the end of battle round 3
therefore lands in reserves just after that sweep and is not destroyed by
it. That is arguably right anyway - such a unit either deployed normally or
HAS already made an ingress move, which is exactly what 20.03 exempts - but
it is an ordering accident rather than a decision, so it is written down.

GATED ON THE DETACHMENT - THE LIMITATION THIS USED TO NAME IS CLOSED
--------------------------------------------------------------------
This module used to write out, at length, why it was NOT gated on its
detachment while the other six Retaliation Cadre modules were: an Enhancement
is a LIST-BUILDING choice, this engine has no army-building step, and the
predefined T'au list handed this one to its Coldstar Commander unconditionally.
The consequence it stated plainly was that fielding a different T'au detachment
left that Commander holding a Retaliation Cadre Enhancement, and its 20 points.

That is fixed. A detachment now belongs to the LIST (game/detachments.py), so
game/army_lists.py's tau_army() hands out the Enhancement of each detachment it
actually declares, and game/enhancements.py's is_active() refuses one whose
detachment is not fielded - so a hand-built scene or an older save cannot run a
Kauyon Enhancement in a Mont'ka army either.

The BATTLESUIT half IS checked, and so is CHARACTER: grant() is where the
bearer decision is actually made in this engine, so that is where both are
enforced.
"""

from game import enhancements
from game.squad import ENGAGEMENT_RANGE_IN, edge_distance
from game.strategic_reserves import withdraw_to_reserves

STARFLARE_IGNITION_SYSTEM_NAME = "Starflare Ignition System"
# Read off the registry rather than repeated here: game/enhancements.py and
# game/factions/tau_empire.py already have to agree about this number, and a
# third copy is one more place for them to drift.
STARFLARE_IGNITION_SYSTEM_POINTS = enhancements.get(STARFLARE_IGNITION_SYSTEM_NAME).points



def _living(models):
    """Models that are actually still in play - see bearer_models() for why
    "dead but still in the list" is the normal state when this rule runs."""
    return [m for m in models if not m.is_dead()]


def bearer_models(squad):
    """Every living model of `squad` carrying this Enhancement.

    game/enhancements.py owns this reading now - it is the same 19.04 question
    for all nineteen Enhancements, and the "a model killed this frame is still
    in Squad.models" trap that this rule's own bug report taught is exactly
    what a shared answer must not lose. The report: without the is_dead()
    filter a unit whose BEARER had just been killed still looked like it had
    the Enhancement, so offer() raised the prompt - and by the time the human
    answered it a frame later, the sweep had run and withdraw()'s re-check
    refused. The prompt closed, nothing happened, and not one line explained
    it."""
    return enhancements.bearer_models(squad, STARFLARE_IGNITION_SYSTEM_NAME)


def enhancement_models(squad):
    """Every model of `squad` that was GIVEN this Enhancement, alive or not.

    The distinction from bearer_models() only matters for reporting: a unit
    whose bearer has just been killed no longer has the Enhancement (19.04),
    but it is still the unit the rule is about, and saying so is the point of
    offer()'s "not offered - because X" line."""
    return enhancements.enhancement_models(squad, STARFLARE_IGNITION_SYSTEM_NAME)


def has_starflare_ignition_system(squad):
    """A living bearer AND an owner who fields Retaliation Cadre.

    The second half is NEW, and it closes the limitation this module's own
    docstring used to write out at length ("picking a different T'au detachment
    leaves that Commander holding a Retaliation Cadre Enhancement"). See
    game/enhancements.py for why that is now answerable: the detachment is
    chosen before the armies are built."""
    return enhancements.is_active(squad, STARFLARE_IGNITION_SYSTEM_NAME)


def grant(squad, model=None, game_log=None):
    """Give this Enhancement to one model of `squad` during army building.

    Delegates to game/enhancements.py's grant(), which owns the bearer
    restriction, the points and the log line for all nineteen. Kept as a named
    function here because callers (and tests) name this rule, not the registry.
    """
    return enhancements.grant(squad, STARFLARE_IGNITION_SYSTEM_NAME,
                              model=model, game_log=game_log)


def _can_bear(model):
    """"T'AU EMPIRE BATTLESUIT model only", plus the general Enhancement rule
    that the bearer is a CHARACTER model. The T'AU EMPIRE half is not checked -
    this engine has no per-model faction keyword (see game/enhancements.py)."""
    return enhancements.get(STARFLARE_IGNITION_SYSTEM_NAME).can_bear(model, None)


class StarflareIgnitionController:
    """The end-of-opponent's-turn offer, and the board -> Strategic Reserves
    move it performs.

    Takes only the GameState: `game_state.tokens` is the same list object
    every other controller receives as `all_tokens` (main.py passes it
    straight through), and this is the one controller that both READS that
    list (Engagement Range) and MUTATES it (removing the withdrawing unit) -
    holding two names for it would make it possible for those two to drift
    apart in a future refactor for no gain.
    """

    def __init__(self, game_state, game_log=None):
        self.game_state = game_state
        self.game_log = game_log

    def refusal_reason(self, squad):
        """Why this unit may NOT withdraw right now, as a sentence, or None if
        it may. can_withdraw() is this predicate; the string exists so that a
        refusal can be written down instead of vanishing - see withdraw()."""
        if squad is None:
            return "no unit"
        if not has_starflare_ignition_system(squad):
            return "no living model of the unit carries the Enhancement any more"
        # "remove that unit from the battlefield" - a unit that is not on it
        # has nothing to remove. Reserves and embarked units (18.02) are both
        # off-board by this engine's own convention.
        if squad in self.game_state.reserves:
            return "the unit is already in Strategic Reserves"
        if squad.embarked_in is not None:
            return "the unit is embarked in a TRANSPORT (rule 18.02), so it is not on the battlefield"
        if not any(m in self.game_state.tokens for m in _living(squad.models)):
            return "the unit has no model on the battlefield"
        # A TRANSPORT taking its passengers off the battlefield with it is not
        # something this rule says anything about, and the passengers would be
        # left pointing at a token that is no longer in play (18.02's
        # embarked_in). No BATTLESUIT datasheet is a TRANSPORT, so this is a
        # guard against a future one rather than a live case - but a silently
        # orphaned embarked unit is exactly the sort of thing that surfaces
        # ten turns later as an unexplained hang.
        if any(s.embarked_in in squad.models for s in self.game_state.embarked_squads):
            return "the unit is carrying passengers (rule 18.02)"
        if self._engaged(squad):
            return "the unit is within Engagement Range of an enemy unit"
        return None

    def _engaged(self, squad):
        """Squad.is_engaged(), but blind to models that are dead and merely
        not swept up yet - see bearer_models() for why that state is the norm
        at the moment this rule is evaluated, not an edge case.

        Not fixed inside Squad.is_engaged() itself: that predicate is read by
        most of the movement/shooting/fight engine, and giving every one of
        those callers a different answer on the strength of one Enhancement's
        timing is a far bigger change than this rule justifies. Kept local and
        named, so it is obvious that the difference is deliberate."""
        for model in _living(squad.models):
            for other in self.game_state.tokens:
                if other.squad is None or other.squad is squad or other.squad.owner == squad.owner:
                    continue
                if other.is_dead():
                    continue
                if edge_distance(model, other) <= ENGAGEMENT_RANGE_IN:
                    return True
        return False

    def can_withdraw(self, squad):
        return self.refusal_reason(squad) is None

    def eligible_units(self, player):
        """Every unit of `player` that could withdraw right now."""
        seen = []
        for token in self.game_state.tokens:
            squad = token.squad
            if squad is None or squad.owner != player or squad in seen:
                continue
            if self.can_withdraw(squad):
                seen.append(squad)
        return seen

    def offer(self, ending_player, decision_manager):
        """WHEN: "at the end of your opponent's turn" - so this is called with
        the player whose turn just ended, and the offer goes to the other one.

        Who that is comes from the eligible units' own `owner`, not from a
        player-name scheme: nothing here needs to know that the two players
        are called "Player 1"/"Player 2".

        One prompt per eligible unit. DecisionManager is a real queue, so
        several simply line up in the order they were asked instead of
        overwriting each other; each callback re-checks can_withdraw(), since
        an earlier answer in that queue could in principle have changed the
        board underneath a later one.
        """
        if decision_manager is None:
            return []
        units, refused, seen = [], [], []
        for token in self.game_state.tokens:
            squad = token.squad
            if squad is None or squad.owner == ending_player or squad in seen:
                continue
            # Deliberately keyed on "was this unit ever given the Enhancement"
            # rather than "does it still have it": a unit whose bearer has just
            # been killed must still reach the reporting below, otherwise the
            # single case this logging exists for is the one it stays silent
            # about. Every other unit on the board is skipped here so the file
            # gets one line per relevant unit, not one per army.
            if not enhancement_models(squad):
                continue
            seen.append(squad)
            reason = self.refusal_reason(squad)
            if reason is None:
                units.append(squad)
            else:
                refused.append((squad, reason))
        # Both outcomes go in the file (file_only - this is diagnostic detail,
        # not something the on-screen log panel needs). Until this existed the
        # rule was completely invisible in a game log: nothing recorded that it
        # had been offered, and nothing recorded why it had not been, so a
        # report about it could only be answered by guessing at the board.
        if self.game_log is not None:
            for squad in units:
                self.game_log.add(
                    f"{squad.owner}: {squad.name} is offered the {STARFLARE_IGNITION_SYSTEM_NAME} "
                    f"withdrawal at the end of {ending_player}'s turn.", file_only=True,
                )
            for squad, reason in refused:
                self.game_log.add(
                    f"{squad.owner}: {squad.name} is not offered the {STARFLARE_IGNITION_SYSTEM_NAME} "
                    f"withdrawal - {reason}.", file_only=True,
                )
        for squad in units:
            decision_manager.request(
                squad.owner,
                f"{STARFLARE_IGNITION_SYSTEM_NAME}: remove {squad.name} from the battlefield "
                f"and place it into Strategic Reserves?",
                [
                    ("Withdraw into Strategic Reserves", lambda s=squad: self.withdraw(s)),
                    ("Stay on the battlefield", None),
                ],
            )
        return units

    def withdraw(self, squad):
        """Board -> Strategic Reserves. Mirrors TransportController.embark()'s
        own removal step: the models leave game_state.tokens, and the unit is
        recorded off-board instead.

        The re-check is kept (the offer resolves asynchronously, so the board
        CAN have moved on underneath it) but a refusal is now written down.
        It used to return False in silence, which is what made the report this
        was fixed for undiagnosable: the human picked "Withdraw", the prompt
        closed, the unit stayed, and the game log had nothing to say about any
        of it - the same "a diagnostic line that omits the one number in
        dispute sends the next investigation back to the board" lesson as the
        [move choice]/[charge]/[coherency] lines."""
        reason = self.refusal_reason(squad)
        if reason is not None:
            if self.game_log is not None and squad is not None:
                self.game_log.add(
                    f"{squad.owner}: {squad.name} cannot use the {STARFLARE_IGNITION_SYSTEM_NAME} "
                    f"after all - {reason}; it stays on the battlefield."
                )
            return False
        # The mechanical move (models out of tokens, unit into reserves, the
        # ingress lock cleared, objectives recomputed) is shared with Seer
        # Council's Unshrouded Truth - see game/strategic_reserves.py, which
        # also records why those last two are not optional.
        return withdraw_to_reserves(
            self.game_state, squad, log=self.game_log,
            message=(f"{squad.owner}: {squad.name} uses the {STARFLARE_IGNITION_SYSTEM_NAME} to "
                     f"leave the battlefield and go into Strategic Reserves (rule 20.03)."),
        )
