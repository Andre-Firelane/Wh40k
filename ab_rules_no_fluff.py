"""A/B probes for "only rules text in the army rules" - at the SOURCE.

User, after a game: "keine hintergrund info texte und example texte in den
armeeregeln bitte. nur reine regeltexte."

Each probe below restores ONE piece of the pre-fix world in
fetch_datasheet_rules.py, REGENERATES the corpus from the cached HTML, and
re-runs the two suites that are supposed to notice. A probe that does not bite
is a finding about the test, not proof the fix works (error class 24), which is
why the whole world is rebuilt rather than one line stubbed (error class 16):
the corpus files are already on disk, so a probe that only edits the scraper
and skips the regeneration would leave a suite reading fixed files and report
a clean pass against a broken parser - exactly the trap section 5b of
test_datasheet_rules.py already documents.

Runs entirely off rules/.cache/, so no network request is made.

    python ab_rules_no_fluff.py

The corpus is regenerated once more on the way out (also from a `finally`), so
an interrupted run does not leave flavour text on disk.
"""

import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SCRAPER = os.path.join(ROOT, "fetch_datasheet_rules.py")
SUITES = ("test_datasheet_rules.py", "test_army_rules_overlay.py")

_TALLY = re.compile(r"(\d+)/(\d+) checks passed")


def run_suite(name):
    """(passed, total) for one suite, or (0, 0) if it did not get that far."""
    proc = subprocess.run([sys.executable, os.path.join(ROOT, name)],
                          cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    matches = _TALLY.findall(proc.stdout or "")
    return (int(matches[-1][0]), int(matches[-1][1])) if matches else (0, 0)


def regenerate():
    subprocess.run([sys.executable, SCRAPER, "--offline"], cwd=ROOT,
                   capture_output=True, text=True)


def measure(label):
    regenerate()
    return label, [run_suite(name) for name in SUITES]


# The pre-fix world, one piece at a time. Each entry is (label, [(old, new)]) -
# a replacement applied to the scraper's source.
PROBES = [
    ("ShowFluff is not skipped: the lore paragraph above every rule comes back", [
        ('"EnhUpgrade", "ShowFluff", "redExample")', '"EnhUpgrade", "redExample")'),
    ]),
    ("redExample is not skipped: the worked example comes back", [
        ('"EnhUpgrade", "ShowFluff", "redExample")', '"EnhUpgrade", "ShowFluff")'),
    ]),
    ("the stratagem legend is parsed and written again", [
        ('    ("type", re.compile(r\'<div class="str11Type[^"]*">(.*?)</div>\', re.S)),\n',
         '    ("type", re.compile(r\'<div class="str11Type[^"]*">(.*?)</div>\', re.S)),\n'
         '    ("legend", re.compile(r\'<div class="str11Legend[^"]*">(.*?)</div>\', re.S)),\n'),
        ('                out.append("*%s*" % item["type"])\n'
         '                out.append("")\n'
         '            if item["text"]:',
         '                out.append("*%s*" % item["type"])\n'
         '                out.append("")\n'
         '            if item["legend"]:\n'
         '                out.append(item["legend"])\n'
         '                out.append("")\n'
         '            if item["text"]:'),
    ]),
    ("the whole pre-fix world at once", [
        ('"EnhUpgrade", "ShowFluff", "redExample")', '"EnhUpgrade")'),
        ('    ("type", re.compile(r\'<div class="str11Type[^"]*">(.*?)</div>\', re.S)),\n',
         '    ("type", re.compile(r\'<div class="str11Type[^"]*">(.*?)</div>\', re.S)),\n'
         '    ("legend", re.compile(r\'<div class="str11Legend[^"]*">(.*?)</div>\', re.S)),\n'),
        ('                out.append("*%s*" % item["type"])\n'
         '                out.append("")\n'
         '            if item["text"]:',
         '                out.append("*%s*" % item["type"])\n'
         '                out.append("")\n'
         '            if item["legend"]:\n'
         '                out.append(item["legend"])\n'
         '                out.append("")\n'
         '            if item["text"]:'),
    ]),
]


def main():
    original = io.open(SCRAPER, encoding="utf-8").read()
    _label, base = measure("BASELINE")
    print("BASELINE")
    for name, (passed, total) in zip(SUITES, base):
        print("    %-32s %d/%d" % (name, passed, total))
    if any(p != t for p, t in base):
        print("\n  the baseline is not green - fix that first, every probe below "
              "would look like it bit")
        return 1

    bites = 0
    try:
        for label, edits in PROBES:
            patched = original
            for old, new in edits:
                if patched.count(old) != 1:
                    raise SystemExit("probe %r: anchor not unique (%d)"
                                     % (label, patched.count(old)))
                patched = patched.replace(old, new)
            io.open(SCRAPER, "w", encoding="utf-8", newline="\n").write(patched)
            try:
                _l, got = measure(label)
            finally:
                io.open(SCRAPER, "w", encoding="utf-8", newline="\n").write(original)
            fell = sum(b[0] - g[0] for b, g in zip(base, got))
            bites += 1 if fell > 0 else 0
            print("\n%s BITES" % ("+" if fell > 0 else "!"), label)
            for name, (passed, total), (was, _t) in zip(SUITES, got, base):
                mark = "  <-- " if passed < was else "      "
                print("  %s%-32s %d/%d (was %d)" % (mark, name, passed, total, was))
            if fell <= 0:
                print("     NO BITE - a finding about the TEST, not proof of the fix")
    finally:
        io.open(SCRAPER, "w", encoding="utf-8", newline="\n").write(original)
        regenerate()

    print("\n%d/%d probes bite" % (bites, len(PROBES)))
    _l, restored = measure("RESTORED")
    print("restored:", ", ".join("%s %d/%d" % (n, p, t)
                                 for n, (p, t) in zip(SUITES, restored)))
    return 0 if bites == len(PROBES) and restored == base else 1


if __name__ == "__main__":
    raise SystemExit(main())
