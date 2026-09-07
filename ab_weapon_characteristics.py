"""A/B probes for the weapon-characteristic sweep - each restores a piece of
the pre-fix world AT THE SOURCE and re-runs the suite that should notice.

Reported: "in den infos stehen voellig falsche schadenswerte ... sind diese
fehler echt oder nur anzeige fehler?" The answer was ANZEIGE for the three
weapons named - the dice being rolled were right all along - and REAL for
thirteen others that only surfaced once rules/*.md and the engine were put
side by side.

So there are three families of probe here:
  * the datacard printing the grouping placeholder again - the reported defect
  * each corrected weapon value put back - the ones nothing was guarding
  * the sweep itself blinded, because a sweep-based test that stops finding
    anything reports zero differences and looks exactly like a pass

A probe that does not bite is a finding about the TEST, not proof of the fix
(error class 24).

    python ab_weapon_characteristics.py
"""

import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
_TALLY = re.compile(r"(\d+)/(\d+) checks passed|passed (\d+), failed (\d+)")


def run(suite):
    proc = subprocess.run([sys.executable, os.path.join(ROOT, suite)], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    hits = _TALLY.findall(proc.stdout or "")
    if not hits:
        return (0, 0)
    passed, total, p2, f2 = hits[-1]
    if passed:
        return (int(passed), int(total))
    return (int(p2), int(p2) + int(f2))


# (label, suite, file, [(old, new)])
PROBES = [
    # --- the reported defect: the card printed the placeholder --------------
    ("the card prints the Damage placeholder again - the reported bug",
     "test_unit_datacard.py", "game/ui/unit_datacard.py",
     [('                str(weapon.ap), printed_characteristic(weapon, "damage"),',
       '                str(weapon.ap), str(weapon.damage),')]),

    ("...and the Attacks placeholder, the half nobody had noticed",
     "test_unit_datacard.py", "game/ui/unit_datacard.py",
     [('                weapon.name, range_label, printed_characteristic(weapon, "attacks"),',
       '                weapon.name, range_label, str(weapon.attacks),')]),

    ("...and the Strength placeholder",
     "test_unit_datacard.py", "game/ui/unit_datacard.py",
     [('                str(skill_for(weapon)), printed_characteristic(weapon, "strength"),',
       '                str(skill_for(weapon)), str(weapon.strength),')]),

    # The honest pre-fix world for the helper is reading the plain field, not a
    # helper that happens to return the same thing.
    ("printed_characteristic ignores the notation entirely",
     "test_unit_datacard.py", "game/ui/unit_datacard.py",
     [('    notation = getattr(weapon, which + "_notation", None)\n'
       "    if notation is not None:\n"
       "        return describe_dice_notation(notation)\n"
       "    return str(getattr(weapon, which))",
       "    return str(getattr(weapon, which))")]),

    # --- the thirteen real ones ---------------------------------------------
    ("the Dark Reapers' missile launcher deals a flat 6 again",
     "test_weapon_characteristics.py", "game/weapons.py",
     [("    damage = 3  # preview/grouping placeholder only - damage_notation is what is rolled\n"
       "    damage_notation = D6()\n"
       "    ignores_cover = True\n\n\n"
       "class DarkReaperMissileLauncherSunburstProfile(WeaponProfile):",
       "    damage = 6\n"
       "    ignores_cover = True\n\n\n"
       "class DarkReaperMissileLauncherSunburstProfile(WeaponProfile):")]),

    ("...and test_dark_reapers.py notices it too",
     "test_dark_reapers.py", "game/weapons.py",
     [("    damage = 3  # preview/grouping placeholder only - damage_notation is what is rolled\n"
       "    damage_notation = D6()\n"
       "    ignores_cover = True\n\n\n"
       "class DarkReaperMissileLauncherSunburstProfile(WeaponProfile):",
       "    damage = 6\n"
       "    ignores_cover = True\n\n\n"
       "class DarkReaperMissileLauncherSunburstProfile(WeaponProfile):")]),

    ("the Eldritch Storm hits on the Farseer's own 2+ again",
     "test_weapon_characteristics.py", "game/weapons.py",
     [('    ballistic_skill = "3+"\n'
       "    attacks = 3  # preview/grouping placeholder only - attacks_notation is what is rolled",
       "    attacks = 3  # preview/grouping placeholder only - attacks_notation is what is rolled")]),

    ("the Paired Hekatarii Blades are A5/AP-1 at the wielder's WS again",
     "test_weapon_characteristics.py", "game/weapons.py",
     [("    attacks = 4\n"
       "    # Printed WS 2+, where the Shade Runner herself is 3+ - a real per-weapon\n"
       "    # override, the same shape as the Power Klaw's own worse one.\n"
       '    weapon_skill = "2+"\n'
       "    strength = 3\n"
       "    ap = -2",
       "    attacks = 5\n"
       "    strength = 3\n"
       "    ap = -1")]),

    ("the Voidscarred share the Voidreavers' A2 melee rows again",
     "test_weapon_characteristics.py", "game/factions/aeldari.py",
     [("_VOIDSCARRED_LOADOUT = [ShurikenPistolProfile, VoidscarredPowerSwordProfile,\n"
       "                        AeldariCloseCombatWeaponA3Profile]",
       "_VOIDSCARRED_LOADOUT = [ShurikenPistolProfile, PowerSwordProfile,\n"
       "                        AeldariCloseCombatWeaponA2Profile]")]),

    ("the Voidreavers' wraithcannon inherits the Wraithguard's 4+ again",
     "test_weapon_characteristics.py", "game/factions/aeldari.py",
     [("                      with_weapons=[VoidreaverWraithcannonProfile],",
       "                      with_weapons=[WraithcannonProfile],")]),

    ("the Firesight Team's pulse pistol takes its wielder's 4+ again",
     "test_weapon_characteristics.py", "game/factions/tau_empire.py",
     [("                  [LongshotPulseRiflesProfile, PulsePistolBs3Profile,",
       "                  [LongshotPulseRiflesProfile, PulsePistolProfile,")]),

    ("Shadowsun's pulse pistol takes her own 2+ again",
     "test_weapon_characteristics.py", "game/factions/tau_empire.py",
     [("                   LightMissilePodProfile, PulsePistolBs3Profile,",
       "                   LightMissilePodProfile, PulsePistolProfile,")]),

    # --- probes on the GUARD itself -----------------------------------------
    # Without these two the suite could pass by measuring nothing, which is how
    # a sweep-based test quietly stops being a test.
    ("the sweep finds no weapons at all (the vacuum guard)",
     "test_weapon_characteristics.py", "verify_rules_vs_engine.py",
     [("    pairs, seen = [], set()\n"
       "    compositions = list(sheet.compositions())",
       "    pairs, seen = [], set()\n"
       "    return pairs\n"
       "    compositions = list(sheet.compositions())")]),

    # An earlier version of this probe replaced the name_diffs.append() with
    # `pass` and did NOT bite - because every drifted name is currently on the
    # exception list, so nothing was being appended to begin with. The honest
    # probe is to take one exception away, which makes a real drift appear.
    ("a real drifted weapon name loses its exception",
     "test_weapon_characteristics.py", "test_weapon_characteristics.py",
     [('    "Grot-Smacka": ', '    "Grot-Smacka NOT": ')]),

    ("...and an exception that covers nothing is an expired excuse",
     "test_weapon_characteristics.py", "test_weapon_characteristics.py",
     [("UNMATCHED_BY_NAME = {\n",
       'UNMATCHED_BY_NAME = {\n    "No Such Weapon": "covers nothing",\n')]),

    ("the [TORRENT] skip is dropped, so 35 non-differences come back",
     "test_weapon_characteristics.py", "test_weapon_characteristics.py",
     [('                if (column in ("BS", "WS")\n'
       '                        and row[column].strip().rstrip("*") in ("N/A", "-", "")\n'
       '                        and getattr(weapon_cls, "torrent", False)):\n'
       "                    continue\n",
       "")]),
]


def main():
    base = {}
    for _label, suite, _f, _e in PROBES:
        if suite not in base:
            base[suite] = run(suite)
            print("BASELINE %-28s %d/%d" % (suite, *base[suite]))
    if any(p != t for p, t in base.values()):
        print("\n  baseline not green - fix that first")
        return 1

    bites = 0
    for label, suite, path, edits in PROBES:
        full = os.path.join(ROOT, path)
        original = io.open(full, encoding="utf-8").read()
        patched = original
        for old, new in edits:
            if patched.count(old) != 1:
                print("!! %s: anchor matched %d times in %s"
                      % (label, patched.count(old), path))
                patched = None
                break
            patched = patched.replace(old, new)
        if patched is None:
            continue
        io.open(full, "w", encoding="utf-8", newline="\n").write(patched)
        try:
            got = run(suite)
        finally:
            io.open(full, "w", encoding="utf-8", newline="\n").write(original)
        fell = base[suite][0] - got[0]
        bites += 1 if fell > 0 else 0
        print("\n%s %s" % ("+ BITES" if fell > 0 else "! NO BITE", label))
        print("      %-28s %d/%d (was %d)" % (suite, got[0], got[1], base[suite][0]))
        if fell <= 0:
            print("      a finding about the TEST, not proof of the fix")

    print("\n%d/%d probes bite" % (bites, len(PROBES)))
    for suite, was in base.items():
        now = run(suite)
        print("restored %-28s %d/%d" % (suite, *now))
        if now != was:
            return 1
    return 0 if bites == len(PROBES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
