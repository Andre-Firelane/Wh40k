"""A/B probes for the Necron Hypercrypt Legion list (the 2026-09-13 app export)
and for testkit.lists_fielding(), the helper the "dormant by roster" pins now go
through.

Each probe restores one wrong world at the SOURCE and must turn at least one of
its declared suites red. A probe that leaves every suite green is a finding
about the TESTS.

The first two are the reason this file exists: seven Necron suites used to read
armies/necrons.json alone, so a SECOND Necron list fielding the Monolith, the
Hexmark Destroyer and the Triarch Praetorians left every "dormant by roster"
pin green. Probe 1 restores that world inside the helper.

EXCLUSIVE: this script rewrites source files while it runs. Nothing else - no
suite, no measurement, no edit, no commit - may run beside it. Every patched
file is hashed before the run and checked after it.

Run: python ab_necron_hypercrypt_army.py
"""

import hashlib
import io
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

ARMY = "armies/necrons_hypercrypt.json"
TESTKIT = "testkit.py"

LIST_SUITE = "test_necron_hypercrypt_army.py"
ROSTERS = "test_army_rosters.py"
TITANS = "test_necron_titans.py"
CULT = "test_necron_destroyer_cult.py"
TRIARCH = "test_necron_triarch.py"
LEGION = "test_necron_hypercrypt_legion.py"
DETACH = "test_detachments.py"


def run(suite):
    proc = subprocess.run([sys.executable, suite], cwd=ROOT,
                          capture_output=True, text=True, timeout=900)
    out = proc.stdout + proc.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", out)
    if not match:
        return None   # crashed before reporting: named, not counted as a bite
    return int(match.group(1)), int(match.group(2))


def clear_pycache():
    for dirpath, dirnames, _ in os.walk(ROOT):
        for d in list(dirnames):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(dirpath, d), ignore_errors=True)
                dirnames.remove(d)


def digest(path):
    return hashlib.sha256(io.open(os.path.join(ROOT, path), "rb").read()).hexdigest()


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
            # Read and write RAW and bend the anchor to the file's own line
            # ending, so a run never rewrites a data file's newlines.
            nl = "\r\n" if "\r\n" in src else "\n"
            old, new = old.replace("\n", nl), new.replace("\n", nl)
            if old not in src:
                raise SystemExit("%s: anchor not found in %s:\n  %s" % (self.name, path, old[:90]))
            if src.count(old) != 1:
                raise SystemExit("%s: anchor is not unique in %s" % (self.name, path))
            io.open(full, "w", encoding="utf-8", newline="").write(src.replace(old, new, 1))
        clear_pycache()
        return self

    def __exit__(self, *exc):
        for full, text in self.backup.items():
            io.open(full, "w", encoding="utf-8", newline="").write(text)
        clear_pycache()
        return False


PROBES = [
    # 1. THE WORLD THE PINS USED TO LIVE IN: the helper reads armies/necrons.json
    #    alone. The three suites whose datasheets the new list fields must go
    #    red, and so must the list suite's leader line.
    Patch("lists_fielding() reads the default Necron list only",
          [(TESTKIT,
            "    return [entry.key for entry in army_lists.ARMY_LISTS\n"
            "            if any(",
            "    return [entry.key for entry in army_lists.ARMY_LISTS  # AB-PROBE\n"
            "            if entry.key == \"necrons\" and any(")],
          expect=[TITANS, CULT, TRIARCH, LIST_SUITE]),

    # 2. The helper forgets leaders. No datasheet a dormancy pin names is a
    #    leader anywhere, so only the list suite's Plasmancer line can see this.
    Patch("lists_fielding() ignores leaders",
          [(TESTKIT,
            "                   or any(led.datasheet.name == datasheet_name for led in unit.leaders)\n",
            "                   or False  # AB-PROBE\n")],
          expect=[LIST_SUITE]),

    # 3. Nine tesla carbines instead of ten. The golden master would bless this
    #    on the next --write; the export does not.
    Patch("one Immortal keeps its gauss blaster",
          [(ARMY, '"Gauss Blaster -> Tesla Carbine": 10', '"Gauss Blaster -> Tesla Carbine": 9')],
          expect=[LIST_SUITE, ROSTERS]),

    # 4. The Overlord without his Resurrection Orb. Free wargear - no points move.
    Patch("the Overlord takes no Resurrection Orb",
          [(ARMY, '"Overlord": ["Resurrection Orb"]', '"Overlord": []')],
          expect=[LIST_SUITE, ROSTERS]),

    # 5. The Monolith keeps its printed gauss flux arcs. Also free.
    Patch("the Monolith keeps its gauss flux arcs",
          [(ARMY, '"4x Gauss Flux Arc -> 4x Death Ray": 1', '"4x Gauss Flux Arc -> 4x Death Ray": 0')],
          expect=[LIST_SUITE, ROSTERS]),

    # 6. The wrong detachment: the default list's Awakened Dynasty. The roster
    #    is byte-identical, so the golden master cannot see it at all.
    Patch("the list declares Awakened Dynasty instead",
          [(ARMY, '"detachments": ["Hypercrypt Legion"]', '"detachments": ["Awakened Dynasty"]')],
          expect=[LIST_SUITE, LEGION, DETACH]),

    # 7. The Overlord stands alone. attach() sums the components, so the army
    #    total is unchanged; only the unit count and the pairing move.
    Patch("the Overlord no longer leads the Lychguard",
          [(ARMY, '"leaders": [\n        {\n          "datasheet": "Overlord"',
            '"__leaders": [\n        {\n          "datasheet": "Overlord"')],
          expect=[LIST_SUITE, ROSTERS]),
]


def main():
    patched = sorted({path for probe in PROBES for path, _o, _n in probe.edits})
    before = {path: digest(path) for path in patched}
    suites = sorted({s for probe in PROBES for s in probe.expect})

    print("baseline...")
    clear_pycache()
    base = {}
    for suite in suites:
        base[suite] = run(suite)
        print("  %-36s %s" % (suite, base[suite]))
        if base[suite] is None or base[suite][0] != base[suite][1]:
            raise SystemExit("baseline is not green: %s" % suite)

    print()
    silent, crashed = [], []
    for probe in PROBES:
        with probe:
            results = {s: run(s) for s in probe.expect}
        print(probe.name)
        for suite in probe.expect:
            got = results[suite]
            if got is None:
                verdict = "CRASHED (not a bite - the suite must degrade to red)"
                crashed.append((probe.name, suite))
            elif got[0] < got[1]:
                verdict = "bit: %d red" % (got[1] - got[0])
            else:
                verdict = "NO BITE"
                silent.append((probe.name, suite))
            print("  %-36s %-10s %s" % (suite, got, verdict))

    after = {path: digest(path) for path in patched}
    moved = [path for path in patched if before[path] != after[path]]
    print()
    print("restored: %s" % ("every patched file is byte-identical" if not moved
                            else "MOVED: %s" % ", ".join(moved)))
    if silent or crashed or moved:
        for name, suite in silent:
            print("NO BITE: %s -> %s" % (name, suite))
        for name, suite in crashed:
            print("CRASH: %s -> %s" % (name, suite))
        raise SystemExit(1)
    print("all %d probes bit every declared suite" % len(PROBES))


if __name__ == "__main__":
    main()
