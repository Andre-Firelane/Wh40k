"""Runtime proof through the REAL main() loop that the round progress bar is
drawn, says what it should, and really cleared the board's top corner.

"Built but never FED" has hit this repo seven times, and a source guard only
shows the call is written down. So this drives selfplay.py's real main() loop
and reports, off the LIVE screen surface:

  * how many frames drew the bar, and how many distinct turns it named;
  * how many pixels of each player's TEAM COLOUR ended up on the track - a
    draw call proves it was rendered, the colour proves it is on the screen;
  * whether the bar OWNS a row rather than covering the map, and whether the
    board and both side panels share a top edge with it.

That last one is the point of --neutralize, and it is the fault that was
reported: the first version drew the bar over the board, which covered the
map's first pixels and left the map's top edge below the panels' ("der balken
ueberdeckt die map" / "die map schliesst jetzt nicht mehr links und rechts mit
den 2 seiten panels ab"). Neutralised, the bar draws exactly as prettily and
the three columns simply stop lining up - which no screenshot of the strip
itself would show.

NOTHING IS STAGED. The bar is drawn on every frame of every game, so this is
one of the rare questions that is measurable passively.

Harness trap this walks into deliberately (documented in CLAUDE.md): importing
selfplay runs nothing, because of its __main__ guard - so it goes through runpy
with run_name="__main__".

Usage:  python verify_round_progress_bar.py [map2] [frames]
        python verify_round_progress_bar.py map2 --neutralize
"""

import runpy
import sys

import pygame

from game.renderer import TOKEN_TEAM_COLORS
from game.ui import round_progress_bar as rp

from game import config

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")
    # THE FAITHFUL PRE-FIX WORLD, in the two moves that together are what the
    # first version did: main() lays the columns out from BAR_HEIGHT, so
    # zeroing that puts them back at the top of the window, and the bar then
    # draws itself at its real size over the BOARD - where it used to live.
    _real_height = rp.BAR_HEIGHT
    rp.BAR_HEIGHT = 0
    rp.bar_rect = lambda window_width: pygame.Rect(
        config.LEFT_PANEL_WIDTH, 0,
        window_width - config.LEFT_PANEL_WIDTH - config.RIGHT_PANEL_WIDTH,
        _real_height)

stats = {
    "frames_drawn": 0,
    "titles_seen": set(),
    "player_1_colour_px": 0,
    "player_2_colour_px": 0,
    "empty_cell_px": 0,
    "badge_drawn_frames": 0,
    "bar_overlaps_the_board": 0,
    "bar_clear_of_the_board": 0,
    "columns_share_the_bars_bottom_edge": 0,
    "columns_out_of_line": 0,
}
#: The three column rects main() built, captured from the widgets it hands them
#: to - the layout lives in main(), which no test runs.
seen = {"board": None, "left": None, "right": None}

_real_draw = rp.draw
_P1 = tuple(TOKEN_TEAM_COLORS["Player 1"][:3])
_P2 = tuple(TOKEN_TEAM_COLORS["Player 2"][:3])
_WANTED = {
    rp._dim(_P1, rp.PLAYED_DIM): "player_1_colour_px",
    _P1: "player_1_colour_px",
    rp._dim(_P2, rp.PLAYED_DIM): "player_2_colour_px",
    _P2: "player_2_colour_px",
    rp.EMPTY_COLOR: "empty_cell_px",
}


def draw(surface, window_width, turn_tracker, player_factions=None):
    rect = _real_draw(surface, window_width, turn_tracker, player_factions)
    board, left, right = seen["board"], seen["left"], seen["right"]
    if board is not None:
        stats["bar_overlaps_the_board" if rect.colliderect(board)
              else "bar_clear_of_the_board"] += 1
        tops = {board.top}
        if left is not None:
            tops.add(left.top)
        if right is not None:
            tops.add(right.top)
        aligned = len(tops) == 1 and tops.pop() == rect.bottom
        stats["columns_share_the_bars_bottom_edge" if aligned
              else "columns_out_of_line"] += 1
    stats["frames_drawn"] += 1
    stats["titles_seen"].add(rp.title_text(turn_tracker))
    if rp.last_badge_rect is not None:
        stats["badge_drawn_frames"] += 1
    # READ IN THE FRAME, not after the loop. The first version of this probe
    # scanned the screen once runpy had returned and reported 0 pixels of every
    # colour: by then main() is gone and the display surface it was drawing to
    # is not readable any more. One scanline per frame rather than the whole
    # track, because 14k get_at() calls per frame across 2500 frames is its own
    # kind of measurement error.
    track = rp.last_track_rect
    if track is not None:
        y = track.y + 3
        for x in range(track.x, track.right):
            key = _WANTED.get(surface.get_at((x, y))[:3])
            if key:
                stats[key] += 1
    return rect


rp.draw = draw

# The three column rects, caught off the widgets main() hands them to. The dice
# panel receives the BOARD rect and the two side panels receive their own, so
# the layout is read from the live frame instead of being recomputed here -
# main() is where it lives, and no test runs main().
from game.ui.dice_panel import DicePanel
from game.ui.action_panel import ActionPanel
from game.ui.game_status_panel import GameStatusPanel

_real_dice = DicePanel.draw
_real_action = ActionPanel.draw
_real_status = GameStatusPanel.draw


def dice_draw(self, surface, dice_manager, *a, **kw):
    if kw.get("bounds_rect") is not None:
        seen["board"] = pygame.Rect(kw["bounds_rect"])
    return _real_dice(self, surface, dice_manager, *a, **kw)


def action_draw(self, surface, rect, *a, **kw):
    seen["left"] = pygame.Rect(rect)
    return _real_action(self, surface, rect, *a, **kw)


def status_draw(self, surface, rect, *a, **kw):
    seen["right"] = pygame.Rect(rect)
    return _real_status(self, surface, rect, *a, **kw)


DicePanel.draw = dice_draw
ActionPanel.draw = action_draw
GameStatusPanel.draw = status_draw

sys.argv = ["selfplay.py"] + sys.argv[1:]
runpy.run_module("selfplay", run_name="__main__")

print()
print("--- round progress bar spy" + (" (NEUTRALIZED: chrome_rect is a no-op)"
                                      if NEUTRALIZE else "") + " ---")
titles = sorted(stats.pop("titles_seen"))
for key, value in stats.items():
    print(f"  {key:34} {value}")
print(f"  {'distinct turns named':34} {len(titles)}")
for title in titles[:6]:
    print(f"      {title}")
if not stats["frames_drawn"]:
    print("  INCONCLUSIVE: the bar was never drawn in this run")
