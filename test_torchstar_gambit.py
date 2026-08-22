"""Tests for Retaliation Cadre's The Torchstar Gambit stratagem
(game/torchstar_gambit.py).

RULE (user-supplied): 1CP, Strategic Ploy. WHEN your Shooting phase. TARGET one
T'AU EMPIRE BATTLESUIT unit from your army that can FLY whose attacks have been
resolved this phase. EFFECT if the unit is not within Engagement Range of one
or more enemy units, it can make a Normal move. If it does, the unit cannot
declare a charge this turn.

Two things carry the risk here, and they are what the checks concentrate on:

  * a Normal move OUTSIDE the Movement phase - it must actually move (the
    normal gates would refuse it), keep a Normal move's distance and end
    condition, and NOT be recorded as the unit's Movement-phase move;
  * "if it DOES" - the no-charge restriction must land on Confirm and must
    NOT land on Cancel or on a rejected Confirm.

Uses real MovementController/ShootingController/ChargeController/
StratagemController/CommandPointManager/GameState objects and real datasheets.

Run: python test_torchstar_gambit.py
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
from game.factions.tau_empire import CRISIS_STARSCYTHE, GHOSTKEEL_BATTLESUIT, STRIKE_TEAM
from game.game_state import GameState
from game.movement import MOVING, MovementController
from game.shooting import ShootingController
from game.stratagems import StratagemController
from game.torchstar_gambit import TORCHSTAR_CP_COST, TorchstarGambitController, can_fly
from game.turn import PHASES, PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker

m = maps.get("map2")
maps.apply_to_config(m)

PASS, FAIL = [], []


def check(name, condition, detail=""):
    (PASS if condition else FAIL).append(name)
    print(f"  {'OK  ' if condition else 'FAIL'} {name}{(' - ' + detail) if detail else ''}")


def scene(sheet=CRISIS_STARSCYTHE, cp=3, phase=PHASE_SHOOTING, active="Player 1",
          enemy_y=40.0, has_shot=True):
    """One T'au unit at y=20 and an enemy row far away at enemy_y, on empty
    ground - so the only thing that can reject a move is the rule under test.
    `enemy_y` is the one knob: bring it down to 21 and the unit is engaged."""
    st = GameState()
    squad = build_squad(sheet, "Player 1", name="1 Suits 1")
    enemy = build_squad(GRETCHIN, "Player 2", name="2 Enemy 1")
    for i, mdl in enumerate(squad.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 2.4, 20.0
        st.add_token(mdl)
    for i, mdl in enumerate(enemy.models):
        mdl.x_in, mdl.y_in = 20.0 + i * 1.4, enemy_y
        st.add_token(mdl)

    tt = TurnTracker()
    tt.started = True
    tt.battle_round = 2
    tt.phase_index = PHASES.index(phase)
    tt.turn_owner = tt.active_player = active

    cps = CommandPointManager()
    cps.cp["Player 1"] = cp
    strat = StratagemController(command_points=cps)
    mc = MovementController(all_tokens=st.tokens, obstacles=st.obstacles, turn_tracker=tt,
                            board_width_in=m.width_in, board_height_in=m.height_in)
    sc = ShootingController(obstacles=st.obstacles, dice_manager=DiceManager(), turn_tracker=tt,
                            all_tokens=st.tokens, movement_controller=mc)
    if has_shot:
        # "whose attacks have been resolved this phase" - exactly what
        # _actually_finish_squad() records at the end of an activation.
        sc.shot_squad_ids.add(squad)
    tc = TorchstarGambitController(strat, movement_controller=mc, shooting_controller=sc,
                                   all_tokens=st.tokens, turn_tracker=tt)
    mc.selected_squad = squad
    return dict(state=st, squad=squad, enemy=enemy, turn=tt, cps=cps, strat=strat,
                movement=mc, shooting=sc, torchstar=tc)


def drag(sc, dy, models=None):
    """Move models dy inches through the same commit path a human drag uses,
    so the distance clamp and the per-segment legality checks really apply.
    Returns the per-model (accepted, errors) results."""
    out = []
    for mdl in (sc["squad"].models if models is None else models):
        mdl.y_in += dy
        out.append(sc["movement"].try_commit_segment(mdl))
    return out


# ============================================ 1. a Normal move, in Shooting
print("\n1) it really makes a Normal move, in the Shooting phase")

sc = scene()
check("offered to a unit that has shot", sc["torchstar"].can_use(sc["squad"]))
check("the normal Movement-phase gate would refuse it here",
      not sc["movement"].can_make_move(sc["squad"]), "wrong phase")

start_y = sc["squad"].models[0].y_in
check("using it costs exactly 1 CP and opens a move",
      sc["torchstar"].use(sc["squad"]) and sc["cps"].cp["Player 1"] == 3 - TORCHSTAR_CP_COST,
      str(sc["cps"].cp["Player 1"]))
check("the move is open in torchstar mode",
      sc["movement"].state == MOVING and sc["movement"].move_mode == "torchstar")

budget = sc["movement"].remaining_range[sc["squad"].models[0].id]
printed = sc["squad"].models[0].profile.movement_in
check("the distance is the unit's own M characteristic", abs(budget - printed) < 1e-6,
      f"{budget}\" vs printed {printed}\"")

drag(sc, 4.0)
check("Confirm succeeds", sc["torchstar"].confirm_move())
check("and the unit actually moved", abs(sc["squad"].models[0].y_in - (start_y + 4.0)) < 1e-6,
      f"{start_y} -> {sc['squad'].models[0].y_in}")

# It is not the unit's Movement-phase move, and must not be recorded as one.
check("it is NOT recorded as the Movement-phase move (rule 09.02)",
      sc["squad"] not in sc["movement"].moved_squad_ids)
check("nor as an Advance", sc["squad"] not in sc["movement"].advanced_squad_ids)

# A Normal move's end condition still applies. It bites at the SEGMENT, not at
# Confirm: rule 09.05/09.06's "must end unengaged" is per-model attributable, so
# try_commit_segment() refuses it the instant the model is placed and snaps it
# back (Squad.disallowed_enemy_squads_for_move() returns every enemy squad for
# any move mode it does not name, and it does not name "torchstar").
sc = scene(enemy_y=32.0)
sc["torchstar"].use(sc["squad"])
results = drag(sc, 9.0)  # would end ~1.4" edge-to-edge from the enemy row
check("dragging into Engagement Range is refused per segment",
      all(not accepted for accepted, _ in results),
      "; ".join(e for _, errs in results for e in errs)[:110])
check("the models snapped back", all(abs(mm.y_in - 20.0) < 1e-6 for mm in sc["squad"].models))
check("so Confirm succeeds, with the unit unengaged",
      sc["torchstar"].confirm_move() and not sc["squad"].is_engaged(sc["state"].tokens))


# ==================================================== 2. "if it does"
print("\n2) RESTRICTIONS attach to the MOVE, not to spending the CP")

sc = scene()
charge = ChargeController(turn_tracker=sc["turn"], all_tokens=sc["state"].tokens, dice_manager=DiceManager())
sc["torchstar"].use(sc["squad"])
check("not charge-locked merely by using it", not sc["squad"].charge_locked_until_end_of_turn)
drag(sc, 3.0)
sc["torchstar"].confirm_move()
check("charge-locked once the move is confirmed", sc["squad"].charge_locked_until_end_of_turn)
check("ChargeController refuses the charge", not charge.can_declare_charge(sc["squad"]))

sc = scene()
sc["torchstar"].use(sc["squad"])
start = [(mm.x_in, mm.y_in) for mm in sc["squad"].models]
drag(sc, 3.0)
check("Cancel puts the models back", sc["torchstar"].cancel_move()
      and all(abs(mm.y_in - y) < 1e-6 for mm, (_, y) in zip(sc["squad"].models, start)))
check("and leaves NO charge lock - the move was not made",
      not sc["squad"].charge_locked_until_end_of_turn)

# Coherency (rule 09.02) is the squad-wide check that can only fail at Confirm -
# drag one model away from the rest and the whole move is refused.
sc = scene()
sc["torchstar"].use(sc["squad"])
drag(sc, 9.0, models=[sc["squad"].models[0]])
check("a coherency-breaking move is rejected at Confirm", not sc["torchstar"].confirm_move())
check("the move stays open to be fixed", sc["movement"].move_mode == "torchstar")
check("with a stated reason", bool(sc["movement"].errors), "; ".join(sc["movement"].errors)[:110])
check("a REJECTED confirm leaves no charge lock either",
      not sc["squad"].charge_locked_until_end_of_turn)


# ================================================== 3. WHEN / TARGET clauses
print("\n3) WHEN / TARGET clauses")

sc = scene(has_shot=False)
check("a unit that has not shot is refused", not sc["torchstar"].can_use(sc["squad"]))
sc["shooting"].shot_squad_ids.add(sc["squad"])
check("and accepted once its attacks are resolved", sc["torchstar"].can_use(sc["squad"]))

sc["turn"].phase_index = PHASES.index(PHASE_MOVEMENT)
check("the Movement phase does not qualify", not sc["torchstar"].can_use(sc["squad"]))
sc["turn"].phase_index = PHASES.index(PHASE_SHOOTING)
sc["turn"].active_player = "Player 2"
check("the opponent's Shooting phase does not qualify", not sc["torchstar"].can_use(sc["squad"]))
sc["turn"].active_player = "Player 1"

sc["cps"].cp["Player 1"] = 0
check("no CP, no offer", not sc["torchstar"].can_use(sc["squad"]))
sc["cps"].cp["Player 1"] = 3

sc["squad"].battle_shocked = True
check("a battle-shocked unit is blocked (rule 01.07)", not sc["torchstar"].can_use(sc["squad"]))
sc["squad"].battle_shocked = False

# EFFECT: "if your unit is not within Engagement Range of one or more enemy
# units" - an engaged unit gets nothing, so it is never offered.
sc = scene(enemy_y=21.0)
check("an engaged unit is refused", sc["squad"].is_engaged(sc["state"].tokens)
      and not sc["torchstar"].can_use(sc["squad"]))

# The two keyword halves this engine can check.
sc = scene(sheet=STRIKE_TEAM)
check("a non-BATTLESUIT unit is refused", not sc["torchstar"].can_use(sc["squad"]))
check("Crisis Battlesuits can FLY", can_fly(build_squad(CRISIS_STARSCYTHE, "Player 1", name="x")))

sc = scene(sheet=GHOSTKEEL_BATTLESUIT)
grounded = not can_fly(sc["squad"])
check("a BATTLESUIT that cannot FLY is refused" if grounded
      else "the Ghostkeel can FLY, so it qualifies",
      (not sc["torchstar"].can_use(sc["squad"])) if grounded else sc["torchstar"].can_use(sc["squad"]),
      f"fly={not grounded}")

# Rule 15.01: once per phase.
sc = scene()
other = build_squad(CRISIS_STARSCYTHE, "Player 1", name="1 Suits 2")
for i, mdl in enumerate(other.models):
    mdl.x_in, mdl.y_in = 40.0 + i * 2.4, 20.0
    sc["state"].add_token(mdl)
sc["shooting"].shot_squad_ids.add(other)
check("first use succeeds", sc["torchstar"].use(sc["squad"]))
sc["torchstar"].cancel_move()
check("a second unit cannot use it the same phase (rule 15.01)", not sc["torchstar"].can_use(other))
sc["strat"].reset_phase()
check("but can once the phase turns over", sc["torchstar"].can_use(other))

# Take to the Skies (21.03) is deliberately not offered during this move -
# asserted so the decision is visible rather than incidental.
sc = scene()
sc["torchstar"].use(sc["squad"])
check("Take to the Skies is not offered during a Torchstar move (documented choice)",
      not sc["movement"].can_take_to_the_skies())


# =================================================================== summary
print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
for name in FAIL:
    print(f"  FAILED: {name}")
sys.exit(1 if FAIL else 0)
