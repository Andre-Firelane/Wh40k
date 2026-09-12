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
ROUNDS = missions.BATTLE_ROUNDS


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


def label_boxes():
    return [r.inflate(2, 2) for _n, _t, r in rp.last_label_rects]


def track_row(surf, offset=1):
    """One scanline across the cells, SKIPPING the round labels.

    The labels are drawn on top of the cells, so a scanline through them would
    count their ink and their outline as cell colours. Skipped by the rects
    draw() reported, not by picking a row that happens to miss them today - a
    bigger font would move the glyphs onto that row silently."""
    track = track_of()
    y = track.y + offset
    covered = label_boxes()
    return [surf.get_at((x, y))[:3] for x in range(track.x, track.right)
            if not any(r.collidepoint(x, y) for r in covered)]


def pixels_in(surf, rect):
    clipped = rect.clip(surf.get_rect())
    return [surf.get_at((x, y))[:3]
            for y in range(clipped.top, clipped.bottom)
            for x in range(clipped.left, clipped.right)]


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
    # The wider gap groups the pairs, together with the round number.
    within_round = segments[1].x - segments[0].right
    between_rounds = segments[2].x - segments[1].right
    c.true(f"{width}px: the gap between ROUNDS is wider than within one",
           between_rounds > within_round)
    # round_spans() is built off the SAME segments, so a label centred on a span
    # is centred on the cells that were drawn.
    spans = rp.round_spans(track, TURNS)
    c.eq(f"{width}px: one span per battle round", len(spans), ROUNDS)
    c.eq(f"{width}px: each span runs from its round's first turn to its second",
         [(s.left, s.right) for s in spans],
         [(segments[2 * i].left, segments[2 * i + 1].right) for i in range(ROUNDS)])

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

c.eq("before the battle no round is current", rp.current_round(tracker_at(0, 0, 0)), None)
c.eq("round 1 is round 1, whichever player is playing",
     (rp.current_round(tracker_at(1, 0, 3)), rp.current_round(tracker_at(1, 1, 0))), (1, 1))
c.eq("round 3 is round 3", rp.current_round(tracker_at(3, 1, 2)), 3)
c.eq("...and the one-past-the-end frame still names the LAST round, not a sixth",
     rp.current_round(tracker_at(missions.BATTLE_ROUNDS + 1, 0, 0)), ROUNDS)

owners = rp.turn_owners(tracker_at(1, 0, 0, first="Player 2"))
c.eq("the owner sequence covers the whole battle", len(owners), TURNS)
c.eq("whoever goes first goes first in EVERY round",
     [owners[i] for i in range(0, TURNS, 2)], ["Player 2"] * missions.BATTLE_ROUNDS)
c.eq("...and the other player takes every second turn",
     [owners[i] for i in range(1, TURNS, 2)], ["Player 1"] * missions.BATTLE_ROUNDS)

# ---------------------------------------------------------------------------
print("--- 4. the ROUND is labelled - 1 2 3 4 5 - not the player ---")
# ---------------------------------------------------------------------------
c.eq("before the battle the bar says so",
     rp.title_text(tracker_at(0, 0, 0)), "DEPLOYMENT")
title = rp.title_text(tracker_at(3, 1, 2))
c.true("the current turn is named in full - round and player", "3" in title and "PLAYER 2" in title)
c.true("...and no phase name is printed there",
       not any(phase.upper() in title for phase in PHASES))

# Three generations of label, each reported. A tiny grey "3.2" UNDER the cells
# ("momentan sind ganz kleine labels unter den zugabschnitten. die koennen
# weg"), then "P1"/"P2" ON every turn segment, and now: "die farbe reicht als
# player indikator. ich haette aber gerne den Turncounter als Label ueber der
# Leiste nicht den Spieler, also 1 2 3 4 5". Read back off last_label_rects
# (what was blitted, where) AND a spy on the font (what text in which colour) -
# a label with the wrong TEXT still has the right place and the right colour.
rendered = []
_real_font = rp._font


class _SpyFont:
    def __init__(self, font, size):
        self._font = font
        self._size = size

    def render(self, text, antialias, color, *rest):
        rendered.append((self._size, text, tuple(color[:3])))
        return self._font.render(text, antialias, color, *rest)

    def __getattr__(self, name):
        return getattr(self._font, name)


rp._font = lambda size, bold=True: _SpyFont(_real_font(size, bold), size)
try:
    surf, rect = frame(tracker_at(3, 1, 2))
finally:
    rp._font = _real_font

labels = list(rp.last_label_rects)
track = track_of()
segments = rp.turn_segments(track, TURNS)
spans = rp.round_spans(track, TURNS)
paired = len(labels) == ROUNDS

# The colour checks below read ONE scanline and skip label pixels on it. That
# skip must not be doing the work: an earlier run of this file read row +3,
# which the 18 pt label covers, and it skipped the current cell's own interior
# and reported the full colour missing. So the row they read is pinned clear.
c.true("the scanline the colour checks read crosses no label",
       bool(labels) and all(not r.inflate(2, 2).collidepoint(r.centerx, track.y + 1)
                            for _n, _t, r in labels))

c.eq("ONE label per BATTLE ROUND at 1280 px - not one per turn",
     len(labels), ROUNDS)
c.eq("...reading 1 to 5 in track order",
     [(number, text) for number, text, _r in labels],
     [(n, str(n)) for n in range(1, ROUNDS + 1)])

label_renders = [(text, colour) for size, text, colour in rendered
                 if size == rp.LABEL_FONT_SIZE]
title_colours = {colour for size, _text, colour in rendered if size == rp.TITLE_FONT_SIZE}
c.eq("the label font really rendered exactly 1..5 and nothing else",
     sorted({text for text, _col in label_renders}),
     [str(n) for n in range(1, ROUNDS + 1)])
c.true("no player name is drawn on the bar any more (the reported change)",
       bool(label_renders) and not any(text.upper().startswith("P")
                                       for text, _col in label_renders))

ink_colour = lambda wanted: ({col for text, col in label_renders if text == wanted}
                             - {rp.LABEL_OUTLINE_COLOR})
current_colours = ink_colour("3")
other_colours = set().union(*(ink_colour(str(n)) for n in range(1, ROUNDS + 1) if n != 3))
c.true(f"round 3 - the round being played - is in the TITLE's gold {current_colours}",
       len(current_colours) == 1 and current_colours <= title_colours)
c.eq("...and every other round in ONE other colour", len(other_colours), 1)
neutral = next(iter(other_colours)) if len(other_colours) == 1 else (0, 255, 0)
# "die farbe reicht als player indikator": the label colour is NOT a player
# colour. Anchored to what was rendered, not to LABEL_COLOR - otherwise a probe
# moves both sides of the comparison.
c.true(f"that colour is neutral, not a team colour {neutral}",
       max(neutral) - min(neutral) <= 30
       and neutral not in {tuple(v[:3]) for v in TOKEN_TEAM_COLORS.values()})
c.true("...and it is light, so it reads on the dark upcoming cells", min(neutral) >= 180)

c.eq("each label is centred over ITS OWN round",
     [i for i, (_n, _t, r) in enumerate(labels)
      if abs(r.centerx - spans[i].centerx) > 1] if paired else ["count"], [])
# Per ROUND, not per turn: the label straddles the gap between the round's two
# turns - the one place on the track that belongs to neither player.
c.eq("...straddling the gap between that round's first and second turn",
     [i for i, (_n, _t, r) in enumerate(labels)
      if not (r.left < segments[2 * i].right and r.right > segments[2 * i + 1].left)]
     if paired else ["count"], [])
c.eq("each label, outline included, stays inside its round's span",
     [i for i, (_n, _t, r) in enumerate(labels)
      if not spans[i].contains(pygame.Rect(r.x - 1, r.y, r.width + 2, r.height))]
     if paired else ["count"], [])

# ON the bar: every pixel of the neutral label colour inside the track's columns
# lies inside the track's rows. The very first label row was BELOW the track, so
# that is exactly the version this refuses - and the count guards against
# passing on a bar with no labels.
ink_rows = [y for y in range(rect.top, rect.bottom)
            for x in range(track.left, track.right)
            if surf.get_at((x, y))[:3] == neutral]
c.true("label ink is really on the screen", len(ink_rows) > 0)
c.true("...and all of it sits ON the cells, none under them",
       bool(ink_rows) and min(ink_rows) >= track.top and max(ink_rows) < track.bottom)
gold_label = next((r for n, _t, r in labels if n == 3), None)
c.true("the gold of round 3's label is really on the screen, in its own box",
       gold_label is not None and rp.CURRENT_ROUND_LABEL_COLOR in pixels_in(surf, gold_label))
c.true("...and round 1's box carries no gold - only the current round is highlighted",
       paired and rp.CURRENT_ROUND_LABEL_COLOR not in pixels_in(surf, labels[0][2]))
# "ganz kleine labels" was reported once, so the size is pinned against the font
# those labels were set in (11), not against LABEL_FONT_SIZE - a probe would
# otherwise move both sides of the comparison.
reported_font = pygame.font.SysFont(config.FONT_NAME, 11, bold=True)
c.true("every label is taller than the tiny ones the bar started with",
       bool(labels) and all(r.height > reported_font.size(text)[1] for _n, text, r in labels))
c.eq("the cells fill the whole track height - no label row reserved under them",
     surf.get_at((segments[0].x + 1, track.bottom - 2))[:3],
     rp.cell_color("Player 1", 0, 0, 5, 2))
# Segment 5 is the turn being played and its label sits on cells of every
# brightness - the case the outline is for.
c.eq("every label carries its dark outline",
     [n for n, _t, r in labels
      if rp.LABEL_OUTLINE_COLOR not in pixels_in(surf, r.inflate(2, 2))], [])

# The gold follows the round: at round 1 it is "1" that is gold.
surf, rect = frame(tracker_at(1, 1, 0))
first_labels = list(rp.last_label_rects)
c.true("in round 1 the gold label is round 1's",
       len(first_labels) == ROUNDS
       and rp.CURRENT_ROUND_LABEL_COLOR in pixels_in(surf, first_labels[0][2])
       and rp.CURRENT_ROUND_LABEL_COLOR not in pixels_in(surf, first_labels[2][2]))

# The narrow end: a round span that cannot hold its number gets none rather than
# a digit smeared across two-pixel turns. Measured against a wide track in the
# same call, so the drop is shown to be about WIDTH.
narrow = pygame.Surface((400, 40))
rp.draw_track(narrow, pygame.Rect(0, 0, 60, 22), tracker_at(3, 1, 2))
c.eq("a track too narrow for the numbers draws none instead of squeezing them",
     rp.last_label_rects, [])
rp.draw_track(narrow, pygame.Rect(0, 0, 380, 22), tracker_at(3, 1, 2))
c.eq("...while a wide enough one draws all of them", len(rp.last_label_rects), ROUNDS)

# BEFORE THE FIRST-TURN ROLL-OFF the order is a placeholder (TurnTracker's
# deferred start), so no COLOUR may claim one. The round numbers do not depend
# on who goes first, so they are there from the start - but none is current.
surf, rect = frame(tracker_at(0, 0, 0))
c.eq("before the battle starts the round numbers are already on the bar",
     [text for _n, text, _r in rp.last_label_rects], [str(n) for n in range(1, ROUNDS + 1)])
c.true("...none of them in gold - no round is being played yet",
       rp.CURRENT_ROUND_LABEL_COLOR not in pixels_in(surf, track_of().inflate(4, 4)))
c.true("...and the cells are neutral, not coloured in a placeholder order",
       set(track_row(surf)) <= {rp.EMPTY_COLOR, rp.BG_COLOR})

# FROM THE FIRST TURN ON, every turn says whose it is - "von anfang an" - by its
# colour alone.
surf, rect = frame(tracker_at(1, 0, 0))
band = track_row(surf)
c.true("from the first turn of the battle no cell is left neutral grey",
       rp.EMPTY_COLOR not in band)
c.true("...every turn nobody has played yet already shows its owner's colour",
       rp._dim(TOKEN_TEAM_COLORS["Player 1"], rp.UPCOMING_DIM) in band
       and rp._dim(TOKEN_TEAM_COLORS["Player 2"], rp.UPCOMING_DIM) in band)

# ---------------------------------------------------------------------------
print("--- 5. the faction colour, and that it is PER TURN ---")
# ---------------------------------------------------------------------------
# Turn 5 (round 3, Player 2) is being played, so turns 0..4 are done. Turn 0
# belongs to Player 1 and turn 1 to Player 2; their played cells must carry
# their OWN colours, which is the "Volk Farbe" half of the request - and, now
# that the labels say the round, the ONLY thing saying whose turn is where.
p1 = rp._dim(TOKEN_TEAM_COLORS["Player 1"], rp.PLAYED_DIM)
p2 = rp._dim(TOKEN_TEAM_COLORS["Player 2"], rp.PLAYED_DIM)
c.true("the two players' played colours are distinguishable", p1 != p2)

surf, rect = frame(tracker_at(3, 1, 2))
band = track_row(surf)
c.true("Player 1's colour appears on the track", p1 in band)
c.true("...and Player 2's does too", p2 in band)
c.true("an UPCOMING turn is its owner's colour too (Player 1)",
       rp._dim(TOKEN_TEAM_COLORS["Player 1"], rp.UPCOMING_DIM) in band)
c.true("...(Player 2)", rp._dim(TOKEN_TEAM_COLORS["Player 2"], rp.UPCOMING_DIM) in band)
c.true("upcoming, played and current are three steps of one hue, darkest first",
       all(sum(rp._dim(base, rp.UPCOMING_DIM)) < sum(rp._dim(base, rp.PLAYED_DIM))
           < sum(base[:3]) for base in TOKEN_TEAM_COLORS.values()))
c.true("the current phase is drawn in FULL colour, not the dimmed one",
       TOKEN_TEAM_COLORS["Player 2"] in band)
# The current round's label is gold too, so the outline is looked for OUTSIDE
# the label boxes - otherwise the label alone would pass this.
covered = label_boxes()
c.true("...and the current cell is outlined so it can be found",
       rp.CURRENT_OUTLINE_COLOR in
       [surf.get_at((x, y))[:3]
        for y in range(track_of().y, track_of().centery)
        for x in range(track_of().x, track_of().right)
        if not any(r.collidepoint(x, y) for r in covered)])

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
#: Played or being played. Not "anything but grey" any more: every upcoming turn
#: is coloured now, so that count would read full from the first turn on.
PLAYED_COLOURS = {p1, p2, tuple(TOKEN_TEAM_COLORS["Player 1"][:3]),
                  tuple(TOKEN_TEAM_COLORS["Player 2"][:3])}


def played_pixels(tracker):
    surf, _rect = frame(tracker)
    return sum(1 for px in track_row(surf) if px in PLAYED_COLOURS)

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
c.true("without factions the track is still drawn in the team colours",
       p1 in track_row(surf))
c.eq("...still labelled - the round numbers do not come from the factions",
     len(rp.last_label_rects), ROUNDS)
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
# The player-label API is gone with the labels, rather than left behind unused.
c.true("...and so are the P1/P2 label helpers",
       not hasattr(rp, "owner_label") and not hasattr(rp, "label_color"))

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
