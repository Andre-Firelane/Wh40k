"""Tests for the game menu, its two hosts, and the wiring that reaches them.

User: "momentan startet das spiel direkt mit der map auswahl und endet mit ESC.
baue ein spieletypisches game menu. dort gibt es momentan nur 3 optionen start
new game, resume game und quit game. im spiel oeffnet ein druck auf ESC das
menue. ausserdem muss noch irgendwo ein kleiner menu knopf sein. vielleicht
links oben neben dem rechten panel."

  1. the module      - the three actions, and what each host offers.
  2. layout          - one set of rects, read by drawing AND by hit-testing,
                       at both ends of the window sizes this game is run at.
  3. input           - ESC means a different thing per host; a disabled entry
                       swallows its own click.
  4. scene_io        - newest()/summary()/map_key_in(), the Resume entry's
                       eligibility gate.
  5. the MENU button - now beside the "Game Status" heading in the right
                       panel: measured on PIXELS against the header bar it
                       shares a row with, and off the board entirely, which
                       leaves the AI switch alone in the board's corner.
  6. the WIRING in main.py - the half no behaviour test can see: that the menu
                       is asked before the map screen, that ESC reaches it, that
                       its branch sits BEFORE the state-gated chain, and that
                       exactly one function closes the window.

Run: python test_game_menu.py
"""

import io
import os
import re

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1600, 900))

from game import config, scene_io  # noqa: E402
from game.dice import DiceManager  # noqa: E402
from game.turn import TurnTracker  # noqa: E402
from game.ui import button_style, dice_panel as dp, round_progress_bar as rpb  # noqa: E402
from game.ui.ai_busy_badge import ai_mode_toggle_rect  # noqa: E402
from game.ui.dice_panel import DicePanel  # noqa: E402
from game.ui.game_menu import GameMenu, NEW_GAME, QUIT, RESUME, SAVE  # noqa: E402
from game.ui.game_status_panel import GameStatusPanel  # noqa: E402
from testkit import Checks  # noqa: E402

c = Checks("game menu")
SCREEN = pygame.Rect(0, 0, 1600, 900)


def _read(path):
    return io.open(path, encoding="utf-8").read()


def _click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1})


def _key(key):
    return pygame.event.Event(pygame.KEYDOWN, {"key": key})


def _board(width, height):
    return pygame.Rect(config.LEFT_PANEL_WIDTH, 0,
                       width - config.LEFT_PANEL_WIDTH - config.RIGHT_PANEL_WIDTH,
                       height - config.RESERVES_PANEL_HEIGHT)


# --------------------------------------------------------------------------
# 1. the module
# --------------------------------------------------------------------------
print("\n=== 1. what each host offers ===")

c.eq("the four actions are distinct", len({NEW_GAME, RESUME, SAVE, QUIT}), 4)

startup = [a for a, _l, _e in GameMenu().entries()]
in_game = [a for a, _l, _e in GameMenu(in_game=True).entries()]
c.eq("the startup menu offers the three the user asked for, in that order",
     startup, [NEW_GAME, RESUME, QUIT])
c.eq("a battle also offers Save, and Resume comes first",
     in_game, [RESUME, SAVE, NEW_GAME, QUIT])
# Save is meaningless with no battle to save, and Resume-in-a-battle is the
# way back to the board rather than a file - the two hosts differ in WHAT is
# on offer, and nowhere else.
c.true("Save is offered only in a battle", SAVE not in startup)

# Resume's eligibility is the whole reason the startup host takes a path.
c.true("with no save, Resume is disabled",
       [e for a, _l, e in GameMenu().entries() if a == RESUME] == [False])
c.true("...and with one, it is enabled",
       [e for a, _l, e in GameMenu(save_path="x", save_note="n").entries()
        if a == RESUME] == [True])
# A DISABLED entry stays on screen. Dropping it would silently change the
# menu's shape between the two hosts.
c.eq("a disabled Resume is still listed", len(GameMenu().entries()), 3)
# The captions under the rows are GONE (user: "Die unterschriften unter den
# buttons koennen weg"), so a row is (action, label, enabled) and nothing else.
# Named consequence, pinned here rather than left to be rediscovered: a greyed
# Resume no longer prints WHY, and an enabled one no longer names the save.
c.true("a row carries no caption any more",
       all(len(row) == 3 for row in GameMenu().entries()))
c.true("...for either host",
       all(len(row) == 3 for row in GameMenu(in_game=True).entries()))
c.true("nothing in the menu still renders one",
       "NOTE_COLOR" not in _read("game/ui/game_menu.py"))

# Accents describe what a press COSTS - the meaning game/ui/button_style.py
# already carries. Start New Game is free at startup and costs the battle in
# one, which is the only accent that differs between the hosts.
c.eq("Resume is the green carry-on", GameMenu(in_game=True)._accent(RESUME), "confirm")
c.eq("Quit is red", GameMenu()._accent(QUIT), "danger")
c.eq("New Game is free at startup", GameMenu()._accent(NEW_GAME), None)
c.eq("...and costs the battle in one", GameMenu(in_game=True)._accent(NEW_GAME), "danger")
# The two reserved accents belong to rules that pin their own hues.
c.true("no entry borrows the Stratagem or Battle Focus accents",
       not any(GameMenu(in_game=g)._accent(a) in ("stratagem", "battle_focus")
               for g in (False, True) for a, _l, _e in GameMenu(in_game=g).entries()))


# --------------------------------------------------------------------------
# 2. layout
# --------------------------------------------------------------------------
print("\n=== 2. layout ===")

for width, height in ((1280, 720), (1920, 1080)):
    rect = pygame.Rect(0, 0, width, height)
    for host in (False, True):
        menu = GameMenu(in_game=host, save_path="x", save_note="n")
        rects = menu.layout(rect)
        c.eq(f"{width}x{height} in_game={host}: one rect per entry",
             len(rects), len(menu.entries()))
        panel = menu.panel_rect(rect)
        c.true(f"{width}x{height} in_game={host}: the panel is on screen",
               rect.contains(panel))
        for _a, r, _e in rects:
            c.true(f"{width}x{height} in_game={host}: entry inside the panel",
                   panel.contains(r))
        pairs = [(rects[i][1], rects[i + 1][1]) for i in range(len(rects) - 1)]
        c.true(f"{width}x{height} in_game={host}: entries do not overlap",
               all(not a.colliderect(b) for a, b in pairs))
        c.true(f"{width}x{height} in_game={host}: entries are stacked in order",
               all(a.bottom <= b.y for a, b in pairs))

# DRAWING and HIT-TESTING must agree, which is the whole reason layout() is a
# function both call rather than two similar blocks - see tile_screen's
# header_bar() for the lesson this repeats.
menu = GameMenu(save_path="x", save_note="n")
surface = pygame.Surface((1600, 900))
menu.draw(surface, (0, 0))
drawn = [(a, tuple(r)) for a, r, _e in menu._rects]
menu.layout(SCREEN)
c.eq("drawing and hit-testing use the same rects",
     drawn, [(a, tuple(r)) for a, r, _e in menu._rects])

# Both hosts paint something, and the in-game one dims what is behind it.
board_paint = pygame.Surface((1600, 900))
board_paint.fill((200, 200, 200))
before = board_paint.get_at((30, 800))[:3]
GameMenu(in_game=True).draw(board_paint, (0, 0))
after = board_paint.get_at((30, 800))[:3]
c.true("the in-game menu dims the frame behind it", sum(after) < sum(before))
fresh = pygame.Surface((1600, 900))
fresh.fill((200, 200, 200))
GameMenu().draw(fresh, (0, 0))
c.true("the startup menu replaces the screen instead", fresh.get_at((30, 800))[:3] != (200, 200, 200))


# --------------------------------------------------------------------------
# 3. input
# --------------------------------------------------------------------------
print("\n=== 3. input ===")

# ESC is the one key whose MEANING depends on the host: in a battle it is the
# way back (the same key that opened the menu), at startup there is no battle
# to go back to, so it answers the entry that leaves.
m = GameMenu()
m.handle_event(_key(pygame.K_ESCAPE), SCREEN)
c.eq("ESC at startup answers QUIT", m.action, QUIT)
m = GameMenu(in_game=True)
m.handle_event(_key(pygame.K_ESCAPE), SCREEN)
c.eq("ESC in a battle answers RESUME", m.action, RESUME)

# run() never returns None, unlike the map and army pickers: this screen HAS a
# Quit entry, so abandoning it is an answer rather than a fourth state.
c.eq("cancelled is never set", GameMenu().cancelled, False)

m = GameMenu()
rects = dict((a, r) for a, r, _e in m.layout(SCREEN))
m.handle_event(_click(rects[RESUME].center), SCREEN)
c.eq("a click on a disabled entry does nothing", m.action, None)
c.true("...and is swallowed rather than falling through",
       m.entry_at(rects[RESUME].center) is None)
m.handle_event(_click(rects[NEW_GAME].center), SCREEN)
c.eq("a click on a live entry answers it", m.action, NEW_GAME)
c.true("...and the screen is then done", m.done)

# The window's own close box means the same thing as Quit.
m = GameMenu(in_game=True)
m.handle_event(pygame.event.Event(pygame.QUIT), SCREEN)
c.eq("closing the window answers QUIT", m.action, QUIT)

# Keyboard: Return activates whatever the arrows are on, and the arrows skip
# entries that cannot be pressed.
m = GameMenu()
m.layout(SCREEN)
m.handle_event(_key(pygame.K_DOWN), SCREEN)
m.handle_event(_key(pygame.K_RETURN), SCREEN)
c.true("the arrows never land on a disabled entry", m.action != RESUME)

# take_action() hands the answer over ONCE - main() polls it every frame, and
# a press served twice would end the battle twice.
m = GameMenu(in_game=True)
m.show()
m.handle_event(_click(dict((a, r) for a, r, _e in m.layout(SCREEN))[QUIT].center), SCREEN)
c.eq("take_action returns the answer", m.take_action(), QUIT)
c.eq("...and only once", m.take_action(), None)

m = GameMenu(in_game=True)
c.eq("a fresh in-game menu is closed", m.is_pending, False)
m.show()
c.eq("show() opens it", m.is_pending, True)
m.dismiss()
c.eq("dismiss() closes it", m.is_pending, False)


# --------------------------------------------------------------------------
# 4. scene_io - what Resume is offered from
# --------------------------------------------------------------------------
print("\n=== 4. finding a save ===")

import tempfile  # noqa: E402

with tempfile.TemporaryDirectory() as tmp:
    c.eq("an empty folder has no newest save", scene_io.newest(tmp), None)
    c.eq("a missing folder is not an error either", scene_io.newest(os.path.join(tmp, "nope")), None)

    older = os.path.join(tmp, "scene_a.json")
    newer = os.path.join(tmp, "autosave.json")
    scene_io.write({"format": scene_io.FORMAT_VERSION, "map": "map1", "squads": [],
                    "turn": {"battle_round": 2, "turn_owner": "Player 1"}}, older)
    scene_io.write({"format": scene_io.FORMAT_VERSION, "map": "map3", "squads": [],
                    "turn": {"battle_round": 4, "turn_owner": "Player 2"}}, newer)
    os.utime(older, (1_600_000_000, 1_600_000_000))
    os.utime(newer, (1_700_000_000, 1_700_000_000))
    c.eq("the newest wins, autosave included", scene_io.newest(tmp), newer)
    # The autosave is not named scene_*, so picking by the filename's stamp
    # would never find it - which is why this goes by mtime.
    c.eq("...even though its name carries no timestamp", os.path.basename(newer), "autosave.json")
    c.eq("map_key_in reads the board back", scene_io.map_key_in(newer), "map3")
    note = scene_io.summary(newer)
    c.true("summary names the map", "map3" in note)
    c.true("...the round", "4" in note)
    c.true("...and whose turn it was", "Player 2" in note)
    # No typographic glyphs: pygame's default SysFont draws them as tofu, the
    # same reason game/rules_text.py folds them.
    c.true("summary is plain ASCII", all(ord(ch) < 128 for ch in note))

    broken = os.path.join(tmp, "broken.json")
    io.open(broken, "w", encoding="utf-8").write("{ not json")
    c.eq("a corrupt snapshot summarises as None", scene_io.summary(broken), None)
    # ...and newest() steps over it to the real save behind. A .json in this
    # folder is not necessarily a snapshot, and returning an unreadable one
    # would grey out Resume while a perfectly good save sat one file down.
    os.utime(broken, (1_800_000_000, 1_800_000_000))
    c.eq("newest() skips a file it cannot read", scene_io.newest(tmp), newer)
    future = os.path.join(tmp, "future.json")
    scene_io.write({"format": 99, "map": "map1", "squads": []}, future)
    c.eq("so does one from a newer format", scene_io.summary(future), None)
    # That None is the eligibility gate: the menu greys Resume rather than
    # offering a press that would then fail (CLAUDE.md error class 5).
    c.true("a file that cannot be summarised leaves Resume disabled",
           [e for a, _l, e in GameMenu(save_path=broken,
                                           save_note=scene_io.summary(broken)).entries()
            if a == RESUME] == [False])


# --------------------------------------------------------------------------
# 5. the MENU button, and the corner it left behind
# --------------------------------------------------------------------------
print("\n=== 5. the MENU button ===")

# User: "ausserdem haette ich den 'Menu' Knopf gerne oben rechts in der rechten
# spalte neben der Game Status ueberschrift" - it used to sit in the board's
# top-right corner. The board rect is still built here, because the third line
# of the same report ("dann liegt nur noch der AI Schalter ueber der Map") is
# an assertion ABOUT the board and is checked below.
menu = GameMenu(in_game=True)


def _panel(width, height):
    return pygame.Rect(width - config.RIGHT_PANEL_WIDTH, rpb.BAR_HEIGHT,
                       config.RIGHT_PANEL_WIDTH, height - rpb.BAR_HEIGHT)


_status_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
_bar_top = _panel(1280, 720).y + button_style.HEADER_MARGIN

for width, height in ((1280, 720), (1366, 768), (1600, 900), (1920, 1080)):
    panel = _panel(width, height)
    board = _board(width, height)
    btn = menu.button_rect(panel)
    bar_top = panel.y + button_style.HEADER_MARGIN
    c.true(f"{width}x{height}: the button is inside the RIGHT PANEL", panel.contains(btn))
    c.true(f"{width}x{height}: ...at the top right of it",
           btn.centerx > panel.centerx
           and btn.top < bar_top + button_style.HEADER_BAR_HEIGHT)
    c.eq(f"{width}x{height}: ...hard against the panel's right edge",
         panel.right - btn.right, button_style.HEADER_MARGIN)
    # The half of the report that is about the BOARD: nothing of the menu is
    # over the map any more.
    c.true(f"{width}x{height}: ...and off the board entirely", not btn.colliderect(board))
    # It shares the header ROW - so it must sit within the bar's own height,
    # not above or below it. Centred, since the bar is 34px and the button 26.
    c.true(f"{width}x{height}: ...vertically inside the header bar's own band",
           btn.top >= bar_top and btn.bottom <= bar_top + button_style.HEADER_BAR_HEIGHT)

# THE SHARED ROW, MEASURED ON PIXELS through the REAL panel rather than
# recomputed from the constants that produced it. The bar and the button divide
# one row between them, and the failure this pins is the one that looks fine
# until a title happens to grow: a button laid OVER a full-width bar.
panel = _panel(1280, 720)
surface = pygame.Surface((1280, 720))
surface.fill((0, 0, 0))
GameStatusPanel().draw(surface, panel, TurnTracker(first_player="Player 1"))
btn = menu.draw_button(surface, panel, (-99, -99))
row_y = _bar_top + button_style.HEADER_BAR_HEIGHT // 2
bar_px = [x for x in range(panel.x, panel.right)
          if surface.get_at((x, row_y))[:3] == button_style.HEADER_BG_COLOR[:3]]
c.true("the header bar is actually drawn", len(bar_px) > 50)
c.true("the bar stops before the button starts", max(bar_px) < btn.x)
c.true("no bar pixel lies under the button",
       not any(surface.get_at((x, y))[:3] == button_style.HEADER_BG_COLOR[:3]
               for x in range(btn.x, btn.right)
               for y in range(_bar_top, _bar_top + button_style.HEADER_BAR_HEIGHT)))
# ...and the title still FITS in what is left. Measured against the rendered
# string, not against a remembered number: "enough room was reserved" and "the
# title still fits" are two different claims and only the second one matters.
title_px = _status_font.size("Game Status")[0]
room = (panel.width - 2 * button_style.HEADER_MARGIN
        - button_style.header_button_reserve() - 2 * button_style.HEADER_TEXT_MARGIN)
c.true(f"the title still fits beside it ({title_px}px in {room}px)", title_px <= room)
# The counter-check, without which the two lines above would pass on a header
# that reserved the whole panel: reserving nothing must still draw a FULL-width
# bar, i.e. the shortening really is the parameter's doing.
plain = pygame.Surface((1280, 720))
plain.fill((0, 0, 0))
button_style.draw_panel_header(plain, panel, "Game Status", _status_font)
plain_px = [x for x in range(panel.x, panel.right)
            if plain.get_at((x, row_y))[:3] == button_style.HEADER_BG_COLOR[:3]]
# Measured as the bar's EXTENT, not as a pixel count: the title's glyphs sit
# on this scanline and are not the bar colour, so counting matching pixels
# answers "how much ink is in the way" instead of "how wide is the bar".
c.eq("a header that reserves nothing is unchanged",
     max(plain_px) - min(plain_px) + 1, panel.width - 2 * button_style.HEADER_MARGIN)
c.eq("...and reserving the button shortens it by exactly that much",
     (max(plain_px) - min(plain_px)) - (max(bar_px) - min(bar_px)),
     button_style.header_button_reserve())

# ONE definition of where the button sits, so the panel that SHORTENS the bar
# and the class that PLACES the button cannot disagree - GameMenu delegates
# rather than doing half the arithmetic itself.
c.eq("GameMenu delegates to button_style",
     menu.button_rect(panel), button_style.header_button_rect(panel))
_menu_src = _read("game/ui/game_menu.py")
c.true("...and keeps no board-corner geometry of its own",
       "BUTTON_MARGIN = " not in _menu_src
       and "BUTTON_WIDTH = " not in _menu_src
       and "BUTTON_HEIGHT = " not in _menu_src)

# --------------------------------------------------------------------------
# THE AI SWITCH now has the board's corner to itself - the user's own summing
# up of the move ("dann liegt nur noch der AI Schalter ueber der Map"). It is
# handed NO avoid_rects any more, so it stops moving.
# --------------------------------------------------------------------------
_toggle_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
for width, height in ((1280, 720), (1366, 768), (1600, 900), (1920, 1080)):
    board = _board(width, height)
    tog = ai_mode_toggle_rect(board, _toggle_font)
    c.true(f"{width}x{height}: the switch sits in the board's top-right corner",
           tog.top == board.y + 12 and tog.right == board.right - 12)
    c.true(f"{width}x{height}: ...clear of the MENU button, which is not here any more",
           not tog.colliderect(menu.button_rect(_panel(width, height))))

# THE DICE, measured rather than assumed - this is what the old
# "btn.x > dice_right" line was protecting, and the switch is 92px wide where
# the button was 74. The dice panel is anchored top-centre in this same board
# rect and WIDENS past MAX_PANEL_WIDTH for big salvoes, so its backdrop's
# padding does reach the corner at the narrow window sizes; what must never
# happen is a DIE under the switch, and that is the thing pinned.
#
# The panel is drawn TWICE with its animation back-dated in between: the
# slide-in parks the whole panel above the board's top edge, and measuring it
# mid-slide reports nonsense (a backdrop at top=-207 on the first frame).
dice_seen = 0
for width, height in ((1280, 720), (1366, 768), (1600, 900), (1920, 1080)):
    screen = pygame.display.set_mode((width, height))
    board = _board(width, height)
    tog = ai_mode_toggle_rect(board, _toggle_font)
    for count in (1, 10, 40, 60, 100):
        dm = DiceManager()
        dm.roll(count, 6, label="hit roll", success_threshold=4)
        dice = DicePanel()
        dice.draw(screen, dm, board)
        dice._anim_start -= 1.0
        dice.draw(screen, dm, board)
        c.true(f"{width}x{height}/{count}: the panel is measured at rest",
               dice.last_backdrop_rect.top >= board.y)
        under = [r for _i, r in dice._die_rects if r.colliderect(tog)]
        dice_seen += len(dice._die_rects)
        c.eq(f"{width}x{height}/{count}: no die is under the AI switch", len(under), 0)
pygame.display.set_mode((1600, 900))
c.true(f"...and that swept real dice ({dice_seen} of them)", dice_seen > 500)

# The AVOID mechanism stays and is exercised at a blocker of the test's own -
# nothing in main.py hands it one today, and a mechanism that ships inert is
# how the next control to share this corner finds it broken (the
# WALL_CROSSING_COST_IN precedent).
board = _board(1920, 1080)
plain_tog = ai_mode_toggle_rect(board, _toggle_font)
blocker = pygame.Rect(plain_tog.x, plain_tog.y, plain_tog.width, plain_tog.height)
moved = ai_mode_toggle_rect(board, _toggle_font, avoid_rects=(blocker,))
c.true("the switch still steps clear of a blocker", moved.topleft != plain_tog.topleft)
c.eq("...straight down, keeping its column", moved.x, plain_tog.x)
c.true("...and below it", moved.top >= blocker.bottom)
c.true("...still inside the board", board.contains(moved))
c.true("the two cannot share a pixel", not moved.colliderect(blocker))
c.true("the stepped switch is still in the board's top-right quadrant",
       moved.centerx > board.centerx and moved.centery < board.centery)
c.eq("avoid_rects defaults to no movement",
     ai_mode_toggle_rect(board, _toggle_font), plain_tog)
c.eq("a None blocker is ignored",
     ai_mode_toggle_rect(board, _toggle_font, avoid_rects=(None,)), plain_tog)


# --------------------------------------------------------------------------
# 6. the wiring in main.py
# --------------------------------------------------------------------------
print("\n=== 6. wiring ===")

main_src = _read("main.py")


def _index(needle):
    return main_src.find(needle)


c.true("main.py builds the in-game menu", "game_menu = GameMenu(in_game=True)" in main_src)
c.true("run() builds the startup one", "GameMenu(save_path=path," in main_src)
c.true("the module and the class are imported apart",
       "from game.ui import game_menu as game_menu_module" in main_src
       and "from game.ui.game_menu import GameMenu" in main_src)

# ESC's bottom rung is the menu now. The two rungs above it are unchanged, and
# the fullscreen-quit rung is GONE - that is a recorded decision being
# reversed, so it is pinned in both directions.
c.true("ESC opens the menu",
       re.search(r"elif movement_controller\.selected_squad is not None:\s*\n"
                 r"\s*movement_controller\.select\(None\)\s*\n"
                 r"(\s*\n)?(\s*#[^\n]*\n)*\s*else:\s*\n"
                 r"(\s*#[^\n]*\n)*\s*_open_game_menu\(\)", main_src) is not None)
c.true("...and ESC no longer ends the process by itself",
       "elif fullscreen:\n                    running = False" not in main_src)

# BEFORE the state-gated chain. Roughly forty of its branches gate on
# controller state with no event.type term, so anything reachable only after
# them is one pending prompt away from being unreachable (error class 15).
menu_branch = _index("if game_menu.is_pending:\n                game_menu.handle_event")
button_branch = _index("game_menu.button_rect(right_panel_rect).collidepoint(event.pos)")
reader_branch = _index("if army_rules_overlay.is_pending:")
chain_start = _index("if event.type == pygame.QUIT:")
c.true("the menu's branch exists", menu_branch > 0)
c.true("the button's hit test exists", button_branch > 0)
c.true("the menu is asked before the state-gated chain", menu_branch < chain_start)
c.true("...and the button too", button_branch < chain_start)
c.true("the menu is asked before the army-rules reader", menu_branch < reader_branch)
c.true("the button is asked after it, so the reader gets the click first",
       button_branch < reader_branch or "not army_rules_overlay.is_pending" in main_src)
c.true("the menu's branch consumes the event",
       "game_menu.handle_event(event, screen.get_rect())\n                continue" in main_src)

# The AI must not act behind the menu. One term on the flag both AI entry
# points already read - and the auto-play tick runs OUTSIDE the event loop, so
# the branch's own `continue` does not cover it.
c.true("the AI is paused while the menu is up",
       "_any_pending_damage_choice() or game_menu.is_pending" in main_src)

# The answer is read once per frame, after the loop.
c.true("main() polls the menu's answer", "game_menu.take_action()" in main_src)
c.true("NEW_GAME and QUIT end the battle",
       re.search(r"outcome = _menu_answer\s*\n\s*running = False", main_src) is not None)
c.true("Save writes a snapshot", '_save_scene("saved from the menu")' in main_src)

# ONE writer for every snapshot, so no caller can quietly stop recording the
# armies - the line that makes a save restorable at all.
c.eq("there is one scene writer", main_src.count("def _save_scene("), 1)
c.true("F9 goes through it", '_save_scene("saved with F9")' in main_src)
c.eq("...and nothing else calls scene_io.write directly",
     main_src.count("scene_io.write("), 1)

# Drawn last, and the button is hidden behind either overlay.
c.true("the menu is drawn", "game_menu.draw(screen, pygame.mouse.get_pos())" in main_src)
c.true("...after the army-rules reader",
       _index("game_menu.draw(screen") > _index("army_rules_overlay.draw(screen)"))
c.true("...and before the frame is shown",
       _index("game_menu.draw(screen") < main_src.rindex("pygame.display.flip()"))
c.true("the button is not drawn under an overlay",
       "if not game_menu.is_pending and not army_rules_overlay.is_pending:" in main_src)
# Now that it lives in the right panel it is inside the AI-busy DIM
# (ai_busy_dim_rects), and it stays bright because it is drawn after it. That
# is wanted rather than tolerated - a stuck prompt is precisely the state a
# player most wants to reach the menu from - so it is pinned as an order.
c.true("the AI-busy dim covers the right panel",
       "ai_busy_dim_rects = (left_panel_rect, right_panel_rect)" in main_src)
c.true("...and the button is drawn after it, so it stays bright",
       _index("game_menu.draw_button(screen") > main_src.rindex("dim_rects=ai_busy_dim_rects"))
# The AI switch is handed NOTHING to avoid any more - the button it used to
# step around has moved into the right panel, and a control that stands still
# is worth more than a tight margin. Pinned in the NEGATIVE, because the way
# this regresses is somebody re-adding a blocker rather than removing one; the
# mechanism itself is exercised in section 5 at a synthetic blocker.
c.true("the AI switch is given no blocker to dodge",
       "avoid_rects=(game_menu.button_rect(" not in main_src)
c.true("...and the call is still there to give one to",
       "ai_toggle_rect = draw_ai_mode_toggle(" in main_src)
# ONE rect for the button, drawn from and clicked against. Worth pinning as the
# same EXPRESSION rather than each half against a literal: the round progress
# bar briefly shipped as chrome over the board, with the button handed a
# shortened rect to step into, and that arrangement is one edit away from
# leaving it DRAWN in one place and CLICKABLE in another. It is the RIGHT
# PANEL's rect now - the same one GameStatusPanel is drawn from, so the button
# lands in the header row that panel shortened for it.
c.true("the button is drawn from and hit-tested against the same rect",
       "game_menu.draw_button(screen, right_panel_rect, pygame.mouse.get_pos())" in main_src
       and "game_menu.button_rect(right_panel_rect).collidepoint(event.pos)" in main_src)
c.true("...and the board rect is not that rect any more",
       "game_menu.button_rect(board_rect_screen)" not in main_src)
# The panel that RESERVES the room is the panel that gets the button. Two
# modules each doing half of that arithmetic is how a title ends up drawn
# underneath a button, so both halves are pinned at their own call site.
c.true("the Game Status header reserves the room",
       "reserve_right=button_style.header_button_reserve()"
       in _read("game/ui/game_status_panel.py"))
c.true("the hover card is suppressed behind the menu",
       re.search(r"if game_menu\.is_pending:\s*\n(\s*#[^\n]*\n)*\s*_datacard_token = None",
                 main_src) is not None)

# run() is the application; main() is one battle.
c.true("run() exists", "\ndef run(map_key=None):" in main_src)
c.true("...above main()", _index("\ndef run(map_key=None):") < _index("\ndef main(map_key=None):"))
c.true("__main__ calls run(), not main()", "\n    run(map_key=_map_key)" in main_src)
c.true("run() loops while the menu asks for a new game",
       "if outcome != game_menu_module.NEW_GAME:" in main_src)
# Without this reset, "new game" would reopen the same save for ever.
c.true("a restart forgets the loaded scene",
       re.search(r"config\.LOAD_SCENE = None\s*\n\s*map_key = cli_map_key", main_src) is not None)
c.true("the menu is skipped when --load named a file",
       "if config.START_MENU and not config.LOAD_SCENE:" in main_src)
c.true("--no-menu exists", '"--no-menu"' in main_src)
c.true("config carries the flag", "START_MENU = True" in _read("game/config.py"))

# main() must not re-create the display: game/sprites.py caches convert_alpha()
# surfaces at module level and they outlive a battle, so the display they were
# converted against has to as well.
c.true("main() reuses the window run() opened",
       "screen = pygame.display.get_surface()" in main_src)

# THE AUTOSAVE (user: "Auto save pro Schlachtrunde"), which is what gives the
# menu's Resume entry anything to offer. Its edge is the battle ROUND, and the
# check runs outside the event loop so no branch can swallow it.
c.true("main() tracks the battle round for the autosave",
       "previous_battle_round" in main_src)
c.true("...and writes on the round's edge",
       "turn_tracker.battle_round != previous_battle_round" in main_src)
c.true("...to a fixed file, so it does not grow without bound",
       "scene_io.AUTOSAVE_NAME" in main_src)
# Held back until nothing is pending: a round boundary is the one instant at
# which every turn-scoped piece of mission state is empty, and half of it
# cannot be written to JSON at all.
c.true("...only from a settled board",
       re.search(r"turn_tracker\.battle_round != previous_battle_round:\s*\n"
                 r"\s*if \(not decision_manager\.is_pending", main_src) is not None)
c.true("...and it is not in the event loop, where a branch could swallow it",
       main_src.index("previous_battle_round = turn_tracker.battle_round\n                _save_scene")
       > main_src.index("input_manager.update_measuring"))
c.true("the snapshot carries the mission state",
       "missions=_mission_slots()" in main_src)
c.true("...and the load path puts it back", "scene_io.restore_missions(" in main_src)

c.finish()
