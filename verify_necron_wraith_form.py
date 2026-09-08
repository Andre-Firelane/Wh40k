"""Runtime proof through the REAL main() loop that Wraith Form's mortal wounds
now LAND - by clicking the defender's choice away.

THE MEASURED SHAPE. Canoptek Wraiths' Wraith Form rolls a D6 per model moved
over an enemy unit and inflicts a mortal wound per 4+. It built a
MortalWoundAllocationSession and had no pending_damage_choice, no
choose_damage_model and no Feel No Pain drain, and main.py asked it nothing -
so rule 06.02's "the defender allocates" had no answer anywhere in the repo.
Measured before the fix, three sixes into a ten-model target:

    the log said "3 mortal wound(s)"
    wounds actually landed: 0

Against a ONE-model target it resolved, which is why it shipped.

A UNIT TEST CANNOT SEE THE OTHER HALF. Driving the controller directly, every
method now works - what was missing was five lines in main.py that call them.
So the click here is a REAL MOUSEBUTTONDOWN posted into main()'s own event
pump, at the on-screen position of a model the game itself says is eligible,
and if the chain has no branch for it, nothing happens.

WHAT IS STAGED, and why each - named rather than quietly faked:
  * THE NECRONS AS PLAYER 1. config ships PLAYER2_ARMY = "necrons", and this is
    a question about the HUMAN's choice; measured against the AI's army it would
    report a truthful-looking zero.
  * THE MOVE ITSELF. A MockAgent run does not walk Canoptek Wraiths across a
    multi-model enemy inside a fixed frame budget, so a passive counter would
    report zero and look like a pass. It is opened through the controller's own
    _use(), which is the call its listener makes.
Everything after that is real: the real dice panel, the real event chain, the
real board highlight, the real phase gate.

Usage:  python verify_necron_wraith_form.py [map2] [frames]
        python verify_necron_wraith_form.py map2 --neutralize
"""

import runpy
import sys

import pygame

from game import wraith_form as wf
from game.input_handler import InputManager
from game.renderer import Renderer
from game.turn import TurnTracker

HUMAN = "Player 1"
OPEN_AT = 700          # well past the pre-game

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

state = {"frames": 0, "ctrl": None, "handler": None, "board": None,
         "tracker": None,
         "opened_at": None, "busy_frames": 0, "resolved_at": None,
         "highlighted": 0, "clicks": 0, "phase_states": [],
         "target": None, "before": None, "rolled": 0}


# --- the live objects -------------------------------------------------------
_real_wf_init = wf.WraithFormController.__init__


def wf_init(self, *args, **kwargs):
    _real_wf_init(self, *args, **kwargs)
    state["ctrl"] = self


wf.WraithFormController.__init__ = wf_init

_real_handler_init = InputManager.__init__


def handler_init(self, *args, **kwargs):
    _real_handler_init(self, *args, **kwargs)
    state["handler"] = self


InputManager.__init__ = handler_init

_real_tracker_init = TurnTracker.__init__


def tracker_init(self, *args, **kwargs):
    """Captured directly. WraithFormController does not hold a turn tracker
    of its own - reading one off its movement_controller gave None and made the
    probe report "0 phase changes after", which reads as a freeze the run did
    not have."""
    _real_tracker_init(self, *args, **kwargs)
    state["tracker"] = self


TurnTracker.__init__ = tracker_init

_real_highlight = Renderer.draw_damage_choice_highlight


def draw_damage_choice_highlight(self, surface, board, models):
    """Also where the live Board is captured - the same call that proves the
    board says which models are pickable."""
    state["board"] = board
    ctrl = state["ctrl"]
    if models and ctrl is not None and models is ctrl.pending_damage_choice:
        state["highlighted"] += 1
    return _real_highlight(self, surface, board, models)


Renderer.draw_damage_choice_highlight = draw_damage_choice_highlight


# --- THE PRE-FIX WORLD ------------------------------------------------------
if NEUTRALIZE:
    # Exactly what shipped: the session is built and nothing can drain it.
    # BOTH members, because either one alone still leaves the other able to
    # resolve it - half a pre-fix world proves nothing.
    wf.WraithFormController.pending_damage_choice = property(lambda self: None)
    wf.WraithFormController.choose_damage_model = lambda self, model: None


# --- the click --------------------------------------------------------------
def screen_pos_of(model):
    """The on-screen pixel a human would click to pick `model` - the exact
    inverse of input_handler.token_at_event()."""
    handler, board = state["handler"], state["board"]
    if handler is None or board is None:
        return None
    nx, ny = board.to_px(model.x_in, model.y_in)
    camera = getattr(handler, "camera", None)
    if camera is not None:
        vis, dest = camera.visible_rect(), camera.dest_rect()
        local = (dest.x + (nx - vis.x) / vis.width * dest.width,
                 dest.y + (ny - vis.y) / vis.height * dest.height)
    else:
        local = (nx, ny)
    off = getattr(handler, "board_offset", (0, 0))
    return (int(local[0] + off[0]), int(local[1] + off[1]))


_pump = {"real": None}


def _install_pump():
    """selfplay REPLACES pygame.event.get at import, so a wrapper installed
    before runpy is simply overwritten. Installed from a frame hook instead,
    by which point selfplay's own pump is in place."""
    if _pump["real"] is None:
        _pump["real"] = pygame.event.get
        pygame.event.get = event_get


def event_get(*args, **kwargs):
    events = list(_pump["real"](*args, **kwargs))
    ctrl = state["ctrl"]
    if ctrl is None or state["opened_at"] is None:
        return events

    # A STANDING PROMPT FIRST. main()'s chain answers decision_manager before
    # the dice, and selfplay answers no prompt belonging to the HUMAN outside
    # the pre-game - one left open swallows every click from here on.
    decisions = getattr(ctrl, "decision_manager", None)
    if decisions is not None and getattr(decisions, "is_pending", False):
        options = list(getattr(decisions, "options", ()) or ())
        if options:
            state["declined"] = state.get("declined", 0) + 1
            decisions.choose(len(options) - 1)
        return events

    # THE ROLL. The same click selfplay would post: a real MOUSEBUTTONDOWN
    # outside the left panel, which is what main()'s dice branch reads as
    # "acknowledged".
    dice = getattr(ctrl, "dice_manager", None)
    if dice is not None and getattr(dice, "is_pending", False):
        surface = pygame.display.get_surface()
        w, h = surface.get_size() if surface else (1200, 800)
        state["dice_clicks"] = state.get("dice_clicks", 0) + 1
        return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (w - 8, h - 8), "button": 1}),
                pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": (w - 8, h - 8), "button": 1})]

    choice = ctrl.pending_damage_choice
    if not choice:
        return events
    pos = screen_pos_of(choice[0])
    if pos is None:
        return events
    # REPLACING selfplay's own events on these frames, not adding to them:
    # selfplay clicks the board every frame, and one landing on another model
    # would resolve the choice for the wrong reason.
    state["clicks"] += 1
    return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1}),
            pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": 1})]


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


_real_flip = pygame.display.flip


def flip(*args, **kwargs):
    _install_pump()
    state["frames"] += 1
    ctrl = state["ctrl"]
    frame = state["frames"]

    if ctrl is not None:
        tracker = state.get("tracker")
        if tracker is not None and getattr(tracker, "started", False):
            now = (tracker.battle_round, tracker.turn_owner, tracker.phase)
            if not state["phase_states"] or state["phase_states"][-1] != now:
                state["phase_states"].append(now)

        if frame == OPEN_AT and state["opened_at"] is None:
            mover = target = None
            for token in (ctrl._tokens() or ()):
                squad = getattr(token, "squad", None)
                if squad is None:
                    continue
                if (mover is None and squad.owner == HUMAN
                        and wf.has_wraith_form(squad) and _living(squad)):
                    mover = squad
                if (target is None and squad.owner != HUMAN
                        and len(_living(squad)) >= 3):
                    target = squad
            if mover is not None and target is not None:
                state["before"] = sum(m.current_wounds for m in target.models)
                state["target"] = target.name
                state["mover"] = mover.name
                state["dice"] = wf.dice_count(mover)
                ctrl._use(mover, target)
                state["opened_at"] = frame
                state["phases_at_open"] = len(state["phase_states"])

        if state["opened_at"] is not None:
            busy = ctrl.is_busy or ctrl.mortal_wound_session is not None
            if busy:
                state["busy_frames"] += 1
            elif state["resolved_at"] is None:
                state["resolved_at"] = frame

    return _real_flip(*args, **kwargs)


pygame.display.flip = flip

from game import config                                              # noqa: E402

# THE NECRONS AS PLAYER 1 - see the module docstring.
config.PLAYER1_ARMY = "necrons"
config.PLAYER2_ARMY = "aeldari"
config.ARMY_SELECT = False

sys.argv = ["selfplay.py"] + (sys.argv[1:] or ["map2", "2500"])
runpy.run_module("selfplay", run_name="__main__")

print()
print("--- Wraith Form mortal wounds" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
if state["ctrl"] is None:
    print("  the controller was never built - INCONCLUSIVE")
    raise SystemExit(2)
if state["opened_at"] is None:
    print("  no Wraith Form bearer and multi-model victim on the board - INCONCLUSIVE")
    raise SystemExit(2)

ctrl = state["ctrl"]
target_squad = None
for token in (ctrl._tokens() or ()):
    squad = getattr(token, "squad", None)
    if squad is not None and squad.name == state["target"]:
        target_squad = squad
        break
after = (sum(m.current_wounds for m in target_squad.models)
         if target_squad is not None else None)
landed = None if after is None else state["before"] - after
changes = len(state["phase_states"]) - state.get("phases_at_open", 0)

print("  opened at                 : frame %d, %s over %s (%d dice)"
      % (state["opened_at"], state.get("mover"), state["target"], state.get("dice", 0)))
print("  frames the board drew the eligible models : %d" % state["highlighted"])
print("  real clicks: %d on the dice, %d on an eligible model"
      % (state.get("dice_clicks", 0), state["clicks"]))
print("  frames it stayed blocking : %d" % state["busy_frames"])
print("  resolved at               : %s"
      % (state["resolved_at"] if state["resolved_at"] else "NEVER"))
print("  WOUNDS LANDED on the target: %s" % landed)
# FRAMES AFTER, not phase changes, is what "the game went on" rests on here:
# measured, a Necron self-play run reaches barely any phase change at all in a
# budget worth waiting for (the documented harness limit), so a phase count
# would read as a freeze the run did not have. What proves there was no
# deadlock is that it stopped blocking and the loop kept running.
after_frames = (state["frames"] - state["resolved_at"]) if state["resolved_at"] else 0
print("  frames the loop ran AFTER it resolved    : %d" % after_frames)
print("  phase changes after (informational)      : %d" % changes)

print()
if NEUTRALIZE:
    if state["highlighted"] or state["clicks"]:
        print("  FAIL: neutralized, but the board still offered the choice")
        raise SystemExit(1)
    print("  OK (as the pre-fix world): the board never said which models were "
          "pickable, no click was possible, and %s wound(s) landed" % landed)
    raise SystemExit(0)
if not state["highlighted"]:
    print("  FAIL: the board never said which models were pickable")
    raise SystemExit(1)
if not state["clicks"]:
    print("  FAIL: no eligible model was ever clickable")
    raise SystemExit(1)
if not landed:
    print("  FAIL: the wounds were rolled and never landed (the reported bug)")
    raise SystemExit(1)
print("  OK: the board showed the choice, a real click resolved it through the "
      "chain, %d wound(s) landed, and the loop ran %d more frames"
      % (landed, after_frames))
