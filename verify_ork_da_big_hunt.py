"""Runtime proof through the REAL main() loop that Da Big Hunt (Mecha Orks stage
G5) is wired: Da Hunt is On, Glory Hog and all three Stratagems - on main()'s own
objects.

test_ork_da_big_hunt.py drives every piece through real controllers built by the
test and pins main.py by AST. What it cannot show is that MAIN'S objects, built
by MAIN'S constructors in MAIN'S order, are connected when the game runs. So this
runs selfplay.py's real main() loop with the ORKS AS PLAYER 1 and asks main()'s
live objects:

  A. THE WIRING: Where D'ya Fink You're Going? stands in main()'s
     fall_back_controller.on_fall_back_declared and holds main()'s token list;
     Goaded into Action holds main()'s ShootingController (its wound ledger),
     MovementController and both injected AI policies; Instinctive Hunters holds
     main()'s GameState and turn tracker.
  B. DA HUNT IS ON on main()'s ShootingController: a Beast Snagga Boyz unit's
     gun gains +1 AP against a Necron VEHICLE and nothing against infantry.
  C. GLORY HOG on main()'s ChargeController: a Beastboss that has fallen back
     may still declare a charge - the printed half - while an ordinary Warboss
     may not.
  D. WHERE D'YA FINK YOU'RE GOING? at main()'s fall-back declaration: a Necron
     VEHICLE engaged with the Beast Snaggas is selected to fall back, main()'s
     listener raises the offer, it is bought (1CP), Ordered Retreat is then
     refused, and the hazard rolls it owes are 3 more than its models.
  E. GOADED INTO ACTION at main()'s end-of-shooting hook and its ONE
     acknowledgement door: the hook is fired as ShootingController fires it, the
     offer is bought (1CP), the D6 lands on main()'s dice manager, and
     _acknowledge_pending_roll() opens a "surge" move on main()'s
     MovementController with the reacting player holding active_player.
  F. INSTINCTIVE HUNTERS at main()'s end-of-Fight boundary: a Beast Snagga unit
     within 6" of a board edge is offered, picked, paid for and put into
     Strategic Reserves.

STAGED, each named rather than quietly faked:
  * THE ORKS AS PLAYER 1, Player 2 Necrons; the units are BUILT (the shipped list
    fields War Horde until stage G6). config.DA_BIG_HUNT_PLAYERS is set for both
    players and config.WAR_HORDE_PLAYERS cleared at the first stage.
  * The clock for each stage, CP topped up.
  * D and E stage the moment rather than the match: a MockAgent run does not
    reliably produce a Necron VEHICLE choosing to fall back out of an Ork
    Engagement Range, nor a Necron unit wounding one particular Beast Snagga
    unit. D calls main()'s fall_back_controller.declare() (the method the Fall
    Back button calls); E stamps the ShootingController's activation ledger the
    way _handle_hit_results() stamps it and then fires main()'s own listener
    list. Everything after those two calls is the engine's.
  * Player 1 prompts this harness does not answer are declined after STALE_FRAMES.

--neutralize loads main.py through an import hook with the main() seams undone
(the fall-back listener, the after-shooting hook, the D6 acknowledgement, the
end-of-Fight offer) and swaps the two rule answers (Da Hunt is On, Glory Hog)
for "nothing". The files on disk are not touched.

Usage:  python verify_ork_da_big_hunt.py [map2] [frames]
        python verify_ork_da_big_hunt.py map2 --neutralize
"""

import importlib.abc
import importlib.util
import math
import os
import runpy
import sys

import pygame

from game import (config, da_big_hunt, da_hunt_goaded_into_action as goaded,
                  da_hunt_instinctive_hunters as hunters, da_hunt_where_dya_fink as wdf,
                  enh_glory_hog, enhancements, fall_back as fall_back_module,
                  forced_desperate_escape)
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import build_squad
from game.factions.necrons import GHOST_ARK, NECRON_WARRIORS
from game.factions.orks import BEAST_SNAGGA_BOYZ, BEASTBOSS, WARBOSS
from game.turn import PHASES, PHASE_FIGHT, PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker
from game.weapons import RANGED

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

HUMAN, AI = "Player 1", "Player 2"
STAGE_AT = 150
STALE_FRAMES = 30

NEUTRALIZE_EDITS = (
    (",\n        where_dya_fink_controller.notify_selected_to_fall_back]", "]"),
    ("    shooting_controller.on_squad_finished_shooting.append(\n"
     "        goaded_into_action_controller.on_squad_finished_shooting)\n", ""),
    ("        goaded_into_action_controller.on_dice_acknowledged()\n", ""),
    ("            instinctive_hunters_controller.offer_at_end_of_fight_phase(\n"
     "                {t.squad for t in state.tokens if t.squad is not None}, mover_before)\n", ""),
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
    da_big_hunt.applies = lambda squad, target_squad=None: False
    enh_glory_hog.applies = lambda squad: False

STAGES = ("b", "c", "d", "e", "f")
state = {"frames": 0, "tracker": None, "wiring": None, "stale": None, "stale_since": 0, "staged": False,
         "declined_other": [], "prompts": [], "rolls": []}
for _key in STAGES:
    state[_key] = None
state["c_before"] = None


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
    state["prompts"].append({"player": player, "frame": state["frames"], "prompt": prompt or "",
                             "labels": [o[0] for o in options]})
    return out


DecisionManager.request = request

_real_roll = DiceManager.roll


def roll(self, count, sides=6, **kwargs):
    state["rolls"].append((state["frames"], kwargs.get("label", ""), kwargs.get("target_name")))
    return _real_roll(self, count, sides, **kwargs)


DiceManager.roll = roll


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
    if (wdf.WHERE_DYA_FINK_NAME in prompt or goaded.GOADED_INTO_ACTION_NAME in prompt
            or hunters.INSTINCTIVE_HUNTERS_NAME in prompt):
        return
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


def _layout(center, count, spacing=1.4, per_row=5):
    rows = (count + per_row - 1) // per_row
    cols = min(count, per_row)
    return [(center[0] + (i % per_row - (cols - 1) / 2.0) * spacing,
             center[1] + (i // per_row - (rows - 1) / 2.0) * spacing) for i in range(count)]


def _fits(L, squad, spots, clearance=1.2):
    setup = L["setup_controller"]
    tokens = [t for t in L["state"].tokens if not t.is_dead() and t.squad is not squad]
    for model, (x, y) in zip(squad.models, spots):
        if not setup.position_valid(model, x, y, squad=squad):
            return False
        if any(math.hypot(x - t.x_in, y - t.y_in) < model.radius_in + t.radius_in + clearance for t in tokens):
            return False
    return True


def _gap_to(L, owner, spots, squad=None):
    others = [t for t in L["state"].tokens if not t.is_dead() and t.squad is not None
              and (t.squad is squad if squad is not None else t.squad.owner != owner)]
    return min((math.hypot(x - t.x_in, y - t.y_in) - t.radius_in for x, y in spots for t in others), default=99.0)


def _place_somewhere(L, squad, want, clearance=1.2, step=1.0):
    setup = L["setup_controller"]
    best = None
    y = 3.0
    while y < setup.board_height_in - 3.0:
        x = 3.0
        while x < setup.board_width_in - 3.0:
            spots = _layout((x, y), len(squad.models))
            score = want(spots)
            if score is not None and (best is None or score > best[0]) and _fits(L, squad, spots, clearance):
                best = (score, spots)
            x += step
        y += step
    if best is None:
        return None
    for model, (x, y) in zip(squad.models, best[1]):
        model.x_in, model.y_in = x, y
        L["state"].add_token(model)
    return best[0]


def _clear_of_enemy(L, owner, squad, least=8.0, prefer=16.0):
    return _place_somewhere(L, squad, lambda spots: -abs(_gap_to(L, owner, spots) - prefer)
                            if _gap_to(L, owner, spots) > least else None)


def _beside(L, squad, other, lo=1.0, hi=3.0, clearance=0.3):
    return _place_somewhere(L, squad, lambda spots: -_gap_to(L, squad.owner, spots, squad=other)
                            if lo < _gap_to(L, squad.owner, spots, squad=other) < hi else None, clearance=clearance)


def _near_edge(L, squad, within=5.0):
    """A legal spot whose models are all within `within` of a board edge - the
    printed TARGET of Instinctive Hunters."""
    setup = L["setup_controller"]

    def want(spots):
        far = max(min(x, y, setup.board_width_in - x, setup.board_height_in - y) for x, y in spots)
        return -far if far <= within and _gap_to(L, squad.owner, spots) > 6.0 else None

    return _place_somewhere(L, squad, want)


def _stage_everything(L):
    if not state["staged"]:
        config.DA_BIG_HUNT_PLAYERS = (HUMAN, AI)
        config.WAR_HORDE_PLAYERS = ()
        state["staged"] = True


def _wiring(L):
    w = L.get("where_dya_fink_controller")
    g = L.get("goaded_into_action_controller")
    h = L.get("instinctive_hunters_controller")
    listeners = list(L["fall_back_controller"].on_fall_back_declared or ())
    return {
        "where_dya_fink": isinstance(w, wdf.WhereDyaFinkController)
        and w.notify_selected_to_fall_back in listeners and w.all_tokens is L["state"].tokens
        and w.decision_manager is L["decision_manager"],
        "goaded": isinstance(g, goaded.GoadedIntoActionController)
        and g.shooting_controller is L["shooting_controller"]
        and g.movement_controller is L["movement_controller"]
        and g.on_squad_finished_shooting in list(L["shooting_controller"].on_squad_finished_shooting)
        and g.ai_destination is not None and g.ai_mover is not None,
        "hunters": isinstance(h, hunters.InstinctiveHuntersController)
        and h.game_state is L["state"] and h.turn_tracker is L["turn_tracker"],
    }


def _answer(L, needle, pick):
    """Answer main()'s prompt whose text contains `needle`; `pick` chooses the
    option by label substring.

    Prompts ahead of it in the queue are declined (their last option) rather
    than waited out: a phase boundary can raise several at once, and the one
    this stage is about is not always at the front."""
    decisions = L["decision_manager"]
    for _ in range(8):
        if not decisions.is_pending:
            return None
        if needle not in (decisions.prompt or ""):
            state["declined_other"].append((decisions.prompt or "")[:60])
            decisions.choose(len(decisions.options) - 1)
            continue
        index = next((i for i, o in enumerate(decisions.options) if pick.lower() in o["label"].lower()), None)
        if index is None:
            return False
        label = decisions.options[index]["label"]
        decisions.choose(index)
        return label
    return None


# ------------------------------------------------------ B. Da Hunt is On
def _stage_b(L):
    _stage_everything(L)
    mob = build_squad(BEAST_SNAGGA_BOYZ, HUMAN, name="1 Beast Snagga Boyz (B)")
    if _clear_of_enemy(L, HUMAN, mob) is None:
        state["b"] = {"error": "no ground for the Beast Snaggas"}
        return
    ark = build_squad(GHOST_ARK, AI, name="2 Ghost Ark (B)")
    if _clear_of_enemy(L, AI, ark, least=10.0, prefer=20.0) is None:
        state["b"] = {"error": "no ground for the Ghost Ark"}
        return
    warriors = next((s for s in L["state"].all_squads() if s.owner == AI and _alive(s)
                     and not any(m.profile.vehicle or m.profile.monster for m in _alive(s))), None)
    sc = L["shooting_controller"]
    model = next(m for m in _alive(mob) if any(w.weapon_type == RANGED for w in m.weapons))
    gun = next(w for w in model.weapons if w.weapon_type == RANGED)
    _set_phase(PHASE_SHOOTING)
    saved = sc.active_squad
    try:
        sc.active_squad = mob
        vs_vehicle = sc._adjusted_weapon([(model, gun)], ark).ap
        vs_infantry = sc._adjusted_weapon([(model, gun)], warriors).ap if warriors is not None else None
    finally:
        sc.active_squad = saved
    state["b"] = {"gun": gun.name, "printed": gun.ap, "vs_vehicle": vs_vehicle, "vs_infantry": vs_infantry,
                  "infantry": getattr(warriors, "name", None), "_mob": mob, "done": True}


# ------------------------------------------------------ C. Glory Hog
def _stage_c(L):
    boss = build_squad(BEASTBOSS, HUMAN, name="1 Beastboss (C)")
    warboss = build_squad(WARBOSS, HUMAN, name="1 Warboss (C)")
    for squad in (boss, warboss):
        # Within charge range of something and outside Engagement Range of it:
        # can_declare_charge() asks both, and neither is what this stage is about.
        if _place_somewhere(L, squad, lambda spots: -_gap_to(L, HUMAN, spots)
                            if 3.0 < _gap_to(L, HUMAN, spots) < 10.0 else None) is None:
            state["c"] = {"error": "no ground 3-10\" from a Player 2 unit for %s" % squad.name}
            return
    granted = True
    try:
        enhancements.grant(boss, enh_glory_hog.GLORY_HOG)
    except ValueError as exc:
        granted = str(exc)
    cc = L["charge_controller"]
    from game.turn import PHASE_CHARGE
    _set_phase(PHASE_CHARGE)
    state["c_before"] = (cc.can_declare_charge(boss), cc.can_declare_charge(warboss))
    for squad in (boss, warboss):
        squad.fell_back_this_turn = True
    # The control: the same two units BEFORE the fall-back flag - if a charge
    # were impossible here anyway, this stage would prove nothing.
    state["c"] = {"granted": granted, "bearer": cc.can_declare_charge(boss),
                  "plain": cc.can_declare_charge(warboss),
                  "before": state["c_before"], "done": True}


# ---------------------------------- D. Where D'ya Fink You're Going?
def _stage_d(L):
    mob = build_squad(BEAST_SNAGGA_BOYZ, HUMAN, name="1 Beast Snagga Boyz (D)")
    if _clear_of_enemy(L, HUMAN, mob) is None:
        state["d"] = {"error": "no ground for the Beast Snaggas"}
        return
    ark = build_squad(GHOST_ARK, AI, name="2 Ghost Ark (D)")
    _r = ark.models[0].radius_in
    if _beside(L, ark, mob, lo=_r + 0.3, hi=_r + 1.6, clearance=0.05) is None:
        state["d"] = {"error": "no ground beside the Beast Snaggas"}
        return
    _set_phase(PHASE_MOVEMENT, AI)
    L["command_points"].cp[HUMAN] = max(L["command_points"].cp.get(HUMAN, 0), 3)
    cp = L["command_points"].cp[HUMAN]
    fb = L["fall_back_controller"]
    prompts_before = len(state["prompts"])
    fb.declare(ark)
    asked = [p for p in state["prompts"][prompts_before:] if wdf.WHERE_DYA_FINK_NAME in p["prompt"]]
    picked = _answer(L, wdf.WHERE_DYA_FINK_NAME, "use")
    fb.choose_mode(fall_back_module.ORDERED_RETREAT)
    after_ordered = fb.mode
    fb.choose_mode(fall_back_module.DESPERATE_ESCAPE)
    tokens = L["state"].tokens
    state["d"] = {"engaged": ark.is_engaged_with(mob), "asked": [p["labels"] for p in asked], "picked": picked,
                  "paid": cp - L["command_points"].cp[HUMAN], "marked": wdf.is_marked(mob),
                  "after_ordered": after_ordered, "mode": fb.mode,
                  "extra_rolls": forced_desperate_escape.extra_hazard_rolls(ark, tokens),
                  "reasons": forced_desperate_escape.reasons(ark, tokens), "done": True}
    fb.decline()


# ------------------------------------------------------ E. Goaded into Action
def _stage_e(L):
    mob = state["b"].get("_mob") if state["b"] else None
    if mob is None or not _alive(mob):
        mob = build_squad(BEAST_SNAGGA_BOYZ, HUMAN, name="1 Beast Snagga Boyz (E)")
        if _clear_of_enemy(L, HUMAN, mob) is None:
            state["e"] = {"error": "no ground for the Beast Snaggas"}
            return
    shooter = next((s for s in L["state"].all_squads() if s.owner == AI and _alive(s)
                    and all(m in L["state"].tokens for m in _alive(s))), None)
    if shooter is None:
        state["e"] = {"error": "no Player 2 unit on the board to have shot"}
        return
    sc = L["shooting_controller"]
    _set_phase(PHASE_SHOOTING, AI)
    L["command_points"].cp[HUMAN] = max(L["command_points"].cp.get(HUMAN, 0), 3)
    cp = L["command_points"].cp[HUMAN]
    # The activation ledger, stamped as _handle_hit_results() stamps it when an
    # attack hits: the unit's wound total the moment it was first hit. One wound
    # is then taken off a model, which is what "lost a wound" means.
    victim = _alive(mob)[0]
    sc.active_squad = shooter
    sc._hit_target_squads_this_activation = {mob}
    sc._wounds_when_hit_this_activation = {id(mob): sum(m.current_wounds for m in _alive(mob))}
    victim.current_wounds = max(victim.current_wounds - 1, 1)
    wounded = [s.name for s in sc.squads_wounded_this_activation()]
    prompts_before = len(state["prompts"])
    for listener in list(sc.on_squad_finished_shooting):
        listener(shooter, sc._hit_target_squads_this_activation)
    sc.active_squad = None
    asked = [p for p in state["prompts"][prompts_before:] if goaded.GOADED_INTO_ACTION_NAME in p["prompt"]]
    picked = _answer(L, goaded.GOADED_INTO_ACTION_NAME, mob.name)
    dice = L["dice_manager"]
    d6 = list(dice.pending_values or ())
    label = dice.label if hasattr(dice, "label") else ""
    opened = None
    if dice.is_pending:
        try:
            L["_acknowledge_pending_roll"]()
        except Exception as exc:
            state["e"] = {"error": "_acknowledge_pending_roll raised %r" % exc}
            return
        mc = L["movement_controller"]
        opened = {"mode": mc.move_mode, "squad": getattr(mc.selected_squad, "name", None),
                  "active": state["tracker"].active_player,
                  "max": round(max(mc.remaining_range.values()), 2) if mc.remaining_range else None}
        L["goaded_into_action_controller"].cancel_move()
    state["e"] = {"shooter": shooter.name, "wounded": wounded, "asked": [p["labels"] for p in asked],
                  "picked": picked, "paid": cp - L["command_points"].cp[HUMAN], "d6": d6, "label": label,
                  "opened": opened, "done": True}


# ------------------------------------------------------ F. Instinctive Hunters
def _stage_f(L):
    mob = build_squad(BEAST_SNAGGA_BOYZ, HUMAN, name="1 Beast Snagga Boyz (F)")
    if _near_edge(L, mob) is None:
        state["f"] = {"error": "no ground within 6\" of a board edge"}
        return
    L["command_points"].cp[HUMAN] = max(L["command_points"].cp.get(HUMAN, 0), 3)
    _set_phase(PHASE_FIGHT, AI)
    prompts_before = len(state["prompts"])
    try:
        L["advance_turn_phase"]()
    except Exception as exc:
        state["f"] = {"error": "advance_turn_phase raised %r" % exc}
        return
    # From HERE: Fight is the last phase, so the boundary itself has already
    # opened the next Command phase and paid its core CP.
    cp = L["command_points"].cp[HUMAN]
    asked = [p for p in state["prompts"][prompts_before:] if hunters.INSTINCTIVE_HUNTERS_NAME in p["prompt"]]
    picked = _answer(L, hunters.INSTINCTIVE_HUNTERS_NAME, mob.name)
    state["f"] = {"asked": [p["labels"] for p in asked], "picked": picked,
                  "paid": cp - L["command_points"].cp[HUMAN],
                  "in_reserves": mob in L["state"].reserves,
                  "off_board": not any(m in L["state"].tokens for m in mob.models), "done": True}


STAGE = {"b": _stage_b, "c": _stage_c, "d": _stage_d, "e": _stage_e, "f": _stage_f}


def flip(*args, **kwargs):
    state["frames"] += 1
    tracker = state["tracker"]
    if tracker is not None and getattr(tracker, "started", False):
        L = _main_locals()
        if L is not None and "fight_controller" in L and "proactive_stratagems" in L:
            if state["wiring"] is None:
                state["wiring"] = _wiring(L)
            _decline_stale_human_prompt(L.get("decision_manager"))
            for key in STAGES:
                record = state[key]
                if record is None:
                    if state["frames"] >= STAGE_AT and _quiet(L):
                        STAGE[key](L)
                    break
                if record.get("error"):
                    raise SystemExit(0)
                if not record.get("done"):
                    break
            else:
                raise SystemExit(0)
    return _real_flip(*args, **kwargs)


_real_flip = pygame.display.flip
pygame.display.flip = flip

_argv = sys.argv[1:] or ["map2", "6000"]
sys.argv = ["selfplay.py"] + _argv
config.PLAYER1_ARMY = "orks"
config.PLAYER2_ARMY = "necrons"
config.ARMY_SELECT = False

try:
    runpy.run_module("selfplay", run_name="__main__")
except SystemExit:
    pass

w = state["wiring"] or {}
b, cc, d, e, f = (state[k] or {} for k in STAGES)


def _err(record):
    return (" ERROR " + record["error"]) if record.get("error") else ""


print()
print("--- Ork Da Big Hunt, live" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
print("  frames                                 : %d" % state["frames"])
print("  A. Where D'ya Fink %s, Goaded %s, Instinctive Hunters %s" % (
    w.get("where_dya_fink"), w.get("goaded"), w.get("hunters")))
print("  B. %s printed AP %s: vs a Ghost Ark %s, vs %s %s%s" % (
    b.get("gun"), b.get("printed"), b.get("vs_vehicle"), b.get("infantry"), b.get("vs_infantry"), _err(b)))
print("  C. Glory Hog granted %s: after falling back the Beastboss may charge %s, the Warboss %s%s" % (
    cc.get("granted"), cc.get("bearer"), cc.get("plain"), _err(cc)))
print("  D. engaged %s, asked %s, picked %s, paid %s, marked %s; Ordered Retreat -> %s, mode %s, "
      "extra rolls %s, reasons %s%s" % (
          d.get("engaged"), d.get("asked"), d.get("picked"), d.get("paid"), d.get("marked"),
          d.get("after_ordered"), d.get("mode"), d.get("extra_rolls"), d.get("reasons"), _err(d)))
print("  E. %s shot; wounded %s, asked %s, picked %s, paid %s, D6 %s -> %s%s" % (
    e.get("shooter"), e.get("wounded"), e.get("asked"), e.get("picked"), e.get("paid"), e.get("d6"),
    e.get("opened"), _err(e)))
print("  F. asked %s, picked %s, paid %s, in reserves %s, off the board %s%s" % (
    f.get("asked"), f.get("picked"), f.get("paid"), f.get("in_reserves"), f.get("off_board"), _err(f)))
print("  stale Player 1 prompts declined        : %s" % (state["declined_other"] or "none"))

if not state["wiring"] or any(r.get("error") for r in (b, cc, d, e, f)) or not f.get("done"):
    print("  INCONCLUSIVE - the run never got through the staging")
    raise SystemExit(2)

if not NEUTRALIZE:
    checks = (
        ("all three controllers hold main()'s collaborators",
         w.get("where_dya_fink") and w.get("goaded") and w.get("hunters")),
        ("Da Hunt is On gives +1 AP against a VEHICLE on main()'s ShootingController, and nothing else",
         b.get("vs_vehicle") == b.get("printed") - 1 and b.get("vs_infantry") == b.get("printed")),
        ("Glory Hog lets the Beastboss declare a charge after falling back; the Warboss may not",
         cc.get("granted") is True and cc.get("bearer") is True and cc.get("plain") is False),
        ("main()'s fall-back declaration offers Where D'ya Fink You're Going?, and it is bought for 1CP",
         bool(d.get("asked")) and d.get("picked") is not None and d.get("paid") == 1 and d.get("marked") is True),
        ("...Ordered Retreat is then refused and the VEHICLE owes 3 extra hazard rolls",
         d.get("after_ordered") is None and d.get("mode") == fall_back_module.DESPERATE_ESCAPE
         and d.get("extra_rolls") == 3 and wdf.WHERE_DYA_FINK_NAME in (d.get("reasons") or [])),
        ("main()'s after-shooting hook offers Goaded into Action to the unit that lost a wound (1CP)",
         e.get("wounded") and bool(e.get("asked")) and e.get("picked") is not None and e.get("paid") == 1),
        ("...and main()'s acknowledgement door turns its D6 into an open surge move",
         (e.get("opened") or {}).get("mode") == goaded.GOADED_MOVE_MODE
         and (e.get("opened") or {}).get("active") == HUMAN
         and (e.get("opened") or {}).get("max") == float(sum(e.get("d6") or [0]))),
        ("Instinctive Hunters is offered at main()'s end-of-Fight boundary; picked, 1CP, into reserves",
         bool(f.get("asked")) and f.get("picked") is not None and f.get("paid") == 1
         and f.get("in_reserves") is True and f.get("off_board") is True),
    )
else:
    checks = (
        ("Da Hunt is On does nothing: the printed AP stands against a VEHICLE",
         b.get("vs_vehicle") == b.get("printed")),
        ("Glory Hog does nothing: the Beastboss may not charge after falling back", cc.get("bearer") is False),
        ("Where D'ya Fink You're Going? is never offered, and Ordered Retreat is allowed",
         not d.get("asked") and d.get("after_ordered") == fall_back_module.ORDERED_RETREAT),
        ("Goaded into Action never hears the shooting end", not e.get("asked") and not e.get("paid")),
        ("Instinctive Hunters is never offered", not f.get("asked") and f.get("in_reserves") is False),
    )
failed = 0
for label, ok in checks:
    print("  %s  %s" % ("PASS" if ok else "FAIL", label))
    failed += 0 if ok else 1
print("  %d/%d" % (len(checks) - failed, len(checks)))
raise SystemExit(1 if failed else 0)
