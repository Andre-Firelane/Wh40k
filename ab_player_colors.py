"""A/B probes for the constant player colours.

Each probe restores ONE piece of the pre-fix world AT THE SOURCE, runs the
suite, and puts it back. A probe that does not break its own suite is a finding
about the TEST (CLAUDE.md error class 24), not a licence to move on.

The first probe is the whole pre-fix world: the rim colour keyed on the active
player again. If test_player_colors.py survives that, it is not testing this
change.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
RENDERER = os.path.join(ROOT, "game", "renderer.py")
SUITE = os.path.join(ROOT, "test_player_colors.py")

BASE = 23  # checks in test_player_colors.py when everything is wired


def run():
    """(passed, total) from one run of the suite."""
    out = subprocess.run([sys.executable, SUITE], capture_output=True, text=True,
                         cwd=ROOT).stdout
    for line in out.splitlines():
        if "checks passed" in line:
            got, total = line.strip().split()[0].split("/")
            return int(got), int(total)
    return -1, -1


def probe(label, old, new, path=RENDERER):
    src = open(path, encoding="utf-8").read()
    if src.count(old) != 1:
        print(f"  SKIP {label}: anchor found {src.count(old)}x")
        return
    open(path, "w", encoding="utf-8").write(src.replace(old, new))
    try:
        # __pycache__ is cleared between runs: these probes write and restore
        # inside the same second, and a stale .pyc has reported the PREVIOUS
        # pass's result here before (CLAUDE.md error class 19).
        for root, dirs, _f in os.walk(ROOT):
            for d in list(dirs):
                if d == "__pycache__":
                    import shutil
                    shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                    dirs.remove(d)
        got, total = run()
    finally:
        open(path, "w", encoding="utf-8").write(src)
    verdict = "BITES" if got < BASE else "*** DID NOT BITE ***"
    print(f"  {verdict:22} {got}/{total}  {label}")


print(f"baseline: {run()[0]}/{run()[1]}  (want {BASE})")

# 1. The WHOLE pre-fix world: the old body, keyed on the active player, with a
#    caller that supplies one. Restoring only the SIGNATURE would leave the
#    owner lookup in place and change no pixel - a half probe, which is exactly
#    how this repo has been told twice that a bug never existed (error class
#    16). "Player 2" stands in for the moment the focus is on the defender,
#    which is the frame the report is about.
probe(
    "the whole pre-fix world (colour follows the active player)",
    """        if token.squad is None:
            return token.color
        return TOKEN_TEAM_COLORS.get(token.squad.owner, token.color)""",
    """        active_player = "Player 2"   # the defender is deciding this frame
        if active_player is None or token.squad is None:
            return token.color
        return OWN_ARMY_COLOR if token.squad.owner == active_player else ENEMY_ARMY_COLOR""",
)

# 2. The table alone, with both players mapped to one colour - the shape a
#    "constant" fix could take that says nothing.
probe(
    "both players share one colour",
    '''TOKEN_TEAM_COLORS = {
    "Player 1": OWN_ARMY_COLOR,
    "Player 2": ENEMY_ARMY_COLOR,
}''',
    '''TOKEN_TEAM_COLORS = {
    "Player 1": OWN_ARMY_COLOR,
    "Player 2": OWN_ARMY_COLOR,
}''',
)

# 3. The two colours swapped. The suite anchors on the two SPOKEN words, so
#    reading its own table cannot save it here.
probe(
    "the two colours swapped",
    '''TOKEN_TEAM_COLORS = {
    "Player 1": OWN_ARMY_COLOR,
    "Player 2": ENEMY_ARMY_COLOR,
}''',
    '''TOKEN_TEAM_COLORS = {
    "Player 1": ENEMY_ARMY_COLOR,
    "Player 2": OWN_ARMY_COLOR,
}''',
)

# 4. The fallback swallowing a known owner - a rim that quietly stops being a
#    team colour at all.
probe(
    "the table is never consulted",
    "        return TOKEN_TEAM_COLORS.get(token.squad.owner, token.color)",
    "        return token.color",
)

# 5. main.py handing the renderer an active player again. Nothing reads it, so
#    only a source check can see this - and it is the line that would come back
#    first if someone re-added the parameter.
probe(
    "main.py passes an active player again",
    """            board_surface, board, state.tokens, state.obstacles,
            deployment_zones=state.deployment_zones,""",
    """            board_surface, board, state.tokens, state.obstacles, turn_tracker.active_player,
            deployment_zones=state.deployment_zones,""",
    path=os.path.join(ROOT, "main.py"),
)
