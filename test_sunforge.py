"""Crisis Sunforge Battlesuits datasheet: stat line, loadout, drone menu,
and the Sunforge ability's two halves (re-roll the Wound roll, re-roll the
Damage roll) against MONSTER/VEHICLE targets.

Real objects throughout (build_squad() off the real datasheet, real
ShootingController/DamageAllocationSession/DiceManager/DecisionManager), no
mocks of the things under test. Every ability claim carries an A/B - without
one, a passing assertion could equally mean "nothing happened and the
baseline already looked like that".
"""

from game.damage_resolution import DamageAllocationSession
from game.decision import DecisionManager
from game.dice import DiceManager
from game.drones import DRONE_SLOTS
from game.factions import build_squad
from game.factions.tau_empire import (
    CRISIS_STARSCYTHE, CRISIS_SUNFORGE, DEVILFISH, KROOT_CARNIVORES,
)
from game.shooting import NORMAL_SHOOTING, ShootingController
# The Damage-roll collaborator moved to game/damage_reroll.py when Fire
# Dragons became its second user; sunforge.damage_reroll_offer() is this
# ability's pre-labelled one.
from game.sunforge import applies, damage_reroll_offer, unit_has_sunforge
from game.units import CrisisSunforgeShasUiProfile, CrisisSunforgeShasVreProfile

PASS = []
FAIL = []
VRE = "Crisis Sunforge Shas'vre"
UI1 = "Crisis Sunforge Shas'ui (1)"


def check(label, ok, detail=""):
    (PASS if ok else FAIL).append(label)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))


def make_sunforge(gear=None, x=20.0, y=20.0):
    squad = build_squad(
        CRISIS_SUNFORGE, "Player 1", gear=gear, name="1 Crisis Sunforge Battlesuits 1", x_in=x, y_in=y,
    )
    for i, m in enumerate(squad.models):
        m.x_in, m.y_in = x + i * 2.2, y
    return squad


def make_vehicle(x=26.0, y=20.0):
    squad = build_squad(DEVILFISH, "Player 2", name="1 Devilfish 1", x_in=x, y_in=y)
    squad.models[0].x_in, squad.models[0].y_in = x, y
    return squad


def make_infantry(x=26.0, y=20.0):
    squad = build_squad(KROOT_CARNIVORES, "Player 2", name="1 Kroot Carnivores 1", x_in=x, y_in=y)
    for i, m in enumerate(squad.models):
        m.x_in, m.y_in = x + (i % 5) * 1.2, y + (i // 5) * 1.2
    return squad


# --- 1. Stat line, keywords, points --------------------------------------
print("\n1. Stat line / keywords / points")

squad = make_sunforge()
vre, ui = squad.models[0], squad.models[1]
p = ui.profile
stats = (p.movement_in, p.toughness, p.armor_save, p.wounds, p.leadership, p.oc, p.weapon_skill, p.ballistic_skill)
check('M10" T5 Sv3+ W4 Ld7+ OC2, WS5+/BS4+', stats == (10, 5, "3+", 4, "7+", 2, "5+", "4+"), str(stats))
check("Invulnerable Save (4+)", p.invulnerable_save == "4+")
check("3 models: 1 Shas'vre + 2 Shas'ui", len(squad.models) == 3 and vre.profile.squad_leader
      and not ui.profile.squad_leader)
check("both lines share one stat row", vre.profile.toughness == p.toughness and vre.profile.wounds == p.wounds)
check("VEHICLE/WALKER/FLY/BATTLESUIT, not INFANTRY",
      p.vehicle and p.walker and p.fly and p.battlesuit and not p.infantry)
check("Deep Strike", p.deep_strike)
check("For The Greater Good", p.for_the_greater_good)
check("base size matches Starscythe (user: gleiche basegröße)",
      CrisisSunforgeShasUiProfile.base_radius_in == 0.98)
check("no Battlesuit Support System - it isn't on the supplied abilities list",
      not p.battlesuit_support_system)
check("keywords line matches the datasheet",
      CRISIS_SUNFORGE.keywords == ("VEHICLE", "WALKER", "FLY", "BATTLESUIT", "CRISIS", "SUNFORGE"))
check("points: 125 for the 1st-2nd unit", CRISIS_SUNFORGE.points_for(0, unit_index=1) == 125)
check("points: 135 from the 3rd unit on", CRISIS_SUNFORGE.points_for(0, unit_index=3) == 135)
check("Squad.points reflects the built unit", squad.points == 125)


# --- 2. Weapons + drones -------------------------------------------------
print("\n2. Weapons and drones")

names = [w.name for w in ui.weapons]
check("every model: 2x Fusion blaster + Battlesuit fists",
      names.count("Fusion Blaster") == 2 and names.count("Battlesuit Fists") == 1, str(names))
fb = next(w for w in ui.weapons if w.name == "Fusion Blaster")
check('Fusion blaster 12"/A1/S9/AP-4, [MELTA 2]',
      (fb.range_in, fb.attacks, fb.strength, fb.ap, fb.melta) == (12, 1, 9, -4, 2))
check("its Damage is a real D6 roll, not a fixed 6",
      fb.damage_notation is not None and fb.damage_notation.sides == 6)
check("Fusion blaster defers BS to the model (both are 4+)", fb.ballistic_skill is None)
fists = next(w for w in ui.weapons if w.name == "Battlesuit Fists")
check("Battlesuit fists melee A3/S5/AP0/D1",
      (fists.weapon_type, fists.attacks, fists.strength, fists.ap, fists.damage) == ("melee", 3, 5, 0, 1))

droned = make_sunforge(gear={VRE: ["Gun Drone", "Marker Drone"], UI1: ["Shield Drone"]})
check("2 drones per model, tracked per model line",
      droned.models[0].gear_names == ["Gun Drone", "Marker Drone"] and droned.models[1].gear_names == ["Shield Drone"])
over = make_sunforge(gear={VRE: ["Gun Drone", "Marker Drone", "Shield Drone"]})
check("a 3rd drone is trimmed (same 2-slot cap as Starscythe)",
      len(over.models[0].gear_names) == DRONE_SLOTS)
guardian = make_sunforge(gear={VRE: ["Guardian Drone"]})
check("no Guardian Drone on the menu (same as Starscythe)", guardian.models[0].gear_names == [])
dupes = make_sunforge(gear={VRE: ["Gun Drone", "Gun Drone"]})
check("no duplicates (same as Starscythe)", dupes.models[0].gear_names == ["Gun Drone"])
check("drone menu matches Starscythe's exactly",
      sorted(g.name for g in CRISIS_SUNFORGE.gear_for(VRE))
      == sorted(g.name for g in CRISIS_STARSCYTHE.gear_for("Crisis Starscythe Shas'vre")))


# --- 3. applies() --------------------------------------------------------
print("\n3. When Sunforge applies")

sf, veh, inf = make_sunforge(), make_vehicle(), make_infantry()
check("unit_has_sunforge is True for this datasheet", unit_has_sunforge(sf))
check("A/B: applies against a VEHICLE target", applies(sf, veh))
check("A/B: does NOT apply against plain INFANTRY", not applies(sf, inf))
starscythe = build_squad(CRISIS_STARSCYTHE, "Player 1", name="1 Crisis Starscythe Battlesuits 1", x_in=20, y_in=20)
check("A/B: a Starscythe team has no Sunforge, even against a VEHICLE", not applies(starscythe, veh))
for m in sf.models:
    m.current_wounds = 0
check("the ability dies with its models", not applies(sf, veh))


# --- 4. Wound-roll half --------------------------------------------------
print("\n4. Sunforge - the Wound-roll half")


def shooting_for(target):
    sq = make_sunforge()
    tokens = list(sq.models) + list(target.models)
    sc = ShootingController(
        all_tokens=tokens, dice_manager=DiceManager(), decision_manager=DecisionManager(),
        player_name="Player 1",
    )
    sc.shooting_type = NORMAL_SHOOTING
    sc.active_squad = sq
    return sc, sq, next(w for w in sq.models[0].weapons if w.name == "Fusion Blaster")


sc_v, sq_v, weapon = shooting_for(make_vehicle())
sc_i, sq_i, _ = shooting_for(make_infantry())
check("A/B: a VEHICLE target offers a Sunforge wound re-roll",
      sc_v._wound_reroll_reason(weapon, make_vehicle()) == "Sunforge")
check("A/B: an INFANTRY target offers none",
      sc_i._wound_reroll_reason(weapon, make_infantry()) is None)
check("it re-rolls the WHOLE Wound roll (its text says 'the Wound roll')",
      sc_v._wound_reroll_is_full(weapon, make_vehicle()) is True)


class _TwinLinkedFusion:
    """The same Fusion blaster but [TWIN-LINKED], to check the precedence
    rule: the failures-only source must win, since it cannot lose a wound
    that has already been rolled."""

    def __init__(self, base):
        self.__dict__.update(base.__dict__)
        for attr in ("name", "twin_linked", "damage_notation", "range_in", "melta"):
            setattr(self, attr, getattr(base, attr))
        self.twin_linked = True


tl = _TwinLinkedFusion(weapon)
check("[TWIN-LINKED] outranks Sunforge when both apply",
      sc_v._wound_reroll_reason(tl, make_vehicle()) == "[TWIN-LINKED]")
check("...and that keeps the failures-only scope",
      sc_v._wound_reroll_is_full(tl, make_vehicle()) is False)


# --- 5. Damage-roll half -------------------------------------------------
print("\n5. Sunforge - the Damage-roll half")


def damage_session(target, damage_reroll, rolls=(1,)):
    """A real DamageAllocationSession for one failed save with a
    dice-notation Damage weapon, so the Damage roll actually happens."""
    dm = DiceManager()
    sq = make_sunforge()
    w = next(x for x in sq.models[0].weapons if x.name == "Fusion Blaster")
    session = DamageAllocationSession(
        list(rolls), w, target, dice_manager=dm, damage_reroll=damage_reroll,
    )
    return session, dm


sess, _dm = damage_session(make_vehicle(), None)
check("a dice-notation Damage weapon really pauses on a Damage roll",
      sess.pending_damage_roll is not None)


def acknowledged_die():
    """A DiceManager in exactly the state the offer really sees: one d6
    rolled AND acknowledged. acknowledge() clears pending_values, which is
    the whole reason can_offer() reads already_rerolled instead of
    can_reroll_all() - a harness that skipped the acknowledge would test a
    state the game never reaches."""
    dm = DiceManager()
    dm.roll(count=1, sides=6, label="Damage: Fusion Blaster")
    dm.acknowledge()
    return dm


decisions = DecisionManager()
dm2 = acknowledged_die()
reroll = damage_reroll_offer(decision_manager=decisions, dice_manager=dm2, owner="Player 1", weapon_name="Fusion Blaster")
results = []
opened = reroll.maybe_offer(1, results.append)
check("A/B: the re-roll is offered even after the roll was acknowledged",
      opened and decisions.is_pending)
check("the choice belongs to the ATTACKER", decisions.player == "Player 1")
labels = [o["label"] for o in decisions.options]
check("both options quote the current roll", any("re-roll" in l and "(1)" in l for l in labels)
      and any("Keep" in l and "(1)" in l for l in labels), str(labels))
decisions.choose(1)  # keep
check("keeping answers False (no re-roll)", results == [False])

decisions2 = DecisionManager()
dm3 = acknowledged_die()
reroll2 = damage_reroll_offer(decision_manager=decisions2, dice_manager=dm3, owner="Player 1", weapon_name="Fusion Blaster")
out = []
reroll2.maybe_offer(1, out.append)
decisions2.choose(0)
check("choosing to re-roll answers True", out == [True])

spent = acknowledged_die()
spent.roll(count=1, sides=6, label="Damage (Sunforge re-roll)", is_reroll=True)
spent.acknowledge()
check("A/B: once the die has been re-rolled the offer is refused",
      not damage_reroll_offer(decision_manager=DecisionManager(), dice_manager=spent,
                               owner="Player 1", weapon_name="F").maybe_offer(1, lambda _: None))
check("...because is_reroll marks the die as spent in the ledger", spent.already_rerolled == {0})

# A/B: the session only gets a damage_reroll when the ability applies.
sc_ok, sq_ok, _ = shooting_for(make_vehicle())
sc_no, sq_no, _ = shooting_for(make_infantry())
veh4, inf4 = make_vehicle(), make_infantry()
fb4 = next(w for w in sq_ok.models[0].weapons if w.name == "Fusion Blaster")
sc_ok._begin_damage_allocation([1], fb4, veh4, None)
sc_no._begin_damage_allocation([1], fb4, inf4, None)
check("A/B end-to-end: a VEHICLE target's session carries a damage re-roll",
      sc_ok.damage_session.damage_reroll is not None)
check("A/B end-to-end: an INFANTRY target's session does not",
      sc_no.damage_session.damage_reroll is None)

# A flat-damage weapon has no Damage roll to re-roll at all. Its session
# finishes synchronously (nothing to pause on), so _check_allocation_done()
# runs to the end and needs the group context a real dispatch would have
# left behind - supplied here rather than skipping the case, since "flat
# damage means no collaborator" is exactly the guard worth proving.
fists4 = next(w for w in sq_ok.models[0].weapons if w.name == "Battlesuit Fists")
veh5 = make_vehicle()
sc_ok.current_group = {
    "weapon_key": ("Battlesuit Fists",),
    "weapon_label": "Battlesuit Fists",
    "pairs": [(sq_ok.models[0], fists4)],
    "target_squad": veh5,
}
sc_ok._begin_damage_allocation([1], fists4, veh5, None)
check("a flat-Damage weapon gets no re-roll collaborator (nothing to re-roll)",
      sc_ok.damage_session is None or sc_ok.damage_session.damage_reroll is None)
check("...and that is the damage_notation guard, not the applies() one",
      fists4.damage_notation is None and applies(sq_ok, veh5))


# --- 6. End-to-end through the session's own seam ------------------------
print("\n6. End-to-end: the re-roll actually changes applied damage")


def run_damage(reroll_choice, forced_first, forced_second):
    """Drives a real DamageAllocationSession from failed save to applied
    wounds, exercising the full seam: Damage roll -> acknowledge -> Sunforge
    offer -> (a real second roll) -> acknowledge -> damage applied.

    Both dice are pinned by overwriting last_values right before each
    acknowledgement, which is the value DiceNotationRoll actually reads.
    `reroll_choice` is the DecisionManager option index (0 = re-roll,
    1 = keep), or None for no collaborator at all."""
    decisions = DecisionManager()
    dm = DiceManager()
    sq = make_sunforge()
    target = make_vehicle()
    before = target.models[0].current_wounds
    w = next(x for x in sq.models[0].weapons if x.name == "Fusion Blaster")
    collaborator = None
    if reroll_choice is not None:
        collaborator = damage_reroll_offer(
            decision_manager=decisions, dice_manager=dm, owner="Player 1", weapon_name=w.name,
        )
    session = DamageAllocationSession([1], w, target, dice_manager=dm, damage_reroll=collaborator)
    assert session.pending_damage_roll is not None, "expected a pending Damage roll"

    dm.last_values = [forced_first]
    dm.acknowledge()
    session.on_damage_roll_acknowledged()

    if reroll_choice is not None and decisions.is_pending:
        decisions.choose(reroll_choice)
        if reroll_choice == 0:
            assert session.pending_damage_roll is not None, "expected a second, real Damage roll"
            dm.last_values = [forced_second]
            dm.acknowledge()
            session.on_damage_roll_acknowledged()
    return before - target.models[0].current_wounds


kept = run_damage(1, 2, 6)
check("A/B: keeping a Damage roll of 2 applies 2 wounds", kept == 2, f"applied {kept}")
rerolled = run_damage(0, 2, 6)
check("re-rolling that 2 into a 6 applies 6 wounds instead", rerolled == 6, f"applied {rerolled}")
none_offered = run_damage(None, 2, 6)
check("A/B: with no collaborator at all the roll stands as-is", none_offered == 2, f"applied {none_offered}")
worse = run_damage(0, 5, 1)
check("the re-roll is a real gamble - a 5 re-rolled into a 1 applies 1",
      worse == 1, f"applied {worse}")

# --- 7. The re-roll prompt must not strand the activation ----------------
# Real freeze, user report: "nach meinem letzten beschuss mit den sunforge
# ist das spiel danach eingefroren. kein knopf hat mehr reagiert und ich
# konnte keinen anderen squad auswaehlen." Reproduced verbatim from
# logs/game_20260813_223111.log lines 1022-1030, whose tell-tale is a weapon
# group with NO "save roll: X saved, Y failed" summary line: answering the
# Sunforge Damage prompt resumes DamageAllocationSession from outside
# ShootingController, so when that answer is what finishes the session,
# nothing ran the controller's own end-of-group step.

from game.factions.orks import DEFF_DREAD  # noqa: E402  (grouped with its own section)
from game.game_state import GameState  # noqa: E402
from game.turn import PHASE_SHOOTING, PHASES, TurnTracker  # noqa: E402
import game.dice as _dice_mod  # noqa: E402


class _Log:
    def __init__(self):
        self.lines = []

    def add(self, message, file_only=False):
        self.lines.append(message)

    def has(self, needle):
        return any(needle.lower() in l.lower() for l in self.lines)


def _freeze_scene(script_values):
    """Sunforge unit firing on a Deff Dread (VEHICLE, so Sunforge applies)
    with scripted dice. Returns the controller once nothing is pending any
    more - i.e. exactly the state the player is left staring at."""
    queue = list(script_values)
    _dice_mod.random.randint = lambda lo, hi: queue.pop(0) if queue else 1

    state = GameState()
    attacker = build_squad(CRISIS_SUNFORGE, "Player 1", name="Sunforge")
    target = build_squad(DEFF_DREAD, "Player 2", name="Deff Dread")
    for i, m in enumerate(attacker.models):
        m.x_in, m.y_in = 20.0 + i * 1.4, 20.0
    for m in target.models:
        m.x_in, m.y_in = 20.0, 26.0
    for squad in (attacker, target):
        for m in squad.models:
            state.add_token(m)

    tt = TurnTracker(first_player="Player 1")
    tt.phase_index = PHASES.index(PHASE_SHOOTING)
    dm, dec, log = DiceManager(), DecisionManager(), _Log()
    sc = ShootingController(
        dice_manager=dm, turn_tracker=tt, all_tokens=state.tokens,
        decision_manager=dec, game_log=log, obstacles=[],
    )
    sc.start_shooting(attacker)
    sc.choose_shooting_type(sc.available_types[0])
    sc.choose_target_squad(target)
    sc.choose_weapon(sc.weapon_eligibility()[0][0])

    for _ in range(40):
        if dec.is_pending:
            labels = [o["label"] for o in dec.options]
            dec.choose(next(i for i, l in enumerate(labels) if l.startswith("Keep")))
        elif dm.is_pending:
            dm.acknowledge()
            sc.on_dice_acknowledged()
        elif sc.pending_damage_choice:
            sc.choose_damage_model(sc.pending_damage_choice[0])
        else:
            break
    return sc, log, target


# 6 attacks: 3 hit, 3 wound, all 3 saves fail; the target dies on the second
# allocation so the third is wasted and the session finishes INSIDE the
# prompt's callback - the exact shape from the log.
DICE = [6, 6, 6, 1, 1, 1] + [6, 6, 6] + [1, 1, 1] + [5, 5, 5]
sc, log, target = _freeze_scene(DICE)

check("freeze repro: the target really was destroyed mid-group",
      all(m.is_dead() for m in target.models))
check("the weapon group ran its end-of-group step (save-roll summary logged)",
      log.has("save roll"))
check("the activation ended - squad released", sc.active_squad is None)
check("no weapon group left dangling", sc.current_group is None)
check("no damage session left dangling", sc.damage_session is None)
check("nothing left half-resolved (pending_step cleared)", sc.pending_step is None)

# A/B: unwire the resume hook and the same scene must strand the controller
# again - otherwise these checks would pass for some unrelated reason.
_real_hook = ShootingController._make_damage_resume_hook
ShootingController._make_damage_resume_hook = lambda self, session, rolls: None
try:
    broken_sc, broken_log, _ = _freeze_scene(DICE)
finally:
    ShootingController._make_damage_resume_hook = _real_hook
check("A/B: without the resume hook the same scene strands the controller",
      broken_sc.active_squad is not None and broken_sc.pending_step == "allocate"
      and not broken_log.has("save roll"),
      f"squad={broken_sc.active_squad}, step={broken_sc.pending_step}")

# The other half of the same defect: while the prompt is open the session is
# NOT done, so the group cannot be closed out early underneath it.
session = DamageAllocationSession(
    [1], build_squad(CRISIS_SUNFORGE, "Player 1").models[0].weapons[1],
    build_squad(DEFF_DREAD, "Player 2"),
)
session.pending_damage_reroll = True
check("a session with an unanswered Damage re-roll prompt is not done",
      not session.done)

print(f"\n{len(PASS)}/{len(PASS) + len(FAIL)} checks passed")
if FAIL:
    print("FAILED:")
    for f in FAIL:
        print("  -", f)
    raise SystemExit(1)
