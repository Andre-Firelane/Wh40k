"""The innermost packing ring has to clear the model standing on the drop
point - and that model is the WIDEST one in the unit, not the smallest.

Reported on the Necron Warriors: "welcher Mechanismus sorgt eigentlich dafuer,
dass hier die Nekonkrieger so viel Abstand zu ihrem Character halten, der
angeschlossen ist? Das sorgt nur dafuer, dass der Footprint unnoetig gross
wird. Koennen Sie sich bitte enger hinstellen?"

WHAT THE MECHANISM WAS
----------------------
game/formation_layout.py pitches its candidate grid off the SMALLEST base in
the unit, for a documented reason (pitching the 22-model Boyz mob off its
0.98" Warboss instead blows it out from 6.24" to 9.00" across - which rule
09.02's 9" span limit still rejects for Player 1, though not for the AI, whose
half of that limit config.SPREAD_LIMIT_PLAYERS lifted). But
_fill() picks widest-model-first, so the model that lands on the drop point is
the widest one - and _first_legal_slot()'s overlap bound then measures every
first-ring slot against IT. A 0.98" Technomancer among 0.63" Warriors needs
1.66" of centre-to-centre clearance while the ring sits at 1.50", so the ring
did not lose a slot to the character, it lost ALL SIX. The Warriors' block
started at ring 2 and the character sat alone in a moat.

That is a distinct failure from game/front_rank.py's, which is about melee
characters ending up buried in the MIDDLE. This one only bites units whose
character is NOT a front-rank fighter - a Technomancer, a Plasmancer - because
those are exactly the ones left in the plain widest-first order.

Every claim below is measured against the pre-fix world (inner_radius removed),
not against a remembered number.
"""

import math
import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")

from testkit import Checks

from game import army_lists, attached_units, formation_layout, front_rank, maps
from game.squad import spread_limit_applies

c = Checks("pack: innermost ring clears the widest model")

maps.apply_to_config(maps.get("map2"))

ORIGIN = (30.0, 36.0)
FACING = -math.pi / 2


# ------------------------------------------------------------------ helpers

def unit(army, needle, owner="player2"):
    return next(s for s in army_lists.preview_squads(army, owner) if needle in s.name)


def pack(squad, pre_fix=False):
    """Slots for `squad`, optionally with the whole pre-fix world restored -
    i.e. ring_candidates() ignoring inner_radius, which is exactly what it did
    before. Restored by wrapping the real function rather than by passing a
    flag, so the probe cannot accidentally test a half-neutralised packer."""
    if not pre_fix:
        return formation_layout.pack_positions(squad, *ORIGIN, base_angle=FACING)
    real = formation_layout.ring_candidates

    def without(ox, oy, step, base_angle, rings=formation_layout.PACK_RINGS,
                inner_radius=None):
        return real(ox, oy, step, base_angle, rings)

    formation_layout.ring_candidates = without
    try:
        return formation_layout.pack_positions(squad, *ORIGIN, base_angle=FACING)
    finally:
        formation_layout.ring_candidates = real


def leader_index(squad):
    if not attached_units.is_attached_unit(squad):
        return None
    leaders = attached_units.leader_models(squad, alive_only=False)
    return next((i for i, m in enumerate(squad.models)
                 if any(m is lead for lead in leaders)), None)


def gap_to_nearest(squad, slots, index):
    """Edge-to-edge distance from this model to its closest squadmate - the
    "moat" the report is about."""
    return min(math.dist(slots[index], slots[j])
               - squad.models[index].radius_in - squad.models[j].radius_in
               for j in range(len(slots)) if j != index)


def spread(squad, slots):
    """The unit's edge-to-edge footprint: what rule 09.02's span limit and
    hiding a unit behind terrain both actually look at. The radius of the
    outermost candidate ring is NOT this - it moves in whole ring steps and so
    reports a change of grid as a change of formation."""
    return max(math.dist(slots[i], slots[j])
               - squad.models[i].radius_in - squad.models[j].radius_in
               for i in range(len(slots)) for j in range(i + 1, len(slots)))


def ring_census(squad, slots, step):
    """How many models landed on each ring index, counting from the drop
    point. The reported bug is visible here as a zero."""
    out = {}
    for slot in slots:
        out[round(math.dist(slot, ORIGIN) / step)] = \
            out.get(round(math.dist(slot, ORIGIN) / step), 0) + 1
    return out


def step_of(squad):
    return max(formation_layout.MODEL_GAP_IN,
               2 * min(m.radius_in for m in squad.models) + 0.1)


# --------------------------------------------------- 1. the reported unit

print("--- 1. the reported unit: Necron Warriors + Technomancer ---")

warriors = unit("necrons", "Necron Warriors")
li = leader_index(warriors)

c.eq("21 models", len(warriors.models), 21)
c.eq("two base sizes - this is what makes the grid and the centre model "
     "disagree", sorted({round(m.radius_in, 3) for m in warriors.models}),
     [0.63, 0.984])
c.eq("the character is NOT a front-rank fighter, so nothing promotes him out "
     "of the plain widest-first order and he takes the drop point",
     len(front_rank.front_rank_models(warriors)), 0)

before = pack(warriors, pre_fix=True)
after = pack(warriors)
step = step_of(warriors)

c.eq("the ring pitch comes from the SMALLEST base and is unchanged", round(step, 2), 1.5)
c.true("but the widest model needs more than that to have a neighbour at all "
       f"({0.984 + 0.63 + 0.05:.2f}\" > {step:.2f}\")", 0.984 + 0.63 + 0.05 > step)

c.eq("the character stood on the drop point before the fix",
     round(math.dist(before[li], ORIGIN), 2), 0.0)
c.eq("and still does - the fix moves the RING, not him",
     round(math.dist(after[li], ORIGIN), 2), 0.0)

census_before = ring_census(warriors, before, step)
census_after = ring_census(warriors, after, step)
c.eq("before: the entire first ring seated nobody", census_before.get(1, 0), 0)
c.true(f"after: it seats models again ({census_after.get(1, 0)})",
       census_after.get(1, 0) > 0)

moat_before = gap_to_nearest(warriors, before, li)
moat_after = gap_to_nearest(warriors, after, li)
c.eq(f"before, the character's moat was {moat_before:.2f}\"",
     round(moat_before, 2), 1.39)
c.true(f"after it is {moat_after:.2f}\" - the units are touching",
       moat_after < 0.1)
c.true("which is the smallest gap the overlap bound allows, not an arbitrary "
       "smaller number", moat_after >= 0.05)

rank_before = sorted(gap_to_nearest(warriors, before, i)
                     for i in range(len(before)) if i != li)
rank_after = sorted(gap_to_nearest(warriors, after, i)
                    for i in range(len(after)) if i != li)
c.true(f"the rank and file were never the problem - they stood "
       f"{rank_before[len(rank_before) // 2]:.2f}\" apart, roughly a fifth of "
       f"the character's moat", rank_before[len(rank_before) // 2] < moat_before / 4)
c.true(f"and they are no looser afterwards "
       f"({rank_before[len(rank_before) // 2]:.2f}\" -> "
       f"{rank_after[len(rank_after) // 2]:.2f}\") - the block did not merely "
       f"trade the character's moat for a wider grid",
       rank_after[len(rank_after) // 2] <= rank_before[len(rank_before) // 2] + 1e-9)

c.true(f"and the footprint shrinks with it "
       f"({spread(warriors, before):.2f}\" -> {spread(warriors, after):.2f}\")",
       spread(warriors, after) < spread(warriors, before))
c.eq("measured", round(spread(warriors, before), 2), 7.20)
c.eq("measured", round(spread(warriors, after), 2), 6.24)

c.eq("no model is left stacked on the drop point (that is how "
     "pack_positions() reports failure)",
     sum(1 for i, s in enumerate(after) if i != li and math.dist(s, ORIGIN) < 1e-9), 0)


# ---------------------------------------- 2. nobody overlaps, 09.02 holds

print("--- 2. the tighter block is still legal ---")

worst = min(math.dist(after[i], after[j])
            - warriors.models[i].radius_in - warriors.models[j].radius_in
            for i in range(len(after)) for j in range(i + 1, len(after)))
c.true(f"no two bases overlap (closest pair {worst:.3f}\" apart)", worst >= 0.05)

placed = [(x, y, warriors.models[i].radius_in) for i, (x, y) in enumerate(after)]
c.true("and the unit is one connected group under rule 09.02",
       formation_layout.bridge_count(placed) is not None)
c.true("no more fragile than before, either",
       formation_layout.bridge_count(placed)
       <= formation_layout.bridge_count(
           [(x, y, warriors.models[i].radius_in) for i, (x, y) in enumerate(before)]))


# ------------------------------- 3. the same defect across both armies

print("--- 3. every other unit: better or untouched, never worse ---")

for army, needle, want_before, want_after in (
    ("necrons", "Necron Warriors", 1.39, 0.05),
    ("necrons", "Immortals", 0.24, 0.24),   # one base size: nothing to fix
):
    squad = unit(army, needle)
    index = leader_index(squad)
    was = gap_to_nearest(squad, pack(squad, pre_fix=True), index)
    now = gap_to_nearest(squad, pack(squad), index)
    c.eq(f"{needle}: moat {was:.2f}\" -> {now:.2f}\"",
         (round(was, 2), round(now, 2)), (want_before, want_after))

# Units with a front-rank fighter get the ring too - an ADDED ring cannot take
# a slot away from anyone, so there is no reason to exempt them. Whether it
# helps depends on where their wide model actually stands: at the default
# pitch Meganobz close their moat, while the Boyz mob's two characters are up
# at the front edge where game/front_rank.py put them and nothing changes.
for army, needle, want_before, want_after in (
    ("orks", "Meganobz", 1.59, 0.05),
    ("orks", "Beast Snagga Boyz", 0.25, 0.05),
):
    squad = unit(army, needle)
    c.true(f"{needle} has a front-rank fighter",
           len(front_rank.front_rank_models(squad)) > 0)
    index = leader_index(squad)
    was = gap_to_nearest(squad, pack(squad, pre_fix=True), index)
    now = gap_to_nearest(squad, pack(squad), index)
    c.eq(f"{needle}: moat {was:.2f}\" -> {now:.2f}\"",
         (round(was, 2), round(now, 2)), (want_before, want_after))

# The other side of the same line, and it is the one that says the fix is
# targeted rather than a blanket tightening: a unit whose two base sizes are
# close enough that the first ring already cleared them is not touched at all.
# 0.79" + 0.56" + 0.05" = 1.40", under the 1.5" pitch.
avengers = unit("aeldari", "Dire Avengers")
c.eq("Dire Avengers carry two base sizes too",
     len({round(m.radius_in, 3) for m in avengers.models}), 2)
c.true("but they need less clearance than the pitch already gives",
       max(m.radius_in for m in avengers.models)
       + min(m.radius_in for m in avengers.models) + 0.05 < step_of(avengers))
c.eq("so their formation is byte-identical before and after",
     [(round(x, 6), round(y, 6)) for x, y in pack(avengers, pre_fix=True)],
     [(round(x, 6), round(y, 6)) for x, y in pack(avengers)])

total_before = total_after = 0.0
for army in ("necrons", "orks", "aeldari"):
    for squad in army_lists.preview_squads(army, "player2"):
        if len(squad.models) < 4:
            continue
        was = spread(squad, pack(squad, pre_fix=True))
        now = spread(squad, pack(squad))
        total_before += was
        total_after += now
c.true(f"summed over every unit of both demo armies the footprint shrinks "
       f"({total_before:.1f}\" -> {total_after:.1f}\")", total_after < total_before)


# ------------------------------------ 4. a homogeneous unit is untouched

print("--- 4. one base size: nothing changes ---")

for army, needle in (("necrons", "Canoptek Wraiths"), ("orks", "Stormboyz"),
                     ("aeldari", "Rangers"), ("necrons", "Immortals")):
    squad = unit(army, needle)
    radii = {round(m.radius_in, 3) for m in squad.models}
    c.eq(f"{needle} has one base size", len(radii), 1)
    c.eq(f"{needle}: identical slots before and after - for a homogeneous unit "
         f"the required inner radius is below the pitch anyway",
         [(round(x, 6), round(y, 6)) for x, y in pack(squad, pre_fix=True)],
         [(round(x, 6), round(y, 6)) for x, y in pack(squad)])


# ---------------------- 4b. why the pitch comes from the smallest base

print("--- 4b. the pitch's own justification, pinned ---")

# This is the decision the fix above sits on top of, and its stated reason went
# stale: it used to read "09.02's 9" span limit rejects the wide pitch at every
# facing, so the unit cannot be deployed". config.SPREAD_LIMIT_PLAYERS lifted
# that half of 09.02 for the AI, so it is now true for Player 1 only. Measured
# rather than asserted from the comment, and pinned so the next reader gets the
# qualified version.

mob = unit("orks", "Boyz 1 + Warboss + Painboy")
narrow = formation_layout.MODEL_GAP_IN
wide = 2 * max(m.radius_in for m in mob.models) + 0.1


def spread_at(squad, gap):
    slots = formation_layout.pack_positions(squad, *ORIGIN, base_angle=FACING,
                                            gap_in=gap)
    for model, (x, y) in zip(squad.models, slots):
        model.x_in, model.y_in = x, y
    return spread(squad, slots)


c.eq("the mob is the 22-model one", len(mob.models), 22)
c.eq("pitched off the smallest base it is 6.24\" across",
     round(spread_at(mob, narrow), 2), 6.24)
c.eq("pitched off the widest, 9.00\"", round(spread_at(mob, wide), 2), 9.00)

for owner, enforced, wide_verdict in (("Player 1", True, False), ("Player 2", False, True)):
    mob.owner = owner
    for model in mob.models:
        model.owner = owner
    c.eq(f"{owner}: the 9\" half of 09.02 is enforced = {enforced}",
         spread_limit_applies(mob), enforced)
    spread_at(mob, wide)
    c.eq(f"{owner}: so the WIDE pitch is "
         f"{'legal' if wide_verdict else 'rejected'}",
         not mob.check_coherency(), wide_verdict)
    spread_at(mob, narrow)
    c.true(f"{owner}: the narrow pitch is legal either way",
           not mob.check_coherency())

c.true("so the narrow pitch is not merely a rules workaround - it is 2.76\" "
       "of footprint, which is the design goal on its own (13.09 needs EVERY "
       "model in the dense area)", spread_at(mob, wide) - spread_at(mob, narrow) > 2.5)


# ------------------------------------------- 5. the fix is not free-floating

print("--- 5. wiring ---")

with open("game/formation_layout.py", encoding="utf-8") as handle:
    source = handle.read()

c.eq("pack_positions() asks for the inner radius in exactly one place",
     source.count("_inner_radius(squad.models)"), 1)
c.true("and the ring is ADDED to the grid, never swapped in for one - which "
       "is what makes it safe to ask for unconditionally",
       "radii.append(inner_radius)" in source)
c.true("ring_candidates() still defaults to the old behaviour for its other "
       "callers (model_return, unquenchable_resolve, eternal_revenant, "
       "returning_positions), which place ONE model rather than laying out a "
       "block", "inner_radius=None" in source)

default_only = formation_layout.ring_candidates(0.0, 0.0, 1.5, FACING)
explicit_none = formation_layout.ring_candidates(0.0, 0.0, 1.5, FACING,
                                                 inner_radius=None)
c.eq("omitting it and passing None mean the same thing", default_only, explicit_none)
c.true("an inner radius INSIDE the grid is ignored - otherwise every unit in "
       "the game would get a second, tighter ring it never asked for",
       formation_layout.ring_candidates(0.0, 0.0, 1.5, FACING, inner_radius=1.2)
       == default_only)
c.true("and one outside it adds exactly one ring, keeping all the originals",
       set(default_only) <= set(formation_layout.ring_candidates(
           0.0, 0.0, 1.5, FACING, inner_radius=1.7)))
c.eq("the outermost candidate is exactly as far out as it ever was - the "
     "block does not grow",
     round(max(math.dist(p, (0.0, 0.0)) for p in
               formation_layout.ring_candidates(0.0, 0.0, 1.5, FACING,
                                                inner_radius=1.7)), 4),
     round(max(math.dist(p, (0.0, 0.0)) for p in default_only), 4))

c.finish()
