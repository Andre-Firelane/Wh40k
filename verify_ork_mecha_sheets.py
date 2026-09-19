"""Runtime proof through the REAL main() loop that the Mecha Orks sheets (stage G1)
are wired: the Weirdboy's Da Jump and Warpath, the Bigboss's Sumfin' to Prove and
the Gunwagon's Mobile Arsenal.

test_ork_mecha_sheets.py drives each ability through real controllers built by
the test and pins main.py by AST. What it cannot show is that MAIN'S objects,
built by MAIN'S constructors in MAIN'S order, are connected when the game runs -
that main()'s own panel draws Da Jump, main()'s dice acknowledgement resolves the
psychic rolls, main()'s phase boundary ends the grant, and the AI's real
take_one_action() jumps and lands a unit. So this runs selfplay.py's real main()
loop with the ORKS AS PLAYER 1 and asks main()'s live objects:

  A. THE WIRING. The live FightController holds a WeirdboyWarpathController on
     main()'s psychic roll with the AI's verdict; the live panel registry holds a
     DaJumpController on the same roll, main()'s GameState, MovementController
     and clock.
  G. THE AI'S DA JUMP through main()'s own auto-play (take_one_action ->
     _handle_movement -> _handle_da_jump): a Player 2 Boyz mob with a Weirdboy,
     far from every Player 1 model in Player 2's Movement phase, jumps (psychic
     roll acknowledged by main()), and the same phase's Ingress step lands it
     again with Deep Strike.
  B. DA JUMP DRAWN on main()'s ActionPanel for a Player 1 mob in Player 1's
     Movement phase, pressed: psychic roll, Strategic Reserves, Deep Strike, and
     the live IngressController takes a mid-board landing for it.
  C. THE WEIRDBOY'S WARPATH through the live FightController: asked at "selected
     to fight", the D6 resolved by main(), [PSYCHIC] in the live chain, and on the
     REAL wound roll the 1s come back as their own "re-roll of 1s" step.
  D. SUMFIN' TO PROVE read off the live FightController (and NOT the live
     ShootingController) for a Boyz mob the Bigboss supports.
  E. MOBILE ARSENAL on the live ShootingController's real Hit roll: a Gunwagon's
     Kannon 1s come back as their own "re-roll of 1s" step.
  F. THE PHASE BOUNDARY: main()'s advance_turn_phase() ends the Warpath grant.

STAGED, each named rather than quietly faked:
  * THE ORKS AS PLAYER 1 (config ships aeldari against necrons), Player 2 Necrons.
  * The units are BUILT (the shipped list does not field these sheets yet - stage
    G6 replaces it): G's Player 2 Boyz + Weirdboy, B's and C's Player 1 Boyz +
    Weirdboy, D's Boyz + Bigboss (never placed), E's Gunwagon.
  * The clock: G sets battle round 2 (rule 20.03 - no arrival before it, and the
    AI only jumps a unit that can come back the same phase) and Player 2's
    Movement phase; B-F set Player 1's phases. B re-stamps phase and selection
    each frame until main() has drawn the button (selfplay clicks Next Phase in
    Player 1's turn), C/E start the Fight step / the activation by hand with
    pile-in bypassed, as verify_ork_kill_rig.py does.
  * F runs in the same frame C finishes; the grant is staged by hand only if it
    is already gone (printed, and then the check fails).
  * The dice: psychic rolls show 4; C forces the Copper Staff's hits to 6 and its
    wounds (and their re-roll) to 1, E forces the Kannon's hits (and their
    re-roll) to 1 - so both attacks end without a save to allocate.
  * Player 1 prompts this harness does not answer are declined after STALE_FRAMES.

--neutralize loads main.py through an import hook with the four main() seams
undone (the Warpath hand-over, the per-phase reset, Da Jump on the registry, Da
Jump for the AI) and swaps game/sumfin_to_prove.py's and game/mobile_arsenal.py's
answers for the pre-G1 "nothing". The files on disk are not touched.

Usage:  python verify_ork_mecha_sheets.py [map2] [frames]
        python verify_ork_mecha_sheets.py map2 --neutralize
"""

import importlib.abc
import importlib.util
import math
import os
import runpy
import sys

import pygame

from game import config, da_jump, mobile_arsenal, sumfin_to_prove, weirdboy_warpath
from game.attached_units import attach
from game.da_jump import DaJumpController
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import build_squad
from game.factions.orks import BIGBOSS, BOYZ, GUNWAGON, WEIRDBOY
from game.game_log import GameLog
from game.objectives import is_within_range_of_objective
from game.psychic_roll import PsychicRollController
from game.turn import PHASES, PHASE_FIGHT, PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker
from game.ui.action_panel import ActionPanel
from game.weirdboy_warpath import WeirdboyWarpathController
from game.weapons import MELEE, RANGED

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

HUMAN, AI = "Player 1", "Player 2"
STAGE_AT = 150
STALE_FRAMES = 30
WAIT = 400
AI_WAIT = 1200
PSYCHIC_FACE = 4

NEUTRALIZE_EDITS = (
    ("        weirdboy_warpath=WeirdboyWarpathController(\n"
     "            psychic_roll_controller, decision_manager=decision_manager, game_log=game_log,\n"
     "            auto_players=ai_players,\n"
     "            verdict=lambda squad: warpath_verdict(state, squad)),\n",
     "        weirdboy_warpath=None,\n"),
    ("        weirdboy_warpath.reset_phase({t.squad for t in state.tokens if t.squad is not None})\n",
     "        pass\n"),
    ("    da_jump_controller = proactive_stratagems.add(DaJumpController(\n",
     "    da_jump_controller = (lambda controller: controller)(DaJumpController(\n"),
    ("            da_jump_controller=da_jump_controller,\n", ""),
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
    # The two module seams: before G1 neither ability existed, so each answers
    # "nothing" - fight.py and shooting.py read them through the module.
    sumfin_to_prove.hit_modifiers = lambda squad: []
    mobile_arsenal.applies = lambda squad, reactive=False: False

# F follows C in the SAME frame (see flip()): selfplay clicks Next Phase in Player
# 1's turn, so one idle frame between them would let a real boundary clear C's
# grant first and leave F nothing of C's to measure.
STAGES = ("g", "b", "c", "f", "d", "e")
state = {"frames": 0, "tracker": None, "wiring": None, "stale": None, "stale_since": 0,
         "declined_other": [], "prompts": [], "rolls": [], "labels": [], "force": None, "log": []}
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


def roll(self, *args, **kwargs):
    out = _real_roll(self, *args, **kwargs)
    label = kwargs.get("label", "") or ""
    if self.pending_values:
        face = None
        if label.startswith("Psychic roll: "):
            face = PSYCHIC_FACE
        force = state["force"]
        if force is not None and force[0] in label:
            face = force[1] if ("Hit Roll" in label and "re-roll" not in label) else force[2]
            if "Wound Roll" in label:
                face = force[2]
        if face is not None:
            self.pending_values[:] = [face] * len(self.pending_values)
            self.last_values = list(self.pending_values)
    state["rolls"].append((state["frames"], label))
    return out


DiceManager.roll = roll

_real_log_add = GameLog.add


def log_add(self, message, *args, **kwargs):
    if "[da jump]" in str(message):
        state["log"].append(str(message))
    return _real_log_add(self, message, *args, **kwargs)


GameLog.add = log_add

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


def _answer(decisions, needle):
    if not decisions.is_pending:
        return None
    for i, option in enumerate(decisions.options):
        if option["label"].startswith(needle):
            decisions.choose(i)
            return option["label"]
    return None


def _mob(owner, tag):
    """A Boyz mob with a Weirdboy attached, built and not yet on the board."""
    return attach(build_squad(WEIRDBOY, owner, name="%s Weirdboy (%s)" % (owner[-1], tag)),
                  build_squad(BOYZ, owner, name="%s Boyz (%s)" % (owner[-1], tag)))


def _layout(center, count, spacing=1.35, per_row=4):
    rows = (count + per_row - 1) // per_row
    cols = min(count, per_row)
    out = []
    for i in range(count):
        r, col = divmod(i, per_row)
        out.append((center[0] + (col - (cols - 1) / 2.0) * spacing,
                    center[1] + (r - (rows - 1) / 2.0) * spacing))
    return out


def _fits(L, squad, spots):
    setup = L["setup_controller"]
    tokens = [t for t in L["state"].tokens if not t.is_dead() and t.squad is not squad]
    for model, (x, y) in zip(squad.models, spots):
        if not setup.position_valid(model, x, y, squad=squad):
            return False
        if any(math.hypot(x - t.x_in, y - t.y_in) < model.radius_in + t.radius_in + 1.2 for t in tokens):
            return False
    return True


def _place(L, squad, spots):
    for model, (x, y) in zip(squad.models, spots):
        model.x_in, model.y_in = x, y
        L["state"].add_token(model)


def _gap_to(L, owner, spots):
    enemies = [t for t in L["state"].tokens if not t.is_dead() and t.squad is not None and t.squad.owner != owner]
    return min((math.hypot(x - t.x_in, y - t.y_in) - t.radius_in for x, y in spots for t in enemies), default=99.0)


def _find_spot(L, squad, want, step=1.0):
    """The best-scoring legal cluster centre for `squad`, by want(spots) -> score or None."""
    setup = L["setup_controller"]
    best = None
    y = 3.0
    while y < setup.board_height_in - 3.0:
        x = 3.0
        while x < setup.board_width_in - 3.0:
            spots = _layout((x, y), len(squad.models))
            score = want(spots)
            if score is not None and (best is None or score > best[0]) and _fits(L, squad, spots):
                best = (score, spots)
            x += step
        y += step
    return best


def _wiring(L):
    fc = L["fight_controller"]
    ww = getattr(fc, "weirdboy_warpath", None)
    reg = L["proactive_stratagems"]
    dj = next((c for c in reg.controllers if isinstance(c, DaJumpController)), None)
    return {
        "warpath": isinstance(ww, WeirdboyWarpathController),
        "warpath_roll": isinstance(getattr(ww, "psychic_roll", None), PsychicRollController)
        and ww.psychic_roll is L.get("psychic_roll_controller"),
        "warpath_ai": callable(getattr(ww, "verdict", None)),
        "da_jump": dj is not None,
        "da_jump_live": dj is not None and dj.psychic_roll is L.get("psychic_roll_controller")
        and dj.game_state is L["state"] and dj.movement_controller is L["movement_controller"]
        and dj.turn_tracker is L["turn_tracker"],
    }


# ------------------------------------------------------------ G. the AI jumps
def _stage_g(L):
    st = L["state"]
    mob = _mob(AI, "G")
    objectives = list(getattr(st, "objectives", ()) or [])

    def want(spots):
        gap = _gap_to(L, AI, spots)
        if gap < 26.0:
            return None
        for model, (x, y) in zip(mob.models, spots):
            model.x_in, model.y_in = x, y
        if objectives and is_within_range_of_objective(mob, objectives):
            return None
        return -gap   # the closest spot still beyond reach: the landing then has somewhere to go
    best = _find_spot(L, mob, want)
    if best is None:
        state["g"] = {"error": "no clear Player 2 ground 26\" from every Player 1 model and off the objectives"}
        return
    _place(L, mob, best[1])
    tracker = state["tracker"]
    tracker.battle_round = max(2, tracker.battle_round)
    L["movement_controller"].moved_squad_ids.discard(mob)
    _set_phase(PHASE_MOVEMENT, AI)
    state["g"] = {"_mob": mob, "unit": mob.name, "frame": state["frames"], "gap": -best[0],
                  "round": tracker.battle_round, "on_objective": is_within_range_of_objective(mob, objectives),
                  "rolls_before": len(state["rolls"])}


def _watch_g(L):
    g = state["g"]
    mob = g["_mob"]
    st = L["state"]
    in_reserves = mob in st.reserves
    if in_reserves and g.get("jumped_at") is None:
        g["jumped_at"] = state["frames"]
        g["deep_strike_flag"] = da_jump.grants_deep_strike(mob)
    back = g.get("jumped_at") is not None and not in_reserves and any(m in st.tokens for m in _alive(mob))
    if back or state["frames"] - g["frame"] >= AI_WAIT:
        g["done"] = True
        g["back"] = back
        g["psychic"] = [lab for _f, lab in state["rolls"][g["rolls_before"]:] if lab.startswith("Psychic roll: Da Jump")]
        ingress = L["ingress_controller"]
        g["ingressed"] = mob in getattr(ingress, "ingressed_this_turn", set())
        g["deep_striking"] = ingress.deep_striking(mob)
        setup = L["setup_controller"]
        if back:
            g["gap_after"] = _gap_to(L, AI, [(m.x_in, m.y_in) for m in _alive(mob)])
            g["edge_margin"] = min(min(m.x_in, m.y_in, setup.board_width_in - m.x_in, setup.board_height_in - m.y_in)
                                   for m in _alive(mob))
        g["log_line"] = any("[da jump]" in line and mob.name in line for line in state["log"])


# ------------------------------------------------------------ B. the button
def _stage_b(L):
    mob = _mob(HUMAN, "B")
    best = _find_spot(L, mob, lambda spots: _gap_to(L, HUMAN, spots))
    if best is None:
        state["b"] = {"error": "no clear Player 1 ground for the Da Jump mob"}
        return
    _place(L, mob, best[1])
    state["tracker"].battle_round = max(2, state["tracker"].battle_round)
    L["movement_controller"].moved_squad_ids.discard(mob)
    _set_phase(PHASE_MOVEMENT)
    L["movement_controller"].select(_alive(mob)[0])
    state["b"] = {"_mob": mob, "unit": mob.name, "frame": state["frames"], "labels_before": len(state["labels"])}


def _watch_b(L):
    b = state["b"]
    mob = b["_mob"]
    tracker = state["tracker"]
    if b.get("pressed") is None:
        if tracker.phase != PHASE_MOVEMENT or tracker.turn_owner != HUMAN:
            _set_phase(PHASE_MOVEMENT)
        if L["movement_controller"].selected_squad is not mob:
            L["movement_controller"].select(_alive(mob)[0])
        drawn = [lab for _f, lab in state["labels"][b["labels_before"]:] if lab.startswith(da_jump.DA_JUMP_NAME)]
        if not drawn and state["frames"] - b["frame"] < WAIT:
            return
        b["drawn"] = drawn[:1]
        b["pressed"] = False
        if drawn:
            panel = L["action_panel"]
            rect = next((r for r, n in panel._stratagem_buttons if n == da_jump.DA_JUMP_NAME), None)
            callback = next((cb for r, cb in panel._buttons if r == rect), None) if rect is not None else None
            if callback is not None:
                callback()
                b["pressed"] = True
                b["press_frame"] = state["frames"]
                b["pending"] = L["dice_manager"].is_pending
                b["pending_label"] = L["dice_manager"].label
                b["in_reserves"] = mob in L["state"].reserves
                b["off_board"] = not any(m in L["state"].tokens for m in mob.models)
                b["deep_strike_flag"] = da_jump.grants_deep_strike(mob)
                b["deselected"] = L["movement_controller"].selected_squad is not mob
        if not b["pressed"]:
            b["done"] = True
        return
    ctrl = L["psychic_roll_controller"]
    resolved = not L["dice_manager"].is_pending and not ctrl.is_busy
    if not (resolved or state["frames"] - b["press_frame"] >= WAIT):
        return
    b["resolved"] = resolved
    b["shocked"] = bool(mob.battle_shocked)
    ingress = L["ingress_controller"]
    b["can_ingress"] = ingress.can_ingress(mob)
    b["deep_striking"] = ingress.deep_striking(mob)
    setup = L["setup_controller"]
    enemies = [t for t in L["state"].tokens if not t.is_dead() and t.squad is not None and t.squad.owner != HUMAN]
    landing = None
    for gy in range(8, int(setup.board_height_in) - 7):
        for gx in range(8, int(setup.board_width_in) - 7):
            if min((math.hypot(gx - t.x_in, gy - t.y_in) - t.radius_in for t in enemies), default=99.0) < 9.5:
                continue
            if ingress.position_valid(mob, mob.models[0], float(gx), float(gy)):
                landing = (gx, gy)
                break
        if landing:
            break
    b["mid_board_landing"] = landing
    b["done"] = True


# ------------------------------------------------------------ C. Warpath
def _stage_c(L):
    st = L["state"]
    target = max((s for s in st.all_squads() if s.owner == AI and len(_alive(s)) >= 5
                  and getattr(s, "embarked_in", None) is None and s not in st.reserves
                  and all(m in st.tokens for m in _alive(s))),
                 key=lambda s: len(_alive(s)), default=None)
    if target is None:
        state["c"] = {"error": "no Player 2 unit of 5+ models on the board"}
        return
    mob = _mob(HUMAN, "C")
    alive = _alive(target)
    for i, model in enumerate(mob.models):
        partner = alive[i % len(alive)]
        model.x_in = partner.x_in
        model.y_in = partner.y_in - partner.radius_in - model.radius_in - 0.5
        st.add_token(model)
    _set_phase(PHASE_FIGHT)
    fc = L["fight_controller"]
    fc.reset_fight_phase()
    saved, fc.pile_in_controller = fc.pile_in_controller, None
    try:
        fc.begin_fight_step()
    finally:
        fc.pile_in_controller = saved
    fc.whose_turn = HUMAN
    prompts_before = len(state["prompts"])
    selectable = fc.can_select_to_fight(mob)
    fc.select_to_fight(mob)
    asked = [p for p in state["prompts"][prompts_before:] if "Warpath" in p["prompt"]]
    chosen = _answer(L["decision_manager"], "Make the psychic roll") if asked else None
    state["c"] = {"_mob": mob, "_target": target, "unit": mob.name, "target": target.name,
                  "frame": state["frames"], "selectable": selectable, "asked": asked, "chosen": chosen,
                  "step": "roll"}


def _watch_c(L):
    c = state["c"]
    mob, target = c["_mob"], c["_target"]
    fc = L["fight_controller"]
    dm = L["dice_manager"]
    if c["step"] == "roll":
        ctrl = L["psychic_roll_controller"]
        resolved = not dm.is_pending and not ctrl.is_busy
        if not (resolved or state["frames"] - c["frame"] >= WAIT):
            return
        c["resolved"] = resolved
        c["active"] = weirdboy_warpath.is_active(mob)
        boy = next(m for m in _alive(mob) if not m.profile.character)
        choppa = next(w for w in boy.weapons if w.weapon_type == MELEE)
        adjusted = fc._adjusted_weapon([(boy, choppa)], target)
        c["chain_psychic"] = bool(getattr(adjusted, "psychic", False))
        # The real wound roll: the Copper Staff's hits forced to 6, its wounds
        # and their re-roll to 1, so the attack ends with nothing to save.
        if fc.target_squad is None:
            fc.choose_target_squad(target)
        key = next((k for k, label, *_r in fc.weapon_eligibility() if "Copper Staff" in str(label)), None)
        c["weapon_key"] = key is not None
        if key is None or dm.is_pending:
            c["step"] = "done"
            c["done"] = True
            return
        state["force"] = ("Copper Staff", 6, 1)
        c["rolls_before"] = len(state["rolls"])
        c["attack_frame"] = state["frames"]
        fc.choose_weapon(key)
        c["step"] = "attack"
        return
    if c["step"] == "attack":
        labels = [lab for _f, lab in state["rolls"][c["rolls_before"]:]]
        settled = fc.current_group is None and not dm.is_pending
        if not (settled or state["frames"] - c["attack_frame"] >= WAIT):
            return
        state["force"] = None
        c["attack_labels"] = labels
        c["reroll_labels"] = [lab for lab in labels if "Wound Roll re-roll of 1s" in lab]
        try:
            fc.cancel()
        except Exception:
            pass
        c["before_boundary"] = weirdboy_warpath.is_active(mob)
        c["step"] = "done"
        c["done"] = True


# ------------------------------------------------------------ D. Sumfin' to Prove
def _stage_d(L):
    c = state["c"] or {}
    target = c.get("_target")
    if target is None:
        state["d"] = {"error": "no target from C"}
        return
    mob = attach(build_squad(BIGBOSS, HUMAN, name="1 Bigboss (D)"), build_squad(BOYZ, HUMAN, name="1 Boyz (D)"))
    boy = next(m for m in mob.models if not m.profile.character)
    fc, sc = L["fight_controller"], L["shooting_controller"]
    saved_f, saved_s = fc.fighting_squad, sc.active_squad
    try:
        fc.fighting_squad = mob
        melee = [(m.amount, m.source) for m in fc._hit_modifiers(boy, target)
                 if m.source == sumfin_to_prove.SUMFIN_TO_PROVE_NAME]
        sc.active_squad = mob
        slugga = next(w for w in boy.weapons if w.weapon_type == RANGED)
        ranged = [(m.amount, m.source) for m in sc._hit_modifiers({"pairs": [(boy, slugga)], "target_squad": target})
                  if m.source == sumfin_to_prove.SUMFIN_TO_PROVE_NAME]
    finally:
        fc.fighting_squad, sc.active_squad = saved_f, saved_s
    state["d"] = {"melee": melee, "ranged": ranged, "done": True}


# ------------------------------------------------------------ E. Mobile Arsenal
def _stage_e(L):
    st = L["state"]
    _set_phase(PHASE_SHOOTING)
    sc = L["shooting_controller"]
    gw = build_squad(GUNWAGON, HUMAN, name="1 Gunwagon (E)")
    token = gw.models[0]
    targets = [s for s in st.all_squads() if s.owner == AI and _alive(s) and s not in st.reserves
               and all(m in st.tokens for m in _alive(s)) and not s.is_engaged(st.tokens)]
    found = None
    st.add_token(token)
    token.x_in, token.y_in = -50.0, -50.0
    for target in sorted(targets, key=lambda s: -len(_alive(s))):
        anchor = _alive(target)[0]
        for radius in (14.0, 18.0, 22.0, 26.0):
            for step in range(18):
                angle = step * math.pi / 9.0
                x = anchor.x_in + radius * math.cos(angle)
                y = anchor.y_in + radius * math.sin(angle)
                if not L["setup_controller"].position_valid(token, x, y, squad=gw):
                    continue
                token.x_in, token.y_in = x, y
                if min(math.hypot(x - t.x_in, y - t.y_in) - t.radius_in - token.radius_in
                       for t in st.tokens if t is not token and not t.is_dead()) < 1.5:
                    continue
                if sc._is_valid_target_squad(target, st.tokens, attacking_squad=gw):
                    found = target
                    break
            if found:
                break
        if found:
            break
    if found is None:
        st.tokens.remove(token)
        state["e"] = {"error": "no ground from which a Gunwagon sees an unengaged Player 2 unit"}
        return
    sc.start_shooting(gw)
    sc.choose_target_squad(found)
    key = next((k for k, *rest in sc.weapon_eligibility() if "Kannon" in str(rest[0])), None)
    if key is None:
        state["e"] = {"error": "the Kannon is not eligible against %s" % found.name}
        return
    state["force"] = ("Kannon", 1, 1)
    rolls_before = len(state["rolls"])
    sc.choose_weapon(key)
    state["e"] = {"_gw": gw, "unit": gw.name, "target": found.name, "frame": state["frames"],
                  "rolls_before": rolls_before}


def _watch_e(L):
    e = state["e"]
    sc = L["shooting_controller"]
    settled = sc.current_group is None and not L["dice_manager"].is_pending
    if not (settled or state["frames"] - e["frame"] >= WAIT):
        return
    state["force"] = None
    labels = [lab for _f, lab in state["rolls"][e["rolls_before"]:]]
    e["labels"] = labels
    e["reroll_labels"] = [lab for lab in labels if "Hit Roll re-roll of 1s" in lab]
    try:
        sc.cancel()
    except Exception:
        pass
    e["done"] = True


# ------------------------------------------------------------ F. the boundary
def _stage_f(L):
    c = state["c"] or {}
    mob = c.get("_mob")
    if mob is None:
        state["f"] = {"error": "no mob from C"}
        return
    staged = []
    if not weirdboy_warpath.is_active(mob):
        mob.weirdboy_warpath_active = True
        staged.append("weirdboy_warpath_active")
    _set_phase(PHASE_FIGHT)
    tracker = state["tracker"]
    before = (tracker.battle_round, tracker.turn_index_in_round, tracker.phase)
    try:
        L["advance_turn_phase"]()
    except Exception as exc:
        state["f"] = {"error": "advance_turn_phase raised %r" % exc}
        return
    state["f"] = {"staged": staged, "clock": (before, (tracker.battle_round, tracker.turn_index_in_round,
                                                      tracker.phase)),
                  "active_after": weirdboy_warpath.is_active(mob), "done": True}


WATCH = {"g": _watch_g, "b": _watch_b, "c": _watch_c, "d": None, "e": _watch_e, "f": None}
STAGE = {"g": _stage_g, "b": _stage_b, "c": _stage_c, "d": _stage_d, "e": _stage_e, "f": _stage_f}


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
                    if (key != "g" or state["frames"] >= STAGE_AT) and _quiet(L):
                        STAGE[key](L)
                    break
                if record.get("error"):
                    raise SystemExit(0)
                if not record.get("done"):
                    WATCH[key](L)
                    if not state[key].get("done"):
                        break
                    # finished in this frame: the next stage may start in it too
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
g, b, cc, d, e, f = (state[k] or {} for k in ("g", "b", "c", "d", "e", "f"))


def _err(record):
    return (" ERROR " + record["error"]) if record.get("error") else ""


print()
print("--- Ork Mecha sheets, live" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
print("  frames                                  : %d" % state["frames"])
print("  A. Weirdboy Warpath on the FightController : %s (main()'s psychic roll %s, AI verdict %s)" % (
    w.get("warpath"), w.get("warpath_roll"), w.get("warpath_ai")))
print("     Da Jump on the registry                 : %s (main()'s roll/state/mover/clock %s)" % (
    w.get("da_jump"), w.get("da_jump_live")))
print("  G. %s, %.1f\" from Player 1, round %s%s" % (g.get("unit"), g.get("gap") or -1, g.get("round"), _err(g)))
print("     jumped at frame %s (Deep Strike %s), psychic rolls %s" % (
    g.get("jumped_at"), g.get("deep_strike_flag"), g.get("psychic")))
print("     back on the board %s, ingressed %s, deep striking %s, edge margin %s, [da jump] line %s" % (
    g.get("back"), g.get("ingressed"), g.get("deep_striking"),
    None if g.get("edge_margin") is None else round(g["edge_margin"], 1), g.get("log_line")))
print("     nearest Player 1 model: %s\" before the jump, %s\" after the landing" % (
    None if g.get("gap") is None else round(g["gap"], 1),
    None if g.get("gap_after") is None else round(g["gap_after"], 1)))
print("  B. %s%s: drawn %s, pressed %s" % (b.get("unit"), _err(b), b.get("drawn"), b.get("pressed")))
print("     roll %s (%s), reserves %s, off board %s, Deep Strike %s, deselected %s" % (
    b.get("pending"), b.get("pending_label"), b.get("in_reserves"), b.get("off_board"),
    b.get("deep_strike_flag"), b.get("deselected")))
print("     resolved by main() %s, shocked %s, can ingress %s, deep striking %s, mid-board landing %s" % (
    b.get("resolved"), b.get("shocked"), b.get("can_ingress"), b.get("deep_striking"), b.get("mid_board_landing")))
print("  C. %s vs %s%s: selectable %s, prompts %s, answered %s" % (
    cc.get("unit"), cc.get("target"), _err(cc), cc.get("selectable"),
    [(p["player"], p["labels"]) for p in cc.get("asked") or []], cc.get("chosen")))
print("     resolved %s, grant %s, live chain [PSYCHIC] %s" % (cc.get("resolved"), cc.get("active"),
                                                              cc.get("chain_psychic")))
print("     attack rolls: %s" % (cc.get("attack_labels"),))
print("  D. live melee %s / live ranged %s%s" % (d.get("melee"), d.get("ranged"), _err(d)))
print("  E. %s at %s%s: rolls %s" % (e.get("unit"), e.get("target"), _err(e), e.get("labels")))
print("  F. staged by hand %s, clock %s, grant after the boundary %s%s" % (
    f.get("staged"), f.get("clock"), f.get("active_after"), _err(f)))
print("  stale Player 1 prompts declined         : %s" % (state["declined_other"] or "none"))

if not state["wiring"] or any(r.get("error") for r in (g, b, cc, d, e, f)) or not f.get("done"):
    print("  INCONCLUSIVE - the run never got through the staging")
    raise SystemExit(2)


def _crossed_a_phase(record):
    clock = record.get("clock")
    return bool(clock) and clock[0] != clock[1]


if not NEUTRALIZE:
    checks = (
        ("the live FightController holds the Weirdboy's Warpath on main()'s psychic roll, with the AI's verdict",
         w.get("warpath") and w.get("warpath_roll") and w.get("warpath_ai")),
        ("Da Jump is on the live registry, on main()'s roll, state, mover and clock",
         w.get("da_jump") and w.get("da_jump_live")),
        ("the AI jumps its far-off Weirdboy mob through main()'s auto-play (psychic roll, Deep Strike)",
         g.get("jumped_at") is not None and bool(g.get("psychic")) and g.get("deep_strike_flag") is True),
        ("...and lands it again the same phase, with Deep Strike", g.get("back") is True
         and g.get("ingressed") is True and g.get("deep_striking") is True),
        ("...closer to the enemy than it stood - the jump is worth its psyker level",
         g.get("gap_after") is not None and g["gap_after"] < (g.get("gap") or 0)),
        ("Da Jump is DRAWN on main()'s panel for the Player 1 mob, and pressing it rolls",
         bool(b.get("drawn")) and b.get("pressed") is True and b.get("pending") is True
         and "Psychic roll: Da Jump" in (b.get("pending_label") or "")),
        ("...the whole mob goes into Strategic Reserves with Deep Strike, and the pick leaves it",
         b.get("in_reserves") is True and b.get("off_board") is True and b.get("deep_strike_flag") is True
         and b.get("deselected") is True),
        ("...main() resolves the roll (a 4: not shocked)", b.get("resolved") is True and b.get("shocked") is False),
        ("...and the live IngressController takes a mid-board landing for it",
         b.get("can_ingress") is True and b.get("deep_striking") is True and b.get("mid_board_landing") is not None),
        ("the Weirdboy's mob selected to fight asks Player 1 about Warpath",
         cc.get("selectable") is True and any(p["player"] == HUMAN for p in cc.get("asked") or [])
         and cc.get("chosen") is not None),
        ("...main() resolves the roll, the grant is up and the live chain gives [PSYCHIC]",
         cc.get("resolved") is True and cc.get("active") is True and cc.get("chain_psychic") is True),
        ("...and on the REAL wound roll its 1s come back as a 'Warpath (Weirdboy)' re-roll step",
         any("Warpath (Weirdboy)" in lab for lab in cc.get("reroll_labels") or [])),
        ("Sumfin' to Prove: +1 to hit on the live FightController, nothing on the live ShootingController",
         d.get("melee") == [(-1, sumfin_to_prove.SUMFIN_TO_PROVE_NAME)] and d.get("ranged") == []),
        ("Mobile Arsenal: the Kannon's hit 1s come back as their own re-roll step on the live ShootingController",
         any("Mobile Arsenal" in lab for lab in e.get("reroll_labels") or [])),
        ("main()'s phase boundary ends the Warpath grant",
         not f.get("staged") and _crossed_a_phase(f) and f.get("active_after") is False),
    )
else:
    checks = (
        ("no Weirdboy Warpath on the live FightController", not w.get("warpath")),
        ("Da Jump is not on the live registry", not w.get("da_jump")),
        ("the AI never jumps", g.get("jumped_at") is None and not g.get("psychic")),
        ("Da Jump is never drawn", not b.get("drawn")),
        ("no Warpath prompt", not cc.get("asked")),
        ("no wound 1s re-roll", not cc.get("reroll_labels")),
        ("no Sumfin' to Prove", d.get("melee") == []),
        ("no Mobile Arsenal re-roll", not e.get("reroll_labels") and bool(e.get("labels"))),
        ("the hand-staged grant survives the boundary", _crossed_a_phase(f) and f.get("active_after") is True),
    )
failed = 0
for label, ok in checks:
    print("  %s  %s" % ("PASS" if ok else "FAIL", label))
    failed += 0 if ok else 1
raise SystemExit(1 if failed else 0)
