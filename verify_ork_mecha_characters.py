"""Runtime proof through the REAL main() loop that the Mecha Orks characters (stage
G2) are wired: Da Boss, Makari, Fix Dat Armour Up, More Dakka (and the cover gate
it found) and the Prophet of da Great Waaagh! aura.

test_ork_mecha_characters.py drives each ability through real controllers built by
the test and pins main.py by AST. What it cannot show is that MAIN'S objects,
built by MAIN'S constructors in MAIN'S order, are connected when the game runs.
So this runs selfplay.py's real main() loop with the ORKS AS PLAYER 1 and asks
main()'s live objects:

  A. THE WIRING: Fix Dat Armour Up holds main()'s placer and state; Da Boss holds
     main()'s CommandPointManager; Makari is on the live panel registry.
  H. THE AI'S MAKARI through main()'s own auto-play: a Player 2 Ghazghkull with
     three Player 2 Boyz units in Advance + charge reach of Player 1, in Player 2's
     Movement phase of battle round 3 - the AI's take_one_action() -> _handle_makari()
     riles them up.
  B. DA BOSS at main()'s phase boundary: Player 1's Ghazghkull is the Warlord, and
     main()'s advance_turn_phase() pays 1CP for the round - once.
  C. MAKARI DRAWN on main()'s ActionPanel for Player 1's Ghazghkull in Player 1's
     Movement phase, pressed, a unit picked through main()'s DecisionManager.
  D. MORE DAKKA on the live ShootingController: a Big Mek-led Meganobz mob's
     attacks lose Benefit of Cover in the REAL hit modifiers, where a plain Meganob
     keeps it.
  E. THE PROPHET AURA on the live FightController: a Player 1 Boyz unit beside
     Ghazghkull gets +1 to hit and +1 to wound.
  F. FIX DAT ARMOUR UP at main()'s Command-phase boundary: the damaged mob's
     player is asked, the answer heals it, the use is spent.

STAGED, each named rather than quietly faked:
  * THE ORKS AS PLAYER 1, Player 2 Necrons; the units are BUILT (the shipped list
    does not field these sheets until stage G6), and Player 1's Ghazghkull is
    marked as the Warlord by hand (the shipped list names none).
  * The clock for each stage; B and F each call main()'s advance_turn_phase() once.
  * D puts the target in cover (_has_benefit_of_cover answers True on main()'s
    ShootingController for the read, then is restored).
  * H's Player 2 Orks: Player 2's army is Necrons, so the Ork units are built for it.
  * Player 1 prompts this harness does not answer are declined after STALE_FRAMES.

--neutralize loads main.py through an import hook with the main() seams undone
(Fix Dat's Command-phase call, both Da Boss syncs, Makari on the registry and for
the AI) and swaps game/more_dakka.py's and game/prophet_of_da_great_waaagh.py's
answers for "nothing". The files on disk are not touched.

Usage:  python verify_ork_mecha_characters.py [map2] [frames]
        python verify_ork_mecha_characters.py map2 --neutralize
"""

import importlib.abc
import importlib.util
import math
import os
import runpy
import sys

import pygame

from game import config, fix_dat_armour_up, makari, more_dakka, prophet_of_da_great_waaagh, riled_up
from game.attached_units import attach
from game.command_points import CommandPointManager
from game.da_boss import DaBossController
from game.decision import DecisionManager
from game.factions import build_squad
from game.factions.orks import BIG_MEK_MEGA_ARMOUR, BOYZ, GHAZGHKULL_THRAKA, MEGANOBZ
from game.fix_dat_armour_up import FixDatArmourUpController
from game.makari import MakariController
from game.turn import PHASES, PHASE_FIGHT, PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker
from game.ui.action_panel import ActionPanel
from game.weapons import MELEE, RANGED

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

HUMAN, AI = "Player 1", "Player 2"
STAGE_AT = 150
STALE_FRAMES = 30
WAIT = 400
AI_WAIT = 900

NEUTRALIZE_EDITS = (
    ("            fix_dat_armour_up_controller.begin_command_phase(state.all_squads(), turn_tracker.turn_owner)\n",
     "            pass\n"),
    ("        # Da Boss: \"at the start of the battle round\" - round 1's CP here.\n"
     "        da_boss_rule_controller.sync_battle_round(turn_tracker.battle_round)\n",
     "        pass\n"),
    ("        # Warlord's unit, so a mid-round load does not pay twice.\n"
     "        da_boss_rule_controller.sync_battle_round(turn_tracker.battle_round)\n",
     "        # Warlord's unit, so a mid-round load does not pay twice.\n        pass\n"),
    ("    makari_controller = proactive_stratagems.add(MakariController(\n",
     "    makari_controller = (lambda controller: controller)(MakariController(\n"),
    ("            makari_controller=makari_controller,\n", ""),
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
    more_dakka.adjusted_weapon = lambda weapon, squad: weapon
    prophet_of_da_great_waaagh.hit_modifiers = lambda squad, tokens: []
    prophet_of_da_great_waaagh.wound_modifiers = lambda squad, tokens: []

STAGES = ("h", "b", "c", "d", "e", "f")
state = {"frames": 0, "tracker": None, "wiring": None, "stale": None, "stale_since": 0,
         "declined_other": [], "prompts": [], "labels": [], "cp_gains": []}
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

_real_gain = CommandPointManager.gain_cp


def gain_cp(self, player, battle_round, amount=1, reason=None, *, source):
    granted = _real_gain(self, player, battle_round, amount, reason, source=source)
    state["cp_gains"].append((state["frames"], player, battle_round, granted, reason or ""))
    return granted


CommandPointManager.gain_cp = gain_cp

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
    if "Makari" in prompt or "Fix Dat" in prompt:
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


def _layout(center, count, spacing=1.35, per_row=4):
    rows = (count + per_row - 1) // per_row
    cols = min(count, per_row)
    out = []
    for i in range(count):
        r, col = divmod(i, per_row)
        out.append((center[0] + (col - (cols - 1) / 2.0) * spacing,
                    center[1] + (r - (rows - 1) / 2.0) * spacing))
    return out


def _fits(L, squad, spots, clearance=1.2):
    setup = L["setup_controller"]
    tokens = [t for t in L["state"].tokens if not t.is_dead() and t.squad is not squad]
    for model, (x, y) in zip(squad.models, spots):
        if not setup.position_valid(model, x, y, squad=squad):
            return False
        if any(math.hypot(x - t.x_in, y - t.y_in) < model.radius_in + t.radius_in + clearance for t in tokens):
            return False
    return True


def _gap_to(L, owner, spots):
    enemies = [t for t in L["state"].tokens if not t.is_dead() and t.squad is not None and t.squad.owner != owner]
    return min((math.hypot(x - t.x_in, y - t.y_in) - t.radius_in for x, y in spots for t in enemies), default=99.0)


def _place_somewhere(L, squad, want, clearance=1.2):
    """Place `squad` on the best-scoring legal cluster; returns the score or None."""
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


def _wiring(L):
    reg = L["proactive_stratagems"]
    fd = L.get("fix_dat_armour_up_controller")
    db = L.get("da_boss_rule_controller")
    return {
        "fix_dat": isinstance(fd, FixDatArmourUpController) and fd.placer is L.get("return_placement_controller")
        and fd.game_state is L["state"],
        "da_boss": isinstance(db, DaBossController) and db.command_points is L["command_points"],
        "makari": any(isinstance(c, MakariController) for c in reg.controllers),
    }


# ------------------------------------------------------------ H. the AI's Makari
def _stage_h(L):
    st = L["state"]
    gh = build_squad(GHAZGHKULL_THRAKA, AI, name="2 Ghazghkull Thraka (H)")
    boyz = [build_squad(BOYZ, AI, name="2 Boyz (H%d)" % i) for i in range(3)]
    if _place_somewhere(L, gh, lambda spots: -_gap_to(L, AI, spots) if _gap_to(L, AI, spots) > 14.0 else None) is None:
        state["h"] = {"error": "no ground for the Player 2 Ghazghkull"}
        return
    for unit in boyz:
        placed = _place_somewhere(
            L, unit, lambda spots: -abs(_gap_to(L, AI, spots) - 12.0) if 4.0 < _gap_to(L, AI, spots) < 18.0 else None)
        if placed is None:
            state["h"] = {"error": "no ground for the Player 2 Boyz within reach of Player 1"}
            return
    state["tracker"].battle_round = max(3, state["tracker"].battle_round)
    for unit in [gh] + boyz:
        L["movement_controller"].moved_squad_ids.discard(unit)
    _set_phase(PHASE_MOVEMENT, AI)
    state["h"] = {"_gh": gh, "_boyz": boyz, "frame": state["frames"], "round": state["tracker"].battle_round,
                  "gaps": [round(_gap_to(L, AI, [(m.x_in, m.y_in) for m in u.models]), 1) for u in boyz]}


def _watch_h(L):
    h = state["h"]
    used = bool(getattr(h["_gh"], "makari_used", False))
    if used or state["frames"] - h["frame"] >= AI_WAIT:
        h["used"] = used
        h["riled"] = [u.name for u in h["_boyz"] if riled_up.is_riled_up(u)]
        h["done"] = True


# ------------------------------------------------------------ B. Da Boss
def _player1_ghazghkull(L):
    gh = state.get("_gh1")
    if gh is None:
        gh = build_squad(GHAZGHKULL_THRAKA, HUMAN, name="1 Ghazghkull Thraka (staged)")
        if _place_somewhere(L, gh, lambda spots: _gap_to(L, HUMAN, spots) if _gap_to(L, HUMAN, spots) > 10.0 else None) is None:
            return None
        gh.models[0].warlord = True
        state["_gh1"] = gh
    return gh


def _stage_b(L):
    gh = _player1_ghazghkull(L)
    if gh is None:
        state["b"] = {"error": "no ground for Player 1's Ghazghkull"}
        return
    tracker = state["tracker"]
    before = len(state["cp_gains"])
    _set_phase(PHASE_FIGHT, HUMAN)
    try:
        L["advance_turn_phase"]()
    except Exception as exc:
        state["b"] = {"error": "advance_turn_phase raised %r" % exc}
        return
    first = [g for g in state["cp_gains"][before:] if "Da Boss" in g[4] and g[1] == HUMAN]
    mid = len(state["cp_gains"])
    _set_phase(PHASE_MOVEMENT, HUMAN)
    try:
        L["advance_turn_phase"]()
    except Exception as exc:
        state["b"] = {"error": "second advance_turn_phase raised %r" % exc}
        return
    second = [g for g in state["cp_gains"][mid:] if "Da Boss" in g[4] and g[1] == HUMAN]
    state["b"] = {"first": first, "second": second, "stamp": getattr(gh, "da_boss_round", None),
                  "round": tracker.battle_round, "done": True}


# ------------------------------------------------------------ C. Makari on the panel
def _stage_c(L):
    gh = _player1_ghazghkull(L)
    if gh is None:
        state["c"] = {"error": "no Player 1 Ghazghkull"}
        return
    L["movement_controller"].moved_squad_ids.discard(gh)
    _set_phase(PHASE_MOVEMENT)
    L["movement_controller"].select(_alive(gh)[0])
    state["c"] = {"_gh": gh, "frame": state["frames"], "labels_before": len(state["labels"])}


def _watch_c(L):
    c = state["c"]
    gh = c["_gh"]
    tracker = state["tracker"]
    if tracker.phase != PHASE_MOVEMENT or tracker.turn_owner != HUMAN:
        _set_phase(PHASE_MOVEMENT)
    if L["movement_controller"].selected_squad is not gh:
        L["movement_controller"].select(_alive(gh)[0])
    drawn = [lab for _f, lab in state["labels"][c["labels_before"]:] if lab.startswith(makari.MAKARI_NAME)]
    if not drawn and state["frames"] - c["frame"] < WAIT:
        return
    c["drawn"] = drawn[:1]
    c["done"] = True
    if not drawn:
        return
    panel = L["action_panel"]
    rect = next((r for r, n in panel._stratagem_buttons if n == makari.MAKARI_NAME), None)
    callback = next((cb for r, cb in panel._buttons if r == rect), None) if rect is not None else None
    if callback is None:
        return
    prompts_before = len(state["prompts"])
    callback()
    decisions = L["decision_manager"]
    asked = [p for p in state["prompts"][prompts_before:] if "Makari" in p["prompt"]]
    picked = None
    if decisions.is_pending:
        index = next((i for i, o in enumerate(decisions.options) if o["label"].startswith(makari.MAKARI_NAME)), None)
        if index is not None:
            picked = decisions.options[index]["label"].split(": ", 1)[1]
            decisions.choose(index)
    if decisions.is_pending and "Makari" in (decisions.prompt or ""):
        decisions.choose(len(decisions.options) - 1)   # Done
    c["asked"] = asked
    c["picked"] = picked
    target = next((s for s in L["state"].all_squads() if s.name == picked), None)
    c["riled"] = riled_up.is_riled_up(target) if target is not None else None
    c["used"] = bool(getattr(gh, "makari_used", False))


# ------------------------------------------------------------ D. More Dakka
def _stage_d(L):
    st = L["state"]
    target = next((s for s in sorted(st.all_squads(), key=lambda s: -len(_alive(s)))
                   if s.owner == AI and _alive(s) and s not in st.reserves
                   and all(m in st.tokens for m in _alive(s))), None)
    if target is None:
        state["d"] = {"error": "no Player 2 unit on the board"}
        return
    mob = attach(build_squad(BIG_MEK_MEGA_ARMOUR, HUMAN, name="1 Big Mek in Mega Armour (D)"),
                 build_squad(MEGANOBZ, HUMAN, name="1 Meganobz (D)", composition_index=1))
    plain = build_squad(MEGANOBZ, HUMAN, name="1 Meganobz (D plain)", composition_index=1)
    sc = L["shooting_controller"]
    _set_phase(PHASE_SHOOTING)
    out = {}
    real = sc._has_benefit_of_cover
    try:
        sc._has_benefit_of_cover = lambda shooter_model, target_squad: True
        for key, squad in (("mob", mob), ("plain", plain)):
            nob = next(m for m in squad.models if not m.profile.character)
            gun = next(w for w in nob.weapons if w.weapon_type == RANGED)
            saved = sc.active_squad
            sc.active_squad = squad
            try:
                out[key] = [(m.amount, m.source) for m in sc._hit_modifiers(
                    {"pairs": [(nob, gun)], "target_squad": target}) if m.source == "Benefit of Cover"]
                out[key + "_ignores"] = bool(sc._adjusted_weapon([(nob, gun)], target).ignores_cover)
            finally:
                sc.active_squad = saved
    finally:
        sc._has_benefit_of_cover = real
    out["target"] = target.name
    out["_mob"] = mob
    out["done"] = True
    state["d"] = out


# ------------------------------------------------------------ E. the Prophet aura
def _stage_e(L):
    gh = _player1_ghazghkull(L)
    if gh is None:
        state["e"] = {"error": "no Player 1 Ghazghkull"}
        return
    boyz = build_squad(BOYZ, HUMAN, name="1 Boyz (E)")
    anchor = gh.models[0]
    for i, model in enumerate(boyz.models):
        model.x_in = anchor.x_in + anchor.radius_in + 1.0 + (i % 5) * 1.0
        model.y_in = anchor.y_in + (i // 5) * 1.0
    target = next((s for s in L["state"].all_squads() if s.owner == AI and _alive(s)), None)
    fc = L["fight_controller"]
    saved = fc.fighting_squad
    try:
        for model in boyz.models:
            L["state"].add_token(model)
        fc.fighting_squad = boyz
        choppa = next(w for w in boyz.models[1].weapons if w.weapon_type == MELEE)
        hit = [(m.amount, m.source) for m in fc._hit_modifiers(boyz.models[1], target)
               if m.source == prophet_of_da_great_waaagh.PROPHET_NAME]
        wound = [(m.amount, m.source) for m in fc._wound_modifiers(choppa, target)
                 if m.source == prophet_of_da_great_waaagh.PROPHET_NAME]
    finally:
        fc.fighting_squad = saved
        for model in boyz.models:
            if model in L["state"].tokens:
                L["state"].tokens.remove(model)
    state["e"] = {"hit": hit, "wound": wound, "done": True}


# ------------------------------------------------------------ F. Fix Dat Armour Up
def _stage_f(L):
    d = state["d"] or {}
    mob = d.get("_mob")
    if mob is None:
        state["f"] = {"error": "no mob from D"}
        return
    if _place_somewhere(L, mob, lambda spots: _gap_to(L, HUMAN, spots) if _gap_to(L, HUMAN, spots) > 10.0 else None) is None:
        state["f"] = {"error": "no ground for the Big Mek mob"}
        return
    nobs = [m for m in mob.models if not m.profile.character]
    nobs[0].current_wounds = 1
    nobs[1].current_wounds = 2
    before = sum(m.current_wounds for m in mob.models)
    prompts_before = len(state["prompts"])
    _set_phase(PHASE_FIGHT, AI)
    tracker = state["tracker"]
    tracker.turn_index_in_round = 1
    try:
        L["advance_turn_phase"]()
    except Exception as exc:
        state["f"] = {"error": "advance_turn_phase raised %r" % exc}
        return
    decisions = L["decision_manager"]
    asked = [p for p in state["prompts"][prompts_before:] if "Fix Dat Armour Up" in p["prompt"]]
    chosen = None
    for _ in range(6):
        if not decisions.is_pending:
            break
        if "Fix Dat Armour Up" in (decisions.prompt or ""):
            index = next(i for i, o in enumerate(decisions.options) if o["label"] == fix_dat_armour_up.USE_LABEL)
            chosen = decisions.options[index]["label"]
            decisions.choose(index)
            break
        decisions.choose(len(decisions.options) - 1)
    state["f"] = {"asked": asked, "chosen": chosen, "owner": tracker.turn_owner, "phase": tracker.phase,
                  "before": before, "after": sum(m.current_wounds for m in mob.models),
                  "used": bool(getattr(mob, "fix_dat_armour_up_used", False)), "done": True}


WATCH = {"h": _watch_h, "b": None, "c": _watch_c, "d": None, "e": None, "f": None}
STAGE = {"h": _stage_h, "b": _stage_b, "c": _stage_c, "d": _stage_d, "e": _stage_e, "f": _stage_f}


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
h, b, cc, d, e, f = (state[k] or {} for k in ("h", "b", "c", "d", "e", "f"))


def _err(record):
    return (" ERROR " + record["error"]) if record.get("error") else ""


print()
print("--- Ork Mecha characters, live" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
print("  frames                                 : %d" % state["frames"])
print("  A. wiring: Fix Dat %s, Da Boss %s, Makari on the registry %s" % (
    w.get("fix_dat"), w.get("da_boss"), w.get("makari")))
print("  H. round %s, Player 2 Boyz gaps %s%s: Makari used %s, riled %s" % (
    h.get("round"), h.get("gaps"), _err(h), h.get("used"), h.get("riled")))
print("  B. Da Boss gains: first boundary %s, second %s, stamp %s%s" % (
    [(g[2], g[3]) for g in b.get("first") or []], [(g[2], g[3]) for g in b.get("second") or []],
    b.get("stamp"), _err(b)))
print("  C. drawn %s, prompts %s, picked %s -> riled %s, used %s%s" % (
    cc.get("drawn"), [p["labels"][:2] for p in cc.get("asked") or []], cc.get("picked"), cc.get("riled"),
    cc.get("used"), _err(cc)))
print("  D. vs %s: More Dakka mob cover %s (ignores %s), plain Meganob cover %s%s" % (
    d.get("target"), d.get("mob"), d.get("mob_ignores"), d.get("plain"), _err(d)))
print("  E. Prophet: hit %s, wound %s%s" % (e.get("hit"), e.get("wound"), _err(e)))
print("  F. %s's %s: prompts %s, answered %s, wounds %s -> %s, spent %s%s" % (
    f.get("owner"), f.get("phase"), [p["labels"] for p in f.get("asked") or []], f.get("chosen"),
    f.get("before"), f.get("after"), f.get("used"), _err(f)))
print("  stale Player 1 prompts declined        : %s" % (state["declined_other"] or "none"))

if not state["wiring"] or any(r.get("error") for r in (h, b, cc, d, e, f)) or not f.get("done"):
    print("  INCONCLUSIVE - the run never got through the staging")
    raise SystemExit(2)

if not NEUTRALIZE:
    checks = (
        ("Fix Dat Armour Up holds main()'s placer and state; Da Boss main()'s CP ledger; Makari is registered",
         w.get("fix_dat") and w.get("da_boss") and w.get("makari")),
        ("the AI's own auto-play uses Makari on its three Boyz units in round 3",
         h.get("used") is True and len(h.get("riled") or []) == 3),
        ("Da Boss: main()'s phase boundary pays Player 1's Warlord 1CP, stamped with the round",
         [g[3] for g in b.get("first") or []] == [1] and b.get("stamp") == (b.get("first") or [[0, 0, None]])[0][2]),
        ("...and the next boundary of the same round pays nothing", not b.get("second")),
        ("Makari is DRAWN on main()'s panel for Ghazghkull, and the pick riles a unit up and spends the use",
         bool(cc.get("drawn")) and bool(cc.get("asked")) and cc.get("riled") is True and cc.get("used") is True),
        ("More Dakka: the live ShootingController drops Benefit of Cover for the Big Mek's mob, not for a plain one",
         d.get("mob") == [] and d.get("mob_ignores") is True and d.get("plain") == [(1, "Benefit of Cover")]),
        ("the Prophet aura: +1 to hit and +1 to wound on the live FightController",
         e.get("hit") == [(-1, prophet_of_da_great_waaagh.PROPHET_NAME)]
         and e.get("wound") == [(-1, prophet_of_da_great_waaagh.PROPHET_NAME)]),
        ("Fix Dat Armour Up: main()'s Command boundary asks Player 1",
         f.get("owner") == HUMAN and any(p["player"] == HUMAN for p in f.get("asked") or [])),
        ("...and the answer heals 3 and spends the use",
         f.get("chosen") == fix_dat_armour_up.USE_LABEL and (f.get("after") or 0) - (f.get("before") or 0) == 3
         and f.get("used") is True),
    )
else:
    checks = (
        ("Makari is not on the live registry", not w.get("makari")),
        ("the AI never uses Makari", not h.get("used")),
        ("Da Boss pays nothing", not b.get("first") and not b.get("second")),
        ("Makari is never drawn", not cc.get("drawn")),
        ("More Dakka does not bite: the mob keeps Benefit of Cover", d.get("mob") == [(1, "Benefit of Cover")]),
        ("no Prophet modifiers", not e.get("hit") and not e.get("wound")),
        ("Fix Dat Armour Up is never asked", not f.get("asked") and not f.get("used")),
    )
failed = 0
for label, ok in checks:
    print("  %s  %s" % ("PASS" if ok else "FAIL", label))
    failed += 0 if ok else 1
raise SystemExit(1 if failed else 0)
