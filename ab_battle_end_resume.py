"""A/B probes for "the statistics overlay is shown at the end of the game".

User: "am Ende des Spiels soll das Statistik Overlay angezeigt werden." The
resume existed and had a button in the board corner; nothing ever raised it on
its own, so the battle ended on a score box and the analysis of how that score
was earned was never offered.

Each probe restores ONE pre-fix world at the SOURCE and must make the suite
RED. Two are worth reading before the rest:

  * probe 3 parks the show() call behind an `if False:`. The substring survives
    that, and so does an AST pin that merely walks the branch - which is why
    the suite pins the two calls as SIBLING STATEMENTS in one body.
  * probe 6 leaves the hint naming the statistics and has it name the board as
    well. "the hint names the statistics" passes on that string; it is the
    second half ("...and no longer promises the board") that has to bite, and
    without it a hint could promise both screens forever.

Run: python ab_battle_end_resume.py

NOTE: this rewrites main.py and game/ui/battle_end_overlay.py in place for the
duration of each probe and restores them afterwards. Nothing else may run
against this working tree while it does - a commit taken mid-probe is how
`if False: return False` reached this repo's history once already.
"""

import io
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

SUITES = ["test_battle_end.py", "test_unit_stats_overlay.py"]


def run(suite):
    """(passed, total) from testkit's reporter. A crash counts as bitten, but
    is reported as a crash: a probe has to make the suite RED, not kill it -
    an aborted run does not say WHICH assurance broke."""
    proc = subprocess.run([sys.executable, suite], cwd=ROOT,
                          capture_output=True, text=True, timeout=900)
    out = proc.stdout + proc.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", out)
    if match:
        return int(match.group(1)), int(match.group(2))
    return (-1, -1)


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
                self.backup[full] = io.open(full, encoding="utf-8").read()
            src = io.open(full, encoding="utf-8").read()
            if old not in src:
                raise SystemExit("%s: anchor not found in %s:\n  %s"
                                 % (self.name, path, old[:90]))
            io.open(full, "w", encoding="utf-8").write(src.replace(old, new, 1))
        return self

    def __exit__(self, *exc):
        for full, text in self.backup.items():
            io.open(full, "w", encoding="utf-8").write(text)
        # The probes rewrite and restore inside the same second, so the
        # __pycache__ race this repo has hit before is live here - clear it
        # between passes rather than measure the previous world.
        for dirpath, dirnames, _ in os.walk(ROOT):
            for name in list(dirnames):
                if name == "__pycache__":
                    shutil.rmtree(os.path.join(dirpath, name), ignore_errors=True)
                    dirnames.remove(name)
        return False


SHOW = (
    "                    unit_stats_overlay_view.show(\n"
    "                        battle_stats, _stats_players(), state.all_squads())\n"
)
SHOW_GONE = ""
SHOW_DEAD = (
    "                    if False:\n"
    "                        unit_stats_overlay_view.show(\n"
    "                            battle_stats, _stats_players(), state.all_squads())\n"
)
SHOW_EMPTY = (
    "                    unit_stats_overlay_view.show(\n"
    "                        battle_stats, [], [])\n"
)

# The show moved OUT of the click, up beside the branch test - it still sits
# inside the battle-end branch, so a pin that only asks "is it in this branch"
# keeps passing while the resume opens on the frame the battle ends, under the
# score box it is supposed to follow.
DISMISS_CLICK = (
    "                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:\n"
    "                    battle_end_overlay.dismiss()\n"
)
DISMISS_CLICK_SPLIT = (
    "                unit_stats_overlay_view.show(\n"
    "                    battle_stats, _stats_players(), state.all_squads())\n"
    "                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:\n"
    "                    battle_end_overlay.dismiss()\n"
)

HINT = 'DISMISS_HINT = "Click for the unit statistics"'
HINT_OLD = 'DISMISS_HINT = "Click to view the final board"'
HINT_BOTH = 'DISMISS_HINT = "Click for the unit statistics, or the final board"'

# The overlay reading the constant at all. Restores the literal it shipped
# with, so the constant is inert and a later edit to it changes nothing.
HINT_READ = "        hint = self.hint_font.render(DISMISS_HINT, True, HINT_COLOR)"
HINT_READ_OLD = ('        hint = self.hint_font.render("Click to view the final board", '
                 "True, HINT_COLOR)")


PROBES = [
    # 1. THE PRE-FIX WORLD: the battle ends, the score box is dismissed, and
    #    the resume is never offered. The state the report was made against.
    Patch("the whole pre-fix world: the battle end never raises the resume",
          [("main.py", SHOW, SHOW_GONE),
           ("game/ui/battle_end_overlay.py", HINT, HINT_OLD)],
          expect=["test_battle_end.py"]),

    # 2. The call alone, hint untouched - so the box promises statistics and
    #    delivers the board.
    Patch("the chain is dropped but the hint still promises statistics",
          [("main.py", SHOW, SHOW_GONE)],
          expect=["test_battle_end.py"]),

    # 3. The call parked behind an `if False:`. The substring survives this,
    #    and so does a pin that merely walks the branch for a call node.
    Patch("the show() call is parked behind an `if False:`",
          [("main.py", SHOW, SHOW_DEAD)],
          expect=["test_battle_end.py"]),

    # 4. The call raised one level out, beside the branch test rather than
    #    inside the click - it still opens, but on the frame the battle ends,
    #    burying the final score under it.
    Patch("the resume is raised beside the branch instead of on the click",
          [("main.py", SHOW, SHOW_GONE),
           ("main.py", DISMISS_CLICK, DISMISS_CLICK_SPLIT)],
          expect=["test_battle_end.py"]),

    # 5. Opened with the wrong arguments: a resume showing no armies at all.
    #    show() returns False on an empty player list, so this is the shape
    #    where the chain is wired and opens nothing.
    Patch("the resume is opened without the armies or their art",
          [("main.py", SHOW, SHOW_EMPTY)],
          expect=["test_battle_end.py"]),

    # 6. The hint naming BOTH screens. Only the second half of the hint check
    #    can catch this, which is why there are two.
    Patch("the hint promises the statistics AND the board",
          [("game/ui/battle_end_overlay.py", HINT, HINT_BOTH)],
          expect=["test_battle_end.py"]),

    # 7. The hint constant back to what it said before the chain existed.
    Patch("the hint is back to promising the final board",
          [("game/ui/battle_end_overlay.py", HINT, HINT_OLD)],
          expect=["test_battle_end.py"]),

    # 8. The constant shipped but never read - the "built, never FED" shape one
    #    layer down. Nothing on screen changes when the constant is edited.
    Patch("the overlay ignores the constant and keeps its own literal",
          [("game/ui/battle_end_overlay.py", HINT_READ, HINT_READ_OLD)],
          expect=["test_battle_end.py"]),
]


def main():
    base = {}
    for suite in SUITES:
        passed, total = run(suite)
        base[suite] = (passed, total)
        print("baseline  %-32s %d/%d" % (suite, passed, total))
    print()

    silent = []
    for probe in PROBES:
        with probe:
            results = {suite: run(suite) for suite in probe.expect}
        bit = False
        lines = []
        for suite, (passed, total) in results.items():
            before = base[suite][0]
            if passed == -1:
                lines.append("%s CRASHED (a probe must go RED, not die)" % suite)
                bit = True
            else:
                lines.append("%s %d/%d (was %d)" % (suite, passed, total, before))
                if passed < before:
                    bit = True
        print("%s  %s" % ("BITES " if bit else "SILENT", probe.name))
        for line in lines:
            print("           %s" % line)
        if not bit:
            silent.append(probe.name)

    print()
    if silent:
        print("PROBES THAT DID NOT BITE (a finding about the TEST, not the code):")
        for name in silent:
            print("  -", name)
        raise SystemExit(1)
    print("all %d probes bit" % len(PROBES))


if __name__ == "__main__":
    main()
