"""Tests for War Horde's Unbridled Carnage stratagem
(game/unbridled_carnage.py) and the AI's deterministic use of it
(ai/agent_driver.py's _unbridled_carnage_verdict()).

RULE (user-supplied): 1CP, War Horde Battle Tactic Stratagem. WHEN Fight
phase. TARGET one ORKS unit from your army that has not been selected to
fight this phase. EFFECT until the end of the phase, each time a model in
your unit makes a melee attack, an unmodified hit roll of 5+ scores a
Critical Hit.

Three things carry real risk and so get the most attention here:

  * that the lowered threshold reaches the ACTUAL hit resolution and is read
    off the RAW die ("unmodified"), measured through the real FightController
    with scripted dice rather than by inspecting a helper - and with an A/B,
    so the extra hits are proven to come from the stratagem and not from War
    Horde's own Get Stuck In, which is up either way;
  * that it is melee-only and expires, i.e. a ranged attack in a later phase
    can never see it;
  * the AI's deterministic verdict, which is a policy and not a rule: that it
    buys the CP when the target survives, does NOT when something engaged can
    already be wiped out, picks the higher-output unit when several qualify,
    and never asks the agent (the test agent raises on decide(), so "no API
    call" is proven rather than assumed).

Uses real StratagemController/CommandPointManager/DecisionManager/
TurnTracker/FightController/GameState objects and real datasheets throughout.

Run: python test_unbridled_carnage.py
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ai import agent_driver
from game import dice as dice_mod
from game import maps
from game.attached_units import attach
from game.command_points import CommandPointManager
from game.decision import DecisionManager
from game.dice import DiceManager, HIT_ROLL
from game.factions import build_squad
from game.factions.orks import BOYZ, GRETCHIN, MEGANOBZ, WARBOSS
from game.factions.tau_empire import BREACHER_TEAM, STRIKE_TEAM
from game.fight import FightController
from game.game_state import GameState
from game.stratagems import StratagemController
from game.turn import PHASES, PHASE_FIGHT, PHASE_SHOOTING, TurnTracker
# The threshold lookup and its constants moved to game/crit_hit.py (via
# game/melee_crit.py) when
# Striking Scorpions' Mandiblasters became a second source for the same number -
# see that module's docstring. The controller and is_orks_unit stay here.
from game.crit_hit import (
    DEFAULT_CRIT_HIT_THRESHOLD, UNBRIDLED_CARNAGE_CRIT_HIT_THRESHOLD, crit_hit_threshold,
)
from game.unbridled_carnage import UnbridledCarnageController, is_orks_unit

m = maps.get("map2")
maps.apply_to_config(m)

checks, failed = 0, []


def ok(label, cond, detail=""):
    global checks
    checks += 1
    if not cond:
        failed.append(label)
    print(("  PASS  " if cond else "  FAIL  ") + label + ((" - " + detail) if detail else ""))


# --------------------------------------------------------------- scripted dice
_scripted = []
_default = [None]  # what an unscripted die shows; None = its best face


def _scripted_randint(low, high):
    if _scripted:
        return _scripted.pop(0)
    return high if _default[0] is None else _default[0]


dice_mod.random.randint = _scripted_randint


def script(*values, default=None):
    _scripted[:] = list(values)
    _default[0] = default


class RaisingAgent:
    """Any decide() call is a bug in the deterministic path under test."""

    def decide(self, *args, **kwargs):
        raise AssertionError("the deterministic Unbridled Carnage path must never call the agent")


def melee_scene(attacker_sheet=BOYZ, target_sheet=STRIKE_TEAM, cp=5, attacker_owner="Player 2"):
    """Two engaged squads in the Fight phase, with the Fight step begun."""
    st = GameState()
    defender_owner = "Player 1" if attacker_owner == "Player 2" else "Player 2"
    attacker = build_squad(attacker_sheet, attacker_owner, name=f"{attacker_owner[-1]} Attacker 1")
    target = build_squad(target_sheet, defender_owner, name=f"{defender_owner[-1]} Target 1")
    for i, mdl in enumerate(attacker.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 1.4, 20.0
    for i, mdl in enumerate(target.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 1.4, 21.2  # inside Engagement Range
    for sq in (attacker, target):
        for mdl in sq.models:
            st.add_token(mdl)

    tt = TurnTracker()
    tt.phase_index = PHASES.index(PHASE_FIGHT)
    tt.turn_owner = attacker_owner
    tt.set_active(attacker_owner)
    cps = CommandPointManager()
    cps.cp["Player 1"] = cp
    cps.cp["Player 2"] = cp
    dm, dec = DiceManager(), DecisionManager()
    strat = StratagemController(command_points=cps)
    fc = FightController(dice_manager=dm, turn_tracker=tt, all_tokens=st.tokens, decision_manager=dec)
    fc.begin_fight_step()
    uc = UnbridledCarnageController(strat, fight_controller=fc, turn_tracker=tt)
    return dict(
        state=st, attacker=attacker, target=target, dice=dm, decision=dec, fight=fc,
        turn=tt, cp=cps, stratagems=strat, carnage=uc,
    )


# ============================================================ 1. the effect
print("\n1) the effect: what threshold a melee hit roll uses")

sc = melee_scene()
boy = sc["attacker"].models[0]
ok("without the stratagem a melee Critical Hit needs an unmodified 6 (rule 05.02)",
   crit_hit_threshold(boy, melee_only=True) == DEFAULT_CRIT_HIT_THRESHOLD == 6)
sc["attacker"].unbridled_carnage_active = True
ok("with it up, a 5 is enough",
   crit_hit_threshold(boy, melee_only=True) == UNBRIDLED_CARNAGE_CRIT_HIT_THRESHOLD == 5)
ok("the ENEMY unit is unaffected by our grant",
   crit_hit_threshold(sc["target"].models[0], melee_only=True) == 6)
ok("a model with no squad degrades to the default rather than crashing",
   crit_hit_threshold(None, melee_only=True) == 6)

ok("Boyz are an ORKS unit", is_orks_unit(sc["attacker"]))
ok("a T'au Strike Team is not", not is_orks_unit(sc["target"]))
ok("an empty/None unit is not", not is_orks_unit(None))

# Rule 19.03: an attached unit has all its components' keywords.
sc2 = melee_scene()
warboss = build_squad(WARBOSS, "Player 2", name="2 Warboss 1")
for mdl in warboss.models:
    mdl.x_in, mdl.y_in = 19.0, 20.0
    sc2["state"].add_token(mdl)
attach(warboss, sc2["attacker"], sc2["state"])
ok("rule 19.03: a Boyz+Warboss attached unit is still an ORKS unit", is_orks_unit(sc2["attacker"]))


# ================================================== 2. end-to-end, with an A/B
print("\n2) end-to-end through the real FightController (A/B on the same dice)")


def run_hit_roll(scene, dice_values):
    """Select, target, swing one weapon group with exactly `dice_values` as the
    hit roll, and report (hits, crits) from the log line the controller wrote."""
    fc = scene["fight"]
    fc.select_to_fight(scene["attacker"])
    if fc.state == "choosing_target":
        fc.choose_target_squad(scene["target"])
    groups = fc.weapon_eligibility()
    assert groups, "no melee weapon group to swing"
    script(*dice_values)
    fc.choose_weapon(groups[0][0])
    assert scene["dice"].is_pending and scene["dice"].roll_kind == HIT_ROLL, "no hit roll on the table"
    rolled = list(scene["dice"].pending_values)
    script(default=1)  # every wound die fails - this test only cares about hits
    scene["dice"].acknowledge()
    fc.on_dice_acknowledged()
    return rolled


class _Log:
    def __init__(self):
        self.lines = []

    def add(self, message, file_only=False):
        self.lines.append(message)


def hit_line(log):
    return next((l for l in log.lines if "hit roll" in l), "")


# One shared roll for both halves: a 5 and a 6, so the difference between the
# two runs can only come from how the 5 is CLASSIFIED.
DICE = [5, 6, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]

base = melee_scene()
base_log = _Log()
base["fight"].game_log = base_log
run_hit_roll(base, DICE)
base_hits = hit_line(base_log)

boosted = melee_scene()
boosted_log = _Log()
boosted["fight"].game_log = boosted_log
ok("the AI's Ork unit can buy it", boosted["carnage"].can_use(boosted["attacker"]))
ok("using it spends exactly 1 CP",
   boosted["carnage"].use(boosted["attacker"]) and boosted["cp"].cp["Player 2"] == 4)
ok("and the grant is up on that unit", boosted["attacker"].unbridled_carnage_active is True)
run_hit_roll(boosted, DICE)
boosted_hits = hit_line(boosted_log)


def parse_hits(line):
    # "... hit roll [...]: N hit(s) (of which M critical), K miss(es)."
    try:
        after = line.split(": ", 1)[1]
        n = int(after.split(" hit(s)")[0])
        crit = int(after.split("of which ")[1].split(" critical")[0])
        return n, crit
    except (IndexError, ValueError):
        return None, None


def sustained_extra(log):
    """[SUSTAINED HITS]'s own extra hits, which fight.py logs on a SEPARATE
    line - as shooting.py has always done, and as fight.py now does too
    since Beast Snagga Boyz' Monster Hunters re-roll can interpose between
    the hit roll and the extra hits it grants (the extras have to be counted
    off whichever roll finally stands, so they cannot be folded into the
    "hit roll" line the way they used to be). Purely a logging split - the
    hit total the rest of the sequence receives is unchanged."""
    line = next((l for l in log.lines if "[SUSTAINED HITS] adds" in l), "")
    try:
        return int(line.split("adds ")[1].split(" extra")[0])
    except (IndexError, ValueError):
        return 0


def total_hits(log):
    hits, crits = parse_hits(hit_line(log))
    return (None if hits is None else hits + sustained_extra(log)), crits


b_hits, b_crits = total_hits(base_log)
u_hits, u_crits = total_hits(boosted_log)
ok("baseline: only the natural 6 is a Critical Hit", b_crits == 1, base_hits)
ok("with Unbridled Carnage the natural 5 is critical too", u_crits == 2, boosted_hits)
ok("the 5 still HITS in both runs (it was always a hit, just not critical)",
   b_hits is not None and u_hits is not None and u_hits > b_hits,
   f"{b_hits} -> {u_hits}")
ok("and the extra hit comes from War Horde's [SUSTAINED HITS 1] on the extra crit",
   u_hits - b_hits == u_crits - b_crits, f"+{u_hits - b_hits} hits for +{u_crits - b_crits} crits")

# "Unmodified": the raw die is what counts. A 1 is always a miss (rule 05.01)
# and never becomes a critical hit no matter what the threshold is.
one_only = melee_scene()
one_only["carnage"].use(one_only["attacker"])
one_log = _Log()
one_only["fight"].game_log = one_log
run_hit_roll(one_only, [1] * 30)
_, crits_on_ones = parse_hits(hit_line(one_log))
ok("rule 05.01 still wins: an unmodified 1 is never a Critical Hit", crits_on_ones == 0)


# ============================================================ 3. WHEN / TARGET
print("\n3) WHEN / TARGET clauses")

sc = melee_scene()
ok("WHEN: not offered outside the Fight phase",
   (sc["turn"].__setattr__("phase_index", PHASES.index(PHASE_SHOOTING)) or True)
   and not sc["carnage"].can_use(sc["attacker"]))
sc["turn"].phase_index = PHASES.index(PHASE_FIGHT)
ok("...and offered again once it is the Fight phase", sc["carnage"].can_use(sc["attacker"]))

ok("TARGET: a non-ORKS unit is never eligible", not sc["carnage"].can_use(sc["target"]))

sc = melee_scene()
sc["fight"].fought_squad_ids.add(sc["attacker"])
ok("TARGET: a unit that has already fought this phase is not eligible",
   not sc["carnage"].can_use(sc["attacker"]))

sc = melee_scene()
sc["fight"].select_to_fight(sc["attacker"])
ok("TARGET: a unit MID-activation has been selected to fight - not eligible either",
   sc["fight"].fighting_squad is sc["attacker"] and not sc["carnage"].can_use(sc["attacker"]))

# Certainty check: a unit not in combat at all can never make a melee attack.
sc = melee_scene()
for mdl in sc["attacker"].models:
    mdl.y_in = 40.0
sc["fight"].engaged_at_start = set()
ok("a unit that cannot fight this phase is refused (the CP would buy nothing)",
   not sc["fight"].is_eligible_to_fight(sc["attacker"]) and not sc["carnage"].can_use(sc["attacker"]))

sc = melee_scene(cp=0)
ok("no CP, no stratagem", not sc["carnage"].can_use(sc["attacker"]))

sc = melee_scene()
sc["attacker"].battle_shocked = True
ok("rule 01.07: a battle-shocked unit cannot be the target of a stratagem",
   not sc["carnage"].can_use(sc["attacker"]))

sc = melee_scene()
sc["carnage"].use(sc["attacker"])
ok("already active on that unit - nothing left to buy", not sc["carnage"].can_use(sc["attacker"]))

# Rule 15.01: once per phase, so a SECOND Ork unit cannot also get it.
sc = melee_scene()
second = build_squad(MEGANOBZ, "Player 2", name="2 Attacker 2", composition_index=0)
for i, mdl in enumerate(second.models):
    mdl.x_in, mdl.y_in = 20.0 + i * 1.6, 19.0
    sc["state"].add_token(mdl)
for i, mdl in enumerate(sc["target"].models):
    mdl.y_in = 20.0  # engage both Ork units
sc["fight"].engaged_at_start = {sc["attacker"], second, sc["target"]}
ok("a second Ork unit is eligible before the stratagem is spent", sc["carnage"].can_use(second))
sc["carnage"].use(sc["attacker"])
ok("rule 15.01: but not once it has been used this phase", not sc["carnage"].can_use(second))

# WHEN is the bare "Fight phase", which is shared (rule 12.04) - so the
# player who does not own the turn can use it too.
sc = melee_scene(attacker_owner="Player 2")
sc["turn"].turn_owner = "Player 1"
sc["turn"].set_active("Player 1")
ok("the Fight phase is shared (12.04): the non-active player may still use it",
   sc["carnage"].can_use(sc["attacker"]))


# ================================================ 4. duration: melee-only, expires
print("\n4) duration and scope")

sc = melee_scene()
sc["carnage"].use(sc["attacker"])
sc["carnage"].reset_phase({t.squad for t in sc["state"].tokens if t.squad is not None})
ok('"until the end of the phase": reset_phase clears the grant',
   sc["attacker"].unbridled_carnage_active is False)
ok("and back to the default threshold with it", crit_hit_threshold(sc["attacker"].models[0], melee_only=True) == 6)

sc = melee_scene()
sc["carnage"].use(sc["attacker"])
sc["carnage"].reset_phase({sc["attacker"], sc["target"]})
ok("both armies are cleared (the Fight phase is shared, either side can hold a grant)",
   not sc["attacker"].unbridled_carnage_active and not sc["target"].unbridled_carnage_active)

# Ranged attacks never read the flag: game/shooting.py's own hit step passes
# no crit threshold at all, so rule 05.02's 6 is structural there.
import inspect

import game.shooting as shooting_mod
import game.unbridled_carnage as uc_mod

ok("no ranged code path reads the grant at all",
   "unbridled_carnage" not in inspect.getsource(shooting_mod))


# ==================================================== 5. the AI's deterministic use
print("\n5) the AI's deterministic verdict (no agent call anywhere)")

# A Boyz mob into a full 10-model Strike Team: it cannot erase them, so buy it.
sc = melee_scene(attacker_sheet=BOYZ, target_sheet=STRIKE_TEAM)
verdict = agent_driver._unbridled_carnage_verdict(sc["attacker"], sc["fight"])
ok("a target it cannot wipe out returns a positive verdict",
   verdict is not None and verdict > 0, f"{verdict}")
ok("...and the handler actually spends the CP for it",
   agent_driver._handle_unbridled_carnage("Player 2", sc["state"].tokens, sc["fight"], sc["carnage"])
   and sc["attacker"].unbridled_carnage_active and sc["cp"].cp["Player 2"] == 4)
ok("a second call does nothing (already up, and 15.01 has been spent)",
   not agent_driver._handle_unbridled_carnage("Player 2", sc["state"].tokens, sc["fight"], sc["carnage"]))

# Same mob against a single wounded model it will certainly erase: keep the CP.
sc = melee_scene(attacker_sheet=BOYZ, target_sheet=STRIKE_TEAM)
survivor = sc["target"].models[0]
for mdl in sc["target"].models[1:]:
    mdl.current_wounds = 0
survivor.current_wounds = 1
ok("a target it can erase outright returns no verdict",
   agent_driver._unbridled_carnage_verdict(sc["attacker"], sc["fight"]) is None)
ok("...so no CP is spent",
   not agent_driver._handle_unbridled_carnage("Player 2", sc["state"].tokens, sc["fight"], sc["carnage"])
   and sc["cp"].cp["Player 2"] == 5)

# Engaged with nothing at all -> no verdict (there is no melee attack to buff).
sc = melee_scene()
for mdl in sc["target"].models:
    mdl.y_in = 40.0
ok("a unit engaged with nothing returns no verdict",
   agent_driver._unbridled_carnage_verdict(sc["attacker"], sc["fight"]) is None)

# Ranking: with two eligible Ork units, the higher-output one gets it, since
# rule 15.01 only allows one use per phase.
sc = melee_scene(attacker_sheet=BOYZ, target_sheet=BREACHER_TEAM)
grots = build_squad(GRETCHIN, "Player 2", name="2 Attacker 2")
for i, mdl in enumerate(grots.models):
    mdl.x_in, mdl.y_in = 20.0 + i * 1.2, 22.4
    sc["state"].add_token(mdl)
for i, mdl in enumerate(sc["target"].models):
    mdl.x_in, mdl.y_in = 20.0 + i * 1.4, 21.2
sc["fight"].engaged_at_start = {sc["attacker"], grots, sc["target"]}
boyz_value = agent_driver._unbridled_carnage_verdict(sc["attacker"], sc["fight"])
grot_value = agent_driver._unbridled_carnage_verdict(grots, sc["fight"])
ok("both Ork units qualify against a target neither can wipe",
   boyz_value is not None and grot_value is not None, f"boyz={boyz_value} grots={grot_value}")
ok("the higher-output unit is ranked first", boyz_value > grot_value)
agent_driver._handle_unbridled_carnage("Player 2", sc["state"].tokens, sc["fight"], sc["carnage"])
ok("...and is the one that gets the stratagem",
   sc["attacker"].unbridled_carnage_active and not grots.unbridled_carnage_active)

# Never touches the opponent's units.
sc = melee_scene(attacker_sheet=BOYZ, target_sheet=STRIKE_TEAM)
ok("Player 1 has nothing Orky, so its own call is a no-op",
   not agent_driver._handle_unbridled_carnage("Player 1", sc["state"].tokens, sc["fight"], sc["carnage"])
   and not sc["attacker"].unbridled_carnage_active)

# Through the real _handle_fight() entry point, with an agent that raises.
sc = melee_scene(attacker_sheet=BOYZ, target_sheet=STRIKE_TEAM)
memory = agent_driver.AIMemory()
acted = agent_driver._handle_fight(
    RaisingAgent(), memory, "Player 2", sc["state"].tokens, sc["fight"],
    sc["fight"].pile_in_controller, None, None,
    unbridled_carnage_controller=sc["carnage"],
)
ok("_handle_fight() buys it before selecting anyone to fight, with 0 agent calls",
   acted and sc["attacker"].unbridled_carnage_active and sc["fight"].fighting_squad is None)
ok("a missing controller is simply skipped",
   not agent_driver._handle_unbridled_carnage("Player 2", sc["state"].tokens, sc["fight"], None))


# =============================================================== summary
print(f"\n{checks - len(failed)}/{checks} checks passed")
if failed:
    print("FAILED:")
    for f in failed:
        print("  - " + f)
    sys.exit(1)
