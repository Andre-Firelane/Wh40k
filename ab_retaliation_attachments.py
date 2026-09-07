"""A/B probes for the Retaliation Cadre list's four attachments.

Each probe restores one wrong world at the SOURCE and must break its own
checks. Probes 2 and 3 are the reason this file exists: both Starscythe units
are the SAME datasheet and both Enforcers are the SAME datasheet, so a leader
put on the wrong one produces IDENTICAL unit names, identical model counts and
an identical army total. Only the WEAPONS tell them apart - which is also how
the user named the pairings ("Farsight in die Flamer Starsythe", "Burst Cannon
Coldstar in die Burst Cannon Starsysthe").

Run: python ab_retaliation_attachments.py
"""

import io
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

SUITES = ["test_tau_enhancements.py"]


def run(suite):
    proc = subprocess.run([sys.executable, suite], cwd=ROOT,
                          capture_output=True, text=True, timeout=900)
    out = proc.stdout + proc.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", out)
    if not match:
        return (-1, -1)   # crashed: counts as bitten
    return int(match.group(1)), int(match.group(2))


class Patch:
    def __init__(self, name, edits, expect):
        self.name = name
        self.edits = edits
        self.expect = expect

    def __enter__(self):
        self.backup = {}
        for path, old, new in self.edits:
            full = os.path.join(ROOT, path)
            if full not in self.backup:
                self.backup[full] = io.open(full, encoding="utf-8", newline="").read()
            src = io.open(full, encoding="utf-8", newline="").read()
            # Read and write RAW, and bend the anchor to whatever line ending
            # this file already uses: the .py sources here are CRLF and the
            # armies/*.json are LF. Letting Python translate on the way in and
            # out instead would rewrite every data file to CRLF on each run -
            # a whole-file diff for nothing, in a repo whose method rests on
            # git diff meaning something.
            nl = "\r\n" if "\r\n" in src else "\n"
            old, new = old.replace("\n", nl), new.replace("\n", nl)
            if old not in src:
                raise SystemExit(f"{self.name}: anchor not found in {path}:\n  {old[:90]}")
            io.open(full, "w", encoding="utf-8", newline="").write(src.replace(old, new, 1))
        return self

    def __exit__(self, *exc):
        for full, text in self.backup.items():
            io.open(full, "w", encoding="utf-8", newline="").write(text)
        for dirpath, dirnames, _ in os.walk(ROOT):
            for d in list(dirnames):
                if d == "__pycache__":
                    shutil.rmtree(os.path.join(dirpath, d), ignore_errors=True)
                    dirnames.remove(d)
        return False


ARMY = "armies/tau_retaliation.json"

PROBES = [
    # 1. THE REPORTED STATE: every character built, none of them attached.
    #    Four renames of the same key: each one hits the first `"leaders"` still
    #    spelled that way, so applying it four times detaches all four in roster
    #    order. The loader ignores a key it does not know, which is what makes a
    #    rename the cheapest way to say "this entry has no leader".
    Patch("nothing is attached - the reported state",
          [(ARMY, '"leaders": [', '"__leaders": ['),
           (ARMY, '"leaders": [', '"__leaders": ['),
           (ARMY, '"leaders": [', '"__leaders": ['),
           (ARMY, '"leaders": [', '"__leaders": [')],
          expect=SUITES),

    # 2. The two Starscythe leaders swapped. Both units are the SAME datasheet
    #    and both leaders are legal on it, so the army total, the unit count and
    #    the model counts are all unchanged - the user named these two by their
    #    WEAPONS, and only a check that reads the weapons can tell them apart.
    #    Swapping the two LOADOUTS rather than the two leader names, because the
    #    leaders are not interchangeable blocks - Farsight carries nothing and
    #    the Coldstar carries gear and a weapon swap, so trading only the
    #    datasheet names leaves each with the other's wargear. That is a list
    #    army_io refuses outright ("Commander Farsight has no model line
    #    'Commander in Coldstar Battlesuit'"), and a probe that cannot be
    #    applied measures nothing. The user named these two units by their guns,
    #    so trading the guns is what "on the wrong unit" means here.
    Patch("the two Starscythe leaders are swapped",
          [(ARMY, '"Burst Cannon -> T\'au Flamer": 1', '"__SWAP__": 1'),
           (ARMY, '"Burst Cannon -> T\'au Flamer": 1', '"__SWAP__": 1'),
           (ARMY, '"Burst Cannon -> T\'au Flamer": 1', '"__SWAP__": 1'),
           (ARMY, '"T\'au Flamer -> Burst Cannon": 1', '"Burst Cannon -> T\'au Flamer": 1'),
           (ARMY, '"T\'au Flamer -> Burst Cannon": 1', '"Burst Cannon -> T\'au Flamer": 1'),
           (ARMY, '"T\'au Flamer -> Burst Cannon": 1', '"Burst Cannon -> T\'au Flamer": 1'),
           (ARMY, '"__SWAP__": 1', '"T\'au Flamer -> Burst Cannon": 1'),
           (ARMY, '"__SWAP__": 1', '"T\'au Flamer -> Burst Cannon": 1'),
           (ARMY, '"__SWAP__": 1', '"T\'au Flamer -> Burst Cannon": 1')],
          expect=SUITES),

    # 3. The two Enforcers swapped. Same datasheet, same colour, same points -
    #    they differ only in which gun replaced the burst cannon, so this moves
    #    nothing a total can see. It also carries the Enhancement to the other
    #    unit, since that rides on the missile-pod Enforcer.
    Patch("the two Enforcers are swapped",
          [(ARMY, '"Burst Cannon -> Cyclic Ion Blaster": 1', '"__SWAP__": 1'),
           (ARMY, '"Burst Cannon -> Fusion Blaster": 1',
            '"Burst Cannon -> Cyclic Ion Blaster": 1'),
           (ARMY, '"__SWAP__": 1', '"Burst Cannon -> Fusion Blaster": 1')],
          expect=SUITES),

    # 4. Starflare Ignition System moves to the OTHER Enforcer - the fusion one,
    #    in the Sunforge. Both are legal bearers and the points are identical,
    #    so only a check that pins the bearer MODEL sees it. It has to be pinned
    #    on the model rather than the unit: after 19.01 the unit holds four
    #    models, and "the unit carries it" would pass with the Enhancement on a
    #    Fireknife suit.
    Patch("Starflare Ignition System moves to the fusion Enforcer",
          [(ARMY, ',\n          "enhancement": "Starflare Ignition System"', ''),
           (ARMY,
            '              "Burst Cannon -> Fusion Blaster": 1\n'
            '            }\n'
            '          }\n'
            '        }\n'
            '      ]',
            '              "Burst Cannon -> Fusion Blaster": 1\n'
            '            }\n'
            '          },\n'
            '          "enhancement": "Starflare Ignition System"\n'
            '        }\n'
            '      ]')],
          expect=SUITES),

    # 5. The Sunforge loses its Enforcer while the other three attachments stay.
    #    Anchored on the fusion loadout because the `"leaders"` key alone is not
    #    unique - four entries carry one, and the two Enforcers are the same
    #    datasheet in the same colour.
    Patch("the Sunforge attachment is forgotten",
          [(ARMY,
            '      "leaders": [\n'
            '        {\n'
            '          "datasheet": "Commander in Enforcer Battlesuit",\n'
            '          "color": [140, 160, 210],\n'
            '          "gear": {\n'
            '            "Commander in Enforcer Battlesuit": ["Shield Drone", "Shield Drone", '
            '"Fusion Blaster", "Fusion Blaster", "Fusion Blaster"]\n',
            '      "__leaders": [\n'
            '        {\n'
            '          "datasheet": "Commander in Enforcer Battlesuit",\n'
            '          "color": [140, 160, 210],\n'
            '          "gear": {\n'
            '            "Commander in Enforcer Battlesuit": ["Shield Drone", "Shield Drone", '
            '"Fusion Blaster", "Fusion Blaster", "Fusion Blaster"]\n')],
          expect=SUITES),
]


def main():
    print("baseline...")
    base = {}
    for suite in SUITES:
        base[suite] = run(suite)
        print(f"  {suite:32s} {base[suite][0]}/{base[suite][1]}")
        if base[suite][0] != base[suite][1]:
            raise SystemExit(f"baseline is not green: {suite}")

    print()
    silent = []
    for probe in PROBES:
        with probe:
            results = {s: run(s) for s in probe.expect}
        bit = False
        lines = []
        for suite, (passed, total) in results.items():
            before = base[suite][0]
            if passed == -1:
                lines.append(f"{suite} CRASHED")
                bit = True
            else:
                lines.append(f"{suite} {passed}/{total} (was {before})")
                if passed < before:
                    bit = True
        print(f"{'BITES ' if bit else 'SILENT'}  {probe.name}")
        for line in lines:
            print(f"           {line}")
        if not bit:
            silent.append(probe.name)

    print()
    if silent:
        print("PROBES THAT DID NOT BITE (a finding about the TEST, not the code):")
        for name in silent:
            print("  -", name)
        raise SystemExit(1)
    print(f"all {len(PROBES)} probes bit")


if __name__ == "__main__":
    main()
