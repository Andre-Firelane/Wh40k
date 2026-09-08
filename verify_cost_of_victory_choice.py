"""Runtime proof through the REAL main() loop that Cost of Victory lets the
player choose WHICH unit, on the board.

REPORTED: "cost of victory wird mir pauschal angeboten, aber ich habe 3 guardian
squads. ich kann nicht waehlen welchen squad zurueck in reserve schicken will.
es muss auf dem feld angeklickt werden."

WHY A RUNTIME PROBE. A source guard shows the call is THERE; this repo has been
caught six times by a controller that was built and never FED. What is measured
here is the prompt main() actually raises, against the tokens main() actually
holds, with unit_pick.pending() - the same function the panel, the board
highlight and the click branch read - deciding whether it can be clicked.

THE ARMY IS THE REPORT'S OWN. armies/aeldari_guardian_battlehost.json fields
Guardian Battlehost and has exactly THREE GUARDIANS units (two Guardian
Defenders and one Storm Guardians, each with characters attached), so the
staging is a shipped list rather than a scene invented to suit the probe. It
goes on PLAYER 1 - the human - because "end of your opponent's Fight phase"
offers the side that did NOT just fight, and a question about the human's
prompts measures the AI's army if the list is put on the wrong side (the
lesson the Necron audit's three probes record).

WHAT IS STAGED, AND WHY. ONE fact: that the battle reaches the end of a Fight
phase at all. On this harness the Shooting phase alone outlives a sane frame
budget, so the Fight boundary is unreachable passively and a passive counter
would report 0 and look like a pass - the documented MockAgent limit. So the
live TurnTracker is parked on the Fight phase, and main()'s own
advance_turn_phase() runs the boundary unmodified. Everything after that - who
is asked, how many units the prompt names, whether it is clickable, and which
unit a click resolves to - is the real thing.

Harness traps this walks into deliberately (both documented in CLAUDE.md):
importing selfplay runs nothing because of its __main__ guard, hence runpy with
run_name="__main__"; and selfplay REPLACES pygame.event.get at import time, so
the per-frame hook goes on pygame.display.flip, which main()'s loop calls once
per frame.

Usage:  python verify_cost_of_victory_choice.py [map2 [frames]]
        python verify_cost_of_victory_choice.py map2 900 --neutralize
"""

import runpy
import sys

import pygame

from game import config, guardian_cost_of_victory as gcv, unit_pick
from game.turn import PHASE_FIGHT, PHASES, TurnTracker

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

# The Guardian Battlehost list on the HUMAN side - see the docstring.
config.PLAYER1_ARMY = "aeldari_guardian_battlehost"
config.PLAYER2_ARMY = "necrons"

GUARDIAN_SIDE = "Player 1"

stats = {"boundaries_staged": 0, "boundaries_measured": 0, "offers_made": 0,
         "eligible_units_on_the_board": 0, "units_named_by_the_prompt": 0,
         "answerable_by_clicking_the_board": 0, "units_ringed": 0,
         "clicked_a_unit_that_was_not_the_first": 0,
         "the_clicked_unit_withdrew": 0, "a_different_unit_withdrew": 0}
seen = []
live = {"tracker": None}

_real_init = TurnTracker.__init__
_real_offer = gcv.CostOfVictoryController.offer_at_end_of_fight_phase
_real_flip = pygame.display.flip


def tracker_init(self, *args, **kwargs):
    out = _real_init(self, *args, **kwargs)
    live["tracker"] = self
    return out


def flip(*args, **kwargs):
    """Park the live clock on the Fight phase - see the docstring.

    Repeated a few times on purpose: ending one player's Fight phase ends
    their TURN, so the next staged boundary belongs to the other player. That
    is how a boundary belonging to the Guardian side's OPPONENT is reached at
    all inside a sane budget. WHICH boundary is measured is decided in offer()
    below, so both runs of this probe measure the same one."""
    tracker = live["tracker"]
    if (tracker is not None and getattr(tracker, "started", False)
            and stats["boundaries_staged"] < 4
            and tracker.phase != PHASE_FIGHT):
        tracker.phase_index = PHASES.index(PHASE_FIGHT)
        stats["boundaries_staged"] += 1
    return _real_flip(*args, **kwargs)


def _old_offer(self, squads, ending_player):
    """THE PRE-FIX WORLD, byte for byte as game/guardian_cost_of_victory.py
    said it: one prompt about whichever unit sorted first, accept or decline."""
    for squad in sorted((s for s in squads if s.owner != ending_player),
                        key=lambda s: (str(s.owner), s.name)):
        self._window.arm(squad.owner)
        if not self.can_use(squad):
            self._window.close()
            continue
        if squad.owner in self.auto_players or self.decision_manager is None:
            self._window.close()
            return False
        self.decision_manager.request(
            squad.owner,
            "%s (%d CP): pull %s into Strategic Reserves and bring back its "
            "destroyed models?"
            % (gcv.COST_OF_VICTORY_NAME, gcv.COST_OF_VICTORY_CP, squad.name),
            [("Use (%d CP)" % gcv.COST_OF_VICTORY_CP,
              (lambda s=squad: self.use(s))),
             ("Decline", lambda: None)],
            is_stratagem=True,
        )
        return True
    return False


def offer(self, squads, ending_player):
    # Only the boundary belonging to the Guardian side's OPPONENT is the one
    # the printed WHEN is about, and it is the same fact in both runs - which
    # is what makes them comparable.
    if ending_player == GUARDIAN_SIDE:
        return _real_offer(self, squads, ending_player)
    stats["boundaries_measured"] += 1

    on_board = {id(getattr(t, "squad", None)) for t in (self.all_tokens or ())
                if not t.is_dead()}
    eligible = [s for s in squads
                if s.owner != ending_player and id(s) in on_board
                and gcv.eligible_unit(s)]
    stats["eligible_units_on_the_board"] = max(
        stats["eligible_units_on_the_board"], len(eligible))

    out = (_old_offer if NEUTRALIZE else _real_offer)(self, squads, ending_player)
    if not out:
        return out
    stats["offers_made"] += 1

    options = self.decision_manager.options
    named = [o["squad"] for o in options if o.get("squad") is not None]
    stats["units_named_by_the_prompt"] = max(
        stats["units_named_by_the_prompt"], len(named))

    pick = unit_pick.pending(self.decision_manager, self.all_tokens)
    if pick is None:
        seen.append("prompt %r -> NOT a board pick; %d unit(s) named, "
                    "%d eligible on the board"
                    % (self.decision_manager.prompt[:70], len(named),
                       len(eligible)))
        return out
    stats["answerable_by_clicking_the_board"] += 1
    stats["units_ringed"] = max(stats["units_ringed"], len(pick.squads))

    # Click the LAST candidate, not the first: the pre-fix world could only
    # ever have offered the first, so resolving a different one is the whole
    # of what the report asked for.
    target = pick.squads[-1]
    first = pick.squads[0]
    if target is not first:
        stats["clicked_a_unit_that_was_not_the_first"] += 1
    before = len([t for t in self.all_tokens if getattr(t, "squad", None) is target])
    pick.pick(target)
    after = len([t for t in self.all_tokens if getattr(t, "squad", None) is target])
    reserves = getattr(self.game_state, "reserves", ())
    if target in reserves:
        stats["the_clicked_unit_withdrew"] += 1
    if any(s in reserves for s in pick.squads if s is not target):
        stats["a_different_unit_withdrew"] += 1
    seen.append("%d ringed %s -> clicked %r (tokens %d -> %d), in reserves=%s"
                % (len(pick.squads), [s.name for s in pick.squads],
                   target.name, before, after, target in reserves))
    return out


TurnTracker.__init__ = tracker_init
pygame.display.flip = flip
gcv.CostOfVictoryController.offer_at_end_of_fight_phase = offer

sys.argv = ["selfplay.py"] + (sys.argv[1:] or ["map2", "1500"])
runpy.run_module("selfplay", run_name="__main__")

print()
print("--- Cost of Victory spy" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
for key, value in stats.items():
    print("  %-38s %s" % (key, value))
for line in seen[:6]:
    print("    " + line)
if not stats["boundaries_measured"]:
    print("  INCONCLUSIVE: no opponent Fight-phase boundary was reached - "
          "raise the frame budget.")
