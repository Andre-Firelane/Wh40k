"""A/B probes for the save/load fixes: every one restores a pre-fix world AT
THE SOURCE and must make its own checks go red.

A check that survives its own probe is a finding about the TEST, not proof of
the fix - this repo has caught that half a dozen times (a guard matching its
own docstring, a tautology comparing a constant to itself, a probe that only
half-restored the old world). So each entry below says how many checks it
expects to lose, and a probe that loses none is reported as a FAILURE of the
probe.

Run: python ab_scene_activation.py
"""

import os
import shutil
import subprocess
import sys

SUITES = ("test_scene_activation.py", "test_scene_io.py")


def _clear_pycache():
    """CLAUDE.md error class 19: these probes rewrite and restore source files
    inside the same second, so a stale .pyc can hand the next run the previous
    world. Cheap insurance, and without it a probe reports the run before it."""
    for root, dirs, _files in os.walk("."):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)


def _run(suite):
    _clear_pycache()
    out = subprocess.run([sys.executable, suite], capture_output=True, text=True)
    line = [l for l in out.stdout.splitlines() if "checks passed" in l]
    if not line:
        return None, None, out.stdout + out.stderr
    passed, total = line[0].split()[0].split("/")
    return int(passed), int(total), out.stdout


BASE = {}
print("baseline")
for suite in SUITES:
    passed, total, text = _run(suite)
    if passed is None:
        print(f"  {suite}: DID NOT RUN\n{text}")
        sys.exit(1)
    if passed != total:
        print(f"  {suite}: {passed}/{total} - not green to begin with, "
              f"fix that before probing\n{text}")
        sys.exit(1)
    BASE[suite] = total
    print(f"  {suite}: {total}/{total}")


PROBES = [
    # (name, file, old, new)
    # The whole pre-fix world: an identity-free file, which is also literally
    # every snapshot already on disk. Neutering only pass 1 is NOT that world -
    # pass 2 still matches on the datasheet name, and the first version of this
    # probe reported a no-op for exactly that reason (CLAUDE.md error class 16:
    # a half-restored world proves nothing).
    ("model identity ignored entirely (the reported world)",
     "game/scene_io.py",
     "    remaining = list(models)",
     '    saved = [{k: v for k, v in e.items() if k not in ("model", "weapons")}\n'
     "             for e in saved]  # AB\n"
     "    remaining = list(models)"),
    ("weapons dropped from the identity, so only the datasheet line matches",
     "game/scene_io.py",
     '                 "model": _profile_name(m), "weapons": _weapon_names(m)}',
     '                 "model": _profile_name(m), "weapons": None}  # AB'),
    ("a casualty is merely dropped again, not recorded as destroyed",
     "game/scene_io.py",
     """    if model in state.tokens:
        state.tokens.remove(model)
    model.current_wounds = 0
    destroyed = getattr(squad, "destroyed_models", None)""",
     """    if model in state.tokens:
        state.tokens.remove(model)
    return  # AB
    destroyed = getattr(squad, "destroyed_models", None)"""),
    ("the wounds clamp removed, so an old file heals a model above its maximum",
     "game/scene_io.py",
     """                model.current_wounds = (wounds if maximum is None
                                        else min(wounds, maximum))""",
     """                model.current_wounds = wounds  # AB"""),
    ("capture() writes no activation section",
     "game/scene_io.py",
     """    acted = activation_state.capture(
        [squad for squad, _p, _t in entries.values()], activation)""",
     """    acted = {}  # AB"""),
    ("restore_activation() puts the controller ledgers back but not the flags",
     "game/activation_state.py",
     """        for field in SQUAD_FLAGS:
            if field in entry:
                setattr(squad, field, entry[field])""",
     """        for field in ():  # AB
            setattr(squad, field, entry[field])"""),
    ("the shooting ledger falls out of the table",
     "game/activation_state.py",
     '        ("shot_squad_ids", SQUADS),',
     '        ("shot_squad_ids_AB", SQUADS),'),
    ("main.py stops passing the slots to capture()",
     "main.py",
     "                             activation=_activation_slots()),",
     "                             ),  # AB"),
    ("main.py stops restoring them on --load",
     "main.py",
     "        complaints += scene_io.restore_activation(",
     "        _unused_ab = (lambda *a: [])("),
    ("a slot the table knows is missing from main()'s wiring",
     "main.py",
     '            "charge": charge_controller,',
     '            "charge_AB": charge_controller,'),
    ("restore_activation moved BEFORE begin_battle, where it is wiped again",
     "main.py",
     """        begin_battle((loaded.get("turn") or {}).get("turn_owner") or "Player 1")""",
     """        complaints += scene_io.restore_activation(
            loaded, [e["squad"] for e in scene_units], _activation_slots())
        begin_battle((loaded.get("turn") or {}).get("turn_owner") or "Player 1")"""),
    ("a NEW Squad flag nobody listed - the ninth-field case",
     "game/squad.py",
     "        self.battle_shocked = False",
     "        self.brand_new_ab_flag = False\n        self.battle_shocked = False"),
    ("a NEW *_squad_ids ledger nobody put in the table",
     "game/pile_in.py",
     "        self.movement_controller = movement_controller\n"
     "        self.piled_in_squad_ids = set()",
     "        self.movement_controller = movement_controller\n"
     "        self.brand_new_ab_squad_ids = set()\n"
     "        self.piled_in_squad_ids = set()"),
]

print("\nprobes")
bit = 0
for name, path, old, new in PROBES:
    original = open(path, encoding="utf-8").read()
    if original.count(old) != 1:
        print(f"  [PROBE BROKEN] {name}: its anchor appears "
              f"{original.count(old)} times in {path}")
        continue
    open(path, "w", encoding="utf-8").write(original.replace(old, new, 1))
    try:
        results = []
        for suite in SUITES:
            passed, total, text = _run(suite)
            results.append((suite, passed, total, text))
    finally:
        open(path, "w", encoding="utf-8").write(original)
    lost = 0
    detail = []
    crashed = False
    for suite, passed, total, _text in results:
        if passed is None:
            crashed = True
            detail.append(f"{suite} CRASHED")
        else:
            lost += total - passed
            if passed != total:
                detail.append(f"{suite} {passed}/{total}")
    if crashed:
        # A probe that makes the suite CRASH instead of go red hides WHICH
        # check broke - the lesson this repo has now learned five times.
        print(f"  [CRASH]  {name}  ({'; '.join(detail)})")
    elif lost:
        bit += 1
        print(f"  [BITES]  {name}  -{lost}  ({'; '.join(detail)})")
    else:
        print(f"  [NO-OP]  {name}  - the suites do not notice this")

_clear_pycache()
print(f"\n{bit}/{len(PROBES)} probes bite")
sys.exit(0 if bit == len(PROBES) else 1)
