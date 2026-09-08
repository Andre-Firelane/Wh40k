"""The AI's side of rule 03.01's pre-game sequence: Declare Battle Formations
(which units ride in which TRANSPORT, which stay in Strategic Reserves) and
the alternating deployment itself.

Deterministic, with no agent call at all - deliberately, for three reasons:

  * twenty-odd placements would be twenty LLM round trips before the game even
    starts, on a planner whose own timeout is 120 s;
  * this codebase has measured repeatedly that wherever the model INVENTS a
    number (a coordinate) rather than picking from a list, the error rate is
    high - see CLAUDE.md's "unerreichbare Koordinaten" entries;
  * _ingress_landing_score() already reached exactly this conclusion for
    reserve arrival, which is the same kind of decision one phase later.

The one genuinely hard part is that during an ALTERNATING deployment the enemy
is only partly on the board, so scoring line of sight against the enemy models
currently placed is close to meaningless - the first unit down would be scored
against an empty table. So exposure is measured against the enemy DEPLOYMENT
ZONE instead (observation.zone_visibility_from_point), which is fully known
from the first frame and is the ground the enemy will actually occupy."""

import math

from ai import observation
from game import shapes
from ai.agent_driver import (
    _DISEMBARK_FACINGS,
    _all_squads,
    _centroid,
    _ingress_pack_positions,
)
from game import attached_units, combat_focus, deployment, formations, movement, pregame
from game.squad import max_model_radius, squad_has_infiltrators

# Candidate grid over the deploying player's own zone. 2" is fine enough that
# a 12"-deep zone gets six rows, and coarse enough that the LOS probing below
# stays affordable.
DEPLOY_GRID_STEP_IN = 2.0
# Only this many of the nearest-to-goal candidates get the (expensive) full
# score. Same cap, for the same reason, as SCORED_LANDING_CANDIDATES.
DEPLOY_SCORED_CANDIDATES = 40
# How many spots across the enemy deployment zone are probed for line of sight.
# Measured rather than guessed: at 8 probes the score barely discriminated on
# map 1 (only two distinct values across 130 candidate spots, 96 of them tied
# at 0), so "hide the key units" had almost nothing to sort on. At 24 the same
# 130 spots spread across 0-4 on map 1 and 0-5 on map 2, which is enough for
# the ranking to mean something.
DEPLOY_ZONE_PROBE_POINTS = 24
# How many scored spots are actually attempted (each costs up to 8 facings).
DEPLOY_PLACEMENT_ATTEMPTS = 12
# ...and how many for the stricter "fully hidden" first pass. Deliberately much
# smaller: a unit that fits inside a Dense area at all fits at one of the best
# few spots, whereas a unit too big for any ruin fails EVERY attempt and pays
# for the whole ladder before falling through to the normal pass.
#
# Measured on map 2, both armies: the whole Hidden feature costs 4.12s -> 4.60s
# of deployment time for 13 units (about +0.04s each), and capping this at 4
# instead of 12 leaves the Hidden coverage completely unchanged (9/9 and 7/9
# units fully hidden). So the cap is cheap insurance rather than a fix for a
# measured problem - an earlier note here claimed the pre-game wall time
# doubled, which was a bad comparison between a 60-frame and a 900-frame run.
DEPLOY_HIDDEN_ATTEMPTS = 4

# A unit whose best ranged weapon reaches at least this far is treated as a
# shooter: it wants a firing lane, not a hiding hole.
SHOOTER_RANGE_IN = 24.0
# Below this it is a short-ranged body that has to close the distance anyway.
# Only the FALLBACK passenger test now - see TRANSPORT_PASSENGER_PRIORITY.
TRANSPORT_PASSENGER_MAX_RANGE_IN = 18.0

# Datasheets that never ride, whatever room is going spare.
#
# User instruction: "ki soll keine gretchins in die transporter packen". Kept
# as its own named rule rather than left to fall out of the priority lists
# below, because it is a different statement: the lists say who is WANTED and
# in what order, this says who is forbidden even when a transport has no list
# of its own and the generic reach heuristic would happily take them (Gretchin
# carry a 12" blasta, so that heuristic rates them an ideal passenger). The
# reasoning, for whoever extends this: capacity spent on a cheap objective-
# holding body is capacity not spent delivering a threat, and Gretchin are
# worth more standing on ground than being driven somewhere.
TRANSPORT_NEVER_EMBARK = ("Gretchin",)
# A shooter is happiest seeing SOME of the enemy zone but not most of it.
SHOOTER_IDEAL_EXPOSURE = (1, 4)

# Forward progress is bucketed before it is compared, so spots within this many
# inches of each other count as EQUALLY aggressive and are then separated by
# how safe they are.
#
# This is the fix for a real report: "die ki hat ihre truppen jetzt gerade im
# spiel teilweise sehr offen hingestellt. es ist gut, dass sie aggressiv
# aufstellt. aber los blocker und die HIDDEN mechanik sollten deutlich
# priorisierter genutzt werden". Before this, a screen's key was
# (-forward, to_objective, exposure) - a strict lexicographic sort in which a
# spot 0.1" further forward beat a spot that was completely out of sight, so
# exposure never actually decided anything and the units ended up in the open.
# Bucketing keeps the aggression (the best bucket is still the most forward one)
# while letting cover and rule 13.09 decide WITHIN it.
FORWARD_BUCKET_IN = 3.0
# ...but a heavy model gets a finer one. The 3" band is calibrated for a screen
# with the whole zone to choose from; a big base is inset so far from the zone
# edge that its entire usable depth is a couple of bands wide, and then "as far
# forward as possible" stops discriminating at all. Measured on map 2: the Kill
# Rig's three available rows (y = 3.1, 6.0, 8.9) put the front two in the SAME
# 3" bucket, so exposure decided between them and sent it to the back row of
# its own army - the very thing the heavy role exists to prevent.
HEAVY_FORWARD_BUCKET_IN = 1.0

# Rule 20.04 makes a reserve unit without [DEEP STRIKE] arrive within 6" of a
# board edge and (before round 3) outside the enemy zone, which is usually
# worse than simply deploying; a [DEEP STRIKE] unit (24.09) instead arrives
# anywhere more than 9" from every enemy, which is the whole reason a real
# player holds one back. This bonus is what makes "DEEP STRIKE encourages
# staying in reserve" an engine-computed term feeding a deterministic sort,
# rather than a sentence in a prompt the model is free to ignore.
#
# Both terms below are in POINTS, so they are actually comparable - an earlier
# version compared a flat 100 against a points-scaled damage value that ran to
# ~200, so any unit with a good matchup could never be reserved no matter what
# abilities it had, which is exactly backwards.
RESERVE_DEEP_STRIKE_BONUS = 100.0
# What a unit gives up by arriving late: roughly one turn of its output out of
# a five-turn game (20.03 lets it arrive from battle round 2).
RESERVE_TURNS_LOST = 1.0
BATTLE_LENGTH_TURNS = 5.0


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------
def _max_ranged_range(squad):
    best = 0.0
    for model in squad.models:
        for weapon in getattr(model, "weapons", ()):
            if getattr(weapon, "melee", False):
                continue
            best = max(best, getattr(weapon, "range_in", 0.0) or 0.0)
    return best


def _model_ranged_range(model):
    best = 0.0
    for weapon in getattr(model, "weapons", ()):
        if getattr(weapon, "melee", False):
            continue
        best = max(best, getattr(weapon, "range_in", 0.0) or 0.0)
    return best


def _bulk_ranged_range(squad):
    """The range MOST of this unit shoots at - the median model's best ranged
    weapon.

    _max_ranged_range() answers a different question ("could anything in here
    reach that far"), and using it to decide whether a unit is a SHOOTER is the
    one-representative trap this codebase has been caught by several times.
    Reported case: a 22-model assault mob of Boyz - twenty-one 12" Sluggas and
    a Warboss whose kombi-weapon reaches 24" - was classified "shooter" on the
    strength of that single gun, and deployed for a firing line it does not
    have. User: "KI hat wieder den grossen Boyz Plop auf dem Home Objective
    platziert... das geht gar nicht die boyz sollen nach vorne".

    The median rather than the mean, because it answers the question in the
    unit's own terms: at this range, half the unit can shoot. One long gun on
    one character cannot move it; a squad where every model carries the long
    gun keeps it."""
    if not squad.models:
        return 0.0
    ranges = sorted(_model_ranged_range(m) for m in squad.models)
    return ranges[len(ranges) // 2]


# A model on a 60 mm base or bigger, that cannot walk through its own army.
# These are the ones that need a lane rather than a gap.
#
# The user's report, twice, the second time with the game to back it up: "die
# ki sollte sehr große fahrzeuge eher in der ersten reihe aufstellen, nicht in
# der 2ten... dann kommen sie durch die eigenen einheiten nicht durch und
# werden ständig blockiert", after a turn 1 in which the Deff Dread managed
# 2.66" of its 8" and the Battlewagon 2.51" of its 10".
#
# Measured on the deployment that produced it (measure_vehicle_lanes.py): the
# army's five biggest models came out ranked 11th to 15th of 15 by how far
# forward they stood, with a mean of 8.4 friendly models sitting in the strip
# each one had to drive through - eleven apiece for the Battlewagon, the Deff
# Dread and Trukk 1. The T'au army on the same board, which has far fewer cheap
# bodies to fill the front with, put its big models at rank 3.0 of 7 with 0.5
# blockers, which is what this is trying to get back to.
#
# 1.18" is where the user's own two examples both sit or above (Deff Dread
# 1.18", Battlewagon 2.10"), and it is a real boundary rather than a gap in the
# data: it is the 60 mm base, below which the next sizes down are the 50 mm
# Warbikers and Crisis suits - units fast or small enough to thread a gap.
HEAVY_BASE_RADIUS_IN = 1.18


def is_heavy(squad):
    """Big enough to need an open lane off the deployment line, and unable to
    walk through its own army to get one.

    Keyed on base size plus rule 13.06's terrain permission rather than on the
    VEHICLE keyword, for the same reason _needs_open_ground() is: the keyword
    is not the property that matters, and this codebase has already been caught
    once by Warbikers, which had every problem a vehicle has and none of the
    handling because the test asked about VEHICLE."""
    if not squad.models:
        return False
    if max_model_radius(squad) < HEAVY_BASE_RADIUS_IN:
        return False
    return not any(
        m.profile.infantry or m.profile.beasts or m.profile.swarm for m in squad.models
    )


def _deployment_role(squad):
    """"heavy" | "assault" | "screen" | "shooter" | "key" - what this unit
    wants out of a deployment spot. Hiding behind terrain is only the right
    answer for SOME units, so one scorer for the whole army would be wrong for
    most of it.

    "heavy" is checked FIRST, ahead of "key", because the two want opposite
    things and a Battlewagon is both. "key" says hide it; "heavy" says give it
    room to move, which means the front row. Room won: a hidden vehicle that
    cannot get out of its own deployment zone contributes nothing to the game,
    whereas an exposed one that reaches the fight can at least trade.

    "assault" is checked LAST, and only ever takes units that would otherwise
    have been a plain "screen". User report: "die skorpekh destroyer standen
    sehr weit hinten und sind nicht durch die warrior durchgekommen. warum so
    weit hinten? nahkkaempfer sollten eher weiter vorne starten, aber
    moeglichst versteckt." Measured on that deployment: the Skorpekh came out
    at -3.04" of forward progress, the second most rearward unit of the whole
    army, behind even the "key" units that are supposed to hide at the back,
    with 1 of 3 models Hidden.

    They were not mis-SCORED - a screen's key already starts with
    -forward_bucket. They were mis-QUEUED and mis-passed: deployment_order_key()
    sorted them behind every bigger unit, so a 3-model elite chose from what a
    21-model blob had left, and _wants_hidden_pass() withholds the fully-hidden
    pass from a screen. Both are right for a screen and wrong for a unit whose
    only job is to arrive; see those two functions.

    The melee test is game/combat_focus.py's, shared with the Charge phase's
    own block, and it is deliberately the strict one rather than "leans melee":
    Gretchin lean melee too (0.97) and are the archetypal cheap screen the
    user wants left on the home objective. See that module for both bands."""
    if is_heavy(squad):
        return "heavy"
    profile = squad.models[0].profile if squad.models else None
    if profile is not None and (profile.vehicle or profile.character or getattr(profile, "monster", False)):
        return "key"
    points = squad.points or 0
    if points >= 100 and len(squad.models) <= 3:
        return "key"
    if _bulk_ranged_range(squad) >= SHOOTER_RANGE_IN:
        return "shooter"
    if combat_focus.is_assault_unit(squad):
        return "assault"
    return "screen"


def deployment_order_key(squad):
    """Heavy models go down FIRST, then cheap screening bodies, then the
    expensive/key units last so they can be placed against what is already on
    the table.

    Heavy first is the other half of the front-row fix, and without it the
    scorer alone cannot deliver: whoever deploys first picks from an empty
    zone, and the front row is a finite amount of ground. Leaving the biggest
    models until last meant they were choosing from whatever the ten-model
    screens had not already taken, which is by definition the back - the
    measured "rank 11 to 15 of 15" in is_heavy()'s comment. They get first
    pick now, and the screens fill in around them, which is also the order a
    player deploys in when they care about a tank getting off the line.

    INFILTRATORS units go absolutely last: rule 24.20 is measured at the
    instant the unit is set up, so placing one early throws the ability away
    (see PregameController._infiltrator_position_valid)."""
    role = _deployment_role(squad)
    return (
        squad_has_infiltrators(squad),
        {"heavy": 0, "assault": 1}.get(role, 3 if role == "key" else 2),
        -len(squad.models),
        -(squad.points or 0),
    )


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------
def _forward_axis(own_zone, board_w_in, board_h_in):
    """A unit vector pointing from the player's own zone toward the middle of
    the table. Derived rather than hardcoded so it is right on both the
    portrait map 1 and the landscape map 2."""
    if own_zone is None:
        return (0.0, 1.0)
    centre = _zone_centroid(own_zone, board_w_in, board_h_in)
    if centre is None:
        return (0.0, 1.0)
    cx, cy = centre
    dx, dy = board_w_in / 2 - cx, board_h_in / 2 - cy
    length = (dx * dx + dy * dy) ** 0.5
    if length < 1e-9:
        return (0.0, 1.0)
    return (dx / length, dy / length)


def _zone_centroid(zone, board_w_in, board_h_in):
    """A representative point inside a zone. Sampled from its shape, so it is
    still inside for a diagonal or holed zone - averaging rectangle centres
    only means anything while the zone IS rectangles."""
    if zone is None:
        return None
    return zone.centroid(board_box=(0.0, 0.0, board_w_in, board_h_in))


def _shape_box(zone, board_box=None):
    """A zone's extent, clipped to the board when the board is known.

    `board_box` is OPTIONAL and clipping is skipped without it - not a
    convenience: a zone bounded by its own rectangle needs no clipping, and
    defaulting the missing board to (0,0,0,0) would clip every such zone away
    to nothing. Two harnesses (measure_deployment_safety.py, smoke_pregame.py)
    call the probe helper with no board, and that is exactly what happened to
    them. A zone with an unbounded part (a half-plane) reports no box of its
    own, and there the board really is the answer, since it is the only place
    anything can stand - so that case still needs one."""
    box = zone.bounding_box() if zone is not None else None
    if box is None:
        return board_box
    if board_box is None:
        return box
    return (max(box[0], board_box[0]), max(box[1], board_box[1]),
            min(box[2], board_box[2]), min(box[3], board_box[3]))


def _shape_grid(box, cols, rows):
    min_x, min_y, max_x, max_y = box
    for i in range(cols):
        x = min_x + (max_x - min_x) * (i + 0.5) / cols
        for j in range(rows):
            yield (x, min_y + (max_y - min_y) * (j + 0.5) / rows)


def _zone_probe_points(zone, count=DEPLOY_ZONE_PROBE_POINTS, board_box=None):
    """Evenly spread sample points across a deployment zone - the stand-in for
    "wherever the enemy army ends up standing".

    Sampled against the zone's own shape rather than laid out per rectangle,
    so a diagonal or holed zone is probed where units can actually stand and
    not across the hole. The grid is OVERSAMPLED by the fraction of its
    bounding box the zone actually fills, so the requested count is still met
    rather than quietly undershot - the same concern the per-rectangle version
    had, now measured instead of assumed."""
    if zone is None:
        return []
    box = _shape_box(zone, board_box)
    if box is None:
        return []
    width, height = box[2] - box[0], box[3] - box[1]
    if width <= 0 or height <= 0:
        return []
    probe = [p for p in _shape_grid(box, 16, 16) if zone.contains_point(*p)]
    fill = max(len(probe) / 256.0, 1e-3)
    cells = count / fill
    cols = max(1, int(round((cells * width / max(height, 1e-6)) ** 0.5)))
    rows = max(1, -(-int(round(cells)) // cols))
    return [p for p in _shape_grid(box, cols, rows) if zone.contains_point(*p)]


def _candidate_points(pregame_ctrl, squad, board_w_in, board_h_in):
    """Every spot worth trying as this unit's drop point.

    Normally a grid over the unit's own deployment zone, inset so a packed
    squad has room. An INFILTRATORS unit (24.20) may go anywhere on the table
    more than 8" from the enemy zone and all enemy units, so it gets a grid
    over the whole board and lets position_valid() do the filtering."""
    radius = max_model_radius(squad)
    # The extra inch is room for the REST of the squad to pack out around the
    # drop point, so a one-model unit does not need it - and paying it anyway
    # is expensive for exactly the units that can least afford it. Measured on
    # map 2's 12"-deep zone: the Kill Rig's 2.10" base made the inset 3.10",
    # leaving a 5.8" band that the 2" grid resolves into just three rows
    # (y = 3.1, 6.0, 8.9), so the frontmost spot it could even be offered was a
    # full inch behind the one it actually fits on.
    inset = radius + (1.0 if len(squad.models) > 1 else 0.0)
    zones = getattr(pregame_ctrl.game_state, "deployment_zones", ())

    board_box = (0.0, 0.0, board_w_in, board_h_in)
    own = None if squad_has_infiltrators(squad) else deployment.zone_for(zones, squad.owner)
    if own is None:
        # INFILTRATORS (24.20) may go anywhere on the table, and a map with no
        # zone at all gets the same treatment - position_valid() does the
        # filtering either way. Routed through the SAME sampling_boxes() call
        # as a zone so the inset is applied here too; handing the raw board
        # rectangle over instead silently widened the grid for every
        # INFILTRATORS unit by exactly the base radius.
        boxes = shapes.Rect(board_w_in / 2, board_h_in / 2, board_w_in, board_h_in).sampling_boxes(inset)
    else:
        # One box per part of the zone, already shrunk by the inset - see
        # shapes.Shape.sampling_boxes(). For the axis-aligned rectangles every
        # shipped map uses, this is the identical grid the rectangle-only code
        # produced; a diagonal or holed zone gets a box that covers it and is
        # then thinned by position_valid() below.
        boxes = own.shape.sampling_boxes(inset, fallback_box=board_box)

    token = squad.models[0]
    points = []
    for (x0, y0, x1, y1) in boxes:
        if x1 < x0 or y1 < y0:
            continue
        nx = max(1, int((x1 - x0) / DEPLOY_GRID_STEP_IN) + 1)
        ny = max(1, int((y1 - y0) / DEPLOY_GRID_STEP_IN) + 1)
        for i in range(nx):
            for j in range(ny):
                x = x0 + (x1 - x0) * (i / (nx - 1) if nx > 1 else 0.5)
                y = y0 + (y1 - y0) * (j / (ny - 1) if ny > 1 else 0.5)
                if pregame_ctrl.position_valid(squad, token, x, y):
                    points.append((x, y))
    return points


def can_be_hidden(squad):
    """Whether rule 13.09 (Hidden) can apply to this unit at all: INFANTRY,
    BEASTS or SWARM - notably NOT Mobile, unlike 13.06's Dense-terrain movement
    exception. all() rather than any(): a unit is only actually protected while
    EVERY model of it is hidden, since is_hidden() is per model and one visible
    model makes the unit targetable."""
    return bool(squad.models) and all(
        m.profile.infantry or m.profile.beasts or m.profile.swarm for m in squad.models
    )


def _hidden_pass_points(squad, context, points, terrain_areas):
    """Which candidate spots the "fully hidden" pass may use for this unit.

    Every Dense spot, except for an "assault" unit, which only gets the ones
    that cost it NO forward ground - the same "hide where hiding is free"
    the heavy role already gets, rather than an all-or-nothing choice between
    the two.

    Straight exclusion was tried first and measured too blunt: it does put the
    reported Boyz mob at the front edge, but it also stops every cheap screen
    from using cover it could have had for nothing, and map 2's mean exposure
    went 0.30 -> 0.60 of 33 probe points with the worst single unit at 5. The
    forward-bucket test keeps the aggression and gets the cover back.

    THIS BRANCH USED TO NAME "screen" AND WAS UNREACHABLE. Reaching it needed
    _wants_hidden_pass() to be True with role == "screen", which only happens
    for the home garrison - and the line above already returns for the home
    garrison. So the measurement in the paragraph above was made, the finding
    was kept, and then the code that carried it was stranded when screens lost
    the pass outright. "assault" is the role that actually wants this bargain,
    and pointing the branch at it makes the finding live again."""
    if not _wants_hidden_pass(squad, context):
        return []
    dense = [p for p in points if _in_dense_area(p[0], p[1], terrain_areas)]
    if not dense or context.get("is_home_garrison"):
        return dense
    if context["roles"][id(squad)] != "assault":
        return dense
    fx, fy = context["forward"]
    ox, oy = context["origin"]

    def bucket(point):
        return int(((point[0] - ox) * fx + (point[1] - oy) * fy) // FORWARD_BUCKET_IN)

    best = max(bucket(p) for p in points)
    return [p for p in dense if bucket(p) >= best]


def _wants_hidden_pass(squad, context):
    """Whether this unit should get the "fully hidden" placement pass at all.

    The pass CONSTRAINS the packer to Dense ground and is tried before the
    normal placement, so it overrides the role scorer rather than serving it.
    That is right where the scorer itself ranks `hidden` at or near the top -
    "key" hides, a "shooter" gets Hidden as a free option, and the home
    garrison wants to sit on its objective unshootable - and wrong for a plain
    "screen", whose whole key starts with -forward_bucket. A screen forced into
    the only ruin in its own deployment zone is a screen that is not in front
    of anything.

    That inconsistency is what the report came down to: with the Boyz mob
    correctly reclassified from "shooter" to "screen", the scorer wanted it at
    the forward edge and this pass put it back in the home-objective ruin
    anyway. User: "das geht gar nicht die boyz sollen nach vorne und gretchins
    das homeobjective halten." """
    if not can_be_hidden(squad):
        return False
    if context.get("is_home_garrison"):
        return True
    return context["roles"][id(squad)] != "screen"


# NOTE on the role list above: "assault" is NOT excluded, so it does get the
# pass. That is the second half of the reported Skorpekh fix - the user asked
# for "moeglichst versteckt" in the same breath as "weiter vorne" - and it is
# safe here in a way it was not for a plain screen, because
# _hidden_pass_points() restricts an assault unit's Dense candidates to the
# forward bucket it would have reached anyway. It can only hide where hiding
# is free, which is the same bargain the "heavy" role already gets.


def _in_dense_area(x_in, y_in, terrain_areas):
    """The positional half of rule 13.09: standing within a terrain area that
    contains a Dense feature.

    Note what this does NOT mean - standing ON the wall. A ruin is a Light
    floor plus Dense walls, and 13.09 asks about the AREA, so the legal and
    intended spot is the floor inside the walls (SetupController.position_valid
    refuses the wall itself). Checked at the point rather than with
    overlaps_model() because this scores candidate spots, not placed models."""
    return any(
        area.has_dense_feature and area.contains_point(x_in, y_in)
        for area in terrain_areas
    )


def hidden_at(squad, x_in, y_in, terrain_areas):
    """Would this unit be Hidden (13.09) standing here, at deployment time?

    The "made no ranged attacks this turn or the previous one" half is free
    here: nothing has shot yet when armies are being set up, so it reduces to
    the keywords plus the position. That is exactly why deployment is the
    cheapest moment to buy the benefit - a Hidden unit cannot be targeted at
    all from beyond 15" (12" with a wall on its own footprint), which is a
    hard targeting restriction rather than a to-hit modifier."""
    return can_be_hidden(squad) and _in_dense_area(x_in, y_in, terrain_areas)


def _nearest_uncontrolled_objective_distance(point, squad, objectives):
    x, y = point
    best = None
    for objective in objectives or ():
        if getattr(objective, "controlled_by", None) == squad.owner:
            continue
        dist = objective.terrain_area.distance_to_point(x, y)
        if best is None or dist < best:
            best = dist
    return best if best is not None else 0.0


def _home_objective(owner, objectives, own_zone):
    """The objective sitting in this player's own deployment zone, if any -
    the one they hold from turn 1 and score 3 VP off every Command phase
    without having to fight for it."""
    best = None
    for objective in objectives or ():
        min_x, min_y, max_x, max_y = objective.terrain_area.bounding_box
        cx, cy = (min_x + max_x) / 2.0, (min_y + max_y) / 2.0
        if own_zone is None or not own_zone.contains_point(cx, cy):
            continue
        if best is None:
            best = objective
    return best


def _garrison_cost_key(squad):
    """Cheapest first, with unknown points sorting LAST - the same ordering
    ai/agent_driver.py's turn-plan garrison check uses, and for the same
    reason: "we cannot tell what this costs" may not be read as "this is the
    cheap one"."""
    return (squad.points is None, squad.points if squad.points is not None else 0, squad.name)


def home_garrison_squad(pregame_ctrl, owner, objectives, own_zone):
    """Which unit should be standing on the home objective when deployment
    ends, or None if this player has no home objective or nothing to spare.

    Rule 14.02 decides control on the Objective Control total, so the job wants
    the cheapest body that can do it - the same rule ai/agent_driver.py now
    enforces on the turn plan, applied one phase earlier so the army does not
    have to spend turn 1 correcting its own deployment. User: "Wieso platziert
    er nicht die Gretchen auf dem Home Objective? Das ist doch der perfekte
    Fit."

    BUT ROLE COMES FIRST, AND CHEAPEST ONLY DECIDES WITHIN A ROLE. Points alone
    hands the job to whatever happens to be cheapest, and that is not a property
    of the job - measured on the current Necron list, the cheapest unit in the
    whole army is the Lychguard at 170, which is its melee anvil with no ranged
    weapons at all, so the army's best counter-charge unit spent every game
    standing on empty ground behind its own lines. Reported by the user: "die ki
    soll fernkampfeinheiten stark bevorzugen, wenn es darum geht das home
    objective zu halten. sie hat im letzten spiel dafuer die lychguard benutzt,
    was voelliger quatsch ist. die immortals waeren perfekt."

    The ordering is game/combat_focus.py's home_garrison_rank(), which is the
    same measurement that already gates the charge block and the `assault`
    deployment role - so this is a third reader of one definition rather than a
    second opinion. It takes the range half of the user's sentence from
    observation.garrison_reach_needed_in(), measured off THIS board.

    Excluded: anything with no Objective Control (rule 14.02 counts OC, so a
    zero-OC unit garrisons nothing), and "heavy" units - a Battlewagon parked
    on an objective is precisely the outcome the heavy role exists to avoid.
    Read off the DECLARED deploy list rather than what is still pending, so the
    designation is the same answer at every step of the alternating sequence."""
    home = _home_objective(owner, objectives, own_zone)
    if home is None:
        return None
    candidates = [
        squad for squad in pregame_ctrl.army(owner)
        if squad.models
        and pregame_ctrl.declaration_for(squad)[0] == pregame.DEPLOY
        and not is_heavy(squad)
        and any(m.profile.oc > 0 for m in squad.models)
    ]
    if not candidates:
        return None
    reach_needed = observation.garrison_reach_needed_in(home, objectives)
    return sorted(candidates, key=lambda sq: (
        combat_focus.home_garrison_rank(sq, reach_needed), _garrison_cost_key(sq)))[0]


def deployment_score(point, squad, pregame_ctrl, context):
    """A sort key (lower is better) for one candidate drop point.

    Shaped like _ingress_landing_score()'s tuple so the two read the same way,
    but the ORDER of the terms depends on the unit's role - which is the whole
    point. "Hide behind terrain" is right for a Ghostkeel and wrong for a
    screening mob whose job is to stand in front of things."""
    x, y = point
    role = context["roles"][id(squad)]
    fx, fy = context["forward"]
    origin = context["origin"]
    forward = (x - origin[0]) * fx + (y - origin[1]) * fy
    # Bucketed, so "as far forward as possible" stops out-voting "and not in
    # the open" over a fraction of an inch - see FORWARD_BUCKET_IN.
    forward_bucket = int(forward // FORWARD_BUCKET_IN)
    to_objective = _nearest_uncontrolled_objective_distance(point, squad, context["objectives"])

    exposure = observation.zone_visibility_from_point(
        x, y, max_model_radius(squad), squad.owner, context["enemy_probes"],
        context["obstacles"], context["terrain_areas"], context["all_tokens"],
    )
    # Rule 13.09: 0 = would be Hidden here, 1 = would not. Ranked ABOVE
    # exposure wherever it can apply, because it is categorically stronger: a
    # low-exposure spot can still be shot by whatever does happen to see it,
    # whereas a Hidden unit cannot be TARGETED at all from beyond 15".
    hidden = 0 if hidden_at(squad, x, y, context["terrain_areas"]) else 1

    # The one unit designated to hold the home objective ranks standing ON it
    # above everything else - see home_garrison_squad(). Nothing else in this
    # scorer would put it there: "screen" wants the forward edge of the zone,
    # and an objective in one's own deployment zone is behind that edge, so
    # after the role fix the objective would simply have gone unheld.
    home = context.get("home_objective")
    if home is not None and context.get("is_home_garrison"):
        on_objective = 0 if home.terrain_area.contains_point(x, y) else 1
        return (on_objective, hidden, exposure, round(to_objective, 1))

    if role == "heavy":
        # Forward first, exactly like a screen, and for a reason that has
        # nothing to do with aggression: a big model parked behind its own army
        # spends the first turns grinding through it. Safety is not dropped,
        # only demoted - within the same forward band it still takes the least
        # visible spot it can find, so it hides where hiding is free.
        return (-int(forward // HEAVY_FORWARD_BUCKET_IN), exposure, round(to_objective, 1))
    if role in ("screen", "assault"):
        # Still the most forward bucket - a screen that hides is not screening
        # anything - but within that bucket it takes cover and 13.09 rather
        # than whatever spot happens to be 0.1" further up.
        #
        # "assault" shares this key unchanged, and that is the point: forward
        # first, hidden within the forward band, is already exactly the user's
        # "nahkkaempfer sollten eher weiter vorne starten, aber moeglichst
        # versteckt". What an assault unit needed was not a different key but
        # an earlier place in the queue and the fully-hidden pass - see
        # deployment_order_key() and _wants_hidden_pass().
        return (-forward_bucket, hidden, exposure, round(to_objective, 1))
    if role == "shooter":
        # Wants a lane into SOME of the enemy zone but not to stand in the
        # open: exposure 0 means no shot at all, exposure 12 means every gun
        # on the far side already has an answer. Hidden is a free OPTION for a
        # shooter rather than a cost - it holds the benefit until it chooses to
        # fire, and firing is what gives it up (13.09's "no ranged attacks this
        # turn or the previous one") - so a spot that has both is strictly best.
        lo, hi = SHOOTER_IDEAL_EXPOSURE
        in_band = 0 if lo <= exposure <= hi else 1
        return (in_band, hidden, exposure, -forward_bucket, round(to_objective, 1))
    # "key": hide it. This is the user's "am Anfang seine wichtigen Einheiten
    # moeglichst hinter Gelaende verstecken". A vehicle or character cannot be
    # Hidden (13.09 is INFANTRY/BEASTS/SWARM only), so `hidden` is a constant 1
    # for most of these and the key degrades to exactly what it was before.
    return (hidden, exposure, -forward_bucket, round(to_objective, 1))


def _score_context(pregame_ctrl, squad, objectives, board_w_in, board_h_in):
    state = pregame_ctrl.game_state
    zones = getattr(state, "deployment_zones", ())
    own = deployment.zone_for(zones, squad.owner)
    enemy = deployment.enemy_zones(zones, squad.owner)
    probes = []
    for zone in enemy:
        probes.extend(_zone_probe_points(zone, board_box=(0.0, 0.0, board_w_in, board_h_in)))
    centre = _zone_centroid(own, board_w_in, board_h_in)
    cx, cy = centre if centre else (board_w_in / 2, board_h_in / 2)
    home = _home_objective(squad.owner, objectives or getattr(state, "objectives", ()), own)
    garrison = home_garrison_squad(
        pregame_ctrl, squad.owner, objectives or getattr(state, "objectives", ()), own)
    return {
        "home_objective": home,
        "is_home_garrison": garrison is squad,
        "roles": {id(squad): _deployment_role(squad)},
        "forward": _forward_axis(own, board_w_in, board_h_in),
        "origin": (cx, cy),
        "enemy_probes": probes,
        "obstacles": state.obstacles,
        "terrain_areas": state.terrain_areas,
        "all_tokens": state.tokens,
        "objectives": objectives or getattr(state, "objectives", ()),
    }


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------
def auto_deploy_squad(pregame_ctrl, setup_controller, squad, board_w_in, board_h_in,
                      objectives=(), game_log=None):
    """Place one unit during rule 03.01's alternating deployment. Returns True
    if it landed.

    Mirrors _auto_ingress_squad()'s structure: rank the drop points, then try
    each of eight facings at each of the best few, because a point that passes
    position_valid() on its own can still fail once the squad is actually
    packed out around it (coherency, a squadmate on a wall, the zone edge).

    Gives up explicitly rather than looping. Unlike an Emergency Disembark
    (18.05), a failed deployment destroys nothing - so the honest outcome is
    to log it, leave the unit in the pool and let the caller move on, which is
    also the single most likely way this state machine could otherwise
    deadlock."""
    candidates = _candidate_points(pregame_ctrl, squad, board_w_in, board_h_in)
    if not candidates:
        _log(game_log, f"[deploy] {squad.owner}: {squad.name} found no legal spot in its zone at all.")
        return False

    context = _score_context(pregame_ctrl, squad, objectives, board_w_in, board_h_in)
    fx, fy = context["forward"]
    ox, oy = context["origin"]
    terrain_areas = context["terrain_areas"]

    # Pre-rank cheaply by forward progress, then pay for the LOS-heavy score on
    # only the best slice - the probing dominates the cost.
    candidates.sort(key=lambda p: -((p[0] - ox) * fx + (p[1] - oy) * fy))

    # ...but reserve part of that slice for spots that would grant rule 13.09
    # (Hidden). Without this the whole feature could be silently defeated by the
    # pre-filter: it keeps the 40 most FORWARD spots, and a Dense terrain area
    # is usually not the most forward ground available - so on a board where the
    # front of the zone is open, no Hidden spot would ever be scored at all and
    # the unit would deploy in the open having "considered" nothing else.
    # _in_dense_area is a plain rectangle test with no line of sight in it, so
    # partitioning here is free.
    dense_pool = _hidden_pass_points(squad, context, candidates, terrain_areas)
    if dense_pool:
        keep = {id(p) for p in dense_pool}
        rest = [p for p in candidates if id(p) not in keep]
        reserved = min(len(dense_pool), DEPLOY_SCORED_CANDIDATES // 2)
        scored = dense_pool[:reserved] + rest[: DEPLOY_SCORED_CANDIDATES - reserved]
    else:
        scored = candidates[:DEPLOY_SCORED_CANDIDATES]
    scored.sort(key=lambda p: deployment_score(p, squad, pregame_ctrl, context))

    # Pack away from the board centre, so a unit hugs the back of its own drop
    # point rather than spilling forward past it.
    base_angle = math.atan2(-fy, -fx)

    # Rule 13.09 protects a unit only while EVERY model of it is hidden - one
    # visible model and the whole unit is targetable again. So it is not enough
    # to pick a drop point inside a Dense area and hope: a 10-model block packs
    # out over several inches and spills out of a ruin, which is exactly why an
    # earlier version of this measured 1 of 9 units fully hidden despite
    # ranking Hidden spots first.
    #
    # Fixed by CONSTRAINING the packer instead of scoring the drop point: pass
    # it a predicate of "legal AND inside a Dense area", so every slot it hands
    # out keeps its model hidden. An area too small for the unit then simply
    # fails, and the second pass places it normally - a bounded two-pass ladder,
    # not a repair loop.
    passes = [(None, "")]
    if dense_pool:
        eligible = {id(p) for p in dense_pool}
        dense_only = [p for p in scored if id(p) in eligible]
        if dense_only:
            passes.insert(0, (
                lambda model, px, py: _in_dense_area(px, py, terrain_areas),
                " (fully hidden, rule 13.09)",
            ))

    for extra_valid, hidden_note in passes:
        if extra_valid is not None:
            points = dense_only
            limit = DEPLOY_HIDDEN_ATTEMPTS
        else:
            points, limit = scored, DEPLOY_PLACEMENT_ATTEMPTS
        placed = _attempt_placements(
            pregame_ctrl, setup_controller, squad, points[:limit],
            base_angle, extra_valid, context, terrain_areas, hidden_note, game_log,
        )
        if placed:
            return True

    _log(
        game_log,
        f"[deploy] {squad.owner}: {squad.name} could not be placed at any of "
        f"{min(len(scored), DEPLOY_PLACEMENT_ATTEMPTS)} spots x {len(_DISEMBARK_FACINGS)} facings - skipped.",
    )
    return False


def _attempt_placements(pregame_ctrl, setup_controller, squad, points, base_angle,
                        extra_valid, context, terrain_areas, hidden_note, game_log):
    """One pass of the candidate x facing ladder. `extra_valid`, if given, is
    ANDed onto the normal legality predicate for every slot - see the Hidden
    pass in auto_deploy_squad()."""
    def slot_valid(model, px, py):
        if not pregame_ctrl.position_valid(squad, model, px, py):
            return False
        return extra_valid is None or extra_valid(model, px, py)

    for rank, (x, y) in enumerate(points):
        for facing in _DISEMBARK_FACINGS:
            if not pregame_ctrl.start_deployment(squad, x, y):
                _log(game_log, f"[deploy] {squad.owner}: {squad.name} could not begin placement.")
                return False
            positions = _ingress_pack_positions(
                squad, x, y, pregame_ctrl.game_state.tokens, angle_offset=facing,
                position_valid=slot_valid,
                base_angle_override=base_angle,
            )
            for model, (px, py) in zip(squad.models, positions):
                model.x_in, model.y_in = setup_controller.clamp_position(model, px, py)
            if pregame_ctrl.confirm_deployment():
                exposure = observation.zone_visibility_from_point(
                    x, y, max_model_radius(squad), squad.owner, context["enemy_probes"],
                    context["obstacles"], terrain_areas, context["all_tokens"],
                )
                # Both safety terms in the line, so "the AI stood in the open"
                # can be checked against what it actually had available instead
                # of reconstructed from coordinates.
                hidden_models = sum(
                    1 for m in squad.models if _in_dense_area(m.x_in, m.y_in, terrain_areas)
                ) if can_be_hidden(squad) else 0
                _log(
                    game_log,
                    f"[deploy] {squad.owner}: {squad.name} ({_deployment_role(squad)}) deployed at "
                    f"({x:.1f},{y:.1f}){hidden_note} - candidate #{rank + 1}, "
                    f"facing {math.degrees(facing):.0f} deg, "
                    f"exposure {exposure}/{len(context['enemy_probes'])}, "
                    f"hidden (13.09) {hidden_models}/{len(squad.models)} models.",
                    file_only=True,
                )
                return True
            pregame_ctrl.cancel_deployment()
    return False


# ---------------------------------------------------------------------------
# Declare Battle Formations
# ---------------------------------------------------------------------------
def _best_damage_value(squad, enemy_squads):
    best = 0.0
    for enemy in enemy_squads:
        for melee in (False, True):
            value = observation.damage_value(squad, enemy, melee=melee)
            if value and value > best:
                best = value
    return best


class Passenger:
    """One entry in a transport's passenger priority list: a datasheet name,
    optionally narrowed to the version WITH an attached character (19.01).

    The `led` flag exists because the user's Trukk order distinguishes two
    things that share one datasheet - "1. slugga boyz mit warboss, 2. slugga
    boyz" - so a datasheet name alone cannot express it. `led=None` means
    "don't care", which is why listing Passenger("Boyz", led=True) BEFORE
    Passenger("Boyz") works: the led unit matches the earlier entry and so
    outranks its plain sibling, while both are still wanted."""

    def __init__(self, datasheet, led=None):
        self.datasheet = datasheet
        self.led = led

    def matches(self, squad):
        sheet = getattr(squad, "datasheet", None)
        if sheet is None or sheet.name != self.datasheet:
            return False
        if self.led is None:
            return True
        return bool(attached_units.leader_components(squad)) == self.led


# Who each TRANSPORT wants to carry, best first, keyed by the transport's own
# datasheet name. Straight from the user's instruction:
#
#     prio battle wagon: 1. meganobs 2. boyz 3. flash gits
#     prio kill rig:     beast boyz
#     prio trukk:        1. slugga boyz mit warboss 2. slugga boyz 3. flash gits
#
# This table is EXHAUSTIVE for the transports it names: a unit that matches no
# entry is not loaded, full stop. That is what actually fixes the report ("ki
# soll keine gretchins in die transporter packen") - the old code had no notion
# of unit type at all, it sorted every candidate by weapon reach and broke ties
# by name, so Gretchin (12" blasta) tied with Boyz (12" slugga) and won a Trukk
# on the letter G.
#
# It also has to OVERRIDE the reach heuristic rather than filter through it,
# which is measurable and not obvious: _max_ranged_range() reports 24" for both
# Flash Gitz (snazzguns) and Boyz-with-Warboss (the Warboss's kombi-weapon), so
# the old "never load a unit that reaches 18" or more" test rejected two of the
# three units the user explicitly asked to be carried.
TRANSPORT_PASSENGER_PRIORITY = {
    "Battlewagon": (
        Passenger("Meganobz"),
        Passenger("Boyz"),
        Passenger("Flash Gitz"),
    ),
    "Kill Rig": (
        Passenger("Beast Snagga Boyz"),
    ),
    "Trukk": (
        Passenger("Boyz", led=True),
        Passenger("Boyz"),
        Passenger("Flash Gitz"),
    ),
}


def _priority_list_for(transport_token):
    sheet = getattr(getattr(transport_token, "squad", None), "datasheet", None)
    if sheet is None:
        return None
    return TRANSPORT_PASSENGER_PRIORITY.get(sheet.name)


def _transport_affinity(squad, transport_token, hints):
    """Lower is a better passenger for THIS transport; None means never load
    it here. Three sources, in order of authority:

      0. the scene author's own EMBARK hint,
      1. TRANSPORT_PASSENGER_PRIORITY, if this transport's datasheet has a list,
      2. otherwise the generic heuristic - a slow, short-ranged body wants the
         ride, a long-ranged gun does not, it would just lose a turn of shooting.

    Tier 1 and 2 are mutually exclusive per transport, so the leading tier
    number only ever serves to sort a hinted unit first."""
    hinted = hints.get(id(squad))
    if hinted and hinted[0] == pregame.EMBARK:
        if hinted[1] is transport_token:
            return (0, 0, squad.name)  # the hand-authored scene's own answer
        # Hinted at a DIFFERENT transport: refuse this one outright rather
        # than falling through to the generic score below. Without this the
        # pairing is only a preference within each transport, and whichever
        # transport happens to be processed first can swallow the unit -
        # e.g. a Trukk loading the Beast Snagga Boyz that the scene wants in
        # the Kill Rig, purely because the Trukk comes earlier in the list.
        # The scene author naming a transport is an instruction about where
        # the unit goes, not just a tie-break.
        return None

    sheet = getattr(squad, "datasheet", None)
    if sheet is not None and sheet.name in TRANSPORT_NEVER_EMBARK:
        return None

    priority = _priority_list_for(transport_token)
    if priority is not None:
        for rank, entry in enumerate(priority):
            if entry.matches(squad):
                return (1, rank, squad.name)
        return None  # the list is the whole answer for this transport

    reach = _max_ranged_range(squad)
    if reach >= TRANSPORT_PASSENGER_MAX_RANGE_IN:
        return None  # never load a unit that does not need the ride
    return (2, round(reach, 1), squad.name)


def plan_battle_formations(pregame_ctrl, owner, enemy_squads=(), hints=None, game_log=None):
    """Decide, for one player, which units ride in which TRANSPORT and which
    start in Strategic Reserves (rules 18.01 / 20.01), then declare them.

    Deterministic. The rule-20.01 half-the-units/half-the-points cap is a hard
    truncation with a logged reason, not a scoring nudge - the same
    "engine corrects the plan, with a rule reference" pattern as
    _validate_turn_plan()."""
    hints = hints or {}
    army = pregame_ctrl.army(owner)
    transports = pregame_ctrl.transports_for(owner)

    # 1. Transports themselves always deploy.
    for transport in transports:
        pregame_ctrl.declare(transport.squad, pregame.DEPLOY)

    # 2. Fill each transport with the passengers that most want a ride.
    assigned = {id(t): [] for t in transports}
    embarked = set()
    for transport in transports:
        wanted = []
        for squad in army:
            if squad is transport.squad or id(squad) in embarked:
                continue
            affinity = _transport_affinity(squad, transport, hints)
            if affinity is None:
                continue
            if formations.embark_errors(squad, transport, assigned[id(transport)]):
                continue
            wanted.append((affinity, squad))
        wanted.sort(key=lambda pair: pair[0])
        for _, squad in wanted:
            if formations.embark_errors(squad, transport, assigned[id(transport)]):
                continue  # capacity ran out as earlier units were loaded
            assigned[id(transport)].append(squad)
            embarked.add(id(squad))
            pregame_ctrl.declare(squad, pregame.EMBARK, transport_token=transport)

    # 3. Rank the rest for Strategic Reserves.
    # Deliberately a PREFERENCE, not a ban: rule 20.01 lets any unit start in
    # Strategic Reserves, and the human's own Formations screen offers it for
    # every unit that fits under the cap. This is only what the AI chooses, and
    # in practice a unit without [DEEP STRIKE] scores at or below zero - which
    # is the honest answer, since arriving at a board edge on turn 2 is nearly
    # always worse than simply deploying.
    candidates = [s for s in army if id(s) not in embarked and s not in [t.squad for t in transports]]
    scored = []
    for squad in candidates:
        value = RESERVE_DEEP_STRIKE_BONUS if _has_deep_strike(squad) else 0.0
        value -= _best_damage_value(squad, enemy_squads) * (RESERVE_TURNS_LOST / BATTLE_LENGTH_TURNS)
        scored.append((value, squad))
    scored.sort(key=lambda pair: (-pair[0], pair[1].name))

    reserves = []
    for value, squad in scored:
        if value <= 0:
            break  # nothing left that actually wants to be in reserve
        trial = reserves + [squad]
        problems = formations.reserve_limit_errors(army, trial)
        if problems:
            _log(
                game_log,
                f"[formations] {owner}: {squad.name} kept on the table - {problems[0]}",
                file_only=True,
            )
            continue
        reserves = trial
        pregame_ctrl.declare(squad, pregame.RESERVES)

    # SUPPORT ARTILLERY IS DELIBERATELY LEFT ALONE, and this is where that
    # decision lands: a SUPPORT WEAPON platform falls through to DEPLOY below,
    # i.e. it stands alone. The printed join is optional and its trade is a
    # real one in both directions - joining buys the platform a screen of
    # Guardian bodies but drops it to Toughness 3 (its own Support Weapon
    # rule), where standing alone keeps T6/W5. There is no Aeldari AI path by
    # standing instruction, and the default is a legal, defensible answer
    # rather than a stall - so it is NAMED here instead of being an oversight
    # somebody has to rediscover.
    for squad in army:
        if id(squad) not in pregame_ctrl._declared:
            pregame_ctrl.declare(squad, pregame.DEPLOY)

    # Named loads, not just a count: the reported "why are Gretchin in a
    # transport" could not be answered from the old counting-only line at all,
    # it had to be reconstructed from the later disembark messages.
    loads = []
    for transport in transports:
        cargo = assigned[id(transport)]
        name = formations.transport_name(transport)
        used = formations.transport_capacity_used(transport, cargo)
        capacity = transport.profile.transport_capacity
        loads.append(
            f"{name} {used}/{capacity} [{', '.join(s.name for s in cargo) or 'empty'}]"
        )
    _log(
        game_log,
        f"[formations] {owner}: {len(reserves)} unit(s) in Strategic Reserves "
        f"({', '.join(s.name for s in reserves) or 'none'}); "
        f"transports: {' | '.join(loads) or 'none'}.",
        file_only=True,
    )
    pregame_ctrl.finish_formations_for(owner)


def _has_deep_strike(squad):
    """Rule 24.09: only "if every model in this unit has this ability"."""
    return bool(squad.models) and all(m.profile.deep_strike for m in squad.models)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def take_pregame_action(pregame_ctrl, setup_controller, player, board_w_in, board_h_in,
                        objectives=(), game_log=None):
    """One pre-game action for `player`, mirroring take_one_action()'s
    "do at most one thing per frame, return whether anything happened"
    contract so main.py can drive it from the same auto-play gate."""
    if not pregame_ctrl.is_active:
        return False

    state = pregame_ctrl.game_state

    if pregame_ctrl.state == pregame.FORMATIONS:
        if player in pregame_ctrl._formations_done:
            return False
        enemies = [s for s in _all_squads(state.tokens) if s.owner != player and s.models]
        enemies += [s for s in pregame_ctrl.army(pregame_ctrl._other(player)) if s.models]
        plan_battle_formations(
            pregame_ctrl, player, enemy_squads=enemies,
            hints=getattr(pregame_ctrl, "scene_hints", {}), game_log=game_log,
        )
        return True

    if pregame_ctrl.state == pregame.DEPLOYING and pregame_ctrl.active_player == player:
        pending = pregame_ctrl.pending_units(player)
        if not pending:
            return False
        squad = sorted(pending, key=deployment_order_key)[0]
        if not auto_deploy_squad(
            pregame_ctrl, setup_controller, squad, board_w_in, board_h_in,
            objectives=objectives, game_log=game_log,
        ):
            # Nothing was destroyed by failing; drop it from the queue so the
            # sequence keeps moving rather than retrying the same unit forever.
            pregame_ctrl.give_up_on(squad)
        return True

    return False


def resolve_scouts(pregame_ctrl, squad, branch, distance, movement_controller=None,
                   setup_controller=None, board_w_in=None, board_h_in=None,
                   objectives=(), game_log=None, ai_players=()):
    """Rule 24.31 for one unit. Wired into ScoutsStep.on_resolve; returns True
    if the AI actually used the ability.

    Deterministic, like the rest of the pre-game. Only the AI's own units are
    touched - a human's Scouts unit is left to the human (returning False just
    means "declined", which 24.31 always permits).

    `ai_players` DEFAULTS TO EMPTY, so a caller that forgets it touches nothing.
    It used to default to ("Player 2",), which meant the same thing as long as
    Player 2 was always the AI - and would have quietly resolved a HUMAN's
    Scouts move the moment that stopped being true. main.py passes
    config.AI_PLAYERS through explicitly; see its comment for why that is the
    one place the fact lives."""
    if squad.owner not in ai_players:
        return False

    if branch == "reserve_redeploy":
        # 24.31: a reserve unit may be set up wholly within its own zone
        # instead. Only worth it if it would rather be on the table - a
        # [DEEP STRIKE] unit specifically would not, since arriving anywhere
        # more than 9" from the enemy (24.09) is the stronger option and is
        # exactly why it was reserved in the first place.
        if _has_deep_strike(squad):
            _log(game_log, f"[scouts] {squad.owner}: {squad.name} stays in reserve - "
                           f"[DEEP STRIKE] arrival beats redeploying into its own zone.", file_only=True)
            return False
        if setup_controller is None or board_w_in is None:
            return False
        pregame_ctrl.game_state.reserves.remove(squad)
        pregame_ctrl._pending.setdefault(squad.owner, []).append(squad)
        placed = auto_deploy_squad(
            pregame_ctrl, setup_controller, squad, board_w_in, board_h_in,
            objectives=objectives, game_log=game_log,
        )
        if not placed:
            # Put it straight back: a declined ability costs nothing, a lost
            # unit would.
            if squad in pregame_ctrl._pending.get(squad.owner, ()):
                pregame_ctrl._pending[squad.owner].remove(squad)
            pregame_ctrl.game_state.reserves.append(squad)
            return False
        _log(game_log, f"[scouts] {squad.owner}: {squad.name} deploys from reserves "
                       f"into its own zone (rule 24.31).")
        return True

    if branch == "scout_move" and movement_controller is not None:
        return _scout_move(
            pregame_ctrl, movement_controller, squad, distance, objectives, game_log,
        )
    return False


def _scout_move(pregame_ctrl, movement_controller, squad, distance, objectives, game_log):
    """Rule 24.32: a free move of up to Scouts X" before the battle, which must
    end more than 8" from every enemy unit.

    Aims at the nearest objective the unit does not already hold - the whole
    point of a scout move is to reach ground first - and walks the distance
    back until a legal end position is found, rather than giving up on the
    first rejection. A rigid translation, so rule 09.02's coherency and 9"
    spread are invariant by construction (the same argument _creep_toward()
    rests on)."""
    state = pregame_ctrl.game_state
    cx = sum(m.x_in for m in squad.models) / len(squad.models)
    cy = sum(m.y_in for m in squad.models) / len(squad.models)

    goal = None
    best = None
    for objective in objectives or ():
        if getattr(objective, "controlled_by", None) == squad.owner:
            continue
        d = objective.terrain_area.distance_to_point(cx, cy)
        if best is None or d < best:
            min_x, min_y, max_x, max_y = objective.terrain_area.bounding_box
            best, goal = d, ((min_x + max_x) / 2, (min_y + max_y) / 2)
    if goal is None:
        return False

    dx, dy = goal[0] - cx, goal[1] - cy
    length = (dx * dx + dy * dy) ** 0.5
    if length < 1e-6:
        return False
    ux, uy = dx / length, dy / length

    start = [(m.x_in, m.y_in) for m in squad.models]
    steps = 8
    for i in range(steps, 0, -1):
        travel = distance * i / steps
        movement_controller.start_scout_move(squad, distance)
        for model, (sx, sy) in zip(squad.models, start):
            model.x_in, model.y_in = sx + ux * travel, sy + uy * travel
        movement_controller.confirm_move()
        if movement_controller.state != movement.MOVING:
            _log(
                game_log,
                f'[scouts] {squad.owner}: {squad.name} makes a {travel:.1f}" scout move '
                f'(of {distance:g}" available, rule 24.32).',
            )
            return True
        movement_controller.cancel_move()

    for model, (sx, sy) in zip(squad.models, start):
        model.x_in, model.y_in = sx, sy
    _log(game_log, f"[scouts] {squad.owner}: {squad.name} found no legal scout move.", file_only=True)
    return False


def _log(game_log, message, file_only=False):
    if game_log is not None:
        game_log.add(message, file_only=file_only)
