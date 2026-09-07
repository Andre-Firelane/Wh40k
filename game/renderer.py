import math

import pygame

from game import arena_biome, biomes, config, movement, sprites, status_effects
from game import placement_overlay
from game.placement_overlay import PlacementOverlay
from game.squad import ENGAGEMENT_RANGE_IN, strongest_model
from game.terrain import DENSE, EXPOSED, LIGHT
from game.ui.text_utils import wrap_text

RANGE_CIRCLE_COLOR = (255, 255, 255, 70)
ENGAGEMENT_WARNING_COLOR = (255, 40, 40, 70)
#: The DEATH GUARD Contagion aura (game/nurgles_gift.py). Drawn OPAQUE onto its
#: own overlay and blitted once at CONTAGION_AURA_ALPHA, rather than as
#: translucent circles like the engagement warning above - see
#: draw_contagion_aura() for why the two differ.
CONTAGION_AURA_COLOR = (60, 120, 45)
#: Measured on a real map2 frame over the sand ground rather than picked: at 34
#: the layer was invisible and at 90 it read as a colour wash over the terrain.
#: 58 was the first value that showed at all; the user then asked for fainter
#: still ("mach die deathguard aura noch ein bisschen durchsichtiger"), and 40
#: is the bottom of the band that is still visible on that same frame.
CONTAGION_AURA_ALPHA = 40
#: The range ruler (game/aura_ruler.py), drawn the same way for the same
#: reason. WHITE because the user asked for the Death Guard look without its
#: meaning - green is Nurgle's Gift and nothing else - and because white is the
#: one tint that stays neutral over all four biomes' ground.
RANGE_AURA_COLOR = (255, 255, 255)
#: Lower than the contagion aura's 40, and measured rather than guessed: white
#: carries much further than that green does. See test_aura_ruler.py, which
#: pins it against the contagion aura's own contrast on the same ground so
#: "subtil" stays a number instead of an opinion.
RANGE_AURA_ALPHA = 26
MEASURE_LINE_COLOR = (255, 255, 255)
# The line-formation drag. Its own colour because ALT can be held during a
# right-drag, so the ruler's white line and this one can be on screen together
# and must not read as one marking. Not SHOOT_TARGET_COLOR's orange either -
# that means "this unit is a legal thing to click" in eleven other places.
LINE_DRAG_COLOR = (255, 190, 60)
LINE_DRAG_WARN_COLOR = (200, 40, 40)
LINE_DRAG_LABEL_BG_COLOR = (20, 16, 8)
LINE_DRAG_WIDTH_PX = 2.0   # ON-SCREEN pixels, through _ring_width()
LINE_DRAG_CAP_IN = 0.35    # half-length of the end ticks, in board inches
MEASURE_TEXT_COLOR = (20, 20, 20)
MEASURE_TEXT_BG = (255, 255, 255)

# draw_reserve_drag_ghost()'s name label: wrap it rather than let it run off
# the window edge, and don't stretch a long name across half the board.
GHOST_LABEL_MAX_WIDTH = 260
GHOST_LABEL_MIN_WIDTH = 120
OBSTACLE_COLOR = (30, 35, 44)  # Dense (walls) - User feedback: darkened further (was (50,58,74)) for more contrast against the now-textured footprint tile below, rather than the flat color it used to sit next to
LIGHT_TERRAIN_COLOR = (92, 112, 138)  # Light (ruin floor/rubble) fallback color, only used when the relevant Sprites/*_Cover.<ext> is missing - see TERRAIN_TILE_ALPHA/Renderer._render_static_layer()
EXPOSED_TERRAIN_COLOR = (66, 92, 96)  # Exposed fallback color, same "only used if the tile texture is missing" as LIGHT_TERRAIN_COLOR above
BARRICADE_COLOR = (78, 168, 208)  # Light terrain shaped like a fence/line (see _is_barricade_shaped) fallback color, same "only used if the tile texture is missing" as above
TERRAIN_COLORS = {DENSE: OBSTACLE_COLOR, LIGHT: LIGHT_TERRAIN_COLOR, EXPOSED: EXPOSED_TERRAIN_COLOR}
BARRICADE_MAX_THICKNESS_IN = 2.75  # a Light obstacle this thin (or thinner) on its short side reads as a fence line, not a ruin floor
# Physical WIDTH of one cover tile (its height follows the art's own aspect
# ratio - see Renderer._cached_tile). One per texture rather than one shared
# value: the two are pictures of different things at different real-world
# scales, so the size that makes a ruin's flagstones read is not the size
# that makes a boulder read.
#
# Both started at the shared 3.0 (User feedback back then: shrink it so more
# copies tile at a sharper resolution - a smaller physical tile packs the
# same source resolution into fewer on-screen pixels, a downscale rather
# than a mild upscale, so less blur, at the cost of repeating more often).
# The dense one is bigger now (User: "dense cover kachel ist jetzt
# quadratisch. mach sie etwas größer auf der map"): at 3.0 its flagstones
# came out around 0.6" across, well under one infantry base, which read as
# noise rather than as a floor.
DENSE_COVER_TILE_SIZE_IN = 4.5
NORMAL_COVER_TILE_SIZE_IN = 3.0
TERRAIN_TILE_ALPHA = 200  # User feedback: "etwas transparent, damit der Kontrast etwas verringert wird" - every non-Dense terrain footprint uses one of these two cover tiles (picked per TerrainArea.has_dense_feature, see _render_static_layer()), blended at less than full opacity so the base Ground tile underneath still shows through a little
VISIBILITY_HIGHLIGHT_COLOR = (255, 255, 120)
SELECTED_MODEL_COLOR = (0, 220, 255)
# The selected UNIT, as opposed to the one model the click landed on. Same hue
# family as SELECTED_MODEL_COLOR on purpose - they mean two halves of one thing
# - but dimmer, because this one is drawn around EVERY model of the unit while
# the cyan marks only the anchor. A 20-model Boyz mob ringed in full cyan reads
# as an alarm rather than a selection.
SELECTION_OUTLINE_COLOR = (0, 140, 175)
SELECTION_LABEL_BG_COLOR = (10, 30, 36)
# Both in ON-SCREEN pixels, converted through _ring_width()/_ring_bump() - see
# those. The old raw values (bump 6, width 3) landed at roughly 0.8 and 1.2
# actual screen pixels at default zoom, i.e. a ring nobody ever saw sitting
# essentially on top of the base rim it was supposed to clear. Same defect and
# same fix as the deployment-zone markings.
SELECTION_ANCHOR_BUMP_PX = 3.0
SELECTION_ANCHOR_WIDTH_PX = 2.5
SELECTION_OUTLINE_BUMP_PX = 1.5
SELECTION_OUTLINE_WIDTH_PX = 2.0
SHOOT_TARGET_COLOR = (255, 120, 0)
COHERENCY_REMOVAL_COLOR = (200, 20, 20)
# On-screen pixels, same treatment as the SELECTION_* pair above. Previously raw
# 5 / 3, i.e. about 1.7 / 1.0 real screen pixels at default zoom - an alarm the
# player is required to act on, drawn thinner than the base rim beneath it.
COHERENCY_REMOVAL_BUMP_PX = 2.0
COHERENCY_REMOVAL_WIDTH_PX = 2.5
DAMAGE_CHOICE_COLOR = (255, 210, 0)
# The models a PARTIAL placement is putting back - rule 01.02.03's model
# return (Reanimation Protocols, Grot Orderly, Word of the Phoenix, ...). User:
# "Widerbeleben - ich kann nicht erkennen, welche einheiten gerade
# zurueckgekommen sind, um sie zu verschieben. bitte hervorheben."
#
# The problem was structural, not a missing colour: a return drops one or two
# models into a unit that is ALREADY STANDING, and the only board marking was
# draw_placement_identity()'s outline around the WHOLE unit - which says
# "this unit is the subject" and is exactly as true of the twenty survivors
# that must not be touched. Nothing said which two bases had just appeared.
#
# WHITE, and a DOUBLE ring. White because every other board marking already
# owns a hue - cyan selection, yellow damage choice, orange shoot target, red
# coherency/enemy, green own army, violet assigning - so a sixth hue would be
# one more thing to learn, while white belongs to none of them and reads on
# every biome's floor. The second ring because a single one differs from the
# selection outline only in colour, and this has to be findable at a glance in
# a crowded blob, which is the whole complaint.
RETURNING_MODEL_COLOR = (255, 255, 255)
RETURNING_MODEL_BUMP_PX = 3.0        # on-screen px, through _ring_bump() - see draw_squad_outline
RETURNING_MODEL_GAP_PX = 3.5         # between the two rings
RETURNING_MODEL_WIDTH_PX = 2.5
ASSIGNING_MODEL_COLOR = (190, 60, 230)
# GREEN, back where it started (User: "ändere die spielerfarbe von spieler 1
# wieder zu grün. blau kann man schlecht erkennen auf blauem grund"). The
# earlier switch to blue (60, 120, 240) was this user's own call and is
# reversed here, because the arena biome - which is now the DEFAULT board -
# arrived AFTER it and paints the floor's guide grid in blue.
#
# MEASURED, and it is the coarse mean-colour proxy's documented limit in
# textbook form: against the arena FLOOR the blue rim scores 115.4 and this
# green only 75.4, so the proxy calls BLUE the better of the two - which is
# why test_arena_biome.py's rim checks stayed green through a rim nobody could
# find. Against the arena's GRID LINE, which is what a rim actually sits among
# out there, blue is 21.7 away with an IDENTICAL red channel (60 vs 60) while
# green is 71.7. Same hue as the lines it lies on: that is what "blau auf
# blauem Grund" means, and no floor-versus-rim number can see it.
#
# 75.4 on that floor is exactly what ENEMY_ARMY_COLOR scores there, a rim
# already accepted as readable. And green sits FURTHER from
# SELECTED_MODEL_COLOR's cyan (85.0) than the blue it replaces did (58.3) -
# that cyan is drawn as a thicker ring 6 px OUTSIDE this rim (see
# draw_selected_model), and keeping clear of it was the old comment's whole
# reason for picking blue.
OWN_ARMY_COLOR = (40, 200, 60)
ENEMY_ARMY_COLOR = (220, 40, 40)
# CONSTANT PER PLAYER, never per focus (User: "Die Farben der Spieler sollen
# nicht mehr wechseln, je nachdem wo der Fokus ist. Sie sollen konstant
# bleiben. Spieler 1 - gruen, Spieler 2 - rot").
#
# The rims used to be keyed on turn_tracker.active_player, so the two armies
# SWAPPED colours whenever it moved. That is not a rare event: active_player is
# documented in game/turn.py as a transient "whose decision is this right now"
# flag - it flips for every defender save roll and every reactive stratagem,
# and only turn_owner tracks whose turn it is. So the whole board changed
# colour mid-activation, twice per shooting attack, and the one thing a rim is
# for - telling the two armies apart at a glance - was the thing it stopped
# doing.
#
# Keyed by OWNER instead, exactly like DEPLOYMENT_ZONE_LINE_COLORS below, which
# has always done it this way and is the same statement in the same two hues:
# green is yours, red is theirs, wherever it is drawn and whatever is happening.
# The zone lines and the rims now agree at all times rather than only on the
# frames where the focus happened to be on Player 1.
TOKEN_TEAM_COLORS = {
    "Player 1": OWN_ARMY_COLOR,
    "Player 2": ENEMY_ARMY_COLOR,
}
UNUSUAL_LOADOUT_TINT = 55  # added to each RGB channel for models with an off-squad weapon loadout (Long-quill etc.) - NOT used for squad_leader models anymore, see SQUAD_LEADER_RING_COLOR
# User report (screenshot: 3 identical-looking Battlesuits, leader
# indistinguishable): UNUSUAL_LOADOUT_TINT's +55-per-channel brighten was
# too subtle to read at a glance, especially against a team colour that
# already runs one channel near its ceiling, so tinting only ever nudged
# the other two. A squad_leader model's ring is now a fixed,
# team-color-independent gold instead of a tinted variant of it - same
# "gold = important" language already used for panel headers
# (config.PANEL_HEADER_COLOR) - so it reads the same regardless of which
# side's colors it's sitting on top of. Since the fill was removed the ring
# is ALL there is to a base, which only makes this matter more.
SQUAD_LEADER_RING_COLOR = (255, 215, 0)
SQUAD_LEADER_BORDER_WIDTH = 2  # the outer ring for a squad_leader model: thicker than TOKEN_BORDER_WIDTH, on top of the distinct color, for extra visibility. Same on-screen-pixel units, same _ring_width() conversion.
MODEL_LABEL_COLOR = (235, 245, 255)  # light text. It used to sit on the dark token fill; on-board bases have no fill anymore (see _draw_tokens), so it now reads against the ground itself - which on the two live factions affects exactly one model, the Painboy, the only one of 152 with no art of its own. The label is still drawn on the dark fill in the embarked-passenger icon below.
TOKEN_FILL_DARKEN = 0.16  # the team color darkened to this fraction. Only _draw_embarked_icon()'s art-less fallback badge fills a disc with it now - an on-board model base is a ring with nothing inside it (see _draw_tokens).
TOKEN_BORDER_WIDTH = 1  # the OUTER, team-colored half of a base's rim, in on-screen pixels - Renderer._ring_width() scales it up to the board's own render resolution
# User report: "der ring hat jetzt zu wenig kontrast auf hellen boden. kannst
# du ihn 2 teilig machen? ein farbiger äußerer ring und einen dunklen inneren
# ring? beide aber dünn". With the fill gone, a mid-bright red or blue rim
# sits directly on desert sand, which is bright enough that neither team
# color separates from it. A dark line immediately inside the colored one
# gives the rim an edge to read against on ANY floor, without a fill and
# without thickening the colored ring itself.
TOKEN_INNER_RING_WIDTH = 1  # the inner, dark half, same on-screen units as TOKEN_BORDER_WIDTH - both deliberately thin ("beide aber dünn")
TOKEN_INNER_RING_COLOR = (16, 18, 22)  # near-black, a shade under config.BACKGROUND_COLOR. Deliberately NOT a darkened team color: the point is a constant dark reference next to a rim whose color varies, and gold/red/blue all darken to something different.
STATUS_LABEL_TEXT_COLOR = (255, 255, 255)
STATUS_LABEL_COLORS = {
    status_effects.BATTLE_SHOCKED: (200, 40, 40),
    status_effects.HIDDEN: (80, 100, 210),
    status_effects.MARKED: (230, 130, 20),
    # The three Aeldari marks. Deliberately three shades of one family rather
    # than three unrelated colours: they all mean "friendly AELDARI attacks
    # against this unit are better", they stack on the same unit, and telling
    # them apart is the 2-letter label's job, not the colour's.
    status_effects.GUIDED: (150, 90, 200),
    status_effects.DOOMED: (110, 60, 170),
    status_effects.WEBBED: (80, 40, 130),
}
STATUS_LABEL_ALPHA = 170  # semi-transparent - User-Report + screenshot: a dense cluster of small-based models (e.g. 10 Kroot Carnivores shoulder to shoulder) turned into a wall of opaque "HIDDEN" pills that buried the models themselves
# User request ("ich hätte an mehrwundigen modellen gerne ein badge, das
# anzeigt wenn ein modell schon schaden erlitten hat, Beispiel am
# devilfish 7/13"): a multi-wound model loses wounds completely
# invisibly - a Devilfish on 7 of 13 looked exactly like an untouched
# one, and the only way to find out was the Ctrl+hover datacard. Shown
# ONLY on a model that has actually taken damage, which is also why this
# can't turn into the "wall of pills" STATUS_LABEL_ALPHA had to be
# lowered for: a 1-wound model can never be damaged-but-alive (anything
# that wounds it removes it), and damage within a unit isn't spread
# around - it piles onto one model until that model dies - so in
# practice a unit shows at most one badge, on whichever model is
# currently soaking the hits.
WOUND_BADGE_TEXT_COLOR = (255, 255, 255)
WOUND_BADGE_ALPHA = 215  # more opaque than STATUS_LABEL_ALPHA: this is a number that has to be READ, not just recognised by color, and a half-transparent "7/13" over a sprite is guesswork
WOUND_BADGE_DAMAGED_COLOR = (200, 130, 20)  # amber: damaged, but still above half its wounds
WOUND_BADGE_CRITICAL_COLOR = (200, 40, 40)  # red: at or below half - same "this is bad" red as STATUS_LABEL_COLORS[BATTLE_SHOCKED]
WOUND_BADGE_CRITICAL_FRACTION = 0.5
# User request ("wenn das stärkste modell im transporter permanent
# angezeigt werden würde, wüsste man immer, was in den transportern drin
# ist"): rule 18.02 pulls an embarked squad's models off the board
# entirely, so there was previously no way to tell what a TRANSPORT was
# carrying without opening its passengers' Ctrl+hover datacard - a small
# icon of each embarked squad's strongest model (game.squad.strongest_model)
# is drawn centered on its TRANSPORT at all times instead. Deliberately
# distinct from SetupController's placement-time model stack (the "a model
# appears on the transport that I can then drag out" the user was
# contrasting this with) - that one only exists mid-Disembark-Move, this one
# is always on.
#
# User feedback (screenshot: the icon dwarfed the Trukk it sat on): drawn at
# EMBARKED_ICON_SCALE of the TRANSPORT's own on-screen size at first - sized
# that way instead of at the model's actual on-battlefield size because a
# model's base is a good deal smaller than most transports, and the first
# version wanted it legible. That reasoning was backwards: the model's real
# battlefield radius (board.in_to_px_len(model.radius_in), same conversion
# every on-board token already uses) IS the size it reads at everywhere else
# in the game, so drawing it any other size here is what actually looked
# wrong - and centered ON the transport's own disc (not floating above it)
# is where a model riding inside one would actually be.
#
# User feedback: no disc/ring underneath, just the sprite itself - see
# _draw_embarked_icon's own docstring for the one exception (a datasheet
# with no art at all still needs *something* to look at).
EMBARKED_ICON_GAP_PX = 3  # horizontal spacing between icons when a TRANSPORT carries more than one embarked squad
EMBARKED_COUNT_BADGE_COLOR = (35, 35, 40)
EMBARKED_COUNT_TEXT_COLOR = (255, 255, 255)
EMBARKED_COUNT_ALPHA = 230
OBJECTIVE_NEUTRAL_COLOR = (170, 170, 170)
OBJECTIVE_COLORS = {
    "Player 1": (70, 140, 230),
    "Player 2": (220, 60, 60),
}
# Death Trap's operation markers (game/primary_missions.py). A hazard amber
# that is neither of OBJECTIVE_COLORS' two player identities and not
# SECURED_BADGE_COLOR's gold: a trapped area is not owned ground and not a
# secured objective, and reusing either colour would say it was.
TRAPPED_AREA_COLOR = (235, 130, 30)
TRAPPED_LABEL_TEXT_COLOR = (20, 20, 20)
TRAPPED_AREA_WIDTH_PX = 3   # ON-SCREEN pixels: goes through _ring_width()
OBJECTIVE_LABEL_BG_COLOR = (20, 20, 20)
SECURED_BADGE_COLOR = (255, 210, 0)
SECURED_BADGE_TEXT_COLOR = (20, 20, 20)
ATTACK_ARROW_COLOR = (220, 30, 30)
ATTACK_ARROW_WIDTH = 4
ATTACK_ARROWHEAD_LENGTH = 18
ATTACK_ARROWHEAD_WIDTH = 14
ATTACK_ARROW_TIP_GAP = 14  # pull the tip back so it doesn't sit on the target's highlight ring
ATTACK_LABEL_COLOR = (255, 255, 255)
ATTACK_LABEL_BG = (150, 20, 20)
# Placement overlay colours/resolution now live with the overlay itself,
# game/placement_overlay.py.

# Board guides (Später-Liste: "dunkler Hintergrund mit subtilen optischen
# Hilfslinien") - all subtle/low-alpha so they read as reference lines, not
# UI elements competing with terrain/tokens.
BOARD_QUARTER_LINE_COLOR = (255, 255, 255, 35)
BOARD_QUARTER_DASH_IN = 0.8
CENTER_CIRCLE_RADIUS_IN = 6.0
CENTER_CIRCLE_COLOR = (255, 255, 255, 60)
# GREEN for the player, RED for the enemy (User: "gegener: rot / spieler:
# gruen"). Player 1 was a blue close to OWN_ARMY_COLOR; green is both the
# stronger "this is yours" signal and no longer a second blue on a board whose
# arena biome is already blue throughout.
#
# BOTH SIDES NOW COINCIDE WITH THE MODEL RIMS AGAIN, and that is recorded
# rather than quietly fixed: this comment used to claim the player's outline
# was deliberately NOT its base colour, which stopped being true the moment
# OWN_ARMY_COLOR went back to green (see there). Both user decisions asked for
# green on the player's side, so the two agreeing is what was asked for twice,
# not a collision - and "green is yours, red is theirs" now says the same thing
# in both places. The two greens are still different shades (rim (40, 200, 60)
# against this lighter (80, 225, 115), 40 apart on the mean-channel proxy),
# and they are never adjacent anyway: one is a ring on a model, the other a
# line along a zone boundary.
#
# Keyed by OWNER, which already encodes "Player 1 is the human" - the same
# assumption the table has always made. The renderer has no other notion of
# who is playing.
DEPLOYMENT_ZONE_LINE_COLORS = {
    "Player 1": (80, 225, 115, 200),
    "Player 2": (235, 80, 80, 200),
}
DEPLOYMENT_ZONE_FALLBACK_COLOR = (170, 170, 170, 200)
# BOTH WIDTHS ARE IN ON-SCREEN PIXELS and go through Renderer._ring_width(),
# which is a FIX and not just a retune. They used to be passed to
# pygame.draw.line() raw, on a surface main.py renders at several times the
# on-screen resolution - the exact defect that produced TOKEN_INNER_RING_WIDTH,
# and the reason _ring_width() exists at all.
#
# MEASURED before the change, at default zoom: the 2-pixel outline landed on
# 0.70 of a screen pixel on map2 at 1920x1080 and 0.37 on map1, and the 5-pixel
# board-edge highlight on 1.74 and 0.94. So "make the markings thicker" (User)
# is mostly a matter of drawing them at the width they already claimed - the
# numbers below are then raised on top of that.
#
# THEN TRIMMED BACK (User: "die aufstellungszonen linien sind jetzt sehr gut
# erkennbar, aber mach sie bitte etwas duenner. die linien sind jetzt sehr
# dick"). The FIX stays and is what bought the visibility; what comes off is
# the bump that was added on top of it, so these land back on roughly the
# widths the constants always claimed. Measured on screen at 1920x1080/map2:
# boundary 3.48 -> 2.78 px, edge highlight 8.35 -> 5.92 px, with the fatter of
# the two cut hardest because it is the one that dominates the picture.
#
# A FRACTION rather than 2 for the boundary, for two measured reasons.
# _ring_width() takes a float, and 2.0 would land EXACTLY on a model's base rim
# (both 2.44 px on map2 at 1920x1080), giving up the one bar this markings work
# has: that a zone line is thicker than the rim the user already accepts as
# readable. And not 2.5 either - round() breaks a .5 tie to EVEN, so 2.5 draws
# 2 px at render scale 1 and 8 at scale 3, a jump of 4x where the constant
# promises 3x. 2.4 is off the tie in the thinner direction.
DEPLOYMENT_ZONE_LINE_WIDTH = 2.4
# The highlight along a zone's own board edge ("Zuordnung der Spielfeldkanten")
# is drawn at the SAME width as the boundary. User: "bei den Aufstellungszonen
# gibt es an den spielfeldrändern sehr dicke Linien. können die genau so dick
# sein wie die innenliegenden Linien?"
#
# It used to be the thicker of the two, on the reasoning that "whose edge is
# this" is a coarser statement than "where does the zone stop". Two widths for
# what a player reads as one set of markings turned out to be the louder
# reading, and 5 against 2.4 is more than twice - on a board edge, where the
# line is already the most prominent thing on the picture because nothing
# crosses it.
#
# DERIVED, not written down twice: the point of the request is that the two are
# EQUAL, and equality between two literals is exactly what drifts the next time
# either is tuned. The name stays because the two are still different ROLES,
# and a future change may want to separate them again - it just has to say so.
BOARD_EDGE_LINE_WIDTH = DEPLOYMENT_ZONE_LINE_WIDTH
# Grid step for tracing a zone's outline from its signed distance. Only ever
# paid on the CACHED static layer (once per scene), so this buys accuracy
# cheaply: 0.25" over a 60x44 board is ~42k evaluations per zone.
ZONE_OUTLINE_STEP_IN = 0.25
# A zone whose boundary IS a board edge sits at distance 0 there; this decides
# "touching" without letting floating point cast the vote.
ZONE_EDGE_TOUCH_TOLERANCE_IN = 1e-6
# A board edge counts as a zone's OWN edge when its outward normal points the
# same way the zone lies from the board centre. Strictly positive, so the two
# edges a full-width band merely runs into sideways (dot product exactly 0)
# drop out - which is what keeps the shipped maps drawing as they always did.
ZONE_OWN_EDGE_MIN_DOT = 1e-6




BOARD_EDGE_NAMES = ("north", "south", "west", "east")


def own_board_edges(board, zone):
    """Which board edges this zone sits BEHIND - its owner's own edges, as
    ((x0,y0),(x1,y1)) pairs in inches.

    Derived, not hardcoded: an edge qualifies when its outward normal points
    the same way as "from the board centre toward this zone". That is the
    generalisation of the test this replaces, which asked only whether a
    rectangle's north or south side lay on a board edge and so could name only
    a horizontal one.

    It is behaviour-identical on the three shipped maps, and the strict > is
    what makes it so: their zones band the full width, so they really do touch
    the west and east edges too, but those normals are exactly PERPENDICULAR
    to the zone direction (dot product 0) and drop out. A corner zone, whose
    direction is diagonal, correctly keeps both of the adjacent edges it sits
    behind.

    A pure function rather than part of the drawing, because "which edges are
    this zone's own" is the part with a right answer - the drawing around it
    only paints what this returns."""
    centroid = zone.centroid(board_box=(0.0, 0.0, board.width_in, board.height_in))
    if centroid is None:
        return []
    away_x = centroid[0] - board.width_in / 2
    away_y = centroid[1] - board.height_in / 2
    length = math.hypot(away_x, away_y)
    if length < 1e-9:
        return []
    away_x, away_y = away_x / length, away_y / length
    candidates = (
        (((0.0, 0.0), (board.width_in, 0.0)), (0.0, -1.0)),                          # north
        (((0.0, board.height_in), (board.width_in, board.height_in)), (0.0, 1.0)),   # south
        (((0.0, 0.0), (0.0, board.height_in)), (-1.0, 0.0)),                         # west
        (((board.width_in, 0.0), (board.width_in, board.height_in)), (1.0, 0.0)),    # east
    )
    return [edge for edge, (nx, ny) in candidates
            if nx * away_x + ny * away_y > ZONE_OWN_EDGE_MIN_DOT]



def obstacle_points_px(board, obstacle):
    """An obstacle's four corners in screen pixels. The one place terrain is
    turned into something drawable, so a rotated piece is drawn as the shape
    the rules actually test rather than as its bounding box."""
    return [tuple(round(v) for v in board.to_px(x_in, y_in))
            for x_in, y_in in obstacle.corners()]


def _points_bounds(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return pygame.Rect(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))



OBJECTIVE_OUTLINE_INFLATE_PX = 5   # was rect.inflate(10, 10), i.e. 5 px a side


def objective_outline_points(board, terrain_area, inflate_px=OBJECTIVE_OUTLINE_INFLATE_PX):
    """The outline of an objective's terrain area, in screen pixels.

    Built from the FEATURES' own corners rather than from the area's
    axis-aligned bounding box, so it follows a rotated footprint instead of
    boxing it in - rule 14.02 measures control with
    TerrainArea.overlaps_model(), which is the rotated rectangle, and an
    outline that disagrees with it draws a promise the rules do not keep.

    Each feature is grown by `inflate_px` on every side IN ITS OWN FRAME (so
    the margin stays even around a turned piece) and the hull of all the grown
    corners is taken, which is what makes a multi-feature area - a ruin's
    floor plus its walls - come out as one outline."""
    per_px = board.in_to_px_len(1.0)
    inflate_in = inflate_px / per_px if per_px else 0.0
    points = []
    for feature in terrain_area.features:
        half_w = feature.width_in / 2 + inflate_in
        half_h = feature.height_in / 2 + inflate_in
        angle = math.radians(getattr(feature, "angle_deg", 0.0))
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        for lx, ly in ((-half_w, -half_h), (half_w, -half_h), (half_w, half_h), (-half_w, half_h)):
            # SNAPPED to a millionth of an inch before hulling. A ruin's walls
            # are inset by half their thickness so their outer edge is exactly
            # the footprint's, but the two are reached by different arithmetic
            # and land 7e-15 apart. That is enough to order two points that
            # should tie the other way round, and the hull then starts at a
            # wall corner and drops a real one - a rectangle came out as a
            # pentagon. A millionth of an inch is far below a pixel at any
            # zoom, so this cannot move an outline anyone can see.
            points.append((round(feature.x_in + lx * cos_a - ly * sin_a, 6),
                           round(feature.y_in + lx * sin_a + ly * cos_a, 6)))
    return [tuple(round(v) for v in board.to_px(x, y)) for x, y in _convex_hull(points)]


def _convex_hull(points):
    """Monotone chain. Returns the hull in order; a degenerate input (all
    points collinear or identical) comes back as-is so the caller still has
    something to draw."""
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts

    # The epsilon is not decoration: a ruin's walls are inset by half their
    # thickness so their outer edge lies EXACTLY on the footprint's, and after
    # the same inflation those corners are collinear with it. Tested against a
    # bare 0 the cross product comes out at ~1e-15 rather than 0 and the wall
    # corners survive as vertices, which turns a rectangle into a six-sided
    # outline that is a rectangle everywhere except in the vertex list.
    eps = 1e-9

    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2 and (out[-1][0] - out[-2][0]) * (p[1] - out[-2][1])                     - (out[-1][1] - out[-2][1]) * (p[0] - out[-2][0]) <= eps:
                out.pop()
            out.append(p)
        return out
    hull = half(pts)[:-1] + half(pts[::-1])[:-1]
    return hull or pts


def _crossing(v0, v1):
    """Where between two samples the signed distance changes sign, as a
    fraction of the gap - linear interpolation, so a traced boundary is not
    quantised to the sampling grid."""
    span = v0 - v1
    if abs(span) < 1e-12:
        return 0.5
    return max(0.0, min(1.0, v0 / span))


def _draw_inset_edge_line(overlay, board, start_in, end_in, color, width):
    """The board-edge highlight for one run along one edge, nudged inward so
    the full line width stays on the board instead of half of it falling off
    the surface.

    `width` is passed in rather than read from BOARD_EDGE_LINE_WIDTH here: that
    constant is in ON-SCREEN pixels and only Renderer knows the board's render
    scale (see Renderer._ring_width). Taking it as an argument is also what
    keeps the inset below agreeing with the width actually drawn - computing
    the two from different numbers is how half a line ends up off the surface."""
    inset = width / 2
    ax, ay = board.to_px(*start_in)
    bx, by = board.to_px(*end_in)
    if abs(ay - by) < 1e-6:                       # horizontal edge
        ay = by = ay + (inset if ay < board.height_px / 2 else -inset)
    elif abs(ax - bx) < 1e-6:                     # vertical edge
        ax = bx = ax + (inset if ax < board.width_px / 2 else -inset)
    pygame.draw.line(overlay, color, (round(ax), round(ay)), (round(bx), round(by)),
                     width=width)


class Renderer:
    def __init__(self, render_scale=1.0):
        # Später-Liste (Kamera-Scrolling/Viewport, higher render resolution):
        # almost everything this class draws lands on board_surface, which
        # main.py now renders at render_scale times the on-screen
        # resolution (derived per map/screen - see
        # game/render_resolution.py) - circle RADII already scale correctly
        # since they're computed via board.in_to_px_len(), but a font's
        # pixel size is a fixed constant, not something board.py's
        # inch<->pixel math touches. Left unscaled, board-drawn text would
        # render render_scale times too SMALL once that whole surface gets
        # scaled back down to fit the screen at the default zoom (User
        # report: "die font size ist jetzt zu klein") - scaled up here
        # instead, so it reads at the same apparent on-screen size as
        # before any of this existed.
        #
        # A hardcoded LINE WIDTH has exactly the same problem, which this
        # comment used to claim it didn't: measured on map2 at a 1300x900
        # board area, the derived resolution is 54.2 ppi (render_scale
        # 3.01) and the camera shows it at 0.400, so a model base's
        # 2-pixel rim was landing on 0.80 of a screen pixel and getting
        # blended away into the floor - which is the report behind
        # TOKEN_INNER_RING_WIDTH. _ring_width() below is the same
        # correction the fonts get.
        self.render_scale = render_scale
        self.font = pygame.font.SysFont(config.FONT_NAME, round(config.FONT_SIZE * render_scale))
        self.label_font = pygame.font.SysFont(config.FONT_NAME, round(max(10, config.FONT_SIZE - 5) * render_scale), bold=True)
        # Deliberately smaller than label_font (used for the 2-letter model-
        # name abbreviation) - see STATUS_LABEL_ALPHA's note on why.
        self.status_label_font = pygame.font.SysFont(config.FONT_NAME, round(max(7, config.FONT_SIZE - 9) * render_scale), bold=True)
        # The one exception: draw_reserve_drag_ghost() draws directly onto
        # the real screen (a mouse-following ghost outside board_surface
        # entirely), which is NOT rendered at render_scale - it needs the
        # plain, unscaled size.
        self.screen_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE)
        # Später-Liste (Kamera-Scrolling/Viewport, higher render resolution):
        # background + deployment-zone guides + terrain never change once
        # the scene is built (nothing in this engine adds/removes/moves
        # terrain or deployment zones mid-battle) - only the tokens do, every
        # frame. Redrawing the static part from scratch every frame (a full
        # surface.fill() plus two separate SRCALPHA overlay allocations/
        # blits, one per obstacle each) turned out to be the dominant cost of
        # draw() by far, and one that scales with board AREA - a real problem
        # once main.py started rendering the board at several times its
        # on-screen resolution so Camera zoom wouldn't look blocky (see
        # game/render_resolution.py): measured ~45ms/frame for just this
        # static part at 4x supersampling, on its own already blowing the
        # ~16.6ms/frame budget for 60fps. Cached here instead - rendered once
        # into its own persistent Surface, then just blitted (cheap, no
        # per-obstacle work) every frame; _cached_static_layer() only
        # re-renders it if the board/obstacles/zones actually changed.
        # main.py additionally clips that blit to the camera's visible rect,
        # so its cost follows the SCREEN area, not the board's pixel count -
        # which is what makes the derived (much higher) resolution affordable.
        self._static_cache_key = None
        self._static_cache_surface = None
        # Same reasoning as the static-layer cache above, for the handful of
        # other per-frame SRCALPHA overlays (token glow, move-range circles,
        # forbidden-engagement-range circles, the placement grid) - their
        # actual CONTENT does need to be redrawn every frame (tokens move,
        # ranges change), but the Surface object itself doesn't need to be
        # reallocated every time: profiling showed pygame.Surface(...,
        # SRCALPHA) construction, not the drawing onto it, was by far the
        # most expensive part of each of these at a higher render resolution
        # (e.g. ~8ms just to allocate a 3168x4320 SRCALPHA surface, vs
        # ~1.7ms to clear one already that size) - see _reusable_overlay()
        # below.
        self._overlay_cache = {}
        self._ground_tile_cache = {}  # (path, tile_px) -> pygame.Surface - the two cover textures' tiles (the ground itself is no longer tiled, see _draw_ground), see _cached_tile()
        # The placement (Set Up / Ingress / Disembark) legality overlay goes a
        # step further than _reusable_overlay: its CONTENT doesn't change
        # either while a unit is being placed, so both the legality mask and
        # the rendered Surface are kept across frames - see
        # game/placement_overlay.py.
        self._placement_overlay = PlacementOverlay()
        # The coherency band is the same machinery with the palette inverted:
        # it paints the region the base must REACH, not the one it must avoid.
        self._coherency_overlay = PlacementOverlay(
            valid_color=placement_overlay.BAND_COLOR,
            invalid_color=placement_overlay.BAND_OUTSIDE_COLOR,
            edge_color=placement_overlay.BAND_EDGE_COLOR,
        )

    def _ring_width(self, on_screen_px):
        """A stroke width given in ON-SCREEN pixels, converted to the board
        surface's own (supersampled) render resolution - the same
        correction the fonts get in __init__, and for the same reason. At
        least 1, so a thin rim never rounds away to nothing."""
        return max(1, round(on_screen_px * self.render_scale))

    def _ring_bump(self, on_screen_px):
        """How far OUTSIDE a model's base rim to draw a highlight ring, given
        in on-screen pixels. Same conversion as _ring_width() and needed for
        the same reason - a gap quoted in raw board-surface pixels shrinks by
        render_scale x camera zoom before anyone sees it, so the ring ends up
        sitting on the rim instead of clearing it.

        Its own method rather than reusing _ring_width(): that one floors at 1
        because a zero-width stroke draws nothing, whereas a zero bump is a
        perfectly good "ring exactly on the rim". Two different questions, and
        one shared name would lie about one of them."""
        return round(on_screen_px * self.render_scale)

    def _reusable_overlay(self, cache_key, size):
        """A persistent SRCALPHA Surface for the given cache_key/size,
        cleared to fully transparent instead of being reallocated when it's
        already the right size (only reallocated on the first call, or if
        `size` changed - e.g. the board's own render resolution changed)."""
        surf = self._overlay_cache.get(cache_key)
        if surf is None or surf.get_size() != size:
            surf = pygame.Surface(size, pygame.SRCALPHA)
            self._overlay_cache[cache_key] = surf
        else:
            surf.fill((0, 0, 0, 0))
        return surf

    def draw(self, surface, board, tokens, obstacles=(), deployment_zones=(), blood_decals=(), terrain_areas=()):
        surface.blit(self._cached_static_layer(board, obstacles, terrain_areas, deployment_zones), (0, 0))
        self.draw_blood_decals(surface, board, blood_decals)
        self._draw_tokens(surface, board, tokens)

    def draw_blood_decals(self, surface, board, decals):
        """Später-Liste (Sprites): Sprites/Blood.<ext>, drawn at
        each (x_in, y_in, radius_in) in GameState.blood_decals - one per
        model death (see GameState.add_blood_decal), falling back to
        drawing nothing if the art isn't present, same "missing art is
        fine" convention as every other sprite lookup. Drawn after the
        static terrain layer but before tokens, so it reads as a stain on
        the ground itself - a model that later stands on top of one
        partially covers it, same as any other floor detail - rather than
        a UI overlay sitting above everything."""
        path = sprites.blood_decal_path()
        if path is None:
            return
        # One size for every stain (sprites.BLOOD_DECAL_DIAMETER_IN), not one
        # per dead model's base - see that constant for the user report.
        decal_surf = sprites.blood_decal_surface(
            path, board.in_to_px_len(sprites.BLOOD_DECAL_DIAMETER_IN),
        )
        for x_in, y_in in decals:
            px, py = board.to_px(x_in, y_in)
            rect = decal_surf.get_rect(center=(round(px), round(py)))
            surface.blit(decal_surf, rect)

    def _cached_static_layer(self, board, obstacles, terrain_areas, deployment_zones):
        # Identity + length, not a full content comparison - cheap (O(1),
        # not O(obstacles)) and correct in practice, since main.py always
        # passes the SAME state.obstacles/state.terrain_areas/deployment_zones
        # list objects every frame, all fully built during scene setup and
        # never mutated afterward (same "identity is enough" reasoning as
        # main.py's own shoot_targets_cache/visibility_cache keys).
        key = (
            id(board), board.width_px, board.height_px,
            id(obstacles), len(obstacles), id(terrain_areas), len(terrain_areas),
            id(deployment_zones), len(deployment_zones),
        )
        if key != self._static_cache_key:
            self._static_cache_surface = self._render_static_layer(board, obstacles, terrain_areas, deployment_zones)
            self._static_cache_key = key
        return self._static_cache_surface

    def _render_static_layer(self, board, obstacles, terrain_areas, deployment_zones):
        surface = pygame.Surface((board.width_px, board.height_px))
        self._draw_ground(surface, board)
        self._draw_deployment_zones(surface, board, deployment_zones)

        dense_cover_tile = self._cover_tile(biomes.DENSE_COVER, board)
        normal_cover_tile = self._cover_tile(biomes.LIGHT_COVER, board)

        # Two passes, in this order, so a ruin's Dense walls render as solid
        # blocks sitting cleanly on top of its Exposed/Light footprint
        # (e.g. rubble/floor) rather than the floor's translucent tint
        # washing back out over the walls drawn beneath it.
        terrain_overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for area in terrain_areas:
            # User: the dense-cover texture for a footprint that has a wall
            # (Dense feature) standing on it (a ruin's floor), the light-cover
            # one (normal_cover_texture_path, see game/sprites.py for the
            # name) for a
            # footprint with no wall at all (a standalone barricade/crater) -
            # picked once per TerrainArea, not per feature, since that's the
            # whole "terrain area" a wall does or doesn't belong to.
            cover_tile = (dense_cover_tile if area.has_dense_feature
                          else normal_cover_tile)
            for obstacle in area.features:
                if obstacle.category == DENSE:
                    continue
                points = obstacle_points_px(board, obstacle)
                rect = _points_bounds(points)
                if cover_tile is not None:
                    # Drawn straight onto `surface`, at TERRAIN_TILE_ALPHA
                    # rather than fully opaque, so the base Ground tile
                    # underneath still shows through a little (less contrast
                    # against the surrounding ground than a flat opaque tile).
                    self._tile_texture(
                        surface, cover_tile, rect,
                        alpha=TERRAIN_TILE_ALPHA, mask_points=points,
                    )
                    continue
                if obstacle.category == LIGHT and self._is_barricade_shaped(obstacle):
                    color = BARRICADE_COLOR
                else:
                    color = TERRAIN_COLORS.get(obstacle.category, OBSTACLE_COLOR)
                # Fallback (no cover tile texture present): translucent flat
                # color overlay instead of a solid block - a visual cue that
                # models can move onto and end their move on this terrain.
                pygame.draw.polygon(terrain_overlay, (*color, 140), points)
        surface.blit(terrain_overlay, (0, 0))

        for obstacle in obstacles:
            if obstacle.category != DENSE:
                continue
            # Dense terrain is drawn as a solid, opaque block - it's a real
            # obstacle, matching how it behaves for LoS (movement depends on
            # the specific model, rule 13.06 - see Obstacle.blocks_movement_for()).
            # A POLYGON of its four corners rather than a Rect of its bounding
            # box: for a rotated wall those are different shapes, and the
            # bounding box is the one the rules do NOT use.
            #
            # The drawn biome paints its own (arena_biome.draw_wall): the one
            # flat OBSTACLE_COLOR below was picked against the three LIGHT
            # photographed grounds and is near-invisible on a dark one -
            # measured, see arena_biome.WALL_FILL.
            points = obstacle_points_px(board, obstacle)
            if biomes.is_procedural():
                arena_biome.draw_wall(surface, board, points)
            else:
                pygame.draw.polygon(
                    surface, TERRAIN_COLORS.get(DENSE, OBSTACLE_COLOR), points)
        return surface

    def _draw_ground(self, surface, board):
        """Später-Liste (Sprites): the battlefield floor
        (sprites.ground_texture_path(), i.e. the selected biome's ground
        picture - see game/biomes.py), if the user has dropped one in - falls
        back to the plain BACKGROUND_COLOR fill (as before any ground art
        existed) if there isn't one, same "missing art is fine" convention as
        unit sprites (see game/sprites.py).

        Unlike the two cover textures this is NOT a repeatable tile (User:
        "wueste-boden ist keine wiederholbare kachel. das sprite soll die
        gesamte map ausfuellen"): it's one picture of a whole desert
        battlefield, so a SINGLE copy is scaled to cover the whole board
        (_ground_image below). Tiling it the way the old seamless
        Sprites/Ground.jpg was tiled would repeat that picture's own frame,
        edge seam and large-scale features several times across the board.

        Only ever called from _render_static_layer(), itself cached (see
        draw()) - the scale below runs once per scene, not once per frame.
        That's also why the scaled copy isn't kept in a cache of its own: it
        would be a second full-board-sized Surface (tens of MB at the
        supersampled render resolution) held alongside the static layer it
        was just blitted into."""
        if biomes.is_procedural():
            surface.blit(arena_biome.ground_surface(board), (0, 0))
            return
        ground_path = sprites.ground_texture_path()
        if ground_path is None:
            surface.fill(config.BACKGROUND_COLOR)
            return
        surface.blit(self._ground_image(ground_path, surface.get_size()), (0, 0))

    def _cover_tile(self, role, board):
        """The Surface one cover footprint is tiled with for `role`
        (biomes.DENSE_COVER / LIGHT_COVER), or None if this biome has no art
        for it - in which case the caller falls back to the flat translucent
        colour overlay, exactly as before.

        The ONE place the two kinds of biome differ for cover: a photographed
        one resolves a file and scales it to that role's physical tile size,
        a drawn one is handed the board and returns a tile at a size of its own
        choosing (see game/arena_biome.COVER_TILE_SIZE_IN for why it gets to
        pick). Both return an opaque Surface, so _tile_texture() below - and
        with it the masked-tile blend that was hard enough to get right once -
        is shared rather than duplicated per biome kind."""
        if biomes.is_procedural():
            return arena_biome.cover_tile(role, board)
        path, tile_size_in = (
            (sprites.dense_cover_texture_path(), DENSE_COVER_TILE_SIZE_IN)
            if role == biomes.DENSE_COVER
            else (sprites.normal_cover_texture_path(), NORMAL_COVER_TILE_SIZE_IN)
        )
        return None if path is None else self._cached_tile(path, board, tile_size_in)

    @staticmethod
    def _ground_image(path, size):
        """The ground art scaled to exactly `size`, "cover"-style: scaled by
        the LARGER of the two axis ratios, so it reaches BOTH board edges
        rather than leaving a strip of unpainted board along the shorter
        one, then centre-cropped to size.

        Deliberately a crop rather than a plain stretch to `size`. The art's
        own aspect ratio is close to map2's 60x44 (1024x748, so ~0.4% of it
        is cropped away there), but map1 is 44x60 PORTRAIT - stretching one
        into the other would smear the sand grain to nearly twice its width.
        Losing a little of the picture off one axis instead is invisible on
        a ground texture."""
        board_w, board_h = size
        raw = pygame.image.load(path).convert()
        src_w, src_h = raw.get_size()
        scale = max(board_w / src_w, board_h / src_h)
        # The max() guards the rounding: the axis that set `scale` lands on
        # the board size exactly in exact arithmetic, but a float hair under
        # it would leave a one-pixel unpainted line along that edge.
        scaled = pygame.transform.smoothscale(
            raw, (max(board_w, round(src_w * scale)), max(board_h, round(src_h * scale))),
        )
        if scaled.get_size() == size:
            return scaled
        image = pygame.Surface(size)
        crop = pygame.Rect(
            (scaled.get_width() - board_w) // 2,
            (scaled.get_height() - board_h) // 2,
            board_w, board_h,
        )
        image.blit(scaled, (0, 0), crop)
        return image

    def _tile_texture(self, surface, tile, rect, alpha=None, mask_points=None):
        """Tiles `tile` across `rect` (clipped to it, so this also works for a
        single terrain footprint, not just the whole board). Tiles are
        grid-aligned to the SURFACE's own (0,0) origin rather than rect's
        own top-left, so e.g. two separate ruin floor patches show the same
        continuous pattern instead of each restarting it at their own
        corner. `alpha` (0-255, None = fully opaque) blends each tile with
        whatever's already drawn underneath instead of fully replacing it -
        the tile Surface is shared across every call for the same texture, so
        this is applied fresh each call rather than baked in once.

        Takes the READY tile rather than resolving one, because where a tile
        comes from is a separate question with two answers (a scaled photo or
        a drawn pattern - see _cover_tile()) while this - the wrapping, the
        origin alignment and the mask blend below - is the same either way."""
        # Set on the CLIP path only. The masked path below carries `alpha` in
        # its mask instead - see there for why - and would otherwise apply it
        # twice. Explicitly cleared rather than left alone, because the tile
        # Surface is shared with every other call for the same texture and a
        # previous clip-path call would leave its own alpha on it.
        tile.set_alpha(alpha if mask_points is None else None)
        tile_w, tile_h = tile.get_size()
        start_x = (rect.x // tile_w) * tile_w
        start_y = (rect.y // tile_h) * tile_h
        if mask_points is None:
            previous_clip = surface.get_clip()
            surface.set_clip(rect)
            for y in range(start_y, rect.bottom, tile_h):
                for x in range(start_x, rect.right, tile_w):
                    surface.blit(tile, (x, y))
            surface.set_clip(previous_clip)
            return
        # A ROTATED footprint cannot be clipped with set_clip(), which only
        # takes a Rect. So the tiles go onto a scratch surface the size of the
        # footprint's bounding box and are then multiplied by a filled polygon
        # mask before being blitted back. The tile grid keeps its alignment to
        # the DESTINATION surface's origin (start_x/start_y above, minus the
        # scratch offset), so two patches still show one continuous pattern
        # rather than each restarting at its own corner.
        #
        # `alpha` RIDES IN THE MASK, and that is not a tidy-up. The tiles are
        # blitted OPAQUE onto a transparent scratch surface; a translucent tile
        # there would first be blended against the scratch's own (0,0,0,0)
        # black - darkening it - and then blended again on the way back, so the
        # footprint came out substantially darker than the same texture drawn
        # through the clip path above. Measured on a solid 200-grey tile over a
        # 60-grey ground at alpha 200: 154 through here against the intended
        # 170, i.e. the texture lost 16 of the 110 points of contrast it was
        # supposed to have. Invisible for years because every shipped texture
        # was the high-contrast desert set; the city biome's ground and rubble
        # are only ~27 points apart in the source art, so more than half of the
        # difference was being blended away and the user reported the light
        # cover as simply not visible.
        #
        # Multiplying by a mask whose own alpha IS `alpha` gets it right in one
        # step: RGB is multiplied by white (unchanged), the patch's alpha
        # becomes `alpha` inside the polygon and 0 outside, and the single blit
        # back is then exactly the blend the clip path performs.
        patch = pygame.Surface(rect.size, pygame.SRCALPHA)
        for y in range(start_y, rect.bottom, tile_h):
            for x in range(start_x, rect.right, tile_w):
                patch.blit(tile, (x - rect.x, y - rect.y))
        mask = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.polygon(mask, (255, 255, 255, 255 if alpha is None else alpha),
                            [(px - rect.x, py - rect.y) for px, py in mask_points])
        patch.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(patch, rect.topleft)

    def _cached_tile(self, path, board, tile_size_in):
        """A texture scaled to tile_size_in physical inches WIDE, keeping its
        own aspect ratio - a deliberate, purely aesthetic pick for each
        texture (no scale was specified for either), chosen close to that
        texture's own source resolution so tiling it doesn't blur/pixelate
        it any further than necessary. Cached per (path, tile_px) -
        recomputed only if the board's own render resolution changes, not
        per tile/frame.

        The height follows from the source's aspect rather than being
        forced square, which is what this used to do. It cost nothing while
        every texture happened to be square, and then a 1024x748
        1024x748 cover texture turned up and had its stonework squeezed
        ~27% narrower than it was drawn. (The art has since been redrawn
        square, so today this is a no-op on the real files - the rule
        stays because nothing makes the next one square.)
        _tile_texture() steps by the tile's own width and height
        separately, so a non-square tile lays out exactly the same."""
        tile_px = max(1, round(board.in_to_px_len(tile_size_in)))
        cache_key = (path, tile_px)
        cached = self._ground_tile_cache.get(cache_key)
        if cached is not None:
            return cached
        raw = pygame.image.load(path).convert()
        src_w, src_h = raw.get_size()
        tile = pygame.transform.smoothscale(raw, (tile_px, max(1, round(tile_px * src_h / src_w))))
        self._ground_tile_cache[cache_key] = tile
        return tile

    def _draw_tokens(self, surface, board, tokens):
        """A model's base is a colored RING and nothing else - no fill at
        all, so the ground (and any blood decal or terrain tint already
        drawn on it) shows straight through the middle of every base. User:
        "nimm die fuellung komplett raus sodass nur der farbige ring uebrig
        bleibt innen sind sie transparent".

        Taking the fill out took the glow pass with it. That pass stroked
        an SRCALPHA ring onto a shared board-sized overlay before the fill
        went down - but pygame strokes a circle INWARD from its radius, so
        the fill (drawn at the same radius) covered every pixel of it:
        measured 0 changed pixels of 1.28M on a full board with the glow
        switched off, i.e. the "outward halo" it was documented as
        producing had never actually been on screen. Removing the fill
        would have made it visible for the first time, as a translucent
        band around the inside of each rim - precisely the not-transparent
        middle being asked about here - so it is deleted rather than moved
        outward, along with a per-frame overlay clear + blit that was
        producing nothing.

        Two passes: pass 1 strokes each base's ring and puts its art (or
        its 2-letter label) on top; pass 2 draws the wound badges last, for
        the same reason status labels are a separate pass - a badge sits
        partly OUTSIDE its own base, so drawing it inside pass 1 would let
        the next token in the list paint straight over a neighbour's
        badge."""
        unusual_loadout_models = self._unusual_loadout_models(tokens)
        badges = []
        for token in tokens:
            color = self._token_color(token)
            is_leader = token.profile is not None and token.profile.squad_leader
            if is_leader:
                # Fixed gold, independent of team color - see
                # SQUAD_LEADER_RING_COLOR's docstring for why a tint of the
                # team color wasn't enough on its own.
                ring_color = SQUAD_LEADER_RING_COLOR
                border_width = SQUAD_LEADER_BORDER_WIDTH
            elif token in unusual_loadout_models:
                ring_color = self._tint(color)
                border_width = TOKEN_BORDER_WIDTH
            else:
                ring_color = color
                border_width = TOKEN_BORDER_WIDTH
            px, py = board.to_px(token.x_in, token.y_in)
            r_px = round(board.in_to_px_len(token.radius_in))
            # Two thin concentric strokes, team color outside and near-black
            # immediately inside it - see TOKEN_INNER_RING_WIDTH. pygame
            # strokes a circle INWARD from the radius it is given, so
            # drawing the second one at the first one's inner edge butts
            # them together with no overlap and no gap.
            #
            # Both are stroked FIRST and the art goes on top of them (User
            # feedback: the art must sit over the base, not have the ring
            # cut across it on top) - and the base keeps its real,
            # unchanged size either way (art must not inflate the effective
            # base footprint).
            outer_width = self._ring_width(border_width)
            inner_width = self._ring_width(TOKEN_INNER_RING_WIDTH)
            pygame.draw.circle(surface, ring_color, (round(px), round(py)), r_px, width=outer_width)
            inner_radius = r_px - outer_width
            if inner_radius > inner_width:
                pygame.draw.circle(surface, TOKEN_INNER_RING_COLOR, (round(px), round(py)), inner_radius, width=inner_width)
            sprite_path = sprites.sprite_for(token)
            if sprite_path is not None:
                # Später-Liste (Sprites): the unit's own art instead of the
                # letter label, sized to roughly match the base (see
                # sprites.SPRITE_SCALE) - only allowed to overhang it a
                # little, not blown up past it.
                sprite_surf = sprites.scaled_surface(sprite_path, r_px * 2)
                anchor_x, anchor_y = sprites.anchor_offset(sprite_path, sprite_surf.get_size())
                surface.blit(sprite_surf, (round(px - anchor_x), round(py - anchor_y)))
            else:
                self._draw_model_label(surface, token, px, py)
            badges.append((token, px, py, r_px))

        for token, px, py, r_px in badges:
            self._draw_wound_badge(surface, token, px, py, r_px)

    def _draw_wound_badge(self, surface, token, px, py, r_px):
        """A "<remaining>/<max>" pill (e.g. "7/13") pinned just ABOVE a
        multi-wound model that has lost wounds - see
        WOUND_BADGE_DAMAGED_COLOR's comment for why only damaged models
        get one. Above, because draw_status_labels() stacks its pills
        below the model: a damaged, battle-shocked model shows both
        without either covering the other.

        Deliberately silent for a model on 0 wounds: that model is dead
        and main.py's per-frame remove_dead_models() is about to take it
        off the board, so a "0/13" badge would only ever flash for the
        remainder of the frame it died in."""
        if token.profile is None or token.current_wounds is None:
            return
        maximum = token.profile.wounds
        remaining = token.current_wounds
        if maximum is None or maximum <= 1 or not 0 < remaining < maximum:
            return
        critical = remaining <= maximum * WOUND_BADGE_CRITICAL_FRACTION
        color = WOUND_BADGE_CRITICAL_COLOR if critical else WOUND_BADGE_DAMAGED_COLOR
        pill = self._pill_surface(
            self.status_label_font,
            f"{remaining}/{maximum}",
            WOUND_BADGE_TEXT_COLOR + (WOUND_BADGE_ALPHA,),
            color + (WOUND_BADGE_ALPHA,),
        )
        surface.blit(pill, pill.get_rect(midbottom=(round(px), round(py - r_px - 3))))

    @staticmethod
    def _pill_surface(font, text, text_color, bg_color, padding=(4, 1)):
        """The small rounded label chip used for both status effects and
        wound badges. Alpha is baked into the two colors passed in rather
        than applied via Surface.set_alpha() afterwards - see
        draw_status_labels()'s docstring for why."""
        text_surf = font.render(text, True, text_color)
        pill_rect = text_surf.get_rect().inflate(*padding)
        pill_surf = pygame.Surface(pill_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(pill_surf, bg_color, pill_surf.get_rect(), border_radius=3)
        pill_surf.blit(text_surf, text_surf.get_rect(center=pill_surf.get_rect().center))
        return pill_surf

    def draw_embarked_passengers(self, surface, board, tokens, embarked_squads):
        """Draws a small icon of each embarked squad's strongest model
        (game.squad.strongest_model), at its real on-battlefield size,
        centered on every on-board TRANSPORT token currently carrying one -
        see this module's comment above EMBARKED_ICON_GAP_PX for why. Several squads
        embarked in the same TRANSPORT (rare, but its capacity can allow it)
        are laid out side by side across that same center point rather than
        overlapping. The icon carries its squad's own team colour
        (_token_color(), fixed per owner), and nothing here gates whether it is
        drawn - the whole point is that this is visible regardless of whose
        turn it is."""
        for transport_token in tokens:
            if transport_token.profile is None or not transport_token.profile.transport:
                continue
            passengers = [s for s in embarked_squads if s.embarked_in is transport_token]
            if not passengers:
                continue
            models = [(squad, strongest_model(squad)) for squad in passengers]
            models = [(squad, model) for squad, model in models if model is not None]
            if not models:
                continue
            px, py = board.to_px(transport_token.x_in, transport_token.y_in)
            icon_radii_px = [round(board.in_to_px_len(model.radius_in)) for _squad, model in models]
            total_width = sum(r * 2 for r in icon_radii_px) + EMBARKED_ICON_GAP_PX * (len(models) - 1)
            cx = px - total_width / 2
            for (squad, model), r_px in zip(models, icon_radii_px):
                cx += r_px
                self._draw_embarked_icon(surface, model, squad, round(cx), round(py), r_px)
                cx += r_px + EMBARKED_ICON_GAP_PX

    def _draw_embarked_icon(self, surface, model, squad, cx, cy, r_px):
        # User feedback: no base/ring underneath - just the sprite itself,
        # unlike a normal on-board token (_draw_tokens draws the disc FIRST
        # specifically so the art sits on top of it). Only a datasheet with
        # no art at all (see sprites.sprite_for's own "missing art is fine"
        # convention) still needs a disc - there'd be nothing to look at
        # otherwise, so that fallback keeps its own small filled circle.
        sprite_path = sprites.sprite_for(model)
        if sprite_path is not None:
            sprite_surf = sprites.scaled_surface(sprite_path, r_px * 2)
            anchor_x, anchor_y = sprites.anchor_offset(sprite_path, sprite_surf.get_size())
            surface.blit(sprite_surf, (round(cx - anchor_x), round(cy - anchor_y)))
        elif model.profile is not None:
            color = self._token_color(model)
            fill_color = tuple(round(c * TOKEN_FILL_DARKEN) for c in color)
            pygame.draw.circle(surface, fill_color, (cx, cy), r_px)
            pygame.draw.circle(surface, color, (cx, cy), r_px, width=TOKEN_BORDER_WIDTH)
            name = model.profile.name
            label = name.split()[-1][:2] if model.profile.squad_leader else name[:2]
            label_surf = self.status_label_font.render(label, True, MODEL_LABEL_COLOR)
            surface.blit(label_surf, label_surf.get_rect(center=(cx, cy)))

        # A small "alive/starting" count badge on the icon's corner - who's
        # in there matters less without also knowing how many of them are
        # left, and a squad whittled down to a few survivors looks
        # identical to a full one without this.
        alive = len([m for m in squad.models if not m.is_dead()])
        total = getattr(squad, "starting_model_count", len(squad.models))
        count_text = str(alive) if alive == total else f"{alive}/{total}"
        pill = self._pill_surface(
            self.status_label_font, count_text,
            EMBARKED_COUNT_TEXT_COLOR + (EMBARKED_COUNT_ALPHA,),
            EMBARKED_COUNT_BADGE_COLOR + (EMBARKED_COUNT_ALPHA,),
        )
        badge_center = (round(cx + r_px * 0.75), round(cy + r_px * 0.75))
        surface.blit(pill, pill.get_rect(center=badge_center))

    def _is_barricade_shaped(self, obstacle):
        """Später-Liste (Gelände-Farbkodierung): Light terrain covers both a
        ruin's rubble floor and freestanding fence/barricade lines - same
        rule category (13.04), but visually very different in the reference
        map. There's no separate "barricade" flag on Obstacle, so this is a
        shape heuristic: a fence line is thin on its short side, a ruin
        floor never is (even the narrowest one in the current demo is 3\"
        thick)."""
        return min(obstacle.width_in, obstacle.height_in) <= BARRICADE_MAX_THICKNESS_IN

    def _draw_deployment_zones(self, surface, board, deployment_zones):
        """Später-Liste ("dunkler Hintergrund mit subtilen optischen
        Hilfslinien... Deployment Zones, Zuordnung der Spielfeldkanten,
        6-Zoll-Mittelkreis, Spielfeld-Viertel"): board-quarter lines, a 6"
        center circle, and each deployment zone as a faint outline plus a
        thicker highlight along the specific board edge it belongs to -
        drawn onto the (already-filled) background so terrain/tokens still
        render on top of it, not under it. Rule 03.01 itself has no
        enforcement hook yet (see DeploymentZone's docstring) - this is
        purely the visual reference layer."""
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        self._draw_board_quarter_lines(overlay, board)
        self._draw_center_circle(overlay, board)
        for zone in deployment_zones:
            self._draw_deployment_zone(overlay, board, zone)
        surface.blit(overlay, (0, 0))

    def _draw_board_quarter_lines(self, overlay, board):
        mid_x_px = board.to_px(board.width_in / 2, 0)[0]
        mid_y_px = board.to_px(0, board.height_in / 2)[1]
        self._draw_dashed_line(overlay, (mid_x_px, 0), (mid_x_px, board.height_px), BOARD_QUARTER_LINE_COLOR)
        self._draw_dashed_line(overlay, (0, mid_y_px), (board.width_px, mid_y_px), BOARD_QUARTER_LINE_COLOR)

    def _draw_dashed_line(self, overlay, start_px, end_px, color):
        sx, sy = start_px
        ex, ey = end_px
        length = ((ex - sx) ** 2 + (ey - sy) ** 2) ** 0.5
        if length == 0:
            return
        dash_px = max(2, round(BOARD_QUARTER_DASH_IN * 18))  # fixed on-screen dash size, independent of zoom
        ux, uy = (ex - sx) / length, (ey - sy) / length
        pos = 0.0
        drawing = True
        while pos < length:
            seg_end = min(pos + dash_px, length)
            if drawing:
                pygame.draw.line(
                    overlay, color,
                    (round(sx + ux * pos), round(sy + uy * pos)),
                    (round(sx + ux * seg_end), round(sy + uy * seg_end)),
                    width=1,
                )
            pos = seg_end
            drawing = not drawing

    def _draw_center_circle(self, overlay, board):
        center_px = board.to_px(board.width_in / 2, board.height_in / 2)
        radius_px = board.in_to_px_len(CENTER_CIRCLE_RADIUS_IN)
        pygame.draw.circle(overlay, CENTER_CIRCLE_COLOR, (round(center_px[0]), round(center_px[1])), round(radius_px), width=2)

    def _draw_deployment_zone(self, overlay, board, zone):
        """The zone's boundary, traced from its signed distance rather than
        from a rectangle list - so a rotated, diagonal or holed zone draws
        itself with no extra case here.

        Runs on the CACHED static layer (_cached_static_layer), i.e. once per
        scene and not per frame, which is what makes sampling affordable at
        all. ZONE_OUTLINE_STEP_IN is the trade: 0.25" over a 60x44 board is
        ~42k distance evaluations per zone."""
        color = DEPLOYMENT_ZONE_LINE_COLORS.get(zone.owner, DEPLOYMENT_ZONE_FALLBACK_COLOR)
        box = zone.bounding_box()
        # An unbounded part (a half-plane) leaves the box open on that side;
        # the board is the only place anything can stand anyway.
        clamp = (0.0, 0.0, board.width_in, board.height_in)
        if box is None:
            box = clamp
        else:
            box = (max(box[0], clamp[0]), max(box[1], clamp[1]),
                   min(box[2], clamp[2]), min(box[3], clamp[3]))
        # Then GROWN by a margin, which is not cosmetic: a point exactly on the
        # boundary counts as inside (signed distance 0 >= 0), so sampling only
        # up to the shape's own extent leaves every corner of the grid "inside"
        # and marching squares finds no sign change at all - the outline simply
        # vanishes along any edge flush with the bounding box, which is every
        # edge of a rectangular zone. Segments falling outside the surface are
        # clipped by pygame.
        margin = 2 * ZONE_OUTLINE_STEP_IN
        box = (box[0] - margin, box[1] - margin, box[2] + margin, box[3] + margin)
        # A traced line sits ON the boundary, where pygame.draw.rect's outline
        # used to sit just INSIDE it. That only shows where the boundary is a
        # board edge, and there it showed as the line vanishing off the
        # surface entirely - so the same inset _draw_inset_edge_line uses is
        # applied here, by clamping into the surface.
        #
        # Both the width and the inset come from the SCALED width, not from the
        # constant: DEPLOYMENT_ZONE_LINE_WIDTH is in on-screen pixels and this
        # surface is supersampled (see _ring_width, and the measurement beside
        # that constant).
        line_width = self._ring_width(DEPLOYMENT_ZONE_LINE_WIDTH)
        inset = line_width / 2

        def to_px(x_in, y_in):
            px, py = board.to_px(x_in, y_in)
            px = min(max(px, inset), board.width_px - 1 - inset)
            py = min(max(py, inset), board.height_px - 1 - inset)
            return (round(px), round(py))

        for (ax_in, ay_in), (bx_in, by_in) in self._shape_outline_segments(zone.shape, box):
            pygame.draw.line(overlay, color, to_px(ax_in, ay_in), to_px(bx_in, by_in),
                             width=line_width)
        self._draw_zone_board_edges(overlay, board, zone, color,
                                    self._ring_width(BOARD_EDGE_LINE_WIDTH))

    @staticmethod
    def _shape_outline_segments(shape, box, step_in=ZONE_OUTLINE_STEP_IN):
        """Marching squares over `shape`'s signed distance: the boundary as a
        list of ((x0,y0),(x1,y1)) segments in inches.

        Crossings are placed by LINEAR INTERPOLATION of the distance along
        each cell edge, not snapped to the cell corner, so a curve (the
        circular hole a mission layout punches around the board centre) comes
        out smooth at a step far coarser than a pixel."""
        min_x, min_y, max_x, max_y = box
        if max_x <= min_x or max_y <= min_y:
            return []
        cols = max(1, int(math.ceil((max_x - min_x) / step_in)))
        rows = max(1, int(math.ceil((max_y - min_y) / step_in)))
        dx = (max_x - min_x) / cols
        dy = (max_y - min_y) / rows
        sd = shape.signed_distance
        # One row of samples at a time, reusing the previous row - halves the
        # distance evaluations versus sampling each cell's four corners.
        rowbuf = [sd(min_x + i * dx, min_y) for i in range(cols + 1)]
        segments = []
        for j in range(rows):
            y1 = min_y + (j + 1) * dy
            nextbuf = [sd(min_x + i * dx, y1) for i in range(cols + 1)]
            y0 = min_y + j * dy
            for i in range(cols):
                x0 = min_x + i * dx
                x1 = x0 + dx
                v00, v10, v01, v11 = rowbuf[i], rowbuf[i + 1], nextbuf[i], nextbuf[i + 1]
                points = []
                if (v00 >= 0) != (v10 >= 0):                       # bottom edge
                    points.append((x0 + dx * _crossing(v00, v10), y0))
                if (v10 >= 0) != (v11 >= 0):                       # right edge
                    points.append((x1, y0 + dy * _crossing(v10, v11)))
                if (v01 >= 0) != (v11 >= 0):                       # top edge
                    points.append((x0 + dx * _crossing(v01, v11), y1))
                if (v00 >= 0) != (v01 >= 0):                       # left edge
                    points.append((x0, y0 + dy * _crossing(v00, v01)))
                # Two crossings is the ordinary case. Four is a saddle (the
                # cell straddles a pinch of the shape); pairing them in the
                # order collected is visually right at this step size and
                # cannot mis-place the boundary, only which two ends join.
                for k in range(0, len(points) - 1, 2):
                    segments.append((points[k], points[k + 1]))
            rowbuf = nextbuf
        return segments

    @staticmethod
    def _draw_zone_board_edges(overlay, board, zone, color, width):
        """"Zuordnung der Spielfeldkanten": a thicker highlight along the
        stretch of each of its owner's own board edges (own_board_edges) that
        this zone actually reaches.

        The run is WALKED rather than read off a rectangle's coordinates, so a
        diagonal zone highlights exactly the part of the edge it reaches
        instead of all of it or none of it."""
        for (sx, sy), (ex, ey) in own_board_edges(board, zone):
            length_in = math.hypot(ex - sx, ey - sy)
            steps = max(1, int(math.ceil(length_in / ZONE_OUTLINE_STEP_IN)))
            run_start = None
            for k in range(steps + 1):
                t = k / steps
                x, y = sx + (ex - sx) * t, sy + (ey - sy) * t
                # Nudge inward by a hair: a zone whose boundary IS the board
                # edge sits exactly at distance 0 there, and floating point
                # must not decide whether that counts.
                touching = zone.signed_distance(x, y) >= -ZONE_EDGE_TOUCH_TOLERANCE_IN
                if touching and run_start is None:
                    run_start = (x, y)
                elif not touching and run_start is not None:
                    _draw_inset_edge_line(overlay, board, run_start, (x, y), color, width)
                    run_start = None
            if run_start is not None:
                _draw_inset_edge_line(overlay, board, run_start, (ex, ey), color, width)

    def _unusual_loadout_models(self, tokens):
        """Which of these tokens should get the tint highlight: either an
        off-squad weapon loadout (Squad.unusual_loadout_models(), e.g. a
        Kroot Long-quill's extra pistol), computed once per squad per frame
        rather than once per token, OR a datasheet-marked squad_leader model
        (e.g. Strike/Breacher Team's Shas'ui) - a sergeant whose loadout is
        identical to the rank-and-file around it and would otherwise be
        completely invisible on the board (see UnitProfile.squad_leader)."""
        seen_squads = set()
        unusual = set()
        for token in tokens:
            if token.profile is not None and token.profile.squad_leader:
                unusual.add(token)
            if token.squad is not None and token.squad not in seen_squads:
                seen_squads.add(token.squad)
                unusual |= token.squad.unusual_loadout_models()
        return unusual

    def _tint(self, color):
        return tuple(min(255, c + UNUSUAL_LOADOUT_TINT) for c in color)

    def _draw_model_label(self, surface, token, px, py):
        """Später-Liste: every model gets a short label (first two letters
        of its unit profile name) so individual models stay identifiable on
        the board, e.g. distinguishing a Boss Nob ('Bo') from a Boy ('Bo')
        isn't perfect, but combined with the loadout color tint it's enough
        to tell squadmates apart at a glance.

        A squad_leader model (see UnitProfile.squad_leader) instead takes its
        LAST word's first two letters, not its first word's - these
        datasheets consistently put the rank suffix at the end of the name
        ("Fire Warrior Shas'ui", "Stealth Shas'vre"), so this reads as "Sh"
        instead of colliding with the rank-and-file's own "Fi"/"St" label.
        Long-quill (one word, no suffix to extract) is unaffected either way
        - it was already visually distinct via its own weapon loadout."""
        if token.profile is None:
            return
        name = token.profile.name
        if token.profile.squad_leader:
            label = name.split()[-1][:2]
        else:
            label = name[:2]
        label_surf = self.label_font.render(label, True, MODEL_LABEL_COLOR)
        label_rect = label_surf.get_rect(center=(round(px), round(py)))
        surface.blit(label_surf, label_rect)

    def draw_status_labels(self, surface, board, status_by_token):
        """Später-Liste (Status-Effekte): a small, semi-transparent colored
        pill per active status effect, stacked below each model -
        status_by_token maps a token to its list of active effect keys
        (game.status_effects). Smaller font + STATUS_LABEL_ALPHA
        transparency (both alpha baked directly into the drawn RGBA colors,
        not via Surface.set_alpha() - avoids relying on how that combines
        with an SRCALPHA surface's own per-pixel alpha) so a dense cluster
        of small-based models doesn't get buried under a wall of opaque
        pills - see STATUS_LABEL_ALPHA's own comment."""
        for token, effects in status_by_token.items():
            if not effects:
                continue
            px, py = board.to_px(token.x_in, token.y_in)
            r_px = board.in_to_px_len(token.radius_in)
            label_y = py + r_px + 3
            for effect in effects:
                label_text = status_effects.LABELS.get(effect, effect)
                color = STATUS_LABEL_COLORS.get(effect, (120, 120, 120)) + (STATUS_LABEL_ALPHA,)
                text_color = STATUS_LABEL_TEXT_COLOR + (STATUS_LABEL_ALPHA,)
                pill_surf = self._pill_surface(self.status_label_font, label_text, text_color, color)
                dest_rect = pill_surf.get_rect(midtop=(round(px), round(label_y)))
                surface.blit(pill_surf, dest_rect)
                label_y += dest_rect.height + 1

    @staticmethod
    def _clamp_rect_to_surface(rect, surface):
        """User report: objectives near the board edge (e.g. the home
        objectives, which sit right at the deployment-zone edge) had their
        icon/label clipped clean off by the surface bounds - a plain blit
        outside a Surface's own size is silently cropped, not shown
        letterboxed or shifted. Nudges rect (without resizing it) so it
        stays fully within surface - same "keep myself within the window
        edges" idea as UnitDatacardOverlay already does for its own
        hover card, just against the board surface instead of the
        window."""
        clamped = rect.copy()
        clamped.x = max(0, min(clamped.x, surface.get_width() - clamped.width))
        clamped.y = max(0, min(clamped.y, surface.get_height() - clamped.height))
        return clamped

    def draw_terrain_markers(self, surface, board, areas, label=""):
        """An operation marker on each of `areas` - Death Trap's "place one of
        your operation markers within that terrain area".

        Drawn with objective_outline_points(), which takes ANY TerrainArea and
        not only an objective's, so a trapped ruin gets the same grown,
        rotation-aware hull an objective marker does and the two read as the
        same kind of board furniture.

        A LIVE pass, deliberately not part of _render_static_layer(): that
        layer is cached on the identity and length of the terrain list, so a
        flag set on an area mid-battle would never invalidate it and the marker
        would simply never appear. Being trapped is exactly such a mid-battle
        flag."""
        if not areas:
            return
        for area in areas:
            points = objective_outline_points(board, area)
            if len(points) < 3:
                continue
            pygame.draw.polygon(surface, TRAPPED_AREA_COLOR, points,
                                self._ring_width(TRAPPED_AREA_WIDTH_PX))
            if not label:
                continue
            # The badge sits on the hull's top-left vertex, the same anchor
            # draw_objectives() pins its info icon to - on a rotated piece that
            # is a real corner, where the bounding box's corner floats in open
            # ground.
            anchor = min(points, key=lambda p: p[0] + p[1])
            text = self.label_font.render(label, True, TRAPPED_LABEL_TEXT_COLOR)
            pad = 3
            box = pygame.Rect(anchor[0], anchor[1] - text.get_height() - pad,
                              text.get_width() + pad * 2, text.get_height() + pad)
            box = self._clamp_rect_to_surface(box, surface)
            pygame.draw.rect(surface, TRAPPED_AREA_COLOR, box, border_radius=3)
            surface.blit(text, (box.x + pad, box.y + pad // 2))

    def draw_objectives(self, surface, board, objectives, all_tokens, hover_native_px=None):
        """Rule 14.01-14.03: an outline around each objective's terrain
        area, colored by whoever currently controls it (grey if
        uncontrolled). User report: the full "{name}: {status} ({oc
        totals})" label used to be drawn permanently above the outline,
        which constantly covered the terrain/models sitting under it -
        replaced with a small "i" info-icon pinned to the outline's corner;
        the full label (plus the SECURED badge) only slides out when
        hover_native_px (board-surface-native pixel coords, same space
        board.to_px() draws in - main.py converts the raw mouse position
        through board_rect_screen/Camera before passing it in) is within
        the icon's own circle. Both the icon and the expanded label are
        clamped to stay fully within the board surface (see
        _clamp_rect_to_surface) so an objective near a board edge doesn't
        get cut off."""
        icon_radius = max(9, self.label_font.get_height() // 2 + 2)
        for objective in objectives:
            area = objective.terrain_area
            points = objective_outline_points(board, area)
            outline_rect = _points_bounds(points)
            color = OBJECTIVE_COLORS.get(objective.controlled_by, OBJECTIVE_NEUTRAL_COLOR)
            if all(abs(getattr(f, "angle_deg", 0.0)) < 1e-9 for f in area.features):
                # Square to the board: the hull IS this rectangle, drawn the
                # way it always was so the rounded corner survives. Only the
                # CORNER STYLE differs between the two calls - the shape comes
                # from objective_outline_points() either way.
                pygame.draw.rect(surface, color, outline_rect, width=4, border_radius=10)
            else:
                pygame.draw.polygon(surface, color, points, width=4)

            # Pinned to the outline's own top-left VERTEX, not to the corner
            # of its bounding box: on a rotated piece those are different
            # points, and the box corner floats in open ground with nothing
            # under it. min(x + y) is the top-left-most point of the hull, and
            # for an axis-aligned outline it IS the box corner, so nothing
            # moves on the square pieces.
            anchor = min(points, key=lambda p: p[0] + p[1]) if points else outline_rect.topleft
            icon_bounds = pygame.Rect(0, 0, icon_radius * 2, icon_radius * 2)
            icon_bounds.center = anchor
            icon_bounds = self._clamp_rect_to_surface(icon_bounds, surface)
            icon_center = icon_bounds.center
            is_hovered = (
                hover_native_px is not None
                and (hover_native_px[0] - icon_center[0]) ** 2 + (hover_native_px[1] - icon_center[1]) ** 2
                <= (icon_radius + 4) ** 2
            )
            pygame.draw.circle(surface, OBJECTIVE_LABEL_BG_COLOR, icon_center, icon_radius)
            pygame.draw.circle(surface, color, icon_center, icon_radius, width=2)
            icon_surf = self.label_font.render("i", True, color)
            surface.blit(icon_surf, icon_surf.get_rect(center=icon_center))

            if not is_hovered:
                continue

            totals = objective.level_of_control(all_tokens)
            control_text = objective.controlled_by or "Uncontrolled"
            oc_text = ", ".join(f"{player} {value}" for player, value in sorted(totals.items()))
            label = f"{objective.name}: {control_text}" + (f" ({oc_text})" if oc_text else "")

            label_surf = self.font.render(label, True, color)
            # outline_rect, not `rect`: this branch still said `rect` after the
            # rotated-outline work renamed it, and only fires while the cursor
            # is on the icon - so it sat here crashing nothing until someone
            # hovered one (User: "beim hovern über das objective info icon").
            # Same class as the Isha's Fury branch that ran against a
            # `board_rect` no scope ever had; see test_event_chain_wiring.py,
            # whose free-name sweep now covers this module too.
            bg_rect = label_surf.get_rect(
                midtop=(outline_rect.centerx, outline_rect.top - 26)).inflate(10, 6)
            bg_rect = self._clamp_rect_to_surface(bg_rect, surface)
            pygame.draw.rect(surface, OBJECTIVE_LABEL_BG_COLOR, bg_rect, border_radius=4)
            surface.blit(label_surf, label_surf.get_rect(center=bg_rect.center))

            if objective.secured_by is not None:
                secured_surf = self.label_font.render(f"SECURED ({objective.secured_by})", True, SECURED_BADGE_TEXT_COLOR)
                secured_bg = secured_surf.get_rect(
                    midtop=(outline_rect.centerx, bg_rect.bottom + 2)).inflate(8, 4)
                secured_bg = self._clamp_rect_to_surface(secured_bg, surface)
                pygame.draw.rect(surface, SECURED_BADGE_COLOR, secured_bg, border_radius=4)
                surface.blit(secured_surf, secured_surf.get_rect(center=secured_bg.center))

    def _token_color(self, token):
        """This model's team colour: Player 1 green, Player 2 red, FIXED.

        See TOKEN_TEAM_COLORS for why this no longer takes an active player.
        Whose turn it is is the player banner's job (and the turn-start
        overlay's, and the panel header's); a model's rim answers "whose model
        is this", which does not change while a decision is being made.

        Falls back to the token's own colour for a squad-less token or an owner
        this table does not know - the renderer has no other notion of who is
        playing, and a made-up third colour would say less than the token's
        own."""
        if token.squad is None:
            return token.color
        return TOKEN_TEAM_COLORS.get(token.squad.owner, token.color)

    def draw_visibility_highlight(self, surface, board, visible_models):
        for token in visible_models:
            px, py = board.to_px(token.x_in, token.y_in)
            r_px = board.in_to_px_len(token.radius_in) + 4
            pygame.draw.circle(
                surface, VISIBILITY_HIGHLIGHT_COLOR, (round(px), round(py)), round(r_px), width=2
            )

    def draw_shoot_targets(self, surface, board, targets):
        for token in targets:
            px, py = board.to_px(token.x_in, token.y_in)
            r_px = board.in_to_px_len(token.radius_in) + 8
            pygame.draw.circle(
                surface, SHOOT_TARGET_COLOR, (round(px), round(py)), round(r_px), width=3
            )

    def _squad_centroid_px(self, board, squad):
        models = [m for m in squad.models if not m.is_dead()] or squad.models
        if not models:
            return None
        avg_x = sum(m.x_in for m in models) / len(models)
        avg_y = sum(m.y_in for m in models) / len(models)
        return board.to_px(avg_x, avg_y)

    def draw_attack_arrow(self, surface, board, attacker_squad, target_squad):
        if attacker_squad is None or target_squad is None:
            return
        start = self._squad_centroid_px(board, attacker_squad)
        end = self._squad_centroid_px(board, target_squad)
        if start is None or end is None:
            return

        dx, dy = end[0] - start[0], end[1] - start[1]
        length = (dx * dx + dy * dy) ** 0.5
        if length == 0:
            return
        ux, uy = dx / length, dy / length

        tip = (end[0] - ux * ATTACK_ARROW_TIP_GAP, end[1] - uy * ATTACK_ARROW_TIP_GAP)
        shaft_end = (tip[0] - ux * ATTACK_ARROWHEAD_LENGTH, tip[1] - uy * ATTACK_ARROWHEAD_LENGTH)

        pygame.draw.line(surface, ATTACK_ARROW_COLOR, start, shaft_end, width=ATTACK_ARROW_WIDTH)

        perp_x, perp_y = -uy, ux
        p2 = (
            shaft_end[0] + perp_x * ATTACK_ARROWHEAD_WIDTH / 2,
            shaft_end[1] + perp_y * ATTACK_ARROWHEAD_WIDTH / 2,
        )
        p3 = (
            shaft_end[0] - perp_x * ATTACK_ARROWHEAD_WIDTH / 2,
            shaft_end[1] - perp_y * ATTACK_ARROWHEAD_WIDTH / 2,
        )
        pygame.draw.polygon(surface, ATTACK_ARROW_COLOR, [tip, p2, p3])

        mid = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        label_surf = self.font.render("Attack", True, ATTACK_LABEL_COLOR)
        label_rect = label_surf.get_rect(center=(round(mid[0]), round(mid[1])))
        bg_rect = label_rect.inflate(8, 4)
        pygame.draw.rect(surface, ATTACK_LABEL_BG, bg_rect, border_radius=4)
        surface.blit(label_surf, label_rect)

    def draw_squad_outline(self, surface, board, squad, color, bump_px, width_px):
        """A ring around every model of `squad` - i.e. "this whole UNIT is the
        subject", as opposed to the per-model rings that mean "this model is".

        Extracted at the second consumer, as the convention requires: the
        coherency-removal highlight was this loop, and the selected-unit outline
        is the same loop again. Both go through _ring_bump()/_ring_width(), so
        `bump_px` and `width_px` are ON-SCREEN pixels here - the raw values both
        call sites used before were shrunk by render_scale x zoom into the
        sub-pixel range before anyone saw them.

        Iterates squad.models rather than a caller-supplied token list, so a
        unit with mixed base sizes (rule 19.01 attached units - a 60 mm
        character among 32 mm bodies) gets each ring sized to its own model.
        Dead models are drawn too: remove_dead_models() runs once per frame, so
        filtering them here would make the outline flicker for one frame
        against a squad list that still contains them (Fehlerklasse 12)."""
        if squad is None:
            return
        bump = self._ring_bump(bump_px)
        width = self._ring_width(width_px)
        for model in squad.models:
            px, py = board.to_px(model.x_in, model.y_in)
            r_px = board.in_to_px_len(model.radius_in) + bump
            pygame.draw.circle(surface, color, (round(px), round(py)), round(r_px), width=width)

    def draw_coherency_removal_highlight(self, surface, board, pending_squad):
        self.draw_squad_outline(
            surface, board, pending_squad, COHERENCY_REMOVAL_COLOR,
            COHERENCY_REMOVAL_BUMP_PX, COHERENCY_REMOVAL_WIDTH_PX,
        )

    def draw_damage_choice_highlight(self, surface, board, candidates):
        if not candidates:
            return
        for model in candidates:
            px, py = board.to_px(model.x_in, model.y_in)
            r_px = board.in_to_px_len(model.radius_in) + 5
            pygame.draw.circle(
                surface, DAMAGE_CHOICE_COLOR, (round(px), round(py)), round(r_px), width=4
            )

    def draw_reserve_drag_ghost(self, surface, squad, mouse_pos_px):
        """Rule 03.02: a lightweight preview of the reserves-panel card
        currently being dragged toward the board, following the mouse -
        `surface` is the whole window (not board_surface), since the mouse
        can be anywhere on screen while dragging, and `mouse_pos_px` is
        already in screen pixels, not board inches."""
        model = squad.models[0]
        r_px = 18
        ghost = pygame.Surface((r_px * 2, r_px * 2), pygame.SRCALPHA)
        pygame.draw.circle(ghost, (*model.color, 160), (r_px, r_px), r_px)
        surface.blit(ghost, (mouse_pos_px[0] - r_px, mouse_pos_px[1] - r_px))
        # The name is data (an attached unit's is "<bodyguard> + <character>",
        # rule 19.01) and this label follows the mouse, so it has to wrap
        # against whatever room is left toward the window edge - and flip to
        # the cursor's left when there isn't enough of it.
        label_x = mouse_pos_px[0] + r_px + 4
        available = surface.get_width() - label_x - 4
        if available < GHOST_LABEL_MIN_WIDTH:
            available = min(GHOST_LABEL_MAX_WIDTH, mouse_pos_px[0] - r_px - 8)
            lines = wrap_text(self.screen_font, squad.name, available) or [squad.name]
            label_x = max(4, mouse_pos_px[0] - r_px - 4 - max(self.screen_font.size(l)[0] for l in lines))
        else:
            available = min(available, GHOST_LABEL_MAX_WIDTH)
            lines = wrap_text(self.screen_font, squad.name, available) or [squad.name]
        line_height = self.screen_font.get_height() + 2
        label_y = mouse_pos_px[1] - len(lines) * line_height // 2
        for line in lines:
            surface.blit(self.screen_font.render(line, True, (255, 255, 255)), (label_x, label_y))
            label_y += line_height

    def draw_placement_overlay(self, surface, board, keep_out_fn, band_fn,
                               session_key, band_key=None):
        """Rules 03.02 / 20.04 / 01.02.03: where this unit may be placed, drawn
        as BASE EDGES.

        TWO LAYERS, because one sign flips (see
        SetupController.base_edge_zones(), which produces both):

          * `keep_out_fn(x, y)` - ground no part of a base may touch. Painted
            red; the outline is the line a base may not cross.
          * `band_fn(x, y)` - 09.02's coherency band, which the base must
            REACH. Painted green, and only for a model return; None otherwise.

        Both are evaluated for a point-sized base, so ONE picture serves every
        model of the unit whatever its base size - which is the whole point.
        The old version drew legal CENTRES, a different curve per base size,
        and the caller had to nominate one model to draw for.

        `surface` is board_surface (this overlay is in board-local pixel
        space, like other board overlays). `session_key` / `band_key` identify
        the placement each mask belongs to; a mask is built once and reused for
        every later frame - see game/placement_overlay.py."""
        self._placement_overlay.draw(
            surface, board, session_key,
            lambda x_in, y_in: not keep_out_fn(x_in, y_in),
        )
        if band_fn is not None:
            self._coherency_overlay.draw(
                surface, board, band_key if band_key is not None else session_key,
                band_fn,
            )

    def draw_assigning_model_highlight(self, surface, board, model):
        """Split-fire helper: highlight the specific model+weapon currently
        awaiting a target assignment, so it's unambiguous which model's
        target is being picked - distinct from the shoot-target ring (which
        marks candidate enemy models, not the attacker)."""
        if model is None:
            return
        px, py = board.to_px(model.x_in, model.y_in)
        r_px = board.in_to_px_len(model.radius_in) + 8
        pygame.draw.circle(
            surface, ASSIGNING_MODEL_COLOR, (round(px), round(py)), round(r_px), width=4
        )

    def draw_selection(self, surface, board, selection):
        """The player's current pick (game/selection.py), drawn as a UNIT: a dim
        ring around every model and a brighter one around the anchor model.

        Replaces draw_selected_model(), which drew ONE cyan ring around the one
        model the click landed on. That was the whole visual: a unit of twenty
        looked exactly like a unit of one, and nothing said which unit the left
        panel was talking about.

        NO NAME PLATE ON THE BOARD any more (User: "Entferne das Label, das den
        Squad namen anzeigt, wenn man eine Einheit auswaehlt. das label stoert
        auf dem spielfeld"). The name moved to the left column's own selection
        box - see action_panel._draw_selection_header(), which shows the same
        string plus the unit's art. The plate had to sit over the board to be
        near its unit, and over the board is where the terrain, the enemy and
        every other overlay are; the panel has room for it and is where the
        player is already reading about the selected unit.

        The RINGS stay, and they are what the plate was really for: they say
        which models are the subject. The anchor ring is deliberately the
        brighter of the two - line of sight is measured FROM the anchor model
        (see main.py's visibility block), so which model it is remains real
        information."""
        if selection is None or selection.squad is None:
            return
        self.draw_squad_outline(
            surface, board, selection.squad, SELECTION_OUTLINE_COLOR,
            SELECTION_OUTLINE_BUMP_PX, SELECTION_OUTLINE_WIDTH_PX,
        )
        anchor = selection.model
        if anchor is not None:
            px, py = board.to_px(anchor.x_in, anchor.y_in)
            r_px = board.in_to_px_len(anchor.radius_in) + self._ring_bump(SELECTION_ANCHOR_BUMP_PX)
            pygame.draw.circle(
                surface, SELECTED_MODEL_COLOR, (round(px), round(py)), round(r_px),
                width=self._ring_width(SELECTION_ANCHOR_WIDTH_PX),
            )

    def draw_returning_models(self, surface, board, models):
        """A double white ring around each model a PARTIAL placement is putting
        back on the board (rule 01.02.03).

        A MODEL list, not a squad, because that is the whole point: the unit is
        already standing and only these one or two bases are new. Same shape as
        draw_damage_choice_highlight() one method up, which rings a candidate
        list for the same reason.

        Dead models are drawn like everywhere else here - remove_dead_models()
        runs once per frame, so filtering would make the rings flicker for one
        frame against a list that still contains them (Fehlerklasse 12)."""
        if not models:
            return
        bump = self._ring_bump(RETURNING_MODEL_BUMP_PX)
        gap = self._ring_bump(RETURNING_MODEL_GAP_PX)
        width = self._ring_width(RETURNING_MODEL_WIDTH_PX)
        for model in models:
            px, py = board.to_px(model.x_in, model.y_in)
            base_px = board.in_to_px_len(model.radius_in)
            for extra in (bump, bump + gap):
                pygame.draw.circle(surface, RETURNING_MODEL_COLOR,
                                   (round(px), round(py)), round(base_px + extra),
                                   width=width)

    def draw_placement_identity(self, surface, board, squad, placing_models=None):
        """Which unit is being placed, drawn on the board during a Set Up.

        Rule 03.01's placement showed only the green/red legality mask: the
        unit's name was in the left panel and NOTHING on the board itself said
        which models the mask belonged to.

        THIS ONE KEEPS ITS NAME PLATE, where a click-selection no longer has
        one. The two look alike but answer different questions: a selection is
        something the player just did and can re-read in the left column's
        selection box at any time, while a placement is something the SEQUENCER
        handed them - it names a unit they did not pick, out of a pool, and
        during the pre-game the left column is showing the placement flow
        rather than a selection. Taking the plate off here would leave the
        green/red mask with nothing saying whose it is, which is the gap this
        method was added to close.

        `placing_models` is the SUBSET this placement owns, when it owns one -
        rule 01.02.03's model return. Then the unit outline alone is a lie by
        omission (it rings the survivors just as brightly as the two models
        that just came back), so those get their own double white ring and the
        plate counts them. Passing None, or the whole unit, keeps the old
        picture exactly - which is what every other Set Up wants."""
        self.draw_squad_outline(
            surface, board, squad, SELECTION_OUTLINE_COLOR,
            SELECTION_OUTLINE_BUMP_PX, SELECTION_OUTLINE_WIDTH_PX,
        )
        returning = [m for m in (placing_models or []) if m in squad.models]
        partial = bool(returning) and len(returning) < len(squad.models)
        if partial:
            self.draw_returning_models(surface, board, returning)
        # Anchored over the RETURNING models when there are some: they are what
        # has to be dragged, and the survivors can be anywhere on the board.
        self._draw_selection_label(
            surface, board, squad,
            text=(f"{squad.name} - place {len(returning)} returning model"
                  f"{'s' if len(returning) != 1 else ''}") if partial else None,
            over=returning if partial else None,
        )

    def _draw_selection_label(self, surface, board, squad, text=None, over=None):
        """The selected unit's name, on a plate above its topmost model.

        The name was already in the left panel (action_panel.py's
        "{squad.name} ({n})"), and this is deliberately the SAME string - the
        board and the panel must not disagree about which unit is picked, and a
        squad name carries the owner digit plus a copy number precisely so two
        units off one datasheet can be told apart.

        Anchored above the topmost model rather than at the centroid, because
        the centroid of a blob sits underneath its own models. Placed with
        _clamp_rect_to_surface() for the reason that helper was written: a unit
        at the board edge would otherwise have its label silently cropped."""
        models = list(over) if over else (
            [m for m in squad.models if not m.is_dead()] or list(squad.models))
        if not models:
            return
        avg_x = sum(m.x_in for m in models) / len(models)
        avg_y = sum(m.y_in for m in models) / len(models)
        centroid = board.to_px(avg_x, avg_y)
        top_px = min(
            board.to_px(m.x_in, m.y_in)[1] - board.in_to_px_len(m.radius_in)
            for m in models
        )
        label_surf = self.font.render(
            text if text else f"{squad.name} ({len(squad.models)})",
            True, RETURNING_MODEL_COLOR if text else SELECTED_MODEL_COLOR)
        bg_rect = label_surf.get_rect(
            midbottom=(round(centroid[0]), round(top_px - self._ring_bump(4.0)))
        ).inflate(10, 6)
        bg_rect = self._clamp_rect_to_surface(bg_rect, surface)
        pygame.draw.rect(surface, SELECTION_LABEL_BG_COLOR, bg_rect, border_radius=4)
        surface.blit(label_surf, label_surf.get_rect(center=bg_rect.center))

    def draw_forbidden_engagement_ranges(self, surface, board, movement_controller, all_tokens):
        """Später-Liste: while a unit is being moved, show the Engagement
        Range of every enemy unit it is NOT allowed to end its move inside,
        as a faint red danger zone. Which enemies count as "forbidden"
        depends on the move type (rule 09.05/09.06 for a normal move,
        11.04 for a charge - see confirm_move()'s validation):
        - normal move (move_mode is None): engaging ANY enemy is illegal,
          so every enemy unit gets a circle.
        - charge (move_mode == "charge"): only engaging a NON-charge-target
          enemy is illegal (you're required to end engaged with your
          declared targets, so those get no circle).
        - pile-in/consolidate: neither forbids touching an extra enemy unit
          beyond the ones already required, so nothing is drawn.
        """
        if movement_controller.state != movement.MOVING or movement_controller.selected_squad is None:
            return
        squad = movement_controller.selected_squad
        move_mode = movement_controller.move_mode

        if move_mode in ("pile_in", "consolidate"):
            return

        allowed_targets = set(movement_controller.charge_targets) if move_mode == "charge" else set()

        overlay = self._reusable_overlay("forbidden_engagement", surface.get_size())
        for token in all_tokens:
            if token.squad is None or token.squad.owner == squad.owner or token.squad in allowed_targets:
                continue
            cx, cy = board.to_px(token.x_in, token.y_in)
            # Engagement Range itself, measured from this enemy's base EDGE -
            # so the ring is exactly 2" wide and the rule to read off it is
            # "don't touch it with your base", which is what rule 03.04
            # actually says (Squad.is_engaged() uses edge_distance()).
            #
            # It used to also add the moving unit's own widest base radius,
            # making the ring the keep-out zone for a model's CENTRE instead.
            # Same forbidden set, but the user has to hold the conversion in
            # their head while dragging - "die roten kreise der gegner ... sind
            # gerade größer als 2 zoll. meine models dürfen sie mit der base
            # mitte nicht betreten. kannst du das so ändern, dass sie genau 2"
            # sind und ich sie mit dem baserand nicht betreten darf? das ist
            # intuitiver".
            #
            # It is also strictly more accurate for an attached unit (19.01),
            # which mixes base sizes: the old ring had to be sized off the
            # WIDEST model in the squad and so over-painted the zone for every
            # smaller one. Each model now brings its own base to the same ring.
            radius_px = board.in_to_px_len(token.radius_in + ENGAGEMENT_RANGE_IN)
            pygame.draw.circle(overlay, ENGAGEMENT_WARNING_COLOR, (round(cx), round(cy)), round(radius_px))
        surface.blit(overlay, (0, 0))

    def draw_contagion_aura(self, surface, board, all_tokens, reach_of=None):
        """The DEATH GUARD army rule's Contagion Range, as a faint green layer.

        User request: "fuer deathguard spezifische aura, die alle einheiten
        haben haette ich gerne einen ganz subtilen gruenen layer. aehnlich wie
        die anzeige der gegnerischen engagement range beim movement."

        Built exactly like draw_forbidden_engagement_ranges() above - one
        reusable SRCALPHA overlay, one filled circle per model, blitted once -
        with two differences that both follow from what it shows:

          * IT IS ALWAYS ON. The engagement warning appears only while a unit
            is being dragged, because it answers a question you are asking at
            that moment. Contagion Range is a standing property of the board:
            it decides Toughness, saves, Movement, Leadership and Objective
            Control for everything inside it, in every phase. So it is drawn
            unconditionally, and is correspondingly fainter.
          * THE RADIUS IS MEASURED FROM THE BASE EDGE, like the engagement
            ring and for the same reason: the rule is "within Contagion Range
            of a DEATH GUARD MODEL", which nurgles_gift._gap() measures edge to
            edge. A ring drawn from the centre would be a different circle from
            the one the rule uses.

        `reach_of(squad) -> inches` is supplied by main.py so the ONE range
        this draws is the one the rule reads - bonuses (Blooming Pestilence)
        and the 12" cap included. Without it the aura is simply not drawn,
        which is the right degradation: a renderer that guessed the range would
        be a second, quietly diverging answer to the question the controller
        already owns.

        THE CIRCLES ARE DRAWN OPAQUE AND THE WHOLE LAYER IS BLITTED ONCE at
        CONTAGION_AURA_ALPHA, which is the one real difference from the
        engagement warning - and it is forced by the numbers. That overlay
        paints a handful of 2" circles; this one paints up to 49 circles of up
        to 12". Drawn as translucent circles they stack, and the union comes
        out as a patchwork of hotspots where models happen to cluster - which
        says nothing about the rule, since being inside the aura twice is the
        same as being inside it once. Painting the union opaque and fading it
        once gives one flat, even tint that means exactly what Afflicted means.
        Measured, not assumed: a real map2 frame at alpha 34 was invisible over
        the sand ground, and at 90 it read as a colour wash over the terrain.
        """
        if reach_of is None:
            return
        overlay = self._reusable_overlay("contagion_aura", surface.get_size())
        drawn = False
        for token in all_tokens or ():
            squad = getattr(token, "squad", None)
            if squad is None or token.is_dead():
                continue
            if not getattr(token.profile, "nurgles_gift", False):
                continue
            reach = reach_of(squad)
            if not reach:
                continue
            cx, cy = board.to_px(token.x_in, token.y_in)
            radius_px = board.in_to_px_len(token.radius_in + reach)
            pygame.draw.circle(overlay, CONTAGION_AURA_COLOR,
                               (round(cx), round(cy)), round(radius_px))
            drawn = True
        if drawn:
            overlay.set_alpha(CONTAGION_AURA_ALPHA)
            surface.blit(overlay, (0, 0))
            # _reusable_overlay() hands the same Surface back next frame, and
            # set_alpha persists on it - harmless here (it is set again above)
            # but reset anyway, so a future second user of this overlay cannot
            # inherit a fade it never asked for.
            overlay.set_alpha(None)

    def draw_range_aura(self, surface, board, squad, radius_in, model=None):
        """The range ruler: one flat white ring of `radius_in` around the
        PICKED MODEL - or around the whole unit when no single model is
        anchored (user: "wenn man einen dieser knoepfe aktiviert, dann wird bei
        angewaehlten modellen die entsprechende Aura subtil angezeigt. optisch
        wie die deathguard Aura, aber in weiss. das hilft bei Reichweiten").

        ONE MODEL WHEN ONE WAS CLICKED, and that is a correction: this used to
        ring every model of the unit, which for a twenty-Warrior blob is a
        blanket rather than a measurement. User: "die Aura Funktion zeigt
        momentan fuer jedes Modell im Squad die Aura an. wenn ich ein
        spezifisches Modell anklicke soll nur die Aura dieses Modells angezeigt
        werden." The union of twenty rings answers "could ANY of us reach it",
        which is rarely the question - the range being measured almost always
        belongs to one model (a weapon, an aura, a charge from where that model
        stands).

        `model=None` still rings the unit, and that is not a leftover: the
        selection can be set WITHOUT a model anchor (MovementController.
        start_scout_move() and game/torchstar_gambit.py both write
        selected_squad directly), and in that state there is no "clicked model"
        to honour. Falling back to the unit is what the ruler did before, so
        those paths are unchanged rather than silently emptied.

        Built exactly like draw_contagion_aura() above, which is what "optisch
        wie die deathguard Aura" asks for, and it inherits that method's one
        hard-won detail: the circles are drawn OPAQUE into a reusable overlay
        and the whole thing is faded ONCE. A unit is up to twenty-odd models,
        so translucent circles would stack into a patchwork of hotspots wherever
        models happen to be packed - which says nothing about distance, since
        being within 6" of two models is the same as being within 6" of one.
        The union, flat, is exactly the shape the question has.

        Two differences from the Death Guard aura, both deliberate:

          * IT IS NOT ALWAYS ON. Contagion Range is a standing property of the
            board; this is a measuring instrument, and it answers only for the
            unit you picked. Nothing is drawn without a selection - "es sollen
            immer nur die auren der ausgewaehlten Modelle angezeigt werden".
          * WHITE, and fainter still. Green means Nurgle's Gift and nothing
            else; a ruler must not read as a rule. White also stays neutral
            against all four biomes, which a hue would not.

        THE RADIUS IS MEASURED FROM THE BASE EDGE, like the engagement ring and
        the contagion aura, because that is how this game measures: base to
        base. So the circle drawn is where a point would be within `radius_in`
        of this model's base - the same approximation those two make, and worth
        naming, since a target model's own base makes the true edge-to-edge
        distance shorter still.
        """
        if squad is None or not radius_in:
            return
        # The anchor only speaks for a unit it actually belongs to. Writing
        # selected_squad directly leaves the previous pick's model behind, and
        # ringing THAT would put the ruler on a unit the player is not looking
        # at - worse than the blanket this replaces.
        models = squad.models
        if model is not None and model.squad is squad:
            models = [model]
        overlay = self._reusable_overlay("range_aura", surface.get_size())
        drawn = False
        for token in models:
            if token.is_dead():
                continue
            cx, cy = board.to_px(token.x_in, token.y_in)
            radius_px = board.in_to_px_len(token.radius_in + radius_in)
            pygame.draw.circle(overlay, RANGE_AURA_COLOR,
                               (round(cx), round(cy)), round(radius_px))
            drawn = True
        if not drawn:
            return
        overlay.set_alpha(RANGE_AURA_ALPHA)
        surface.blit(overlay, (0, 0))
        # Same reset as the contagion aura's: _reusable_overlay() hands the
        # same Surface back next frame and set_alpha persists on it.
        overlay.set_alpha(None)

    def draw_move_range(self, surface, board, movement_controller):
        if movement_controller.state != movement.MOVING or movement_controller.selected_squad is None:
            return

        overlay = self._reusable_overlay("move_range", surface.get_size())
        for model in movement_controller.selected_squad.models:
            waypoint = movement_controller.last_waypoint.get(model.id)
            remaining = movement_controller.remaining_range.get(model.id)
            if waypoint is None or remaining is None:
                continue
            cx, cy = board.to_px(*waypoint)
            radius_px = board.in_to_px_len(remaining)
            pygame.draw.circle(
                overlay, RANGE_CIRCLE_COLOR, (round(cx), round(cy)), round(radius_px), width=2
            )
        surface.blit(overlay, (0, 0))

    def draw_move_feedback(self, surface, board, movement_controller, dragging_token):
        if dragging_token is None:
            return

        origin = movement_controller.last_waypoint.get(dragging_token.id)
        if origin is None:
            return

        ox_in, oy_in = origin
        ox_px, oy_px = board.to_px(ox_in, oy_in)
        cx_px, cy_px = board.to_px(dragging_token.x_in, dragging_token.y_in)

        dist_in = ((dragging_token.x_in - ox_in) ** 2 + (dragging_token.y_in - oy_in) ** 2) ** 0.5

        pygame.draw.line(surface, MEASURE_LINE_COLOR, (ox_px, oy_px), (cx_px, cy_px), width=1)
        self._draw_distance_label(surface, dist_in, (ox_px, oy_px), (cx_px, cy_px))

    def draw_line_drag(self, surface, board, input_manager):
        """The line being dragged, and what it produced.

        Deliberately its OWN colour rather than the ruler's white: ALT can be
        held during a right-drag, so both markings can be on screen at once,
        and two things that mean different things must not read as the same
        thing. Amber normally, the established red once rule 09.02's spread is
        broken - nothing is prevented, per the user's decision that the drag
        stays free and Confirm is what refuses.

        Widths go through _ring_width(). The width=1 calls in draw_measure_tool
        below are the generation BEFORE that correction existed and are not a
        precedent to copy: raw, a 2px line lands under one screen pixel here.

        THE READOUT SPLITS REQUESTED FROM ACHIEVED, and that is the whole
        honesty of it. Frontage and rank count are what the GESTURE asked for,
        because that is what the player is steering. The spread is measured off
        the real positions after the clamp, because that is the number
        check_coherency() will judge at Confirm - reporting the requested one
        would be a green readout over a formation that is going to be
        rejected."""
        if not input_manager.line_drag_active:
            return
        start_in = input_manager.line_drag_start_in
        end_in = input_manager.line_drag_end_in or start_in
        info = input_manager.line_drag_info

        over = info is not None and (info.over_limit or info.split)
        color = LINE_DRAG_WARN_COLOR if over else LINE_DRAG_COLOR
        width = self._ring_width(LINE_DRAG_WIDTH_PX)

        ax, ay = board.to_px(*start_in)
        bx, by = board.to_px(*end_in)
        pygame.draw.line(surface, color, (round(ax), round(ay)), (round(bx), round(by)), width=width)

        # End caps: short perpendicular ticks, so the frontage reads as a
        # measured segment rather than as an arrow pointing somewhere.
        dx, dy = bx - ax, by - ay
        length_px = math.hypot(dx, dy)
        if length_px > 1e-6:
            cap = board.in_to_px_len(LINE_DRAG_CAP_IN)
            nx, ny = -dy / length_px * cap, dx / length_px * cap
            for px_, py_ in ((ax, ay), (bx, by)):
                pygame.draw.line(surface, color,
                                 (round(px_ - nx), round(py_ - ny)),
                                 (round(px_ + nx), round(py_ + ny)), width=width)

        if info is None:
            return
        lines = [f'{info.length_in:.1f}" front',
                 f"{info.frontage} wide x {info.ranks} deep"]
        if info.limit_in is not None:
            lines.append(f'spread {info.widest_in:.1f}" of {info.limit_in:.0f}"')
        if info.legal_frontages:
            legal = info.legal_frontages
            lines.append(f"legal: {legal[0]}-{legal[-1]} wide"
                         if legal[-1] - legal[0] + 1 == len(legal)
                         else "legal: " + ",".join(str(f) for f in legal))
        if info.short:
            lines.append(f"{info.short} cannot reach")
        if info.split:
            lines.append(f"SPLIT into {info.groups} groups")
        self._draw_line_drag_readout(surface, lines, (bx, by), over)

    def _draw_line_drag_readout(self, surface, lines, at_px, over):
        """Anchored at the CURSOR end, not the midpoint: the midpoint is where
        the ruler puts its own label and where the models now stand, and a
        number 400 px away from the hand steering the line is a number nobody
        reads."""
        text_color = LINE_DRAG_WARN_COLOR if over else LINE_DRAG_COLOR
        surfaces = [self.font.render(line, True, text_color) for line in lines]
        pad = 6
        w = max(s.get_width() for s in surfaces) + 2 * pad
        h = sum(s.get_height() for s in surfaces) + 2 * pad
        rect = pygame.Rect(round(at_px[0]) + 12, round(at_px[1]) + 12, w, h)
        rect = self._clamp_rect_to_surface(rect, surface)
        pygame.draw.rect(surface, LINE_DRAG_LABEL_BG_COLOR, rect, border_radius=4)
        y = rect.y + pad
        for s in surfaces:
            surface.blit(s, (rect.x + pad, y))
            y += s.get_height()

    def draw_measure_tool(self, surface, board, input_manager):
        if not input_manager.measuring or input_manager.measure_origin_in is None:
            return

        origin_token = input_manager.measure_origin_token
        hovered_token = input_manager.hovered_token

        if origin_token is not None and hovered_token is not None and hovered_token is not origin_token:
            self._draw_model_distance(surface, board, origin_token, hovered_token)
        else:
            origin_radius_in = origin_token.radius_in if origin_token is not None else 0.0
            self._draw_freehand_distance(
                surface, board, input_manager.measure_origin_in, origin_radius_in, input_manager.mouse_pos_in
            )

    def _draw_freehand_distance(self, surface, board, origin_in, origin_radius_in, current_in):
        ox_px, oy_px = board.to_px(*origin_in)
        cx_px, cy_px = board.to_px(*current_in)

        center_dist_in = (
            (current_in[0] - origin_in[0]) ** 2 + (current_in[1] - origin_in[1]) ** 2
        ) ** 0.5
        dist_in = max(0.0, center_dist_in - origin_radius_in)

        pygame.draw.line(surface, MEASURE_LINE_COLOR, (ox_px, oy_px), (cx_px, cy_px), width=1)
        self._draw_distance_label(surface, dist_in, (ox_px, oy_px), (cx_px, cy_px))

    def _draw_model_distance(self, surface, board, token_a, token_b):
        ax_px, ay_px = board.to_px(token_a.x_in, token_a.y_in)
        bx_px, by_px = board.to_px(token_b.x_in, token_b.y_in)

        center_dist_in = (
            (token_b.x_in - token_a.x_in) ** 2 + (token_b.y_in - token_a.y_in) ** 2
        ) ** 0.5
        edge_dist_in = max(0.0, center_dist_in - token_a.radius_in - token_b.radius_in)

        pygame.draw.line(surface, MEASURE_LINE_COLOR, (ax_px, ay_px), (bx_px, by_px), width=1)
        self._draw_distance_label(surface, edge_dist_in, (ax_px, ay_px), (bx_px, by_px))

    def _draw_distance_label(self, surface, dist_in, point_a_px, point_b_px):
        label = f'{dist_in:.1f}"'
        text_surf = self.font.render(label, True, MEASURE_TEXT_COLOR)

        mid_x = (point_a_px[0] + point_b_px[0]) / 2
        mid_y = (point_a_px[1] + point_b_px[1]) / 2
        label_pos = (round(mid_x) + 6, round(mid_y) - 18)

        bg_rect = text_surf.get_rect(topleft=label_pos).inflate(6, 4)
        pygame.draw.rect(surface, MEASURE_TEXT_BG, bg_rect)
        surface.blit(text_surf, label_pos)
