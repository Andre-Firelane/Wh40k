"""How far does the AI actually get, on a board that has an army on it?

MEASURES THE ORK ARMY, DELIBERATELY, AND NO LONGER THE DEFAULT ONE. This script
builds its own roster from game/factions/orks.py rather than reading
config.PLAYER2_ARMY, so it kept measuring the Orks when Player 2's default army
switched to the Necrons - and that is the intended behaviour, not an oversight
of the kind CLAUDE.md's error class 16 describes.

The reason is that this is a BASELINE, not a test: every number in CLAUDE.md's
movement-quality section (54% -> 64% achieved progress, 185" -> 206" of ground,
the "perfect ordering is worth ~3%" result, the rejected formation solver) was
measured here against this exact army on this exact terrain. Re-pointing it at a
different army would not update those numbers, it would make them
incomparable - and the whole value of the series is that a movement change can
be measured against what came before.

So: this says what the AI's movement is like, it does not say what the current
default army's movement is like. Those were the same statement until the armies
were switched; they are not any more. A Necron equivalent, if one is ever
wanted, belongs beside this as its own baseline rather than replacing it.

WHY THIS EXISTS, and why measure_movement_fixes.py is not enough: that harness
sets `state.tokens = list(sq.models)` - it measures a board with ONE unit
standing on it. Blockage by the AI's own units, the single biggest disruptor of
its movement, cannot occur there by construction. Measured A/B with identical
code, terrain and goals:

    median share of ACHIEVABLE progress    isolated 81%   crowded 54%

and the real game logs sit at 67%, between the two. Every "300/300 without
stalling" in CLAUDE.md was measured in the isolated world, which is why movement
fixes keep measuring green and the game keeps not working.

WHERE THE CROWDED LOSS COMES FROM, measured by running the same units against
the same goals in four worlds:

    alone on the board          76%
    + the whole ENEMY army      77%   (costs nothing)
    + its OWN army              54%
    + both                      62%

So the enemy is not the problem and never was - the AI's units get in each
other's way. Two follow-ups worth not repeating: reordering them barely helps
(an oracle over 15 random orders beat the AI's own heuristic by ~3% of total
ground), and per-unit search has little headroom left either (76% alone).

THREE WAYS THIS FIXTURE WAS WRONG BEFORE, all of which flattered or maligned a
change that was then acted on - the same failure this file exists to prevent,
one level up:

  * ONE SHARED GOAL for every unit. Fourteen units ordered to the same
    coordinate pile up on it by construction, so most of the "crowding" was
    self-inflicted. Each unit now gets its own goal, as a turn plan gives it.
  * NO Take to the Skies. The real path (_handle_movement) declares it
    whenever game.movement.take_to_the_skies_pays() says so, and a flying
    model ignores terrain and models in transit. Without it the two worst
    units in the whole report were the two that fly.
  * NO bulk-fallback rule. A VEHICLE-only squad gets no rigid fallback in the
    real path; the harness gave it one.

MEDIAN OR TOTAL? Both are printed, and they answer different questions. The
median is per-move quality; the TOTAL ground gained is the army's actual
achievement, and when an effect is concentrated in one unit and displaces its
neighbours the two disagree sharply. Lifting the 9" spread limit for the AI
moved the median 62% -> 54% and the total 187.5" -> 185.2", i.e. the median
alone would have condemned a change that is really neutral overall and worth
+33 points to the unit it was aimed at.

WHAT IS SCORED, and why it is not distance travelled: a unit can burn 86% of its
movement and still put only 64% of it toward where it was ordered to go - which
is exactly the reported symptom ("bewegungen nach vorne geplant, aber die
einheit bewegt sich kaum oder nur seitlich"). So the headline number is

    got = progress toward the commanded point / min(gap to it, the unit's M)

the share of what this unit could HONESTLY have achieved this turn, which
separates "did not arrive" from "could never have arrived".

Also reported, because the AI is meant to keep its units packed (small
footprints hide better and leave room for the neighbours): final spread per
unit, and how many units end fully out of the enemy's line of sight.

Run:  python measure_crowded_movement.py [map_key] [--turns=N]
"""

import math
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ai import agent_driver
from game import attached_units, config, line_of_sight, maps, squad as squad_module
from game.factions import build_squad
from game.factions.orks import (
    BATTLEWAGON, BATTLEWAGON_ADD_BIG_SHOOTAS, BATTLEWAGON_ADD_ZZAP_GUN,
    BEAST_SNAGGA_BOYZ, BEASTBOSS, BOYZ, BOYZ_BIG_CHOPPA_TO_POWER_KLAW,
    DEFF_DREAD, DEFFKOPTAS, FLASH_GITZ, GRETCHIN, KILL_RIG, MEGANOBZ, PAINBOY,
    STORMBOYZ, STORMBOYZ_CHOPPA_TO_POWER_KLAW, TANKBUSTAS, WARBIKERS,
    WARBIKERS_ADD_POWER_KLAW, WARBOSS, WARBOSS_ADD_ATTACK_SQUIG,
    WARBOSS_MEGA_ARMOUR,
)
from game.factions.tau_empire import (
    GHOSTKEEL_BATTLESUIT, KROOT_CARNIVORES, PATHFINDER_TEAM, RIPTIDE_BATTLESUIT,
    STRIKE_TEAM,
)
from game.game_state import GameState
from game.movement import MovementController, take_to_the_skies_pays
from game.squad import edge_distance, min_model_movement
from game.turn import PHASE_MOVEMENT, PHASES, TurnTracker

STALL_IN = 0.5
DEFAULT_TURNS = 3
# Size buckets the game logs are broken down by - the failure is very much a
# function of unit size (measured in the logs: 8-14 models 77%, vehicles 72%,
# 2-7 models 50%, 15+ models 20%), so an overall median alone hides where it
# actually lives.
BUCKETS = ((1, 1, "single-model"), (2, 7, "2-7 models"),
           (8, 14, "8-14 models"), (15, 99, "15+ models"))


def movers(state):
    """Player 2's REAL roster, as main() builds it - including the 22-model
    Boyz mob and the 7-model Meganobz, which are the two worst cases in the
    logs and which measure_movement_fixes.py's own fixture predates."""
    out = []

    def add(label, squad):
        out.append((label, squad))
        return squad

    add("Kill Rig", build_squad(KILL_RIG, owner="Player 2", name="Kill Rig"))
    add("Beast Snagga + Beastboss", attached_units.attach(
        build_squad(BEASTBOSS, owner="Player 2", name="Beastboss"),
        build_squad(BEAST_SNAGGA_BOYZ, owner="Player 2", name="Beast Snagga Boyz"),
        game_state=state))
    add("Battlewagon", build_squad(
        BATTLEWAGON, owner="Player 2", name="Battlewagon",
        choices={"Battlewagon": {BATTLEWAGON_ADD_BIG_SHOOTAS: 1,
                                 BATTLEWAGON_ADD_ZZAP_GUN: 1}}))
    add("Meganobz + Warboss", attached_units.attach(
        build_squad(WARBOSS_MEGA_ARMOUR, owner="Player 2", name="Warboss in Mega Armour"),
        build_squad(MEGANOBZ, owner="Player 2", composition_index=1, name="Meganobz"),
        game_state=state))

    mob = build_squad(BOYZ, owner="Player 2", composition_index=1,
                      choices={"Boss Nob": {BOYZ_BIG_CHOPPA_TO_POWER_KLAW: 1}},
                      name="Boyz")
    mob = attached_units.attach(build_squad(
        WARBOSS, owner="Player 2", name="Warboss",
        choices={"Warboss": {WARBOSS_ADD_ATTACK_SQUIG: 1}}), mob, game_state=state)
    mob = attached_units.attach(build_squad(PAINBOY, owner="Player 2", name="Painboy"),
                                mob, game_state=state)
    add("Boyz 20 + Warboss + Painboy", mob)

    for index in (1, 2):
        add(f"Gretchin {index}", build_squad(
            GRETCHIN, owner="Player 2", name=f"Gretchin {index}", unit_index=index))
        add(f"Warbikers {index}", build_squad(
            WARBIKERS, owner="Player 2", composition_index=0,
            choices={"Boss Nob on Warbike": {WARBIKERS_ADD_POWER_KLAW: 1}},
            name=f"Warbikers {index}", unit_index=index))
    add("Stormboyz", build_squad(
        STORMBOYZ, owner="Player 2", composition_index=1,
        choices={"Boss Nob": {STORMBOYZ_CHOPPA_TO_POWER_KLAW: 1}}, name="Stormboyz"))
    add("Deff Dread", build_squad(DEFF_DREAD, owner="Player 2", name="Deff Dread"))
    add("Deffkoptas", build_squad(
        DEFFKOPTAS, owner="Player 2", composition_index=1, name="Deffkoptas"))
    add("Flash Gitz", build_squad(
        FLASH_GITZ, owner="Player 2", composition_index=1, name="Flash Gitz"))
    add("Tankbustas", build_squad(TANKBUSTAS, owner="Player 2", name="Tankbustas"))
    return out


def defenders():
    """A static Player 1 presence. Never moved - it exists so that enemy models
    block movement (rule 03.01), Engagement Range is real, and there is
    something for the line-of-sight measurement to be seen BY."""
    return [
        build_squad(STRIKE_TEAM, owner="Player 1", name="Strike Team 1", unit_index=1),
        build_squad(STRIKE_TEAM, owner="Player 1", name="Strike Team 2", unit_index=2),
        build_squad(KROOT_CARNIVORES, owner="Player 1", name="Kroot Carnivores 1"),
        build_squad(PATHFINDER_TEAM, owner="Player 1", name="Pathfinder Team 1"),
        build_squad(RIPTIDE_BATTLESUIT, owner="Player 1", name="Riptide Battlesuit 1"),
        build_squad(GHOSTKEEL_BATTLESUIT, owner="Player 1", name="Ghostkeel Battlesuit 1"),
    ]


def block(squad, x_in, y_in, pitch=1.6, per_row=5):
    for index, model in enumerate(squad.models):
        model.x_in = x_in + (index % per_row) * pitch
        model.y_in = y_in + (index // per_row) * pitch


def _fits(state, squad, settled):
    if any(squad_module.model_terrain_violation(m, state.obstacles) for m in squad.models):
        return False
    if squad.check_coherency():
        return False
    for model in squad.models:
        if not (model.radius_in <= model.x_in <= config.BOARD_WIDTH_IN - model.radius_in
                and model.radius_in <= model.y_in <= config.BOARD_HEIGHT_IN - model.radius_in):
            return False
    return not any(
        math.dist((m.x_in, m.y_in), (px, py)) < m.radius_in + pr + 0.2
        for m in squad.models for (px, py, pr) in settled
    )


def lay_out(state, squads, band, settled):
    """Put each squad down on legal ground inside a horizontal band, none
    overlapping anything already settled. Returns those that found room."""
    low, high = band
    placed = []
    for label, squad in squads:
        found = False
        for step in range(600):
            x = 4.0 + (step % 18) * 3.0
            y = low + (step // 18) * 2.5
            if y > high:
                break
            block(squad, x, y)
            if _fits(state, squad, settled):
                found = True
                break
        if not found:
            continue
        settled.extend((m.x_in, m.y_in, m.radius_in) for m in squad.models)
        placed.append((label, squad))
    return placed


def spread_of(squad):
    if len(squad.models) < 2:
        return 0.0
    return max(edge_distance(a, b)
               for i, a in enumerate(squad.models) for b in squad.models[i + 1:])


def out_of_sight(squad, enemy_models, state):
    """True if no enemy model can see any model of this squad. The real
    line-of-sight check, not the cheap probe the AI optimises against - a
    metric scored with the AI's own approximation would only prove that the AI
    agrees with itself."""
    for model in squad.models:
        for enemy in enemy_models:
            if line_of_sight.has_line_of_sight(enemy, model, state.obstacles,
                                               state.tokens, state.terrain_areas):
                return False
    return True


def assign_goals(placed, board_w, board_h):
    """One goal point per unit, spread across the far side of the board.

    Emphatically NOT one shared goal, which is what this harness did first and
    which quietly invalidated everything measured with it: fourteen units all
    ordered to the same coordinate pile up on it by construction, so the
    "crowding" being measured was mostly self-inflicted by the fixture. It also
    misrepresents the game - a turn plan gives each unit its own destination
    (game/planner_prompt.py), and units that share one are the exception the
    over-garrison check exists to correct.

    Measured on the shared-goal version: reordering the units barely moved the
    result (best of 25 random orders beat the AI's own heuristic by 4%), which
    is the signature of a fixture where the destinations, not the sequence, are
    what collide."""
    goals = {}
    span = board_w - 8.0
    for index, (label, _squad) in enumerate(sorted(placed, key=lambda e: e[0])):
        share = (index + 0.5) / max(1, len(placed))
        goals[label] = (4.0 + span * share, board_h * 0.80)
    return goals


def move_once(state, squad, goal):
    """One Normal Move, driven exactly as _handle_movement() drives it.

    The `flying` half is not optional detail. Rule 21.03 (Take to the Skies) is
    a deterministic policy in the real path - and it changes the move
    completely, since a flying model ignores terrain and other models in
    transit. A harness that leaves it out measures every FLY unit as if it were
    walking: before this was mirrored, the two worst units in the whole report
    were the Stormboyz (16%) and the Deffkoptas (25%), and both of them fly.
    The Stormboyz half of that is now history rather than current behaviour -
    they are all-INFANTRY, so take_to_the_skies_pays() rules them out (13.06
    already crosses walls for them). Measured A/B when that rule went in:
    crowded median got 60% -> 65%, total ground 202.1" -> 209.1".

    WHICH squads declare it is read from take_to_the_skies_pays() rather than
    spelled out again here. It used to be a local copy of the real path's
    `any(m.profile.fly ...)`, which is exactly how this fixture drifted from
    the code it measures three times before (see the header)."""
    tracker = TurnTracker(first_player="Player 2")
    tracker.phase_index = PHASES.index(PHASE_MOVEMENT)
    controller = MovementController(
        obstacles=state.obstacles, player_name="Player 2", turn_tracker=tracker,
        all_tokens=state.tokens, board_width_in=config.BOARD_WIDTH_IN,
        board_height_in=config.BOARD_HEIGHT_IN,
    )
    use_fly = take_to_the_skies_pays(squad)
    # VEHICLE-only squads get no bulk translation in the real path either.
    allow_bulk = not all(m.profile.vehicle for m in squad.models)

    def start_fn():
        controller.start_move()
        if use_fly:
            controller.take_to_the_skies()

    before = agent_driver._centroid(squad)
    controller.select(squad.models[0])
    agent_driver._advance_toward(controller, squad, goal, start_move_fn=start_fn,
                                 allow_bulk_fallback=allow_bulk, flying=use_fly)
    return before, agent_driver._centroid(squad)


def score(before, after, goal, budget):
    travelled = math.dist(before, after)
    gap = math.dist(before, goal)
    progress = gap - math.dist(after, goal)
    want = min(gap, budget)
    if gap > 1e-9:
        ux, uy = (goal[0] - before[0]) / gap, (goal[1] - before[1]) / gap
        dx, dy = after[0] - before[0], after[1] - before[1]
        lateral = abs(-uy * dx + ux * dy)
    else:
        lateral = 0.0
    return dict(travelled=travelled, progress=progress, lateral=lateral,
                used=travelled / budget if budget else 0.0,
                got=progress / want if want > 1e-9 else 1.0)


def run(state, placed, home, enemy_models, goals, turns, crowded):
    """One world. `crowded` False reproduces measure_movement_fixes.py's own
    setup - only the moving unit exists - so the difference between the two is
    itself a reported number rather than something to be rediscovered."""
    for label, squad in placed:
        for model, (x, y) in zip(squad.models, home[label]):
            model.x_in, model.y_in = x, y
    everyone = list(state.tokens)

    rows, stalls = [], 0
    for _turn in range(turns):
        order = sorted(placed, key=lambda entry: agent_driver._movement_priority_key(
            entry[1], state.tokens, None))
        for label, squad in order:
            state.tokens = everyone if crowded else list(squad.models)
            budget = min_model_movement(squad) or 6.0
            goal = goals[label]
            before, after = move_once(state, squad, goal)
            row = score(before, after, goal, budget)
            row.update(label=label, models=len(squad.models))
            rows.append(row)
            if row["travelled"] < STALL_IN:
                stalls += 1
    state.tokens = everyone

    spreads = [(spread_of(sq), label) for label, sq in placed if len(sq.models) > 1]
    hidden = sum(1 for _l, sq in placed if out_of_sight(sq, enemy_models, state))
    broken = sum(1 for _l, sq in placed if sq.check_coherency())
    return dict(rows=rows, stalls=stalls, spreads=spreads, hidden=hidden,
                units=len(placed), broken=broken)


def median(values):
    return sorted(values)[len(values) // 2] if values else 0.0


def summarise(name, result):
    rows = result["rows"]
    total = len(rows)
    share = lambda test: 100.0 * sum(1 for r in rows if test(r)) / total
    # Total ground is the army's actual achievement and the median is per-move
    # quality; they disagree whenever an effect is concentrated in one unit and
    # displaces its neighbours, so both are printed. See the module docstring
    # for the change that the median alone would have condemned.
    print(f"  {name:9s} n={total:4d}  stalled {result['stalls']:3d}  "
          f"med used {100 * median([r['used'] for r in rows]):3.0f}%  "
          f"med got {100 * median([r['got'] for r in rows]):3.0f}%  "
          f"total {sum(max(r['progress'], 0.0) for r in rows):6.1f}\"  "
          f"<60% {share(lambda r: r['got'] < 0.60):5.1f}%  "
          f"<35% {share(lambda r: r['got'] < 0.35):5.1f}%  "
          f"sideways {share(lambda r: r['lateral'] > max(r['progress'], 0.0)):5.1f}%")
    return median([r["got"] for r in rows])


def detail(result):
    rows = result["rows"]
    print("    by unit size:")
    for low, high, label in BUCKETS:
        group = [r for r in rows if low <= r["models"] <= high]
        if not group:
            continue
        print(f"      {label:14s} n={len(group):4d}  "
              f"med used {100 * median([r['used'] for r in group]):3.0f}%  "
              f"med got {100 * median([r['got'] for r in group]):3.0f}%")
    per_unit = {}
    for row in rows:
        per_unit.setdefault(row["label"], []).append(row["got"])
    print("    worst units (median got):")
    for label, got in sorted(per_unit.items(), key=lambda kv: median(kv[1]))[:5]:
        print(f"      {label:30s} {100 * median(got):3.0f}%")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    map_key = args[0] if args else "map2"
    turns = DEFAULT_TURNS
    for flag in flags:
        if flag.startswith("--turns="):
            turns = int(flag.split("=", 1)[1])

    battle_map = maps.apply_to_config(maps.get(map_key))
    state = GameState()
    battle_map.build(state)
    settled = []
    placed = lay_out(state, movers(state), (4.0, config.BOARD_HEIGHT_IN * 0.30), settled)
    enemy = [(sq.name, sq) for sq in defenders()]
    enemy_placed = lay_out(state, enemy,
                           (config.BOARD_HEIGHT_IN * 0.62, config.BOARD_HEIGHT_IN * 0.88),
                           settled)
    enemy_models = [m for _l, sq in enemy_placed for m in sq.models]
    state.tokens = [m for _l, sq in placed for m in sq.models] + enemy_models
    home = {label: [(m.x_in, m.y_in) for m in sq.models] for label, sq in placed}
    goals = assign_goals(placed, config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN)

    # Say how many were left out, rather than dropping them silently: on a
    # small board the roster does not fit, and a quietly shorter run reads as
    # "this map is fine" when it is really "this map was measured with half the
    # traffic".
    offered = len(movers(GameState())) + len(defenders())
    print(f"=== {map_key}: {len(placed)} moving units, {len(enemy_placed)} static enemy "
          f"units, {len(state.tokens)} tokens, {turns} turns ===")
    if len(placed) + len(enemy_placed) < offered:
        print(f"    NOTE: {offered - len(placed) - len(enemy_placed)} of {offered} units found "
              f"no legal room on this board and were left out")
    print('    one goal per unit, spread along the far edge; '
          '"got" = share of min(gap, M) actually closed')
    print()

    crowded = run(state, placed, home, enemy_models, goals, turns, crowded=True)
    isolated = run(state, placed, home, enemy_models, goals, turns, crowded=False)
    crowded_med = summarise("CROWDED", crowded)
    isolated_med = summarise("ISOLATED", isolated)

    print()
    detail(crowded)
    print()
    print(f"    median achievable progress: ISOLATED {100 * isolated_med:.0f}%"
          f"  ->  CROWDED {100 * crowded_med:.0f}%"
          f"   (the cost of having an army on the board)")
    spreads = crowded["spreads"]
    widest, widest_label = max(spreads) if spreads else (0.0, "-")
    print(f"    footprint after {turns} turns: median spread "
          f"{median([s for s, _l in spreads]):.2f}\", "
          f"widest {widest:.2f}\" ({widest_label})")
    loose = sorted(spreads, reverse=True)[:3]
    print("      loosest: " + ", ".join(f"{label} {s:.2f}\"" for s, label in loose))
    print(f"    fully out of enemy line of sight: "
          f"{crowded['hidden']}/{crowded['units']} units")
    print(f"    out of coherency at the end: {crowded['broken']}/{crowded['units']} units")
    return 0


if __name__ == "__main__":
    sys.exit(main())
