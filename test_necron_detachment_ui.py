"""Are the Necron detachment panel Stratagems really OFFERED, and at the right
moment? - measured by drawing the real ActionPanel.

WHY THIS FILE EXISTS
--------------------
Three stratagem audits (Aeldari, T'au, Necrons) found the same structural gap:
a controller whose can_use() is right, whose effect is right, and whose button
nobody had ever seen drawn. `proactive_stratagems.add(X(` in main.py and a direct
can_use() call both hold perfectly while the panel draws nothing at all.

The Necron detachments added after Awakened Dynasty put their panel Stratagems
on game/proactive_stratagems.py, so they reach the panel through the registry
rather than as bespoke keyword arguments. This file renders that path, once per
phase, and asks which Stratagem names came out of the button funnel. It GROWS
by one block per detachment; the Canoptek Court is the first.

THE CANOPTEK COURT has two panel buttons and four reactive Stratagems:

    Cynosure of Eradication (2CP)  "The start of your Shooting phase or the
                                    start of the Fight phase."
    Solar Pulse (1CP)              "Start of your Shooting phase."

Cynosure's second half has NO "your", and that is measurable at the real panel:
MovementController.can_select() admits both players in the Fight phase
(12.02/12.04), so the button must appear in the OPPONENT's Fight phase too -
section 2. Every other absence in another player's turn is asked at can_use(),
because outside the Fight phase select() refuses the unit and a panel that draws
nothing proves nothing.

WHAT EACH SECTION IS FOR, and the three things without which this measures
nothing while staying green:
  0. LIVENESS - every render reached _draw_movement_ui() with a unit selected,
     and an empty registry draws no Court button. A render that fell into
     another _draw_dispatch branch draws zero buttons and satisfies every
     absence check by inspecting nothing.
  1. THE PHASE MATRIX - each button in all five phases; Cynosure has three
     negatives, Solar Pulse four.
  3. THE DETACHMENT GATE AT THE PANEL - without it section 1 proves only that
     buttons appear, not that they appear BECAUSE the detachment is fielded.
  5. THE LEDGER RESETS, each isolated from the other: after a purchase BOTH
     rule 15.01 and the Stratagem's own per-phase mark refuse it, so resetting
     one alone must leave the button gone and resetting both must bring it back.
     Asked the other way round, one reset could hide behind the other.
  6. THE CLICK REALLY PAYS - Solar Pulse charges only after its objective prompt
     is answered, so a test that stops at the click reports "bought and did
     nothing"; drain() answers it.

THE BOARD IS REBUILT PER SECTION. Buying either Stratagem applies it and leaves
a mark (court_cynosure_active on the squad, the pulsed objective on the
controller), so a section that clicks would poison every later render of the
same unit - which surfaces as "the button is gone" somewhere unrelated.
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
from game import attached_units, config, maps, rules_text            # noqa: E402
from game import court_cynosure_of_eradication as cyn                # noqa: E402
from game import court_power_matrix as pm                            # noqa: E402
from game import court_solar_pulse as solar                          # noqa: E402
from game import fight as fight_module                               # noqa: E402
from game.command_points import CommandPointManager                  # noqa: E402
from game.decision import DecisionManager                            # noqa: E402
from game.dice import DiceManager                                    # noqa: E402
from game.game_state import GameState                                # noqa: E402
from game.mission_context import objective_centre                    # noqa: E402
from game.movement import MovementController                         # noqa: E402
from game.proactive_stratagems import ProactiveStratagems            # noqa: E402
from game.shooting import ShootingController                         # noqa: E402
from game.stratagems import StratagemController                      # noqa: E402
from game.turn import (PHASES, PHASE_FIGHT, PHASE_SHOOTING,          # noqa: E402
                       TurnTracker)
from game.ui.action_panel import ActionPanel                         # noqa: E402

from game.factions import necrons as nec                             # noqa: E402

c = Checks("Necron detachment Stratagem buttons")

pygame.init()
pygame.display.set_mode((1200, 900))

HUMAN = "Player 1"
FOE = "Player 2"
ROUND = 2

COURT = dict(CANOPTEK_COURT_PLAYERS=(HUMAN,))
NO_COURT = dict(CANOPTEK_COURT_PLAYERS=())

M2 = maps.get("map2")
maps.apply_to_config(M2)

CYN = cyn.CYNOSURE_NAME
SOLAR = solar.SOLAR_PULSE_NAME
COURT_NAMES = (CYN, SOLAR)

# TRANSCRIBED from rules/necrons/detachments/Canoptek Court.md, deliberately not
# imported: the suite and the modules are then two independent statements of
# one table. `own` is the set of phases the printed WHEN says "your" about;
# `any` the phases it names without an owner.
WHEN = {
    CYN: dict(own=frozenset({PHASE_SHOOTING}), any=frozenset({PHASE_FIGHT})),
    SOLAR: dict(own=frozenset({PHASE_SHOOTING}), any=frozenset()),
}


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


def cluster(squad, point, spacing=1.3, per_row=4):
    n = len(squad.models)
    rows = (n + per_row - 1) // per_row
    cols = min(n, per_row)
    for i, model in enumerate(squad.models):
        r, col = divmod(i, per_row)
        model.x_in = point[0] + (col - (cols - 1) / 2.0) * spacing
        model.y_in = point[1] + (r - (rows - 1) / 2.0) * spacing
    return squad


def led_warriors(name="1 Necron Warriors 1"):
    """A Technomancer supporting Necron Warriors: a CRYPTEK unit (19.03)."""
    warriors = tk.build(nec.NECRON_WARRIORS, HUMAN, name=name)
    tech = tk.build(nec.TECHNOMANCER, HUMAN,
                    name=name.replace("Necron Warriors", "Technomancer"))
    return attached_units.attach(tech, warriors)


# ------------------------------------------------------------------- the board

B = {}
ALL_TOKENS = []


def build_board():
    """A fresh map2 board. ALL_TOKENS is mutated IN PLACE, because the panel's
    MovementController is handed the list itself.

    The Wraiths (CANOPTEK) stand deep in your deployment zone; the CRYPTEK unit
    stands on your home objective, which is also in your zone. Your zone is
    ALWAYS inside the Power Matrix, so neither is refused for a region reason
    the phase matrix is not about, and the objective is within Solar Pulse's 18"
    of the Technomancer by construction.
    """
    B.clear()
    st = GameState()
    M2.build(st)
    zones = {z.owner: z for z in st.deployment_zones}
    own = zones[HUMAN]
    home = next(o for o in st.objectives if own.contains_point(*objective_centre(o)))
    hx, hy = objective_centre(home)
    deep = next((x, y) for y in [v * 0.5 for v in range(2, 88)]
                for x in [v * 0.5 for v in range(2, 120)]
                if own.contains_circle(x, y, 4.5) and ((x - hx) ** 2 + (y - hy) ** 2) ** 0.5 > 15.0)
    B["state"] = st
    B["own"] = own
    B["home"] = home
    B["wraiths"] = cluster(tk.build(nec.CANOPTEK_WRAITHS, HUMAN, name="1 Canoptek Wraiths 1"),
                           deep, spacing=2.5, per_row=3)
    B["led"] = cluster(led_warriors(), (hx, hy), spacing=1.3, per_row=6)
    ALL_TOKENS[:] = [m for key in ("wraiths", "led") for m in B[key].models]
    for model in ALL_TOKENS:
        st.add_token(model)
    for objective in st.objectives:
        objective.controlled_by = None
    return B


build_board()


def court(sc=None, tracker=None, cp=10):
    """Both Court panel controllers on one registry, sharing a
    StratagemController so rule 15.01 binds them the way it does in a game.

    Each gets its OWN shooting/fight ledger stubs: those are what their printed
    "the START of ... phase" reads, and the panel's real ShootingController is a
    separate object that never shoots here."""
    sc = sc if sc is not None else strat(cp)
    shoot = SimpleNamespace(active_squad=None, shot_squad_ids=set())
    fight = SimpleNamespace(state=fight_module.NOT_STARTED, fought_squad_ids=set())
    matrix = pm.PowerMatrixController(game_state=B["state"], turn_tracker=tracker)
    decision = DecisionManager()
    built = {
        CYN: cyn.CynosureOfEradicationController(
            sc, turn_tracker=tracker, shooting_controller=shoot, fight_controller=fight,
            power_matrix=matrix, game_log=tk.Log()),
        SOLAR: solar.SolarPulseController(
            sc, turn_tracker=tracker, shooting_controller=shoot, game_state=B["state"],
            decision_manager=decision, game_log=tk.Log()),
    }
    registry = ProactiveStratagems()
    for name in COURT_NAMES:
        registry.add(built[name])
    return dict(sc=sc, shoot=shoot, fight=fight, matrix=matrix, decision=decision,
                built=built, registry=registry)


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
    """Draw the real panel for `squad` in `phase`; (labels, names, buttons).

    mover.select() is not optional: _draw_movement_ui() asks the registry about
    the SELECTED squad and no other, so a render without a selection draws the
    no-selection screen and every absence would pass by measuring nothing."""
    tracker = turn_at(phase, owner)
    for ctrl in rig["built"].values():
        ctrl.turn_tracker = tracker
    rig["matrix"].turn_tracker = tracker
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
            mover.selected_squad is squad)


def press(name, buttons):
    """Click the drawn button; True if there was one. RETURNS rather than
    raises when there is none - a probe that removes a button has to turn this
    file RED, not crash it."""
    rect = next((r for r, n in _panel._stratagem_buttons if n == name), None)
    if rect is None:
        return False
    callback = next((cb for r, cb in buttons if r == rect), None)
    if callback is None:
        return False
    callback()
    return True


def drain(rig, pick=0, limit=4):
    """Answer the follow-up prompt a Stratagem raises AFTER its button."""
    steps = 0
    dm = rig["decision"]
    while dm.is_pending and steps < limit:
        options = dm.options or []
        dm.choose(pick if pick >= 0 else len(options) + pick)
        steps += 1
    return steps


# ==========================================================================
print("=== 0. the render really produced a panel ===")
# ==========================================================================

with settings_as(**COURT):
    build_board()
    rig = court()
    c.true("(live) the Wraiths stand wholly within the Power Matrix",
           pm.unit_wholly_within(B["wraiths"], rig["matrix"]))
    c.true("(live) ...and so does the CRYPTEK unit", pm.unit_wholly_within(B["led"], rig["matrix"]))
    c.true("(live) the CRYPTEK unit's home objective is within Solar Pulse's reach",
           B["home"] in rig["built"][SOLAR].objectives_for(B["led"]))
    c.true("(live) the Wraiths are a Court unit with no CRYPTEK model",
           pm.is_court_unit(B["wraiths"]) and not rig["built"][SOLAR].cryptek_models(B["wraiths"]))
    for _phase in PHASES:
        for _key in ("wraiths", "led"):
            _l, _n, _b, _sel = render(B[_key], _phase, rig)
            c.true("%s / %s: a unit was selected AND the unit screen was drawn" % (_phase, _key),
                   _sel and bool(_reached))
    _labels_m, _n, _b, _sel = render(B["wraiths"], "Movement", rig)
    c.true("the movement screen drew its ordinary Move button",
           any(lab.startswith("Move") for lab in _labels_m))
    _l, _names_empty, _b, _sel = render(B["led"], PHASE_SHOOTING, rig, registry=ProactiveStratagems())
    c.eq("with an EMPTY registry no Court button is drawn, even in the right phase",
         [n for n in _names_empty if n in COURT_NAMES], [])


# ==========================================================================
print("=== 1. the phase matrix: 2 Stratagems x 5 phases, your turn ===")
# ==========================================================================

with settings_as(**COURT):
    for _name, _key in ((CYN, "wraiths"), (CYN, "led"), (SOLAR, "led")):
        for _phase in PHASES:
            build_board()
            rig = court()
            _l, names, _b, _sel = render(B[_key], _phase, rig)
            c.eq("%s for the %s in %s" % (_name, _key, _phase),
                 _name in names, _phase in phases_for(_name))


# ==========================================================================
print("=== 2. whose phase ===")
# ==========================================================================

with settings_as(**COURT):
    # Cynosure prints "the start of THE Fight phase" - no owner - and the
    # Fight phase is the one place the real panel admits the other player's
    # turn, so its missing owner clause shows here.
    build_board()
    rig = court()
    _l, names, _b, _sel = render(B["wraiths"], PHASE_FIGHT, rig, owner=FOE)
    c.true("(live) the panel selected the unit in the opponent's Fight phase", _sel and bool(_reached))
    c.true("Cynosure IS offered at the start of the OPPONENT's Fight phase", CYN in names)
    _l, names, _b, _sel = render(B["led"], PHASE_FIGHT, rig, owner=FOE)
    c.eq("...while Solar Pulse is not (it prints no Fight phase at all)", SOLAR in names, False)

    # "YOUR Shooting phase": outside the Fight phase select() refuses a unit
    # that is not the turn owner's, so the refusal is asked at can_use().
    for _name, _key in ((CYN, "wraiths"), (SOLAR, "led")):
        build_board()
        rig = court()
        for ctrl in rig["built"].values():
            ctrl.turn_tracker = turn_at(PHASE_SHOOTING, FOE)
        c.eq("%s refuses the OPPONENT's Shooting phase" % _name,
             rig["built"][_name].can_use(B[_key]), False)
        for ctrl in rig["built"].values():
            ctrl.turn_tracker = turn_at(PHASE_SHOOTING, HUMAN)
        c.eq("...and accepts your own (the counter-proof)", rig["built"][_name].can_use(B[_key]), True)


# ==========================================================================
print("=== 3. the detachment gate, AT THE PANEL ===")
# ==========================================================================

with settings_as(**NO_COURT):
    for _phase in PHASES:
        for _key in ("wraiths", "led"):
            build_board()
            rig = court()
            _l, names, _b, _sel = render(B[_key], _phase, rig)
            c.eq("no Canoptek Court, no Court button (%s, %s)" % (_phase, _key),
                 [n for n in names if n in COURT_NAMES], [])


# ==========================================================================
print("=== 4. the printed TARGET and 'start of the phase' clauses, as negatives ===")
# ==========================================================================

with settings_as(**COURT):
    build_board()
    rig = court()
    _l, names, _b, _sel = render(B["wraiths"], PHASE_SHOOTING, rig)
    c.true("the Wraiths get Cynosure in your Shooting phase", CYN in names)
    c.eq("...but never Solar Pulse - no CRYPTEK model", SOLAR in names, False)

    # "while that unit is wholly within your Power Matrix": one base out.
    _straddle = next((x, y) for y in [v * 0.5 for v in range(2, 88)]
                     for x in [v * 0.5 for v in range(2, 120)]
                     if 0.2 <= B["own"].shape.signed_distance(x, y) <= 0.8)
    _saved = (B["wraiths"].models[0].x_in, B["wraiths"].models[0].y_in)
    B["wraiths"].models[0].x_in, B["wraiths"].models[0].y_in = _straddle
    c.eq("(live) a straddling base takes the unit out of the matrix",
         pm.unit_wholly_within(B["wraiths"], rig["matrix"]), False)
    _l, names, _b, _sel = render(B["wraiths"], PHASE_SHOOTING, rig)
    c.eq("...and Cynosure is gone from the panel", CYN in names, False)
    B["wraiths"].models[0].x_in, B["wraiths"].models[0].y_in = _saved

    # "The START of your Shooting phase": once any unit has shot, neither.
    build_board()
    rig = court()
    rig["shoot"].shot_squad_ids.add(B["wraiths"])
    _l, names, _b, _sel = render(B["led"], PHASE_SHOOTING, rig)
    c.eq("once a unit has shot, neither is offered",
         [n for n in names if n in COURT_NAMES], [])
    rig["shoot"].shot_squad_ids.clear()
    rig["shoot"].active_squad = B["wraiths"]
    _l, names, _b, _sel = render(B["led"], PHASE_SHOOTING, rig)
    c.eq("...nor while one is shooting", [n for n in names if n in COURT_NAMES], [])

    # "The start of the Fight phase": the Fight step has begun.
    build_board()
    rig = court()
    rig["fight"].state = fight_module.SELECTING
    _l, names, _b, _sel = render(B["wraiths"], PHASE_FIGHT, rig)
    c.eq("once the Fight step has begun, Cynosure is gone", CYN in names, False)
    rig["fight"].state = fight_module.NOT_STARTED
    rig["fight"].fought_squad_ids.add(B["led"])
    _l, names, _b, _sel = render(B["wraiths"], PHASE_FIGHT, rig)
    c.eq("...and once any unit has fought", CYN in names, False)

    # Not enough CP: 2CP printed.
    build_board()
    rig = court(cp=1)
    _l, names, _b, _sel = render(B["led"], PHASE_SHOOTING, rig)
    c.eq("with 1CP, Cynosure (2CP) is not drawn", CYN in names, False)
    c.true("...while Solar Pulse (1CP) still is - the counter-proof", SOLAR in names)


# ==========================================================================
print("=== 5. the two resets, each isolated ===")
# ==========================================================================

with settings_as(**COURT):
    build_board()
    rig = court()
    _l, names, buttons, _sel = render(B["wraiths"], PHASE_SHOOTING, rig)
    c.true("Cynosure is on the panel before any purchase", CYN in names)
    c.true("...pressed", press(CYN, buttons))
    _l, names, _b, _sel = render(B["wraiths"], PHASE_SHOOTING, rig)
    c.eq("...and gone after it", CYN in names, False)
    rig["sc"].reset_phase()
    _l, names, _b, _sel = render(B["wraiths"], PHASE_SHOOTING, rig)
    c.eq("15.01's ledger reset ALONE leaves it gone - the unit still carries the grant",
         CYN in names, False)
    _l, names, _b, _sel = render(B["led"], PHASE_SHOOTING, rig)
    c.true("...while another unit may buy it again", CYN in names)
    cyn.reset_phase([B["wraiths"], B["led"]])
    _l, names, _b, _sel = render(B["wraiths"], PHASE_SHOOTING, rig)
    c.true("...and the grant's own end-of-phase reset brings it back", CYN in names)

    build_board()
    rig = court()
    _l, names, buttons, _sel = render(B["led"], PHASE_SHOOTING, rig)
    c.true("Solar Pulse is on the panel before any purchase", SOLAR in names)
    press(SOLAR, buttons)
    drain(rig)
    _l, names, _b, _sel = render(B["led"], PHASE_SHOOTING, rig)
    c.eq("...and gone after it", SOLAR in names, False)
    rig["built"][SOLAR].reset_phase()
    _l, names, _b, _sel = render(B["led"], PHASE_SHOOTING, rig)
    c.eq("its own reset ALONE leaves it gone - rule 15.01 still refuses", SOLAR in names, False)
    rig["sc"].reset_phase()
    _l, names, _b, _sel = render(B["led"], PHASE_SHOOTING, rig)
    c.true("...and with 15.01's reset too, it is back", SOLAR in names)

    build_board()
    rig = court()
    _l, names, buttons, _sel = render(B["led"], PHASE_SHOOTING, rig)
    press(SOLAR, buttons)
    drain(rig)
    rig["sc"].reset_phase()
    _l, names, _b, _sel = render(B["led"], PHASE_SHOOTING, rig)
    c.eq("15.01's reset ALONE leaves Solar Pulse gone - the pulse is still set",
         SOLAR in names, False)


# ==========================================================================
print("=== 6. the click really pays ===")
# ==========================================================================

with settings_as(**COURT):
    build_board()
    rig = court()
    _l, names, buttons, _sel = render(B["wraiths"], PHASE_SHOOTING, rig)
    _before = rig["sc"].command_points.cp[HUMAN]
    c.true("pressing Cynosure", press(CYN, buttons))
    c.eq("...spends its printed 2CP", _before - rig["sc"].command_points.cp[HUMAN], cyn.CYNOSURE_CP)
    c.true("...and grants the unit [DEVASTATING WOUNDS]", cyn.is_active(B["wraiths"]))

    build_board()
    rig = court()
    _l, names, buttons, _sel = render(B["led"], PHASE_SHOOTING, rig)
    _before = rig["sc"].command_points.cp[HUMAN]
    c.true("pressing Solar Pulse", press(SOLAR, buttons))
    c.true("...asks WHICH objective first", rig["decision"].is_pending)
    c.eq("...and has spent nothing yet", rig["sc"].command_points.cp[HUMAN], _before)
    _offered = [o.get("label") for o in (rig["decision"].options or [])]
    c.true("...offering the home objective among them", B["home"].name in _offered)
    c.true("(live) the answer drained", drain(rig) >= 1)
    c.eq("...then spends its printed 1CP", _before - rig["sc"].command_points.cp[HUMAN],
         solar.SOLAR_PULSE_CP)
    c.eq("...and pulses exactly the objective that was picked",
         getattr(rig["built"][SOLAR].pulsed_objective(HUMAN), "name", None),
         _offered[0] if _offered else "<nothing offered>")

    build_board()
    rig = court()
    _l, names, buttons, _sel = render(B["led"], PHASE_SHOOTING, rig)
    _before = rig["sc"].command_points.cp[HUMAN]
    press(SOLAR, buttons)
    drain(rig, pick=-1)
    c.eq("Cancel on the objective prompt costs nothing",
         rig["sc"].command_points.cp[HUMAN], _before)
    c.eq("...and pulses nothing", rig["built"][SOLAR].pulsed_objective(HUMAN), None)
    _l, names, _b, _sel = render(B["led"], PHASE_SHOOTING, rig)
    c.true("...and the button is still there", SOLAR in names)


# ==========================================================================
print("=== 7. what the corpus prints, and what the panel draws ===")
# ==========================================================================

_CORPUS = rules_text.detachment_stratagems("NECRONS", "Canoptek Court")
c.eq("the printed detachment was read - six Stratagems", len(_CORPUS), 6)
for _name in COURT_NAMES:
    with settings_as(**COURT):
        build_board()
        rig = court()
        _key = "led"
        _labels_s, names, _b, _sel = render(B[_key], PHASE_SHOOTING, rig)
    _label = next((lab for lab in _labels_s if lab.startswith(_name + " (")), None)
    c.true("%s: a label was drawn" % _name, _label is not None)
    found = rules_text.stratagem_named("NECRONS", ["Canoptek Court"], _name)
    c.true("...the DRAWN name resolves to the printed Stratagem", found is not None)
    c.true("...the right one", found is not None and found.name.lower() == _name.lower())
    _printed_cp = re.search(r"(\d+)", str(found.cost)) if found is not None else None
    _drawn_cp = re.search(r"\((\d+) CP\)", _label or "")
    c.eq("...and the label's cost is the printed cost",
         _drawn_cp.group(1) if _drawn_cp else None, _printed_cp.group(1) if _printed_cp else None)


# ==========================================================================
print("=== 8. which Court Stratagems belong on the panel, by AST ===")
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

_court_modules = sorted(f for f in os.listdir("game") if f.startswith("court_") and f.endswith(".py"))
c.true("the Court module sweep is live (%d)" % len(_court_modules), len(_court_modules) >= 7)
_with_label, _reactive = [], []
for _file in _court_modules:
    _tree = ast.parse(io.open(os.path.join("game", _file), encoding="utf-8").read())
    for _cls in (n for n in _tree.body if isinstance(n, ast.ClassDef)):
        _methods = {f.name for f in _cls.body if isinstance(f, ast.FunctionDef)}
        if "panel_label" in _methods:
            _with_label.append(_cls.name)
        elif "maybe_offer" in _methods or "notify_model_destroyed" in _methods \
                or "on_move_finished" in _methods:
            _reactive.append(_cls.name)
c.eq("exactly the two panel Stratagems define panel_label()",
     sorted(_with_label), ["CynosureOfEradicationController", "SolarPulseController"])
c.eq("...and every one of them is on main.py's registry",
     sorted(n for n in _with_label if n not in _registered), [])
c.eq("the four reactive Stratagems are found by their hooks",
     sorted(_reactive), ["CountertemporalShiftController", "CurseOfTheCryptekController",
                         "ReactiveSubroutinesController", "SuboptimalFacadeController"])
c.eq("...and none of them is on the registry",
     sorted(n for n in _reactive if n in _registered), [])

c.finish()
