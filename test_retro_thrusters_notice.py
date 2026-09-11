"""The end of the Fight phase says what it is waiting for.

Report: "Zug 3 KI macht nichts mehr nach Fight Step. ich musste end of turn
anklicken."

Reproduced from the reported game, logs/game_20260911_132318.log:1067 and
:1447 - both times the line

    "Player 1: 1 The Twin Lance 1 can still use Retro-thrusters - select it to
     move or skip; the turn ends once you do."

is immediately followed by "Player 2's turn ends." The AI was not stuck: Fight
is the last phase (07.02), so "the end of the Fight phase" and "the end of the
turn" are one instant, and ai/agent_driver.py holds its own turn-end open while
the opponent still owes that move. Three things were wrong with how that looked
and what it cost:

  * the only sign was that one log line. The button is invisible until the unit
    is selected, so a player who does not already know the ability exists has
    nothing to act on.
  * the board said nothing at all.
  * the End Turn click went straight through - _has_unresolved_declaration()
    has no retro-thrusters term - and the free 6" move was discarded in
    silence.

And a fourth, found while reading it: that branch in ai/agent_driver.py had no
`else`, so EVERY other reason it stops there was a silent frame loop.

Deliberately NOT fixed by adding a term to _has_unresolved_declaration(): that
would be a hard lock, and a player who cannot find the Skip button would be
stuck for good. The user asked for a hint and a warning.
"""

import io
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()
pygame.font.init()

import testkit as tk  # noqa: E402
from game import config, fight as fight_module  # noqa: E402
from game import renderer as rd  # noqa: E402
from game.retro_thrusters import RetroThrustersController  # noqa: E402
from game.ui import action_panel as ap  # noqa: E402
from game.ui.fight_warning_overlay import FightWarningOverlay  # noqa: E402
from game.wait_notice import WaitNotice  # noqa: E402

checks = tk.Checks("Retro-thrusters: the wait is visible")

MAIN = io.open("main.py", encoding="utf-8").read()
DRIVER = io.open(os.path.join("ai", "agent_driver.py"), encoding="utf-8").read()


class Log:
    def __init__(self):
        self.lines = []

    def add(self, msg):
        self.lines.append(msg)

    def has(self, needle):
        return any(needle in l for l in self.lines)


# --- 1. WaitNotice: the shared once-per-window ledger -----------------------
print("--- 1. WaitNotice ---")

log = Log()
notice = WaitNotice(game_log=log)
checks.eq("the first time it is said", notice.say_once("a", "first"), True)
checks.eq("...and not the second", notice.say_once("a", "first again"), False)
checks.eq("only one line reached the log", len(log.lines), 1)
checks.eq("a DIFFERENT key is its own question", notice.say_once("b", "second"), True)
checks.eq("...so two lines now", len(log.lines), 2)
checks.true("it can be asked without saying anything", notice.already_said("a"))
notice.reset()
checks.eq("reset re-arms it - without a point at X, a once-per-phase line "
          "becomes once-per-battle", notice.say_once("a", "first"), True)
# It must survive having no log at all: main.py builds one before the log in
# some orders, and a crash there would be a crash in the frame loop.
checks.eq("no log is not a crash", WaitNotice().say_once("a", "x"), True)


# --- 2. the controller's own question ---------------------------------------
print("--- 2. pending_squads() ---")
# The one source all three halves read. Built as a scene so the eligibility
# latch is the real one rather than a stub's idea of it.


from game.board import Board  # noqa: E402
from game.factions import tau_empire as tau  # noqa: E402
from game.movement import MovementController  # noqa: E402

tk_attacker, tk_target = tau.THE_TWIN_LANCE, tau.KROOT_CARNIVORES


def scene():
    return tk.fight_scene(tk_attacker, tk_target, attacker_owner="Player 1")


sc = scene()
lance = sc["attacker"]
fc = sc["fight"]
rt_log = Log()
rt = RetroThrustersController(
    fight_controller=fc,
    movement_controller=MovementController(turn_tracker=sc["turn"],
                                           all_tokens=sc["state"].tokens),
    turn_tracker=sc["turn"], all_tokens=sc["state"].tokens, game_log=rt_log,
)
rt.note_eligibility()
checks.true("the Twin Lance latched as eligible while the phase ran",
            rt.can_use(lance))
checks.eq("...so it is listed as pending", [s.name for s in rt.pending_squads()], [lance.name])
checks.eq("...and under its own owner", [s.name for s in rt.pending_squads("Player 1")],
          [lance.name])
checks.eq("...but not under the other one", rt.pending_squads("Player 2"), [])
rt.decline(lance)
checks.eq("declining clears it", rt.pending_squads(), [])

# The wait announcement is once per OWNER per Fight phase, and the phase reset
# has to re-arm it - without a point at X, a "deferred until X" note becomes a
# once-per-battle note and every later phase goes silent.
rt2 = RetroThrustersController(
    fight_controller=fc,
    movement_controller=MovementController(turn_tracker=sc["turn"],
                                           all_tokens=sc["state"].tokens),
    turn_tracker=sc["turn"], all_tokens=sc["state"].tokens, game_log=rt_log,
)
rt2.note_eligibility()
rt_log.lines.clear()
rt2.announce_wait_once("Player 2")
checks.eq("the wait is announced once", len(rt_log.lines), 1)
rt2.announce_wait_once("Player 2")
checks.eq("...and not again in the same phase", len(rt_log.lines), 1)
rt2.reset_fight_phase()
rt2.note_eligibility()
rt2.announce_wait_once("Player 2")
checks.eq("...but a NEW Fight phase re-arms it", len(rt_log.lines), 2)


# --- 3. the panel names them ------------------------------------------------
print("--- 3. the left panel ---")

PANEL = pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, 900)
SURFACE = pygame.Surface((config.LEFT_PANEL_WIDTH, 900))
BG = (12, 12, 12)


class FakeRetro:
    def __init__(self, squads):
        self._squads = squads

    def pending_squads(self, owner=None):
        if owner is None:
            return list(self._squads)
        return [s for s in self._squads if s.owner == owner]


class FakeFight:
    def __init__(self, state):
        self.state = state
        self.whose_turn = "Player 1"

    def can_pass(self):
        return False


class FakePileIn:
    def has_pending_squads(self):
        return False

    def squads_pending_pile_in(self, player=None):
        return []


def panel_ink(color, tol=12):
    n = 0
    for y in range(SURFACE.get_height()):
        for x in range(SURFACE.get_width()):
            px = SURFACE.get_at((x, y))[:3]
            if all(abs(px[i] - color[i]) <= tol for i in range(3)):
                n += 1
    return n


def render_fight_status(retro, state=fight_module.DONE):
    SURFACE.fill(BG)
    panel = ap.ActionPanel()
    panel._buttons = []
    panel._draw_fight_step_status(
        SURFACE, PANEL, 180, FakeFight(state), FakePileIn(),
        retro_thrusters_controller=retro)
    return panel


class Sq:
    def __init__(self, name, owner):
        self.name, self.owner = name, owner


_one = Sq("1 The Twin Lance 1", "Player 1")
render_fight_status(FakeRetro([_one]))
checks.true("the box is painted in its own accent",
            panel_ink(ap.RETRO_ACCENT_COLOR) > 20)
# THE counter-check: without it this passes on a panel that paints the box
# unconditionally, which is the opposite complaint.
render_fight_status(FakeRetro([]))
checks.eq("nothing is painted when nothing is pending",
          panel_ink(ap.RETRO_ACCENT_COLOR), 0)
# ...and the branch it replaces still works.
_p = render_fight_status(FakeRetro([]))
checks.true("a finished Fight step still says so", _p is not None)

# Its colour must be its OWN - the pile-in box can be up in the same phase and
# names DIFFERENT units, so sharing one colour would make them one message.
checks.true("the accent differs from the pile-in box's",
            ap.RETRO_ACCENT_COLOR != ap.PILE_IN_ACCENT_COLOR)
checks.true("...and so does its background",
            ap.RETRO_BOX_BG_COLOR != ap.PILE_IN_BOX_BG_COLOR)

# Grouped by OWNER, because the panel has no idea which player is the human.
_two = [Sq("1 The Twin Lance 1", "Player 1"), Sq("2 Ghost Ark 1", "Player 2")]
render_fight_status(FakeRetro(_two))
checks.true("two owners still paint one box", panel_ink(ap.RETRO_ACCENT_COLOR) > 20)

# The alternation can still be running while a unit that already fought owes
# its move, and being told only at the very end leaves no time to act.
render_fight_status(FakeRetro([_one]), state=fight_module.SELECTING)
checks.true("it is shown during SELECTING too", panel_ink(ap.RETRO_ACCENT_COLOR) > 20)


# --- 4. the board rings them ------------------------------------------------
print("--- 4. the board ---")

BOARD_SURF = pygame.Surface((600, 600))


def board_ink(color, tol=14):
    n = 0
    for y in range(0, BOARD_SURF.get_height(), 2):
        for x in range(0, BOARD_SURF.get_width(), 2):
            px = BOARD_SURF.get_at((x, y))[:3]
            if all(abs(px[i] - color[i]) <= tol for i in range(3)):
                n += 1
    return n


_r = rd.Renderer()
_board = Board(40.0, 30.0, 20)
sc2 = scene()
lance2 = sc2["attacker"]
tk.line_up(lance2, x=15.0, y=15.0)
BOARD_SURF.fill((0, 0, 0))
_r.draw_retro_thrusters_pending(BOARD_SURF, _board, [lance2])
checks.true("a pending unit is ringed", board_ink(rd.RETRO_PENDING_COLOR) > 0)
BOARD_SURF.fill((0, 0, 0))
_r.draw_retro_thrusters_pending(BOARD_SURF, _board, [])
checks.eq("an empty list rings nothing", board_ink(rd.RETRO_PENDING_COLOR), 0)
checks.eq("the ring colour is the panel's, so the two read as one fact",
          rd.RETRO_PENDING_COLOR, ap.RETRO_ACCENT_COLOR)
# It must not be a colour the board already uses for something else.
for name in ("COHERENCY_REMOVAL_COLOR", "DAMAGE_CHOICE_COLOR", "SHOOT_TARGET_COLOR",
             "RETURNING_MODEL_COLOR"):
    checks.true(f"...and not {name}",
                rd.RETRO_PENDING_COLOR != getattr(rd, name))


# --- 5. the End Turn warning carries BOTH reasons ---------------------------
print("--- 5. the warning ---")

ov = FightWarningOverlay()
checks.eq("the melee reason alone still warns", ov.warn_once(["1 Boyz 1"]), True)
checks.true("...and is pending", ov.is_pending)
ov.dismiss()
ov.reset()
checks.eq("the retro reason ALONE warns too",
          ov.warn_once([], retro_names=["1 The Twin Lance 1"]), True)
checks.true("...and is pending", ov.is_pending)
ov.dismiss()
ov.reset()
checks.eq("neither reason raises nothing", ov.warn_once([], retro_names=[]), False)

# ...and it is still ONE warning per phase, whichever reason raised it.
ov.reset()
ov.warn_once([], retro_names=["1 The Twin Lance 1"])
ov.dismiss()
checks.eq("a second click in the same phase goes through",
          ov.warn_once([], retro_names=["1 The Twin Lance 1"]), False)
ov.reset()
checks.eq("...and a new phase re-arms it",
          ov.warn_once([], retro_names=["1 The Twin Lance 1"]), True)

# On PIXELS: both reasons named, and the single-reason picture unchanged.
WARN = pygame.Surface((1000, 800))


def warn_text_rows(overlay):
    WARN.fill((0, 0, 0))
    overlay.draw(WARN)
    return sum(1 for y in range(WARN.get_height())
               if any(WARN.get_at((x, y))[:3] != (0, 0, 0) for x in range(0, 1000, 3)))


ov.dismiss()
ov.reset()
ov.warn_once(["1 Boyz 1"])
_melee_only = warn_text_rows(ov)
ov.dismiss()
ov.reset()
ov.warn_once(["1 Boyz 1"], retro_names=["1 The Twin Lance 1"])
_both = warn_text_rows(ov)
checks.true("the box grows when the second reason is there too", _both > _melee_only)
ov.dismiss()
ov.reset()
ov.warn_once([], retro_names=["1 The Twin Lance 1"])
checks.true("the retro-only box is drawn at all", warn_text_rows(ov) > 0)


# --- 6. the AI says WHY it is waiting ---------------------------------------
print("--- 6. the AI's reason ---")
# The branch had no `else`, so every state but DONE was a silent frame loop.

from ai.agent_driver import _announce_fight_wait  # noqa: E402


class FakeTurn:
    def __init__(self, owner):
        self.turn_owner = owner


class FakePileInPending:
    def __init__(self, squads):
        self._squads = squads

    def squads_pending_pile_in(self, player=None):
        return list(self._squads)


wlog = Log()
wn = WaitNotice(game_log=wlog)
_announce_fight_wait("Player 2", FakeTurn("Player 2"), FakeFight(fight_module.NOT_STARTED),
                     FakePileInPending([_one]), wn)
checks.true("an outstanding Pile In is named", wlog.has("piled in or skipped"))
checks.true("...with the unit", wlog.has("1 The Twin Lance 1"))
checks.true("...and its owner, so 'is that me?' has an answer", wlog.has("Player 1:"))
_before = len(wlog.lines)
_announce_fight_wait("Player 2", FakeTurn("Player 2"), FakeFight(fight_module.NOT_STARTED),
                     FakePileInPending([_one]), wn)
checks.eq("...said once, not once per frame", len(wlog.lines), _before)

wlog2 = Log()
wn2 = WaitNotice(game_log=wlog2)
_f = FakeFight(fight_module.SELECTING)
_f.whose_turn = "Player 1"
_announce_fight_wait("Player 2", FakeTurn("Player 2"), _f, FakePileIn(), wn2)
checks.true("the 12.04 alternation is named", wlog2.has("to select a unit to fight"))

# Silent while the turn belongs to the HUMAN: waiting is correct then, and they
# have their own End Turn button. Without this it would chatter every phase.
wlog3 = Log()
wn3 = WaitNotice(game_log=wlog3)
_announce_fight_wait("Player 2", FakeTurn("Player 1"), FakeFight(fight_module.NOT_STARTED),
                     FakePileInPending([_one]), wn3)
checks.eq("nothing is said during the human's own turn", wlog3.lines, [])


# --- 7. wiring: the halves no behaviour test can see ------------------------
print("--- 7. wiring ---")

checks.true("the panel gets the controller at both call sites",
            MAIN.count("retro_thrusters_controller=retro_thrusters_controller") >= 1)
checks.true("main.py rings the pending units on the board",
            "renderer.draw_retro_thrusters_pending(" in MAIN)
checks.true("...and not while a damage allocation owns the board",
            "if not _any_pending_damage_choice():" in MAIN)
checks.true("the End Turn gate asks for the second reason too",
            "retro_names=[s.name for s in retro_thrusters_controller.pending_squads(\"Player 1\")]"
            in MAIN)
# By AST, not by substring: "_announce_fight_wait(player, turn_tracker," also
# matches the function's own def line, so a probe that deletes the CALL leaves
# the guard green. The repo has paid for this shape before - a guard that
# matches its own definition.
import ast  # noqa: E402

_calls = [n for n in ast.walk(ast.parse(DRIVER))
          if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "_announce_fight_wait"]
checks.eq("the AI branch really CALLS the announcer, not just defines it",
          len(_calls), 1)
checks.true("main.py builds the shared notice", "fight_wait_notice = WaitNotice(" in MAIN)
checks.true("...hands it to the driver", "fight_wait_notice=fight_wait_notice," in MAIN)
checks.true("...and resets it on the Fight-phase boundary",
            "fight_wait_notice.reset()" in MAIN)
# Deliberately NOT a hard lock - see the module docstring.
checks.eq("retro-thrusters is NOT a term in the phase gate",
          "retro_thrusters_controller.pending_squads()" in
          MAIN[MAIN.index("def _has_unresolved_declaration"):
               MAIN.index("def _fight_warning_intercepts_end_turn")], False)

checks.finish()
