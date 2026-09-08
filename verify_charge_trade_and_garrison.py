"""The two 2026-09-08 reports, measured in a REAL main() loop.

  1. "der grosse necron warrior squad hat den avatar of khaine gecharged" -
     does the trade actually reach the option the tactical layer is shown?
  2. "die necrons kommen immer nicht so richtig von ihrem home objective weg"
     - does the over-garrison pass now free a surplus unit off an objective an
     enemy is standing near?

A source guard says the call is THERE; only a running game says it arrives.
This repo has shipped seven "built but never fed" controllers, so both halves
are read off the live objects main() built, not off a fixture.

WHAT IS STAGED, AND WHY - one thing per half, both named rather than hidden:

  * THE CHARGE. Necron Warriors are declared against an enemy that is actually
    within charge range. Over a MockAgent run the AI's own movement rarely
    parks a 21-model blob 12" from anything in its own Charge phase (the
    documented harness limit), and a passive counter would have printed 0 and
    looked like a pass. The OPTION TEXT is then built by the real
    _handle_charge() against the real board.

  * THE GARRISON. MockAgent's plan_turn() gives every unit role "advance" and
    no coordinate, so _planned_garrisons() finds no garrison at all and the
    pass can never fire on its own. The reported turn's PLAN SHAPE is staged -
    two units ordered onto the home objective - and handed to the real
    _validate_turn_plan() with the live state and turn tracker.

Everything after those two facts is the shipped code: the real objectives,
the real Objective Control, the real correction, the real option text.

Usage:  python verify_charge_trade_and_garrison.py [map2 [frames]]
        python verify_charge_trade_and_garrison.py map2 900 --neutralize
"""

import runpy
import sys

import pygame

from ai import agent_driver
from game import config
from game.turn import PHASE_CHARGE, PHASES

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

# The reported pairing. Necrons on the AI side is the shipped default, and the
# Aeldari list is the one that fields the Avatar of Khaine.
config.PLAYER1_ARMY = "aeldari"
config.PLAYER2_ARMY = "necrons"

AI = "Player 2"
FRAMES = int(sys.argv[2]) if len(sys.argv) > 2 else 1200

stats = {"charge_options_seen": 0, "with_the_trade": 0, "without_it": 0,
         "garrison_runs": 0, "units_freed": 0, "kept": 0}
samples = []
live = {"state": None, "tracker": None, "did_garrison": False}

_real_flip = pygame.display.flip
_real_choose = agent_driver._choose
_real_note = agent_driver._charge_trade_note
_real_validate = agent_driver._validate_turn_plan
_real_held = agent_driver._held_objectives


class Log:
    def __init__(self):
        self.lines = []

    def add(self, line, **kwargs):
        self.lines.append(line)


def held(state, player):
    """The pre-fix world for report 2: an enemy anywhere within 12" took the
    objective out of the pass entirely, whatever its Objective Control."""
    out = _real_held(state, player)
    if not NEUTRALIZE:
        return out
    return [(o, t) for o, t in out
            if not agent_driver._enemies_near_objective(o, state, player)]


def note(squad, target):
    """The pre-fix world for report 1: the option carried the odds and no
    valuation at all, which is what squad_summary() still gives it."""
    return "" if NEUTRALIZE else _real_note(squad, target)


def choose(agent, all_tokens, turn_tracker, options, player, *args, **kwargs):
    """Read the option text the tactical layer is actually shown."""
    for option in options:
        if option.get("type") not in ("declare_charge", "charge_target"):
            continue
        stats["charge_options_seen"] += 1
        text = option.get("description", "")
        if "would remove about" in text:
            stats["with_the_trade"] += 1
            if len(samples) < 4:
                samples.append("CHARGE: " + text[text.index(" - it would remove"):][:150])
        else:
            stats["without_it"] += 1
            if len(samples) < 4:
                samples.append("CHARGE (no trade): " + text[-110:])
    return _real_choose(agent, all_tokens, turn_tracker, options, player, *args, **kwargs)


def validate(plan, player, state, turn_tracker, game_log=None, *args, **kwargs):
    """Keep the live board, so the garrison half can be measured against it."""
    live["state"] = state
    live["tracker"] = turn_tracker
    return _real_validate(plan, player, state, turn_tracker, game_log, *args, **kwargs)


def flip(*args, **kwargs):
    """Stage the two facts the harness does not produce, once each."""
    state, tracker = live["state"], live["tracker"]
    if state is None or tracker is None or not getattr(tracker, "started", False):
        return _real_flip(*args, **kwargs)

    # ---- report 2: the reported plan shape, against the live board --------
    if not live["did_garrison"]:
        squads = [s for s in state.all_squads() if s.owner == AI and s.models]
        home = next((o for o in state.objectives
                     if o.level_of_control(state.tokens).get(AI, 0) > 0), None)
        if home is not None and len(squads) >= 2:
            centre = agent_driver._objective_centre(home)
            # THE REPORTED CONDITION: something of the enemy's within 12" of
            # the objective. That is what used to switch the pass off, so
            # without it both worlds free the surplus and this measures
            # nothing. One enemy unit is walked over; nothing else is touched.
            near = [s for s in state.all_squads() if s.owner != AI and s.models]
            if near:
                for i, model in enumerate(near[0].models):
                    model.x_in = centre[0] - 2.0 + (i % 4) * 1.2
                    model.y_in = centre[1] + 9.0 + (i // 4) * 1.2
            on_it = sorted(
                (s for s in squads
                 if any(home.terrain_area.overlaps_model(m) for m in s.models)),
                key=lambda s: s.name)
            # Two units ordered to stand on the same objective - the shape the
            # reported turn plan had. Anything already near it is used, so the
            # coordinates are the board's and not invented.
            picked = (on_it + [s for s in squads if s not in on_it])[:2]
            plan = {"turn_intent": "staged", "unit_plans": {
                s.name: {"role": "hold", "position": centre, "target": None,
                         "priority": 5, "reason": "garrison"} for s in picked}}
            log = Log()
            _real_validate(plan, AI, state, tracker, log)
            stats["garrison_runs"] += 1
            live["did_garrison"] = True
            for s in picked:
                entry = plan["unit_plans"][s.name]
                if entry["role"] == "advance" and entry["position"] is None:
                    stats["units_freed"] += 1
                else:
                    stats["kept"] += 1
            threat = dict((o.name, t) for o, t
                          in agent_driver._held_objectives(state, AI)).get(home.name)
            samples.append("GARRISON on %s (threat OC %s): %s"
                           % (home.name, threat,
                              "; ".join("%s -> %s" % (s.name, plan["unit_plans"][s.name]["role"])
                                        for s in picked)))
            for line in log.lines:
                if "14.01-14.02" in line:
                    samples.append("  " + line[:150])

    # ---- report 1: put the AI in its Charge phase next to something -------
    if stats["charge_options_seen"] == 0 and tracker.turn_owner == AI:
        enemies = [s for s in state.all_squads() if s.owner != AI and s.models]
        mine = [s for s in state.all_squads()
                if s.owner == AI and s.models and len(s.models) > 5]
        if enemies and mine:
            target = max(enemies, key=lambda s: len(s.models))
            squad = mine[0]
            anchor = target.models[0]
            for i, model in enumerate(squad.models):
                model.x_in = anchor.x_in - 4.0 + (i % 5) * 1.4
                model.y_in = anchor.y_in - 7.0 + (i // 5) * 1.4
            tracker.phase_index = PHASES.index(PHASE_CHARGE)
    return _real_flip(*args, **kwargs)


agent_driver._charge_trade_note = note
agent_driver._held_objectives = held
agent_driver._choose = choose
agent_driver._validate_turn_plan = validate
pygame.display.flip = flip

sys.argv = [sys.argv[0]] + ([sys.argv[1]] if len(sys.argv) > 1 else ["map2"]) + [str(FRAMES)]
try:
    runpy.run_module("selfplay", run_name="__main__")
except SystemExit:
    pass

print()
print("=" * 74)
print("REPORT 1 - the charge option the tactical layer is shown")
print("=" * 74)
print("  charge options seen        : %d" % stats["charge_options_seen"])
print("  ...carrying the trade      : %d" % stats["with_the_trade"])
print("  ...carrying only the odds  : %d" % stats["without_it"])
print()
print("=" * 74)
print("REPORT 2 - the over-garrison pass on an objective an enemy is near")
print("=" * 74)
print("  passes run                 : %d" % stats["garrison_runs"])
print("  units freed off it         : %d" % stats["units_freed"])
print("  units kept on it           : %d" % stats["kept"])
print()
for line in samples:
    print("  " + line[:190])
print()
if stats["charge_options_seen"] == 0:
    print("INCONCLUSIVE: no charge option was ever built - raise the frame budget.")
    raise SystemExit(2)
verdict = (stats["with_the_trade"] > 0 and stats["units_freed"] > 0)
print("VERDICT:", "both halves arrive in a real game" if verdict
      else "at least one half did NOT arrive (this is the reported behaviour)")
raise SystemExit(0 if verdict != NEUTRALIZE else 1)
