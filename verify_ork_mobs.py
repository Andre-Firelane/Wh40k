"""Runtime proof through the REAL main() loop that the 2026-09 Ork mob abilities
are wired.

test_ork_mobs.py drives each ability through its real controller and pins main.py
by AST. What it cannot show is that MAIN'S objects, built by MAIN'S constructors
in MAIN'S order, are connected when the game runs. So this runs selfplay.py's real
main() loop with the ORKS AS PLAYER 1 and asks main()'s live objects:

  A. THE WIRING. The live ShootingController holds the Ammo Runts controller, the
     live FightController the Rokkit Charge controller (with the AI's verdict),
     and Mobbed listens on the live ChargeController's charge-end hook.
  B. THIEVIN' SCAVENGERS through main()'s own phase boundary. A Player 1 Gretchin
     unit stands on an objective in Player 1's Movement phase; the boundary main()
     runs when that phase ends must secure the objective - for Player 1.
  C. MOBBED through main()'s own listener list and dice acknowledgement. A Beast
     Snagga Boyz unit that ends a charge engaged with a Player 2 MONSTER/VEHICLE
     makes it take a Battle-Shock test, which main()'s acknowledgement resolves.
  D. AMMO RUNTS through the live ShootingController: a Player 1 Boyz unit selected
     to shoot in Player 1's Shooting phase is asked, and declining spends nothing.

STAGED, each named rather than quietly faked:
  * THE ORKS AS PLAYER 1 (config ships aeldari against necrons).
  * B: the phase (Player 1's Movement), the Gretchin models' positions (on an
    objective no enemy model stands on) and that objective's Secured flag cleared.
    The boundary itself is main()'s - selfplay clicks Next Phase in Player 1's turn;
    if nothing has crossed it after ADVANCE_WAIT frames, main()'s own
    advance_turn_phase() is called once, and the report says so.
  * C: the Beast Snagga Boyz unit (built and put on the board - the shipped list
    embarks its only one in a Kill Rig) beside the enemy model, and the "charge
    ended" moment: main()'s listeners are called the way ChargeController calls them.
  * D: the phase (Player 1's Shooting) and the selection; the prompt is answered
    "Save it for later" and the activation cancelled.
  * Player 1 prompts this harness does not answer are declined after STALE_FRAMES.

--neutralize loads main.py through an import hook with the measured seams undone
(the Thievin' Scavengers sweep, the Mobbed listener and acknowledgement, the Ammo
Runts and Rokkit Charge controllers). The files on disk are not touched.

Usage:  python verify_ork_mobs.py [map2] [frames]
        python verify_ork_mobs.py map2 --neutralize
"""

import importlib.abc
import importlib.util
import os
import runpy
import sys

import pygame

from game import config, mobbed, thievin_scavengers
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import build_squad
from game.factions.orks import BEAST_SNAGGA_BOYZ
from game.mission_context import objective_centre
from game.ork_ammo_runts import AmmoRuntsController
from game.rokkit_charge import RokkitChargeController
from game.squad import is_monster_or_vehicle_unit
from game.turn import PHASES, PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

HUMAN = "Player 1"
STAGE_AT = 150
STALE_FRAMES = 30
ADVANCE_WAIT = 240
WAIT = 240

NEUTRALIZE_EDITS = (
    ("            thievin_scavengers.secure_at_end_of_movement(\n"
     "                state.objectives, state.tokens, mover_before, game_log=game_log)\n",
     "            pass\n"),
    ("    charge_controller.on_charge_move_finished.append(\n"
     "        mobbed_controller.on_charge_move_finished)\n",
     "    pass\n"),
    ("        mobbed_controller.on_dice_acknowledged()\n", "        pass\n"),
    ("        ork_ammo_runts=ork_ammo_runts_controller, pulsa_rokkit=pulsa_rokkit_controller,\n",
     "        pulsa_rokkit=pulsa_rokkit_controller,\n"),
    ("        rokkit_charge=RokkitChargeController(\n"
     "            decision_manager=decision_manager, game_log=game_log,\n"
     "            auto_players=ai_players,\n"
     "            verdict=lambda squad: rokkit_charge_verdict(squad, fight_controller)),\n",
     ""),
)

if NEUTRALIZE:
    _MAIN_PATH = os.path.abspath("main.py")
    with open(_MAIN_PATH, encoding="utf-8") as fh:
        _src = fh.read().replace("\r\n", "\n")
    for _anchor, _replacement in NEUTRALIZE_EDITS:
        if _src.count(_anchor) != 1:
            raise SystemExit("neutralize anchor not unique in main.py: %r (%d)"
                             % (_anchor[:80], _src.count(_anchor)))
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

state = {"frames": 0, "tracker": None, "wiring": None, "b": None, "c": None, "d": None,
         "stale": None, "stale_since": 0, "declined_other": [], "sweeps": [], "rolls": [],
         "prompts": []}


def _main_locals():
    frame = sys._getframe(1)
    while frame is not None and frame.f_code.co_name != "main":
        frame = frame.f_back
    return frame.f_locals if frame is not None else None


_real_tracker_init = TurnTracker.__init__


def tracker_init(self, *args, **kwargs):
    _real_tracker_init(self, *args, **kwargs)
    state["tracker"] = self


TurnTracker.__init__ = tracker_init

_real_request = DecisionManager.request


def request(self, player, prompt, options, *args, **kwargs):
    out = _real_request(self, player, prompt, options, *args, **kwargs)
    if "Ammo Runts" in (prompt or ""):
        state["prompts"].append({"player": player, "frame": state["frames"], "prompt": prompt,
                                 "labels": [o[0] for o in options]})
    return out


DecisionManager.request = request

_real_roll = DiceManager.roll


def roll(self, *args, **kwargs):
    state["rolls"].append((state["frames"], kwargs.get("label", "")))
    return _real_roll(self, *args, **kwargs)


DiceManager.roll = roll

_real_sweep = thievin_scavengers.secure_at_end_of_movement


def sweep(objectives, all_tokens, player, game_log=None):
    out = _real_sweep(objectives, all_tokens, player, game_log=game_log)
    state["sweeps"].append((state["frames"], player, [o.name for o in out]))
    return out


thievin_scavengers.secure_at_end_of_movement = sweep


def _squads(L):
    out = []
    for token in L["state"].tokens:
        squad = getattr(token, "squad", None)
        if squad is not None and squad not in out:
            out.append(squad)
    return out


def _alive(squad):
    return any(not m.is_dead() for m in squad.models)


def _quiet(L):
    return not L["dice_manager"].is_pending and not L["decision_manager"].is_pending


def _decline_stale_human_prompt(decisions):
    if decisions is None or not decisions.is_pending or decisions.player != HUMAN:
        state["stale"] = None
        return
    prompt = decisions.prompt or ""
    key = (id(decisions._queue[0]), prompt)
    if state["stale"] != key:
        state["stale"], state["stale_since"] = key, state["frames"]
        return
    if state["frames"] - state["stale_since"] >= STALE_FRAMES:
        state["declined_other"].append(prompt[:60])
        decisions.choose(len(decisions.options) - 1)
        state["stale"] = None


def _set_phase(phase):
    tracker = state["tracker"]
    tracker.phase_index = PHASES.index(phase)
    tracker.turn_owner = HUMAN
    tracker.set_active(HUMAN)


def _wiring(L):
    charge = L["charge_controller"]
    return {
        "ammo_runts": isinstance(getattr(L["shooting_controller"], "ork_ammo_runts", None), AmmoRuntsController),
        "rokkit_charge": isinstance(getattr(L["fight_controller"], "rokkit_charge", None), RokkitChargeController),
        "rokkit_verdict": getattr(getattr(L["fight_controller"], "rokkit_charge", None), "verdict", None) is not None,
        "mobbed_listener": L["mobbed_controller"].on_charge_move_finished in charge.on_charge_move_finished,
    }


def _stage_b(L):
    st = L["state"]
    grots = next((s for s in _squads(L) if s.owner == HUMAN and _alive(s)
                  and getattr(s.datasheet, "name", "") == "Gretchin"), None)
    enemy_tokens = [t for t in st.tokens if t.squad is not None and t.squad.owner != HUMAN and not t.is_dead()]
    objective = next((o for o in st.objectives
                      if not any(o.terrain_area.overlaps_model(t) for t in enemy_tokens)), None)
    if grots is None or objective is None:
        state["b"] = {"error": "no Player 1 Gretchin on the board" if grots is None else "no objective free of enemies"}
        return
    cx, cy = objective_centre(objective)
    living = [m for m in grots.models if not m.is_dead()]
    for i, model in enumerate(living):
        model.x_in, model.y_in = cx - 2.2 + (i % 5) * 1.1, cy - 0.55 + (i // 5) * 1.1
    objective.secured_by = None
    _set_phase(PHASE_MOVEMENT)
    state["b"] = {"unit": grots.name, "objective": objective.name, "frame": state["frames"],
                  "sweeps_before": len(state["sweeps"]), "forced": False, "_objective": objective,
                  "on_footprint": sum(1 for m in living if objective.terrain_area.overlaps_model(m))}


def _watch_b(L):
    b = state["b"]
    tracker = state["tracker"]
    crossed = tracker.phase != PHASE_MOVEMENT or tracker.turn_owner != HUMAN
    if not crossed and not b["forced"] and state["frames"] - b["frame"] >= ADVANCE_WAIT and _quiet(L):
        b["forced"] = True
        L["advance_turn_phase"]()
        crossed = tracker.phase != PHASE_MOVEMENT
    if crossed or state["frames"] - b["frame"] >= ADVANCE_WAIT + WAIT:
        b["done"] = True
        b["crossed"] = crossed
        b["secured_by"] = b["_objective"].secured_by
        b["controlled_by"] = b["_objective"].controlled_by
        b["sweeps"] = state["sweeps"][b["sweeps_before"]:]


def _stage_c(L):
    st = L["state"]
    target = next((s for s in _squads(L) if s.owner != HUMAN and _alive(s) and is_monster_or_vehicle_unit(s)), None)
    if target is None:
        state["c"] = {"error": "no Player 2 MONSTER/VEHICLE on the board"}
        return
    anchor = next(m for m in target.models if not m.is_dead())
    mob = build_squad(BEAST_SNAGGA_BOYZ, HUMAN, name="1 Beast Snagga Boyz (staged)")
    gap = anchor.profile.base_radius_in + mob.models[0].profile.base_radius_in + 1.0
    for i, model in enumerate(mob.models):
        model.x_in, model.y_in = anchor.x_in - 6.3 + i * 1.4, anchor.y_in - gap
    for model in mob.models:
        st.add_token(model)
    target.battle_shocked = False
    engaged = [s.name for s in mobbed.targets_for(mob, st.tokens)]
    rolls_before = len(state["rolls"])
    for listener in list(L["charge_controller"].on_charge_move_finished):
        listener(mob)
    labels = [label for _f, label in state["rolls"][rolls_before:]]
    state["c"] = {"unit": mob.name, "target": target.name, "engaged": engaged, "frame": state["frames"],
                  "mobbed_rolls": [x for x in labels if "Mobbed" in x],
                  "rolling": getattr(L["battle_shock_controller"].rolling_squad, "name", None)}


def _watch_c(L):
    c = state["c"]
    bsc = L["battle_shock_controller"]
    resolved = bsc.rolling_squad is None and not L["dice_manager"].is_pending
    if resolved or state["frames"] - c["frame"] >= WAIT:
        c["done"] = True
        c["resolved"] = resolved
        c["queue_empty"] = not L["mobbed_controller"].is_busy


def _stage_d(L):
    boyz = next((s for s in _squads(L) if s.owner == HUMAN and _alive(s)
                 and getattr(s.datasheet, "name", "") == "Boyz"), None)
    if boyz is None:
        state["d"] = {"error": "no Player 1 Boyz on the board"}
        return
    _set_phase(PHASE_SHOOTING)
    sc = L["shooting_controller"]
    used_before = bool(getattr(boyz, "ammo_runts_used", False))
    prompts_before = len(state["prompts"])
    try:
        sc.start_shooting(boyz)
    except Exception as exc:          # a probe must report, not crash the loop
        state["d"] = {"error": "start_shooting raised %r" % exc}
        return
    decisions = L["decision_manager"]
    answered = False
    for _ in range(6):
        if not decisions.is_pending:
            break
        labels = [o["label"] for o in decisions.options]
        if "Save it for later" in labels and "Ammo Runts" in (decisions.prompt or ""):
            decisions.choose(labels.index("Save it for later"))
            answered = True
            break
        decisions.choose(len(labels) - 1)
    try:
        sc.cancel()
    except Exception:
        pass
    state["d"] = {"unit": boyz.name, "asked": state["prompts"][prompts_before:], "answered": answered,
                  "used_before": used_before, "used_after": bool(getattr(boyz, "ammo_runts_used", False)),
                  "done": True}


def flip(*args, **kwargs):
    state["frames"] += 1
    tracker = state["tracker"]
    if tracker is not None and getattr(tracker, "started", False):
        L = _main_locals()
        if L is not None and "mobbed_controller" in L:
            if state["wiring"] is None:
                state["wiring"] = _wiring(L)
            _decline_stale_human_prompt(L.get("decision_manager"))
            if state["b"] is None:
                if state["frames"] >= STAGE_AT and _quiet(L):
                    _stage_b(L)
            elif not state["b"].get("done") and not state["b"].get("error"):
                _watch_b(L)
            elif state["c"] is None:
                if _quiet(L) and L["battle_shock_controller"].rolling_squad is None:
                    _stage_c(L)
            elif not state["c"].get("done") and not state["c"].get("error"):
                _watch_c(L)
            elif state["d"] is None:
                if _quiet(L):
                    _stage_d(L)
            else:
                raise SystemExit(0)
    return _real_flip(*args, **kwargs)


_real_flip = pygame.display.flip
pygame.display.flip = flip

_argv = sys.argv[1:] or ["map2", "4000"]
sys.argv = ["selfplay.py"] + _argv
config.PLAYER1_ARMY = "orks"
config.PLAYER2_ARMY = "necrons"
config.ARMY_SELECT = False

try:
    runpy.run_module("selfplay", run_name="__main__")
except SystemExit:
    pass

w = state["wiring"] or {}
b = state["b"] or {}
cc = state["c"] or {}
d = state["d"] or {}
print()
print("--- Ork mob abilities, live" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
print("  frames                           : %d" % state["frames"])
print("  A. Ammo Runts on ShootingController: %s" % w.get("ammo_runts"))
print("     Rokkit Charge on FightController: %s (verdict injected: %s)" % (w.get("rokkit_charge"), w.get("rokkit_verdict")))
print("     Mobbed on the charge-end hook : %s" % w.get("mobbed_listener"))
print("  B. %s on %s (%s model(s) on the footprint)%s" % (
    b.get("unit"), b.get("objective"), b.get("on_footprint"), (" ERROR " + b["error"]) if b.get("error") else ""))
print("     boundary crossed              : %s%s" % (b.get("crossed"), " (advance_turn_phase() called by the probe)" if b.get("forced") else ""))
print("     sweeps at that boundary       : %s" % (b.get("sweeps"),))
print("     controlled_by / secured_by    : %s / %s" % (b.get("controlled_by"), b.get("secured_by")))
print("  C. %s beside %s, engaged: %s%s" % (
    cc.get("unit"), cc.get("target"), cc.get("engaged"), (" ERROR " + cc["error"]) if cc.get("error") else ""))
print("     Mobbed rolls opened           : %s (rolling: %s)" % (cc.get("mobbed_rolls"), cc.get("rolling")))
print("     resolved by main()'s ack      : %s, queue empty: %s" % (cc.get("resolved"), cc.get("queue_empty")))
print("  D. %s selected to shoot%s" % (d.get("unit"), (" ERROR " + d["error"]) if d.get("error") else ""))
print("     Ammo Runts prompts            : %s" % ([(p["player"], p["labels"]) for p in d.get("asked") or []],))
print("     declined, spend before/after  : %s / %s" % (d.get("used_before"), d.get("used_after")))
print("  stale Player 1 prompts declined  : %s" % (state["declined_other"] or "none"))

if not state["wiring"] or b.get("error") or cc.get("error") or d.get("error") or not d.get("done"):
    print("  INCONCLUSIVE - the run never got through the staging")
    raise SystemExit(2)

engaged_ok = cc.get("target") in (cc.get("engaged") or [])
if not NEUTRALIZE:
    checks = (
        ("the live ShootingController holds the Ammo Runts controller", w.get("ammo_runts") is True),
        ("the live FightController holds Rokkit Charge, with the AI's verdict",
         w.get("rokkit_charge") is True and w.get("rokkit_verdict") is True),
        ("Mobbed listens on the live charge-end hook", w.get("mobbed_listener") is True),
        ("main()'s Movement boundary swept Thievin' Scavengers for Player 1",
         any(player == HUMAN for _f, player, _names in b.get("sweeps") or [])),
        ("...and the objective the Gretchin control is secured for Player 1", b.get("secured_by") == HUMAN),
        ("the staged mob is engaged with the enemy unit", engaged_ok),
        ("ending its charge through main()'s listeners opens a Mobbed test", bool(cc.get("mobbed_rolls"))),
        ("...which main()'s acknowledgement resolves", cc.get("resolved") is True and cc.get("queue_empty") is True),
        ("Player 1's Boyz selected to shoot are asked about Ammo Runts",
         any(p["player"] == HUMAN for p in d.get("asked") or [])),
        ("...and declining spends nothing", d.get("answered") is True and d.get("used_after") is False),
    )
else:
    checks = (
        ("no Ammo Runts controller on the live ShootingController", w.get("ammo_runts") is False),
        ("no Rokkit Charge controller on the live FightController", w.get("rokkit_charge") is False),
        ("Mobbed does not listen", w.get("mobbed_listener") is False),
        ("no Thievin' Scavengers sweep at the boundary", not b.get("sweeps")),
        ("the objective is not secured", b.get("secured_by") != HUMAN),
        ("the staged mob is engaged with the enemy unit", engaged_ok),
        ("no Mobbed test opens", not cc.get("mobbed_rolls")),
        ("no Ammo Runts prompt", not d.get("asked")),
    )
failed = 0
for label, ok in checks:
    print("  %s  %s" % ("PASS" if ok else "FAIL", label))
    failed += 0 if ok else 1
raise SystemExit(1 if failed else 0)
