"""game/battle_stats.py - the numbers behind the Unit Statistics overlay.

Driven through the REAL controllers wherever a number is produced by them,
because the three seams this feature hangs on are all mid-sequence and none of
them is reachable by calling the ledger directly:

  * a volley that misses entirely never builds a DamageAllocationSession, so
    the tanking number has to come out of _finish_group() - that is the single
    most important thing a defender can be credited with and the one case a
    test written against the save results would silently skip;
  * Feel No Pain and damage reduction happen inside the session;
  * the distance is measured from move_start, which only exists during a move.
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import testkit as tk
from testkit import Checks
from game import battle_stats, weapons
from game.dice_notation import D3, D6
from game.movement import MovementController
from game.factions import aeldari, necrons, orks

c = Checks("battle statistics")


def body_of(func):
    """A function's source with its docstring removed - a guard that matches
    the prose explaining it is not a guard (this repo has paid for that five
    times)."""
    import inspect, ast, textwrap
    src = textwrap.dedent(inspect.getsource(func))
    tree = ast.parse(src).body[0]
    if (tree.body and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)):
        tree.body = tree.body[1:]
    return ast.unparse(tree)


def run_shooting(faces, attacker_sheet=aeldari.GUARDIAN_DEFENDERS,
                 target_sheet=orks.BOYZ, gap=6.0):
    """One full shooting activation with every die showing `faces`, recorded
    into a fresh ledger. Returns (ledger, attacker, target)."""
    ledger = battle_stats.BattleStats()
    battle_stats.CURRENT = ledger
    try:
        tk.script(default=faces)
        scene = tk.shooting_scene(attacker_sheet, target_sheet,
                                  attacker_owner="Player 2", gap=gap)
        s, dice = scene["shooting"], scene["dice"]
        s.start_shooting(scene["attacker"])
        if s.state == "choosing_shooting_type":
            s.choose_shooting_type(s.available_types[0])
        s.choose_target_squad(scene["target"])
        if s.state == "choosing_weapon":
            s.choose_weapon(s.remaining_weapon_types[0])
        for _ in range(300):
            if dice.is_pending:
                dice.acknowledge()
                s.on_dice_acknowledged()
            elif s.pending_damage_choice:
                s.choose_damage_model(s.pending_damage_choice[0])
            else:
                break
        return ledger, scene["attacker"], scene["target"]
    finally:
        battle_stats.CURRENT = None


def run_melee(faces, attacker_sheet=aeldari.HOWLING_BANSHEES, target_sheet=orks.BOYZ):
    """One full melee activation with every die showing `faces`.

    The melee half is driven separately and not assumed to follow from the
    ranged one: game/fight.py is a SECOND wiring of the same seams, and an A/B
    probe that unhooked only the melee attacker went unnoticed until this
    existed."""
    ledger = battle_stats.BattleStats()
    battle_stats.CURRENT = ledger
    try:
        tk.script(*([faces] * 400), default=faces)
        scene = tk.fight_scene(attacker_sheet, target_sheet, attacker_owner="Player 2")
        f, dice, decision = scene["fight"], scene["dice"], scene["decision"]
        # The unit has to be SELECTED to fight before it has weapon options -
        # rule 12.04's alternating selection is a real step, and skipping it
        # leaves weapon_eligibility() empty and the whole drive vacuous.
        f.select_to_fight(scene["attacker"])
        options = f.weapon_eligibility()
        if not options:
            return ledger, scene["attacker"], scene["target"]
        f.choose_weapon(options[0][0])
        for _ in range(400):
            if dice.is_pending:
                dice.acknowledge()
                f.on_dice_acknowledged()
            elif f.pending_damage_choice:
                f.choose_damage_model(f.pending_damage_choice[0])
            elif decision.is_pending:
                tk.pick_option(decision, decision.options[0]["label"])
            else:
                break
        return ledger, scene["attacker"], scene["target"]
    finally:
        battle_stats.CURRENT = None


def got(ledger, squad, field):
    record = ledger.record(squad.name)
    return getattr(record, field) if record else 0


# ======================================================= 1. what a weapon COULD do
print("\n=== 1. max_damage: the printed notation, never the placeholder ===")

# The reported example: "bei brightlance schuss zb. 8".
bright = weapons.BrightLanceProfile
c.eq("a Bright Lance shot could do 8 (printed D6+2)", weapons.max_damage(bright), 8)
c.true("...and its printed characteristic really IS a notation",
       bright.damage_notation is not None)


class _Plain(weapons.WeaponProfile):
    damage = 3
    damage_notation = None


class _Notated(weapons.WeaponProfile):
    damage = 3           # the placeholder: the MEAN of a D6, not its maximum
    damage_notation = D6()


class _TwoDice(weapons.WeaponProfile):
    damage = 7
    damage_notation = D6(dice=2)


c.eq("a flat Damage characteristic is its own maximum", weapons.max_damage(_Plain), 3)
c.eq("a D6 is 6, not the 3 stored beside it", weapons.max_damage(_Notated), 6)
c.eq("a 2D6 is 12", weapons.max_damage(_TwoDice), 12)
c.eq("a D3 is 3", weapons.max_damage(type("X", (weapons.WeaponProfile,),
                                          {"damage": 9, "damage_notation": D3()})), 3)

# The measurement the docstring rests on. If the placeholder were reliable
# there would be no reason for this function to exist at all.
_mismatch = _total = 0
for _name in dir(weapons):
    _obj = getattr(weapons, _name)
    if isinstance(_obj, type) and issubclass(_obj, weapons.WeaponProfile) \
            and _obj.damage_notation is not None:
        _total += 1
        if _obj.damage != weapons.max_damage(_obj):
            _mismatch += 1
c.true("the guard is live - it found notation weapons to check", _total >= 40)
c.true("...and the plain int really is unreliable (most of them differ)",
       _mismatch > _total / 2)


# ============================================ 2. wounds dealt, and points pro rata
print("\n=== 2. best killing units ===")

ledger, attacker, target = run_shooting(6)      # everything hits, wounds, no save
wounds = got(ledger, attacker, "wounds_dealt")
c.true("a volley that lands credits the ATTACKER with wounds", wounds > 0)
c.eq("...and the defender is credited with none",
     got(ledger, target, "wounds_dealt"), 0)

# Pro rata: the share of the target's own starting wounds, times its points.
start = battle_stats.starting_wounds(target)
c.true("the target's starting wounds are read off models + destroyed_models",
       start == sum(m.profile.wounds for m in list(target.models) + list(target.destroyed_models)))
expected = (wounds / start) * target.points
c.true("points are that share of the target's cost (%.1f)" % expected,
       abs(got(ledger, attacker, "points_dealt") - expected) < 0.01)
c.true("...which is less than the whole unit, since it survived",
       got(ledger, attacker, "points_dealt") < target.points)

# THE MELEE HALF, driven for real. game/fight.py wires the same three seams a
# second time, and only running the ranged one leaves that wiring unmeasured -
# which an A/B probe proved by unhooking it with every check still green.
mledger, mattacker, mtarget = run_melee(6)
c.true("a melee activation credits the ATTACKER with wounds too",
       got(mledger, mattacker, "wounds_dealt") > 0)
c.true("...and scores points for them", got(mledger, mattacker, "points_dealt") > 0)
mledger, mattacker, mtarget = run_melee(1)
c.true("a melee that misses entirely credits the DEFENDER",
       got(mledger, mtarget, "prevented") > 0)
c.eq("...and the attacker with nothing", got(mledger, mattacker, "wounds_dealt"), 0)

# An unpriced target must not crash the ranking - Squad.points may be None.
unpriced = tk.build(orks.BOYZ, "Player 1", name="1 Unpriced 1")
unpriced.points = None
led = battle_stats.BattleStats()
shooter = tk.build(aeldari.DARK_REAPERS, "Player 2", name="2 Shooter 1")
led.record_damage(shooter, unpriced.models[0], 3)
c.eq("an unpriced target still counts wounds", got(led, shooter, "wounds_dealt"), 3)
c.eq("...and scores no points rather than crashing", got(led, shooter, "points_dealt"), 0)

# Friendly fire is nobody's kill: [HAZARDOUS] and Deadly Demise hit your own.
led = battle_stats.BattleStats()
mine = tk.build(orks.BOYZ, "Player 1", name="1 Mine 1")
also_mine = tk.build(orks.BOYZ, "Player 1", name="1 Mine 2")
led.record_damage(mine, also_mine.models[0], 4)
c.eq("a wound on your OWN army credits nobody", got(led, mine, "wounds_dealt"), 0)

# An unnamed attacker (every ability-built MortalWoundAllocationSession) is
# counted as such rather than dropped, which is what makes the gap measurable.
led = battle_stats.BattleStats()
led.record_damage(None, also_mine.models[0], 5)
c.eq("a wound with no named attacker is counted as unattributed",
     led.unattributed_wounds, 5)


# ================================================ 3. what the defender turned aside
print("\n=== 3. best tanking units ===")

# THE CASE A TEST WRITTEN AT THE SAVE RESULTS WOULD MISS. With every die a 1
# nothing hits, so no DamageAllocationSession is ever built and
# _check_allocation_done() never runs - the credit has to come from
# _finish_group().
ledger, attacker, target = run_shooting(1)
missed_all = got(ledger, target, "prevented")
c.true("a volley that misses ENTIRELY still credits the defender", missed_all > 0)
c.eq("...and the attacker gets no wounds for it",
     got(ledger, attacker, "wounds_dealt"), 0)

# It is valued at what those attacks COULD have done, per attack.
shuriken = max(weapons.max_damage(w) for _m, w in
               [(m, w) for m in attacker.models for w in m.weapons
                if w.weapon_type == weapons.RANGED])
c.true("the value is a whole multiple of the weapon's maximum damage",
       abs(missed_all % shuriken) < 1e-6)

# ...and a volley that lands everything is turned aside by nothing.
ledger, attacker, target = run_shooting(6)
c.eq("a volley that lands entirely is prevented by nothing",
     got(ledger, target, "prevented"), 0)

# OVERKILL IS NOT PREVENTION. This is why the number counts ATTACKS that
# failed rather than damage points that went missing: a big-Damage weapon
# killing a one-wound model wastes most of its Damage, and crediting that
# waste would put cheap chaff at the top of the tanking table.
led = battle_stats.BattleStats()
chaff = tk.build(orks.GRETCHIN, "Player 1", name="1 Chaff 1")


class _Overkiller(weapons.WeaponProfile):
    name = "Overkiller"
    damage = 8
    damage_notation = D6(bonus=2)


led.record_attack_group(chaff, _Overkiller, attacks=4, landed=4)
c.eq("every attack landing means nothing was turned aside",
     got(led, chaff, "prevented"), 0)
led.record_attack_group(chaff, _Overkiller, attacks=4, landed=1)
c.eq("three attacks turned aside are worth 3 x 8", got(led, chaff, "prevented"), 24)

# Feel No Pain and damage reduction, which the user asked to be included,
# are counted where they happen rather than inferred as a leftover.
led = battle_stats.BattleStats()
led.record_prevented(chaff.models[0], 3)
c.eq("Feel No Pain / damage reduction add to the same number",
     got(led, chaff, "prevented"), 3)

c.true("record_prevented is reached from the Feel No Pain roll itself",
       "battle_stats.report_prevented" in
       open("game/feel_no_pain.py", encoding="utf-8").read())
c.true("...and from the one place every Damage reduction meets",
       "battle_stats.report_prevented" in
       open("game/damage_resolution.py", encoding="utf-8").read())


# ============================================================ 4. inches travelled
print("\n=== 4. fastest units ===")

led = battle_stats.BattleStats()
runner = tk.build(aeldari.WINDRIDERS, "Player 1", name="1 Runner 1")
led.notify_move(runner, None, 12.0)
led.notify_move(runner, "charge", 7.5)
led.notify_move(runner, "consolidate", 2.0)
c.eq("distance ACCUMULATES over the battle", got(led, runner, "distance_in"), 21.5)
c.true("every move type counts, not just the Movement phase - charge included",
       got(led, runner, "distance_in") > 12.0)

# Through the real controller: the distance is the FARTHEST single model, and
# it is read from move_start, which only exists mid-move.
squad = tk.build(orks.BOYZ, "Player 1", name="1 Movers 1")
tk.line_up(squad, x=10.0, y=30.0)
mc = MovementController(all_tokens=list(squad.models))
mc.selected_squad = squad
mc.start_move()
first, second = squad.models[0], squad.models[1]
first.x_in += 3.0
second.x_in += 5.0
c.eq("the real controller measures the farthest model, not the average",
     round(mc._farthest_moved(squad), 3), 5.0)

# ...and THROUGH confirm_move(), which is the only thing that proves the seam
# is really wired. Calling notify_move() by hand tests the ledger's addition
# and nothing else - an A/B probe that deleted the call site in movement.py
# left every check above green.
led = battle_stats.BattleStats()
battle_stats.CURRENT = led
try:
    # A three-model unit on purpose: tk.line_up() spreads ten Boyz wider than
    # rule 09.02's 9" limit, so confirm_move() would refuse before the seam
    # under test was ever reached - and the check would have failed for a
    # reason that has nothing to do with statistics.
    walkers = tk.build(aeldari.WINDRIDERS, "Player 1", name="1 Walkers 1")
    tk.line_up(walkers, x=10.0, y=40.0)
    mc2 = MovementController(all_tokens=list(walkers.models))
    mc2.selected_squad = walkers
    mc2.start_move()
    for model in walkers.models:
        model.x_in += 4.0
    mc2.confirm_move()
    confirm_errors = list(mc2.errors)
finally:
    battle_stats.CURRENT = None
# confirm_move() returns None either way - `errors` is this controller's
# success test, which is what the AI reads too. Asserting on the return value
# would be the "confirm() raised nothing, so it moved" false success CLAUDE.md
# lists as error class 6.
c.eq("...on a move the controller really did accept", confirm_errors, [])
c.true("the real confirm_move() reports the distance to the ledger",
       got(led, walkers, "distance_in") > 0)
c.eq("...and it is the distance actually travelled",
     round(got(led, walkers, "distance_in"), 2), 4.0)

# The [HEAVY] bookkeeping and the statistics read ONE definition of that -
# two copies would be two answers the moment either learned something.
c.true("rule 24.16's own bookkeeping goes through the same helper",
       "_farthest_moved(" in open("game/movement.py", encoding="utf-8").read())
_move_src = open("game/movement.py", encoding="utf-8").read()
c.eq("the distance formula exists exactly once",
     _move_src.count("** 2 + (model.y_in - start[1]) ** 2) ** 0.5"), 1)


# ================================================= 5. identity: names, and 19.01
print("\n=== 5. which unit a number belongs to ===")

led = battle_stats.BattleStats()
leader = tk.build(aeldari.FARSEER, "Player 1", name="1 Farseer 1")
bodyguard = tk.build(aeldari.GUARDIAN_DEFENDERS, "Player 1", name="1 Guardian Defenders 1")
# Rule 19.01's merge: attach() empties the leader squad and points it at the
# unit that now owns its models. A statistic recorded against the stale squad
# has to land on the live one.
leader.absorbed_into = bodyguard
led.notify_move(leader, None, 6.0)
c.eq("a merged-away squad's numbers land on the unit that absorbed it",
     got(led, bodyguard, "distance_in"), 6.0)
c.eq("...and nothing is stranded on the stale squad",
     led.record(leader.name), None)


# ================================================================ 6. the rankings
print("\n=== 6. the three rankings ===")

led = battle_stats.BattleStats()
squads = []
for i, (w, p, d) in enumerate(((10, 100.0, 5.0), (4, 40.0, 30.0), (7, 70.0, 12.0), (1, 9.0, 1.0))):
    s = tk.build(orks.BOYZ, "Player 1", name="1 Rank %d" % i)
    squads.append(s)
    r = led._record_for(s)
    r.wounds_dealt, r.points_dealt, r.distance_in = w, p, d
    r.prevented = float(w * 2)
enemy = tk.build(necrons.NECRON_WARRIORS, "Player 2", name="2 Other 1")
led._record_for(enemy).wounds_dealt = 999

c.eq("top_killers returns three, best first",
     [r.name for r in led.top_killers("Player 1")],
     ["1 Rank 0", "1 Rank 2", "1 Rank 1"])
c.eq("top_movers ranks by distance instead",
     [r.name for r in led.top_movers("Player 1")],
     ["1 Rank 1", "1 Rank 2", "1 Rank 0"])
c.eq("a ranking is per PLAYER - the other army does not appear",
     [r.name for r in led.top_killers("Player 2")], ["2 Other 1"])

# A unit with nothing to show is left out rather than padding the table with
# zeroes, which is what makes an empty table mean "nothing happened yet".
led2 = battle_stats.BattleStats()
led2._record_for(squads[0]).distance_in = 4.0
c.eq("a unit with a zero in that column is not listed",
     led2.top_killers("Player 1"), [])
c.eq("...but it is listed in the column it does have",
     [r.name for r in led2.top_movers("Player 1")], ["1 Rank 0"])

# Ties break on the name, so a table redrawn every frame does not shuffle.
led3 = battle_stats.BattleStats()
for name in ("1 B 1", "1 A 1"):
    s = tk.build(orks.BOYZ, "Player 1", name=name)
    led3._record_for(s).wounds_dealt = 5
c.eq("an exact tie is broken by name, not by insertion order",
     [r.name for r in led3.top_killers("Player 1")], ["1 A 1", "1 B 1"])


# ========================================================= 7. surviving a --load
print("\n=== 7. save and load ===")

led = battle_stats.BattleStats()
saved_squad = tk.build(orks.BOYZ, "Player 1", name="1 Keeper 1")
r = led._record_for(saved_squad)
r.wounds_dealt, r.points_dealt, r.prevented, r.distance_in = 12, 88.5, 140.0, 31.25
led.unattributed_wounds = 4

blob = led.save_state()
fresh = battle_stats.BattleStats()
c.eq("loading reports no problems", fresh.load_state(blob), [])
c.eq("wounds survive the round trip", got(fresh, saved_squad, "wounds_dealt"), 12)
c.eq("points survive", got(fresh, saved_squad, "points_dealt"), 88.5)
c.eq("prevented damage survives", got(fresh, saved_squad, "prevented"), 140.0)
c.eq("distance survives", got(fresh, saved_squad, "distance_in"), 31.25)
c.eq("the unattributed count survives", fresh.unattributed_wounds, 4)
c.eq("...and the record is still owned by the right player",
     fresh.record("1 Keeper 1").owner, "Player 1")

import json
c.true("the whole thing is JSON, like every other snapshot section",
       json.loads(json.dumps(blob)) == blob)

# An empty battle writes nothing, which is what keeps an untouched snapshot
# byte-identical to one written before this section existed.
c.eq("an untouched battle has no units to write",
     battle_stats.BattleStats().save_state()["units"], {})


# ========================================================== 8. nothing blocks
print("\n=== 8. a ledger, not a controller ===")

# These four names are what main.py's gates and test_event_chain_wiring.py's
# SS 6/10/11/12/17/20 fire on. A statistic that acquired one would start
# blocking a phase - and a statistic is never worth a stuck phase.
for name in ("is_busy", "pending_damage_choice", "choose_damage_model",
             "on_dice_acknowledged"):
    c.eq("BattleStats has no %s" % name,
         hasattr(battle_stats.BattleStats(), name), False)

c.true("the module-level ledger starts empty, so nothing records outside a battle",
       battle_stats.CURRENT is None)

# The reporting helpers must be no-ops without a battle: every unit test in
# this repo builds sessions and rolls Feel No Pain without ever wanting a
# resume, and a helper that assumed a ledger would take them all down.
battle_stats.report_damage(None, None, 3)
battle_stats.report_prevented(None, 3)
battle_stats.report_group(None, None)
battle_stats.report_move(None, None, 3.0)
c.true("reporting without a ledger does nothing and raises nothing", True)

c.finish()
