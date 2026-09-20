"""A/B probes for War Horde: its four Enhancements, six Stratagems, the AI's
handlers, and the shared-ledger seam the detachment exposed (a kept model swept
again the next frame).

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
writing nothing - safe to run beside anything.
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

WH = "test_ork_war_horde.py"
UI = "test_ork_detachment_ui.py"
WIRING = "test_event_chain_wiring.py"

NB = os.path.join("game", "horde_orks_is_never_beaten.py")
BH = os.path.join("game", "horde_breakin_heads.py")
HIT = os.path.join("game", "horde_hit_em_harder.py")
MOW = os.path.join("game", "horde_mow_em_down.py")
CRD = os.path.join("game", "horde_close_range_dakka.py")
FFI = os.path.join("game", "horde_fungus_fuel_injection.py")
BOSS = os.path.join("game", "enh_da_boss_is_watchin.py")
WOPPA = os.path.join("game", "enh_headwoppas_killchoppa.py")
FAD = os.path.join("game", "fight_after_death.py")
GS = os.path.join("game", "game_state.py")
OBJ = os.path.join("game", "objectives.py")
SQ = os.path.join("game", "squad.py")
SIO = os.path.join("game", "scene_io.py")
FI = os.path.join("game", "fight.py")
SH = os.path.join("game", "shooting.py")
CS = os.path.join("game", "coldstar.py")
MX = os.path.join("game", "move_exceptions.py")
ACT = os.path.join("game", "activation_state.py")
ENH = os.path.join("game", "enhancements.py")
WAR = os.path.join("game", "war_horde.py")
AG = os.path.join("ai", "agent_driver.py")
MAIN = "main.py"


def lines(*parts):
    return NL.join(parts)


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


def gone(*anchor_lines):
    """Replace a guard `if ...:` / `    return ...` with `pass`, keeping its indentation."""
    indent = anchor_lines[0][:len(anchor_lines[0]) - len(anchor_lines[0].lstrip())]
    return lines(*anchor_lines), indent + "pass" + MARK


# (label, [(path, anchor, replacement)], suites)
PROBES = [
    # ------------------------------------------------------- the shared ledger
    ("the sweep takes a kept model again (the pre-fix world)",
     # One line: game/game_state.py is stored with CRLF, so a two-line anchor
     # joined with "\n" never matches.
     [(GS, '                     if token.is_dead() and not getattr(token, "kept_after_death", False)]',
       "                     if token.is_dead()]" + MARK)], (WH,)),
    ("the ledger no longer marks a kept model",
     [(FAD, "        model.kept_after_death = True", "        pass" + MARK)], (WH,)),
    ("a model handed over twice is owed twice",
     [(FAD, lines("        if model not in self._owed:", "            self._owed.append(model)"),
       "        self._owed.append(model)" + MARK)], (WH,)),
    ("removal leaves the mark on",
     [(FAD, "            model.kept_after_death = False", "            pass" + MARK)], (WH,)),
    ("remove_for() removes every unit's kept models",
     [(FAD, '        mine = [m for m in self._owed if getattr(m, "squad", None) is squad]',
       "        mine = list(self._owed)" + MARK)], (WH,)),
    ("a kept dead model adds Objective Control",
     [(OBJ, lines("            # Objective Control: it is destroyed, only not REMOVED yet.",
                  "            if token.is_dead():", "                continue"),
       "            # Objective Control: it is destroyed, only not REMOVED yet." + MARK)], (WH,)),
    ("a kept dead model counts for coherency",
     [(SQ, lines("        # is destroyed, only not removed yet. A unit without one is unaffected.",
                 "        models = [m for m in self.models if not m.is_dead()]"),
       "        models = list(self.models)" + MARK)], (WH,)),
    ("a save lists a kept model as a living one",
     [(SIO, '                for m in squad.models if not getattr(m, "kept_after_death", False)',
       "                for m in squad.models" + MARK)], (WH,)),

    # ---------------------------------------------------- Orks Is Never Beaten
    ("Never Beaten ignores riled up",
     [(NB, "        return NEVER_BEATEN_RILED_UP_BONUS if riled_up.is_riled_up(squad) else 0",
       "        return 0" + MARK)], (WH,)),
    ("Never Beaten opens on a ranged attack",
     [(NB, "        if not melee or attacking_squad is None or target_squad is None:",
       "        if attacking_squad is None or target_squad is None:" + MARK)], (WH,)),
    ("Never Beaten accepts a TITANIC unit",
     [(NB, *gone("        if titanic.is_titanic_unit(squad):", "            return False"))], (WH,)),
    ("Never Beaten rolls for a unit already selected to fight",
     [(NB, "        return self.is_active(squad) and not self.has_been_selected_to_fight(squad)",
       "        return self.is_active(squad)" + MARK)], (WH,)),
    ("Never Beaten: the AI ignores its verdict",
     [(NB, *gone("        if target_squad.owner in self.auto_players and not self.is_worth_using(",
                 "                target_squad, attacking_squad):", "            return False"))], (WH,)),
    ("main.py never removes a unit's kept models when it has fought",
     [(MAIN, "            never_beaten_controller.on_unit_finished_fighting(_fighter)",
       "            pass" + MARK)], (WH,)),
    ("main.py never feeds Never Beaten from the sweep",
     [(MAIN, "        never_beaten_controller.intercept_destroyed(_swept)", "        pass" + MARK)], (WH,)),

    # ---------------------------------------------------------- Breakin' Heads
    ("Breakin' Heads accepts an unattached unit",
     [(BH, *gone("    if not attached_units.is_attached_unit(squad):", "        return False"))], (WH,)),
    ("Breakin' Heads accepts a non-INFANTRY unit",
     [(BH, '    return attached_units.unit_has_keyword(squad, lambda m: getattr(m.profile, "infantry", False))',
       "    return True" + MARK)], (WH,)),
    ("Breakin' Heads offers over open dice",
     [(BH, *gone('        if self.dice_manager is not None and getattr(self.dice_manager, "pending_values", None) is not None:',
                 "            return False"))], (WH,)),
    ("Breakin' Heads never lifts the shock",
     [(BH, "            squad.battle_shocked = False", "            pass" + MARK)], (WH,)),
    ("Breakin' Heads: the AI ignores its verdict",
     [(BH, *gone("                if self.verdict is not None and not self.verdict(squad):",
                 "                    continue"))], (WH,)),
    ("main.py never registers Breakin' Heads at the battle-shock door",
     [(MAIN, "    battle_shock_module.add_became_battle_shocked_listener(breakin_heads_controller.on_became_battle_shocked)",
       "    pass" + MARK)], (WH,)),
    ("main.py never raises the queued offer",
     [(MAIN, "        breakin_heads_controller.offer_pending()", "        pass" + MARK)], (WH,)),
    ("main.py never clears the listener list between battles",
     [(MAIN, "    battle_shock_module.clear_became_battle_shocked_listeners()", "    pass" + MARK)], (WH,)),

    # ---------------------------------------------------------- Hit 'Em Harder
    ("Hit 'Em Harder is offered when every weapon already has [LETHAL HITS]",
     [(HIT, *gone("        if not would_change_anything(squad):", "            return False"))], (WH,)),
    ("Hit 'Em Harder outside the Fight phase",
     [(HIT, *gone("        if self.turn_tracker.phase != PHASE_FIGHT:", "            return False"))], (WH, UI)),
    ("game/fight.py's chain drops Hit 'Em Harder",
     [(FI, "        weapon = horde_hit_em_harder.adjusted_weapon(weapon, self.fighting_squad)",
       "        pass" + MARK)], (WH,)),
    ("main.py builds Hit 'Em Harder off the registry",
     [(MAIN, "hit_em_harder_controller = proactive_stratagems.add(HitEmHarderController(",
       "hit_em_harder_controller = (HitEmHarderController(" + MARK)], (WH, UI, WIRING)),
    ("main.py never resets Hit 'Em Harder",
     [(MAIN, "        hit_em_harder_controller.reset_phase(_horde_squads)", "        pass" + MARK)], (WH,)),
    ("a save loses Hit 'Em Harder",
     [(ACT, '    "hit_em_harder_active",', "   " + MARK)], (WH,)),

    # ------------------------------------------------------------ Mow 'Em Down
    ("Mow 'Em Down accepts a WALKER",
     [(MOW, '    return not attached_units.unit_has_keyword(squad, lambda m: getattr(m.profile, "walker", False))',
       "    return True" + MARK)], (WH,)),
    ("Mow 'Em Down accepts a unit that did not charge",
     [(MOW, *gone('        if not getattr(squad, "charged_this_turn", False):', "            return False"))], (WH, UI)),
    ("game/fight.py's chain drops Mow 'Em Down",
     [(FI, "        weapon = horde_mow_em_down.adjusted_weapon(weapon, self.fighting_squad)",
       "        pass" + MARK)], (WH,)),

    # ------------------------------------------------------- Close-Range Dakka
    ("Close-Range Dakka mid-activation",
     [(CRD, *gone("        if self.shooting_controller.active_squad is squad:", "            return False"))], (WH, UI)),
    ("Close-Range Dakka in your opponent's Shooting phase",
     [(CRD, *gone("        if squad.owner != self.turn_tracker.turn_owner:", "            return False"))], (UI,)),
    ("game/shooting.py's chain drops Close-Range Dakka",
     [(SH, "        weapon = horde_close_range_dakka.adjusted_weapon(weapon, self.active_squad)",
       "        pass" + MARK)], (WH,)),

    # --------------------------------------------------- Fungus-Fuel Injection
    ("Fungus-Fuel Injection after the unit moved",
     [(FFI, *gone('            if squad in getattr(self.movement_controller, "moved_squad_ids", ()):',
                  "                return False"))], (WH, UI)),
    ("the Move characteristic drops Fungus-Fuel Injection",
     [(CS, "    total += horde_fungus_fuel_injection.move_bonus_for(squad)", "    pass" + MARK)], (WH,)),

    # ------------------------------------------------------------ Enhancements
    ("Da Boss is Watchin' is once per unit, not per army",
     [(BOSS, "        return not self.is_used(squad.owner, squad)", "        return True" + MARK)], (WH, UI)),
    ("Da Boss is Watchin' outside your Movement phase",
     [(BOSS, "        if tt.phase != PHASE_MOVEMENT or squad.owner != tt.turn_owner:",
       "        if False:" + MARK)], (WH, UI)),
    ("main.py builds Da Boss off the registry",
     [(MAIN, "da_boss_controller = proactive_stratagems.add(DaBossIsWatchinController(",
       "da_boss_controller = (DaBossIsWatchinController(" + MARK)], (UI, WIRING)),
    ("Headwoppa's Killchoppa without a charge",
     [(WOPPA, *gone('    if not getattr(getattr(model, "squad", None), "charged_this_turn", False):',
                    "        return weapon"))], (WH,)),
    ("game/fight.py's chain drops Headwoppa's Killchoppa",
     [(FI, "        weapon = enh_headwoppas_killchoppa.adjusted_weapon(weapon, pairs[0][0] if pairs else None)",
       "        pass" + MARK)], (WH,)),
    ("the bearer shares its melee group",
     [(FI, "            enh_headwoppas_killchoppa.attack_key(model),", "            False," + MARK)], (WH,)),
    ("the Move characteristic drops Follow Me Ladz",
     [(CS, "    total += enh_follow_me_ladz.move_bonus_for(squad)", "    pass" + MARK)], (WH,)),
    ("Kunnin' But Brutal loses its SHOOT half",
     [(MX, lines("            or enh_kunnin_but_brutal.applies(squad)",
                 "            or any(_flag(squad, name) for name in SHOOT_AFTER_FALL_BACK_FLAGS))"),
       "            or any(_flag(squad, name) for name in SHOOT_AFTER_FALL_BACK_FLAGS))" + MARK)], (WH,)),
    ("Kunnin' But Brutal loses its CHARGE half",
     [(MX, "            or enh_kunnin_but_brutal.applies(squad)" + NL
       + "            # Da Big Hunt's Glory Hog prints ONLY \"declare a charge\", so it is",
       "            # Da Big Hunt's Glory Hog prints ONLY \"declare a charge\", so it is" + MARK)], (WH,)),
    ("a registry point value drifts from the corpus",
     [(ENH, '_add("Follow Me Ladz", 20, _WAR_HORDE,',
       '_add("Follow Me Ladz", 25, _WAR_HORDE,' + MARK + NL + "    ")], (WH,)),
    ("Get Stuck In without the detachment gate",
     [(WAR, *gone('    if not fields_war_horde(getattr(squad, "owner", None)):', "        return weapon"))], (WH,)),

    # --------------------------------------------------------------------- AI
    ("the AI's Da Boss ignores reach",
     [(AG, *gone("        if gap is None or gap > observation.advance_reach_in(squad) + CHARGE_RANGE_IN:",
                 "            continue"))], (WH,)),
    ("the AI's Fungus-Fuel ignores the Move window",
     [(AG, "        if gap is None or not (move < gap <= move + ffi.FUNGUS_FUEL_BONUS_IN):",
       "        if gap is None:" + MARK)], (WH,)),
    ("the AI's Close-Range Dakka ignores its dice floor",
     [(AG, "        if extra >= crd.CLOSE_RANGE_DAKKA_MIN_EXTRA_DICE and (best is None or extra > best[0]):",
       "        if (best is None or extra > best[0]):" + MARK)], (WH,)),
    ("the AI's Hit 'Em Harder ignores its gain floor",
     [(AG, "        if gain >= hit.HIT_EM_HARDER_MIN_GAIN and (best is None or gain > best[0]):",
       "        if (best is None or gain > best[0]):" + MARK)], (WH,)),
    ("the AI's Mow 'Em Down ignores the target size",
     [(AG, "        if size >= mow.MOW_EM_DOWN_MIN_TARGET_MODELS and (best is None or size > best[0]):",
       "        if (best is None or size > best[0]):" + MARK)], (WH,)),
]


def main():
    check_only = "--check" in sys.argv
    probes = PROBES
    # --only SUBSTRING re-runs just the probes whose label contains it (a probe
    # that did not bite is re-checked after the test is fixed, not the whole set).
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
