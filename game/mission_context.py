"""MISSION CONTEXT and the board geometry every mission predicate asks about.

THE TWENTY-SIXTH EXTRACTION, at the SECOND consumer as this repo's convention
requires. All of this was written for game/secondary_missions.py's Tactical
card deck and lived there while that deck was the only thing asking. The
PRIMARY missions (game/primary_missions.py) ask the same questions - what is No
Man's Land, which objective is whose home, what are the table quarters, whose
half of the board is this point in - so the answers move here.

WHY MOVE RATHER THAN IMPORT
---------------------------
The other direction was available and is worse: game/primary_missions.py could
have imported these from game/secondary_missions.py. That would make a
player's PRIMARY mission depend on the SECONDARY card deck - two systems that
share nothing except this geometry, and one of which is off for most players
(config.SECONDARY_MISSION_CARD_PLAYERS). The dependency would be backwards and
permanent.

game/secondary_missions.py RE-EXPORTS every name below, so its seventeen cards
and the 543 checks in test_secondary_missions.py are unchanged BY
CONSTRUCTION - the same re-export idiom this codebase already uses for
is_tau_unit and has_detachment. test_secondary_missions.py pins that the
re-exported names are the SAME OBJECTS, not merely equal ones.

WHAT DID NOT MOVE
-----------------
Card-specific predicates stay with their cards: Outflank's board-edge tests,
Burden of Trust's guards, Display of Might's No Man's Land test, the expansion
objective ranking. They have one consumer each. The rule is "extract at the
second consumer", not "extract everything that looks generic".
"""

from game import config

# Rule 03.04's Engagement Range and the objective range live on the units they
# belong to. This one is a MISSION distance: "not within 6" of the centre of
# the battlefield", printed identically on Engage on All Fronts (Secondary) and
# Reconnaissance Sweep (Primary).
#
# It was ENGAGE_CENTRE_EXCLUSION_IN while Engage on All Fronts was its only
# carrier. A constant named after the first ability to want it is the lying
# name this repo renames rather than copies (see game/melee_crit.py,
# game/ere_we_go.py); secondary_missions.py keeps the old name as an alias so
# its own test pins still read.
CENTRE_EXCLUSION_IN = 6.0


def _other_player(player):
    # Was a local copy in game/secondary_missions.py, per this codebase's usual
    # per-module small-helper convention. It came along with MissionContext,
    # whose `opponent` property is its main caller; game/missions.py and the
    # others still keep their own.
    return "Player 2" if player == "Player 1" else "Player 1"


def _live_squads(tokens):
    """Every squad with at least one model still on the board. Derived from
    tokens rather than from a squad list so a wiped-out unit cannot linger -
    the same source main.py's own `{t.squad for t in state.tokens}` sets use."""
    return {t.squad for t in tokens if t.squad is not None and t.squad.models}


def board_centre():
    """The centre of the battlefield, in inches. Read from config at CALL time
    - maps.apply_to_config() writes the board dimensions at startup, so a
    module-level copy would be the pre-map board (see game/config.py's own note
    forbidding `from game.config import BOARD_WIDTH_IN`)."""
    return (config.BOARD_WIDTH_IN / 2.0, config.BOARD_HEIGHT_IN / 2.0)


def model_distance_to_point(model, x_in, y_in):
    """Base-EDGE distance from a model to a bare point, the same
    edge-not-centre convention game/squad.py's edge_distance() uses between two
    models. It was kept local while the Secondary deck was its only consumer;
    the Primary missions are the second, which is what moved it here."""
    dx = model.x_in - x_in
    dy = model.y_in - y_in
    return max(0.0, (dx * dx + dy * dy) ** 0.5 - model.radius_in)


def _unit_within_of_point(squad, x_in, y_in, range_in):
    return any(model_distance_to_point(m, x_in, y_in) <= range_in for m in squad.models)


def objective_centre(objective):
    """The middle of an objective's terrain footprint, in inches. An Objective
    is a TerrainArea (13.01) made of axis-aligned features, so this is the
    centre of their common bounding box - the same `bounding_box` the renderer
    already draws the marker's outline from."""
    min_x, min_y, max_x, max_y = objective.terrain_area.bounding_box
    return ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)


def zone_distance(zone, x_in, y_in):
    """Distance from a point to the nearest edge of a deployment zone, 0 if
    inside it.

    This WAS a second, hand-written copy of DeploymentZone.distance_to_point()
    - identical arithmetic, and the two disagreed only on the empty-zone
    fallback (0.0 there, inf here; see shapes.Union.signed_distance for which
    one won and why). Kept as a name because six call sites read it, but it is
    now the one definition asked once, so a zone that is not a rectangle list
    answers here too."""
    return zone.distance_to_point(x_in, y_in)


def _board_box():
    return (0.0, 0.0, config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN)


def _zone_centre(zone):
    """A representative point inside the zone. Sampled from the shape rather
    than averaged over rectangle centres, so it is still inside for a diagonal
    or holed zone - a rectangle-centre average is only meaningful while the
    zone IS rectangles.

    NO PRODUCTION CALLER since in_own_territory() went from comparing zone
    CENTRES to comparing the zones themselves (see its docstring for why). It
    stays, and stays re-exported by game/secondary_missions.py, because
    test_deployment_shapes.py rebuilds both superseded rules from it: the
    pre-shape axis pick and the centre bisector that replaced it. A pre-fix
    world you cannot rebuild is a fix you cannot measure."""
    return zone.centroid(board_box=_board_box())


def in_own_territory(ctx, x_in, y_in):
    """Whether a point is in `ctx.player`'s own half of the board.

    User's definition, supplied with the Beacon card: "Territory heisst einfach
    ausserhalb meiner Spielfeldhaelfte" - so territory is a HALF-BOARD, a much
    bigger area than the deployment zone inside it, which is why Beacon pays 5
    for leaving it and only 3 for leaving the zone.

    Which half is whose is DERIVED from where the two deployment zones sit
    rather than assumed, and the derivation is the PERPENDICULAR BISECTOR of
    the line between the two zone centres: your territory is every point
    closer to your own zone than to your opponent's. That is the split for a
    diagonal or corner deployment as much as for a banded one - the dividing
    line simply turns with the zones instead of being picked from two board
    axes.

    It replaces exactly that axis pick ("whichever of x/y separates them,
    split the board in half there"), which could only ever produce a
    horizontal or a vertical line. Behaviour-neutral where the old form
    applied: measured over a 201x201 grid on all three shipped maps for both
    players, 0 of 40401 points change hands on each - the shipped zones are
    symmetric about the board centre, so their bisector IS the old centre
    line.

    Falls back to "everything is your territory" when the zones are unknown -
    that scores 0 rather than inventing a free 5 VP."""
    mine = [z for z in ctx.deployment_zones if z.owner == ctx.player]
    theirs = [z for z in ctx.deployment_zones if z.owner == ctx.opponent]
    if not mine or not theirs:
        return True
    my_cx, my_cy = _zone_centre(mine[0])
    their_cx, their_cy = _zone_centre(theirs[0])
    # Squared distances: same comparison, no sqrt - this is read once per model
    # per scoring card.
    to_mine = (x_in - my_cx) ** 2 + (y_in - my_cy) ** 2
    to_theirs = (x_in - their_cx) ** 2 + (y_in - their_cy) ** 2
    return to_mine <= to_theirs


def table_quarters():
    """The four table quarters, as (min_x, min_y, max_x, max_y) in inches.

    Split at the battlefield centre on both axes - the plain reading of "table
    quarter", and the only one that works on all three boards here (44x60
    portrait, 60x44 landscape, 30x30 square) without special cases."""
    centre_x, centre_y = board_centre()
    width, height = config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN
    return [
        (0.0, 0.0, centre_x, centre_y),          # NW
        (centre_x, 0.0, width, centre_y),        # NE
        (0.0, centre_y, centre_x, height),       # SW
        (centre_x, centre_y, width, height),     # SE
    ]


def _model_wholly_in_rect(model, rect):
    min_x, min_y, max_x, max_y = rect
    r = model.radius_in
    return (min_x <= model.x_in - r and model.x_in + r <= max_x
            and min_y <= model.y_in - r and model.y_in + r <= max_y)


def unit_has_presence_in(squad, rect, ctx):
    """Engage on All Fronts' own definition of "presence":

        "You have a presence in a table quarter if one or more friendly units
        (excl. AIRCRAFT & battle-shocked) are wholly within it and not within
        6" of the battlefield centre."

    Two conditions on the SAME unit, and the second is the one that makes the
    card hard: a unit parked on the middle of the board sits in a quarter but
    is too close to the centre to count, so spreading out is not enough - you
    have to spread out AWAY from the middle.

    "Wholly within it" is measured per model base, so a unit straddling a
    centre line is in neither quarter."""
    if squad.battle_shocked or not squad.models:
        return False
    if not all(_model_wholly_in_rect(m, rect) for m in squad.models):
        return False
    centre_x, centre_y = board_centre()
    return all(model_distance_to_point(m, centre_x, centre_y) > CENTRE_EXCLUSION_IN
               for m in squad.models)


def quarters_with_presence(ctx):
    quarters = table_quarters()
    friendly = ctx.friendly_squads()
    return [rect for rect in quarters
            if any(unit_has_presence_in(sq, rect, ctx) for sq in friendly)]


def no_mans_land_objectives(ctx):
    """The objectives in No Man's Land - i.e. inside NOBODY's deployment zone.

    That single test also delivers the card's "excl. home objectives" clause
    for free, and does it without reading names: every map here places its home
    objectives inside their owner's zone, so "not in a deployment zone" and
    "not a home objective" pick out the same set. Deriving it from geometry
    rather than from the string "Home" means a renamed or newly added objective
    is classified correctly on its own."""
    out = []
    for objective in ctx.objectives:
        cx, cy = objective_centre(objective)
        if not any(z.contains_point(cx, cy) for z in ctx.deployment_zones):
            out.append(objective)
    return out


def own_home_objective(ctx):
    """The card player's OWN home objective: the one inside their deployment
    zone. Derived from geometry, like every other objective classification
    here, so a renamed objective still resolves."""
    mine = [z for z in ctx.deployment_zones if z.owner == ctx.player]
    for objective in ctx.objectives:
        cx, cy = objective_centre(objective)
        if any(z.contains_point(cx, cy) for z in mine):
            return objective
    return None


def enemy_home_objective(ctx):
    """The OPPONENT's home objective - own_home_objective() from the other
    side, so the two cannot disagree about what "home" means."""
    theirs = [z for z in ctx.deployment_zones if z.owner == ctx.opponent]
    for objective in ctx.objectives:
        cx, cy = objective_centre(objective)
        if any(z.contains_point(cx, cy) for z in theirs):
            return objective
    return None


def _non_home_objectives(ctx):
    """Every objective except the card player's OWN home one.

    Cleanse says "excl. your home objective" - singular and possessive, so the
    ENEMY's home objective is a legal target. Derived from geometry like
    no_mans_land_objectives(): a home objective is one inside its owner's
    deployment zone, so "mine" is one inside MY zone."""
    mine = [z for z in ctx.deployment_zones if z.owner == ctx.player]
    out = []
    for objective in ctx.objectives:
        cx, cy = objective_centre(objective)
        if not any(z.contains_point(cx, cy) for z in mine):
            out.append(objective)
    return out


class MissionContext:
    """Everything a card's predicate is allowed to look at. A plain bag rather
    than passing five arguments around: a new card that needs one more fact
    adds a field here instead of changing every predicate's signature."""

    def __init__(self, player, tokens=(), turn_tracker=None, ending_player=None,
                 destroyed_this_turn=(), destroyed_squads_this_turn=(),
                 destroyed_characters_this_battle=(), all_squads=None,
                 objectives=(), deployment_zones=(), card_state=None,
                 battle_round=None, embarked_squads=(), hand=(), terrain_areas=(),
                 on_objective_at_turn_start=(),
                 on_central_objective_at_turn_start=(),
                 in_terrain_at_turn_start=None,
                 objectives_controlled_at_turn_start=()):
        # The cards currently in hand. Two cards ask whether ANOTHER card is
        # "active" (Cleanse about Plunder and vice versa), which is the only
        # thing in this module that looks sideways at the rest of the hand.
        self.hand = list(hand)
        # Terrain areas (13.01) - Plunder's targets.
        self.terrain_areas = list(terrain_areas)
        # id(squad) for every enemy unit that was within range of an objective
        # at the START of this turn. A snapshot, because Overwhelming Force
        # asks about a moment that has passed by the time it scores - and about
        # units that no longer exist.
        self.on_objective_at_turn_start = set(on_objective_at_turn_start)
        # Three more turn-start snapshots, all filled by the PRIMARY mission
        # controller and left empty by the Secondary deck. Same reason as the
        # one above: each is a fact about a moment that is over by the time the
        # box scores, and about units that no longer exist by then.
        #
        # id(squad) for every enemy unit within range of a CENTRAL objective
        # (Secure Asset's kill clause). A separate set from the one above, not
        # a subset computed later, because "any objective" and "a central one"
        # are different questions and the units are gone by scoring time.
        self.on_central_objective_at_turn_start = set(on_central_objective_at_turn_start)
        # {id(squad): frozenset(id(terrain_area))} for every enemy unit
        # standing in one or more terrain areas (Death Trap's kill clause,
        # which needs to know WHICH area, not merely that there was one).
        self.in_terrain_at_turn_start = dict(in_terrain_at_turn_start or {})
        # id(objective) for the objectives THIS player controlled at the start
        # of the turn (Unstoppable Force's "you did not control at the start of
        # the turn"). Unlike the two above this is about the board, not about
        # the dead - but it is just as unrecoverable once control has changed.
        self.objectives_controlled_at_turn_start = set(objectives_controlled_at_turn_start)
        # The battle round the ENDING TURN belonged to. Passed in rather than
        # read off turn_tracker: begin_end_of_turn() runs AFTER
        # TurnTracker.advance_phase(), which - when the second player's turn
        # ends - has already incremented battle_round. A card asking "is this
        # round 5" would then see 6 and never fire.
        self.battle_round = battle_round
        # Units inside a TRANSPORT (18.02). Neither on the board nor in
        # reserves; Beacon's setup explicitly offers them.
        self.embarked_squads = list(embarked_squads)
        # Board furniture, for cards that talk about places rather than kills.
        self.objectives = list(objectives)
        self.deployment_zones = list(deployment_zones)
        # The per-card scratchpad. A card that remembers something across the
        # battle (which objective is your tempting target, which unit is your
        # beacon) MUST keep it here and not on itself: the SecondaryMissionCard
        # objects are module-level singletons shared by every battle, and
        # writing state onto one is the shared-class-attribute trap this
        # codebase already documents for UnitProfile. The controller owns the
        # dict, keyed by card, so two battles cannot see each other's choices.
        self.card_state = {} if card_state is None else card_state
        self.player = player
        self.tokens = list(tokens)
        self.turn_tracker = turn_tracker
        self.ending_player = ending_player
        # Models destroyed since the last turn boundary, both sides. Cards that
        # say "destroyed this turn" read this; nothing else does.
        self.destroyed_this_turn = list(destroyed_this_turn)
        # Whole UNITS wiped out since the last turn boundary. A separate list,
        # not derived from the models above: "unit destroyed" is main.py's own
        # attached_units.unit_is_destroyed() judgement (19.01 merges a leader
        # into its bodyguard squad, so a half-dead unit is not a destroyed
        # one), and re-deriving it here would be a second opinion on a question
        # the engine already answers.
        self.destroyed_squads_this_turn = list(destroyed_squads_this_turn)
        # Enemy CHARACTER models destroyed at ANY point in the battle - a
        # longer lifetime than everything above, for Assassination's
        # "have been destroyed during the battle" clause.
        self.destroyed_characters_this_battle = list(destroyed_characters_this_battle)
        # Every unit still in the game, wherever it is - board, Strategic
        # Reserves (03.02) or embarked in a transport (18.02). `tokens` is the
        # BOARD only, so a card asking "are any left at all" must not use it:
        # a character sitting in reserves is not on the battlefield and is also
        # very much not destroyed. main.py supplies state.all_squads().
        self._all_squads = None if all_squads is None else list(all_squads)

    @property
    def opponent(self):
        return _other_player(self.player)

    def friendly_squads(self):
        return [sq for sq in _live_squads(self.tokens) if sq.owner == self.player]

    def enemy_squads(self):
        return [sq for sq in _live_squads(self.tokens) if sq.owner != self.player]

    def all_squads(self):
        """Board + reserves + embarked. Falls back to the board alone when no
        richer source was supplied (tests that only care about the board)."""
        if self._all_squads is None:
            return list(_live_squads(self.tokens))
        return [sq for sq in self._all_squads if sq is not None and sq.models]

    def living_enemy_models(self):
        return [m for sq in self.all_squads() if sq.owner != self.player for m in sq.models]


# How close two objectives' distances to the board centre may be and still
# count as tied. A tie is not a coincidence to be broken - it is how a
# point-symmetric board says "these two are the middle" (map3's Objective East
# and Objective West are a mirror pair, both 6.13" out).
#
# MEASURED INERT on the three shipped maps, which is why it is written down
# rather than assumed: map3's two distances are not merely close but BIT
# IDENTICAL (6.13394652731827872 both, delta exactly 0.0), so nothing today
# depends on this number. It is the safety net for a future map whose mirroring
# goes through different arithmetic on each side - the same 7e-15 mismatch that
# once turned a rectangle into a pentagon in renderer.objective_outline_points().
# A thousandth of an inch absorbs that and cannot reach anything real: the
# nearest genuinely-not-central objective on any shipped map is 11" further out.
CENTRAL_OBJECTIVE_TIE_IN = 0.001


def central_objectives(ctx):
    """The "central objectives" - the objective(s) nearest the middle of the
    battlefield, TIES INCLUDED.

    Read by two Primary missions (Secure Asset's kill clause, Unstoppable
    Force's final scoring). There was no such predicate before them, and the
    name alone could not supply one: "Central Objective" is a NAME on map1 and
    map2 and DOES NOT EXIST on map3, whose middle is a 9" no-man's-land disc
    holding two objectives instead of one. A name test would leave two scoring
    boxes permanently dead on that map.

    Derived from geometry, like every other classification in this module, and
    deliberately with NO distance constant: "nearest, plus whatever ties with
    it" needs no threshold to be chosen and cannot be quietly wrong on a map
    nobody measured. Measured on the three shipped boards:

        map1  Central 0.0"   | next nearest 17.4"  -> {Central Objective}
        map2  Central 0.0"   | next nearest 20.0"  -> {Central Objective}
        map3  East/West 6.1" | next nearest 22.8"  -> {Objective East, West}

    Candidates are the NO MAN'S LAND objectives, not all of them: an objective
    inside a deployment zone is that player's home objective, which is the one
    thing "central" certainly does not mean. On all three shipped maps this
    changes nothing (every home objective is further out than the winner
    anyway) - it is there so a map that packed a deployment zone against the
    middle could not hand someone their own home objective as a central one.
    """
    candidates = no_mans_land_objectives(ctx)
    if not candidates:
        return []
    centre_x, centre_y = board_centre()

    def distance(objective):
        cx, cy = objective_centre(objective)
        return ((cx - centre_x) ** 2 + (cy - centre_y) ** 2) ** 0.5

    nearest = min(distance(o) for o in candidates)
    return [o for o in candidates
            if distance(o) <= nearest + CENTRAL_OBJECTIVE_TIE_IN]
