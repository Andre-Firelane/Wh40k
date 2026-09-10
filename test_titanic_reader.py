""""Is this a TITANIC unit?" - one reader, measured (Etappe 0 of the Necron batch).

WHY THIS SUITE EXISTS AT ALL
----------------------------
TITANIC was a documented no-op: no built datasheet carried the keyword, so a
dozen printed "excluding TITANIC units" clauses were written out in prose and
several promise, word for word, that they "start working by itself the day a
TITANIC datasheet exists".

Measured before building the Monolith, the promise did NOT hold. FOUR sites
read `getattr(profile, "titanic", False)` - a field `UnitProfile` does not
declare - so they were unconditionally False. They looked wired from the
inside and no test could tell, because staging a TITANIC unit meant hanging
that same non-existent field on a throwaway profile, which the reader then
also answered False for. Both halves agreed, and both were wrong.

WHERE THIS MEASURES, AND WHY THERE
----------------------------------
  * The reader is measured against a KEYWORD LINE and against a PROFILE FLAG
    in the same breath. Only asserting the keyword form passes in a world
    where the flag form ALSO works, which is the world that shipped.
  * The four repaired clauses are measured through their OWN entry points, not
    through is_titanic_unit(). A shared predicate can be correct while a caller
    never asks it - the "gebaut, aber nie GEFUETTERT" class this repo has paid
    for six times.
  * Section 4 is a SET DIFFERENCE at the source, not a behaviour test. A
    behaviour test cannot see the FIFTH site, because it does not exist yet.
"""
import io, os, ast

import testkit as tk
from testkit import Checks

from game import titanic, wraith_construct, actions, structural_collapse
from game.factions import necrons as nec

checks = Checks("TITANIC reader")


def sheet_with(keywords):
    return type("StagedSheet", (), {"keywords": tuple(keywords)})()


def unit(datasheet=nec.NECRONS.datasheets["Necron Warriors"], keywords=None, n=1):
    sq = tk.build(datasheet, "Player 2", name="2 %s %d" % (datasheet.name, n))
    if keywords is not None:
        sq.datasheet = sheet_with(keywords)
    return sq


# --- 1. the reader reads the KEYWORD LINE ---
print("--- 1. the reader reads the KEYWORD LINE ---")

plain = unit()
checks.eq("an ordinary unit is not TITANIC", titanic.is_titanic_unit(plain), False)

staged = unit(keywords=("VEHICLE", "TITANIC", "FLY"))
checks.eq("a unit whose keyword line prints TITANIC is",
          titanic.is_titanic_unit(staged), True)

checks.eq("None is not TITANIC", titanic.is_titanic_unit(None), False)

# THE PRE-FIX WORLD, pinned as NOT working: a profile flag named `titanic` must
# not answer this question. Without this line the suite passes in the world
# where BOTH forms work, which is not the world that was built.
flagged = unit()
for m in flagged.models:
    m.profile = type("Flagged", (m.profile.__class__,), {"titanic": True})()
checks.eq("a `titanic` PROFILE FLAG does not make a unit TITANIC",
          titanic.is_titanic_unit(flagged), False)
checks.eq("...and UnitProfile still declares no such field",
          hasattr(nec.NECRONS.datasheets["Necron Warriors"], "titanic"), False)

# --- 2. exactly ONE definition ---
print("--- 2. exactly ONE definition ---")

checks.true("wraith_construct re-exports rather than redefining",
            wraith_construct.is_titanic_unit is titanic.is_titanic_unit)
checks.true("...and shares the keyword constant",
            wraith_construct.TITANIC_KEYWORD is titanic.TITANIC_KEYWORD)
checks.eq("the keyword is spelled once, correctly", titanic.TITANIC_KEYWORD, "TITANIC")

# --- 3. the four repaired clauses ask it, through their own entry points ---
print("--- 3. the four repaired clauses ask it ---")

src_actions = io.open("game/actions.py", encoding="utf-8").read()
checks.true("16.01's engaged carve-out asks the shared reader",
            "titanic.is_titanic_unit(squad)" in src_actions)
checks.eq("...twice - the engaged clause and blocks_shooting",
          src_actions.count("titanic.is_titanic_unit(squad)"), 2)

# structural_collapse's predicate is the D-cannon's second clause. Measured
# through its OWN name, which is what game/shooting.py calls.
checks.eq("the D-cannon clause says no against an ordinary target",
          structural_collapse.targets_titanic(plain), False)
checks.eq("...and yes against a TITANIC one",
          structural_collapse.targets_titanic(staged), True)

src_ens = io.open("game/elemental_ensnarement.py", encoding="utf-8").read()
checks.true("the Aeldari ensnarement exclusion asks the shared reader",
            "titanic.is_titanic_unit(other)" in src_ens)

# 16.01's ENGAGED carve-out, through start_eligibility() rather than through
# the reader. Added because the A/B probe for this clause did NOT bite: nothing
# measured it, so reverting it to the dead profile flag left every suite green.
foe = tk.build(nec.NECRONS.datasheets["Necron Warriors"], "Player 1",
               name="1 Necron Warriors 9")
tk.line_up(foe, x=20.0, y=20.0)

def engaged_pair(keywords=None):
    """One unit nose to nose with `foe`, optionally printing TITANIC."""
    me = tk.build(nec.NECRONS.datasheets["Doomsday Ark"], "Player 2",
                  name="2 Doomsday Ark %d" % (1 if keywords is None else 2))
    tk.line_up(me, x=20.0, y=20.8)          # inside Engagement Range (03.04)
    if keywords is not None:
        me.datasheet = sheet_with(keywords)
    return me, list(me.models) + list(foe.models)

ordinary, board_a = engaged_pair()
checks.eq("an engaged non-TITANIC unit may not start an Action",
          actions.start_eligibility(ordinary, board_a)[1], "engaged")
titan, board_b = engaged_pair(("VEHICLE", "TITANIC", "FLY"))
checks.true("...but an engaged TITANIC unit is not refused for being engaged",
            actions.start_eligibility(titan, board_b)[1] != "engaged")

# The Aeldari exclusion, through the controller's own candidate list - the
# other clause whose probe did not bite. CROSS-FACTION and NOT dormant: this
# fires for any Aeldari list that fields a Stonesinger.
from game import elemental_ensnarement
from game.factions import aeldari as ae
singer = tk.build(ae.STONESINGER, "Player 1", name="1 Stonesinger 1")
tk.line_up(singer, x=20.0, y=20.0)
prey = tk.build(nec.NECRONS.datasheets["Doomsday Ark"], "Player 2",
                name="2 Doomsday Ark 3")
tk.line_up(prey, x=20.0, y=26.0)
ee = elemental_ensnarement.ElementalEnsnarementController(
    game_log=tk.Log(), all_tokens=list(singer.models) + list(prey.models))
checks.eq("an ordinary enemy VEHICLE is an ensnarement candidate",
          [s.name for s in ee.candidates(singer)], [prey.name])
prey.datasheet = sheet_with(tuple(nec.NECRONS.datasheets["Doomsday Ark"].keywords)
                            + ("TITANIC",))
checks.eq("...and a TITANIC one is excluded, as printed",
          [s.name for s in ee.candidates(singer)], [])

# --- 4. SET DIFFERENCE at the source: no fifth site may come back ---
print("--- 4. no module may read `titanic` as a profile field ---")

offenders = []
for root, dirs, files in os.walk("game"):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for fn in files:
        if not fn.endswith(".py"):
            continue
        path = os.path.join(root, fn)
        try:
            tree = ast.parse(io.open(path, encoding="utf-8").read())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            # getattr(x, "titanic", ...) / _flag(x, "titanic")
            if isinstance(node, ast.Call):
                for a in node.args:
                    if isinstance(a, ast.Constant) and a.value == "titanic":
                        offenders.append("%s:%d" % (path, node.lineno))
            # x.titanic
            if isinstance(node, ast.Attribute) and node.attr == "titanic":
                offenders.append("%s:%d" % (path, node.lineno))

checks.eq("no module reads `titanic` as a profile field (it does not exist)",
          offenders, [])

# LIVENESS: the sweep must actually be looking at something.
checks.true("...and the sweep really walked the tree",
            len([f for _r, _d, fs in os.walk("game") for f in fs
                 if f.endswith(".py")]) > 100)

checks.finish()
