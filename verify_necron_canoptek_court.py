"""Runtime proof through the REAL main() loop that the Canoptek Court is wired.

The suites drive the Court's controllers directly and pin main.py's wiring by
AST. What neither can show is that MAIN'S objects, built by MAIN'S constructors
in MAIN'S order, are connected when the game runs - "built but never FED" has
hit this repo more than half a dozen times. So this runs selfplay.py's real
main() loop and asks main()'s own live locals three questions:

  A. THE LISTENER LIST. movement_controller.on_move_finished is fed by nine
     .append/.extend calls across main(). One of them used to be an ASSIGNMENT,
     which silently dropped every listener fed before it - Wraith Form, Higher
     Duty, the Spirit Stone, the Spirit Mark and Internal Grenade Racks never
     heard a move in a real game. Asked: is every fed listener on the live list?
  B. THE POWER MATRIX. main() stamps the latch at the start of a real phase, and
     main's ShootingController offers a CRYPTEK/CANOPTEK unit standing wholly
     within the matrix the WHOLE Hit roll. Asked of the live objects after a real
     phase change - nothing is stamped by this script.
  C. THE TWO PANEL BUTTONS reach the screen, and only in their printed phases:
     Cynosure of Eradication ("the start of your Shooting phase or the start of
     THE Fight phase" - so the opponent's Fight phase too) and Solar Pulse ("Start
     of your Shooting phase").

STAGED, each named rather than quietly faked:
  * THE NECRONS AS PLAYER 1. config ships PLAYER2_ARMY = "necrons"; a question
    about the human's buttons that does not field them as Player 1 measures the
    AI's army and reports a truthful-looking zero.
  * THE DETACHMENT, by wrapping game/detachments.apply_to_config() - it rewrites
    every detachment setting from scratch, so a flag set before it is erased. No
    shipped list fields the Canoptek Court (user decision).
  * For C only, after A and B are answered: a selected unit every frame, and the
    phase (a MockAgent run does not visit all five reliably). The phase is read
    LIVE at draw time. ENTERING THE FIGHT PHASE, the rotation also calls what
    main()'s own phase change calls there - pile_in_controller and
    fight_controller.reset_fight_phase(). Without that the fight controller
    carries `done` over from an earlier real Fight phase, and Cynosure's "start
    of the Fight phase" is refused for a reason no game produces (measured: 631
    refusals, all of them that one).

THE OPPONENT'S FIGHT PHASE IS REPORTED, NOT JUDGED, and the reason is measured
in ai/agent_driver.py's _handle_fight(): the AI begins the Fight step the moment
no Pile In is pending on EITHER side. So in the AI's Fight phase the human's
window for Cynosure is exactly as long as a human unit still owes a Pile In -
which is exactly when a human unit could fight at all. This staging engages
nobody, so whether that column fills depends only on whether a frame is drawn
before the AI's tick closes the window (measured: it sometimes is). The
owner-blind clause itself is proven at the real panel by
test_necron_detachment_ui.py section 2.

--neutralize loads main.py through an import hook with the measured seams undone
(the on_move_finished .extend back to an assignment, the stamp, the shooting
controller's matrix, and both registry registrations). The file on disk is not
touched. It must show the pre-wiring world: listeners missing, no stamp, no whole
roll, no buttons.

Usage:  python verify_necron_canoptek_court.py [map2] [frames]
        python verify_necron_canoptek_court.py map2 --neutralize
"""

import importlib.abc
import importlib.util
import os
import runpy
import sys

import pygame

from game import config, detachments
from game import court_power_matrix as pm
from game.renderer import Renderer
from game.turn import (PHASES, PHASE_CHARGE, PHASE_COMMAND, PHASE_FIGHT,
                       PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker)
from game.ui import button_style

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

HUMAN = "Player 1"
FOE = "Player 2"
SETTING = "CANOPTEK_COURT_PLAYERS"
MIN_FRAMES = 1200

# TRANSCRIBED from rules/necrons/detachments/Canoptek Court.md.
WHEN = {
    "Cynosure of Eradication": {PHASE_SHOOTING, PHASE_FIGHT},
    "Solar Pulse": {PHASE_SHOOTING},
}

#: The listeners main() feeds movement_controller.on_move_finished, by the local
#: name of the controller that owns each bound method.
FED_LISTENERS = (
    "spirit_stone_controller", "spirit_mark_controller", "higher_duty_controller",
    "wraith_form_controller", "internal_grenade_racks_controller",
    "reactive_subroutines_controller", "ishas_fury_controller",
    "path_of_the_outcast_controller", "grenade_pack_controller",
)

#: (anchor, replacement) applied to main.py's SOURCE in memory for --neutralize.
NEUTRALIZE_EDITS = (
    ("    movement_controller.on_move_finished.extend([",
     "    movement_controller.on_move_finished = (["),
    ("        power_matrix_controller.stamp_at_start_of_phase()", "        pass"),
    ("    shooting_controller.power_matrix = power_matrix_controller", "    pass"),
    ("proactive_stratagems.add(CynosureOfEradicationController(", "(CynosureOfEradicationController("),
    ("proactive_stratagems.add(SolarPulseController(", "(SolarPulseController("),
)

if NEUTRALIZE:
    _MAIN_PATH = os.path.abspath("main.py")
    with open(_MAIN_PATH, encoding="utf-8") as fh:
        _src = fh.read()
    for _anchor, _replacement in NEUTRALIZE_EDITS:
        if _src.count(_anchor) != 1:
            raise SystemExit("neutralize anchor not unique in main.py: %r (%d)"
                             % (_anchor, _src.count(_anchor)))
        _src = _src.replace(_anchor, _replacement)
    _NEUTRAL_SRC = _src

    class _NeutralLoader(importlib.abc.Loader):
        def create_module(self, spec):
            return None

        def exec_module(self, module):
            module.__file__ = _MAIN_PATH
            exec(compile(_NEUTRAL_SRC, _MAIN_PATH, "exec"), module.__dict__)

    class _NeutralFinder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path, target=None):
            if fullname != "main":
                return None
            return importlib.util.spec_from_loader("main", _NeutralLoader(), origin=_MAIN_PATH)

    sys.meta_path.insert(0, _NeutralFinder())

state = {"frames": 0, "tracker": None, "first_phase": None, "inspected": False,
         "rotating": False, "rotate": False, "selected": 0, "seen": {},
         "off_when": [], "foreign": set(), "phases": set(), "result": {}}

# ------------------------------------------------------------------- staging

_real_apply = detachments.apply_to_config


def apply_to_config(*args, **kwargs):
    out = _real_apply(*args, **kwargs)
    setattr(config, SETTING, (HUMAN,))
    return out


detachments.apply_to_config = apply_to_config

_real_tracker_init = TurnTracker.__init__


def tracker_init(self, *args, **kwargs):
    _real_tracker_init(self, *args, **kwargs)
    state["tracker"] = self


TurnTracker.__init__ = tracker_init

_real_draw_button = button_style.draw_button


def draw_button(surface, rect, label, font, hovered=False, pressed=False, accent=None):
    name = (label or "").split(" (")[0].strip()
    if state["rotating"] and name in WHEN:
        tracker = state["tracker"]
        phase = tracker.phase if tracker is not None else None
        seen = state["seen"].setdefault(name, {"frame": state["frames"], "phases": set()})
        if phase is not None:
            seen["phases"].add(phase)
            if phase not in WHEN[name]:
                state["off_when"].append((name, phase, state["frames"]))
            if tracker.turn_owner == FOE:
                state["foreign"].add((name, phase))
    return _real_draw_button(surface, rect, label, font, hovered=hovered, pressed=pressed,
                             accent=accent)


button_style.draw_button = draw_button


def _main_locals():
    frame = sys._getframe(2)
    while frame is not None and frame.f_code.co_name != "main":
        frame = frame.f_back
    return frame.f_locals if frame is not None else None


def _squads(locals_):
    game_state = locals_.get("state")
    if game_state is None or not hasattr(game_state, "all_squads"):
        return []
    return list(game_state.all_squads())


def inspect(L):
    """Questions A and B, asked of main()'s live objects."""
    result = state["result"]
    mc = L.get("movement_controller")
    owners = {id(getattr(fn, "__self__", None)) for fn in (mc.on_move_finished if mc else ())}
    present = [n for n in FED_LISTENERS if n in L]
    result["listeners_known"] = len(present)
    result["listeners_missing"] = [n for n in present if id(L[n]) not in owners]

    matrix = L.get("power_matrix_controller")
    latched = matrix._latched.get(HUMAN) if matrix is not None else None
    result["stamped"] = latched is not None
    result["stamp_is_this_phase"] = latched is not None and latched[0] == matrix._phase_key()
    result["regions"] = pm.describe(latched[1]) if latched is not None else None

    shooter = L.get("shooting_controller")
    squads = _squads(L)
    court = [s for s in squads if s.owner == HUMAN and pm.is_court_unit(s)
             and matrix is not None and matrix.unit_wholly_within(s)]
    enemy = next((s for s in squads if s.owner == FOE), None)
    result["court_unit"] = court[0].name if court else None
    result["reason"] = None
    if shooter is not None and court and enemy is not None:
        saved = shooter.active_squad
        shooter.active_squad = court[0]
        try:
            result["reason"] = shooter._hit_reroll_reason(enemy)
        finally:
            shooter.active_squad = saved
    result["shooter_has_matrix"] = shooter is not None and shooter.power_matrix is matrix


# WHY a button was refused in the Fight phase, MEASURED rather than guessed:
# an absence nobody explained is a story about the harness.
from game import court_cynosure_of_eradication as _cyn   # noqa: E402

_real_cyn_can_use = _cyn.CynosureOfEradicationController.can_use


def _cyn_can_use(self, squad):
    out = _real_cyn_can_use(self, squad)
    tt = self.turn_tracker
    if state["rotating"] and squad is not None and tt is not None and tt.phase == PHASE_FIGHT:
        state["fight_calls"] = state.get("fight_calls", 0) + 1
        if not out:
            fc = self.fight_controller
            if not self.at_start_of_phase_for(squad):
                why = "start-of-Fight window closed (fight state=%s, fought=%d)" % (
                    getattr(fc, "state", None), len(getattr(fc, "fought_squad_ids", ()) or ()))
            elif _cyn.is_active(squad):
                why = "already granted"
            elif not pm.is_court_unit(squad):
                why = "not a CRYPTEK/CANOPTEK unit (%s)" % squad.name
            elif not pm.unit_wholly_within(squad, self.power_matrix):
                why = "not wholly within the matrix (%s)" % squad.name
            else:
                why = "CP / rule 15.01"
            counts = state.setdefault("why_fight", {})
            counts[why] = counts.get(why, 0) + 1
    return out


_cyn.CynosureOfEradicationController.can_use = _cyn_can_use

_ORDER = (PHASE_COMMAND, PHASE_MOVEMENT, PHASE_SHOOTING, PHASE_CHARGE, PHASE_FIGHT)
_real_flip = pygame.display.flip


def flip(*args, **kwargs):
    tracker = state["tracker"]
    state["frames"] += 1
    if tracker is not None and getattr(tracker, "started", False) and not state["inspected"]:
        key = (tracker.battle_round, tracker.turn_owner, tracker.phase)
        if state["first_phase"] is None:
            state["first_phase"] = key
        elif key != state["first_phase"] or state["frames"] > MIN_FRAMES:
            L = _main_locals()
            if L is not None:
                inspect(L)
                state["result"]["inspected_at"] = (state["frames"], key)
                state["inspected"] = True
                state["rotating"] = True
                state["pile_in"] = L.get("pile_in_controller")
                state["fight"] = L.get("fight_controller")
    if state["rotating"] and tracker is not None:
        phase = _ORDER[(state["frames"] // 40) % len(_ORDER)]
        if phase == PHASE_FIGHT and state.get("staged_phase") != PHASE_FIGHT:
            # What main()'s real phase change into the Fight phase calls.
            for _ctrl in (state.get("pile_in"), state.get("fight")):
                if _ctrl is not None:
                    _ctrl.reset_fight_phase()
            state["fight_entries"] = state.get("fight_entries", 0) + 1
        state["staged_phase"] = phase
        tracker.phase_index = PHASES.index(phase)
        foreign = phase == PHASE_FIGHT and (state["frames"] // 200) % 2 == 1
        owner = FOE if foreign else HUMAN
        tracker.turn_owner = owner
        tracker.set_active(owner)
        state["phases"].add(phase)
        if state["frames"] % 17 == 0:
            state["rotate"] = True
    return _real_flip(*args, **kwargs)


pygame.display.flip = flip

_real_move_range = Renderer.draw_move_range


def draw_move_range(self, surface, board, movement_controller):
    if state["rotating"]:
        squads = []
        for token in movement_controller.all_tokens or ():
            squad = getattr(token, "squad", None)
            if squad is not None and squad.owner == HUMAN and squad not in squads:
                squads.append(squad)
        if squads and (state.pop("rotate", False) or movement_controller.selected_squad is None):
            movement_controller.select(squads[(state["frames"] // 17) % len(squads)].models[0])
        if movement_controller.selected_squad is not None:
            state["selected"] += 1
    return _real_move_range(self, surface, board, movement_controller)


Renderer.draw_move_range = draw_move_range

_argv = sys.argv[1:] or ["map2", "3000"]
sys.argv = ["selfplay.py"] + _argv
config.PLAYER1_ARMY = "necrons"
config.PLAYER2_ARMY = "aeldari"
config.ARMY_SELECT = False

try:
    runpy.run_module("selfplay", run_name="__main__")
except SystemExit:
    pass

r = state["result"]
drawn = sorted(state["seen"])
print()
print("--- Canoptek Court wiring" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
print("  frames                         : %d" % state["frames"])
print("  inspected at                   : %s" % (r.get("inspected_at"),))
print("  A. fed listeners found in main : %s" % r.get("listeners_known"))
print("     missing from the live list  : %s" % (r.get("listeners_missing") or "none"))
print("  B. Power Matrix stamped        : %s (for this phase: %s) - %s"
      % (r.get("stamped"), r.get("stamp_is_this_phase"), r.get("regions")))
print("     shooting holds the matrix   : %s" % r.get("shooter_has_matrix"))
print("     whole Hit roll offered to   : %s -> %r" % (r.get("court_unit"), r.get("reason")))
print("  C. frames with a selection     : %d, phases staged: %s"
      % (state["selected"], ", ".join(sorted(state["phases"]))))
for name in sorted(WHEN):
    info = state["seen"].get(name)
    print("     %-26s %s" % (name, ("f%d %s" % (info["frame"], ",".join(sorted(info["phases"]))))
                             if info else "NOT DRAWN"))
print("     off-WHEN sightings          : %d" % len(state["off_when"]))
print("     drawn in the OPPONENT's turn: %s"
      % (", ".join("%s/%s" % p for p in sorted(state["foreign"])) or "none"))
print("     Cynosure asked in the Fight phase: %d time(s)" % state.get("fight_calls", 0))
for _why, _n in sorted(state.get("why_fight", {}).items(), key=lambda kv: -kv[1])[:6]:
    print("        refused %5dx: %s" % (_n, _why))

if not state["inspected"] or state["frames"] < MIN_FRAMES:
    print("  INCONCLUSIVE - the run never reached a real phase change or was too short")
    raise SystemExit(2)

ok = True
if state["off_when"]:
    print("  FAIL - a button appeared outside its printed WHEN")
    ok = False
if not NEUTRALIZE:
    checks = (
        ("every fed listener is on the live list", r.get("listeners_known", 0) >= 6
         and not r.get("listeners_missing")),
        ("main() stamped the matrix for the phase it is in", r.get("stamp_is_this_phase")),
        ("main's ShootingController offers the whole Hit roll in the matrix",
         r.get("reason") == pm.POWER_MATRIX_LABEL),
        ("both buttons reached the screen", set(drawn) == set(WHEN)),
        ("Cynosure appeared at the start of a Fight phase (staged entries: %d)"
         % state.get("fight_entries", 0),
         PHASE_FIGHT in (state["seen"].get("Cynosure of Eradication") or {}).get("phases", ())),
    )
else:
    checks = (
        ("the rebind dropped fed listeners", bool(r.get("listeners_missing"))),
        ("nothing stamped the matrix", not r.get("stamped")),
        ("no whole Hit roll without the matrix", r.get("reason") != pm.POWER_MATRIX_LABEL),
        ("no Court button reached the screen", not drawn),
    )
for label, passed in checks:
    print("  %-4s %s" % ("ok" if passed else "FAIL", label))
    ok = ok and bool(passed)
print("  VERDICT: %s" % ("OK" if ok else "FAILED"))
raise SystemExit(0 if ok else 1)
