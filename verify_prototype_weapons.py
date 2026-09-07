"""Runtime proof through the REAL main() loop that the three Experimental
Prototype Cadre weapon Enhancements actually reach their weapons.

WHY A RUNTIME PROBE AND NOT JUST A SUITE
----------------------------------------
test_tau_enhancements.py calls enh_prototype_weapons.apply_all() with a
directly-built squad list and is green - it never goes through main.py. The
bug was entirely in what main.py HANDED it: at Declare Battle Formations,
register_unit() has deliberately put nothing into state.tokens / reserves /
embarked_squads, so state.all_squads() is EMPTY and apply_all([]) upgraded
nothing. "Built but never fed" has hit this repo seven times now and a green
suite has never once caught it. Reported: "experimental cadre waffen upgrades
(enhancements) greifen alle nicht".

WHAT IT MEASURES: the three named weapons' printed characteristics, read off
the LIVE squads main() built, after the pre-game step has run.

Harness trap this walks into deliberately (documented in CLAUDE.md): importing
selfplay runs nothing because of its __main__ guard - hence runpy with
run_name="__main__".

Usage:  python verify_prototype_weapons.py [map2]
        python verify_prototype_weapons.py map2 --neutralize   # must report 0 upgraded
"""

import runpy
import sys

from game import config, enh_prototype_weapons

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

# The Recon list is the shipped roster that fields Experimental Prototype Cadre
# and equips the weapons these Enhancements name, so it is the one on which they
# are anything but dormant. It used to be the Prototypes list, which bought all
# THREE; that list was retired on user request and Recon buys TWO of them - the
# Plasma Accelerator Rifle and the Thermoneutronic Projector. The third,
# Supernova Launcher, now has no bearer at all, which is pinned as such in
# test_tau_enhancements.py section 13 rather than left to be rediscovered here.
config.PLAYER1_ARMY = "tau_recon"
config.PLAYER2_ARMY = "necrons"

stats = {"apply_all_calls": 0, "squads_handed_over": 0, "weapons_upgraded": 0}
report = []
live_squads = []

_real_apply_all = enh_prototype_weapons.apply_all


def apply_all(squads, game_log=None):
    squads = list(squads)
    stats["apply_all_calls"] += 1
    # Captured BEFORE the neutralisation below, so the counter-proof can still
    # read the same live weapons and report that they are UNCHANGED - "not on
    # the table" would be a much weaker statement than "S8, still printed".
    live_squads.extend(squads)
    if NEUTRALIZE:
        # THE FAITHFUL PRE-FIX WORLD: main.py used to reach for a container
        # that is empty at this point in the pre-game sequence. Everything
        # else - the registry, grant(), is_active(), the weapon classes - was
        # and is correct, so blinding any of those would prove something
        # weaker than the bug that was reported.
        squads = []
    stats["squads_handed_over"] += len(squads)
    out = _real_apply_all(squads, game_log=game_log)
    stats["weapons_upgraded"] += len(out)
    for model, weapon, name in out:
        report.append("%s / %s (%s)" % (model.profile.name, weapon.name, name))
    return out


enh_prototype_weapons.apply_all = apply_all

sys.argv = ["selfplay.py"] + (sys.argv[1:] or ["map2", "400"])
runpy.run_module("selfplay", run_name="__main__")

print()
print("--- Prototype weapon spy" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
for key, value in stats.items():
    print("  %-22s %s" % (key, value))

# The characteristics themselves, read off the live squads - the upgrades are
# applied IN PLACE, so this is the same object the shooting step will fire.
print("  upgraded weapons:")
for line in report or ["    (none)"]:
    print("    " + line)

seen = {}
for spec in enh_prototype_weapons.UPGRADES:
    seen[spec.weapon_cls.__name__] = None
for squad in live_squads:
    for model in squad.models:
        for weapon in model.weapons:
            key = type(weapon).__name__
            if key in seen and seen[key] is None:
                seen[key] = "S%s AP%s D%s A%s  upgraded=%s" % (
                    weapon.strength, weapon.ap, weapon.damage, weapon.attacks,
                    getattr(weapon, enh_prototype_weapons.UPGRADED_ATTR, False))
print("  live characteristics:")
for key, value in seen.items():
    print("    %-42s %s" % (key, value or "(not on the table)"))
