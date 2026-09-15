"""Are War Horde's panel buttons really OFFERED, and at the right moment? -
measured by drawing the real ActionPanel.

WHY THIS FILE EXISTS
--------------------
Every stratagem audit in this repo found the same structural gap: a controller
whose can_use() is right, whose effect is right, and whose button nobody had
ever seen drawn. `proactive_stratagems.add(X(` in main.py and a direct can_use()
both hold while the panel draws nothing. This renders the registry path once per
phase and asks which names came out of the button funnel.

WAR HORDE has five panel buttons - four Stratagems and one Enhancement ability -
and two reactive Stratagems (Breakin' Heads, Orks Is Never Beaten):

    Da Boss is Watchin' (no CP)   "In your Movement phase" - an Enhancement
    Fungus-Fuel Injection (1CP)   "Your Movement phase ... selected to move"
    Close-Range Dakka (1CP)       "Your Shooting phase ... selected to shoot"
    Hit 'Em Harder (1CP)          "Fight phase ... selected to fight"
    Mow 'Em Down (1CP)            "Fight phase ... that made a charge move"

The two Fight-phase WHENs have NO "your", and that is measurable at the real
panel: MovementController.can_select() admits both players in the Fight phase
(12.02/12.04), so both buttons must appear in the OPPONENT's Fight phase too -
section 2. Every other absence in the other player's turn is asked at can_use(),
because outside the Fight phase select() refuses the unit.

WHAT EACH SECTION IS FOR, and the things without which this measures nothing:
  0. LIVENESS - every render reached _draw_movement_ui() with a unit selected,
     and an empty registry draws no War Horde button.
  1. THE PHASE MATRIX - each button for each unit it can target, in all five
     phases; plus the TARGET negatives (never for a unit it cannot target).
  3. THE DETACHMENT GATE AT THE PANEL.
  4. THE PRINTED CLAUSES as negatives, and the CP gate - which the no-CP Da Boss
     button is the counter-proof of.
  5. THE RESETS, each isolated: after a purchase both rule 15.01 and the grant's
     own mark refuse it, so one reset alone must leave the button gone.
  6. THE CLICK REALLY PAYS.
  7. LABEL AGAINST CORPUS.
  8. WHICH War Horde classes belong on the panel, by AST.

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
from game import attached_units, config, enhancements as E, maps, riled_up, rules_text  # noqa: E402
from game import enh_da_boss_is_watchin as boss                      # noqa: E402
from game import horde_close_range_dakka as crd                      # noqa: E402
from game import horde_fungus_fuel_injection as ffi                  # noqa: E402
from game import horde_hit_em_harder as hit                          # noqa: E402
from game import horde_mow_em_down as mow                            # noqa: E402
from game.command_points import CommandPointManager                  # noqa: E402
from game.decision import DecisionManager                            # noqa: E402
from game.dice import DiceManager                                    # noqa: E402
from game.game_state import GameState                                # noqa: E402
from game.movement import MovementController                         # noqa: E402
from game.proactive_stratagems import ProactiveStratagems            # noqa: E402
from game.shooting import ShootingController                         # noqa: E402
from game.stratagems import StratagemController                      # noqa: E402
from game.turn import (PHASES, PHASE_FIGHT, PHASE_MOVEMENT,          # noqa: E402
                       PHASE_SHOOTING, TurnTracker)
from game.ui.action_panel import ActionPanel                         # noqa: E402

from game.factions import orks as ork                                # noqa: E402

c = Checks("War Horde panel buttons")

pygame.init()
pygame.display.set_mode((1200, 900))

HUMAN = "Player 1"
FOE = "Player 2"
ROUND = 2

WH = dict(WAR_HORDE_PLAYERS=(HUMAN, FOE))
NO_WH = dict(WAR_HORDE_PLAYERS=())

M2 = maps.get("map2")
maps.apply_to_config(M2)

BOSS = boss.DA_BOSS_IS_WATCHIN
FUEL = ffi.FUNGUS_FUEL_NAME
DAKKA = crd.CLOSE_RANGE_DAKKA_NAME
HIT = hit.HIT_EM_HARDER_NAME
MOW = mow.MOW_EM_DOWN_NAME
NAMES = (BOSS, FUEL, DAKKA, HIT, MOW)

# TRANSCRIBED from rules/orks/detachments/War Horde.md, deliberately not
# imported. `own`: the phases the printed WHEN says "your" about; `any`: the
# phases it names without an owner.
WHEN = {
    BOSS: dict(own=frozenset({PHASE_MOVEMENT}), any=frozenset()),
    FUEL: dict(own=frozenset({PHASE_MOVEMENT}), any=frozenset()),
    DAKKA: dict(own=frozenset({PHASE_SHOOTING}), any=frozenset()),
    HIT: dict(own=frozenset(), any=frozenset({PHASE_FIGHT})),
    MOW: dict(own=frozenset(), any=frozenset({PHASE_FIGHT})),
}
# Which of the two board units each button can target: the Warboss-led Boyz
# carry Da Boss is Watchin' and ranged weapons; the Battlewagon is a VEHICLE
# that charged and has no ranged weapon.
APPLIES = {(BOSS, "led"), (DAKKA, "led"), (HIT, "led"),
           (FUEL, "wagon"), (HIT, "wagon"), (MOW, "wagon")}


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


def cluster(squad, point, spacing=1.35, per_row=4):
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


def build_board():
    """A fresh map2 board, both units deep in your deployment zone and nowhere
    near an enemy - the stubs below answer the engagement questions, so no
    button is refused for a geometric reason the matrix is not about."""
    B.clear()
    st = GameState()
    M2.build(st)
    own = next(z for z in st.deployment_zones if z.owner == HUMAN)
    points = [(x, y) for y in [v * 0.5 for v in range(2, 88)] for x in [v * 0.5 for v in range(2, 120)]
              if own.contains_circle(x, y, 5.0)]
    boyz = tk.build(ork.BOYZ, HUMAN, name="1 Boyz 1")
    warboss = tk.build(ork.WARBOSS, HUMAN, name="1 Warboss 1")
    led = attached_units.attach(warboss, boyz)
    E.grant(led, BOSS, model=next(m for m in led.models if m.profile.character))
    B["led"] = cluster(led, points[0])
    wagon = tk.build(ork.BATTLEWAGON, HUMAN, name="1 Battlewagon 1")
    wagon.charged_this_turn = True
    far = next(p for p in points if abs(p[0] - points[0][0]) + abs(p[1] - points[0][1]) > 12.0)
    B["wagon"] = cluster(wagon, far)
    B["state"] = st
    ALL_TOKENS[:] = [m for key in ("led", "wagon") for m in B[key].models]
    for model in ALL_TOKENS:
        st.add_token(model)
    return B


def horde(sc=None, cp=10):
    """The five War Horde panel controllers on one registry, sharing a
    StratagemController so rule 15.01 binds them the way it does in a game.
    The fight/shooting/movement collaborators are stubs holding exactly the
    ledgers the printed WHENs read."""
    sc = sc if sc is not None else strat(cp)
    fight = SimpleNamespace(fought_squad_ids=set(), fighting_squad=None)
    fight.is_eligible_to_fight = lambda squad: squad not in fight.fought_squad_ids
    shoot = SimpleNamespace(active_squad=None, shot_squad_ids=set())
    shoot.can_shoot = lambda squad: squad not in shoot.shot_squad_ids
    mover = SimpleNamespace(moved_squad_ids=set(), advanced_squad_ids=set())
    built = {
        BOSS: boss.DaBossIsWatchinController(squads_provider=lambda: [B["led"], B["wagon"]],
                                             game_log=tk.Log()),
        FUEL: ffi.FungusFuelInjectionController(sc, movement_controller=mover, game_log=tk.Log()),
        DAKKA: crd.CloseRangeDakkaController(sc, shooting_controller=shoot, game_log=tk.Log()),
        HIT: hit.HitEmHarderController(sc, fight_controller=fight, game_log=tk.Log()),
        MOW: mow.MowEmDownController(sc, fight_controller=fight, game_log=tk.Log()),
    }
    registry = ProactiveStratagems()
    for name in NAMES:
        registry.add(built[name])
    return dict(sc=sc, fight=fight, shoot=shoot, mover=mover, built=built, registry=registry)


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


def horde_names(names):
    return [n for n in names if n in NAMES]


# ==========================================================================
print("=== 0. the render really produced a panel ===")
# ==========================================================================

with settings_as(**WH):
    build_board()
    rig = horde()
    for _phase in PHASES:
        for _key in ("led", "wagon"):
            _l, _n, _b, _ok = render(B[_key], _phase, rig)
            c.true("%s / %s: a unit was selected AND the unit screen was drawn" % (_phase, _key), _ok)
    _labels_m, _n, _b, _ok = render(B["led"], PHASE_MOVEMENT, rig)
    c.true("the movement screen drew its ordinary Move button", any(lab.startswith("Move") for lab in _labels_m))
    _l, _names_empty, _b, _ok = render(B["wagon"], PHASE_FIGHT, rig, registry=ProactiveStratagems())
    c.eq("with an EMPTY registry no War Horde button is drawn, even in the right phase",
         horde_names(_names_empty), [])


# ==========================================================================
print("=== 1. the phase matrix: 5 buttons x 2 units x 5 phases, your turn ===")
# ==========================================================================

with settings_as(**WH):
    for _name in NAMES:
        for _key in ("led", "wagon"):
            for _phase in PHASES:
                build_board()
                rig = horde()
                _l, names, _b, _ok = render(B[_key], _phase, rig)
                _want = (_name, _key) in APPLIES and _phase in phases_for(_name)
                c.eq("%s for the %s in %s" % (_name, _key, _phase), _name in names, _want)


# ==========================================================================
print("=== 2. whose phase ===")
# ==========================================================================

with settings_as(**WH):
    for _name, _key in ((HIT, "led"), (HIT, "wagon"), (MOW, "wagon")):
        build_board()
        rig = horde()
        _l, names, _b, _ok = render(B[_key], PHASE_FIGHT, rig, owner=FOE)
        c.true("(live) the panel selected the %s in the opponent's Fight phase" % _key, _ok)
        c.true("%s IS offered in the OPPONENT's Fight phase" % _name, _name in names)
    for _name, _key, _phase in ((BOSS, "led", PHASE_MOVEMENT), (FUEL, "wagon", PHASE_MOVEMENT),
                                (DAKKA, "led", PHASE_SHOOTING)):
        build_board()
        rig = horde()
        _ctrl = rig["built"][_name]
        _ctrl.turn_tracker = turn_at(_phase, FOE)
        c.eq("%s refuses the OPPONENT's %s phase" % (_name, _phase), _ctrl.can_use(B[_key]), False)
        _ctrl.turn_tracker = turn_at(_phase, HUMAN)
        c.eq("...and accepts your own (the counter-proof)", _ctrl.can_use(B[_key]), True)


# ==========================================================================
print("=== 3. the detachment gate, AT THE PANEL ===")
# ==========================================================================

with settings_as(**NO_WH):
    for _phase in PHASES:
        for _key in ("led", "wagon"):
            build_board()
            rig = horde()
            _l, names, _b, _ok = render(B[_key], _phase, rig)
            c.eq("no War Horde, no War Horde button (%s, %s)" % (_phase, _key), horde_names(names), [])


# ==========================================================================
print("=== 4. the printed clauses and the CP gate, as negatives ===")
# ==========================================================================

with settings_as(**WH):
    build_board()
    rig = horde()
    rig["mover"].moved_squad_ids.add(B["wagon"])
    _l, names, _b, _ok = render(B["wagon"], PHASE_MOVEMENT, rig)
    c.eq("Fungus-Fuel: gone once the unit has moved", FUEL in names, False)

    build_board()
    rig = horde()
    rig["shoot"].shot_squad_ids.add(B["led"])
    _l, names, _b, _ok = render(B["led"], PHASE_SHOOTING, rig)
    c.eq("Close-Range Dakka: gone once the unit has shot", DAKKA in names, False)
    build_board()
    rig = horde()
    rig["shoot"].active_squad = B["led"]
    _l, names, _b, _ok = render(B["led"], PHASE_SHOOTING, rig)
    c.eq("...and while it is shooting", DAKKA in names, False)

    build_board()
    rig = horde()
    rig["fight"].fought_squad_ids.add(B["wagon"])
    _l, names, _b, _ok = render(B["wagon"], PHASE_FIGHT, rig)
    c.eq("Hit 'Em Harder and Mow 'Em Down: gone once the unit has fought",
         [n for n in names if n in (HIT, MOW)], [])

    build_board()
    B["wagon"].charged_this_turn = False
    rig = horde()
    _l, names, _b, _ok = render(B["wagon"], PHASE_FIGHT, rig)
    c.eq("Mow 'Em Down: gone for a vehicle that did not charge", MOW in names, False)
    c.true("...while Hit 'Em Harder stays (the counter-proof)", HIT in names)

    build_board()
    rig = horde(cp=0)
    _l, names, _b, _ok = render(B["led"], PHASE_MOVEMENT, rig)
    c.true("with 0CP Da Boss is Watchin' is still drawn - it costs no CP", BOSS in names)
    _l, names, _b, _ok = render(B["wagon"], PHASE_MOVEMENT, rig)
    c.eq("...while Fungus-Fuel Injection (1CP) is not", FUEL in names, False)


# ==========================================================================
print("=== 5. the resets, each isolated ===")
# ==========================================================================

with settings_as(**WH):
    build_board()
    rig = horde()
    _l, names, buttons, _ok = render(B["led"], PHASE_FIGHT, rig)
    c.true("Hit 'Em Harder is on the panel before any purchase", HIT in names)
    c.true("...pressed", press(HIT, buttons))
    _l, names, _b, _ok = render(B["led"], PHASE_FIGHT, rig)
    c.eq("...and gone after it", HIT in names, False)
    rig["sc"].reset_phase()
    _l, names, _b, _ok = render(B["led"], PHASE_FIGHT, rig)
    c.eq("15.01's reset ALONE leaves it gone - the unit still carries the grant", HIT in names, False)
    _l, names, _b, _ok = render(B["wagon"], PHASE_FIGHT, rig)
    c.true("...while another unit may buy it again", HIT in names)
    hit.reset_phase([B["led"], B["wagon"]])
    _l, names, _b, _ok = render(B["led"], PHASE_FIGHT, rig)
    c.true("...and the grant's own end-of-phase reset brings it back", HIT in names)

    build_board()
    rig = horde()
    _l, names, buttons, _ok = render(B["wagon"], PHASE_MOVEMENT, rig)
    c.true("Fungus-Fuel Injection is on the panel before any purchase", FUEL in names)
    press(FUEL, buttons)
    ffi.reset_phase([B["wagon"]])
    _l, names, _b, _ok = render(B["wagon"], PHASE_MOVEMENT, rig)
    c.eq("its own reset ALONE leaves it gone - rule 15.01 still refuses", FUEL in names, False)
    rig["sc"].reset_phase()
    _l, names, _b, _ok = render(B["wagon"], PHASE_MOVEMENT, rig)
    c.true("...and with 15.01's reset too, it is back", FUEL in names)

    build_board()
    rig = horde()
    _l, names, buttons, _ok = render(B["led"], PHASE_MOVEMENT, rig)
    c.true("Da Boss is Watchin' is on the panel before it is used", BOSS in names)
    press(BOSS, buttons)
    rig["sc"].reset_phase()
    _l, names, _b, _ok = render(B["led"], PHASE_MOVEMENT, rig)
    c.eq("...once per BATTLE: no phase reset brings it back", BOSS in names, False)


# ==========================================================================
print("=== 6. the click really pays ===")
# ==========================================================================

with settings_as(**WH):
    for _name, _key, _phase, _cp, _effect in (
            (FUEL, "wagon", PHASE_MOVEMENT, ffi.FUNGUS_FUEL_CP, ffi.is_active),
            (DAKKA, "led", PHASE_SHOOTING, crd.CLOSE_RANGE_DAKKA_CP, crd.is_active),
            (HIT, "led", PHASE_FIGHT, hit.HIT_EM_HARDER_CP, hit.is_active),
            (MOW, "wagon", PHASE_FIGHT, mow.MOW_EM_DOWN_CP, mow.is_active)):
        build_board()
        rig = horde()
        _l, names, buttons, _ok = render(B[_key], _phase, rig)
        _before = rig["sc"].command_points.cp[HUMAN]
        c.true("pressing %s" % _name, press(_name, buttons))
        c.eq("...spends its printed %dCP" % _cp, _before - rig["sc"].command_points.cp[HUMAN], _cp)
        c.true("...and grants the unit its effect", _effect(B[_key]))

    build_board()
    rig = horde()
    _l, names, buttons, _ok = render(B["led"], PHASE_MOVEMENT, rig)
    _before = rig["sc"].command_points.cp[HUMAN]
    c.true("pressing Da Boss is Watchin'", press(BOSS, buttons))
    c.eq("...spends no CP", rig["sc"].command_points.cp[HUMAN], _before)
    c.true("...and the unit is riled up", riled_up.is_riled_up(B["led"]))


# ==========================================================================
print("=== 7. what the corpus prints, and what the panel draws ===")
# ==========================================================================

_CORPUS = rules_text.detachment_stratagems("ORKS", "War Horde")
c.eq("the printed detachment was read - six Stratagems", len(_CORPUS), 6)
for _name, _key, _phase in ((FUEL, "wagon", PHASE_MOVEMENT), (DAKKA, "led", PHASE_SHOOTING),
                            (HIT, "led", PHASE_FIGHT), (MOW, "wagon", PHASE_FIGHT)):
    with settings_as(**WH):
        build_board()
        rig = horde()
        _labels_s, names, _b, _ok = render(B[_key], _phase, rig)
    _label = next((lab for lab in _labels_s if lab.startswith(_name + " (")), None)
    c.true("%s: a label was drawn" % _name, _label is not None)
    found = rules_text.stratagem_named("ORKS", ["War Horde"], _name)
    c.true("...the DRAWN name resolves to the printed Stratagem",
           found is not None and found.name.lower() == _name.lower())
    _printed_cp = re.search(r"(\d+)", str(found.cost)) if found is not None else None
    _drawn_cp = re.search(r"\((\d+) CP\)", _label or "")
    c.eq("...and the label's cost is the printed cost",
         _drawn_cp.group(1) if _drawn_cp else None, _printed_cp.group(1) if _printed_cp else None)
c.eq("Da Boss is Watchin' is NOT a Stratagem in the corpus",
     rules_text.stratagem_named("ORKS", ["War Horde"], BOSS), None)
_WH_MD = io.open(os.path.join("rules", "orks", "detachments", "War Horde.md"), encoding="utf-8").read()
c.true("...it is printed as an Enhancement", "### Da Boss is Watchin' - 25 pts" in _WH_MD)


# ==========================================================================
print("=== 8. which War Horde classes belong on the panel, by AST ===")
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

_modules = sorted(f for f in os.listdir("game")
                  if f.endswith(".py") and (f.startswith("horde_") or f in (
                      "enh_da_boss_is_watchin.py", "enh_headwoppas_killchoppa.py",
                      "enh_kunnin_but_brutal.py", "enh_follow_me_ladz.py")))
c.eq("the War Horde module sweep is live", len(_modules), 10)
_with_label, _reactive = [], []
for _file in _modules:
    _tree = ast.parse(io.open(os.path.join("game", _file), encoding="utf-8").read())
    for _cls in (n for n in _tree.body if isinstance(n, ast.ClassDef)):
        _methods = {f.name for f in _cls.body if isinstance(f, ast.FunctionDef)}
        if "panel_label" in _methods:
            _with_label.append(_cls.name)
        elif "maybe_offer" in _methods or "on_became_battle_shocked" in _methods:
            _reactive.append(_cls.name)
c.eq("exactly the five panel buttons define panel_label()",
     sorted(_with_label), ["CloseRangeDakkaController", "DaBossIsWatchinController",
                           "FungusFuelInjectionController", "HitEmHarderController", "MowEmDownController"])
c.eq("...and every one of them is on main.py's registry", sorted(n for n in _with_label if n not in _registered), [])
c.eq("the two reactive Stratagems are found by their hooks",
     sorted(_reactive), ["BreakinHeadsController", "OrksIsNeverBeatenController"])
c.eq("...and neither is on the registry", sorted(n for n in _reactive if n in _registered), [])

c.finish()
