"""The SHAPE of ai/agent_driver.py, guarded at the source.

1) No top-level name is defined twice. From the initial commit until
   2026-09-09 the file carried a byte-for-byte copy of its own per-model
   movement core (lines 1121-2621 duplicated 2626-4185: 39 module-level names,
   38 identical and one - _advance_toward_per_model - an OLDER generation
   without the packed candidate or the fallback round). Python binds the
   second definition, so the first copy was dead, and any edit made in it did
   nothing. A behaviour test cannot see that; only the source can.

2) The charge ladder has ONE definition. _handle_charge() climbs
   _run_charge_attempts(), and so does measure_reported_moves.py - a harness
   that copies the loop measures a ladder the AI may no longer climb.

Run: python test_agent_driver_shape.py
"""
import ast
import collections
import os

from testkit import Checks

HERE = os.path.dirname(os.path.abspath(__file__))
DRIVER = os.path.join(HERE, "ai", "agent_driver.py")
HARNESS = os.path.join(HERE, "measure_reported_moves.py")

c = Checks("agent_driver shape")


def duplicate_top_level_names(source):
    """Every module-level def/class/assignment name bound more than once."""
    names = collections.Counter()
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names[node.name] += 1
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names[target.id] += 1
    return sorted(name for name, n in names.items() if n > 1)


def function_source(tree, name):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def calls_in(node):
    out = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            f = sub.func
            out.append(f.id if isinstance(f, ast.Name) else getattr(f, "attr", None))
    return out


with open(DRIVER, encoding="utf-8") as handle:
    driver_src = handle.read()
tree = ast.parse(driver_src)

print("1) no module-level name is defined twice")
dups = duplicate_top_level_names(driver_src)
c.eq("ai/agent_driver.py binds every top-level name exactly once", dups, [])

# The checker must BITE: the exact shape that was shipped - a second copy of a
# function appended to the module - has to be reported, else the line above
# would pass on an empty checker.
probe = driver_src + "\n\ndef _advance_toward_per_model(*a, **k):\n    return None\n"
c.eq("...and the checker reports a duplicated function when there is one",
     duplicate_top_level_names(probe), ["_advance_toward_per_model"])
c.true("the live _advance_toward_per_model still offers the packed candidate "
       "(the dead copy did not)",
       "_place_packed" in ast.get_source_segment(
           driver_src, function_source(tree, "_advance_toward_per_model_impl")))

print("2) the charge ladder is defined once and climbed from both sides")
ladder = function_source(tree, "_run_charge_attempts")
handler = function_source(tree, "_handle_charge")
c.true("_run_charge_attempts exists at module level", ladder is not None)
c.true("_handle_charge climbs it", "_run_charge_attempts" in calls_in(handler))
c.true("_handle_charge no longer carries its own approach loop",
       "CHARGE_APPROACH_PLAN" not in ast.get_source_segment(driver_src, handler))
c.true("the ladder tries every approach in CHARGE_APPROACH_PLAN",
       "CHARGE_APPROACH_PLAN" in ast.get_source_segment(driver_src, ladder))
c.true("the ladder rolls a failed attempt back through cancel_move",
       "cancel_move" in calls_in(ladder))
with open(HARNESS, encoding="utf-8") as handle:
    harness_src = handle.read()
c.true("measure_reported_moves.py climbs the same ladder, not a copy",
       "_run_charge_attempts(" in harness_src and "CHARGE_APPROACH_PLAN" not in harness_src)

c.finish()
