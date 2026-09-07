"""Picking a unit by CLICKING IT ON THE BATTLEFIELD, everywhere.

User: "Immer wenn man eine einheit auf dem schlachtfeld waehlen muss (zb wall
of mirrors) will ich die einheit nicht aus einer liste waehlen, sondern auf dem
schlachtfeld. Wie bei overwatch."

WHAT IS WORTH ASSERTING HERE, in order of how badly it can go wrong:

1. THE TWO REFUSALS. game/unit_pick.py turns a prompt into a board pick only if
   every tagged unit is really standing on the board and no unit is offered
   twice. Get either wrong and the game waits for a click that can never
   happen - CLAUDE.md's Fehlerklasse 25, the one class here that deadlocks
   instead of quietly doing nothing. Both are measured from BOTH sides: the
   refusal, and the fact that the decision is still answerable as a list.

2. THE COVERAGE SWEEP (section 6). A behaviour test cannot see the 57th call
   site, because it does not exist yet. So the set of option lists that name a
   unit and are NOT tagged is pinned at the SOURCE, each with its reason. A new
   untagged one fails this suite by name.

3. THE WIRING. "Built but never fed" has hit this repo six times, and a board
   pick that is blocked-but-unclickable is the worst version of it. main.py's
   branch, the panel screen, the board rings and the overlay's stand-aside are
   four readers of ONE derivation, and the suite checks each of them.
"""

import ast
import io
import os
import re

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()
pygame.font.init()

import testkit as tk  # noqa: E402
from game import config, unit_pick  # noqa: E402
from game.board import Board  # noqa: E402
from game.decision import DecisionManager  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game.renderer import Renderer  # noqa: E402
from game.ui.action_panel import ActionPanel  # noqa: E402
from game.ui.decision_overlay import DecisionOverlay  # noqa: E402
from game.factions import aeldari as ae  # noqa: E402

checks = tk.Checks("Unit pick")

HERE = os.path.dirname(os.path.abspath(__file__))


def squad_at(name, x, y, owner="Player 1"):
    squad = tk.build(ae.RANGERS, owner=owner, name=name)
    for i, model in enumerate(squad.models):
        model.x_in, model.y_in = x + i * 1.2, y
    return squad


ALPHA = squad_at("1 Rangers ALPHA", 10.0, 10.0)
BETA = squad_at("1 Rangers BETA", 25.0, 10.0)
GAMMA = squad_at("2 Rangers GAMMA", 25.0, 20.0, owner="Player 2")
TOKENS = list(ALPHA.models) + list(BETA.models) + list(GAMMA.models)


def opened(options, subject=None):
    """A fresh manager with one pending decision - so no test leaks a queue
    entry into the next one."""
    manager = DecisionManager()
    manager.request("Player 1", "which unit?", options, subject=subject)
    return manager


EMPTY = unit_pick.UnitPick("", None, [], {}, [], lambda _i: None)


def safe(pick):
    """`pick` or a blank stand-in. A probe that switches the feature off makes
    pending() return None everywhere, and indexing into that would ABORT this
    suite instead of turning it red - the ninth time this repo has recorded
    that lesson. Red names which assurance was lost; a traceback does not."""
    return EMPTY if pick is None else pick


# --- 1. the tag rides in the option tuple ---------------------------------
print("--- 1. the tag ---")

taken = []
dm = opened([(ALPHA.name, lambda: taken.append(ALPHA), ALPHA),
             ("Decline", lambda: taken.append("no"))])

# The label/callback pair has to sit at the SAME index it always did: choose(),
# the overlay and ai/agent_driver.py's _maybe_resolve_decision() all address an
# option by number, and none of them was touched by this feature.
checks.eq("options still read as label/callback",
          [o["label"] for o in dm.options], [ALPHA.name, "Decline"])
checks.eq("a plain 2-tuple option simply has no unit", dm.options[1]["squad"], None)
checks.true("a 3-tuple option carries its unit", dm.options[0]["squad"] is ALPHA)
checks.eq("the manager can find the option that offers a unit",
          dm.index_of_squad(ALPHA), 0)
checks.eq("...and says so when nothing offers it", dm.index_of_squad(GAMMA), None)
checks.eq("subject defaults to None", dm.subject, None)
checks.eq("...and is carried when given", opened([("x", None)], subject="Central").subject,
          "Central")
dm.choose(0)
checks.eq("choosing by index still runs the callback", taken, [ALPHA])
checks.eq("...and pops the queue", dm.is_pending, False)


# --- 2. is this decision answerable on the board? -------------------------
print("--- 2. pending() ---")

checks.eq("nothing pending is not a pick", unit_pick.pending(DecisionManager(), TOKENS), None)

plain = opened([("Use", None), ("Decline", None)])
checks.eq("an untagged decision stays a list", unit_pick.pending(plain, TOKENS), None)

dm = opened([(ALPHA.name, lambda: None, ALPHA), (BETA.name, lambda: None, BETA),
             ("Decline", lambda: None)], subject="Central Objective")
pick = unit_pick.pending(dm, TOKENS)
checks.true("a tagged decision with its units on the board IS a pick", pick is not None)
pick = safe(pick)
checks.eq("it lists the units in the order they were offered",
          [s.name for s in pick.squads], [ALPHA.name, BETA.name])
checks.eq("it carries the prompt", pick.prompt, "which unit?")
checks.eq("it carries the subject", pick.subject, "Central Objective")
checks.eq("the non-unit options become the way out",
          [label for label, _i in pick.skip_options], ["Decline"])
checks.eq("...and keep the index they resolve through",
          [i for _label, i in pick.skip_options], [2])
checks.true("an offered unit is eligible", pick.is_eligible(ALPHA))
checks.eq("...and one that was not offered is not", pick.is_eligible(GAMMA), False)
checks.eq("...and neither is nothing", pick.is_eligible(None), False)

# REFUSAL 1: a unit that is not on the board cannot be clicked. Both halves -
# the refusal AND that the decision is still answerable - because a refusal
# that left the prompt unanswerable would be the very deadlock it prevents.
off_board = squad_at("1 Rangers RESERVE", 5.0, 5.0)
dm = opened([(off_board.name, lambda: None, off_board), ("Decline", lambda: None)])
checks.eq("a unit with no token on the board is refused",
          unit_pick.pending(dm, TOKENS), None)
checks.true("...and the decision is still there to answer as a list", dm.is_pending)
checks.eq("...with every option intact", len(dm.options), 2)

# ONE unit off the board is enough: dropping it silently would remove a legal
# option, so the whole prompt falls back rather than half of it.
dm = opened([(ALPHA.name, lambda: None, ALPHA),
             (off_board.name, lambda: None, off_board)])
checks.eq("one off-board unit refuses the whole prompt", unit_pick.pending(dm, TOKENS), None)

# A squad wiped out THIS frame still has models in it - remove_dead_models()
# runs once per frame (Fehlerklasse 12) - so liveness is asked of the tokens.
dead = squad_at("1 Rangers DEAD", 30.0, 30.0)
for model in dead.models:
    model.current_wounds = 0
dm = opened([(dead.name, lambda: None, dead), ("Decline", lambda: None)])
checks.eq("a unit whose models are all dead cannot be clicked",
          unit_pick.pending(dm, TOKENS + list(dead.models)), None)

# REFUSAL 2: a click says "this unit", not "this option".
dm = opened([("Free", lambda: None, ALPHA), ("1 CP", lambda: None, ALPHA),
             ("Decline", lambda: None)])
checks.eq("the same unit offered twice is refused", unit_pick.pending(dm, TOKENS), None)
checks.true("...and that decision is still answerable as a list", dm.is_pending)

# A mandatory choice gets no way out invented for it.
dm = opened([(ALPHA.name, lambda: None, ALPHA), (BETA.name, lambda: None, BETA)])
checks.eq("a prompt with no way out offers none", safe(unit_pick.pending(dm, TOKENS)).skip_options, [])


# --- 3. resolving a click -------------------------------------------------
print("--- 3. the click ---")

taken = []
dm = opened([(ALPHA.name, lambda: taken.append(ALPHA), ALPHA),
             (BETA.name, lambda: taken.append(BETA), BETA),
             ("Decline", lambda: taken.append("no"))])
pick = safe(unit_pick.pending(dm, TOKENS))
checks.eq("clicking a unit that was not offered does nothing", pick.pick(GAMMA), False)
checks.eq("...it resolves nothing", taken, [])
checks.true("...and the decision stays open", dm.is_pending)
checks.true("clicking an offered unit takes", pick.pick(BETA))
checks.eq("...and runs THAT unit's callback, not the first one", taken, [BETA])
checks.eq("...and pops the decision", dm.is_pending, False)

# The rings. "Wie bei overwatch" - so this feeds the same draw_shoot_targets()
# that Fire Overwatch's eligible units go through.
dm = opened([(ALPHA.name, lambda: None, ALPHA), ("Decline", lambda: None)])
pick = safe(unit_pick.pending(dm, TOKENS))
ringed = unit_pick.target_models(pick, TOKENS)
checks.eq("only the eligible unit's models are ringed",
          sorted({m.squad.name for m in ringed}), [ALPHA.name])
checks.eq("...all of them", len(ringed), len([m for m in ALPHA.models]))
checks.eq("no pick, no rings", unit_pick.target_models(None, TOKENS), set())


# --- 4. the two screens -----------------------------------------------------
print("--- 4. the screens ---")

PPI = 20
board = Board(60.0, 44.0, PPI)
LEFT = pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, 900)
movement = MovementController(all_tokens=TOKENS)


def panel_pixels(pick_record):
    """The pick screen, drawn for real.

    Only that screen is exercised: with the pick branch gone the dispatch falls
    through to branches that want the rest of the game's controllers, and
    standing those up would be testing the panel rather than this feature. A
    fall-through is caught and reported as "nothing drawn" so a probe that
    removes the branch turns this suite RED instead of aborting it."""
    surface = pygame.Surface((config.LEFT_PANEL_WIDTH, 900))
    panel = ActionPanel()
    try:
        panel.draw(surface, LEFT, movement, None, unit_pick=pick_record)
    except AttributeError:
        return panel, None
    return panel, pygame.image.tostring(surface, "RGB")


dm = opened([(ALPHA.name, lambda: None, ALPHA), (BETA.name, lambda: None, BETA),
             ("Decline", lambda: None)], subject="Central Objective")
pick = safe(unit_pick.pending(dm, TOKENS))
panel, with_two = panel_pixels(pick)
checks.true("the panel draws the pick screen", bool(panel._buttons))

# The eligible units are NAMED, not only ringed: the ring is the faster read,
# but a unit standing behind another one survives only in the list.
one = unit_pick.UnitPick(pick.prompt, pick.subject, [ALPHA], {id(ALPHA): 0},
                         pick.skip_options, pick.choose)
_p, with_one = panel_pixels(one)
checks.true("the screen changes when the eligible set does", with_two != with_one)

# The subject is what makes the question answerable where a rule has one.
other = unit_pick.UnitPick(pick.prompt, "Objective West", pick.squads, pick.indices,
                           pick.skip_options, pick.choose)
_p, elsewhere = panel_pixels(other)
checks.true("the screen names the SUBJECT, not a placeholder", with_two != elsewhere)
none_subject = unit_pick.UnitPick(pick.prompt, None, pick.squads, pick.indices,
                                  pick.skip_options, pick.choose)
_p, no_subject = panel_pixels(none_subject)
checks.true("a rule with no subject simply gets no heading", with_two != no_subject)

# The way out is a real button, wired to the same choose() a click uses.
panel, _ = panel_pixels(pick)
for _rect, callback in panel._buttons[:1]:
    callback()
checks.eq("the panel's way out resolves the decision", dm.is_pending, False)

# The overlay stands aside. It dims the whole window, so drawing it over a
# board the player has to click would defeat the point.
overlay = DecisionOverlay()
dm = opened([(ALPHA.name, lambda: None, ALPHA), ("Decline", lambda: None)])
pick = safe(unit_pick.pending(dm, TOKENS))
screen = pygame.Surface((1280, 720))
screen.fill((7, 11, 13))
blank = pygame.image.tostring(screen, "RGB")
overlay.draw(screen, dm, (), board_pick=True)
checks.eq("the overlay draws NOTHING during a board pick",
          pygame.image.tostring(screen, "RGB"), blank)
checks.eq("...and leaves no clickable button behind",
          overlay.handle_click((640, 360)), None)
overlay.draw(screen, dm, (), board_pick=False)
checks.true("...but a list decision still gets its modal box",
            pygame.image.tostring(screen, "RGB") != blank)

# A stale button rect must not keep swallowing clicks after the picture is
# gone: the overlay clears them FIRST, before it returns.
overlay.draw(screen, dm, (), board_pick=True)
checks.eq("a pick clears last frame's option buttons",
          overlay.handle_click((640, 360)), None)

# The rings really reach the board.
def ring_pixels(models):
    surface = pygame.Surface((board.width_px, board.height_px))
    surface.fill((0, 0, 0))
    Renderer(render_scale=1.0).draw_shoot_targets(surface, board, models)
    return sum(1 for x in range(0, surface.get_width(), 3)
               for y in range(0, surface.get_height(), 3)
               if surface.get_at((x, y))[:3] != (0, 0, 0))


dm = opened([(ALPHA.name, lambda: None, ALPHA), ("Decline", lambda: None)])
pick = safe(unit_pick.pending(dm, TOKENS))
inked = ring_pixels(unit_pick.target_models(pick, TOKENS))
checks.true("the eligible unit really gets rings on the board", inked > 0)
checks.eq("...and nothing is drawn without a pick", ring_pixels(set()), 0)
checks.true("...and fewer rings than if every unit qualified",
            inked < ring_pixels(set(TOKENS)))


# --- 5. wiring: four readers, one derivation --------------------------------
print("--- 5. wiring ---")

MAIN = io.open(os.path.join(HERE, "main.py"), encoding="utf-8").read()
PANEL_SRC = io.open(os.path.join(HERE, "game/ui/action_panel.py"), encoding="utf-8").read()


def at(needle, src=None):
    """.find(), never .index(): a source guard must REPORT what is missing
    instead of dying on a traceback - which is exactly backwards when the point
    of an A/B probe is to show which assurances the pre-fix world loses."""
    position = (src if src is not None else MAIN).find(needle)
    return None if position < 0 else position


# The IMPORT, not the exact import LINE: this pinned "from game import
# unit_pick" verbatim and went red the moment a second module joined that same
# line - a formatting change, not a wiring one. Same lesson as the punctuation
# pins this repo has had to turn around before.
checks.true("main.py imports the module",
            re.search(r"^from game import .*\bunit_pick\b", MAIN, re.M) is not None)
checks.true("...and derives the pick in ONE helper",
            "return unit_pick.pending(decision_manager, state.tokens)" in MAIN)
checks.eq("the helper is defined once", MAIN.count("def board_unit_pick():"), 1)
# Derived FRESH in the event branch: resolving one pick can enqueue the next in
# the same event, and a record captured at the top of the frame would then be
# answering a question that is already gone.
# The whole guarded STATEMENT, not just the call: a probe that neutralises the
# branch to `if False:` leaves every substring below intact, and a pin that
# survives it is measuring nothing. This is the same lesson as the docstring
# match and the `if False and ...` pin already recorded in CLAUDE.md.
GUARDED = "pick = board_unit_pick()" + chr(10) + " " * 20 + "if pick is not None:"
checks.true("the event branch asks for a fresh derivation and acts on it",
            GUARDED in MAIN)
checks.true("the board click resolves through the record", "pick.pick(clicked.squad)" in MAIN)
checks.true("...and the left panel keeps its own clicks",
            "action_panel.handle_click(event.pos)" in MAIN)
checks.true("the frame derives it once for drawing",
            "frame_unit_pick = board_unit_pick()" in MAIN)
checks.true("the rings are drawn from it",
            "unit_pick.target_models(frame_unit_pick, state.tokens)" in MAIN)
checks.true("the panel is handed it", "unit_pick=frame_unit_pick" in MAIN)
checks.true("the overlay is told to stand aside",
            "board_pick=frame_unit_pick is not None" in MAIN)

# It lives INSIDE the pending-decision branch. That branch swallows every other
# click while a decision is open, which is what keeps a non-modal pick from
# letting "Next Phase" be pressed out from under an unanswered question.
branch = at("elif decision_manager.is_pending:")
checks.true("the pick is handled inside the pending-decision branch",
            branch is not None and at("pick.pick(clicked.squad)") > branch)
# ...and ahead of InputManager, the LAST link in the chain and the one that
# turns a board click into a camera pan. Compared against that rather than
# against "elif board_rect_screen..." - a dozen branches contain that same
# line, so the first hit would be this branch itself and the check would pass
# by measuring nothing.
checks.true("...and ahead of the camera/selection fallthrough",
            at("pick.pick(clicked.squad)") < at("input_manager.handle_event("))

checks.eq("the panel declares the parameter at both stages",
          PANEL_SRC.count("unit_pick=None"), 2)
checks.eq("...and forwards it down the chain", PANEL_SRC.count("unit_pick=unit_pick"), 1)
checks.true("the dispatch branches on it", "if unit_pick is not None:" in PANEL_SRC)


# --- 6. coverage: every unit list is tagged ---------------------------------
print("--- 6. coverage ---")

# THE structural guard. A behaviour test cannot see a call site that does not
# exist yet, so the MENGENDIFFERENZ is taken at the source: every option list
# whose label reads "<loop var>.name" either carries its third element or is
# named below with the reason it cannot.
EXEMPT = {
    # Not units at all - these name OBJECTIVES or CARDS.
    "game/aac_marker_beacon.py",
    "game/enh_strategic_conqueror.py",
    "game/kauyon_tempting_trap.py",
    "game/primary_missions.py",
    # Two entries in this file are objective/card lists; the unit ones are
    # tagged (Beacon's draw_choices, Burden of Trust's guards).
    "game/secondary_missions.py",
    # Units, but not clickable: Rapid Ingress offers units in Strategic
    # Reserves (no token) and lists a Homing Beacon unit TWICE.
    "game/rapid_ingress.py",
    # Not a decision at all: the datacard's per-component ability groups.
    "game/ui/unit_datacard.py",
}


def option_tuples():
    """Every (label, callback[, squad]) whose label mentions the loop variable's
    name - in both shapes an option list takes here: a comprehension, and
    appends inside a for-loop."""
    for root, dirs, files in os.walk(os.path.join(HERE, "game")):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for fn in sorted(files):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, HERE).replace("\\", "/")
            tree = ast.parse(io.open(path, encoding="utf-8").read())
            for node in ast.walk(tree):
                if isinstance(node, ast.ListComp) and len(node.generators) == 1:
                    target, elt = node.generators[0].target, node.elt
                    if isinstance(target, ast.Name) and isinstance(elt, ast.Tuple):
                        yield rel, node.lineno, target.id, elt
                elif isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                    for call in ast.walk(node):
                        if (isinstance(call, ast.Call)
                                and isinstance(call.func, ast.Attribute)
                                and call.func.attr == "append" and call.args
                                and isinstance(call.args[0], ast.Tuple)):
                            yield rel, call.lineno, node.target.id, call.args[0]


tagged, untagged = [], []
for rel, lineno, var, elt in option_tuples():
    if len(elt.elts) < 2 or f"{var}.name" not in ast.unparse(elt.elts[0]):
        continue
    (tagged if len(elt.elts) == 3 else untagged).append((rel, lineno))

checks.true("the sweep actually found the tagged call sites", len(tagged) >= 55)
stray = sorted({rel for rel, _ln in untagged} - EXEMPT)
checks.eq("every option list that names a unit is tagged (or documented)", stray, [])
# ...and the exempt list is not allowed to rot: each entry must still have an
# untagged unit-ish option list in it, or it is a stale excuse.
still_untagged = {rel for rel, _ln in untagged}
checks.eq("no exemption outlives its reason", sorted(EXEMPT - still_untagged), [])

checks.finish()
