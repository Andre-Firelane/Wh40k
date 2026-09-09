"""A/B probes for map 4 and the territory rule it needed.

Each restores ONE piece of the pre-change world AT THE SOURCE and re-runs the
suite it should break. A probe that does not bite is a finding about the TEST
(Fehlerklasse 24), not an all-clear.

TWO suites, because the change spans two files: the map itself
(test_map4_sundered.py) and the cross-map territory rule
(test_deployment_shapes.py), whose section 6 is where a fourth board is meant
to inherit its checks for free.
"""

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MAP4 = os.path.join(ROOT, "test_map4_sundered.py")
SHAPES = os.path.join(ROOT, "test_deployment_shapes.py")

G = lambda *p: os.path.join(ROOT, "game", *p)

MAPS_PY = G("maps.py")
CONTEXT_PY = G("mission_context.py")


def clear_cache():
    # The probes rewrite and restore a module inside the same second, so a
    # stale .pyc would make the NEXT run report the previous run's failures -
    # the documented __pycache__ race (Fehlerklasse 19).
    for root, dirs, _f in os.walk(ROOT):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                dirs.remove(d)


def run(suite):
    out = subprocess.run([sys.executable, suite], capture_output=True, text=True,
                         cwd=ROOT).stdout
    for line in out.splitlines():
        if "checks passed" in line:
            got, total = line.strip().split()[0].split("/")
            return int(got), int(total)
    return -1, -1


clear_cache()
BASE = {MAP4: run(MAP4)[0], SHAPES: run(SHAPES)[0]}
assert BASE[MAP4] > 0 and BASE[SHAPES] > 0, "baseline run failed - fix that first"
print("baseline: map4 %d, deployment_shapes %d" % (BASE[MAP4], BASE[SHAPES]))
print()


def probe(label, path, old, new, suites=(MAP4,)):
    src = open(path, encoding="utf-8").read()
    if src.count(old) != 1:
        print(f"  SKIP {label}: anchor found {src.count(old)}x")
        return
    open(path, "w", encoding="utf-8").write(src.replace(old, new, 1))
    try:
        clear_cache()
        results = [(s, run(s)) for s in suites]
    finally:
        open(path, "w", encoding="utf-8").write(src)
    # -1 means the suite CRASHED rather than going red, which is a finding
    # about the SUITE and not a passing probe (this repo's nineteen-times
    # lesson). It is reported as its own outcome so it cannot be read as a
    # bite.
    crashed = any(got < 0 for _s, (got, _t) in results)
    bites = (not crashed) and any(got < BASE[s] for s, (got, _t) in results)
    shown = "  ".join("%s %d/%d" % (os.path.basename(s)[5:-3], g, t) for s, (g, t) in results)
    verdict = "*** SUITE CRASHED ***" if crashed else ("BITES" if bites else "*** DID NOT BITE ***")
    print(f"  {verdict:22} {shown}  {label}")


# --------------------------------------------------------------------------
# THE TERRITORY RULE - the half the user actually asked about.
# --------------------------------------------------------------------------

# 1. THE WHOLE PRE-CHANGE WORLD: compare the two zone CENTRES, which is what
#    in_own_territory() did before map 4 existed. On a banded map that is the
#    same line; on two parallel diagonals it is fourteen degrees out.
probe(
    "the territory split goes back to comparing zone CENTRES",
    CONTEXT_PY,
    """    return (mine[0].distance_to_point(x_in, y_in)
            <= theirs[0].distance_to_point(x_in, y_in))""",
    """    my_cx, my_cy = _zone_centre(mine[0])
    their_cx, their_cy = _zone_centre(theirs[0])
    return ((x_in - my_cx) ** 2 + (y_in - my_cy) ** 2
            <= (x_in - their_cx) ** 2 + (y_in - their_cy) ** 2)""",
    suites=(MAP4, SHAPES))

# 2. The comparison inverted. A rule that answers "nearer THEIR zone" is still
#    a parallel midline - it is just the wrong side of it - so the section
#    that only checks the LINE would pass and the ones that name a side must
#    not.
probe(
    "the two zones swap sides",
    CONTEXT_PY,
    """    return (mine[0].distance_to_point(x_in, y_in)
            <= theirs[0].distance_to_point(x_in, y_in))""",
    """    return (theirs[0].distance_to_point(x_in, y_in)
            <= mine[0].distance_to_point(x_in, y_in))""",
    suites=(MAP4, SHAPES))

# 3. Distance measured to the zone's BOUNDING BOX rather than to the zone.
#    The plausible shortcut, and on a diagonal zone the box is the whole board
#    - so every point reports 0 and everything belongs to everybody.
probe(
    "distance measured to the zone's bounding box instead of its shape",
    CONTEXT_PY,
    """    return (mine[0].distance_to_point(x_in, y_in)
            <= theirs[0].distance_to_point(x_in, y_in))""",
    """    def _box_distance(zone):
        bx0, by0, bx1, by1 = zone.bounding_box()
        return max(bx0 - x_in, 0.0, x_in - bx1) + max(by0 - y_in, 0.0, y_in - by1)
    return _box_distance(mine[0]) <= _box_distance(theirs[0])""",
    suites=(MAP4, SHAPES))


# --------------------------------------------------------------------------
# THE ZONES - the "schraege deployment zones" half.
# --------------------------------------------------------------------------

# 4. The two edges stop being PARALLEL: Player 2's runs to the opposite
#    corner instead of to the mirrored midpoint. Both zones are still
#    triangles cut off by a diagonal, and both still hold an army - so
#    anything that only checks "the zones are slanted" survives this.
probe(
    "Player 2's edge is no longer parallel to Player 1's",
    MAPS_PY,
    'MAP4_P2_EDGE = (30.0, 60.0)     # (30,0) -> (60,44)',
    'MAP4_P2_EDGE = (20.0, 60.0)     # PROBE: not parallel any more')

# 5. The board-edge half-planes dropped from the zone shape. The zone still
#    answers contains_point() correctly - only its BOUNDING BOX goes away,
#    and with it every consumer that SAMPLES the zone. This is the failure
#    map 3 found with a smoke run and no suite.
probe(
    "the zone loses the four board-edge half-planes that bound it",
    MAPS_PY,
    """        shapes.HalfPlane.through(x0, 0.0, x1, MAP4_HEIGHT_IN, inside_x, inside_y),
        shapes.HalfPlane(1.0, 0.0, 0.0),
        shapes.HalfPlane(-1.0, 0.0, -MAP4_WIDTH_IN),
        shapes.HalfPlane(0.0, 1.0, 0.0),
        shapes.HalfPlane(0.0, -1.0, -MAP4_HEIGHT_IN),""",
    """        shapes.HalfPlane.through(x0, 0.0, x1, MAP4_HEIGHT_IN, inside_x, inside_y),""")

# 6. The two owners swapped, so Player 2 no longer keeps the low-y corner -
#    the convention every other map holds and that lets the rest of the scene
#    stay ignorant of which board is running.
probe(
    "Player 2 stops keeping the low-y corner",
    MAPS_PY,
    """        ("Player 2", _map4_zone(MAP4_P2_EDGE, MAP4_WIDTH_IN, 0.0)),   # high x, low y
        ("Player 1", _map4_zone(MAP4_P1_EDGE, 0.0, MAP4_HEIGHT_IN)),  # low x, high y""",
    """        ("Player 1", _map4_zone(MAP4_P2_EDGE, MAP4_WIDTH_IN, 0.0)),   # PROBE: swapped
        ("Player 2", _map4_zone(MAP4_P1_EDGE, 0.0, MAP4_HEIGHT_IN)),  # PROBE: swapped""",
    suites=(MAP4, SHAPES))

# 7. The annotation believed over the construction: the band narrowed to the
#    24.25" the art labels. Every zone check that only asks "is it a
#    triangle" survives; the ones that measure the construction must not.
probe(
    "the drawn 24.25in label believed over the measured construction",
    MAPS_PY,
    'MAP4_P1_EDGE = (0.0, 30.0)      # (0,0) -> (30,44)',
    'MAP4_P1_EDGE = (0.65, 30.65)    # PROBE: band squeezed to the 24.25in label')


# --------------------------------------------------------------------------
# THE TERRAIN
# --------------------------------------------------------------------------

# 8. THE ANGLE SIGN. The measurement that settled it: +55 covers 92.1% of the
#    drawn piece, -55 only 62.0%. Flipping it leaves a board that still has
#    eight rotated pieces at the same magnitudes and still mirrors cleanly -
#    which is why the sign needs its own line.
probe(
    "the rotated ruins take a NEGATIVE angle, as an unmeasured guess would",
    MAPS_PY,
    "both(rubble_ruin, 46.80, 33.29, 11.01, 6.78, angle_deg=55.0)",
    "both(rubble_ruin, 46.80, 33.29, 11.01, 6.78, angle_deg=-55.0)")

# 9. The percentile fit's raw container position, i.e. the seam left open. It
#    is 0.38" - a sliver nobody chose to leave, and exactly the width the fit
#    trimmed off the pair.
probe(
    "the diagonal stack's seam back on the raw percentile fit",
    MAPS_PY,
    "both(barricade, 11.15, 18.75, 6.71, 2.05, angle_deg=55.0)",
    "both(barricade, 10.93, 18.43, 6.71, 2.05, angle_deg=55.0)")

# 10. The same for the other seam, the braced bar beside the rubble slab.
probe(
    "the braced bar back on its raw measured x, reopening its seam",
    MAPS_PY,
    "both(barricade, 34.96, 36.92, 2.08, 5.65)",
    "both(barricade, 35.14, 36.92, 2.08, 5.65)")

# 11. THE CONTROL for the two above, and the reason they are not just "shove
#     everything together": a pair the art leaves open, closed anyway. If
#     nothing bites here then the seam checks would pass on a board that
#     glued every neighbour.
probe(
    "a pair the art leaves OPEN is glued shut as well",
    MAPS_PY,
    "both(barricade, 21.50, 34.92, 9.49, 2.82, angle_deg=63.0)",
    "both(barricade, 15.30, 24.20, 9.49, 2.82, angle_deg=63.0)")

# 12. The east container fitted independently instead of mirrored. That fit
#     is what the art gives when a dimension guide line severs the piece's
#     tip - 0.93" shorter and 4 degrees off - and it is why the complete
#     flank is the one that is measured.
probe(
    "the east container takes its own severed fit instead of the mirror",
    MAPS_PY,
    """    both(barricade, 11.15, 18.75, 6.71, 2.05, angle_deg=55.0)""",
    """    state.add_terrain_area(barricade(11.15, 18.75, 6.71, 2.05, angle_deg=55.0))
    state.add_terrain_area(barricade(48.85, 25.25, 5.78, 2.05, angle_deg=59.0))""")

# 13. The central ruin given l_walls()' L instead of ruin()'s two opposite
#     corner Ls. It is ON the board centre, so "the two sides nearest the
#     centre" has no answer and l_walls() falls back to an arbitrary corner -
#     which makes the one piece that is its own mirror asymmetric.
probe(
    "the central ruin takes an L of walls, breaking its own mirror symmetry",
    MAPS_PY,
    """    centre_ruin = state.add_terrain_area(
        ruin(x_in=30.00, y_in=22.00, width_in=11.05, height_in=9.62,
             corners=("sw", "ne")))""",
    """    centre_ruin = state.add_terrain_area(rubble_ruin(30.00, 22.00, 11.05, 9.62))""")

# 14. All four corner Ls built. The walls stay symmetric, so only the check
#     that counts them can see it - and it matters because it walls the
#     middle objective in on all four sides.
probe(
    "the central ruin keeps all four corner Ls",
    MAPS_PY,
    """             corners=("sw", "ne")))""",
    """             ))""")


# --------------------------------------------------------------------------
# THE OBJECTIVES
# --------------------------------------------------------------------------

# 15. The rotated ruins back where a 1" nudge outward puts a corner inside a
#     deployment zone. Their tightest corner clears by 1.41", so this is the
#     margin the board really has - and the cross-map invariant in
#     test_deployment_shapes.py section 9 has to see it too.
probe(
    "a rotated ruin nudged until a corner reaches into a deployment zone",
    MAPS_PY,
    "both(rubble_ruin, 46.80, 33.29, 11.01, 6.78, angle_deg=55.0)",
    "both(rubble_ruin, 48.80, 32.29, 11.01, 6.78, angle_deg=55.0)",
    suites=(MAP4, SHAPES))

# 16. The two compass names swapped. Both objectives still exist, still sit
#     in a mirror pair, and are still No Man's Land - only the names point
#     the wrong way, which is worse than no name at all.
probe(
    "the two compass names point the wrong way",
    MAPS_PY,
    """    state.add_objective(se_ruin, name="Objective Southeast")
    state.add_objective(nw_ruin, name="Objective Northwest")""",
    """    state.add_objective(se_ruin, name="Objective Northwest")
    state.add_objective(nw_ruin, name="Objective Southeast")""")

# 17. The central objective dropped. The board still has four objectives in
#     two mirror pairs and still passes every home/No-Man's-Land test - it
#     just has nothing for Secure Asset or Unstoppable Force to read.
probe(
    "the central objective is never registered",
    MAPS_PY,
    """    state.add_objective(centre_ruin, name="Central Objective")""",
    """    pass  # PROBE: no central objective""")
