"""Runtime proof through the REAL main() loop that Green Tide (Mecha Orks stage G3)
is wired: its three Stratagem buttons, the AI's Mob Mentality, Mob-handed
Brutality and 'Ardboyz on main()'s own objects, and the three grants ending at
main()'s phase boundary.

test_ork_green_tide.py and test_ork_green_tide_ui.py drive every piece through
real controllers built by the tests and pin main.py by AST. What they cannot show
is that MAIN'S objects, built by MAIN'S constructors in MAIN'S order, are
connected when the game runs. So this runs selfplay.py's real main() loop with the
ORKS AS PLAYER 1 and asks main()'s live objects:

  A. THE WIRING: the three controllers are on main()'s panel registry; Mob
     Mentality holds main()'s BattleShockController, DecisionManager, token list
     and a line-of-sight callable; Unbridled Carnage main()'s FightController;
     'Ere We Go main()'s MovementController.
  H. THE AI'S MOB MENTALITY through main()'s own auto-play: a Player 2 Boyz mob of
     20 and a Player 2 Beast Snagga Boyz unit below half strength beside it, in
     Player 2's Command phase - take_one_action() -> _handle_mob_mentality() buys
     it, and the AI's own Battle-shock test for that unit then passes WITHOUT
     dice.
  B. MOB MENTALITY DRAWN on main()'s ActionPanel for Player 1's mob of 20, pressed
     (one candidate: no prompt), paid; main()'s BattleShockController then passes
     the battle-shocked unit's 08.03 test without dice.
  C. 'ERE WE GO DRAWN for Player 1's Boyz in Player 1's Movement phase, pressed,
     paid; the Advance roll's terms carry +2.
  D. UNBRIDLED CARNAGE DRAWN for Player 1's charged Boyz unit, engaged with a
     Player 2 unit in Player 1's Fight phase, pressed, paid; main()'s
     FightController chain then gives the Boyz' Choppa +1 A and [SUSTAINED HITS 1]
     (Mob-handed Brutality), and a charged Beast Snagga Boyz unit's weapon
     [LETHAL HITS] against that non-VEHICLE target.
  E. 'ARDBOYZ: main()'s datacard prints 4+ for a Boy of the mob that bought it,
     and the save roll's threshold is 4.
  F. THE RESETS: main()'s advance_turn_phase() ends all three grants.

STAGED, each named rather than quietly faked:
  * THE ORKS AS PLAYER 1, Player 2 Necrons; the units are BUILT (the shipped list
    fields War Horde until stage G6). config.GREEN_TIDE_PLAYERS is set for both
    players and config.WAR_HORDE_PLAYERS cleared, at the first stage: War Horde's
    Get Stuck In would otherwise hand every Ork [SUSTAINED HITS 1] and make D's
    Sustained Hits check prove nothing.
  * The clock for each stage; the Command-phase stages call main()'s
    battle_shock_controller.reset_command_phase() - the "start of the Command
    phase" main() itself runs on the real boundary - and top the player's CP up.
  * A Beast Snagga Boyz unit "below half strength" is built with 4 of its 10
    models; D engages the mob by placing it beside a Player 2 unit.
  * Player 1 prompts this harness does not answer are declined after STALE_FRAMES.

--neutralize loads main.py through an import hook with the main() seams undone
(the three registry adds, the three resets, Mob Mentality for the AI) and swaps
game/green_tide.py's and game/enh_ardboyz.py's answers for "nothing". The files
on disk are not touched.

Usage:  python verify_ork_green_tide.py [map2] [frames]
        python verify_ork_green_tide.py map2 --neutralize
"""

import importlib.abc
import importlib.util
import math
import os
import runpy
import sys

import pygame

from game import (config, damage_resolution, enh_ardboyz, enhancements, green_tide, green_tide_ere_we_go as ewg,
                  green_tide_mob_mentality as mm, green_tide_unbridled_carnage as uc, movement)
from game.battle_shock import BattleShockController
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import build_squad
from game.factions.orks import BEAST_SNAGGA_BOYZ, BOYZ
from game.fight import FightController
from game.turn import PHASES, PHASE_COMMAND, PHASE_FIGHT, PHASE_MOVEMENT, TurnTracker
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
    ("    unbridled_carnage_controller = proactive_stratagems.add(UnbridledCarnageController(\n",
     "    unbridled_carnage_controller = (lambda controller: controller)(UnbridledCarnageController(\n"),
    ("    ere_we_go_controller = proactive_stratagems.add(EreWeGoController(\n",
     "    ere_we_go_controller = (lambda controller: controller)(EreWeGoController(\n"),
    ("    mob_mentality_controller = proactive_stratagems.add(MobMentalityController(\n",
     "    mob_mentality_controller = (lambda controller: controller)(MobMentalityController(\n"),
    ("        unbridled_carnage_controller.reset_phase(_horde_squads)\n"
     "        ere_we_go_controller.reset_phase(_horde_squads)\n"
     "        mob_mentality_controller.reset_phase(_horde_squads)\n", ""),
    ("            mob_mentality_controller=mob_mentality_controller,\n", ""),
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
    green_tide.adjusted_weapon = lambda weapon, squad, target_squad=None: weapon
    enh_ardboyz.save_override = lambda model: None

STAGES = ("h", "b", "c", "d", "e", "f")
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
    if mm.MOB_MENTALITY_NAME in prompt:
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


def _gap_to(L, owner, spots, squad=None):
    """Edge-of-enemy distance from the nearest spot (or to `squad` only)."""
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


def _stage_everything(L):
    """The two config settings, once - see STAGED in the module docstring."""
    if not state["staged"]:
        config.GREEN_TIDE_PLAYERS = (HUMAN, AI)
        config.WAR_HORDE_PLAYERS = ()
        state["staged"] = True


def _wiring(L):
    reg = L["proactive_stratagems"]
    by_type = {type(c).__name__: c for c in reg.controllers}
    mmc = L.get("mob_mentality_controller")
    ucc = L.get("unbridled_carnage_controller")
    ewc = L.get("ere_we_go_controller")
    return {
        "registered": sorted(n for n in ("UnbridledCarnageController", "EreWeGoController", "MobMentalityController")
                             if n in by_type),
        "mob_mentality": isinstance(mmc, mm.MobMentalityController)
        and mmc.battle_shock_controller is L["battle_shock_controller"]
        and mmc.decision_manager is L["decision_manager"] and mmc.all_tokens is L["state"].tokens
        and mmc.visible is not None,
        "unbridled_carnage": isinstance(ucc, uc.UnbridledCarnageController)
        and ucc.fight_controller is L["fight_controller"],
        "ere_we_go": isinstance(ewc, ewg.EreWeGoController) and ewc.movement_controller is L["movement_controller"],
    }


def _mob_and_straggler(L, owner, tag):
    """A 20-model Boyz mob clear of the enemy (more than 6", preferring 20"), and
    a Beast Snagga Boyz unit of 4 (of 10) right beside it. None if the board has
    no room."""
    mob = build_squad(BOYZ, owner, name="%s Boyz (%s)" % (owner[-1], tag), composition_index=1)
    if _place_somewhere(L, mob, lambda spots: -abs(_gap_to(L, owner, spots) - 20.0)
                        if _gap_to(L, owner, spots) > 6.0 else None) is None:
        return None, None
    bsb = build_squad(BEAST_SNAGGA_BOYZ, owner, name="%s Beast Snagga Boyz (%s)" % (owner[-1], tag))
    bsb.models = bsb.models[:4]
    if _place_somewhere(L, bsb, lambda spots: -_gap_to(L, owner, spots, squad=mob)
                        if 1.0 < _gap_to(L, owner, spots, squad=mob) < 4.0 else None) is None:
        return mob, None
    return mob, bsb


def _command_phase_for(L, owner):
    _set_phase(PHASE_COMMAND, owner)
    L["battle_shock_controller"].reset_command_phase()
    L["command_points"].cp[owner] = max(L["command_points"].cp.get(owner, 0), 3)


def _press(L, name):
    panel = L["action_panel"]
    rect = next((r for r, n in panel._stratagem_buttons if n == name), None)
    callback = next((cb for r, cb in panel._buttons if r == rect), None) if rect is not None else None
    if callback is None:
        return False
    callback()
    return True


# ------------------------------------------------------ H. the AI's Mob Mentality
def _stage_h(L):
    _stage_everything(L)
    mob, bsb = _mob_and_straggler(L, AI, "H")
    if bsb is None:
        state["h"] = {"error": "no ground for the Player 2 mob and its straggler"}
        return
    visible = L["mob_mentality_controller"].visible(mob, bsb)
    _command_phase_for(L, AI)
    state["h"] = {"_mob": mob, "_bsb": bsb, "frame": state["frames"], "visible": visible,
                  "rolls_before": len(state["rolls"])}


def _watch_h(L):
    h = state["h"]
    bsc = L["battle_shock_controller"]
    rolled = h["_bsb"] in bsc.rolled_squad_ids
    if rolled or state["frames"] - h["frame"] >= AI_WAIT:
        h["covered"] = mm.auto_passes(h["_bsb"])
        h["rolled"] = rolled
        h["dice"] = [r[1] for r in state["rolls"][h["rolls_before"]:] if r[2] == h["_bsb"].name]
        h["shocked"] = h["_bsb"].battle_shocked
        # WHICH rule passed it: Insane Bravery also passes without dice, so the
        # log line has to name Mob Mentality.
        h["by"] = [str(e) for e in L["game_log"].entries
                   if h["_bsb"].name in e and "automatically succeeds" in e]
        h["done"] = True


# ------------------------------------------------------ B. Mob Mentality on the panel
def _stage_b(L):
    mob, bsb = _mob_and_straggler(L, HUMAN, "B")
    if bsb is None:
        state["b"] = {"error": "no ground for Player 1's mob and its straggler"}
        return
    bsb.battle_shocked = True
    _command_phase_for(L, HUMAN)
    L["movement_controller"].select(_alive(mob)[0])
    state["b"] = {"_mob": mob, "_bsb": bsb, "frame": state["frames"], "labels_before": len(state["labels"]),
                  "visible": L["mob_mentality_controller"].visible(mob, bsb)}


def _watch_b(L):
    b = state["b"]
    tracker = state["tracker"]
    if tracker.phase != PHASE_COMMAND or tracker.turn_owner != HUMAN:
        _set_phase(PHASE_COMMAND)
    if L["movement_controller"].selected_squad is not b["_mob"]:
        L["movement_controller"].select(_alive(b["_mob"])[0])
    drawn = [lab for _f, lab in state["labels"][b["labels_before"]:] if lab.startswith(mm.MOB_MENTALITY_NAME)]
    if not drawn and state["frames"] - b["frame"] < WAIT:
        return
    b["drawn"] = drawn[:1]
    b["done"] = True
    if not drawn:
        return
    cp = L["command_points"].cp[HUMAN]
    b["pressed"] = _press(L, mm.MOB_MENTALITY_NAME)
    b["asked"] = L["decision_manager"].is_pending
    b["paid"] = cp - L["command_points"].cp[HUMAN]
    b["covered"] = mm.auto_passes(b["_bsb"])
    rolls_before = len(state["rolls"])
    L["battle_shock_controller"].start_roll(b["_bsb"])
    b["dice"] = [r[1] for r in state["rolls"][rolls_before:]]
    b["shocked"] = b["_bsb"].battle_shocked
    b["rolled"] = b["_bsb"] in L["battle_shock_controller"].rolled_squad_ids


# ------------------------------------------------------ C. 'Ere We Go on the panel
def _stage_c(L):
    boyz = build_squad(BOYZ, HUMAN, name="1 Boyz (C)")
    if _place_somewhere(L, boyz, lambda spots: _gap_to(L, HUMAN, spots) if _gap_to(L, HUMAN, spots) > 12.0 else None) is None:
        state["c"] = {"error": "no ground for Player 1's Boyz"}
        return
    L["command_points"].cp[HUMAN] = max(L["command_points"].cp[HUMAN], 3)
    _set_phase(PHASE_MOVEMENT)
    L["movement_controller"].moved_squad_ids.discard(boyz)
    L["movement_controller"].select(_alive(boyz)[0])
    state["c"] = {"_boyz": boyz, "frame": state["frames"], "labels_before": len(state["labels"])}


def _watch_c(L):
    c = state["c"]
    tracker = state["tracker"]
    if tracker.phase != PHASE_MOVEMENT or tracker.turn_owner != HUMAN:
        _set_phase(PHASE_MOVEMENT)
    if L["movement_controller"].selected_squad is not c["_boyz"]:
        L["movement_controller"].select(_alive(c["_boyz"])[0])
    drawn = [lab for _f, lab in state["labels"][c["labels_before"]:] if lab.startswith(ewg.ERE_WE_GO_NAME)]
    if not drawn and state["frames"] - c["frame"] < WAIT:
        return
    c["drawn"] = drawn[:1]
    c["done"] = True
    if not drawn:
        return
    cp = L["command_points"].cp[HUMAN]
    c["pressed"] = _press(L, ewg.ERE_WE_GO_NAME)
    c["paid"] = cp - L["command_points"].cp[HUMAN]
    c["terms"] = movement.advance_roll_modifiers(c["_boyz"], L["state"].tokens)
    c["total_on_3"] = movement.advance_total(c["_boyz"], [3], L["state"].tokens)


# ------------------------------------------------------ D. Unbridled Carnage + the rule
def _stage_d(L):
    st = L["state"]
    targets = [s for s in sorted(st.all_squads(), key=lambda s: (-len(_alive(s)), s.name))
               if s.owner == AI and _alive(s) and s not in st.reserves
               and all(m in st.tokens for m in _alive(s))
               and not any(m.profile.vehicle or m.profile.monster for m in _alive(s))]
    if not targets:
        state["d"] = {"error": "no Player 2 infantry unit on the board"}
        return
    # Engaged = edge to edge within 2": the nearest Boy's CENTRE 0.6-2.3" from the
    # target's edge (a Boy's base is ~0.5" in radius). Every infantry target is
    # tried in turn - a unit packed among its friends may have no room beside it.
    mob = build_squad(BOYZ, HUMAN, name="1 Boyz (D)")
    target = None
    for candidate in targets:
        placed = _place_somewhere(
            L, mob, lambda spots, t=candidate: -abs(_gap_to(L, HUMAN, spots, squad=t) - 1.2)
            if 0.6 < _gap_to(L, HUMAN, spots, squad=t) < 2.3 else None, clearance=0.05)
        if placed is not None:
            target = candidate
            break
    if target is None:
        state["d"] = {"error": "no ground beside any of %s" % [t.name for t in targets]}
        return
    mob.charged_this_turn = True
    bsb = build_squad(BEAST_SNAGGA_BOYZ, HUMAN, name="1 Beast Snagga Boyz (D)")
    bsb.charged_this_turn = True
    L["command_points"].cp[HUMAN] = max(L["command_points"].cp[HUMAN], 3)
    _set_phase(PHASE_FIGHT)
    L["movement_controller"].select(_alive(mob)[0])
    state["d"] = {"_mob": mob, "_bsb": bsb, "_target": target, "target": target.name,
                  "frame": state["frames"], "labels_before": len(state["labels"])}


def _watch_d(L):
    d = state["d"]
    tracker = state["tracker"]
    if tracker.phase != PHASE_FIGHT or tracker.turn_owner != HUMAN:
        _set_phase(PHASE_FIGHT)
    if L["movement_controller"].selected_squad is not d["_mob"]:
        L["movement_controller"].select(_alive(d["_mob"])[0])
    drawn = [lab for _f, lab in state["labels"][d["labels_before"]:] if lab.startswith(uc.UNBRIDLED_CARNAGE_NAME)]
    if not drawn and state["frames"] - d["frame"] < WAIT:
        return
    d["drawn"] = drawn[:1]
    d["done"] = True
    fc = L["fight_controller"]
    d["eligible"] = fc.is_eligible_to_fight(d["_mob"])
    if drawn:
        cp = L["command_points"].cp[HUMAN]
        d["pressed"] = _press(L, uc.UNBRIDLED_CARNAGE_NAME)
        d["paid"] = cp - L["command_points"].cp[HUMAN]
    boy = next(m for m in d["_mob"].models if not m.profile.character
               and any(w.weapon_type == MELEE and w.name == "Choppa" for w in m.weapons))
    choppa = next(w for w in boy.weapons if w.weapon_type == MELEE and w.name == "Choppa")
    bb = d["_bsb"].models[1]
    bw = next(w for w in bb.weapons if w.weapon_type == MELEE)
    saved = fc.fighting_squad
    try:
        fc.fighting_squad = d["_mob"]
        adj = fc._adjusted_weapon([(boy, choppa)], d["_target"])
        d["choppa"] = (choppa.attacks, adj.attacks, adj.sustained_hits)
        fc.fighting_squad = d["_bsb"]
        badj = fc._adjusted_weapon([(bb, bw)], d["_target"])
        d["bsb_lethal"] = (bool(bw.lethal_hits), bool(badj.lethal_hits))
    finally:
        fc.fighting_squad = saved


# ------------------------------------------------------ E. 'Ardboyz
def _stage_e(L):
    mob = build_squad(BOYZ, HUMAN, name="1 Boyz (E)")
    enhancements.grant(mob, enh_ardboyz.ARDBOYZ)
    if _place_somewhere(L, mob, lambda spots: _gap_to(L, HUMAN, spots) if _gap_to(L, HUMAN, spots) > 10.0 else None) is None:
        state["e"] = {"error": "no ground for the 'Ardboyz"}
        return
    boy = next(m for m in mob.models if not m.profile.character)
    gun = next(w for w in boy.weapons if w.weapon_type == RANGED)
    rows = dict(L["unit_datacard"].card_parts(boy)["stat_rows"])
    state["e"] = {"printed": boy.profile.armor_save, "card": rows.get("Sv"),
                  "threshold": damage_resolution.save_thresholds(boy, gun)[0], "done": True}


# ------------------------------------------------------ F. the resets
def _stage_f(L):
    marked = [(state[k] or {}).get(u) for k, u in (("b", "_bsb"), ("c", "_boyz"), ("d", "_mob"))]
    if any(s is None for s in marked):
        state["f"] = {"error": "an earlier stage left nothing to reset"}
        return
    bsb, boyz, mob = marked
    before = (mm.auto_passes(bsb), ewg.is_active(boyz), uc.is_active(mob))
    _set_phase(PHASE_FIGHT, HUMAN)
    try:
        L["advance_turn_phase"]()
    except Exception as exc:
        state["f"] = {"error": "advance_turn_phase raised %r" % exc}
        return
    state["f"] = {"before": before, "after": (mm.auto_passes(bsb), ewg.is_active(boyz), uc.is_active(mob)),
                  "done": True}


WATCH = {"h": _watch_h, "b": _watch_b, "c": _watch_c, "d": _watch_d, "e": None, "f": None}
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
print("--- Ork Green Tide, live" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
print("  frames                                 : %d" % state["frames"])
print("  A. registered %s; Mob Mentality wired %s, Unbridled Carnage %s, 'Ere We Go %s" % (
    w.get("registered"), w.get("mob_mentality"), w.get("unbridled_carnage"), w.get("ere_we_go")))
print("  H. visible %s%s: covered %s, rolled %s, dice %s, battle-shocked %s, passed by %s" % (
    h.get("visible"), _err(h), h.get("covered"), h.get("rolled"), h.get("dice"), h.get("shocked"),
    [line.split("(")[-1].split(")")[0] for line in h.get("by") or []]))
print("  B. visible %s, drawn %s, pressed %s, asked %s, paid %s, covered %s; 08.03 dice %s, shocked %s, rolled %s%s" % (
    b.get("visible"), b.get("drawn"), b.get("pressed"), b.get("asked"), b.get("paid"), b.get("covered"),
    b.get("dice"), b.get("shocked"), b.get("rolled"), _err(b)))
print("  C. drawn %s, pressed %s, paid %s, terms %s, a 3 becomes %s%s" % (
    cc.get("drawn"), cc.get("pressed"), cc.get("paid"), cc.get("terms"), cc.get("total_on_3"), _err(cc)))
print("  D. vs %s: eligible %s, drawn %s, pressed %s, paid %s; Choppa A/A'/SH %s; BSB lethal printed/chain %s%s" % (
    d.get("target"), d.get("eligible"), d.get("drawn"), d.get("pressed"), d.get("paid"), d.get("choppa"),
    d.get("bsb_lethal"), _err(d)))
print("  E. 'Ardboyz: printed %s, datacard %s, save threshold %s%s" % (
    e.get("printed"), e.get("card"), e.get("threshold"), _err(e)))
print("  F. grants before %s -> after the boundary %s%s" % (f.get("before"), f.get("after"), _err(f)))
print("  stale Player 1 prompts declined        : %s" % (state["declined_other"] or "none"))

if not state["wiring"] or any(r.get("error") for r in (h, b, cc, d, e, f)) or not f.get("done"):
    print("  INCONCLUSIVE - the run never got through the staging")
    raise SystemExit(2)

if not NEUTRALIZE:
    checks = (
        ("the three Stratagems are on main()'s registry, each holding main()'s collaborators",
         w.get("registered") == ["EreWeGoController", "MobMentalityController", "UnbridledCarnageController"]
         and w.get("mob_mentality") and w.get("unbridled_carnage") and w.get("ere_we_go")),
        ("the AI's own auto-play buys Mob Mentality for its straggler",
         h.get("covered") is True and h.get("visible") is True),
        ("...and the AI's Battle-shock test for it passes WITHOUT dice - by Mob Mentality, not Insane Bravery",
         h.get("rolled") is True and h.get("dice") == [] and h.get("shocked") is False
         and any("(Mob Mentality)" in line for line in h.get("by") or [])),
        ("Mob Mentality is DRAWN on main()'s panel for the mob of 20, and the sole candidate is paid for without a prompt",
         bool(b.get("drawn")) and b.get("pressed") is True and b.get("asked") is False and b.get("paid") == 1
         and b.get("covered") is True),
        ("...main()'s BattleShockController passes the battle-shocked unit's 08.03 test without dice",
         b.get("dice") == [] and b.get("shocked") is False and b.get("rolled") is True),
        ("'Ere We Go is DRAWN, paid, and the Advance roll carries +2",
         bool(cc.get("drawn")) and cc.get("paid") == 1 and cc.get("terms") == [(ewg.ERE_WE_GO_NAME, 2)]
         and cc.get("total_on_3") == 5),
        ("Unbridled Carnage is DRAWN for the engaged, charged mob and paid",
         d.get("eligible") is True and bool(d.get("drawn")) and d.get("paid") == 1),
        ("...main()'s FightController: the Choppa has +1 A and [SUSTAINED HITS 1] (Mob-handed Brutality)",
         (d.get("choppa") or (0, 0, 0))[1] == (d.get("choppa") or (0, 0, 0))[0] + 1
         and (d.get("choppa") or (0, 0, 0))[2] == 1),
        ("...and a charged Beast Snagga Boyz unit's weapon gains [LETHAL HITS] against the infantry target",
         d.get("bsb_lethal") == (False, True)),
        ("'Ardboyz: main()'s datacard prints 4+ and the save roll needs a 4",
         e.get("printed") == "5+" and e.get("card") == "4+" and e.get("threshold") == 4),
        ("main()'s phase boundary ends all three grants",
         f.get("before") == (True, True, True) and f.get("after") == (False, False, False)),
    )
else:
    checks = (
        ("none of the three is on the live registry", not w.get("registered")),
        ("the AI never buys Mob Mentality, and no roll is passed by it",
         not h.get("covered") and not any("(Mob Mentality)" in line for line in h.get("by") or [])),
        ("Mob Mentality is never drawn", not b.get("drawn")),
        ("'Ere We Go is never drawn", not cc.get("drawn")),
        ("Unbridled Carnage is never drawn", not d.get("drawn")),
        ("no Mob-handed Brutality: no Sustained Hits, no Lethal Hits",
         (d.get("choppa") or (0, 0, 1))[2] == 0 and d.get("bsb_lethal") == (False, False)),
        ("'Ardboyz does nothing: 5+ everywhere", e.get("card") == "5+" and e.get("threshold") == 5),
    )
failed = 0
for label, ok in checks:
    print("  %s  %s" % ("PASS" if ok else "FAIL", label))
    failed += 0 if ok else 1
raise SystemExit(1 if failed else 0)
