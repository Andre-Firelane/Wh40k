"""Runtime proof through the REAL main() loop that Blitz Brigade (Mecha Orks stage
G4) is wired: Unstoppable Momentum's two halves, both Enhancements, both wired
Stratagems - on main()'s own objects.

test_ork_blitz_brigade.py drives every piece through real controllers built by
the test and pins main.py by AST. What it cannot show is that MAIN'S objects,
built by MAIN'S constructors in MAIN'S order, are connected when the game runs.
So this runs selfplay.py's real main() loop with the ORKS AS PLAYER 1 and asks
main()'s live objects:

  A. THE WIRING: Unstoppable Momentum's charge re-roll holds main()'s dice and
     charge controller; Impending Krunch main()'s BattleShockController (through
     its queue), DecisionManager and token list; Keep It Runnin' main()'s
     TransportController and FightController; the ShootingController's
     embarked-units view IS main()'s embarked list.
  H. THE AI'S IMPENDING KRUNCH: a Player 2 Battlewagon ends a charge move engaged
     with a Player 1 unit in Player 2's Charge phase - main()'s charge-end hook
     list is fired exactly as confirm_charge_move() fires it, and the AI buys the
     Stratagem (1CP) and the Player 1 unit's Battle-shock test at -1 is thrown.
  C. THE AI'S CHARGE RE-ROLL through main()'s ONE acknowledgement door
     (_acknowledge_pending_roll): a Player 2 Battlewagon's charge roll of 3
     that reaches nothing is re-rolled in full, unasked.
  B. THE ADVANCE on main()'s MovementController: Player 1's Battlewagon advances
     6" and no die is thrown.
  D. TARGETIN' GIZMOS on main()'s ShootingController: a Big Mek-led Meganobz
     unit embarked by main()'s TransportController; the Gunwagon's gun gains
     [IGNORES COVER], and the real Hit modifiers carry no Benefit of Cover.
  E. BOSS BOOMER DRAWN on main()'s ActionPanel: a Battlewagon carrying a Warboss
     shows Intimidating Motivation in Player 1's Movement phase; pressed, it
     spends the ability's use.
  F. KEEP IT RUNNIN' at main()'s end-of-Fight boundary: an unengaged Boyz unit
     3" from a Battlewagon is offered, picked, paid for and embarked.

STAGED, each named rather than quietly faked:
  * THE ORKS AS PLAYER 1, Player 2 Necrons; the units are BUILT (the shipped list
    fields War Horde until stage G6). config.BLITZ_BRIGADE_PLAYERS is set for
    both players and config.WAR_HORDE_PLAYERS cleared at the first stage.
  * The clock for each stage, CP topped up; H fires main()'s charge-end hook
    list for a unit placed engaged (a MockAgent charge with a WAGON is not
    something a 6000-frame run reliably produces); C scripts the charge dice
    (random.randint is swapped for exactly that one call - NOT testkit, whose
    import pins every die of the whole run to 1); F puts the Boyz in
    main()'s FightController's engaged_at_start - "eligible to fight this phase".
  * Player 1 prompts this harness does not answer are declined after STALE_FRAMES.

--neutralize loads main.py through an import hook with the main() seams undone
(the charge re-roll's ack call, the embarked view, Impending Krunch's hook and
acknowledgement, Keep It Runnin's offer and reset) and swaps the three rule
answers (the fixed Advance, Targetin' Gizmos, Boss Boomer) for "nothing". The
files on disk are not touched.

Usage:  python verify_ork_blitz_brigade.py [map2] [frames]
        python verify_ork_blitz_brigade.py map2 --neutralize
"""

import importlib.abc
import importlib.util
import math
import os
import runpy
import sys

import pygame

from game import dice as dice_module
from game import (blitz_brigade, blitz_impending_krunch as krunch, blitz_keep_it_runnin as kir, config,
                  enh_boss_boomer, enh_targetin_gizmos, enhancements)
from game.attached_units import attach
from game.blitz_brigade import UnstoppableMomentumChargeRerollController
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import build_squad
from game.factions.orks import BATTLEWAGON, BIG_MEK_MEGA_ARMOUR, BOYZ, GUNWAGON, MEGANOBZ, WARBOSS
from game.turn import PHASES, PHASE_CHARGE, PHASE_FIGHT, PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker
from game.ui.action_panel import ActionPanel
from game.weapons import RANGED

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

HUMAN, AI = "Player 1", "Player 2"
STAGE_AT = 150
STALE_FRAMES = 30
WAIT = 400

NEUTRALIZE_EDITS = (
    ("            if not decision_manager.is_pending:\n"
     "                unstoppable_momentum_controller.maybe_offer_charge_reroll()\n", ""),
    ("    shooting_controller.embarked_squads_provider = lambda: state.embarked_squads\n", ""),
    ("    charge_controller.on_charge_move_finished.append(\n"
     "        impending_krunch_controller.on_charge_move_finished)\n", ""),
    ("        impending_krunch_controller.on_dice_acknowledged()\n", ""),
    ("            keep_it_runnin_controller.offer_at_end_of_fight_phase(\n"
     "                {t.squad for t in state.tokens if t.squad is not None})\n", ""),
    ("        keep_it_runnin_controller.reset_phase()\n", ""),
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
    blitz_brigade.advance_roll_is_fixed = lambda squad: False
    enh_targetin_gizmos.applies = lambda squad, embarked_squads=(): False
    enh_boss_boomer.lent_models = lambda squad, all_squads, flag: []

STAGES = ("h", "c", "b", "d", "e", "f")
state = {"frames": 0, "tracker": None, "wiring": None, "stale": None, "stale_since": 0, "staged": False,
         "declined_other": [], "prompts": [], "labels": [], "rolls": []}
for _key in STAGES:
    state[_key] = None


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

_real_button = ActionPanel._draw_button


def draw_button(self, surface, rect, label, *args, **kwargs):
    state["labels"].append((state["frames"], label))
    return _real_button(self, surface, rect, label, *args, **kwargs)


ActionPanel._draw_button = draw_button


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
    if kir.KEEP_IT_RUNNIN_NAME in prompt or "Intimidating Motivation" in prompt:
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


def _layout(center, count, spacing=1.2, per_row=5):
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


def _place_somewhere(L, squad, want, clearance=1.2):
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
            x += 1.0
        y += 1.0
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


def _scripted_dice(values):
    """Swap random.randint for scripted faces, returning the real one to put
    back. Used around ONE call; testkit is deliberately not imported - it pins
    every die of the whole run to a default of 1."""
    real = dice_module.random.randint
    queue = list(values)
    dice_module.random.randint = lambda low, high: queue.pop(0) if queue else real(low, high)
    return real


def _stage_everything(L):
    if not state["staged"]:
        config.BLITZ_BRIGADE_PLAYERS = (HUMAN, AI)
        config.WAR_HORDE_PLAYERS = ()
        state["staged"] = True


def _wiring(L):
    um = L.get("unstoppable_momentum_controller")
    ik = L.get("impending_krunch_controller")
    kc = L.get("keep_it_runnin_controller")
    provider = getattr(L["shooting_controller"], "embarked_squads_provider", None)
    return {
        "charge_reroll": isinstance(um, UnstoppableMomentumChargeRerollController)
        and um.dice_manager is L["dice_manager"] and um.charge_controller is L["charge_controller"],
        "krunch": isinstance(ik, krunch.ImpendingKrunchController)
        and ik.queue.battle_shock_controller is L["battle_shock_controller"]
        and ik.decision_manager is L["decision_manager"] and ik.all_tokens is L["state"].tokens,
        "keep_it_runnin": isinstance(kc, kir.KeepItRunninController)
        and kc.transport_controller is L["transport_controller"] and kc.fight_controller is L["fight_controller"],
        "embarked_view": provider is not None and provider() is L["state"].embarked_squads,
    }


def _press(L, name):
    panel = L["action_panel"]
    rect = next((r for r, n in panel._stratagem_buttons if n == name), None)
    callback = next((cb for r, cb in panel._buttons if r == rect), None) if rect is not None else None
    if callback is None:
        return False
    callback()
    return True


def _enemy_infantry(L, owner):
    st = L["state"]
    return [s for s in sorted(st.all_squads(), key=lambda s: (-len(_alive(s)), s.name))
            if s.owner != owner and _alive(s) and s not in st.reserves
            and all(m in st.tokens for m in _alive(s))
            and not any(m.profile.vehicle or m.profile.monster for m in _alive(s))]


# ------------------------------------------------------ H. the AI's Impending Krunch
def _stage_h(L):
    _stage_everything(L)
    wagon = build_squad(BATTLEWAGON, AI, name="2 Battlewagon (H)")
    target = None
    for candidate in _enemy_infantry(L, AI):
        if _beside(L, wagon, candidate, lo=wagon.models[0].radius_in + 0.3,
                   hi=wagon.models[0].radius_in + 1.6, clearance=0.05) is not None:
            target = candidate
            break
    if target is None:
        state["h"] = {"error": "no ground beside a Player 1 infantry unit"}
        return
    _set_phase(PHASE_CHARGE, AI)
    L["command_points"].cp[AI] = max(L["command_points"].cp.get(AI, 0), 3)
    cp = L["command_points"].cp[AI]
    rolls_before = len(state["rolls"])
    engaged = [t.name for t in L["impending_krunch_controller"].targets_for(wagon)]
    for listener in list(L["charge_controller"].on_charge_move_finished):
        listener(wagon)
    state["h"] = {"target": target.name, "engaged": engaged, "paid": cp - L["command_points"].cp[AI],
                  "tests": [(r[2], r[1]) for r in state["rolls"][rolls_before:]
                            if krunch.IMPENDING_KRUNCH_NAME in r[1]],
                  "done": True}


# ------------------------------------------------------ C. the AI's charge re-roll
def _stage_c(L):
    wagon = build_squad(BATTLEWAGON, AI, name="2 Battlewagon (C)")
    target = None
    for candidate in _enemy_infantry(L, AI):
        if _place_somewhere(L, wagon, lambda spots, t=candidate: -abs(_gap_to(L, AI, spots, squad=t) - 9.0)
                            if 7.0 < _gap_to(L, AI, spots, squad=t) < 11.0
                            and _gap_to(L, AI, spots) > 6.0 else None) is not None:
            target = candidate
            break
    if target is None:
        state["c"] = {"error": "no ground 9\" from a Player 1 infantry unit"}
        return
    _set_phase(PHASE_CHARGE, AI)
    cc = L["charge_controller"]
    real = _scripted_dice([1, 2])
    try:
        cc.declare_charge(wagon)
    finally:
        dice_module.random.randint = real
    dm = L["dice_manager"]
    first = list(dm.pending_values or ())
    reaches = bool(cc.targets_reachable_with(sum(first))) if first else None
    try:
        L["_acknowledge_pending_roll"]()
    except Exception as exc:
        state["c"] = {"error": "_acknowledge_pending_roll raised %r" % exc}
        return
    lines = [str(e) for e in L["game_log"].entries if blitz_brigade.UNSTOPPABLE_MOMENTUM in e]
    # A re-roll that REACHED leaves this staged charge waiting for its move -
    # and the panel on the charge screen for every later stage. The measurement
    # is done; the staged charge is declined, as a player may (rule 11.02).
    left_open = cc.active_squad is wagon
    if left_open:
        cc.decline_charge_move()
    state["c"] = {"first": first, "first_reaches": reaches, "log": lines, "left_open": left_open,
                  "closed": cc.active_squad is not wagon, "done": True}


# ------------------------------------------------------ B. the Advance
def _stage_b(L):
    wagon = build_squad(BATTLEWAGON, HUMAN, name="1 Battlewagon (B)")
    if _clear_of_enemy(L, HUMAN, wagon) is None:
        state["b"] = {"error": "no ground for Player 1's Battlewagon"}
        return
    _set_phase(PHASE_MOVEMENT)
    mc = L["movement_controller"]
    mc.moved_squad_ids.discard(wagon)
    mc.select(wagon.models[0])
    mc.start_move()
    before = mc.remaining_range.get(wagon.models[0].id)
    rolls_before = len(state["rolls"])
    mc.start_run()
    after = mc.remaining_range.get(wagon.models[0].id)
    dice = [r[1] for r in state["rolls"][rolls_before:]]
    mc.cancel_move()
    mc.select(None)
    state["b"] = {"added": round((after or 0) - (before or 0), 3), "dice": dice, "done": True}


# ------------------------------------------------------ D. Targetin' Gizmos
def _stage_d(L):
    gun_wagon = build_squad(GUNWAGON, HUMAN, name="1 Gunwagon (D)")
    enhancements.grant(gun_wagon, enh_targetin_gizmos.TARGETIN_GIZMOS)
    if _clear_of_enemy(L, HUMAN, gun_wagon) is None:
        state["d"] = {"error": "no ground for the Gunwagon"}
        return
    mob = attach(build_squad(BIG_MEK_MEGA_ARMOUR, HUMAN, name="1 Big Mek (D)"),
                 build_squad(MEGANOBZ, HUMAN, name="1 Meganobz (D)"))
    if _beside(L, mob, gun_wagon, lo=0.5, hi=2.5) is None:
        state["d"] = {"error": "no ground beside the Gunwagon"}
        return
    L["transport_controller"].embark(mob, gun_wagon.models[0], require_move=False)
    target = next(iter(_enemy_infantry(L, HUMAN)), None)
    sc = L["shooting_controller"]
    gun = next(w for w in gun_wagon.models[0].weapons if w.weapon_type == RANGED)
    _set_phase(PHASE_SHOOTING)
    saved, real = sc.active_squad, sc._has_benefit_of_cover
    try:
        sc.active_squad = gun_wagon
        sc._has_benefit_of_cover = lambda shooter_model, target_squad: True
        ignores = bool(sc._adjusted_weapon([(gun_wagon.models[0], gun)], target).ignores_cover)
        cover = [m.source for m in sc._hit_modifiers({"pairs": [(gun_wagon.models[0], gun)], "target_squad": target})
                 if m.source == "Benefit of Cover"]
    finally:
        sc.active_squad, sc._has_benefit_of_cover = saved, real
    state["d"] = {"embarked": mob.embarked_in is gun_wagon.models[0], "ignores": ignores, "cover": cover,
                  "target": getattr(target, "name", None), "done": True}


# ------------------------------------------------------ E. Boss Boomer on the panel
def _stage_e(L):
    wagon = build_squad(BATTLEWAGON, HUMAN, name="1 Battlewagon (E)")
    enhancements.grant(wagon, enh_boss_boomer.BOSS_BOOMER)
    if _clear_of_enemy(L, HUMAN, wagon) is None:
        state["e"] = {"error": "no ground for the Boss Boomer Battlewagon"}
        return
    boss = build_squad(WARBOSS, HUMAN, name="1 Warboss (E)")
    if _beside(L, boss, wagon, lo=0.5, hi=2.5) is None:
        state["e"] = {"error": "no ground beside the Battlewagon"}
        return
    L["transport_controller"].embark(boss, wagon.models[0], require_move=False)
    L["movement_controller"].moved_squad_ids.discard(wagon)
    _set_phase(PHASE_MOVEMENT)
    L["movement_controller"].select(_alive(wagon)[0])
    state["e"] = {"_wagon": wagon, "embarked": boss.embarked_in is wagon.models[0], "quiet_frames": 0,
                  "blocked": {}, "labels_before": len(state["labels"])}


def _watch_e(L):
    e = state["e"]
    wagon = e["_wagon"]
    tracker = state["tracker"]
    if tracker.phase != PHASE_MOVEMENT or tracker.turn_owner != HUMAN:
        _set_phase(PHASE_MOVEMENT)
    if L["movement_controller"].selected_squad is not wagon:
        L["movement_controller"].select(_alive(wagon)[0])
    drawn = [lab for _f, lab in state["labels"][e["labels_before"]:] if lab.startswith("Intimidating Motivation")]
    if not _quiet(L):
        # A roll or a prompt owns the panel this frame (the dice of an earlier
        # stage's queue, a stale prompt) - not a frame the button could be in.
        key = "dice" if L["dice_manager"].is_pending else ("prompt" if L["decision_manager"].is_pending else "other")
        e["blocked"][key] = e["blocked"].get(key, 0) + 1
        if sum(e["blocked"].values()) < 4 * WAIT:
            return
    else:
        e["quiet_frames"] += 1
    if not drawn and e["quiet_frames"] < WAIT and sum(e["blocked"].values()) < 4 * WAIT:
        return
    e["why_not"] = L["intimidating_motivation_controller"].why_not(wagon)
    e["drawn"] = drawn[:1]
    e["done"] = True
    if not drawn:
        return
    ctrl = L["intimidating_motivation_controller"]
    e["pressed"] = _press(L, "Intimidating Motivation")
    decisions = L["decision_manager"]
    if decisions.is_pending and "Intimidating Motivation" in (decisions.prompt or ""):
        decisions.choose(0)
    e["spent"] = ctrl.is_spent(HUMAN)


# ------------------------------------------------------ F. Keep It Runnin'
def _boyz_spots(L, boyz, least=10.0, limit=12):
    """Legal cluster centres for the Boyz clear of the enemy, best first."""
    setup = L["setup_controller"]
    found = []
    y = 3.0
    while y < setup.board_height_in - 3.0:
        x = 3.0
        while x < setup.board_width_in - 3.0:
            spots = _layout((x, y), len(boyz.models))
            gap = _gap_to(L, HUMAN, spots)
            if gap > least and _fits(L, boyz, spots):
                found.append((-abs(gap - 16.0), spots))
            x += 2.0
        y += 2.0
    return [spots for _score, spots in sorted(found, key=lambda f: f[0], reverse=True)[:limit]]


def _wagon_beside(L, boyz, wagon):
    """A Battlewagon spot the Boyz are wholly within 6" of - can_embark() itself
    decides, so the stage cannot disagree with the rule it stages."""
    tc = L["transport_controller"]
    model = wagon.models[0]
    setup = L["setup_controller"]
    cands = sorted(((x * 0.5, y * 0.5) for x in range(6, 2 * int(setup.board_width_in) - 6)
                    for y in range(6, 2 * int(setup.board_height_in) - 6)
                    if 1.0 < _gap_to(L, HUMAN, [(x * 0.5, y * 0.5)], squad=boyz) - model.radius_in < 2.5),
                   key=lambda pt: _gap_to(L, HUMAN, [pt], squad=boyz))
    for x, y in cands:
        if not _fits(L, wagon, [(x, y)], clearance=0.3):
            continue
        model.x_in, model.y_in = x, y
        L["state"].add_token(model)
        if tc.can_embark(boyz, model, require_move=False, range_in=kir.KEEP_IT_RUNNIN_RANGE_IN):
            return True
        L["state"].tokens.remove(model)
    return False


def _stage_f(L):
    boyz = build_squad(BOYZ, HUMAN, name="1 Boyz (F)")
    wagon = build_squad(BATTLEWAGON, HUMAN, name="1 Battlewagon (F)")
    placed = False
    for spots in _boyz_spots(L, boyz):
        for model, (x, y) in zip(boyz.models, spots):
            model.x_in, model.y_in = x, y
            L["state"].add_token(model)
        if _wagon_beside(L, boyz, wagon):
            placed = True
            break
        for model in boyz.models:
            L["state"].tokens.remove(model)
    if not placed:
        state["f"] = {"error": "no ground for Boyz and a Battlewagon they are wholly within 6\" of"}
        return
    L["fight_controller"].engaged_at_start.add(boyz)
    L["command_points"].cp[HUMAN] = max(L["command_points"].cp[HUMAN], 3)
    cp = L["command_points"].cp[HUMAN]
    _set_phase(PHASE_FIGHT, HUMAN)
    prompts_before = len(state["prompts"])
    try:
        L["advance_turn_phase"]()
    except Exception as exc:
        state["f"] = {"error": "advance_turn_phase raised %r" % exc}
        return
    asked = [p for p in state["prompts"][prompts_before:] if kir.KEEP_IT_RUNNIN_NAME in p["prompt"]]
    # The price is measured from HERE: Fight is the last phase, so the boundary
    # itself already opened the next Command phase and paid its core CP.
    cp = L["command_points"].cp[HUMAN]
    decisions = L["decision_manager"]
    picked = None
    transport_asked = None
    for _ in range(6):
        if not decisions.is_pending:
            break
        prompt = decisions.prompt or ""
        if kir.KEEP_IT_RUNNIN_NAME in prompt and "which TRANSPORT" in prompt:
            # Step two - more than one transport in range: this stage's own.
            transport_asked = [o["label"] for o in decisions.options]
            index = next((i for i, o in enumerate(decisions.options) if o["label"] == wagon.name), None)
            if index is None:
                break
            decisions.choose(index)
            continue
        if kir.KEEP_IT_RUNNIN_NAME in prompt:
            index = next((i for i, o in enumerate(decisions.options) if boyz.name in o["label"]), None)
            if index is None:
                break
            picked = decisions.options[index]["label"]
            decisions.choose(index)
            continue
        decisions.choose(len(decisions.options) - 1)
    state["f"] = {"asked": asked, "picked": picked, "transport_asked": transport_asked,
                  "paid": cp - L["command_points"].cp[HUMAN],
                  "embarked": boyz.embarked_in is wagon.models[0], "done": True}


WATCH = {"h": None, "c": None, "b": None, "d": None, "e": _watch_e, "f": None}
STAGE = {"h": _stage_h, "c": _stage_c, "b": _stage_b, "d": _stage_d, "e": _stage_e, "f": _stage_f}


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
                    if (key != "h" or state["frames"] >= STAGE_AT) and _quiet(L):
                        STAGE[key](L)
                    break
                if record.get("error"):
                    raise SystemExit(0)
                if not record.get("done"):
                    WATCH[key](L)
                    if not state[key].get("done"):
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
h, cc, b, d, e, f = (state[k] or {} for k in ("h", "c", "b", "d", "e", "f"))


def _err(record):
    return (" ERROR " + record["error"]) if record.get("error") else ""


print()
print("--- Ork Blitz Brigade, live" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
print("  frames                                 : %d" % state["frames"])
print("  A. charge re-roll %s, Krunch %s, Keep It Runnin' %s, embarked view %s" % (
    w.get("charge_reroll"), w.get("krunch"), w.get("keep_it_runnin"), w.get("embarked_view")))
print("  H. Krunch beside %s, engaged %s: paid %s, tests %s%s" % (
    h.get("target"), h.get("engaged"), h.get("paid"), h.get("tests"), _err(h)))
print("  C. first roll %s (reaches %s); Unstoppable Momentum log %s; staged charge left open %s, closed %s%s" % (
    cc.get("first"), cc.get("first_reaches"), [l[:70] for l in cc.get("log") or []], cc.get("left_open"),
    cc.get("closed"), _err(cc)))
print("  B. Advance added %s, dice %s%s" % (b.get("added"), b.get("dice"), _err(b)))
print("  D. embarked %s; vs %s: ignores cover %s, cover modifiers %s%s" % (
    d.get("embarked"), d.get("target"), d.get("ignores"), d.get("cover"), _err(d)))
print("  E. embarked %s, drawn %s (why not: %s; quiet frames %s, blocked %s), pressed %s, spent %s%s" % (
    e.get("embarked"), e.get("drawn"), e.get("why_not"), e.get("quiet_frames"), e.get("blocked"),
    e.get("pressed"), e.get("spent"), _err(e)))
print("  F. asked %s, picked %s, then which transport %s, paid %s, embarked %s%s" % (
    [p["labels"][:2] for p in f.get("asked") or []], f.get("picked"), f.get("transport_asked"), f.get("paid"),
    f.get("embarked"), _err(f)))
print("  stale Player 1 prompts declined        : %s" % (state["declined_other"] or "none"))

if not state["wiring"] or any(r.get("error") for r in (h, cc, b, d, e, f)) or not f.get("done"):
    print("  INCONCLUSIVE - the run never got through the staging")
    raise SystemExit(2)

if not NEUTRALIZE:
    checks = (
        ("all three controllers hold main()'s collaborators, and the shooting view IS main()'s embarked list",
         w.get("charge_reroll") and w.get("krunch") and w.get("keep_it_runnin") and w.get("embarked_view")),
        ("the AI buys Impending Krunch at main()'s charge-end hook (1CP)", h.get("paid") == 1),
        ("...and a Battle-shock test at -1 is thrown for an engaged Player 1 unit (one at a time)",
         bool(h.get("tests")) and h["tests"][0][0] in (h.get("engaged") or [])
         and "-1" in h["tests"][0][1]),
        ("main()'s acknowledgement door re-rolls the AI WAGON's failed charge (Unstoppable Momentum)",
         cc.get("first_reaches") is False and any("re-rolled in full" in l for l in cc.get("log") or [])),
        ("the Battlewagon's Advance on main()'s MovementController adds 6\" and throws no die",
         b.get("added") == 6.0 and b.get("dice") == []),
        ("Targetin' Gizmos: the Gunwagon carrying a Big Mek ignores cover on main()'s ShootingController",
         d.get("embarked") is True and d.get("ignores") is True and d.get("cover") == []),
        ("Boss Boomer: Intimidating Motivation is DRAWN for the Battlewagon carrying a Warboss, and used",
         e.get("embarked") is True and bool(e.get("drawn")) and e.get("pressed") is True and e.get("spent") is True),
        ("Keep It Runnin': main()'s end-of-Fight boundary offers the Boyz; picked, 1CP, embarked",
         bool(f.get("asked")) and f.get("picked") is not None and f.get("paid") == 1 and f.get("embarked") is True),
    )
else:
    checks = (
        ("the charge re-roll is never asked at main()'s door", not any("re-rolled in full" in l for l in cc.get("log") or [])),
        ("the ShootingController has no embarked view", not w.get("embarked_view")),
        ("Impending Krunch never hears the charge end", not h.get("paid") and not h.get("tests")),
        ("the Battlewagon ROLLS its Advance", bool(b.get("dice"))),
        ("Targetin' Gizmos does nothing: cover stays", d.get("ignores") is False and d.get("cover") == ["Benefit of Cover"]),
        ("Boss Boomer lends nothing: never drawn", not e.get("drawn")),
        ("Keep It Runnin' is never offered", not f.get("asked") and f.get("embarked") is False),
    )
failed = 0
for label, ok in checks:
    print("  %s  %s" % ("PASS" if ok else "FAIL", label))
    failed += 0 if ok else 1
raise SystemExit(1 if failed else 0)
