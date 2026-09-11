"""Runtime proof through the REAL main() loop that the start of the Shooting
phase now waits for the END of the Movement phase.

WHY A RUNTIME PROBE
-------------------
What broke was ORDERING inside main.py's advance_turn_phase(), and no suite
drives main(). The `turn_tracker.phase == PHASE_SHOOTING` block ran BEFORE the
`phase_before == PHASE_MOVEMENT` block, so five abilities whose printed WHEN is
"in your Shooting phase" were offered ahead of the reactions to the phase that
had just ended. Reported as "Rapid ingress und eater plague overlays
ueberlappen sich" and reproduced from the game log
(logs/game_20260911_132318.log:506-518): Rapid Ingress accepted, its placement
open on the board and in the left panel, and Eater Plague rolling dice and
allocating five mortal wounds on top of it - with the dice not even
acknowledgeable until the decision underneath them was answered.

WHAT IS MEASURED, AND WHY NOTHING IS STAGED
-------------------------------------------
The discriminator is pure ORDER, and both halves of it happen on EVERY
Movement -> Shooting boundary regardless of what is on the board:

  * rapid_ingress_controller.offer() is called unconditionally (it no-ops and
    continues the chain when nothing qualifies - the common case); and
  * the five start-of-Shooting offers are raised unconditionally too.

So this probe stages NOTHING. It counts, per boundary, whether a
start-of-Shooting offer ran before or after the end-of-Movement reactions were
entered. Fixed: never before. Neutralized: always before.

It also records, opportunistically, what the report itself describes - whether
a dice roll was still pending when the Rapid Ingress window opened. That one
depends on Eater Plague actually finding a target in a MockAgent run, so it is
reported honestly as 0 when the battle never gets there rather than dressed up
as a pass.

The armies are the reported pairing (T'au Retaliation Cadre vs Death Guard) on
the reported map, so Eater Plague is on the table at all.

Harness traps this walks into deliberately (both documented in CLAUDE.md):
importing selfplay runs nothing because of its __main__ guard - hence runpy
with run_name="__main__"; and selfplay REPLACES pygame.event.get at import
time, so nothing here hooks the event pump.

Usage:  python verify_shooting_start_after_movement.py [map4 [frames]]
        python verify_shooting_start_after_movement.py map4 1200 --neutralize
"""

import runpy
import sys

from game import config, dice, mortal_wound_abilities as mwa, rapid_ingress
from game.turn import PHASE_SHOOTING, TurnTracker

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

# The reported pairing: Eater Plague belongs to Typhus, so Death Guard has to
# be on the table for the ability under discussion to exist at all.
config.PLAYER1_ARMY = "tau_retaliation"
config.PLAYER2_ARMY = "death_guard"

stats = {
    "shooting_boundaries": 0,
    "boundaries_where_a_start_offer_ran": 0,
    "start_offer_ran_BEFORE_the_movement_reactions": 0,
    "start_offer_ran_AFTER_them": 0,
    "boundaries_where_the_chain_parked_instead": 0,
    "dice_pending_when_the_ingress_window_opened": 0,
    "ingress_offers_entered": 0,
}
seen = []

live = {"tracker": None, "dice": None, "mortal": []}
cur = {"id": 0, "ingress": 0, "offers": 0, "prefix_fired": False}

_real_advance = TurnTracker.advance_phase
_real_tracker_init = TurnTracker.__init__
_real_dice_init = dice.DiceManager.__init__
_real_ingress_offer = rapid_ingress.RapidIngressController.offer

# The three that raise a dice roll and a mortal-wound allocation - the class of
# ability the report actually collided with. Each defines its own
# offer_at_shooting_phase, so each is patched.
OFFERERS = [mwa.EaterPlagueController, mwa.LivingLightningController,
            mwa.MatterAbsorptionController]
_real_offers = {c: c.offer_at_shooting_phase for c in OFFERERS}


def tracker_init(self, *args, **kwargs):
    out = _real_tracker_init(self, *args, **kwargs)
    live["tracker"] = self
    return out


def dice_init(self, *args, **kwargs):
    out = _real_dice_init(self, *args, **kwargs)
    live["dice"] = self
    return out


def dice_pending():
    d = live["dice"]
    return bool(d is not None and getattr(d, "pending_values", None))


def advance_phase(self):
    """The marker, and - under --neutralize - the pre-fix world itself.

    Called from the top of main()'s advance_turn_phase(), so this is the exact
    instant the clock becomes Shooting: before either of the two blocks runs.
    """
    out = _real_advance(self)
    if self.phase != PHASE_SHOOTING:
        return out
    if cur["id"] and cur["offers"] == 0:
        stats["boundaries_where_the_chain_parked_instead"] += 1
    cur["id"] += 1
    cur["ingress"] = 0
    cur["offers"] = 0
    cur["prefix_fired"] = False
    stats["shooting_boundaries"] += 1
    if NEUTRALIZE:
        # THE FAITHFUL PRE-FIX WORLD: the five offers raised the instant the
        # phase is entered, ahead of everything the Movement phase still owed.
        # Counted through the same note_offer() the fixed world goes through -
        # calling the real method directly would slip past the spy and report a
        # truthful-looking zero.
        cur["prefix_fired"] = True
        for controller in live["mortal"]:
            note_offer(type(controller).__name__)
            squads = {t.squad for t in controller._tokens() if t.squad is not None}
            _real_offers[type(controller)](controller, squads, self.turn_owner)
    return out


def note_offer(name):
    """Record ONE start-of-Shooting offer against the current boundary."""
    first = cur["offers"] == 0
    cur["offers"] += 1
    if not first:
        return
    stats["boundaries_where_a_start_offer_ran"] += 1
    if cur["ingress"] == 0:
        stats["start_offer_ran_BEFORE_the_movement_reactions"] += 1
        seen.append("boundary %d: %s ran before the Movement phase's own "
                    "reactions" % (cur["id"], name))
    else:
        stats["start_offer_ran_AFTER_them"] += 1


def ingress_offer(self, mover, decision_manager, on_resolved=None, **kwargs):
    cur["ingress"] += 1
    stats["ingress_offers_entered"] += 1
    if dice_pending():
        stats["dice_pending_when_the_ingress_window_opened"] += 1
        seen.append("boundary %d: a dice roll was still pending when the Rapid "
                    "Ingress window opened" % cur["id"])
    return _real_ingress_offer(self, mover, decision_manager,
                               on_resolved=on_resolved, **kwargs)


def make_offer_spy(cls):
    real = _real_offers[cls]

    def offer_at_shooting_phase(self, squads, player):
        if NEUTRALIZE and cur["prefix_fired"]:
            # Already raised (and already counted) above, in the pre-fix world.
            return False
        note_offer(cls.__name__)
        return real(self, squads, player)

    return offer_at_shooting_phase


def make_mortal_init(cls):
    real_init = cls.__init__

    def __init__(self, *args, **kwargs):
        out = real_init(self, *args, **kwargs)
        live["mortal"].append(self)
        return out

    return __init__


TurnTracker.advance_phase = advance_phase
TurnTracker.__init__ = tracker_init
dice.DiceManager.__init__ = dice_init
rapid_ingress.RapidIngressController.offer = ingress_offer
for _cls in OFFERERS:
    _cls.offer_at_shooting_phase = make_offer_spy(_cls)
    _cls.__init__ = make_mortal_init(_cls)

sys.argv = ["selfplay.py"] + (sys.argv[1:] or ["map4", "1200"])
runpy.run_module("selfplay", run_name="__main__")

print()
print("--- start-of-Shooting ordering spy"
      + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
for key, value in stats.items():
    print("  %-48s %s" % (key, value))
for line in seen[:6]:
    print("    " + line)
if stats["shooting_boundaries"] == 0:
    print("  INCONCLUSIVE: the battle never entered a Shooting phase - give it "
          "more frames.")
