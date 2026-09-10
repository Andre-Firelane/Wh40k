"""The base-contact house rule: no Pile-In and no Consolidation for a model
already touching an enemy.

  User: "Modelle in Base contact duerfen weder Pile in noch consolidate moves
   durchfuehren... als Base contact wuerde ich weniger als 0,2 Zoll Abstand
   definieren."

  ...and, raised separately and load-bearing: "denke aber daran, dass bei einem
   rueckzug models natuerlich den base contact verlassen koennen."

WHAT EXISTED BEFORE was an OPTIMISATION covering a fraction of this: one
`continue` in ai/agent_driver.py's phase-2 spreading loop - AI only, pile-in
only, against the ONE aimed target squad, at 0.15". The human side had nothing:
clamp_move() carried no contact term at all, so a player could drag any model
its full 3" in either move. Consolidation had nothing on either side.

THE COUNTER-CHECK IS THE POINT OF SECTION 3. A version of this rule that keyed
off "is this model engaged" rather than off the MOVE MODE would trap a bound
unit on the table forever - it could never Fall Back out of contact. So every
other mode is walked here, both Fall Back modes included. Without that section,
this file would pass just as happily against a fix that froze every move in the
game.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import testkit as tk  # noqa: E402
from game import base_contact  # noqa: E402
from game.factions import orks  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game.squad import edge_distance  # noqa: E402

checks = tk.Checks("Base contact")


def scene(gap):
    """One friendly model and one enemy, `gap` inches edge to edge."""
    mine = tk.build(orks.BOYZ, "Player 1", name="1 Boyz 1")
    theirs = tk.build(orks.BOYZ, "Player 2", name="2 Boyz 1")
    tk.line_up(mine, x=10.0, y=10.0)
    tk.line_up(theirs, x=40.0, y=40.0)
    a, b = mine.models[0], theirs.models[0]
    b.x_in = a.x_in + a.radius_in + b.radius_in + gap
    b.y_in = a.y_in
    return mine, theirs, a, b


# --- 1. the predicate, walked across the threshold -------------------------
print("--- 1. the threshold ---")

for gap, frozen in ((0.0, True), (0.05, True), (0.19, True),
                    (0.2, False), (0.21, False), (5.0, False)):
    mine, theirs, a, b = scene(gap)
    tokens = list(mine.models) + list(theirs.models)
    got = base_contact.is_frozen(a, mine, tokens, "pile_in")
    checks.eq("a gap of %.2f\" is %s" % (gap, "contact" if frozen else "clear"), got, frozen)
    # Measured, not assumed: the fixture really does sit where it says.
    checks.true("...and the fixture really is %.2f\" apart" % gap,
                abs(edge_distance(a, b) - gap) < 0.001)

# The threshold is asserted against the CONSTANT, not against 0.2 - so tuning
# it moves the rule rather than breaking the test for the wrong reason.
mine, theirs, a, b = scene(base_contact.BASE_CONTACT_GAP_IN - 0.01)
checks.true("just inside BASE_CONTACT_GAP_IN is contact",
            base_contact.is_frozen(a, mine, list(mine.models) + list(theirs.models), "pile_in"))
mine, theirs, a, b = scene(base_contact.BASE_CONTACT_GAP_IN + 0.01)
checks.eq("just outside it is not",
          base_contact.is_frozen(a, mine, list(mine.models) + list(theirs.models), "pile_in"),
          False)
checks.eq("the user's definition, as shipped", base_contact.BASE_CONTACT_GAP_IN, 0.2)


# --- 2. ANY enemy, and only LIVING ones ------------------------------------
print("--- 2. any enemy, living only ---")

# The one place this is STRICTER than the optimisation it replaces: that one
# measured against the single aimed target squad. A model wedged against a
# non-target enemy is as stuck as one against the target.
mine, target, a, _b = scene(4.0)
other = tk.build(orks.BOYZ, "Player 2", name="2 Boyz 2")
tk.line_up(other, x=60.0, y=60.0)
c = other.models[0]
c.x_in, c.y_in = a.x_in + a.radius_in + c.radius_in + 0.05, a.y_in
tokens = list(mine.models) + list(target.models) + list(other.models)
checks.true("contact with a NON-target enemy freezes too",
            base_contact.is_frozen(a, mine, tokens, "pile_in"))

# A model that died this frame is still in every list (Fehlerklasse 12) and
# must not pin anyone: remove_dead_models() has not run yet.
for m in other.models:
    m.current_wounds = 0
checks.eq("a corpse does not freeze anyone",
          base_contact.is_frozen(a, mine, tokens, "pile_in"), False)

# Friendlies never freeze - the rule is about enemies.
friend = tk.build(orks.BOYZ, "Player 1", name="1 Boyz 2")
tk.line_up(friend, x=70.0, y=70.0)
f = friend.models[0]
f.x_in, f.y_in = a.x_in + a.radius_in + f.radius_in + 0.05, a.y_in
checks.eq("a friendly model in contact does not freeze",
          base_contact.is_frozen(a, mine, list(mine.models) + list(friend.models), "pile_in"),
          False)

# frozen_models() has to name the SAME set the clamp enforces - the renderer,
# the panel hint and the log all read it.
mine2, theirs2, a2, _b2 = scene(0.05)
tokens2 = list(mine2.models) + list(theirs2.models)
listed = base_contact.frozen_models(mine2, tokens2, "pile_in")
checks.true("frozen_models() names the model the clamp freezes", a2 in listed)
checks.eq("...and every model it names really is frozen",
          [m for m in listed
           if not base_contact.is_frozen(m, mine2, tokens2, "pile_in")], [])


# --- 3. ONLY the two moves - a retreat always leaves contact ----------------
print("--- 3. every other move is untouched ---")

# THE USER'S CONSTRAINT, and the counter-check without which this whole file
# would pass against a fix that froze every move in the game.
mine, theirs, a, _b = scene(0.05)
tokens = list(mine.models) + list(theirs.models)
checks.true("the model IS in contact", base_contact.in_base_contact(
    a, base_contact.enemy_models(mine, tokens)))

for mode in ("pile_in", "consolidate"):
    checks.true("%s freezes it" % mode, base_contact.is_frozen(a, mine, tokens, mode))

for mode in (None, "fall_back", "retro_thrusters_fall_back", "charge",
             "surge", "scout", "battle_focus", "torchstar"):
    checks.eq("%s does NOT freeze it" % (mode or "an ordinary move"),
              base_contact.is_frozen(a, mine, tokens, mode), False)

# Both Fall Back modes are named explicitly, because there are two and missing
# one would strand a unit under exactly the rule the user warned about.
checks.eq("the frozen set is exactly the two moves",
          sorted(base_contact.FROZEN_MOVE_MODES), ["consolidate", "pile_in"])


# --- 4. the clamp and the pick-up gate -------------------------------------
print("--- 4. clamp_move and is_movable ---")


def mover(squad, tokens, mode):
    """A MovementController with the move already open.

    selected_squad is set directly rather than through select(), which takes a
    TOKEN and runs can_select()'s phase rules - none of which this file is
    about. The move STARTERS are real, so move_mode and the per-model budgets
    come from the engine."""
    mc = MovementController(all_tokens=tokens)
    mc.selected_squad = squad
    if mode == "pile_in":
        mc.start_pile_in_move(3.0, [])
    elif mode == "consolidate":
        mc.start_consolidate_move(3.0, [], "ongoing")
    return mc


mine, theirs, a, _b = scene(0.05)
free = mine.models[5]
free.x_in, free.y_in = 25.0, 25.0
tokens = list(mine.models) + list(theirs.models)

mc = mover(mine, tokens, "pile_in")
checks.eq("the mode really is pile_in", mc.move_mode, "pile_in")
before = (a.x_in, a.y_in)
got = mc.clamp_move(a, a.x_in + 2.0, a.y_in)
checks.eq("clamp_move() returns a frozen model to its origin", got, before)
checks.eq("...and it cannot even be picked up", mc.is_movable(a), False)
checks.true("...while a model NOT in contact still can be", mc.is_movable(free))
moved = mc.clamp_move(free, free.x_in + 1.0, free.y_in)
checks.true("...and really moves", moved != (free.x_in, free.y_in))

# The same, for a CONSOLIDATION - which had no rule at all before, on either
# side. This is the half the AI optimisation never covered.
mine, theirs, a, _b = scene(0.05)
tokens = list(mine.models) + list(theirs.models)
mc = mover(mine, tokens, "consolidate")
checks.eq("the mode really is consolidate", mc.move_mode, "consolidate")
checks.eq("a consolidation freezes it too", mc.clamp_move(a, a.x_in + 2.0, a.y_in),
          (a.x_in, a.y_in))

# THE RETREAT, end to end and through the same clamp. This is the user's own
# constraint, and it is the case that matters most: a unit in base contact
# cannot make an ordinary Move at all (09.07 sends it to Fall Back), so if the
# freeze reached Fall Back the unit would be stuck on the table for good.
#
# Measured rather than assumed - can_make_move() refuses an engaged squad, so
# staging a "normal move" here would have tested nothing and passed for the
# wrong reason. It did, on the first run.
mine, theirs, a, _b = scene(0.05)
tokens = list(mine.models) + list(theirs.models)
mc = MovementController(all_tokens=tokens)
mc.selected_squad = mine
checks.eq("an engaged unit cannot make an ordinary Move (09.07)",
          mc.can_make_move(mine), False)
mc.start_fall_back_move("ordered_retreat")
checks.eq("...it Falls Back instead", mc.move_mode, "fall_back")
checks.true("a model in base contact CAN be picked up to retreat",
            mc.is_movable(a))
retreated = mc.clamp_move(a, a.x_in - 2.0, a.y_in)
checks.true("...and the clamp really lets it leave contact",
            retreated != (a.x_in, a.y_in))

# ...and an ordinary Movement-phase move is untouched too, on a unit that is
# free to make one.
clear_mine = tk.build(orks.BOYZ, "Player 1", name="1 Boyz 3")
tk.line_up(clear_mine, x=10.0, y=30.0)
mc2 = MovementController(all_tokens=list(clear_mine.models))
mc2.selected_squad = clear_mine
mc2.start_move()
checks.eq("an ordinary move has no frozen mode", mc2.move_mode, None)
free2 = clear_mine.models[0]
checks.true("...and its models move", mc2.is_movable(free2))


# --- 5. the GROUP drag: the front stands, the rest follows ------------------
print("--- 5. the group drag ---")

# The user's decision when asked how the whole-unit drag should behave with a
# frozen model in it: "Front steht, Rest zieht."
#
# It needs NO code of its own, and that is the finding rather than a
# convenience: apply_group_drag() clamps each model INDEPENDENTLY through
# clamp_move(), and its own docstring already says the translation is not
# rigid in practice ("one model hitting an obstacle/board edge doesn't halt
# the others - it just won't travel as far"). So the freeze falls out of the
# clamp, and game/whole_unit_drag.py and game/line_drag.py are untouched.
#
# The "no squadmate overlap by construction" guarantee is PINNED here rather
# than argued: a frozen model stays on a position that was already legal, and
# commit_group_drag() validates each model against the others.
# The enemy goes PERPENDICULAR to the rank here, not along it. line_up() lays
# the squad out on x, and scene() puts the enemy on +x - which drops it inside
# the formation, touching two of my own models AND overlapping one from the
# start. The overlap check below then measures the fixture rather than the
# drag; it did, on the first run.
mine = tk.build(orks.BOYZ, "Player 1", name="1 Boyz 1")
theirs = tk.build(orks.BOYZ, "Player 2", name="2 Boyz 1")
tk.line_up(mine, x=10.0, y=10.0)
tk.line_up(theirs, x=40.0, y=40.0)
front = mine.models[0]
foe = theirs.models[0]
foe.x_in = front.x_in
foe.y_in = front.y_in - (front.radius_in + foe.radius_in + 0.05)
tokens = list(mine.models) + list(theirs.models)
checks.true("exactly one model starts in base contact",
            len(base_contact.frozen_models(mine, tokens, "pile_in")) == 1)
mc = mover(mine, tokens, "pile_in")
frozen_before = (front.x_in, front.y_in)
others_before = {m.id: (m.x_in, m.y_in) for m in mine.models[1:]}

# Dragged ACROSS the enemy rather than into it: the point is what the frozen
# model does, and a drag that pushes squadmates onto the enemy base would be
# refused for a different reason entirely.
# Dragged ALONG the rank, away from the enemy: the point is what the frozen
# model does, and a drag that pushes squadmates onto the enemy base would be
# refused for an entirely different reason.
mc.apply_group_drag(1.0, 0.0)
mc.commit_group_drag()

checks.eq("the frozen front model did not move",
          (front.x_in, front.y_in), frozen_before)
moved = [m for m in mine.models[1:] if (m.x_in, m.y_in) != others_before[m.id]]
checks.true("...while the rest of the unit followed the drag (%d of %d)"
            % (len(moved), len(mine.models) - 1), len(moved) > 0)
checks.eq("...and no squadmates ended up overlapping",
          mine.check_model_overlap(tokens), [])
# A rule turned into an error message would be the wrong fix - the errors list
# is for illegal play, and standing still is not illegal.
checks.eq("...and nothing was reported as an error", mc.errors, [])

# whole_unit_drag.py and line_drag.py really are untouched - asserted at the
# source, because "it works" and "it needed no change" are two claims.
import io as _io  # noqa: E402
for _mod in ("game/whole_unit_drag.py", "game/line_drag.py"):
    checks.eq("%s needs no base-contact code" % _mod,
              "base_contact" in _io.open(_mod, encoding="utf-8").read(), False)


checks.finish()
