"""Runtime proof through the REAL main() loop that the 2026-09 Ork characters are
wired.

test_ork_characters.py drives each ability through its real controller and pins
main.py by AST. What it cannot show is that MAIN'S objects, built by MAIN'S
constructors in MAIN'S order, are connected when the game runs. So this runs
selfplay.py's real main() loop with the ORKS AS PLAYER 1 and asks main()'s live
objects:

  A. THE WIRING. The live ShootingController holds Boss' Ammo Runt; the live
     registry holds Intimidating Motivation and Keep Huntin'!, and the live
     MovementController's two hooks call them; Krushin' Impetus listens on the
     live ChargeController's charge-end hook; Crude Surgery holds main()'s placer.
  B. CRUDE SURGERY through main()'s own phase boundary. Player 1's Boyz + Warboss
     + Painboy mob has lost two Boys and a Painboy wound when Player 2's Fight
     phase ends; main()'s advance_turn_phase() begins Player 1's Command phase,
     and the mob heals 3 - the Painboy topped up, both Boys revived, placed by the
     HUMAN through main()'s placer.
  C. KRUSHIN' IMPETUS through main()'s charge-end listeners and dice
     acknowledgement, against a Player 2 unit of several models - whose owner, the
     AI, has to allocate the mortal wounds.
  D. INTIMIDATING MOTIVATION drawn on main()'s own ActionPanel for Player 1's
     Warboss mob in Player 1's Movement phase, and pressed.
  E. BOSS' AMMO RUNT asked through the live ShootingController when that mob is
     selected to shoot, declined, spending nothing.

STAGED, each named rather than quietly faked:
  * THE ORKS AS PLAYER 1 (config ships aeldari against necrons).
  * B: the losses, the clock (Player 2's Fight phase) and one advance_turn_phase()
    call when quiet; the placement is confirmed by the probe.
  * C: the Warboss in Mega Armour mob (the shipped list embarks it in a
    Battlewagon) beside the Player 2 unit, and the "charge ended" moment: main()'s
    listeners are called the way ChargeController calls them.
  * D/E: the phase and the selection, re-stamped while waiting for main() to draw
    (selfplay clicks Next Phase in Player 1's turn).
  * Player 1 prompts this harness does not answer are declined after STALE_FRAMES.

--neutralize loads main.py through an import hook with the measured seams undone.
The files on disk are not touched.

Usage:  python verify_ork_characters.py [map2] [frames]
        python verify_ork_characters.py map2 --neutralize
"""

import importlib.abc
import importlib.util
import os
import runpy
import sys

import pygame

from game import config, krushin_impetus
from game.attached_units import attach
from game.boss_ammo_runt import BossAmmoRuntController
from game.boss_motivation import IntimidatingMotivationController, KeepHuntinController
from game.crude_surgery import CrudeSurgeryController
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import build_squad
from game.factions.orks import MEGANOBZ, WARBOSS_MEGA_ARMOUR
from game.turn import PHASES, PHASE_FIGHT, PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker
from game.ui.action_panel import ActionPanel

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

HUMAN, AI = "Player 1", "Player 2"
STAGE_AT = 150
STALE_FRAMES = 30
WAIT = 240

NEUTRALIZE_EDITS = (
    ("        boss_ammo_runt=boss_ammo_runt_controller,\n", ""),
    ("    proactive_stratagems.add(intimidating_motivation_controller)\n"
     "    proactive_stratagems.add(keep_huntin_controller)\n", ""),
    ("    movement_controller.on_move_started.append(intimidating_motivation_controller.on_move_started)\n"
     "    movement_controller.on_move_finished.append(intimidating_motivation_controller.on_move_finished)\n"
     "    movement_controller.on_move_started.append(keep_huntin_controller.on_move_started)\n"
     "    movement_controller.on_move_finished.append(keep_huntin_controller.on_move_finished)\n", ""),
    ("    charge_controller.on_charge_move_finished.append(\n"
     "        krushin_impetus_controller.on_charge_move_finished)\n", ""),
    ("            crude_surgery_controller.begin_command_phase(state.all_squads(), turn_tracker.turn_owner)\n",
     "            pass\n"),
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

state = {"frames": 0, "tracker": None, "wiring": None, "b": None, "c": None, "d": None, "e": None,
         "stale": None, "stale_since": 0, "declined_other": [], "rolls": [], "prompts": [],
         "surgery_calls": [], "labels": []}


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
    state["prompts"].append({"player": player, "frame": state["frames"], "prompt": prompt,
                             "labels": [o[0] for o in options]})
    return out


DecisionManager.request = request

_real_roll = DiceManager.roll


def roll(self, *args, **kwargs):
    state["rolls"].append((state["frames"], kwargs.get("label", "")))
    return _real_roll(self, *args, **kwargs)


DiceManager.roll = roll

_real_begin = CrudeSurgeryController.begin_command_phase


def begin(self, squads, player):
    out = _real_begin(self, squads, player)
    state["surgery_calls"].append((state["frames"], player, out))
    return out


CrudeSurgeryController.begin_command_phase = begin

_real_button = ActionPanel._draw_button


def draw_button(self, surface, rect, label, *args, **kwargs):
    state["labels"].append((state["frames"], label))
    return _real_button(self, surface, rect, label, *args, **kwargs)


ActionPanel._draw_button = draw_button


def _squads(L):
    return list(L["state"].all_squads())


def _alive(squad):
    return [m for m in squad.models if not m.is_dead()]


def _quiet(L):
    return (not L["dice_manager"].is_pending and not L["decision_manager"].is_pending
            and L["setup_controller"].state != "placing")


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


def _set_phase(phase, owner=HUMAN):
    tracker = state["tracker"]
    tracker.phase_index = PHASES.index(phase)
    tracker.turn_owner = owner
    tracker.set_active(owner)


def _wiring(L):
    mc, reg = L["movement_controller"], L["proactive_stratagems"]
    im, kh = L["intimidating_motivation_controller"], L["keep_huntin_controller"]
    return {
        "boss_ammo_runt": isinstance(getattr(L["shooting_controller"], "boss_ammo_runt", None),
                                     BossAmmoRuntController),
        "registry": (any(isinstance(c, IntimidatingMotivationController) for c in reg.controllers)
                     and any(isinstance(c, KeepHuntinController) for c in reg.controllers)),
        "hooks": (im.on_move_started in mc.on_move_started and im.on_move_finished in mc.on_move_finished
                  and kh.on_move_started in mc.on_move_started and kh.on_move_finished in mc.on_move_finished),
        "krushin": L["krushin_impetus_controller"].on_charge_move_finished
                   in L["charge_controller"].on_charge_move_finished,
        "placer": L["crude_surgery_controller"].placer is L["return_placement_controller"],
    }


def _doc_mob(L):
    return next((s for s in _squads(L) if s.owner == HUMAN and _alive(s)
                 and any(getattr(m.profile, "crude_surgery", False) for m in _alive(s))
                 and any(getattr(m.profile, "intimidating_motivation", False) for m in _alive(s))), None)


# ----------------------------------------------------------------- B. surgery
def _stage_b(L):
    mob = _doc_mob(L)
    if mob is None:
        state["b"] = {"error": "no Player 1 Warboss + Painboy mob on the board"}
        return
    boys = [m for m in _alive(mob) if not m.profile.character and m.profile.name == "Boy"]
    doc = next(m for m in _alive(mob) if m.profile.crude_surgery)
    for m in boys[:2]:
        m.current_wounds = 0
    doc.current_wounds = doc.profile.wounds - 1
    state["b"] = {"unit": mob.name, "_mob": mob, "_doc": doc, "_dead": boys[:2], "frame": state["frames"],
                  "stage": "dying"}


def _watch_b(L):
    b = state["b"]
    mob = b["_mob"]
    if b["stage"] == "dying":
        if all(m in mob.destroyed_models for m in b["_dead"]) and _quiet(L):
            tracker = state["tracker"]
            tracker.phase_index = PHASES.index(PHASE_FIGHT)
            tracker.turn_owner = AI
            tracker.set_active(AI)
            tracker.turn_index_in_round = 0
            b["models_before"] = len(mob.models)
            b["calls_before"] = len(state["surgery_calls"])
            L["advance_turn_phase"]()
            b["stage"] = "healing"
            b["heal_frame"] = state["frames"]
            b["phase_after"] = (state["tracker"].turn_owner, state["tracker"].phase)
        elif state["frames"] - b["frame"] >= WAIT:
            b.update(done=True, error="the two Boys never left the board")
        return
    placer, setup = L["return_placement_controller"], L["setup_controller"]
    if b.get("placing") is None and setup.state == "placing":
        b["placing"] = [m.profile.name for m in (setup.placing_models or [])]
        b["placing_squad"] = getattr(placer.pending_squad, "name", None)
        placer.confirm()
    if b.get("placing") is not None or state["frames"] - b["heal_frame"] >= WAIT:
        b["done"] = True
        b["calls"] = state["surgery_calls"][b["calls_before"]:]
        b["models_after"] = len(mob.models)
        b["doc_wounds"] = (b["_doc"].current_wounds, b["_doc"].profile.wounds)
        b["revived_on_board"] = sum(1 for m in b["_dead"] if m in L["state"].tokens and not m.is_dead())


# ----------------------------------------------------------------- C. krushin
def _stage_c(L):
    st = L["state"]
    target = max((s for s in _squads(L) if s.owner == AI and len(_alive(s)) >= 5
                  and s.embarked_in is None and any(m in st.tokens for m in _alive(s))),
                 key=lambda s: len(_alive(s)), default=None)
    if target is None:
        state["c"] = {"error": "no Player 2 unit of 5+ models on the board"}
        return
    alive = [m for m in _alive(target) if m in st.tokens]
    anchor = alive[0]
    mob = attach(build_squad(WARBOSS_MEGA_ARMOUR, HUMAN, name="1 Warboss in Mega Armour (staged)"),
                 build_squad(MEGANOBZ, HUMAN, name="1 Meganobz (staged)"), game_state=st)
    for i, model in enumerate(mob.models):
        partner = alive[i % len(alive)]
        model.x_in = partner.x_in
        model.y_in = partner.y_in - partner.profile.base_radius_in - model.profile.base_radius_in - 0.5
    for model in mob.models:
        st.add_token(model)
    engaged = [s.name for s in krushin_impetus.targets(mob, st.tokens)]
    wounds_before = sum(m.current_wounds for m in target.models)
    rolls_before = len(state["rolls"])
    for listener in list(L["charge_controller"].on_charge_move_finished):
        listener(mob)
    labels = [label for _f, label in state["rolls"][rolls_before:]]
    state["c"] = {"unit": mob.name, "target": target.name, "_target": target, "engaged": engaged,
                  "frame": state["frames"], "krushin_rolls": [x for x in labels if "Krushin" in x],
                  "wounds_before": wounds_before, "anchor": anchor.id}


def _watch_c(L):
    c = state["c"]
    ctrl = L["krushin_impetus_controller"]
    settled = (not ctrl.is_busy and ctrl.pending_damage_choice is None and ctrl.mortal_wound_session is None
               and not L["dice_manager"].is_pending)
    if settled or state["frames"] - c["frame"] >= WAIT:
        c["done"] = True
        c["settled"] = settled
        c["open_choice_owner"] = (ctrl.pending_damage_choice[0].squad.owner
                                  if ctrl.pending_damage_choice else None)
        c["wounds_lost"] = c["wounds_before"] - sum(max(0, m.current_wounds) for m in c["_target"].models)


# ------------------------------------------------------------ D. the button
def _stage_d(L):
    mob = _doc_mob(L)
    if mob is None:
        state["d"] = {"error": "no Player 1 Warboss mob left on the board"}
        return
    L["movement_controller"].moved_squad_ids.discard(mob)
    _set_phase(PHASE_MOVEMENT)
    L["movement_controller"].select(_alive(mob)[0])
    state["d"] = {"unit": mob.name, "_mob": mob, "frame": state["frames"],
                  "labels_before": len(state["labels"]),
                  "why_not": L["intimidating_motivation_controller"].why_not(mob)}


def _watch_d(L):
    d = state["d"]
    mob = d["_mob"]
    tracker = state["tracker"]
    if tracker.phase != PHASE_MOVEMENT or tracker.turn_owner != HUMAN:
        _set_phase(PHASE_MOVEMENT)
    if L["movement_controller"].selected_squad is not mob:
        L["movement_controller"].select(_alive(mob)[0])
    drawn = [lab for _f, lab in state["labels"][d["labels_before"]:] if lab.startswith("Intimidating Motivation")]
    if drawn or state["frames"] - d["frame"] >= WAIT:
        d["done"] = True
        d["drawn"] = drawn[:1]
        ctrl = L["intimidating_motivation_controller"]
        d["why_not_at_end"] = ctrl.why_not(mob)
        if drawn:
            prompts_before = len(state["prompts"])
            used = ctrl.use(mob)
            decisions = L["decision_manager"]
            picked = None
            if decisions.is_pending and "Intimidating Motivation" in (decisions.prompt or ""):
                tagged = [i for i, o in enumerate(decisions.options) if o.get("squad") is not None]
                if tagged:
                    picked = decisions.options[tagged[0]]["squad"].name
                    decisions.choose(tagged[0])
            d["used"] = used
            d["prompted"] = len(state["prompts"]) > prompts_before
            d["picked"] = picked
            d["spent"] = ctrl.is_spent(HUMAN)


# ------------------------------------------------------- E. Boss' Ammo Runt
def _stage_e(L):
    mob = _doc_mob(L)
    if mob is None:
        state["e"] = {"error": "no Player 1 Warboss mob left on the board"}
        return
    _set_phase(PHASE_SHOOTING)
    sc = L["shooting_controller"]
    prompts_before = len(state["prompts"])
    try:
        sc.start_shooting(mob)
    except Exception as exc:          # a probe must report, not crash the loop
        state["e"] = {"error": "start_shooting raised %r" % exc}
        return
    decisions = L["decision_manager"]
    for _ in range(6):
        if not decisions.is_pending:
            break
        labels = [o["label"] for o in decisions.options]
        decisions.choose(labels.index("Save it for later") if "Save it for later" in labels else len(labels) - 1)
    try:
        sc.cancel()
    except Exception:
        pass
    asked = [p for p in state["prompts"][prompts_before:] if "Ammo Runt" in (p["prompt"] or "")]
    state["e"] = {"unit": mob.name, "asked": asked, "used_after": bool(getattr(mob, "boss_ammo_runt_used", False)),
                  "done": True}


def flip(*args, **kwargs):
    state["frames"] += 1
    tracker = state["tracker"]
    if tracker is not None and getattr(tracker, "started", False):
        L = _main_locals()
        if L is not None and "crude_surgery_controller" in L:
            if state["wiring"] is None:
                state["wiring"] = _wiring(L)
            _decline_stale_human_prompt(L.get("decision_manager"))
            for key, stage, watch, gate in (("b", _stage_b, _watch_b, lambda: state["frames"] >= STAGE_AT),
                                            ("c", _stage_c, _watch_c, lambda: True),
                                            ("d", _stage_d, _watch_d, lambda: True),
                                            ("e", _stage_e, None, lambda: True)):
                record = state[key]
                if record is None:
                    if gate() and _quiet(L):
                        stage(L)
                    break
                if not record.get("done") and not record.get("error"):
                    watch(L)
                    break
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
e = state["e"] or {}


def _err(record):
    return (" ERROR " + record["error"]) if record.get("error") else ""


print()
print("--- Ork characters, live" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
print("  frames                              : %d" % state["frames"])
print("  A. Boss' Ammo Runt on ShootingController : %s" % w.get("boss_ammo_runt"))
print("     motivations on the registry / hooks   : %s / %s" % (w.get("registry"), w.get("hooks")))
print("     Krushin' Impetus on the charge-end hook : %s" % w.get("krushin"))
print("     Crude Surgery holds main()'s placer     : %s" % w.get("placer"))
print("  B. %s%s" % (b.get("unit"), _err(b)))
print("     advance -> %s, Crude Surgery calls: %s" % (b.get("phase_after"), b.get("calls")))
print("     models %s -> %s, Painboy wounds %s, revived on board %s" % (
    b.get("models_before"), b.get("models_after"), b.get("doc_wounds"), b.get("revived_on_board")))
print("     placement opened for the human: %s (%s)" % (b.get("placing"), b.get("placing_squad")))
print("  C. %s beside %s, engaged: %s%s" % (cc.get("unit"), cc.get("target"), cc.get("engaged"), _err(cc)))
print("     rolls: %s, settled: %s, open choice owner: %s, wounds lost: %s" % (
    cc.get("krushin_rolls"), cc.get("settled"), cc.get("open_choice_owner"), cc.get("wounds_lost")))
print("  D. %s%s: why_not %r -> %r" % (d.get("unit"), _err(d), d.get("why_not"), d.get("why_not_at_end")))
print("     drawn: %s, used: %s, prompted: %s, picked: %s, spent: %s" % (
    d.get("drawn"), d.get("used"), d.get("prompted"), d.get("picked"), d.get("spent")))
print("  E. %s%s: prompts %s, spend after decline: %s" % (
    e.get("unit"), _err(e), [(p["player"], p["labels"]) for p in e.get("asked") or []], e.get("used_after")))
print("  stale Player 1 prompts declined     : %s" % (state["declined_other"] or "none"))

if not state["wiring"] or any(r.get("error") for r in (b, cc, d, e)) or not e.get("done"):
    print("  INCONCLUSIVE - the run never got through the staging")
    raise SystemExit(2)

if not NEUTRALIZE:
    checks = (
        ("the live ShootingController holds Boss' Ammo Runt", w.get("boss_ammo_runt") is True),
        ("both motivations are on the live registry", w.get("registry") is True),
        ("...and on the live MovementController's two hooks", w.get("hooks") is True),
        ("Krushin' Impetus listens on the live charge-end hook", w.get("krushin") is True),
        ("Crude Surgery holds main()'s return placer", w.get("placer") is True),
        ("main()'s Command-phase boundary begins Crude Surgery for Player 1",
         any(player == HUMAN and out for _f, player, out in b.get("calls") or [])),
        ("...the Painboy is topped up", b.get("doc_wounds") and b["doc_wounds"][0] == b["doc_wounds"][1]),
        ("...both Boys come back", (b.get("models_after") or 0) - (b.get("models_before") or 0) == 2),
        ("...set up by the HUMAN through the placement flow", bool(b.get("placing"))),
        ("...and stand on the board after the confirm", b.get("revived_on_board") == 2),
        ("the staged Warboss in Mega Armour mob is engaged with the Player 2 unit", cc.get("target") in (cc.get("engaged") or [])),
        ("ending its charge through main()'s listeners rolls Krushin' Impetus", bool(cc.get("krushin_rolls"))),
        ("...and the whole thing settles - the AI allocates its own mortal wounds", cc.get("settled") is True),
        ("Intimidating Motivation is DRAWN on main()'s panel for the Warboss mob", bool(d.get("drawn"))),
        ("...and pressing it spends the army's use", d.get("spent") is True),
        ("Boss' Ammo Runt is asked when the mob is selected to shoot",
         any("Use Boss' Ammo Runt" in p["labels"] for p in e.get("asked") or [])),
        ("...and declining spends nothing", e.get("used_after") is False),
    )
else:
    checks = (
        ("no Boss' Ammo Runt on the live ShootingController", w.get("boss_ammo_runt") is False),
        ("no motivation on the live registry", w.get("registry") is False),
        ("...nor on the hooks", w.get("hooks") is False),
        ("Krushin' Impetus does not listen", w.get("krushin") is False),
        ("the boundary never begins Crude Surgery", not any(out for _f, _p, out in b.get("calls") or [])),
        ("no Krushin' Impetus roll", not cc.get("krushin_rolls")),
        ("Intimidating Motivation is never drawn", not d.get("drawn")),
        ("no Boss' Ammo Runt prompt", not any("Use Boss' Ammo Runt" in p["labels"] for p in e.get("asked") or [])),
    )
failed = 0
for label, ok in checks:
    print("  %s  %s" % ("PASS" if ok else "FAIL", label))
    failed += 0 if ok else 1
raise SystemExit(1 if failed else 0)
