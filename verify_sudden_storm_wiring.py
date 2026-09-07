"""Runtime proof through the REAL main() loop that Protocol of the Sudden
Storm's [ASSAULT] grant reaches rule 10.05's gate.

"Built but never FED" has hit this repo six times, and a source guard only
shows the call is written down. So this drives selfplay.py's real main() loop
with a spy on coldstar.weapon_has_assault() and on
shooting.available_shooting_types(), and reports whether a unit that actually
bought the Stratagem and actually Advanced was actually offered Assault
shooting.

Harness trap this walks into deliberately (documented in CLAUDE.md): importing
selfplay runs nothing, because of its __main__ guard - so it goes through
runpy with run_name="__main__".

Usage:  python verify_sudden_storm_wiring.py [map2]
        python verify_sudden_storm_wiring.py map2 --neutralize   # must report 0 hits
"""

import runpy
import sys

from game import coldstar, protocol_sudden_storm, shooting

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

stats = {"granted": 0, "gate_true_via_storm": 0, "advanced_and_offered": 0,
         "advanced_and_blocked": 0, "forced_probe_offered": 0,
         "forced_probe_blocked": 0}
# The live board, captured from whatever the real loop last asked about. A
# MockAgent run buys the Stratagem but does not reliably go on to Advance AND
# shoot in the same activation (the documented limit of this harness), so the
# probe below asks the real module function, about the real squad, against the
# real token list, with only the "it Advanced" fact supplied.
live = {"tokens": None}

_real_gate = coldstar.weapon_has_assault
_real_types = shooting.available_shooting_types


def gate(weapon, squad):
    if NEUTRALIZE:
        # THE FAITHFUL PRE-FIX WORLD, and it has to be exactly this shape:
        # the grant still reaches the adjuster chain (that half always
        # worked and was always green), and ONLY rule 10.05's gate is blind
        # to it. Neutralising is_active() outright would break both halves
        # and prove something weaker than the bug that was reported.
        real = protocol_sudden_storm.is_active
        protocol_sudden_storm.is_active = lambda squad: False
        try:
            return _real_gate(weapon, squad)
        finally:
            protocol_sudden_storm.is_active = real
    out = _real_gate(weapon, squad)
    if out and squad is not None and getattr(squad, "sudden_storm_active", False) \
            and not getattr(weapon, "assault", False):
        stats["gate_true_via_storm"] += 1
    return out


def types(squad, all_tokens, movement_controller=None):
    live["tokens"] = all_tokens
    out = _real_types(squad, all_tokens, movement_controller)
    advanced = (movement_controller is not None
                and squad in getattr(movement_controller, "advanced_squad_ids", ()))
    if advanced and getattr(squad, "sudden_storm_active", False):
        if shooting.ASSAULT_SHOOTING in out:
            stats["advanced_and_offered"] += 1
        else:
            stats["advanced_and_blocked"] += 1
    return out


coldstar.weapon_has_assault = gate
shooting.available_shooting_types = types
# shooting.py imported the name directly, so rebind it there too.
shooting.weapon_has_assault = gate

_real_grant = protocol_sudden_storm.SuddenStormController._grant


class _Advanced:
    def __init__(self, squads):
        self.advanced_squad_ids = set(squads)


def grant(self, controller, player, targets):
    stats["granted"] += 1
    out = _real_grant(self, controller, player, targets)
    squad = targets[0]
    tokens = live["tokens"]
    if tokens is None:
        tokens = [m for m in squad.models]
    probe = _real_types(squad, tokens, _Advanced([squad]))
    if shooting.ASSAULT_SHOOTING in probe:
        stats["forced_probe_offered"] += 1
    else:
        stats["forced_probe_blocked"] += 1
    print(f"    [spy] {squad.name} bought Sudden Storm; if it Advances -> {probe}")
    return out


protocol_sudden_storm.SuddenStormController._grant = grant

sys.argv = ["selfplay.py"] + sys.argv[1:]
runpy.run_module("selfplay", run_name="__main__")

print()
print("--- Sudden Storm spy" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
for key, value in stats.items():
    print(f"  {key:24} {value}")
