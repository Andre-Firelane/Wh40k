"""Runtime proof through the REAL main() loop that ONE switch stops the AI.

THE REPORTED BUG. User, after a game played with the red corner dot off:
"Protokoll of undying legions wurde wieder automatisch ausgefuehrt, obwohl KI
Modus aus war." Measured in logs/game_20260904_174253.log - "auto-play OFF" at
line 17, the human then hand-placed all eight of Player 2's units, and at line
175 a CP was still spent on that Stratagem with nobody having clicked anything.
Auto-play only ever gated ai/agent_driver.py's frame tick; the ~83
`auto_players` gates inside the ability and Stratagem controllers listened to
nothing at all.

"Built but never FED" has shipped in this repo six times, and a source guard
only shows that a call is written down - so this drives selfplay.py's real
main() loop and:

  1. CLICKS the new board switch at the coordinates main() itself drew it at,
     and checks the mode really flipped (not a rect computed twice);
  2. asks the LIVE controller main() built - not a fresh one - whether it would
     fire, in both modes, against a real Necron unit that has really lost
     models on the real board.

IT STAGES THE LOSSES ITSELF, deliberately. Over thousands of MockAgent frames
"a Necron unit lost models to an enemy attack while a human watched" does not
reliably happen, so a passive counter would report 0 and look exactly like a
pass - the documented harness limit this repo has been bitten by before. Every
other link in the chain is real: the controller, its auto_players view, the CP
ledger, the DecisionManager, main()'s own wiring.

Harness trap this walks into deliberately (documented in CLAUDE.md): importing
selfplay runs nothing because of its __main__ guard, so it goes through runpy.

Usage:  python verify_ai_mode_switch.py [map2]
        python verify_ai_mode_switch.py map2 --neutralize
"""

import runpy
import sys

import pygame

from game import ai_mode, protocol_undying_legions
from game.ui import ai_busy_badge

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

if NEUTRALIZE:
    # THE PRE-FIX WORLD: the gates hold a frozen set again, so the switch
    # cannot reach them. Faithful rather than one-line - the members are still
    # right, and the mode is still flipped; only the membership stops being
    # live, which is exactly what was wrong.
    class _Frozen(ai_mode.AutoAnswerPlayers):
        """Members frozen, mode ignored - the world before the fix."""
        def __contains__(self, player):
            return player in self.members

        def __iter__(self):
            return iter(sorted(self.members))

        def __len__(self):
            return len(self.members)

        def __bool__(self):
            return bool(self.members)

        def __getitem__(self, index):
            return sorted(self.members)[index]

    ai_mode.players = lambda auto_players: (
        auto_players if isinstance(auto_players, _Frozen) else _Frozen(auto_players))

state = {"toggle_rect": None, "clicked": None, "mode_after_click": None,
         "controller": None, "results": {}, "unit": None, "seen": None}

_real_draw_toggle = ai_busy_badge.draw_ai_mode_toggle
_real_ul_init = protocol_undying_legions.UndyingLegionsController.__init__


def draw_toggle(surface, board_rect, on, font, mouse_pos=None, avoid_rects=()):
    # selfplay REPLACES pygame.event.get wholesale at import time, so a wrapper
    # installed before runpy is simply overwritten. Installing it from here -
    # the first frame the switch draws, by which point selfplay's own pump is
    # in place - wraps the real one instead of racing it.
    _install_pump()
    rect = _real_draw_toggle(surface, board_rect, on, font, mouse_pos, avoid_rects)
    if state["toggle_rect"] is None:
        state["toggle_rect"] = rect.copy()
        state["seen"] = _frames["n"]
    return rect


def ul_init(self, *args, **kwargs):
    _real_ul_init(self, *args, **kwargs)
    state["controller"] = self


ai_busy_badge.draw_ai_mode_toggle = draw_toggle
protocol_undying_legions.UndyingLegionsController.__init__ = ul_init

_frames = {"n": 0}
_pump = {"real": None}


def _install_pump():
    if _pump["real"] is None:
        _pump["real"] = pygame.event.get
        pygame.event.get = event_get


def _necron_unit():
    """A real Necron unit off the real board that has lost models.

    Losses are staged (see the module docstring); everything else - the squad,
    its owner, the tokens - is whatever main() built."""
    from game import awakened_dynasty
    controller = state["controller"]
    if controller is None or controller.game_state is None:
        state["stage_note"] = "no controller/game_state"
        return None
    squads = {t.squad for t in controller.game_state.tokens if t.squad is not None}
    state["stage_note"] = "%d squads on the board" % len(squads)
    # The controller's OWN target predicate decides eligibility, so this cannot
    # drift from what the Stratagem really accepts.
    for squad in sorted(squads, key=lambda s: (-len(s.models), s.name)):
        if squad.owner != "Player 2" or len(squad.models) < 3:
            continue
        if not awakened_dynasty.stratagem_target_ok(squad):
            continue
        for model in squad.models[:2]:
            model.current_wounds = 0
        controller.game_state.remove_dead_models()
        state["stage_note"] = "staged"
        return squad
    return None


def _ask(label):
    """Would the live controller fire by itself, or ask?"""
    controller = state["controller"]
    squad = state["unit"]
    if controller is None or squad is None:
        state["results"][label] = "no unit staged"
        return
    manager = controller.decision_manager
    # Staged like the losses, and for the same reason: by the time the probe
    # gets here the AI has spent its Command Points on the real game, and an
    # unaffordable Stratagem is refused before the mode is ever consulted -
    # which would look exactly like the mode working.
    controller.stratagem_controller.command_points.cp[squad.owner] = 5
    controller.stratagem_controller.used_this_phase = type(
        controller.stratagem_controller.used_this_phase)()
    # A fired Stratagem leaves its D3 pending, and can_use() refuses while one
    # is - so the second measurement would be refused for a reason that has
    # nothing to do with the mode, and would read as a pass.
    controller._pending = None
    if controller.dice_manager is not None and controller.dice_manager.is_pending:
        controller.dice_manager.acknowledge()
    cp_before = controller.stratagem_controller.command_points.cp.get(squad.owner)
    offered = controller.maybe_offer(squad)
    prompted = manager is not None and manager.is_pending
    cp_after = controller.stratagem_controller.command_points.cp.get(squad.owner)
    state["results"][label] = (
        f"offered={offered} prompted={prompted} cp {cp_before}->{cp_after}")
    if prompted:
        manager.choose(len(manager.options) - 1)   # decline, leave the game clean


def event_get(*args, **kwargs):
    _frames["n"] += 1
    events = list(_pump["real"](*args, **kwargs))
    if state["seen"] is None:
        return events
    # Scheduled RELATIVE to the frame the switch first drew: the pre-game runs
    # first, so a fixed frame number fires before anything exists - which is
    # exactly the silent zero this probe is built to avoid.
    n = _frames["n"] - state["seen"]
    if n == 2:
        # REPLACING selfplay's own events on the frames under test: it clicks
        # the board every frame to drive the game, and one of those landing on
        # the switch would be mistaken for this probe's click.
        state["mode_before_click"] = ai_mode.enabled()
        return [pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                   {"pos": state["toggle_rect"].center, "button": 1})]
    if n == 3:
        state["clicked"] = True
        state["mode_after_click"] = ai_mode.enabled()
        # The mode has to go back ON or the pre-game never finishes: with it
        # off the AI deploys nothing, and nothing on the board means nothing to
        # ask about. That is itself the fix working.
        ai_mode.set_enabled(True)
        return []
    # From here the schedule is CONDITIONAL, not counted: the switch first
    # draws during the pre-game, when the board is still empty, so a fixed
    # frame number would stage nothing and report a silent zero.
    if state["unit"] is None and n > 3:
        state["unit"] = _necron_unit()
        return events
    if state["unit"] is not None and "mode ON " not in state["results"]:
        ai_mode.set_enabled(True)
        _ask("mode ON ")
        return []
    if state["unit"] is not None and "mode OFF" not in state["results"]:
        ai_mode.set_enabled(False)
        _ask("mode OFF")
        ai_mode.set_enabled(True)
        return []
    return events


sys.argv = [a for a in sys.argv if a != "--frames"]
if len(sys.argv) < 2:
    sys.argv.append("map2")
sys.argv.append("2500")

try:
    runpy.run_module("selfplay", run_name="__main__")
except SystemExit:
    pass

print("\n--- AI mode switch spy ---")
print("  switch drawn at        :", state["toggle_rect"])
print("  click posted           :", bool(state["clicked"]))
print("  mode before / after    : %s -> %s"
      % (state.get("mode_before_click"), state.get("mode_after_click")))
print("  staged unit            : %s (%s)" % (getattr(state["unit"], "name", None), state.get("stage_note")))
for label in ("mode ON ", "mode OFF"):
    print("  %s              : %s" % (label, state["results"].get(label, "not reached")))
