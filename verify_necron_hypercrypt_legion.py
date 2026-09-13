"""Runtime proof through the REAL main() loop that the Hypercrypt Legion is wired.

The suites drive the detachment's controllers directly and pin main.py's wiring
by AST. What neither can show is that MAIN'S objects, built by MAIN'S
constructors in MAIN'S order, are connected when the game runs. So this runs
selfplay.py's real main() loop and asks main()'s own live locals:

  A. THE LIVE WIRING. Hyperphasing holds the AI's policy; Quantum Deflection is
     in BOTH attack controllers' target-reaction lists and Entropic Damping in
     the shooting one only; Reanimation Crypts holds the shared Reanimation
     boost; the three panel Stratagems are on main()'s registry; and main()'s
     phase gate waits while Reanimation Crypts still owes a die.
  B. THE AFTER-ATTACK HOOKS hand Hyperphasic Recall the ledger of the phase they
     belong to - main()'s own hook closures, called with an enemy unit, with a
     spy on the controller.
  C. THE THREE BUTTONS reach the screen, and only in their printed phases:
     Reanimation Crypts ("Your Command phase"), Dimensional Corridor ("Your
     Charge phase") on the unit screen, and Cosmic Precision ("Your Movement
     phase") on the ARRIVAL screen - the Set Up screen of an ingress move opened
     through main()'s own IngressController.

STAGED, each named rather than quietly faked:
  * THE NECRONS AS PLAYER 1 - config ships PLAYER2_ARMY = "necrons", and a
    question about the human's buttons that does not field them as Player 1
    measures the AI's army and reports a truthful-looking zero.
  * THE DETACHMENT, by wrapping game/detachments.apply_to_config(): it rewrites
    every detachment setting from scratch. Player 1 fields the default necrons
    list (Awakened Dynasty); the one shipped list that declares Hypercrypt
    Legion, necrons_hypercrypt, is no player's default.
  * For C only, after A and B are answered, every frame: the phase, rotated
    through all five (a MockAgent run does not visit them reliably) with the
    turn owned by Player 1 and the battle round PINNED to 2 (rule 20.03's
    arrival floor; measured: selfplay's own "Next Phase" clicks otherwise race
    the clock past round 3, where 20.03 destroys every unit still in Reserves -
    one run lost both staged Reserve units that way and drew no Reanimation
    Crypts button); a unit with something to recover moved into
    Reserves (three of its models destroyed); a unit given a gated arrival -
    the Eternity Gate's lock, its Monolith's start-of-turn fact, its entry in
    gate_arrivals_this_turn - with the smallest enemy unit moved 10" away so a
    charge exists; and, in Movement frames only, a NECRONS unit arriving from
    Reserves (cancelled again when the phase moves on, so the unit screen is
    reachable in the other four). The phase is read LIVE at draw time.

--neutralize loads main.py through an import hook with the measured seams undone
(the policy, both reaction entries, the boost, the three registrations, the gate
term and both Recall hooks). The file on disk is not touched. It must show the
pre-wiring world.

Usage:  python verify_necron_hypercrypt_legion.py [map2] [frames]
        python verify_necron_hypercrypt_legion.py map2 --neutralize
"""

import importlib.abc
import importlib.util
import os
import runpy
import sys

import pygame

from game import config, detachments, reanimation_protocols
from game.hypercrypt_hyperphasic_recall import HyperphasicRecallController
from game.renderer import Renderer
from game.strategic_reserves import withdraw_to_reserves
from game.turn import (PHASES, PHASE_CHARGE, PHASE_COMMAND, PHASE_FIGHT,
                       PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker)
from game.ui import button_style

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

HUMAN = "Player 1"
FOE = "Player 2"
SETTING = "HYPERCRYPT_LEGION_PLAYERS"
MIN_FRAMES = 1200

# TRANSCRIBED from rules/necrons/detachments/Hypercrypt Legion.md.
WHEN = {
    "Reanimation Crypts": {PHASE_COMMAND},
    "Dimensional Corridor": {PHASE_CHARGE},
    "Cosmic Precision": {PHASE_MOVEMENT},
}

#: (anchor, replacement) applied to main.py's SOURCE in memory for --neutralize.
NEUTRALIZE_EDITS = (
    ("        choose=lambda eligible, cap: hyperphasing_choice(state, turn_tracker, eligible, cap))",
     "        choose=None)"),
    ("        quantum_deflection_controller, entropic_damping_controller,\n", ""),
    ("        repair_barge_controller, quantum_deflection_controller,\n", "        repair_barge_controller,\n"),
    ("    reanimation_crypts_controller.boost = reanimation_boost", "    pass"),
    ("proactive_stratagems.add(ReanimationCryptsController(", "(ReanimationCryptsController("),
    ("proactive_stratagems.add(CosmicPrecisionController(", "(CosmicPrecisionController("),
    ("proactive_stratagems.add(DimensionalCorridorController(", "(DimensionalCorridorController("),
    ("            or reanimation_crypts_controller.is_busy", "            or False"),
    ("        hyperphasic_recall_controller.maybe_offer(\n"
     "            shooter_squad, shooting_controller.models_lost_this_activation)", "        pass"),
    ("            hyperphasic_recall_controller.maybe_offer(\n"
     "                _fighter, fight_controller.models_lost_this_activation)", "            pass"),
)

if NEUTRALIZE:
    _MAIN_PATH = os.path.abspath("main.py")
    with open(_MAIN_PATH, encoding="utf-8") as fh:
        _src = fh.read().replace("\r\n", "\n")
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

state = {"frames": 0, "tracker": None, "first_phase": None, "inspected": False, "rotating": False,
         "seen": {}, "off_when": [], "phases": set(), "result": {}, "recall_calls": [],
         "staged": {}, "L": None, "arrivals_opened": 0}

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
    return _real_draw_button(surface, rect, label, font, hovered=hovered, pressed=pressed, accent=accent)


button_style.draw_button = draw_button

from game.ingress import IngressController                          # noqa: E402

_real_destroy_reserves = IngressController.destroy_remaining_reserves


def destroy_remaining_reserves(self, *args, **kwargs):
    if state["rotating"]:
        state["reserves_destroyed"] = state.get("reserves_destroyed", 0) + 1
    return _real_destroy_reserves(self, *args, **kwargs)


IngressController.destroy_remaining_reserves = destroy_remaining_reserves

_real_recall_offer = HyperphasicRecallController.maybe_offer


def recall_offer(self, attacker, lost):
    state["recall_calls"].append((getattr(attacker, "name", None), getattr(lost, "__self__", None)))
    return _real_recall_offer(self, attacker, lost)


HyperphasicRecallController.maybe_offer = recall_offer


def _main_locals():
    frame = sys._getframe(2)
    while frame is not None and frame.f_code.co_name != "main":
        frame = frame.f_back
    return frame.f_locals if frame is not None else None


def _squads(L):
    game_state = L.get("state")
    return list(game_state.all_squads()) if game_state is not None else []


def inspect(L):
    """Questions A and B, asked of main()'s live objects."""
    r = state["result"]
    hc = L.get("hyperphasing_controller")
    r["policy"] = hc is not None and hc.choose is not None
    r["policy_answers"] = hc.choose([], 2) if r["policy"] else None
    sc, fc = L.get("shooting_controller"), L.get("fight_controller")
    qd, ed = L.get("quantum_deflection_controller"), L.get("entropic_damping_controller")
    r["qd_shooting"] = qd in (sc.target_reactions if sc else ())
    r["ed_shooting"] = ed in (sc.target_reactions if sc else ())
    r["qd_fight"] = qd in (fc.target_reactions if fc else ())
    r["ed_fight"] = ed in (fc.target_reactions if fc else ())
    rc = L.get("reanimation_crypts_controller")
    r["boost"] = rc is not None and rc.boost is L.get("reanimation_boost") and rc.boost is not None
    registry = L.get("proactive_stratagems")
    held = list(getattr(registry, "controllers", ()) or ())
    r["registered"] = sorted(name for name, key in (
        ("Reanimation Crypts", "reanimation_crypts_controller"),
        ("Cosmic Precision", "cosmic_precision_controller"),
        ("Dimensional Corridor", "dimensional_corridor_controller")) if L.get(key) in held)
    gate = L.get("_has_unresolved_declaration")
    if gate is not None and rc is not None:
        saved = rc._queue
        try:
            rc._queue = []
            baseline = bool(gate())
            rc._queue = [object()]
            busy = bool(gate())
        finally:
            rc._queue = saved
        r["gate"] = (baseline, busy)

    # B. main()'s own after-attack hooks, with an enemy unit.
    foe = next((s for s in _squads(L) if s.owner == FOE and any(m in L["state"].tokens for m in s.models)), None)
    state["recall_calls"].clear()
    for hook in ("_necron_after_enemy_shooting", "_necron_after_enemy_fight"):
        fn = L.get(hook)
        if fn is None or foe is None:
            continue
        try:
            fn(foe)
        except Exception as exc:          # a crash is a finding, reported
            r.setdefault("hook_errors", []).append("%s: %r" % (hook, exc))
    r["recall_ledgers"] = [("shooting" if who is sc else "fight" if who is fc else repr(who))
                           for _name, who in state["recall_calls"]]


def stage(L):
    """C's staging, re-applied every rotating frame (a real phase change may clear it)."""
    st = L["state"]
    ic = L["ingress_controller"]
    tracker = state["tracker"]
    staged = state["staged"]
    # PINNED, every frame, and measured first: with the turn staged as Player 1's,
    # selfplay clicks "Next Phase" in it, so the real clock races round after
    # round - and rule 20.03 destroys every unit still in Reserves at the end of
    # battle round 3, which took both staged Reserve units off the table.
    state["max_round"] = max(state.get("max_round", 0), tracker.battle_round)
    tracker.battle_round = 2
    if not staged:
        mine = [s for s in _squads(L) if s.owner == HUMAN and any(m in st.tokens for m in s.models)
                and len([m for m in s.models if not m.is_dead()]) >= 4
                and reanimation_protocols.has_reanimation_protocols(s)
                and all(getattr(m.profile, "infantry", False) for m in s.models)]
        if len(mine) < 3:
            staged["error"] = "fewer than three Necron infantry units on the board (%d)" % len(mine)
            return
        crypt, gated, arriving = mine[0], mine[1], mine[2]
        for model in list(crypt.models[:3]):
            model.current_wounds = 0
            if model in st.tokens:
                st.tokens.remove(model)
            crypt.models.remove(model)
            crypt.destroyed_models.append(model)
        withdraw_to_reserves(st, crypt)
        withdraw_to_reserves(st, arriving)
        foes = sorted((s for s in _squads(L) if s.owner == FOE and any(m in st.tokens for m in s.models)),
                      key=lambda s: len(s.models))
        staged.update(crypt=crypt, gated=gated, arriving=arriving, foe=foes[0] if foes else None)
    gated, foe = staged["gated"], staged["foe"]
    gated.eternity_gate_charge_locked = True
    gated.eternity_gate_bearer_started_on_board = True
    ic.gate_arrivals_this_turn.add(gated)
    if foe is not None:
        gx = sum(m.x_in for m in gated.models) / len(gated.models)
        gy = sum(m.y_in for m in gated.models) / len(gated.models)
        fx = sum(m.x_in for m in foe.models) / len(foe.models)
        fy = sum(m.y_in for m in foe.models) / len(foe.models)
        spread = max(abs(m.y_in - fy) for m in foe.models) + max(abs(m.y_in - gy) for m in gated.models)
        ty = gy + (10.0 + spread) * (1 if gy < config.BOARD_HEIGHT_IN / 2.0 else -1)
        for m in foe.models:
            m.x_in, m.y_in = gx + (m.x_in - fx), ty + (m.y_in - fy)


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
                state["L"] = L
    if state["rotating"] and tracker is not None and state["L"] is not None:
        L = state["L"]
        phase = _ORDER[(state["frames"] // 40) % len(_ORDER)]
        ic, setup = L["ingress_controller"], L["setup_controller"]
        if phase != PHASE_MOVEMENT and ic.is_ingressing(state["staged"].get("arriving")):
            ic.cancel_ingress()
        tracker.phase_index = PHASES.index(phase)
        tracker.turn_owner = HUMAN
        tracker.set_active(HUMAN)
        state["phases"].add(phase)
        stage(L)
        arriving = state["staged"].get("arriving")
        if phase == PHASE_MOVEMENT and arriving is not None and not ic.is_ingressing(arriving):
            if setup.state != "placing" and arriving in L["state"].reserves:
                ic.start_ingress(arriving, 3.0, 3.0)
            if ic.is_ingressing(arriving):
                state["arrivals_opened"] += 1
            else:
                # WHY no arrival opened, measured rather than guessed.
                why = "setup=%s in_reserves=%s can_ingress=%s placing=%s" % (
                    setup.state, arriving in L["state"].reserves, ic.can_ingress(arriving),
                    getattr(setup.setting_up_squad, "name", None))
                counts = state.setdefault("why_no_arrival", {})
                counts[why] = counts.get(why, 0) + 1
    return _real_flip(*args, **kwargs)


pygame.display.flip = flip

_real_move_range = Renderer.draw_move_range


def draw_move_range(self, surface, board, movement_controller):
    gated = state["staged"].get("gated")
    if state["rotating"] and gated is not None and movement_controller.selected_squad is not gated:
        movement_controller.select(gated.models[0])
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
print("--- Hypercrypt Legion wiring" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
print("  frames                          : %d" % state["frames"])
print("  inspected at                    : %s" % (r.get("inspected_at"),))
print("  A. Hyperphasing holds a policy  : %s (empty -> %r)" % (r.get("policy"), r.get("policy_answers")))
print("     Quantum Deflection shooting/fight: %s / %s" % (r.get("qd_shooting"), r.get("qd_fight")))
print("     Entropic Damping shooting/fight  : %s / %s" % (r.get("ed_shooting"), r.get("ed_fight")))
print("     Reanimation Crypts holds the boost: %s" % r.get("boost"))
print("     on main()'s registry         : %s" % (r.get("registered") or "none"))
print("     phase gate (idle, busy)      : %s" % (r.get("gate"),))
print("  B. Recall offered from the hooks: %s %s" % (r.get("recall_ledgers"), r.get("hook_errors") or ""))
print("  C. staging                      : %s, arrivals opened %d, phases %s"
      % (state["staged"].get("error") or "ok", state["arrivals_opened"], ", ".join(sorted(state["phases"]))))
for name in sorted(WHEN):
    info = state["seen"].get(name)
    print("     %-22s %s" % (name, ("f%d %s" % (info["frame"], ",".join(sorted(info["phases"]))))
                             if info else "NOT DRAWN"))
print("     off-WHEN sightings           : %d" % len(state["off_when"]))
print("     real round before the pin: max %s; Reserves destroyed while staging: %d"
      % (state.get("max_round"), state.get("reserves_destroyed", 0)))
for _why, _n in sorted(state.get("why_no_arrival", {}).items(), key=lambda kv: -kv[1])[:4]:
    print("     no arrival opened %4dx     : %s" % (_n, _why))

if not state["inspected"] or state["frames"] < MIN_FRAMES or state["staged"].get("error"):
    print("  INCONCLUSIVE - no real phase change, too short a run, or the staging failed")
    raise SystemExit(2)

ok = True
if state["off_when"]:
    print("  FAIL - a button appeared outside its printed WHEN")
    ok = False
_gate = r.get("gate") or (None, None)
if not NEUTRALIZE:
    checks = (
        ("Hyperphasing holds the AI's policy", r.get("policy") and r.get("policy_answers") == []),
        ("Quantum Deflection answers both attack steps", r.get("qd_shooting") and r.get("qd_fight")),
        ("Entropic Damping answers shooting only", r.get("ed_shooting") and not r.get("ed_fight")),
        ("Reanimation Crypts holds the shared boost", r.get("boost")),
        ("all three panel Stratagems are on main()'s registry", len(r.get("registered") or ()) == 3),
        ("the phase gate waits on Reanimation Crypts' dice", _gate == (False, True)),
        ("both hooks offer Hyperphasic Recall with their own ledger",
         r.get("recall_ledgers") == ["shooting", "fight"] and not r.get("hook_errors")),
        ("all three buttons reached the screen", set(drawn) == set(WHEN)),
    )
else:
    checks = (
        ("no policy", not r.get("policy")),
        ("no Quantum Deflection / Entropic Damping reactions",
         not (r.get("qd_shooting") or r.get("qd_fight") or r.get("ed_shooting"))),
        ("no boost", not r.get("boost")),
        ("nothing on the registry", not r.get("registered")),
        ("the gate does not wait on the dice", _gate[0] == _gate[1]),
        ("no Recall offer from the hooks", not r.get("recall_ledgers")),
        ("no Hypercrypt button reached the screen", not drawn),
    )
for label, passed in checks:
    print("  %-4s %s" % ("ok" if passed else "FAIL", label))
    ok = ok and bool(passed)
print("  VERDICT: %s" % ("OK" if ok else "FAILED"))
raise SystemExit(0 if ok else 1)
