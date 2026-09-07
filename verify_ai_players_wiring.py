"""Does every rule that takes `auto_players` really GET it, in a real battle?

The `verify_mark_wiring.py` pattern, for the switch. A source guard only shows
the argument is written down; this drives the REAL main() loop and spies on
every constructor under game/ that declares `auto_players`, then reports what
each one was actually handed.

WHY IT IS WORTH ITS OWN SCRIPT. "Built, but never FED" has hit this repo six
times, and this exact class hit it seven more: seven reactive controllers
(kauyon_* x3, montka_* x3, aac_autoreactive_camouflage) DECLARED `auto_players`,
READ it, and were constructed without it - so the AI fell through to
ai/agent_driver.py's _maybe_resolve_decision() and paid a real API call for a
decision that was supposed to be free. That was invisible to every suite,
because a unit test builds the controller itself and passes what it likes.

Two questions, and the second is the one no suite can answer:

  1. Did EVERY such controller receive a non-empty `auto_players`?
  2. Did they all receive the SAME one - i.e. is there really one fact?

Usage:  python verify_ai_players_wiring.py [map2] [--frames N]
Exit 0 if every controller was fed and they all agree.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import ast
import importlib
import pathlib
import runpy

MAP = "map2"
FRAMES = "600"
for arg in sys.argv[1:]:
    if arg.startswith("--frames"):
        FRAMES = arg.split("=", 1)[1] if "=" in arg else FRAMES
    elif arg.startswith("map"):
        MAP = arg

ROOT = pathlib.Path(__file__).parent


def classes_taking_auto_players():
    """Every class under game/ whose __init__ declares `auto_players`.

    Read from the SOURCE rather than by importing and introspecting, so a
    module that is never imported in this run still counts - "never imported"
    is itself one of the ways a controller goes unfed."""
    found = {}
    for path in sorted((ROOT / "game").rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if not isinstance(item, ast.FunctionDef) or item.name != "__init__":
                    continue
                names = [a.arg for a in item.args.args + item.args.kwonlyargs]
                if "auto_players" in names:
                    rel = path.relative_to(ROOT).as_posix()[:-3].replace("/", ".")
                    found[node.name] = rel
    return found


TARGETS = classes_taking_auto_players()
seen = {}          # class name -> list of the values it was constructed with
missing_import = []

for cls_name, module_name in sorted(TARGETS.items()):
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:                      # pragma: no cover - diagnostic
        missing_import.append(f"{module_name}: {exc}")
        continue
    cls = getattr(module, cls_name, None)
    if cls is None:
        continue

    def make_spy(cls=cls, cls_name=cls_name):
        real = cls.__init__

        def spy(self, *args, **kwargs):
            seen.setdefault(cls_name, []).append(tuple(kwargs.get("auto_players", ())))
            return real(self, *args, **kwargs)

        return spy

    cls.__init__ = make_spy()

sys.argv = ["selfplay.py", MAP, FRAMES]
try:
    runpy.run_path("selfplay.py", run_name="__main__")
except SystemExit:
    pass

print("\n" + "=" * 72)
print(f"{len(TARGETS)} classes under game/ declare auto_players")
print(f"{len(seen)} of them were constructed in this battle")

fed, unfed, built_empty = [], [], []
for name in sorted(seen):
    values = seen[name]
    if all(v for v in values):
        fed.append(name)
    elif any(v for v in values):
        built_empty.append((name, values))
    else:
        unfed.append(name)

never_built = sorted(set(TARGETS) - set(seen))

print(f"\n  fed a non-empty auto_players : {len(fed)}")
print(f"  built with ()                : {len(unfed)}")
print(f"  inconsistent between builds  : {len(built_empty)}")
print(f"  never constructed at all     : {len(never_built)}")

values = {v for vs in seen.values() for v in vs if v}
print(f"\n  distinct non-empty values handed out: {sorted(values)}")

ok = True
if unfed:
    ok = False
    print("\n  *** CONSTRUCTED WITH () - the AI pays an API call for these:")
    for name in unfed:
        print(f"      {name}  ({TARGETS[name]})")
if built_empty:
    ok = False
    print("\n  *** BUILT INCONSISTENTLY:")
    for name, vs in built_empty:
        print(f"      {name}: {vs}")
if len(values) > 1:
    ok = False
    print("\n  *** MORE THAN ONE ANSWER to 'who is the AI' reached the controllers.")
if missing_import:
    print("\n  (modules that would not import, not counted:)")
    for line in missing_import:
        print(f"      {line}")

# Never-constructed is NOT a failure: plenty of these belong to armies this
# battle does not field. Printed so the number can be read, not judged.
if never_built:
    print(f"\n  not fielded by this battle ({len(never_built)}): "
          f"{', '.join(never_built[:6])}{' ...' if len(never_built) > 6 else ''}")

print("\n" + ("PASS - one fact, and every fielded controller got it" if ok else "FAIL"))
sys.exit(0 if ok else 1)
