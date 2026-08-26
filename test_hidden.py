"""Rule 13.09 (Hidden) - the whole mechanic, plus the reported bug.

WHY THIS SUITE EXISTS
---------------------
There was no dedicated Hidden test at all, which is most of why the bug below
survived: the arithmetic in status_effects.is_hidden() is fine and passes in
isolation, so nothing in the repo ever exercised the OTHER half - the shooting
controller's bookkeeping that tells it a unit has fired.

User report, two halves of one cause:
  "teste mal bitte ob die hidden-mechanik funktioniert. in einem game gerade
   scheint das nicht zu funktionieren."
  "und schau mal bitte, dass das HD label verschwindet, wenn die einheit
   geschossen hat. dann ist man nicht mehr hidden. dann sollte das label auch
   verschwinden."

Cause: main.py's Next Phase button calls shooting_controller.cancel()
unconditionally (a deliberate "abandon and move on" design for shooting), and
cancel() skipped the rule-13.09 bookkeeping entirely. So the ordinary human
sequence "fire the main gun, don't bother with the pistol, click Next Phase"
left the unit recorded as never having shot - it stayed Hidden, kept its HD
label, and stayed unshootable from beyond its detection range.

Section 5 reproduces exactly that, with an A/B against the pre-fix behaviour.
"""

import testkit as tk
from game import status_effects
from game.factions.orks import BOYZ, TANKBUSTAS, TRUKK
from game.factions.tau_empire import STRIKE_TEAM
from game.terrain import DENSE, LIGHT, Obstacle, TerrainArea

c = tk.Checks("rule 13.09 Hidden")


def dense_area(x=20.0, y=20.0, w=30.0, h=8.0):
    return TerrainArea([Obstacle(x, y, w, h, category=DENSE)])


def scene(attacker=TANKBUSTAS, target=STRIKE_TEAM, gap=6.0, owner="Player 2"):
    """Attacker inside a big Dense ruin; both sides two turns in, so the
    "this turn or the previous one" window has room on both sides."""
    s = tk.shooting_scene(attacker, target, attacker_owner=owner, gap=gap)
    area = dense_area()
    s["shooting"].terrain_areas = [area]
    s["area"] = area
    s["turn"].player_turn_count = {"Player 1": 2, "Player 2": 2}
    return s


def all_hidden(squad, s):
    return all(
        status_effects.is_hidden(m, [s["area"]], s["turn"],
                                 s["shooting"].last_ranged_attack_turn)
        for m in squad.models
    )


# --------------------------------------------------------------- 1. keywords

s = scene()
unit, area, tt, sc = s["attacker"], s["area"], s["turn"], s["shooting"]

c.true("every Tankbusta stands inside the dense area",
       all(area.overlaps_model(m) for m in unit.models))
c.true("INFANTRY in a dense area with no shot fired is Hidden", all_hidden(unit, s))

# A VEHICLE in the very same footprint is not - 13.09 lists INFANTRY/BEASTS/
# SWARM, notably NOT MOBILE (unlike 13.06's dense-movement exception).
truck = tk.build(TRUKK, "Player 2", name="Trukk")
for m in truck.models:
    m.x_in, m.y_in = 20.0, 20.0
c.true("the Trukk really is in the same dense area",
       all(area.overlaps_model(m) for m in truck.models))
c.eq("a VEHICLE in dense terrain is NOT Hidden", all_hidden(truck, s), False)

# --------------------------------------------------------- 2. dense terrain

light = TerrainArea([Obstacle(20.0, 20.0, 30.0, 8.0, category=LIGHT)])
c.eq("Light terrain does not hide (13.09 needs a Dense feature)",
     status_effects.is_hidden(unit.models[0], [light], tt, {}), False)
c.eq("no terrain at all does not hide",
     status_effects.is_hidden(unit.models[0], [], tt, {}), False)

far = tk.build(BOYZ, "Player 2", name="Boyz far")
for i, m in enumerate(far.models):
    m.x_in, m.y_in = 20.0 + i, 60.0  # well clear of the ruin
c.eq("INFANTRY outside the dense area is not Hidden", all_hidden(far, s), False)

# ------------------------------------------------- 3. the "did it shoot" window

# 13.09: hidden while its unit "made no ranged attacks this turn or the
# previous one". player_turn_count is per player, so these are that owner's
# own turn numbers.
window = [
    (None, True,  "never shot"),
    (2,    False, "shot THIS turn"),
    (1,    False, "shot the PREVIOUS turn"),
    (0,    True,  "shot two turns ago"),
]
for last, want, label in window:
    ledger = {} if last is None else {unit: last}
    got = all(status_effects.is_hidden(m, [area], tt, ledger) for m in unit.models)
    c.eq(f"turn 2, {label} -> hidden={want}", got, want)

# ------------------------------------------------------ 4. detection + targeting

s = scene(gap=20.0)
shooter, hider, area, sc = s["target"], s["attacker"], s["area"], s["shooting"]
tokens = s["state"].tokens

gap = min(((a.x_in - b.x_in) ** 2 + (a.y_in - b.y_in) ** 2) ** 0.5
          for a in shooter.models for b in hider.models)
c.true(f"the shooter really is beyond 15\" (measured {gap:.1f}\")",
       gap > status_effects.DETECTION_RANGE_IN)
c.eq("a hidden model beyond 15\" is not detectable",
     status_effects.is_detectable(hider.models[0], shooter, [area], s["turn"],
                                  sc.last_ranged_attack_turn), False)
c.eq("and the unit is therefore not a legal target",
     sc._is_valid_target_squad(hider, tokens, attacking_squad=shooter,
                               shooting_type="Normal"), False)

# One visible model is enough to make the whole unit shootable again - Hidden
# is per model, and is_detectable() is asked of every model in turn.
hider.models[0].y_in = shooter.models[0].y_in + 4.0
c.true("a single model stepping into detection range makes it a legal target",
       sc._is_valid_target_squad(hider, tokens, attacking_squad=shooter,
                                 shooting_type="Normal"))
hider.models[0].y_in = 20.0

# Close the distance and it becomes a legal target again.
for m in shooter.models:
    m.y_in = 30.0
c.true("within 15\" the same hidden unit IS a legal target",
       sc._is_valid_target_squad(hider, tokens, attacking_squad=shooter,
                                 shooting_type="Normal"))

# House rule (status_effects.CLOSE_DETECTION_RANGE_IN): a Dense feature standing
# on the model's OWN footprint tightens detection from 15" to 12".
wall = TerrainArea([Obstacle(20.0, 20.0, 1.0, 1.0, category=DENSE),
                    Obstacle(20.0, 34.0, 40.0, 20.0, category=DENSE)])
tight = tk.build(BOYZ, "Player 2", name="Boyz tight")
for m in tight.models:
    m.x_in, m.y_in = 20.0, 20.0
watcher = tk.build(STRIKE_TEAM, "Player 1", name="Watcher")
for m in watcher.models:
    m.x_in, m.y_in = 20.0, 33.5  # ~13.5" away: inside 15", outside 12"
c.true("a wall sits on the model's own footprint",
       status_effects._wall_on_own_footprint(tight.models[0], [wall]))
c.eq("with the house rule the 13.5\" observer cannot see it",
     status_effects.is_detectable(tight.models[0], watcher, [wall], tt, {}), False)
for m in watcher.models:
    m.y_in = 31.0  # ~11" - inside 12" too
c.true("but an 11\" observer can",
       status_effects.is_detectable(tight.models[0], watcher, [wall], tt, {}))

# --------------------------------------- 5. THE REPORTED BUG: Next Phase mid-shot

def fire_one_group(s):
    """Start an activation, resolve exactly ONE weapon group, and leave the
    rest unfired - the state a human is in when they click Next Phase."""
    sc, unit, target, tokens = s["shooting"], s["attacker"], s["target"], s["state"].tokens
    tk.script(*([6] * 80), default=6)
    sc.start_shooting(unit)
    sc.choose_target_squad(target)
    keys = [row[0] for row in sc.weapon_eligibility()]
    sc.choose_weapon(keys[0])
    for _ in range(60):
        if sc.dice_manager.is_pending:
            sc.dice_manager.acknowledge()
            sc.on_dice_acknowledged()
        elif sc.pending_damage_choice is not None:
            sc.choose_damage_model(sc.pending_damage_choice[0])
        else:
            break
    return keys


s = scene()
unit, area, sc, tt = s["attacker"], s["area"], s["shooting"], s["turn"]
keys = fire_one_group(s)
c.true("the fixture unit really has more than one weapon group", len(keys) > 1)
c.eq("mid-activation, more weapon groups are still open", sc.state, "choosing_weapon")
c.true("it has actually fired a group", sc._fired_this_activation)
c.true("still Hidden mid-activation (nothing has closed the activation yet)",
       all_hidden(unit, s))

sc.cancel()  # <- exactly what main.py's Next Phase button does
c.eq("after Next Phase the shot is on the ledger",
     sc.last_ranged_attack_turn.get(unit), tt.turn_number_for(unit.owner))
c.eq("the unit is no longer Hidden", all_hidden(unit, s), False)
c.eq("and the HD label is gone",
     status_effects.active_effects(unit.models[0], [area], tt,
                                   sc.last_ranged_attack_turn), [])

# A/B: the pre-fix world is cancel() ignoring the fact that a group resolved.
s = scene()
unit, area, sc, tt = s["attacker"], s["area"], s["shooting"], s["turn"]
fire_one_group(s)
sc._fired_this_activation = False  # <- reproduces the old cancel(), which never asked
sc.cancel()
c.eq("A/B: pre-fix, the shot was never recorded",
     sc.last_ranged_attack_turn.get(unit), None)
c.eq("A/B: pre-fix, the unit stayed Hidden after shooting", all_hidden(unit, s), True)
c.eq("A/B: pre-fix, the HD label stayed on",
     status_effects.active_effects(unit.models[0], [area], tt,
                                   sc.last_ranged_attack_turn), ["hidden"])

# ------------------------------------- 6. cancelling WITHOUT firing costs nothing

s = scene()
unit, sc = s["attacker"], s["shooting"]
sc.start_shooting(unit)
sc.choose_target_squad(s["target"])
c.eq("opening the shooting UI is not yet a ranged attack",
     sc._fired_this_activation, False)
sc.cancel()
c.eq("open + pick target + Next Phase leaves the ledger untouched",
     sc.last_ranged_attack_turn.get(unit), None)
c.true("so a unit that never fired keeps Hidden", all_hidden(unit, s))

# ------------------------------------------- 7. the normal end is unchanged

s = scene()
unit, sc, tt = s["attacker"], s["shooting"], s["turn"]
tk.script(*([6] * 120), default=6)
sc.start_shooting(unit)
sc.choose_target_squad(s["target"])
for _ in range(6):
    keys = [row[0] for row in sc.weapon_eligibility()]
    if sc.state != "choosing_weapon" or not keys:
        break
    sc.choose_weapon(keys[0])
    for _ in range(60):
        if sc.dice_manager.is_pending:
            sc.dice_manager.acknowledge()
            sc.on_dice_acknowledged()
        elif sc.pending_damage_choice is not None:
            sc.choose_damage_model(sc.pending_damage_choice[0])
        else:
            break
c.eq("firing every group ends the activation on its own", sc.state, "idle")
c.eq("and records the shot, as it always did",
     sc.last_ranged_attack_turn.get(unit), tt.turn_number_for(unit.owner))
c.eq("that unit is not Hidden either", all_hidden(unit, s), False)

c.finish()
