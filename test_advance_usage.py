"""Tests for the AI being able to Advance (rule 09.06) at all.

REPORT: "was mir auffaellt ist, dass die ki sehr wenig rennen benutzt. gerade
im waagh zug hat man dadurch ja kaum abzuege. man darf danach noch chargen."

The Advance was not being weighed and rejected - it was unreachable by
construction, through three rules that were each defensible alone:

  1. ai/observation.py told the planner a position order must lie inside a
     circle of radius M (the flat Move characteristic);
  2. ai/agent_driver.py's _validate_turn_plan() clamped anything outside that
     circle back onto it;
  3. the tactical layer only builds an "Advance toward the planned position"
     option when the commanded point is FURTHER than a plain move - which (1)
     and (2) had just made impossible.

Rule 3 is CORRECT and is deliberately left alone: if a plain move already
reaches the commanded point, Advancing lands on the same spot and forfeits
non-Assault shooting for nothing. The fix is rules 1 and 2 - the planner may
now ask for the Advance band, and the clamp lets it through.

WAAAGH! is the case the report names, and the reason the numbers matter: the
army rule suspends 09.06's charge forfeit, so for a melee unit the extra D6 is
close to free. charge_now() therefore reports the advance-first charge chance
alongside the plain-move one, and the tactical option carries both.

A/B: the pre-fix world is restored by putting reach back on the flat Move
characteristic. Restoring _CLAMP_TOLERANCE_IN alone would NOT be enough - the
three rules only bite together, and this repo has now hit that trap three
times.

Uses real MovementController/TurnTracker/WaaaghController/GameState objects and
real datasheets throughout.

Run: python test_advance_usage.py
"""
import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from testkit import Checks, GameState, TurnTracker, build_squad

from ai import agent_driver, observation
from game import attached_units, maps
from game.dice import DiceManager
from game.ere_we_go import ERE_WE_GO_ROLL_BONUS
from game.factions.orks import BOYZ, FLASH_GITZ, WARBOSS
from game.factions.tau_empire import STRIKE_TEAM
from game.movement import MovementController
from game.squad import min_model_movement
from game.turn import PHASE_MOVEMENT, PHASES
from game.waaagh import WaaaghController

maps.apply_to_config(maps.get("map2"))
c = Checks("Advance usage (rule 09.06)")


def close(label, got, want, tol):
    """Checks has no float comparison; percentages need one."""
    return c.true(f"{label} ({got:.1f} vs {want:.1f})", abs(got - want) <= tol)


class plain_move_reach:
    """The pre-fix world: reach is the flat Move characteristic."""

    def __enter__(self):
        self._saved = observation.advance_reach_in
        observation.advance_reach_in = min_model_movement
        return self

    def __exit__(self, *exc):
        observation.advance_reach_in = self._saved
        return False


class RaisingAgent:
    def decide(self, *a, **k):
        raise AssertionError("no agent call should be needed to build options")


def scene(gap_in=14.0, waaagh=True, ork_sheet=BOYZ, ork_kwargs=None):
    """One Ork unit `gap_in` from one Tau unit, in the Ork player's own
    Movement phase."""
    state = GameState()
    orks = build_squad(ork_sheet, "Player 2", name="2 Boyz 1", **(ork_kwargs or {}))
    foe = build_squad(STRIKE_TEAM, "Player 1", name="1 Foe 1")
    for i, model in enumerate(orks.models):
        model.x_in, model.y_in = 20.0 + (i % 5) * 1.4, 20.0 - (i // 5) * 1.4
    for i, model in enumerate(foe.models):
        model.x_in, model.y_in = 20.0 + i * 1.4, 20.0 + gap_in
    for squad in (orks, foe):
        for model in squad.models:
            state.add_token(model)

    turn = TurnTracker()
    turn.phase_index = PHASES.index(PHASE_MOVEMENT)
    turn.turn_owner = "Player 2"
    turn.set_active("Player 2")
    wa = WaaaghController()
    if waaagh:
        wa.active_players.add("Player 2")
    mover = MovementController(obstacles=state.obstacles, turn_tracker=turn,
                               all_tokens=state.tokens, dice_manager=DiceManager())
    return {"state": state, "orks": orks, "foe": foe, "turn": turn,
            "waaagh": wa, "move": mover}


def options_for(sc, position=None, target=None):
    """The option types and descriptions _handle_movement() builds for the Ork
    squad, with the plan naming `position`/`target`."""
    seen = {}

    def spy(agent, all_tokens, tracker, options, player, on_thinking, **kwargs):
        seen["types"] = [o["type"] for o in options]
        seen["descriptions"] = [o["description"] for o in options]
        return options[0]

    memory = agent_driver.AIMemory()
    memory.turn_plan = {"turn_intent": "", "malformed": False, "unit_plans": {
        sc["orks"].name: {"role": "advance", "target": target, "position": position,
                          "priority": 1, "reason": "test"}}}
    memory._turn_key = (sc["turn"].battle_round, "Player 2")
    real, agent_driver._choose = agent_driver._choose, spy
    try:
        agent_driver._handle_movement(
            RaisingAgent(), memory, "Player 2", sc["state"], sc["move"],
            None, None, None, None, waaagh_controller=sc["waaagh"])
    finally:
        agent_driver._choose = real
    return seen.get("types", []), seen.get("descriptions", [])


# ===========================================================================
# 1. The reported failure: a plan position inside a plain move leaves no
#    Advance option anywhere, which is how the WAAAGH turn ran.
# ===========================================================================
print("\n1. the reported turn: a reachable plan position hides the Advance")

sc = scene()
move = min_model_movement(sc["orks"])
c.eq("scene: the Boyz mob moves 6\"", move, 6)
c.true("scene: WAAAGH! is active for this unit",
       agent_driver.squad_waaagh_active(sc["orks"], sc["waaagh"]))

types, _ = options_for(sc, position=(20.0, 20.0 + move * 0.9))
c.true("a plan position inside the move offers a plain move", "move_to_planned_position" in types)
c.true("...and no Advance at all - the reported state",
       not any(t.startswith("advance") for t in types))

# The same board with NO position named is the one unit that did Advance that
# turn: the option exists, it was the position order that removed it.
sc = scene()
types, _ = options_for(sc, position=None)
c.true("with no position named, the same unit IS offered an Advance",
       "advance_to_nearest_enemy" in types)


# ===========================================================================
# 2. A position in the Advance band now survives the validator - and that is
#    what puts the option back.
# ===========================================================================
print("\n2. an order in the Advance band survives validation")

reach = observation.advance_reach_in(sc["orks"])
c.eq("advance reach is M plus the average D6", reach, move + observation.AVERAGE_ADVANCE_IN)


def validated_position(sc, spot):
    plan = {"turn_intent": "", "malformed": False, "unit_plans": {
        sc["orks"].name: {"role": "advance", "target": None, "position": spot,
                          "priority": 1, "reason": "test"}}}
    out = agent_driver._validate_turn_plan(plan, "Player 2", sc["state"], sc["turn"], None)
    return out["unit_plans"][sc["orks"].name].get("position")


sc = scene()
band = (20.0, 20.0 + move + 3.0)
kept = validated_position(sc, band)
c.true("a point 3\" past the plain move is left untouched",
       kept is not None and abs(kept[1] - band[1]) < 0.05)

with plain_move_reach():
    sc = scene()
    kept_pre = validated_position(sc, band)
c.true("A/B: pre-fix the same point was clamped back inside the move",
       kept_pre is not None and kept_pre[1] < band[1] - 0.5)

# Still bounded: an order well beyond even an Advance is clamped as before.
sc = scene()
far = (20.0, 20.0 + move + 20.0)
kept_far = validated_position(sc, far)
c.true("a point beyond the Advance band is still clamped",
       kept_far is not None and kept_far[1] < far[1] - 1.0)
c.true("...and clamped no further than the Advance reach",
       kept_far[1] - 20.0 <= reach + 0.6)

# Fed the position the VALIDATOR kept, not the raw order - the whole point is
# that the chain, not one link of it, now lets the Advance through.
sc = scene()
types, descriptions = options_for(sc, position=validated_position(sc, band))
c.true("the tactical layer now offers the Advance to that point",
       "advance_to_planned_position" in types)
c.true("...alongside the plain move to it", "move_to_planned_position" in types)

with plain_move_reach():
    sc = scene()
    kept_pre = validated_position(sc, band)
    types_pre, _ = options_for(sc, position=kept_pre)
c.true("A/B: pre-fix the clamped order left no Advance option",
       not any(t.startswith("advance") for t in types_pre))


# ===========================================================================
# 3. Rule 3 is deliberately unchanged: no Advance when a plain move gets there
# ===========================================================================
print("\n3. an Advance that buys nothing is still not offered")

sc = scene()
types, _ = options_for(sc, position=(20.0, 20.0 + move - 1.0))
c.true("a point inside the plain move gets no Advance option",
       not any(t.startswith("advance") for t in types))
c.true("...because Advancing would land on the same spot and cost the shooting",
       "move_to_planned_position" in types)


# ===========================================================================
# 4. The number on the option: what the extra D6 buys, as a probability
# ===========================================================================
print("\n4. the option states what the Advance is worth")

sc = scene(gap_in=14.0)
_, descriptions = options_for(sc, position=None)
advance_text = next(d for d in descriptions if "Advance toward" in d)
c.true("the WAAAGH! text says the charge survives",
       "can still declare a charge" in advance_text)
c.true("...and the option quotes both charge chances",
       "after a plain move needs" in advance_text and "after this Advance" in advance_text)

# The two numbers themselves.
plain = observation.charge_now(sc["orks"], sc["foe"])
after = observation.charge_chance_after_advancing(sc["orks"], sc["foe"])
before = float(plain["chance_to_reach_it_this_turn"].rstrip("%"))
c.eq("a 12.7\" edge gap needs a 7+ after a 6\" move", plain["charge_roll_needed"], 7)
c.true(f"advancing first is a real improvement ({before:.0f}% -> {after:.0f}%)",
       after > before + 20)

# Without a WAAAGH the charge is forfeit, so there is no before/after to quote.
sc = scene(gap_in=30.0, waaagh=False)
_, descriptions = options_for(sc, position=None)
advance_text = next((d for d in descriptions if "Advance toward" in d), "")
c.true("without WAAAGH! the option says the charge is lost",
       "cannot shoot with non-Assault weapons or declare a charge" in advance_text)
c.true("...and quotes no charge chances", "after this Advance" not in advance_text)

# A charge that is already near-certain gets no note - a superlative on every
# option is the same as none.
sc = scene(gap_in=7.0)
note = agent_driver._advance_charge_note(sc["orks"], sc["foe"], True)
c.eq("a charge that is already certain gets no note", note, "")


# ===========================================================================
# 5. The joint probability is exact, not "average Advance then charge"
# ===========================================================================
print("\n5. the advance-first chance is the real joint distribution")


def brute_force(squad, foe):
    """Every (D6, 2D6) outcome enumerated, as a percentage."""
    gap = squad.min_distance_to(foe)
    move = min_model_movement(squad)
    bonus = ERE_WE_GO_ROLL_BONUS if getattr(squad, "ere_we_go_active", False) else 0
    hits = 0
    for die in range(1, 7):
        left = max(0.0, gap - move - die - bonus)
        for a in range(1, 7):
            for b in range(1, 7):
                if a + b + bonus >= math.ceil(left) or left <= 0:
                    hits += 1
    return 100.0 * hits / (6 * 36)


sc = scene(gap_in=14.0)
close("matches a full enumeration of both rolls",
      observation.charge_chance_after_advancing(sc["orks"], sc["foe"]),
      brute_force(sc["orks"], sc["foe"]), 0.6)

# Averaging the Advance roll first is materially wrong exactly where the
# decision is closest - a marginal charge. At this gap it understates by a
# third, which would turn "worth Advancing for" into "not worth it".
sc = scene(gap_in=19.0)
close("still matches a full enumeration on a marginal charge",
      observation.charge_chance_after_advancing(sc["orks"], sc["foe"]),
      brute_force(sc["orks"], sc["foe"]), 0.6)
naive = observation.charge_roll_chance(
    max(0.0, sc["orks"].min_distance_to(sc["foe"])
        - min_model_movement(sc["orks"]) - observation.AVERAGE_ADVANCE_IN))
joint = observation.charge_chance_after_advancing(sc["orks"], sc["foe"])
c.true(f"...and beats averaging the Advance roll first "
       f"(naive {naive:.0f}% vs joint {joint:.0f}%)", joint - naive > 5.0)

# 'Ere We Go's +2 applies to the Advance roll AND the charge roll, so it must
# raise both the reach and the odds.
sc = scene(gap_in=14.0)
plain_reach = observation.advance_reach_in(sc["orks"])
without = observation.charge_chance_after_advancing(sc["orks"], sc["foe"])
sc["orks"].ere_we_go_active = True
c.eq("'Ere We Go widens the Advance reach by its +2",
     observation.advance_reach_in(sc["orks"]), plain_reach + ERE_WE_GO_ROLL_BONUS)
c.true("...and raises the advance-first charge chance",
       observation.charge_chance_after_advancing(sc["orks"], sc["foe"]) > without)


# ===========================================================================
# 6. What the planner is told
# ===========================================================================
print("\n6. the observation states both radii and both chances")

sc = scene(gap_in=14.0)
obs = observation.build_planning_observation(
    [sc["orks"], sc["foe"]], [], sc["turn"], "Player 2",
    objectives=sc["state"].objectives, obstacles=sc["state"].obstacles,
    terrain_areas=sc["state"].terrain_areas, waaagh_controller=sc["waaagh"])
entry = next(u for u in obs["squads"] if u["name"] == "2 Boyz 1")
circle = entry["reachable_this_turn"]
c.eq("the plain-move radius is unchanged", circle["radius_in"], float(move))
c.true("a second, wider Advance radius is reported", "if_you_advance" in circle)
c.eq("...at M plus the average D6", circle["if_you_advance"]["radius_in"],
     round(move + observation.AVERAGE_ADVANCE_IN, 1))
c.true("...and its note says the WAAAGH! keeps the charge",
       "NOT its charge" in circle["if_you_advance"]["note"])

charge_entry = entry["threat_assessment"]["best_targets_for_you"]["best_to_charge"][0]
c.true("the charge target carries the advance-first chance",
       "chance_if_you_advance_first" in charge_entry)
c.true("...next to the plain-move chance",
       "chance_to_reach_it_this_turn" in charge_entry)

sc = scene(gap_in=14.0, waaagh=False)
obs = observation.build_planning_observation(
    [sc["orks"], sc["foe"]], [], sc["turn"], "Player 2",
    objectives=sc["state"].objectives, obstacles=sc["state"].obstacles,
    terrain_areas=sc["state"].terrain_areas, waaagh_controller=sc["waaagh"])
entry = next(u for u in obs["squads"] if u["name"] == "2 Boyz 1")
c.true("without WAAAGH! the note says the charge is lost too",
       "AND its charge" in entry["reachable_this_turn"]["if_you_advance"]["note"])
charge_entry = entry["threat_assessment"]["best_targets_for_you"]["best_to_charge"][0]
c.true("...and no advance-first chance is quoted",
       "chance_if_you_advance_first" not in charge_entry)


# ===========================================================================
# 7. A shooting unit is not pushed into Advancing
# ===========================================================================
print("\n7. the choice is offered, not forced")

sc = scene(gap_in=14.0, ork_sheet=FLASH_GITZ)
types, _ = options_for(sc, position=(20.0, 20.0 + min_model_movement(sc["orks"]) + 3.0))
c.true("a shooting unit still gets the plain move to the same point",
       "move_to_planned_position" in types)
c.true("...as well as the Advance", "advance_to_planned_position" in types)

# The prompts say which to prefer rather than the engine deciding.
from ai import planner_prompt, tactical_prompt
c.true("the planner prompt names the second radius",
       "if_you_advance" in planner_prompt.PLANNER_SYSTEM_PROMPT)
c.true("...and points at the quantified gain",
       "chance_if_you_advance_first" in planner_prompt.PLANNER_SYSTEM_PROMPT)
c.true("the tactical prompt tells it to read the two chances",
       "after this Advance" in tactical_prompt.TACTICAL_SYSTEM_PROMPT)


# ===========================================================================
# 8. An attached unit moves at its slowest component's pace (19.01/09.02)
# ===========================================================================
print("\n8. attached units")

sc = scene(gap_in=14.0)
mob = attached_units.attach(
    build_squad(WARBOSS, "Player 2", name="Warboss"), sc["orks"])
c.eq("the Warboss does not speed the mob up", min_model_movement(mob), 6)
c.eq("...so the Advance reach is the mob's", observation.advance_reach_in(mob),
     6 + observation.AVERAGE_ADVANCE_IN)

c.finish()
