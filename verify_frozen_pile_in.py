"""Does the base-contact house rule really reach the board, in the real loop?

  User: "Modelle in Base contact duerfen weder Pile in noch consolidate moves
   durchfuehren."
  ...and: "denke aber daran, dass bei einem rueckzug models natuerlich den base
   contact verlassen koennen."

The `verify_sudden_storm_wiring.py` pattern. Source guards and test_base_contact.py
show the rule is written and enforced; this drives the REAL main() loop and asks
the LIVE objects main() built - because "built but never FED" has hit this repo
six times, and is_movable() sits behind input_handler's real mouse chain.

WHY THE SITUATION IS STAGED, and only the situation. A MockAgent run does not
put a HUMAN unit into a pile-in with a model in base contact: selfplay answers
no prompt belonging to the human outside the pre-game (the documented harness
limit), and the AI's own pile-ins are resolved in one synchronous call with no
frame in between to look at. A passive count would report 0 and read like a
pass. So this pushes one enemy model into contact with one of the human's, opens
a REAL pile-in through main()'s own MovementController, and then asks the real
engine. Everything after the placement is real: the real clamp, the real
pick-up gate, the real renderer.

AND IT MEASURES THE RETREAT TOO, because that is the half a wrong fix would
break: the same model, in the same contact, has to be draggable the moment the
move is a Fall Back.

Usage:  python verify_frozen_pile_in.py [map2] [--frames N] [--neutralize]

`--neutralize` removes the rule (is_frozen always False) and must report the
model moving under a pile-in.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import runpy

MAP = "map2"
FRAMES = 900
NEUTRALIZE = "--neutralize" in sys.argv[1:]
for arg in sys.argv[1:]:
    if arg.startswith("--frames"):
        FRAMES = int(arg.split("=", 1)[1])
    elif arg.startswith("map"):
        MAP = arg

from game import base_contact                            # noqa: E402
from game import config                                  # noqa: E402

config.ARMY_SELECT = False

if NEUTRALIZE:
    # BOTH halves, or the probe reports a board still ringing models it no
    # longer freezes - a pre-fix world that is only half restored is exactly
    # the trap this repo records five instances of.
    base_contact.is_frozen = lambda *a, **k: False
    base_contact.frozen_models = lambda *a, **k: []

seen = {"staged": False, "squad": None, "frozen": None,
        "pile_in_movable": None, "pile_in_moved": None,
        "fallback_movable": None, "fallback_moved": None,
        "ringed": None, "panel_said": None}

from game.renderer import Renderer                        # noqa: E402
from game.ui.action_panel import ActionPanel              # noqa: E402

_real_ring = Renderer.draw_frozen_models


def spy_ring(self, surface, board, models):
    if models:
        seen["ringed"] = len(models)
    return _real_ring(self, surface, board, models)


Renderer.draw_frozen_models = spy_ring

_real_text = ActionPanel._draw_text


def spy_text(self, surface, rect, text, y, **kw):
    if "base contact" in (text or ""):
        seen["panel_said"] = text
    return _real_text(self, surface, rect, text, y, **kw)


ActionPanel._draw_text = spy_text

real_flip = pygame.display.flip
frames = {"n": 0}


def flip(*args, **kwargs):
    frames["n"] += 1
    if not seen["staged"] and frames["n"] > 60:
        frame = sys._getframe(1)
        while frame is not None and frame.f_code.co_name != "main":
            frame = frame.f_back
        if frame is not None:
            stage(frame.f_locals)
    return real_flip(*args, **kwargs)


def stage(loc):
    state = loc.get("state")
    mc = loc.get("movement_controller")
    humans = loc.get("human_players") or set()
    if state is None or mc is None or not humans:
        return
    mine = None
    for token in state.tokens:
        sq = token.squad
        if sq is not None and sq.owner in humans and len(sq.models) >= 3:
            mine = sq
            break
    foe = None
    for token in state.tokens:
        if token.squad is not None and token.squad.owner not in humans:
            foe = token
            break
    if mine is None or foe is None:
        return
    front = mine.models[0]
    # One enemy model pushed into contact - the only thing staged.
    foe.x_in = front.x_in
    foe.y_in = front.y_in - (front.radius_in + foe.radius_in + 0.05)
    seen["squad"] = mine.name
    seen["frozen"] = len(base_contact.frozen_models(mine, state.tokens, "pile_in"))

    # A REAL pile-in through main()'s own controller.
    mc.selected_squad = mine
    mc.start_pile_in_move(3.0, [])
    seen["pile_in_movable"] = mc.is_movable(front)
    before = (front.x_in, front.y_in)
    got = mc.clamp_move(front, front.x_in + 2.0, front.y_in)
    seen["pile_in_moved"] = got != before

    # ...and the SAME model, in the SAME contact, retreating.
    mc.start_fall_back_move("ordered_retreat")
    seen["fallback_movable"] = mc.is_movable(front)
    got2 = mc.clamp_move(front, front.x_in - 2.0, front.y_in)
    seen["fallback_moved"] = got2 != (front.x_in, front.y_in)

    # Leave a pile-in open so the ring and the panel hint get a frame.
    mc.start_pile_in_move(3.0, [])
    seen["staged"] = True


pygame.display.flip = flip
sys.argv = ["selfplay.py", MAP, str(FRAMES)]
try:
    runpy.run_module("selfplay", run_name="__main__")
except SystemExit:
    pass
finally:
    pygame.display.flip = real_flip

print()
print("=" * 68)
print("  verify_frozen_pile_in.py  (%s)" % ("NEUTRALIZED" if NEUTRALIZE else "as shipped"))
print("=" * 68)
print("  frames run                    : %d" % frames["n"])
print("  staged contact on             : %s" % seen["squad"])
print("  models frozen by the rule     : %s" % seen["frozen"])
print("  PILE IN  - can be picked up   : %s" % seen["pile_in_movable"])
print("  PILE IN  - the clamp let it   : %s" % seen["pile_in_moved"])
print("  FALL BACK- can be picked up   : %s" % seen["fallback_movable"])
print("  FALL BACK- the clamp let it   : %s" % seen["fallback_moved"])
print("  board rang frozen models      : %s" % seen["ringed"])
print("  panel said                    : %s" % (seen["panel_said"] or "nothing"))
print()

if not seen["staged"]:
    print("  INCONCLUSIVE - never staged the contact (raise --frames)")
    raise SystemExit(2)

ok = True
if NEUTRALIZE:
    if seen["pile_in_moved"]:
        print("  the pre-fix world is reproduced: a model in base contact piled in")
    else:
        print("  UNEXPECTED: neutralized run still froze the model")
        ok = False
else:
    for label, got, want in (
            ("a frozen model cannot be picked up for a pile-in", seen["pile_in_movable"], False),
            ("...and the clamp holds it still", seen["pile_in_moved"], False),
            ("THE RETREAT still picks up", seen["fallback_movable"], True),
            ("...and the clamp lets it leave contact", seen["fallback_moved"], True)):
        if got == want:
            print("  OK   %s" % label)
        else:
            print("  FAILED: %s (got %s, want %s)" % (label, got, want))
            ok = False
    if seen["ringed"]:
        print("  OK   the board rings the frozen model(s)")
    else:
        print("  FAILED: the board never rang a frozen model")
        ok = False

raise SystemExit(0 if ok else 1)
