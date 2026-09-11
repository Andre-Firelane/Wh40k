"""Runtime proof through the REAL main() loop that the game now SAYS the AI is
waiting on a Retro-thrusters move.

WHY A RUNTIME PROBE
-------------------
Nothing here was a rules bug. ai/agent_driver.py holds its own turn-end open
while the opponent still owes an end-of-Fight-phase Retro-thrusters decision -
correctly, rule 12.04 makes the Fight step shared - and the only sign of it was
one line in the game log. Reported as "Zug 3 KI macht nichts mehr nach Fight
Step. ich musste end of turn anklicken", and the log shows exactly that
(logs/game_20260911_132318.log:1067 and :1447, each followed immediately by
"Player 2's turn ends."): the human clicked End Turn, and the free 6" move went
away without a word.

The three halves added are all WIRING - a panel argument, a renderer call, and
a second reason on the End Turn warning - and this repo has shipped
"built but never FED" eight times. A source guard shows the call is written;
only a real frame shows it RUNS.

WHAT IS STAGED, AND WHY
-----------------------
ONE fact: that a unit owes the move at all. The window opens at the end of a
Fight phase for a unit with The Twin Lance's Retro-thrusters, and a MockAgent
run reaches neither in a sane frame budget (the documented harness limit) - a
passive counter would report 0 and read like a pass. So pending_squads() is
made to name a real Player 1 squad off the live board. Everything measured
after that is the real thing: main()'s own render, the real ActionPanel, the
real Renderer, and the real End Turn gate.

Usage:  python verify_retro_thrusters_stall.py [map2 [frames]]
        python verify_retro_thrusters_stall.py map2 900 --neutralize
"""

import inspect
import runpy
import sys

from game import retro_thrusters
from game.ui import action_panel as ap
from game.ui import fight_warning_overlay as fwo
from game import renderer as rnd

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

HUMAN = "Player 1"

stats = {
    "frames_with_a_unit_owing_the_move": 0,
    "panel_got_the_controller_in_the_right_slot": 0,
    "panel_got_something_else_there": 0,
    "panel_reached_the_fight_step_status": 0,
    "panel_named_the_unit": 0,
    "board_ringed_the_unit": 0,
    "end_turn_gate_asked_for_the_reason": 0,
    "end_turn_gate_raised_on_it": 0,
}
seen = []
live = {"squad": None, "tokens": None}

_real_pending = retro_thrusters.RetroThrustersController.pending_squads
_real_panel_hint = ap.ActionPanel._draw_retro_thrusters_pending
_real_panel_draw = ap.ActionPanel.draw
_real_fight_status = ap.ActionPanel._draw_fight_step_status
_DRAW_SIG = inspect.signature(_real_panel_draw)
_real_ring = rnd.Renderer.draw_retro_thrusters_pending
_real_warn = fwo.FightWarningOverlay.warn_once


def pending_squads(self, owner=None):
    """Stage the window: one real Player 1 squad off the live board.

    The controller itself is untouched - this only answers the question main.py
    asks it, which is the fact the harness cannot reach on its own.
    """
    real = _real_pending(self, owner)
    if real:
        return real
    if live["squad"] is None:
        for token in getattr(self, "all_tokens", None) or live["tokens"] or ():
            squad = getattr(token, "squad", None)
            if squad is not None and squad.owner == HUMAN:
                live["squad"] = squad
                break
    squad = live["squad"]
    if squad is None:
        return real
    if owner is not None and owner != squad.owner:
        return real
    stats["frames_with_a_unit_owing_the_move"] += 1
    return [squad]


def panel_draw(self, *args, **kwargs):
    """THE POSITIONAL CHAIN. action_panel.draw() takes ~80 parameters and is
    called positionally for the first ten of them; this file carries the scar
    of a parameter added to two of three signatures. Binding the real signature
    says which ARGUMENT landed on retro_thrusters_controller, which is the one
    thing a source guard cannot."""
    try:
        bound = _DRAW_SIG.bind(self, *args, **kwargs)
        got = bound.arguments.get("retro_thrusters_controller")
    except TypeError:
        got = None
    if isinstance(got, retro_thrusters.RetroThrustersController):
        stats["panel_got_the_controller_in_the_right_slot"] += 1
    else:
        stats["panel_got_something_else_there"] += 1
    return _real_panel_draw(self, *args, **kwargs)


def fight_status(self, *args, **kwargs):
    stats["panel_reached_the_fight_step_status"] += 1
    return _real_fight_status(self, *args, **kwargs)


def panel_hint(self, surface, rect, button_width, controller, text_y):
    if NEUTRALIZE:
        # THE PRE-FIX WORLD: the panel had no hint to draw. The DONE branch
        # wrote "Fight step complete." over an open decision and the
        # alternation branch said nothing at all - so nothing named the unit,
        # which is what is being counted here.
        return text_y
    stats["panel_named_the_unit"] += 1
    return _real_panel_hint(self, surface, rect, button_width, controller, text_y)


def ring(self, surface, board, squads):
    if NEUTRALIZE:
        return None  # the board drew no ring at all
    if squads:
        stats["board_ringed_the_unit"] += 1
    return _real_ring(self, surface, board, squads)


def warn_once(self, unit_names, retro_names=()):
    if retro_names:
        stats["end_turn_gate_asked_for_the_reason"] += 1
    if NEUTRALIZE:
        # THE PRE-FIX WORLD: the gate did not ask for the second reason at all,
        # so a click with nothing but a Retro-thrusters move owing went
        # straight through and ended the turn.
        retro_names = ()
    out = _real_warn(self, unit_names, retro_names=retro_names)
    if out and not unit_names and retro_names:
        stats["end_turn_gate_raised_on_it"] += 1
        seen.append("End Turn intercepted on the Retro-thrusters reason alone: %s"
                    % list(retro_names))
    return out


retro_thrusters.RetroThrustersController.pending_squads = pending_squads
ap.ActionPanel._draw_retro_thrusters_pending = panel_hint
ap.ActionPanel.draw = panel_draw
ap.ActionPanel._draw_fight_step_status = fight_status
rnd.Renderer.draw_retro_thrusters_pending = ring
fwo.FightWarningOverlay.warn_once = warn_once

sys.argv = ["selfplay.py"] + (sys.argv[1:] or ["map2", "900"])
runpy.run_module("selfplay", run_name="__main__")

# The End Turn gate is only reached when a human actually clicks it, which this
# harness does not do outside the pre-game - so the last two numbers are driven
# here, through the REAL overlay, with the reason the REAL gate would hand it.
overlay = fwo.FightWarningOverlay()
warn_once(overlay, [], retro_names=[live["squad"].name] if live["squad"] else [])

print()
print("--- Retro-thrusters visibility spy"
      + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
for key, value in stats.items():
    print("  %-42s %s" % (key, value))
print("  %-42s %s" % ("the unit staged", live["squad"].name if live["squad"] else None))
for line in seen[:4]:
    print("    " + line)
if live["squad"] is None:
    print("  INCONCLUSIVE: no Player 1 squad was ever on the board.")
if stats["panel_reached_the_fight_step_status"] == 0:
    print("  NOTE: the panel never reached its Fight-step branch in this run, so"
          " the hint itself could not draw - the documented MockAgent limit. What"
          " this run proves about the panel is that the controller ARRIVES in the"
          " right slot; the hint's own pixels are covered by"
          " test_retro_thrusters_notice.py against the real panel.")
