"""Core rule: a dice can never be re-rolled more than once.

Reproduces the reported turn (logs/game_20260808_213013.log, the Twin Fusion
Blaster shot at 2 Meganobz 1): a single-die Wound roll was re-rolled by
Command Re-roll (15.02) into a 2 - still a failure - and [TWIN-LINKED]
(24.38) then re-rolled that SAME die again into a 4, which wounded and
killed a Meganob. Every case below is the numbers from that log or the
other pairings that reach the same illegal double re-roll.
"""
from game import maps
from game import dice as dice_mod
from game.game_state import GameState
from game.dice import DiceManager, CHARGE_ROLL, WOUND_ROLL, HIT_ROLL
from game.decision import DecisionManager
from game.command_points import CommandPointManager
from game.command_reroll import CommandRerollController
from game.stratagems import StratagemController
from game.turn import TurnTracker, PHASES, PHASE_SHOOTING, PHASE_FIGHT
from game.shooting import ShootingController
from game.fight import FightController
from game.factions import build_squad
from game.factions.tau_empire import GHOSTKEEL_BATTLESUIT, BREACHER_TEAM, STEALTH_BATTLESUITS
from game.factions.orks import MEGANOBZ
from game.weapons import TwinFusionBlasterProfile, WeaponProfile, MELEE
from game.objectives import Objective
from game.terrain import TerrainArea, Obstacle, EXPOSED

m = maps.get('map2'); maps.apply_to_config(m)
checks, failed = 0, []


def ok(label, cond):
    global checks
    checks += 1
    if not cond:
        failed.append(label)
    print(("  PASS  " if cond else "  FAIL  ") + label)


# --------------------------------------------------------------- scripted dice
_scripted = []
_default = [None]  # what an unscripted die shows; None = its best face


def _scripted_randint(low, high):
    if _scripted:
        return _scripted.pop(0)
    return high if _default[0] is None else _default[0]


dice_mod.random.randint = _scripted_randint


def script(*values, default=None):
    """`default` covers rolls whose size the test does not want to hard-code
    (e.g. "every die of this roll fails", when the number of attacks comes
    from the datasheet)."""
    _scripted[:] = list(values)
    _default[0] = default


# ------------------------------------------------------- 1. DiceManager memory
print("\n1) DiceManager remembers which dice have already been re-rolled")
dm = DiceManager()
script(3, 3, 3)
dm.roll(count=3, sides=6, label="Hit Roll", roll_kind=HIT_ROLL)
ok("a fresh roll has no spent dice", dm.already_rerolled == set())
ok("every die of a fresh roll is re-rollable", dm.rerollable_indices() == [0, 1, 2])
script(5)
ok("re-rolling a free die works", dm.reroll_die(1) is True)
ok("that die is now spent", dm.already_rerolled == {1})
ok("and is gone from the re-rollable list", dm.rerollable_indices() == [0, 2])
before = list(dm.pending_values)
ok("re-rolling the SAME die again is refused", dm.reroll_die(1) is False)
ok("and it keeps the value it landed on", dm.pending_values == before)
ok("a full re-roll is refused once any die is spent", dm.reroll_all() is False)
ok("nothing was thrown by that refusal", dm.pending_values == before)

dm.acknowledge()
ok("acknowledging keeps the spent-dice memory (abilities read it after)",
   dm.already_rerolled == {1})
script(2, 2)
dm.roll(count=2, sides=6, label="Charge Roll", roll_kind=CHARGE_ROLL)
ok("a brand new roll clears it", dm.already_rerolled == set())
script(6, 6)
ok("reroll_all works on an untouched roll", dm.reroll_all() is True)
ok("it marks every die spent", dm.already_rerolled == {0, 1})
ok("a second full re-roll is refused", dm.reroll_all() is False)

script(4, 4)
dm.roll(count=2, sides=6, label="Wound Roll", roll_kind=WOUND_ROLL, is_reroll=True)
ok("a roll that IS a re-roll starts fully spent", dm.already_rerolled == {0, 1})
ok("and offers nothing to re-roll", dm.rerollable_indices() == [])


# ------------------------------------------- 2. Command Re-roll gating (15.02)
print("\n2) Command Re-roll cannot be spent on dice that already went twice")


def fresh_command_reroll(cp=3):
    dm = DiceManager()
    tt = TurnTracker()
    cps = CommandPointManager()
    cps.cp["Player 1"] = cp
    strat = StratagemController(command_points=cps)
    return dm, cps, CommandRerollController(strat, dm, turn_tracker=tt)


dm, cps, cr = fresh_command_reroll()
script(1, 1, 1)
dm.roll(count=3, sides=6, label="Hit Roll", roll_kind=HIT_ROLL)
ok("offered on a normal roll", cr.can_use() is True)
script(1)
dm.reroll_die(0)
ok("still offered while other dice are free", cr.can_use() is True)
cr.start()
ok("it asks which die", cr.selecting_die is True)
before = list(dm.pending_values)
cr.choose_die(0)
ok("clicking the already-re-rolled die is ignored", dm.pending_values == before)
ok("and the selection stays open (no CP burned on nothing)", cr.selecting_die is True)
ok("no CP was spent", cps.cp["Player 1"] == 3)
script(6)
cr.choose_die(2)
ok("clicking a free die does re-roll it", dm.pending_values[2] == 6)
ok("and spends the CP", cps.cp["Player 1"] == 2)

dm, cps, cr = fresh_command_reroll()
script(4)
dm.roll(count=1, sides=6, label="Wound Roll", roll_kind=WOUND_ROLL, is_reroll=True)
ok("NOT offered on an ability's own re-roll (the reported pairing)", cr.can_use() is False)

dm, cps, cr = fresh_command_reroll()
script(2, 2)
dm.roll(count=2, sides=6, label="Charge Roll", roll_kind=CHARGE_ROLL)
ok("offered on an untouched Charge roll", cr.can_use() is True)
script(3)
dm.reroll_die(0)
ok("not offered once part of the Charge roll went twice (must re-roll in full)",
   cr.can_use() is False)

dm, cps, cr = fresh_command_reroll()
script(1, 1, 1)
dm.roll(count=3, sides=6, label="Hit Roll", roll_kind=HIT_ROLL)
script(2)
dm.reroll_die(0)
script(2)
dm.reroll_die(1)
ok("with exactly one free die left it is still offered", cr.can_use() is True)
script(6)
cr.start()
ok("and picks that die without asking", cr.selecting_die is False)
ok("throwing the right one", dm.pending_values[2] == 6)


# ------------------------------------------------ shooting-activation scaffold
def shooting_scene(shooter_sheet, target_sheet=MEGANOBZ, weapon=TwinFusionBlasterProfile,
                   objectives=(), greater_good=None):
    """One shooter, one target, clear line of sight, a single weapon so the
    activation is exactly attacks -> hit -> wound."""
    st = GameState()
    shooter = build_squad(shooter_sheet, "Player 1", name="1 Shooter 1")
    target = build_squad(target_sheet, "Player 2", name="2 Target 1", composition_index=0)
    for i, mdl in enumerate(shooter.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 1.5, 20.0
        mdl.weapons = [weapon()] if weapon is not None else mdl.weapons
    for i, mdl in enumerate(target.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 1.5, 26.0
    for sq in (shooter, target):
        for mdl in sq.models:
            st.add_token(mdl)
    tt = TurnTracker()
    tt.phase_index = PHASES.index(PHASE_SHOOTING)
    cps = CommandPointManager()
    cps.cp["Player 1"] = 5
    strat = StratagemController(command_points=cps)
    dm = DiceManager()
    dec = DecisionManager()
    sc = ShootingController(
        obstacles=st.obstacles, dice_manager=dm, turn_tracker=tt, all_tokens=st.tokens,
        decision_manager=dec, objectives=list(objectives), greater_good=greater_good,
    )
    cr = CommandRerollController(strat, dm, turn_tracker=tt)
    return dict(state=st, shooter=shooter, target=target, dice=dm, decision=dec,
                shooting=sc, command_reroll=cr, cps=cps, turn=tt)


def begin_activation(scene):
    sc, dm = scene["shooting"], scene["shooting"].dice_manager
    sc.start_shooting(scene["shooter"])
    if sc.state == "choosing_shooting_type":
        sc.choose_shooting_type(sc.available_types[0])
    sc.choose_target_squad(scene["target"])
    key = sc.weapon_eligibility()[0][0]
    sc.choose_weapon(key)
    return dm


def ack(scene):
    """One click on the dice tray - the same order main.py uses."""
    scene["dice"].acknowledge()
    scene["shooting"].on_dice_acknowledged()


def prompts(scene):
    d = scene["decision"]
    return d.prompt if d.is_pending else None


# ------------------------------------------------- 3. the reported turn itself
print("\n3) the reported shot: Command Re-roll on the Wound roll, then [TWIN-LINKED]")
scene = shooting_scene(GHOSTKEEL_BATTLESUIT)
script(5)                       # hit roll [5] - a hit, exactly as logged
dm = begin_activation(scene)
ok("the hit roll is on the table", dm.is_pending and dm.roll_kind == HIT_ROLL)
script(1)                       # wound roll [1] - a failure
ack(scene)
ok("the wound roll follows", dm.roll_kind == WOUND_ROLL and len(dm.pending_values) == 1)
ok("Command Re-roll is offered on it", scene["command_reroll"].can_use() is True)
script(2)                       # the logged post-re-roll value: still a failure
scene["command_reroll"].start()
ok("the die was re-rolled to the logged 2", dm.pending_values == [2])
ok("and is now spent", dm.already_rerolled == {0})
ack(scene)
ok("[TWIN-LINKED] is NOT offered on that same die (was: re-rolled it again)",
   prompts(scene) is None)
ok("no second re-roll was thrown either", dm.is_pending is False or dm.roll_kind != WOUND_ROLL)

print("\n   A/B: with the memory ignored, the reported double re-roll comes back")
scene = shooting_scene(GHOSTKEEL_BATTLESUIT)
scene["dice"].already_rerolled = set()
script(5)
dm = begin_activation(scene)
script(1)
ack(scene)
script(2)
dm.pending_values[0] = 2  # stand in for the Command Re-roll, without marking it spent
ack(scene)
ok("un-tracked, the [TWIN-LINKED] offer does appear (test reaches the real path)",
   prompts(scene) is not None and "re-roll failed wound rolls" in prompts(scene).lower())

print("\n   and an untouched failure is still offered its one [TWIN-LINKED] re-roll")
scene = shooting_scene(GHOSTKEEL_BATTLESUIT)
script(5)
dm = begin_activation(scene)
script(1)
ack(scene)
ack(scene)
ok("offer made", prompts(scene) is not None)
script(6)
scene["decision"].choose(0)
ok("the re-roll is on the table", dm.roll_kind == WOUND_ROLL and dm.pending_values == [6])
ok("its dice start out spent", dm.already_rerolled == {0})
ok("Command Re-roll cannot be spent on it", scene["command_reroll"].can_use() is False)


# ------------------------------ 4. Forward Observers' automatic re-roll of 1s
print("\n4) Forward Observers (re-roll 1s) and the dice it may not touch")


class _AlwaysObserving:
    """Stand-in for the Greater Good controller: Forward Observers applies,
    nothing else does (the three methods shooting.py asks it for)."""

    def has_forward_observers(self, shooter, target):
        return True

    def is_guided_attack(self, shooter, target):
        return False

    def marked_by_markerlight(self, target):
        return False


scene = shooting_scene(STEALTH_BATTLESUITS, weapon=TwinFusionBlasterProfile,
                       greater_good=_AlwaysObserving())
n = len(scene["shooter"].models)
script(*([1] * n))                       # every hit die a natural 1
dm = begin_activation(scene)
ok(f"hit roll of {n} natural 1s", dm.pending_values == [1] * n)
script(*([6] * n))
ack(scene)
ok("Forward Observers re-rolls all of them", len(dm.pending_values) == n)
ok("those dice are marked spent", dm.already_rerolled == set(range(n)))
ok("Command Re-roll is refused on the re-roll", scene["command_reroll"].can_use() is False)

print("\n   a 1 produced BY a Command Re-roll is not re-rolled again")
scene = shooting_scene(STEALTH_BATTLESUITS, weapon=TwinFusionBlasterProfile,
                       greater_good=_AlwaysObserving())
n = len(scene["shooter"].models)
script(default=4)                        # all hits, no natural 1s anywhere
dm = begin_activation(scene)
ok("hit roll with no natural 1s", dm.pending_values == [4] * n)
script(1)                                # Command Re-roll turns die 0 into a 1
scene["command_reroll"].start()
scene["command_reroll"].choose_die(0)
ok("the picked die is now a 1", dm.pending_values[0] == 1)
script(default=4)
ack(scene)
ok("Forward Observers does NOT throw that 1 again - the wound roll follows",
   dm.roll_kind == WOUND_ROLL)

print("\n   wound step: [TWIN-LINKED] only gets the failures Forward Observers left alone")
scene = shooting_scene(STEALTH_BATTLESUITS, weapon=TwinFusionBlasterProfile,
                       greater_good=_AlwaysObserving())
n = len(scene["shooter"].models)
script(default=4)                        # all hit, no 1s -> straight to wounds
dm = begin_activation(scene)
# n-1 natural 1s plus one plain (non-1) failure: S9 vs Meganobz T5 wounds on
# 3+, so a 2 fails without being a 1 Forward Observers could touch.
script(*([1] * (n - 1) + [2]))
ack(scene)
ok("wound roll is on the table", dm.roll_kind == WOUND_ROLL and len(dm.pending_values) == n)
script(default=2)                        # the re-rolled 1s fail again
ack(scene)
ok("Forward Observers re-rolled exactly the 1s", len(dm.pending_values) == n - 1)
ok("and they are spent", dm.already_rerolled == set(range(n - 1)))
ack(scene)
offer = prompts(scene)
ok("[TWIN-LINKED] is still offered (an untouched failure remains)", offer is not None)
if offer is not None:
    script(default=6)
    scene["decision"].choose(0)
    ok("but it throws only the die that never went, not all n failures",
       dm.pending_values is not None and len(dm.pending_values) == 1)


# ------------------------------- 5. Breach and Clear's full re-roll of a roll
print("\n5) Breach and Clear re-rolls the whole roll - minus dice that already went")
# The ability only applies while the TARGET stands on an objective, so the
# objective's terrain area is placed over the target's own footprint.
obj = Objective(TerrainArea([Obstacle(16.0, 22.0, 12.0, 8.0, category=EXPOSED)]), name="Obj")
scene = shooting_scene(BREACHER_TEAM, weapon=None, objectives=[obj])
# Breacher Team's own Pulse Blaster (A2, not [TWIN-LINKED]) is the weapon
# under test; the squad is trimmed so the roll stays small enough to follow
# die by die.
scene["shooter"].models[:] = scene["shooter"].models[:2]
script(default=6)                        # everything hits
dm = begin_activation(scene)
n = len(dm.pending_values)
ok(f"hit roll of {n} (2 models x A2)", n == 4)
script(default=1)                        # every wound die fails
ack(scene)
ok("wound roll of failures", dm.roll_kind == WOUND_ROLL and len(dm.pending_values) == n)
script(6)
scene["command_reroll"].start()
scene["command_reroll"].choose_die(0)
ok("Command Re-roll turns one of them into a wound", dm.pending_values[0] == 6)
ok("that die is spent", dm.already_rerolled == {0})
script(default=1)
ack(scene)
offer = prompts(scene)
ok("Breach and Clear is offered", offer is not None and "wound roll" in offer.lower())
labels = [opt["label"] for opt in scene["decision"].options]
ok(f"and offers only the {n - 1} dice that have not gone yet (label: {labels[0]!r})",
   f"({n - 1} dice)" in labels[0])
scene["decision"].choose(0)
ok("it throws exactly those dice", len(dm.pending_values) == n - 1)
ok("and they are spent", dm.already_rerolled == set(range(n - 1)))


# ---------------------------------------- 6. the same pairing in the Fight phase
print("\n6) melee: [TWIN-LINKED] does not re-throw a Command Re-rolled failure")


class _TwinMelee(WeaponProfile):
    """A plain [TWIN-LINKED] melee weapon - the datasheets in this demo have
    none, and the rule under test is the re-roll, not any one profile."""
    name = "Twin Melee Test Weapon"
    weapon_type = MELEE
    range_in = 0
    attacks = 1
    strength = 9
    ap = -1
    damage = 1
    twin_linked = True


def melee_scene():
    """Two engaged squads; the attacker swings a [TWIN-LINKED] melee weapon
    so the Fight phase reaches the same offer the shooting phase does."""
    st = GameState()
    # A multi-model attacker, so the wound roll has both a die the Command
    # Re-roll spends AND failures [TWIN-LINKED] may still legally throw.
    attacker = build_squad(STEALTH_BATTLESUITS, "Player 1", name="1 Attacker 1")
    target = build_squad(MEGANOBZ, "Player 2", name="2 Target 1", composition_index=0)
    for i, mdl in enumerate(attacker.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 1.5, 20.0
        mdl.weapons = [_TwinMelee()]
    for i, mdl in enumerate(target.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 1.5, 21.2   # inside Engagement Range
    for sq in (attacker, target):
        for mdl in sq.models:
            st.add_token(mdl)
    tt = TurnTracker()
    tt.phase_index = PHASES.index(PHASE_FIGHT)
    cps = CommandPointManager()
    cps.cp["Player 1"] = 5
    dm, dec = DiceManager(), DecisionManager()
    fc = FightController(dice_manager=dm, turn_tracker=tt, all_tokens=st.tokens, decision_manager=dec)
    cr = CommandRerollController(StratagemController(command_points=cps), dm, turn_tracker=tt)
    return dict(state=st, attacker=attacker, target=target, dice=dm, decision=dec,
                fight=fc, command_reroll=cr)


def melee_ack(scene):
    scene["dice"].acknowledge()
    scene["fight"].on_dice_acknowledged()


scene = melee_scene()
fc = scene["fight"]
fc.begin_fight_step()
fc.select_to_fight(scene["attacker"])
if fc.state == "choosing_target":
    fc.choose_target_squad(scene["target"])
script(default=6)                        # everything hits
dm = scene["dice"]
if fc.weapon_eligibility():
    fc.choose_weapon(fc.weapon_eligibility()[0][0])
ok("a melee hit roll is on the table", dm.is_pending and dm.roll_kind == HIT_ROLL)
script(default=1)                        # every wound die fails
melee_ack(scene)
ok("the wound roll follows", dm.roll_kind == WOUND_ROLL)
n = len(dm.pending_values)
script(2)                                # Command Re-roll: still a failure
scene["command_reroll"].start()
if scene["command_reroll"].selecting_die:
    scene["command_reroll"].choose_die(0)
ok("one failure was re-rolled and is spent", dm.already_rerolled == {0})
script(default=6)
melee_ack(scene)
offer = scene["decision"].prompt if scene["decision"].is_pending else None
if n == 1:
    ok("with that as the only die, [TWIN-LINKED] is not offered at all", offer is None)
else:
    ok("[TWIN-LINKED] is offered for the other failures", offer is not None)
    scene["decision"].choose(0)
    ok(f"and throws {n - 1} dice, not all {n} failures", len(dm.pending_values) == n - 1)
    ok("which are then spent too", dm.already_rerolled == set(range(n - 1)))


print(f"\n{checks - len(failed)}/{checks} checks passed")
if failed:
    print("FAILED:")
    for f in failed:
        print("  - " + f)
    raise SystemExit(1)
