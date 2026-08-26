import pygame

from game import config, movement, sprites, status_effects
from game.placement_overlay import PlacementOverlay
from game.squad import ENGAGEMENT_RANGE_IN, strongest_model
from game.terrain import DENSE, EXPOSED, LIGHT
from game.ui.text_utils import wrap_text

RANGE_CIRCLE_COLOR = (255, 255, 255, 70)
ENGAGEMENT_WARNING_COLOR = (255, 40, 40, 70)
MEASURE_LINE_COLOR = (255, 255, 255)
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
SHOOT_TARGET_COLOR = (255, 120, 0)
COHERENCY_REMOVAL_COLOR = (200, 20, 20)
DAMAGE_CHOICE_COLOR = (255, 210, 0)
ASSIGNING_MODEL_COLOR = (190, 60, 230)
OWN_ARMY_COLOR = (60, 120, 240)  # User: "ändere die farbe der eigenen bases von grün zu blau. gegner bleibt rot" - was (40, 200, 60). Deliberately a deep blue rather than anything near SELECTED_MODEL_COLOR's cyan, which is drawn as a thicker ring 6 px OUTSIDE this rim (see draw_selected_model) and would otherwise read as the same colour twice.
ENEMY_ARMY_COLOR = (220, 40, 40)
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
DEPLOYMENT_ZONE_LINE_COLORS = {
    "Player 1": (90, 150, 230, 150),
    "Player 2": (230, 90, 90, 150),
}
DEPLOYMENT_ZONE_FALLBACK_COLOR = (150, 150, 150, 150)
DEPLOYMENT_ZONE_LINE_WIDTH = 2
BOARD_EDGE_LINE_WIDTH = 5  # thicker highlight along a zone's own board edge - "Zuordnung der Spielfeldkanten"


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

    def _ring_width(self, on_screen_px):
        """A stroke width given in ON-SCREEN pixels, converted to the board
        surface's own (supersampled) render resolution - the same
        correction the fonts get in __init__, and for the same reason. At
        least 1, so a thin rim never rounds away to nothing."""
        return max(1, round(on_screen_px * self.render_scale))

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

    def draw(self, surface, board, tokens, obstacles=(), active_player=None, deployment_zones=(), blood_decals=(), terrain_areas=()):
        surface.blit(self._cached_static_layer(board, obstacles, terrain_areas, deployment_zones), (0, 0))
        self.draw_blood_decals(surface, board, blood_decals)
        self._draw_tokens(surface, board, tokens, active_player)

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

        dense_cover_path = sprites.dense_cover_texture_path()
        normal_cover_path = sprites.normal_cover_texture_path()

        # Two passes, in this order, so a ruin's Dense walls render as solid
        # blocks sitting cleanly on top of its Exposed/Light footprint
        # (e.g. rubble/floor) rather than the floor's translucent tint
        # washing back out over the walls drawn beneath it.
        terrain_overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for area in terrain_areas:
            # User: Dense_Cover for a footprint that has a wall (Dense
            # feature) standing on it (a ruin's floor), Normal_Cover for a
            # footprint with no wall at all (a standalone barricade/crater) -
            # picked once per TerrainArea, not per feature, since that's the
            # whole "terrain area" a wall does or doesn't belong to.
            cover_path, cover_tile_size_in = (
                (dense_cover_path, DENSE_COVER_TILE_SIZE_IN) if area.has_dense_feature
                else (normal_cover_path, NORMAL_COVER_TILE_SIZE_IN)
            )
            for obstacle in area.features:
                if obstacle.category == DENSE:
                    continue
                top_left = board.to_px(obstacle.min_x, obstacle.min_y)
                width_px = board.in_to_px_len(obstacle.width_in)
                height_px = board.in_to_px_len(obstacle.height_in)
                rect = pygame.Rect(round(top_left[0]), round(top_left[1]), round(width_px), round(height_px))
                if cover_path is not None:
                    # Drawn straight onto `surface`, at TERRAIN_TILE_ALPHA
                    # rather than fully opaque, so the base Ground tile
                    # underneath still shows through a little (less contrast
                    # against the surrounding ground than a flat opaque tile).
                    self._tile_texture(
                        surface, cover_path, board, rect, cover_tile_size_in, alpha=TERRAIN_TILE_ALPHA,
                    )
                    continue
                if obstacle.category == LIGHT and self._is_barricade_shaped(obstacle):
                    color = BARRICADE_COLOR
                else:
                    color = TERRAIN_COLORS.get(obstacle.category, OBSTACLE_COLOR)
                # Fallback (no cover tile texture present): translucent flat
                # color overlay instead of a solid block - a visual cue that
                # models can move onto and end their move on this terrain.
                pygame.draw.rect(terrain_overlay, (*color, 140), rect)
        surface.blit(terrain_overlay, (0, 0))

        for obstacle in obstacles:
            if obstacle.category != DENSE:
                continue
            top_left = board.to_px(obstacle.min_x, obstacle.min_y)
            width_px = board.in_to_px_len(obstacle.width_in)
            height_px = board.in_to_px_len(obstacle.height_in)
            rect = pygame.Rect(round(top_left[0]), round(top_left[1]), round(width_px), round(height_px))
            # Dense terrain is drawn as a solid, opaque block - it's a real
            # obstacle, matching how it behaves for LoS (movement depends on
            # the specific model, rule 13.06 - see Obstacle.blocks_movement_for()).
            pygame.draw.rect(surface, TERRAIN_COLORS.get(DENSE, OBSTACLE_COLOR), rect)
        return surface

    def _draw_ground(self, surface, board):
        """Später-Liste (Sprites): the battlefield floor
        (Sprites/<sprites.GROUND_TEXTURE_NAME>.<ext>), if the user has
        dropped one in - falls back to the plain BACKGROUND_COLOR fill (as
        before any ground art existed) if there isn't one, same "missing art
        is fine" convention as unit sprites (see game/sprites.py).

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
        ground_path = sprites.ground_texture_path()
        if ground_path is None:
            surface.fill(config.BACKGROUND_COLOR)
            return
        surface.blit(self._ground_image(ground_path, surface.get_size()), (0, 0))

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

    def _tile_texture(self, surface, path, board, rect, tile_size_in, alpha=None):
        """Tiles the image at `path` across `rect` (clipped to it, so this
        also works for a single terrain footprint, not just the whole
        board), each tile sized to `tile_size_in` physical inches - like
        everything else this renderer draws, going through
        board.in_to_px_len() rather than a hardcoded pixel size. Tiles are
        grid-aligned to the SURFACE's own (0,0) origin rather than rect's
        own top-left, so e.g. two separate ruin floor patches show the same
        continuous pattern instead of each restarting it at their own
        corner. `alpha` (0-255, None = fully opaque) blends each tile with
        whatever's already drawn underneath instead of fully replacing it -
        the cached tile Surface is shared across every call for the same
        `path`, so this is applied fresh each call rather than baked in once."""
        tile = self._cached_tile(path, board, tile_size_in)
        if alpha is not None:
            tile.set_alpha(alpha)
        tile_w, tile_h = tile.get_size()
        start_x = (rect.x // tile_w) * tile_w
        start_y = (rect.y // tile_h) * tile_h
        previous_clip = surface.get_clip()
        surface.set_clip(rect)
        for y in range(start_y, rect.bottom, tile_h):
            for x in range(start_x, rect.right, tile_w):
                surface.blit(tile, (x, y))
        surface.set_clip(previous_clip)

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
        Dense_Cover-Desert.jpg turned up and had its stonework squeezed
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

    def _draw_tokens(self, surface, board, tokens, active_player):
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
            color = self._token_color(token, active_player)
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

    def draw_embarked_passengers(self, surface, board, tokens, embarked_squads, active_player=None):
        """Draws a small icon of each embarked squad's strongest model
        (game.squad.strongest_model), at its real on-battlefield size,
        centered on every on-board TRANSPORT token currently carrying one -
        see this module's comment above EMBARKED_ICON_GAP_PX for why. Several squads
        embarked in the same TRANSPORT (rare, but its capacity can allow it)
        are laid out side by side across that same center point rather than
        overlapping. `active_player` is only used for the icon's own team
        color (same blue/own vs red/enemy convention as _token_color()),
        never gates whether it's drawn - the whole point is that this is
        visible regardless of whose turn it is."""
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
                self._draw_embarked_icon(surface, model, squad, round(cx), round(py), r_px, active_player)
                cx += r_px + EMBARKED_ICON_GAP_PX

    def _draw_embarked_icon(self, surface, model, squad, cx, cy, r_px, active_player):
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
            color = self._token_color(model, active_player)
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
        color = DEPLOYMENT_ZONE_LINE_COLORS.get(zone.owner, DEPLOYMENT_ZONE_FALLBACK_COLOR)
        for x_in, y_in, width_in, height_in in zone.rects:
            min_x_in, max_x_in = x_in - width_in / 2, x_in + width_in / 2
            min_y_in, max_y_in = y_in - height_in / 2, y_in + height_in / 2
            top_left = board.to_px(min_x_in, min_y_in)
            width_px = board.in_to_px_len(width_in)
            height_px = board.in_to_px_len(height_in)
            rect = pygame.Rect(round(top_left[0]), round(top_left[1]), round(width_px), round(height_px))
            pygame.draw.rect(overlay, color, rect, width=DEPLOYMENT_ZONE_LINE_WIDTH)

            # "Zuordnung der Spielfeldkanten": a thicker highlight on whichever
            # board edge this rect actually touches (its owner's own edge).
            if abs(min_y_in) < 1e-6:
                edge_y_px = round(board.to_px(0, 0)[1])
                pygame.draw.line(overlay, color, (rect.left, edge_y_px), (rect.right, edge_y_px), width=BOARD_EDGE_LINE_WIDTH)
            if abs(max_y_in - board.height_in) < 1e-6:
                edge_y_px = round(board.to_px(0, board.height_in)[1]) - BOARD_EDGE_LINE_WIDTH
                pygame.draw.line(overlay, color, (rect.left, edge_y_px), (rect.right, edge_y_px), width=BOARD_EDGE_LINE_WIDTH)

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
            min_x, min_y, max_x, max_y = objective.terrain_area.bounding_box
            top_left = board.to_px(min_x, min_y)
            bottom_right = board.to_px(max_x, max_y)
            rect = pygame.Rect(
                round(top_left[0]), round(top_left[1]),
                round(bottom_right[0] - top_left[0]), round(bottom_right[1] - top_left[1]),
            )
            color = OBJECTIVE_COLORS.get(objective.controlled_by, OBJECTIVE_NEUTRAL_COLOR)
            outline_rect = rect.inflate(10, 10)
            pygame.draw.rect(surface, color, outline_rect, width=4, border_radius=10)

            icon_bounds = pygame.Rect(0, 0, icon_radius * 2, icon_radius * 2)
            icon_bounds.center = outline_rect.topleft
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
            bg_rect = label_surf.get_rect(midtop=(rect.centerx, rect.top - 26)).inflate(10, 6)
            bg_rect = self._clamp_rect_to_surface(bg_rect, surface)
            pygame.draw.rect(surface, OBJECTIVE_LABEL_BG_COLOR, bg_rect, border_radius=4)
            surface.blit(label_surf, label_surf.get_rect(center=bg_rect.center))

            if objective.secured_by is not None:
                secured_surf = self.label_font.render(f"SECURED ({objective.secured_by})", True, SECURED_BADGE_TEXT_COLOR)
                secured_bg = secured_surf.get_rect(midtop=(rect.centerx, bg_rect.bottom + 2)).inflate(8, 4)
                secured_bg = self._clamp_rect_to_surface(secured_bg, surface)
                pygame.draw.rect(surface, SECURED_BADGE_COLOR, secured_bg, border_radius=4)
                surface.blit(secured_surf, secured_surf.get_rect(center=secured_bg.center))

    def _token_color(self, token, active_player):
        """The currently active player's own models are blue, everyone
        else's are red - a quick visual reminder of whose turn it is, on top
        of the player banner. Falls back to the token's own color if there's
        no active player to compare against (or no squad, which shouldn't
        happen in practice)."""
        if active_player is None or token.squad is None:
            return token.color
        return OWN_ARMY_COLOR if token.squad.owner == active_player else ENEMY_ARMY_COLOR

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

    def draw_coherency_removal_highlight(self, surface, board, pending_squad):
        if pending_squad is None:
            return
        for model in pending_squad.models:
            px, py = board.to_px(model.x_in, model.y_in)
            r_px = board.in_to_px_len(model.radius_in) + 5
            pygame.draw.circle(
                surface, COHERENCY_REMOVAL_COLOR, (round(px), round(py)), round(r_px), width=3
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

    def draw_placement_overlay(self, surface, board, token, position_valid_fn, session_key):
        """Rules 03.02/20.04: while placing a unit (Set Up or Ingress), show
        where this model could legally end up right now, per
        `position_valid_fn(token, x_in, y_in)` - a one-model-at-a-time
        approximation (it doesn't account for where the rest of the squad
        will end up, e.g. coherency), but enough to see legal ground before
        dragging. `surface` is board_surface (this overlay is in board-local
        pixel space, like other board overlays).

        `session_key` identifies the placement this mask belongs to; the mask
        is built once per (session, base size) and reused for every later
        frame instead of being recomputed - see game/placement_overlay.py for
        why that is exact and what it was costing before."""
        self._placement_overlay.draw(
            surface, board,
            (session_key, round(token.radius_in, 3)),
            lambda x_in, y_in: position_valid_fn(token, x_in, y_in),
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

    def draw_selected_model(self, surface, board, selected_model):
        if selected_model is None:
            return
        px, py = board.to_px(selected_model.x_in, selected_model.y_in)
        r_px = board.in_to_px_len(selected_model.radius_in) + 6
        pygame.draw.circle(
            surface, SELECTED_MODEL_COLOR, (round(px), round(py)), round(r_px), width=3
        )

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
