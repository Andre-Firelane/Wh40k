"""Runtime proof through the REAL main() loop that the 2026-09 Kill Rig's psychic
abilities are wired.

test_ork_kill_rig.py drives each ability through real controllers built by the
test and pins main.py by AST. What it cannot show is that MAIN'S objects, built by
MAIN'S constructors in MAIN'S order, are connected when the game runs - and that
main()'s own dice acknowledgement resolves the psychic roll. So this runs
selfplay.py's real main() loop with the ORKS AS PLAYER 1 and asks main()'s live
objects:

  A. THE WIRING. The live FightController holds a WarpathController on main()'s
     psychic roll; Beastscent listens on the live TransportController's
     on_disembark_started, on the same psychic roll and main()'s clock.
  B. BEASTSCENT through the live TransportController: in Player 1's Movement
     phase a Beast Snagga Boyz unit is selected to disembark from a Kill Rig (the
     call the panel's Disembark button makes), Player 1 is asked, the answer puts
     a D6 on the table, main()'s acknowledgement resolves it, the passenger's
     attacks get +1 to wound against a MONSTER in the live ShootingController, and
     the Kill Rig's spent psyker level refuses it Warpath this battle round.
  C. WARPATH through the live FightController: in Player 1's Fight phase a second,
     damaged Kill Rig is selected to fight, Player 1 is asked, the D6 comes up 1,
     main()'s acknowledgement battle-shocks the Kill Rig, and the live chain gives
     its melee weapons [LETHAL HITS] and [PSYCHIC] - which drops its own Damaged -1
     from the live Hit modifiers.
  D. THE BOUNDARIES through main()'s own advance_turn_phase(): the end of Player
     1's Fight phase ends Warpath (per phase) and Beastscent (the turn-end sweep).
  E. THE AI'S FIGHT GUARD on main()'s live objects: a Player 2 Kill Rig, engaged
     with Player 1's, is selected by ai/agent_driver._handle_fight(); its Warpath
     roll must still be the pending roll when the call returns (the AI must not
     throw its Hit roll over it), and main()'s acknowledgement resolves it.

STAGED, each named rather than quietly faked:
  * THE ORKS AS PLAYER 1 (config ships aeldari against necrons), Player 2 Necrons.
  * Three Kill Rigs and a Beast Snagga Boyz unit are BUILT: rig A (Player 1)
    carrying the Boyz, rig B (Player 1, 5 wounds left) touching rig C (Player 2), on
    the clearest ground away from every token and objective (the shipped list
    carries its Kill Rig elsewhere and rarely reaches a fight).
  * The phases and turn owners (Player 1 Movement, Player 1 Fight, Player 2 Fight),
    the Fight step's start (begun with the pile-in check bypassed - both rigs
    would otherwise owe a pile-in no harness answers), the psychic D6 faces (4 for
    Beastscent, 1 for Warpath - a 1 is the only face with an observable shock),
    Player 1's answers, the placement and fight cancelled after the reads, and
    one advance_turn_phase() call.
  * E calls _handle_fight() the way take_one_action() does, with a MockAgent.
  * Player 1 prompts this harness does not answer are declined after STALE_FRAMES.

--neutralize loads main.py through an import hook with the measured seams undone
(the psychic roll's acknowledgement, the Warpath hand-over, the Beastscent
listener, the Warpath per-phase reset, the Beastscent turn-end sweep). The files on
disk are not touched. The AI fight guard is A/B-probed by ab_ork_kill_rig.py; a
neutralized main() has no Warpath to guard.

Usage:  python verify_ork_kill_rig.py [map2] [frames]
        python verify_ork_kill_rig.py map2 --neutralize
"""

import importlib.abc
import importlib.util
import math
import os
import runpy
import sys

import pygame

from game import beastscent, config, unstable_energies, warpath
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import build_squad
from game.factions.orks import BEAST_SNAGGA_BOYZ, KILL_RIG
from game.objectives import is_within_range_of_objective
from game.psychic_roll import PsychicRollController
from game.turn import PHASES, PHASE_FIGHT, PHASE_MOVEMENT, TurnTracker
from game.warpath import WarpathController
from game.weapons import MELEE

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

HUMAN = "Player 1"
FOE = "Player 2"
STAGE_AT = 150
STALE_FRAMES = 30
WAIT = 400
FIXED = {"Beastscent": 4, "Warpath": 1}

NEUTRALIZE_EDITS = (
    ("        psychic_roll_controller.on_dice_acknowledged()\n", "        pass\n"),
    ("        warpath=WarpathController(\n"
     "            psychic_roll_controller, decision_manager=decision_manager, game_log=game_log,\n"
     "            auto_players=ai_players,\n"
     "            verdict=lambda squad: warpath_verdict(state, squad)),\n",
     "        warpath=None,\n"),
    ("    transport_controller.on_disembark_started.append(beastscent_controller.on_disembark_started)\n",
     "    pass\n"),
    ("        warpath.reset_phase({t.squad for t in state.tokens if t.squad is not None})\n", "        pass\n"),
    ("                squad.beastscent_active = False\n", "                pass\n"),
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
         "e": None, "stale": None, "stale_since": 0, "declined_other": [], "prompts": [], "rolls": []}


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
    if "Warpath" in (prompt or "") or "Beastscent" in (prompt or ""):
        state["prompts"].append({"player": player, "frame": state["frames"], "prompt": prompt,
                                 "labels": [o[0] for o in options]})
    return out


DecisionManager.request = request

_real_roll = DiceManager.roll


def roll(self, *args, **kwargs):
    out = _real_roll(self, *args, **kwargs)
    label = kwargs.get("label", "") or ""
    if label.startswith("Psychic roll: ") and self.pending_values:
        for ability, face in FIXED.items():
            if label.startswith("Psychic roll: %s" % ability):
                self.pending_values[0] = face
                self.last_values = list(self.pending_values)
    state["rolls"].append((state["frames"], label))
    return out


DiceManager.roll = roll


def _alive(squad):
    return any(not m.is_dead() for m in squad.models)


def _quiet(L):
    return not L["dice_manager"].is_pending and not L["decision_manager"].is_pending


def _decline_stale_human_prompt(decisions):
    if decisions is None or not decisions.is_pending or decisions.player != HUMAN:
        state["stale"] = None
        return
    prompt = decisions.prompt or ""
    if "Warpath" in prompt or "Beastscent" in prompt:
        return
    key = (id(decisions._queue[0]), prompt)
    if state["stale"] != key:
        state["stale"], state["stale_since"] = key, state["frames"]
        return
    if state["frames"] - state["stale_since"] >= STALE_FRAMES:
        state["declined_other"].append(prompt[:60])
        decisions.choose(len(decisions.options) - 1)
        state["stale"] = None


def _set_phase(phase, owner):
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


def _wiring(L):
    fc = L["fight_controller"]
    wp = getattr(fc, "warpath", None)
    tc = L["transport_controller"]
    bs = L.get("beastscent_controller")
    listening = bs is not None and bs.on_disembark_started in tc.on_disembark_started
    return {
        "warpath": isinstance(wp, WarpathController),
        "warpath_roll": isinstance(getattr(wp, "psychic_roll", None), PsychicRollController)
        and wp.psychic_roll is L.get("psychic_roll_controller"),
        "warpath_ai": callable(getattr(wp, "verdict", None)),
        "beastscent": listening,
        "beastscent_roll": listening and bs.psychic_roll is L.get("psychic_roll_controller")
        and bs.turn_tracker is L["turn_tracker"],
    }


def _setup(L):
    st, setup = L["state"], L["setup_controller"]
    rig_a = build_squad(KILL_RIG, HUMAN, name="1 Kill Rig (staged A)")
    rig_b = build_squad(KILL_RIG, HUMAN, name="1 Kill Rig (staged B)")
    rig_c = build_squad(KILL_RIG, FOE, name="2 Kill Rig (staged C)")
    boyz = build_squad(BEAST_SNAGGA_BOYZ, HUMAN, name="1 Beast Snagga Boyz (staged)")
    ta, tb, tcx = rig_a.models[0], rig_b.models[0], rig_c.models[0]
    r = tb.radius_in
    others = [t for t in st.tokens if not t.is_dead()]
    best = None
    counts = [0, 0]
    for gx in range(6, int(setup.board_width_in) - 5):
        for gy in range(6, int(setup.board_height_in) - 5):
          for ux, uy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            # B and C touching along (ux, uy), A a clear hull-and-3" to the side.
            spots = {"b": (gx - ux * (r + 0.25), gy - uy * (r + 0.25)),
                     "c": (gx + ux * (r + 0.25), gy + uy * (r + 0.25)),
                     "a": (gx - uy * (2 * r + 3.0), gy + ux * (2 * r + 3.0))}
            if not all(setup.position_valid(tb, x, y, squad=rig_b) for x, y in spots.values()):
                continue
            counts[0] += 1
            # Rig C off every objective: the AI's Warpath verdict refuses on one (a
            # 1 would drop the Kill Rig's OC to 0), and E needs it to roll.
            tcx.x_in, tcx.y_in = spots["c"]
            if is_within_range_of_objective(rig_c, st.objectives):
                continue
            counts[1] += 1
            score = min((math.hypot(x - t.x_in, y - t.y_in) - t.radius_in - r
                         for x, y in spots.values() for t in others), default=99.0)
            if best is None or score > best[0]:
                best = (score, spots)
    # Clear of every other token by more than Engagement Range (1"), so the only
    # fight on that ground is the staged one and the AI has one unit to select.
    if best is None or best[0] <= 1.05:
        state["setup"] = {"error": "no clear ground for the staged Kill Rigs (best %.2f\", %d placeable, %d off objectives, board %sx%s, %d tokens)"
                                   % (best[0] if best else -1, counts[0], counts[1], setup.board_width_in, setup.board_height_in, len(others))}
        return
    for token, key in ((ta, "a"), (tb, "b"), (tcx, "c")):
        token.x_in, token.y_in = best[1][key]
        st.add_token(token)
    tb.current_wounds = 5
    boyz.embarked_in = ta
    st.embarked_squads.append(boyz)
    state["setup"] = {"a": rig_a, "b": rig_b, "c": rig_c, "boyz": boyz, "clearance": best[0]}


def _stage_b(L):
    s = state["setup"]
    _set_phase(PHASE_MOVEMENT, HUMAN)
    prompts_before = len(state["prompts"])
    tc = L["transport_controller"]
    tc.start_disembark(s["boyz"])
    asked = [p for p in state["prompts"][prompts_before:] if "Beastscent" in p["prompt"]]
    chosen = _answer(L["decision_manager"], "Make the psychic roll") if asked else None
    state["b"] = {"frame": state["frames"], "asked": asked, "chosen": chosen,
                  "opened": tc.is_disembarking(s["boyz"]), "pending": L["dice_manager"].is_pending}


def _watch_b(L):
    b, s = state["b"], state["setup"]
    ctrl = L.get("psychic_roll_controller")
    resolved = not L["dice_manager"].is_pending and (ctrl is None or not ctrl.is_busy)
    if not (resolved or state["frames"] - b["frame"] >= WAIT):
        return
    b["resolved"] = resolved
    b["active"] = beastscent.is_active(s["boyz"])
    b["spent"] = unstable_energies.spent_this_round(s["a"], state["tracker"].battle_round)
    b["shocked"] = bool(s["a"].battle_shocked)
    sc = L["shooting_controller"]
    saved = sc.active_squad
    sc.active_squad = s["boyz"]
    try:
        b["wound_mods"] = [(m.amount, m.source) for m in sc._wound_modifiers(s["c"])
                           if m.source == beastscent.BEASTSCENT_NAME]
    finally:
        sc.active_squad = saved
    wp = getattr(L["fight_controller"], "warpath", None)
    b["warpath_a"] = wp.can_use(s["a"]) if wp is not None else None
    b["warpath_b"] = wp.can_use(s["b"]) if wp is not None else None
    if L["transport_controller"].is_disembarking(s["boyz"]):
        L["transport_controller"].cancel_disembark()
    b["done"] = True


def _stage_c(L):
    s = state["setup"]
    _set_phase(PHASE_FIGHT, HUMAN)
    fc = L["fight_controller"]
    fc.reset_fight_phase()
    saved, fc.pile_in_controller = fc.pile_in_controller, None
    try:
        fc.begin_fight_step()
    finally:
        fc.pile_in_controller = saved
    fc.whose_turn = HUMAN
    prompts_before = len(state["prompts"])
    selectable = fc.can_select_to_fight(s["b"])
    fc.select_to_fight(s["b"])
    asked = [p for p in state["prompts"][prompts_before:] if "Warpath" in p["prompt"]]
    chosen = _answer(L["decision_manager"], "Make the psychic roll") if asked else None
    state["c"] = {"frame": state["frames"], "selectable": selectable, "asked": asked, "chosen": chosen}


def _watch_c(L):
    c, s = state["c"], state["setup"]
    ctrl = L.get("psychic_roll_controller")
    resolved = not L["dice_manager"].is_pending and (ctrl is None or not ctrl.is_busy)
    if not (resolved or state["frames"] - c["frame"] >= WAIT):
        return
    fc = L["fight_controller"]
    model = s["b"].models[0]
    saw = next(w for w in model.weapons if w.name == "Saw Blades")
    adjusted = fc._adjusted_weapon([(model, saw)], s["c"])
    c["resolved"] = resolved
    c["shocked"] = bool(s["b"].battle_shocked)
    c["active"] = warpath.is_active(s["b"])
    c["granted"] = (bool(adjusted.lethal_hits), bool(adjusted.psychic))
    c["mods_plain"] = [(m.amount, m.source) for m in fc._hit_modifiers(model, s["c"]) if m.amount > 0]
    c["mods_live"] = [(m.amount, m.source) for m in fc._hit_modifiers(model, s["c"], adjusted) if m.amount > 0]
    try:
        fc.cancel()
    except Exception:
        pass
    # Beastscent and Warpath must both still be up for D to see them end.
    c["before_boundary"] = (beastscent.is_active(s["boyz"]), warpath.is_active(s["b"]))
    c["done"] = True


def _stage_d(L):
    s = state["setup"]
    staged = []
    if not beastscent.is_active(s["boyz"]):
        s["boyz"].beastscent_active = True
        staged.append("beastscent_active")
    if not warpath.is_active(s["b"]):
        s["b"].warpath_active = True
        staged.append("warpath_active")
    _set_phase(PHASE_FIGHT, HUMAN)
    tracker = state["tracker"]
    before = (tracker.battle_round, tracker.turn_index_in_round, tracker.phase)
    try:
        L["advance_turn_phase"]()
    except Exception as exc:
        state["d"] = {"error": "advance_turn_phase raised %r" % exc}
        return
    state["d"] = {"staged": staged, "owner_after": state["tracker"].turn_owner,
                  "clock": (before, (tracker.battle_round, tracker.turn_index_in_round, tracker.phase)),
                  "warpath_after": warpath.is_active(s["b"]), "beastscent_after": beastscent.is_active(s["boyz"]),
                  "done": True}


def _stage_e(L):
    from ai import agent_driver
    from ai.mock_agent import MockAgent
    s = state["setup"]
    s["c"].battle_shocked = False
    _set_phase(PHASE_FIGHT, FOE)
    fc = L["fight_controller"]
    fc.reset_fight_phase()
    saved, fc.pile_in_controller = fc.pile_in_controller, None
    try:
        fc.begin_fight_step()
    finally:
        fc.pile_in_controller = saved
    fc.whose_turn = FOE
    rolls_before = len(state["rolls"])
    eligible = [q.name for q in fc.eligible_to_select_now()]
    try:
        agent_driver._handle_fight(MockAgent(), agent_driver.AIMemory(), FOE, L["state"].tokens, fc,
                                   L["pile_in_controller"], L["movement_controller"], None)
    except Exception as exc:
        state["e"] = {"error": "_handle_fight raised %r" % exc}
        return
    labels = [label for _f, label in state["rolls"][rolls_before:]]
    state["e"] = {"frame": state["frames"], "eligible": eligible,
                  "selected": getattr(fc.fighting_squad, "name", None), "labels_in_call": labels,
                  "pending": L["dice_manager"].is_pending, "pending_label": L["dice_manager"].label,
                  "rolls_before": rolls_before}


def _watch_e(L):
    e = state["e"]
    ctrl = L.get("psychic_roll_controller")
    if (ctrl is not None and not ctrl.is_busy) or state["frames"] - e["frame"] >= WAIT:
        e["done"] = True
        e["resolved"] = ctrl is not None and not ctrl.is_busy
        e["shocked"] = bool(state["setup"]["c"].battle_shocked)
        e["active"] = warpath.is_active(state["setup"]["c"])


def flip(*args, **kwargs):
    state["frames"] += 1
    tracker = state["tracker"]
    if tracker is not None and getattr(tracker, "started", False):
        L = _main_locals()
        if L is not None and "fight_controller" in L and "transport_controller" in L:
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
            elif not state["c"].get("done"):
                _watch_c(L)
            elif state["d"] is None:
                if _quiet(L):
                    _stage_d(L)
            elif state["d"].get("error"):
                raise SystemExit(0)
            elif state["e"] is None:
                if _quiet(L):
                    _stage_e(L)
            elif not state["e"].get("done") and not state["e"].get("error"):
                _watch_e(L)
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
e = state["e"] or {}
print()
print("--- Ork Kill Rig, live" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
print("  frames                                 : %d" % state["frames"])
print("  A. Warpath on the FightController      : %s (main()'s psychic roll: %s, AI verdict: %s)" % (
    w.get("warpath"), w.get("warpath_roll"), w.get("warpath_ai")))
print("     Beastscent on on_disembark_started   : %s (main()'s psychic roll and clock: %s)" % (
    w.get("beastscent"), w.get("beastscent_roll")))
if s.get("error"):
    print("  SETUP ERROR " + s["error"])
else:
    print("  staged three Kill Rigs %.1f\" clear of every other token" % (s.get("clearance") or -1))
print("  B. Beastscent prompts                  : %s; answered %s; placement open %s" % (
    [(p["player"], p["labels"]) for p in b.get("asked") or []], b.get("chosen"), b.get("opened")))
print("     resolved by main()'s ack / grant / level spent / rig shocked: %s / %s / %s / %s" % (
    b.get("resolved"), b.get("active"), b.get("spent"), b.get("shocked")))
print("     live shooting wound mods vs the MONSTER: %s" % (b.get("wound_mods"),))
print("     Warpath usable: rig A (spent) %s, rig B %s" % (b.get("warpath_a"), b.get("warpath_b")))
print("  C. Warpath prompts (selectable %s)       : %s; answered %s" % (
    cc.get("selectable"), [(p["player"], p["labels"]) for p in cc.get("asked") or []], cc.get("chosen")))
print("     resolved by main()'s ack / shocked on the 1 / grant: %s / %s / %s" % (
    cc.get("resolved"), cc.get("shocked"), cc.get("active")))
print("     live chain [LETHAL HITS], [PSYCHIC]  : %s" % (cc.get("granted"),))
print("     worsening hit mods without / with the weapon: %s / %s" % (cc.get("mods_plain"), cc.get("mods_live")))
print("  D. after advance_turn_phase() (staged by hand: %s): owner %s, clock %s, Warpath %s, Beastscent %s%s" % (
    d.get("staged"), d.get("owner_after"), d.get("clock"), d.get("warpath_after"), d.get("beastscent_after"),
    (" ERROR " + d["error"]) if d.get("error") else ""))
print("  E. AI selects %s (eligible %s)%s" % (e.get("selected"), e.get("eligible"),
                                          (" ERROR " + e["error"]) if e.get("error") else ""))
print("     rolls thrown inside _handle_fight()  : %s" % (e.get("labels_in_call"),))
print("     pending when it returned             : %s (%s)" % (e.get("pending"), e.get("pending_label")))
print("     resolved by main()'s ack / shocked / grant: %s / %s / %s" % (
    e.get("resolved"), e.get("shocked"), e.get("active")))
print("  stale Player 1 prompts declined        : %s" % (state["declined_other"] or "none"))

if not state["wiring"] or s.get("error") or d.get("error") or e.get("error") or not e.get("done"):
    print("  INCONCLUSIVE - the run never got through the staging")
    raise SystemExit(2)

def _crossed_a_turn(d):
    """The forced advance really ended a turn: a new (round, turn) slot, in its
    Command phase. NOT "Player 2 owns it" - the staged Fight phase is Player 1's
    by fiat, and when the real slot was Player 2's second turn of the round, the
    next turn is the new round's first, which can be Player 1's again."""
    clock = d.get("clock")
    if not clock:
        return False
    (round_before, index_before, _phase_before), (round_after, index_after, phase_after) = clock
    return (round_after, index_after) != (round_before, index_before) and phase_after == "Command"


if not NEUTRALIZE:
    checks = (
        ("the live FightController holds Warpath on main()'s psychic roll, with the AI's verdict",
         w.get("warpath") and w.get("warpath_roll") and w.get("warpath_ai")),
        ("Beastscent listens on the live TransportController, on main()'s psychic roll and clock",
         w.get("beastscent") and w.get("beastscent_roll")),
        ("a passenger selected to disembark asks Player 1 about Beastscent",
         any(p["player"] == HUMAN for p in b.get("asked") or []) and b.get("chosen") is not None),
        ("...the D6 is resolved by main()'s acknowledgement", b.get("resolved") is True),
        ("...the passenger has the grant, the Kill Rig spent its level and is not shocked on a 4",
         b.get("active") is True and b.get("spent") == 1 and b.get("shocked") is False),
        ("...+1 to wound against the MONSTER in the live ShootingController",
         b.get("wound_mods") == [(-1, "Beastscent")]),
        ("...and the spent level refuses rig A Warpath while rig B may use it",
         b.get("warpath_a") is False and b.get("warpath_b") is True),
        ("a Kill Rig selected to fight asks Player 1 about Warpath",
         cc.get("selectable") is True and any(p["player"] == HUMAN for p in cc.get("asked") or [])),
        ("...main()'s acknowledgement battle-shocks it on the 1",
         cc.get("resolved") is True and cc.get("shocked") is True),
        ("...the live chain gives its melee weapons [LETHAL HITS] and [PSYCHIC]",
         cc.get("active") is True and cc.get("granted") == (True, True)),
        ("...and [PSYCHIC] drops its own Damaged -1 from the live Hit modifiers",
         bool(cc.get("mods_plain")) and cc.get("mods_live") == []),
        ("main()'s turn boundary ends Warpath and Beastscent",
         not d.get("staged") and _crossed_a_turn(d)
         and d.get("warpath_after") is False and d.get("beastscent_after") is False),
        ("the AI's _handle_fight() selects its Kill Rig and leaves the psychic roll pending",
         e.get("selected") == getattr(s.get("c"), "name", None)
         and [x for x in e.get("labels_in_call") or [] if x] and all(
             x.startswith("Psychic roll") for x in e.get("labels_in_call") or [] if x)
         and "Psychic roll: Warpath" in (e.get("pending_label") or "")),
        ("...which main()'s acknowledgement resolves (shocked on the 1, grant up)",
         e.get("resolved") is True and e.get("shocked") is True and e.get("active") is True),
    )
else:
    checks = (
        ("no Warpath on the live FightController", not w.get("warpath")),
        ("Beastscent does not listen", not w.get("beastscent")),
        ("no Beastscent prompt", not b.get("asked")),
        ("no Warpath prompt", not cc.get("asked")),
        ("the hand-staged grants survive the turn boundary",
         _crossed_a_turn(d) and d.get("warpath_after") is True and d.get("beastscent_after") is True),
        ("the AI makes no psychic roll", not any((x or "").startswith("Psychic roll")
                                                for x in e.get("labels_in_call") or [])),
    )
failed = 0
for label, ok in checks:
    print("  %s  %s" % ("PASS" if ok else "FAIL", label))
    failed += 0 if ok else 1
raise SystemExit(1 if failed else 0)
