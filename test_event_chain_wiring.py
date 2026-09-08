"""main.py's event chain, checked at the SOURCE.

The reported crash was `NameError: name 'board_rect' is not defined` at the
Isha's Fury mortal-wound branch. Two more defects sat in the same two
branches behind it: a `token_at_event()` call with the old four-argument
signature, and no MOUSEBUTTONDOWN guard at all (so the branch also reached
for `event.pos` on a KEYDOWN).

None of it was reachable by any behaviour test. These branches only run
while one specific ability owes a mortal-wound allocation, so a stale name
and a stale call signature could sit there indefinitely - the same
"built, never exercised" class as VengefulStarsController's missing feed
and Path of the Outcast's missing dice acknowledgement, both of which also
needed a SOURCE guard rather than a behaviour test to catch.

Section 1 is the general one: no free name inside main() may be unbound.
That is the check that reproduces the reported crash exactly, and it covers
every future line of that ~4000-line function, not just these two branches.
Sections 2 and 3 pin the two specific drifts underneath it.

SECTION 1b IS THE SAME SWEEP OVER THE WHOLE ENGINE, and it exists because the
class turned up a second time somewhere else: `NameError: name 'rect' is not
defined` out of Renderer.draw_objectives(), raised only while the cursor sat
on an objective's info icon. The rotated-outline work had renamed that local
to outline_rect and left two reads behind. main.py was never the special
thing - a branch nothing exercises is, and those are everywhere.
"""
import ast
import builtins
import importlib
import io
import os
import re
import sys

from testkit import Checks

ck = Checks("main.py event chain wiring")
SRC = io.open("main.py", encoding="utf-8").read()
TREE = ast.parse(SRC)
MAIN = next(n for n in TREE.body
            if isinstance(n, ast.FunctionDef) and n.name == "main")


def _bound_names(fn):
    """Every name that gets bound anywhere inside `fn` (any nesting)."""
    bound = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bound.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.arg):
            bound.add(node.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                bound.add((a.asname or a.name).split(".")[0])
    return bound


def _module_names(body, names=None):
    """TRUE module-level bindings: top-level assignments, imports, defs and
    classes, plus the same inside module-level if/try/with/for.

    DELIBERATELY DOES NOT DESCEND into function or class bodies, and that is
    the whole check. An earlier version walked everything, so a local of one
    function counted as "defined" for every other function in the file - which
    is exactly the hole the objective-hover crash fell through: `rect` is a
    local of _render_static_layer(), and draw_objectives() read a name by that
    spelling that no scope of its own ever bound. Measured on main.py, the
    permissive version forgave 441 extra names."""
    names = set() if names is None else names
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                names.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                    names.add(sub.id)
        elif isinstance(node, (ast.If, ast.Try, ast.With, ast.For, ast.While)):
            _module_names(node.body, names)
            _module_names(getattr(node, "orelse", []), names)
            for handler in getattr(node, "handlers", []):
                _module_names(handler.body, names)
    return names


def _outermost_functions(tree):
    """Every top-level function and every method, but nothing nested inside
    them - _bound_names() already covers a nested scope from the outside, and
    analysing both would report an inner function's own locals twice."""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    yield sub


def _unbound_in(tree):
    """(function name, unbound name, line) for every name a function READS that
    nothing binds - not a local, not a true module-level name, not a builtin."""
    module_level = _module_names(tree.body)
    out = []
    for fn in _outermost_functions(tree):
        bound = _bound_names(fn)
        for node in ast.walk(fn):
            if (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
                    and node.id not in bound
                    and node.id not in module_level
                    and not hasattr(builtins, node.id)):
                out.append((fn.name, node.id, node.lineno))
    return sorted(set(out))


# --------------------------------------------------------- 1. unbound names
print("\n=== 1. no undefined name is read inside main() ===")

bound = _bound_names(MAIN)
# The reported crash was exactly one entry here: ('main', 'board_rect', 3021).
ck.eq("free names in main() that are bound nowhere",
      [(n, line) for fn, n, line in _unbound_in(TREE) if fn == "main"], [])

# The board rectangle has exactly one name, and this is it. A branch that
# invents a second one is how the crash happened in the first place.
ck.true("board_rect_screen is the bound name for the board rect",
        "board_rect_screen" in bound)
ck.eq("no bare `board_rect` survives anywhere in main.py",
      SRC.count("board_rect.collidepoint"), 0)


# --------------------------------------------- 1b. ...and in the whole engine
print("\n=== 1b. no undefined name is read anywhere in game/ or ai/ ===")

# main.py was not the only place this could happen, and a SECOND report proved
# it: "NameError: name 'rect' is not defined" from Renderer.draw_objectives(),
# raised only while the cursor sat on an objective's info icon. The
# rotated-outline work had renamed that local to outline_rect and left two uses
# behind; no behaviour test reaches a hover branch, so it had been crashing
# nobody since.
#
# Same class as the Isha's Fury branch section 1 exists for, in a different
# file - so the sweep is the same sweep, pointed at every module instead of at
# one function. It costs about a second and covers every line of the engine,
# which is the only kind of guard that catches a branch nothing exercises.
ENGINE_DIRS = ("game", "ai")
engine_files = sorted(
    os.path.join(base, name)
    for root in ENGINE_DIRS
    for base, _, names in os.walk(root)
    if "__pycache__" not in base
    for name in names
    if name.endswith(".py")
)
engine_unbound = []
for path in engine_files:
    for fn, name, line in _unbound_in(ast.parse(io.open(path, encoding="utf-8").read())):
        engine_unbound.append(f"{path}:{line} {fn}() reads unbound {name!r}")
ck.eq("free names in game/ or ai/ that are bound nowhere", engine_unbound, [])
# ...and the sweep is actually looking at something. A guard that quietly
# scanned nothing would report the same empty list.
ck.true(f"the sweep sees the whole engine ({len(engine_files)} modules)",
        len(engine_files) > 200)
ck.true("...including the renderer, where the second report came from",
        os.path.join("game", "renderer.py") in engine_files)


# ------------------------------------------------- 2. token_at_event() shape
print("\n=== 2. every token_at_event() call uses the current signature ===")

# game/input_handler.py: def token_at_event(self, tokens, board, event_pos)
calls = [n for n in ast.walk(MAIN)
         if isinstance(n, ast.Call)
         and isinstance(n.func, ast.Attribute)
         and n.func.attr == "token_at_event"]
ck.true("main() actually calls token_at_event (guard is live)", len(calls) > 0)

bad_arity = [(c.lineno, len(c.args)) for c in calls if len(c.args) != 3]
ck.eq("token_at_event calls with the wrong number of arguments", bad_arity, [])

# Order matters as much as arity: `(tokens, event, camera)` is three
# arguments too, and it fails with AttributeError instead of TypeError.
shapes = {}
for c in calls:
    shapes[c.lineno] = tuple(ast.unparse(a) for a in c.args)
wrong_shape = sorted(
    (line, shape) for line, shape in shapes.items()
    if shape != ("state.tokens", "board", "event.pos")
)
ck.eq("token_at_event calls not of the form (state.tokens, board, event.pos)",
      wrong_shape, [])


# ------------------------------------- 3. mortal-wound branches are guarded
print("\n=== 3. every pending_damage_choice branch guards its event ===")

# A branch that reads event.pos without first checking the event TYPE will
# crash on the next KEYDOWN, which is a different crash from the reported
# one but reachable from the same states.
def _branch_tests(fn):
    """Every `elif <x>.pending_damage_choice is not None:` test in the chain,
    paired with the source of its body."""
    out = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.If):
            continue
        test = ast.unparse(node.test)
        if ".pending_damage_choice is not None" not in test:
            continue
        if not test.endswith("is not None"):
            continue  # a compound gate (the phase-advance lock), not a branch
        body = "\n".join(ast.unparse(s) for s in node.body)
        out.append((node.lineno, test, body))
    return out


branches = _branch_tests(MAIN)
ck.true("found the mortal-wound branches (guard is live)", len(branches) >= 7)

unguarded = []
for line, test, body in branches:
    if "event.pos" not in body:
        continue
    if "event.type == pygame.MOUSEBUTTONDOWN" not in body or "event.button == 1" not in body:
        unguarded.append((line, test))
ck.eq("branches that read event.pos without a MOUSEBUTTONDOWN guard",
      sorted(unguarded), [])

# And each one confines its click to the board before resolving it.
unbounded = []
for line, test, body in branches:
    if "token_at_event" in body and "board_rect_screen.collidepoint" not in body:
        unbounded.append((line, test))
ck.eq("branches that resolve a board click without a board-rect check",
      sorted(unbounded), [])

# The two that were broken must be in the set the checks above ran over -
# otherwise this file could pass by not looking at them.
names = " ".join(t for _, t, _ in branches)
ck.true("the Isha's Fury branch is covered", "ishas_fury_controller" in names)
ck.true("the grenade pack branch is covered", "grenade_pack_controller" in names)


# ---------------------------------------------------------------------------
# 4. CONSTRUCTION ORDER inside main()
#
# main() is a ~4000-line function, and a controller wired to a collaborator
# that is built FURTHER DOWN raises UnboundLocalError on the first real start.
# No suite can see it: they build controllers directly and never run main().
# Hit three times in one session while adding Death Guard (a listener
# registered ~100 lines before its controller, a Stratagem block ~160 lines
# before fight_controller, and a collaborator assigned 15 lines before its own
# constructor), every time caught only by smoke_pregame.py - which is minutes
# rather than the seconds this takes.
#
# The rule checked here is narrow and exact: for a statement `A.b = C` at the
# top level of main()'s body, where A and C are BOTH plain locals that main()
# assigns somewhere, both assignments have to come first. That is the shape all
# three mistakes had. It deliberately does NOT try to order every use of every
# name - control flow makes that undecidable, and the false positives would
# make the guard worthless.
# ---------------------------------------------------------------------------
print("\n=== 4. construction order in main() ===")

# MAIN is already main()'s FunctionDef node - see the top of this file.
_main_fn = MAIN
ck.true("found main()", _main_fn is not None)


_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


def _own_level(fn):
    """Every node of `fn` that runs at ITS level - i.e. without descending into
    a nested def/lambda/class. The nested defs themselves are included (their
    NAME is a local of fn), their bodies are not.

    Scope-awareness is load-bearing, not tidiness. This guard is about
    CONSTRUCTION ORDER: "was the collaborator built by the time this line
    runs". A name assigned inside a nested helper is not a local of main() at
    all, and a statement inside one does not run during construction - it runs
    when the helper is called, arbitrarily later. Mixing the two produced a
    real false positive: main() has a nested helper whose PARAMETER is `squad`
    and which does `squad.embarked_in = transport`, and the moment any OTHER
    nested helper assigned a variable called `squad`, the walk-everything
    version reported that line as running "before squad is built".

    No coverage is lost by narrowing it. Whether a name is bound AT ALL is
    section 1's job; this section only answers whether it is bound YET.
    Measured on the current main(): 23 nested-only names stop counting as
    locals, and the set of inspected `a.b = c` statements drops from 40 to
    39 - the one that goes is precisely that nested false positive."""
    out = []
    stack = [node for node in fn.body if not isinstance(node, _SCOPES)]
    out.extend(node for node in fn.body if isinstance(node, _SCOPES))
    while stack:
        node = stack.pop()
        out.append(node)
        for child in ast.iter_child_nodes(node):
            if isinstance(child, _SCOPES):
                out.append(child)
            else:
                stack.append(child)
    return out


def _first_binding_line(nodes):
    """LOWEST line at which each plain local name is assigned.

    min(), not "the first one the walk happens to reach": the node order here
    is a traversal order, not source order, so setdefault() reported whichever
    branch of an if/elif the walk entered first. That produced an honest-
    looking but wrong line number in the failure message - the thing a reader
    of this guard acts on."""
    out = {}
    for node in sorted(nodes, key=lambda n: getattr(n, "lineno", 0)):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            targets = [node.target]
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(node.name, node.lineno)
        for target in targets:
            if isinstance(target, ast.Name):
                out.setdefault(target.id, node.lineno)
    return out


_main_level = _own_level(_main_fn)
_bound_at = _first_binding_line(_main_level)

_too_early = []
for node in _main_level:
    if not isinstance(node, ast.Assign) or len(node.targets) != 1:
        continue
    target = node.targets[0]
    if not isinstance(target, ast.Attribute) or not isinstance(target.value, ast.Name):
        continue
    if not isinstance(node.value, ast.Name):
        continue
    owner, source = target.value.id, node.value.id
    for name in (owner, source):
        line = _bound_at.get(name)
        if line is not None and line > node.lineno:
            _too_early.append((node.lineno, f"{owner}.{target.attr} = {source}",
                               f"{name} is only assigned at line {line}"))

ck.eq("no `a.b = c` in main() runs before a or c is built",
      sorted(_too_early), [])

# The guard has to be LIVE - if the shape it looks for stopped occurring, it
# would pass by looking at nothing.
_pairs = sum(1 for node in _main_level
             if isinstance(node, ast.Assign) and len(node.targets) == 1
             and isinstance(node.targets[0], ast.Attribute)
             and isinstance(node.targets[0].value, ast.Name)
             and isinstance(node.value, ast.Name))
ck.true(f"the guard is live - it inspected {_pairs} collaborator assignments",
        _pairs >= 10)

print("\n=== 5. every registered target reaction implements the protocol ===")

# THE BUG THIS PINS was game-breaking and invisible to every suite:
# KrootPackmatesController was registered in main()'s shooting_target_reactions
# tuple but implemented only on_targets_selected(), whose docstring claimed to
# BE "ShootingController.target_reactions' contract". The real contract is
# maybe_offer(attacking_squad, target_squad, melee=False), so EVERY game died
# with AttributeError the first time any unit selected a shooting target - in
# any faction, since the tuple is iterated unconditionally.
#
# A behaviour test could not see it (no suite drives main()'s tuples), and a
# name-count guard would not either. What catches it is asking the CLASSES
# named in those tuples whether they have the method.

_REACTION_TUPLES = ("shooting_target_reactions", "fight_target_reactions")


def _tuple_members(fn, name):
    """The variable names listed in `name = (a, b, c)` inside main()."""
    for node in ast.walk(fn):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == name
                and isinstance(node.value, (ast.Tuple, ast.List))):
            return [e.id for e in node.value.elts if isinstance(e, ast.Name)]
    return []


def _constructed_class(fn, var):
    """The class name in `var = ClassName(...)` inside main()."""
    for node in ast.walk(fn):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == var
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)):
            return node.value.func.id
    return None


_CLASS_IMPORTS = {}
for _node in ast.walk(TREE):
    if isinstance(_node, ast.ImportFrom) and _node.module:
        for _alias in _node.names:
            _CLASS_IMPORTS[_alias.asname or _alias.name] = _node.module

_checked = 0
for _tuple_name in _REACTION_TUPLES:
    _members = _tuple_members(MAIN, _tuple_name)
    ck.true(f"{_tuple_name} is a tuple of named controllers", bool(_members))
    for _var in _members:
        _cls_name = _constructed_class(MAIN, _var)
        _module = _CLASS_IMPORTS.get(_cls_name)
        if _cls_name is None or _module is None:
            ck.true(f"{_var}'s class can be resolved", False)
            continue
        _cls = getattr(__import__(_module, fromlist=[_cls_name]), _cls_name)
        ck.true(f"{_cls_name} implements maybe_offer() for {_tuple_name}",
                callable(getattr(_cls, "maybe_offer", None)))
        _checked += 1

# Live-guard: if the tuples stopped being found this section would pass by
# inspecting nothing, which is the failure mode of every source guard.
ck.true(f"the guard is live - it resolved {_checked} reaction controllers",
        _checked >= 4)


# ---------------------------------------------------------------------------
# 6. every mortal-wound choice main.py BLOCKS ON can also be RESOLVED
# ---------------------------------------------------------------------------
print("\n=== 6. blocked-on damage choices are clickable and drawn ===")

# Real user report: "die ki hat nach der schussphase in ihrem zug 2 einfach
# aufgehört zu agieren". The log ended on "Spore-laced Shock Waves: <unit>
# suffers 3 mortal wound(s)" and nothing after it.
#
# Three controllers - lethal_ichor, spore_laced, sickening_impact - were asked
# about their pending_damage_choice in main()'s _blocked() (so the phase could
# not advance) AND in _any_pending_damage_choice() (so run_ai_action() was
# skipped), and had no click branch in the event chain at all. Nothing could
# ever clear the choice they were being blocked on: a total deadlock, reachable
# only against Death Guard, which is why it survived this long.
#
# The "built, never fed" class in the one variant no behaviour test sees -
# built, BLOCKED ON, never made clickable. A unit test drives the controller
# directly and passes; a smoke run never reaches the ability at all. Only the
# source can answer it, which is why this lives here and not in a suite.

_ASKED = set(re.findall(r"(\w+_controller)\.pending_damage_choice", SRC))
_CLICKABLE = set(re.findall(r"(\w+_controller)\.choose_damage_model\(", SRC))
_DRAWN = set(re.findall(
    r"draw_damage_choice_highlight\([^)]*?(\w+_controller)\.pending_damage_choice", SRC))

# Live-guard first: a regex that stopped matching would make every check below
# pass by inspecting nothing - the failure mode of every source guard here.
ck.true("the guard is live - it found %d controllers with a damage choice" % len(_ASKED),
        len(_ASKED) >= 12)

ck.eq("every controller main.py asks about has a click branch that resolves it",
      sorted(_ASKED - _CLICKABLE), [])

ck.eq("...and the board draws which models are eligible, so the human can see it",
      sorted(_ASKED - _DRAWN), [])

# The three from the report, named individually: a regression that brought back
# exactly one of them would otherwise only show up as a list diff.
_REPORTED = ("lethal_ichor_controller", "spore_laced_controller",
             "sickening_impact_controller")
for _name in _REPORTED:
    ck.true("%s is clickable (the reported hang)" % _name, _name in _CLICKABLE)
    ck.true("%s is drawn on the board" % _name, _name in _DRAWN)

# The two gates are what turn an unresolvable choice into a DEADLOCK rather
# than a missed opportunity, so pin that they really do wait on these.
_GATE = "def _has_unresolved_declaration("
_BLOCKED_SRC = SRC[SRC.index(_GATE):] if _GATE in SRC else ""
ck.true("the phase-advance gate was found", bool(_BLOCKED_SRC))
for _name in _REPORTED:
    ck.true("%s is one of the controllers the phase gate waits on" % _name,
            ("%s.pending_damage_choice is not None" % _name) in _BLOCKED_SRC
            or ("%s.is_busy" % _name) in _BLOCKED_SRC)


# ---------------------------------------------------------------------------
# 7. EVERY runtime [ASSAULT] grant is read by the rule-10.05 gate
# ---------------------------------------------------------------------------
print("\n=== 7. every [ASSAULT] grant reaches weapon_has_assault() ===")

# THE DEFECT THIS CATCHES, reported by a player against Protocol of the Sudden
# Storm: "ich konnte nach dem vorruecken nicht mehr schiessen mit den necron
# kriegern."
#
# [ASSAULT] is read in TWO unrelated places, and a grant wired to only one of
# them looks finished while doing nothing:
#   * ShootingController._adjusted_weapon() - the damage maths. Easy to wire,
#     easy to test, and it is what every unit test of such a Stratagem checks.
#   * coldstar.weapon_has_assault() - reached from
#     shooting.available_shooting_types(), and the ONLY thing that decides
#     whether a unit that Advanced may shoot at all (rule 10.05). This is the
#     entire reason [ASSAULT] gets granted in the first place.
# Three of the four shipped grants were wired to the chain and not the gate.
# A behaviour test cannot see a FOURTH one appearing, so this is a source
# sweep: any module that hands out `.assault = True` at runtime must be named
# inside weapon_has_assault()'s body.
_COLDSTAR = io.open(os.path.join("game", "coldstar.py"), encoding="utf-8").read()
_WHA = "def weapon_has_assault("
ck.true("weapon_has_assault() was found", _WHA in _COLDSTAR)
_WHA_BODY = _COLDSTAR[_COLDSTAR.index(_WHA):] if _WHA in _COLDSTAR else ""

# Documented gaps, named rather than silently subtracted. EMPTY - and the one
# entry it used to hold is why this comment is here. `_ASSAULT_GRANT_GAPS =
# {"montka"}` was justified, in this file and again in game/coldstar.py, with
# "no shipped army list fields Mont'ka, so it is dormant". That was true when
# it was written and stopped being true when the tau_montka roster was added:
# the justification went stale while the assertion stayed green, which is the
# failure mode a NAMED gap has and a set difference does not.
#
# Measured on that roster before the fix: Killing Blow active for all 14 of its
# units in rounds 1-3, granting [ASSAULT] to 102 of their 151 ranged weapons,
# none of which this gate could see. It is closed via Squad.montka_killing_blow
# (game/montka.py's refresh_killing_blow()), so the round condition reaches a
# function that is handed only (weapon, squad).
#
# A future entry here must carry the measurement that says it is dormant, not a
# recollection of one.
_ASSAULT_GRANT_GAPS = set()

_grantors = sorted(
    name[:-3]
    for name in os.listdir("game")
    if name.endswith(".py") and name[:-3] not in ("weapons", "coldstar")
    and "assault = True" in io.open(os.path.join("game", name), encoding="utf-8").read()
)
ck.true("the sweep found the known grantors (it is not vacuous)",
        len(_grantors) >= 4)
for _mod in _grantors:
    if _mod in _ASSAULT_GRANT_GAPS:
        ck.true("%s is the documented gap, and says so in weapon_has_assault()" % _mod,
                _mod in _WHA_BODY)
        continue
    ck.true("%s's [ASSAULT] grant is read by the Advance gate" % _mod,
            ("%s.is_active(squad)" % _mod) in _WHA_BODY
            or ("%s.applies(squad)" % _mod) in _WHA_BODY
            or ("%s.grants_assault(squad)" % _mod) in _WHA_BODY)


# ---------------------------------------------------------------------------
# 8. NO END-OF-PHASE OFFER READS turn_tracker.turn_owner
# ---------------------------------------------------------------------------
print()
print("=== 8. end-of-phase offers use mover_before, not turn_owner ===")

# advance_turn_phase() calls turn_tracker.advance_phase() near the TOP and runs
# every end-of-phase reaction offer AFTERWARDS. Fight is the last phase, so by
# then turn_owner has already flipped to the next player - reading it there
# names the wrong side. Four offers at the end-of-Fight-phase seam did exactly
# that, and their own comments claimed they were on OPPOSITE sides of each
# other while all four passed the identical expression. Reported for Wall of
# Mirrors: "Frage nach Wall of Mirrors kam am Anfang der Gegner Runde".
#
# mover_before (captured before the advance) is the correct value and was
# already sitting unused two lines above them. A behaviour test cannot see a
# FIFTH offer being added, so this is a source sweep over the statements that
# run after the advance.
_ADV = "turn_tracker.advance_phase()"
def _advance_turn_phase_tail():
    """main()'s advance_turn_phase() body, from advance_phase() onward."""
    for node in ast.walk(MAIN):
        if isinstance(node, ast.FunctionDef) and node.name == "advance_turn_phase":
            body = ast.get_source_segment(SRC, node) or ""
            return body.split(_ADV, 1)[1] if _ADV in body else ""
    return ""


_TAIL = _advance_turn_phase_tail()
ck.true("advance_turn_phase() was found and does advance the phase", bool(_TAIL))

# The offers themselves. Each is named so a fifth one cannot be added silently:
# a call taking a player argument at this seam has to appear here.
_END_OF_PHASE_OFFERS = (
    "wall_of_mirrors_controller.offer_at_end_of_fight_phase(",
    "cost_of_victory_controller.offer_at_end_of_fight_phase(",
    "webway_tunnel_controller.offer_at_end_of_fight_phase(",
    "elemental_ensnarement_controller.offer_at_end_of_fight(",
    "resurrection_orb_controller.offer_at_end_of_phase(",
    # The two Aeldari offers that were NOT on this list, and were exactly the
    # bug it exists for: both read the live clock in their own can_use() and
    # were therefore never offered at all - Skyborne Sanctuary in both of its
    # printings, Overflight in both halves of its WHEN. Neither takes an owner
    # in its argument list: Skyborne's phase "belongs to nobody", and
    # Overflight is handed phase_before/mover_before instead of reading either.
    "_skyborne.offer_at_end_of_fight_phase(",
    "overflight_controller.offer_at_end_of_phase(",
)
for _call in _END_OF_PHASE_OFFERS:
    ck.true("%s is still made at this seam" % _call.split("(")[0], _call in _TAIL)
    _args = _TAIL.split(_call, 1)[1]
    # Up to the matching close paren, shallowly - enough to see the arguments.
    _depth, _end = 1, 0
    for _i, _ch in enumerate(_args):
        if _ch == "(":
            _depth += 1
        elif _ch == ")":
            _depth -= 1
            if _depth == 0:
                _end = _i
                break
    _arglist = _args[:_end]
    ck.true("%s takes mover_before, not the flipped turn_owner"
            % _call.split("(")[0],
            "turn_tracker.turn_owner" not in _arglist)

# ...and the value it must use is still captured BEFORE the advance.
ck.true("mover_before is captured before advance_phase()",
        "mover_before = turn_tracker.turn_owner" in SRC.split(_ADV, 1)[0])

# The three armed windows are closed once per boundary, and BEFORE the offers
# above arm new ones - otherwise a window would survive its own phase.
_RESETS = ("wall_of_mirrors_controller.reset_phase()",
           "cost_of_victory_controller.reset_phase()",
           "webway_tunnel_controller.reset_phase()",
           # Both Skyborne printings share one loop; Overflight's reset
           # ROTATES its kill ledger rather than clearing it, because this
           # block runs BEFORE the offer that reads it.
           "_skyborne.reset_phase()",
           "overflight_controller.reset_phase()")
# THE ANCHOR IS THE EARLIEST OFFER, not the first entry of the tuple. Overflight
# is offered above Wall of Mirrors, so comparing against a fixed index would
# quietly measure the ordering against the wrong call.
_FIRST_OFFER = min(_TAIL.index(_c) for _c in _END_OF_PHASE_OFFERS if _c in _TAIL)
for _reset in _RESETS:
    ck.true("%s is cleared each phase" % _reset.split(".")[0], _reset in _TAIL)
    ck.true("...before that boundary's own offers arm a new window",
            _reset in _TAIL and _TAIL.index(_reset) < _FIRST_OFFER)

# Overflight's owner rule moved OUT of can_use() and into the offer, because
# can_use() is answered frames later when neither the phase nor the turn owner
# is what it was. Both facts have to be handed over at the seam, and the
# controller must not read the clock behind their back.
_ov_args = _TAIL.split("overflight_controller.offer_at_end_of_phase(", 1)[1]
_ov_args = _ov_args[:_ov_args.index("\n        if ")] if "\n        if " in _ov_args else _ov_args[:200]
ck.true("Overflight is handed phase_before and mover_before at the seam",
        "phase_before" in _ov_args and "mover_before" in _ov_args)
_OV_SRC = io.open(os.path.join("game", "windrider_overflight.py"), encoding="utf-8").read()
_ov_can_use = _OV_SRC.split("def can_use", 1)[1].split("\n    def ", 1)[0]
ck.true("...and its can_use() reads neither the clock nor the turn owner",
        "turn_tracker.phase" not in _ov_can_use
        and "turn_tracker.turn_owner" not in _ov_can_use)
_SKY_SRC = io.open(os.path.join("game", "skyborne_sanctuary.py"), encoding="utf-8").read()
_sky_can_use = _SKY_SRC.split("    def can_use", 1)[1].split("\n    def ", 1)[0]
ck.true("Skyborne Sanctuary's can_use() reads no live phase either",
        "turn_tracker.phase" not in _sky_can_use)


# ---------------------------------------------------------------------------
# 9. A SINGLE-SLOT CALLBACK IS NEVER ASSIGNED TWICE WITHOUT CHAINING
# ---------------------------------------------------------------------------
print()
print("=== 9. every re-assigned on_* callback chains the previous one ===")

# fight_controller.on_unit_finished_fighting is ONE slot. main.py set it to a
# chained handler for seven abilities (Undying Legions, Curse of the Walking
# Pox, Lethal Ichor, Undying Spite, To Their Final Breaths, Malevolent Souls,
# Vaul's Vengeance) and then, ~120 lines later, assigned it AGAIN for rule
# 15.12's Counteroffensive - silently throwing all seven away. Every one of
# them had a green suite, because those drive the controllers directly; only
# the source can see a slot being written twice.
#
# Section 4 checks the ORDER of `a.b = c`; it cannot see this. The rule here is
# narrow on purpose: `on_*` names are this codebase's single-slot callbacks
# (lists are named target_reactions/charge_declaration_reactions and appended
# to, and data attributes like homing_beacon_bearer are legitimately re-set).
_CALLBACK_ASSIGNS = {}
_CALLBACK_READS = {}
for _node in _own_level(MAIN):
    if isinstance(_node, ast.Assign):
        for _t in _node.targets:
            if (isinstance(_t, ast.Attribute) and _t.attr.startswith("on_")
                    and isinstance(_t.value, ast.Name)):
                _CALLBACK_ASSIGNS.setdefault(
                    "%s.%s" % (_t.value.id, _t.attr), []).append(_node.lineno)
for _node in ast.walk(MAIN):
    if (isinstance(_node, ast.Attribute) and _node.attr.startswith("on_")
            and isinstance(_node.ctx, ast.Load) and isinstance(_node.value, ast.Name)):
        _CALLBACK_READS.setdefault(
            "%s.%s" % (_node.value.id, _node.attr), []).append(_node.lineno)

ck.true("the sweep found on_* callback slots at all (it is not vacuous)",
        len(_CALLBACK_ASSIGNS) >= 2)
for _slot, _lines in sorted(_CALLBACK_ASSIGNS.items()):
    _lines = sorted(_lines)
    if len(_lines) < 2:
        continue
    for _prev, _this in zip(_lines, _lines[1:]):
        # The chaining idiom is "capture the old value, then install a wrapper
        # that calls it" - so the old value must be READ between the two
        # assignments. Without that read, the later assignment is a clobber.
        ck.true("%s re-assigned at line %d chains the handler from line %d"
                % (_slot, _this, _prev),
                any(_prev < _read < _this for _read in _CALLBACK_READS.get(_slot, ())))


# ---------------------------------------------------------------------------
# 10. A CONTROLLER THAT BLOCKS THE PHASE ADVANCE MUST BE RESOLVABLE
# ---------------------------------------------------------------------------
print()
print("=== 10. everything the phase gate waits on can be resolved ===")

# THE INVERSE OF SECTION 6, and the one section 6 structurally cannot make.
# That one starts from "who does main.py ASK about pending_damage_choice"; a
# controller nobody asks is invisible to it. Aspect Host's Khaine's Vengeance
# was exactly that: its is_busy sat in _has_unresolved_declaration(), so an
# unresolved hazard step froze the phase FOREVER, while neither its dice
# acknowledgement nor its damage choice was wired anywhere in the event chain.
# Built, blocking, and unclickable - a hard hang rather than a silent no-op.
#
# So this one starts from the GATE: whatever it waits on, something in the
# chain has to be able to end.
def _function_body(name):
    for node in ast.walk(MAIN):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(SRC, node) or ""
    return ""


_GATE_SRC = _function_body("_has_unresolved_declaration")
ck.true("_has_unresolved_declaration() was found", bool(_GATE_SRC))
_BLOCKING = set(re.findall(r"(\w+_controller)\.is_busy", _GATE_SRC))
# Both places a human answer can be routed from: the event chain, and the left
# panel - a reactive move hands its Confirm/Cancel to the panel as a CALLBACK
# (an attribute reference, no parentheses), which is how Higher Duty and the
# three reactive-move Stratagems are ended.
_PANEL_SRC = io.open(os.path.join("game", "ui", "action_panel.py"), encoding="utf-8").read()
_ENDINGS = r"\.(?:on_dice_acknowledged|choose_damage_model|choose\w*|confirm\w*|cancel\w*|decline\w*|skip\w*|resolve\w*)"
_RESOLVABLE = (set(re.findall(r"(\w+_controller)%s" % _ENDINGS, SRC))
               | set(re.findall(r"(\w+_controller)%s" % _ENDINGS, _PANEL_SRC)))
# Documented gaps, NAMED with their reason rather than silently subtracted.
# secondary_mission_controller's is_busy is answered by the shared
# DecisionManager queue - its own docstring says so, and main.py's chain
# already gates on decision_manager.is_pending - so there is no method of its
# own to call and nothing here to find.
_BUSY_GAPS = {"secondary_mission_controller"}
for _gap in sorted(_BUSY_GAPS):
    ck.true("%s is the documented gap, and blocks through the shared queue" % _gap,
            _gap in _BLOCKING)

ck.true("the guard is live - it found %d blocking controllers" % len(_BLOCKING),
        len(_BLOCKING) >= 8)
ck.eq("every controller the phase gate waits on can be ended from the chain",
      sorted(_BLOCKING - _RESOLVABLE - _BUSY_GAPS), [])
# The reported one, by name, so a partial regression is not just a list diff.
ck.true("khaines_vengeance_controller is one the gate waits on",
        "khaines_vengeance_controller" in _BLOCKING)
ck.true("...and it is resolvable (the reported deadlock)",
        "khaines_vengeance_controller" in _RESOLVABLE)


# ---------------------------------------------------------------------------
# 11. EVERY DICE-DRIVEN CONTROLLER IS ACKNOWLEDGED
# ---------------------------------------------------------------------------
print()
print("=== 11. every on_dice_acknowledged() owner is called ===")

# THE GUARD THAT WOULD HAVE CAUGHT CRUSHING STRIDES. Spirit Conclave's
# Crushing Strides rolled its dice, and main.py never told the controller the
# roll had been acknowledged - so the mortal wounds were never inflicted AND
# its own _pending latch turned the Stratagem off for the rest of the battle.
# Its unit test was green throughout, because a unit test calls
# on_dice_acknowledged() itself. Only the source can answer this.
#
# Faction-blind by construction: it resolves the CLASS of every controller
# main() builds, so the next detachment batch is covered without an edit.
_DICE_OWNERS, _UNRESOLVED = set(), 0
for _node in MAIN.body:
    if not (isinstance(_node, ast.Assign) and len(_node.targets) == 1
            and isinstance(_node.targets[0], ast.Name)
            and isinstance(_node.value, ast.Call)):
        continue
    _var = _node.targets[0].id
    if not _var.endswith("_controller"):
        continue
    _func = _node.value.func
    # `X = SomeController(...)` and `X = registry.add(SomeController(...))`.
    while isinstance(_func, ast.Attribute) and _node.value.args:
        inner = _node.value.args[0]
        if isinstance(inner, ast.Call):
            _node = ast.Assign(targets=_node.targets, value=inner)
            _func = inner.func
        else:
            break
    if not isinstance(_func, ast.Name):
        continue
    _cls = _CLASS_IMPORTS.get(_func.id)
    if _cls is None:
        _UNRESOLVED += 1
        continue
    try:
        _mod = importlib.import_module(_cls)
        _obj = getattr(_mod, _func.id, None)
    except Exception:
        _UNRESOLVED += 1
        continue
    if _obj is not None and callable(getattr(_obj, "on_dice_acknowledged", None)):
        _DICE_OWNERS.add(_var)

# Documented gaps, named rather than silently subtracted. Empty today.
_ACK_GAPS = set()
_ACKED = set(re.findall(r"(\w+_controller)\.on_dice_acknowledged\(\)", SRC))

ck.true("the guard is live - it resolved %d dice-owning controllers"
        % len(_DICE_OWNERS), len(_DICE_OWNERS) >= 20)
ck.eq("every controller that owns a dice acknowledgement is called from the chain",
      sorted(_DICE_OWNERS - _ACKED - _ACK_GAPS), [])
ck.true("crushing_strides_controller is one of them (the reported no-op)",
        "crushing_strides_controller" in _DICE_OWNERS
        and "crushing_strides_controller" in _ACKED)


# ---------------------------------------------------------------------------
# 12. EVERY DAMAGE CHOICE ALSO PAUSES THE AI FOR A FRAME
# ---------------------------------------------------------------------------
print("\n=== 12. every pending damage choice pauses the AI for a frame ===")

# THE THIRD LIST, and the only one nothing was watching. main() answers "is a
# damage allocation open?" in three separate places, each a hand-maintained
# list of the same controllers:
#   A  _has_unresolved_declaration()  - the phase cannot advance
#   B  _any_pending_damage_choice()   - run_ai_action() is skipped for one
#                                       frame, so the render gets to show the
#                                       model actually gone before the AI acts
#   C  the Deadly Demise / Emergency Disembark start gate
# Section 6 above checks that everything in (A) is clickable and drawn. (C)'s
# shorter list is already written down as a known open point. (B) was written
# down NOWHERE, and was short by FOUR: ishas_fury, grenade_pack,
# grav_inhibitor and flickerjump - each with a pending_damage_choice, each with
# a click branch, each drawing its eligible models, each blocking the phase in
# (A), and none of them pausing the AI.
#
# The consequence is not a deadlock - that is (A)'s job, and (A) had them. It
# is the one-frame race this snapshot exists for: the human's click resolves
# the choice and the AI takes its next action in the SAME frame, before the
# board ever renders the casualty. No behaviour test and no smoke run can see a
# one-frame ordering; only the source can.
#
# READ BY AST, NOT BY REGEX, and that is three separate reasons rather than
# taste. The function opens with a 44-line docstring ABOUT controllers, which
# today happens to contain no `_controller` token - one sentence naming one and
# a regex would forgive a removal, which is error class 24 exactly. The tuple
# carries comments BETWEEN its elements. And a regex over the body has no
# honest right edge: bounded on the next `def`, a decorator or a nested helper
# silently widens it, and a silently widened body makes the difference SHRINK
# and the check pass. The AST fails in the safe direction instead - an
# extraction that stops working returns the empty set, the difference becomes
# the whole of _ASKED, and this section goes red.


def _function_node(name):
    for node in ast.walk(MAIN):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _pause_snapshot_names():
    """The controller names in _any_pending_damage_choice()'s `for c in (...)`."""
    fn = _function_node("_any_pending_damage_choice")
    if fn is None:
        return set()
    for node in ast.walk(fn):
        if isinstance(node, ast.comprehension) and isinstance(node.iter, ast.Tuple):
            return {e.id for e in node.iter.elts if isinstance(e, ast.Name)}
    return set()


_PAUSED = _pause_snapshot_names()

# Live-guard first, and it has to catch a broken SHAPE as well as a short list:
# a refactor that turned the tuple into a list comprehension or a module
# constant would return the empty set, and "0 names" has to read as a broken
# extractor rather than as an empty list.
ck.true("the guard is live - it read %d controllers out of the AI-pause tuple"
        % len(_PAUSED), len(_PAUSED) >= 18)

# Documented gaps, named rather than silently subtracted. Empty, and it should
# stay that way: the comprehension already filters on
# `.squad.owner != "Player 2"`, so adding a name can only ever pause the AI over
# a HUMAN's open choice. That filter is what makes this list safe to complete -
# see the function's own docstring for the starvation that came from counting
# the AI's own choices, which is the mistake this guard must not tempt anyone
# into re-fixing by trimming the tuple instead of the filter.
_PAUSE_GAPS = set()

ck.eq("every controller main.py asks about also pauses the AI for a frame",
      sorted(_ASKED - _PAUSED - _PAUSE_GAPS), [])

# The four this guard was written for, by name, so a regression that brings
# back exactly one of them is not just a list diff - the same care section 6
# takes with its own reported three.
for _name in ("ishas_fury_controller", "grenade_pack_controller",
              "grav_inhibitor_controller", "flickerjump_controller"):
    ck.true("%s pauses the AI while its choice is open" % _name, _name in _PAUSED)

# ...and the other direction, which is free: a name in the tuple that owns no
# pending_damage_choice is a typo the AST cannot see, and it would pause the AI
# on an attribute that is always falsy.
ck.eq("nothing in the AI-pause snapshot lacks a pending_damage_choice",
      sorted(_PAUSED - _ASKED), [])


# ---------------------------------------------------------------------------
# 13. EVERY OUT-OF-PHASE MOVE IS WAITED ON BY THE PHASE GATE
# ---------------------------------------------------------------------------
print("\n=== 13. every ability-granted move mode is in the phase gate ===")

# _has_unresolved_declaration() had NO movement_controller term of any kind,
# and main()'s "Next Phase" branch calls movement_controller.select(None) right
# after it passes - which clears the selection and the state but neither
# move_mode nor the model positions. So clicking Next Phase over an open
# Torchstar Gambit move left the models where they had been dragged, the CP
# spent, and the Stratagem's own charge lock never applied. Twelve move modes
# are opened this way by eleven modules; exactly two of their controllers were
# waited on already, and both for an unrelated reason (they hold
# turn_tracker.active_player, and say so in their own comments).
#
# THE SET DIFFERENCE IS OVER MOVE MODES, NOT CONTROLLERS, and that is the whole
# design rather than a convenience. The controller version was built as far as
# measuring it and then rejected:
#   * nine of the eleven owners would land in the difference on day one. A
#     check that reports nine names is a bug list with a test harness around
#     it, and it gets silenced by nine _GAPS entries that then look considered.
#   * battle_focus_pool is not named *_controller and has no is_busy at all, so
#     it could never leave the difference except by renaming a variable used a
#     dozen times in main.py. A test must not dictate a variable name.
#   * retro_thrusters_controller would be a real false positive:
#     ai/agent_driver.py holds the AI's turn end for it through
#     has_pending_for_opponent_of(), a purpose-built protection this guard
#     cannot see.
#   * four of the eleven module -> main.py-variable mappings are not derivable
#     from source at all and would need a hand-written table - exactly the kind
#     game/ui/action_panel.py records growing wrong.
# Modes are what the doors carry, what the gate reads and what the panel routes
# on: one vocabulary, no map.
_MOVE_PATH = os.path.join("game", "movement.py")
_MOVE_SRC = io.open(_MOVE_PATH, encoding="utf-8").read()
_MOVE_TREE = ast.parse(_MOVE_SRC)
_MC = next(n for n in _MOVE_TREE.body
           if isinstance(n, ast.ClassDef) and n.name == "MovementController")

# The three extension doors, and the Movement phase's own starters. Both listed
# so that a TWELFTH start_* method cannot be added without landing in one or
# the other - the guard on the guard. Without it a new door would simply not be
# swept, and every difference below would stay empty by measuring less.
_DOOR_NAMES = ("start_post_shooting_move", "start_battle_focus_move",
               "start_retro_thruster_move")
_PHASE_STARTERS = ("start_move", "start_fall_back_move", "start_charge_move",
                   "start_surge_move", "start_scout_move", "start_pile_in_move",
                   "start_consolidate_move", "start_run")

_STARTERS = {n.name for n in _MC.body
             if isinstance(n, ast.FunctionDef) and n.name.startswith("start_")}
ck.true("the three extension doors still exist", set(_DOOR_NAMES) <= _STARTERS)
ck.eq("every MovementController.start_* method is classified",
      sorted(_STARTERS - set(_DOOR_NAMES) - set(_PHASE_STARTERS)), [])

# The doors' own move_mode defaults, read off the signatures rather than
# restated here: a default renamed in movement.py must not leave this guard
# measuring a mode that no longer exists.
_DOOR_DEFAULTS, _OPENERS, _BY_DOOR = {}, {}, {}
for _fn in _MC.body:
    if not (isinstance(_fn, ast.FunctionDef) and _fn.name in _DOOR_NAMES):
        continue
    _defs = _fn.args.defaults
    for _arg, _d in zip(_fn.args.args[len(_fn.args.args) - len(_defs):], _defs):
        if _arg.arg == "move_mode" and isinstance(_d, ast.Constant):
            _DOOR_DEFAULTS[_fn.name] = _d.value
    # start_retro_thruster_move names its two modes itself rather than taking
    # them from a caller, so they are read off its own assignments.
    for _n in ast.walk(_fn):
        if (isinstance(_n, ast.Assign) and isinstance(_n.value, ast.Constant)
                and isinstance(_n.value.value, str)
                and any(isinstance(_t, ast.Attribute) and _t.attr == "move_mode"
                        for _t in _n.targets)):
            _OPENERS.setdefault(_n.value.value, []).append(
                "movement.py:%d" % _n.lineno)
            _BY_DOOR.setdefault(_fn.name, set()).add(_n.value.value)

# Every caller of a door, anywhere in game/. AST rather than a substring sweep:
# the mode arrives as a keyword whose value is a literal in some modules and a
# module-level constant in others, and two callers pass no mode at all and take
# the door's default. A grep for '"torchstar"' finds none of that, and would
# find the handful of docstrings that discuss these modes by name - error class
# 24 again.
_UNRESOLVED = []
for _name in sorted(os.listdir("game")):
    if not _name.endswith(".py"):
        continue
    _msrc = io.open(os.path.join("game", _name), encoding="utf-8").read()
    if not any(_d in _msrc for _d in _DOOR_NAMES):
        continue
    _mtree = ast.parse(_msrc)
    _consts = {_t.id: _n.value.value
               for _n in _mtree.body
               if isinstance(_n, ast.Assign) and isinstance(_n.value, ast.Constant)
               and isinstance(_n.value.value, str)
               for _t in _n.targets if isinstance(_t, ast.Name)}
    for _node in ast.walk(_mtree):
        if not (isinstance(_node, ast.Call)
                and isinstance(_node.func, ast.Attribute)
                and _node.func.attr in _DOOR_DEFAULTS):
            continue
        _kw = next((k.value for k in _node.keywords if k.arg == "move_mode"), None)
        if _kw is None:
            _mode = _DOOR_DEFAULTS[_node.func.attr]
        elif isinstance(_kw, ast.Constant) and isinstance(_kw.value, str):
            _mode = _kw.value
        elif isinstance(_kw, ast.Name) and _kw.id in _consts:
            _mode = _consts[_kw.id]
        else:
            _UNRESOLVED.append("%s:%d" % (_name, _node.lineno))
            continue
        _OPENERS.setdefault(_mode, []).append("%s:%d" % (_name, _node.lineno))
        _BY_DOOR.setdefault(_node.func.attr, set()).add(_mode)

# An unresolvable call is a FINDING, not something to drop quietly: a mode this
# sweep cannot read is a mode the differences below silently forgive.
ck.eq("every door call names a move_mode this guard can resolve", _UNRESOLVED, [])
ck.true("the guard is live - it resolved %d out-of-phase move modes from %d "
        "call sites" % (len(_OPENERS), sum(len(v) for v in _OPENERS.values())),
        len(_OPENERS) >= 11)

_movement_module = importlib.import_module("game.movement")
_OUT_OF_PHASE = set(_movement_module.MovementController.OUT_OF_PHASE_MOVE_MODES)

ck.eq("every ability-granted move mode is one the phase gate waits on",
      sorted(set(_OPENERS) - _OUT_OF_PHASE), [])
# The other direction, which catches a dead entry: an ability deleted while its
# mode stayed in the set would otherwise sit there for ever, blocking a phase
# for a move nothing can open.
ck.eq("...and the set names no mode that nothing actually opens",
      sorted(_OUT_OF_PHASE - set(_OPENERS)), [])

# The contract start_battle_focus_move()'s own docstring states - "any mode
# passed here must also be listed in REACTIVE_MOVE_MODES, or the AI will walk
# straight over the move it just granted" - has been REPORTED BROKEN TWICE, in
# the same words both times. It holds today; this pins it so there is no third
# report. Read off which door each mode came through, so a new reactive move
# cannot be added without landing here.
_REACTIVE_OPENED = _BY_DOOR.get("start_battle_focus_move", set())
ck.true("the reactive door was swept", len(_REACTIVE_OPENED) >= 4)
ck.eq("every mode opened through the reactive door is in REACTIVE_MOVE_MODES",
      sorted(_REACTIVE_OPENED
             - set(_movement_module.MovementController.REACTIVE_MOVE_MODES)), [])

# ...and the gate really READS the set, as an expression. A mention in a
# comment must not count, so this is an AST test for an `in` comparison whose
# left side is the attribute movement_controller.move_mode - not a substring.
_GATE_NODE = _function_node("_has_unresolved_declaration")
ck.true("_has_unresolved_declaration() was found", _GATE_NODE is not None)
ck.true("the phase gate tests movement_controller.move_mode against a set",
        any(isinstance(_n, ast.Compare) and _n.ops
            and isinstance(_n.ops[0], ast.In)
            and isinstance(_n.left, ast.Attribute)
            and _n.left.attr == "move_mode"
            and isinstance(_n.left.value, ast.Name)
            and _n.left.value.id == "movement_controller"
            for _n in ast.walk(_GATE_NODE)) if _GATE_NODE is not None else False)
# The state test is not optional: a stale move_mode left behind by select(None)
# would otherwise block the phase for ever.
ck.true("...and only while a move is actually open",
        any(isinstance(_n, ast.Compare) and isinstance(_n.left, ast.Attribute)
            and _n.left.attr == "state"
            and isinstance(_n.left.value, ast.Name)
            and _n.left.value.id == "movement_controller"
            for _n in ast.walk(_GATE_NODE)) if _GATE_NODE is not None else False)


# ---------------------------------------------------------------------------
# 14. EVERY PROACTIVE STRATAGEM CONTROLLER REACHES THE PANEL
# ---------------------------------------------------------------------------
print("\n=== 14. every panel Stratagem is registered or handed over ===")

# THE LESSON OF TWO AUDITS, as a guard rather than as a checklist. Both the
# Aeldari and the T'au batches shipped with the same shape - the rule right,
# the controller right, and the button never on the screen - and in both cases
# the only thing standing between a new Stratagem and that outcome was somebody
# remembering to write one line in main.py.
#
# A controller ANNOUNCES that it wants a panel button by defining
# panel_label(); that is the whole contract in game/proactive_stratagems.py. So
# a class that defines one and reaches neither the registry nor a panel
# argument is a button nobody can press, and this says so at the source - which
# is the only place that can, because a behaviour test cannot see a Stratagem
# that does not exist yet.
#
# TWO REGISTRATION FORMS and one alias form, all measured rather than assumed:
# main.py writes both `add(SomeController(...))` and `add(existing_var)`, and
# game/targeting_array.py imports its class under a DIFFERENT NAME
# (`ActivationRerollController as TargetingArrayController`) - so a sweep that
# matched class names literally would report that one as unreachable when it is
# registered under its alias.
_ALIASES = {}
for _name in sorted(os.listdir("game")):
    if not _name.endswith(".py"):
        continue
    for _node in ast.walk(ast.parse(
            io.open(os.path.join("game", _name), encoding="utf-8").read())):
        if isinstance(_node, ast.ImportFrom):
            for _a in _node.names:
                if _a.asname:
                    _ALIASES.setdefault(_a.name, set()).add(_a.asname)

_REGISTERED, _REG_VARS = set(), set()
for _node in ast.walk(TREE):
    if not (isinstance(_node, ast.Call) and isinstance(_node.func, ast.Attribute)
            and _node.func.attr == "add"
            and isinstance(_node.func.value, ast.Name)
            and _node.func.value.id == "proactive_stratagems" and _node.args):
        continue
    _arg = _node.args[0]
    if isinstance(_arg, ast.Call) and isinstance(_arg.func, ast.Name):
        _REGISTERED.add(_arg.func.id)
    elif isinstance(_arg, ast.Name):
        _REG_VARS.add(_arg.id)

# ...and the controllers the panel takes as its own argument instead: the three
# that predate the registry still arrive that way, and a fourth would too.
_PANEL_ARGS = set()
for _node in ast.walk(TREE):
    if (isinstance(_node, ast.Call) and isinstance(_node.func, ast.Attribute)
            and _node.func.attr == "draw"
            and isinstance(_node.func.value, ast.Name)
            and _node.func.value.id == "action_panel"):
        for _a in list(_node.args) + [k.value for k in _node.keywords]:
            if isinstance(_a, ast.Name):
                _PANEL_ARGS.add(_a.id)

# Resolve every registered/handed-over VARIABLE back to the class it was built
# from, so both forms land in one set of class names.
for _node in ast.walk(TREE):
    if (isinstance(_node, ast.Assign) and len(_node.targets) == 1
            and isinstance(_node.targets[0], ast.Name)
            and _node.targets[0].id in (_REG_VARS | _PANEL_ARGS)
            and isinstance(_node.value, ast.Call)):
        _f = _node.value.func
        # `X = registry.add(SomeController(...))` unwraps one level.
        if isinstance(_f, ast.Attribute) and _node.value.args and \
                isinstance(_node.value.args[0], ast.Call) and \
                isinstance(_node.value.args[0].func, ast.Name):
            _REGISTERED.add(_node.value.args[0].func.id)
        elif isinstance(_f, ast.Name):
            _REGISTERED.add(_f.id)

_REACHABLE = set(_REGISTERED)
for _real, _names in _ALIASES.items():
    _short = _real.rsplit(".", 1)[-1]
    if _REACHABLE & _names:
        _REACHABLE.add(_short)

_WANTS_BUTTON = {}
for _name in sorted(os.listdir("game")):
    if not _name.endswith(".py"):
        continue
    _msrc = io.open(os.path.join("game", _name), encoding="utf-8").read()
    if "def panel_label(" not in _msrc:
        continue
    for _cls in ast.walk(ast.parse(_msrc)):
        if isinstance(_cls, ast.ClassDef) and any(
                isinstance(_f, ast.FunctionDef) and _f.name == "panel_label"
                for _f in _cls.body):
            _WANTS_BUTTON[_cls.name] = _name

# Documented gaps, named rather than silently subtracted. Empty.
_BUTTON_GAPS = set()

ck.true("the guard is live - it found %d controllers asking for a button"
        % len(_WANTS_BUTTON), len(_WANTS_BUTTON) >= 25)
ck.true("...and it resolved %d reachable ones" % len(_REACHABLE),
        len(_REACHABLE) >= 25)
ck.eq("every controller that defines panel_label() reaches the panel",
      sorted("%s (%s)" % (c, _WANTS_BUTTON[c])
             for c in _WANTS_BUTTON if c not in _REACHABLE and c not in _BUTTON_GAPS),
      [])


# ---------------------------------------------------------------------------
# 15. AN END-OF-PHASE OFFER NEVER READS THE LIVE CLOCK
# ---------------------------------------------------------------------------
print("\n=== 15. end-of-phase offers use a window, not the phase ===")

# SIX BUGS OF ONE SHAPE, across two factions and two audits: Wall of Mirrors,
# Cost of Victory, Webway Tunnel, Elemental Ensnarement, Skyborne Sanctuary and
# Overflight all expressed "at the end of the Fight phase" as a live test
#
#     if self.turn_tracker.phase != PHASE_FIGHT: return False
#
# inside can_use(). That check can NEVER hold. main()'s advance_turn_phase()
# calls turn_tracker.advance_phase() FIRST and only then runs the end-of-phase
# offers, so the clock already reads the next phase when the offer is made -
# and later still when a human answers the queued prompt. The result was not
# "sometimes wrong" but a guaranteed silent no-op: a prompt whose every option
# returned False, or no prompt at all.
#
# game/phase_window.py exists for exactly this, and section 8 already pins that
# these offers take mover_before rather than the flipped turn_owner. What it
# does NOT pin is the clock read inside can_use() - which is the half that was
# broken all six times. This is that half.
#
# ONLY offer_at_end_*, deliberately. A START-of-phase offer reads the live
# clock CORRECTLY: it fires once the clock has already become the phase it
# names, which is why game/grot_orderly.py's `phase != PHASE_COMMAND` is right
# and must not be swept up here. Measured: 24 controllers have some offer_at_*
# method, 14 of them an end-of-phase one, and exactly one of the other ten
# reads the clock - the start-of-phase case just described.
_END_OFFERS, _LIVE_CLOCK = [], []
for _name in sorted(os.listdir("game")):
    if not _name.endswith(".py"):
        continue
    _msrc = io.open(os.path.join("game", _name), encoding="utf-8").read()
    if "def offer_at_end" not in _msrc:
        continue
    _mtree = ast.parse(_msrc)
    for _cls in ast.walk(_mtree):
        if not isinstance(_cls, ast.ClassDef):
            continue
        if not any(isinstance(_f, ast.FunctionDef)
                   and _f.name.startswith("offer_at_end") for _f in _cls.body):
            continue
        _END_OFFERS.append((_name, _cls.name))
        _can = next((_f for _f in _cls.body if isinstance(_f, ast.FunctionDef)
                     and _f.name == "can_use"), None)
        if _can is None:
            continue
        # A phase COMPARISON, by AST - not the substring ".phase", which a
        # docstring explaining the trap would satisfy all by itself.
        for _n2 in ast.walk(_can):
            if (isinstance(_n2, ast.Compare) and isinstance(_n2.left, ast.Attribute)
                    and _n2.left.attr == "phase"):
                _LIVE_CLOCK.append("%s (%s)" % (_cls.name, _name))
                break

ck.true("the guard is live - it found %d end-of-phase offers" % len(_END_OFFERS),
        len(_END_OFFERS) >= 10)
ck.eq("no end-of-phase offer decides eligibility from the live clock",
      sorted(set(_LIVE_CLOCK)), [])
# ...and the module that exists for it is really used by some of them, so the
# check above cannot pass because nobody offers anything at a boundary.
ck.true("...and game/phase_window.py is what they use instead",
        sum(1 for _f, _c in _END_OFFERS
            if "PhaseWindow" in io.open(os.path.join("game", _f),
                                        encoding="utf-8").read()) >= 5)


# ---------------------------------------------------------------------------
# 16. EVERY ENHANCEMENT FLAG IS READ BY SOMETHING
# ---------------------------------------------------------------------------
print("\n=== 16. every registered Enhancement is read somewhere ===")

# The Enhancement version of "built, but never FED". game/enhancements.py's
# registry is a table: adding a row gives a rule points, a bearer restriction
# and a UnitProfile field, and every one of those is testable on its own while
# NOTHING reads the field. The rule is then bought, paid for, shown on the
# datacard - and does nothing.
#
# Faction-blind by construction, so the next batch is covered without an edit;
# it lives in this file because this is the repo's only faction-blind source
# guard, and a per-faction suite could only ever check its own.
import importlib as _il  # noqa: E402

_enh = _il.import_module("game.enhancements")
_GAMESRC = {}
for _name in sorted(os.listdir("game")):
    if _name.endswith(".py"):
        _GAMESRC[_name] = io.open(os.path.join("game", _name),
                                  encoding="utf-8").read()

_UNREAD = []
for _spec in _enh.ENHANCEMENTS.values():
    # Read ANYWHERE outside enhancements.py itself - the registry names the
    # field once, so a second mention is the first reader.
    _readers = [f for f, s in _GAMESRC.items()
                if f != "enhancements.py" and _spec.flag in s]
    if not _readers:
        _UNREAD.append("%s (%s)" % (_spec.name, _spec.flag))

ck.true("the guard is live - it checked %d registered Enhancements"
        % len(_enh.ENHANCEMENTS), len(_enh.ENHANCEMENTS) >= 40)
ck.eq("every Enhancement's UnitProfile field is read by some rule",
      sorted(_UNREAD), [])

# --------------------------------------------------------------------------
# 17. every module that OPENS a mortal-wound session can DRAIN it
# --------------------------------------------------------------------------
print("=== 17. every module that opens a mortal-wound session can drain it ===")

# THE INVERSION OF SECTION 6, one layer further out.
#
# Section 6 starts from main.py's side: "every controller main.py ASKS about
# pending_damage_choice must also be clickable and drawn". Sections 10, 11 and
# 12 start there too. All four are therefore blind to a controller main.py
# never asks about at all - and that is exactly what shipped:
#
#   game/wraith_form.py built a MortalWoundAllocationSession and had no
#   pending_damage_choice, no choose_damage_model and no FNP drain. Measured
#   before the fix: three sixes rolled, the log said "3 mortal wound(s)", and
#   ZERO landed on a ten-model target - the session parked on pending_choice
#   with ten candidates and nothing in the repo could ever answer it. Against
#   a ONE-model target it resolved fine, which is why it survived.
#
# The same sweep found three more (drakolithe, harvester_of_souls,
# monofilament_snare), so this is a class and not an incident - and a
# behaviour test cannot see the twenty-second module, because it does not
# exist yet. Hence a SET DIFFERENCE at the source.
#
# BY AST, NOT BY SUBSTRING, and this one is not a style preference: a
# substring sweep for the class name hits ~30 modules in game/, of which nine
# only MENTION it in a docstring - and game/mortal_wound_abilities.py names it
# inside a comment that explains this very bug. A guard that matches its own
# explanation is Fehlerklasse 24, paid four times in this repo already.

_MW_CLASS = "MortalWoundAllocationSession"
_MW_DRAINS = ("pending_damage_choice", "choose_damage_model")

# damage_resolution.py DEFINES the class and drains its own session
# synchronously in the same function - it is not a controller and has no
# player to ask. Every other name here would be an excuse, so the exemption
# carries three liveness assertions below and cannot rot into one.
_MW_DRAIN_GAPS = {"damage_resolution.py"}

_mw_trees = {}
for _name, _text in _GAMESRC.items():
    try:
        _mw_trees[_name] = ast.parse(_text)
    except SyntaxError:                     # pragma: no cover - would fail loudly below
        pass


def _mw_calls(tree):
    """Every construction of the session in this module, as Call nodes.

    Accepts the attribute form too (damage_resolution.MortalWoundAllocationSession),
    so moving a call behind the module name does not silently leave the sweep.
    """
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if ((isinstance(func, ast.Name) and func.id == _MW_CLASS)
                or (isinstance(func, ast.Attribute) and func.attr == _MW_CLASS)):
            out.append(node)
    return out


def _mw_defines(tree, wanted):
    """True if the module defines `wanted` as a method of some class.

    A module-level function of the same name would not be reachable as
    `controller.pending_damage_choice`, and a docstring naming it is not a
    definition at all - which is the whole reason this is an AST walk.
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for sub in node.body:
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name == wanted:
                return True
            # @property wraps the FunctionDef, so the decorator is irrelevant;
            # what matters is that the name is bound on the class.
    return False


_mw_creators = {n for n, t in _mw_trees.items() if _mw_calls(t)}
_mw_drainers = {n for n in _mw_creators
                if all(_mw_defines(_mw_trees[n], w) for w in _MW_DRAINS)}

# LIVENESS. A broken extractor returns the empty set, the difference below
# collapses to nothing and the guard would pass by inspecting nothing - the
# same failure direction section 12 documents. These three make that loud.
ck.true("the guard is live - it read the whole of game/ (%d modules)" % len(_mw_trees),
        len(_mw_trees) > 200)
ck.true("...and found %d modules opening a mortal-wound session" % len(_mw_creators),
        len(_mw_creators) >= 18)
ck.true("...including the four this guard was written for",
        {"wraith_form.py", "drakolithe.py", "harvester_of_souls.py",
         "monofilament_snare.py"} <= _mw_creators)

ck.eq("every module that opens a mortal-wound session can drain it",
      sorted(_mw_creators - _mw_drainers - _MW_DRAIN_GAPS), [])

# The exemption, checked three ways so a stale excuse falls through rather
# than standing green forever - the lesson of the Mont'ka gap, whose prose
# justification went stale while its assertion stayed green.
for _gap in sorted(_MW_DRAIN_GAPS):
    _tree = _mw_trees.get(_gap)
    ck.true("%s is still exempt for a reason: it still opens one" % _gap,
            _tree is not None and bool(_mw_calls(_tree)))
    ck.true("...it is the module that DEFINES the class",
            any(isinstance(n, ast.ClassDef) and n.name == _MW_CLASS
                for n in ast.walk(_tree)) if _tree is not None else False)
    # ...and the behavioural half of the excuse: it answers its own session
    # synchronously, so there is no player left waiting on it.
    _sync = False
    for _fn in ast.walk(_tree) if _tree is not None else []:
        if not isinstance(_fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _mw_calls(_fn):
            continue
        for _sub in ast.walk(_fn):
            # `while not session.done:` - matched on the ATTRIBUTE node, not on
            # a dump substring: ast.dump() renders it as attr='done', so the
            # obvious ".done" needle never fires (found by this guard's own
            # first run).
            if isinstance(_sub, ast.While) and any(
                    isinstance(_n, ast.Attribute) and _n.attr == "done"
                    for _n in ast.walk(_sub.test)):
                _sync = True
    ck.true("...and drains it synchronously in the same function", _sync)

# --------------------------------------------------------------------------
# 17b. the log= a session is handed must be CALLABLE
# --------------------------------------------------------------------------
print("=== 17b. a session's log= is a callable, not the GameLog object ===")

# MortalWoundAllocationSession calls `self.log(message)` (damage_resolution.py's
# _finish_apply and its Devastating Wounds twin). GameLog has no __call__, and
# neither does testkit.Log - so a site that hands over the OBJECT crashes with
# TypeError the moment a wound actually lands.
#
# It only lands against a ONE-model target: with two or more eligible models
# the session parks on pending_choice BEFORE the first log call. So this is the
# mirror image of section 17 - multi-model targets leak, single-model targets
# crash - and the same three modules had both.
#
# Measured before the fix: 18 of 21 sites passed a callable, exactly three
# passed `self.game_log`.

# The premise, asserted rather than assumed: neither the real GameLog nor the
# test double answers a call, so handing either one over is a crash and not a
# style question.
_gamelog = _il.import_module("game.game_log").GameLog
ck.true("the premise holds - GameLog defines no __call__",
        "__call__" not in vars(_gamelog))
ck.true("...and neither does the test double",
        "__call__" not in vars(_il.import_module("testkit").Log))


def _mw_log_arg_ok(call):
    """Is this construction's log= something the session can CALL?

    Written as a REFUSAL of the one shape that is wrong, not as a whitelist of
    the shapes that are right: the four accepted spellings today are a lambda,
    a conditional lambda, a bound `_log`/`log` method and a passthrough
    parameter, and a whitelist would reject the fifth honest one a future
    module invents. What can be named exactly is the mistake - handing over the
    GameLog itself.
    """
    for kw in call.keywords:
        if kw.arg != "log":
            continue
        value = kw.value
        if isinstance(value, ast.Attribute) and value.attr == "game_log":
            return False
        if isinstance(value, ast.Name) and value.id == "game_log":
            return False
    return True


_mw_bad_log = sorted(n for n in _mw_creators
                     if not all(_mw_log_arg_ok(c) for c in _mw_calls(_mw_trees[n])))
ck.true("the guard is live - it checked %d construction sites"
        % sum(len(_mw_calls(_mw_trees[n])) for n in _mw_creators),
        sum(len(_mw_calls(_mw_trees[n])) for n in _mw_creators) >= 18)
ck.eq("no session is handed the GameLog object as its log", _mw_bad_log, [])
# Named individually, so a partial regression reads as a name and not as a
# list diff.
for _mod in ("drakolithe.py", "harvester_of_souls.py", "monofilament_snare.py"):
    ck.true("%s hands its session a callable log" % _mod, _mod not in _mw_bad_log)

# --------------------------------------------------------------------------
# 17c. ...and main.py knows about all four
# --------------------------------------------------------------------------
# Section 17 proves the module CAN answer. These prove main.py ASKS - which
# then drags sections 6, 10, 11 and 12 in behind them for free.
# The phase gate is read as its OWN function body, not as "the name appears in
# main.py": the click branch mentions pending_damage_choice too, so a whole-file
# search stays green with the gate term deleted. Found by this section's own
# A/B probe, which reported NO BITE until the body was isolated.
_MW_GATE_BODY = ""
for _node in ast.walk(ast.parse(SRC)):
    if (isinstance(_node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and _node.name == "_has_unresolved_declaration"):
        _MW_GATE_BODY = ast.get_source_segment(SRC, _node) or ""
ck.true("the phase gate body was found", len(_MW_GATE_BODY) > 200)

for _ctrl in ("wraith_form_controller", "drakolithe_controller",
              "harvester_of_souls_controller", "monofilament_snare_controller"):
    ck.true("%s is asked about its damage choice" % _ctrl,
            "%s.pending_damage_choice" % _ctrl in SRC)
    ck.true("...and the phase gate waits on %s" % _ctrl,
            "%s.pending_damage_choice" % _ctrl in _MW_GATE_BODY)

# --------------------------------------------------------------------------
# 17d. a CALLABLE log is never used as the GameLog OBJECT
# --------------------------------------------------------------------------
print("=== 17d. a callable log is never called as .log.add(...) ===")

# THE MIRROR OF 17b, one level in. 17b guards the CALLER ("what you hand a
# session as log= must be callable"); this guards the CALLEE ("a class that
# stores a callable must not then treat it as the object").
#
# This repo runs TWO logging idioms, told apart only by the FIELD NAME:
#
#   self.game_log -> the GameLog OBJECT, written as self.game_log.add(msg).
#                    ~90 controllers.
#   self.log      -> a CALLABLE (a bound _log, or a lambda), written as
#                    self.log(msg). Four modules: damage_resolution,
#                    dice_notation, feel_no_pain, hazard.
#
# damage_resolution.py's automatic Damage re-roll branch was written in the
# first idiom against a field holding the second. It shipped because the ONLY
# weapon that can reach that branch is the D-cannon (Structural Collapse,
# "re-roll a Damage roll of 1"), and firing it crashed the game outright:
#   AttributeError: 'function' object has no attribute 'add'
# Its suite held throughout - it drove auto_reroll_for() directly and pinned
# the source string "auto_reroll_for(amount)", and both of those are true of a
# branch whose body has never run.
#
# A behaviour test cannot see the NEXT crossing, because the line does not
# exist yet. Hence a source sweep - and by AST, not substring: `.log.add(` also
# matches game/strategic_reserves.py's withdraw_to_reserves(log=...), whose
# `log` parameter really is the object (all nine callers pass log=self.game_log)
# and which is therefore correct. What is being pinned is the SELF-attribute
# contract, so that is what gets parsed.

_LOG_FIELD_CLASSES = {}     # module -> {class names that store a callable self.log}
for _name, _tree in _mw_trees.items():
    for _cls in [n for n in ast.walk(_tree) if isinstance(n, ast.ClassDef)]:
        for _fn in [n for n in _cls.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and n.name == "__init__"]:
            if "log" not in [a.arg for a in _fn.args.args + _fn.args.kwonlyargs]:
                continue
            for _st in ast.walk(_fn):
                if not isinstance(_st, ast.Assign):
                    continue
                for _t in _st.targets:
                    if (isinstance(_t, ast.Attribute) and _t.attr == "log"
                            and isinstance(_t.value, ast.Name) and _t.value.id == "self"
                            and isinstance(_st.value, ast.Name) and _st.value.id == "log"):
                        _LOG_FIELD_CLASSES.setdefault(_name, set()).add(_cls.name)

# Liveness: a sweep that stops finding the contract reports no violations and
# reads exactly like a pass.
ck.true("the sweep found the callable-log classes (it is not vacuous): %d in %d module(s)"
        % (sum(len(v) for v in _LOG_FIELD_CLASSES.values()), len(_LOG_FIELD_CLASSES)),
        len(_LOG_FIELD_CLASSES) >= 4)
for _known in ("damage_resolution.py", "dice_notation.py", "feel_no_pain.py", "hazard.py"):
    ck.true("%s is in the sweep" % _known, _known in _LOG_FIELD_CLASSES)


def _self_log_add_lines(tree):
    """Lines calling self.log.add(...) - the crossing, as an AST shape."""
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add"):
            continue
        inner = node.func.value
        if (isinstance(inner, ast.Attribute) and inner.attr == "log"
                and isinstance(inner.value, ast.Name) and inner.value.id == "self"):
            out.append(node.lineno)
    return out


for _name in sorted(_LOG_FIELD_CLASSES):
    _bad = _self_log_add_lines(_mw_trees[_name])
    ck.eq("%s never calls .add() on its callable log" % _name, _bad, [])
    # The positive half: the contract is real, not assumed. A module that
    # stores `log` and never calls it would make the check above vacuous.
    _calls_it = any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "log" and isinstance(n.func.value, ast.Name)
        and n.func.value.id == "self"
        for n in ast.walk(_mw_trees[_name]))
    ck.true("...and really does CALL it, so the contract is callable", _calls_it)

# And the caller half, generalised from 17b to every one of these classes: a
# construction site that hands one of them the GameLog object is the same bug
# seen from the other end.
_LOG_CLASS_NAMES = {c for v in _LOG_FIELD_CLASSES.values() for c in v}


def _log_ctor_calls(tree):
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if ((isinstance(func, ast.Name) and func.id in _LOG_CLASS_NAMES)
                or (isinstance(func, ast.Attribute) and func.attr in _LOG_CLASS_NAMES)):
            out.append(node)
    return out


_ctor_sites = sum(len(_log_ctor_calls(t)) for t in _mw_trees.values())
ck.true("the caller sweep is live - %d construction site(s)" % _ctor_sites,
        _ctor_sites >= 10)
_bad_ctors = sorted(n for n, t in _mw_trees.items()
                    if not all(_mw_log_arg_ok(c) for c in _log_ctor_calls(t)))
ck.eq("no callable-log class is handed the GameLog object", _bad_ctors, [])

# --------------------------------------------------------------------------
# 18. An offer that names ONE unit out of several must let the player CHOOSE
# --------------------------------------------------------------------------
# REPORTED: "cost of victory wird mir pauschal angeboten, aber ich habe 3
# guardian squads. ich kann nicht waehlen welchen squad zurueck in reserve
# schicken will. es muss auf dem feld angeklickt werden."
#
# Four Stratagems printing "TARGET: One <X> unit from your army" looped over
# the eligible units, raised a prompt about whichever sorted FIRST, and
# returned - so the other candidates were never mentioned and the one that was
# could only be accepted or declined. A BEHAVIOUR test cannot see the fifth,
# because it does not exist yet; and the four owning suites could not see these
# four either, because each stages exactly ONE eligible squad, where the broken
# and the correct shape are indistinguishable. So the guard is a rule about
# the SOURCE.
#
# THE INVARIANT, and it is narrow on purpose: an offer that raises a request
# from INSIDE a loop over candidates must TAG at least one option with a unit.
# Naming a unit in the prompt TEXT and offering a bare yes/no is the shape that
# was reported - the engine has already chosen, and the player is asked to
# rubber-stamp it.
#
# WHAT THIS DELIBERATELY DOES NOT FLAG, measured rather than assumed: four
# per-unit ABILITIES raise their request inside such a loop too
# (auxiliary_cadre, elemental_ensnarement, hallucinogen_grenades,
# neocapacitor_shields). Every one of them tags its options with the ENEMY unit
# the ability targets, so the player still chooses on the board; the loop there
# is over BEARERS, which is a different question (see game/per_unit_offer.py).
# A guard that flagged them would be a false-alarm machine, and a guard with
# false alarms gets deleted.
print("\n18. one-unit-out-of-several offers")


def _has_three_tuple(node):
    for sub in ast.walk(node):
        if isinstance(sub, ast.Tuple) and len(sub.elts) == 3:
            return True
    return False


def _tags_a_unit(call, func):
    """Does this request() call pass any THREE-tuple option? That third slot
    is what game/unit_pick.py reads to make a prompt clickable.

    A bare NAME argument is resolved against the assignments in `func` first.
    Without that, neocapacitor_shields.py - which builds `options = [...]` and
    then passes it - reads as untagged, and the guard reports a unit choice
    that is in fact perfectly clickable. Found by this section's own first run:
    a guard with false alarms gets deleted, so it has to see what the code
    actually passes."""
    args = list(call.args) + [kw.value for kw in call.keywords]
    for arg in args:
        if _has_three_tuple(arg):
            return True
        if isinstance(arg, ast.Name):
            for sub in ast.walk(func):
                targets = []
                if isinstance(sub, ast.Assign):
                    targets = sub.targets
                elif isinstance(sub, (ast.AugAssign, ast.AnnAssign)):
                    targets = [sub.target]
                if any(isinstance(t, ast.Name) and t.id == arg.id for t in targets):
                    if sub.value is not None and _has_three_tuple(sub.value):
                        return True
                # options.append((label, cb, squad))
                if (isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Attribute)
                        and isinstance(sub.func.value, ast.Name)
                        and sub.func.value.id == arg.id
                        and _has_three_tuple(sub)):
                    return True
    return False


_untagged_offers = []
_offers_seen = 0
for _fname in sorted(os.listdir("game")):
    if not _fname.endswith(".py"):
        continue
    _src = io.open(os.path.join("game", _fname), encoding="utf-8").read()
    try:
        _tree = ast.parse(_src)
    except SyntaxError:
        continue
    for _node in ast.walk(_tree):
        if not (isinstance(_node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and _node.name.startswith("offer_at_")):
            continue
        for _loop in [n for n in ast.walk(_node) if isinstance(n, ast.For)]:
            _reqs = [c for c in ast.walk(_loop)
                     if isinstance(c, ast.Call)
                     and isinstance(c.func, ast.Attribute)
                     and c.func.attr == "request"]
            if not _reqs:
                continue
            _offers_seen += 1
            if not any(_tags_a_unit(c, _node) for c in _reqs):
                _untagged_offers.append("%s.%s" % (_fname, _node.name))

# Liveness: a sweep that stops finding these offers reports zero and looks like
# a pass. Four legitimate ones exist today.
ck.true("the sweep really examined some looping offers", _offers_seen >= 4)
ck.eq("no looping offer raises an untagged prompt", sorted(set(_untagged_offers)), [])
for _mod in ("guardian_cost_of_victory", "warhost_webway_tunnel",
             "skyborne_sanctuary", "windrider_overflight"):
    ck.true("%s offers every candidate, not just the first" % _mod,
            "unit_choice_offer.offer_one_of(" in
            io.open("game/%s.py" % _mod, encoding="utf-8").read())

# ---------------------------------------------------------------------------
# 19. EVERY RUNTIME [PISTOL] GRANT REACHES THE ENGAGED-SHOOTING GATE
# ---------------------------------------------------------------------------
print()
print("=== 19. every [PISTOL] grant is read by the engaged-shooting gate ===")

# The [PISTOL] twin of section 7, and it exists because that section's warning
# came true a second time. [PISTOL] is read in TWO places that look nothing
# like each other:
#
#   * ShootingController's adjuster chain - the damage maths, easy to wire and
#     easy to test, and what every unit test drives;
#   * is_close_quarters(), reached from available_shooting_types() and
#     _weapon_eligible_for_type(), which is the ONLY thing that decides whether
#     an ENGAGED unit may shoot at all (rule 10.06). That permission is the
#     entire reason [PISTOL] gets granted.
#
# The one shipped grant, Blades of Asuryan, was wired to the chain and not the
# gate. REPORTED: "ich konnte zwar mit asurmen schiessen, aber nicht mit dem
# rest meines avengers squads. das umwandeln der waffen in pistol hat wohl
# nicht geklappt." Measured on that scene: the chain granted [PISTOL] to 6 of 6
# ranged weapons while the gate saw 1 of 6 - Asurmen's Bloody Twins, which is
# printed [PISTOL], which is why he alone could fire.
#
# A behaviour test cannot see a SECOND grant appearing, so this is a source
# sweep: any module that hands out `.pistol = True` at runtime must be named
# inside is_close_quarters()'s body.
_SHOOT_SRC = io.open(os.path.join("game", "shooting.py"), encoding="utf-8").read()
_ICQ = "def is_close_quarters("
ck.true("is_close_quarters() was found", _ICQ in _SHOOT_SRC)
_ICQ_BODY = ""
for _node in ast.walk(ast.parse(_SHOOT_SRC)):
    if (isinstance(_node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and _node.name == "is_close_quarters"):
        _ICQ_BODY = ast.get_source_segment(_SHOOT_SRC, _node) or ""
ck.true("...and its body was isolated", len(_ICQ_BODY) > 200)

# Documented gaps, named rather than silently subtracted - and a future entry
# has to carry the MEASUREMENT that says it is dormant, not a recollection of
# one. Section 7's comment records what a stale justification costs.
_PISTOL_GRANT_GAPS = set()

_pistol_grantors = sorted(
    name[:-3]
    for name in os.listdir("game")
    if name.endswith(".py") and name[:-3] not in ("weapons", "shooting")
    and ".pistol = True" in io.open(os.path.join("game", name), encoding="utf-8").read()
)
# Liveness: a sweep that stops finding grantors reports an empty difference and
# looks exactly like a pass.
ck.true("the sweep found the known grantor (it is not vacuous)",
        len(_pistol_grantors) >= 1)
for _mod in _pistol_grantors:
    if _mod in _PISTOL_GRANT_GAPS:
        ck.true("%s is the documented gap, and says so in is_close_quarters()" % _mod,
                _mod in _ICQ_BODY)
        continue
    ck.true("%s's [PISTOL] grant is read by the engaged-shooting gate" % _mod,
            ("%s.adjusted_weapon(" % _mod) in _ICQ_BODY
            or ("%s.is_active(squad)" % _mod) in _ICQ_BODY
            or ("%s.applies(squad)" % _mod) in _ICQ_BODY)

# The gate can only ask about a grant if it is TOLD which unit is shooting, so
# the parameter is mandatory - a default would be the very bug this section is
# about, silently restored (the reasoning _detectable_models() gives for its
# own). Checked on the signature rather than on a call site: one forgotten
# caller is what a mandatory parameter turns into a crash instead of a no-op.
for _node in ast.walk(ast.parse(_SHOOT_SRC)):
    if (isinstance(_node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and _node.name in ("is_close_quarters", "_weapon_side")):
        _args = [a.arg for a in _node.args.args]
        ck.eq("%s() takes the squad" % _node.name, _args[-1], "squad")
        ck.eq("...with no default that could hide a missed caller" % (),
              len(_node.args.defaults), 0)

ck.finish()
