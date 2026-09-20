"""A/B probes for the 2026-09 Ork vehicles (stage E3d): High-speed Carnage, Deff
from Above, Dread 'Ard / Mobile Fortress, Damaged 6, Aerial Manoover, Pilin' Out,
the transport lines, the AI's two policies, the matchup hint and main.py's wiring.

Each probe restores one piece of a plausible broken world AT THE SOURCE, runs the
suite(s) that are supposed to catch it, and puts the file back byte for byte. A
probe that does NOT turn its suite red is a finding about the TEST; a probe that
makes the suite CRASH or HANG is a finding too. Either way this file exits
non-zero.

EXCLUSIVE. This rewrites source files while it runs. No suite, measurement, edit
or commit may run beside it. Every replacement carries the marker AB-PROBE, so
after a run

    git grep -n --untracked "AB-PROBE" -- . ":!ab_*.py" ":!CLAUDE*.md" ":!docs/*"

must come back empty. --untracked is not optional here: this stage's modules
were new files, and a killed run left a probe in game/aerial_manoover.py that
the plain `git grep` walked past.

The driver also hashes every probed file before the first
probe and after the last, and fails if any differs. Every suite run has a
timeout - a probe that hangs a suite is reported, not waited on.

`--check` only verifies that every anchor is unique and the marker is absent,
writing nothing - safe to run beside anything. `--only SUBSTRING` re-runs the
probes whose label contains it.
"""

import hashlib
import io
import os
import re
import shutil
import subprocess
import sys

NL = chr(10)
MARK = "  # AB-PROBE"
TIMEOUT_S = 300

TV = "test_ork_vehicles.py"
TP = "test_target_priority.py"
WIRING = "test_event_chain_wiring.py"

HSC = os.path.join("game", "high_speed_carnage.py")
DFA = os.path.join("game", "deff_from_above.py")
DR = os.path.join("game", "damage_reduction.py")
DRES = os.path.join("game", "damage_resolution.py")
AM = os.path.join("game", "aerial_manoover.py")
PO = os.path.join("game", "pilin_out.py")
TR = os.path.join("game", "transport.py")
UN = os.path.join("game", "units.py")
FI = os.path.join("game", "fight.py")
SH = os.path.join("game", "shooting.py")
AG = os.path.join("ai", "agent_driver.py")
MAIN = "main.py"


def read(path):
    return io.open(path, encoding="utf-8", newline="").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def digest(path):
    return hashlib.sha1(read(path).encode("utf-8")).hexdigest()


def run(suite):
    """(passed, total, text); passed is None for a crash and "HANG" for a timeout."""
    for root, dirs, _files in os.walk("."):
        for name in list(dirs):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)
    try:
        out = subprocess.run([sys.executable, suite], capture_output=True, text=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return "HANG", None, ""
    text = out.stdout + out.stderr
    match = re.search(r"(\d+)/(\d+) checks passed", text)
    return (int(match.group(1)), int(match.group(2)), text) if match else (None, None, text)


# (label, [(path, anchor, replacement)], suites)
PROBES = [
    # ---------------------------------------------------- High-speed Carnage
    ("High-speed Carnage: no +1 S",
     [(HSC, "    boosted.strength = weapon.strength + HIGH_SPEED_CARNAGE_BONUS",
       "    boosted.strength = weapon.strength" + MARK)], (TV,)),
    ("High-speed Carnage: no +1 D",
     [(HSC, "    boosted.damage = weapon.damage + HIGH_SPEED_CARNAGE_BONUS",
       "    boosted.damage = weapon.damage" + MARK)], (TV,)),
    ("High-speed Carnage: a dice-notation Damage is left alone",
     [(HSC, "        boosted.damage_notation = _plus(weapon.damage_notation)",
       "        boosted.damage_notation = weapon.damage_notation" + MARK)], (TV,)),
    ("High-speed Carnage: applies without a charge",
     [(HSC, '    return (squad is not None and bool(getattr(squad, "charged_this_turn", False))',
       "    return (squad is not None and True" + MARK)], (TV,)),
    ("High-speed Carnage: reaches ranged weapons too",
     [(HSC, '    if weapon is None or getattr(weapon, "weapon_type", None) != MELEE or not applies(squad):',
       "    if weapon is None or not applies(squad):" + MARK)], (TV,)),
    ("High-speed Carnage: not in the Fight adjuster chain",
     [(FI, "        weapon = high_speed_carnage.adjusted_weapon(weapon, self.fighting_squad)",
       "        weapon = weapon" + MARK)], (TV,)),
    ("High-speed Carnage: every model must print it",
     [(UN, "    high_speed_carnage = True  # see game/high_speed_carnage.py; inherited by BikerNobProfile",
       "    high_speed_carnage = False" + MARK)], (TV,)),

    # ------------------------------------------------------- Deff from Above
    ("Deff from Above: a reactive shot gains it",
     [(DFA, "    if squad is None or reactive or ingress_controller is None:",
       "    if squad is None or ingress_controller is None:" + MARK)], (TV,)),
    ("Deff from Above: no ingress needed",
     [(DFA, '    return squad in getattr(ingress_controller, "ingressed_this_turn", ())',
       "    return True" + MARK)], (TV,)),
    ("Deff from Above: a penalty instead of a bonus",
     [(DFA, "    return [Modifier(-1, DEFF_FROM_ABOVE_NAME)]",
       "    return [Modifier(1, DEFF_FROM_ABOVE_NAME)]" + MARK)], (TV,)),
    ("Deff from Above: not in the Shooting hit modifiers",
     [(SH, "        modifiers.extend(deff_from_above.hit_modifiers(",
       "        modifiers.extend([] if True else deff_from_above.hit_modifiers(" + MARK)], (TV,)),
    ("Deff from Above: the Deffkoptas do not print it",
     [(UN, "    deff_from_above = True  # see game/deff_from_above.py",
       "    deff_from_above = False" + MARK)], (TV,)),

    # ---------------------------------------- Dread 'Ard / Mobile Fortress
    ("Mobile Fortress: melee attacks are reduced too",
     [(DR, '    if getattr(weapon, "weapon_type", None) == RANGED:', "    if True:" + MARK)], (TV,)),
    ("Mobile Fortress: the session hands no weapon",
     [(DRES, "        reduced = damage_reduction.adjusted_damage(model, result, self.weapon)",
       "        reduced = damage_reduction.adjusted_damage(model, result)" + MARK)], (TV,)),
    ("Mobile Fortress: printed as an every-attack reduction",
     [(UN, "    ranged_damage_reduction = 1  # Mobile Fortress - see game/damage_reduction.py",
       "    damage_reduction = 1" + MARK)], (TV,)),
    ("Dread 'Ard: gone from the Deff Dread",
     [(UN, "    damage_reduction = 1  # Dread 'Ard - see game/damage_reduction.py",
       "    damage_reduction = 0" + MARK)], (TV,)),
    ("Damaged 6: read as Damaged 5",
     [(UN, "    damaged_threshold = 6  # CORE: Damaged 6 (rule 24.39)",
       "    damaged_threshold = 5" + MARK)], (TV,)),

    # --------------------------------------------------------- transport lines
    ("Trukk: JUMP PACK models are not refused",
     [(UN, '    transport_excludes = ("jump_pack", "ghazghkull_thraka")  # "cannot transport GHAZGHKULL THRAKA/JUMP PACK models"',
       '    transport_excludes = ("ghazghkull_thraka",)' + MARK)], (TV,)),
    ("Battlewagon: a capacity of 12",
     [(UN, '    transport_capacity = 22  # "a transport capacity of 22 ORKS INFANTRY models"',
       "    transport_capacity = 12" + MARK)], (TV,)),

    # -------------------------------------------------------- Aerial Manoover
    ("Aerial Manoover: an engaged unit is offered",
     [(AM, "        if engagement.is_engaged(squad, tokens):", "        if False:" + MARK)], (TV,)),
    ("Aerial Manoover: offered when rule 20.03 destroys it",
     [(AM, "        return not withdrawal_is_doomed(self.turn_tracker)", "        return True" + MARK)], (TV,)),
    ("Aerial Manoover: offered to the side whose Fight phase ended",
     [(AM, "        others = sorted({s.owner for s in squads if s is not None and s.owner != mover_before})",
       "        others = sorted({s.owner for s in squads if s is not None and s.owner == mover_before})" + MARK)],
     (TV,)),
    ("Aerial Manoover: the AI is prompted",
     [(AM, "            if player in self.auto_players:", "            if False:" + MARK)], (TV,)),
    ("Aerial Manoover: only the first unit is ever asked",
     [(AM, "                self.decision_manager, eligible, self.can_use,",
       "                self.decision_manager, eligible[:1], self.can_use," + MARK)], (TV,)),
    ("main.py: Aerial Manoover is not offered",
     [(MAIN, "            aerial_manoover_controller.offer_at_end_of_fight_phase(",
       "            (lambda *_a: None)(" + MARK)], (TV, WIRING)),
    ("main.py: no AI policy for Aerial Manoover",
     [(MAIN, "        turn_tracker=turn_tracker, auto_players=ai_players," + NL
       + "        choose=lambda eligible: aerial_manoover_choice(state, turn_tracker, eligible))",
       "        turn_tracker=turn_tracker, auto_players=ai_players," + NL
       + "        choose=None)" + MARK)], (TV,)),

    # ------------------------------------------------------------ Pilin' Out
    ("Pilin' Out: fires in the Trukk owner's own Movement phase",
     [(PO, "        if tt.phase != PHASE_MOVEMENT or tt.turn_owner != mover.owner:",
       "        if tt.phase != PHASE_MOVEMENT:" + MARK)], (TV,)),
    ("Pilin' Out: fires in any phase",
     [(PO, "        if tt.phase != PHASE_MOVEMENT or tt.turn_owner != mover.owner:",
       "        if tt.turn_owner != mover.owner:" + MARK)], (TV,)),
    ("Pilin' Out: no 8\" range",
     [(PO, "            if any(edge_distance(token, m) <= PILIN_OUT_RANGE_IN for m in living):",
       "            if True:" + MARK)], (TV,)),
    ("Pilin' Out: every TRANSPORT has it",
     [(PO, '    return bool(getattr(profile, "pilin_out", False))', "    return True" + MARK)], (TV,)),
    ("Pilin' Out: the mode is determine_mode()'s",
     [(PO, "        self.transport_controller.start_disembark(passenger, mode=RAPID)",
       "        self.transport_controller.start_disembark(passenger)" + MARK)], (TV,)),
    ("Pilin' Out: the next passenger is asked while a placement is open",
     [(PO, "        while self._current is None and self._asking is None and self._queue:",
       "        while self._asking is None and self._queue:" + MARK)], (TV,)),
    ("Pilin' Out: a declined passenger is asked again",
     [(PO, "        if passenger is None or id(passenger) in self._declined:",
       "        if passenger is None:" + MARK)], (TV,)),
    ("Pilin' Out: a cancelled placement is not a decline",
     [(PO, "                self._declined.add(id(squad))", "                pass" + MARK)], (TV,)),
    ("Pilin' Out: the AI is prompted",
     [(PO, "            if passenger.owner in self.auto_players:", "            if False:" + MARK)], (TV,)),
    ("Pilin' Out: an arrival that did not land still triggers",
     [(PO, "        living = [m for m in mover.models if not m.is_dead() and m in tokens]",
       "        living = [m for m in mover.models if not m.is_dead()]" + MARK)], (TV,)),
    ("Pilin' Out: an enemy disembark does not trigger",
     [(PO, "            return self.notify_move_ended(squad)", "            return False" + MARK)], (TV,)),
    ("Pilin' Out: the Trukk does not print it",
     [(UN, "    pilin_out = True  # see game/pilin_out.py", "    pilin_out = False" + MARK)], (TV,)),

    # ------------------------------------------------ transport resolved hook
    ("transport: nothing is told a disembark resolved",
     [(TR, "        for listener in list(self.on_disembark_resolved or ()):",
       "        for listener in ():" + MARK)], (TV,)),
    ("transport: start_disembark ignores a printed mode",
     [(TR, "        self._disembark_mode = mode if mode is not None else self.determine_mode(squad.embarked_in, squad)",
       "        self._disembark_mode = self.determine_mode(squad.embarked_in, squad)" + MARK)], (TV,)),
    ("transport: a Combat disembark resolves before its hazard roll",
     [(TR, "            if mode in (COMBAT, EMERGENCY):",
       "            self._fire_resolved(squad, True)" + MARK + NL + "            if mode in (COMBAT, EMERGENCY):")],
     (TV,)),

    # --------------------------------------------------------------- main.py
    ("main.py: Pilin' Out does not hear moves",
     [(MAIN, "    movement_controller.on_move_finished.append(pilin_out_controller.on_move_finished)",
       "    pass" + MARK)], (TV,)),
    ("main.py: Pilin' Out does not hear arrivals",
     [(MAIN, "    ingress_controller.on_ingress_resolved.append(pilin_out_controller.on_ingress_resolved)",
       "    pass" + MARK)], (TV,)),
    ("main.py: Pilin' Out does not hear disembarks",
     [(MAIN, "    transport_controller.on_disembark_resolved.append(pilin_out_controller.on_disembark_resolved)",
       "    pass" + MARK)], (TV,)),
    ("main.py: the decline memo is never cleared",
     [(MAIN, "            pilin_out_controller.reset_movement_phase()", "            pass" + MARK)], (TV,)),
    ("main.py: the charge lock is swept over the ending player's units only",
     [(MAIN, "            for squad in state.all_squads():", "            for squad in ending_squads:" + MARK)], (TV,)),

    # ---------------------------------------------------------------------- AI
    ("AI: Pilin' Out never lets them out",
     [(AG, "    return remaining > 0 and _expected_incoming_wounds(state, transport_squad) >= remaining",
       "    return False" + MARK)], (TV,)),
    ("AI: Aerial Manoover never withdraws",
     [(AG, "    return hyperphasing_choice(state, turn_tracker, candidates, len(candidates or ()))",
       "    return []" + MARK)], (TV,)),
    ("AI: the matchup hint reads the carried profile only",
     [(AG, "            for profile in weapon_profiles.valued_profiles(weapon, target):",
       "            for profile in weapon_profiles.profiles(weapon)[:1]:" + MARK)], (TP,)),
]


def main():
    check_only = "--check" in sys.argv
    probes = PROBES
    if "--only" in sys.argv:
        needle = sys.argv[sys.argv.index("--only") + 1]
        probes = [p for p in PROBES if needle in p[0]]
        if not probes:
            print("no probe label contains %r" % needle)
            raise SystemExit(2)
    touched = sorted({path for _l, edits, _s in probes for path, _a, _r in edits})
    for path in touched:
        if "AB-PROBE" in read(path):
            print("REFUSED: %s already contains the AB-PROBE marker" % path)
            raise SystemExit(2)
    bad_anchor = 0
    for label, edits, _suites in probes:
        for path, anchor, _replacement in edits:
            n = read(path).count(anchor)
            if n != 1:
                print("  ANCHOR x%d  %s (%s)" % (n, label, path))
                bad_anchor += 1
    if check_only:
        print("%d probe(s), %d anchor problem(s)" % (len(probes), bad_anchor))
        raise SystemExit(1 if bad_anchor else 0)

    before = {path: digest(path) for path in touched}
    suites = sorted({s for _l, _e, ss in probes for s in ss})
    base = {}
    for suite in suites:
        got, total, text = run(suite)
        if got is None or got == "HANG":
            print("BASELINE DID NOT RUN for %s:%s%s" % (suite, NL, text[-2000:]))
            raise SystemExit(2)
        base[suite] = total - got
        print("baseline %-36s %s/%s (%d red)" % (suite, got, total, total - got))
    print()
    sys.stdout.flush()

    bad = bad_anchor
    runs = 0
    for label, edits, probe_suites in probes:
        originals = {path: read(path) for path, _a, _r in edits}
        ok = True
        for path, anchor, replacement in edits:
            src = read(path)
            if src.count(anchor) != 1:
                print("  SKIP     %s: anchor not unique in %s (%d)" % (label, path, src.count(anchor)))
                ok = False
                break
            write(path, src.replace(anchor, replacement))
        try:
            if not ok:
                continue
            for suite in probe_suites:
                runs += 1
                got, tot, out = run(suite)
                if got == "HANG":
                    verdict, detail, tail = "HANG", "suite timed out after %ds" % TIMEOUT_S, []
                    bad += 1
                elif got is None:
                    verdict = "CRASH"
                    detail = "suite crashed - a probe must turn it RED, not crash it"
                    bad += 1
                    tail = [ln for ln in out.splitlines() if ln.strip()][-1:]
                elif tot - got > base[suite]:
                    verdict = "BITES"
                    detail = "%s/%s (%d red)" % (got, tot, tot - got)
                    tail = [ln.strip() for ln in out.splitlines() if ln.strip().startswith("FAIL:")][:1]
                else:
                    verdict = "NO BITE"
                    detail = "%s/%s - FINDING ABOUT THE TEST" % (got, tot)
                    bad += 1
                    tail = []
                print("  %-8s %s [%s]: %s" % (verdict, label, suite, detail))
                for ln in tail:
                    print("             " + ln[:110])
                sys.stdout.flush()
        finally:
            for path, text in originals.items():
                write(path, text)

    after = {path: digest(path) for path in touched}
    drift = [p for p in touched if before[p] != after[p]]
    print()
    if drift:
        print("RESTORE FAILED for: %s" % ", ".join(drift))
        bad += 1
    print("%d probe(s), %d suite run(s)" % (len(probes), runs))
    print("%d probe run(s) did not bite" % bad if bad else "every probe bit")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
