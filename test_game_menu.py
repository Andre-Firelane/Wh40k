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
  5. the board button- measured clear of the dice panel, and the AUTO-PLAY dot
                       steps out of its way.
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
from game.ui import button_style, dice_panel as dp  # noqa: E402
from game.ui.ai_busy_badge import ai_mode_toggle_rect  # noqa: E402
from game.ui.game_menu import GameMenu, NEW_GAME, QUIT, RESUME, SAVE  # noqa: E402
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

startup = [a for a, _l, _e, _n in GameMenu().entries()]
in_game = [a for a, _l, _e, _n in GameMenu(in_game=True).entries()]
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
       [e for a, _l, e, _n in GameMenu().entries() if a == RESUME] == [False])
c.true("...and with one, it is enabled",
       [e for a, _l, e, _n in GameMenu(save_path="x", save_note="n").entries()
        if a == RESUME] == [True])
# A DISABLED entry stays on screen. Dropping it would silently change the
# menu's shape between the two hosts, and the reason it cannot be pressed is
# the useful thing to show.
c.eq("a disabled Resume is still listed", len(GameMenu().entries()), 3)
c.true("...and says why", "no saved" in
       [n for a, _l, _e, n in GameMenu().entries() if a == RESUME][0])

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
               for g in (False, True) for a, _l, _e, _n in GameMenu(in_game=g).entries()))


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
           [e for a, _l, e, _n in GameMenu(save_path=broken,
                                           save_note=scene_io.summary(broken)).entries()
            if a == RESUME] == [False])


# --------------------------------------------------------------------------
# 5. the board button
# --------------------------------------------------------------------------
print("\n=== 5. the board button ===")

menu = GameMenu(in_game=True)
for width, height in ((1280, 720), (1366, 768), (1600, 900), (1920, 1080)):
    board = _board(width, height)
    btn = menu.button_rect(board)
    c.true(f"{width}x{height}: the button is inside the board", board.contains(btn))
    c.true(f"{width}x{height}: ...in its top-right corner",
           btn.centerx > board.centerx and btn.centery < board.centery)
    # "links oben neben dem rechten panel" - hard against the right panel.
    c.true(f"{width}x{height}: ...hard against the right panel",
           board.right - btn.right < 20)

    # THE ARITHMETIC, pinned rather than assumed: the dice panel is anchored
    # top-centre inside this same board rect, and it is the one thing that
    # could grow into this corner. 1280 is the narrowest window this project
    # is run at (tile_screen's own footer note names it) and is where the
    # margin is tightest - 14px measured.
    panel_width = min(board.width - 2 * dp.BACKDROP_MARGIN, dp.MAX_PANEL_WIDTH)
    dice_right = board.x + (board.width - panel_width) // 2 + panel_width
    c.true(f"{width}x{height}: the button clears the dice panel", btn.x > dice_right)

# The AI-MODE SWITCH shares this corner (it replaced the AUTO-PLAY dot that
# used to). It steps DOWN out of the way - not sideways, because sideways walks
# it into the dice panel.
board = _board(1920, 1080)
btn = menu.button_rect(board)
_toggle_font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True)
plain = ai_mode_toggle_rect(board, _toggle_font)
moved = ai_mode_toggle_rect(board, _toggle_font, avoid_rects=(btn,))
c.true("without a blocker the switch sits in the corner",
       plain.top == board.y + 12 and plain.right == board.right - 12)
c.true("the switch steps clear of the button", moved.topleft != plain.topleft)
c.eq("...straight down, keeping its column", moved.x, plain.x)
c.true("...and below the button", moved.top >= btn.bottom)
c.true("...still inside the board", board.contains(moved))
c.true("the two cannot share a pixel", not moved.colliderect(btn))
# The existing assurances about where the switch lives must survive the step.
c.true("the stepped switch is still in the board's top-right quadrant",
       moved.centerx > board.centerx and moved.centery < board.centery)
# A caller that passes nothing behaves exactly as before, which is what keeps
# test_ai_busy_badge.py green.
c.eq("avoid_rects defaults to no movement",
     ai_mode_toggle_rect(board, _toggle_font), plain)
c.eq("a None blocker is ignored",
     ai_mode_toggle_rect(board, _toggle_font, avoid_rects=(None,)), plain)


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
button_branch = _index("game_menu.button_rect(board_rect_screen).collidepoint(event.pos)")
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
c.true("the AUTO-PLAY dot is told to avoid the button",
       "avoid_rects=(game_menu.button_rect(board_rect_screen),)" in main_src)
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
