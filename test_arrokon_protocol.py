"""Tests for Retaliation Cadre's The Arro'kon Protocol stratagem
(game/arrokon_protocol.py).

RULE (user-supplied): 1CP, Battle Tactic Stratagem. WHEN your Shooting phase.
TARGET one T'AU EMPIRE BATTLESUIT unit from your army that has not been
selected to shoot this phase. EFFECT until the end of the phase, each time a
model in your unit makes an attack that targets an enemy unit that contains 6
or more models, that attack has the [SUSTAINED HITS 1] ability; if that attack
targets an enemy unit that contains 11 or more models, it has [SUSTAINED
HITS 2] instead.

Three things carry real risk and so get the most attention here:

  * the TIER BOUNDARIES (5/6/10/11 models), and that the count is read LIVE
    rather than frozen at target selection - a unit whose 11th model is
    already dead is a 10-model unit, i.e. tier 1. (That the count is re-read
    once per WEAPON GROUP follows by construction, since the adjuster runs
    inside on_dice_acknowledged(); only the live-vs-snapshot half is asserted
    directly here.);
  * that the grant reaches the actual hit resolution, i.e. that extra hits
    really appear, measured through the real ShootingController rather than
    by inspecting a weapon copy;
  * that eligibility is honest - in particular the "nothing in range is big
    enough" refusal, which gets an A/B so that "suppressed" is proven to come
    from THAT check and not from some other clause quietly rejecting the same
    case (the same trap test_stim_injectors.py documents for its own gate).

Uses real StratagemController/CommandPointManager/DecisionManager/TurnTracker/
ShootingController/GameState objects and real datasheets throughout.

Run: python test_arrokon_protocol.py
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game import arrokon_protocol as ap
from game import dice as dice_mod
from game import maps
from game.arrokon_protocol import ArrokonProtocolController, arrokon_adjusted_weapon, sustained_hits_for_target
from game.attached_units import attach
from game.command_points import CommandPointManager
from game.decision import DecisionManager
from game.dice import DiceManager, HIT_ROLL
from game.factions import build_squad
from game.factions.orks import BOYZ, GRETCHIN, WARBOSS
from game.factions.tau_empire import (COMMANDER_IN_COLDSTAR_BATTLESUIT, CRISIS_STARSCYTHE,
                                      STEALTH_BATTLESUITS, STRIKE_TEAM)
from game.game_state import GameState
from game.shooting import ShootingController
from game.squad import Squad
from game.stratagems import StratagemController
from game.turn import PHASES, PHASE_FIGHT, PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker
from game.weapons import WeaponProfile

# Retaliation Cadre must be DECLARED for this suite: its rule and all six of
# its Stratagems gate on config.RETALIATION_CADRE_PLAYERS, which is empty until
# an army list that fields the detachment is chosen. Set here so the subject of
# these checks actually applies - the same precondition
# test_death_guard_stratagems.py's `detachment_on` exists for.
from game import config as _config  # noqa: E402
_config.RETALIATION_CADRE_PLAYERS = ("Player 1", "Player 2")

m = maps.get("map2")
maps.apply_to_config(m)

PASS, FAIL = [], []


def check(name, condition, detail=""):
    (PASS if condition else FAIL).append(name)
    print(f"  {'OK  ' if condition else 'FAIL'} {name}{(' - ' + detail) if detail else ''}")


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


def place(squad, positions):
    for model, (x, y) in zip(squad.models, positions):
        model.x_in, model.y_in = x, y
    return squad


def row(x, y, n, dx=1.5):
    return [(x + i * dx, y) for i in range(n)]


def trim(squad, n):
    """Cut a real datasheet's unit down to n models, so the tier boundaries can
    be tested on the exact counts the rule names rather than on whatever sizes
    the published compositions happen to offer.

    Asserts rather than silently truncating short: asking for 12 models from a
    datasheet whose largest composition is 11 would otherwise leave every label
    below quoting a count the test never actually used - the exact way a green
    suite can stop meaning what it says."""
    assert len(squad.models) >= n, f"{squad.name} has {len(squad.models)} models, need {n}"
    squad.models = squad.models[:n]
    return squad


def merged(name, *squads):
    """One real Squad holding every model of several builds - the only way to
    get a unit larger than any published composition, for the 'well past the
    boundary' cases."""
    models = [m for squad in squads for m in squad.models]
    return Squad(name, models, owner=squads[0].owner)


class PlainGun(WeaponProfile):
    """A deliberately featureless ranged weapon: no [SUSTAINED HITS] of its
    own, no [LETHAL HITS]/[TORRENT]/[DEVASTATING WOUNDS] to open a decision
    prompt mid-activation, and one attack per model so the hit-roll dice count
    is exactly the model count. Keeps the end-to-end tests measuring THIS rule
    and nothing else."""
    name = "Plain Gun"
    range_in = 36
    attacks = 1
    strength = 5
    ap = 0
    damage = 1


# =============================================================== 1. the tiers
print("\n1) tier boundaries, read from the rule text (6+ -> 1, 11+ -> 2)")

# Gretchin's largest composition is 11 models, which lands exactly on the
# upper boundary - both boundaries (5/6 and 10/11) are therefore real counts,
# not approximations.
for n, expected in ((1, 0), (5, 0), (6, 1), (7, 1), (10, 1), (11, 2)):
    squad = trim(build_squad(GRETCHIN, "Player 2", name=f"g{n}"), n)
    check(f"{n} models -> [SUSTAINED HITS {expected}]", sustained_hits_for_target(squad) == expected,
          f"got {sustained_hits_for_target(squad)}")

# Well past the boundary, so a mis-ordered tier table could not pass by luck.
huge = merged("huge", build_squad(GRETCHIN, "Player 2", name="h1"), build_squad(GRETCHIN, "Player 2", name="h2"))
check(f"{len(huge.models)} models -> still [SUSTAINED HITS 2]", sustained_hits_for_target(huge) == 2)

check("no target at all -> nothing", sustained_hits_for_target(None) == 0)

# Dead models are only stripped from Squad.models once per frame, so a unit
# being shot to pieces mid-activation would otherwise keep its higher tier for
# the rest of that activation.
dying = trim(build_squad(GRETCHIN, "Player 2", name="dying"), 11)
check("11 models is the top tier", sustained_hits_for_target(dying) == 2)
dying.models[0].current_wounds = 0
check("one dead model drops it to 10 alive -> tier 1", sustained_hits_for_target(dying) == 1,
      f"{ap.alive_model_count(dying)} alive of {len(dying.models)} still in the list")
dying.models[0].current_wounds = dying.models[0].profile.wounds

# Rule 19.01: an attached unit is a single unit, so its count is the merged
# total - a 10-model mob plus a joined character is an 11-model unit.
mob = place(trim(build_squad(BOYZ, "Player 2", name="mob"), 10), row(10, 40, 10))
check("10-model mob alone is tier 1", sustained_hits_for_target(mob) == 1)
boss = place(build_squad(WARBOSS, "Player 2", name="boss"), [(24, 40)])
attach(boss, mob)
check("rule 19.01: joining a character pushes it to tier 2", sustained_hits_for_target(mob) == 2,
      f"{ap.alive_model_count(mob)} models after the merge")


# ==================================================== 2. the weapon adjustment
print("\n2) the weapon adjustment (grant, never overwrite, never mutate)")

crisis = place(build_squad(CRISIS_STARSCYTHE, "Player 1", name="crisis"), row(20, 20, 3))
big = place(trim(build_squad(GRETCHIN, "Player 2", name="big"), 11), row(20, 30, 11))
small = place(trim(build_squad(GRETCHIN, "Player 2", name="small"), 4), row(40, 30, 4))
six = place(trim(build_squad(GRETCHIN, "Player 2", name="six"), 6), row(50, 30, 6))

base = PlainGun()
pairs = [(crisis.models[0], base)]

check("no grant, no change", arrokon_adjusted_weapon(base, pairs, big) is base)

crisis.arrokon_protocol_active = True
check("too small a target, no change", arrokon_adjusted_weapon(base, pairs, small) is base)
check("6 models -> [SUSTAINED HITS 1]", arrokon_adjusted_weapon(base, pairs, six).sustained_hits == 1)
check("11 models -> [SUSTAINED HITS 2]", arrokon_adjusted_weapon(base, pairs, big).sustained_hits == 2)
check("the original instance is never mutated", base.sustained_hits == 0)
check("a copy is returned, not the original", arrokon_adjusted_weapon(base, pairs, big) is not base)

# Grants the ability rather than setting it - two sources of the same ability
# do not stack, and a better existing value wins (game/war_horde.py's reading).
already = PlainGun()
already.sustained_hits = 2
check("a better existing [SUSTAINED HITS] is kept, not stacked",
      arrokon_adjusted_weapon(already, [(crisis.models[0], already)], six) is already)
check("and is raised when this rule offers more",
      arrokon_adjusted_weapon(PlainGun(), pairs, big).sustained_hits == 2)

# The flag is read off the ATTACKING model's own unit, so another unit under
# the stratagem cannot lend it.
other = place(build_squad(STEALTH_BATTLESUITS, "Player 1", name="other"), row(30, 20, 3))
check("a different unit's grant does not apply",
      arrokon_adjusted_weapon(base, [(other.models[0], base)], big) is base)
crisis.arrokon_protocol_active = False


# ====================================================== 3. through the engine
print("\n3) through the real ShootingController - do extra hits actually appear?")


def shooting_scene(shooter_sheet, target_sheet, target_models, cp=3):
    """One Battlesuit shooter, one target unit trimmed to an exact size, clear
    line of sight, a single featureless weapon so the activation is exactly
    hit -> wound."""
    st = GameState()
    shooter = build_squad(shooter_sheet, "Player 1", name="1 Shooter 1")
    target = trim(build_squad(target_sheet, "Player 2", name="2 Target 1", composition_index=0), target_models)
    for i, mdl in enumerate(shooter.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 1.5, 20.0
        mdl.weapons = [PlainGun()]
    for i, mdl in enumerate(target.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 1.5, 26.0
    for sq in (shooter, target):
        for mdl in sq.models:
            st.add_token(mdl)
    tt = TurnTracker()
    tt.started = True
    tt.phase_index = PHASES.index(PHASE_SHOOTING)
    tt.turn_owner = tt.active_player = "Player 1"
    cps = CommandPointManager()
    cps.cp["Player 1"] = cp
    strat = StratagemController(command_points=cps)
    dm = DiceManager()
    dec = DecisionManager()
    sc = ShootingController(
        obstacles=st.obstacles, dice_manager=dm, turn_tracker=tt, all_tokens=st.tokens, decision_manager=dec,
    )
    controller = ArrokonProtocolController(
        strat, shooting_controller=sc, all_tokens=st.tokens, turn_tracker=tt,
    )
    return dict(state=st, shooter=shooter, target=target, dice=dm, decision=dec,
                shooting=sc, arrokon=controller, strat=strat, cps=cps, turn=tt)


def fire(scene):
    """Start the activation and return the hit roll's dice tray."""
    sc = scene["shooting"]
    sc.start_shooting(scene["shooter"])
    if sc.state == "choosing_shooting_type":
        sc.choose_shooting_type(sc.available_types[0])
    sc.choose_target_squad(scene["target"])
    sc.choose_weapon(sc.weapon_eligibility()[0][0])
    return scene["dice"]


def ack(scene):
    scene["dice"].acknowledge()
    scene["shooting"].on_dice_acknowledged()


# Three Crisis models, one attack each: hit roll of [6, 6, 4] = 3 hits, two of
# them critical. Without the stratagem the wound roll is 3 dice.
scene = shooting_scene(CRISIS_STARSCYTHE, GRETCHIN, 11)
script(6, 6, 4)
dm = fire(scene)
check("baseline: 3 attacks on the table", dm.is_pending and dm.roll_kind == HIT_ROLL
      and len(dm.pending_values) == 3, str(dm.pending_values))
script(default=1)  # the wound roll's own dice - value irrelevant, only the count is read
ack(scene)
baseline_wound_dice = len(scene["dice"].pending_values)
check("baseline: 2 crits add nothing without the stratagem", baseline_wound_dice == 3,
      f"{baseline_wound_dice} wound dice")

# Same shot, same dice, stratagem up, 12-model target -> [SUSTAINED HITS 2]:
# each of the 2 critical hits adds 2 extra hits, so 3 + 4 = 7.
scene = shooting_scene(CRISIS_STARSCYTHE, GRETCHIN, 11)
check("can_use accepts the unit", scene["arrokon"].can_use(scene["shooter"]))
check("and quotes tier 2 against an 11-model unit", scene["arrokon"].best_available_tier(scene["shooter"]) == 2,
      str(scene["arrokon"].best_available_tier(scene["shooter"])))
check("using it spends exactly 1 CP", scene["arrokon"].use(scene["shooter"]) and scene["cps"].cp["Player 1"] == 2,
      str(scene["cps"].cp["Player 1"]))
check("and sets the grant", scene["shooter"].arrokon_protocol_active)
script(6, 6, 4)
fire(scene)
script(default=1)
ack(scene)
tier2_wound_dice = len(scene["dice"].pending_values)
check("[SUSTAINED HITS 2]: 2 crits add 4 extra hits (3 -> 7)", tier2_wound_dice == 7,
      f"{tier2_wound_dice} wound dice")

# Identical, but a 6-model target -> tier 1, so 2 crits add 2 (3 -> 5).
scene = shooting_scene(CRISIS_STARSCYTHE, GRETCHIN, 6)
scene["arrokon"].use(scene["shooter"])
script(6, 6, 4)
fire(scene)
script(default=1)
ack(scene)
tier1_wound_dice = len(scene["dice"].pending_values)
check("[SUSTAINED HITS 1]: 2 crits add 2 extra hits (3 -> 5)", tier1_wound_dice == 5,
      f"{tier1_wound_dice} wound dice")

# A 5-model target is below both tiers: the grant is up, and buys nothing.
scene = shooting_scene(CRISIS_STARSCYTHE, GRETCHIN, 5)
scene["shooter"].arrokon_protocol_active = True  # forced: can_use() would (correctly) refuse here
script(6, 6, 4)
fire(scene)
script(default=1)
ack(scene)
check("a 5-model target gets no extra hits even with the grant up",
      len(scene["dice"].pending_values) == 3, f"{len(scene['dice'].pending_values)} wound dice")

# A/B: the same shot with the grant removed must go back to 3, proving the
# extra hits above came from THIS rule and not from the datasheet's weapons or
# some other ability in the chain.
scene = shooting_scene(CRISIS_STARSCYTHE, GRETCHIN, 11)
scene["shooter"].arrokon_protocol_active = False
script(6, 6, 4)
fire(scene)
script(default=1)
ack(scene)
check("A/B: without the grant the identical shot is 3 wound dice",
      len(scene["dice"].pending_values) == 3, f"{len(scene['dice'].pending_values)} wound dice")


# ================================================== 4. WHEN / TARGET clauses
print("\n4) WHEN / TARGET clauses")

scene = shooting_scene(CRISIS_STARSCYTHE, GRETCHIN, 11)
c, shooter, tt = scene["arrokon"], scene["shooter"], scene["turn"]

check("your own Shooting phase qualifies", c.can_use(shooter))

tt.phase_index = PHASES.index(PHASE_MOVEMENT)
check("the Movement phase does not", not c.can_use(shooter))
tt.phase_index = PHASES.index(PHASE_FIGHT)
check("the Fight phase does not", not c.can_use(shooter))
tt.phase_index = PHASES.index(PHASE_SHOOTING)

tt.active_player = "Player 2"
check("the OPPONENT's Shooting phase does not (WHEN says 'your')", not c.can_use(shooter))
tt.active_player = "Player 1"

check("a non-BATTLESUIT unit is not a legal target",
      not c.can_use(build_squad(STRIKE_TEAM, "Player 1", name="strike")))

shooter.battle_shocked = True
check("a battle-shocked unit is blocked (rule 01.07)", not c.can_use(shooter))
shooter.battle_shocked = False

scene["cps"].cp["Player 1"] = 0
check("no CP, no offer", not c.can_use(shooter))
scene["cps"].cp["Player 1"] = 3

shooter.arrokon_protocol_active = True
check("already up on this unit, nothing to buy", not c.can_use(shooter))
shooter.arrokon_protocol_active = False

# "has not been selected to shoot this phase", in both of its forms.
scene["shooting"].shot_squad_ids.add(shooter)
check("a unit that already shot is not a legal target", not c.can_use(shooter))
scene["shooting"].shot_squad_ids.discard(shooter)
scene["shooting"].active_squad = shooter
check("nor is one mid-activation (selected, but not yet in shot_squad_ids)", not c.can_use(shooter))
scene["shooting"].active_squad = None
check("and it is legal again once neither holds", c.can_use(shooter))

# Rule 15.01: once per phase, per player.
check("first use succeeds", c.use(shooter))
scene["shooting"].shot_squad_ids.discard(shooter)
second = build_squad(STEALTH_BATTLESUITS, "Player 1", name="1 Stealth 1")
place(second, row(30, 20, 3))
for mdl in second.models:
    mdl.weapons = [PlainGun()]
    scene["state"].add_token(mdl)
check("a second unit cannot use it the same phase (rule 15.01)", not c.can_use(second))
scene["strat"].reset_phase()
check("but can once the phase turns over", c.can_use(second))

# Rule 19.03: an attached unit pools its components' keywords.
scene = shooting_scene(CRISIS_STARSCYTHE, GRETCHIN, 11)
coldstar = place(build_squad(COMMANDER_IN_COLDSTAR_BATTLESUIT, "Player 1", name="coldstar"), [(26, 20)])
for mdl in coldstar.models:
    mdl.weapons = [PlainGun()]
    scene["state"].add_token(mdl)
attach(coldstar, scene["shooter"])
check("rule 19.03: an attached unit still qualifies as BATTLESUIT",
      scene["arrokon"].can_use(scene["shooter"]))


# ============================================== 5. the "buys nothing" refusal
print("\n5) refusing when nothing in range is big enough (with an A/B)")

# Same board, same everything, only the target's SIZE differs.
big_scene = shooting_scene(CRISIS_STARSCYTHE, GRETCHIN, 8)
small_scene = shooting_scene(CRISIS_STARSCYTHE, GRETCHIN, 4)
check("an 8-model enemy in range makes it worth using", big_scene["arrokon"].can_use(big_scene["shooter"]))
check("a 4-model enemy in range does not", not small_scene["arrokon"].can_use(small_scene["shooter"]))
check("and best_available_tier says so", small_scene["arrokon"].best_available_tier(small_scene["shooter"]) == 0)

# A/B: the refusal must come from the size check, not from some other clause
# rejecting the same board. Widen the tiers to include 4 models and the SAME
# scene must now be accepted.
original_tiers = ap.ARROKON_TIERS
ap.ARROKON_TIERS = ((11, 2), (1, 1))
check("A/B: with the tier at 1+ model the same scene IS offered",
      small_scene["arrokon"].can_use(small_scene["shooter"]),
      "so the refusal above came from the size check, not another clause")
ap.ARROKON_TIERS = original_tiers
check("tiers restored", ap.ARROKON_TIERS == original_tiers)

# Out of range is out of reach: a big unit the shooter cannot legally shoot at
# right now does not count either.
far_scene = shooting_scene(CRISIS_STARSCYTHE, GRETCHIN, 11)
for mdl in far_scene["target"].models:
    mdl.y_in += 200.0  # far beyond the 36" PlainGun
check("a big unit out of range does not count", not far_scene["arrokon"].can_use(far_scene["shooter"]))
check("qualifying_target_squads is empty then", far_scene["arrokon"].qualifying_target_squads(far_scene["shooter"]) == [])


# ============================================================ 6. the duration
print("\n6) 'until the end of the phase'")

scene = shooting_scene(CRISIS_STARSCYTHE, GRETCHIN, 11)
scene["arrokon"].use(scene["shooter"])
check("the grant is up", scene["shooter"].arrokon_protocol_active)
scene["arrokon"].reset_phase({t.squad for t in scene["state"].tokens if t.squad is not None})
check("reset_phase expires it", not scene["shooter"].arrokon_protocol_active)
check("and the target squad is untouched by it either way",
      not getattr(scene["target"], "arrokon_protocol_active", False))


# =============================================================== 7. the AI path
print("\n7) the AI decision path (ai/agent_driver.py)")

from ai.agent_driver import AIMemory, _handle_arrokon_for_squad


class ScriptedAgent:
    """Returns a fixed option index and records what it was shown - so the
    test can assert the option text carries the tier, which is the whole
    reason this is an option rather than a prompt-prose rule."""

    def __init__(self, index):
        self.index = index
        self.seen = []

    def decide(self, observation):
        self.seen.append(observation)
        return self.index


def ai_scene(target_models=11, cp=3):
    scene = shooting_scene(CRISIS_STARSCYTHE, GRETCHIN, target_models, cp=cp)
    scene["turn"].turn_owner = scene["turn"].active_player = "Player 1"
    return scene


scene = ai_scene()
memory = AIMemory()
agent = ScriptedAgent(1)  # index 1 = "use it"
tokens = scene["state"].tokens
acted = _handle_arrokon_for_squad(agent, memory, "Player 1", tokens, scene["shooter"], scene["arrokon"], None)
check("the AI is offered the choice", acted and len(agent.seen) == 1)
check("accepting sets the grant", scene["shooter"].arrokon_protocol_active)
check("and spends exactly 1 CP", scene["cps"].cp["Player 1"] == 2, str(scene["cps"].cp["Player 1"]))

scene = ai_scene()
memory = AIMemory()
agent = ScriptedAgent(0)  # index 0 = "don't"
acted = _handle_arrokon_for_squad(agent, memory, "Player 1", scene["state"].tokens, scene["shooter"], scene["arrokon"], None)
check("declining grants nothing", acted and not scene["shooter"].arrokon_protocol_active)
check("and spends no CP", scene["cps"].cp["Player 1"] == 3, str(scene["cps"].cp["Player 1"]))
before = len(agent.seen)
acted_again = _handle_arrokon_for_squad(agent, memory, "Player 1", scene["state"].tokens, scene["shooter"], scene["arrokon"], None)
check("a decline is remembered, not re-asked every call",
      not acted_again and len(agent.seen) == before)

# An ineligible squad must be cached as a decline too - its eligibility check
# ends in a line-of-sight sweep, and re-running that every call for the rest of
# the phase is the perf bug _handle_greater_good_for_squad() documents.
scene = ai_scene(target_models=4)
memory = AIMemory()
agent = ScriptedAgent(1)
_handle_arrokon_for_squad(agent, memory, "Player 1", scene["state"].tokens, scene["shooter"], scene["arrokon"], None)
check("an ineligible squad is never asked", not agent.seen)
check("and is cached so the sweep does not re-run", scene["shooter"].name in memory.declined_arrokon)

# The option text has to carry the tier and the target - a bare yes/no is the
# thing this project has repeatedly found gets answered badly.
scene = ai_scene()
memory = AIMemory()
agent = ScriptedAgent(0)
_handle_arrokon_for_squad(agent, memory, "Player 1", scene["state"].tokens, scene["shooter"], scene["arrokon"], None)
options = agent.seen[0].get("available_actions") or agent.seen[0].get("options") or []
text = " ".join(str(o.get("description", o)) for o in options)
check("the option text quotes the tier", "[SUSTAINED HITS 2]" in text, text[:160])
expected_detail = f"2 Target 1 ({ap.alive_model_count(scene['target'])} models)"
check("and names the target it applies to", expected_detail in text, f"want {expected_detail!r} in {text[:200]!r}")
check("and says it must come before shooting", "BEFORE" in text)


# ===================================================================== summary
print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
for name in FAIL:
    print(f"  FAILED: {name}")
sys.exit(1 if FAIL else 0)
