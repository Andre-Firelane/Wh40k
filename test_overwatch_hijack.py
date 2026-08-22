"""Fire Overwatch (15.08/15.09) must not be hijacked by a normal activation.

User report: "der battle wagon hat overwatch eingesetzt (ki) und hat einfach
immer wieder mit den big shoota geschossen und auch auf 5en getroffen."

Both halves reproduced from logs/game_20260821_183516.log, whose Overwatch
reads: one `needed 6+` Big Shoota roll (correct, rule 15.09) followed by
three `needed 5+` rolls of the same 20 attacks (the Battlewagon's four
[RAPID FIRE 2] Big Shootas inside half range).

Three separate defects had to line up:
  1. can_shoot() enforced "it is the Shooting phase" but not "it is this
     unit's OWN Shooting phase" (rule 07.02), so a Player 2 unit could start
     a normal activation during Player 1's Shooting phase.
  2. start_shooting() overwrote a live reactive activation, replacing
     SNAP_SHOOTING with Normal - 6+ becomes 5+ and the weapon group comes
     back.
  3. start_shooting() never cleared _reactive, so a hijacked activation was
     never booked into shot_squad_ids/fired_weapon_types either, which is
     what made it repeat rather than happen once.

Fixing 1 exposed a fourth, latent one: a MULTI-group unit Overwatching then
had nothing to advance it past CHOOSING_WEAPON, so ai/agent_driver.py's
_handle_shooting() gained the same resume branch _handle_fight() already has.

Every group below carries an A/B probe. The pre-fix can_shoot is
reimplemented locally rather than toggled in the engine - without it, "the
AI could not restart the shot" would only prove the scene never tried.
"""

from testkit import (
    Checks, build, line_up, Log, RecordingDice, script, DecisionManager,
    GameState, TurnTracker, PHASES, PHASE_SHOOTING,
)
from game import shooting as sh
from game.command_points import CommandPointManager
from game.factions.orks import BATTLEWAGON, BATTLEWAGON_ADD_BIG_SHOOTAS, KILL_RIG
from game.factions.tau_empire import CRISIS_STARSCYTHE, STRIKE_TEAM
from game.overwatch import FireOverwatchController
from game.stratagems import StratagemController

c = Checks("Fire Overwatch hijack (15.08/15.09)")


def scene(shooter_sheet, shooter_choices=None, turn_owner="Player 1", gap=6.0,
          target_sheet=CRISIS_STARSCYTHE):
    """Ork shooter (Player 2) vs T'au target (Player 1), Shooting phase.

    turn_owner defaults to Player 1 - i.e. the reported situation, an
    Overwatch fired during the OPPONENT's turn."""
    state = GameState()
    shooter = build(shooter_sheet, "Player 2", name="2 Shooter 1", choices=shooter_choices)
    target = build(target_sheet, "Player 1", name="1 Target 1")
    line_up(shooter, x=20.0, y=20.0)
    line_up(target, x=20.0, y=20.0 + gap)
    for squad in (shooter, target):
        for model in squad.models:
            state.add_token(model)
    tt = TurnTracker(first_player=turn_owner)
    tt.phase_index = PHASES.index(PHASE_SHOOTING)
    tt.turn_owner = turn_owner
    tt.set_active(turn_owner)
    log, dice, dec = Log(), RecordingDice(), DecisionManager()
    sc = sh.ShootingController(
        dice_manager=dice, turn_tracker=tt, all_tokens=state.tokens,
        decision_manager=dec, game_log=log, obstacles=[], player_name="Player 2",
    )
    cp = CommandPointManager(game_log=log)
    cp.cp["Player 2"] = 5
    ow = FireOverwatchController(
        StratagemController(game_log=log, command_points=cp), sc,
        all_tokens=state.tokens, turn_tracker=tt, game_log=log,
    )
    return dict(state=state, shooter=shooter, target=target, shooting=sc,
                overwatch=ow, dice=dice, log=log, turn=tt)


def prefix_can_shoot(sc, squad):
    """can_shoot() as it was BEFORE the fix: phase only, no owner check."""
    if squad is None or squad in sc.shot_squad_ids:
        return False
    if sc.turn_tracker is not None and sc.turn_tracker.phase != PHASE_SHOOTING:
        return False
    if not sh.available_shooting_types(squad, sc.all_tokens, sc.movement_controller):
        return False
    already = sc.fired_weapon_types.get(squad, set())
    return any(k not in already for k in sh._attack_groups(squad, one_shot_used=sc.one_shot_used))


def drain(sc, dice, limit=400):
    """Click through dice/damage the way main.py's loop does. Returns the
    first frame where nothing was pending (i.e. where the AI would run)."""
    for _ in range(limit):
        if dice.is_pending:
            dice.acknowledge()
            sc.on_dice_acknowledged()
            continue
        if sc.pending_damage_choice:
            sc.choose_damage_model(sc.pending_damage_choice[0])
            continue
        return [dict(state=sc.state, reactive=sc._reactive,
                     remaining=len(sc.remaining_weapon_types))]
    return []


BW_CHOICES = {"Battlewagon": {BATTLEWAGON_ADD_BIG_SHOOTAS: 1}}

# ---------------------------------------------------- 1. the reported scene
s = scene(BATTLEWAGON, BW_CHOICES)
sc, wagon, target, ow, dice = s["shooting"], s["shooter"], s["target"], s["overwatch"], s["dice"]

c.true("scene: the Battlewagon has exactly one attack group",
        len(sh._attack_groups(wagon)) == 1)
c.true("scene: 4x Big Shoota",
        sum(w.name == "Big Shoota" for w in wagon.models[0].weapons) == 4)
c.true("scene: it is Player 1's turn", s["turn"].turn_owner == "Player 1")
c.true("scene: the shooter belongs to Player 2", wagon.owner == "Player 2")

ow.offer("Player 1")
c.true("Overwatch is offered to Player 2", wagon in ow.eligible_squads())
ow.choose_unit(wagon)
c.true("the snap shot opens as Snap Shooting", sc.shooting_type == sh.SNAP_SHOOTING)
c.true("...and is flagged reactive", sc._reactive is True)

script(*([6] * 40), default=2)
sc.choose_target_squad(target)
sc.choose_weapon(sc.weapon_eligibility()[0][0])
label, _ = dice.last_roll
c.true("the hit roll is a Snap Shot Hit Roll", "Snap Shot Hit Roll" in label)
c.true("...on an unmodified 6 (rule 15.09)", dice.success_threshold == 6)
c.true("...with the reported 20 attacks", "20 attack(s)" in label)

# THE FIX: no normal activation may start for this unit in Player 1's phase.
c.true("can_shoot() says no mid-snap-shot (rule 07.02)", sc.can_shoot(wagon) is False)
c.true("A/B: the pre-fix can_shoot() said yes", prefix_can_shoot(sc, wagon) is True)

drain(sc, dice)
c.true("the snap shot ends after its one group", sc.state == sh.IDLE)
c.true("can_shoot() still says no afterwards", sc.can_shoot(wagon) is False)
c.true("A/B: the pre-fix can_shoot() said yes afterwards too",
        prefix_can_shoot(sc, wagon) is True)
c.true("exactly one hit roll was made",
        sum("Hit Roll" in l for l, _ in dice.rolled) == 1)
c.true("no roll used the normal 5+ threshold",
        all("Snap Shot" in l for l, _ in dice.rolled if "Hit Roll" in l))

before = sc.shooting_type
sc.start_shooting(wagon)
c.true("start_shooting() is refused, so nothing reopens",
        sc.active_squad is None and sc.shooting_type == before)

# ------------------------------------- 2. A/B: the hijack, with fix bypassed
s = scene(BATTLEWAGON, BW_CHOICES)
sc, wagon, target, ow, dice = s["shooting"], s["shooter"], s["target"], s["overwatch"], s["dice"]
# Saves all pass here (default=6) on purpose: the point of this group is the
# SECOND roll, and a wiped-out target would make _begin_resolution() skip it.
script(*([6] * 40), default=6)
ow.offer("Player 1")
ow.choose_unit(wagon)
sc.choose_target_squad(target)
sc.choose_weapon(sc.weapon_eligibility()[0][0])
drain(sc, dice)
c.true("A/B setup: the target survived the first shot",
        any(m.current_wounds > 0 for m in target.models))
# Reach around can_shoot() exactly the way the old code effectively did.
sc.active_squad = wagon
sc.target_squad = None
sc.shooting_type = sh.NORMAL_SHOOTING
sc._enter_target_selection()
sc.choose_target_squad(target)
weapons = sc.weapon_eligibility()
c.true("A/B: the same weapon group is offered a second time", bool(weapons))
if weapons:
    sc.choose_weapon(weapons[0][0])
    c.true("A/B: and it hits on 5+, exactly as reported", dice.success_threshold == 5)
    c.true("A/B: with the same 20 attacks", "20 attack(s)" in dice.last_roll[0])

# ----------------------------- 3. start_shooting() vs a live reactive shot
# Force the unit's OWN phase so can_shoot() cannot be what refuses - the
# guard under test is the reactive one.
s = scene(BATTLEWAGON, BW_CHOICES, turn_owner="Player 2")
sc, wagon = s["shooting"], s["shooter"]
c.true("setup: can_shoot() is true in the unit's own phase", sc.can_shoot(wagon) is True)
sc.start_snap_shooting(wagon)
c.true("setup: a reactive activation is live",
        sc._reactive is True and sc.shooting_type == sh.SNAP_SHOOTING)
sc.start_shooting(wagon)
c.true("start_shooting() leaves the reactive activation alone",
        sc.shooting_type == sh.SNAP_SHOOTING and sc._reactive is True)

# ------------------------------------ 4. _reactive is cleared on a real start
s = scene(BATTLEWAGON, BW_CHOICES, turn_owner="Player 2")
sc, wagon = s["shooting"], s["shooter"]
sc._reactive = True      # stale leftover, as start_snap_shooting() would leave
sc.active_squad = None   # ...but nothing in flight, so the guard lets us in
sc.start_shooting(wagon)
c.true("a normal activation is never flagged reactive", sc._reactive is False)
c.true("...and it did open", sc.active_squad is wagon)

# ---------------------------------- 5. the normal path is untouched
s = scene(KILL_RIG, turn_owner="Player 2", target_sheet=STRIKE_TEAM)
sc, rig, target, dice = s["shooting"], s["shooter"], s["target"], s["dice"]
c.true("scene: the Kill Rig has several attack groups", len(sh._attack_groups(rig)) >= 3)
script(*([6] * 400), default=6)
sc.start_shooting(rig)
if sc.state == sh.CHOOSING_SHOOTING_TYPE:
    sc.choose_shooting_type(sc.available_types[0])
c.true("its own activation opens normally", sc.state == sh.CHOOSING_TARGET)
sc.choose_target_squad(target)
sc.choose_weapon(sc.weapon_eligibility()[0][0])
idle = drain(sc, dice)
c.true("after group 1 it waits at CHOOSING_WEAPON",
        bool(idle) and idle[0]["state"] == sh.CHOOSING_WEAPON)
c.true("...with groups left", bool(idle) and idle[0]["remaining"] >= 1)
c.true("...and can_shoot() still allows the restart the AI relies on",
        sc.can_shoot(rig) is True)
c.true("...the fired group is booked", len(sc.fired_weapon_types.get(rig, set())) == 1)

# ------------------------- 6. multi-group snap shot completes, all snap rolls
s = scene(KILL_RIG, target_sheet=STRIKE_TEAM)
sc, rig, target, ow, dice = s["shooting"], s["shooter"], s["target"], s["overwatch"], s["dice"]
script(*([6] * 600), default=6)
ow.offer("Player 1")
ow.choose_unit(rig)
c.true("a multi-group unit opens with all its groups", len(sc.remaining_weapon_types) >= 3)
sc.choose_target_squad(target)
sc.choose_weapon(sc.weapon_eligibility()[0][0])
resumes = 0
for _ in range(600):
    if dice.is_pending:
        dice.acknowledge()
        sc.on_dice_acknowledged()
        continue
    if sc.pending_damage_choice:
        sc.choose_damage_model(sc.pending_damage_choice[0])
        continue
    if sc.state == sh.IDLE:
        break
    if sc.state == sh.CHOOSING_WEAPON and sc.current_group is None:
        resumes += 1
        weapons = sc.weapon_eligibility()
        if weapons:
            sc.choose_weapon(weapons[0][0])
        else:
            sc.stop_shooting()
        continue
    break
c.true("the multi-group snap shot finishes instead of stalling", sc.state == sh.IDLE)
c.true("...via the resume branch", resumes >= 1)
hit_rolls = [l for l, _ in dice.rolled if "Hit Roll" in l]
c.true("every hit roll in it stayed a Snap Shot",
        bool(hit_rolls) and all("Snap Shot" in l for l in hit_rolls))
c.true("...and it was never booked as the unit's real activation",
        rig not in sc.shot_squad_ids and not sc.fired_weapon_types.get(rig))

# ------------------------- 7. the AI's own resume branch, with no agent calls
import ai.agent_driver as ad


class ExplodingAgent:
    def decide(self, *a, **k):
        raise AssertionError("the resume branch must not consult the agent")


class Memory:
    declined_shoot = set()


s = scene(KILL_RIG, target_sheet=STRIKE_TEAM)
sc, rig, target, ow, dice = s["shooting"], s["shooter"], s["target"], s["overwatch"], s["dice"]
script(*([6] * 600), default=6)
ow.offer("Player 1")
ow.choose_unit(rig)
sc.choose_target_squad(target)
sc.choose_weapon(sc.weapon_eligibility()[0][0])
for _ in range(400):
    if dice.is_pending:
        dice.acknowledge()
        sc.on_dice_acknowledged()
        continue
    if sc.pending_damage_choice:
        sc.choose_damage_model(sc.pending_damage_choice[0])
        continue
    break
c.true("setup: parked at CHOOSING_WEAPON mid-Overwatch", sc.state == sh.CHOOSING_WEAPON)
before_target = sc.target_squad
# ExplodingAgent is the assertion: the resume branch must fire the next
# weapon group by itself. Without it, _handle_shooting() falls through to its
# shoot loop, start_shooting() hijacks the snap shot, and the agent gets
# consulted - caught here rather than crashing the suite so the A/B run
# reports a failure like every other check.
try:
    acted = ad._handle_shooting(
        ExplodingAgent(), Memory(), "Player 2", s["state"].tokens, sc, None,
        lambda *a, **k: None,
    )
except AssertionError:
    acted = "consulted the agent (hijack path)"
c.true("_handle_shooting() acts on it without consulting the agent", acted is True)
c.true("...it fired the next group rather than re-picking a target (rule 10.02)",
        sc.target_squad is before_target)
c.true("...still Snap Shooting", sc.shooting_type == sh.SNAP_SHOOTING)
c.true("...and it did not start a fresh activation", sc.active_squad is rig)

# ------------- 8. the mirror case: a HUMAN Overwatch must still work
# Fix 1 tightens can_shoot(), and start_snap_shooting() deliberately bypasses
# it - so the same Overwatch fired the other way round (Player 1 reacting in
# Player 2's turn) has to be unaffected.
s = scene(BATTLEWAGON, BW_CHOICES, turn_owner="Player 2")
sc, wagon, target = s["shooting"], s["shooter"], s["target"]
# Swap roles: the T'au unit reacts during the Ork turn.
ow = FireOverwatchController(
    StratagemController(game_log=s["log"],
                        command_points=CommandPointManager(game_log=s["log"])), sc,
    all_tokens=s["state"].tokens, turn_tracker=s["turn"], game_log=s["log"],
)
ow.stratagem_controller.command_points.cp["Player 1"] = 5
ow.offer("Player 2")
c.true("a human unit is offered Overwatch in the AI's turn", target in ow.eligible_squads())
ow.choose_unit(target)
c.true("...and its snap shot opens", sc.active_squad is target)
c.true("...as Snap Shooting", sc.shooting_type == sh.SNAP_SHOOTING)
script(*([6] * 60), default=6)
sc.choose_target_squad(wagon)
weapons = sc.weapon_eligibility()
c.true("...with weapons to fire", bool(weapons))
if weapons:
    sc.choose_weapon(weapons[0][0])
    c.true("...on an unmodified 6", s["dice"].success_threshold == 6)
c.true("but it still cannot start a NORMAL activation in the AI's turn",
        sc.can_shoot(target) is False)

c.finish()
