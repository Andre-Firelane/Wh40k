"""Headless self-play harness for main()'s real loop.

Exists because every previous version of it lived in a scratch file and had to
be rebuilt from CLAUDE.md's description. The things that make a naive harness
stall - and that this one handles - are:

  * main()'s auto-play (Shift+A) only ever drives PLAYER 2. Player 1's phases
    have to be advanced by clicking "Next Phase", and ONLY during Player 1's
    turn: click it during Player 2's turn and the AI is skipped past its own
    phases before it can act, which looks exactly like an engine stall.
  * a pending dice roll blocks everything until it is acknowledged.
  * the modal overlays (turn start, turn plan, stratagem notice, WAAAGH!)
    swallow input until they are dismissed.
  * rule 03.01's pre-game sequence (game/pregame.py) runs BEFORE any of that
    and needs Player 1's own formations declared and units placed, or the run
    never reaches battle round 1 at all.
  * two offers that belong to the HUMAN but hold up PLAYER 2: Fire Overwatch
    (15.08) at the end of Player 2's Movement phase, and the Twin Lance's
    Retro-thrusters at the end of the Fight phase, which Player 2 now waits
    for by design. Both are declined below.

Rather than clicking blindly, the fake event source reads main()'s own locals
from the calling frame, so it only ever produces the one input the game is
actually waiting for.

Usage:  python selfplay.py [map_key] [frames] [--no-deployment]
Uses MockAgent - no API calls, no money.

WHY A RUN CAN STOP EARLY WITHOUT ANYTHING BEING BROKEN (measured while adding
the reactive Retaliation Cadre stratagems): outside the pre-game, nothing here
answers a DecisionManager break point that belongs to the HUMAN. The AI answers
only its own (ai/agent_driver.py's _maybe_resolve_decision() returns False for
any prompt whose player isn't its own), so a Player 1 prompt - Heroic
Intervention, Grav-Inhibitor Field, [LETHAL HITS], ... - sits forever with the
log going quiet, which is what the runs that "stall in a Shooting phase" have
always been. A pending damage-model pick (rule 06.02) does the same.

Answering them here (always option 0) WAS tried: it gets further, then runs far
slower - 3000 frames unfinished after six minutes, against about ninety seconds
as it stands. Doing that trade properly needs the damage-choice half as well,
and measuring it; that is its own piece of work. Until then: before reading a
quiet log as an engine hang, check decision_manager.is_pending.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

ARGS = [a for a in sys.argv[1:] if a != "--no-deployment"]
PREGAME = "--no-deployment" not in sys.argv[1:]
MAP_KEY = ARGS[0] if ARGS else "map2"
MAX_FRAMES = int(ARGS[1]) if len(ARGS) > 1 else 4000

pygame.init()

state = {"frames": 0, "armed": False}


def _click(pos):
    return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1}),
            pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": 1})]


def fake_events():
    """One synthetic input per frame, chosen from what main() is waiting on."""
    state["frames"] += 1
    if state["frames"] >= MAX_FRAMES:
        raise SystemExit(0)

    # Walk out to main()'s own frame. Not simply _getframe(1): the event hook
    # is installed as a lambda, so the immediate caller is that lambda, and
    # main() may be a frame or two further up.
    loc = {}
    frame = sys._getframe(1)
    while frame is not None:
        if "turn_tracker" in frame.f_locals:
            loc = frame.f_locals
            break
        frame = frame.f_back

    if not state["armed"]:
        # Shift+A: turn Player 2's auto-play on, once.
        state["armed"] = True
        return [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a, "mod": pygame.KMOD_LSHIFT,
                                                    "unicode": "A", "scancode": 4})]

    for name in ("turn_start_overlay", "turn_plan_overlay",
                 "stratagem_notice_overlay", "waaagh_notice_overlay"):
        overlay = loc.get(name)
        if overlay is not None and getattr(overlay, "is_pending", False):
            return _click((10, 10))

    dice_manager = loc.get("dice_manager")
    if dice_manager is not None and getattr(dice_manager, "is_pending", False):
        # NOT a click in the left panel: main()'s dice branch routes those to
        # the action panel (rule 15.02's Command Re-roll lives there) and only
        # acknowledges the roll for a click somewhere else. Clicking at (10,10)
        # here is what made an earlier version of this harness sit on a pending
        # roll forever, which looks exactly like an engine deadlock.
        surface = pygame.display.get_surface()
        w, h = surface.get_size() if surface else (1200, 800)
        return _click((w - 8, h - 8))

    # Rule 03.01: the pre-game sequence owns the game before battle round 1.
    # Placed after the overlay and dice branches on purpose - the two roll-offs
    # run THROUGH dice_manager, so those have to be serviced first. Player 2's
    # side is driven by main()'s own auto-play; this only answers for Player 1.
    pregame_ctrl = loc.get("pregame_controller")
    if pregame_ctrl is not None and getattr(pregame_ctrl, "is_active", False):
        decisions = loc.get("decision_manager")
        if decisions is not None and decisions.is_pending:
            overlay = loc.get("decision_overlay")
            rects = getattr(overlay, "_option_rects", None)
            if rects:
                return _click(rects[0].center)
            decisions.choose(0)
            return []
        if pregame_ctrl.state == "deploying" and pregame_ctrl.active_player == pregame_ctrl.human_player:
            # A unit has to be selected before "Auto-place this unit" exists.
            if pregame_ctrl.selected_unit is None:
                pending = pregame_ctrl.pending_units(pregame_ctrl.human_player)
                if pending:
                    pregame_ctrl.select_unit(pending[0])
                    return []
        panel = loc.get("action_panel")
        buttons = getattr(panel, "_buttons", [])
        if buttons:
            # The pre-game panel only ever offers legal choices, so the first
            # button is always a valid answer (declare/deploy/auto-place).
            return _click(buttons[0][0].center)
        return []

    # Rule 15.08 Fire Overwatch is offered to the HUMAN at the end of Player
    # 2's Movement phase and blocks everything until it is answered - a fourth
    # trap on top of the three in the module docstring, and one that stops the
    # run dead in Player 2's Shooting phase where it looks like an AI stall.
    # Decline it: the harness is here to exercise Player 2's own turn.
    overwatch_ctrl = loc.get("fire_overwatch_controller")
    if overwatch_ctrl is not None and getattr(overwatch_ctrl, "state", None) == "choosing_unit":
        panel = loc.get("action_panel")
        for rect, callback in reversed(getattr(panel, "_buttons", [])):
            if "decline" in getattr(callback, "__qualname__", "").lower():
                return _click(rect.center)
        overwatch_ctrl.decline()
        return []

    # Starflare Ignition System Enhancement (game/starflare_ignition.py):
    # offered to the HUMAN at the end of EVERY opponent turn once the bearer is
    # on the board and clear of Engagement Range - so unlike the one-off human
    # prompts in the module docstring, this one would stall every single run at
    # the first end-of-turn. Declined here (the last option is always "stay on
    # the battlefield"), which leaves the board exactly as it was: this harness
    # exists to exercise Player 2's turn, not to redeploy Player 1's army.
    decisions = loc.get("decision_manager")
    if decisions is not None and decisions.is_pending and "Starflare" in (decisions.prompt or ""):
        decisions.choose(len(decisions.options) - 1)
        return []

    # The Twin Lance's Retro-thrusters (game/retro_thrusters.py) is offered to
    # the HUMAN at the end of the Fight phase, and since battle round
    # 2026-08-16 Player 2 deliberately HOLDS its turn-end while that offer is
    # open - otherwise ending the turn skipped it, which is the bug that made
    # it wait. So an unanswered offer here stalls Player 2's turn for good.
    # Declined for the same reason Fire Overwatch above is: this harness is
    # here to exercise Player 2's turn, and Skip is exactly what a human who
    # does not want the move would click.
    retro_ctrl = loc.get("retro_thrusters_controller")
    if retro_ctrl is not None:
        for squad in retro_ctrl.pending_squads("Player 1"):
            retro_ctrl.decline(squad)

    # Only Player 1's own phases need advancing by hand - see the module
    # docstring for why doing it during Player 2's turn breaks the run.
    tracker = loc.get("turn_tracker")
    status_panel = loc.get("game_status_panel")
    if tracker is not None and tracker.started and tracker.turn_owner == "Player 1":
        rect = getattr(status_panel, "_button_rect", None) if status_panel else None
        if rect is not None:
            return _click(rect.center)
    return []


pygame.event.get = lambda *a, **k: fake_events()

from game import config

config.PREGAME_DEPLOYMENT = PREGAME

import main
from ai.mock_agent import MockAgent

# main() constructs a ClaudeAgent, which costs real money and needs a key.
# Self-play must never do either, so the class is swapped out before main()
# ever calls it.
main.ClaudeAgent = lambda *a, **k: MockAgent()

if __name__ == "__main__":
    try:
        main.main(MAP_KEY)
    except SystemExit:
        pass
    print(f"self-play {MAP_KEY} (pregame={PREGAME}): {state['frames']} frames, no exception")
