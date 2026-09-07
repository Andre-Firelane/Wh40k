"""Runtime proof through the REAL main() loop that Mont'ka's Killing Blow
reaches rule 10.05's Advance gate.

WHAT WAS WRONG. Killing Blow grants army-wide [ASSAULT] in the detachment's
battle rounds, and [ASSAULT] is read in two unrelated places: the damage chain
(ShootingController._adjusted_weapon(), which always worked and was always
green) and coldstar.weapon_has_assault(), reached from
shooting.available_shooting_types() - the ONLY thing deciding whether a unit
that Advanced may shoot at all. The second was blind to it, because the rule is
gated on the battle round and that function is handed only (weapon, squad).
Measured on the shipped tau_montka roster before the fix: Killing Blow active
for all 14 of its units, granting [ASSAULT] to 102 of their 151 ranged weapons,
of which the gate could see NONE.

It is closed by a flag - Squad.montka_killing_blow, stamped once per phase
change by montka.refresh_killing_blow() from the same is_active() the chain
uses. A flag has its own failure mode, and it is the one this repo has been
caught by six times: honoured by the reader and set by nothing. A source guard
only shows the call is written down. So this drives the real loop.

WHAT IS STAGED, and why each thing has to be. The MockAgent cannot be relied on
to buy nothing, Advance, and shoot in one activation inside a frame budget -
the documented limit of this harness - so a passive counter would report 0 and
look exactly like a pass. What is staged is ONLY the "it Advanced" fact; the
detachment comes from the real list, the stamp comes from main()'s own
per-phase call, and the answer comes from the real module function asked about
the real squad against the real token list.

Harness trap walked into deliberately (CLAUDE.md): importing selfplay runs
nothing because of its __main__ guard, so this goes through runpy with
run_name="__main__".

Usage:  python verify_tau_montka_assault.py [map2] [frames]
        python verify_tau_montka_assault.py map2 --neutralize   # must report 0
"""

import runpy
import sys

from game import army_lists, coldstar, detachments, montka, shooting
from game.movement import MovementController

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

HUMAN = "Player 1"

stats = {"phases_stamped": 0, "units_stamped": 0,
         "advanced_and_offered": 0, "advanced_and_blocked": 0,
         "probe_offered": 0, "probe_blocked": 0}
live = {"tokens": None, "round": None, "squads": []}

_real_refresh = montka.refresh_killing_blow
_real_gate = coldstar.weapon_has_assault
_real_types = shooting.available_shooting_types


def refresh(squads, turn_tracker):
    """main()'s own per-phase stamp, watched rather than replaced.

    Counting here is what separates "the reader honours a flag" from "anything
    ever sets it" - the two halves a flag-based fix has to prove separately."""
    out = _real_refresh(squads, turn_tracker)
    stats["phases_stamped"] += 1
    live["round"] = getattr(turn_tracker, "battle_round", None)
    stamped = [s for s in (squads or ()) if getattr(s, "montka_killing_blow", False)]
    stats["units_stamped"] = max(stats["units_stamped"], len(stamped))
    # The squads come from HERE rather than only from available_shooting_types():
    # main() stamps on every phase change, but a run that never reaches a
    # Shooting phase never calls that function - and then the probe below would
    # have nothing to ask about and would report a truthful-looking zero.
    if squads:
        live["squads"] = list(squads)
    return out


def gate(weapon, squad):
    if NEUTRALIZE:
        # THE FAITHFUL PRE-FIX WORLD, and it has to be exactly this shape: the
        # grant still reaches the adjuster chain (that half always worked), and
        # ONLY rule 10.05's gate is blind to it. Neutralising the flag itself
        # would break both halves and prove something weaker than the bug.
        real = montka.grants_assault
        montka.grants_assault = lambda squad: False
        try:
            return _real_gate(weapon, squad)
        finally:
            montka.grants_assault = real
    return _real_gate(weapon, squad)


def types(squad, all_tokens, movement_controller=None):
    live["tokens"] = all_tokens
    out = _real_types(squad, all_tokens, movement_controller)
    advanced = (movement_controller is not None
                and squad in getattr(movement_controller, "advanced_squad_ids", ()))
    if advanced and getattr(squad, "montka_killing_blow", False):
        if shooting.ASSAULT_SHOOTING in out:
            stats["advanced_and_offered"] += 1
        else:
            stats["advanced_and_blocked"] += 1
    return out


montka.refresh_killing_blow = refresh
coldstar.weapon_has_assault = gate
shooting.available_shooting_types = types
# shooting.py imported the name directly, so rebind it there too.
shooting.weapon_has_assault = gate

# BOTH players field Mont'ka, so the loop cannot spend its whole budget on a
# side the rule does not touch. Wrapped rather than pre-set: apply_to_config()
# writes every detachment setting from scratch, so a flag set before it runs is
# simply erased.
_real_apply = detachments.apply_to_config


def apply_to_config(*args, **kwargs):
    out = _real_apply(*args, **kwargs)
    from game import config
    config.MONTKA_PLAYERS = ("Player 1", "Player 2")
    return out


detachments.apply_to_config = apply_to_config

# THE LIVE BOARD, captured from main()'s own MovementController rather than
# from a phase change. Measured on this roster: tau_montka reaches the end of
# the pre-game but not a single phase change inside any budget worth waiting
# for, where the default armies reach seven - so a probe that could only read
# the board through the per-phase stamp would report zeros and look exactly
# like a failure. (A/B'd: the stall is there with this session's gate term
# removed too, so it is a property of the roster and not of the fix.)
_real_mc_init = MovementController.__init__


def _mc_init(self, *args, **kwargs):
    _real_mc_init(self, *args, **kwargs)
    # `is not None`, not truthiness: main() builds this controller during the
    # pre-game, when state.tokens is still EMPTY and every unit is added to
    # that same list object later. Storing only a non-empty list would keep
    # the one reference that never fills.
    if getattr(self, "all_tokens", None) is not None:
        live["tokens"] = self.all_tokens


MovementController.__init__ = _mc_init


class _Advanced:
    def __init__(self, squads):
        self.advanced_squad_ids = set(squads)


_argv = sys.argv[1:] or ["map2", "3000"]
sys.argv = ["selfplay.py"] + _argv
# The list is what fields the detachment; passed the same way the army-select
# screen would answer.
from game import config  # noqa: E402
config.PLAYER1_ARMY = "tau_montka"
config.PLAYER2_ARMY = "tau_montka"
config.ARMY_SELECT = False

runpy.run_module("selfplay", run_name="__main__")

# THE PROBE. Everything above is passive; this supplies the ONE fact the
# harness cannot be relied on to produce - that a unit Advanced - and then asks
# the real functions about the real squads on the real board.
tokens = live["tokens"] or []
squads, _seen = [], set()
for _t in tokens:
    _s = getattr(_t, "squad", None)
    if _s is not None and _s.owner == HUMAN and id(_s) not in _seen:
        _seen.add(id(_s))
        squads.append(_s)

# THE STAMP. main() makes it on every phase change; when the run never reaches
# one, the reader and the window can still be measured against the real board -
# so the two halves are reported SEPARATELY rather than folded into one verdict
# that a slow roster could fail for the wrong reason. The feed itself is pinned
# at the source (test_tau_doctrines.py section 4b) and by an A/B probe that
# removes main.py's call.
_fed_by_main = stats["phases_stamped"] > 0
if not _fed_by_main and squads:
    from game.turn import TurnTracker as _TT

    class _Round:
        battle_round = 1

    _real_refresh(squads, _Round())

for squad in squads:
    if not getattr(squad, "montka_killing_blow", False):
        continue
    offered = _real_types(squad, tokens, _Advanced([squad]))
    if shooting.ASSAULT_SHOOTING in offered:
        stats["probe_offered"] += 1
    else:
        stats["probe_blocked"] += 1

refused = 0
total = 0
for squad in squads:
    for model in squad.models:
        for weapon in model.weapons:
            if getattr(weapon, "weapon_type", None) is None:
                continue
            if weapon.weapon_type != shooting.RANGED:
                continue
            total += 1
            if not gate(weapon, squad):
                refused += 1

print()
print("--- Mont'ka Killing Blow at the Advance gate"
      + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
print("  battle round at the last stamp : %s" % live["round"])
print("  units on the board             : %d" % len(squads))
for key, value in stats.items():
    print("  %-30s %s" % (key, value))
print("  ranged weapons                 : %d" % total)
print("  ...refused at the Advance gate : %d" % refused)

print("  stamp came from main()           : %s" % _fed_by_main)
if not squads:
    print("  INCONCLUSIVE: no Player 1 unit was ever on the board")
    raise SystemExit(2)

if NEUTRALIZE:
    # NOT "nothing is offered": eleven of the fourteen carry a PRINTED Assault
    # weapon and keep an Assault option regardless - what Killing Blow buys
    # them is the other 102 weapons, which is exactly why the gap could sit
    # there looking survivable. The pre-fix world is "the granted weapons are
    # refused, and the three units with no printed Assault weapon are shut out
    # altogether" - the two numbers the report was written from.
    ok = refused > 0 and stats["probe_blocked"] > 0
    print("  VERDICT: " + ("the pre-fix world is reproduced"
                           if ok else "NOT reproduced - the probe proves nothing"))
    raise SystemExit(0 if ok else 1)

ok = (stats["probe_offered"] > 0 and stats["probe_blocked"] == 0
      and refused == 0)
print("  VERDICT: " + ("Killing Blow reaches rule 10.05" if ok else "FAILED"))
raise SystemExit(0 if ok else 1)
