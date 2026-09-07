"""Does a save taken by the REAL game come back as the same battle?

The suites drive scene_io and the controllers directly. This drives main()'s
own loop through selfplay.py, lets a battle actually happen, presses SAVE the
way the menu's Save Game entry does, and then LOADS that file into a second
main() - which is the whole path a player uses and the one that was reported
broken:

    "schaden auf einheiten wurde nicht gespeichert"
    "es wurde nicht gespeichert, wer schon welche aktion ausgefuehrt hat"

Both halves are STAGED rather than waited for, and the reason is the harness
limit CLAUDE.md already records: a MockAgent run rarely reaches a Shooting
phase, and never reliably in a fixed frame budget. A passive counter would
therefore report a clean zero and look exactly like a pass. So this damages a
unit and marks it as having acted through the ENGINE'S OWN objects on a live
board, and everything after that - the capture, the file, the rebuild, the
restore - is real.

    python verify_save_load.py [map] [--neutralize]

--neutralize restores the pre-fix world (no per-model identity, no activation
section) and must report the reported failure instead.
"""

import os
import runpy
import sys

sys.argv = [a for a in sys.argv]
NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")
MAP = sys.argv[1] if len(sys.argv) > 1 else "map2"

import main  # noqa: E402
from game import config, scene_io  # noqa: E402

SAVE = os.path.join(scene_io.SCENES_DIR, "verify_save_load.json")

if NEUTRALIZE:
    # The world the report came from, both halves at once: models carry no
    # identity in the file, and nothing writes an activation section.
    _real_capture = scene_io.capture

    def capture(*args, **kwargs):
        kwargs.pop("activation", None)
        data = _real_capture(*args, **kwargs)
        data.pop("activation", None)
        for entry in data["squads"]:
            for model in entry["models"]:
                model.pop("model", None)
                model.pop("weapons", None)
        return data

    scene_io.capture = capture

# ------------------------------------------------------------------ pass 1
SNAPSHOT = {}


def _stage_and_save(locals_):
    """Put a real mid-turn state on a live board, then press Save."""
    state = locals_["state"]
    squads = [e["squad"] for e in locals_["scene_units"]]
    on_board = [s for s in squads if s.models and s.models[0] in state.tokens]

    # A unit with a character at the tail - the shape the report is about.
    led = next((s for s in on_board
                if len(s.models) > 2
                and s.models[-1].profile.wounds > s.models[0].profile.wounds),
               None)
    if led is None:
        led = max(on_board, key=lambda s: len(s.models))
    # Kill everything but the character, and hurt the character - exactly the
    # "1 Skorpekh Destroyers 1 + Skorpekh Lord -> one model on 5 wounds" line
    # out of the user's own save file.
    survivor = led.models[-1]
    for model in list(led.models[:-1]):
        led.models.remove(model)
        if model in state.tokens:
            state.tokens.remove(model)
        model.current_wounds = 0
        led.destroyed_models.append(model)
    survivor.current_wounds = max(1, survivor.profile.wounds - 2)

    # ...and a second unit that has already acted this turn.
    actor = next(s for s in on_board if s is not led)
    locals_["shooting_controller"].shot_squad_ids.add(actor)
    locals_["movement_controller"].moved_squad_ids.add(actor)
    locals_["movement_controller"].advanced_squad_ids.add(actor)
    locals_["movement_controller"].moved_distance_this_turn[actor] = 6.5
    actor.charged_this_turn = True

    SNAPSHOT["led"] = (led.name,
                       [(m.profile.name, m.current_wounds) for m in led.models])
    SNAPSHOT["actor"] = actor.name
    SNAPSHOT["max"] = {m.profile.name: m.profile.wounds for m in led.models}

    locals_["_save_scene"]("saved by verify_save_load", path=SAVE, quiet=True)


def _drive(hook, frames):
    """Run selfplay's real main() loop, calling `hook` once at `frames`."""
    fired = []
    real_take = main.take_pending_placement if hasattr(main, "take_pending_placement") else None
    import pygame
    count = {"n": 0}
    real_flip = pygame.display.flip

    def flip(*args, **kwargs):
        count["n"] += 1
        if count["n"] == frames and not fired:
            fired.append(True)
            frame = sys._getframe(1)
            while frame is not None and frame.f_code.co_name != "main":
                frame = frame.f_back
            if frame is None:
                raise SystemExit("could not reach main()'s frame")
            hook(frame.f_locals)
        return real_flip(*args, **kwargs)

    pygame.display.flip = flip
    try:
        runpy.run_module("selfplay", run_name="__main__")
    except SystemExit:
        pass
    finally:
        pygame.display.flip = real_flip
    return bool(fired)


config.MAP = MAP
sys.argv = ["selfplay.py", MAP, "300"]
print("=" * 74)
print(f"PASS 1 - play {MAP}, stage a mid-turn state, press Save")
print("=" * 74)
if not _drive(_stage_and_save, 260):
    print("FAILED: never reached the frame to save on")
    raise SystemExit(1)
print(f"saved            : {SAVE} ({os.path.getsize(SAVE)} bytes)")
print(f"damaged unit     : {SNAPSHOT['led'][0]}")
print(f"  survivors      : {SNAPSHOT['led'][1]}")
print(f"already acted    : {SNAPSHOT['actor']}")

data = scene_io.read(SAVE)
entry = next(e for e in data["squads"] if e["name"] == SNAPSHOT["led"][0])
print(f"file names WHICH model : {entry['models'][0].get('model')!r}")
print(f"file has an activation section : {'activation' in data}")

# ------------------------------------------------------------------ pass 2
RESULT = {}


def _inspect(locals_):
    squads = {e["squad"].name: e["squad"] for e in locals_["scene_units"]}
    led = squads[SNAPSHOT["led"][0]]
    actor = squads[SNAPSHOT["actor"]]
    RESULT["led"] = [(m.profile.name, m.current_wounds) for m in led.models]
    RESULT["over_max"] = [(m.profile.name, m.current_wounds, m.profile.wounds)
                          for m in led.models
                          if m.current_wounds > m.profile.wounds]
    RESULT["shot"] = actor in locals_["shooting_controller"].shot_squad_ids
    RESULT["can_move"] = locals_["movement_controller"].can_move(actor)
    RESULT["distance"] = locals_["movement_controller"].moved_distance_this_turn.get(actor)
    RESULT["charged"] = actor.charged_this_turn


print("\n" + "=" * 74)
print("PASS 2 - load that file into a second main() and ask the live objects")
print("=" * 74)
config.LOAD_SCENE = SAVE
config.MAP = MAP
sys.argv = ["selfplay.py", MAP, "40"]
if not _drive(_inspect, 12):
    print("FAILED: never reached the frame to inspect on")
    raise SystemExit(1)

want = SNAPSHOT["led"][1]
print(f"damage    : survivors {RESULT['led']}")
print(f"            expected  {want}   -> {'SAME' if RESULT['led'] == want else 'DIFFERENT'}")
print(f"            models above their own maximum wounds: {RESULT['over_max']}")
print(f"activation: {SNAPSHOT['actor']}")
print(f"            already shot this phase : {RESULT['shot']}")
print(f"            may move again          : {RESULT['can_move']}")
print(f"            moved_distance_this_turn: {RESULT['distance']}")
print(f"            charged_this_turn       : {RESULT['charged']}")

ok = (RESULT["led"] == want and not RESULT["over_max"] and RESULT["shot"]
      and not RESULT["can_move"] and RESULT["distance"] == 6.5
      and RESULT["charged"])
print("\n" + ("PASS - the loaded battle is the battle that was saved"
               if ok else
               "FAIL - the loaded battle is not the battle that was saved"))
if NEUTRALIZE:
    print("(--neutralize: FAIL is the expected result, and is the report)")
    raise SystemExit(0 if not ok else 1)
raise SystemExit(0 if ok else 1)
