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

checks.finish()
