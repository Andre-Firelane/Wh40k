"""A/B probes for the two reports of 2026-09-08, at the SOURCE.

  1. "ich habe 2 vespiden, aber die rueckkehr in reserve wurde mir immer nur
     von einem der beiden squads angeboten" - three controllers raised one
     prompt per turn end and returned (game/per_unit_offer.py).
  2. "defend stronghold wurde mir nicht zugerechnet" - the result box was
     raised in the same advance_turn_phase() that opened the card's scoring
     prompt, freezing a score without it and burying the prompt behind itself.

Each probe restores ONE half of the pre-fix world and has to make its own
suite red. The last three restore a whole pre-fix world.
"""

import io
import os
import re
import shutil
import subprocess
import sys

AIRBORNE = os.path.join("game", "airborne_agility.py")
RIDE = os.path.join("game", "ride_the_wind.py")
CLOUD = os.path.join("game", "cloudstrider.py")
OFFER = os.path.join("game", "per_unit_offer.py")
MAIN = "main.py"

VESPID = "test_tau_kroot_and_vespid.py"
WINDRIDER = "test_aeldari_detachment_rules.py"
BAHARROTH = "test_baharroth.py"
FINAL = "test_final_round_scoring.py"


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, t):
    io.open(p, "w", encoding="utf-8", newline="").write(t)


def clear_cache():
    # The documented __pycache__ race: these probes rewrite and restore inside
    # the same second, so a stale .pyc reports the PREVIOUS run's result.
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


# The one-prompt-and-return loop each of the three used to have. Restoring it
# is a real restoration, not a stub: this is what the code said.
AIRBORNE_OLD = '''        candidates = sorted(
            (s for s in squads
             if s.owner != ending_player and s.owner not in self.auto_players),
            key=lambda s: (str(s.owner), s.name))
        for squad in candidates:
            if not self.can_use(squad):
                continue
            if self.decision_manager is None:
                return False
            self.decision_manager.request(
                squad.owner,
                (f"{squad.name}: Airborne Agility - leave the battlefield and go "
                 f"into Strategic Reserves?"),
                [("Go into Strategic Reserves", lambda s=squad: self.use(s)),
                 ("Stay on the battlefield", lambda: None)])
            return True
        return False'''

AIRBORNE_NEW = '''        candidates = sorted(
            (s for s in squads
             if s.owner != ending_player and s.owner not in self.auto_players),
            key=lambda s: (str(s.owner), s.name))
        return per_unit_offer.offer_each(
            self.decision_manager, candidates, self.can_use,
            lambda s: (f"{s.name}: Airborne Agility - leave the battlefield and go "
                       f"into Strategic Reserves?"),
            lambda s: [("Go into Strategic Reserves", lambda t=s: self.use(t)),
                       ("Stay on the battlefield", lambda: None)])'''

RIDE_NEW = '''        return per_unit_offer.offer_each(
            self.decision_manager, candidates, self.can_use,
            lambda s: ("%s: %s - pull it back into Strategic Reserves? (%d of %d left "
                       "this turn)" % (RIDE_THE_WIND_LABEL, s.name,
                                       self.remaining(), self.limit())),
            lambda s: [("Go into Strategic Reserves", lambda t=s: self.use(t)),
                       ("Stay on the battlefield", lambda: None)])'''

RIDE_OLD = '''        for squad in candidates:
            if not self.can_use(squad):
                continue
            if self.decision_manager is None:
                return False
            self.decision_manager.request(
                squad.owner,
                "%s: %s - pull it back into Strategic Reserves? (%d of %d left "
                "this turn)" % (RIDE_THE_WIND_LABEL, squad.name,
                                self.remaining(), self.limit()),
                [("Go into Strategic Reserves", lambda s=squad: self.use(s)),
                 ("Stay on the battlefield", lambda: None)])
            return True
        return False'''

CLOUD_NEW = '''        return per_unit_offer.offer_each(
            self.decision_manager, self._candidates(opponent),
            lambda s: can_withdraw(s, self.game_state),
            lambda s: f"{s.name}: {CLOUDSTRIDER_LABEL} - withdraw into Strategic Reserves?",
            lambda s: [("Withdraw", lambda t=s: self.withdraw(t)),
                       ("Stay", lambda: None)])'''

CLOUD_OLD = '''        for squad in self._candidates(opponent):
            self.decision_manager.request(
                squad.owner,
                f"{squad.name}: {CLOUDSTRIDER_LABEL} - withdraw into Strategic Reserves?",
                [("Withdraw", lambda s=squad: self.withdraw(s)), ("Stay", lambda: None)])
            return True
        return False'''

# The chain itself: keep the loop, drop the continuation. This is the subtler
# pre-fix world - one prompt per unit is REQUESTED, but only the first ever
# reaches the queue because nothing offers the rest.
CHAIN_NEW = '''        def _chain(callback):
            def _answer():
                if callback is not None:
                    callback()
                offer_each(decision_manager, rest, still_eligible,
                           prompt_for, options_for)
            return _answer'''

CHAIN_OLD = '''        def _chain(callback):
            def _answer():
                if callback is not None:
                    callback()
            return _answer'''

GATE_NEW = "if turn_tracker.battle_over and not decision_manager.is_pending:"
GATE_OLD = "if turn_tracker.battle_over:"

FRAME_NEW = "        _check_battle_end()\n\n        # `turn_tracker.started` gates the whole block"
FRAME_OLD = "        # `turn_tracker.started` gates the whole block"


PROBES = [
    ("Airborne Agility asks only the FIRST unit (THE REPORT)",
     [(AIRBORNE, AIRBORNE_NEW, AIRBORNE_OLD)], VESPID),
    ("Ride the Wind asks only the first, so its cap counter is decorative",
     [(RIDE, RIDE_NEW, RIDE_OLD)], WINDRIDER),
    ("Cloudstrider asks only the first",
     [(CLOUD, CLOUD_NEW, CLOUD_OLD)], BAHARROTH),
    ("the chain drops its continuation - Vespid",
     [(OFFER, CHAIN_NEW, CHAIN_OLD)], VESPID),
    ("the chain drops its continuation - Windrider Host",
     [(OFFER, CHAIN_NEW, CHAIN_OLD)], WINDRIDER),
    ("the chain drops its continuation - Cloudstrider",
     [(OFFER, CHAIN_NEW, CHAIN_OLD)], BAHARROTH),
    ("the result box no longer waits for an open decision (THE REPORT)",
     [(MAIN, GATE_NEW, GATE_OLD)], FINAL),
    ("the per-frame re-check is gone, so the held result never appears",
     [(MAIN, FRAME_NEW, FRAME_OLD)], FINAL),
    ("the WHOLE pre-fix battle end (gate and per-frame call)",
     [(MAIN, GATE_NEW, GATE_OLD), (MAIN, FRAME_NEW, FRAME_OLD)], FINAL),
]


baselines = {}
for suite in (VESPID, WINDRIDER, BAHARROTH, FINAL):
    got, total, text = run(suite)
    if got is None:
        print("BASELINE DID NOT RUN for %s:\n%s" % (suite, text[-1500:]))
        raise SystemExit(2)
    baselines[suite] = got
    print("baseline %-40s %d/%d" % (suite, got, total))
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
                print("  SKIP     %s: anchor not unique in %s" % (label, path))
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
