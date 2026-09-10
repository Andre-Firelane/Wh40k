import math
import threading

from ai import connection
from ai import observation
from ai.observation import build_observation, build_planning_observation
from game import status_effects
from game.ingress import INGRESS_MIN_BATTLE_ROUND
from game import arrokon_protocol as arrokon_module
from game import base_contact
from game import coldstar
from game import combat_focus
from game import config
from game import attached_units
from game.coherency import coherency_report, connected_groups
from game import consolidate as consolidate_module
from game import crushing_impact as crushing_impact_module
from game import explosives as explosives_module
from game import fall_back as fall_back_module
from game import fight as fight_module
from game import formation_layout
from game import front_rank
from game.terrain import DENSE, Obstacle
from game import game_log as game_log_module
from game import geometry
from game import greater_good as greater_good_module
from game import line_of_sight
# For REACTIVE_MOVE_MODES - the set of move_modes a player can have OPEN
# during the opponent's turn, which _is_blocked() has to hold still for.
from game.movement import MovementController, take_to_the_skies_pays
from game import objective_control
from game import overwatch as overwatch_module
from game import pathfinding
from game import protocol_conquering_tyrant
from game import protocol_hungry_void
from game import shooting as shooting_module
from game.weapons import RANGED as RANGED_WEAPON
from game.charge import CHARGE_RANGE_IN
from game.consolidate import CONSOLIDATE_RANGE_IN
from game.damage_estimate import expected_wounds_against
from game.dice import CHARGE_ROLL
from game.ere_we_go import ERE_WE_GO_ROLL_BONUS
from game.objectives import is_on_objective
from game.pile_in import PILE_IN_RANGE_IN
from game.setup import PLACING
from game.shooting import _wound_threshold as _shooting_wound_threshold
from game.squad import COHERENCY_RANGE_IN, ENGAGEMENT_RANGE_IN, MAX_SPREAD_IN, OBJECTIVE_CONSOLIDATION_RANGE_IN, attached_unit_toughness, edge_distance, max_model_radius, min_model_movement, model_engaged_with, model_terrain_violation, spread_limit_applies
from game.transport import DISEMBARK_DISTANCE_IN
from game.turn import PHASE_CHARGE, PHASE_COMMAND, PHASE_FIGHT, PHASE_MOVEMENT, PHASE_SHOOTING
from game.waaagh import squad_waaagh_active
from game.weapons import RANGED

# _movement_priority_key()'s fallback sort priority for a squad the strategic
# plan doesn't mention (no plan yet, or Claude simply skipped it) - sorts
# after every squad the plan DOES give a real (presumably much smaller)
# priority to, per rule-of-thumb "plan-assigned order wins, everything else
# keeps today's vehicle/distance-based order among itself".
_SPOT_CONFLICT_MARGIN_IN = 3.0  # a squad needs room around its ordered spot, not just the point
_UNPLANNED_MOVE_PRIORITY = 10**6

CHARGE_TARGET_CLEARANCE_IN = 1.0  # aim to land well inside Engagement Range (2"), not right at its edge
PILE_IN_CLEARANCE_IN = 0.1  # rule 12.03: pile in "as close as possible" - much tighter than a charge's safety margin

# (angle, fraction-of-roll) detour legs _handle_charge() sweeps through - see
# _charge_per_model()'s phase 1. The first entry is the plain direct approach,
# so an unobstructed charge still takes the straight line on its very first
# attempt and behaves exactly as it did before the sweep existed.
#
# The angles reach 90 degrees (a pure sidestep along an obstacle) rather than
# stopping around 60 like the Movement phase's ADVANCE_ANGLE_JITTER_DEG: the
# whole point here is slipping past a wall the direct line runs into, and a
# shallower angle keeps grazing the same wall - measured on the reported
# Ghostkeel case, 65 degrees still only moved 1.3" of a 7" roll. Nothing goes
# BEYOND 90, though, since a charge must still end in Engagement Range with
# its declared target - retreating from it can never achieve that.
#
# Each angle is tried at two detour lengths, shorter first: a detour that's
# too short never clears the obstacle, and one that eats the whole roll
# leaves nothing to close in with.
# Extra distance a charging model may travel along its own approach line to
# get OFF a piece of terrain it would otherwise stop on. Ordered smallest
# first, so an unobstructed charge still lands exactly where it intended.
_CHARGE_STEP_OVER_IN = (0.0, 0.8, 1.6, 2.6, 4.0)

# Fractions of the shared phase-1 translation to fall back through when the
# full one leaves the squad less coherent than it started (see
# _run_phase_one()). A shorter shared offset is strictly more likely to fit
# every model - each one's obstacle is that much further away - and the
# implicit last rung, not moving at all, is coherency-safe by definition.
_PHASE_ONE_FRACTIONS = (1.0, 0.75, 0.5, 0.25)

# How much of a coherency-breaking per-model placement to keep, tried in order,
# when shrinking it back toward the formation it started from (see
# _repair_coherency_by_shrinking()). Deliberately short: each rung costs a
# fresh start()/placement pass, and the sweep above already runs dozens.
_COHERENCY_SHRINK_FRACTIONS = (0.6, 0.35, 0.15)

# How far a REGROUP move is allowed to push the re-formed block toward its
# target, as a fraction of the squad's own move budget - longest first (see
# _regroup_move()). The 0.0 rung is "close up where you stand", which asks the
# least of the stragglers and is therefore the one most likely to hold; the
# longer rungs exist so re-forming does not automatically cost the whole turn's
# advance when there is range to spare.
_REGROUP_ADVANCE_FRACTIONS = (0.6, 0.3, 0.0)

# How many engagement slots a single model may try before settling (see
# _ranked_free_slots()/_charge_per_model()'s phase 2). Its first choice can be
# blocked by a squadmate or a piece of terrain that only shows up once the step
# is actually attempted, and one blocked choice used to mean the model simply
# stopped short. Small on purpose: each try is a full clamp + validate, the
# list is already in preference order, and the search stops the moment a
# candidate puts the model in Engagement Range.
_ENGAGEMENT_SLOT_TRIES = 6

# How far short of touching a friendly model a clamped destination is pulled
# back (see _clamp_target_against_friendly_models()). Small enough that no rule
# threshold can notice it, large enough to be outside floating-point noise on
# an exactly-tangent circle.
_FRIENDLY_CLAMP_EPSILON_IN = 0.01

CHARGE_APPROACH_PLAN = tuple(
    [(0.0, 0.0)]
    + [(angle, fraction)
       for angle in (-45.0, 45.0, -65.0, 65.0, -90.0, 90.0)
       for fraction in (0.35, 0.6)]
)
# Facings the disembark placement sweeps through before giving up - the
# enemy-facing side first, then progressively around the transport.
_DISEMBARK_FACINGS = (0.0, math.pi / 4, -math.pi / 4, math.pi / 2, -math.pi / 2,
                      3 * math.pi / 4, -3 * math.pi / 4, math.pi)
DISEMBARK_MODEL_GAP_IN = 1.5  # lateral spacing between disembarked models - matches the deployment scene's own spacing

# Staging (user-requested tactical heuristic, not itself a rule - see CLAUDE.md):
# how many candidate Dense terrain areas get an actual (relatively pricey,
# real line_of_sight.has_line_of_sight() calls) exposure check, and how
# cheap each of those checks is made (far below the SAMPLE_POINTS=24 default
# used for anything rules-critical like Benefit of Cover - this only ever
# ranks candidates against each other, it never resolves an actual rule).
STAGING_CANDIDATE_AREAS = 6
STAGING_EXPOSURE_SAMPLE_POINTS = 6

# Auto-Ingress landing search (user-requested "always deploy reserves as
# early as possible" policy, rule 20.04's Ingress move - see
# _ingress_landing_candidates()): a handful of depths into the legal 6"
# edge margin (deepest/closest-to-board-center first, since that's usually
# closest to a target on the far side of the board), tried at positions
# spanning the FULL length of each of the 4 battlefield edges, not just a
# narrow window near the "closest to the front" spot. Real user report,
# reproduced against a realistic (not just freshly-deployed) round-2 board:
# both players' deployment zones on this board/army sit entirely within
# their own 6" ingress margin and stay busy with ~65 models each even after
# a round of movement - a search that only jitters +/-8" around the ideal
# point can find EVERY candidate in that narrow window illegal while the
# rest of the same edge (just further from the "ideal" spot) is wide open.
# "Deploy somewhere, even if not perfectly placed" beats "deploy nowhere"
# for this policy - the closest-to-target sort in _ingress_landing_
# candidates() still prefers a nearby spot on the rare board where one
# actually exists.
INGRESS_LANDING_DEPTH_STEPS_IN = (5.9, 4.0, 2.0, 0.3)
INGRESS_LANDING_LATERAL_STEP_IN = 3.0  # spacing between sampled points along an edge's full length
# _auto_ingress_squad() needs to reach candidates on OTHER edges too, not
# just whichever handful happen to be numerically closest to the target -
# a real gap found via the actual demo scene: the enemy's own deployment
# edge is typically packed with their own models (naturally - it's their
# home zone), so the closest-by-distance candidates can ALL be illegal
# (landing among those models) while plenty of room exists on a flank/back
# edge further down the sorted list. Each candidate check is cheap pure
# geometry (no line_of_sight calls), so trying dozens of them costs
# comfortably under the "feels frozen" budget even in the worst case.
INGRESS_LANDING_CANDIDATE_LIMIT = 60
# Rule 24.09 ([DEEP STRIKE]) lets a unit "be set up anywhere on the
# battlefield more than 8" from all enemy units" - not just inside the 6"
# edge margin the plain Ingress move is confined to. The engine has honoured
# that since the enemy-deployment-zone lock was lifted for it, but the AI's
# CANDIDATE SWEEP above never was: it only ever offers points on the four
# edges, so a Deep Strike unit could only ever be placed as if it had no such
# ability. Reported from a real game ("die reserven werden sehr schlecht
# platziert... tankbustas und kopter sind beides antitank einheiten, aber
# konnten beides nichts sehen") - the Deffkoptas have the ability, could have
# dropped next to the Crisis suits they are built to kill, and instead landed
# on a board edge 37" away. A coarse interior grid, sampled on top of the edge
# candidates rather than instead of them, so an edge spot still wins whenever
# it genuinely scores better.
DEEP_STRIKE_GRID_STEP_IN = 4.0
# How many of the candidates actually get the (line-of-sight heavy) threat
# score - see _ingress_landing_candidates() for why this is capped.
SCORED_LANDING_CANDIDATES = 45
# Resolution at which two landing spots count as doing equal damage - see
# _ingress_landing_score()'s return value.
LANDING_DAMAGE_BUCKET_PTS = 10.0


class AIMemory:
    """Small persistent bit of bookkeeping the AI driver needs that the
    engine itself doesn't track: which squads already chose "no action" this
    phase, for the two decision points where the engine has no "declined"
    concept of its own (Movement/Charge/Fight all mark a decision either way
    via moved_squad_ids/charged_squad_ids/fought_squad_ids - but there's no
    decline_shooting()/decline-before-rolling-a-charge equivalent, so without
    this the same squad would be re-offered the same "hold fire"/"don't even
    try to charge" choice every single keypress for the rest of the phase).
    Reset whenever the battle round/phase/active player changes."""

    def __init__(self):
        self._phase_key = None
        self.declined_shoot = set()
        self.declined_charge = set()
        self.declined_explosives = set()
        self.declined_arrokon = set()
        self.declined_disembark = set()
        self.declined_greater_good = set()
        self.declined_crushing_impact = set()
        self.declined_consolidate = set()
        # Rule 15.02 (Command Re-roll): id() of the dice_manager.pending_values
        # list already asked (and declined) about - NOT reset by _sync() like
        # the declined_* sets above, since it's scoped to one specific still-
        # pending roll, not a phase. A single value (not a set) is enough:
        # only one roll can ever be pending at a time, and a fresh roll always
        # gets a fresh list object (a new id()), so this naturally "resets"
        # itself the moment the roll changes - no unbounded growth, no risk of
        # a stale id() (from a long-since-garbage-collected list) coincidentally
        # matching a new one over a long session.
        self.last_asked_reroll_id = None
        # The strategic planning phase's result for the player's CURRENT own
        # turn (see _maybe_generate_turn_plan()) - ai/claude_agent.py's
        # sanitized {"turn_intent": str, "unit_plans": {squad_name: {...}}}
        # shape, or None before the first Movement-phase decision of a turn
        # generates one. Deliberately tracked with its own _turn_key, coarser
        # than _phase_key below (battle_round+active_player, no phase) - the
        # plan is meant to survive Movement->Shooting->Charge->Fight of the
        # SAME own turn, not reset on every phase change like declined_*.
        self.turn_plan = None
        # The planning call runs on a background thread so the pygame loop
        # keeps rendering while it's in flight (see _maybe_generate_turn_plan()).
        # `turn_plan_thread` is non-None only while one is actually running.
        self.turn_plan_thread = None
        self.turn_plan_result = None
        # Which phase the plan was last checked against the board (see
        # _revalidate_plan_for_phase()) - a plan written in the Movement phase
        # is read again in Shooting, Charge and Fight, by which time the units
        # it names may be dead.
        self._plan_validated_phase = None
        # Event-driven re-planning (see _maybe_replan_after_events()): the
        # names of the enemy units that were on the board when this turn's
        # plan was written, how many re-plans this turn has already spent,
        # and whether something has since happened that invalidates it.
        self.plan_observation = None
        self.plan_enemy_snapshot = None
        self.replans_used = 0
        self.replan_requested = False
        self.charge_failed_this_turn = False
        self._turn_key = None

    def _sync(self, turn_tracker):
        key = (turn_tracker.battle_round, turn_tracker.phase, turn_tracker.active_player)
        if key != self._phase_key:
            self._phase_key = key
            self.declined_shoot = set()
            self.declined_charge = set()
            self.declined_explosives = set()
            self.declined_arrokon = set()
            self.declined_disembark = set()
            self.declined_greater_good = set()
            self.declined_crushing_impact = set()
            self.declined_consolidate = set()

    def _sync_turn_plan(self, turn_tracker):
        key = (turn_tracker.battle_round, turn_tracker.active_player)
        if key != self._turn_key:
            self._turn_key = key
            self.turn_plan = None
            # A plan still in flight belongs to the turn that just ended - let
            # the (daemon) thread finish into a result dict nothing reads any
            # more, rather than adopting last turn's orders for this turn.
            self.turn_plan_thread = None
            self.turn_plan_result = None
            self._plan_validated_phase = None
            self.plan_observation = None
            self.plan_enemy_snapshot = None
            self.replans_used = 0
            self.replan_requested = False
            self.charge_failed_this_turn = False

    @property
    def is_planning(self):
        """True while the turn plan is still being generated - main.py shows
        an indicator, and take_one_action() holds off acting until it lands."""
        return self.turn_plan_thread is not None and self.turn_plan_thread.is_alive()


def _all_squads(all_tokens):
    return {t.squad for t in all_tokens if t.squad is not None}


def _squad_by_name(name, all_tokens):
    for squad in _all_squads(all_tokens):
        if squad.name == name:
            return squad
    return None


def _centroid(squad):
    n = len(squad.models)
    return (sum(m.x_in for m in squad.models) / n, sum(m.y_in for m in squad.models) / n)


def _nearest_enemy_squad(squad, all_tokens):
    enemies = [s for s in _all_squads(all_tokens) if s.owner != squad.owner and s.models]
    if not enemies:
        return None
    return min(enemies, key=lambda e: squad.min_distance_to(e))


def _charge_roll_probability(needed):
    """Percent chance that 2D6 comes up `needed` or higher - the odds behind
    a charge declaration (see _handle_charge()). Counted off the 36 equally
    likely 2D6 outcomes rather than approximated, since the whole point is to
    give Claude a number it can actually weigh."""
    if needed <= 2:
        return 100.0
    if needed > 12:
        return 0.0
    hits = sum(1 for a in range(1, 7) for b in range(1, 7) if a + b >= needed)
    return 100.0 * hits / 36.0


# How many extra planning calls one turn may spend reacting to events. Two is
# enough for the cases that actually matter (a kill, then a failed charge)
# while keeping the cost of a turn bounded and predictable.
MAX_REPLANS_PER_TURN = 2


def _maybe_replan_after_events(memory, player, state, turn_tracker, game_log=None):
    """Throw the turn plan away and write a new one when something has
    happened that the old one could not have accounted for.

    The two triggers are the user's own call ("Eigentlich kann der Plan
    nachgezogen werden, wenn eine gegnerische Einheit stirbt oder ein Charge
    nicht klappt. damit sind die meisten Faelle abgedeckt"), and they are well
    chosen: both change the situation in a way no amount of deterministic
    clean-up can repair. A dead enemy frees up every unit that was pointed at
    it - that is a re-allocation decision, not a correction - and a failed
    charge leaves a unit standing in the open where the plan assumed it would
    be in combat.

    Deliberately NOT a re-plan before every action (which is what was
    originally proposed): measured at 15-25 decisions per AI turn, that is
    15-25 calls on the expensive planning model instead of one, and it
    dissolves the plan's actual job - allocating work ACROSS units - into a
    sequence of locally sensible, globally incoherent choices. This keeps one
    coordinating plan and re-writes it when it stops matching the board.

    Does not stall anything: the existing plan stays in force while the new
    one is computed on its background thread (see _maybe_generate_turn_plan()),
    so the worst case is a few decisions made on slightly stale orders."""
    if memory.turn_plan is None or memory.replan_requested:
        return  # nothing to replace yet, or one is already queued
    if turn_tracker.turn_owner != player:
        return  # only worth re-planning a turn we are actually playing
    if memory.replans_used >= MAX_REPLANS_PER_TURN:
        return

    reason = None
    enemies_now = {s.name for s in _all_squads(state.tokens) if s.owner != player}
    if memory.plan_enemy_snapshot is not None:
        killed = memory.plan_enemy_snapshot - enemies_now
        if killed:
            reason = f"{', '.join(sorted(killed))} destroyed"
    if reason is None and memory.charge_failed_this_turn:
        reason = "a charge failed"

    if reason is None:
        return
    memory.charge_failed_this_turn = False
    memory.replans_used += 1
    memory.replan_requested = True
    if game_log is not None:
        game_log.add(f"{player}: re-planning the rest of the turn ({reason}).")


def _revalidate_plan_for_phase(memory, player, state, turn_tracker, game_log=None):
    """Re-run the deterministic plan checks whenever the phase changes.

    A turn plan is written once, in the Movement phase, and then read again by
    Shooting, Charge and Fight - by which point the board has moved on: named
    targets die, transports blow up, charges fail. That is real open-loop
    staleness (user: "vielleicht reicht es nicht, einen Plan am Anfang der
    Runde zu formulieren und dann nach und nach auszufuehren, weil ja viele
    zufaellige Aktionen auch im Spiel waehrend des Zuges sind").

    This is the free half of the answer: _validate_turn_plan() is pure
    engine-side arithmetic with no API call at all, so running it again at
    every phase boundary costs nothing and clears out whatever has since
    become impossible. It does NOT rewrite intent - a plan that has gone
    stale in substance rather than legality still needs a real re-plan."""
    if memory.turn_plan is None:
        return
    if memory._plan_validated_phase == turn_tracker.phase:
        return
    memory._plan_validated_phase = turn_tracker.phase
    _validate_turn_plan(memory.turn_plan, player, state, turn_tracker, game_log)


def _current_unit_plans(memory):
    """This turn's per-squad plan entries (see _maybe_generate_turn_plan()),
    or None before one exists. The plan is cached for the player's whole turn
    on purpose, so Shooting and Charge read the SAME plan the Movement phase
    was steered by - a squad told to attack one enemy unit should move at it,
    shoot it and charge it, not re-decide from scratch each phase."""
    return memory.turn_plan["unit_plans"] if memory.turn_plan else None


def _planned_position(squad, plan):
    """The bare (x, y) this turn's plan gave `squad`, or None.

    Complements _planned_enemy_target()/_planned_objective(): those can only
    resolve things that HAVE a name, which left the plan unable to express any
    instruction about a place - the exact gap the user described for terrain
    ("hinter Mauer XY", where the wall has no name to refer to)."""
    entry = plan.get(squad.name) if plan else None
    return entry.get("position") if entry else None


def _distance_from_squad_to_point(squad, point):
    return min(
        ((m.x_in - point[0]) ** 2 + (m.y_in - point[1]) ** 2) ** 0.5 - m.radius_in
        for m in squad.models
    )


def _reach_origin(squad):
    """Where this unit's move actually starts from.

    For a passenger that is the TRANSPORT, not its own models: rule 18.02 puts
    an embarked unit off the battlefield and nothing maintains its coordinates
    while it rides (measured on the demo scene: one passenger squad's centroid
    sat 11" from its own Trukk, another 30" from its Devilfish). _reach_to_point()
    already knew this; the clamp in _validate_turn_plan() did not - it measured
    the distance from the transport and then projected the shortened order from
    the stale centroid, so the "as far along that line as it can reach" point was
    computed along a line starting in the wrong place."""
    transport = getattr(squad, "embarked_in", None)
    if transport is not None:
        return transport.x_in, transport.y_in
    return _centroid(squad)


def _reach_to_point(squad, point, allow_advance=False):
    """(gap, reach) for "can this unit get to `point` this turn?".

    `allow_advance` counts rule 09.06's Advance as a way of getting there, and
    is passed by the two places that judge a PLAN's position order. It was the
    missing half of a loop that had closed on itself: the planner is told its
    position must lie inside a circle of radius M, this function clamps
    anything outside that circle back onto it, and the tactical layer only
    builds an Advance option when the commanded point is further away than a
    plain move. So no plan could ever ask for the extra D6, and none did -
    measured over the reported WAAAGH! turn, six units were ordered to
    "advance" and exactly one of them was offered an Advance (the only one
    whose plan named no position at all). Advancing is always LEGAL; whether
    it is worth its cost is a judgement, and the observation now states that
    cost (see ai/observation.py's advance_reach_in()) instead of this function
    pre-empting it.

    Split out because an EMBARKED unit has to be measured differently, and
    measuring it like an on-board one produced a real, expensive mistake. A
    passenger's own model coordinates are not maintained while it rides - the
    same fact if_you_disembark() was built around, where one squad was found
    sitting 30" from its own transport - so the gap came out of stale positions.

    Observed: the plan ordered "2 Boyz 2 + Warboss" to (36,33) to disembark and
    charge the Stealth Battlesuits under WAAAGH. Measured from those stale
    coordinates that read as 17" against a 6" move, so the clamp rewrote the
    order to (34,21). From the TRANSPORT, at roughly (38,22), the same point was
    about 11" - comfortably inside 3" of disembark plus the unit's own 6" move.
    The order was never unreachable; the unit disembarked anyway, on an order
    whose whole purpose the clamp had just removed, and stood in the open.

    So: for a passenger, measure from where it would actually step out, and
    allow the disembark distance on top of its own movement."""
    transport = getattr(squad, "embarked_in", None)
    if transport is not None:
        gap = ((transport.x_in - point[0]) ** 2 + (transport.y_in - point[1]) ** 2) ** 0.5
        # One definition of "how much closer getting out puts you", shared with
        # the threat numbers in ai/observation.py. Both used to state it
        # separately and only this one had it right, which is why a passenger's
        # "best_targets_for_you" came out empty several inches too early.
        # Algebraically what this line always did (hull radius off the gap plus
        # 3" onto the reach), just no longer said twice.
        reach = observation.advance_reach_in(squad) if allow_advance else min_model_movement(squad)
        return max(0.0, gap - observation.disembark_reach_in(transport)), reach
    reach = observation.advance_reach_in(squad) if allow_advance else min_model_movement(squad)
    return _distance_from_squad_to_point(squad, point), reach


def _planned_enemy_target(squad, plan, all_tokens):
    """The enemy squad this turn's plan (see _maybe_generate_turn_plan())
    named as `target` for `squad`, or None if it named nothing, named an
    objective instead, or named something that no longer exists (a unit wiped
    out since the plan was made, or a name the planner simply got wrong).

    The plan is deliberately allowed to go stale rather than be re-generated:
    resolving it by name every time means a target that dies mid-turn just
    quietly stops being offered, instead of the tactical layer trying to act
    on a squad that isn't there any more."""
    if not plan:
        return None
    entry = plan.get(squad.name)
    if entry is None:
        return None
    target_name = (entry.get("target") or "").strip()
    if not target_name:
        return None
    target = _squad_by_name(target_name, all_tokens)
    if target is None or target.owner == squad.owner or not target.models:
        return None
    return target


def _planned_objective(squad, plan, objectives):
    """The mission objective this turn's plan named as `target` for `squad`,
    or None if it named nothing, named an enemy unit instead, or named an
    objective that doesn't exist.

    Real gap found via user report ("der ghostkeel sollte zum central
    objective rücken - nicht gemacht", "das strike team sollte ebenfalls
    richtung mitte vorrücken - nicht gemacht"), with the plan screenshot
    showing both squads assigned target "Central Objective": the plan's
    `target` is very often an OBJECTIVE, not an enemy squad, and while
    _planned_enemy_target() correctly refuses to resolve an objective name,
    NOTHING then used it either. The only objective option ever offered came
    from _best_objective_target() - the driver's OWN heuristic pick (nearest
    uncontrolled first) - so a plan naming a different objective was simply
    unfollowable. Reproduced from the log: the Ghostkeel, ordered to the
    Central Objective at ~(27.5, 34.8), was offered No Man's Land (NE) at
    (37.5, 22.2) instead - right next to where it stood - and ended the turn
    sitting on that one."""
    if not plan or not objectives:
        return None
    entry = plan.get(squad.name)
    if entry is None:
        return None
    target_name = (entry.get("target") or "").strip()
    if not target_name:
        return None
    for objective in objectives:
        if objective.name == target_name:
            return objective
    return None


# Half-width margin added to a vehicle's own radius when working out which
# friendly squads are standing in its way (see _vehicle_corridors()).
VEHICLE_CORRIDOR_MARGIN_IN = 1.0


def _needs_open_ground(squad):
    """Units that need real room among their OWN army to manoeuvre - the
    property the movement ordering and corridor reservation care about.

    Rule 13.06 gives INFANTRY (and BEASTS/SWARM) a free pass through Dense
    terrain; everything else is a wide, awkward base that its own infantry can
    box in. Reported case: Ork Warbikers are `infantry=False, vehicle=False` -
    so they had every problem a vehicle has and none of the handling, because
    both the vehicle-first ordering and the corridor reservation tested
    `profile.vehicle`. User: "ich glaube der kommt nicht gut mit mauern
    zurecht, weil er nicht durchfahren kann."

    Deliberately NOT the same question as _blocked_by_walls() below, and the
    two have since diverged. The wall-crossing house rule
    (config.VEHICLES_CROSS_WALLS) lets the AI's vehicles drive through Dense
    terrain, but it does not make them any narrower: a Battlewagon still needs
    its own Meganobz to get out of the lane, so the ordering must keep
    treating it as a unit that needs space."""
    return bool(squad.models) and not any(
        m.profile.infantry or m.profile.beasts or m.profile.swarm for m in squad.models
    )


def _blocked_by_walls(squad):
    """Whether Dense terrain actually stops this unit - "must it go around a
    wall?", which is a different question from _needs_open_ground()'s "does it
    need room?".

    Asked through the same seam every mover, route search and clamp uses
    (Obstacle.blocks_movement_for), so it cannot disagree with them. That
    matters because of the wall-crossing house rule
    (config.VEHICLES_CROSS_WALLS, keyed on the OWNER): the rule reached
    MovementController.clamp_move() and pathfinding.blocking_obstacles_for()
    the day it was written, but this file went on deciding "must go around"
    from the INFANTRY/BEASTS/SWARM keywords alone. So the AI kept planning
    detours it no longer needs and, worse, kept telling itself so - the charge
    option text said in as many words that a unit "cannot cross the terrain in
    between and has to go around it" about a vehicle that now drives straight
    through. Measured on map 2: 0 of 14 Dense features block a Player 2
    Battlewagon, Warbiker or Deff Dread, and all 14 still block Player 1's.

    User: "wir haben mal geaendert, dass sich Fahrzeuge jetzt durch Waende
    bewegen duerfen... Es kommt mir nicht so vor, als ob die das auch nutzen.
    Sicher, dass diese Aenderung auch wirklich angekommen ist." - it had, for
    the mover; this is the half of the codebase it had not reached."""
    if not squad.models:
        return False
    probe = Obstacle(0.0, 0.0, 1.0, 1.0, DENSE)
    return any(probe.blocks_movement_for(m) for m in squad.models)


# How much further than the straight line a routed charge may be before the
# detour is worth reporting at all - below this the two are the same answer.
CHARGE_DETOUR_REPORT_IN = 1.0


def _charge_gap(squad, target, movement_controller):
    """The distance this squad's charge actually has to cover to reach
    `target` - the straight line for a unit that may cross Dense terrain,
    the ROUTED distance for one that may not.

    Rule 11.04 measures target eligibility as a straight line ("within 12" of
    your unit AND within the maximum distance"), and that stays untouched - a
    player is allowed to declare a charge round a corner and fail it. What was
    wrong is the AI's own ODDS: they were computed from that same straight line
    for every unit, so a walker with a wall between it and its target was told
    it needed an 8+ when no roll at all could have got it there. Reported case:
    the Deff Dread declared a charge on Kroot Carnivores 2 at a 7.2" straight-
    line gap, rolled 9", and failed all 13 approach directions, because rule
    13.06 makes it go around a Dense wall that put the real path past 12".

    Reuses game/pathfinding.py's find_route(), the same search the movement
    side already trusts, and falls back to the straight line whenever no route
    is found.

    Known limit, measured rather than assumed: this is a LOWER bound on the
    real distance, not a guarantee. find_route() searches on a 1" grid for a
    point mover and does not model the engagement-position and overlap checks
    the charge itself still has to pass, so it can report a way through that
    the charge cannot quite take. On the reported case it returns 8.4" (needing
    9+ rather than the straight line's 8+, and flagging the detour) where the
    charge in fact could not be completed at any roll. It makes the odds less
    wrong, not exact."""
    gap = squad.min_distance_to(target)
    if not _blocked_by_walls(squad) or not squad.models or not target.models:
        return gap
    mover, enemy = min(
        ((a, b) for a in squad.models for b in target.models),
        key=lambda pair: edge_distance(pair[0], pair[1]),
    )
    hard_obstacles = pathfinding.blocking_obstacles_for(mover, movement_controller.obstacles)
    # Everything except the ONE model being charged stays an obstacle,
    # including the rest of the target's own squad: a 10-model mob is a wall of
    # bases, and a route threading through it is not one the charge could take.
    others = [t for t in pathfinding.enemy_models_for(mover, movement_controller.all_tokens)
              if t is not enemy]
    route = pathfinding.find_route(
        (mover.x_in, mover.y_in), (enemy.x_in, enemy.y_in), mover.radius_in,
        CHARGE_RANGE_IN + gap, hard_obstacles, others,
        movement_controller.board_width_in, movement_controller.board_height_in,
    )
    if not route:
        return gap
    length, prev = 0.0, (mover.x_in, mover.y_in)
    for point in route:
        length += ((point[0] - prev[0]) ** 2 + (point[1] - prev[1]) ** 2) ** 0.5
        prev = point
    # find_route() aims at the enemy's CENTRE; the charge only has to close to
    # edge contact, so both base radii come back off the routed length.
    return max(gap, length - mover.radius_in - enemy.radius_in)


def _squad_goal_point(squad, all_tokens, plan):
    """Where this squad is trying to get to: its plan position, else its plan
    target, else the nearest enemy. None if it has nowhere to go.

    Deliberately ONE function used by both _vehicle_corridors() and
    _predicted_centroid_after_move(): the two were deriving the goal slightly
    differently, and the corridor logic silently broke because of it - the
    vehicle's lane was computed toward the nearest enemy while the blocker's
    predicted move was computed toward its plan position, so the two were
    measured against different geometry and a squad heading straight up the
    lane looked like it was leaving it."""
    goal = _planned_position(squad, plan)
    if goal is not None:
        return goal
    target = _planned_enemy_target(squad, plan, all_tokens)
    if target is None:
        target = _nearest_enemy_squad(squad, all_tokens)
    if target is None or not target.models:
        return None
    return _centroid(target)


def _vehicle_corridors(all_tokens, player, plan=None):
    """For each of `player`'s own VEHICLE squads, the strip of board it needs
    to drive through this turn: (origin, unit direction, length, half-width).

    Used to decide movement ORDER, not legality - see _movement_priority_key()
    for why neither "vehicles first" nor "vehicles last" is right on its own."""
    corridors = []
    for squad in _all_squads(all_tokens):
        if squad.owner != player or not squad.models:
            continue
        if not _needs_open_ground(squad):
            continue
        goal = _squad_goal_point(squad, all_tokens, plan)
        if goal is None:
            continue
        cx, cy = _centroid(squad)
        dx, dy = goal[0] - cx, goal[1] - cy
        span = (dx * dx + dy * dy) ** 0.5
        if span < 1e-9:
            continue
        radius = max(m.radius_in for m in squad.models)
        corridors.append((
            (cx, cy), (dx / span, dy / span),
            min(span, min_model_movement(squad)),
            radius + VEHICLE_CORRIDOR_MARGIN_IN,
        ))
    return corridors


def _point_in_corridor(x_in, y_in, radius_in, corridor):
    (ox, oy), (ux, uy), length, half_width = corridor
    rx, ry = x_in - ox, y_in - oy
    along = rx * ux + ry * uy
    if not (0.0 <= along <= length):
        return False
    return abs(-rx * uy + ry * ux) <= half_width + radius_in


def _squad_in_corridor(squad, corridor):
    return any(_point_in_corridor(m.x_in, m.y_in, m.radius_in, corridor) for m in squad.models)


def _predicted_centroid_after_move(squad, all_tokens, plan):
    """Roughly where this squad ends up if it moves toward its own goal -
    plan position, else plan target, else the nearest enemy."""
    cx, cy = _centroid(squad)
    goal = _squad_goal_point(squad, all_tokens, plan)
    if goal is None:
        return (cx, cy)
    dx, dy = goal[0] - cx, goal[1] - cy
    span = (dx * dx + dy * dy) ** 0.5
    if span < 1e-9:
        return (cx, cy)
    travel = min(span, min_model_movement(squad))
    return (cx + dx / span * travel, cy + dy / span * travel)


def _clears_a_vehicle_path(squad, corridors, all_tokens, plan):
    """Would moving this squad FIRST actually free a vehicle's road?

    Standing in the corridor is not enough. Real case from the log, exactly
    as the user described it ("Zuerst hat sich der Strike Squad in den Weg
    gestellt, und dann war der Devilfish dran und hatte keinen Platz"):
    Strike Team 2 was correctly identified as a blocker and correctly moved
    first - but its OWN goal lay in the same direction as the Devilfish's, so
    it advanced from behind the transport to (12.6, 12.3), directly in front
    of it, and the Devilfish got no further than (12.8, 5.0). Moving a blocker
    first only helps if the blocker actually LEAVES; one whose destination is
    still inside the corridor is better off going after the vehicle, which by
    then has driven clear and left the road open behind it."""
    blocks_something = False
    for corridor in corridors:
        if not _squad_in_corridor(squad, corridor):
            continue
        blocks_something = True
        px, py = _predicted_centroid_after_move(squad, all_tokens, plan)
        radius = max(m.radius_in for m in squad.models)
        (ox, oy), (ux, uy), _length, half_width = corridor
        # Sideways out of the lane, specifically. Testing "is the destination
        # still inside the corridor box" is not enough: a blocker travelling
        # the SAME direction as the vehicle leaves the box through its far
        # end, which clears nothing - it has only pushed the obstruction
        # further down the road, which is precisely what happened in the
        # reported case. Only lateral separation actually frees the lane.
        rx, ry = px - ox, py - oy
        if abs(-rx * uy + ry * ux) <= half_width + radius:
            return False  # still in the lane afterwards - let the vehicle go first
    # Every lane it stands in, it also leaves. Checking ALL of them matters
    # with more than one vehicle on the board: returning on the first corridor
    # cleared would wave a squad through that is still blocking the second.
    return blocks_something


def _disembark_zones(all_tokens, player, plan, embarked_squads=()):
    """Discs around this player's own loaded transports that other squads
    should keep out of, as (centre, radius).

    User request: "bei transportern waere schlau, dass sie generell etwas
    abstand halten. ausserdem sollten im weg stehende einheiten vor dem
    disembark versuch wegbewegt werden. oder auch sich nicht direkt neben
    transporter stellen, die einen disembark befehl haben."

    All three are the same underlying need: a squad can only disembark into
    space that is actually free, and the reported failures were four
    consecutive "could not be placed after disembarking" for two Trukks whose
    surroundings were packed with their own army. The radius covers where the
    passengers have to physically stand - the transport's own base plus the
    rule 18.04 placement distance plus a model's width."""
    zones = []
    for squad in embarked_squads:
        transport = getattr(squad, "embarked_in", None)
        if transport is None or transport.squad is None or transport.squad.owner != player:
            continue
        if not squad.models:
            continue
        entry = plan.get(squad.name) if plan else None
        # Any loaded transport gets a little room; one under orders to unload
        # gets the full ring its passengers will need.
        wanted = 3.0 if entry is None or entry.get("role") != "disembark" else DISEMBARK_DISTANCE_IN.get("tactical", 3.0)
        zones.append((
            (transport.x_in, transport.y_in),
            transport.radius_in + wanted + 2 * max_model_radius(squad),
        ))
    return zones


def _stands_in_disembark_zone(squad, zones):
    for (cx, cy), radius in zones:
        for model in squad.models:
            if ((model.x_in - cx) ** 2 + (model.y_in - cy) ** 2) ** 0.5 <= radius + model.radius_in:
                return True
    return False


def _takes_someone_elses_spot(squad, all_tokens, plan):
    """Would this room-needing squad's own destination land on the spot ANOTHER
    friendly squad has been ordered to occupy?

    The mirror of the corridor rule, and the case it missed. The corridor logic
    clears a lane FOR a vehicle; nothing stopped a vehicle from parking ON the
    ground the infantry behind it was ordered to take. Observed in a real turn 3:
    Trukk 1 was told to "screen for Meganobz/Boyz", moved first because vehicles
    sort early, stopped at (22.9,23.8) - and the Meganobz, ordered to (24,27),
    then had ten placements rejected in a row and stood still for the turn
    ("in zug 3 sind fast alle squads stehen geblieben").

    Only a squad with an explicit planned position counts as displaced: that is
    a destination somebody committed to, not a guess, so yielding to it cannot
    trade a good move for a speculative one."""
    if not plan:
        return False
    goal = _squad_goal_point(squad, all_tokens, plan)
    if goal is None:
        return False
    clearance = max_model_radius(squad) + _SPOT_CONFLICT_MARGIN_IN
    for other in {t.squad for t in all_tokens if t.squad is not None}:
        if other is squad or other.owner != squad.owner or not other.models:
            continue
        spot = _planned_position(other, plan)
        if spot is None:
            continue
        if ((goal[0] - spot[0]) ** 2 + (goal[1] - spot[1]) ** 2) ** 0.5 <= clearance:
            return True
    return False


def _movement_priority_key(squad, all_tokens, plan=None, corridors=(), disembark_zones=()):
    """User-requested ordering fix: process a player's OWN squads
    frontmost-first (closest to their nearest enemy first), not just
    alphabetically by name - a squad further back that happens to move
    first can otherwise claim the exact ground a more forward squad
    actually needed room to advance into, forcing the forward squad's own
    _advance_toward() to detour more (or, on a sufficiently cramped board,
    fail outright) than if it had simply gone first. Squads with no enemy
    left on the board (or none at all) sort last (float('inf')) - there's
    no "front" to speak of for them, so they shouldn't get priority over
    squads that actually have somewhere to go. `squad.name` is a pure
    tie-breaker, purely for a deterministic order between equally-close
    squads.

    Real, related bug found via user report ("die KI kommt mit der
    Bewegung von großen Fahrzeugen nicht klar") plus a fully faithful
    reproduction against the real demo scene/army: a VEHICLE squad (e.g.
    the Devilfish, base radius 2.1" vs ~0.6-1.0" for the infantry around
    it) moving LAST among its own army - which the distance-only sort
    above would do here, since it starts deep in its own deployment zone,
    farthest from any enemy - lets every smaller, more maneuverable
    squadmate claim ground in front of it FIRST each movement phase.
    _route_around_waypoints()'s corner-/model-routing (see its own
    docstring) can route around ONE or a few blockers, but reproduced
    directly: once several squads have already converged on nearby
    objectives ahead of it, the Devilfish can end up surrounded by a dozen
    or more friendly models plus terrain all at once - genuinely no single
    waypoint routes around ALL of that, this file's bounded heuristics are
    deliberately not a real pathfinder. Moving VEHICLE squads (own no
    INFANTRY/BEASTS/SWARM/MOBILE Dense-terrain pass-through either, so
    they're the squads most likely to need room) BEFORE the rest of the
    army every phase - a squad is "vehicle-priority" only if EVERY model in
    it has the VEHICLE keyword, same all() convention as is_monster_or_
    vehicle_unit() - means the board is still relatively open when they
    get their turn, letting the smaller/more nimble squads (which also
    aren't blocked by Dense terrain at all, rule 13.06) route around
    WHATEVER the vehicle ends up doing afterward, rather than the other
    way around. Complements, not replaces, the corner-/model-routing fix -
    that still matters for whatever a vehicle squad's OWN nearest
    vehicle-priority squadmate (if any) is doing, or for the single
    obstacle/model still directly in its way even when it moves first.

    `plan` (the strategic planning phase's sanitized `unit_plans` dict, see
    AIMemory.turn_plan/_maybe_generate_turn_plan() - None by default, so
    this function is unchanged when no plan exists yet): if given AND it has
    an entry for this squad, that entry's own `priority` integer becomes the
    DOMINANT sort key (lower moves first, per the plan's own instructions to
    Claude) - the vehicle/distance heuristic above still breaks ties among
    multiple planned squads that happen to share the same priority. A squad
    the plan doesn't mention (an incomplete/malformed plan, or one Claude
    simply skipped) sorts after every planned squad, keeping its relative
    order among other unplanned squads exactly as before - this is a strict
    generalization of the pre-existing tuple, not a behavior change, whenever
    `plan` is None or doesn't cover a given squad."""
    is_vehicle = _needs_open_ground(squad)
    # Three tiers, not two. "Vehicles first" is right when the road ahead is
    # clear and wrong when the vehicle is boxed in by its own infantry - and
    # "vehicles last" has the mirror problem. The user put it exactly right:
    # "Manchmal ist es besser, erst die grossen Basen zu moven, aber oft ist
    # es auch besser, erst mit den kleinen Platz zu machen, um die Bewegung
    # der grossen Basis ueberhaupt erst zu ermoeglichen."
    #
    # So this is not a size question at all, it's a DEPENDENCY question: the
    # squads that are standing in a vehicle's path AND whose own move takes
    # them out of it go first (they are what actually clears - see
    # _clears_a_vehicle_path(), and note that merely standing in the way is
    # not enough: a blocker heading the same direction as the vehicle just
    # advances deeper into the corridor), the vehicle goes next into the room they
    # just made, and everyone else follows. A squad only earns tier 0 by
    # actually sitting inside a vehicle's corridor this turn, so on an open
    # board no squad does and the ordering collapses back to the old
    # vehicles-first behaviour.
    if is_vehicle and _takes_someone_elses_spot(squad, all_tokens, plan):
        # Room-needing, but headed for ground somebody else was ordered to hold:
        # go LAST, so the squad that was sent there gets it. Deliberately only a
        # demotion of this one squad and not a general rule - on open ground no
        # destination collides, so the ordering falls straight back to
        # vehicles-first (see _takes_someone_elses_spot()).
        tier = 2
    elif is_vehicle:
        tier = 1
    elif disembark_zones and _stands_in_disembark_zone(squad, disembark_zones):
        # Standing where a transport's passengers have to be placed - move
        # first, so the space is clear by the time the disembark is attempted.
        tier = 0
    elif corridors and _clears_a_vehicle_path(squad, corridors, all_tokens, plan):
        tier = 0
    else:
        tier = 2
    vehicle_priority = tier
    nearest = _nearest_enemy_squad(squad, all_tokens)
    distance = squad.min_distance_to(nearest) if nearest is not None else float("inf")
    plan_entry = plan.get(squad.name) if plan else None
    plan_priority = plan_entry["priority"] if plan_entry is not None else _UNPLANNED_MOVE_PRIORITY
    # VEHICLE ahead of the plan's own priority, not behind it. The plan's
    # `priority` says which unit's JOB matters most; it says nothing about
    # who physically needs room first, and letting it dominate re-created
    # exactly the traffic jam the vehicle rule above exists to prevent -
    # user report: "Der Planner hat dem Devilfish gesagt, dass er Richtung
    # Central Objective fliegen soll. Er ist aber nur nach rechts geflogen...
    # Der Weg war verstopft von Fire-Warrior-Variern. Ich glaube, generell
    # waere es gut, erst die dicken Sachen zu bewegen und dann die kleinen."
    # Reordering only changes the SEQUENCE units move in, never what each one
    # is told to do, so the plan loses nothing by yielding here.
    return (vehicle_priority, plan_priority, distance, squad.name)


def _translate_squad_toward(movement_controller, squad, target_point, max_distance):
    """Move every model in squad by the SAME offset toward target_point, capped
    at max_distance - clamped per-model through clamp_move()/
    try_commit_segment(), the exact primitives InputManager uses for a
    human's mouse drag, so terrain/board-edge/enemy-model blocking (and,
    since the "Umbau Bewegung" instant-validation change, friendly-model
    overlap and disallowed-enemy-engagement too) still applies.

    Returns True only if the translation came out RIGID, i.e. every model
    actually took the shared offset.

    That return value matters, and its absence was a real defect: this
    docstring used to claim squad shape and coherency were "preserved by
    construction", which is true of a rigid translation and NOT true of what
    this function does. The per-model clamp above can stop one model dead
    (terrain, an enemy base, a squadmate) while its squadmates travel the full
    offset, and the formation splits. Measured on the boxed-in Tankbustas from
    logs/game_20260808_213013.log: a requested 6" translation moved the
    centroid 1.00" and broke coherency outright.

    _creep_toward()'s whole correctness argument rests on the invariant this
    breaks, so it now asks for the flag rather than assuming it."""
    cx, cy = _centroid(squad)
    dx, dy = target_point[0] - cx, target_point[1] - cy
    dist = (dx * dx + dy * dy) ** 0.5
    if dist <= 1e-9 or max_distance <= 0:
        return False
    move = min(dist, max_distance)
    scale = move / dist
    ox, oy = dx * scale, dy * scale
    rigid = True
    for model in squad.models:
        wanted = (model.x_in + ox, model.y_in + oy)
        new_x, new_y = movement_controller.clamp_move(model, wanted[0], wanted[1])
        model.x_in, model.y_in = new_x, new_y
        movement_controller.try_commit_segment(model)
        if abs(model.x_in - wanted[0]) > 1e-6 or abs(model.y_in - wanted[1]) > 1e-6:
            rigid = False
    return rigid


# Real user report ("die KI spielt extrem passiv... bleibt mit den
# allermeisten Einheiten einfach immer stehen"): _translate_squad_toward()'s
# dead-straight rigid translation has no way to steer around whatever's
# directly in its path - fine for a sparse board, but with THIS army (10-
# model squads packed tightly in their own deployment zone) and terrain
# sitting between the lines, a straight line toward the nearest enemy walks
# straight into a wall or another already-placed unit for MOST squads.
# Confirmed via direct reproduction against the live demo scene: even an
# agent hard-coded to always pick "advance" still ended up not moving for
# 5 of 7 squads, because the one straight-line attempt failed and the
# existing "no repositioning retry" fallback just gave up and stayed put -
# that's what actually looked like passivity, not a cautious agent
# deliberately choosing to stand still. ADVANCE_ANGLE_JITTER_DEG sweeps
# progressively wider detours around the direct line (closest-to-target
# first), and ADVANCE_DISTANCE_FRACTIONS falls back to a shorter move only
# once no angle at all works at full range - same "bounded sampled search,
# not real pathfinding" style as the staging/ingress candidate searches.
ADVANCE_ANGLE_JITTER_DEG = (0.0, -20.0, 20.0, -40.0, 40.0, -60.0, 60.0, -90.0, 90.0, -120.0, 120.0, 180.0)
ADVANCE_DISTANCE_FRACTIONS = (1.0, 0.5, 0.25)

# How much of a move's realistically achievable distance (see consider() in
# _advance_toward_per_model()) an attempt has to actually cover before the
# sweep stops looking and confirms it. The old code had no such notion at
# all - it confirmed the first attempt that merely passed validation, which
# in practice meant a squad regularly "completed" its move having shuffled a
# single model forward an inch while the other nine stood still (reproduced
# straight out of the real game logs). Half of what was achievable is a
# deliberately forgiving bar: on open ground the very first plan now clears
# it outright (the whole squad travels its full distance), so this costs
# nothing in the common case and only keeps the sweep honest in cramped ones.
_GOOD_PROGRESS_FRACTION = 0.5
# How many of the best sub-par attempts to re-run at the end when no plan
# cleared the bar. Bounded because each retry re-runs a full placement plus a
# confirm; the list is score-sorted, so the first entries are the ones worth
# spending that on.
_MAX_FALLBACK_RETRIES = 3


def _rotate_point_around(cx, cy, x, y, angle_deg):
    rad = math.radians(angle_deg)
    dx, dy = x - cx, y - cy
    rx = dx * math.cos(rad) - dy * math.sin(rad)
    ry = dx * math.sin(rad) + dy * math.cos(rad)
    return cx + rx, cy + ry


def _advance_toward_bulk(movement_controller, squad, target_point, start_move_fn=None, confirm_fn=None, cancel_fn=None):
    """The whole squad as one rigid block: tries a bounded sweep of shared
    candidate directions/distances (see the module comment above) instead
    of giving up the moment the one direct line is blocked.
    movement_controller.select(squad.models[0]) must already have been
    called by the caller. Each attempt (re-)starts the move itself, since a
    failed attempt's cancel wipes remaining_range
    (MovementController._clear_move_state()) - re-priming it is required
    before every retry, not just the first. `start_move_fn`/`confirm_fn`/
    `cancel_fn` default to movement_controller's own start_move/confirm_move/
    cancel_move (a Normal Move) - _execute_fall_back() passes
    movement_controller.start_fall_back_move(mode)/fall_back_controller.
    confirm()/.decline() instead, so this same retry sweep can drive rule
    09.07's Fall Back move too (routing every attempt's confirm/cancel
    through FallBackController itself, not raw MovementController calls,
    matters there specifically for Desperate Escape's post-move Hazard
    Roll wiring - see FallBackController.confirm()) without duplicating the
    whole geometry for it. Whichever confirm_fn is used is expected to
    leave movement_controller.errors set on failure, same contract as
    confirm_move() itself.

    Returns True and leaves the squad moved there if any candidate
    succeeded; False if every one failed."""
    start = start_move_fn if start_move_fn is not None else movement_controller.start_move
    confirm = confirm_fn if confirm_fn is not None else movement_controller.confirm_move
    cancel = cancel_fn if cancel_fn is not None else movement_controller.cancel_move
    cx, cy = _centroid(squad)
    for fraction in ADVANCE_DISTANCE_FRACTIONS:
        for angle in ADVANCE_ANGLE_JITTER_DEG:
            start()
            max_distance = movement_controller.remaining_range.get(squad.models[0].id, 0.0) * fraction
            rotated_target = _rotate_point_around(cx, cy, target_point[0], target_point[1], angle)
            _translate_squad_toward(movement_controller, squad, rotated_target, max_distance)
            # "confirm_move() raised no error" is NOT the same as "the squad
            # moved". If every model got clamped back to where it started -
            # boxed in by terrain and friendly models, the common case in a
            # crowded midfield - the squad is simply standing where it began,
            # which was already legal, so confirm() has nothing to object to
            # and reports success at zero movement. Measured on a crowded
            # 254-scenario stress run: EVERY squad that ended up standing
            # still got there through this branch, and the creep fallback
            # below it was never reached once. Same false-success shape the
            # per-model placement paths were already fixed for.
            #
            # BOTH bars, not just distance covered. The angle sweep reaches all
            # the way to 180 degrees, so a candidate can carry the squad
            # sideways or straight backwards and still clear a displacement
            # bar - and because bulk then reports success, no further angle is
            # tried and _creep_toward() (which is strictly toward the target)
            # is never reached. That is a full turn spent driving away from the
            # objective. Reproduced in a blind alley open only to the rear: the
            # squad committed a move with -0.80" of goal progress. The
            # per-model stage got this same guard when the user reported
            # "manchmal bewegt sich der Devilfisch statt nach vorne einfach
            # sinnlos nach rechts"; the bulk stage never did, which is what
            # ended up moving the Warbikers backwards ("die bikes tun sich
            # extrem schwer durch das enge gelände vorzurücken und sind
            # eigentlich immer rechts stuck").
            progress, displacement = _squad_progress((cx, cy), _centroid(squad), target_point)
            if displacement < MIN_ROUTE_PROGRESS_IN or progress < MIN_GOAL_PROGRESS_IN:
                cancel()
                continue
            confirm()
            if not movement_controller.errors:
                return True
            cancel()
    return False


# Corner-routing fallback (see _route_around_waypoints()) - how far outside
# a blocking obstacle's own corner to aim, and how many of the nearest
# blocking obstacles get their corners tried at all (kept small: each one
# adds ADVANCE_DISTANCE_FRACTIONS more attempts, and this is only a bounded
# "aim past the corner" heuristic, not real pathfinding).
CORNER_ROUTE_CLEARANCE_IN = 0.3
CORNER_ROUTE_MAX_OBSTACLES = 3
# A waypoint barely different from where the model already stands isn't a
# real routing option - it's indistinguishable from "stay put" and would
# just get "successfully" re-picked forever (see _route_around_waypoints()'s
# own docstring for the real stall this caused before this filter existed).
MIN_ROUTE_PROGRESS_IN = 1.0
# A committed move has to actually close the gap to where it was going, not
# merely cover ground - see _advance_toward_per_model()'s consider().
MIN_GOAL_PROGRESS_IN = 0.5
# How many rings out from an Ingress drop point to look for model slots (see
# _ingress_pack_positions()). Enough room for a large squad plus blocked
# slots; beyond this the unit is no longer arriving where it was scored.
_INGRESS_PACK_RINGS = 4
# How far the WHOLE formation has to be able to advance along a route leg
# before a rigid routed move bothers taking it (see _place_rigid_route()):
# below this the squad is wedged and the remaining legs cannot help.
MIN_RIGID_LEG_IN = 0.25


def _route_around_waypoints(model, target_x, target_y, obstacles, movement_controller, squad):
    """User report ("die KI bewegt sich immer noch nicht wirklich nach
    vorne... den Devilfish hat sie gar nicht bewegt") plus the user's own
    correct diagnosis: a VEHICLE (no INFANTRY/BEASTS/SWARM/MOBILE keyword)
    cannot pass through Dense terrain at all (rule 13.05/13.06 -
    clamp_move()'s obstacle_fraction already enforces this correctly, cross
    referenced and confirmed directly: a straight line through a wall gets
    truncated right at its face, it does NOT let the model through). The
    actual gap is that _advance_toward_per_model()'s retry sweep only ever
    rotates the AIM around the far target_point - once a model ends up
    pressed flush against a wall, every one of those rotated aims still
    points back into the same wall for a wall of any real size, so it
    stalls there for every future call, never finding its way around.
    Confirmed directly: a test vehicle blocked by a 16"-tall wall advanced
    normally for one turn, then made ZERO further progress for the next two
    (position changing only in the 12th decimal place) - matching the
    user's real Devilfish, deployed a few inches from actual Dense ruin
    walls, ending up parked at the exact same coordinate turn after turn.

    Returns candidate waypoints for `model` to head toward instead, given
    whatever is actually blocking its straight path to (target_x,
    target_y) - sorted closest-to-the-original-target first. A simple,
    bounded "go around it" heuristic (not real pathfinding) - consistent
    with this file's existing style for movement heuristics (see e.g.
    _best_staging_point()'s own "bounded sampled search, not a true
    solver" precedent). Only the closest CORNER_ROUTE_MAX_OBSTACLES
    blockers of EACH kind (terrain, friendly models) are considered, to
    keep the number of extra attempts bounded.

    Real bug found while building this: the first version only offered the
    obstacle's 4 corners, each pushed diagonally outward - reproduced
    directly that this does NOT fix the stall at all, because reaching a
    "far side" corner from where the model is actually standing (typically
    flush against the NEAR face) requires a diagonal line that itself still
    crosses the obstacle's rectangle (e.g. blocked at (12.49, 1.5) by a wall
    spanning x=14-16 - a diagonal aim at the wall's far-side corner (17.8,
    9.8) crosses x=14-16 at a y still well within the wall's own y-range,
    so clamp_move() truncates it right back at the near face again, same as
    every angle-jitter attempt already did). Fixed by ALSO offering "slide
    along my current axis, then clear the obstacle's extent on the OTHER
    axis" waypoints - (my own x, just past the obstacle's y-range) and
    (my own y, just past the obstacle's x-range) - which stay on one
    constant coordinate the whole way, so the straight line to them can
    only ever run parallel to (never through) the obstacle's rectangle.
    Every candidate (corners included) is then filtered to keep only the
    ones ACTUALLY reachable in a straight line without crossing this or any
    OTHER blocking terrain/model - so a corner that happens to already be
    reachable directly is still offered too, just never a diagonal one that
    only looks reachable.

    Second real bug found while building this, only visible after the fix
    above: sorting purely by distance-to-the-original-target still picked
    the "(near-face x, my own y)" waypoint every time, since it's naturally
    the closest one to a target on the far side - but once the model is
    ALREADY sitting flush against that near face, that waypoint is barely
    different from where it already is, so it "succeeds" with next to no
    actual movement and the model stalls right back at the same spot next
    call. Fixed with MIN_ROUTE_PROGRESS_IN: a waypoint within 1" of the
    model's CURRENT position isn't a real routing option and is dropped
    before sorting - reproduced and confirmed this is what finally lets the
    "slide past the obstacle's extent" waypoints (the ones that actually
    matter) win out once the model is genuinely stuck.

    Third real, separate cause found via a fully faithful reproduction
    against the actual demo scene/army: even with the terrain-corner fix
    above, the real Devilfish (base radius 2.1", far larger than the
    ~0.6-1.0" infantry around it) still stalled - not on terrain this time,
    but on its OWN nearby army. _clamp_target_against_friendly_models()
    (rule 03.01: a model's base may pass through friendly models but never
    end atop one) already correctly blocks a straight line that would end
    on/through another Player 2 model - with several squads converging on
    similar objectives ahead of the Devilfish in the same movement-phase
    processing order (see _movement_priority_key()), and its own large
    radius inflating every other model's effective blocking radius, most
    directions ended up blocked by a FRIENDLY model, not a wall - the wall-
    only fix above had nothing to route around in that case. Fixed by also
    generating "step to one side of this specific blocking model" waypoints
    (perpendicular to the mover-to-target line, offset by both models'
    combined radius plus clearance) for each friendly model actually
    blocking the direct path (via the same segment_circle_entry_fraction()
    check MovementController.clamp_move()'s own enemy-model blocking
    already uses) - the same "go around the thing that's actually in the
    way" idea as the terrain corners, just for a circle instead of a
    rectangle. Every candidate is reachability-filtered against BOTH
    terrain AND every friendly blocker (not just the one that produced it),
    exactly like the terrain-only candidates already were."""
    mx, my = model.x_in, model.y_in
    blocking_obstacles = [
        o for o in obstacles
        if o.blocks_movement_for(model)
        and o.blocks_segment((mx, my), (target_x, target_y))
    ]
    # Same "friendly blockers" definition _clamp_target_against_friendly_
    # models() itself uses - every other Player-owned model currently on
    # the board (this pre-move-loop call always has an empty `placed`, so
    # every squadmate counts too, same as that function's own base case).
    friendly_tokens = [
        t for t in movement_controller.all_tokens
        if t is not model and t.squad is not None and t.squad.owner == squad.owner
    ]
    blocking_models = [
        t for t in friendly_tokens
        if geometry.segment_circle_entry_fraction(
            (mx, my), (target_x, target_y), (t.x_in, t.y_in), t.radius_in + model.radius_in,
        ) < 1.0
    ]
    if not blocking_obstacles and not blocking_models:
        return []
    blocking_obstacles.sort(key=lambda o: (o.x_in - mx) ** 2 + (o.y_in - my) ** 2)
    blocking_obstacles = blocking_obstacles[:CORNER_ROUTE_MAX_OBSTACLES]
    blocking_models.sort(key=lambda t: (t.x_in - mx) ** 2 + (t.y_in - my) ** 2)
    blocking_models = blocking_models[:CORNER_ROUTE_MAX_OBSTACLES]

    clearance = model.radius_in + CORNER_ROUTE_CLEARANCE_IN
    candidates = []
    for o in blocking_obstacles:
        # "Slide past it" waypoints parallel to the obstacle's own edges, plus
        # its corners pushed outward - genuinely useful when the model isn't
        # pressed flush against this particular obstacle (e.g. a second,
        # different obstacle is what's actually blocking it right now).
        # Asked of the obstacle so a ROTATED piece offers the ways past its
        # real edges, and so this file's two copies of the routing cannot be
        # taught different geometry.
        candidates.extend(o.route_waypoints(mx, my, clearance))

    dx, dy = target_x - mx, target_y - my
    dist_to_target = (dx * dx + dy * dy) ** 0.5
    if dist_to_target > 1e-9:
        # Unit vector perpendicular to the mover-to-target line - "step to
        # one side" of each blocking model, not "back toward where I came
        # from" or "further past the target".
        px, py = -dy / dist_to_target, dx / dist_to_target
        for t in blocking_models:
            side_radius = t.radius_in + model.radius_in + CORNER_ROUTE_CLEARANCE_IN
            candidates.append((t.x_in + px * side_radius, t.y_in + py * side_radius))
            candidates.append((t.x_in - px * side_radius, t.y_in - py * side_radius))

    def reachable(point):
        if any(
            o.blocks_movement_for(model)
            and o.blocks_segment((mx, my), point)
            for o in obstacles
        ):
            return False
        if any(
            geometry.segment_circle_entry_fraction((mx, my), point, (t.x_in, t.y_in), t.radius_in + model.radius_in) < 1.0
            for t in friendly_tokens
        ):
            return False
        return True

    waypoints = [
        p for p in candidates
        if reachable(p) and (p[0] - mx) ** 2 + (p[1] - my) ** 2 >= MIN_ROUTE_PROGRESS_IN ** 2
    ]
    waypoints.sort(key=lambda p: (p[0] - target_x) ** 2 + (p[1] - target_y) ** 2)
    return waypoints


# Real, severe bug found via user report ("die moves wirken oft blockiert, zu
# kurz... ab zug 2 bewegt sich die ki kaum noch") and reproduced on a
# COMPLETELY EMPTY board - no terrain, no enemy anywhere near, nothing in the
# way at all: every model of a squad used to head for the SAME shared aim
# point, so the squad's own models converged on one spot and blocked each
# other. _clamp_target_against_friendly_models() then truncated each model at
# the first squadmate standing in its path, and try_commit_segment() rejected
# outright any model that would still have landed on one (reverting it to
# 0.00"). The resulting sheared formation failed confirm_move()'s coherency
# check, so the angle/fraction ladder retried at ever shorter distances until
# some degenerate stub of a move finally passed. Measured: a 10-model squad
# with M=7" averaged 1.65" of actual movement, with several models at exactly
# 0.00" - matching the real game logs, where 1-5 of 10 models per squad moved
# in a typical turn (Kroot Carnivores 2, round 3->4: exactly ONE model of ten).
#
# The fix is to stop aiming every model at one point: each model gets its own
# destination slot instead - the aim point plus that model's CURRENT offset
# from the squad centroid, i.e. the formation the squad already has, carried
# forward. Every model then travels on a parallel course rather than a
# converging one, so squadmates stop blocking each other by construction,
# while each model still routes/clamps/validates individually exactly as
# before (a model stopped by terrain simply falls behind, which the coherency
# retry ladder below still catches). Same scenario, same code path, after the
# fix: 10/10 models move the full 7.00" and coherency holds.
def _formation_slot(model, aim_point, centroid, tighten=1.0):
    """This model's own destination for an attempt: `aim_point` with the
    model's offset from the squad centroid carried over, so the squad advances
    in the shape it already has instead of collapsing onto a single point (see
    the module comment above for the bug this fixes) - scaled by `tighten`, so
    an over-stretched squad closes up as it goes.

    Scaling every offset about the centroid by one shared factor is a
    similarity transform: relative bearings are untouched (nobody swaps sides
    or crosses a squadmate), every pairwise distance shrinks by exactly that
    factor, and each model still gets its own distinct slot, which is the whole
    point of this function. See _tightening_factor() for how the factor is
    picked."""
    return (aim_point[0] + (model.x_in - centroid[0]) * tighten,
            aim_point[1] + (model.y_in - centroid[1]) * tighten)


# How much of rule 09.02's 9" spread limit a squad is aimed at when it has to
# close up, and the most it may tighten in any single move. The margin matters:
# a formation sitting AT the limit has no room left for the per-model clamping
# that terrain forces on it, so the next obstacle it meets splits it.
_FORMATION_COMFORT_FRACTION = 0.7
_MIN_FORMATION_TIGHTEN = 0.6
def _capped_aim(centroid, aim_point, budget):
    """`aim_point` pulled back to what the squad can actually cover this turn.

    Without this the tightening in _formation_slot() only ever arrives when the
    squad ARRIVES. Measured on the stretched Meganobz of
    test_formation_coherency.py: _tightening_factor() asked for 0.85 on every
    one of four moves - a target spread of 6.30" against 9.00" - and delivered
    7.45" -> 7.41" -> 7.38" -> 7.36", i.e. 0.4% of the 15% it asked for.

    The reason is geometric rather than a bug in the shrink. Each model is sent
    toward `far target + its own tightened offset` and capped at its own
    movement. When the target is several turns away, every one of those aims
    points in almost the same direction and every model travels the same
    distance along it - which is a rigid translation, and a rigid translation
    cannot change spread at all. The offsets only converge over the last few
    inches, so the formation closes up exactly once, on arrival.

    Aiming at the point the squad can really reach this turn puts the slots
    inside everyone's reach instead: a leading model has a short trip and stops
    on its slot rather than running on, a trailing one spends its whole move
    catching up, and the formation tightens every turn instead of never. The
    centroid still travels the full budget toward the goal, so this costs no
    ground - see measure_movement_fixes.py."""
    dx, dy = aim_point[0] - centroid[0], aim_point[1] - centroid[1]
    dist = (dx * dx + dy * dy) ** 0.5
    if budget <= 0 or dist <= budget or dist < 1e-9:
        return aim_point
    scale = budget / dist
    return (centroid[0] + dx * scale, centroid[1] + dy * scale)


def _truncate_route(origin, waypoints, budget):
    """`waypoints` cut short at `budget` of travel - the route-walking
    equivalent of _capped_aim(), and needed for the same reason: the formation
    offsets are added to the LAST waypoint, so a route longer than one turn
    puts the tightened shape somewhere the squad will not stand this turn.

    The cut point is interpolated rather than rounded to the nearest waypoint,
    so the anchor is exactly as far along the road as the squad can go. No
    ground is lost - a model could not have travelled past it anyway."""
    if budget <= 0 or not waypoints:
        return waypoints
    total = 0.0
    previous = origin
    for index, waypoint in enumerate(waypoints):
        leg = ((waypoint[0] - previous[0]) ** 2 + (waypoint[1] - previous[1]) ** 2) ** 0.5
        if total + leg >= budget:
            if leg < 1e-9:
                return list(waypoints[:index + 1])
            scale = (budget - total) / leg
            cut = (previous[0] + (waypoint[0] - previous[0]) * scale,
                   previous[1] + (waypoint[1] - previous[1]) * scale)
            return list(waypoints[:index]) + [cut]
        total += leg
        previous = waypoint
    return list(waypoints)


def _tightening_factor(squad):
    """How much to shrink a squad's formation while it moves, as a factor on
    each model's offset from the centroid. 1.0 means "keep the current shape".

    Reported by the user, and confirmed by measurement: "die truppen, die aus
    transportern aussteigen sind sehr weit auseinandergezogen durch die
    ringform. bei anschliessenden bewegungen ruecken sie sich aber nicht weiter
    zusammen. das laesst natuerlich viel raum für kohaerenz fehler." Exactly
    right, and it was structural rather than incidental - _formation_slot()
    carried each model's offset over unchanged, so a unit that disembarked into
    a wide ring kept that ring for the rest of the game and every later move
    re-aimed at the same stretched shape. Measured on the Meganobz from
    logs/game_20260808_213013.log: 7.83" edge spread against a 9.0" limit, i.e.
    almost no slack, and any model the terrain clamps then splits the unit.

    Only ever shrinks, never expands: spreading a compact squad out has no
    benefit here and would be a new way to break coherency. Bounded below by
    _MIN_FORMATION_TIGHTEN so one move cannot ask for a formation tighter than
    the bases physically fit into - a badly stretched unit closes up over a
    couple of turns instead, which is also what a player does by hand."""
    if len(squad.models) < 2:
        return 1.0
    spread = max(
        edge_distance(a, b)
        for i, a in enumerate(squad.models)
        for b in squad.models[i + 1:]
    )
    # TRIED AND REVERTED, measured rather than argued: deriving this target
    # from the unit's OWN size instead of from a fraction of rule 09.02's limit
    # (n bases at the smallest legal pitch, hex-packed, as the edge span of a
    # circle of the same area - which does predict the packer well, 5.44" for
    # the 20-strong mob against pack_positions()' own 5.44"). The motivation was
    # real: config.SPREAD_LIMIT_PLAYERS lifts the 9" limit for the AI, so a
    # target expressed as a fraction of it is a fraction of a number that no
    # longer binds this player. But measured on measure_crowded_movement.py it
    # cost 185.2" of ground gained against 169.7", i.e. -8%, and bought nothing
    # back: median spread 6.02" -> 6.45" and the widest unit 12.78" -> 12.51".
    # Sweeping the strictness confirmed it rather than tuning it away - "no
    # tightening at all" scored as well as every setting tried. Compaction has
    # to come from the placement (the packers already build tight blocks), not
    # from spending movement on it every turn.
    comfortable = MAX_SPREAD_IN * _FORMATION_COMFORT_FRACTION
    if spread <= comfortable or spread <= 1e-9:
        return 1.0
    return max(_MIN_FORMATION_TIGHTEN, comfortable / spread)


def _squad_progress(before_centroid, after_centroid, goal_point):
    """How much an attempt actually achieved, as (progress, displacement):
    `progress` is how much closer to goal_point the squad's centroid got
    (negative if it ended up further away - a sideways detour scores near
    zero), `displacement` is how far the centroid moved at all. Both are
    squad-wide on purpose: the old per-model "did ANY single model cover 1
    inch" gate accepted an attempt where one model of ten shuffled forward
    and the other nine stood still, then stopped the sweep there (see
    _advance_toward_per_model()'s own candidate-scoring for how this is used
    now)."""
    def dist(a, b):
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
    return (
        dist(before_centroid, goal_point) - dist(after_centroid, goal_point),
        dist(before_centroid, after_centroid),
    )


def _place_per_model_move(movement_controller, squad, aim_point, fraction, start):
    """One placement attempt shared by _advance_toward_per_model()'s
    angle-jitter sweep and its corner-routing fallback: start a fresh move,
    then send every model of squad toward its OWN formation slot around
    aim_point (see _formation_slot()) - each capped by its own
    remaining_range * fraction, routed around whatever's actually in ITS OWN
    path, and kept off squadmates already placed this same attempt,
    closest-to-aim_point model processed first.

    Places the models but deliberately does NOT confirm: the caller scores
    the result first (see _squad_progress()) and only then decides whether to
    confirm this attempt or cancel it and keep looking. confirm_move() has
    irreversible side effects on success (moved_squad_ids, the Advance/Fall
    Back flags, cleared move state), so "confirm and undo if it turns out to
    be a poor move" is not an option - the score has to be known first.

    Real, severe, PRE-EXISTING bug found via user report ("ghostkeel/
    devilfish bewegen sich immer noch kaum", still reproducing after
    _place_per_model_route()'s own false-success fix above - this
    function has the exact same flaw and predates today's session
    entirely): try_commit_segment() can reject a model's ONLY candidate
    segment this attempt (e.g. flying straight at a far-off target lands
    exactly inside a Dense terrain wall - rule 21.03's Take to the Skies
    bypasses terrain/models IN TRANSIT, but never the final-position check,
    see model_terrain_violation()'s own docstring) - rejection reverts the
    model to `origin`, i.e. its position from BEFORE this attempt. Since
    nothing else moved either, confirm() then runs its fresh checks against
    a squad that is, in total, back exactly where it started - finds
    nothing wrong with THAT (of course - it's unchanged and was already
    legal), and reports success at zero net movement. The very first
    angle/fraction combination tried (straight line, full distance) is
    exactly the one most likely to clip a piece of terrain near a distant
    target, so this could silently "succeed" on attempt #1 every time,
    never even reaching the angles that might have gone somewhere.
    Reproduced directly against the real demo scene: Ghostkeel's first,
    straight-at-target attempt "succeeded" while moving exactly 0.00\".
    That false success is now caught by the caller's own scoring instead
    (an attempt whose centroid never moved scores zero displacement and is
    discarded), which also subsumes what the old per-model "did ANY model
    cover 1 inch" gate was doing here - and catches the far more common
    case that gate missed entirely: nine of ten models standing still while
    one shuffles forward.

    Real, severe bug, reported three ways at once ("ki hat pile in mit meganobz
    nicht genutzt", "kopter sind nicht nach vorne geflogen", "bikes fahren sich
    oft in mauer-buchten fest") and visible straight away in
    logs/game_20260808_213013.log, which carries 77 coherency rejections in a
    single game: a per-model placement splits the formation, confirm_move()
    throws the WHOLE attempt away, and the squad ends up standing still. The
    Meganobz lost their entire Movement phase that way - nine consecutive
    rejections, then "remained stationary" - and then had to charge from where
    they never wanted to be.

    The caller's existing fraction ladder does not fix this, and measuring why
    is what made the repair below the right shape: `fraction` scales each
    model's BUDGET, not its displacement, and `move = min(dist, max_distance)`
    means a model already close to its slot travels the full distance at every
    rung. Shrinking the budget therefore holds the near models still while
    cutting the far ones - it can widen the very gap it is meant to close.

    _repair_coherency_by_shrinking() scales what every model ACTUALLY achieved
    instead, by one shared factor, which is the interpolation between the
    formation as it stands (coherent, by definition - it is a legal board
    state) and the one this attempt produced. Coherency is continuous in the
    positions, so some factor near zero always holds, and shrinking gives back
    a formation with the same flow-around-the-obstacle shape, just less of
    it - which beats handing back nothing at all."""
    origin = [(m.x_in, m.y_in) for m in squad.models]
    baseline_errors = len(squad.check_coherency())
    centroid_after, budget = _place_per_model_pass(
        movement_controller, squad, aim_point, fraction, start)
    if len(squad.check_coherency()) > baseline_errors:
        _sweep_stats["split_passes"] = _sweep_stats.get("split_passes", 0) + 1
        _repair_coherency_by_shrinking(
            movement_controller, squad, origin, start, baseline_errors)
        centroid_after = _centroid(squad)
    return centroid_after, budget


# How much of rule 03.03's 2" an anchored slot actually aims for. Short of the
# limit on purpose: a slot placed exactly AT 2" has no margin left for the
# clamping that terrain, squadmates and the model's own remaining range then do
# to it, so it would arrive just outside as often as just inside.
_COHERENCY_AIM_FRACTION = 0.75


def _coherency_reach(a, b):
    """The centre-to-centre distance at which `a` and `b` are exactly at rule
    03.03's 2" - coherency is measured edge to edge (see edge_distance), so two
    big bases may stand much further apart in centre terms than two small
    ones."""
    return COHERENCY_RANGE_IN + a.radius_in + b.radius_in


def _nearest_placed(x, y, placed):
    return min(placed, key=lambda p: (p.x_in - x) ** 2 + (p.y_in - y) ** 2, default=None)


def _anchored_slot(model, slot, placed):
    """Left as the identity on purpose. See _close_up_to_placed() for what
    actually enforces rule 03.03 here, and read this before adding a
    planning-time version back.

    The obvious move is to pull each model's INTENDED slot in until it is
    within 2" of a squadmate already placed this pass - the same greedy
    construction _disembark_pack_positions() and _ingress_pack_positions() use,
    which is what makes those two coherent by construction rather than by
    hope. It was built that way first, and measured, and it is wrong here.

    Why it is wrong: unlike a disembark ring, the intended slots are ALREADY
    coherent. _formation_slot() is a similarity transform of the formation the
    squad is standing in - which is a legal board state, so coherent - scaled
    by _tightening_factor() with a factor of at most 1. Every pairwise distance
    therefore shrinks or stays put, and connectivity cannot break. There is
    nothing at the planning stage to repair, and pulling individual slots
    toward whichever squadmate happens to be nearest only breaks the uniform
    shrink apart: models are processed nearest-the-aim-point first, so the
    laggards get dragged toward the leaders and the formation strings out into
    a comet instead of closing up. Measured on the strung-out 10-Boyz case in
    test_formation_coherency.py, spread over four moves:

        neither half   7.36 -> 7.31 -> 7.31 -> 7.04 -> 6.17
        this, alone    7.36 -> 8.47 -> 8.47 -> 6.66 -> 6.23

    i.e. it made the squad wider, which is the 9" half of the same rule, and
    broke the regression that exists to keep a stretched squad closing up.

    What actually breaks connectivity is ARRIVAL, not aim: terrain, squadmates
    and remaining range stop individual models short of slots that were fine.
    That is checkable only after the fact, which is where the repair belongs."""
    return slot


def _in_coherency_with_any(model, placed):
    return any(edge_distance(model, other) <= COHERENCY_RANGE_IN for other in placed)


def _close_up_to_placed(movement_controller, squad, model, placed):
    """Spend some of `model`'s leftover move tucking it back in beside the
    squad, after it arrived out of rule 03.03's 2" of every squadmate already
    placed this pass.

    This is the constructive half of the 2" rule, and where measurement put it:
    of 1708 coherency rejections across every log in the repo, the connectivity
    half is the sole reason for 46% and involved in 99% once the single
    9"-spread outlier unit is set aside. The cause was structural - the whole
    placement was aimed, and only then asked at confirm_move() whether it still
    hung together, so one model clamped short by a wall threw away the entire
    attempt. That is the reported "sixteen consecutive coherency rejections,
    then remained stationary".

    Aimed at the far side of the anchor, TOWARD the rest of the placed models,
    rather than straight back along the line the model came in on. Both restore
    connectivity; only this one also closes the formation up, because it puts
    the straggler on the group's side of its neighbour instead of leaving it
    hanging off the outside edge. The two halves of rule 03.03 pull in opposite
    directions otherwise - satisfying the 2" by chaining models one after
    another is exactly how a squad blows the 9" - and this is what keeps them
    pointing the same way.

    Goes through _clamp_target_against_friendly_models()/clamp_move()/
    try_commit_segment() like every other step in this file, so it can never
    put a model somewhere the move itself could not, and simply achieves
    nothing if the model is boxed in - which is no worse than the rejection it
    is trying to avoid."""
    anchor = _nearest_placed(model.x_in, model.y_in, placed)
    if anchor is None:
        return
    towards_x = sum(p.x_in for p in placed) / len(placed)
    towards_y = sum(p.y_in for p in placed) / len(placed)
    dx, dy = towards_x - anchor.x_in, towards_y - anchor.y_in
    if (dx * dx + dy * dy) ** 0.5 < 1e-6:
        # The anchor IS the group (a single placed model): there is no "inward"
        # direction to prefer, so come straight in along the way we came.
        dx, dy = model.x_in - anchor.x_in, model.y_in - anchor.y_in
    dist = (dx * dx + dy * dy) ** 0.5
    if dist < 1e-9:
        return
    allowed = _coherency_reach(model, anchor) * _COHERENCY_AIM_FRACTION
    scale = allowed / dist
    target_x = anchor.x_in + dx * scale
    target_y = anchor.y_in + dy * scale
    target_x, target_y = _clamp_target_against_friendly_models(
        model, target_x, target_y, squad, movement_controller, placed, caller="close-up")
    new_x, new_y = movement_controller.clamp_move(model, target_x, target_y)

    # Judged before it is committed, and dropped unless it is an improvement on
    # BOTH halves of rule 03.03 at once. clamp_move() only returns coordinates,
    # it does not move anything, so the candidate can be tried on the model and
    # put back at no cost - the same place-check-roll-back shape the rest of
    # this file uses, and the reason it is needed here specifically is that the
    # two halves of the rule pull against each other: a tuck that restores the
    # 2" by dragging a straggler across the formation can widen the 9". That is
    # not hypothetical - without this guard it cost the stretched Meganobz case
    # in test_formation_coherency.py 0.05" of closing over four moves, which
    # was enough to stop the squad tightening at all.
    before_spread = _squad_spread(squad)
    before_errors = len(squad.check_coherency())
    origin = (model.x_in, model.y_in)
    model.x_in, model.y_in = new_x, new_y
    if (len(squad.check_coherency()) > before_errors
            or _squad_spread(squad) > before_spread + 1e-6):
        model.x_in, model.y_in = origin
        return
    movement_controller.try_commit_segment(model)


# Halvings used to find how far a blocked model can actually get. Six brings
# the answer within ~1.5% of the true limit, and a refused attempt is free -
# try_commit_segment() only charges the budget when it ACCEPTS a placement - so
# the only price is a handful of legality checks.
_BACKOFF_STEPS = 6

# Sideways dodges tried BEFORE giving up any distance, smallest first: the same
# move length, swung around the model's own position. This is what a player
# does when a squadmate is standing on the spot - put the model down beside it,
# just as far forward - and it is what keeps a Normal move worth its full
# inches. The user's point, and it is the reason this stage exists at all:
# "die maximale bewegungsreichweite auszureizen in bestimmten situationen ist
# essentiell... da darf kein zoll liegengelassen werden" - whether move+charge
# reaches (11.04), how many models end up in line of sight, and how many stand
# on an objective all turn on the last inch.
#
# Measured across three scenarios (map2 with a far and a near goal, map3):
# dodging beats not dodging on ground gained and on charge probability in every
# one of them - on map2's far goal, mean charge chance 61.5% -> 70.2% and the
# share of models moving under half an inch 9.4% -> 3.9%.
#
# WHERE THE LIMIT COMES FROM. The sweep does not separate 32 from 45 cleanly
# (32 wins one scenario, 45 the other two), so it is set by argument rather
# than by the winner of a noisy run: a dodge of angle t keeps cos(t) of its
# forward progress, so 45 degrees still banks 71% of the step while 60 is down
# to half. Smallest first, so a wide swing is only ever used when nothing
# narrower fits.
_DODGE_ANGLES_DEG = (10.0, -10.0, 20.0, -20.0, 32.0, -32.0, 45.0, -45.0)

# How many times _stage_toward() walks the whole squad toward its slots. Each
# pass frees the ground the previous one vacated; it stops early as soon as a
# pass changes nothing, so this is a ceiling and not a cost.
_PACK_WALK_PASSES = 4
# Close enough to a slot to stop asking for it - a base width's tenth, well
# inside the 0.05" overlap margin _first_legal_slot() leaves between models.
_PACK_ARRIVED_IN = 0.05


def _advance_model_toward(movement_controller, model, target_x, target_y, _tries_left=4):
    """Move one model as far toward (target_x, target_y) as the rules allow,
    and return whether it ended up anywhere new.

    The reason this is not simply clamp_move() + try_commit_segment(), which is
    what every placement in this file used to do: those two do not compose into
    "as far as legal". clamp_move() stops a model at terrain, at the board edge
    and at ENEMY models - but NOT at friendly ones, because rule 03.01 lets a
    base move through them and only forbids ENDING on one. So the position it
    hands back can be sitting on a squadmate, try_commit_segment() rejects the
    whole segment, and the model goes back to where it started having moved
    nothing at all.

    Reported by the user for the 20-strong Boyz mob - "warum bleiben einzelne
    modelle hinten stehen, waehrend andere nach vorne laufen. als mensch wuerde
    ich doch modell fuer modell bewegen und versuchen jedes einzelne modell so
    weit wie moeglich nach vorne zu verschieben" - and measured on exactly that
    unit: of 136 segment commits in one move, 35 were rejected, every one of
    them for "cannot end their move on top of" another model. Those models had
    aimed 4.38" on average and got 0.00", which is why four of twenty-two stood
    still while the rest covered their full 6".

    Sliding the model up until it touches is what a player does by hand, and it
    is free to look for. The user's proposal here was to give the AI a licence
    the human does not have - "fuer sie zaehlt nur, ob das ergebnis legal ist,
    aber nicht wie sie dahingekommen ist... ohne restkontingent abzuziehen" -
    and the conclusion is right while the mechanism turned out not to be the
    problem: a REFUSED attempt already costs nothing, because
    try_commit_segment() deducts from the budget only when it ACCEPTS. What the
    old code lost was not budget but the attempt itself - it asked once and gave
    up. So no licence is needed, only persistence. (A rebasing primitive that
    measured the budget from the model's starting point instead of summing the
    segments was built and removed: with a multi-waypoint route it would have
    replaced the walk around an obstacle with a straight line into it, and it
    bought nothing the ladder below does not.)

    The rules still decide every placement: each rung goes through the same
    clamp_move()/try_commit_segment() pair, so a model can never end further
    than its Movement characteristic, on top of another model, off the board,
    or anywhere its move type forbids."""
    origin = (model.x_in, model.y_in)
    reach_x, reach_y = movement_controller.clamp_move(model, target_x, target_y)
    model.x_in, model.y_in = reach_x, reach_y
    ok, _errors = movement_controller.try_commit_segment(model)
    if ok:
        return math.dist(origin, (model.x_in, model.y_in)) > 1e-9

    # Refused, and try_commit_segment() has already put the model back on
    # `origin`. Before giving up any distance at all, try to go just as far in
    # a slightly different direction: the thing in the way is almost always a
    # single squadmate's base, and stepping around it costs nothing while
    # stopping short costs inches that matter (User: "die maximale
    # bewegungsreichweite auszureizen in bestimmten situationen ist
    # essentiell... da darf kein zoll liegengelassen werden").
    span = math.dist(origin, (reach_x, reach_y))
    if span > 1e-6:
        heading = math.atan2(reach_y - origin[1], reach_x - origin[0])
        for degrees in _DODGE_ANGLES_DEG:
            angle = heading + math.radians(degrees)
            aim_x = origin[0] + math.cos(angle) * span
            aim_y = origin[1] + math.sin(angle) * span
            dodge_x, dodge_y = movement_controller.clamp_move(model, aim_x, aim_y)
            # Only worth trying if the swing actually keeps the distance - a
            # dodge that clamps to half the length is just a short step with
            # extra steps, and the ladder below does that better.
            if math.dist(origin, (dodge_x, dodge_y)) < span - 0.05:
                continue
            model.x_in, model.y_in = dodge_x, dodge_y
            ok, _errors = movement_controller.try_commit_segment(model)
            if ok:
                return True
            model.x_in, model.y_in = origin

    # Nowhere at full distance. Now ask for less, halving each time.
    share = 0.5
    for _step in range(_BACKOFF_STEPS):
        aim_x = origin[0] + (reach_x - origin[0]) * share
        aim_y = origin[1] + (reach_y - origin[1]) * share
        step_x, step_y = movement_controller.clamp_move(model, aim_x, aim_y)
        if math.dist(origin, (step_x, step_y)) > 1e-6:
            model.x_in, model.y_in = step_x, step_y
            ok, _errors = movement_controller.try_commit_segment(model)
            if ok:
                # Bounded: each round leaves the model further along with less
                # budget, so this terminates on its own - the cap is a backstop
                # against a pathological sequence of one-inch gains.
                if _tries_left > 0:
                    _advance_model_toward(movement_controller, model, target_x, target_y,
                                          _tries_left - 1)
                return True
        share *= 0.5
    return False


def _point_toward(squad, target_point, distance_in):
    """`distance_in` along the straight line from the squad's centroid toward
    `target_point`, or None if it is already there."""
    cx, cy = _centroid(squad)
    gap = math.dist((cx, cy), target_point)
    if gap < 1e-6 or distance_in <= 0:
        return None
    step = min(distance_in, gap)
    return (cx + (target_point[0] - cx) / gap * step,
            cy + (target_point[1] - cy) / gap * step)


def _place_packed(movement_controller, squad, spot, facing_point, start):
    """Squeeze `squad` into a tight block centred on `spot`, models walked into
    it. Leaves the move OPEN - the caller confirms or rolls back.

    This is the "deformable mass" placement (user: "squads sind nicht als
    starre objekte zu betrachten sondern als formbare masse, die sich hinter
    eine deckung quetschen kann oder durch einen engen korridor schlaengeln
    kann"), and it is the one thing the ordinary sweep cannot express, because
    every candidate that sweep produces keeps the shape the squad is standing
    in. Measured on the real crowded board, at every fraction of the move:

        Stormboyz 12" forward   rigid translation BLOCKED   packed block fits
        Deffkoptas 12" forward  rigid translation BLOCKED   packed block fits
        Boyz mob   6" forward   rigid translation BLOCKED   packed block fits
        Meganobz   5" forward   rigid translation BLOCKED   packed block fits

    What stops those units is their own 5-7" footprint, not the ground: packed
    they are 3-5" across and fit everywhere they were being refused.

    Returns False without touching the squad if this ground cannot hold a
    packed formation. `facing_point` is what the block grows AWAY from - the
    enemy, so its near edge sits on `spot` rather than beyond it - or None."""
    if len(squad.models) < 2:
        return False
    others = [t for t in movement_controller.all_tokens if t.squad is not squad]

    def slot_ok(model, x_in, y_in):
        if not formation_layout.on_board(x_in, y_in, model.radius_in):
            return False
        if model_terrain_violation(model, movement_controller.obstacles, x_in, y_in):
            return False
        return not any(
            math.dist((x_in, y_in), (o.x_in, o.y_in)) < model.radius_in + o.radius_in
            for o in others
        )

    if facing_point is not None:
        base_angle = math.atan2(spot[1] - facing_point[1], spot[0] - facing_point[0])
    else:
        base_angle = -math.pi / 2
    smallest = min(m.radius_in for m in squad.models)
    slots = formation_layout.pack_positions(
        squad, spot[0], spot[1], base_angle=base_angle,
        position_valid=slot_ok, gap_in=2 * smallest + 0.05,
    )
    if len(set(slots)) != len(slots):
        return False  # the packer had to stack models: this ground does not fit

    # Which model walks to which slot is a decision in its own right, and it
    # used to be made by accident: slots come back in squad order, but the
    # packer fills them widest-first outwards from the drop point, so slot i
    # belongs to nobody in particular. Measured on the real board, pairing by
    # index asks roughly twice the walk that matching by distance does - see
    # formation_layout.match_models_to_slots(), which also explains why the
    # front-rank characters are held in place rather than matched away.
    fixed = {i for i, model in enumerate(squad.models)
             if model in front_rank.front_rank_models(squad)}
    targets = formation_layout.match_models_to_slots(squad.models, slots, fixed=fixed)

    start()
    # Several passes, not one. A model's target is checked against everything
    # that is NOT a squadmate, so it can be legal and still be occupied right
    # now by a squadmate who has not moved yet - try_commit_segment() refuses
    # that, _advance_model_toward() then dodges or backs off, and the model
    # ends short and overlapping. Measured on the Meganobz, one pass left three
    # of seven models 1.7"-2.4" short and the whole move was rejected with
    # "Models cannot end their move on top of another model".
    #
    # Repeating lets a model walk into the space a squadmate has just vacated,
    # which is the "squeeze through" a player does by hand. Rule 03.01 already
    # allows moving THROUGH a friendly model, so nothing here is being bent -
    # only the order in which the spaces come free. Stops as soon as a pass
    # changes nothing, so an unobstructed squeeze still costs one pass.
    remaining = sorted(range(len(squad.models)),
                       key=lambda i: math.dist((squad.models[i].x_in, squad.models[i].y_in),
                                               targets[i]))
    for _pass in range(_PACK_WALK_PASSES):
        moved_any = False
        still = []
        for index in remaining:
            model = squad.models[index]
            before = (model.x_in, model.y_in)
            _advance_model_toward(movement_controller, model, *targets[index])
            if math.dist((model.x_in, model.y_in), targets[index]) <= _PACK_ARRIVED_IN:
                moved_any = True
                continue
            if math.dist((model.x_in, model.y_in), before) > 1e-6:
                moved_any = True
            still.append(index)
        remaining = still
        if not remaining or not moved_any:
            break
    return True


def _stage_toward(movement_controller, squad, spot, enemy_squads, start, confirm, cancel):
    """Move to `spot` and PACK the unit there, as tightly as the rules allow.

    Staging is the one move where compressing is the whole point. A piece of
    cover big enough to hide a squeezed unit is usually not big enough to hide a
    sprawled one, and the observation now judges cover against the squeezed
    footprint (formation_layout.packed_radius) - so unless the move actually
    delivers that footprint, the spot it picked is a promise rather than a
    measurement. Measured before this existed, with units walking to their own
    staging spots in their current shape: Beast Snagga arrived with 10 of 11
    models in enemy line of sight, Gretchin with 7 of 11, and only the
    single-model Deff Dread got what it was told - because a one-model unit IS
    the point that was tested.

    NOT used for ordinary advances, and that restraint is measured too: packing
    costs movement, and applying it to every move took the 20-strong mob from
    42% of its achievable progress to 7% (see _needs_regroup()). Here the
    compression IS the objective, so paying for it is the right trade.

    Falls back to False if the ground cannot hold a packed formation, leaving
    the squad untouched for the caller's ordinary path."""
    if len(squad.models) < 2:
        return False
    origin = [(m.x_in, m.y_in) for m in squad.models]
    facing = _squad_centroid_of_nearest(squad, enemy_squads)
    if not _place_packed(movement_controller, squad, spot, facing, start):
        return False

    # confirm_move() reports through movement_controller.errors, not through a
    # return value - it returns None on success AND on failure. Testing what it
    # returned, which this did, made _stage_toward() unable to succeed at all:
    # every packed staging move ever attempted was thrown away and silently
    # fell back to the ordinary one. Same success test the other callers use
    # (errors is emptied on success and filled on failure).
    confirm()
    if not movement_controller.errors:
        return True
    cancel()
    for model, (x_in, y_in) in zip(squad.models, origin):
        model.x_in, model.y_in = x_in, y_in
    return False


def _squad_spread(squad):
    """The 9" half of rule 03.03: the widest edge-to-edge gap in the unit."""
    if len(squad.models) < 2:
        return 0.0
    return max(edge_distance(a, b)
               for i, a in enumerate(squad.models)
               for b in squad.models[i + 1:])


def _place_per_model_pass(movement_controller, squad, aim_point, fraction, start):
    """One raw placement pass - every model toward its own formation slot. See
    _place_per_model_move(), which wraps this with the coherency repair."""
    start()
    centroid = _centroid(squad)
    # Read once, before anything moves: _formation_slot() reads each model's
    # live position, so recomputing this mid-pass would measure a formation
    # that is already half-tightened and shrink it twice over.
    tighten = _tightening_factor(squad)
    # The FASTEST model's budget, and that is measured rather than an
    # oversight. Taking the slowest model's instead (a Technomancer M6 among
    # Necron Warriors M5 - the obvious fix for a mixed 19.01 unit whose fast
    # leader outruns the rank and file) was tried on 2026-09-09 and cost the
    # reported 21-model blob 2.71" -> 1.84" of progress: with a tightening
    # factor below 1 the slots converge on the aim point, and an aim point set
    # exactly one slow move away leaves the FRONT models stopping on slots
    # inside their own range while only the rear spends its full move. The
    # overshoot from the fastest model's budget is what keeps every model
    # walking its whole distance. See measure_reported_moves.py case C.
    budget = max((movement_controller.remaining_range.get(m.id, 0.0) for m in squad.models), default=0.0)
    # Slots are built around what the squad can REACH this turn, not around a
    # target several turns away - otherwise the tightening never actually
    # happens. See _capped_aim().
    aim_point = _capped_aim(centroid, aim_point, budget)
    placed = []
    for model in sorted(squad.models, key=lambda m: (m.x_in - aim_point[0]) ** 2 + (m.y_in - aim_point[1]) ** 2):
        max_distance = movement_controller.remaining_range.get(model.id, 0.0) * fraction
        slot = _formation_slot(model, aim_point, centroid, tighten)
        # Rule 03.03, built in rather than checked afterwards - see
        # _anchored_slot(). The first model of the pass has nothing to anchor
        # to and simply takes its slot; every later one is aimed somewhere it
        # still hangs together with the squad it is joining.
        slot = _anchored_slot(model, slot, placed)
        dx, dy = slot[0] - model.x_in, slot[1] - model.y_in
        dist = (dx * dx + dy * dy) ** 0.5
        if dist > 1e-9 and max_distance > 0:
            move = min(dist, max_distance)
            scale = move / dist
            target_x, target_y = model.x_in + dx * scale, model.y_in + dy * scale
            target_x, target_y = _clamp_target_against_friendly_models(
                model, target_x, target_y, squad, movement_controller, placed,
                max_travel=max_distance, caller="pass")
            _advance_model_toward(movement_controller, model, target_x, target_y)
        # Aiming somewhere reachable is not arriving there: clamp_move() may
        # have stopped this model short against a wall or a base. Check where
        # it actually landed and spend leftover range closing the gap.
        if placed and not _in_coherency_with_any(model, placed):
            _close_up_to_placed(movement_controller, squad, model, placed)
        placed.append(model)
    return _centroid(squad), budget


def _repair_coherency_by_shrinking(movement_controller, squad, origin, start, baseline_errors):
    """Give back a shorter version of a per-model placement that broke
    coherency, instead of letting the caller throw the whole attempt away.

    Every model is put at `origin + factor * (where it got to)` for a shared,
    shrinking factor - so the formation keeps the shape this attempt found
    (models that flowed around an obstacle still flowed around it) and only
    the amount changes. `origin` is a legal, coherent board state, and
    coherency is continuous in the positions, so a small enough factor always
    works; the ladder stops at the first one that is no worse than
    `baseline_errors` (rule 09.02 - a squad that entered the phase already
    broken is not asked to repair itself, see _run_phase_one()).

    Each shrunken destination still goes through clamp_move() and
    try_commit_segment(), so a trial can never place a model somewhere the
    real move could not, and a model whose interpolated spot is itself
    illegal (an intermediate position can overlap a squadmate even when both
    endpoints are clear) simply stays at its origin.

    Leaves the squad at the best rung it found, or back at `origin` if none
    held - which is what the caller would have ended up with anyway."""
    reached = [(m.x_in, m.y_in) for m in squad.models]

    def restore_origin():
        for model, (x, y) in zip(squad.models, origin):
            model.x_in, model.y_in = x, y

    for factor in _COHERENCY_SHRINK_FRACTIONS:
        restore_origin()
        start()  # fresh remaining_range: this is the whole move again, not a step
        for model, (ox, oy), (rx, ry) in zip(squad.models, origin, reached):
            target_x = ox + (rx - ox) * factor
            target_y = oy + (ry - oy) * factor
            new_x, new_y = movement_controller.clamp_move(model, target_x, target_y)
            model.x_in, model.y_in = new_x, new_y
            ok, _errors = movement_controller.try_commit_segment(model)
            if not ok:
                model.x_in, model.y_in = ox, oy
        if len(squad.check_coherency()) <= baseline_errors:
            return True
    restore_origin()
    start()
    return False


class _EngagementPaddedModel:
    """Lightweight duck-typed stand-in (only x_in/y_in/radius_in - all
    game/pathfinding.py ever reads) with its radius padded by
    ENGAGEMENT_RANGE_IN - see the pathfinding call site's own comment for
    why this exists instead of just inflating the mover's radius."""
    __slots__ = ("x_in", "y_in", "radius_in")

    def __init__(self, x_in, y_in, radius_in):
        self.x_in = x_in
        self.y_in = y_in
        self.radius_in = radius_in


def _engagement_padded_models(models, extra_radius):
    return [_EngagementPaddedModel(m.x_in, m.y_in, m.radius_in + extra_radius) for m in models]


def _place_per_model_route(movement_controller, squad, waypoints, start):
    """Like _place_per_model_move(), but every model walks a SEQUENCE of
    waypoints (game/pathfinding.py's find_route() - a real grid/A* search,
    see its own module docstring) instead of jumping straight at one aim
    point - each model following the route offset by its own formation slot
    (see _formation_slot()), so the squad walks the route in the shape it
    already has rather than every model filing through the exact same
    points. Each waypoint is capped by whatever remaining_range is left
    after the previous one - the same clamp_move()/try_commit_segment()
    per-segment machinery a human's own multi-point drag already uses, so
    find_route()'s output is only ever a SUGGESTION: this still re-validates
    every single step exactly as strictly as before, never trusts the route
    blindly. No fraction ladder here (unlike _place_per_model_move) - the
    route already respects the movement budget and is already obstacle/
    model-clear by construction, so shortening it further has no obvious
    benefit; a genuine coherency failure just falls through to the caller's
    existing corner-routing/angle-sweep fallback instead.

    Real, severe bug found while reproducing the user's real-scene report
    ("ghostkeel/devilfish hat sich nur ~1\" bewegt"): find_route()'s
    enemy-model avoidance only keeps the route from crossing an enemy
    model's BASE circle - it has no notion of the ADDITIONAL Engagement
    Range (2") a Normal/Advance move must also stay clear of (rule 03.04/
    09.05/09.06, see Squad.disallowed_enemy_squads_for_move()). A route that
    hugs close enough to an enemy-heavy area can end EVERY one of its
    waypoints within that 2" buffer, without ever crossing a base - each
    waypoint's try_commit_segment() then correctly rejects it and reverts
    the model back to `origin` (rule-correct on its own), but since NOTHING
    ever successfully committed, every model ends this whole attempt
    exactly where it started - which is, trivially, still a fully legal
    (just zero-distance) position. The old code below then called confirm()
    on that unchanged position, found no errors (of course - nothing
    moved), and reported SUCCESS - silently masking a real routing failure
    as a satisfied move and (crucially) short-circuiting past the caller's
    own corner-routing/angle-sweep fallback, which might have found a
    genuinely different, unblocked direction. Reproduced directly against
    the real demo scene's terrain/army: a VEHICLE squad's pathfinding
    attempt "succeeded" while moving exactly 0.00". That false success is
    now caught by the caller's own scoring instead (see
    _squad_progress()/_advance_toward_per_model()), which also subsumes the
    old per-model "did ANY model cover 1 inch" gate that used to guard it
    here.

    Places the models but deliberately does NOT confirm - see
    _place_per_model_move()'s docstring for why the score has to be known
    before confirm_move() is ever called. Returns the squad's centroid
    afterwards."""
    start()
    centroid = _centroid(squad)
    tighten = _tightening_factor(squad)  # see _place_per_model_pass()
    budget = max((movement_controller.remaining_range.get(m.id, 0.0) for m in squad.models), default=0.0)
    # Same reason as _place_per_model_pass()'s _capped_aim(): the formation
    # offsets are added to the LAST waypoint, so a road longer than one turn
    # puts the tightened shape where the squad will not be standing. Cutting
    # the road at what it can walk costs nothing - it could not have gone past
    # that point anyway - and makes the shrink land this turn.
    waypoints = _truncate_route(centroid, waypoints, budget)
    placed = []
    final_aim = waypoints[-1]
    for model in sorted(squad.models, key=lambda m: (m.x_in - final_aim[0]) ** 2 + (m.y_in - final_aim[1]) ** 2):
        # Snapshot this model's formation offset ONCE, before it starts
        # walking - _formation_slot() reads the model's live position, so
        # re-deriving it at every waypoint would compound the offset further
        # with each step instead of holding the formation.
        offset_x = (model.x_in - centroid[0]) * tighten
        offset_y = (model.y_in - centroid[1]) * tighten
        for index, waypoint in enumerate(waypoints):
            target_x, target_y = waypoint[0] + offset_x, waypoint[1] + offset_y
            if index == len(waypoints) - 1:
                # Rule 03.03 only judges where the move ENDS, so only the last
                # waypoint is anchored - see _anchored_slot(). Anchoring the
                # intermediate ones would be wrong as well as pointless: a
                # squad walking a detour is strung out along it by design, and
                # pulling each step toward the models already parked at the far
                # end would bend the route out of shape.
                target_x, target_y = _anchored_slot(model, (target_x, target_y), placed)
            target_x, target_y = _clamp_target_against_friendly_models(
                model, target_x, target_y, squad, movement_controller, placed, caller="route")
            _advance_model_toward(movement_controller, model, target_x, target_y)
        if placed and not _in_coherency_with_any(model, placed):
            _close_up_to_placed(movement_controller, squad, model, placed)
        placed.append(model)
    return _centroid(squad), budget


def _route_length(origin, waypoints):
    """Total travel along a find_route() waypoint list, starting from origin.

    This is the "how far is it really" figure for a unit that cannot cross
    Dense terrain (rule 13.06) - it is what the straight-line distance is NOT,
    and confusing the two is what stalled the reported squads. Measured on the
    real demo terrain: a Warbiker squad 9.0" from its destination in a straight
    line had a 17.1" road to it, because the ruin wall between them has to be
    driven around."""
    total = 0.0
    previous = origin
    for waypoint in waypoints:
        total += ((waypoint[0] - previous[0]) ** 2 + (waypoint[1] - previous[1]) ** 2) ** 0.5
        previous = waypoint
    return total


def _route_leads_somewhere(origin, waypoints, target_point):
    """Does this route actually end up closer to target_point than it started?

    find_route() does not only return real routes: when the destination itself
    is blocked it retargets to the nearest unblocked cell, and when the mover
    barely fits anywhere it can hand back a single short hop that leads AWAY.
    A routed candidate is exempted from the straight-line progress bar (see
    consider()) precisely because a genuine detour's first leg points sideways
    - that exemption must not extend to a route that is not a detour at all,
    or the AI trades "walks into a wall" for "walks backwards", which is the
    older bug this file already fixed twice."""
    if not waypoints:
        return False

    def to_target(point):
        return ((point[0] - target_point[0]) ** 2 + (point[1] - target_point[1]) ** 2) ** 0.5

    return to_target(waypoints[-1]) < to_target(origin) - MIN_GOAL_PROGRESS_IN


def _place_rigid_route(movement_controller, squad, waypoints, start):
    """The pathfinder's route walked by the whole squad as ONE rigid block:
    every model is offered the same shared offset at every waypoint, so the
    formation is carried along the detour unchanged.

    Why this exists alongside _place_per_model_route(), which walks the same
    waypoints: that one moves each model independently, and independent
    clamping is exactly how a formation comes apart. A wall that stops half
    the squad and lets the other half through leaves the squad in two pieces,
    confirm_move() rejects the whole attempt on coherency (rule 09.02), and
    nothing was actually gained. That is the failure the user reported for the
    Warbikers, and the log is unambiguous about it: sixteen consecutive
    candidate rejections in one turn, every one of them a coherency split, and
    the squad finished the turn 0.09" from where it started.

    A rigid translation cannot fail that way. Every model moves by the same
    offset, so the pairwise distances inside the squad do not change at all -
    coherency and the 9" spread are invariant, at every waypoint and every
    distance (the same argument _creep_toward() rests on, which is spelled out
    in full there). What it trades away is flow: a single model wedged against
    something caps the shared offset for everyone. So this is offered as a
    SECOND candidate rather than a replacement - per-model goes first and wins
    whenever it holds together, and this catches the case where it doesn't.

    Placement only, no confirm - see _place_per_model_move()'s docstring for
    why the caller has to score before confirming. Returns the squad's centroid
    afterwards, same contract as the other placement plans."""
    start()
    budget = max((movement_controller.remaining_range.get(m.id, 0.0) for m in squad.models), default=0.0)
    for waypoint in waypoints:
        # The offset is measured from the LEAD model, since the route was
        # planned for it, and every model then moves by that SAME vector.
        lead = squad.models[0]
        ox, oy = waypoint[0] - lead.x_in, waypoint[1] - lead.y_in
        leg = (ox * ox + oy * oy) ** 0.5
        if leg < 1e-9:
            continue

        # "Everyone moves by the same offset" has to be enforced on the RESULT,
        # not just requested. clamp_move() cuts each model's step to whatever
        # ITS own lane allows, so simply asking all of them to take the offset
        # leaves the blocked ones behind and the free ones ahead - which is
        # per-model movement wearing a rigid coat, and it breaks formation
        # exactly like the real thing (measured while building this: the first
        # version of this function tore the Warbikers into two groups on its
        # first leg). So: ask each model where it COULD get to, take the
        # distance the most constrained one managed, and move everybody
        # exactly that far. That distance is on every model's own already-
        # validated path, so no one is asked to do anything its own clamp
        # rejected, and the shared offset makes coherency invariant.
        shared = leg
        for model in squad.models:
            reached = movement_controller.clamp_move(model, model.x_in + ox, model.y_in + oy)
            shared = min(shared, ((reached[0] - model.x_in) ** 2 + (reached[1] - model.y_in) ** 2) ** 0.5)
        if shared < MIN_RIGID_LEG_IN:
            break  # the formation as a whole cannot get through here

        scale = shared / leg
        for model in squad.models:
            new_x, new_y = movement_controller.clamp_move(
                model, model.x_in + ox * scale, model.y_in + oy * scale)
            model.x_in, model.y_in = new_x, new_y
            movement_controller.try_commit_segment(model)
    return _centroid(squad), budget


# One line per per-model sweep, so a movement report can be read from the
# log instead of re-run from raw coordinates: which candidate won and how much
# of the intended distance it delivered, how many candidates were tried and
# filed as fallbacks, how often the friendly clamp cut a model's target short
# (see _clamp_target_against_friendly_models) and how many passes ended split.
# Measured on the reported 21-model blob (measure_reported_moves.py case C):
# 42 candidates, 535 truncations against 286 clear landings, 4 split passes -
# none of which the old log could show. Module-level because the sweep is one
# synchronous call and the counters are written from three functions that
# share no argument.
_sweep_stats = {}


def _reset_sweep_stats():
    _sweep_stats.clear()
    _sweep_stats.update(candidates=0, fallbacks=0, truncated=0, clear=0, relanded=0,
                        split_passes=0, winner=None, achieved=0.0, intended=0.0)


def _log_move_sweep(movement_controller, squad, moved):
    log = getattr(movement_controller, "game_log", None)
    if log is None or not _sweep_stats:
        return
    s = _sweep_stats
    won = (f"won={s['winner']} ({s['achieved']:.2f}\" of {s['intended']:.2f}\")"
           if moved and s["winner"] else "won=NONE")
    log.add(
        f"  [move sweep] {squad.name}: {s['candidates']} candidates, {won}, "
        f"fallbacks {s['fallbacks']}, friendly clamp: clear {s['clear']}, "
        f"relanded {s.get('relanded', 0)}, truncated {s['truncated']}, "
        f"split passes {s['split_passes']}",
        file_only=True,
    )


def _advance_toward_per_model(movement_controller, squad, target_point, start_move_fn=None, confirm_fn=None, cancel_fn=None, flying=False):
    """The per-model sweep (see _advance_toward_per_model_impl) plus its
    [move sweep] log line - split so the line is written on EVERY exit of a
    function that returns from a dozen places."""
    _reset_sweep_stats()
    moved = _advance_toward_per_model_impl(
        movement_controller, squad, target_point, start_move_fn=start_move_fn,
        confirm_fn=confirm_fn, cancel_fn=cancel_fn, flying=flying)
    _log_move_sweep(movement_controller, squad, moved)
    return moved


def _advance_toward_per_model_impl(movement_controller, squad, target_point, start_move_fn=None, confirm_fn=None, cancel_fn=None, flying=False):
    """Fallback for when NO whole-squad rigid translation
    (_advance_toward_bulk()) can find a legal way to move together - moves
    each model INDIVIDUALLY toward target_point, exactly like a human
    dragging one model at a time (clamp_move()/try_commit_segment(), each
    capped by its own remaining range and independently routed around
    whatever's actually in ITS OWN path). Unlike the bulk version's single
    shared offset - where every model is clamped against the SAME
    requested vector, so one model wedged against an obstacle drags the
    whole rigid attempt down with it even though its squadmates have room
    to spare - a model with a clear lane can travel its own full distance
    while a boxed-in one simply falls behind, letting the squad flow
    around a single obstacle instead of being blocked by it as one block.

    Real user report: "sie muss natürlich auch in der Lage sein, Modelle
    individuell zu platzieren, damit die Bewegung passt" - the widened
    angle/distance sweep in _advance_toward_bulk() still shares ONE
    direction across the whole squad per attempt; a genuinely awkward
    formation (e.g. squeezed between two obstacles on either side) can
    have no single shared direction that works for every model at once,
    even though moving each one along its own best path clearly would.

    Coherency (rule 09.02) is only checked at the very end via
    confirm_move(), so this can still legally fail if the models end up
    too spread out - retried at progressively shorter target distances
    (same ADVANCE_DISTANCE_FRACTIONS ladder as the bulk version) to keep
    formation tighter when the full-distance attempt doesn't hold
    together. Same start_move()-per-attempt requirement as the bulk
    version, for the same reason (cancel_move() wipes remaining_range).

    Real, severe bug found via user report ("sie bewegt ihre Fahrzeuge ab
    Zug 2 nicht mehr", after bulk had already been disabled for VEHICLE
    squads per a separate user directive): every model here used to head
    STRAIGHT toward target_point with no directional variety at all (only
    ADVANCE_DISTANCE_FRACTIONS varied the DISTANCE, never the direction) -
    unlike _advance_toward_bulk(), which already sweeps
    ADVANCE_ANGLE_JITTER_DEG. As long as bulk was still tried as a fallback,
    its own angle sweep quietly covered for this gap; the moment a
    VEHICLE-only squad (no bulk fallback at all, see _advance_toward()) hit
    so much as a single Dense wall sitting right along the one straight
    line toward the enemy, there was no alternate direction left to try at
    all - reproduced directly against the real demo scene's Crisis
    Starscythe Battlesuits: stuck reporting "cannot end their move on top
    of Dense terrain" on every one of 3 fraction attempts, round after
    round, because all 3 pointed the exact same direction. Now sweeps the
    same ADVANCE_ANGLE_JITTER_DEG angles (rotated around the squad's own
    centroid, same helper _advance_toward_bulk() uses) as an outer loop
    around the existing fraction ladder.

    `start_move_fn`/`confirm_fn`/`cancel_fn` default to movement_controller's
    own start_move/confirm_move/cancel_move (a Normal Move) - see
    _advance_toward_bulk()'s docstring for why this is parametrized (Fall
    Back reuses this same retry ladder).

    Returns True (squad moved, formation possibly no longer rigid) if any
    angle/fraction attempt held together; False if every one couldn't
    produce a legal formation.

    Real, severe bug found via user report ("kann es sein, dass es dieses
    Überlappungsproblem auch beim normalen Move gibt?" - following the same
    bug just fixed for charges): every model here moves toward the exact
    SAME shared target_point, completely independently - an even more
    direct case than a charge's "each model's own nearest enemy", since
    with a generous enough remaining_range, EVERY model can reach that
    identical point exactly, landing squarely on top of every other one.
    Reproduced directly: 5 models advancing toward a distant point failed
    12 STRAIGHT angle-jitter attempts (every one of them, at the full-
    distance fraction) with "Models cannot end their move on top of
    another model" before happening to succeed only once the distance
    fraction dropped low enough to accidentally undershoot the point. For
    a VEHICLE-only squad (no bulk fallback at all, per the existing
    directive - see _advance_toward()), a slightly less fortunate geometry
    would exhaust the entire 36-combination sweep and simply never move.
    Fixed the same way as _charge_per_model(): each model's naive
    destination is clamped short of colliding with its OWN squadmates
    already placed this same attempt (see _clamp_target_against_friendly_
    models()'s own docstring), models processed closest-to-target first so
    the ones that can actually reach it claim their spot before any that
    have to stack in behind.

    Real, severe bug found via user report ("die KI bewegt sich immer noch
    nicht wirklich nach vorne... den Devilfish hat sie gar nicht bewegt...
    ich glaube sie kommt mit der Bewegung von großen Fahrzeugen nicht
    klar") plus the user's own correct diagnosis: the angle sweep below
    only ever rotates the aim around the FAR target_point - once a model
    ends up pressed flush against a wall it can't pass through (VEHICLE/
    MONSTER, no INFANTRY/BEASTS/SWARM/MOBILE keyword - clamp_move()'s own
    obstacle-crossing prevention already correctly stops it there, verified
    directly), every one of those rotated aims still points back into the
    same wall for a wall of any real size - but usually still finds SOME
    angle with a tiny sliver of legal room to slide along the wall's face,
    which the existing "accept the first success" logic happily takes as
    "done", so the model stalls flush against the wall for every future
    call, making only microscopic (technically legal, functionally
    negligible) progress forever - confirmed directly (a test vehicle
    blocked by a 16"-tall wall advanced normally for one turn, then made
    ZERO further progress for the next two, matching the real Devilfish -
    deployed a few inches from actual Dense ruin walls - ending up parked
    at the exact same coordinate turn after turn). _route_around_waypoints()
    (a bounded "aim at the blocking obstacle's corner" heuristic, not real
    pathfinding) is tried FIRST, ahead of the angle sweep, exactly to avoid
    exhausting into one of those negligible "successes" before ever trying
    a destination actually likely to go somewhere - see its own call site's
    comment for why this is tried first rather than as a last resort. A
    model with a genuinely clear direct lane (the common case) never gets
    any corner-routing candidates in the first place."""
    start = start_move_fn if start_move_fn is not None else movement_controller.start_move
    confirm = confirm_fn if confirm_fn is not None else movement_controller.confirm_move
    cancel = cancel_fn if cancel_fn is not None else movement_controller.cancel_move
    cx, cy = _centroid(squad)

    # Corner-routing (see _route_around_waypoints()) is tried FIRST, ahead of
    # the blind angle-jitter sweep below, whenever something's actually
    # blocking the direct path - deliberately NOT the other way around (a
    # "try the normal sweep, only fall back to corner-routing if it fails
    # outright" design was tried and rejected: a model pressed flush against
    # a wall usually still finds SOME rotated angle with a sliver of legal
    # room to slide along the wall's face, so the sweep "succeeds" with a
    # technically-legal but functionally-negligible move long before ever
    # exhausting into a real fallback - confirmed directly, this is exactly
    # what was still happening with corner-routing only as a last resort).
    # Trying corner-routing first sidesteps that without needing to revert
    # an already-"successful" confirm_move() and re-search - which would
    # risk corrupting move types whose confirm() has its own side effects on
    # success (e.g. FallBackController.confirm() kicking off a Desperate
    # Escape Hazard Roll) - a model with a genuinely clear direct lane
    # (the overwhelmingly common case - nothing blocking it at all) never
    # even computes a candidate here (_route_around_waypoints() returns an
    # empty list whenever nothing blocks target_point), so this is a no-op
    # for it.
    representative = squad.models[0]

    # Real pathfinding (game/pathfinding.py's find_route() - grid + A*, see
    # its own module docstring) tried FIRST, ahead of even the corner-
    # routing heuristic below: corner-routing only ever escapes the closest
    # CORNER_ROUTE_MAX_OBSTACLES blockers of each kind one at a time and
    # cannot compose around several simultaneous obstacles/models at once -
    # exactly the documented "surrounded by a dozen friendly models plus
    # terrain at once" ceiling (see _movement_priority_key()'s own docstring
    # for the real Devilfish case this was found on). find_route() is a real
    # graph search, so it composes around any number of simultaneous
    # blockers - but it still only ever PROPOSES a waypoint list;
    # _place_per_model_route() re-validates every single step exactly as
    # strictly via clamp_move()/try_commit_segment(), never trusts the route
    # blindly, same as every other candidate in this file. Uses
    # profile.movement_in as the movement-budget estimate
    # (movement_controller.remaining_range isn't populated until start() is
    # called - the same pre-start estimate _handle_movement()'s own Staging
    # option already relies on); an Advance bonus not yet rolled/applied at
    # this point just means the computed route may undershoot what's
    # actually achievable this turn, not that it's wrong.
    # Real, separate bug found while wiring this in: neither this pathfinding
    # attempt NOR the corner-routing fallback below know anything about
    # Take to the Skies (rule 21.03) - `flying` (True whenever
    # _handle_movement() is about to call take_to_the_skies() for this
    # squad, e.g. any BATTLESUIT/Devilfish-class unit with the FLY keyword)
    # is only applied INSIDE start(), which hasn't run yet when this
    # pre-start routing decision is made. Both would still see the
    # (irrelevant, since flight bypasses it) nearby terrain/models as
    # "blocking" and hand back a needlessly short detour waypoint - which
    # then "succeeds" immediately once start() actually does make the model
    # unobstructed, stranding it at that near detour point instead of
    # continuing on toward the real target_point. User report ("ghostkeel
    # hat sich aber nur 1\" bewegt", despite the turn plan saying "advance")
    # matches this exactly: Ghostkeel always flies (FLY keyword), so this
    # was very likely never a real obstacle-avoidance failure at all. Fix:
    # skip straight to the plain angle/fraction sweep below when flying -
    # its very first attempt (angle 0, full fraction, i.e. a straight line
    # at target_point) now succeeds immediately, since nothing but final-
    # position overlap (still enforced regardless of flying, see
    # model_terrain_violation()'s own docstring) can stop it.

    # Candidate plans are SCORED rather than "first one that doesn't error
    # wins" (see _squad_progress() and _GOOD_PROGRESS_FRACTION): an attempt
    # that clears the good-enough bar is confirmed straight away (the common
    # case - on open ground the very first plan now carries the whole squad
    # its full distance), while a legal-but-feeble one is cancelled and kept
    # only as a fallback, so the sweep gets a fair chance to find something
    # better instead of settling for the first stub of a move that happened
    # to pass validation.
    origin_centroid = (cx, cy)
    fallbacks = []  # [(achieved, displacement, plan, route_length)] - best re-run at the end

    distance_to_target = ((target_point[0] - cx) ** 2 + (target_point[1] - cy) ** 2) ** 0.5

    def consider(plan, route_length=None, label=""):
        """Run one candidate placement; confirm it if it's good enough,
        otherwise cancel and file it as a fallback. Returns True only if the
        squad has actually been left moved and confirmed.

        `route_length` marks the candidate as one the PATHFINDER produced,
        and is how long the road it proposed is. It changes which yardstick
        the two bars below use - see the comments there.

        Real, severe bug found by reproducing the user's report ("die bikes
        sind immer rechts stuck und ruecken niemals weiter vor. sie kommen
        einfach nicht an der wand vorbei"): straight-line progress is the
        WRONG measure for a unit that has to go around something. Measured
        against the real demo terrain, with the Warbikers standing inside the
        NE ruin's L-walls exactly where the log had them, 13 of 35 tested
        destinations produced literally 0.00" of movement - every one of them
        a destination on the far side of a wall. The trace is unambiguous: for
        a goal 9.0" away with a 17.1"-long legal road to it, find_route()'s
        candidate carried the squad 6.66" along that road and was DISCARDED
        for scoring 0.03" of straight-line progress, a hair under the 0.5"
        bar. Every remaining candidate is a straight line into the wall, so
        the squad stood still. A detour's first leg is close to perpendicular
        to the goal by definition, so this rejected precisely the units that
        need routing - the ones that cannot cross Dense terrain (rule 13.06:
        Warbikers, Deff Dread, Trukks), which is exactly the user's
        "fahrzeuge/mounted und waende sind immernoch ein riesen problem"."""
        after, budget = plan()
        _sweep_stats["candidates"] = _sweep_stats.get("candidates", 0) + 1
        progress, displacement = _squad_progress(origin_centroid, after, target_point)
        if displacement < MIN_ROUTE_PROGRESS_IN:
            cancel()  # nothing really happened - not even worth keeping
            return False
        if route_length is None and progress < MIN_GOAL_PROGRESS_IN:
            # Covered ground but got no closer: the angle sweep reaches all
            # the way to 180 degrees, so a candidate can shuffle a squad
            # sideways (or backwards) and still clear the displacement bar.
            # Filing it lets a purely lateral move win the fallback round and
            # be committed, which is what the user sees as "manchmal bewegt
            # sich der Devilfisch statt nach vorne einfach sinnlos nach
            # rechts, wenn vorne nicht passt". Discard it instead, so a
            # shorter move that actually goes the right way - ultimately
            # _creep_toward(), which is strictly toward the target - gets the
            # chance rather than being pre-empted by a longer useless one.
            #
            # Skipped entirely for a routed candidate: this bar exists to
            # catch a move with no sense of direction, and a route from
            # find_route() has the opposite problem - it is the SHORTEST legal
            # path to the goal, so it never wanders, it just cannot always
            # start out pointing at the goal. Distance covered along it is
            # then the honest measure of progress, and that is what the
            # displacement bar above already checks.
            cancel()
            return False
        # "Good enough" is measured against what this move could realistically
        # have achieved - whichever is smaller, the squad's whole movement
        # budget or the distance to the target itself. Without that second
        # term, a squad standing 2" from an objective it can fully reach could
        # never clear a bar set at half its 7" budget.
        #
        # For a routed candidate both halves switch to road terms: how far it
        # travelled, against how much of the road was realistically walkable
        # this turn. Comparing a detour's straight-line progress to a
        # straight-line target distance is the same category error as above,
        # one step further on - it would keep the route out of the "confirm it
        # now" branch and leave it to win a fallback round it might not.
        achieved = displacement if route_length is not None else progress
        reachable_this_turn = route_length if route_length is not None else distance_to_target
        intended = min(reachable_this_turn, budget) if budget > 0 else reachable_this_turn
        if achieved >= _GOOD_PROGRESS_FRACTION * intended:
            confirm()
            if not movement_controller.errors:
                _sweep_stats.update(winner=label, achieved=achieved, intended=intended)
                return True
            cancel()
            return False
        cancel()
        # Filed under `achieved` so a routed candidate is ranked by the road
        # distance it covered, on the same scale the fallback round re-checks.
        fallbacks.append((achieved, displacement, plan, route_length, label))
        _sweep_stats["fallbacks"] = _sweep_stats.get("fallbacks", 0) + 1
        return False

    if not flying:
        estimated_budget = coldstar.effective_movement_in(representative)  # see game/coldstar.py
        if estimated_budget > 0:
            hard_obstacles = pathfinding.blocking_obstacles_for(representative, movement_controller.obstacles)
            # Real, related bug found while fixing the false-success one
            # above: find_route()'s own hard_models avoidance only keeps
            # clear of an enemy's literal BASE circle, not the ADDITIONAL
            # Engagement Range (2") a Normal/Advance/Fall Back move must
            # also end clear of - a route that hugs an enemy-heavy area
            # closely enough can satisfy "never crosses a base" while still
            # ending every waypoint within that 2" buffer, wasting the whole
            # attempt on a route try_commit_segment() was always going to
            # reject (now correctly caught as a failure by
            # _place_per_model_route() above, instead of masked as a
            # zero-distance "success" - but still worth avoiding computing
            # in the first place). Padding each enemy model's radius by
            # ENGAGEMENT_RANGE_IN for pathfinding purposes only (NOT the
            # mover's own radius, which also inflates Dense-terrain
            # clearance and has nothing to do with engagement) steers the
            # search around that buffer from the start, same as a human
            # planning a route would account for it.
            hard_models = _engagement_padded_models(
                pathfinding.enemy_models_for(representative, movement_controller.all_tokens), ENGAGEMENT_RANGE_IN,
            )
            route = pathfinding.find_route(
                (representative.x_in, representative.y_in), target_point, representative.radius_in, estimated_budget,
                hard_obstacles, hard_models, movement_controller.board_width_in, movement_controller.board_height_in,
            )
            origin = (representative.x_in, representative.y_in)
            if route and _route_leads_somewhere(origin, route, target_point):
                road = _route_length(origin, route)
                # Per-model first (models flow around what is in each one's own
                # lane), then the SAME route walked as one rigid block. The
                # rigid version exists because per-model routing is the one
                # thing that can pull a formation apart: each model is clamped
                # separately, so a wall that stops half the squad and not the
                # other half breaks coherency (rule 09.02) and the whole
                # attempt is thrown out. That is not a hypothetical - it is
                # what the reported game did, sixteen times in a row for the
                # Warbikers, every single rejection a coherency one. A rigid
                # translation cannot do that: it moves every model by the same
                # offset, so the pairwise distances inside the squad never
                # change (the invariant _creep_toward() is built on). Until
                # now nothing was both routed AND rigid - _place_per_model_
                # route() is routed but per-model, _creep_toward() is rigid but
                # dead straight, so a boxed-in squad had no candidate that
                # could get around a wall without risking its formation.
                if consider(lambda: _place_per_model_route(movement_controller, squad, route, start),
                            route_length=road, label="route"):
                    return True
                if consider(lambda: _place_rigid_route(movement_controller, squad, route, start),
                            route_length=road, label="rigid-route"):
                    return True

        for waypoint in _route_around_waypoints(representative, target_point[0], target_point[1], movement_controller.obstacles, movement_controller, squad):
            for fraction in ADVANCE_DISTANCE_FRACTIONS:
                if consider(lambda w=waypoint, f=fraction: _place_per_model_move(movement_controller, squad, w, f, start),
                            label=f"corner@{fraction}"):
                    return True

    # LAST: the squad as a DEFORMABLE MASS. Every candidate above keeps the
    # shape the squad is standing in, so a unit whose own FOOTPRINT is what
    # blocks it has nothing up there that can help - and measured on the
    # crowded board that is most of them. At every fraction of their move:
    #
    #   Stormboyz 12" forward   rigid translation BLOCKED   packed block fits
    #   Deffkoptas 12" forward  rigid translation BLOCKED   packed block fits
    #   Boyz mob   6" forward   rigid translation BLOCKED   packed block fits
    #   Meganobz   5" forward   rigid translation BLOCKED   packed block fits
    #
    # Offered as a candidate rather than substituted for the sweep, because
    # packing is NOT free: closing up costs the rear models extra walking, and
    # measured on those same units in isolation it gained the Stormboyz 12
    # points of achievable progress and the Deffkoptas 21 while costing the
    # Meganobz 17 and the Beast Snagga 20. consider() applies the same bar to
    # it as to everything else, so it wins only where it really is better.
    #
    # Measured contribution over three turns of the full army, A/B against the
    # same run with this block disabled: 17 of 42 moves end packed, median
    # share of achievable progress 62% -> 64%, total ground 201.4" -> 206.9",
    # moves under 60% of achievable 47.6% -> 40.5%, squads left standing still
    # 2 -> 0. On an empty board it is neutral (total 267.2" -> 267.8").
    #
    # Placed last on principle - the sweep's opening pass is angle 0, the plain
    # move straight at the target, and a squeeze should not pre-empt an
    # ordinary advance that goes further. Measured, the position makes no
    # difference either way (byte-identical results): packing rarely clears
    # consider()'s immediate bar and mostly competes in the fallback round,
    # ranked against the others on distance achieved.
    #
    # No move is open at this point - every plan starts its own - so the reach
    # comes from the move characteristic, the same estimate the routing branch
    # above uses (coldstar.effective_movement_in, which honours the Coldstar
    # override).
    packing_reach = coldstar.effective_movement_in(representative)

    def packed_plan(spot):
        """consider()'s plan contract: (centroid afterwards, the budget to
        judge it against).

        A refusal reports the squad where it already stands, which scores as
        zero progress - consider() then cancels, and that cancel is a no-op
        because _place_packed() only opens the move once it has slots to walk
        into."""
        _place_packed(movement_controller, squad, spot, target_point, start)
        return _centroid(squad), packing_reach

    for fraction in ADVANCE_DISTANCE_FRACTIONS:
        spot = _point_toward(squad, target_point, packing_reach * fraction)
        if spot is not None and consider(lambda p=spot: packed_plan(p), label=f"packed@{fraction}"):
            return True

    for fraction in ADVANCE_DISTANCE_FRACTIONS:
        for angle in ADVANCE_ANGLE_JITTER_DEG:
            rotated_target = _rotate_point_around(cx, cy, target_point[0], target_point[1], angle)
            if consider(lambda t=rotated_target, f=fraction: _place_per_model_move(movement_controller, squad, t, f, start),
                        label=f"sweep{angle:+.0f}@{fraction}"):
                return True

    # Nothing cleared the good-enough bar. Rather than give up and remain
    # stationary (which is what the old "first legal attempt wins" loop
    # effectively did once every attempt failed), fall back to the best
    # partial move actually seen - re-running it is safe because these plans
    # are fully deterministic given the same board state, and the sweep
    # cancelled each one back to the starting position. The top few are tried
    # in turn, since a plan is only scored on its POSITIONS here - whether it
    # also survives confirm_move()'s squad-wide coherency check isn't known
    # until it's actually confirmed.

    fallbacks.sort(key=lambda entry: (entry[0], entry[1]), reverse=True)
    for _achieved, _displacement, plan, route_length, label in fallbacks[:_MAX_FALLBACK_RETRIES]:
        after, _budget = plan()
        # Re-score the RE-RUN, don't trust the score the sweep recorded. A
        # replayed plan does not always reproduce its original placement, and
        # when it collapses to a near-zero move confirm() has nothing to
        # object to - the squad is simply back where it started, which was
        # already legal - so it reports success at no movement at all. That
        # false success then swallows the whole attempt: measured on a
        # crowded 254-scenario stress run, every single squad that ended up
        # standing still got there this way, and _creep_toward() below was
        # never reached even once. Same failure shape as the one
        # _place_per_model_move()'s docstring describes, one level up.
        # Both bars on the re-run, for the same reason consider() applies both:
        # a replay that drifts can land sideways or short of the goal, and the
        # displacement check alone would wave that through. A routed candidate
        # skips the straight-line bar here too, on exactly the same grounds as
        # in consider() - re-imposing it at the replay would undo the fix and
        # is where a detour would quietly die instead.
        replay_progress, replay_displacement = _squad_progress(origin_centroid, after, target_point)
        if replay_displacement < MIN_ROUTE_PROGRESS_IN:
            cancel()
            continue
        if route_length is None and replay_progress < MIN_GOAL_PROGRESS_IN:
            cancel()
            continue
        confirm()
        if not movement_controller.errors:
            _sweep_stats.update(winner=f"fallback:{label}",
                                achieved=replay_displacement if route_length is not None else replay_progress,
                                intended=min(route_length if route_length is not None else distance_to_target,
                                             _budget) if _budget > 0 else distance_to_target)
            return True
        cancel()
    return False


# How many halving steps the creep fallback spends locating the largest legal
# translation, and the smallest result still worth committing.
_CREEP_BISECTION_STEPS = 7
MIN_CREEP_PROGRESS_IN = 0.5


def _creep_toward(movement_controller, squad, target_point, start, confirm, cancel):
    """Last resort before standing still: commit the LARGEST rigid translation
    toward target_point that is still legal, found by bisection.

    User framing that prompted this ("wenn der move, den ich vorhatte nicht
    klappt, dann versuche ich eben einen etwas kuerzeren move, aber bleibe
    nicht einfach stehen") - every other stage in this file is all-or-nothing:
    a candidate either clears its bar or is discarded whole, so a squad whose
    every candidate fails ends up not moving at all.

    Why bisection is sound here rather than just another heuristic: a RIGID
    translation moves every model by the same offset, so the pairwise
    distances inside the squad do not change at all. Coherency (rule 09.02)
    and the 9" spread are therefore INVARIANT under it - a squad that is
    coherent where it stands is coherent at every translated position, at any
    distance. That is exactly the condition the caller cannot check mid-move,
    and it is the one this fallback cannot break. What remains - terrain,
    model overlap, ending in an enemy's Engagement Range - is per-model and
    degrades continuously as the distance shrinks, with "no move at all"
    (legal by definition, the squad is standing there) as the limit. So some
    legal distance always exists, and bisection finds close to the largest.

    That argument only holds while the translation really is rigid, though,
    and _translate_squad_toward() clamps each model on its own - so a single
    blocked model turns the trial into a partial translation that CAN break
    coherency, and the invariant quietly stops applying. A trial is therefore
    rejected unless the translation came back rigid, which is what makes the
    reasoning above true of the code and not just of the idea.

    Trials are placement-then-rollback: confirm_move() has irreversible side
    effects on success, so legality is judged on the candidate positions
    directly and only the winning distance is actually confirmed."""
    cx, cy = _centroid(squad)
    dx, dy = target_point[0] - cx, target_point[1] - cy
    to_target = (dx * dx + dy * dy) ** 0.5
    if to_target < 1e-9:
        return False

    origin = [(m.x_in, m.y_in) for m in squad.models]

    def revert():
        for model, (x, y) in zip(squad.models, origin):
            model.x_in, model.y_in = x, y

    def reachable(distance):
        """Place the squad `distance` along the line and report how far the
        centroid actually got, or None if that placement isn't legal."""
        start()
        rigid = _translate_squad_toward(movement_controller, squad, target_point, distance)
        errors = (
            squad.check_coherency()
            + squad.check_terrain(movement_controller.obstacles)
            + squad.check_model_overlap(movement_controller.all_tokens)
        )
        if not rigid:
            # Not a rigid translation after all - some model was clamped, so
            # this trial has no claim on the coherency invariant above. Shorter
            # distances are still worth trying: that is what the bisection is
            # for, and a shorter offset is exactly what an obstructed model
            # needs.
            errors.append("not rigid")
        if not errors and squad.is_engaged(movement_controller.all_tokens):
            errors.append("engaged")
        moved = _squad_progress(( cx, cy), _centroid(squad), target_point)[1]
        cancel()
        revert()
        return None if errors else moved

    start()
    budget = min((movement_controller.remaining_range.get(m.id, 0.0) for m in squad.models), default=0.0)
    cancel()
    revert()
    hi = min(budget, to_target)
    if hi <= MIN_CREEP_PROGRESS_IN:
        return False

    best = reachable(hi)
    if best is None:
        lo = 0.0
        best = 0.0
        for _ in range(_CREEP_BISECTION_STEPS):
            mid = (lo + hi) / 2.0
            achieved = reachable(mid)
            if achieved is None:
                hi = mid
            else:
                lo, best = mid, achieved
        hi = lo

    # Judge the distance ACTUALLY covered, not the distance asked for.
    # reachable() has always measured it and this used to throw the number
    # away: a translation straight into a wall is clamped back to the starting
    # position, which is legal (the squad is standing where it already stood),
    # so it reports no errors and this committed a confirm_move() that moved
    # the squad zero inches - and returned True, so the caller logged "moved"
    # and never fell through to remain_stationary(). That is the same
    # false-success shape both placement stages above were already fixed for,
    # and it is why the reported Deff Dread looked frozen with nothing in the
    # log to say so: reproduced against map2's central ruin at (26.70,15.94),
    # _advance_toward() returned True having moved 0.00".
    #
    # Reporting failure instead is also the better outcome under the rules:
    # the caller falls back to remain_stationary(), which is what the unit
    # actually did, and which keeps [HEAVY] (rule 24.16) instead of spending a
    # move that never happened.
    if best < MIN_CREEP_PROGRESS_IN:
        return False

    start()
    _translate_squad_toward(movement_controller, squad, target_point, hi)
    confirm()
    if movement_controller.errors:
        cancel()
        revert()
        return False
    return True


def _regroup_slot_targets(squad, slots):
    """Match each model to one packed slot, cheapest pair first, so nobody has
    to walk across the formation to reach a spot a nearer squadmate could have
    taken. Returns {model index -> (x, y)}."""
    pairs = sorted(
        (((m.x_in - s[0]) ** 2 + (m.y_in - s[1]) ** 2, mi, si)
         for mi, m in enumerate(squad.models)
         for si, s in enumerate(slots)),
        key=lambda p: p[0],
    )
    taken_models, taken_slots, chosen = set(), set(), {}
    for _cost, mi, si in pairs:
        if mi in taken_models or si in taken_slots:
            continue
        taken_models.add(mi)
        taken_slots.add(si)
        chosen[mi] = slots[si]
    return chosen


def _needs_regroup(squad):
    """Whether this unit should re-form before it does anything else: it is out
    of rule 09.02's coherency, so the ordinary sweep cannot help it at all (see
    _regroup_move()).

    TRIED AND REJECTED, measured rather than argued, so it is not tried again:
    also firing this for a unit that is CONNECTED but merely strung out. The
    motivation was real - config.SPREAD_LIMIT_PLAYERS lifts the 9" limit for the
    AI, which took away the thing that used to force units back into shape, and
    the widest unit promptly went from 8.6" to 12.8" over three turns of
    measure_crowded_movement.py. But re-forming IS a move, and it is paid for
    out of the same budget: measured, the mob this was aimed at went from 42% to
    7% of its achievable progress, stalls doubled, and the spread it bought back
    was not even a fix. The same verdict came out of the other two attempts at
    tidying units up mid-move (see _tightening_factor()).

    Compaction has to come from the PLACEMENT - the packers in
    game/formation_layout.py already build tight blocks at deployment, disembark
    and arrival - not from spending a turn's movement on it afterwards."""
    return len(squad.models) > 1 and bool(squad.check_coherency())


def _regroup_move(movement_controller, squad, target_point, start, confirm, cancel):
    """Re-form a squad that enters its move out of shape - either out of rule
    09.02's coherency outright, or merely strung out far past what it should
    hold (see _needs_regroup()) - instead of aiming a broken formation at the
    enemy and having the whole move thrown away.

    Real, severe bug, reported and then reproduced from
    logs/game_20260816_210737.log: Meganobz + Warboss in Mega Armour made an
    Emergency Disembark (18.05), were shot down from 7 models to 4, and ended
    the phase split 3+1 with a 4.93" gap. The following Movement phase logged
    SEVENTEEN consecutive `[coherency] could not end its move here`
    rejections, moved 0.00", and the end-of-turn Regaining Coherency rule then
    destroyed three of the four survivors. Reproduced exactly: with the squad
    one model short of coherency, _advance_toward() returns False having moved
    nothing at all; the identical squad made coherent moves its full 5".

    The cause is a mismatch, not a missing check. Everything inside this file
    tolerates a squad that was ALREADY broken (_place_per_model_move() and
    _run_phase_one() both compare against a `baseline_errors` taken before
    they start, deliberately, so a move is only rolled back for making things
    WORSE) - but confirm_move() is the final gate and is absolute: rule 09.02
    says a unit must END its move in coherency, full stop. So every candidate
    those tolerant stages produce is discarded at the door, including
    _creep_toward(), the last-resort net, whose whole guarantee is that a
    rigid translation cannot CHANGE coherency - which for a squad that starts
    broken means it cannot fix it either. There is no candidate in the sweep
    whose GOAL is to close the gap, so the unit is frozen until the end of the
    turn kills models off it.

    confirm_move() is right and is not touched. What was missing is the move a
    human makes here: walk the stragglers back to the body of the unit.
    game/formation_layout.py's pack_positions() is exactly that shape and is
    already the primitive behind disembark and Ingress placement - it builds a
    block whose single connected group is guaranteed BY CONSTRUCTION rather
    than hoped for, which is precisely the property the sweep cannot offer.

    The block is packed around the centroid of the LARGEST connected group
    (the body of the unit moves least, the stragglers do the walking), pushed
    toward `target_point` by a ladder of fractions of the squad's own budget
    so re-forming does not automatically forfeit the advance, and grown on the
    side the squad is coming FROM so its far edge stays inside the stragglers'
    reach. Every model still goes through clamp_move()/try_commit_segment()
    like every other placement in this file, so this can never put a model
    somewhere the move itself could not.

    Returns True with the squad moved and confirmed, or False having left it
    exactly where it started (the caller's remaining stages then run
    unchanged, and would in any case be no worse off than before)."""
    if not _needs_regroup(squad):
        return False

    origin = [(m.x_in, m.y_in) for m in squad.models]
    body = max(connected_groups(squad.models), key=len)
    ax = sum(m.x_in for m in body) / len(body)
    ay = sum(m.y_in for m in body) / len(body)
    budget = min_model_movement(squad)  # the SLOWEST model has to make it too
    dx, dy = target_point[0] - ax, target_point[1] - ay
    reach = (dx * dx + dy * dy) ** 0.5
    ux, uy = (dx / reach, dy / reach) if reach > 1e-9 else (0.0, 0.0)
    # Grow the block back toward where the squad is standing: packed away from
    # the target instead of into it, the far slots stay reachable.
    base_angle = math.atan2(-uy, -ux) if reach > 1e-9 else -math.pi / 2

    def slot_ok(model, x, y):
        """Standable ground (13.05/13.06) clear of every token outside this
        squad - squadmate spacing and coherency are pack_positions()' own job.
        Filtering the CANDIDATES (rather than discovering it at commit time)
        is what keeps a slot inside a wall from costing the whole block."""
        if model_terrain_violation(model, movement_controller.obstacles, x, y):
            return False
        for other in movement_controller.all_tokens:
            if other.squad is squad:
                continue
            gap = ((x - other.x_in) ** 2 + (y - other.y_in) ** 2) ** 0.5
            if gap < model.radius_in + other.radius_in + 0.05:
                return False
        return True

    aims = [(ax + ux * budget * f, ay + uy * budget * f) for f in _REGROUP_ADVANCE_FRACTIONS]
    # Last rung: meet in the middle. The rungs above all pack the block around
    # the BODY, which asks the stragglers to cover the whole gap on their own -
    # and a straggler further out than one move simply cannot, however short
    # the advance is made. Aiming at the centroid of the WHOLE unit instead
    # walks both halves at each other, which closes twice as much ground and is
    # what a player does when a model is stranded. It gives up position (the
    # body backs up), which is why it is tried only after the others.
    aims.append((sum(mo.x_in for mo in squad.models) / len(squad.models),
                 sum(mo.y_in for mo in squad.models) / len(squad.models)))

    for aim_x, aim_y in aims:
        for model, (ox, oy) in zip(squad.models, origin):
            model.x_in, model.y_in = ox, oy
        start()
        slots = formation_layout.pack_positions(
            squad, aim_x, aim_y, base_angle=base_angle, position_valid=slot_ok,
        )
        targets = _regroup_slot_targets(squad, slots)
        placed = []
        # Nearest-to-its-own-slot first: a model already standing where it
        # belongs claims that ground before one that still has to walk in, the
        # same "first claim wins" order the per-model passes use.
        for index in sorted(range(len(squad.models)),
                            key=lambda i: (squad.models[i].x_in - targets[i][0]) ** 2
                            + (squad.models[i].y_in - targets[i][1]) ** 2):
            model = squad.models[index]
            tx, ty = targets[index]
            tx, ty = _clamp_target_against_friendly_models(
                model, tx, ty, squad, movement_controller, placed, caller="regroup")
            new_x, new_y = movement_controller.clamp_move(model, tx, ty)
            model.x_in, model.y_in = new_x, new_y
            movement_controller.try_commit_segment(model)  # reverts this model alone if illegal
            placed.append(model)
        confirm()
        # The coherency re-check is belt and braces: an empty `errors` after a
        # confirm that actually ran already means rule 09.02 is satisfied, but
        # a confirm that DIDN'T run (a squad the controller refuses to move at
        # all) also leaves `errors` empty, and reporting that as a successful
        # regroup would hand the caller a move it never made.
        if not movement_controller.errors and not squad.check_coherency():
            if movement_controller.game_log is not None:
                movement_controller.game_log.add(
                    f"  [regroup] {squad.name} re-formed into coherency (rule 09.02) "
                    f"instead of standing still",
                    file_only=True,
                )
            return True
        cancel()

    for model, (ox, oy) in zip(squad.models, origin):
        model.x_in, model.y_in = ox, oy
    return False


def _advance_toward(movement_controller, squad, target_point, start_move_fn=None, confirm_fn=None, cancel_fn=None, allow_bulk_fallback=True, flying=False):
    """Rule 09.02's Normal Move, aimed at target_point (either the nearest
    enemy's centroid or a staging point). Tries per-model movement first
    (_advance_toward_per_model() - each model travels its own full,
    independently-routed distance), falling back to the whole squad as one
    rigid block (_advance_toward_bulk()) only if that somehow fails - unless
    `allow_bulk_fallback` is False, in which case per-model is the ONLY
    movement attempted at all. User directive ("Einheiten die aus Fahrzeugen
    bestehen... sollten sich auch immer individuell bewegen. dort auch keine
    bulk moves mehr."): _handle_movement() passes False for any squad whose
    models are all VEHICLE-keyword (e.g. Crisis Battlesuits) - a wide-based,
    often terrain-blocked unit type where a rigid shared-offset translation
    is exactly the thing most likely to get needlessly stuck.

    Real, severe bug found via user report ("die KI macht immer nur noch
    bulk bewegungen... dadurch bleiben einheiten oft hinten stehen"): bulk
    was tried FIRST here until now, and confirm_move() only fails on an
    actually ILLEGAL result (overlap, broken coherency, terrain/board-edge
    violation) - it has no concept of "legal but needlessly short", so a
    rigid translation where one model is wedged against an obstacle/another
    unit drags the WHOLE squad's move down to whatever that one model can
    manage, and confirm_move() happily accepts that short, legal-but-
    suboptimal result. _advance_toward_per_model() almost never even got a
    chance to run, since bulk essentially always "succeeded" in this sense
    - reproduced directly: squads that had clear room to advance
    individually stayed clumped up short of where they could have gone,
    purely because the shared bulk vector was capped by their most boxed-in
    squadmate. _advance_toward_per_model() is a strict superset of what
    bulk can achieve (an open board with nothing in the way produces the
    same result either way, via its own ADVANCE_DISTANCE_FRACTIONS
    coherency-retry ladder), so trying it first can only ever do as well or
    better - bulk is kept only as a defensive fallback, not because it's
    expected to ever actually be needed.

    `start_move_fn`/`confirm_fn`/`cancel_fn`, if given, are passed straight
    through to both stages instead of the movement_controller defaults (a
    Normal Move) - _execute_fall_back() uses this to reuse the exact same
    retry sweep for rule 09.07's Fall Back move (movement_controller.
    start_fall_back_move(mode)/fall_back_controller.confirm()/.decline()
    have to be what (re-)primes/confirms/cancels a Fall Back's retries, not
    a Normal Move's start_move()/confirm_move()/cancel_move()).

    Returns True and leaves the squad moved there if either stage
    succeeded; False if both failed (the caller falls back to
    remain_stationary())."""
    start = start_move_fn if start_move_fn is not None else movement_controller.start_move
    confirm = confirm_fn if confirm_fn is not None else movement_controller.confirm_move
    cancel = cancel_fn if cancel_fn is not None else movement_controller.cancel_move

    # A squad that ENTERS the move out of shape gets one shot at re-forming
    # BEFORE the ordinary sweep. For a squad that is out of coherency outright
    # the sweep cannot succeed at all: every candidate it produces keeps the
    # shape the squad is standing in, and confirm_move() rejects all of them on
    # rule 09.02 (see _regroup_move() for the reported seventeen-rejection
    # freeze this closes). For one that is merely strung out it can succeed but
    # will keep the string - see _needs_regroup() for why that case only exists
    # since the 9" spread limit was lifted for the AI. A squad already in shape
    # - the overwhelmingly common case - reaches the sweep by exactly the same
    # path as before, having paid one connected-components walk for it.
    if _needs_regroup(squad) and _regroup_move(
        movement_controller, squad, target_point, start, confirm, cancel,
    ):
        return True

    if _advance_toward_per_model(
        movement_controller, squad, target_point,
        start_move_fn=start_move_fn, confirm_fn=confirm_fn, cancel_fn=cancel_fn, flying=flying,
    ):
        return True
    if allow_bulk_fallback and _advance_toward_bulk(
        movement_controller, squad, target_point,
        start_move_fn=start_move_fn, confirm_fn=confirm_fn, cancel_fn=cancel_fn,
    ):
        return True

    # Everything above is all-or-nothing: each candidate either clears its bar
    # or is thrown away whole, so a squad whose every candidate fails would
    # stand completely still. Take whatever distance is legal instead - see
    # _creep_toward() for why a rigid translation is the one move shape that
    # cannot break coherency, at any distance.
    #
    # Creep toward the FIRST WAYPOINT of the route before creeping toward the
    # target itself. Both are rigid translations, so both are coherency-safe;
    # the difference is where they point. A straight line at the target runs
    # into whatever is in the way - for a unit that cannot cross Dense terrain
    # (rule 13.06) that is a wall, and the largest legal translation into a
    # wall is roughly nothing, which is why the last-resort net caught nothing
    # for the reported Warbikers. The route's first leg points along the way
    # AROUND it, so the same bisection has real distance to find.
    if not flying:
        waypoint = _first_route_waypoint(movement_controller, squad, target_point)
        if waypoint is not None and _creep_toward(movement_controller, squad, waypoint, start, confirm, cancel):
            return True
    return _creep_toward(movement_controller, squad, target_point, start, confirm, cancel)


def _first_route_waypoint(movement_controller, squad, target_point):
    """The first corner of the pathfinder's route to target_point, or None if
    the way there is straight (or unroutable) - i.e. the direction a rigid
    translation should actually head in when the direct line is blocked."""
    if not squad.models:
        return None
    lead = squad.models[0]
    budget = coldstar.effective_movement_in(lead)
    if budget <= 0:
        return None
    route = pathfinding.find_route(
        (lead.x_in, lead.y_in), target_point, lead.radius_in, budget,
        pathfinding.blocking_obstacles_for(lead, movement_controller.obstacles),
        _engagement_padded_models(
            pathfinding.enemy_models_for(lead, movement_controller.all_tokens), ENGAGEMENT_RANGE_IN),
        movement_controller.board_width_in, movement_controller.board_height_in,
    )
    if not route or not _route_leads_somewhere((lead.x_in, lead.y_in), route, target_point):
        return None
    first = route[0]
    # A first waypoint that is essentially the target itself means the route is
    # a straight line - creeping at it is the very same attempt the caller
    # makes next anyway, so skip the duplicate.
    if ((first[0] - target_point[0]) ** 2 + (first[1] - target_point[1]) ** 2) ** 0.5 < 1e-6:
        return None
    return first


def _translate_squad_for_charge(movement_controller, squad, target_squad, max_distance, clearance=CHARGE_TARGET_CLEARANCE_IN):
    """Rule 11.04: aim to end up within Engagement Range of target_squad,
    NOT at its centroid - _translate_squad_toward()'s "aim at the centroid"
    strategy can walk the charging models straight onto/through the
    target's own models once the roll is generous enough to reach that far,
    which then fails check_model_overlap()/coherency and gets the whole
    charge silently declined (a real bug, found via a reproduction where a
    roll of 11 against a target 8.6" away landed exactly on top of it).

    Picks whichever (own model, enemy model) pair is currently closest, and
    translates the WHOLE squad by a single shared offset (preserving shape/
    coherency) just far enough to bring THAT pair to `clearance` edge-to-edge
    distance. If max_distance (the charge roll, or the Fight phase's 3" pile-
    in range) isn't enough to cover that gap, the squad simply travels as
    far as allowed and ends up short - correctly failing
    check_charge_engagement()/check_pile_in_engagement() afterwards. That's
    not a bug: a charge roll can legitimately come up short, and a pile-in
    isn't required to close the whole distance either.

    `clearance` defaults to CHARGE_TARGET_CLEARANCE_IN (1", comfortably
    inside the 2" Engagement Range, not right on the boundary - a safety
    margin for the FIRST time a unit reaches the enemy via a charge, whose
    max_distance/direction is a one-shot dice roll it can't retry). Rule
    12.03 (Pile In) reuses this same function with a much tighter
    PILE_IN_CLEARANCE_IN instead (see _pile_in_squad()) - reusing
    CHARGE_TARGET_CLEARANCE_IN there would make pile-in a no-op for any
    squad that just charged, since it would already be sitting exactly at
    that same 1" clearance from its own charge move moments earlier."""
    own_model, enemy_model = min(
        ((a, b) for a in squad.models for b in target_squad.models),
        key=lambda pair: edge_distance(pair[0], pair[1]),
    )
    dx = enemy_model.x_in - own_model.x_in
    dy = enemy_model.y_in - own_model.y_in
    center_dist = (dx * dx + dy * dy) ** 0.5
    if center_dist <= 1e-9 or max_distance <= 0:
        return
    desired_center_dist = clearance + own_model.radius_in + enemy_model.radius_in
    travel = max(0.0, min(center_dist - desired_center_dist, max_distance))
    scale = travel / center_dist
    ox, oy = dx * scale, dy * scale
    for model in squad.models:
        new_x, new_y = movement_controller.clamp_move(model, model.x_in + ox, model.y_in + oy)
        model.x_in, model.y_in = new_x, new_y
        movement_controller.try_commit_segment(model)


def _charge_along_route(movement_controller, squad, target_squad, max_distance,
                        clearance=CHARGE_TARGET_CLEARANCE_IN, slots=None):
    """Phase 1 of a charge, driven by a real path instead of a straight leg.

    CHARGE_APPROACH_PLAN's sweep is two straight legs (sidestep, then turn in),
    which clears one obstacle EDGE and nothing more structured. A unit that
    cannot walk through Dense terrain (13.06) and has a wall, a doorway or a
    corner between it and its target needs an actual route, and the Movement
    phase has had one - game/pathfinding.py's find_route() - for a long time.
    Reproduced from the reported case: the Deff Dread's best sweep approach
    left it 5.01" short of Engagement Range on a 9" roll, while the routed path
    is 8.4" and fits inside that roll.

    Carries the WHOLE formation along the route as a rigid translation per leg,
    so coherency is preserved by construction (pairwise distances do not change
    under a shared offset - the same invariant _creep_toward() relies on), then
    hands over to _charge_per_model()'s phase 2 to spread into engagement.
    Every step still goes through clamp_move()/try_commit_segment(), so the
    route is a proposal and never a bypass of any rule.

    Does nothing (leaving the caller's sweep to carry on) when no route is
    found or the unit is already in contact."""
    if not squad.models or not target_squad.models:
        return
    mover, enemy = min(
        ((a, b) for a in squad.models for b in target_squad.models),
        key=lambda pair: edge_distance(pair[0], pair[1]),
    )
    hard_obstacles = pathfinding.blocking_obstacles_for(mover, movement_controller.obstacles)
    others = [t for t in pathfinding.enemy_models_for(mover, movement_controller.all_tokens)
              if t is not enemy]
    route = pathfinding.find_route(
        (mover.x_in, mover.y_in), (enemy.x_in, enemy.y_in), mover.radius_in, max_distance,
        hard_obstacles, others, movement_controller.board_width_in, movement_controller.board_height_in,
    )
    if not route:
        return

    # Stop short of the enemy's base rather than aiming at its centre - the
    # charge has to END at clearance, not on top of the model.
    stop_short = clearance + mover.radius_in + enemy.radius_in
    for leg in route:
        ox, oy = leg[0] - mover.x_in, leg[1] - mover.y_in
        length = (ox * ox + oy * oy) ** 0.5
        if length <= 1e-9:
            continue
        gap_to_enemy = ((enemy.x_in - mover.x_in) ** 2 + (enemy.y_in - mover.y_in) ** 2) ** 0.5
        travel = min(length, max(0.0, gap_to_enemy - stop_short)) if length >= gap_to_enemy else length
        if travel <= 1e-9:
            break
        ox, oy = ox / length * travel, oy / length * travel
        for model in squad.models:
            start_pos = (model.x_in, model.y_in)
            model.x_in, model.y_in = movement_controller.clamp_move(
                model, model.x_in + ox, model.y_in + oy)
            ok, _errors = movement_controller.try_commit_segment(model)
            if not ok:
                model.x_in, model.y_in = start_pos

    # Phase 2 (spread into engagement, roll back anything that breaks
    # coherency) is identical whichever way phase 1 got here, so it is reused
    # rather than duplicated: a zero-length approach leaves the formation where
    # this function already put it.
    _charge_per_model(movement_controller, squad, target_squad, max_distance,
                      clearance=clearance, approach_angle_deg=0.0, detour_fraction=0.0,
                      skip_approach=True, slots=slots)


def _charge_per_model(movement_controller, squad, target_squad, max_distance, clearance=CHARGE_TARGET_CLEARANCE_IN,
                      must_close_to_1in=True,
                      approach_angle_deg=0.0, detour_fraction=0.5, skip_approach=False, slots=None):
    """Fallback for when the whole-squad rigid charge translation
    (_translate_squad_for_charge()) can't find a legal move - moves each
    model individually toward WHICHEVER target_squad model is closest TO
    IT (not the single closest pair shared by the whole squad), each
    capped by the same charge-roll distance (max_distance is flat across
    the unit for a charge - rule 11.04, unlike a Normal Move's per-model M
    characteristic) and independently routed around whatever's actually
    in ITS OWN path via clamp_move() - same "flow around an obstacle
    instead of being blocked as a rigid block" idea as
    _advance_toward_per_model(), applied to a charge move.

    Real user report: "die Charge Rolls waren zwar erfolgreich, aber sie
    bewegt sich dann nicht... da muss sie auch Modell für Modell bewegen"
    - a charge whose roll clears the declare-eligibility bar can still
    fail to physically fit as one rigid block (the same tight-formation-
    vs-obstacle problem _advance_toward_bulk() has), silently declining a
    charge that was otherwise perfectly winnable.

    Unlike _advance_toward_per_model(), there's no distance-fraction retry
    ladder here - `travel` per model is already computed as "only as far
    as needed to reach clearance", not an arbitrary overshoot, so
    shortening it further would just leave that model needlessly short of
    Engagement Range instead of reducing spread. A charge roll that's
    genuinely too short to physically fit is allowed to fail
    (check_charge_engagement(), checked by the caller) - the caller
    declines it the same as always, no different from before this
    function was added.

    Doesn't call start_charge_move()/confirm_charge_move() itself - the
    caller (_handle_charge()) drives those around this, exactly as it did
    around the bulk _translate_squad_for_charge() call.

    Real, severe bug found via user report ("die KI würfelt oft Charge,
    aber führt den Charge dann nicht aus... ich glaube sie ist schlecht
    darin, die Modelle auf engem Raum zu platzieren"): every model here
    used to move toward its own nearest enemy model COMPLETELY
    independently, with each one blind to where its own squadmates were
    landing - clamp_move() (rule 03.01: bases can move THROUGH friendly
    models, just never end on top of one) only ever blocks against ENEMY
    models during the drag itself; overlap between this squad's OWN models
    was only ever caught much later, by confirm_charge_move()'s
    check_model_overlap(), with zero chance left to do anything about it.
    The ordinary case for a charge - several models all converging on the
    same one or two enemy models, exactly the "engen Raum" the user
    describes - is precisely when several of THIS squad's own models are
    likely to independently pick the same nearest-enemy target and end up
    stacked on (or very near) each other, silently killing an otherwise
    perfectly winnable charge with no retry at all.

    Fixed by clamping each model's own naive destination against every
    OTHER friendly token already on the board, PLUS every squadmate this
    very call has already placed (`placed`) - reusing game.geometry.
    max_unblocked_fraction_models(), the exact same circle-collision math
    clamp_move() itself already uses for enemy blocking, just aimed at
    friendly models instead. Squadmates not yet processed this call are
    deliberately excluded (they're still sitting at their OLD position,
    which is about to change - checking against that would be pointless).
    Models are processed CLOSEST-to-their-own-nearest-enemy-first, so the
    ones actually able to reach engagement claim their spot first, and any
    squadmate that has to stack in behind them (because the roll/space
    doesn't fit everyone in) is the one that ends up nudged back, not an
    arbitrary one picked by list order.

    Real, severe bug found via user report ("die kroot vom gegner haben
    gerade eine 9\" charge gewürfelt, stealth war 7\" entfernt. aber danach
    haben sie sich nicht bewegt"), reproduced exactly from the log's own
    coordinates: this is the SAME convergence failure that crippled the
    Movement phase (see _formation_slot()), which _charge_per_model() never
    got fixed for. Every model headed for its OWN nearest enemy model, so
    the squad funnelled onto the same few targets; models were processed
    closest-first, and by the time the back rank was reached the front rank
    was already standing in the way, so _clamp_target_against_friendly_
    models() truncated those to zero. Measured on the reported case (10
    Kroot, 7.7" away, 9" roll): six models rushed to y~30 while three stayed
    put at y~22-24 and one shuffled 1.55" - the unit split into two clumps
    ~6" apart. The charge ENGAGEMENT check passed (4 models did reach the
    enemy); it was COHERENCY that failed, and since there is no retry ladder
    for charges the whole charge was then declined.

    Fixed by moving in two phases instead:

    1. Carry the whole formation forward by ONE shared offset - the same
       rigid translation that brings the closest own/enemy model pair to
       `clearance`. Shape is preserved, so this can never break coherency by
       itself, and it gets the entire unit as far forward as the roll allows.
    2. Spend whatever movement each model has LEFT closing individually onto
       its own nearest enemy, to get more models into Engagement Range than
       a rigid block alone would - but roll back any single step that breaks
       squad coherency, so phase 2 can only ever improve on phase 1's
       result, never wreck it.

    Both phases still clamp and validate every model through
    clamp_move()/try_commit_segment() exactly as before.

    `approach_angle_deg`/`detour_fraction` turn PHASE 1 into a detour leg:
    the direction the formation travels as a block is rotated, and only that
    fraction of the roll is spent on it, leaving the rest for phase 2's
    individual close-in (which still heads straight for each model's own
    nearest enemy). Two legs, in other words - sidestep clear of whatever is
    in the way, then turn in - which is what finally gave charges a way
    AROUND an obstacle. The caller (_handle_charge()) sweeps through
    CHARGE_APPROACH_PLAN.

    Real user report ("kroot haben wieder den charge move nicht ausgeführt,
    obwohl der wurf gereicht hat"), reproduced from the log: a Ghostkeel -
    a SINGLE-model unit, so coherency cannot possibly be the cause - rolled
    7" and still failed. It was standing inside a ruin footprint, and the
    straight line to its target ran into a Dense wall: clamp_move() stopped
    it at the wall, it never reached Engagement Range, and
    check_charge_engagement() then declined the whole charge. The Movement
    phase has had an angle sweep, corner routing and A* for exactly this
    since the movement rework; the charge had NOTHING, so a single wall on
    the direct line was an automatic failure with no second attempt.

    Measured on that reproduction: rotating the approach ALONE still failed
    (the angled line grazed the same wall, moving 1.3" of a 7" roll), and
    spending the whole roll on the detour failed too (nothing left to close
    with) - only varying angle AND fraction together actually gets a unit
    around a wall it has the movement to clear."""
    # Melee characters claim an engagement slot BEFORE the rank and file, then
    # everyone else closest-first as before.
    #
    # Slots are handed out in this order and taken as they are claimed, so a
    # character who is not the nearest model gets whatever the mob left over -
    # and rule 12.05 only lets models in Engagement Range fight at all, so
    # "left over" often means he does not swing. Deployment now puts him at the
    # front (game/front_rank.py), which makes this agree with distance most of
    # the time anyway; it is the turns where a move or casualties have shuffled
    # him backwards that this is for.
    #
    # Costs nothing when he cannot use the priority: _ranked_free_slots() only
    # offers slots his remaining movement can actually reach, so a character
    # out of range claims nothing and the order for everyone else is unchanged.
    fighters = {id(m) for m in front_rank.front_rank_models(squad)}

    def close_in_pairs():
        return sorted(
            ((m, min(target_squad.models, key=lambda e: edge_distance(m, e))) for m in squad.models),
            key=lambda pair: (id(pair[0]) not in fighters, edge_distance(pair[0], pair[1])),
        )

    # What the squad's coherency looked like BEFORE ANY of this. A unit can
    # enter the Charge/Fight phase already breaking coherency or the 9" spread
    # limit (casualties, a previous move, an enemy that shot the middle out of
    # it) - measured on one reported case, the Warbikers were 10.47" apart
    # before they ever declared. Judging each trial against "no errors at all"
    # then rejects EVERY step, the whole move collapses to nothing, and the log
    # blames coherency for something this move never caused. Trials are
    # therefore compared against this baseline: a step has to avoid making
    # things worse, not repair a mess it inherited.
    #
    # Measured BEFORE phase 1, deliberately - see phase 1's own rollback ladder
    # for why taking it afterwards was a real bug rather than a detail.
    baseline_errors = len(squad.check_coherency())

    # --- Phase 1: the whole formation forward, as one block ---
    # `skip_approach` means phase 1 has already been done by someone else -
    # _charge_along_route(), which brings the formation up along a real path -
    # and only the spread-into-engagement half below is wanted.
    own_model, enemy_model = min(
        ((a, b) for a in squad.models for b in target_squad.models),
        key=lambda pair: edge_distance(pair[0], pair[1]),
    )
    dx = enemy_model.x_in - own_model.x_in
    dy = enemy_model.y_in - own_model.y_in
    center_dist = (dx * dx + dy * dy) ** 0.5
    if not skip_approach and center_dist > 1e-9 and max_distance > 0:
        desired = clearance + own_model.radius_in + enemy_model.radius_in
        travel = max(0.0, min(center_dist - desired, max_distance))
        if approach_angle_deg:
            # A DETOUR, not an approach: "just far enough to reach clearance"
            # is measured along the DIRECT line, so on an angled attempt it's
            # far too short to actually clear whatever blocks that line - the
            # unit shuffles sideways an inch or two, phase 2 then walks
            # straight back into the same obstacle, and the charge fails
            # exactly as it did with no sweep at all.
            #
            # Spend `detour_fraction` of the roll getting AROUND instead, and
            # deliberately keep the rest for phase 2 to turn in with. Both
            # halves matter: too short a detour never clears the obstacle,
            # while spending the whole roll on it leaves nothing to actually
            # reach the enemy with. That's why the sweep varies the fraction
            # as well as the angle.
            travel = max_distance * detour_fraction
            rad = math.radians(approach_angle_deg)
            cos_a, sin_a = math.cos(rad), math.sin(rad)
            dx, dy = dx * cos_a - dy * sin_a, dx * sin_a + dy * cos_a
        ox, oy = dx / center_dist * travel, dy / center_dist * travel
        _run_phase_one(movement_controller, squad, ox, oy, max_distance,
                       close_in_pairs, baseline_errors)

    # --- Phase 2: SPREAD around the target, don't just close on the nearest ---
    _spread_into_engagement(movement_controller, squad, target_squad, clearance,
                            must_close_to_1in, baseline_errors, close_in_pairs, slots=slots)


def _position_snapshot(movement_controller, squad):
    """Everything a squad's placement consists of, so a whole trial pass can be
    undone: where each model stands plus the two pieces of movement bookkeeping
    try_commit_segment() advances behind it (rule 09.02 measures distance from
    the last committed waypoint, so restoring the position alone would leave
    the squad having "spent" range it no longer used).

    Same place -> check -> roll back pattern as _engagement_step(), one level
    up: that one compares a single model's candidate destinations, this one
    compares whole shared-offset passes."""
    return {
        model.id: (model.x_in, model.y_in,
                   movement_controller.last_waypoint.get(model.id),
                   movement_controller.remaining_range.get(model.id))
        for model in squad.models
    }


def _restore_positions(movement_controller, squad, snapshot):
    """Put a squad back exactly as _position_snapshot() found it."""
    for model in squad.models:
        entry = snapshot.get(model.id)
        if entry is None:
            continue
        model.x_in, model.y_in, waypoint, remaining = entry
        if waypoint is not None:
            movement_controller.last_waypoint[model.id] = waypoint
        if remaining is not None:
            movement_controller.remaining_range[model.id] = remaining


def _run_phase_one(movement_controller, squad, ox, oy, max_distance,
                   close_in_pairs, baseline_errors):
    """Carry the whole formation forward by ONE shared offset, and never leave
    it less coherent than it started.

    A rigid translation cannot change any pair of models' distance, so it
    cannot break coherency (rule 09.02) or the 9" spread limit at ANY distance
    - the same invariant _creep_toward() rests on. That guarantee only holds
    while EVERY model actually makes the shared step, though, and this loop
    reverts any single model that cannot (terrain, an enemy base, a squadmate).
    One reverted model turns the rigid block into a split formation.

    Real, severe bug, reported ("ki hat pile in mit meganobz nicht genutzt, um
    mehr modelle in den kampf zu bekommen") and reproduced exactly from
    logs/game_20260808_213013.log's own coordinates: of six Meganobz, five
    stepped the shared 0.9" and the sixth - already at 1.0" from the Kroot, so
    its step ran into an enemy base - stayed put. The squad split, and because
    the phase-2 baseline used to be measured AFTER this loop, phase 2 accepted
    the broken state as normal and worked happily inside it. confirm_pile_in()
    then rejected the whole thing: 1 of 6 models in Engagement Range, with the
    pile-in unspent.

    Fixed by keeping the invariant instead of assuming it: if the full offset
    leaves the unit worse off than `baseline_errors`, put everything back and
    try progressively shorter shared offsets. Shorter is strictly more likely
    to fit (every model's obstacle is further away), and the last rung - not
    moving at all - is coherency-safe by definition, so this can only improve
    on the previous behaviour. The common case (a clear lane, every model makes
    the full step) still costs exactly one pass."""
    step = (ox * ox + oy * oy) ** 0.5
    if step <= 1e-9:
        return
    snapshot = _position_snapshot(movement_controller, squad)
    for fraction in _PHASE_ONE_FRACTIONS:
        _place_shared_offset(movement_controller, squad, ox * fraction, oy * fraction,
                             step * fraction, max_distance, close_in_pairs)
        if len(squad.check_coherency()) <= baseline_errors:
            return
        _restore_positions(movement_controller, squad, snapshot)


def _place_shared_offset(movement_controller, squad, ox, oy, step, max_distance,
                         close_in_pairs):
    """One pass of the shared translation - every model moved by (ox, oy),
    each one still validated individually through clamp_move()/
    try_commit_segment() and reverted on its own if it cannot be placed."""
    placed = []
    for model, _enemy in close_in_pairs():
        start_pos = (model.x_in, model.y_in)
        for extra in _CHARGE_STEP_OVER_IN:
            # A model whose landing spot sits ON a piece of terrain gets
            # reverted by try_commit_segment() - and one reverted model is
            # enough to leave the unit short of Engagement Range and lose
            # the whole charge. Reported case, reproduced exactly: Boyz
            # charging 12" over a 0.6"-thin Dense wall, where the direct
            # approach needs only 5.25" and therefore lands six of ten
            # models squarely on top of the wall. They are INFANTRY, so
            # rule 13.06 lets them cross it - they just may not STOP on
            # it. Stepping a little further along the same line puts them
            # down on the far side, which is what a player physically
            # does, and the roll had 6.75" spare to pay for it.
            if step + extra > max_distance + 1e-9:
                break
            scale = (step + extra) / step if step > 1e-9 else 1.0
            target_x, target_y = _clamp_target_against_friendly_models(
                model, start_pos[0] + ox * scale, start_pos[1] + oy * scale,
                squad, movement_controller, placed,
                max_travel=step + extra, caller="shared-offset")
            model.x_in, model.y_in = movement_controller.clamp_move(model, target_x, target_y)
            ok, _errors = movement_controller.try_commit_segment(model)
            if ok:
                break
            model.x_in, model.y_in = start_pos
        placed.append(model)


def _spread_into_engagement(movement_controller, squad, target_squad, clearance,
                            must_close_to_1in, baseline_errors, close_in_pairs, slots=None):
    """Phase 2: SPREAD around the target, don't just close on the nearest.

    Every model used to head for its own nearest enemy model, which meant the
    whole squad converged on the one face of the enemy unit closest to it,
    bunched up, and left most of its own models with nowhere to stand. Measured
    on this file's own charge scenarios: 3 of 10 and 5 of 10 models ended up in
    Engagement Range. User: "die erwuerfelte reichweite sollte auch ausgereizt
    werden... nicht nur die 6" an den gegner ranlaufen, sondern um die
    gegnerische einheit herum laufen bis die 12" ausgereizt sind, sodass
    moeglichst viele modelle in den nahkampf kommen. wenn die vordersten
    modelle nur so weit laufen wie sie muessen, dann können die hinteren nicht
    mehr zuschlagen, weil die einheit klumpt."

    Correct, and it is what the rules reward: only models within Engagement
    Range fight, so a charge is worth as many of them as the roll can buy. Each
    model is sent to its own distinct slot on a ring AROUND the target unit
    (_engagement_slots()) instead of at the nearest enemy model, claimed
    nearest-first so the models that can reach a spot take it.

    `baseline_errors` comes from the caller and is the squad's coherency
    BEFORE phase 1 - see _run_phase_one() for why measuring it here instead
    was a real bug."""
    if slots is None:
        # Built here for a caller that has no ring yet (pile-in, consolidate,
        # a test driving this directly); the charge ladder builds it ONCE per
        # target and hands it down through _charge_per_model().
        slots = _engagement_slots(
            target_squad, max_model_radius(squad), clearance,
            legal=_engagement_slot_filter(squad, movement_controller,
                                          _keep_out_for_open_move(squad, movement_controller)))
    claimed = []
    for _pass in range(2):
        for model, nearest_enemy in close_in_pairs():
            # TWO DIFFERENT THINGS, split apart. The house rule (a model in
            # base contact may not be MOVED by a Pile-In or a Consolidation)
            # used to be indistinguishable from an optimisation that shares
            # this line - and the charge path uses the same line at 1.05", so
            # they had to be separated rather than retuned.
            #
            # Routed through base_contact.is_frozen() rather than repeating
            # the distance test: the skip and clamp_move()'s clamp must not
            # disagree (Fehlerklasse 10). A model the AI thinks it can move
            # but the clamp freezes wastes a whole pass; one the AI skips but
            # the clamp would have allowed loses ground. Kept even though the
            # clamp would freeze it anyway, so the candidate ladder is not
            # burned on a model that cannot move.
            if movement_controller.move_mode in base_contact.FROZEN_MOVE_MODES:
                if base_contact.is_frozen(model, squad, movement_controller.all_tokens,
                                          movement_controller.move_mode):
                    continue
            elif edge_distance(model, nearest_enemy) <= clearance + 0.05:
                # CHARGE ONLY, and the 1.05" is unchanged on purpose: that
                # measure_charge_scenes.py comes out identical is the check
                # that this split did not leak.
                continue  # already as tight against the target as it can get
            # NOTE: deliberately NOT "skip anything already in Engagement
            # Range". That is what it used to do, and it is why a pile-in
            # gained almost nothing: the front ranks - already engaged - stood
            # perfectly still, so the models behind them had nowhere to squeeze
            # into and the whole move was invisible. User: "bei pile in geht es
            # mehr um die hinteren modelle, die noch nicht engaged sind. die
            # müssen sich noch weiter nach vorne drängeln." They can only do
            # that if the front closes up first, which is exactly what a player
            # does by hand. Models are processed closest-first, so the front
            # takes the tightest slots and frees the outer ones for the rear.
            budget = movement_controller.remaining_range.get(model.id, 0.0)
            if budget <= 0.05:
                continue
            # Candidate destinations in preference order: every reachable
            # engagement slot (tightest first for a charge - rule 11.04's 1"
            # obligation - nearest first otherwise), and last of all the plain
            # "just close on the nearest enemy model" fallback for a model that
            # cannot reach any slot at all.
            #
            # ONE candidate was tried before, and that is what the reported
            # pile-in died on (Warbikers 2 vs Strike Team 2,
            # logs/game_20260805_232655.log): the single nearest slot was
            # physically underneath a squadmate, _clamp_target_against_friendly_
            # models() truncated the step to 0.64", and the model stopped 1.94"
            # short of Engagement Range with 2.4" of its pile-in unspent and a
            # free slot 1.7" to the side that was never looked at. Trying the
            # ranked list instead costs nothing when the first one works.
            candidates = [(s, 0.0) for s in _ranked_free_slots(
                model, slots, claimed, budget, must_close_to_1in=must_close_to_1in,
                squad=squad)]
            candidates.append(
                ((nearest_enemy.x_in, nearest_enemy.y_in),
                 clearance + model.radius_in + nearest_enemy.radius_in))
            # Judge each candidate by the only thing either move is FOR: does
            # this model end up within Engagement Range, and if not, how close
            # does it get (rule 12.05 - only models in Engagement Range fight).
            # User: "die ki benutzt pile in moves nicht genug, um mehr modelle
            # in nahkampfreichweite zu bekommen. das muss das oberste ziel dabei
            # sein."
            best = None
            for goal, desired in candidates:
                good, landed, _remaining = _engagement_step(
                    movement_controller, squad, model, goal, desired, budget,
                    baseline_errors, keep=False)
                if not good:
                    continue
                gap = min(
                    ((landed[0] - e.x_in) ** 2 + (landed[1] - e.y_in) ** 2) ** 0.5
                    - model.radius_in - e.radius_in
                    for e in target_squad.models
                )
                key = (0 if gap <= ENGAGEMENT_RANGE_IN else 1, round(gap, 3))
                if best is None or key < best[0]:
                    best = (key, goal, desired)
                if key[0] == 0:
                    # In Engagement Range, and the candidates are already in
                    # preference order - nothing further down the list can be
                    # a better answer, so stop paying for trials.
                    break
            if best is None:
                continue
            good, landed, _remaining = _engagement_step(
                movement_controller, squad, model, best[1], best[2], budget,
                baseline_errors, keep=True)
            if good and best[2] == 0.0:
                claimed.append(best[1])  # this ring slot is taken


def _engagement_step(movement_controller, squad, model, goal, desired, budget,
                     baseline_errors, keep):
    """Move one model toward `goal`, stopping `desired` short of it, and report
    where it actually ended up.

    With keep=False the model is put back where it started, so several
    candidate destinations can be COMPARED before one of them is committed -
    the step is otherwise identical, right down to going through clamp_move()
    and try_commit_segment(), so a trial and the real thing can never disagree
    about what is legal.

    "Legal" here means try_commit_segment() accepted the placement AND the step
    did not add a coherency error on top of whatever the squad already had
    (`baseline_errors` - see _charge_per_model(): a unit can enter the phase
    already broken, and demanding a clean sheet rejects every step it could
    make).

    Returns (legal, (x, y) it reached, remaining range there)."""
    start = (model.x_in, model.y_in)
    dx, dy = goal[0] - start[0], goal[1] - start[1]
    dist = (dx * dx + dy * dy) ** 0.5
    if dist <= 1e-9:
        return False, start, budget
    travel = max(0.0, min(dist - desired, budget))
    if travel <= 0.05:
        return False, start, budget
    others = [m for m in squad.models if m is not model]
    target_x, target_y = _clamp_target_against_friendly_models(
        model, start[0] + dx / dist * travel, start[1] + dy / dist * travel,
        squad, movement_controller, others, max_travel=travel, caller="engagement-step")
    model.x_in, model.y_in = movement_controller.clamp_move(model, target_x, target_y)
    ok, _errors = movement_controller.try_commit_segment(model)
    good = ok and len(squad.check_coherency()) <= baseline_errors
    landed = (model.x_in, model.y_in)
    remaining = movement_controller.remaining_range.get(model.id, budget)
    if not keep or not good:
        # Undo this one model's step - position, waypoint and the distance
        # try_commit_segment() just deducted - and leave the rest of the squad
        # exactly as it was.
        model.x_in, model.y_in = start
        movement_controller.last_waypoint[model.id] = start
        movement_controller.remaining_range[model.id] = budget
    return good, landed, remaining


# How the engagement ring is sampled: the arc between neighbouring slots on
# a ring, and the depth between concentric rings. Both are fixed lengths, not
# multiples of the base - the ring used to be sampled every 2r+0.1", which for
# a 1.57"-base C'tan meant SIX slots on a ring 19" round (and one ring, since
# the ring depth used the same number). The reported charges were possible
# BETWEEN those slots: brute-forced on the log's own boards, case A (Lychguard
# vs Krootox, 12" roll) had 87 legal engaged end spots and case B (C'tan vs
# Dire Avengers, 6" roll) had 5, and the ladder found none of them from
# thirteen approaches. A model does not need a slot exactly one base apart
# from the next; it needs SOME legal spot within reach, and _ranked_free_
# slots() spaces the ones it hands out.
_ENGAGEMENT_ARC_STEP_IN = 0.45
_ENGAGEMENT_RING_STEP_IN = 0.5
# Where a CHARGE's ring starts: at base contact, not at CHARGE_TARGET_
# CLEARANCE_IN (which stays what phase 1 stops short by). Rule 11.04 asks a
# model that can end within 1" to do so, and a slot at 0.1" is the surest way
# to be there after clamping. Measured on measure_charge_scenes.py (100 hard
# scenes / 100 easy): the ring from 1.0" got 273 / 334 models engaged on the
# completed charges, the ring from 0.1" 325 / 433, at the same completion.
_CHARGE_RING_INNER_EDGE_IN = PILE_IN_CLEARANCE_IN


def _charge_keep_out(squad, target_squad, all_tokens):
    """The enemy units a CHARGE may not end within Engagement Range of - every
    one but its target (rule 11.04 AFTER MOVING). Spelled out here because the
    ladder's caller asks it after the move has been cancelled, when
    disallowed_enemy_squads_for_move() no longer knows the targets."""
    return {t.squad for t in all_tokens
            if t.squad is not None and t.squad.owner != squad.owner
            and t.squad is not target_squad}


def _keep_out_for_open_move(squad, movement_controller):
    """The same question for whatever move is OPEN right now - a charge keeps
    its targets, a pile-in and a consolidate have no forbidden unit at all
    (Squad.disallowed_enemy_squads_for_move)."""
    return squad.disallowed_enemy_squads_for_move(
        movement_controller.all_tokens, movement_controller.move_mode,
        movement_controller.charge_targets, movement_controller.surge_target)


def _engagement_slot_filter(squad, movement_controller, keep_out_squads):
    """legal(x, y) for an engagement slot of this squad's widest base: on the
    board, off Dense terrain (13.05), not overlapping any token that is not
    one of this squad's own models (those are the ones about to move), and
    not within Engagement Range of a unit in `keep_out_squads`.

    Everything try_commit_segment() and check_charge_engagement() will reject
    later, asked BEFORE a slot is handed out - the ring used to offer slots on
    walls, on other units and inside a third unit's Engagement Range, and
    every one of those cost one of _ENGAGEMENT_SLOT_TRIES for nothing. Squad-
    mates are left to _ranked_free_slots(), which reads them live."""
    r = max_model_radius(squad)
    probe = max(squad.models, key=lambda m: m.radius_in) if squad.models else None
    tokens = movement_controller.all_tokens
    blockers = [t for t in tokens
                if t.squad is not None and t.squad is not squad and not t.is_dead()]
    keep_out = [t for t in blockers if t.squad in keep_out_squads]
    dense = [o for o in movement_controller.obstacles if o.category == DENSE]

    def legal(x, y):
        if probe is None or not formation_layout.on_board(x, y, r):
            return False
        if model_terrain_violation(probe, dense, x, y):
            return False
        for t in blockers:
            if math.hypot(x - t.x_in, y - t.y_in) < r + t.radius_in + _LANDING_OVERLAP_MARGIN_IN:
                return False
        for t in keep_out:
            if math.hypot(x - t.x_in, y - t.y_in) - r - t.radius_in <= ENGAGEMENT_RANGE_IN + _LANDING_OVERLAP_MARGIN_IN:
                return False
        return True

    return legal


def _engagement_slots(target_squad, own_radius, clearance, *,
                      arc_step_in=_ENGAGEMENT_ARC_STEP_IN, legal=None):
    """Standing room all the way AROUND the target unit, at just inside
    Engagement Range - so a charging squad can wrap it instead of piling onto
    the one face nearest to where the charge started.

    Slots that would land inside the enemy formation (too close to some other
    model of it) are dropped, so what comes back is the reachable perimeter;
    with `legal` (see _engagement_slot_filter()) so is every slot the move
    could not end on anyway. Sampled every `arc_step_in` along each ring and
    every _ENGAGEMENT_RING_STEP_IN in depth - see the two constants for why
    the old one-base pitch missed the reported charges."""
    slots = []
    for enemy in target_squad.models:
        inner = clearance + own_radius + enemy.radius_in
        # CONCENTRIC rings, not one. A single ring at the tightest distance
        # only has room for as many models as fit on that one circle - which
        # is what capped a pile-in at six of nine models even though every
        # one of them was close enough to reach. Everything out to Engagement
        # Range is legal standing room and counts for fighting, so offer the
        # depth too: the front rank takes the inner ring, the rank behind it
        # the next one out, exactly how the models end up on a real table.
        ring = inner
        while ring <= ENGAGEMENT_RANGE_IN + own_radius + enemy.radius_in + 1e-9:
            steps = max(8, int(round((2 * math.pi * ring) / arc_step_in)))
            for k in range(steps):
                angle = 2 * math.pi * k / steps
                x = enemy.x_in + ring * math.cos(angle)
                y = enemy.y_in + ring * math.sin(angle)
                if not all(((x - e.x_in) ** 2 + (y - e.y_in) ** 2) ** 0.5 >= inner - 0.05
                           for e in target_squad.models):
                    continue
                if legal is not None and not legal(x, y):
                    continue
                # Third element: this slot's own EDGE distance to the nearest
                # target model. _ranked_free_slots() ranks on it so a model
                # that can reach 1" is not allowed to settle at 2" (rule
                # 11.04 WHILE MOVING is a "can -> must", not a preference).
                edge = min(
                    ((x - e.x_in) ** 2 + (y - e.y_in) ** 2) ** 0.5 - own_radius - e.radius_in
                    for e in target_squad.models
                )
                slots.append((x, y, max(0.0, edge)))
            ring += _ENGAGEMENT_RING_STEP_IN
    # Tightest first, so the models processed earliest (closest to the enemy)
    # claim the inner ring and leave the outer ones for the rear ranks.
    slots.sort(key=lambda p: min((p[0] - e.x_in) ** 2 + (p[1] - e.y_in) ** 2
                                 for e in target_squad.models))
    return slots


def _ranked_free_slots(model, slots, claimed, budget, must_close_to_1in=True,
                       squad=None, limit=_ENGAGEMENT_SLOT_TRIES):
    """The engagement slots this model can actually reach, best first - at most
    `limit` of them.

    Tightest first, not merely nearest, because rule 11.04 WHILE MOVING is an
    obligation and not a preference: "Each model that CAN end its move within 1"
    of one or more charge targets MUST do so." Picking the slot closest to the
    MODEL let a model settle at up to Engagement Range (2") while a 1" slot was
    within its budget - reported as a charge that visibly stopped 2" short of the
    target and was accepted anyway.

    That was self-inflicted: _engagement_slots() was widened from one ring to
    concentric rings out to the full 2" while chasing a pile-in metric ("models
    in Engagement Range"), which is the right measure for a pile-in and the wrong
    one for a charge. Ranking by ring depth first restores the obligation while
    keeping the wrap-around the wider rings were built for - an outer slot is
    still taken, but only when nothing tighter is reachable.

    Ties on ring depth fall back to distance from the model, so the squad still
    fans out rather than all reaching for the same cell.

    A slot a SQUADMATE is currently standing on is not standing room, and
    `squad` is what makes that visible here. It used to be invisible, and the
    reported pile-in is exactly what that costs: models in base contact are
    skipped entirely (rule 12.03 forbids moving them), so they claimed nothing,
    a squadmate aimed at the very spot one of them was parked on, and
    _clamp_target_against_friendly_models() then truncated the step to almost
    nothing. Read live rather than pre-computed, so a spot frees up as soon as
    the model on it moves off - which is the whole point of processing the
    front rank first."""
    ranked = []
    for slot in slots:
        if any((slot[0] - c[0]) ** 2 + (slot[1] - c[1]) ** 2 < (2 * model.radius_in + 0.1) ** 2
               for c in claimed):
            continue
        gap = ((model.x_in - slot[0]) ** 2 + (model.y_in - slot[1]) ** 2) ** 0.5
        if gap > budget:
            continue
        if squad is not None and any(
            m is not model
            and (slot[0] - m.x_in) ** 2 + (slot[1] - m.y_in) ** 2
                < (model.radius_in + m.radius_in) ** 2
            for m in squad.models
        ):
            continue
        # slot[2] is the slot's own edge distance to the target (see
        # _engagement_slots()); rounded so near-equal rings tie and the
        # model-distance tie-break decides.
        key = ((round(slot[2], 2), gap) if must_close_to_1in and len(slot) > 2
               else (0.0, gap))
        ranked.append((key, slot))
    ranked.sort(key=lambda pair: pair[0])
    # One slot per base-width of arc. The ring is sampled far more densely
    # than a base is wide (_ENGAGEMENT_ARC_STEP_IN), so without this the
    # `limit` tries all landed on one 2"-stretch of the same arc and failed
    # for the same reason six times. A slot within one base of a better one
    # already kept is the same answer with a different rounding.
    min_gap = 2 * model.radius_in + 0.05
    kept = []
    for _key, slot in ranked:
        if any((slot[0] - k[0]) ** 2 + (slot[1] - k[1]) ** 2 < min_gap * min_gap for k in kept):
            continue
        kept.append(slot)
        if len(kept) >= limit:
            break
    return kept


# The landing search (_free_landing_near): rings of this pitch out to this
# radius around the point a model was aimed at, and the margins it keeps over
# the rule numbers.
_LANDING_RING_STEP_IN = 0.25
_LANDING_MAX_RADIUS_IN = 2.0
# Squad.check_model_overlap() rejects at `centre distance < r1 + r2`, so a spot
# put exactly on that boundary survives by floating-point luck - the same
# 1.9599" against 1.96" the truncating clamp had to back off for.
_LANDING_OVERLAP_MARGIN_IN = 0.02
# Rule 09.02's 2.0", with room for float noise: a real rejection in
# logs/game_20260908_204854.log read `closest gap 2.00" (needs <= 2.0")`.
_LANDING_COHERENCY_IN = 1.9
# How much a sideways offset from the intended point costs on top of its
# distance. At 1.0 a spot one inch SHORT of the point (still on the model's
# line) costs 1.0 and a spot one inch BESIDE it costs 2.0 - so stopping short
# beats sliding sideways at equal distance. Measured without it, on
# measure_crowded_movement.py --army=necrons: the 21-model blob's third move
# had eighteen models re-landed along a wall, 3.63" of displacement for 0.89"
# of progress, and that candidate WON the sweep (a routed candidate is judged
# on distance covered) - 18% of achievable against 52% with the old clamp.
_LANDING_LATERAL_WEIGHT = 1.0
# Caller tags whose search is switched off - for A/B probes only, so the six
# call sites can be measured one at a time (see the `caller` argument).
LANDING_SEARCH_OFF_FOR = frozenset()
# Call sites that do NOT get the search, by measurement. The route walker
# (_place_per_model_route, caller "route") lands every model at every
# waypoint of an A* road, and a routed candidate is judged by the sweep on
# DISTANCE COVERED along that road, not on progress toward the goal - so a
# search that finds every model somewhere legal beside the road makes a poor
# routed candidate clear the bar and win before the rigid route or the angle
# sweep get their turn. Per-caller A/B on measure_crowded_movement.py, both
# armies, with the lateral penalty in place:
#
#                     Orks median / total / stalls    Necrons median / total
#   search everywhere      70% / 223.7" / 1               57% / 116.6"
#   search except "route"  74% / 232.9" / 0               60% / 119.9"
#   no search (old clamp)  64% / 217.7" / 0               60% / 117.9"
#
# and the 21-model Necron blob's third move went 52% -> 14% of achievable
# with the route search on (eighteen models re-landed beside a wall for
# 0.89" of progress) and back to 52% without it. The other four call sites
# keep the search; the engagement step is the second exclusion, below.
# "engagement-step" is excluded for a different reason than "route": the
# search's cost knows distance and lateral offset, not Engagement Range, so it
# re-landed a piling-in model on a legal spot BESIDE its engagement slot and
# out of range. Measured on the reported Warbikers pile-in
# (test_melee_engagement.py section 3, a real board state): 2 of 3 engaged
# is the brute-forced optimum, and with the search on that path it fell
# below it; the two reported charge fixtures (measure_reported_moves.py A/B)
# read the same with and without. The engagement step keeps the old cut.
_LANDING_SEARCH_EXCLUDED = frozenset({"route", "engagement-step"})
# How far a model may re-land when the ONLY thing on its intended point is a
# squadmate placed earlier in the same pass (another unit's model on it gets
# the full radius). None = the full radius, 0.0 = the old truncation.
#
# Measured on 2026-09-09 (fixture C = the reported 21-model blob in
# measure_reported_moves.py; the worlds are measure_crowded_movement.py's):
#
#   radius     C     Orks crowded      Necrons crowded   Necrons isolated
#   None      74%    74% / 232.9"      60% / 119.9"      68% / 139.4"
#   1.0"      71%    67% / 228.7"      60% / 119.5"      68% / 138.1"
#   0.5"      71%    65% / 220.7"      60% / 118.9"      72% / 140.5"
#   0.0"      70%    63% / 217.4"      65% / 121.6"      74% / 140.7"
#   (old)     54%    65% / 217.7"      60% / 117.9"      74% / 140.7"
#
# Almost the whole Ork gain is squadmate re-landing: a mob whose slots are
# taken by its own front rank flows around them instead of stopping behind
# them. The price is one row: the Necron blob ALONE on the board makes 43%
# instead of 92% of its second move, because re-landing beside squadmates
# widens the shape (Ork widest spread 7.78" -> 10.35") and the packed
# candidate that wins that move no longer reaches its slots. Full radius
# shipped - 353" of ground over both crowded worlds against 339" at 0.0 -
# and the number above is the one to change if that trade is ever reversed.
_LANDING_SQUADMATE_RADIUS_IN = None


def _free_landing_near(model, target_xy, squad, movement_controller, placed, *,
                       max_travel=None, heading=None, max_radius=None, caller=""):
    """The nearest LEGAL end point around `target_xy`, or None.

    Rule 03.01 lets a base move THROUGH friendly models and only forbids
    ENDING on one. _clamp_target_against_friendly_models() honoured the first
    half (a clear landing is returned untouched) but answered an occupied
    landing by truncating the move at the FIRST friendly base along the line -
    which is neither what the rule says nor what a player does. Measured on
    the reported 21-model blob (measure_reported_moves.py case C): the clamp
    truncated 535 of 821 model targets in ONE move, throwing away 810" of
    aimed distance, and in 445 of those 535 cases a free landing spot lay
    within 2" of the intended point (154 within a quarter inch). The models
    that got cut short then stood while their squadmates ran on, the unit
    split, and confirm_move() threw the whole candidate away - which is the
    mechanism behind "die modelle stehen sich gegenseitig im weg".

    Legal means everything try_commit_segment() will check, asked HERE: on the
    board, not on Dense terrain (13.05), not overlapping any token (friendly
    blockers as the clamp defines them - other units plus squadmates already
    placed this pass - AND enemies), not within Engagement Range of an enemy
    unit this move may not touch (Squad.disallowed_enemy_squads_for_move, so
    a charge keeps its targets and a pile-in has no such list), within
    `max_travel` (default: the model's remaining range) of where the model
    stands, and reachable by clamp_move() without being shortened - the
    engine's own transit rule, so an enemy base or a wall in the way is not
    argued with here.

    Preference: a spot within _LANDING_COHERENCY_IN of a squadmate already
    placed comes first (the constructive half of rule 09.02, which is what
    the per-model pass is trying to keep); among those, the lowest COST, which
    is the distance from the intended point plus _LANDING_LATERAL_WEIGHT times
    the sideways part of that offset (measured across `heading`, the direction
    the model was going) - so a model whose spot is taken stops a little
    short rather than sliding along whatever blocked it. Deterministic: the
    sweep's fallback round replays candidates and relies on a replay landing
    where the first run did.

    Bounded: the rings hold ~225 points at the default radius, the blockers
    and obstacles are cut down ONCE to those that can touch that disc, and
    the search stops as soon as the next ring's radius already exceeds the
    best cost found (a spot on a ring of radius R costs at least R) - the
    common case ends on the first or second ring.

    `max_radius` defaults to the larger of 2" and one base diameter: a
    Battlewagon boxed in by its own infantry needs to look further than a
    Boy does. NOT a substitute for planning where a unit goes - the aim is
    the caller's; this only decides where the model comes to rest when the
    exact point is taken."""
    if caller in LANDING_SEARCH_OFF_FOR or caller in _LANDING_SEARCH_EXCLUDED:
        return None
    tx, ty = target_xy
    r = model.radius_in
    budget = movement_controller.remaining_range.get(model.id, 0.0)
    if max_travel is not None:
        budget = min(budget, max_travel)
    if budget <= 1e-9:
        return None
    if max_radius is None:
        max_radius = max(_LANDING_MAX_RADIUS_IN, 2.0 * r)
    mx, my = model.x_in, model.y_in
    if heading is None:
        heading = math.atan2(ty - my, tx - mx) if (tx - mx) ** 2 + (ty - my) ** 2 > 1e-12 else 0.0

    tokens = movement_controller.all_tokens
    widest = max((t.radius_in for t in tokens), default=0.0)
    reach = max_radius + r + widest + ENGAGEMENT_RANGE_IN + _LANDING_OVERLAP_MARGIN_IN
    blockers = [
        t for t in tokens
        if t is not model and t.squad is not None
        and (t.squad is not squad or t in placed)
        and abs(t.x_in - tx) <= reach and abs(t.y_in - ty) <= reach
    ]
    disallowed = squad.disallowed_enemy_squads_for_move(
        tokens, movement_controller.move_mode, movement_controller.charge_targets,
        movement_controller.surge_target)
    keep_out = [t for t in blockers if t.squad in disallowed]
    # Asked of the piece itself, not its bounding box - a rotated footprint's
    # box is not its shape (game/terrain.py), and test_rotated_terrain.py
    # holds this file to that.
    obstacles = [
        o for o in movement_controller.obstacles
        if o.category == DENSE and o.distance_to_point(tx, ty) <= reach
    ]
    anchors = [p for p in placed if not p.is_dead()]

    def coherent(x, y):
        if not anchors:
            return True
        return any(math.hypot(x - p.x_in, y - p.y_in) - r - p.radius_in <= _LANDING_COHERENCY_IN
                   for p in anchors)

    def legal(x, y):
        if math.hypot(x - mx, y - my) > budget + 1e-9:
            return False
        if not formation_layout.on_board(x, y, r):
            return False
        if model_terrain_violation(model, obstacles, x, y):
            return False
        for t in blockers:
            if math.hypot(x - t.x_in, y - t.y_in) < r + t.radius_in + _LANDING_OVERLAP_MARGIN_IN:
                return False
        for t in keep_out:
            if math.hypot(x - t.x_in, y - t.y_in) - r - t.radius_in <= ENGAGEMENT_RANGE_IN + _LANDING_OVERLAP_MARGIN_IN:
                return False
        # Last, because it is the expensive one: the engine's own transit
        # rule must deliver the model to this exact point.
        cx, cy = movement_controller.clamp_move(model, x, y)
        return math.hypot(cx - x, cy - y) <= 1e-6

    ux, uy = math.cos(heading), math.sin(heading)

    def cost(x, y):
        dx, dy = x - tx, y - ty
        lateral = abs(-dx * uy + dy * ux)
        return math.hypot(dx, dy) + _LANDING_LATERAL_WEIGHT * lateral

    rings = max(1, int(math.ceil(max_radius / _LANDING_RING_STEP_IN - 1e-9)))
    best = None       # (cost, x, y) among spots coherent with the placed squadmates
    fallback = None   # (cost, x, y) among the rest
    for x, y in formation_layout.ring_candidates(tx, ty, _LANDING_RING_STEP_IN, heading, rings=rings):
        ring = math.hypot(x - tx, y - ty)
        if best is not None and best[0] <= ring + 1e-9:
            break  # nothing further out can cost less than this ring's radius
        if not legal(x, y):
            continue
        c = cost(x, y)
        if coherent(x, y):
            if best is None or c < best[0]:
                best = (c, x, y)
        elif fallback is None or c < fallback[0]:
            fallback = (c, x, y)
    chosen = best if best is not None else fallback
    return None if chosen is None else (chosen[1], chosen[2])


def _clamp_target_against_friendly_models(model, target_x, target_y, squad, movement_controller, placed,
                                          max_travel=None, caller=""):
    """Shared by _charge_per_model() and _advance_toward_per_model(): rule
    03.01 lets a model's base move THROUGH friendly models, but never end
    move on top of one - movement_controller.clamp_move() only ever
    enforces the ENEMY half of that during a drag (see its own docstring),
    so friendly overlap between several models of the SAME move (which all
    move independently, each blind to where its squadmates are landing) was
    only ever caught much later, by confirm_move()'s check_model_overlap(),
    with no chance left to recover - the exact bug reported for charges
    ("KI würfelt Charge, führt ihn aber nicht aus... enger Raum") and,
    reproduced directly the same way, for ordinary Normal Moves too (every
    model in _advance_toward_per_model() walks toward the SAME shared
    target point - an even more direct case than charge's "each model's own
    nearest enemy").

    Clamps `target_x, target_y` short of colliding with every OTHER
    friendly token already on the board, plus every squadmate THIS call has
    already placed (`placed`, grown by the caller as it processes models in
    some order) - reusing game.geometry.max_unblocked_fraction_models(), the
    same circle-collision math clamp_move() itself already uses for enemy
    blocking, just aimed at friendly models instead. Squadmates not yet
    processed this call are deliberately excluded from `placed` (they're
    still sitting at their OLD position, about to change - checking against
    that would be pointless).

    SINCE 2026-09-09 an occupied landing is first answered by
    _free_landing_near(): the nearest legal spot around the intended point,
    inside `max_travel` (the caller's per-model cap - the sweep's fraction
    rungs must stay short rungs) and preferring one that keeps rule 09.02's
    2" to a squadmate already placed. Only when that finds nothing does the
    truncation below run, unchanged. `caller` names the call site so the A/B
    probes can switch the search off per site (LANDING_SEARCH_OFF_FOR).

    Real, severe, PRE-EXISTING bug found via user report ("ghostkeel/
    devilfish bewegen sich kaum", still reproducing after both false-
    success fixes above): max_unblocked_fraction_models() stops a candidate
    target at the FIRST friendly model's circle the WHOLE path would enter
    - but the rule (and this function's own docstring, above) is "can move
    THROUGH friendly models, only can't END on one". Any friendly model
    merely standing somewhere along the line to an otherwise-fine, distant
    target - not AT the target itself - was needlessly truncating the move
    to just short of that model's edge, even though nothing about the
    actual intended endpoint was ever illegal. Reproduced directly: a
    flying Ghostkeel's intended ~8" move got clamped down to ~1" purely
    because a completely different, unrelated squad's model happened to
    sit along the straight line - the exact "moved only ~1\"" symptom
    reported, and the real reason today's earlier `flying` fix alone didn't
    resolve it (that fix correctly stopped the ENGINE from treating a
    flying model's transit as blocked - it had no effect on THIS separate,
    pre-transit clamp, which was never flying-aware or transit-aware to
    begin with, for grounded models either). Fixed: only clamp when the
    ALREADY-COMPUTED (naive) endpoint itself actually overlaps a friendly
    model - if it doesn't, the straight line is returned completely
    unchanged, matching "pass through, don't end there" exactly. Only in
    the genuine "would land on someone" case does it fall back to the old
    truncate-at-first-entry behavior (still a rough, conservative fix in
    that narrower case, but that's the same behavior this function already
    had for the case it was actually built for)."""
    friendly_blockers = [
        t for t in movement_controller.all_tokens
        if t is not model and t.squad is not None and t.squad.owner == squad.owner
        and (t.squad is not squad or t in placed)
    ]
    landing_clear = not any(
        ((target_x - t.x_in) ** 2 + (target_y - t.y_in) ** 2) ** 0.5 < t.radius_in + model.radius_in
        for t in friendly_blockers
    )
    if landing_clear:
        _sweep_stats["clear"] = _sweep_stats.get("clear", 0) + 1
        return target_x, target_y
    spot = None
    only_squadmates = not any(
        t.squad is not squad
        and ((target_x - t.x_in) ** 2 + (target_y - t.y_in) ** 2) ** 0.5 < t.radius_in + model.radius_in
        for t in friendly_blockers)
    radius = _LANDING_SQUADMATE_RADIUS_IN if only_squadmates else None
    if radius is None or radius > 0.0:
        spot = _free_landing_near(model, (target_x, target_y), squad, movement_controller, placed,
                                  max_travel=max_travel, caller=caller, max_radius=radius)
    if spot is not None:
        _sweep_stats["relanded"] = _sweep_stats.get("relanded", 0) + 1
        return spot
    _sweep_stats["truncated"] = _sweep_stats.get("truncated", 0) + 1
    fraction = geometry.max_unblocked_fraction_models(
        (model.x_in, model.y_in), (target_x, target_y), friendly_blockers, inflate_radius=model.radius_in,
    )
    # max_unblocked_fraction_models() stops exactly ON the blocker's edge, and
    # Squad.check_model_overlap() rejects at `center_dist < r1 + r2` - so the
    # clamped point is precisely on the boundary and whether it survives comes
    # down to floating-point rounding. Measured on the reported pile-in
    # (Warbikers 2, logs/game_20260805_232655.log): the clamp produced a
    # squadmate gap of 1.9599... against a 1.96" limit and the step was thrown
    # out with "Models cannot end their move on top of another model", which is
    # why that model stopped short of Engagement Range for no real reason.
    # Back off by a hair so a function documented as clamping SHORT of a
    # collision actually does, deterministically.
    dx, dy = target_x - model.x_in, target_y - model.y_in
    length = (dx * dx + dy * dy) ** 0.5 * fraction
    if length > 1e-9:
        fraction *= max(0.0, length - _FRIENDLY_CLAMP_EPSILON_IN) / length
    return model.x_in + dx * fraction, model.y_in + dy * fraction


def _predict_squad_positions_from_point(squad, origin_x, origin_y, base_offset, all_tokens, toward_enemy=False,
                                        angle_offset=0.0):
    """The same "spread in a line facing away from the nearest enemy"
    geometry _spread_squad_from_point() commits to the board, but returns
    the candidate (x, y) per model instead of mutating anything - lets a
    caller peek at where a squad WOULD land (e.g. _has_target_after_
    disembark(), deciding whether disembarking is even worth offering)
    without touching real model positions first.

    `toward_enemy` (default False, preserving the original away-from-enemy
    safety bias used by Ingress) flips the facing toward the nearest enemy
    instead - real bug, found via user report ("die breacher steigen
    einfach nicht aus dem devilfish aus, obwohl sie gute targets hatten"):
    _has_target_after_disembark() judged reachability from the SAME away-
    facing point this function always produced, even though rule 18.04
    allows placement in ANY direction within the disembark distance
    (3"/Tactical, 6"/Combat) - the away-facing bias (deliberately built for
    Ingress, where a freshly-arrived unit should NOT rush toward combat)
    pushes the predicted spot several inches further from the enemy than
    necessary, which can flip a genuinely reachable charge (rule 11.01's
    12" declare range is a tight enough threshold that this offset alone
    can matter) or shot to "out of range" in the check, even though a
    toward-facing placement - equally legal under 18.04, and exactly what
    the actual disembark's own gap-clearance still respects - would have
    reached it. Reproduced directly: a Devilfish sitting ~12.5" from an
    enemy squad's edge measured "no charge target" via the away-facing
    point (pushed to ~16"+) while the toward-facing point (~9.5") clearly
    had one. Disembark's own call sites (both the eligibility check and the
    actual placement, so they stay consistent with each other) pass
    toward_enemy=True; Ingress keeps the original default."""
    nearest_enemy = _nearest_enemy_squad(squad, all_tokens)
    if nearest_enemy is not None:
        ex, ey = _centroid(nearest_enemy)
        dx, dy = (ex - origin_x, ey - origin_y) if toward_enemy else (origin_x - ex, origin_y - ey)
    else:
        dx, dy = 0.0, -1.0
    dist = (dx * dx + dy * dy) ** 0.5
    if dist <= 1e-9:
        dx, dy, dist = 0.0, -1.0, 1.0
    ux, uy = dx / dist, dy / dist       # unit vector pointing away from (or, if toward_enemy, toward) the enemy
    if angle_offset:
        # Same idea as _DISEMBARK_FACINGS: the models are laid out in a LINE,
        # and a line is a shape that fails wholesale when a board edge or a
        # wall crosses it, however open the ground a quarter-turn away is. The
        # caller sweeps offsets so one blocked orientation does not throw away
        # the landing spot itself.
        cos_a, sin_a = math.cos(angle_offset), math.sin(angle_offset)
        ux, uy = ux * cos_a - uy * sin_a, ux * sin_a + uy * cos_a
    px, py = -uy, ux                    # perpendicular unit vector, for spreading models side-by-side

    # Real bug, found via user report ("die KI hat ihre Reserven in Runde 2
    # nicht eingesetzt"): DISEMBARK_MODEL_GAP_IN (1.5") was sized for this
    # demo's ordinary infantry bases (~0.5"-0.63" radius, so 2*radius is
    # comfortably under 1.5") - for a wider-based unit (e.g. Crisis
    # Starscythe Battlesuits, radius ~0.8"-0.98"), a flat 1.5" gap is
    # LESS than 2*radius, so adjacent spread-out models overlap EACH OTHER
    # by construction, and check_model_overlap() (rule 03.01) then fails
    # this squad's placement at literally every candidate point on the
    # board, no matter how open the area is - reproduced directly: every
    # sampled Ingress landing candidate failed with "Models cannot end
    # their move on top of another model", even in spots with nothing
    # else nearby at all. Widening the search (see
    # _ingress_landing_candidates()) couldn't have fixed this - the squad
    # was colliding with itself, not with the board.
    gap = max(DISEMBARK_MODEL_GAP_IN, 2 * max_model_radius(squad) + 0.1)

    n = len(squad.models)
    positions = []
    for i in range(n):
        lateral = (i - (n - 1) / 2) * gap
        x = origin_x + ux * base_offset + px * lateral
        y = origin_y + uy * base_offset + py * lateral
        positions.append((x, y))
    return positions


# NOTE: the line-shaped committer this pair of helpers used to feed
# (_spread_squad_from_point) is gone - Disembark moved to
# _disembark_pack_positions() and Ingress to _ingress_pack_positions(), both
# of which pack a clump and validate every slot. _predict_squad_positions_
# from_point() above is kept because the disembark ELIGIBILITY checks still
# want a cheap "roughly where would they end up" guess without touching the
# board; it is deliberately not what does the placing any more.


def _on_board(x_in, y_in, radius_in):
    """Would a model of this size sit fully inside the table at (x, y)?
    Same bounds MovementController enforces - checked here so a placement
    can avoid an off-board slot instead of being rejected wholesale."""
    return (
        radius_in <= x_in <= config.BOARD_WIDTH_IN - radius_in
        and radius_in <= y_in <= config.BOARD_HEIGHT_IN - radius_in
    )


def _disembark_pack_positions(squad, transport_token, max_distance_in, all_tokens, angle_offset=0.0,
                              setup_controller=None):
    """Rule 18.04/18.05 placement geometry: pack the disembarking models into
    one CLUMP on the chosen side of the TRANSPORT, so that EVERY model stays
    within `max_distance_in` of the TRANSPORT's own base (the hard
    requirement TransportController._make_extra_check() enforces) while
    still keeping each model clear of the TRANSPORT and of its squadmates.

    Replaces the previous single straight LINE of models, which was the
    direct cause of a real endless loop (user report: "am ende des spiels war
    die KI in einer art endlos loop gefangen"). That line's width grew with
    squad size - for this demo's 10-model Breacher Team it spanned 13.5",
    putting the outermost models 4.9" from the TRANSPORT against a 3"
    Rapid/Tactical limit - so confirm_disembark() rejected the placement,
    the caller cancelled it, cancel_disembark() put the squad back INSIDE the
    transport exactly as it was, and the very next call re-ran the identical
    decision from the identical state, forever (an API call per frame with a
    real agent). The line geometry was documented as a known v1 risk for
    "much larger squads" - the demo's move from 5- to 10-model squads is what
    turned that risk into the reported hang.

    Slots are laid out facing the nearest enemy first (same reasoning as the
    old line's toward_enemy=True: a squad only disembarks at all because
    _has_target_after_disembark() found something worth reaching). Returns one
    (x, y) per model, in squad order.

    CLUMP, not ring - the fill order is the whole change, and it exists because
    of a reported charge failure ("warum die beast snagga boys gerade den charge
    move nicht durchgeführt haben. der wurf hat locker gereicht"), user
    diagnosis: "das kernproblem ist die ringplatzierung bei disembark. vor allem
    bei großen transportern. eine klumpenformation wäre robuster im nachgang."

    Correct, and the reason is structural rather than a matter of taste. The
    legal ground is an ANNULUS around the hull, and walking it ring-by-ring
    fills the nearest arc all the way round before using any of the depth - so
    the unit comes out as a thin band wrapped about the transport. Two things
    follow, both of which bite on the NEXT move rather than here:

      * the band is long and one model thick, so its coherency graph is a
        CHAIN. Measured on the reported case, 11 Beast Snagga Boyz off a Kill
        Rig: 5 bridge edges, the tightest with 0.57" of slack - any one of them
        splits the unit;
      * the transport itself ends up INSIDE the formation, so the rigid
        translation the charge opens with (_run_phase_one()) has its own
        transport in the way.

    That is exactly how the reported charge died: a 2.93" gap and a 7" roll,
    and phase 1 only had to carry the unit 1.93". One model stepped over a wall
    by the step-over ladder's 0.8", that model happened to be the single bridge
    between the two halves, the unit split, and _run_phase_one() responded by
    shortening the shared offset for everybody to 0.48". Final distance 2.44" -
    a charge that a plain rigid step would have completed at 1.00".

    Sorting the same candidates by distance from a drop point instead grows a
    two-dimensional blob on one side. The drop point sits at the FULL
    `max_distance_in` along the facing ray, so the block is centred on the far
    edge of the band and grows back toward the hull - which is what "use the 3
    inches" means here, and it also leaves the transport outside the formation
    rather than in the middle of it.

    Measured over the reported case plus the four historical disembark spots
    CLAUDE.md records, ring -> clump, first facing that confirms:

        bridges (single points of failure)   5, 2, 0, 0, 0  ->  0, 0, 0, 0, 0
        still coherent after one model
          drifts 0.8" off the shared step  91%, 85%, 100%, 100%, 100%
                                          -> 98%, 100%, 100%, 100%, 100%
        same at 1.2"                      73%, 85%, 100%, 100%, 100%
                                          -> 97%,  99%, 100%, 100%, 100%
        facings that confirm                 8/8 everywhere, both ways

    Spread moves either way by under half an inch (worst 6.99" -> 7.61", best
    6.94" -> 4.93"), all far inside rule 09.02's 9" limit - and spread was never
    the thing that failed; connectivity was."""
    n = len(squad.models)
    if not squad.models:
        return []
    model_radius = max_model_radius(squad)
    smallest_radius = min(m.radius_in for m in squad.models)

    # An attached unit (19.01) can mix base sizes, and that breaks the single
    # `spacing`/`inner`/`outer` this used to compute from one radius, in two
    # opposite directions at once:
    #
    # - CLEARANCE ("do not overlap a squadmate or the TRANSPORT") is set by
    #   the WIDEST model, so sizing off models[0] - a bodyguard, hence the
    #   small one - packs the character in too tightly and rule 03.01 rejects
    #   the placement.
    # - The DISTANCE CAP (18.04: every model within max_distance of the
    #   TRANSPORT, measured edge to edge) is set by the NARROWEST, because
    #   edge distance is ring_radius - model_radius - transport_radius, so a
    #   smaller base on the same ring sits FURTHER out. Sizing off the widest
    #   put a 0.63" Boy 3.35" from a Trukk against a 3" limit.
    #
    # Using the widest for both is not a safe compromise either: it costs
    # real ring capacity (2.11" of arc per model instead of 1.41"), which is
    # exactly what an 11-model unit disembarking into a board CORNER cannot
    # spare - measured, that lost the corner case outright.
    #
    # So candidate slots are generated densely, off the SMALLEST base, and
    # each one is then validated against the SPECIFIC model being placed.
    # Every constraint is per model, which is what the rules say anyway; the
    # single-radius version was only ever an approximation that held while a
    # Squad was homogeneous.
    inner = transport_token.radius_in + smallest_radius + 0.05
    outer = transport_token.radius_in + smallest_radius + max_distance_in
    step = max(0.35, 2 * smallest_radius + 0.1)

    # Rule 03.02: the finished unit has to be UNENGAGED, unless the mode
    # waives it (18.04's Combat Disembark, SetupController.allows_engaged).
    # That is a whole-squad check in confirm_setup(), so a single engaged
    # slot fails the entire placement - and for an Emergency Disembark
    # (18.05) a failed placement destroys the unit. It has to be a filter on
    # the CANDIDATES, exactly like terrain and overlap already are.
    #
    # This is what the reported wipe was (log game_20260805_232655, round 4:
    # a Trukk killed at (7.83,21.73) with 6 Meganobz aboard, "could not be
    # placed after disembarking from any facing" at all eight facings, unit
    # destroyed). Every facing failed on engagement alone, and the reason it
    # failed at ALL of them is right below: the arcs are ordered toward the
    # NEAREST ENEMY, so the generator packs the squad into precisely the
    # models whose Engagement Range makes the placement illegal. Measured on
    # that board, 66 sq.in of legal, unengaged ground sat inside the 6"
    # limit - room for six 0.79" bases many times over.
    enemy_models = (
        []
        if (setup_controller is not None and setup_controller.allows_engaged)
        else [
            t for t in all_tokens
            if t.squad is not None and t.squad.owner != squad.owner
        ]
    )

    nearest = _nearest_enemy_squad(squad, all_tokens)
    if nearest is not None:
        ncx, ncy = _centroid(nearest)
        dx, dy = ncx - transport_token.x_in, ncy - transport_token.y_in
        dist = (dx * dx + dy * dy) ** 0.5
        base_angle = (math.atan2(dy, dx) if dist > 1e-9 else -math.pi / 2) + angle_offset
    else:
        base_angle = -math.pi / 2 + angle_offset

    # Slots over the whole annulus, then ordered by distance from a DROP POINT
    # on the facing ray - see the docstring. The drop point sits at the outer
    # edge of the band, so the block uses the full `max_distance_in` of depth
    # and grows back toward the hull instead of wrapping around it.
    drop_x = transport_token.x_in + outer * math.cos(base_angle)
    drop_y = transport_token.y_in + outer * math.sin(base_angle)
    candidates = []
    ring_radius = inner
    while ring_radius <= outer + 1e-9:
        capacity = max(1, int((2 * math.pi * ring_radius) / step))
        astep = 2 * math.pi / capacity
        for k in range(capacity):
            angle = base_angle + k * astep
            candidates.append((
                ring_radius,
                transport_token.x_in + ring_radius * math.cos(angle),
                transport_token.y_in + ring_radius * math.sin(angle),
            ))
        ring_radius += step
    candidates.sort(key=lambda c: (c[1] - drop_x) ** 2 + (c[2] - drop_y) ** 2)

    # Widest first: the hardest model to fit picks from the whole board of
    # candidates rather than from whatever the small ones left over. Squad
    # order is restored on the way out, since the caller zips these positions
    # against squad.models.
    def fill(order, pool_for):
        chosen = {}
        placed = []  # (x, y, radius) already assigned this placement
        for index in order:
            model = squad.models[index]
            for (ring_radius, x, y) in pool_for(index):
                # Clear of the TRANSPORT, and inside the rule's distance cap -
                # both measured edge to edge for THIS model's own base.
                edge = ring_radius - model.radius_in - transport_token.radius_in
                if edge < 0.05 or edge > max_distance_in:
                    continue
                if not _on_board(x, y, model.radius_in):
                    continue
                # Standable ground for THIS model (13.05/13.06) and clear of
                # every token outside the squad - the check that used to be
                # skipped entirely, which let a slot inside a wall be handed out
                # and fail the whole placement at confirm time (user: three turns
                # running with an explicit order to disembark).
                if setup_controller is not None and not setup_controller.position_valid(
                    model, x, y, squad=squad,
                ):
                    continue
                # Engagement Range (03.04), edge to edge, same as Squad.is_engaged().
                if any(
                    ((x - e.x_in) ** 2 + (y - e.y_in) ** 2) ** 0.5 - model.radius_in - e.radius_in
                    <= ENGAGEMENT_RANGE_IN
                    for e in enemy_models
                ):
                    continue
                # Rule 03.01 against squadmates already placed, using BOTH radii.
                if any(
                    ((x - px) ** 2 + (y - py) ** 2) ** 0.5 < model.radius_in + pr + 0.05
                    for px, py, pr in placed
                ):
                    continue
                # Rule 09.02 coherency is edge to edge, so centres may be that
                # much further apart again. Enforced as the placement is built,
                # which is what guarantees a single connected group instead of
                # hoping the ring produced one.
                if placed and not any(
                    ((x - px) ** 2 + (y - py) ** 2) ** 0.5 <= COHERENCY_RANGE_IN + model.radius_in + pr
                    for px, py, pr in placed
                ):
                    continue
                chosen[index] = (x, y)
                placed.append((x, y, model.radius_in))
                break
        return chosen

    widest_first = sorted(range(n), key=lambda i: -squad.models[i].radius_in)
    chosen = fill(widest_first, lambda index: candidates)

    # Melee characters step out at the FRONT of the block, not buried in the
    # middle of it - see game/front_rank.py, and the same treatment
    # game/formation_layout.py's deployment packer gets. A unit that unloads
    # with its Warboss six ranks back charges with its Warboss six ranks back,
    # and rule 12.05 only lets models in Engagement Range fight.
    #
    # Placed FIRST rather than swapped afterwards, for the reason measured
    # there: a character with a bigger base than the rank and file fits nowhere
    # in a finished block except the hole the packer already cleared for him.
    fighters = [m for m in front_rank.front_rank_models(squad) if not m.is_dead()]
    if fighters and chosen:
        # `base_angle` here points AT the nearest enemy (unlike the deployment
        # packer's, which points away), so it IS the forward direction.
        fx, fy = math.cos(base_angle), math.sin(base_angle)
        limit = max(x * fx + y * fy for (x, y) in chosen.values()) + 1e-9
        front_first = sorted(
            (c for c in candidates if c[1] * fx + c[2] * fy <= limit),
            key=lambda c: -(c[1] * fx + c[2] * fy),
        )
        priority = [i for m in fighters for i, x in enumerate(squad.models) if x is m]
        led = fill(
            priority + [i for i in widest_first if i not in set(priority)],
            lambda index, p=set(priority): front_first if index in p else candidates,
        )
        # Never trade a working placement for a better-looking one - same
        # two-part test the deployment packer uses, and the fragility half of
        # it is not optional: a bigger base at the tip of the block has fewer
        # neighbours, which measurably turned this very case (Kill Rig, 11
        # Beast Snagga with a 0.98" Beastboss) from a clump back into a chain.
        if formation_layout.no_worse_than(
            led, chosen, lambda i: squad.models[i].radius_in):
            chosen = led

    # More models than the reachable, on-board, connected area can hold: the
    # remainder go on the outermost arc anyway. The placement is then
    # rejected by confirm_disembark() as it always was - but the CALLER
    # remembers the failure instead of retrying it forever (see
    # _handle_disembark_for_squad()), and tries the next facing first.
    leftover = 0
    for index in range(n):
        if index in chosen:
            continue
        angle = base_angle + leftover * (2 * math.pi / max(1, n))
        leftover += 1
        chosen[index] = (
            transport_token.x_in + outer * math.cos(angle),
            transport_token.y_in + outer * math.sin(angle),
        )

    return [chosen[i] for i in range(n)]


def _ingress_pack_positions(
    squad, origin_x, origin_y, all_tokens, angle_offset=0.0, position_valid=None,
    base_angle_override=None,
):
    """Rule 20.04 arrival geometry: pack the squad onto concentric rings
    around its drop point, keeping every model on legal ground and the unit in
    one connected group (rule 09.02).

    Replaces the straight LINE of models this used to share with the disembark
    path before that one was rebuilt. A line is a shape that fails wholesale:
    six models at a 1.5" pitch is a 7.5" bar that has to be clear along its
    whole length, and the spots worth arriving at are exactly the ones with a
    wall or a board edge nearby. Measured on the reported board, at each of the
    Tankbustas' six best-scoring landing spots, EVERY one of the eight facings
    left between one and six models on illegal ground - so the whole ranking
    was thrown away and the unit arrived at a spot with nothing in range, which
    is the user's "tank bustas kamen wieder oben rechts und hatten nichts in
    reichweite". Rings degrade gracefully instead: a blocked slot costs one
    slot, not the placement.

    Same three guarantees as _disembark_pack_positions(), for the same reasons
    (see its docstring): every slot is checked for THIS model, squadmates never
    overlap, and each new model is placed in coherency range of one already
    down, so a single connected group is built rather than hoped for.

    The ring geometry itself now lives in game/formation_layout.py, because the
    human's "Place as Block" placement needs exactly the same shape and
    game/setup.py cannot import ai/. What stays here is the only part that is
    actually an AI judgement: WHICH WAY the block should face."""
    if not squad.models:
        return []

    # Face the way the line used to: away from the nearest enemy, so a freshly
    # arrived unit packs on the safe side of its own drop point.
    #
    # `base_angle_override` exists for pre-game deployment (rule 03.01), where
    # the fallback below is actively wrong: early in an alternating deployment
    # there is often no enemy on the board at all, and a fixed -pi/2 packs the
    # unit toward negative y - which is backwards into their own zone for one
    # player and forwards into no man's land for the other. The caller passes
    # "away from the board centre" instead.
    if base_angle_override is not None:
        base_angle = base_angle_override
    elif (nearest_enemy := _nearest_enemy_squad(squad, all_tokens)) is not None:
        ex, ey = _centroid(nearest_enemy)
        dx, dy = origin_x - ex, origin_y - ey
        dist = (dx * dx + dy * dy) ** 0.5
        base_angle = math.atan2(dy, dx) if dist > 1e-9 else -math.pi / 2
    else:
        base_angle = -math.pi / 2

    return formation_layout.pack_positions(
        squad, origin_x, origin_y,
        base_angle=base_angle + angle_offset,
        position_valid=position_valid,
        rings=_INGRESS_PACK_RINGS,
        gap_in=DISEMBARK_MODEL_GAP_IN,
    )


def _spread_disembarked_squad(setup_controller, squad, transport_token, all_tokens, max_distance_in, angle_offset=0.0):
    """Rule 18.04/18.05: place a disembarking squad around its TRANSPORT
    within `max_distance_in` (the mode's own DISEMBARK_DISTANCE_IN, read
    from transport_controller.disembark_mode by the caller - no longer a
    fixed guess that silently stopped fitting once squads got bigger). See
    _disembark_pack_positions() for the geometry and the endless-loop bug
    it exists to fix."""
    positions = _disembark_pack_positions(
        squad, transport_token, max_distance_in, all_tokens, angle_offset,
        setup_controller=setup_controller,
    )
    for model, (x, y) in zip(squad.models, positions):
        model.x_in, model.y_in = setup_controller.clamp_position(model, x, y)


def _place_disembarked_squad(transport_controller, setup_controller, squad, transport_token, all_tokens):
    """Try to actually land a squad that SetupController is currently
    placing after a Disembark Move, sweeping _DISEMBARK_FACINGS until one
    of them confirms. Returns True if the squad is on the battlefield.

    One shot at "face the enemy" is exactly what kept failing (user: "bei
    den trukks hat auch kein disembark geklappt. das muss viel robuster
    werden. wenn ein disembark im entscheidenden moment fehlschlägt ist das
    spiel gelaufen") - the clump is anchored on the direction of the nearest
    enemy, so when that side happens to be blocked by terrain, friendly
    models or the board edge, the whole unloading fails even though there
    was room a quarter turn away. Same bounded retry ladder the charge and
    the movement sweep already use.

    Shared by both callers on purpose. The resume path (a Combat/Emergency
    Disembark picked up in a later frame) used to call
    _spread_disembarked_squad() exactly once, with the default facing - so
    the ONE placement in this codebase whose failure destroys the unit
    outright (18.05) was also the only one without the retry ladder."""
    for offset in _DISEMBARK_FACINGS:
        _spread_disembarked_squad(
            setup_controller, squad, transport_token, all_tokens,
            DISEMBARK_DISTANCE_IN[transport_controller.disembark_mode], offset,
        )
        transport_controller.confirm_disembark()
        if setup_controller.setting_up_squad is None:
            return True
    return False


def _maybe_resume_disembark_placement(transport_controller, setup_controller, player, all_tokens, game_log=None):
    """Finish a Disembark Move of `player`'s own that SetupController is
    already mid-placement on, whatever phase it is and whoever's turn it is.

    Real hang, user-reported ("wenn ein transporter zerstört wird, hängt das
    spiel daran anschließend, die insassen aussteigen zu lassen ... die ki
    hat nicht weiter gemacht und ich konnte auch nichts machen"). A
    voluntary Disembark Move (18.04) only ever starts inside the AI's own
    Movement phase, so resuming it from _handle_movement() was enough. An
    Emergency Disembark (18.05) is the opposite: it is triggered by the
    TRANSPORT being DESTROYED, which almost always happens in the OPPONENT's
    Shooting or Fight phase. take_one_action()'s phase dispatch never calls
    _handle_movement() there, and _is_blocked()'s turn_owner check returns
    early long before it anyway - so nothing on the AI side could ever
    complete the placement, and the human was left staring at a stack of the
    AI's models with no indication that they were now expected to spread out
    somebody else's unit by hand.

    Hence: checked in take_one_action() BEFORE _is_blocked(), exactly like
    the reactive charge resume and _maybe_resolve_rapid_ingress_placement()
    above it, and scoped to `player`'s own squad so a human placement is
    never touched."""
    if transport_controller is None or setup_controller is None:
        return False
    squad = setup_controller.setting_up_squad
    if (
        setup_controller.state != PLACING or squad is None or squad.owner != player
        or not transport_controller.is_disembarking(squad)
    ):
        return False
    mode = transport_controller.disembark_mode
    transport_token = transport_controller.disembark_transport
    if _place_disembarked_squad(transport_controller, setup_controller, squad, transport_token, all_tokens):
        return True
    # Couldn't legally be placed from any facing. cancel_disembark() is the
    # only way out - for a voluntary disembark it puts the squad back aboard
    # (and the caller records the refusal so this doesn't re-run forever),
    # for an Emergency Disembark it is rule 18.05's "destroyed".
    if game_log is not None:
        game_log.add(
            f"{squad.owner}: {squad.name} could not be placed after disembarking from any facing "
            f"({mode} disembark, rule 18.04/18.05).",
            file_only=True,
        )
    transport_controller.cancel_disembark()
    return False


def _nearest_model_to_point(squad, x_in, y_in):
    return min(squad.models, key=lambda m: (m.x_in - x_in) ** 2 + (m.y_in - y_in) ** 2)


class _ExposureProbe:
    """A minimal duck-typed stand-in for a Token, so a hypothetical landing
    point can be fed straight into line_of_sight.has_line_of_sight()
    without actually moving any real model (which would mutate live game
    state mid-decision, before the move is even confirmed) - only the
    attributes has_line_of_sight()/its own _blocking_models() actually
    read (x_in/y_in/radius_in, and squad - so the squad's OWN other models
    are correctly excluded as blockers, same as a real model of that squad
    would be, rule 06.01)."""
    __slots__ = ("x_in", "y_in", "radius_in", "squad")

    def __init__(self, x_in, y_in, radius_in, squad):
        self.x_in = x_in
        self.y_in = y_in
        self.radius_in = radius_in
        self.squad = squad


def _exposure_at(x_in, y_in, squad, enemy_squads, obstacles, all_tokens, terrain_areas):
    """How many enemy squads would have line of sight to `squad` if its
    representative model stood at (x_in, y_in) - a cheap approximation
    (checked against each enemy squad's single model NEAREST to the
    candidate point, at a reduced sample_points, rather than a full
    per-model sweep of every enemy) used only to RANK candidate staging
    points against each other, not to resolve any actual rule - the real
    Benefit of Cover/Hidden checks (rule 13.08/13.09) are unaffected and
    still run at full precision once the squad has actually moved there."""
    probe = _ExposureProbe(x_in, y_in, max_model_radius(squad), squad)
    count = 0
    for enemy in enemy_squads:
        nearest = _nearest_model_to_point(enemy, x_in, y_in)
        if line_of_sight.has_line_of_sight(
            probe, nearest, obstacles, all_tokens, terrain_areas,
            sample_points=STAGING_EXPOSURE_SAMPLE_POINTS,
        ):
            count += 1
    return count


def _reaches_objective_after_disembark(squad, predicted_positions, objectives):
    """Would landing at `predicted_positions` put this squad on (or right
    next to) a mission objective it doesn't already hold?

    Real gap found via user report ("breacher werden nicht ausgeladen,
    obwohl es einen befehl dafür gab. lag es vielleicht am platzmangel?" -
    no, space was never the problem: the whole game log contained not a
    single disembark event, because the choice was never offered at all).
    _has_target_after_disembark() only ever asked "is there an ENEMY worth
    shooting or charging from there" - claiming ground was not a reason it
    accepted, even though the plan's own order for that squad was "disembark
    next to the Central Objective to begin claiming the central zone".
    Objectives are the primary VP source (3 VP each, every own Command
    phase), so getting out to take one is at least as good a reason to
    disembark as a shot is."""
    if not objectives:
        return False
    radius = max_model_radius(squad)
    for x, y in predicted_positions:
        probe = _ExposureProbe(x, y, radius, squad)
        for objective in objectives:
            if objective.controlled_by == squad.owner:
                continue  # already ours - getting out changes nothing there
            if objective.terrain_area.distance_to_model(probe) <= OBJECTIVE_CONSOLIDATION_RANGE_IN:
                return True
    return False


def _has_target_after_disembark(squad, predicted_positions, all_tokens, obstacles, terrain_areas):
    """User-requested policy ("die KI sollte nur aus Transports aussteigen,
    wenn es anschließend ein gutes Ziel zum Schießen/Chargen gibt"): would
    landing at `predicted_positions` (one (x, y) per model, see
    _predict_squad_positions_from_point()) leave `squad` with anything
    worth doing THIS turn - an enemy unit within charge-declare range
    (12", rule 11.01/CHARGE_RANGE_IN), or within one of its own ranged
    weapons' range and actually visible (line_of_sight, same cheap
    STAGING_EXPOSURE_SAMPLE_POINTS precision as the staging heuristic
    above - this only gates a coarse "is disembarking worth it at all"
    check, it doesn't resolve any actual rule)?

    Deliberately approximate, same spirit as every other "one representative
    model/position" simplification in this file: ignores engagement,
    Hidden/LONE OPERATIVE, [INDIRECT FIRE], and the fact that the real
    spread (via SetupController.clamp_position(), board edges, terrain)
    could land slightly differently than these raw, unclamped predicted
    points - close enough for a "worth it or not" gate, not precise enough
    to resolve an actual shot/charge."""
    enemy_squads = [s for s in _all_squads(all_tokens) if s.owner != squad.owner and s.models]
    if not enemy_squads:
        return False
    probes = [_ExposureProbe(x, y, max_model_radius(squad), squad) for x, y in predicted_positions]

    # Charge: any enemy squad within 12" straight-line of any predicted model.
    if any(
        edge_distance(probe, enemy_model) <= CHARGE_RANGE_IN
        for probe in probes
        for enemy in enemy_squads
        for enemy_model in enemy.models
    ):
        return True

    # Shooting: any of the squad's own ranged weapons whose range reaches an
    # enemy model that's actually visible from that same predicted spot.
    ranged_weapons = [w for w in squad.models[0].weapons if w.weapon_type == RANGED]
    if not ranged_weapons:
        return False
    max_range = max(w.range_in for w in ranged_weapons)
    for probe in probes:
        for enemy in enemy_squads:
            # A target the rules will not let this unit shoot at is not a
            # reason to get out. User's own framing: there are exactly three
            # reasons to disembark - shoot, charge, or take an objective off
            # the enemy - and this branch is the "shoot" one, so it has to
            # mean a shot that can actually happen. LONE OPERATIVE (24.24)
            # caps how far away the shooter may be; the check was documented
            # as ignoring it, and the result was Boyz unloading on turn 1 to
            # "shoot Sluggas" at something they could never have targeted.
            lone_range = status_effects.lone_operative_range(enemy)
            nearest = _nearest_model_to_point(enemy, probe.x_in, probe.y_in)
            if lone_range is not None and edge_distance(probe, nearest) > lone_range:
                continue
            if edge_distance(probe, nearest) > max_range:
                continue
            if line_of_sight.has_line_of_sight(
                probe, nearest, obstacles, all_tokens, terrain_areas,
                sample_points=STAGING_EXPOSURE_SAMPLE_POINTS,
            ):
                return True
    return False


def _best_staging_point(squad, max_distance, all_tokens, obstacles, terrain_areas):
    """User-requested tactical heuristic ("Staging": reposition into safer
    ground before committing to an attack), not itself a rule. Among the
    Dense terrain areas within reach, picks whichever reachable landing
    point is seen by the fewest enemy squads (_exposure_at()) - an actual
    line-of-sight-based search, not just "walk toward the nearest terrain
    regardless of whether it would actually break sight". Returns None if
    the squad is already fully hidden where it stands (nothing to gain by
    moving) or no reachable candidate beats staying put.

    Aims each candidate at a terrain area's bounding-box CENTER, not just
    its nearest edge - a real ruin's footprint is walls around an open,
    walkable (rule 13.06) floor, so heading for the middle actually walks
    the squad in among the walls rather than just up to the outside face of
    the nearest one, which on its own wouldn't put anything between the
    squad and a threat standing on the same side of that one wall."""
    cx, cy = _centroid(squad)
    enemy_squads = [s for s in _all_squads(all_tokens) if s.owner != squad.owner and s.models]
    if not enemy_squads or max_distance <= 0:
        return None

    current_exposure = _exposure_at(cx, cy, squad, enemy_squads, obstacles, all_tokens, terrain_areas)
    if current_exposure == 0:
        return None

    dense_areas = [a for a in terrain_areas if a.has_dense_feature]
    dense_areas.sort(key=lambda a: a.distance_to_point(cx, cy))

    # Delegates to the same computation the PLANNER is shown
    # (observation.staging_positions()), instead of the older exposure-only
    # search that used to live here.
    #
    # Why it had to change (user: "im testgame gerade sind sotmboyz und warbiker
    # nach hinten gesprintet anstatt zu stagen"): the old search minimised ONE
    # quantity - how many enemy squads can see the spot - with no term for
    # ground gained, no charge risk, and line of sight measured against the
    # enemy where it stands right now. For a unit near a board edge the
    # least-seen reachable spot is behind it, so "stage" reliably meant
    # "retreat". Worse, there were then two different answers to the same
    # question on the board: the planner ranked safe spots by progress and
    # charge risk while this option ignored both.
    spots = observation.staging_positions(
        squad, enemy_squads, obstacles, terrain_areas, all_tokens,
        goal=_squad_centroid_of_nearest(squad, enemy_squads),
        board_w_in=config.BOARD_WIDTH_IN, board_h_in=config.BOARD_HEIGHT_IN,
    )
    if not spots:
        return None
    # Already sorted best-progress-first, and every entry stays hidden even
    # after the enemy moves - so this is the most forward genuinely safe spot.
    return (spots[0]["x"], spots[0]["y"])


def _squad_centroid_of_nearest(squad, enemy_squads):
    """Centroid of the closest enemy unit - the direction "forward" means for
    this squad, so a staging spot can be ranked on ground gained."""
    nearest = min(enemy_squads, key=lambda e: _squad_distance_between(squad, e))
    return (sum(m.x_in for m in nearest.models) / len(nearest.models),
            sum(m.y_in for m in nearest.models) / len(nearest.models))


def _squad_distance_between(a, b):
    return min(((m.x_in - o.x_in) ** 2 + (m.y_in - o.y_in) ** 2) ** 0.5 - m.radius_in - o.radius_in
               for m in a.models for o in b.models)


def _nearest_objective(squad, candidates):
    """Nearest of `candidates` (already-filtered Objectives) to squad's own
    centroid, by distance to the objective's terrain area - ties broken by
    objective.name for determinism (same tie-break style as
    _movement_priority_key()'s squad.name). Returns (objective, aim_point)
    where aim_point is the objective's terrain-area bounding-box center
    (same "aim at the middle, not the nearest edge" reasoning as
    _best_staging_point()/_consolidate_toward_objective() - a real
    objective's footprint can be a ruin's walkable interior, not just its
    outer edge)."""
    cx, cy = _centroid(squad)
    objective = min(candidates, key=lambda o: (o.terrain_area.distance_to_point(cx, cy), o.name))
    min_x, min_y, max_x, max_y = objective.terrain_area.bounding_box
    return objective, ((min_x + max_x) / 2, (min_y + max_y) / 2)


def _best_objective_target(squad, objectives, all_tokens):
    """User-requested tactical policy ("die KI muss Objectives mit hoher
    Priorität verfolgen"): among mission objectives (rule 14.01) this squad
    isn't already standing on, pick the single best one to head toward -
    deliberately only ONE candidate (not a scored/weighted list), matching
    this file's established "one best candidate per option type" pattern
    (see _best_staging_point()/_nearest_enemy_squad()) - actually judging
    whether a given objective is WORTH going for (who's defending it, how
    much OC is already there) is left to Claude via the OC-present/
    controlled_by data now visible in the observation (see
    ai/observation.py's objective_summary()), not duplicated here as a
    second hard-coded heuristic.

    Excludes any objective the squad is already standing on
    (is_on_objective(), the same footprint-overlap check
    Objective.level_of_control() itself uses) regardless of who currently
    controls it - a squad that just arrived at a still-contested objective
    (nobody's flipped it yet) has nowhere meaningful to "move to" on top of
    its own position; _handle_movement()'s remain_stationary annotation
    covers that case instead (see its own comment).

    Two-tier preference, still pure geometry (not a scoring algorithm):
    prefer the nearest UNCONTROLLED objective over the nearest one the
    enemy already holds, since standing up an uncontrolled objective is a
    structural fact (is anyone there at all, winning?), not a judgment
    call - only falls back to the nearest enemy-controlled one if no
    uncontrolled objective is available at all. This avoids the failure
    mode of a squad only ever being offered "go fight for contested
    ground" when free ground was sitting right there, without ever scoring/
    weighing anything.

    Returns (objective, aim_point) or None if there's nothing to offer."""
    candidates = [o for o in objectives if not is_on_objective(squad, [o])]
    if not candidates:
        return None
    uncontrolled = [o for o in candidates if o.controlled_by is None]
    if uncontrolled:
        return _nearest_objective(squad, uncontrolled)
    not_ours = [o for o in candidates if o.controlled_by != squad.owner]
    if not not_ours:
        return None
    return _nearest_objective(squad, not_ours)


def _lateral_positions(span):
    """Evenly spaced points from 0 to `span` inclusive, roughly
    INGRESS_LANDING_LATERAL_STEP_IN apart - used to scan a battlefield
    edge's FULL length (see _ingress_landing_candidates()), not just a
    window around one preferred spot."""
    steps = max(1, round(span / INGRESS_LANDING_LATERAL_STEP_IN))
    return [i * span / steps for i in range(steps + 1)]


def _preferred_ingress_target(squad, all_tokens, objectives):
    """Where a freshly-arriving reserve squad should aim to land, in
    priority order - user-requested policy ("Rapid Ingress... sind
    Werkzeuge, um möglichst viel OC auf Objectives zu bekommen"):

    1. The nearest mission objective (rule 14.01) not already controlled
       by squad.owner - uncontrolled preferred over enemy-held, same
       two-tier structural preference as _best_objective_target() (a
       squad hasn't landed yet, so there's no "already standing on it" to
       exclude here, unlike that helper).
    2. Otherwise, the nearest enemy squad's centroid (the previous, only,
       behavior).
    3. Otherwise (no objectives, no enemy left), board center.

    A squad's models retain their x_in/y_in while in reserves (this file's
    existing _nearest_enemy_squad()/min_distance_to() calls already relied
    on that before this function existed), so _centroid(squad) is safe to
    use here too."""
    if objectives:
        candidates = [o for o in objectives if o.controlled_by != squad.owner]
        if candidates:
            uncontrolled = [o for o in candidates if o.controlled_by is None]
            _, point = _nearest_objective(squad, uncontrolled or candidates)
            return point
    nearest_enemy = _nearest_enemy_squad(squad, all_tokens)
    if nearest_enemy is not None:
        return _centroid(nearest_enemy)
    return config.BOARD_WIDTH_IN / 2, config.BOARD_HEIGHT_IN / 2


def _ingress_landing_score(point, squad, enemy_squads, objectives, obstacles, terrain_areas, all_tokens):
    """Rank one reserve landing spot the way a movement destination is ranked.

    Reserve arrival used to be sorted purely by distance to a preferred target -
    "as far forward as legal", with no notion of what the unit could do there or
    what could be done to it. That is the same blind spot the movement side had
    before threat assessment existed, and the user asked for the same treatment
    ("Platzierung von Einheiten aus Reserve sollte das gleiche Threat Management
    haben wie movement. Entweder dort, wo man direkt viel schaden anrichten kann,
    oder in sicherheit, wo man später aktiv werden kann. oder für missionen").

    Those are exactly three criteria, and they are already computable:
      1. damage now      - can this unit shoot something from here, and how hard
      2. safety for later - does the spot stay hidden once the enemy moves too,
                            and how likely is a charge into it
      3. missions        - how close is a contestable objective

    Deliberately still deterministic, with no agent call: the timing of Ingress
    is a standing instruction rather than a judgment call, and the judgment that
    IS wanted enters one level up - the planner already sees reserve units and
    can name a position for one, which _auto_ingress_squad() honours before this
    ranking is consulted at all. Returns a sort key, lower is better."""
    x, y = point
    radius = max_model_radius(squad)
    live = [e for e in enemy_squads if e.models]

    # 1. What this unit could shoot from here, weighted by how much it hurts.
    # Ranges come from EVERY model, not squad.models[0]: models[0] is whichever
    # model the datasheet lists first, and for Ork Tankbustas that is the Boss
    # Nob, whose Rokkit Pistol reaches 12" while the five Tankbustas behind him
    # carry 24" Rokkit Launchas. Scoring landing spots against half the unit's
    # real reach is exactly how an anti-tank squad ends up parked out of range
    # of everything - the same representative-model assumption ranged_weapon_
    # summary() was already fixed for.
    damage = 0.0
    ranges = [w.range_in for m in squad.models for w in m.weapons
              if getattr(w, "weapon_type", None) == "ranged"]
    if ranges:
        # NO movement bonus: a unit that has just ingressed is ingress_locked and
        # cannot move again until the Charge phase, so crediting it with its Move
        # characteristic gave it range it does not have this turn.
        reach = max(ranges)
        for enemy in live:
            gap = observation._point_distance_to_squad((x, y), enemy)
            if gap > reach:
                continue
            if not observation.visible_enemy_units_from_point(
                x, y, radius, [enemy], obstacles, terrain_areas, all_tokens,
            ):
                continue
            damage = max(damage, observation.damage_value(squad, enemy))

    # 2. Safety for later: hidden after the enemy's own move, and hard to charge.
    # How close this spot gets the unit to something worth shooting NEXT turn,
    # once the ingress lock is gone. Without this the score had nothing to say
    # about a spot that is useless now and decisive in one turn: whenever no
    # candidate could shoot on arrival - the common case, since arrival must stay
    # 8" clear of every enemy - the damage term was 0 everywhere and EXPOSURE
    # decided, which reliably picks the emptiest corner. Reported twice in one
    # game: Tankbustas landed at (2,24) and Deffkoptas at (6,54) with the enemy
    # near (7,5), and both then stood still.
    # "Worth shooting" here means worth shooting FOR THIS UNIT, by the same
    # value measure as the damage term - otherwise this pulls a specialist
    # toward whatever cheap screen happens to be nearest and leaves it there.
    # Anything within half the best available value counts, so a slightly
    # weaker but much closer target is still allowed to win.
    best_next_turn = config.BOARD_WIDTH_IN + config.BOARD_HEIGHT_IN
    if ranges:
        values = {id(e): observation.damage_value(squad, e) for e in live}
        worthwhile = max(values.values(), default=0.0) * 0.5
        for enemy in live:
            if values[id(enemy)] <= max(worthwhile, 0.05):
                continue
            gap = observation._point_distance_to_squad((x, y), enemy)
            best_next_turn = min(
                best_next_turn,
                max(0.0, gap - max(ranges) - min_model_movement(squad)),
            )

    exposed = sum(
        1 for e in live
        if observation._could_shoot_point(e, x, y)
        and not observation._spot_stays_hidden(
            x, y, radius, e, obstacles, terrain_areas, all_tokens,
            config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN)
    )
    charge_risk = len([
        t for t in observation.charge_threats(squad, live, at_point=(x, y))
        if t["charge_roll_needed"] <= 8
    ])

    # 3. Missions: how far to an objective this army does not already hold.
    contestable = [o for o in objectives if getattr(o, "controlled_by", None) != squad.owner]
    to_objective = min(
        (o.terrain_area.distance_to_point(x, y) for o in contestable),
        default=config.BOARD_WIDTH_IN,
    )

    # A spot that can hurt something now still outranks a merely safe one. Among
    # spots that cannot, what decides is no longer pure hiding: how far this spot
    # still is from a worthwhile target NEXT turn comes first, then exposure,
    # charge risk and the objective.
    # Damage is bucketed into LANDING_DAMAGE_BUCKET_PTS rather than compared
    # exactly: expected_kills() is an explicit approximation, so a one-point
    # difference between two spots is noise, and letting noise decide would
    # silently override the safety terms below it. Within a bucket the spots
    # are a tie and exposure/charge risk settle it.
    bucket = -int(damage // LANDING_DAMAGE_BUCKET_PTS)
    return (bucket, round(best_next_turn), exposed, charge_risk, round(to_objective, 1))


def _ingress_landing_candidates(ingress_controller, squad, all_tokens, objectives=(), limit=INGRESS_LANDING_CANDIDATE_LIMIT,
                                score_with=None):
    """Rule 20.04 doesn't restrict Ingress to the owner's own battlefield
    edge - so all 4 edges are viable candidates. Scans each edge's FULL
    length (_lateral_positions()), not just a window near the "ideal"
    spot - see the module comment above INGRESS_LANDING_DEPTH_STEPS_IN for
    why a narrow window isn't enough on a sufficiently crowded board. At
    each sampled lateral position, tries a bounded set of depths into the
    legal 6" margin (deepest first, since that's usually closest to a
    target on the far side of the board), keeping the deepest-legal point.
    Returns up to `limit` candidates, closest to _preferred_ingress_
    target() first (an objective worth contesting, else the nearest
    reachable enemy squad's centroid, else board center) - NOT just the
    single best one, because legality here only checks the ONE
    representative point, not the squad's actual spread-out formation
    (_auto_ingress_squad needs several tries, since the very best-looking
    point can still turn out to collide with existing terrain/models once
    the models are actually spread into their final line - see its own
    docstring)."""
    representative = squad.models[0]
    tx, ty = _preferred_ingress_target(squad, all_tokens, objectives)

    edges = (
        (config.BOARD_HEIGHT_IN, lambda depth, lateral: (depth, lateral)),                                  # left
        (config.BOARD_HEIGHT_IN, lambda depth, lateral: (config.BOARD_WIDTH_IN - depth, lateral)),           # right
        (config.BOARD_WIDTH_IN, lambda depth, lateral: (lateral, depth)),                                    # top
        (config.BOARD_WIDTH_IN, lambda depth, lateral: (lateral, config.BOARD_HEIGHT_IN - depth)),           # bottom
    )

    candidates = []
    for span, edge in edges:
        for lateral in _lateral_positions(span):
            for depth in INGRESS_LANDING_DEPTH_STEPS_IN:
                x, y = edge(depth, lateral)
                if ingress_controller.position_valid(squad, representative, x, y):
                    candidates.append((x, y))
                    break  # deepest-legal-depth-first per lateral position - no need to try shallower

    # [DEEP STRIKE] (24.09) is not confined to the edge margin - see
    # DEEP_STRIKE_GRID_STEP_IN. position_valid() already enforces everything
    # that still does apply (>8" from every enemy model, terrain, overlap,
    # board edge), so this only widens WHERE the sweep looks, never what it
    # accepts. Added to the edge candidates rather than replacing them: an
    # edge spot is a perfectly good drop zone when it scores better.
    if ingress_controller._has_deep_strike(squad):
        step = DEEP_STRIKE_GRID_STEP_IN
        y = step
        while y < config.BOARD_HEIGHT_IN:
            x = step
            while x < config.BOARD_WIDTH_IN:
                if ingress_controller.position_valid(squad, representative, x, y):
                    candidates.append((x, y))
                x += step
            y += step

    candidates.sort(key=lambda p: (p[0] - tx) ** 2 + (p[1] - ty) ** 2)
    if score_with is not None:
        # Threat-aware ranking (see _ingress_landing_score()); distance to the
        # preferred target stays as the tie-breaker so an otherwise equal pair
        # still lands forward rather than arbitrarily.
        #
        # Only the nearest SCORED_LANDING_CANDIDATES are scored: _ingress_
        # landing_score() runs line-of-sight probes per enemy, which is orders
        # of magnitude more expensive than the pure geometry above, and this
        # runs on the main thread while the window is drawing. Scoring the full
        # Deep Strike grid measured at 1.2s - a visible freeze. The pre-sort is
        # distance to the preferred target, so what gets dropped is the far end
        # of the board, which the score would not have picked anyway.
        scored = candidates[:SCORED_LANDING_CANDIDATES]
        scored.sort(key=lambda p: score_with(p) + ((p[0] - tx) ** 2 + (p[1] - ty) ** 2,))
        candidates = scored + candidates[SCORED_LANDING_CANDIDATES:]
    return candidates[:limit]


def _best_ingress_landing_point(ingress_controller, squad, all_tokens, objectives=()):
    """The single closest-to-the-front legal candidate, if any - a thin
    convenience wrapper around _ingress_landing_candidates() for callers
    that (unlike _auto_ingress_squad()) don't need to retry against
    several candidates. (Currently unused anywhere in this file - kept
    signature-consistent with the other ingress-landing helpers rather
    than left to drift.)"""
    candidates = _ingress_landing_candidates(ingress_controller, squad, all_tokens, objectives=objectives, limit=1)
    return candidates[0] if candidates else None


def _auto_ingress_squad(setup_controller, ingress_controller, squad, all_tokens, objectives=(),
                        state=None, plan=None, game_log=None):
    """Deploys `squad` from strategic reserves via an Ingress move (rule
    20.04) as soon as it's legally eligible, landing as close as possible
    to the front (see _ingress_landing_candidates()) so it's useful as
    soon as possible - a deterministic policy per explicit user
    instruction ("Reserven immer zum möglichst frühen Zeitpunkt
    einsetzen"), not a judgment call, so no agent.decide() call at all
    (same "no real decision, don't ask" reasoning as the mandatory
    Battle-Shock roll in _handle_battle_shock()).

    Tries EVERY sampled candidate (closest first), not just the first one -
    a real gap found while testing this against the actual demo scene: a
    candidate's single representative point can pass position_valid() and
    still fail once the squad's models are actually packed out around it
    (_ingress_pack_positions() - e.g. one of the outer models lands on a
    wall or another model that the centre point alone was clear of).
    Without retrying, a squad whose closest-to-the-front spot happens to
    spread illegally would keep failing the exact same way on every future
    call (nothing else moves it in between), stalling forever - directly
    against the "always deploy as early as possible" policy this exists
    for. Even so, this is still a bounded, sampled search, not a true
    solver - in the (rare, extreme) case where every one of the ~36 sampled
    points fails once spread out, the squad just stays in reserves and
    tries again on a later call (a fresh, possibly different, sampled set,
    since the board may have changed by then), same "no repair loop, just
    keep trying next time" limitation as every other AI move in this file.

    Returns True only if it actually landed; False if every candidate this
    call sampled failed - callers should treat False as "didn't act" (e.g.
    try another reserve squad, or fall through to normal on-board movement
    handling), not as a spent action, since nothing observable happened."""
    # Where to land is now a threat judgement, not just "as far forward as
    # legal" (see _ingress_landing_score()). The planner gets the first word:
    # if it named a position for this reserve unit, that spot leads the list,
    # because only the planner knows what it wanted the unit there FOR.
    score_with = None
    if state is not None:
        foes = [q for q in _all_squads(state.tokens) if q.owner != squad.owner and q.models]
        score_with = lambda p: _ingress_landing_score(
            p, squad, foes, objectives, state.obstacles, state.terrain_areas, all_tokens,
        )
    candidates = _ingress_landing_candidates(
        ingress_controller, squad, all_tokens, objectives=objectives, score_with=score_with,
    )
    planned = _planned_position(squad, plan) if plan else None
    if planned is not None:
        candidates = sorted(
            candidates,
            key=lambda p: (p[0] - planned[0]) ** 2 + (p[1] - planned[1]) ** 2,
        )
    source = "its turn plan named that spot" if planned is not None else "best damage/safety/objective spot"
    for rank, (x, y) in enumerate(candidates):
        # Every FACING at this spot before giving up on the spot itself. The
        # models are laid out in a line, so a single blocked orientation used to
        # discard the whole landing point - and the points are ranked, so the
        # one discarded is the BEST one. Measured on the reported board: the
        # Tankbustas' top-scoring spot (in range of, and with line of sight to,
        # the Crisis suits they are built to kill) failed on its one facing and
        # they ended up 20" away with nothing to shoot at, which is exactly the
        # report ("tankbustas und kopter ... konnten beides nichts sehen").
        # Same ladder, and same reason, as _DISEMBARK_FACINGS.
        placed = False
        for facing in _DISEMBARK_FACINGS:
            ingress_controller.start_ingress(squad, x, y)
            if setup_controller.setting_up_squad is not squad:
                break  # start_ingress() itself refused this spot - facings cannot help
            positions = _ingress_pack_positions(
                squad, x, y, all_tokens, angle_offset=facing,
                # The FULL arrival rule per slot, not just standable ground:
                # rule 20.04's >8" from every enemy model, the 6" edge margin
                # and (before round 3) the enemy deployment zone all decide
                # whether an individual model may stand there, and a slot that
                # fails any of them has to be skipped rather than handed out.
                position_valid=lambda model, px, py: ingress_controller.position_valid(squad, model, px, py),
            )
            for model, (px, py) in zip(squad.models, positions):
                model.x_in, model.y_in = setup_controller.clamp_position(model, px, py)
            ingress_controller.confirm_ingress()
            if setup_controller.setting_up_squad is None:
                placed = True
                break
            ingress_controller.cancel_ingress()
        if placed:
            # Logged HERE, not before the loop, and with the spot actually used.
            # The line used to report candidates[0] - the best-SCORING spot -
            # while the loop lands on the first one that survives being spread
            # out, which is frequently a different, much worse one (measured:
            # the top spot failed and a squad landed 20" away from it). A
            # diagnostic line that names a place the unit is not standing is
            # worse than none, since every later investigation starts from it.
            if game_log is not None:
                behind = f", candidate #{rank + 1} - {rank} better-scoring spot(s) would not fit" if rank else ""
                game_log.add(
                    f"  [ingress] {squad.name} lands at ({x:.0f},{y:.0f}) ({source}{behind})",
                    file_only=True,
                )
            return True  # landed successfully
        # No facing worked here - the inner loop already cancelled its own last
        # attempt, so nothing is left open to clean up. Try the next spot.
    if game_log is not None:
        game_log.add(
            f"  [ingress] {squad.name} could not be placed at any of {len(candidates)} sampled spots "
            "- stayed in reserves this call",
            file_only=True,
        )
    return False  # nowhere legal to land in this sampled set yet - try again next call


def _pile_in_squad(pile_in_controller, movement_controller, squad):
    """Rule 12.03: piling in is optional, but which enemy units it must stay
    engaged with isn't really a player choice (PileInController's own
    docstring: "mandatory, not optional per the rule text") - so the only
    real decision left is which ONE of those already-engaged targets to aim
    the (small, <=3") translation at.

    Real, severe bug found via user report ("pile ins werden geskipped"):
    this used to ONLY try _translate_squad_for_charge()'s rigid whole-squad
    translation and, on any failure, skip the pile-in entirely with no
    retry at all. Fixed by trying _charge_per_model() (despite its name,
    purely geometric - moves each model to ITS OWN nearest enemy model,
    independently routed around whatever's in its own way), with the same
    PILE_IN_CLEARANCE_IN "as close as possible" (rule 12.03) target the
    rigid version used.

    User directive: "bitte zwinge die KI beim chargen und pile in Modell
    für Modell zu bewegen. Keine bulk moves mehr in der Charge- und Fight-
    Phase." - the rigid whole-squad translation fallback that briefly
    existed here has been removed entirely; _charge_per_model() is the ONLY
    pile-in movement this file performs, skip_pile_in() the only remaining
    fallback if even that can't land legally."""
    targets = pile_in_controller.pile_in_targets(squad)
    if not targets:
        pile_in_controller.skip_pile_in(squad)
        return
    movement_controller.select(squad.models[0])
    before = _engaged_model_count(squad, targets)

    # Which of the engaged enemy units to aim the translation at used to be
    # "the nearest one", assumed to be the best answer. It is measurable
    # instead: run the placement against each candidate and keep whichever
    # arrangement puts the most models in Engagement Range, since that is the
    # only thing a pile-in is for (rule 12.05 - only models in Engagement Range
    # fight). User: "die ki benutzt pile in moves nicht genug, um mehr modelle
    # in nahkampfreichweite zu bekommen. das muss das oberste ziel dabei sein."
    #
    # Only worth paying for with more than one target; a single-target pile-in
    # - the common case - runs exactly once, as before.
    ordered = sorted(targets, key=lambda t: squad.min_distance_to(t))
    target = ordered[0]
    if len(ordered) > 1:
        best_count = -1
        for candidate in ordered:
            pile_in_controller.start_pile_in(squad)
            if movement_controller.move_mode != "pile_in":
                break
            _charge_per_model(movement_controller, squad, candidate, PILE_IN_RANGE_IN,
                              clearance=PILE_IN_CLEARANCE_IN, must_close_to_1in=False)
            count = _engaged_model_count(squad, targets)
            movement_controller.cancel_move()  # restores every model's start position
            if count > best_count:
                target, best_count = candidate, count

    pile_in_controller.start_pile_in(squad)
    # Rule 12.03 (PILE-IN MOVE), WHILE MOVING: "Each model that is moved must end
    # its move closer to the closest pile-in target, AND ENGAGED WITH IT IF
    # POSSIBLE" - engaged, i.e. within Engagement Range (2"). There is no 1"
    # clause here, unlike a charge (11.04), so a model standing at 2" satisfies
    # the rule fully and the outer rings are legal standing room. Enforcing the
    # charge's stricter obligation here cost two models of a nine-model pile-in
    # for nothing (measured: 6->8 dropped to 6->6), so it is switched off.
    _charge_per_model(movement_controller, squad, target, PILE_IN_RANGE_IN,
                      clearance=PILE_IN_CLEARANCE_IN, must_close_to_1in=False)
    pile_in_controller.confirm_pile_in()
    if movement_controller.errors:
        # confirm_pile_in() deliberately does NOT consume the squad's pile-in
        # when the move is rejected (so a human can reposition and retry) -
        # but nothing here ever repositions, so the squad stayed eligible,
        # got picked again on the very next frame, failed again, and the
        # Fight step never began. That is the reported stall: "die ki macht
        # nicht weiter" after a pile-in, and it needs only one squad whose
        # placement is blocked - a wall was in the way in the reported case.
        #
        # Rule 12.03 makes piling in optional, so declining is a legal
        # outcome: revert the illegal placement and mark the squad done, the
        # same "no repair loop" convention this file uses everywhere else.
        pile_in_controller.decline_pile_in()
        pile_in_controller.skip_pile_in(squad)
    if movement_controller.errors:
        # Genuinely couldn't land legally model-by-model - fall back to
        # skipping this pile-in rather than getting stuck.
        pile_in_controller.decline_pile_in()
        pile_in_controller.skip_pile_in(squad)
        return

    # What the pile-in was FOR, in the log, so a reported "the pile-in did
    # nothing" can be checked against a number instead of reconstructed from
    # the two [move detail] coordinate lines around it - which is how the
    # reported case had to be diagnosed.
    game_log = getattr(movement_controller, "game_log", None)
    if game_log is not None:
        after = _engaged_model_count(squad, targets)
        # ...and how many the base-contact house rule held still, because a
        # diagnostic line that leaves out the disputed number sends the next
        # investigation back to the board.
        frozen = len(base_contact.frozen_models(
            squad, movement_controller.all_tokens, movement_controller.move_mode))
        game_log.add(
            f"  [pile in] {squad.name} -> {target.name}: {before} -> {after} of "
            f"{len(squad.models)} model(s) in Engagement Range"
            + (f"; {frozen} frozen in base contact" if frozen else ""),
            file_only=True,
        )


def _engaged_model_count(squad, target_squads):
    """How many of `squad`'s models are within Engagement Range of any of
    `target_squads` - rule 12.05, the models that will actually get to fight.

    The objective a charge and a pile-in are both judged by, so it lives in one
    place rather than being re-derived at each call site."""
    return sum(
        1 for model in squad.models
        if any(edge_distance(model, enemy) <= ENGAGEMENT_RANGE_IN
               for target in target_squads for enemy in target.models)
    )


def _wound_allocation_pick(candidates):
    """Which of the equally eligible models takes this wound (rule 05.04
    step 1 / 06.02 step 1). The engine has already narrowed the list down to
    the models the RULES allow; everything left here is tactics, so this is
    the right place for a preference rather than the allocation session.

    Leader model LAST (user report: "ki ligt wunden immer zuerst auf den
    squad leader. das ist dumm. auf den solllten wunden immer zuletzt gelegt
    werden"). The old behaviour was plain candidates[0], and a datasheet
    lists its leader model first, so build_squad() puts it at models[0] and
    it took every wound before a single rank-and-file model did - i.e. the
    model carrying the unit's best kit (Power Klaw, the DS8 Support Turret,
    Kroot pistol) died first, every time.

    Only the leaders that SHARE their squad's W/Sv were affected, because
    only those share its allocation group: Fire Warrior/Breacher Shas'ui,
    Long-quill, Stealth Shas'vre, Crisis Shas'vre, Tankbusta Boss Nob. A
    tougher leader (Boyz'/Stormboyz'/Warbikers' Boss Nob, 2-4W) is already
    a group of its own and sorted last by Squad.allocation_groups(), and an
    attached CHARACTER (19.01) is already protected by 05.03/06.02 - this
    closes the one gap neither of those covers.

    Deliberately not extended into a general "which model is worth least"
    valuation: that needs a weapon-value model this file doesn't have, and
    the reported case is exactly the squad_leader flag."""
    return next((m for m in candidates if not m.profile.squad_leader), candidates[0])


def _resolve_own_damage_choice(player, controllers):
    """Rule 05.04/06.02: when a wound/mortal wound has more than one equally
    valid model to land on, it's the OWNED player's own choice (a human
    picks for their own units by clicking) - previously nobody ever made
    this choice for Player 2's squads, since main.py's board-click handler
    only fires on a human mouse click and no AI hook existed at all, which
    would have silently stalled the game the first time one of the AI's own
    squads took an ambiguous wound. Picks via _wound_allocation_pick()
    (leader model last) with no agent.decide() call rather than asking -
    every candidate is already "equally eligible" by the engine's own
    priority rules, so this is a standing policy, not a per-wound judgement
    call.

    A multi-wound save failure (e.g. 3 failed D2 saves) can need several
    SEQUENTIAL choose_damage_model() calls before the whole allocation
    session is actually done (each pick can complete one model and leave
    another wound still needing one) - drains all of them in one go rather
    than requiring a separate keypress per wound, since there's no real
    decision being made here at all (unlike, say, a shooting target choice).

    Returns True if it resolved (part or all of) an allocation for `player`
    (that's this call's one action), None if it's the other (human) player's
    own choice to leave untouched, or False if nothing is pending at all."""
    for controller in controllers:
        choice = getattr(controller, "pending_damage_choice", None)
        if not choice:
            continue
        owner = choice[0].squad.owner if choice[0].squad is not None else None
        if owner != player:
            return None  # belongs to the other (human) player - leave it to their own click
        guard = 0
        while choice:
            guard += 1
            if guard > 50:
                break  # safety net against an unexpected infinite loop
            controller.choose_damage_model(_wound_allocation_pick(choice))
            choice = getattr(controller, "pending_damage_choice", None)
            if choice and (choice[0].squad is None or choice[0].squad.owner != player):
                break  # a later wound turned out to need the human's own choice instead
        return True
    return False


def _maybe_resolve_decision(agent, decision_manager, turn_tracker, state, player, on_thinking):
    """Generic resolution for ANY pending game.decision.DecisionManager
    break point that belongs to `player` - Rapid Ingress (15.07), the
    reactive offer main.py opens for whichever player's opponent just ended
    their Movement phase (game/rapid_ingress.py), plus the dormant [LETHAL
    HITS]/[PRECISION]/[TWIN-LINKED] decision points (24.23/24.28/24.38) no
    current datasheet has triggered yet. Fire Overwatch (15.08) USED to be
    one of these too, but was redesigned into its own board-click-a-unit
    state (see game/overwatch.py/_maybe_resolve_fire_overwatch()) - no
    longer routed through DecisionManager at all.

    This was a real, frequently-hit gap: _is_blocked() (below) treats ANY
    pending decision as an opaque block, and until now nothing in this file
    ever read decision_manager.options/called .choose() - so whenever one of
    these opened for Player 2 specifically, "A" did nothing at all: not
    blocked-and-waiting, just silently unable to ever resolve it, since
    there was no code path that could. The human had to manually click
    through Player 2's own decision every single time.

    Mirrors _choose()'s own options format (a list with one dict per
    alternative) purely for that reuse - decision_manager.choose(index) is
    the same call main.py's DecisionOverlay click handler already makes for
    a human, so this doesn't duplicate or bypass any resolution logic, it
    just lets the AI reach the same button.

    A decision belonging to the OTHER (human) player is deliberately left
    completely untouched (returns False) - _is_blocked() then still gates
    everything else on it, exactly as before, and the human resolves it via
    the normal DecisionOverlay click, unchanged."""
    if not decision_manager.is_pending or decision_manager.player != player:
        return False
    options = [
        {"type": "decision_option", "index": i, "description": opt["label"]}
        for i, opt in enumerate(decision_manager.options)
    ]
    chosen = _choose(agent, state.tokens, turn_tracker, options, player, on_thinking)
    decision_manager.choose(chosen["index"])
    return True


def _maybe_resolve_rapid_ingress_placement(setup_controller, ingress_controller, rapid_ingress_controller, player, all_tokens, objectives=()):
    """Rule 15.07 (Rapid Ingress): real gap found via user report ("ich
    musste jetzt wieder für die KI die Modelle platzieren bei Rapid
    Ingress. sie muss selbst ihre Modelle platzieren."). Accepting the
    reactive offer (already resolved generically by _maybe_resolve_
    decision() above, since it's just another DecisionManager break
    point) only spends the CP and records rapid_ingress_controller.
    pending_squad (game/rapid_ingress.py's _resolve()) - the actual
    Ingress move (rule 20.04) still needs an (x, y) drop point, which a
    human supplies by dragging the Reserves-panel card onto the board
    (main.py's dragging_reserve_squad flow). Nothing on the AI side ever
    performed that follow-up placement - the module's own docstring had
    already flagged this as a "known limitation", written back when the
    accept/decline choice itself was still unreachable for the AI in the
    first place (before _maybe_resolve_decision() existed); making that
    first half reachable is precisely what uncovered this second, then-
    purely-theoretical half.

    Checked independently of whose phase it nominally is - Rapid Ingress
    fires at the END of the opponent's Movement phase, so by the time
    this runs, turn_tracker.active_player has often already moved on to
    that opponent's later phases. take_one_action() checks this BEFORE
    _is_blocked()'s active-player gate, same as _maybe_resolve_decision()/
    _maybe_command_reroll() - otherwise a pending placement belonging to
    `player` would sit there, silently unreachable, for the rest of the
    opponent's turn.

    Reuses _auto_ingress_squad()'s landing search unchanged - the exact
    same IngressController.start_ingress()/confirm_ingress() plumbing a
    normal Ingress move already uses, since rule 15.07's EFFECT literally
    is "that unit makes an ingress move" - no separate placement rule to
    reimplement. Sets ingress_controller.homing_beacon_bearer first,
    mirroring main.py's human drag-start exactly (IngressController.
    homing_beacon_bearer's docstring), so the Homing Beacon (user-supplied
    wargear item)'s alternate 3"/9" placement rule applies whenever this
    particular pending squad was picked via its free use. Consumes the
    reactive window (rapid_ingress_controller.consume()) once done, win or
    lose - same "one attempt, then it's closed" semantics as a human's
    single drag-and-drop (rule 15.07's window doesn't reopen just because
    the first attempt failed to find a legal spot).

    Returns True if there was a pending placement for `player` to make
    (regardless of whether it actually landed - either way, this call's
    one action is spent); False if nothing was pending."""
    squad = rapid_ingress_controller.pending_squad
    if squad is None or squad.owner != player:
        return False
    ingress_controller.homing_beacon_bearer = rapid_ingress_controller.pending_homing_beacon_bearer
    _auto_ingress_squad(setup_controller, ingress_controller, squad, all_tokens, objectives=objectives)
    rapid_ingress_controller.consume(squad)
    return True


def _maybe_resolve_fire_overwatch(agent, memory, fire_overwatch_controller, turn_tracker, all_tokens, player, on_thinking):
    """Rule 15.08 (Fire Overwatch): redesigned (user report - the old
    DecisionManager text-button list gave no way to tell "Strike Team 1"
    from "Strike Team 2" on the board) into FireOverwatchController's own
    CHOOSING_UNIT state, the same board-click-a-unit shape every other
    target picker in this file already uses - see game/overwatch.py's
    docstring. _maybe_resolve_decision() (generic DecisionManager
    resolution, above) no longer covers this at all now that it isn't a
    DecisionManager break point, so this is its direct replacement -
    checked at the same priority (before _is_blocked()'s generic turn_owner
    gate), since this can legitimately be open for `player` at the end of
    the OPPONENT's own Movement phase, well outside `player`'s nominal
    turn.

    A decision belonging to the OTHER (human) player is left completely
    untouched (returns False) - _is_blocked() then blocks everything else
    on it, same as before, and the human resolves it via the new left-
    panel Decline button / a board click, unchanged."""
    if fire_overwatch_controller is None or fire_overwatch_controller.state != overwatch_module.CHOOSING_UNIT:
        return False
    if fire_overwatch_controller.player != player:
        return False
    eligible = sorted(fire_overwatch_controller.eligible_squads(), key=lambda s: s.name)
    options = [
        {"type": "fire_overwatch", "squad": s.name, "description": f"Fire Overwatch: shoot with {s.name} (1 CP)"}
        for s in eligible
    ]
    options.append({"type": "decline_fire_overwatch", "description": "Fire Overwatch: decline"})
    chosen = _choose(agent, all_tokens, turn_tracker, options, player, on_thinking)
    if chosen["type"] == "decline_fire_overwatch":
        fire_overwatch_controller.decline()
    else:
        squad = _squad_by_name(chosen["squad"], all_tokens)
        fire_overwatch_controller.choose_unit(squad)
    return True


def _foreign_activation_in_progress(shooting_controller, charge_controller, player):
    """Real bug, found via user report: a reactive stratagem (Fire Overwatch/
    Rapid Ingress's Snap Shooting, rule 15.08/15.09; Heroic Intervention's
    reactive charge, rule 15.11) starts mid-flight during what turn_tracker
    still calls the OTHER player's own phase/turn - e.g. accepting Fire
    Overwatch at the end of Player 2's Movement phase kicks off a Snap
    Shooting activation for one of PLAYER 1's squads via shooting_controller,
    but turn_tracker.active_player/phase are still "Player 2's Shooting
    phase" at that exact instant (nothing about a reactive offer touches
    them - only an actual dice roll later does, via set_active()). With
    ai_auto_play on, take_one_action(player="Player 2") saw an unblocked
    "Player 2's own Shooting phase" and went ahead and used Explosives with
    one of Player 2's OWN squads on the very same shooting_controller
    instance WHILE Player 1's reactive shot was still mid target-choice -
    clobbering that in-progress activation's state (active_squad/state/
    remaining_weapon_types etc. all got overwritten out from under it).
    User's own diagnosis matched exactly: "it needs some kind of queue to
    avoid overlaps." The turn_tracker.active_player check `_is_blocked()`
    already does isn't enough - it only catches "not this player's turn AT
    ALL", not "a shared controller is already mid-activation for a squad
    that belongs to someone else". charge_controller checked too, since
    Heroic Intervention (15.11) is the exact same shape of bug (a reactive
    charge for the OTHER player, started mid the charging player's own
    Charge phase) - fight_controller isn't, since its FIGHTS_FIRST/REMAINING
    alternation already gates on ownership itself (whose_turn), unlike
    these two single-"active squad" controllers."""
    if shooting_controller is not None and shooting_controller.active_squad is not None:
        if shooting_controller.active_squad.owner != player:
            return True
    if charge_controller is not None and charge_controller.active_squad is not None:
        if charge_controller.active_squad.owner != player:
            return True
    return False


def _coherency_removal_cost(squad, model):
    """Sort key for "which model do we give up" - lowest is removed first.

    Characters (19.01 leader/support components) last, the datasheet's own
    sergeant/leader model next-to-last, then the fewest wounds, then the id so
    the pick is deterministic and a test can pin it."""
    leaders = {id(m) for m in attached_units.leader_models(squad, alive_only=False)}
    is_character = id(model) in leaders
    is_sergeant = bool(model.profile is not None and model.profile.squad_leader)
    wounds = model.profile.wounds if model.profile is not None else 1
    return (is_character, is_sergeant, wounds, model.id)


def _coherency_removal_pick(squad):
    """Which model this unit gives up when rule 09.02's Regaining Coherency
    forces a removal at the end of the turn, or None if there is nothing to
    pick from.

    Two different violations, two different answers:

      * split into several groups - remove from anywhere OUTSIDE the largest
        group. Keeping the body of the unit and giving up the stragglers is
        both the fewest models lost and what a player does by hand. All of the
        stragglers are candidates together, not just the smallest group: with
        two singletons broken off, both are going to have to go, and taking
        them cheapest-first is what decides which one is still standing if
        something (a Feel No Pain-style reprieve, a later rules change) cuts
        the removals short.
      * one group, but wider than the 9" spread limit - remove one END of the
        widest pair, since only those two models can actually reduce it.

    Within whichever set that leaves, the cheapest model goes (see
    _coherency_removal_cost): the characters are the reason the unit is worth
    anything, and they are exactly what was being lost before - reported case
    logs/game_20260816_210737.log line 1596-1598, where Boyz + Warboss split
    4+1+1 at the end of the turn and the two models destroyed were the Boss
    Nob and the Warboss."""
    if len(squad.models) < 2:
        return None
    groups = connected_groups(squad.models)
    if len(groups) > 1:
        body = max(groups, key=len)
        candidates = [mo for group in groups if group is not body for mo in group]
    else:
        widest = max(
            ((edge_distance(a, b), a, b)
             for i, a in enumerate(squad.models)
             for b in squad.models[i + 1:]),
            key=lambda item: item[0],
        )
        candidates = [widest[1], widest[2]]
    return min(candidates, key=lambda m: _coherency_removal_cost(squad, m))


def _maybe_resolve_coherency_removal(coherency_enforcer, player, game_log=None):
    """Rule 09.02's Regaining Coherency is "the controlling player's choice,
    one model at a time" - and until now the AI made no choice at all.

    game/coherency.py's CoherencyEnforcer sets pending_squad and main.py waits
    for a click on the board; _is_blocked() below stops the AI dead while that
    is pending, so the only thing that could ever answer it was a HUMAN
    clicking - including for Player 2's own units. That is a rules problem
    before it is a UX one (the choice belongs to the unit's owner), and the
    reported case shows what it costs in practice: in
    logs/game_20260816_210737.log the AI lost Boss Nob + Warboss off one unit
    and three of four surviving Meganobz off another, all picked by the
    opposing player.

    Deterministic and API-call-free - see _coherency_removal_pick() for the
    choice itself. Returns True if a model was removed (one per call, matching
    the enforcer's own one-at-a-time contract)."""
    if coherency_enforcer is None:
        return False
    squad = coherency_enforcer.pending_squad
    if squad is None or squad.owner != player:
        return False
    model = _coherency_removal_pick(squad)
    if model is None:
        return False
    if game_log is not None:
        detail = coherency_report(squad)
        game_log.add(
            f"  [coherency] {player}: {squad.name} gives up {model.profile.name} to regain "
            f"coherency (rule 09.02) - {detail or 'no report'}",
            file_only=True,
        )
    coherency_enforcer.remove_model(model)
    return True


def _is_blocked(
    turn_tracker, decision_manager, dice_manager, coherency_enforcer, player,
    shooting_controller=None, charge_controller=None, rapid_ingress_controller=None, setup_controller=None,
    fire_overwatch_controller=None, movement_controller=None,
):
    """Real bug, found via user report: 'when I charge, the AI just sits
    there during Pile In and when striking back.' Command/Movement/
    Shooting/Charge are each wholly one player's own phase, so blocking
    `player` whenever it isn't their turn is correct there. But rule 12.04's
    Fight phase deliberately ALTERNATES between BOTH players regardless of
    whose turn it is - if Player 1 (the human) charges during their own
    turn, the resulting Fight phase still very much has real Pile In and
    strike-back decisions belonging to Player 2 (the AI). This blanket
    check used to block every one of those, silently, for the AI's whole
    side of the Fight phase - _handle_fight() already has its own correct
    ownership gating for every decision it makes (squad.owner == player for
    Pile In, fight_controller.whose_turn == player for the fight-selection
    alternation itself), so it doesn't need this generic check's help and
    shouldn't be blocked by it.

    Second real bug, found via user report: "ich habe dadurch versehentlich
    meine Charge-Phase übersprungen" - this used to compare against
    turn_tracker.active_player, not turn_owner. game/turn.py's TurnTracker
    documents the distinction itself: active_player is a transient "whose
    decision is this right now" flag, flipped constantly by things like a
    defending save roll (mid the ATTACKER's own Shooting phase) or a
    reactive Stratagem's decision window - nothing guarantees it's back to
    equal turn_owner by the time some LATER phase (e.g. the human's own
    Charge phase) rolls around, if whatever flipped it was the last thing
    to touch it. Whenever that left active_player == "Player 2" during what
    was actually still Player 1's own turn, this check (and, transitively,
    main.py's automatic phase-advance for the AI) incorrectly treated it as
    Player 2's turn to act - _handle_charge() found nothing for Player 2 to
    do (correctly - it wasn't their phase), and the resulting "nothing left
    to decide" then auto-advanced straight past Player 1's own Charge phase.
    turn_owner is only ever changed by TurnTracker.advance_phase() itself,
    so comparing against that instead is the stable, correct check for "is
    this fundamentally player's own turn" that Command/Movement/Shooting/
    Charge actually need.

    Third real bug, found via user report: "Rapid Ingress und Fire Overwatch
    überlappen sich noch teilweise und die KI macht einfach weiter." Once a
    Rapid Ingress accept is chosen, the reactive DecisionManager break point
    itself resolves immediately (that's just the CP spend + picking a
    squad) - but the squad still needs a drag-and-drop placement
    (rapid_ingress_controller.pending_squad), which take_one_action()
    already auto-resolves via _maybe_resolve_rapid_ingress_placement()
    whenever the pending squad is `player`'s own. If it belongs to the
    OTHER (human) player instead, though, nothing previously stopped THIS
    call from proceeding anyway - decision_manager.is_pending is already
    False by then, so the human's still-open Reserves-panel drag (and the
    Fire Overwatch offer deferred to fire once that drag either lands or
    the window expires - see game/rapid_ingress.py's _pick()) was
    completely invisible to this gate, and the AI just kept right on
    playing its own turn underneath it - "overlapping" instead of queuing
    behind it. A still-pending squad (regardless of whose - the call above
    already drained `player`'s own) means this reactive window isn't over
    yet, so it blocks here too, same as a pending DecisionManager choice.

    Fourth real bug, found via user report: "wenn ich rapid ingress
    verwende macht die ki mit ihren aktionen einfach weiter. die muesste
    warten bis ich den move confirmed habe." rapid_ingress_controller.
    pending_squad (the check just below) only covers the window BEFORE the
    reserves-panel card is dropped onto the board - main.py's own drop
    handler calls rapid_ingress_controller.consume() the INSTANT the card
    lands (deliberately, so the window counts as "used" whether or not the
    drop turns out to be legal - see rapid_ingress.py's own comment), which
    immediately clears pending_squad. But dropping the card only STARTS
    SetupController's placement flow (state == PLACING) - the human still
    has to drag the stacked models apart and click Confirm, exactly like
    any other Ingress/Disembark placement. Nothing here checked THAT still-
    open state at all, so the moment the card was dropped, this reactive
    window looked fully "closed" even though the human's own placement
    decision (which model goes where, Confirm vs. Cancel) was still very
    much in progress - and since Rapid Ingress fires during the OPPONENT's
    (here: the AI's own) Movement phase, turn_owner == player was already
    true, so nothing else blocked it either. Only blocks a placement that
    ISN'T `player`'s own (a normal human Ingress/Disembark during their OWN
    turn is already blocked by the turn_owner check below regardless - this
    matters specifically for the reactive case, where that check doesn't
    fire) - `player`'s OWN pending placement (e.g. _handle_movement()'s
    Disembark-resume, or _maybe_resolve_rapid_ingress_placement() above)
    stays unblocked, exactly what the owner comparison guarantees.

    Fifth: fire_overwatch_controller.state == CHOOSING_UNIT (rule 15.08,
    redesigned - see game/overwatch.py/_maybe_resolve_fire_overwatch()'s
    own docstrings) is no longer a DecisionManager break point, so
    decision_manager.is_pending no longer covers it at all - by the time
    execution reaches here, _maybe_resolve_fire_overwatch() above has
    already drained anything belonging to `player`, so a still-open
    CHOOSING_UNIT here can only be the OTHER (human) player's own pending
    choice - same "still-pending-window, regardless of whose - the call
    above already drained player's own" reasoning as rapid_ingress_
    controller.pending_squad just above.

    Sixth, found via user report and then REPORTED AGAIN, in the same words,
    for a second ability: "ki hat mich den fadeback move nicht ausfuehren
    lassen, sondern hat direkt weitergemacht", and later "ranger / gleiches
    problem, wie damals bei fade back. die ki laesst mich nicht bewegen und
    macht gleich weiter". The first fix looked at the open move but compared
    move_mode to the single string "battle_focus", so Rangers' Path of the
    Outcast - which is the same manoeuvre under its own mode name - walked
    straight back into it. The set of reactive modes therefore lives at
    MovementController.REACTIVE_MOVE_MODES, next to the one method they all
    come through, and this gate reads it.

    Battle Focus' reactive manoeuvres (Fade Back, Opportunity Seized - see
    game/battle_focus.py) and Rangers' Path of the Outcast (game/
    path_of_the_outcast.py) fire in the OPPONENT's turn: the DecisionManager
    break point that offers them resolves the instant "spend a token" is
    picked, but all that does is OPEN a Normal move (move_mode ==
    "battle_focus") that the human still has to drag and confirm. Exactly the
    same shape as the fourth case above - dropping a Rapid Ingress card
    closes its own window while leaving a placement in progress - and with
    exactly the same consequence: decision_manager.is_pending is already
    False, Fade Back fires during the AI's OWN Shooting phase so turn_owner
    == player is already true, and nothing else looked at the open move at
    all, so the AI simply carried on shooting with its next unit underneath
    it. Only blocks a move that is NOT `player`'s own, for the same reason
    the placement check above does: the AI's own granted move is driven by
    the AI itself and must not deadlock against this gate."""
    if decision_manager.is_pending or dice_manager.is_pending:
        return True
    if coherency_enforcer is not None and coherency_enforcer.pending_squad is not None:
        return True
    if rapid_ingress_controller is not None and rapid_ingress_controller.pending_squad is not None:
        return True
    if fire_overwatch_controller is not None and fire_overwatch_controller.state == overwatch_module.CHOOSING_UNIT:
        return True
    if (
        movement_controller is not None
        and movement_controller.move_mode in MovementController.REACTIVE_MOVE_MODES
    ):
        # A reactive move is open - see the sixth case above. Read off the set
        # rather than compared to one mode name: this gate said "battle_focus"
        # only, and Rangers' Path of the Outcast then reproduced the very bug
        # the sixth case was written to fix.
        reactive_squad = movement_controller.selected_squad
        if reactive_squad is not None and reactive_squad.owner != player:
            return True
    if (
        setup_controller is not None and setup_controller.state == PLACING
        and setup_controller.setting_up_squad is not None
        and setup_controller.setting_up_squad.owner != player
    ):
        return True
    if _foreign_activation_in_progress(shooting_controller, charge_controller, player):
        return True
    # Real, severe bug found via user report ("die KI verliert die
    # Kontrolle..."): a reactive activation belonging to `player` (e.g.
    # Fire Overwatch's Snap Shooting for the AI, rule 15.08/15.09, or a
    # Heroic Intervention charge for the AI, rule 15.11) can legitimately
    # be sitting mid-CHOOSING_TARGET during the OTHER player's own phase -
    # _foreign_activation_in_progress() above only blocks the opposite case
    # (someone ELSE's activation), it never says "and unblock player's own
    # reactive one here too". Without this, the blanket
    # `turn_owner != player` check below fired anyway (Command/Movement/
    # Shooting/Charge are each nominally "wholly one player's turn"), and
    # _handle_shooting()/_handle_charge() never even got a chance to pick a
    # target for it - reproduced: the activation sat at CHOOSING_TARGET
    # forever, for the rest of the game, since NOTHING else could ever
    # continue it either; the only way to unstick it was a human board
    # click on the highlighted target, exactly the reported symptom.
    if shooting_controller is not None and shooting_controller.active_squad is not None and shooting_controller.active_squad.owner == player:
        return False
    if charge_controller is not None and charge_controller.active_squad is not None and charge_controller.active_squad.owner == player:
        return False
    if turn_tracker.phase == PHASE_FIGHT:
        return False
    return turn_tracker.turn_owner != player


def _roll_has_a_failure(dice_manager):
    """A roll with zero failures can only get WORSE (or stay the same) from
    a re-roll, never better - so there's never a reason to even consider
    Command Re-roll on one. This is a plain fact, not a guessed heuristic:
    filters out the common case (a fine roll) without ever skipping a roll
    that's actually worth reconsidering."""
    threshold = dice_manager.success_threshold
    if threshold is None:
        return True  # no pass/fail concept for this roll (e.g. plain damage count) - don't filter it out
    return any(v < threshold for v in dice_manager.pending_values)


# A charge roll is 2D6, so 12 is the best a re-roll could possibly come out
# as - if even that reaches nothing, the re-roll cannot rescue this charge and
# the CP is better kept.
MAX_CHARGE_ROLL = 12

# How much of an enemy unit this unit has to expect to destroy in melee before
# a failed charge is worth 1 CP to re-roll (observation.expected_kills()'s
# fraction_of_unit, melee=True, taken against the best unit it could reach).
#
# Measured across every datasheet in this project rather than guessed, against
# a soft target (Strike Team, T3): the real melee units land at 0.40-1.00
# (Boyz 1.00, Deff Dread 0.56, Warboss 0.46, Tankbustas 0.45, Stormboyz 0.44,
# Kroot 0.44, Meganobz 0.42, Deffkoptas 0.40) and everything else at 0.13 or
# below (Warbikers 0.13, Gretchin 0.12, Stealth 0.11, Crisis 0.10, Strike/
# Breacher/Ghostkeel 0.08, Trukk 0.06, Devilfish 0.04). 0.25 sits in the
# middle of that gap, so the threshold does not balance on any one datasheet -
# and the user's own example is at the extreme end of it: a Trukk (0.06) never
# qualifies, the Boyz it is carrying (1.00) always do.
MIN_CHARGE_REROLL_MELEE_FRACTION = 0.25

# How far the nearest reachable enemy may be before a failed charge is no
# longer worth 1 CP to re-roll (user: "und gegner nicht mehr als 7 zoll
# entfernt sind"). Unit-to-unit, edge to edge - Squad.min_distance_to(), the
# same measurement rule 11.02/11.04 uses.
#
# The rule is a good one, and the arithmetic says why: rule 11.04 needs the
# 2D6 to cover the WHOLE gap, and 2D6 makes 7+ 58% of the time, 8+ 42%, 9+
# 28%. So 7" is the last distance at which a re-roll is better than even
# money; past it the CP is buying a coin-flip that is already losing.
#
# Taken literally as a DISTANCE, not as an effective one: with War Horde's
# 'Ere We Go up (+2 to Charge rolls, see game/ere_we_go.py) a 7" gap only
# needs a 5+, i.e. 83%. That makes a "yes" here better than the number above,
# never worse - the gate can only ever be too cautious, which is the safe
# direction for something that spends CP on its own.
MAX_CHARGE_REROLL_GAP_IN = 7.0


def _best_melee_prospect(squad, target_squads):
    """The most of any one enemy unit `squad` can expect to destroy in a round
    of fighting (observation.expected_kills(melee=True)), plus that unit, or
    (0.0, None) if there is nothing to judge. Approximate for the same
    documented reasons expected_kills() itself is."""
    best_fraction, best_target = 0.0, None
    for target in target_squads:
        estimate = observation.expected_kills(squad, target, melee=True)
        if estimate is None:
            continue
        if estimate["fraction_of_unit"] > best_fraction:
            best_fraction, best_target = estimate["fraction_of_unit"], target
    return best_fraction, best_target


def _charge_reroll_verdict(charge_controller, dice_manager, player):
    """User rule, given in two parts. First: "kannst du der ki mitgeben, dass
    sie immer bei charges, die verfehlt sind einen command reroll macht? aber
    nur, wenn es auch gute nahkampf erfolgsaussichten gibt. zb nicht mit einem
    transporter." Then, later: "und zwar bei der ersten gelegenheit für
    nahkampfeinheiten, die nach ihren charge roll nichts erreichen können. und
    gegner nicht mehr als 7 zoll entfernt sind."

    So three conditions, all of which have to hold: the roll reached NOTHING,
    the unit is a real melee unit (MIN_CHARGE_REROLL_MELEE_FRACTION - that is
    what "zb nicht mit einem transporter" defines), and the nearest reachable
    enemy is within MAX_CHARGE_REROLL_GAP_IN. "At the first opportunity" needs
    no code of its own: rule 15.02's window is "just after making the charge
    roll", which is exactly when this is asked, and every branch below answers
    immediately rather than deferring.

    Returns (should_reroll, reason) for a PENDING charge roll, or None when
    this isn't a call to make here (no charge in progress, not this player's
    unit, or the roll didn't fail) - in which case _maybe_command_reroll()
    falls back to asking the agent, exactly as before.

    Decided in the engine rather than taught to the model as a prompt line,
    for the reason this project has now hit repeatedly: a tactic expressed as
    a rule the engine applies is followed every time, the same tactic as prose
    stays optional. It is also arithmetic the model would otherwise have to do
    from raw coordinates - "did 7" reach that unit" and "would my melee
    weapons actually hurt it" - which is exactly the kind of derivation that
    has gone wrong before (the wound-threshold and charge-odds hints exist
    because of it). Both answers come from the engine's own predicates:
    ChargeController.targets_reachable_with() is the real rule 11.04 gate, and
    observation.expected_kills() is the same estimate the threat/trade numbers
    already use.

    Deterministic in BOTH directions on purpose, so a hopeless charge costs no
    API call either. A charge roll that DID reach something is left to the
    agent as before: re-rolling a charge is all-or-nothing (15.02: "must be
    re-rolled in full"), so trading a hit for a better one is a genuine
    judgement call, not a rule."""
    if charge_controller is None or dice_manager is None:
        return None
    squad = charge_controller.active_squad
    if squad is None or squad.owner != player or not dice_manager.pending_values:
        return None

    rolled = sum(dice_manager.pending_values)
    if charge_controller.targets_reachable_with(rolled):
        return None  # this charge reached something - whether to gamble it is a real decision

    could_reach = charge_controller.targets_reachable_with(MAX_CHARGE_ROLL)
    if not could_reach:
        return False, f'no unit is within reach even on a {MAX_CHARGE_ROLL}" charge roll'

    reached = f'{rolled}" reached nothing'
    # Second half of the user's rule, added after the melee-quality half:
    # "und gegner nicht mehr als 7 zoll entfernt sind". Measured to the
    # NEAREST unit the re-roll could actually reach, since that is the one the
    # re-rolled charge would be declared against.
    gap = min(squad.min_distance_to(t) for t in could_reach)
    if gap > MAX_CHARGE_REROLL_GAP_IN:
        return False, (
            f'{reached}, and the nearest reachable enemy is {gap:.1f}" away '
            f'(further than {MAX_CHARGE_REROLL_GAP_IN:.0f}", so a re-roll is worse than even money)'
        )

    fraction, target = _best_melee_prospect(squad, could_reach)
    if fraction < MIN_CHARGE_REROLL_MELEE_FRACTION:
        if target is None:
            return False, f"{reached}, and it has no melee attack worth a CP"
        return False, f"{reached}, but it is weak in melee - it would only destroy {fraction:.0%} of {target.name}"
    return True, (
        f'{reached}, the nearest reachable enemy is {gap:.1f}" away, and it would destroy '
        f"{fraction:.0%} of {target.name} in melee"
    )


def _maybe_command_reroll(agent, memory, command_reroll_controller, turn_tracker, state, player, on_thinking,
                          charge_controller=None, game_log=None):
    """Rule 15.02 (Command Re-roll, Core Stratagem, 1CP): a real decision to
    make about the CURRENTLY PENDING roll, before it's acknowledged - has to
    run before the generic dice-pending block, not after.
    CommandRerollController.can_use() checks ownership via
    turn_tracker.active_player, which the engine itself flips to the
    DEFENDING player during a save roll - so for rolls that actually belong
    to `player` (its own attack rolls, or save rolls against its own
    models), this naturally offers the choice to `player`, with no extra
    bookkeeping needed here. But can_use() has no idea WHO is asking - it
    just answers "can whoever active_player currently is use this
    Stratagem", so without the explicit turn_tracker.active_player ==
    player check below, take_one_action() (always called with
    player="Player 2") would ask the AI to decide about a roll that isn't
    even its own - e.g. Player 1's own Advance roll, where active_player
    correctly stays Player 1 the whole time (an Advance only ever involves
    the mover's own unit, nothing flips it). Real user report: "Claude hat
    gerade bei meinem advance wurf überlegt, ob er einen command reroll
    machen will" - confirmed exactly this: the AI got asked about (and, had
    it said yes, would have spent Player 1's CP to reroll) the human's own
    roll, a decision that should stay entirely with the human (who already
    has their own "Command Re-roll (1CP)" button for it, see
    ActionPanel._draw_command_reroll()).
    Returns True if it made a decision (that's this call's one action).

    Real bug found via an earlier user report ("nothing happens until I
    click, and then it takes a few seconds"): declining ("keep_roll")
    doesn't call command_reroll_controller.start(), so nothing marks the
    stratagem as used - can_use() stays True for the exact same still-
    pending roll on EVERY subsequent frame. With ai_auto_play on, that
    meant re-asking Claude the identical question every single frame (a
    fresh multi-second API call each time) until either Claude randomly
    said yes or a human click happened to land between two calls - the
    delay the user was seeing was the tail of an already-running chain of
    repeated calls, not something their click caused. memory.
    last_asked_reroll_id (keyed by id() of the pending roll's own value
    list - stable for that roll's whole lifetime, including through an
    accepted reroll's in-place mutation, and naturally distinct once a new
    roll replaces it) makes this a genuine "ask once per roll" decision,
    same as declined_shoot/declined_charge/declined_explosives are for
    their own decision points.

    A FAILED charge roll skips the agent entirely and is settled by
    _charge_reroll_verdict() - see its own docstring for the user rule behind
    that and why it belongs in the engine."""
    if command_reroll_controller is None or not command_reroll_controller.can_use():
        return False
    if turn_tracker.active_player != player:
        return False  # this roll isn't player's to reroll - leave it to the human's own UI
    dice_manager = command_reroll_controller.dice_manager
    roll_id = id(dice_manager.pending_values)
    if roll_id == memory.last_asked_reroll_id:
        return False
    if dice_manager.roll_kind != CHARGE_ROLL and not _roll_has_a_failure(dice_manager):
        return False  # a clean roll is never worth spending a CP to reconsider

    memory.last_asked_reroll_id = roll_id
    verdict = None
    if dice_manager.roll_kind == CHARGE_ROLL:
        verdict = _charge_reroll_verdict(charge_controller, dice_manager, player)
    if verdict is not None:
        should_reroll, reason = verdict
        if game_log is not None:
            squad_name = charge_controller.active_squad.name
            what = "re-rolls the failed charge" if should_reroll else "keeps the failed charge roll"
            game_log.add(f"[charge reroll] {squad_name} {what} - {reason}.", file_only=True)
        if not should_reroll:
            return True
    else:
        options = [
            {"type": "keep_roll", "description": f"Keep this roll ({dice_manager.pending_values})"},
            {"type": "command_reroll", "description": f"Command Re-roll (1CP): re-roll this {dice_manager.roll_kind} roll"},
        ]
        chosen = _choose(agent, state.tokens, turn_tracker, options, player, on_thinking)
        if chosen["type"] != "command_reroll":
            return True

    command_reroll_controller.start()
    if command_reroll_controller.selecting_die:
        # Re-roll the worst (lowest) die - the clearly dominant choice, not
        # a real second decision, so no extra agent.decide() call.
        worst_index = min(
            range(len(dice_manager.pending_values)),
            key=lambda i: dice_manager.pending_values[i],
        )
        command_reroll_controller.choose_die(worst_index)
    return True


def _choose(agent, all_tokens, turn_tracker, options, player, on_thinking=None, objectives=(), plan_context=None):
    """0 real alternatives -> caller shouldn't have offered a choice at all;
    1 -> take it, no API call; 2+ -> ask the agent. on_thinking(), if given,
    fires right before the (possibly slow, network-bound) agent.decide() call
    - main.py uses it to flash a "Claude is thinking..." overlay so a Haiku
    round-trip taking a couple of seconds doesn't look like a frozen window.

    `objectives` (mission objectives, see game/objectives.py) is only ever
    passed with real data by _handle_movement()'s own _choose() call -
    objective-seeking is fundamentally a movement decision, so every other
    call site (shooting/charge/fight/battle-shock/etc.) is left alone,
    defaulting to an empty tuple (build_observation() already treats that
    the same as "no objectives to show").

    `plan_context` (the strategic planning phase's result for THIS squad,
    see _maybe_generate_turn_plan()/AIMemory.turn_plan) is, for the same
    reason, only ever passed with real data by _handle_movement()'s own
    call - every other call site defaults to None, so build_observation()
    simply omits the "turn_plan" key for them."""
    if len(options) == 1:
        return options[0]
    if on_thinking is not None:
        on_thinking()
    observation = build_observation(
        _all_squads(all_tokens), turn_tracker, options, player, objectives=objectives, plan_context=plan_context,
    )
    index = connection.ask(agent.decide, observation)
    if not isinstance(index, int) or not (0 <= index < len(options)):
        index = 0
    return options[index]


def take_one_action(*args, **kwargs):
    """One AI action, or nothing at all if the agent has gone offline.

    THE ONE PLACE an unreachable agent stops the AI instead of the game.
    User: "momentan stürzt das Spiel ab, wenn KI Modus an ist und die
    Verbindung verloren geht oder api Fehler oder Guthaben leer. besser wäre
    eine Meldung 'Connection lost' und das Spiel geht aber ohne KI weiter."

    Only ai.connection.AIUnavailable is caught - never a bare Exception. That
    type is raised by exactly one thing (the guarded API call in
    ai/claude_agent.py), so a genuine bug in a handler still crashes loudly
    rather than being turned into a silently skipped turn, which would be far
    harder to notice than a traceback.

    ABORTING MID-ACTION IS ACCEPTABLE HERE, and worth naming: the agent may
    have gone offline after a move was begun or a prompt opened. Whatever is
    half-done stays on screen, and the human - who is now playing both sides -
    can confirm or cancel it like any other open decision. The alternative
    (unwinding the engine) would be a second, much larger notion of "undo"
    for a case that ends the AI's involvement anyway.

    A no-op once offline, so the loop stops paying a failed round-trip per
    frame: is_online() is checked BEFORE the call, not only after it."""
    if not connection.is_online():
        return None
    try:
        return _take_one_action(*args, **kwargs)
    except connection.AIUnavailable:
        return None


def _take_one_action(
    agent, memory, state, turn_tracker, movement_controller, shooting_controller,
    charge_controller, fight_controller, battle_shock_controller, pile_in_controller,
    decision_manager, dice_manager, game_log, coherency_enforcer=None, player="Player 2",
    mission_controller=None,
    on_thinking=None, advance_phase_fn=None, command_reroll_controller=None,
    explosives_controller=None, insane_bravery_controller=None,
    transport_controller=None, setup_controller=None, ingress_controller=None,
    rapid_ingress_controller=None, greater_good_controller=None, fall_back_controller=None,
    crushing_impact_controller=None, deadly_demise_controller=None, consolidate_controller=None,
    fire_overwatch_controller=None, waaagh_controller=None, arrokon_controller=None,
    unbridled_carnage_controller=None, ere_we_go_controller=None,
    retro_thrusters_controller=None,
    # Awakened Dynasty's three PROACTIVE protocols. The reactive three need
    # nothing here - they answer inside their own controllers via auto_players.
    hungry_void_controller=None, conquering_tyrant_controller=None,
    sudden_storm_controller=None,
    # Death Lord's Chosen's detachment rule Deadly Vectors needs NO handler -
    # it is not optional, asks nothing and rolls itself from main.py. It is
    # here for one reason: its mortal wounds land on the OPPONENT, so when the
    # AI is the victim its own allocation choice has to be resolvable, and
    # _resolve_own_damage_choice() is the only thing that ever does that for
    # Player 2's models. Without it, main.py's is_blocked() gate would hold on
    # a pending_damage_choice nobody could answer - a real deadlock, the same
    # one deadly_demise_controller was added to that list to prevent.
    deadly_vectors_controller=None,
    # Death Lord's Chosen. Only Grim Reapers gets a handler: the other two the
    # AI uses (Undying Spite, Sickening Impact) are REACTIVE and answer inside
    # their own controllers via auto_players, and the remaining three are
    # irrelevant to the AI by user instruction.
    grim_reapers_controller=None,
):
    """Resolve exactly ONE pending decision for `player` (Player 2 by
    default) and return - this is the function main.py's "A" key calls. A
    no-op if it isn't currently player's turn, or a human decision (dice
    ack, damage allocation, decision prompt, coherency removal) is pending
    elsewhere.

    Deliberately does NOT auto-resolve dice: it kicks off at most one roll
    (e.g. a hit roll after choosing a shooting target/weapon) and then
    returns immediately, leaving dice_manager.is_pending true - the EXACT
    same DicePanel + click-to-acknowledge flow a human's own action already
    goes through (main.py's event loop already calls every controller's
    on_dice_acknowledged() on that click) takes over from there, chaining
    through wound/save/damage rolls one visible step at a time. This is also
    why a save roll against one of Player 1's own squads is properly shown
    to, and clicked through by, the human - turn_tracker.set_active() already
    flips to the defending player for exactly that roll, unchanged from the
    human-vs-human path. See CLAUDE.md for the full phase-by-phase design.

    Charge is the one phase where a real further decision (which reachable
    enemy to charge) can only be made AFTER seeing the roll - _handle_charge()
    is written to resume that second half on a LATER take_one_action() call,
    once the human has clicked to acknowledge the charge roll in between.

    If advance_phase_fn is given (a callable mirroring main.py's own "Next
    Phase" click, including its coherency/battle-shock gating - see
    ai_advance_phase() in main.py) and this call finds NOTHING left for
    `player` to decide in the current phase, it's invoked automatically -
    "remain stationary for every squad" is a deliberate choice, not an
    absence of one, so the AI should be the one to decide the phase is over,
    not require a human to do it on its behalf. The Fight phase is the one
    exception: advancing out of it only happens once fight_controller.state
    is DONE (both players have nothing left), since it's shared between
    both players, not just `player`'s own phase.

    User clarification after an earlier (too broad) attempt at this: "die
    AI darf natürlich selbstständig in die nächste Phase springen. aber in
    meinem Zug soll die Phase nicht automatisch weiterspringen... ich habe
    dadurch versehentlich meine Charge-Phase übersprungen." - this auto-
    advance is only ever supposed to fire once it's genuinely `player`'s own
    turn to begin with, which is exactly what _is_blocked()'s turn_owner
    check (not the old, buggy active_player one - see its own docstring)
    now guarantees: reaching the code below at all already means
    turn_tracker.turn_owner == player (or it's the shared Fight phase, gated
    separately). Before that fix, a stale active_player left over from an
    earlier defending save roll or reactive Stratagem decision could make
    this fire during the HUMAN's own turn - finding nothing for Player 2 to
    do there (correctly, since it wasn't their phase) and then auto-
    advancing straight past whatever phase the human was still using.

    A pending damage-allocation choice for one of `player`'s OWN squads is
    resolved right away (see _resolve_own_damage_choice()) - one of Player
    1's own choices to make (the human clicks it as always) still blocks
    everything else, exactly as before.

    Likewise, a pending game.decision.DecisionManager break point (see
    _maybe_resolve_decision()) is resolved immediately whenever it belongs
    to `player` - e.g. Fire Overwatch/Rapid Ingress reactively offered to
    `player` at the end of the opponent's Movement phase, or a [LETHAL
    HITS]/[PRECISION]/[TWIN-LINKED] choice mid-attack. Before this existed,
    _is_blocked() (further down) treated EVERY pending decision as an opaque
    block regardless of whose it was, and nothing else in this file ever
    called decision_manager.choose() - so a decision offered to `player`
    just sat there forever no matter how many times "A" was pressed, since
    there was no code path that could ever resolve it, forcing the human to
    click through it on `player`'s behalf every time. A decision belonging
    to the human is still left untouched, same as before.

    If accepting that Rapid Ingress offer left rapid_ingress_controller
    with a pending_squad belonging to `player`, _maybe_resolve_rapid_
    ingress_placement() immediately places it too (reusing the same
    landing search as a normal Ingress move) - resolving the accept/
    decline choice above uncovered this as a SECOND, previously purely
    theoretical gap: nothing ever performed the follow-up placement a
    human supplies by dragging the Reserves-panel card, so the squad sat
    in reserves indefinitely once `player` accepted its own offer.

    Stratagems (rule 15.01), where applicable to the current demo scene:
    Command Re-roll (15.02, _maybe_command_reroll()) is considered for
    EVERY pending re-rollable roll that belongs to `player` (including its
    own save rolls, per CommandRerollController.can_use()'s ownership
    check), before the roll is acknowledged. Insane Bravery (15.04) is
    considered inside _handle_battle_shock() before a mandatory roll.
    Explosives (15.05) is considered inside _handle_shooting(), as a
    separate decision from the normal shoot/hold-fire choice (it doesn't
    consume the unit's own shooting action).

    Transports (18.01-18.05): _handle_movement() offers each of `player`'s
    Transports' embarked passengers a "stay embarked or disembark" choice
    per squad (_handle_disembark_for_squad()) - but only once disembarking
    would actually leave something worth shooting/charging this turn
    (_has_target_after_disembark(), a user policy); otherwise it stays
    embarked automatically, no agent.decide() call spent. An Emergency
    Disembark (18.05) isn't a choice at all and doesn't come from that path:
    it is triggered by the TRANSPORT being destroyed, in whatever phase
    that happened, and is finished by _maybe_resume_disembark_placement()
    below - checked ahead of _is_blocked(), see its docstring. Either way
    the hazard roll (06.03) follows the placement, and its resulting wound
    allocation is handled by _resolve_own_damage_choice()
    (transport_controller is in its controller list, same as shooting/
    fight/explosives). Fight phase pile-ins
    (rule 12.03) are no longer always skipped - _handle_fight() now makes a
    real (small, geometry-only) pile-in move toward one already-engaged
    enemy for each of `player`'s eligible squads first (_pile_in_squad()).

    Crushing Impact (15.06, if crushing_impact_controller is given) is
    considered inside _handle_charge() for each of `player`'s own MONSTER/
    VEHICLE squads that already charged this phase, before any new charge
    is declared - see _handle_crushing_impact_for_squad(). Deadly Demise
    (24.08, if deadly_demise_controller is given) needs no dedicated
    handler at all - its own trigger/roll already run unconditionally from
    main.py's remove_dead_models() loop regardless of player; the only AI
    gap was its resulting pending_damage_choice, now resolved for `player`'s
    own squads simply by adding it to _resolve_own_damage_choice()'s
    controller list below, exactly like shooting/fight/explosives already
    are. Consolidate (12.07/12.08, if consolidate_controller is given) is
    considered inside _handle_fight() for each of `player`'s own squads
    that have already fought - see _consolidate_squad(); Ongoing/Objective
    apply automatically (no real choice), Engaging is the one genuine
    trade-off (pulling a nearby enemy into combat forces it to fight this
    same Fight step immediately) and is the only one that asks.

    Two user-requested tactical policies, both handled inside
    _handle_movement(): Strategic Reserves (rule 20.04, if ingress_controller
    is given) are auto-deployed the moment they're legally eligible, landing
    as close to the front as a bounded search finds legal
    (_auto_ingress_squad()) - "deploy reserves as early as possible" is a
    deterministic policy, not a judgment call, so this never asks the agent.
    Staging is a real third movement option offered alongside "remain
    stationary"/"move toward the nearest enemy" - a line-of-sight-based
    search (_best_staging_point()) for a reachable spot behind Dense terrain
    that's seen by fewer enemy squads than the squad's current position;
    Claude decides whether it's worth taking, guided by
    ai/claude_agent.py's SYSTEM_PROMPT.

    Rule 09.06 (Advance) is offered as its own move-type option, alongside
    the plain "move toward the nearest enemy" - MovementController.
    start_run() itself is what rolls the D6 and adds it to the squad's
    remaining_range; the actual trade-off (extra reach now vs. losing this
    turn's own non-Assault shooting/charge eligibility) is a fixed, already-
    known rule consequence of the choice, not something that depends on
    seeing any future decision - so it's simply spelled out in the option's
    own description text, and Claude weighs it with the SYSTEM_PROMPT's
    guidance exactly like Fall Back's trade-off already is."""
    controllers = [
        shooting_controller, charge_controller, fight_controller, battle_shock_controller,
        explosives_controller, transport_controller, fall_back_controller,
        crushing_impact_controller, deadly_demise_controller,
        deadly_vectors_controller,
    ]
    controllers = [c for c in controllers if c is not None]

    damage_result = _resolve_own_damage_choice(player, controllers)
    if damage_result is not False:
        return  # either resolved one of player's own choices, or it's the human's to make

    if _maybe_resolve_decision(agent, decision_manager, turn_tracker, state, player, on_thinking):
        return

    if rapid_ingress_controller is not None and setup_controller is not None and ingress_controller is not None:
        if _maybe_resolve_rapid_ingress_placement(
            setup_controller, ingress_controller, rapid_ingress_controller, player, state.tokens,
            objectives=state.objectives,
        ):
            return

    # Rule 18.05 (Emergency Disembark): triggered by the TRANSPORT being
    # destroyed, so it fires in whatever phase and whoever's turn that
    # happened in - checked here, ahead of _is_blocked() and the phase
    # dispatch, for the same reason as the two resumes around it. See
    # _maybe_resume_disembark_placement()'s own docstring for the reported
    # hang this closes.
    if _maybe_resume_disembark_placement(
        transport_controller, setup_controller, player, state.tokens, game_log=game_log,
    ):
        return

    # Rule 09.02's Regaining Coherency, for `player`'s OWN units - ahead of
    # _is_blocked(), which treats any pending removal as a hard stop and would
    # otherwise leave the AI waiting for the opposing human to choose which of
    # its models die. See _maybe_resolve_coherency_removal().
    if _maybe_resolve_coherency_removal(coherency_enforcer, player, game_log=game_log):
        return

    if _maybe_resolve_fire_overwatch(agent, memory, fire_overwatch_controller, turn_tracker, state.tokens, player, on_thinking):
        return

    if command_reroll_controller is not None and dice_manager.is_pending:
        if _maybe_command_reroll(
            agent, memory, command_reroll_controller, turn_tracker, state, player, on_thinking,
            charge_controller=charge_controller, game_log=game_log,
        ):
            return

    if _is_blocked(
        turn_tracker, decision_manager, dice_manager, coherency_enforcer, player,
        shooting_controller, charge_controller, rapid_ingress_controller, setup_controller,
        fire_overwatch_controller, movement_controller,
    ):
        return

    memory._sync(turn_tracker)
    # The plan is written once in Movement but read by every later phase, so
    # re-check it against the board each time the phase changes - free, no API
    # call. See _revalidate_plan_for_phase().
    _revalidate_plan_for_phase(memory, player, state, turn_tracker, game_log)
    _maybe_replan_after_events(memory, player, state, turn_tracker, game_log)
    all_tokens = state.tokens
    phase = turn_tracker.phase

    # Real, severe bug found via user report ("ki verliert die Kontrolle bei
    # charge move... das muss ich übernehmen"): a reactive charge (Heroic
    # Intervention, rule 15.11) declared for `player` during the OPPONENT's
    # own Charge phase rolls its 2D6 and waits for the human to acknowledge
    # it (charge_controller.active_squad set, max_distance still None) - by
    # the time that roll IS acknowledged, turn_tracker.phase has typically
    # already moved on to Fight (Heroic Intervention fires right as the
    # opponent's Charge phase ends). The phase dispatch below only ever
    # calls _handle_charge() while phase == PHASE_CHARGE, so without this,
    # NOTHING would ever call it again for the rest of the game once phase
    # changed - reproduced: charge_controller sat at DECLARING_TARGETS with
    # a real, resolvable roll (max_distance set, an actual target reachable)
    # for dozens of subsequent phases across multiple battle rounds, since
    # every one of them hit this same dead end; the only way to unstick it
    # was a human manually dragging the charge move to completion on the
    # board. Checked before the phase switch, exactly like
    # _is_blocked()'s analogous "player's own reactive activation" exception
    # above - the charge resume takes priority over whatever `phase`
    # nominally is right now.
    if (
        charge_controller.active_squad is not None and charge_controller.active_squad.owner == player
        and charge_controller.max_distance is not None
    ):
        acted = _handle_charge(
            agent, memory, player, all_tokens, charge_controller, movement_controller, on_thinking,
            crushing_impact_controller=crushing_impact_controller, plan=_current_unit_plans(memory),
            game_log=game_log,
        )
    elif phase == PHASE_COMMAND:
        acted = _maybe_call_waaagh(player, turn_tracker, waaagh_controller)
        if not acted:
            acted = _handle_battle_shock(agent, player, all_tokens, battle_shock_controller, insane_bravery_controller, turn_tracker, on_thinking)
    elif phase == PHASE_MOVEMENT:
        acted = _handle_movement(
            agent, memory, player, state, movement_controller, transport_controller, setup_controller,
            game_log, on_thinking, ingress_controller=ingress_controller, fall_back_controller=fall_back_controller,
            waaagh_controller=waaagh_controller, ere_we_go_controller=ere_we_go_controller,
            last_ranged_attack_turn=getattr(shooting_controller, "last_ranged_attack_turn", None),
            mission_controller=mission_controller,
            sudden_storm_controller=sudden_storm_controller,
            shooting_controller=shooting_controller,
        )
    elif phase == PHASE_SHOOTING:
        acted = _handle_shooting(
            agent, memory, player, all_tokens, shooting_controller, explosives_controller, on_thinking,
            greater_good_controller=greater_good_controller, plan=_current_unit_plans(memory),
            charge_controller=charge_controller, arrokon_controller=arrokon_controller,
            conquering_tyrant_controller=conquering_tyrant_controller, game_log=game_log,
        )
    elif phase == PHASE_CHARGE:
        acted = _handle_charge(
            agent, memory, player, all_tokens, charge_controller, movement_controller, on_thinking,
            crushing_impact_controller=crushing_impact_controller, plan=_current_unit_plans(memory),
            game_log=game_log,
        )
    elif phase == PHASE_FIGHT:
        acted = _handle_fight(
            agent, memory, player, all_tokens, fight_controller, pile_in_controller, movement_controller, on_thinking,
            consolidate_controller=consolidate_controller, game_log=game_log,
            unbridled_carnage_controller=unbridled_carnage_controller,
            hungry_void_controller=hungry_void_controller,
            grim_reapers_controller=grim_reapers_controller,
        )
    else:
        acted = False

    if acted or advance_phase_fn is None:
        return

    if phase == PHASE_FIGHT:
        # Real bug found via user report ("der end turn button wird jetzt
        # irgendwie immer überspringen"): _is_blocked() deliberately lets
        # execution reach here during the Fight phase regardless of whose
        # turn_owner it is (see its own comment - Fight alternates between
        # both players, so `player`'s own pile-in/strike-back decisions
        # must not be blocked just because it's nominally the OPPONENT's
        # turn). But Fight is also always the LAST phase (rule 07.02) - so
        # advance_phase_fn() here doesn't just end the Fight phase, it ends
        # turn_owner's WHOLE TURN. Without this turn_owner check, the
        # instant fight_controller reached DONE (nothing left for EITHER
        # side to fight - the common case when nobody's engaged yet) during
        # the HUMAN's (Player 1's) own turn, ai_auto_play calling this every
        # frame would end Player 1's turn on its own, the moment it became
        # true - the human's own "Next Phase"/"End Turn" click never got a
        # chance to matter, exactly the reported symptom. Reproduced from a
        # real game log: "Player 1: Fight phase begins." immediately
        # followed by "Player 1's turn ends." with zero fight activity in
        # between, right after auto-play had been turned on earlier in that
        # same turn. `player` is always "Player 2" here, so this only ever
        # auto-ends Player 2's OWN turn - Player 1 keeps having to click
        # their own End Turn, even when their Fight phase has nothing left
        # to do, same as every other phase already requires.
        if fight_controller.state == fight_module.DONE and turn_tracker.turn_owner == player:
            # Ending this turn also closes "the end of the Fight phase" for
            # the OPPONENT, and one thing lives in that window: The Twin
            # Lance's Retro-thrusters (game/retro_thrusters.py). It opens at
            # exactly this instant - DONE - so ending the turn here skipped
            # it every time. Reported: "das spiel muss mir die möglichkeit
            # lassen bei meinen twin lance am ende des gegnerischen zuges
            # noch ihre bewegung zu machen. das wurde jetzt einfach
            # übersprungen."
            #
            # This wait is bounded, which is what makes it safe: the offer
            # is answered by taking one of its two moves or by the Skip
            # button (decline()), and announce_wait_once() logs that the
            # turn is being held so it doesn't just look stalled. That is
            # the difference from the open-ended "wait until the opponent is
            # done consolidating" this file already rejected once - that one
            # had no answer that ever came.
            if retro_thrusters_controller is not None and retro_thrusters_controller.has_pending_for_opponent_of(player):
                retro_thrusters_controller.announce_wait_once(player)
                return
            advance_phase_fn()
    else:
        advance_phase_fn()


def _maybe_call_waaagh(player, turn_tracker, waaagh_controller):
    """User policy: the AI always calls a WAAAGH! in battle round 2, if it
    still can (once per battle, only at the very start of `player`'s own
    Command phase) - a deterministic policy, not a judgment call, same as
    Strategic Reserves' "deploy as early as possible" (see
    take_one_action()'s own docstring: "a deterministic policy, not a
    judgment call, so this never asks the agent") - so this never spends an
    agent.decide() call. Round 2 specifically (not "as soon as possible" in
    round 1) is the user's own choice, not derived from anything else -
    presumably because round 1 is normally spent Advancing into position
    rather than already fighting, so the round 2 charge phase is the first
    one where the melee/invulnerable-save boost reliably matters.
    Returns whether it actually called one (True), so the PHASE_COMMAND
    branch above knows to treat this as this frame's one action, exactly
    like every other _handle_*() function's own True/False contract."""
    if waaagh_controller is None or turn_tracker is None:
        return False
    if turn_tracker.battle_round != 2:
        return False
    return waaagh_controller.call(player, turn_tracker)


def _handle_battle_shock(agent, player, all_tokens, battle_shock_controller, insane_bravery_controller, turn_tracker, on_thinking):
    """Rule 08.03: making the roll itself is mandatory, not a real choice -
    but rule 15.04 (Insane Bravery, Core Stratagem, 1CP, usable once per
    BATTLE not per phase) offers a real one first: guarantee a pass now, or
    risk the roll and save the CP for later. Kicks off whichever roll (a
    real 2D6 roll, or none at all if Insane Bravery auto-passes) the human
    clicks to acknowledge via the normal dice UI."""
    for squad in sorted(_all_squads(all_tokens), key=lambda s: s.name):
        if squad.owner != player or not battle_shock_controller.can_roll(squad):
            continue

        if insane_bravery_controller is not None and insane_bravery_controller.can_use(squad):
            options = [
                {"type": "roll_normally", "squad": squad.name, "description": f"{squad.name}: roll normally"},
                {"type": "insane_bravery", "squad": squad.name, "description": f"{squad.name}: Insane Bravery (1CP) - automatically pass"},
            ]
            chosen = _choose(agent, all_tokens, turn_tracker, options, player, on_thinking)
            if chosen["type"] == "insane_bravery":
                insane_bravery_controller.use(squad)
                return True

        battle_shock_controller.start_roll(squad)
        return True
    return False


def _log_disembark(game_log, player, passenger_squad, what, plan=None, failed=False):
    """Every way a disembark can quietly not happen used to leave NOTHING in
    the log, so a turn plan that explicitly ordered a squad out (user report:
    "breacher werden nicht ausgeladen, obwohl es einen befehl dafür gab") was
    indistinguishable from one that never tried.

    `failed=True` marks the outcomes where the unit TRIED and could not be put
    on the board - the ones the on-screen log's "Failed" filter is for. Set by
    the caller rather than sniffed from `what`: only the caller knows whether a
    line describes a decision ("chose to stay embarked") or a defeat."""
    if game_log is None:
        return
    ordered = (" (its turn plan ordered it to disembark)"
               if _plan_ordered_disembark(plan, passenger_squad) else "")
    game_log.add(f"{player}: {passenger_squad.name} {what}{ordered}.",
                 category=game_log_module.FAILED_ORDER if failed else None)


def _plan_ordered_disembark(plan, passenger_squad):
    entry = plan.get(passenger_squad.name) if plan else None
    return bool(entry and entry.get("role") == "disembark")


def _handle_disembark_for_squad(
    agent, memory, player, all_tokens, obstacles, terrain_areas, passenger_squad,
    transport_controller, setup_controller, on_thinking, plan=None, objectives=(),
    game_log=None,
):
    """Rule 18.04 (Disembark Move): a real per-passenger-squad decision -
    stay embarked (safe, but does nothing this turn) or disembark (gets the
    unit onto the battlefield, but locks it out of a charge this turn for
    Rapid/Combat, and out of shooting-eligible positioning choices). Checked
    once per squad per phase (memory.declined_disembark - same "the engine
    has no 'declined' concept of its own" reasoning as declined_shoot/
    declined_charge/declined_explosives). Returns True if a decision was
    made.

    User policy: "die KI sollte nur aus Transports aussteigen, wenn es
    anschließend ein gutes Ziel zum Schießen/Chargen gibt" - staying
    embarked is otherwise strictly safer (a passenger only ever takes
    damage via rule 18.05's Emergency Disembark, which isn't a choice at
    all), so "would disembarking even leave anything worth doing" is a
    real, computable gate (_has_target_after_disembark()), not a
    subjective judgment call to leave to the agent - if nothing's in
    reach, "disembark" isn't even offered as an option, no agent.decide()
    call spent. Only once a target actually exists does the agent get the
    (still real) choice between staying embarked and disembarking."""
    if passenger_squad.name in memory.declined_disembark:
        return False
    if not transport_controller.can_disembark(passenger_squad):
        # Rule 18.04 says no (transport advanced/fell back this phase, was set
        # up this turn, nowhere legal to place, ...). Worth a line: a turn plan
        # that ordered this squad out otherwise fails completely silently, and
        # that cost a whole round of guesswork from raw coordinates once.
        # Only a FAILED order when the plan actually asked for it: with no such
        # order this is the ordinary "its transport advanced this phase" case,
        # and putting that under the failure filter would bury the real ones.
        _log_disembark(game_log, player, passenger_squad,
                       "is not eligible to disembark this phase (rule 18.04)", plan,
                       failed=_plan_ordered_disembark(plan, passenger_squad))
        return False

    transport_token = passenger_squad.embarked_in
    # toward_enemy=True: must match _spread_disembarked_squad()'s own
    # facing exactly (see that function's docstring) - otherwise this
    # eligibility check would be judging a different landing spot than the
    # one the squad will actually end up at if it says yes.
    predicted = _predict_squad_positions_from_point(
        passenger_squad, transport_token.x_in, transport_token.y_in,
        transport_token.radius_in + DISEMBARK_MODEL_GAP_IN, all_tokens, toward_enemy=True,
    )
    # Is getting out worth it at all? Three independent reasons, any one of
    # which is enough. The combat one used to be the ONLY one, which is why
    # a passenger explicitly ordered out to take an objective never even got
    # asked (see _reaches_objective_after_disembark()'s docstring).
    plan_entry = plan.get(passenger_squad.name) if plan else None
    ordered_out = plan_entry is not None and plan_entry.get("role") == "disembark"
    # The mirror of ordered_out: a plan that explicitly parks this squad has
    # already weighed getting out and said no, so don't ask again. Without
    # this the role was purely permissive - "disembark" forced the question,
    # but "hold"/"stage" did nothing to suppress it, so the tactical layer
    # unloaded a squad the plan had just written "Stay aboard Trukk 1 this
    # turn, too far to usefully disembark and fight" about (user: "Warum
    # steigen die boyz jetzt schon aus, obwohl es nichts zum chargen gibt?").
    if plan_entry is not None and plan_entry.get("role") in (
        "stay_embarked", "hold", "stage", "reserve"):
        _log_disembark(game_log, player, passenger_squad,
                       f"stays embarked - its turn plan assigned '{plan_entry.get('role')}'", plan)
        memory.declined_disembark.add(passenger_squad.name)
        return True
    if not (
        ordered_out
        or _has_target_after_disembark(passenger_squad, predicted, all_tokens, obstacles, terrain_areas)
        or _reaches_objective_after_disembark(passenger_squad, predicted, objectives)
    ):
        _log_disembark(game_log, player, passenger_squad,
                       "stays embarked - nothing to shoot, charge or claim from where the Transport is", plan)
        memory.declined_disembark.add(passenger_squad.name)
        return True

    # A passenger contributes nothing while aboard, so surface both what it
    # would bring to the fight and whatever the turn plan said to do with it
    # (user report: "sie weiß nicht, dass im devilfish breacher stecken, mit
    # denen man sehr viel schaden austeilen könnte") - the same "put the
    # numbers in the option text" approach the shooting options already use.
    planned_target = _planned_enemy_target(passenger_squad, plan, all_tokens)
    plan_note = f" [your turn plan assigned {planned_target.name} to this squad]" if planned_target is not None else ""
    options = [
        {"type": "stay_embarked", "squad": passenger_squad.name,
         "description": f"{passenger_squad.name}: stay embarked (it cannot shoot, hold an objective or fight while aboard)"},
        {"type": "disembark", "squad": passenger_squad.name,
         "description": (
             f"{passenger_squad.name}: disembark from its Transport and join the fight "
             f"(weapons: {_ranged_weapon_summary(passenger_squad)}){plan_note}"
         )},
    ]
    chosen = _choose(agent, all_tokens, transport_controller.turn_tracker, options, player, on_thinking)
    if chosen["type"] == "stay_embarked":
        _log_disembark(game_log, player, passenger_squad, "chose to stay embarked", plan)
        memory.declined_disembark.add(passenger_squad.name)
        return True

    # Rule 18.02: embarked_in gets cleared by TransportController._begin_
    # placement() as soon as start_disembark() runs - transport_token was
    # already captured above, before that happened.
    transport_controller.start_disembark(passenger_squad)
    # _begin_placement() runs synchronously inside start_disembark() for
    # EVERY mode now - a Combat Disembark's hazard roll (06.03) no longer
    # comes first, it follows the confirmed placement (see
    # TransportController.confirm_disembark() for why), so there is no
    # pending roll to hand back to a later frame here.
    if setup_controller.setting_up_squad is passenger_squad:
        if not _place_disembarked_squad(
            transport_controller, setup_controller, passenger_squad, transport_token, all_tokens,
        ):
            _log_disembark(game_log, player, passenger_squad,
                           "could not be placed after disembarking from any facing - stayed aboard",
                           plan, failed=True)
            transport_controller.cancel_disembark()
            memory.declined_disembark.add(passenger_squad.name)
    else:
        # start_disembark() didn't even reach placement - nothing changed, so
        # this squad must not be asked again this phase (see below).
        _log_disembark(game_log, player, passenger_squad,
                       "disembark never reached the placement step", plan, failed=True)
        memory.declined_disembark.add(passenger_squad.name)
    return True


def _execute_fall_back(fall_back_controller, movement_controller, squad, all_tokens, game_log):
    """Rule 09.07: retreat directly away from the nearest enemy squad's
    centroid - confirm_move()'s generic "must end unengaged" check (there's
    no special-cased Fall Back end condition) decides actual legality, so
    any direction that gets clear works; straight away from the enemy is
    the obvious, always-available one, same "nearest enemy centroid" idea
    _nearest_enemy_squad()/_centroid() already use for a normal advance,
    just pointed the opposite way. Reuses _advance_toward()'s per-model-
    first/bulk-fallback retry sweep for the actual movement (see its own
    docstring for why per-model goes first) - `start_move_fn` is passed
    through so each retry attempt (re)primes the move via
    movement_controller.start_fall_back_move(mode) instead of a Normal
    Move's start_move(), since that's what FallBackController.choose_mode()
    already called once to set move_mode="fall_back" in the first place.

    Always picks Ordered Retreat, never Desperate Escape, when the squad
    itself isn't already battle-shocked (fall_back_controller.declare()
    forces Desperate Escape automatically if it IS - no real choice there,
    same as the human UI) - no reason for the AI to volunteer for
    Desperate Escape's extra Hazard Roll/immediate Battle-Shock test risk
    when a plain retreat is equally legal for an unshocked unit.

    User-requested tactical policy: "ki soll sich mit schwachen
    Nahkampfeinheiten zurückziehen, damit andere wieder auf den Gegner
    schießen können" - rule 03.04/_is_valid_target_squad() already block
    shooting at any enemy unit that's currently engaged (with ANYONE, not
    just the shooter) - retreating a losing melee unit out of engagement
    is what actually re-opens that enemy to the rest of the army's ranged
    fire this same turn (Movement precedes Shooting), not a new mechanic of
    its own. Falls back to remain_stationary() if the retreat can't
    physically land unengaged anywhere sampled - same "no repair loop,
    remain stationary instead" fallback every other AI move in this file
    uses."""
    fall_back_controller.declare(squad)
    if fall_back_controller.state == fall_back_module.CHOOSING_MODE:
        fall_back_controller.choose_mode(fall_back_module.ORDERED_RETREAT)
    if fall_back_controller.acting_squad is not squad or movement_controller.move_mode != "fall_back":
        # declare()/choose_mode() refused (e.g. can_make_fall_back_move()
        # no longer holds) - nothing to do, remain stationary instead.
        movement_controller.remain_stationary()
        return

    nearest = _nearest_enemy_squad(squad, all_tokens)
    cx, cy = _centroid(squad)
    if nearest is not None:
        ex, ey = _centroid(nearest)
        dx, dy = cx - ex, cy - ey
    else:
        dx, dy = 0.0, -1.0
    dist = (dx * dx + dy * dy) ** 0.5
    if dist <= 1e-9:
        dx, dy, dist = 0.0, -1.0, 1.0
    ux, uy = dx / dist, dy / dist
    # Comfortably further than any single move could possibly reach - the
    # actual distance travelled is decided by clamp_move()/remaining_range,
    # not by how far this target point sits; it only sets the DIRECTION.
    reach = min_model_movement(squad) * 4.0
    target_point = (cx + ux * reach, cy + uy * reach)

    # Captured once, before the retry loop - cancel_fn (fall_back_controller.
    # decline()) resets fall_back_controller.mode/acting_squad to None
    # between failed attempts (needed so a LATER attempt's confirm_fn can
    # still tell Ordered Retreat from Desperate Escape correctly, since
    # FallBackController.confirm() reads self.mode directly - it has no
    # idea this is attempt #5 of a retry sweep), so start_fn restores both
    # right before every attempt, not just the first.
    mode = fall_back_controller.mode

    def start_fn():
        fall_back_controller.mode = mode
        fall_back_controller.acting_squad = squad
        movement_controller.start_fall_back_move(mode)

    # User directive: vehicle-only squads never get the rigid bulk fallback
    # for any move type, Fall Back included - see _handle_movement()'s own
    # advance/staging call for the fuller reasoning.
    allow_bulk = not all(m.profile.vehicle for m in squad.models)

    if not _advance_toward(
        movement_controller, squad, target_point, start_move_fn=start_fn,
        confirm_fn=fall_back_controller.confirm, cancel_fn=fall_back_controller.decline,
        allow_bulk_fallback=allow_bulk,
    ):
        movement_controller.remain_stationary()
        if game_log is not None:
            game_log.add(f"{squad.name}'s Fall Back move was illegal, remained stationary instead.",
                     category=game_log_module.FAILED_ORDER)


# How far beyond a unit's reach a spot the collision pass SHIFTED an order to
# may lie before the order is dropped instead of shifted (see
# _separate_colliding_positions()). Anything up to this far is left to
# _validate_turn_plan()'s reach clamp, which shortens the line and keeps the
# heading; further than this the shifted point is no longer the same piece of
# ground and the unit is better off picking its own.
#
# Judgement, calibrated on the logs rather than discovered in them: over every
# log in the repo the shortfall (ordered distance minus the unit's reach) runs
# 0"-18" with a median of exactly 3.0". Absolute inches rather than a ratio
# because the thing at stake is geometric - whether the point is still the same
# piece of ground, behind the same wall, inside the same objective - and that
# does not scale with how fast the unit happens to be.
#
# THIS USED TO ALSO DECIDE WHICH REACH OVERSHOOTS WENT BACK TO THE PLANNER on
# the retry channel (_problems_for_the_planner()): up to 3" the clamp absorbed
# them, beyond that the order was sent back. Measured twice, in opposite
# directions, and both measurements point the same way. From
# logs/game_20260815_203850.log: the WAAAGH turn's first plan came back with 18
# problems, five of them reach overshoots of 1"-2", and the REVISION pulled the
# whole army back into its own deployment zone and turned four disembark orders
# into "stay_embarked" - a re-plan is not free and not neutral. From
# logs/game_20260909_210843.log: Canoptek Wraiths (10" move) ordered to (25,20),
# 17" away, were sent back; the revision ordered them to (44,7), reachable, and
# 2" FURTHER from the Central Objective the order's own reason named - the unit
# walked backwards, exactly as instructed. Sending an overshoot back hands the
# planner the same open question it already answered badly; the clamp, plus the
# observation now OFFERING the first leg toward every distant goal (see
# ai/observation.py's first_leg_toward()), answers it deterministically. So no
# overshoot goes back any more, whatever its size - see _problems_for_the_planner().
_CLAMP_TOLERANCE_IN = 3.0


def _problems_for_the_planner(plan, player, state):
    """The orders in this plan that only the PLANNER can fix - the ones that
    go back to it once on the retry channel (see _run_turn_plan()).

    Kept separate from _validate_turn_plan()'s corrections because the two
    answer different questions. The validator asks "what do we do with a bad
    order"; this asks "is the order bad in a way a deterministic rewrite would
    make WORSE", which is what lets the planner be told about it and fix it
    ITSELF (user: "sollte fix nicht aber sein, dass der planner gar nicht
    erst die zu weit entfernte koordinate vorschlagen kann? der planner ist
    hier der wissende").

    What qualifies: an order whose fix needs a judgement this code cannot
    make. A LONE OPERATIVE target that cannot be shot from the ordered spot
    (which of the two - the spot or the target - was the point?), a garrison
    too large for its objective (which unit is freed, and what should it do
    instead?), a lone unit parked on an objective nobody threatens.

    What NO LONGER qualifies: a position beyond the unit's reach. It did,
    beyond a 3" tolerance, on the argument that clamping is lossy - a
    coordinate is chosen for a property and the point along the line inherits
    none of it. That argument is right and the retry was still the wrong
    answer, measured on logs/game_20260909_210843.log: the planner was asked
    to replace an order 17" away with something reachable and came back with
    a reachable point 2" further from its own goal. Handing the SAME open
    request back to the same reasoner reproduces the same mistake; what fixes
    it is offering the point (ai/observation.py's first_leg_toward(), now
    attached to every distant goal in the observation) and, for an order that
    still ignores it, clamping and the backwards-order guard in
    _validate_turn_plan(). Both deterministic, no second planner call."""
    problems = []
    squads_by_name = {s.name: s for s in _all_squads(state.tokens)}
    for squad in list(state.embarked_squads):
        squads_by_name.setdefault(squad.name, squad)
    problems.extend(_unshootable_from_position_problems(plan, squads_by_name, state))
    problems.extend(_over_garrison_problems(plan, squads_by_name, state, player))
    problems.extend(_lone_garrison_problems(plan, squads_by_name, state, player))
    return problems


# A position has to be at least this much further from the order's own goal
# than the unit already stands before it counts as a step backwards. Absolute
# inches: a lateral step to a covered spot can sit a few tenths further from
# the goal and is a real order; two inches further is not "beside", it is
# "away".
_BACKWARD_ORDER_TOLERANCE_IN = 1.0


def _order_goal_point(entry, squad, state):
    """(point, name) of the thing this order says the unit is heading for, or
    (None, None) when it names nothing this code can locate.

    Read from the `target` field first - an objective's centre, or the
    centroid of an ENEMY unit. A friendly unit as target says nothing about
    direction (a unit is not walking "toward" its own transport in the sense
    that matters here) and is ignored. Then, because the reported order had an
    EMPTY target field and put its goal in prose ("Push toward Central
    Objective; move to a reachable point (44,7)"), the reason text is scanned
    for objective and enemy-unit names and the earliest mention wins. The
    reason is the field the tactical layer reads whole, so a goal stated there
    is a goal the order really has."""
    def locate(name):
        for objective in state.objectives:
            if objective.name == name:
                return _objective_centre(objective), objective.name
        other = _squad_by_name(name, state.tokens)
        if other is not None and other.owner != squad.owner and other.models:
            return _centroid(other), other.name
        return None, None

    target = entry.get("target")
    if target:
        point, found = locate(target)
        if point is not None:
            return point, found
    reason = (entry.get("reason") or "").lower()
    if not reason:
        return None, None
    candidates = [o.name for o in state.objectives]
    candidates += [s.name for s in _all_squads(state.tokens) if s.owner != squad.owner and s.models]
    best = None
    for name in candidates:
        at = reason.find(name.lower())
        if at >= 0 and (best is None or at < best[0]):
            best = (at, name)
    if best is None:
        return None, None
    return locate(best[1])


def _planned_garrisons(plan, squads_by_name, state, player):
    """{objective: [squad, ...]} for the objectives this plan leaves the
    player's units standing on at the end of the turn.

    Where a unit ENDS is the question, so a named position is read in
    preference to the unit's current spot - which is the whole reason the
    reported Kill Rig counts here at all. Its role was "advance", not "hold",
    so no amount of role-reading would have found it; what parked it was the
    coordinate, ordered to (40,6), then (32,8), then (27,9), every one of them
    inside P2 Home Objective's own footprint (x 24.1-35.5, y 3.7-10.7).

    A unit with no position and an ACTIVE role is left out on purpose: the
    plan has told it to go somewhere, and this function has no business
    guessing that it will fail to. Only a passive role means "you will still
    be standing where you are".

    Anything off the battlefield is excluded outright rather than being given a
    passive role to match. Rules 18.02/20.04: a passenger and a reserve unit
    stand on nothing at all, and - the reason this is an exclusion and not a
    judgement call - their model coordinates are stale leftovers that were
    never a board position (see _reach_origin(), where the same fact was worth
    30" of error). Reading them here counted a passenger as garrisoning
    whatever its transport happened to be parked on, which a test caught by
    putting Beast Snagga Boyz in a Kill Rig sitting on the objective."""
    passive = ("hold", "screen", "stage")
    off_board = {id(s) for s in list(state.embarked_squads) + list(getattr(state, "reserves", ()))}
    garrisons = {}
    for name, entry in plan.get("unit_plans", {}).items():
        squad = squads_by_name.get(name)
        if squad is None or not squad.models or squad.owner != player:
            continue
        if id(squad) in off_board or getattr(squad, "embarked_in", None) is not None:
            continue
        spot = entry.get("position")
        for objective in state.objectives:
            if spot is not None:
                here = objective.terrain_area.contains_point(spot[0], spot[1])
            elif entry.get("role") in passive:
                here = any(objective.terrain_area.overlaps_model(m) for m in squad.models)
            else:
                here = False
            if here:
                garrisons.setdefault(objective.name, []).append(squad)
    return garrisons


def _enemies_near_objective(objective, state, player):
    """The enemy models close enough to contest `objective` next turn - one
    definition of "near", read by both questions asked about it below
    (how MUCH they could bring, and whether there is anyone at all)."""
    return [
        token for token in state.tokens
        if token.squad is not None and token.squad.owner != player
        and objective.terrain_area.distance_to_model(token) <= observation.GARRISON_THREAT_RANGE_IN
    ]


def _uncontested_objectives(state, player):
    """The objectives this player controls that no enemy is near at all.

    Still the strict reading, and still what _lone_garrison_swaps() wants:
    handing an objective to a cheaper unit is a fair trade when nobody is
    coming for it, and a different proposition when something is 12" away. The
    over-garrison pass is the one that now works in Objective Control instead
    - see _held_objectives()."""
    return [objective for objective, _threat_oc in _held_objectives(state, player)
            if not _enemies_near_objective(objective, state, player)]


def _held_objectives(state, player):
    """[(objective, threat_oc)] for every objective this player controls -
    threat_oc being the Objective Control the enemy could bring onto it next
    turn, i.e. the bar this player's garrison actually has to clear.

    THIS USED TO BE _uncontested_objectives(), and returned only the
    objectives no enemy was within GARRISON_THREAT_RANGE_IN of. Reported as
    "die necrons kommen immer nicht so richtig von ihrem home objective weg.
    sowohl necron warriors als auch immortals klumpen auf dem home objective":
    an enemy inside that range switched the whole over-garrison pass OFF for
    that objective, so any number of units could sit on it indefinitely. In
    the reported game an Avatar of Khaine stood about 12" from P2 Home from
    turn 2 onward, and a 270-point, 21-model Necron Warriors blob spent the
    rest of the battle parked behind an objective an 11-model Immortals unit
    was already holding - measured off that log, it advanced two inches in
    five turns.

    A THREAT JUSTIFIES A GARRISON, NOT AN UNLIMITED ONE, and rule 14.02 says
    exactly how big a garrison that is: control goes to the higher Objective
    Control total, so what a defender needs is more OC than the enemy can
    bring, not more units than the enemy has. Measured on the reported board:
    the Avatar's OC is 5, the Immortals' 21, the Necron Warriors' 41 - so the
    Immortals hold it against that threat on their own and every one of those
    41 points of OC was surplus. See _garrison_surplus(), which spends this
    number.

    Both halves of "do we control it" remain the ones ai/observation.py
    already reports to the planner as "your_units_here"/"enemy_units_
    within_12in", deliberately: this check has to agree with the numbers the
    plan was written against, or it corrects orders on grounds the planner was
    never shown."""
    out = []
    for objective in state.objectives:
        oc = objective.level_of_control(state.tokens)
        ours = oc.get(player, 0)
        theirs = max((v for k, v in oc.items() if k != player), default=0)
        if ours <= 0 or ours <= theirs:
            continue
        # Summed over MODELS rather than taken from level_of_control(), which
        # only counts what is standing ON the marker: the units that make an
        # objective worth defending are precisely the ones not on it yet.
        threat_oc = sum(objective_control.effective_oc(token, state.tokens, objective)
                        for token in _enemies_near_objective(objective, state, player))
        out.append((objective, threat_oc))
    return out


def _garrison_surplus(plan, squads_by_name, state, player):
    """[(objective, keepers, freed)] - which of the units this plan parks on an
    objective are actually needed to hold it, and which are spare.

    ONE definition, read by both the report to the planner
    (_over_garrison_problems()) and the correction that runs when the planner
    does not act on it. It was written out twice, and the two copies were the
    same six lines - the shape this codebase keeps having to consolidate, and
    one that would have drifted the moment either side learned about threats.

    HOW MANY ARE KEPT is rule 14.02's own arithmetic: units are taken in
    _garrison_fitness() order - the unit best suited to standing there, then
    the cheapest - until their Objective Control exceeds what the enemy can
    bring (see _held_objectives()). For an objective nobody is near, threat_oc
    is 0 and the first keeper's own OC clears it, so exactly one unit is kept
    and the behaviour is the one this pass has always had. The `keepers and`
    guard is what makes that true rather than nearly true: without it a unit
    whose OC is 0 - battle-shocked, rule 01.07 - would keep the loop running
    and free nobody."""
    garrisons = _planned_garrisons(plan, squads_by_name, state, player)
    out = []
    for objective, threat_oc in _held_objectives(state, player):
        squads = garrisons.get(objective.name, [])
        if len(squads) < 2:
            continue
        keepers, freed, oc = [], [], 0
        for squad in sorted(squads, key=lambda sq: _garrison_fitness(sq, objective, state)):
            if keepers and oc > threat_oc:
                freed.append(squad)
                continue
            keepers.append(squad)
            oc += sum(objective_control.effective_oc(m, state.tokens, objective)
                      for m in squad.models)
        if freed:
            out.append((objective, keepers, freed))
    return out


def _garrison_cost_key(squad):
    """Sort key for "which of these units should be the one left holding it".

    Cheapest first, which is the prompt's own rule ("garrison with the
    cheapest unit that holds it; never park a powerful unit while weaker ones
    do the fighting"). A unit whose points are unknown sorts LAST rather than
    first: Squad.points is None whenever any component is unpriced, and the
    honest reading of "we cannot tell what this costs" is that we may not
    claim it is the cheap one. Erring that way frees it to fight, which is the
    direction the reported failure was in."""
    return (squad.points is None, squad.points if squad.points is not None else 0, squad.name)


def _garrison_fitness(squad, objective, state):
    """How well suited `squad` is to being the unit left standing on
    `objective`, lower is better - the ONE definition all three garrison sites
    read.

    Role band first, points within the band. The band is
    combat_focus.home_garrison_rank(), measured against the reach
    observation.garrison_reach_needed_in() takes off this board; see that
    function and _cheaper_garrison_candidates() for why role has to come first
    and why the reach half is a separate term from the ratio.

    BOTH SITES, deliberately: _garrison_surplus() picks the keepers out of two
    or three units, and the lone-garrison pass decides whether one unit should
    hand the job to another. Those are one question asked twice, and answering
    it from two different orderings is exactly the quiet drift this codebase
    keeps consolidating away - it would have let the over-garrison pass keep
    the very unit the lone pass was rewritten to stop choosing.

    It used to be THREE sites: the over-garrison correction and the report it
    sends to the planner first each sorted their own copy of the same list.
    They are one call now (_garrison_surplus()), which is what let the keeper
    rule learn about threats in one place instead of two."""
    reach_needed = observation.garrison_reach_needed_in(
        objective, getattr(state, "objectives", ()))
    return (combat_focus.home_garrison_rank(squad, reach_needed),
            _garrison_cost_key(squad))


def _objective_centre(objective):
    """The point ai/observation.py reports to the planner as an objective's
    position. Read from THERE rather than re-derived, so a rewritten order
    names a spot the planner would recognise - the two used to be separate
    copies of the same bounding-box arithmetic."""
    return observation.objective_centre(objective)


def _can_hold_objectives(squad):
    """Whether this unit could contribute to controlling anything at all.

    Rule 14.02 counts Objective Control, and rule 01.07 sets a battle-shocked
    unit's OC to "-", so such a unit garrisons precisely nothing - sending it
    to take over the job would hand the objective away."""
    if squad.battle_shocked:
        return False
    return any(m.profile.oc > 0 for m in squad.models if not m.is_dead())


def _cheaper_garrison_candidates(objective, holder, squads_by_name, state, player, busy):
    """Units that could take `objective`'s garrison job off `holder`, cheapest
    first - the ones that make leaving a 170-point mob parked on it a mistake
    rather than a judgement call.

    A candidate has to be genuinely available: on the battlefield (rules
    18.02/20.04 put a passenger and a reserve unit nowhere at all), able to
    hold ground at all, able to REACH the objective under its own movement
    this turn, strictly cheaper than the holder - and not already assigned to
    an objective of its own, since pulling it off one to cover another just
    moves the hole.

    ORDERED BY ROLE FIRST, POINTS SECOND. Cheapest-first alone hands the job to
    whichever unit is cheapest, and an army's assault units are routinely its
    cheapest - so this correction, whose entire purpose is to stop good units
    being wasted on empty ground, was itself doing the wasting. Reported by the
    user as "die lych guard waren sehr passiv. die sollten eher weiter nach
    vorne pushen": measured on logs/game_20260826_185516.log, the strongest
    case is not even the unit reported. This pass moved the Necron Warriors off
    P2 Home Objective and handed it to the 85-point Skorpekh Destroyers, who
    then spent four of five turns standing on ground no enemy came within 12"
    of - the army's best melee unit, with no ranged weapons at all, garrisoning.

    THE ROLE IS ALSO PART OF "CHEAPER", which is the half a sort key could not
    fix and the reported failure came back through. "Strictly cheaper than the
    holder" was the whole definition of a worthwhile swap, so with points alone
    deciding it, this pass could only ever move the job DOWN the points list -
    and on the current Necron list that meant it took P2 Home Objective off the
    270-point Necron Warriors and gave it to the 170-point Lychguard, the
    army's melee anvil, while the Immortals were not even eligible to be
    considered because they cost more. Measured on the reported game
    (logs/game_20260826_234856.log, lines 124-125). The gate is now the same
    (band, points) pair as the ordering, so a swap has to be an improvement on
    the axis that matters first: a unit that would be WORSE at the job is not a
    candidate for it however little it costs.

    combat_focus.home_garrison_rank() is the repo's existing measurement of
    "where does this unit's damage come from" read a third way (it already
    gates the charge block and the deployment `assault` role), so this is
    another consumer rather than a second opinion. It also carries the range
    half of the user's "starke fernkaempfer mit hoher reichweite", against the
    distance observation.garrison_reach_needed_in() measures on this board.

    Still a SORT KEY within a band: if several units are equally suited, the
    cheapest takes the job, which is what that rule was always for."""
    centre = _objective_centre(objective)
    def fitness(squad):
        return _garrison_fitness(squad, objective, state)

    held = fitness(holder)
    off_board = {id(sq) for sq in list(state.embarked_squads) + list(getattr(state, "reserves", ()))}
    loaded_hulls = {
        id(passenger.embarked_in) for passenger in state.embarked_squads
        if getattr(passenger, "embarked_in", None) is not None
    }
    out = []
    for squad in squads_by_name.values():
        if squad is holder or squad.owner != player or not squad.models:
            continue
        if id(squad) in off_board or getattr(squad, "embarked_in", None) is not None:
            continue
        if id(squad) in busy or not _can_hold_objectives(squad):
            continue
        # A loaded transport already has a job that matters more than standing
        # on uncontested ground: its passengers are off the battlefield
        # entirely until it puts them down (rule 18.02). Parking it garrisons
        # the objective and benches the unit inside it at the same time.
        if any(id(m) in loaded_hulls for m in squad.models):
            continue
        if fitness(squad) >= held:
            continue
        gap, reach = _reach_to_point(squad, centre)
        if gap > reach:
            continue
        out.append((squad, gap))
    return [sq for sq, _ in sorted(out, key=lambda pair: (fitness(pair[0]), pair[1]))]


def _lone_garrison_swaps(plan, squads_by_name, state, player, shortened=()):
    """[(objective, holder, replacement), ...] - objectives this plan leaves a
    needlessly EXPENSIVE unit sitting on when a cheaper one could do it.

    _over_garrison_problems() below is the same rule for the case where two or
    three units pile onto one objective, and it keeps the cheapest of THEM.
    What neither it nor anything else caught is the single-unit case, which is
    the one that was reported: "die 20 boyz wurden gerade auf dem home
    objective geparkt, obwohl die KI auch 2 gretchin trupps hat. das geht gar
    nicht, die boyz sollen nach vorne und gretchins das homeobjective halten."
    There is only ever one unit on the objective, so the count test never
    fires, and a 170-point mob spends the game standing on ground that a
    45-point one holds exactly as well - rule 14.02 decides control on the
    higher OC total, and the enemy is not contesting it at all.

    A unit that is already assigned to some objective is off limits as a
    replacement (`busy`), so this can only ever move the job to a unit that had
    no objective of its own.

    `shortened` names the units whose coordinate the reach clamp just rewrote,
    and they are exempt unless their role is passive. A clamped order is one
    the planner aimed somewhere far forward and the engine cut back to what the
    unit can walk this turn; that shortened point can land on a controlled
    objective purely in passing, and treating a unit crossing its own ground as
    a garrison would take the waypoint away from a unit that is on its way
    somewhere. Measured on test_plan_churn.py's reported turn, that is exactly
    what happened to Warbikers 2: ordered to (30,35), clamped to (47,24), which
    is inside No Man's Land (E). A PASSIVE role is different - it says the unit
    is meant to be standing there when the turn ends - so it is still caught."""
    garrisons = _planned_garrisons(plan, squads_by_name, state, player)
    busy = {id(sq) for squads in garrisons.values() for sq in squads}
    passive = ("hold", "screen", "stage")
    swaps = []
    for objective in _uncontested_objectives(state, player):
        squads = garrisons.get(objective.name, [])
        if len(squads) != 1:
            continue  # nobody there, or the over-garrison pass owns this case
        holder = squads[0]
        entry = plan.get("unit_plans", {}).get(holder.name, {})
        if holder.name in shortened and entry.get("role") not in passive:
            continue
        candidates = _cheaper_garrison_candidates(
            objective, holder, squads_by_name, state, player, busy)
        if not candidates:
            continue
        replacement = candidates[0]
        busy.add(id(replacement))  # it is spoken for now, for any later objective
        swaps.append((objective, holder, replacement))
    return swaps


def _lone_garrison_problems(plan, squads_by_name, state, player):
    """The planner-facing half of _lone_garrison_swaps(). Reported on the same
    one-retry channel as the other checks here, because only the planner knows
    what the freed unit should be doing instead - the rewrite below is the
    backstop for when it does not act on this."""
    problems = []
    for objective, holder, replacement in _lone_garrison_swaps(
        plan, squads_by_name, state, player
    ):
        cost = f" ({holder.points} pts)" if holder.points is not None else ""
        cheap = f" ({replacement.points} pts)" if replacement.points is not None else ""
        problems.append(
            f"{holder.name}{cost} is left holding {objective.name}, which no enemy is within "
            f"{observation.GARRISON_THREAT_RANGE_IN:.0f}\" of and which you already control. "
            f"Control is decided by the higher Objective Control total, not by how good the unit "
            f"is, so {replacement.name}{cheap} holds it exactly as well, can reach it this turn "
            f"and is better suited to standing there. Garrison behind your own lines with a "
            f"long-ranged shooting unit - it still fires from back there - and give "
            f"{holder.name} a job where the game is actually being decided"
        )
    return problems


def _over_garrison_problems(plan, squads_by_name, state, player):
    """Orders that park more than one unit on an objective nobody contests.

    Rule 14.01-14.02: control goes to the higher Objective Control total, so a
    second and third unit on an objective the enemy is nowhere near adds
    nothing at all and subtracts those units from the game.

    THIRD report of this same behaviour, which is the argument for handling it
    here rather than with more prose. The first was answered with a prompt
    paragraph and came back unchanged; the second added the two numbers the
    decision turns on ("your_units_here"/"enemy_units_within_12in") plus a
    hard rule phrased in terms of them - see observation.objective_threat_
    summary()'s own docstring - and it came back again. Measured on the
    reported turn, the planner had every number it needed: P2 Home Objective
    read your_units_here = [Boyz 1 + Warboss, Gretchin 2, Kill Rig],
    enemy_units_within_12in = [], oc = {Player 2: 35}. Its own written reason
    for one of the three even says so - "one cheap-ish garrison unit isn't
    needed here since Tankbustas/Gretchin also sit on it, but keep this strong
    unit ready" - and it held anyway. A rule taught only as prompt text stays
    optional; that is what this file exists for.

    Reported to the planner first, on the same one-retry channel as the other
    checks here, because only it knows what the freed units should do instead.
    _validate_turn_plan() keeps the cheapest and frees the rest if it does
    not."""
    problems = []
    for objective, keepers, freed in _garrison_surplus(plan, squads_by_name, state, player):
        problems.append(
            f"{len(keepers) + len(freed)} of your units are all left standing on "
            f"{objective.name}: "
            + ", ".join(f"{s.name} ({s.points} pts)" if s.points is not None else s.name
                        for s in keepers + freed)
            + ". You already control it, and control is decided by the higher Objective Control "
            f"total, not by how many units are present - "
            + ", ".join(s.name for s in keepers)
            + " already out-controls anything the enemy can bring onto it. Leave that there and give "
            + ", ".join(s.name for s in freed)
            + " a real job somewhere the game is being decided"
        )
    return problems


def _unshootable_from_position_problems(plan, squads_by_name, state):
    """Orders that send a squad somewhere it cannot possibly shoot the very
    target the same order names.

    Rule 24.24 (LONE OPERATIVE) is the case that has one: such a unit can only
    be selected as a target from within its own short range, so "stand at X and
    shoot Y" is self-contradictory whenever X is further from Y than that.

    Reported by the user, from the log's own orders: "wenn der plan war, den
    ghostkeel zu beschiessen, dann war der plan falsch, denn der ghostkeel hat
    lone op." Correct - `2 Deffkoptas 1: advance -> 1 Ghostkeel Battlesuit 1
    @(26,8) (Rokkits can hurt the Ghostkeel; move up within 24in to shoot it)`.
    The Ghostkeel stood at (26.45,23.79), so the ordered spot is 15.8" away and
    the shot is illegal from it, whatever the rokkits' range says.

    _validate_turn_plan()'s existing 24.24 check does not catch this and is not
    wrong to miss it: it asks whether the target can be reached AT ALL this turn
    (19.96" away, 12" of movement, so yes - 7.96" inside the limit) and would
    have been wrong to drop a target the unit really could have closed on. The
    contradiction only appears once the ordered POSITION is taken into account,
    which is the same blind spot the destination-line-of-sight field was added
    for: the planner reasons about where the unit STANDS, and its order is about
    where the unit will BE.

    Measured generously on purpose - the squad's models spread around the aimed
    point, so the nearest one can be up to half the formation's own width closer
    than the point itself. Only an order that no model could shoot from is
    reported."""
    problems = []
    for name, entry in plan.get("unit_plans", {}).items():
        spot = entry.get("position")
        target_name = entry.get("target")
        if spot is None or not target_name:
            continue
        squad = squads_by_name.get(name)
        target = _squad_by_name(target_name, state.tokens)
        if squad is None or not squad.models or target is None or not target.models:
            continue
        lone_range = status_effects.lone_operative_range(target)
        if lone_range is None:
            continue
        gap = _distance_from_squad_to_point(target, spot) - _squad_half_width(squad)
        if gap > lone_range:
            problems.append(
                f"{name}: ordered to stand at ({spot[0]:.0f},{spot[1]:.0f}) and attack "
                f"{target.name}, but that target has LONE OPERATIVE {lone_range:.0f}\" and the "
                f"ordered spot is {gap:.0f}\" from it - it cannot be shot at from there at all. "
                f"Either name a spot within {lone_range:.0f}\" of it, or give this unit a "
                f"different target"
            )
    return problems


def _squad_half_width(squad):
    """Half the squad's widest pair - how far its most forward model can sit
    from the point the formation is aimed at (see _formation_slot(), which
    carries each model's offset from the centroid over to the destination)."""
    if len(squad.models) < 2:
        return 0.0
    return max(
        edge_distance(a, b)
        for i, a in enumerate(squad.models)
        for b in squad.models[i + 1:]
    ) / 2.0


# Two of my own squads ordered closer together than their bases plus a little
# working room can be called the same destination.
_ORDER_COLLISION_MARGIN_IN = 1.5


# Passes of the push-apart loop below. Each pass separates a spot from every
# settled one it still overlaps; two or three are enough because the shifts are
# tiny and shrink each time, and an unbounded loop over a crowded flank is the
# one way this could stall a turn.
_SEPARATION_PASSES = 3


def _separate_colliding_positions(plan, squads_by_name):
    """Push apart orders that send two of the player's OWN squads to the same
    spot, in plan-priority order, and say what moved.

    Observed harm, which is why this is checked at all: the plan sent
    "2 Boyz 1" to (31,21) and "2 Deff Dread 1" to (30,22) - 1.4" apart, both
    inside map2's central ruin. The Boyz, being INFANTRY, walked over its wall
    (rule 13.06) and parked in the ruin's only 3.0"-wide doorway; the Deff
    Dread's base is 2.36" across and that doorway was its single way in, so it
    moved zero inches and stood there for the rest of the game.

    This USED to be reported to the planner instead, on the argument that a
    coordinate is chosen for a property (that objective, behind that wall) and a
    spot 2" to one side inherits none of it, so only the planner can decide
    which unit keeps it. The argument is sound and the price turned out to be
    far higher than the thing it was buying. Measured over every log in the
    repo: 57 of 131 plan problems are this one, and not one of them is a real
    stack - the two ordered points run 0.4"-4.1" apart with a median of 2.8",
    which is a nudge, and the mover already clamps units apart on the board
    anyway. What it bought instead was a re-plan, and a re-plan is not neutral.
    In logs/game_20260815_203850.log the WAAAGH turn came back with 18
    problems, THIRTEEN of them this one, and the revision - the plan that
    actually ran - pulled the whole army back into its own deployment zone and
    turned all four disembark orders into "stay_embarked". Round 3 was 4
    complaints of 1.4"-3.6", all of them this one, and the Battlewagon reversed.

    So: separate them here, cheaply, and keep the intent. Priority order is the
    plan's own (`priority`, "lower moves first"), so the unit the plan wanted
    there first keeps the spot and the later one steps aside - which is also
    what physically happens on the board. A spot that cannot be cleared without
    leaving the unit's own reach loses its position rather than being invented
    somewhere arbitrary; the movement options then come from the engine, so
    whatever the tactical layer does instead is legal by construction - the same
    resolution _validate_turn_plan()'s garrison pass uses."""
    ordered = []
    for name, entry in plan.get("unit_plans", {}).items():
        spot = entry.get("position")
        squad = squads_by_name.get(name)
        if spot is not None and squad is not None and squad.models:
            priority = entry.get("priority")
            if not isinstance(priority, int) or isinstance(priority, bool):
                priority = _UNPLANNED_MOVE_PRIORITY
            ordered.append((priority, name, entry, squad))
    ordered.sort(key=lambda o: (o[0], o[1]))  # name breaks ties, so this is stable

    corrections = []
    settled = []  # (x, y, radius) of the spots already granted this turn
    for _priority, name, entry, squad in ordered:
        spot = entry["position"]
        radius = max_model_radius(squad)
        moved = _pushed_clear(spot, radius, settled)
        if moved is None:
            settled.append((spot[0], spot[1], radius))
            continue
        # Only accept the shift if the unit can still get there. Everything else
        # in this file measures reach through _reach_to_point() so a passenger is
        # measured from its transport; this has to as well or a shifted disembark
        # order silently becomes unreachable.
        gap, reach = _reach_to_point(squad, moved)
        if gap - reach > _CLAMP_TOLERANCE_IN:
            entry["position"] = None
            corrections.append(
                f"{name}: ordered to ({spot[0]:.0f},{spot[1]:.0f}), which another unit already "
                f"has, and it cannot reach anywhere clear of it - spot dropped, it picks its own"
            )
            continue
        entry["position"] = moved
        settled.append((moved[0], moved[1], radius))
        corrections.append(
            f"{name}: ordered to ({spot[0]:.0f},{spot[1]:.0f}), where another unit is already "
            f"going - shifted {((moved[0] - spot[0]) ** 2 + (moved[1] - spot[1]) ** 2) ** 0.5:.1f}\" "
            f"to ({moved[0]:.0f},{moved[1]:.0f}) so both units fit"
        )
    return corrections


def _pushed_clear(spot, radius, settled):
    """`spot` moved just clear of every spot in `settled`, or None if it already
    is. Each pass shoves it directly away from whatever it still overlaps.

    Bounded rather than run to a fixed point: on a crowded flank pushing clear
    of one spot can push into another, and an unbounded loop there is the one
    way this could stall a turn. A spot still touching after the last pass is
    accepted anyway - it is a target point for the mover, not a placement, and
    the mover already clamps units apart when they arrive. For the same reason
    a shifted point is not re-checked against the board edge: a target outside
    it just means "go as far that way as you legally can"."""
    x, y = spot
    for _ in range(_SEPARATION_PASSES):
        worst = 0.0
        for sx, sy, sradius in settled:
            dx, dy = x - sx, y - sy
            gap = (dx * dx + dy * dy) ** 0.5
            needed = radius + sradius + _ORDER_COLLISION_MARGIN_IN
            if gap >= needed:
                continue
            worst = max(worst, needed - gap)
            if gap < 1e-6:
                # Ordered to the very same point - no direction to push along, so
                # pick one. Deterministic on purpose: a random nudge would make
                # the same plan produce different turns.
                dx, dy, gap = 1.0, 0.0, 1.0
            x += dx / gap * (needed - gap)
            y += dy / gap * (needed - gap)
        if worst == 0.0:
            break
    if abs(x - spot[0]) < 1e-6 and abs(y - spot[1]) < 1e-6:
        return None
    return (x, y)


def _planned_squad_coverage(plan, player, state):
    """How many of the plan's orders name a squad this player actually has.

    The floor under the revision retry in _run_turn_plan(). Counting ENTRIES
    would not do: the failure this exists to catch was a revision whose whole
    unit_plans was one entry literally named "placeholder", which is a full
    entry and zero coverage."""
    names = {s.name for s in _all_squads(state.tokens) if s.owner == player}
    names.update(s.name for s in getattr(state, "reserves", ()) if s.owner == player)
    names.update(s.name for s in state.embarked_squads if s.owner == player)
    return sum(1 for name in plan.get("unit_plans", {}) if name in names)


def _run_turn_plan(agent, build_observation, out, recheck=None, coverage=None):
    """Thread body for _maybe_generate_turn_plan(). Never raises into the
    thread - a network error, a timeout, or a malformed tool call all come
    back as out["error"] so the caller can log it and play on.

    `recheck` returns the impossible-order strings for a finished plan. If it
    finds any, the plan goes back to the planner ONCE with those strings
    attached. Deliberately in here rather than on the main thread: the second
    call is another multi-second request, and the game has to keep rendering
    through it exactly as it does through the first."""
    try:
        # Built in here rather than by the caller. The covered-position sweep
        # measured 585 ms of a 637 ms observation build - a third of a second of
        # frozen window every turn, which is the very thing threading the
        # planner was meant to stop. Same safety argument as `recheck`: this
        # only reads geometry, and the AI is standing still waiting for its own
        # plan, so nothing moves underneath it.
        observation = build_observation()
        out["observation"] = observation
        plan = connection.ask(agent.plan_turn, observation)
        problems = list(recheck(plan)) if recheck else []
        # A stub plan goes back to the planner too, not just into a warning.
        # It is structurally valid, so nothing downstream rejects it - but every
        # unit then acts on an order with no reasoning behind it, which is worse
        # than a plan with one bad coordinate.
        if plan.get("malformed") and plan.get("unit_plans"):
            problems.append(
                "the orders came back as a placeholder - every unit needs its own "
                "reason explaining why THAT unit does THAT thing this turn"
            )
        if problems:
            out["problems"] = problems
            # Guarded separately from the first call: by this point there IS a
            # usable plan, and a timeout or a network error while polishing it
            # must not throw it away. Losing one coordinate to the clamp is a
            # small cost; losing every order for every squad is a whole turn
            # played blind.
            try:
                revised = connection.ask(agent.plan_turn, observation,
                                         problems=problems)
                # Two conditions, and the second one is the important one.
                #
                # "Fewer problems" alone is a criterion that REWARDS deleting
                # orders: every problem is attached to a named squad, so a plan
                # that names no real squad scores a perfect zero. Observed for
                # real - a first plan with orders for all twelve units and three
                # fixable coordinates was replaced by a revision whose entire
                # unit_plans was one entry called "placeholder" at (0,0). It
                # scored 0 < 3, was accepted, and the turn ran with no orders at
                # all while the log said "it re-planned".
                #
                # So coverage is a floor, never traded away: a revision has to
                # still speak for as many of this army's squads as the original
                # did. Losing one coordinate to the clamp is cheap; losing every
                # order for every squad is the whole turn.
                fixed_more = len(list(recheck(revised))) < len(problems)
                covers_enough = coverage is None or coverage(revised) >= coverage(plan)
                if fixed_more and covers_enough:
                    plan = revised
                    out["revised"] = True
                elif fixed_more:
                    # Its own key, not revision_error: that one means the second
                    # CALL failed, and the caller words it that way.
                    out["revision_rejected"] = (
                        f"it answered with orders for {coverage(revised)} of this army's "
                        f"squads instead of {coverage(plan)}"
                    )
            except Exception as exc:  # noqa: BLE001
                out["revision_error"] = f"{type(exc).__name__}: {exc}"
        out["plan"] = plan
    except Exception as exc:  # noqa: BLE001 - the whole point is to not crash the game
        out["error"] = f"{type(exc).__name__}: {exc}"


def _validate_turn_plan(plan, player, state, turn_tracker, game_log=None):
    """Correct the orders the RULES make impossible, using the engine itself
    as the authority - then log every correction.

    Why this exists at all (user: "Ich gehe eigentlich davon aus, dass der
    Planner alle Regeln kennt. Ich verstehe nicht, warum es da Luecken gibt"):
    the planner does not read the codebase. It knows exactly what the
    observation JSON and the system prompt tell it, and nothing else. The
    tactical layer never has this problem because its options are GENERATED
    by the engine (`available_actions`) - an illegal action simply never
    appears, so it cannot be chosen. The planner writes free-form orders
    instead, so it can always write an impossible one, and every rule taught
    only as prompt text is a rule it can forget.

    Patching that rule-by-rule (a new observation field each time one is
    reported) closes the reported gap and guarantees the next one. This
    closes the CLASS instead: whatever the plan says, the engine's own
    predicates get the last word before any of it is acted on. Prompt text
    and observation fields stay - they make the planner write better plans -
    but they are no longer what makes a plan legal."""
    if not plan or not plan.get("unit_plans"):
        return plan

    squads_by_name = {s.name: s for s in _all_squads(state.tokens)}
    for squad in list(getattr(state, "reserves", ())) + list(state.embarked_squads):
        squads_by_name.setdefault(squad.name, squad)
    # Rule 20.04: a unit arriving from Reserves is SET UP, not moved - where it
    # can appear has nothing to do with its Move characteristic. Its models
    # still exist as Tokens, but their coordinates are inert leftovers from
    # scene setup that never meant a board position (ai/observation.py's
    # squad_summary() already refuses to report them for exactly this reason).
    # The position clamp below did read them, and that is what put both
    # reserve units in the reported game into a corner: the planner ordered
    # the Deffkoptas to (49,25) next to the Kroot and the Tankbustas to
    # (15,35) within Rokkit range of the Ghostkeel, and the clamp measured
    # both against leftovers sitting at the origin - "ordered to (49,25), 54"
    # away but moves 12" - clamped to (11,5)" and "ordered to (15,35), 37"
    # away but moves 6" - clamped to (2,6)". Both landed there and did
    # nothing, which is the reported "wieder irgendwo hinten platziert, wo sie
    # keinen impact haben"; it also masked DEEP STRIKE entirely, since the
    # landing sweep ranks its candidates by distance to the planned spot.
    reserve_ids = {id(s) for s in getattr(state, "reserves", ())}

    corrections = []
    matched = 0
    clamped_names = set()
    for name, entry in plan["unit_plans"].items():
        squad = squads_by_name.get(name)
        if squad is None:
            # Used to be a silent `continue`, which is how a plan whose only
            # entry was named "placeholder" got carried all the way through
            # without a single line saying the turn had no orders. An order for
            # a unit that does not exist is worth exactly one log line.
            corrections.append(f"{name}: no such unit - order ignored")
            continue
        matched += 1
        role = entry.get("role")

        # Rule 20.03: Strategic Reserves cannot arrive before a set round.
        if role == "reserve_commit" and turn_tracker.battle_round < INGRESS_MIN_BATTLE_ROUND:
            entry["role"] = "reserve"
            # The reason goes with the role. See the over-garrison pass below
            # for the reported failure this prevents: _handle_movement() hands
            # the whole entry to the tactical layer as plan_context, so a
            # reason still arguing to arrive this turn outranks the field that
            # says it cannot.
            entry["reason"] = (
                f"Stays in Strategic Reserves - rule 20.03 allows no arrival before battle "
                f"round {INGRESS_MIN_BATTLE_ROUND}, and this is round {turn_tracker.battle_round}."
            )
            corrections.append(
                f"{name}: 'reserve_commit' in battle round {turn_tracker.battle_round} "
                f"-> 'reserve' (rule 20.03: no arrival before round {INGRESS_MIN_BATTLE_ROUND})"
            )
            continue

        # The named target may simply not be there any more. This is the
        # staleness a once-per-turn plan cannot see: it is written in the
        # Movement phase and still being read in Shooting, Charge and Fight,
        # by which time the unit it names can be dead. Checked at every phase
        # boundary (see _revalidate_plan_for_phase()), so the plan cleans
        # itself up as the turn goes on instead of steering squads at a unit
        # that no longer exists.
        named = entry.get("target")
        if named and _squad_by_name(named, state.tokens) is None \
                and not any(o.name == named for o in state.objectives):
            entry["target"] = None
            corrections.append(f"{name}: target {named} is no longer on the battlefield -> target dropped")
            continue

        # A named position has to be reachable THIS turn. Objectives and enemy
        # units carry "turns_to_reach"; a bare coordinate carries nothing, so
        # position_x/position_y quietly bypassed the whole one-turn-horizon
        # discipline. Observed: Stormboyz (12" move) ordered to a point 17"
        # away - 1.4 turns - walked their full move in the right direction and
        # stopped halfway across open ground, which is the worst place to be
        # and a spot the plan never evaluated because it reasoned about the
        # destination rather than the waypoint. Clamped onto the reachable part
        # of the same line: the unit still goes where the plan was heading, and
        # the plan's own exposure reasoning now applies to a point it reaches.
        # THE MIRROR OF THE CLAMP BELOW: an ACTIVE order to a point the unit is
        # already standing AROUND. Measured on the reported board, all 74
        # models where the log leaves them: the 21-model Necron blob ordered to
        # (34,8) - 1.97" from its centroid and inside its own formation - moved
        # 0.00", while the same blob on the same board ordered to points
        # outside its formation moved 2.50" and 4.72". Nothing was stuck: the
        # models on the far side of the spot would have had to walk backwards
        # into their own squadmates, so every rung of _advance_toward()'s
        # ladder came back with nothing and the unit spent its move on a no-op.
        #
        # ONLY FOR AN ACTIVE ROLE, and that is the whole scope of this check.
        # A PASSIVE role - hold/screen/stage - plus a coordinate inside the
        # formation says "stay where you are", which is a coherent order the
        # unit carries out correctly by standing still; dropping it there would
        # be this pass overruling an intent the planner really had. That is
        # also what the reported turn actually was: role "hold" next to a
        # reason describing a reposition. The unit obeyed the field, which is
        # the right half to obey - what frees it is the over-garrison pass
        # below, which has a rule saying it must leave.
        #
        # The order is DROPPED rather than replaced, for the reason every other
        # check in this file drops one: a coordinate is picked for a property,
        # and this code cannot pick a replacement that serves a purpose it
        # cannot see. Without one the movement options come from the engine and
        # are legal by construction - and the unit gets its real options back,
        # since a named position also suppresses the Advance and the
        # move-to-target ones (see _handle_movement()). That is the actual cost
        # of the no-op: not that it fails, but that it crowds out the rest.
        spot = entry.get("position")
        if spot is not None and squad.models and id(squad) not in reserve_ids \
                and entry.get("role") not in ("hold", "screen", "stage") \
                and geometry.point_inside_hull(spot, [(m.x_in, m.y_in) for m in squad.models]):
            entry["position"] = None
            entry["reason"] = (
                f"{entry.get('reason') or ''} (The ordered position was inside this unit's own "
                f"formation, so it was already there and the coordinate was dropped - move it "
                f"somewhere it is not already standing, or leave it be.)").strip()
            corrections.append(
                f"{name}: ordered to ({spot[0]:.0f},{spot[1]:.0f}), which is inside its own "
                f"formation - it is already standing there, so the position was dropped "
                f"(a {len(squad.models)}-model unit cannot move onto a point in its own middle)"
            )

        spot = entry.get("position")
        if spot is not None and squad.models and id(squad) not in reserve_ids:
            # Advance counted in: clamping to the flat Move characteristic
            # made rule 09.06 unaskable-for. See _reach_to_point().
            gap, reach = _reach_to_point(squad, spot, allow_advance=True)
            if gap > reach:
                # Projected from the same origin the gap was measured from -
                # see _reach_origin(). For a passenger these used to disagree
                # by the distance between its stale coordinates and its
                # transport, which put the clamped point somewhere neither the
                # planner nor the check had ever evaluated.
                #
                # For a unit on the board the shortened point is THE FIRST LEG
                # toward the ordered spot, from ai/observation.py - the same
                # helper that offers the planner a first leg toward every
                # distant goal, so "clamped" and "offered" are one point (and
                # it is nudged off walls and the board edge the same way). A
                # passenger keeps the plain projection: its leg starts at its
                # transport, which first_leg_toward() does not model.
                cx, cy = _reach_origin(squad)
                dx, dy = spot[0] - cx, spot[1] - cy
                span = (dx * dx + dy * dy) ** 0.5
                leg = None
                if getattr(squad, "embarked_in", None) is None:
                    leg = observation.first_leg_toward(squad, spot, reach, state.obstacles)
                if leg is not None:
                    entry["position"] = (leg["x"], leg["y"])
                    clamped_names.add(name)
                    corrections.append(
                        f"{name}: ordered to ({spot[0]:.0f},{spot[1]:.0f}), {gap:.0f}\" away but "
                        f"moves {reach:.0f}\" - clamped to "
                        f"({entry['position'][0]:.0f},{entry['position'][1]:.0f}), "
                        f"as far along that line as it can actually reach this turn"
                    )
                elif span > 1e-9:
                    scale = reach / span
                    entry["position"] = (cx + dx * scale, cy + dy * scale)
                    clamped_names.add(name)
                    corrections.append(
                        f"{name}: ordered to ({spot[0]:.0f},{spot[1]:.0f}), {gap:.0f}\" away but "
                        f"moves {reach:.0f}\" - clamped to "
                        f"({entry['position'][0]:.0f},{entry['position'][1]:.0f}), "
                        f"as far along that line as it can actually reach this turn"
                    )

        # THE THIRD ORDER SHAPE, and the one the retry channel used to CREATE:
        # a reachable position that walks AWAY from the order's own goal.
        # Measured on logs/game_20260909_210843.log: Canoptek Wraiths at (34,4)
        # with a 10" move, goal "Push toward Central Objective" at (30,22).
        # The first order, (25,20), was 17" away and went back to the planner
        # (that channel is gone now - see _problems_for_the_planner()); the
        # revision ordered (44,7), which is reachable and 20.5" from the
        # objective where the unit stood 18.4" from it. The unit moved
        # backwards, exactly as ordered, and the reason text still said
        # "push toward". Nothing in the validator compared the order with its
        # own goal.
        #
        # Only for an ACTIVE role, only while the goal is beyond a plain move
        # (a unit already within reach of its goal that repositions a little
        # further from it is fine-tuning - out of a charge arc, into a firing
        # line - and this pass has no business overruling that), and only by
        # a margin (_BACKWARD_ORDER_TOLERANCE_IN). The replacement is the
        # first leg toward the goal from ai/observation.py - the SAME point
        # the observation offered the planner for that goal, so the order the
        # unit gets is one the planner could have written itself. Advance
        # band preserved: an order that needed an Advance keeps its Advance.
        # A passenger is skipped - its leg would start at its transport, and
        # first_leg_toward() measures from the models.
        spot = entry.get("position")
        if spot is not None and squad.models and id(squad) not in reserve_ids \
                and getattr(squad, "embarked_in", None) is None \
                and entry.get("role") not in ("hold", "screen", "stage"):
            goal, goal_name = _order_goal_point(entry, squad, state)
            if goal is not None:
                origin = _reach_origin(squad)
                plain = min_model_movement(squad)
                stands = math.dist(origin, goal)
                ordered = math.dist(spot, goal)
                if stands > plain and ordered > stands + _BACKWARD_ORDER_TOLERANCE_IN:
                    advancing = math.dist(origin, spot) > plain
                    reach = observation.advance_reach_in(squad) if advancing else plain
                    leg = observation.first_leg_toward(squad, goal, reach, state.obstacles)
                    if leg is None:
                        entry["position"] = None
                        entry["reason"] = (
                            f"{entry.get('reason') or ''} (The ordered position at "
                            f"({spot[0]:.0f},{spot[1]:.0f}) was further from {goal_name} than "
                            f"this unit already stood, and no legal point lies on the line toward "
                            f"it, so the coordinate was dropped - move toward {goal_name}.)").strip()
                        corrections.append(
                            f"{name}: ordered to ({spot[0]:.0f},{spot[1]:.0f}), {ordered:.0f}\" from "
                            f"{goal_name} while it stands {stands:.0f}\" from it - a step backwards, "
                            f"and no legal point lies on the line toward it -> position dropped"
                        )
                    else:
                        entry["position"] = (leg["x"], leg["y"])
                        clamped_names.add(name)
                        entry["reason"] = (
                            f"{entry.get('reason') or ''} (The ordered position at "
                            f"({spot[0]:.0f},{spot[1]:.0f}) was further from {goal_name} than "
                            f"this unit already stood, so it was replaced by the first leg toward "
                            f"{goal_name} at ({leg['x']:.0f},{leg['y']:.0f}).)").strip()
                        corrections.append(
                            f"{name}: ordered to ({spot[0]:.0f},{spot[1]:.0f}), {ordered:.0f}\" from "
                            f"{goal_name} while it stands {stands:.0f}\" from it - a step backwards, "
                            f"replaced by the first leg toward it, ({leg['x']:.0f},{leg['y']:.0f})"
                            + (", Advancing" if advancing else "")
                        )

        # Rule 24.24 (LONE OPERATIVE): naming a target this squad could not
        # get within shooting range of all turn is an order that can never be
        # carried out. Reported AFTER the observation field and the prompt
        # rule for exactly this were already in place ("der Planner hat immer
        # noch die Stealth Suits angewiesen, auf den Ghostkeel zu schiessen,
        # obwohl sie ihn mit Lone Op gar nicht erreichen koennen") - which is
        # the whole argument for this function existing: a rule taught only
        # as prompt text stays optional, a rule checked here does not.
        target = _squad_by_name(entry.get("target"), state.tokens) if entry.get("target") else None
        lone_range = status_effects.lone_operative_range(target) if target is not None else None
        if lone_range is not None and squad.models:
            gap = squad.min_distance_to(target) - min_model_movement(squad)
            if gap > lone_range:
                entry["target"] = None
                corrections.append(
                    f"{name}: target {target.name} has LONE OPERATIVE {lone_range:.0f}\" and cannot "
                    f"be reached this turn ({gap:.1f}\" short even after moving) -> target dropped "
                    f"(rule 24.24)"
                )
            elif entry.get("position") is not None:
                # The target IS reachable, but the order also says where to
                # stand - and rule 24.24 is about where the shooter stands.
                # Reported case: Deffkoptas sent to (26,8) to shoot a Ghostkeel
                # 15.8" from there. See _unshootable_from_position_problems(),
                # which offers the planner the chance to fix this itself first;
                # this is the backstop for when it does not.
                #
                # The TARGET is dropped rather than the position, deliberately.
                # The position is achievable and was picked for a reason this
                # code cannot see (the order's own words were "while staying out
                # of easy charge range"); the shot from it is the impossible
                # half. Without a plan target the tactical layer picks its own,
                # and its options come from valid_target_models(), so whatever
                # it shoots is legal by construction.
                spot = entry["position"]
                stand_off = _distance_from_squad_to_point(target, spot) - _squad_half_width(squad)
                if stand_off > lone_range:
                    entry["target"] = None
                    corrections.append(
                        f"{name}: ordered to stand at ({spot[0]:.0f},{spot[1]:.0f}), which is "
                        f"{stand_off:.0f}\" from {target.name} - it has LONE OPERATIVE "
                        f"{lone_range:.0f}\" and cannot be shot at from there -> target dropped "
                        f"(rule 24.24)"
                    )

        # Rules 18.04/18.05: getting out has to accomplish something this
        # turn. Both predicates below are the SAME ones the Movement phase
        # already uses to decide whether to even offer the choice, so this
        # cannot disagree with what the tactical layer would do.
        if role == "disembark":
            transport = squad.embarked_in
            if transport is None:
                entry["role"] = "hold"
                entry["reason"] = (
                    "Ordered to disembark, but this unit is not aboard anything - it is already "
                    "on the battlefield. Hold and use it from where it stands."
                )
                corrections.append(f"{name}: ordered to disembark but is not embarked -> 'hold'")
                continue
            predicted = _predict_squad_positions_from_point(
                squad, transport.x_in, transport.y_in,
                transport.radius_in + DISEMBARK_MODEL_GAP_IN, state.tokens, toward_enemy=True,
            )
            has_target = _has_target_after_disembark(
                squad, predicted, state.tokens, state.obstacles, state.terrain_areas)
            takes_objective = _reaches_objective_after_disembark(squad, predicted, state.objectives)
            if not has_target and not takes_objective:
                entry["role"] = "stage"
                entry["reason"] = (
                    "Stays aboard its transport - disembarking here would leave it with nothing "
                    "to shoot and no objective in reach this turn (rules 18.04/18.05)."
                )
                corrections.append(
                    f"{name}: ordered to disembark with nothing to shoot and no objective in "
                    f"reach -> 'stage' (stays aboard; rules 18.04/18.05)"
                )

    # Rule 14.01-14.02: more than one unit parked on an objective nobody is
    # contesting. Done after the per-entry loop because it is the only check
    # here that is about the plan as a WHOLE - no single order is wrong, it is
    # the third one on the same objective that is - and because it has to read
    # the positions the loop above may just have clamped.
    #
    # See _over_garrison_problems() for why this is enforced rather than
    # explained: this is the third report of it, and the previous two answers
    # were a prompt paragraph and a pair of observation fields, both of which
    # the planner then had in front of it while doing it again.
    for objective, keepers, freed in _garrison_surplus(plan, squads_by_name, state, player):
        for squad in freed:
            entry = plan["unit_plans"].get(squad.name)
            if entry is None:
                continue
            # An embarked unit is not standing on anything (rule 18.02) and is
            # never in `squads`, so nothing here can order a passenger out - a
            # disembark has its own conditions two blocks up.
            had_role = entry.get("role")
            had_spot = entry.get("position")
            entry["role"] = "advance"
            # The position is dropped rather than replaced. It was the
            # redundant garrison spot, and the argument every other check in
            # this file rests on applies unchanged: a coordinate is picked for
            # a property, and this code cannot pick a replacement that serves
            # a purpose it cannot see. Without one, the movement options come
            # from the engine (see _handle_movement()), so whatever the
            # tactical layer does instead is legal by construction. `target`
            # stays - it governs shooting and charging, not where to stand.
            entry["position"] = None
            # AND THE REASON, which is the half that was missing. Reported as
            # "die necron warriors sind nicht aus der eigenen deployment zone
            # rausgekommen. war das der plan? die sollten lieber nach vorne
            # marschieren." - and the log shows this very correction firing on
            # them ("role 'hold' -> 'advance' and garrison spot (30,7)
            # dropped"), followed by "Player 2 has 2 Necron Warriors 1 +
            # Technomancer remain stationary."
            #
            # The role was rewritten and the reason was not, so the entry that
            # reached the tactical layer said role='advance' next to "cheapest
            # way to keep holding it is to leave this big blob here as
            # garrison since it's already in place; stay Hidden and do not
            # fire" - and _handle_movement() hands the WHOLE entry over as
            # plan_context, reason included. It obeyed the sentence, not the
            # field. ai/planner_prompt.py already warns the planner about
            # exactly this hazard for the "disembark" role ("on the role, not
            # on your reason"); nothing was enforcing it on the corrections
            # this file makes itself.
            #
            # Replaced rather than appended to: the old text is the problem,
            # and a reason that argues both ways is not better than one that
            # argues the wrong way.
            entry["reason"] = (
                f"Freed from garrisoning {objective.name} - "
                + ", ".join(s.name for s in keepers)
                + " already out-controls anything the enemy can bring onto it (rules 14.01-14.02: "
                "control is the higher OC total, not how many units are present). Move this unit "
                "forward and put its points to work somewhere the game is being decided."
            )
            # Says what actually changed rather than a fixed phrase. The
            # reported Kill Rig is why: its role was ALREADY "advance" and only
            # the coordinate parked it, so a blanket "-> 'advance'" would have
            # read as a no-op on the one order whose rewrite mattered most, and
            # sent the next investigation looking at roles.
            did = []
            if had_role != "advance":
                did.append(f"role '{had_role}' -> 'advance'")
            if had_spot is not None:
                did.append(f"garrison spot ({had_spot[0]:.0f},{had_spot[1]:.0f}) dropped")
            corrections.append(
                f"{squad.name}: {' and '.join(did) or 'freed'} - "
                f"{len(keepers) + len(freed)} of our units were left standing on "
                f"{objective.name} (rules 14.01-14.02: control is the higher OC total, and "
                + ", ".join(s.name for s in keepers)
                + " already out-controls anything the enemy can bring onto it)"
            )

    # Rule 14.01-14.02 again, for the case the pass above cannot see: ONE unit
    # on an uncontested objective, but the wrong one. Reported as "die 20 boyz
    # wurden gerade auf dem home objective geparkt, obwohl die KI auch 2
    # gretchin trupps hat" - the count test never fires on a single unit, so a
    # 170-point mob held ground a 45-point one holds identically.
    #
    # The job is MOVED rather than just dropped, which is the difference from
    # the over-garrison pass: there, another unit was already standing there to
    # hold it, so freeing one changed nothing about control. Here, freeing the
    # holder without sending anyone else gives the objective away, so the
    # replacement is ordered onto it in the same breath.
    for objective, holder, replacement in _lone_garrison_swaps(
        plan, squads_by_name, state, player, shortened=clamped_names
    ):
        held = plan["unit_plans"].get(holder.name)
        if held is None:
            continue
        centre = _objective_centre(objective)
        taker = plan["unit_plans"].setdefault(replacement.name, {})
        taker["role"] = "hold"
        taker["position"] = centre
        taker["reason"] = f"Hold {objective.name} - the cheapest unit that can."
        had_role = held.get("role")
        had_spot = held.get("position")
        held["role"] = "advance"
        # Dropped, not replaced - the same reasoning as the over-garrison pass:
        # a coordinate is picked for a property, and this code cannot pick a
        # replacement that serves a purpose it cannot see. Without one the
        # movement options come from the engine and are legal by construction.
        held["position"] = None
        # Same stale-reason fix as the over-garrison pass above, and this site
        # is where the asymmetry was most visible: the REPLACEMENT already got
        # a fresh reason written for it two lines up, while the unit being
        # freed kept the sentence explaining why it should stay.
        held["reason"] = (
            f"Freed from garrisoning {objective.name} - {replacement.name} takes that job "
            f"instead (rules 14.01-14.02: control is the higher OC total). Move this unit "
            f"forward and put its points to work somewhere the game is being decided."
        )
        did = []
        if had_role != "advance":
            did.append(f"role '{had_role}' -> 'advance'")
        if had_spot is not None:
            did.append(f"garrison spot ({had_spot[0]:.0f},{had_spot[1]:.0f}) dropped")
        corrections.append(
            f"{holder.name}: {' and '.join(did) or 'freed'} - it was garrisoning {objective.name} "
            f"alone with no enemy within {observation.GARRISON_THREAT_RANGE_IN:.0f}\", and "
            f"{replacement.name} is better suited to it and can reach it this turn, so the "
            f"garrison job goes to it instead (rules 14.01-14.02: control is the higher OC total)"
        )

    # Two of our own squads sent to the same ground. Last, so it sees the
    # positions the clamp above may have shortened and the ones the garrison
    # pass may have dropped - resolving collisions between coordinates that are
    # about to change would separate spots nobody ends up using.
    corrections.extend(_separate_colliding_positions(plan, squads_by_name))

    if not matched:
        # Every order was for a unit this army does not have, so the turn has no
        # coordination at all - exactly the state `malformed` exists to announce,
        # reached by a route _sanitize_turn_plan() cannot see (it has no game
        # state, so it cannot know whether "placeholder" is a squad). Setting it
        # here is what makes the caller's existing loud WARNING fire.
        plan["malformed"] = True
    if corrections and game_log is not None:
        for line in corrections:
            game_log.add(f"{player}: turn plan corrected - {line}")
    return plan


def _maybe_generate_turn_plan(agent, memory, player, state, turn_tracker, game_log, on_thinking,
                              last_ranged_attack_turn=None, mission_controller=None,
                              waaagh_controller=None):
    """The strategic planning phase (ai/claude_agent.py's
    PLANNER_SYSTEM_PROMPT/plan_turn()): once per the player's own turn,
    before the first real Movement-phase decision, ask for a short turn plan
    and cache it on `memory` for the rest of the turn (Movement->Shooting->
    Charge->Fight) - see AIMemory._sync_turn_plan(). A no-op (no API call) on
    every later call this same turn, mirroring _choose()'s own "nothing to
    decide, don't call the agent" cheapness. Advisory only - see
    _movement_priority_key()'s `plan` param and _handle_movement()'s own
    `plan_context` construction for how it's actually used.

    Real, severe bug found via user report ("ich verstehe nicht, warum sie
    vorher nicht näher an meine squads rangelaufen sind... vielleicht müssen
    die pläne für die einzelnen einheiten detaillierter sein. statt 'central
    objective support' sollte da eher stehen 'move kroot to enemy kroot 1
    unit, fire and charge it'"): this used to hand the planner ONLY the
    player's own squads, even though PLANNER_SYSTEM_PROMPT explicitly
    promises it "every enemy squad the same way". The planner was therefore
    blind to the entire enemy army - it could not name an enemy unit as a
    target because, as far as its observation went, none existed. Every plan
    it could possibly produce had to be phrased in terms of the only things
    it COULD see (its own units and the objectives), which is exactly the
    vague, objective-only planning the user is describing. Fixed by passing
    every squad on the board, both players' (squad_summary() already carries
    `owner`, so the planner can tell them apart). Own reserves stay own-only
    on purpose - the enemy's reserves are hidden information, not something
    the planner is entitled to see."""
    memory._sync_turn_plan(turn_tracker)
    if memory.turn_plan is not None and not memory.replan_requested:
        return

    on_board_squads = list(_all_squads(state.tokens))
    own_squads = [s for s in on_board_squads if s.owner == player]
    reserve_squads = [s for s in state.reserves if s.owner == player]
    # Rule 18.02: an embarked squad is off the battlefield, so it never
    # appears in state.tokens and was invisible to the planner - which is
    # why it had nothing to say about the Devilfish's cargo (user report:
    # "ich glaube nicht, dass sie weiß, dass im devilfish breacher stecken").
    # Own passengers only, for the same reason own reserves are: what's
    # inside the opponent's transport is hidden information.
    embarked_squads = [s for s in state.embarked_squads if s.owner == player]
    if not own_squads and not reserve_squads and not embarked_squads:
        memory.turn_plan = {"turn_intent": "", "unit_plans": {}}
        return

    # Run the call on a background thread and return immediately.
    #
    # This used to be a plain blocking call, which meant the pygame loop
    # stopped pumping events for its whole duration - no rendering, no
    # response to input, and Windows marking the window "not responding".
    # With a stronger planning model and a big observation that is tens of
    # seconds, and on a stalled connection it was the SDK's ten-minute
    # default (user report: "jetzt hat sich das spiel aufgehängt als der
    # planner aktiv war"). The turn genuinely cannot start without its plan,
    # so the AI still waits - but the WINDOW no longer does.
    if memory.turn_plan_thread is None:
        build_observation = lambda: build_planning_observation(  # noqa: E731 - thread body
            on_board_squads, reserve_squads, turn_tracker, player, objectives=state.objectives,
            embarked_squads=embarked_squads, obstacles=state.obstacles, terrain_areas=state.terrain_areas,
            last_ranged_attack_turn=last_ranged_attack_turn,
            mission_controller=mission_controller, waaagh_controller=waaagh_controller,
        )
        memory.turn_plan_result = {}
        memory.turn_plan_thread = threading.Thread(
            target=_run_turn_plan,
            args=(agent, build_observation, memory.turn_plan_result),
            # Reads squad positions only, and only while the AI is standing
            # still waiting for its own plan - nothing moves during the call.
            kwargs={
                "recheck": lambda p: _problems_for_the_planner(p, player, state),
                "coverage": lambda p: _planned_squad_coverage(p, player, state),
            },
            daemon=True,
        )
        memory.turn_plan_thread.start()
        if game_log is not None and memory.turn_plan is None:
            game_log.add(f"{player} is planning its turn...")
        return

    if memory.turn_plan_thread.is_alive():
        return  # still thinking - the caller sees no plan yet and holds off

    memory.turn_plan_thread = None
    result = memory.turn_plan_result or {}
    memory.turn_plan_result = None
    if "error" in result:
        # Play the turn unplanned rather than blocking on it forever. Every
        # _planned_* lookup already tolerates a missing plan (that's the
        # pre-planner code path), so this degrades rather than breaking.
        memory.turn_plan = {"turn_intent": "", "unit_plans": {}}
        if game_log is not None:
            game_log.add(f"{player}: WARNING - turn planning failed ({result['error']}); playing this turn without a plan.")
        return
    # Kept so the threat log below can report the numbers the plan was actually
    # written against; produced by the thread along with the plan itself.
    memory.plan_observation = result.get("observation")
    if game_log is not None and result.get("problems"):
        # Whether sending it back worked is a question about the PLANNER, so it
        # has to be answerable from the log rather than assumed. Either line
        # says which orders were impossible; "re-planned" means it found its own
        # replacement, "kept" means it did not and the clamp below takes over.
        outcome = (
            "re-planned" if result.get("revised")
            else f"could not be reached ({result['revision_error']})" if result.get("revision_error")
            # Loud on purpose: this is the revision being REFUSED, which is the
            # difference between "the planner had nothing better" and "the
            # planner tried to answer by deleting the plan".
            else f"was REJECTED - {result['revision_rejected']}" if result.get("revision_rejected")
            else "kept its original orders"
        )
        game_log.add(
            f"{player}: turn plan had {len(result['problems'])} order(s) only the planner can fix, "
            f"sent back to it - it {outcome}.", file_only=True,
        )
        for problem in result["problems"]:
            game_log.add(f"  [plan problem] {problem}", file_only=True)
    memory.turn_plan = _validate_turn_plan(result["plan"], player, state, turn_tracker, game_log)
    # Baseline for the "an enemy unit died" trigger - taken when the plan is
    # written, so it measures change since THIS plan, not since the turn began.
    memory.plan_enemy_snapshot = {s.name for s in _all_squads(state.tokens) if s.owner != player}
    memory.replan_requested = False
    if game_log is not None and memory.turn_plan.get("turn_intent"):
        game_log.add(f"{player} turn plan: {memory.turn_plan['turn_intent']}")
    if game_log is not None and memory.turn_plan.get("malformed"):
        # Loud, because the alternative is a whole turn played blind: every
        # unit falls back to "no plan entry", the threat/score/terrain data goes
        # unread, and nothing in the log said so.
        game_log.add(
            f"{player}: WARNING - the turn plan came back unusable "
            f"({len(memory.turn_plan.get('unit_plans') or {})} unit orders); "
            "this turn runs WITHOUT a plan."
        )
    if game_log is not None and memory.turn_plan.get("truncated"):
        # User report: "in zug 2 hat der thinking layer irgendwie die strike
        # teams vergessen" - it hadn't; the plan hit max_tokens mid-tool-call
        # and everything after the cut (both Strike Teams, alphabetically
        # last) was simply missing. Silent before this line existed.
        game_log.add(
            f"{player}: WARNING - the turn plan was cut off at the token limit; "
            "some squads have no orders this turn."
        )
    if game_log is not None:
        # The per-unit orders were only ever shown in the TurnPlanOverlay,
        # never written to the log - so a "the AI ignored its own plan"
        # report couldn't be checked against what the plan actually said
        # afterwards. File-only: the on-screen log panel already shows the
        # intent, and one line per squad would swamp it.
        for squad_name, entry in sorted(memory.turn_plan.get("unit_plans", {}).items()):
            target = f" -> {entry['target']}" if entry.get("target") else ""
            # Log the position too. Without it a plan that DOES name a spot is
            # indistinguishable from one that doesn't, which made "does the
            # planner ever use coordinates?" unanswerable from the logs - the
            # same observability gap that cost a round of guesswork on charges
            # and on disembarks.
            spot = entry.get("position")
            where = f" @({spot[0]:.0f},{spot[1]:.0f})" if spot else ""
            target = target + where
            reason = f" ({entry['reason']})" if entry.get("reason") else ""
            game_log.add(
                f"  [turn plan] {squad_name}: {entry['role']}{target}{reason}",
                file_only=True,
            )

    # The threat/trade numbers the plan was written against, so a questionable
    # plan can be checked after the game against what the planner was actually
    # looking at (user: "ergaenze bitte auch die gefahrenberechnung im log,
    # damit du sie fuer untersuchungen nach dem spiel auslesen kannst").
    # File-only: this is several lines per squad, far too much for the on-screen
    # panel, and only ever wanted when reading the log back.
    if game_log is not None:
        for entry in (memory.plan_observation or {}).get("squads", []):
            # A passenger carries the same numbers under a different key (its
            # decision is "get out or not", not "stand here or not"), and used
            # to be skipped entirely - so the units this line exists to explain
            # were the one kind it never covered.
            assessment = entry.get("threat_assessment") or entry.get("if_you_disembark")
            if not assessment:
                continue
            aboard = entry.get("if_you_stay_aboard")
            where = "here"
            if "if_you_disembark" in entry:
                where = "if it gets out"
            worst = ", ".join(
                f"{t['unit']} {t['kills_per_turn']}/turn ({t['via']})"
                for t in assessment["biggest_threats_to_you"]
            ) or "nothing in reach"
            # Reported per attack mode, because that is how the observation
            # states it - a single merged list is what described a Rokkit team
            # as a melee unit (see observation.ranked_targets()). Value first:
            # it is the ranking key, so a log line that led with the casualty
            # count would not explain the order it prints things in.
            targets = assessment["best_targets_for_you"]
            best = " ; ".join(
                f"{how} " + ", ".join(
                    f"{t['unit']} {t['value_you_remove_per_turn']} pts/turn"
                    f" ({t['kills_per_turn']} models"
                    + (f", {t['trade']}" if t.get("trade") else "") + ")"
                    for t in targets[key]
                )
                for key, how in (("best_to_shoot", "by shooting:"),
                                 ("best_to_charge", "by charging:"))
                if targets.get(key)
            ) or "nothing in reach"
            losses = assessment.get("worst_case_losses_per_turn_if_everything_shoots_you")
            if losses is None:
                losses = assessment.get("worst_case_losses_per_turn_if_you_stand_there", 0.0)
            staying = ""
            if aboard:
                staying = (
                    f" | staying aboard: contributes nothing, loses "
                    f"{aboard['models_lost_if_the_transport_dies']} models if its transport dies "
                    f"(transport takes {aboard.get('transport_losses_per_turn', 0)}/turn)"
                )
            game_log.add(
                f"  [threat] {entry['name']}: loses {losses * 100:.0f}%/turn {where}"
                f" | threatened by {worst} | can hit {best}{staying}",
                file_only=True,
            )


def _ere_we_go_gain(squad, all_tokens, movement_controller):
    """How much War Horde's 'Ere We Go (+2 to Advance AND Charge rolls) is
    worth to this unit right now, as (charge-odds gain, closeness).

    The charge half is the one that can be put a number on: with `gap` left
    after moving, the unit needs `gap` on 2D6, and the +2 turns that into
    `gap - 2`. The difference in probability is the gain, and it peaks exactly
    where a charge is a coin-flip - which is where a re-roll-shaped boost is
    worth the most and where the WAAAGH! turn wants it.

    Closeness is the tie-break, not a second term: when nothing is chargeable
    this turn the +2 is purely an Advance bonus, worth the same 2" to anybody,
    so the unit nearest the enemy - the one actually going forward - gets it.
    Both are deterministic; no agent call anywhere in this path."""
    enemies = [s for s in _all_squads(all_tokens) if s.owner != squad.owner and s.models]
    if not enemies:
        return 0.0, 0.0
    gap = min(_squad_distance_between(squad, e) for e in enemies)
    move = min_model_movement(squad)
    needed = max(2, math.ceil(gap - move))
    gain = _charge_roll_probability(needed - ERE_WE_GO_ROLL_BONUS) - _charge_roll_probability(needed)
    return gain, -gap


def _handle_ere_we_go(player, all_tokens, movement_controller, ere_we_go_controller, waaagh_controller,
                      turn_tracker, game_log=None):
    """Buy 'Ere We Go at the first opportunity of the WAAAGH! turn, per the
    user: "auch deterministisch. bei der ersten gelegenheit eines squads im
    waagh zug". Returns True if the CP was actually spent.

    TIMING is the instruction taken literally: the stratagem's WHEN is the
    start of your Movement phase, so the first opportunity in the WAAAGH! turn
    is that phase - and can_use() enforces "nothing of yours has moved yet",
    so this cannot fire late even if it is called late.

    WHICH unit is not left to chance, because rule 15.01 allows exactly one
    use per phase: the eligible unit that gains the most (see
    _ere_we_go_gain()). Restricting it to the WAAAGH! turn is the user's own
    call and a sound one - +2 to Advance AND Charge is worth most in the turn
    the army is already Advancing-and-charging (the Waaagh! army rule lifts
    rule 09.06's ban on charging after an Advance, see game/charge.py), and
    the CP is better kept in any other turn.

    Needs no memory.declined_* memo, like _handle_unbridled_carnage(): the
    choice is a pure function of the board, so a "no" this frame is a "no"
    next frame too, and a "yes" cannot repeat (can_use() refuses once the
    grant is up, and 15.01 refuses a second use this phase)."""
    if ere_we_go_controller is None or waaagh_controller is None or turn_tracker is None:
        return False
    if not waaagh_controller.is_active(player):
        return False
    candidates = [
        s for s in sorted(_all_squads(all_tokens), key=lambda s: s.name)
        if s.owner == player and ere_we_go_controller.can_use(s)
    ]
    if not candidates:
        return False
    best = max(candidates, key=lambda s: _ere_we_go_gain(s, all_tokens, movement_controller))
    if not ere_we_go_controller.use(best):
        return False
    if game_log is not None:
        gain, closeness = _ere_we_go_gain(best, all_tokens, movement_controller)
        game_log.add(
            f"[ere we go] {player}: {best.name} - WAAAGH! turn, {-closeness:.1f}\" from the nearest enemy, "
            f"the +2 improves its charge odds by {gain:.0f} percentage points.",
            file_only=True,
        )
    return True


def _handle_movement(
    agent, memory, player, state, movement_controller, transport_controller, setup_controller,
    game_log, on_thinking, ingress_controller=None, fall_back_controller=None, waaagh_controller=None,
    last_ranged_attack_turn=None, mission_controller=None, ere_we_go_controller=None,
    sudden_storm_controller=None, shooting_controller=None,
):
    all_tokens = state.tokens

    # Strategic planning phase (see ai/claude_agent.py's PLANNER_SYSTEM_PROMPT):
    # generates memory.turn_plan exactly once per own turn, then no-ops on
    # every later call this same turn - see _maybe_generate_turn_plan()/
    # AIMemory._sync_turn_plan(). Deliberately the very first thing this
    # function does, before even the Disembark-resume/auto-Ingress steps
    # below, so a plan is in place before any real movement decision.
    _maybe_generate_turn_plan(
        agent, memory, player, state, movement_controller.turn_tracker, game_log, on_thinking,
        last_ranged_attack_turn=last_ranged_attack_turn, mission_controller=mission_controller,
        waaagh_controller=waaagh_controller,
    )
    if memory.is_planning and memory.turn_plan is None:
        # The FIRST plan of the turn is still in flight on its background
        # thread. A mid-turn re-plan deliberately does not stall anything: the
        # previous plan stays in force until the new one lands, so the turn
        # keeps running on slightly stale orders rather than freezing.
        # Plan still in flight on its background thread. Return True ("acted")
        # rather than False: False is this function's "nothing left to do this
        # phase" signal and would make take_one_action() advance straight past
        # the Movement phase - skipping the entire turn the plan is for.
        return True

    # War Horde's 'Ere We Go (1CP): its WHEN is the START of the Movement
    # phase, so it goes ahead of everything that moves anything - including
    # the Disembark/Ingress resumes below, both of which are movement and
    # would shut the window. Deterministic, so a "yes" costs no agent call and
    # the next frame simply falls straight through it.
    if _handle_ere_we_go(
        player, all_tokens, movement_controller, ere_we_go_controller, waaagh_controller,
        movement_controller.turn_tracker, game_log,
    ):
        return True

    # Awakened Dynasty's Sudden Storm shares 'Ere We Go's window exactly - a
    # Movement-phase Stratagem whose value is spent the moment the unit moves -
    # so it is checked in the same place and for the same reason.
    if _handle_sudden_storm(
        player, all_tokens, movement_controller, sudden_storm_controller,
        shooting_controller, game_log,
    ):
        return True

    # Resume a Disembark Move already in progress: a Combat/Emergency
    # hazard roll (rule 06.03) paused it, a human has since clicked to
    # acknowledge that roll (and any resulting wound allocation - already
    # routed to _resolve_own_damage_choice() via transport_controller being
    # in take_one_action()'s controllers list) in a PREVIOUS frame, and
    # TransportController._begin_placement() has now stacked the squad's
    # models on the TRANSPORT, ready to be spread out and confirmed.
    if (
        transport_controller is not None and setup_controller is not None
        and setup_controller.state == PLACING and setup_controller.setting_up_squad is not None
        and setup_controller.setting_up_squad.owner == player
        and transport_controller.is_disembarking(setup_controller.setting_up_squad)
    ):
        squad = setup_controller.setting_up_squad
        if not _maybe_resume_disembark_placement(
            transport_controller, setup_controller, player, all_tokens, game_log=game_log,
        ):
            # Couldn't legally be placed from any facing - abandoned rather
            # than left stuck. cancel_disembark() restores the squad EXACTLY
            # as it was (back inside the transport), so without recording the
            # failure the very next call would re-run this identical attempt
            # from this identical state forever - the reported endless loop.
            memory.declined_disembark.add(squad.name)
        return True

    # Rule 20.04 (Ingress move): deploy any of player's own strategic-
    # reserves squads that are legally eligible right now, as early as
    # possible - see _auto_ingress_squad()'s docstring for why this is
    # deterministic (no agent.decide() call) rather than an offered choice.
    # Checked before the on-board squad loop below, same priority as the
    # Disembark-resume branch above.
    if ingress_controller is not None and setup_controller is not None:
        for squad in sorted(list(state.reserves), key=lambda s: s.name):
            if squad.owner == player and ingress_controller.can_ingress(squad):
                if _auto_ingress_squad(
                    setup_controller, ingress_controller, squad, all_tokens,
                    objectives=state.objectives, state=state,
                    plan=(memory.turn_plan["unit_plans"] if memory.turn_plan else None),
                    game_log=game_log,
                ):
                    return True

    plan = memory.turn_plan["unit_plans"] if memory.turn_plan else None
    corridors = _vehicle_corridors(all_tokens, player, plan)
    zones = _disembark_zones(all_tokens, player, plan, state.embarked_squads)
    for squad in sorted(_all_squads(all_tokens), key=lambda s: _movement_priority_key(s, all_tokens, plan, corridors, zones)):
        if squad.owner != player:
            continue

        if transport_controller is not None and setup_controller is not None and squad.models and squad.models[0].profile.transport:
            for passenger_squad in transport_controller.embarked_squads_in(squad.models[0]):
                if _handle_disembark_for_squad(
                    agent, memory, player, all_tokens, state.obstacles, state.terrain_areas, passenger_squad,
                    transport_controller, setup_controller, on_thinking, plan=plan, objectives=state.objectives,
                    game_log=game_log,
                ):
                    return True

        if not movement_controller.can_move(squad):
            continue

        # Rule 09.06: Advancing costs this unit its shooting (non-Assault
        # weapons) AND its charge for the turn. Real user report ("der kroot
        # trupp steht genau vor meinem stealth team, aber weder schießt er
        # noch charged er") traced straight to this: the plan said "Advance
        # toward and attack enemy Stealth Battlesuits 1, 4.4 inches away",
        # the squad (M=7") Advanced, gained 2 useless inches - and was then
        # rule-correctly barred from both shooting and charging the enemy it
        # had just walked up to. The prompt already advised skipping Advance
        # in exactly this case, but that left the model to work out for
        # itself whether a plain move would have sufficed; the plan role
        # being *named* "advance" (meaning "push forward", not the 09.06
        # move type) makes that trap even easier to fall into. So don't
        # offer it at all when a plain move would leave the enemy chargeable
        # anyway - Advance is then strictly worse, never a judgment call.
        #
        # Orks army rule "Waaagh!" (user-supplied, see game/waaagh.py):
        # while active for this squad, Advancing no longer costs it the
        # charge (only non-Assault shooting) - user policy: "in dem Zug
        # möglichst immer advance anwenden mit nahkampforientierten
        # einheiten, da man danach ja noch chargen kann". So the whole
        # "strictly worse when a plain move already reaches charge range"
        # reasoning above no longer applies: Advance is worth offering
        # unconditionally, and its own trade-off description below is
        # rewritten to say so (Claude still makes the final call - see
        # SYSTEM_PROMPT's own WAAAGH! guidance - but the option is never
        # withheld the way it normally would be here).
        waaagh_charge_ok = squad_waaagh_active(squad, waaagh_controller)
        advance_trade_off_text = (
            "but this unit can still declare a charge this turn (WAAAGH! is active) - it just can't "
            "shoot with non-Assault weapons"
        ) if waaagh_charge_ok else (
            "but this unit cannot shoot with non-Assault weapons or declare a charge this turn"
        )

        def _advance_is_worth_offering(enemy_squad):
            if waaagh_charge_ok:
                return True
            if enemy_squad is None:
                return True
            reach = min_model_movement(squad)
            return squad.min_distance_to(enemy_squad) - reach > CHARGE_RANGE_IN

        # Rule 14.01-14.02 (mission objectives): a squad standing on an
        # objective is actively holding ground by staying put, not being
        # passive - annotate remain_stationary so Claude reads it that way
        # (see ai/claude_agent.py's SYSTEM_PROMPT's new "Map control /
        # objectives" guidance) instead of defaulting to "nothing to do
        # here, might as well advance" and giving up OC it already has.
        held_objectives = [o.name for o in state.objectives if any(o.terrain_area.overlaps_model(m) for m in squad.models)]
        stationary_description = f"{squad.name}: remain stationary"
        if held_objectives:
            stationary_description += f" (currently holding/contesting: {', '.join(held_objectives)})"
        options = [{"type": "remain_stationary", "squad": squad.name, "description": stationary_description}]
        can_advance = movement_controller.can_make_move(squad)
        nearest = _nearest_enemy_squad(squad, all_tokens) if can_advance else None

        # The turn plan's own named target, if it named an ENEMY squad for
        # this unit (see _planned_enemy_target()). Real gap found via user
        # report ("statt 'central objective support' sollte da eher stehen
        # 'move kroot to enemy kroot 1 unit, fire and charge it'"): the plan
        # could already name a target, but NOTHING in this file ever read it
        # - only `priority` was used, purely to sort the squad loop. So even
        # a perfectly specific plan was unactionable, because the only
        # advance option ever offered was toward whichever enemy happened to
        # be NEAREST. Offering the planned target as its own option is what
        # makes a plan something the tactical layer can actually carry out.
        # A bare place on the board, for orders that point at neither a unit
        # nor an objective ("get behind the ruin", "hold this corner"). See
        # the plan schema's position_x/position_y comment for why this exists.
        planned_position = _planned_position(squad, plan) if can_advance else None
        if planned_position is not None:
            gap = _distance_from_squad_to_point(squad, planned_position)
            reach = min_model_movement(squad)
            options.append({
                "type": "move_to_planned_position", "squad": squad.name,
                "description": (
                    f"{squad.name}: move toward ({planned_position[0]:.0f}, {planned_position[1]:.0f}) "
                    f"- the position your turn plan gave this squad ({gap:.0f}\" away; this unit "
                    f"moves {reach:.0f}\" per turn)"
                ),
            })
            # An Advance that KEEPS the commanded spot. Without this, a squad
            # whose plan named a position had no way to buy the extra D6" except
            # by picking an option that aims somewhere else entirely - and that
            # is what happened: the Warbikers were ordered to (39,34), took
            # "Advance toward the nearest enemy" for the extra distance, and so
            # were evaluated against the ENEMY instead of the commanded point,
            # drifting to the board edge at x=43.0 with ~0" of progress. Measured
            # afterwards, a legal 12" move from there gained +9.1" toward (39,34),
            # so the ground was never the obstacle - the goal point was wrong.
            # Only worth offering when a normal move cannot already get there.
            if gap > reach:
                options.append({
                    "type": "advance_to_planned_position", "squad": squad.name,
                    "description": (
                        f"{squad.name}: Advance toward ({planned_position[0]:.0f}, "
                        f"{planned_position[1]:.0f}) - the position your turn plan gave this squad "
                        f"({gap:.0f}\" away, further than this unit's {reach:.0f}\" move) - roll a D6 "
                        f"for extra movement distance, {advance_trade_off_text}"
                        + _advance_charge_note(squad, _planned_enemy_target(squad, plan, all_tokens)
                                               or _nearest_enemy_squad(squad, all_tokens), waaagh_charge_ok)
                    ),
                })

        planned_target = _planned_enemy_target(squad, plan, all_tokens) if can_advance else None
        # A plan that names BOTH a place and a target means "stand here, shoot
        # that" - the documented split, and what the prompt tells the planner.
        # Offering a move-at-the-target option alongside the move-to-the-place
        # one put two competing choices in front of the tactical layer, and it
        # took the enemy: ordered to (22,30) with a target named for next turn,
        # the Stormboyz set off at the Kroot instead and stopped 12" short of
        # the commanded spot, in the open. When a position is given it governs
        # the MOVE; the target still governs shooting and charging.
        if planned_position is not None:
            planned_target_move_offered = False
        else:
            planned_target_move_offered = True
        if planned_target_move_offered and planned_target is not None and planned_target is not nearest:
            reach = min_model_movement(squad)
            options.append({
                "type": "move_to_planned_target", "squad": squad.name,
                "description": (
                    f"{squad.name}: move toward {planned_target.name} - the enemy unit your turn "
                    f"plan assigned to this squad ({squad.min_distance_to(planned_target):.0f}\" away; "
                    f"this unit moves {reach:.0f}\" per turn)"
                ),
            })
            if _advance_is_worth_offering(planned_target):
                options.append({
                    "type": "advance_to_planned_target", "squad": squad.name,
                    "description": (
                        f"{squad.name}: Advance toward {planned_target.name} (your turn plan's target for "
                        f"this squad) - roll a D6 for extra movement distance, {advance_trade_off_text}"
                        + _advance_charge_note(squad, planned_target, waaagh_charge_ok)
                    ),
                })

        if can_advance and nearest is not None:
            # Distances spelled out rather than left to be derived from raw
            # coordinates - same reason the planning observation now carries
            # them (see ai/observation.py's add_planning_distances()): a
            # model judging "can I get there" from (x, y) pairs is doing
            # arithmetic it is unreliable at, and it showed (user report:
            # orders to attack units that were nowhere near).
            reach = min_model_movement(squad)
            options.append({
                "type": "move_to_nearest_enemy", "squad": squad.name,
                "description": (
                    f"{squad.name}: move toward the nearest enemy squad ({nearest.name}, "
                    f"{squad.min_distance_to(nearest):.0f}\" away; this unit moves {reach:.0f}\" per turn)"
                ),
            })
            # Rule 09.06 (Advance): a real, standard 40k trade-off - real
            # gap found via a dedicated audit ("advance-move (09.06)... die
            # ki bewegt sich immer nur mit ihrer festen Movement-
            # Charakteristik, nie mit dem Zusatzwürfel") - MovementController.
            # start_run() existed and was fully functional, but nothing in
            # this file ever called it, so the AI never used the one move
            # type that trades extra reach for this turn's own shooting
            # (non-Assault weapons)/charge eligibility. This ISN'T a
            # multi-step-lookahead problem the way e.g. Crushing Impact is
            # (that one depends on a genuinely FUTURE, not-yet-existing
            # opportunity several decisions away) - the cost here is a fixed,
            # already-known rule consequence of THIS one decision, so it's
            # simply stated directly in the option text below, exactly like
            # Fall Back's own trade-off is - no lookahead needed, just the
            # right information attached to the single choice being made
            # right now. See ai/claude_agent.py's SYSTEM_PROMPT for the
            # actual guidance on weighing it.
            if planned_position is None and _advance_is_worth_offering(nearest):
                options.append({
                    "type": "advance_to_nearest_enemy", "squad": squad.name,
                    "description": (
                        f"{squad.name}: Advance toward the nearest enemy squad ({nearest.name}) - roll a D6 for "
                        f"extra movement distance, {advance_trade_off_text}"
                        + _advance_charge_note(squad, nearest, waaagh_charge_ok)
                    ),
                })

        # Rule 14.01-14.02 (mission objectives) - user-requested tactical
        # policy: the AI needs to actively contest/claim objectives for map
        # control, not just cluster on the nearest enemy. _best_objective_
        # target() picks the single best objective to head toward (its own
        # docstring explains the two-tier "prefer uncontrolled" preference
        # and why it deliberately doesn't score/weigh candidates itself -
        # that's left to Claude via the OC-present/controlled_by data in
        # the observation, see ai/observation.py's objective_summary()).
        #
        # Dedup: if the nearest enemy squad is itself already standing on
        # this exact objective, "move toward it" would produce the same
        # destination as move_to_nearest_enemy above under a different
        # label - skip offering it, since it isn't a genuinely different
        # choice, just redundant noise in the option list.
        objective_point = None
        planned_objective = _planned_objective(squad, plan, state.objectives) if can_advance else None
        if planned_objective is not None:
            # The plan named a specific objective for this squad - head for
            # THAT one, not whichever _best_objective_target() would rank
            # highest on its own. See _planned_objective()'s docstring for
            # the reported bug this fixes (a squad ordered to the Central
            # Objective being offered only the nearby one it already sat on).
            min_x, min_y, max_x, max_y = planned_objective.terrain_area.bounding_box
            objective = planned_objective
            objective_point = ((min_x + max_x) / 2, (min_y + max_y) / 2)
        elif can_advance:
            objective_target = _best_objective_target(squad, state.objectives, all_tokens)
            if objective_target is not None and (
                nearest is None or not any(objective_target[0].terrain_area.overlaps_model(m) for m in nearest.models)
            ):
                objective, objective_point = objective_target

        if objective_point is not None:
            status = "uncontrolled" if objective.controlled_by is None else f"controlled by {objective.controlled_by}"
            # Rule 14.01 totals OC across the unit's models; an attached
            # unit (19.01) mixes OC values, so the sum is the meaningful
            # number here as well as the correct one.
            own_oc = sum(m.profile.oc for m in squad.models)
            obj_gap = min(objective.terrain_area.distance_to_model(m) for m in squad.models)
            reach = min_model_movement(squad)
            plan_note = " [the objective your turn plan assigned to this squad]" if planned_objective is not None else ""
            options.append({
                "type": "move_to_objective", "squad": squad.name,
                "description": (
                    f"{squad.name}: move onto {objective.name} ({status}, {obj_gap:.0f}\" away; this unit "
                    f"moves {reach:.0f}\" per turn) to claim/contest it for map control "
                    f"(this squad's OC: {own_oc}){plan_note}"
                ),
            })
            if planned_position is None and _advance_is_worth_offering(nearest):
                options.append({
                    "type": "advance_to_objective", "squad": squad.name,
                    "description": (
                        f"{squad.name}: Advance toward {objective.name} ({status}, {obj_gap:.0f}\" away) - "
                        f"roll a D6 for extra movement distance, {advance_trade_off_text}"
                    ),
                })

        # Staging (user-requested tactical heuristic, rule 09.02's Normal
        # Move covers it mechanically - it's just a different destination
        # point than "move_to_nearest_enemy" above): a squad that hasn't
        # moved yet this phase has remaining_range == its own M
        # characteristic (movement_controller.remaining_range only gets
        # populated once start_move() actually runs below), so
        # profile.movement_in is a reliable stand-in for computing this
        # BEFORE committing to a move type.
        staging_point = None
        if can_advance:
            max_distance_estimate = min_model_movement(squad)
            staging_point = _best_staging_point(squad, max_distance_estimate, all_tokens, state.obstacles, state.terrain_areas)
            if staging_point is not None:
                options.append({
                    "type": "stage_to_cover", "squad": squad.name,
                    "description": f"{squad.name}: reposition toward nearby cover to break enemy line of sight",
                })

        # Rule 09.07 (Fall Back) - user-requested tactical policy: "ki soll
        # sich mit schwachen Nahkampfeinheiten zurückziehen, damit andere
        # wieder auf den Gegner schießen können". Fall Back is the ONLY move
        # type available to an engaged squad at all (can_make_move() above
        # is its exact inverse) - previously this branch never even
        # considered it, so an engaged AI squad always just sat there via
        # "remain_stationary" being the sole option (no agent.decide() call,
        # since there was nothing else to weigh). Offered as a real option
        # now whenever legal, letting the agent weigh it against just
        # staying put - see ai/claude_agent.py's SYSTEM_PROMPT for the
        # actual guidance on when retreating is worth it (rule 03.04/
        # _is_valid_target_squad() already block shooting at any enemy unit
        # currently engaged with ANYONE, so pulling a losing melee unit out
        # is what actually reopens that enemy to the rest of the army's
        # ranged fire this same turn - Movement precedes Shooting).
        if fall_back_controller is not None and movement_controller.can_make_fall_back_move(squad):
            options.append({
                "type": "fall_back", "squad": squad.name,
                "description": f"{squad.name}: Fall Back out of engagement (rule 09.07)",
            })

        # Surface THIS squad's own plan entry (if the strategic planning
        # phase produced one) plus the whole-turn intent as extra context -
        # see ai/claude_agent.py's SYSTEM_PROMPT "Turn plan" guideline and
        # ai/observation.py's build_observation()'s plan_context param.
        plan_entry = plan.get(squad.name) if plan else None
        plan_context = {"turn_intent": memory.turn_plan["turn_intent"], **plan_entry} if plan_entry else None

        chosen = _choose(
            agent, all_tokens, movement_controller.turn_tracker, options, player, on_thinking,
            objectives=state.objectives, plan_context=plan_context,
        )

        movement_controller.select(squad.models[0])
        if chosen["type"] == "remain_stationary":
            movement_controller.remain_stationary()
        elif chosen["type"] == "fall_back":
            _execute_fall_back(fall_back_controller, movement_controller, squad, all_tokens, game_log)
        else:
            if chosen["type"] == "stage_to_cover":
                target_point = staging_point
                # Staging PACKS the unit at the spot - the cover was measured
                # against a squeezed footprint, so only a squeezed arrival
                # delivers it. See _stage_toward(); it falls through to the
                # ordinary move below if that ground cannot hold the block.
                if _stage_toward(movement_controller, squad, staging_point,
                                 [s for s in _all_squads(all_tokens)
                                  if s.owner != squad.owner and s.models],
                                 movement_controller.start_move,
                                 movement_controller.confirm_move,
                                 movement_controller.cancel_move):
                    if game_log is not None:
                        game_log.add(
                            f"  [move choice] {squad.name}: stage_to_cover (packed) -> "
                            f"({staging_point[0]:.1f},{staging_point[1]:.1f})", file_only=True)
                    return True
            elif chosen["type"] in ("move_to_objective", "advance_to_objective"):
                target_point = objective_point
            elif chosen["type"] in ("move_to_planned_position", "advance_to_planned_position"):
                target_point = planned_position
            elif chosen["type"] in ("move_to_planned_target", "advance_to_planned_target"):
                target_point = _centroid(planned_target)
            else:
                target_point = _centroid(nearest)
            # Which option actually won, and where it aims. Without this line a
            # report like "the bikes went backwards" cannot be diagnosed at all:
            # the plan's own coordinate is in the log, and the final positions
            # are in the log, but nothing said WHICH of the offered movement
            # options the tactical layer picked - and "it chose a different
            # destination" and "it aimed at the right point and the move failed"
            # need completely different fixes. Same observability gap the
            # "[turn plan] ... @(x,y)" addition closed on the planner side.
            if game_log is not None:
                planned_note = ""
                if planned_position is not None:
                    planned_note = (f"; plan named ({planned_position[0]:.0f},"
                                    f"{planned_position[1]:.0f})")
                game_log.add(
                    f"  [move choice] {squad.name}: {chosen['type']} -> "
                    f"({target_point[0]:.1f},{target_point[1]:.1f}){planned_note}",
                    file_only=True,
                )
            # User directive: "Einheiten die aus Fahrzeugen bestehen, wie zb
            # Crisis, sollten sich auch immer individuell bewegen. Dort auch
            # keine bulk moves mehr." - a squad entirely made of VEHICLE-
            # keyword models (e.g. Crisis Battlesuits: VEHICLE/WALKER, not
            # INFANTRY - see game/units.py's CrisisStarscytheShasUiProfile -
            # so it does NOT get 13.06's free Dense-terrain pass-through)
            # never gets the rigid bulk fallback at all, only per-model.
            allow_bulk = not all(m.profile.vehicle for m in squad.models)

            # User report: "die AI benutzt kein 'take to the skies'" - rule
            # 21.03 lets any model with FLY (e.g. those same Crisis
            # Battlesuits - VEHICLE/WALKER/FLY together, see their profile's
            # own docstring) bypass terrain/other models entirely for a flat
            # -2" distance penalty (unless HOVER). Since this squad type is
            # exactly the one most prone to getting boxed in by terrain (no
            # free INFANTRY-style Dense-terrain pass-through, and now no
            # bulk-translation fallback either), taking to the skies is a
            # deterministic policy, not a judgment call for the agent.
            #
            # WHICH squads it pays for is take_to_the_skies_pays()'s question,
            # not an any()/all() spelled out here - see its docstring. This
            # used to read `any(m.profile.fly ...)` on the premise that the
            # declaration "can only ever help this squad's own mobility, at a
            # fixed, small cost". True for the squad it was written for, where
            # every model flies; false for an attached unit (19.01) whose
            # leader is the only flyer, because the 2" is charged to the whole
            # squad and the bypass is granted per model. Second user report,
            # "die necron krieger sind hinten nicht rausgekommen": one
            # Technomancer turned it on for twenty Necron Warriors, who paid
            # 40% of a 5" move every turn and flew over nothing.
            use_fly = take_to_the_skies_pays(squad)
            use_advance = chosen["type"] in (
                "advance_to_nearest_enemy", "advance_to_objective", "advance_to_planned_target",
                "advance_to_planned_position",
            )

            def start_fn():
                movement_controller.start_move()
                if use_advance:
                    # Rule 09.06: MovementController.start_move() itself
                    # already re-applies a previously-rolled bonus for this
                    # squad (see its own comment: "the Advance roll is made
                    # once and is final for the phase") before start_run()
                    # is even reached here - so a later retry attempt within
                    # _advance_toward()'s angle/fraction sweep correctly
                    # keeps the SAME D6 result instead of re-rolling it, with
                    # no extra bookkeeping needed on this side.
                    movement_controller.start_run()
                if use_fly:
                    movement_controller.take_to_the_skies()

            if not _advance_toward(movement_controller, squad, target_point, start_move_fn=start_fn, allow_bulk_fallback=allow_bulk, flying=use_fly):
                # Every sampled direction/distance failed (see
                # _advance_toward()'s docstring) - genuinely nowhere legal
                # to go this turn, not just "the one straight line happened
                # to be blocked". Falls back to remaining stationary.
                movement_controller.remain_stationary()
                if game_log is not None:
                    game_log.add(
                        f"{player}: {squad.name}'s advance was illegal, remained stationary instead.",
                        category=game_log_module.FAILED_ORDER,
                    )
        return True
    return False


def _handle_explosives_for_squad(agent, memory, player, all_tokens, squad, explosives_controller, on_thinking):
    """Rule 15.05 (Explosives, Core Stratagem, 1CP): a decision separate
    from (not a replacement for) the squad's normal shoot/hold-fire choice
    below - it doesn't consume the unit's own shooting action. Checked once
    per squad per phase (memory.declined_explosives, same reasoning as
    declined_shoot/declined_charge - the engine has no "declined" concept
    of its own for this either). Returns True if a decision was made.

    can_use() now also checks TARGET reachability (rule 15.05: an unengaged
    enemy unit within 8" of, and visible to, a qualifying model) via a
    line_of_sight() scan - same shape as the perf bug already found and
    fixed for Greater Good (see _handle_greater_good_for_squad's docstring):
    a squad with nothing in range would otherwise get that scan re-run on
    EVERY take_one_action() call for the rest of the phase. Fixed the same
    way - a False can_use() is cached like an explicit decline, since
    nothing it checks (engaged/advanced/ability/shooting-eligibility/
    visible targets) changes mid-Shooting-phase. controller.state != IDLE
    (someone else's flow currently open) is the one genuinely transient
    case, so it's checked separately and left uncached."""
    if squad.name in memory.declined_explosives:
        return False
    if explosives_controller.state != explosives_module.IDLE:
        return False  # someone else's flow is open right now - transient, don't cache
    if not explosives_controller.can_use(squad):
        memory.declined_explosives.add(squad.name)
        return False

    explosives_controller.start(squad)  # free - no CP spent yet, just enters the model/target selection
    if explosives_controller.state == explosives_module.CHOOSING_MODEL:
        # Our squads are fully homogeneous - any qualifying model is equally
        # good, so no real choice, no agent.decide() call needed.
        explosives_controller.choose_model(explosives_controller.choosable_models()[0])

    if explosives_controller.state == explosives_module.CHOOSING_TARGET:
        targets = sorted(explosives_controller.eligible_target_squads(), key=lambda s: s.name)
        if not targets:
            explosives_controller.cancel()
            memory.declined_explosives.add(squad.name)
            return True

        options = [{"type": "no_explosives", "squad": squad.name, "description": f"{squad.name}: don't use Explosives"}]
        for target in targets:
            options.append({
                "type": "explosives", "squad": squad.name, "target": target.name,
                "description": f"{squad.name}: use Explosives (1CP) on {target.name}",
            })
        chosen = _choose(agent, all_tokens, explosives_controller.turn_tracker, options, player, on_thinking)
        if chosen["type"] == "no_explosives":
            explosives_controller.cancel()
            memory.declined_explosives.add(squad.name)
        else:
            target = _squad_by_name(chosen["target"], all_tokens)
            explosives_controller.choose_target(target)
            # Spends the CP and rolls 6D6, leaving it pending - the human
            # clicks through it exactly like any other roll (already wired
            # in main.py's dice-ack chain).
    return True


def _handle_arrokon_for_squad(agent, memory, player, all_tokens, squad, arrokon_controller, on_thinking):
    """Retaliation Cadre's The Arro'kon Protocol (1CP, game/arrokon_protocol.py):
    a decision separate from (not a replacement for) the squad's own
    shoot/hold-fire choice below - it doesn't consume the unit's shooting
    activation, it buffs it, so it has to be offered BEFORE the unit is
    selected to shoot (its own TARGET clause says so). Checked once per squad
    per phase (memory.declined_arrokon, same "the engine has no 'declined'
    concept of its own" reasoning as declined_shoot/declined_explosives).
    Returns True if a decision was made.

    A False can_use() is cached exactly like an explicit decline, for the
    perf reason _handle_greater_good_for_squad()'s docstring spells out: its
    last check is a line-of-sight sweep over every big enough enemy unit, and
    nothing it looks at (BATTLESUIT, already shot, CP, what is in range)
    changes mid-Shooting-phase in a way that could turn a "no" into a "yes"
    for this squad. The one genuinely transient input is whether it has
    already been used this phase (rule 15.01), and that only ever goes from
    yes to no.

    The option text carries the tier rather than the rule text, for the same
    reason _matchup_hint() carries a wound threshold instead of raw S and T:
    "[SUSTAINED HITS 2] against a 12-model unit" is a decision, "6 or more
    models" is arithmetic to be redone."""
    if squad.name in memory.declined_arrokon:
        return False
    if not arrokon_controller.can_use(squad):
        memory.declined_arrokon.add(squad.name)
        return False

    targets = arrokon_controller.qualifying_target_squads(squad)
    tier = max((arrokon_module.sustained_hits_for_target(t) for t in targets), default=0)
    best = max(targets, key=arrokon_module.sustained_hits_for_target, default=None)
    detail = (
        f"{best.name} ({arrokon_module.alive_model_count(best)} models)" if best is not None else "a large enemy unit"
    )
    options = [
        {
            "type": "no_arrokon", "squad": squad.name,
            "description": f"{squad.name}: don't use The Arro'kon Protocol",
        },
        {
            "type": "arrokon", "squad": squad.name,
            "description": (
                f"{squad.name}: use The Arro'kon Protocol (1CP) - until the end of the phase this unit's attacks "
                f"have [SUSTAINED HITS 1] against enemy units of 6+ models, [SUSTAINED HITS 2] against 11+ "
                f"(best right now: [SUSTAINED HITS {tier}] against {detail}). Each critical hit then adds that "
                "many extra hits. Must be used BEFORE this unit shoots."
            ),
        },
    ]
    chosen = _choose(agent, all_tokens, arrokon_controller.turn_tracker, options, player, on_thinking)
    if chosen["type"] == "no_arrokon":
        memory.declined_arrokon.add(squad.name)
    else:
        arrokon_controller.use(squad)  # TARGET is trivially this squad - the CP is spent right here
    return True


def _handle_greater_good_for_squad(agent, memory, player, all_tokens, squad, greater_good_controller, shooting_controller, on_thinking):
    """T'au Empire army rule "For The Greater Good" (user-supplied, not a
    core rulebook rule - game/greater_good.py): a decision separate from
    (not a replacement for) the squad's normal shoot/hold-fire choice
    below - marking a target doesn't consume the unit's own shooting
    activation. Checked once per squad per phase (memory.
    declined_greater_good, same "the engine has no 'declined' concept of
    its own" reasoning as declined_shoot/declined_charge/declined_
    explosives). Returns True if a decision was made.

    Real user report: "die KI benutzt gar kein Markerlight" - the whole
    controller (game/greater_good.py) was fully wired for a human (button
    in ActionPanel, board-click target selection) but ai/agent_driver.py
    never referenced it anywhere at all, so the AI's own T'au squads with
    this ability (Stealth Battlesuits' For The Greater Good/Forward
    Observers, any Marker Drone-equipped Shas'ui) simply never became
    Observers or marked anything - a gap of the same shape as Explosives
    before _handle_explosives_for_squad() existed.

    declined_greater_good therefore holds ONLY an explicit "no_mark" from
    the model - a real decline, exactly like declined_shoot/declined_charge.
    It used to also swallow "can_use() said no" and "no targets", for perf:
    can_use()'s last clause is a full line-of-sight sweep (measured at
    4732 ms on a 179-model board), and re-running it on every
    take_one_action() call was seconds per phase.

    That is now GreaterGoodController.any_eligible_target()'s own cache,
    which is both faster and stricter, and dropping the two extra entries
    fixes a real bug the old comment argued itself into. It claimed
    "positions are frozen until the next Movement phase" - they are not.
    The opponent's reactive moves (MovementController.REACTIVE_MOVE_MODES)
    and the active player's own out-of-phase moves both happen mid-Shooting
    phase, so a squad that saw nothing at the start of the phase would never
    look again after an enemy Fade Back moved into view.

    greater_good_controller.state != IDLE stays uncached and unchanged:
    some OTHER squad's marking flow (possibly the human's) being open is
    genuinely transient, and retrying plainly next call is right."""
    if squad.name in memory.declined_greater_good:
        return False
    if greater_good_controller.state != greater_good_module.IDLE:
        return False  # someone else's flow is open right now - transient, don't cache
    if not greater_good_controller.can_use(squad, shooting_controller):
        return False

    greater_good_controller.start(squad)  # free - no CP, just enters target selection
    targets = sorted(greater_good_controller.eligible_targets(squad), key=lambda s: s.name)
    if not targets:
        greater_good_controller.cancel()
        return True

    options = [{"type": "no_mark", "squad": squad.name, "description": f"{squad.name}: don't become an Observer"}]
    for target in targets:
        options.append({
            "type": "mark_target", "squad": squad.name, "target": target.name,
            "description": f"{squad.name}: mark {target.name} as Spotted (Observer, For the Greater Good)",
        })
    chosen = _choose(agent, all_tokens, greater_good_controller.turn_tracker, options, player, on_thinking)
    if chosen["type"] == "no_mark":
        greater_good_controller.cancel()
        memory.declined_greater_good.add(squad.name)
    else:
        target = _squad_by_name(chosen["target"], all_tokens)
        greater_good_controller.choose_target(target)
    return True


def _ranged_weapon_summary(squad):
    """Compact "what am I actually shooting with" summary (S/AP/D per
    distinct ranged weapon on the squad's own representative model) - user
    report: a single Crisis Starscythe Battlesuit (Burst cannon + T'au
    flamer - both low-AP, anti-infantry weapons, no anti-tank option at all
    on this datasheet) shot an enemy Devilfish (a well-armored VEHICLE)
    while an equally visible, equally in-range Breacher Team stood right
    there - a badly lopsided matchup Claude had no way to actually judge,
    since build_observation() never sent weapon stats at all and the option
    text just said "shoot Devilfish" with nothing to weigh it against. Same
    fix pattern as the Markerlight/Guided-target hint above: put the actual
    numbers directly in the option text, the same thing a human glances at
    on the datasheet before picking a target, instead of asking Claude to
    guess from the squad's name alone."""
    seen = []
    for weapon in squad.models[0].weapons:
        if weapon.weapon_type != RANGED:
            continue
        label = f"{weapon.name} (S{weapon.strength}/AP{weapon.ap}/D{weapon.damage})"
        if label not in seen:
            seen.append(label)
    return ", ".join(seen) if seen else "no ranged weapons"


def _target_profile_hint(target):
    """The other half of the matchup: the target's own Toughness/Save, plus
    its VEHICLE/MONSTER keyword when it has one - exactly what the weapon
    stats above need to be weighed against (a low-AP weapon barely dents a
    good Sv/high-T VEHICLE, but shreds a T3/Sv5+ infantry squad, and vice
    versa for a high-AP, low-shot-count weapon)."""
    profile = target.models[0].profile
    keyword = ""
    if profile.vehicle:
        keyword = ", VEHICLE"
    elif profile.monster:
        keyword = ", MONSTER"
    return f"T{profile.toughness}, Sv{profile.armor_save}{keyword}"


def _advance_charge_note(squad, enemy, waaagh_charge_ok):
    """What the extra D6 buys, as a charge probability - the difference
    between plain-moving and Advancing at `enemy` this turn.

    Only produced while Advancing keeps the charge (an active WAAAGH!, rule
    09.06's cost suspended by the army rule). Otherwise there is no
    before/after to compare: Advancing forfeits the charge outright, which the
    option's own trade-off sentence already says.

    A NUMBER on the option rather than another sentence in the prompt, for the
    reason this file has now measured several times: a tactic attached to a
    choice as a figure gets acted on, the same tactic as prose competes with
    everything else in the system prompt. The user's point is exactly a
    quantitative one - "gerade im waagh zug hat man dadurch ja kaum abzuege.
    man darf danach noch chargen" - so the option should show what the trade
    is worth instead of asserting that it is cheap."""
    if not waaagh_charge_ok or enemy is None or not enemy.models or not squad.models:
        return ""
    plain = observation.charge_now(squad, enemy)
    after = observation.charge_chance_after_advancing(squad, enemy)
    try:
        before = float(plain["chance_to_reach_it_this_turn"].rstrip("%"))
    except (KeyError, ValueError):
        return ""
    if after <= before + 1.0:
        # Already a near-certain charge (or already hopeless): the extra
        # inches change nothing worth reading, and a superlative on every
        # option is the same as none.
        return ""
    return (
        f" - charging {enemy.name} after a plain move needs "
        f"{plain['charge_roll_needed']}+ ({before:.0f}%), after this Advance {after:.0f}%"
    )


def _matchup_hint(squad, target):
    """How good is this shot, as the one number that actually decides it: the
    wound roll the squad's BEST ranged weapon needs against this target.

    The raw stats were already in the option text (weapon S/AP/D via
    _ranged_weapon_summary(), target T/Sv via _target_profile_hint()) - and
    the exact matchup that fix was written for came back anyway: Crisis
    Starscythe Battlesuits, carrying nothing but low-AP anti-infantry guns,
    opened up on a Devilfish while two infantry squads stood equally visible
    and in range. Deriving "S5 against T9 means 6s" from two separate numbers
    is evidently not reliable, so derive it here and state the result. Same
    approach as the charge option's hit probability, which had the same
    problem before it stopped printing raw distances and started printing
    odds."""
    toughness = attached_unit_toughness(target)
    best = None
    for model in squad.models:
        for weapon in model.weapons:
            if weapon.weapon_type != RANGED:
                continue
            needed = _shooting_wound_threshold(weapon.strength, toughness)
            if best is None or needed < best:
                best = needed
    if best is None:
        return ""
    if best >= 6:
        verdict = " - a very poor matchup, look for a softer target"
    elif best == 5:
        verdict = " - a weak matchup"
    else:
        verdict = ""
    return f"; your best weapon wounds it on {best}+{verdict}"


# How far ahead the best shot has to be before the option text calls it the
# best - the same restraint, and roughly the same size, as
# CHARGE_COST_MIN_DROP_PCT below: 15% is outside the noise of an estimate that
# ignores re-rolls and cover, a few percent is not.
SHOT_VALUE_CLEAR_LEAD = 1.15


def _shot_value_hints(squad, targets):
    """What each of these shots is WORTH, in enemy points destroyed per turn,
    with the best one named as such - as {target name: text}.

    _matchup_hint() above states a per-shot success chance, and on its own that
    is a systematically misleading way to choose between targets: a Rokkit at
    S9 wounds T4 Stealth Battlesuits on 2s and a T8 Ghostkeel on 3s, so the
    only number on the option said "shoot the infantry" to the exact unit whose
    guns exist for the vehicle. Reported case, and the fix is the same shape as
    the hint it sits next to: compute the number that actually decides it
    rather than printing an input to it (user: "die deffkopter haben auch anti
    tank waffen. haben aber irgendwie immer auf die stealth suites geschossen.
    und die fahrzeuge ignoriert").

    Points removed rather than models killed, for the reason
    observation.damage_value() gives: a share of a cheap screen outnumbers a
    share of the expensive thing every time, so counting bodies aims a
    specialist at the screen. The two hints are complementary and both are
    kept - the wound threshold is what stops a low-Strength gun firing at a
    hull it cannot hurt, the value is what stops a high-Strength one wasting
    itself on bodies.

    Unlike the planner's version of the same number, this one DOES drop
    weapons that cannot reach the target (the `gap_in` argument): here the
    distance is a fact - the shot is being taken now, from where the unit
    stands - whereas a planning estimate has to allow for the move that comes
    first. It matters on exactly the reported case: a Deffkopta squadron's 12"
    Sluggas were being credited against Stealth Battlesuits 16" away, which is
    most of what made shooting them look as good as shooting the vehicle its
    24" Rokkits are for (26 vs 29 points counting the Sluggas, 22 vs 29
    without them).

    Otherwise the same approximation as every other estimate in this file: no
    re-rolls, no [SUSTAINED HITS]/[LETHAL HITS]/[DEVASTATING WOUNDS], no
    cover. It answers "which of these shots is worth the most", not "what will
    this attack roll"."""
    values = {
        t.name: observation.damage_value(squad, t, melee=False,
                                         gap_in=squad.min_distance_to(t))
        for t in targets
    }
    ranked = sorted(values.values(), reverse=True)
    best = ranked[0] if ranked else 0.0
    runner_up = ranked[1] if len(ranked) > 1 else 0.0
    # A favourite is only named when it is CLEARLY ahead of the next one.
    # Two targets a few percent apart are a tie as far as an approximation
    # this rough can tell, and printing "the most valuable" on both - which
    # the first version of this did - is worse than printing it on neither.
    clear_lead = best > 0 and best >= runner_up * SHOT_VALUE_CLEAR_LEAD

    out = {}
    for target in targets:
        value = values[target.name]
        if value <= 0.05:
            out[target.name] = "; this shot destroys almost nothing"
            continue
        note = ""
        if clear_lead and value >= best:
            note = " - the most valuable shot available to this unit"
        elif best > 0 and value < best * 0.5:
            note = f" - less than half of what your best target here is worth ({best:.0f})"
        out[target.name] = f"; worth ~{value:.0f} enemy points per turn{note}"
    return out


# How much worse the charge has to get before shooting a would-be charge
# target is worth mentioning at all, and before the option text actually
# recommends shooting something else, both in percentage points of 2D6 charge
# chance. A one-pip shift (e.g. 4+ to 5+, 92% -> 83%) is inside the noise of an
# approximate casualty estimate; losing half your chance is not.
CHARGE_COST_MIN_DROP_PCT = 15.0
CHARGE_COST_SERIOUS_DROP_PCT = 30.0


def _survivors_after_expected_casualties(squad, target, kills):
    """Which models of `target` are still standing after `kills` of them are
    destroyed by `squad`'s shooting - closest to the shooter first.

    The ordering is not a guess: attacks must be allocated to the closest
    eligible model of the target unit, so casualties come off the FRONT of the
    unit, which is exactly why shooting a unit lengthens the run into it."""
    by_distance = sorted(
        target.models,
        key=lambda m: min(edge_distance(m, shooter) for shooter in squad.models),
    )
    return by_distance[kills:]


def _charge_cost_of_shooting(squad, target, charge_controller):
    """The one number behind "don't shoot the unit you mean to charge": the
    charge roll this squad needs against `target` now, versus the roll it
    needs after its own shooting has killed the target's closest models.

    User-supplied tactical rule ("Es ist ungünstig auf einen Squad zu
    schießen, den man chargen will, weil man dann im Zweifel seine
    Charge-Distanz vergrößert"). Deliberately NOT a prompt sentence: the size
    of the effect is a property of the target's formation, not of the rule -
    against a tightly packed unit, killing three models moves the front edge
    barely at all, against a single file it can move it several inches and
    take the charge out of reach entirely. A prompt rule would have to be
    obeyed blindly in both cases; a computed roll-vs-roll can be weighed. Same
    reasoning (and same place in the option text) as _matchup_hint()'s wound
    threshold, which replaced "here are S and T, work it out".

    Returns "" whenever there is nothing to warn about: no charge possible
    this turn anyway, the target out of charge range to begin with, too few
    expected casualties to move the front edge, a front edge that does not
    move, or a shift too small to matter (see CHARGE_COST_MIN_DROP_PCT - a
    92%-to-83% charge is not a trade-off, and printing one as if it were
    trains exactly the over-cautious reading this file has had to undo twice
    already). Approximate in exactly the ways expected_kills() is (see its
    docstring) - it answers "roughly how much reach does this shot cost me",
    which is what the choice between two targets needs."""
    if charge_controller is None:
        return ""
    turn_tracker = getattr(charge_controller, "turn_tracker", None)
    if turn_tracker is not None and (
        turn_tracker.turn_owner != squad.owner or turn_tracker.phase != PHASE_SHOOTING
    ):
        # A reactive snap shot (Fire Overwatch, 15.08/15.09) happens in the
        # OPPONENT's turn, where this squad has no charge to protect.
        return ""
    if not charge_controller.can_declare_charge(squad, ignore_phase=True):
        return ""

    gap_now = squad.min_distance_to(target)
    if gap_now > CHARGE_RANGE_IN:
        return ""  # rule 11.02: not a chargeable target either way, so shooting it costs nothing
    kills = observation.expected_kills(squad, target)
    expected = int(round(kills["models_killed_per_turn"])) if kills else 0
    if expected <= 0:
        return ""

    survivors = _survivors_after_expected_casualties(squad, target, expected)
    needed_now = math.ceil(gap_now)
    if not survivors:
        return (
            f"; this shot is expected to destroy the unit outright "
            f"(~{expected} of {len(target.models)} models), so no charge is needed"
        )
    gap_after = min(edge_distance(a, b) for a in squad.models for b in survivors)
    needed_after = math.ceil(gap_after)
    if needed_after <= needed_now:
        return ""  # packed formation: the front edge barely moves, no trade-off to report
    if gap_after > CHARGE_RANGE_IN:
        return (
            f"; you could charge it on {needed_now}+ "
            f"({_charge_roll_probability(needed_now):.0f}%) right now, but killing its ~{expected} closest "
            f"models leaves the survivors {gap_after:.1f}\" away - out of charge range entirely this turn"
        )
    before = _charge_roll_probability(needed_now)
    after = _charge_roll_probability(needed_after)
    if before - after < CHARGE_COST_MIN_DROP_PCT:
        return ""
    advice = (
        " - shoot a different unit if you mean to charge this one"
        if before - after >= CHARGE_COST_SERIOUS_DROP_PCT else ""
    )
    return (
        f"; you could charge it on {needed_now}+ ({before:.0f}%) right now, "
        f"but killing its ~{expected} closest models pushes that to {needed_after}+ "
        f"({after:.0f}%){advice}"
    )


def _choose_shooting_target_and_weapon(agent, memory, player, all_tokens, shooting_controller, squad, on_thinking, greater_good_controller=None, plan=None, charge_controller=None):
    """User report: the AI had no way to know which of several valid
    targets was already Spotted (For The Greater Good, game/greater_good.py)
    - is_guided_attack() applies its +1 BS (and, if the marking Observer
    itself has MARKERLIGHT, ignores cover too) automatically once a target
    IS chosen, but nothing ever surfaced that status to the choice itself:
    build_observation() only sends name/owner/wounds/positions, and the
    plain "shoot {target.name}" text carried no hint either - so preferring
    a marked target (per ai/claude_agent.py's SYSTEM_PROMPT guidance) wasn't
    something Claude could actually act on, only something it was told to
    want. Appending "(Spotted - Guided bonus)" to an already-marked target's
    own option text is the fix - same principle as every other trade-off in
    this file: the option's own description carries whatever's needed to
    weigh it, not a separate lookahead/inference step.

    Second user report, same underlying gap: a weapon-vs-armor mismatch (see
    _ranged_weapon_summary()'s own docstring) went unnoticed for the exact
    same reason - nothing told Claude what it was shooting WITH or what the
    target could actually shrug off. Both halves of that matchup are now
    attached to every shoot option too.

    Third report, and the reason _shot_value_hints() sits alongside them: the
    matchup hint alone ranks targets by how EASY they are to wound, which is
    the wrong way round for a specialist and sent Deffkopta Rokkits into
    Stealth Battlesuits while vehicles stood in range."""
    targets = sorted({t.squad for t in shooting_controller.valid_target_models(all_tokens)}, key=lambda s: s.name)
    options = [{"type": "hold_fire", "squad": squad.name, "description": f"{squad.name}: hold fire"}]
    weapon_summary = _ranged_weapon_summary(squad)
    # The enemy unit this turn's plan assigned to this squad, if any - the
    # plan aims a squad's movement, shooting AND charge at one target for the
    # whole turn (see _planned_enemy_target()), so if that unit is shootable
    # right now, say so on its own option rather than leaving the plan as
    # unattached background text Claude has to re-derive the link from.
    planned_target = _planned_enemy_target(squad, plan, all_tokens)
    # Computed across the whole candidate set, not per option, because the
    # useful statement is a comparison ("the most valuable shot available")
    # and that cannot be made one target at a time.
    value_hints = _shot_value_hints(squad, targets)
    for target in targets:
        guided = greater_good_controller is not None and greater_good_controller.is_guided_attack(squad, target)
        suffix = " (Spotted - Guided bonus: +1 to hit, and ignores cover if marked with a Markerlight)" if guided else ""
        if target is planned_target:
            suffix += " [this is the target your turn plan assigned to this squad]"
        options.append({
            "type": "shoot", "squad": squad.name, "target": target.name,
            "description": (
                f"{squad.name} (weapons: {weapon_summary}): shoot {target.name} "
                f"({_target_profile_hint(target)}{_matchup_hint(squad, target)}"
                f"{value_hints.get(target.name, '')})"
                f"{_charge_cost_of_shooting(squad, target, charge_controller)}{suffix}"
            ),
        })

    chosen = _choose(agent, all_tokens, shooting_controller.turn_tracker, options, player, on_thinking)

    if chosen["type"] == "hold_fire":
        shooting_controller.cancel()
        memory.declined_shoot.add(squad.name)
    else:
        target = _squad_by_name(chosen["target"], all_tokens)
        shooting_controller.choose_target_squad(target)
        # STOP HERE if picking the target opened a decision. Rule 10.02's
        # select-targets step is the trigger for every target reaction
        # (Psychic Shield, Stim Injectors, 'Ard as Nails), and choose_weapon()
        # below immediately throws the Hit roll - so doing both in one call
        # put the dice on screen before the defender had answered. User
        # report: "bei psychic shield kann ich erst entscheiden, wenn der hit
        # roll schon gewuerfelt wird. das ist falsch. die ki muss mit dem
        # hitroll warten, bis ich mich entschieden habe."
        #
        # Worse for Psychic Shield specifically, which is why it surfaced
        # there: answering it can make the selection that just happened
        # ILLEGAL (see game/psychic_shield.py), so the Hit roll was being
        # thrown for a target the attacker was about to lose.
        #
        # Returning is enough - nothing is left half-done. _is_blocked()
        # treats a pending decision as a hard stop, and once it is answered
        # _handle_shooting() resumes this activation either way: at
        # CHOOSING_WEAPON if the answer left the target alone, or at
        # CHOOSING_TARGET if Psychic Shield undid it. Both branches already
        # exist above.
        if shooting_controller.decision_manager is not None and shooting_controller.decision_manager.is_pending:
            return True
        weapons = shooting_controller.weapon_eligibility()
        if weapons:
            shooting_controller.choose_weapon(weapons[0][0])
        # choose_weapon() just kicked off the hit roll - leave it pending,
        # the human clicks through hit/wound/save/damage from here on,
        # exactly like any other shot (see take_one_action()'s docstring).
    return True


def _handle_shooting(agent, memory, player, all_tokens, shooting_controller, explosives_controller, on_thinking, greater_good_controller=None, plan=None, charge_controller=None, arrokon_controller=None, conquering_tyrant_controller=None, game_log=None):
    # Real, severe bug found via user report ("die KI verliert die
    # Kontrolle..."): resume an activation someone ELSE already started
    # for `player`'s squad and left sitting at CHOOSING_TARGET with no
    # target picked yet - most commonly a reactive Fire Overwatch snap shot
    # (rule 15.08/15.09, FireOverwatchController calls
    # shooting_controller.start_snap_shooting() directly, completely
    # outside this function). Without this check, the loop below NEVER
    # notices it (it only ever calls start_shooting() itself, on a squad it
    # chose to begin with) - the activation was reproduced sitting at
    # CHOOSING_TARGET/target_squad=None FOREVER, for the rest of the game,
    # since nothing else could ever pick a target for it either; the only
    # way to unstick it was a human board click on the highlighted target,
    # exactly the "I have to take over" symptom reported. Mirrors
    # _handle_charge()'s own pre-existing "resume" branch (there, for
    # Heroic Intervention) for the identical reason.
    squad = shooting_controller.active_squad
    if (
        squad is not None and squad.owner == player
        and shooting_controller.state == shooting_module.CHOOSING_TARGET
    ):
        return _choose_shooting_target_and_weapon(
            agent, memory, player, all_tokens, shooting_controller, squad, on_thinking,
            greater_good_controller=greater_good_controller, plan=plan, charge_controller=charge_controller,
        )

    # Same shape, one step further along: an activation of `player`'s own
    # that has fired one weapon group and is sitting at CHOOSING_WEAPON with
    # more groups left. In `player`'s OWN Shooting phase the loop below
    # happens to cover this - can_shoot() is still true (the fired group is
    # booked into fired_weapon_types, the others are not), so start_shooting()
    # re-opens the activation and picks the next group. A REACTIVE activation
    # (rule 15.08/15.09's Snap Shooting, which runs in the opponent's turn
    # and is deliberately never booked) has no such fallback: can_shoot()
    # correctly says no outside the unit's own phase, so nothing here would
    # ever choose the next weapon, and the unit would sit at CHOOSING_WEAPON
    # forever with _is_blocked() returning False the whole time - reproduced
    # with a 3-group unit Overwatching (2 groups left, nothing pending, no
    # caller). Exactly the hang _handle_fight() already has its own
    # CHOOSING_WEAPON resume branch for, and for the identical reason.
    #
    # The target is NOT re-picked here: rule 10.02 selects targets once, for
    # the whole activation, before any attack is resolved.
    if (
        squad is not None and squad.owner == player
        and shooting_controller.state == shooting_module.CHOOSING_WEAPON
        and shooting_controller.current_group is None
    ):
        weapons = shooting_controller.weapon_eligibility()
        if weapons:
            shooting_controller.choose_weapon(weapons[0][0])
        else:
            # Nothing left that can reach the chosen target - end the
            # activation rather than returning True forever without progress.
            shooting_controller.stop_shooting()
        return True

    if greater_good_controller is not None:
        for squad in sorted(_all_squads(all_tokens), key=lambda s: s.name):
            if squad.owner != player:
                continue
            if _handle_greater_good_for_squad(agent, memory, player, all_tokens, squad, greater_good_controller, shooting_controller, on_thinking):
                return True

    if explosives_controller is not None:
        for squad in sorted(_all_squads(all_tokens), key=lambda s: s.name):
            if squad.owner != player:
                continue
            if _handle_explosives_for_squad(agent, memory, player, all_tokens, squad, explosives_controller, on_thinking):
                return True

    # Before the shoot loop below, not after: The Arro'kon Protocol's own
    # TARGET clause is "a unit that has NOT been selected to shoot this
    # phase", so an offer made after the unit has fired would be illegal.
    if arrokon_controller is not None:
        for squad in sorted(_all_squads(all_tokens), key=lambda s: s.name):
            if squad.owner != player:
                continue
            if _handle_arrokon_for_squad(agent, memory, player, all_tokens, squad, arrokon_controller, on_thinking):
                return True

    # Awakened Dynasty's Conquering Tyrant, ahead of the shoot loop for the
    # same reason Arro'kon's own loop is: "has not been selected to shoot this
    # phase". Deterministic, so a "yes" costs no agent call.
    if _handle_conquering_tyrant(player, all_tokens, shooting_controller,
                                 conquering_tyrant_controller, game_log):
        return True

    for squad in sorted(_all_squads(all_tokens), key=lambda s: s.name):
        if squad.owner != player or squad.name in memory.declined_shoot or not shooting_controller.can_shoot(squad):
            continue

        shooting_controller.start_shooting(squad)
        if shooting_controller.state == shooting_module.CHOOSING_SHOOTING_TYPE:
            shooting_controller.choose_shooting_type(shooting_controller.available_types[0])
        if shooting_controller.state != shooting_module.CHOOSING_TARGET:
            continue  # couldn't actually start (e.g. no eligible shooting type at all) - try the next squad

        return _choose_shooting_target_and_weapon(
            agent, memory, player, all_tokens, shooting_controller, squad, on_thinking,
            greater_good_controller=greater_good_controller, plan=plan, charge_controller=charge_controller,
        )
    return False


def _handle_crushing_impact_for_squad(agent, memory, player, all_tokens, squad, crushing_impact_controller, on_thinking):
    """Rule 15.06 (Crushing Impact, Core Stratagem, 1CP): WHEN a friendly
    MONSTER/VEHICLE unit ends a charge move, a real decision separate from
    the charge itself - checked once per squad per phase (memory.
    declined_crushing_impact, same "the engine has no 'declined' concept of
    its own" reasoning as declined_shoot/declined_charge/declined_
    explosives). Returns True if a decision was made.

    Gap found via a dedicated audit ("welche decision points fehlen noch in
    agent_driver.py"): CrushingImpactController is fully wired for a human
    (ActionPanel button, board-click enemy/model selection - see main.py)
    but this file never referenced it at all, so the AI's own MONSTER/
    VEHICLE squads (e.g. Crisis Starscythe Battlesuits - the current
    roster's only unit type that can charge into engagement at all) never
    got the option, even after a successful charge."""
    if squad.name in memory.declined_crushing_impact or not crushing_impact_controller.can_use(squad):
        return False

    options = [
        {"type": "no_crushing_impact", "squad": squad.name, "description": f"{squad.name}: don't use Crushing Impact"},
        {
            "type": "crushing_impact", "squad": squad.name,
            "description": (
                f"{squad.name}: Crushing Impact (1CP) - roll a number of D6 equal to this unit's Toughness; "
                "each 1 deals a mortal wound to this unit, each 5+ deals a mortal wound to the enemy it charged"
            ),
        },
    ]
    chosen = _choose(agent, all_tokens, crushing_impact_controller.turn_tracker, options, player, on_thinking)
    if chosen["type"] == "no_crushing_impact":
        memory.declined_crushing_impact.add(squad.name)
        return True

    crushing_impact_controller.start(squad)  # TARGET is trivial (always this squad) - the CP is spent right here
    if crushing_impact_controller.state != crushing_impact_module.CHOOSING_ENEMY:
        return True  # can_use()'s preconditions somehow stopped holding - nothing more to do this call

    enemies = sorted(crushing_impact_controller.eligible_enemy_squads(), key=lambda s: s.name)
    if len(enemies) == 1:
        enemy = enemies[0]
    else:
        # A real choice when engaged with more than one enemy unit - which
        # one takes the potential mortal wounds.
        enemy_options = [
            {
                "type": "target_enemy", "squad": squad.name, "target": e.name,
                "description": f"{squad.name}: Crushing Impact against {e.name}",
            }
            for e in enemies
        ]
        chosen2 = _choose(agent, all_tokens, crushing_impact_controller.turn_tracker, enemy_options, player, on_thinking)
        enemy = _squad_by_name(chosen2["target"], all_tokens)
    crushing_impact_controller.choose_enemy(enemy)

    if crushing_impact_controller.state == crushing_impact_module.CHOOSING_MODEL:
        # Homogeneous squads - any qualifying model rolls the same D6 count
        # (its own Toughness), so no real choice, no extra agent.decide() call.
        models = crushing_impact_controller.choosable_models()
        if models:
            crushing_impact_controller.choose_model(models[0])
    return True


def _shooting_specialist_charge_block(squad):
    """Why this unit is not offered a charge at all, or None if it may charge.

    User report, from a game in which the Lokhust Heavy Destroyers charged
    Howling Banshees + Jain Zar and the Immortals charged Striking Scorpions:
    "havey destroyer - die sollten nicht chargen. das sind fernkampf
    einheiten. erst recht keine so starken nahkampfeinheiten, wie banshees.
    baue gerne eine charge sperre ein, wenn die fernkampfwaffen so extrem viel
    staerker sind als die nahkampfwaffen. [...] aber da musst du vorsichtig
    sein. manche einhetien sind sowohl nahkaempfer als auch fernkaempfer. wie
    zb shard of the void dragen. da soll die sperre nicht greifen."

    WITHHELD RATHER THAN ARGUED AGAINST. Offering the charge with a warning
    attached is the shape this file has been caught by before (the rearward
    staging points, the three charge odds to choose between): a list with a
    bad entry plus the hope that the model reads the sign does not work, and
    the option that should never be taken should not be in the list. It also
    saves the API call the choice would have cost.

    THE MEASUREMENT IS game/combat_focus.py's, not a second one here, and it
    is deliberately defender-FREE even though a target is available at this
    point. A per-target ratio was built first and measured, and it does not
    separate: against 1-wound T2 Gretchin everything wounds, so the Immortals
    come out at 1.03 there while the Necron Warriors - a unit that must stay
    free - reach 1.19 against a Deff Dread. The two sets overlap, and a
    threshold inside an overlap decides by whichever enemy happens to stand
    nearest. The unit's own profile does separate, cleanly and with a factor
    of six of headroom on the case the user named; see that module's
    docstring for both bands.

    The 1" the charge itself is worth is NOT weighed against the shooting it
    costs, and that is the point rather than an omission: for a unit whose
    guns are worth 1.4x its fists, being locked in engagement range is a
    running cost for as long as the combat lasts, and no single-turn
    comparison sees that.
    """
    if not combat_focus.is_shooting_specialist(squad):
        return None
    return (
        f"not offered a charge - this is a shooting unit ("
        f"{combat_focus.describe_ratio(squad)}), so a charge trades its best attack for "
        f"its worst and locks it out of shooting for as long as the fight lasts"
    )


def _charge_trade_note(squad, target):
    """What this charge is WORTH and what it COSTS, in the same points-per-turn
    the planner is already given for the same pairing.

    THE REPORTED FAILURE, and why this is an option-text change rather than a
    second charge block. A 21-model Necron Warriors blob charged an Avatar of
    Khaine; measured against those two datasheets, the charge removes 7.5
    points a turn (0.0 models - 3% of a one-model unit) while the Avatar's own
    attacks take 89.1 points of Necron Warriors back every turn the fight
    lasts, and the fight in the log did exactly that: 2 of 21 models reached
    engagement range and dealt zero wounds.

    Both numbers already existed. ai/observation.py's threat_assessment()
    reports them, and in the very log this was reported from the PLANNER - the
    one decision that receives them - refused this charge three turns running
    and said why ("Charging the Avatar trades down badly (345 vs 250 pts)").
    The tactical layer made it, because squad_summary() carries no valuation at
    all and the option said only how likely the roll was. That is an A/B on the
    information, run by the game itself: the same model family, the same board,
    the same turn, right with the numbers and wrong without them.

    So this is the same fix the odds already are, ten lines up - the option
    text is where a charge's trade-offs belong in this file, and for the same
    stated reason ("it belongs in the option's own text rather than being
    something Claude is expected to infer").

    A SECOND WITHHOLDING BLOCK WAS MEASURED AND REJECTED, and the measurement
    is why this is not one. Over the two AI armies against every shipped enemy
    list - 2070 attacker/defender pairings - the reported charge sits at
    gain/loss 0.08, in the worst 1.7%, but the population it would have to be
    separated from is continuous: among units the existing shooting-specialist
    block does not already stop, the share of the target a charge removes runs
    0.01, 0.01, 0.02, 0.03 (the reported case), 0.04, 0.05, 0.06, 0.07, 0.08
    with no gap anywhere in it, and the cheap-screen charges that tie up a gun
    line sit in the same range as the hopeless ones. A threshold there would
    land inside an overlap and decide by whichever enemy happened to stand
    nearest - the exact failure _shooting_specialist_charge_block()'s own
    docstring records for the per-target ratio it rejected. Withholding is the
    right answer for a choice that should NEVER be taken; this one sometimes
    should.

    Returns "" for a pairing that cannot be valued (an unpriced army, or a unit
    with nothing that attacks), rather than a zero that would read as "this
    charge is worthless"."""
    gain = observation.damage_value(squad, target, melee=True)
    loss = observation.damage_value(target, squad, melee=True)
    got = observation.expected_kills(squad, target, melee=True)
    if got is None:
        return ""
    return (
        f" - it would remove about {got['models_killed_per_turn']:.1f} of its models "
        f"({gain:.0f} pts/turn) and that unit's own attacks would take about "
        f"{loss:.0f} pts/turn of this squad back for as long as the fight lasts"
    )


# How the slot-first charge (_charge_slot_first) treats its followers: how
# many ranked slots the LEAD tries, and how close behind a placed squadmate a
# model that reaches no slot of its own is walked (edge to edge - inside
# _LANDING_COHERENCY_IN so the landing search and this agree on "beside").
_SLOT_FIRST_LEAD_TRIES = 12
_CHARGE_TRAIL_EDGE_IN = 1.5


def _charge_slot_first(movement_controller, squad, target_squad, max_distance, slots):
    """The charge as a player makes it: pick the spot, walk the lead model
    there along a real path, bring the rest up behind it. Tried BEFORE the
    rigid-shove sweep, and for every unit - not only those Dense terrain
    stops (see _run_charge_attempts()).

    WHY. The thirteen swept approaches all begin the same way: the whole
    formation is shoved rigidly toward the nearest own/enemy pair, and only
    what is left of the roll is then spent finding a slot. When the nearest
    pair's line runs into a wall the unit may not END on (13.05), or into a
    third unit's Engagement Range, every approach loses most of the roll
    before phase 2 starts. Both reported charges were like that, and both were
    physically possible: brute-forced on the log's own boards, the Lychguard
    (case A, 12" roll) had legal engaged end spots for two of six models
    ~11" away round the flank, the C'tan (case B, 6" roll) five spots on the
    far side of its own Warriors - and all thirteen approaches failed. The
    Movement phase has had A* for exactly this for a long time; the charge's
    only routed approach (_charge_along_route) is gated on _blocked_by_walls(),
    which is False for every AI unit since walls became free to cross, so it
    never ran. This approach is not gated: it routes around whatever the
    ENGINE will not let the unit end in.

    HOW. `slots` is the legal engagement ring (built once by the ladder).
    Leads are tried in order - the unit's melee characters first (rule 12.05,
    game/front_rank.py), then the rest nearest to the target first - until
    one lands, at most _SLOT_FIRST_LEAD_TRIES routes in all. For each of a
    lead's ranked reachable slots, tightest first: a straight leg if the line
    is clear, else find_route() with every enemy BASE as a hard blocker
    (bases stop transit, 03.01) and nothing else - padding the non-targets by
    Engagement Range, the obvious way to keep the route out of ground the
    charge may not END on (11.04), was measured and rejected: on case B it
    finds no path at all (the only way round the Warriors skims the
    Avengers' range), on case A it lengthens the best path from 12.26" to
    14.05". What a leg may not END on is the engine's question, asked per
    waypoint: a waypoint try_commit_segment() refuses (a squadmate's base, a
    third unit's Engagement Range, Dense terrain) is re-landed within reach
    by the landing search (_free_landing_near, caller "charge-route"), and
    only if that fails too does the slot fall. The first slot the lead really
    ends engaged on is kept. Then the followers, nearest to the lead's
    landing first: each walks the SAME routed step to a slot of its own
    within its budget, else to a spot _CHARGE_TRAIL_EDGE_IN behind the
    nearest squadmate already placed (eight bearings round it, nearest to
    the follower first); a follower's step is kept only when it lands
    legally AND within rule 09.02's 2" of the placed set, so the unit grows
    outward from the lead as one connected group. Measured before this was
    routed (measure_charge_scenes.py --hard --diagnose): of 14 charges that
    a legal path could complete, the lead landed in 8 and the followers -
    walking straight with the +-45 degree dodge - lost 7 of those 8.

    Once the unit stands connected and engaged, phase 2 of the ordinary
    charge (_spread_into_engagement) runs over it with whatever budget the
    followers have left, so a model that only trailed a squadmate still
    closes onto a slot if it can - measured without that pass, the approach
    completed more charges than the sweep and put FEWER models into the fight
    (100 hard scenes: 97 completed / 273 engaged against 92 / 314).

    Returns True if the unit ends in one connected group with at least one
    model engaged with the target - the caller confirms it like any approach;
    otherwise puts everything back exactly as it found it and returns False,
    and the sweep runs as before. Every step is validated by the engine; this
    only chooses where to aim."""
    if not slots or not squad.models or not target_squad.models:
        return False
    if movement_controller.move_mode != "charge":
        return False
    snapshot = _position_snapshot(movement_controller, squad)

    def undo(model):
        x, y, waypoint, remaining = snapshot[model.id]
        model.x_in, model.y_in = x, y
        movement_controller.last_waypoint[model.id] = waypoint if waypoint is not None else (x, y)
        if remaining is not None:
            movement_controller.remaining_range[model.id] = remaining

    def engaged(model):
        return any(edge_distance(model, e) <= ENGAGEMENT_RANGE_IN for e in target_squad.models)

    by_gap = sorted(squad.models, key=lambda m: min(edge_distance(m, e) for e in target_squad.models))
    fighters = front_rank.front_rank_models(squad)
    leads = list(fighters) + [m for m in by_gap if m not in fighters]
    board_w, board_h = movement_controller.board_width_in, movement_controller.board_height_in

    def walk(model, waypoints):
        """Every leg through the engine; a leg the engine refuses to END is
        re-landed nearby - transit is not the question, the end point is."""
        for wx, wy in waypoints:
            before = (model.x_in, model.y_in)
            model.x_in, model.y_in = movement_controller.clamp_move(model, wx, wy)
            ok, _errors = movement_controller.try_commit_segment(model)
            if ok:
                continue
            model.x_in, model.y_in = before
            spot = _free_landing_near(model, (wx, wy), squad, movement_controller, [],
                                      caller="charge-route")
            if spot is None:
                return False
            model.x_in, model.y_in = movement_controller.clamp_move(model, spot[0], spot[1])
            ok, _errors = movement_controller.try_commit_segment(model)
            if not ok:
                model.x_in, model.y_in = before
                return False
        return True

    lead = None
    tries = 0
    for candidate_lead in leads:
        if tries >= _SLOT_FIRST_LEAD_TRIES:
            break
        hard_obstacles = pathfinding.blocking_obstacles_for(candidate_lead, movement_controller.obstacles)
        hard_models = pathfinding.enemy_models_for(candidate_lead, movement_controller.all_tokens)
        start = (candidate_lead.x_in, candidate_lead.y_in)
        for slot in _ranked_free_slots(candidate_lead, slots, [], max_distance, must_close_to_1in=True,
                                       squad=squad, limit=_SLOT_FIRST_LEAD_TRIES):
            if tries >= _SLOT_FIRST_LEAD_TRIES:
                break
            tries += 1
            goal = (slot[0], slot[1])
            if pathfinding._direct_line_clear(start, goal, hard_obstacles, hard_models, candidate_lead.radius_in):
                route = [goal]
            else:
                route = pathfinding.find_route(start, goal, candidate_lead.radius_in, max_distance,
                                               hard_obstacles, hard_models, board_w, board_h)
                if not route or math.dist(route[-1], goal) > 0.35:
                    continue
            if walk(candidate_lead, route) and engaged(candidate_lead):
                lead = candidate_lead
                break
            undo(candidate_lead)
        if lead is not None:
            break
    if lead is None:
        return False

    placed = [lead]
    claimed = [(lead.x_in, lead.y_in)]

    def touches_placed(model):
        return any(edge_distance(model, p) <= _LANDING_COHERENCY_IN for p in placed)

    def routed_step(model, goal, budget):
        """One follower's walk to `goal` by a legal path within `budget`,
        kept only if it lands touching the placed set; else undone."""
        hard_obstacles = pathfinding.blocking_obstacles_for(model, movement_controller.obstacles)
        hard_models = pathfinding.enemy_models_for(model, movement_controller.all_tokens)
        start = (model.x_in, model.y_in)
        if math.dist(start, goal) > budget + 1e-9:
            return False
        if pathfinding._direct_line_clear(start, goal, hard_obstacles, hard_models, model.radius_in):
            route = [goal]
        else:
            route = pathfinding.find_route(start, goal, model.radius_in, budget,
                                           hard_obstacles, hard_models, board_w, board_h)
            if not route or math.dist(route[-1], goal) > 0.35:
                return False
        if walk(model, route) and touches_placed(model):
            return True
        undo(model)
        return False

    def trail_points(model, anchor):
        """Eight spots _CHARGE_TRAIL_EDGE_IN behind `anchor`, the one nearest
        this follower first."""
        reach = _CHARGE_TRAIL_EDGE_IN + model.radius_in + anchor.radius_in
        points = [(anchor.x_in + reach * math.cos(a), anchor.y_in + reach * math.sin(a))
                  for a in (k * math.pi / 4 for k in range(8))]
        return sorted(points, key=lambda p: math.dist(p, (model.x_in, model.y_in)))

    followers = sorted((m for m in squad.models if m is not lead),
                       key=lambda m: edge_distance(m, lead))
    for model in followers:
        if touches_placed(model):
            placed.append(model)
            continue
        budget = movement_controller.remaining_range.get(model.id, 0.0)
        done = False
        if budget > 0.05:
            for candidate in _ranked_free_slots(model, slots, claimed, budget, must_close_to_1in=True,
                                                squad=squad):
                if routed_step(model, (candidate[0], candidate[1]), budget):
                    claimed.append((model.x_in, model.y_in))
                    done = True
                    break
            if not done:
                anchors = sorted(placed, key=lambda p: edge_distance(model, p))[:2]
                for anchor in anchors:
                    for point in trail_points(model, anchor):
                        if routed_step(model, point, budget):
                            done = True
                            break
                    if done:
                        break
        if not done:
            _restore_positions(movement_controller, squad, snapshot)
            return False
        placed.append(model)

    if squad.check_coherency() or not any(engaged(m) for m in squad.models):
        _restore_positions(movement_controller, squad, snapshot)
        return False
    # Connected and engaged: now as many into the fight as the leftover
    # budgets allow, every step keeping the unit connected (baseline 0).
    fighters = {id(m) for m in front_rank.front_rank_models(squad)}

    def close_in_pairs():
        return sorted(
            ((m, min(target_squad.models, key=lambda e: edge_distance(m, e))) for m in squad.models),
            key=lambda pair: (id(pair[0]) not in fighters, edge_distance(pair[0], pair[1])),
        )

    _spread_into_engagement(movement_controller, squad, target_squad, CHARGE_TARGET_CLEARANCE_IN,
                            True, 0, close_in_pairs, slots=slots)
    return True


def _charge_nearest_legal_slot(candidate, enemy, movement_controller):
    """How far the nearest model of `candidate` would have to MOVE to stand on
    a legal engagement slot round `enemy` - None when the ring has no legal
    slot at all. The same ring the charge ladder will build (dense, filtered
    for 13.05, other bases and every other unit's Engagement Range), asked
    BEFORE the roll.

    Rule 11.02 makes a target eligible at 12" in a straight line, and that
    stays untouched - a player may declare a charge that cannot be completed.
    The AI's own OFFER is a different matter: a charge onto a unit with no
    legal standing room round it (parked inside Dense terrain, walled in by
    other bases, or with every spot inside a third unit's Engagement Range)
    is a charge that fails from every approach and burns the unit's charge
    for the phase (11.03). Reported twice (measure_reported_moves.py A/B);
    case A's ring had 27 legal slots of 196, the nearest 11.17" off against a
    straight-line gap of 9.3" - the roll the odds quoted was two pips too
    low."""
    keep_out = _charge_keep_out(candidate, enemy, movement_controller.all_tokens)
    slots = _engagement_slots(
        enemy, max_model_radius(candidate), _CHARGE_RING_INNER_EDGE_IN,
        legal=_engagement_slot_filter(candidate, movement_controller, keep_out))
    return min((math.dist((m.x_in, m.y_in), (s[0], s[1]))
                for m in candidate.models for s in slots), default=None)


def _run_charge_attempts(movement_controller, squad, target, max_distance, reopen, confirm):
    """THE charge-move ladder: every approach the AI tries for a declared
    charge, in order, until one confirms. Returns (True, []) on success,
    (False, last_errors) once every approach has been rolled back, or
    (None, last_errors) when a retry's `reopen` did NOT open a move - see
    below; the caller then returns and comes back, exactly as it does when
    the FIRST begin_charge_move() is reacted to.

    WHY A RETRY CAN COME BACK WITHOUT A MOVE. `reopen` is
    ChargeController.begin_charge_move(), and that runs the declaration
    reaction chain (rule "just after an enemy unit has declared a charge":
    Grav-Inhibitor Field, Photon Grenades, Combat Embarkation) EVERY time it
    is called - once per retry, so up to thirteen times for one declaration.
    A reactor that opens a prompt owns the continuation and the move stays
    closed. Measured before this guard existed (Photon Grenades, a human
    defender, a charge that fails on 13.05 from every approach): the human
    was asked TWICE about one declaration, the ladder then placed all five
    models with no move open - clamp_move() hands back the wish and
    try_commit_segment() accepts when nothing is open (game/movement.py) -
    and declined the charge with the second prompt still standing, so the
    answer resumed a charge that was already over. The reactors keep a memo
    of the declaration they have asked about (their `_offered_key`), which is
    what stops the re-prompt; this guard is what stops the placement, for
    any reactor that has no memo, and for the one legitimate case: Combat
    Embarkation re-opening target selection on a retry, which leaves the
    charge with no targets and nothing to open a move for.

    ONE definition, on purpose. _handle_charge() drives it in the game and
    measure_reported_moves.py drives it against a board rebuilt from a game
    log - a harness that copied the loop measured a ladder that could drift
    from the one the AI actually climbs.

    `reopen` re-opens the charge move before every attempt but the first
    (the caller has already opened it for that one; a rolled-back attempt
    leaves the move cancelled). `confirm` is the caller's confirm - the
    ChargeController's, which books the charge, or the bare
    MovementController's in a harness. Success and failure are read from
    movement_controller.errors either way, the same test every mover uses.

    A ROUTED approach is tried first for any unit that cannot cross Dense
    terrain (13.06), ahead of the blind angle sweep. The sweep is two straight
    legs - sidestep, then turn in - which handles one obstacle edge and
    nothing more involved; a walker that has to go through a doorway or round
    the end of a wall needs an actual path. Reported case, reproduced from the
    log's own coordinates: the Deff Dread rolled 9" against a 7.2"
    straight-line gap and the best of all 13 sweep approaches left it 5.01"
    short, while A* finds an 8.4" way round - inside the roll. INFANTRY skip
    it entirely: they walk through the wall, so the direct line already is
    the route. (And so does every AI unit while the wall-crossing house rule
    makes Dense terrain passable for its owner - _blocked_by_walls() asks the
    same seam clamp_move() does.)"""
    last_errors = []
    approaches = list(CHARGE_APPROACH_PLAN)
    routed_first = _blocked_by_walls(squad)
    # The engagement ring, ONCE for the whole ladder: which slots are legal
    # depends on the board and on the target, not on the approach - and the
    # thirteen approaches used to rebuild and re-filter it every time.
    slots = _engagement_slots(
        target, max_model_radius(squad), _CHARGE_RING_INNER_EDGE_IN,
        legal=_engagement_slot_filter(
            squad, movement_controller,
            _charge_keep_out(squad, target, movement_controller.all_tokens)))
    first = True
    for attempt in ["slot-first"] + (["route"] if routed_first else []) + approaches:
        if not first:  # a retry: re-open the move cancelled by the last round
            reopen()
            if movement_controller.move_mode != "charge":
                # Reacted to, or nothing left to declare: no move to place
                # into. Hand the continuation back instead of placing blind.
                return None, last_errors
        first = False
        if attempt == "slot-first":
            _charge_slot_first(movement_controller, squad, target, max_distance, slots)
        elif attempt == "route":
            _charge_along_route(movement_controller, squad, target, max_distance, slots=slots)
        else:
            angle, detour = attempt
            _charge_per_model(movement_controller, squad, target, max_distance,
                              approach_angle_deg=angle, detour_fraction=detour, slots=slots)
        confirm()
        if not movement_controller.errors:
            return True, []
        last_errors = list(movement_controller.errors)
        movement_controller.cancel_move()
    return False, last_errors


def _log_charge_geometry(game_log, squad, target, max_distance, movement_controller=None):
    """Why a charge failed, in the terms the placement works in: how many
    engagement slots the ring offered, how many of them are LEGAL (off walls,
    off other bases, clear of every unit but the target), how many of those
    any model could reach inside the roll, and the nearest one. Written when a
    charge is declined from every approach, so the next report can be read
    instead of reverse-engineered."""
    if game_log is None or not squad.models or not target.models:
        return
    ring = _engagement_slots(target, max_model_radius(squad), _CHARGE_RING_INNER_EDGE_IN)
    legal_note = ""
    slots = ring
    if movement_controller is not None:
        slots = _engagement_slots(
            target, max_model_radius(squad), _CHARGE_RING_INNER_EDGE_IN,
            legal=_engagement_slot_filter(
                squad, movement_controller,
                _charge_keep_out(squad, target, movement_controller.all_tokens)))
        legal_note = f" ({len(slots)} legal)"
    reach = [min(math.dist((s[0], s[1]), (m.x_in, m.y_in)) for m in squad.models) for s in slots]
    within = sum(1 for r in reach if r <= max_distance)
    nearest = min(reach) if reach else float("inf")
    game_log.add(
        f"  [charge geometry] {squad.name} -> {target.name}: {len(ring)} engagement slots{legal_note}, "
        f"{within} within the {max_distance}\" roll, nearest {nearest:.2f}\" away; "
        f"straight-line gap {squad.min_distance_to(target):.2f}\"",
        file_only=True,
    )


def _handle_charge(agent, memory, player, all_tokens, charge_controller, movement_controller, on_thinking, crushing_impact_controller=None, plan=None, game_log=None):
    # Resume a charge this player already declared, now that its roll has
    # been acknowledged (by a human click, in a PREVIOUS frame) and
    # max_distance is known - decide/confirm the actual target and move.
    squad = charge_controller.active_squad
    if squad is not None and squad.owner == player and charge_controller.max_distance is not None:
        eligible = sorted(charge_controller.eligible_charge_target_squads(), key=lambda s: s.name)
        if not eligible:
            # Rule-correct - a roll that reaches nothing cannot name a target -
            # but silent until now, which makes a declared-then-vanished charge
            # indistinguishable in the log from one that was never declared.
            if game_log is not None:
                game_log.add(
                    f'  [charge] {squad.name}: rolled {charge_controller.max_distance}", '
                    f'which reaches no enemy - charge abandoned (rule 11.04)', file_only=True)
            charge_controller.decline_charge_move()
            return True

        # A declaration that ALREADY stands is resumed, never re-decided.
        #
        # This branch is re-entered on a later take_one_action() call whenever
        # the declaration was deferred (see just below), and the AI declares
        # exactly ONE target on purpose: rule 11.04 requires the charging unit
        # to end up engaged with EVERY target it named, so a second one does
        # not add a second opportunity, it adds a second obligation. Choosing
        # again on re-entry could pick a different target - and since a
        # different target is not in charge_targets, it was ADDED rather than
        # swapped, quietly turning a one-target charge into an impossible
        # two-target one.
        #
        # Reported as "das Deff Dread hatte massig Platz und hat trotzdem die
        # Charge nicht geschafft, was ich ueberhaupt nicht verstehe", and the
        # log says exactly that: a single-model walker with an 8" roll failing
        # with 'must be engaged with charge target "1 Riptide Battlesuit 1".;
        # must be engaged with charge target "1 Strike Team 1".' - it had to
        # reach both at once, which no roll was going to do.
        declared = list(charge_controller.charge_targets)
        if declared:
            target = declared[0]
        elif len(eligible) == 1:
            target = eligible[0]
        else:
            planned_target = _planned_enemy_target(squad, plan, all_tokens)
            target_options = [
                {
                    "type": "charge_target", "squad": squad.name, "target": t.name,
                    "description": (
                        f"{squad.name}: charge {t.name}"
                        # The trade, per target. This is the choice the whole
                        # note exists for: two reachable enemies read as
                        # interchangeable when the option says only their
                        # names, and on the reported board they were worth 57
                        # and 7.5 points a turn.
                        + _charge_trade_note(squad, t)
                        + (" [the target your turn plan assigned to this squad]" if t is planned_target else "")
                    ),
                }
                for t in eligible
            ]
            chosen = _choose(agent, all_tokens, charge_controller.turn_tracker, target_options, player, on_thinking)
            target = _squad_by_name(chosen["target"], all_tokens)

        if not declared:
            charge_controller.toggle_charge_target(target)
        if movement_controller.move_mode != "charge":
            # Open the move - unless a reaction's resume already did (the
            # re-entry case just below). begin_charge_move() runs the
            # declaration reaction chain every time it is called, and calling
            # it over an OPEN move asked the chain a second time about the
            # same standing declaration: measured with a reactor that keeps
            # no memo, the second prompt opened while the move stayed open,
            # so the guard below could not see it, and the ladder then
            # declined the charge with that prompt still standing.
            charge_controller.begin_charge_move()
        if movement_controller.move_mode != "charge":
            # Something reacted to the declaration and owns resuming it - a
            # defender's stratagem offered at rule "just after an enemy unit
            # has declared a charge" (game/grav_inhibitor_field.py's
            # ChargeController.on_charge_declared hook). The move has NOT
            # opened, so the per-model sweep below would move nothing and
            # confirm_charge_move() would burn the charge without one. Return
            # and come back once the human has answered: the resume branch at
            # the top of this function re-enters here with the declaration
            # still standing.
            return True
        # User directive: "bitte zwinge die KI beim chargen und pile in
        # Modell für Modell zu bewegen. Keine bulk moves mehr in der Charge-
        # und Fight-Phase." - the whole-squad rigid translation
        # (_translate_squad_for_charge()) used to be tried as a fallback
        # after _charge_per_model() (and, before that, was even tried
        # FIRST) - removed entirely now, per-model is the ONLY charge
        # movement this file performs. A charge roll that's genuinely too
        # short/cramped to physically fit even model-by-model is allowed to
        # fail (check_charge_engagement(), checked below) and gets declined
        # - same "no repair loop" fallback as everywhere else in this file,
        # just without a second geometry to fall back to anymore.
        # Sweep several approach directions instead of only the direct line
        # (see _charge_per_model()'s docstring): a single wall or a badly
        # placed friendly model on the straight line used to fail the whole
        # charge outright, with no second attempt - the Movement phase has
        # had exactly this kind of sweep for a long time, the charge never
        # got one. Each failed attempt is fully rolled back by cancel_move()
        # (positions restored to move_start), so a later angle starts from
        # the same board state as the first.
        # The ladder itself lives in _run_charge_attempts() - the one
        # definition measure_reported_moves.py climbs too. Success is logged by
        # ChargeController.confirm_charge_move() itself, so it covers reactive
        # charges (Heroic Intervention) as well.
        completed, last_errors = _run_charge_attempts(
            movement_controller, squad, target, charge_controller.max_distance,
            reopen=charge_controller.begin_charge_move,
            confirm=charge_controller.confirm_charge_move)
        if completed:
            return True
        if completed is None:
            # A retry's begin_charge_move() was reacted to (see the ladder's
            # docstring): the declaration still stands and someone else owns
            # resuming it. Same answer as the first-attempt guard above -
            # return, and the resume branch re-enters here next call.
            return True

        # Genuinely impossible from any direction - decline, but say WHY.
        # Without this the log only ever showed "illegal move - <squad>
        # snapped back", which left every reported charge failure to be
        # reverse-engineered from raw coordinates (twice, so far).
        if game_log is not None:
            game_log.add(
                f"{player}: {squad.name} could not complete its charge on {target.name} from any "
                f"approach direction ({charge_controller.max_distance}\" roll) - "
                + "; ".join(last_errors),
                category=game_log_module.FAILED_ORDER)
            _log_charge_geometry(game_log, squad, target, charge_controller.max_distance,
                                 movement_controller=movement_controller)
        # A failed charge leaves this unit standing in the open where the plan
        # assumed it would be locked in combat - one of the two events worth
        # re-planning the rest of the turn for (see _maybe_replan_after_events()).
        memory.charge_failed_this_turn = True
        charge_controller.decline_charge_move()
        return True

    # Rule 15.06 (Crushing Impact): offer it for any of player's own
    # MONSTER/VEHICLE squads that already charged this phase, before
    # considering any NEW charge declaration below - see
    # _handle_crushing_impact_for_squad(). Checked against charge_controller.
    # charged_squad_ids directly (not the loop below, which only iterates
    # squads still eligible to DECLARE a fresh charge).
    if crushing_impact_controller is not None:
        for charged_squad in sorted(charge_controller.charged_squad_ids, key=lambda s: s.name):
            if charged_squad.owner != player:
                continue
            if _handle_crushing_impact_for_squad(agent, memory, player, all_tokens, charged_squad, crushing_impact_controller, on_thinking):
                return True

    # Otherwise: look for a new squad to declare (or decline) a charge with.
    # The roll hasn't happened yet, so which specific enemy ends up reachable
    # isn't known - this first choice is just "attempt a charge with this
    # squad at all" (can_declare_charge() already guarantees at least one
    # enemy is within 12" straight-line).
    for candidate in sorted(_all_squads(all_tokens), key=lambda s: s.name):
        if candidate.owner != player or candidate.name in memory.declined_charge or not charge_controller.can_declare_charge(candidate):
            continue

        # A shooting unit is never offered the choice - see
        # _shooting_specialist_charge_block(). Recorded in declined_charge
        # (the same set a real decline writes to) rather than re-derived every
        # frame: the verdict itself is a pure function of the unit and costs
        # nothing to recompute, but the log line does not want repeating, and
        # the set is already reset per battle_round/phase/player.
        #
        # `continue`, not `return True`: no game action was taken, so the next
        # candidate is considered in this same call rather than a frame later.
        blocked = _shooting_specialist_charge_block(candidate)
        if blocked is not None:
            memory.declined_charge.add(candidate.name)
            if game_log is not None:
                game_log.add(f"  [charge] {candidate.name}: {blocked}", file_only=True)
            continue

        # Real user report ("die generischen kroot haben 2 mal einen charge
        # gewürfelt aber dann den charge abgebrochen"): both of those were
        # rule-correct short rolls, not a movement bug - the squad sat 11.3"
        # and 9.0" from its nearest enemy and rolled 8" and 7". But the AI
        # had no way of knowing that: the option said only "declare a
        # charge", with no distance and no odds, so an 8%-likely charge read
        # exactly like a 92%-likely one. Declaring uses up the unit's charge
        # for the phase either way, so this is a real, quantifiable
        # trade-off - and, like every other trade-off in this file (Advance,
        # Fall Back, Crushing Impact), it belongs in the option's own text
        # rather than being something Claude is expected to infer.
        reachable = sorted(
            charge_controller._enemy_squads_within(candidate, CHARGE_RANGE_IN),
            key=lambda s: candidate.min_distance_to(s),
        )
        # Is there anywhere legal to STAND? A target with no legal engagement
        # slot within 12" of any model is a charge that fails from every
        # approach - see _charge_nearest_legal_slot(). Not offered at all
        # (error class 5: the engine must not offer what it does not want
        # chosen), and recorded in declined_charge like the shooting block
        # above so the log says so once per phase.
        standing = {enemy: _charge_nearest_legal_slot(candidate, enemy, movement_controller)
                    for enemy in reachable}
        feasible = [enemy for enemy in reachable
                    if standing[enemy] is not None and standing[enemy] <= CHARGE_RANGE_IN]
        if reachable and not feasible:
            memory.declined_charge.add(candidate.name)
            if game_log is not None:
                game_log.add(
                    f"  [charge] {candidate.name}: not offered - no legal standing room within "
                    f"{CHARGE_RANGE_IN:.0f}\" round any of the {len(reachable)} enemy unit(s) in range "
                    f"(every engagement spot is on Dense terrain, on a base, or inside another "
                    f"unit's Engagement Range)", file_only=True)
            continue
        # The odds are quoted for the enemy that is nearest BY THE MOVE the
        # charge really needs: the longer of the routed gap and the walk to
        # the nearest legal slot.
        nearest_enemy = min(
            feasible,
            key=lambda s: max(_charge_gap(candidate, s, movement_controller), standing[s]),
        ) if feasible else None
        odds_note = ""
        if nearest_enemy is not None:
            straight = candidate.min_distance_to(nearest_enemy)
            # The distance the charge has to actually cover, which is not the
            # straight line for a unit that has to go around terrain - see
            # _charge_gap(). Reporting the straight line told the Deff Dread a
            # 7.2" charge was an 8+ when the wall in the way made it impossible.
            gap = _charge_gap(candidate, nearest_enemy, movement_controller)
            walk = standing[nearest_enemy]
            needed = math.ceil(max(gap, walk))
            detour = ""
            if gap - straight >= CHARGE_DETOUR_REPORT_IN:
                detour = (
                    f" (only {straight:.1f}\" in a straight line, but this unit cannot cross the "
                    f"terrain in between and has to go around it)"
                )
            elif walk - gap >= CHARGE_DETOUR_REPORT_IN:
                # The near side is taken - a base, a wall, a third unit's
                # Engagement Range - and the nearest legal spot is round the
                # flank. Quoted, because the roll has to reach THAT.
                detour = (
                    f" (only {gap:.1f}\" to the unit, but the nearest legal spot to stand is "
                    f"{walk:.1f}\" away - the near side is blocked)"
                )
                gap = walk
            if needed > CHARGE_RANGE_IN:
                odds_note = (
                    f" - nearest target is {nearest_enemy.name}, {gap:.1f}\" away by the route this "
                    f"unit can actually take{detour}, which no 2D6 roll can cover - this charge "
                    "cannot succeed this turn"
                )
            else:
                odds_note = (
                    f" - nearest target is {nearest_enemy.name} at {gap:.1f}\"{detour}, so the 2D6 "
                    f"charge roll has to come up {needed}+ "
                    f"({_charge_roll_probability(needed):.0f}% chance); "
                    "declaring uses up this unit's charge for the phase whether or not the roll gets there"
                    # HOW LIKELY it is was added here for a reported failure;
                    # WHAT IT IS WORTH is the other half of the same sentence,
                    # and its absence is the reported one now. See
                    # _charge_trade_note(): a 92% charge that removes nothing
                    # and costs the squad 89 points a turn read exactly like a
                    # 92% charge that wins the game.
                    + _charge_trade_note(candidate, nearest_enemy)
                )
        planned_target = _planned_enemy_target(candidate, plan, all_tokens)
        if planned_target is not None:
            odds_note += f" [your turn plan assigned {planned_target.name} to this squad"
            # And what THAT one costs, if it is not the unit the odds above are
            # about. Naming the plan's target beside a probability computed for
            # a different unit is the shape of the reported failure: the
            # Meganobz were offered a 97% charge on a Riptide 2.3" away, with
            # "[your turn plan assigned 1 Stealth Battlesuits 1 to this squad]"
            # appended - and the Stealth Battlesuits were 10.1" off, an 8%
            # proposition. The option read as "the plan wants something you
            # cannot reach", so it was declined, and a 97% charge on a 200-point
            # walker was thrown away. Both numbers, or the choice is between a
            # figure for one unit and a name for another.
            if planned_target is not nearest_enemy:
                planned_gap = _charge_gap(candidate, planned_target, movement_controller)
                planned_needed = math.ceil(planned_gap)
                if planned_needed > CHARGE_RANGE_IN:
                    odds_note += (
                        f", but it is {planned_gap:.1f}\" away - out of reach of any 2D6 roll "
                        f"this turn, so declaring means charging {nearest_enemy.name} instead"
                        if nearest_enemy is not None else
                        f", but it is {planned_gap:.1f}\" away - out of reach this turn"
                    )
                else:
                    odds_note += (
                        f", which is {planned_gap:.1f}\" away and would need "
                        f"{planned_needed}+ ({_charge_roll_probability(planned_needed):.0f}%)"
                    )
            odds_note += "]"

        options = [
            {"type": "decline_charge", "squad": candidate.name, "description": f"{candidate.name}: do not charge"},
            {
                "type": "declare_charge", "squad": candidate.name,
                "description": f"{candidate.name}: declare a charge{odds_note}",
            },
        ]
        chosen = _choose(agent, all_tokens, charge_controller.turn_tracker, options, player, on_thinking)
        if chosen["type"] == "decline_charge":
            memory.declined_charge.add(candidate.name)
            # Logged, because the alternative is what actually happened: a
            # reported "why did the Meganobz not charge" had to be answered by
            # reconstructing coordinates and eliminating units alphabetically
            # against the unattributed charge rolls, only to find the unit had
            # declined a 97% charge - a decision that left no trace at all.
            if game_log is not None:
                game_log.add(f"  [charge] {candidate.name}: declined to charge"
                             f"{odds_note or ' (no target in range)'}", file_only=True)
        else:
            movement_controller.select(candidate.models[0])
            charge_controller.declare_charge(candidate)
            # Rolls the 2D6 and leaves it pending - the human clicks to
            # acknowledge (sets max_distance), then a LATER take_one_action()
            # call resumes above with the actual target choice.
        return True
    return False


def _consolidate_toward_squads(movement_controller, squad, targets, clearance):
    """Reuses _charge_per_model()'s per-model geometry (move each model to
    ITS OWN nearest model of the target, independently routed around
    whatever's in its own way), aimed at whichever of `targets` is currently
    nearest - same "aim at the closest mandatory target, let confirm_move()
    validate the full requirement" simplification _pile_in_squad() already
    uses for its own mandatory multi-target case. `targets` are always
    already-mandatory (Ongoing) or already-chosen (Engaging) enemy squads,
    never a free geometric pick among them."""
    nearest = min(targets, key=lambda t: squad.min_distance_to(t))
    _charge_per_model(movement_controller, squad, nearest, CONSOLIDATE_RANGE_IN, clearance=clearance)


def _consolidate_toward_objective(movement_controller, squad, objective, max_distance):
    """Objective Consolidation's target is a mission objective, not an enemy
    squad - no engagement-range clearance math needed (this mode only
    applies when nothing enemy is within CONSOLIDATE_RANGE_IN to begin with,
    rule 12.08's own mode priority), so this just walks each model straight
    toward the objective's terrain area's center (same bounding-box-center
    idea _best_staging_point() already uses for a Dense terrain area)."""
    min_x, min_y, max_x, max_y = objective.terrain_area.bounding_box
    target_point = ((min_x + max_x) / 2, (min_y + max_y) / 2)
    for model in squad.models:
        dx, dy = target_point[0] - model.x_in, target_point[1] - model.y_in
        dist = (dx * dx + dy * dy) ** 0.5
        if dist <= 1e-9 or max_distance <= 0:
            continue
        travel = min(dist, max_distance)
        scale = travel / dist
        new_x, new_y = movement_controller.clamp_move(model, model.x_in + dx * scale, model.y_in + dy * scale)
        model.x_in, model.y_in = new_x, new_y
        movement_controller.try_commit_segment(model)


def _confirm_consolidate_move(consolidate_controller, movement_controller, squad, game_log):
    consolidate_controller.confirm_consolidate()
    if movement_controller.errors:
        # confirm_consolidate() leaves the failed move in place rather than
        # resetting anything itself (mirrors confirm_move()'s own contract) -
        # same "no repositioning retry, just skip it" fallback every other
        # AI move in this file uses.
        consolidate_controller.decline_consolidate()
        if game_log is not None:
            game_log.add(f"{squad.name}'s consolidation move was illegal, skipped instead.",
                     category=game_log_module.FAILED_ORDER)


def _resolve_objective_consolidation(consolidate_controller, movement_controller, squad, game_log):
    """Shared by both places Objective Consolidation can be reached: rule
    12.08's own mode (determine_mode() == OBJECTIVE) and Engaging's escape
    hatch (switch_to_objective_consolidation()) - both leave
    consolidate_controller in the exact same state shape (CHOOSING_OBJECTIVE
    if 2+ candidates, otherwise already auto-resolved via
    _begin_objective_move()), so the same follow-up applies either way."""
    if consolidate_controller.state == consolidate_module.CHOOSING_OBJECTIVE:
        # Consolidate's own 3" range is short enough that 2+ objectives
        # simultaneously in reach of one squad is a rare edge case - no
        # meaningful difference between them worth an extra agent.decide()
        # call, same "no real choice" reasoning as elsewhere in this file.
        choosable = consolidate_controller.choosable_objectives()
        if choosable:
            consolidate_controller.choose_objective(choosable[0])
    if movement_controller.move_mode == "consolidate" and movement_controller.consolidate_targets:
        objective = movement_controller.consolidate_targets[0]
        _consolidate_toward_objective(movement_controller, squad, objective, CONSOLIDATE_RANGE_IN)
    _confirm_consolidate_move(consolidate_controller, movement_controller, squad, game_log)


def _consolidate_squad(agent, memory, player, all_tokens, squad, consolidate_controller, movement_controller, game_log, on_thinking):
    """One consolidation attempt per squad per Fight phase, guaranteed.

    User report ("die KI consolidated nicht nachdem nahkampf mit den boyz auf
    die kroot. ich kann auch nichts machen") - reproduced: an ONGOING
    consolidation whose move comes back illegal (the reported squad had
    fought and was already out of coherency, which no <=3" reposition can
    repair) was declined by _confirm_consolidate_move() but never RECORDED
    anywhere. can_consolidate() therefore stayed True, _handle_fight() picked
    the same squad again on the very next frame - it checks Consolidate
    before the Fight step's own alternation - failed again, and returned True
    forever. The Fight step never advanced, and under auto-play the AI
    re-selected that squad every frame, so the human could not act either.
    Exactly the shape of the earlier PileInController stall, one phase later:
    the engine has no "declined" concept of its own (a human simply doesn't
    click the button), so an attempt that lands nowhere has to be remembered
    HERE or it is not remembered at all.

    The guard is a post-condition rather than another branch in
    _attempt_consolidate() below: the invariant that actually matters is
    "after this call, this squad is either consolidated or off the list",
    and stating it once covers every existing branch and every future one.
    decline_consolidate() is called alongside it because a failed attempt can
    leave the controller mid-selection (CHOOSING_ENGAGING_TARGETS with a live
    consolidate move) - marking it declined without clearing that would swap
    a busy-loop for a stuck panel."""
    if squad.name in memory.declined_consolidate or not consolidate_controller.can_consolidate(squad):
        return False

    acted = _attempt_consolidate(
        agent, memory, player, all_tokens, squad, consolidate_controller, movement_controller, game_log, on_thinking,
    )

    if consolidate_controller.can_consolidate(squad) and squad.name not in memory.declined_consolidate:
        consolidate_controller.decline_consolidate()
        memory.declined_consolidate.add(squad.name)
        if game_log is not None:
            game_log.add(
                f"{squad.name} did not consolidate (rule 12.07 is optional) - not asked again this phase.",
                file_only=True,
            )
    return acted


def _attempt_consolidate(agent, memory, player, all_tokens, squad, consolidate_controller, movement_controller, game_log, on_thinking):
    """Rules 12.07/12.08 (Consolidate): after a squad has fought, it gets an
    optional small (<=3") reposition - checked once per squad per phase
    (memory.declined_consolidate, same "the engine has no 'declined' concept
    of its own" reasoning as declined_shoot/declined_charge/declined_
    explosives/declined_crushing_impact). Real gap found via a dedicated
    audit ("consolidate... heißt das, dass die KI den aktuell immer
    überspringt?"): ConsolidateController is fully wired for a human
    (ActionPanel button, board-click/panel-list target selection - see
    main.py) but this file never referenced it at all - the AI never
    repositioned after fighting, never pulled a nearby unengaged enemy into
    combat, and never moved onto a mission objective after a fight. Returns
    True if a decision was made.

    determine_mode()'s three modes get very different treatment, per rule
    12.08's own text: Ongoing (already engaged - the targets are mandatory,
    exactly like a pile-in) and Objective (unengaged, no enemy within 3" at
    all by definition of this mode - free upside, zero engagement risk) are
    both applied automatically, no agent.decide() call, same "no real
    choice" reasoning _pile_in_squad() already uses for its own mandatory
    targets. Engaging (unengaged, but within 3" of an enemy) is the one
    genuine two-sided call: pulling that enemy into combat forces it to
    fight THIS SAME Fight step immediately if it hasn't already (rule
    12.08) - a real trade-off, so it's the only branch that actually asks.

    Eligibility is checked by _consolidate_squad(), the only caller - which
    also guarantees the squad is off the list afterwards either way."""
    movement_controller.select(squad.models[0])
    mode = consolidate_controller.determine_mode(squad)
    if mode is None:
        memory.declined_consolidate.add(squad.name)
        return True

    if mode == consolidate_module.ONGOING:
        targets = consolidate_controller.ongoing_targets(squad)
        consolidate_controller.start_consolidate(squad)
        if movement_controller.move_mode == "consolidate" and targets:
            _consolidate_toward_squads(movement_controller, squad, targets, PILE_IN_CLEARANCE_IN)
        _confirm_consolidate_move(consolidate_controller, movement_controller, squad, game_log)
        return True

    if mode == consolidate_module.OBJECTIVE:
        consolidate_controller.start_consolidate(squad)
        _resolve_objective_consolidation(consolidate_controller, movement_controller, squad, game_log)
        return True

    # ENGAGING - the one real decision.
    consolidate_controller.start_consolidate(squad)  # -> state == CHOOSING_ENGAGING_TARGETS, active_squad == squad
    targets = sorted(consolidate_controller.eligible_engaging_targets(squad), key=lambda s: s.name)
    target_names = ", ".join(t.name for t in targets)
    options = [
        {"type": "decline_consolidate", "squad": squad.name, "description": f"{squad.name}: don't consolidate"},
        {
            "type": "engage_consolidate", "squad": squad.name,
            "description": (
                f"{squad.name}: consolidate into melee with {target_names} - forces any of them that haven't "
                "fought yet this Fight step to fight immediately"
            ),
        },
    ]
    chosen = _choose(agent, all_tokens, consolidate_controller.turn_tracker, options, player, on_thinking)
    if chosen["type"] == "decline_consolidate":
        if consolidate_controller.can_switch_to_objective():
            # Rule 12.08's own escape hatch: an objective ALSO in reach is
            # the same free-upside, zero-engagement-risk case as the
            # OBJECTIVE branch above, so take it rather than doing nothing.
            consolidate_controller.switch_to_objective_consolidation()
            _resolve_objective_consolidation(consolidate_controller, movement_controller, squad, game_log)
        else:
            consolidate_controller.decline_consolidate()
            memory.declined_consolidate.add(squad.name)
        return True

    for target in targets:
        consolidate_controller.toggle_engaging_target(target)
    consolidate_controller.begin_engaging_move()
    if movement_controller.move_mode == "consolidate":
        _consolidate_toward_squads(movement_controller, squad, targets, PILE_IN_CLEARANCE_IN)
    _confirm_consolidate_move(consolidate_controller, movement_controller, squad, game_log)
    return True


def _squad_remaining_wounds(squad):
    """Wounds still standing between this unit and destruction - the number an
    attack has to beat to wipe it out entirely."""
    return sum(m.current_wounds for m in squad.models if not m.is_dead() and m.current_wounds is not None)


# --- Awakened Dynasty: the three PROACTIVE protocols ------------------------
#
# The three reactive ones (Undying Legions, Eternal Revenant, Vengeful Stars)
# need nothing here: they resolve inside their own controllers via
# auto_players, the same arrangement 'Ard as Nails and Grot Orderly use, so
# the human prompt and the AI answer share one verdict.
#
# These three are different for one reason: rule 15.01 allows ONE use of a
# Stratagem per phase, so the choice is not "should this unit buy it" but
# "which of my units should" - and that is a comparison across the army, which
# only a handler here can make. Same shape, and same reasoning, as
# _handle_unbridled_carnage() and _handle_ere_we_go().
#
# NONE of them takes a memory.declined_* memo, for the reason those two record:
# the verdict is a pure function of the board, so a "no" this frame is a "no"
# next frame and re-deriving it costs nothing. A "yes" cannot repeat because
# can_use() refuses once the grant is up and 15.01 refuses a second use.


def _hungry_void_verdict(squad, fight_controller):
    """Protocol of the Hungry Void (1CP), decided deterministically.

    Returns the GAIN in expected melee wounds (a positive float) if the CP is
    worth spending, else None. The float doubles as the ranking key, since
    15.01 allows one use per phase.

    Measured as a real A/B rather than a heuristic: expected_wounds_against()
    is asked once with the unit's ordinary weapons and once with the boosted
    ones, and the difference is the answer. That matters because +1 Strength
    is worth a great deal or nothing at all depending on where it lands
    relative to the target's Toughness - S7 against T8 is a 5+ to wound, S8
    against T8 is a 4+, while S9 against T8 was already a 3+ and gains
    nothing.

    Like Unbridled Carnage, it is SKIPPED when the unit can already erase an
    engaged target unaided: the sensible line there is to swing at that one
    and keep the CP. And like it, game/damage_estimate.py's documented
    understatement is the safe direction - it can only make a target look more
    survivable than it is, i.e. buy the Stratagem in a borderline case rather
    than skip it."""
    if fight_controller is None:
        return None
    targets = fight_controller.engaged_enemy_squads(squad)
    if not targets:
        return None  # nothing to swing at - the grant would buy nothing
    best = 0.0
    for target in targets:
        plain = expected_wounds_against(squad, target, melee=True) or 0.0
        if plain >= _squad_remaining_wounds(target):
            return None  # can already erase something - save the CP
        boosted = _boosted_melee_wounds(squad, target)
        best = max(best, boosted - plain)
    return best if best > 0 else None


def _boosted_melee_wounds(squad, target):
    """`squad`'s expected melee output against `target` AS IF Hungry Void were
    up, without buying it.

    THE ADJUSTED WEAPONS HAVE TO BE SWAPPED IN, not merely flagged:
    game/damage_estimate.py reads model.weapons directly and knows nothing
    about any adjuster chain, so setting hungry_void_active alone measures
    exactly the unmodified unit. (Found the hard way - the first version of
    this did that and every verdict came back 0.)

    So the grant is applied through the SAME
    protocol_hungry_void.adjusted_weapon() the real fight step calls, the
    copies are swapped in, measured, and swapped back in a finally. Reusing
    that function rather than re-deriving "+1 Strength" also picks up the AP
    half of the grant for free, which a hand-rolled version would miss."""
    was_active = getattr(squad, "hungry_void_active", False)
    originals = {}
    try:
        squad.hungry_void_active = True
        for model in squad.models:
            if model.is_dead():
                continue
            originals[id(model)] = model.weapons
            model.weapons = [
                protocol_hungry_void.adjusted_weapon(weapon, squad)
                if weapon.weapon_type != RANGED_WEAPON else weapon
                for weapon in model.weapons
            ]
        return expected_wounds_against(squad, target, melee=True) or 0.0
    finally:
        squad.hungry_void_active = was_active
        for model in squad.models:
            if id(model) in originals:
                model.weapons = originals[id(model)]


def _handle_hungry_void(player, all_tokens, fight_controller, hungry_void_controller,
                        game_log=None):
    """Buy Hungry Void for whichever of `player`'s units gains most from it.

    Checked BEFORE any unit is selected to fight, because the Stratagem's own
    TARGET clause is "a unit that has NOT been selected to fight this phase" -
    an offer after that point would be illegal."""
    if hungry_void_controller is None:
        return False
    best_squad, best_value = None, 0.0
    for squad in sorted(_all_squads(all_tokens), key=lambda s: s.name):
        if squad.owner != player or not hungry_void_controller.can_use(squad):
            continue
        value = _hungry_void_verdict(squad, fight_controller)
        if value is not None and value > best_value:
            best_squad, best_value = squad, value
    if best_squad is None:
        return False
    if not hungry_void_controller.use(best_squad):
        return False
    if game_log is not None:
        game_log.add(
            f"[hungry void] {player}: {best_squad.name} - +1 Strength is worth about "
            f"{best_value:.1f} extra wound(s) in melee.",
            file_only=True,
        )
    return True


def _conquering_tyrant_verdict(squad, all_tokens, shooting_controller):
    """Protocol of the Conquering Tyrant (1CP), decided deterministically.

    Returns the unit's expected ranged output against the best target it can
    actually reach AT HALF RANGE, or None if the CP would buy nothing. The
    float is the ranking key for 15.01's one use per phase.

    HALF RANGE IS THE WHOLE GATE, and it is what makes this verdict different
    from Unbridled Carnage's: the Stratagem only re-rolls "an attack that
    targets a unit within half range", so a unit whose targets are all further
    off gains literally nothing. That is measured through the Stratagem's own
    applies(), not re-derived - it already knows to read half range through
    game/weapon_range.py rather than off the printed characteristic.

    The re-roll's VALUE scales with how many dice the unit throws, which is
    what expected output stands in for. No attempt is made to model the
    re-roll itself: game/damage_estimate.py explicitly does not, and the
    ranking only needs to be monotonic in volume, not exact."""
    if shooting_controller is None:
        return None
    best = 0.0
    for target in _all_squads(all_tokens):
        if target.owner == squad.owner:
            continue
        if not any(not m.is_dead() for m in target.models):
            continue
        # Would any of this unit's weapons actually be re-rolled against it?
        # Asked with the grant switched on, since applies() gates on it.
        was_active = getattr(squad, "conquering_tyrant_active", False)
        try:
            squad.conquering_tyrant_active = True
            in_half = any(
                protocol_conquering_tyrant.applies(
                    squad, weapon, [(model, weapon)], target)
                for model in squad.models if not model.is_dead()
                for weapon in model.weapons if weapon.weapon_type == RANGED_WEAPON
            )
        finally:
            squad.conquering_tyrant_active = was_active
        if not in_half:
            continue
        expected = expected_wounds_against(squad, target) or 0.0
        best = max(best, expected)
    return best if best > 0 else None


def _handle_conquering_tyrant(player, all_tokens, shooting_controller,
                              conquering_tyrant_controller, game_log=None):
    """Buy Conquering Tyrant for whichever unit throws the most dice at
    something inside half range.

    Ahead of the shoot loop, for the same reason Arro'kon's own loop is: the
    TARGET clause says "has not been selected to shoot this phase"."""
    if conquering_tyrant_controller is None:
        return False
    best_squad, best_value = None, 0.0
    for squad in sorted(_all_squads(all_tokens), key=lambda s: s.name):
        if squad.owner != player or not conquering_tyrant_controller.can_use(squad):
            continue
        value = _conquering_tyrant_verdict(squad, all_tokens, shooting_controller)
        if value is not None and value > best_value:
            best_squad, best_value = squad, value
    if best_squad is None:
        return False
    if not conquering_tyrant_controller.use(best_squad):
        return False
    if game_log is not None:
        game_log.add(
            f"[conquering tyrant] {player}: {best_squad.name} - about {best_value:.1f} "
            f"expected wound(s) against a target inside half range.",
            file_only=True,
        )
    return True


def _sudden_storm_verdict(squad, movement_controller):
    """Protocol of the Sudden Storm (1CP), decided deterministically.

    Returns how many of the unit's ranged weapons would be RESCUED by the
    [ASSAULT] grant, or None if none would be.

    THE GATE IS "WOULD THIS UNIT ADVANCE", and it is the whole point. Rule
    10.05 already lets an Advancing unit fire [ASSAULT] weapons, so this
    Stratagem is worth exactly the weapons that do NOT already have it, on a
    unit that is actually going to Advance. Bought by a unit that then walks,
    it does nothing at all.

    "Would Advance" is read as "cannot reach a target without Advancing",
    which is the only version of the question available at this point in the
    phase - the AI has not yet decided how this unit moves, and the Stratagem's
    window closes once it has. Deliberately conservative: a unit already in
    range of something is assumed to walk and shoot, which is the line that
    cannot waste a CP."""
    if movement_controller is None:
        return None
    rescuable = [
        weapon
        for model in squad.models if not model.is_dead()
        for weapon in model.weapons
        if weapon.weapon_type == RANGED_WEAPON and not weapon.assault
    ]
    if not rescuable:
        return None  # every gun is already [ASSAULT] - the grant buys nothing
    return float(len(rescuable))


def _handle_sudden_storm(player, all_tokens, movement_controller, sudden_storm_controller,
                         shooting_controller=None, game_log=None):
    """Buy Sudden Storm for the unit with the most guns to rescue, but only
    for one that would actually have to Advance to reach anything.

    Bought at the START of the Movement phase, ahead of anything that moves -
    the same placement 'Ere We Go uses, and for the same reason: its own
    window closes once the unit has moved."""
    if sudden_storm_controller is None:
        return False
    best_squad, best_value = None, 0.0
    for squad in sorted(_all_squads(all_tokens), key=lambda s: s.name):
        if squad.owner != player or not sudden_storm_controller.can_use(squad):
            continue
        if shooting_controller is not None and _has_target_without_advancing(
                squad, all_tokens, shooting_controller):
            continue  # it can shoot after a plain move - the grant is wasted
        value = _sudden_storm_verdict(squad, movement_controller)
        if value is not None and value > best_value:
            best_squad, best_value = squad, value
    if best_squad is None:
        return False
    if not sudden_storm_controller.use(best_squad):
        return False
    if game_log is not None:
        game_log.add(
            f"[sudden storm] {player}: {best_squad.name} - {best_value:.0f} ranged weapon(s) "
            f"gain [ASSAULT], so it can Advance and still shoot.",
            file_only=True,
        )
    return True


def _has_target_without_advancing(squad, all_tokens, shooting_controller):
    """Whether this unit already has something it could shoot where it stands.

    Used only to REFUSE Sudden Storm: a unit that can already shoot has no
    reason to Advance, so the [ASSAULT] grant would buy it nothing. Asked
    through the engine's own eligibility, not a distance guess, so "could
    shoot" means what it means everywhere else (range, visibility, engagement).

    Note this is measured BEFORE the unit moves, so it answers "from where it
    stands now" - which is the only version of the question available while
    the Stratagem's window is still open."""
    types = shooting_module.available_shooting_types(squad, all_tokens)
    return any(shooting_controller.has_valid_target(squad, shooting_type, all_tokens)
               for shooting_type in types)


def _unbridled_carnage_verdict(squad, fight_controller):
    """War Horde's Unbridled Carnage (1CP, game/unbridled_carnage.py), decided
    DETERMINISTICALLY - no agent call, per the user: "ki soll diese
    deterministisch einsetzen... es sollte eingesetzt werden, wenn orks ein
    ziel im nahkampf angreifen, dass sie rechnerisch nicht vollständig
    auslöschen."

    Returns the unit's expected melee output (a positive float) if the CP is
    worth spending, or None if it is not - the float doubles as the ranking
    key for which unit gets it, since rule 15.01 allows only ONE use per
    phase and the extra Critical Hits scale with attack volume (with War
    Horde's own Get Stuck In giving every Ork melee weapon [SUSTAINED HITS 1],
    a 5+ crit threshold is worth roughly an extra hit per six attacks).

    "Cannot wipe it out" is read across EVERY engaged enemy unit, not just one
    of them: the stratagem's window closes the instant the unit is selected to
    fight, which is also when its target is chosen, so at decision time there
    is no way to know which enemy it will actually swing at. If one of them
    could be erased outright, the sensible line is to swing at that one and
    keep the CP - so this only fires when NO engaged target can be finished
    off unaided. With a single engaged enemy (the ordinary case) the two
    readings coincide exactly.

    The estimate is game/damage_estimate.py's, with all of its documented
    caveats - notably that it models no [SUSTAINED HITS] at all, so it
    UNDERSTATES an Ork unit's real output. That bias is the safe direction
    here: it can only make the AI judge a target survivable when it is
    borderline, i.e. buy the stratagem in a close case rather than skip it."""
    targets = fight_controller.engaged_enemy_squads(squad)
    if not targets:
        return None  # nothing to swing at - the grant would buy nothing
    best = 0.0
    for target in targets:
        expected = expected_wounds_against(squad, target, melee=True) or 0.0
        if expected <= 0:
            continue  # this unit does nothing to that target either way
        if expected >= _squad_remaining_wounds(target):
            return None  # it can already erase something - save the CP
        best = max(best, expected)
    return best if best > 0 else None


def _handle_grim_reapers(player, all_tokens, grim_reapers_controller, game_log=None):
    """Death Lord's Chosen's Grim Reapers: buy it at the FIRST OPPORTUNITY.

    USER INSTRUCTION, verbatim: "GRIM REAPERS - erste gelegenheit". So there is
    deliberately NO verdict function here, and that absence is the design
    rather than an omission - the three Awakened Dynasty handlers each measure
    what their grant is worth because each can be worth nothing (Hungry Void's
    +1 Strength can fail to cross a wound threshold; Blooming Pestilence's +3"
    is capped away from round 3). A Hit re-roll against anything that is not a
    MONSTER or VEHICLE cannot be worth nothing to a unit that is about to
    fight, so measuring it would only ever produce the same answer more slowly.

    The one thing that IS enforced is the printed TARGET line, and can_use()
    already does it: "has not been selected to fight this phase". That is why
    this runs BEFORE the fight loop, exactly like Unbridled Carnage below - an
    offer after that point would be illegal.

    Deterministic by construction: `sorted(..., key=name)` picks the same unit
    on every replay, and the function takes no `agent`, so it cannot cost an
    API call however it is wired.

    No memory.declined_* memo, for the reason _handle_unbridled_carnage()
    records: the verdict is a pure function of the board, and a "yes" cannot
    repeat because can_use() refuses once the grant is up and rule 15.01
    refuses a second use this phase."""
    if grim_reapers_controller is None:
        return False
    for squad in sorted(_all_squads(all_tokens), key=lambda s: s.name):
        if squad.owner != player or not grim_reapers_controller.can_use(squad):
            continue
        if not grim_reapers_controller.use(squad):
            continue
        if game_log is not None:
            game_log.add(
                f"[grim reapers] {player}: {squad.name} - first eligible TERMINATOR "
                f"unit this Fight phase.", file_only=True)
        return True
    return False


def _handle_unbridled_carnage(player, all_tokens, fight_controller, unbridled_carnage_controller, game_log=None):
    """Buy Unbridled Carnage for whichever of `player`'s own units gains the
    most from it, if any. Returns True if the CP was actually spent, so the
    caller can treat that as this frame's one action.

    Checked BEFORE any unit is selected to fight, because the stratagem's own
    TARGET clause is "a unit that has NOT been selected to fight this phase" -
    an offer after that point would be illegal. Same placement, and same
    reasoning, as The Arro'kon Protocol's loop ahead of the shoot loop in
    _handle_shooting().

    Needs no memory.declined_* memo, unlike every agent-driven stratagem
    handler: the verdict is a pure function of the board, so a "no" this frame
    is a "no" next frame too and re-deriving it costs nothing (no API call and
    no line-of-sight sweep). A "yes" cannot repeat either - can_use() refuses
    once the grant is up, and rule 15.01 refuses a second use this phase."""
    if unbridled_carnage_controller is None:
        return False
    best_squad, best_value = None, 0.0
    for squad in sorted(_all_squads(all_tokens), key=lambda s: s.name):
        if squad.owner != player or not unbridled_carnage_controller.can_use(squad):
            continue
        value = _unbridled_carnage_verdict(squad, fight_controller)
        if value is not None and value > best_value:
            best_squad, best_value = squad, value
    if best_squad is None:
        return False
    if not unbridled_carnage_controller.use(best_squad):
        return False
    if game_log is not None:
        game_log.add(
            f"[unbridled carnage] {player}: {best_squad.name} - expected to strip only "
            f"{best_value:.1f} wound(s) in melee, not enough to destroy any unit it is engaged with.",
            file_only=True,
        )
    return True


def _handle_fight(
    agent, memory, player, all_tokens, fight_controller, pile_in_controller, movement_controller, on_thinking,
    consolidate_controller=None, game_log=None, unbridled_carnage_controller=None,
    hungry_void_controller=None, grim_reapers_controller=None,
):
    # Rule 12.07/12.08 (Consolidate): checked first, for any of player's own
    # squads that have already fought and haven't consolidated (or declined
    # to) yet this phase. can_consolidate() is the single gate - the same one
    # the human UI reads (main.py's ActionPanel) - and it requires the Fight
    # step to be OVER, so this loop is a no-op until then and cannot shuffle
    # the board while units are still striking. Checked before the branches
    # below rather than after them because Fight is the last phase: once the
    # step is DONE those branches return False, which is what lets
    # take_one_action() end the turn - consolidation has to get its frames in
    # first.
    if consolidate_controller is not None:
        for squad in sorted(_all_squads(all_tokens), key=lambda s: s.name):
            if squad.owner == player and _consolidate_squad(
                agent, memory, player, all_tokens, squad, consolidate_controller, movement_controller, game_log, on_thinking,
            ):
                return True

    if fight_controller.state == fight_module.NOT_STARTED:
        # Rule 12.03: piling in is optional, but a real (small, geometry-
        # only) pile-in move is made for each of the AI's own eligible
        # squads - see _pile_in_squad() - rather than always skipping it;
        # skip_pile_in() is only used there as its own no-targets fallback.
        for squad in sorted(_all_squads(all_tokens), key=lambda s: s.name):
            if squad.owner == player and pile_in_controller.can_pile_in(squad):
                _pile_in_squad(pile_in_controller, movement_controller, squad)
                return True
        # Nothing more of Player 2's own to skip - if that was true for
        # BOTH players, the Fight step itself is just waiting on a forced,
        # no-choice-involved click to actually begin (rule 12.04), so the AI
        # takes that step too instead of leaving it to a human middleman.
        if not pile_in_controller.has_pending_squads():
            fight_controller.begin_fight_step()
            return True
        return False

    # Resume a fight this player already started. The CHOOSING_TARGET /
    # CHOOSING_WEAPON handling below used to be reachable ONLY inside the same
    # call that ran select_to_fight() - so once control left this function with
    # one of those states still pending (a weapon group finishes, its dice are
    # acknowledged, and the unit still has further weapons to swing), the very
    # next call fell straight through the SELECTING gate and returned False
    # forever. The unit sat there with its attacks offered and nothing picking
    # them. That is the reported stall, and the screenshot showed it exactly:
    # the Actions panel waiting on "CHOPPA (2/9)" while the AI did nothing.
    # Same shape as the resume branch _handle_charge() already needed.
    if (
        fight_controller.state in (fight_module.CHOOSING_TARGET, fight_module.CHOOSING_WEAPON)
        and fight_controller.fighting_squad is not None
        and fight_controller.fighting_squad.owner == player
    ):
        return _resolve_fight_choices(
            agent, player, all_tokens, fight_controller, fight_controller.fighting_squad, on_thinking)

    if fight_controller.state != fight_module.SELECTING or fight_controller.whose_turn != player:
        return False  # not Player 2's sub-turn in the Fight step's alternation right now

    # War Horde's Unbridled Carnage (1CP): must be bought BEFORE a unit is
    # selected to fight, so it goes ahead of the selection below - and ahead
    # of the _choose() call in it, so a "yes" never costs an extra agent call
    # (the next frame's deterministic check simply says no and falls straight
    # through to selecting).
    if _handle_unbridled_carnage(player, all_tokens, fight_controller, unbridled_carnage_controller, game_log):
        return True

    # Awakened Dynasty's Hungry Void: the same window and the same "not yet
    # selected to fight" TARGET clause, so it sits alongside.
    if _handle_hungry_void(player, all_tokens, fight_controller, hungry_void_controller, game_log):
        return True

    # Death Lord's Chosen's Grim Reapers: the third stratagem sharing this
    # window and the same "not yet selected to fight" TARGET clause. Bought at
    # the first opportunity by user instruction, so it has no verdict function -
    # see _handle_grim_reapers().
    if _handle_grim_reapers(player, all_tokens, grim_reapers_controller, game_log):
        return True

    eligible = sorted(fight_controller.eligible_to_select_now(), key=lambda s: s.name)
    if not eligible:
        if fight_controller.can_pass():
            fight_controller.pass_fighting()
            return True
        return False

    if len(eligible) == 1:
        squad = eligible[0]
    else:
        options = [{"type": "fight_with", "squad": s.name, "description": f"Fight with {s.name}"} for s in eligible]
        chosen = _choose(agent, all_tokens, fight_controller.turn_tracker, options, player, on_thinking)
        squad = _squad_by_name(chosen["squad"], all_tokens)

    fight_controller.select_to_fight(squad)
    # STOP HERE if selecting opened a decision - the Fight-phase twin of the
    # guard _choose_shooting_target_and_weapon() already carries, and it was
    # missing here. select_to_fight() auto-picks the target when a unit is
    # engaged with exactly one enemy (the ordinary case), and THAT is rule
    # 12.02's select-targets step - the trigger for every target reaction
    # (Forewarned, Stim Injectors, 'Ard as Nails). _resolve_fight_choices()
    # below immediately throws the Hit roll, so doing both in one call put
    # the dice on screen before the defender had answered. User report:
    # "forewarned wurde angeboten, da wurde der trefferwurf schon
    # gewuerfelt. das ist zu frueh. das muss ich davor entscheiden."
    #
    # Returning is enough and nothing is left half-done: _is_blocked() treats
    # a pending decision as a hard stop, and once it is answered the
    # CHOOSING_TARGET/CHOOSING_WEAPON resume branch above re-enters
    # _resolve_fight_choices() for this same unit.
    if _defender_is_deciding(fight_controller):
        return True
    return _resolve_fight_choices(agent, player, all_tokens, fight_controller, squad, on_thinking)


def _melee_group_pairs(fight_controller, squad):
    """{attack_key: [(model, weapon), ...]} for the groups this squad can still
    fight with against its chosen target, already filtered by rule 12.02's
    Engagement Range and by the [EXTRA ATTACKS]/[ONE SHOT] locks - i.e. exactly
    what weapon_eligibility() counts, but with the model/weapon pairs kept so
    a group can be valued and checked for overlap. Reaches into fight.py's own
    grouping rather than re-deriving it, same reasoning as the existing
    charge_controller._enemy_squads_within() use above: one source of truth for
    which weapon may still swing.

    Engagement Range comes from the controller's own activation snapshot
    (fight.py's _engaged_with(), rule 12.02), not from a fresh
    model_engaged_with() call: all of a unit's melee attacks are made in one
    activation, so an earlier group's casualties must not shrink a later
    group here either. A live check made this function disagree with
    weapon_eligibility() the moment a target's front models died - the very
    "one source of truth" this docstring claims."""
    target = getattr(fight_controller, "target_squad", None)
    if target is None:
        return {}
    groups = fight_module._melee_attack_groups(
        squad,
        getattr(fight_controller, "_used_other_melee_weapon", set()),
        getattr(fight_controller, "one_shot_used", None),
    )
    return {
        key: [(m, w) for m, w in pairs if fight_controller._engaged_with(m, target)]
        for key, pairs in groups.items()
    }


def _melee_group_value(pairs, target):
    """Expected wounds this melee attack group would inflict on `target` -
    every model in the group swinging its own weapon at its own WS (Power Klaw
    prints a WORSE WS than its wielder, see fight.py's
    effective_weapon_skill(), which is exactly why the choice is not simply
    "the biggest S")."""
    if not pairs or not target.models:
        return 0.0
    d_profile = target.models[0].profile
    return sum(
        observation.expected_wounds(
            weapon, weapon.attacks, fight_module.effective_weapon_skill(model, weapon), d_profile,
        )
        for model, weapon in pairs
    )


def _melee_group_rivals(chosen_pairs, groups):
    """Which of `groups` this squad would GIVE UP by swinging `chosen_pairs`.

    Rule 04.01/24.11: a model makes its melee attacks with one of its melee
    weapons, so the moment it swings one, its other non-[EXTRA ATTACKS]
    weapons are locked out for this activation - that, and only that, makes
    picking a group a real decision. Groups belonging to different models (a
    Boss Nob's Power Klaw and the Boyz' Choppas) do not compete at all: both
    get used, one call after the other, so asking the agent to "choose"
    between them would be a paid-for non-question."""
    committed = {model for model, weapon in chosen_pairs if not weapon.extra_attacks}
    rivals = []
    for key, label, pairs, value in groups:
        if any(model in committed and not weapon.extra_attacks for model, weapon in pairs):
            rivals.append((key, label, pairs, value))
    return rivals


def _choose_melee_weapon(agent, player, all_tokens, fight_controller, squad, weapons, on_thinking):
    """Which melee weapon this unit actually swings - the Fight phase's own
    version of the shooting phase's target choice.

    User report ("im Nahkampf kann nicht einfach alle Waffen nutzen, sondern
    muss sich entscheiden ... die KI müsste sich da natürlich für die
    effizientere Waffe entscheiden"): the rule itself was already enforced by
    the engine (fight.py's _melee_locked_out()/_lock_other_melee_weapon()),
    for the human and the AI alike - but this code picked
    weapon_eligibility()[0], i.e. whichever weapon happened to sit first on
    the model, with no notion of efficiency and no decision at all.

    Two different situations, deliberately handled differently:

    - The hardest-hitting group forecloses another one (a datasheet where one
      model carries two selectable melee weapons): a genuine, irreversible
      trade-off, so it goes to the agent as a real choice between exactly
      those rival groups, with the expected wounds against THIS target printed
      on every option - the same "put the computed consequence in the option
      text" approach as _matchup_hint() and the charge odds.
    - Nothing is foreclosed: no trade-off at all (every remaining group will
      swing on a later call), so no API call - but the groups are ordered
      best-first, which is a real gain rather than cosmetics: if the target is
      destroyed by the first group, the remaining ones never get to swing at
      all, so the hardest-hitting weapon must go first."""
    by_key = _melee_group_pairs(fight_controller, squad)
    target = fight_controller.target_squad
    eligible = [
        (key, label, by_key.get(key, []))
        for key, label, eligible_count, _total in weapons
        if eligible_count > 0 and by_key.get(key)
    ]
    if not eligible or target is None:
        # Only groups whose models cannot reach the chosen target are left
        # (weapon_eligibility() still lists them) - resolving one is a no-op
        # that just drains the queue, exactly as before this function existed.
        fight_controller.choose_weapon(weapons[0][0])
        return

    valued = sorted(
        ((key, label, pairs, _melee_group_value(pairs, target)) for key, label, pairs in eligible),
        key=lambda entry: -entry[3],
    )
    best = valued[0]
    rivals = _melee_group_rivals(best[2], valued[1:])
    if not rivals:
        fight_controller.choose_weapon(best[0])
        return

    contenders = [best] + rivals
    options = [
        {
            "type": "melee_weapon", "squad": squad.name, "weapon": label,
            "description": (
                f"{squad.name}: fight with {label} ({len(pairs)} model(s) in range, "
                f"S{pairs[0][1].strength}/AP{pairs[0][1].ap}/D{pairs[0][1].damage}, "
                f"~{value:.1f} wounds expected against {target.name}) - a model that swings this "
                "cannot also use its other melee weapons this fight"
            ),
        }
        for _key, label, pairs, value in contenders
    ]
    chosen = _choose(agent, all_tokens, fight_controller.turn_tracker, options, player, on_thinking)
    key = next((k for k, label, _p, _v in contenders if label == chosen["weapon"]), best[0])
    fight_controller.choose_weapon(key)


def _defender_is_deciding(fight_controller):
    """Whether the target-selection step just handed the DEFENDER an open
    choice (rule 12.02 is the trigger for Forewarned, Stim Injectors and
    'Ard as Nails).

    Its own function rather than the condition inline twice: both places that
    constitute the select-targets step here must stop at it, and the shooting
    side already learned that lesson one report earlier."""
    manager = getattr(fight_controller, "decision_manager", None)
    return manager is not None and manager.is_pending


def _resolve_fight_choices(agent, player, all_tokens, fight_controller, squad, on_thinking):
    """Pick this unit's fight target and its next melee weapon group. Split out
    of _handle_fight() so it can be re-entered on a LATER call - a unit with
    several weapon groups comes back here once per group, and before this
    existed there was no path back in (see the resume branch above)."""
    if fight_controller.state == fight_module.CHOOSING_TARGET:
        targets = sorted(fight_controller.engaged_enemy_squads(squad), key=lambda s: s.name)
        if len(targets) == 1:
            target = targets[0]
        else:
            target_options = [
                {"type": "fight_target", "squad": squad.name, "target": t.name, "description": f"{squad.name}: attack {t.name}"}
                for t in targets
            ]
            chosen2 = _choose(agent, all_tokens, fight_controller.turn_tracker, target_options, player, on_thinking)
            target = _squad_by_name(chosen2["target"], all_tokens)
        fight_controller.choose_target_squad(target)
        # The multi-target half of the same break point - see the guard in
        # _handle_fight(). This is the path an explicitly chosen target takes,
        # and it raises the very same reactions.
        if _defender_is_deciding(fight_controller):
            return True

    if fight_controller.state == fight_module.CHOOSING_WEAPON:
        weapons = fight_controller.weapon_eligibility()
        if weapons:
            _choose_melee_weapon(agent, player, all_tokens, fight_controller, squad, weapons, on_thinking)
        else:
            # Nothing left to swing with, but the controller is still parked in
            # CHOOSING_WEAPON - end the unit's fight rather than returning True
            # forever with nothing happening.
            if hasattr(fight_controller, "stop_fighting"):
                fight_controller.stop_fighting()
        # choose_weapon() just kicked off the hit roll - leave it pending,
        # same reasoning as _handle_shooting() above.
    return True
