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


def eligible_units(pregame_controller, owner, game_log=None):
    """Every unit of `owner` that rule 24.31 offers a choice to this step,
    with which branch applies. Returns [(squad, branch), ...] where branch is
    "reserve_redeploy" or "scout_move".

    WHY THE EXCLUSIONS ARE LOGGED. "Wholly within your deployment zone" is
    printed twice - once in 24.31's second bullet and again as 24.32's own
    ELIGIBLE IF - so a unit standing outside its zone genuinely cannot scout.
    The catch is that INFILTRATORS (24.20) deploy OUTSIDE their zone by
    design, so a unit with both abilities is correctly refused and the player
    has no way to see why.

    Reported as a bug for exactly that reason: a human's Striking Scorpions
    (SCOUTS 7" and INFILTRATORS) were never offered anything and looked broken.
    They were not - they were ineligible, silently. So every SCOUTS unit that
    is passed over now says so, the same "report WHY rather than silently
    returning nothing" that eligible_transports_for_scout_move() already does.
    """
    state = pregame_controller.game_state
    zones = getattr(state, "deployment_zones", ())
    out = []

    def _log(message):
        if game_log is not None:
            game_log.add(message, file_only=True)

    for squad in pregame_controller.army(owner):
        if not has_scouts(squad):
            continue
        if squad in state.reserves:
            out.append((squad, "reserve_redeploy"))
        elif squad.embarked_in is not None:
            _log(f"[scouts] {owner}: {squad.name} is embarked, so 24.31's own "
                 f"unit branch does not apply (the DEDICATED TRANSPORT branch is "
                 f"reported separately).")
        elif not _wholly_within_own_zone(squad, zones):
            _log(f"[scouts] {owner}: {squad.name} has Scouts but is NOT wholly "
                 f"within its deployment zone, so 24.31/24.32 offer it no scout "
                 f"move. Expected for an INFILTRATORS unit (24.20), which "
                 f"deploys outside the zone on purpose.")
        else:
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

    def __init__(self, movement_controller, game_log=None, on_resolve=None,
                 decision_manager=None, human_players=()):
        self.movement_controller = movement_controller
        self.game_log = game_log
        # Optional callable(pregame, squad, branch, distance) -> bool, wired to
        # the AI so it can take its own scout moves. Returning False means
        # "declined", which is always legal (24.31 offers, never compels).
        self.on_resolve = on_resolve
        # THE HUMAN'S HALF, and the reason this class grew a pending state.
        #
        # Real bug, user report: "Die KI laesst mich immer noch nicht den
        # reaktiven Move fuer die Scouts machen. Sie macht einfach weiter."
        # deployment_ai.resolve_scouts() returns False for a unit it does not
        # own, and its docstring says that means "left to the human" - but
        # nothing implemented the other half. _resolve_next() read False as
        # "declined", popped the unit and drained the whole queue in one
        # synchronous loop, so a human's Striking Scorpions were logged as
        # declining a move they were never offered.
        #
        # A comment promising a behaviour that no code performs is the same
        # class of defect as a controller that is built and never fed.
        self.decision_manager = decision_manager
        self.human_players = set(human_players)
        self._queue = []
        self._pregame = None
        self._pending = None   # (squad, branch) while the human is deciding or moving

    def start(self, pregame_controller):
        self._pregame = pregame_controller
        self._queue = []
        for owner in ("Player 1", "Player 2"):
            eligible_transports_for_scout_move(pregame_controller, owner, self.game_log)
            for squad, branch in eligible_units(pregame_controller, owner, self.game_log):
                self._queue.append((squad, branch))
        if not self._queue:
            self._log("Pre-battle abilities: no unit has Scouts (rule 24.31).")
            pregame_controller.finish_prebattle_abilities()
            return
        self._resolve_next()

    @property
    def current(self):
        return self._queue[0] if self._queue else None

    @property
    def is_pending(self):
        """True while a human is being offered, or is taking, a scout move.
        The pre-game must not advance past this."""
        return self._pending is not None

    def _resolve_next(self):
        while self._queue:
            squad, branch = self._queue[0]
            distance = scout_distance(squad)
            if self.on_resolve is not None and self.on_resolve(self._pregame, squad, branch, distance):
                self._queue.pop(0)
                continue
            if self._offer_to_human(squad, branch, distance):
                return   # PAUSE - the queue resumes from _finish_current()
            self._log(
                f'{squad.owner}: {squad.name} declines its Scouts {distance:g}" '
                f"option (rule 24.31).",
                file_only=True,
            )
            self._queue.pop(0)
        self._pregame.finish_prebattle_abilities()

    def _offer_to_human(self, squad, branch, distance):
        """Opens the choice for a human-owned unit. Returns True if the queue
        must now WAIT.

        Only the scout-move branch is offered: "reserve_redeploy" sets a unit
        up in its own zone instead, which is a placement rather than a move and
        would need SetupController threaded through here. Declined for a human
        with a logged reason rather than half-implemented - the same guard
        shape eligible_transports_for_scout_move() already uses."""
        if squad.owner not in self.human_players or self.decision_manager is None:
            return False
        if branch != "scout_move" or self.movement_controller is None:
            return False
        self._pending = (squad, branch)
        self.decision_manager.request(
            squad.owner,
            f'{squad.name}: Scouts {distance:g}" - take the pre-battle move? (rule 24.31)',
            [
                (f'Scout Move (up to {distance:g}")',
                 lambda: self.movement_controller.start_scout_move(squad, distance)),
                ("Decline", self._decline_current),
            ],
        )
        return True

    def _decline_current(self):
        squad = self._pending[0] if self._pending else None
        if squad is not None:
            self._log(
                f"{squad.owner}: {squad.name} declines its Scouts option (rule 24.31).",
                file_only=True,
            )
        self._finish_current()

    def on_scout_move_finished(self, squad):
        """Wired to MovementController.on_scout_move_finished in main.py, so a
        confirmed OR cancelled move both resume the queue - a cancel that did
        not resume would strand the whole pre-game."""
        if self._pending is not None and self._pending[0] is squad:
            self._finish_current()

    def _finish_current(self):
        self._pending = None
        if self._queue:
            self._queue.pop(0)
        self._resolve_next()

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)
