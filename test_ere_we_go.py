"""Tests for War Horde's 'Ere We Go stratagem (game/ere_we_go.py) and the AI's
deterministic use of it (ai/agent_driver.py's _handle_ere_we_go()).

RULE (user-supplied): 1CP, War Horde Battle Tactic Stratagem. WHEN start of
your Movement phase. TARGET one ORKS INFANTRY unit from your army. EFFECT
until the end of the turn, add 2 to Advance and Charge rolls made for your
unit.

Used DETERMINISTICALLY, per the user: at the first opportunity of the WAAAGH!
turn.

Four things carry real risk and so get the most attention here:

  * that the +2 reaches BOTH rolls through the real controllers, each with an
    A/B on the same dice - and in particular that it survives a Command
    Re-roll of the Advance die, which is where a bonus applied at roll time
    and re-derived at acknowledgement can silently cancel itself;
  * that the +2 lands BEFORE rule 15.11's "greater than 6 after modifiers"
    cap, and that the Command-Re-roll forecast (targets_reachable_with())
    sees the same number the real roll will;
  * the "start of your Movement phase" window, which this engine has to read
    as "nothing of yours has moved yet";
  * that the AI fires it only in the WAAAGH! turn, at the first opportunity,
    on the unit that gains most, with zero agent calls (the test agent raises
    on decide()).

Uses real StratagemController/CommandPointManager/TurnTracker/
MovementController/ChargeController/WaaaghController/GameState objects and
real datasheets throughout.

Run: python test_ere_we_go.py
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ai import agent_driver
from game import dice as dice_mod
from game import maps
from game.attached_units import attach
from game.charge import ChargeController
from game.command_points import CommandPointManager
from game.command_reroll import CommandRerollController
from game.dice import ADVANCE_ROLL, CHARGE_ROLL, DiceManager
from game.ere_we_go import ERE_WE_GO_ROLL_BONUS, EreWeGoController, is_orks_infantry_unit, roll_bonus
from game.factions import build_squad
from game.factions.orks import BOYZ, DEFFKOPTAS, GRETCHIN, MEGANOBZ, STORMBOYZ, TRUKK, WARBIKERS, WARBOSS
from game.factions.tau_empire import STRIKE_TEAM
from game.game_state import GameState
from game.movement import MovementController, advance_total
from game.stratagems import StratagemController
from game.turn import PHASES, PHASE_CHARGE, PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker
from game.waaagh import WaaaghController

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
_default = [None]


def _scripted_randint(low, high):
    if _scripted:
        return _scripted.pop(0)
    return high if _default[0] is None else _default[0]


dice_mod.random.randint = _scripted_randint


def script(*values, default=None):
    _scripted[:] = list(values)
    _default[0] = default


class RaisingAgent:
    def decide(self, *args, **kwargs):
        raise AssertionError("the deterministic 'Ere We Go path must never call the agent")


def scene(phase=PHASE_MOVEMENT, cp=5, waaagh=True, gap_in=14.0, target_sheet=BOYZ, target_kwargs=None):
    """One Ork infantry unit and one enemy unit `gap_in` apart, in the Ork
    player's own turn."""
    st = GameState()
    orks = build_squad(target_sheet, "Player 2", name="2 Boyz 1", **(target_kwargs or {}))
    foe = build_squad(STRIKE_TEAM, "Player 1", name="1 Foe 1")
    for i, mdl in enumerate(orks.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 1.4, 20.0
    for i, mdl in enumerate(foe.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 1.4, 20.0 + gap_in
    for sq in (orks, foe):
        for mdl in sq.models:
            st.add_token(mdl)

    tt = TurnTracker()
    tt.phase_index = PHASES.index(phase)
    tt.turn_owner = "Player 2"
    tt.set_active("Player 2")
    cps = CommandPointManager()
    cps.cp["Player 1"] = cps.cp["Player 2"] = cp
    dm = DiceManager()
    strat = StratagemController(command_points=cps)
    wa = WaaaghController()
    if waaagh:
        wa.active_players.add("Player 2")
    mc = MovementController(obstacles=st.obstacles, turn_tracker=tt, all_tokens=st.tokens, dice_manager=dm)
    cc = ChargeController(dice_manager=dm, turn_tracker=tt, all_tokens=st.tokens, movement_controller=mc, waaagh=wa)
    ewg = EreWeGoController(strat, movement_controller=mc, turn_tracker=tt)
    return dict(state=st, orks=orks, foe=foe, dice=dm, move=mc, charge=cc, turn=tt,
                cp=cps, stratagems=strat, ere=ewg, waaagh=wa)


# ==================================================== 1. TARGET / WHEN clauses
print("\n1) TARGET and WHEN")

sc = scene()
ok("Boyz are an ORKS INFANTRY unit", is_orks_infantry_unit(sc["orks"]))
ok("...and can buy it at the start of their own Movement phase", sc["ere"].can_use(sc["orks"]))
# Selecting a unit is not movement - it is also how the human reaches the
# button, since the ActionPanel only draws it for a selected squad.
sc["move"].select(sc["orks"].models[0])
ok("merely SELECTING the unit does not close the window", sc["ere"].can_use(sc["orks"]))
sc["move"].start_move()
ok("...but an open move does", not sc["ere"].can_use(sc["orks"]))
ok("a T'au unit cannot", not is_orks_infantry_unit(sc["foe"]) and not sc["ere"].can_use(sc["foe"]))
ok("Gretchin ARE infantry, so they qualify (only 'Ard as Nails excludes GROTS)",
   is_orks_infantry_unit(build_squad(GRETCHIN, "Player 2", name="grots")))
ok("a Trukk is not INFANTRY", not is_orks_infantry_unit(build_squad(TRUKK, "Player 2", name="trukk")))
ok("Warbikers are not INFANTRY",
   not is_orks_infantry_unit(build_squad(WARBIKERS, "Player 2", name="bikes", composition_index=0)))
ok("Deffkoptas are not INFANTRY", not is_orks_infantry_unit(build_squad(DEFFKOPTAS, "Player 2", name="koptas")))

# Rule 19.03 keyword pooling.
st = GameState()
boyz = build_squad(BOYZ, "Player 2", name="2 Boyz 1")
wb = build_squad(WARBOSS, "Player 2", name="2 Warboss 1")
for mdl in list(boyz.models) + list(wb.models):
    mdl.x_in, mdl.y_in = 20.0, 20.0
    st.add_token(mdl)
attach(wb, boyz, st)
ok("rule 19.03: Boyz + Warboss is still an ORKS INFANTRY unit", is_orks_infantry_unit(boyz))

sc = scene(phase=PHASE_SHOOTING)
ok("WHEN: not in another phase", not sc["ere"].can_use(sc["orks"]))
sc = scene()
sc["turn"].turn_owner = "Player 1"
ok("WHEN: not in the OPPONENT's Movement phase", not sc["ere"].can_use(sc["orks"]))

sc = scene(cp=0)
ok("no CP, no stratagem", not sc["ere"].can_use(sc["orks"]))
sc = scene()
sc["orks"].battle_shocked = True
ok("rule 01.07: a battle-shocked unit cannot be the target of a stratagem",
   not sc["ere"].can_use(sc["orks"]))
sc = scene()
sc["ere"].use(sc["orks"])
ok("already up on that unit - nothing left to buy", not sc["ere"].can_use(sc["orks"]))

# "START of your Movement phase" - once anything of yours has moved, the window
# is shut, for the whole army and not just the unit that moved.
sc = scene()
other = build_squad(STORMBOYZ, "Player 2", name="2 Stormboyz 1", composition_index=1)
for i, mdl in enumerate(other.models):
    mdl.x_in, mdl.y_in = 30.0 + i * 1.4, 20.0
    sc["state"].add_token(mdl)
ok("a second Ork infantry unit is eligible too", sc["ere"].can_use(other))
sc["move"].select(other.models[0])
sc["move"].remain_stationary()
ok("...but once ANY of your units has moved, the start of the phase has passed",
   not sc["ere"].can_use(sc["orks"]) and not sc["ere"].can_use(other))

# Rule 15.01: once per phase.
sc = scene()
other = build_squad(STORMBOYZ, "Player 2", name="2 Stormboyz 1", composition_index=1)
for i, mdl in enumerate(other.models):
    mdl.x_in, mdl.y_in = 30.0 + i * 1.4, 20.0
    sc["state"].add_token(mdl)
sc["ere"].use(sc["orks"])
ok("rule 15.01: a second unit cannot also get it this phase", not sc["ere"].can_use(other))


# ============================================================ 2. the Advance roll
print("\n2) the Advance roll (+2), A/B on the same die")


def advance_bonus(sc):
    sc["move"].select(sc["orks"].models[0])
    sc["move"].start_move()
    script(3)
    sc["move"].start_run()
    applied = sc["move"].advance_bonus_by_squad[sc["orks"]]
    return applied


base = scene()
b = advance_bonus(base)
boosted = scene()
boosted["ere"].use(boosted["orks"])
u = advance_bonus(boosted)
ok("baseline: a 3 on the Advance die is 3 inches", b == 3, str(b))
ok(f"with 'Ere We Go it is 3 + {ERE_WE_GO_ROLL_BONUS}", u == 3 + ERE_WE_GO_ROLL_BONUS, str(u))
ok("advance_total() is the one definition both roll sites use",
   advance_total(boosted["orks"], [3]) == 5 and advance_total(base["orks"], [3]) == 3)
# The bonus has to reach every model's own movement budget, not just the
# squad-level bookkeeping number. Compared per POSITION in the two scenes'
# model lists, since they are separate Token objects with different ids.
base_ranges = [base["move"].remaining_range[m.id] for m in base["orks"].models]
boosted_ranges = [boosted["move"].remaining_range[m.id] for m in boosted["orks"].models]
ok("every model's own remaining range went up by exactly the bonus",
   len(base_ranges) == len(boosted_ranges) and base_ranges
   and all(u - b == ERE_WE_GO_ROLL_BONUS for b, u in zip(base_ranges, boosted_ranges)),
   f"{base_ranges[:3]} -> {boosted_ranges[:3]}")

# The Command Re-roll reconciliation is where a bonus applied at roll time can
# silently cancel itself, so it gets its own check through the real controller.
sc = scene()
sc["ere"].use(sc["orks"])
sc["move"].select(sc["orks"].models[0])
sc["move"].start_move()
script(2)
sc["move"].start_run()
before_range = dict(sc["move"].remaining_range)
ok("a 2 with the stratagem up is 4 inches", sc["move"].advance_bonus_by_squad[sc["orks"]] == 4)
cr = CommandRerollController(StratagemController(command_points=sc["cp"]), sc["dice"], turn_tracker=sc["turn"])
script(6)
cr.start()
if cr.selecting_die:
    cr.choose_die(0)
sc["dice"].acknowledge()
sc["move"].on_dice_acknowledged()
ok("after a Command Re-roll to a 6 it is 8, not 6 - the +2 survived",
   sc["move"].advance_bonus_by_squad[sc["orks"]] == 6 + ERE_WE_GO_ROLL_BONUS,
   str(sc["move"].advance_bonus_by_squad[sc["orks"]]))
ok("...and the models' remaining range moved by exactly the difference",
   all(sc["move"].remaining_range[k] - before_range[k] == 4 for k in before_range))


# ============================================================= 3. the Charge roll
print("\n3) the Charge roll (+2), A/B on the same dice")


def charge_distance(sc, dice):
    sc["turn"].phase_index = PHASES.index(PHASE_CHARGE)
    script(*dice)
    sc["charge"].declare_charge(sc["orks"])
    sc["dice"].acknowledge()
    sc["charge"].on_dice_acknowledged()
    return sc["charge"].max_distance


base = scene(gap_in=8.0)
bd = charge_distance(base, [3, 4])
boosted = scene(gap_in=8.0)
boosted["ere"].use(boosted["orks"])
ud = charge_distance(boosted, [3, 4])
ok("baseline: 3+4 is a 7 inch charge", bd == 7, str(bd))
ok(f"with 'Ere We Go it is 7 + {ERE_WE_GO_ROLL_BONUS}", ud == 7 + ERE_WE_GO_ROLL_BONUS, str(ud))

# The Command Re-roll forecast has to see the same number the real roll will.
sc = scene(gap_in=8.0)
sc["ere"].use(sc["orks"])
sc["turn"].phase_index = PHASES.index(PHASE_CHARGE)
script(2, 2)
sc["charge"].declare_charge(sc["orks"])
reachable_raw = sc["charge"].targets_reachable_with(4)
ok("targets_reachable_with() applies the +2 too (4 becomes 6, still short of 8)",
   not reachable_raw)
ok("...and a raw 6 becomes 8, which reaches", bool(sc["charge"].targets_reachable_with(6)))
sc["dice"].acknowledge()
sc["charge"].on_dice_acknowledged()
ok("the real roll agrees with the forecast", sc["charge"].max_distance == 6)

# Rule 15.11's cap is "after modifiers", so the +2 lands before it.
sc = scene(gap_in=4.0)
sc["ere"].use(sc["orks"])
sc["turn"].phase_index = PHASES.index(PHASE_CHARGE)
sc["charge"]._mode = "into_the_fray"
sc["charge"].active_squad = sc["orks"]
capped, note = sc["charge"]._capped_roll(5)
ok("Into the Fray (15.11): 5 + 2 = 7 is capped to 6, i.e. the +2 lands BEFORE the cap",
   capped == 6 and "Into the Fray" in note, f"{capped} {note}")
uncapped, _ = sc["charge"]._capped_roll(3)
ok("...while 3 + 2 = 5 is under the cap and stays 5", uncapped == 5)


# ================================================================= 4. duration
print("\n4) duration: until the end of the turn")

sc = scene()
sc["ere"].use(sc["orks"])
ok("the grant is up", roll_bonus(sc["orks"]) == ERE_WE_GO_ROLL_BONUS)
sc["turn"].phase_index = PHASES.index(PHASE_CHARGE)
ok("it survives a phase change (unlike the phase-scoped stratagems)",
   roll_bonus(sc["orks"]) == ERE_WE_GO_ROLL_BONUS)
sc["ere"].expire_for_turn({sc["orks"]})
ok("...and expires at the end of the turn", roll_bonus(sc["orks"]) == 0)
ok("a unit that never had it reads 0", roll_bonus(sc["foe"]) == 0 and roll_bonus(None) == 0)


# =================================================== 5. the AI's deterministic use
print("\n5) the AI's deterministic use (WAAAGH! turn, first opportunity, 0 agent calls)")

sc = scene(gap_in=14.0)
acted = agent_driver._handle_ere_we_go(
    "Player 2", sc["state"].tokens, sc["move"], sc["ere"], sc["waaagh"], sc["turn"], None,
)
ok("in the WAAAGH! turn it buys it straight away",
   acted and sc["orks"].ere_we_go_active and sc["cp"].cp["Player 2"] == 4)
ok("a second call does nothing", not agent_driver._handle_ere_we_go(
    "Player 2", sc["state"].tokens, sc["move"], sc["ere"], sc["waaagh"], sc["turn"], None))

sc = scene(gap_in=14.0, waaagh=False)
ok("outside the WAAAGH! turn it keeps the CP", not agent_driver._handle_ere_we_go(
    "Player 2", sc["state"].tokens, sc["move"], sc["ere"], sc["waaagh"], sc["turn"], None)
   and sc["cp"].cp["Player 2"] == 5)

sc = scene(phase=PHASE_SHOOTING)
ok("and it never fires outside the Movement phase", not agent_driver._handle_ere_we_go(
    "Player 2", sc["state"].tokens, sc["move"], sc["ere"], sc["waaagh"], sc["turn"], None))

sc = scene()
ok("a missing controller is simply skipped", not agent_driver._handle_ere_we_go(
    "Player 2", sc["state"].tokens, sc["move"], None, sc["waaagh"], sc["turn"], None))

# Which unit: the one whose charge odds gain most from the +2. With 6" move,
# a unit 14" away needs an 8 (a coin-flip, so the +2 is worth a lot) while one
# 24" away cannot charge at all this turn.
sc = scene(gap_in=14.0)
far = build_squad(BOYZ, "Player 2", name="2 Boyz 2")
for i, mdl in enumerate(far.models):
    mdl.x_in, mdl.y_in = 20.0 + i * 1.4, 44.0
    sc["state"].add_token(mdl)
near_gain, _ = agent_driver._ere_we_go_gain(sc["orks"], sc["state"].tokens, sc["move"])
far_gain, _ = agent_driver._ere_we_go_gain(far, sc["state"].tokens, sc["move"])
ok("the unit in charge range values it more than one out of reach",
   near_gain > far_gain, f"{near_gain:.0f} vs {far_gain:.0f} percentage points")
agent_driver._handle_ere_we_go(
    "Player 2", sc["state"].tokens, sc["move"], sc["ere"], sc["waaagh"], sc["turn"], None)
ok("...and is the one that gets it",
   sc["orks"].ere_we_go_active and not far.ere_we_go_active)

# Through the real _handle_movement() entry point, with an agent that raises.
sc = scene(gap_in=14.0)
memory = agent_driver.AIMemory()
memory.turn_plan = {"turn_intent": "", "unit_plans": [], "malformed": False}
memory.plan_turn_key = ("Player 2", 1)
acted = agent_driver._handle_movement(
    RaisingAgent(), memory, "Player 2", sc["state"], sc["move"], None, None, None, None,
    waaagh_controller=sc["waaagh"], ere_we_go_controller=sc["ere"],
)
ok("_handle_movement() buys it before anything moves, with 0 agent calls",
   acted and sc["orks"].ere_we_go_active and not sc["move"].moved_squad_ids)


# =============================================================== summary
print(f"\n{checks - len(failed)}/{checks} checks passed")
if failed:
    print("FAILED:")
    for f in failed:
        print("  - " + f)
    sys.exit(1)
