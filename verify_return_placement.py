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

...and, since 2026-09-07, the third half of the same picture: the board has to
SAY WHICH MODELS just came back (user: "Widerbeleben - ich kann nicht erkennen,
welche einheiten gerade zurueckgekommen sind, um sie zu verschieben"). The unit
outline is equally true of the survivors standing beside them, so the returning
ones get their own ring - counted here in the REAL frame, because a source
guard only shows that the call is written down.

NOTE ON --frames: the default is deliberately generous. The human's first
Command phase is a long way past the pre-game, and with too few frames this
reports 0 activations and reads like a failure of the thing being measured.

Usage:  python verify_return_placement.py [map2] [--frames N] [--neutralize]

`--neutralize` restores the pre-fix world for that last half (the identity draw
never learns which models are the new ones) and must report no rings at all.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import runpy

MAP = "map2"
FRAMES = "3000"
NEUTRALIZE = "--neutralize" in sys.argv[1:]
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
        "damaged": [], "queued": [], "engine_seated": [], "opened_for": [],
        "confirmed": 0, "placer": None,
        "activations": 0, "survivors_moved": 0, "green_fraction": None,
        "band_drawn": None, "keepout_same": None, "radius_intact": None,
        "identity_frames": 0, "ringed": None, "unit_size": None}

# WHICH MODELS the board rings, counted in the real frame. Spied on the
# RENDERER rather than on the controller: "built but never FED" has hit this
# repo six times, and only the drawing answers whether main.py hands the
# subset over at all.
from game.renderer import Renderer                   # noqa: E402

_real_identity = Renderer.draw_placement_identity
_real_rings = Renderer.draw_returning_models


def spy_identity(self, surface, board, squad, placing_models=None):
    seen["identity_frames"] += 1
    if NEUTRALIZE:
        placing_models = None       # the pre-fix world: it never knew
    return _real_identity(self, surface, board, squad, placing_models=placing_models)


if NEUTRALIZE:
    # ...and the SECOND pre-fix world this probe now covers: place()'s fork
    # folded "somebody is already placing" in with "this is the AI", so a
    # human's second reanimating unit had its models seated by the engine.
    # Restored by putting can_start_setup() back into the auto branch, which is
    # exactly how the line read.
    _pre_fix_place = ReturnPlacementController.place

    def _silent_place(self, squad, models, spots, **kwargs):
        setup_ctrl = self.setup_controller
        if (setup_ctrl is not None and squad.owner not in self.auto_players
                and not setup_ctrl.can_start_setup(squad)):
            self.auto_players = set(self.auto_players) | {squad.owner}
            try:
                return _pre_fix_place(self, squad, models, spots, **kwargs)
            finally:
                self.auto_players = {p for p in self.auto_players
                                     if p != squad.owner}
        return _pre_fix_place(self, squad, models, spots, **kwargs)

    ReturnPlacementController.place = _silent_place


def spy_rings(self, surface, board, models):
    if models:
        seen["ringed"] = len(models)
    return _real_rings(self, surface, board, models)


Renderer.draw_placement_identity = spy_identity
Renderer.draw_returning_models = spy_rings

_real_place = ReturnPlacementController.place


def spy_place(self, squad, models, spots, **kwargs):
    seen["placer"] = self
    before = {m.id: (m.x_in, m.y_in) for m in squad.models}
    result = _real_place(self, squad, models, spots, **kwargs)
    opened = self.setup_controller is not None and \
        self.setup_controller.state == setup_mod.PLACING
    # WHOSE placement, not merely that one is open: with a queue in front of
    # it, setup.state is PLACING for the unit ALREADY being placed, so
    # "state == PLACING" alone cannot tell a queued unit from a seated one.
    mine = (opened and self.setup_controller.setting_up_squad is squad)
    if squad.owner in self.auto_players:
        seen["ai_opened"] += 1 if opened else 0
    elif not mine and opened:
        # Somebody else's placement is open. Either this one queued behind it
        # (correct) or the engine seated it (the reported bug).
        if getattr(self, "_waiting", None):
            seen["queued"].append(squad.name)
        else:
            seen["engine_seated"].append(squad.name)
    elif mine:
        seen["human_opened"] += 1
        seen["opened_for"].append(squad.name)
        placing = list(self.setup_controller.placing_models)
        seen["human_placed"].append((squad.name, len(placing), len(squad.models)))
        seen["unit_size"] = len(squad.models)
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


NO_RING_NOTE = (chr(10) + "  *** NOTHING WAS RINGED - the board never said "
                "which models came back.")

if NEUTRALIZE:
    # THE ROLL-HOLD, the primary half: without it _apply_and_advance() puts the
    # next unit's die on the table over an open placement, which is what made
    # the silent seating reachable at all.
    def _roll_ahead(self, squad, rolled):
        self._apply(squad, rolled)
        self._roll_next()

    rp.ReanimationProtocolsController._apply_and_advance = _roll_ahead

ReturnPlacementController.place = spy_place

# THE CONFIRM IS STAGED, and it has to be. selfplay answers no prompt belonging
# to the HUMAN outside the pre-game (the documented harness limit), so nothing
# ever presses Confirm - and with the queue holding the next unit behind an
# open placement, a passive run measures exactly ONE placement and never
# reaches the half this was extended for. Pressed through the controller's own
# confirm(), which is the call game/ui/action_panel.py hands to the button.
_real_flip_rp = pygame.display.flip


def _flip_rp(*args, **kwargs):
    placer = seen.get("placer")
    if placer is not None and placer.is_busy:
        seen["confirm_wait"] = seen.get("confirm_wait", 0) + 1
        if seen["confirm_wait"] % 30 == 0 and placer.confirm():
            seen["confirmed"] += 1
    return _real_flip_rp(*args, **kwargs)


pygame.display.flip = _flip_rp

_real_begin = rp.ReanimationProtocolsController.begin_command_phase


def spy_begin(self, squads, player):
    # TWO units, not one. A single damaged unit cannot show the defect this
    # was extended for: place()'s fork used to fold "somebody is already
    # placing" in with "this is the AI", so the SECOND unit to reanimate in one
    # Command phase had its models seated by the engine with no prompt and no
    # distinguishing log line. Measured before the fix, the placement opened
    # for the FIRST unit twice.
    if not seen["staged"] and player not in config.AI_PLAYERS:
        for squad in sorted(squads, key=lambda s: s.name):
            if squad.owner == player and len(squad.models) > 3:
                for model in squad.models[:2]:
                    model.current_wounds = 0
                for model in list(squad.models[:2]):
                    squad.models.remove(model)
                    squad.destroyed_models.append(model)
                seen["damaged"].append(squad.name)
                print(f"[staged] killed 2 models of {squad.name}")
                if len(seen["damaged"]) == 2:
                    seen["staged"] = True
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
print(f"units staged as damaged         : {', '.join(seen['damaged']) or 'none'}")
print(f"placements opened, per unit     : {', '.join(seen['opened_for']) or 'none'}")
print(f"queued behind an open placement : {', '.join(seen['queued']) or 'none'}")
print(f"confirmed by the probe          : {seen['confirmed']}")
print(f"seated by the ENGINE for a human: {', '.join(seen['engine_seated']) or 'none'}"
      f"   (must be none)")
print(f"identity draws on the board     : {seen['identity_frames']}")
print(f"models ringed as RETURNING      : {seen['ringed']}"
      f" of {seen['unit_size']} in the unit")

ok = (seen["human_opened"] > 0 and seen["ai_opened"] == 0
      and seen["survivors_moved"] == 0
      # THE QUEUE: no human's models may be seated by the engine because
      # somebody else's placement happened to be open, and no unit may get a
      # second placement while another gets none.
      and not seen["engine_seated"]
      and len(seen["opened_for"]) == len(set(seen["opened_for"]))
      and all(p < t for _n, p, t in seen["human_placed"])
      # The overlay must show a RING, not the map. 20% is a deliberately loose
      # ceiling: the exact figure moves with where the survivors stand, and the
      # claim is the order of magnitude (85.9% before the fix).
      and (seen["green_fraction"] is None or seen["green_fraction"] < 0.20)
      # The base-edge half: one keep-out line for every base size, a band to
      # reach, and a model whose radius was left alone.
      and (seen["keepout_same"] is None or seen["keepout_same"][1] == 0)
      and seen["band_drawn"] is not False
      and seen["radius_intact"] is not False
      # ...and the board says WHICH models are the new ones: some, not all.
      and seen["ringed"] is not None
      and (seen["unit_size"] is None or seen["ringed"] < seen["unit_size"]))
if seen["human_opened"] == 0:
    print("\n  *** THE HUMAN'S RETURN NEVER OPENED A PLACEMENT - this measured nothing.")
if seen["ringed"] is None and seen["human_opened"]:
    print(NO_RING_NOTE)
if seen["ai_opened"]:
    print("\n  *** A PLACEMENT WAS OPENED FOR THE AI - it would stall or cost a call.")
if seen["engine_seated"]:
    print("\n*** THE ENGINE SEATED A HUMAN'S MODELS because another "
          "placement was open - the reported bug.")
if len(seen["opened_for"]) != len(set(seen["opened_for"])):
    print("\n*** ONE UNIT GOT TWO PLACEMENTS while another got none.")

print("\n" + ("PASS - the human places, the AI lands, the board says which"
               if ok else "FAIL"))
sys.exit(0 if ok else 1)
