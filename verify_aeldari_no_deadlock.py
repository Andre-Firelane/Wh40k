"""Runtime proof through the REAL main() loop that Khaine's Vengeance can no
longer freeze the game - by CLICKING it away.

THE REPORTED SHAPE: Aspect Host's Khaine's Vengeance opens a Desperate Escape
step, and its is_busy sits in main.py's _has_unresolved_declaration(). Neither
its dice acknowledgement nor its damage choice was wired anywhere in the event
chain - so once the Stratagem was used, NOTHING could end the step and the
phase could never advance again. Built, blocking, and unclickable: CLAUDE.md's
error class 25 in its worst form, a hard hang rather than a silent no-op.

A unit test cannot see it. Driving the controller directly, every field is set
correctly and every method works; what was missing was the four lines in
main.py that call them. So the click here is a REAL MOUSEBUTTONDOWN posted into
main()'s own event pump, at the on-screen position of a model the game itself
says is eligible - and if the chain has no branch for it, nothing happens.

WHAT IS STAGED, and why each:
  * the Aspect Host detachment (no shipped list fields it);
  * the hazard step itself - a MockAgent run does not produce a Fall Back
    within 6" of Howling Banshees inside a fixed frame budget, so a passive
    counter would report zero and look like a pass. It is opened through the
    controller's own effect, which is the call use() makes once the CP is paid.
Everything after that is the real thing: the real dice panel, selfplay's own
acknowledgement click, the real event chain, the real phase gate.

Usage:  python verify_aeldari_no_deadlock.py [map2] [frames]
        python verify_aeldari_no_deadlock.py map2 --neutralize
"""

import runpy
import sys

import pygame

from game import aspect_khaines_vengeance as akv
from game import detachments
from game.input_handler import InputManager
from game.renderer import Renderer

HUMAN = "Player 1"
OPEN_AT = 600          # frames in - well past the pre-game

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

state = {"frames": 0, "ctrl": None, "handler": None, "board": None,
         "opened_at": None, "busy_frames": 0, "resolved_at": None,
         "highlighted": 0, "clicks": 0, "phase_states": []}


# --- the detachment ---------------------------------------------------------
_real_apply = detachments.apply_to_config


def apply_to_config(*args, **kwargs):
    out = _real_apply(*args, **kwargs)
    from game import config
    config.ASPECT_HOST_PLAYERS = (HUMAN,)
    return out


detachments.apply_to_config = apply_to_config


# --- the live objects -------------------------------------------------------
_real_kv_init = akv.KhainesVengeanceController.__init__


def kv_init(self, *args, **kwargs):
    _real_kv_init(self, *args, **kwargs)
    state["ctrl"] = self


akv.KhainesVengeanceController.__init__ = kv_init

_real_handler_init = InputManager.__init__


def handler_init(self, *args, **kwargs):
    _real_handler_init(self, *args, **kwargs)
    state["handler"] = self


InputManager.__init__ = handler_init

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
    # Exactly what shipped: the step exists and blocks the phase, and nothing
    # in the chain can end it. BOTH halves, because either one alone leaves the
    # other still able to resolve it - half a pre-fix world proves nothing.
    akv.KhainesVengeanceController.on_dice_acknowledged = lambda self: None
    akv.KhainesVengeanceController.choose_damage_model = lambda self, model: None


# --- the click --------------------------------------------------------------
def screen_pos_of(model):
    """The on-screen pixel a human would click to pick `model`.

    The exact inverse of input_handler.token_at_event(): board inches ->
    native px -> the camera's visible/dest mapping -> plus the board offset.
    Verified by asking token_at_event() itself, so a wrong transform reports
    INCONCLUSIVE rather than a silent miss."""
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
    # the dice, and selfplay does not answer a prompt that belongs to the
    # HUMAN outside the pre-game - the documented harness limit. One left
    # unanswered therefore swallows every click from here on, including the
    # dice acknowledgement below. Declined (the last option) rather than
    # accepted, which is what selfplay does for Fire Overwatch and Starflare.
    decisions = getattr(ctrl, "decision_manager", None)
    if decisions is not None and getattr(decisions, "is_pending", False):
        options = list(getattr(decisions, "options", ()) or ())
        if options:
            state["declined"] = state.get("declined", 0) + 1
            decisions.choose(len(options) - 1)
        return events

    # THE ROLL. selfplay acknowledges a pending roll itself, but only
    # when its own earlier branches have not already claimed the frame -
    # measured, the hazard roll opened here sits unanswered for hundreds of
    # frames. So the probe posts the same click selfplay would: a real
    # MOUSEBUTTONDOWN outside the left panel, which is what main()'s dice
    # branch reads as "acknowledged".
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
    # selfplay clicks the board every frame to drive the game, and one of those
    # landing on another model would resolve the choice for the wrong reason.
    state["clicks"] += 1
    return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1}),
            pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": 1})]


_real_flip = pygame.display.flip


def flip(*args, **kwargs):
    _install_pump()
    state["frames"] += 1
    ctrl = state["ctrl"]
    frame = state["frames"]

    if ctrl is not None:
        tracker = getattr(ctrl, "turn_tracker", None)
        if tracker is not None:
            now = (tracker.battle_round, tracker.turn_owner, tracker.phase)
            if not state["phase_states"] or state["phase_states"][-1] != now:
                state["phase_states"].append(now)

        if frame == OPEN_AT and state["opened_at"] is None:
            victim = None
            for token in (ctrl.all_tokens or ()):
                squad = getattr(token, "squad", None)
                if (squad is not None and squad.owner != HUMAN
                        and len([m for m in squad.models if not m.is_dead()]) >= 3):
                    victim = squad
                    break
            if victim is not None:
                ctrl._pending[HUMAN] = victim
                ctrl._force_tests(None, HUMAN, [victim])
                state["opened_at"] = frame
                state["victim"] = victim.name
                state["phases_at_open"] = len(state["phase_states"])

        if state["opened_at"] is not None:
            if ctrl.is_busy or ctrl.pending_damage_choice is not None:
                state["busy_frames"] += 1
            elif state["resolved_at"] is None:
                state["resolved_at"] = frame

    return _real_flip(*args, **kwargs)


pygame.display.flip = flip

sys.argv = ["selfplay.py"] + (sys.argv[1:] or ["map2", "2500"])
runpy.run_module("selfplay", run_name="__main__")

print()
print("--- Khaine's Vengeance deadlock" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
if state["ctrl"] is None:
    print("  the controller was never built - INCONCLUSIVE")
    raise SystemExit(2)
if state["opened_at"] is None:
    print("  no victim to open the step on - INCONCLUSIVE")
    raise SystemExit(2)

after_open = len(state["phase_states"]) - state.get("phases_at_open", 0)
print("  hazard step opened at     : frame %d, on %s"
      % (state["opened_at"], state.get("victim")))
print("  frames the board drew the eligible models : %d" % state["highlighted"])
print("  real clicks: %d on the dice, %d on an eligible model"
      % (state.get("dice_clicks", 0), state["clicks"]))
print("  frames it stayed blocking : %d" % state["busy_frames"])
print("  resolved at               : %s"
      % (state["resolved_at"] if state["resolved_at"] else "NEVER"))
print("  phase changes AFTER it opened             : %d" % after_open)

print()
if state["resolved_at"] is None:
    print("  FAIL: the step never resolved - the phase is frozen (the reported hang)")
    raise SystemExit(1)
if not state["highlighted"]:
    print("  FAIL: it resolved, but the board never said which models were pickable")
    raise SystemExit(1)
print("  OK: the board showed the choice, a real click resolved it through the "
      "chain, and the game went on (%d phase changes after)" % after_open)
