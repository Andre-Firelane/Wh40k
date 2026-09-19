"""Are Green Tide's panel buttons really OFFERED, and at the right moment? -
measured by drawing the real ActionPanel (Mecha Orks stage G3).

The shape of test_ork_detachment_ui.py, which says why this file exists: a
controller whose can_use() is right and whose button nobody has ever seen drawn
is the one gap every stratagem audit here found. Three buttons:

    Unbridled Carnage (1CP)  "Fight phase, when a friendly BOYZ unit that made a
                              charge move this turn is selected to fight"
    'Ere We Go (1CP)         "Your Movement phase, when a friendly BEAST SNAGGA
                              BOYZ/BOYZ unit is selected to move"
    Mob Mentality (1CP)      "Start of the Battle-shock step of your Command
                              phase" - TARGET a friendly ORKS INFANTRY unit of
                              13+ models

Unbridled Carnage's WHEN has no "your": it must appear in the OPPONENT's Fight
phase as well (section 2).

  0. LIVENESS - every render reached _draw_movement_ui() with a unit selected,
     and an empty registry draws no Green Tide button.
  1. THE PHASE MATRIX - each button for each unit, in every phase; the TARGET
     negatives come with it.
  2. WHOSE PHASE.
  3. THE DETACHMENT GATE AT THE PANEL.
  4. THE PRINTED CLAUSES and the CP gate, as negatives.
  5. THE RESETS, each isolated.
  6. THE CLICK REALLY PAYS - Mob Mentality's second question drained.
  7. LABEL AGAINST CORPUS.
  8. WHICH Green Tide classes belong on the panel, by AST.

THE BOARD IS REBUILT PER SECTION: buying a button applies it and leaves a mark.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import ast                                                           # noqa: E402
import io                                                            # noqa: E402
import re                                                            # noqa: E402
from types import SimpleNamespace                                    # noqa: E402

import pygame                                                        # noqa: E402

import testkit as tk                                                 # noqa: E402
from testkit import Checks, settings_as                              # noqa: E402
from game import config, maps, rules_text                            # noqa: E402
from game import green_tide_ere_we_go as ewg                         # noqa: E402
from game import green_tide_mob_mentality as mm                      # noqa: E402
from game import green_tide_unbridled_carnage as uc                  # noqa: E402
from game.battle_shock import BattleShockController                  # noqa: E402
from game.command_points import CommandPointManager                  # noqa: E402
from game.decision import DecisionManager                            # noqa: E402
from game.dice import DiceManager                                    # noqa: E402
from game.game_state import GameState                                # noqa: E402
from game.movement import MovementController                         # noqa: E402
from game.proactive_stratagems import ProactiveStratagems            # noqa: E402
from game.shooting import ShootingController                         # noqa: E402
from game.stratagems import StratagemController                      # noqa: E402
from game.turn import (PHASES, PHASE_COMMAND, PHASE_FIGHT,           # noqa: E402
                       PHASE_MOVEMENT, TurnTracker)
from game.ui.action_panel import ActionPanel                         # noqa: E402

from game.factions import orks as ork                                # noqa: E402

c = Checks("Green Tide panel buttons")

pygame.init()
pygame.display.set_mode((1200, 900))

HUMAN = "Player 1"
FOE = "Player 2"
ROUND = 2

# War Horde off - it is Player 2's by default and irrelevant here.
GT = dict(GREEN_TIDE_PLAYERS=(HUMAN, FOE), WAR_HORDE_PLAYERS=())
NO_GT = dict(GREEN_TIDE_PLAYERS=(), WAR_HORDE_PLAYERS=())

M2 = maps.get("map2")
maps.apply_to_config(M2)

CARNAGE = uc.UNBRIDLED_CARNAGE_NAME
ERE = ewg.ERE_WE_GO_NAME
MOB = mm.MOB_MENTALITY_NAME
NAMES = (CARNAGE, ERE, MOB)

# TRANSCRIBED from rules/orks/detachments/Green Tide.md, deliberately not
# imported. `own`: the phases the printed WHEN says "your" about; `any`: the
# phases it names without an owner.
WHEN = {
    CARNAGE: dict(own=frozenset(), any=frozenset({PHASE_FIGHT})),
    ERE: dict(own=frozenset({PHASE_MOVEMENT}), any=frozenset()),
    MOB: dict(own=frozenset({PHASE_COMMAND}), any=frozenset()),
}
# The two board units: a 20-model Boyz mob that charged (every button's TARGET),
# and a Beast Snagga Boyz unit below half strength 6" from it - 'Ere We Go's
# other datasheet, and Mob Mentality's CANDIDATE (not its target: 10 models,
# not BOYZ for Unbridled Carnage).
APPLIES = {(CARNAGE, "mob"), (ERE, "mob"), (MOB, "mob"), (ERE, "bsb")}


def phases_for(name):
    return WHEN[name]["own"] | WHEN[name]["any"]


def turn_at(phase, owner=HUMAN):
    tracker = TurnTracker(first_player=owner)
    tracker.started = True
    tracker.phase_index = PHASES.index(phase)
    tracker.turn_owner = owner
    tracker.set_active(owner)
    tracker.battle_round = ROUND
    return tracker


def strat(cp=10):
    pool = CommandPointManager()
    for player in pool.cp:
        pool.cp[player] = cp
    return StratagemController(command_points=pool, game_log=tk.Log())


def cluster(squad, point, spacing=1.2, per_row=5):
    n = len(squad.models)
    rows = (n + per_row - 1) // per_row
    cols = min(n, per_row)
    for i, model in enumerate(squad.models):
        r, col = divmod(i, per_row)
        model.x_in = point[0] + (col - (cols - 1) / 2.0) * spacing
        model.y_in = point[1] + (r - (rows - 1) / 2.0) * spacing
    return squad


# ------------------------------------------------------------------- the board

B = {}
ALL_TOKENS = []


def build_board(second_candidate=False):
    """A fresh map2 board in your deployment zone, nowhere near an enemy - the
    stubs answer the fight/move ledgers, so no button is refused for a
    geometric reason the matrix is not about."""
    B.clear()
    st = GameState()
    M2.build(st)
    own = next(z for z in st.deployment_zones if z.owner == HUMAN)
    points = [(x, y) for y in [v * 0.5 for v in range(2, 88)] for x in [v * 0.5 for v in range(2, 120)]
              if own.contains_circle(x, y, 4.0)]
    mob = tk.build(ork.BOYZ, HUMAN, name="1 Boyz 1", composition_index=1)
    mob.charged_this_turn = True
    B["mob"] = cluster(mob, points[0])
    near = next(p for p in points if 5.5 < abs(p[0] - points[0][0]) + abs(p[1] - points[0][1]) < 7.0)
    bsb = tk.build(ork.BEAST_SNAGGA_BOYZ, HUMAN, name="1 Beast Snagga Boyz 1")
    B["bsb"] = cluster(bsb, near)
    squads = [B["mob"], B["bsb"]]
    if second_candidate:
        other = next(p for p in points if 5.5 < abs(p[0] - points[0][0]) + abs(p[1] - points[0][1]) < 7.0
                     and abs(p[0] - near[0]) + abs(p[1] - near[1]) > 4.0)
        B["bsb2"] = cluster(tk.build(ork.BEAST_SNAGGA_BOYZ, HUMAN, name="1 Beast Snagga Boyz 2"), other)
        squads.append(B["bsb2"])
    B["state"] = st
    ALL_TOKENS[:] = [m for s in squads for m in s.models]
    for model in ALL_TOKENS:
        st.add_token(model)
    # Below half strength: 4 of 10 left, and the death sweep run as a frame would.
    for s in squads[1:]:
        for model in s.models[:6]:
            model.current_wounds = 0
    st.remove_dead_models()
    ALL_TOKENS[:] = list(st.tokens)
    return B


def tide(sc=None, cp=10):
    """The three Green Tide panel controllers on one registry, sharing a
    StratagemController so rule 15.01 binds them the way it does in a game, and
    a REAL BattleShockController for Mob Mentality's window."""
    sc = sc if sc is not None else strat(cp)
    fight = SimpleNamespace(fought_squad_ids=set(), fighting_squad=None)
    fight.is_eligible_to_fight = lambda squad: squad not in fight.fought_squad_ids
    mover = SimpleNamespace(moved_squad_ids=set(), advanced_squad_ids=set())
    bsc = BattleShockController(game_log=tk.Log(), dice_manager=DiceManager(), all_tokens=ALL_TOKENS)
    decision = DecisionManager()
    built = {
        CARNAGE: uc.UnbridledCarnageController(sc, fight_controller=fight, game_log=tk.Log()),
        ERE: ewg.EreWeGoController(sc, movement_controller=mover, game_log=tk.Log()),
        MOB: mm.MobMentalityController(sc, battle_shock_controller=bsc, decision_manager=decision,
                                       all_tokens=ALL_TOKENS, game_log=tk.Log()),
    }
    registry = ProactiveStratagems()
    for name in NAMES:
        registry.add(built[name])
    return dict(sc=sc, fight=fight, mover=mover, bsc=bsc, decision=decision, built=built, registry=registry)


# ------------------------------------------------------------- the render rig

_panel = ActionPanel()
_surface = pygame.Surface((config.LEFT_PANEL_WIDTH, 900))
_rect = pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, 900)
_labels = []
_reached = []
_real_button = ActionPanel._draw_button
_real_movement_ui = ActionPanel._draw_movement_ui


def _spy_button(self, surface, rect, label, *a, **kw):
    out = _real_button(self, surface, rect, label, *a, **kw)
    _labels.append(label)
    return out


def _spy_movement_ui(self, *a, **kw):
    _reached.append(True)
    return _real_movement_ui(self, *a, **kw)


ActionPanel._draw_button = _spy_button
ActionPanel._draw_movement_ui = _spy_movement_ui


def render(squad, phase, rig, owner=HUMAN, registry=None):
    """Draw the real panel for `squad` in `phase`; (labels, names, buttons, reached)."""
    tracker = turn_at(phase, owner)
    for ctrl in rig["built"].values():
        ctrl.turn_tracker = tracker
    rig["bsc"].turn_tracker = tracker
    mover = MovementController([], tk.Log(), owner, DiceManager(), tracker, ALL_TOKENS)
    shooter = ShootingController(obstacles=[], game_log=tk.Log(), player_name=owner,
                                 dice_manager=DiceManager(), turn_tracker=tracker,
                                 all_tokens=ALL_TOKENS, decision_manager=DecisionManager())
    _labels.clear()
    _reached.clear()
    _surface.fill((0, 0, 0))
    mover.select(squad.models[0])
    _panel.draw(_surface, _rect, mover, shooter, dice_manager=DiceManager(),
                proactive_stratagems=rig["registry"] if registry is None else registry)
    return (list(_labels), [n for _, n in _panel._stratagem_buttons], list(_panel._buttons),
            mover.selected_squad is squad and bool(_reached))


def press(name, buttons):
    """Click the drawn button; False if there was none - a probe that removes a
    button has to turn this file RED, not crash it."""
    rect = next((r for r, n in _panel._stratagem_buttons if n == name), None)
    if rect is None:
        return False
    callback = next((cb for r, cb in buttons if r == rect), None)
    if callback is None:
        return False
    callback()
    return True


def drain(decision, want):
    """Answer the open prompt with the option whose label contains `want`."""
    if not decision.is_pending:
        return False
    option = next((o for o in decision.options if want in o["label"]), None)
    if option is None:
        return False
    decision.choose(decision.options.index(option))
    return True


def tide_names(names):
    return [n for n in names if n in NAMES]


# ==========================================================================
print("=== 0. the render really produced a panel ===")
# ==========================================================================

with settings_as(**GT):
    build_board()
    rig = tide()
    for _phase in PHASES:
        for _key in ("mob", "bsb"):
            _l, _n, _b, _ok = render(B[_key], _phase, rig)
            c.true("%s / %s: a unit was selected AND the unit screen was drawn" % (_phase, _key), _ok)
    _l, _names_empty, _b, _ok = render(B["mob"], PHASE_FIGHT, rig, registry=ProactiveStratagems())
    c.eq("with an EMPTY registry no Green Tide button is drawn, even in the right phase",
         tide_names(_names_empty), [])
    rig["bsc"].turn_tracker = turn_at(PHASE_COMMAND)
    c.true("the premise: the Beast Snagga Boyz owe a Battle-shock roll", rig["bsc"].can_roll(B["bsb"]))


# ==========================================================================
print("=== 1. the phase matrix: 3 buttons x 2 units x every phase, your turn ===")
# ==========================================================================

with settings_as(**GT):
    for _name in NAMES:
        for _key in ("mob", "bsb"):
            for _phase in PHASES:
                build_board()
                rig = tide()
                _l, names, _b, _ok = render(B[_key], _phase, rig)
                _want = (_name, _key) in APPLIES and _phase in phases_for(_name)
                c.eq("%s for the %s in %s" % (_name, _key, _phase), _name in names, _want)


# ==========================================================================
print("=== 2. whose phase ===")
# ==========================================================================

with settings_as(**GT):
    build_board()
    rig = tide()
    _l, names, _b, _ok = render(B["mob"], PHASE_FIGHT, rig, owner=FOE)
    c.true("(live) the panel selected the mob in the opponent's Fight phase", _ok)
    c.true("Unbridled Carnage IS offered in the OPPONENT's Fight phase", CARNAGE in names)
    for _name, _key, _phase in ((ERE, "mob", PHASE_MOVEMENT), (MOB, "mob", PHASE_COMMAND)):
        build_board()
        rig = tide()
        _ctrl = rig["built"][_name]
        _ctrl.turn_tracker = turn_at(_phase, FOE)
        # A decision window of YOURS inside the opponent's phase (active_player
        # flips, turn_owner does not): your units then answer can_roll(), so only
        # the controller's own "your Command phase" clause can refuse.
        _ctrl.turn_tracker.set_active(HUMAN)
        rig["bsc"].turn_tracker = _ctrl.turn_tracker
        c.eq("%s refuses the OPPONENT's %s phase" % (_name, _phase), _ctrl.can_use(B[_key]), False)
        _ctrl.turn_tracker = turn_at(_phase, HUMAN)
        rig["bsc"].turn_tracker = _ctrl.turn_tracker
        c.eq("...and accepts your own (the counter-proof)", _ctrl.can_use(B[_key]), True)


# ==========================================================================
print("=== 3. the detachment gate, AT THE PANEL ===")
# ==========================================================================

with settings_as(**NO_GT):
    for _phase in PHASES:
        for _key in ("mob", "bsb"):
            build_board()
            rig = tide()
            _l, names, _b, _ok = render(B[_key], _phase, rig)
            c.eq("no Green Tide, no Green Tide button (%s, %s)" % (_phase, _key), tide_names(names), [])


# ==========================================================================
print("=== 4. the printed clauses and the CP gate, as negatives ===")
# ==========================================================================

with settings_as(**GT):
    build_board()
    rig = tide()
    rig["fight"].fought_squad_ids.add(B["mob"])
    _l, names, _b, _ok = render(B["mob"], PHASE_FIGHT, rig)
    c.eq("Unbridled Carnage: gone once the unit has fought", CARNAGE in names, False)

    build_board()
    rig = tide()
    rig["fight"].fighting_squad = B["mob"]
    _l, names, _b, _ok = render(B["mob"], PHASE_FIGHT, rig)
    c.eq("...and while it is fighting", CARNAGE in names, False)

    build_board()
    B["mob"].charged_this_turn = False
    rig = tide()
    _l, names, _b, _ok = render(B["mob"], PHASE_FIGHT, rig)
    c.eq("Unbridled Carnage: gone for a mob that did not charge", CARNAGE in names, False)

    build_board()
    rig = tide()
    rig["mover"].moved_squad_ids.add(B["mob"])
    _l, names, _b, _ok = render(B["mob"], PHASE_MOVEMENT, rig)
    c.eq("'Ere We Go: gone once the unit has moved", ERE in names, False)

    build_board()
    rig = tide()
    # The roll is the MOB's, so the Beast Snagga Boyz still owe theirs - only the
    # "step has begun" clause can refuse here.
    rig["bsc"].rolled_squad_ids.add(B["mob"])
    _l, names, _b, _ok = render(B["mob"], PHASE_COMMAND, rig)
    c.eq("Mob Mentality: gone once a Battle-shock roll of yours was made", MOB in names, False)

    build_board()
    for _m in B["mob"].models[:8]:
        _m.current_wounds = 0
    B["state"].remove_dead_models()
    ALL_TOKENS[:] = list(B["state"].tokens)
    rig = tide()
    _l, names, _b, _ok = render(B["mob"], PHASE_COMMAND, rig)
    c.eq("Mob Mentality: gone for a mob of 12 (13+ models)", MOB in names, False)

    build_board()
    rig = tide(cp=0)
    for _name, _phase in ((CARNAGE, PHASE_FIGHT), (ERE, PHASE_MOVEMENT), (MOB, PHASE_COMMAND)):
        _l, names, _b, _ok = render(B["mob"], _phase, rig)
        c.eq("with 0CP %s is not drawn" % _name, _name in names, False)


# ==========================================================================
print("=== 5. the resets, each isolated ===")
# ==========================================================================

with settings_as(**GT):
    build_board()
    rig = tide()
    _l, names, buttons, _ok = render(B["mob"], PHASE_FIGHT, rig)
    c.true("Unbridled Carnage is on the panel before any purchase", CARNAGE in names)
    c.true("...pressed", press(CARNAGE, buttons))
    _l, names, _b, _ok = render(B["mob"], PHASE_FIGHT, rig)
    c.eq("...and gone after it", CARNAGE in names, False)
    rig["sc"].reset_phase()
    _l, names, _b, _ok = render(B["mob"], PHASE_FIGHT, rig)
    c.eq("15.01's reset ALONE leaves it gone - the unit still carries the grant", CARNAGE in names, False)
    uc.reset_phase([B["mob"]])
    _l, names, _b, _ok = render(B["mob"], PHASE_FIGHT, rig)
    c.true("...and the grant's own end-of-phase reset brings it back", CARNAGE in names)

    build_board()
    rig = tide()
    _l, names, buttons, _ok = render(B["mob"], PHASE_MOVEMENT, rig)
    c.true("'Ere We Go is on the panel before any purchase", ERE in names)
    press(ERE, buttons)
    ewg.reset_phase([B["mob"]])
    _l, names, _b, _ok = render(B["mob"], PHASE_MOVEMENT, rig)
    c.eq("its own reset ALONE leaves it gone - rule 15.01 still refuses", ERE in names, False)
    rig["sc"].reset_phase()
    _l, names, _b, _ok = render(B["mob"], PHASE_MOVEMENT, rig)
    c.true("...and with 15.01's reset too, it is back", ERE in names)

    build_board()
    rig = tide()
    _l, names, buttons, _ok = render(B["mob"], PHASE_COMMAND, rig)
    c.true("Mob Mentality is on the panel before any purchase", MOB in names)
    press(MOB, buttons)
    rig["sc"].reset_phase()
    _l, names, _b, _ok = render(B["mob"], PHASE_COMMAND, rig)
    c.eq("15.01's reset ALONE leaves it gone - its one candidate is covered", MOB in names, False)
    mm.reset_phase([B["bsb"]])
    _l, names, _b, _ok = render(B["mob"], PHASE_COMMAND, rig)
    c.true("...and the grant's own reset brings it back", MOB in names)


# ==========================================================================
print("=== 6. the click really pays ===")
# ==========================================================================

with settings_as(**GT):
    for _name, _phase, _cp, _effect, _on in (
            (CARNAGE, PHASE_FIGHT, uc.UNBRIDLED_CARNAGE_CP, uc.is_active, "mob"),
            (ERE, PHASE_MOVEMENT, ewg.ERE_WE_GO_CP, ewg.is_active, "mob"),
            (MOB, PHASE_COMMAND, mm.MOB_MENTALITY_CP, mm.auto_passes, "bsb")):
        build_board()
        rig = tide()
        _l, names, buttons, _ok = render(B["mob"], _phase, rig)
        _before = rig["sc"].command_points.cp[HUMAN]
        c.true("pressing %s" % _name, press(_name, buttons))
        c.eq("...spends its printed %dCP" % _cp, _before - rig["sc"].command_points.cp[HUMAN], _cp)
        c.true("...and grants the effect (to the %s)" % _on, _effect(B[_on]))

    # Two candidates: the button opens a pick, and only the PICK pays.
    build_board(second_candidate=True)
    rig = tide()
    _l, names, buttons, _ok = render(B["mob"], PHASE_COMMAND, rig)
    _before = rig["sc"].command_points.cp[HUMAN]
    c.true("pressing Mob Mentality with two units in reach", press(MOB, buttons))
    c.true("...opens the pick", rig["decision"].is_pending)
    c.eq("...having paid nothing yet", rig["sc"].command_points.cp[HUMAN], _before)
    c.true("...drained: the second Beast Snagga Boyz picked", drain(rig["decision"], B["bsb2"].name))
    c.eq("...and THAT pays 1CP", _before - rig["sc"].command_points.cp[HUMAN], 1)
    c.true("...covering the unit picked, not the other",
           mm.auto_passes(B["bsb2"]) and not mm.auto_passes(B["bsb"]))


# ==========================================================================
print("=== 7. what the corpus prints, and what the panel draws ===")
# ==========================================================================

_CORPUS = rules_text.detachment_stratagems("ORKS", "Green Tide")
c.eq("the printed detachment was read - three Stratagems", len(_CORPUS), 3)
for _name, _phase in ((CARNAGE, PHASE_FIGHT), (ERE, PHASE_MOVEMENT), (MOB, PHASE_COMMAND)):
    with settings_as(**GT):
        build_board()
        rig = tide()
        _labels_s, names, _b, _ok = render(B["mob"], _phase, rig)
    _label = next((lab for lab in _labels_s if lab.startswith(_name + " (")), None)
    c.true("%s: a label was drawn" % _name, _label is not None)
    found = rules_text.stratagem_named("ORKS", ["Green Tide"], _name)
    c.true("...the DRAWN name resolves to the printed Stratagem",
           found is not None and found.name.lower() == _name.lower())
    _printed_cp = re.search(r"(\d+)", str(found.cost)) if found is not None else None
    _drawn_cp = re.search(r"\((\d+) CP\)", _label or "")
    c.eq("...and the label's cost is the printed cost",
         _drawn_cp.group(1) if _drawn_cp else None, _printed_cp.group(1) if _printed_cp else None)


# ==========================================================================
print("=== 8. which Green Tide classes belong on the panel, by AST ===")
# ==========================================================================

MAIN_TREE = ast.parse(io.open("main.py", encoding="utf-8").read())
_registered = set()
for node in ast.walk(MAIN_TREE):
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add" and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "proactive_stratagems"):
        for arg in node.args:
            inner = arg.func if isinstance(arg, ast.Call) else arg
            if isinstance(inner, ast.Name):
                _registered.add(inner.id)
c.true("the registry sweep is live (%d registered)" % len(_registered), len(_registered) > 10)

_modules = sorted(f for f in os.listdir("game") if f.endswith(".py") and f.startswith("green_tide_"))
c.eq("the Green Tide module sweep is live", len(_modules), 3)
_with_label = []
for _file in _modules:
    _tree = ast.parse(io.open(os.path.join("game", _file), encoding="utf-8").read())
    for _cls in (n for n in _tree.body if isinstance(n, ast.ClassDef)):
        if "panel_label" in {f.name for f in _cls.body if isinstance(f, ast.FunctionDef)}:
            _with_label.append(_cls.name)
c.eq("all three Stratagems define panel_label()",
     sorted(_with_label), ["EreWeGoController", "MobMentalityController", "UnbridledCarnageController"])
c.eq("...and every one of them is on main.py's registry", sorted(n for n in _with_label if n not in _registered), [])

c.finish()
