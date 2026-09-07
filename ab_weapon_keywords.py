"""A/B probes for the weapon-keyword work - each restores a piece of the
pre-fix world AT THE SOURCE and re-runs the suite that should notice.

Reported: "in den weapon info tabellen im overlay fehlen die keywords (zb twin
linked oder sustained hits)". Building the display put the engine's keyword
flags beside the printed keyword column of rules/*.md for the first time, and
that comparison found five genuine engine differences on top of the missing
display - the same shape as the thirteen the characteristics sweep found.

So there are four families of probe here:
  * the card drawing no keywords again - the reported defect
  * the formatter losing a piece of its spelling (the ANTI entries, the dice
    [SUSTAINED HITS X], the printed alphabetical order)
  * each corrected weapon keyword put back
  * the sweep itself blinded, because a sweep-based test that stops finding
    anything reports zero differences and looks exactly like a pass

A probe that does not bite is a finding about the TEST, not proof of the fix
(error class 24).

    python ab_weapon_keywords.py
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
    # --- the reported defect: the table drew no keywords at all -------------
    ("the weapon table draws no keyword band - the reported bug",
     "test_unit_datacard.py", "game/ui/unit_datacard.py",
     [("            keyword_y = row_y + band_heights[index] + 2\n"
       "            for line in self._weapon_keyword_lines(weapon, box_rect):",
       "            keyword_y = row_y + band_heights[index] + 2\n"
       "            for line in []:")]),

    ("printed_keywords returns nothing for every weapon",
     "test_unit_datacard.py", "game/weapons.py",
     [("    printed = []\n"
       "    for keyword, threshold in anti_entries(weapon):",
       "    return []\n"
       "    printed = []\n"
       "    for keyword, threshold in anti_entries(weapon):")]),

    ("...and the corpus sweep notices that too",
     "test_weapon_characteristics.py", "game/weapons.py",
     [("    printed = []\n"
       "    for keyword, threshold in anti_entries(weapon):",
       "    return []\n"
       "    printed = []\n"
       "    for keyword, threshold in anti_entries(weapon):")]),

    # --- the spelling ------------------------------------------------------
    ("[ANTI-X Y+] is dropped from the printed list",
     "test_weapon_characteristics.py", "game/weapons.py",
     [("    for keyword, threshold in anti_entries(weapon):\n"
       '        printed.append("ANTI-%s %d+" % (keyword, threshold))',
       "    for keyword, threshold in ():\n"
       '        printed.append("ANTI-%s %d+" % (keyword, threshold))')]),

    ("a dice [SUSTAINED HITS X] prints its grouping placeholder instead",
     "test_weapon_characteristics.py", "game/weapons.py",
     [("    if weapon.sustained_hits_notation is not None:\n"
       '        printed.append("SUSTAINED HITS %s" % describe(weapon.sustained_hits_notation))\n'
       "    elif weapon.sustained_hits:",
       "    if False:\n"
       '        printed.append("SUSTAINED HITS %s" % describe(weapon.sustained_hits_notation))\n'
       "    elif weapon.sustained_hits:")]),

    ("the printed alphabetical order is abandoned",
     "test_weapon_characteristics.py", "game/weapons.py",
     [("    return sorted(printed)", "    return list(reversed(printed))")]),

    # --- the five real ones -------------------------------------------------
    ("the paired Hekatarii blades lose [TWIN-LINKED] again",
     "test_weapon_characteristics.py", "game/weapons.py",
     [("    # [TWIN-LINKED] (24.38) - re-roll the Wound roll. Found by the keyword\n"
       "    # sweep in test_weapon_characteristics.py section 5: the printed row\n"
       "    # carries it and this profile did not, so the blades were re-rolling\n"
       "    # nothing at all.\n"
       "    twin_linked = True\n",
       "")]),

    ("Jain Zar's Silent Death takes back the Blade's [ANTI-INFANTRY 3+]",
     "test_weapon_characteristics.py", "game/weapons.py",
     [("    assault = True\n"
       "    # NO [ANTI-INFANTRY 3+]: that keyword is the BLADE of Destruction's alone.",
       "    assault = True\n"
       '    anti = ("INFANTRY", 3)\n'
       "    # NO [ANTI-INFANTRY 3+]: that keyword is the BLADE of Destruction's alone.")]),

    ("...and test_jain_zar.py notices it too",
     "test_jain_zar.py", "game/weapons.py",
     [("    assault = True\n"
       "    # NO [ANTI-INFANTRY 3+]: that keyword is the BLADE of Destruction's alone.",
       "    assault = True\n"
       '    anti = ("INFANTRY", 3)\n'
       "    # NO [ANTI-INFANTRY 3+]: that keyword is the BLADE of Destruction's alone.")]),

    ("the Defiler's ectoplasma destructor loses [BLAST] again",
     "test_weapon_characteristics.py", "game/weapons.py",
     [("    blast = 1  # plain [BLAST] is X=1, see WeaponProfile.blast - missing until the keyword sweep; the printed row is \"blast, lethal hits\" and the Defiler's other two D6-attack guns already carried it\n"
       "    lethal_hits = True",
       "    lethal_hits = True")]),

    ("the Blight-hauler's krak missile gets its unprinted [LETHAL HITS] back",
     "test_weapon_characteristics.py", "game/weapons.py",
     [("    damage_notation = D6()\n"
       "    # NO [LETHAL HITS]: this row's keyword column is empty on the printed",
       "    damage_notation = D6()\n"
       "    lethal_hits = True\n"
       "    # NO [LETHAL HITS]: this row's keyword column is empty on the printed")]),

    ("...and its frag half loses the [BLAST] it really does print",
     "test_weapon_characteristics.py", "game/weapons.py",
     [('    name = "Missile Launcher - frag"\n'
       "    blast = 1  # plain [BLAST] is X=1, see WeaponProfile.blast",
       '    name = "Missile Launcher - frag"')]),

    ("the Twin Lance's XV pulse pistol is [PISTOL] on the strength of its name again",
     "test_weapon_characteristics.py", "game/weapons.py",
     [("    damage = 2\n    rapid_fire = 2\n\n\nclass XvPulsePistolMeleeProfile",
       "    damage = 2\n    rapid_fire = 2\n    pistol = True\n\n\nclass XvPulsePistolMeleeProfile")]),

    ("...and test_twin_lance.py notices it too",
     "test_twin_lance.py", "game/weapons.py",
     [("    damage = 2\n    rapid_fire = 2\n\n\nclass XvPulsePistolMeleeProfile",
       "    damage = 2\n    rapid_fire = 2\n    pistol = True\n\n\nclass XvPulsePistolMeleeProfile")]),

    # --- probes on the GUARDS themselves ------------------------------------
    # Without these the suite could pass by measuring nothing, which is how a
    # sweep-based test quietly stops being a test.
    ("the keyword sweep compares no columns at all (the vacuum guard)",
     "test_weapon_characteristics.py", "test_weapon_characteristics.py",
     [('            if row is None or "Keywords" not in row:\n'
       "                continue\n"
       "            keyword_compared += 1",
       "            if True:\n"
       "                continue\n"
       "            keyword_compared += 1")]),

    ("a real unmodeled keyword loses its exception",
     "test_weapon_characteristics.py", "test_weapon_characteristics.py",
     [('    "Dread Klaw": ', '    "Dread Klaw NOT": ')]),

    ("...and an exception that covers nothing is an expired excuse",
     "test_weapon_characteristics.py", "test_weapon_characteristics.py",
     [("KEYWORD_EXCEPTIONS = {\n",
       'KEYWORD_EXCEPTIONS = {\n    "No Such Weapon": "covers nothing",\n')]),

    ("the BLAST/BLAST 1 spelling is no longer folded together",
     "test_weapon_characteristics.py", "test_weapon_characteristics.py",
     [('        if keyword == "blast 1":\n            keyword = "blast"\n', "")]),

    # --- probes on the card's layout ---------------------------------------
    ("the column separators run through the keyword band again",
     "test_unit_datacard.py", "game/ui/unit_datacard.py",
     [("            bands.append((band_top, band_top + band_height))",
       "            bands.append((band_top, band_top + row_height))")]),

    ("the row height stops accounting for the keyword lines",
     "test_unit_datacard.py", "game/ui/unit_datacard.py",
     [("        height = self._weapon_band_height(weapon)\n"
       "        keyword_lines = self._weapon_keyword_lines(weapon, box_rect)",
       "        height = self._weapon_band_height(weapon)\n"
       "        return height\n"
       "        keyword_lines = self._weapon_keyword_lines(weapon, box_rect)")]),
]


def main():
    base = {}
    for _label, suite, _f, _e in PROBES:
        if suite not in base:
            base[suite] = run(suite)
            print("BASELINE %-32s %d/%d" % (suite, *base[suite]))
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
        print("      %-32s %d/%d (was %d)" % (suite, got[0], got[1], base[suite][0]))

    print("\n%d/%d probes bite" % (bites, len(PROBES)))
    for suite in base:
        print("restored %-32s %d/%d" % (suite, *run(suite)))
    return 0 if bites == len(PROBES) else 1


if __name__ == "__main__":
    sys.exit(main())
