"""Three bugs reported after logs/game_20260816_122550.log.

  1. A Breach and Clear / Sunforge wound re-roll was all-or-nothing: the
     only way to use it was to throw the WHOLE roll, successes included.
     "ich kann mich nicht dazu entscheiden NUR die failed wounds zu
     wiederholen, entweder alles oder nichts. das ist falsch."

  2. A MARKERLIGHT Strike Team marked a Battlewagon, and the Crisis Sunforge
     unit shooting it still gave it the Benefit of Cover. Cause found in the
     log: the Sunforge had marked a Deff Dread in the same phase, so it was
     an Observer unit - and the printed army rule excludes Observer units
     from being Guided at all. The reported behaviour was therefore CORRECT
     ("du hattest recht. observer units profitieren nicht."). What the same
     printed text DID show missing: "excluding Fortification and
     Battle-shocked units" - a Battle-shocked unit must not be able to mark.
     This section pins both down so the report cannot re-open the first.

  3. The Twin Lance's end-of-Fight-phase Retro-thrusters move was skipped
     during the opponent's turn, because the AI ends its turn the instant
     FightController reaches DONE - the same instant the offer opens.

Every section carries an A/B against the pre-fix behaviour, so a passing
check is evidence about the fix and not about the scenario.
"""

from game import fight as fight_module
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions.tau_empire import (
    BREACHER_TEAM, CRISIS_SUNFORGE, STRIKE_TEAM, THE_TWIN_LANCE,
)
from game.factions.orks import BATTLEWAGON
from game.game_state import GameState
from game.greater_good import GreaterGoodController
from game.movement import MovementController
from game.retro_thrusters import RetroThrustersController
from game.objectives import Objective
from game.shooting import NORMAL_SHOOTING, ShootingController
from game.squad import squad_has_markerlight
from game.terrain import Obstacle, TerrainArea
from game.turn import PHASE_FIGHT
from testkit import Checks, Log, build, line_up, pick_option

c = Checks("three reported fixes")
check = c.true


# ================================================================ 1. re-roll
print("\n1. Breach and Clear / Sunforge: 'only the failures' must be offered")


def wound_offer(free_wounds, free_no_effect, wounds=None, crits=0):
    """Drive _offer_twin_linked_choice() with a real ShootingController and
    a real DecisionManager, for a roll whose re-rollable share is
    `free_wounds` successes and `free_no_effect` failures.

    A real Breacher Team against a target standing on a real objective, so
    _wound_reroll_reason() genuinely returns "Breach and Clear" - the
    reported ability - rather than the offer being poked open by hand."""
    target = build(BATTLEWAGON, "Player 2", name="2 Battlewagon 1")
    line_up(target, y=26.0)
    shooter = build(BREACHER_TEAM, "Player 1", name="1 Breacher Team 1")
    line_up(shooter, y=20.0)
    objective = Objective(TerrainArea([Obstacle(target.models[0].x_in, 26.0, 6.0, 6.0)]), "Obj")
    dec = DecisionManager()
    sc = ShootingController(
        all_tokens=list(shooter.models) + list(target.models),
        dice_manager=DiceManager(), decision_manager=dec, player_name="Player 1",
        objectives=[objective],
    )
    sc.shooting_type = NORMAL_SHOOTING
    sc.active_squad = shooter
    weapon = next(w for w in shooter.models[0].weapons if w.weapon_type == "ranged")
    assert sc._wound_reroll_reason(weapon, target) == "Breach and Clear"
    assert sc._wound_reroll_is_full(weapon, target) is True
    total_wounds = free_wounds if wounds is None else wounds
    sc._offer_twin_linked_choice(
        free_no_effect, total_wounds, crits, weapon, target, target.models[0].profile,
        weapon.name, 4, "Player 1", (free_wounds, crits, free_no_effect),
    )
    return dec, sc


# Breach and Clear is a full-re-roll source, which is the branch that used
# to offer no subset.
dec, sc = wound_offer(free_wounds=3, free_no_effect=2)
labels = [o["label"] for o in dec.options]
check("the full re-roll is still offered", any("whole Wound roll" in l for l in labels))
check("the failures-only re-roll is offered too", any("only the 2 failed" in l for l in labels))
check("'Keep result' is still there", any("Keep result" in l for l in labels))
c.eq("exactly three options", len(labels), 3)

check("the subset option appears exactly once, not per failed die",
      len([l for l in labels if "only the" in l]) == 1)

# Picking the failures-only option must throw ONLY the failed dice and keep
# the successes - that is the whole point of the choice.
dec2, sc2 = wound_offer(free_wounds=3, free_no_effect=2, wounds=4, crits=1)
check("the failures-only option is choosable", pick_option(dec2, "only the"))
c.eq("failures-only throws just the failed dice", len(sc2.dice_manager.pending_values or []), 2)
pending = sc2._pending_twin_linked_reroll or {}
c.eq("...and carries every wound already rolled over", pending.get("wounds"), 4)
c.eq("...crits included", pending.get("crits"), 1)
check("...and is not labelled a full re-roll", pending.get("full") is False)

# The full option still discards: it throws every re-rollable die and keeps
# only what was rolled by dice that had already used their one re-roll.
dec3, sc3 = wound_offer(free_wounds=3, free_no_effect=2, wounds=4, crits=1)
check("the full option is choosable", pick_option(dec3, "whole Wound roll"))
c.eq("full re-roll throws successes and failures alike",
     len(sc3.dice_manager.pending_values or []), 5)
c.eq("...carrying over only the already-re-rolled wounds",
     (sc3._pending_twin_linked_reroll or {}).get("wounds"), 1)

# With no re-rollable SUCCESS the two options would roll identical dice -
# offering both would be two buttons for one outcome.
dec4, _ = wound_offer(free_wounds=0, free_no_effect=3)
labels4 = [o["label"] for o in dec4.options]
c.eq("no successful die to lose -> no duplicate option", len(labels4), 2)
check("...and the one re-roll offered covers all 3", any("(3 dice)" in l for l in labels4))

# [TWIN-LINKED] is failures-only by explicit user correction and must be
# untouched by this - it never had a full option to subset.
target_tl = build(BATTLEWAGON, "Player 2", name="2 Battlewagon 1")
line_up(target_tl, y=26.0)
shooter_tl = build(CRISIS_SUNFORGE, "Player 1", name="shooter")
line_up(shooter_tl, y=20.0)
dec_tl = DecisionManager()
sc_tl = ShootingController(
    all_tokens=list(shooter_tl.models) + list(target_tl.models),
    dice_manager=DiceManager(), decision_manager=dec_tl, player_name="Player 1",
)
sc_tl.shooting_type = NORMAL_SHOOTING
sc_tl.active_squad = shooter_tl
w_tl = shooter_tl.models[0].weapons[0]
if not w_tl.twin_linked:
    import copy
    w_tl = copy.copy(w_tl)
    w_tl.twin_linked = True
check("[TWIN-LINKED] is still a failures-only source",
      sc_tl._wound_reroll_is_full(w_tl, target_tl) is False)
sc_tl._offer_twin_linked_choice(
    2, 3, 0, w_tl, target_tl, target_tl.models[0].profile, w_tl.name, 4, "Player 1", (3, 0, 2),
)
c.eq("...so it keeps its two options", len([o["label"] for o in dec_tl.options]), 2)


# ============================================================ 2. Markerlight
print("\n2. An Observer unit is not Guided at all, and Battle Shock blocks marking")


def greater_good_scene():
    state = GameState()
    strike = build(STRIKE_TEAM, "Player 1", name="1 Strike Team 1")
    sunforge = build(CRISIS_SUNFORGE, "Player 1", name="1 Crisis Sunforge Battlesuits 1")
    wagon = build(BATTLEWAGON, "Player 2", name="2 Battlewagon 1")
    dread = build(BATTLEWAGON, "Player 2", name="2 Deff Dread 1")
    line_up(strike, x=10.0, y=20.0)
    line_up(sunforge, x=10.0, y=24.0)
    line_up(wagon, x=10.0, y=30.0)
    line_up(dread, x=40.0, y=30.0)
    for sq in (strike, sunforge, wagon, dread):
        for m in sq.models:
            state.add_token(m)
    gg = GreaterGoodController(all_tokens=state.tokens, game_log=Log())
    return state, gg, strike, sunforge, wagon, dread


def build_non_observer(state, gg):
    """A second T'au unit with For The Greater Good that never spent an
    Observer action - the control case for every "because it is an Observer"
    check below."""
    squad = build(CRISIS_SUNFORGE, "Player 1", name="1 Crisis Sunforge Battlesuits 2")
    line_up(squad, x=30.0, y=24.0)
    for m in squad.models:
        if m not in state.tokens:
            state.add_token(m)
    assert not gg.is_observer(squad)
    return squad


state, gg, strike, sunforge, wagon, dread = greater_good_scene()

check("the scene really is the reported one: Strike Team has MARKERLIGHT",
      squad_has_markerlight(strike))
check("...and the Sunforge does not", not squad_has_markerlight(sunforge))

# Exactly the reported sequence: the Sunforge spends its own Observer action
# on one target, the MARKERLIGHT Strike Team marks another.
gg.spotted_by[dread] = sunforge
gg.observer_squad_ids.add(sunforge)
gg.spotted_by[wagon] = strike
gg.observer_squad_ids.add(strike)

# "Units ... (excluding Observer units) are Guided units" - a standing
# exclusion, so the reported Battlewagon KEEPING its cover was correct. This
# was briefly changed to a per-target exclusion and reverted once the user
# supplied the printed text; the checks below pin the printed reading down so
# the same report cannot re-open it.
check("an Observer unit is not Guided, even against someone else's mark",
      not gg.is_guided_attack(sunforge, wagon))
check("...nor against the target it marked itself",
      not gg.is_guided_attack(sunforge, dread))
check("a unit that never became an Observer IS Guided",
      gg.is_guided_attack(build_non_observer(state, gg), wagon))
check("the MARKERLIGHT source is still recognised on the Battlewagon",
      gg.marked_by_markerlight(wagon))
check("...and not on the target the non-MARKERLIGHT Sunforge marked",
      not gg.marked_by_markerlight(dread))

# End to end through the real cover predicate - the line the report was read
# off ("+1 (Benefit of Cover)" on the Fusion Blaster).
sc = ShootingController(
    all_tokens=state.tokens, dice_manager=DiceManager(), decision_manager=DecisionManager(),
    greater_good=gg, player_name="Player 1",
)
sc.shooting_type = NORMAL_SHOOTING
sc.active_squad = sunforge
weapon = next(w for w in sunforge.models[0].weapons if w.weapon_type == "ranged")
check("an Observer shooter does NOT strip the Battlewagon's cover",
      not sc._cover_ignored_for_group(weapon, wagon))

# A/B: the same board, shot by a unit that did not spend an Observer action,
# does strip it - so the check above is about Observer status and not about
# the scene lacking a MARKERLIGHT mark.
sc.active_squad = build_non_observer(state, gg)
check("A/B: a non-Observer shooter DOES strip it",
      sc._cover_ignored_for_group(weapon, wagon))

# A unit with no Greater Good at all is unaffected either way.
plain = build(BATTLEWAGON, "Player 1", name="1 Not Tau")
line_up(plain, x=10.0, y=22.0)
check("a unit without For The Greater Good is never Guided",
      not gg.is_guided_attack(plain, wagon))

# "...is eligible to shoot (excluding Fortification and Battle-shocked
# units)": a Battle-shocked unit cannot become an Observer at all.
state2, gg2, strike2, sunforge2, wagon2, dread2 = greater_good_scene()
gg2.turn_tracker = None


class _NoShots:
    shot_squad_ids = ()


check("A/B: the unit can mark while it is steady", gg2.can_use(strike2, _NoShots()))
strike2.battle_shocked = True
check("a Battle-shocked unit cannot become an Observer (01.07 / army rule)",
      not gg2.can_use(strike2, _NoShots()))
strike2.battle_shocked = False
check("...and can again once the Battle Shock is gone", gg2.can_use(strike2, _NoShots()))


# ========================================================= 3. Retro-thrusters
print("\n3. The opponent's turn must wait for a pending Retro-thrusters move")


def retro_scene():
    state = GameState()
    lance = build(THE_TWIN_LANCE, "Player 1", name="1 The Twin Lance 1")
    orks = build(BATTLEWAGON, "Player 2", name="2 Battlewagon 1")
    # 3" spacing: the Twin Lance is on a 60mm base (1.18" radius), so
    # line_up()'s 1.4" default would overlap the two models and every
    # confirm_move() would be rejected as an illegal position.
    line_up(lance, x=20.0, y=20.0, spacing=3.0)
    line_up(orks, x=20.0, y=40.0, spacing=3.0)
    for sq in (lance, orks):
        for m in sq.models:
            state.add_token(m)
    log = Log()
    mc = MovementController(all_tokens=state.tokens, game_log=log)
    rt = RetroThrustersController(
        movement_controller=mc, all_tokens=state.tokens, game_log=log,
    )
    return state, rt, lance, orks, log, mc


state, rt, lance, orks, log, mc = retro_scene()
check("nothing is pending before anything was eligible", not rt.pending_squads())

rt._eligible_this_phase.add(id(lance))  # what note_eligibility() latches
check("an eligible unit is pending", lance in rt.pending_squads())
check("...and shows up as the OPPONENT's pending offer for Player 2",
      rt.has_pending_for_opponent_of("Player 2"))
check("...but not as Player 1's own", not rt.has_pending_for_opponent_of("Player 1"))

rt.announce_wait_once("Player 2")
check("the wait is announced so the game does not just look stalled",
      log.has("can still use Retro-thrusters"))
before = len(log.lines)
rt.announce_wait_once("Player 2")
c.eq("...exactly once per Fight phase", len(log.lines), before)

# Skip is what makes the wait terminate, and it has to be reachable.
rt.decline(lance)
check("declining clears the pending offer", not rt.pending_squads())
check("...so the turn is free to end", not rt.has_pending_for_opponent_of("Player 2"))

# Taking the move clears it too, and the offer stays open while the move is
# still on the table (otherwise the turn could end mid-move).
state, rt, lance, orks, log, mc = retro_scene()
rt._eligible_this_phase.add(id(lance))
mc.turn_tracker = None
check("both halves are offered to an unengaged unit",
      rt.available_moves(lance) == ["normal", "fall_back"])
check("the move opens", rt.start(lance, fall_back=False))
check("...and the offer counts as still pending while it is open",
      rt.has_pending_for_opponent_of("Player 2"))
rt.confirm()
check("...and is gone once confirmed", not rt.has_pending_for_opponent_of("Player 2"))

# A new Fight phase re-arms everything, announcement included.
rt.reset_fight_phase()
check("a fresh Fight phase has nothing pending", not rt.pending_squads())

# The AI's own turn-end gate, driven through the real helper it calls.
state, rt, lance, orks, log, mc = retro_scene()
rt._eligible_this_phase.add(id(lance))
advanced = []


def fake_advance():
    advanced.append(True)


class _Tracker:
    turn_owner = "Player 2"
    phase = PHASE_FIGHT


class _Fight:
    state = fight_module.DONE


# Mirrors take_one_action()'s PHASE_FIGHT branch verbatim.
def turn_end_gate(rt_ctrl):
    if _Fight.state == fight_module.DONE and _Tracker.turn_owner == "Player 2":
        if rt_ctrl is not None and rt_ctrl.has_pending_for_opponent_of("Player 2"):
            rt_ctrl.announce_wait_once("Player 2")
            return
        fake_advance()


turn_end_gate(rt)
c.eq("the AI holds its turn open while the offer stands", len(advanced), 0)
rt.decline(lance)
turn_end_gate(rt)
c.eq("...and ends it as soon as the offer is answered", len(advanced), 1)

# A/B: without the gate the turn ended on the very same state - the bug.
advanced.clear()
turn_end_gate(None)
c.eq("A/B: pre-fix the turn ended regardless", len(advanced), 1)


# --- the Skip button has to actually exist and be clickable --------------
print("\n3b. Skip is a real button, inside the panel")

import os  # noqa: E402

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

from game import config  # noqa: E402
from game.ui.action_panel import ActionPanel  # noqa: E402

pygame.init()
pygame.display.set_mode((320, 240))

state, rt, lance, orks, log, mc = retro_scene()
rt._eligible_this_phase.add(id(lance))
mc.select(lance.models[0])
panel = ActionPanel()
surface = pygame.Surface((config.LEFT_PANEL_WIDTH, 900))
panel_rect = pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH, 900)


def panel_shooting(tokens):
    """The panel dereferences shooting_controller unconditionally, so it
    needs a real one even for a screen that has nothing to do with shooting."""
    return ShootingController(
        all_tokens=tokens, dice_manager=DiceManager(),
        decision_manager=DecisionManager(), player_name="Player 1",
    )


buttons_sc = panel_shooting(state.tokens)
panel.draw(surface, panel_rect, mc, buttons_sc, retro_thrusters_controller=rt)
buttons = list(panel._buttons)
check("something was drawn for the selected unit", bool(buttons))
check("every button stays inside the panel",
      all(panel_rect.contains(r) for r, _ in buttons))
# The panel keeps only (rect, callback), so identify the buttons by clicking
# each one in a throwaway copy of the scene and classifying what it did -
# a stronger check than reading a label would have been anyway.
outcomes = []
for index in range(len(buttons)):
    probe_state, probe_rt, probe_lance, _orks, _log, probe_mc = retro_scene()
    probe_rt._eligible_this_phase.add(id(probe_lance))
    probe_mc.select(probe_lance.models[0])
    panel.draw(surface, panel_rect, probe_mc, panel_shooting(probe_state.tokens),
               retro_thrusters_controller=probe_rt)
    if index >= len(panel._buttons):
        continue
    panel._buttons[index][1]()
    if probe_rt.active_squad is probe_lance:
        outcomes.append("move:" + (probe_mc.move_mode or "?"))
    elif not probe_rt.pending_squads():
        outcomes.append("skip")

c.eq('the 6" Normal move is on the panel', outcomes.count("move:retro_thrusters"), 1)
c.eq("the Fall Back move is on the panel",
     outcomes.count("move:retro_thrusters_fall_back"), 1)
c.eq("and so is Skip, which is what lets the held turn end", outcomes.count("skip"), 1)

c.finish()
