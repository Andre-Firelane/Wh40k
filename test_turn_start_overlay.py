"""The "PLAYER 2 TURN 1" banner, and the faction logo on it.

User: "es gibt ja den promt, der anzeigt, wer jetzt am zug ist. 'Player 2,
Turn 1' baue dort bitte auch das fraktions Logo ein."

THERE WAS NO TEST FOR THIS OVERLAY AT ALL before this - which is the usual
reason a drawing bug survives here, so the suite covers the banner itself and
not only the addition.

Measured on PIXELS rather than against the constants that produced them: a
check that recomputes the layout formula agrees with itself whatever the
formula says. What is asserted is that the box really grew, that the artwork
really landed inside the reserved tile, that the heading was not covered by it,
and that a faction with no art still gets a badge rather than an empty square.
"""

import io
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()
pygame.font.init()
pygame.display.set_mode((200, 200))

import testkit as tk  # noqa: E402
from game import sprites  # noqa: E402
from game.ui import faction_badge  # noqa: E402
from game.ui import game_status_panel as gsp  # noqa: E402
from game.ui import turn_start_overlay as tso  # noqa: E402

checks = tk.Checks("Turn start overlay")

HERE = os.path.dirname(os.path.abspath(__file__))
SIZE = (1280, 720)
GROUND = (9, 13, 17)
# A faction this build really fields, and one that exists nowhere - so the
# artwork path and the placeholder path are both driven by something honest.
REAL = "NECRONS"
NO_ART = "NO SUCH FACTION"


def render(**kwargs):
    surface = pygame.Surface(SIZE)
    surface.fill(GROUND)
    overlay = tso.TurnStartOverlay()
    overlay.show("Player 2", 1, **kwargs)
    overlay.draw(surface)
    return surface


def ink_rows(surface):
    """The y range the banner really occupies. The overlay dims the whole
    window, so "not the background colour" is every pixel - the box is found by
    its own brightness instead, which is what a player sees."""
    rows = []
    for y in range(surface.get_height()):
        for x in range(surface.get_width()):
            r, g, b = surface.get_at((x, y))[:3]
            if r + g + b > 150:
                rows.append(y)
                break
    return (min(rows), max(rows)) if rows else None


def ink_cols(surface, y0, y1, x0=0, x1=None):
    cols = []
    for x in range(x0, x1 if x1 is not None else surface.get_width()):
        for y in range(y0, y1):
            r, g, b = surface.get_at((x, y))[:3]
            if r + g + b > 150:
                cols.append(x)
                break
    return (min(cols), max(cols)) if cols else None


def inside(surface, top, bottom):
    """The x range strictly INSIDE the banner's own frame.

    Without this every band measurement also picks up the box border, which
    runs the full height of the banner - so "the artwork fits in its tile"
    would be measuring a 460px box instead of a 76px tile."""
    edges = ink_cols(surface, top, bottom)
    return (edges[0] + 6, edges[1] - 5) if edges else (0, surface.get_width())


# --- 1. the banner still says who is on turn --------------------------------
print("--- 1. the banner ---")

plain = render()
checks.true("a banner with no faction still draws", ink_rows(plain) is not None)

overlay = tso.TurnStartOverlay()
checks.eq("nothing pending to start with", overlay.is_pending, False)
overlay.show("Player 2", 1, faction_keyword=REAL)
checks.true("showing it makes it pending", overlay.is_pending)
overlay.dismiss()
checks.eq("dismissing clears it", overlay.is_pending, False)
# The badge has to go with it. A kept logo would be drawn on the NEXT banner -
# the other player's turn, with the wrong army's badge on it.
checks.eq("...and lets go of the faction too", overlay._keyword, None)
checks.eq("...and of its artwork", overlay._logo_path, None)


# --- 2. the logo is really on it --------------------------------------------
print("--- 2. the logo ---")

with_logo = render(faction_keyword=REAL)
plain_top, plain_bottom = ink_rows(plain)
logo_top, logo_bottom = ink_rows(with_logo)
plain_height = plain_bottom - plain_top
logo_height = logo_bottom - logo_top
checks.true("the banner grows to make room for the badge", logo_height > plain_height)
# By about the tile, not by an arbitrary amount - so a badge that is reserved
# but not drawn, or drawn outside its reservation, shows up here.
reserved = tso.BADGE_TOP_GAP + tso.BADGE_BOX + tso.BADGE_BOTTOM_GAP
checks.true(f"...by about the reserved tile block (grew {logo_height - plain_height})",
            abs((logo_height - plain_height) - reserved) <= 4)

# There is ink inside the tile band itself - i.e. something was actually drawn
# there, not just space left for it.
band_top = logo_top + tso.BADGE_TOP_GAP
band_bottom = band_top + tso.BADGE_BOX
box_x0, box_x1 = inside(with_logo, logo_top, logo_bottom)
cols = ink_cols(with_logo, band_top + 4, band_bottom - 4, box_x0, box_x1)
checks.true("the tile band really has artwork in it", cols is not None)
if cols is not None:
    centre = (cols[0] + cols[1]) / 2
    checks.true(f"...and it is centred on the banner (centre {centre:.0f})",
                abs(centre - SIZE[0] / 2) <= 6)
    checks.true("...and it fits inside the tile", cols[1] - cols[0] <= tso.BADGE_BOX + 8)

# The heading is BELOW the tile, not under it: a banner whose own text the
# badge covers is worse than one with no badge.
heading_band = ink_cols(with_logo, band_bottom + tso.BADGE_BOTTOM_GAP,
                        band_bottom + tso.BADGE_BOTTOM_GAP + 30, box_x0, box_x1)
checks.true("the heading bar is still drawn, below the tile", heading_band is not None)

# Two different factions must not render the same picture - otherwise the badge
# is a decoration rather than information.
other = render(faction_keyword="ORKS")
checks.true("a different faction draws a different badge",
            pygame.image.tostring(with_logo, "RGB") != pygame.image.tostring(other, "RGB"))

# It has to be the ARTWORK, not the two-letter placeholder. Nothing above could
# tell them apart - both are ink in the tile, and two factions differ either
# way - so the same faction is rendered twice with only its art taken away.
# Reaching into _logo_path is the only way to stage "this file is missing"; the
# alternative is a check that passes for a banner showing "NE".
checks.true("the faction really has a logo file",
            sprites.faction_logo_path(REAL) is not None)
starved = pygame.Surface(SIZE)
starved.fill(GROUND)
_o = tso.TurnStartOverlay()
_o.show("Player 2", 1, faction_keyword=REAL)
_o._logo_path = None
_o.draw(starved)
checks.true("the banner draws the ARTWORK, not the monogram",
            pygame.image.tostring(with_logo, "RGB") != pygame.image.tostring(starved, "RGB"))


# --- 3. a faction with no art still gets a badge ----------------------------
print("--- 3. the placeholder ---")

checks.eq("the test's stand-in really has no logo file",
          sprites.faction_logo_path(NO_ART), None)
mono = render(faction_keyword=NO_ART)
mono_top, mono_bottom = ink_rows(mono)
checks.true("it still reserves the tile", (mono_bottom - mono_top) > plain_height)
mono_x0, mono_x1 = inside(mono, mono_top, mono_bottom)
mono_cols = ink_cols(mono, mono_top + tso.BADGE_TOP_GAP + 4,
                     mono_top + tso.BADGE_TOP_GAP + tso.BADGE_BOX - 4, mono_x0, mono_x1)
checks.true("...and draws the monogram in it", mono_cols is not None)
checks.eq("the monogram is the shared one", faction_badge.monogram(NO_ART), "NS")

# And a faction the game cannot name at all draws NO tile - an empty framed
# square reads as art that failed to load.
checks.eq("no keyword, no tile", faction_badge.has_content(None, None), False)
checks.eq("...which is why the plain banner is the short one",
          ink_rows(render(faction_keyword=None))[1] - ink_rows(render(faction_keyword=None))[0],
          plain_height)


# --- 4. one badge, two callers ----------------------------------------------
print("--- 4. the extraction ---")

# The Game Status panel re-exports rather than re-implements, so the panel and
# the banner cannot disagree about what a faction tile is.
checks.true("the panel's monogram IS the shared one",
            gsp._faction_monogram is faction_badge.monogram)
for name in ("LOGO_PADDING", "ACTIVE_BORDER_WIDTH", "ACTIVE_GLOW_COLOR",
             "MONOGRAM_LENGTH", "MONOGRAM_COLOR", "MONOGRAM_FONT_SIZES"):
    checks.eq(f"the panel re-exports {name}", getattr(gsp, name),
              getattr(faction_badge, name))
checks.true("the panel's tile size is its OWN, not the shared module's",
            not hasattr(faction_badge, "LOGO_BOX"))
checks.true("the banner picks a bigger tile than the 200px column does",
            tso.BADGE_BOX > gsp.LOGO_BOX)

PANEL_SRC = io.open(os.path.join(HERE, "game/ui/game_status_panel.py"), encoding="utf-8").read()
checks.true("the panel draws through the shared function",
            "faction_badge.draw(surface, tile_rect, logo_path, active, keyword)" in PANEL_SRC)
checks.true("...and letters through the shared one too",
            "return faction_badge.font_for(text, box_px)" in PANEL_SRC)


# --- 5. wiring: ONE derivation of who fields what ---------------------------
print("--- 5. wiring ---")

MAIN = io.open(os.path.join(HERE, "main.py"), encoding="utf-8").read()
checks.eq("main.py derives the factions in one helper",
          MAIN.count("def current_player_factions():"), 1)
checks.eq("...and nowhere else", MAIN.count("derive_player_factions(_all_squads("), 1)
checks.true("the banner is handed the turn owner's faction",
            "faction_keyword=current_player_factions().get(turn_tracker.turn_owner)" in MAIN)
checks.true("...and the status panel reads the same derivation",
            "player_factions=current_player_factions()" in MAIN)

checks.finish()
