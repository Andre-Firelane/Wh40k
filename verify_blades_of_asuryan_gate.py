"""Runtime proof through the REAL main() loop that Blades of Asuryan's
[PISTOL] grant reaches rule 10.06's gate.

REPORTED: "ich konnte zwar mit asurmen schiessen, aber nicht mit dem rest meines
avengers squads. das umwandeln der waffen in pistol hat wohl nicht geklappt."

"Built but never FED" has hit this repo six times, and a source guard only shows
the call is written down. So this drives selfplay.py's real main() loop, waits
for a unit to really buy the Stratagem, and then asks the REAL module functions
about the REAL squad against the REAL token list.

WHAT IS STAGED, AND WHY - TWO facts, both named because a passive run measures
neither and would report 0 while looking exactly like a pass.

  1. THE PURCHASE. Blades of Asuryan is a panel BUTTON on the human's side, and
     this harness clicks no human panel button - measured first: 2500 frames,
     zero purchases. So the probe drives the LIVE controller main() built, with
     its real StratagemController and real CP, on a real squad off main()'s own
     token list. It goes through use(), so can_use()'s whole eligibility chain
     is real and a squad that should not qualify still cannot.
  2. THE ENGAGEMENT, which is the entire precondition of rule 10.06. Supplied
     as a token LIST with one synthetic adjacent enemy appended - nothing on the
     board moves, the list is an argument, the way verify_sudden_storm_wiring.py
     supplies "it Advanced".

Everything else is real: the weapons, the squad, the gate, and the per-weapon
half needs no staging at all.

THE ARMY IS THE REPORT'S OWN: armies/aeldari_guardian_battlehost.json fields
Guardian Battlehost, and it goes on PLAYER 1 - the human - because a question
about the human's units measures the AI's army if the list is on the wrong side
(the lesson the Necron audit's probes record).

Usage:  python verify_blades_of_asuryan_gate.py [map2 [frames]]
        python verify_blades_of_asuryan_gate.py map2 2500 --neutralize
"""

import copy
import runpy
import sys

import pygame

from game import config, guardian_blades_of_asuryan as gba, shooting
from game.turn import PHASE_SHOOTING, PHASES

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

config.PLAYER1_ARMY = "aeldari_guardian_battlehost"
config.PLAYER2_ARMY = "necrons"

stats = {"grants": 0, "ranged_weapons": 0,
         "weapons_the_gate_lets_fire": 0, "printed_pistols": 0,
         "engaged_probe_offers_close_quarters": 0,
         "engaged_probe_blocked": 0}
seen = []
live = {"tokens": None}

_real_types = shooting.available_shooting_types
_real_grant = gba.BladesOfAsuryanController._grant
_real_is_cq = shooting.is_close_quarters


def types(squad, all_tokens, movement_controller=None):
    live["tokens"] = all_tokens
    return _real_types(squad, all_tokens, movement_controller)


shooting.available_shooting_types = types

if NEUTRALIZE:
    # THE FAITHFUL PRE-FIX WORLD, and it has to be exactly this shape: the
    # grant still reaches the adjuster chain (that half always worked and was
    # always green), and ONLY the eligibility gate is blind to it. Switching
    # the Stratagem off outright would break both halves and prove something
    # weaker than the bug that was reported.
    def _printed_only(weapon, squad):
        return weapon.close_quarters or weapon.pistol

    shooting.is_close_quarters = _printed_only


def _ranged(squad):
    return [(m, w) for m in squad.models for w in m.weapons
            if getattr(w, "weapon_type", None) == "ranged"]


def _adjacent_enemy(squad):
    """A synthetic enemy model 0.1" from one of this unit's models.

    A COPY placed into a probe LIST - nothing on the board is touched, and the
    real token list is left exactly as main() holds it."""
    anchor = squad.models[0]
    for token in (live["tokens"] or ()):
        other = getattr(token, "squad", None)
        if other is not None and other.owner != squad.owner:
            ghost = copy.copy(token)
            ghost.x_in = anchor.x_in
            ghost.y_in = (anchor.y_in + anchor.radius_in
                          + getattr(ghost, "radius_in", 0.5) + 0.1)
            return ghost
    return None


def grant(self, controller, player, targets):
    out = _real_grant(self, controller, player, targets)
    for squad in targets or ():
        stats["grants"] += 1
        pairs = _ranged(squad)
        stats["ranged_weapons"] = max(stats["ranged_weapons"], len(pairs))
        printed = sum(1 for _m, w in pairs if w.close_quarters or w.pistol)
        stats["printed_pistols"] = max(stats["printed_pistols"], printed)
        allowed = sum(1 for _m, w in pairs
                      if shooting._weapon_eligible_for_type(
                          w, shooting.CLOSE_QUARTERS_SHOOTING, squad))
        stats["weapons_the_gate_lets_fire"] = max(
            stats["weapons_the_gate_lets_fire"], allowed)

        # The engaged half: the one supplied fact, as an argument.
        ghost = _adjacent_enemy(squad)
        probe = list(live["tokens"] or []) + ([ghost] if ghost is not None else [])
        offered = _real_types(squad, probe)
        if shooting.CLOSE_QUARTERS_SHOOTING in offered:
            stats["engaged_probe_offers_close_quarters"] += 1
        else:
            stats["engaged_probe_blocked"] += 1
        seen.append("%s: %d ranged weapon(s), %d printed [PISTOL]; the gate "
                    "lets %d fire; engaged -> %s"
                    % (squad.name, len(pairs), printed, allowed, offered))
    return out


gba.BladesOfAsuryanController._grant = grant

# --- staging fact 1: capture the LIVE controller and buy it once -----------
_real_ctrl_init = gba.BladesOfAsuryanController.__init__


def ctrl_init(self, *args, **kwargs):
    out = _real_ctrl_init(self, *args, **kwargs)
    live["controller"] = self
    return out


gba.BladesOfAsuryanController.__init__ = ctrl_init

_real_shoot_init = shooting.ShootingController.__init__


def shoot_init(self, *args, **kwargs):
    out = _real_shoot_init(self, *args, **kwargs)
    live["shooting"] = self
    return out


shooting.ShootingController.__init__ = shoot_init

_real_flip = pygame.display.flip


def flip(*args, **kwargs):
    """Buy it once, on a real squad, through the real controller.

    The clock is parked on the Shooting phase for the attempt because that is
    the Stratagem's printed WHEN and this harness reaches the human's Shooting
    phase rarely; the purchase itself still goes through use(), so every other
    eligibility clause is answered for real."""
    controller = live.get("controller")
    shoot = live.get("shooting")
    if controller is None or shoot is None or live.get("bought"):
        return _real_flip(*args, **kwargs)
    tracker = getattr(controller, "turn_tracker", None)
    tokens = getattr(shoot, "all_tokens", None)
    if tracker is None or not getattr(tracker, "started", False) or not tokens:
        return _real_flip(*args, **kwargs)
    live["tokens"] = tokens
    squads, seen_ids = [], set()
    for token in tokens:
        squad = getattr(token, "squad", None)
        if squad is None or id(squad) in seen_ids:
            continue
        seen_ids.add(id(squad))
        squads.append(squad)
    candidates = [s for s in squads if gba.eligible_unit(s)]
    if not candidates:
        return _real_flip(*args, **kwargs)
    target = candidates[0]
    phase_index, owner = tracker.phase_index, tracker.active_player
    tracker.phase_index = PHASES.index(PHASE_SHOOTING)
    tracker.active_player = target.owner
    try:
        if controller.use(target):
            live["bought"] = True
    finally:
        tracker.phase_index, tracker.active_player = phase_index, owner
    return _real_flip(*args, **kwargs)


pygame.display.flip = flip

sys.argv = ["selfplay.py"] + (sys.argv[1:] or ["map2", "2500"])
runpy.run_module("selfplay", run_name="__main__")

print()
print("--- Blades of Asuryan spy" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
for key, value in stats.items():
    print("  %-38s %s" % (key, value))
for line in seen[:6]:
    print("    " + line)
if not stats["grants"]:
    print("  INCONCLUSIVE: no unit bought the Stratagem - raise the frame budget.")
