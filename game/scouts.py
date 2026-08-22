"""Rule 24.31 (SCOUTS) / 24.32 (SCOUT MOVE), resolved in rule 03.01's Resolve
Pre-battle Abilities step - after deployment and after Determine First Turn
(see pregame.SCOUTS_BEFORE_FIRST_TURN_ROLLOFF for why that order).

24.31 offers exactly one of three things per eligible unit:

  (a) a unit in Strategic Reserves may instead be set up wholly within your
      deployment zone;
  (b) a unit wholly within your deployment zone may make a scout move;
  (c) a DEDICATED TRANSPORT wholly within your deployment zone may make a
      scout move, if every model embarked within it has Scouts.

(a) reuses the deployment placement flow verbatim, (b) reuses
MovementController. (c) is unreachable with the datasheets in this project -
see eligible_transports_for_scout_move(), which reports WHY rather than
silently returning nothing."""

from game.squad import unit_wide_ability


def scout_distance(squad):
    """The X in Scouts X" for this unit, or None if it does not have the
    ability. Rule 24.31 applies only "if every model in a unit has this
    ability", hence unit_wide_ability (which is also 19.04-aware, so an
    attached character does not silently grant or remove it).

    The comprehension is load-bearing: unit_wide_ability routes through
    attached_units.unit_has_ability, which by 19.04 can report True while an
    individual model's `scouts` is still None - a bare min() over the raw
    attribute list would raise. min rather than max so a mixed attached unit
    gets the conservative distance."""
    if not unit_wide_ability(squad, "scouts"):
        return None
    values = [m.profile.scouts for m in squad.models if m.profile.scouts]
    return min(values) if values else None


def has_scouts(squad):
    return scout_distance(squad) is not None


def _wholly_within_own_zone(squad, deployment_zones):
    from game import deployment

    zone = deployment.zone_for(deployment_zones, squad.owner)
    if zone is None:
        return False
    return all(zone.contains_circle(m.x_in, m.y_in, m.radius_in) for m in squad.models)


def eligible_units(pregame_controller, owner):
    """Every unit of `owner` that rule 24.31 offers a choice to this step,
    with which branch applies. Returns [(squad, branch), ...] where branch is
    "reserve_redeploy" or "scout_move"."""
    state = pregame_controller.game_state
    zones = getattr(state, "deployment_zones", ())
    out = []

    for squad in pregame_controller.army(owner):
        if not has_scouts(squad):
            continue
        if squad in state.reserves:
            out.append((squad, "reserve_redeploy"))
        elif squad.embarked_in is None and _wholly_within_own_zone(squad, zones):
            out.append((squad, "scout_move"))
    return out


def eligible_transports_for_scout_move(pregame_controller, owner, game_log=None):
    """Rule 24.31's third branch. Returns [] with a logged reason on every
    board this project can currently build.

    Built as a guard rather than a feature, deliberately. Three independent
    things make it unreachable today, and each would have to change before it
    could fire:

      * UnitProfile has no `dedicated_transport` flag at all - "DEDICATED
        TRANSPORT" exists only in a Datasheet's display-only `keywords` tuple,
        which by this project's convention is never read as a rule.
      * The only datasheet with Scouts is Kroot Carnivores (7"), and the only
        transport_requires_infantry TRANSPORT here is the Devilfish, whose
        transport_excludes names KROOT - so they can never embark in it.
      * No Ork profile sets `scouts` at all, so the Trukk has no candidate
        passengers either.

    Reporting which precondition failed means the gap surfaces as a log line
    the day a datasheet grants Scouts to a transportable unit, instead of
    silently doing nothing. Adding a speculative `dedicated_transport` flag
    now would be modelling a rule nothing can exercise."""
    state = pregame_controller.game_state
    scouting_passengers = [
        s for s in state.embarked_squads
        if s.owner == owner and has_scouts(s)
    ]
    if not scouting_passengers and game_log is not None:
        game_log.add(
            f"[scouts] {owner}: no embarked unit has the Scouts ability, so rule 24.31's "
            f"DEDICATED TRANSPORT branch does not apply.",
            file_only=True,
        )
    return []


class ScoutsStep:
    """Drives rule 24.31 for both players during PREBATTLE_ABILITIES.

    Held by PregameController as `scouts_step`; if it is None the step is
    skipped entirely, which is what keeps the pre-game working for armies that
    have no Scouts unit at all."""

    def __init__(self, movement_controller, game_log=None, on_resolve=None):
        self.movement_controller = movement_controller
        self.game_log = game_log
        # Optional callable(pregame, squad, branch, distance) -> bool, wired to
        # the AI so it can take its own scout moves. Returning False means
        # "declined", which is always legal (24.31 offers, never compels).
        self.on_resolve = on_resolve
        self._queue = []
        self._pregame = None

    def start(self, pregame_controller):
        self._pregame = pregame_controller
        self._queue = []
        for owner in ("Player 1", "Player 2"):
            eligible_transports_for_scout_move(pregame_controller, owner, self.game_log)
            for squad, branch in eligible_units(pregame_controller, owner):
                self._queue.append((squad, branch))
        if not self._queue:
            self._log("Pre-battle abilities: no unit has Scouts (rule 24.31).")
            pregame_controller.finish_prebattle_abilities()
            return
        self._resolve_next()

    @property
    def current(self):
        return self._queue[0] if self._queue else None

    def _resolve_next(self):
        while self._queue:
            squad, branch = self._queue[0]
            distance = scout_distance(squad)
            handled = False
            if self.on_resolve is not None:
                handled = bool(self.on_resolve(self._pregame, squad, branch, distance))
            if not handled:
                self._log(
                    f'{squad.owner}: {squad.name} declines its Scouts {distance:g}" '
                    f"option (rule 24.31).",
                    file_only=True,
                )
            self._queue.pop(0)
        self._pregame.finish_prebattle_abilities()

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)
