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
"""
import ast
import builtins
import io
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


def _module_names(tree):
    names = set()
    for node in tree.body:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                names.add(sub.id)
            elif isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(sub.name)
            elif isinstance(sub, (ast.Import, ast.ImportFrom)):
                for a in sub.names:
                    names.add((a.asname or a.name).split(".")[0])
    return names


# --------------------------------------------------------- 1. unbound names
print("\n=== 1. no undefined name is read inside main() ===")

bound = _bound_names(MAIN)
module_level = _module_names(TREE)
loaded = {}
for node in ast.walk(MAIN):
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
        loaded.setdefault(node.id, node.lineno)

unbound = sorted(
    (name, line) for name, line in loaded.items()
    if name not in bound and name not in module_level and not hasattr(builtins, name)
)
# The reported crash was exactly one entry here: ('board_rect', 3021).
ck.eq("free names in main() that are bound nowhere", unbound, [])

# The board rectangle has exactly one name, and this is it. A branch that
# invents a second one is how the crash happened in the first place.
ck.true("board_rect_screen is the bound name for the board rect",
        "board_rect_screen" in bound)
ck.eq("no bare `board_rect` survives anywhere in main.py",
      SRC.count("board_rect.collidepoint"), 0)


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


def _first_binding_line(fn):
    """Line at which each plain local name is first assigned."""
    out = {}
    for node in ast.walk(fn):
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


_bound_at = _first_binding_line(_main_fn)

_too_early = []
for node in ast.walk(_main_fn):
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
_pairs = sum(1 for node in ast.walk(_main_fn)
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

ck.finish()
