"""A/B probes for "Rapid ingress und eater plague overlays ueberlappen sich".

Each probe restores ONE half of the pre-fix world at the SOURCE and has to make
its own suite red. The important ones are not the collision itself - that is a
nuisance - but the two ways this fix could fail SILENTLY:

  * a chain that never reaches its tail, so five abilities stop being offered
    at all (worse than the reported bug); and
  * a token that is read instead of taken, so they are offered twice.

Both have their own probe, and so does the strand underneath: Fire Overwatch
used to continue the chain the instant a Snap Shooting activation STARTED,
which would have dropped the same collision one link further down.

Run it ALONE: it rewrites main.py and game/overwatch.py while it runs.
"""

import io
import os
import re
import shutil
import subprocess
import sys

MAIN = "main.py"
OVERWATCH = os.path.join("game", "overwatch.py")

SUITE = "test_shooting_start_order.py"
MODAL = "test_one_modal_at_a_time.py"
HIJACK = "test_overwatch_hijack.py"


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, t):
    io.open(p, "w", encoding="utf-8", newline="").write(t)


def clear_cache():
    for root, dirs, _f in os.walk("."):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)


def run(suite):
    clear_cache()
    out = subprocess.run([sys.executable, suite], capture_output=True, text=True)
    text = out.stdout + out.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    if not match:
        return None, None, text
    return int(match.group(1)), int(match.group(2)), text


# --- (a) the offers go back where they collided -----------------------------
ARM_NEW = '''            _shooting_start_owed[0] = turn_tracker.turn_owner'''
ARM_OLD = '''            _pre_fix_squads = {t.squad for t in state.tokens if t.squad is not None}
            matter_absorption_controller.offer_at_shooting_phase(_pre_fix_squads, turn_tracker.turn_owner)
            living_lightning_controller.offer_at_shooting_phase(_pre_fix_squads, turn_tracker.turn_owner)
            eater_plague_controller.offer_at_shooting_phase(_pre_fix_squads, turn_tracker.turn_owner)
            auxiliary_cadre_controller.offer_at_start_of_shooting_phase(turn_tracker.turn_owner)
            guiding_presence_controller.offer_at_start_of_shooting_phase(turn_tracker.turn_owner)'''

# --- (b) Fire Overwatch continues the chain mid-salvo again -----------------
DEFER_NEW = '''        self._deferred_on_resolved = on_resolved
        self.stratagem_controller.use(player, self._stratagem, [squad])'''
DEFER_OLD = '''        self.stratagem_controller.use(player, self._stratagem, [squad])
        if on_resolved is not None:
            on_resolved()'''

# --- (c) the salvo that never began --------------------------------------
NEVER_NEW = '''        if getattr(self.shooting_controller, "active_squad", None) is not squad:
            self._on_shot_finished(mover)'''
NEVER_OLD = '''        pass'''

# --- (d) the deferred callback is READ, not taken --------------------------
TAKE_CB_NEW = '''        callback, self._deferred_on_resolved = self._deferred_on_resolved, None
        if callback is not None:
            callback()'''
TAKE_CB_OLD = '''        if self._deferred_on_resolved is not None:
            self._deferred_on_resolved()'''

# --- (e) the owed token is READ, not taken ---------------------------------
TAKE_TOKEN_NEW = '''        owner, _shooting_start_owed[0] = _shooting_start_owed[0], None'''
TAKE_TOKEN_OLD = '''        owner = _shooting_start_owed[0]'''

# --- (f) the safety net goes away -------------------------------------------
NET_NEW = '''        if _shooting_start_owed[0] is not None:
            owed_owner, _shooting_start_owed[0] = _shooting_start_owed[0], None
            game_log.add(
                f"{owed_owner}: the start-of-Shooting-phase abilities were not offered "
                f"this phase - the Rapid Ingress window was still open when it ended."
            )'''
NET_OLD = '''        pass'''

# --- (g) the chain loses its tail -------------------------------------------
TAIL_NEW = '''on_resolved=_take_start_of_shooting_offers'''
TAIL_OLD = '''on_resolved=None'''

# --- (h) the tail runs IN FRONT of Fire Overwatch ---------------------------
ORDER_NEW = '''                on_resolved=lambda: fire_overwatch_controller.offer(
                    mover_before, on_resolved=_take_start_of_shooting_offers),'''
ORDER_OLD = '''                on_resolved=lambda: (_take_start_of_shooting_offers(),
                                     fire_overwatch_controller.offer(mover_before)),'''


PROBES = [
    ("the five offers go back into the entering-Shooting block",
     [(MAIN, ARM_NEW, ARM_OLD)], MODAL),
    ("...and the same, against the ordering suite",
     [(MAIN, ARM_NEW, ARM_OLD)], SUITE),
    ("Fire Overwatch continues the chain the instant the salvo STARTS",
     [(OVERWATCH, DEFER_NEW, DEFER_OLD)], SUITE),
    ("a salvo that never began strands the chain for the rest of the battle",
     [(OVERWATCH, NEVER_NEW, NEVER_OLD)], SUITE),
    ("the deferred callback is read instead of taken, so it can fire twice",
     [(OVERWATCH, TAKE_CB_NEW, TAKE_CB_OLD)], SUITE),
    ("the owed token is read instead of taken",
     [(MAIN, TAKE_TOKEN_NEW, TAKE_TOKEN_OLD)], SUITE),
    ("THE SILENT ONE: the safety net is gone, so a lost chain says nothing",
     [(MAIN, NET_NEW, NET_OLD)], SUITE),
    ("the chain loses its tail, so the five are never offered at all",
     [(MAIN, TAIL_NEW, TAIL_OLD)], SUITE),
    ("...and the same, against the source guard",
     [(MAIN, TAIL_NEW, TAIL_OLD)], MODAL),
    ("the tail runs in FRONT of Fire Overwatch, i.e. mid-salvo",
     [(MAIN, ORDER_NEW, ORDER_OLD)], SUITE),
    ("THE WHOLE PRE-FIX WORLD: old order, immediate continuation, no tail",
     [(MAIN, ARM_NEW, ARM_OLD), (MAIN, TAIL_NEW, TAIL_OLD),
      (OVERWATCH, DEFER_NEW, DEFER_OLD)], SUITE),
]


baselines = {}
for suite in (SUITE, MODAL, HIJACK):
    got, total, text = run(suite)
    if got is None:
        print("BASELINE DID NOT RUN for %s:\n%s" % (suite, text[-1500:]))
        raise SystemExit(2)
    baselines[suite] = got
    print("baseline %-34s %d/%d" % (suite, got, total))
print()

bad = 0
for label, edits, suite in PROBES:
    originals = {}
    try:
        ok = True
        for path, new, old in edits:
            originals.setdefault(path, read(path))
            src = read(path)
            if src.count(new) != 1:
                print("  SKIP     %s: anchor not unique in %s (%d)"
                      % (label, path, src.count(new)))
                ok = False
                bad += 1
                break
            write(path, src.replace(new, old))
        if not ok:
            continue
        got, total, text = run(suite)
        if got is None:
            verdict, detail = "BITES", "(crashed - counts as red)"
        elif got < baselines[suite]:
            verdict, detail = "BITES", "%d/%d" % (got, total)
        else:
            verdict, detail = "NO BITE", "%d/%d - FINDING ABOUT THE TEST" % (got, total)
            bad += 1
        print("  %-8s %s: %s" % (verdict, label, detail))
        if got is not None and got < baselines[suite]:
            for line in text.splitlines():
                if line.strip().startswith("FAIL:"):
                    print("             " + line.strip()[:110])
                    break
    finally:
        for path, original in originals.items():
            write(path, original)

clear_cache()
print()
print("all probes bite" if not bad else "%d probe(s) did not bite" % bad)
raise SystemExit(1 if bad else 0)
