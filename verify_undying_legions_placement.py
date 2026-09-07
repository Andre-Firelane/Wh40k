"""Do the OTHER two doors into reanimate() let a human place their models?

User: "Einheiten wurde automatisch platziert bei protocol of the undying
legion, obwohl ich necrons spiele. da scheint sich noch eine automatismus zu
verstecken, der nur bei KI greifen soll."

verify_return_placement.py already proves the ARMY RULE's own door. It cannot
see this one: `reanimation_protocols.reanimate()` has three callers, and the
other two - Protocol of the Undying Legions and the Resurrection Orb - were
never handed a ReturnPlacementController, so they seated a human's models
themselves. This is the `verify_sudden_storm_wiring.py` pattern for those two:
a source guard shows the wiring is WRITTEN DOWN, this drives the REAL main()
loop and asks the controllers main() actually built.

WHY THE FACT IS STAGED. Both doors are reactive and rare - Undying Legions
fires "just after an enemy unit resolved its attacks" against a unit that lost
models, and a MockAgent run reliably reaches no such moment in a fixed frame
budget (this repo's documented harness limit). A passive counter would report 0
and read like a pass. So this reaches into main()'s own frame, takes the LIVE
controllers, kills two models of a real HUMAN Necron unit, and fires each door
by hand. Everything after that - the placer, the SetupController, the fork on
auto_players - is the real thing.

Usage:  python verify_undying_legions_placement.py [map2] [--neutralize]
        --neutralize restores the pre-fix world (neither door gets a placer)
        and MUST report that the models were seated automatically.
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

from game import config                              # noqa: E402
from game import setup as setup_mod                  # noqa: E402

config.PLAYER1_ARMY = "necrons"      # the human plays Necrons - the report
config.PLAYER2_ARMY = "necrons"
config.ARMY_SELECT = False
config.MAP_SELECT = False
config.MAP = MAP

RESULTS = {}


def _human(locals_):
    """The human player, from main()'s own live view."""
    ai = set(locals_["ai_players"])
    for player in sorted(locals_["armies"]):
        if player not in ai:
            return player
    return None


def _pick_unit(locals_, human):
    """A standing Necron unit of the human with room to recover."""
    state = locals_["state"]
    seen = []
    for squad in sorted(state.all_squads(), key=lambda s: s.name):
        if squad.owner != human:
            continue
        living = [m for m in squad.models if not m.is_dead()]
        if len(living) >= 5 and any(m.x_in is not None for m in living):
            seen.append(squad)
    return seen[0] if seen else None


def _kill(squad, n):
    for model in list(squad.models)[:n]:
        model.current_wounds = 0
        squad.models.remove(model)
        squad.destroyed_models.append(model)


def inspect(locals_):
    human = _human(locals_)
    placer = locals_["return_placement_controller"]
    setup = locals_["setup_controller"]
    ul = locals_["undying_legions_controller"]
    orb = locals_["resurrection_orb_controller"]

    if NEUTRALIZE:
        # The pre-fix world: neither door holds a placer, so reanimate() falls
        # back to seating the models itself - for everyone.
        ul.placer = None
        orb.placer = None

    RESULTS["human"] = human
    RESULTS["ul_has_placer"] = ul.placer is placer
    RESULTS["orb_has_placer"] = orb.placer is placer

    squad = _pick_unit(locals_, human)
    if squad is None:
        RESULTS["error"] = "no human Necron unit on the board to damage"
        return
    RESULTS["unit"] = squad.name

    # Fire Undying Legions on the real controller. The Stratagem's own gates
    # (detachment, "lost models", CP) are left alone; only the dice are driven,
    # because a die is not what this is measuring.
    config.AWAKENED_DYNASTY_PLAYERS = tuple(
        set(getattr(config, "AWAKENED_DYNASTY_PLAYERS", ())) | {human})
    _kill(squad, 2)
    before = len(squad.models)
    RESULTS["can_use"] = ul.can_use(squad)
    if ul.can_use(squad):
        ul.use(squad)
        dice = locals_["dice_manager"]
        if dice.pending_values is not None:
            dice.acknowledge()
        ul.on_dice_acknowledged()
    RESULTS["ul_returned"] = len(squad.models) - before
    RESULTS["ul_opened"] = setup.state == setup_mod.PLACING
    RESULTS["ul_placing"] = (len(setup.placing_models or [])
                             if setup.state == setup_mod.PLACING else 0)
    RESULTS["ul_total"] = len(squad.models)
    if placer.is_busy:
        placer.cancel()


def drive(frames=400, at=320):
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

print(f"human player                    : {RESULTS['human']}")
print(f"Undying Legions holds the placer: {RESULTS['ul_has_placer']}")
print(f"Resurrection Orb holds it       : {RESULTS['orb_has_placer']}")
print(f"unit                            : {RESULTS['unit']}")
print(f"Stratagem usable                : {RESULTS['can_use']}")
print(f"models returned                 : {RESULTS['ul_returned']}")
print(f"placement opened for the human  : {RESULTS['ul_opened']}"
      f"  (placing {RESULTS['ul_placing']} of {RESULTS['ul_total']})")

ok = (RESULTS["ul_returned"] > 0
      and RESULTS["ul_opened"]
      and 0 < RESULTS["ul_placing"] < RESULTS["ul_total"]
      and RESULTS["ul_has_placer"] and RESULTS["orb_has_placer"])
if NEUTRALIZE:
    ok = (RESULTS["ul_returned"] > 0 and not RESULTS["ul_opened"])
    print("\n" + ("PASS - reproduced: the models were seated automatically"
                  if ok else "FAIL - the pre-fix world was not restored"))
else:
    print("\n" + ("PASS - the human places their own returning models"
                  if ok else "FAIL"))
sys.exit(0 if ok else 1)
