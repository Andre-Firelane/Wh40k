"""Runtime proof through the REAL main() loop that the Orks army rules are wired.

test_ork_army_rules.py drives the controllers directly and pins main.py by AST.
What neither can show is that MAIN'S objects, built in MAIN'S order, do it in a
running game. So this runs selfplay.py's real main() loop with the ORKS ON BOTH
SIDES - Player 1 the human, Player 2 the AI - and asks what happened:

  A. WAR CRY IS OFFERED IN BOTH COMMAND PHASES. main() asks the human at the
     start of the battle's first Command phase (begin_battle) and at the start
     of every later one - "THE Command phase", so the opponent's too. The
     first prompt is DECLINED, which must bring the question back at the next
     Command phase; the second is USED, after which it must never come again.
  B. THE AI ANSWERS WITHOUT A PROMPT AND WITHOUT THE MODEL. Player 2's War Cry
     goes through ai/agent_driver.py's war_cry_verdict(), injected by main():
     no War Cry prompt is ever raised to Player 2, and MockAgent is never shown
     a War Cry or an Advance re-roll option (0 LLM decisions about them).
  C. WHAT THE USE BUYS, read off main()'s live units the moment it lands: every
     Player 1 unit with the ability riled up (Reserves included); a 5+
     invulnerable save; [ASSAULT] at the Advance-shooting gate and the Assault
     shooting type offered after an Advance; an Advance that no longer stops a
     charge - each measured against the same unit with the flag off, so a
     reading that is true anyway cannot pass. And at every later phase change,
     main()'s own refresh keeps the army riled up exactly until its deadline.
  D. THE ADVANCE RE-ROLL, both halves: a human's Advance roll carries a
     "Re-roll Advance" button in main()'s live RollChoiceView, and an AI unit's
     Advance of 1 is thrown again by main()'s own _acknowledge_pending_roll()
     without a prompt.

STAGED, each named rather than quietly faked:
  * THE ORKS ON BOTH SIDES (config.PLAYER1_ARMY / PLAYER2_ARMY) - config ships
    aeldari against necrons, and a question about the Ork army rule would
    otherwise measure armies that do not have it and report a truthful-looking
    zero.
  * THE HUMAN'S ANSWERS. This harness answers no human prompt outside the
    pre-game, so a War Cry prompt would stall the run: it is answered the moment
    it is raised (Decline, then Use) through DecisionManager.choose(), the call
    the decision overlay's click makes.
  * D's two Advance rolls, thrown once in a quiet frame of Player 1's turn
    through main()'s live DiceManager - a MockAgent run does not reliably
    Advance a given unit - and cleared again. Everything after the throw is
    main()'s.

--neutralize loads main.py through an import hook with the measured seams undone
(both War Cry offers, the start-of-phase refresh, the Advance re-roll offer and
its dice-panel provider). The file on disk is not touched. It must show the
pre-wiring world: no prompt, no use, nobody riled up, no button, no re-roll.

Usage:  python verify_ork_army_rules.py [map2] [frames]
        python verify_ork_army_rules.py map2 --neutralize
"""

import importlib.abc
import importlib.util
import os
import runpy
import sys

import pygame

import ai.agent_driver as agent_driver
from ai.mock_agent import MockAgent
from game import (coldstar, config, invulnerable_save, move_exceptions, riled_up,
                  shooting)
from game.decision import DecisionManager
from game.dice import ADVANCE_ROLL
from game.turn import PHASE_COMMAND, TurnTracker
from game.waaagh import WaaaghAdvanceRerollController
from game.war_cry import WarCryController
from game.weapons import RANGED

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

HUMAN = "Player 1"
AI = "Player 2"
STAGE_AT = 200          # frames before D is staged (a quiet frame of Player 1's turn after that)
AFTER_USE_KEYS = 5      # phase changes to watch after the use before stopping early

#: (anchor, replacement) applied to main.py's SOURCE in memory, IN ORDER, for
#: --neutralize. Each anchor must be unique at the moment it is applied.
NEUTRALIZE_EDITS = (
    ("        riled_up.refresh(state.all_squads(), turn_tracker)\n"
     "        if not resuming:\n"
     "            war_cry_controller.offer_at_start_of_command_phase(turn_tracker)\n",
     "        pass\n"),
    ("        # anything this phase can read it, and before War Cry's offer below.\n"
     "        riled_up.refresh(state.all_squads(), turn_tracker)\n",
     "        pass\n"),
    ("            war_cry_controller.offer_at_start_of_command_phase(turn_tracker)\n",
     "            pass\n"),
    ("            waaagh_advance_reroll_controller.maybe_offer_advance_reroll(_adv_squad)\n",
     "            pass\n"),
    ("        lambda: waaagh_advance_reroll_controller.pending_roll_choice(movement_controller.selected_squad),\n",
     "        lambda: None,\n"),
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

state = {"frames": 0, "tracker": None, "prompts": [], "offers": [], "uses": [], "verdicts": [],
         "llm_calls": 0, "llm_offered": 0, "adv_offers": [], "effects": None,
         "phase_keys": [], "watched": [], "staged": None, "stage_error": None,
         "why_not": {}, "declined_other": [], "stale": None, "stale_since": 0}

STALE_FRAMES = 30


# ------------------------------------------------------------------- helpers

def _clock():
    tracker = state["tracker"]
    if tracker is None:
        return None, None, None
    return tracker.battle_round, tracker.turn_owner, tracker.phase


def _main_locals():
    """main()'s live locals, read FRESH each time: a cached f_locals snapshot
    would miss names main() binds later."""
    frame = sys._getframe(1)
    while frame is not None and frame.f_code.co_name != "main":
        frame = frame.f_back
    return frame.f_locals if frame is not None else None


def _ork_units(game_state, owner):
    return [s for s in game_state.all_squads() if s.owner == owner and riled_up.has_ability(s)]


def _on_board(game_state, squad):
    return any(m in game_state.tokens for m in squad.models)


# ----------------------------------------------------------------- the spies

_real_tracker_init = TurnTracker.__init__


def tracker_init(self, *args, **kwargs):
    _real_tracker_init(self, *args, **kwargs)
    state["tracker"] = self


TurnTracker.__init__ = tracker_init

_real_request = DecisionManager.request


def request(self, player, prompt, options, *args, **kwargs):
    out = _real_request(self, player, prompt, options, *args, **kwargs)
    text = prompt or ""
    if "War Cry" in text or "re-roll it?" in text:
        battle_round, owner, phase = _clock()
        entry = {"player": player, "war_cry": "War Cry" in text, "round": battle_round,
                 "owner": owner, "phase": phase, "frame": state["frames"], "answered": None}
        state["prompts"].append(entry)
        if entry["war_cry"] and player == HUMAN:
            _answer(self, entry)
    return out


DecisionManager.request = request

_real_offer = WarCryController.offer_at_start_of_command_phase


def offer(self, turn_tracker=None):
    battle_round, owner, phase = _clock()
    opened = _real_offer(self, turn_tracker)
    state["offers"].append({"round": battle_round, "owner": owner, "phase": phase, "opened": opened})
    return opened


WarCryController.offer_at_start_of_command_phase = offer

_real_use = WarCryController.use


def use(self, player, turn_tracker=None):
    took = _real_use(self, player, turn_tracker)
    battle_round, owner, phase = _clock()
    state["uses"].append({"player": player, "took": took, "round": battle_round, "owner": owner,
                          "phase": phase, "frame": state["frames"]})
    return took


WarCryController.use = use

# main.py binds war_cry_verdict with `from ai.agent_driver import ...`, so the
# spy has to be in place BEFORE main is imported - selfplay imports it below.
_real_verdict = agent_driver.war_cry_verdict


def war_cry_verdict(player, turn_tracker, all_tokens):
    answer = _real_verdict(player, turn_tracker, all_tokens)
    state["verdicts"].append((player, getattr(turn_tracker, "turn_owner", None), bool(answer)))
    return answer


agent_driver.war_cry_verdict = war_cry_verdict

_real_decide = MockAgent.decide


def decide(self, observation):
    state["llm_calls"] += 1
    descriptions = " | ".join(str(a.get("description", "")) for a in observation.get("available_actions", []) or ()
                              if isinstance(a, dict))
    if "Use War Cry" in descriptions or "Re-roll the Advance" in descriptions:
        state["llm_offered"] += 1
    return _real_decide(self, observation)


MockAgent.decide = decide

_real_adv = WaaaghAdvanceRerollController.maybe_offer_advance_reroll


def adv_offer(self, squad):
    dice = self.dice_manager
    before = list(dice.pending_values) if dice is not None and dice.pending_values else None
    out = _real_adv(self, squad)
    state["adv_offers"].append({"owner": getattr(squad, "owner", None), "before": before, "returned": out,
                                "rerolled": bool(dice is not None and 0 in dice.already_rerolled)})
    return out


WaaaghAdvanceRerollController.maybe_offer_advance_reroll = adv_offer


# ------------------------------------------------------------ the human side

def _answer(decision_manager, entry):
    """Decline the first War Cry prompt, Use the second. Only ever the FRONT
    prompt, so no other question is answered by mistake."""
    if (not decision_manager.is_pending or decision_manager.player != HUMAN
            or "War Cry" not in (decision_manager.prompt or "")):
        return False
    declined_before = any(e["answered"] == "decline" for e in state["prompts"])
    entry["answered"] = "use" if declined_before else "decline"
    L = _main_locals()
    decision_manager.choose(0 if declined_before else 1)
    if declined_before:
        _measure_effects(L)
    return True


def _measure_effects(L):
    r = state["effects"] = {}
    if L is None:
        r["error"] = "main()'s frame not found"
        return
    game_state, mover = L["state"], L["movement_controller"]
    mine = _ork_units(game_state, HUMAN)
    r["units"] = len(mine)
    r["riled"] = sum(1 for s in mine if riled_up.is_riled_up(s))
    r["reserves"] = sum(1 for s in mine if s in game_state.reserves)
    r["reserves_riled"] = sum(1 for s in mine if s in game_state.reserves and riled_up.is_riled_up(s))
    r["deadlines"] = sorted({s.riled_up_expires_turn for s in mine if s.riled_up_expires_turn is not None})
    unit = gun = None
    for squad in sorted(mine, key=lambda s: s.name):
        ranged = [w for m in squad.models for w in m.weapons if w.weapon_type == RANGED]
        if _on_board(game_state, squad) and ranged and not any(w.assault for w in ranged):
            unit, gun = squad, ranged[0]
            break
    r["unit"], r["gun"] = getattr(unit, "name", None), getattr(gun, "name", None)
    if unit is None:
        return
    real_flag = unit.riled_up
    added = unit not in mover.advanced_squad_ids
    mover.advanced_squad_ids.add(unit)
    try:
        for flag, key in ((False, "plain"), (True, "riled_effects")):
            unit.riled_up = flag
            r[key] = {
                "invuln": invulnerable_save.effective_invulnerable_save(unit.models[0]),
                "gate_assault": coldstar.weapon_has_assault(gun, unit),
                "types_after_advance": list(shooting.available_shooting_types(unit, game_state.tokens, mover)),
                "charge_after_advance": move_exceptions.may_charge_after_advancing(unit),
            }
    finally:
        unit.riled_up = real_flag
        if added:
            mover.advanced_squad_ids.discard(unit)


# ------------------------------------------------------------- per frame

def _watch(L, tracker):
    key = (tracker.battle_round, tracker.turn_owner, tracker.phase)
    if state["phase_keys"] and state["phase_keys"][-1] == key:
        return
    state["phase_keys"].append(key)
    mine = _ork_units(L["state"], HUMAN)
    state["watched"].append({
        "key": key, "serial": riled_up.turn_serial(tracker), "units": len(mine),
        "riled": sum(1 for s in mine if riled_up.is_riled_up(s)),
        "after_use": any(u["player"] == HUMAN and u["took"] for u in state["uses"]),
    })


def _stage_rerolls(L, tracker):
    if state["staged"] is not None or state["frames"] < STAGE_AT:
        return
    dice, decisions, mover = L["dice_manager"], L["decision_manager"], L["movement_controller"]
    setup = L.get("setup_controller")
    # WHY a frame was not quiet, counted rather than guessed.
    why = ("dice pending" if dice.is_pending
           else "decision pending for %s: %s" % (decisions.player, (decisions.prompt or "")[:60])
           if decisions.is_pending
           else "placement open" if setup is not None and getattr(setup, "state", None) == "placing"
           else "move open (%s)" % mover.move_mode if getattr(mover, "move_mode", None) is not None
           else None)
    if why is not None:
        state["why_not"][why] = state["why_not"].get(why, 0) + 1
        return
    game_state = L["state"]

    def first_on_board(owner):
        return next((s for s in sorted(_ork_units(game_state, owner), key=lambda s: s.name)
                     if _on_board(game_state, s)), None)

    human_unit, ai_unit = first_on_board(HUMAN), first_on_board(AI)
    r = state["staged"] = {"frame": state["frames"], "human_unit": getattr(human_unit, "name", None),
                           "ai_unit": getattr(ai_unit, "name", None)}
    if human_unit is None or ai_unit is None:
        state["stage_error"] = "no Ork unit on the board for one side"
        return
    saved = mover.selected_squad
    view = L["roll_choice_view"]
    try:
        # D1. A human's Advance roll: the button main()'s live view offers.
        mover.selected_squad = human_unit
        dice.roll(1, label="Advance", roll_kind=ADVANCE_ROLL, rolled_for=human_unit)
        view.invalidate()
        choice = view.pending(dice, L["human_players"])
        r["human_labels"] = [o.label for o in choice.options] if choice is not None else []
        dice.acknowledge()
        view.invalidate()
        # D2. An AI unit's Advance of 1, through main()'s own acknowledgement.
        mover.selected_squad = ai_unit
        dice.roll(1, label="Advance", roll_kind=ADVANCE_ROLL, rolled_for=ai_unit)
        dice.pending_values[0] = 1
        prompts_before, offers_before = len(state["prompts"]), len(state["adv_offers"])
        r["ai_mode_on"] = AI in L["ai_players"]
        r["ack_returned"] = L["_acknowledge_pending_roll"]()
        r["ai_rerolled"] = 0 in dice.already_rerolled
        r["ai_offer_calls"] = len(state["adv_offers"]) - offers_before
        r["ai_prompts"] = len(state["prompts"]) - prompts_before
        if decisions.is_pending and "re-roll it?" in (decisions.prompt or ""):
            decisions.choose(len(decisions.options) - 1)
        if dice.is_pending:
            dice.acknowledge()
    except Exception as exc:              # a crash is a finding, reported
        state["stage_error"] = "%s: %s" % (type(exc).__name__, exc)
    finally:
        mover.selected_squad = saved


def _decline_stale_human_prompt(decisions):
    """This harness answers no human prompt outside the pre-game, and an Ork
    Player 1 is asked things an Aeldari one never is. One left open blocks every
    later frame. A Player 1 prompt that is NOT War Cry and has stood for
    STALE_FRAMES frames gets its LAST option (Decline or Skip on every such
    prompt) and is named in the report - staged, not hidden."""
    if decisions is None or not decisions.is_pending or decisions.player != HUMAN:
        state["stale"] = None
        return
    prompt = decisions.prompt or ""
    if "War Cry" in prompt:
        return
    key = (id(decisions._queue[0]), prompt)
    if state["stale"] != key:
        state["stale"], state["stale_since"] = key, state["frames"]
        return
    if state["frames"] - state["stale_since"] >= STALE_FRAMES:
        state["declined_other"].append(prompt[:70])
        decisions.choose(len(decisions.options) - 1)
        state["stale"] = None


_real_flip = pygame.display.flip


def flip(*args, **kwargs):
    state["frames"] += 1
    tracker = state["tracker"]
    if tracker is not None and getattr(tracker, "started", False):
        L = _main_locals()
        if L is not None and "roll_choice_view" in L and "_acknowledge_pending_roll" in L:
            decisions = L.get("decision_manager")
            waiting = [e for e in state["prompts"]
                       if e["war_cry"] and e["player"] == HUMAN and e["answered"] is None]
            if waiting and decisions is not None:
                _answer(decisions, waiting[-1])
            _decline_stale_human_prompt(decisions)
            _watch(L, tracker)
            _stage_rerolls(L, tracker)
            after = [w for w in state["watched"] if w["after_use"]]
            if not NEUTRALIZE and state["staged"] is not None and len(after) >= AFTER_USE_KEYS:
                raise SystemExit(0)
    return _real_flip(*args, **kwargs)


pygame.display.flip = flip

_argv = sys.argv[1:] or ["map2", "4000"]
sys.argv = ["selfplay.py"] + _argv
config.PLAYER1_ARMY = "orks"
config.PLAYER2_ARMY = "orks"
config.ARMY_SELECT = False

try:
    runpy.run_module("selfplay", run_name="__main__")
except SystemExit:
    pass

# ---------------------------------------------------------------- the report

p1 = [e for e in state["prompts"] if e["war_cry"] and e["player"] == HUMAN]
p2 = [e for e in state["prompts"] if e["war_cry"] and e["player"] == AI]
owners = sorted({e["owner"] for e in p1 if e["owner"]})
use_index = next((i for i, e in enumerate(p1) if e["answered"] == "use"), None)
again = p1[use_index + 1:] if use_index is not None else []
human_uses = [u for u in state["uses"] if u["player"] == HUMAN and u["took"]]
ai_verdicts = [v for v in state["verdicts"] if v[0] == AI]
eff = state["effects"] or {}
deadline = (eff.get("deadlines") or [None])[-1]
after = [w for w in state["watched"] if w["after_use"]]
violations = [w for w in after if deadline is not None
              and (w["riled"] == w["units"] and w["units"] > 0) != (w["serial"] < deadline)]
staged = state["staged"] or {}
max_riled = max((w["riled"] for w in state["watched"]), default=0)

print()
print("--- Orks army rules wiring" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
print("  frames / phase changes seen     : %d / %d" % (state["frames"], len(state["phase_keys"])))
print("  A. War Cry prompts to Player 1  : %s"
      % [(e["round"], e["owner"], e["phase"], e["answered"]) for e in p1])
print("     offers made by main()        : %d, uses %s"
      % (len(state["offers"]), [(u["player"], u["round"], u["owner"]) for u in state["uses"] if u["took"]]))
print("  B. prompts to Player 2 / verdict calls for Player 2 (yes): %d / %d (%d)"
      % (len(p2), len(ai_verdicts), sum(1 for v in ai_verdicts if v[2])))
print("     MockAgent decisions / shown War Cry or an Advance re-roll: %d / %d"
      % (state["llm_calls"], state["llm_offered"]))
print("  C. at the use                   : %s of %s units riled (Reserves %s of %s), deadline %s"
      % (eff.get("riled"), eff.get("units"), eff.get("reserves_riled"), eff.get("reserves"), deadline))
print("     measured on                  : %s (%s)" % (eff.get("unit"), eff.get("gun")))
print("     flag off                     : %s" % (eff.get("plain"),))
print("     flag on                      : %s" % (eff.get("riled_effects"),))
print("     phase changes after the use  : %s" % [(w["key"][0], w["key"][1][-1], w["key"][2], w["serial"],
                                                   "%d/%d" % (w["riled"], w["units"])) for w in after])
print("     refresh disagreements        : %d" % len(violations))
print("  D. staged                       : %s%s" % ({k: v for k, v in staged.items()},
                                                    (" ERROR " + state["stage_error"]) if state["stage_error"] else ""))

for _why, _n in sorted(state["why_not"].items(), key=lambda kv: -kv[1])[:4]:
    print("     not quiet %5dx             : %s" % (_n, _why))
print("     stale Player 1 prompts declined: %s" % (state["declined_other"] or "none"))

if state["stage_error"] or not staged:
    print("  INCONCLUSIVE - the Advance rolls were never staged (%s)" % (state["stage_error"] or "no quiet frame"))
    raise SystemExit(2)
if not NEUTRALIZE and (len(p1) < 2 or not after):
    print("  INCONCLUSIVE - the run did not reach a second Command phase and a phase change after the use")
    raise SystemExit(2)

riled = eff.get("riled_effects") or {}
plain = eff.get("plain") or {}
if not NEUTRALIZE:
    checks = (
        ("War Cry was asked in a Command phase of BOTH players",
         set(owners) >= {HUMAN, AI} and all(e["phase"] == PHASE_COMMAND for e in p1)),
        ("declined, it came back; used, it never came back",
         p1[0]["answered"] == "decline" and use_index is not None and not again and len(human_uses) == 1),
        ("the AI was never prompted - its verdict answered", not p2 and bool(ai_verdicts)),
        ("MockAgent was never shown War Cry or an Advance re-roll", state["llm_offered"] == 0),
        ("every Player 1 unit with the ability is riled up at the use, Reserves included",
         eff.get("units", 0) > 0 and eff.get("riled") == eff.get("units")
         and eff.get("reserves_riled") == eff.get("reserves")),
        ("5+ invulnerable save, and not without the flag",
         riled.get("invuln") == "5+" and plain.get("invuln") != "5+"),
        ("[ASSAULT] at the Advance gate and the Assault type after an Advance, and neither without",
         riled.get("gate_assault") is True and "Assault" in (riled.get("types_after_advance") or [])
         and plain.get("gate_assault") is False and "Assault" not in (plain.get("types_after_advance") or [])),
        ("an Advance no longer stops the charge, and does without the flag",
         riled.get("charge_after_advance") is True and plain.get("charge_after_advance") is False),
        ("main()'s refresh keeps the army riled up exactly until the deadline", bool(after) and not violations),
        ("a human's Advance roll carries Re-roll Advance", "Re-roll Advance" in (staged.get("human_labels") or [])),
        ("an AI unit's Advance of 1 is thrown again, with no prompt",
         staged.get("ai_rerolled") is True and staged.get("ai_prompts") == 0 and staged.get("ai_offer_calls", 0) >= 1),
    )
else:
    checks = (
        ("no War Cry prompt to anyone", not p1 and not p2),
        ("no War Cry used", not state["uses"]),
        ("no verdict ever asked", not state["verdicts"]),
        ("no Player 1 unit ever riled up", max_riled == 0),
        ("no Re-roll Advance button", "Re-roll Advance" not in (staged.get("human_labels") or [])),
        ("the AI's Advance of 1 is kept - nothing offered it a re-roll",
         not staged.get("ai_rerolled") and staged.get("ai_offer_calls", 0) == 0),
    )
ok = True
for label, passed in checks:
    print("  %-4s %s" % ("ok" if passed else "FAIL", label))
    ok = ok and bool(passed)
print("  VERDICT: %s" % ("OK" if ok else "FAILED"))
raise SystemExit(0 if ok else 1)
