"""Does a human's returning model really open a placement, in the real loop?

The `verify_sudden_storm_wiring.py` pattern. A source guard shows the call is
written down; this drives the REAL main() loop and watches what happens.

WHY THE FACT HAS TO BE STAGED. A MockAgent run does not reach a human
Reanimation return on its own - selfplay answers no prompt belonging to the
human outside the pre-game (this repo's documented harness limit), and with
nothing shooting, nothing dies, so Reanimation Protocols skips every unit. A
passive count would report 0 and read like a pass. So this kills two of the
HUMAN's Necrons on the first Command phase, which is exactly the board the user
described, and then watches the real controllers.

Two things have to be true, and they are the two halves of the change:
  * the human's return OPENS a SetupController placement over the returning
    models only, with the survivors left standing;
  * the AI's return opens nothing at all - it lands where the ability said, in
    the same frame, at no API cost.

Usage:  python verify_return_placement.py [map2] [--frames N]
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import runpy

MAP = "map2"
FRAMES = "1200"
for arg in sys.argv[1:]:
    if arg.startswith("--frames"):
        FRAMES = arg.split("=", 1)[1]
    elif arg.startswith("map"):
        MAP = arg

from game import config                              # noqa: E402
from game import reanimation_protocols as rp         # noqa: E402
from game import setup as setup_mod                  # noqa: E402
from game.return_placement import ReturnPlacementController  # noqa: E402

config.PLAYER1_ARMY = "necrons"
config.PLAYER2_ARMY = "necrons"
config.ARMY_SELECT = False

seen = {"human_opened": 0, "ai_opened": 0, "human_placed": [], "staged": False,
        "activations": 0, "survivors_moved": 0, "green_fraction": None,
        "band_drawn": None, "keepout_same": None, "radius_intact": None}

_real_place = ReturnPlacementController.place


def spy_place(self, squad, models, spots, **kwargs):
    before = {m.id: (m.x_in, m.y_in) for m in squad.models}
    result = _real_place(self, squad, models, spots, **kwargs)
    opened = self.setup_controller is not None and \
        self.setup_controller.state == setup_mod.PLACING
    if squad.owner in self.auto_players:
        seen["ai_opened"] += 1 if opened else 0
    elif opened:
        seen["human_opened"] += 1
        placing = list(self.setup_controller.placing_models)
        seen["human_placed"].append((squad.name, len(placing), len(squad.models)))
        # ...and HOW MUCH GROUND the overlay would paint green for it. User:
        # "immer wenn man Einheiten platzieren muss, zb durch Reanimation, muss
        # man in coherency platzieren ... im Moment geht das ueber die ganze
        # map?" Asked through the REAL predicate main.py hands the renderer, so
        # this is the picture, not a re-derivation of it.
        if placing:
            valid = self.setup_controller.placement_validator(squad)
            token = max(placing, key=lambda m: m.radius_in)
            import game.config as _cfg
            w, h = _cfg.BOARD_WIDTH_IN, _cfg.BOARD_HEIGHT_IN
            total = ok = 0
            x = 0.0
            while x <= w:
                y = 0.0
                while y <= h:
                    total += 1
                    ok += bool(valid(token, x, y))
                    y += 1.0
                x += 1.0
            seen["green_fraction"] = ok / total
            # ...and the two BASE-EDGE zones the renderer is actually handed.
            # The point of the base-edge reading is that the keep-out line does
            # not move with the base size, so it is asked for two very
            # different radii and must answer the same.
            keep_out, band = self.setup_controller.base_edge_zones(squad, token)
            seen["band_drawn"] = band is not None
            saved = token.radius_in
            token.radius_in = 2.1                      # a Doomsday-Ark base
            keep_out_big, _ = self.setup_controller.base_edge_zones(squad, token)
            token.radius_in = saved
            same = diff = 0
            x = 0.0
            while x <= w:
                y = 0.0
                while y <= h:
                    if keep_out(x, y) == keep_out_big(x, y):
                        same += 1
                    else:
                        diff += 1
                    y += 1.0
                x += 1.0
            seen["keepout_same"] = (same, diff)
            seen["radius_intact"] = token.radius_in == saved
        # The survivors must not have been picked up by the placement.
        for model in squad.models:
            if model.id in before and model not in placing:
                if (model.x_in, model.y_in) != before[model.id]:
                    seen["survivors_moved"] += 1
    return result


ReturnPlacementController.place = spy_place

_real_begin = rp.ReanimationProtocolsController.begin_command_phase


def spy_begin(self, squads, player):
    if not seen["staged"] and player not in config.AI_PLAYERS:
        for squad in sorted(squads, key=lambda s: s.name):
            if squad.owner == player and len(squad.models) > 3:
                for model in squad.models[:2]:
                    model.current_wounds = 0
                for model in list(squad.models[:2]):
                    squad.models.remove(model)
                    squad.destroyed_models.append(model)
                seen["staged"] = True
                print(f"[staged] killed 2 models of {squad.name}")
                break
    result = _real_begin(self, squads, player)
    if result:
        seen["activations"] += 1
    return result


rp.ReanimationProtocolsController.begin_command_phase = spy_begin

sys.argv = ["selfplay.py", MAP, FRAMES]
try:
    runpy.run_path("selfplay.py", run_name="__main__")
except SystemExit:
    pass

print("\n" + "=" * 72)
print(f"Reanimation Protocols activated : {seen['activations']}")
print(f"placements opened for the human : {seen['human_opened']}")
print(f"placements opened for the AI    : {seen['ai_opened']}   (must be 0)")
for name, placing, total in seen["human_placed"][:5]:
    print(f"    {name}: placing {placing} of {total} models")
print(f"survivors moved by a placement  : {seen['survivors_moved']}   (must be 0)")
if seen["green_fraction"] is not None:
    print(f"legal centres for it            : {100 * seen['green_fraction']:.1f}%"
          f" of the board   (coherency, rule 09.02)")
if seen["keepout_same"] is not None:
    same, diff = seen["keepout_same"]
    print(f"keep-out line, 1.26in vs 4.2in base: {same} same / {diff} different"
          f"   (must be 0 different - one line for the unit)")
    print(f"coherency band drawn            : {seen['band_drawn']}")
    print(f"the model's radius survived it  : {seen['radius_intact']}")

ok = (seen["human_opened"] > 0 and seen["ai_opened"] == 0
      and seen["survivors_moved"] == 0
      and all(p < t for _n, p, t in seen["human_placed"])
      # The overlay must show a RING, not the map. 20% is a deliberately loose
      # ceiling: the exact figure moves with where the survivors stand, and the
      # claim is the order of magnitude (85.9% before the fix).
      and (seen["green_fraction"] is None or seen["green_fraction"] < 0.20)
      # The base-edge half: one keep-out line for every base size, a band to
      # reach, and a model whose radius was left alone.
      and (seen["keepout_same"] is None or seen["keepout_same"][1] == 0)
      and seen["band_drawn"] is not False
      and seen["radius_intact"] is not False)
if seen["human_opened"] == 0:
    print("\n  *** THE HUMAN'S RETURN NEVER OPENED A PLACEMENT - this measured nothing.")
if seen["ai_opened"]:
    print("\n  *** A PLACEMENT WAS OPENED FOR THE AI - it would stall or cost a call.")

print("\n" + ("PASS - the human places, the AI lands" if ok else "FAIL"))
sys.exit(0 if ok else 1)
