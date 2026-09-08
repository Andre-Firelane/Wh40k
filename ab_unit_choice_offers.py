"""A/B probes for the 2026-09-08 report, at the SOURCE.

  "cost of victory wird mir pauschal angeboten, aber ich habe 3 guardian
   squads. ich kann nicht waehlen welchen squad zurueck in reserve schicken
   will. es muss auf dem feld angeklickt werden."

Four Stratagems printed "TARGET: One <X> unit from your army" and each looped
over the eligible units, raised a prompt about the FIRST, and returned. Each
probe restores ONE of those pre-fix loops, byte for byte as the code said it,
and has to make its suite red. The last three attack the shared helper and the
tagging itself, which no single-controller probe can reach.

The four suites that own these rules are driven as well as the new one: a fix
that only the new file notices is exactly the drift this repo consolidates.
"""

import io
import os
import re
import shutil
import subprocess
import sys

COV = os.path.join("game", "guardian_cost_of_victory.py")
WWT = os.path.join("game", "warhost_webway_tunnel.py")
SKY = os.path.join("game", "skyborne_sanctuary.py")
OVF = os.path.join("game", "windrider_overflight.py")
HELPER = os.path.join("game", "unit_choice_offer.py")

CHOICE = "test_unit_choice_offers.py"
WIRING = "test_event_chain_wiring.py"


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


# ---------------------------------------------------------------- Cost of
# Victory. The pre-fix loop, exactly as it stood.
COV_NEW = '''        for player in sorted({s.owner for s in squads if s.owner != ending_player},
                             key=str):
            self._window.arm(player)
            candidates = [s for s in sorted(squads, key=lambda s: s.name)
                          if s.owner == player and self.can_use(s)]
            if unit_choice_offer.offer_one_of(
                    self.decision_manager, player, candidates,
                    "%s (%d CP): pull which unit into Strategic Reserves, "
                    "bringing back its destroyed models?"
                    % (COST_OF_VICTORY_NAME, COST_OF_VICTORY_CP),
                    self.use, auto_players=self.auto_players,
                    is_stratagem=True):
                return True
            self._window.close()       # nothing offered - and no AI path
        return False'''

COV_OLD = '''        for squad in sorted((s for s in squads if s.owner != ending_player),
                            key=lambda s: (str(s.owner), s.name)):
            self._window.arm(squad.owner)
            if not self.can_use(squad):
                self._window.close()
                continue
            if squad.owner in self.auto_players or self.decision_manager is None:
                self._window.close()
                return False           # no AI path
            self.decision_manager.request(
                squad.owner,
                "%s (%d CP): pull %s into Strategic Reserves and bring back its "
                "destroyed models?"
                % (COST_OF_VICTORY_NAME, COST_OF_VICTORY_CP, squad.name),
                [("Use (%d CP)" % COST_OF_VICTORY_CP, (lambda s=squad: self.use(s))),
                 ("Decline", lambda: None)],
                is_stratagem=True,
            )
            return True
        return False'''

# ---------------------------------------------------------------- Webway
WWT_NEW = '''        for player in sorted({s.owner for s in squads if s.owner != ending_player},
                             key=str):
            self._window.arm(player)
            candidates = [s for s in sorted(squads, key=lambda s: s.name)
                          if s.owner == player and self.can_use(s)]
            if unit_choice_offer.offer_one_of(
                    self.decision_manager, player, candidates,
                    "%s (%d CP): pull which unit off the battlefield and into "
                    "Strategic Reserves?" % (WEBWAY_TUNNEL_NAME, WEBWAY_TUNNEL_CP),
                    self.use, auto_players=self.auto_players,
                    is_stratagem=True):
                return True
            self._window.close()       # nothing offered - and no AI path
        return False'''

WWT_OLD = '''        for squad in sorted((s for s in squads if s.owner != ending_player),
                            key=lambda s: (str(s.owner), s.name)):
            self._window.arm(squad.owner)
            if not self.can_use(squad):
                self._window.close()
                continue
            if squad.owner in self.auto_players or self.decision_manager is None:
                self._window.close()
                return False           # no AI path
            self.decision_manager.request(
                squad.owner,
                "%s (%d CP): pull %s off the battlefield and into Strategic "
                "Reserves?" % (WEBWAY_TUNNEL_NAME, WEBWAY_TUNNEL_CP, squad.name),
                [("Use (%d CP)" % WEBWAY_TUNNEL_CP, (lambda s=squad: self.use(s))),
                 ("Decline", lambda: None)],
                is_stratagem=True,
            )
            return True
        return False'''

# ---------------------------------------------------------------- Overflight
OVF_NEW = '''        for player in sorted({s.owner for s in candidates}, key=str):
            self._window.arm(player)
            eligible = [s for s in sorted(candidates, key=lambda s: s.name)
                        if s.owner == player and self.can_use(s)]
            if unit_choice_offer.offer_one_of(
                    self.decision_manager, player, eligible,
                    \'%s (%d CP): which unit that destroyed an enemy unit this \'
                    \'phase makes a Normal move of up to %g"?\'
                    % (OVERFLIGHT_NAME, OVERFLIGHT_CP, OVERFLIGHT_MOVE_IN),
                    self.use, auto_players=self.auto_players,
                    is_stratagem=True):
                return True
            self._window.close()       # nothing offered - and no AI path
        return False'''

OVF_OLD = '''        for squad in sorted(candidates, key=lambda s: (str(s.owner), s.name)):
            self._window.arm(squad.owner)
            if not self.can_use(squad):
                self._window.close()
                continue
            if squad.owner in self.auto_players or self.decision_manager is None:
                self._window.close()
                return False           # no AI path
            self.decision_manager.request(
                squad.owner,
                \'%s (%d CP): %s destroyed an enemy unit this phase - make a \'
                \'Normal move of up to %g"?\'
                % (OVERFLIGHT_NAME, OVERFLIGHT_CP, squad.name, OVERFLIGHT_MOVE_IN),
                [("Use (%d CP)" % OVERFLIGHT_CP, (lambda s=squad: self.use(s))),
                 ("Decline", lambda: None)],
                is_stratagem=True,
            )
            return True
        return False'''

# ---------------------------------------------------------------- Skyborne
SKY_NEW = '''        for player in sorted({s.owner for s in squads}, key=str):
            self._window.arm(player)
            candidates = [s for s in sorted(squads, key=lambda s: s.name)
                          if s.owner == player and self.can_use(s)]
            if unit_choice_offer.offer_one_of(
                    self.decision_manager, player, candidates,
                    "%s (%d CP): which unit embarks within a TRANSPORT?"
                    % (SKYBORNE_SANCTUARY_NAME, SKYBORNE_SANCTUARY_CP),
                    self._choose_transport, auto_players=self.auto_players,
                    is_stratagem=True):
                return True
            self._window.close()       # nothing offered - and no AI path
        return False'''

SKY_OLD = '''        for squad in sorted(squads, key=lambda s: (str(s.owner), s.name)):
            self._window.arm(squad.owner)
            if not self.can_use(squad):
                self._window.close()
                continue
            if squad.owner in self.auto_players or self.decision_manager is None:
                self._window.close()
                return False           # no AI path
            transport = self.transports_for(squad)[0]
            self.decision_manager.request(
                squad.owner,
                "%s (%d CP): embark %s within %s?"
                % (SKYBORNE_SANCTUARY_NAME, SKYBORNE_SANCTUARY_CP, squad.name,
                   transport.squad.name),
                [("Use (%d CP)" % SKYBORNE_SANCTUARY_CP,
                  (lambda s=squad, t=transport: self.use(s, t))),
                 ("Decline", lambda: None)],
                is_stratagem=True,
            )
            return True
        return False'''

# Skyborne's second step: take the "only ask when it is a question" branch out,
# so a single legal transport raises a prompt that has one answer.
SKY_STEP2_NEW = "        if len(transports) == 1 or self.decision_manager is None:"
SKY_STEP2_OLD = "        if self.decision_manager is None:"

# ------------------------------------------------------- the helper itself
# 1. Drop the squad TAG. The prompt still lists every candidate by name, so
#    every count in the suite holds - and unit_pick.pending() returns None, so
#    it is a list again and can never be clicked on the board. This is the
#    half of the report that a count-only test cannot see.
TAG_NEW = ('        [(label(squad), (lambda s=squad: action(s)), squad) '
           'for squad in candidates]')
TAG_OLD = ('        [(label(squad), (lambda s=squad: action(s))) '
           'for squad in candidates]')

# 2. Offer only the first candidate - the report, expressed inside the helper
#    so it hits all four controllers at once.
FIRST_NEW = "    if not candidates or decision_manager is None:"
FIRST_OLD = ("    candidates = list(candidates)[:1]\n"
             "    if not candidates or decision_manager is None:")

# 3. Late binding: the classic loop-variable capture. Every option resolves to
#    the LAST candidate, which is why "clicking the SECOND resolves the SECOND"
#    is the load-bearing check rather than an option count.
LATE_NEW = "        [(label(squad), (lambda s=squad: action(s)), squad) for squad in candidates]"
LATE_OLD = "        [(label(squad), (lambda: action(squad)), squad) for squad in candidates]"


# The guard resolves a bare NAME argument against the function's assignments.
# Without it neocapacitor_shields.py - which builds `options = [...]` and then
# passes it - reads as untagged, and the guard fires on a prompt that is in
# fact clickable. This probe is what keeps that fix honest.
RESOLVE_NEW = "        if isinstance(arg, ast.Name):"
RESOLVE_OLD = "        if False:"

PROBES = [
    ("Cost of Victory offers one unit, yes/no (THE REPORT)",
     [(COV, COV_NEW, COV_OLD)], CHOICE),
    # The four owning suites CANNOT see this - each stages one eligible
    # squad, where the broken and the correct shape are identical. Measured:
    # both were tried as probe targets and reported NO BITE. The source guard
    # is what covers the class, so that is what the probe drives.
    ("...and the source guard sees it too",
     [(COV, COV_NEW, COV_OLD)], WIRING),
    ("Webway Tunnel offers one unit, yes/no",
     [(WWT, WWT_NEW, WWT_OLD)], CHOICE),
    ("Overflight offers one unit, yes/no",
     [(OVF, OVF_NEW, OVF_OLD)], CHOICE),
    ("Skyborne Sanctuary offers one unit and picks its transport silently",
     [(SKY, SKY_NEW, SKY_OLD)], CHOICE),
    ("Skyborne asks which transport even when there is only one",
     [(SKY, SKY_STEP2_NEW, SKY_STEP2_OLD)], CHOICE),
    ("the options lose their squad tag - a list again, never clickable",
     [(HELPER, TAG_NEW, TAG_OLD)], CHOICE),
    ("the helper offers only the first candidate - all four at once",
     [(HELPER, FIRST_NEW, FIRST_OLD)], CHOICE),
    ("late binding: every option resolves to the LAST candidate",
     [(HELPER, LATE_NEW, LATE_OLD)], CHOICE),
    ("the WHOLE pre-fix world - all four loops back",
     [(COV, COV_NEW, COV_OLD), (WWT, WWT_NEW, WWT_OLD),
      (OVF, OVF_NEW, OVF_OLD), (SKY, SKY_NEW, SKY_OLD)], CHOICE),
    ("...and the source guard names every one of the four",
     [(COV, COV_NEW, COV_OLD), (WWT, WWT_NEW, WWT_OLD),
      (OVF, OVF_NEW, OVF_OLD), (SKY, SKY_NEW, SKY_OLD)], WIRING),
    ("the guard's local-resolution goes, and a clickable prompt reads untagged",
     [(WIRING, RESOLVE_NEW, RESOLVE_OLD)], WIRING),
]


baselines = {}
for suite in (CHOICE, WIRING):
    got, total, text = run(suite)
    if got is None:
        print("BASELINE DID NOT RUN for %s:\n%s" % (suite, text[-1500:]))
        raise SystemExit(2)
    baselines[suite] = got
    print("baseline %-42s %d/%d" % (suite, got, total))
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
        print("  %-8s %s [%s]: %s" % (verdict, label, suite, detail))
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
