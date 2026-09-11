"""Monolith: "Eternity Gate".

RULE (verbatim, rules/necrons/Monolith.md):

  "In your Movement phase (excluding the first battle round), you can select
   one friendly NECRONS INFANTRY unit that is either in strategic reserves or
   on the battlefield (if you select a unit on the battlefield, remove that
   unit from the battlefield and place it into strategic reserves). That unit
   can make an ingress move, and while making that ingress move, that unit
   must be set up wholly within 6" of this unit and unengaged (instead of more
   than 8" horizontally from all enemy units), even if that is within your
   opponent's deployment zone. That unit cannot make a charge move this turn."

THE FOURTH ARRIVAL MODE in game/ingress.py, after plain 20.04, the Homing
Beacon and the relaxed "anywhere on the battlefield" pair. The Beacon is the
closest shape - "set up within X of the bearer instead of the board edge" - and
this borrows its three seams. What is NEW is the distance the replacement
names.

"UNENGAGED" IS NOT A NUMBER THE OTHER MODES USE. Every other arrival names a
band (8", 9", 6") and refuses anything at or inside it. This one names a STATE,
and rule 03.04 defines it: a unit is engaged while it is within Engagement
Range, which this engine keeps as squad.ENGAGEMENT_RANGE_IN. So the gated
arrival's minimum enemy distance is that constant and not a fourth literal -
if the engine's reading of 03.04 ever moves, this moves with it, which a 2.0
written here would not.

THE DEPLOYMENT-ZONE WAIVER IS PRINTED, not inherited. Rule 20.04 bans arriving
in the opponent's zone before the third battle round, and [DEEP STRIKE] is the
only other thing here that waives it. The Monolith HAS Deep Strike, but the
unit coming THROUGH the gate need not - a plain Necron Warriors unit has none -
so the waiver has to be attached to the ARRIVAL rather than read off the
arriving unit's keywords. Getting that wrong would make the ability work only
for units that did not need it.

"EITHER IN STRATEGIC RESERVES OR ON THE BATTLEFIELD" is two source states and
one destination. A unit already in reserves simply arrives; a unit on the board
is WITHDRAWN first, through strategic_reserves.withdraw_to_reserves() - the
same helper Airborne Agility uses, so the two cannot disagree about what
leaving the battlefield means (objective control is recomputed, the models come
off the token list, and the unit is not counted as destroyed).

"EXCLUDING THE FIRST BATTLE ROUND" IS NOT REDUNDANT HERE even though rule
20.03 already bans round-1 arrivals, and the difference is the withdrawal: a
version that only checked the arrival gate would let a player pull a unit off
the board in round 1 and discover afterwards that it cannot come back until
round 2. The gate is checked BEFORE anything is removed.

"THAT UNIT CANNOT MAKE A CHARGE MOVE THIS TURN" rides
Squad.charge_locked_until_end_of_turn, the field rule 11.04's other exceptions
already use, so 18.02's and 09.07's readers need no new term.
"""

from game import ai_mode, awakened_dynasty, strategic_reserves
from game.squad import ENGAGEMENT_RANGE_IN

ETERNITY_GATE_RANGE_IN = 6.0
ETERNITY_GATE_LABEL = "Eternity Gate"

#: "unengaged (instead of more than 8" horizontally from all enemy units)".
#: Rule 03.04's band, taken from squad.py rather than written out, so this
#: cannot drift from the engine's own reading of what "engaged" means.
ETERNITY_GATE_MIN_ENEMY_DISTANCE_IN = ENGAGEMENT_RANGE_IN

FIRST_ALLOWED_BATTLE_ROUND = 2   # "excluding the first battle round"


def _alive(squad):
    return [m for m in squad.models if not m.is_dead()] if squad else []


def bearers(all_tokens):
    """Living Monolith models on the board."""
    return [t for t in (all_tokens or ())
            if getattr(t.profile, "eternity_gate", False) and not t.is_dead()]


def bearer_squads(all_tokens):
    seen, out = set(), []
    for token in bearers(all_tokens):
        squad = getattr(token, "squad", None)
        if squad is not None and id(squad) not in seen:
            seen.add(id(squad))
            out.append(squad)
    return out


def is_eligible_passenger(squad):
    """"one friendly NECRONS INFANTRY unit" - both keywords, per rule 19.03's
    any-model pooling for the faction half and every-model for INFANTRY.

    INFANTRY is asked of every living model rather than any: a unit is an
    INFANTRY unit when its models are infantry, and pooling that with any()
    would let a single infantry component drag a vehicle through the gate."""
    if squad is None or not awakened_dynasty.is_necrons_unit(squad):
        return False
    models = _alive(squad)
    return bool(models) and all(getattr(m.profile, "infantry", False) for m in models)


class EternityGateController:
    def __init__(self, decision_manager=None, game_log=None, game_state=None,
                 ingress_controller=None, turn_tracker=None, auto_players=()):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.game_state = game_state
        self.ingress_controller = ingress_controller
        self.turn_tracker = turn_tracker
        self.auto_players = ai_mode.players(auto_players)
        self._used_this_turn = set()     # id(monolith squad)

    # ------------------------------------------------------------- plumbing
    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _tokens(self):
        return list(self.game_state.tokens) if self.game_state is not None else []

    def reset_turn(self):
        self._used_this_turn.clear()

    def _battle_round(self):
        return getattr(self.turn_tracker, "battle_round", 0) or 0

    # ------------------------------------------------------------- the gate
    def candidates(self, monolith_squad):
        """Eligible passengers: friendly NECRONS INFANTRY units, either in
        strategic reserves or standing on the battlefield."""
        if monolith_squad is None or self.game_state is None:
            return []
        out, seen = [], set()
        for squad in getattr(self.game_state, "reserves", ()) or ():
            if squad.owner == monolith_squad.owner and is_eligible_passenger(squad):
                seen.add(id(squad))
                out.append(squad)
        for token in self._tokens():
            squad = getattr(token, "squad", None)
            if squad is None or id(squad) in seen:
                continue
            if squad is monolith_squad or squad.owner != monolith_squad.owner:
                continue
            if is_eligible_passenger(squad):
                seen.add(id(squad))
                out.append(squad)
        return sorted(out, key=lambda s: s.name)

    def can_use(self, monolith_squad):
        if monolith_squad is None or self.ingress_controller is None:
            return False
        if self._battle_round() < FIRST_ALLOWED_BATTLE_ROUND:
            return False    # "excluding the first battle round" - checked BEFORE anything is withdrawn
        if id(monolith_squad) in self._used_this_turn:
            return False
        if not any(bearers([m for m in monolith_squad.models])):
            return False
        return bool(self.candidates(monolith_squad))

    def offer(self, monolith_squad):
        """"You CAN select one friendly NECRONS INFANTRY unit" - a choice, so
        a human is asked and the AI answers for free.

        THE AI DECLINES, and that is a NAMED decision rather than a missing
        path. Every other deterministic answer in this faction is a local
        judgement the board settles - how many wounds are recoverable, whether
        a target is in half range. This one is not: it withdraws a unit from
        the battlefield to bring it back somewhere else, which is a question
        about the whole army's plan, and ai/agent_driver.py has no input that
        could tell a good gate from a bad one. Declining leaves the unit
        standing where the planner put it, which is a legal answer and not a
        hang - the same call game/enh_solid_image_projection.py records for
        the same shape of ability."""
        if not self.can_use(monolith_squad):
            return False
        player = monolith_squad.owner
        candidates = self.candidates(monolith_squad)
        if player in self.auto_players or self.decision_manager is None:
            self._log("%s (%s): the AI leaves its units where they stand - see "
                      "game/eternity_gate.py." % (ETERNITY_GATE_LABEL,
                                                  monolith_squad.name),
                      file_only=True)
            return False
        options = [
            (s.name, (lambda t=s: self.use(monolith_squad, t)), s)
            for s in candidates
        ]
        options.append(("Decline", None))
        self.decision_manager.request(
            player,
            "%s (%s): send which NECRONS INFANTRY unit through the gate?"
            % (ETERNITY_GATE_LABEL, monolith_squad.name),
            options,
        )
        return True

    def use(self, monolith_squad, passenger):
        """Open the gated arrival for `passenger`. Withdraws it first when it
        is standing on the battlefield."""
        if not self.can_use(monolith_squad) or passenger not in self.candidates(monolith_squad):
            return False
        self._used_this_turn.add(id(monolith_squad))
        if passenger not in (getattr(self.game_state, "reserves", ()) or ()):
            # (game_state, squad) - the argument order Airborne Agility uses.
            strategic_reserves.withdraw_to_reserves(
                self.game_state, passenger, log=self.game_log,
                message="%s (%s): %s is removed from the battlefield and placed "
                        "into strategic reserves."
                        % (ETERNITY_GATE_LABEL, monolith_squad.name,
                           passenger.name))
        self.ingress_controller.eternity_gate_squad = passenger
        self.ingress_controller.eternity_gate_bearer = monolith_squad
        passenger.charge_locked_until_end_of_turn = True
        self._log('%s (%s): %s may arrive wholly within %.0f" of the Monolith and '
                  "unengaged, and cannot charge this turn."
                  % (ETERNITY_GATE_LABEL, monolith_squad.name, passenger.name,
                     ETERNITY_GATE_RANGE_IN))
        return True
