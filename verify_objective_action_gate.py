"""Does the objective-action control gate really reach the PANEL, in the real loop?

  User: "Actions wie plunder werden angeboten, obwohl Einheit gar nicht auf
   einem objective steht ( muss nach Move aktualisiert werden)"

The `verify_frozen_pile_in.py` pattern. The suites drive the predicate and the
controller directly; this drives the REAL main() loop and asks the LIVE
SecondaryMissionController main() built, because what the report is about is a
BUTTON, and "built but never FED" has hit this repo six times.

IT ALSO MEASURES THE SECOND HALF OF THE REPORT - "muss nach Move aktualisiert
werden". controlled_by is recomputed in advance_turn_phase() at every phase
boundary, so by the Shooting phase - the only phase either action may start in
- it is the post-movement board. The probe moves the unit and asks again
through the same live controller, so the refresh is measured rather than
argued.

WHY THE SITUATION IS STAGED, and only the situation. FOUR facts: the deck has
to be on for Player 1 (selfplay empties the config tuple at import - the
documented harness opt-out, restored here to the value game/config.py ships),
Cleanse has to be IN HAND (the deck is shuffled and deals two a round - over a
bounded run it may never appear), the phase has to be Shooting AND the card
player's own turn, and a unit has to be standing on a non-home objective. A passive count would report 0 and read like a pass. Every
answer after that is real: the live controller, the live ActionController, the
live objectives, main()'s own 14.02 recomputation.

Usage:  python verify_objective_action_gate.py [map4] [--frames N] [--neutralize]

`--neutralize` drops the control term and must report the button appearing on
an objective the unit does not control - the reported bug.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import runpy

MAP = "map4"                       # the reported board
FRAMES = 1200
NEUTRALIZE = "--neutralize" in sys.argv[1:]
for arg in sys.argv[1:]:
    if arg.startswith("--frames"):
        FRAMES = int(arg.split("=", 1)[1])
    elif arg.startswith("map"):
        MAP = arg

from game import config                                  # noqa: E402
from game import mission_context                         # noqa: E402
from game import secondary_missions as sm                # noqa: E402
from game.objectives import is_within_range_of_objective  # noqa: E402

config.ARMY_SELECT = False
config.MAP_SELECT = False

if NEUTRALIZE:
    # The pre-fix world: the bare 3" gate, no control term. BOTH readers go
    # through this one function, so restoring it here restores it for Cleanse
    # AND Secure Asset - a half-restored world is the trap this repo records
    # five instances of.
    def _bare(squad, ctx):
        return [o for o in mission_context._non_home_objectives(ctx)
                if is_within_range_of_objective(squad, [o])]
    mission_context.objective_action_targets_for = _bare
    sm.objective_action_targets_for = _bare

seen = {"staged": False, "squad": None, "objective": None,
        "held_offers": None, "enemy_offers": None, "nobody_offers": None,
        "moved_away_offers": None, "controlled_by": None,
        "phase": None, "turn_owner": None, "refusal": None}

real_flip = pygame.display.flip
frames = {"n": 0}


def flip(*args, **kwargs):
    frames["n"] += 1
    if not seen["staged"] and frames["n"] > 80:
        frame = sys._getframe(1)
        while frame is not None and frame.f_code.co_name != "main":
            frame = frame.f_back
        if frame is not None:
            stage(frame.f_locals)
    return real_flip(*args, **kwargs)


def offers_for(ctrl, squad):
    return [entry[0] for entry in ctrl.available_actions_for(squad)]


def stage(loc):
    state = loc.get("state")
    ctrl = loc.get("secondary_mission_controller")
    turn = loc.get("turn_tracker")
    if state is None or ctrl is None or turn is None:
        return
    objectives = list(state.objectives)
    if not objectives:
        return
    ctx = ctrl._context()
    non_home = mission_context._non_home_objectives(ctx)
    if not non_home:
        return
    objective = non_home[0]

    mine = None
    for token in state.tokens:
        sq = token.squad
        if sq is not None and sq.owner == ctrl.player and sq.models:
            if sq.models[0].profile.oc > 0:
                mine = sq
                break
    if mine is None:
        return

    # THE THREE STAGED FACTS, each one named in the module docstring.
    # selfplay.py empties SECONDARY_MISSION_CARD_PLAYERS at import (the
    # documented harness opt-out: it answers no human prompt outside the
    # pre-game). Restore the value game/config.py SHIPS, so the live
    # controller plays the deck the real game gives Player 1.
    config.SECONDARY_MISSION_CARD_PLAYERS = ("Player 1",)
    ctrl.hand = [sm.CLEANSE]
    # Shooting AND the card player's own turn: advance_phase() wraps past Fight
    # into the OTHER player's Command phase, and available_actions_for() rightly
    # returns nothing when turn_owner is not the card player. Getting this wrong
    # reports a truthful-looking zero.
    for _ in range(12):
        if turn.phase == "Shooting" and turn.turn_owner == ctrl.player:
            break
        turn.advance_phase()
    seen["phase"] = turn.phase
    seen["turn_owner"] = turn.turn_owner
    cx, cy = mission_context.objective_centre(objective)
    for i, model in enumerate(mine.models):
        model.x_in, model.y_in = cx + i * 1.1, cy

    seen["squad"] = mine.name
    seen["objective"] = objective.name

    # main()'s own 14.02 recomputation - the "after the move" the report asks for.
    for obj in objectives:
        obj.update_control(list(state.tokens))
    seen["controlled_by"] = objective.controlled_by
    seen["held_offers"] = offers_for(ctrl, mine)
    if not seen["held_offers"]:
        # MEASURE the refusal rather than tell a story about it - an
        # explanation nobody checked is a story about the harness.
        ok_, why = ctrl.action_controller.can_start(sm.CLEANSE_ACTION, mine, ctrl._context())
        seen["refusal"] = why or ("plays_cards=%s" % ctrl.plays_cards)

    objective.controlled_by = "Player 2"
    seen["enemy_offers"] = offers_for(ctrl, mine)
    objective.controlled_by = None
    seen["nobody_offers"] = offers_for(ctrl, mine)

    # ...and a real MOVE off the objective, then main()'s own recomputation.
    for model in mine.models:
        model.x_in += 30.0
    for obj in objectives:
        obj.update_control(list(state.tokens))
    seen["moved_away_offers"] = offers_for(ctrl, mine)

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
print("=" * 72)
print("  verify_objective_action_gate.py  (%s)"
      % ("NEUTRALIZED" if NEUTRALIZE else "as shipped"))
print("=" * 72)
print("  frames run                       : %d" % frames["n"])
print("  unit staged                      : %s" % seen["squad"])
print("  objective                        : %s" % seen["objective"])
print("  phase / turn owner               : %s / %s" % (seen["phase"], seen["turn_owner"]))
print("  controlled_by after 14.02        : %r" % seen["controlled_by"])
if seen["refusal"]:
    print("  measured refusal                 : %s" % seen["refusal"])
print("  OFFERS while YOU hold it         : %s" % (seen["held_offers"] or "none"))
print("  OFFERS while the ENEMY holds it  : %s" % (seen["enemy_offers"] or "none"))
print("  OFFERS while NOBODY holds it     : %s" % (seen["nobody_offers"] or "none"))
print("  OFFERS after moving 30\" away     : %s" % (seen["moved_away_offers"] or "none"))
print()

if not seen["staged"]:
    print("  INCONCLUSIVE - never staged the situation (raise --frames)")
    raise SystemExit(2)

ok = True
if NEUTRALIZE:
    if seen["enemy_offers"] or seen["nobody_offers"]:
        print("  the pre-fix world is reproduced: the button appears on an objective")
        print("  the unit does not control - and 16.01 would lock its shooting AND")
        print("  charging for an action that can never complete.")
    else:
        print("  UNEXPECTED: neutralized run still withheld the offer")
        ok = False
else:
    for label, got, want in (
            ("offered while you hold the objective", bool(seen["held_offers"]), True),
            ("WITHHELD while the enemy holds it", bool(seen["enemy_offers"]), False),
            ("WITHHELD while nobody holds it", bool(seen["nobody_offers"]), False),
            ("WITHHELD once the unit has moved away", bool(seen["moved_away_offers"]), False)):
        if got == want:
            print("  OK   %s" % label)
        else:
            print("  FAILED: %s (got %s, want %s)" % (label, got, want))
            ok = False

raise SystemExit(0 if ok else 1)
