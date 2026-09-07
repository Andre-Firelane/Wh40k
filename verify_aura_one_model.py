"""Runtime proof through the REAL main() loop that the range ruler rings only
the model that was picked.

A source guard shows the argument is written down; it does not show that the
value arriving at the renderer is the anchor the player picked. "Built but
never FED" has shipped in this repo six times, so this drives selfplay.py's
real main() loop, turns the ruler on, picks ONE model of a multi-model unit
through the REAL MovementController.select() - the same call a board click
makes - and then reports what main() actually handed the renderer.

WHY select() RATHER THAN A SYNTHETIC CLICK. That was the first version, and it
measured nothing twice: a click lands on whatever occupies that pixel, models
move between capture and click, and MovementController.can_select() refuses the
other player's units outside their turn. Both runs ended up ringing a lone
Doomsday Ark, which is "1 of 1" in the fixed AND the broken world. Driving the
same entry point the click drives keeps the wiring under test (main() -> the
renderer) while removing the part that was only ever noise.

Harness traps this walks into deliberately, both already paid for once:
  * importing selfplay runs nothing (its __main__ guard), so it goes via runpy;
  * selfplay REPLACES pygame.event.get at import, so anything hooked onto the
    pump has to be installed from a per-frame hook rather than before runpy.

Usage:  python verify_aura_one_model.py [map2]
        python verify_aura_one_model.py map2 --neutralize
"""

import runpy
import sys

from game import aura_ruler
from game.renderer import Renderer

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

state = {"picked": None, "rung": []}

_real_aura = Renderer.draw_range_aura
_real_move_range = Renderer.draw_move_range


def draw_range_aura(self, surface, board, squad, radius_in, model=None):
    if NEUTRALIZE:
        model = None   # the pre-fix world: every model of the unit, every frame
    if squad is not None and radius_in:
        rings = 1 if (model is not None and model.squad is squad) else len(squad.models)
        state["rung"].append((squad.name, len(squad.models), rings))
    return _real_aura(self, surface, board, squad, radius_in, model=model)


def draw_move_range(self, surface, board, movement_controller):
    """A per-frame hook that is handed the REAL MovementController main() built."""
    if state["picked"] is None:
        for token in movement_controller.all_tokens or ():
            squad = getattr(token, "squad", None)
            if squad is None or len(squad.models) < 5:
                continue
            if any(m.is_dead() for m in squad.models):
                continue
            model = squad.models[len(squad.models) // 2]
            movement_controller.select(model)
            if movement_controller.selected_model is model:
                state["picked"] = (squad.name, len(squad.models), model)
                break
    return _real_move_range(self, surface, board, movement_controller)


Renderer.draw_range_aura = draw_range_aura
Renderer.draw_move_range = draw_move_range

# The ruler is a module-level session preference, so it can simply be switched
# on here - exactly as the toolbar toggle would.
aura_ruler.set_enabled(True)
aura_ruler.set_radius(6)

sys.argv = ["selfplay.py"] + (sys.argv[1:] or ["map2"])
runpy.run_module("selfplay", run_name="__main__")

print()
print("--- range ruler spy" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
if state["picked"] is None:
    print("  no multi-model unit could be picked - INCONCLUSIVE")
    raise SystemExit(2)
name, models, model = state["picked"]
print(f"  picked               : one model of {name} ({models} models)")
seen = [entry for entry in state["rung"] if entry[0] == name]
if not seen:
    print("  the ruler never drew for it - INCONCLUSIVE")
    raise SystemExit(2)
print(f"  RULER RANG           : {seen[-1][2]} of {models} models")
