"""Does the left panel really answer for all 27 controllers, in the real loop?

  User: "das overwatch panel links scheint manchmal noch Faehigkeiten zu
   verdecken. manchmal muss ich Einheiten fuer die Verteilung irgendwelcher
   Mortal wounds auswaehlen, links steht aber overwatch."

The `verify_sudden_storm_wiring.py` pattern. Source guards show the wiring is
written down (test_event_chain_wiring.py sections 12 and 20); this drives the
REAL main() loop and watches what the panel actually draws.

WHY ONE FACT IS STAGED, and only one. A MockAgent run does not produce a
human-owned mortal-wound allocation on its own - selfplay answers no prompt
belonging to the human outside the pre-game (this repo's documented harness
limit), and reaching Flickerjump's end-of-phase D6 needs a board this harness
does not build. A passive count would report 0 and read like a pass. So this
opens a REAL MortalWoundAllocationSession on a REAL human squad, through the
REAL flickerjump controller that main() built - one of the 25 that had no panel
branch at all - and stages the overwatch state that collided with it. Every
step after that is real: main()'s own list, main()'s own hand-off, the real
ActionPanel drawing into the real frame.

WHAT IT REPORTS
  * which screen the panel drew while the allocation was open;
  * whether the board rang overwatch targets at the same time;
  * whether the panel stayed clickable (its toolbar registers buttons).

Usage:  python verify_damage_pick_panel.py [map2] [--frames N] [--neutralize]

`--neutralize` restores the pre-fix world - the panel answers for shooting and
fight only - and must report the FIRE OVERWATCH screen instead.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import runpy

MAP = "map2"
FRAMES = 2200
NEUTRALIZE = "--neutralize" in sys.argv[1:]
for arg in sys.argv[1:]:
    if arg.startswith("--frames"):
        FRAMES = int(arg.split("=", 1)[1])
    elif arg.startswith("map"):
        MAP = arg

from game import config                                  # noqa: E402
from game import overwatch as overwatch_mod              # noqa: E402
from game.damage_resolution import MortalWoundAllocationSession  # noqa: E402
from game.ui.action_panel import ActionPanel             # noqa: E402

config.ARMY_SELECT = False

seen = {"list_size": None, "screen": None, "staged": False,
        "overwatch_rings": None, "panel_buttons": None, "squad": None,
        "overwatch_state": None}

# WHICH BRANCH WINS, measured over EVERY screen the dispatch can draw rather
# than over the two this probe expects. The first neutralized run reported
# "nothing", which would have been a finding about the probe: the dispatch has
# 30 branches and any of them can be the one that fills the hole.
_real_required = ActionPanel._draw_action_required


def spy_required(self, surface, rect, accent, message):
    seen["screen"] = "ALLOCATE: " + message
    return _real_required(self, surface, rect, accent, message)


ActionPanel._draw_action_required = spy_required

for _name in [n for n in dir(ActionPanel)
              if n.startswith("_draw_") and n not in ("_draw_action_required",
                                                      "_draw_button", "_draw_text",
                                                      "_draw_global_toolbar",
                                                      "_draw_selection_header",
                                                      "_draw_dispatch")]:
    _real = getattr(ActionPanel, _name)

    def _spy(self, *a, _n=_name, _r=_real, **kw):
        if seen["staged"] and seen["screen"] is None:
            seen["screen"] = _n
        return _r(self, *a, **kw)

    setattr(ActionPanel, _name, _spy)

_real_draw = ActionPanel.draw


def spy_draw(self, *args, **kwargs):
    # *args, because main.py calls this positionally with 34 arguments - the
    # three-stage positional chain this file's own scar tissue is about.
    # Remember which record this frame carries, so the neutralized world can
    # tell the two old controllers from the 25 new ones.
    self._probe_pick = kwargs.get("damage_pick")
    if NEUTRALIZE and self._probe_pick is not None:
        kwargs["damage_pick"] = None
        # ...and with no record the dispatch falls through, exactly as it did.
    out = _real_draw(self, *args, **kwargs)
    if seen["staged"] and seen["panel_buttons"] is None:
        seen["panel_buttons"] = len(self._buttons)
    return out


ActionPanel.draw = spy_draw

real_flip = pygame.display.flip
frames = {"n": 0}


def flip(*args, **kwargs):
    frames["n"] += 1
    if not seen["staged"] and frames["n"] > 40:
        frame = sys._getframe(1)
        while frame is not None and frame.f_code.co_name != "main":
            frame = frame.f_back
        if frame is not None:
            stage(frame.f_locals)
    return real_flip(*args, **kwargs)


def stage(loc):
    """Open a REAL allocation on a REAL human squad, through main()'s own
    flickerjump controller, and stage the overwatch state beside it."""
    controllers = loc.get("damage_choice_controllers")
    if controllers is None:
        return
    seen["list_size"] = len(controllers)
    state = loc.get("state")
    flicker = loc.get("flickerjump_controller")
    overwatch_ctrl = loc.get("fire_overwatch_controller")
    if state is None or flicker is None:
        return
    humans = loc.get("human_players") or set()
    squads = {t.squad for t in state.tokens
              if t.squad is not None and t.squad.owner in humans
              and len([m for m in t.squad.models if not m.is_dead()]) > 2}
    if not squads:
        return
    squad = sorted(squads, key=lambda s: s.name)[0]
    flicker.mortal_wound_session = MortalWoundAllocationSession(
        squad, 1, dice_manager=loc.get("dice_manager"), log=lambda _m: None)
    if flicker.pending_damage_choice is None:
        flicker.mortal_wound_session = None
        return
    # The collision from the report: overwatch offering at the same instant.
    if overwatch_ctrl is not None:
        overwatch_ctrl.state = overwatch_mod.CHOOSING_UNIT
        overwatch_ctrl.player = squad.owner
        seen["overwatch_state"] = overwatch_ctrl.state
    seen["squad"] = squad.name
    seen["staged"] = True
    # What the board rings, read from main()'s own derived set on the NEXT
    # frame - recorded by the renderer spy below.


from game.renderer import Renderer                       # noqa: E402

_real_shoot_targets = Renderer.draw_shoot_targets


def spy_shoot_targets(self, surface, board, models):
    if seen["staged"] and seen["overwatch_rings"] is None:
        seen["overwatch_rings"] = len(models or ())
    return _real_shoot_targets(self, surface, board, models)


Renderer.draw_shoot_targets = spy_shoot_targets

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
print("  verify_damage_pick_panel.py  (%s)" % ("NEUTRALIZED" if NEUTRALIZE else "as shipped"))
print("=" * 68)
print("  frames run                    : %d" % frames["n"])
print("  staged an allocation          : %s" % seen["staged"])
print("  main()'s shared list holds    : %s controllers" % seen["list_size"])
print("  on unit                       : %s" % seen["squad"])
print("  overwatch was offering        : %s" % seen["overwatch_state"])
print("  PANEL DREW                    : %s" % (seen["screen"] or "nothing"))
print("  board rang overwatch targets  : %s" % seen["overwatch_rings"])
print("  panel buttons while open      : %s" % seen["panel_buttons"])
print()

if not seen["staged"]:
    print("  INCONCLUSIVE - never staged the allocation (raise --frames)")
    raise SystemExit(2)

ok = True
if NEUTRALIZE:
    if seen["screen"] and seen["screen"].startswith("ALLOCATE"):
        print("  UNEXPECTED: the neutralized panel still named the allocation")
        ok = False
    else:
        print("  the pre-fix world is reproduced: the panel drew %s"
              % (seen["screen"] or "no screen at all"))
        print("  (WHICH branch fills the hole depends on what else is open that")
        print("   frame - Fire Overwatch is the one the user hit. The defect is")
        print("   that ANY other branch answers while an allocation is waiting.)")
else:
    if seen["screen"] and seen["screen"].startswith("ALLOCATE"):
        print("  the panel names the allocation, not overwatch")
    else:
        print("  FAILED: the panel did not draw the allocation screen")
        ok = False
    if seen["overwatch_rings"] == 0:
        print("  ...and the overwatch rings stood down")
    else:
        print("  FAILED: the board rang overwatch targets at the same time")
        ok = False

raise SystemExit(0 if ok else 1)
