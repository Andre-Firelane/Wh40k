"""A/B probes for the AI/human switch (stage 0).

Each probe restores ONE piece of the pre-change world AT THE SOURCE, runs the
suite, and puts it back. A probe that does not bite is a finding about the TEST
(CLAUDE.md Fehlerklasse 24), not a licence to move on.

Probe 1 is the whole pre-change world - the literal back at a call site. If
test_ai_mode.py survives that, it is not testing this change.
"""

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(ROOT, "main.py")
DEP = os.path.join(ROOT, "ai", "deployment_ai.py")
CONFIG = os.path.join(ROOT, "game", "config.py")
SUITE = os.path.join(ROOT, "test_ai_mode.py")

BASE = 27


def clear_cache():
    # These probes write and restore inside the same second; a stale .pyc has
    # reported the previous pass's result here before (Fehlerklasse 19).
    for root, dirs, _f in os.walk(ROOT):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                dirs.remove(d)


def run():
    out = subprocess.run([sys.executable, SUITE], capture_output=True, text=True,
                         cwd=ROOT).stdout
    for line in out.splitlines():
        if "checks passed" in line:
            got, total = line.strip().split()[0].split("/")
            return int(got), int(total)
    return -1, -1


def probe(label, old, new, path=MAIN):
    src = open(path, encoding="utf-8").read()
    if src.count(old) < 1:
        print(f"  SKIP {label}: anchor not found")
        return
    open(path, "w", encoding="utf-8").write(src.replace(old, new, 1))
    try:
        clear_cache()
        got, total = run()
    finally:
        open(path, "w", encoding="utf-8").write(src)
    print(f"  {'BITES' if got < BASE else '*** DID NOT BITE ***':22} {got}/{total}  {label}")


clear_cache()
print(f"baseline: {run()[0]}/{BASE}")

# 1. THE WHOLE PRE-CHANGE WORLD at one site: the literal is back, so that
#    controller no longer reads the shared fact.
probe(
    "the literal ('Player 2',) is back at a call site",
    "auto_players=ai_players",
    'auto_players=("Player 2",)',
)

# 2. One of the seven that USED to be unwired goes unwired again. This is the
#    class that cost real API calls, and only a call-expression check sees it.
probe(
    "a controller that reads auto_players is not handed it",
    """            for m in squad.models if not m.is_dead()),
        decision_manager=decision_manager, game_log=game_log,
        auto_players=ai_players,
    )""",
    """            for m in squad.models if not m.is_dead()),
        decision_manager=decision_manager, game_log=game_log,
    )""",
)

# 3. Scouts goes back to its own inverse literal - two lists for one fact.
probe(
    "scouts keeps a second list of its own",
    "            human_players=human_players,",
    '            human_players=("Player 1",),',
)

# 4. The agent is no longer told which side it plays, so the call and the
#    controllers could disagree about who is automatic.
probe(
    "the agent is not told which side it plays",
    "            player=ai_players[0],",
    "",
)

# 5. Construction order (Fehlerklasse 23): the binding moves BELOW its first
#    use. Green in every suite, UnboundLocalError on the first real start -
#    which has happened three times in this repo.
probe(
    "ai_players is bound after it is first used",
    """    ai_players = tuple(p for p in sorted(armies) if p in config.AI_PLAYERS)
    human_players = tuple(p for p in sorted(armies) if p not in ai_players)
""",
    "",
)

# 6. The empty-AI guard removed: ai_players[0] would raise the moment somebody
#    sets config.AI_PLAYERS = (), which this change made reachable.
probe(
    "run_ai_action() no longer guards an empty AI side",
    """        nonlocal last_shown_turn_plan
        if not ai_players:
            return""",
    "        nonlocal last_shown_turn_plan",
)

# 7. deployment_ai's default goes back to ("Player 2",) - so a caller that
#    forgets it silently resolves a HUMAN's Scouts move.
probe(
    "resolve_scouts defaults to the AI again",
    "                   objectives=(), game_log=None, ai_players=()):",
    '                   objectives=(), game_log=None, ai_players=("Player 2",)):',
    path=DEP,
)

# 8. The fact itself is removed from config, so there is nowhere central to
#    change it.
probe(
    "config.AI_PLAYERS is gone",
    'AI_PLAYERS = ("Player 2",)',
    'AI_PLAYERS_REMOVED = ("Player 2",)',
    path=CONFIG,
)
