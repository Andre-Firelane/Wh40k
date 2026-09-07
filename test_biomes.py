"""The four BIOMES the battlefield can be painted in, and their buttons.

User: "ich habe die texturen fuer die maps in ordner geordnet. es gibt jetzt 3
biome. kannst du bei der map auswahl bitte ganz oben noch 3 knoepfe reinpacken,
ueber die man sein biom waehlen kann?" - and later, for the fourth: "neben den
3 biomen soll es noch eine 4. option geben. dort besteht die map nicht aus
sprites, sondern du renderst sie."

THREE OF THE FOUR ARE PICTURES, THE FOURTH IS DRAWING CODE. That split runs
through this whole file: every "each biome supplies three files" check below
belongs to PHOTO_KEYS, and the arena gets the opposite check - that it supplies
NONE, so a missing folder can never be mistaken for missing art. What the arena
actually looks like is test_arena_biome.py's job; this file only asks that it
is a biome like the others.

Two claims, and they need separate checks:

  1. THE TABLE (game/biomes.py + game/sprites.py) - four biomes, the
     photographed three each supplying three real files off the disk, found by
     ROLE rather than by a transcribed filename, and PURELY COSMETIC: the
     board, both zones, every terrain footprint and every objective are
     identical whichever is picked.
  2. THE BUTTONS (game/ui/map_select.py) - four of them at the top of the map
     picker, one shown as selected, a click switching biome WITHOUT also
     picking a map, and the previews below actually repainting.

The regression guarantee for (1) is that the desert files are byte-identical
to the three that used to sit loose in Sprites/, so resolving them through a
BIOME must render the same pixels as reaching them directly. Checked as PIXELS
rather than as a promise - see section 4, which isolates the lookup.

Run: python test_biomes.py
"""

import hashlib
import os
import shutil

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1600, 900))

from game import biomes, config, maps, sprites  # noqa: E402
from game.game_state import GameState  # noqa: E402
from game.ui import button_style, map_preview, tile_screen as ts  # noqa: E402
from game.ui.map_select import ACCENT_COLOR, MapSelectScreen  # noqa: E402
from testkit import Checks  # noqa: E402

c = Checks("biomes")

_ORIGINAL_BIOME = config.BIOME
SCREEN_RECT = pygame.Rect(0, 0, 1600, 900)
screen = pygame.display.get_surface()


def board_digest(map_key, biome_key, box=360):
    """A hash of the rendered board - the only honest way to ask "does picking
    this actually change the picture", since every other observable (zones,
    terrain, objectives) is required NOT to change."""
    config.BIOME = biome_key
    map_preview.clear_cache()
    surface = map_preview.surface_for(maps.get(map_key), box, box)
    return hashlib.sha1(pygame.image.tobytes(surface, "RGB")).hexdigest()


def raises(key):
    try:
        biomes.get(key)
    except KeyError:
        return True
    return False


# --- 1. the table ----------------------------------------------------------

PHOTO_KEYS = ["city", "desert", "forest"]

c.eq("four biomes", len(biomes.BIOMES), 4)
c.eq("...city, desert, forest, arena, in button order", biomes.keys(),
     PHOTO_KEYS + ["arena"])

# The one question anybody asks about the difference, and it has to answer for
# every biome rather than only for the one it was written for.
c.true("the arena is the drawn one", biomes.is_procedural(biomes.get("arena")))
c.true("...and it is the ONLY drawn one",
       [b.key for b in biomes.BIOMES if biomes.is_procedural(b)] == ["arena"])
c.true("...which is exactly 'this biome has no folder'",
       biomes.get("arena").folder is None
       and all(biomes.get(k).folder for k in PHOTO_KEYS))
# The no-argument form reads the SETTING, which is what the renderer calls.
config.BIOME = "arena"
c.true("is_procedural() with no argument asks about the selected biome",
       biomes.is_procedural())
config.BIOME = "desert"
c.true("...and says no for a photographed one", not biomes.is_procedural())
config.BIOME = _ORIGINAL_BIOME
c.eq("the default is the drawn one (user: \"mach arena biom bitte als default\")",
     biomes.DEFAULT_BIOME, "arena")
c.true("...and config ships with a known one", _ORIGINAL_BIOME in biomes.BIOMES_BY_KEY)
# The two answer different questions - "what does the game open on" and "what
# do we do with a setting we do not recognise" - and the right answer is the
# same one: a stale settings value should land on the board the game normally
# shows, not on a different-looking one. Pinned so the two cannot drift.
c.eq("...the same one the fallback uses", _ORIGINAL_BIOME, biomes.DEFAULT_BIOME)

# The folder on disk is misspelled "Dessert" while every file inside it says
# "Desert". THE FOLDER WINS, exactly as it does for the eight Necron sprite
# names and the four T'au ones - the table transcribes the typo instead of
# asking for a rename. Pinned so a later tidy-up is a visible change rather
# than the silent loss of a whole biome.
c.eq("the desert biome's folder is spelled the way it is ON DISK",
     biomes.get("desert").folder, "Dessert")
c.eq("...but its BUTTON says Desert, because the label is a decision",
     biomes.get("desert").name, "Desert")
for key in ("city", "forest"):
    c.eq(f"{key}: folder and label agree where the disk is consistent",
         biomes.get(key).folder, biomes.get(key).name)

c.true("an unknown biome key raises rather than quietly playing the default",
       raises("swamp"))
c.true("...and a known one does not", not raises("forest"))

# current() is the opposite call and deliberately tolerant: it is read on the
# RENDER path, every time the static layer is rebuilt, so a stale settings
# value should repaint the table rather than take the game down mid-frame.
config.BIOME = "no such biome"
c.eq("a bad SETTING falls back instead of raising, because it is read per frame",
     biomes.current().key, biomes.DEFAULT_BIOME)
config.BIOME = _ORIGINAL_BIOME


# --- 2. every biome supplies all three real files --------------------------

# At the MODEL level - the file has to exist on disk. A table check would pass
# on a name that resolves to nothing, which is exactly the failure that
# started this: once the textures were sorted into folders, all three lookups
# returned None and the renderer silently fell back to flat colours.
seen = {}
for biome in [biomes.get(k) for k in PHOTO_KEYS]:
    config.BIOME = biome.key
    paths = {
        "ground": sprites.ground_texture_path(),
        "dense cover": sprites.dense_cover_texture_path(),
        "light cover": sprites.normal_cover_texture_path(),
    }
    for role, path in paths.items():
        c.true(f"{biome.key}: the {role} art resolves to a file that exists",
               path is not None and os.path.isfile(path))
        c.true(f"{biome.key}: ...out of its own folder ({biome.folder})",
               path is not None
               and os.path.basename(os.path.dirname(path)) == biome.folder)
    c.eq(f"{biome.key}: the three roles are three DIFFERENT files",
         len(set(paths.values())), 3)
    seen[biome.key] = paths

# No two biomes share a picture - otherwise one of them is not really a biome.
c.eq("all nine pictures are distinct",
     len({p for paths in seen.values() for p in paths.values()}), 9)

# The arena answers all three roles with None, and that is NOT the "missing
# art" the renderer falls back on - it means the biome is drawn instead
# (game/arena_biome.py). Checked here because the two look identical from
# sprites.py's side, and only game/renderer.py's is_procedural() branch keeps
# them apart: without it the arena would render as flat BACKGROUND_COLOR.
config.BIOME = "arena"
for role, path_of in (("ground", sprites.ground_texture_path),
                      ("dense cover", sprites.dense_cover_texture_path),
                      ("light cover", sprites.normal_cover_texture_path)):
    c.true(f"arena: the {role} lookup resolves to no file at all",
           path_of() is None)
config.BIOME = _ORIGINAL_BIOME

# The roles are matched by PREFIX, not by a transcribed name - which is what
# lets the desert folder spell its light cover with a hyphen
# (Light_Cover-Desert.jpg) where the other two use an underscore. That
# inconsistency is real and is the whole reason for the prefix rule, so it is
# pinned rather than left to chance.
c.true("the desert light cover really is the hyphenated odd one out",
       "-" in os.path.basename(seen["desert"]["light cover"]))
c.true("...and the other two are not, so the prefix rule is doing real work",
       all("-" not in os.path.basename(seen[k]["light cover"])
           for k in ("city", "forest")))

# normal_cover_texture_path() resolves to the biome's LIGHT_Cover file. The
# two names disagree on purpose: the renderer's split is "footprint with a
# wall on it" vs "without", not the terrain CATEGORY.
for key in PHOTO_KEYS:
    c.true(f"{key}: normal_cover_texture_path() is the Light_Cover picture",
           os.path.basename(seen[key]["light cover"]).lower().startswith("light_cover"))
    c.true(f"{key}: dense_cover_texture_path() is the Dense_Cover one",
           os.path.basename(seen[key]["dense cover"]).lower().startswith("dense_cover"))

config.BIOME = _ORIGINAL_BIOME


# --- 3. purely cosmetic ----------------------------------------------------

# Every biome must change the PICTURE and nothing else. Both halves are
# checked, because either one alone is worthless: a biome that changes nothing
# is a dead button, and one that changes the board is a bug.
for map_key in ("map1", "map2", "map3"):
    digests = {key: board_digest(map_key, key) for key in biomes.keys()}
    c.eq(f"{map_key}: each biome paints a visibly different board",
         len(set(digests.values())), 4)

    shapes = {}
    for key in biomes.keys():
        config.BIOME = key
        state = GameState()
        maps.get(map_key).build(state)
        shapes[key] = (
            len(state.obstacles), len(state.terrain_areas),
            len(state.objectives), len(state.deployment_zones),
            tuple(sorted((round(o.min_x, 4), round(o.min_y, 4),
                          round(o.max_x, 4), round(o.max_y, 4))
                         for o in state.obstacles)),
            tuple(sorted((o.name,) + tuple(round(v, 4)
                                           for v in o.terrain_area.bounding_box)
                         for o in state.objectives)),
        )
    c.eq(f"{map_key}: ...while terrain, objectives and zones are identical",
         len(set(shapes.values())), 1)

config.BIOME = _ORIGINAL_BIOME


# --- 4. the default reproduces the pre-change board exactly ----------------

# The desert folder's three files are byte-identical to the wueste-boden.jpg /
# Dense_Cover-Desert.jpg / Light_Cover-Desert.jpg that used to sit loose in
# Sprites/ (verified by hash when this was written). So resolving them THROUGH
# A BIOME has to render the same pixels as handing the renderer those files
# directly - i.e. the lookup change is behaviour-neutral and the whole thing is
# invisible until a button is pressed.
#
# It isolates the LOOKUP, deliberately: both sides go through today's renderer,
# so the separate masked-tile blend fix (see test_ground_texture.py) moves both
# equally and is not what this measures. That fix DOES change how every biome
# looks, which is why it has its own checks rather than hiding inside this one.
#
# Checked by pointing the three lookups at COPIES of the desert files placed
# OUTSIDE the biome folders - the closest reachable stand-in for the old world,
# the originals being gone from the working tree - and comparing the rendered
# board against what the biome path itself produces.
scratch = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(scratch, exist_ok=True)
config.BIOME = "desert"
loose = {}
for role, path_of in (("ground", sprites.ground_texture_path),
                      ("dense", sprites.dense_cover_texture_path),
                      ("light", sprites.normal_cover_texture_path)):
    dest = os.path.join(scratch, f"_biome_ab_{role}.jpg")
    shutil.copyfile(path_of(), dest)
    loose[role] = dest

biome_digests = {mk: board_digest(mk, "desert") for mk in ("map1", "map2", "map3")}

real = (sprites.ground_texture_path, sprites.dense_cover_texture_path,
        sprites.normal_cover_texture_path)
sprites.ground_texture_path = lambda: loose["ground"]
sprites.dense_cover_texture_path = lambda: loose["dense"]
sprites.normal_cover_texture_path = lambda: loose["light"]
try:
    for map_key, expected in biome_digests.items():
        map_preview.clear_cache()
        surface = map_preview.surface_for(maps.get(map_key), 360, 360)
        got = hashlib.sha1(pygame.image.tobytes(surface, "RGB")).hexdigest()
        c.eq(f"{map_key}: the default biome renders the pre-change board, "
             f"pixel for pixel", got, expected)
finally:
    (sprites.ground_texture_path, sprites.dense_cover_texture_path,
     sprites.normal_cover_texture_path) = real
    for path in loose.values():
        os.remove(path)
map_preview.clear_cache()
config.BIOME = _ORIGINAL_BIOME


# --- 5. the buttons --------------------------------------------------------

def fresh(biome="desert"):
    config.BIOME = biome
    picker = MapSelectScreen(default="map2")
    picker.layout(SCREEN_RECT)
    return picker


def click(picker, pos, rect=SCREEN_RECT):
    picker.handle_event(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1}), rect)


picker = fresh()
rects = picker.biome_rects
c.eq("one button per biome", sorted(rects), sorted(biomes.keys()))

# "ganz oben" - inside the header bar, above every tile, clear of the heading
# that shares that bar, and not overlapping each other.
bar = ts.header_bar(SCREEN_RECT)
for key, rect in rects.items():
    c.true(f"{key}: its button sits inside the header bar at the very top",
           bar.contains(rect))
    c.true(f"{key}: ...above every map tile",
           all(rect.bottom <= tile.rect.top for tile in picker.tiles))
c.eq("...in BIOMES order, left to right",
     [k for k, _ in sorted(rects.items(), key=lambda kv: kv[1].left)], biomes.keys())
c.eq("no two buttons overlap",
     sum(1 for a in rects.values() for b in rects.values()
         if a is not b and a.colliderect(b)), 0)

# The tiles keep their full height - the reason the row went INSIDE the header
# instead of into a strip of its own. Checked against a screen with no biome
# row at all rather than against a remembered number.
plain_area = ts.tile_area(SCREEN_RECT)
c.true("the tiles are as tall as they were before the row existed",
       all(tile.rect.height <= plain_area.height
           and tile.rect.top == plain_area.top for tile in picker.tiles))

# Narrow windows: this game runs fullscreen at whatever the desktop is, so the
# row has to survive a small one. Measured rather than asserted loosely.
title_end = ts.MARGIN + picker.fonts["title"].size("CHOOSE THE BATTLEFIELD")[0]
for width in (1280, 1366, 1600, 1920, 2560):
    narrow = pygame.Rect(0, 0, width, 900)
    small = MapSelectScreen(default="map2")
    small.layout(narrow)
    left = min(r.left for r in small.biome_rects.values())
    right = max(r.right for r in small.biome_rects.values())
    c.true(f"{width}px: the row clears the heading by {left - title_end}px",
           left > title_end)
    c.true(f"{width}px: ...and stays inside the window",
           right <= width - ts.MARGIN)

# Clicking a biome switches the paint...
picker = fresh("desert")
c.eq("the picker reports the live setting as its biome", picker.biome, "desert")
click(picker, picker.biome_rects["forest"].center)
c.eq("clicking Forest selects it", picker.biome, "forest")
c.eq("...and writes it where the renderer will read it", config.BIOME, "forest")

# ...and does NOT also pick a map, which is the whole risk of putting two kinds
# of button on one screen.
c.true("clicking a biome does not choose a map", picker.chosen is None)
c.true("...and does not end the screen", not picker.done)

# A map click still works afterwards, and leaves the biome alone. It SELECTS
# now rather than choosing - the map screen takes two beats (a click
# highlights, the footer button commits, see game/ui/map_select.py) - but what
# this pin is about is unchanged: the biome row must not swallow tile clicks.
picker.layout(SCREEN_RECT)
click(picker, picker.tiles[0].rect.center)
c.true("a map click still reaches the tiles", picker.selected is not None)
c.eq("...and leaves the biome alone", picker.biome, "forest")
# ...and the second beat still lands, with the biome still untouched: the two
# kinds of button on this screen have to stay independent all the way through.
picker.draw(pygame.Surface(SCREEN_RECT.size), (2, 2))
click(picker, picker.footer.confirm.center)
c.true("...and confirming then picks that map", picker.chosen is not None)
c.eq("...still leaving the biome alone", picker.biome, "forest")

# Re-clicking the selected biome is a no-op, and says so.
picker = fresh("city")
c.true("choose_biome() reports a real change", picker.choose_biome("forest"))
c.true("...and reports a repeated click as no change", not picker.choose_biome("forest"))
c.true("...and refuses an unknown key", not picker.choose_biome("swamp"))
c.eq("...leaving the selection where it was", picker.biome, "forest")

# ESC still quits - the biome row sits above that branch in the event chain,
# and a control that swallowed a keypress is this repo's error class 15.
picker = fresh("desert")
picker.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE}),
                    SCREEN_RECT)
c.true("ESC still quits the screen", picker.cancelled)

# The previews below actually repaint - the reason the buttons are on THIS
# screen at all. Compared as PIXELS off the tile's own art, not as a cache key.
config.BIOME = "desert"
map_preview.clear_cache()
before = hashlib.sha1(pygame.image.tobytes(
    map_preview.surface_for(maps.get("map2"), 300, 300), "RGB")).hexdigest()
picker = fresh("desert")
click(picker, picker.biome_rects["city"].center)
after = hashlib.sha1(pygame.image.tobytes(
    map_preview.surface_for(maps.get("map2"), 300, 300), "RGB")).hexdigest()
c.true("the map previews repaint in the newly picked biome", after != before)

# The selected one is drawn PRESSED, which is what tells you which is on.
# Measured on a real surface, with the mouse parked off-screen so no hover
# state can account for the difference.
#
# Sampled at a BACKGROUND point inside each button (just in from its left
# edge, clear of the centred label) and compared against button_style's own
# palette constants. A first version of this averaged the whole button and
# only asked whether the selected one was brighter - which its A/B probe
# showed passing with `pressed` hard-wired to False, because what that
# average really measured was how much white LETTERING each label has
# ("DESERT" simply has more ink than "CITY"). The state, not the wording.
config.BIOME = "desert"
picker = MapSelectScreen(default="map2")
picker.draw(screen, mouse_pos=(-50, -50))


def fill_at(rect):
    return screen.get_at((rect.left + 10, rect.centery))[:3]


c.eq("the selected button is drawn in the PRESSED fill",
     fill_at(picker.biome_rects["desert"]), button_style.BG_ACTIVE)
for key in ("city", "forest"):
    c.eq(f"...and {key}, which is not selected, in the idle one",
         fill_at(picker.biome_rects[key]), button_style.BG_NORMAL)

# The word BIOME is on screen, so three place names beside a list of maps do
# not read as three more maps. Found by its own colour in the strip to the
# left of the first button.
#
# The y range is the BUTTON's own band, not the whole header bar: draw_header
# paints a full-width accent-coloured rule along the bar's bottom edge in the
# very same colour, and counting that made this check pass with the label
# deleted - its A/B probe is what showed it.
first = picker.biome_rects[biomes.BIOMES[0].key]
first_left = first.left
label_pixels = sum(
    1
    for x in range(first_left - 80, first_left - 8)
    for y in range(first.top, first.bottom)
    if screen.get_at((x, y))[:3] == ACCENT_COLOR
)
c.true(f"the row is labelled BIOME ({label_pixels} px of label colour)",
       label_pixels > 20)

config.BIOME = _ORIGINAL_BIOME
map_preview.clear_cache()

c.finish()
