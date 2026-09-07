"""Runtime proof through the REAL main() loop that Wall of Mirrors is offered
to the right side, at the right moment, and that saying yes does something.

WHY A RUNTIME PROBE
-------------------
Both halves of this bug lived in main.py's ORDERING, which no suite drives.
advance_turn_phase() advances the clock FIRST and runs the end-of-Fight-phase
offers SECOND, so:

  * turn_tracker.turn_owner had already flipped, and the offer named the wrong
    player - reported as "Frage nach Wall of Mirrors kam am Anfang der Gegner
    Runde";
  * the controller's WHEN was a live `phase == PHASE_FIGHT` test, which by then
    can never hold, so accepting did nothing at all - "funktioniert auch nicht".

Before this, test_tau_detachment_stratagems.py exercised only
is_eligible_unit(); neither half was visible to it.

WHAT IS STAGED, AND WHY
-----------------------
ONE fact: that the battle reaches the end of a Fight phase at all. Measured on
this harness, T'au vs Necrons on map2 gets through exactly TWO phase advances
in 3000 frames - the Shooting phase alone outlives the budget, so the Fight
boundary is simply unreachable passively and a passive counter would report 0
and look like a pass (the documented MockAgent limit). So the probe parks the
live TurnTracker on the Fight phase once, and lets main()'s own
advance_turn_phase() run the boundary unmodified. Everything measured after
that - which player is asked, what the clock reads, whether the unit really
leaves the board - is the real thing.

The prompt is answered here too: the Kauyon list is on the HUMAN side, and this
harness answers no human prompt outside the pre-game.

Harness trap this walks into deliberately (documented in CLAUDE.md): importing
selfplay runs nothing because of its __main__ guard - hence runpy with
run_name="__main__". And selfplay REPLACES pygame.event.get at import time, so
the per-frame hook below goes on pygame.display.flip instead, which main()'s
own loop calls once per frame.

Usage:  python verify_wall_of_mirrors.py [map2 [frames]]
        python verify_wall_of_mirrors.py map2 900 --neutralize   # the report
"""

import runpy
import sys

import pygame

from game import config, kauyon_wall_of_mirrors as mirrors
from game.turn import PHASE_FIGHT, PHASES, TurnTracker

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

# The Kauyon list on the human side: with the AI having just fought, "end of
# your OPPONENT'S Fight phase" points at the human.
config.PLAYER1_ARMY = "tau"
config.PLAYER2_ARMY = "necrons"

KAUYON_SIDE = "Player 1"

stats = {"boundaries_staged": 0, "boundaries_measured": 0, "offers_made": 0,
         "asked_the_kauyon_side": 0, "asked_the_wrong_side": 0,
         "clock_had_already_moved_on": 0, "accepted": 0,
         "withdrew_to_reserves": 0}
seen = []
live = {"tracker": None}

_real_init = TurnTracker.__init__
_real_offer = mirrors.WallOfMirrorsController.offer_at_end_of_fight_phase
_real_flip = pygame.display.flip


def tracker_init(self, *args, **kwargs):
    out = _real_init(self, *args, **kwargs)
    live["tracker"] = self
    return out


def flip(*args, **kwargs):
    """Park the live clock on the Fight phase - see the docstring.

    Repeated a few times on purpose: ending one player's Fight phase ends
    their TURN, so the second staged boundary is the other player's. That is
    how a boundary belonging to the Kauyon side's OPPONENT is reached at all
    within a sane frame budget - the first player's own turn alone outlives it.
    WHICH boundary gets measured is decided in offer() below, not here, so
    both runs of this probe measure the same one.
    """
    tracker = live["tracker"]
    if (tracker is not None and getattr(tracker, "started", False)
            and stats["boundaries_staged"] < 4
            and tracker.phase != PHASE_FIGHT):
        tracker.phase_index = PHASES.index(PHASE_FIGHT)
        stats["boundaries_staged"] += 1
    return _real_flip(*args, **kwargs)


def offer(self, ending_player):
    # main.py passes mover_before in BOTH runs - the neutralisation below only
    # simulates what it used to read - so this is the same fact either way and
    # is what makes the two runs comparable. Only the boundary that belongs to
    # the Kauyon side's OPPONENT is the one the printed WHEN is about.
    measured = ending_player != KAUYON_SIDE
    if not measured:
        return _real_offer(self, ending_player)
    stats["boundaries_measured"] += 1
    if NEUTRALIZE:
        # THE FAITHFUL PRE-FIX WORLD, and it needs BOTH halves: main.py read
        # the already-flipped turn_owner (so the argument named the other
        # side), and can_use() asked the live clock. Restoring only one would
        # prove something weaker than the two reports together.
        others = [p for p in self._players() if p != ending_player]
        ending_player = others[0] if others else ending_player
    out = _real_offer(self, ending_player)
    if not out:
        return out
    stats["offers_made"] += 1
    asked = self.decision_manager.player
    if asked == KAUYON_SIDE:
        stats["asked_the_kauyon_side"] += 1
    else:
        stats["asked_the_wrong_side"] += 1
    if self.turn_tracker.phase != PHASE_FIGHT:
        stats["clock_had_already_moved_on"] += 1

    options = self.decision_manager.options
    index = next((i for i, o in enumerate(options) if o.get("squad") is not None), None)
    if index is None:
        return out
    squad = options[index]["squad"]
    before = len([t for t in self.all_tokens if getattr(t, "squad", None) is squad])
    if NEUTRALIZE:
        class _Shut:
            def is_open(self, player=None):
                return False
        real_window, self._window = self._window, _Shut()
        try:
            self.decision_manager.choose(index)
        finally:
            self._window = real_window
    else:
        self.decision_manager.choose(index)
    stats["accepted"] += 1
    after = len([t for t in self.all_tokens if getattr(t, "squad", None) is squad])
    in_reserves = squad in getattr(self.game_state, "reserves", ())
    if in_reserves and after == 0:
        stats["withdrew_to_reserves"] += 1
    seen.append("%s asked (clock reads %r); %s: tokens %d -> %d, in reserves=%s"
                % (asked, self.turn_tracker.phase, squad.name, before, after,
                   in_reserves))
    return out


TurnTracker.__init__ = tracker_init
pygame.display.flip = flip
mirrors.WallOfMirrorsController.offer_at_end_of_fight_phase = offer

sys.argv = ["selfplay.py"] + (sys.argv[1:] or ["map2", "900"])
runpy.run_module("selfplay", run_name="__main__")

print()
print("--- Wall of Mirrors spy" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
for key, value in stats.items():
    print("  %-28s %s" % (key, value))
for line in seen[:6]:
    print("    " + line)
