"""A/B probes for the GRENADES keyword gap (test_explosives.py sections 10/11).

REPORTED: "warum kann ich mit meinem autarch+ scorpions keine explosives
einsetzen?" - AutarchProfile, and 17 other profile classes, never set the
`grenades` flag their datasheets print.

Each probe rewrites game/units.py at the SOURCE, runs the suite, and restores
the file in a `finally`. A probe must turn the suite RED (non-zero exit, no
Traceback); a probe that passes is a finding about the test, and a probe that
crashes the suite is one too.

EXCLUSIVE: this rewrites a source file while it runs. Nothing else - no suite,
no measurement, no edit, no commit - may run alongside it.

Run: python ab_explosives_grenades.py
"""
import os
import shutil
import subprocess
import sys

SUITE = "test_explosives.py"
UNITS = os.path.join("game", "units.py")
MARK = ("    grenades = True  # the GRENADES keyword - printed on the datasheet's "
        "keyword bar; rule 15.05 (Explosives) reads it")


def clear_cache():
    for root, dirs, _files in os.walk("."):
        for d in dirs:
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)


def run_suite():
    clear_cache()
    proc = subprocess.run([sys.executable, SUITE], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    out = proc.stdout + proc.stderr
    return proc.returncode, out


def class_body(lines, cls):
    start = next(i for i, line in enumerate(lines) if line.startswith("class %s(" % cls))
    end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("class "))
    return start, end


def drop_autarch(lines):
    """Pre-fix world for the reported unit only."""
    start, end = class_body(lines, "AutarchProfile")
    idx = next(i for i in range(start, end) if lines[i] == MARK)
    return lines[:idx] + lines[idx + 1:]


def drop_all(lines):
    """The whole pre-fix world: all 18 inserted flags gone."""
    return [line for line in lines if line != MARK]


def leak_to_kroot_hounds(lines):
    """The reverse direction: the flag on a SHARED base class reaches the
    stand-alone Kroot Hounds, whose keyword bar does not print GRENADES."""
    start, end = class_body(lines, "KrootHoundProfile")
    idx = next(i for i in range(start, end) if lines[i].startswith("    leadership = "))
    return lines[:idx + 1] + ["    grenades = True"] + lines[idx + 1:]


PROBES = [
    ("AutarchProfile loses the flag", drop_autarch),
    ("all 18 inserted flags removed (the reported world)", drop_all),
    ("the flag leaks onto the shared KrootHoundProfile base", leak_to_kroot_hounds),
]


def main():
    original = open(UNITS, encoding="utf-8").read()
    code, out = run_suite()
    if code != 0:
        print("BASELINE IS RED - fix the suite before probing:\n" + out[-2000:])
        return 1
    print("baseline: green")

    bad = 0
    lines = original.split("\n")
    for label, probe in PROBES:
        try:
            with open(UNITS, "w", encoding="utf-8", newline="") as handle:
                handle.write("\n".join(probe(list(lines))))
            code, out = run_suite()
        finally:
            with open(UNITS, "w", encoding="utf-8", newline="") as handle:
                handle.write(original)
        red = [line for line in out.splitlines() if "FAIL" in line]
        if "Traceback" in out:
            bad += 1
            print("CRASHED  %s\n%s" % (label, out[-1200:]))
        elif code == 0:
            bad += 1
            print("NO BITE  %s" % label)
        else:
            print("bites    %s (%d red line(s))" % (label, len(red)))
            for line in red[:4]:
                print("           " + line.strip())
    clear_cache()
    print("\n%d of %d probe(s) did not bite cleanly" % (bad, len(PROBES)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
