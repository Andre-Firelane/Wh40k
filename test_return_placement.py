"""A returning model is SET UP - so a human sets it up.

User: "wenn ein Mensch zb. necrons spielt, muss er die stratagems,
Faehigkeiten und Platzierung der Modelle manuell ganz normal steuern koennen."

Rule 01.02.03 says a model put back on the battlefield is set up, and setting
up is the controlling player's job. Eight abilities in this engine return
models and all eight picked the spot themselves, for both sides. The spot was
never illegal - formation_layout seats it in coherency by construction - it was
just never anybody's choice.

TWO HALVES, and either alone is a regression:

  * the AI must land on exactly the spots it landed on before, in the same
    frame, with nothing opened. Otherwise every AI measurement in this repo
    stops being comparable, and a prompt the AI cannot answer costs an API call.
  * a human must get an ordinary Set Up - drag, Confirm, Cancel - over the
    RETURNING models only, with the survivors left standing.

WHY IT RIDES SetupController RATHER THAN A NEW PENDING STATE. A new state that
main() blocks on has to be clickable AND drawn, or it is a hard deadlock
(Fehlerklasse 25, which cost this repo a game-stopping bug). PLACING is already
blocked on, routed, painted and has Confirm/Cancel. The price is that
SetupController had to learn to place a SUBSET of a unit, and the three traps
in doing so are what section 2 is about.
"""

import os
import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import testkit as tk
from testkit import Checks, GameState

from game import config, reanimation_protocols as rp, setup as setup_mod
from game.return_placement import ReturnPlacementController
from game.setup import SetupController
from game.factions.necrons import NECRON_WARRIORS

c = Checks("returning models are placed")

HUMAN, AI = "Player 1", "Player 2"


def scene(owner, dead=2):
    """A Necron unit standing on the board with `dead` models to recover."""
    state = GameState()
    squad = tk.build(NECRON_WARRIORS, owner, name=f"{owner[-1]} Necron Warriors 1")
    tk.line_up(squad, x=20.0, y=20.0)
    state.tokens.extend(squad.models)
    for model in squad.models[:dead]:
        model.current_wounds = 0
    state.remove_dead_models()
    setup = SetupController(state, all_tokens=state.tokens,
                            board_width_in=60.0, board_height_in=44.0)
    placer = ReturnPlacementController(setup_controller=setup, game_state=state,
                                       auto_players=(AI,))
    return state, squad, setup, placer


# --------------------------------------------------------------------------
# 1. The fork
# --------------------------------------------------------------------------
print("=== 1. the AI lands, the human places ===")

state, squad, setup, placer = scene(AI)
before = len(squad.models)
spent, revived = rp.reanimate(squad, 3, all_tokens=state.tokens,
                              game_state=state, placer=placer)
c.true(f"the AI got its models back ({len(revived)})", len(revived) > 0)
c.eq("...in the same frame, with no placement opened", setup.state, setup_mod.IDLE)
c.eq("...and nothing pending", placer.is_busy, False)
c.true("...and they are on the board", all(m in state.tokens for m in revived))
c.eq("...standing in the squad", len(squad.models), before + len(revived))

state, squad, setup, placer = scene(HUMAN)
before = len(squad.models)
spent, revived = rp.reanimate(squad, 3, all_tokens=state.tokens,
                              game_state=state, placer=placer)
c.true(f"a human got the same models back ({len(revived)})", len(revived) > 0)
c.eq("...but a placement is OPEN so they can be positioned", setup.state, setup_mod.PLACING)
c.eq("...on the right unit", setup.setting_up_squad is squad, True)
c.true("...and the controller knows it is waiting", placer.is_busy)

# THE SUBSET, which is the whole reason SetupController had to change.
c.eq("only the RETURNING models are being placed",
     sorted(m.id for m in setup.placing_models), sorted(m.id for m in revived))
c.true("...not the survivors", len(setup.placing_models) < len(squad.models))
c.true("...and the placement knows it is partial", setup.is_partial)


# --------------------------------------------------------------------------
# 2. The three traps in placing a subset
# --------------------------------------------------------------------------
print("\n=== 2. the survivors are not part of it ===")

survivor = next(m for m in squad.models if m not in revived)
returner = revived[0]

# (a) a survivor cannot be dragged
c.eq("a survivor is not draggable", setup.is_placeable(survivor), False)
c.eq("...a returning model is", setup.is_placeable(returner), True)

# (b) the overlap exemption. A survivor standing still must be AVOIDED, or
# confirm_setup()'s whole-squad check_model_overlap() rejects at the end what
# the drag allowed all along - Fehlerklasse 8, which has cost a whole unit.
c.eq("a returning model may not be dropped on top of a survivor",
     setup.position_valid(returner, survivor.x_in, survivor.y_in, squad=squad), False)

# (c) rule 18.02. The unit was not set up, it got a model back.
squad.set_up_this_turn = False
setup.confirm_setup()
c.eq("confirming a return does NOT mark the unit as set up this turn",
     getattr(squad, "set_up_this_turn", False), False)
c.eq("...and the placement is over", setup.state, setup_mod.IDLE)

# ...while an ordinary Set Up still does mark it, which is what makes the
# check above a distinction rather than a deletion.
state2, squad2, setup2, _placer2 = scene(HUMAN, dead=0)
for model in squad2.models:
    if model in state2.tokens:
        state2.tokens.remove(model)
setup2.start_setup(squad2, 30.0, 30.0, on_cancel=lambda s: None)
setup2.arrange_as_block(30.0, 30.0)
setup2.confirm_setup()
c.eq("an ordinary Set Up still marks it", getattr(squad2, "set_up_this_turn", False), True)


# --------------------------------------------------------------------------
# 3. Confirm and Cancel
# --------------------------------------------------------------------------
print("\n=== 3. both ways out ===")

state, squad, setup, placer = scene(HUMAN)
standing = len(squad.models)
_spent, revived = rp.reanimate(squad, 3, all_tokens=state.tokens,
                               game_state=state, placer=placer)
done = []
placer._pending = (squad, list(revived), done.append)
c.eq("confirming ends the placement", placer.confirm(), True)
c.eq("...and the models stay", len(squad.models), standing + len(revived))
c.eq("...and the ability is told", len(done), 1)

# CANCEL puts them back down. A return that is not placed did not happen -
# which is how all eight abilities already read "nowhere legal to stand".
state, squad, setup, placer = scene(HUMAN)
standing = len(squad.models)
dead_before = len(squad.destroyed_models)
_spent, revived = rp.reanimate(squad, 3, all_tokens=state.tokens,
                               game_state=state, placer=placer)
c.eq("cancelling ends the placement", placer.cancel(), True)
c.eq("...the unit is back to its survivors", len(squad.models), standing)
c.eq("...the models are destroyed again", len(squad.destroyed_models), dead_before)
c.true("...and off the board", all(m not in state.tokens for m in revived))
c.eq("...with nothing pending", placer.is_busy, False)
c.eq("...and the placement closed", setup.state, setup_mod.IDLE)


# --------------------------------------------------------------------------
# 4. A model with nowhere to stand is not offered
# --------------------------------------------------------------------------
print("\n=== 4. nowhere legal stays down ===")

state, squad, setup, placer = scene(HUMAN)
returned = placer.place(squad, [squad.destroyed_models[0]], [None])
c.eq("a model with no spot is not returned", returned, [])
c.eq("...and no placement is opened for it", setup.state, setup_mod.IDLE)
c.eq("...nor anything left pending", placer.is_busy, False)


# --------------------------------------------------------------------------
# 5. Wiring - blocked on, resolvable, drawn
# --------------------------------------------------------------------------
print("\n=== 5. it cannot deadlock ===")

import pathlib  # noqa: E402

ROOT = pathlib.Path(r"c:\Users\Andre\Desktop\WH40")
MAIN_SRC = (ROOT / "main.py").read_text(encoding="utf-8")
PANEL_SRC = (ROOT / "game" / "ui" / "action_panel.py").read_text(encoding="utf-8")

# It rides PLACING, so it inherits all three - which is the reason it rides
# PLACING. Checked anyway, because "it inherits it" is only true while the
# branch it inherits from still exists.
c.true("main.py blocks the phase on a placement",
       "or setup_controller.state == setup.PLACING" in MAIN_SRC)
c.true("...routes clicks to it", "setup_controller.state == setup.PLACING" in MAIN_SRC)
c.true("...and paints the legality overlay for it",
       "renderer.draw_placement_overlay(" in MAIN_SRC)

# The panel must be able to RESOLVE it, or the placement is a deadlock with a
# nicer title.
c.true("the panel routes Confirm to the return controller",
       "confirm_callback = return_placement_controller.confirm" in PANEL_SRC)
c.true("...and Cancel", "cancel_callback = return_placement_controller.cancel" in PANEL_SRC)
c.true("...and names it", '"Returning Models" if is_return' in PANEL_SRC)

# The whole four-stage chain, which this file has a scar from: a parameter
# added to some stages and not others crashes every frame.
import ast  # noqa: E402

for name in ("draw", "_draw_dispatch", "_draw_pregame_ui", "_draw_pregame_deploying",
             "_draw_setup_ui"):
    node = next(n for n in ast.walk(ast.parse(PANEL_SRC))
                if isinstance(n, ast.FunctionDef) and n.name == name)
    params = {a.arg for a in node.args.args + node.args.kwonlyargs}
    c.true(f"{name}() takes return_placement_controller",
           "return_placement_controller" in params)

# ...and no stage USES it without declaring it, which is how the half-wired
# version of this crashed.
unbound = []
for node in ast.walk(ast.parse(PANEL_SRC)):
    if isinstance(node, ast.FunctionDef):
        params = {a.arg for a in node.args.args + node.args.kwonlyargs}
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Name) and sub.id == "return_placement_controller"
                    and "return_placement_controller" not in params):
                unbound.append(f"{node.name}:{sub.lineno}")
c.eq("no stage reads it without taking it", sorted(unbound), [])

# Construction order (Fehlerklasse 23): the placer needs setup_controller,
# which is built ~600 lines after the ability that uses it.
c.true("the placer is built after the setup controller",
       MAIN_SRC.index("setup_controller = SetupController(")
       < MAIN_SRC.index("return_placement_controller = ReturnPlacementController("))
c.true("...and assigned onto the ability afterwards",
       MAIN_SRC.index("return_placement_controller = ReturnPlacementController(")
       < MAIN_SRC.index("reanimation_controller.placer = return_placement_controller"))

# The overlay must paint for a model that is actually being placed.
c.true("the placement overlay follows the subset",
       "setup_controller.placing_models" in MAIN_SRC)


# --------------------------------------------------------------------------
# 6. Which abilities are routed, and which are named as not
# --------------------------------------------------------------------------
print("=== 6. the eight abilities ===")

import ast  # noqa: F811  (already imported above; kept local to this block)

# Eight abilities put a model back. FOUR are routed through the placer; the
# other four are named here with their reason, so "not done" is a decision on
# the record rather than an omission - and so adding the fifth is a visible
# one-line change.
ROUTED = {
    "reanimation_protocols": "reanimation_controller.placer",
    "grot_orderly": "grot_orderly_controller.placer",
    "unquenchable_resolve": "unquenchable_resolve_controller.placer",
    "curse_of_the_walking_pox": "placer=return_placement_controller",
}
for module, wiring in sorted(ROUTED.items()):
    src = (ROOT / "game" / f"{module}.py").read_text(encoding="utf-8")
    c.true(f"{module} takes a placer", "placer=None" in src)
    c.true(f"...and consults it", "self.placer is not None" in src
           or "placer=self.placer" in src or "placer=placer" in src)
    c.true(f"...and main.py hands it one", wiring in MAIN_SRC)

# The four that are NOT routed, each for a stated reason. Checked as "still
# places for itself", so wiring one up makes this list shrink rather than
# leaving a stale claim behind.
NOT_ROUTED = {
    "spiritseer": "TearsOfIsha.resolve() has no caller - unreachable for both "
                  "sides, so routing it is speculative work behind a dead path",
    "protocol_eternal_revenant": "returns a CHARACTER into a unit of one, where "
                                 "there are no survivors to stand in coherency with",
    "enh_phoenix_gem": "same single-model ring return as the Revenant",
    "word_of_the_phoenix": "returns up to D3+1 at once behind two dice rolls; "
                           "its own offer landed first and the placement half "
                           "is the next step",
}
for module in sorted(NOT_ROUTED):
    src = (ROOT / "game" / f"{module}.py").read_text(encoding="utf-8")
    c.true(f"{module} still places for itself ({NOT_ROUTED[module][:40]}...)",
           "model_return.set_up_model(" in src or "set_up_model(" in src)

# --------------------------------------------------------------------------
# 7. Every DOOR into reanimate(), not just the ability that owns it
# --------------------------------------------------------------------------
print("=== 7. the doors into reanimate() ===")

# User: "Einheiten wurde automatisch platziert bei protocol of the undying
# legion, obwohl ich necrons spiele."
#
# Section 6 asks which ABILITIES are routed, and it answered "reanimation
# protocols is" - true of the army rule's own controller, and blind to the
# fact that TWO OTHER MODULES call the same reanimate() directly. Both placed
# a human's models for them (measured before the fix: the models came back and
# setup.state stayed IDLE). Fehlerklasse 9 in plain form: the funnel is not
# always the one that looks like it, so count the callers.
#
# A behaviour test cannot see the FOURTH door, because it does not exist yet.
# So this is a SET DIFFERENCE at the source: every call to reanimate() outside
# its own module must pass a placer, and main.py must hand that module one.
GAME = ROOT / "game"


def call_sites(func_name, exclude):
    """Every Call node named `func_name` in game/, with the module it is in."""
    found = []
    for path in sorted(GAME.rglob("*.py")):
        if path.name in exclude:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
            if name == func_name:
                found.append((path.stem, node))
    return found


doors = call_sites("reanimate", exclude={"reanimation_protocols.py"})
c.true("reanimate() has more than one door (%d: %s)"
       % (len(doors), sorted(m for m, _ in doors)), len(doors) >= 2)
c.true("...and the army rule's own controller is not among them - it lives "
       "in the same module as the function",
       "reanimation_protocols" not in {m for m, _ in doors})

for module, node in sorted(doors, key=lambda pair: pair[0]):
    passes = any(kw.arg == "placer" for kw in node.keywords)
    c.true("%s hands reanimate() a placer (line %d)" % (module, node.lineno), passes)

# ...and every one of those modules must actually GET one from main.py.
#
# Checked as an AST CALL EXPRESSION, not as a substring. The obvious form -
# `"placer=return_placement_controller," in MAIN_SRC` - is already true because
# Curse of the Walking Pox passes it too, so it stays green with Undying
# Legions unwired. Its own A/B probe is what found that (Fehlerklasse 24).
MAIN_TREE = ast.parse(MAIN_SRC)


def controller_class_with_placer(module):
    """The class in game/<module>.py that holds a `self.placer`."""
    tree = ast.parse((GAME / (module + ".py")).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Attribute) and sub.attr == "placer"
                    and isinstance(sub.value, ast.Name) and sub.value.id == "self"):
                return node.name
    return None


def main_hands_a_placer(class_name):
    """True if main() gives that class a placer - either way round.

    Two shapes, because construction order in main() is real (Fehlerklasse 23):
    a constructor keyword for a controller built AFTER the placer, and an
    attribute assignment for one built before it.
    """
    for node in ast.walk(MAIN_TREE):
        if (isinstance(node, ast.Call)
                and getattr(node.func, "id", None) == class_name
                and any(kw.arg == "placer" for kw in node.keywords)):
            return True
    # ...or `<something>.placer = return_placement_controller`
    for node in ast.walk(MAIN_TREE):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if (isinstance(target, ast.Attribute) and target.attr == "placer"
                    and isinstance(node.value, ast.Name)
                    and node.value.id == "return_placement_controller"):
                # The name on the left must be the local this class was
                # assigned to, or any assignment anywhere would satisfy any
                # class - which is the hole this whole block exists to close.
                local = getattr(target.value, "id", None)
                for other in ast.walk(MAIN_TREE):
                    if (isinstance(other, ast.Assign)
                            and isinstance(other.value, ast.Call)
                            and getattr(other.value.func, "id", None) == class_name
                            and any(getattr(t, "id", None) == local
                                    for t in other.targets)):
                        return True
    return False


for module, _node in sorted(doors, key=lambda pair: pair[0]):
    class_name = controller_class_with_placer(module)
    c.true("%s has a controller that holds a placer (%s)" % (module, class_name),
           class_name is not None)
    if class_name:
        c.true("...and main.py hands %s one" % class_name,
               main_hands_a_placer(class_name))

# Construction order again, for the door that takes it as an argument: it is
# built AFTER the placer, so a constructor argument is the right shape - and
# main() is a 4000-line function where that is a real question.
c.true("Undying Legions is built after the placer",
       MAIN_SRC.index("return_placement_controller = ReturnPlacementController(")
       < MAIN_SRC.index("undying_legions_controller = UndyingLegionsController("))
c.true("...and the orb is built BEFORE it, hence the assignment",
       MAIN_SRC.index("resurrection_orb_controller = ResurrectionOrbController(")
       < MAIN_SRC.index("return_placement_controller = ReturnPlacementController("))


# --------------------------------------------------------------------------
# 8. Both extra doors, end to end, both sides
# --------------------------------------------------------------------------
print("=== 8. Undying Legions and the Resurrection Orb ===")

from game import attached_units, config as cfg  # noqa: E402
from game import protocol_undying_legions as ul_mod  # noqa: E402
from game import resurrection_orb as orb_mod  # noqa: E402
from game.command_points import CommandPointManager  # noqa: E402
from game.decision import DecisionManager  # noqa: E402
from game.dice import DiceManager  # noqa: E402
from game.factions import necrons as nec  # noqa: E402
from game.stratagems import StratagemController  # noqa: E402

# The human plays Necrons - that is the whole report - so the detachment has
# to be theirs too, or can_use() refuses for a reason that is not this one.
_SAVED_DYNASTY = getattr(cfg, "AWAKENED_DYNASTY_PLAYERS", ())
cfg.AWAKENED_DYNASTY_PLAYERS = (HUMAN, AI)


def block_up(squad, x=20.0, y=20.0, per_row=4, spacing=1.7):
    """A compact, LEGAL block - not tk.line_up().

    Two reasons, both measured. A ten-model line is 12in long, so it fails
    09.02's 9in spread the moment confirm_setup() looks at it, and the human
    half of this section is the only half that runs confirm_setup() at all.
    And 1.4in between a 40mm Overlord (r 0.787) and a 32mm Warrior (r 0.63) is
    an OVERLAP of the survivors - the returning models would then be refused
    for a collision that was already on the board before they came back.
    """
    for index, model in enumerate(squad.models):
        model.x_in = x + (index % per_row) * spacing
        model.y_in = y + (index // per_row) * spacing
    return squad


def necron_scene(owner, dead=2, with_orb=False):
    """A damaged Necron unit, its placer forked on auto_players."""
    state = GameState()
    squad = tk.build(NECRON_WARRIORS, owner, composition_index=0,
                     name="%s Necron Warriors 7" % owner[-1])
    if with_orb:
        lord = tk.build(nec.OVERLORD, owner, name="%s Overlord 7" % owner[-1],
                        choices={"Overlord": {nec.OVERLORD_TO_VOIDSCYTHE: 1}},
                        gear={"Overlord": [nec.OVERLORD_RESURRECTION_ORB]})
        squad = attached_units.attach(lord, squad, game_state=state)
    block_up(squad)
    state.tokens = list(squad.models)
    for model in squad.models[:dead]:
        model.current_wounds = 0
    state.remove_dead_models()
    setup = SetupController(state, all_tokens=state.tokens,
                            board_width_in=60.0, board_height_in=44.0)
    placer = ReturnPlacementController(setup_controller=setup, game_state=state,
                                       auto_players=(AI,))
    return state, squad, setup, placer


def fire_undying_legions(owner, dead=2):
    state, squad, setup, placer = necron_scene(owner, dead=dead)
    pool = CommandPointManager()
    for player in pool.cp:
        pool.cp[player] = 10
    dice, decisions = DiceManager(), DecisionManager()
    ctrl = ul_mod.UndyingLegionsController(
        StratagemController(command_points=pool, game_log=tk.Log()),
        dice_manager=dice, decision_manager=decisions, game_log=tk.Log(),
        game_state=state, auto_players=(AI,), placer=placer)
    tk.script(2, default=2)
    before = len(squad.models)
    ctrl.maybe_offer(squad)
    if decisions.is_pending:
        decisions.choose(0)          # the human says "Use"
    dice.acknowledge()
    ctrl.on_dice_acknowledged()
    return before, squad, setup, placer


def fire_orb(owner, dead=4):
    # FOUR dead, not two: the orb's AI gate is RESURRECTION_ORB_MIN_RECOVERABLE
    # (4) against Undying Legions' 2, so a two-model scene would measure the AI
    # declining rather than the AI placing.
    state, squad, setup, placer = necron_scene(owner, dead=dead, with_orb=True)
    decisions = DecisionManager()
    ctrl = orb_mod.ResurrectionOrbController(
        dice_manager=DiceManager(), decision_manager=decisions, game_log=tk.Log(),
        game_state=state, auto_players=(AI,), placer=placer)
    tk.script(4, default=4)
    before = len(squad.models)
    ctrl.offer_at_end_of_phase({squad}, owner)
    if decisions.is_pending:
        decisions.choose(0)
    ctrl.dice_manager.acknowledge()
    ctrl.on_dice_acknowledged()
    return before, squad, setup, placer


for label, fire in (("Undying Legions", fire_undying_legions),
                    ("the Resurrection Orb", fire_orb)):
    # The AI: unchanged, in the same frame, nothing opened.
    before, squad, setup, placer = fire(AI)
    c.true("the AI gets its models back from %s" % label, len(squad.models) > before)
    c.eq("...in the same frame (%s)" % label, setup.state, setup_mod.IDLE)
    c.eq("...with nothing pending (%s)" % label, placer.is_busy, False)

    # The human: same models, but they are theirs to place.
    before, squad, setup, placer = fire(HUMAN)
    c.true("a human gets the same models back from %s" % label, len(squad.models) > before)
    c.eq("...and a placement is OPEN (%s) - the reported bug" % label,
         setup.state, setup_mod.PLACING)
    c.eq("...on the right unit (%s)" % label, setup.setting_up_squad is squad, True)
    c.true("...over the returning models only (%s)" % label, setup.is_partial)
    c.eq("...and it can be resolved (%s)" % label, placer.confirm(), True)
    c.eq("...leaving nothing pending (%s)" % label, placer.is_busy, False)

cfg.AWAKENED_DYNASTY_PLAYERS = _SAVED_DYNASTY

# --------------------------------------------------------------------------
# 9. A returning model must be placed IN COHERENCY - and it is drawn that way
# --------------------------------------------------------------------------
print("=== 9. coherency is part of the placement ===")

# User: "immer wenn man Einheiten platzieren muss, zb durch Reanimation, muss
# man in coherency platzieren. dementsprechend muss auch das overlay sein. im
# Moment geht das ueber die ganze map?"
#
# It did. position_valid() leaves coherency out on purpose - its docstring says
# it "depends on the whole squad's final positions together, not a single
# point", which is true while every model of the unit is still in the air. A
# RETURN is the case where it is not: the survivors stand still and are the
# anchor. Measured on map2 before the change: 85.9% of the board painted green
# where 2.0% was legal - 42x too much ground, and the rejection only arrived at
# Confirm.
from game.squad import COHERENCY_RANGE_IN, coherency_probe  # noqa: E402

state9, squad9, setup9, placer9 = scene(HUMAN, dead=2)
returned9 = rp.reanimate(squad9, 2, all_tokens=state9.tokens,
                         position_valid=lambda m, x, y: setup9.position_valid(m, x, y, squad=squad9),
                         game_state=state9, placer=placer9)[1]
c.eq("a return placement is open", setup9.state, setup_mod.PLACING)
c.true("...and it is partial", setup9.is_partial)

valid9 = setup9.placement_validator(squad9)
# DEGRADE TO RED, NEVER CRASH. Under an A/B probe that stops the placement from
# opening at all, `placing_models` is empty and a bare [0] takes the whole suite
# down with it - which hides WHICH check broke. This repo has learned that one
# more than once (the two str.index() guards, the padded row in
# test_faction_badges.py).
placing9 = list(setup9.placing_models or [])
c.true("there is a returning model to place", bool(placing9))
moving9 = placing9[0] if placing9 else squad9.models[0]
anchor9 = next((m for m in squad9.models if m not in placing9), squad9.models[-1])

# WHERE THE PREDICATE STOPS SAYING YES is the coherency edge, and that is what
# is measured - not "next to it is legal, far away is not", which passes with
# the range written wrong. The model is walked away from the unit until the
# validator refuses, and that distance is compared against the RULE's own
# probe. Walking outwards also keeps the other terms (overlap, terrain) out of
# the answer: open ground in that direction is empty.
probe9 = coherency_probe(squad9.models, moving9)
cx = sum(m.x_in for m in squad9.models) / len(squad9.models)
cy = sum(m.y_in for m in squad9.models) / len(squad9.models)
dx, dy = moving9.x_in - cx, moving9.y_in - cy
length = (dx * dx + dy * dy) ** 0.5 or 1.0
dx, dy = dx / length, dy / length

last_ok = None
first_bad = None
step = 0.05
for i in range(1, 400):
    x, y = moving9.x_in + dx * step * i, moving9.y_in + dy * step * i
    if valid9(moving9, x, y):
        last_ok = (x, y)
    else:
        first_bad = (x, y)
        break
c.true("walking outwards eventually becomes illegal", first_bad is not None)
c.true("...and the last legal point is still coherent",
       last_ok is not None and probe9(*last_ok))
c.eq("...while the first illegal one is exactly where coherency ends",
     first_bad is not None and probe9(*first_bad), False)
c.eq("the far side of the board is not legal either",
     valid9(moving9, anchor9.x_in + 20.0, anchor9.y_in + 15.0), False)

# THE DRAG AGREES WITH THE PICTURE. This is the half that makes it a rule and
# not a colour: clamp_drag() is judged by the same predicate, so a model
# dragged across the board stops at the edge of coherency instead of standing
# somewhere Confirm would reject.
setup9.selected_model = moving9
dropped = setup9.clamp_drag(moving9, anchor9.x_in + 20.0, anchor9.y_in + 15.0)
c.true("dragging far away clamps back to legal ground", valid9(moving9, *dropped))
c.true("...which is inside coherency range of the unit",
       coherency_probe(squad9.models, moving9)(*dropped))

# THE OVERLAY IS THE SAME PREDICATE, so the green area really shrank. Measured
# as a fraction of the board rather than pinned to a number: the point is the
# ORDER of magnitude, and the exact figure moves with the survivors' positions.
def _green_fraction(controller, squad, token, step=1.0):
    fn = controller.placement_validator(squad)
    total = ok = 0
    x = 0.0
    while x <= 60.0:
        y = 0.0
        while y <= 44.0:
            total += 1
            ok += bool(fn(token, x, y))
            y += step
        x += step
    return ok / total

fraction = _green_fraction(setup9, squad9, moving9)
c.true("the overlay paints a small legal region, not the map (%.1f%%)"
       % (100 * fraction), fraction < 0.10)

# ...and a FULL Set Up is deliberately untouched (the user's own call): every
# model is still in the air there, so there is no anchor to measure against.
state_full = GameState()
full = tk.build(NECRON_WARRIORS, HUMAN, composition_index=0, name="1 Necron Warriors 9")
tk.line_up(full, x=20.0, y=20.0)
state_full.tokens = list(full.models)
setup_full = SetupController(state_full, all_tokens=state_full.tokens,
                             board_width_in=60.0, board_height_in=44.0)
setup_full.start_setup(full, 20.0, 20.0, on_cancel=lambda s: None)
c.eq("a full Set Up is not partial", setup_full.is_partial, False)
c.true("...and still paints the whole legal board (%.0f%%)"
       % (100 * _green_fraction(setup_full, full, full.models[0])),
       _green_fraction(setup_full, full, full.models[0]) > 0.50)

# --- the probe answers CONNECTIVITY, not "has a neighbour" -----------------
# Squad.check_coherency() was rewritten for exactly this: two mutually-coherent
# clusters satisfy every model individually while the unit has split in half.
# A returning model that BRIDGES two clusters is legal; one that only touches
# the near cluster is not, however close it is.
bridge_squad = tk.build(NECRON_WARRIORS, HUMAN, composition_index=0,
                        name="1 Necron Warriors 10")
left, right, mover = bridge_squad.models[0], bridge_squad.models[1], bridge_squad.models[2]
bridge_squad.models = [left, right, mover]
gap = left.radius_in + right.radius_in + COHERENCY_RANGE_IN * 2 - 0.4   # too far to touch
left.x_in, left.y_in = 20.0, 20.0
right.x_in, right.y_in = 20.0 + gap, 20.0
probe = coherency_probe(bridge_squad.models, mover)
c.true("the two clusters really cannot reach each other",
       gap > left.radius_in + right.radius_in + COHERENCY_RANGE_IN)
c.true("a model BETWEEN them, touching both, is coherent",
       probe((left.x_in + right.x_in) / 2, 20.0))
c.eq("...but hugging only one of them is NOT - the unit would stay split",
     probe(left.x_in + left.radius_in + mover.radius_in + 0.1, 20.0), False)
c.true("with the rest in one piece it is the familiar 'within 2 inches'",
       coherency_probe([left, mover], mover)(
           left.x_in + left.radius_in + mover.radius_in + COHERENCY_RANGE_IN - 0.1, 20.0))
c.true("a lone model has nothing to stay coherent with",
       coherency_probe([mover], mover)(50.0, 40.0))

# --- the cached overlay mask must not outlive the positions it was built from
key_before = setup9.overlay_cache_key(moving9)
c.eq("the same board gives the same key", setup9.overlay_cache_key(moving9), key_before)
anchor9.x_in += 3.0
c.true("...moving a squadmate changes it, so the mask is rebuilt",
       setup9.overlay_cache_key(moving9) != key_before)
anchor9.x_in -= 3.0
c.true("two same-sized models of the same placement get different keys",
       setup9.overlay_cache_key(moving9) != setup9.overlay_cache_key(anchor9))
c.eq("a full Set Up keeps the cheap generation key",
     setup_full.overlay_cache_key(full.models[0]), setup_full.placement_generation)

# main.py must actually USE it, or the mask is cached across moves that
# invalidate it - the "built but never FED" class this repo has hit six times.
# BOTH layers: the keep-out zone is the same for every model of the unit, the
# coherency band is not, so they carry separate keys.
c.true("main.py keys the keep-out layer on it",
       "setup_controller.overlay_cache_key(None)" in MAIN_SRC)
c.true("...and the coherency band on its own model",
       "setup_controller.overlay_cache_key(band_token)" in MAIN_SRC)

# --------------------------------------------------------------------------
# 10. The overlay is drawn as BASE EDGES, and that is the rule itself
# --------------------------------------------------------------------------
print("=== 10. base edges, not centres ===")

# User: "momentan ist die Grenze des overlays so dass der Base Mittelpunkt bis
# zur Grenze gehen kann. intuitiver waere aber der Baserand ... bei Baserand
# muss jedes Modell unabhaengig von der Basegroesse den selben Abstand
# einhalten."
#
# The centre reading was not just less intuitive, it was UNDRAWABLE for a unit
# with mixed bases: the legal-centre region is a different curve per base size,
# the overlay shows one, and main.py nominated the biggest model on the claim
# that its region is a subset of every other's. Coherency broke that claim.
import math  # noqa: E402
import random  # noqa: E402

state10, squad10, setup10, placer10 = scene(HUMAN, dead=2)
rp.reanimate(squad10, 2, all_tokens=state10.tokens,
             position_valid=lambda m, x, y: setup10.position_valid(m, x, y, squad=squad10),
             game_state=state10, placer=placer10)
placing10 = list(setup10.placing_models or [])
c.true("a return placement is open for the zones", bool(placing10))
token10 = placing10[0] if placing10 else squad10.models[0]
_EXPECTED_R = token10.radius_in
keep_out, band = setup10.base_edge_zones(squad10, token10)
rule10 = setup10.placement_validator(squad10)

# Asked AFTER a real query: keep_out() sets the radius to zero for the
# duration of the CALL, so reading it before one has been made proves nothing.
# Its own A/B probe found that (Fehlerklasse 24).
keep_out(20.0, 20.0)
c.eq("the token's radius is left exactly as it was after a query",
     token10.radius_in, _EXPECTED_R)
c.true("a return placement has a coherency band", band is not None)
# DEGRADE TO RED, NEVER CRASH: under a probe that removes the band or mangles
# the radius, everything below would take the suite down and hide WHICH check
# broke. Twelfth instance of that lesson in this repo.
if band is None:
    band = lambda x_in, y_in: False
c.eq("...and the query left the radius alone", token10.radius_in, _EXPECTED_R)

# THE EQUIVALENCE, at points where it can be decided exactly rather than by
# sampling a disc: a model whose base is tangent to a squadmate's 2" band is
# legal, one a hair further out is not - and the BAND says the same thing.
# The model stands somewhere the engine chose, so that spot is in the band by
# construction; walking away from the unit leaves it. The band is a
# CONNECTIVITY question over every component of the rest of the unit, so a
# point measured off ONE squadmate is not necessarily in it - which is exactly
# why the probe is asked rather than a distance re-derived here.
def _touches_band_at(probe, radius, x_in, y_in):
    """Does a base of `radius` centred here reach the band anywhere?"""
    if probe(x_in, y_in):
        return True
    if radius <= 0:          # a probe left the radius mangled - report, do not divide
        return False
    step = radius / 6.0
    n = int(radius / step) + 1
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            dx, dy = i * step, j * step
            if dx * dx + dy * dy <= radius * radius and probe(x_in + dx, y_in + dy):
                return True
    return False


cx10 = sum(m.x_in for m in squad10.models) / len(squad10.models)
cy10 = sum(m.y_in for m in squad10.models) / len(squad10.models)
ox, oy = token10.x_in - cx10, token10.y_in - cy10
norm = (ox * ox + oy * oy) ** 0.5 or 1.0
ox, oy = ox / norm, oy / norm
inside_pt = (token10.x_in, token10.y_in)
outside_pt = (token10.x_in + ox * 30.0, token10.y_in + oy * 30.0)
# ASKED OF THE BASE, NOT THE CENTRE - which is the whole change. The engine
# placed this model legally, so its BASE touches the band; its centre need not
# be inside it, and demanding that would be the centre reading all over again.
c.true("the base of the model where the engine put it touches the band",
       _touches_band_at(band, token10.radius_in, *inside_pt))
c.eq("...far away from the unit it does not",
     _touches_band_at(band, token10.radius_in, *outside_pt), False)

# ...and THAT is the SAME line whatever base the model has - the whole point of
# the change. Measured on the SAME model with its radius swapped, because a
# different model would change which squadmates are "the others" and move the
# band for a reason that has nothing to do with base size.
_saved_r = token10.radius_in
token10.radius_in = 2.1                                # a Doomsday-Ark base
keep_out_big, band_big = setup10.base_edge_zones(squad10, token10)
token10.radius_in = _saved_r
if band_big is None:
    band_big = lambda x_in, y_in: False
c.eq("the band is the same line for a 4.2in base as for a 1.26in one",
     (band_big(*inside_pt), band_big(*outside_pt)),
     (band(*inside_pt), band(*outside_pt)))
c.true("...so a big base standing there reaches it just the same",
       _touches_band_at(band_big, 2.1, *inside_pt))
# ...and the claim has to be tested where it can FAIL: a point just outside the
# band, which a radius-dependent band would answer differently. Two points 30in
# apart agree whatever the radius is, so they prove nothing on their own.
edge_probe = None
for k in range(1, 400):
    pt = (token10.x_in + ox * 0.05 * k, token10.y_in + oy * 0.05 * k)
    if not band(*pt):
        edge_probe = pt
        break
c.true("found a point just outside the band", edge_probe is not None)
if edge_probe is not None:
    c.eq("...and a 4.2in base does not move that line",
         band_big(*edge_probe), band(*edge_probe))

# The keep-out zone likewise: a model's OWN size must not move the line.
edge_pt = (0.05, 10.0)                                  # just inside the board edge
c.true("a point-sized base is allowed right up to the board edge",
       not keep_out(*edge_pt))
c.true("...and off the board it is forbidden", keep_out(-0.5, 10.0))
c.eq("...identically for a much bigger model - one line for the unit",
     (keep_out_big(*edge_pt), keep_out_big(-0.5, 10.0)),
     (keep_out(*edge_pt), keep_out(-0.5, 10.0)))

# WHICH IS WHAT THE RULE SAYS. "Base clear of the red AND touching the green"
# must agree with placement_validator() - the predicate the drag clamp uses -
# or the picture and the game would mean different things.
def _base_clear(x_in, y_in, radius):
    if radius <= 0:
        return not keep_out(x_in, y_in)
    step = radius / 6.0
    n = int(radius / step) + 1
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            dx, dy = i * step, j * step
            if dx * dx + dy * dy <= radius * radius and keep_out(x_in + dx, y_in + dy):
                return False
    return True


def _base_touches_band(x_in, y_in, radius):
    if band is None:
        return True
    if radius <= 0:
        return band(x_in, y_in)
    step = radius / 6.0
    n = int(radius / step) + 1
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            dx, dy = i * step, j * step
            if dx * dx + dy * dy <= radius * radius and band(x_in + dx, y_in + dy):
                return True
    return False


rng10 = random.Random(19)
agree = disagree = 0
for _ in range(600):
    x = rng10.uniform(2.0, 40.0)
    y = rng10.uniform(2.0, 40.0)
    drawn = (_base_clear(x, y, token10.radius_in)
             and _base_touches_band(x, y, token10.radius_in))
    if rule10(token10, x, y) == drawn:
        agree += 1
    else:
        disagree += 1
# Not 100%: the disc is sampled, and the thin walls of a ruin are about as wide
# as the sample spacing. The claim is that the two readings are the SAME rule,
# which is exact by construction (every term is measured edge to edge); this
# just catches a wiring mistake that would make them differ wholesale.
c.true("reading the picture by base edge agrees with the rule (%d/%d)"
       % (agree, agree + disagree), agree / (agree + disagree) > 0.97)

# The renderer must actually draw BOTH layers, or the band is a fact nobody
# sees - "built but never FED", six times in this repo.
RENDER_SRC = (ROOT / "game" / "renderer.py").read_text(encoding="utf-8")
c.true("the renderer draws the keep-out layer",
       "self._placement_overlay.draw(" in RENDER_SRC)
# Checked as a REACHABLE call, not as a string: `if False:` in front of it
# leaves the text in place, and its own A/B probe is what found that
# (Fehlerklasse 24).
_band_draw = RENDER_SRC[RENDER_SRC.find("def draw_placement_overlay"):]
_band_draw = _band_draw[:_band_draw.find("self._coherency_overlay.draw(")]
c.true("...and the coherency band as its own layer",
       "self._coherency_overlay.draw(" in RENDER_SRC)
c.true("...behind a real condition, not a disabled one",
       "if band_fn is not None:" in _band_draw and "if False" not in _band_draw)
c.true("...with the band's own palette, so it reads as 'reach this'",
       "invalid_color=placement_overlay.BAND_OUTSIDE_COLOR" in RENDER_SRC)
c.true("main.py hands it both zones",
       "setup_controller.base_edge_zones(" in MAIN_SRC)
c.true("...and no longer nominates the biggest model to draw for",
       "max(overlay_models, key=lambda m: m.radius_in)" not in MAIN_SRC)


# --------------------------------------------------------------------------
# 11. WHICH models just came back
# --------------------------------------------------------------------------
print("=== 11. which models just came back ===")

# User: "Widerbeleben - ich kann nicht erkennen, welche einheiten gerade
# zurueckgekommen sind, um sie zu verschieben. bitte hervorheben."
#
# The gap was structural, not a missing colour: a return drops one or two
# models into a unit that is ALREADY STANDING, and the only board marking was
# draw_placement_identity()'s outline around the WHOLE unit - equally true of
# the survivors that must not be touched. Measured on PIXELS, because a source
# guard would only say the call is there, not that anything is painted.

import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((320, 240))

from game.board import Board  # noqa: E402
from game.renderer import Renderer, RETURNING_MODEL_COLOR  # noqa: E402

_PPI = 24.0


def _drawn(placing):
    """The board with a placement identity on it, and the returning rings' own
    colour count - a whole unit versus the subset that came back.

    The two "returning" models are stood well clear of the line the survivors
    are in, which is the real shape of a return (they are set up wherever the
    player drags them) and also what lets a ring be attributed to ONE model:
    tk.line_up() packs bases 1.4" apart, closer than the rings are wide."""
    state11, squad11, setup11, _placer11 = scene(HUMAN, dead=2)
    for index, model in enumerate(squad11.models[:2]):
        model.x_in, model.y_in = 40.0 + index * 3.0, 30.0
    board11 = Board(60.0, 44.0, _PPI)
    surface = pygame.Surface((board11.width_px, board11.height_px))
    surface.fill((0, 0, 0))
    Renderer(render_scale=1.0).draw_placement_identity(
        surface, board11, squad11,
        placing_models=(squad11.models[:2] if placing == "subset"
                        else (list(squad11.models) if placing == "all" else None)),
    )
    white = sum(1 for x in range(surface.get_width())
                for y in range(surface.get_height())
                if surface.get_at((x, y))[:3] == RETURNING_MODEL_COLOR)
    return surface, squad11, board11, white


_surface, _squad11, _board11, _subset_white = _drawn("subset")
_none_surface, _, _, _none_white = _drawn(None)
_all_surface, _, _, _all_white = _drawn("all")

c.true("a partial placement rings the returning models", _subset_white > 0)
c.true("...and an ordinary Set Up draws none of that", _none_white == 0)
# The whole unit is not "some models came back" - it is a plain Set Up, and
# ringing all twenty would say nothing.
c.true("...nor does a placement that owns the whole unit", _all_white == 0)


def _ring_pixels(surface, board11, model):
    """White pixels within a couple of base radii of this model."""
    cx, cy = board11.to_px(model.x_in, model.y_in)
    reach = board11.in_to_px_len(model.radius_in) + 14
    return sum(1 for x in range(int(cx - reach), int(cx + reach))
               for y in range(int(cy - reach), int(cy + reach))
               if 0 <= x < surface.get_width() and 0 <= y < surface.get_height()
               and surface.get_at((x, y))[:3] == RETURNING_MODEL_COLOR)


_returning = _squad11.models[:2]
_survivors = _squad11.models[2:]
c.true("each returning model gets its own ring",
       all(_ring_pixels(_surface, _board11, m) > 0 for m in _returning))
# The whole point: the survivors standing beside them must NOT be marked, or
# the picture says the same thing the unit outline already said.
c.true("...and no survivor is marked",
       all(_ring_pixels(_surface, _board11, m) == 0 for m in _survivors))

# TWO rings, not one - a single ring differs from the selection outline only in
# colour, and this has to be findable at a glance in a packed blob.
_m = _returning[0]
_cx, _cy = _board11.to_px(_m.x_in, _m.y_in)
_scan = [x for x in range(int(_cx), int(_cx) + 30)
         if _surface.get_at((x, int(_cy)))[:3] == RETURNING_MODEL_COLOR]
_runs = 1 + sum(1 for a, b in zip(_scan, _scan[1:]) if b - a > 1)
c.eq("the returning marker is a DOUBLE ring", _runs, 2)

# ...and the plate counts them, so the panel's "Returning Models" heading has
# an answer on the board too.
RENDER_SRC11 = (ROOT / "game" / "renderer.py").read_text(encoding="utf-8")
c.true("the name plate says how many are being placed",
       "returning model" in RENDER_SRC11)
c.true("the highlight is its own method, not inlined into the identity draw",
       "def draw_returning_models(" in RENDER_SRC11)

# --------------------------------------------------------------------------
# 12. a second placement QUEUES; it is not seated by the engine
# --------------------------------------------------------------------------
print("=== 12. two placements in one frame ===")

# User: "Einheiten wurde automatisch platziert ... obwohl ich necrons spiele."
#
# place()'s fork used to read:
#
#     if (owner in auto_players or setup_controller is None
#             or not setup_controller.can_start_setup(squad)):
#         ...engine seats them, same frame...
#
# and can_start_setup() is "state == IDLE", so the third disjunct meant
# SOMEBODY IS ALREADY PLACING. Folded in with the AI's answer it became a
# silent human -> engine fallback. Measured with two damaged human Necron units
# reanimating in one Command phase: the placement opened for the FIRST unit
# twice and the second unit's models were seated with no prompt and no
# distinguishing log line.

state_q, squad_a, setup_q, placer_q = scene(HUMAN)
# A SHORT unit: ten Warriors in a line plus two coming back exceed 09.02's 9"
# spread, and confirm_setup() would then refuse the second placement for a
# reason that has nothing to do with the queue.
squad_b = tk.build(NECRON_WARRIORS, HUMAN, name="1 Necron Warriors 2")
squad_b.models[:] = squad_b.models[:4]
tk.line_up(squad_b, x=40.0, y=20.0)
state_q.tokens.extend(squad_b.models)
for _m in squad_b.models[:2]:
    _m.current_wounds = 0
state_q.remove_dead_models()

opened = []
placer_q.setup_controller = setup_q


def _note_open():
    if setup_q.setting_up_squad is not None:
        opened.append(setup_q.setting_up_squad.name)


rp.reanimate(squad_a, 2, all_tokens=state_q.tokens, game_state=state_q, placer=placer_q)
_note_open()
c.eq("the first unit's placement opens", setup_q.setting_up_squad is squad_a, True)

# ...and now the second arrives while the first is still open.
before_b = len(squad_b.models)
rp.reanimate(squad_b, 2, all_tokens=state_q.tokens, game_state=state_q, placer=placer_q)
c.eq("the second does NOT steal the open placement",
     setup_q.setting_up_squad is squad_a, True)
c.true("...it is queued instead", placer_q.is_busy)
c.eq("...and its models are on the board, waiting to be positioned",
     len(squad_b.models) > before_b, True)

# THE INVARIANT that makes main.py's existing gate enough: a queued placement
# always has an OPEN one in front of it, and an open one is
# setup_controller.state == PLACING, which the phase gate already waits on.
# Written down because the first version of this fix added a second gate term
# and an `or bool(self._waiting)` for a state that cannot occur - both dead,
# both found by their own A/B probes reporting NO BITE.
c.true("a queued placement always has an open one in front of it",
       not placer_q._waiting or placer_q._pending is not None)
c.true("...so is_busy is true while either is outstanding", placer_q.is_busy)
c.true("...and the phase gate already waits on an open placement",
       "setup_controller.state == setup.PLACING" in MAIN_SRC)

placer_q.confirm()
_note_open()
c.eq("confirming the first opens the SECOND", setup_q.setting_up_squad is squad_b, True)
c.eq("each unit got its own placement, once", opened, [squad_a.name, squad_b.name])
placer_q.confirm()
c.eq("...and the queue is empty afterwards", placer_q.is_busy, False)

# CANCEL owes the queue exactly what confirm does - a placement abandoned is
# still a placement finished, and the unit behind it is still waiting.
state_c, squad_c, setup_c, placer_c = scene(HUMAN)
squad_d = tk.build(NECRON_WARRIORS, HUMAN, name="1 Necron Warriors 4")
squad_d.models[:] = squad_d.models[:4]
tk.line_up(squad_d, x=40.0, y=20.0)
state_c.tokens.extend(squad_d.models)
for _m in squad_d.models[:2]:
    _m.current_wounds = 0
state_c.remove_dead_models()
rp.reanimate(squad_c, 2, all_tokens=state_c.tokens, game_state=state_c, placer=placer_c)
rp.reanimate(squad_d, 2, all_tokens=state_c.tokens, game_state=state_c, placer=placer_c)
placer_c.cancel()
c.eq("cancelling the first also opens the second",
     setup_c.setting_up_squad is squad_d, True)

# THE AI IS UNCHANGED - the module's own docstring makes that a standing
# promise, and it is the half a queue could most easily break.
state_ai, squad_ai, setup_ai, placer_ai = scene(AI)
squad_ai2 = tk.build(NECRON_WARRIORS, AI, name="2 Necron Warriors 2")
squad_ai2.models[:] = squad_ai2.models[:4]
tk.line_up(squad_ai2, x=40.0, y=20.0)
state_ai.tokens.extend(squad_ai2.models)
for _m in squad_ai2.models[:2]:
    _m.current_wounds = 0
state_ai.remove_dead_models()
rp.reanimate(squad_ai, 2, all_tokens=state_ai.tokens, game_state=state_ai, placer=placer_ai)
rp.reanimate(squad_ai2, 2, all_tokens=state_ai.tokens, game_state=state_ai, placer=placer_ai)
c.eq("two AI units in one frame open nothing", setup_ai.state, setup_mod.IDLE)
c.eq("...and queue nothing", placer_ai.is_busy, False)
c.true("...and both got their models back",
       len(squad_ai.models) > 8 and len(squad_ai2.models) > 2)

# A FOREIGN placement (an arrival, a disembark) is a different branch and must
# NOT be queued - nothing here owns the resume for a placement it did not open,
# so queuing it would be a deadlock. The engine still answers; what changed is
# that it SAYS SO, which was the missing half of the report.
state_f, squad_f, setup_f, placer_f = scene(HUMAN)
other = tk.build(NECRON_WARRIORS, HUMAN, name="1 Necron Warriors 9")
tk.line_up(other, x=52.0, y=20.0)
state_f.tokens.extend(other.models)
setup_f.start_setup(other, other.models[0].x_in, other.models[0].y_in,
                    on_cancel=lambda _squad: None)
c.eq("something else is placing", setup_f.state, setup_mod.PLACING)
log_f = tk.Log()
placer_f.game_log = log_f
rp.reanimate(squad_f, 2, all_tokens=state_f.tokens, game_state=state_f, placer=placer_f)
c.eq("a foreign placement is not stolen", setup_f.setting_up_squad is other, True)
c.eq("...and nothing is queued behind it", placer_f.is_busy, False)
c.true("...but the log SAYS the engine placed them",
       log_f.has("placed by the engine"))

c.finish()
