from game import whole_unit_drag
from game import formation_layout, front_rank, line_drag
from game.squad import coherency_probe
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
        # WHICH of the unit's models this placement owns. None means all of
        # them, which is every Set Up (03.02 sets up a UNIT) and therefore
        # every caller that existed before rule 01.02.03's model return needed
        # a subset. See placing_models below.
        self._placing_models = None
        # Whether confirming counts as "set up this turn" (rule 18.02, which
        # reads it as "cannot embark"). True for a real Set Up; False for a
        # model return, because a unit that reanimated two models was not set
        # up - it was standing there all along.
        self._mark_set_up = True
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

    @property
    def placing_models(self):
        """The models THIS placement may move.

        Every model of the unit for a Set Up - rule 03.02 sets up a UNIT, and
        that is what every caller but one wants. A SUBSET for rule 01.02.03's
        model return, where the survivors are already standing somewhere legal
        and must not be touched: only the models coming back are being placed.

        One property rather than a parameter threaded through nine methods,
        because "which models are being placed" is asked by the stacking loop,
        both drags, the line drag, is_placeable(), position_valid()'s overlap
        exemption and cancel_setup() - and those nine agreeing is the whole
        difference between a partial placement and a broken one."""
        if self.setting_up_squad is None:
            return []
        if self._placing_models is None:
            return list(self.setting_up_squad.models)
        return [m for m in self._placing_models if m in self.setting_up_squad.models]

    @property
    def is_partial(self):
        """Whether this placement owns only some of the unit's models."""
        return self._placing_models is not None

    def placement_validator(self, squad=None):
        """The predicate the CURRENT placement is judged by: the owning rule's
        own, if it supplied one, else the plain Set Up checks. Returns
        `f(token, x_in, y_in) -> bool`.

        FOR A PARTIAL PLACEMENT IT ALSO CARRIES 09.02's COHERENCY. User:
        "immer wenn man Einheiten platzieren muss, zb durch Reanimation, muss
        man in coherency platzieren. dementsprechend muss auch das overlay
        sein. im Moment geht das über die ganze map?" - measured on map2, a
        Reanimation return painted 85.9% of the board green where 2.0% was
        legal, 42x too much ground, and the rejection only arrived at Confirm.

        WHY ONLY A PARTIAL ONE. position_valid()'s docstring gives the reason
        coherency is not in it: it "depends on the whole squad's final
        positions together, not a single point" - true while every model of the
        unit is still in the air. A RETURN is the case where it is not: the
        survivors are standing still and are the anchor, so "would this model
        leave the unit in one piece" has an exact answer per position. A full
        Set Up keeps today's behaviour (user's own call), and so does the
        deployment AI, which reads position_valid() directly and never comes
        through here.

        ONE PROBE PER MODEL, cached: the overlay asks thousands of points and
        the drag clamp bisects, while everything except the dragged model
        stands still - see squad.coherency_probe()."""
        base = self._placement_validator
        if base is None:
            base = lambda token, x_in, y_in: self.position_valid(
                token, x_in, y_in, squad=squad)
        if not self.is_partial:
            return base

        unit = squad if squad is not None else self.setting_up_squad
        if unit is None:
            return base
        probes = {}

        def _valid(token, x_in, y_in):
            if not base(token, x_in, y_in):
                return False
            probe = probes.get(id(token))
            if probe is None:
                probe = probes[id(token)] = coherency_probe(unit.models, token)
            return probe(x_in, y_in)

        return _valid

    def base_edge_zones(self, squad=None, token=None):
        """The placement drawn as BASE EDGES instead of centres.

        User: "momentan ist die Grenze des overlays so dass der Base
        Mittelpunkt bis zur Grenze gehen kann. intuitiver waere aber der
        Baserand ... bei Baserand muss jedes Modell unabhaengig von der
        Basegroesse den selben Abstand einhalten."

        WHY THE CENTRE VERSION HAD TO GO. Every rule here is measured edge to
        edge (edge_distance() is centres minus both radii), so the RULE already
        treats all base sizes alike. The picture did not: the legal-centre
        region is a different curve per base size, the overlay can only draw
        one, and main.py picked the biggest model on the claim that its region
        is "a subset of every other model's". Coherency broke that claim -
        it GROWS with the radius while terrain and edges shrink with it -
        so neither model's mask was safe for the other. Measured on a
        Warriors + Overlord unit: 8.6 sq.in legal for the big model only,
        9.3 sq.in for the small one only.

        TWO ZONES, BECAUSE ONE SIGN FLIPS. Returned as
        `(keep_out, band)`, both `f(x_in, y_in) -> bool` and both evaluated
        for a POINT-SIZED base, which is what makes them independent of who is
        being placed:

          * `keep_out(x, y)` - no part of any base may be here. Board edge,
            Dense terrain, other models, and whatever the owning rule adds
            (01.02.03's Engagement clause). Exact: the predicate tests the
            model's disc against that geometry, so "the whole base is out of
            the red" is the same statement.
          * `band(x, y)` - 09.02's coherency, which reads the other way round:
            the base must REACH this, not avoid it. `edge_distance <= 2"` says
            the base overlaps the 2"-grown neighbours, so "touch the green" is
            again exactly the rule. None when there is nothing to stay coherent
            with (a full Set Up, where every model is still in the air).

        HOW THE POINT-SIZED READING IS TAKEN: the token's own radius is set to
        zero for the duration of each call. Every term reads `radius_in` off
        the model it is handed, so this asks the SAME predicates rather than a
        second copy of the rules - and it keeps the model's identity, which a
        stand-in object would lose (position_valid() exempts a model from
        colliding with itself by identity)."""
        base = self._placement_validator
        if base is None:
            base = lambda t, x_in, y_in: self.position_valid(t, x_in, y_in, squad=squad)
        if token is None:
            return (lambda x_in, y_in: False), None

        def keep_out(x_in, y_in):
            real = token.radius_in
            token.radius_in = 0.0
            try:
                return not base(token, x_in, y_in)
            finally:
                token.radius_in = real

        band = None
        unit = squad if squad is not None else self.setting_up_squad
        if self.is_partial and unit is not None:
            real = token.radius_in
            token.radius_in = 0.0
            try:
                # Built here, inside the zero-radius window: coherency_probe()
                # freezes the moving model's radius when it is created.
                band = coherency_probe(unit.models, token)
            finally:
                token.radius_in = real
        return keep_out, band

    def overlay_cache_key(self, token=None):
        """What the placement overlay's cached legality mask must be keyed on.

        The mask is deliberately built once per placement rather than per frame
        (game/placement_overlay.py), and placement_generation was enough while
        the legal ground was a fact about the BOARD - terrain, edges, other
        units - which does not move while a unit is being placed.

        A PARTIAL placement broke that: 09.02's coherency is now part of the
        predicate (see placement_validator()), so the legal region for one
        model is drawn from where its SQUADMATES stand, and they move as the
        player positions them. Keying on the generation alone would keep
        painting the ring from before the last model was dropped.

        Which is why this lives here and not in main.py: "what the legal ground
        depends on" is a fact about the rule being enforced, and the drawing
        code should not have to know that coherency reads neighbours."""
        if not self.is_partial:
            return self.placement_generation
        unit = self.setting_up_squad
        if unit is None:
            return self.placement_generation
        # The OTHER models: the drawn one contributes nothing to its own ring,
        # and leaving it out is what keeps the key stable while it is dragged.
        # Its identity still has to be in there, or two same-sized models would
        # share a mask that is only correct for one of them.
        others = tuple(sorted(
            (round(m.x_in, 2), round(m.y_in, 2))
            for m in unit.models
            if m is not token and not m.is_dead() and m.x_in is not None
        ))
        return (self.placement_generation, id(token), others)

    def can_start_setup(self, squad):
        return self.state == IDLE and squad is not None

    def start_setup(
        self, squad, x_in, y_in, on_cancel, extra_check=None, allow_engaged=False,
        placement_validator=None, models=None, positions=None, mark_set_up=True,
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
        at-confirm-time squad check) - see placement_validator().

        THREE ARGUMENTS FOR RULE 01.02.03's MODEL RETURN, all defaulting to
        what every existing caller already got:

        `models` limits the placement to a SUBSET of the unit. A Set Up places
        a unit; a model return puts one or two models back into a unit that is
        already standing, and the survivors must not move. None means all of
        them, so no existing caller changes.

        `positions` gives each placed model its STARTING point instead of
        stacking them all on (x_in, y_in). A return already knows a legal spot
        for each model (formation_layout.returning_positions()), so the human
        starts from the engine's own answer and nudges it, rather than from a
        pile that has to be dragged apart. None keeps the stack-then-block
        behaviour every Set Up has.

        `mark_set_up=False` stops confirming from setting
        `squad.set_up_this_turn`. Rule 18.02 reads that as "cannot embark this
        turn", and a unit that reanimated a model was not set up - it never
        left. Easy to miss, because it shows up a phase later as a transport
        that will not take passengers."""
        if not self.can_start_setup(squad):
            return
        # Set the placement's own state first: the block layout below is judged
        # by placement_validator(), which reads _placement_validator, and
        # add_token() has to have happened before overlap can be judged against
        # the real token list.
        placing = list(models) if models is not None else list(squad.models)
        starts = list(positions) if positions is not None else None
        for index, model in enumerate(placing):
            if starts is not None and index < len(starts) and starts[index] is not None:
                model.x_in, model.y_in = starts[index]
            else:
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
        self._placing_models = list(models) if models is not None else None
        self._mark_set_up = mark_set_up
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

    @property
    def block_placement_enabled(self):
        """Quality-of-life (user: "ich will oft nicht jedes modell einzeln
        anfassen beim platzieren. besteht die moeglichkeit, dass es ein toggle
        gibt, womit ich squads in bloecken platzieren kann und danach noch
        bewegen kann, wenn ich will?"). When on, start_setup() lays the unit
        out as a block instead of stacking it on the drop point, and a drag
        moves the whole block rigidly rather than one model.

        THE VALUE LIVES IN game/whole_unit_drag.py, shared with
        MovementController.group_move_enabled - the user merged the two
        ("Block Deployment und Block Movement zusammenfassen"), and one
        preference must have one home. Still a named attribute here so both
        read sites and the tests that assign to it are unchanged.

        A persistent GLOBAL preference, never reset per placement - which is
        also why it is not an __init__ assignment: constructing a controller
        must not silently reset what the player chose."""
        return whole_unit_drag.is_enabled()

    @block_placement_enabled.setter
    def block_placement_enabled(self, value):
        whole_unit_drag.set_enabled(value)

    def toggle_block_placement(self):
        """Flip the shared whole-unit-drag preference. Deliberately unguarded
        and callable at any time. Takes effect on the next placement; it never
        rearranges a placement already in progress, since that would throw away
        adjustments the player has already made by hand."""
        whole_unit_drag.toggle()

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
        placing = self.placing_models
        if squad is None or not placing:
            return
        valid = self.placement_validator(squad)
        positions = formation_layout.pack_positions(
            squad, origin_x, origin_y,
            base_angle=formation_layout.away_from_board_centre(origin_x, origin_y),
            position_valid=valid,
        )
        for model, (x_in, y_in) in zip(placing, positions):
            model.x_in, model.y_in = self.clamp_position(model, x_in, y_in)

    def apply_line_drag(self, start_in, end_in, legal_frontages=()):
        """Total-War style: form the unit being placed up along the segment
        start_in -> end_in, the drag's LENGTH setting the frontage. Returns a
        LineDragInfo, or None when nothing is being placed.

        The Set Up sibling of MovementController.apply_line_drag(), and the
        differences are all forced by Set Up having no per-model distance
        budget:

        - the ordering reads the GESTURE-START snapshot (begin_drag's
          _group_drag_origin), not the live positions. During a drag those hold
          the previous frame's preview, so reading them would make the layout a
          function of its own output - a model stopped at the zone edge would
          ratchet along it frame by frame.
        - clamp_drag() per model rather than clamp_position(): it is
          validator-aware, so the deployment zone is enforced by the very
          predicate the green/red overlay paints, and the front rank hugs the
          zone edge instead of protruding out of it.
        - melee characters go to the front unconditionally. The Movement half
          has to check the unit can afford the extra walk; here walk is free.
        - nothing commits. confirm_setup() judges, exactly as every other Set
          Up drag does.

        Known edge, inherited from clamp_drag()'s own third case: with the
        block toggle off, start_setup() stacks every model on the drop point,
        so all of them stand on illegal ground and clamp_drag() lets them
        follow freely. The first line drag out of a stacked squad therefore
        places without clamping; the second is clamped normally."""
        squad = self.setting_up_squad
        placing = self.placing_models
        if squad is None or not placing:
            return None
        origins = [self._group_drag_origin.get(m.id) for m in placing]
        if any(origin is None for origin in origins):
            origins = [(m.x_in, m.y_in) for m in placing]

        length = ((end_in[0] - start_in[0]) ** 2 + (end_in[1] - start_in[1]) ** 2) ** 0.5
        frontage, ranks, _ = formation_layout.line_shape(placing, length)
        depth_toward = (sum(o[0] for o in origins) / len(origins),
                        sum(o[1] for o in origins) / len(origins))
        # `models=placing` matters: during a rule 01.02.03 return that is a
        # genuine SUBSET, and line_positions() used to read squad.models while
        # indexing origins by the subset - an IndexError, i.e. a right-drag in
        # the middle of a Reanimation placement crashed the game.
        #
        # No ladder here, unlike the Movement-phase sibling: Set Up has no
        # movement budget to strand anyone with, so the priority always
        # applies.
        targets = formation_layout.line_positions(
            squad, start_in, end_in, depth_toward=depth_toward, origins=origins,
            frontage=frontage, models=placing,
            priority=front_rank.drag_priority_tiers(squad, placing),
        )
        for model, target in zip(placing, targets):
            model.x_in, model.y_in = self.clamp_drag(model, target[0], target[1])
        return line_drag.measure(squad, targets, length, frontage, ranks, legal_frontages)

    def finish_line_drag(self):
        """End of the gesture: nothing. A Set Up commits nothing on release -
        confirm_setup() judges the placement, exactly as it does for every
        other Set Up drag. Its own method rather than the caller special-casing
        Set Up, so ending a gesture stays branch-free and the difference is
        stated where it belongs."""
        return None

    def begin_drag(self):
        """Snapshot the block's current shape so a drag translates it rigidly,
        and give a line drag the origins its ordering has to read.

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
        self._group_drag_origin = {m.id: (m.x_in, m.y_in) for m in self.placing_models}

    def apply_group_drag(self, dx_in, dy_in):
        """Move the whole block by (dx_in, dy_in), reduced to the largest
        fraction of that offset at which EVERY model still stands on legal
        ground.

        Bisection rather than per-model clamping, for the reason in
        begin_drag(): the block has to stay rigid.

        If the block did NOT start legal it follows the cursor freely instead.
        That is not a fallback for a broken state but a real case: turning the
        toggle on mid-placement over a still-stacked squad leaves every model
        overlapping, and bisecting from an illegal origin would find no legal
        fraction and freeze the unit in place. Same reasoning - and same
        wording - as clamp_drag()'s third case."""
        squad = self.setting_up_squad
        if squad is None or not self._group_drag_origin:
            return

        placing = self.placing_models

        def place(fraction):
            for model in placing:
                origin = self._group_drag_origin.get(model.id)
                if origin is None:
                    continue
                model.x_in = origin[0] + dx_in * fraction
                model.y_in = origin[1] + dy_in * fraction

        valid = self.placement_validator(squad)

        def legal():
            return all(
                self._on_board(model, model.x_in, model.y_in) and valid(model, model.x_in, model.y_in)
                for model in placing
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
            and token in self.placing_models
        )

    def position_valid(self, token, x_in, y_in, squad=None, ignore_model_overlap=False):
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
        point.

        `ignore_model_overlap=True` drops the other-models term as well, for
        a caller that only wants to DRAW the legal region (see
        PregameController.overlay_position_valid() - user: "ich sehe ja, wenn
        sich modelle ueberlappen"). Never for a caller that decides whether a
        placement may stand: overlap is still clamped and still checked at
        confirm time."""
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
        if not ignore_model_overlap:
            for other in self.all_tokens:
                # THE EXEMPTION IS THE PLACEMENT'S, NOT THE UNIT'S. A Set Up
                # places every model, so "my own squadmates do not block me" is
                # the same set either way. A PARTIAL placement is different:
                # the survivors are standing still and must be avoided like any
                # other model, or confirm_setup()'s check_model_overlap() -
                # which judges the whole squad - would reject at the end what
                # this let the player do all along. That is Fehlerklasse 8, and
                # it has cost a whole unit before.
                exempt = (self.placing_models
                          if self.is_partial and squad is self.setting_up_squad
                          else (squad.models if squad is not None else ()))
                if other is token or other in exempt:
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
        #
        # NOT for a model return: the unit was not set up, it was standing
        # there and got a model back (rule 01.02.03). Marking it would quietly
        # stop it embarking for the rest of the turn, which surfaces a phase
        # later as a transport that will not take passengers.
        if self._mark_set_up:
            squad.set_up_this_turn = True
        if self.game_log is not None:
            self.game_log.add(f"{squad.owner} set up {squad.name}.")
        self._reset_state()

    def cancel_setup(self):
        """Rule 03.02: "If you cannot set up all of the models in a unit,
        remove that unit from the battlefield and return it to its
        original position" - the whole unit goes back (via on_cancel), not
        just the models that were causing a problem.

        A PARTIAL placement is a different rule, not an exception to that one.
        Rule 01.02.03's model return puts one or two models back into a unit
        that is already on the battlefield; abandoning it takes back exactly
        those models and leaves the unit standing. `on_cancel` is unchanged and
        still receives the SQUAD - the caller knows which models it handed over
        and undoes its own half (model_return.set_up_model()'s four parts)."""
        if self.setting_up_squad is None:
            return
        squad = self.setting_up_squad
        for model in self.placing_models:
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
        # Back to "this placement owns the whole unit" and "confirming is a Set
        # Up". Leaving either behind would carry one rule's answer into the
        # next placement - and the next one is usually an ordinary Set Up,
        # where a stale subset means most of the unit cannot be dragged.
        self._placing_models = None
        self._mark_set_up = True
        self.placement_generation += 1
