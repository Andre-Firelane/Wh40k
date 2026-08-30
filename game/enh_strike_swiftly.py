"""Mont'ka Enhancement: Strike Swiftly (45 pts).

RULE (the ERRATA'd second sentence, which is what
rules/tau_empire/detachments/Mont'ka.md prints under the original):
  T'AU EMPIRE model only. In the Resolve Pre-battle Abilities step, you can
  select up to two friendly T'AU EMPIRE units within 6" of this model that do
  not have the Scouts ability. Until the end of the battle, all models in the
  selected units have the Scouts 6" ability.

IT MUST RUN BEFORE THE SCOUTS STEP, AND THAT IS THE WHOLE TIMING PROBLEM
-------------------------------------------------------------------------
Rule 24.31's Scout move is resolved in the SAME step this Enhancement fires in
(game/scouts.py's ScoutsStep, driven from
PregameController._begin_prebattle_abilities()). A unit granted Scouts after
that step has already been passed over, and would carry an ability it can never
use - the grant would look correct in every unit test and do nothing in a game.

So PregameController gained an ORDERED list of pre-battle steps instead of the
single `scouts_step` hook it had, and this one is registered ahead of it. The
list is what makes the order explicit rather than implicit in which attribute
main.py happens to set.

"THAT DO NOT HAVE THE SCOUTS ABILITY" is checked with game/scouts.py's own
has_scouts(), not with a fresh look at model.profile.scouts: that predicate
routes through rule 24.31's "every model in the unit" reading and is 19.04
aware, so a unit whose attached character lacks the ability is correctly not
already-a-Scout. Re-deriving it here is exactly the second opinion this repo
consolidates.

"SCOUTS 6"", NOT THE UNIT'S OWN DISTANCE. The grant is a flat 6", written onto
every model's own UnitProfile instance. scout_distance() takes the min over the
unit, so a mixed attached unit gets 6" and not something better - which is that
function's own documented conservative choice, inherited here for free.

MEASURED FROM THE BEARER MODEL, not from its unit: "within 6" of THIS MODEL".
After a rule 19.01 merge those are different circles.

"UP TO TWO", offered one unit at a time for the same reason Student of Kauyon
is - a flat option list cannot express "choose two of seven" readably, and the
running count is what enforces the two. Declining is legal.

An owner in `auto_players` takes the nearest units first (ties by name, so a
self-play run is reproducible): a Scout move is worth most to whatever is
already far forward, and among units all within 6" of one character the nearest
is the cheapest tie-break that is not arbitrary. A rule answering its own
prompt, not an AI path - the standing T'au rule.
"""

from game import enhancements, scouts
from game.squad import edge_distance

STRIKE_SWIFTLY = "Strike Swiftly"
MAX_UNITS = 2
SELECTION_RANGE_IN = 6.0
GRANTED_SCOUT_DISTANCE_IN = 6


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def grant_scouts(squad, game_log=None):
    """"all models in the selected units have the Scouts 6" ability"."""
    if squad is None:
        return False
    for model in squad.models:
        model.profile.scouts = GRANTED_SCOUT_DISTANCE_IN
    if game_log is not None:
        game_log.add(f'{squad.owner}: {squad.name} has Scouts {GRANTED_SCOUT_DISTANCE_IN}" '
                     f"(rule 24.31) from the {STRIKE_SWIFTLY} Enhancement.")
    return True


class StrikeSwiftlyStep:
    """One of PregameController's pre-battle steps, registered BEFORE
    game/scouts.py's - see the module docstring."""

    def __init__(self, decision_manager=None, game_log=None, auto_players=(),
                 game_state=None):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = set(auto_players)
        self.game_state = game_state
        self.granted = {}     # player -> [squads]
        self._pending_players = []
        self._on_done = None

    # --- the rule ---------------------------------------------------------

    def _squads(self):
        seen = []
        for token in (getattr(self.game_state, "tokens", None) or ()):
            squad = getattr(token, "squad", None)
            if squad is not None and squad not in seen:
                seen.append(squad)
        return seen

    def bearer_units(self, player):
        return enhancements.bearer_units(self._squads(), STRIKE_SWIFTLY, player=player)

    def _bearer_models(self, squad):
        return enhancements.bearer_models(squad, STRIKE_SWIFTLY)

    def eligible_targets(self, bearer_squad):
        """"friendly T'AU EMPIRE units within 6" of this model that do not have
        the Scouts ability"."""
        from game import tau_detachments
        bearers = self._bearer_models(bearer_squad)
        if not bearers:
            return []
        already = [s for s in self.granted.get(bearer_squad.owner, []) if s is not None]
        out = []
        for squad in self._squads():
            if squad.owner != bearer_squad.owner or squad in already:
                continue
            if not tau_detachments.is_tau_unit(squad):
                continue
            if scouts.has_scouts(squad):
                continue
            if any(edge_distance(b, m) <= SELECTION_RANGE_IN
                   for b in bearers for m in _living(squad)):
                out.append(squad)
        return out

    def remaining(self, player):
        return MAX_UNITS - len(self.granted.get(player, []))

    def grant(self, player, squad):
        """The prompt callback: grant, then re-offer while there is room."""
        if squad is None or self.remaining(player) <= 0:
            return False
        grant_scouts(squad, game_log=self.game_log)
        self.granted.setdefault(player, []).append(squad)
        if player not in self.auto_players and self.decision_manager is not None:
            if not self._offer(player):
                self._next_player()
        return True

    # --- the pre-battle step ---------------------------------------------

    def start(self, pregame_controller, on_done=None):
        """Returns True if it took over (a prompt is on screen), False if there
        was nothing to do - in which case the caller runs the next step
        immediately."""
        self._on_done = on_done
        self._pending_players = list(getattr(pregame_controller, "_owners", lambda: ())())
        return self._next_player()

    def _next_player(self):
        while self._pending_players:
            player = self._pending_players.pop(0)
            if self._offer(player):
                return True
        if self._on_done is not None:
            done, self._on_done = self._on_done, None
            done()
        return False

    def _offer(self, player):
        """Ask (or decide) for one unit. Returns True while a human prompt is
        outstanding."""
        while self.remaining(player) > 0:
            candidates = []
            for bearer_squad in self.bearer_units(player):
                for target in self.eligible_targets(bearer_squad):
                    if target not in candidates:
                        candidates.append(target)
            if not candidates:
                return False
            if player in self.auto_players or self.decision_manager is None:
                self.grant(player, self._pick(player, candidates))
                continue
            options = [(f"{STRIKE_SWIFTLY}: {t.name}",
                        (lambda target=t: self.grant(player, target)))
                       for t in candidates]
            # Declining MUST advance the chain, not fall through to a None
            # callback: this step gates the rest of Resolve Pre-battle
            # Abilities, so a "no thanks" that does nothing would stall the
            # pregame on a prompt that has already been answered.
            options.append(("No more", lambda: self.decline(player)))
            self.decision_manager.request(
                player,
                f'{STRIKE_SWIFTLY}: give Scouts {GRANTED_SCOUT_DISTANCE_IN}" to a friendly '
                f"T'AU EMPIRE unit? ({self.remaining(player)} left)",
                options)
            return True
        return False

    def decline(self, player):
        """"Up to two" - stopping early is a legal answer. Spends this
        player's whole allowance so the offer does not come straight back, then
        moves on."""
        self.granted[player] = [None] * MAX_UNITS
        self._next_player()
        return True

    def _pick(self, player, candidates):
        bearers = [m for s in self.bearer_units(player) for m in self._bearer_models(s)]

        def distance(squad):
            return min((edge_distance(b, m) for b in bearers for m in _living(squad)),
                       default=SELECTION_RANGE_IN)

        return sorted(candidates, key=lambda s: (distance(s), s.name))[0]
