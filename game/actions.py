"""Rule 16.01: PERFORMING ACTIONS - the generic framework, transcribed from
the core rulebook text the user supplied.

Until now this engine had no Actions concept at all (game/fall_back.py said so
in its own comment, and CLAUDE.md carried it as a named gap). The Secondary
Mission card "Cleanse" is the first thing that needs one, so this is the
framework plus exactly the hooks that card requires - not a speculative system.

THE PRINTED RULE
----------------
Each action states STARTS / UNITS / USE LIMIT / COMPLETES / EFFECT, plus any
additional restrictions. `ActionDefinition` below is those six fields and
nothing else, so a new action is one object rather than new machinery.

A unit is eligible to START an action unless one or more of these apply:
  - it is not on the battlefield
  - it is an AIRCRAFT/FORTIFICATION unit
  - it is battle-shocked
  - it has an OC characteristic of 0 or '-'
  - it is engaged (unless it is a TITANIC unit)
  - it made an Advance or Fall Back move this turn
  - it started another action this turn

If a unit starts an action, until the end of the turn it is not eligible to
shoot (excluding TITANIC units) and not eligible to declare a charge.

If a unit performing an action makes a move (excluding pile-in and
consolidation moves) or leaves the battlefield, it does NOT complete that
action. Otherwise, on completion the Effect triggers.

WHAT IS A DOCUMENTED NO-OP HERE
-------------------------------
AIRCRAFT and FORTIFICATION do not exist as keywords in this engine (the same
carve-out game/rapid_ingress.py already writes down), and neither does TITANIC.
All three tests are written out anyway, reading the profile flags if they ever
appear, so the transcription stays complete and the exceptions stay visible
rather than being quietly dropped.

WHY THE LOCKS LIVE ON THE SQUAD
-------------------------------
"Not eligible to shoot" and "not eligible to declare a charge" are read by
game/shooting.py's can_shoot() and game/charge.py's can_declare_charge() - the
two places that already answer those questions. A separate opinion in this
module would be the second-source drift this codebase keeps consolidating away,
so the controller sets a flag those two read, exactly as Fall Back and the
Disembark locks already do.
"""

from game.squad import ENGAGEMENT_RANGE_IN, edge_distance


class ActionDefinition:
    """One action's six printed fields.

    `units(squad, ctx)` is the UNITS line - the action's OWN restriction, on
    top of 16.01's generic eligibility (which start_eligibility() applies for
    every action alike).

    `completes(state, ctx)` is the COMPLETES line, asked at the moment the
    action would complete. `effect(state, ctx)` is what fires then.

    `use_limit(state_list, squad, ctx)` is the USE LIMIT line: given the
    actions already started this turn, may `squad` start another one? Default
    is unlimited.
    """

    def __init__(self, key, name, starts, units, completes, effect,
                 use_limit=None, target_options=None, completes_immediately=False):
        self.key = key
        self.name = name
        self.starts = starts              # a phase constant, for the caller to gate on
        self._units = units
        self._completes = completes
        self._effect = effect
        self._use_limit = use_limit
        # Some actions attach to a thing (Cleanse: an objective). Returns
        # [(label, target), ...] for the player to choose between.
        self._target_options = target_options
        # "COMPLETES: Immediately" (Plunder) rather than at some later instant
        # (Cleanse's end of turn). An immediate action is finished the moment
        # it is started, so 16.01's move-cancellation can no longer reach it -
        # but its two locks still apply, because those key on STARTING.
        self.completes_immediately = completes_immediately

    def units(self, squad, ctx):
        return bool(self._units(squad, ctx))

    def target_options(self, squad, ctx):
        return list(self._target_options(squad, ctx)) if self._target_options else []

    def use_limit_allows(self, started, squad, target, ctx):
        return True if self._use_limit is None else bool(self._use_limit(started, squad, target, ctx))

    def completes(self, state, ctx):
        return bool(self._completes(state, ctx))

    def effect(self, state, ctx):
        if self._effect is not None:
            self._effect(state, ctx)


class ActionState:
    """One unit performing one action this turn."""

    def __init__(self, definition, squad, target=None):
        self.definition = definition
        self.squad = squad
        self.target = target
        self.broken = False  # set when a move or leaving the battlefield cancels it
        # Already finished - only ever true for a "COMPLETES: Immediately"
        # action, which is done before anything can interfere with it.
        self.completed = False

    @property
    def key(self):
        return self.definition.key


def _flag(profile, name):
    return bool(getattr(profile, name, False))


def unit_is_on_battlefield(squad, tokens):
    live = {id(t.squad) for t in tokens if t.squad is not None and t.squad.models}
    return id(squad) in live


def start_eligibility(squad, tokens, movement_controller=None, started_this_turn=()):
    """Rule 16.01's generic START eligibility, in the printed order.

    Returns (True, None) or (False, reason) - the reason string exists so a
    refused offer can say WHY rather than silently not appearing, which is how
    an eligibility bug hides."""
    if squad is None or not squad.models:
        return False, "not on the battlefield"
    if not unit_is_on_battlefield(squad, tokens):
        return False, "not on the battlefield"
    profile = squad.models[0].profile
    # AIRCRAFT/FORTIFICATION: no datasheet here carries either keyword, so this
    # is a documented no-op that still reads the flags if they ever land.
    if _flag(profile, "aircraft") or _flag(profile, "fortification"):
        return False, "AIRCRAFT/FORTIFICATION units cannot perform actions"
    if squad.battle_shocked:
        return False, "battle-shocked"
    if profile.oc <= 0:
        return False, "OC 0"
    # TITANIC is the printed exception, and also not a keyword here.
    if not _flag(profile, "titanic") and _is_engaged(squad, tokens):
        return False, "engaged"
    if squad.fell_back_this_turn:
        return False, "Fell Back this turn"
    if movement_controller is not None and squad in movement_controller.advanced_squad_ids:
        return False, "Advanced this turn"
    if any(state.squad is squad for state in started_this_turn):
        return False, "already started an action this turn"
    return True, None


def _is_engaged(squad, tokens):
    """Rule 03.04, measured here rather than through Squad.is_engaged() so it
    can run off the same token list the rest of this module uses."""
    enemies = [t for t in tokens
               if t.squad is not None and t.squad.owner != squad.owner and not t.is_dead()]
    return any(edge_distance(m, e) <= ENGAGEMENT_RANGE_IN
               for m in squad.models for e in enemies)


class ActionController:
    """Tracks which units are performing which actions this turn.

    Deliberately one controller for ALL actions rather than one per action:
    16.01's eligibility, its two locks and its move-cancellation are shared by
    every action there will ever be, and "started another action this turn"
    is a question across all of them at once.
    """

    def __init__(self, tokens_source=None, movement_controller=None, game_log=None):
        self._tokens_source = tokens_source or (lambda: [])
        self.movement_controller = movement_controller
        self.game_log = game_log
        self.states = []              # ActionState, this turn only
        self.completed_this_turn = []  # [(ActionState, ...)] resolved at the turn's end

    # ------------------------------------------------------------ queries

    def _tokens(self):
        return list(self._tokens_source())

    def can_start(self, definition, squad, ctx=None):
        ok, reason = start_eligibility(squad, self._tokens(), self.movement_controller, self.states)
        if not ok:
            return False, reason
        if not definition.units(squad, ctx):
            return False, f"does not meet {definition.name}'s UNITS line"
        return True, None

    def state_for(self, squad):
        return next((s for s in self.states if s.squad is squad and not s.broken), None)

    def is_performing(self, squad):
        return self.state_for(squad) is not None

    def blocks_shooting(self, squad):
        """"It is not eligible to shoot (excluding TITANIC units)" - and the
        lock survives the action being BROKEN by a move: the unit still
        started one this turn, which is what the rule keys on."""
        state = next((s for s in self.states if s.squad is squad), None)
        if state is None:
            return False
        # Advanced Acquisition Cadre's Microdrone Support: "that action does not
        # prevent your unit from being eligible to shoot". It lifts THIS half
        # only - blocks_charge() below is untouched, because the printed text
        # says nothing about charging.
        from game import aac_microdrone_support
        if aac_microdrone_support.is_active(squad):
            return False
        return not _flag(squad.models[0].profile, "titanic") if squad.models else True

    def blocks_charge(self, squad):
        """"It is not eligible to declare a charge" - no TITANIC carve-out on
        this half of the rule."""
        return any(s.squad is squad for s in self.states)

    # ------------------------------------------------------------ lifecycle

    def start(self, definition, squad, target=None, ctx=None):
        ok, reason = self.can_start(definition, squad, ctx)
        if not ok:
            self._log(f"{squad.name} cannot start {definition.name}: {reason}.", file_only=True)
            return None
        if not definition.use_limit_allows(self.states, squad, target, ctx):
            self._log(f"{squad.name} cannot start {definition.name}: use limit.", file_only=True)
            return None
        state = ActionState(definition, squad, target)
        self.states.append(state)
        where = f" on {getattr(target, 'name', target)}" if target is not None else ""
        self._log(f"{squad.name} starts the {definition.name} action{where}.")
        if definition.completes_immediately:
            # "COMPLETES: Immediately" - resolved here, not at the turn's end.
            # Its EFFECT fires now and nothing later can take it back; the
            # two locks stay on the unit for the rest of the turn regardless.
            state.completed = True
            definition.effect(state, ctx)
            self._log(f"{squad.name} completes the {definition.name} action{where}.")
        return state

    def notify_move(self, squad, move_kind=None):
        """"If a unit performing an action makes a move (excluding pile-in and
        consolidation moves) ... that unit does not complete that action."

        Called from every move-confirm path. The two named exceptions are
        passed by name rather than inferred, so a new move type has to say
        which it is instead of silently counting as neither."""
        if move_kind in ("pile_in", "consolidate"):
            return
        state = self.state_for(squad)
        if state is None:
            return
        state.broken = True
        self._log(f"{squad.name} moved, so its {state.definition.name} action will not complete.")

    def resolve_end_of_turn(self, player, ctx=None):
        """Complete every unbroken action belonging to `player` whose COMPLETES
        line is satisfied, firing its EFFECT. Returns the completed states.

        Cleanse is the only action so far and completes at the end of the turn;
        an action that completes elsewhere would be resolved from its own hook
        and simply not be in this list."""
        completed = []
        for state in self.states:
            if state.squad.owner != player:
                continue
            if state.completed:
                # Already resolved when it was started ("COMPLETES:
                # Immediately") - reported here so every consumer reads one
                # list, whatever the action's own timing was.
                completed.append(state)
                continue
            if state.broken:
                continue
            if not state.squad.models or not unit_is_on_battlefield(state.squad, self._tokens()):
                # "or leaves the battlefield" - the other half of the
                # cancellation clause, checked here because a unit can be
                # destroyed at any point after starting.
                self._log(f"{state.squad.name} left the battlefield, so its "
                          f"{state.definition.name} action did not complete.")
                continue
            if not state.definition.completes(state, ctx):
                self._log(f"{state.squad.name} did not complete the "
                          f"{state.definition.name} action.")
                continue
            state.definition.effect(state, ctx)
            completed.append(state)
            where = f" on {getattr(state.target, 'name', state.target)}" if state.target else ""
            self._log(f"{state.squad.name} completes the {state.definition.name} action{where}.")
        self.completed_this_turn = completed
        return completed

    def reset_for_turn(self):
        """16.01's bookkeeping is per TURN: "it started another action this
        turn", and both locks last "until the end of the turn"."""
        self.states = []

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)
