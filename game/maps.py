"""Board layouts ("maps") the demo scene can be played on.

Until now main() built exactly one battlefield inline: board size from
config, one hard-coded terrain block, one pair of deployment zones and one
hard-coded per-model position table per army. A second layout (User: "ich
hätte gerne eine 2te map ... dabei soll die erste map und aufstellung nicht
weggeworfen werden. sondern es soll zusätzlich existieren") needs all four of
those to vary together - and they really do vary together: map 2 is
LANDSCAPE, so its deployment zones run along different edges, at a different
depth, and every position in the old tables is outside the board.

So a BattleMap carries exactly that set - board size, zones, terrain, and the
deployment positions the armies use on it - and nothing else. WHICH units get
built, their wargear, points and reserve/transport assignments stay in
main.py: those are the army lists, and both maps field the same two armies.

Board size is the one piece of this that isn't passed around as a value:
config.BOARD_WIDTH_IN/BOARD_HEIGHT_IN are read directly by two dozen call
sites across the engine and the AI. apply_to_config() therefore writes the
chosen map's dimensions into those names once, before anything else runs -
every one of those readers goes through `config.BOARD_WIDTH_IN` at call time
(none of them does `from game.config import BOARD_WIDTH_IN`, checked), so
they all see the selected map. It is deliberately a one-shot at startup, not
something to call again mid-game.
"""

from game import shapes
from game.deployment import DeploymentZone
from game.terrain import LIGHT, Obstacle, ruin, ruin_l


class BattleMap:
    """One playable battlefield: its size, its deployment zones, its terrain,
    and where each army sets up on it."""

    def __init__(self, key, name, width_in, height_in, zones, terrain, player1, player2,
                 army_roster=None):
        self.key = key
        self.name = name
        self.width_in = width_in
        self.height_in = height_in
        self.zones = zones          # [(owner, rects_or_Shape), ...] - see build()
        self._terrain = terrain     # callable(state) -> adds terrain areas + objectives
        self.player1 = player1      # Player1Deployment
        self.player2 = player2      # Player2Deployment
        # Which units of an army list this map actually fields, keyed by army
        # list ("aeldari"/"orks"/"necrons") - or None for "all of them", which
        # is what the two full boards use and why they are unaffected by this
        # existing.
        #
        # A small map wants a small army: the point of map 3 is a turn that
        # takes seconds, and fourteen units against eleven does not. The army
        # LISTS stay in game/army_lists.py either way - this only says which of
        # them turn up, so there is still exactly one place a unit is defined.
        #
        # PER ARMY AND NOT PER PLAYER, with "{p}" standing in for the owner's
        # digit. A roster has to name units by their exact squad name (see
        # army_lists.unit_name()), and that name starts with the owner - so the
        # moment EITHER player could field ANY of the three lists, a set of
        # fixed names could only ever be right for one pairing. With the wrong
        # one, no name would match and the map would silently field half a
        # battle, which is exactly what the guard in main.py refuses loudly.
        self.army_roster = {
            key: set(names) for key, names in (army_roster or {}).items()
        } or None

    def roster_for(self, armies=None):
        """The complete set of squad names this map fields for this pairing -
        {player -> army key} in, one flat set of exact squad names out - or
        None for a map that fields everything.

        A list neither player picked simply contributes nothing; a list BOTH
        picked contributes its names twice, once per owner, which is what makes
        a mirror match work."""
        if self.army_roster is None:
            return None
        names = set()
        for owner, key in sorted((armies or {}).items()):
            for name in self.army_roster.get(key, ()):
                names.add(name.replace("{p}", str(owner)[-1]))
        return names

    def fields(self, squad, armies=None):
        """Whether this map's scene includes `squad`."""
        roster = self.roster_for(armies)
        return roster is None or squad.name in roster

    @property
    def center(self):
        return (self.width_in / 2, self.height_in / 2)

    def build(self, state):
        """Adds this map's deployment zones, terrain areas and objectives to
        `state`. Call once, after apply_to_config()."""
        for owner, spec in self.zones:
            # A zone is written either as axis-aligned rectangles (the form the
            # two big boards use) or as a game/shapes.py Shape - which is what
            # a diagonal, rotated or holed zone needs. One line here, because
            # DeploymentZone answers every question from a signed distance
            # either way.
            if isinstance(spec, shapes.Shape):
                state.add_deployment_zone(DeploymentZone(owner, shape=spec))
            else:
                state.add_deployment_zone(DeploymentZone(owner, spec))
        self._terrain(state, self)


class Player1Deployment:
    """Where Player 1 (T'au) sets up. `squads` is one list of per-model
    (x_in, y_in) per entry of main()'s own ARMY table, in the same order."""

    def __init__(self, squads, devilfish):
        self.squads = squads
        self.devilfish = devilfish


class Player2Deployment:
    """Where Player 2 (Orks) sets up - one attribute per unit, since that
    army is built unit by unit in main() rather than from a single table."""

    def __init__(self, gretchin, stormboyz, warbikers, boyz1, trukks, deff_dread):
        self.gretchin = gretchin
        self.stormboyz = stormboyz
        self.warbikers = warbikers
        self.boyz1 = boyz1
        self.trukks = trukks
        self.deff_dread = deff_dread


# ---------------------------------------------------------------------------
# Map 1 - the original 44"x60" portrait board.
#
# Terrain, zones and positions below are the exact values main() used inline
# before there was more than one map; the long provenance comments that
# belong to individual pieces/positions moved here with them, unedited.
# ---------------------------------------------------------------------------

def _map1_terrain(state, battle_map):
    # Positions come from actually measuring the reference image's own pixels
    # (loaded straight from the image file, not eyeballed off a screenshot):
    # the board frame and 1"-grid spacing were located via color-transition/
    # brightness scans, then every green (rubble) and gold (barricade/corner-
    # brace) terrain marking was found via a connected-component scan and
    # converted from pixel to inch coordinates using that scale - see
    # CLAUDE.md for the full method and the per-piece confidence notes.
    # North-half pieces are the measured positions directly; every south-half
    # piece is that same piece mirrored through the board center (44 - x,
    # 60 - y) - confirmed independently by the fact that the *measured*
    # south-half blobs land within a fraction of an inch of that mirror,
    # matching the map's real 180-degree rotational symmetry. The source
    # article ("Take cover with updated terrain rules",
    # warhammer-community.com) additionally names this layout's official piece
    # inventory (4 large rectangles 7"x11.5", 2 large right-angle triangles
    # 8"x11.5", 4 medium rectangles 6"x4", 2 long lines 10"x2.5", 4 short
    # lines 6"x2") - used where it lines up with a measurement (e.g. the four
    # large rectangles below), but NOT blindly substituted for one: the two
    # "triangles" were first drawn as their full 8"x11.5" bounding rectangle
    # on the assumption they belonged at the measured NW/SE corner spots -
    # wrong twice over (a triangle is half that area, and the actual measured
    # blob there is a thin 1.5"x7.1" strip, not anywhere near 8"x11.5") -
    # fixed below to track the measurement, not the inventory entry that
    # happened to be left over. The central ruin is a dedicated 17th piece,
    # not part of that 16-piece inventory (already used up by the 8 mirrored
    # pairs below) - presumably added specifically for the mission's central
    # objective.
    #
    # Wall layout (User-Vorgabe): every ruin except the central one gets
    # ruin_l() instead of ruin() - two partial (2/3), doorless walls forming
    # an L whose corner points at the board's center - rather than the old
    # all-four-sides-with-a-door-in-the-middle layout, which visually read as
    # walls bunched at the corners. The central ruin keeps ruin()'s original
    # corner layout, since it has no single "facing the enemy" side.
    cx, cy = battle_map.center
    state.add_terrain_area(ruin_l(x_in=5.0, y_in=13.0, width_in=3.0, height_in=8.0, facing_x=cx, facing_y=cy))  # tall thin ruin, NW corner
    p2_home_area = state.add_terrain_area(ruin_l(x_in=20.0, y_in=13.0, width_in=11.5, height_in=7.0, facing_x=cx, facing_y=cy))  # large rectangle
    state.add_objective(p2_home_area, name="P2 Home Objective")
    state.add_terrain_area([Obstacle(x_in=32.0, y_in=13.3, width_in=10.0, height_in=2.5, category=LIGHT)])  # long line

    # Re-cropped straight from the source image at 3x zoom after the user
    # flagged this whole area as wrong: no ruin actually sits at the spot
    # picked in the previous pass (that crop shows plain red zone) - removed.
    # In its place, two DIFFERENT pieces the crop actually shows near the tall
    # corner ruin: a small gray ruin with gold corner braces, and a separate
    # small ruin containing a distinct green machine/generator graphic (not
    # moss - a different decoration style, still a normal Dense ruin footprint
    # for our purposes).
    state.add_terrain_area([Obstacle(x_in=10.0, y_in=18.0, width_in=6.0, height_in=2.5, category=LIGHT)])  # short line, next to the tall ruin
    state.add_terrain_area(ruin_l(x_in=3.5, y_in=21.0, width_in=6.5, height_in=5.0, facing_x=cx, facing_y=cy))  # small ruin, gold corner braces
    state.add_terrain_area(ruin_l(x_in=8.0, y_in=27.0, width_in=4.0, height_in=6.0, facing_x=cx, facing_y=cy))  # small ruin, green machine/generator graphic
    no_mans_land_ne = state.add_terrain_area(ruin_l(x_in=37.5, y_in=22.2, width_in=11.5, height_in=7.0, facing_x=cx, facing_y=cy))  # large rectangle
    state.add_objective(no_mans_land_ne, name="Objective Northeast")

    central_area = state.add_terrain_area(ruin(x_in=22.0, y_in=30.0, width_in=11.0, height_in=9.5))
    state.add_objective(central_area, name="Central Objective")

    # South-half pieces - each one the matching north-half piece above, mirrored.
    state.add_terrain_area(ruin_l(x_in=39.0, y_in=47.0, width_in=3.0, height_in=8.0, facing_x=cx, facing_y=cy))  # tall thin ruin, SE corner
    p1_home_area = state.add_terrain_area(ruin_l(x_in=24.0, y_in=47.0, width_in=11.5, height_in=7.0, facing_x=cx, facing_y=cy))
    state.add_objective(p1_home_area, name="P1 Home Objective")
    state.add_terrain_area([Obstacle(x_in=12.0, y_in=46.7, width_in=10.0, height_in=2.5, category=LIGHT)])

    state.add_terrain_area([Obstacle(x_in=34.0, y_in=42.0, width_in=6.0, height_in=2.5, category=LIGHT)])  # short line, next to the tall ruin
    state.add_terrain_area(ruin_l(x_in=40.5, y_in=39.0, width_in=6.5, height_in=5.0, facing_x=cx, facing_y=cy))  # small ruin, gold corner braces
    state.add_terrain_area(ruin_l(x_in=36.0, y_in=33.0, width_in=4.0, height_in=6.0, facing_x=cx, facing_y=cy))  # small ruin, green machine/generator graphic
    no_mans_land_sw = state.add_terrain_area(ruin_l(x_in=6.5, y_in=37.8, width_in=11.5, height_in=7.0, facing_x=cx, facing_y=cy))
    state.add_objective(no_mans_land_sw, name="Objective Southwest")


MAP1 = BattleMap(
    key="map1",
    name="Take Cover (44\"x60\", portrait)",
    width_in=44.0,
    height_in=60.0,
    # Deployment zones (rule 03.01): a flat 18"-deep rectangle along each
    # player's own board edge, matching the reference map's explicitly labeled
    # "18"" red-zone depth. An earlier version modeled the blue zone as
    # stepped (18.5"/19.5", read off two different numbers near its bottom
    # edge) - dropped: that's almost certainly just where the map's DRAWN
    # boundary line happens to bend around the corner terrain pieces (the two
    # large triangles below sit right on that line), not a real depth
    # difference the mission rules would define.
    zones=[
        ("Player 2", [(22.0, 9.0, 44.0, 18.0)]),
        ("Player 1", [(22.0, 51.0, 44.0, 18.0)]),
    ],
    terrain=_map1_terrain,
    # User feedback, 5th round: a squad-average-based reconstruction (an
    # earlier version of this) loses per-model adjustments - e.g. one Stealth
    # Battlesuit nudged individually to avoid standing on a wall (rule
    # 13.05/13.06: BATTLESUIT isn't INFANTRY/BEASTS/SWARM/MOBILE, so it can't
    # just walk through Dense terrain the way this map's infantry squads can) -
    # rebuilding a uniform row from the average put it right back on that wall.
    # So this is each model's own exact x_in/y_in, dragged by hand in a live
    # run and read back via a temporary "P" debug key (since removed) that
    # dumped every model - not just each squad's center - to a file.
    player1=Player1Deployment(
        squads=[
            [  # Breacher Team 1 (embarked in the Devilfish, with Cadre Fireblade)
                (11.20, 49.30), (12.70, 49.30), (14.20, 49.30), (15.70, 49.30), (17.20, 49.30),
                (11.20, 51.30), (12.70, 51.30), (14.20, 51.30), (15.70, 51.30), (17.20, 51.30),
            ],
            [  # Strike Team 1
                (21.08, 51.68), (22.58, 51.68), (24.08, 51.68), (25.58, 51.68), (27.08, 51.68),
                (21.08, 53.68), (22.58, 53.68), (24.08, 53.68), (25.58, 53.68), (27.08, 53.68),
            ],
            [  # Strike Team 2
                (30.69, 48.43), (32.19, 48.43), (33.69, 48.43), (35.19, 48.43), (36.69, 48.43),
                (30.69, 50.43), (32.19, 50.43), (33.69, 50.43), (35.19, 50.43), (36.69, 50.43),
            ],
            [  # Kroot Carnivores 1
                (5.65, 42.90), (7.15, 42.90), (8.65, 42.90), (10.15, 42.90), (11.65, 42.90),
                (5.65, 44.90), (7.15, 44.90), (8.65, 44.90), (10.15, 44.90), (11.65, 44.90),
            ],
            [  # Kroot Carnivores 2
                (19.74, 45.09), (21.24, 45.09), (22.74, 45.09), (24.24, 45.09), (25.74, 45.09),
                (19.74, 47.09), (21.24, 47.09), (22.74, 47.09), (24.24, 47.09), (25.74, 47.09),
            ],
            [  # Stealth Battlesuits - deliberately NOT a uniform row (hand-adjusted around a wall)
                (32.24, 46.39), (31.09, 44.73), (33.33, 44.79), (35.45, 44.70), (34.53, 46.39),
            ],
            [(5.2, 48.2)],  # Ghostkeel Battlesuit
        ],
        # Deliberately in the same guaranteed-terrain-free near-edge strip the
        # squads above use (y>51), but further IN from the SE corner than the
        # tall thin ruin there (x 37.5-40.5) to keep clearance, and further
        # back (y=57) than every already-placed squad's own deepest model
        # (Strike Team 1's y=53.68 is the max among all of them) so it can't be
        # placed on top of anything already deployed.
        devilfish=(41.0, 57.0),
    ),
    player2=Player2Deployment(
        gretchin=[
            # 10x Gretchin, on the P2 Home Objective (x 14.25-25.75, y 9.5-16.5)
            (16.50, 11.30), (17.75, 11.30), (19.00, 11.30), (20.25, 11.30), (21.50, 11.30),
            (16.50, 13.30), (17.75, 13.30), (19.00, 13.30), (20.25, 13.30), (21.50, 13.30),
            (23.00, 12.30),  # Runtherd
        ],
        # 10x Stormboyz (Boss Nob first), forward near the NW ruin. User
        # report: the original two-row layout put 3 of the 10 models
        # (6.00,15.30), (4.50,17.30), (6.00,17.30) ON TOP of the ruin's own
        # Dense wall segments - illegal even for INFANTRY (rule 13.06 only lets
        # a model move THROUGH Dense terrain, rule 13.05 still forbids ending a
        # move overlapping it; model_terrain_violation() applies
        # unconditionally, no INFANTRY exception). The ruin's own walls block a
        # roughly x[3.87,7.13] band up to about y~17.6, which a straight
        # two-row rectangle can't dodge without either shrinking to fewer than
        # 5 columns or leaving the NW corner - re-searched (automated overlap
        # search, same method as elsewhere in this block) for a layout that
        # hugs the board's NW corner/ruin instead, clear of every Dense wall
        # segment, the board edge, and the Boyz 1 block below.
        stormboyz=[
            (0.70, 17.00), (2.20, 17.00),
            (0.70, 15.50), (2.20, 15.50), (3.70, 15.50), (5.20, 15.50),
            (0.70, 14.00), (2.20, 14.00), (3.70, 14.00), (5.20, 14.00),
        ],
        # TWO 3-model Warbiker squads instead of one 6-model squad (user:
        # "splitte den 6er bike squad bitte in 2 3er bike squads auf. vielleicht
        # ist es im echten spiel auch schwierig mit einem 6er squad die
        # kohärenz in engen korridoren zu halten"). Exactly right, and
        # measurable: the 6-model squad spans ~6" in formation, and the
        # shortest way out of the NE ruin is a 3.5" slot between the wall's end
        # and the board edge - six bikes cannot pass it without either
        # overlapping or breaking rule 09.02's 9" spread, which is why that
        # squad kept stalling there. Three bikes fit through the same slot with
        # room over. Costs nothing: the points list prices Warbikers at 3
        # models for 60 and 6 for 120.
        warbikers=[
            # 3x Warbikers (Boss Nob on Warbike first), right flank, clear of
            # both ruins and the Trukks - the front row of what used to be the
            # 6-model block.
            [(36.50, 13.50), (39.10, 13.50), (41.70, 13.50)],
            # 3x Warbikers behind Boyz 1 (which sits at y 15.50-17.05,
            # x 11.00-17.20), west of Gretchin's own block (x>=16.50) and east
            # of the Stormboyz (x<=5.20).
            [(9.50, 13.50), (12.10, 13.50), (14.70, 13.50)],
        ],
        # Boyz 1's own disembark spot - two rounds of user reports:
        # 1) the first attempt (south of the P2 Home ruin, y=17.30/18.85) put
        #    its second row at y=18.85, PAST the Player 2 deployment zone's own
        #    y<=18 bound - illegal, even though DeploymentZone itself doesn't
        #    enforce it (see that class's own docstring).
        # 2) the fix for that (retreating to the open strip north of every
        #    ruin, y~5.2-6.75) over-corrected - legal, but "zu weit hinten".
        # Re-searched for the FORWARD-most legal 5x2 block: inside the P2 Home
        # ruin's own LIGHT footprint (non-blocking) but west of where its Dense
        # south wall actually starts (x=18.08), below Gretchin's own footprint,
        # and clear of both the ruin's Dense walls and Trukk 1.
        boyz1=[
            (11.00, 17.05), (12.55, 17.05), (14.10, 17.05), (15.65, 17.05), (17.20, 17.05),
            (11.00, 15.50), (12.55, 15.50), (14.10, 15.50), (15.65, 15.50), (17.20, 15.50),
        ],
        # Trukk 1 sits directly BEHIND the Deff Dread (same x, lower y - P2
        # deploys at low y and advances toward high y), which is why it's not
        # level with Trukk 2 (User: "kannst den deffdread etwas weiter vorne
        # platzieren vielleicht an die position des linken trukks und den trukk
        # dafür direkt dahinter?"). 0.92" edge gap between the two hulls -
        # deliberately not tighter, so Trukk 1 keeps a usable disembark ring
        # (18.04) on the side the Deff Dread isn't covering.
        trukks=[(29.0, 12.0), (33.0, 15.5)],
        # Moved up to what used to be Trukk 1's spot; verified clear of every
        # terrain feature/token, and it's the forward-most of P2's non-reserve
        # units now, which is the point of the change.
        deff_dread=(29.0, 15.5),
    ),
)


# ---------------------------------------------------------------------------
# Map 2 - a 60"x44" LANDSCAPE board (User: "für map layout 2 habe ich ein png
# abgelegt map2 layout.png ... bedenke dabei, dass die map im querformat ist").
#
# Measured the same way map 1 was, from "map2 layout.png" itself rather than
# by eye: the two shaded deployment zones fix the scale (both are exactly 20
# px/inch and 12" deep, which is also what the image's own "12"" labels say),
# and every terrain piece was then found by a connected-component scan over
# the footprint/rubble/barricade colors, with each piece's angle and size
# taken from a brute-force minimum-area-rectangle sweep over its pixels.
#
# The layout has the same 180-degree rotational symmetry map 1 does (every
# measured south/east piece lands within ~0.2" of the mirror of its north/west
# twin), so - exactly as in map 1 - the north/west half below is the measured
# half and the south/east half is defined as its mirror through the board
# center, rather than carrying two independently noisy measurements of the
# same thing.
#
# Piece inventory as measured: 4 large rectangles 11.5"x7" (each carrying an
# objective marker), 1 larger central rectangle 12.2"x9.75" (the 5th
# objective), 4 medium rectangles 6"x4", 2 long lines 10"x2.5", 2 short lines
# 6"x2.4" and 2 green container pieces 6.5"x2.4".
#
# TEN of those fifteen pieces stand at an angle in the source image (the
# medium rectangles at 60 degrees, the long lines at 27, the short lines at
# -52.5, the containers at -31.5). They are deliberately built STRAIGHT here,
# each snapped to whichever board axis its long side was already nearest, at
# its measured center and measured size (User: "begradige die schrägen
# foodprints. also rotiere sie so, dass alles wieder gerade ist. dann haben
# wir auch kein problem damit.").
#
# That decision is what keeps this map inside the engine's existing geometry.
# An Obstacle is axis-aligned by construction, and line of sight, movement
# clamping, the A* grid, the placement overlay, the AI's corner-routing and
# the renderer all read its min_x/max_x/min_y/max_y as the shape itself - a
# genuinely rotated obstacle would have to be taught to all six at once. The
# alternative that was built first, approximating each slanted piece with a
# staircase of small axis-aligned slabs, worked but cost 105 terrain features
# (36 of them sight-blocking) against map 1's 43/28, and covered ~25% more
# ground than the real piece. Straightening costs an angle and buys back both:
# exact footprints, and 35 features (20 sight-blocking) - fewer than map 1.
#
# Which pieces get walls follows the user's earlier instruction directly
# ("hat ein footprint grüne strukturen drauf, kannst du dort nach unseren
# regeln mauern platzieren"): the pieces whose footprint carries green rubble/
# structure markings are built as ruins with our own L-wall layout (ruin_l,
# same rule as map 1 - two partial doorless walls facing the board center);
# the pieces that carry only gold barricade markings and no rubble are
# barricades, i.e. a plain LIGHT footprint with no wall on it, the same
# treatment map 1 gives its own "long line"/"short line" pieces.
# ---------------------------------------------------------------------------

MAP2_WIDTH_IN = 60.0
MAP2_HEIGHT_IN = 44.0


def _mirror(x_in, y_in):
    """The same piece 180 degrees around the board center - the symmetry the
    measured layout actually has."""
    return MAP2_WIDTH_IN - x_in, MAP2_HEIGHT_IN - y_in


def _map2_terrain(state, battle_map):
    cx, cy = battle_map.center

    def straighten(x_in, y_in, long_in, short_in, measured_angle_deg):
        """A measured piece, straightened: same center, same two side lengths,
        laid along whichever board axis its long side was already nearest.
        `measured_angle_deg` is only read for that decision - it is the angle
        the piece has in the source image, kept here so the snapping stays
        checkable against the measurement instead of becoming a bare
        width/height nobody can trace back."""
        angle = ((measured_angle_deg + 90.0) % 180.0) - 90.0   # into [-90, 90)
        long_is_vertical = abs(angle) > 45.0
        width_in, height_in = (short_in, long_in) if long_is_vertical else (long_in, short_in)
        return x_in, y_in, width_in, height_in

    def extend_east_to(piece, edge_x_in):
        """A straightened piece widened eastwards until its east edge sits on
        `edge_x_in`. Its west edge, its center row and its height stay where
        they were measured - only the width changes."""
        x_in, y_in, width_in, height_in = piece
        west_in = x_in - width_in / 2
        new_width_in = edge_x_in - west_in
        return west_in + new_width_in / 2, y_in, new_width_in, height_in

    def barricade(x_in, y_in, width_in, height_in):
        """A piece with barricade markings but no rubble: LIGHT footprint
        only, nothing on it that blocks sight or movement."""
        return [Obstacle(x_in=x_in, y_in=y_in, width_in=width_in, height_in=height_in, category=LIGHT)]

    def rubble_ruin(x_in, y_in, width_in, height_in, h_wall_fraction=None, v_wall_fraction=None):
        return ruin_l(x_in=x_in, y_in=y_in, width_in=width_in, height_in=height_in,
                      facing_x=cx, facing_y=cy, h_wall_fraction=h_wall_fraction,
                      v_wall_fraction=v_wall_fraction)

    # --- North/west half: the measured positions ---
    nw_medium = straighten(9.83, 6.91, 6.0, 4.0, 60.0)        # medium rectangle, gold barricades, no rubble
    nw_container = straighten(16.46, 7.07, 6.5, 2.4, -31.5)   # green container/machine piece
    n_large = (29.80, 7.17)                                    # large rectangle, rubble + objective
    ne_longline = straighten(44.60, 9.19, 10.0, 2.5, 27.0)     # long line, barricade + small machine
    ne_shortline = straighten(52.38, 8.15, 6.0, 2.4, -52.5)    # short line, gold cross braces, no rubble
    w_large = (10.30, 18.80)                                   # large rectangle on its side, rubble + objective
    ne_medium = straighten(42.87, 18.02, 6.0, 4.0, 60.0)       # medium rectangle, rubble

    # As measured, this medium ruin stops 1.33" short of the large ruin next
    # to it, and their two sight-blocking walls stop 2.66" apart - a slot that
    # reads as closed on screen but that line of sight goes straight through
    # (User: "erweitere ... dieses geländestück sodass diese lücke geschlossen
    # wird auf beiden seiten. so kleine lücken sind immer doof für die
    # sichtlinien logik"). The piece is widened east until its footprint is
    # flush with its neighbour's west edge, and its horizontal arm is run the
    # FULL length of that edge instead of the default two thirds - widening
    # alone would not have closed anything, because l_walls() anchors the arm
    # at the corner nearest the board center and a two-thirds arm on a wider
    # footprint still stops short of the join.
    # Both halves of the board get this: the south/west half is defined below
    # as this piece's mirror, and the mirror puts the same arm on the north
    # edge, running west into the west large ruin the same way.
    ne_medium = extend_east_to(ne_medium, _mirror(*w_large)[0] - 7.0 / 2)

    state.add_terrain_area(barricade(*nw_medium))
    state.add_terrain_area(barricade(*nw_container))
    p2_home_area = state.add_terrain_area(
        ruin_l(x_in=n_large[0], y_in=n_large[1], width_in=11.5, height_in=7.0, facing_x=cx, facing_y=cy))
    state.add_objective(p2_home_area, name="P2 Home Objective")
    state.add_terrain_area(barricade(*ne_longline))
    state.add_terrain_area(barricade(*ne_shortline))
    # The two large rectangles on the flanks stand on their short edge (the
    # measurement reads them as the same 11.5"x7" piece turned 90 degrees), so
    # they're given as 7"x11.5 - already straight, nothing to snap.
    west_objective_area = state.add_terrain_area(
        ruin_l(x_in=w_large[0], y_in=w_large[1], width_in=7.0, height_in=11.5, facing_x=cx, facing_y=cy))
    state.add_objective(west_objective_area, name="Objective West")
    # v_wall_fraction=0: the two medium ruins keep only their horizontal arm
    # (User marked the vertical ones for removal). The horizontal one is
    # deliberately the survivor - it is the arm that was run out to
    # h_wall_fraction=1.0 above to close the sight-line slot against the large
    # flank ruin, so dropping the other arm leaves that fix untouched.
    state.add_terrain_area(rubble_ruin(*ne_medium, h_wall_fraction=1.0, v_wall_fraction=0.0))

    # --- Central piece: its own 12.2"x9.75" rectangle, on the board center.
    # Keeps ruin()'s all-four-sides-with-a-door layout - unlike every other
    # ruin on this map - for the same reason map 1's central ruin does: no
    # single side of it faces "the enemy".
    # Only two of its four corner "L"s are built (User marked the other two
    # for removal): the ones that survive are diagonally opposite, so the
    # piece stays 180-degree rotationally symmetric like the rest of the map.
    central_area = state.add_terrain_area(
        ruin(x_in=30.0, y_in=22.0, width_in=12.2, height_in=9.75, corners=("nw", "se")))
    state.add_objective(central_area, name="Central Objective")

    # --- South/east half: each piece is the mirror of its twin above ---
    se_medium = _mirror(nw_medium[0], nw_medium[1]) + nw_medium[2:]
    se_container = _mirror(nw_container[0], nw_container[1]) + nw_container[2:]
    s_large = _mirror(*n_large)
    sw_longline = _mirror(ne_longline[0], ne_longline[1]) + ne_longline[2:]
    sw_shortline = _mirror(ne_shortline[0], ne_shortline[1]) + ne_shortline[2:]
    e_large = _mirror(*w_large)
    sw_medium = _mirror(ne_medium[0], ne_medium[1]) + ne_medium[2:]

    state.add_terrain_area(barricade(*se_medium))
    state.add_terrain_area(barricade(*se_container))
    p1_home_area = state.add_terrain_area(
        ruin_l(x_in=s_large[0], y_in=s_large[1], width_in=11.5, height_in=7.0, facing_x=cx, facing_y=cy))
    state.add_objective(p1_home_area, name="P1 Home Objective")
    state.add_terrain_area(barricade(*sw_longline))
    state.add_terrain_area(barricade(*sw_shortline))
    east_objective_area = state.add_terrain_area(
        ruin_l(x_in=e_large[0], y_in=e_large[1], width_in=7.0, height_in=11.5, facing_x=cx, facing_y=cy))
    state.add_objective(east_objective_area, name="Objective East")
    state.add_terrain_area(rubble_ruin(*sw_medium, h_wall_fraction=1.0, v_wall_fraction=0.0))


MAP2 = BattleMap(
    key="map2",
    name="Landscape layout (60\"x44\")",
    width_in=MAP2_WIDTH_IN,
    height_in=MAP2_HEIGHT_IN,
    # Both zones run the full 60" width and are 12" deep, straight off the
    # image: the shaded bands span every pixel column of the board and are
    # exactly 240 px tall at the 20 px/inch scale the same measurement fixes,
    # which is also what the image's own "12"" labels say. Player 2 keeps the
    # top edge and Player 1 the bottom one, the same way round as map 1, so
    # nothing else in the scene has to know which map it is.
    zones=[
        ("Player 2", [(30.0, 6.0, 60.0, 12.0)]),
        ("Player 1", [(30.0, 38.0, 60.0, 12.0)]),
    ],
    terrain=_map2_terrain,
    # Deployment positions: found by the same automated overlap search the map
    # 1 comments describe (every model checked against the board edge at its
    # real base radius, against every Dense terrain feature, against every
    # other already-placed model, and each squad checked for rule 09.02
    # coherency and the 9" maximum spread), searching forward-most first
    # within the owner's own 12"-deep zone. Filled in below by that search,
    # not by eye.
    player1=Player1Deployment(
        squads=[
            [  # Breacher Team 1 (embarked in the Devilfish, with Cadre Fireblade)
                (10.80, 41.30), (12.30, 41.30), (13.80, 41.30), (15.30, 41.30), (16.80, 41.30),
                (10.80, 43.30), (12.30, 43.30), (13.80, 43.30), (15.30, 43.30), (16.80, 43.30),
            ],
            [  # Strike Team 1
                (17.80, 33.50), (19.30, 33.50), (20.80, 33.50), (22.30, 33.50), (23.80, 33.50),
                (17.80, 35.50), (19.30, 35.50), (20.80, 35.50), (22.30, 35.50), (23.80, 35.50),
            ],
            [  # Strike Team 2 - just east of the home ruin's north wall (which
               # ends at x=32.12), so the block clears it at every model's radius
                (33.00, 33.50), (34.50, 33.50), (36.00, 33.50), (37.50, 33.50), (39.00, 33.50),
                (33.00, 35.50), (34.50, 35.50), (36.00, 35.50), (37.50, 35.50), (39.00, 35.50),
            ],
            [  # Kroot Carnivores 1
                (9.00, 33.50), (10.50, 33.50), (12.00, 33.50), (13.50, 33.50), (15.00, 33.50),
                (9.00, 35.50), (10.50, 35.50), (12.00, 35.50), (13.50, 35.50), (15.00, 35.50),
            ],
            [  # Kroot Carnivores 2
                (45.00, 33.50), (46.50, 33.50), (48.00, 33.50), (49.50, 33.50), (51.00, 33.50),
                (45.00, 35.50), (46.50, 35.50), (48.00, 35.50), (49.50, 35.50), (51.00, 35.50),
            ],
            [  # Stealth Battlesuits, holding the eastern flank
                (54.00, 33.50), (56.00, 33.50), (58.00, 33.50), (54.00, 35.50), (56.00, 35.50),
            ],
            [(2.50, 35.00)],  # Ghostkeel Battlesuit, western flank
        ],
        # Rear left, in open ground well clear of the home ruin and of every
        # deployed squad, so its disembark ring (18.04) is unobstructed on
        # every facing.
        devilfish=(8.00, 41.00),
    ),
    player2=Player2Deployment(
        # On the P2 Home Objective (footprint x 24.05-35.55, y 3.67-10.67),
        # inside the part of it the ruin's own L of Dense walls leaves open -
        # the same "cheapest unit garrisons the home objective" arrangement
        # map 1 uses.
        gretchin=[
            (25.50, 7.00), (26.75, 7.00), (28.00, 7.00), (29.25, 7.00), (30.50, 7.00),
            (25.50, 5.00), (26.75, 5.00), (28.00, 5.00), (29.25, 5.00), (30.50, 5.00),
            (25.50, 3.00),  # Runtherd
        ],
        stormboyz=[
            (2.50, 10.50), (4.00, 10.50), (5.50, 10.50), (7.00, 10.50), (8.50, 10.50),
            (2.50, 8.50), (4.00, 8.50), (5.50, 8.50), (7.00, 8.50), (8.50, 8.50),
        ],
        warbikers=[
            [(47.00, 10.50), (49.60, 10.50), (52.20, 10.50)],
            [(13.00, 10.50), (15.60, 10.50), (18.20, 10.50)],
        ],
        boyz1=[
            (36.20, 10.50), (37.70, 10.50), (39.20, 10.50), (40.70, 10.50), (42.20, 10.50),
            (36.20, 8.50), (37.70, 8.50), (39.20, 8.50), (40.70, 8.50), (42.20, 8.50),
        ],
        # Both Trukks stand in open ground on either side of the home ruin
        # rather than tucked against it: a transport that starts the game with
        # a wall on one side has that many fewer facings for its passengers to
        # disembark into (18.04), which this project has already had to fix
        # once as a real bug.
        trukks=[(19.00, 5.50), (45.00, 5.50)],
        # Forward-most Player 2 unit, stopped just short of the home ruin's own
        # south wall (which starts at x=27.88) - the search would not put a
        # 1.18"-radius hull any further east at this y.
        deff_dread=(26.70, 10.50),
    ),
)


# ---------------------------------------------------------------------------
# Map 3 - 60"x44" landscape, built from the layout the user supplied as
# Sprites/Map3.png (2400x1760 px, i.e. exactly 40 px per inch).
#
# It REPLACES the old 30"x30" test board of the same key (User: "map3
# ersetzen"). What that board was for - a whole turn in seconds, and every
# awkward geometry present at once - is gone with it; see CLAUDE.md for what
# moved where.
#
# Measured, not eyeballed, and every number below is a measurement:
#
#   * The board is 60"x44": the source image's aspect ratio is exactly 15:11
#     and its deployment zones sit exactly on the half-board lines.
#   * The layout has the same 180-degree rotational symmetry map 1 and map 2
#     have. Only the north/west half is measured here; the other half is its
#     mirror through the board centre, so a single noisy measurement cannot
#     make the two halves disagree. Checked before writing this: every
#     measured piece finds its mirror within 0.1" and 1.4 degrees.
#   * FOUR of the eighteen pieces stand at an angle (37.0 and -52.5 degrees,
#     each twice). Unlike map 2, they are built AT THAT ANGLE -
#     game/terrain.py's Obstacle takes angle_deg since the rotation work, so
#     the straightening map 2 needed is no longer the price of using this
#     engine's geometry.
#   * Every footprint is ONE clean rectangle (User: "ignoriere
#     unregelmaessigkeiten wie schutt. mache saubere rechtecke draus. und alle
#     footprints sollen rechtecke sein"). The source art draws irregular
#     rubble spilling past each footprint's edge; the measurement fits the
#     rectangle to the piece and discards the spill, which is why the fitted
#     rectangle covers 93-98% of each piece's drawn pixels rather than 100%.
#     A piece is only built ROTATED when it really is a turned rectangle,
#     which is decided by how much of its minimum-area box it fills (102% for
#     a true one against 66% for a wedge) - see the central pair below.
#
# The DEPLOYMENT ZONES are the reason the shape work came first: each is a
# board QUADRANT with a 9" circle around the board centre cut out of it. That
# is not expressible as axis-aligned rectangles at all - see game/shapes.py's
# module docstring for the measurement that killed the rectangle approximation
# (a grav tank cannot be deployed anywhere in a 16-strip staircase of one).
# The 9" is measured: 355 px in BOTH zones independently, i.e. 8.88", against
# the "9"" the source image annotates - the 0.12" is the dashed line's width.
#
# Player 2 keeps the LOW-Y corner, as on both other maps, so nothing else in
# the scene has to know which map it is. The source image tints that corner
# blue and this engine draws Player 1 blue, so the rendered colours are the
# other way round from the picture; that is a palette, not a layout.
# ---------------------------------------------------------------------------

MAP3_WIDTH_IN = 60.0
MAP3_HEIGHT_IN = 44.0
# The circle bitten out of both deployment zones, centred on the board.
MAP3_CENTRE_HOLE_RADIUS_IN = 9.0


def _map3_mirror(x_in, y_in):
    """The same piece 180 degrees around the board centre - the symmetry the
    measured layout actually has."""
    return MAP3_WIDTH_IN - x_in, MAP3_HEIGHT_IN - y_in


def _map3_zone(x_side, y_side):
    """One quadrant of the board minus the centre circle, as a shape.

    `x_side`/`y_side` are +1 or -1 and pick the quadrant: +1 keeps the high
    side of that axis. The four board edges are included as half-planes so the
    shape is bounded - without them it reports no bounding box and every
    caller that samples it (the renderer's outline, the AI's candidate grid)
    would have to fall back to the whole board."""
    cx, cy = MAP3_WIDTH_IN / 2, MAP3_HEIGHT_IN / 2
    return shapes.Intersection([
        shapes.HalfPlane(x_side, 0.0, x_side * cx),
        shapes.HalfPlane(0.0, y_side, y_side * cy),
        shapes.Outside(shapes.Disc(cx, cy, MAP3_CENTRE_HOLE_RADIUS_IN)),
        shapes.HalfPlane(1.0, 0.0, 0.0),
        shapes.HalfPlane(-1.0, 0.0, -MAP3_WIDTH_IN),
        shapes.HalfPlane(0.0, 1.0, 0.0),
        shapes.HalfPlane(0.0, -1.0, -MAP3_HEIGHT_IN),
    ])


def _map3_terrain(state, battle_map):
    cx, cy = battle_map.center

    def barricade(x_in, y_in, width_in, height_in, angle_deg=0.0):
        """A piece with barricade markings and no rubble on it: a LIGHT
        footprint only, nothing that blocks sight or movement. Same reading
        map 2 uses for its own gold-braced pieces."""
        return [Obstacle(x_in=x_in, y_in=y_in, width_in=width_in, height_in=height_in,
                         category=LIGHT, angle_deg=angle_deg)]

    def rubble_ruin(x_in, y_in, width_in, height_in, angle_deg=0.0,
                    h_wall_fraction=None, v_wall_fraction=None):
        """A piece whose art carries green rubble/structure: built as a ruin
        with our own L-wall layout (two partial doorless walls facing the
        board centre), the same rule map 1 and map 2 follow. The walls turn
        with the footprint - see game/terrain.py's l_walls()."""
        return ruin_l(x_in=x_in, y_in=y_in, width_in=width_in, height_in=height_in,
                      facing_x=cx, facing_y=cy, angle_deg=angle_deg,
                      h_wall_fraction=h_wall_fraction, v_wall_fraction=v_wall_fraction)

    def both(build, x_in, y_in, *args, **kwargs):
        """The measured piece AND its mirror. Returns the two terrain areas so
        a caller can hang an objective on either."""
        mx, my = _map3_mirror(x_in, y_in)
        return (state.add_terrain_area(build(x_in, y_in, *args, **kwargs)),
                state.add_terrain_area(build(mx, my, *args, **kwargs)))

    # -- the two big ruins on the diagonal, each carrying an objective -------
    # Measured (9.59, 11.88), 11.14 x 6.92 at 37.1 degrees.
    nw_ruin, se_ruin = both(rubble_ruin, 9.59, 11.88, 11.14, 6.92, angle_deg=37.1)
    state.add_objective(nw_ruin, name="Objective Northwest")
    state.add_objective(se_ruin, name="Objective Southeast")

    # -- the two home ruins, one inside each deployment zone -----------------
    # Measured (44.10, 6.67), 11.10 x 6.95, square to the board.
    p2_home, p1_home = both(rubble_ruin, 44.10, 6.67, 11.10, 6.95)
    state.add_objective(p2_home, name="P2 Home Objective")
    state.add_objective(p1_home, name="P1 Home Objective")

    # -- the two central pieces, inside the circle both zones give up --------
    # Measured (35.87, 20.22), 7.48 x 10.85, SQUARE to the board. These are the
    # pair the 9" hole exists for: both sit in No Man's Land despite standing
    # in a quadrant that is otherwise somebody's deployment zone.
    #
    # UPRIGHT, and that is a correction the user had to point out. The art
    # draws these two as WEDGES, and fitting each its minimum-area rectangle
    # laid a long thin 11.5 x 5.75 block diagonally through the wedge at 57
    # degrees - the tightest rectangle around the shape, and not the shape
    # anyone reads it as. The two readings are told apart by FILL: a genuinely
    # rotated rectangle fills its minimum-area box (measured 102-103% here,
    # over 100% because the fit is trimmed at the 2nd/98th percentile), a wedge
    # only two thirds of it (66%). Where the fill says "wedge", the upright box
    # wins.
    east_ruin, west_ruin = both(rubble_ruin, 35.87, 20.22, 7.48, 10.85)
    state.add_objective(east_ruin, name="Objective East")
    state.add_objective(west_ruin, name="Objective West")

    # -- the rubble pieces flanking the centre line --------------------------
    both(rubble_ruin, 31.65, 9.00, 3.10, 3.70)
    both(rubble_ruin, 28.55, 9.10, 2.80, 3.90)

    # -- barricades: gold bracing, no rubble, so no walls --------------------
    both(barricade, 25.88, 6.03, 2.05, 5.65)             # tall cross-braced bar
    both(barricade, 19.84, 11.21, 5.89, 3.79, angle_deg=-52.5)
    # The long flank band. Measured as ONE 9.55 x 2.65 piece: the first pass
    # split it into three because the erosion that separates touching pieces
    # cut this one apart as well, and the halves then landed asymmetrically.
    both(barricade, 50.08, 21.38, 9.55, 2.65)
    # The green container, and the piece the first pass MISSED ENTIRELY: its
    # art has no grey ground under it, and that pass masked only grey. The
    # mask now takes green and gold as terrain in their own right.
    both(barricade, 43.90, 16.85, 2.00, 7.00)


MAP3 = BattleMap(
    key="map3",
    name="Crucible (60\"x44\", corner deployment)",
    width_in=MAP3_WIDTH_IN,
    height_in=MAP3_HEIGHT_IN,
    # Corner quadrants with the middle 9" bitten out - see _map3_zone(). The
    # first map whose zones are not rectangles at all.
    zones=[
        ("Player 2", _map3_zone(x_side=1.0, y_side=-1.0)),   # high x, low y
        ("Player 1", _map3_zone(x_side=-1.0, y_side=1.0)),   # low x, high y
    ],
    terrain=_map3_terrain,
    # No hand-placed positions: this map is only ever played through rule
    # 03.01's pre-game sequence, which deploys both armies itself.
    # --no-deployment refuses to run without them, by the guard in main().
    player1=Player1Deployment(squads=[], devilfish=(0.0, 0.0)),
    player2=Player2Deployment(gretchin=[], stormboyz=[], warbikers=[],
                              boyz1=[], trukks=[], deff_dread=[]),
    # A full-size board fields the full army, like map 1 and map 2. The old
    # 30"x30" board carried a four-units-a-side roster because it was small;
    # nothing about this one wants that.
)

MAPS = {m.key: m for m in (MAP1, MAP2, MAP3)}
DEFAULT_MAP_KEY = MAP1.key


def get(key):
    """The BattleMap for `key`. Accepts the bare number too ("2" == "map2"),
    which is what the command line ends up passing."""
    if key is None:
        key = DEFAULT_MAP_KEY
    key = str(key).strip().lower()
    if key.isdigit():
        key = "map" + key
    if key not in MAPS:
        raise KeyError("unknown map %r - known maps: %s" % (key, ", ".join(sorted(MAPS))))
    return MAPS[key]


def apply_to_config(battle_map, config_module=None):
    """Writes the map's board size into config, where the rest of the engine
    and the AI read it from. See this module's own docstring for why this is a
    write into config rather than a value passed around: call it once, at
    startup, before anything reads a board dimension."""
    if config_module is None:
        from game import config as config_module
    config_module.BOARD_WIDTH_IN = battle_map.width_in
    config_module.BOARD_HEIGHT_IN = battle_map.height_in
    return battle_map
