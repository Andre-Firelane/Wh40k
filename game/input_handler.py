import pygame

from game import line_drag, movement, setup

# QoL (auto-move-on-drag): how far the cursor has to travel before a
# left-press on one of your own models counts as "this is a drag, start the
# Normal move" instead of "this was just a click to select it". In screen
# pixels, deliberately not inches, so the gesture feels identical at every
# zoom level.
DRAG_START_THRESHOLD_PX = 4


class InputManager:
    def __init__(self, board_offset=(0, 0), camera=None):
        self.dragging_token = None
        self.drag_offset = (0.0, 0.0)
        # QoL (auto-move-on-drag): the model a left-press landed on while NOT
        # already in a move, held here until the cursor passes
        # DRAG_START_THRESHOLD_PX. main.py reads this to know that the drag
        # following this press is spoken for and must not also begin a camera
        # pan - the same collision dragging_token already guards against, one
        # gesture earlier (we only learn it's a drag at the first motion).
        self.pending_move_token = None
        self._pending_move_down_px = (0, 0)
        # Deselect-on-click: where a left-press on EMPTY ground landed, or None
        # if no such press is open. The press itself no longer deselects,
        # because the very same press also starts a camera pan (main.py) - so
        # every pan used to throw the selection away, which is the whole reason
        # this exists. The release decides: cursor still within
        # DRAG_START_THRESHOLD_PX means it really was a click into the void, so
        # let go of the unit; anything further means it was a pan and the
        # selection survives. Same threshold, same shape and the same reasoning
        # as pending_move_token above - one press, two possible meanings,
        # settled by whether the cursor travelled.
        self._void_press_px = None
        self.dragging_group = False       # QoL group-move: dragging_token's whole squad rides along, see movement.py's apply_group_drag()
        # The Set Up equivalent (game/setup.py's apply_group_drag). Its own flag
        # rather than reusing dragging_group: that one commits through
        # MovementController's per-model distance budget, which does not exist
        # during a Set Up, and a Set Up commits nothing on release at all.
        self.dragging_setup_group = False
        self.group_drag_start_in = (0.0, 0.0)
        self.hovered_token = None
        self.board_offset = board_offset
        # Später-Liste (Kamera-Scrolling/Viewport): optional, remaps a
        # screen-local pixel position through the current zoom/pan before
        # it's converted to inches - see game/camera.py. None means "no
        # camera", i.e. the identity mapping this class always used before
        # zoom/pan existed.
        self.camera = camera

        # Total-War style line formation, on the RIGHT button. `start_in` is
        # the single authority for "a drag is live" - no second boolean to fall
        # out of sync with it.
        self.line_drag_start_in = None
        self.line_drag_end_in = None
        # The controller and squad captured AT THE PRESS, never re-read on
        # release: a release can arrive after the state that started the drag
        # is gone (a move confirmed, a placement finished), and re-deciding
        # then would commit the gesture against whatever happens to be live -
        # catch the subject of the window once.
        self.line_drag_controller = None
        self.line_drag_squad = None
        # Swept once on the press: which frontages keep the unit inside rule
        # 09.02's spread. Invariant under the drag, because sliding and
        # rotating a rigid block changes no pairwise distance.
        self.line_drag_legal = ()
        self.line_drag_info = None

        self.mouse_pos_in = (0.0, 0.0)
        self.measuring = False
        self.measure_origin_in = None
        self.measure_origin_token = None

    def _local_pos(self, event_pos):
        local = (event_pos[0] - self.board_offset[0], event_pos[1] - self.board_offset[1])
        if self.camera is not None:
            return self.camera.to_native_px(local)
        return local

    def _find_token_at(self, tokens, x_in, y_in):
        for token in reversed(tokens):
            if token.contains_point(x_in, y_in):
                return token
        return None

    def token_at_event(self, tokens, board, event_pos):
        x_in, y_in = board.to_in(*self._local_pos(event_pos))
        return self._find_token_at(tokens, x_in, y_in)

    def track_pointer(self, event_pos, tokens, board):
        """Where the cursor is (in inches) and which model it is over.

        Split out of handle_event() because main.py's event chain is a long
        if/elif over CONTROLLER STATE and handle_event() sits at the very END
        of it: whenever anything was pending (a Fire Overwatch offer, a damage
        allocation, a decision prompt) motion events matched an earlier branch
        and never reached it, so these two fields silently froze - and the ALT
        ruler, which renderer.draw_measure_tool() draws from exactly these two,
        froze with them. That is the user report "ich kann oft keine
        entfernungen messen. zb bei overwatch".

        main.py now calls this for every MOUSEMOTION BEFORE that chain runs, so
        pointer tracking is never gated on game state. handle_event() still
        calls it as well, so this class stays self-sufficient for anyone
        driving it directly (test_block_placement.py does); it only reads and
        assigns, so running twice for one event means the same thing as once.
        """
        x_in, y_in = board.to_in(*self._local_pos(event_pos))
        self.mouse_pos_in = (x_in, y_in)
        self.hovered_token = self._find_token_at(tokens, x_in, y_in)
        return x_in, y_in

    @property
    def line_drag_active(self):
        return self.line_drag_start_in is not None

    def begin_line_drag(self, event_pos, tokens, board, movement_controller,
                        setup_controller=None, blocked=False,
                        start_placement=None):
        """Start a line-formation drag at `event_pos`. True if one opened.

        The anchor comes from the PRESS EVENT'S OWN position, not from
        mouse_pos_in: that field is only as fresh as the last MOUSEMOTION, and
        the press point is the load-bearing end of the line.

        `blocked` is the caller's answer to "does a modal own the board's
        clicks right now". Gating the START is legitimate where gating the
        VIEW would not be: this gesture MUTATES model positions, so it is an
        action. What must never be gated is the continuation or the release -
        that would strand a half-written formation with no route to a commit.

        `start_placement(x_in, y_in) -> bool`, if given, sets a CARRIED unit
        down at the press point - a card picked out of the pre-game pool
        (03.01) or out of the Reserves strip (20.04). It is what makes the
        gesture usable where it is worth the most (user: "wenn ich in der
        aufstellungsphase oder bei reserven meine einheiten platzieren will,
        dann muss ich sie erstmal auf der map platzieren und kann dann im 2ten
        schritt erst die drag-formation benutzen ... ohne zwischen step?"):
        without it a unit had to be dropped, judged and only then re-formed,
        i.e. the formation was drawn on the second gesture rather than the
        first. A CALLBACK rather than a controller argument because "which
        unit is carried, and where does it go back to" is main.py's question -
        the pre-game sequencer and the Ingress rule each own half of the
        answer, and neither belongs in an input handler.

        Four-way, mirroring handle_event()'s own button-1 branch and in the
        same order, because both controllers can be live at once (a Rapid
        Ingress placement during the Movement phase) and one gesture must not
        get two answers depending on where it is read."""
        if blocked or self.line_drag_active or self.dragging_token is not None:
            return False

        mx_in, my_in = board.to_in(*self._local_pos(event_pos))
        clicked = self._find_token_at(tokens, mx_in, my_in)

        if setup_controller is not None and setup_controller.state == setup.PLACING:
            controller = setup_controller
            squad = setup_controller.setting_up_squad
            setup_controller.begin_drag()
        elif (setup_controller is not None and start_placement is not None
                and start_placement(mx_in, my_in)):
            # A carried unit outranks a right-press on a unit already standing
            # on the board, and deliberately: the pre-game's left click makes
            # exactly the same call (main.py intercepts the board click while
            # awaiting_drop), so both buttons agree on what carrying a unit
            # means. Tried AFTER the branch above, never before it - a
            # placement already open must not be interrupted by a second one.
            controller = setup_controller
            squad = setup_controller.setting_up_squad
            setup_controller.begin_drag()
        else:
            # A press on one of your OWN models picks that unit, so a line can
            # be drawn without selecting first. select() is called only with a
            # real token, never with None - the None case is the one that
            # CLEARS, and a right-press that misses must not be destructive.
            if (clicked is not None and clicked.squad is not None
                    and movement_controller.state != movement.MOVING
                    and movement_controller.can_select(clicked.squad)):
                movement_controller.select(clicked)
            squad = movement_controller.selected_squad
            if squad is None:
                return False
            if movement_controller.state != movement.MOVING:
                # Same promotion the left button's auto-move-on-drag already
                # does. Gated on can_make_move() (09.05), so an engaged unit,
                # an already-moved one, or any phase other than Movement is
                # simply a no-op - Fall Back (09.07) is deliberately excluded,
                # being a mode choice with its own panel branch rather than
                # something a mouse gesture should decide.
                if not movement_controller.can_make_move(squad):
                    return False
                movement_controller.start_move()
                if movement_controller.state != movement.MOVING:
                    return False
            controller = movement_controller

        if squad is None or not squad.models:
            return False

        self.line_drag_start_in = (mx_in, my_in)
        self.line_drag_end_in = (mx_in, my_in)
        self.line_drag_controller = controller
        self.line_drag_squad = squad
        self.line_drag_legal = line_drag.legal_frontage_window(
            squad, (mx_in, my_in), (mx_in, my_in),
            origins=self._line_origins(controller, squad),
        )
        self.line_drag_info = None
        return True

    def _line_origins(self, controller, squad):
        """Where each model is walking FROM, as the controller sees it - the
        Movement phase's committed waypoints, or the Set Up gesture's own
        snapshot. Never the live positions during a drag: those hold the
        previous frame's preview."""
        waypoints = getattr(controller, "last_waypoint", None)
        if waypoints:
            found = [waypoints.get(m.id) for m in squad.models]
            if all(p is not None for p in found):
                return found
        snapshot = getattr(controller, "_group_drag_origin", None)
        if snapshot:
            found = [snapshot.get(m.id) for m in squad.models]
            if all(p is not None for p in found):
                return found
        return [(m.x_in, m.y_in) for m in squad.models]

    def update_line_drag(self, right_held):
        """Re-lay the formation from the current cursor, once a frame.

        Polled rather than event-driven, and for the reason the ALT ruler is:
        a poll has no branch to be swallowed by, and a lost MOUSEBUTTONUP
        (ALT+TAB, focus loss) cannot strand a gesture that is actively
        rewriting model positions. That failure mode is strictly worse here
        than it was for the ruler - it stranded a drawing, this would strand a
        mutation."""
        if not self.line_drag_active:
            return
        if not right_held:
            self.end_line_drag()
            return
        self.line_drag_end_in = self.mouse_pos_in
        controller = self.line_drag_controller
        squad = self.line_drag_squad
        if controller is None or squad is None:
            self.end_line_drag()
            return
        # Branch-free: both controllers carry apply_line_drag/finish_line_drag
        # under the same names, exactly as they already both carry
        # apply_group_drag. What differs is entirely inside them - one charges
        # a per-model movement budget, the other has none.
        info = controller.apply_line_drag(
            self.line_drag_start_in, self.line_drag_end_in,
            legal_frontages=self.line_drag_legal)
        if info is None:
            # The controller left the state that started this - a move
            # confirmed, a placement finished. Nothing to keep laying out.
            self.end_line_drag()
            return
        self.line_drag_info = info

    def end_line_drag(self):
        """Finish the gesture on the controller captured at the PRESS.

        Idempotent, because two things can end it: the real MOUSEBUTTONUP and
        the poll's held-button failsafe. Without that, a release and the poll
        in the same frame would commit twice."""
        controller = self.line_drag_controller
        self.line_drag_start_in = None
        self.line_drag_end_in = None
        self.line_drag_controller = None
        self.line_drag_squad = None
        self.line_drag_legal = ()
        self.line_drag_info = None
        if controller is not None:
            controller.finish_line_drag()

    def update_measuring(self, alt_held):
        """Drive the ALT ruler from the modifier's CURRENT state, once a frame.

        This used to be a KEYDOWN/KEYUP pair inside main.py's state-gated event
        chain, which is the other half of why ALT "oft" did nothing: the key
        press was swallowed by whichever branch was active, i.e. at exactly the
        moments a distance matters most. A poll cannot be swallowed by anyone.

        It also closes the mirror-image bug the event pair had: ALT+TAB sends
        the KEYUP to another window, so measuring stayed stuck on until the key
        was tapped again. Here the ruler simply follows whether ALT is down.

        Takes the flag rather than reading pygame.key.get_mods() itself so the
        transition (and only the transition - start_measuring() snapshots an
        origin, so it must not re-run every frame) is testable without real
        keyboard state.
        """
        if alt_held and not self.measuring:
            self.start_measuring()
        elif not alt_held and self.measuring:
            self.stop_measuring()

    def start_measuring(self):
        self.measuring = True
        self.measure_origin_token = self.hovered_token
        if self.measure_origin_token is not None:
            # Use the model's true center, not wherever inside its base the cursor happened to be.
            self.measure_origin_in = (self.measure_origin_token.x_in, self.measure_origin_token.y_in)
        else:
            self.measure_origin_in = self.mouse_pos_in

    def stop_measuring(self):
        self.measuring = False
        self.measure_origin_in = None
        self.measure_origin_token = None

    def handle_event(self, event, tokens, board, movement_controller, setup_controller=None):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.line_drag_active:
                # A line drag is already writing this squad's positions. Letting
                # a left-press also grab a model would give two writers the same
                # tokens - the same collision the camera-pan suppression in
                # main.py guards against one gesture over.
                return
            mx_in, my_in = board.to_in(*self._local_pos(event.pos))
            clicked_token = self._find_token_at(tokens, mx_in, my_in)

            if setup_controller is not None and setup_controller.state == setup.PLACING:
                if clicked_token is not None and setup_controller.is_placeable(clicked_token):
                    self.dragging_token = clicked_token
                    self.drag_offset = (clicked_token.x_in - mx_in, clicked_token.y_in - my_in)
                    # QoL: with "Place as Block" on, a drag moves the whole unit
                    # rigidly instead of one model. Holding SHIFT overrides it
                    # for this one drag, so a single model can still be nudged
                    # without turning the toggle off ("danach noch bewegen
                    # kann, wenn ich will"). Kept in its own flag rather than
                    # reusing dragging_group: that one routes to
                    # MovementController, whose group drag works off a Movement
                    # move's per-model distance budget, which does not exist
                    # during a Set Up.
                    solo = pygame.key.get_mods() & pygame.KMOD_SHIFT
                    self.dragging_setup_group = setup_controller.block_placement_enabled and not solo
                    if self.dragging_setup_group:
                        setup_controller.begin_drag()
                        self.group_drag_start_in = (mx_in, my_in)
            elif movement_controller.state == movement.MOVING:
                if clicked_token is not None and movement_controller.is_movable(clicked_token):
                    self.dragging_token = clicked_token
                    self.drag_offset = (clicked_token.x_in - mx_in, clicked_token.y_in - my_in)
                    # LOS is always checked from whichever model was just clicked.
                    movement_controller.selected_model = clicked_token
                    self.dragging_group = movement_controller.group_move_enabled
                    self.group_drag_start_in = (mx_in, my_in)
            else:
                if clicked_token is None:
                    # Deliberately NOT select(None) here. See _void_press_px:
                    # this same press begins a camera pan, so deselecting now
                    # means every pan loses the selection. Deferred to the
                    # release, which can tell a click from a pan.
                    self._void_press_px = event.pos
                else:
                    movement_controller.select(clicked_token)
                # QoL (User-Wunsch: "wenn ich einheiten geklickt halte und
                # anfangen will zu dragen, dann springt die aktion automatisch
                # auf move"): remember the model, but don't start the move yet
                # - a plain click must still just select. The MOUSEMOTION
                # branch promotes this to a real move once the cursor actually
                # travels. Gated on can_make_move() (rule 09.05), so it only
                # ever auto-starts the one move type a bare drag is
                # unambiguous about: an engaged squad (Fall Back, 09.07), an
                # already-moved squad, or any phase other than Movement leaves
                # this None and the drag stays a camera pan as before.
                # selected_squad is compared identity-wise because select()
                # silently does nothing for a squad that isn't yours to pick
                # (can_select()) - without this, clicking an enemy model while
                # one of your own squads is selected would arm the gesture for
                # the WRONG squad, since can_make_move() itself has no
                # ownership check.
                if (
                    clicked_token is not None
                    and movement_controller.selected_squad is clicked_token.squad
                    and movement_controller.can_make_move(clicked_token.squad)
                ):
                    self.pending_move_token = clicked_token
                    self._pending_move_down_px = event.pos

        elif event.type == pygame.MOUSEMOTION:
            mx_in, my_in = self.track_pointer(event.pos, tokens, board)

            if self.pending_move_token is not None and self.dragging_token is None:
                dx_px = event.pos[0] - self._pending_move_down_px[0]
                dy_px = event.pos[1] - self._pending_move_down_px[1]
                if dx_px * dx_px + dy_px * dy_px >= DRAG_START_THRESHOLD_PX ** 2:
                    token = self.pending_move_token
                    self.pending_move_token = None
                    movement_controller.start_move()
                    # is_movable() confirms start_move() actually took (it's a
                    # no-op if can_make_move() flipped false in between) before
                    # this turns into a live drag - identical bookkeeping to
                    # the MOVING branch above, except the offsets are taken
                    # from HERE rather than the press, so the model doesn't
                    # jump by the few pixels the threshold cost.
                    if movement_controller.is_movable(token):
                        self.dragging_token = token
                        self.drag_offset = (token.x_in - mx_in, token.y_in - my_in)
                        movement_controller.selected_model = token
                        self.dragging_group = movement_controller.group_move_enabled
                        self.group_drag_start_in = (mx_in, my_in)

            if self.dragging_token:
                if self.dragging_setup_group and setup_controller is not None:
                    dx_in = mx_in - self.group_drag_start_in[0]
                    dy_in = my_in - self.group_drag_start_in[1]
                    setup_controller.apply_group_drag(dx_in, dy_in)
                elif self.dragging_group:
                    dx_in = mx_in - self.group_drag_start_in[0]
                    dy_in = my_in - self.group_drag_start_in[1]
                    movement_controller.apply_group_drag(dx_in, dy_in)
                else:
                    target_x = mx_in + self.drag_offset[0]
                    target_y = my_in + self.drag_offset[1]
                    if setup_controller is not None and setup_controller.is_placeable(self.dragging_token):
                        # clamp_drag(), not clamp_position(): a human drag is
                        # held inside the legal (green) area so a model can't
                        # be let go somewhere it isn't allowed to stand.
                        target_x, target_y = setup_controller.clamp_drag(
                            self.dragging_token, target_x, target_y
                        )
                    else:
                        target_x, target_y = movement_controller.clamp_move(
                            self.dragging_token, target_x, target_y
                        )
                    self.dragging_token.x_in = target_x
                    self.dragging_token.y_in = target_y

            # Re-read after the drag above, not before it: the token under the
            # cursor is usually the one that was just moved there. track_pointer()
            # already set this from the same coordinates - this is the settled
            # answer, and the reason that call's cheapness is worth stating.
            self.hovered_token = self._find_token_at(tokens, mx_in, my_in)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            # A press that never travelled far enough stays what it always
            # was: a plain selection click.
            self.pending_move_token = None
            # ...and the mirror of that for a press on empty ground: a click
            # lets go of the unit, a pan does not. Read BEFORE the drag
            # bookkeeping below, and cleared unconditionally, so a press that
            # somehow never reaches its own release cannot arm a later one.
            void_press = self._void_press_px
            self._void_press_px = None
            if void_press is not None and self.dragging_token is None:
                dx = event.pos[0] - void_press[0]
                dy = event.pos[1] - void_press[1]
                if dx * dx + dy * dy < DRAG_START_THRESHOLD_PX ** 2:
                    movement_controller.select(None)
            if self.dragging_token is not None:
                if self.dragging_setup_group:
                    pass  # a Set Up commits nothing on release - confirm_setup() judges it
                elif self.dragging_group:
                    movement_controller.commit_group_drag()
                elif not (setup_controller is not None and setup_controller.is_placeable(self.dragging_token)):
                    movement_controller.try_commit_segment(self.dragging_token)
            self.dragging_token = None
            self.dragging_group = False
            self.dragging_setup_group = False
