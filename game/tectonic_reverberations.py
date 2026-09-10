"""The Geomancer's "Tectonic Reverberations" (Necrons).

RULE (printed, word for word):
  "In your Movement phase, you can select one enemy unit within 18" of and
   visible to this model. Until the start of your next Movement phase that
   enemy unit is pinned. While a unit is pinned, subtract 2 from that unit's
   Move characteristic and subtract 2 from Charge rolls made for it."

THE STATUS IS ALREADY BUILT, and that is the whole point of this module being
short. The Night Spinner's Monofilament Web prints the same two sentences, so
PINNED - both its penalties and both its seams - lives in game/pinned.py, which
was extracted the day this became its second source.

WHAT IS THIS ABILITY'S OWN is three things:

  * THE TRIGGER. A SELECTION in your own Movement phase, not a consequence of
    shooting. So it is offered once per Movement phase, it is a real choice
    ("you CAN select"), and an owner in `auto_players` answers it without an
    API call.
  * THE CONDITION. "within 18" of and VISIBLE to this model" - two tests, and
    the visibility one is why this reads the real line-of-sight code rather
    than measuring a distance and stopping.
  * THE CLOCK. "Until the start of your next MOVEMENT phase", where the Night
    Spinner's is "until the start of your next TURN". One phase apart, and the
    difference is real: a unit pinned by the Geomancer is still pinned through
    the applying player's Command phase. Folding the two clocks together would
    silently shorten this ability by a phase - CLAUDE.md's error class 14 in
    its exact shape - so each source names its own and each boundary clears
    only its own.

"ONE ENEMY UNIT" is a choice between units, so the options are TAGGED with
their squads and the pick can be answered on the BOARD (game/unit_pick.py)
rather than from a list of names.

THE AI PICKS BY DAMAGE VALUE, the shared ranking every other deterministic
target choice in this engine uses, so it costs no API call. -2 Move and -2
Charge is worth most against whatever was going to hurt most.
"""

from game import ai_mode, line_of_sight
from game import pinned as pinned_status
from game.squad import edge_distance

TECTONIC_REVERBERATIONS_LABEL = "Tectonic Reverberations"

#: "one enemy unit within 18" of ... this model".
TECTONIC_RANGE_IN = 18.0


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def unit_has_ability(squad):
    return squad is not None and any(
        getattr(m.profile, "tectonic_reverberations", False) for m in _living(squad))


class TectonicReverberationsController:
    """Offered at the start of the owner's Movement phase, once per bearer."""

    def __init__(self, decision_manager=None, game_state=None, game_log=None,
                 turn_tracker=None, auto_players=(), target_pick=None,
                 obstacles=None, terrain_areas=None):
        self.decision_manager = decision_manager
        self.game_state = game_state
        self.game_log = game_log
        self.turn_tracker = turn_tracker
        self.auto_players = ai_mode.players(auto_players)
        # target_pick(attacker, candidates) -> squad. main.py passes the shared
        # damage-value ranking; None falls back to name order, which keeps a
        # headless test reproducible.
        self.target_pick = target_pick
        self.obstacles = obstacles if obstacles is not None else []
        self.terrain_areas = terrain_areas if terrain_areas is not None else []
        self._offered_this_phase = set()

    def _tokens(self):
        return getattr(self.game_state, "tokens", None) or []

    def bearers(self, player):
        """Living Geomancer models belonging to `player`."""
        return [t for t in self._tokens()
                if getattr(t, "squad", None) is not None
                and t.squad.owner == player
                and not t.is_dead()
                and getattr(t.profile, "tectonic_reverberations", False)]

    def candidates(self, bearer):
        """"one enemy unit within 18" of and visible to this model" - both
        halves, measured from the BEARER model rather than its unit, because
        the printed subject is "this model"."""
        owner = getattr(getattr(bearer, "squad", None), "owner", None)
        tokens = self._tokens()
        out = {}
        for token in tokens:
            other = getattr(token, "squad", None)
            if other is None or other.owner == owner or token.is_dead():
                continue
            if id(other) in out:
                continue
            if edge_distance(bearer, token) > TECTONIC_RANGE_IN:
                continue
            if not line_of_sight.has_line_of_sight(
                    bearer, token, self.obstacles, tokens, self.terrain_areas):
                continue
            out[id(other)] = other
        return sorted(out.values(), key=lambda s: s.name)

    def offer_at_start_of_movement(self, player):
        """Called at the start of `player`'s Movement phase.

        The clock is read LIVE here and that is correct rather than the error
        class 15 trap: this is a START-of-phase offer, so the phase really has
        just become the Movement phase - the same reading game/grot_orderly.py
        records for the identical shape."""
        raised = False
        for bearer in self.bearers(player):
            key = (id(bearer), getattr(self.turn_tracker, "battle_round", None))
            if key in self._offered_this_phase:
                continue
            targets = self.candidates(bearer)
            if not targets:
                continue
            self._offered_this_phase.add(key)
            if player in self.auto_players or self.decision_manager is None:
                self._pin(bearer, self._pick(bearer, targets))
                continue
            options = [("%s: %s" % (TECTONIC_REVERBERATIONS_LABEL, t.name),
                        (lambda target=t, b=bearer: self._pin(b, target)), t)
                       for t in targets]
            options.append(("Decline", None))
            self.decision_manager.request(
                player,
                "%s: pin which enemy unit? (-2 Move and -2 to Charge rolls "
                "until the start of your next Movement phase)"
                % TECTONIC_REVERBERATIONS_LABEL,
                options)
            raised = True
        return raised

    def _pick(self, bearer, candidates):
        if self.target_pick is not None:
            squad = getattr(bearer, "squad", None)
            chosen = self.target_pick(squad, candidates)
            if chosen is not None:
                return chosen
        return candidates[0]

    def _pin(self, bearer, target):
        owner = getattr(getattr(bearer, "squad", None), "owner", None)
        return pinned_status.pin(
            target, owner, until=pinned_status.UNTIL_MOVEMENT,
            log=(self.game_log.add if self.game_log is not None else None),
            label=TECTONIC_REVERBERATIONS_LABEL)

    def clear_at_start_of_movement(self, player):
        """"Until the start of your next Movement phase" - a pin this player
        applied expires as that phase begins, one phase later than the Night
        Spinner's."""
        squads = {}
        for token in self._tokens():
            squad = getattr(token, "squad", None)
            if squad is not None:
                squads[id(squad)] = squad
        return pinned_status.clear_at(player, pinned_status.UNTIL_MOVEMENT,
                                      list(squads.values()))

    def reset_phase(self):
        """The per-bearer offer memo is keyed on the battle round, so it only
        needs clearing when a battle ends - kept for symmetry with its
        neighbours and for a test that wants a clean slate."""
        self._offered_this_phase.clear()
