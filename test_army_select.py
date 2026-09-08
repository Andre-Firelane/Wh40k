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
from game.ui import army_select, tile_screen as ts  # noqa: E402
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
c.eq("ten lists on offer", keys,
     ["aeldari", "aeldari_warhost", "aeldari_warhost_guardians", "orks",
      "necrons", "tau", "tau_montka", "tau_retaliation", "tau_recon",
      "death_guard"])
# FIVE FACTIONS, TEN LISTS - two of them with a real choice underneath, which
# is what the two-step "pick a people, then a list" flow was built for and had
# only ever been measured against a made-up registry.
c.eq("...across five factions", len(army_lists.factions()), 5)
c.eq("...and the T'au have four of them",
     [e.key for e in army_lists.lists_for("T'AU EMPIRE")],
     ["tau", "tau_montka", "tau_retaliation", "tau_recon"])
# Pinned as the whole MAPPING rather than as "every other faction has exactly
# one": that older shape said something true about a registry in which only the
# T'au had a choice, and it stopped being the claim worth making the moment a
# second faction got one. A count per faction moves visibly whenever any list is
# added, wherever it lands.
c.eq("...and each faction offers exactly this many",
     {f.key: len(army_lists.lists_for(f.key)) for f in army_lists.factions()},
     {"AELDARI": 3, "ORKS": 1, "NECRONS": 1, "T'AU EMPIRE": 4, "DEATH GUARD": 1})
c.eq("every list is reachable by key", sorted(army_lists.BY_KEY), sorted(keys))

# The tile's own text: name / logo / detachment, per the user's description of
# what a tile should carry. The logo is checked against the DISK, not against
# the table - a key that resolves to no file is exactly the failure a glance at
# the mapping cannot see.
# Death Guard has NO art yet - no model sprites and no faction badge. That is
# recorded as a PIN rather than skipped, so dropping the files in later is a
# visible one-line change here instead of a silent one, exactly as the Necron
# and Aeldari "no sprite" pins were before their art arrived.
# Death Guard's badge arrived last and emptied this set - the pin did its job
# and turned over. Kept as a set rather than deleted: it is where the next
# faction shipped ahead of its art goes, and an empty one is the claim that
# every fieldable list has a badge today.
LISTS_WITHOUT_ART = set()
for entry in army_lists.ARMY_LISTS:
    c.true(f"{entry.name} names a detachment", bool(entry.detachment))
    c.true(f"{entry.name} names its army rule", bool(entry.army_rule))
    has_badge = sprites.faction_logo_path(entry.faction_keyword) is not None
    if entry.faction_keyword in LISTS_WITHOUT_ART:
        c.true(f"{entry.name} has NO badge yet - art not uploaded", not has_badge)
    else:
        c.true(f"{entry.name}'s badge resolves to a file on disk", has_badge)
c.eq("every army list has badge art, so GameStatusPanel never needs a monogram",
     LISTS_WITHOUT_ART, set())

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
    # Revised again on 2026-09-01 (user: "Falcon raus / Shining Spears raus /
    # Avatar of Khaine rein"): two entries out and one in, so 20 list entries
    # become 19 and the unit count falls with it - the Avatar has no LEADER
    # line, so unlike the Warlock Skyrunner before him he adds a unit rather
    # than merging into one. Models 74 - 1 (Falcon) - 3 (Spears) + 1 = 71, and
    # the army gets DEARER by 20 despite losing an entry: 250 for the Avatar
    # against the 230 the two departing entries cost between them.
    "aeldari": (11, 71, 1910),   # 19 list entries, SIX attachments merged
    "orks": (14, 103, 1935),     # 17 list entries, three attachments merged
    "necrons": (9, 68, 2020),    # 15 list entries, SIX attachments merged
    # Replaced wholesale on 2026-08-30 by the list the user supplied: out go
    # the Ghostkeel, the Strike Team, the Coldstar + Starscythes and Farsight +
    # Sunforges, in come Shadowsun, an Ethereal, a second Fireblade and
    # Breacher Team, the Broadsides, Kroot Hounds, a second Pathfinder Team,
    # two Piranhas, a second Stealth team and the Vespid. It was the first
    # list here to field TWO detachments (Kauyon + Advanced Acquisition Cadre)
    # - the Aeldari list does too now - and it is still the only one that buys
    # no Enhancement at all: the supplied list names none,
    # so 2030 is its units and nothing else.
    "tau": (18, 76, 2165),       # 21 list entries, THREE attachments merged,
                                 # and the first list here that buys Enhancements
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
# Helpers for the sections below, now that picking an army is TWO questions
# (user: "erst waehlt man das Volk und dann kommen die verschiedenen Listen zur
# Auswahl. also in 2 Stufen").
# --------------------------------------------------------------------------
def list_screen(lists=None, defaults=None, faction=None):
    """A screen already past the FACTION question.

    Most of what follows is about what a LIST tile looks like, and that is step
    two now. Answering step one here keeps those sections testing the thing
    they were written for instead of testing the new step by accident."""
    screen = ArmySelectScreen(lists=lists, defaults=defaults)
    screen.choose(faction if faction is not None else screen.items[0].key)
    return screen


def multi_list_faction(count=5, base_key="orks"):
    """`count` lists that all belong to ONE faction.

    The shape the user has since created: the T'au now ship TWO lists (Kauyon
    and Mont'ka), which is what section 4c below drives. This helper stays for
    the cases a real pair cannot reach - the PAGER needs more tiles than one
    page holds, and the shared cell size needs several lists to share it - so
    the geometry is still measured against several lists of one faction rather
    than against several factions.

    Registered in BY_KEY because everything a tile needs goes through the real
    registry: preview_squads() builds the units and detachments.points_for()
    prices the detachments. They reuse the base list's builder, so these are
    genuine buildable lists, not stubs."""
    base = army_lists.get(base_key)
    made = []
    for index in range(count):
        entry = army_lists.ArmyList(
            f"{base_key}_variant_{index}", f"{base.name} List {index + 1}",
            base.faction_keyword, base.army_rule, base.detachments, base.build,
            force_disposition=base.force_disposition,
        )
        army_lists.BY_KEY[entry.key] = entry
        made.append(entry)
    return made


def many_factions(count):
    """`count` lists that each belong to a DIFFERENT faction.

    The mirror of multi_list_faction(): that one grows step TWO, this one grows
    step ONE. Needed since the faction step became a grid - five real factions
    now fit on one page at every supported resolution, so the only way to reach
    its pager at all is to invent more factions.

    They reuse the base list's builder and go into BY_KEY like the other
    helper's do, so they are genuine buildable lists rather than stubs."""
    base = army_lists.get("orks")
    made = []
    for index in range(count):
        entry = army_lists.ArmyList(
            f"faction_{index}", f"Faction {index + 1}",
            f"MADE UP FACTION {index}", base.army_rule, base.detachments, base.build,
            force_disposition=base.force_disposition,
        )
        army_lists.BY_KEY[entry.key] = entry
        made.append(entry)
    return made


# --------------------------------------------------------------------------
# 4. The two steps - and the human answers both of them
# --------------------------------------------------------------------------
print("\n=== 4. two steps, one human ===")

screen = ArmySelectScreen(defaults={"Player 1": "aeldari", "Player 2": "necrons"})
c.eq("it opens on Player 1", screen.current_player, "Player 1")
c.true("it is not done yet", not screen.done)
# Step one is the FACTION now (user: "erst waehlt man das Volk und dann
# kommen die verschiedenen Listen zur Auswahl. also in 2 Stufen").
c.true("step 1 tells the player how to choose", "Click a faction" in screen.hint())
c.true("...and says a second question follows", "lists come next" in screen.hint())

screen.choose("orks")
c.eq("after the first pick it asks Player 2", screen.current_player, "Player 2")
c.eq("Player 1's pick is recorded", screen.choices["Player 1"], "orks")
# The user's clarification, pinned as a check: the human picks for the AI.
c.true("Player 2's first step says the human picks for the AI",
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
# 4b. The FACTION step - the new first half of each player's turn
# --------------------------------------------------------------------------
print("\n=== 4b. the faction step ===")

from game.ui.army_select import STAGE_FACTION, STAGE_LIST  # noqa: E402

# The grouping is DERIVED from ArmyList.faction_keyword and named from the
# Faction the rules already carry - never written down a second time.
factions = army_lists.factions()
c.eq("one entry per faction that has a list",
     [f.key for f in factions],
     ["AELDARI", "ORKS", "NECRONS", "T'AU EMPIRE", "DEATH GUARD"])
c.eq("...in ARMY_LISTS order, so adding a list cannot reshuffle the tiles",
     [f.key for f in factions],
     list(dict.fromkeys(e.faction_keyword for e in army_lists.ARMY_LISTS)))
c.true("each carries its display name", all(f.name and f.name != f.key for f in factions))
c.true("...its badge", all(sprites.faction_logo_path(f.faction_keyword) for f in factions))
c.true("...and its army rule", all(f.army_rule for f in factions))
c.eq("every list is reachable through exactly one faction",
     sorted(e.key for f in factions for e in f.lists),
     sorted(e.key for e in army_lists.ARMY_LISTS))
c.eq("lists_for names one faction's lists", [e.key for e in army_lists.lists_for("ORKS")], ["orks"])
c.eq("faction_of goes the other way", army_lists.faction_of("tau"), "T'AU EMPIRE")

# A faction with SEVERAL lists is the shape that is coming, and the grouping
# has to hold it - checked against a real multi-list faction rather than
# against today's one-each registry, which would pass either way.
grouped = army_lists.factions(multi_list_faction(3))
c.eq("three lists of one faction group into ONE tile", len(grouped), 1)
c.eq("...carrying all three", len(grouped[0].lists), 3)

# The four steps, in order.
steps = ArmySelectScreen()
c.eq("it opens on Player 1's FACTION", (steps.current_player, steps.stage),
     ("Player 1", STAGE_FACTION))
c.eq("...offering factions, not lists", [i.key for i in steps.items], [f.key for f in factions])
steps.choose("ORKS")
c.eq("then Player 1's LIST", (steps.current_player, steps.stage), ("Player 1", STAGE_LIST))
c.eq("...offering only that faction's lists", [i.key for i in steps.items], ["orks"])
c.eq("...and no list is recorded yet", steps.choices.get("Player 1"), None)
steps.choose("orks")
c.eq("only then is Player 1's list recorded", steps.choices["Player 1"], "orks")
c.eq("...and it moves to Player 2's FACTION", (steps.current_player, steps.stage),
     ("Player 2", STAGE_FACTION))
steps.choose("NECRONS")
steps.choose("necrons")
c.true("done after four answers", steps.done)
c.eq("both players fielded what was picked", steps.choices,
     {"Player 1": "orks", "Player 2": "necrons"})

# BACK walks one STEP, which is the whole point of splitting the question.
walk = ArmySelectScreen()
walk.choose("ORKS")
walk.back()
c.eq("Back from a list step returns to the faction", walk.stage, STAGE_FACTION)
c.eq("...and forgets that faction", walk.factions_chosen.get("Player 1"), None)
walk.choose("AELDARI")
c.eq("...so another faction can be picked", [i.key for i in walk.items],
     ["aeldari", "aeldari_warhost", "aeldari_warhost_guardians"])
c.eq("Back at the very first step does nothing", ArmySelectScreen().back(), False)

# Changing faction after a list was already recorded must DROP that list -
# otherwise Back-then-forward finishes with an Ork faction and an Aeldari list.
swap = ArmySelectScreen()
swap.choose("orks")            # answers both of Player 1's steps
swap.back()                    # back to Player 1's list step
swap.back()                    # back to Player 1's faction step
swap.choose("AELDARI")
c.eq("re-picking a faction clears the list under it", swap.choices.get("Player 1"), None)
c.eq("...and offers the new faction's lists", [i.key for i in swap.items],
     ["aeldari", "aeldari_warhost", "aeldari_warhost_guardians"])

# A key from the wrong step is refused rather than stored.
wrong = ArmySelectScreen()
try:
    wrong.select("orks")
    c.true("a list key is refused at the faction step", False)
except KeyError:
    c.true("a list key is refused at the faction step", True)
wrong.choose("ORKS")
try:
    wrong.select("NECRONS")
    c.true("a faction key is refused at the list step", False)
except KeyError:
    c.true("a faction key is refused at the list step", True)

# choose(list) still answers BOTH steps in one call - what --army1, a saved
# scene and the headless harnesses rely on, and the reason the click path could
# be split in two without touching any of them.
short = ArmySelectScreen()
short.choose("death_guard")
c.eq("a list key answers both questions at once", short.choices["Player 1"], "death_guard")
c.eq("...recording the faction it belongs to", short.factions_chosen["Player 1"], "DEATH GUARD")
c.eq("...and moving on to the next player", short.current_player, "Player 2")
# ...from EITHER step, and across factions: the shortcut rewinds first. This is
# also the case that used to recurse for ever, because army_lists.get() lower
# cases and "AELDARI" lands on "aeldari".
across = ArmySelectScreen()
across.choose("ORKS")
across.choose("aeldari")
c.eq("the shortcut works from the list step too", across.choices["Player 1"], "aeldari")
c.eq("...replacing the faction that was on screen", across.factions_chosen["Player 1"], "AELDARI")

# The faction step draws: badge, name, list count, and NO portrait grid.
faction_screen = ArmySelectScreen()
faction_tiles = faction_screen.layout(SCREEN_RECT)
c.true("a faction tile carries no portrait grid",
       all(not t.cells and not t.section_labels for t in faction_tiles))
c.true("faction tiles are inside the screen",
       all(SCREEN_RECT.contains(t.rect) for t in faction_tiles))
c.true("...and do not overlap",
       all(not a.rect.colliderect(b.rect)
           for i, a in enumerate(faction_tiles) for b in faction_tiles[i + 1:]))
c.true("...and are shorter than a list tile, having less to show",
       faction_tiles[0].rect.height < list_screen().layout(SCREEN_RECT)[0].rect.height)
faction_surface = pygame.Surface(SCREEN_RECT.size)
faction_screen.draw(faction_surface, (2, 2))
c.true("the faction step really draws something",
       any(faction_surface.get_at((x, y))[:3] != faction_surface.get_at((2, 2))[:3]
           for x in range(faction_tiles[0].rect.x, faction_tiles[0].rect.right, 7)
           for y in range(faction_tiles[0].rect.y, faction_tiles[0].rect.bottom, 7)))

# --------------------------------------------------------------------------
# 4c. A faction with TWO REAL lists
# --------------------------------------------------------------------------
print("\n=== 4c. the T'au have two lists ===")

# The two-step flow was built for "ich habe vor pro Volk mehrere listen
# anzulegen" and had nothing but multi_list_faction() to grow until now. The
# T'au ship two: Kauyon and Mont'ka, the same twenty-one entries under
# different detachments.
_tau_lists = army_lists.lists_for("T'AU EMPIRE")
c.eq("the T'au offer four lists",
     [e.key for e in _tau_lists],
     ["tau", "tau_montka", "tau_retaliation", "tau_recon"])
c.eq("...with different names, or the second step would show four of the same",
     len({e.name for e in _tau_lists}), 4)
# Read off .detachment - the FIRST of each list's tuple - because the Recon list
# is the first anywhere to field THREE detachments at once, and a tile, a log
# line and a saved scene all want a single name.
c.eq("...and different lead detachments",
     [e.detachment for e in _tau_lists],
     ["Kauyon", "Mont'ka", "Retaliation Cadre", "Advanced Acquisition Cadre"])
# THREE, not four: the Prototypes list was retired on user request, and it was
# the only one declaring Disruption - so Death Trap is dormant again. Named
# rather than quietly relaxed; test_force_dispositions.py carries the same fact
# on the mission side.
c.eq("...and THREE different Primary Missions between them",
     len({e.force_disposition for e in _tau_lists}), 3)

# The screen really offers both at step two, and picking the second answers
# with the second - which is the whole point of splitting the question.
_two = ArmySelectScreen()
_two.select("T'AU EMPIRE")
_two.confirm()
c.eq("picking the T'au leads to all of their lists",
     [e.key for e in _two._step_items()],
     ["tau", "tau_montka", "tau_retaliation", "tau_recon"])
_two.select("tau_montka")
_two.confirm()
c.eq("...and choosing the second one is what the player gets",
     _two.choices.get("Player 1"), "tau_montka")

# Back from the list step returns to the faction step, which is the reason the
# two are separate steps at all - and now has something to go back FOR.
_two.back()
c.eq("Back returns to that faction's list step",
     [e.key for e in _two._step_items()],
     ["tau", "tau_montka", "tau_retaliation", "tau_recon"])
_two.back()
c.eq("...and again to the factions",
     [e.key for e in _two._step_items()],
     [f.key for f in army_lists.factions()])

# The one-call shortcut still answers both questions at once, which is what
# --army1, a snapshot and the ten harnesses use.
_short = ArmySelectScreen()
_short.choose("tau_montka")
c.eq("choose() still answers straight through to the second list",
     _short.choices.get("Player 1"), "tau_montka")


# --------------------------------------------------------------------------
# 5. Tiles: name/logo/detachment, and one portrait per unit
# --------------------------------------------------------------------------
print("\n=== 5. tile layout ===")

screen = list_screen(lists=multi_list_faction())
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
# The Aeldari list is the case that motivated it: six of its eleven units are
# attached (19.01), and an attached unit's single portrait is its CHARACTER,
# so before the split those six mobs were invisible.
# Its own screen, on the AELDARI faction: the tiles above are five lists of one
# faction, which is what the pager and the shared cell size need, and this is
# about one specific list's contents.
aeldari_screen = list_screen(faction="AELDARI")
aeldari_tile = next(t for t in aeldari_screen.layout(SCREEN_RECT)
                    if t.entry.key == "aeldari")
character_labels = [e.label for e in aeldari_tile.characters]
squad_labels = [e.label for e in aeldari_tile.units]
# NINE, not the six attached leaders alone: a standalone character counts too,
# and Warlock Skyrunners is a one-model CHARACTER unit that belongs here rather
# than under SQUADS. The ninth is the Avatar of Khaine, and he is the reason
# this pair of numbers moved in OPPOSITE directions when the list lost an
# entry: he replaced two SQUAD entries (Falcon, Shining Spears) with a
# CHARACTER one, so the split shifted 12/8 -> 10/9.
c.eq("every attached leader is listed as a character", len(character_labels), 9)
c.true("...naming them by datasheet, not by squad id",
       "Farseer" in character_labels and "Eldrad Ulthran" in character_labels)
c.true("...including a standalone character with no LEADER line",
       "Avatar of Khaine" in character_labels)
c.eq("...and every unit is listed as a squad", len(squad_labels), 10)
c.true("the mobs the characters lead are now visible in their own right",
       {"Guardian Defenders", "Storm Guardians", "Dire Avengers",
        "Howling Banshees", "Warp Spiders"} <= set(squad_labels))
c.true("a bodyguard is never filed as a character",
       not ({"Guardian Defenders", "Storm Guardians"} & set(character_labels)))

# A standalone CHARACTER unit belongs in the character column even though it
# was never attached to anything - which is what the keyword is read for.
necron_tile = next(t for t in list_screen(faction="NECRONS").layout(SCREEN_RECT)
                   if t.entry.key == "necrons")
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
#
# THE SUBJECT IS THE TILE WITH THE MOST SQUADS, not the one with the most
# cells, and that is the same distinction _cell_size() spells out: the
# CHARACTER rows are reserved at the page maximum for every tile, so a tile is
# as tall as "everyone's character rows + its own squad rows" and the tile that
# reaches the bottom is whichever has the most squad ROWS. This check named the
# most-cells tile and passed anyway for as long as the two happened to be the
# same tile - with 12 Aeldari squads and 14 Ork ones at 5 columns both came to
# 3 rows. Dropping the Falcon and the Shining Spears took the Aeldari list to
# 10 squads (2 rows) and broke the coincidence, leaving that tile legitimately
# 108 px short at the bottom. Same species of latent test bug the layout's own
# comment records, and fixed the same way: ask the question the layout answers.
tallest = max(tiles, key=lambda t: len(t.units))
lowest_cell = max(r.bottom for r, _e in tallest.cells)
c.eq(f"the fullest tile ({tallest.entry.key}) reaches its bottom edge",
     tallest.rect.bottom - lowest_cell <= 40, True)
# Relative to the tile, not an absolute pixel count: the test window is
# smaller than a real one, and the point is that a portrait is a picture
# rather than an icon.
# Keyed off the tiles on screen rather than a list name: these are now five
# lists of ONE faction, so the keys are that faction's, not the registry's.
c.true("portraits are a sizeable share of the tile",
       cell_sizes[tiles[0].entry.key] >= tiles[0].rect.width // 8)

# The cell size is derived, not fixed: a small window has to fit the same
# number of units into a smaller tile.
small = list_screen(lists=multi_list_faction())
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
# ...and for the player currently choosing, not for a fixed one. Any of this
# faction's lists will do - the point is WHO the previews are built for.
screen.choose(screen.items[0].key)
p2_tiles = screen.layout(SCREEN_RECT)
c.true("step 2's tiles are built for Player 2",
       all(s.owner == "Player 2" for t in p2_tiles for s in t.squads))


# --------------------------------------------------------------------------
# 6. Hit tests and hover detail
# --------------------------------------------------------------------------
print("\n=== 6. hover and click ===")

# Hit tests and hover are about LIST tiles - portraits only exist there - so
# this runs on step two, with several lists of one faction on screen.
screen = list_screen(lists=multi_list_faction())
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

# TWO BEATS. User: "erst auswaehlen, dann wird die entsprechende kachel
# gehighlightet und dann auf den auswahl button unten druecken." A left click
# SELECTS; only the footer button fields the list.
screen.handle_event(
    pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": tiles[2].rect.center, "button": 1}),
    SCREEN_RECT)
c.eq("clicking a tile selects that list", screen.selected_key, tiles[2].entry.key)
c.eq("...and fields nothing yet", screen.choices.get("Player 1"), None)
c.eq("...so the step has not advanced", screen.current_player, "Player 1")
screen.handle_event(
    pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": tiles[0].rect.center, "button": 1}),
    SCREEN_RECT)
c.eq("clicking another moves the selection", screen.selected_key, tiles[0].entry.key)
screen.draw(pygame.Surface(SCREEN_RECT.size), (2, 2))
c.true("a confirm button appears once a list is selected", screen.footer.confirm is not None)
screen.handle_event(
    pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                       {"pos": screen.footer.confirm.center, "button": 1}),
    SCREEN_RECT)
c.eq("pressing Confirm fields the selected list",
     screen.choices.get("Player 1"), tiles[0].entry.key)
c.eq("...and the next player starts with nothing selected", screen.selected_key, None)

# A right click goes back a step.
screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (5, 5), "button": 3}),
                    SCREEN_RECT)
c.eq("right-click goes back", screen.current_player, "Player 1")
c.eq("...and clears the selection it had", screen.selected_key, None)

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
# Step two again: the hover card is a portrait's, and portraits are on LIST
# tiles. The faction step gets its own drawing checks in section 4b.
screen = list_screen(lists=multi_list_faction())
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
plain_screen = list_screen(lists=multi_list_faction())
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
c.true("step 2 offers a Back button", step2.footer.back is not None)
step1 = ArmySelectScreen()
step1.draw(pygame.Surface(SCREEN_RECT.size), (2, 2))
c.eq("step 1 has nothing to go back to", step1.footer.back, None)


# --------------------------------------------------------------------------
# 7b. Pagination - what happens with more lists than fit on one screen
# --------------------------------------------------------------------------
print("\n=== 7b. pagination ===")

# Paging now belongs to STEP TWO, and that is the point of the change: the
# first step lists five factions, the second lists one faction's lists, and it
# is the second that will grow ("ich habe vor pro Volk mehrere listen
# anzulegen"). So the pager is exercised against five lists of ONE faction -
# the shape that is coming - rather than against five factions, which is what
# it used to be and no longer says anything about a list pager.
five = multi_list_faction()
paged = list_screen(lists=five)
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
       paged.footer.prev is not None and paged.footer.next is not None)
paged.handle_event(
    pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": paged.footer.next.center, "button": 1}),
    SCREEN_RECT)
c.eq("clicking Next pages forward", paged.page, 1)
c.eq("...and chooses nothing", paged.choices, {})
paged.handle_event(
    pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": paged.footer.prev.center, "button": 1}),
    SCREEN_RECT)
c.eq("clicking Prev pages back", paged.page, 0)

# A list picked on page 2 is still the list that gets fielded.
paged.turn_page(1)
paged.layout(SCREEN_RECT)
paged.handle_event(
    pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                       {"pos": paged.tiles[0].rect.center, "button": 1}),
    SCREEN_RECT)
c.eq("a tile on a later page can be selected", paged.selected_key, five[3].key)
# The selection SURVIVES paging - it is an answer, not a pointer position - and
# the button names it, so confirming from another page is not a surprise.
paged.turn_page(-1)
c.eq("...and paging away does not lose it", paged.selected_key, five[3].key)
c.true("...the confirm label names it", five[3].name in paged.confirm_label)
paged.confirm()
c.eq("...so it is the list that gets fielded",
     paged.choices.get("Player 1"), five[3].key)

# With three lists there is one page and no pager chrome at all - checked
# against an explicit three, not against the registry, so adding a fifth list
# later cannot quietly turn this into a different assertion.
single = ArmySelectScreen(lists=army_lists.ARMY_LISTS[:3])
single.draw(pygame.Surface(SCREEN_RECT.size), (2, 2))
c.eq("three lists need no pager", single.page_count, 1)
c.true("...so no pager buttons are drawn",
       single.footer.prev is None and single.footer.next is None)
c.eq("...and turning the page does nothing", single.turn_page(1), False)

# How many tiles a ROW holds FOLLOWS THE WINDOW: a fixed count would either
# waste a wide screen or cramp a narrow one, and both were measured. This is
# the LIST step, which is still one row of tall tiles - see 7c for the step
# that stopped being a row.
#
# THESE CHECKS USED TO DRIVE THE FACTION STEP while sitting under a heading
# that says paging "now belongs to STEP TWO". They do now.
wide = list_screen(lists=multi_list_faction())
wide_tiles = wide.layout(pygame.Rect(0, 0, 1920, 1080))
c.eq("a 1920-wide screen fits four tiles per page", wide.tiles_per_page, 4)
c.eq("...and five lists need a second page", wide.page_count, 2)
c.true("...and the tiles are still large", wide_tiles[0].rect.width >= 400)

narrow = list_screen(lists=multi_list_faction())
narrow_tiles = narrow.layout(pygame.Rect(0, 0, 1366, 768))
c.eq("a 1366-wide screen fits three", narrow.tiles_per_page, 3)
c.eq("...and pages the fourth", narrow.page_count, 2)
c.true("...without the tiles dropping below the readable width",
       narrow_tiles[0].rect.width >= 400)
c.true("...and every portrait still inside its tile",
       all(t.rect.contains(r) for t in narrow_tiles for r, _e in t.cells))

# Never more than four ACROSS, however wide the screen: past that an item is
# easier to compare by paging than by scanning sideways.
huge = list_screen(lists=multi_list_faction())
huge.layout(pygame.Rect(0, 0, 3840, 2160))
c.eq("a very wide screen still shows at most four", huge.tiles_per_page, 4)

# A page index left over from a wider window must not survive into a narrower
# one - it would index past the end and show an empty screen.
shrunk = list_screen(lists=multi_list_faction())
shrunk.layout(pygame.Rect(0, 0, 1920, 1080))
shrunk.turn_page(1)
c.eq("paged to the last page on a wide screen", shrunk.page, 1)
shrunk.layout(pygame.Rect(0, 0, 1024, 720))
c.true("a narrower window clamps the page rather than showing nothing",
       shrunk.page < shrunk.page_count and len(shrunk.tiles) > 0)


# --------------------------------------------------------------------------
# 7c. The faction step is a GRID, so its pager arrives much later
# --------------------------------------------------------------------------
print("\n=== 7c. the faction grid ===")

# User: "bei der volkauswahl im pregame ist jetzt viel verschwendeter platz,
# weil die volk kacheln sehr klein sind. die koennen sich in einem grid
# anordnen statt nur nebeneinander. so sollte die paginierung dann erst sehr
# spaet einsetzen."
for width, height, want_columns in ((1920, 1080, 4), (1366, 768, 3), (1280, 720, 2)):
    grid = ArmySelectScreen()
    tiles = grid.layout(pygame.Rect(0, 0, width, height))
    xs = sorted({t.rect.x for t in tiles})
    ys = sorted({t.rect.y for t in tiles})
    want_rows = -(-5 // want_columns)
    c.eq(f"{width}x{height}: the same column count a row would have had",
         len(xs), want_columns)
    c.eq(f"...and the five factions WRAP onto {want_rows} rows", len(ys), want_rows)
    c.eq(f"...all on one page ({width})", grid.page_count, 1)
    c.true(f"...tiles do not overlap ({width})",
           all(not a.rect.colliderect(b.rect)
               for i, a in enumerate(tiles) for b in tiles[i + 1:]))
    c.true(f"...and every one is inside the band ({width})",
           all(ts.tile_area(pygame.Rect(0, 0, width, height)).contains(t.rect)
               for t in tiles))

# The grid BLOCK is centred in the band rather than pinned to the top. Pinned,
# a short grid reads as one row nailed to the ceiling over a void - which is
# the "verschwendeter platz" being reported.
centred = ArmySelectScreen()
tiles = centred.layout(pygame.Rect(0, 0, 1600, 900))
band = ts.tile_area(pygame.Rect(0, 0, 1600, 900))
top_gap = min(t.rect.y for t in tiles) - band.y
bottom_gap = band.bottom - max(t.rect.bottom for t in tiles)
c.true(f"the grid is centred vertically ({top_gap} vs {bottom_gap})",
       abs(top_gap - bottom_gap) <= 1)

# WHAT THE GRID BUYS, as the number the request asks for. Measured against the
# single row it replaced: 4 across at 1920, so five factions paged.
deep = ArmySelectScreen()
deep.layout(pygame.Rect(0, 0, 1920, 1080))
c.eq("five real factions no longer page at all", deep.page_count, 1)
big = ArmySelectScreen(lists=many_factions(24))
big.layout(pygame.Rect(0, 0, 1920, 1080))
c.eq("...and neither do twenty-four", big.page_count, 1)
c.true(f"...one page holds {big.tiles_per_page}, where a row held 4",
       big.tiles_per_page > 4 * 2)
huge_grid = ArmySelectScreen(lists=many_factions(60))
huge_grid.layout(pygame.Rect(0, 0, 1920, 1080))
c.true("the pager does still arrive eventually", huge_grid.page_count > 1)
c.true("...and its pages are not empty",
       len(huge_grid.layout(pygame.Rect(0, 0, 1920, 1080))) > 0)

# The clamp, on the step that can now actually page.
clamped = ArmySelectScreen(lists=many_factions(60))
clamped.layout(pygame.Rect(0, 0, 1920, 1080))
clamped.turn_page(1)
clamped.layout(pygame.Rect(0, 0, 1024, 700))
c.true("a faction page index is clamped into a narrower window",
       clamped.page < clamped.page_count and len(clamped.tiles) > 0)

# THE CARDS GREW, which is the other half of the sentence ("die volk kacheln
# sehr klein"). Measured against the minimum the content needs, and against the
# cap that keeps the growth carried by ART rather than by padding.
grown = ArmySelectScreen()
grown_tiles = grown.layout(pygame.Rect(0, 0, 1920, 1080))
floor = grown._faction_tile_min_height()
c.true(f"a faction card is taller than its bare content "
       f"({grown_tiles[0].rect.height} > {floor})",
       grown_tiles[0].rect.height > floor)
c.true("...but not taller than a card holding the largest badge",
       grown_tiles[0].rect.height
       <= 2 * army_select.TILE_PAD + army_select.FACTION_LOGO_MAX_PX)
c.true("...and still wider than it is tall, so it reads as a card",
       grown_tiles[0].rect.width > grown_tiles[0].rect.height)

# THE BADGE GROWS WITH THE CARD, measured on PIXELS. Without this the growth is
# padding and the card becomes the "mostly empty space [that] reads as
# something failing to load" this screen's own layout rule rules out - and the
# A/B probe that pins the badge back at LOGO_PX came back 328/328, a finding
# about this suite rather than about the code.
grown_surface = pygame.Surface((1920, 1080))
grown.draw(grown_surface, (-1, -1))
badge_tile = grown_tiles[0].rect
# The VERTICAL extent of ink in a column exactly LOGO_PX wide at the card's
# left edge. Both halves of that matter: the name starts at
# TILE_PAD + logo_px + 14, so a column this narrow can only ever contain the
# badge whatever size it is drawn at - the first version of this check used a
# FACTION_LOGO_MAX_PX-wide band, caught the name, and passed with the badge
# pinned back at LOGO_PX. And the vertical extent is what separates the two
# sizes; horizontally these logos are a few px narrower than tall.
badge_x = badge_tile.x + army_select.TILE_PAD
badge_ys = [y
            for y in range(badge_tile.y + 1, badge_tile.bottom - 1)
            for x in range(badge_x, badge_x + army_select.LOGO_PX)
            if grown_surface.get_at((x, y))[:3] not in
            (army_select.BG_COLOR, ts.TILE_BG_COLOR, ts.TILE_BORDER_COLOR)]
badge_px = (max(badge_ys) - min(badge_ys) + 1) if badge_ys else 0
c.true(f"the badge grew with the card ({badge_px}px, printed size is {army_select.LOGO_PX})",
       badge_px > army_select.LOGO_PX)
c.true("...without exceeding its own cap",
       badge_px <= army_select.FACTION_LOGO_MAX_PX)
# The counter-check: it must still FIT the card, or "bigger" would be satisfied
# by art spilling over the card's edges.
c.true("...and stays inside the card",
       badge_px <= badge_tile.height - 2 * army_select.TILE_PAD)
# The growth is "use what is left over", not "always be big": a page carrying
# four rows gets much shorter cards than a page carrying two, and they stay off
# the cap. MEASURED rather than asserted as "exactly the floor" - four rows of
# the minimum still leave 76px of an 1280x720 band over, and those get shared
# out, so the floor is a lower bound and not the answer.
tight = ArmySelectScreen(lists=many_factions(24))
tight_tiles = tight.layout(pygame.Rect(0, 0, 1280, 720))
tight_h = tight_tiles[0].rect.height
c.true(f"a deep page gets shorter cards than a shallow one "
       f"({tight_h} < {grown_tiles[0].rect.height})",
       tight_h < grown_tiles[0].rect.height)
c.true("...at or above the minimum", tight_h >= tight._faction_tile_min_height())
c.true("...and nowhere near the cap",
       tight_h < 2 * army_select.TILE_PAD + army_select.FACTION_LOGO_MAX_PX)
# ...and the rows it does use FILL the band, which is the point of growing at
# all. Within one row gap, because the height is an integer share.
tight_rows = len(sorted({t.rect.y for t in tight_tiles}))
band720 = ts.tile_area(pygame.Rect(0, 0, 1280, 720))
spent = tight_rows * tight_h + ts.TILE_GAP * (tight_rows - 1)
c.true(f"...while filling the band ({spent} of {band720.height})",
       band720.height - spent <= tight_rows)


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
# See test_map_select.py's twin of this check: main() is ONE BATTLE now, so a
# screen that is abandoned answers the menu with QUIT and run() - the
# application loop around main() - is what closes the window.
c.true("...and abandoning it answers the menu's QUIT",
       re.search(r"if chosen is None:\s*\n\s*return game_menu_module\.QUIT", main_src) is not None)
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
# Two lists from DIFFERENT factions, and that is load-bearing rather than
# tidy: the check below tells P1's contributions from P2's by matching the name
# MINUS its owner digit, so it needs two lists whose unit names do not overlap.
# Taking ARMY_LISTS[0] and [1] used to do that by accident and stopped the day a
# faction got a second list - two Aeldari lists share half their datasheets, and
# the failure looks like a bug in roster_for() rather than like a sample that
# went stale. The disjointness is asserted, so a future overlap says so here.
_first = army_lists.ARMY_LISTS[0].key
_second = next(e.key for e in army_lists.ARMY_LISTS
               if e.faction_keyword != army_lists.ARMY_LISTS[0].faction_keyword)
_p1 = sorted(s.name for s in army_lists.preview_squads(_first, "Player 1"))[:2]
_p2 = sorted(s.name for s in army_lists.preview_squads(_second, "Player 1"))[:2]
c.true("the two sampled lists share no unit name",
       not ({n[2:] for n in _p1} & {n[2:] for n in _p2}))


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


# --------------------------------------------------------------------------
# 7d. the tile HEADER: nothing overlaps, nothing runs out the side
# --------------------------------------------------------------------------
print(chr(10) + "=== 7d. the tile header ===")

# User, with a screenshot: "Oben ueberlagert sich text". Two faults in one
# picture, and 352 checks saw neither, because nothing here had ever measured
# the header:
#   * the NAME is wrapped, but the height assumed a flat four lines - so
#     "T'au Empire (Prototypes)" on a four-tile page pushed the three lines
#     under it into the summary line;
#   * the detachment and disposition lines were not wrapped at all, so
#     "Auxiliary Cadre + Experimental Prototype Cadre (2 DP)" simply ran out
#     past the tile's own edge into its neighbour.
# The T'au page is the reported case: four lists, so four tiles, so the
# narrowest a list tile gets.
from game.ui.army_select import (  # noqa: E402
    LOGO_PX, LOGO_TEXT_GAP, TILE_PAD as _TILE_PAD,
)

# 1920x1080 on purpose, not this file's usual 1600x900: four tiles fit there,
# which is the page the user photographed and the narrowest a list tile gets.
HDR_RECT = pygame.Rect(0, 0, 1920, 1080)
hdr_screen = ArmySelectScreen()
hdr_screen.select("T'AU EMPIRE")
hdr_screen.confirm()
hdr_tiles = hdr_screen.layout(HDR_RECT)
c.eq("the T'au page shows all four lists side by side", len(hdr_tiles), 4)

over_edge = []
into_summary = []
for tile in hdr_tiles:
    text_width = hdr_screen._header_text_width(tile.rect.width)
    blocks = hdr_screen._header_blocks(tile.entry, text_width)
    for font, _colour, lines in blocks:
        for line in lines:
            if font.size(line)[0] > text_width:
                over_edge.append((tile.entry.key, line))
    # Where the header's text really ends, against where the summary line
    # starts (grid_top - label height - 8, see _draw_tile).
    text_bottom = tile.rect.y + _TILE_PAD + hdr_screen._blocks_height(blocks)
    summary_top = (hdr_screen._grid_top(tile)
                   - hdr_screen.label_font.get_height() - 8)
    if text_bottom > summary_top:
        into_summary.append((tile.entry.key, text_bottom - summary_top))

c.eq("no header line runs out past its tile", over_edge, [])
c.eq("...and none of them reaches the summary line", into_summary, [])

# The reported case was "T'au Empire (Prototypes)", whose tile name wraps at
# this width - which is what makes the case worth pinning rather than hoping.
# That list has since been retired, so this takes the LONGEST name on the page
# instead of naming one: the assertion is about a name that wraps, not about
# which list happens to own it. It used to be guarded with `if proto:`, which
# meant it quietly measured nothing the moment that list went away.
longest = max(hdr_tiles, key=lambda t: len(t.entry.name))
name_lines = hdr_screen._header_blocks(
    longest.entry, hdr_screen._header_text_width(longest.rect.width))[0][2]
c.true("the longest list name on the page really does wrap here (%r)"
       % longest.entry.name, len(name_lines) > 1)

# The height REACTS to that: a name that wraps costs a line, and the header
# grows by one rather than letting the block below it run over.
one_line = hdr_screen._header_height(hdr_screen.items, 4000)
c.true("a wide column needs a shorter header than a narrow one",
       one_line < hdr_screen._header_height(
           hdr_screen.items, hdr_screen._header_text_width(hdr_tiles[0].rect.width)))

# Every tile on the page starts its grid at the SAME y - that is what makes two
# lists comparable side by side, and it is why the height is a page-wide
# worst case rather than each tile's own.
c.eq("every tile starts its grid at the same height",
     len(set(hdr_screen._grid_top(t) - t.rect.y for t in hdr_tiles)), 1)

# The text column leaves room for the badge whether or not the art exists - a
# tile whose text starts somewhere else because a file is missing is worse
# than a little empty space.
c.eq("the text column is the tile minus its padding and the badge",
     hdr_screen._header_text_width(400), 400 - 2 * _TILE_PAD - (LOGO_PX + LOGO_TEXT_GAP))

c.finish()
