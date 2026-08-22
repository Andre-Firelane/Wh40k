"""Anti-tank units were told, every turn, that their best use was charging
infantry - and they behaved accordingly.

Two reports, one root cause (user: "die panzaknackas waren fuer mich zu passiv.
die haben sehr gute anti tank waffen und haben sich hinter der mauer versteckt.
konnten so ihr potential nicht abrufen." / "die deffkopter haben auch anti tank
waffen. haben aber irgendwie immer auf die stealth suites geschossen. und die
fahrzeuge ignoriert.").

Everything the AI reads about "what should I attack" was denominated in MODELS
KILLED, and models-killed is the wrong currency for a specialist:

  * threat_assessment().best_targets_for_you ranked every pairing by casualties
    and collapsed the two attack modes into whichever killed more bodies. A
    Rokkit team's list therefore reads "Kroot Carnivores 7.3/turn (melee)" and
    the Battlesuits its S9/AP-2/D3 guns exist for never appear at all.
  * the tactical shoot option printed only the wound threshold, which is a
    per-shot SUCCESS CHANCE: S9 wounds T4 Stealth Battlesuits on 2s and a T8
    Ghostkeel on 3s, so the one number on the option said "shoot the infantry"
    to exactly the unit whose guns are for the vehicle.

Measured across every log kept in this repo: a vehicle appears in 3.8% of the
best-target entries (14 of 747 for the Tankbustas) while the enemy army has
four of them.

The board below is logs/game_20260816_210737.log's own [move detail]
coordinates at the moment the Deffkoptas fired on the Stealth Battlesuits, so
this is the reported turn and not an illustration of it.

Every check that claims the fix did something also runs A/B against the pre-fix
behaviour, re-implemented locally - otherwise a passing suite only proves the
scene is easy.
"""

import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")

from testkit import (Checks, DecisionManager, DiceManager, GameState, TurnTracker,
                     build_squad)

from ai import agent_driver, observation
from game import maps
from game.factions import orks, tau_empire
from game import damage_estimate
from game import squad as squad_module
from game.shooting import ShootingController
from game.turn import PHASE_SHOOTING, PHASES

c = Checks("target priority (anti-tank units)")


# --------------------------------------------------------------- the scene

# Composition index per unit where the army list does not use the first one -
# main.py fields the 6-model Deffkopta squadron, and the log's six positions
# are the check that this table matches the game that was played.
COMPOSITION = {"2 Deffkoptas 1": 1}

P2_UNITS = {
    "2 Tankbustas 1": (orks.TANKBUSTAS, [
        (37.42, 5.47), (35.77, 2.00), (37.03, 2.09),
        (34.62, 5.09), (38.34, 3.71), (37.98, 8.39)]),
    "2 Deffkoptas 1": (orks.DEFFKOPTAS, [
        (38.94, 19.18), (39.58, 17.22), (40.95, 18.76),
        (38.30, 21.14), (40.22, 15.27), (42.01, 16.43)]),
}
P1_UNITS = {
    "1 Stealth Battlesuits 1": (tau_empire.STEALTH_BATTLESUITS, [
        (30.23, 37.54), (27.98, 37.53), (26.39, 39.21), (29.54, 39.55), (31.93, 38.02)]),
    "1 Ghostkeel Battlesuit 1": (tau_empire.GHOSTKEEL_BATTLESUIT, [(7.31, 25.66)]),
    "1 Devilfish": (tau_empire.DEVILFISH, [(6.81, 25.41)]),
    "1 Riptide Battlesuit 1": (tau_empire.RIPTIDE_BATTLESUIT, [(36.41, 35.97)]),
    "1 The Twin Lance 1": (tau_empire.THE_TWIN_LANCE, [(46.97, 28.52), (45.92, 31.22)]),
    "1 Strike Team 1": (tau_empire.STRIKE_TEAM, [
        (42.38, 25.10), (44.21, 24.96), (43.34, 26.34), (43.05, 23.87), (39.75, 26.90),
        (41.21, 26.13), (43.48, 29.01), (45.09, 23.49), (43.53, 27.69), (42.05, 27.34)]),
    "1 Kroot Carnivores 1": (tau_empire.KROOT_CARNIVORES, [
        (27.24, 28.18), (26.04, 27.27), (28.62, 27.59), (27.06, 29.66), (28.60, 29.45),
        (25.62, 29.08), (24.66, 27.86), (29.82, 28.49), (30.40, 27.05), (26.88, 31.15)]),
}


def scene():
    battle_map = maps.get("map2")
    maps.apply_to_config(battle_map)
    state = GameState()
    battle_map.build(state)
    squads = {}
    for owner, table in (("Player 2", P2_UNITS), ("Player 1", P1_UNITS)):
        for name, (sheet, positions) in table.items():
            squad = build_squad(sheet, owner, unit_index=1,
                                composition_index=COMPOSITION.get(name, 0))
            squad.name = name
            squad.models = squad.models[:len(positions)]
            for model, (x, y) in zip(squad.models, positions):
                model.x_in, model.y_in = x, y
                state.tokens.append(model)
            squads[name] = squad
    return state, squads


STATE, SQUADS = scene()
FOES = [s for n, s in SQUADS.items() if n.startswith("1 ")]
TANKBUSTAS = SQUADS["2 Tankbustas 1"]
DEFFKOPTAS = SQUADS["2 Deffkoptas 1"]


def is_vehicle(squad):
    profile = squad.models[0].profile
    return profile.vehicle or profile.monster


# ---------------------------------------------------------------------------
# 1. The scene itself - if these are wrong, nothing below means anything
# ---------------------------------------------------------------------------

c.eq("Tankbustas fielded at 6 models", len(TANKBUSTAS.models), 6)
c.eq("Deffkoptas fielded at 6 models", len(DEFFKOPTAS.models), 6)
c.true("Tankbustas carry S9 Rokkits",
     any(w.strength == 9 for m in TANKBUSTAS.models for w in m.weapons
         if w.weapon_type == "ranged"))
c.true("Deffkoptas carry S9 Rokkits",
     any(w.strength == 9 for m in DEFFKOPTAS.models for w in m.weapons
         if w.weapon_type == "ranged"))
vehicles = [s.name for s in FOES if is_vehicle(s)]
c.eq("the enemy army on this board has four vehicles", len(vehicles), 4)
c.true("Ghostkeel is one of them", "1 Ghostkeel Battlesuit 1" in vehicles)
c.true("Stealth Battlesuits are NOT a vehicle",
     not is_vehicle(SQUADS["1 Stealth Battlesuits 1"]))

# The wound thresholds that used to be the only number on the shoot option -
# this is the bias, stated as data.
stealth_needs = agent_driver._matchup_hint(DEFFKOPTAS, SQUADS["1 Stealth Battlesuits 1"])
ghost_needs = agent_driver._matchup_hint(DEFFKOPTAS, SQUADS["1 Ghostkeel Battlesuit 1"])
c.true("wound threshold alone favours the infantry: 2+ vs Stealth",
     "wounds it on 2+" in stealth_needs)
c.true("...and 3+ vs the Ghostkeel", "wounds it on 3+" in ghost_needs)


# ---------------------------------------------------------------------------
# 2. ranked_targets(): value-ranked, split by attack mode
# ---------------------------------------------------------------------------

def old_merged_ranking(squad, enemies, limit=3):
    """The pre-fix behaviour: one list, ranked by casualties, with the attack
    mode collapsed to whichever kills more bodies. Kept here rather than
    behind a flag in the engine so the comparison is against real code."""
    rows = []
    for enemy in enemies:
        best = None
        for melee in (False, True):
            got = observation.expected_kills(squad, enemy, melee=melee)
            if got is None or got["models_killed_per_turn"] <= 0.05:
                continue
            if best is None or got["models_killed_per_turn"] > best[0]:
                best = (got["models_killed_per_turn"], enemy, melee)
        if best is not None:
            rows.append(best)
    rows.sort(key=lambda r: -r[0])
    return [(enemy.name, "melee" if melee else "shooting") for _k, enemy, melee in rows[:limit]]


for squad in (TANKBUSTAS, DEFFKOPTAS):
    label = squad.name
    old = old_merged_ranking(squad, FOES)
    c.eq(f"A/B {label}: the old merged list named no vehicle at all",
         [n for n, _ in old if any(v == n for v in vehicles)], [])
    c.true(f"A/B {label}: the old merged list was all melee",
         all(mode == "melee" for _n, mode in old))

    new = observation.ranked_targets(squad, FOES)
    c.true(f"{label}: the role is split into shoot/charge lists",
         set(new) == {"best_to_shoot", "best_to_charge"})
    shoot = [e["unit"] for e in new["best_to_shoot"]]
    c.true(f"{label}: best_to_shoot leads with a vehicle ({shoot[0]})",
         shoot and shoot[0] in vehicles)
    c.true(f"{label}: best_to_shoot is sorted by value, descending",
         [e["value_you_remove_per_turn"] for e in new["best_to_shoot"]]
         == sorted((e["value_you_remove_per_turn"] for e in new["best_to_shoot"]), reverse=True))
    c.true(f"{label}: every entry carries the value it was ranked on",
         all("value_you_remove_per_turn" in e
             for k in new for e in new[k]))
    c.true(f"{label}: the casualty count is kept alongside the value",
         all("kills_per_turn" in e for k in new for e in new[k]))

# The specific inversion the report is about: shooting the Ghostkeel is worth
# more points than shooting the Stealth suits, even though the Stealth suits
# are far easier to wound.
ghost = observation.damage_value(TANKBUSTAS, SQUADS["1 Ghostkeel Battlesuit 1"])
stealth = observation.damage_value(TANKBUSTAS, SQUADS["1 Stealth Battlesuits 1"])
kroot = observation.damage_value(TANKBUSTAS, SQUADS["1 Kroot Carnivores 1"])
c.true(f"shooting the Ghostkeel is worth more than the Stealth suits ({ghost:.1f} > {stealth:.1f})",
     ghost > stealth)
c.true(f"...and far more than the Kroot mob ({ghost:.1f} > {kroot:.1f})", ghost > kroot)
c.true("while the CASUALTY count says the opposite (Kroot first)",
     observation.expected_kills(TANKBUSTAS, SQUADS["1 Kroot Carnivores 1"])["models_killed_per_turn"]
     > observation.expected_kills(TANKBUSTAS, SQUADS["1 Ghostkeel Battlesuit 1"])["models_killed_per_turn"])

# A melee unit must NOT be pushed the other way by this: its value still sits
# in best_to_charge.
boyz = build_squad(orks.BOYZ, "Player 2", unit_index=1)
boyz.name = "2 Boyz test"
for i, model in enumerate(boyz.models):
    model.x_in, model.y_in = 26.0 + i * 1.2, 26.0
lists = observation.ranked_targets(boyz, FOES)
charge_top = lists["best_to_charge"][0]["value_you_remove_per_turn"]
shoot_top = lists["best_to_shoot"][0]["value_you_remove_per_turn"] if lists["best_to_shoot"] else 0.0
c.true(f"a melee mob is still worth far more charging than shooting "
     f"({charge_top:.0f} vs {shoot_top:.0f})", charge_top > shoot_top * 2)


# ---------------------------------------------------------------------------
# 3. threat_assessment(): same lists, but gated on what it can actually reach
# ---------------------------------------------------------------------------

assessment = observation.threat_assessment(TANKBUSTAS, FOES)
c.true("threat_assessment reports the split lists",
     set(assessment["best_targets_for_you"]) <= {"best_to_shoot", "best_to_charge"})
c.true("the incoming-threat half is untouched (still a flat, casualty-ranked list)",
     isinstance(assessment["biggest_threats_to_you"], list)
     and all("via" in t for t in assessment["biggest_threats_to_you"]))

near = observation.threat_assessment(TANKBUSTAS, FOES)["best_targets_for_you"]
named = {e["unit"] for k in near for e in near[k]}
reachable = {s.name for s in FOES
             if TANKBUSTAS.min_distance_to(s) - 6.0 <= 24.0
             or TANKBUSTAS.min_distance_to(s) - 6.0 <= 12.0}
c.true("nothing out of reach is listed", named <= reachable)

far = build_squad(tau_empire.STRIKE_TEAM, "Player 1", unit_index=1)
far.name = "1 Far Away"
for i, model in enumerate(far.models):
    model.x_in, model.y_in = 5.0 + i * 1.2, 43.0
gated = observation.threat_assessment(TANKBUSTAS, [far])["best_targets_for_you"]
c.eq("a unit 40\" away is gated out of both lists",
     [e["unit"] for k in gated for e in gated[k]], [])
c.true("...but the same unit IS listed when the reach gate is removed",
     any(e["unit"] == "1 Far Away"
         for k, entries in observation.ranked_targets(TANKBUSTAS, [far]).items()
         for e in entries))

# The passenger path (at_point/point_radius_in) still works after the rewrite.
aboard = observation.threat_assessment(
    TANKBUSTAS, FOES, at_point=(40.0, 20.0), point_radius_in=4.4)
c.true("the at_point path still produces lists",
     isinstance(aboard["best_targets_for_you"], dict))
c.true("...and measuring from a point 15\" further forward names more targets",
     sum(len(v) for v in aboard["best_targets_for_you"].values())
     >= sum(len(v) for v in assessment["best_targets_for_you"].values()))


# ---------------------------------------------------------------------------
# 4. matchup_targets(): the reserve field is now the same function
# ---------------------------------------------------------------------------

reserve = observation.matchup_targets(DEFFKOPTAS, FOES)
c.true("reserve list still carries the target's position",
     all("where_it_is" in e for k in reserve for e in reserve[k]))
c.true("the on-board list does NOT carry it (an on-board unit is not placed by coordinate)",
     all("where_it_is" not in e
         for k, entries in observation.ranked_targets(DEFFKOPTAS, FOES).items()
         for e in entries))
c.true("reserve list is not reach-gated: it names the far-away unit too",
     any(e["unit"] == "1 Far Away"
         for k, entries in observation.matchup_targets(DEFFKOPTAS, [far]).items()
         for e in entries))
c.true("on-board and reserve rankings now agree on the order",
     [e["unit"] for e in reserve.get("best_to_shoot", [])][:1]
     == [e["unit"] for e in observation.ranked_targets(DEFFKOPTAS, FOES)["best_to_shoot"]][:1])


# ---------------------------------------------------------------------------
# 5. The shoot option the tactical layer actually reads
# ---------------------------------------------------------------------------

def shoot_options(squad, foes):
    """The real option text, built through the real ShootingController."""
    state = GameState()
    for group in [squad] + list(foes):
        for model in group.models:
            state.tokens.append(model)
    turn = TurnTracker(first_player="Player 2")
    turn.phase_index = PHASES.index(PHASE_SHOOTING)
    controller = ShootingController(
        dice_manager=DiceManager(), turn_tracker=turn, all_tokens=state.tokens,
        decision_manager=DecisionManager(), game_log=None, obstacles=[])
    controller.start_shooting(squad)
    targets = sorted({t.squad for t in controller.valid_target_models(state.tokens)},
                     key=lambda s: s.name)
    hints = agent_driver._shot_value_hints(squad, targets)
    return {t.name: hints[t.name] for t in targets}, targets


# Rebuilt without terrain so line of sight is not the thing under test here.
kopta2 = build_squad(orks.DEFFKOPTAS, "Player 2", unit_index=1)
kopta2.name = "2 Deffkoptas 1"
for i, model in enumerate(kopta2.models):
    model.x_in, model.y_in = 20.0 + i * 1.6, 20.0
foes2 = []
for name, sheet, x, y in (("1 Stealth", tau_empire.STEALTH_BATTLESUITS, 20.0, 30.0),
                          ("1 Ghostkeel", tau_empire.GHOSTKEEL_BATTLESUIT, 30.0, 30.0),
                          ("1 Devilfish", tau_empire.DEVILFISH, 36.0, 30.0)):
    squad = build_squad(sheet, "Player 1", unit_index=1)
    squad.name = name
    for i, model in enumerate(squad.models):
        model.x_in, model.y_in = x + i * 1.6, y
    foes2.append(squad)

hints, targets = shoot_options(kopta2, foes2)
c.eq("all three targets are shootable in the option scene", len(targets), 3)
for name in ("1 Stealth", "1 Ghostkeel", "1 Devilfish"):
    c.true(f"{name}'s option now states what the shot is worth",
         "enemy points per turn" in hints[name])
c.true("the weakest of the three is called out as such",
     "less than half" in hints["1 Devilfish"])
c.eq("a near-tie names no favourite at all (13 vs 14 is inside the noise)",
     sum(1 for text in hints.values() if "most valuable" in text), 0)

# ...and where there IS a clear leader, exactly one option is named.
tank2 = build_squad(orks.TANKBUSTAS, "Player 2", unit_index=1)
tank2.name = "2 Tankbustas 1"
for i, model in enumerate(tank2.models):
    model.x_in, model.y_in = 20.0 + i * 1.6, 20.0
kroot2 = build_squad(tau_empire.KROOT_CARNIVORES, "Player 1", unit_index=1)
kroot2.name = "1 Kroot"
for i, model in enumerate(kroot2.models):
    model.x_in, model.y_in = 20.0 + i * 1.2, 30.0
ghost2 = build_squad(tau_empire.GHOSTKEEL_BATTLESUIT, "Player 1", unit_index=1)
ghost2.name = "1 Ghostkeel"
ghost2.models[0].x_in, ghost2.models[0].y_in = 30.0, 30.0

hints2, _ = shoot_options(tank2, [kroot2, ghost2])
c.eq("with a clear leader, exactly one option is named the best",
     sum(1 for text in hints2.values() if "most valuable" in text), 1)
c.true("and it is the vehicle, not the 10-model mob",
     "most valuable" in hints2["1 Ghostkeel"])

# A/B: the pre-fix option text carried the wound threshold and nothing else,
# which pointed the other way.
c.true("A/B: the old text alone ranked the Kroot mob ahead (2+ vs 3+)",
     "wounds it on 2+" in agent_driver._matchup_hint(tank2, kroot2)
     and "wounds it on 3+" in agent_driver._matchup_hint(tank2, ghost2))

# The other direction: a unit with no anti-tank guns is not pushed AT a
# vehicle by this. Grot Blastas do almost nothing to a Riptide, and the option
# text has to say so rather than making "vehicle" attractive per se.
grots = build_squad(orks.GRETCHIN, "Player 2", unit_index=1)
grots.name = "2 Gretchin"
for i, model in enumerate(grots.models):
    model.x_in, model.y_in = 20.0 + i * 1.2, 20.0
riptide = build_squad(tau_empire.RIPTIDE_BATTLESUIT, "Player 1", unit_index=1)
riptide.name = "1 Riptide"
riptide.models[0].x_in, riptide.models[0].y_in = 22.0, 26.0
kroot3 = build_squad(tau_empire.KROOT_CARNIVORES, "Player 1", unit_index=1)
kroot3.name = "1 Kroot"
for i, model in enumerate(kroot3.models):
    model.x_in, model.y_in = 20.0 + i * 1.2, 24.0
weak = agent_driver._shot_value_hints(grots, [riptide, kroot3])
c.true("Grot Blastas are told the Riptide is the poor shot, not the good one",
       "less than half" in weak["1 Riptide"])
c.true("...and the mob is named the best one for them",
       "most valuable" in weak["1 Kroot"])


# ---------------------------------------------------------------------------
# 6. The [threat] log line renders the new shape
# ---------------------------------------------------------------------------

rendered = []
targets_block = observation.threat_assessment(TANKBUSTAS, FOES)["best_targets_for_you"]
best = " ; ".join(
    f"{how} " + ", ".join(
        f"{t['unit']} {t['value_you_remove_per_turn']} pts/turn"
        f" ({t['kills_per_turn']} models"
        + (f", {t['trade']}" if t.get("trade") else "") + ")"
        for t in targets_block[key])
    for key, how in (("best_to_shoot", "by shooting:"), ("best_to_charge", "by charging:"))
    if targets_block.get(key)
) or "nothing in reach"
rendered.append(best)
c.true("the log line names both modes separately",
     "by shooting:" in best and "by charging:" in best)
c.true("...and leads with the value it ranked on", "pts/turn" in best)
c.true("...and still carries the trade verdict", "trading" in best)


# ---------------------------------------------------------------------------
# 7. A WOUNDED target is worth more, because killing it is closer
#
# Follow-up report on the same units (user: "die panzaknacker haben auf die
# feuerkrieger geschossen, obwohl da auch ein angeschlagener riptide stand.
# das macht keinen sinn. die haben doch anti tank waffen").
#
# Section 5 above fixed WHICH currency the ranking uses; this is the other
# half of the same sum. Wounds were converted to models by dividing by the
# PRINTED characteristic, so a Riptide on its last wound scored exactly what a
# fresh one did and "finish it off" - the entire reason to shoot the damaged
# thing - could not appear in any ranking.
# ---------------------------------------------------------------------------

print()
print("7. a wounded target")

RIPTIDE_W = riptide.models[0].profile.wounds


def old_models_destroyed(defender, total_wounds):
    """The pre-fix conversion: flat divide by the printed wounds of the soak
    group. Local so a passing check proves the fix and not the scene."""
    if not total_wounds or total_wounds <= 0:
        return 0.0
    _, each = damage_estimate.defender_soak(defender)
    return total_wounds / max(1, each)


def value_at(target, wounds_left, old=False):
    """damage_value() with `target` sitting on `wounds_left`, optionally with
    the old conversion patched back in."""
    was = [m.current_wounds for m in target.models]
    target.models[0].current_wounds = wounds_left
    real = damage_estimate.models_destroyed_by
    if old:
        damage_estimate.models_destroyed_by = old_models_destroyed
        observation.models_destroyed_by = old_models_destroyed
    try:
        return observation.damage_value(TANKBUSTAS, target)
    finally:
        damage_estimate.models_destroyed_by = real
        observation.models_destroyed_by = real
        for model, w in zip(target.models, was):
            model.current_wounds = w


c.true("the scene: the Riptide is a single model with more than one wound",
       len(riptide.models) == 1 and RIPTIDE_W > 1)
c.true("the scene: it is worth real points", (riptide.points or 0) > 100)

full = value_at(riptide, RIPTIDE_W)
half = value_at(riptide, RIPTIDE_W // 2)
last = value_at(riptide, 1)

print(f"    Riptide {RIPTIDE_W}/{RIPTIDE_W} -> {full:.1f} pts   "
      f"{RIPTIDE_W // 2}/{RIPTIDE_W} -> {half:.1f}   1/{RIPTIDE_W} -> {last:.1f}")

c.true("a half-dead Riptide is worth more than a fresh one", half > full * 1.5)
c.true("...and one on its last wound is worth its whole points value",
       abs(last - riptide.points) < 0.5)
c.true("...with the damaged value rising monotonically", full < half < last)

# A/B: without the fix the three numbers are the same.
old_full = value_at(riptide, RIPTIDE_W, old=True)
old_half = value_at(riptide, RIPTIDE_W // 2, old=True)
old_last = value_at(riptide, 1, old=True)
c.true("A/B - the old conversion scored a dying Riptide exactly like a fresh one",
       abs(old_full - old_half) < 0.01 and abs(old_full - old_last) < 0.01)

# An UNDAMAGED unit must be untouched by all of this.
fresh_before = old_models_destroyed(
    kroot3, observation.expected_wounds_against(TANKBUSTAS, kroot3))
fresh_after = damage_estimate.models_destroyed_by(
    kroot3, observation.expected_wounds_against(TANKBUSTAS, kroot3))
c.true("an undamaged unit is valued exactly as before",
       abs(fresh_before - fresh_after) < 1e-9)

# The tactical shoot option is what the AI actually reads. Its own scene,
# because the module-level FOES list is the reported board and has no Riptide
# on it: a Tankbusta squad with a wounded Riptide and a Fire Warrior squad both
# in Rokkit range, which is precisely the choice the user watched it get wrong.
tb2 = build_squad(orks.TANKBUSTAS, "Player 2", unit_index=1)
tb2.name = "2 Tankbustas"
for i, model in enumerate(tb2.models):
    model.x_in, model.y_in = 20.0 + i * 1.4, 20.0
rip2 = build_squad(tau_empire.RIPTIDE_BATTLESUIT, "Player 1", unit_index=1)
rip2.name = "1 Riptide"
rip2.models[0].x_in, rip2.models[0].y_in = 22.0, 30.0
warriors = build_squad(tau_empire.STRIKE_TEAM, "Player 1", unit_index=1)
warriors.name = "1 Strike Team"
for i, model in enumerate(warriors.models):
    model.x_in, model.y_in = 14.0 + i * 1.2, 30.0

fresh_hints, _ = shoot_options(tb2, [rip2, warriors])
rip2.models[0].current_wounds = 3
hurt_hints, _ = shoot_options(tb2, [rip2, warriors])
print(f"    fresh:   {fresh_hints['1 Riptide']}")
print(f"    wounded: {hurt_hints['1 Riptide']}")
def quoted_points(text):
    """The "~N enemy points per turn" figure out of an option hint."""
    return float(text.split("worth ~")[1].split(" ")[0])


c.true("the shoot option names the wounded Riptide the most valuable shot",
       "most valuable" in hurt_hints["1 Riptide"])
c.true("...and the points it quotes rise as the Riptide is worn down",
       quoted_points(hurt_hints["1 Riptide"]) > quoted_points(fresh_hints["1 Riptide"]) * 2)
c.true("...while the Fire Warriors' quoted value does not move",
       abs(quoted_points(hurt_hints["1 Strike Team"])
           - quoted_points(fresh_hints["1 Strike Team"])) < 0.6)
rip2.models[0].current_wounds = rip2.models[0].profile.wounds

# Rule 05.03/05.04 ordering. Meganobz because they have 3 wounds each, so
# "one model" and "one wound" are distinguishable.
nobz = build_squad(orks.MEGANOBZ, "Player 2", unit_index=1)
each = nobz.models[0].profile.wounds
c.true("the scene: Meganobz have more than one wound apiece", each > 1)
c.true("a fresh unit needs a full model's wounds to lose a model",
       abs(damage_estimate.models_destroyed_by(nobz, each) - 1.0) < 1e-9)
c.true("...and half that kills half a model",
       abs(damage_estimate.models_destroyed_by(nobz, each / 2.0) - 0.5) < 1e-9)
nobz.models[1].current_wounds = 1
c.true("a wounded model is spent first, so one wound kills a whole model"
       " (05.04 step 1)",
       abs(damage_estimate.models_destroyed_by(nobz, 1.0) - 1.0) < 1e-9)
c.true("...and the wounds beyond it fall on a fresh model at its full value",
       abs(damage_estimate.models_destroyed_by(nobz, 1.0 + each) - 2.0) < 1e-9)

# 05.03: an attached unit's bodyguards soak before its CHARACTER, so a
# CHARACTER's larger wound pool does not slow the first kills down.
mob = build_squad(orks.BOYZ, "Player 2", unit_index=1)
c.true("a mob loses a rank-and-file model per wound, not a leader's worth",
       abs(damage_estimate.models_destroyed_by(mob, 1.0) - 1.0) < 1e-9)

c.true("nothing is destroyed by zero wounds",
       damage_estimate.models_destroyed_by(riptide, 0.0) == 0.0)


# ---------------------------------------------------------------------------
# 8. The unit's own ANTI-TANK RULE was worth nothing to the estimate
#
# Same report, third layer (user: "mal abgesehen von den remaining wounds,
# haetten die panzaknacker auch auf den riptide schiessen sollen, auch wenn er
# volle lebenspunkte gehabt haette... noch dazu haben sie anti tank regeln,
# also die entscheidung war auf allen ebenen falsch").
#
# The points-per-wound conversion was right; its INPUT was not. Tankbustas'
# Tank Hunters is +1 to Hit and +1 to Wound against a MONSTER or VEHICLE unit
# - roughly double the output, and the entire reason the unit counts as
# anti-tank - and expected_wounds() applied neither. So the estimate described
# a Rokkit team as though its special rule did not exist, which is exactly the
# half of "why is it shooting infantry" that section 7's wound fix does not
# touch.
#
# The multi-damage half of the same question was ALREADY right and is pinned
# here so it stays that way: D3 damage against 1-wound Fire Warriors is capped
# at 1 (see expected_wounds()'s effective_damage).
# ---------------------------------------------------------------------------

print()
print("8. the unit's own anti-tank rule")

rok_squad = build_squad(orks.TANKBUSTAS, "Player 2", unit_index=1)
rok_squad.name = "2 Tankbustas"
shooter = rok_squad.models[0]
rokkit = next(w for m in rok_squad.models for w in m.weapons
              if w.weapon_type == "ranged" and w.damage > 1)

monsters = {
    "Riptide": build_squad(tau_empire.RIPTIDE_BATTLESUIT, "Player 1", unit_index=1),
    "Ghostkeel": build_squad(tau_empire.GHOSTKEEL_BATTLESUIT, "Player 1", unit_index=1),
    "Devilfish": build_squad(tau_empire.DEVILFISH, "Player 1", unit_index=1),
}
infantry = {
    "Strike Team": build_squad(tau_empire.STRIKE_TEAM, "Player 1", unit_index=1),
    "Breacher Team": build_squad(tau_empire.BREACHER_TEAM, "Player 1", unit_index=1),
    "Kroot": build_squad(tau_empire.KROOT_CARNIVORES, "Player 1", unit_index=1),
}

c.true("the scene: the squad actually has Tank Hunters",
       shooter.profile.tank_hunters)
c.true("the scene: its rokkit is a multi-damage weapon", rokkit.damage > 1)
c.true("the scene: the vehicles read as MONSTER/VEHICLE and the infantry does not",
       all(squad_module.is_monster_or_vehicle_unit(t) for t in monsters.values())
       and not any(squad_module.is_monster_or_vehicle_unit(t) for t in infantry.values()))

for name, target in monsters.items():
    c.true(f"Tank Hunters improves both rolls against {name}",
           damage_estimate.attack_modifiers(shooter, target) == (-1, -1))
for name, target in infantry.items():
    c.true(f"...and does nothing against {name}",
           damage_estimate.attack_modifiers(shooter, target) == (0, 0))


def without_modifiers(fn):
    """Run fn() with attack_modifiers() neutralised - the pre-change estimate."""
    real = damage_estimate.attack_modifiers
    damage_estimate.attack_modifiers = lambda m, d, melee=False: (0, 0)
    try:
        return fn()
    finally:
        damage_estimate.attack_modifiers = real


print(f"    {'target':16s} {'before':>8s} {'after':>8s}")
for name, target in list(monsters.items()) + list(infantry.items()):
    before = without_modifiers(lambda t=target: observation.damage_value(rok_squad, t))
    after = observation.damage_value(rok_squad, target)
    print(f"    {name:16s} {before:8.1f} {after:8.1f}")
    if name in monsters:
        c.true(f"{name} is worth substantially more once the rule counts",
               after > before * 1.8)
    else:
        c.true(f"{name} is untouched by an anti-VEHICLE rule",
               abs(after - before) < 1e-9)

# The decision the user watched go wrong: every vehicle ahead of every body.
worst_vehicle = min(observation.damage_value(rok_squad, t) for t in monsters.values())
best_infantry = max(observation.damage_value(rok_squad, t) for t in infantry.values())
c.true("every MONSTER/VEHICLE now outranks every infantry squad for this unit",
       worst_vehicle > best_infantry)
c.true("...and it did NOT before, which is the reported bug",
       without_modifiers(lambda: min(observation.damage_value(rok_squad, t)
                                     for t in monsters.values()))
       <= without_modifiers(lambda: max(observation.damage_value(rok_squad, t)
                                        for t in infantry.values())))

# A unit WITHOUT the rule must be completely unaffected by any of this.
plain = build_squad(orks.FLASH_GITZ, "Player 2", unit_index=1)
c.true("a squad without Tank Hunters gets no modifiers",
       damage_estimate.attack_modifiers(plain.models[0], monsters["Riptide"]) == (0, 0))
c.true("...and its valuation is unchanged",
       abs(observation.damage_value(plain, monsters["Riptide"])
           - without_modifiers(lambda: observation.damage_value(plain, monsters["Riptide"]))) < 1e-9)

# The multi-damage half, pinned: D3 against 1-wound models is capped at 1.
prof_inf, _ = damage_estimate.defender_soak(infantry["Strike Team"])
prof_mon, _ = damage_estimate.defender_soak(monsters["Riptide"])
c.true("multi-damage is wasted on 1-wound infantry (already modelled)",
       min(rokkit.damage, prof_inf.wounds) == 1 and prof_inf.wounds == 1)
c.true("...and lands in full on a multi-wound target",
       min(rokkit.damage, prof_mon.wounds) == rokkit.damage)

# The defender's side of the same hook, so this does not only count our buffs.
drone_team = build_squad(tau_empire.STRIKE_TEAM, "Player 1", unit_index=1,
                         gear={"Fire Warrior Shas'ui": ["Guardian Drone"]})
c.true("the scene: the Guardian Drone is actually on the unit",
       squad_module.squad_has_guardian_drone(drone_team))
c.true("a Guardian Drone makes the unit harder to wound in the estimate too",
       damage_estimate.attack_modifiers(shooter, drone_team) == (0, 1))
c.true("...and that lowers what shooting it is worth",
       observation.damage_value(rok_squad, drone_team)
       < observation.damage_value(rok_squad, infantry["Strike Team"]))

# Rules 05.01/05.02: an unmodified 1 always fails, so no modifier stack can
# push a roll past 5/6. Only reachable now that modifiers are honoured.
c.true("a hit roll can never beat 5/6 however good the modifiers",
       abs(damage_estimate._threshold_chance(2 - 3) - 5.0 / 6.0) < 1e-9)
c.true("...and neither can a wound roll",
       abs(damage_estimate._threshold_chance(1) - 5.0 / 6.0) < 1e-9)
c.true("...while an impossible roll is still zero",
       damage_estimate._threshold_chance(7) == 0.0)

c.finish()
