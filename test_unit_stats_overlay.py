"""game/ui/unit_stats_overlay.py - the Unit Statistics resume, on PIXELS.

Rendered onto a real Surface with real fonts and read back, rather than
compared against the constants that produced the layout: a screen that agrees
with its own arithmetic can still put the text outside the panel.
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
pygame.init()
pygame.display.set_mode((1280, 720))

import testkit as tk
from testkit import Checks
from game import battle_stats
from game.ui import unit_stats_overlay as uso
from game.ui import button_style
from game.ui.ai_busy_badge import ai_mode_toggle_rect
from game.factions import aeldari, necrons

c = Checks("unit statistics overlay")

WINDOW = (1280, 720)
PLAYERS = [("Player 1", "AELDARI"), ("Player 2", "NECRONS")]


def scene(**per_squad):
    """A ledger with a few units on both sides, plus the live squads."""
    ledger = battle_stats.BattleStats()
    squads = []
    rows = per_squad or {
        "1 Guardian Defenders 1 + Farseer + Warlock Conclave":
            ("Player 1", aeldari.GUARDIAN_DEFENDERS, dict(wounds_dealt=14, points_dealt=137.4,
                                                          prevented=64.0, distance_in=31.5)),
        "1 Dark Reapers 1": ("Player 1", aeldari.DARK_REAPERS,
                             dict(wounds_dealt=9, points_dealt=96.0, distance_in=8.0)),
        "1 Windriders 1": ("Player 1", aeldari.WINDRIDERS,
                           dict(wounds_dealt=4, points_dealt=41.2, prevented=22.0,
                                distance_in=48.5)),
        "2 Necron Warriors 1": ("Player 2", necrons.NECRON_WARRIORS,
                                dict(wounds_dealt=6, prevented=140.0, distance_in=15.0)),
    }
    for name, (owner, sheet, values) in rows.items():
        squad = tk.build(sheet, owner, name=name)
        squads.append(squad)
        record = ledger._record_for(squad)
        for key, value in values.items():
            setattr(record, key, value)
    return ledger, squads


def opened(size=WINDOW, player=None):
    ledger, squads = scene()
    overlay = uso.UnitStatsOverlay()
    overlay.show(ledger, PLAYERS, squads)
    if player:
        overlay.player = player
    surface = pygame.Surface(size)
    surface.fill((0, 0, 0))
    overlay.draw(surface)
    return overlay, surface


def colour_count(surface, colour, rect=None):
    area = rect or surface.get_rect()
    return sum(1 for x in range(area.x, area.right, 2)
               for y in range(area.y, area.bottom, 2)
               if surface.get_at((x, y))[:3] == colour)


def ink_outside(surface, panel, colours):
    """Pixels of `colours` that landed OUTSIDE the panel - the check that a
    layout agreeing with itself cannot pass vacuously."""
    total = 0
    for x in range(0, surface.get_width(), 2):
        for y in range(0, surface.get_height(), 2):
            if panel.collidepoint(x, y):
                continue
            if surface.get_at((x, y))[:3] in colours:
                total += 1
    return total


# ============================================ 0. liveness: it really draws rows
print("\n=== 0. liveness ===")

overlay, surface = opened()
c.true("the overlay reports the panel it drew", overlay.last_rect is not None)
c.true("...and the panel is inside the window",
       surface.get_rect().contains(overlay.last_rect))
lead = colour_count(surface, uso.LEAD_COLOR, overlay.last_rect)
body = colour_count(surface, uso.TEXT_COLOR, overlay.last_rect)
c.true("a first-place row is drawn in the lead colour", lead > 0)
c.true("...and the runners-up in the body colour", body > 0)
c.true("section headings are drawn",
       colour_count(surface, uso.SECTION_COLOR, overlay.last_rect) > 0)
c.true("the title is drawn", colour_count(surface, uso.TITLE_COLOR, overlay.last_rect) > 0)

# Without this the three checks above would pass on any screen that draws
# SOMETHING - an empty ledger must look different.
empty = uso.UnitStatsOverlay()
empty_ledger, squads = battle_stats.BattleStats(), scene()[1]
empty.show(empty_ledger, PLAYERS, squads)
empty_surface = pygame.Surface(WINDOW)
empty_surface.fill((0, 0, 0))
empty.draw(empty_surface)
c.eq("an empty ledger draws NO rows",
     colour_count(empty_surface, uso.LEAD_COLOR, empty.last_rect), 0)
# Scanned over the BODY, not the whole panel: the footer hint is drawn in the
# same dim colour, so a panel-wide count says "it explains itself" even when
# nothing was written into the tables at all. An A/B probe that deleted the
# empty-state text entirely passed the panel-wide version.
_body = pygame.Rect(empty.last_rect.x, empty.last_rect.y + uso.HEADER_HEIGHT,
                    empty.last_rect.width,
                    empty.last_rect.height - uso.HEADER_HEIGHT - uso.FOOTER_HEIGHT)
c.true("...and says so instead of showing a bare frame",
       colour_count(empty_surface, uso.DIM_TEXT_COLOR, _body) > 0)
c.true("...which is really the tables talking, not the footer hint",
       colour_count(empty_surface, uso.DIM_TEXT_COLOR, _body)
       < colour_count(empty_surface, uso.DIM_TEXT_COLOR, empty.last_rect))
c.true("...while still drawing its headings",
       colour_count(empty_surface, uso.SECTION_COLOR, empty.last_rect) > 0)


# =============================================== 1. the button beside the switch
print("\n=== 1. the STATS button sits beside the AI switch ===")

font = pygame.font.SysFont(None, 19, bold=True)
for width, height in ((1280, 720), (1366, 768), (1600, 900), (1920, 1080)):
    board = pygame.Rect(220, 28, width - 440, height - 56)
    ai_rect = ai_mode_toggle_rect(board, font)
    stats_rect = uso.button_rect(board, font, ai_rect)
    label = "%dx%d" % (width, height)
    c.true("%s: the button is to the LEFT of the switch" % label,
           stats_rect.right < ai_rect.left)
    c.eq("%s: ...on the same row" % label, stats_rect.y, ai_rect.y)
    c.eq("%s: ...at the same height" % label, stats_rect.height, ai_rect.height)
    c.true("%s: ...and does not overlap it" % label,
           not stats_rect.colliderect(ai_rect))
    c.true("%s: ...and stays on the board" % label, board.contains(stats_rect))

# The switch must not MOVE to make room - it was deliberately given the corner
# to itself, and test_game_menu.py pins the absence of avoid_rects in main.py
# in the negative for the same reason.
board = pygame.Rect(220, 28, 1160, 746)
before = ai_mode_toggle_rect(board, font)
uso.button_rect(board, font, before)
c.eq("asking for the button does not move the AI switch",
     ai_mode_toggle_rect(board, font), before)

# ...and it really draws where it says.
surface = pygame.Surface(WINDOW)
surface.fill((0, 0, 0))
ai_rect = ai_mode_toggle_rect(pygame.Rect(220, 28, 840, 620), font)
drawn = uso.draw_button(surface, pygame.Rect(220, 28, 840, 620), font, ai_rect)
c.eq("draw_button reports the rect it drew at",
     tuple(drawn), tuple(uso.button_rect(pygame.Rect(220, 28, 840, 620), font, ai_rect)))
c.true("...and really put ink there",
       colour_count(surface, button_style.TEXT_NORMAL, drawn) > 0)
c.eq("no button without a switch to sit beside",
     uso.button_rect(board, font, None), None)


# ==================================================== 2. nothing escapes the panel
print("\n=== 2. the panel contains its own text ===")

for size in ((1280, 720), (1920, 1080)):
    overlay, surface = opened(size)
    escaped = ink_outside(surface, overlay.last_rect,
                          {uso.TEXT_COLOR, uso.LEAD_COLOR, uso.SECTION_COLOR,
                           uso.TITLE_COLOR, uso.HEADER_COLOR})
    c.eq("%dx%d: no text is drawn outside the panel" % size, escaped, 0)
    c.true("%dx%d: ...and the panel does not fill the window" % size,
           overlay.last_rect.width < size[0] and overlay.last_rect.height < size[1])

# The clip has to be handed back, or every later draw in the frame is confined
# to this panel's body.
overlay, _ = opened()
surface = pygame.Surface(WINDOW)
marker = pygame.Rect(3, 3, 4, 4)
surface.set_clip(marker)
overlay.draw(surface)
c.eq("the surface clip is restored", surface.get_clip(), marker)


# ================================================ 3. prediction vs what was drawn
print("\n=== 3. the height prediction matches the drawing ===")

overlay, surface = opened((1920, 1080))
rect = overlay.last_rect
body_width = (rect.width - 2 * uso.PADDING - button_style.SCROLLBAR_WIDTH - 6)
predicted = overlay._content_height(body_width)
body_top = rect.y + uso.HEADER_HEIGHT + 6
drawn_height = overlay._last_content_bottom - body_top
c.true("the predicted content height matches what was laid down "
       "(%d vs %d)" % (predicted, drawn_height),
       abs(predicted - drawn_height) <= 2)


# ============================================================ 4. switching army
print("\n=== 4. the badges switch army ===")

overlay, surface = opened()
c.eq("it opens on the first player", overlay.player, "Player 1")
c.eq("both badges are recorded for the click handler",
     sorted(overlay.last_badge_rects), ["Player 1", "Player 2"])
c.true("the badges are inside the panel header",
       all(overlay.last_rect.contains(r) for r in overlay.last_badge_rects.values()))

p1_ink = colour_count(surface, uso.TEXT_COLOR, overlay.last_rect) \
    + colour_count(surface, uso.LEAD_COLOR, overlay.last_rect)

badge = overlay.last_badge_rects["Player 2"]
overlay.handle_event(pygame.event.Event(
    pygame.MOUSEBUTTONDOWN, button=1, pos=badge.center))
c.eq("clicking the other badge switches army", overlay.player, "Player 2")
c.true("...and does NOT close the screen", overlay.is_pending)

surface.fill((0, 0, 0))
overlay.draw(surface)
p2_ink = colour_count(surface, uso.TEXT_COLOR, overlay.last_rect) \
    + colour_count(surface, uso.LEAD_COLOR, overlay.last_rect)
c.true("...and the tables really show a different army now", p1_ink != p2_ink)

# Clicking the badge that is already showing must not close it either.
overlay.handle_event(pygame.event.Event(
    pygame.MOUSEBUTTONDOWN, button=1, pos=overlay.last_badge_rects["Player 2"].center))
c.true("clicking the badge already shown is a no-op, not a dismiss",
       overlay.is_pending and overlay.player == "Player 2")


# ================================================= 5. scrolling and dismissing
print("\n=== 5. input ===")

overlay, surface = opened((1280, 720))
c.true("at 1280x720 there is something to scroll", overlay._scroll_max > 0)

# THE REPORTED BUG SHAPE: pygame emits a MOUSEBUTTONDOWN with button 4/5
# alongside every MOUSEWHEEL. A test that sends a BARE wheel event cannot see
# it - game/ui/army_rules_overlay.py carries the report that taught this.
overlay.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-1, x=0))
overlay.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=5, pos=(640, 360)))
c.true("one REAL wheel notch does not close the screen", overlay.is_pending)
c.true("...and it actually scrolled", overlay.scroll > 0)

overlay.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_HOME))
c.eq("Home returns to the top", overlay.scroll, 0)
overlay.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_END))
c.eq("End goes to the bottom", overlay.scroll, overlay._scroll_max)
overlay.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEUP))
c.true("PageUp scrolls back", overlay.scroll < overlay._scroll_max)

overlay.handle_event(pygame.event.Event(
    pygame.MOUSEBUTTONDOWN, button=1, pos=(overlay.last_rect.centerx,
                                           overlay.last_rect.bottom - 40)))
c.eq("a plain left click closes it", overlay.is_pending, False)

overlay, _ = opened()
overlay.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
c.eq("ESC closes it", overlay.is_pending, False)
c.eq("...and it forgets its scroll position", overlay.scroll, 0)

# It draws nothing at all while closed, so nothing of it can survive a dismiss.
closed_surface = pygame.Surface(WINDOW)
closed_surface.fill((7, 7, 7))
overlay.draw(closed_surface)
c.eq("a closed overlay draws nothing", colour_count(closed_surface, uso.TITLE_COLOR), 0)

# An empty player list must not open a screen with no army on it.
c.eq("it refuses to open with no players",
     uso.UnitStatsOverlay().show(battle_stats.BattleStats(), [], []), False)


# =============================================================== 6. main.py wiring
print("\n=== 6. wiring ===")

MAIN = open("main.py", encoding="utf-8").read()


def before(first, second):
    """Index order, with find() so a missing needle reports a failed check
    rather than crashing the suite."""
    a, b = MAIN.find(first), MAIN.find(second)
    return 0 <= a < b if (a >= 0 and b >= 0) else False


c.true("main.py builds the ledger", "battle_stats = BattleStats()" in MAIN)
c.true("...and publishes it so the recording seams can reach it",
       "battle_stats_module.CURRENT = battle_stats" in MAIN)
c.true("...and clears it when the battle ends, so a second main() starts fresh",
       "battle_stats_module.CURRENT = None" in MAIN)
c.true("the ledger is built BEFORE the controllers that report into it",
       before("battle_stats = BattleStats()", "shooting_controller = ShootingController"))

c.true("main.py builds the overlay", "unit_stats_overlay_view = UnitStatsOverlay()" in MAIN)
# The call EXPRESSION, never a name count: a mention in a docstring has kept a
# guard green after the call site was deleted (Fehlerklasse 24).
c.true("the button is drawn every frame",
       "stats_button_rect = unit_stats_overlay.draw_button(" in MAIN)
c.true("the overlay is drawn every frame", "unit_stats_overlay_view.draw(screen)" in MAIN)
c.true("...after the army-rules reader",
       before("army_rules_overlay.draw(screen)", "unit_stats_overlay_view.draw(screen)"))

c.true("the button's click is handled BEFORE the state-gated chain",
       before("stats_button_rect.collidepoint(event.pos)", "if event.type == pygame.QUIT:"))
c.true("...and opens the overlay with the ledger and both armies",
       "unit_stats_overlay_view.show(\n                    battle_stats, _stats_players(), state.all_squads())" in MAIN)
c.true("the overlay owns every event while it is up",
       "unit_stats_overlay_view.handle_event(event)\n                continue" in MAIN)
c.true("...and that branch also sits before the chain",
       before("unit_stats_overlay_view.handle_event(event)", "if event.type == pygame.QUIT:"))

c.true("the hover datacard steps aside for it",
       "or unit_stats_overlay_view.is_pending" in MAIN)
c.true("the AI switch is not clickable underneath it",
       MAIN.count("and not unit_stats_overlay_view.is_pending") >= 3)

# It is NOT a click-away notice: it has its own handle_event, so it must stay
# out of _front_notice()'s ordering, which is the ordering of notices with a
# .dismiss(). test_one_modal_at_a_time.py pins that set.
front = MAIN[MAIN.find("def _front_notice():"):]
front = front[:front.find("def advance_turn_phase():")]
c.eq("it is not in _front_notice()'s notice set",
     "unit_stats_overlay_view" in front, False)

c.true("the resume is saved with the scene",
     "stats=battle_stats" in MAIN)
c.true("...and restored after begin_battle(), like the mission state",
       before("begin_battle(", "scene_io.restore_stats(loaded, battle_stats)"))

c.finish()
