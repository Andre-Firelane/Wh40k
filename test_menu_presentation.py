"""How the main menu and the picking screens LOOK: bigger type, and artwork
behind the main menu.

Two user asks, one screen family:

  * "Die Font im Main Menu und Auswahl screen darf viel groesser sein"
  * "main-manu-background.jpg als hintergrund im hauptmenue setzen"

The font set is shared - game/ui/tile_screen.py's make_fonts() is read by the
map picker, the army picker AND the game menu - so "bigger" is one change with
three consumers, and the thing that can go wrong is not the size but the boxes
that were measured around the old one: a header bar of fixed height, a footer
whose confirm button GROWS when its label wraps, and a menu panel that has to
stay on a 1280x720 screen. Section 2 measures those at the narrowest window
this game is run at.

The backdrop is the "missing art is fine" convention every lookup in
game/sprites.py follows, plus one thing that is not cosmetic: the veil. Gold
heading text and a bordered panel sit straight on top of a photograph, and
without the veil their contrast is whatever happens to be behind them.

Run: python test_menu_presentation.py
"""

import os
import shutil
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((1280, 720))

from game import config, sprites  # noqa: E402
from game.ui import button_style, tile_screen as ts  # noqa: E402
from game.ui.army_select import ArmySelectScreen  # noqa: E402
from game.ui.game_menu import GameMenu  # noqa: E402
from game.ui.map_select import MapSelectScreen  # noqa: E402
from testkit import Checks  # noqa: E402

c = Checks("menu presentation")

NARROW = pygame.Rect(0, 0, 1280, 720)   # the narrowest window this game is run at
WIDE = pygame.Rect(0, 0, 1920, 1080)


def _present(buttons):
    """The footer controls that are on screen this frame."""
    return [r for r in (buttons.back, buttons.prev, buttons.next, buttons.confirm) if r]


# --------------------------------------------------------------------------
# 1. the type really is bigger
# --------------------------------------------------------------------------
print("\n1) bigger type")

FONTS = ts.make_fonts()
for role in ("title", "subtitle", "name", "label", "body", "small"):
    c.true("the %s font is bigger than the in-battle HUD's" % role,
           FONTS[role].get_height() > pygame.font.SysFont(
               config.FONT_NAME, config.FONT_SIZE).get_height())

# The hierarchy is unchanged - the ask was about size, not about which line
# shouts loudest. Pinned as an ORDER rather than as six numbers, so raising the
# set again does not mean editing six literals here.
heights = [FONTS[role].get_height()
           for role in ("title", "name", "subtitle", "label", "body", "small")]
c.eq("...and the roles keep their order", heights, sorted(heights, reverse=True))

# Every offset is one constant, so "bigger again" is one edit per role.
c.true("the offsets are named, not written into make_fonts()",
       all(hasattr(ts, name) for name in
           ("TITLE_FONT_DELTA", "SUBTITLE_FONT_DELTA", "NAME_FONT_DELTA",
            "LABEL_FONT_DELTA", "BODY_FONT_DELTA", "SMALL_FONT_DELTA")))


# --------------------------------------------------------------------------
# 2. the boxes that hold it still fit, at 1280x720
# --------------------------------------------------------------------------
print("\n2) it still fits")

# The header bar has a fixed height and holds the title with the hint under it.
# HEADER_HEIGHT itself is deliberately UNCHANGED - its own A/B probe showed the
# old value still clears the bigger type, and every pixel taken from the bar
# comes out of the tile band.
bar = ts.header_bar(NARROW)
hint_bottom = 16 + FONTS["title"].get_height() + FONTS["subtitle"].get_height()
c.true("the header bar still holds title and hint", hint_bottom + 12 <= bar.height)

# The footer's confirm button GROWS for a wrapped label, and its label names the
# pick, so the longest real map or army name is the binding case.
from game import army_lists as _al, maps as _maps  # noqa: E402

surface = pygame.Surface(NARROW.size)
ALL_NAMES = [m.name for m in _maps.MAPS.values()] + [e.name for e in _al.ARMY_LISTS]
overflow = []
for name in ALL_NAMES:
    got = ts.draw_footer(surface, NARROW, FONTS, 0, 1, confirm_label="Confirm: %s" % name)
    if not NARROW.contains(got.confirm):
        overflow.append(name)
c.eq("no real name pushes the confirm button off a 1280x720 screen", overflow, [])

# ...and does not merely SCRAPE the bottom edge. This is what FOOTER_HEIGHT and
# CONFIRM_BUTTON_WIDTH are actually for: staying on screen is satisfied by a
# 4px sliver, while the footer used to have 14px of air under its buttons.
# Without this the two constants are not load-bearing and their probes do not
# bite - which is exactly what those probes reported.
worst = min(NARROW.bottom - r.bottom
            for name in ALL_NAMES
            for r in _present(ts.draw_footer(surface, NARROW, FONTS, 0, 3,
                                             back_label="Back",
                                             confirm_label="Confirm: %s" % name)))
c.true("...and every footer control keeps its clearance below it (%d px)" % worst,
       worst >= ts.FOOTER_CLEARANCE_PX)

# ...and all four footer controls at once still do not overlap.
crowded = ts.draw_footer(surface, NARROW, FONTS, 0, 3,
                         back_label="Back", confirm_label="Confirm: Death Guard")
present = _present(crowded)
c.eq("a crowded footer still draws all four controls", len(present), 4)
c.eq("...and none of them overlap",
     [(i, j) for i, a in enumerate(present) for j, b in enumerate(present)
      if i < j and a.colliderect(b)], [])

# There is still a band left for the tiles themselves, which is what the header
# and footer were grown out of.
band = ts.tile_area(NARROW)
c.true("the tile band survives the bigger chrome", band.height > 350)

# The menu panel is laid out off the font heights, but ENTRY_HEIGHT and
# PANEL_WIDTH are fixed - so the panel has to be re-checked at the narrow size.
for in_game in (False, True):
    menu = GameMenu(in_game=in_game, save_path="x", save_note="note")
    c.true("the %s menu panel is still on a 1280x720 screen"
           % ("in-game" if in_game else "startup"),
           NARROW.contains(menu.panel_rect(NARROW)))
    rects = [r for _a, r, _e in menu.layout(NARROW)]
    c.true("...with its entries inside it",
           all(menu.panel_rect(NARROW).contains(r) for r in rects))
    # A row must be tall enough for its own label. The menu hit-tests against
    # ITS OWN rect and throws away the one draw_button() returns, so a row too
    # short for its label is drawn taller than it is clickable - silently.
    probe = pygame.Surface(NARROW.size)
    grown = [button_style.draw_button(probe, r, label, menu.fonts["label"]).height
             for r, (_a, label, _e) in zip(rects, menu.entries())]
    c.true("...each row is tall enough for its own label",
           all(height == rects[0].height for height in grown))
    # Nothing is drawn between two rows any more - the captions are gone (user:
    # "Die unterschriften unter den buttons koennen weg"), so the gap between
    # consecutive rows is exactly ENTRY_GAP. Without this the notes could come
    # back by accident and only a screenshot would say so.
    gaps = [b.y - a.bottom for a, b in zip(rects, rects[1:])]
    c.true("...and the rows are stacked with nothing between them",
           all(gap == gaps[0] for gap in gaps) and gaps[0] < 20)


# --------------------------------------------------------------------------
# 3. the header hint cannot run under the biome row
# --------------------------------------------------------------------------
print("\n3) the hint yields to the biome row")

# The map screen shares its header bar with the biome buttons, and its hint is
# NOT a fixed string - it names the selected map. This overlapped even at the
# old font size once a fourth biome arrived (measured: the Crucible hint is
# 608px against a row starting 616px in), so it is cut to fit.
screen = MapSelectScreen()
screen.layout(NARROW)
longest = max(_maps.MAPS.values(), key=lambda m: len(m.name))
screen.select(longest)
budget = screen._hint_width(NARROW)
c.true("the hint has a measured budget", budget and budget > 0)
c.true("...that stops short of the biome row",
       budget + ts.MARGIN < min(r.left for r in screen.biome_layout(NARROW).values()))
c.true("...and the hint really is cut to it",
       FONTS["subtitle"].size(ts.ellipsised(FONTS["subtitle"], screen._hint(), budget))[0]
       <= budget)
c.true("a hint that fits is left alone",
       ts.ellipsised(FONTS["subtitle"], "short", 400) == "short")
c.true("...and no budget means no limit",
       ts.ellipsised(FONTS["subtitle"], screen._hint(), None) == screen._hint())

# Drawn, not just computed. Measured on the header ALONE, so the biome row's
# own ink cannot be mistaken for the hint's: the rightmost pixel the hint puts
# down has to stop inside the budget.
paint = pygame.Surface(NARROW.size)
paint.fill((0, 0, 0))
ts.draw_header(paint, NARROW, FONTS, "CHOOSE THE BATTLEFIELD", screen._hint(),
               (90, 160, 205), hint_max_width=budget)
bar = ts.header_bar(NARROW)
hint_band = range(bar.y + 14 + FONTS["title"].get_height(), bar.bottom - 2)
ink = [x for x in range(NARROW.width) for y in hint_band
       if paint.get_at((x, y))[:3] not in (ts.HEADER_BG_COLOR, (0, 0, 0))]
c.true("the hint really was drawn", bool(ink))
c.true("...and stops inside its budget", max(ink) <= ts.MARGIN + budget)
c.true("...well clear of the biome row",
       max(ink) < min(r.left for r in screen.biome_layout(NARROW).values()))

# ...and the MAP SCREEN is what hands the header that budget. Checked by spying
# on the call rather than by reading the pixels it produces: the biome row is
# drawn on the same surface a frame later, so its ink cannot be told from the
# hint's - and without this the screen could pass None and nothing would notice
# (its own A/B probe reported exactly that).
_seen = {}
_real_header = ts.draw_header


def _spy(*args, **kwargs):
    _seen["hint_max_width"] = kwargs.get("hint_max_width")
    return _real_header(*args, **kwargs)


ts.draw_header = _spy
try:
    screen.draw(pygame.Surface(NARROW.size))
finally:
    ts.draw_header = _real_header
c.eq("the map screen tells the header how much room the hint has",
     _seen.get("hint_max_width"), screen._hint_width(NARROW))


# --------------------------------------------------------------------------
# 4. the main menu's backdrop
# --------------------------------------------------------------------------
print("\n4) artwork behind the main menu")

path = sprites.menu_background_path()
c.true("the supplied backdrop resolves to a file on disk",
       path is not None and os.path.isfile(path))
c.true("...found by its own name, wherever the folder puts it",
       path is not None and sprites.MENU_BACKGROUND_NAME in os.path.basename(path))

cover = sprites.menu_background_surface(path, NARROW.size)
c.eq("the backdrop fills the window exactly", cover.get_size(), NARROW.size)

# COVER, not fit. Measured with a synthetic image of a deliberately wrong
# aspect: cover crops the overhang and every edge pixel is still image, while
# fitting it leaves bars of the surface's own black down two sides. Asking the
# real artwork would not separate the two - its own corners are near-black.
_probe_dir = tempfile.mkdtemp()
_probe_path = os.path.join(_probe_dir, "probe.png")
_probe = pygame.Surface((400, 100))
_probe.fill((10, 200, 60))
pygame.image.save(_probe, _probe_path)
_scaled = sprites.menu_background_surface(_probe_path, (600, 600))
_edges = [_scaled.get_at((0, 300))[:3], _scaled.get_at((599, 300))[:3],
          _scaled.get_at((300, 0))[:3], _scaled.get_at((300, 599))[:3]]
c.true("it COVERS the window rather than letterboxing into it",
       all(sum(abs(a - b) for a, b in zip(edge, (10, 200, 60))) < 24 for edge in _edges))
shutil.rmtree(_probe_dir, ignore_errors=True)
c.true("...and cached per size", cover is sprites.menu_background_surface(path, NARROW.size))
c.true("...per size, so a resize gets its own",
       sprites.menu_background_surface(path, WIDE.size).get_size() == WIDE.size)

# The startup host paints it; the in-battle host must NOT - its backdrop is the
# frozen board, which is the whole point of a pause screen.
# A band of the lower screen clear of BOTH the menu panel (measured: it ends at
# y=534 for the startup host and y=578 in a battle) and of the footer's key
# hint over on the right, so what is sampled is only the backdrop.
BAND = [(x, y) for x in range(20, NARROW.width - 340, 17)
        for y in range(NARROW.height - 120, NARROW.height - 20, 11)]


def _colours(surf):
    """How many DISTINCT colours a band of the screen holds - a picture has
    many, a fill has one. Stronger than "this pixel is not black": the corner
    of this particular artwork is very nearly black."""
    return set(surf.get_at(pt)[:3] for pt in BAND)


start_surface = pygame.Surface(NARROW.size)
start_surface.fill((0, 0, 0))
GameMenu(save_path="x", save_note="n").draw(start_surface, (0, 0))
c.true("the startup menu paints a PICTURE behind it, not a fill",
       len(_colours(start_surface)) > 20)

board_paint = pygame.Surface(NARROW.size)
board_paint.fill((200, 200, 200))
GameMenu(in_game=True).draw(board_paint, (0, 0))
c.true("the in-battle menu still only dims the frozen board",
       len(_colours(board_paint)) == 1
       and sum(board_paint.get_at(BAND[0])[:3]) < 3 * 200)

# The veil is not decoration: without it the panel's contrast against the
# heading area depends on the photograph.
def _mean(surf):
    values = [sum(surf.get_at(pt)[:3]) for pt in BAND]
    return sum(values) / len(values)


c.true("the artwork is darkened before anything is drawn on it",
       _mean(start_surface) < _mean(cover))

# Missing art costs a picture, never the screen.
_real = sprites.menu_background_path
sprites.menu_background_path = lambda: None
try:
    fallback = pygame.Surface(NARROW.size)
    fallback.fill((0, 0, 0))
    GameMenu(save_path="x", save_note="n").draw(fallback, (0, 0))
    c.eq("a missing backdrop falls back to the flat fill",
         fallback.get_at((40, NARROW.height - 40))[:3], ts.BG_COLOR)
finally:
    sprites.menu_background_path = _real

# The pickers are deliberately NOT given the artwork: the ask named the main
# menu, and a photograph behind a grid of map previews would fight them.
picker = pygame.Surface(NARROW.size)
picker.fill((0, 0, 0))
ArmySelectScreen().draw(picker)
c.eq("the army picker keeps its flat background",
     picker.get_at((NARROW.width - 10, NARROW.height - 10))[:3], ts.BG_COLOR)

c.finish()
