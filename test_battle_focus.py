"""Aeldari army rule Battle Focus: the token account and the three Agile
Manoeuvres wired in the first step (Swift as the Wind, Flitting Shadows, Star
Engines).

No Aeldari datasheet exists yet - the user asked for the army rule first - so
the ability is granted to real T'au datasheets by copying each model's profile,
the same way test_fail_safe_detonator.py grants Deadly Demise to one model.
copy.copy() per model rather than assigning the flag: UnitProfile carries it as
a CLASS attribute, so setting it in place would silently switch it on for every
other unit built from the same datasheet, in this suite and in any other.

Every effect is asserted through the function the ENGINE actually reads -
coldstar.effective_movement_in(), coldstar.weapon_has_assault(),
ShootingController._is_valid_target_squad() - never through the flag the
manoeuvre sets. A flag that is set but read nowhere is exactly the failure this
suite exists to catch.
"""

import copy
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from game import battle_focus, coldstar
from game.factions.tau_empire import (
    COMMANDER_IN_COLDSTAR_BATTLESUIT, CRISIS_STARSCYTHE, DEVILFISH, STRIKE_TEAM,
)
from game.movement import MovementController
from game.shooting import SNAP_SHOOTING, NORMAL_SHOOTING
from game.turn import PHASE_MOVEMENT, PHASES
from testkit import Checks, DiceManager, GameState, Log, TurnTracker, build, line_up, shooting_scene

checks = Checks("Battle Focus")


def _read_source(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def aeldari(squad):
    """Give every model in this unit the Battle Focus ability."""
    for model in squad.models:
        model.profile = copy.copy(model.profile)
        model.profile.battle_focus = True
    return squad


def movement_tracker(owner="Player 1"):
    tracker = TurnTracker(first_player=owner)
    tracker.phase_index = PHASES.index(PHASE_MOVEMENT)
    tracker.turn_owner = owner
    tracker.set_active(owner)
    return tracker


def pool(players=("Player 1",), **kwargs):
    return battle_focus.BattleFocusPool(players=players, game_log=Log(), **kwargs)


# ------------------------------------------------------ 1. the token account

print("--- 1. token account ---")

for size, want in (("incursion", 2), ("strike_force", 4), ("onslaught", 6),
                   ("Strike Force", 4), ("nonsense", 4)):
    checks.eq(f"battle size {size!r} grants", battle_focus.tokens_for_battle_size(size), want)

p = pool(battle_size="strike_force")
p.sync_battle_round(1)
checks.eq("round 1 grants 4", p.tokens["Player 1"], 4)
p.sync_battle_round(1)
checks.eq("same round again is a no-op", p.tokens["Player 1"], 4)

squad = aeldari(build(STRIKE_TEAM, "Player 1", name="Guardians"))
p._spend("Player 1", battle_focus.SWIFT_AS_THE_WIND, squad)
checks.eq("spending one leaves 3", p.tokens["Player 1"], 3)
p.sync_battle_round(2)
checks.eq("a new round refills to 4 (unspent are lost, not carried)", p.tokens["Player 1"], 4)
checks.true("the loss is logged", p.game_log.has("unspent Battle Focus token"))

p2 = pool(battle_size="incursion")
p2.sync_battle_round(1)
checks.eq("incursion grants 2", p2.tokens["Player 1"], 2)

nobody = pool(players=())
nobody.sync_battle_round(1)
checks.eq("no ASURYANI army: nothing is granted", dict(nobody.tokens), {})
checks.eq("and nothing can be spent", nobody.can_use("Player 1", battle_focus.SWIFT_AS_THE_WIND, squad), False)


# --------------------------------------------- 2. whose army counts as ASURYANI

print("--- 2. qualifying players ---")

aeldari_squad = aeldari(build(STRIKE_TEAM, "Player 1", name="A"))
plain_squad = build(STRIKE_TEAM, "Player 2", name="B")
checks.eq("derived from the ability", battle_focus.qualifying_players([aeldari_squad, plain_squad]),
          ("Player 1",))
checks.eq("an army without it does not qualify", battle_focus.qualifying_players([plain_squad]), ())
checks.true("has_battle_focus is true for the granted unit", battle_focus.has_battle_focus(aeldari_squad))
checks.eq("and false for a plain one", battle_focus.has_battle_focus(plain_squad), False)
wiped = aeldari(build(STRIKE_TEAM, "Player 1", name="Wiped"))
wiped.models = []
checks.eq("a wiped-out unit does not qualify", battle_focus.has_battle_focus(wiped), False)

# Lazy derivation through the provider: the pre-game sequence means the army is
# empty when the pool is built, so an empty first look must not be final.
army = []
lazy = battle_focus.BattleFocusPool(game_log=Log(), squads_provider=lambda: list(army))
lazy.sync_battle_round(1)
checks.eq("empty army: no players yet", lazy.players, ())
army.append(aeldari_squad)
lazy.sync_battle_round(1)
checks.eq("once the army exists, the players are derived", lazy.players, ("Player 1",))
checks.eq("and the round-1 tokens land", lazy.tokens["Player 1"], 4)


# ------------------------------------------- 3. the two restriction axes

print("--- 3. restrictions ---")

p = pool()
p.sync_battle_round(1)
unit_a = aeldari(build(STRIKE_TEAM, "Player 1", name="A"))
unit_b = aeldari(build(STRIKE_TEAM, "Player 1", name="B"))

checks.true("A may use Swift as the Wind", p.can_use("Player 1", battle_focus.SWIFT_AS_THE_WIND, unit_a))
p._spend("Player 1", battle_focus.SWIFT_AS_THE_WIND, unit_a)
checks.eq("per-UNIT axis: A is out of ALL manoeuvres this phase",
          p.can_use("Player 1", battle_focus.FLITTING_SHADOWS, unit_a), False)
checks.true("Swift as the Wind repeats for a DIFFERENT unit",
            p.can_use("Player 1", battle_focus.SWIFT_AS_THE_WIND, unit_b))

p._spend("Player 1", battle_focus.FLITTING_SHADOWS, unit_b)
unit_c = aeldari(build(STRIKE_TEAM, "Player 1", name="C"))
checks.eq("per-MANOEUVRE axis: Flitting Shadows cannot repeat this phase",
          p.can_use("Player 1", battle_focus.FLITTING_SHADOWS, unit_c), False)
checks.true("but Star Engines is still untouched",
            p.can_use("Player 1", battle_focus.STAR_ENGINES, unit_c))

checks.eq("tokens spent so far", p.tokens["Player 1"], 2)
p.reset_phase([unit_a, unit_b, unit_c])
checks.true("a new phase frees the unit again", p.can_use("Player 1", battle_focus.FLITTING_SHADOWS, unit_a))
checks.eq("but not the tokens", p.tokens["Player 1"], 2)

broke = pool()
broke.sync_battle_round(1)
broke.tokens["Player 1"] = 0
checks.eq("no tokens, no manoeuvre", broke.can_use("Player 1", battle_focus.SWIFT_AS_THE_WIND, unit_a), False)
checks.true("and the refusal says why",
            "token" in broke.refusal_reason("Player 1", battle_focus.SWIFT_AS_THE_WIND, unit_a))
checks.eq("a unit without the ability is never eligible",
          pool().can_use("Player 1", battle_focus.SWIFT_AS_THE_WIND, plain_squad), False)


# ------------------------------------------------ 4. Swift as the Wind

print("--- 4. Swift as the Wind ---")

state = GameState()
tracker = movement_tracker()
mover = MovementController(turn_tracker=tracker, all_tokens=state.tokens, player_name="Player 1")
runner = aeldari(build(STRIKE_TEAM, "Player 1", name="Runners"))
line_up(runner, x=10.0, y=10.0)
for model in runner.models:
    state.add_token(model)

printed = runner.models[0].profile.movement_in
checks.eq("before: the engine reports the printed Move",
          coldstar.effective_movement_in(runner.models[0]), printed)

p = pool(movement_controller=mover, turn_tracker=tracker)
p.sync_battle_round(1)
checks.true("the trigger is available in the owner's Movement phase", p.can_swift_as_the_wind(runner))
checks.true("using it succeeds", p.use_swift_as_the_wind(runner))
checks.eq("after: +2\" through the function the engine reads",
          coldstar.effective_movement_in(runner.models[0]), printed + 2.0)
checks.eq("every model, not just the first",
          all(coldstar.effective_movement_in(m) == printed + 2.0 for m in runner.models), True)

mover.select(runner.models[0])
mover.start_move()
checks.eq("the move budget is the boosted characteristic",
          round(mover.remaining_range[runner.models[0].id], 3), round(printed + 2.0, 3))

# Top-up: the same manoeuvre bought while the unit is already moving.
state2 = GameState()
tracker2 = movement_tracker()
mover2 = MovementController(turn_tracker=tracker2, all_tokens=state2.tokens, player_name="Player 1")
mid = aeldari(build(STRIKE_TEAM, "Player 1", name="MidMove"))
line_up(mid, x=10.0, y=10.0)
for model in mid.models:
    state2.add_token(model)
mover2.select(mid.models[0])
mover2.start_move()
before_budget = mover2.remaining_range[mid.models[0].id]
p2 = pool(movement_controller=mover2, turn_tracker=tracker2)
p2.sync_battle_round(1)
checks.true("still offered once the move has begun", p2.can_swift_as_the_wind(mid))
p2.use_swift_as_the_wind(mid)
checks.eq("the running move is topped up by 2\"",
          round(mover2.remaining_range[mid.models[0].id] - before_budget, 3), 2.0)

# Lifetime: phase, not turn.
p.reset_phase([runner])
checks.eq("the bonus is gone next phase", coldstar.effective_movement_in(runner.models[0]), printed)

# Stacks on top of the Coldstar Commander's flat override (19.01 attached unit).
from game import attached_units
crisis = aeldari(build(CRISIS_STARSCYTHE, "Player 1", name="Crisis"))
coldstar_cmd = aeldari(build(COMMANDER_IN_COLDSTAR_BATTLESUIT, "Player 1", name="Coldstar"))
attached_units.attach(coldstar_cmd, crisis)
checks.eq("Coldstar's flat override alone", coldstar.effective_movement_in(crisis.models[0]),
          coldstar.COLDSTAR_MOVEMENT_IN)
crisis.swift_as_the_wind_active = True
checks.eq("Swift as the Wind ADDS to the override, it does not replace it",
          coldstar.effective_movement_in(crisis.models[0]), coldstar.COLDSTAR_MOVEMENT_IN + 2.0)
crisis.swift_as_the_wind_active = False

# A unit that has finished its move is past the trigger.
p3 = pool(movement_controller=mover, turn_tracker=tracker)
p3.sync_battle_round(1)
mover.moved_squad_ids.add(runner)
checks.eq("a unit that already moved is past the trigger", p3.can_swift_as_the_wind(runner), False)
mover.moved_squad_ids.discard(runner)

# Wrong phase / wrong player.
tracker.phase_index = PHASES.index("Shooting")
checks.eq("not in the Shooting phase", p3.can_swift_as_the_wind(runner), False)
tracker.phase_index = PHASES.index(PHASE_MOVEMENT)
tracker.turn_owner = "Player 2"
checks.eq("not in the opponent's turn", p3.can_swift_as_the_wind(runner), False)
tracker.turn_owner = "Player 1"


# ---------------------------------------------------- 5. Star Engines

print("--- 5. Star Engines ---")

state3 = GameState()
tracker3 = movement_tracker()
dice = DiceManager()
mover3 = MovementController(turn_tracker=tracker3, all_tokens=state3.tokens,
                            player_name="Player 1", dice_manager=dice)
tank = aeldari(build(DEVILFISH, "Player 1", name="Falcon"))
line_up(tank, x=20.0, y=20.0, spacing=3.0)
for model in tank.models:
    state3.add_token(model)

ranged = [w for w in tank.models[0].weapons if w.weapon_type == "ranged"]
melee = [w for w in tank.models[0].weapons if w.weapon_type == "melee"]
checks.true("the test vehicle has a ranged weapon", bool(ranged))
checks.eq("before: no [ASSAULT]", coldstar.weapon_has_assault(ranged[0], tank), ranged[0].assault)

p4 = pool(movement_controller=mover3, turn_tracker=tracker3)
p4.sync_battle_round(1)
checks.eq("not offered before the unit has Advanced", p4.can_star_engines(tank), False)

mover3.select(tank.models[0])
mover3.start_move()
mover3.start_run()
checks.true("the unit really Advanced", tank in mover3.advance_bonus_by_squad)
checks.true("now it is offered", p4.can_star_engines(tank))
checks.true("using it succeeds", p4.use_star_engines(tank))
checks.true("after: [ASSAULT] through the function the engine reads",
            coldstar.weapon_has_assault(ranged[0], tank))
if melee:
    checks.eq("melee weapons are untouched (the rule says Ranged)",
              coldstar.weapon_has_assault(melee[0], tank), melee[0].assault)

infantry = aeldari(build(STRIKE_TEAM, "Player 1", name="Foot"))
p5 = pool(movement_controller=mover3, turn_tracker=tracker3)
p5.sync_battle_round(1)
mover3.advance_bonus_by_squad[infantry] = 3  # pretend it Advanced too
checks.eq("a non-VEHICLE unit is never eligible", p5.can_star_engines(infantry), False)

p4.expire_for_turn([tank])
checks.eq("the grant ends with the turn", coldstar.weapon_has_assault(ranged[0], tank), ranged[0].assault)
p4.reset_phase([tank])
tank.star_engines_active = True
checks.true("a phase change does NOT end it (it is until end of turn)",
            coldstar.weapon_has_assault(ranged[0], tank))
tank.star_engines_active = False


# -------------------------------------------------- 6. Flitting Shadows

print("--- 6. Flitting Shadows ---")

scene = shooting_scene(STRIKE_TEAM, STRIKE_TEAM, attacker_owner="Player 2", gap=6.0)
shooter, hider, sc = scene["attacker"], scene["target"], scene["shooting"]
aeldari(hider)

checks.true("baseline: the Overwatcher can snap-shoot this unit",
            sc._is_valid_target_squad(hider, scene["state"].tokens,
                                      attacking_squad=shooter, shooting_type=SNAP_SHOOTING))
checks.true("baseline: it also has a valid Snap Shooting target at all",
            sc.has_valid_target(shooter, SNAP_SHOOTING, scene["state"].tokens))

hider.flitting_shadows_active = True
checks.eq("protected: not a legal Snap Shooting target",
          sc._is_valid_target_squad(hider, scene["state"].tokens,
                                    attacking_squad=shooter, shooting_type=SNAP_SHOOTING), False)
checks.eq("so the would-be Overwatcher has nothing to shoot and stops being eligible",
          sc.has_valid_target(shooter, SNAP_SHOOTING, scene["state"].tokens), False)
checks.true("ordinary shooting is unaffected - it says Fire Overwatch",
            sc._is_valid_target_squad(hider, scene["state"].tokens,
                                      attacking_squad=shooter, shooting_type=NORMAL_SHOOTING))

# Through the pool, in the phase it is triggered in.
tracker4 = movement_tracker()
p6 = pool(turn_tracker=tracker4)
p6.sync_battle_round(1)
hider.flitting_shadows_active = False
hider.owner = "Player 1"
checks.true("offered in the owner's Movement phase", p6.can_flitting_shadows(hider))
checks.true("using it succeeds", p6.use_flitting_shadows(hider))
checks.true("and the protection is live", battle_focus.blocks_fire_overwatch(hider))
p6.expire_for_turn([hider])
checks.eq("gone at the end of the turn", battle_focus.blocks_fire_overwatch(hider), False)


# ------------------------------------------------------- 7. A/B probes

print("--- 7. A/B probes ---")

# Each probe unwires ONE effect and confirms the corresponding check above was
# actually load-bearing - a green suite with the effect neutralised would only
# prove the scenes never reach it.
saved_bonus = battle_focus.movement_bonus_in
battle_focus.movement_bonus_in = lambda model: 0.0
runner.swift_as_the_wind_active = True
checks.eq("A/B: with movement_bonus_in() neutralised the +2 disappears",
          coldstar.effective_movement_in(runner.models[0]), printed)
battle_focus.movement_bonus_in = saved_bonus
checks.eq("A/B: and comes back when it is restored",
          coldstar.effective_movement_in(runner.models[0]), printed + 2.0)
runner.swift_as_the_wind_active = False

saved_assault = battle_focus.grants_assault
battle_focus.grants_assault = lambda squad: False
tank.star_engines_active = True
checks.eq("A/B: with grants_assault() neutralised [ASSAULT] disappears",
          coldstar.weapon_has_assault(ranged[0], tank), ranged[0].assault)
battle_focus.grants_assault = saved_assault
checks.true("A/B: and comes back when it is restored",
            coldstar.weapon_has_assault(ranged[0], tank))
tank.star_engines_active = False

saved_block = battle_focus.blocks_fire_overwatch
battle_focus.blocks_fire_overwatch = lambda squad: False
hider.flitting_shadows_active = True
checks.true("A/B: with blocks_fire_overwatch() neutralised the unit is targetable again",
            sc._is_valid_target_squad(hider, scene["state"].tokens,
                                      attacking_squad=shooter, shooting_type=SNAP_SHOOTING))
battle_focus.blocks_fire_overwatch = saved_block
checks.eq("A/B: and is protected again when it is restored",
          sc._is_valid_target_squad(hider, scene["state"].tokens,
                                    attacking_squad=shooter, shooting_type=SNAP_SHOOTING), False)


# ------------------------------------------------- 8. the panels, rendered

print("--- 8. panels ---")

# Drawing code that never gets drawn is how a button ends up registered
# outside the panel, or not registered at all. Same shape as
# test_report_20260816.py's panel section: render headless, then identify the
# buttons by CLICKING them, since the panel keeps only (rect, callback).
import pygame

from game import config as game_config
from game.shooting import ShootingController
from game.ui.action_panel import ActionPanel
from game.ui.game_status_panel import GameStatusPanel

pygame.init()
pygame.display.set_mode((320, 240))

state8 = GameState()
tracker8 = movement_tracker()
mover8 = MovementController(turn_tracker=tracker8, all_tokens=state8.tokens,
                            player_name="Player 1", dice_manager=DiceManager())
panel_squad = aeldari(build(STRIKE_TEAM, "Player 1", name="Panel Guardians"))
line_up(panel_squad, x=10.0, y=10.0)
for model in panel_squad.models:
    state8.add_token(model)
mover8.select(panel_squad.models[0])

p8 = pool(movement_controller=mover8, turn_tracker=tracker8)
p8.sync_battle_round(1)

panel = ActionPanel()
panel_rect = pygame.Rect(0, 0, game_config.LEFT_PANEL_WIDTH, 900)
surface = pygame.Surface((game_config.LEFT_PANEL_WIDTH, 900))
panel_sc = ShootingController(
    all_tokens=state8.tokens, dice_manager=DiceManager(),
    decision_manager=scene["decision"], player_name="Player 1",
)

panel.draw(surface, panel_rect, mover8, panel_sc, None, battle_focus_pool=p8)
with_pool = list(panel._buttons)
checks.true("buttons were drawn for the selected unit", bool(with_pool))
checks.true("every button stays inside the 220px panel",
            all(panel_rect.contains(r) for r, _ in with_pool))

panel.draw(surface, panel_rect, mover8, panel_sc, None)
without_pool = list(panel._buttons)
checks.true("the pool adds buttons that are not there without it",
            len(with_pool) > len(without_pool))

# Click each new button and see which one spends a token.
panel.draw(surface, panel_rect, mover8, panel_sc, None, battle_focus_pool=p8)
spent_by = []
for rect, callback in list(panel._buttons):
    before = p8.tokens["Player 1"]
    callback()
    if p8.tokens["Player 1"] < before:
        spent_by.append(rect)
    p8.reset_phase([panel_squad])
checks.eq("exactly two manoeuvres are offered to foot infantry mid-Movement "
          "(Swift as the Wind + Flitting Shadows; Star Engines needs a VEHICLE that Advanced)",
          len(spent_by), 2)

status = GameStatusPanel()
status_rect = pygame.Rect(0, 0, game_config.RIGHT_PANEL_WIDTH, 500)
with_tokens = pygame.Surface((game_config.RIGHT_PANEL_WIDTH, 500))
without_tokens = pygame.Surface((game_config.RIGHT_PANEL_WIDTH, 500))
status.draw(with_tokens, status_rect, tracker8, None, None, p8)
status.draw(without_tokens, status_rect, tracker8, None, None, pool(players=()))
checks.true("the Battle Focus row is drawn for an ASURYANI army",
            pygame.image.tobytes(with_tokens, "RGB") != pygame.image.tobytes(without_tokens, "RGB"))

no_pool = pygame.Surface((game_config.RIGHT_PANEL_WIDTH, 500))
status.draw(no_pool, status_rect, tracker8, None, None, None)
checks.true("and a game without one renders exactly as it did before",
            pygame.image.tobytes(no_pool, "RGB") == pygame.image.tobytes(without_tokens, "RGB"))


# --------------------------------------------------- 9. Sudden Strike

print("--- 9. Sudden Strike ---")

import copy as _copy

from game.consolidate import CONSOLIDATE_RANGE_IN, ConsolidateController
from game import fight as fight_module
from game.fight import FightController
from game.pile_in import PILE_IN_RANGE_IN, PILE_IN_TARGET_RANGE_IN, PileInController
from game.turn import PHASE_FIGHT
from testkit import DecisionManager, script


def trim(squad, keep, state=None):
    """Cut a unit down to `keep` models, dropping the rest from the board.

    Needed because a 10-model unit lined up in a row spans over 9", which
    rule 09.02's spread limit rejects on confirm - and these sections confirm
    real moves. A shorter unit is the honest way to get a legal formation
    without hand-placing a blob."""
    dropped = squad.models[keep:]
    squad.models = squad.models[:keep]
    if state is not None:
        for model in dropped:
            if model in state.tokens:
                state.tokens.remove(model)
    return squad


state9 = GameState()
tracker9 = TurnTracker(first_player="Player 1")
tracker9.phase_index = PHASES.index(PHASE_FIGHT)
tracker9.turn_owner = "Player 1"
tracker9.set_active("Player 1")
mover9 = MovementController(turn_tracker=tracker9, all_tokens=state9.tokens, player_name="Player 1")

strikers = aeldari(build(STRIKE_TEAM, "Player 1", name="Strikers"))
foes = build(STRIKE_TEAM, "Player 2", name="Foes")
for squad_, y in ((strikers, 20.0), (foes, 21.2)):
    line_up(squad_, x=10.0, y=y)
    for model in squad_.models:
        state9.add_token(model)

pc = PileInController(turn_tracker=tracker9, all_tokens=state9.tokens, movement_controller=mover9)
mover9.select(strikers.models[0])
pc.start_pile_in(strikers)
checks.eq("baseline pile-in reaches the printed 3 inches",
          round(mover9.remaining_range[strikers.models[0].id], 2), round(PILE_IN_RANGE_IN, 2))
mover9.cancel_move()

p9 = pool(movement_controller=mover9, turn_tracker=tracker9)
p9.sync_battle_round(1)
checks.true("the trigger is available in the Fight phase", p9.can_sudden_strike(strikers))
checks.true("using it succeeds", p9.use_sudden_strike(strikers))

pc.piled_in_squad_ids.clear()
mover9.select(strikers.models[0])
pc.start_pile_in(strikers)
checks.eq("with Sudden Strike the pile-in reaches 6 inches",
          round(mover9.remaining_range[strikers.models[0].id], 2), 6.0)
mover9.cancel_move()

checks.eq("rule 12.03's own BEFORE MOVING target range is untouched", PILE_IN_TARGET_RANGE_IN, 5.0)
checks.eq("and the printed constants themselves are never mutated",
          (PILE_IN_RANGE_IN, CONSOLIDATE_RANGE_IN), (3.0, 3.0))
checks.eq("melee_move_range_in reports 6 for a Sudden Strike unit",
          battle_focus.melee_move_range_in(strikers, CONSOLIDATE_RANGE_IN), 6.0)
checks.eq("and the printed 3 for anyone else",
          battle_focus.melee_move_range_in(foes, CONSOLIDATE_RANGE_IN), 3.0)

# Consolidation: one number decides both how far it moves and what it can
# reach, so per the user's decision the 6 inches widens the reach too. The
# range lives in determine_mode()'s ENGAGING branch (12.08) - ongoing_targets()
# filters on engagement instead, and is deliberately NOT affected.
state9b = GameState()
loner = aeldari(trim(build(STRIKE_TEAM, "Player 1", name="Loner"), 3))
distant = trim(build(STRIKE_TEAM, "Player 2", name="Distant"), 3)
for squad_, y in ((loner, 20.0), (distant, 24.5)):
    line_up(squad_, x=40.0, y=y)
    for model in squad_.models:
        state9b.add_token(model)
cc = ConsolidateController(turn_tracker=tracker9, all_tokens=state9b.tokens,
                           movement_controller=mover9)
checks.eq("precondition: unengaged, and the enemy sits between 3 and 6 inches",
          (loner.is_engaged(state9b.tokens), 3.0 < loner.min_distance_to(distant) <= 6.0),
          (False, True))
checks.eq("without the manoeuvre that enemy is out of consolidation reach",
          cc.determine_mode(loner), None)
loner.sudden_strike_active = True
checks.eq("with it, an Engaging Consolidation becomes available",
          cc.determine_mode(loner), "engaging")
loner.sudden_strike_active = False

p9.reset_phase([strikers])
checks.eq("the grant ends with the phase", strikers.sudden_strike_active, False)

fc9 = FightController(turn_tracker=tracker9, all_tokens=state9.tokens, game_log=Log())
p9b = pool(movement_controller=mover9, turn_tracker=tracker9, fight_controller=fc9)
p9b.sync_battle_round(1)
fc9.fought_squad_ids.add(strikers)
checks.eq("a unit that already fought is past the trigger", p9b.can_sudden_strike(strikers), False)
fc9.fought_squad_ids.discard(strikers)
tracker9.phase_index = PHASES.index(PHASE_MOVEMENT)
checks.eq("and it is a Fight phase manoeuvre only", p9b.can_sudden_strike(strikers), False)
tracker9.phase_index = PHASES.index(PHASE_FIGHT)


# --------------------------------- 9b. Sudden Strike's second window
#
# User report: "ich kann mich ja auch 6 zoll consolidaten. das wird mir aber
# nicht angeboten beim consolidate". Measured before the fix: with the enemy
# 4.5" away and the Fight step over, determine_mode() answered None (nothing
# within the printed 3"), so the unit was offered no consolidation at ALL -
# and can_sudden_strike() had already shut, so there was no way left to buy
# the 6" that opens it. The manoeuvre is now offered in a second window, just
# before the Consolidation move. See BattleFocusPool.can_sudden_strike().

print("--- 9b. Sudden Strike at the Consolidation step ---")


def consolidation_scene(gap):
    """A finished Fight step: both units have fought, nobody bought Sudden
    Strike, and the enemy sits `gap` inches away."""
    st = GameState()
    tr = TurnTracker(first_player="Player 1")
    tr.phase_index = PHASES.index(PHASE_FIGHT)
    tr.turn_owner = "Player 1"
    tr.set_active("Player 1")
    mine = aeldari(trim(build(STRIKE_TEAM, "Player 1", name="Mine"), 3))
    foe = trim(build(STRIKE_TEAM, "Player 2", name="Foe"), 3)
    line_up(mine, x=40.0, y=20.0)
    line_up(foe, x=40.0, y=20.0 + gap)
    for squad_ in (mine, foe):
        for model in squad_.models:
            st.add_token(model)
    mover_ = MovementController(turn_tracker=tr, all_tokens=st.tokens,
                                player_name="Player 1")
    fc_ = FightController(turn_tracker=tr, all_tokens=st.tokens, game_log=Log())
    cc_ = ConsolidateController(turn_tracker=tr, all_tokens=st.tokens,
                                movement_controller=mover_, fight_controller=fc_)
    pool_ = pool(players=("Player 1", "Player 2"), movement_controller=mover_,
                 turn_tracker=tr, fight_controller=fc_, all_tokens=st.tokens)
    pool_.consolidate_controller = cc_
    pool_.sync_battle_round(1)
    fc_.fought_squad_ids.update({mine, foe})
    fc_.state = fight_module.DONE
    mover_.select(mine.models[0])
    return {"mine": mine, "foe": foe, "cons": cc_, "mover": mover_,
            "pool": pool_, "fight": fc_, "state": st, "turn": tr}


# The reported board, end to end through the real controllers.
s9b = consolidation_scene(4.5)
checks.true("precondition: the enemy is outside the printed 3in but inside 6in",
            3.0 < s9b["mine"].min_distance_to(s9b["foe"]) <= 6.0)
checks.eq("without the manoeuvre no consolidation is available at all",
          s9b["cons"].determine_mode(s9b["mine"]), None)
checks.true("Sudden Strike is offered at the Consolidation step",
            s9b["pool"].can_sudden_strike(s9b["mine"]))
checks.true("and using it there succeeds", s9b["pool"].use_sudden_strike(s9b["mine"]))
checks.eq("which opens an Engaging Consolidation",
          s9b["cons"].determine_mode(s9b["mine"]), "engaging")
s9b["cons"].start_consolidate(s9b["mine"])
s9b["cons"].toggle_engaging_target(s9b["foe"])
s9b["cons"].begin_engaging_move()
checks.eq("and the move itself really reaches 6 inches",
          round(s9b["mover"].remaining_range[s9b["mine"].models[0].id], 2), 6.0)

# Still engaged: the mode never changes, but the extra 3" of movement does -
# so the manoeuvre must be offered here too, not only when it unlocks a mode.
s9c = consolidation_scene(1.2)
checks.eq("an already-engaged unit consolidates Ongoing either way",
          s9c["cons"].determine_mode(s9c["mine"]), "ongoing")
checks.true("it is offered there as well", s9c["pool"].can_sudden_strike(s9c["mine"]))
s9c["pool"].use_sudden_strike(s9c["mine"])
s9c["cons"].start_consolidate(s9c["mine"])
checks.eq("and lengthens the Ongoing Consolidation to 6 inches",
          round(s9c["mover"].remaining_range[s9c["mine"].models[0].id], 2), 6.0)

# The refusals - this project's standing rule is that the engine must not
# offer what would buy nothing.
s9d = consolidation_scene(20.0)
checks.eq("nothing is reachable even at 6 inches",
          s9d["cons"].determine_mode(s9d["mine"], reach=6.0), None)
checks.eq("so the manoeuvre is not offered",
          s9d["pool"].can_sudden_strike(s9d["mine"]), False)

s9e = consolidation_scene(1.2)
s9e["cons"].start_consolidate(s9e["mine"])
checks.eq("precondition: a consolidation move is under way",
          s9e["mover"].move_mode, "consolidate")
checks.eq("a token spent now could not lengthen it, so it is refused",
          s9e["pool"].can_sudden_strike(s9e["mine"]), False)

s9f = consolidation_scene(4.5)
s9f["fight"].fought_squad_ids.discard(s9f["mine"])
checks.eq("precondition: a unit that never fought owes no consolidation",
          s9f["cons"].can_consolidate(s9f["mine"]), False)
checks.eq("the second window does not apply to it",
          s9f["pool"].can_sudden_strike(s9f["mine"]), False)

s9g = consolidation_scene(4.5)
s9g["mine"].sudden_strike_active = True
checks.eq("and a unit that already has the grant is never offered it twice",
          s9g["pool"].can_sudden_strike(s9g["mine"]), False)

# Window 1 is untouched: bought before the unit is selected to fight.
s9h = consolidation_scene(1.2)
s9h["fight"].fought_squad_ids.clear()
s9h["fight"].state = fight_module.SELECTING
s9h["fight"].engaged_at_start = {s9h["mine"], s9h["foe"]}
checks.true("window 1 (before fighting) still opens",
            s9h["pool"].can_sudden_strike(s9h["mine"]))

s9h2 = consolidation_scene(4.5)
s9h2["pool"].consolidate_controller = None
checks.eq("with no ConsolidateController attached at all, only window 1 exists",
          s9h2["pool"].can_sudden_strike(s9h2["mine"]), False)

# determine_mode(reach=) must be side-effect free - it is asked from the panel
# every frame, and a probe that flipped squad.sudden_strike_active instead
# would leave the grant standing if anything in between raised.
s9i = consolidation_scene(4.5)
s9i["cons"].determine_mode(s9i["mine"], reach=6.0)
checks.eq("asking 'what would 6 inches open' grants nothing",
          getattr(s9i["mine"], "sudden_strike_active", False), False)
checks.eq("and the default reach is still the printed 3 inches",
          s9i["cons"].determine_mode(s9i["mine"]), None)

# The button has to reach the screen - a predicate nothing draws is exactly
# the "built but never fed" failure this repo has hit six times.
s9j = consolidation_scene(4.5)
panel9 = ActionPanel()
rect9 = pygame.Rect(0, 0, game_config.LEFT_PANEL_WIDTH, 900)
surf9 = pygame.Surface((game_config.LEFT_PANEL_WIDTH, 900))
sc9 = ShootingController(all_tokens=s9j["state"].tokens, dice_manager=DiceManager(),
                         decision_manager=DecisionManager(), player_name="Player 1")
panel9.draw(surf9, rect9, s9j["mover"], sc9, None,
            fight_controller=s9j["fight"], consolidate_controller=s9j["cons"],
            battle_focus_pool=s9j["pool"])
buttons9 = list(panel9._buttons)
checks.true("the Consolidation-step panel draws buttons", bool(buttons9))
spent9 = []
for rect_, callback_ in buttons9:
    before = s9j["pool"].tokens["Player 1"]
    callback_()
    if s9j["pool"].tokens["Player 1"] < before:
        spent9.append(rect_)
    s9j["mine"].sudden_strike_active = False
    s9j["pool"].tokens["Player 1"] = before
checks.eq("exactly one of them is Sudden Strike", len(spent9), 1)


# ------------------------------------------------------ 10. Fade Back

print("--- 10. Fade Back ---")

scene10 = shooting_scene(STRIKE_TEAM, STRIKE_TEAM, attacker_owner="Player 2", gap=8.0)
shooter10, runner10 = scene10["attacker"], scene10["target"]
aeldari(trim(runner10, 3, scene10["state"]))
line_up(runner10, x=10.0, y=28.0)
tracker10 = scene10["turn"]
mover10 = MovementController(turn_tracker=tracker10, all_tokens=scene10["state"].tokens,
                             player_name="Player 1")


def reactive_pool(mover, tracker, tokens, decisions=None, dice=None):
    p = battle_focus.BattleFocusPool(
        players=("Player 1",), game_log=Log(), movement_controller=mover,
        turn_tracker=tracker, dice_manager=dice or DiceManager(),
        decision_manager=decisions or DecisionManager(), all_tokens=tokens,
    )
    p.sync_battle_round(1)
    return p


p10 = reactive_pool(mover10, tracker10, scene10["state"].tokens,
                    decisions=scene10["decision"], dice=scene10["dice"])

checks.eq("it is the opponent's Shooting phase", tracker10.active_player, "Player 2")
checks.true("a unit that was hit gets the offer", p10.offer_fade_back(shooter10, {runner10}))
checks.eq("and the offer belongs to the reacting player", scene10["decision"].player, "Player 1")
labels = [o["label"] for o in scene10["decision"].options]
checks.true("the option names the unit", any(runner10.name in l for l in labels))
checks.true("declining is offered", any("Decline" in l for l in labels))

script(4)  # the D6 of "D6+1 inches"
scene10["decision"].choose(0)
checks.eq("a token was spent", p10.tokens["Player 1"], 3)
checks.eq("a Normal move is open", mover10.move_mode, "battle_focus")
checks.eq("with D6+1 inches of range",
          round(mover10.remaining_range[runner10.models[0].id], 2), 5.0)
checks.eq("the reacting player is active for the duration - without this "
          "MovementController.select() would refuse the unit and the token "
          "would buy nothing", tracker10.active_player, "Player 1")
checks.true("confirming succeeds", p10.confirm_reactive_move())
checks.eq("and hands the turn back", tracker10.active_player, "Player 2")

p10b = reactive_pool(mover10, tracker10, scene10["state"].tokens)
checks.eq("a unit that was NOT hit gets nothing", p10b.offer_fade_back(shooter10, set()), False)
checks.eq("nor one outside the hit set",
          p10b.offer_fade_back(shooter10, {build(STRIKE_TEAM, "Player 1", name="Untouched")}), False)
checks.eq("and the shooter's own side is never offered it",
          p10b.offer_fade_back(runner10, {shooter10}), False)

titan = aeldari(build(STRIKE_TEAM, "Player 1", name="Titan"))
titan.datasheet = _copy.copy(titan.datasheet)
titan.datasheet.keywords = tuple(titan.datasheet.keywords) + ("TITANIC",)
checks.true("a TITANIC unit is excluded", battle_focus.excluded_from_reactive_manoeuvre(titan))
checks.eq("and is not offered the manoeuvre", p10b.offer_fade_back(shooter10, {titan}), False)
checks.eq("an ordinary unit is not excluded",
          battle_focus.excluded_from_reactive_manoeuvre(runner10), False)


# ------------------------- 10b. a unit that is already dead is not asked

print("--- 10b. wiped-out units are not offered a reactive move ---")

# User report: "Du brauchst nicht nach 'Fadeback' der aeldari zu fragen, wenn
# der Trupp vollstaendig gestorben ist."
#
# Fade Back fires from ShootingController.on_squad_finished_shooting, and that
# hook runs INSIDE the activation that did the killing - remove_dead_models()
# runs once per frame, afterwards. So the unit this activation wiped out is
# still in `hit_squads` with a full models list of corpses. Testing
# `squad.models` alone answers True for it, which is why this needs its own
# predicate rather than the emptiness check _perform_reactive() already had -
# and that one runs after the D6 and after the token is spent anyway.

dead10 = aeldari(trim(build(STRIKE_TEAM, "Player 1", name="Wiped"), 3))
line_up(dead10, x=10.0, y=34.0)
checks.true("a living unit counts as on the battlefield",
            battle_focus.is_on_the_battlefield(dead10))

p10c = reactive_pool(mover10, tracker10, scene10["state"].tokens)
checks.true("and while it lives it IS offered Fade Back",
            p10c.offer_fade_back(shooter10, {dead10}))

# BEFORE the sweep: every model at 0 wounds, all still in squad.models.
for model in dead10.models:
    model.current_wounds = 0
checks.eq("every model is dead", sum(1 for m in dead10.models if not m.is_dead()), 0)
checks.true("but the corpses are still in squad.models - this is the frame the "
            "hook runs in", len(dead10.models) > 0)
checks.eq("a wiped-out unit is not on the battlefield",
          battle_focus.is_on_the_battlefield(dead10), False)

p10d = reactive_pool(mover10, tracker10, scene10["state"].tokens,
                     decisions=DecisionManager())
checks.eq("and it is NOT offered Fade Back", p10d.offer_fade_back(shooter10, {dead10}), False)
checks.eq("so no decision is raised at all", p10d.decision_manager.is_pending, False)
checks.eq("and no token is spent", p10d.tokens["Player 1"], 4)

# AFTER the sweep, one frame later: models list emptied. Same answer, and it is
# the same expression that gives it - an empty list makes any() False.
dead10.models = []
checks.eq("an emptied unit is not on the battlefield either",
          battle_focus.is_on_the_battlefield(dead10), False)
p10e = reactive_pool(mover10, tracker10, scene10["state"].tokens,
                     decisions=DecisionManager())
checks.eq("nor offered Fade Back after the sweep",
          p10e.offer_fade_back(shooter10, {dead10}), False)

# A live unit hit in the same activation still gets its offer - the gate is per
# unit, not "somebody in this activation died".
p10f = reactive_pool(mover10, tracker10, scene10["state"].tokens,
                     decisions=DecisionManager())
checks.true("a survivor hit by the same activation is still offered it",
            p10f.offer_fade_back(shooter10, {dead10, runner10}))
checks.eq("and only the survivor is named",
          [o["label"] for o in p10f.decision_manager.options
           if "Decline" not in o["label"]],
          [f'Fade Back: {runner10.name} makes a D6+1" Normal move'])

# The gate lives in _reactive_candidates(), which both manoeuvres go through,
# so Opportunity Seized is covered by construction rather than separately.
src_bf = _read_source("game/battle_focus.py")
gate = "if not is_on_the_battlefield(squad):"
checks.eq("the check is written exactly once", src_bf.count(gate), 1)
checks.eq("and the function it sits in is _reactive_candidates - the gate BOTH "
          "manoeuvres go through, so Opportunity Seized inherits it rather "
          "than needing its own copy",
          src_bf[:src_bf.index(gate)].rsplit("    def ", 1)[1].split("(")[0],
          "_reactive_candidates")

# A/B: put the pre-fix world back - the gate removed - and the offer returns.
# On a FRESH corpse, not on dead10: that one has been emptied by the sweep
# above, and an emptied unit is refused further down the gate anyway, so the
# probe would pass for the wrong reason and report the bug had never existed.
corpse = aeldari(trim(build(STRIKE_TEAM, "Player 1", name="Fresh Corpse"), 3))
line_up(corpse, x=10.0, y=36.0)
for model in corpse.models:
    model.current_wounds = 0

_pre_fix = battle_focus.is_on_the_battlefield
battle_focus.is_on_the_battlefield = lambda squad: True
try:
    p10g = reactive_pool(mover10, tracker10, scene10["state"].tokens,
                         decisions=DecisionManager())
    checks.true("A/B: without the gate the wiped-out unit IS offered Fade Back "
                "again - i.e. the gate is what answers the report",
                p10g.offer_fade_back(shooter10, {corpse}))
finally:
    battle_focus.is_on_the_battlefield = _pre_fix

p10h = reactive_pool(mover10, tracker10, scene10["state"].tokens,
                     decisions=DecisionManager())
checks.eq("and with it back in place, it is refused again",
          p10h.offer_fade_back(shooter10, {corpse}), False)


# ----------------------------------------------- 11. Opportunity Seized

print("--- 11. Opportunity Seized ---")

state11 = GameState()
tracker11 = movement_tracker(owner="Player 2")   # the FALLING BACK player's turn
mover11 = MovementController(turn_tracker=tracker11, all_tokens=state11.tokens,
                             player_name="Player 2")
watcher = aeldari(trim(build(STRIKE_TEAM, "Player 1", name="Watchers"), 3))
retreater = trim(build(STRIKE_TEAM, "Player 2", name="Retreater"), 3)
bystander = aeldari(trim(build(STRIKE_TEAM, "Player 1", name="Bystander"), 3))
for squad_, y in ((watcher, 30.0), (retreater, 31.2), (bystander, 50.0)):
    line_up(squad_, x=10.0, y=y)
    for model in squad_.models:
        state11.add_token(model)

p11 = reactive_pool(mover11, tracker11, state11.tokens)
checks.true("the two start the phase engaged", watcher.is_engaged_with(retreater))
p11.reset_phase([watcher, retreater, bystander])   # this is where the snapshot happens

for model in retreater.models:
    model.y_in = 45.0                               # it falls back out of engagement
checks.eq("afterwards the board no longer shows them engaged",
          watcher.is_engaged_with(retreater), False)
checks.true("but the phase-start snapshot still qualifies the watcher",
            p11.offer_opportunity_seized(retreater))
opts = [o["label"] for o in p11.decision_manager.options]
checks.true("the watcher is offered", any(watcher.name in l for l in opts))
checks.eq("a unit that was never engaged with it is not",
          any(bystander.name in l for l in opts), False)
checks.eq("and the offer belongs to the reacting player",
          p11.decision_manager.player, "Player 1")

script(2)
p11.decision_manager.choose(0)
checks.eq("token spent", p11.tokens["Player 1"], 3)
checks.eq("D6+1 inches of Normal move",
          round(mover11.remaining_range[watcher.models[0].id], 2), 3.0)
checks.true("cancelling backs it out", p11.cancel_reactive_move())
checks.eq("and hands the turn back", tracker11.active_player, "Player 2")

# The hook itself - a real Fall Back move has to fire it.
fired = []
mover11.on_fall_back_finished = fired.append
for model in retreater.models:
    model.y_in = 31.2                               # engaged again, so a Fall Back is legal
mover11.select(retreater.models[0])
checks.true("a Fall Back is available", mover11.can_make_fall_back_move(retreater))
mover11.start_fall_back_move("ordered_retreat")
for model in retreater.models:
    model.y_in += 4.0
mover11.confirm_move()
checks.eq("confirm_move() fired the hook once, with the squad that fell back",
          fired, [retreater])


# ------------------------------------------- 12. A/B probes, new manoeuvres

print("--- 12. A/B probes (new manoeuvres) ---")

saved_range = battle_focus.melee_move_range_in
battle_focus.melee_move_range_in = lambda squad, printed: printed
strikers.sudden_strike_active = True
pc.piled_in_squad_ids.clear()
mover9.select(strikers.models[0])
pc.start_pile_in(strikers)
checks.eq("A/B: neutralised, the pile-in is back to 3 inches",
          round(mover9.remaining_range[strikers.models[0].id], 2), 3.0)
mover9.cancel_move()
battle_focus.melee_move_range_in = saved_range
pc.piled_in_squad_ids.clear()
mover9.select(strikers.models[0])
pc.start_pile_in(strikers)
checks.eq("A/B: restored, it is 6 inches again",
          round(mover9.remaining_range[strikers.models[0].id], 2), 6.0)
mover9.cancel_move()

saved_excl = battle_focus.excluded_from_reactive_manoeuvre
battle_focus.excluded_from_reactive_manoeuvre = lambda squad: False
checks.true("A/B: without the TITANIC exclusion the titan IS offered",
            p10b.offer_fade_back(shooter10, {titan}))
battle_focus.excluded_from_reactive_manoeuvre = saved_excl

# --- the AI has to wait for a reactive move it does not own -----------------
# User report: "ki hat mich den fadeback move nicht ausfuehren lassen, sondern
# hat direkt weitergemacht". Picking "spend a token" resolves the
# DecisionManager break point immediately, but all that does is OPEN a Normal
# move the human still has to drag and confirm - and nothing looked at that
# open move, so the AI carried straight on with its next shooting activation
# underneath it. Same shape as the Rapid Ingress placement case _is_blocked()
# already covers.
print("--- the AI waits for a foreign reactive move ---")
from ai.agent_driver import _is_blocked  # noqa: E402
from game.factions import aeldari as ae  # noqa: E402
from game.turn import PHASE_SHOOTING as _PS  # noqa: E402
from testkit import DiceManager as _DiceM, GameState as _GameState  # noqa: E402
from testkit import TurnTracker as _TT, build as _build, line_up as _line_up  # noqa: E402

_DM = DecisionManager
_Mover = MovementController

_wait_state = _GameState()
_wait_squad = _build(ae.GUARDIAN_DEFENDERS, "Player 1", name="1 Guardian Defenders W1")
_line_up(_wait_squad)
for _m in _wait_squad.models:
    _wait_state.add_token(_m)
_wait_tt = _TT("Player 2")
while _wait_tt.phase != _PS or _wait_tt.turn_owner != "Player 2":
    _wait_tt.advance_phase()
_wait_mover = _Mover(obstacles=[], all_tokens=_wait_state.tokens, turn_tracker=_wait_tt)
_wait_dec, _wait_dice = _DM(), _DiceM()


def _ai_blocked(mover=None):
    return _is_blocked(_wait_tt, _wait_dec, _wait_dice, None, "Player 2",
                       movement_controller=mover)


checks.eq("nothing open: the AI acts", _ai_blocked(_wait_mover), False)

# What BattleFocusPool._perform_reactive() does: hand the active-player flag to
# the reacting player, then open the move.
_wait_tt.set_active("Player 1")
_wait_mover.select(_wait_squad.models[0])
_wait_mover.start_battle_focus_move(_wait_squad, 5.0)
checks.eq("the granted move is open", _wait_mover.move_mode, "battle_focus")
checks.eq("so the AI waits", _ai_blocked(_wait_mover), True)
# A/B: this is exactly what the AI used to see - nothing at all.
checks.eq("A/B: without the check the AI carried on regardless", _ai_blocked(None), False)

_wait_mover.cancel_move()
_wait_tt.set_active("Player 2")
checks.eq("and it is released once the move is resolved", _ai_blocked(_wait_mover), False)

# The AI's OWN granted move must NOT block it - it is the thing driving it.
_own_squad = _build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders W2")
_line_up(_own_squad, y=30.0)
for _m in _own_squad.models:
    _wait_state.add_token(_m)
_wait_mover.select(_own_squad.models[0])
_wait_mover.start_battle_focus_move(_own_squad, 5.0)
checks.eq("its own reactive move does not deadlock it", _ai_blocked(_wait_mover), False)
_wait_mover.cancel_move()


# ------------------------------------------ 13. the turquoise colour code

print("--- 13. turquoise colour code ---")

# User: "colorcode fuer agile manouvers ist momentan lila wie stratagems. soll
# aber tuerkis sein. (buttons, ueberschriften)".
#
# An Agile Manoeuvre spends a Battle Focus TOKEN, not CP, so wearing rule
# 15.01's violet said the wrong thing about what a click costs. Two halves,
# and each is asserted where it is actually DRAWN rather than at the constant:
# the BUTTONS through the real ActionPanel, the UEBERSCHRIFT through the real
# DecisionOverlay. A palette entry nothing blits is the failure this section
# exists to catch.

import math

from game.decision import DecisionManager as RealDecisionManager
from game.ui import button_style
from game.ui.decision_overlay import DecisionOverlay

TURQUOISE = button_style.BORDER_NORMAL_BATTLE_FOCUS
VIOLET = button_style.BORDER_NORMAL_STRATAGEM

checks.true("the accent is registered, so accent='battle_focus' is not "
            "silently the default blue",
            "battle_focus" in button_style._PALETTES)
# .get(), not [] - an A/B probe that DELETES the entry made this line raise
# instead of going red, which hides which check broke. Fourth instance of that
# lesson in this repo (see the two str.index() guards and the padded-row fix in
# test_faction_badges.py).
checks.true("and it is not the default palette under a new name",
            button_style._PALETTES.get("battle_focus") != button_style._PALETTES[None])

# Turquoise sits BETWEEN this palette's blue and its green, so it is by
# construction closer to both than they are to each other - inherent to the
# hue the user named, not a slip. Measured so the tightest pair is written
# down: the neighbour that shares a panel with these buttons is the default
# blue ("Move"/"Advance" sit right beside them).
_gap_blue = math.dist(TURQUOISE, button_style.BORDER_NORMAL)
_gap_green = math.dist(TURQUOISE, button_style.BORDER_NORMAL_CONFIRM)
checks.true("turquoise is clearly apart from the default blue beside it "
            "(dist %.1f)" % _gap_blue, _gap_blue > 60)
checks.true("and from the confirm green (dist %.1f)" % _gap_green, _gap_green > 60)
checks.true("and nowhere near the violet it replaces (dist %.1f)"
            % math.dist(TURQUOISE, VIOLET),
            math.dist(TURQUOISE, VIOLET) > 150)


def accent_pixels(surface, rect):
    """(turquoise count, violet count) inside this rect. Exact matches only:
    draw_button() strokes the border in the palette colour undithered, so an
    exact hit means that palette really drew."""
    turq = viol = 0
    for x in range(rect.x, min(rect.right, surface.get_width())):
        for y in range(rect.y, min(rect.bottom, surface.get_height())):
            px = surface.get_at((x, y))[:3]
            if px == TURQUOISE:
                turq += 1
            elif px == VIOLET:
                viol += 1
    return turq, viol


# --- the buttons -----------------------------------------------------------
# Its OWN scene rather than section 8's: that one has already spent its way
# through the pool, and a drained pool offers no manoeuvre buttons at all -
# which would make this section pass by measuring nothing.
state13 = GameState()
tracker13 = movement_tracker()
mover13 = MovementController(turn_tracker=tracker13, all_tokens=state13.tokens,
                             player_name="Player 1", dice_manager=DiceManager())
squad13 = aeldari(build(STRIKE_TEAM, "Player 1", name="Colour Guardians"))
line_up(squad13, x=10.0, y=10.0)
for model13 in squad13.models:
    state13.add_token(model13)
mover13.select(squad13.models[0])
pool13 = pool(movement_controller=mover13, turn_tracker=tracker13)
pool13.sync_battle_round(1)

panelc = ActionPanel()
rectc = pygame.Rect(0, 0, game_config.LEFT_PANEL_WIDTH, 900)
scc = ShootingController(all_tokens=state13.tokens, dice_manager=DiceManager(),
                         decision_manager=DecisionManager(), player_name="Player 1")
colour_surface = pygame.Surface((game_config.LEFT_PANEL_WIDTH, 900))
colour_surface.fill((0, 0, 0))
panelc.draw(colour_surface, rectc, mover13, scc, None, battle_focus_pool=pool13)

# Identify the manoeuvre buttons the way section 8 does - by CLICKING them and
# seeing which spend a token - so this cannot drift from which buttons the
# rule actually offers.
manoeuvre_rects = []
for rect13, callback13 in list(panelc._buttons):
    before13 = pool13.tokens["Player 1"]
    callback13()
    if pool13.tokens["Player 1"] < before13:
        manoeuvre_rects.append(rect13)
    pool13.reset_phase([squad13])
checks.eq("the manoeuvre buttons are on screen to be measured", len(manoeuvre_rects), 2)

for rect13 in manoeuvre_rects:
    turq13, viol13 = accent_pixels(colour_surface, rect13)
    checks.true("an Agile Manoeuvre button is drawn in turquoise", turq13 > 0)
    checks.eq("and carries no Stratagem violet at all", viol13, 0)

# Gegenprobe: a FREE action drawn in the same pass must NOT be turquoise, or
# this section would pass on a panel that had gone turquoise all over.
free_rects = [r for r, _ in panelc._buttons if r not in manoeuvre_rects]
checks.true("there are non-manoeuvre buttons in the same render", bool(free_rects))
checks.eq("none of them borrowed the turquoise",
          sum(accent_pixels(colour_surface, r)[0] for r in free_rects), 0)

# Sudden Strike is the fourth manoeuvre button, at its own draw site in a
# different phase - measured separately rather than assumed to have come along.
s13 = consolidation_scene(4.5)
panel13 = ActionPanel()
strike_surface = pygame.Surface((game_config.LEFT_PANEL_WIDTH, 900))
strike_surface.fill((0, 0, 0))
sc13 = ShootingController(all_tokens=s13["state"].tokens, dice_manager=DiceManager(),
                          decision_manager=DecisionManager(), player_name="Player 1")
panel13.draw(strike_surface, pygame.Rect(0, 0, game_config.LEFT_PANEL_WIDTH, 900),
             s13["mover"], sc13, None, fight_controller=s13["fight"],
             consolidate_controller=s13["cons"], battle_focus_pool=s13["pool"])
strike_rects = []
for rect13, callback13 in list(panel13._buttons):
    before13 = s13["pool"].tokens["Player 1"]
    callback13()
    if s13["pool"].tokens["Player 1"] < before13:
        strike_rects.append(rect13)
    s13["mine"].sudden_strike_active = False
    s13["pool"].tokens["Player 1"] = before13
checks.eq("the Sudden Strike button is on screen", len(strike_rects), 1)
strike_turq, strike_viol = accent_pixels(strike_surface, strike_rects[0])
checks.true("Sudden Strike is turquoise too", strike_turq > 0)
checks.eq("and it dropped the violet as well", strike_viol, 0)

# --- the ueberschrift ------------------------------------------------------
# DecisionManager.accent is the ONE derived answer the overlay colours by.
dm13 = RealDecisionManager()
dm13.request("Player 1", "plain core decision", [("Yes", None)])
checks.eq("a core/datasheet decision has no accent", dm13.accent, None)
dm13.choose(0)
dm13.request("Player 1", "a stratagem", [("Yes", None)], is_stratagem=True)
checks.eq("a Stratagem prompt is still violet", dm13.accent, "stratagem")
dm13.choose(0)
dm13.request("Player 1", "a manoeuvre", [("Yes", None)], is_battle_focus=True)
checks.eq("an Agile Manoeuvre prompt is turquoise", dm13.accent, "battle_focus")
checks.eq("and is NOT flagged a Stratagem - it spends a token, not CP",
          dm13.is_stratagem, False)
dm13.choose(0)
checks.eq("an empty queue has no accent", dm13.accent, None)

# The real offer, raised by the pool itself, must carry the flag - a colour
# nothing sets is the same dead wiring as a palette nothing blits.
offer_dm = RealDecisionManager()
offer_pool = pool(decision_manager=offer_dm)
offer_squad = aeldari(build(STRIKE_TEAM, "Player 1", name="Offer Guardians"))
line_up(offer_squad, x=10.0, y=10.0)
checks.true("the pool raises a reactive offer",
            offer_pool._raise_offer("Player 1", battle_focus.FADE_BACK,
                                    [offer_squad], "a test"))
checks.eq("and flags it turquoise, not violet", offer_dm.accent, "battle_focus")

# ...and that the OVERLAY paints it. Same question as the buttons: what
# reaches the screen.
overlay13 = DecisionOverlay()


def heading_colours(decision_manager):
    surf = pygame.Surface((900, 700))
    surf.fill((0, 0, 0))
    overlay13.draw(surf, decision_manager)
    found = set()
    for x in range(900):
        for y in range(700):
            found.add(surf.get_at((x, y))[:3])
    return found


TURQ_HEADING = button_style.TEXT_NORMAL_BATTLE_FOCUS
VIOL_HEADING = button_style.TEXT_NORMAL_STRATAGEM
painted13 = heading_colours(offer_dm)
checks.true("the overlay paints the manoeuvre heading turquoise",
            TURQ_HEADING in painted13 or TURQUOISE in painted13)
checks.true("and no Stratagem violet appears on it",
            VIOL_HEADING not in painted13 and VIOLET not in painted13)

strat_dm13 = RealDecisionManager()
strat_dm13.request("Player 1", "Fire Overwatch (1 CP)", [("Use", None)], is_stratagem=True)
strat_painted13 = heading_colours(strat_dm13)
checks.true("a Stratagem overlay is unchanged - still violet",
            VIOL_HEADING in strat_painted13 or VIOLET in strat_painted13)
checks.true("and did not turn turquoise",
            TURQ_HEADING not in strat_painted13 and TURQUOISE not in strat_painted13)

plain_dm13 = RealDecisionManager()
plain_dm13.request("Player 1", "allocate the wound", [("Model A", None)])
plain_painted13 = heading_colours(plain_dm13)
checks.true("and a plain core decision keeps this overlay's own gold",
            (255, 215, 0) in plain_painted13)


# ------------------------------- 14. the buttons DURING a move in progress

print("--- 14. the manoeuvre buttons while the move is running ---")

# REPORTED: "battle focus +2 Movement wurde beim unteren guardian trupp nicht
# angeboten, obwohl ich noch tokens hatte. diese faehigkeit kann mehrmals
# angewendet werden pro phase."
#
# The rule was right and section 3 already pinned it. The PANEL was the bug:
# the manoeuvre block lived only in _draw_movement_ui()'s `else` arm, so the
# moment "Move" was pressed every button vanished, and after Confirm
# moved_squad_ids shut Swift as the Wind for good.
#
# Section 8 above renders with state == SELECTED and could not see it. This
# section renders with state == MOVING - the hole the report fell through.
# Own scene per check, because a fresh pool is needed (a spent one offers
# nothing and the section would pass by measuring nothing) and because
# clicking Confirm ends the move for every later click in the same render.

from game import movement as movement_mod  # noqa: E402
from game.turn import PHASE_CHARGE  # noqa: E402
from game.factions.aeldari import FALCON  # noqa: E402
from game.ui.action_panel import HINT_COLOR  # noqa: E402


_SC14 = [None]


def moving_scene(sheet=STRIKE_TEAM, give_battle_focus=True, engaged=False):
    st14 = GameState()
    tr14 = movement_tracker("Player 1")
    mv14 = MovementController(turn_tracker=tr14, all_tokens=st14.tokens,
                              player_name="Player 1", dice_manager=DiceManager())
    sq14 = build(sheet, "Player 1", name="Mid-move unit")
    # Trimmed: line_up() spaces models 1.4" apart, so a full 10-model squad
    # spans 12.6" and confirm_move() would refuse it on rule 09.02's 9" limit
    # - a refusal that has nothing to do with what this section measures.
    sq14.models = sq14.models[:5]
    if give_battle_focus:
        sq14 = aeldari(sq14)
    line_up(sq14, x=10.0, y=10.0)
    for model in sq14.models:
        st14.add_token(model)
    if engaged:
        # Rule 09.07: Fall Back is only available to an ENGAGED unit, so
        # without this start_fall_back_move() silently refuses, the state
        # stays SELECTED, and the `else` arm draws the buttons - i.e. the
        # check would pass while measuring the wrong arm entirely.
        foe = build(sheet, "Player 2", name="Foe")
        foe.models = foe.models[:2]
        line_up(foe, x=10.0, y=11.0)
        for model in foe.models:
            st14.add_token(model)
    mv14.select(sq14.models[0])
    p14 = pool(movement_controller=mv14, turn_tracker=tr14)
    p14.sync_battle_round(1)
    # Its OWN ShootingController. Section 8's is left mid-activation, which
    # sends _draw_dispatch to the shooting screen and past the movement UI
    # entirely - the section would then measure nothing and say so only here.
    sc14 = ShootingController(all_tokens=st14.tokens, dice_manager=DiceManager(),
                              turn_tracker=tr14, player_name="Player 1")
    _SC14[0] = sc14
    return st14, tr14, mv14, sq14, p14


class _FallBackStub:
    """Just enough for the panel's Fall Back arm to name its Confirm/Cancel.
    This section measures the manoeuvre buttons, not Fall Back itself."""

    state = None      # never CHOOSING_MODE, so _draw_dispatch keeps going

    def confirm(self):
        return None

    def cancel(self):
        return None

    def decline(self):
        return None


def render14(mover, p):
    surf = pygame.Surface((game_config.LEFT_PANEL_WIDTH, 900))
    surf.fill((0, 0, 0))
    panel.draw(surf, panel_rect, mover, _SC14[0], None, battle_focus_pool=p,
               fall_back_controller=_FallBackStub())
    return surf, list(panel._buttons)


def token_spenders(setup_move, sheet=STRIKE_TEAM, give_battle_focus=True, engaged=False):
    """How many of the drawn buttons spend a Battle Focus token. A fresh
    scene per button, so an earlier Confirm cannot poison a later click -
    identify by CLICKING, the way sections 8 and 13 do, so the check cannot
    drift away from the rule."""
    _st, _tr, mover, _sq, p = moving_scene(sheet, give_battle_focus, engaged)
    setup_move(mover, _sq)
    _surf, buttons = render14(mover, p)
    spenders = 0
    for index in range(len(buttons)):
        _st2, _tr2, mover2, sq2, p2 = moving_scene(sheet, give_battle_focus, engaged)
        setup_move(mover2, sq2)
        _surf2, buttons2 = render14(mover2, p2)
        if index >= len(buttons2):
            continue
        before = p2.tokens["Player 1"]
        buttons2[index][1]()
        if p2.tokens["Player 1"] < before:
            spenders += 1
    return spenders, buttons


def plain_move(mover, _squad):
    mover.start_move()


# 14.1 LIVENESS. A render that fell into another _draw_dispatch arm draws zero
# buttons and satisfies every absence check below, so prove we are really in
# the MOVING arm first - by finding the Confirm button, which only it draws.
_st, _tr, mover14, squad14, p14 = moving_scene()
mover14.start_move()
checks.eq("the scene really is mid-move", mover14.state, movement_mod.MOVING)
_surf14, buttons14 = render14(mover14, p14)
checks.true("buttons were drawn at all", bool(buttons14))
# Which ARM drew them, recorded by a spy: a render that fell into another
# _draw_dispatch branch draws zero buttons and satisfies every absence check
# below, so this has to be proven rather than assumed.
_arms = []
_orig_draw_am = ActionPanel._draw_agile_manoeuvres


def _spy_draw_am(self, surface, rect, button_width, button_y, squad, pool_, mover):
    _arms.append(getattr(mover, "state", None))
    return _orig_draw_am(self, surface, rect, button_width, button_y, squad, pool_, mover)


ActionPanel._draw_agile_manoeuvres = _spy_draw_am
render14(mover14, p14)
ActionPanel._draw_agile_manoeuvres = _orig_draw_am
checks.eq("...and the manoeuvre block really ran from the MOVING arm",
          _arms, [movement_mod.MOVING])

# 14.2 THE REPORTED CASE.
spent14, _b = token_spenders(plain_move)
checks.eq("two manoeuvres are offered to foot infantry mid-move "
          "(Swift as the Wind + Flitting Shadows)", spent14, 2)

# 14.3 STAR ENGINES at its printed trigger - the state its gate can ONLY be
# satisfied in, since advance_bonus_by_squad is written by start_run() and
# start_run() is reachable only from this arm.
def advance_move(mover, _squad):
    mover.start_move()
    mover.start_run()


script(6)
spent_vehicle, _b = token_spenders(advance_move, sheet=FALCON, give_battle_focus=False)
checks.eq("a VEHICLE that has Advanced is offered three, Star Engines included",
          spent_vehicle, 3)

# 14.4 FALL BACK is one of the three printed triggers.
def fall_back_move(mover, _squad):
    mover.start_fall_back_move("ordered_retreat")


_stfb, _trfb, moverfb, squadfb, pfb = moving_scene(engaged=True)
moverfb.start_fall_back_move("ordered_retreat")
checks.eq("the scene really is mid-Fall-Back", moverfb.move_mode, "fall_back")
checks.eq("...and in the MOVING arm", moverfb.state, movement_mod.MOVING)
checks.true("a unit mid-Fall-Back is still offered Swift as the Wind",
            pfb.can_swift_as_the_wind(squadfb))
spent_fb, _b = token_spenders(fall_back_move, engaged=True)
checks.true("and the panel really draws it there", spent_fb >= 1)

# 14.5 NEGATIVE: a charge move is NOT one of the printed triggers. Asked of
# the rule rather than rendered - the panel's charge arm needs a
# ChargeController for its own Confirm, and the phase check already refuses
# here anyway, which is exactly why 14.6 below has to exist as well.
_stc, trc, moverc, squadc, pc = moving_scene()
trc.phase_index = PHASES.index(PHASE_CHARGE)
moverc.start_charge_move(7, [squadc])
checks.eq("the scene really is mid-charge", moverc.move_mode, "charge")
checks.true("a charge move offers no manoeuvre", not pc.can_swift_as_the_wind(squadc))
checks.true("...nor Flitting Shadows", not pc.can_flitting_shadows(squadc))

# 14.6 NEGATIVE: a surge move is a MOVEMENT-phase mode that passes can_move(),
# so only the move-TYPE gate keeps it out. Without this check that gate could
# be deleted and 14.5 would still pass (the phase check covers charge).
_sts, _trs, movers, squads, ps = moving_scene()
movers.start_surge_move(squads, 6.0, (12.0, 12.0))
_surfs, buttonss = render14(movers, ps)
spent_surge = 0
for index in range(len(buttonss)):
    before = ps.tokens["Player 1"]
    buttonss[index][1]()
    if ps.tokens["Player 1"] < before:
        spent_surge += 1
checks.eq("a surge move offers no manoeuvre either", spent_surge, 0)

# 14.7 AFTER Confirm: the fix must not have WIDENED the rule.
_st7, _tr7, mover7, squad7, p7 = moving_scene()
mover7.start_move()
mover7.confirm_move()
checks.true("the unit is booked as having moved", squad7 in mover7.moved_squad_ids)
checks.true("Swift as the Wind is correctly gone", not p7.can_swift_as_the_wind(squad7))
checks.true("...but Flitting Shadows, whose window is the phase, is still there",
            p7.can_flitting_shadows(squad7))

# 14.8 THE USER'S SENTENCE, through the real panel: a SECOND unit, also
# mid-move, is still offered it after the first one spent a token.
st8b = GameState()
tr8b = movement_tracker("Player 1")
mv8b = MovementController(turn_tracker=tr8b, all_tokens=st8b.tokens,
                          player_name="Player 1", dice_manager=DiceManager())
unit_a = aeldari(build(STRIKE_TEAM, "Player 1", name="Unit A"))
unit_b = aeldari(build(STRIKE_TEAM, "Player 1", name="Unit B"))
line_up(unit_a, x=10.0, y=10.0)
line_up(unit_b, x=10.0, y=30.0)
for _sq in (unit_a, unit_b):
    for model in _sq.models:
        st8b.add_token(model)
p8b = pool(movement_controller=mv8b, turn_tracker=tr8b)
p8b.sync_battle_round(1)
mv8b.select(unit_a.models[0])
mv8b.start_move()
tokens_before = p8b.tokens["Player 1"]
p8b.use_swift_as_the_wind(unit_a)
checks.eq("unit A spent exactly one token", p8b.tokens["Player 1"], tokens_before - 1)
mv8b.select(unit_b.models[0])
mv8b.start_move()
checks.true("...and unit B, also mid-move, is STILL offered Swift as the Wind",
            p8b.can_swift_as_the_wind(unit_b))
_surf8b, buttons8b = render14(mv8b, p8b)
spent8b = 0
for index in range(len(buttons8b)):
    before = p8b.tokens["Player 1"]
    buttons8b[index][1]()
    if p8b.tokens["Player 1"] < before:
        spent8b += 1
    mv8b.select(unit_b.models[0])
checks.true("and the panel really draws it for unit B", spent8b >= 1)

# 14.9 THE TOP-UP IS REAL - the click has to DO something, not just draw.
_st9, _tr9, mover9, squad9, p9 = moving_scene()
mover9.start_move()
model9 = squad9.models[0]
before9 = mover9.remaining_range[model9.id]
p9.use_swift_as_the_wind(squad9)
checks.eq("the running move is topped up by 2 inches",
          round(mover9.remaining_range[model9.id] - before9, 3), 2.0)

# 14.10 THE HINT LINE, on pixels - plus the counter-check that keeps the panel
# from growing a Battle Focus line on every unit of every other army.
_st10, _tr10, mover10, squad10, p10 = moving_scene()
mover10.start_move()
p10.tokens["Player 1"] = 0
surf10, buttons10 = render14(mover10, p10)
painted10 = {surf10.get_at((x, y))[:3]
             for x in range(0, panel_rect.width, 2) for y in range(0, 900, 2)}
checks.true("with no tokens left, the panel SAYS so", HINT_COLOR in painted10)

_st10b, _tr10b, mover10b, squad10b, p10b = moving_scene(give_battle_focus=False)
mover10b.start_move()
surf10b, _b10b = render14(mover10b, p10b)
painted10b = {surf10b.get_at((x, y))[:3]
              for x in range(0, panel_rect.width, 2) for y in range(0, 900, 2)}
checks.true("...but a unit that never had the rule is told nothing",
            HINT_COLOR not in painted10b)

# The reason must not repeat the manoeuvre's name: the panel labels its own
# hint line, and the only logging caller prefixes the name too, so the old
# wording read "Flitting Shadows - Flitting Shadows has already been...".
# A SECOND unit asks after the first one spent it: Flitting Shadows is not in
# REPEATABLE_PER_PHASE, so the per-manoeuvre axis is what refuses here.
# (reset_phase() would clear both axes, so it cannot stage this.)
_st10c, _tr10c, mover10c, squad10c, p10c = moving_scene()
other10c = aeldari(build(STRIKE_TEAM, "Player 1", name="Other unit"))
other10c.models = other10c.models[:5]
line_up(other10c, x=10.0, y=30.0)
for _m in other10c.models:
    _st10c.add_token(_m)
mover10c.start_move()
p10c.use_flitting_shadows(squad10c)
_why10c = p10c.refusal_reason("Player 1", battle_focus.FLITTING_SHADOWS, other10c)
checks.true("the per-manoeuvre refusal really fired", bool(_why10c))
checks.true("...and does not repeat the manoeuvre's own name",
            battle_focus.FLITTING_SHADOWS not in (_why10c or ""))

# 14.11 the boolean and the reason cannot disagree.
_st11, _tr11, mover11, squad11, p11 = moving_scene()
for _setup in (lambda: None, lambda: mover11.start_move()):
    _setup()
    for _man, _can in ((battle_focus.SWIFT_AS_THE_WIND, p11.can_swift_as_the_wind),
                       (battle_focus.FLITTING_SHADOWS, p11.can_flitting_shadows),
                       (battle_focus.STAR_ENGINES, p11.can_star_engines)):
        ok, why = p11.why_not(_man, squad11)
        checks.eq("why_not agrees with can_%s" % _man, ok, _can(squad11))
        checks.true("a live button never carries a reason too", not (ok and why))


checks.finish()
