"""Seer Council Enhancement: Torc of Morai-Heg (20 pts).

RULE (verbatim, rules/aeldari/detachments/Seer Council.md):
  "ASURYANI PSYKER model only. Once per turn, when your opponent targets a unit
  from their army within 12" of the bearer with a Stratagem, the bearer can use
  this Enhancement. If it does, increase the CP cost of that usage of that
  Stratagem by 1CP."

  FAQ: "After using the Torc, if my opponent does not have the necessary CP
  available for the selected Stratagem, what happens? - No CP are spent and
  that Stratagem's effects are not resolved (but that Stratagem still counts as
  having been used this phase)."

THE FIRST SURCHARGE. Every CP effect in this engine so far has been a DISCOUNT
on your own Stratagem; this raises the price of your OPPONENT's. So
StratagemController grows `cost_surcharges` beside `cost_discounts` rather than
letting a "discount" return a negative number - a discount that makes things
dearer is a lying name, and the two are not symmetrical in one respect that
matters (below).

THE ORDER IS DISCOUNT, THEN CLAMP, THEN SURCHARGE. A discount cannot take a
cost below zero (nobody is PAID command points), and the surcharge then applies
to what is actually owed. Both orders agree on ordinary numbers and disagree
exactly when a discount is bigger than the cost: a 1CP Stratagem with a 2CP
discount and this surcharge costs 1CP, not 0. Written the other way round the
Enhancement would be free to ignore whenever the opponent held any discount at
all.

THE FAQ CLAUSE IS THE ONE PEOPLE LEAVE OUT, and it is not a detail: made
unaffordable BY the surcharge, the Stratagem still counts as used this phase.
So the opponent cannot retry it more cheaply after the Torc has bitten - which
is most of what 20 points buys. StratagemController.use() therefore has to
distinguish "unaffordable anyway" (nothing happens, as before) from
"unaffordable BECAUSE of the surcharge" (record it as used, resolve nothing).

AUTOMATIC WHILE AVAILABLE - a NAMED simplification. The text says "the bearer
CAN use this Enhancement", and a player might rationally save it for a dearer
Stratagem later in the same turn. Offering that choice would mean interrupting
the opponent's Stratagem between its affordability check and its payment, and
this engine's use() is synchronous - there is no seam there. So it is applied
to the first eligible usage each turn. Named here rather than left to be
discovered; it is the same call rule 24.29's [PSYCHIC] and Kauyon's
modifier-ignoring already get, one step weaker because here the choice is real.

MEASURED FROM THE BEARER MODEL to the TARGETED unit - "targets a unit from
their army WITHIN 12" OF THE BEARER", not of the bearer's unit.
"""
from game import enhancements
from game.squad import edge_distance

TORC_OF_MORAI_HEG = "Torc of Morai-Heg"

TORC_LABEL = "Torc of Morai-Heg"

#: 'within 12" of the bearer'.
TORC_RANGE_IN = 12.0

#: "increase the CP cost of that usage of that Stratagem by 1CP".
TORC_SURCHARGE_CP = 1


def bearer_models(squad):
    return enhancements.bearer_models(squad, TORC_OF_MORAI_HEG)


class TorcOfMoraiHegSurcharge:
    """Plugged into StratagemController.cost_surcharges.

    Mirrors the cost-discount protocol exactly - available_surcharge() is a
    PURE QUERY that can_use() may call as often as it likes, and consume() is
    the only thing that spends the once-per-turn use. Getting that split wrong
    would burn the Enhancement merely by asking whether a button is enabled."""

    def __init__(self, game_state=None, turn_tracker=None, game_log=None):
        self.game_state = game_state
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        #: bearer's player -> the turn it was last spent in.
        self._used_in_turn = {}

    # --- the once-per-turn window ----------------------------------------

    def _turn(self):
        """"Once per TURN" - a turn, not a battle round and not a phase. Keyed
        on (battle_round, turn_owner) because TurnTracker has no single
        monotonic turn counter."""
        return (getattr(self.turn_tracker, "battle_round", None),
                getattr(self.turn_tracker, "turn_owner", None))

    def available(self, player):
        return self._used_in_turn.get(player) != self._turn()

    # --- who holds one, and can it reach ---------------------------------

    def _squads(self):
        seen, out = set(), []
        for token in getattr(self.game_state, "tokens", ()) or ():
            squad = getattr(token, "squad", None)
            if squad is not None and id(squad) not in seen:
                seen.add(id(squad))
                out.append(squad)
        return out

    def _bearers_against(self, user):
        """Every living bearer model belonging to somebody OTHER than the
        player using the Stratagem - "your OPPONENT targets"."""
        return [(s, m) for s in self._squads() if s.owner != user
                for m in bearer_models(s)]

    def _in_range(self, bearer_model, target):
        for other in getattr(target, "models", ()) or ():
            if other.is_dead():
                continue
            if edge_distance(bearer_model, other) <= TORC_RANGE_IN:
                return True
        return False

    # --- the two halves ---------------------------------------------------

    def available_surcharge(self, user, stratagem=None, targets=()):
        """A PURE QUERY: the extra CP this usage would cost, or 0."""
        for squad, model in self._bearers_against(user):
            if not self.available(squad.owner):
                continue
            if any(self._in_range(model, t) for t in targets or ()):
                return TORC_SURCHARGE_CP
        return 0

    def consume(self, user, stratagem=None, targets=()):
        """Called once the surcharged usage has actually gone through - or been
        blocked by the surcharge, which per the FAQ still spends it."""
        for squad, model in self._bearers_against(user):
            if not self.available(squad.owner):
                continue
            if any(self._in_range(model, t) for t in targets or ()):
                self._used_in_turn[squad.owner] = self._turn()
                if self.game_log is not None:
                    self.game_log.add(
                        "%s: %s - %s costs %s %dCP more."
                        % (squad.owner, TORC_LABEL,
                           getattr(stratagem, "name", "that Stratagem"),
                           user, TORC_SURCHARGE_CP))
                return
