"""A/B probes for the 2026-09 Ork Kill Rig (stage E3e): the psychic roll, Warpath,
Beastscent, the datasheet lines they hang on, the AI's two verdicts and fight
guard, and main.py's wiring.

Each probe restores one piece of a plausible broken world AT THE SOURCE, runs the
suite(s) that are supposed to catch it, and puts the file back byte for byte. A
probe that does NOT turn its suite red is a finding about the TEST; a probe that
makes the suite CRASH or HANG is a finding too. Either way this file exits
non-zero.

EXCLUSIVE. This rewrites source files while it runs. No suite, measurement, edit
or commit may run beside it. Every replacement carries the marker AB-PROBE, so
after a run

    git grep -n --untracked "AB-PROBE" -- . ":!ab_*.py" ":!CLAUDE*.md" ":!docs/*"

must come back empty (--untracked: new modules are untracked until the commit).
The driver also hashes every probed file before the first probe and after the
last, and fails if any differs. Every suite run has a timeout - a probe that
hangs a suite is reported, not waited on.

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

TK = "test_ork_kill_rig.py"
WC = "test_weapon_characteristics.py"

PR = os.path.join("game", "psychic_roll.py")
WP = os.path.join("game", "warpath.py")
BS = os.path.join("game", "beastscent.py")
FI = os.path.join("game", "fight.py")
SH = os.path.join("game", "shooting.py")
TR = os.path.join("game", "transport.py")
UN = os.path.join("game", "units.py")
WE = os.path.join("game", "weapons.py")
AS = os.path.join("game", "activation_state.py")
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
    # ---------------------------------------------------------- psychic roll
    ("psychic roll: a battle-shocked unit may roll",
     [(PR, '        if getattr(squad, "battle_shocked", False):', "        if False:" + MARK)], (TK,)),
    ("psychic roll: the Unstable Energies budget is not asked",
     [(PR, "        if not unstable_energies.can_use(squad, psychic_level, self._battle_round()):",
       "        if False:" + MARK)], (TK,)),
    ("psychic roll: a pending die does not stop a second roll",
     [(PR, "        if self.dice_manager is None or self.dice_manager.is_pending or self._pending is not None:",
       "        if self.dice_manager is None:" + MARK)], (TK,)),
    ("psychic roll: the level is not spent",
     [(PR, "        unstable_energies.spend(squad, psychic_level, self._battle_round())", "        pass" + MARK)],
     (TK,)),
    ("psychic roll: a 1 does not battle-shock",
     [(PR, "        if value == PSYCHIC_ROLL_FAILURE:", "        if False:" + MARK)], (TK,)),
    ("psychic roll: every roll battle-shocks",
     [(PR, "        if value == PSYCHIC_ROLL_FAILURE:", "        if value is not None:" + MARK)], (TK,)),
    ("psychic roll: a replaced roll is read off the other die",
     [(PR, '        if getattr(self.dice_manager, "label", None) == label:', "        if True:" + MARK)], (TK,)),
    ("psychic roll: the shock bypasses the one door",
     [(PR, '            battle_shock.set_battle_shocked(squad, source="a psychic roll (%s)" % ability_name)',
       "            squad.battle_shocked = True" + MARK)], (TK,)),

    # --------------------------------------------------------------- Warpath
    ("Warpath: no [LETHAL HITS]",
     [(WP, "    granted.lethal_hits = True", "    pass" + MARK)], (TK,)),
    ("Warpath: no [PSYCHIC]",
     [(WP, "    granted.psychic = True", "    pass" + MARK)], (TK,)),
    ("Warpath: ranged weapons too",
     [(WP, '    if weapon is None or getattr(weapon, "weapon_type", None) != MELEE or not is_active(squad):',
       "    if weapon is None or not is_active(squad):" + MARK)], (TK,)),
    ("Warpath: a human is never asked",
     [(WP, "        if squad.owner in self.auto_players:", "        if True:" + MARK)], (TK,)),
    ("Warpath: the verdict is not asked",
     [(WP, "            if self.verdict is not None and not self.verdict(squad):", "            if False:" + MARK)],
     (TK,)),
    ("Warpath: no psychic roll",
     [(WP, "        self.psychic_roll.roll(squad, WARPATH_NAME, WARPATH_PSYCHIC_LEVEL)", "        pass" + MARK)],
     (TK,)),
    ("Warpath: the psyker gates are not asked",
     [(WP, "                and self.psychic_roll.can_roll(squad, WARPATH_PSYCHIC_LEVEL))", "                )" + MARK)],
     (TK,)),
    ("Warpath: reset_phase keeps the grant",
     [(WP, "            squad.warpath_active = False", "            pass" + MARK)], (TK,)),

    # ------------------------------------------------------------ fight.py
    ("fight: Warpath is not offered at selection",
     [(FI, "            self.warpath.offer(squad)", "            pass" + MARK)], (TK,)),
    ("fight: Warpath is not in the adjuster chain",
     [(FI, "        weapon = warpath.adjusted_weapon(weapon, self.fighting_squad)", "        pass" + MARK)], (TK,)),
    ("fight: [PSYCHIC] drops no hit modifier",
     [(FI, '        if weapon is not None and getattr(weapon, "psychic", False):', "        if False:" + MARK)], (TK,)),
    ("fight: the Hit roll's threshold is asked without the weapon",
     [(FI, "        hit_modifiers = self._hit_modifiers(fighter_model, target_squad," + NL
       + '                                            self._adjusted_weapon(group["pairs"], target_squad))',
       "        hit_modifiers = self._hit_modifiers(fighter_model, target_squad)" + MARK)], (TK,)),
    ("fight: the hit STEP asks without the weapon",
     [(FI, '            self._hit_modifiers(group["pairs"][0][0], target_squad, weapon),',
       '            self._hit_modifiers(group["pairs"][0][0], target_squad),' + MARK)], (TK,)),
    ("fight: Beastscent is not in the wound modifiers",
     [(FI, "        modifiers.extend(beastscent.wound_modifiers(self.fighting_squad, target_squad))",
       "        pass" + MARK)], (TK,)),

    # --------------------------------------------------------- shooting.py
    ("shooting: Beastscent is not in the wound modifiers",
     [(SH, "        modifiers.extend(beastscent.wound_modifiers(self.active_squad, target_squad))",
       "        pass" + MARK)], (TK,)),

    # ------------------------------------------------------------ Beastscent
    ("Beastscent: in the opponent's Movement phase too",
     [(BS, "        if tt is None or tt.phase != PHASE_MOVEMENT or tt.turn_owner != rig.owner:",
       "        if tt is None or tt.phase != PHASE_MOVEMENT:" + MARK)], (TK,)),
    ("Beastscent: in any phase",
     [(BS, "        if tt is None or tt.phase != PHASE_MOVEMENT or tt.turn_owner != rig.owner:",
       "        if tt is None or tt.turn_owner != rig.owner:" + MARK)], (TK,)),
    ("Beastscent: every TRANSPORT has it",
     [(BS, '    return bool(getattr(profile, "beastscent", False))', "    return True" + MARK)], (TK,)),
    ("Beastscent: the roll is the passenger's",
     [(BS, "        self.psychic_roll.roll(transport_token.squad, BEASTSCENT_NAME, BEASTSCENT_PSYCHIC_LEVEL)",
       "        self.psychic_roll.roll(passenger, BEASTSCENT_NAME, BEASTSCENT_PSYCHIC_LEVEL)" + MARK)], (TK,)),
    ("Beastscent: +1 against every target",
     [(BS, "    if not is_monster_or_vehicle_unit(target_squad):", "    if False:" + MARK)], (TK,)),
    ("Beastscent: a penalty instead of a bonus",
     [(BS, "BEASTSCENT_WOUND_BONUS = -1", "BEASTSCENT_WOUND_BONUS = 1" + MARK)], (TK,)),
    ("Beastscent: clear_turn keeps it",
     [(BS, "            squad.beastscent_active = False", "            pass" + MARK)], (TK,)),
    ("Beastscent: a human is never asked",
     [(BS, "        if rig.owner in self.auto_players:", "        if True:" + MARK)], (TK,)),
    ("Beastscent: the psyker gates are not asked",
     [(BS, "        return self.psychic_roll is not None and self.psychic_roll.can_roll(rig, BEASTSCENT_PSYCHIC_LEVEL)",
       "        return self.psychic_roll is not None" + MARK)], (TK,)),

    # ------------------------------------------------------------ transport
    ("transport: nothing hears a disembark start",
     [(TR, "            for listener in list(self.on_disembark_started or ()):",
       "            for listener in ():" + MARK)], (TK,)),

    # ------------------------------------------------------------ datasheet
    ("Kill Rig: Feel No Pain 6+ again",
     [(UN, '    feel_no_pain = "5+"  # CORE "Feel No Pain 5+" - rule 24.12, an existing generic field',
       '    feel_no_pain = "6+"' + MARK)], (TK,)),
    ("Kill Rig: the pre-codex capacity of 11",
     [(UN, '    transport_capacity = 12  # "a transport capacity of 12 BEAST SNAGGAS INFANTRY models"',
       "    transport_capacity = 11" + MARK)], (TK,)),
    ("Kill Rig: prints no Warpath",
     [(UN, '    warpath = True  # "Warpath (psychic level 1)" - see game/warpath.py', "    warpath = False" + MARK)],
     (TK,)),
    ("'Eavy Lobba: plain [BLAST]",
     [(WE, "    blast = 2  # [BLAST 2], see WeaponProfile.blast", "    blast = 1" + MARK)], (TK, WC)),
    ("save: Beastscent is not kept",
     [(AS, '    "beastscent_active",', MARK)], (TK,)),

    # --------------------------------------------------------------- main.py
    ("main.py: the psychic roll is never acknowledged",
     [(MAIN, "        psychic_roll_controller.on_dice_acknowledged()", "        pass" + MARK)], (TK,)),
    ("main.py: no Warpath on the FightController",
     [(MAIN, "        warpath=WarpathController(", "        unused_warpath=WarpathController(" + MARK)], (TK,)),
    ("main.py: Warpath outlives its phase",
     [(MAIN, "        warpath.reset_phase({t.squad for t in state.tokens if t.squad is not None})", "        pass" + MARK)],
     (TK,)),
    ("main.py: Beastscent does not listen",
     [(MAIN, "    transport_controller.on_disembark_started.append(beastscent_controller.on_disembark_started)",
       "    pass" + MARK)], (TK,)),
    ("main.py: Beastscent outlives its turn",
     [(MAIN, "                squad.beastscent_active = False", "                pass" + MARK)], (TK,)),

    # ------------------------------------------------------------------- AI
    ("AI: Warpath rolls on an objective",
     [(AG, "    return not _psychic_shock_costs_an_objective(state, squad)", "    return True" + MARK)], (TK,)),
    ("AI: Beastscent on a Combat disembark",
     [(AG, "    if disembark_mode in (COMBAT, EMERGENCY):", "    if False:" + MARK)], (TK,)),
    ("AI: Beastscent with no MONSTER/VEHICLE in reach",
     [(AG, "        if is_monster_or_vehicle_unit(squad):", "        if True:" + MARK)], (TK,)),
    ("AI: Beastscent at any distance",
     [(AG, "        if edge_distance(transport_token, token) > BEASTSCENT_REACH_IN:", "        if False:" + MARK)],
     (TK,)),
    ("AI: the fight driver throws its Hit roll over the psychic roll",
     [(AG, '    if getattr(fight_controller, "dice_manager", None) is not None and fight_controller.dice_manager.is_pending:',
       "    if False:" + MARK)], (TK,)),
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
