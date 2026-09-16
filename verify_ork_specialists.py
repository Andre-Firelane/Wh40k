"""Runtime proof through the REAL main() loop that the 2026-09 Ork specialists'
abilities are wired.

test_ork_specialists.py drives each ability through its real controller and pins
main.py by AST. What it cannot show is that MAIN'S objects, built by MAIN'S
constructors in MAIN'S order, are connected when the game runs. So this runs
selfplay.py's real main() loop with the ORKS AS PLAYER 1 and asks main()'s live
objects:

  A. THE WIRING. The live ShootingController holds the Pulsa Rokkit controller
     (with the AI's target pick) and main()'s objectives; Rokkit Barrage listens on
     its on_squad_finished_shooting; Bomb Squigs listens on the live
     MovementController's on_move_finished, with main()'s turn tracker and line of
     sight.
  B. BOMB SQUIGS through main()'s own listener list and dice acknowledgement.
     A Player 1 Tankbustas unit ends a Normal move near a
     Player 2 unit in Player 1's Movement phase: the human is asked, the answer
     spends a token and throws the D6, main()'s acknowledgement rolls the D3, and
     the mortal wounds land. (The staging prefers a MONSTER/VEHICLE target for C,
     usually a single model, so no 06.02 choice opens here; test_ork_specialists.py
     drains a multi-model one.)
  C. PULSA ROKKIT through the live ShootingController: the Tankbustas selected to
     shoot in Player 1's Shooting phase are asked, the answer marks the enemy
     MONSTER/VEHICLE unit, the live adjuster chain grants +1 AP and [LETHAL HITS]
     against it, and main()'s own phase boundary clears the mark.
  D. ROKKIT BARRAGE through the live on_squad_finished_shooting list: the enemy
     unit the volley hit takes a Battle-shock test at -1, which main()'s
     acknowledgement resolves.

STAGED, each named rather than quietly faked:
  * THE ORKS AS PLAYER 1 (config ships aeldari against necrons).
  * A Tankbustas unit is BUILT and put on the board beside a Player 2 unit the
    real line of sight reaches (the shipped list may embark or reserve its own),
    with one Tankbusta given the Pulsa Rokkit (the shipped list buys no gear).
  * B: the phase (Player 1's Movement) and the "move ended" moment - main()'s
    listeners are called the way MovementController calls them; the human prompt
    is answered with the first unit; the Bomb Squigs D6 and D3 are fixed to 6 and 3
    (a failed gate would test nothing downstream).
  * C: the phase (Player 1's Shooting) and the selection; the prompt is answered
    with the enemy unit and the activation cancelled; if nothing has crossed the
    phase after ADVANCE_WAIT frames, main()'s own advance_turn_phase() is called
    once, and the report says so.
  * D: the "has shot" moment - main()'s listeners are called with the hit unit
    the way ShootingController calls them.
  * Player 1 prompts this harness does not answer are declined after STALE_FRAMES.

--neutralize loads main.py through an import hook with the measured seams undone
(the Pulsa Rokkit hand-over and phase reset, the Bomb Squigs listener and dice
acknowledgement, the Rokkit Barrage listener). The files on disk are not touched.

Usage:  python verify_ork_specialists.py [map2] [frames]
        python verify_ork_specialists.py map2 --neutralize
"""

import importlib.abc
import importlib.util
import os
import runpy
import sys

import pygame

from game import bomb_squigs, config
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import build_squad
from game.factions.orks import TANKBUSTAS
from game.pulsa_rokkit import PulsaRokkitController
from game.squad import is_monster_or_vehicle_unit
from game.turn import PHASES, PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker
from game.weapons import RANGED

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

HUMAN = "Player 1"
STAGE_AT = 150
STALE_FRAMES = 30
ADVANCE_WAIT = 240
WAIT = 400
FIXED = {"Bomb Squigs": 6, "Bomb Squigs - mortal wounds": 3}

NEUTRALIZE_EDITS = (
    ("        ork_ammo_runts=ork_ammo_runts_controller, pulsa_rokkit=pulsa_rokkit_controller,\n",
     "        ork_ammo_runts=ork_ammo_runts_controller,\n"),
    ("        pulsa_rokkit_controller.reset_phase()\n", "        pass\n"),
    ("    movement_controller.on_move_finished.append(bomb_squigs_controller.on_move_finished)\n",
     "    pass\n"),
    ("        bomb_squigs_controller.on_dice_acknowledged()\n", "        pass\n"),
    ("    shooting_controller.on_squad_finished_shooting.append(\n"
     "        rokkit_barrage_controller.offer_after_shooting)\n",
     "    pass\n"),
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

state = {"frames": 0, "tracker": None, "wiring": None, "setup": None, "b": None, "c": None, "d": None,
         "stale": None, "stale_since": 0, "declined_other": [], "rolls": [], "prompts": []}


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
    if "Bomb Squigs" in (prompt or "") or "Pulsa Rokkit" in (prompt or ""):
        state["prompts"].append({"player": player, "frame": state["frames"], "prompt": prompt,
                                 "labels": [o[0] for o in options]})
    return out


DecisionManager.request = request

_real_roll = DiceManager.roll


def roll(self, *args, **kwargs):
    out = _real_roll(self, *args, **kwargs)
    label = kwargs.get("label", "") or ""
    if label in FIXED and self.pending_values:
        self.pending_values[0] = FIXED[label]
    state["rolls"].append((state["frames"], label))
    return out


DiceManager.roll = roll


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
    sc = L["shooting_controller"]
    bsq = L["bomb_squigs_controller"]
    pulsa = getattr(sc, "pulsa_rokkit", None)
    return {
        "pulsa": isinstance(pulsa, PulsaRokkitController),
        "pulsa_pick": getattr(pulsa, "target_pick", None) is not None,
        "objectives": sc.objectives is L["state"].objectives,
        "barrage": L["rokkit_barrage_controller"].offer_after_shooting in sc.on_squad_finished_shooting,
        "squigs": bsq.on_move_finished in L["movement_controller"].on_move_finished,
        "squigs_clock": bsq.turn_tracker is L["turn_tracker"] and bsq.visible is not None,
    }


def _answer(decisions, needle):
    """Choose the first option whose label starts with `needle`; None when there is
    no such prompt at the front of the queue."""
    if not decisions.is_pending:
        return None
    labels = [o["label"] for o in decisions.options]
    for i, label in enumerate(labels):
        if label.startswith(needle):
            decisions.choose(i)
            return label
    return None


def _setup(L):
    """Build the Tankbustas beside a Player 2 unit the real line of sight reaches;
    prefer a MONSTER/VEHICLE unit, so the Pulsa Rokkit has something to mark."""
    st = L["state"]
    visible = L["bomb_squigs_controller"].visible
    enemies = [s for s in _squads(L) if s.owner != HUMAN and _alive(s)]
    enemies.sort(key=lambda s: (not is_monster_or_vehicle_unit(s), s.name))
    tank = build_squad(TANKBUSTAS, HUMAN, name="1 Tankbustas (staged)")
    next(m for m in tank.models if m.profile.name == "Tankbusta").pulsa_rokkit = True
    for model in tank.models:
        st.add_token(model)
    for enemy in enemies:
        anchor = next(m for m in enemy.models if not m.is_dead())
        for dx, dy in ((0.0, -1.0), (0.0, 1.0), (-1.0, 0.0), (1.0, 0.0)):
            gap = anchor.profile.base_radius_in + 0.8 + 4.0
            for i, model in enumerate(tank.models):
                model.x_in = anchor.x_in + dx * gap + (dy != 0) * (i - 2.5) * 1.8
                model.y_in = anchor.y_in + dy * gap + (dx != 0) * (i - 2.5) * 1.8
            if enemy in bomb_squigs.targets(tank, st.tokens, visible):
                state["setup"] = {"unit": tank, "target": enemy}
                return
    state["setup"] = {"error": "no Player 2 unit the staged Tankbustas can see"}


def _stage_b(L):
    tank, target = state["setup"]["unit"], state["setup"]["target"]
    _set_phase(PHASE_MOVEMENT)
    rolls_before = len(state["rolls"])
    prompts_before = len(state["prompts"])
    wounds_before = sum(m.current_wounds for m in target.models if not m.is_dead())
    used_before = getattr(tank, "bomb_squigs_used", 0)
    for listener in list(L["movement_controller"].on_move_finished):
        listener(tank, "normal")
    asked = [p for p in state["prompts"][prompts_before:] if "Bomb Squigs" in p["prompt"]]
    chosen = _answer(L["decision_manager"], "Bomb Squigs:") if asked else None
    state["b"] = {"unit": tank.name, "target": target.name, "frame": state["frames"], "asked": asked,
                  "chosen": chosen, "rolls_before": rolls_before, "wounds_before": wounds_before,
                  "used": used_before}


def _watch_b(L):
    b = state["b"]
    ctrl = L["bomb_squigs_controller"]
    target = state["setup"]["target"]
    labels = [label for _f, label in state["rolls"][b["rolls_before"]:]]
    settled = (bool(labels) and not ctrl.is_busy and ctrl.pending_damage_choice is None
               and not L["dice_manager"].is_pending)
    if (settled and "Bomb Squigs - mortal wounds" in labels) or state["frames"] - b["frame"] >= WAIT:
        b["done"] = True
        b["labels"] = [x for x in labels if x.startswith("Bomb Squigs")]
        b["settled"] = settled
        b["wounds_lost"] = b["wounds_before"] - sum(m.current_wounds for m in target.models if not m.is_dead())


def _stage_c(L):
    tank, target = state["setup"]["unit"], state["setup"]["target"]
    _set_phase(PHASE_SHOOTING)
    sc = L["shooting_controller"]
    prompts_before = len(state["prompts"])
    try:
        sc.start_shooting(tank)
    except Exception as exc:          # a probe must report, not crash the loop
        state["c"] = {"error": "start_shooting raised %r" % exc}
        return
    asked = [p for p in state["prompts"][prompts_before:] if "Pulsa Rokkit" in p["prompt"]]
    chosen = _answer(L["decision_manager"], "Pulsa Rokkit:") if asked else None
    pulsa = L["pulsa_rokkit_controller"]
    shooter = next(m for m in tank.models if any(w.weapon_type == RANGED and w.damage > 1 for w in m.weapons)
                   and m.profile.name == "Tankbusta")
    weapon = next(w for w in shooter.weapons if w.weapon_type == RANGED)
    try:
        adjusted = sc._adjusted_weapon([(shooter, weapon)], target)
    except Exception as exc:
        adjusted = None
        state["c"] = {"error": "_adjusted_weapon raised %r" % exc}
    try:
        sc.cancel()
    except Exception:
        pass
    if state["c"] is not None:
        return
    state["c"] = {"unit": tank.name, "target": target.name, "frame": state["frames"], "asked": asked,
                  "chosen": chosen, "marked": getattr(pulsa.marked_target(tank), "name", None),
                  "printed": (weapon.ap, bool(weapon.lethal_hits)),
                  "adjusted": (adjusted.ap, bool(adjusted.lethal_hits)) if adjusted is not None else None,
                  "forced": False, "is_vehicle": is_monster_or_vehicle_unit(target)}


def _watch_c(L):
    c = state["c"]
    tracker = state["tracker"]
    crossed = tracker.phase != PHASE_SHOOTING or tracker.turn_owner != HUMAN
    if not crossed and not c["forced"] and state["frames"] - c["frame"] >= ADVANCE_WAIT and _quiet(L):
        c["forced"] = True
        L["advance_turn_phase"]()
        crossed = tracker.phase != PHASE_SHOOTING
    if crossed or state["frames"] - c["frame"] >= ADVANCE_WAIT + WAIT:
        c["done"] = True
        c["crossed"] = crossed
        c["mark_after"] = getattr(L["pulsa_rokkit_controller"].marked_target(state["setup"]["unit"]), "name", None)


def _stage_d(L):
    tank, target = state["setup"]["unit"], state["setup"]["target"]
    _set_phase(PHASE_SHOOTING)
    rolls_before = len(state["rolls"])
    for listener in list(L["shooting_controller"].on_squad_finished_shooting):
        try:
            listener(tank, [target])
        except Exception as exc:     # another listener's precondition, not this probe's subject
            state["declined_other"].append("listener %r raised %r" % (getattr(listener, "__name__", "?"), exc))
    labels = [label for _f, label in state["rolls"][rolls_before:]]
    state["d"] = {"target": target.name, "frame": state["frames"],
                  "barrage_rolls": [x for x in labels if "Rokkit Barrage" in x],
                  "rolling": getattr(L["battle_shock_controller"].rolling_squad, "name", None)}


def _watch_d(L):
    d = state["d"]
    resolved = L["battle_shock_controller"].rolling_squad is None and not L["dice_manager"].is_pending
    if resolved or state["frames"] - d["frame"] >= WAIT:
        d["done"] = True
        d["resolved"] = resolved


def flip(*args, **kwargs):
    state["frames"] += 1
    tracker = state["tracker"]
    if tracker is not None and getattr(tracker, "started", False):
        L = _main_locals()
        if L is not None and "bomb_squigs_controller" in L:
            if state["wiring"] is None:
                state["wiring"] = _wiring(L)
            _decline_stale_human_prompt(L.get("decision_manager"))
            if state["setup"] is None:
                if state["frames"] >= STAGE_AT and _quiet(L):
                    _setup(L)
            elif state["setup"].get("error"):
                raise SystemExit(0)
            elif state["b"] is None:
                if _quiet(L):
                    _stage_b(L)
            elif not state["b"].get("done"):
                _watch_b(L)
            elif state["c"] is None:
                if _quiet(L):
                    _stage_c(L)
            elif not state["c"].get("done") and not state["c"].get("error"):
                _watch_c(L)
            elif state["d"] is None:
                if _quiet(L) and L["battle_shock_controller"].rolling_squad is None:
                    _stage_d(L)
            elif not state["d"].get("done"):
                _watch_d(L)
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
s = state["setup"] or {}
b = state["b"] or {}
cc = state["c"] or {}
d = state["d"] or {}
print()
print("--- Ork specialists, live" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
print("  frames                              : %d" % state["frames"])
print("  A. Pulsa Rokkit on ShootingController: %s (AI pick injected: %s)" % (w.get("pulsa"), w.get("pulsa_pick")))
print("     ShootingController has main()'s objectives: %s" % w.get("objectives"))
print("     Rokkit Barrage on shot-finished   : %s" % w.get("barrage"))
print("     Bomb Squigs on move-finished      : %s (clock + line of sight: %s)" % (w.get("squigs"), w.get("squigs_clock")))
if s.get("error"):
    print("  SETUP ERROR " + s["error"])
else:
    print("  staged %s beside %s" % (getattr(s.get("unit"), "name", None), getattr(s.get("target"), "name", None)))
print("  B. Bomb Squigs prompts               : %s" % ([(p["player"], p["labels"]) for p in b.get("asked") or []],))
print("     answered                          : %s; tokens used %s -> %s" % (
    b.get("chosen"), b.get("used"), getattr(s.get("unit"), "bomb_squigs_used", None)))
print("     rolls                             : %s" % (b.get("labels"),))
print("     settled / wounds the target lost  : %s / %s" % (b.get("settled"), b.get("wounds_lost")))
print("  C. Pulsa Rokkit prompts              : %s%s" % ([(p["player"], p["labels"]) for p in cc.get("asked") or []],
                                                        (" ERROR " + cc["error"]) if cc.get("error") else ""))
print("     marked                            : %s (MONSTER/VEHICLE: %s)" % (cc.get("marked"), cc.get("is_vehicle")))
print("     launcha AP/[LETHAL] printed -> live chain: %s -> %s" % (cc.get("printed"), cc.get("adjusted")))
print("     boundary crossed / mark after     : %s%s / %s" % (
    cc.get("crossed"), " (advance_turn_phase() called by the probe)" if cc.get("forced") else "", cc.get("mark_after")))
print("  D. Rokkit Barrage rolls              : %s (rolling: %s)" % (d.get("barrage_rolls"), d.get("rolling")))
print("     resolved by main()'s ack          : %s" % d.get("resolved"))
print("  stale Player 1 prompts declined      : %s" % (state["declined_other"] or "none"))

if not state["wiring"] or s.get("error") or cc.get("error") or not d.get("done"):
    print("  INCONCLUSIVE - the run never got through the staging")
    raise SystemExit(2)

if not NEUTRALIZE:
    checks = (
        ("the live ShootingController holds Pulsa Rokkit, with the AI's pick", w.get("pulsa") and w.get("pulsa_pick")),
        ("...and main()'s objectives (Finderz Keeperz reads them)", w.get("objectives") is True),
        ("Rokkit Barrage listens on the live shot-finished list", w.get("barrage") is True),
        ("Bomb Squigs listens on the live move-finished list, with main()'s clock and sight",
         w.get("squigs") is True and w.get("squigs_clock") is True),
        ("a Normal move through main()'s listeners asks Player 1 about Bomb Squigs",
         any(p["player"] == HUMAN for p in b.get("asked") or [])),
        ("...the answer spends a token and throws the D6", getattr(s.get("unit"), "bomb_squigs_used", 0) >= 1
         and "Bomb Squigs" in (b.get("labels") or [])),
        ("...main()'s acknowledgement rolls the D3", "Bomb Squigs - mortal wounds" in (b.get("labels") or [])),
        ("...and the mortal wounds land and settle", b.get("settled") is True and (b.get("wounds_lost") or 0) > 0),
        ("Player 1's Tankbustas selected to shoot are asked about Pulsa Rokkit",
         any(p["player"] == HUMAN for p in cc.get("asked") or [])),
        ("...the answer marks the enemy MONSTER/VEHICLE unit", cc.get("marked") == cc.get("target")
         and cc.get("is_vehicle") is True),
        ("...the live chain grants +1 AP and [LETHAL HITS] against it",
         cc.get("adjusted") == ((cc.get("printed") or (0,))[0] - 1, True)),
        ("...and main()'s phase boundary clears the mark", cc.get("crossed") is True and cc.get("mark_after") is None),
        ("the volley's target takes a Rokkit Barrage test through main()'s listeners",
         bool(d.get("barrage_rolls")) and "-1 to the test" in (d.get("barrage_rolls") or [""])[0]),
        ("...which main()'s acknowledgement resolves", d.get("resolved") is True),
    )
else:
    checks = (
        ("no Pulsa Rokkit controller on the live ShootingController", not w.get("pulsa")),
        ("Rokkit Barrage does not listen", w.get("barrage") is False),
        ("Bomb Squigs does not listen", w.get("squigs") is False),
        ("no Bomb Squigs prompt", not b.get("asked")),
        ("no Pulsa Rokkit prompt", not cc.get("asked")),
        ("no Rokkit Barrage test", not d.get("barrage_rolls")),
    )
failed = 0
for label, ok in checks:
    print("  %s  %s" % ("PASS" if ok else "FAIL", label))
    failed += 0 if ok else 1
raise SystemExit(1 if failed else 0)
