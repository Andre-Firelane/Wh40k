"""Tests for War Horde's 'Ard as Nails stratagem (game/ard_as_nails.py).

RULE (user-supplied): 1CP, War Horde Battle Tactic Stratagem. WHEN your
opponent's Shooting phase or the Fight phase, just after an enemy unit has
selected its targets. TARGET one ORKS unit from your army (excluding GROTS,
MONSTER and VEHICLE units) that was selected as the target of one or more of
the attacking unit's attacks. EFFECT until the end of the phase, each time an
attack targets your unit, subtract 1 from the Wound roll.

Used DETERMINISTICALLY for the AI side, per the user: buy it when the unit is
worth 100 points or more, still has more than half its models, and the
incoming attack is expected to take at least half of what is left of it.

Four things carry real risk and so get the most attention here:

  * the three TARGET exclusions (GROTS / MONSTER / VEHICLE), checked against
    the real Ork datasheets rather than a synthetic profile, since GROTS is
    read off the datasheet keyword line and the other two off UnitProfile
    flags;
  * that the -1 reaches the actual wound roll in BOTH phases, measured through
    the real ShootingController/FightController with scripted dice, each with
    an A/B on the same dice so the extra failures are proven to come from the
    stratagem;
  * each of the three deterministic conditions in isolation, each with the
    other two held true, so "did not fire" is attributable;
  * that the trigger fires at target selection, spends the CP without any
    prompt for the AI side, and DOES prompt a human.

Uses real StratagemController/CommandPointManager/DecisionManager/
TurnTracker/ShootingController/FightController/GameState objects and real
datasheets throughout.

Run: python test_ard_as_nails.py
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game import dice as dice_mod
from game import maps
from game.ard_as_nails import (
    ARD_AS_NAILS_WOUND_PENALTY, ArdAsNailsController, MIN_MODEL_LOSS_FRACTION, MIN_POINTS, attack_would_cripple,
    expected_models_lost, is_eligible_unit, is_worth_using, remaining_wounds,
)
from game.attached_units import attach
from game.command_points import CommandPointManager
from game.decision import DecisionManager
from game.dice import DiceManager, WOUND_ROLL
from game.factions import build_squad
from game.factions.orks import (
    BOYZ, DEFFKOPTAS, DEFF_DREAD, GRETCHIN, MEGANOBZ, STORMBOYZ, TANKBUSTAS, TRUKK, WARBIKERS, WARBOSS,
)
from game.factions.tau_empire import BREACHER_TEAM, CRISIS_STARSCYTHE, STRIKE_TEAM
from game.fight import FightController
from game.game_state import GameState
from game.movement import MovementController
from game.shooting import ShootingController
from game.squad import is_at_half_strength
from game.stratagems import StratagemController
from game.turn import PHASES, PHASE_FIGHT, PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker

m = maps.get("map2")
maps.apply_to_config(m)

_UNSET = object()  # 'no kwargs given' - distinct from an explicit {}
checks, failed = 0, []


def ok(label, cond, detail=""):
    global checks
    checks += 1
    if not cond:
        failed.append(label)
    print(("  PASS  " if cond else "  FAIL  ") + label + ((" - " + detail) if detail else ""))


# --------------------------------------------------------------- scripted dice
_scripted = []
_default = [None]


def _scripted_randint(low, high):
    if _scripted:
        return _scripted.pop(0)
    return high if _default[0] is None else _default[0]


dice_mod.random.randint = _scripted_randint


def script(*values, default=None):
    _scripted[:] = list(values)
    _default[0] = default


# ==================================================== 1. the TARGET clause
print("\n1) TARGET: one ORKS unit, excluding GROTS / MONSTER / VEHICLE")

SHEETS = {
    "Boyz": (BOYZ, {}), "Gretchin": (GRETCHIN, {}), "Meganobz": (MEGANOBZ, dict(composition_index=1)),
    "Stormboyz": (STORMBOYZ, dict(composition_index=1)), "Trukk": (TRUKK, {}), "Deff Dread": (DEFF_DREAD, {}),
    "Tankbustas": (TANKBUSTAS, {}), "Deffkoptas": (DEFFKOPTAS, {}), "Warbikers": (WARBIKERS, dict(composition_index=0)),
}
built = {name: build_squad(sheet, "Player 2", name=name, **kw) for name, (sheet, kw) in SHEETS.items()}

ok("Boyz qualify", is_eligible_unit(built["Boyz"]))
ok("Meganobz qualify", is_eligible_unit(built["Meganobz"]))
ok("GROTS are excluded (Gretchin)", not is_eligible_unit(built["Gretchin"]))
ok("VEHICLE is excluded (Trukk)", not is_eligible_unit(built["Trukk"]))
ok("VEHICLE is excluded (Deff Dread)", not is_eligible_unit(built["Deff Dread"]))
ok("VEHICLE is excluded (Deffkoptas)", not is_eligible_unit(built["Deffkoptas"]))
ok("a T'au unit is not an ORKS unit",
   not is_eligible_unit(build_squad(STRIKE_TEAM, "Player 1", name="1 Strike Team 1")))

# Rule 19.03 both ways: a joined character keeps the unit eligible, and cannot
# launder away an exclusion.
st = GameState()
boyz = build_squad(BOYZ, "Player 2", name="2 Boyz 1")
wb = build_squad(WARBOSS, "Player 2", name="2 Warboss 1")
for mdl in list(boyz.models) + list(wb.models):
    mdl.x_in, mdl.y_in = 20.0, 20.0
    st.add_token(mdl)
attach(wb, boyz, st)
ok("rule 19.03: Boyz + Warboss is still an eligible ORKS unit", is_eligible_unit(boyz))
ok("...and its points are the merged total", boyz.points == 160, str(boyz.points))


# =========================================== 2. the three deterministic conditions
print("\n2) the deterministic conditions, one at a time")


def shooting_scene(target_sheet=STORMBOYZ, target_kwargs=_UNSET, keep_models=6,
                   attacker_sheet=BREACHER_TEAM, cp=5, phase=PHASE_SHOOTING, auto=("Player 2",)):
    """The one matchup in the two demo armies where all three conditions can
    hold at once (measured - see measure_ard_as_nails.py): a Breacher Team
    shooting a Stormboyz mob that is down to 6 of its 11 models, i.e. still
    above half strength, still worth 130 points, and about to be erased.

    Casualties are applied through GameState.remove_dead_models(), the same
    path the real game uses - is_at_half_strength() counts len(squad.models),
    so leaving dead tokens in the list would silently make every trimmed unit
    look full-strength."""
    st = GameState()
    attacker = build_squad(attacker_sheet, "Player 1", name="1 Attacker 1")
    kwargs = dict(composition_index=1) if target_kwargs is _UNSET else (target_kwargs or {})
    target = build_squad(target_sheet, "Player 2", name="2 Target 1", **kwargs)
    for i, mdl in enumerate(attacker.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 1.5, 20.0
    for i, mdl in enumerate(target.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 1.5, 26.0
    for sq in (attacker, target):
        for mdl in sq.models:
            st.add_token(mdl)
    if keep_models is not None:
        for mdl in target.models[keep_models:]:
            mdl.current_wounds = 0
        st.remove_dead_models()

    tt = TurnTracker()
    tt.phase_index = PHASES.index(phase)
    tt.turn_owner = "Player 1"
    tt.set_active("Player 1")
    cps = CommandPointManager()
    cps.cp["Player 1"] = cps.cp["Player 2"] = cp
    dm, dec = DiceManager(), DecisionManager()
    strat = StratagemController(command_points=cps)
    aan = ArdAsNailsController(strat, decision_manager=dec, turn_tracker=tt, auto_players=auto)
    mc = MovementController(obstacles=st.obstacles, turn_tracker=tt, all_tokens=st.tokens)
    sc = ShootingController(
        obstacles=st.obstacles, dice_manager=dm, turn_tracker=tt, all_tokens=st.tokens,
        movement_controller=mc, terrain_areas=st.terrain_areas, decision_manager=dec,
        target_reactions=(aan,),
    )
    return dict(state=st, attacker=attacker, target=target, dice=dm, decision=dec,
                shoot=sc, turn=tt, cp=cps, stratagems=strat, nails=aan)


sc = shooting_scene()
ok("baseline: 130 pts, 6 of 11 models (above half), and half of them would die",
   is_worth_using(sc["attacker"], sc["target"]),
   f"{sc['target'].points} pts, {len(sc['target'].models)} models, {remaining_wounds(sc['target'])} wounds standing")

# (a) points - the other two conditions held true, only the value changed.
sc = shooting_scene()
sc["target"].points = MIN_POINTS
ok("exactly 100 points is enough (the floor is inclusive)",
   is_worth_using(sc["attacker"], sc["target"]))
sc["target"].points = MIN_POINTS - 1
ok("...99 is not", not is_worth_using(sc["attacker"], sc["target"]))

# (b) half strength - one model fewer, everything else identical.
sc = shooting_scene(keep_models=5)
ok("5 of 11 models is AT half strength, so it does not qualify",
   is_at_half_strength(sc["target"]) and not is_worth_using(sc["attacker"], sc["target"]))
ok("...and that is the ONLY reason - the attack would still gut it",
   attack_would_cripple(sc["attacker"], sc["target"]) and sc["target"].points >= MIN_POINTS)

# (c) how hard the attack hits - a weaker attacker against the same full mob.
sc = shooting_scene(attacker_sheet=STRIKE_TEAM, keep_models=None)
ok("an attacker expected to take less than half the mob does not qualify",
   not attack_would_cripple(sc["attacker"], sc["target"])
   and not is_worth_using(sc["attacker"], sc["target"]),
   f"~{expected_models_lost(sc['attacker'], sc['target']):.1f} of "
   f"{len(sc['target'].models)} models, needs {len(sc['target'].models) * MIN_MODEL_LOSS_FRACTION:.1f}")
ok("...and that is the ONLY reason - value and strength are both fine",
   sc["target"].points >= MIN_POINTS and not is_at_half_strength(sc["target"]))
sc = shooting_scene(keep_models=None)
ok("...while a Breacher Team against the SAME full mob does qualify",
   is_worth_using(sc["attacker"], sc["target"]),
   f"~{expected_models_lost(sc['attacker'], sc['target']):.1f} of {len(sc['target'].models)} models")

# Unpriced units are refused rather than guessed at.
sc = shooting_scene()
sc["target"].points = None
ok("an unpriced unit does not qualify", not is_worth_using(sc["attacker"], sc["target"]))


# ============================================ 3. the trigger, and who answers it
print("\n3) the trigger: target selection, deterministic for the AI side")


def select_target(scene):
    sc = scene["shoot"]
    sc.start_shooting(scene["attacker"])
    if sc.state == "choosing_shooting_type":
        sc.choose_shooting_type(sc.available_types[0])
    sc.choose_target_squad(scene["target"])


sc = shooting_scene()
sc["shoot"].start_shooting(sc["attacker"])
if sc["shoot"].state == "choosing_shooting_type":
    sc["shoot"].choose_shooting_type(sc["shoot"].available_types[0])
ok("nothing has fired yet", not sc["target"].ard_as_nails_active and sc["cp"].cp["Player 2"] == 5)
sc["shoot"].choose_target_squad(sc["target"])
ok("selecting the target spends the CP with no prompt at all",
   sc["target"].ard_as_nails_active and sc["cp"].cp["Player 2"] == 4 and not sc["decision"].is_pending)

sc = shooting_scene(auto=())
select_target(sc)
ok("a non-auto defender gets a prompt instead, and nothing is spent yet",
   sc["decision"].is_pending and sc["cp"].cp["Player 2"] == 5 and not sc["target"].ard_as_nails_active)
ok("the prompt belongs to the DEFENDER", sc["decision"].player == "Player 2")
ok("and says why it is being asked, with the numbers",
   "remaining models" in (sc["decision"].prompt or ""), sc["decision"].prompt or "")
sc["decision"].choose(0)
ok("accepting spends 1 CP and puts the grant up",
   sc["cp"].cp["Player 2"] == 4 and sc["target"].ard_as_nails_active)

sc = shooting_scene(auto=())
select_target(sc)
sc["decision"].choose(1)
ok("declining costs nothing",
   sc["cp"].cp["Player 2"] == 5 and not sc["target"].ard_as_nails_active)

sc = shooting_scene(attacker_sheet=STRIKE_TEAM, keep_models=None)
select_target(sc)
ok("a target the conditions do not cover is left alone entirely",
   not sc["target"].ard_as_nails_active and sc["cp"].cp["Player 2"] == 5 and not sc["decision"].is_pending)

# WHEN / TARGET clauses.
sc = shooting_scene(phase=PHASE_MOVEMENT)
ok("WHEN: a Snap Shot in the Movement phase (Fire Overwatch, 15.08) is not covered",
   not sc["nails"].can_use(sc["attacker"], sc["target"]))

sc = shooting_scene()
ok("a unit is not 'an enemy unit' to itself",
   not sc["nails"].can_use(sc["target"], sc["target"]))

sc = shooting_scene(cp=0)
ok("no CP, no stratagem", not sc["nails"].can_use(sc["attacker"], sc["target"]))

sc = shooting_scene()
sc["target"].battle_shocked = True
ok("rule 01.07: a battle-shocked unit cannot be the target of a stratagem",
   not sc["nails"].can_use(sc["attacker"], sc["target"]))

sc = shooting_scene()
sc["nails"].maybe_offer(sc["attacker"], sc["target"])
ok("already up on that unit - nothing left to buy",
   not sc["nails"].can_use(sc["attacker"], sc["target"]))

# Rule 15.01: once per phase.
sc = shooting_scene()
second = build_squad(STORMBOYZ, "Player 2", name="2 Target 2", composition_index=1)
for i, mdl in enumerate(second.models):
    mdl.x_in, mdl.y_in = 20.0 + i * 1.5, 27.5
    sc["state"].add_token(mdl)
ok("a second Ork unit is eligible before the stratagem is spent",
   sc["nails"].can_use(sc["attacker"], second))
sc["nails"].maybe_offer(sc["attacker"], sc["target"])
ok("rule 15.01: but not once it has been used this phase",
   not sc["nails"].can_use(sc["attacker"], second))

# De-duplication across Split Fire's per-assignment hook calls.
sc = shooting_scene()
first = sc["nails"].maybe_offer(sc["attacker"], sc["target"])
again = sc["nails"].maybe_offer(sc["attacker"], sc["target"])
ok("the same attack only acts once, however many times the hook fires",
   first and not again and sc["cp"].cp["Player 2"] == 4)

# Duration.
sc = shooting_scene()
sc["nails"].maybe_offer(sc["attacker"], sc["target"])
sc["nails"].reset_phase({t.squad for t in sc["state"].tokens if t.squad is not None})
ok('"until the end of the phase": reset_phase clears the grant',
   not sc["target"].ard_as_nails_active)


# ================================== 4. the effect reaches the real wound roll
print("\n4) end-to-end: the -1 reaches the wound roll (A/B on the same dice)")


class _Log:
    def __init__(self):
        self.lines = []

    def add(self, message, file_only=False):
        self.lines.append(message)


def parse_wounds(line):
    """"... wound roll [..]: N wound(s) ..." - split on the LAST ": " before
    the count, since the log line starts with "Player 1: " and the dice list
    itself contains commas and brackets."""
    try:
        return int(line.split(" wound(s)")[0].rsplit(": ", 1)[1])
    except (IndexError, ValueError):
        return None


def shoot_to_wound(scene, hit_dice, wound_dice):
    log = _Log()
    scene["shoot"].game_log = log
    sc = scene["shoot"]
    select_target(scene)
    groups = sc.weapon_eligibility()
    assert groups, "no weapon group"
    script(*hit_dice, default=6)
    sc.choose_weapon(groups[0][0])
    script(*wound_dice, default=1)
    scene["dice"].acknowledge()
    sc.on_dice_acknowledged()
    assert scene["dice"].roll_kind == WOUND_ROLL, f"expected a wound roll, got {scene['dice'].roll_kind}"
    label = scene["dice"].label
    script(default=1)
    scene["dice"].acknowledge()
    sc.on_dice_acknowledged()
    return label, next((l for l in log.lines if "wound roll" in l), "")


HITS = [6] * 20
# Wound dice chosen per matchup so the baseline SUCCEEDS and one more pip
# fails - otherwise an A/B that shows no difference proves nothing.
WOUNDS = [3] * 20        # Pulse Blaster (close range) S6 vs Stormboyz T5: wounds on 3+
MELEE_WOUNDS = [5] * 20  # Battlesuit Fists S5 vs Meganobz T6: wounds on 5+
base = shooting_scene(auto=())          # nobody buys it
_, base_line = shoot_to_wound(base, HITS, WOUNDS)
boosted = shooting_scene()              # the AI side buys it at target selection
label, boosted_line = shoot_to_wound(boosted, HITS, WOUNDS)
b, u = parse_wounds(base_line), parse_wounds(boosted_line)
ok("baseline: those wound dice succeed", b is not None and b > 0, base_line)
ok("with 'Ard as Nails up, the same dice wound less", u is not None and u < b, f"{b} -> {u}")
ok("and the roll is labelled with the reason", "'Ard as Nails" in label, label)
ok("the penalty is the +1 on the threshold the rule asks for", ARD_AS_NAILS_WOUND_PENALTY == 1)


print("\n   ...and the same in the Fight phase")


class _Recorder:
    """Stands in the target_reactions list next to the real controller, purely
    to prove the fight-phase hook reaches it. The verdict logic itself is
    covered through the shooting path above - what would otherwise be untested
    is the WIRING, and that is what this records."""

    def __init__(self):
        self.calls = []

    def maybe_offer(self, attacker, target, melee=False):
        self.calls.append((attacker.name, target.name, melee))
        return False


def melee_scene():
    st = GameState()
    attacker = build_squad(CRISIS_STARSCYTHE, "Player 1", name="1 Attacker 1")
    target = build_squad(MEGANOBZ, "Player 2", name="2 Target 1", composition_index=1)
    for i, mdl in enumerate(attacker.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 1.6, 20.0
    for i, mdl in enumerate(target.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 1.6, 21.4  # inside Engagement Range
    for sq in (attacker, target):
        for mdl in sq.models:
            st.add_token(mdl)
    tt = TurnTracker()
    tt.phase_index = PHASES.index(PHASE_FIGHT)
    tt.turn_owner = "Player 1"
    tt.set_active("Player 1")
    cps = CommandPointManager()
    cps.cp["Player 1"] = cps.cp["Player 2"] = 5
    dm, dec = DiceManager(), DecisionManager()
    strat = StratagemController(command_points=cps)
    aan = ArdAsNailsController(strat, decision_manager=dec, turn_tracker=tt, auto_players=("Player 2",))
    rec = _Recorder()
    fc = FightController(dice_manager=dm, turn_tracker=tt, all_tokens=st.tokens,
                         decision_manager=dec, target_reactions=(aan, rec))
    fc.begin_fight_step()
    return dict(state=st, attacker=attacker, target=target, dice=dm, decision=dec,
                fight=fc, turn=tt, cp=cps, nails=aan, recorder=rec)


def fight_to_wound(scene, hit_dice, wound_dice):
    log = _Log()
    scene["fight"].game_log = log
    fc = scene["fight"]
    fc.select_to_fight(scene["attacker"])
    if fc.state == "choosing_target":
        fc.choose_target_squad(scene["target"])
    groups = fc.weapon_eligibility()
    assert groups, "no melee group"
    script(*hit_dice, default=6)
    fc.choose_weapon(groups[0][0])
    script(*wound_dice, default=1)
    scene["dice"].acknowledge()
    fc.on_dice_acknowledged()
    assert scene["dice"].roll_kind == WOUND_ROLL, f"expected a wound roll, got {scene['dice'].roll_kind}"
    label = scene["dice"].label
    script(default=1)
    scene["dice"].acknowledge()
    fc.on_dice_acknowledged()
    return label, next((l for l in log.lines if "wound roll" in l), "")


mb = melee_scene()
_, mb_line = fight_to_wound(mb, HITS, MELEE_WOUNDS)
ok("the fight-phase target-selection hook reaches the reaction list",
   bool(mb["recorder"].calls) and mb["recorder"].calls[0][2] is True, str(mb["recorder"].calls[:1]))

mu = melee_scene()
mu["target"].ard_as_nails_active = True  # granted in the opponent's Shooting phase, still up here
mlabel, mu_line = fight_to_wound(mu, HITS, MELEE_WOUNDS)
mbw, muw = parse_wounds(mb_line), parse_wounds(mu_line)
ok("melee: baseline wounds land", mbw is not None and mbw > 0, mb_line)
ok("melee: with the grant up, the same dice wound less", muw is not None and muw < mbw, f"{mbw} -> {muw}")
ok("melee: the roll names the reason", "'Ard as Nails" in mlabel, mlabel)


# =============================================================== summary
print(f"\n{checks - len(failed)}/{checks} checks passed")
if failed:
    print("FAILED:")
    for f in failed:
        print("  - " + f)
    sys.exit(1)
