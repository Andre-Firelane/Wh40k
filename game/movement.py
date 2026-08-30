from game import config, geometry
from game import scuttling_walker
from game.coherency import coherency_report
from game import whirling_death
from game.coldstar import effective_movement_in
from game import guardian_time_to_strike
from game import montka_aggressive_mobility, montka_pulse_onslaught
from game.dice import ADVANCE_ROLL
from game.roll_bonus import advance_and_charge_bonus
from game.squad import model_engaged_with, model_terrain_violation, model_overlaps_any
from game.terrain import DENSE, may_cross_walls
from game.turn import PHASE_MOVEMENT, PHASE_FIGHT

IDLE = "idle"
SELECTED = "selected"
MOVING = "moving"


def advance_total(squad, values, all_tokens=None):
    """Rule 09.06's Advance roll turned into extra inches: the D6 plus every
    bonus to Advance rolls this unit currently has - see game/roll_bonus.py,
    which folds War Horde's 'Ere We Go (+2, a unit flag) and the Avatar of
    Khaine's The Bloody-Handed (+1, a 6" aura, which is why `all_tokens` is
    needed at all).

    One helper because TWO places have to agree on it: start_run() applies the
    result the moment the die is rolled, and on_dice_acknowledged() re-derives
    it to reconcile a Command Re-roll (15.02) against what was applied. Both
    are MovementController methods, so both pass self.all_tokens; the argument
    is optional so a caller without a board still gets the flag-based half."""
    # Mont'ka's Pulse Onslaught leaves a unit `shaken`: -2 on Advance rolls
    # made for it. Folded here rather than at start_run() so
    # on_dice_acknowledged()'s Command Re-roll reconciliation sees the same
    # number - the whole reason this helper exists. Floored at 0: a negative
    # Advance would move the unit backwards.
    total = (sum(values) + advance_and_charge_bonus(squad, all_tokens)
             - montka_pulse_onslaught.roll_penalty_for(squad))
    return max(0, total)

# Pull back slightly from an obstacle boundary when blocked, so the model doesn't
# land exactly on the edge (which would falsely re-block any further slide along it).
OBSTACLE_PULLBACK_IN = 0.01

TAKE_TO_THE_SKIES_DISTANCE_PENALTY_IN = 2.0  # rule 21.03
RETRO_THRUSTER_MOVE_IN = 6.0  # The Twin Lance's Retro-thrusters: "a Normal move of up to 6\"" - the ability names the distance, so it is NOT the unit's own M characteristic (which is 10" and would be wrong in its favour); see start_retro_thruster_move()


def take_to_the_skies_pays(squad):
    """Would declaring 21.03 leave this unit BETTER off? Eligibility is
    can_take_to_the_skies() (a MovementController method, because it is a
    question about a move in progress); this is the separate question of
    whether the declaration is worth making, and it is a pure function of who
    in the squad flies.

    WHERE IT CAME FROM. This started as a workaround for the two halves of
    21.03 being applied to different sets of models: take_to_the_skies()
    charged the penalty to the whole squad while clamp_move() granted the
    bypass only to FLY models. Reported as "die necron krieger sind hinten
    nicht rausgekommen. sie hatten enorme schwierigkeiten nach vorne zu
    laufen"; measured on the logged unit, 21 of 21 models paid and 1 of 21
    flew, cutting twenty Necron Warriors from a 5" move to a 3" one every
    Movement phase. THAT DEFECT IS NOW FIXED AT SOURCE - the user ruled "es
    fliegen nur fly modelle", so take_to_the_skies() charges only the flyers -
    and this function is no longer compensating for it. What is left here is
    the genuine question it was always named for.

    HOVER (24.17) removes the penalty outright, and take_to_the_skies() reads
    that off ANY model in the squad, so for those units the declaration is
    free and there is nothing to weigh - take it whenever a model can.

    AN ALL-INFANTRY UNIT NEVER DECLARES IT, whatever it has for keywords
    otherwise. User ruling: "einheiten, die ausschliesslich aus infanterie
    modellen bestehen sollten niemals take to the skies benutzen, weil sie ja
    eh durch waende laufen koennen." Rule 13.06 already lets INFANTRY (and
    BEASTS/SWARM/MOBILE) cross Dense terrain for free, so the terrain half of
    21.03 - the half worth having - buys such a unit nothing it did not already
    have. What is left is the pass-through-models half, and that is not worth
    2" off every model. This is a "niemals", so it is checked BEFORE the HOVER
    branch below rather than after it.

    It is deliberately the INFANTRY keyword and not can_move_through_dense_
    terrain(), even though 13.06 covers four keywords: the ruling names
    infantry, and BEASTS in particular are a different case (the Canoptek
    Wraiths cross walls by 13.06 AND fly, and nobody asked to ground them).
    When a BEASTS/SWARM unit that flies is next reported, that is the moment to
    widen this - not now, guessing.

    NOT a judgement call handed to the agent, and deliberately so: this is
    arithmetic over profile flags with no board state in it, the same reason
    the policy it replaces was deterministic."""
    flyers = [m for m in squad.models if m.profile.fly]
    if not flyers:
        return False
    if all(m.profile.infantry for m in squad.models):
        return False  # rule 13.06 already gives them the terrain half for free
    if any(m.profile.hover for m in squad.models):
        return True  # rule 24.17: no distance penalty, so nothing to trade off
    # A partial declaration only handicaps the flyers relative to the squad
    # they have to stay in coherency with (09.02), and the walkers still cannot
    # cross what they could not cross before.
    return len(flyers) == len(squad.models)


class MovementController:
    def __init__(
        self, obstacles=None, game_log=None, player_name="Player 1", dice_manager=None,
        turn_tracker=None, all_tokens=None, board_width_in=None, board_height_in=None,
    ):
        self.selected_squad = None
        self.selected_model = None  # the exact model clicked; anchor for the LOS check
        self.state = IDLE
        self.move_start = {}       # token.id -> (x_in, y_in) at the very start of the whole move
        self.last_move_start = {}  # the same map for the move that JUST finished - survives _clear_move_state() so on_move_finished listeners can still read it (see game/wraith_form.py)
        self.last_waypoint = {}    # token.id -> (x_in, y_in), the last committed point
        self.remaining_range = {}  # token.id -> inches still available to move
        self.previous_waypoint = {}       # token.id -> waypoint before the last committed segment (1-step undo)
        self.previous_remaining_range = {}  # token.id -> remaining_range before the last committed segment
        self.errors = []
        self.obstacles = obstacles if obstacles is not None else []
        self.game_log = game_log
        self.player_name = player_name
        self.dice_manager = dice_manager
        self.turn_tracker = turn_tracker
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.board_width_in = board_width_in
        self.board_height_in = board_height_in
        self.run_used = False
        self.moved_squad_ids = set()      # squads already selected to move this Movement phase
        self.stationary_squad_ids = set()  # squads that chose Remain Stationary this turn (rule 10.07)
        self.advanced_squad_ids = set()    # squads that made an Advance move this turn (rule 10.04/10.05)
        self.advance_bonus_by_squad = {}   # squad -> D6 bonus already rolled this phase (rule 09.06: the Advance
                                            # roll is final for the phase - cancelling the move must not let it be
                                            # re-rolled, see start_move()/start_run())
        self._pending_advance = None       # (squad, bonus_applied) while an Advance roll awaits acknowledgement -
                                            # a Command Re-roll (15.02) can still change the die under us, so the
                                            # applied bonus is reconciled in on_dice_acknowledged()
        self.moved_distance_this_turn = {}  # squad -> farthest any single model in it moved this turn (rule 24.16's [HEAVY])
        self.move_mode = None              # None | "charge" | "pile_in" | "consolidate" - which end-of-move rule confirm_move() applies
        # Fired once a Fall Back move has been fully confirmed, with the squad
        # that fell back. The Aeldari Agile Manoeuvre Opportunity Seized
        # triggers on "an enemy unit ENDS a Fall Back move" - so it has to be
        # after all of confirm_move()'s bookkeeping, not at the moment the mode
        # is set: the handler raises a break point for the opponent, and that
        # opponent's own move must not start while this one is still settling.
        self.on_fall_back_finished = None
        self._fell_back_pending = None
        # Seer Council's Isha's Fury triggers on "an enemy unit ENDS a Normal,
        # Advance or Fall Back move" - broader than the hook above, which is
        # Fall Back only. Same placement and the same reason: fired after all of
        # confirm_move()'s bookkeeping, because the handler opens a break point
        # for the opponent and that must not land mid-settle. Receives
        # (squad, move_mode) so a consumer can tell the three apart.
        # Listeners for "directly after a unit ends a Normal, Advance or Fall
        # Back move" - a LIST since Rangers' Path of the Outcast joined Seer
        # Council's Isha's Fury on it, the same generalisation
        # on_squad_finished_shooting and target_reactions already got.
        self.on_move_finished = []
        # Fired when a SCOUT move (24.32) ends, by confirm OR cancel, with the
        # squad. Its own hook rather than a place in on_move_finished above,
        # because that list is deliberately restricted to Normal/Advance/Fall
        # Back moves - Wraith Form and Isha's Fury read it and must not see a
        # pre-game scout move. game/scouts.py needs the opposite: it has to
        # know the human is finished with the unit so the SCOUTS queue can move
        # on, and "cancelled" counts just as much as "confirmed".
        self.on_scout_move_finished = None
        self._move_finished_pending = None
        self.charge_targets = []           # squads the current charge move must end engaged with (rule 11.04)
        self.pile_in_targets = []          # squads the current pile-in move must still be engaged with (rule 12.03)
        self.consolidate_targets = []      # squads the current consolidation move must end engaged with (rule 12.08)
        self.consolidate_mode = None       # "ongoing" | "engaging" while move_mode == "consolidate"
        self.flying_this_move = False      # rule 21.03: "Take to the Skies" declared for the current move
        self.desperate_escape_this_move = False  # rule 09.07: Desperate Escape mode of a Fall Back move - models may be moved across other models (not terrain) during this drag
        self.surge_target = None           # rule 21.02: the enemy squad a surge move must end unengaged-with-others-except
        self.on_remain_stationary = None   # optional callable(squad) - e.g. Strike Team's DS8 Support Turret ability (game/support_turret.py), wired in main.py
        self.group_move_enabled = False    # QoL: drag every model in the squad at once instead of one at a time (see toggle_group_move()) - a persistent global preference (User-Wunsch: "die toggles sollen global gelten"), same as live_los_highlight_enabled below, not reset per move/squad
        self.live_los_highlight_enabled = False  # QoL perf toggle: the "what can the dragged model see" board highlight, off by default (see toggle_live_los_highlight())

    def select(self, token):
        if token is not None and token.squad is not None and not self.can_select(token.squad):
            return  # not your turn - the opposing player's units can't be selected

        self.selected_squad = token.squad if token is not None else None
        self.selected_model = token
        self.state = SELECTED if self.selected_squad is not None else IDLE
        self._clear_move_state()
        self.errors = []

    def can_select(self, squad):
        if self.turn_tracker is None or squad is None:
            return True
        if self.turn_tracker.phase == PHASE_FIGHT:
            return True  # rule 12.02/12.04: both players act during the Fight phase
        return squad.owner == self.turn_tracker.active_player

    def can_move(self, squad):
        """Base gate shared by every move type this phase (rule 09.02 step
        1): correct phase, and not yet selected to move."""
        if squad is None or squad in self.moved_squad_ids:
            return False
        if self.turn_tracker is not None and self.turn_tracker.phase != PHASE_MOVEMENT:
            return False
        return True

    def can_make_move(self, squad):
        """Rule 09.05/09.06: a Normal or Advance move additionally requires
        the unit to already be unengaged before it can even be selected.
        (Fall Back, 09.07, is the only move type eligible to an engaged
        unit - see can_make_fall_back_move(), its exact inverse.) Rule
        20.04: a unit that just made an Ingress move can't make any other
        type of move until the next Charge phase."""
        if not self.can_move(squad):
            return False
        if squad.ingress_locked:
            return False
        return not squad.is_engaged(self.all_tokens)

    def can_make_fall_back_move(self, squad):
        """Rule 09.07: Fall Back is the inverse of can_make_move() - only
        offered to a squad that IS currently engaged, subject to the same
        base gates (correct phase, not yet moved this phase, not
        ingress-locked)."""
        if not self.can_move(squad):
            return False
        if squad.ingress_locked:
            return False
        return squad.is_engaged(self.all_tokens)

    def reset_movement_phase(self):
        """Rule 09.02/09.03: a new Movement phase comes around every battle
        round, so squads that already moved in a previous one must be able
        to move again. Called once when the active player's turn reaches
        the Movement phase. This also clears the "did this squad remain
        stationary / advance this turn" bookkeeping the Shooting phase reads
        (rules 10.04-10.07), which is correct since that's exactly the point
        a new turn's movement history starts fresh."""
        self.moved_squad_ids = set()
        self.stationary_squad_ids = set()
        self.advanced_squad_ids = set()
        self.moved_distance_this_turn = {}
        self.advance_bonus_by_squad = {}
        self._pending_advance = None

    def remain_stationary(self):
        """Rule 09.02 step 2: 'Remain stationary' is itself a move type -
        selecting it uses up the unit's one move for this phase without
        changing its position."""
        if not self.can_move(self.selected_squad):
            return
        self.moved_squad_ids.add(self.selected_squad)
        self.stationary_squad_ids.add(self.selected_squad)
        if self.game_log is not None:
            self.game_log.add(f"{self._active_player_name()} has {self.selected_squad.name} remain stationary.")
        if self.on_remain_stationary is not None:
            self.on_remain_stationary(self.selected_squad)

    def _begin_move(self, max_distance):
        """Shared setup for every move type: snapshot each model's start
        position, then give it max_distance of remaining range (a flat
        number for all models, or a callable(model) -> float)."""
        self._clear_move_state()
        for model in self.selected_squad.models:
            pos = (model.x_in, model.y_in)
            self.move_start[model.id] = pos
            self.last_waypoint[model.id] = pos
            self.remaining_range[model.id] = max_distance(model) if callable(max_distance) else max_distance
        self.state = MOVING
        self.errors = []
        self.run_used = False
        self.move_mode = None
        self.charge_targets = []
        self.pile_in_targets = []
        self.consolidate_targets = []
        self.consolidate_mode = None
        self.flying_this_move = False
        self.desperate_escape_this_move = False
        self.surge_target = None

    def start_move(self):
        if not self.can_make_move(self.selected_squad):
            return
        # effective_movement_in(), not the printed characteristic: Coldstar
        # Commander's own ability (user-supplied) overrides the Move
        # characteristic of every model in the unit it leads (game/coldstar.py).
        self._begin_move(effective_movement_in)
        # Rule 09.06: the Advance roll is made once and is final for the
        # phase - if this squad already rolled one (and then, say, cancelled
        # the move to redo its positioning), re-apply the same bonus and keep
        # start_run() locked out instead of letting a fresh drag earn a new
        # roll.
        bonus = self.advance_bonus_by_squad.get(self.selected_squad)
        if bonus is not None:
            for model in self.selected_squad.models:
                self.remaining_range[model.id] = self.remaining_range.get(model.id, 0.0) + bonus
            self.run_used = True

    def start_fall_back_move(self, mode):
        """Rule 09.07: like start_move(), but for a squad that's currently
        engaged - confirm_move() still ends up at the generic "must end
        unengaged" check (no move_mode == "fall_back" branch needed there,
        since Fall Back's own end condition is identical to a Normal move's).
        `mode` is "ordered_retreat" or "desperate_escape" - only the latter
        sets desperate_escape_this_move, which clamp_move() reads to let
        models be dragged across other models (not terrain) this move.
        Called by FallBackController once a mode has been chosen."""
        if self.selected_squad is None or not self.can_make_fall_back_move(self.selected_squad):
            return
        # effective_movement_in(), not the printed characteristic: Coldstar
        # Commander's own ability (user-supplied) overrides the Move
        # characteristic of every model in the unit it leads (game/coldstar.py).
        self._begin_move(effective_movement_in)
        self.move_mode = "fall_back"
        self.desperate_escape_this_move = (mode == "desperate_escape")

    def start_charge_move(self, max_distance, charge_targets):
        """Rule 11.04: like start_move(), but every model gets the same
        charge-roll distance instead of the unit's M characteristic, and
        confirm_move() will check charge engagement instead of "must end
        unengaged". Called by ChargeController once a charge roll has been
        made and at least one charge target declared."""
        if self.selected_squad is None:
            return
        self._begin_move(max_distance)
        self.move_mode = "charge"
        self.charge_targets = charge_targets

    def can_make_surge_move(self, squad):
        """Rule 21.02 ELIGIBLE IF (minus "the rule allowing this move type
        has been triggered", which is up to whatever ability/stratagem
        calls start_surge_move() - we have none yet, this is the reusable
        move-type machinery for whenever one arrives, the same way
        start_charge_move() is reusable infra ChargeController drives)."""
        if not self.can_move(squad):
            return False
        if squad.battle_shocked:
            return False
        return not squad.is_engaged(self.all_tokens)

    def start_surge_move(self, squad, max_distance, surge_target):
        """Rule 21.02: like start_charge_move(), but the maximum distance
        comes from whatever rule triggered the surge (not the unit's own M
        characteristic or a charge roll), and confirm_move() checks that
        the unit isn't engaged with anything other than surge_target
        (rule 21.01/21.02's own "closest enemy unit", see
        squad.closest_enemy_squad()) instead of "must end unengaged"."""
        if squad is not self.selected_squad or not self.can_make_surge_move(squad):
            return
        self._begin_move(max_distance)
        self.move_mode = "surge"
        self.surge_target = surge_target

    def start_scout_move(self, squad, max_distance):
        """Rule 24.32 (SCOUT MOVE): like start_surge_move(), but the maximum
        distance is the unit's own Scouts X" and the after-move condition is
        "more than 8" horizontally from all enemy units".

        Deliberately NOT gated on can_move()/can_make_move() the way every
        other move type is: a scout move happens in rule 03.01's Resolve
        Pre-battle Abilities step, before any Movement phase exists, so a
        unit's per-phase move budget has no bearing on it (and would refuse
        it - nothing has had a Movement phase yet). It also isn't gated on
        selected_squad, since the caller (game/scouts.py) drives it directly
        rather than through the human's selection."""
        self.selected_squad = squad
        self._begin_move(max_distance)
        self.move_mode = "scout"

    def start_post_shooting_move(self, squad, move_mode="torchstar", max_distance=None):
        """A Normal move made in the SHOOTING phase, after the unit's own
        attacks have been resolved. Two abilities grant one:

          * Retaliation Cadre's The Torchstar Gambit (1CP, see
            game/torchstar_gambit.py) - "it can make a Normal move", i.e. the
            unit's own M characteristic;
          * Asurmen's Tactical Acumen (see game/tactical_acumen.py) - "it can
            make a Normal move of up to 6"", i.e. a flat cap.

        Hence the two parameters. `move_mode` stays per-ability rather than
        shared, because it is what routes the Confirm button to the controller
        that owns the move's consequences (both of these lock out a charge, but
        each does it from its own confirm) - the same reason Battle Focus's
        reactive moves have their own mode.

        Deliberately NOT gated on can_move()/can_make_move(), for the same
        reason start_scout_move() isn't: those two ask "is this the unit's
        Movement-phase move?" (right phase, not selected to move yet), and
        this is not that move - the unit has normally already made its
        Movement-phase move before it shot. Every condition that DOES apply
        is the stratagem's own (phase, has shot, unengaged, keywords) and is
        checked by TorchstarGambitController.can_use().

        What stays identical to a Normal move is what matters: by default the
        distance is the unit's own M characteristic (via
        effective_movement_in(), so a Coldstar Commander's override still
        applies), and the end condition is confirm_move()'s generic "must end
        unengaged" branch, which any move_mode not named there falls into."""
        if squad is None or squad is not self.selected_squad:
            return
        self._begin_move(effective_movement_in if max_distance is None else max_distance)
        self.move_mode = move_mode

    #: Every move_mode that can be OPEN while it is the other player's turn.
    #:
    #: This exists because the AI driver has to know when to hold still. A
    #: reactive move belongs to the player who is NOT taking the turn, and the
    #: DecisionManager window that offered it has already closed by the time the
    #: move is open - so nothing else tells the AI that a human is mid-drag.
    #: ai/agent_driver.py's _is_blocked() reads exactly this set.
    #:
    #: It lives here, on start_battle_focus_move(), because that method is the
    #: single door every such move comes through: any mode passed to it is
    #: reactive by construction and BELONGS IN THIS SET. Own-turn extra moves
    #: (Torchstar Gambit, Tactical Acumen) go through start_post_shooting_move()
    #: instead and deliberately are not here.
    #:
    #: Hard-coding one mode here instead of a set is a bug that has now been
    #: reported TWICE, in the same words both times: "the AI did not let me make
    #: the move, it just carried on". First for Fade Back, when nothing looked at
    #: the open move at all; then for Rangers' Path of the Outcast, when the gate
    #: looked but compared against the string "battle_focus" only.
    REACTIVE_MOVE_MODES = frozenset({"battle_focus", "path_of_the_outcast",
                                     "raid_and_run", "overflight"})

    def start_battle_focus_move(self, squad, max_distance, move_mode="battle_focus"):
        """A reactive Normal move of an already-rolled distance, taken in the
        OPPONENT's turn.

        ANY `move_mode` passed here must also be listed in REACTIVE_MOVE_MODES
        above, or the AI will walk straight over the move it just granted.

        Built for the Aeldari Agile Manoeuvres Opportunity Seized and Fade Back
        (see game/battle_focus.py): "can make a Normal move of up to D6+1"".
        Rangers' Path of the Outcast is the second, identical in every way that
        matters, which is why `move_mode` is a parameter rather than fixed: it
        is what routes the Confirm button back to the controller that owns the
        consequence, so each ability needs its own.

        `max_distance` is that already-rolled distance, not a characteristic -
        the manoeuvre names its own number, so effective_movement_in() would be
        the wrong source (and, at D6+1", usually the more generous one).

        Not gated on can_move()/can_make_move(), for the reason
        start_scout_move()/start_post_shooting_move() give: those ask "is this the
        unit's Movement-phase move?", and this is not that move - it happens in
        the OPPONENT's turn. Every condition that does apply belongs to the
        manoeuvre and is checked by BattleFocusPool. What stays identical to a
        Normal move is the end condition: confirm_move()'s generic "must end
        unengaged" branch, which any move_mode not named there falls into."""
        if squad is None or squad is not self.selected_squad:
            return
        self._begin_move(lambda model: max_distance)
        self.move_mode = move_mode

    def start_retro_thruster_move(self, squad, fall_back=False):
        """The Twin Lance's Retro-thrusters (see game/retro_thrusters.py):
        "at the end of the Fight phase... this unit can either make a Normal
        move of up to 6\" or a Fall Back move".

        Not gated on can_move()/can_make_move(), for the same reason
        start_post_shooting_move() and start_scout_move() aren't: those ask "is
        this the unit's Movement-phase move?", and this is a different move
        happening in a different phase. The conditions that DO apply are the
        ability's own and are checked by RetroThrustersController.can_use().

        The Normal-move half is capped at a flat 6", NOT the unit's own M -
        the ability names the distance itself, and 6 is less than this
        datasheet's 10" Move, so reading the characteristic would be wrong
        in the unit's favour. The Fall Back half takes the full Move
        characteristic, since the ability puts no number on that one.

        `fall_back` picks between them. Fall Back is the reason this move
        exists at all for an engaged unit: a Normal move must end unengaged
        (confirm_move()'s generic branch, which "retro_thrusters" falls
        into), which an engaged unit usually cannot do. Fall Back is always
        the ORDERED RETREAT variant - Desperate Escape (09.07) is what a
        battle-shocked unit is forced into during its own Movement phase,
        and nothing in this ability's text imposes it."""
        if squad is None or squad is not self.selected_squad:
            return
        if fall_back:
            self.start_fall_back_move("ordered_retreat")
            self.move_mode = "retro_thrusters_fall_back"
            return
        self._begin_move(lambda model: RETRO_THRUSTER_MOVE_IN)
        self.move_mode = "retro_thrusters"

    def start_pile_in_move(self, max_distance, pile_in_targets):
        """Rule 12.03: like start_charge_move(), but for a pile-in move -
        confirm_move() will check pile-in engagement instead. Called by
        PileInController."""
        if self.selected_squad is None:
            return
        self._begin_move(max_distance)
        self.move_mode = "pile_in"
        self.pile_in_targets = pile_in_targets

    def start_consolidate_move(self, max_distance, targets, mode):
        """Rule 12.08: like start_pile_in_move(), but for a consolidation
        move - confirm_move() checks Ongoing or Engaging Consolidation
        engagement depending on mode. Called by ConsolidateController."""
        if self.selected_squad is None:
            return
        self._begin_move(max_distance)
        self.move_mode = "consolidate"
        self.consolidate_targets = targets
        self.consolidate_mode = mode

    def can_advance(self):
        """Rule 09.06: whether this move can still be turned into an Advance.

        The ONE definition, read by start_run() itself and by the panel's
        Advance button - game/ui/action_panel.py used to carry its own
        hand-maintained list of move modes that must NOT offer it, and a list
        that has to grow with every new mode grows wrong: "scout" was missing
        from it.

        `move_mode is None` is the whole rule, not shorthand. An Advance is a
        choice made as part of a unit's OWN Movement-phase move, and that is
        the only move this controller leaves unnamed. Every named mode is
        either not a move that can Advance (charge, pile_in, consolidate,
        surge, fall_back) or a move granted by something else whose printed
        text says "a Normal move" - scout (24.32), torchstar, tactical_acumen,
        fire_and_fade, battle_focus, path_of_the_outcast, retro_thrusters.

        The remaining three terms mirror start_run()'s own refusals, so the
        button appears exactly when clicking it would do something (this
        project's standing rule: the engine must not offer what it would not
        accept)."""
        return (
            self.state == MOVING
            and self.selected_squad is not None
            and self.move_mode is None
            and not self.run_used
            and self.dice_manager is not None
            and self.selected_squad not in self.advance_bonus_by_squad
        )

    def start_run(self):
        if not self.can_advance():
            return

        # Jain Zar's Whirling Death: "do not make an Advance roll. Instead ...
        # add 6 inches". No die is thrown at all, which is why this returns
        # before the roll rather than substituting a value into it: there is
        # then nothing for rule 15.02's Command Re-roll to replace, and
        # _pending_advance (whose only job is to correct such a re-roll) is
        # correctly left unset.
        # Mont'ka's Aggressive Mobility is the SECOND source of exactly this
        # shape - "do not make an Advance roll for it. Instead ... add 6 inches"
        # - so it takes the same no-die branch rather than a second one. The
        # two can never both apply (one is Aeldari, one T'au); Whirling Death
        # is asked first only because it was here first.
        no_roll_bonus = None
        if whirling_death.unit_has_jain_zar(self.selected_squad):
            no_roll_bonus = (whirling_death.begin_advance(self.selected_squad),
                             "Whirling Death")
        elif montka_aggressive_mobility.skips_advance_roll(self.selected_squad):
            no_roll_bonus = (montka_aggressive_mobility.AGGRESSIVE_MOBILITY_BONUS_IN,
                             montka_aggressive_mobility.AGGRESSIVE_MOBILITY_NAME)
        elif guardian_time_to_strike.skips_advance_roll(self.selected_squad):
            no_roll_bonus = (guardian_time_to_strike.TIME_TO_STRIKE_BONUS_IN,
                             guardian_time_to_strike.TIME_TO_STRIKE_NAME)
        if no_roll_bonus is not None:
            bonus, _label = no_roll_bonus
            for model in self.selected_squad.models:
                self.remaining_range[model.id] = self.remaining_range.get(model.id, 0.0) + bonus
            self.run_used = True
            self.advance_bonus_by_squad[self.selected_squad] = bonus
            if self.game_log is not None:
                self.game_log.add(
                    f"{self._active_player_name()} has {self.selected_squad.name} advance "
                    f'({no_roll_bonus[1]}: no roll, a flat {bonus}").'
                )
            return

        values = self.dice_manager.roll(count=1, sides=6, label="Advance", roll_kind=ADVANCE_ROLL)
        bonus = advance_total(self.selected_squad, values, self.all_tokens)
        for model in self.selected_squad.models:
            self.remaining_range[model.id] = self.remaining_range.get(model.id, 0.0) + bonus
        self.run_used = True
        self.advance_bonus_by_squad[self.selected_squad] = bonus
        # The roll is still pending at this point, so rule 15.02's Command
        # Re-roll can still replace this die before it's acknowledged -
        # remember what we applied so on_dice_acknowledged() can correct it.
        self._pending_advance = (self.selected_squad, bonus)

        if self.game_log is not None:
            self.game_log.add(f"{self._active_player_name()} has {self.selected_squad.name} advance (D6: {bonus}).")

    def on_dice_acknowledged(self):
        """Rule 15.02 (Command Re-roll) can replace the Advance die while
        the roll is still pending - start_run() has already added the
        original result to every model's remaining_range by then (it reads
        DiceManager.roll()'s return value synchronously, unlike the Charge
        roll, which ChargeController only reads here at acknowledgement).
        Reconcile the difference so the re-rolled result is the one the
        unit actually gets to move."""
        if self._pending_advance is None:
            return
        squad, applied = self._pending_advance
        self._pending_advance = None
        if self.dice_manager is None or self.dice_manager.roll_kind != ADVANCE_ROLL:
            return
        values = self.dice_manager.last_values
        if not values:
            return
        # Through the SAME helper start_run() used - the +2 from War Horde's
        # 'Ere We Go is applied when the die is rolled, and this compares the
        # re-rolled value against that. A bare sum() here would quietly drop
        # the bonus on any Command Re-roll.
        final = advance_total(squad, values, self.all_tokens)
        delta = final - applied
        if delta == 0:
            return

        self.advance_bonus_by_squad[squad] = final
        # Only models still holding range from this move get adjusted - if
        # the move was cancelled (or already confirmed) while the roll sat
        # pending, remaining_range is gone and the corrected bonus above is
        # what a fresh start_move() will re-apply instead.
        for model in squad.models:
            if model.id in self.remaining_range:
                self.remaining_range[model.id] = max(0.0, self.remaining_range[model.id] + delta)

        if self.game_log is not None:
            self.game_log.add(
                f"{squad.name}'s Advance roll was re-rolled: {applied} -> {final} "
                f"(move distance adjusted by {delta:+d})."
            )

    def can_take_to_the_skies(self):
        """Rule 21.03: before moving any models, a FLYING unit (has a model
        with the FLY keyword) selected to make a normal, advance, or charge
        move may declare it takes to the skies (fall-back move, 09.07, isn't
        implemented yet, so not offered for it). Like start_run()/Advance,
        not strictly re-checked against "hasn't moved any models yet" -
        available any time this move hasn't already declared it."""
        if self.state != MOVING or self.selected_squad is None or self.flying_this_move:
            return False
        if self.move_mode not in (None, "charge"):
            return False
        return any(m.profile.fly for m in self.selected_squad.models)

    def take_to_the_skies(self):
        if not self.can_take_to_the_skies():
            return
        self.flying_this_move = True
        # ONLY THE FLY MODELS PAY, because only they are moved this way. User
        # ruling on the printed rule, asked for after the two halves were found
        # to disagree: "es fliegen nur fly modelle." clamp_move()'s bypass has
        # always been gated per model on token.profile.fly, so that side was
        # already right; this loop charged the 2" to the whole squad, which is
        # what made an attached unit (19.01) with a single flying leader pay
        # twenty times over for one model's bypass - reported as "die necron
        # krieger sind hinten nicht rausgekommen", measured at 21/21 models
        # paying against 1/21 flying, i.e. a 5" move cut to 3" for twenty
        # Necron Warriors every Movement phase.
        #
        # Rule 24.17 (HOVER): "do not subtract 2" from the maximum distance"
        # - the rest of Take to the Skies (ignoring terrain/models) still
        # applies. Left as a squad-wide exemption rather than being made
        # per-model along with the penalty: that is the existing reading, no
        # datasheet in any of the four rosters prints HOVER, and narrowing it
        # was not part of the ruling above.
        if not any(m.profile.hover for m in self.selected_squad.models):
            for model in self.selected_squad.models:
                if not model.profile.fly:
                    continue
                self.remaining_range[model.id] = max(
                    0.0, self.remaining_range.get(model.id, 0.0) - TAKE_TO_THE_SKIES_DISTANCE_PENALTY_IN,
                )
        if self.game_log is not None:
            self.game_log.add(f"{self._active_player_name()} has {self.selected_squad.name} take to the skies (rule 21.03).")

    def toggle_group_move(self):
        """QoL feature (not a rule): drag the whole squad at once, in its
        current formation, instead of one model at a time. Only a drag
        convenience - apply_group_drag() below still runs every model
        through the exact same clamp_move() per-model checks (remaining
        range/terrain/enemy models/board edges) a normal single-model drag
        does, so a squad can still end up sheared apart by an obstacle and
        fail check_coherency() on Confirm, same as it always could. A
        persistent GLOBAL preference (User-Wunsch: "die toggles sollen
        global gelten... bleibt er für alle squads an, bis ich ihn
        ausschalte") - nothing resets it at the start/end of a move or
        squad selection anymore (it used to, back when it lived inside the
        per-squad movement UI), same as toggle_live_los_highlight() below.
        Unrestricted to MOVING state on purpose, now that it's toggled from
        an always-visible toolbar rather than a screen that only exists
        mid-move - lets it be set before a drag even starts."""
        self.group_move_enabled = not self.group_move_enabled

    def toggle_live_los_highlight(self):
        """QoL perf toggle (not a rule, not the movement-mode state above -
        see main.py's visibility_cache): whether dragging a model shows a
        live "which enemy models can this one currently see" board
        highlight. User-request follow-up to the same LOS-cost-at-~130-
        models complaint that motivated Move Whole Squad's own LOS skip
        (that one only disables the highlight while group-dragging) - this
        is the general version, off by default, and unlike group_move_
        enabled it's a persistent session preference: nothing resets it
        automatically at the start/end of a move, since re-enabling it
        before every single drag would defeat the point of turning it off
        for performance in the first place. Unrestricted to MOVING state on
        purpose (harmless, and lets it be toggled before a drag even
        starts)."""
        self.live_los_highlight_enabled = not self.live_los_highlight_enabled

    def apply_group_drag(self, dx_in, dy_in):
        """Rigid-translate every model in the selected squad by the same
        (dx_in, dy_in) offset from its OWN last committed waypoint - one
        shared offset preserves the squad's current formation exactly, the
        same "move everything by one vector" approach
        ai/agent_driver.py's _translate_squad_toward() uses for the AI.
        Each model is still clamped independently through clamp_move(), so
        one model hitting an obstacle/board edge doesn't halt the others -
        it just won't travel as far, and may need fixing by hand (or a
        Cancel) before Confirm. Doesn't commit anything - see
        commit_group_drag(), called once when the drag gesture ends."""
        if self.selected_squad is None:
            return
        for model in self.selected_squad.models:
            origin = self.last_waypoint.get(model.id)
            if origin is None:
                continue
            ox, oy = origin
            model.x_in, model.y_in = self.clamp_move(model, ox + dx_in, oy + dy_in)

    def commit_group_drag(self):
        """Counterpart to apply_group_drag(): validates and locks in every
        model's traveled distance at once, the same try_commit_segment() a
        normal single-model drag runs on mouse-up. A model whose target
        position is illegal (overlap/terrain/disallowed engagement) snaps
        back individually - the rest of the group keeps its shared-offset
        position, breaking the rigid formation at that one spot rather than
        rejecting the whole group's move (matches apply_group_drag()'s own
        already-documented "one model hitting an obstacle doesn't halt the
        others" philosophy - an instant-check rejection is just one more
        reason a model can fall behind, not a new failure category).

        apply_group_drag() writes every model's PREVIEW target position
        before any of them is validated here - so, unlike a plain
        single-model drag, two squadmates' freshly-written previews could
        otherwise reject each other purely by iteration order even though
        only one of them is really "still in the way". Each model is
        therefore validated against every OTHER squadmate not yet
        committed in THIS SAME call (still holding its raw, unvalidated
        preview) excluded from the overlap check - once a model commits
        successfully it becomes a real blocker for the rest of the batch,
        same "first claim wins, closest processed first" idea already used
        by ai/agent_driver.py's per-model movement loops."""
        if self.selected_squad is None:
            return
        errors = []
        committed = set()
        for model in self.selected_squad.models:
            still_pending = {m for m in self.selected_squad.models if m is not model and m not in committed}
            ok, model_errors = self.try_commit_segment(model, exclude_from_overlap=still_pending)
            if ok:
                committed.add(model)
            else:
                errors.extend(model_errors)
        self.errors = list(dict.fromkeys(errors))

    # Set by main.py - rule 16.01's move-cancellation hook, see confirm_move().
    action_controller = None
    # Set by main.py - the Shadow Weaver Platform's snare, read at the same
    # seam and for the same reason. A class attribute like the one above, so
    # every existing MovementController (tests, harnesses) keeps working
    # without a constructor change.
    monofilament_snare = None
    # Set by main.py - the Exodites' Drakolithe, read at the same seam.
    drakolithe = None

    def confirm_move(self):
        if self.selected_squad is None:
            return

        errors = self.selected_squad.check_coherency()
        errors += self.selected_squad.check_terrain(self.obstacles)
        errors += self.selected_squad.check_model_overlap(self.all_tokens)
        if self.move_mode == "charge":
            errors += self.selected_squad.check_charge_engagement(self.charge_targets, self.all_tokens)
        elif self.move_mode == "pile_in":
            errors += self.selected_squad.check_pile_in_engagement(self.pile_in_targets, self.all_tokens)
        elif self.move_mode == "consolidate":
            if self.consolidate_mode == "ongoing":
                errors += self.selected_squad.check_ongoing_consolidation(self.consolidate_targets, self.all_tokens)
            elif self.consolidate_mode == "engaging":
                errors += self.selected_squad.check_engaging_consolidation(self.consolidate_targets)
            else:  # "objective"
                errors += self.selected_squad.check_objective_consolidation(self.consolidate_targets[0])
        elif self.move_mode == "surge":
            errors += self.selected_squad.check_surge_engagement(self.surge_target, self.all_tokens)
        elif self.move_mode == "scout":
            errors += self.selected_squad.check_scout_move_clearance(self.all_tokens)
        elif self.selected_squad.is_engaged(self.all_tokens):
            errors.append("Your unit must end this move unengaged (rule 09.05/09.06).")
        if errors:
            # Coherency is the one failure here whose message ("not a single
            # connected group", "spread too far apart") names no models and
            # no distances. When it's the cause, follow it with the numbers -
            # measured NOW, on the rejected positions, because the revert
            # below throws exactly the state that has to be explained away.
            if self.game_log is not None:
                detail = coherency_report(self.selected_squad)
                if detail is not None:
                    self.game_log.add(
                        f"  [coherency] {self.selected_squad.name} could not end its "
                        f"{self.move_mode or 'move'} here - {detail}",
                        file_only=True,
                    )
            self._revert_last_segment(errors)
            self.errors = errors
            return

        if self.game_log is not None:
            self.game_log.add(f"{self.selected_squad.owner} moved {self.selected_squad.name}.")
            positions = ", ".join(f"({m.x_in:.2f},{m.y_in:.2f})" for m in self.selected_squad.models)
            self.game_log.add(
                f"  [move detail] {self.selected_squad.name} mode={self.move_mode} final positions: {positions}",
                file_only=True,
            )
            # Canary (see GameLog's own docstring for why this exists at
            # all): `errors` above is already known empty at this point, so
            # re-checking coherency on the SAME, unchanged squad state
            # should be tautological - if this ever actually fires, that's
            # direct proof either check_coherency() itself or the error-
            # collection above has a real bug, caught the instant it
            # happens instead of requiring a synthetic reproduction.
            canary = self.selected_squad.check_coherency()
            if canary:
                self.game_log.add(
                    f"!!! CANARY: {self.selected_squad.name} reports a coherency violation "
                    f"immediately after a successful confirm_move() - {canary}"
                )

        if self.move_mode == "charge":
            self.selected_squad.fights_first = True
            self.selected_squad.charged_this_turn = True
        elif self.move_mode not in ("pile_in", "consolidate", "scout", "torchstar",
                                    "tactical_acumen", "fire_and_fade",
                                    "battle_focus", "path_of_the_outcast"):
            # The two post-shooting modes are excluded for a related reason
            # (see start_post_shooting_move()): they happen in the SHOOTING
            # phase and are
            # not the unit's Movement-phase move, which it has normally
            # already made - marking it here would retroactively claim a
            # phase that is over. moved_distance_this_turn is left alone for
            # the same reason and is harmless: rule 24.16's [HEAVY] is read
            # when a unit SHOOTS, this unit has already shot, and the only
            # shooting still ahead of it is a Snap Shot (15.09), which
            # ignores every modifier anyway.
            #
            # The two REACTIVE modes ("battle_focus" - Fade Back and
            # Opportunity Seized - and "path_of_the_outcast") are excluded for
            # the same reason one step further out: they happen in the
            # OPPONENT's turn, so booking them claims a Movement phase that is
            # not merely over but belongs to the other player. It self-heals
            # today, because reset_movement_phase() runs before the reacting
            # player's own Movement phase - but Rangers are the datasheet that
            # makes the stakes concrete, since [HEAVY] (24.16) is on their main
            # gun, and relying on a reset in another file for correctness is
            # exactly the coupling the note below warns about.
            #
            # "scout" is excluded explicitly, not by accident: a Scout Move
            # (24.32) happens in rule 03.01's Resolve Pre-battle Abilities
            # step, BEFORE battle round 1 - it is not the unit's Movement-phase
            # move. Counting it here would mark the unit as already moved
            # (blocking 09.02) and as having moved more than 3" (stripping
            # [HEAVY], 24.16) for its first real turn. That self-heals today,
            # because main.py calls reset_movement_phase() on reaching the
            # Movement phase - but relying on a reset in another file for
            # correctness is exactly the coupling that bites later.
            self.moved_squad_ids.add(self.selected_squad)
            if self.run_used:
                self.advanced_squad_ids.add(self.selected_squad)
            # "ends a Normal, Advance or Fall Back move" - exactly those three.
            # There is no "normal"/"advance" move_mode: a plain Normal move
            # leaves it None and an Advance is a Normal move plus the D6 (tracked
            # in advanced_squad_ids), so the qualifying set is None + fall_back.
            # Every named mode - charge, pile_in, consolidate, surge, scout,
            # battle_focus, retro_thrusters, torchstar - is deliberately excluded.
            if self.move_mode in (None, "fall_back"):
                if self.move_mode == "fall_back":
                    kind = "fall_back"
                else:
                    kind = "advance" if self.selected_squad in self.advanced_squad_ids else "normal"
                self._move_finished_pending = (self.selected_squad, kind)
            if self.move_mode == "fall_back":
                # Rule 09.07: "until the end of the turn" - reset alongside
                # charge_locked_until_end_of_turn/set_up_this_turn in
                # main.py's advance_turn_phase(), same "until end of turn"
                # flag idiom.
                self.selected_squad.fell_back_this_turn = True
                self._fell_back_pending = self.selected_squad
            # Rule 24.16 ([HEAVY]): "no model in that unit has moved more
            # than 3\" this turn" - recorded here (Normal/Advance/Surge are
            # the only Movement-phase move types; Charge/Pile-In/Consolidate
            # happen in later phases, after this turn's Shooting phase - and
            # thus this [HEAVY] check - has already passed).
            max_dist = 0.0
            for model in self.selected_squad.models:
                start = self.move_start.get(model.id)
                if start is not None:
                    dist = ((model.x_in - start[0]) ** 2 + (model.y_in - start[1]) ** 2) ** 0.5
                    max_dist = max(max_dist, dist)
            self.moved_distance_this_turn[self.selected_squad] = max_dist
        # Where every model STOOD before this move, kept past the state clear
        # below. Canoptek Wraiths' Wraith Form needs the segment each model
        # actually travelled ("one enemy unit it MOVED OVER"), and
        # on_move_finished fires after _clear_move_state() has emptied
        # move_start - so the snapshot has to be taken here. Additive: no
        # listener signature changes, see game/wraith_form.py.
        self.last_move_start = dict(self.move_start)
        # Rule 16.01: "If a unit performing an action makes a move (excluding
        # pile-in and consolidation moves) ... that unit does not complete that
        # action." Reported here, at the one place every confirmed move passes
        # through, and with the move's OWN mode so the two named exceptions are
        # recognised by name rather than guessed at.
        if self.action_controller is not None:
            self.action_controller.notify_move(self.selected_squad, self.move_mode)
        # The Shadow Weaver Platform's Monofilament Snare: a snared unit rolls
        # a D6 per model each time it makes a Normal, Advance or Fall Back move
        # and bleeds a mortal wound for every 1. Reported from the SAME seam as
        # rule 16.01 above - confirm_move() is the one place every confirmed
        # move passes through, and the move's own mode is what tells the two
        # rules apart from a Charge or a Pile-In.
        if self.monofilament_snare is not None:
            self.monofilament_snare.notify_move(self.selected_squad, self.move_mode)
        # The Exodites' Drakolithe reacts to the same instant, but to ANY move:
        # its printed text names no move types where the snare above names
        # three. See game/drakolithe.py.
        if self.drakolithe is not None:
            self.drakolithe.notify_move(self.selected_squad, self.move_mode)
        # Captured before the clear below wipes it - see on_scout_move_finished.
        _finished_scout = self.selected_squad if self.move_mode == "scout" else None
        self._clear_move_state()
        self.errors = []
        self.state = SELECTED
        self.move_mode = None
        self.charge_targets = []
        self.pile_in_targets = []
        self.consolidate_targets = []
        self.consolidate_mode = None
        self.flying_this_move = False
        self.desperate_escape_this_move = False
        self.surge_target = None

        fell_back = self._fell_back_pending
        self._fell_back_pending = None
        if fell_back is not None and self.on_fall_back_finished is not None:
            self.on_fall_back_finished(fell_back)
        if _finished_scout is not None and self.on_scout_move_finished is not None:
            self.on_scout_move_finished(_finished_scout)
        moved = self._move_finished_pending
        self._move_finished_pending = None
        if moved is not None:
            for listener in (self.on_move_finished or ()):
                listener(*moved)

    def cancel_move(self):
        if self.selected_squad is None:
            return

        for model in self.selected_squad.models:
            origin = self.move_start.get(model.id)
            if origin is not None:
                model.x_in, model.y_in = origin

        # A cancelled scout move still ENDS it, and the SCOUTS queue is waiting
        # on exactly that - without this a cancel would strand the pre-game.
        _finished_scout = self.selected_squad if self.move_mode == "scout" else None
        self._clear_move_state()
        self.errors = []
        self.state = SELECTED
        self.move_mode = None
        self.charge_targets = []
        self.pile_in_targets = []
        self.consolidate_targets = []
        self.consolidate_mode = None
        self.flying_this_move = False
        self.desperate_escape_this_move = False
        self.surge_target = None
        if _finished_scout is not None and self.on_scout_move_finished is not None:
            self.on_scout_move_finished(_finished_scout)

    def is_movable(self, token):
        return (
            self.state == MOVING
            and self.selected_squad is not None
            and token in self.selected_squad.models
        )

    def _enemy_models(self, token):
        """Rule 03.01: a model's base can be moved through friendly models,
        but not through enemy ones."""
        if token.squad is None:
            return []
        return [
            other for other in self.all_tokens
            if other is not token and other.squad is not None
            and other.squad.owner != token.squad.owner
        ]

    def clamp_move(self, token, x_in, y_in):
        """Clamp a candidate position for the *current, uncommitted* drag
        segment: at most the remaining range, never through an obstacle or an
        enemy model's base, and never across the edge of the battlefield."""
        origin = self.last_waypoint.get(token.id)
        if origin is None:
            return x_in, y_in

        ox, oy = origin
        dx, dy = x_in - ox, y_in - oy
        dist = (dx * dx + dy * dy) ** 0.5
        remaining = self.remaining_range.get(token.id, 0.0)
        # The crossing house rule's price, applied to the BUDGET rather than to
        # what is left over afterwards - "3 Zoll von ihrer Bewegung abziehen".
        # Deducting it after the fact was tried first and is silently free: a
        # model that spends its whole move travelling has nothing left for the
        # toll to come out of, so it crosses for nothing. See _wall_toll().
        toll, walls_block = self._wall_toll(token, origin, (x_in, y_in), remaining)
        budget = max(0.0, remaining - toll)
        if dist > budget and dist > 0:
            scale = budget / dist
            x_in, y_in = ox + dx * scale, oy + dy * scale

        if self.flying_this_move and token.profile.fly:
            # Rule 21.03: while taking to the skies, a FLYING model can move
            # horizontally through all terrain features and through any
            # model (friendly or enemy, including MONSTER/VEHICLE) - only
            # remaining range and the board edges still constrain it.
            fraction = 1.0
        else:
            # Rule 13.05/13.06: only Dense terrain blocks movement, and even
            # then not for INFANTRY/BEASTS/SWARM/MOBILE models - Exposed/Light
            # terrain (13.03/13.04) "can be traversed without hindrance".
            blocking_obstacles = [o for o in self.obstacles if o.blocks_movement_for(token)]
            if walls_block:
                # Either the model cannot afford the toll, or this segment
                # would not have reached a wall anyway. Both mean rule 13.06
                # applies unchanged for this step, so put the walls back.
                blocking_obstacles = blocking_obstacles + [
                    o for o in self.obstacles
                    if o.category == DENSE and o not in blocking_obstacles
                ]
            obstacle_fraction = geometry.max_unblocked_fraction(
                (ox, oy), (x_in, y_in), blocking_obstacles, inflate_radius=token.radius_in
            )
            if self.desperate_escape_this_move or scuttling_walker.can_cross_models(token):
                # Rule 09.07 (Desperate Escape): models "may be moved across
                # other models" - unlike Take to the Skies above, this bypass
                # is models-only, terrain still blocks normally.
                #
                # The Defiler's Scuttling Walker joins it here rather than in
                # the FLY branch above, and the difference matters: it moves
                # THROUGH models and terrain but is still bound by rule 09.02's
                # end-of-move checks, so it cannot FINISH inside a wall or in
                # Engagement Range. Its terrain half is handled one level down,
                # in Obstacle.blocks_movement_for().
                model_fraction = 1.0
            else:
                model_fraction = geometry.max_unblocked_fraction_models(
                    (ox, oy), (x_in, y_in), self._enemy_models(token), inflate_radius=token.radius_in
                )
            fraction = min(obstacle_fraction, model_fraction)
        if fraction < 1.0:
            seg_dx, seg_dy = x_in - ox, y_in - oy
            seg_len = (seg_dx * seg_dx + seg_dy * seg_dy) ** 0.5
            if seg_len > 0:
                fraction = max(0.0, fraction - OBSTACLE_PULLBACK_IN / seg_len)
            x_in = ox + (x_in - ox) * fraction
            y_in = oy + (y_in - oy) * fraction

        if self.board_width_in is not None:
            x_in = max(token.radius_in, min(self.board_width_in - token.radius_in, x_in))
        if self.board_height_in is not None:
            y_in = max(token.radius_in, min(self.board_height_in - token.radius_in, y_in))

        return x_in, y_in

    def _finalize_segment(self, token):
        """Unconditionally locks in the distance traveled since the last
        waypoint and deducts it from the model's remaining range. Keeps a
        1-step undo (previous_waypoint/previous_remaining_range) so a
        confirm-time-only failure (coherency, or the "must reach target"
        half of Charge/Pile-In/Consolidate/Surge) can still snap the whole
        squad's last segment back via _revert_last_segment(). Only ever
        called by try_commit_segment() after it has confirmed the position
        is legal - never call this directly."""
        origin = self.last_waypoint.get(token.id)
        self.previous_waypoint[token.id] = origin
        self.previous_remaining_range[token.id] = self.remaining_range.get(token.id, 0.0)

        ox, oy = origin
        dist = ((token.x_in - ox) ** 2 + (token.y_in - oy) ** 2) ** 0.5
        remaining = self.remaining_range.get(token.id, 0.0)
        # The toll again, so the bookkeeping matches what clamp_move() already
        # allowed: it shortened this step by the toll, and the same amount has
        # to leave the budget or the next step gets it back.
        toll, _walls_block = self._wall_toll(token, (ox, oy), (token.x_in, token.y_in), remaining)
        self.remaining_range[token.id] = max(0.0, remaining - dist - toll)
        self.last_waypoint[token.id] = (token.x_in, token.y_in)

    def _wall_toll(self, token, origin, requested, remaining):
        """`(toll, walls_block)` for one candidate segment under the crossing
        house rule (config.VEHICLES_CROSS_WALLS - see there for why it exists;
        Obstacle.blocks_movement_for() is the permission half).

        `toll` comes off the distance this step may cover, and `walls_block`
        says to treat Dense terrain as impassable for this step after all. The
        three outcomes:

          * the model crosses Dense terrain for free by rule 13.06 anyway
            (INFANTRY/BEASTS/SWARM/MOBILE), or is flying over it (21.03) -
            nothing to charge, nothing to block;
          * it cannot afford the toll out of what is left of its move - then it
            simply cannot grind over the wall, and 13.06 applies unmodified, so
            it is stopped at the wall exactly as before;
          * it can afford it AND the part of this segment it can still pay for
            actually reaches a wall - charge once.

        The last condition is why the affordable length is tested rather than
        the requested one: a model aimed far past a wall it would only reach in
        the last inch should not be billed for a crossing it never makes, and
        without the toll it may legitimately drive right up to the wall and
        stop - which is strictly better for it than being shortened by 3" for
        nothing."""
        if not may_cross_walls(token) or config.WALL_CROSSING_COST_IN <= 0:
            return 0.0, False
        profile = getattr(token, "profile", None)
        if profile is None or profile.can_move_through_dense_terrain:
            return 0.0, False
        if self.flying_this_move and profile.fly:
            return 0.0, False
        walls = [o for o in self.obstacles if o.category == DENSE]
        if not walls:
            return 0.0, False
        if remaining <= config.WALL_CROSSING_COST_IN:
            return 0.0, True

        ox, oy = origin
        dx, dy = requested[0] - ox, requested[1] - oy
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 1e-9:
            return 0.0, True
        affordable = min(dist, remaining - config.WALL_CROSSING_COST_IN)
        scale = affordable / dist
        reach = (ox + dx * scale, oy + dy * scale)
        crosses = geometry.max_unblocked_fraction(
            origin, reach, walls, inflate_radius=token.radius_in) < 1.0
        return (config.WALL_CROSSING_COST_IN, False) if crosses else (0.0, True)

    def _instant_violations(self, token, exclude_from_overlap=frozenset()):
        """The subset of a move's legality that's attributable to THIS ONE
        model's placement alone, checkable the instant it's placed rather
        than only once the whole squad has finished moving: Dense terrain
        (rule 13.05), overlapping another model - friendly or enemy (rule
        03.01) - and (move-mode-specific) ending within Engagement Range of
        an enemy unit this move type forbids touching right now (see
        Squad.disallowed_enemy_squads_for_move()). Deliberately excludes
        Coherency and the "must actually reach the declared target" half of
        Charge/Pile-In/Consolidate/Surge - both are squad-wide, only
        resolvable once every model has been placed, and stay
        confirm_move()-only.

        `exclude_from_overlap` lets a caller that writes several models'
        PREVIEW positions before validating any of them (only
        commit_group_drag() does this - a plain single-model drag, and
        every AI per-model loop, fully validates+commits one model before
        touching the next) name the squadmates still holding a provisional,
        not-yet-validated target this same batch - otherwise two freshly
        conflicting previews could reject EACH OTHER purely by processing
        order, even though only one of them is really "the last one in".
        A squadmate that's simply standing still, untouched this move, is
        NOT excluded here - its position is already final and must count as
        a real blocker, exactly like check_model_overlap()'s confirm-time
        check."""
        errors = []
        if model_terrain_violation(token, self.obstacles):
            errors.append("Models cannot end their move on top of Dense terrain (walls).")
        if model_overlaps_any(token, self.all_tokens, exclude=exclude_from_overlap):
            errors.append("Models cannot end their move on top of another model.")
        if self.selected_squad is not None:
            for enemy_squad in self.selected_squad.disallowed_enemy_squads_for_move(
                self.all_tokens, self.move_mode, self.charge_targets, self.surge_target,
            ):
                if model_engaged_with(token, enemy_squad):
                    errors.append(
                        f'This model cannot be within Engagement Range of "{enemy_squad.name}" right now.'
                    )
        return errors

    def try_commit_segment(self, token, exclude_from_overlap=frozenset()):
        """Called when a drag/computed-move segment ends: validates token's
        CURRENT (already clamp_move()-clipped) position against every rule
        violation attributable to this one model's placement alone (see
        _instant_violations()) and only commits if none apply. On
        rejection, snaps token back to its waypoint from just before THIS
        attempt (last_waypoint) - remaining_range, move_start and every
        other model are left untouched, as if this one segment never
        happened. Sets self.errors either way (the movement UI already
        renders self.errors every frame - see action_panel.py's
        _draw_message_box() - so no separate display plumbing is needed).
        Returns (True, []) on success, (False, [messages]) on rejection."""
        origin = self.last_waypoint.get(token.id)
        if origin is None:
            return True, []

        errors = self._instant_violations(token, exclude_from_overlap=exclude_from_overlap)
        if errors:
            token.x_in, token.y_in = origin
            self.errors = errors
            return False, errors

        self._finalize_segment(token)
        self.errors = []
        return True, []

    def _clear_move_state(self):
        self.move_start = {}
        self.last_waypoint = {}
        self.remaining_range = {}
        self.previous_waypoint = {}
        self.previous_remaining_range = {}

    def _revert_last_segment(self, errors=()):
        """Only reached by confirm_move() now for the two failure classes
        that try_commit_segment()'s per-model instant check can't catch -
        Coherency, and the "must actually reach the declared target" half
        of Charge/Pile-In/Consolidate/Surge - both genuinely squad-wide,
        only resolvable once every model has been placed, so there's no
        single model to blame. Snaps every model in the squad back to its
        position from just before its most recent committed segment,
        refunding that segment's distance - squad-wide is still the right
        granularity here, unlike try_commit_segment()'s single-model
        revert. One step, not a full undo history: enough to make the last
        adjustment differently without redoing the whole move.

        `errors` is confirm_move()'s reason list, purely so the log line can
        NAME the failure. Without it the file only ever said "illegal move -
        X snapped back", which is where the reported "ten snap-backs then 0
        inches moved" case stalled: ten identical lines that don't
        distinguish coherency from "never reached the charge target", the
        only two things that can reach this method at all."""
        if self.selected_squad is None:
            return
        reverted_any = False
        for model in self.selected_squad.models:
            prev_pos = self.previous_waypoint.pop(model.id, None)
            prev_range = self.previous_remaining_range.pop(model.id, None)
            if prev_pos is None:
                continue
            model.x_in, model.y_in = prev_pos
            self.last_waypoint[model.id] = prev_pos
            if prev_range is not None:
                self.remaining_range[model.id] = prev_range
            reverted_any = True
        if reverted_any and self.game_log is not None:
            self.game_log.add(
                f"{self._active_player_name()}: illegal move - {self.selected_squad.name} "
                f"snapped back to before the last step."
            )
            if errors:
                # File-only: the action panel already shows self.errors to a
                # human mid-move, so this is purely so the FILE says which of
                # the two possible squad-wide failures it was. Reading back a
                # run of these is how "it tried ten times and moved 0 inches"
                # becomes a diagnosis instead of a guess.
                self.game_log.add(
                    f"  [move reject] {self.selected_squad.name} mode={self.move_mode}: "
                    + " ".join(errors),
                    file_only=True,
                )

    def _active_player_name(self):
        return self.turn_tracker.active_player if self.turn_tracker is not None else self.player_name
