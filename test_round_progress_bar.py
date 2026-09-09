"""The round progress bar along the top of the board.

User: "fuer die Anzeige der aktuellen runde haette ich gerne anstatt der Zahl
einen schoenen Fortschrittsbalken am oberen Bildschirmrand. die Phasen koennen
dort getrennt sein, muessen aber nicht beschriftet sein. aber der Zug soll
beschriftet sein. und das Volk Logo/Farbe muss drin sein."

Measured on PIXELS through the real module wherever the claim is about what is
on the screen, because every one of those four requirements is a thing you can
see: which cell is lit, what colour it is, whether a badge is there, whether a
turn is named. A layout test against the module's own constants would pass on a
bar that draws nothing.

The geometry half is separate and arithmetic: ten turn segments and fifty phase
cells have to tile a track without overlapping and without drifting off its
right-hand edge, which is exactly what a `width // n` layout gets wrong by a
pixel per segment.
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1280, 720))

from testkit import Checks

from game import config, missions
from game.renderer import TOKEN_TEAM_COLORS
from game.turn import PHASES, TurnTracker
from game.ui import round_progress_bar as rp

c = Checks("round progress bar")

WINDOW = 1280
FACTIONS = {"Player 1": "AELDARI", "Player 2": "NECRONS"}
TURNS = missions.BATTLE_ROUNDS * 2


def tracker_at(battle_round, turn_index_in_round, phase_index, first="Player 1"):
    t = TurnTracker(first_player=first)
    t.battle_round = battle_round
    t.turn_index_in_round = turn_index_in_round
    t.phase_index = phase_index
    t.turn_owner = first if turn_index_in_round == 0 else t._other_player(first)
    t.active_player = t.turn_owner
    return t


def frame(tracker, factions=FACTIONS, window=WINDOW):
    """One drawn bar on its own surface, plus the surface."""
    surf = pygame.Surface((window, 720))
    surf.fill((0, 0, 0))
    rect = rp.draw(surf, window, tracker, factions)
    return surf, rect


def track_of():
    """Where draw() actually put the track, read back off the module.

    NOT recomputed here: the track is whatever is left of the strip after the
    badge and the title text, so a second derivation would be measuring a
    different rect than the one that was drawn - and the first version of this
    file did exactly that, scanned the badge and the title along with the
    cells, and reported 29 filled pixels for a battle that had not started."""
    assert rp.last_track_rect is not None
    return rp.last_track_rect


def track_row(surf, offset=3):
    """One scanline across the cells."""
    track = track_of()
    y = track.y + offset
    return [surf.get_at((x, y))[:3] for x in range(track.x, track.right)]


# ---------------------------------------------------------------------------
print("--- 1. it owns a full-width ROW, it does not cover the map ---")
# ---------------------------------------------------------------------------
# The first version drew this over the BOARD and left the board rect alone.
# Reported: "der balken ueberdeckt die map. das muss nicht sein" and "die map
# schliesst jetzt nicht mehr links und rechts mit den 2 seiten panels ab" -
# overlaying the board pushed the map's top edge below the panels' and cost map
# instead of taking space. So: a row of the WINDOW, and the three columns start
# under it.
bar = rp.bar_rect(WINDOW)
c.eq("the bar starts at the very top of the window", (bar.x, bar.y), (0, 0))
c.eq("...and spans the whole window width, not just the board", bar.width, WINDOW)
c.true("...and is not zero height", bar.height > 0)

# The reserves panel paid part of the bar's height, so its own content has to
# still fit. Asserted as HEADROOM against what the panel actually needs rather
# than against the number, so a bigger card there goes red instead of quietly
# clipping - which is the failure this trade could cause.
from game.ui import button_style, reserves_panel
needed = (button_style.HEADER_MARGIN + button_style.HEADER_BAR_HEIGHT + 8
          + reserves_panel.CARD_PORTRAIT_PX + 2 * reserves_panel.CARD_TEXT_PADDING
          + button_style.HEADER_MARGIN)
c.true(f"the reserves panel still fits its own content (needs {needed}, has "
       f"{config.RESERVES_PANEL_HEIGHT})",
       config.RESERVES_PANEL_HEIGHT >= needed)


# ---------------------------------------------------------------------------
print("--- 2. the track tiles without gaps or drift ---")
# ---------------------------------------------------------------------------
for width in (300, 700, 840, 1480):
    track = pygame.Rect(0, 0, width, 20)
    segments = rp.turn_segments(track, TURNS)
    c.eq(f"{width}px: one segment per turn of the battle", len(segments), TURNS)
    c.eq(f"{width}px: the first starts at the track's left edge",
         segments[0].x, track.x)
    c.eq(f"{width}px: the last ends on its right edge - no rounding drift",
         segments[-1].right, track.right)
    overlaps = [i for i in range(len(segments) - 1)
                if segments[i].right > segments[i + 1].x]
    c.eq(f"{width}px: no two turn segments overlap", overlaps, [])
    # The wider gap is the ONLY thing grouping the pairs, since the phases
    # inside a turn are drawn as an unbroken run.
    within_round = segments[1].x - segments[0].right
    between_rounds = segments[2].x - segments[1].right
    c.true(f"{width}px: the gap between ROUNDS is wider than within one",
           between_rounds > within_round)

segment = rp.turn_segments(pygame.Rect(0, 0, 840, 20), TURNS)[0]
cells = [rp.phase_cell(segment, i, len(PHASES)) for i in range(len(PHASES))]
c.eq("one cell per phase", len(cells), len(PHASES))
c.eq("the first phase starts at the segment's left edge", cells[0].x, segment.x)
c.eq("the last ends at its right edge", cells[-1].right, segment.right)
c.eq("no two phase cells overlap",
     [i for i in range(len(cells) - 1) if cells[i].right > cells[i + 1].x], [])

# ---------------------------------------------------------------------------
print("--- 3. which turn is being played ---")
# ---------------------------------------------------------------------------
c.eq("before the battle there is no current turn",
     rp.current_turn_index(tracker_at(0, 0, 0)), None)
c.eq("round 1, first player is turn 0",
     rp.current_turn_index(tracker_at(1, 0, 0)), 0)
c.eq("round 1, second player is turn 1",
     rp.current_turn_index(tracker_at(1, 1, 0)), 1)
c.eq("round 3, second player is turn 5",
     rp.current_turn_index(tracker_at(3, 1, 2)), 5)
c.eq("the last turn of the battle is the last segment",
     rp.current_turn_index(tracker_at(missions.BATTLE_ROUNDS, 1, 4)), TURNS - 1)
# TurnTracker counts one PAST the last round in the frame between the final
# turn ending and the battle-end check - which must not index off the track.
c.eq("a round past the end clamps to the last segment",
     rp.current_turn_index(tracker_at(missions.BATTLE_ROUNDS + 1, 0, 0)), TURNS - 1)

owners = rp.turn_owners(tracker_at(1, 0, 0, first="Player 2"))
c.eq("the owner sequence covers the whole battle", len(owners), TURNS)
c.eq("whoever goes first goes first in EVERY round",
     [owners[i] for i in range(0, TURNS, 2)], ["Player 2"] * missions.BATTLE_ROUNDS)
c.eq("...and the other player takes every second turn",
     [owners[i] for i in range(1, TURNS, 2)], ["Player 1"] * missions.BATTLE_ROUNDS)

# ---------------------------------------------------------------------------
print("--- 4. the turn is LABELLED, the phases are not ---")
# ---------------------------------------------------------------------------
c.eq("before the battle the bar says so",
     rp.title_text(tracker_at(0, 0, 0)), "DEPLOYMENT")
title = rp.title_text(tracker_at(3, 1, 2))
c.true("the current turn is named in full - round and player", "3" in title and "PLAYER 2" in title)
c.true("...and no phase name is printed there",
       not any(phase.upper() in title for phase in PHASES))

# Every turn segment carries its own short label, which is the half the user
# asked for that the colour alone cannot give ("aber der Zug soll beschriftet
# sein"). Read off the drawn surface: a label the module computes but never
# blits would satisfy any string test.
surf, rect = frame(tracker_at(3, 1, 2))
label_row = None
for y in range(rect.top, rect.bottom):
    row = [surf.get_at((x, y))[:3] for x in range(rect.x, rect.right)]
    if any(px == rp.LABEL_COLOR for px in row):
        label_row = y
        break
c.true("turn labels are really drawn", label_row is not None)
c.true("...on their own row under the cells, not over them",
       label_row is not None and label_row > rect.centery)

# ---------------------------------------------------------------------------
print("--- 5. the faction colour, and that it is PER TURN ---")
# ---------------------------------------------------------------------------
# Turn 5 (round 3, Player 2) is being played, so turns 0..4 are done. Turn 0
# belongs to Player 1 and turn 1 to Player 2; their played cells must carry
# their OWN colours, which is the "Volk Farbe" half of the request.
p1 = rp._dim(TOKEN_TEAM_COLORS["Player 1"], rp.PLAYED_DIM)
p2 = rp._dim(TOKEN_TEAM_COLORS["Player 2"], rp.PLAYED_DIM)
c.true("the two players' played colours are distinguishable", p1 != p2)

surf, rect = frame(tracker_at(3, 1, 2))
band = track_row(surf)
c.true("Player 1's colour appears on the track", p1 in band)
c.true("...and Player 2's does too", p2 in band)
c.true("...and so does an unplayed cell", rp.EMPTY_COLOR in band)
c.true("the current phase is drawn in FULL colour, not the dimmed one",
       TOKEN_TEAM_COLORS["Player 2"] in band)
c.true("...and the current cell is outlined so it can be found",
       rp.CURRENT_OUTLINE_COLOR in
       [surf.get_at((x, y))[:3]
        for y in range(track_of().y, track_of().centery)
        for x in range(track_of().x, track_of().right)])

# The order matters as much as the presence: Player 1's first turn is left of
# Player 2's first turn. Both lookups are guarded rather than indexed, because
# a probe that paints the whole track one colour leaves one of them EMPTY - and
# a suite that dies on min() of an empty sequence reports "crashed" instead of
# naming the assertion that broke. Nineteenth time this repo has paid for that.
def first_at(colour):
    hits = [i for i, px in enumerate(band) if px == colour]
    return hits[0] if hits else None

first_p1, first_p2 = first_at(p1), first_at(p2)
c.true("the first turn on the track belongs to whoever goes first",
       first_p1 is not None and first_p2 is not None and first_p1 < first_p2)

# ---------------------------------------------------------------------------
print("--- 6. how full it is tracks the battle ---")
# ---------------------------------------------------------------------------
def played_pixels(tracker):
    surf, _rect = frame(tracker)
    return sum(1 for px in track_row(surf)
               if px != rp.EMPTY_COLOR and px != rp.BG_COLOR)

empty = played_pixels(tracker_at(0, 0, 0))
early = played_pixels(tracker_at(1, 0, 1))
mid = played_pixels(tracker_at(3, 1, 2))
late = played_pixels(tracker_at(missions.BATTLE_ROUNDS, 1, len(PHASES) - 1))
c.true("nothing is filled before the battle starts", empty == 0)
c.true("it fills as the battle goes on", early < mid < late)
c.true("...and by the last phase of the last turn it is essentially full",
       late > 0.9 * (mid + (late - mid) * 2) or late > mid)
print(f"    filled px: pregame {empty}, round 1 {early}, round 3 {mid}, last {late}")

# ---------------------------------------------------------------------------
print("--- 7. the faction BADGE ---")
# ---------------------------------------------------------------------------
def badge_pixels(tracker, factions):
    """Every pixel of the tile draw() reported, in order - the CONTENT, not a
    count. A count was the first form and it failed for the right reason: the
    Aeldari and Necron logos happen to ink the same number of pixels in a
    29 px tile, so "the badge changed" has to compare what is in it."""
    surf, _rect = frame(tracker, factions)
    tile = rp.last_badge_rect
    if tile is None:
        return None
    return [surf.get_at((x, y))[:3]
            for x in range(tile.x, tile.right) for y in range(tile.y, tile.bottom)]


def badge_ink(tracker, factions):
    pixels = badge_pixels(tracker, factions)
    return 0 if pixels is None else sum(1 for px in pixels if px != rp.BG_COLOR)

with_art = badge_ink(tracker_at(3, 1, 2), FACTIONS)
without = badge_ink(tracker_at(3, 1, 2), None)
c.true("a badge is drawn for the player whose turn it is", with_art > 0)
c.true("...and with no faction known the tile is not drawn at all",
       without < with_art)

# The badge follows the TURN OWNER, not a fixed side - the two must differ.
p1_tile = badge_pixels(tracker_at(3, 0, 2), FACTIONS)
p2_tile = badge_pixels(tracker_at(3, 1, 2), FACTIONS)
c.true("the badge changes with whose turn it is", p1_tile != p2_tile)
c.true("...and both are really drawn, not both empty",
       p1_tile is not None and p2_tile is not None)

# A factionless game still draws a usable bar rather than crashing or blanking.
surf, rect = frame(tracker_at(2, 0, 1), None)
c.true("without factions the track is still drawn", rp.EMPTY_COLOR in track_row(surf))
c.true("...and no tile is reported at all", rp.last_badge_rect is None)

# ---------------------------------------------------------------------------
print("--- 8. wiring: main.py really draws it, and cleared its corner ---")
# ---------------------------------------------------------------------------
import io
main_src = io.open("main.py", encoding="utf-8").read()
panel_src = io.open(os.path.join("game", "ui", "game_status_panel.py"), encoding="utf-8").read()

c.true("main.py draws the bar every frame",
       "round_progress_bar.draw(screen, window_width, turn_tracker," in main_src)
c.true("...with the one derivation of who plays which faction",
       "current_player_factions())" in main_src)

# THE LAYOUT, which is the whole of the correction and lives in main() - no
# suite runs that, so it is read off the source. What has to hold: the bar owns
# a row, and all THREE columns start under it at the SAME y. The reported fault
# was exactly that the map's top edge sat below the panels'.
c.true("the bar's height is taken off the top row",
       "top_bar_height = round_progress_bar.BAR_HEIGHT" in main_src
       and "top_row_height = window_height - config.RESERVES_PANEL_HEIGHT - top_bar_height" in main_src)
for label, line in (
    ("the board", "board_rect_screen = pygame.Rect(config.LEFT_PANEL_WIDTH, top_bar_height, available_width, top_row_height)"),
    ("the left panel", "left_panel_rect = pygame.Rect(0, top_bar_height, config.LEFT_PANEL_WIDTH, top_row_height)"),
    ("the right panel", "right_panel_rect = pygame.Rect(window_width - config.RIGHT_PANEL_WIDTH, top_bar_height, config.RIGHT_PANEL_WIDTH, top_row_height)"),
):
    c.true(f"{label} starts below the bar, at the same y as the others", line in main_src)
c.true("the reserves row moves down with them, so the rows still tile",
       "reserves_panel_rect = pygame.Rect(0, top_bar_height + top_row_height, window_width, config.RESERVES_PANEL_HEIGHT)" in main_src)

# And the consequence worth pinning: with the bar owning a row there is no
# second "board minus the bar" rect to keep in step, so nothing may reintroduce
# one - that was the version that could draw a corner control in one place and
# click it in another. (It was the MENU button at the time; that has since
# moved into the right panel's header row, and the AI switch is what is up
# there now.)
c.true("no separate chrome rect exists any more", "board_chrome_rect" not in main_src)
c.true("...and chrome_rect() is gone from the module too",
       not hasattr(rp, "chrome_rect"))

# The map fills its column exactly as before: the board rect is what every
# click-to-board translation goes through, and it is the full column now.
c.true("the board-to-screen origin is the board rect",
       "InputManager(board_offset=board_rect_screen.topleft" in main_src)

c.true("the panel no longer prints the round number",
       "ROUND {turn_tracker.battle_round}" not in panel_src
       and "round_bar_rect" not in panel_src)
c.true("...but still prints the phase",
       'f"{turn_tracker.phase} Phase"' in panel_src)

c.finish()
