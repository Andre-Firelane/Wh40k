from game import formation_layout
from game.terrain import DENSE

IDLE = "idle"
PLACING = "placing"


class SetupController:
    """Rule 03.02 (Set Up): whenever a rule instructs you to set up a unit
    (reserves arriving via Ingress, rule 20.04; a unit disembarking from a
    TRANSPORT, rules 18.04/18.05; or, later, initial deployment), its
    models get placed on the battlefield so the unit ends up in coherency
    and unengaged - "all other requirements and restrictions" (e.g.
    deployment zone limits) aren't modeled yet, since no concrete
    deployment map/zone rules have been given.

    Deliberately agnostic about where a unit comes from or goes back to -
    the caller (IngressController, TransportController, ...) is responsible
    for that: it removes the squad from wherever it was (reserves,
    embarked within a TRANSPORT) before calling start_setup(), and supplies
    `on_cancel` to put it back there if the placement is abandoned. This
    lets every "set up a unit" rule share the exact same drag-into-
    coherency workflow and PLACING state machine instead of each building
    its own.

    Workflow: the caller drops the unit's models on the board (start_setup)
    - they appear stacked at the drop point and can then be dragged apart
    individually, exactly like a Movement move (no distance limit, no
    terrain/model blocking - 03.02 doesn't restrict that), until confirmed.
    "If you cannot set up all of the models in a unit, remove that unit
    from the battlefield and return it to its original position" -
    modeled as cancel_setup() sending the whole unit back (via on_cancel)
    rather than leaving it partially placed."""

    def __init__(
        self, game_state, obstacles=None, all_tokens=None, game_log=None,
        board_width_in=None, board_height_in=None,
    ):
        self.game_state = game_state
        self.obstacles = obstacles if obstacles is not None else []
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.game_log = game_log
        self.board_width_in = board_width_in
        self.board_height_in = board_height_in

        self.state = IDLE
        self.setting_up_squad = None
        self.errors = []
        self._extra_check = None      # optional callable(squad) -> list[str]
        self._allow_engaged = False   # rule 18.04 Combat Disembark can be set up engaged
        self._on_cancel = None        # required callable(squad) - where the squad goes back to
        # Full per-position legality predicate for THIS placement, supplied by
        # whichever rule started it (rule 20.04's Ingress constraints, rule
        # 18.04's distance-from-TRANSPORT, ...) - position_valid() below only
        # knows the checks common to every Set Up. Used by clamp_position()
        # so a drag can't be dropped on illegal ground in the first place, and
        # by main.py to paint the same predicate as the green/red overlay, so
        # what you see and what you're allowed to do cannot drift apart.
        self._placement_validator = None
        # Bumped on every start_setup/reset so caches tied to "this one
        # placement" (the overlay's legality mask) can tell placements apart
        # even when the same squad is set up twice in a row.
        self.placement_generation = 0
        # Quality-of-life (user: "ich will oft nicht jedes modell einzeln
        # anfassen beim platzieren. besteht die moeglichkeit, dass es ein
        # toggle gibt, womit ich squads in bloecken platzieren kann und danach
        # noch bewegen kann, wenn ich will?"). When on, start_setup() lays the
        # unit out as a block instead of stacking it on the drop point, and a
        # drag moves the whole block rigidly rather than one model. A
        # persistent GLOBAL preference, never reset per placement - the same
        # treatment MovementController.group_move_enabled gets, and for the
        # same stated reason ("die toggles sollen global gelten").
        self.block_placement_enabled = True
        # Positions at the moment a block drag started, so the drag is a rigid
        # translation from where the block WAS rather than an accumulation of
        # per-frame deltas (which would drift and shear).
        self._group_drag_origin = {}

    @property
    def allows_engaged(self):
        """Whether the CURRENT placement may end within Engagement Range of
        an enemy - i.e. whether confirm_setup()'s "must be set up unengaged"
        check (rule 03.02) is waived, as rule 18.04's Combat Disembark
        waives it. Public because anything that GENERATES candidate
        positions has to know: a slot the generator hands out but confirm
        rejects fails the WHOLE unit, and for an Emergency Disembark (18.05)
        that means the unit is destroyed (user report: a Trukk was shot down
        and all six Meganobz died with it, on a board with 66 sq.in of legal
        unengaged ground inside the 6" limit)."""
        return self._allow_engaged

    def placement_validator(self, squad=None):
        """The predicate the CURRENT placement is judged by: the owning rule's
        own, if it supplied one, else the plain Set Up checks. Returns
        `f(token, x_in, y_in) -> bool`."""
        if self._placement_validator is not None:
            return self._placement_validator
        return lambda token, x_in, y_in: self.position_valid(token, x_in, y_in, squad=squad)

    def can_start_setup(self, squad):
        return self.state == IDLE and squad is not None

    def start_setup(
        self, squad, x_in, y_in, on_cancel, extra_check=None, allow_engaged=False,
        placement_validator=None,
    ):
        """Begin placing `squad`'s models on the battlefield, all stacked
        at the drop point (x_in, y_in) to start - the caller then drags
        each one apart before confirming. `on_cancel(squad)` is required -
        it's how the squad gets put back where it came from if the
        placement is abandoned (SetupController itself doesn't know or
        care whether that's reserves, a TRANSPORT, or something else).
        `extra_check`, if given, is called at confirm time alongside the
        built-in checks (e.g. rule 20.04's Ingress set-up-distance/enemy-
        proximity constraints, or 18.04/18.05's set-up-distance-from-
        TRANSPORT constraint). `allow_engaged=True` skips the "must be set
        up unengaged" check (rule 18.04's Combat Disembark can be set up
        engaged with units its TRANSPORT is already engaged with).
        `placement_validator(token, x_in, y_in) -> bool`, if given, is that
        same rule's per-POSITION check (the live counterpart of extra_check's
        at-confirm-time squad check) - see placement_validator()."""
        if not self.can_start_setup(squad):
            return
        # Set the placement's own state first: the block layout below is judged
        # by placement_validator(), which reads _placement_validator, and
        # add_token() has to have happened before overlap can be judged against
        # the real token list.
        for model in squad.models:
            model.x_in, model.y_in = x_in, y_in
            if model not in self.game_state.tokens:
                self.game_state.add_token(model)
        self.setting_up_squad = squad
        self.state = PLACING
        self.errors = []
        self._extra_check = extra_check
        self._allow_engaged = allow_engaged
        self._on_cancel = on_cancel
        self._placement_validator = placement_validator
        self._group_drag_origin = {}
        self.placement_generation += 1

        if self.block_placement_enabled:
            self.arrange_as_block(x_in, y_in)

    def invalidate_placement(self):
        """Tell caches keyed on placement_generation that the CURRENT
        placement's legal ground has changed underneath them, without
        restarting the placement or moving anything.

        Needed because a placement's validator is not a constant: Retaliation
        Cadre's The Shortened Blade (2CP, game/shortened_blade.py) is bought
        mid-placement and relaxes the arrival's distance-to-enemies rule, so
        the overlay's cached legality mask - which is deliberately computed
        once per placement, not per frame - would otherwise keep painting the
        old ring until the placement restarted."""
        self.placement_generation += 1

    def toggle_block_placement(self):
        """Quality-of-life only, so deliberately unguarded and callable at any
        time - same treatment as MovementController.toggle_group_move(). Takes
        effect on the next placement; it never rearranges a placement already
        in progress, since that would throw away adjustments the player has
        already made by hand."""
        self.block_placement_enabled = not self.block_placement_enabled

    def arrange_as_block(self, origin_x, origin_y):
        """Lay the unit being placed out as a block around (origin_x, origin_y)
        instead of leaving it stacked there.

        Uses the same ring packer the AI's own arrival and deployment use
        (game/formation_layout.py), so a hand-dropped block and an AI-placed
        one are the same shape and obey the same three guarantees - per-model
        legality, no squadmate overlap, and rule 09.02 coherency by
        construction.

        Facing is "away from the board centre" (formation_layout's own
        helper): for a unit being set up in its own deployment zone the block
        then grows backwards into the zone rather than spilling forward out of
        it. The AI's version instead faces away from the nearest enemy, which
        is a threat judgement and stays on its side of the line."""
        squad = self.setting_up_squad
        if squad is None or not squad.models:
            return
        valid = self.placement_validator(squad)
        positions = formation_layout.pack_positions(
            squad, origin_x, origin_y,
            base_angle=formation_layout.away_from_board_centre(origin_x, origin_y),
            position_valid=valid,
        )
        for model, (x_in, y_in) in zip(squad.models, positions):
            model.x_in, model.y_in = self.clamp_position(model, x_in, y_in)

    def begin_group_drag(self):
        """Snapshot the block's current shape so a drag translates it rigidly.

        Rigid matters: under a pure translation the pairwise model distances do
        not change at all, so rule 09.02's coherency and 9" spread are
        invariant no matter how far the block is dragged - the same argument
        _creep_toward() rests on. Clamping each model separately against
        terrain instead (what MovementController.apply_group_drag does, because
        a Movement move has a per-model distance budget to respect) would shear
        the block apart, which is exactly what this feature exists to avoid."""
        squad = self.setting_up_squad
        if squad is None:
            return
        self._group_drag_origin = {m.id: (m.x_in, m.y_in) for m in squad.models}

    def apply_group_drag(self, dx_in, dy_in):
        """Move the whole block by (dx_in, dy_in), reduced to the largest
        fraction of that offset at which EVERY model still stands on legal
        ground.

        Bisection rather than per-model clamping, for the reason in
        begin_group_drag(): the block has to stay rigid.

        If the block did NOT start legal it follows the cursor freely instead.
        That is not a fallback for a broken state but a real case: turning the
        toggle on mid-placement over a still-stacked squad leaves every model
        overlapping, and bisecting from an illegal origin would find no legal
        fraction and freeze the unit in place. Same reasoning - and same
        wording - as clamp_drag()'s third case."""
        squad = self.setting_up_squad
        if squad is None or not self._group_drag_origin:
            return

        def place(fraction):
            for model in squad.models:
                origin = self._group_drag_origin.get(model.id)
                if origin is None:
                    continue
                model.x_in = origin[0] + dx_in * fraction
                model.y_in = origin[1] + dy_in * fraction

        valid = self.placement_validator(squad)

        def legal():
            return all(
                self._on_board(model, model.x_in, model.y_in) and valid(model, model.x_in, model.y_in)
                for model in squad.models
            )

        place(0.0)
        if not legal():
            place(1.0)
            return

        place(1.0)
        if legal():
            return
        low, high = 0.0, 1.0  # low is known-legal (checked just above), high known-illegal
        for _ in range(self._CLAMP_BISECTION_STEPS):
            mid = (low + high) / 2
            place(mid)
            if legal():
                low = mid
            else:
                high = mid
        place(low)

    def _on_board(self, token, x_in, y_in):
        if self.board_width_in is not None and not (token.radius_in <= x_in <= self.board_width_in - token.radius_in):
            return False
        if self.board_height_in is not None and not (token.radius_in <= y_in <= self.board_height_in - token.radius_in):
            return False
        return True

    def is_placeable(self, token):
        return (
            self.state == PLACING
            and self.setting_up_squad is not None
            and token in self.setting_up_squad.models
        )

    def position_valid(self, token, x_in, y_in, squad=None):
        """Whether `token` could legally end up at (x_in, y_in) right now -
        used to paint the green/red placement overlay (Renderer.
        draw_placement_overlay()), including while a squad is still being
        dragged out of the Reserves panel and hasn't actually been dropped
        yet (`squad` given explicitly, since self.setting_up_squad is only
        set once PLACING begins - see IngressController.position_valid()).
        Checks the board edge, terrain that blocks movement for this model
        (13.05/13.06), and overlap with any OTHER already-placed token -
        deliberately NOT this squad's own other members, since we don't
        know where they'll end up yet, and not coherency/engagement, which
        depend on the whole squad's final positions together, not a single
        point."""
        if squad is None:
            squad = self.setting_up_squad
        if self.board_width_in is not None and not (token.radius_in <= x_in <= self.board_width_in - token.radius_in):
            return False
        if self.board_height_in is not None and not (token.radius_in <= y_in <= self.board_height_in - token.radius_in):
            return False
        for obstacle in self.obstacles:
            # Dense terrain (walls) can never be the model's final resting
            # spot, even for INFANTRY/BEASTS/SWARM/MOBILE models that can
            # move/be placed through it (rule 13.06) - see Squad.check_terrain().
            if obstacle.category == DENSE and obstacle.overlaps_circle(x_in, y_in, token.radius_in):
                return False
        for other in self.all_tokens:
            if other is token or (squad is not None and other in squad.models):
                continue
            dist = ((x_in - other.x_in) ** 2 + (y_in - other.y_in) ** 2) ** 0.5
            if dist < token.radius_in + other.radius_in:
                return False
        return True

    # How finely clamp_drag() splits the drag segment when the cursor leaves
    # legal ground - 6 halvings resolve a 12" drag to under 0.2".
    _CLAMP_BISECTION_STEPS = 6

    def clamp_position(self, token, x_in, y_in):
        """Unlike a Movement move, Set Up has no distance limit, and 03.02
        doesn't mention terrain or passing through other models while
        placing - only keep the model on the battlefield.

        This is the plain geometric clamp, used by anything that computes a
        position outright and validates the finished squad itself (see
        ai/agent_driver.py's disembark facing ladder, which re-places the same
        models several times over and must not have earlier attempts held in
        place). The human drag gesture wants clamp_drag() below instead."""
        if self.board_width_in is not None:
            x_in = max(token.radius_in, min(self.board_width_in - token.radius_in, x_in))
        if self.board_height_in is not None:
            y_in = max(token.radius_in, min(self.board_height_in - token.radius_in, y_in))
        return x_in, y_in

    def clamp_drag(self, token, x_in, y_in):
        """Where a MOUSE DRAG aimed at (x_in, y_in) actually puts the model.

        Set Up restricts nothing about the PATH - only where the model ends
        up - so this is a landing rule, not a movement rule (User: "kann man
        es nicht so machen, dass ich das modell gar nicht erst in die rote
        zone dragen kann wie bei der maximalreichweite von movement?"):

        - cursor over legal ground -> go straight there, even if the straight
          line crossed illegal ground on the way. Nothing in 03.02 forbids
          that, and forbidding it would make a legal spot on the far side of a
          wall unreachable by dragging at all.
        - cursor over illegal ground -> slide up to the boundary instead, so
          the model hugs the edge of the legal region rather than being
          dropped somewhere it isn't allowed to stay.
        - model currently ON illegal ground -> follow the cursor freely. That
          is the normal starting state, not an error: start_setup() stacks
          every model on the drop point, which for a Disembark is the
          TRANSPORT's own centre - inside its hull, so illegal. Clamping there
          would trap the whole unit on top of its transport.

        Judged by the same predicate the green/red overlay paints (see
        placement_validator()), so what you see is what you can do."""
        x_in, y_in = self.clamp_position(token, x_in, y_in)
        valid = self.placement_validator(self.setting_up_squad)
        if valid(token, x_in, y_in):
            return x_in, y_in
        ox, oy = token.x_in, token.y_in
        if not valid(token, ox, oy):
            return x_in, y_in

        low, high = 0.0, 1.0  # `low` is always known-legal, `high` known-illegal
        for _ in range(self._CLAMP_BISECTION_STEPS):
            mid = (low + high) / 2
            if valid(token, ox + (x_in - ox) * mid, oy + (y_in - oy) * mid):
                low = mid
            else:
                high = mid
        return ox + (x_in - ox) * low, oy + (y_in - oy) * low

    def confirm_setup(self):
        if self.setting_up_squad is None:
            return
        squad = self.setting_up_squad

        errors = squad.check_coherency()
        errors += squad.check_terrain(self.obstacles)
        errors += squad.check_model_overlap(self.all_tokens)
        if not self._allow_engaged and squad.is_engaged(self.all_tokens):
            errors.append("Your unit must be set up unengaged (rule 03.02).")
        if self._extra_check is not None:
            errors += self._extra_check(squad)
        if errors:
            self.errors = errors
            return

        # Rule 18.02: "not set up on the battlefield this turn" blocks
        # embarking - cleared at end of turn by main.py, alongside
        # Squad.fights_first.
        squad.set_up_this_turn = True
        if self.game_log is not None:
            self.game_log.add(f"{squad.owner} set up {squad.name}.")
        self._reset_state()

    def cancel_setup(self):
        """Rule 03.02: "If you cannot set up all of the models in a unit,
        remove that unit from the battlefield and return it to its
        original position" - the whole unit goes back (via on_cancel), not
        just the models that were causing a problem."""
        if self.setting_up_squad is None:
            return
        squad = self.setting_up_squad
        for model in squad.models:
            if model in self.game_state.tokens:
                self.game_state.tokens.remove(model)
        on_cancel = self._on_cancel
        self._reset_state()
        on_cancel(squad)

    def _reset_state(self):
        self._group_drag_origin = {}
        self.setting_up_squad = None
        self.state = IDLE
        self.errors = []
        self._extra_check = None
        self._allow_engaged = False
        self._on_cancel = None
        self._placement_validator = None
        self.placement_generation += 1
