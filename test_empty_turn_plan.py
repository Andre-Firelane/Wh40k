"""Regression tests for the empty turn plan reported from
logs/game_20260808_205150.log.

What happened there: the FIRST plan had orders for every squad but three
fixable position problems, so it went back to the planner on the one-retry
channel. The revision came back with its entire unit_plans as a single entry
keyed literally "placeholder" at (0,0). It was accepted, because the only
acceptance test was "fewer problems" - and a plan that names no real squad has
none. The whole turn then ran with no orders, and nothing in the log said so:

    Player 2: turn plan had 3 unreachable position(s), sent back to the
              planner - it re-planned.
    Player 2 turn plan: Hold our home objective and Central Objective ...
      [turn plan] placeholder: advance @(0,0)

Each case below asserts the fix AND (where it matters) reproduces the old
behaviour with the fix disabled, so the test is known to hit the real cause."""
from game import maps, config
from game.game_state import GameState
from game.factions import build_squad
from game.factions.orks import BOYZ, GRETCHIN, TANKBUSTAS, TRUKK, WARBIKERS
from game.turn import TurnTracker
from game.game_log import GameLog
from ai import agent_driver
from ai.claude_agent import _is_placeholder_plan, _sanitize_turn_plan

m = maps.get('map2'); maps.apply_to_config(m)
checks, failed = 0, []
def ok(label, cond):
    global checks
    checks += 1
    if not cond:
        failed.append(label)
    print(("  PASS  " if cond else "  FAIL  ") + label)


def entry(role="advance", target="", reason="", position=None, priority=1):
    return {"role": role, "target": target, "reason": reason,
            "position": position, "priority": priority}


def build_army(state):
    """Player 2's squads from the reported log, placed in its own zone."""
    squads = [
        (BOYZ, "2 Boyz 1", 26.0, 9.0),
        (GRETCHIN, "2 Gretchin 1", 21.0, 12.0),
        (TANKBUSTAS, "2 Tankbustas 1", 10.0, 13.0),
        (TRUKK, "2 Trukk 1", 34.0, 10.0),
        (WARBIKERS, "2 Warbikers 1", 38.0, 10.0),
    ]
    built = []
    for sheet, name, x, y in squads:
        squad = build_squad(sheet, "Player 2", name=name)
        for i, model in enumerate(squad.models):
            model.x_in, model.y_in = x + (i % 3) * 1.4, y + (i // 3) * 1.4
        state.tokens.extend(squad.models)
        built.append(squad)
    return built


# ------------------------------------------------- 1. the acceptance criterion
print("\n1) a revision that deletes the orders is refused (the reported cause)")
state = GameState(); m.build(state)
army = build_army(state)

# The reported first plan: real orders for every squad, one unreachable spot.
good_plan = {
    "turn_intent": "hold and advance",
    "unit_plans": {
        "2 Boyz 1": entry(reason="screen the objective", position=(26.0, 12.0)),
        "2 Gretchin 1": entry(reason="hold home", position=(21.0, 14.0)),
        "2 Tankbustas 1": entry(reason="rokkits on the ghostkeel", position=(10.0, 33.0)),
        "2 Trukk 1": entry(reason="carry boyz up", position=(34.0, 12.0)),
        "2 Warbikers 1": entry(reason="threaten the kroot", position=(35.0, 12.0)),
    },
    "malformed": False,
}
# The reported revision: one entry, no real squad.
stub_plan = {"turn_intent": "hold and advance",
             "unit_plans": {"placeholder": entry(position=(0.0, 0.0))},
             "malformed": False}

recheck = lambda p: agent_driver._unreachable_position_problems(p, "Player 2", state)
coverage = lambda p: agent_driver._planned_squad_coverage(p, "Player 2", state)

ok("the good plan covers all 5 squads", coverage(good_plan) == 5)
ok("the stub covers 0 squads", coverage(stub_plan) == 0)
problems = recheck(good_plan)
ok("the good plan really does have problems to send back (%d)" % len(problems), len(problems) > 0)
ok("the stub really does score zero problems", len(recheck(stub_plan)) == 0)


class ScriptedAgent:
    """First call returns `first`, the retry returns `second`."""
    def __init__(self, first, second):
        self.first, self.second, self.calls = first, second, 0
    def plan_turn(self, observation, problems=()):
        self.calls += 1
        return self.first if self.calls == 1 else self.second


out = {}
agent = ScriptedAgent(good_plan, stub_plan)
agent_driver._run_turn_plan(agent, lambda: {"squads": []}, out,
                            recheck=recheck, coverage=coverage)
ok("the retry was made", agent.calls == 2)
ok("the stub revision was NOT taken", out["plan"] is good_plan)
ok("it is not reported as 're-planned'", not out.get("revised"))
ok("the refusal is reported", "revision_rejected" in out)
ok("the refusal names the coverage it lost",
   "0 of this army's squads instead of 5" in out.get("revision_rejected", ""))
ok("orders for every squad survive", len(out["plan"]["unit_plans"]) == 5)

print("\n   A/B: with the coverage floor removed, the reported bug comes back")
out_old = {}
agent_old = ScriptedAgent(good_plan, stub_plan)
agent_driver._run_turn_plan(agent_old, lambda: {"squads": []}, out_old,
                            recheck=recheck, coverage=None)
ok("without the floor the stub IS accepted (reproduces the report)",
   out_old["plan"] is stub_plan and out_old.get("revised"))

print("\n   a genuine revision is still taken")
fixed_plan = {
    "turn_intent": "hold and advance",
    "unit_plans": dict(good_plan["unit_plans"],
                       **{"2 Tankbustas 1": entry(reason="rokkits", position=(10.0, 15.0)),
                          "2 Warbikers 1": entry(reason="flank", position=(40.0, 16.0))}),
    "malformed": False,
}
ok("the fixed plan has fewer problems", len(recheck(fixed_plan)) < len(problems))
out2 = {}
agent2 = ScriptedAgent(good_plan, fixed_plan)
agent_driver._run_turn_plan(agent2, lambda: {"squads": []}, out2,
                            recheck=recheck, coverage=coverage)
ok("a real fix is accepted", out2["plan"] is fixed_plan and out2.get("revised"))
ok("and it is not reported as rejected", "revision_rejected" not in out2)

print("\n   a revision that keeps coverage but fixes nothing is still refused")
out3 = {}
agent3 = ScriptedAgent(good_plan, good_plan)
agent_driver._run_turn_plan(agent3, lambda: {"squads": []}, out3,
                            recheck=recheck, coverage=coverage)
ok("repeating the same impossible order is not an improvement", not out3.get("revised"))

print("\n   an equal-coverage revision counts as enough (no ratchet)")
swapped = {"turn_intent": "x",
           "unit_plans": dict(fixed_plan["unit_plans"]), "malformed": False}
out4 = {}
agent4 = ScriptedAgent(good_plan, swapped)
agent_driver._run_turn_plan(agent4, lambda: {"squads": []}, out4,
                            recheck=recheck, coverage=coverage)
ok("same squad count, fewer problems -> accepted", out4.get("revised") is True)

print("\n   embarked and reserve squads count as coverage")
passenger = build_squad(BOYZ, "Player 2", name="2 Boyz 2")
state.embarked_squads.append(passenger)
reserve = build_squad(TANKBUSTAS, "Player 2", name="2 Tankbustas 2")
state.reserves.append(reserve)
ok("a passenger counts",
   coverage({"unit_plans": {"2 Boyz 2": entry()}}) == 1)
ok("a reserve unit counts",
   coverage({"unit_plans": {"2 Tankbustas 2": entry()}}) == 1)
enemy = build_squad(BOYZ, "Player 1", name="1 Boyz 9")
for model in enemy.models:
    model.x_in, model.y_in = 30.0, 40.0
state.tokens.extend(enemy.models)
ok("an ENEMY squad does not count as this army's coverage",
   coverage({"unit_plans": {"1 Boyz 9": entry()}}) == 0)


# ------------------------------------------------------- 2. stub detection
print("\n2) a placeholder squad NAME is detected (was invisible)")
ok("the reported stub is flagged",
   _is_placeholder_plan({"placeholder": entry()}))
ok("case and padding do not hide it",
   _is_placeholder_plan({"  PLACEHOLDER  ": entry()}))
ok("other marker words too",
   _is_placeholder_plan({"example unit": entry()}) and _is_placeholder_plan({"TBD": entry()}))
ok("a real one-unit plan is NOT flagged",
   not _is_placeholder_plan({"2 Boyz 1": entry(reason="screen the objective")}))
ok("a real two-unit plan sharing a reason is NOT flagged",
   not _is_placeholder_plan({"2 Boyz 1": entry(reason="push"),
                             "2 Gretchin 1": entry(reason="push")}))
print("\n   the existing signals still work")
ok("placeholder reason still flagged",
   _is_placeholder_plan({"2 Boyz 1": entry(reason="(test plan)")}))
ok("three identical reasons still flagged",
   _is_placeholder_plan({"a": entry(reason="go"), "b": entry(reason="go"),
                         "c": entry(reason="go")}))

print("\n   sanitize marks it malformed end-to-end")
sanitized = _sanitize_turn_plan({
    "turn_intent": "Hold our home objective and Central Objective ...",
    "unit_plans": [{"squad": "placeholder", "role": "advance",
                    "position_x": 0, "position_y": 0, "priority": 1, "reason": ""}],
})
ok("malformed is set on the reported shape", sanitized["malformed"] is True)
ok("the intent is still kept for the overlay", sanitized["turn_intent"].startswith("Hold our home"))
real = _sanitize_turn_plan({
    "turn_intent": "push the centre",
    "unit_plans": [{"squad": "2 Boyz 1", "role": "advance", "position_x": -1,
                    "position_y": -1, "priority": 1, "reason": "screen the objective"}],
})
ok("a real plan is not marked malformed", real["malformed"] is False)


# --------------------------------------------------- 3. the validator speaks up
print("\n3) an order for a unit that does not exist is logged, not swallowed")
log = GameLog()
tracker = TurnTracker("Player 2")
validated = agent_driver._validate_turn_plan(
    {"turn_intent": "x", "unit_plans": {"placeholder": entry(position=(0.0, 0.0))},
     "malformed": False},
    "Player 2", state, tracker, log)
lines = list(log.entries)
ok("the unknown unit is named in the log",
   any("placeholder" in line and "no such unit" in line for line in lines))
ok("malformed is escalated so the caller's WARNING fires",
   validated["malformed"] is True)

print("\n   a plan with real orders is untouched")
log2 = GameLog()
validated2 = agent_driver._validate_turn_plan(
    {"turn_intent": "x",
     "unit_plans": {"2 Boyz 1": entry(reason="screen", position=(26.0, 12.0))},
     "malformed": False},
    "Player 2", state, tracker, log2)
lines2 = list(log2.entries)
ok("no 'no such unit' line", not any("no such unit" in line for line in lines2))
ok("not marked malformed", validated2["malformed"] is False)

print("\n   a mixed plan keeps the real order and reports only the bogus one")
log3 = GameLog()
validated3 = agent_driver._validate_turn_plan(
    {"turn_intent": "x",
     "unit_plans": {"2 Boyz 1": entry(reason="screen", position=(26.0, 12.0)),
                    "Ghost Unit": entry(position=(20.0, 20.0))},
     "malformed": False},
    "Player 2", state, tracker, log3)
lines3 = list(log3.entries)
ok("the bogus order is reported", any("Ghost Unit" in line for line in lines3))
ok("but the plan is not called malformed (one real order stands)",
   validated3["malformed"] is False)
ok("the real order survives", "2 Boyz 1" in validated3["unit_plans"])


print("\n%d checks, %d failed" % (checks, len(failed)))
for f in failed:
    print("  FAILED: " + f)
raise SystemExit(1 if failed else 0)
