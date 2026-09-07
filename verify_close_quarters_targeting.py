"""Can an ENGAGED Monster/Vehicle really shoot out of the melee, in the REAL
main() loop?

User: "monster und fahrzeuge koennen aus dem nahkampf rausschiessen auf eine
andere einheit. im letzten spiel konnte ich das mit dem voiddragon nicht."

test_close_quarters_shooting.py drives the ShootingController directly, which
is the right level for a rule. It cannot show that the controller main()
actually builds behaves the same way, and this repo has hit "built but never
fed" six times - so this asks the LIVE controller from main()'s own frame, and
reads the answer off valid_target_models(), which is what the board highlight
and the target click both use.

WHY THE FACT IS STAGED. The reported situation needs a Monster locked in melee
during its owner's Shooting phase with a second enemy unit in range and in line
of sight. A MockAgent run reaches no such moment in a fixed frame budget (this
repo's documented harness limit), and a passive counter would report 0 and read
like a pass. So this reaches into main()'s frame, puts the human's C'tan Shard
of the Void Dragon into a real melee and stands a second enemy unit off at
8 inches with LINE OF SIGHT CHECKED INDEPENDENTLY (game/line_of_sight.py, not
the controller under test - otherwise the staging would be measuring the thing
it is meant to set up). Everything after that is the real thing.

Usage:  python verify_close_quarters_targeting.py [map2] [--neutralize]
        --neutralize restores the pre-fix world (under Close-Quarters shooting
        only the unit you are locked with is a legal target) and MUST report
        that the second unit cannot be shot.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import runpy

MAP = "map2"
NEUTRALIZE = "--neutralize" in sys.argv
for arg in sys.argv[1:]:
    if arg.startswith("map"):
        MAP = arg

from game import config                       # noqa: E402
from game import line_of_sight                # noqa: E402
from game import shooting as shooting_mod     # noqa: E402
from game.squad import ENGAGEMENT_RANGE_IN, edge_distance, is_monster_or_vehicle_unit  # noqa: E402
from game.weapons import RANGED               # noqa: E402

config.PLAYER1_ARMY = "necrons"        # the human fields the Void Dragon
config.PLAYER2_ARMY = "death_guard"    # the pairing from the reported game
config.ARMY_SELECT = False
config.MAP_SELECT = False
config.MAP = MAP

RESULTS = {}


def _human(locals_):
    ai = set(locals_["ai_players"])
    for player in sorted(locals_["armies"]):
        if player not in ai:
            return player
    return None


def _neutralize(controller):
    """The pre-fix world, restored on the live controller: under
    Close-Quarters shooting a target the unit is not engaged with was rejected
    outright, whoever was firing."""
    original = controller._is_valid_target_squad

    def gated(target_squad, all_tokens, attacking_squad=shooting_mod._UNSET,
              shooting_type=shooting_mod._UNSET):
        attacker = (controller.active_squad if attacking_squad is shooting_mod._UNSET
                    else attacking_squad)
        stype = (controller.shooting_type if shooting_type is shooting_mod._UNSET
                 else shooting_type)
        if (stype == shooting_mod.CLOSE_QUARTERS_SHOOTING and attacker is not None
                and target_squad is not None
                and not attacker.is_engaged_with(target_squad)):
            return False
        return original(target_squad, all_tokens, attacking_squad, shooting_type)

    controller._is_valid_target_squad = gated


def _move_squad_to(squad, x_in, y_in):
    for i, model in enumerate(squad.models):
        model.x_in, model.y_in = x_in + i * 1.4, y_in


def _stage(locals_, human):
    """Put the human's Monster into a melee with one enemy unit and stand a
    second enemy unit off at 8 inches with clear line of sight."""
    state = locals_["state"]
    mine = [s for s in state.all_squads()
            if s.owner == human and is_monster_or_vehicle_unit(s)
            and any(w.weapon_type == RANGED for m in s.models for w in m.weapons)
            and s.models and s.models[0].x_in is not None]
    foes = [s for s in state.all_squads()
            if s.owner != human and s.models and s.models[0].x_in is not None]
    if not mine or len(foes) < 2:
        return None
    monster = sorted(mine, key=lambda s: s.name)[0]
    near, far = sorted(foes, key=lambda s: s.name)[:2]

    mx, my = monster.models[0].x_in, monster.models[0].y_in
    r = monster.models[0].radius_in
    # Locked with `near`: base to base, comfortably inside Engagement Range.
    _move_squad_to(near, mx, my + r + near.models[0].radius_in + 1.0)
    # `far` at 8 inches of clearance, in the first direction with real line of
    # sight - checked here, not by the controller this script is measuring.
    obstacles = locals_["state"].obstacles
    placed = False
    for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0), (0.7, 0.7), (-0.7, 0.7)):
        d = r + far.models[0].radius_in + 8.0
        _move_squad_to(far, mx + dx * d, my + dy * d)
        if any(line_of_sight.has_line_of_sight(sm, fm, obstacles, state.tokens,
                                               state.terrain_areas)
               for sm in monster.models for fm in far.models):
            placed = True
            break
    if not placed:
        return None
    return monster, near, far


def inspect(locals_):
    human = _human(locals_)
    RESULTS["human"] = human
    sc = locals_["shooting_controller"]
    state = locals_["state"]

    staged = _stage(locals_, human)
    if staged is None:
        RESULTS["error"] = "could not stage a monster/vehicle melee on this board"
        return
    monster, near, far = staged
    RESULTS["monster"] = monster.name
    RESULTS["near"] = near.name
    RESULTS["far"] = far.name
    RESULTS["engaged_with_near"] = monster.is_engaged_with(near)
    RESULTS["far_clear"] = (
        min(edge_distance(a, b) for a in monster.models for b in far.models)
        > ENGAGEMENT_RANGE_IN and not far.is_engaged(state.tokens))

    locals_["turn_tracker"].turn_owner = human
    locals_["turn_tracker"].set_active(human)
    RESULTS["types"] = shooting_mod.available_shooting_types(
        monster, state.tokens, locals_["movement_controller"])

    if NEUTRALIZE:
        _neutralize(sc)

    sc.cancel()
    sc.start_shooting(monster)
    if sc.state == shooting_mod.CHOOSING_SHOOTING_TYPE:
        sc.choose_shooting_type(shooting_mod.CLOSE_QUARTERS_SHOOTING)
    RESULTS["shooting_type"] = sc.shooting_type
    RESULTS["can_target_near"] = sc._is_valid_target_squad(near, state.tokens)
    RESULTS["can_target_far"] = sc._is_valid_target_squad(far, state.tokens)
    offered = {t.squad.name for t in sc.valid_target_models(state.tokens) if t.squad}
    RESULTS["highlighted"] = sorted(offered)
    RESULTS["far_highlighted"] = far.name in offered

    # And the click that follows the highlight.
    sc.choose_target_squad(far)
    RESULTS["target_taken"] = sc.target_squad is far


def drive(frames=260, at=200):
    import pygame
    fired = []
    count = {"n": 0}
    real_flip = pygame.display.flip

    def flip(*args, **kwargs):
        count["n"] += 1
        if count["n"] == at and not fired:
            fired.append(True)
            frame = sys._getframe(1)
            while frame is not None and frame.f_code.co_name != "main":
                frame = frame.f_back
            if frame is None:
                raise SystemExit("could not reach main()'s frame")
            inspect(frame.f_locals)
        return real_flip(*args, **kwargs)

    pygame.display.flip = flip
    sys.argv = ["selfplay.py", MAP, str(frames)]
    try:
        runpy.run_module("selfplay", run_name="__main__")
    except SystemExit:
        pass
    finally:
        pygame.display.flip = real_flip
    return bool(fired)


if not drive():
    print("FAILED: never reached main()'s frame")
    raise SystemExit(1)

print("\n" + "=" * 74)
print("mode:", "NEUTRALIZED (pre-fix world)" if NEUTRALIZE else "fixed")
print("=" * 74)
if "error" in RESULTS:
    print("FAILED:", RESULTS["error"])
    raise SystemExit(1)

print("human player                  : %s" % RESULTS["human"])
print("monster/vehicle unit          : %s" % RESULTS["monster"])
print("locked in melee with          : %s (engaged=%s)"
      % (RESULTS["near"], RESULTS["engaged_with_near"]))
print("second enemy unit             : %s (clear of every melee=%s)"
      % (RESULTS["far"], RESULTS["far_clear"]))
print("shooting types offered        : %s" % RESULTS["types"])
print("activation type               : %s" % RESULTS["shooting_type"])
print("can target the unit it fights : %s" % RESULTS["can_target_near"])
print("CAN TARGET THE OTHER UNIT     : %s" % RESULTS["can_target_far"])
print("board highlight offers        : %s" % ", ".join(RESULTS["highlighted"]))
print("the target click takes        : %s" % RESULTS["target_taken"])

stage_ok = (RESULTS["engaged_with_near"] and RESULTS["far_clear"]
            and RESULTS["shooting_type"] == shooting_mod.CLOSE_QUARTERS_SHOOTING)
if not stage_ok:
    print("\nFAIL - the stage itself is wrong, nothing was measured")
    sys.exit(1)

if NEUTRALIZE:
    ok = (RESULTS["can_target_near"] and not RESULTS["can_target_far"]
          and not RESULTS["far_highlighted"])
    print("\n" + ("PASS - reproduced: only the unit it is locked with can be shot"
                  if ok else "FAIL - the pre-fix world was not restored"))
else:
    ok = (RESULTS["can_target_near"] and RESULTS["can_target_far"]
          and RESULTS["far_highlighted"] and RESULTS["target_taken"])
    print("\n" + ("PASS - it shoots out of the melee at the other unit"
                  if ok else "FAIL"))
sys.exit(0 if ok else 1)
