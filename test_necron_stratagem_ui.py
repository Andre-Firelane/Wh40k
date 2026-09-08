"""Are the three Necron panel Stratagems really OFFERED, and at the right
moment? - measured by drawing the real ActionPanel.

WHY THIS FILE EXISTS
--------------------
The Aeldari audit found five "the rule is right, the controller is right, and
the button is never on the screen" defects; the T'au audit found four more.
Both times the structural cause was the same: no test had ever drawn the real
panel for that faction's buttons.

The Necrons are in the same position, and worse guarded than either. The three
proactive protocols do NOT go through game/proactive_stratagems.py - none of
them defines panel_label(), so they are handed to ActionPanel.draw() as their
own keyword arguments, and section 14 of test_event_chain_wiring.py ("every
controller with a panel_label() reaches the panel") cannot see them. The only
standing proof was test_awakened_dynasty.py's

    "hungry_void_controller=hungry_void_controller" in main_src

which holds under `if False:`, holds while the panel draws nothing at all, and
holds when the button appears in every phase.

So this file renders. Real controllers, real ActionPanel, once per phase, then
asks which Stratagem names came out of the button funnel.

THE PHASE MATRIX IS THE POINT (section 2). Each of the three is rendered in all
FIVE phases and must appear in exactly the ones its printed WHEN names - two
negatives per Stratagem per player. A test that renders only the right phase
cannot tell "offered correctly" from "offered always".

WHAT DIFFERS FROM THE AELDARI AND T'AU MIRRORS, all measured rather than
assumed, and each a place a copied suite would quietly measure nothing:

  * HUNGRY VOID HAS NO OWNER CLAUSE, and that is faithful: its printed WHEN is
    "Fight phase.", where Sudden Storm and Conquering Tyrant both print "Your".
    Every one of the fourteen T'au registry Stratagems reads active_player, so
    the T'au suite had to ask the owner clause at can_use() - the panel draws
    nothing in most phases outside a unit's own turn because
    MovementController.select() refuses it.

    THAT DOES NOT APPLY IN THE FIGHT PHASE. can_select() returns True
    unconditionally there (rules 12.02/12.04, both players act), so Hungry
    Void's missing owner clause is measurable AT THE REAL PANEL with the turn
    flipped - section 2b. It is the one thing this matrix can prove that
    neither of the other two could.

  * THE BUTTONS ARE BESPOKE KEYWORD ARGUMENTS, not a registry. Section 6
    therefore pins the three-stage chain by AST - signature, both forwarding
    hops, and the positional prefix of main.py's call - rather than an index,
    and pins the standing decision NOT to migrate them, so a later clean-up
    that registers one turns this red on purpose.

  * TWO OF THE THREE REFUSE ON AN ENGINE LEDGER (fought_squad_ids,
    shot_squad_ids). Those are pinned as NEGATIVES - mark the unit, render, the
    button is gone - because that is the printed TARGET line and nothing else
    measures it at the panel.

Section 0 proves each render produced a panel at all: a draw that fell into
another _draw_dispatch branch draws ZERO buttons and satisfies every absence
check by inspecting nothing. Section 3 proves the buttons appear because the
detachment gate opened rather than because the panel draws them regardless.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import ast                                                           # noqa: E402
import io                                                            # noqa: E402

import pygame                                                        # noqa: E402

import testkit as tk                                                 # noqa: E402
from testkit import Checks, settings_as                              # noqa: E402
from game import config                                              # noqa: E402
from game import rules_text                                          # noqa: E402
from game.command_points import CommandPointManager                  # noqa: E402
from game.decision import DecisionManager                            # noqa: E402
from game.dice import DiceManager                                    # noqa: E402
from game.movement import MovementController                         # noqa: E402
from game.shooting import ShootingController                         # noqa: E402
from game.stratagems import StratagemController                      # noqa: E402
from game.turn import (PHASES, PHASE_CHARGE, PHASE_COMMAND,          # noqa: E402
                       PHASE_FIGHT, PHASE_MOVEMENT, PHASE_SHOOTING,
                       TurnTracker)
from game.ui.action_panel import ActionPanel                         # noqa: E402

from game import protocol_conquering_tyrant as tyrant                # noqa: E402
from game import protocol_hungry_void as void                        # noqa: E402
from game import protocol_sudden_storm as storm                      # noqa: E402

from game.factions.necrons import IMMORTALS, NECRON_WARRIORS         # noqa: E402
from game.factions.orks import BOYZ                                  # noqa: E402

c = Checks("Necron Stratagem buttons")

pygame.init()
pygame.display.set_mode((1200, 900))

HUMAN = "Player 1"
FOE = "Player 2"

# Battle round 2: none of the three prints a round clause, so any round would
# do - chosen rather than defaulted so a tracker built at round 0 cannot make a
# future round clause absent for a reason that has nothing to do with the panel.
ROUND = 2

DETACH = dict(AWAKENED_DYNASTY_PLAYERS=(HUMAN,))


def turn_at(phase, owner=HUMAN, active=None):
    tracker = TurnTracker(first_player=owner)
    tracker.phase_index = PHASES.index(phase)
    tracker.turn_owner = owner
    tracker.active_player = active or owner
    tracker.battle_round = ROUND
    return tracker


def strat(cp=10):
    pool = CommandPointManager()
    for player in pool.cp:
        pool.cp[player] = cp
    return StratagemController(command_points=pool, game_log=tk.Log())


# ------------------------------------------------------------------- the board
# REBUILT PER SECTION, and that is not tidiness: buying one of these APPLIES it
# and leaves a mark on the squad (hungry_void_active and its two neighbours),
# and is_active(squad) is the FIRST refusal in every can_use(). A section that
# clicks therefore poisons every later section that renders the same squad -
# which surfaces as "the button is gone" somewhere with nothing to do with the
# click.

B = {}
ALL_TOKENS = []


def build_board():
    """A fresh board. ALL_TOKENS is mutated IN PLACE, because controllers and
    stubs are handed the list itself and have to keep seeing the live one.

    The foe sits 6" away: far enough to be outside Engagement Range, close
    enough that nothing here is refused for a distance reason a Stratagem's
    WHEN never mentions.
    """
    B.clear()
    B["warriors"] = tk.line_up(tk.build(NECRON_WARRIORS, HUMAN,
                                        name="1 Necron Warriors 1"),
                               10.0, 20.0, spacing=1.3)
    B["immortals"] = tk.line_up(tk.build(IMMORTALS, HUMAN, name="1 Immortals 1"),
                                18.0, 20.0, spacing=1.3)
    B["foe"] = tk.line_up(tk.build(BOYZ, FOE, name="2 Boyz 1"), 26.0, 20.0,
                          spacing=1.3)
    ALL_TOKENS[:] = [m for s in B.values() for m in s.models]
    return B


build_board()


class _FightStub:
    """FightController as HungryVoidController asks it: one question.

    `fought_squad_ids` holds SQUADS despite the name - game/fight.py adds the
    squad - and that is the ledger the printed TARGET line turns on.
    """

    def __init__(self):
        self.fought_squad_ids = set()


class _ShootStub:
    """ShootingController as ConqueringTyrantController asks it. The panel is
    still handed a REAL one; this is only what the controller reads."""

    def __init__(self):
        self.shot_squad_ids = set()


# ------------------------------------------------------------- the render rig

_panel = ActionPanel()
_surface = pygame.Surface((config.LEFT_PANEL_WIDTH, 900))
_rect = pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, 900)
_labels = []
_drawn = []          # (label, rect) in draw order
_real_button = ActionPanel._draw_button


def _spy_button(self, surface, rect, label, *a, **kw):
    out = _real_button(self, surface, rect, label, *a, **kw)
    _labels.append(label)
    _drawn.append((label, out))
    return out


ActionPanel._draw_button = _spy_button

_reached = []
_real_movement_ui = ActionPanel._draw_movement_ui


def _spy_movement_ui(self, *a, **kw):
    _reached.append(True)
    return _real_movement_ui(self, *a, **kw)


ActionPanel._draw_movement_ui = _spy_movement_ui


def controllers(sc=None, fight=None, shoot=None, tracker=None):
    """One of each, sharing a StratagemController so rule 15.01 binds them the
    way it does in a real game."""
    sc = sc if sc is not None else strat()
    return {
        void.HUNGRY_VOID_NAME: void.HungryVoidController(
            sc, fight_controller=fight if fight is not None else _FightStub(),
            turn_tracker=tracker, game_log=tk.Log()),
        storm.SUDDEN_STORM_NAME: storm.SuddenStormController(
            sc, turn_tracker=tracker, game_log=tk.Log(),
            dice_manager=DiceManager(), decision_manager=DecisionManager()),
        tyrant.CONQUERING_TYRANT_NAME: tyrant.ConqueringTyrantController(
            sc, shooting_controller=shoot if shoot is not None else _ShootStub(),
            turn_tracker=tracker, game_log=tk.Log()),
    }


def render(squad, phase, built, owner=HUMAN, active=None):
    """Draw the real panel for `squad` in `phase` and report what came out.

    Returns (labels, stratagem_names, buttons).

    mover.select() is not optional: _draw_movement_ui() opens with
    `movement_controller.selected_squad` and draws the no-selection screen
    without one, so every absence check would pass by measuring nothing.

    The three arrive as their OWN keyword arguments - they predate
    game/proactive_stratagems.py and none of them defines panel_label() - which
    is the second panel path this file exists to cover.
    """
    tracker = turn_at(phase, owner, active)
    for ctrl in built.values():
        if ctrl is not None:            # the None-handed-over render below
            ctrl.turn_tracker = tracker
    mover = MovementController([], tk.Log(), owner, DiceManager(), tracker,
                               ALL_TOKENS)
    # BY KEYWORD: ShootingController's first positional is `obstacles`, not the
    # token list, so a positional call quietly hands it the models as terrain.
    shooter = ShootingController(obstacles=[], game_log=tk.Log(),
                                 player_name=owner, dice_manager=DiceManager(),
                                 turn_tracker=tracker, all_tokens=ALL_TOKENS,
                                 decision_manager=DecisionManager())
    _labels.clear()
    _drawn.clear()
    _reached.clear()
    _surface.fill((0, 0, 0))
    mover.select(squad.models[0])
    _panel.draw(_surface, _rect, mover, shooter,
                dice_manager=DiceManager(),
                hungry_void_controller=built[void.HUNGRY_VOID_NAME],
                sudden_storm_controller=built[storm.SUDDEN_STORM_NAME],
                conquering_tyrant_controller=built[tyrant.CONQUERING_TYRANT_NAME])
    return (list(_labels), [n for _, n in _panel._stratagem_buttons],
            list(_panel._buttons))


def press(name, buttons):
    """Click the drawn button; True if there was one.

    RETURNS rather than raises when there is none - a probe that removes the
    buttons has to turn this file RED, not crash it.
    """
    rect = next((r for r, n in _panel._stratagem_buttons if n == name), None)
    if rect is None:
        return False
    callback = next((cb for r, cb in buttons if r == rect), None)
    if callback is None:
        return False
    callback()
    return True


# The panel drops "Protocol of the" from every one of these - a bigger
# shortening than the Arro'kon Protocol's leading "The", and section 5 pins
# that rules_text still resolves the printed rule from what is DRAWN.
DRAWN_NAMES = {
    void.HUNGRY_VOID_NAME: "Hungry Void",
    storm.SUDDEN_STORM_NAME: "Sudden Storm",
    tyrant.CONQUERING_TYRANT_NAME: "Conquering Tyrant",
}

# TRANSCRIBED from rules/necrons/detachments/Awakened Dynasty.md, deliberately
# not imported: the suite and the modules are then two independent statements
# of one table, and a table that moved would have to move in both.
#
# `owner` says whether the printed WHEN says "Your". Hungry Void's does not.
WHEN = {
    void.HUNGRY_VOID_NAME: (frozenset({PHASE_FIGHT}), False),
    storm.SUDDEN_STORM_NAME: (frozenset({PHASE_MOVEMENT}), True),
    tyrant.CONQUERING_TYRANT_NAME: (frozenset({PHASE_SHOOTING}), True),
}


# ==========================================================================
print("=== 0. the render really produced a panel ===")
# ==========================================================================

# Without this every negative below could pass by inspecting nothing: a draw
# that fell into another _draw_dispatch branch draws ZERO buttons.
_built = controllers()
for _phase in PHASES:
    labels, _names, _buttons = render(B["warriors"], _phase, _built)
    # THE DISPATCH BRANCH, not the button count. Measured: in Command, Charge
    # and Fight the panel draws no buttons at all without a charge/fight
    # controller, so a button count would either be false or force this rig to
    # build half the game. What every absence check below depends on is that
    # the draw reached _draw_movement_ui() - the branch all three live in.
    c.true("%s: the render reached the unit screen" % _phase, bool(_reached))

# ...and where the panel does draw buttons, it really drew them.
labels, _n, _b = render(B["warriors"], PHASE_MOVEMENT, _built)
c.true("the movement screen drew Move", any(lab.startswith("Move") for lab in labels))
c.true("...and the shooting screen drew something",
       len(render(B["warriors"], PHASE_SHOOTING, _built)[0]) > 0)

# Every drawn Stratagem button is INSIDE the panel. Hungry Void's sits below
# the Fight button while the other two sit near the top, so a column that
# overran the panel height would drop Hungry Void alone.
build_board()
with settings_as(**DETACH):
    _built = controllers()
    render(B["warriors"], PHASE_FIGHT, _built)
    _rects = [r for r, _n in _panel._stratagem_buttons]
    c.true("...and there WAS a Stratagem button to measure", len(_rects) > 0)
    c.true("...and it is inside the panel",
           all(_rect.contains(r) for r in _rects) if _rects else False)


# ==========================================================================
print("=== 1. the bespoke keyword path draws and pays ===")
# ==========================================================================

build_board()
with settings_as(**DETACH):
    _built = controllers()
    _labels_f, names, buttons = render(B["warriors"], PHASE_FIGHT, _built)
    c.true("Hungry Void is drawn", DRAWN_NAMES[void.HUNGRY_VOID_NAME] in names)

    # None handed over draws nothing at all - the panel's own `is not None`
    # guard, which is what makes a missing keyword argument silent.
    _labels_n, names_none, _b = render(
        B["warriors"], PHASE_FIGHT,
        {void.HUNGRY_VOID_NAME: None, storm.SUDDEN_STORM_NAME: None,
         tyrant.CONQUERING_TYRANT_NAME: None})
    c.eq("...and a controller handed over as None draws nothing", names_none, [])
    c.true("...while the panel itself still reached the unit screen", bool(_reached))


# ==========================================================================
print("=== 2. the phase matrix: 3 Stratagems x 5 phases ===")
# ==========================================================================

with settings_as(**DETACH):
    for name, (phases, _owner_clause) in WHEN.items():
        for phase in PHASES:
            build_board()
            built = controllers()
            _l, names, _b = render(B["warriors"], phase, built)
            drawn = DRAWN_NAMES[name] in names
            want = phase in phases
            c.eq("%s in %s" % (DRAWN_NAMES[name], phase), drawn, want)


# ==========================================================================
print("=== 2b. Hungry Void has no owner clause - and it shows at the panel ===")
# ==========================================================================

# Printed: "WHEN: Fight phase." - no "Your". Both players fight in the Fight
# phase (12.02/12.04), and MovementController.can_select() returns True
# unconditionally there, so this is measurable at the REAL panel with the turn
# flipped. Neither the Aeldari nor the T'au matrix could do that.

with settings_as(**DETACH):
    build_board()
    built = controllers()
    _l, names, _b = render(B["warriors"], PHASE_FIGHT, built, owner=FOE)
    c.true("Hungry Void is offered in the OPPONENT's Fight phase too",
           DRAWN_NAMES[void.HUNGRY_VOID_NAME] in names)

    # The counter-proof: the two that DO print "Your" are absent there, so this
    # section is not simply measuring a panel that draws everything.
    build_board()
    built = controllers()
    _l, names, _b = render(B["warriors"], PHASE_MOVEMENT, built, owner=FOE)
    c.eq("Sudden Storm is NOT offered in the opponent's Movement phase",
         DRAWN_NAMES[storm.SUDDEN_STORM_NAME] in names, False)
    build_board()
    built = controllers()
    _l, names, _b = render(B["warriors"], PHASE_SHOOTING, built, owner=FOE)
    c.eq("Conquering Tyrant is NOT offered in the opponent's Shooting phase",
         DRAWN_NAMES[tyrant.CONQUERING_TYRANT_NAME] in names, False)

    # ...and the same three statements at can_use(), independently of the panel.
    for name, (_phases, owner_clause) in WHEN.items():
        phase = list(WHEN[name][0])[0]
        build_board()
        built = controllers(tracker=turn_at(phase, FOE))
        c.eq("%s refuses a foreign turn: %s" % (DRAWN_NAMES[name], owner_clause),
             not built[name].can_use(B["warriors"]), owner_clause)


# ==========================================================================
print("=== 3. the detachment gate, AT THE PANEL ===")
# ==========================================================================

# Without this section 2 proves only that buttons appear, not that they appear
# BECAUSE the detachment is fielded.
with settings_as(AWAKENED_DYNASTY_PLAYERS=()):
    for phase in PHASES:
        build_board()
        built = controllers()
        _l, names, _b = render(B["warriors"], phase, built)
        c.eq("no detachment, no Necron Stratagem in %s" % phase,
             [n for n in names if n in DRAWN_NAMES.values()], [])


# ==========================================================================
print("=== 4. the printed TARGET ledgers, as negatives ===")
# ==========================================================================

# "a unit that has not already fought / shot". Nothing else measures these at
# the panel, and they are the half of the printed TARGET line a phase matrix
# cannot see.
with settings_as(**DETACH):
    build_board()
    fight = _FightStub()
    built = controllers(fight=fight)
    _l, names, _b = render(B["warriors"], PHASE_FIGHT, built)
    c.true("Hungry Void before the unit fights",
           DRAWN_NAMES[void.HUNGRY_VOID_NAME] in names)
    fight.fought_squad_ids.add(B["warriors"])
    _l, names, _b = render(B["warriors"], PHASE_FIGHT, built)
    c.eq("...and gone once it has fought",
         DRAWN_NAMES[void.HUNGRY_VOID_NAME] in names, False)

    build_board()
    shoot = _ShootStub()
    built = controllers(shoot=shoot)
    _l, names, _b = render(B["warriors"], PHASE_SHOOTING, built)
    c.true("Conquering Tyrant before the unit shoots",
           DRAWN_NAMES[tyrant.CONQUERING_TYRANT_NAME] in names)
    shoot.shot_squad_ids.add(B["warriors"])
    _l, names, _b = render(B["warriors"], PHASE_SHOOTING, built)
    c.eq("...and gone once it has shot",
         DRAWN_NAMES[tyrant.CONQUERING_TYRANT_NAME] in names, False)


# ==========================================================================
print("=== 5. the click really pays, and rule 15.01 binds ===")
# ==========================================================================

with settings_as(**DETACH):
    for name, (phases, _oc) in WHEN.items():
        phase = list(phases)[0]
        build_board()
        sc = strat(cp=10)
        built = controllers(sc=sc)

        # THE 15.01 RESET CHECK COMES FIRST. After a purchase can_use() refuses
        # for 15.01's own reason, so a reset check placed afterwards is masked
        # by the very rule it is trying to measure.
        c.true("%s: available before any purchase" % DRAWN_NAMES[name],
               built[name].can_use(B["warriors"]))

        _l, _n, buttons = render(B["warriors"], phase, built)
        before = sc.command_points.cp[HUMAN]
        c.true("%s: the drawn button was pressed" % DRAWN_NAMES[name],
               press(DRAWN_NAMES[name], buttons))
        after = sc.command_points.cp[HUMAN]
        c.eq("%s: it really spent its CP" % DRAWN_NAMES[name], before - after, 1)

        # ...and 15.01: not twice in the same phase, even on another unit.
        c.eq("%s: not a second time this phase" % DRAWN_NAMES[name],
             built[name].can_use(B["immortals"]), False)

        # The button is gone from the panel too, not merely refused underneath.
        _l, names, _b = render(B["warriors"], phase, built)
        c.eq("%s: and the button is gone" % DRAWN_NAMES[name],
             DRAWN_NAMES[name] in names, False)


# ==========================================================================
print("=== 6. what the corpus prints, and what the panel draws ===")
# ==========================================================================

_CORPUS = rules_text.detachment_stratagems("NECRONS", "Awakened Dynasty")
_by_name = {s.name: s for s in _CORPUS}
c.true("the printed detachment was read", len(_CORPUS) >= 6)

for name, drawn in DRAWN_NAMES.items():
    # The full printed heading is upper-case in the corpus; the module's name
    # constant is the title-case form.
    c.true("%s is a printed Stratagem" % name,
           any(name.lower() == s.name.lower() for s in _CORPUS))
    # ...and the SHORTENED name the panel draws still finds the printed rule,
    # through rules_text's unique-suffix fallback. Both halves, so a rename
    # that breaks the fallback shows up here instead of as an empty tooltip.
    # A LIST of detachments - detachment_stratagems() above takes a single
    # name and stratagem_named() takes the armys whole list, and passing a
    # bare string to the second silently finds nothing.
    found = rules_text.stratagem_named("NECRONS", ["Awakened Dynasty"], drawn)
    c.true("...and the DRAWN name '%s' still resolves it" % drawn, found is not None)
    c.true("...to the right one",
           found is not None and name.lower() == found.name.lower())

c.true("the panel really does shorten the name",
       all(drawn != full for full, drawn in DRAWN_NAMES.items()))


# ==========================================================================
print("=== 7. the bespoke chain, by AST ===")
# ==========================================================================

PANEL_SRC = io.open(os.path.join("game", "ui", "action_panel.py"),
                    encoding="utf-8").read()
MAIN_SRC = io.open("main.py", encoding="utf-8").read()
PANEL_TREE = ast.parse(PANEL_SRC)
MAIN_TREE = ast.parse(MAIN_SRC)

PARAMS = ("hungry_void_controller", "sudden_storm_controller",
          "conquering_tyrant_controller")
STAGES = ("draw", "_draw_dispatch", "_draw_movement_ui")


def _fn(tree, name):
    return next((n for n in ast.walk(tree)
                 if isinstance(n, ast.FunctionDef) and n.name == name), None)


# (a) all THREE signatures carry all three names. action_panel.py's own comment
# records the failure this catches: "added to draw() and _draw_movement_ui()
# and forwarded through both, but not to THIS signature - the three-stage chain
# half-wired, which crashes every frame".
for stage in STAGES:
    node = _fn(PANEL_TREE, stage)
    c.true("%s() exists" % stage, node is not None)
    names = {a.arg for a in (node.args.args + node.args.kwonlyargs)} if node else set()
    for param in PARAMS:
        c.true("%s() takes %s" % (stage, param), param in names)

# (b) both forwarding hops pass it BY KEYWORD, with a matching name. A
# substring `hungry_void_controller=hungry_void_controller` cannot tell the two
# hops apart, and matches a comment - which is all the standing proof was.
for outer, inner in (("draw", "_draw_dispatch"), ("_draw_dispatch", "_draw_movement_ui")):
    node = _fn(PANEL_TREE, outer)
    forwarded = set()
    for sub in ast.walk(node) if node else []:
        if not isinstance(sub, ast.Call):
            continue
        func = sub.func
        if not (isinstance(func, ast.Attribute) and func.attr == inner):
            continue
        for kw in sub.keywords:
            if (kw.arg in PARAMS and isinstance(kw.value, ast.Name)
                    and kw.value.id == kw.arg):
                forwarded.add(kw.arg)
    for param in PARAMS:
        c.true("%s -> %s forwards %s by keyword" % (outer, inner, param),
               param in forwarded)

# (c) main.py's POSITIONAL prefix still lines up with draw()'s signature. The
# three arrive by keyword, so an index pin would be vacuous; what actually
# protects them is that nothing was inserted mid-signature.
_draw_call = None
for node in ast.walk(MAIN_TREE):
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "draw"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "action_panel"):
        _draw_call = node
c.true("main.py's action_panel.draw() call was found", _draw_call is not None)

if _draw_call is not None:
    positional = [a.id for a in _draw_call.args if isinstance(a, ast.Name)]
    sig = _fn(PANEL_TREE, "draw")
    sig_names = [a.arg for a in sig.args.args][1:]      # drop self
    c.true("...and every positional argument is a plain name",
           len(positional) == len(_draw_call.args))
    # FROM INDEX 2: main.py's first two locals are `screen` and
    # `left_panel_rect` where the parameters are `surface` and `rect`, so those
    # two carry no information. Everything after them follows the convention
    # that the local is named for the parameter, which is what makes a
    # parameter inserted mid-signature visible here at all.
    c.true("...and enough positionals to be worth comparing", len(positional) > 4)
    c.eq("...and the positional tail matches draw()'s own signature",
         positional[2:], sig_names[2:len(positional)])
    passed = {kw.arg for kw in _draw_call.keywords}
    for param in PARAMS:
        c.true("main.py hands over %s by keyword" % param, param in passed)

# (d) THE STANDING DECISION, pinned: these three are NOT on the registry, and
# defining panel_label() would put them there. If a later session migrates
# them, this moves - deliberately, because section 14 of the wiring guard would
# then cover them and this file's chain checks would become the wrong shape.
for module, klass in (("protocol_hungry_void", "HungryVoidController"),
                      ("protocol_sudden_storm", "SuddenStormController"),
                      ("protocol_conquering_tyrant", "ConqueringTyrantController")):
    src = io.open(os.path.join("game", module + ".py"), encoding="utf-8").read()
    c.eq("%s defines no panel_label() - the bespoke path" % module,
         "def panel_label" in src, False)

_registered = set()
for node in ast.walk(MAIN_TREE):
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "proactive_stratagems"):
        for arg in node.args:
            inner = arg.func if isinstance(arg, ast.Call) else arg
            if isinstance(inner, ast.Name):
                _registered.add(inner.id)
c.true("the registry sweep is live - it found the other Stratagems",
       len(_registered) > 10)
for klass in ("HungryVoidController", "SuddenStormController",
              "ConqueringTyrantController"):
    c.eq("%s is not on the registry" % klass, klass in _registered, False)

c.finish()
