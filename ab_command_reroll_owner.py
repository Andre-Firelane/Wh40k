"""A/B probes for test_command_reroll.py - each restores ONE piece of the
pre-fix world at its SOURCE and must turn the named suites RED.

Report: "ich konnte gerade command reroll in der selben aktiverung 2 mal
einsetzen. einmal bei wound, einmal bei damage".

Restore is a REVERSE REPLACEMENT on the file as it is after the run, not a
write-back of a snapshot: a parallel session editing another part of the same
file during the run keeps its edit. A crash (a traceback with no summary line)
is reported as its own outcome, never as a bite - a probe must make a suite
red, not kill it.

Exclusive: nothing else may run suites, measurements, edits or commits while
this runs - it rewrites game/ files for seconds at a time."""
import io
import os
import shutil
import subprocess
import sys

SUITE = "test_command_reroll.py"

PROBES = [
    ("payer back to active_player",
     "game/command_reroll.py",
     "unit.owner, self._stratagem, [unit])",
     "(self.turn_tracker.active_player if self.turn_tracker is not None else unit.owner), "
     "self._stratagem, [unit])",
     2, [SUITE]),
    ("no target handed to 15.01 again",
     "game/command_reroll.py",
     "unit.owner, self._stratagem, [unit])",
     "unit.owner, self._stratagem, [])",
     2, [SUITE]),
    ("allow_repeat_target=True back on Command Re-roll",
     "game/command_reroll.py",
     "effect=self._do_reroll,\n        )",
     "effect=self._do_reroll, allow_repeat_target=True,\n        )",
     1, [SUITE]),
    ("the Damage roll made for the TARGET (the realistic slip)",
     "game/damage_resolution.py",
     "rolled_for=self.attacker_squad,\n                title=\"Damage Roll\"",
     "rolled_for=self.target_squad,\n                title=\"Damage Roll\"",
     1, [SUITE]),
    ("shooting's save rolls made for the attacker",
     "game/shooting.py",
     "rolled_for=target_squad, roll_kind=SAVE_ROLL",
     "rolled_for=self.active_squad, roll_kind=SAVE_ROLL",
     2, [SUITE]),
    ("the Mortal Wound sweep's roll names no unit",
     "game/mortal_wound_sweep.py",
     "rolled_for=self._sweep_bearer,",
     "rolled_for=None,",
     1, [SUITE]),
    ("DiceManager.roll() keeps the previous roll's unit",
     "game/dice.py",
     "self.rolled_for = rolled_for\n",
     "self.rolled_for = rolled_for or self.rolled_for\n",
     1, [SUITE]),
    ("the dice panel ignores whose roll it is",
     "game/roll_choice.py",
     "return human_players is None or owner_of() in human_players",
     # NOT a bare "return True": that text already stood elsewhere in the file,
     # and the first version of this driver restored EVERY occurrence of it -
     # which rewrote take()'s own `return True` into this line. The driver now
     # refuses a replacement text that is already present (see main()).
     "return True  # ab-probe: the panel ignores the owner",
     1, [SUITE]),
    ("the AI asks active_player again",
     "ai/agent_driver.py",
     "if command_reroll_controller.roll_owner() != player:",
     "if turn_tracker.active_player != player:",
     1, [SUITE]),
    ("main.py stops handing the dice panel the human view",
     "main.py",
     "unmodified_six_controller,\n            human_players=human_players)",
     "unmodified_six_controller)",
     1, [SUITE]),
]


def clear_cache():
    for root, dirs, _files in os.walk("."):
        if "__pycache__" in dirs:
            shutil.rmtree(os.path.join(root, "__pycache__"), ignore_errors=True)


def read(path):
    return io.open(path, encoding="utf-8", newline="").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def run(suite):
    proc = subprocess.run([sys.executable, suite], capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    out = proc.stdout + proc.stderr
    crashed = proc.returncode != 0 and "checks passed" not in out
    fails = [ln.strip() for ln in out.splitlines() if ln.lstrip().startswith("FAIL")]
    return proc.returncode, crashed, fails, out


def main():
    base_code, base_crash, base_fails, _ = run(SUITE)
    if base_code != 0:
        print("BASELINE IS RED - fix the suite before probing:", base_fails or "crash")
        return 2
    silent, crashes = [], []
    for label, path, old, new, times, suites in PROBES:
        text = read(path)
        found = text.count(old)
        if found != times:
            print("ANCHOR  %s: expected %d occurrence(s) in %s, found %d" % (label, times, path, found))
            silent.append(label)
            continue
        # The restore below replaces the probe text back. If that text is
        # ALREADY in the file, the restore would rewrite those occurrences
        # too - measured, not imagined: it turned roll_choice.take()'s
        # `return True` into a line that raises NameError. Refuse instead.
        if text.count(new):
            print("COLLIDE %s: the replacement text already occurs in %s - make it unique" % (label, path))
            silent.append(label)
            continue
        write(path, text.replace(old, new))
        clear_cache()
        try:
            for suite in suites:
                code, crashed, fails, out = run(suite)
                if crashed:
                    crashes.append(label)
                    print("CRASH   %s -> %s\n%s" % (label, suite, out[-600:]))
                elif code == 0:
                    silent.append(label)
                    print("NO BITE %s -> %s" % (label, suite))
                else:
                    print("BITES   %s -> %s: %d red" % (label, suite, len(fails)))
                    for line in fails[:3]:
                        print("          " + line)
        finally:
            current = read(path)
            if current.count(new) >= times:
                write(path, current.replace(new, old))
            else:
                print("RESTORE %s: the probe text is gone from %s - check by hand!" % (label, path))
            clear_cache()
    print("\n%d probe(s), %d silent, %d crash(es)" % (len(PROBES), len(silent), len(crashes)))
    return 1 if (silent or crashes) else 0


if __name__ == "__main__":
    sys.exit(main())
