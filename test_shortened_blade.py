"""Tests for Retaliation Cadre's The Shortened Blade stratagem
(game/shortened_blade.py).

RULE (user-supplied): 2CP, Strategic Ploy. WHEN your Movement phase. TARGET one
T'AU EMPIRE BATTLESUIT unit from your army that is arriving using the Deep
Strike ability this phase. EFFECT the unit can be set up anywhere on the
battlefield more than 6" horizontally from all enemy models. RESTRICTIONS a
unit targeted with it is not eligible to declare a charge that turn.

The whole effect is one number (8" -> 6" from enemy models), so what actually
needs proving is that the number reaches BOTH places that enforce it - Confirm
(_extra_check) and the live drag/overlay predicate (position_valid) - and that
the charge lock really lands. Each of those gets an A/B against the same
position with the stratagem off, so a pass cannot come from the spot having
been legal anyway.

Uses real IngressController/SetupController/StratagemController/
CommandPointManager/ChargeController/GameState objects and real datasheets.

Run: python test_shortened_blade.py
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game import maps
from game.charge import ChargeController
from game.command_points import CommandPointManager
from game.dice import DiceManager
from game.factions import build_squad
from game.factions.orks import GRETCHIN
from game.factions.tau_empire import CRISIS_STARSCYTHE, STRIKE_TEAM
from game.game_state import GameState
from game.ingress import INGRESS_MIN_ENEMY_DISTANCE_IN, IngressController, SHORTENED_BLADE_MIN_ENEMY_DISTANCE_IN
from game.setup import SetupController
from game.shortened_blade import SHORTENED_BLADE_CP_COST, ShortenedBladeController
from game.stratagems import StratagemController
from game.turn import PHASES, PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker

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


def scene(arriving_sheet=CRISIS_STARSCYTHE, cp=4, phase=PHASE_MOVEMENT, active="Player 1"):
    """One reserve unit and one enemy unit, on open ground far from any
    terrain, so the only thing that can make a position illegal is the
    distance rule under test."""
    st = GameState()
    arriving = build_squad(arriving_sheet, "Player 1", name="1 Arriving 1")
    enemy = build_squad(GRETCHIN, "Player 2", name="2 Enemy 1")
    for i, mdl in enumerate(enemy.models):
        mdl.x_in, mdl.y_in = 30.0 + i * 1.4, 22.0  # > 2x the 0.63" Gretchin base, so they do not overlap
        st.add_token(mdl)
    st.reserves.append(arriving)

    tt = TurnTracker()
    tt.started = True
    tt.battle_round = 2  # rule 20.03: reserves arrive from round 2
    tt.phase_index = PHASES.index(phase)
    tt.turn_owner = tt.active_player = active

    cps = CommandPointManager()
    cps.cp["Player 1"] = cp
    strat = StratagemController(command_points=cps)
    setup = SetupController(st, obstacles=st.obstacles, all_tokens=st.tokens,
                            board_width_in=m.width_in, board_height_in=m.height_in)
    ingress = IngressController(setup, st, st.tokens, turn_tracker=tt,
                                board_width_in=m.width_in, board_height_in=m.height_in)
    blade = ShortenedBladeController(strat, ingress_controller=ingress, setup_controller=setup,
                                     turn_tracker=tt, game_log=None)
    return dict(state=st, arriving=arriving, enemy=enemy, turn=tt, cps=cps, strat=strat,
                setup=setup, ingress=ingress, blade=blade)


def start_arrival(sc, x=30.0, y=30.0):
    sc["ingress"].start_ingress(sc["arriving"], x, y)
    return sc["ingress"].is_ingressing(sc["arriving"])


def put_at(sc, y):
    """Line the arriving unit up in a row at a given y, in front of the enemy
    row at y=22 - so the gap is a single number the test controls. Spaced wider
    than twice the 0.98" Crisis base so the row itself is legal (models may not
    overlap) and coherent (<= 2" apart), leaving the distance rule under test as
    the only thing that can reject it."""
    for i, mdl in enumerate(sc["arriving"].models):
        mdl.x_in, mdl.y_in = 30.0 + i * 2.4, y
    return sc["arriving"]


# ============================================================ 1. the distance
print("\n1) the distance rule, in both places that enforce it")

sc = scene()
check("the arrival starts", start_arrival(sc))
check("its models Deep Strike", sc["ingress"].deep_striking(sc["arriving"]))

token = sc["arriving"].models[0]
gap = INGRESS_MIN_ENEMY_DISTANCE_IN - 1.0  # 7" - inside 8", outside 6"
near_y = 22.0 + gap + token.radius_in + sc["enemy"].models[0].radius_in + 0.1

check("without the stratagem, a 7\" spot is refused by the drag/overlay",
      not sc["ingress"].position_valid(sc["arriving"], token, 30.0, near_y))
put_at(sc, near_y)
check("and by Confirm", bool(sc["ingress"]._extra_check(sc["arriving"])),
      "; ".join(sc["ingress"]._extra_check(sc["arriving"])))

check("the stratagem can be used", sc["blade"].use(sc["arriving"]))
check("it costs exactly 2 CP", sc["cps"].cp["Player 1"] == 4 - SHORTENED_BLADE_CP_COST,
      str(sc["cps"].cp["Player 1"]))

# A/B: the identical position, now legal.
check("A/B: with it, the same spot passes the drag/overlay",
      sc["ingress"].position_valid(sc["arriving"], token, 30.0, near_y))
check("A/B: and Confirm", sc["ingress"]._extra_check(sc["arriving"]) == [],
      "; ".join(sc["ingress"]._extra_check(sc["arriving"])))

# It is 6", not "no limit at all".
too_close_y = 22.0 + SHORTENED_BLADE_MIN_ENEMY_DISTANCE_IN - 1.0
check("5\" is still refused - the floor moved, it did not vanish",
      not sc["ingress"].position_valid(sc["arriving"], token, 30.0, too_close_y))
put_at(sc, too_close_y)
errors = sc["ingress"]._extra_check(sc["arriving"])
# The message names the DISTANCE, not this Stratagem. It used to say "(The
# Shortened Blade)", which was true while this was the only source of the rule;
# Baharroth's Cloudstrider and then Windrider Host's Daring Riders arm the same
# relaxed placement, so a message crediting this one would be wrong two times
# in three. What the player needs from it is the number they must clear, and
# that is what is pinned - the assurance moved rather than loosened.
check("and Confirm says so, naming the relaxed distance",
      bool(errors)
      and ('%.0f"' % SHORTENED_BLADE_MIN_ENEMY_DISTANCE_IN) in errors[0],
      "; ".join(errors))
check("...and does NOT credit one of the three sources",
      bool(errors) and "Shortened Blade" not in errors[0], "; ".join(errors))

# The mask the overlay caches has to be told the ground changed.
sc2 = scene()
start_arrival(sc2)
before = sc2["setup"].placement_generation
sc2["blade"].use(sc2["arriving"])
check("using it invalidates the cached placement overlay",
      sc2["setup"].placement_generation > before,
      f"{before} -> {sc2['setup'].placement_generation}")


# ========================================================== 2. RESTRICTIONS
print("\n2) RESTRICTIONS: no charge this turn")

sc = scene()
start_arrival(sc)
charge = ChargeController(turn_tracker=sc["turn"], all_tokens=sc["state"].tokens, dice_manager=DiceManager())
check("not charge-locked before", not sc["arriving"].charge_locked_until_end_of_turn)
sc["blade"].use(sc["arriving"])
check("charge-locked after", sc["arriving"].charge_locked_until_end_of_turn)
put_at(sc, 30.0)
sc["ingress"].confirm_ingress()
check("the arrival confirmed", sc["ingress"].is_ingressing(sc["arriving"]) is False
      and sc["arriving"] not in sc["state"].reserves)
check("ChargeController refuses the charge", not charge.can_declare_charge(sc["arriving"]))


# ====================================================== 3. WHEN / TARGET
print("\n3) WHEN / TARGET clauses")

sc = scene()
check("no arrival open yet -> not usable", not sc["blade"].can_use(sc["arriving"]))
start_arrival(sc)
check("arrival open -> usable", sc["blade"].can_use(sc["arriving"]))

sc["turn"].phase_index = PHASES.index(PHASE_SHOOTING)
check("the Shooting phase does not qualify", not sc["blade"].can_use(sc["arriving"]))
sc["turn"].phase_index = PHASES.index(PHASE_MOVEMENT)

# Rapid Ingress (15.07) arrives during the OPPONENT's Movement phase, which the
# WHEN ("your Movement phase") does not cover.
sc["turn"].active_player = "Player 2"
check("an arrival in the opponent's Movement phase does not qualify",
      not sc["blade"].can_use(sc["arriving"]))
sc["turn"].active_player = "Player 1"

sc["cps"].cp["Player 1"] = 1
check("2 CP required", not sc["blade"].can_use(sc["arriving"]), "1 CP available")
sc["cps"].cp["Player 1"] = 4

check("usable once", sc["blade"].use(sc["arriving"]))
check("not offered twice for the same arrival", not sc["blade"].can_use(sc["arriving"]))

# A non-BATTLESUIT unit, and a unit without [DEEP STRIKE], are both refused -
# the two halves of the TARGET clause this engine can actually check.
sc = scene(arriving_sheet=STRIKE_TEAM)
start_arrival(sc)
check("a non-BATTLESUIT arrival is refused", not sc["blade"].can_use(sc["arriving"]))

sc = scene()
start_arrival(sc)
sc["arriving"].models[0].profile = type(
    "NoDeepStrike", (type(sc["arriving"].models[0].profile),), {"deep_strike": False},
)()
check("one model without [DEEP STRIKE] refuses the whole unit (rule 24.09)",
      not sc["blade"].can_use(sc["arriving"]))


# ============================================== 4. scoped to ONE arrival
print("\n4) the placement rule is scoped to this one arrival")

sc = scene()
start_arrival(sc)
sc["blade"].use(sc["arriving"])
check("armed", sc["ingress"].relaxed_arrival_squad is sc["arriving"])
sc["ingress"].cancel_ingress()
check("cancelling the arrival disarms it", sc["ingress"].relaxed_arrival_squad is None)
check("but the charge lock stays - it is a property of the turn, not the placement",
      sc["arriving"].charge_locked_until_end_of_turn)

sc = scene()
start_arrival(sc)
sc["blade"].use(sc["arriving"])
put_at(sc, 30.0)
sc["ingress"].confirm_ingress()
check("confirming disarms it too", sc["ingress"].relaxed_arrival_squad is None)

# A DIFFERENT unit arriving while the flag names another one keeps the normal 8".
sc = scene()
start_arrival(sc)
other = build_squad(CRISIS_STARSCYTHE, "Player 1", name="1 Other 1")
sc["ingress"].relaxed_arrival_squad = other
token = sc["arriving"].models[0]
near_y = 22.0 + INGRESS_MIN_ENEMY_DISTANCE_IN - 1.0
check("another unit's grant does not relax this arrival",
      not sc["ingress"].position_valid(sc["arriving"], token, 30.0, near_y))


# =================================================================== summary
print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
for name in FAIL:
    print(f"  FAILED: {name}")
sys.exit(1 if FAIL else 0)
