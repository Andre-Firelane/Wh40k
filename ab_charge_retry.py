"""A/B probes for the charge ladder's retry guard and the reactors' memo, at
the SOURCE. Each probe restores ONE clause of the pre-fix world (in
ai/agent_driver.py, game/kauyon_photon_grenades.py or
game/kauyon_combat_embarkation.py), runs test_charge_retry_reactions.py and
must make it red - and must make it RED, not crash it. The last probe
restores the whole pre-fix world.

A probe that does not bite is a finding about the TEST, not a pass.

Run: python ab_charge_retry.py
"""
import io
import os
import re
import shutil
import subprocess
import sys

DRIVER = os.path.join("ai", "agent_driver.py")
PHOTON = os.path.join("game", "kauyon_photon_grenades.py")
EMBARK = os.path.join("game", "kauyon_combat_embarkation.py")
SUITE = "test_charge_retry_reactions.py"

MEMO_CHECK = ("        key = self._declaration_key(charging_squad, targets)\n"
              "        if key == self._offered_key:\n"
              "            return False  # this same declaration has already been asked about\n")
MEMO_GONE = "        key = self._declaration_key(charging_squad, targets)\n"
GUARD = ("            reopen()\n"
         "            if movement_controller.move_mode != \"charge\":\n"
         "                # Reacted to, or nothing left to declare: no move to place\n"
         "                # into. Hand the continuation back instead of placing blind.\n"
         "                return None, last_errors\n")
GUARD_GONE = "            reopen()\n"
NONE_IS_COME_BACK = "        if completed is None:\n"
NONE_IS_FAILURE = "        if completed is None and False:\n"
OPEN_ONLY_IF_CLOSED = ("        if movement_controller.move_mode != \"charge\":\n"
                       "            # Open the move - unless a reaction's resume already did (the\n")
OPEN_ALWAYS = ("        if True:\n"
               "            # Open the move - unless a reaction's resume already did (the\n")

PROBES = [
    ("Photon Grenades forgets which declaration it asked about", [(PHOTON, MEMO_CHECK, MEMO_GONE)]),
    ("Combat Embarkation forgets which declaration it asked about", [(EMBARK, MEMO_CHECK, MEMO_GONE)]),
    ("the ladder places blind when a retry's reopen opened no move", [(DRIVER, GUARD, GUARD_GONE)]),
    ("_handle_charge treats the handed-back continuation as a failed charge",
     [(DRIVER, NONE_IS_COME_BACK, NONE_IS_FAILURE)]),
    ("the resume branch re-runs the reaction chain over an already open move",
     [(DRIVER, OPEN_ONLY_IF_CLOSED, OPEN_ALWAYS)]),
    ("whole pre-fix world", [(PHOTON, MEMO_CHECK, MEMO_GONE), (EMBARK, MEMO_CHECK, MEMO_GONE),
                             (DRIVER, GUARD, GUARD_GONE), (DRIVER, NONE_IS_COME_BACK, NONE_IS_FAILURE),
                             (DRIVER, OPEN_ONLY_IF_CLOSED, OPEN_ALWAYS)]),
]


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, t):
    io.open(p, "w", encoding="utf-8", newline="").write(t)


def clear_cache():
    for root, dirs, _f in os.walk("."):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)


def run(script):
    clear_cache()
    out = subprocess.run([sys.executable, script], capture_output=True, text=True)
    return out.stdout + out.stderr, out.returncode


def result(text):
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    return (int(match.group(1)), int(match.group(2))) if match else (None, None)


originals = {p: read(p) for p in (DRIVER, PHOTON, EMBARK)}
base_text, base_code = run(SUITE)
base = result(base_text)
print(f"baseline {SUITE}: {base[0]}/{base[1]} (exit {base_code})")
if base[0] is None or base_code != 0:
    sys.exit("baseline is not green - fix that first")

bad = 0
try:
    for label, edits in PROBES:
        texts = dict(originals)
        skipped = False
        for path, old, new in edits:
            if texts[path].count(old) != 1:
                print(f"  PROBE SKIPPED (anchor not found exactly once in {path}): {label}")
                skipped = True
                break
            texts[path] = texts[path].replace(old, new)
        if skipped:
            bad += 1
            continue
        for path, text in texts.items():
            write(path, text)
        try:
            text, code = run(SUITE)
        finally:
            for path, text_ in originals.items():
                write(path, text_)
        got, total = result(text)
        if got is None:
            verdict, detail = "CRASHED", "the suite did not report - a probe must make it red, not crash it"
            bad += 1
        elif got < base[0]:
            verdict, detail = "BITES", f"{got}/{total}"
        else:
            verdict, detail = "NO BITE", f"{got}/{total} - FINDING ABOUT THE TEST"
            bad += 1
        print(f"  {verdict:8s} {label}: {detail}")
finally:
    for path, text_ in originals.items():
        write(path, text_)
    clear_cache()

print("all probes bite" if not bad else f"{bad} probe(s) did not bite")
sys.exit(1 if bad else 0)
