"""A/B probes for the replaced Mont'ka roster (the 2026-09-06 app export).

Each probe restores one wrong world at the SOURCE and must break its own
checks. Two of them are the reason this file exists:

  * the Pathfinder Shas'ui's grenade launcher. build_squad() DROPS a `choices`
    entry naming a (line, option) pair the datasheet does not carry, so the
    unit comes out one weapon short AND correctly priced - the shape that
    survives a points check and a glance at the total.
  * the two attachments, which have to be read off the export's own "Attached
    Units" heading rather than off a sentence.

Run: python ab_montka_roster.py
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


ARMY = "armies/tau_montka.json"
TAU = "game/factions/tau_empire.py"

PROBES = [
    # 1. The datasheet change reverted: the launcher option goes back to being
    #    offered on the rank and file only. The list's `choices` entry for the
    #    Shas'ui is then silently ignored - no error, no points change, one
    #    weapon missing. The only probe here that still patches SOURCE, because
    #    it is the only one about a datasheet rather than about a list.
    Patch("the grenade launcher is offered on the rank and file only",
          [(TAU,
            "        # The same option on the Shas'ui - see the note above the datasheet.\n"
            "        WargearOption(\n"
            "            _PATHFINDER_LEADER, replaces=None,\n"
            "            with_weapons=[SemiAutomaticGrenadeLauncherEmpProfile],\n"
            "            max_models=1, name=PATHFINDER_CARBINE_TO_GRENADE_LAUNCHER,\n"
            "        ),\n", "")],
          expect=SUITES),

    # 2. Rail rifles instead of ion rifles. Both replace the pulse carbine and
    #    both are three models - but rail rifles are FREE and ion rifles are +5
    #    each, so this is also the 15 points that separate 85 from the list's 100.
    Patch("the Pathfinders take rail rifles instead of ion rifles",
          [(ARMY, '"Pulse Carbine -> Ion Rifle": 3',
            '"Pulse Carbine -> Rail Rifle": 3')],
          expect=SUITES),

    # 3-4. The two attachments. Detaching a character keeps the army total and
    #      the model count identical - attach() sums the components - so only an
    #      attachment check sees it; dropping just one leaves fifteen units.
    #
    #      A leader is removed by renaming the key that carries it, which is the
    #      whole edit now: under the old builder this was a two-line
    #      attach-and-register pair inside a hand-written loop.
    Patch("nothing is attached - both characters stand alone",
          [(ARMY, '"leaders": [\n        {\n          "datasheet": "Commander Farsight"',
            '"__leaders": [\n        {\n          "datasheet": "Commander Farsight"'),
           (ARMY, '"leaders": [\n        {\n          "datasheet": "Commander in Coldstar Battlesuit"',
            '"__leaders": [\n        {\n          "datasheet": "Commander in Coldstar Battlesuit"')],
          expect=SUITES),
    Patch("Farsight is left out of the Sunforge",
          [(ARMY, '"leaders": [\n        {\n          "datasheet": "Commander Farsight"',
            '"__leaders": [\n        {\n          "datasheet": "Commander Farsight"')],
          expect=SUITES),

    # 5. The Enhancement moves to a Cadre Fireblade, where the previous roster
    #    had it. Both bearers are legal ("T'AU EMPIRE model only") and the army
    #    total is unchanged, so nothing but the bearer check moves.
    Patch("Strategic Conqueror goes back onto a Cadre Fireblade",
          [(ARMY, '          "enhancement": "Strategic Conqueror"\n',
            '          "enhancement": null\n'),
           (ARMY, '"Cadre Fireblade": ["Gun Drone", "Gun Drone"]\n          }',
            '"Cadre Fireblade": ["Gun Drone", "Gun Drone"]\n          },\n'
            '          "enhancement": "Strategic Conqueror"')],
          expect=SUITES),

    # 6. The Breacher Shas'ui keeps the previous roster's Gun Drone in place of
    #    the export's Shield Drone. FREE either way, so the points do not move
    #    and nothing but a per-model loadout check can see it.
    Patch("the Breacher Shas'ui takes a Gun Drone again",
          [(ARMY, '"Breacher Fire Warrior Shas\'ui": ["Guardian Drone", "Shield Drone"]',
            '"Breacher Fire Warrior Shas\'ui": ["Guardian Drone", "Gun Drone"]')],
          expect=SUITES),

    # 7. The Starscythe keep their printed three T'au flamers instead of trading
    #    all six barrels for burst cannons. That is +15 on the unit, so it moves
    #    the army total too - the cheap half of the check.
    Patch("the Starscythe keep their printed flamers",
          [(ARMY, '"T\'au Flamer -> Burst Cannon": 1',
            '"T\'au Flamer -> Burst Cannon": 0')],
          expect=SUITES),

    # 8. The transport hint dropped: the Breachers walk and both Devilfish
    #    drive around empty. Costs nothing in points or models, and the export
    #    names two DEDICATED TRANSPORTS without saying who rides in them - so
    #    the pairing is the one part of this roster read from the shape of the
    #    list rather than off a printed line, and it is worth a probe.
    Patch("the Breachers are not declared into anything",
          [(ARMY, '"transport": "devilfish_1"', '"__transport": "devilfish_1"'),
           (ARMY, '"transport": "devilfish_2"', '"__transport": "devilfish_2"')],
          expect=SUITES),

    # 9. The two Cadre Fireblades stand alone again, as the export prints them.
    #    This is the USER'S override of the export, and it costs NOTHING in
    #    points - attach() sums the components - so the army total cannot see
    #    it and only the unit count and the pairings move.
    #
    #    IT IS ALSO THE ONE-LINE EDIT THE WHOLE REWORK WAS FOR.
    Patch("the Fireblades no longer lead the Breachers",
          [(ARMY, '"leaders": [\n        {\n          "datasheet": "Cadre Fireblade"',
            '"__leaders": [\n        {\n          "datasheet": "Cadre Fireblade"')],
          expect=SUITES),

    # 10. THIS PROBE REPLACES ONE THAT NO LONGER HAS A WORLD TO RESTORE. It used
    #     to be "Mont'ka is back on the shared roster builder" - but each list is
    #     its own file now, so that is not a state the code can be in, and a
    #     probe that cannot be applied is worse than none.
    #
    #     What it really guarded was that Mont'ka's roster is its OWN. This
    #     mutates one of the twelve entries it has in common with Kauyon: under
    #     the shared builder that edit moved BOTH lists at once, which is the
    #     bug-shaped coupling the split removed.
    Patch("one of the entries Mont'ka shares with Kauyon is changed",
          [(ARMY, '"datasheet": "Kroot Carnivores"', '"datasheet": "Kroot Hounds"')],
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
