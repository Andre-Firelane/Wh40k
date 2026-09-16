"""A/B probes for the 2026-09 Ork mob abilities (stage E3a, part 2b): Ammo Runts,
Tide of Muscle, Never Too Busy to Fight, Mobbed, Rokkit Charge (and the AI's
verdict), Krumpin' Time, Arrogant Invulnerability (and the AP-worsening
extraction), Downtrodden, Thievin' Scavengers, and main.py's wiring.

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

TM = "test_ork_mobs.py"
WIRING = "test_event_chain_wiring.py"
WAGON = "test_battlewagon.py"
SCENE = "test_scene_activation.py"

OAR = os.path.join("game", "ork_ammo_runts.py")
TOM = os.path.join("game", "tide_of_muscle.py")
KT = os.path.join("game", "krumpin_time.py")
MOB = os.path.join("game", "mobbed.py")
RK = os.path.join("game", "rokkit_charge.py")
AINV = os.path.join("game", "arrogant_invulnerability.py")
APW = os.path.join("game", "ap_worsening.py")
TS = os.path.join("game", "thievin_scavengers.py")
TR = os.path.join("game", "transport.py")
FO = os.path.join("game", "formations.py")
ACTS = os.path.join("game", "actions.py")
DR = os.path.join("game", "damage_resolution.py")
SH = os.path.join("game", "shooting.py")
FI = os.path.join("game", "fight.py")
ACT = os.path.join("game", "activation_state.py")
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
    # ------------------------------------------------------------ Ammo Runts
    ("Ammo Runts: the bonus is not in the Shooting hit modifiers",
     [(SH, "        modifiers.extend(ork_ammo_runts.hit_modifiers(self.active_squad))", "        pass" + MARK)], (TM,)),
    ("Ammo Runts: never offered when selected to shoot",
     [(SH, "            self.ork_ammo_runts.offer(squad)", "            pass" + MARK)], (TM,)),
    ("Ammo Runts: a penalty instead of a bonus",
     [(OAR, "    return [Modifier(-AMMO_RUNTS_HIT_BONUS, AMMO_RUNTS_NAME)]",
       "    return [Modifier(AMMO_RUNTS_HIT_BONUS, AMMO_RUNTS_NAME)]" + MARK)], (TM,)),
    ("Ammo Runts: the once-per-battle spend is not recorded",
     [(OAR, "        setattr(squad, self.USED_ATTR, True)", "        pass" + MARK)], (TM,)),
    ("Ammo Runts: offered outside your Shooting phase",
     [(OAR,) + gone("        if tt is not None and (tt.phase != PHASE_SHOOTING or squad.owner != tt.turn_owner):",
                    "            return \"not your Shooting phase\"")], (TM,)),
    ("Ammo Runts: a human is not asked (used outright for everyone)",
     [(OAR, lines("        if squad.owner in self.auto_players:", "            return self.use(squad)"),
       "        return self.use(squad)" + MARK)], (TM,)),
    ("Ammo Runts: the spend is not saved",
     [(ACT, '    "ammo_runts_used",', '    # "ammo_runts_used",' + MARK)], (TM, SCENE)),
    ("main.py: the Ammo Runts grant never expires",
     [(MAIN, "        ork_ammo_runts.reset_phase({t.squad for t in state.tokens if t.squad is not None})",
       "        pass" + MARK)], (TM,)),
    ("main.py: ShootingController never gets the Ammo Runts controller",
     [(MAIN, "        ammo_runt=ammo_runt_controller, ork_ammo_runts=ork_ammo_runts_controller,",
       "        ammo_runt=ammo_runt_controller," + MARK)], (TM,)),

    # --------------------------------------------------------- Tide of Muscle
    ("Tide of Muscle: not in the fight chain",
     [(FI, "        weapon = tide_of_muscle.adjusted_weapon(weapon, self.fighting_squad)", "        pass" + MARK)], (TM,)),
    ("Tide of Muscle: ignores whether the unit charged",
     [(TOM, lines('    return (squad is not None and bool(getattr(squad, "charged_this_turn", False))',
                  '            and bool(unit_wide_ability(squad, "tide_of_muscle")))'),
       '    return squad is not None and bool(unit_wide_ability(squad, "tide_of_muscle"))' + MARK)], (TM,)),
    ("Tide of Muscle: mutates the carried weapon",
     [(TOM, lines("    granted = copy.copy(weapon)", "    granted.lethal_hits = True", "    return granted"),
       lines("    weapon.lethal_hits = True", "    return weapon" + MARK))], (TM,)),

    # ------------------------------------------------ Never Too Busy to Fight
    ("Never Too Busy: the engaged clause ignores it",
     [(ACTS, "            and not never_too_busy_to_fight.applies(squad)", "            and True" + MARK)], (TM,)),
    ("Never Too Busy: lifts the battle-shocked clause too",
     [(ACTS, lines("    if squad.battle_shocked:", '        return False, "battle-shocked"'),
       lines("    if squad.battle_shocked and not never_too_busy_to_fight.applies(squad):",
             '        return False, "battle-shocked"' + MARK))], (TM,)),

    # ---------------------------------------------------------------- Mobbed
    ("Mobbed: always -1, never -2",
     [(MOB, "    return MOBBED_BIG_MOB_PENALTY if len(living_models(squad)) >= MOBBED_BIG_MOB_MODELS else MOBBED_PENALTY",
       "    return MOBBED_PENALTY" + MARK)], (TM,)),
    ("Mobbed: counts dead models",
     [(MOB, '    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]',
       '    return list(getattr(squad, "models", ()) or ())' + MARK)], (TM,)),
    ("Mobbed: tests any engaged enemy, not only MONSTER/VEHICLE",
     [(MOB, "         if living_models(e) and is_monster_or_vehicle_unit(e) and units_are_engaged(squad, e)),",
       "         if living_models(e) and units_are_engaged(squad, e))," + MARK)], (TM,)),
    ("Mobbed: tests friendly units too",
     [(MOB, "               if t.squad is not None and t.squad.owner != squad.owner and not t.is_dead()}",
       "               if t.squad is not None and not t.is_dead()}" + MARK)], (TM,)),
    ("Mobbed: overwrites a roll another rule has open",
     [(MOB, '        return bool(getattr(dice, "pending_values", None))', "        return False" + MARK)], (TM,)),
    ("Mobbed: the acknowledgement does not release the queue",
     [(MOB, lines("        \"\"\"The queue's re-entry point - one more test per acknowledged roll.\"\"\"",
                  "        return self._drain()"),
       lines("        \"\"\"The queue's re-entry point - one more test per acknowledged roll.\"\"\"",
             "        return False" + MARK))], (TM,)),
    ("main.py: Mobbed is never fed the charge end",
     [(MAIN, "        mobbed_controller.on_charge_move_finished)", "        (lambda squad: None))" + MARK)], (TM,)),
    ("main.py: Mobbed's queue is never acknowledged",
     [(MAIN, "        mobbed_controller.on_dice_acknowledged()", "        pass" + MARK)], (TM,)),

    # --------------------------------------------------------- Rokkit Charge
    ("Rokkit Charge: not in the fight chain",
     [(FI, "        weapon = rokkit_charge.adjusted_weapon(weapon, self.fighting_squad)", "        pass" + MARK)], (TM,)),
    ("Rokkit Charge: never offered when selected to fight",
     [(FI, "            self.rokkit_charge.offer(squad)", "            pass" + MARK)], (TM,)),
    ("Rokkit Charge: no [HAZARDOUS]",
     [(RK, "    boosted.hazardous = True", "    pass" + MARK)], (TM,)),
    ("Rokkit Charge: no +1 Strength",
     [(RK, "    boosted.strength = weapon.strength + ROKKIT_CHARGE_BONUS", "    boosted.strength = weapon.strength" + MARK)], (TM,)),
    ("Rokkit Charge: a dice-notation Attacks keeps its bonus",
     [(RK, '    boosted.attacks_notation = _plus(getattr(weapon, "attacks_notation", None))',
       '    boosted.attacks_notation = getattr(weapon, "attacks_notation", None)' + MARK)], (TM,)),
    ("Rokkit Charge: offered without a charge",
     [(RK, lines('        return (has_ability(squad) and bool(getattr(squad, "charged_this_turn", False))',
                 "                and not is_active(squad))"),
       "        return has_ability(squad) and not is_active(squad)" + MARK)], (TM,)),
    ("Rokkit Charge: the AI ignores its verdict",
     [(RK, "            if self.verdict is not None and not self.verdict(squad):", "            if False:" + MARK)], (TM,)),
    ("the fight hazard ledger reads the printed weapon",
     [(FI, "        if pairs and self._adjusted_weapon(pairs, _haz_target).hazardous:",
       "        if pairs and pairs[0][1].hazardous:" + MARK)], (TM,)),
    ("the AI's verdict ignores the hazard cost",
     [(AG, "    return gain > loss", "    return gain > 0" + MARK)], (TM,)),
    ("the AI's A/B leaves the boosted weapons on the unit",
     [(AG, lines("        setattr(squad, flag, was_active)", "        for model in squad.models:",
                 "            if id(model) in originals:", "                model.weapons = originals[id(model)]"),
       "        setattr(squad, flag, was_active)" + MARK)], (TM,)),
    ("main.py: the Rokkit Charge verdict is not injected",
     [(MAIN, "            verdict=lambda squad: rokkit_charge_verdict(squad, fight_controller)),",
       "            verdict=None)," + MARK)], (TM,)),

    # --------------------------------------------------------- Krumpin' Time
    ("Krumpin' Time: ignores riled up",
     [(KT, lines('    return (squad is not None and bool(unit_wide_ability(squad, "krumpin_time"))',
                 "            and riled_up.is_riled_up(squad))"),
       '    return squad is not None and bool(unit_wide_ability(squad, "krumpin_time"))' + MARK)], (TM,)),
    ("Krumpin' Time: not in the fight hit modifiers",
     [(FI, "        modifiers.extend(krumpin_time.hit_modifiers(self.fighting_squad))", "        pass" + MARK)], (TM,)),
    ("Krumpin' Time: leaks into the Shooting phase",
     [(SH, "        modifiers.extend(ork_ammo_runts.hit_modifiers(self.active_squad))",
       lines("        modifiers.extend(ork_ammo_runts.hit_modifiers(self.active_squad))",
             "        from game import krumpin_time as _kt",
             "        modifiers.extend(_kt.hit_modifiers(self.active_squad))" + MARK))], (TM,)),

    # ---------------------------------------------- Arrogant Invulnerability
    ("Arrogant Invulnerability: not in save_thresholds()",
     [(DR, "    ap = arrogant_invulnerability.adjusted_ap(ap, model)", "    pass" + MARK)], (TM,)),
    ("Arrogant Invulnerability: read off the model, not the unit (19.04)",
     [(AINV, lines("    from game.squad import unit_wide_ability  # lazy: damage_resolution imports this module",
                   '    return bool(unit_wide_ability(squad, "arrogant_invulnerability"))'),
       '    return bool(getattr(model.profile, "arrogant_invulnerability", False))' + MARK)], (TM,)),
    ("AP worsening runs past 0",
     [(APW, "    return min(0, ap + steps)", "    return ap + steps" + MARK)], (TM, WAGON)),

    # ------------------------------------------------------------ Downtrodden
    ("Downtrodden: counted per model",
     [(TR, "    return others + (downtrodden + 1) // 2", "    return others + downtrodden" + MARK)], (TM,)),
    ("Downtrodden: rounds down",
     [(TR, "    return others + (downtrodden + 1) // 2", "    return others + downtrodden // 2" + MARK)], (TM,)),
    ("Downtrodden: can_embark() counts per model",
     [(TR, "        return squad_capacity_cost(squad) <= self.remaining_capacity(transport_token)",
       "        return sum(_model_capacity_cost(m) for m in squad.models) <= self.remaining_capacity(transport_token)" + MARK)],
     (TM,)),
    ("Downtrodden: embarked_model_count() counts per model",
     [(TR, "        return sum(squad_capacity_cost(s) for s in self.embarked_squads_in(transport_token))",
       "        return sum(_model_capacity_cost(m) for s in self.embarked_squads_in(transport_token) for m in s.models)" + MARK)],
     (TM,)),
    ("Downtrodden: Declare Battle Formations counts per model",
     [(FO, "    needed = squad_capacity_cost(squad)", "    needed = sum(_model_capacity_cost(m) for m in squad.models)" + MARK)],
     (TM,)),

    # ---------------------------------------------------- Thievin' Scavengers
    ("Thievin' Scavengers: 3\" range instead of rule 14.02's footprint",
     [(TS, "        if model.is_dead() or not objective.terrain_area.overlaps_model(model):",
       "        if model.is_dead() or objective.terrain_area.distance_to_model(model) > 3.0:" + MARK)], (TM,)),
    ("Thievin' Scavengers: a battle-shocked unit still controls",
     [(TS, "    if squad is None or objective.controlled_by != squad.owner or squad.battle_shocked:",
       "    if squad is None or objective.controlled_by != squad.owner:" + MARK)], (TM,)),
    ("Thievin' Scavengers: ignores who controls the objective",
     [(TS, "    if squad is None or objective.controlled_by != squad.owner or squad.battle_shocked:",
       "    if squad is None or squad.battle_shocked:" + MARK)], (TM,)),
    ("main.py: the end-of-Movement sweep is never called",
     [(MAIN, "            thievin_scavengers.secure_at_end_of_movement(", "            (lambda *a, **k: None)(" + MARK)],
     (TM,)),
    ("main.py: the sweep is asked for the flipped turn_owner",
     [(MAIN, "                state.objectives, state.tokens, mover_before, game_log=game_log)",
       "                state.objectives, state.tokens, turn_tracker.turn_owner, game_log=game_log)" + MARK)],
     (TM, WIRING)),
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
