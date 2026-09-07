"""Runtime proof, on the objects main() really built, that every ability hung
on "an attacking unit has finished its attacks" is actually reached.

THE BUG THIS EXISTS FOR (not reported - found while tracing another one)
------------------------------------------------------------------------
fight_controller.on_unit_finished_fighting is a single SLOT. main.py set it to
a chained handler covering seven abilities and then, ~120 lines later, assigned
it AGAIN for rule 15.12's Counteroffensive - silently throwing all seven away:

    Undying Legions, Curse of the Walking Pox, Lethal Ichor, Undying Spite,
    To Their Final Breaths, Malevolent Souls, Vaul's Vengeance

Every one has a green suite, because those drive the controllers directly. Only
the source can see a slot being written twice, and only a runtime probe can
show what the LIVE object does with it.

WHAT IS STAGED: the call itself. A MockAgent run does not reliably reach a melee
activation inside a sane frame budget (the documented harness limit), so the
probe fires main()'s own callback with a real squad from the live board. What it
measures - which controllers that one call reaches - is entirely real.

Usage:  python verify_fight_finished_chain.py [map2 [frames]]
        python verify_fight_finished_chain.py map2 --neutralize   # 1 of 8
"""

import runpy
import sys

from game import config

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

MAP = "map2"
FRAMES = 400
_rest = list(sys.argv[1:])
if _rest:
    MAP = _rest[0]
if len(_rest) > 1:
    FRAMES = int(_rest[1])

config.PLAYER1_ARMY = "death_guard"
config.PLAYER2_ARMY = "necrons"

# (main.py local, method it must reach) - the seven that were being thrown
# away, plus Counteroffensive, the one assignment that was doing the throwing.
WATCHED = [
    ("undying_legions_controller", "maybe_offer"),
    ("curse_of_the_walking_pox_controller", "resolve_after_attacks"),
    ("lethal_ichor_controller", "on_unit_finished_fighting"),
    ("undying_spite_controller", "resolve_after_attacks"),
    ("to_their_final_breath_controller", "resolve_after_attacks"),
    ("malevolent_souls_controller", "resolve_after_attacks"),
    ("vauls_vengeance_controller", "on_attacker_finished"),
    ("counteroffensive_controller", "offer_after"),
]

RESULTS = {}


def inspect(loc):
    fight = loc["fight_controller"]
    hook = fight.on_unit_finished_fighting
    if NEUTRALIZE:
        # THE FAITHFUL PRE-FIX WORLD: the LAST assignment won outright, so the
        # slot held nothing but the Counteroffensive lambda.
        hook = (lambda squad: loc["counteroffensive_controller"].offer_after(
            squad, loc["decision_manager"]))

    reached = set()
    for name, method in WATCHED:
        ctrl = loc.get(name)
        if ctrl is None:
            continue
        real = getattr(ctrl, method)

        def spy(*a, _n=name, _r=real, **k):
            reached.add(_n)
            try:
                return _r(*a, **k)
            except Exception:
                # A spy must report REACH, not survive the ability's own
                # preconditions on a board it was not staged for.
                return None

        setattr(ctrl, method, spy)

    squad = next((t.squad for t in loc["state"].tokens
                  if getattr(t, "squad", None) is not None), None)
    RESULTS["squad"] = getattr(squad, "name", None)
    try:
        hook(squad)
    except Exception as exc:                     # noqa: BLE001
        RESULTS["raised"] = "%s: %s" % (type(exc).__name__, exc)
    RESULTS["reached"] = sorted(reached)
    RESULTS["missed"] = sorted(n for n, _ in WATCHED
                               if loc.get(n) is not None and n not in reached)


def drive():
    import pygame
    fired = []
    count = {"n": 0}
    real_flip = pygame.display.flip

    def flip(*args, **kwargs):
        count["n"] += 1
        if count["n"] == FRAMES and not fired:
            fired.append(True)
            frame = sys._getframe(1)
            while frame is not None and frame.f_code.co_name != "main":
                frame = frame.f_back
            if frame is None:
                raise SystemExit("could not reach main()'s frame")
            inspect(frame.f_locals)
        return real_flip(*args, **kwargs)

    pygame.display.flip = flip
    sys.argv = ["selfplay.py", MAP, str(FRAMES + 40)]
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

print()
print("--- on_unit_finished_fighting" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
print("  fired with          %s" % RESULTS.get("squad"))
print("  reached %d of %d:" % (len(RESULTS.get("reached", ())), len(WATCHED)))
for name in RESULTS.get("reached", ()):
    print("      %s" % name)
if RESULTS.get("missed"):
    print("  NOT reached:")
    for name in RESULTS["missed"]:
        print("      %s" % name)
if RESULTS.get("raised"):
    print("  raised: %s" % RESULTS["raised"])
