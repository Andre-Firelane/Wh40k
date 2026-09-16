"""A/B probes for the 2026-09 Ork specialists (stage E3c): Finderz Keeperz, Rokkit
Barrage, Bomb Squigs, Pulsa Rokkit, valued_profiles() and main.py's wiring.

Each probe restores one piece of a plausible broken world AT THE SOURCE, runs the
suite(s) that are supposed to catch it, and puts the file back byte for byte. A
probe that does NOT turn its suite red is a finding about the TEST; a probe that
makes the suite CRASH or HANG is a finding too. Either way this file exits
non-zero.

EXCLUSIVE. This rewrites source files while it runs. No suite, measurement, edit
or commit may run beside it. Every replacement carries the marker AB-PROBE, so
after a run

    git grep -n "AB-PROBE" -- . ":!ab_*.py" ":!CLAUDE*.md"

must come back empty. The driver also hashes every probed file before the first
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

TS = "test_ork_specialists.py"
WIRING = "test_event_chain_wiring.py"
DAAC = "test_aeldari_detachment_rules.py"
TP = "test_target_priority.py"
HG = "test_home_garrison.py"
TR = "test_transport_priority.py"

FK = os.path.join("game", "finderz_keeperz.py")
OBJ = os.path.join("game", "objectives.py")
RB = os.path.join("game", "rokkit_barrage.py")
BSAS = os.path.join("game", "battle_shock_after_shooting.py")
BS = os.path.join("game", "bomb_squigs.py")
PR = os.path.join("game", "pulsa_rokkit.py")
WP = os.path.join("game", "weapon_profiles.py")
DE = os.path.join("game", "damage_estimate.py")
CF = os.path.join("game", "combat_focus.py")
SQ = os.path.join("game", "squad.py")
SH = os.path.join("game", "shooting.py")
ACT = os.path.join("game", "activation_state.py")
DAI = os.path.join("ai", "deployment_ai.py")
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
    # ------------------------------------------------------- Finderz Keeperz
    ("Finderz Keeperz: not in the Shooting adjuster chain",
     [(SH, "        weapon = finderz_keeperz.adjusted_weapon(",
       "        weapon = weapon if True else finderz_keeperz.adjusted_weapon(" + MARK)], (TS,)),
    ("Finderz Keeperz: no AP bonus",
     [(FK, "    granted.ap = weapon.ap - FINDERZ_KEEPERZ_AP_BONUS", "    granted.ap = weapon.ap" + MARK)], (TS,)),
    ("Finderz Keeperz: a reactive shot gains it",
     [(FK, "    if reactive or not objectives or not has_ability(squad):",
       "    if not objectives or not has_ability(squad):" + MARK)], (TS,)),
    ("Finderz Keeperz: a melee weapon gains it",
     [(FK, '    if weapon is None or getattr(weapon, "weapon_type", None) != RANGED:',
       "    if weapon is None:" + MARK)], (TS,)),
    ("Finderz Keeperz: every model must print it (a supporting Painboy strips it)",
     [(FK, '    return squad is not None and bool(unit_wide_ability(squad, "finderz_keeperz"))',
       '    return squad is not None and all(getattr(m.profile, "finderz_keeperz", False) for m in squad.models)'
       + MARK)], (TS,)),
    ("objectives: the TARGET half of the shared OR is ignored",
     [(OBJ, "    return target_squad is not None and is_within_range_of_objective(",
       "    return False and target_squad is not None and is_within_range_of_objective(" + MARK)], (TS, DAAC)),

    # --------------------------------------------------------- Rokkit Barrage
    ("Rokkit Barrage: the flag is one the Tankbustas do not print",
     [(RB, '    flag = "rokkit_barrage"', '    flag = "finderz_keeperz"' + MARK)], (TS,)),
    ("Rokkit Barrage: excludes MONSTER/VEHICLE like Panicked Quarry",
     [(RB, "    eligible = staticmethod(any_target)",
       '    eligible = staticmethod(lambda s: not getattr(s.models[0].profile, "vehicle", False))' + MARK)], (TS,)),
    ("battle-shock base: no -1",
     [(BSAS, "    penalty = BATTLE_SHOCK_PENALTY", "    penalty = 0" + MARK)], (TS,)),
    ("battle-shock base: an AI owner is prompted",
     [(BSAS, "                or squad.owner in self.auto_players):", "                or False):" + MARK)], (TS,)),
    ("battle-shock base: the injected pick is ignored",
     [(BSAS, "        if len(targets) > 1 and self.target_pick is not None:", "        if False:" + MARK)], (TS,)),
    ("AI pick: an already battle-shocked unit is not avoided",
     [(AG, '        return (bool(getattr(squad, "battle_shocked", False)), not on_objective,',
       "        return (False, not on_objective," + MARK)], (TS,)),
    ("AI pick: objectives are ignored",
     [(AG, "        on_objective = bool(objectives) and is_within_range_of_objective(squad, objectives)",
       "        on_objective = False" + MARK)], (TS,)),
    ("AI pick: points are ignored",
     [(AG, '                -(getattr(squad, "points", None) or 0), squad.name)',
       "                0, squad.name)" + MARK)], (TS,)),

    # ------------------------------------------------------------ Bomb Squigs
    ("Bomb Squigs: an Advance throws one",
     [(BS, "        if kind != BOMB_SQUIGS_MOVE_KIND:", "        if False:" + MARK)], (TS,)),
    ("Bomb Squigs: the opponent's Movement phase counts",
     [(BS, "        if tt is not None and (tt.phase != PHASE_MOVEMENT or tt.turn_owner != squad.owner):",
       "        if tt is not None and tt.phase != PHASE_MOVEMENT:" + MARK)], (TS,)),
    ("Bomb Squigs: no twice-per-battle limit",
     [(BS, "        if squigs_left(squad) <= 0:", "        if False:" + MARK)], (TS,)),
    ("Bomb Squigs: no once-per-turn limit",
     [(BS, '        if tt is not None and getattr(squad, "bomb_squigs_turn", None) == turn_number(tt):',
       "        if False:" + MARK)], (TS,)),
    ("Bomb Squigs: no 12\" range",
     [(BS, "        if not any(gap_to(m, enemy) <= BOMB_SQUIGS_RANGE_IN for m in models):",
       "        if False:" + MARK)], (TS,)),
    ("Bomb Squigs: visibility ignored",
     [(BS, "        if visible is not None and not any(visible(m, enemy) for m in models):",
       "        if False:" + MARK)], (TS,)),
    ("Bomb Squigs: no Decline",
     [(BS, '        options.append(("Decline", None))', "        pass" + MARK)], (TS,)),
    ("Bomb Squigs: an AI owner is prompted",
     [(BS, "        if squad.owner in self.auto_players or self.decision_manager is None:",
       "        if self.decision_manager is None:" + MARK)], (TS,)),
    ("Bomb Squigs: the token is never spent",
     [(BS, '        squad.bomb_squigs_used = int(getattr(squad, "bomb_squigs_used", 0) or 0) + 1',
       "        pass" + MARK)], (TS,)),
    ("Bomb Squigs: a 2 does not fizzle",
     [(BS, "            if values[0] < BOMB_SQUIGS_THRESHOLD:", "            if False:" + MARK)], (TS,)),
    ("Bomb Squigs: the wounds never land",
     [(BS, '        self._inflict(ctx["target"], wounds)', "        pass" + MARK)], (TS,)),
    ("Bomb Squigs: a finished single-model session stays in the slot",
     [(BS, "        self._check_session_done()", "        pass" + MARK)], (TS,)),
    ("Bomb Squigs: three tokens",
     [(BS, "BOMB_SQUIGS_PER_BATTLE = 2", "BOMB_SQUIGS_PER_BATTLE = 3" + MARK)], (TS,)),
    ("Bomb Squigs: turn numbers are 0-based",
     [(BS, "    return turn_serial(turn_tracker) + 1", "    return turn_serial(turn_tracker)" + MARK)], (TS,)),
    ("Bomb Squigs: the spend is not saved",
     [(ACT, '    "bomb_squigs_used",', '    # "bomb_squigs_used",' + MARK)], (TS,)),

    # ------------------------------------------------------------ Pulsa Rokkit
    ("Pulsa Rokkit: never offered when selected to shoot",
     [(SH, "            self.pulsa_rokkit.offer(squad)", "            pass" + MARK)], (TS,)),
    ("Pulsa Rokkit: not in the Shooting adjuster chain",
     [(SH, "            weapon = self.pulsa_rokkit.adjusted_weapon(",
       "            weapon = weapon if True else self.pulsa_rokkit.adjusted_weapon(" + MARK)], (TS,)),
    ("Pulsa Rokkit: no AP bonus",
     [(PR, "        granted.ap = weapon.ap - PULSA_ROKKIT_AP_BONUS", "        granted.ap = weapon.ap" + MARK)], (TS,)),
    ("Pulsa Rokkit: no [LETHAL HITS]",
     [(PR, "        granted.lethal_hits = True", "        pass" + MARK)], (TS,)),
    ("Pulsa Rokkit: the grant reaches every target, not the marked one",
     [(PR, "        if target_squad is None or self.marked_target(squad) is not target_squad:",
       "        if target_squad is None or self.marked_target(squad) is None:" + MARK)], (TS,)),
    ("Pulsa Rokkit: a reactive shot gets it",
     [(PR, '        if reactive or weapon is None or getattr(weapon, "weapon_type", None) != RANGED:',
       '        if weapon is None or getattr(weapon, "weapon_type", None) != RANGED:' + MARK)], (TS,)),
    ("Pulsa Rokkit: any unit may be marked, not only MONSTER/VEHICLE",
     [(PR, "            if is_monster_or_vehicle_unit(enemy)", "            if True" + MARK)], (TS,)),
    ("Pulsa Rokkit: no 24\" range",
     [(PR, "            and any(gap_to(m, enemy) <= PULSA_ROKKIT_RANGE_IN for m in models)]",
       "            and True]" + MARK)], (TS,)),
    ("Pulsa Rokkit: the opponent's Shooting phase counts",
     [(PR, "        if tt is not None and (tt.phase != PHASE_SHOOTING or tt.turn_owner != squad.owner):",
       "        if tt is not None and tt.phase != PHASE_SHOOTING:" + MARK)], (TS,)),
    ("Pulsa Rokkit: asked again after marking",
     [(PR, "        if id(squad) in self._marks:", "        if False:" + MARK)], (TS,)),
    ("Pulsa Rokkit: the mark survives the phase",
     [(PR, "        self._marks.clear()", "        pass" + MARK)], (TS,)),
    ("Pulsa Rokkit: an AI owner is prompted",
     [(PR, "        if squad.owner in self.auto_players or self.decision_manager is None:",
       "        if self.decision_manager is None:" + MARK)], (TS,)),
    ("Pulsa Rokkit: a dead bearer still carries it",
     [(PR, '            if not m.is_dead() and getattr(m, "pulsa_rokkit", False)]',
       '            if getattr(m, "pulsa_rokkit", False)]' + MARK)], (TS,)),
    ("Pulsa Rokkit: no Decline",
     [(PR, '        options.append(("Decline", None))', "        pass" + MARK)], (TS,)),

    # ------------------------------------------------------ valued_profiles()
    ("valued_profiles: a hazardous profile counts",
     [(WP, '              if not getattr(p, "hazardous", False)', "              if True" + MARK)], (TS,)),
    ("valued_profiles: a Hunter profile counts against anything",
     [(WP, "              and (hunter_allows(p, target_squad) if target_squad is not None else not is_hunter(p))]",
       "              and True]" + MARK)], (TS, TP)),
    ("valued_profiles: nothing usable returns the whole chain",
     [(WP, "    return usable or chain[:1]", "    return usable or chain" + MARK)], (TS,)),
    ("deployment AI reads only the carried profile",
     [(DAI, "        for profile in weapon_profiles.valued_profiles(weapon):",
       "        for profile in weapon_profiles.profiles(weapon)[:1]:" + MARK)], (TS, TR)),
    ("combat_focus reach reads only the carried profile",
     [(CF, "            for profile in weapon_profiles.valued_profiles(weapon):",
       "            for profile in weapon_profiles.profiles(weapon)[:1]:" + MARK)], (TS, HG)),
    ("damage_estimate reads only the carried profile",
     [(DE, "            candidates = [p for p in weapon_profiles.valued_profiles(carried, defender)",
       "            candidates = [p for p in weapon_profiles.profiles(carried)[:1]" + MARK)], (TP,)),

    # --------------------------------------------------------------- retired
    ("Tank Hunters: the ranged-only flag counts in melee",
     [(SQ, "    if profile.tank_hunters_ranged_only and not melee:",
       "    if profile.tank_hunters_ranged_only:" + MARK)], (TS,)),

    # ----------------------------------------------------------------- main
    ("main: ShootingController is not handed Pulsa Rokkit",
     [(MAIN, "        ork_ammo_runts=ork_ammo_runts_controller, pulsa_rokkit=pulsa_rokkit_controller,",
       "        ork_ammo_runts=ork_ammo_runts_controller," + MARK)], (TS,)),
    ("main: Bomb Squigs never hears a move",
     [(MAIN, "    movement_controller.on_move_finished.append(bomb_squigs_controller.on_move_finished)",
       "    pass" + MARK)], (TS,)),
    ("main: Bomb Squigs' dice are never acknowledged",
     [(MAIN, "        bomb_squigs_controller.on_dice_acknowledged()", "        pass" + MARK)], (TS, WIRING)),
    ("main: the Pulsa Rokkit mark is never reset",
     [(MAIN, "        pulsa_rokkit_controller.reset_phase()", "        pass" + MARK)], (TS,)),
    ("main: Rokkit Barrage never hears a volley",
     [(MAIN, "        rokkit_barrage_controller.offer_after_shooting)", "        (lambda *a: None))" + MARK)], (TS,)),
    ("main: Bomb Squigs' open allocation does not hold the phase",
     [(MAIN, "            or bomb_squigs_controller.pending_damage_choice is not None",
       "            or False" + MARK)],
     # Specialists only: test_event_chain_wiring.py's section 10 walks gate ->
     # resolvable, never resolvable -> gate, so it cannot see a missing gate term.
     (TS,)),
    ("main: Bomb Squigs is missing from the damage-choice list",
     [(MAIN, "        krushin_impetus_controller, bomb_squigs_controller,",
       "        krushin_impetus_controller," + MARK)], (TS, WIRING)),
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
