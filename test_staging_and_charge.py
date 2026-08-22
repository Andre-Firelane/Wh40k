"""Staging that is really staging, and a charge the planner can see.

Reported from logs/game_20260819_222130.log (map 3, battle round 2, WAAAGH!
active and 'Ere We Go already paid for). The 20-strong Boyz mob was ordered to
a "staging position at (3.8, 9.5)" with the reason "close distance under
WAAAGH! for a charge next turn". Two things were wrong with that, and they had
one root:

  * that spot gains 1.00" of ground and moves 3.2" SIDEWAYS - 17% of the unit's
    6" move. It qualified because the staging filter was a flat inch. So the
    mob crabbed across the board, which is what the user saw ("anstatt nach
    vorne zu stürmen und zu chargen sind sie eher zur seite und teilweise
    zurückgegangen").
  * a full move forward instead would have left 4.2" to the Ghostkeel: a 5+
    charge at 83%, and 97% with the 'Ere We Go the AI had already bought that
    turn. Nothing in the observation told the planner that, so "advance and
    charge now" and "stage and charge next turn" looked like equals.

And a third effect fell out of the first: the staging spot was close enough
that a Normal move reached it, which suppresses the Advance option entirely
(_advance_is_worth_offering) - so the token spot also cost the unit its run,
which is the user's "die ki benutzt gar nicht mehr rennen".

Run: python test_staging_and_charge.py
"""

import math

from testkit import Checks, GameState, build_squad

from game import attached_units, config, maps
from game.factions.orks import (
    BOYZ, BOYZ_BIG_CHOPPA_TO_POWER_KLAW, PAINBOY, WARBOSS,
)
from game.factions.tau_empire import (
    GHOSTKEEL_BATTLESUIT, PATHFINDER_TEAM, RIPTIDE_BATTLESUIT, STRIKE_TEAM,
)
from game.squad import min_model_movement
from ai import observation as O
from ai import planner_prompt

c = Checks("staging and charge tempo")


def head(title):
    print("\n" + "=" * 74 + f"\n{title}\n" + "=" * 74)


# The mob's real positions from the log's [move detail] line, and the Tau line
# where it stood. Player 2 holds the low-y edge, so forward is +y.
MOB_POSITIONS = [
    (8.52, 10.67), (7.29, 8.71), (8.34, 9.42), (4.82, 10.88), (7.26, 7.44),
    (6.01, 7.58), (8.54, 8.16), (9.56, 9.96), (5.79, 9.96), (9.51, 4.80),
    (5.68, 5.40), (4.65, 6.14), (4.10, 4.99), (9.76, 8.51), (4.53, 8.76),
    (11.68, 6.07), (4.24, 3.73), (3.06, 4.26), (9.12, 3.57), (11.34, 8.71),
    (3.48, 9.98), (5.87, 11.87),
]
ENEMY_LINE = ((GHOSTKEEL_BATTLESUIT, (9.0, 24.0), "1 Ghostkeel Battlesuit 1"),
              (STRIKE_TEAM, (5.0, 25.0), "1 Strike Team 1"),
              (RIPTIDE_BATTLESUIT, (22.0, 24.0), "1 Riptide Battlesuit 1"),
              (PATHFINDER_TEAM, (17.0, 25.0), "1 Pathfinder Team 1"))


def scene():
    state = GameState()
    maps.apply_to_config(maps.get("map3")).build(state)
    mob = build_squad(BOYZ, owner="Player 2", composition_index=1,
                      choices={"Boss Nob": {BOYZ_BIG_CHOPPA_TO_POWER_KLAW: 1}},
                      name="2 Boyz 1")
    mob = attached_units.attach(build_squad(WARBOSS, owner="Player 2", name="2 Warboss 1"),
                                mob, game_state=state)
    mob = attached_units.attach(build_squad(PAINBOY, owner="Player 2", name="2 Painboy 1"),
                                mob, game_state=state)
    for model, (x, y) in zip(mob.models, MOB_POSITIONS):
        model.x_in, model.y_in = x, y
    foes = []
    for sheet, (x, y), name in ENEMY_LINE:
        squad = build_squad(sheet, owner="Player 1", name=name)
        for index, model in enumerate(squad.models):
            model.x_in, model.y_in = x + (index % 5) * 1.3, y + (index // 5) * 1.3
        foes.append(squad)
    state.tokens = list(mob.models) + [m for s in foes for m in s.models]
    return state, mob, foes


def centroid(squad):
    return (sum(m.x_in for m in squad.models) / len(squad.models),
            sum(m.y_in for m in squad.models) / len(squad.models))


def goal_of(mob, foes):
    nearest = min(foes, key=lambda e: mob.min_distance_to(e))
    return centroid(nearest), nearest


class pre_fix_staging:
    """A/B: the whole pre-fix world, both halves of it.

    All three of them: one inch of progress whatever the unit's move is, cover
    judged at a single point rather than across the footprint the unit occupies,
    and no direction test. Restoring only one is not enough - each of the other
    two rejects the reported spot on its own, so a partial A/B reports that the
    bug never existed."""

    def __enter__(self):
        self.fraction = O.MIN_STAGING_ADVANCE_FRACTION
        self.probes = O._footprint_probes
        self.advance = O._is_an_advance
        O.MIN_STAGING_ADVANCE_FRACTION = 0.0
        O._footprint_probes = lambda x, y, r, f, tx, ty: [(x, y)]
        O._is_an_advance = lambda progress_in, sideways_in: True

    def __exit__(self, *exc):
        O.MIN_STAGING_ADVANCE_FRACTION = self.fraction
        O._footprint_probes = self.probes
        O._is_an_advance = self.advance


# =====================================================================
head("1. the reported staging spot, and why it qualified")
# =====================================================================
state, mob, foes = scene()
goal, nearest = goal_of(mob, foes)
cx, cy = centroid(mob)
budget = min_model_movement(mob)
c.eq("the scene is the reported one - a 22-model mob", len(mob.models), 22)
c.eq("moving 6\"", budget, 6.0)
c.true("and the enemy is forward of it (Player 2 holds the low-y edge)", goal[1] > cy)

with pre_fix_staging():
    before = O.staging_positions(mob, foes, state.obstacles, state.terrain_areas, state.tokens,
                                 goal=goal)
reported = [s for s in before if abs(s["x"] - 3.8) < 0.3 and abs(s["y"] - 9.5) < 0.3]
c.true("A/B - the pre-fix filters offer the spot the log names, (3.8,9.5)",
       len(reported) == 1)
if reported:
    spot = reported[0]
    sideways = abs(spot["x"] - cx)
    forward = spot["y"] - cy
    print(f"    it gains {spot['progress_toward_your_goal_in']:.2f}\" "
          f"({100 * spot['progress_toward_your_goal_in'] / budget:.0f}% of the move) "
          f"and moves {sideways:.1f}\" sideways for {forward:.1f}\" forward")
    c.true("...and it really is a token gain - under a fifth of the unit's move",
           spot["progress_toward_your_goal_in"] < 0.2 * budget)
    c.true("...while moving further sideways than forward", sideways > forward)

after = O.staging_positions(mob, foes, state.obstacles, state.terrain_areas, state.tokens,
                            goal=goal)
c.true("now it is not offered at all",
       not any(abs(s["x"] - 3.8) < 0.3 and abs(s["y"] - 9.5) < 0.3 for s in after))
c.true("every spot still offered is an advance, not a shuffle across the front",
       all(s["progress_toward_your_goal_in"] >= 0.25 * budget - 1e-6 for s in after))
print(f"    staging spots offered: {len(before)} before, {len(after)} now")

# =====================================================================
head("2. the charge that was available instead")
# =====================================================================
state, mob, foes = scene()
ghostkeel = next(e for e in foes if "Ghostkeel" in e.name)
now = O.charge_now(mob, ghostkeel)
print(f"    Ghostkeel: {mob.min_distance_to(ghostkeel):.2f}\" away, "
      f"{now['gap_after_moving_in']:.1f}\" left after a full move, "
      f"needs {now['charge_roll_needed']}+, {now['chance_to_reach_it_this_turn']}")
c.true("a full move leaves about four inches", 3.5 < now["gap_after_moving_in"] < 5.0)
c.eq("which is a 5+ charge", now["charge_roll_needed"], 5)
c.eq("i.e. 83% - the turn the plan gave up", now["chance_to_reach_it_this_turn"], "83%")

far = next(e for e in foes if "Riptide" in e.name)
far_now = O.charge_now(mob, far)
c.true("and a target it genuinely could not reach reads as unlikely",
       float(far_now["chance_to_reach_it_this_turn"].rstrip("%")) < 25.0)

# =====================================================================
head("3. the planner is now told, on the entry it already reads")
# =====================================================================
assessment = O.threat_assessment(mob, foes)
charge_rows = assessment["best_targets_for_you"].get("best_to_charge", [])
c.true("the mob has melee targets listed at all", len(charge_rows) >= 2)
c.true("every one carries the odds of reaching it THIS turn",
       all("chance_to_reach_it_this_turn" in row for row in charge_rows))
by_name = {row["unit"]: row for row in charge_rows}
if "1 Ghostkeel Battlesuit 1" in by_name and "1 Pathfinder Team 1" in by_name:
    gk, pf = by_name["1 Ghostkeel Battlesuit 1"], by_name["1 Pathfinder Team 1"]
    print(f"    {pf['unit']}: value {pf['value_you_remove_per_turn']}, "
          f"{pf['chance_to_reach_it_this_turn']} this turn")
    print(f"    {gk['unit']}: value {gk['value_you_remove_per_turn']}, "
          f"{gk['chance_to_reach_it_this_turn']} this turn")
    c.true("the higher-value target is the one it cannot reach",
           pf["value_you_remove_per_turn"] > gk["value_you_remove_per_turn"])
    c.true("...and the difference is now visible instead of having to be inferred",
           float(gk["chance_to_reach_it_this_turn"].rstrip("%"))
           > float(pf["chance_to_reach_it_this_turn"].rstrip("%")) + 40.0)

# =====================================================================
head("4. a unit with no position yet is not given a charge roll")
# =====================================================================
reserve = O.matchup_targets(mob, foes)
c.true("a reserve unit still gets its melee matchups",
       len(reserve.get("best_to_charge", [])) >= 1)
c.true("...but no charge roll, because it has nowhere to charge from (18.02/20.04)",
       all("chance_to_reach_it_this_turn" not in row
           for row in reserve.get("best_to_charge", [])))

# =====================================================================
head("5. staging uses the board it is actually on")
# =====================================================================
state, mob, foes = scene()
goal, _nearest = goal_of(mob, foes)
with pre_fix_staging():
    spots = O.staging_positions(mob, foes, state.obstacles, state.terrain_areas, state.tokens,
                                goal=goal)
c.true("no spot is off the 30x30 board",
       all(0 < s["x"] < config.BOARD_WIDTH_IN and 0 < s["y"] < config.BOARD_HEIGHT_IN
           for s in spots))
c.eq("and the defaults come from config, not a hardcoded board",
     (O.staging_positions.__defaults__[1], O.staging_positions.__defaults__[2]), (None, None))

# =====================================================================
head("6. the prompt says which one to prefer")
# =====================================================================
text = planner_prompt.SYSTEM_PROMPT if hasattr(planner_prompt, "SYSTEM_PROMPT") else max(
    (v for v in vars(planner_prompt).values() if isinstance(v, str)), key=len)
for needle, label in (
    ("chance_to_reach_it_this_turn", "the new field is named"),
    ("Getting into combat AT ALL this turn", "tempo is stated as the rule"),
    ("WAAAGH", "and the Advance-and-charge case is called out"),
):
    c.true(label, needle in text)

c.finish()
