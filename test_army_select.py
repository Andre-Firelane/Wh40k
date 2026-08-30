"""Tests for the army selection screen and the list registry behind it.

User: "ich haette gerne noch, bevor das Pre game losgeht, eine
Auswahlmoeglichkeit fuer die Voelker/listen ... Es soll Spieler 1 und Spieler 2
angezeigt werden, nacheinander ... eine Kachel mit dem Volk name/logo/
detachment und dann die Portraits der einheiten darin ... Wenn man ueber die
Portraits hovert, sieht man noch mal im Detail, was in dem Squad drin steckt."
Plus two clarifications that are pinned here as their own checks: "Aber ich
waehle fuer die KI. Die KI soll nicht selber waehlen" and "Die Listen sollen
auch erstmal predefined sein".

WHAT THIS SUITE IS FOR, in three parts:

  1-3. game/army_lists.py: the three lists build for EITHER player, with the
       right names, and the detachment settings follow the choice - including
       being taken AWAY again, which is the half that is easy to leave out.
  4-7. game/ui/army_select.py: the two steps, the tile/portrait geometry, the
       hover detail, and drawing for real onto a Surface.
  8.   the WIRING in main.py and in the headless harnesses. A behaviour test
       cannot see this class of bug - a screen that is built and never shown,
       or a harness that hangs on a click nobody will make - which is exactly
       why this repo has been bitten by it three times (CLAUDE.md: the
       VengefulStars controller, the mark wiring, Path of the Outcast).

Run: python test_army_select.py
"""

import io
import os
import re

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1600, 900))

from game import army_lists, config, loadout, maps, scene_io, sprites  # noqa: E402
from game.ui.army_select import ArmySelectScreen  # noqa: E402
from testkit import Checks  # noqa: E402

c = Checks("army selection")
SCREEN_RECT = pygame.Rect(0, 0, 1600, 900)


def _read(path):
    return io.open(path, encoding="utf-8").read()


# --------------------------------------------------------------------------
# 1. The registry: three predefined lists, no army-building step
# --------------------------------------------------------------------------
print("\n=== 1. the list registry ===")

keys = [entry.key for entry in army_lists.ARMY_LISTS]
c.eq("five lists on offer", keys, ["aeldari", "orks", "necrons", "tau", "death_guard"])
c.eq("every list is reachable by key", sorted(army_lists.BY_KEY), sorted(keys))

# The tile's own text: name / logo / detachment, per the user's description of
# what a tile should carry. The logo is checked against the DISK, not against
# the table - a key that resolves to no file is exactly the failure a glance at
# the mapping cannot see.
# Death Guard has NO art yet - no model sprites and no faction badge. That is
# recorded as a PIN rather than skipped, so dropping the files in later is a
# visible one-line change here instead of a silent one, exactly as the Necron
# and Aeldari "no sprite" pins were before their art arrived.
LISTS_WITHOUT_ART = {"DEATH GUARD"}
for entry in army_lists.ARMY_LISTS:
    c.true(f"{entry.name} names a detachment", bool(entry.detachment))
    c.true(f"{entry.name} names its army rule", bool(entry.army_rule))
    has_badge = sprites.faction_logo_path(entry.faction_keyword) is not None
    if entry.faction_keyword in LISTS_WITHOUT_ART:
        c.true(f"{entry.name} has NO badge yet - art not uploaded", not has_badge)
    else:
        c.true(f"{entry.name}'s badge resolves to a file on disk", has_badge)

# An unknown key is refused loudly rather than falling through to a default -
# the failure mode that guard exists for is "the game silently fielded a
# different army".
try:
    army_lists.get("tyranids")
    c.true("an unknown army key is refused", False)
except SystemExit as exc:
    c.true("an unknown army key is refused", "tyranids" in str(exc))
    c.true("...and the message names the lists that do exist", "necrons" in str(exc))


# --------------------------------------------------------------------------
# 2. Every list builds for EITHER player
# --------------------------------------------------------------------------
print("\n=== 2. any list, any player ===")

# The whole point of the extraction: before it, Player 1 WAS the Aeldari and
# Player 2 was one of the other two. The totals are written out as the list's
# own arithmetic rather than copied from a previous run - CLAUDE.md's error
# class 17, which test_player1_army.py has now been bitten by twice.
EXPECTED = {
    # key: (units after 19.01 merging, models, points)
    # Still 20 list entries after the Shroud Runners -> Windriders swap (one
    # datasheet out, one in), but a unit FEWER: the Warlock Skyrunner used to
    # stand alone because its JOIN names WINDRIDERS and the list fielded none,
    # and now it merges into them. Models are unchanged (3 out, 3 in); the
    # points drop is only the transcription's own Shroud Runners 90 -> Windriders 80.
    "aeldari": (12, 74, 1890),   # 20 list entries, SIX attachments merged
    "orks": (14, 103, 1935),     # 17 list entries, three attachments merged
    "necrons": (9, 68, 2020),    # 15 list entries, SIX attachments merged
    # Replaced wholesale on 2026-08-30 by the list the user supplied: out go
    # the Ghostkeel, the Strike Team, the Coldstar + Starscythes and Farsight +
    # Sunforges, in come Shadowsun, an Ethereal, a second Fireblade and
    # Breacher Team, the Broadsides, Kroot Hounds, a second Pathfinder Team,
    # two Piranhas, a second Stealth team and the Vespid. It is also the only
    # list here fielding TWO detachments (Kauyon + Advanced Acquisition Cadre)
    # and the only one that buys no Enhancement - the supplied list names none,
    # so 2030 is its units and nothing else.
    "tau": (19, 94, 2030),       # 21 list entries, TWO attachments merged
}
for key, (units, models, points) in EXPECTED.items():
    for owner in ("Player 1", "Player 2"):
        squads = army_lists.preview_squads(key, owner)
        c.eq(f"{key} for {owner}: units", len(squads), units)
        c.eq(f"{key} for {owner}: models", sum(len(s.models) for s in squads), models)
        c.eq(f"{key} for {owner}: points", sum(s.points or 0 for s in squads), points)
        c.true(f"{key} for {owner}: every unit belongs to that player",
               all(s.owner == owner for s in squads))
        # The name is an identifier (the AI's plan orders, the map rosters and
        # a saved scene all key on it), so the owner's digit has to be in it.
        c.true(f"{key} for {owner}: every name carries the owner's digit",
               all(s.name.startswith(owner[-1] + " ") for s in squads))

c.eq("unit_name() forms the identifier", army_lists.unit_name("Player 2", "Boyz 1"), "2 Boyz 1")

# A mirror match is two distinct armies, because the digit separates them.
p1_names = {s.name for s in army_lists.preview_squads("orks", "Player 1")}
p2_names = {s.name for s in army_lists.preview_squads("orks", "Player 2")}
c.eq("a mirror match shares no unit name", sorted(p1_names & p2_names), [])

# PREDEFINED, per the user: the tile is a fixed list, so building it twice has
# to produce the same thing. (It is also what lets the screen cache previews.)
again = army_lists.preview_squads("aeldari", "Player 1")
c.eq("a list is predefined - it builds identically every time",
     [s.name for s in again], [s.name for s in army_lists.preview_squads("aeldari", "Player 1")])


# --------------------------------------------------------------------------
# 3. apply_to_config: the detachment follows the choice, both ways
# --------------------------------------------------------------------------
print("\n=== 3. detachment settings follow the choice ===")


class _Cfg:
    """A stand-in config so the real one is not left rewritten by a test."""
    SEER_COUNCIL_PLAYERS = ("Player 1",)
    AWAKENED_DYNASTY_PLAYERS = ("Player 2",)
    PLAYER1_ARMY = "aeldari"
    PLAYER2_ARMY = "necrons"


cfg = _Cfg()
army_lists.apply_to_config({"Player 1": "aeldari", "Player 2": "necrons"}, config_module=cfg)
c.eq("default pairing: Seer Council is Player 1's", cfg.SEER_COUNCIL_PLAYERS, ("Player 1",))
c.eq("default pairing: Awakened Dynasty is Player 2's", cfg.AWAKENED_DYNASTY_PLAYERS, ("Player 2",))

# Swap the two lists over. The settings must swap with them - and the half that
# is easy to get wrong is the REMOVAL: a setting that is only ever added to
# would leave Player 1 running Seer Council with no Aeldari on the table.
army_lists.apply_to_config({"Player 1": "necrons", "Player 2": "aeldari"}, config_module=cfg)
c.eq("swapped: Seer Council moved to Player 2", cfg.SEER_COUNCIL_PLAYERS, ("Player 2",))
c.eq("swapped: Awakened Dynasty moved to Player 1", cfg.AWAKENED_DYNASTY_PLAYERS, ("Player 1",))

# Orks have no such setting - War Horde gates on the units' own ORKS keyword.
army_lists.apply_to_config({"Player 1": "orks", "Player 2": "orks"}, config_module=cfg)
c.eq("no Aeldari on the table: nobody runs Seer Council", cfg.SEER_COUNCIL_PLAYERS, ())
c.eq("no Necrons on the table: nobody runs Awakened Dynasty", cfg.AWAKENED_DYNASTY_PLAYERS, ())
c.eq("the choice is written back to the army settings",
     (cfg.PLAYER1_ARMY, cfg.PLAYER2_ARMY), ("orks", "orks"))

# Both players on the same detachment list is a legal mirror.
army_lists.apply_to_config({"Player 1": "necrons", "Player 2": "necrons"}, config_module=cfg)
c.eq("a Necron mirror gives BOTH players the detachment",
     cfg.AWAKENED_DYNASTY_PLAYERS, ("Player 1", "Player 2"))


# --------------------------------------------------------------------------
# 4. The two steps - and the human answers both of them
# --------------------------------------------------------------------------
print("\n=== 4. two steps, one human ===")

screen = ArmySelectScreen(defaults={"Player 1": "aeldari", "Player 2": "necrons"})
c.eq("it opens on Player 1", screen.current_player, "Player 1")
c.true("it is not done yet", not screen.done)
c.true("step 1 tells the player how to choose", "Click a list" in screen.hint())

screen.choose("orks")
c.eq("after the first pick it asks Player 2", screen.current_player, "Player 2")
c.eq("Player 1's pick is recorded", screen.choices["Player 1"], "orks")
# The user's clarification, pinned as a check: the human picks for the AI.
c.true("step 2 says the human picks the AI's list too",
       "AI's list too" in screen.hint() and "never chooses its own" in screen.hint())

screen.back()
c.eq("Back returns to Player 1", screen.current_player, "Player 1")
c.eq("...and un-records that pick", "Player 1" in screen.choices, False)

screen.choose("aeldari")
screen.choose("orks")
c.true("done once both have a list", screen.done)
c.eq("both choices survive", screen.choices, {"Player 1": "aeldari", "Player 2": "orks"})
c.eq("choosing past the end does nothing", screen.choose("necrons"), False)

mirror = ArmySelectScreen()
mirror.choose("necrons")
mirror.choose("necrons")
c.eq("both players may pick the same list", mirror.choices,
     {"Player 1": "necrons", "Player 2": "necrons"})

# The AI never picks its own list, and the strongest form of that is
# structural: this screen has no route to an agent at all - it imports nothing
# from ai/, so there is nothing for a later edit to start calling.
select_src = _read(os.path.join("game", "ui", "army_select.py"))
c.true("the screen cannot reach an agent",
       "from ai" not in select_src and "import ai" not in select_src)


# --------------------------------------------------------------------------
# 5. Tiles: name/logo/detachment, and one portrait per unit
# --------------------------------------------------------------------------
print("\n=== 5. tile layout ===")

screen = ArmySelectScreen()
tiles = screen.layout(SCREEN_RECT)
c.eq("one tile per list", len(tiles), 3)
c.true("every tile is inside the screen", all(SCREEN_RECT.contains(t.rect) for t in tiles))
c.true("tiles do not overlap",
       all(not a.rect.colliderect(b.rect) for i, a in enumerate(tiles) for b in tiles[i + 1:]))
c.true("the tiles are large", all(t.rect.width > 300 and t.rect.height > 400 for t in tiles))

for tile in tiles:
    c.eq(f"{tile.entry.name}: a cell per character and per squad",
         len(tile.cells), len(tile.characters) + len(tile.units))
    c.true(f"{tile.entry.name}: every cell sits inside its own tile",
           all(tile.rect.contains(rect) for rect, _e in tile.cells))
    c.true(f"{tile.entry.name}: cells do not overlap each other",
           all(not a.colliderect(b)
               for i, (a, _e1) in enumerate(tile.cells)
               for b, _e2 in tile.cells[i + 1:]))
    # "die Portraits der einheiten darin" - every one of them has real art.
    c.true(f"{tile.entry.name}: every entry has a portrait",
           all(entry.path is not None for _r, entry in tile.cells))
    c.true(f"{tile.entry.name}: cells are squares",
           all(r.width == r.height for r, _e in tile.cells))
    c.eq(f"{tile.entry.name}: both sections are labelled",
         [title for title, _r in tile.section_labels], ["CHARACTERS", "SQUADS"])
    c.true(f"{tile.entry.name}: characters are drawn above squads",
           max(r.bottom for r, e in tile.cells if e.is_character)
           <= min(r.top for r, e in tile.cells if not e.is_character))


# THE SPLIT ITSELF (user: "hier wuerde ich tatsaechlich in diesem Screen die
# Charaktere von den Squads trennen, weil jetzt sieht man auf dem ersten Blick
# schlecht, welche Squads da in der Liste sind").
#
# The Aeldari list is the case that motivated it: five of its thirteen units
# are attached (19.01), and an attached unit's single portrait is its
# CHARACTER, so before the split those five mobs were invisible.
aeldari_tile = next(t for t in tiles if t.entry.key == "aeldari")
character_labels = [e.label for e in aeldari_tile.characters]
squad_labels = [e.label for e in aeldari_tile.units]
# Eight, not the five attached leaders alone: the Avatar-style standalone
# characters count too, and Warlock Skyrunners is a one-model CHARACTER unit
# that belongs here rather than under SQUADS.
c.eq("every attached leader is listed as a character", len(character_labels), 8)
c.true("...naming them by datasheet, not by squad id",
       "Farseer" in character_labels and "Eldrad Ulthran" in character_labels)
c.eq("...and every unit is listed as a squad", len(squad_labels), 12)
c.true("the mobs the characters lead are now visible in their own right",
       {"Guardian Defenders", "Storm Guardians", "Dire Avengers",
        "Howling Banshees", "Warp Spiders"} <= set(squad_labels))
c.true("a bodyguard is never filed as a character",
       not ({"Guardian Defenders", "Storm Guardians"} & set(character_labels)))

# A standalone CHARACTER unit belongs in the character column even though it
# was never attached to anything - which is what the keyword is read for.
necron_tile = next(t for t in tiles if t.entry.key == "necrons")
necron_characters = [e.label for e in necron_tile.characters]
# The C'tan Shard is the ONLY one left after the list revision - it is the
# one Necron character with no printed LEADER line, so it can never merge.
c.true("a lone character unit is filed as a character",
       "C'tan Shard of the Void Dragon" in necron_characters)
c.eq("...and it is the only lone one this list has now that six of the seven "
     "characters lead something", len(necron_characters), 7)
c.true("...and a lone non-character unit is not",
       "Doomsday Ark" in [e.label for e in necron_tile.units])

# The split does not lose or invent anything: every model in the list is
# still accounted for exactly once.
for tile in tiles:
    covered = sum(len(e.models) for e in tile.characters + tile.units)
    c.eq(f"{tile.entry.name}: the two columns cover every model exactly once",
         covered, sum(len(s.models) for s in tile.squads))

# The cell size is derived, not fixed: a small window has to fit the same
# number of units into a smaller tile.
# One cell size for all three tiles: they hold different numbers of entries,
# and per-tile sizing would put 150 px portraits next to 88 px ones on the
# same screen.
cell_sizes = {t.entry.key: t.cells[0][0].width for t in tiles}
# The tile with the MOST SQUADS is the one that overflows when the sizing
# forgets that CHARACTER rows are reserved at the page maximum for every tile.
# It is not necessarily the tile with the most cells - the Orks list has fewer
# entries than the Aeldari one but more squads, so it sits lower. Checked at
# several window sizes because the bug only shows once the reserved rows push
# the tallest squad block past the available height.
for _w, _h in ((1920, 1080), (1600, 900), (1366, 768), (1280, 720)):
    _screen = ArmySelectScreen()
    _tiles = _screen.layout(pygame.Rect(0, 0, _w, _h))
    for _tile in _tiles:
        c.true(f"{_w}x{_h} {_tile.entry.key}: no portrait spills out of its tile",
               all(_tile.rect.contains(_r) for _r, _e in _tile.cells))
    _most_squads = max(_tiles, key=lambda t: len(t.units))
    c.true(f"{_w}x{_h}: the tile with the most squads fits too",
           all(_most_squads.rect.contains(_r) for _r, _e in _most_squads.cells))

c.eq("every tile uses the same portrait size", len(set(cell_sizes.values())), 1)
c.true("...and the tiles are the same height", len({t.rect.height for t in tiles}) == 1)

# The grid fills the tile rather than leaving it mostly empty - the first
# version capped cells at 88 px and left the bottom two thirds of a
# 900 px-tall tile blank.
tallest = max(tiles, key=lambda t: len(t.cells))
lowest_cell = max(r.bottom for r, _e in tallest.cells)
c.true("the fullest tile's portraits reach its bottom edge",
       tallest.rect.bottom - lowest_cell <= 40)
# Relative to the tile, not an absolute pixel count: the test window is
# smaller than a real one, and the point is that a portrait is a picture
# rather than an icon.
c.true("portraits are a sizeable share of the tile",
       cell_sizes["orks"] >= tiles[0].rect.width // 8)

# The cell size is derived, not fixed: a small window has to fit the same
# number of units into a smaller tile.
small = ArmySelectScreen()
small_tiles = small.layout(pygame.Rect(0, 0, 1024, 720))
c.true("a smaller window still fits every entry",
       all(len(t.cells) == len(t.characters) + len(t.units) for t in small_tiles))
c.true("...by using smaller cells",
       small_tiles[0].cells[0][0].width < tiles[0].cells[0][0].width)
c.true("...and still inside its tile",
       all(t.rect.contains(r) for t in small_tiles for r, _e in t.cells))

# The previews the tiles show are the units the game will actually build.
c.eq("a tile shows the list that will be fielded",
     [s.name for s in tiles[1].squads],
     [s.name for s in army_lists.preview_squads("orks", "Player 1")])
# ...and for the player currently choosing, not for a fixed one.
screen.choose("aeldari")
p2_tiles = screen.layout(SCREEN_RECT)
c.true("step 2's tiles are built for Player 2",
       all(s.owner == "Player 2" for t in p2_tiles for s in t.squads))


# --------------------------------------------------------------------------
# 6. Hit tests and hover detail
# --------------------------------------------------------------------------
print("\n=== 6. hover and click ===")

screen = ArmySelectScreen()
tiles = screen.layout(SCREEN_RECT)
c.eq("tile_at finds the tile under the cursor", screen.tile_at(tiles[2].rect.center), 2)
c.eq("tile_at outside every tile is None", screen.tile_at((2, 2)), None)

cell_rect, hovered = tiles[1].cells[0]
c.true("portrait_at finds the entry under the cursor",
       screen.portrait_at(cell_rect.center) is hovered)
c.eq("portrait_at off a portrait is None", screen.portrait_at((2, 2)), None)

# "Wenn man ueber die Portraits hovert, sieht man noch mal im Detail, was in
# dem Squad drin steckt" - the detail is the unit's model lines with their
# weapons, straight out of game/loadout.py so it reads the same here as it does
# in the pre-game's own transport buttons.
header, lines = screen._detail_lines(hovered)
c.eq("the detail names what is under the cursor", header[0], hovered.label)
c.true("the detail gives its size", f"{len(hovered.models)} model" in header[1])
c.true("the detail gives its points", "pts" in header[1])
c.eq("the detail is that entry's real loadout", lines[:len(lines) - len(hovered.partners and [1] or [])],
     loadout.model_loadout_lines(hovered.models))
c.true("...which names weapons, not just the unit", any(":" in line for line in lines))

# Half of an attached unit has to say what the other half is: two separate
# pictures would otherwise lose the fact that they are ONE unit (19.01).
leader = next(e for e in tiles[0].characters if e.partners)
_h, leader_lines = screen._detail_lines(leader)
c.true("a leader's card names the unit it leads",
       any(line.startswith("Leads ") and "19.01" in line for line in leader_lines))
bodyguard = next(e for e in tiles[0].units if e.partners)
_h2, bodyguard_lines = screen._detail_lines(bodyguard)
c.true("a bodyguard's card names who leads it",
       any(line.startswith("Led by ") and "19.01" in line for line in bodyguard_lines))
c.true("a unit that is nobody's half says neither",
       not any("19.01" in line for line in screen._detail_lines(
           next(e for e in tiles[0].units if not e.partners))[1]))
lone = next(e for t in tiles for _r, e in t.cells if len(e.models) == 1)
c.true("a one-model entry reads \"1 model\", not \"1 models\"",
       screen._detail_lines(lone)[0][1].startswith("1 model |"))
many = next(e for t in tiles for _r, e in t.cells if len(e.models) > 1)
c.true("...and a multi-model one is still plural",
       screen._detail_lines(many)[0][1].startswith(f"{len(many.models)} models"))

# A left click on a tile fields that list.
screen.handle_event(
    pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": tiles[2].rect.center, "button": 1}),
    SCREEN_RECT)
c.eq("clicking a tile picks that list", screen.choices.get("Player 1"), tiles[2].entry.key)

# A right click goes back a step.
screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (5, 5), "button": 3}),
                    SCREEN_RECT)
c.eq("right-click goes back", screen.current_player, "Player 1")

# Motion updates the hover without choosing anything.
screen.handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": cell_rect.center}), SCREEN_RECT)
c.true("motion sets the hovered entry", screen.hovered_entry is not None)
c.eq("motion chooses nothing", screen.choices, {})

# ESC and the window's close button both abandon the screen, which main()
# reads as "quit" - the same meaning ESC has everywhere else in fullscreen.
for label, event in (("ESC", pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE})),
                     ("QUIT", pygame.event.Event(pygame.QUIT, {}))):
    aborted = ArmySelectScreen()
    aborted.handle_event(event, SCREEN_RECT)
    c.true(f"{label} abandons the screen", aborted.cancelled and aborted.done)


# --------------------------------------------------------------------------
# 7. It actually draws
# --------------------------------------------------------------------------
print("\n=== 7. drawing ===")

surface = pygame.Surface(SCREEN_RECT.size)
screen = ArmySelectScreen()
tiles = screen.layout(SCREEN_RECT)
hover_rect = tiles[0].cells[0][0]
screen.draw(surface, hover_rect.center)

# Pixels, not just "it did not raise": a tile has to differ from the empty
# background, and the hovered portrait's detail card has to appear next to the
# cursor.
from game.ui.army_select import BG_COLOR  # noqa: E402

def _differs(rect):
    sub = surface.subsurface(rect)
    return any(sub.get_at((x, y))[:3] != BG_COLOR
               for x in range(0, rect.width, 7) for y in range(0, rect.height, 7))

c.true("the tiles are drawn", all(_differs(t.rect) for t in tiles))
c.true("the header is drawn", _differs(pygame.Rect(0, 0, SCREEN_RECT.width, 60)))
c.true("the hovered portrait's detail card is drawn next to the cursor",
       _differs(pygame.Rect(hover_rect.centerx + 24, hover_rect.centery + 24, 200, 40)))

# A/B in the other direction: the same frame drawn with the cursor OFF every
# portrait has to differ exactly where the card was, so the card is genuinely
# the hover's doing rather than something that is always there.
plain = pygame.Surface(SCREEN_RECT.size)
plain_screen = ArmySelectScreen()
plain_screen.layout(SCREEN_RECT)
plain_screen.draw(plain, (hover_rect.centerx, tiles[0].rect.bottom - 4))
card_area = pygame.Rect(hover_rect.centerx + 24, hover_rect.centery + 24, 200, 40)
c.true("no card is drawn without a hovered portrait",
       any(surface.get_at((x, y)) != plain.get_at((x, y))
           for x in range(card_area.x, card_area.right, 5)
           for y in range(card_area.y, card_area.bottom, 5)))
c.eq("...and nothing was hovered in that frame", plain_screen.hovered_entry, None)

# Step 2 draws its Back button and step 1 does not.
step2 = ArmySelectScreen()
step2.choose("orks")
step2.draw(pygame.Surface(SCREEN_RECT.size), (2, 2))
c.true("step 2 offers a Back button", step2.back_rect is not None)
step1 = ArmySelectScreen()
step1.draw(pygame.Surface(SCREEN_RECT.size), (2, 2))
c.eq("step 1 has nothing to go back to", step1.back_rect, None)


# --------------------------------------------------------------------------
# 7b. Pagination - what happens with more lists than fit on one screen
# --------------------------------------------------------------------------
print("\n=== 7b. pagination ===")

# This build ships three lists, so the pager is unreachable through the real
# registry - and an unreachable feature is an untested one. The screen takes
# its lists as an argument for exactly this: five entries, two pages.
five = (list(army_lists.ARMY_LISTS) + list(army_lists.ARMY_LISTS))[:5]
paged = ArmySelectScreen(lists=five)
c.eq("five lists make two pages", paged.page_count, 2)
c.eq("it opens on the first page", paged.page, 0)

first = paged.layout(SCREEN_RECT)
c.eq("a page shows at most three tiles", len(first), 3)
c.eq("...the first three", [t.entry.key for t in first], [e.key for e in five[:3]])
first_cell = first[0].cells[0][0].width
first_width = first[0].rect.width

paged.turn_page(1)
second = paged.layout(SCREEN_RECT)
c.eq("the second page shows the rest", [t.entry.key for t in second], [e.key for e in five[3:]])
# The leftover page must not stretch two tiles across the whole screen, and
# must not resize the portraits either - paging is meant to move the eye, not
# to redraw at a different scale.
c.eq("a partial page keeps the tile width", second[0].rect.width, first_width)
c.eq("...and the portrait size", second[0].cells[0][0].width, first_cell)

# Only the current page can be clicked: a tile that is not on screen must not
# be reachable by a coordinate that happens to land where it would have been.
c.eq("hit tests only see the current page", len(paged.tiles), 2)
c.eq("...so a click in the empty third slot chooses nothing",
     paged.tile_at((SCREEN_RECT.width - 100, SCREEN_RECT.centery)), None)

paged.turn_page(1)
c.eq("Next wraps round rather than dead-ending", paged.page, 0)
paged.turn_page(-1)
c.eq("Prev wraps the other way", paged.page, 1)

# Three ways in, because a screen that can only be paged one way is one
# swallowed event away from being unpageable.
paged.page = 0
paged.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RIGHT}), SCREEN_RECT)
c.eq("the right arrow pages forward", paged.page, 1)
paged.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_LEFT}), SCREEN_RECT)
c.eq("the left arrow pages back", paged.page, 0)
paged.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, {"y": -1, "x": 0}), SCREEN_RECT)
c.eq("the wheel pages too", paged.page, 1)

# The buttons, drawn and then clicked - not called directly, so this covers
# their rects as well as their effect.
paged.page = 0
paged.draw(pygame.Surface(SCREEN_RECT.size), (2, 2))
c.true("the pager draws both buttons",
       paged.prev_rect is not None and paged.next_rect is not None)
paged.handle_event(
    pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": paged.next_rect.center, "button": 1}),
    SCREEN_RECT)
c.eq("clicking Next pages forward", paged.page, 1)
c.eq("...and chooses nothing", paged.choices, {})
paged.handle_event(
    pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": paged.prev_rect.center, "button": 1}),
    SCREEN_RECT)
c.eq("clicking Prev pages back", paged.page, 0)

# A list picked on page 2 is still the list that gets fielded.
paged.turn_page(1)
paged.layout(SCREEN_RECT)
paged.handle_event(
    pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                       {"pos": paged.tiles[0].rect.center, "button": 1}),
    SCREEN_RECT)
c.eq("a tile on a later page can be chosen",
     paged.choices.get("Player 1"), five[3].key)

# With three lists there is one page and no pager chrome at all - checked
# against an explicit three, not against the registry, so adding a fifth list
# later cannot quietly turn this into a different assertion.
single = ArmySelectScreen(lists=army_lists.ARMY_LISTS[:3])
single.draw(pygame.Surface(SCREEN_RECT.size), (2, 2))
c.eq("three lists need no pager", single.page_count, 1)
c.true("...so no pager buttons are drawn",
       single.prev_rect is None and single.next_rect is None)
c.eq("...and turning the page does nothing", single.turn_page(1), False)

# How many tiles a page holds FOLLOWS THE WINDOW: a fixed count would either
# waste a wide screen or cramp a narrow one, and both were measured.
wide = ArmySelectScreen()
wide_tiles = wide.layout(pygame.Rect(0, 0, 1920, 1080))
c.eq("a 1920-wide screen fits four tiles per page", wide.tiles_per_page, 4)
# The FIFTH list is what finally makes the pager real in an actual game. The
# machinery has been here since the army-select screen was built, but until now
# it could only be exercised against an artificial registry - so this line
# changing from 1 to 2 is the moment it went live, not a regression.
c.eq("...and five lists need a second page", wide.page_count, 2)
c.true("...and the tiles are still large", wide_tiles[0].rect.width >= 400)

narrow = ArmySelectScreen()
narrow_tiles = narrow.layout(pygame.Rect(0, 0, 1366, 768))
c.eq("a 1366-wide screen fits three", narrow.tiles_per_page, 3)
c.eq("...and pages the fourth", narrow.page_count, 2)
c.true("...without the tiles dropping below the readable width",
       narrow_tiles[0].rect.width >= 400)
c.true("...and every portrait still inside its tile",
       all(t.rect.contains(r) for t in narrow_tiles for r, _e in t.cells))

# Never more than four across, however wide the screen: past that a list is
# easier to compare by paging than by scanning.
huge = ArmySelectScreen()
huge.layout(pygame.Rect(0, 0, 3840, 2160))
c.eq("a very wide screen still shows at most four", huge.tiles_per_page, 4)

# A page index left over from a wider window must not survive into a narrower
# one - it would index past the end and show an empty screen.
shrunk = ArmySelectScreen(lists=(list(army_lists.ARMY_LISTS) + list(army_lists.ARMY_LISTS))[:5])
shrunk.layout(pygame.Rect(0, 0, 1920, 1080))
shrunk.turn_page(1)
c.eq("paged to the last page on a wide screen", shrunk.page, 1)
shrunk.layout(pygame.Rect(0, 0, 1024, 720))
c.true("a narrower window clamps the page rather than showing nothing",
       shrunk.page < shrunk.page_count and len(shrunk.tiles) > 0)


# --------------------------------------------------------------------------
# 8. Wiring - the class of bug a behaviour test cannot see
# --------------------------------------------------------------------------
print("\n=== 8. wiring ===")

main_src = _read("main.py")


def _line_of(pattern):
    match = re.search(pattern, main_src)
    return main_src[:match.start()].count("\n") if match else None


c.true("main() runs the selection screen", "ArmySelectScreen(defaults=armies).run(screen)" in main_src)
c.true("...gated on config.ARMY_SELECT", "if config.ARMY_SELECT and not config.LOAD_SCENE:" in main_src)
c.true("...and abandoning it closes the program",
       re.search(r"if chosen is None:\s*\n\s*pygame\.quit\(\)\s*\n\s*return", main_src) is not None)
c.true("main() writes the detachment settings from the choice",
       "army_lists.apply_to_config(armies)" in main_src)
c.true("main() builds each player's chosen list",
       "army_lists.get(armies[owner]).build(" in main_src)
c.true("the map filters on the chosen pairing", "battle_map.fields(squad, armies)" in main_src)
c.true("the map's roster guard reads the chosen pairing",
       "battle_map.roster_for(armies)" in main_src)

# ORDER is the whole point: the choice has to be made before anything is built
# from it, exactly like maps.apply_to_config().
select_line = _line_of(r"ArmySelectScreen\(defaults=armies\)")
apply_line = _line_of(r"army_lists\.apply_to_config\(armies\)")
build_line = _line_of(r"army_lists\.get\(armies\[owner\]\)\.build\(")
c.true("the screen runs before the settings are written", select_line < apply_line)
c.true("the settings are written before any unit is built", apply_line < build_line)

# main.py must no longer carry a second copy of the army lists.
c.true("main.py no longer builds squads itself",
       "from game.factions import build_squad" not in main_src and "= build_squad(" not in main_src)
c.true("main.py no longer imports datasheets", "from game.factions.orks import" not in main_src)

# --load adopts the snapshot's own lists; without that every unit name in it
# would miss.
c.true("a saved scene records which lists were on the table",
       "armies=armies" in main_src and "def armies_in(" in _read(os.path.join("game", "scene_io.py")))
c.true("--load rebuilds those lists", "scene_io.armies_in(config.LOAD_SCENE)" in main_src)

# The headless harnesses cannot answer a click, so they must all opt out. A new
# one that forgets this hangs, which is the failure this check exists to make
# impossible to ship.
for harness in ("selfplay.py", "smoke_pregame.py", "smoke_log_input.py", "smoke_measure_tool.py",
                "smoke_end_turn_warning.py"):
    src = _read(harness)
    c.true(f"{harness} turns the selection screen off", "config.ARMY_SELECT = False" in src)
    c.true(f"{harness} does so before importing main",
           src.index("config.ARMY_SELECT = False") < src.index("import main"))


# --------------------------------------------------------------------------
# 9. The map rosters, now that either player can field either list
# --------------------------------------------------------------------------
print("\n=== 9. per-army map rosters ===")

# EVERY shipped map now fields the whole army: the 30"x30" test board that
# carried a four-units-a-side roster has been replaced by a full 60"x44" one.
for key in ("map1", "map2", "map3"):
    c.eq(f"{key} fields everything", maps.get(key).roster_for({"Player 1": "orks"}), None)
c.true("so no shipped map carries a partial roster at all",
       all(maps.get(k).army_roster is None for k in ("map1", "map2", "map3")))

# The MECHANISM still has to work, because a future small map will want it -
# and the guard that used to ride on map 3's own table is exercised here
# instead, on a map built for the purpose. Two halves, and only the second one
# needed a shipped map to have a roster:
#   - the DATA half ("does this hand-written name still match a unit?") has no
#     subject any more; nothing hand-writes a roster.
#   - the MECHANISM half ("{p} resolves to the owner, an unpicked list
#     contributes nothing, a list BOTH players picked contributes twice") is
#     what a future map depends on, so it is pinned.
_keys = [e.key for e in army_lists.ARMY_LISTS]
_first, _second = _keys[0], _keys[1]
_p1 = sorted(s.name for s in army_lists.preview_squads(_first, "Player 1"))[:2]
_p2 = sorted(s.name for s in army_lists.preview_squads(_second, "Player 1"))[:2]


def _templated(names):
    return {("{p}" + n[1:]) if n[:1].isdigit() else n for n in names}


_probe = maps.BattleMap(
    key="probe", name="probe", width_in=30.0, height_in=30.0,
    zones=[("Player 1", [(15.0, 26.0, 30.0, 8.0)]), ("Player 2", [(15.0, 4.0, 30.0, 8.0)])],
    terrain=lambda state, battle_map: None,
    player1=maps.Player1Deployment(squads=[], devilfish=(0.0, 0.0)),
    player2=maps.Player2Deployment(gretchin=[], stormboyz=[], warbikers=[],
                                   boyz1=[], trukks=[], deff_dread=[]),
    army_roster={_first: _templated(_p1), _second: _templated(_p2)},
)
c.true("a roster table stores the owner as a placeholder, never a digit",
       all("{p}" in n for names in _probe.army_roster.values() for n in names))
_mixed = _probe.roster_for({"Player 1": _first, "Player 2": _second})
c.true("...and roster_for resolves it away", all("{p}" not in n for n in _mixed))
c.eq("each side contributes its own two units", len(_mixed), 4)
c.true("Player 1's names start with 1 and Player 2's with 2",
       all(n.startswith("1 ") for n in _mixed if n[2:] in {x[2:] for x in _p1})
       and all(n.startswith("2 ") for n in _mixed if n[2:] in {x[2:] for x in _p2}))
_mirror = _probe.roster_for({"Player 1": _first, "Player 2": _first})
c.eq("a list BOTH players picked contributes twice, once per owner", len(_mirror), 4)
c.eq("a list nobody picked contributes nothing",
     len(_probe.roster_for({"Player 1": _first})), 2)
_squads = {s.name: s for s in army_lists.preview_squads(_first, "Player 1")}
_named = next(iter(_mixed))
c.true("fields() matches by EXACT name, so a rename cannot pass silently",
       _probe.fields(_squads[_p1[0]], {"Player 1": _first, "Player 2": _second})
       and not _probe.fields(type("S", (), {"name": "1 No Such Unit 1"})(),
                             {"Player 1": _first, "Player 2": _second}))


# --------------------------------------------------------------------------
# 10. A snapshot's armies round-trip
# --------------------------------------------------------------------------
print("\n=== 10. scene snapshots ===")


class _EmptyState:
    tokens = []
    reserves = []
    embarked_squads = []


data = scene_io.capture(_EmptyState(), "map2", armies={"Player 1": "orks", "Player 2": "aeldari"})
c.eq("capture records the pairing", data["armies"], {"Player 1": "orks", "Player 2": "aeldari"})
path = os.path.join("scenes", "_army_select_roundtrip.json")
try:
    scene_io.write(data, path)
    c.eq("armies_in reads it back", scene_io.armies_in(path),
         {"Player 1": "orks", "Player 2": "aeldari"})
    older = scene_io.read(path)
    older.pop("armies")
    scene_io.write(older, path)
    c.eq("a snapshot from before this existed simply says nothing",
         scene_io.armies_in(path), None)
finally:
    if os.path.exists(path):
        os.remove(path)

c.eq("capture without armies stays silent",
     "armies" in scene_io.capture(_EmptyState(), "map2"), False)

c.finish()
